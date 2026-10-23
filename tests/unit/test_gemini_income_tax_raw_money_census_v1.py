from __future__ import annotations

import asyncio
import json
import os
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_income_tax_family_v1 import _primary_page, _primary_tax_rows

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage import gemini_financial_page_store_v1 as page_store
from bctc_ai.storage import gemini_income_tax_raw_money_census_v1 as target
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    build_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    build_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (
    GeminiIncomeTaxSourcePageReplayV1Error,
)


def _put(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes_v1(value)
    path.write_bytes(raw)
    return {"path": relative, "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _fixture(tmp_path, monkeypatch, *, pages=None, year="2025", legacy=False, documents=1,
             prompt_variant="compact", prompt_sha256="d" * 64,
             prompt_digest_encoding=False, manifest_v4=False):
    root = tmp_path / "artifacts"
    root.mkdir()
    database = root / "source.sqlite3"
    page_store.initialize_gemini_financial_page_store_v1(database)
    pages = deepcopy(pages) if pages is not None else [_primary_page(_primary_tax_rows())]
    if legacy:
        table = pages[0]["sections"][0]["tables"][0]
        table["columns"].insert(1, {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"})
        for row in table["rows"]:
            row["values_exact"].insert(1, row["label_exact"])
    authorities = []
    for document_ordinal in range(1, documents + 1):
        logical = f"vietstock_bctc/BANK/{year}/{document_ordinal}.pdf"
        source = {"source_logical_name": logical, "source_sha256": "b" * 64, "source_size_bytes": 123}
        frontier = []
        for physical, page in enumerate(pages, 1):
            image_sha = f"{physical:064x}"
            with monkeypatch.context() as patch:
                if legacy:
                    patch.setattr(page_store, "validate_financial_page_json_v1", deepcopy)
                stored = _ingest(database, source_logical_name=logical, physical_page=physical,
                                 image_sha256=image_sha, page_json=page,
                                 prompt_variant=prompt_variant, prompt_sha256=prompt_sha256)
            frontier.append({"physical_page": physical, "page_json_version_id": stored["page_json_version_id"]})
        material = {"document": {**source, "document_id": "gfpstorev1:document:" + canonical_json_sha256_v1(source)},
                    "page_count": len(frontier), "pages": frontier}
        if manifest_v4:
            material.update(format_version="GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
                            extraction_contract={"prompt_sha256": prompt_sha256})
        manifest = {**material, "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material)}
        document_root = f"documents/{document_ordinal}"
        local_manifest = "current-document-manifests/manifest.json"
        manifest_ref = _put(root, f"{document_root}/{local_manifest}", manifest)
        plan_id = "gjfpdocv1:" + canonical_json_sha256_v1(source)
        selection = build_current_document_manifest_selection_v1(
            document_plan_id=plan_id, source_sha256=source["source_sha256"],
            document_manifest_id=manifest["document_manifest_id"],
            document_manifest_ref={**manifest_ref, "path": local_manifest},
            page_image_frontier_sha256=canonical_json_sha256_v1([
                {"physical_page": physical, "image_sha256": f"{physical:064x}"}
                for physical in range(1, len(pages) + 1)
            ]),
            page_prompt_frontier_sha256=canonical_json_sha256_v1([
                {"physical_page": physical,
                 "prompt_sha256" if prompt_digest_encoding else "prompt_variant":
                     prompt_sha256 if prompt_digest_encoding else prompt_variant}
                for physical in range(1, len(pages) + 1)
            ]), prior_selection_ids=[],
        )
        selection_ref = _put(root, f"{document_root}/current-document-manifest-selections/selection.json", selection)
        counts = Counter(page["status"] for page in pages)
        authorities.append({"source_ordinal": document_ordinal, "relative_path": logical,
                            "source_sha256": source["source_sha256"], "source_size_bytes": 123,
                            "document_plan_id": plan_id, "document_manifest_id": manifest["document_manifest_id"],
                            "document_manifest_ref": manifest_ref, "selection_id": selection["selection_id"],
                            "selection_ref": selection_ref, "page_count": len(pages),
                            "page_json_frontier_sha256": canonical_json_sha256_v1(frontier),
                            "page_status_counts": {key: counts[key] for key in (
                                "FINANCIAL_NOTE_CONTENT", "MIXED_FINANCIAL_CONTENT",
                                "NO_RELEVANT_FINANCIAL_CONTENT", "PRIMARY_FINANCIAL_STATEMENT")},
                            "provider_counts": [{"count": len(pages), "gateway": "GOOGLE_GEMINI_API",
                                                 "selected_provider": "GOOGLE_GEMINI_API", "selected_service_tier": "flex"}]})
    database_ref = {"path": "source.sqlite3", "sha256": sha256(database.read_bytes()).hexdigest(),
                    "size_bytes": database.stat().st_size}
    index = build_current_corpus_manifest_index_v1(
        corpus_plan_id="gjfpcorpusv1:" + "1" * 64, corpus_run_id="gjfpcrunv1:" + "2" * 64,
        corpus_plan_ref={"path": "plan.json", "sha256": "3" * 64, "size_bytes": 10},
        database_ref=database_ref, ledger_ref={"path": "ledger.sqlite3", "sha256": "4" * 64, "size_bytes": 10},
        documents=authorities,
        store_usage_summary={"attempts": [], "cached_input_tokens": 0, "input_tokens": 0,
                             "output_tokens": 0, "thought_tokens": 0, "run_count": len(pages) * documents,
                             "total_cost_usd": "0.000000000000"},
    )
    index_ref = _put(root, "indexes/index.json", index)
    return {"database": database, "artifact_root": root, "database_ref": database_ref,
            "corpus_index_ref": index_ref}, index, pages


def _load(source, corpus=1, run=1):
    return target.load_income_tax_original_document_census_v1(
        source, corpus_document_ordinal=corpus, run_document_ordinal=run,
    )


def test_single_official_load_four_money_denominator_and_hash_domains(tmp_path, monkeypatch):
    options, _, original = _fixture(tmp_path, monkeypatch, legacy=True)
    calls = []
    actual = target.load_income_tax_source_page_json_versions_v1

    def counted(*args, **kwargs):
        calls.append(tuple(kwargs["page_json_version_ids"]))
        return actual(*args, **kwargs)

    monkeypatch.setattr(target, "load_income_tax_source_page_json_versions_v1", counted)
    before = options["database"].read_bytes()
    with target.open_income_tax_original_census_source_v1(**options) as source:
        result = _load(source)
    census = result["census"]
    assert len(calls) == 1
    assert result["records"][0]["page_json"] == original[0]
    assert census["counts"]["raw_money_cells"] == 12
    assert census["tables"][0]["raw_money_column_ordinals"] == [1, 3, 4, 5]
    assert [cell["original_raw_column_ordinal"] for cell in census["raw_money_cells"][:4]] == [1, 3, 4, 5]
    page = census["pages"][0]
    assert page["stored_blob_sha256"] == sha256(canonical_json_bytes_v1(original[0]) + b"\n").hexdigest()
    assert page["original_object_canonical_sha256"] == canonical_json_sha256_v1(original[0])
    assert page["stored_blob_sha256"] != page["original_object_canonical_sha256"]
    assert page["validated_object_canonical_sha256"] != page["original_object_canonical_sha256"]
    assert page["official_source_replay_receipt"]["classification"] == "LOSSLESS_REDUNDANT_TEXT_LABEL_COLUMN_NORMALIZATION"
    assert census["family_acceptance_claimed"] is census["dispositions_classified"] is False
    assert census["pdf_bytes_or_visuals_verified"] is False
    assert options["database"].read_bytes() == before


def test_all_statuses_zero_money_unknown_and_lexical_states_are_retained(tmp_path, monkeypatch):
    page = _primary_page(_primary_tax_rows())
    table = page["sections"][0]["tables"][0]
    table["rows"][0]["values_exact"] = [None, "-", "0", "(1)"]
    table["columns"].append({"header_path_exact": ["Chưa phân loại"], "value_kind": "UNKNOWN"})
    for row in table["rows"]:
        row["values_exact"].append("123")
    empty = {"status": "NO_RELEVANT_FINANCIAL_CONTENT", "sections": [],
             "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}
    note = deepcopy(page)
    note["status"] = "FINANCIAL_NOTE_CONTENT"
    note["sections"][0].update(content_kind="FINANCIAL_NOTE", statement_type="NOT_APPLICABLE")
    text_only = deepcopy(note)
    for column in text_only["sections"][0]["tables"][0]["columns"]:
        column["value_kind"] = "TEXT"
    options, _, _ = _fixture(tmp_path, monkeypatch, pages=[page, empty, note, text_only])
    with target.open_income_tax_original_census_source_v1(**options) as source:
        census = _load(source)["census"]
    assert census["counts"]["pages"] == 4
    assert census["counts"]["zero_money_pages"] == 2
    assert census["counts"]["raw_money_cells"] == 24
    assert census["counts"]["unassessed_unknown_raw_cell_positions"] == 6
    cells = census["raw_money_cells"][:4]
    assert [cell["raw_value_exact"] for cell in cells] == [None, "-", "0", "(1)"]
    assert [cell["raw_lexical_state"] for cell in cells] == ["RAW_NULL", "RAW_NONEMPTY_STRING", "RAW_NONEMPTY_STRING", "RAW_NONEMPTY_STRING"]
    assert census["tables"][0]["unassessed_unknown_column_ordinals"] == [5]


def test_source_and_output_branches_have_no_mutable_aliases_and_cold_repeats_exactly(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with target.open_income_tax_original_census_source_v1(**options) as source:
        authorities = source.document_authorities
        authorities[0]["ids"].clear()
        first = _load(source)
    pristine = deepcopy(first)
    first["records"][0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"
    assert first["loaded"] == pristine["loaded"]
    assert first["census"] == pristine["census"]
    first["census"]["rows"][0]["row_exact"]["values_exact"][0] = "888"
    assert first["census"]["raw_money_cells"] == pristine["census"]["raw_money_cells"]
    with target.open_income_tax_original_census_source_v1(**options) as cold:
        second = _load(cold)
    assert second == pristine
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="closed"):
        _load(source)


def test_sparse_run_ordinal_and_byte_identical_logical_sources_stay_distinct(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch, documents=2)
    with target.open_income_tax_original_census_source_v1(**options) as source:
        first = _load(source, corpus=1, run=7)
        second = _load(source, corpus=2, run=1)
    assert first["axis_document"]["source_sha256"] == second["axis_document"]["source_sha256"]
    assert first["axis_document"]["document_id"] != second["axis_document"]["document_id"]
    assert second["census"]["source_binding"]["corpus_document_ordinal"] == 2
    assert second["records"][0]["document_ordinal"] == 1
    assert first["census"]["raw_money_cells"][0]["cell_census_id"] != second["census"]["raw_money_cells"][0]["cell_census_id"]


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecars_rejected_before_source_load(tmp_path, monkeypatch, suffix):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    Path(str(options["database"]) + suffix).write_bytes(b"sidecar")
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="sidecar"):
        with target.open_income_tax_original_census_source_v1(**options):
            pytest.fail("sidecar context yielded")


@pytest.mark.parametrize("target_file", ["database", "index", "manifest", "selection"])
def test_scope_exit_rejects_actual_drift_even_after_successful_load(tmp_path, monkeypatch, target_file):
    options, index, _ = _fixture(tmp_path, monkeypatch)
    if target_file == "database":
        path = options["database"]
    else:
        reference = options["corpus_index_ref"] if target_file == "index" else index["documents"][0]["document_manifest_ref" if target_file == "manifest" else "selection_ref"]
        path = options["artifact_root"] / reference["path"]
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="changed"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)
            path.write_bytes(path.read_bytes() + b" ")


@pytest.mark.parametrize("year", ["2024", "2099"])
def test_out_of_scope_sources_rejected_at_authority_boundary(tmp_path, monkeypatch, year):
    options, _, _ = _fixture(tmp_path, monkeypatch, year=year)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="non-current"):
        with target.open_income_tax_original_census_source_v1(**options):
            pytest.fail("out-of-scope source yielded")


@pytest.mark.parametrize("ordinal", [0, -1, True, 1.0, 2])
def test_invalid_corpus_ordinals_latch_context_invalid(tmp_path, monkeypatch, ordinal):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="invalidated"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="ordinal"):
                _load(source, corpus=ordinal)


def test_no_supplied_loaded_records_or_approval_boolean_api(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="Use open"):
        target.IncomeTaxOriginalCensusSourceV1()
    with target.open_income_tax_original_census_source_v1(**options) as source:
        for extra in ({"loaded": []}, {"page_records": []}, {"authenticated": True}):
            with pytest.raises(TypeError):
                target.load_income_tax_original_document_census_v1(
                    source, corpus_document_ordinal=1, run_document_ordinal=1, **extra,
                )
        _load(source)


@pytest.mark.parametrize("where", ["loaded_missing", "loaded_extra", "loaded_reversed", "source", "physical", "original_value"])
def test_original_loader_boundary_rejects_incomplete_or_replaced_return(tmp_path, monkeypatch, where):
    pages = [_primary_page(_primary_tax_rows()), _primary_page(_primary_tax_rows())]
    options, _, _ = _fixture(tmp_path, monkeypatch, pages=pages)
    actual = target.load_income_tax_source_page_json_versions_v1

    def mutated(*args, **kwargs):
        result = actual(*args, **kwargs)
        if where == "loaded_missing":
            result.pop()
        elif where == "loaded_extra":
            result.append(deepcopy(result[0]))
        elif where == "loaded_reversed":
            result.reverse()
        elif where == "source":
            result[0]["source_sha256"] = "f" * 64
        elif where == "physical":
            result[0]["physical_page"] = 9
        else:
            result[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"
        return result

    monkeypatch.setattr(target, "load_income_tax_source_page_json_versions_v1", mutated)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)


@pytest.mark.parametrize("relative", ["../index.json", "/index.json", "C:/index.json", "indexes\\index.json", "indexes/./index.json"])
def test_index_path_cannot_escape_or_alias_artifact_root(tmp_path, monkeypatch, relative):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    options["corpus_index_ref"] = {**options["corpus_index_ref"], "path": relative}
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="escapes"):
        with target.open_income_tax_original_census_source_v1(**options):
            pytest.fail("unsafe path yielded")


def test_duplicate_document_load_cannot_be_caught_and_promoted(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="invalidated"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)
            with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="already loaded"):
                _load(source)


