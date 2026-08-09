from __future__ import annotations

from bctc_ai.schema.coverage import (
    SCHEMA_CONSUMERS,
    SchemaSearchEvidence,
    evaluate_mandatory_search,
    load_schema_coverage,
)


def test_every_consumer_contains_tm_1944_in_workbook_order(project_root):
    contract = load_schema_coverage(project_root)
    assert contract.version == 2
    assert len(contract.targets) == 1935
    assert contract.targets[-1].schema_id == 1944
    assert (
        contract.targets[-1].canonical_name
        == "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    )
    for consumer in SCHEMA_CONSUMERS:
        identifiers = contract.ids_for(consumer)
        assert len(identifiers) == 1935
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
    assert complete.universal_target_count == 1935
    assert complete.target_count_by_statement == {
        "CDKT": 99,
        "KQKD": 25,
        "LCTT": 110,
        "TM": 1701,
    }
    assert complete.completed_count_by_role == {"ROLE_A": 1935, "ROLE_B": 1935}
    assert complete.outcome_count_by_role["ROLE_A"]["NOT_OBSERVED"] == 1935
    assert complete.outcome_count_by_role["ROLE_B"]["NOT_OBSERVED"] == 1934
    assert complete.outcome_count_by_role["ROLE_B"]["OBSERVED_VALUE"] == 1
    assert complete.applicable_count_by_role == {"ROLE_A": 1935, "ROLE_B": 1935}
    assert complete.observed_count_by_role == {"ROLE_A": 0, "ROLE_B": 1}
    assert complete.mapped_numeric_count_by_role == {"ROLE_A": 0, "ROLE_B": 1}
    assert complete.not_observed_count_by_role == {"ROLE_A": 1935, "ROLE_B": 1934}
    assert complete.not_applicable_count_by_role == {"ROLE_A": 0, "ROLE_B": 0}
    assert complete.ambiguous_count_by_role == {"ROLE_A": 0, "ROLE_B": 0}
    assert complete.unresolved_count_by_role == {"ROLE_A": 0, "ROLE_B": 0}
    assert complete.tm_1944_completed_by_role == {"ROLE_A": True, "ROLE_B": True}


def test_mandatory_search_preserves_all_universal_terminal_outcomes(project_root):
    contract = load_schema_coverage(project_root)
    canonical_outcomes = (
        "OBSERVED_VALUE",
        "OBSERVED_ZERO",
        "DASH",
        "BLANK",
        "NOT_OBSERVED",
        "NOT_APPLICABLE",
        "AMBIGUOUS",
        "UNRESOLVED",
    )
    assert all(outcome in contract.terminal_outcomes for outcome in canonical_outcomes)
    expected_ids = contract.ids_for("MANDATORY_SEARCH")
    outcome_by_id = dict(
        zip(expected_ids[: len(canonical_outcomes)], canonical_outcomes, strict=True)
    )
    evidence = [
        SchemaSearchEvidence(
            document_id="sha256:status-document",
            role=role,
            schema_id=schema_id,
            terminal_outcome=outcome_by_id.get(schema_id, "NOT_OBSERVED"),
        )
        for role in contract.mandatory_search_roles
        for schema_id in expected_ids
    ]
    result = evaluate_mandatory_search(contract, "sha256:status-document", evidence)
    assert result.status == "PASS"
    for role in contract.mandatory_search_roles:
        for outcome in canonical_outcomes:
            expected = 1928 if outcome == "NOT_OBSERVED" else 1
            assert result.outcome_count_by_role[role][outcome] == expected
        assert result.observed_count_by_role[role] == 4
        assert result.mapped_numeric_count_by_role[role] == 2
        assert result.not_observed_count_by_role[role] == 1928
        assert result.not_applicable_count_by_role[role] == 1
        assert result.ambiguous_count_by_role[role] == 1
        assert result.unresolved_count_by_role[role] == 1
        assert result.applicable_count_by_role[role] == 1934
        assert sum(result.outcome_count_by_role_and_statement[role]["CDKT"].values()) == 99
