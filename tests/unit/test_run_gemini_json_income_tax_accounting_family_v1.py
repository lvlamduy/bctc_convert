from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_income_tax_family_v1 import _page, _primary_page, _primary_tax_rows, _row

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    build_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
)

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("income_tax_runner_tests_v1", PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _fixture(tmp_path):
    database = tmp_path / "source.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _primary_page(_primary_tax_rows())
    stored = _ingest(database, page_json=page, physical_page=1)
    document = {
        "manifest": {
            "document": {
                "source_logical_name": "report.pdf",
                "source_sha256": "b" * 64,
                "source_size_bytes": 123,
            },
            "pages": [{"physical_page": 1, "page_json_version_id": stored["page_json_version_id"]}],
        },
        "ids": [stored["page_json_version_id"]],
    }
    document["manifest"]["document"]["document_id"] = (
        "gfpstorev1:document:" + canonical_json_sha256_v1(document["manifest"]["document"])
    )
    specs, compiled = runner._compile_specs_v1()
    return database, document, specs, compiled


def test_actual_batched_sqlite_load_stream_and_independent_cold_replay(tmp_path):
    database, document, specs, compiled = _fixture(tmp_path)
    indexed, trials, timing = runner._evaluate_stream_v1(database, [document], compiled)
    assert trials[0]["status"] == runner.READY
    assert timing["selected_json_api_calls"] == timing["selected_json_sql_rows"] == 1
    assert timing["selected_json_sql_payload_bytes"] > 0
    assert timing["peak_document_selected_pages"] == 1
    assert timing["sql_total_statements_claimed"] is False
    replay = runner.replay_income_tax_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(document["ids"]),
        indexed_query_evidence=indexed,
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"]
        ),
    )
    assert same_typed_json_v1(replay, trials)


def test_cold_replay_never_uses_cache_and_rejects_query_tamper(tmp_path, monkeypatch):
    database, document, specs, compiled = _fixture(tmp_path)
    indexed, _, _ = runner._evaluate_stream_v1(database, [document], compiled)

    def forbidden(*args, **kwargs):
        raise AssertionError("Cold replay consulted cache")

    monkeypatch.setattr(runner.BaseClusterCache, "get_or_build", forbidden)
    altered = deepcopy(indexed)
    altered["query_receipt"]["selected_page_count"] += 1
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="Cold replay indexed"):
        runner.replay_income_tax_trials_from_source_v1(
            source_page_database=database,
            selected_page_json_version_ids=tuple(document["ids"]),
            indexed_query_evidence=altered,
            compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
                specs["topology"], specs["evaluation"], specs["schema"]
            ),
        )


def test_source_missing_json_and_source_path_or_physical_tamper_fail(tmp_path):
    database, document, _, compiled = _fixture(tmp_path)
    for field, value in (
        ("physical_page", 2),
        ("page_json_version_id", "gfpstorev1:json:" + "0" * 64),
    ):
        changed = deepcopy(document)
        changed["manifest"]["pages"][0][field] = value
        with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="physical page differs"):
            runner._evaluate_stream_v1(database, [changed], compiled)
    changed = deepcopy(document)
    changed["manifest"]["document"]["source_logical_name"] = "another.pdf"
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="document ID differs"):
        runner._evaluate_stream_v1(database, [changed], compiled)
    changed = deepcopy(document)
    changed["ids"] = ["gfpstorev1:json:" + "0" * 64]
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="provenance is absent"):
        runner._evaluate_stream_v1(database, [changed], compiled)


def test_cache_key_binds_full_ordered_context_and_all_specs_and_implementations():
    records = [
        {"page_json_version_id": "a", "page_json": {"unit": "Million"}},
        {"page_json_version_id": "b", "page_json": {"context": "primary"}},
    ]
    specs, refs = {"repair_spec": "a", "adapter": "b"}, [{"sha256": "c" * 64}]
    expected = runner.base_cluster_cache_key_v1(records, specs, refs)
    assert runner.base_cluster_cache_key_v1(list(reversed(records)), specs, refs) != expected
    changed = deepcopy(records)
    changed[1]["page_json"]["context"] = "note"
    assert runner.base_cluster_cache_key_v1(changed, specs, refs) != expected
    assert (
        runner.base_cluster_cache_key_v1(records, {**specs, "repair_spec": "drift"}, refs)
        != expected
    )
    assert runner.base_cluster_cache_key_v1(records, specs, [{"sha256": "d" * 64}]) != expected


def test_append_only_cache_hit_and_content_tamper(tmp_path):
    cache = runner.BaseClusterCache(tmp_path / "cache.sqlite3")
    calls = []

    def build():
        calls.append(True)
        return {"synthetic": "one", "unit": "Million"}

    first, hit = cache.get_or_build("a" * 64, build)
    assert hit is False
    second, hit = cache.get_or_build("a" * 64, build)
    assert second == first and hit is True and len(calls) == 1
    cache.connection.execute("UPDATE f39_base_cluster_cache SET content=?", (b"{}",))
    cache.connection.commit()
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="hash differs"):
        cache.get_or_build("a" * 64, build)
    cache.close()


def test_cache_hit_and_independent_cold_replay_match(tmp_path):
    database, document, specs, compiled = _fixture(tmp_path)
    cache = runner.BaseClusterCache(tmp_path / "cache.sqlite3")
    first, trials, _ = runner._evaluate_stream_v1(database, [document], compiled, cache=cache)
    second, replayed, timing = runner._evaluate_stream_v1(
        database, [document], compiled, cache=cache
    )
    assert first == second and trials == replayed and timing["base_cache_hits"] == 1
    cold = runner.replay_income_tax_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(document["ids"]),
        indexed_query_evidence=first,
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"]
        ),
    )
    assert same_typed_json_v1(cold, trials)
    cache.close()


def test_source_guard_authenticated_bytes_no_copy_and_identity_change_rejected(tmp_path):
    path = tmp_path / "source.sqlite3"
    path.write_bytes(b"immutable synthetic bytes")
    ref = {"size_bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest()}
    with runner._authenticated_source_v1(path, ref) as actual:
        assert actual == path
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="changed"):
        with runner._authenticated_source_v1(path, ref):
            path.write_bytes(b"modified synthetic bytes!")


