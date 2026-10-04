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
