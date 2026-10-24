"""UNRUN F36 batch authority tests using real private SQLite/PDF witness fixtures.

Only the private authority dispatch is spied/replaced for differential checks;
all source authentication, pixel checks, projections and financial APIs are real.
No actual corpus/source PDF or provider is used.
"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
import test_f36_primary_witness_public_integration_v1 as protocol

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation import (
    gemini_json_operating_expense_primary_witness_admission_v1 as admission,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, same_typed_json_v1


def _mixed_case(tmp_path):
    cases = []
    for number, variant in enumerate(("READY", "READY", "PERIOD_HOLD", "NOT_OBSERVED"), 1):
        directory = tmp_path / str(number)
        directory.mkdir()
        cases.append(protocol._case(directory, variant, name=f"batch-{number}.pdf"))
    declared = cases[0]
    documents, axis, pages = [], [], {}
    for ordinal, case in enumerate(cases, 1):
        document = deepcopy(case.base["selected_document_axis"][0])
        document["document_ordinal"] = ordinal
        documents.append(document)
        for original in case.base["selected_page_axis"]:
            selected = deepcopy(original)
            selected["document_ordinal"] = ordinal
            axis.append(selected)
        pages[ordinal] = case.pages[1]
    base = family._fresh_original_primary_base_v1(
        evidence={"selected_document_axis": documents, "selected_page_axis": axis},
        pages=pages, compiled_specs=declared.compiled)
    return SimpleNamespace(**{**vars(declared), "base": base, "pages": pages,
        "index": {"documents": [case.index["documents"][0] for case in cases]}})


def _run(c, cap):
    return family._admitted_primary_run_v1(
        evidence=c.base, pages=c.pages, compiled_specs=c.compiled, admission=cap)


def _page_snapshot(pages):
    return [[ordinal, bundle] for ordinal, bundle in pages.items()]


def _per_document_reference(self, *, pages, documents, selected_page_axis, compiled_specs):
    """Actual pre-batch public projection, including its per-document full checks."""
    self.require_run(documents, selected_page_axis, compiled_specs)
    private, facts = {}, {}
    for document in documents:
        ordinal = document["document_ordinal"]
        private[ordinal], facts[ordinal] = self.project(
            pages=pages[ordinal], document=document,
            selected_page_axis=[p for p in selected_page_axis if p["document_ordinal"] == ordinal],
            compiled_specs=compiled_specs)
    return private, facts


def _public_outputs(c, cap):
    indexed, trials = protocol._build(c, cap)
    replay = family.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=c.pages,
        compiled_specs=c.compiled, primary_witness_admission=cap)
    coverage = family.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=c.pages,
        compiled_specs=c.compiled, primary_witness_admission=cap, fail_on_violation=False)
    observation = protocol.runner.validate_source_observation_mapping_contract_v1({"trials": trials})
    return [indexed, trials, replay, coverage, observation]


def test_batch_authority_reads_are_two_boundaries_and_public_project_stays_per_call(tmp_path, monkeypatch):
    c = _mixed_case(tmp_path)
    before = canonical_json_bytes_v1([_page_snapshot(c.pages), c.compiled])
    cap = protocol._auth(c)
    try:
        calls, original_read = [], admission._read
        def read(path):
            calls.append(str(path))
            return original_read(path)
        with monkeypatch.context() as spy:
            spy.setattr(admission, "_read", read)
            reference = _per_document_reference(cap, pages=c.pages,
                documents=c.base["selected_document_axis"], selected_page_axis=c.base["selected_page_axis"],
                compiled_specs=c.compiled)
            authorities = [ref["path"] for ref in cap._data["authority_refs"]]
            assert calls == authorities * 4
            calls.clear()
            private, facts = _run(c, cap)
            assert calls == authorities * 2
        assert same_typed_json_v1(private, reference[0])
        assert same_typed_json_v1(facts, reference[1])
        assert private[1] is not c.pages[1]
        assert all(private[n] is c.pages[n] for n in (2, 3, 4))
        assert list(facts) == [1, 2, 3, 4]
        assert len(facts[1]["projection_receipts"]) == len(facts[1]["pixel_verification_receipts"]) == 3
        assert all(facts[n]["projection_receipts"] == facts[n]["pixel_verification_receipts"] == []
                   for n in (2, 3, 4))
        assert canonical_json_bytes_v1([_page_snapshot(c.pages), c.compiled]) == before
    finally:
        cap.close()


def test_batch_full_public_outputs_are_typed_equal_to_per_document_reference(tmp_path, monkeypatch):
    c = _mixed_case(tmp_path)
    before = canonical_json_bytes_v1([c.base, _page_snapshot(c.pages), c.compiled])
    cap = protocol._auth(c)
    try:
        with monkeypatch.context() as baseline:
            baseline.setattr(admission.PrimaryWitnessAdmissionV1, "_project_run_v1", _per_document_reference)
            reference = _public_outputs(c, cap)
        actual = _public_outputs(c, cap)
        assert canonical_json_bytes_v1(actual) == canonical_json_bytes_v1(reference)
        indexed, trials, replay, _coverage, observation = actual
        assert [trial["status"] for trial in trials] == [
            protocol.fixture.READY, protocol.fixture.READY,
            protocol.fixture.UNRESOLVED, protocol.fixture.NOT_OBSERVED]
        assert same_typed_json_v1(trials, replay) and observation["violation_count"] == 0
        assert indexed["selected_document_axis"] == c.base["selected_document_axis"]
        assert indexed["selected_page_axis"] == c.base["selected_page_axis"]
        count = protocol.runner._primary_witness_application_receipt_v1(indexed=indexed, compiled=c.compiled)
        assert count["logical_document_application_count"] == 1 and len(count["applied_witness_ids"]) == 3
        assert canonical_json_bytes_v1([c.base, _page_snapshot(c.pages), c.compiled]) == before
    finally:
        cap.close()


@pytest.mark.parametrize("authority", ["pdf", "spec"])
@pytest.mark.parametrize("after_document", [1, 4])
def test_mid_or_final_document_authority_drift_cannot_return_partial_batch(
        tmp_path, monkeypatch, authority, after_document):
    c = _mixed_case(tmp_path)
    cap = protocol._auth(c)
    original = admission.PrimaryWitnessAdmissionV1._project_document_facts_v1
    completed = []
    def project(self, **kwargs):
        result = original(self, **kwargs)
        ordinal = kwargs["document"]["document_ordinal"]
        completed.append(ordinal)
        if ordinal == after_document:
            path = c.pdf if authority == "pdf" else c.path
            path.write_bytes(path.read_bytes() + b"changed after document")
        return result
    with monkeypatch.context() as injection:
        injection.setattr(admission.PrimaryWitnessAdmissionV1, "_project_document_facts_v1", project)
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            _run(c, cap)
    assert completed == list(range(1, after_document + 1))
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        cap.close()


@pytest.mark.parametrize("attack", ["closed", "compiled-policy", "earlier-original", "nonapplicable-original", "page-axis"])
def test_each_document_and_final_original_policy_scope_guards_remain_live(tmp_path, monkeypatch, attack):
    c = _mixed_case(tmp_path)
    cap = protocol._auth(c)
    original = admission.PrimaryWitnessAdmissionV1._project_document_facts_v1
    completed = []
    def project(self, **kwargs):
        result = original(self, **kwargs)
        ordinal = kwargs["document"]["document_ordinal"]
        completed.append(ordinal)
        if ordinal == 1:
            if attack == "closed":
                self.close()
            elif attack == "compiled-policy":
                c.compiled["query_policy"]["batch_test_change"] = True
            elif attack in {"earlier-original", "nonapplicable-original"}:
                target = 1 if attack == "earlier-original" else 2
                next(iter(c.pages[target].values()))["completion"]["uncertainty_exact"].append("changed after admission")
            else:
                c.base["selected_page_axis"][0]["physical_page"] = 999
        return result
    with monkeypatch.context() as injection:
        injection.setattr(admission.PrimaryWitnessAdmissionV1, "_project_document_facts_v1", project)
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            _run(c, cap)
    assert completed and completed[0] == 1
    if attack == "closed":
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            cap.close()
    else:
        cap.close()


@pytest.mark.parametrize("attack", ["missing-document", "extra-document", "document-bool", "page-ordinal-float"])
def test_batch_complete_typed_original_and_selected_axes_are_required(tmp_path, attack):
    c = _mixed_case(tmp_path)
    cap = protocol._auth(c)
    try:
        if attack == "missing-document":
            c.pages.pop(4)
        elif attack == "extra-document":
            c.pages[5] = deepcopy(c.pages[4])
        elif attack == "document-bool":
            c.base["selected_document_axis"][0]["document_ordinal"] = True
        else:
            c.base["selected_page_axis"][0]["selected_page_ordinal"] = 1.0
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            _run(c, cap)
    finally:
        cap.close()


def test_projection_exception_still_runs_final_authority_barrier_without_leaking_batch_state(tmp_path, monkeypatch):
    c = _mixed_case(tmp_path)
    cap = protocol._auth(c)
    calls, original_read = [], admission._read
    class ProjectionStopped(ValueError):
        pass
    def read(path):
        calls.append(str(path))
        return original_read(path)
    def stop(self, **kwargs):
        raise ProjectionStopped("private projection failed")
    try:
        with monkeypatch.context() as failure:
            failure.setattr(admission, "_read", read)
            failure.setattr(admission.PrimaryWitnessAdmissionV1, "_project_document_facts_v1", stop)
            with pytest.raises(ProjectionStopped):
                _run(c, cap)
        authorities = [ref["path"] for ref in cap._data["authority_refs"]]
        assert calls == authorities * 2
        # No persistent batch flag: the same live capability still performs a fresh complete call.
        private, facts = _run(c, cap)
        assert list(private) == list(facts) == [1, 2, 3, 4]
    finally:
        cap.close()


def test_default_none_paths_are_byte_exact_and_never_enter_batch(tmp_path, monkeypatch):
    c = protocol._case(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("default None must not enter witness batching")
    monkeypatch.setattr(admission.PrimaryWitnessAdmissionV1, "_project_run_v1", forbidden)
    assert same_typed_json_v1(c.old, family.compile_gemini_json_operating_expense_family_specs_v1(*c.specs, None))
    expected = family._without_witness_build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=c.base, page_json_by_document=c.pages, compiled_specs=c.old)
    actual = family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=c.base, page_json_by_document=c.pages, compiled_specs=c.old)
    assert canonical_json_bytes_v1(actual) == canonical_json_bytes_v1(expected)
    assert all(admission.AXIS_FIELD not in d["cluster"] for d in actual["candidate_dispositions"])