def test_sidecar_symlink_wrong_hash_and_unsafe_path_fail_closed(tmp_path):
    path = tmp_path / "source.sqlite3"
    path.write_bytes(b"immutable")
    ref = {"size_bytes": len(b"immutable"), "sha256": "0" * 64}
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="changed"):
        with runner._authenticated_source_v1(path, ref):
            pass
    Path(str(path) + "-wal").touch()
    with pytest.raises(
        runner.generic.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error,
        match="sidecar",
    ):
        with runner._authenticated_source_v1(path, ref):
            pass
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="absolute"):
        runner._safe_path(Path("relative.json"))
    alias = tmp_path / "alias"
    alias.symlink_to(path)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="Symlink"):
        runner._safe_path(alias)


def test_duplicate_json_cannot_reseal_flags(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_bytes(b'{"status":"PASS","status":"FAIL"}')
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="Duplicate"):
        runner._json(path)


def test_cli_explicit_paths_and_bounded_mode_are_not_final_authority():
    args = runner._parser().parse_args(
        [
            "--repo-root",
            "/repo",
            "--corpus-index",
            "/index.json",
            "--source-page-database",
            "/source.sqlite3",
            "--artifact-root",
            "/artifacts",
            "--source-pdf-root",
            "/pdf",
            "--output-dir",
            "/newout",
            "--results-database",
            "/newout/results.sqlite3",
            "--document-limit",
            "1",
        ]
    )
    assert args.document_limit == 1
    assert not hasattr(args, "official") and not hasattr(args, "provider")


def test_existing_output_is_not_overwritten(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    args = SimpleNamespace(
        repo_root=runner.ROOT,
        corpus_index=tmp_path / "index.json",
        artifact_root=tmp_path / "artifacts",
        source_page_database=tmp_path / "store.sqlite3",
        source_pdf_root=tmp_path / "pdf",
        output_dir=output,
        results_database=output / "results.sqlite3",
    )
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="Fresh output"):
        runner.run(args)
    assert list(output.iterdir()) == []


def test_shared_pins_exact_and_raw_blank_never_coerced():
    runner._assert_shared_pins_v1()
    source = {"before_exact": None}
    cloned = json.loads(canonical_json_bytes_v1(source))
    assert cloned["before_exact"] is None


def test_actual_manifest_shape_document_id_and_local_selection_ref(tmp_path):
    source = {
        "source_logical_name": "vietstock_bctc/ABB/2025/report.pdf",
        "source_sha256": "b" * 64,
        "source_size_bytes": 123,
    }
    material = {
        "document": {
            **source,
            "document_id": "gfpstorev1:document:" + canonical_json_sha256_v1(source),
        },
        "page_count": 1,
        "pages": [{"physical_page": 1, "page_json_version_id": "gfpstorev1:json:" + "a" * 64}],
    }
    manifest = {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
    document_root = tmp_path / "documents" / ("f" * 64)
    manifest_path = document_root / "current-document-manifests" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(canonical_json_bytes_v1(manifest))
    reference = {
        "path": "current-document-manifests/manifest.json",
        "sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "size_bytes": manifest_path.stat().st_size,
    }
    selection = build_current_document_manifest_selection_v1(
        document_plan_id="gjfpdocv1:" + "c" * 64,
        source_sha256=source["source_sha256"],
        document_manifest_id=manifest["document_manifest_id"],
        document_manifest_ref=reference,
        page_image_frontier_sha256="d" * 64,
        page_prompt_frontier_sha256="e" * 64,
        prior_selection_ids=[],
    )
    selection_path = document_root / "current-document-manifest-selections" / "selection.json"
    selection_path.parent.mkdir()
    selection_path.write_bytes(canonical_json_bytes_v1(selection))
    index_document = {
        "relative_path": source["source_logical_name"],
        "source_sha256": source["source_sha256"],
        "source_size_bytes": source["source_size_bytes"],
        "document_manifest_id": manifest["document_manifest_id"],
        "document_manifest_ref": {**reference, "path": str(manifest_path.relative_to(tmp_path))},
        "selection_id": selection["selection_id"],
        "selection_ref": {
            "path": str(selection_path.relative_to(tmp_path)),
            "sha256": sha256(selection_path.read_bytes()).hexdigest(),
            "size_bytes": selection_path.stat().st_size,
        },
        "page_count": 1,
        "page_json_frontier_sha256": canonical_json_sha256_v1(manifest["pages"]),
    }
    index = {"documents": [index_document], "summary": {"page_count": 1}}
    documents, ids = runner._documents_v1(index, tmp_path)
    assert documents[0]["manifest"]["document"]["document_id"] == material["document"]["document_id"]
    assert ids == [manifest["pages"][0]["page_json_version_id"]]
    changed = deepcopy(index)
    changed["documents"][0]["source_sha256"] = "0" * 64
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="frontier differs"):
        runner._documents_v1(changed, tmp_path)


def test_selected_prefix_and_physical_count_need_exact_committed_scope():
    source = {"source_logical_name": "prefix.pdf", "source_sha256": "b" * 64}
    document = {"manifest": {"document": source}, "ids": ["one", "two"]}
    row = {
        "relative_path": "prefix.pdf",
        "source_sha256": "b" * 64,
        "source_page_count": 3,
        "included_last_physical_page": 2,
        "review_conclusion": runner.PREFIX_CONCLUSION,
    }
    proof = runner._check_page_scope_v1(document, 3, {"prefix.pdf": row})
    assert proof["selected_page_count"] == 2
    assert proof["source_physical_page_count"] == 3
    assert proof["excluded_non_vietnamese_appendix_page_count"] == 1
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="exact prefix"):
        runner._check_page_scope_v1(document, 3, {})
    changed = {**row, "source_sha256": "0" * 64}
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="scope source/count"):
        runner._check_page_scope_v1(document, 3, {"prefix.pdf": changed})


def test_sparse_diagnostic_keeps_exact_immutable_index_positions_without_mutation():
    documents = [{"source": value} for value in range(1, 7)]
    original = deepcopy(documents)
    selected, ordinals = runner._diagnostic_documents_v1(documents, document_ordinals=[1, 3, 6])
    assert selected == [documents[0], documents[2], documents[5]]
    assert ordinals == [1, 3, 6] and documents == original
    assert runner._diagnostic_documents_v1(documents) == (documents, None)
    assert runner._diagnostic_documents_v1(documents, document_limit=2) == (documents[:2], [1, 2])


