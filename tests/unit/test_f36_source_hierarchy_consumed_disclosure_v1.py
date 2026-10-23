"""Synthetic coverage proofs; no actual PDF, database or financial admission."""

from __future__ import annotations

import copy

import pytest
import test_f36_primary_witness_public_integration_v1 as witness_fixture
from test_gemini_json_operating_expense_family_v1 import (
    VERSION_ID,
    _base_rows,
    _operating_page,
    _row,
    _source_row_coverage_inputs,
)

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1 as digest

PUBLICATION = "Chi xuất bản tài liệu, quảng cáo"
PARENT = "Chi phí hoạt động khác"
SIBLING = "Chi phí dịch vụ tư vấn"
ACCOUNTED = "ACCOUNTED_SOURCE_HIERARCHY_CONSUMED_DISCLOSURE"


def _fixture(mutate=None):
    rows = _base_rows()
    position = len(rows) - 3
    rows[position:position] = [
        _row(PARENT, "10", "12"),
        _row("Trong đó:", None, None, kind="GROUP", path=[PARENT, "Trong đó:"]),
        _row(PUBLICATION, "4", "5", path=[PARENT, "Trong đó:", PUBLICATION]),
        _row(SIBLING, "6", "7", path=[PARENT, "Trong đó:", SIBLING]),
    ]
    rows[-1]["values_exact"] = ["93", "78"]
    page = _operating_page(rows)
    if mutate is not None:
        mutate(page, position)
    indexed, trials, pages, compiled = _source_row_coverage_inputs(page)
    return indexed, trials, pages, compiled, position + 3


def _coverage(fixture):
    indexed, trials, pages, compiled, _ordinal = fixture
    return family.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=pages,
        compiled_specs=compiled, fail_on_violation=False,
    )


def _publication(coverage, ordinal):
    return next(item for item in coverage["raw_target_like_row_axis"] if item["row_ordinal"] == ordinal)


def test_public_coverage_accounts_only_the_literal_and_preserves_every_financial_output():
    fixture = _fixture()
    indexed, trials, pages, compiled, ordinal = fixture
    assert trials[0]["status"] == family.READY
    before = copy.deepcopy((indexed, trials, pages, compiled))
    coverage = _coverage(fixture)
    row = _publication(coverage, ordinal)
    assert row["coverage"] == ACCOUNTED
    assert row["role"] is None and row["report_norm_id"] is None
    assert row["values_exact"] == ["4", "5"]
    proof, = row["evidence"]["source_hierarchy_consumed_disclosure_axis"]
    assert proof["parent_row_exact"]["label_exact"] == PARENT
    assert proof["wrapper_row_exact"]["values_exact"] == [None, None]
    assert proof["original_row_exact"]["label_exact"] == PUBLICATION
    assert proof["nested_equation"]["status"] == proof["root_equation"]["status"] == "EXACT"
    assert not proof["financial_mapping_permission_granted"]
    assert not proof["operand_or_role_permission_granted"] and not proof["source_modified"]
    assert proof["receipt_id"] == "gjoefav1:source-hierarchy-disclosure:" + digest({
        key: value for key, value in proof.items() if key != "receipt_id"
    })
    assert coverage["violation_count"] == 0
    assert all("source_hierarchy_consumed_disclosure_axis" not in item.get("evidence", {})
               for item in coverage["raw_target_like_row_axis"] if item["row_ordinal"] != ordinal)
    assert (indexed, trials, pages, compiled) == before
    family.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=pages, compiled_specs=compiled,
    )
    assert family.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=pages, compiled_specs=compiled,
    ) == coverage


def test_unreviewed_sibling_is_not_exempted_by_the_same_exact_hierarchy_equation():
    def mutate(page, position):
        row = page["sections"][0]["tables"][0]["rows"][position + 3]
        row["label_exact"] = "Chi tiết chi phí hỗ trợ"
        row["hierarchy_path_exact"][-1] = row["label_exact"]

    fixture = _fixture(mutate)
    assert fixture[1][0]["status"] == family.READY
    coverage = _coverage(fixture)
    assert _publication(coverage, fixture[-1])["coverage"] == ACCOUNTED
    sibling = next(item for item in coverage["violation_axis"] if item["label_exact"] == "Chi tiết chi phí hỗ trợ")
    assert sibling["coverage"] == "VIOLATION_UNCLASSIFIED_VISIBLE_OPERATING_EXPENSE_ROW"
    indexed, trials, pages, compiled, _ordinal = fixture
    with pytest.raises(family.GeminiJsonOperatingExpenseFamilyV1Error, match="coverage has"):
        family.build_operating_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed, trials=trials, page_json_by_document=pages, compiled_specs=compiled,
        )


