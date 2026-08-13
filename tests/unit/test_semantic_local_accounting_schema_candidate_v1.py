from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.mapping import semantic_local_accounting_schema_candidate_v1 as candidate_module
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    SemanticLocalAccountingSchemaCandidateV1Error,
    _authority_snapshot,
    _build_payload,
    _validate_payload,
)


@pytest.fixture(scope="module")
def authority_and_schema(project_root):
    return _authority_snapshot(project_root)


def _graph(*, accepted: bool = True) -> dict:
    nodes = []
    for kind, role, suffix in (
        ("ACCOUNTING_ROLE", "OWNER_LABEL", "owner"),
        ("ACCOUNTING_ROLE", "BRANCH_LABEL", "branch"),
        ("LOGICAL_ROW", "SHORT_TERM", "short"),
        ("LOGICAL_ROW", "MEDIUM_TERM", "medium"),
        ("LOGICAL_ROW", "LONG_TERM", "long"),
        ("LOGICAL_ROW", "TOTAL", "total"),
    ):
        attributes = (
            {"accounting_role": role}
            if kind == "ACCOUNTING_ROLE"
            else {
                "row_role": role,
                "total_resolution": (
                    "IMMEDIATE_UNLABELED_NUMERIC_ROW" if role == "TOTAL" else None
                ),
            }
        )
        nodes.append(
            {
                "node_id": f"slagv2:node:{suffix:0<64}",
                "kind": kind,
                "attributes": attributes,
            }
        )
    return {
        "graph_id": f"slagv2:graph:{'a' * 64}",
        "status": ("ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE" if accepted else "UNRESOLVED"),
        "family_id": "LOAN_MATURITY_BUCKETS",
        "family_spec_sha256": ("2184e8f9adc3439e06b68adac426060ef876795b8bb1dc4bb4754e6da12b0e06"),
        "supplied_family_collision_scope_spec_sha256_by_id": {
            "LOAN_MATURITY_BUCKETS": (
                "2184e8f9adc3439e06b68adac426060ef876795b8bb1dc4bb4754e6da12b0e06"
            )
        },
        "nodes": nodes if accepted else [],
    }


def test_exact_tm_authority_builds_candidate_only_strict_maturity_core(
    authority_and_schema,
) -> None:
    authority, by_id = authority_and_schema
    result = _validate_payload(_build_payload(_graph(), authority, by_id))

    assert result["status"] == "CANDIDATE_SET_READY"
    assert [item["typed_role"] for item in result["role_candidates"]] == [
        "OWNER_LABEL",
        "BRANCH_LABEL",
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
        "TOTAL",
    ]
    assert [item["candidate_report_norm_ids"] for item in result["role_candidates"]] == [
        [716],
        [752],
        [753],
        [754],
        [755],
        [],
    ]
    assert result["role_candidates"][-1]["disposition"] == "SOURCE_ONLY_VALIDATION"
    assert result["unassessed_schema_children"] == [
        {
            "report_norm_id": 5747,
            "parent_report_norm_id": 752,
            "canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            "display_order": 204,
            "disposition": "UNASSESSED_SCHEMA_CHILD",
        }
    ]
    assert result["source_semantics"] == {
        "statement_type": None,
        "report_scope": None,
        "canonical_period_type": None,
    }
    assert result["readiness"] == {
        "schema_candidate_set_ready": True,
        "schema_mapping_ready": False,
        "canonicalization_eligible": False,
        "export_eligible": False,
    }
    assert all(
        value is False for key, value in result["safety"].items() if key != "typed_graph_roles_only"
    )


def test_unresolved_graph_emits_no_schema_candidates_or_absence(authority_and_schema) -> None:
    authority, by_id = authority_and_schema
    result = _validate_payload(_build_payload(_graph(accepted=False), authority, by_id))

    assert result["status"] == "UNRESOLVED_GRAPH_NOT_ACCEPTED"
    assert result["role_candidates"] == []
    assert result["unassessed_schema_children"] == []
    assert result["metrics"] == {
        "candidate_role_count": 0,
        "singleton_schema_candidate_count": 0,
        "source_only_validation_role_count": 0,
        "unassessed_schema_child_count": 0,
    }


@pytest.mark.parametrize(
    "mutation",
    (
        lambda graph: graph["nodes"].pop(),
        lambda graph: graph["nodes"][-1]["attributes"].update({"total_resolution": "FORGED"}),
        lambda graph: graph.update({"family_id": "OTHER"}),
    ),
)
def test_graph_role_total_and_family_drift_fail_closed(authority_and_schema, mutation) -> None:
    authority, by_id = authority_and_schema
    graph = _graph()
    mutation(graph)
    with pytest.raises(SemanticLocalAccountingSchemaCandidateV1Error):
        _build_payload(graph, authority, by_id)


def test_payload_identity_and_safety_tamper_fail_closed(authority_and_schema) -> None:
    authority, by_id = authority_and_schema
    original = _build_payload(_graph(), authority, by_id)
    for field, mutation in (
        ("safety", lambda item: item["safety"].update({"schema_mapping_authority": True})),
        ("source", lambda item: item["source_semantics"].update({"report_scope": "CONSOLIDATED"})),
        (
            "mapping",
            lambda item: item["role_candidates"][2].update({"candidate_report_norm_ids": [1944]}),
        ),
    ):
        tampered = deepcopy(original)
        mutation(tampered)
        with pytest.raises(SemanticLocalAccountingSchemaCandidateV1Error, match="identity|safety"):
            _validate_payload(tampered), field


def test_exported_safety_view_cannot_weaken_minted_policy(
    authority_and_schema, monkeypatch
) -> None:
    authority, by_id = authority_and_schema
    monkeypatch.setattr(candidate_module, "SAFETY", {"schema_mapping_authority": True})
    result = _build_payload(_graph(), authority, by_id)

    assert result["safety"]["schema_mapping_authority"] is False