def test_pinned_index_and_database_bytes_checked_before_yield(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    options["database_ref"] = {**options["database_ref"], "sha256": "0" * 64}
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="SHA"):
        with target.open_income_tax_original_census_source_v1(**options):
            pytest.fail("unverified bytes yielded")


def test_authority_receipt_json_is_not_a_source_capability():
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="active original"):
        _load({"authenticated": True, "receipt_id": "self-resealed"})


def test_database_fd_is_closed_when_operation_fails(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="caller failure"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            descriptor = source._descriptor
            raise RuntimeError("caller failure")
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_duplicate_run_ordinal_invalidates_source_even_if_caught(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch, documents=2)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="invalidated"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source, corpus=1, run=17)
            with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="Run document ordinal"):
                _load(source, corpus=2, run=17)
            with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="invalidated"):
                _load(source, corpus=2, run=18)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecars_created_after_load_fail_context_exit(tmp_path, monkeypatch, suffix):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="sidecar"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)
            Path(str(options["database"]) + suffix).write_bytes(b"late sidecar")
    with pytest.raises(OSError):
        os.fstat(source._descriptor)


def test_same_bytes_database_path_replacement_is_not_same_open_source(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    replacement = tmp_path / "replacement.sqlite3"
    replacement.write_bytes(options["database"].read_bytes())
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="identity"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)
            os.replace(replacement, options["database"])