def test_even_an_existing_closed_dash_equation_does_not_enter_the_numeric_only_disclosure_policy():
    def mutate(page, position):
        rows = page["sections"][0]["tables"][0]["rows"]
        rows[position + 2]["values_exact"] = ["-", "-"]
        rows[position + 3]["values_exact"] = ["10", "12"]

    fixture = _fixture(mutate)
    assert fixture[1][0]["status"] == family.READY
    row = _publication(_coverage(fixture), fixture[-1])
    assert row["coverage"] == "VIOLATION_UNCLASSIFIED_VISIBLE_OPERATING_EXPENSE_ROW"
    assert "source_hierarchy_consumed_disclosure_axis" not in row["evidence"]


def test_eligible_candidate_is_replayed_once_and_returned_proof_cannot_poison_later_calls(monkeypatch):
    fixture = _fixture()
    original = family.validate_gemini_json_operating_expense_candidate_replay_v1
    calls = []

    def observed(*args, **kwargs):
        calls.append(kwargs["regions"])
        return original(*args, **kwargs)

    monkeypatch.setattr(family, "validate_gemini_json_operating_expense_candidate_replay_v1", observed)
    first = _coverage(fixture)
    assert len(calls) == 1
    proof = _publication(first, fixture[-1])["evidence"]["source_hierarchy_consumed_disclosure_axis"][0]
    proof["parent_row_exact"]["values_exact"] = ["999", "999"]
    second = _coverage(fixture)
    assert len(calls) == 2
    assert _publication(second, fixture[-1])["evidence"]["source_hierarchy_consumed_disclosure_axis"][0][
        "parent_row_exact"]["values_exact"] == ["10", "12"]


@pytest.mark.parametrize("suffix", [" và chi phí khác", " (Thuyết minh 15)", " theo tỷ lệ"])
def test_unreviewed_whole_meanings_do_not_gain_disclosure_permission(suffix):
    def mutate(page, position):
        row = page["sections"][0]["tables"][0]["rows"][position + 2]
        row["label_exact"] += suffix
        row["hierarchy_path_exact"][-1] = row["label_exact"]

    fixture = _fixture(mutate)
    row = _publication(_coverage(fixture), fixture[-1])
    assert row["coverage"].startswith("VIOLATION_")
    assert "source_hierarchy_consumed_disclosure_axis" not in row["evidence"]


@pytest.mark.parametrize("attack", [
    "wrong-parent", "wrapper-kind", "wrapper-value", "wrapper-missing-edge", "wrapper-later",
    "foreign-prefix", "unit", "lane", "changed-value", "dash", "null", "open-continuation",
])
def test_unsupported_source_structure_or_numeric_chain_remains_unaccounted(attack):
    def mutate(page, position):
        table = page["sections"][0]["tables"][0]
        rows = table["rows"]
        parent, wrapper, leaf = rows[position:position + 3]
        if attack == "wrong-parent":
            parent["label_exact"] = "Chi cho hoạt động quản lý công vụ"
            for row in rows[position:position + 4]:
                row["hierarchy_path_exact"][0] = parent["label_exact"]
        elif attack == "wrapper-kind":
            wrapper["row_kind"] = "ITEM"
        elif attack == "wrapper-value":
            wrapper["values_exact"][0] = "0"
        elif attack == "wrapper-missing-edge":
            wrapper["hierarchy_path_exact"] = ["Trong đó:"]
        elif attack == "wrapper-later":
            rows[position + 1], rows[position + 2] = rows[position + 2], rows[position + 1]
        elif attack == "foreign-prefix":
            leaf["hierarchy_path_exact"] = ["Chủ thể khác", *leaf["hierarchy_path_exact"]]
        elif attack == "unit":
            table["unit_exact"] = "đơn vị chưa được chứng minh"
        elif attack == "lane":
            table["columns"][1]["header_path_exact"] = copy.deepcopy(table["columns"][0]["header_path_exact"])
        elif attack == "open-continuation":
            table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
        else:
            leaf["values_exact"][0] = {"changed-value": "40", "dash": "-", "null": None}[attack]

    fixture = _fixture(mutate)
    coverage = _coverage(fixture)
    assert not any("source_hierarchy_consumed_disclosure_axis" in item.get("evidence", {})
                   for item in coverage["raw_target_like_row_axis"])
    assert coverage["violation_count"] > 0