@pytest.mark.parametrize("ordinals", [[], [1, 1], [3, 1], [0], [7], [True]])
def test_invalid_sparse_diagnostic_fails_before_any_replay(ordinals):
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="unique, ascending"):
        runner._diagnostic_documents_v1([{}, {}, {}], document_ordinals=ordinals)


def test_first_n_and_sparse_modes_cannot_be_combined():
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="only one"):
        runner._diagnostic_documents_v1([{}, {}], document_limit=1, document_ordinals=[1])


def test_additive_render_metadata_binds_all_original_repairs_without_changing_pixels():
    _, compiled = runner._compile_specs_v1()
    value = runner._json(runner.RENDER_BINDINGS_PATH)
    profiles = runner._repair_render_bindings_v1(compiled)
    original = runner._json(runner.SPEC_PATHS["repair"])
    assert list(profiles) == [r["repair_id"] for r in original["repairs"]]
    assert len(profiles) == 13
    assert list(profiles.values()).count((2, 2)) == 2
    assert list(profiles.values()).count((300 / 72, 300 / 72)) == 11
    assert compiled["income_tax_source_repairs"] == original["repairs"]
    assert value["family_terminal_claimed"] is False


@pytest.mark.parametrize("change", [
    "missing", "duplicate", "reordered", "wrong_id", "unknown_profile", "extra_field",
    "wrong_family", "wrong_base", "wrong_spec", "wrong_contract", "terminal",
])
def test_render_metadata_frontier_identity_scope_and_profile_tamper_fail(change):
    _, compiled = runner._compile_specs_v1()
    value = runner._json(runner.RENDER_BINDINGS_PATH)
    if change == "missing":
        value["bindings"].pop()
    elif change == "duplicate":
        value["bindings"][1] = deepcopy(value["bindings"][0])
    elif change == "reordered":
        value["bindings"].reverse()
    elif change == "wrong_id":
        value["bindings"][0]["repair_id"] = "gjitfav1:repair:" + "0" * 64
    elif change == "unknown_profile":
        value["bindings"][0]["profile"] = "AUTO_TRY_UNTIL_PASS"
    elif change == "extra_field":
        value["bindings"][0]["sha256"] = "replacement hash not permitted"
    elif change == "wrong_family":
        value["family_id"] = "OPERATING_EXPENSE"
    elif change == "wrong_base":
        value["base_git_commit"] = "0" * 40
    elif change == "wrong_spec":
        value["original_source_repair_spec_sha256"] = "0" * 64
    elif change == "wrong_contract":
        value["original_render_contract"]["alpha"] = 0
    elif change == "terminal":
        value["family_terminal_claimed"] = True
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="bindings|specification"):
        runner._validate_repair_render_bindings_v1(value, compiled)


def test_pinned_render_registry_cannot_reseal_or_switch_an_allowed_profile(tmp_path, monkeypatch):
    _, compiled = runner._compile_specs_v1()
    value = runner._json(runner.RENDER_BINDINGS_PATH)
    value["bindings"][0]["profile"] = "EXISTING_RENDERING_PDF_MATRIX_300_DPI_OVER_72_RGB_PNG"
    alternate = tmp_path / "different-bindings.json"
    alternate.write_bytes(canonical_json_bytes_v1(value))
    monkeypatch.setattr(runner, "RENDER_BINDINGS_PATH", alternate)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="bindings bytes"):
        runner._repair_render_bindings_v1(compiled)


def test_render_correction_cannot_change_a_registered_source_value_or_image_hash():
    _, compiled = runner._compile_specs_v1()
    value = runner._json(runner.RENDER_BINDINGS_PATH)
    for change in ("after_exact", "page_render"):
        changed = deepcopy(compiled)
        if change == "after_exact":
            changed["income_tax_source_repairs"][0]["after_exact"]["values_exact"][0] = "0"
        else:
            changed["income_tax_source_repairs"][0]["visual_evidence"]["page_render"]["sha256"] = "0" * 64
        with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="specification differs"):
            runner._validate_repair_render_bindings_v1(value, changed)


@pytest.mark.parametrize("presentation,expected_reason", [
    ("equal", None),
    ("opposite", "SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"),
    ("conflicting", "CONFLICTING_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"),
])
def test_note_primary_rejection_keeps_queried_region_and_cold_database_replay(
    tmp_path, presentation, expected_reason,
):
    database, document, specs, compiled = _fixture(tmp_path)
    amounts = [("10", "20"), ("30", "40"), ("40", "60")]
    if presentation == "opposite":
        amounts = [tuple("(" + value + ")" for value in lane) for lane in amounts]
    elif presentation == "conflicting":
        amounts = [("90", "80"), ("10", "20"), ("100", "100")]
    note = _page([
        _row("Chi phí thuế TNDN hiện hành", *amounts[0]),
        _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", *amounts[1]),
        _row("Chi phí thuế thu nhập doanh nghiệp", *amounts[2], kind="TOTAL"),
    ])
    stored = _ingest(database, page_json=note, physical_page=2, image_sha256="f" * 64)
    document["ids"].append(stored["page_json_version_id"])
    document["manifest"]["pages"].append({
        "physical_page": 2, "page_json_version_id": stored["page_json_version_id"],
    })
    indexed, trials, _ = runner._evaluate_stream_v1(database, [document], compiled)
    candidate = trials[0]["candidates"][0]
    assert candidate["component_regions"] == indexed["accepted_clusters"][0]["component_regions"]
    if expected_reason is None:
        assert trials[0]["status"] == runner.READY and trials[0]["mappings"]
    else:
        assert trials[0]["status"] == runner.UNRESOLVED
        assert trials[0]["mappings"] == [] and trials[0]["selected_candidate_id"] is None
        assert trials[0]["reasons"] == [expected_reason]
        evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]
        assert evidence["evidence"]["primary_mappings"]
        assert evidence["evidence"]["note_mappings"]
        assert evidence["receipt_id"] == "gjitfav1:unresolved:" + canonical_json_sha256_v1({
            key: value for key, value in evidence.items() if key != "receipt_id"
        })
    cold = runner.replay_income_tax_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(document["ids"]),
        indexed_query_evidence=indexed,
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"],
        ),
    )
    assert same_typed_json_v1(cold, trials)


