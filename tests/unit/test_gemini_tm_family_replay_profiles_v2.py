"""Synthetic closed-profile controls; no restored data or provider calls.

Happy paths use real admission/source replay. Explicit loader fault seams in
negative controls exercise fail-closed guards, not financial authentication.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_gemini_json_cash_equivalents_adapter_v1 import _page, _rows
from test_gemini_tm_multitable_bridge_v1 import _real_store_request

from bctc_ai.export import gemini_tm_family_replay_profiles_v2 as profiles
from bctc_ai.export import gemini_tm_multitable_bridge_v1 as base


def _unopened_request() -> dict:
    request = dict.fromkeys(base._REQUEST_FIELDS)
    request.update(request_format_version=profiles.REQUEST_FORMAT,
                   source_replay_profile=profiles.F40_PROFILE,
                   source_replay_runner_ref=profiles.approved_f40_runner_ref_v2(),
                   expected_family_id="CASH_EQUIVALENTS", expected_run_kind="EXPERIMENTAL")
    return request


@pytest.mark.parametrize("mutation", ["missing_profile", "missing_version", "wrong_version", "unknown_profile",
                                    "f37", "wrong_family", "wrong_kind", "runner_path", "runner_sha", "runner_bytes", "plugin"])
def test_profile_shape_rejected_before_file_or_sqlite_access(mutation: str, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _unopened_request()
    if mutation == "missing_profile":
        request.pop("source_replay_profile")
    elif mutation == "missing_version":
        request.pop("request_format_version")
    elif mutation == "wrong_version":
        request["request_format_version"] = "V1"
    elif mutation == "unknown_profile":
        request["source_replay_profile"] = "arbitrary.module:callback"
    elif mutation == "f37":
        request["source_replay_profile"] = profiles.F37_PROFILE
    elif mutation == "wrong_family":
        request["expected_family_id"] = "INCOME_TAX"
    elif mutation == "wrong_kind":
        request["expected_run_kind"] = "OFFICIAL"
    elif mutation == "runner_path":
        request["source_replay_runner_ref"]["path"] = "other.py"
    elif mutation == "runner_sha":
        request["source_replay_runner_ref"]["sha256"] = "0" * 64
    elif mutation == "runner_bytes":
        request["source_replay_runner_ref"]["size_bytes"] += 1
    else:
        request["callback"] = "trust-me"

    def forbidden(*_args, **_kwargs):
        raise AssertionError("invalid profile reached file admission")

    monkeypatch.setattr(base, "authenticate_ref_v1", forbidden)
    with pytest.raises(ValueError):
        profiles.authenticate_family_store_run_v2(request)


def test_exact_f40_real_synthetic_source_store_replay_and_export(tmp_path: Path) -> None:
    request = _real_store_request(tmp_path, f40_profile=True)
    store_before = Path(request["store_ref"]["path"]).read_bytes()
    bundle = profiles.authenticate_family_store_run_v2(request)
    profile = bundle["source_replay_profile_receipt"]
    assert profile["profile_id"] == profiles.F40_PROFILE
    assert profile["full_trial_count"] == 1
    assert profile["selected_page_count"] == 1
    assert profile["authenticated_repair_count"] == 0  # No selected source matches the historical9 registry.
    assert profile["trial_axis_sha256"] == base.canonical_json_sha256_v1(bundle["sweep"]["trials"])
    assert bundle["run_metadata"]["implementation_axis_sha256"] == profile["producer_axis_sha256"]
    assert len(bundle["producer_files"]) == 15
    assert request["expected_run_kind"] == "EXPERIMENTAL" and not request["require_current_selection"]
    result = profiles.export_tm_family_store_document_v2(request=request)
    receipt = json.loads((Path(result["output_dir"]) / "receipt.json").read_bytes())
    assert receipt["provenance"]["source_replay_profile"] == profile
    assert receipt["provenance"]["checked_request_sha256"] == base.sha256(base.json_bytes(request)).hexdigest()
    assert receipt["financial_acceptance"] == "NOT_CLAIMED"
    assert profile["pdf_residual_acceptance"] == "NOT_CLAIMED"
    assert Path(request["store_ref"]["path"]).read_bytes() == store_before


def test_actual_family_local_narrative_recovery_cannot_use_generic_fallback(tmp_path: Path) -> None:
    rows = _rows()
    # The evaluator-only fixture uses [] for an unlabeled total. The canonical
    # page contract requires a nonempty path, including [None] for that total.
    # Keep every row flat/self-labelled; invent no owner, relation or value.
    for row in rows:
        row["hierarchy_path_exact"] = [row["label_exact"]]
    page = _page(rows, owner="Thuyết minh báo cáo tài chính")
    page["sections"][0]["narratives_exact"] = ["30. Tiền và các khoản tương đương tiền"]
    request = _real_store_request(tmp_path, f40_profile=True, page_json_override=page)
    bundle = profiles.authenticate_family_store_run_v2(request)
    assert bundle["trial"]["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert len(base.project_multitable_document_v1(bundle)) == 8
    legacy_request = {key: request[key] for key in base._REQUEST_FIELDS}
    with pytest.raises((ValueError, RuntimeError)):
        base.authenticate_multitable_store_run_v1(legacy_request)
    assert not Path(request["output_dir"]).exists()


@pytest.mark.parametrize("mutation", ["drop", "extra", "order", "digest", "size", "noncanonical", "request_axis", "runner"])
def test_stored15_axis_exact_bytes_and_profile_ref_are_mandatory(mutation: str) -> None:
    root = Path(__file__).resolve().parents[2]
    refs = profiles.approved_f40_producer_refs_v2()
    request = {"producer_root": str(root), "expected_family_id": "CASH_EQUIVALENTS", "producer_refs": copy.deepcopy(refs)}
    profile = _unopened_request()
    raw = base.json_bytes(refs)
    if mutation == "drop":
        refs.pop()
        raw = base.json_bytes(refs)
    elif mutation == "extra":
        refs.append({"path": "fake.py", "sha256": "a" * 64, "size_bytes": 1})
        raw = base.json_bytes(refs)
    elif mutation == "order":
        refs.reverse()
        raw = base.json_bytes(refs)
    elif mutation == "digest":
        refs[0]["sha256"] = "a" * 64
        raw = base.json_bytes(refs)
    elif mutation == "size":
        refs[0]["size_bytes"] += 1
        raw = base.json_bytes(refs)
    elif mutation == "noncanonical":
        raw = json.dumps(refs, indent=2).encode("utf-8")
    elif mutation == "request_axis":
        request["producer_refs"].pop()
    else:
        profile["source_replay_runner_ref"]["sha256"] = "a" * 64
    with pytest.raises(ValueError):
        profiles.validate_f40_profile_axis_v2(request=request, profile=profile, stored_refs=refs, stored_axis_bytes=raw)


def test_correct15_axis_and_same_combined_root_are_accepted_as_source_metadata() -> None:
    root = Path(__file__).resolve().parents[2]
    refs = profiles.approved_f40_producer_refs_v2()
    profiles.validate_f40_profile_axis_v2(
        request={"producer_root": str(root), "expected_family_id": "CASH_EQUIVALENTS", "producer_refs": refs},
        profile=_unopened_request(), stored_refs=refs, stored_axis_bytes=base.json_bytes(refs),
    )


def test_foreign_root_and_cached_generic_module_are_not_hot_switched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="foreign F40 producer root"):
        profiles._load_f40_runner_v2(tmp_path)
    name = "run_gemini_json_multitable_hierarchical_accounting_family_v1"
    monkeypatch.setitem(sys.modules, name, SimpleNamespace(__file__=str(tmp_path / "foreign.py")))
    with pytest.raises(ValueError, match="foreign cached generic runner"):
        profiles._load_f40_runner_v2(root)


@pytest.mark.parametrize("member", ["replay_cash_equivalents_trials_from_source_v1", "_authenticate_source_repairs_v1"])
def test_replaced_source_callback_fails_callable_origin_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, member: str) -> None:
    request = _real_store_request(tmp_path, f40_profile=True)
    runner = profiles._load_f40_runner_v2(Path(request["producer_root"]))

    def fake_callback(**_kwargs):
        return []

    monkeypatch.setattr(runner, member, fake_callback)
    with pytest.raises(ValueError, match="callable origin"):
        profiles.authenticate_family_store_run_v2(request)


@pytest.mark.parametrize("fault", ["drop", "duplicate", "ordinal", "mapping"])
def test_full_trial_axis_guard_rejects_faulty_cold_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    request = _real_store_request(tmp_path, f40_profile=True)
    runner = profiles._load_f40_runner_v2(Path(request["producer_root"]))
    # Explicit negative loader seam: real cold replay executes first, then the
    # returned result is faulted. No successful financial proof is claimed.
    fault_runner = SimpleNamespace(**vars(runner))

    def faulty_replay(**kwargs):
        trials = copy.deepcopy(runner.replay_cash_equivalents_trials_from_source_v1(**kwargs))
        if fault == "drop":
            trials.pop()
        elif fault == "duplicate":
            trials.append(copy.deepcopy(trials[0]))
        elif fault == "ordinal":
            trials[0]["document_ordinal"] = 2
        else:
            trials[0]["mappings"][0]["values"][0]["coefficient"] += 1
        return trials

    fault_runner.replay_cash_equivalents_trials_from_source_v1 = faulty_replay
    monkeypatch.setattr(profiles, "_load_f40_runner_v2", lambda _root: fault_runner)
    with pytest.raises(ValueError, match="full original trial axis"):
        profiles.authenticate_family_store_run_v2(request)
    assert not Path(request["output_dir"]).exists()


def test_v1_entry_rejects_v2_fields_instead_of_silently_ignoring_profile(tmp_path: Path) -> None:
    request = _real_store_request(tmp_path, f40_profile=True)
    with pytest.raises(ValueError, match="request fields drift"):
        base.authenticate_multitable_store_run_v1(request)
