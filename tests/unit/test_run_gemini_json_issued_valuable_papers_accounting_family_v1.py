from __future__ import annotations

import argparse
import copy
import importlib.util
import inspect
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
    _checked_source_replay_adapter_v1,
    _run_checked_source_replay_adapter_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_issued_valuable_papers_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_issued_valuable_papers_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _receipt(*, policy: str = runner.DISJOINT_EXPANSION) -> dict:
    return {
        "comparison_axis": [],
        "corpus_relation": {"overlap_count": 0},
        "current_axis_validation": {
            "candidate_source_count": 0,
            "manifest_document_count": 2,
            "replay_source_count": 0,
            "selected_page_json_version_count": 3,
            "trial_source_count": 2,
        },
        "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
        "format_version": runner.HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
        "oracle_authentication": {
            "artifact_count": 2,
            "refs": [
                {
                    **reference,
                    "expected_trial_count": runner.PINNED_HISTORICAL_ORACLE_TRIAL_COUNT,
                }
                for reference in runner.PINNED_HISTORICAL_ORACLES
            ],
            "source_count": 16,
        },
        "policy": policy,
    }


def _sealed_audit() -> dict:
    axes = {
        "clusters": [],
        "equations": [],
        "historical_comparator": [],
        "mappings": [],
        "query_recoveries": [],
        "residual_trials": [],
        "source_repairs": [],
        "source_only_rows": [],
    }
    fields = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()},
        "audit_metrics": {
            "equation_count": 0,
            "historical_comparator_exact_count": None,
            "mapping_count": 0,
            "residual_trial_count": 0,
            "source_repair_count": 0,
            "source_only_row_count": 0,
        },
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": _receipt(),
        "query_evidence_id": "fixture-query",
        "query_receipt": {
            "accepted_cluster_count": 0,
            "selected_document_count": 2,
            "selected_page_count": 3,
        },
        "selected_page_json_frontier_sha256": "a" * 64,
        "source_observation_contract": {
            "cell_count": 0,
            "derived_cell_count": 0,
            "format_version": "SOURCE_OBSERVATION_MAPPING_CONTRACT_AUDIT_V1",
            "mapping_count": 0,
            "partial_mapping_count": 0,
            "source_blank_cell_count": 0,
            "status": "PASS",
            "violation_count": 0,
            "violations": [],
        },
        "spec_refs": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {},
    }
    return {
        **fields,
        "audit_id": "gjivpfeav1:audit:" + canonical_json_sha256_v1(fields),
    }


def _reseal(audit: dict) -> None:
    material = {key: audit[key] for key in audit if key != "audit_id"}
    audit["audit_id"] = "gjivpfeav1:audit:" + canonical_json_sha256_v1(material)


def test_pinned_issued_oracles_authenticate_and_have_unique_source_axis() -> None:
    compiled = runner.compile_gemini_json_issued_valuable_papers_family_specs_v1(
        runner.generic._json(
            ROOT / "config/families/tm-issued-valuable-papers-topology-v1.json"
        ),
        runner.generic._json(
            ROOT / "config/families/tm-issued-valuable-papers-evaluation-v1.json"
        ),
        runner.generic._json(
            ROOT / "config/families/tm-issued-valuable-papers-schema-binding-v1.json"
        ),
        runner.generic._json(
            ROOT
            / "data/registered/gemini_json_issued_valuable_papers_source_repairs_v1.json"
        ),
    )
    refs, rows = runner._normalised_historical_oracle_rows(compiled_specs=compiled)
    assert refs == [
        {
            **reference,
            "expected_trial_count": runner.PINNED_HISTORICAL_ORACLE_TRIAL_COUNT,
        }
        for reference in runner.PINNED_HISTORICAL_ORACLES
    ]
    assert len(rows) == 16
    assert len({row["source_sha256"] for row in rows}) == 16
    assert [row["oracle_ref_index"] for row in rows] == [0] * 8 + [1] * 8


def test_disjoint_audit_receipt_validates_and_tamper_fails_closed() -> None:
    audit = _sealed_audit()
    assert runner.validate_issued_valuable_papers_experimental_audit_content_v1(audit)

    tampered = copy.deepcopy(audit)
    tampered["historical_comparator_policy_receipt"]["corpus_relation"]["overlap_count"] = 1
    _reseal(tampered)
    with pytest.raises(
        runner.RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error,
        match="disjoint comparator",
    ):
        runner.validate_issued_valuable_papers_experimental_audit_content_v1(tampered)


