from __future__ import annotations

import json
from pathlib import Path

from bctc_ai.evaluation import (
    accounting_family_topology_v1 as topology_v1,
)
from bctc_ai.evaluation import (
    family_first_accounting_evidence_sweep_v1 as evidence_v1,
)
from bctc_ai.evaluation import (
    family_first_accounting_schema_mapping_v1 as mapping_v1,
)
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
    build_loan_enterprise_family12_topology_spec_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_ROOT = _ROOT / "config" / "families"


def _load(name: str) -> dict[str, object]:
    return json.loads((_CONFIG_ROOT / name).read_text(encoding="utf-8"))


def test_family12_tracked_topology_evaluation_and_schema_specs_compile_together() -> None:
    family = _load("tm-loan-enterprise-family12-topology-v4.json")
    evaluation = _load("tm-loan-enterprise-family12-evaluation-v5.json")
    binding = _load("tm-loan-enterprise-family12-schema-binding-v6.json")

    assert family == build_loan_enterprise_family12_topology_spec_v1()
    compiled = topology_v1._spec(family)
    policy = evidence_v1._evaluation_spec(evaluation, compiled, raw_family_spec=family)
    parsed_binding = mapping_v1._schema_spec(binding, family)
    nodes, _schema_ref = mapping_v1._schema_graph(_ROOT)
    parent, direct, aggregates = mapping_v1._bind_schema(nodes, parsed_binding)

    assert policy["format_version"] == evidence_v1.EVALUATION_SPEC_FORMAT_V5
    assert policy["expected_lane_unit_kind_alternatives"] == [
        ["MONEY", "MONEY"],
        ["MONEY", "PERCENT", "MONEY", "PERCENT"],
    ]
    assert parsed_binding["format_version"] == mapping_v1.SPEC_FORMAT_VERSION_V6
    assert parsed_binding["family_owner_report_norm_id"] == 716
    assert parent["schema_id"] == 766
    assert len(direct) == 19
    assert aggregates == []
    assert direct["FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"]["schema_id"] == 6058
    assert direct["FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"]["parent_id"] == 727
    assert all(
        node["parent_id"] == 766
        for role, node in direct.items()
        if role != "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"
    )


def test_family12_hierarchy_declares_nested_direct_frontiers_without_mixed_levels() -> None:
    evaluation = _load("tm-loan-enterprise-family12-evaluation-v5.json")
    equations = {
        equation["result_role"]: equation
        for equation in evaluation["hierarchical_closure_spec"]["equations"]
    }

    foreign = equations["FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"]
    assert foreign["component_selection_policy"] == ("EXHAUSTIVE_VISIBLE_SUBSET_OF_DECLARED_POOL")
    assert foreign["component_role_alternatives"][0]["component_roles"] == [
        "FOREIGN_BRANCH_ENTERPRISE_LOANS",
        "FOREIGN_BRANCH_INDIVIDUAL_LOANS",
    ]

    core = equations["CORE_LOAN_ENTERPRISE_SUBTOTAL"]
    core_pool = core["component_role_alternatives"][0]["component_roles"]
    assert {
        "ECONOMIC_ORGANIZATION_LOANS_GROUP",
        "INDIVIDUAL_LOANS_GROUP",
        "OTHER_CUSTOMER_LOANS_GROUP",
        "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS",
    } <= set(core_pool)
    assert "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS" not in core_pool
    assert "FOREIGN_BRANCH_ENTERPRISE_LOANS" not in core_pool
    assert "FOREIGN_BRANCH_INDIVIDUAL_LOANS" not in core_pool
    assert core["component_selection_policy"] == ("EXHAUSTIVE_VISIBLE_SUBSET_OF_DECLARED_POOL")
    assert core["visible_source_policy"] == "REQUIRE_EXHAUSTIVE_COMPONENTS"

    root = equations["LOAN_ENTERPRISE_FAMILY12"]
    assert root["component_selection_policy"] == "DECLARED_EXACT_ALTERNATIVE"
    assert [
        alternative["component_roles"] for alternative in root["component_role_alternatives"]
    ] == [
        ["CORE_LOAN_ENTERPRISE_SUBTOTAL"],
        [
            "CORE_LOAN_ENTERPRISE_SUBTOTAL",
            "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS",
        ],
    ]
    assert root["trailing_result_policy"] == "CORROBORATE_UNIQUE_MATCH_IF_PRESENT"


def test_family12_production_specs_are_declarative_and_partition_every_source_role() -> None:
    family = _load("tm-loan-enterprise-family12-topology-v4.json")
    binding = _load("tm-loan-enterprise-family12-schema-binding-v6.json")
    family_roles = [child["role"] for child in family["children"]]
    bound_roles = [item["role"] for item in binding["role_bindings"]]

    assert set([*bound_roles, *binding["ignored_roles"]]) == set(family_roles)
    assert len([*bound_roles, *binding["ignored_roles"]]) == len(family_roles)
    serialized = json.dumps(
        {
            "binding": binding,
            "evaluation": _load("tm-loan-enterprise-family12-evaluation-v5.json"),
            "family": family,
        },
        ensure_ascii=False,
    )
    for token in (
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
        "2025",
        "2026",
        "document_ordinal",
        "page_sequence",
    ):
        assert token not in serialized
