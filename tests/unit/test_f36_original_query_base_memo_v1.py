"""UNRUN source-bound ORIGINAL generic query-base memo tests.

Real synthetic SQLite/PDF witness fixtures, source queries, authentication and
financial APIs are retained. Spies select fresh-vs-memo construction or inject
late faults; no financial result or source-authority return is mocked.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
import test_f36_primary_witness_batch_authority_v1 as batch
import test_f36_primary_witness_public_integration_v1 as protocol

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation import (
    gemini_json_operating_expense_primary_witness_admission_v1 as admission,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)


def _get(c, cap):
    return cap._original_query_base_v1(
        pages=c.pages, documents=c.base["selected_document_axis"],
        selected_page_axis=c.base["selected_page_axis"], compiled_specs=c.compiled)


def test_real_warm_pipeline_constructs_generic_original_base_once_but_recovery_remains_fresh(tmp_path, monkeypatch):
    c = batch._mixed_case(tmp_path)
    original = canonical_json_bytes_v1([c.base, batch._page_snapshot(c.pages), c.compiled])
    reference_cap, memo_cap = protocol._auth(c), protocol._auth(c)
    constructions, recoveries = [], []
    real_build = family._fresh_original_primary_base_v1
    real_recovery = family._without_witness_build_gemini_json_operating_expense_indexed_query_evidence_v1
    real_get = admission.PrimaryWitnessAdmissionV1._original_query_base_v1

    def build(**kwargs):
        constructions.append(None)
        return real_build(**kwargs)

    def recover(**kwargs):
        recoveries.append(None)
        return real_recovery(**kwargs)

    def always_fresh(self, **kwargs):
        # Differential dispatch only; execute the same full source/authority
        # guards and real builder, with no entry retained for the next call.
        object.__setattr__(self, "_original_query_memo_v1", None)
        return real_get(self, **kwargs)

    try:
        with monkeypatch.context() as spy:
            spy.setattr(family, "_fresh_original_primary_base_v1", build)
            spy.setattr(family, "_without_witness_build_gemini_json_operating_expense_indexed_query_evidence_v1", recover)
            with monkeypatch.context() as fresh:
                fresh.setattr(admission.PrimaryWitnessAdmissionV1, "_original_query_base_v1", always_fresh)
                expected = batch._public_outputs(c, reference_cap)
            assert len(constructions) == 3 and len(recoveries) == 4
            constructions.clear()
            recoveries.clear()
            actual = batch._public_outputs(c, memo_cap)
            assert len(constructions) == 1 and len(recoveries) == 4
        assert canonical_json_bytes_v1(actual) == canonical_json_bytes_v1(expected)
        assert [trial["status"] for trial in actual[1]] == [
            protocol.fixture.READY, protocol.fixture.READY,
            protocol.fixture.UNRESOLVED, protocol.fixture.NOT_OBSERVED]
        assert canonical_json_bytes_v1([c.base, batch._page_snapshot(c.pages), c.compiled]) == original
    finally:
        reference_cap.close()
        memo_cap.close()


def test_entry_is_one_immutable_json_payload_outside_per_document_seal_and_each_return_is_detached(tmp_path):
    c = batch._mixed_case(tmp_path)
    cap = protocol._auth(c)
    try:
        data_before = canonical_json_bytes_v1(cap._data)
        first = _get(c, cap)
        entry = cap._original_query_memo_v1
        assert type(entry) is tuple and len(entry) == 3 and type(entry[2]) is bytes and len(entry[2]) > 0
        assert same_typed_json_v1(first, decode_canonical_json_bytes_v1(entry[2]))
        untouched = deepcopy(first)
        first["candidate_dispositions"][0]["cluster"]["reasons"].append("CALLER_OUTPUT_MUTATED")
        second = _get(c, cap)
        assert same_typed_json_v1(second, untouched)
        assert not (protocol._container_ids(first) & protocol._container_ids(second))
        assert cap._original_query_memo_v1 is entry
        assert canonical_json_bytes_v1(cap._data) == data_before
        assert admission.AXIS_FIELD not in entry[2].decode("utf-8")
    finally:
        cap.close()
    assert cap._original_query_memo_v1 is None
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        _get(c, cap)


@pytest.mark.parametrize("ordinal", [1, 2])
def test_self_resealed_caller_indexed_axis_cannot_seed_original_query_memo(tmp_path, ordinal):
    c = batch._mixed_case(tmp_path)
    cap = protocol._auth(c)
    try:
        indexed = family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
            base_indexed_query_evidence=c.base, page_json_by_document=c.pages,
            compiled_specs=c.compiled, primary_witness_admission=cap)
        assert cap._original_query_memo_v1 is None
        bad = deepcopy(indexed)
        fact = bad["candidate_dispositions"][ordinal - 1]["cluster"][admission.AXIS_FIELD]
        fact["pdf_pixels_verified"] = not fact["pdf_pixels_verified"]
        fact["receipt_id"] = "gjoepwa1:document:" + family.canonical_json_sha256_v1(
            {k: v for k, v in fact.items() if k != "receipt_id"})
        bad = protocol._reseal_indexed(bad, c.compiled)
        with pytest.raises(ValueError):
            family.build_gemini_json_operating_expense_trials_v1(
                indexed_query_evidence=bad, page_json_by_document=c.pages,
                compiled_specs=c.compiled, primary_witness_admission=cap)
        memo = decode_canonical_json_bytes_v1(cap._original_query_memo_v1[2])
        assert admission.AXIS_FIELD not in canonical_json_bytes_v1(memo).decode("utf-8")
        expected = family._fresh_original_primary_base_v1(evidence=c.base, pages=c.pages, compiled_specs=c.compiled)
        assert same_typed_json_v1(memo, expected)
    finally:
        cap.close()


def test_real_source_cold_replay_constructs_new_empty_admission_and_independent_original_base(tmp_path, monkeypatch):
    c = protocol._case(tmp_path)
    cap = protocol._auth(c)
    builds, cold_caps = [], []
    real_build = family._fresh_original_primary_base_v1
    real_auth = protocol.runner._authenticate_primary_witness_admission_v1

    def build(**kwargs):
        builds.append(None)
        return real_build(**kwargs)

    def authenticate(**kwargs):
        fresh = real_auth(**kwargs)
        assert fresh is not cap and fresh._original_query_memo_v1 is None
        cold_caps.append(fresh)
        return fresh

    with monkeypatch.context() as spy:
        spy.setattr(family, "_fresh_original_primary_base_v1", build)
        indexed, trials = protocol._build(c, cap)
        family.validate_gemini_json_operating_expense_replay_v1(
            indexed_query_evidence=indexed, trials=trials, page_json_by_document=c.pages,
            compiled_specs=c.compiled, primary_witness_admission=cap)
        assert len(builds) == 1
        cap.close()
        assert cap._original_query_memo_v1 is None
        spy.setattr(protocol.runner, "_authenticate_primary_witness_admission_v1", authenticate)
        replayed = protocol.runner.replay_operating_expense_trials_from_source_v1(
            source_page_database=c.database, selected_page_json_version_ids=tuple(c.versions),
            compiled_specs=protocol.runner.compile_gemini_json_flat_family_specs_v1(*c.specs[:3]),
            indexed_query_evidence=indexed, primary_witness_spec_path=c.path,
            expected_primary_witness_sha256=c.pin, primary_witness_index=c.index,
            primary_witness_pdf_root=c.root)
        assert len(cold_caps) == 1 and len(builds) == 2
        assert same_typed_json_v1(replayed, trials)
        assert cold_caps[0]._original_query_memo_v1 is None
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            _get(c, cold_caps[0])


@pytest.mark.parametrize("primed", [False, True])
@pytest.mark.parametrize("fault", ["foreign-original", "compiled-policy", "pdf", "spec"])
def test_late_miss_or_hit_drift_fails_before_return_and_clears_the_entry(tmp_path, monkeypatch, primed, fault):
    c = batch._mixed_case(tmp_path)
    cap = protocol._auth(c)
    if primed:
        _get(c, cap)
    real_build = family._fresh_original_primary_base_v1
    real_decode = admission.decode_canonical_json_bytes_v1
    changed = []

    def mutate():
        if changed:
            return
        changed.append(fault)
        if fault == "foreign-original":
            next(iter(c.pages[2].values()))["completion"]["uncertainty_exact"].append("LATE_FOREIGN_SOURCE_CHANGE")
        elif fault == "compiled-policy":
            c.compiled["query_policy"]["late_memo_change"] = True
        else:
            path = c.pdf if fault == "pdf" else c.path
            path.write_bytes(path.read_bytes() + b"late memo authority change")

    def build(**kwargs):
        result = real_build(**kwargs)
        mutate()
        return result

    def decode(payload):
        result = real_decode(payload)
        mutate()
        return result

    with monkeypatch.context() as injection:
        if primed:
            injection.setattr(admission, "decode_canonical_json_bytes_v1", decode)
        else:
            injection.setattr(family, "_fresh_original_primary_base_v1", build)
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            _get(c, cap)
    assert changed == [fault] and cap._original_query_memo_v1 is None
    if fault in {"pdf", "spec"}:
        with pytest.raises(admission.PrimaryWitnessAdmissionError):
            cap.close()
    else:
        cap.close()


@pytest.mark.parametrize("fault", ["extra-page", "missing-page", "selected-axis", "document-axis", "closed"])
def test_every_hit_rechecks_full_original_frontier_and_live_scope(tmp_path, fault):
    c = batch._mixed_case(tmp_path)
    cap = protocol._auth(c)
    _get(c, cap)
    if fault == "extra-page":
        c.pages[2]["gfpstorev1:json:" + "f" * 64] = deepcopy(next(iter(c.pages[2].values())))
    elif fault == "missing-page":
        c.pages[2].pop(next(iter(c.pages[2])))
    elif fault == "selected-axis":
        c.base["selected_page_axis"][-1]["selected_page_ordinal"] = 1.0
    elif fault == "document-axis":
        c.base["selected_document_axis"][1]["source_logical_name"] = "changed-source.pdf"
    else:
        cap.close()
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        _get(c, cap)
    assert cap._original_query_memo_v1 is None
    if fault != "closed":
        cap.close()


def test_failed_construction_never_installs_a_half_entry_or_returns_partial_result(tmp_path, monkeypatch):
    c = protocol._case(tmp_path)
    cap = protocol._auth(c)
    real_build, calls = family._fresh_original_primary_base_v1, []
    class ConstructionStopped(ValueError):
        pass
    def stop(**kwargs):
        calls.append(None)
        real_build(**kwargs)
        raise ConstructionStopped("construction completed but publication not allowed")
    try:
        with monkeypatch.context() as failure:
            failure.setattr(family, "_fresh_original_primary_base_v1", stop)
            with pytest.raises(ConstructionStopped):
                _get(c, cap)
        assert len(calls) == 1 and cap._original_query_memo_v1 is None
        result = _get(c, cap)
        assert result["selected_page_axis"] == c.base["selected_page_axis"]
        assert cap._original_query_memo_v1 is not None
    finally:
        cap.close()


def test_default_none_never_uses_original_query_memo(tmp_path, monkeypatch):
    c = protocol._case(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("default None cannot use witness query memo")
    monkeypatch.setattr(admission.PrimaryWitnessAdmissionV1, "_original_query_base_v1", forbidden)
    indexed = family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=c.base, page_json_by_document=c.pages, compiled_specs=c.old)
    actual = family.build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed, page_json_by_document=c.pages, compiled_specs=c.old)
    expected = family._without_witness_build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed, page_json_by_document=c.pages, compiled_specs=c.old)
    assert canonical_json_bytes_v1(actual) == canonical_json_bytes_v1(expected)