def test_semantic_axes_seal_residual_trials_and_source_only_rows() -> None:
    source_only = {
        "consumed_by_exact_equation": True,
        "declared_role": None,
        "row_ordinal": 3,
        "source_ref": {"label_exact": "Kỳ hạn tổng hợp"},
    }
    ready_trial = {
        "candidates": [
            {
                "closure_receipt": {
                    "equations": [],
                    "query_receipt": {"query": "sealed"},
                    "source_only_unmapped_rows": [source_only],
                },
                "component_regions": [],
                "mappings": [],
            }
        ],
        "document_ordinal": 1,
        "reasons": [],
        "source_logical_name": "ready.pdf",
        "source_sha256": "1" * 64,
        "status": runner.READY,
    }
    residual_trial = {
        "candidates": [],
        "document_ordinal": 2,
        "reasons": ["NO_EXACT_OWNER"],
        "source_logical_name": "residual.pdf",
        "source_sha256": "2" * 64,
        "status": "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY",
    }
    axes = runner._semantic_axes(trials=[ready_trial, residual_trial])
    assert axes["source_only_rows"] == [
        {
            "document_ordinal": 1,
            "source_logical_name": "ready.pdf",
            "source_only_row": source_only,
            "source_sha256": "1" * 64,
        }
    ]
    assert axes["residual_trials"] == [
        {
            "document_ordinal": 2,
            "reasons": ["NO_EXACT_OWNER"],
            "source_logical_name": "residual.pdf",
            "source_sha256": "2" * 64,
            "status": "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY",
        }
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("policy", "UNKNOWN"),
        ("oracle_ref_order", None),
        ("candidate_count", 1),
    ],
)
def test_policy_unknown_order_and_axis_count_tamper_fail_closed(field: str, value: object) -> None:
    audit = _sealed_audit()
    receipt = audit["historical_comparator_policy_receipt"]
    if field == "policy":
        receipt["policy"] = value
    elif field == "oracle_ref_order":
        receipt["oracle_authentication"]["refs"].reverse()
    else:
        receipt["current_axis_validation"]["candidate_source_count"] = value
    _reseal(audit)
    with pytest.raises(
        runner.RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error,
        match="policy receipt",
    ):
        runner.validate_issued_valuable_papers_experimental_audit_content_v1(audit)


def test_run_rejects_disjoint_official_before_reading_inputs() -> None:
    args = argparse.Namespace(
        historical_comparator_policy=runner.DISJOINT_EXPANSION,
        run_kind="OFFICIAL",
    )
    with pytest.raises(
        runner.RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error,
        match="requires STRICT_RELEASE",
    ):
        runner.run(args)


def test_run_rejects_nonregistered_source_repair_before_reading_inputs(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        historical_comparator_policy=runner.DISJOINT_EXPANSION,
        run_kind="EXPERIMENTAL",
        source_repair_spec=tmp_path / "substitute.json",
    )
    with pytest.raises(
        runner.RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error,
        match="registered source-repair artifact",
    ):
        runner.run(args)


