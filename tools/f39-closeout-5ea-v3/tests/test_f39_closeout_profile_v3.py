"""UNRUN synthetic metadata/protocol controls, never corpus/PDF acceptance.

Root must first capture this entire draft in its own reviewed Git branch, then
run only that fresh Linux clone under the serialized Python 3.12 test lease.
These tests import external stdlib tools, never project producer modules. A
positive profile-contract test is not registration or approval of that profile.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def adapter():
    return _load("adapter-v3/f39_local_pdf_audit_adapter_v3.py", "_synthetic_f39_audit_v3")


def _ref(tmp_path, name, digit="a"):
    return {"path": str(tmp_path / name), "sha256": digit * 64, "size_bytes": 1}


def _profile(adapter, tmp_path):
    # Deliberately invented UNIT metadata. No actual new FULL metric or hash is
    # guessed here, and production APPROVED_RUN_PROFILE_REF remains None.
    run_refs = {name: {"sha256": digit * 64, "size_bytes": 1}
                for name, digit in (("sweep", "1"), ("audit", "2"), ("results", "3"))}
    run_refs["corpus_index"] = _ref(tmp_path, "synthetic-index.json", "4")
    return {
        "format_version": "F39_CLOSEOUT_5EA_APPROVED_FULL_RUN_PROFILE_V3",
        "reviewed_and_approved": True, "resolved": True,
        "expected_head": adapter.BASE_COMMIT, "family_id": "INCOME_TAX",
        "family_run_id": "gjfafstorev1:run:" + "5" * 64, "sweep_id": "SYNTHETIC_UNIT_SWEEP_ONLY",
        "expected_refs": run_refs,
        "metrics": {"document_count": 271, "ready_count": 0, "not_observed_count": 0,
                    "unresolved_count": 271, "mapping_count": 0},
        "selected_page_count": 14945,
        "full_run_receipt_ref": _ref(tmp_path, "synthetic-full-proof.json", "6"),
        "synthetic_gate_receipt_ref": _ref(tmp_path, "synthetic-gate.json", "7"),
        "gate_reader_ref": _ref(tmp_path, "synthetic-reader.py", "8"),
        "full_run_receipt_bindings": {key: [key] for key in
            ("head", "run_id", "sweep_sha256", "audit_sha256", "results_sha256", "exit_status")},
        "negative_admission_axis_sha256": "9" * 64,
        "retained_hold_bindings": {
            ordinal: {"index_document_sha256": "a" * 64, "trial_reasons": [rule["reason"]]}
            for ordinal, rule in adapter.RETAINED_HOLD_RULES.items()
        },
    }


def _full_proof(adapter, profile):
    return {"head": adapter.BASE_COMMIT, "run_id": profile["family_run_id"], "exit_status": 0,
            **{name + "_sha256": profile["expected_refs"][name]["sha256"]
               for name in ("sweep", "audit", "results")}}


def test_unregistered_profile_cannot_start_new_full_admission(adapter, tmp_path):
    assert adapter.APPROVED_RUN_PROFILE_REF is None
    with ExitStack() as guards, pytest.raises(adapter.F39AuditError, match="READY_FOR_PROFILE_BINDING"):
        adapter.read_approved_run_profile_v3(guards=guards, repo=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_valid_synthetic_profile_contract_does_not_register_or_modify_it(adapter, tmp_path):
    profile = _profile(adapter, tmp_path)
    original = copy.deepcopy(profile)
    validated = adapter.validate_run_profile_contract_v3(profile)
    assert validated == original and profile == original
    validated["metrics"]["ready_count"] = 999
    assert profile == original
    assert adapter.APPROVED_RUN_PROFILE_REF is None


@pytest.mark.parametrize("mutation", ["unreviewed", "unresolved", "old_head", "old_sweep", "subset",
    "bad_sum", "missing_hold", "wrong_reason", "missing_gate", "missing_proof_binding", "bool_size"])
def test_profile_contract_rejects_unapproved_old_incomplete_or_wrongly_typed_metadata(adapter, tmp_path, mutation):
    profile = _profile(adapter, tmp_path)
    if mutation == "unreviewed":
        profile["reviewed_and_approved"] = False
    elif mutation == "unresolved":
        profile["resolved"] = False
    elif mutation == "old_head":
        profile["expected_head"] = "11380ed935a84b64d72c4e7d367f0451ce0e62e0"
    elif mutation == "old_sweep":
        profile["expected_refs"]["sweep"]["sha256"] = next(iter(adapter.REJECTED_SWEEPS))
    elif mutation == "subset":
        profile["metrics"]["document_count"] = 204
    elif mutation == "bad_sum":
        profile["metrics"]["ready_count"] = 1
    elif mutation == "missing_hold":
        del profile["retained_hold_bindings"]["225"]
    elif mutation == "wrong_reason":
        profile["retained_hold_bindings"]["110"]["trial_reasons"] = ["GENUINE_SOURCE_AMBIGUITY"]
    elif mutation == "missing_gate":
        profile["synthetic_gate_receipt_ref"] = None
    elif mutation == "missing_proof_binding":
        del profile["full_run_receipt_bindings"]["head"]
    else:
        profile["expected_refs"]["results"]["size_bytes"] = True
    with pytest.raises(adapter.F39AuditError):
        adapter.validate_run_profile_contract_v3(profile)


def test_actual_full_receipt_bindings_require_exact_code_run_artifacts_and_integer_exit_zero(adapter, tmp_path):
    profile = _profile(adapter, tmp_path)
    proof = _full_proof(adapter, profile)
    adapter.validate_full_run_receipt_bindings_v3(profile, proof)
    for key in proof:
        changed = copy.deepcopy(proof)
        changed[key] = False if key == "exit_status" else "wrong-new-code-or-run-proof"
        with pytest.raises(adapter.F39AuditError, match="completion receipt"):
            adapter.validate_full_run_receipt_bindings_v3(profile, changed)
    del proof["audit_sha256"]
    with pytest.raises(adapter.F39AuditError, match="pointer"):
        adapter.validate_full_run_receipt_bindings_v3(profile, proof)


@pytest.mark.parametrize("ordinal", [110, 225])
def test_both_required_holds_bind_source_document_and_preserve_exact_unresolved_reasons(adapter, tmp_path, ordinal):
    profile = _profile(adapter, tmp_path)
    document = {"unit_fixture": True, "source_ordinal": ordinal}
    rule = adapter.RETAINED_HOLD_RULES[str(ordinal)]
    profile["retained_hold_bindings"][str(ordinal)]["index_document_sha256"] = adapter.digest(document)
    summary = {"document_ordinal": ordinal, "status": adapter.UNRESOLVED, "mapping_count": 0,
               "selected_candidate_id": None, "reasons": [rule["reason"]]}
    adapter.validate_retained_hold_trial_v3(profile, summary, document)
    for field, value in (("status", adapter.READY), ("mapping_count", 1),
                         ("selected_candidate_id", "unit:accepted"), ("reasons", ["issuer ambiguity"])):
        changed = {**summary, field: value}
        with pytest.raises(adapter.F39AuditError, match="HOLD"):
            adapter.validate_retained_hold_trial_v3(profile, changed, document)
    with pytest.raises(adapter.F39AuditError, match="source-bound"):
        adapter.validate_retained_hold_trial_v3(profile, summary, {**document, "source_ordinal": 1})


def _axis_case(adapter, tmp_path):
    profile = _profile(adapter, tmp_path)
    documents = [{"source_sha256": f"{ordinal:064x}", "relative_path": f"unit-{ordinal}.pdf",
                  "source_size_bytes": 1} for ordinal in range(1, 272)]
    source = documents[109]
    material = {
        "source_pdf": {"source_sha256": source["source_sha256"], "source_logical_name": source["relative_path"], "source_size_bytes": 1},
        "source_observation_receipt": _production_source_receipt(
            {"source_locator": {"document_ordinal": 110, "source_sha256": source["source_sha256"]}}, "gjitflabelv1:source:"),
        "status": "PASS_FRESH_PDF_PIXELS_REGISTERED_MANUAL_NEGATIVE_REVIEW_NOT_FINANCIAL_ACCEPTANCE",
        "text_layer_claimed": False, "source_values_changed": False,
    }
    axis = [[] for _ in range(271)]
    axis[109] = [_production_source_receipt(material, "gjitflabelv1:pdf-auth:")]
    profile["negative_admission_axis_sha256"] = adapter.digest(axis)
    return profile, {"documents": documents}, axis


def _production_source_receipt(material, prefix, *, final_lf=True):
    # Independent exact grammar of contracts_v1 at both53b6/5ea Git blob
    # 74ff2f1c07b15a834e39cf895d92bb09c3ea95d9, lines433-451.
    raw = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    raw = (raw + ("\n" if final_lf else "")).encode("utf-8")
    return {**material, "receipt_id": prefix + sha256(raw).hexdigest()}


@pytest.mark.parametrize("target", ["outer_pdf", "nested_source"])
def test_exact_production_lf_source_seals_reject_no_lf_reseal_without_fallback(adapter, tmp_path, target):
    profile, index, axis = _axis_case(adapter, tmp_path)
    if target == "outer_pdf":
        material = {key: value for key, value in axis[109][0].items() if key != "receipt_id"}
        axis[109][0] = _production_source_receipt(material, "gjitflabelv1:pdf-auth:", final_lf=False)
    else:
        material = {key: value for key, value in axis[109][0]["source_observation_receipt"].items() if key != "receipt_id"}
        axis[109][0]["source_observation_receipt"] = _production_source_receipt(material, "gjitflabelv1:source:", final_lf=False)
        outer = {key: value for key, value in axis[109][0].items() if key != "receipt_id"}
        axis[109][0] = _production_source_receipt(outer, "gjitflabelv1:pdf-auth:")
    profile["negative_admission_axis_sha256"] = adapter.digest(axis)
    with pytest.raises(adapter.F39AuditError, match="production source receipt"):
        adapter.validate_negative_admission_axis_v3(
            {"registered_source_label_discrepancy_admission_axis": axis}, index, profile)


def test_negative_axis_protocol_keeps_every_empty_slot_without_claiming_real_pixel_proof(adapter, tmp_path):
    profile, index, axis = _axis_case(adapter, tmp_path)
    # This checks transport metadata, not an independently rendered PDF. The
    # production cold factory still must reproduce fresh registered pixel auth.
    validated = adapter.validate_negative_admission_axis_v3(
        {"registered_source_label_discrepancy_admission_axis": axis}, index, profile)
    assert validated == axis and len(validated) == 271
    assert sum(bool(entry) for entry in validated) == 1
    axis[109][0]["source_pdf"]["source_size_bytes"] = 999
    assert validated[109][0]["source_pdf"]["source_size_bytes"] == 1


@pytest.mark.parametrize("mutation", ["missing", "compact", "reordered", "drift", "wrong_document", "boolean_acceptance"])
def test_negative_axis_rejects_missing_compact_changed_or_foreign_warm_authority(adapter, tmp_path, mutation):
    profile, index, axis = _axis_case(adapter, tmp_path)
    if mutation == "missing":
        axis = None
    elif mutation == "compact":
        axis = [entry for entry in axis if entry]
    elif mutation == "reordered":
        axis.reverse()
    elif mutation == "drift":
        axis[109][0]["source_pdf"]["source_size_bytes"] = 2
    else:
        material = {key: value for key, value in axis[109][0].items() if key != "receipt_id"}
        if mutation == "wrong_document":
            nested = {key: value for key, value in material["source_observation_receipt"].items() if key != "receipt_id"}
            nested["source_locator"]["document_ordinal"] = 1
            material["source_observation_receipt"] = _production_source_receipt(nested, "gjitflabelv1:source:")
        else:
            material["source_values_changed"] = True
        axis[109] = [_production_source_receipt(material, "gjitflabelv1:pdf-auth:")]
        # Simulates a changed owner profile's checksum only to exercise the
        # independent source/boundary checks. It does not register that profile.
        profile["negative_admission_axis_sha256"] = adapter.digest(axis)
    with pytest.raises(adapter.F39AuditError):
        adapter.validate_negative_admission_axis_v3(
            {"registered_source_label_discrepancy_admission_axis": axis}, index, profile)


def test_cold_factory_receives_complete_snapshot_including_unrelated_empty_slots(adapter, tmp_path):
    _profile_value, _index, axis = _axis_case(adapter, tmp_path)
    captured = {}
    census = [{"synthetic_census": 1}]
    caption = [[], [{"synthetic_caption": 1}]]
    sentinel = object()

    def factory(*, expected_source_label_discrepancy_axis, **options):
        captured.update(options, negative=expected_source_label_discrepancy_axis)
        return sentinel

    assert adapter.bind_cold_replay_v3(factory, negative_admission_axis=axis,
        expected_census_refs=census, expected_caption_admission_axis=caption) is sentinel
    assert captured["negative"] == axis and len(captured["negative"]) == 271
    assert captured["expected_census_refs"] is census and captured["expected_caption_admission_axis"] is caption
    axis.pop()
    axis[109][0]["source_pdf"]["source_size_bytes"] = 999
    assert len(captured["negative"]) == 271
    assert captured["negative"][109][0]["source_pdf"]["source_size_bytes"] == 1


@pytest.mark.parametrize("axis", [None, [], [[]], [None] * 271])
def test_cold_factory_never_gets_default_or_incomplete_negative_axis(adapter, axis):
    def never_called(**_kwargs):
        raise AssertionError("must fail before constructing the cold closure")

    with pytest.raises(adapter.F39AuditError, match="Never compact"):
        adapter.bind_cold_replay_v3(never_called, negative_admission_axis=axis)


def test_negative_printed_label_review_is_allowed_only_as_explicit_unmapped_hold(adapter):
    row = {"document_ordinal": 110, "original_row_ordinal": 17, "mapping_citations": [],
           "locator": {"source_sha256": adapter.NEGATIVE_SOURCE_SHA256, "page_json_version_id": adapter.NEGATIVE_VID,
                       "physical_page": 6, "section_id": "s1", "table_id": "t1"}}
    assert adapter.known_findings_for_row(row) == [adapter.NEGATIVE_ROW_FINDING]
    review = {"reviewer": "SYNTHETIC UNIT OWNER", "reviewed_at_utc": "2026-10-26T00:00:00Z",
              "evidence": "Synthetic negative row test only; no PDF was reviewed.",
              "all_listed_source_rows_or_pages_reviewed": True, "printed_counterpart_verified": False,
              "printed_label_discrepancy_documented": True, "raw_sign_unit_blank_preserved": True}
    adapter.review_is_complete(review, allow_known_unprinted=True)
    with pytest.raises(adapter.F39AuditError, match="Printed row counterpart"):
        adapter.review_is_complete(review)
    row["locator"]["physical_page"] = 7
    assert adapter.known_findings_for_row(row) == []


def test_exclusive_audit_write_never_replaces_owner_file(adapter, tmp_path):
    path = tmp_path / "existing-owner-receipt.json"
    path.write_bytes(b"owner-original")
    with pytest.raises(FileExistsError):
        adapter.write_once(path, b"replacement")
    assert path.read_bytes() == b"owner-original"


@pytest.mark.skipif(sys.platform != "linux", reason="promoter uses Linux held-descriptor primitives")
def test_promoter_held_input_rejects_post_read_mutation_without_writing_store(tmp_path):
    promoter = _load("promotion-v3/promote_f39_official_v3.py", "_synthetic_f39_promoter_v3")
    path = tmp_path / "unit-input.json"
    path.write_bytes(b"old")
    reference = {"path": str(path), "sha256": sha256(b"old").hexdigest(), "size_bytes": 3}
    held = promoter.Held()
    try:
        assert held.read(reference, 1024) == b"old"
        path.write_bytes(b"new")
        with pytest.raises(RuntimeError, match="Final input drift"):
            held.validate()
    finally:
        held.close()
    assert sorted(child.name for child in tmp_path.iterdir()) == ["unit-input.json"]
