"""Runner caption-admission joins; synthetic protocol tests are NOT PDF proof.

Real owned-source tests below use the actual SQLite/index/loader and exercise
the unrelated EMPTY caption axis. The one applicable synthetic protocol
replaces only the already-tested pixel-auth boundary, never source authority.
Actual KLB66 warm/cold source proof remains a separate required witness.
"""
from __future__ import annotations

import sqlite3
from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _record
from test_gemini_json_income_tax_recognition_frontier_v1 import _public_query
from test_gemini_json_income_tax_registered_section_caption_integration_v1 import (
    _index_protocol,
)
from test_gemini_json_income_tax_registered_section_caption_integration_v1 import (
    caption_fixture as caption_fixture,
)
from test_run_gemini_json_income_tax_accounting_family_v1 import (
    _invoke_authenticated_raw_cold,
    _raw_census_authority_fixture,
    _raw_census_generic_ingest,
    _raw_census_sweep,
    runner,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import GeminiAccountingFamilyStoreV1Error


def _document(records, *, size_bytes=12345):
    first = records[0]
    return {
        "manifest": {
            "document": {"document_id": first["document_id"], "source_logical_name": first["source_logical_name"],
                         "source_sha256": first["source_sha256"], "source_size_bytes": size_bytes},
            "pages": [{"page_json_version_id": record["page_json_version_id"], "physical_page": record["physical_page"]}
                      for record in records],
        },
        "ids": [record["page_json_version_id"] for record in records],
    }


@pytest.fixture
def admission_protocol(caption_fixture, monkeypatch):
    records, compiled, _, _ = caption_fixture
    document, calls = _document(records), []
    loaded = [{**{key: value for key, value in record.items() if key not in {"document_id", "document_ordinal", "selected_page_ordinal"}},
               "source_json_replay_receipt": {}} for record in records]
    monkeypatch.setattr(runner, "_load_registered_section_caption_auth_envelope_v1",
                        family._load_registered_section_caption_auth_envelope_v1)

    def pixel_protocol(doc, actual_loaded, specs, root, *, original_records, registry_loader):
        assert original_records is records
        assert doc is document and actual_loaded is loaded
        assert registry_loader()[0] == specs["income_tax_section_caption_auth_envelope"]
        _, _, projection = family._prepare_income_tax_evaluation_records_v1(original_records, compiled_specs=specs)
        source = specs["income_tax_section_caption_auth_envelope"]["clone_registry"]["sources"][0]
        calls.append("fresh")
        return [{"repair_id": repair_id, "document_id": records[0]["document_id"], "runtime_document_ordinal": 1,
                 "pdf_source": deepcopy(source["pdf_source"]),
                 "loaded_original_records_object_sha256": canonical_json_sha256_v1(records),
                 "pure_clone_replay_receipt": deepcopy(projection["ordered_caption_clone_receipts"][0])}
                for repair_id in projection["ordered_caption_repair_ids"]]

    def recheck_protocol(receipts, *, registry_loader):
        registry_loader()
        assert len(receipts) == 1
        calls.append("late")

    monkeypatch.setattr(runner.section_caption_pdf_auth, "authenticate_registered_section_caption_pdf_v1", pixel_protocol)
    monkeypatch.setattr(runner.section_caption_pdf_auth, "recheck_registered_section_caption_pdf_v1", recheck_protocol)
    before = deepcopy(records)
    bundle = runner._authenticate_section_caption_admission_v1(document, loaded, records, compiled, None)
    cluster, _ = _public_query(records, compiled)
    assert cluster["status"] == family.READY
    indexed = _index_protocol(records, compiled, cluster)
    assert records == before
    return document, records, compiled, bundle, indexed, calls


def test_applicable_protocol_joins_full_fresh_original_clone_without_source_mutation(admission_protocol):
    document, records, compiled, bundle, indexed, calls = admission_protocol
    before = canonical_json_bytes_v1([document, records, compiled, bundle, indexed])
    runner._recheck_section_caption_admission_v1([bundle], [document], compiled, indexed_query_evidence=indexed)
    assert calls == ["fresh", "late"]
    assert canonical_json_bytes_v1([document, records, compiled, bundle, indexed]) == before
    assert bundle["projection_receipt"]["source_database_pdf_or_pixels_authenticated"] is False


@pytest.mark.parametrize("change", [
    "missing_bundle", "empty_applicable", "duplicate_receipt", "runtime_ordinal",
    "original_hash", "clone_hash", "indexed_projection",
])
def test_caption_admission_cannot_join_missing_or_self_resealed_axis(admission_protocol, change):
    document, _, compiled, bundle, indexed, calls = admission_protocol
    bundles = [deepcopy(bundle)]
    indexed = deepcopy(indexed)
    if change == "missing_bundle":
        bundles = []
    elif change == "empty_applicable":
        bundles[0]["receipts"] = []
    elif change == "duplicate_receipt":
        bundles[0]["receipts"].append(deepcopy(bundles[0]["receipts"][0]))
    elif change == "runtime_ordinal":
        bundles[0]["runtime_document_ordinal"] = 66
    elif change == "original_hash":
        bundles[0]["receipts"][0]["loaded_original_records_object_sha256"] = "f" * 64
    elif change == "clone_hash":
        bundles[0]["receipts"][0]["pure_clone_replay_receipt"]["evaluation_records_object_canonical_sha256"] = "f" * 64
    else:
        cluster = indexed["candidate_dispositions"][0]["cluster"]
        cluster["income_tax_section_caption_projection_receipt"]["ordered_caption_repair_ids"] = []
        indexed = _index_protocol(
            [{**axis, "page_json": record["page_json"]} for axis, record in
             zip(indexed["selected_page_axis"], admission_protocol[1], strict=True)],
            compiled, family._reseal_cluster(cluster),
        )
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        runner._recheck_section_caption_admission_v1(bundles, [document], compiled, indexed_query_evidence=indexed)
    assert calls == ["fresh"]


@pytest.mark.parametrize("disposition", [family.NOT_OBSERVED, family.UNRESOLVED])
def test_unrelated_nonready_projection_requires_explicit_empty_admission(monkeypatch, disposition):
    page = {"status": "NO_RELEVANT_FINANCIAL_CONTENT", "sections": [],
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}
    records, compiled = [_record(page)], _adapter_compiled()
    pdf = {"logical_name": records[0]["source_logical_name"], "sha256": records[0]["source_sha256"], "size_bytes": 12345}
    records[0]["document_id"] = family.section_caption_core._document_id(pdf)
    document = _document(records)
    _, _, projection = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    base = runner.coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    cluster = family._reseal_cluster(base, status=disposition, component_regions=[],
        reasons=[] if disposition == family.NOT_OBSERVED else ["SYNTHETIC_PROTOCOL_ONLY"],
        income_tax_section_caption_projection_receipt=projection)
    indexed = _index_protocol(records, compiled, cluster)
    bundle = {"document_source": deepcopy(document["manifest"]["document"]), "runtime_document_ordinal": 1,
              "original_records_sha256": canonical_json_sha256_v1(records), "projection_receipt": projection, "receipts": []}
    calls = []
    monkeypatch.setattr(runner.section_caption_pdf_auth, "recheck_registered_section_caption_pdf_v1",
                        lambda receipts, **_kwargs: calls.append(deepcopy(receipts)))
    runner._recheck_section_caption_admission_v1([bundle], [document], compiled, indexed_query_evidence=indexed)
    assert calls == [[]]
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        runner._recheck_section_caption_admission_v1([], [document], compiled, indexed_query_evidence=indexed)


def _owned_warm_caption_axis(fixture, output):
    output.mkdir()
    refs, bundles = [], []
    with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
        indexed, trials, _ = runner._evaluate_stream_v1(
            fixture.options["database"], fixture.documents, fixture.compiled,
            original_census_source=source,
            raw_census_sink=lambda census: refs.append(runner._write_raw_census_document_v1(output, census)),
            original_document_records_callback=lambda document, loaded, records: bundles.append(
                runner._authenticate_section_caption_admission_v1(document, loaded, records, fixture.compiled, None)),
        )
        runner._recheck_section_caption_admission_v1(
            bundles, fixture.documents, fixture.compiled, indexed_query_evidence=indexed)
    return indexed, trials, refs, bundles


def _cold(fixture, refs, bundles, **kwargs):
    return runner._make_authenticated_source_replay_adapter_v1(
        database=fixture.options["database"], database_ref=fixture.options["database_ref"],
        artifact_root=fixture.options["artifact_root"], corpus_index_ref=fixture.options["corpus_index_ref"],
        documents=fixture.documents, expected_census_refs=refs, expected_caption_admission_axis=bundles, **kwargs,
    )


def test_real_owned_empty_caption_axis_reloads_original_independently_in_cold(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    calls = []
    actual = runner._authenticate_section_caption_admission_v1

    def observe(*args, **kwargs):
        calls.append(args[2][0]["document_ordinal"])
        return actual(*args, **kwargs)

    monkeypatch.setattr(runner, "_authenticate_section_caption_admission_v1", observe)
    indexed, trials, refs, bundles = _owned_warm_caption_axis(fixture, tmp_path / "warm")
    assert [bundle["receipts"] for bundle in bundles] == [[], []]
    assert _invoke_authenticated_raw_cold(fixture, _cold(fixture, refs, bundles), indexed) == trials
    assert calls == [1, 2, 1, 2]


def test_cold_fresh_axis_cannot_omit_warm_empty_document_or_create_results(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    indexed, trials, refs, _bundles = _owned_warm_caption_axis(fixture, tmp_path / "warm")
    results = tmp_path / "must-not-persist.sqlite3"
    with pytest.raises(GeminiAccountingFamilyStoreV1Error):
        _raw_census_generic_ingest(fixture, results, _raw_census_sweep(fixture, indexed, trials),
                                   _cold(fixture, refs, []))
    assert not results.exists()


@pytest.mark.parametrize("drift", ["database", "implementation"])
def test_last_cold_caption_callback_precedes_actual_source_file_barriers(tmp_path, monkeypatch, drift):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    indexed, trials, refs, bundles = _owned_warm_caption_axis(fixture, tmp_path / "warm")
    dependency = tmp_path / "pinned-dependency.py"
    dependency.write_bytes(b"# Synthetic pinned dependency, never imported.\n")
    adapter = _cold(fixture, refs, bundles, implementation_refs=[runner.generic._file_ref(dependency)])
    actual = runner._recheck_section_caption_admission_v1
    calls = []

    def late(*args, **kwargs):
        actual(*args, **kwargs)
        calls.append(True)
        if len(calls) == 2:
            if drift == "database":
                with sqlite3.connect(fixture.options["database"]) as connection:
                    connection.execute("PRAGMA user_version=9")
            else:
                dependency.write_bytes(dependency.read_bytes() + b" ")

    monkeypatch.setattr(runner, "_recheck_section_caption_admission_v1", late)
    results = tmp_path / "must-not-persist.sqlite3"
    with pytest.raises(GeminiAccountingFamilyStoreV1Error):
        _raw_census_generic_ingest(fixture, results, _raw_census_sweep(fixture, indexed, trials), adapter)
    assert len(calls) == 2 and not results.exists()



def test_legacy_unowned_replay_cannot_admit_registered_caption_source(admission_protocol, monkeypatch, tmp_path):
    _, records, _, _, indexed, _ = admission_protocol
    specs, _ = runner._compile_specs_v1()
    monkeypatch.setattr(runner, "query_selected_multitable_hierarchical_family_regions_v1", lambda *_args, **_kwargs: indexed)
    database = tmp_path / "not-opened-by-this-negative.sqlite3"
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="requires the owned original-source replay adapter"):
        runner.replay_income_tax_trials_from_source_v1(
            source_page_database=database,
            selected_page_json_version_ids=[record["page_json_version_id"] for record in records],
            compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
                specs["topology"], specs["evaluation"], specs["schema"]),
            indexed_query_evidence=indexed,
        )
    assert not database.exists()


def test_none_warm_axis_cannot_reach_source_open_for_registered_caption(admission_protocol, monkeypatch, tmp_path):
    # Negative protocol check only: no database/census authority is fabricated
    # or admitted. The exact missing-warm-axis guard MUST precede any source
    # opening or retained-census read; placeholder refs must never be consumed.
    document, records, _compiled, _, indexed, _ = admission_protocol
    specs, _family_compiled = runner._compile_specs_v1()
    database = tmp_path / "must-not-open.sqlite3"
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Missing applicable warm axis reached source/census I/O")
    monkeypatch.setattr(runner, "open_income_tax_original_census_source_v1", forbidden)
    monkeypatch.setattr(runner, "_raw_census_summary_v1", forbidden)
    adapter = runner._make_authenticated_source_replay_adapter_v1(
        database=database, database_ref={"path": str(database), "sha256": "f" * 64, "size_bytes": 1},
        artifact_root=tmp_path, corpus_index_ref={"path": "unread.json", "sha256": "f" * 64, "size_bytes": 1},
        documents=[document], expected_census_refs=[{}], expected_caption_admission_axis=None,
    )
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="requires the complete warm admission axis"):
        adapter(source_page_database=database,
                selected_page_json_version_ids=[record["page_json_version_id"] for record in records],
                indexed_query_evidence=indexed,
                compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
                    specs["topology"], specs["evaluation"], specs["schema"]))
    assert not database.exists()