def _patch_source_replay_fixture(monkeypatch: pytest.MonkeyPatch, *, expected_page_unit_claims=None) -> tuple[dict, list[dict]]:
    region = {
        "document_ordinal": 1,
        "page_json_version_id": "page-1",
        "physical_page": 1,
        "section_id": "s1",
        "table_id": "t1",
    }
    indexed = {
        "accepted_clusters": [
            {"component_regions": [region], "document_ordinal": 1}
        ],
        "selected_page_axis": [{"document_ordinal": 1, "page_json_version_id": "page-1",
                                "physical_page": 1, "selected_page_ordinal": 1}],
    }
    trial = {"document_ordinal": 1, "fixture": "source-replayed"}
    payload_provenance = [{"page_json_version_id": "page-1", "fixture": "authenticated-metadata-io"}]

    def metadata_io(source_database, *, selected_ids):
        assert source_database.name == "source.sqlite3"
        assert selected_ids == ["page-1"]
        return payload_provenance

    def query_receipt(regions, *, selected_page_axis, selected_page_provenance, authenticated_page_unit_claims):
        assert regions == [region]
        assert selected_page_axis is indexed["selected_page_axis"]
        assert selected_page_provenance is payload_provenance
        assert authenticated_page_unit_claims is expected_page_unit_claims
        return {"query": "receipt"}

    def evaluate(**kwargs):
        assert kwargs["selected_page_axis"] is indexed["selected_page_axis"]
        assert kwargs["selected_page_provenance"] is payload_provenance
        assert kwargs["authenticated_page_unit_claims"] is expected_page_unit_claims
        return {"candidate": "evaluated"}

    def replay(candidate, **kwargs):
        assert kwargs["selected_page_axis"] is indexed["selected_page_axis"]
        assert kwargs["selected_page_provenance"] is payload_provenance
        assert kwargs["authenticated_page_unit_claims"] is expected_page_unit_claims
        return candidate

    monkeypatch.setattr(runner.generic, "_json", lambda _path: {"repairs": []})
    monkeypatch.setattr(
        runner,
        "bind_gemini_json_issued_valuable_papers_source_repairs_v1",
        lambda *_args: {"family_compiled": True},
    )
    monkeypatch.setattr(
        runner,
        "query_selected_multitable_hierarchical_family_regions_v1",
        lambda *_args, **_kwargs: indexed,
    )
    monkeypatch.setattr(
        runner.generic,
        "_load_selected_pages_by_document",
        lambda *_args, **_kwargs: {1: {"page-1": {}}},
    )
    monkeypatch.setattr(
        runner,
        "_selected_payload_provenance_v1",
        metadata_io,
    )
    monkeypatch.setattr(
        runner,
        "adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1",
        lambda value, **_kwargs: (value, []),
    )
    monkeypatch.setattr(
        runner,
        "build_gemini_json_issued_valuable_papers_region_query_receipt_v1",
        query_receipt,
    )
    monkeypatch.setattr(
        runner,
        "evaluate_gemini_json_issued_valuable_papers_family_cluster_v1",
        evaluate,
    )
    monkeypatch.setattr(
        runner,
        "validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1",
        replay,
    )
    monkeypatch.setattr(
        runner.generic,
        "_trials",
        lambda **_kwargs: [trial],
    )
    return indexed, [trial]


def test_source_replay_hook_is_byte_bound_and_rebuilds_exact_trials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    indexed, trials = _patch_source_replay_fixture(monkeypatch)
    runner_ref = runner.generic._file_ref(RUNNER_PATH, root=ROOT)
    implementation_refs = [runner_ref]
    checked, checked_ref = _checked_source_replay_adapter_v1(
        runner.replay_issued_valuable_papers_trials_from_source_v1,
        adapter_ref=runner_ref,
        implementation_refs=implementation_refs,
    )
    assert checked is runner.replay_issued_valuable_papers_trials_from_source_v1
    assert checked_ref == runner_ref
    _run_checked_source_replay_adapter_v1(
        checked,
        adapter_ref=runner_ref,
        implementation_refs=implementation_refs,
        source_page_database=tmp_path / "source.sqlite3",
        selected_page_json_version_ids=["page-1"],
        compiled_specs={"topology": {}, "evaluation": {}, "schema": {}},
        indexed_query_evidence=indexed,
        expected_trials=trials,
    )

    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="different trial axis",
    ):
        _run_checked_source_replay_adapter_v1(
            checked,
            adapter_ref=runner_ref,
            implementation_refs=implementation_refs,
            source_page_database=tmp_path / "source.sqlite3",
            selected_page_json_version_ids=["page-1"],
            compiled_specs={"topology": {}, "evaluation": {}, "schema": {}},
            indexed_query_evidence=indexed,
            expected_trials=[{"document_ordinal": 1, "fixture": "tampered"}],
        )