@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("size_bytes", 1)])
def test_resealed_selection_cannot_lie_about_local_manifest_byte_pins(tmp_path, monkeypatch, field, value):
    options, index, _ = _fixture(tmp_path, monkeypatch)
    document = index["documents"][0]
    path = options["artifact_root"] / document["selection_ref"]["path"]
    selection = json.loads(path.read_bytes())
    selection["document_manifest_ref"][field] = value
    selection["selection_id"] = "gjfcdmsv1:selection:" + canonical_json_sha256_v1({key: item for key, item in selection.items() if key != "selection_id"})
    document["selection_ref"] = _put(options["artifact_root"], document["selection_ref"]["path"], selection)
    document["selection_id"] = selection["selection_id"]
    index["document_selection_frontier_sha256"] = canonical_json_sha256_v1([
        {key: item[key] for key in ("document_manifest_id", "document_plan_id", "selection_id")}
        for item in index["documents"]
    ])
    index["corpus_manifest_index_id"] = "gjfccmiv1:index:" + canonical_json_sha256_v1({key: item for key, item in index.items() if key != "corpus_manifest_index_id"})
    options["corpus_index_ref"] = _put(options["artifact_root"], options["corpus_index_ref"]["path"], index)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="Selected manifest binding"):
        with target.open_income_tax_original_census_source_v1(**options):
            pytest.fail("bad local manifest reference yielded")