@pytest.mark.parametrize("attack", ["equation-value", "equation-ref", "root-removed", "source-changed"])
def test_caller_resealed_closure_or_mapping_cannot_replace_fresh_source_proof(attack):
    fixture = _fixture()
    indexed, trials, pages, _compiled, _ordinal = fixture
    trial = trials[0]
    candidate = trial["candidates"][0]
    if attack == "root-removed":
        trial["mappings"] = [item for item in trial["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"]
    elif attack == "source-changed":
        rows = pages[1][VERSION_ID]["sections"][0]["tables"][0]["rows"]
        next(row for row in rows if row["label_exact"] == PUBLICATION)["values_exact"][0] = "999"
    else:
        equation = next(item for item in candidate["closure_receipt"]["equations"]
                        if any(ref["label_exact"] == PUBLICATION
                               for refs in item["component_source_refs"] for ref in refs))
        if attack == "equation-value":
            equation["component_sums"][0] += 1
            equation["result_coefficients"][0] += 1
        else:
            equation["component_source_refs"][0][0]["row_ordinal"] += 1
        equation["equation_id"] = equation["equation_id"].rsplit(":", 1)[0] + ":" + digest({
            key: value for key, value in equation.items() if key != "equation_id"
        })
        candidate["candidate_id"] = candidate["candidate_id"].rsplit(":", 1)[0] + ":" + digest({
            key: value for key, value in candidate.items() if key != "candidate_id"
        })
        trial["selected_candidate_id"] = candidate["candidate_id"]
    with pytest.raises(family.GeminiJsonOperatingExpenseFamilyV1Error, match="replay drifted|selected mappings differ"):
        _coverage(fixture)
    assert indexed["selected_document_axis"][0]["source_sha256"] == trial["source_sha256"]


def test_unrelated_candidate_emits_no_proof_and_does_not_trigger_extra_replay(monkeypatch):
    indexed, trials, pages, compiled = _source_row_coverage_inputs(_operating_page())

    def unexpected(*_args, **_kwargs):
        raise AssertionError("unrelated candidate must not be replayed for this policy")

    monkeypatch.setattr(family, "validate_gemini_json_operating_expense_candidate_replay_v1", unexpected)
    coverage = family.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=pages, compiled_specs=compiled,
    )
    assert not any("source_hierarchy_consumed_disclosure_axis" in item.get("evidence", {})
                   for item in coverage["raw_target_like_row_axis"])


@pytest.mark.parametrize("mode", ["live", "missing", "closed"])
def test_actual_live_primary_capability_is_forwarded_to_disclosure_replay(tmp_path, monkeypatch, mode):
    # Only the synthetic input-data factory is replaced. The existing real
    # SQLite ingestion, selected-source query, PDF render/crops, admission and
    # public financial functions run unchanged in the future unit-test lease.
    note = copy.deepcopy(_fixture()[2][1][VERSION_ID])
    rows = note["sections"][0]["tables"][0]["rows"]
    rows[-2]["values_exact"] = ["(7)", "(10)"]
    rows[-1]["values_exact"] = ["83", "66"]
    with monkeypatch.context() as input_data:
        input_data.setattr(witness_fixture.fixture, "_operating_page", lambda: copy.deepcopy(note))
        case = witness_fixture._case(tmp_path)
    cap = witness_fixture._auth(case)
    closed = False
    try:
        indexed, trials = witness_fixture._build(case, cap)
        assert trials[0]["status"] == family.READY
        before = copy.deepcopy((indexed, trials, case.pages))
        original = family.validate_gemini_json_operating_expense_candidate_replay_v1
        calls = []

        def observed(*args, **kwargs):
            calls.append(kwargs.get("primary_witness_admission"))
            return original(*args, **kwargs)

        monkeypatch.setattr(family, "validate_gemini_json_operating_expense_candidate_replay_v1", observed)
        if mode == "closed":
            cap.close()
            closed = True

        def coverage():
            return family.build_operating_expense_source_row_coverage_receipt_v1(
                indexed_query_evidence=indexed, trials=trials, page_json_by_document=case.pages,
                compiled_specs=case.compiled, primary_witness_admission=None if mode == "missing" else cap,
                fail_on_violation=False,
            )

        if mode == "live":
            result = coverage()
            row = next(item for item in result["raw_target_like_row_axis"] if item["label_exact"] == PUBLICATION)
            assert row["coverage"] == ACCOUNTED
            assert calls == [cap]
        else:
            with pytest.raises(witness_fixture.admission.PrimaryWitnessAdmissionError):
                coverage()
            assert calls == []
        assert (indexed, trials, case.pages) == before
    finally:
        if not closed:
            cap.close()
