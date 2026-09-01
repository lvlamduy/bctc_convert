from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest
from test_gemini_json_multitable_hierarchical_family_v1 import _json as _family_spec
from test_gemini_json_multitable_hierarchical_indexed_wiring_v1 import (
    _fixture as _indexed_fixture,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_multitable_hierarchical_accounting_family_v1", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_net_interest_historical_oracle_accepts_its_single_verified_mapping_axis() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-net-interest-income-topology-v1.json"),
        _family_spec("tm-net-interest-income-evaluation-v1.json"),
        _family_spec("tm-net-interest-income-schema-binding-v1.json"),
    )

    oracles = runner._historical_oracles(compiled_specs=compiled)
    profile = runner._release_profile(compiled)

    assert [item[0]["format_version"] for item in oracles] == [
        "ANNUAL_2025_NET_INTEREST_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
    ]
    assert (
        sum(
            len(runner._historical_verified_mappings(trial))
            for _oracle_ref, oracle in oracles
            for trial in oracle["trials"]
        )
        == 8
    )
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 140,
        "not_observed_count": 0,
        "ready_count": 140,
        "unresolved_count": 0,
    }
    assert profile["axis_counts"] == {
        "clusters": 140,
        "equations": 140,
        "historical_comparator": 16,
        "mappings": 140,
    }


def test_customer_collateral_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-customer-collateral-held-topology-v1.json"),
        _family_spec("tm-customer-collateral-held-evaluation-v1.json"),
        _family_spec("tm-customer-collateral-held-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 314,
        "not_observed_count": 82,
        "ready_count": 58,
        "unresolved_count": 0,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 75,
        "historical_comparator_exact_count": 56,
        "historical_disposition_exact_count": 16,
        "historical_mapping_exact_count": 40,
        "historical_mapping_record_count": 40,
        "mapping_count": 314,
    }
    assert profile["axis_counts"] == {
        "clusters": 58,
        "equations": 75,
        "historical_comparator": 56,
        "mappings": 314,
    }
    assert profile["query_receipt"]["accepted_cluster_count"] == 58
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "CUSTOMER_COLLATERAL_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_CUSTOMER_COLLATERAL_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_bank_pledged_assets_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-bank-pledged-discounted-assets-topology-v1.json"),
        _family_spec("tm-bank-pledged-discounted-assets-evaluation-v1.json"),
        _family_spec("tm-bank-pledged-discounted-assets-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 114,
        "not_observed_count": 90,
        "ready_count": 50,
        "unresolved_count": 0,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 52,
        "historical_comparator_exact_count": 34,
        "historical_disposition_exact_count": 16,
        "historical_mapping_exact_count": 18,
        "historical_mapping_record_count": 18,
        "mapping_count": 114,
    }
    assert profile["axis_counts"] == {
        "clusters": 50,
        "equations": 52,
        "historical_comparator": 34,
        "mappings": 114,
    }
    assert profile["query_receipt"]["accepted_cluster_count"] == 50
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "BANK_PLEDGED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_BANK_PLEDGED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_contingent_liabilities_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-contingent-liabilities-commitments-topology-v1.json"),
        _family_spec("tm-contingent-liabilities-commitments-evaluation-v1.json"),
        _family_spec("tm-contingent-liabilities-commitments-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 769,
        "not_observed_count": 57,
        "ready_count": 83,
        "unresolved_count": 0,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 557,
        "historical_comparator_exact_count": 121,
        "historical_disposition_exact_count": 16,
        "historical_mapping_exact_count": 105,
        "historical_mapping_record_count": 105,
        "mapping_count": 769,
    }
    assert profile["axis_counts"] == {
        "clusters": 83,
        "equations": 557,
        "historical_comparator": 121,
        "mappings": 769,
    }
    assert profile["query_receipt"]["accepted_cluster_count"] == 83
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_employee_income_release_profile_decimal_oracles_and_axes_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-employee-income-topology-v1.json"),
        _family_spec("tm-employee-income-evaluation-v1.json"),
        _family_spec("tm-employee-income-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 300,
        "not_observed_count": 74,
        "ready_count": 60,
        "unresolved_count": 6,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 140,
        "historical_comparator_exact_count": 43,
        "historical_disposition_exact_count": 12,
        "historical_mapping_exact_count": 31,
        "historical_mapping_record_count": 31,
        "mapping_count": 300,
    }
    assert profile["axis_counts"] == {
        "clusters": 60,
        "equations": 140,
        "historical_comparator": 47,
        "mappings": 300,
    }
    assert profile["query_receipt"]["accepted_cluster_count"] == 66
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "EMPLOYEE_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_EMPLOYEE_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]
    assert runner._canonical_comparator_decimal("30.30", 2) == ("30.30", 2)
    assert runner._canonical_comparator_decimal("13.94", None) == ("13.94", 2)
    assert runner._canonical_comparator_decimal("13.940", 2) is None