def test_triple_source_primary_rejection_stays_bound_to_queried_note(tmp_path):
    database, document, specs, compiled = _fixture(tmp_path)
    pages = [
        _page([
            _row("Lợi nhuận kế toán trước thuế", "100", "80"),
            _row("Thu nhập chịu thuế", "100", "80"),
        ]),
        _page([
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ], owner="Chi phí thuế thu nhập doanh nghiệp hiện hành"),
    ]
    for physical, page in enumerate(pages, 2):
        stored = _ingest(database, page_json=page, physical_page=physical,
                         image_sha256=str(physical) * 64)
        document["ids"].append(stored["page_json_version_id"])
        document["manifest"]["pages"].append({
            "physical_page": physical, "page_json_version_id": stored["page_json_version_id"],
        })
    indexed, trials, _ = runner._evaluate_stream_v1(database, [document], compiled)
    assert trials[0]["status"] == runner.UNRESOLVED
    assert trials[0]["reasons"] == ["UNRESOLVED_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"]
    assert trials[0]["mappings"] == [] and trials[0]["selected_candidate_id"] is None
    candidate = trials[0]["candidates"][0]
    assert candidate["component_regions"] == indexed["accepted_clusters"][0]["component_regions"]
    evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    rejected = evidence["rejected_primary_candidate"]
    assert rejected["status"] == runner.UNRESOLVED and rejected["mappings"] == []
    assert rejected["reasons"] == ["CONFLICTING_DIRECT_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"]
    assert rejected["component_regions"] != candidate["component_regions"]
    assert evidence["source_context_receipt"]["receipt_id"].startswith("gjitfav1:source-context:")
    cold = runner.replay_income_tax_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(document["ids"]),
        indexed_query_evidence=indexed,
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"],
        ),
    )
    assert same_typed_json_v1(cold, trials)


def _raw_census_authority_fixture(tmp_path, monkeypatch, *, pages=None, documents=1):
    from test_gemini_income_tax_raw_money_census_v1 import _fixture as source_fixture

    from bctc_ai.storage import gemini_income_tax_raw_money_census_v1 as census_module

    options, index, original_pages = source_fixture(
        tmp_path, monkeypatch, pages=pages, documents=documents,
    )
    # This is the real manifest/selection/index parser, not a pre-approved stub.
    selected_documents, selected_ids = runner._documents_v1(index, options["artifact_root"])
    specs, compiled = runner._compile_specs_v1()
    return SimpleNamespace(
        options=options, index=index, original_pages=original_pages,
        documents=selected_documents, ids=selected_ids, specs=specs, compiled=compiled,
        census_module=census_module,
    )


def _raw_census_authority_refs(fixture):
    root = fixture.options["artifact_root"]
    paths = [fixture.options["database"], root / fixture.options["corpus_index_ref"]["path"]]
    paths.extend(root / document[key]["path"]
                 for document in fixture.index["documents"]
                 for key in ("document_manifest_ref", "selection_ref"))
    return {str(path): (path.stat().st_size, sha256(path.read_bytes()).hexdigest()) for path in paths}


def _raw_census_stream(fixture, *, documents=None, callback=None, sink=None):
    censuses = []
    with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
        result = runner._evaluate_stream_v1(
            fixture.options["database"], fixture.documents if documents is None else documents,
            fixture.compiled, original_census_source=source,
            raw_census_sink=censuses.append if sink is None else sink,
            original_document_callback=callback,
        )
    return result, censuses


@pytest.mark.parametrize("disposition", ["ready", "unresolved", "unrelated_unresolved"])
def test_authenticated_raw_census_stream_retains_ready_and_held_original_quarter_and_ytd_cells(
    tmp_path, monkeypatch, disposition,
):
    primary = _primary_page(_primary_tax_rows())
    if disposition == "unresolved":
        primary["sections"][0]["tables"][0]["rows"][1]["values_exact"][-1] = "không rõ"
    elif disposition == "unrelated_unresolved":
        unrelated = _row("Thu nhập từ hoạt động dịch vụ", "11", "12")
        unrelated["values_exact"] = ["11", "12", "13", "14"]
        primary["sections"][0]["tables"][0]["rows"] = [unrelated]
    empty = {"status": "NO_RELEVANT_FINANCIAL_CONTENT", "sections": [],
             "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, pages=[primary, empty])
    before = _raw_census_authority_refs(fixture)
    (indexed, trials, timing), censuses = _raw_census_stream(fixture)
    assert trials[0]["status"] == {
        "ready": runner.READY, "unresolved": runner.UNRESOLVED, "unrelated_unresolved": runner.UNRESOLVED,
    }[disposition]
    if disposition == "unrelated_unresolved":
        # The current family recovery retains this no-anchor algorithm HOLD.
        # An authenticated denominator is not a genuine-absence/N proof.
        assert trials[0]["reasons"] == ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]
    assert len(censuses) == 1
    census = censuses[0]
    table = primary["sections"][0]["tables"][0]
    expected = [value for row in table["rows"] for value in row["values_exact"]]
    assert [cell["raw_value_exact"] for cell in census["raw_money_cells"]] == expected
    assert [cell["original_raw_column_ordinal"] for cell in census["raw_money_cells"]] == [1, 2, 3, 4] * len(table["rows"])
    assert census["counts"]["raw_money_cells"] == 4 * len(table["rows"])
    assert census["counts"]["pages"] == 2 and census["counts"]["zero_money_pages"] == 1
    assert census["pages"][1]["status_exact"] == "NO_RELEVANT_FINANCIAL_CONTENT"
    assert census["tables"][0]["columns_exact"] == table["columns"]
    assert census["family_acceptance_claimed"] is census["dispositions_classified"] is False
    assert census["pdf_bytes_or_visuals_verified"] is False
    assert census["relevance"] == "UNASSESSED_NO_FAMILY_OWNER_ROLE_LANE_OR_ACCEPTANCE_DECISION"
    assert timing["selected_json_api_calls"] == 1 and timing["selected_json_sql_rows"] == 2
    assert indexed["selected_page_axis"]
    assert _raw_census_authority_refs(fixture) == before