def test_cross_async_task_cannot_reuse_or_rescue_source_context(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)

    async def run():
        async def other_task(source):
            with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="owning thread/task"):
                _load(source)

        with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="invalidated"):
            with target.open_income_tax_original_census_source_v1(**options) as source:
                await asyncio.create_task(other_task(source))

    asyncio.run(run())


def test_blank_group_and_unlabelled_total_cells_are_not_silently_excluded(tmp_path, monkeypatch):
    page = _primary_page(_primary_tax_rows())
    table = page["sections"][0]["tables"][0]
    table["rows"].insert(0, {"label_exact": "Nhóm", "hierarchy_path_exact": ["Nhóm"],
                             "row_kind": "GROUP", "values_exact": [None, None, None, None]})
    table["rows"].append({"label_exact": None, "hierarchy_path_exact": [None],
                          "row_kind": "TOTAL", "values_exact": ["1", "2", "3", "4"]})
    options, _, _ = _fixture(tmp_path, monkeypatch, pages=[page])
    with target.open_income_tax_original_census_source_v1(**options) as source:
        census = _load(source)["census"]
    assert census["counts"]["raw_money_cells"] == 20
    assert [cell["raw_value_exact"] for cell in census["raw_money_cells"][:4]] == [None] * 4
    assert census["rows"][-1]["row_exact"]["label_exact"] is None
    assert census["rows"][-1]["row_exact"]["row_kind"] == "TOTAL"
    assert [cell["raw_value_exact"] for cell in census["raw_money_cells"][-4:]] == ["1", "2", "3", "4"]