def test_source_replay_hook_ref_drift_and_exception_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    indexed, trials = _patch_source_replay_fixture(monkeypatch)
    runner_ref = runner.generic._file_ref(RUNNER_PATH, root=ROOT)
    drifted_ref = {**runner_ref, "sha256": "0" * 64}
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="does not authenticate",
    ):
        _checked_source_replay_adapter_v1(
            runner.replay_issued_valuable_papers_trials_from_source_v1,
            adapter_ref=drifted_ref,
            implementation_refs=[drifted_ref],
        )

    monkeypatch.setattr(
        runner,
        "evaluate_gemini_json_issued_valuable_papers_family_cluster_v1",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("fixture adapter failure")),
    )
    with pytest.raises(RuntimeError, match="fixture adapter failure"):
        _run_checked_source_replay_adapter_v1(
            runner.replay_issued_valuable_papers_trials_from_source_v1,
            adapter_ref=runner_ref,
            implementation_refs=[runner_ref],
            source_page_database=tmp_path / "source.sqlite3",
            selected_page_json_version_ids=["page-1"],
            compiled_specs={"topology": {}, "evaluation": {}, "schema": {}},
            indexed_query_evidence=indexed,
            expected_trials=trials,
        )


def test_current_cold_adapter_is_byte_bound_and_freshly_authenticates_on_each_call(monkeypatch, tmp_path):
    from test_gemini_json_issued_valuable_papers_page_unit_scopes_v1 import _catalog
    from test_gemini_json_issued_valuable_papers_source_total_lanes_v1 import _compiled

    claims = []  # Protocol-only fake DB; no financial permission is mocked in.
    indexed, trials = _patch_source_replay_fixture(monkeypatch, expected_page_unit_claims=claims)
    monkeypatch.setattr(runner, "bind_gemini_json_issued_valuable_papers_source_repairs_v1", lambda *_args: _compiled())
    loads, authentications = [], []

    def load(root):
        assert root == ROOT
        loads.append(root)
        return _catalog()

    def authenticate(**kwargs):
        assert kwargs["source_pdf_root"] == tmp_path
        assert kwargs["selected_page_axis"] is indexed["selected_page_axis"]
        assert kwargs["selected_page_provenance"][0]["fixture"] == "authenticated-metadata-io"
        assert kwargs["page_json_by_document"] == {1: {"page-1": {}}}
        authentications.append(kwargs)
        return claims

    monkeypatch.setattr(runner.page_units, "load_registered_page_unit_catalog_v1", load)
    monkeypatch.setattr(runner.page_units, "authenticate_registered_page_unit_scopes_v1", authenticate)
    callback = runner._fresh_page_unit_source_replay_adapter_v1(tmp_path)
    captured = inspect.getclosurevars(callback).nonlocals
    assert set(captured) == {"pdf_root"}
    assert captured == {"pdf_root": tmp_path}
    assert list(inspect.signature(callback).parameters) == ["source_page_database", "selected_page_json_version_ids",
                                                           "compiled_specs", "indexed_query_evidence"]
    reference = runner.generic._file_ref(RUNNER_PATH, root=ROOT)
    for _ in range(2):
        _run_checked_source_replay_adapter_v1(callback, adapter_ref=reference, implementation_refs=[reference],
            source_page_database=tmp_path / "source.sqlite3", selected_page_json_version_ids=["page-1"],
            compiled_specs={"topology": {}, "evaluation": {}, "schema": {}}, indexed_query_evidence=indexed,
            expected_trials=trials)
    assert len(loads) == 4  # Fresh descriptor frontier + fresh compiler load per call.
    assert len(authentications) == 2

    def unavailable(**_kwargs):
        raise ValueError("fresh PDF source is unavailable")

    monkeypatch.setattr(runner.page_units, "authenticate_registered_page_unit_scopes_v1", unavailable)
    with pytest.raises(ValueError, match="fresh PDF source is unavailable"):
        _run_checked_source_replay_adapter_v1(callback, adapter_ref=reference, implementation_refs=[reference],
            source_page_database=tmp_path / "source.sqlite3", selected_page_json_version_ids=["page-1"],
            compiled_specs={"topology": {}, "evaluation": {}, "schema": {}}, indexed_query_evidence=indexed,
            expected_trials=trials)