def test_authenticated_raw_census_sparse_stream_retains_full_and_run_ordinals_separately(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=3)
    original = deepcopy(fixture.documents)
    selected, ordinals = runner._diagnostic_documents_v1(fixture.documents, document_ordinals=[2, 3])
    (_indexed, trials, timing), censuses = _raw_census_stream(fixture, documents=selected)
    assert ordinals == [2, 3]
    assert [census["source_binding"]["corpus_document_ordinal"] for census in censuses] == [2, 3]
    assert [census["source_binding"]["run_document_ordinal"] for census in censuses] == [1, 2]
    assert [trial["document_ordinal"] for trial in trials] == [1, 2]
    assert [census["pages"][0]["locator"]["document_ordinal"] for census in censuses] == [1, 2]
    assert censuses[0]["pages"][0]["locator"]["document_id"] != censuses[1]["pages"][0]["locator"]["document_id"]
    assert timing["selected_json_api_calls"] == 2
    assert fixture.documents == original


def test_authenticated_raw_census_stream_and_repair_callback_share_one_original_load(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    calls, callbacks = [], []
    actual = fixture.census_module.load_income_tax_source_page_json_versions_v1

    def counted(*args, **kwargs):
        calls.append(tuple(kwargs["page_json_version_ids"]))
        return actual(*args, **kwargs)

    def repair_authentication_callback(document, loaded):
        callbacks.append((deepcopy(document), deepcopy(loaded)))
        # A repair is allowed to operate on its own private clone, not this source.
        private = deepcopy(loaded)
        private[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"

    monkeypatch.setattr(fixture.census_module, "load_income_tax_source_page_json_versions_v1", counted)
    before = _raw_census_authority_refs(fixture)
    (_indexed, trials, timing), censuses = _raw_census_stream(fixture, callback=repair_authentication_callback)
    assert calls == [tuple(document["ids"]) for document in fixture.documents]
    assert len(callbacks) == len(censuses) == len(trials) == 2
    assert timing["selected_json_api_calls"] == 2
    for (_, loaded), census in zip(callbacks, censuses, strict=True):
        assert loaded[0]["page_json"] == fixture.original_pages[0]
        assert census["rows"][0]["row_exact"] == fixture.original_pages[0]["sections"][0]["tables"][0]["rows"][0]
    assert _raw_census_authority_refs(fixture) == before


@pytest.mark.parametrize("missing", ["source", "sink", "source_with_callback"])
def test_authenticated_raw_census_stream_requires_paired_source_sink_and_callback_owner(tmp_path, monkeypatch, missing):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
        kwargs = {"original_census_source": source, "raw_census_sink": lambda value: None}
        if missing == "sink":
            kwargs.pop("raw_census_sink")
        else:
            kwargs.pop("original_census_source")
            if missing == "source_with_callback":
                kwargs = {"original_document_callback": lambda document, loaded: None}
        with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
            runner._evaluate_stream_v1(fixture.options["database"], fixture.documents, fixture.compiled, **kwargs)


@pytest.mark.parametrize("fake_source", [{"authenticated": True}, {"status": "PASS"}, True])
def test_authenticated_raw_census_stream_cannot_accept_caller_approval_flags(tmp_path, monkeypatch, fake_source):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, fixture.census_module.GeminiIncomeTaxRawMoneyCensusV1Error)):
        runner._evaluate_stream_v1(
            fixture.options["database"], fixture.documents, fixture.compiled,
            original_census_source=fake_source, raw_census_sink=lambda value: None,
        )


@pytest.mark.parametrize("mutation", ["source_path", "source_sha", "selected_id", "physical_page"])
def test_authenticated_raw_census_stream_rejects_supplied_document_axis_drift(tmp_path, monkeypatch, mutation):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    changed = deepcopy(fixture.documents)
    if mutation == "source_path":
        changed[0]["manifest"]["document"]["source_logical_name"] = "vietstock_bctc/BANK/2025/other.pdf"
    elif mutation == "source_sha":
        changed[0]["manifest"]["document"]["source_sha256"] = "0" * 64
    elif mutation == "selected_id":
        changed[0]["ids"][0] = "gfpstorev1:json:" + "0" * 64
    else:
        changed[0]["manifest"]["pages"][0]["physical_page"] = 2
    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, fixture.census_module.GeminiIncomeTaxRawMoneyCensusV1Error)):
        _raw_census_stream(fixture, documents=changed)


@pytest.mark.parametrize("surface", ["document", "loaded"])
def test_authenticated_raw_census_callback_cannot_mutate_original_evaluation_inputs(tmp_path, monkeypatch, surface):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    before = _raw_census_authority_refs(fixture)

    def corrupt(document, loaded):
        if surface == "document":
            document["ids"].clear()
        else:
            loaded[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"

    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, fixture.census_module.GeminiIncomeTaxRawMoneyCensusV1Error)):
        _raw_census_stream(fixture, callback=corrupt)
    assert _raw_census_authority_refs(fixture) == before


def test_authenticated_raw_census_sink_cannot_poison_source_denominator_before_evaluation(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    before = _raw_census_authority_refs(fixture)

    def corrupt(census):
        census["raw_money_cells"][0]["raw_value_exact"] = "999"

    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, fixture.census_module.GeminiIncomeTaxRawMoneyCensusV1Error)):
        _raw_census_stream(fixture, sink=corrupt)
    assert _raw_census_authority_refs(fixture) == before


def _written_authenticated_raw_census_stream(fixture, output):
    output.mkdir()
    references, censuses = [], []

    def retain(census):
        censuses.append(deepcopy(census))
        references.append(runner._write_raw_census_document_v1(output, census))

    result, _ = _raw_census_stream(fixture, sink=retain)
    return result, references, censuses


def _authenticated_raw_cold_adapter(fixture, references, *, documents=None):
    return runner._make_authenticated_source_replay_adapter_v1(
        database=fixture.options["database"], database_ref=fixture.options["database_ref"],
        artifact_root=fixture.options["artifact_root"], corpus_index_ref=fixture.options["corpus_index_ref"],
        documents=fixture.documents if documents is None else documents, expected_census_refs=references,
    )