def test_stored_empty_string_requiring_lossy_validator_change_cannot_gain_authentication(tmp_path, monkeypatch):
    page = _primary_page(_primary_tax_rows())
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = ""
    options, _, _ = _fixture(tmp_path, monkeypatch, pages=[page], legacy=True)
    before = options["database"].read_bytes()
    # The official ORIGINAL loader admits only exact replay or lossless duplicate
    # TEXT-label removal. Census cannot silently extend it to empty -> null.
    with pytest.raises(GeminiIncomeTaxSourcePageReplayV1Error, match="Validation changed"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)
    assert options["database"].read_bytes() == before


@pytest.mark.parametrize("where", ["source_ordinal", "document_count", "page_count", "status_nonzero", "status_zero", "provider_count"])
def test_coherently_resealed_authority_cannot_use_boolean_counts_or_ordinals(tmp_path, monkeypatch, where):
    options, index, _ = _fixture(tmp_path, monkeypatch)
    if where == "source_ordinal":
        index["documents"][0]["source_ordinal"] = True
    elif where in {"document_count", "page_count"}:
        index["summary"][where] = True
    elif where.startswith("status_"):
        key = "PRIMARY_FINANCIAL_STATEMENT" if where == "status_nonzero" else "FINANCIAL_NOTE_CONTENT"
        index["summary"]["page_status_counts"][key] = where == "status_nonzero"
    else:
        index["summary"]["provider_counts"][0]["count"] = True
    index["corpus_manifest_index_id"] = "gjfccmiv1:index:" + canonical_json_sha256_v1({
        key: value for key, value in index.items() if key != "corpus_manifest_index_id"
    })
    options["corpus_index_ref"] = _put(options["artifact_root"], options["corpus_index_ref"]["path"], index)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="plain"):
        with target.open_income_tax_original_census_source_v1(**options):
            pytest.fail("Boolean authority count was treated as an integer")


_SIMPLE_PROMPT_SHA = "2c1d1e6b26f96207616fbfbfc65b3cbaed1abff1b65a380bbb0b30c4d63b539c"