def test_audit_content_rejects_resealed_unit_registration_lineage_drift():
    from test_gemini_json_issued_valuable_papers_page_unit_scopes_v1 import _catalog, _context

    catalog, context = _context()
    audit = _sealed_audit()
    audit["axes"]["page_unit_scopes"] = context["authenticated_page_unit_claims"]
    audit["spec_refs"] = {"page_unit_catalog": {"sha256": runner.PAGE_UNIT_CATALOG_SHA256},
        "page_unit_review": catalog["review_ref"], "page_unit_renderer": catalog["renderer_ref"]}

    def reseal():
        audit["axis_counts"] = {k: len(v) for k, v in audit["axes"].items()}
        audit["axis_sha256"] = {k: canonical_json_sha256_v1(v) for k, v in audit["axes"].items()}
        audit["audit_id"] = "gjivpfeav1:audit:" + canonical_json_sha256_v1({
            k: v for k, v in audit.items() if k != "audit_id"})

    reseal()
    assert runner.validate_issued_valuable_papers_experimental_audit_content_v1(audit) == audit
    assert _catalog() == catalog
    claim = audit["axes"]["page_unit_scopes"][0]
    claim["selected_source"]["source_sha256"] = "0" * 64
    claim["unit_claim_id"] = "gjivppuv1:claim:" + canonical_json_sha256_v1({
        k: v for k, v in claim.items() if k != "unit_claim_id"})
    reseal()
    with pytest.raises(ValueError, match="registration/lineage"):
        runner.validate_issued_valuable_papers_experimental_audit_content_v1(audit)


@pytest.mark.parametrize("stage", ["after_ingest", "after_export"])
def test_outer_run_cannot_return_success_after_late_page_unit_pdf_drift(tmp_path, monkeypatch, stage):
    from contextlib import contextmanager

    from test_f25_registered_page_unit_pdf_auth_v1 import _held_protocol

    catalog, options, held_options = _held_protocol(tmp_path, monkeypatch)
    hold = runner.page_units.hold_registered_page_unit_inputs_v1
    monkeypatch.setattr(runner.page_units, "hold_registered_page_unit_inputs_v1", lambda **_kwargs: hold(**held_options))
    selected = list(held_options["selected_page_json_version_ids"])
    database = tmp_path / "never-opened.sqlite3"
    monkeypatch.setattr(runner.generic, "_json", lambda _path: {})
    monkeypatch.setattr(runner, "validate_current_corpus_manifest_index_v1", lambda _value: {"database_ref": {}})
    monkeypatch.setattr(runner.generic, "_content_ref", lambda *_args: database)
    monkeypatch.setattr(runner.generic, "_selected_page_axis", lambda **_kwargs: selected)
    # Negative lifecycle protocol only: no financial candidate/validator is
    # substituted with a passing result, and no database API is executed.
    monkeypatch.setattr(runner, "compile_gemini_json_issued_valuable_papers_family_specs_v1",
        lambda *_args, **_kwargs: {"topology": {"family_id": runner.FAMILY_ID},
            "issued_valuable_papers_source_repairs": [], "issued_valuable_papers_page_unit_catalog": catalog})
    monkeypatch.setattr(runner, "_authenticate_source_repairs_v1", lambda **_kwargs: [])

    @contextmanager
    def snapshot(*_args, **_kwargs):
        yield argparse.Namespace(path=database)

    monkeypatch.setattr(runner.generic, "_authenticated_sqlite_snapshot", snapshot)
    reached = []
    partial = tmp_path / "provisional-protocol-output.txt"

    def body(_args, **_kwargs):
        assert runner.page_units.authenticate_registered_page_unit_scopes_v1(**options)
        reached.append("authenticated")
        partial.write_text("provisional lifecycle protocol only", encoding="utf-8")
        reached.append(stage)
        path = options["source_pdf_root"] / "synthetic.pdf"
        if stage == "after_ingest":
            path.unlink()
        else:
            replacement = path.with_name("replacement.pdf")
            replacement.write_bytes(path.read_bytes())
            replacement.replace(path)
        return {"disposition": "SUCCEEDED"}  # Must not escape the real outer guard.

    monkeypatch.setattr(runner, "_run_with_authenticated_database", body)
    config = ROOT / "config/families"
    args = argparse.Namespace(run_kind="EXPERIMENTAL", historical_comparator_policy=runner.DISJOINT_EXPANSION,
        source_repair_spec=runner.SOURCE_REPAIR_SPEC_PATH, corpus_index=tmp_path / "unused-index.json",
        artifact_root=tmp_path, source_pdf_root=options["source_pdf_root"],
        topology_spec=config / "tm-issued-valuable-papers-topology-v1.json",
        evaluation_spec=config / "tm-issued-valuable-papers-evaluation-v1.json",
        schema_binding_spec=config / "tm-issued-valuable-papers-schema-binding-v1.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        runner.run(args)
    assert reached == ["authenticated", stage]
    assert partial.is_file() and not database.exists()