def _invoke_authenticated_raw_cold(fixture, adapter, indexed, *, ids=None):
    return adapter(
        source_page_database=fixture.options["database"],
        selected_page_json_version_ids=tuple(fixture.ids if ids is None else ids),
        indexed_query_evidence=indexed,
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            fixture.specs["topology"], fixture.specs["evaluation"], fixture.specs["schema"],
        ),
    )


def _rewrite_raw_census_reference(reference, census):
    # Adversarial self-reseal: all ordinary JSON IDs and byte pins are valid.
    census["census_id"] = "f39rawcellv1:census:" + canonical_json_sha256_v1(
        {key: value for key, value in census.items() if key != "census_id"}
    )
    raw = canonical_json_bytes_v1(census)
    Path(reference["census_ref"]["path"]).write_bytes(raw)
    reference["census_id"] = census["census_id"]
    reference["counts"] = deepcopy(census["counts"])
    reference["census_ref"].update(sha256=sha256(raw).hexdigest(), size_bytes=len(raw))


def test_authenticated_raw_census_warm_and_independent_cold_have_exact_cells_and_trials(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    calls = []
    actual = fixture.census_module.load_income_tax_source_page_json_versions_v1

    def counted(*args, **kwargs):
        calls.append(tuple(kwargs["page_json_version_ids"]))
        return actual(*args, **kwargs)

    monkeypatch.setattr(fixture.census_module, "load_income_tax_source_page_json_versions_v1", counted)
    before = _raw_census_authority_refs(fixture)
    (indexed, trials, _), references, censuses = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    retained = {ref["census_ref"]["path"]: Path(ref["census_ref"]["path"]).read_bytes() for ref in references}

    def forbidden(*args, **kwargs):
        raise AssertionError("Authenticated cold source replay consulted base cache")

    monkeypatch.setattr(runner.BaseClusterCache, "get_or_build", forbidden)
    cold_timing = []
    actual_stream = runner._evaluate_stream_v1

    def observe_cold(*args, **kwargs):
        assert kwargs["independent_base"] is not None
        result = actual_stream(*args, **kwargs)
        cold_timing.append(result[2])
        return result

    monkeypatch.setattr(runner, "_evaluate_stream_v1", observe_cold)
    adapter = _authenticated_raw_cold_adapter(fixture, references)
    cold = _invoke_authenticated_raw_cold(fixture, adapter, indexed)
    assert same_typed_json_v1(cold, trials)
    assert calls == [tuple(document["ids"]) for document in fixture.documents] * 2
    assert len(cold_timing) == 1
    metrics = cold_timing[0]["document_period_inventory_cache"]
    assert metrics["requests"] == metrics["disabled_requests"] == metrics["builds"] > 0
    assert metrics["hits"] == metrics["peak_entries"] == metrics["peak_stored_bytes"] == metrics["dependency_checks"] == 0
    for reference, expected in zip(references, censuses, strict=True):
        raw, actual_census = runner._read_raw_census_ref_v1(reference)
        assert actual_census == expected
        assert raw == retained[reference["census_ref"]["path"]]
    assert _raw_census_authority_refs(fixture) == before


@pytest.mark.parametrize("mutation", ["raw_cell", "selected_page", "row_axis", "false_acceptance", "source_hash"])
def test_authenticated_raw_census_cold_rejects_fully_self_resealed_warm_forgery(tmp_path, monkeypatch, mutation):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (indexed, _trials, _), references, censuses = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    forged = deepcopy(censuses[0])
    if mutation == "raw_cell":
        forged["raw_money_cells"][0]["raw_value_exact"] = "999"
    elif mutation == "selected_page":
        forged["source_binding"]["ordered_selected_page_axis"][0]["page_json_version_id"] = "gfpstorev1:json:" + "0" * 64
        forged["source_binding"]["ordered_selected_page_axis_sha256"] = canonical_json_sha256_v1(
            forged["source_binding"]["ordered_selected_page_axis"]
        )
    elif mutation == "row_axis":
        forged["rows"].reverse()
    elif mutation == "false_acceptance":
        forged["family_acceptance_claimed"] = True
    else:
        forged["source_binding"]["document_source_axis"]["source_sha256"] = "0" * 64
    _rewrite_raw_census_reference(references[0], forged)
    before = _raw_census_authority_refs(fixture)
    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, ValueError)):
        adapter = _authenticated_raw_cold_adapter(fixture, references)
        _invoke_authenticated_raw_cold(fixture, adapter, indexed)
    assert _raw_census_authority_refs(fixture) == before


@pytest.mark.parametrize("mutation", ["omit_census", "duplicate_census", "reverse_census", "query_axis", "selected_ids"])
def test_authenticated_raw_census_cold_rejects_incomplete_or_reordered_evidence_axes(tmp_path, monkeypatch, mutation):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    (indexed, _trials, _), references, _ = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    changed_indexed, ids = deepcopy(indexed), list(fixture.ids)
    if mutation == "omit_census":
        references.pop()
    elif mutation == "duplicate_census":
        references[1] = deepcopy(references[0])
    elif mutation == "reverse_census":
        references.reverse()
    elif mutation == "query_axis":
        changed_indexed["query_receipt"]["selected_page_count"] += 1
    else:
        ids.reverse()
    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, ValueError)):
        adapter = _authenticated_raw_cold_adapter(fixture, references)
        _invoke_authenticated_raw_cold(fixture, adapter, changed_indexed, ids=ids)


@pytest.mark.parametrize("target_file", ["database", "index", "manifest", "selection"])
def test_authenticated_raw_census_cold_source_drift_preserves_prior_outputs(tmp_path, monkeypatch, target_file):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (indexed, _trials, _), references, _ = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    retained = {ref["census_ref"]["path"]: Path(ref["census_ref"]["path"]).read_bytes() for ref in references}
    if target_file == "database":
        path = fixture.options["database"]
    elif target_file == "index":
        path = fixture.options["artifact_root"] / fixture.options["corpus_index_ref"]["path"]
    else:
        key = "document_manifest_ref" if target_file == "manifest" else "selection_ref"
        path = fixture.options["artifact_root"] / fixture.index["documents"][0][key]["path"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, ValueError)):
        adapter = _authenticated_raw_cold_adapter(fixture, references)
        _invoke_authenticated_raw_cold(fixture, adapter, indexed)
    assert all(Path(path).read_bytes() == raw for path, raw in retained.items())


