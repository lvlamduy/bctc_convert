from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from bctc_ai.mapping import semantic_local_accounting_schema_candidate_v1 as candidate_module
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    SemanticLocalAccountingSchemaCandidateV1Error,
    _authority_snapshot,
    _build_payload,
    _git_file_bytes_at_commit,
    _historical_loan_maturity_v1_epoch,
    _historical_loan_maturity_v1_schema_view,
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

    # This helper remains the live-schema authority used by later family
    # builders; historical E-0045 replay has a separate, explicit seam.
    assert authority["schema_revision"] == "UNIVERSAL_BANK_BCTC_SCHEMA@6076"
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
            "display_order": 209,
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


def _compatible_contexts() -> dict[int, SimpleNamespace]:
    contexts = {
        schema_id: SimpleNamespace(mapping_eligible=True, context_status="RESOLVED")
        for schema_id in (560, 716, 752, 753, 754, 755, 5747)
    }
    contexts[1944] = SimpleNamespace(mapping_eligible=False, context_status="UNRESOLVED_ORPHAN")
    return contexts


def test_historical_epoch_is_git_authenticated_and_not_read_from_live_files(
    project_root, monkeypatch
) -> None:
    authority, display_orders = _historical_loan_maturity_v1_epoch(project_root)

    assert authority["schema_revision"] == "UNIVERSAL_BANK_BCTC_SCHEMA@6056"
    assert authority["schema_item_count"] == 1935
    assert authority["tm_item_count"] == 1701
    assert display_orders == {
        560: 0,
        716: 157,
        752: 200,
        753: 201,
        754: 202,
        755: 203,
        5747: 204,
        1944: 1700,
    }

    original = candidate_module._git_file_bytes_at_commit

    def _corrupt_one_blob(project_root, commit, relative):
        payload = original(project_root, commit, relative)
        return payload + b"x" if relative == "data/registered/schema_registry.json" else payload

    monkeypatch.setattr(candidate_module, "_git_file_bytes_at_commit", _corrupt_one_blob)
    with pytest.raises(SemanticLocalAccountingSchemaCandidateV1Error, match="identity drifted"):
        _historical_loan_maturity_v1_epoch(project_root)


def test_missing_historical_git_object_fails_closed(project_root) -> None:
    with pytest.raises(
        SemanticLocalAccountingSchemaCandidateV1Error,
        match="commit identity is invalid",
    ):
        _git_file_bytes_at_commit(
            project_root,
            "7078ea7",
            "template/Bank_TM_ReportNormId.v2.xlsx",
        )
    with pytest.raises(
        SemanticLocalAccountingSchemaCandidateV1Error,
        match="lacks authority input",
    ):
        _git_file_bytes_at_commit(
            project_root,
            "0" * 40,
            "template/Bank_TM_ReportNormId.v2.xlsx",
        )


def test_unrelated_append_and_absolute_order_shift_do_not_drift_historical_family_view(
    authority_and_schema, project_root
) -> None:
    _authority, live_by_id = authority_and_schema
    shifted = deepcopy(live_by_id)
    for item in shifted.values():
        item.display_order += 17
    shifted[716].children.insert(0, 9000)
    _historical_authority, historical_orders = _historical_loan_maturity_v1_epoch(project_root)

    frozen = _historical_loan_maturity_v1_schema_view(
        shifted, _compatible_contexts(), historical_orders
    )

    assert {schema_id: frozen[schema_id].display_order for schema_id in historical_orders} == {
        560: 0,
        716: 157,
        752: 200,
        753: 201,
        754: 202,
        755: 203,
        5747: 204,
        1944: 1700,
    }
    assert live_by_id[752].display_order == 205
    assert frozen[752].children[0] == 753


@pytest.mark.parametrize("drift", ("name", "edge", "context"))
def test_live_family_semantic_drift_still_fails_closed(
    authority_and_schema, project_root, drift
) -> None:
    _authority, live_by_id = authority_and_schema
    changed = deepcopy(live_by_id)
    contexts = _compatible_contexts()
    if drift == "name":
        changed[753].canonical_name = "Forged short-term leaf"
    elif drift == "edge":
        changed[752].children.remove(754)
    else:
        contexts[754].mapping_eligible = False
    _historical_authority, historical_orders = _historical_loan_maturity_v1_epoch(project_root)

    with pytest.raises(SemanticLocalAccountingSchemaCandidateV1Error, match="live"):
        _historical_loan_maturity_v1_schema_view(changed, contexts, historical_orders)


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