def _write_test_prompt_scope(monkeypatch, path, value):
    # Test-only independently byte-pinned local authority; no production loader,
    # source query, validation, replay, or approval result is mocked.
    raw = canonical_json_bytes_v1(value)
    path.write_bytes(raw)
    monkeypatch.setattr(target, "_PROMPT_ENCODING_SCOPE_PATH", path)
    monkeypatch.setattr(target, "_PROMPT_ENCODING_SCOPE_SHA256", sha256(raw).hexdigest())
    monkeypatch.setattr(target, "_PROMPT_ENCODING_SCOPE_SIZE_BYTES", len(raw))
    monkeypatch.setattr(target, "_PROMPT_ENCODING_DIAGNOSTIC_SCOPE_SHA256",
                        canonical_json_sha256_v1(value["scope"]))


def _legacy_prompt_fixture(tmp_path, monkeypatch, *, prompt_variant="simple", prompt_sha256=_SIMPLE_PROMPT_SHA):
    cfg = json.loads(target._PROMPT_ENCODING_SCOPE_PATH.read_bytes())
    pages = [_primary_page(_primary_tax_rows()), _primary_page(_primary_tax_rows())]
    options, index, _ = _fixture(tmp_path, monkeypatch, pages=pages,
                               prompt_variant=prompt_variant, prompt_sha256=prompt_sha256,
                               prompt_digest_encoding=True, manifest_v4=True)
    document = index["documents"][0]
    manifest = json.loads((options["artifact_root"] / document["document_manifest_ref"]["path"]).read_bytes())
    selection = json.loads((options["artifact_root"] / document["selection_ref"]["path"]).read_bytes())
    ids = [page["page_json_version_id"] for page in manifest["pages"]]
    cfg.update(corpus_manifest_index_id=index["corpus_manifest_index_id"],
               corpus_index_ref=deepcopy(options["corpus_index_ref"]),
               database_ref=deepcopy(options["database_ref"]))
    # Synthetic registration models the reviewed technical encoding only. It is
    # not evidence that this fixture has a real FULL271 partner or PDF review.
    cfg["scope"] = [{
        "source_ordinal": 1, "relative_path": document["relative_path"], "page_count": 2,
        "common_selection_ref": deepcopy(document["selection_ref"]),
        "full271_selection_ref": deepcopy(document["selection_ref"]),
        "selection_prompt_frontier_sha256": selection["page_prompt_frontier_sha256"],
        "replayed_prompt_frontier_sha256": canonical_json_sha256_v1([
            {"physical_page": physical, "prompt_variant": prompt_variant} for physical in (1, 2)
        ]),
        "selected_page_json_version_ids_sha256": canonical_json_sha256_v1(ids),
        "selected_page_json_version_ids_exactly_equal_full271": True,
        "page_image_frontier_replays_from_sqlite": True,
    }]
    keys = cfg["source_bindings"][0]
    cfg["source_bindings"] = [{key: deepcopy(document[key]) for key in keys}]
    cfg["diagnostic_scope_sha256"] = canonical_json_sha256_v1(cfg["scope"])
    path = tmp_path / "registered-prompt-scope.json"
    _write_test_prompt_scope(monkeypatch, path, cfg)
    return options, index, cfg, path, ids


def _reseal_prompt_test_index(options, index):
    index["document_selection_frontier_sha256"] = canonical_json_sha256_v1([
        {key: item[key] for key in ("document_manifest_id", "document_plan_id", "selection_id")}
        for item in index["documents"]
    ])
    index["corpus_manifest_index_id"] = "gjfccmiv1:index:" + canonical_json_sha256_v1({
        key: item for key, item in index.items() if key != "corpus_manifest_index_id"
    })
    options["corpus_index_ref"] = _put(options["artifact_root"], options["corpus_index_ref"]["path"], index)