def test_authenticated_raw_census_files_are_write_once_and_tamper_checked(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (_indexed, _trials, _), references, censuses = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    reference = references[0]
    path = Path(reference["census_ref"]["path"])
    original = path.read_bytes()
    with pytest.raises((runner.RunGeminiJsonIncomeTaxV1Error, FileExistsError)):
        runner._write_raw_census_document_v1(tmp_path / "warm", censuses[0])
    assert path.read_bytes() == original
    path.write_bytes(original + b" ")
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        runner._read_raw_census_ref_v1(reference)


def _raw_census_sweep(fixture, indexed, trials):
    return runner.build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=fixture.index["corpus_manifest_index_id"],
        topology_spec=fixture.specs["topology"], evaluation_spec=fixture.specs["evaluation"],
        schema_binding_spec=fixture.specs["schema"], trials=trials, indexed_query_evidence=indexed,
    )


def _raw_census_generic_ingest(fixture, results, sweep, adapter):
    index_path = fixture.options["artifact_root"] / fixture.options["corpus_index_ref"]["path"]
    implementation_ref = runner.generic._file_ref(PATH)
    return runner.ingest_gemini_accounting_family_sweep_v1(
        results, sweep=sweep, corpus_index_ref=runner.generic._file_ref(index_path),
        implementation_refs=[implementation_ref], run_kind="EXPERIMENTAL",
        source_page_database=fixture.options["database"], selected_page_json_version_ids=fixture.ids,
        corpus_artifact_root=fixture.options["artifact_root"], source_replay_adapter=adapter,
        source_replay_adapter_ref=implementation_ref,
    )


def test_authenticated_raw_census_persists_exact_per_document_blobs_under_real_family_run(tmp_path, monkeypatch):
    import sqlite3

    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    (indexed, trials, _), references, censuses = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    sweep = _raw_census_sweep(fixture, indexed, trials)
    adapter = _authenticated_raw_cold_adapter(fixture, references)
    results = tmp_path / "family-results.sqlite3"
    stored = _raw_census_generic_ingest(fixture, results, sweep, adapter)
    receipt = runner._store_raw_money_censuses_v1(results, family_run_id=stored["family_run_id"], census_refs=references)
    assert receipt["exact_per_document_blob_reload"] is True and receipt["document_count"] == 2
    assert receipt["family_acceptance_claimed"] is False
    with sqlite3.connect(results) as connection:
        rows = connection.execute(
            "SELECT document_ordinal,corpus_document_ordinal,census_id,census_sha256,census_bytes,source_ref_json "
            "FROM f39_raw_money_census_v1 WHERE family_run_id=? ORDER BY document_ordinal",
            (stored["family_run_id"],),
        ).fetchall()
        assert len(rows) == 2
        for row, reference, census in zip(rows, references, censuses, strict=True):
            raw = canonical_json_bytes_v1(census)
            assert row == (reference["document_ordinal"], reference["corpus_document_ordinal"], census["census_id"],
                           sha256(raw).hexdigest(), raw, canonical_json_bytes_v1(reference["census_ref"]))
        assert connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert runner.load_gemini_accounting_family_sweep_v1(results, stored["family_run_id"]) == sweep
    before = results.read_bytes()
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="already contains"):
        runner._store_raw_money_censuses_v1(results, family_run_id=stored["family_run_id"], census_refs=references)
    assert results.read_bytes() == before


@pytest.mark.parametrize("mutation", ["absent_run", "different_source", "omitted_document"])
def test_authenticated_raw_census_persistence_cannot_detach_from_family_run_source_axis(tmp_path, monkeypatch, mutation):
    import sqlite3

    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    (indexed, trials, _), references, censuses = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    stored = _raw_census_generic_ingest(
        fixture, tmp_path / "family-results.sqlite3", _raw_census_sweep(fixture, indexed, trials),
        _authenticated_raw_cold_adapter(fixture, references),
    )
    family_run_id = stored["family_run_id"]
    if mutation == "absent_run":
        family_run_id = "gjfafstorev1:run:" + "0" * 64
    elif mutation == "different_source":
        changed = deepcopy(censuses[0])
        changed["source_binding"]["document_source_axis"]["source_sha256"] = "0" * 64
        _rewrite_raw_census_reference(references[0], changed)
    else:
        references.pop()
    results = tmp_path / "family-results.sqlite3"
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        runner._store_raw_money_censuses_v1(results, family_run_id=family_run_id, census_refs=references)
    with sqlite3.connect(results) as connection:
        assert connection.execute("SELECT COUNT(*) FROM family_trial WHERE family_run_id=?", (stored["family_run_id"],)).fetchone() == (2,)
        exists = connection.execute("SELECT name FROM sqlite_master WHERE name='f39_raw_money_census_v1'").fetchone()
        if exists:
            assert connection.execute("SELECT COUNT(*) FROM f39_raw_money_census_v1").fetchone() == (0,)


def test_authenticated_raw_census_cold_exit_barrier_blocks_generic_persistence_and_preserves_warm_files(tmp_path, monkeypatch):
    from bctc_ai.storage.gemini_accounting_family_store_v1 import (
        GeminiAccountingFamilyStoreV1Error,
    )

    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (indexed, trials, _), references, _ = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    retained = {ref["census_ref"]["path"]: Path(ref["census_ref"]["path"]).read_bytes() for ref in references}
    index_path = fixture.options["artifact_root"] / fixture.options["corpus_index_ref"]["path"]
    actual_stream = runner._evaluate_stream_v1
    completed = []

    def evaluate_then_drift(*args, **kwargs):
        result = actual_stream(*args, **kwargs)
        completed.append(True)
        # The cold pass computed matching trial/census objects, but its owning
        # source context has not yet authenticated its exit barrier.
        index_path.write_bytes(index_path.read_bytes() + b" ")
        return result

    adapter = _authenticated_raw_cold_adapter(fixture, references)
    monkeypatch.setattr(runner, "_evaluate_stream_v1", evaluate_then_drift)
    results = tmp_path / "must-not-exist.sqlite3"
    with pytest.raises(GeminiAccountingFamilyStoreV1Error) as captured:
        _raw_census_generic_ingest(fixture, results, _raw_census_sweep(fixture, indexed, trials), adapter)
    assert type(captured.value) is GeminiAccountingFamilyStoreV1Error
    cause = captured.value.__cause__
    assert type(cause) is fixture.census_module.GeminiIncomeTaxRawMoneyCensusV1Error
    assert str(cause) in {"Authority file identity changed", "Authority file bytes changed"}
    assert completed == [True]
    assert not results.exists()
    assert all(Path(path).read_bytes() == raw for path, raw in retained.items())


