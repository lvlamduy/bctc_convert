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
    _alias_occurrences,
    _money,
    _source_table,
    _two_period_axis,
    _unit_axis,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _compile_units as _compile_lossless_unit_policy,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
)
from bctc_ai.evaluation.source_reference_identity_v1 import (
    stable_unique_source_refs_v1,
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
    "MULTI_COMPONENT_AFS_OR_HTM_REQUIRED_QUALITY_VAMC_OPTIONAL_OWNER_RESET_FENCE_"
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


def _compile_investment_units(
    value: Any,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Compile the two exact source units accepted by this family.

    Investment-securities notes in the corpus are published in either million
    VND or exact VND, and neither may be silently rescaled.  Authenticate that
    exact lossless policy before delegating common alias validation.
    """

    if type(value) is not list:
        raise ValueError("investment-securities money-unit bindings are absent")
    accepted_units = {
        item.get("canonical_unit")
        for item in value
        if type(item) is dict and item.get("accepted") is True
    }
    if accepted_units != {"MILLION_VND", "VND"}:
        raise ValueError("investment-securities accepted money-unit axis is invalid")
    return _compile_lossless_unit_policy(canonical_clone_v1(value))


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
        != "AFS_OR_HTM_REQUIRED_QUALITY_VAMC_OPTIONAL_WITHIN_ONE_OWNER_RESET_FENCE"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("typed_control_exclusions")
        != [
            "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
            "LISTING_STATUS_VIEW",
            "NON_SNAPSHOT_MULTI_MONEY_AXIS_VIEW",
            "PROVISION_MOVEMENT",
            "INVESTMENT_SECURITIES_TRADING_ACTIVITY",
            "OTHER_LONG_TERM_INVESTMENT_VIEW",
            "INTEREST_RATE_OR_PERCENTAGE_VIEW",
        ]
    ):
        raise _error("investment-securities evaluation spec is invalid")
    try:
        unit_bindings, unit_binding_by_alias = _compile_investment_units(
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
        or tokens[0] in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
        or (len(tokens[0]) == 1 and "a" <= tokens[0] <= "z")
    ):
        tokens.pop(0)
    stripped = " ".join(tokens)
    return stripped == alias or stripped.startswith(alias + " ")


def _contains_ascii_bounded_alias(value: Any, alias: str) -> bool:
    """Match a normalized alias even when non-ASCII OCR text is attached."""

    text = _normalized(value)
    start = text.find(alias)
    while start >= 0:
        end = start + len(alias)
        left = text[start - 1] if start else ""
        right = text[end] if end < len(text) else ""
        left_bound = not left or not (left.isascii() and left.isalnum())
        right_bound = not right or not (right.isascii() and right.isalnum())
        if left_bound and right_bound:
            return True
        start = text.find(alias, start + 1)
    return False


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
    def roles_on(values: Sequence[Any]) -> set[str]:
        found: set[str] = set()
        for value in values:
            folded = _normalized(value)
            for role in _STRUCTURAL_ROLES:
                for alias in compiled_specs["aliases_by_role"][role]:
                    if not _contains_alias(value, alias):
                        continue
                    if role == "VAMC_BRANCH" and "khong bao gom" in folded:
                        continue
                    found.add(role)
        return found

    roles = roles_on(_surface_axis(section, table))
    local_values: list[Any] = [table.get("title_exact")]
    for row in table.get("rows") or []:
        if type(row) is dict:
            local_values.extend(row.get("hierarchy_path_exact") or [])
    local_roles = roles_on(local_values)
    local_core = local_roles & {"AFS_BRANCH", "HTM_BRANCH"}
    if len(local_core) == 1:
        # A section narrative can announce AFS and then serialize a separately
        # titled HTM table in the same section.  The table-local branch is the
        # nearer owner and must not remain ambiguous with that earlier caption.
        roles -= {"AFS_BRANCH", "HTM_BRANCH"}
        roles.update(local_core)
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
            # Gemini can preserve a non-Latin continuation annotation directly
            # beside an otherwise exact ancestor label (for example
            # ``Chứng khoán Nợ带有- ...``).  The normalized ASCII-boundary
            # lookup authenticates that visible ancestor without weakening the
            # stricter start-of-row rule used for the row being mapped.
            if not any(
                _matches_alias(value, alias) or _contains_ascii_bounded_alias(value, alias)
                for alias in matcher["aliases"]
            ):
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
    visible_group_roles: set[str] | None = None,
) -> int | None:
    label = row.get("label_exact")
    path = row.get("hierarchy_path_exact")
    if visible_group_roles is None:
        visible_group_roles = {
            group_role
            for group_role in _GROUP_ROLES
            if _path_has_role(
                path,
                group_role,
                compiled_specs=compiled_specs,
                label_exact=label,
                table_context_roles=table_context_roles,
            )
        }
    scores = []
    for matcher in compiled_specs["matchers_by_role"][role]:
        aliases = [alias for alias in matcher["aliases"] if _matches_alias(label, alias)]
        if not aliases:
            continue
        within = matcher["within_role"]
        if within is None:
            scores.extend(len(_normalized(alias)) for alias in aliases)
            continue
        path_bound = _path_has_role(
            path,
            within,
            compiled_specs=compiled_specs,
            label_exact=label,
            table_context_roles=table_context_roles,
        )
        bound = path_bound or _structural_context_supports_role(within, table_context_roles)
        # Some source tables flatten an intermediate group row.  Authenticate
        # that abbreviated lineage generically when the already-matched child
        # alias is under exactly one declared structural branch.  Ambiguous
        # aliases such as a bare "Khác" still match several group roles and are
        # rejected by the row ambiguity gate; branch evidence only prevents an
        # otherwise identical child label from crossing AFS and HTM.
        if visible_group_roles and within in _GROUP_ROLES:
            # A visible exact group ancestor is stronger than the abbreviated
            # structural-branch fallback below.  This prevents the same child
            # label (issuer/government/etc.) from crossing DEBT/EQUITY/OTHER.
            bound = within in visible_group_roles
        elif not bound and within in _GROUP_ROLES:
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
            if not visible_group_roles and (
                table_context_roles == {branch} or branch_visible_in_label
            ):
                bound = True
        if bound:
            scores.extend(len(_normalized(alias)) for alias in aliases)
    return max(scores) if scores else None


def _investment_document_unit_context_axis(
    page_json_by_version: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate one exact document-wide unit for this two-unit family.

    Unlike the shared single-output-unit helper, this family accepts both VND
    and million VND and must propagate whichever source unit is explicitly
    printed.  Only exact table-unit carriers count; at least two distinct pages
    must agree, and any accepted/unaccepted conflict fails closed.
    """

    aliases = list(compiled_specs["unit_binding_by_alias"])
    evidence = []
    conflicts = []
    for page_json_version_id, page_json in sorted(page_json_by_version.items()):
        if _PAGE_VERSION.fullmatch(page_json_version_id) is None or type(page_json) is not dict:
            raise _error("investment-securities document unit context page is invalid")
        sections = page_json.get("sections")
        if type(sections) is not list:
            raise _error("investment-securities document unit context section axis is invalid")
        for section_ordinal, section in enumerate(sections, start=1):
            if type(section) is not dict or type(section.get("tables")) is not list:
                continue
            for table_ordinal, table in enumerate(section["tables"], start=1):
                if type(table) is not dict:
                    continue
                unit_exact = table.get("unit_exact")
                if type(unit_exact) is not str or not unit_exact.strip():
                    continue
                matches = _alias_occurrences(_normalized(unit_exact), aliases)
                if not matches:
                    continue
                bindings = [compiled_specs["unit_binding_by_alias"][alias] for alias in matches]
                identities = {
                    (
                        binding["canonical_unit"],
                        binding["magnitude_power10"],
                        binding["accepted"],
                    )
                    for binding in bindings
                }
                locator = {
                    "page_json_version_id": page_json_version_id,
                    "section_id": f"s{section_ordinal}",
                    "source_page_status": page_json.get("status"),
                    "table_id": f"t{table_ordinal}",
                }
                if len(identities) != 1:
                    conflicts.append({**locator, "source_exact": unit_exact})
                    continue
                binding = bindings[0]
                evidence.append(
                    {
                        **locator,
                        "accepted": binding["accepted"],
                        "canonical_unit": binding["canonical_unit"],
                        "magnitude_power10": binding["magnitude_power10"],
                        "matched_aliases": matches,
                        "source_exact": unit_exact,
                        "source_kind": "TABLE_UNIT",
                    }
                )
    primary_evidence = [
        item for item in evidence if item["source_page_status"] == "PRIMARY_FINANCIAL_STATEMENT"
    ]
    primary_conflicts = [
        item for item in conflicts if item["source_page_status"] == "PRIMARY_FINANCIAL_STATEMENT"
    ]
    primary_root_evidence = _investment_primary_root_evidence(
        page_json_by_version, regions, compiled_specs=compiled_specs
    )

    def consensus(axis: list[dict[str, Any]], conflict_axis: list[dict[str, Any]]) -> bool:
        identities = {
            (item["canonical_unit"], item["magnitude_power10"], item["accepted"]) for item in axis
        }
        return (
            not conflict_axis
            and len(identities) == 1
            and len({item["page_json_version_id"] for item in axis}) >= 2
            and next(iter(identities))[2]
        )

    root_identities = {item["canonical_unit"] for item in primary_root_evidence}
    if len(root_identities) == 1:
        selected_evidence = primary_root_evidence
        consensus_scope = "PRIMARY_STATEMENT_FAMILY_ROOT_EXACT_VALUE_PAIR"
    elif consensus(primary_evidence, primary_conflicts):
        selected_evidence = primary_evidence
        consensus_scope = "PRIMARY_FINANCIAL_STATEMENT_TABLE_UNITS"
    elif consensus(evidence, conflicts):
        selected_evidence = evidence
        consensus_scope = "ALL_SELECTED_DOCUMENT_TABLE_UNITS"
    else:
        selected_evidence = []
        consensus_scope = None
    identities = {
        (
            item["canonical_unit"],
            item.get("magnitude_power10", 6 if item["canonical_unit"] == "MILLION_VND" else 0),
            item.get("accepted", True),
        )
        for item in selected_evidence
    }
    distinct_pages = {item["page_json_version_id"] for item in selected_evidence}
    unique = bool(selected_evidence)
    return {
        "canonical_unit": next(iter(identities))[0] if unique else None,
        "consensus_scope": consensus_scope,
        "conflicts": conflicts,
        "distinct_page_version_count": len(distinct_pages),
        "evidence": evidence,
        "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
        "primary_root_evidence": primary_root_evidence,
        "primary_root_evidence_axis_sha256": canonical_json_sha256_v1(primary_root_evidence),
        "rule": (
            "PRIMARY_FAMILY_ROOT_EXACT_VALUE_PAIR_ELSE_PRIMARY_STATEMENT_CONSENSUS_"
            "ELSE_ALL_DOCUMENT_CONSENSUS_AT_LEAST_TWO_PAGES"
        ),
        "status": "UNIQUE" if unique else "NOT_UNIQUE",
    }


def _investment_document_period_context_axis(
    page_json_by_version: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve one exact lane order for headerless component continuations."""

    local_evidence = []
    for region in regions:
        page = page_json_by_version.get(region["page_json_version_id"])
        if type(page) is not dict:
            continue
        _section_value, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        money_axis = _investment_money_axis(table)
        projected = _table_with_investment_money_axis(table, money_axis["money_column_ordinals"])
        axis = _investment_local_period_axis(projected)
        if axis.get("complete"):
            local_evidence.append(
                {
                    "page_json_version_id": region["page_json_version_id"],
                    "physical_page": region["physical_page"],
                    "section_id": region["section_id"],
                    "signatures": canonical_clone_v1(axis["signatures"]),
                    "source": axis["source"],
                    "table_id": region["table_id"],
                }
            )
    local_signatures = {
        canonical_json_sha256_v1(item["signatures"]): item["signatures"] for item in local_evidence
    }
    primary_root_evidence = _investment_primary_root_evidence(
        page_json_by_version, regions, compiled_specs=compiled_specs
    )
    root_signatures = {
        canonical_json_sha256_v1(item["period_signatures"]): item["period_signatures"]
        for item in primary_root_evidence
    }
    if len(local_signatures) == 1:
        signatures = next(iter(local_signatures.values()))
        source = "SELECTED_COMPONENT_LOCAL_PERIOD_CONSENSUS"
    elif not local_signatures and len(root_signatures) == 1:
        signatures = next(iter(root_signatures.values()))
        source = "PRIMARY_STATEMENT_FAMILY_ROOT_EXACT_VALUE_PAIR"
    else:
        signatures = None
        source = None
    return {
        "local_evidence": local_evidence,
        "primary_root_evidence": primary_root_evidence,
        "rule": "LOCAL_COMPONENT_CONSENSUS_ELSE_EXACT_VALUE_MATCHED_PRIMARY_FAMILY_ROOT",
        "signatures": canonical_clone_v1(signatures),
        "source": source,
        "status": "UNIQUE" if signatures is not None else "NOT_UNIQUE",
    }


def _investment_period_axis(
    table: Mapping[str, Any], *, document_period_context: Mapping[str, Any]
) -> dict[str, Any]:
    axis = _investment_local_period_axis(table)
    if axis.get("complete"):
        return axis
    if (
        axis.get("reasons") != ["TWO_PERIOD_AXIS_INCOMPLETE"]
        or document_period_context.get("status") != "UNIQUE"
    ):
        return axis
    context_signatures = document_period_context.get("signatures")
    local_signatures = axis.get("signatures")
    if (
        type(context_signatures) is not list
        or len(context_signatures) != 2
        or type(local_signatures) is not list
        or len(local_signatures) != 2
        or any(
            local is not None and local != context
            for local, context in zip(local_signatures, context_signatures, strict=True)
        )
    ):
        return axis
    return {
        **canonical_clone_v1(axis),
        "complete": True,
        "document_period_context_evidence": canonical_clone_v1(document_period_context),
        "reasons": [],
        "signatures": canonical_clone_v1(context_signatures),
        "source": "DOCUMENT_EXACT_PERIOD_CONTEXT",
    }


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
    # Some Gemini pages flatten several numbered notes into one section and
    # attach all subsection captions as narratives.  In that representation,
    # an other-long-term-investment table can inherit the preceding HTM
    # caption.  Its own visible rows remain authoritative: a row explicitly
    # naming ``đầu tư dài hạn`` is outside this family's schema.
    if any("dau tu dai han" in label for label in row_labels):
        return "OTHER_LONG_TERM_INVESTMENT_VIEW"
    activity_surface = " ".join([folded, *row_labels])
    trading_activity = "mua ban" in activity_surface and any(
        token in activity_surface
        for token in ("hoat dong", "lai", "lo", "thu nhap", "chi phi")
    )
    if trading_activity or any(token in activity_surface for token in _ACTIVITY_TOKENS):
        return (
            "INVESTMENT_SECURITIES_TRADING_ACTIVITY"
            if "mua ban" in activity_surface
            else "PROVISION_MOVEMENT"
        )
    columns = table.get("columns")
    if type(columns) is list:
        money_column_count = sum(
            type(column) is dict and column.get("value_kind") == "MONEY"
            for column in columns
        )
        percent_column_count = sum(
            type(column) is dict and column.get("value_kind") == "PERCENT"
            for column in columns
        )
        if money_column_count != 2 and percent_column_count and len(columns) > 2:
            return "INTEREST_RATE_OR_PERCENTAGE_VIEW"
    if any("chua niem yet" in label for label in row_labels) and any(
        "niem yet" in label and "chua niem yet" not in label for label in row_labels
    ):
        return "LISTING_STATUS_VIEW"
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


def _investment_money_axis(table: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve the two visible period lanes without trusting a blank spacer.

    A continued source table can contain three serialized columns even though
    the PDF visibly has only two value lanes: Gemini marks the first populated
    lane ``UNKNOWN``, inserts a universally blank ``MONEY`` spacer, and keeps
    the second populated lane as ``MONEY``.  Promote that exact populated pair
    only when the spacer is blank in every row and both retained lanes contain
    source-visible money.  All other column shapes retain their declared axis.
    """

    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        return {"money_column_ordinals": [], "projection": None}
    declared = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if len(columns) != 3 or len(declared) != 2:
        return {"money_column_ordinals": declared, "projection": None}
    unknown = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "UNKNOWN"
    ]
    if len(unknown) != 1:
        return {"money_column_ordinals": declared, "projection": None}

    def values_at(ordinal: int) -> list[Any]:
        return [
            row["values_exact"][ordinal - 1]
            for row in rows
            if type(row) is dict
            and type(row.get("values_exact")) is list
            and len(row["values_exact"]) == len(columns)
        ]

    blank_declared = [
        ordinal
        for ordinal in declared
        if values_at(ordinal) and all(v is None for v in values_at(ordinal))
    ]
    populated_declared = [
        ordinal for ordinal in declared if any(value is not None for value in values_at(ordinal))
    ]
    promoted = unknown[0]
    if (
        len(blank_declared) != 1
        or len(populated_declared) != 1
        or not any(value is not None for value in values_at(promoted))
    ):
        return {"money_column_ordinals": declared, "projection": None}
    selected = sorted([promoted, populated_declared[0]])
    return {
        "money_column_ordinals": selected,
        "projection": {
            "discarded_universally_blank_declared_money_ordinal": blank_declared[0],
            "promoted_populated_unknown_ordinal": promoted,
            "rule": "POPULATED_UNKNOWN_PLUS_POPULATED_MONEY_ACROSS_BLANK_SPACER",
        },
    }


def _table_with_investment_money_axis(
    table: Mapping[str, Any], money_column_ordinals: Sequence[int]
) -> dict[str, Any]:
    """Return a receipt-local table view with the authenticated period lanes."""

    clone = canonical_clone_v1(table)
    selected = set(money_column_ordinals)
    for ordinal, column in enumerate(clone.get("columns", []), start=1):
        if type(column) is not dict:
            continue
        if ordinal in selected:
            column["value_kind"] = "MONEY"
        elif column.get("value_kind") == "MONEY":
            column["value_kind"] = "UNKNOWN"
    # A small legacy Gemini frontier serialized visual line breaks as the two
    # literal characters ``\\n``.  Treat those characters as line separators
    # only inside column headers, and bind the exact before/after surfaces in
    # the receipt-local projection.  This prevents the trailing ``n`` from
    # turning ``Triệu đồng`` into a false bare-``đồng`` (VND) unit.
    repairs = []
    for column_ordinal, column in enumerate(clone.get("columns", []), start=1):
        if type(column) is not dict or type(column.get("header_path_exact")) is not list:
            continue
        for path_ordinal, value in enumerate(column["header_path_exact"], start=1):
            if type(value) is not str or "\\n" not in value:
                continue
            normalized = value.replace("\\n", "\n")
            column["header_path_exact"][path_ordinal - 1] = normalized
            repairs.append(
                {
                    "column_ordinal": column_ordinal,
                    "path_ordinal": path_ordinal,
                    "source_exact": value,
                    "projected_exact": normalized,
                }
            )
    if repairs:
        clone["investment_serialized_header_linebreak_projection"] = {
            "repairs": repairs,
            "rule": "LITERAL_BACKSLASH_N_IN_COLUMN_HEADER_TO_VISUAL_LINE_BREAK",
        }
    return clone


def _investment_local_period_axis(table: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve exact dates or the bank-note relative current/comparative labels."""

    axis = _two_period_axis(table)
    if axis.get("complete") or axis.get("reasons") != ["TWO_PERIOD_AXIS_INCOMPLETE"]:
        return axis
    if len(axis.get("money_column_ordinals", [])) != 2:
        return axis
    extra_aliases = (
        {"so du cuoi ky", "so du cuoi nam", "so du cuoi quy"},
        {"so du dau ky", "so du dau nam", "so du dau quy"},
    )
    signatures = canonical_clone_v1(axis.get("signatures"))
    semantic_roles = canonical_clone_v1(axis.get("semantic_roles_by_lane"))
    expected = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
    for lane, aliases in enumerate(extra_aliases):
        if signatures[lane] is not None:
            continue
        folded = _normalized(axis["headers_exact"][lane])
        matches = [alias for alias in aliases if alias == folded or f" {alias} " in f" {folded} "]
        if len(matches) == 1:
            signatures[lane] = ["SEMANTIC_ALIAS", expected[lane]]
            semantic_roles[lane] = [expected[lane]]
    if signatures != [
        ["SEMANTIC_ALIAS", "CURRENT_PERIOD"],
        ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
    ]:
        return axis
    return {
        **canonical_clone_v1(axis),
        "complete": True,
        "reasons": [],
        "semantic_roles_by_lane": semantic_roles,
        "signatures": signatures,
        "source": "LOCAL_MONEY_COLUMN_HEADERS_INVESTMENT_RELATIVE_ROLE",
    }


def _selected_family_total_pairs(
    page_json_by_version: Mapping[str, dict[str, Any]], regions: Sequence[Mapping[str, Any]]
) -> set[tuple[int, int]]:
    pairs = set()
    for region in regions:
        page = page_json_by_version.get(region["page_json_version_id"])
        if type(page) is not dict:
            continue
        _section_value, table = _source_table(
            page, section_id=region["section_id"], table_id=region["table_id"]
        )
        ordinals = _investment_money_axis(table)["money_column_ordinals"]
        if len(ordinals) != 2:
            continue
        for row in table.get("rows") or []:
            if type(row) is not dict or row.get("row_kind") not in {"SUBTOTAL", "TOTAL"}:
                continue
            values = row.get("values_exact")
            if type(values) is not list or any(ordinal > len(values) for ordinal in ordinals):
                continue
            try:
                pair = tuple(
                    _source_money(values[ordinal - 1])["coefficient"] for ordinal in ordinals
                )
            except ValueError:
                continue
            pairs.add(pair)
    return pairs


def _investment_primary_root_evidence(
    page_json_by_version: Mapping[str, dict[str, Any]],
    regions: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Find an explicit-unit primary-statement root that equals a note total."""

    selected_total_pairs = _selected_family_total_pairs(page_json_by_version, regions)
    evidence = []
    owner_aliases = {
        _normalized(alias) for alias in compiled_specs["query_policy"]["owner_aliases"]
    }
    for page_json_version_id, page in sorted(page_json_by_version.items()):
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                money_axis = _investment_money_axis(table)
                if len(money_axis["money_column_ordinals"]) != 2:
                    continue
                projected_table = _table_with_investment_money_axis(
                    table, money_axis["money_column_ordinals"]
                )
                unit_axis = _unit_axis(projected_table, compiled_specs=compiled_specs)
                period_axis = _investment_local_period_axis(projected_table)
                if not unit_axis.get("complete") or not period_axis.get("complete"):
                    continue
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if (
                        type(row) is not dict
                        or _normalized(row.get("label_exact")) not in owner_aliases
                    ):
                        continue
                    values = row.get("values_exact")
                    ordinals = money_axis["money_column_ordinals"]
                    if type(values) is not list or any(
                        ordinal > len(values) for ordinal in ordinals
                    ):
                        continue
                    try:
                        coefficients = tuple(
                            _source_money(values[ordinal - 1])["coefficient"]
                            for ordinal in ordinals
                        )
                    except ValueError:
                        continue
                    if coefficients not in selected_total_pairs:
                        continue
                    evidence.append(
                        {
                            "canonical_unit": unit_axis["canonical_unit"],
                            "coefficients": list(coefficients),
                            "page_json_version_id": page_json_version_id,
                            "period_signatures": canonical_clone_v1(period_axis["signatures"]),
                            "row_id": f"r{row_ordinal}",
                            "section_id": f"s{section_ordinal}",
                            "source_exact": row.get("label_exact"),
                            "source_kind": "PRIMARY_STATEMENT_FAMILY_ROOT_EXACT_VALUE_PAIR",
                            "table_id": f"t{table_ordinal}",
                            "unit_evidence": canonical_clone_v1(unit_axis["evidence"]),
                        }
                    )
    return evidence


def classify_gemini_json_investment_securities_table_v1(
    page_json: Any,
    section: Any,
    table: Any,
    *,
    compiled_specs: Mapping[str, Any],
    continuation_parent_roles: Sequence[str] = (),
) -> dict[str, Any]:
    """Inventory one table without assigning document-level ownership."""

    if type(page_json) is not dict or type(section) is not dict or type(table) is not dict:
        raise _error("investment-securities source table is invalid")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("investment-securities table axes are invalid")
    money_axis = _investment_money_axis(table)
    money_ordinals = money_axis["money_column_ordinals"]
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
    source_only_rows = []
    ambiguous_rows = []
    unbound_total_rows: list[tuple[int, Mapping[str, Any]]] = []
    combined_provision_control_ordinals = []
    unbound_money_row_ordinals = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        label = row.get("label_exact")
        values = row.get("values_exact")
        has_selected_axis = type(values) is list and all(
            1 <= ordinal <= len(values) for ordinal in money_ordinals
        )
        if not has_selected_axis:
            continue
        has_selected_value = any(values[ordinal - 1] is not None for ordinal in money_ordinals)
        visible_group_roles = {
            group_role
            for group_role in _GROUP_ROLES
            if _path_has_role(
                row.get("hierarchy_path_exact"),
                group_role,
                compiled_specs=compiled_specs,
                label_exact=row.get("label_exact"),
                table_context_roles=contexts,
            )
        }
        scored = [
            (role, score)
            for role in compiled_specs["bindings"]
            if (
                score := _role_match_score(
                    row,
                    role,
                    table_context_roles=contexts,
                    compiled_specs=compiled_specs,
                    visible_group_roles=visible_group_roles,
                )
            )
            is not None
        ]
        maximum = max((score for _role, score in scored), default=None)
        matched = [role for role, score in scored if score == maximum]
        structural_declarations = {
            role
            for role in _STRUCTURAL_ROLES
            if _row_declares_structural_role(row, role, compiled_specs=compiled_specs)
        }
        # A ruled anonymous SUBTOTAL/TOTAL with dash cells is a visible zero
        # control, not a decorative branch heading.  A numbered subsection
        # caption can nevertheless be serialized as TOTAL solely because it
        # carries ruled placeholder cells (for example a zero-population
        # quality-analysis heading).  Keep that explicit caption source-only;
        # all other ruled totals continue to the arithmetic resolver below.
        numbered_structural_caption = bool(
            re.match(r"^[0-9]+(?:\s+[0-9]+)*\b", _normalized(label) or "")
        )
        placeholder_structural_heading = bool(structural_declarations) and (
            row.get("row_kind") not in {"SUBTOTAL", "TOTAL"}
            or numbered_structural_caption
        )
        if placeholder_structural_heading:
            for ordinal in money_ordinals:
                try:
                    cell = _source_money(values[ordinal - 1])
                except ValueError:
                    placeholder_structural_heading = False
                    break
                if cell["coefficient"] is None and cell["state"] == "BLANK_SOURCE_CELL":
                    continue
                if cell["coefficient"] != 0 or not (
                    cell["state"] == "DASH_ZERO" or cell["state"].endswith("ZERO_IF_EQUATION_EXACT")
                ):
                    placeholder_structural_heading = False
                    break
        if not matched and placeholder_structural_heading:
            source_only_rows.append(
                {
                    "disposition": "SOURCE_ONLY_STRUCTURAL_HEADING_WITH_PLACEHOLDER_CELLS",
                    "owner_role": sorted(structural_declarations)[0],
                    "row_ordinal": row_ordinal,
                }
            )
            continue
        combined_provision_control = not matched and "du phong" in _normalized(label) and (
            any(
                _contains_alias(label, alias)
                for alias in compiled_specs["query_policy"]["owner_aliases"]
            )
            or (
                provision_section
                and "trai phieu doanh nghiep chua niem yet" in _normalized(label)
            )
        )
        if combined_provision_control:
            role_hits.append({"role": "UNSCOPED_TOTAL_CONTROL", "row_ordinal": row_ordinal})
            if provision_section:
                combined_provision_control_ordinals.append(row_ordinal)
            continue
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

    # A more detailed source row can reuse the same semantic role as an exact
    # ancestor (for example a named bond under the already mapped TCTD total).
    # Preserve it as source-only corroborating detail instead of double-counting
    # the schema leaf.
    retained_hits = []
    for hit in role_hits:
        row = rows[hit["row_ordinal"] - 1]
        path_axis = [
            value
            for value in row.get("hierarchy_path_exact") or []
            if type(value) is str and _normalized(value) != _normalized(row.get("label_exact"))
        ]
        same_role_ancestor = next(
            (
                prior
                for prior in retained_hits
                if prior["role"] == hit["role"]
                and any(
                    _contains_ascii_bounded_alias(
                        value,
                        _normalized(rows[prior["row_ordinal"] - 1].get("label_exact")),
                    )
                    for value in path_axis
                    if _normalized(rows[prior["row_ordinal"] - 1].get("label_exact"))
                )
            ),
            None,
        )
        if same_role_ancestor is None:
            retained_hits.append(hit)
            continue
        ancestor_row = rows[same_role_ancestor["row_ordinal"] - 1]
        ancestor_values = ancestor_row.get("values_exact")
        current_values = row.get("values_exact")
        ancestor_has_value = type(ancestor_values) is list and any(
            1 <= ordinal <= len(ancestor_values) and ancestor_values[ordinal - 1] is not None
            for ordinal in money_ordinals
        )
        current_has_value = type(current_values) is list and any(
            1 <= ordinal <= len(current_values) and current_values[ordinal - 1] is not None
            for ordinal in money_ordinals
        )
        if (
            hit["role"].endswith("_PROVISION")
            and ancestor_has_value
            and current_has_value
            and [
                ancestor_values[ordinal - 1]
                for ordinal in money_ordinals
                if ordinal <= len(ancestor_values)
            ]
            != [
                current_values[ordinal - 1]
                for ordinal in money_ordinals
                if ordinal <= len(current_values)
            ]
        ):
            # Two distinct rows carrying the same provision caption can be a
            # source-reader label shift at a subtotal boundary: the first is
            # the preceding debt subtotal and the second is the actual signed
            # provision.  Preserve both for the evaluator; it may reclassify
            # only after both debt and provision child equations prove the
            # interpretation.  Otherwise the distinct observations still fail
            # closed downstream.
            retained_hits.append(hit)
            continue
        if not ancestor_has_value and current_has_value:
            retained_hits[retained_hits.index(same_role_ancestor)] = hit
            source_only_rows.append(
                {
                    "disposition": "SOURCE_ONLY_STRUCTURAL_PARENT_FOR_MAPPED_SCHEMA_LEAF",
                    "owner_role": hit["role"],
                    "row_ordinal": same_role_ancestor["row_ordinal"],
                }
            )
            continue
        source_only_rows.append(
            {
                "disposition": "SOURCE_ONLY_BELOW_MAPPED_SCHEMA_LEAF",
                "owner_role": hit["role"],
                "row_ordinal": hit["row_ordinal"],
            }
        )
    role_hits = retained_hits

    # A source can print one schema leaf and immediately decompose it into
    # instrument-level rows introduced by ``Trong đó``.  Older Gemini JSON can
    # lose the leaf label from those child hierarchy paths while retaining the
    # ``Trong đó`` marker.  Collapse the children only when at least two rows
    # of the same role add exactly to the visible parent in both lanes.  This
    # preserves the schema-bound aggregate once and records every finer row as
    # source-only evidence rather than double-counting it.
    exact_detail_children = set()
    for role in sorted({hit["role"] for hit in role_hits}):
        if compiled_specs["child_by_role"].get(role, {}).get("role_kind") not in {
            "ADDITIVE_CHILD",
            "NONADDITIVE_CHILD",
        }:
            continue
        hits = sorted(
            (hit for hit in role_hits if hit["role"] == role),
            key=lambda hit: hit["row_ordinal"],
        )
        for parent_hit in hits:
            parent_ordinal = parent_hit["row_ordinal"]
            parent_path = rows[parent_ordinal - 1].get("hierarchy_path_exact") or []
            if any(
                "trong do" in _normalized(value) for value in parent_path if type(value) is str
            ):
                continue
            following_boundary = next(
                (
                    ordinal
                    for ordinal, row in enumerate(rows[parent_ordinal:], start=parent_ordinal + 1)
                    if type(row) is dict
                    and row.get("row_kind") in {"GROUP", "SUBTOTAL", "TOTAL"}
                ),
                len(rows) + 1,
            )
            children = [
                hit
                for hit in hits
                if parent_ordinal < hit["row_ordinal"] < following_boundary
                and any(
                    "trong do" in _normalized(value)
                    for value in rows[hit["row_ordinal"] - 1].get("hierarchy_path_exact") or []
                    if type(value) is str
                )
            ]
            if len(children) < 2:
                continue
            try:
                parent_pair = tuple(
                    _source_money(
                        rows[parent_ordinal - 1]["values_exact"][column_ordinal - 1]
                    )["coefficient"]
                    for column_ordinal in money_ordinals
                )
                child_pairs = [
                    tuple(
                        _source_money(
                            rows[child["row_ordinal"] - 1]["values_exact"][column_ordinal - 1]
                        )["coefficient"]
                        for column_ordinal in money_ordinals
                    )
                    for child in children
                ]
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            if not any(value for pair in child_pairs for value in pair) or parent_pair != tuple(
                sum(pair[lane] for pair in child_pairs) for lane in range(len(money_ordinals))
            ):
                continue
            for child in children:
                exact_detail_children.add(child["row_ordinal"])
                source_only_rows.append(
                    {
                        "disposition": (
                            "SOURCE_ONLY_EXACT_DETAIL_DECOMPOSITION_OF_MAPPED_SCHEMA_LEAF"
                        ),
                        "owner_role": role,
                        "row_ordinal": child["row_ordinal"],
                    }
                )
            break
    if exact_detail_children:
        role_hits = [
            hit for hit in role_hits if hit["row_ordinal"] not in exact_detail_children
        ]
        unbound_money_row_ordinals = [
            ordinal
            for ordinal in unbound_money_row_ordinals
            if ordinal not in exact_detail_children
        ]
        ambiguous_rows = [
            ordinal for ordinal in ambiguous_rows if ordinal not in exact_detail_children
        ]

    # Gemini sometimes resets hierarchy_path_exact to a generic "Trong đó"
    # node while preserving the immediately preceding typed parent row.  Bind
    # an otherwise-unmatched child only to that nearest source-visible group,
    # never across an intervening subtotal/total boundary.  The child alias and
    # its declared within_role must both agree with the parent.
    continuation_parents = set(continuation_parent_roles)
    if not continuation_parents <= _GROUP_ROLES:
        raise _error("investment-securities continuation parent role is invalid")
    recovered_ordinals = []
    total_boundaries = {ordinal for ordinal, _row in unbound_total_rows}
    for row_ordinal in unbound_money_row_ordinals:
        prior_groups = [
            hit
            for hit in role_hits
            if hit["row_ordinal"] < row_ordinal and hit["role"] in _GROUP_ROLES
        ]
        eligible_parents = (
            {max(prior_groups, key=lambda item: item["row_ordinal"])["role"]}
            if prior_groups
            else continuation_parents
        )
        if not eligible_parents:
            continue
        parent_boundary = (
            max(prior_groups, key=lambda item: item["row_ordinal"])["row_ordinal"]
            if prior_groups
            else 0
        )
        if any(parent_boundary < ordinal < row_ordinal for ordinal in total_boundaries):
            continue
        row = rows[row_ordinal - 1]
        label = row.get("label_exact")
        scored = []
        for role in compiled_specs["bindings"]:
            aliases = [
                alias
                for matcher in compiled_specs["matchers_by_role"][role]
                if matcher["within_role"] in eligible_parents
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
    # A page-break continuation may serialize its final ruled subtotal as an
    # ITEM with no label. Bind it only when it is the last value-bearing row
    # and the continued fragment exposes one unambiguous AFS/HTM branch.
    continuation_trailing_totals = []
    if table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE":
        value_rows = [
            ordinal
            for ordinal, row in enumerate(rows, start=1)
            if type(row) is dict
            and type(row.get("values_exact")) is list
            and any(
                1 <= column <= len(row["values_exact"])
                and row["values_exact"][column - 1] is not None
                for column in money_ordinals
            )
        ]
        current_core_branches = {
            role.split("_", 1)[0]
            for role in (hit["role"] for hit in role_hits)
            if role.startswith(("AFS_", "HTM_")) and "_PROVISION" not in role
        }
        for row_ordinal in list(unbound_money_row_ordinals):
            row = rows[row_ordinal - 1]
            if (
                not _normalized(row.get("label_exact"))
                and value_rows
                and row_ordinal == max(value_rows)
                and len(current_core_branches) == 1
            ):
                role_hits.append(
                    {
                        "role": next(iter(current_core_branches)) + "_TOTAL",
                        "row_ordinal": row_ordinal,
                    }
                )
                continuation_trailing_totals.append(row_ordinal)
    if continuation_trailing_totals:
        projected = set(continuation_trailing_totals)
        unbound_money_row_ordinals = [
            ordinal for ordinal in unbound_money_row_ordinals if ordinal not in projected
        ]
    # A source can disclose a finer breakdown below a schema-bound leaf.  It
    # must remain visible in the receipt, but it is not a second additive
    # observation of the leaf and must not poison the otherwise complete
    # family table.  This applies only when the exact hierarchy names one
    # already-bound ADDITIVE/NONADDITIVE leaf and the row itself matched no
    # declared role; rows below a schema group remain unresolved because a
    # more specific existing child ID may still apply.
    source_only_ordinals = set()
    for row_ordinal in unbound_money_row_ordinals:
        row = rows[row_ordinal - 1]
        path_values = {
            _normalized(value)
            for value in row.get("hierarchy_path_exact") or []
            if type(value) is str and _normalized(value)
        }
        owner_hits = []
        for hit in role_hits:
            if hit["row_ordinal"] >= row_ordinal:
                continue
            owner_role = hit["role"]
            owner_kind = compiled_specs["child_by_role"].get(owner_role, {}).get("role_kind")
            if owner_kind not in {"ADDITIVE_CHILD", "NONADDITIVE_CHILD"}:
                continue
            owner_label = _normalized(rows[hit["row_ordinal"] - 1].get("label_exact"))
            if owner_label and owner_label in path_values:
                owner_hits.append(hit)
        owner_roles = sorted({hit["role"] for hit in owner_hits})
        if len(owner_roles) == 1:
            source_only_ordinals.add(row_ordinal)
            source_only_rows.append(
                {
                    "disposition": "SOURCE_ONLY_BELOW_MAPPED_SCHEMA_LEAF",
                    "owner_role": owner_roles[0],
                    "row_ordinal": row_ordinal,
                }
            )
    if source_only_ordinals:
        unbound_money_row_ordinals = [
            ordinal for ordinal in unbound_money_row_ordinals if ordinal not in source_only_ordinals
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
        generic_family_total = any(
            _contains_alias(row.get("label_exact"), alias)
            for alias in compiled_specs["query_policy"]["owner_aliases"]
        ) and not any(
            _contains_alias(row.get("label_exact"), alias)
            for branch_role in ("AFS_BRANCH", "HTM_BRANCH")
            for alias in compiled_specs["aliases_by_role"][branch_role]
        )
        if generic_family_total:
            # A labelled "total investment securities" remains family-wide
            # even when it is printed at the end of a locally HTM-typed table.
            # The arithmetic resolver must bind it to an exact combined (or
            # single-branch) frontier instead of silently relabelling it HTM.
            role_hits.append({"role": "UNSCOPED_TOTAL_CONTROL", "row_ordinal": row_ordinal})
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
        vamc_precedes = any(
            hit["row_ordinal"] < row_ordinal and hit["role"].startswith("VAMC_")
            for hit in role_hits
        )
        # Once a visible VAMC component has started, an anonymous source total
        # can be VAMC-only or a combined HTM/VAMC (or AFS/VAMC) carrying total.
        # Keep it unscoped for arithmetic resolution instead of forcing it
        # back into the only AFS/HTM branch seen earlier in the table.
        candidates = path_branches or (set() if vamc_precedes else core_branches)
        if len(candidates) == 1:
            role_hits.append(
                {"role": next(iter(candidates)) + "_TOTAL", "row_ordinal": row_ordinal}
            )
            continue
        current_roles = {hit["role"] for hit in role_hits}
        row_declared_branches = {
            role
            for role in _STRUCTURAL_ROLES
            if _row_declares_structural_role(row, role, compiled_specs=compiled_specs)
        }
        if not row_declared_branches:
            # Gemini can serialize a ruled subtotal with neither label nor
            # hierarchy. Recover its scope from the nearest source-visible
            # structural heading inside the current block. An intervening
            # subtotal/total is a hard boundary, so this can bind the VAMC
            # subtotal but cannot leak VAMC ownership to a later family total.
            block_start = max(
                (
                    ordinal
                    for ordinal, prior_row in enumerate(rows[: row_ordinal - 1], start=1)
                    if type(prior_row) is dict
                    and prior_row.get("row_kind") in {"SUBTOTAL", "TOTAL"}
                ),
                default=0,
            )
            prior_branch_declarations = [
                (
                    prior_ordinal,
                    {
                        role
                        for role in _STRUCTURAL_ROLES
                        if _row_declares_structural_role(
                            prior_row, role, compiled_specs=compiled_specs
                        )
                    },
                )
                for prior_ordinal, prior_row in enumerate(
                    rows[block_start : row_ordinal - 1], start=block_start + 1
                )
                if type(prior_row) is dict
            ]
            prior_branch_declarations = [
                item for item in prior_branch_declarations if len(item[1]) == 1
            ]
            if prior_branch_declarations:
                row_declared_branches = max(
                    prior_branch_declarations, key=lambda item: item[0]
                )[1]
        quality_control = "QUALITY_BRANCH" in row_declared_branches or (
            not row_declared_branches and contexts == {"QUALITY_BRANCH"}
        )
        vamc_control = "VAMC_BRANCH" in row_declared_branches or (
            not row_declared_branches and contexts == {"VAMC_BRANCH"}
        )
        if quality_control and any(role.startswith("QUALITY_") for role in current_roles):
            role_hits.append({"role": "QUALITY_TOTAL_CONTROL", "row_ordinal": row_ordinal})
        elif (
            vamc_control
            and any(role.startswith("VAMC_") for role in current_roles)
            and (
                "VAMC_BRANCH" in row_declared_branches
                or not any(role.startswith(("AFS_", "HTM_")) for role in current_roles)
            )
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
    if combined_provision_control_ordinals and not component_roles:
        component_roles = ["AFS", "HTM"]
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
        "combined_provision_control_ordinals": combined_provision_control_ordinals,
        "continuation_parent_roles": sorted(continuation_parents),
        "contexts": sorted(contexts),
        "disposition": disposition,
        "money_column_ordinals": money_ordinals,
        "money_axis_projection": money_axis["projection"],
        "reasons": sorted(set(reasons)),
        "role_hits": role_hits,
        "source_only_rows": source_only_rows,
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
    region = {
        "component_roles": canonical_clone_v1(item["classification"]["component_roles"]),
        "continuation_parent_roles": canonical_clone_v1(
            item["classification"]["continuation_parent_roles"]
        ),
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
    target = item.get("adjacent_blank_projection_target")
    if target is not None:
        region["single_lane_blank_projection"] = {
            "rule": (
                "ADJACENT_PAGE_CONTINUATION_SINGLE_SOURCE_BLANK_LANE_PROJECTED_"
                "TO_EXACT_TARGET_TWO_PERIOD_AXIS"
            ),
            "source_money_column_ordinal": item["classification"]["money_column_ordinals"][0],
            "target_page_json_version_id": target["record"]["page_json_version_id"],
            "target_section_id": target["section_id"],
            "target_table_id": target["table_id"],
        }
    if item.get("promoted_summary_control") is True:
        region["promoted_summary_control"] = True
    return region


def _marker_matches(value: Any, aliases: Sequence[str]) -> str | None:
    matches = [alias for alias in aliases if _contains_alias(value, alias)]
    if not matches:
        return None
    maximum = max(map(len, matches))
    winners = sorted(alias for alias in matches if len(alias) == maximum)
    return winners[0] if len(winners) == 1 else None


def _row_declares_structural_role(
    row: Mapping[str, Any], role: str, *, compiled_specs: Mapping[str, Any]
) -> bool:
    """Bind a control total to the structural branch visible on that row.

    A compact source table can place QUALITY, VAMC and provision blocks one
    after another.  Table-wide context is therefore insufficient for an
    anonymous/subtotal control: a later provision subtotal must not inherit a
    QUALITY label from an earlier row.  Consume only the row's exact label and
    hierarchy path here.
    """

    values = [row.get("label_exact"), *(row.get("hierarchy_path_exact") or [])]
    return any(
        _contains_alias(value, alias)
        for value in values
        for alias in compiled_specs["aliases_by_role"][role]
    )


def _trailing_continuation_parent_roles(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
    continuation_table: Mapping[str, Any] | None = None,
) -> list[str]:
    """Return the nearest source-declared group before a page continuation."""

    contexts = _context_roles(section, table, compiled_specs=compiled_specs)
    # Try the literal boundary fragments before falling back to an earlier
    # complete parent path.  Otherwise a valid split caption such as
    # ``... ngày đáo`` + ``hạn`` is shadowed by the last complete debt leaf
    # above it.  Both fragments must be non-empty, neither may independently
    # declare any GROUP role, and their concatenation must declare exactly one
    # role.  This keeps the repair limited to an exact physical-page boundary.
    if continuation_table is not None:
        prior_labels = [
            row.get("label_exact")
            for row in reversed(table.get("rows") or [])
            if type(row) is dict and _normalized(row.get("label_exact"))
        ]
        continuation_labels = [
            row.get("label_exact")
            for row in continuation_table.get("rows") or []
            if type(row) is dict and _normalized(row.get("label_exact"))
        ]
        if prior_labels and continuation_labels:
            fragments = [prior_labels[0], continuation_labels[0]]
            fragment_roles = {
                role
                for fragment in fragments
                for role in _GROUP_ROLES
                if any(
                    _matches_alias(fragment, alias)
                    for alias in compiled_specs["aliases_by_role"][role]
                )
            }
            joined = f"{fragments[0]} {fragments[1]}"
            joined_roles = [
                role
                for role in sorted(_GROUP_ROLES)
                if any(
                    _matches_alias(joined, alias)
                    for alias in compiled_specs["aliases_by_role"][role]
                )
            ]
            if not fragment_roles and len(joined_roles) == 1:
                return joined_roles
    for row in reversed(table.get("rows") or []):
        if type(row) is not dict:
            continue
        direct = [
            role
            for role in sorted(_GROUP_ROLES)
            if any(
                _matches_alias(row.get("label_exact"), alias)
                for alias in compiled_specs["aliases_by_role"][role]
            )
        ]
        if direct:
            return direct
        matched = [
            role
            for role in sorted(_GROUP_ROLES)
            if _role_match_score(
                row,
                role,
                table_context_roles=contexts,
                compiled_specs=compiled_specs,
            )
            is not None
        ]
        if matched:
            return matched
    return []


def _inside_selected_owner_fence(
    item: Mapping[str, Any],
    *,
    active: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    owner_markers: Sequence[Mapping[str, Any]],
    reset_markers: Sequence[Mapping[str, Any]],
    max_continuation_pages: int,
) -> bool:
    """Return whether an unusable table can invalidate the selected family note.

    Explicitly titled investment tables always remain in scope.  A titleless
    continuation is in scope only inside the declared page window around the
    selected components and only when no reset lies between it and the nearest
    selected component.  This prevents a later credit-risk, listing or fair-
    value table from poisoning a complete investment note merely because one
    of its row labels happens to reuse an AFS/HTM alias.
    """

    if not active:
        return True
    position = item["position"]
    if any(
        marker["position"][:2] == position[:2] and marker["position"] <= position
        for marker in owner_markers
    ):
        return True
    page_json = item["record"]["page_json"]
    section = page_json["sections"][int(item["section_id"][1:]) - 1]
    table = section["tables"][int(item["table_id"][1:]) - 1]
    local_headings = [section.get("title_exact"), table.get("title_exact")]
    local_declares_family = any(
        _contains_alias(value, alias)
        for value in local_headings
        for role in _STRUCTURAL_ROLES
        for alias in compiled_specs["aliases_by_role"][role]
    )
    # A numbered local heading starts another explicit note owner.  If it does
    # not itself declare an investment-securities structural role, aliases in
    # its rows (for example a credit-risk provision table) cannot invalidate
    # the selected investment note nearby.  Untitled/"continued" fragments
    # remain eligible for the reset-free continuation rule below.
    if not local_declares_family and any(
        re.match(r"^[0-9]+(?:\s+[0-9]+)*\b", _normalized(value) or "") for value in local_headings
    ):
        return False
    nearest = min(
        active,
        key=lambda candidate: (
            abs(candidate["position"][0] - position[0]),
            candidate["position"],
        ),
    )
    nearest_position = nearest["position"]
    if abs(nearest_position[0] - position[0]) > max_continuation_pages:
        return False
    lower, upper = sorted((position, nearest_position))
    return not any(lower < marker["position"] < upper for marker in reset_markers)


def _item_hit_pair(
    item: Mapping[str, Any], hit: Mapping[str, Any]
) -> tuple[int | None, int | None] | None:
    table = item["table"]
    row_ordinal = hit["row_ordinal"]
    rows = table.get("rows") or []
    money_ordinals = item["classification"]["money_column_ordinals"]
    if not 1 <= row_ordinal <= len(rows) or len(money_ordinals) != 2:
        return None
    values = rows[row_ordinal - 1].get("values_exact")
    if type(values) is not list or any(ordinal > len(values) for ordinal in money_ordinals):
        return None
    try:
        return tuple(
            _source_money(values[ordinal - 1])["coefficient"] for ordinal in money_ordinals
        )
    except ValueError:
        return None


def _neutral_investment_leaf_fingerprint(
    item: Mapping[str, Any], *, branch_prefix: str | None = None
) -> tuple[tuple[str, tuple[int | None, int | None]], ...]:
    fingerprint = []
    for hit in item["classification"]["role_hits"]:
        role = hit["role"]
        if not role.startswith(("AFS_", "HTM_")):
            continue
        if branch_prefix is not None and not role.startswith(branch_prefix + "_"):
            continue
        role_kind = item["compiled_specs"]["child_by_role"].get(role, {}).get("role_kind")
        if role_kind not in {"ADDITIVE_CHILD", "NONADDITIVE_CHILD"}:
            continue
        pair = _item_hit_pair(item, hit)
        if pair is None:
            return ()
        fingerprint.append((role.split("_", 1)[1], pair))
    return tuple(
        sorted(
            fingerprint,
            key=lambda entry: (
                entry[0],
                tuple(
                    (coefficient is None, coefficient if coefficient is not None else 0)
                    for coefficient in entry[1]
                ),
            ),
        )
    )


def _branch_total_pair(
    item: Mapping[str, Any], *, branch_prefix: str
) -> tuple[int | None, int | None] | None:
    pairs = {
        pair
        for hit in item["classification"]["role_hits"]
        if hit["role"] == branch_prefix + "_TOTAL"
        and (pair := _item_hit_pair(item, hit)) is not None
    }
    return next(iter(pairs)) if len(pairs) == 1 else None


def _terminal_total_pair(item: Mapping[str, Any]) -> tuple[int | None, int | None] | None:
    rows = item["table"].get("rows") or []
    if not rows:
        return None
    terminal_ordinal = len(rows)
    terminal = rows[-1]
    if terminal.get("row_kind") not in {"GROUP", "SUBTOTAL", "TOTAL"}:
        return None
    matches = [
        hit for hit in item["classification"]["role_hits"] if hit["row_ordinal"] == terminal_ordinal
    ]
    if len(matches) != 1:
        return None
    return _item_hit_pair(item, matches[0])


def _exact_repeated_detail_view_positions(
    active: Sequence[dict[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> set[tuple[int, int, int]]:
    """Find detail views exactly repeated by one preceding dual-branch summary.

    Some notes first print an AFS/HTM summary with the complete leaf population,
    then repeat each branch in a separate detailed view.  Aggregating both views
    doubles every schema leaf.  Exclude the detailed repetitions only when each
    branch has an exact role-neutral leaf multiset and an exact terminal total;
    partial, reordered-but-different, or extra-row views remain active.
    """

    wrapped = [{**item, "compiled_specs": compiled_specs} for item in active]
    plans = []
    for summary in wrapped:
        if (
            summary["classification"]["component_roles"] != ["AFS", "HTM"]
            or summary["classification"]["source_only_rows"]
        ):
            continue
        selected = []
        for prefix in ("AFS", "HTM"):
            fingerprint = _neutral_investment_leaf_fingerprint(summary, branch_prefix=prefix)
            total_pair = _branch_total_pair(summary, branch_prefix=prefix)
            if len(fingerprint) < 2 or total_pair is None:
                selected = []
                break
            matches = []
            for detail in wrapped:
                if (
                    detail["position"] <= summary["position"]
                    or detail["position"][0] - summary["position"][0] > 2
                    or detail["classification"]["source_only_rows"]
                    or any(
                        role.startswith(("QUALITY_", "VAMC_"))
                        for role in (hit["role"] for hit in detail["classification"]["role_hits"])
                    )
                ):
                    continue
                if (
                    _neutral_investment_leaf_fingerprint(detail) == fingerprint
                    and _terminal_total_pair(detail) == total_pair
                ):
                    matches.append(detail)
            if len(matches) != 1:
                selected = []
                break
            selected.append(matches[0])
        if len(selected) == 2 and selected[0]["position"] != selected[1]["position"]:
            plans.append(selected)
    if len(plans) != 1:
        return set()
    return {tuple(item["position"]) for item in plans[0]}


def _table_is_last_on_selected_page(item: Mapping[str, Any]) -> bool:
    page = item["record"]["page_json"]
    source_position = (int(item["section_id"][1:]), int(item["table_id"][1:]))
    table_positions = [
        (section_ordinal, table_ordinal)
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1)
        if type(section) is dict
        for table_ordinal, table in enumerate(section.get("tables") or [], start=1)
        if type(table) is dict
    ]
    return bool(table_positions) and source_position == max(table_positions)


def _adjacent_single_lane_blank_projection_pairs(
    inventory: Sequence[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Authenticate a one-column blank stub continued by an exact two-lane table."""

    active = [
        item
        for item in inventory
        if item["classification"]["disposition"] == "ACTIVE_SNAPSHOT_COMPONENT"
    ]
    pairs = []
    for source in inventory:
        classification = source["classification"]
        table = source["table"]
        if (
            classification["disposition"] != "DECLARED_ROLE_TABLE_NOT_USABLE"
            or classification["reasons"]
            != ["SNAPSHOT_COMPONENT_REQUIRES_EXACTLY_TWO_MONEY_COLUMNS"]
            or len(classification["money_column_ordinals"]) != 1
            or classification["ambiguous_row_ordinals"]
            or classification["unbound_money_row_ordinals"]
            or classification["source_only_rows"]
            or not classification["role_hits"]
            or table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            or not _table_is_last_on_selected_page(source)
        ):
            continue
        money_ordinal = classification["money_column_ordinals"][0]
        rows = table.get("rows") or []
        if any(
            hit["row_ordinal"] > len(rows)
            or type(rows[hit["row_ordinal"] - 1].get("values_exact")) is not list
            or money_ordinal > len(rows[hit["row_ordinal"] - 1]["values_exact"])
            or rows[hit["row_ordinal"] - 1]["values_exact"][money_ordinal - 1] is not None
            for hit in classification["role_hits"]
        ):
            continue
        candidates = [
            target
            for target in active
            if target["record"]["selected_page_ordinal"]
            == source["record"]["selected_page_ordinal"] + 1
            and target["record"]["physical_page"] == source["record"]["physical_page"] + 1
            and target["position"][1:] == [1, 1]
            and target["table"].get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
            and target["classification"]["component_roles"] == classification["component_roles"]
            and len(target["classification"]["money_column_ordinals"]) == 2
            and any(hit["role"].endswith("_TOTAL") for hit in target["classification"]["role_hits"])
        ]
        if len(candidates) == 1:
            pairs.append((source, candidates[0]))
    return pairs


def coalesce_gemini_json_investment_securities_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select every usable component in one generic owner/reset interval."""

    pages = _page_record_axis(page_records)
    inventory = []
    reset_markers = []
    owner_markers = []
    previous_table_entry = None
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
                continuation_parent_roles = []
                if (
                    table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                    and previous_table_entry is not None
                    and previous_table_entry["table"].get("continuation")
                    == "CONTINUES_ON_NEXT_PAGE"
                    and record["physical_page"]
                    == previous_table_entry["record"]["physical_page"] + 1
                    and record["selected_page_ordinal"]
                    == previous_table_entry["record"]["selected_page_ordinal"] + 1
                ):
                    continuation_parent_roles = _trailing_continuation_parent_roles(
                        previous_table_entry["section"],
                        previous_table_entry["table"],
                        compiled_specs=compiled_specs,
                        continuation_table=table,
                    )
                classification = classify_gemini_json_investment_securities_table_v1(
                    record["page_json"],
                    section,
                    table,
                    compiled_specs=compiled_specs,
                    continuation_parent_roles=continuation_parent_roles,
                )
                section_position = position[:2] + [0]
                section_owner_qualified = (
                    any(marker["position"] == section_position for marker in owner_markers)
                    and not any(
                        marker["position"] == section_position for marker in reset_markers
                    )
                    and table_ordinal == 1
                    and not _normalized(table.get("title_exact"))
                )
                table_owner_qualified = any(
                    marker["position"] == position for marker in owner_markers
                )
                adjacent_owner_qualified = bool(
                    previous_table_entry is not None
                    and previous_table_entry["classification"]["role_hits"]
                    and not _normalized(table.get("title_exact"))
                    and not any(
                        previous_table_entry["position"]
                        < marker["position"]
                        <= position
                        for marker in reset_markers
                    )
                    and (
                        (
                            previous_table_entry["record"]["page_json_version_id"]
                            == record["page_json_version_id"]
                            and previous_table_entry["section_id"] == section_id
                            and previous_table_entry["table_ordinal"] + 1 == table_ordinal
                        )
                        or (
                            table.get("continuation") == "CONTINUES_FROM_PREVIOUS_PAGE"
                            and previous_table_entry["table"].get("continuation")
                            == "CONTINUES_ON_NEXT_PAGE"
                            and record["selected_page_ordinal"]
                            == previous_table_entry["record"]["selected_page_ordinal"] + 1
                        )
                    )
                )
                # Do not let an owner marker on one titled table leak across a
                # flattened generic page section and veto every later financial
                # table.  Zero-hit tables are inventory only under a direct
                # section/table owner or an exact titleless adjacency/continuation.
                local_owner_qualified = (
                    section_owner_qualified
                    or table_owner_qualified
                    or adjacent_owner_qualified
                )
                if classification["role_hits"] or (
                    local_owner_qualified
                    and classification["unbound_money_row_ordinals"]
                ):
                    inventory.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table": table,
                            "table_id": table_id,
                        }
                    )
                previous_table_entry = {
                    "classification": classification,
                    "record": record,
                    "position": position,
                    "section": section,
                    "section_id": section_id,
                    "table": table,
                    "table_ordinal": table_ordinal,
                }
    blank_projection_pairs = _adjacent_single_lane_blank_projection_pairs(inventory)
    for source, target in blank_projection_pairs:
        source["classification"]["disposition"] = (
            "PROJECTED_ADJACENT_CONTINUATION_SINGLE_LANE_BLANK_ROLE"
        )
        source["adjacent_blank_projection_target"] = target
    active = [
        item
        for item in inventory
        if item["classification"]["disposition"] == "ACTIVE_SNAPSHOT_COMPONENT"
    ]
    repeated_detail_positions = _exact_repeated_detail_view_positions(
        active, compiled_specs=compiled_specs
    )
    if repeated_detail_positions:
        for item in active:
            if tuple(item["position"]) in repeated_detail_positions:
                item["classification"]["disposition"] = "EXCLUDED_EXACT_REPEATED_DETAIL_VIEW"
                item["classification"]["exact_repeated_view_receipt"] = {
                    "rule": "EXACT_ROLE_NEUTRAL_LEAF_MULTISET_AND_TERMINAL_BRANCH_TOTAL",
                }
        active = [
            item
            for item in active
            if item["classification"]["disposition"] == "ACTIVE_SNAPSHOT_COMPONENT"
        ]
    reasons = []
    investment_core = [
        item
        for item in active
        if any(
            hit["role"].startswith(("AFS_", "HTM_")) and "_PROVISION" not in hit["role"]
            for hit in item["classification"]["role_hits"]
        )
    ]
    if not investment_core:
        if inventory:
            reasons.append("INVESTMENT_SECURITIES_DETAIL_COMPONENT_NOT_RESOLVED")
    max_continuation_pages = compiled_specs["topology"]["limits"]["max_continuation_pages"]
    summary_controls = []
    if investment_core:
        for item in inventory:
            if (
                item["classification"]["disposition"] == "EXCLUDED_SUMMARY_ONLY_CONTROL"
                and item["classification"]["component_roles"]
                and _inside_selected_owner_fence(
                    item,
                    active=active,
                    compiled_specs=compiled_specs,
                    owner_markers=owner_markers,
                    reset_markers=reset_markers,
                    max_continuation_pages=max_continuation_pages,
                )
            ):
                item["promoted_summary_control"] = True
                summary_controls.append(item)
    selected_components = [*active, *summary_controls]
    if selected_components:
        first = min(item["position"] for item in selected_components)
        last = max(item["position"] for item in selected_components)
        if (
            last[0] - first[0]
            > max_continuation_pages
        ):
            reasons.append("INVESTMENT_SECURITIES_COMPONENT_SPAN_EXCEEDS_DECLARED_BOUND")
        for item in selected_components:
            prior_resets = [
                marker for marker in reset_markers if marker["position"] < item["position"]
            ]
            if not prior_resets:
                continue
            latest_reset = max(prior_resets, key=lambda marker: marker["position"])
            local_owners = [
                marker
                for marker in owner_markers
                if latest_reset["position"] <= marker["position"] <= item["position"]
            ]
            if not local_owners:
                reasons.append("COMPONENT_CROSSES_RESET_WITHOUT_LOCAL_OWNER")
    selected_keys = {
        (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        for item in selected_components
    }
    projected_keys = {
        (source["record"]["page_json_version_id"], source["section_id"], source["table_id"])
        for source, _target in blank_projection_pairs
    }
    excluded_outside_fence = []
    declared_inventory = []
    for item in inventory:
        key = (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        disposition = item["classification"]["disposition"]
        if key in projected_keys:
            disposition = "PROJECTED_ADJACENT_CONTINUATION_SINGLE_LANE_BLANK_ROLE"
        elif key in selected_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif disposition in {
            "DECLARED_ROLE_TABLE_NOT_USABLE",
            "NO_DECLARED_ROLE_POPULATION",
        }:
            if _inside_selected_owner_fence(
                item,
                active=active,
                compiled_specs=compiled_specs,
                owner_markers=owner_markers,
                reset_markers=reset_markers,
                max_continuation_pages=max_continuation_pages,
            ):
                reasons.append(
                    "UNUSABLE_DECLARED_ROLE_TABLE_IN_SELECTED_DOCUMENT"
                    if disposition == "DECLARED_ROLE_TABLE_NOT_USABLE"
                    else "UNRECOGNIZED_OWNER_QUALIFIED_MONEY_TABLE_IN_SELECTED_DOCUMENT"
                )
            else:
                disposition = "EXCLUDED_OUTSIDE_SELECTED_OWNER_FENCE"
                excluded_outside_fence.append(
                    {
                        "page_json_version_id": item["record"]["page_json_version_id"],
                        "physical_page": item["record"]["physical_page"],
                        "position": item["position"],
                        "section_id": item["section_id"],
                        "table_id": item["table_id"],
                    }
                )
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
    selected_items = sorted(
        [*selected_components, *(source for source, _target in blank_projection_pairs)],
        key=lambda item: item["position"],
    )
    regions = [_region(item, ordinal) for ordinal, item in enumerate(selected_items, start=1)]
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
        READY
        if regions and investment_core and not reasons
        else UNRESOLVED
        if inventory
        else NOT_OBSERVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_role_table_inventory": declared_inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_fence_receipt": {
            "excluded_outside_fence": excluded_outside_fence,
            "max_continuation_pages": max_continuation_pages,
            "rule": (
                "EXPLICIT_OWNER_OR_RESET_FREE_DECLARED_CONTINUATION_WINDOW_AROUND_"
                "SELECTED_COMPONENTS"
            ),
        },
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
    base_fields = {
        "component_roles",
        "continuation_parent_roles",
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
            or frozenset(raw)
            not in {
                frozenset(base_fields),
                frozenset(base_fields | {"single_lane_blank_projection"}),
                frozenset(base_fields | {"promoted_summary_control"}),
            }
            or type(raw.get("component_roles")) is not list
            or not raw["component_roles"]
            or raw["component_roles"] != sorted(set(raw["component_roles"]))
            or any(role not in {"AFS", "HTM", "QUALITY", "VAMC"} for role in raw["component_roles"])
            or type(raw.get("continuation_parent_roles")) is not list
            or raw["continuation_parent_roles"] != sorted(set(raw["continuation_parent_roles"]))
            or any(role not in _GROUP_ROLES for role in raw["continuation_parent_roles"])
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
        if raw.get("promoted_summary_control") not in {None, True}:
            raise _error("investment-securities promoted summary control is invalid")
        projection = raw.get("single_lane_blank_projection")
        if projection is not None and (
            type(projection) is not dict
            or set(projection)
            != {
                "rule",
                "source_money_column_ordinal",
                "target_page_json_version_id",
                "target_section_id",
                "target_table_id",
            }
            or projection.get("rule")
            != (
                "ADJACENT_PAGE_CONTINUATION_SINGLE_SOURCE_BLANK_LANE_PROJECTED_"
                "TO_EXACT_TARGET_TWO_PERIOD_AXIS"
            )
            or type(projection.get("source_money_column_ordinal")) is not int
            or projection["source_money_column_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(projection.get("target_page_json_version_id", "")) is None
            or _SECTION_ID.fullmatch(projection.get("target_section_id", "")) is None
            or _TABLE_ID.fullmatch(projection.get("target_table_id", "")) is None
        ):
            raise _error("investment-securities blank-lane projection is invalid")
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
    for index, region in enumerate(checked):
        projection = region.get("single_lane_blank_projection")
        if projection is None:
            continue
        if index + 1 >= len(checked):
            raise _error("investment-securities blank-lane projection target is absent")
        target = checked[index + 1]
        if (
            projection["target_page_json_version_id"] != target["page_json_version_id"]
            or projection["target_section_id"] != target["section_id"]
            or projection["target_table_id"] != target["table_id"]
            or target["selected_page_ordinal"] != region["selected_page_ordinal"] + 1
            or target["physical_page"] != region["physical_page"] + 1
            or target["component_roles"] != region["component_roles"]
        ):
            raise _error("investment-securities blank-lane projection target drifted")
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
        # ``ktCap`` is a sealed source-reader serialization artifact observed
        # where the PDF visibly contains a dash.  Admit only the exact marker
        # (optionally missing one surrounding dash), preserve the raw string,
        # and still require an independent subtotal/total equation before it
        # can become a mapped zero.  Arbitrary Latin annotations remain invalid.
        if re.fullmatch(r"-?ktcap-?", body, flags=re.IGNORECASE):
            return {
                "coefficient": 0,
                "source_text": value,
                "state": "KTCAP_SERIALIZATION_ARTIFACT_ZERO_IF_EQUATION_EXACT",
            }
        # Some sealed Gemini pages attach a non-Latin continuation annotation
        # to a visible dash glyph (for example ``-接着-`` or ``-单``).  Preserve
        # that raw evidence as a conditional zero; it becomes usable only when
        # an independent complete accounting equation proves the lane exactly.
        if (
            len(body) >= 2
            and (body[0] in dashes or body[-1] in dashes)
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
    def aggregate_lane(lane: int) -> dict[str, Any]:
        coefficients = [record["cells"][lane]["coefficient"] for record in records]
        if any(coefficient is None for coefficient in coefficients):
            return {
                "coefficient": None,
                "source_text": None,
                "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
            }
        return {
            "coefficient": sum(coefficients),
            "source_text": None,
            "state": "DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
        }

    return _record(
        role,
        [aggregate_lane(lane) for lane in range(2)],
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
        complete_records := [
            record
            for record in records
            if all(type(value) is int for value in _coefficients(record))
        ]
    ) and len({tuple(_coefficients(record)) for record in complete_records}) == 1 and not any(
        any(
            value is not None and value != _coefficients(complete_records[0])[lane]
            for lane, value in enumerate(_coefficients(record))
        )
        for record in records
    ):
        selected = complete_records[0]
        # One fully observed presentation can corroborate the same role in a
        # second presentation whose blank lanes carry no observation.  Fill
        # only from that explicit complete row; complementary partial rows or
        # conflicting observations are never combined/backsolved.
        state = "CORROBORATED_COMPLETE_SOURCE_ROW_WITH_COMPATIBLE_PARTIAL_PRESENTATIONS"
    elif (
        "PROVISION" in role
        and all(
            type(value) is int
            for record in records
            for value in _coefficients(record)
        )
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
        stable_unique_source_refs_v1([ref for record in records for ref in record["source_refs"]]),
        state,
    )


def _coefficients(record: Mapping[str, Any]) -> list[int | None]:
    return [cell["coefficient"] for cell in record["cells"]]


def _equation(
    *,
    equation_kind: str,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    multipliers: Sequence[int] | None = None,
    canonical_unit: str | None = None,
) -> dict[str, Any]:
    weights = list(multipliers) if multipliers is not None else [1] * len(components)
    result_values = _coefficients(result)
    sums: list[int | None] = []
    deltas: list[int | None] = []
    lane_statuses = []
    for lane, result_value in enumerate(result_values):
        component_values = [record["cells"][lane]["coefficient"] for record in components]
        component_sum = (
            None
            if any(value is None for value in component_values)
            else sum(
                weight * value
                for value, weight in zip(component_values, weights, strict=True)
            )
        )
        sums.append(component_sum)
        if component_sum is None or result_value is None:
            deltas.append(None)
            lane_statuses.append("UNOBSERVED_SOURCE_LANE")
            continue
        delta = component_sum - result_value
        deltas.append(delta)
        lane_statuses.append("EXACT" if delta == 0 else "MISMATCH")
    precision_receipt = None
    rounded_component_counts = [
        sum(
            type(component["cells"][lane]["coefficient"]) is int
            and component["cells"][lane]["coefficient"] != 0
            for component in components
        )
        for lane in range(len(result_values))
    ]
    rounded_lanes = [
        lane
        for lane, (lane_status, delta) in enumerate(zip(lane_statuses, deltas, strict=True))
        if lane_status == "MISMATCH"
        and canonical_unit == "MILLION_VND"
        and type(delta) is int
        and abs(delta) <= 1
        and rounded_component_counts[lane] >= 2
    ]
    for lane in rounded_lanes:
        lane_statuses[lane] = "EXACT_WITHIN_ONE_MILLION_VND_ROUNDING"
    if all(lane_status == "EXACT" for lane_status in lane_statuses):
        status = "EXACT"
    elif any(lane_status == "MISMATCH" for lane_status in lane_statuses):
        status = "MISMATCH"
    elif all(lane_status == "UNOBSERVED_SOURCE_LANE" for lane_status in lane_statuses):
        status = "NO_COMPLETE_OBSERVED_LANE"
    elif "UNOBSERVED_SOURCE_LANE" in lane_statuses:
        status = (
            "EXACT_OBSERVED_LANES_WITH_BLANK_SOURCE_LANES_AND_"
            "WITHIN_ONE_MILLION_VND_ROUNDING"
            if rounded_lanes
            else "EXACT_OBSERVED_LANES_WITH_BLANK_SOURCE_LANES"
        )
    else:
        status = "EXACT_WITHIN_ONE_MILLION_VND_ROUNDING"
    if rounded_lanes:
        precision_receipt = {
            "canonical_unit": canonical_unit,
            "maximum_absolute_delta": 1,
            "observed_deltas": deltas,
            "rule": "PRINTED_MILLION_VND_COMPONENTS_MAY_DIFFER_FROM_PRINTED_TOTAL_BY_ONE",
        }
    material = {
        "component_roles": [record["role"] for record in components],
        "component_source_refs": [
            canonical_clone_v1(record["source_refs"]) for record in components
        ],
        "component_sums": sums,
        "equation_kind": equation_kind,
        "lane_statuses": lane_statuses,
        "multipliers": weights,
        "result_coefficients": result_values,
        "result_role": result["role"],
        "result_source_refs": canonical_clone_v1(result["source_refs"]),
        "status": status,
    }
    if precision_receipt is not None:
        material["precision_receipt"] = precision_receipt
    return {**material, "equation_id": "gjfisev1:equation:" + canonical_json_sha256_v1(material)}


def _equation_closes(equation: Mapping[str, Any]) -> bool:
    return equation.get("status") in {
        "EXACT",
        "EXACT_OBSERVED_LANES_WITH_BLANK_SOURCE_LANES",
        "EXACT_OBSERVED_LANES_WITH_BLANK_SOURCE_LANES_AND_WITHIN_ONE_MILLION_VND_ROUNDING",
        "EXACT_WITHIN_ONE_MILLION_VND_ROUNDING",
    }


def _best_closing_equations(
    equations: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Prefer byte-exact closures; use declared rounded closure only as fallback."""

    exact = [equation for equation in equations if equation.get("status") == "EXACT"]
    return exact or [equation for equation in equations if _equation_closes(equation)]


def _source_record_position(record: Mapping[str, Any]) -> tuple[int, int] | None:
    refs = record.get("source_refs")
    if type(refs) is not list or len(refs) != 1 or type(refs[0]) is not dict:
        return None
    ref = refs[0]
    locator = ref.get("locator")
    if (
        type(locator) is not dict
        or type(locator.get("fragment_ordinal")) is not int
        or type(ref.get("row_ordinal")) is not int
    ):
        return None
    return locator["fragment_ordinal"], ref["row_ordinal"]


def _select_unscoped_closing_equation(
    equations: Sequence[Mapping[str, Any]], *, terminal_control: bool
) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    """Resolve coincident exact frontiers without licensing arbitrary proof.

    Nonterminal totals are local controls and therefore use the narrowest
    closing frontier.  Only the final value-bearing TOTAL of the final selected
    region may use the widest closing frontier, which represents the printed
    family total.  Fully blank leaves have already been removed before this
    resolver, so a comprehensive zero-valued frontier can never manufacture a
    source observation for them.
    """

    closing = _best_closing_equations(equations)
    if not closing:
        return None, {
            "candidate_equation_count": 0,
            "disposition": "NO_CLOSING_FAMILY_FRONTIER",
            "terminal_control": terminal_control,
        }
    widths = [len(set(equation["component_roles"])) for equation in closing]
    selected_width = (max if terminal_control else min)(widths)
    finalists = [
        equation
        for equation, width in zip(closing, widths, strict=True)
        if width == selected_width
    ]
    selected = finalists[0]
    return selected, {
        "candidate_equation_count": len(closing),
        "disposition": (
            "TERMINAL_STRUCTURALLY_COMPREHENSIVE_EXACT_FRONTIER"
            if terminal_control
            else "NONTERMINAL_NARROW_EXACT_FRONTIER"
        ),
        "selected_component_role_count": selected_width,
        "selected_equation_id": selected["equation_id"],
        "terminal_control": terminal_control,
    }


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
        and "VAMC" not in ref["locator"].get("component_roles", [])
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


def _record_has_explicit_role_path(
    record: Mapping[str, Any], role: str, *, compiled_specs: Mapping[str, Any]
) -> bool:
    """Require the source row/path itself to name a role, without table fallback."""

    return any(
        _path_has_role(
            ref.get("hierarchy_path_exact"),
            role,
            compiled_specs=compiled_specs,
            label_exact=ref.get("label_exact"),
            table_context_roles=set(),
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
        additive_siblings = [
            role for role in _parent_children(parent) if role != "AFS_DEBT_GOVERNMENT_GUARANTEED"
        ]
        subset_visible = subset_visible or any(
            _matches_alias(value, alias)
            for ref in guaranteed["source_refs"]
            for value in ref.get("hierarchy_path_exact") or []
            if type(value) is str and _normalized(value) != _normalized(ref.get("label_exact"))
            for sibling in additive_siblings
            for alias in compiled_specs["aliases_by_role"][sibling]
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
    document_unit_context = _investment_document_unit_context_axis(
        page_json_by_version, region_axis, compiled_specs=compiled_specs
    )
    document_period_context = _investment_document_period_context_axis(
        page_json_by_version, region_axis, compiled_specs=compiled_specs
    )
    raw_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    table_receipts = []
    reasons = []
    period_signatures = []
    units = []
    for region_index, region in enumerate(region_axis):
        page_json = page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("investment-securities selected page JSON is absent")
        section, table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        classification = classify_gemini_json_investment_securities_table_v1(
            page_json,
            section,
            table,
            compiled_specs=compiled_specs,
            continuation_parent_roles=region["continuation_parent_roles"],
        )
        blank_projection = region.get("single_lane_blank_projection")
        projection_receipt = None
        serialized_header_projection = None
        if blank_projection is None:
            expected_disposition = (
                "EXCLUDED_SUMMARY_ONLY_CONTROL"
                if region.get("promoted_summary_control") is True
                else "ACTIVE_SNAPSHOT_COMPONENT"
            )
            if (
                classification["disposition"] != expected_disposition
                or classification["component_roles"] != region["component_roles"]
                or classification["reasons"]
            ):
                raise _error("investment-securities source fragment classification drifted")
            projected_table = _table_with_investment_money_axis(
                table, classification["money_column_ordinals"]
            )
            serialized_header_projection = projected_table.get(
                "investment_serialized_header_linebreak_projection"
            )
            period_axis = _investment_period_axis(
                projected_table, document_period_context=document_period_context
            )
            unit_axis = _unit_axis(
                projected_table,
                compiled_specs=compiled_specs,
                document_unit_context=document_unit_context,
            )
        else:
            if (
                classification["disposition"] != "DECLARED_ROLE_TABLE_NOT_USABLE"
                or classification["component_roles"] != region["component_roles"]
                or classification["reasons"]
                != ["SNAPSHOT_COMPONENT_REQUIRES_EXACTLY_TWO_MONEY_COLUMNS"]
                or classification["money_column_ordinals"]
                != [blank_projection["source_money_column_ordinal"]]
                or classification["ambiguous_row_ordinals"]
                or classification["unbound_money_row_ordinals"]
                or classification["source_only_rows"]
                or table.get("continuation") != "CONTINUES_ON_NEXT_PAGE"
            ):
                raise _error("investment-securities blank-lane source projection drifted")
            target_region = region_axis[region_index + 1]
            target_page = page_json_by_version.get(target_region["page_json_version_id"])
            if type(target_page) is not dict:
                raise _error("investment-securities blank-lane target page is absent")
            target_section, target_table = _source_table(
                target_page,
                section_id=target_region["section_id"],
                table_id=target_region["table_id"],
            )
            target_classification = classify_gemini_json_investment_securities_table_v1(
                target_page,
                target_section,
                target_table,
                compiled_specs=compiled_specs,
                continuation_parent_roles=target_region["continuation_parent_roles"],
            )
            if (
                target_classification["disposition"] != "ACTIVE_SNAPSHOT_COMPONENT"
                or target_classification["component_roles"] != region["component_roles"]
                or target_classification["reasons"]
                or len(target_classification["money_column_ordinals"]) != 2
                or target_table.get("continuation") != "CONTINUES_FROM_PREVIOUS_PAGE"
            ):
                raise _error("investment-securities blank-lane target projection drifted")
            target_projected_table = _table_with_investment_money_axis(
                target_table, target_classification["money_column_ordinals"]
            )
            serialized_header_projection = target_projected_table.get(
                "investment_serialized_header_linebreak_projection"
            )
            period_axis = _investment_period_axis(
                target_projected_table, document_period_context=document_period_context
            )
            unit_axis = _unit_axis(
                target_projected_table,
                compiled_specs=compiled_specs,
                document_unit_context=document_unit_context,
            )
            projection_receipt = {
                "source_money_column_ordinal": blank_projection["source_money_column_ordinal"],
                "target_money_column_ordinals": target_classification["money_column_ordinals"],
                "target_region": canonical_clone_v1(target_region),
                "rule": blank_projection["rule"],
            }
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
                if blank_projection is None:
                    cells = [_source_money(values[ordinal - 1]) for ordinal in money_ordinals]
                else:
                    source_value = values[money_ordinals[0] - 1]
                    if source_value is not None:
                        raise ValueError
                    cells = [
                        {
                            "coefficient": 0,
                            "source_text": source_value,
                            "state": (
                                "ADJACENT_CONTINUATION_SINGLE_LANE_BLANK_ZERO_IF_EQUATION_EXACT"
                            ),
                        }
                        for _lane in range(2)
                    ]
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
        table_receipt = {
            "classification": classification,
            "period_axis": period_axis,
            "region": canonical_clone_v1(region),
            "unit_axis": unit_axis,
        }
        if projection_receipt is not None:
            table_receipt["single_lane_blank_projection_receipt"] = projection_receipt
        if serialized_header_projection is not None:
            table_receipt["serialized_header_linebreak_projection_receipt"] = canonical_clone_v1(
                serialized_header_projection
            )
        table_receipts.append(table_receipt)
    if (
        period_signatures
        and len({canonical_json_sha256_v1(item) for item in period_signatures}) != 1
    ):
        reasons.append("COMPONENT_PERIOD_AXES_DIFFER")
    resolved_units = set(units)
    if len(resolved_units) > 1:
        reasons.append("COMPONENT_MONEY_UNITS_DIFFER")
    candidate_unit = next(iter(resolved_units)) if len(resolved_units) == 1 else None

    def candidate_equation(**kwargs: Any) -> dict[str, Any]:
        return _equation(canonical_unit=candidate_unit, **kwargs)

    source_visible_blank_value_omissions = []
    for role, source_records in list(raw_records.items()):
        observed_records = []
        for source_record in source_records:
            blank_lanes = [
                lane
                for lane, cell in enumerate(source_record["cells"], start=1)
                if cell.get("source_text") is None
            ]
            if not blank_lanes:
                observed_records.append(source_record)
                continue
            all_blank = len(blank_lanes) == len(source_record["cells"])
            # A blank source cell is an absence of a numeric observation, not
            # a printed zero.  Keep a partially observed role with an explicit
            # null lane, but remove an all-blank role before any equation can
            # manufacture a mapped zero.
            source_visible_blank_value_omissions.append(
                {
                    "blank_lanes": blank_lanes,
                    "disposition": (
                        "SOURCE_VISIBLE_ALL_BLANK_NO_VALUE_OBSERVATION"
                        if all_blank
                        else "SOURCE_VISIBLE_PARTIAL_BLANK_LANE_NO_VALUE_OBSERVATION"
                    ),
                    "role": role,
                    "source_refs": canonical_clone_v1(source_record["source_refs"]),
                }
            )
            if all_blank:
                continue
            for lane in blank_lanes:
                source_record["cells"][lane - 1] = {
                    "coefficient": None,
                    "source_text": None,
                    "state": "BLANK_SOURCE_CELL",
                }
            observed_records.append(source_record)
        raw_records[role] = observed_records

    promoted_summary_equations = []
    promoted_summary_resolution_receipts = []
    promoted_summary_records: dict[
        tuple[str, str, str], list[tuple[str, dict[str, Any]]]
    ] = defaultdict(list)
    for role, source_records in raw_records.items():
        for source_record in source_records:
            refs = source_record["source_refs"]
            if len(refs) != 1:
                continue
            locator = refs[0]["locator"]
            if locator.get("promoted_summary_control") is not True:
                continue
            promoted_summary_records[
                (
                    locator["page_json_version_id"],
                    locator["section_id"],
                    locator["table_id"],
                )
            ].append((role, source_record))

    resolved_promoted_summary_record_ids = set()
    for table_identity, role_records in sorted(promoted_summary_records.items()):
        ordered = sorted(role_records, key=lambda item: item[1]["source_refs"][0]["row_ordinal"])
        row_ordinals = [record["source_refs"][0]["row_ordinal"] for _role, record in ordered]
        if (
            len(ordered) < 2
            or len(set(row_ordinals)) != len(row_ordinals)
            or ordered[-1][1]["source_refs"][0].get("row_kind") != "TOTAL"
            or any(
                record["source_refs"][0].get("row_kind") == "TOTAL"
                for _role, record in ordered[:-1]
            )
        ):
            continue
        detail_records = [
            _record(
                "SOURCE_ONLY_PROMOTED_SUMMARY_DETAIL:" + role,
                record["cells"],
                record["source_refs"],
                "SOURCE_ONLY_PROMOTED_SUMMARY_DETAIL",
            )
            for role, record in ordered[:-1]
        ]
        terminal_record = _record(
            "PROMOTED_SUMMARY_TOTAL_CONTROL",
            ordered[-1][1]["cells"],
            ordered[-1][1]["source_refs"],
            "PROMOTED_SUMMARY_TOTAL_CONTROL",
        )
        variants = [
            candidate_equation(
                equation_kind=(
                    "EXACT_PROMOTED_SUMMARY_DETAIL_ROWS_EQUAL_TERMINAL_CONTROL_" + kind
                ),
                components=detail_records,
                result=terminal_record,
                multipliers=[weight] * len(detail_records),
            )
            for kind, weight in (
                ("SOURCE_SIGNED", 1),
                ("ABSOLUTE_PRESENTATION", -1),
            )
        ]
        closing = _best_closing_equations(variants)
        if not closing:
            continue
        equation = closing[0]
        promoted_summary_equations.append(equation)
        resolved_promoted_summary_record_ids.update(id(record) for _role, record in ordered)

        quality_role = None
        detail_roles = [role for role, _record_value in ordered[:-1]]
        if len(detail_roles) == 2 and set(detail_roles) == {"AFS_TOTAL", "HTM_TOTAL"}:
            quality_matches = []
            for candidate_role in (
                "QUALITY_STANDARD",
                "QUALITY_WATCH",
                "QUALITY_SUBSTANDARD",
                "QUALITY_DOUBTFUL",
                "QUALITY_LOSS",
            ):
                if all(
                    any(
                        _matches_alias(value, alias)
                        for value in record["source_refs"][0].get("hierarchy_path_exact") or []
                        if type(value) is str
                        for alias in compiled_specs["aliases_by_role"][candidate_role]
                    )
                    for _role, record in ordered[:-1]
                ):
                    quality_matches.append(candidate_role)
            if len(quality_matches) == 1:
                quality_role = quality_matches[0]
                raw_records[quality_role].append(
                    _record(
                        quality_role,
                        ordered[-1][1]["cells"],
                        ordered[-1][1]["source_refs"],
                        "SOURCE_TOTAL_RECLASSIFIED_FROM_EXACT_AFS_HTM_QUALITY_SLICES",
                    )
                )
        promoted_summary_resolution_receipts.append(
            {
                "detail_source_roles": detail_roles,
                "disposition": (
                    "EXACT_QUALITY_ROLE_TOTAL_FROM_AFS_HTM_SLICE_DECOMPOSITION"
                    if quality_role is not None
                    else "SOURCE_ONLY_EXACT_INTERNAL_PROMOTED_SUMMARY_DECOMPOSITION"
                ),
                "equation_id": equation["equation_id"],
                "quality_role": quality_role,
                "table_identity": list(table_identity),
                "terminal_source_role": ordered[-1][0],
            }
        )
    for role, source_records in list(raw_records.items()):
        raw_records[role] = [
            record
            for record in source_records
            if id(record) not in resolved_promoted_summary_record_ids
        ]

    raw_total_records = {role: raw_records.pop(role, []) for role in ("AFS_TOTAL", "HTM_TOTAL")}
    raw_control_records = {
        role: raw_records.pop(role, []) for role in sorted(_SOURCE_CONTROL_ROLES)
    }
    source_row_reclassifications = []
    for prefix in ("AFS", "HTM"):
        provision_role = f"{prefix}_PROVISION"
        provision_rows = raw_records.get(provision_role, [])
        if len(provision_rows) < 2:
            continue

        def collapsed_raw_role(role: str) -> dict[str, Any] | None:
            values = raw_records.get(role, [])
            if not values:
                return None
            return _corroborate_identical(role, values) or _aggregate(role, values)

        debt_children = [
            record
            for role in _parent_children(f"{prefix}_DEBT")
            if (record := collapsed_raw_role(role)) is not None
        ]
        provision_children = [
            record
            for role in _parent_children(provision_role)
            if (record := collapsed_raw_role(role)) is not None
        ]
        if len(debt_children) < 2 or not provision_children:
            continue
        gross_candidates = [
            (row, equation)
            for row in provision_rows
            if (
                equation := _equation(
                    equation_kind=(
                        "EXACT_SOURCE_LABEL_SHIFTED_PROVISION_ROW_IS_PRECEDING_DEBT_SUBTOTAL"
                    ),
                    components=debt_children,
                    result=row,
                )
            )["status"]
            == "EXACT"
        ]
        if len(gross_candidates) != 1:
            continue
        gross_row, gross_equation = gross_candidates[0]
        actual_candidates = []
        for row in provision_rows:
            if row is gross_row:
                continue
            variants = [
                _equation(
                    equation_kind=(
                        "EXACT_REMAINING_PROVISION_ROW_EQUALS_VISIBLE_PROVISION_CHILDREN"
                    ),
                    components=provision_children,
                    result=row,
                    multipliers=[weight] * len(provision_children),
                )
                for weight in (1, -1)
            ]
            exact_variants = [equation for equation in variants if equation["status"] == "EXACT"]
            if exact_variants:
                actual_candidates.append((row, exact_variants[0]))
        if len(actual_candidates) != 1:
            continue
        actual_row, provision_equation = actual_candidates[0]
        raw_records[provision_role] = [actual_row]
        raw_records[f"{prefix}_DEBT"].append(
            _record(
                f"{prefix}_DEBT",
                gross_row["cells"],
                gross_row["source_refs"],
                "SOURCE_ROW_RECLASSIFIED_BY_EXACT_DEBT_AND_PROVISION_FRONTIERS",
            )
        )
        source_row_reclassifications.append(
            {
                "from_role": provision_role,
                "gross_debt_equation": gross_equation,
                "provision_equation": provision_equation,
                "rule": "UNIQUE_EXACT_PRECEDING_DEBT_SUBTOTAL_AND_REMAINING_PROVISION_PARENT",
                "to_role": f"{prefix}_DEBT",
            }
        )
    records = {}
    for role, values in raw_records.items():
        if not values:
            continue
        # A source may print the same semantic group both as a labelled group
        # row and as an immediately following blank-labelled subtotal.  Equal
        # observations corroborate one value; distinct rows remain additive
        # populations.  Never double-count byte-distinct source receipts merely
        # because Gemini preserved both structural rows.
        corroborated = _corroborate_identical(role, values)
        records[role] = corroborated if corroborated is not None else _aggregate(role, values)
    equations = promoted_summary_equations

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
        equation = candidate_equation(
            equation_kind="EXACT_VISIBLE_QUALITY_ROWS_EQUAL_SOURCE_TOTAL",
            components=quality_records,
            result=control,
        )
        equations.append(equation)
        if not _equation_closes(equation):
            reasons.append("QUALITY_VISIBLE_TOTAL_DOES_NOT_CLOSE_ROLE_FRONTIER")

    vamc_records = [
        records[role] for role in ("VAMC_FACE_VALUE", "VAMC_PROVISION") if role in records
    ]
    broader_vamc_controls = []
    for control in raw_control_records["VAMC_NET_TOTAL_CONTROL"]:
        variants = [
            candidate_equation(
                equation_kind="EXACT_VISIBLE_VAMC_NET_WITH_SOURCE_SIGNED_PROVISION",
                components=vamc_records,
                result=control,
            )
        ]
        if len(vamc_records) == 2:
            variants.append(
                candidate_equation(
                    equation_kind="EXACT_VISIBLE_VAMC_NET_LESS_POSITIVE_PROVISION",
                    components=vamc_records,
                    result=control,
                    multipliers=[1, -1],
                )
            )
        exact_variants = _best_closing_equations(variants)
        if exact_variants:
            equations.append(exact_variants[0])
        else:
            # A VAMC-only continuation table can end with both its own net
            # subtotal and a broader investment-securities total.  Defer a
            # non-VAMC closure to the generic all-family frontier resolver;
            # it remains unresolved there unless a complete exact equation
            # independently identifies the broader population.
            broader_vamc_controls.append(control)
    raw_control_records["UNSCOPED_TOTAL_CONTROL"].extend(broader_vamc_controls)
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
                or candidate_ref.get("row_kind") not in {"SUBTOTAL", "TOTAL"}
                or not any(
                    type(coefficient) is int and coefficient != 0
                    for record in others
                    for coefficient in _coefficients(record)
                )
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
            equation = candidate_equation(
                equation_kind="EXACT_TRAILING_SOURCE_ROW_IS_SIBLING_GROUP_AGGREGATE",
                components=others,
                result=candidate,
            )
            if _equation_closes(equation):
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
            equation = candidate_equation(
                equation_kind="DERIVED_PROVISION_PARENT_EQUALS_EXHAUSTIVE_VISIBLE_CHILDREN",
                components=children,
                result=records[parent],
            )
            equations.append(equation)
            continue
        if parent not in records:
            continue
        variants = [
            candidate_equation(
                equation_kind="EXACT_VISIBLE_PARENT_EQUALS_EXHAUSTIVE_ADDITIVE_CHILDREN",
                components=children,
                result=records[parent],
            )
        ]
        if parent.endswith("_PROVISION"):
            variants.append(
                candidate_equation(
                    equation_kind="EXACT_SIGNED_PROVISION_PARENT_EQUALS_NEGATED_DETAIL_CHILDREN",
                    components=children,
                    result=records[parent],
                    multipliers=[-1] * len(children),
                )
            )
        exact_variants = _best_closing_equations(variants)
        if exact_variants:
            equation = exact_variants[0]
            equations.append(equation)
        else:
            equations.append(variants[0])
            reasons.append(f"PARENT_CHILD_EQUATION_MISMATCH:{parent}")
    for prefix in ("AFS", "HTM"):
        total_role = f"{prefix}_TOTAL"
        component_records = _top_component_records(prefix, records, compiled_specs=compiled_specs)
        total_candidates = raw_total_records[total_role]
        if not component_records:
            # A printed branch total is still a complete source observation
            # when every detailed row is blank and therefore omitted.  Map
            # only that visible total; never project its value into the absent
            # children.
            direct_total = _corroborate_identical(total_role, total_candidates)
            if total_candidates and direct_total is None:
                reasons.append(f"{prefix}_MULTIPLE_DISTINCT_VISIBLE_TOTALS_WITHOUT_COMPONENTS")
            elif direct_total is not None:
                records[total_role] = direct_total
            continue
        provision_role = f"{prefix}_PROVISION"
        effective_total_candidates = []
        for total in total_candidates:
            provision = records.get(provision_role)
            if provision is None or not _record_has_explicit_role_path(
                total, provision_role, compiled_specs=compiled_specs
            ):
                effective_total_candidates.append(total)
                continue
            variants = [
                candidate_equation(
                    equation_kind="EXACT_ANONYMOUS_PROVISION_SUBTOTAL_CORROBORATES_PARENT",
                    components=[provision],
                    result=total,
                    multipliers=[weight],
                )
                for weight in (1, -1)
            ]
            exact_variants = _best_closing_equations(variants)
            if exact_variants:
                equations.append(exact_variants[0])
            else:
                effective_total_candidates.append(total)
        total_candidates = effective_total_candidates
        gross_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        net_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        all_candidate_equations = []
        component_frontiers = [("CORE", component_records)]
        if prefix == "HTM" and "VAMC_FACE_VALUE" in records:
            component_frontiers.append(
                ("CORE_PLUS_VAMC_FACE", [*component_records, records["VAMC_FACE_VALUE"]])
            )
        for total in total_candidates:
            for frontier_kind, frontier_records in component_frontiers:
                gross_kind = "EXACT_VISIBLE_GROSS_COMPONENT_TOTAL"
                if frontier_kind != "CORE":
                    gross_kind += ":" + frontier_kind
                gross = candidate_equation(
                    equation_kind=gross_kind,
                    components=frontier_records,
                    result=total,
                )
                all_candidate_equations.append(gross)
                if _equation_closes(gross):
                    gross_matches.append((total, gross))
                if provision_role not in records:
                    continue
                provision = records[provision_role]
                for kind, weight in (
                    ("EXACT_VISIBLE_NET_TOTAL_WITH_SOURCE_SIGNED_PROVISION", 1),
                    ("EXACT_VISIBLE_NET_TOTAL_LESS_POSITIVE_PROVISION", -1),
                ):
                    equation_kind = kind
                    if frontier_kind != "CORE":
                        equation_kind += ":" + frontier_kind
                    net = candidate_equation(
                        equation_kind=equation_kind,
                        components=[*frontier_records, provision],
                        result=total,
                        multipliers=[*([1] * len(frontier_records)), weight],
                    )
                    all_candidate_equations.append(net)
                    if _equation_closes(net):
                        net_matches.append((total, net))

        exact_gross_matches = [pair for pair in gross_matches if pair[1]["status"] == "EXACT"]
        if exact_gross_matches:
            gross_matches = exact_gross_matches
        exact_net_matches = [pair for pair in net_matches if pair[1]["status"] == "EXACT"]
        if exact_net_matches:
            net_matches = exact_net_matches

        gross_record = _corroborate_identical(
            total_role, [record for record, _equation_receipt in gross_matches]
        )
        if gross_matches and gross_record is None:
            reasons.append(f"{prefix}_MULTIPLE_DISTINCT_VISIBLE_GROSS_TOTALS")
        elif gross_record is not None:
            records[total_role] = gross_record
            gross_equation = next(
                equation_receipt
                for record, equation_receipt in gross_matches
                if _coefficients(record) == _coefficients(gross_record)
            )
            equations.append(gross_equation)
            # Some sources flatten the only visible DEBT/EQUITY/OTHER group and
            # print just its children followed by the branch total.  When the
            # complete gross frontier is exactly the complete child frontier
            # of one and only one missing group, that visible total proves the
            # group parent as well.  This is an equation-derived structural
            # projection, not a label or document-specific fallback.
            missing_group_frontiers = []
            component_role_axis = set(gross_equation["component_roles"])
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
                group_equation = candidate_equation(
                    equation_kind=("DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL"),
                    components=children,
                    result=records[group_role],
                )
                equations.append(group_equation)
        elif len(component_records) == 1:
            singleton = component_records[0]
            records[total_role] = _record(
                total_role,
                singleton["cells"],
                singleton["source_refs"],
                "DERIVED_EXACT_SINGLETON_COMPONENT_TOTAL",
            )
            singleton_equation = candidate_equation(
                equation_kind="DERIVED_EXACT_SINGLETON_COMPONENT_TOTAL",
                components=[singleton],
                result=records[total_role],
            )
            equations.append(singleton_equation)

        if net_matches:
            net_records = [record for record, _equation_receipt in net_matches]
            net_record = _corroborate_identical(total_role, net_records)
            if net_record is None:
                reasons.append(f"{prefix}_MULTIPLE_DISTINCT_VISIBLE_NET_TOTALS")
            else:
                matching_equations = [
                    equation_receipt
                    for record, equation_receipt in net_matches
                    if _coefficients(record) == _coefficients(net_record)
                ]
                equations.extend(matching_equations)
                if total_role not in records:
                    records[total_role] = net_record
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
    quality_frontier = [
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
    if quality_frontier:
        unscoped_frontiers.append(
            (
                "QUALITY_VISIBLE_ROLE_FRONTIER",
                quality_frontier,
                [1] * len(quality_frontier),
            )
        )
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
            f"COMBINED_{branch_kind}_{vamc_kind}",
            [*branch_components, *vamc_components],
            [*branch_weights, *vamc_weights],
        )
        for branch_kind, branch_components, branch_weights in [
            *afs_frontiers,
            *htm_frontiers,
        ]
        for vamc_kind, vamc_components, vamc_weights in vamc_frontiers
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
    value_bearing_positions = [
        position
        for values in [
            *raw_records.values(),
            *raw_total_records.values(),
            *raw_control_records.values(),
        ]
        for record in values
        if (position := _source_record_position(record)) is not None
    ]
    terminal_source_position = max(value_bearing_positions, default=None)
    all_source_records = [
        record
        for values in [
            *raw_records.values(),
            *raw_total_records.values(),
            *raw_control_records.values(),
        ]
        for record in values
    ]

    def source_ref_identity(source_ref: Mapping[str, Any]) -> tuple[str, str, str, int]:
        locator = source_ref["locator"]
        return (
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            source_ref["row_ordinal"],
        )

    consumed_source_rows = {
        source_ref_identity(source_ref)
        for record in records.values()
        for source_ref in record["source_refs"]
    }
    consumed_source_rows.update(
        source_ref_identity(source_ref)
        for equation in equations
        if _equation_closes(equation)
        for refs in [
            *equation["component_source_refs"],
            equation["result_source_refs"],
        ]
        for source_ref in refs
    )
    table_terminal_rows: dict[tuple[str, str, str], int] = {}
    for source_record in all_source_records:
        for source_ref in source_record["source_refs"]:
            identity = source_ref_identity(source_ref)
            table_identity = identity[:3]
            table_terminal_rows[table_identity] = max(
                table_terminal_rows.get(table_identity, 0), identity[3]
            )
    trailing_total_reclassification_receipts = []
    combined_frontiers = [
        (kind, components, weights)
        for kind, components, weights in unscoped_frontiers
        if kind.startswith("COMBINED_")
    ]
    for source_role in ("AFS_TOTAL", "HTM_TOTAL"):
        for source_total in raw_total_records[source_role]:
            refs = source_total["source_refs"]
            if len(refs) != 1:
                continue
            source_ref = refs[0]
            identity = source_ref_identity(source_ref)
            if (
                identity in consumed_source_rows
                or source_ref.get("row_kind") != "TOTAL"
                or identity[3] != table_terminal_rows[identity[:3]]
            ):
                continue
            reclassified_total = _record(
                "UNSCOPED_TOTAL_CONTROL",
                source_total["cells"],
                source_total["source_refs"],
                "SOURCE_TOTAL_RECLASSIFIED_BY_EXACT_COMBINED_FAMILY_FRONTIER",
            )
            variants = [
                candidate_equation(
                    equation_kind="EXACT_RECLASSIFIED_TRAILING_SOURCE_TOTAL_" + kind,
                    components=components,
                    result=reclassified_total,
                    multipliers=weights,
                )
                for kind, components, weights in combined_frontiers
            ]
            selected, resolution = _select_unscoped_closing_equation(
                variants, terminal_control=True
            )
            resolution["control_source_refs"] = canonical_clone_v1(
                source_total["source_refs"]
            )
            resolution["source_role"] = source_role
            trailing_total_reclassification_receipts.append(resolution)
            if selected is None:
                reasons.append(
                    "TRAILING_VISIBLE_BRANCH_TOTAL_DOES_NOT_CLOSE_LOCAL_OR_COMBINED_FRONTIER"
                )
                if variants:
                    equations.append(variants[0])
                continue
            equations.append(selected)
            consumed_source_rows.add(identity)
    unscoped_control_resolution_receipts = []
    for control in raw_control_records["UNSCOPED_TOTAL_CONTROL"]:
        variants = [
            candidate_equation(
                equation_kind="EXACT_UNSCOPED_SOURCE_TOTAL_" + kind,
                components=components,
                result=control,
                multipliers=weights,
            )
            for kind, components, weights in unscoped_frontiers
        ]
        control_position = _source_record_position(control)
        terminal_control = bool(
            control_position is not None
            and control_position == terminal_source_position
            and control_position[0] == region_axis[-1]["fragment_ordinal"]
            and control["source_refs"][0].get("row_kind") == "TOTAL"
        )
        selected, resolution_receipt = _select_unscoped_closing_equation(
            variants, terminal_control=terminal_control
        )
        resolution_receipt["control_source_refs"] = canonical_clone_v1(
            control["source_refs"]
        )
        unscoped_control_resolution_receipts.append(resolution_receipt)
        if selected is not None:
            equations.append(selected)
        else:
            reasons.append("UNSCOPED_VISIBLE_TOTAL_DOES_NOT_CLOSE_ANY_FAMILY_FRONTIER")
            if variants:
                equations.append(variants[0])
    proven_role_lanes: dict[str, set[int]] = defaultdict(set)
    for equation in equations:
        if not _equation_closes(equation):
            continue
        equation_roles = [*equation["component_roles"], equation["result_role"]]
        for lane, lane_status in enumerate(equation["lane_statuses"], start=1):
            if lane_status == "UNOBSERVED_SOURCE_LANE":
                continue
            for role in equation_roles:
                proven_role_lanes[role].add(lane)
    optional_omissions = []
    for role, record in list(records.items()):
        conditional_lanes = [
            lane
            for lane, cell in enumerate(record["cells"], start=1)
            if cell["state"].endswith("ZERO_IF_EQUATION_EXACT")
        ]
        if not conditional_lanes:
            continue
        unproven_conditional_lanes = []
        for lane in conditional_lanes:
            cell = record["cells"][lane - 1]
            if cell.get("source_text") is not None and lane in proven_role_lanes[role]:
                cell["state"] = "INFERRED_" + cell["state"]
            else:
                unproven_conditional_lanes.append(lane)
        if not unproven_conditional_lanes:
            continue
        if role.startswith(_OPTIONAL_DIRECT_VIEW_PREFIXES):
            optional_omissions.append(
                {
                    "blank_lanes": unproven_conditional_lanes,
                    "disposition": "OPTIONAL_DIRECT_VIEW_BLANK_VALUE_OMISSION",
                    "role": role,
                    "source_refs": canonical_clone_v1(record["source_refs"]),
                }
            )
            del records[role]
            continue
        reasons.append(f"UNPROVEN_BLANK_ZERO_IN_MAPPING_ROLE:{role}")
    reasons = sorted(set(reasons))
    exact = not reasons and all(_equation_closes(equation) for equation in equations)
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
                "unit": candidate_unit,
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
            "document_period_context": document_period_context,
            "equations": equations,
            "optional_direct_view_omissions": optional_omissions,
            "promoted_summary_resolution_receipts": promoted_summary_resolution_receipts,
            "query_receipt": canonical_clone_v1(expected_receipt),
            "rule": "EXACT_MULTI_COMPONENT_HIERARCHY_AND_TOTAL_ALL_LANES",
            "source_visible_blank_value_omissions": source_visible_blank_value_omissions,
            "structural_root_receipt": {
                "emitted_mapping": False,
                "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
            "source_row_reclassifications": source_row_reclassifications,
            "table_receipts": table_receipts,
            "trailing_total_reclassification_receipts": (
                trailing_total_reclassification_receipts
            ),
            "unscoped_control_resolution_receipts": unscoped_control_resolution_receipts,
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