def test_registered_prompt_encoding_production_scope_exact_twenty_and_literal_pin():
    raw = target._PROMPT_ENCODING_SCOPE_PATH.read_bytes()
    assert sha256(raw).hexdigest() == target._PROMPT_ENCODING_SCOPE_SHA256 == "2e23473ce9246764d3a37d112f6f42a567824ebd053834e8299641f8b5bdd479"
    assert len(raw) == target._PROMPT_ENCODING_SCOPE_SIZE_BYTES == 56250
    cfg = json.loads(raw)
    assert len(cfg["scope"]) == len(cfg["source_bindings"]) == 20
    assert sum(item["page_count"] for item in cfg["scope"]) == 1113
    assert canonical_json_sha256_v1(cfg["scope"]) == "218e69be9ccf1f620a3a4552f9f1d824b22b1aecee32a9641273285161b53151"
    assert [item["source_ordinal"] for item in cfg["scope"]] == [1, 7, 14, 15, 16, 17, 29, 40, 42, 45, 65, 80, 81, 87, 104, 109, 154, 179, 195, 201]
    assert cfg["corpus_index_ref"]["sha256"] == "acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1"
    assert cfg["database_ref"]["sha256"] == "a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220"
    assert cfg["database_ref"]["size_bytes"] == 553984000
    assert cfg["simple_prompt_sha256"] == _SIMPLE_PROMPT_SHA


def test_registered_prompt_encoding_public_context_original_census_and_fresh_cold(tmp_path, monkeypatch):
    options, _, _, _, _ = _legacy_prompt_fixture(tmp_path, monkeypatch)
    before = options["database"].read_bytes()
    with target.open_income_tax_original_census_source_v1(**options) as source:
        warm = _load(source, run=17)
    with target.open_income_tax_original_census_source_v1(**options) as source:
        cold = _load(source, run=17)
    assert cold == warm
    assert options["database"].read_bytes() == before
    proof = warm["census"]["source_binding"]["registered_prompt_frontier_encoding_witness"]
    assert proof["encoding"] == "PHYSICAL_PAGE_PROMPT_SHA256_OBSERVED"
    assert proof["recorded_sha256"] == proof["recomputed_sha256"] != proof["variant_encoding_sha256"]
    assert proof["prompt_body_sha256"] == _SIMPLE_PROMPT_SHA
    assert proof["financial_or_pdf_or_export_permission_granted"] is False
    assert proof["source_values_or_period_keys_modified"] is False
    assert all(item["source_json_replay_receipt"]["mapping_input"] == "ORIGINAL_STORED_JSON_UNMODIFIED"
               for item in warm["loaded"])
    assert warm["records"][0]["page_json"] == warm["loaded"][0]["page_json"]


def test_registered_prompt_encoding_standard_source_binding_unchanged(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch)
    with target.open_income_tax_original_census_source_v1(**options) as source:
        census = _load(source)["census"]
    assert "registered_prompt_frontier_encoding_witness" not in census["source_binding"]


@pytest.mark.parametrize("where", [
    "selection_ref", "source_sha256", "source_size_bytes", "document_plan_id", "document_manifest_id",
    "selected_ids", "reversed_selected_ids", "recorded_digest", "variant_digest", "page_count",
    "corpus_index_id", "corpus_index_ref", "database_ref",
])
def test_registered_prompt_encoding_exact_registered_axes_required(tmp_path, monkeypatch, where):
    options, _, cfg, path, ids = _legacy_prompt_fixture(tmp_path, monkeypatch)
    scope, binding = cfg["scope"][0], cfg["source_bindings"][0]
    if where == "selection_ref":
        scope["common_selection_ref"]["sha256"] = "0" * 64
    elif where in {"source_sha256", "document_plan_id", "document_manifest_id"}:
        binding[where] = "0" * 64
    elif where == "source_size_bytes":
        binding[where] += 1
    elif where in {"selected_ids", "reversed_selected_ids"}:
        scope["selected_page_json_version_ids_sha256"] = canonical_json_sha256_v1(
            list(reversed(ids)) if where.startswith("reversed") else ["gfpstorev1:json:" + "0" * 64]
        )
    elif where in {"recorded_digest", "variant_digest"}:
        scope["selection_prompt_frontier_sha256" if where == "recorded_digest" else "replayed_prompt_frontier_sha256"] = "0" * 64
    elif where == "page_count":
        scope["page_count"] += 1
    elif where == "corpus_index_id":
        cfg["corpus_manifest_index_id"] = "gjfccmiv1:index:" + "0" * 64
    else:
        cfg[where]["sha256"] = "0" * 64
    cfg["diagnostic_scope_sha256"] = canonical_json_sha256_v1(cfg["scope"])
    _write_test_prompt_scope(monkeypatch, path, cfg)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="invalidated"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error):
                _load(source)