def test_authenticated_raw_census_summary_never_claims_dispositions_or_source_authentication(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (_indexed, _trials, _), references, _ = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    summary = runner._raw_census_summary_v1(references)
    assert summary["status"] == "PASS_RETAINED_RAW_CENSUS_BYTES_NOT_SOURCE_AUTHENTICATION_OR_ACCEPTANCE"
    assert summary["family_acceptance_claimed"] is summary["all_raw_family_coverage_acceptance_claimed"] is False
    assert summary["dispositions_classified"] is summary["raw_cells_normalized_or_repaired"] is False
    assert "source_context_successfully_exited" not in summary


def test_authenticated_raw_census_keeps_unrelated_held_parallel_blank_dash_zero_and_negative_cells(tmp_path, monkeypatch):
    row = _row("Thu nhập từ hoạt động dịch vụ", None, "-")
    row["values_exact"] = [None, "-", "0", "(1)"]
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, pages=[_primary_page([row])])
    (_indexed, trials, _timing), censuses = _raw_census_stream(fixture)
    # Retain the exact algorithm gap instead of fabricating NOT_OBSERVED from
    # an unrelated row or claiming that raw retention classified its meaning.
    assert trials[0]["status"] == runner.UNRESOLVED
    assert trials[0]["reasons"] == ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]
    assert censuses[0]["counts"]["raw_money_cells"] == 4
    assert [cell["raw_value_exact"] for cell in censuses[0]["raw_money_cells"]] == [None, "-", "0", "(1)"]
    assert [cell["raw_lexical_state"] for cell in censuses[0]["raw_money_cells"]] == [
        "RAW_NULL", "RAW_NONEMPTY_STRING", "RAW_NONEMPTY_STRING", "RAW_NONEMPTY_STRING",
    ]
    assert censuses[0]["rows"][0]["row_exact"] == row
    assert censuses[0]["dispositions_classified"] is False


def test_authenticated_raw_census_evaluator_cannot_mutate_original_records_after_emitting_census(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    actual_trial = runner._trial_v1
    before = _raw_census_authority_refs(fixture)

    def corrupt_after_trial(cluster, records, compiled):
        result = actual_trial(cluster, records, compiled)
        records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"
        return result

    monkeypatch.setattr(runner, "_trial_v1", corrupt_after_trial)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        _raw_census_stream(fixture)
    assert _raw_census_authority_refs(fixture) == before


def test_authenticated_raw_census_closed_source_cannot_be_reused_for_another_stream(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
        pass
    with pytest.raises(fixture.census_module.GeminiIncomeTaxRawMoneyCensusV1Error, match="closed"):
        runner._evaluate_stream_v1(
            fixture.options["database"], fixture.documents, fixture.compiled,
            original_census_source=source, raw_census_sink=lambda census: None,
        )


def test_authenticated_raw_census_sparse_independent_cold_keeps_original_index_membership(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=3)
    documents = [fixture.documents[1], fixture.documents[2]]
    references = []
    output = tmp_path / "sparse-warm"
    output.mkdir()

    def retain(census):
        references.append(runner._write_raw_census_document_v1(output, census))

    (indexed, trials, _), _censuses = _raw_census_stream(fixture, documents=documents, sink=retain)
    adapter = _authenticated_raw_cold_adapter(fixture, references, documents=documents)
    ids = [version for document in documents for version in document["ids"]]
    cold = _invoke_authenticated_raw_cold(fixture, adapter, indexed, ids=ids)
    assert same_typed_json_v1(cold, trials)
    assert [ref["document_ordinal"] for ref in references] == [1, 2]
    assert [ref["corpus_document_ordinal"] for ref in references] == [2, 3]


def test_authenticated_raw_census_run_pins_both_actual_authority_validator_implementations(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    pdf_root = tmp_path / "empty-pdf-root"
    pdf_root.mkdir()
    output = tmp_path / "provisional-output"
    captured = {}
    actual_ref = runner.generic._file_ref

    class StopBeforeOriginalSourceOpen(RuntimeError):
        pass

    def observe_reference(path):
        reference = actual_ref(path)
        captured[Path(path).resolve()] = deepcopy(reference)
        return reference

    def stop_without_approving_source(*args, **kwargs):
        raise StopBeforeOriginalSourceOpen("Dependency pins captured; no source capability granted")

    monkeypatch.setattr(runner.generic, "_file_ref", observe_reference)
    monkeypatch.setattr(runner, "open_income_tax_original_census_source_v1", stop_without_approving_source)
    args = SimpleNamespace(
        repo_root=runner.ROOT,
        corpus_index=fixture.options["artifact_root"] / fixture.options["corpus_index_ref"]["path"],
        artifact_root=fixture.options["artifact_root"], source_page_database=fixture.options["database"],
        source_pdf_root=pdf_root, output_dir=output, results_database=output / "results.sqlite3",
        base_cluster_cache=None, source_page_scope=runner.PAGE_SCOPE_PATH,
        document_limit=None, document_ordinals=None,
    )
    with pytest.raises(StopBeforeOriginalSourceOpen, match="no source capability granted"):
        runner.run(args)
    for relative in (
        "src/bctc_ai/storage/gemini_current_corpus_manifest_index_v1.py",
        "src/bctc_ai/storage/gemini_current_document_manifest_selection_v1.py",
    ):
        path = (runner.ROOT / relative).resolve()
        assert path in captured
        assert captured[path] == actual_ref(path)
        assert captured[path]["sha256"] == sha256(path.read_bytes()).hexdigest()
        assert captured[path]["size_bytes"] == path.stat().st_size
    assert not args.results_database.exists()