def test_subsidiary_acquisition_release_profile_and_absence_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-subsidiary-acquisition-disposal-topology-v1.json"),
        _family_spec("tm-subsidiary-acquisition-disposal-evaluation-v1.json"),
        _family_spec("tm-subsidiary-acquisition-disposal-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 0,
        "not_observed_count": 140,
        "ready_count": 0,
        "unresolved_count": 0,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 0,
        "historical_comparator_exact_count": 16,
        "historical_disposition_exact_count": 16,
        "historical_mapping_exact_count": 0,
        "historical_mapping_record_count": 0,
        "mapping_count": 0,
    }
    assert profile["axis_counts"] == {
        "clusters": 0,
        "equations": 0,
        "historical_comparator": 16,
        "mappings": 0,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "SUBSIDIARY_ACQUISITION_DISPOSAL_8BANK_BOUND_REPORT_ABSENCE_V1",
        "ANNUAL_2025_SUBSIDIARY_ACQUISITION_DISPOSAL_8BANK_BOUND_REPORT_ABSENCE_V1",
    ]


def test_cash_equivalents_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-cash-equivalents-topology-v1.json"),
        _family_spec("tm-cash-equivalents-evaluation-v1.json"),
        _family_spec("tm-cash-equivalents-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 548,
        "not_observed_count": 35,
        "ready_count": 105,
        "unresolved_count": 0,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 109,
        "historical_comparator_exact_count": 90,
        "historical_disposition_exact_count": 16,
        "historical_mapping_exact_count": 74,
        "historical_mapping_record_count": 74,
        "mapping_count": 548,
    }
    assert profile["axis_counts"] == {
        "clusters": 105,
        "equations": 109,
        "historical_comparator": 90,
        "mappings": 548,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "CASH_EQUIVALENTS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_CASH_EQUIVALENTS_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_income_tax_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-income-tax-topology-v1.json"),
        _family_spec("tm-income-tax-evaluation-v1.json"),
        _family_spec("tm-income-tax-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 499,
        "not_observed_count": 71,
        "ready_count": 69,
        "unresolved_count": 0,
    }
    assert profile["audit_metrics"] == {
        "equation_count": 152,
        "historical_comparator_exact_count": 105,
        "historical_disposition_exact_count": 16,
        "historical_mapping_exact_count": 89,
        "historical_mapping_record_count": 89,
        "mapping_count": 499,
    }
    assert profile["axis_counts"] == {
        "clusters": 69,
        "equations": 152,
        "historical_comparator": 105,
        "mappings": 499,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "INCOME_TAX_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_INCOME_TAX_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_other_activity_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-other-activity-topology-v1.json"),
        _family_spec("tm-other-activity-evaluation-v1.json"),
        _family_spec("tm-other-activity-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 587,
        "not_observed_count": 68,
        "ready_count": 72,
        "unresolved_count": 0,
    }
    assert profile["axis_counts"] == {
        "clusters": 72,
        "equations": 176,
        "historical_comparator": 111,
        "mappings": 587,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "OTHER_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_OTHER_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_operating_expense_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-operating-expense-topology-v1.json"),
        _family_spec("tm-operating-expense-evaluation-v1.json"),
        _family_spec("tm-operating-expense-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 1648,
        "not_observed_count": 0,
        "ready_count": 138,
        "unresolved_count": 2,
    }
    assert profile["axis_counts"] == {
        "clusters": 138,
        "equations": 334,
        "historical_comparator": 218,
        "mappings": 1648,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "OPERATING_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_OPERATING_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_capital_contribution_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-capital-contribution-dividend-income-topology-v1.json"),
        _family_spec("tm-capital-contribution-dividend-income-evaluation-v1.json"),
        _family_spec("tm-capital-contribution-dividend-income-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 428,
        "not_observed_count": 22,
        "ready_count": 118,
        "unresolved_count": 0,
    }
    assert profile["axis_counts"] == {
        "clusters": 118,
        "equations": 192,
        "historical_comparator": 71,
        "mappings": 428,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
    ]


def test_combined_securities_release_profile_and_historical_oracles_are_pinned() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-combined-securities-net-topology-v1.json"),
        _family_spec("tm-combined-securities-net-evaluation-v1.json"),
        _family_spec("tm-combined-securities-net-schema-binding-v1.json"),
    )
    profile = runner._release_profile(compiled)
    assert profile["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 12,
        "not_observed_count": 128,
        "ready_count": 12,
        "unresolved_count": 0,
    }
    assert profile["axis_counts"] == {
        "clusters": 12,
        "equations": 36,
        "historical_comparator": 17,
        "mappings": 12,
    }
    assert profile["query_receipt"]["selected_page_count"] == 8947
    assert [
        item[0]["format_version"] for item in runner._historical_oracles(compiled_specs=compiled)
    ] == [
        "COMBINED_SECURITIES_NET_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "ANNUAL_2025_COMBINED_SECURITIES_NET_8BANK_BOUND_REPORT_ABSENCE_V1",
    ]