@pytest.mark.parametrize("variant,body", [("compact", _SIMPLE_PROMPT_SHA), ("simple", "d" * 64)])
def test_registered_prompt_encoding_all_original_rows_must_be_simple_correct_body(tmp_path, monkeypatch, variant, body):
    options, _, _, _, _ = _legacy_prompt_fixture(tmp_path, monkeypatch, prompt_variant=variant, prompt_sha256=body)
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="body/manifest"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)


@pytest.mark.parametrize("where", ["unknown_selection", "image", "manifest_version", "manifest_prompt", "manifest_extra_prompt_axis"])
def test_registered_prompt_encoding_cannot_approve_resealed_unknown_source_axes(tmp_path, monkeypatch, where):
    options, index, cfg, cfg_path, _ = _legacy_prompt_fixture(tmp_path, monkeypatch)
    document = index["documents"][0]
    selection_path = options["artifact_root"] / document["selection_ref"]["path"]
    selection = json.loads(selection_path.read_bytes())
    if where in {"unknown_selection", "image"}:
        if where == "unknown_selection":
            selection["prior_selection_ids"] = ["gjfcdmsv1:selection:" + "f" * 64]
        else:
            selection["page_image_frontier_sha256"] = "0" * 64
    else:
        manifest_path = options["artifact_root"] / document["document_manifest_ref"]["path"]
        manifest = json.loads(manifest_path.read_bytes())
        if where == "manifest_version":
            manifest["format_version"] = "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3"
        elif where == "manifest_prompt":
            manifest["extraction_contract"]["prompt_sha256"] = "0" * 64
        else:
            manifest["extraction_contract"]["page_prompt_sha256s"] = []
        manifest["document_manifest_id"] = "gfdmv1:manifest:" + canonical_json_sha256_v1({
            key: item for key, item in manifest.items() if key != "document_manifest_id"
        })
        document["document_manifest_id"] = selection["document_manifest_id"] = manifest["document_manifest_id"]
        document["document_manifest_ref"] = _put(options["artifact_root"], document["document_manifest_ref"]["path"], manifest)
        selection["document_manifest_ref"].update({key: document["document_manifest_ref"][key] for key in ("sha256", "size_bytes")})
    selection["selection_id"] = "gjfcdmsv1:selection:" + canonical_json_sha256_v1({
        key: item for key, item in selection.items() if key != "selection_id"
    })
    document["selection_id"] = selection["selection_id"]
    document["selection_ref"] = _put(options["artifact_root"], document["selection_ref"]["path"], selection)
    _reseal_prompt_test_index(options, index)
    if where.startswith("manifest_"):
        # Rebind the synthetic authority to the actual coherently sealed new
        # index, so this negative reaches the manifest contract guard rather
        # than merely failing because its index/selection registration changed.
        cfg["corpus_manifest_index_id"] = index["corpus_manifest_index_id"]
        cfg["corpus_index_ref"] = deepcopy(options["corpus_index_ref"])
        cfg["source_bindings"] = [{key: deepcopy(document[key]) for key in cfg["source_bindings"][0]}]
        cfg["scope"][0]["common_selection_ref"] = deepcopy(document["selection_ref"])
        cfg["diagnostic_scope_sha256"] = canonical_json_sha256_v1(cfg["scope"])
        _write_test_prompt_scope(monkeypatch, cfg_path, cfg)
    match = "body/manifest" if where.startswith("manifest_") else "frontier"
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match=match):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)


@pytest.mark.parametrize("when", ["before_context", "after_load"])
def test_registered_prompt_encoding_authority_file_drift_rejected(tmp_path, monkeypatch, when):
    options, _, _, path, _ = _legacy_prompt_fixture(tmp_path, monkeypatch)
    if when == "before_context":
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(target.GeminiIncomeTaxRawMoneyCensusV1Error, match="Authority"):
        with target.open_income_tax_original_census_source_v1(**options) as source:
            _load(source)
            path.write_bytes(path.read_bytes() + b" ")
