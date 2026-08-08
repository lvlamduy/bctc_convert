from __future__ import annotations

from bctc_ai.schema.coverage import (
    SCHEMA_CONSUMERS,
    SchemaSearchEvidence,
    evaluate_mandatory_search,
    load_schema_coverage,
)


def test_every_consumer_contains_tm_1944_in_workbook_order(project_root):
    contract = load_schema_coverage(project_root)
    assert len(contract.targets) == 1824
    assert contract.targets[-1].schema_id == 1944
    assert (
        contract.targets[-1].canonical_name
        == "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    )
    for consumer in SCHEMA_CONSUMERS:
        identifiers = contract.ids_for(consumer)
        assert len(identifiers) == 1824
        assert identifiers[-1] == 1944
        assert 1944 in identifiers


def test_mandatory_search_requires_1944_from_both_independent_roles(project_root):
    contract = load_schema_coverage(project_root)
    evidence = [
        SchemaSearchEvidence(
            document_id="sha256:document",
            role=role,
            schema_id=schema_id,
            terminal_outcome="NOT_OBSERVED",
        )
        for role in ("ROLE_A", "ROLE_B")
        for schema_id in contract.ids_for("MANDATORY_SEARCH")
        if not (role == "ROLE_B" and schema_id == 1944)
    ]
    incomplete = evaluate_mandatory_search(contract, "sha256:document", evidence)
    assert incomplete.status == "INCOMPLETE"
    assert incomplete.missing_by_role["ROLE_A"] == ()
    assert incomplete.missing_by_role["ROLE_B"] == (1944,)
    assert incomplete.tm_1944_completed_by_role == {"ROLE_A": True, "ROLE_B": False}

    evidence.append(
        SchemaSearchEvidence(
            document_id="sha256:document",
            role="ROLE_B",
            schema_id=1944,
            terminal_outcome="OBSERVED_VALUE",
        )
    )
    complete = evaluate_mandatory_search(contract, "sha256:document", evidence)
    assert complete.status == "PASS"
    assert complete.completed_count_by_role == {"ROLE_A": 1824, "ROLE_B": 1824}
    assert complete.tm_1944_completed_by_role == {"ROLE_A": True, "ROLE_B": True}