def test_audit_replay_rejects_coherent_axis_and_embedded_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: ([], [{"fixture": "historical-oracle"}]),
    )
    database, selected, evidence, trials, compiled = _indexed_fixture(tmp_path)
    topology = _family_spec("tm-other-assets-topology-v1.json")
    evaluation = _family_spec("tm-other-assets-evaluation-v1.json")
    schema = _family_spec("tm-other-assets-schema-binding-v1.json")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=evidence,
    )
    sweep_output = tmp_path / "sweep.json"
    sweep_output.write_bytes(runner.canonical_json_bytes_v1(sweep))
    spec_refs = {
        "evaluation": {"fixture": "evaluation"},
        "schema_binding": {"fixture": "schema_binding"},
        "topology": {"fixture": "topology"},
    }
    audit = runner.build_multitable_hierarchical_experimental_audit_v1(
        sweep=sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected,
        indexed_query_evidence=evidence,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    replay_args = {
        "database": database,
        "sweep": sweep,
        "sweep_output": sweep_output,
        "selected_page_json_version_ids": selected,
        "indexed_query_evidence": evidence,
        "trials": trials,
        "compiled_specs": compiled,
        "spec_refs": spec_refs,
    }
    assert (
        runner.validate_multitable_hierarchical_experimental_audit_replay_v1(audit, **replay_args)
        == audit
    )

    forged_audit = copy.deepcopy(audit)
    forged_audit["axes"]["mappings"][0]["coefficients"][0] += 777
    forged_audit["axis_sha256"]["mappings"] = runner.canonical_json_sha256_v1(
        forged_audit["axes"]["mappings"]
    )
    audit_material = {key: value for key, value in forged_audit.items() if key != "audit_id"}
    forged_audit["audit_id"] = "gjmthfeav1:audit:" + runner.canonical_json_sha256_v1(audit_material)
    runner.validate_multitable_hierarchical_experimental_audit_content_v1(forged_audit)
    with pytest.raises(
        runner.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_multitable_hierarchical_experimental_audit_replay_v1(
            forged_audit, **replay_args
        )

    forged_sweep = copy.deepcopy(sweep)
    forged_sweep["specs"]["schema_binding"]["value"]["family_root_report_norm_id"] = 999999
    forged_sweep["specs"]["schema_binding"]["sha256"] = runner.canonical_json_sha256_v1(
        forged_sweep["specs"]["schema_binding"]["value"]
    )
    sweep_material = {key: value for key, value in forged_sweep.items() if key != "sweep_id"}
    forged_sweep["sweep_id"] = "gjfafsv1:sweep:" + runner.canonical_json_sha256_v1(sweep_material)
    with pytest.raises(
        runner.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error,
        match="caller and embedded compiled specs differ",
    ):
        runner.validate_multitable_hierarchical_experimental_audit_replay_v1(
            audit,
            **{
                **replay_args,
                "sweep": forged_sweep,
                "indexed_query_evidence": forged_sweep["indexed_query_evidence"],
                "trials": forged_sweep["trials"],
            },
        )


def test_interbank_funding_release_profiles_bind_base_and_repaired_frontiers() -> None:
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        _family_spec("tm-interbank-funding-topology-v1.json"),
        _family_spec("tm-interbank-funding-evaluation-v1.json"),
        _family_spec("tm-interbank-funding-schema-binding-v1.json"),
    )

    base = runner._release_profile(
        compiled,
        selected_page_json_frontier_sha256=(runner.PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256),
    )
    assert base["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 1613,
        "not_observed_count": 0,
        "ready_count": 137,
        "unresolved_count": 3,
    }

    repaired = runner._release_profile(
        compiled,
        selected_page_json_frontier_sha256=(
            runner.PINNED_INTERBANK_FUNDING_EFFECTIVE_PAGE_JSON_FRONTIER_SHA256
        ),
    )
    assert repaired["selected_page_json_frontier_sha256"] == (
        "610b72858f2417c9da1afd7fefb02e195243639e6600d593ba8360b659475349"
    )
    assert repaired["sweep_metrics"] == {
        "document_count": 140,
        "mapping_count": 1652,
        "not_observed_count": 0,
        "ready_count": 140,
        "unresolved_count": 0,
    }
    assert repaired["axis_counts"] == {
        "clusters": 140,
        "equations": 868,
        "historical_comparator": 103,
        "mappings": 1652,
    }

    with pytest.raises(
        runner.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error,
        match="release frontier is not pinned",
    ):
        runner._release_profile(
            compiled,
            selected_page_json_frontier_sha256="0" * 64,
        )
