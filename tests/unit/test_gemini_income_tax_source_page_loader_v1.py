from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_income_tax_family_v1 import _primary_page, _primary_tax_rows
from test_run_gemini_json_income_tax_accounting_family_v1 import runner

from bctc_ai.evaluation.gemini_financial_page_json_v1 import validate_financial_page_json_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage import gemini_financial_page_store_v1 as shared
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (
    GeminiIncomeTaxSourcePageReplayV1Error,
    load_income_tax_source_page_json_versions_v1,
    prove_lossless_text_label_validation_v1,
)


def _legacy_page(*, column_index=1):
    page = _primary_page(_primary_tax_rows())
    table = page["sections"][0]["tables"][0]
    table["columns"].insert(column_index, {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"})
    for row in table["rows"]:
        row["values_exact"].insert(column_index, row["label_exact"])
    return page


def _legacy_store(tmp_path, monkeypatch, page=None):
    page = page or _legacy_page()
    database = tmp_path / "historical-source.sqlite3"
    shared.initialize_gemini_financial_page_store_v1(database)
    # Simulate earlier ingestion retaining this canonical structure. Production
    # never patches a validator or writes the restored source database.
    with monkeypatch.context() as context:
        context.setattr(shared, "validate_financial_page_json_v1", deepcopy)
        stored = _ingest(database, page_json=page, physical_page=1)
    return database, stored, page


@pytest.mark.parametrize("column_index", [0, 1, 4])
def test_lossless_label_projection_retains_original_all_money_columns_and_cells(column_index):
    page = _legacy_page(column_index=column_index)
    before = canonical_json_bytes_v1(page)
    validated = validate_financial_page_json_v1(page)
    proof = prove_lossless_text_label_validation_v1(page, validated)
    assert len(proof) == 1
    assert proof[0]["redundant_text_column_ordinal"] == column_index + 1
    assert canonical_json_bytes_v1(page) == before
    assert len(page["sections"][0]["tables"][0]["columns"]) == 5


def test_exact_replay_and_group_blank_are_distinct_from_money_blank():
    ordinary = _primary_page(_primary_tax_rows())
    assert prove_lossless_text_label_validation_v1(ordinary, validate_financial_page_json_v1(ordinary)) == []
    page = _legacy_page()
    table = page["sections"][0]["tables"][0]
    group = deepcopy(table["rows"][0])
    group["label_exact"] = "Nhóm chỉ tiêu"
    group["hierarchy_path_exact"] = ["Nhóm chỉ tiêu"]
    group["row_kind"] = "GROUP"
    group["values_exact"] = [None] * len(table["columns"])
    table["rows"].insert(0, group)
    # The witness may retain an unpopulated label position on a GROUP. It never
    # replaces any of that group's financial blank cells with numeric zeros.
    validated = deepcopy(page)
    validated["sections"][0]["tables"][0]["columns"].pop(1)
    for row in validated["sections"][0]["tables"][0]["rows"]:
        row["values_exact"].pop(1)
    assert prove_lossless_text_label_validation_v1(page, validated)
    assert group["values_exact"] == [None] * 5


@pytest.mark.parametrize("mutation", [
    "money", "sign", "blank_zero", "dash_zero", "period", "unit", "label", "hierarchy",
    "row_kind", "row_order", "row_added", "row_removed", "section_title", "table_title",
    "narrative", "completion", "other_text", "column_order",
])
def test_additional_change_besides_duplicate_label_removal_fails_closed(mutation):
    page = _legacy_page()
    validated = validate_financial_page_json_v1(page)
    table = validated["sections"][0]["tables"][0]
    if mutation in {"money", "sign", "blank_zero", "dash_zero"}:
        raw = {"money": "999", "sign": "(10)", "blank_zero": None, "dash_zero": "-"}[mutation]
        page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = raw
        table["rows"][0]["values_exact"][0] = "0" if mutation in {"blank_zero", "dash_zero"} else "11"
    elif mutation == "period":
        table["columns"][0]["header_path_exact"] = ["Quý I năm 2025"]
    elif mutation == "unit":
        table["unit_exact"] = "VND"
    elif mutation in {"label", "hierarchy", "row_kind"}:
        key = {"label": "label_exact", "hierarchy": "hierarchy_path_exact", "row_kind": "row_kind"}[mutation]
        table["rows"][0][key] = ["khác"] if mutation == "hierarchy" else "khác"
    elif mutation == "row_order":
        table["rows"].reverse()
    elif mutation == "row_added":
        table["rows"].append(deepcopy(table["rows"][0]))
    elif mutation == "row_removed":
        table["rows"].pop()
    elif mutation == "section_title":
        validated["sections"][0]["title_exact"] = "khác"
    elif mutation == "table_title":
        table["title_exact"] = "khác"
    elif mutation == "narrative":
        validated["sections"][0]["narratives_exact"] = ["khác"]
    elif mutation == "completion":
        validated["completion"]["all_relevant_content_transcribed"] = False
    elif mutation == "other_text":
        table["rows"][0]["values_exact"].append("Thuyết minh khác")
        table["columns"].append({"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"})
    elif mutation == "column_order":
        table["columns"].reverse()
    with pytest.raises(GeminiIncomeTaxSourcePageReplayV1Error):
        prove_lossless_text_label_validation_v1(page, validated)


@pytest.mark.parametrize("mutation", ["not_duplicate", "nontext", "short_row", "blank_item", "only_blank_groups"])
def test_column_removal_without_complete_observed_duplicate_text_labels_fails(mutation):
    page = _legacy_page()
    table = page["sections"][0]["tables"][0]
    if mutation == "not_duplicate":
        table["rows"][0]["values_exact"][1] = "Nhóm khác"
    elif mutation == "nontext":
        table["columns"][1]["value_kind"] = "MONEY"
    elif mutation == "short_row":
        table["rows"][0]["values_exact"].pop()
    elif mutation == "blank_item":
        table["rows"][0]["values_exact"][1] = None
    else:
        for row in table["rows"]:
            row["row_kind"] = "GROUP"
            row["values_exact"][1] = None
    target = deepcopy(page)
    target["sections"][0]["tables"][0]["columns"].pop(1)
    for row in target["sections"][0]["tables"][0]["rows"]:
        row["values_exact"].pop(1)
    with pytest.raises(GeminiIncomeTaxSourcePageReplayV1Error):
        prove_lossless_text_label_validation_v1(page, target)


def test_real_sqlite_legacy_page_original_bytes_and_receipt_are_authenticated(tmp_path, monkeypatch):
    db, stored, original = _legacy_store(tmp_path, monkeypatch)
    before = sha256(db.read_bytes()).hexdigest()
    with pytest.raises(shared.GeminiFinancialPageStoreV1Error, match="canonical JSON does not replay"):
        shared.load_page_json_versions_v1(db, page_json_version_ids=[stored["page_json_version_id"]])
    loaded = load_income_tax_source_page_json_versions_v1(db, page_json_version_ids=[stored["page_json_version_id"]])[0]
    assert same_typed_json_v1(loaded["page_json"], original)
    receipt = loaded["source_json_replay_receipt"]
    assert receipt["classification"] == "LOSSLESS_REDUNDANT_TEXT_LABEL_COLUMN_NORMALIZATION"
    material = {k: v for k, v in receipt.items() if k != "replay_receipt_id"}
    assert receipt["replay_receipt_id"] == "f39sourcejsonv1:" + canonical_json_sha256_v1(material)
    assert receipt["canonical_json_sha256"] == sha256(canonical_json_bytes_v1(original) + b"\n").hexdigest()
    assert sha256(db.read_bytes()).hexdigest() == before


def test_legacy_page_hot_and_independent_cold_replay_keep_original_source_column_ordinals(tmp_path, monkeypatch):
    db, stored, original = _legacy_store(tmp_path, monkeypatch)
    source = {"source_logical_name": "report.pdf", "source_sha256": "b" * 64, "source_size_bytes": 123}
    document = {"manifest": {"document": source, "pages": [
        {"physical_page": 1, "page_json_version_id": stored["page_json_version_id"]}]},
        "ids": [stored["page_json_version_id"]]}
    specs, compiled = runner._compile_specs_v1()
    indexed, trials, timing = runner._evaluate_stream_v1(db, [document], compiled)
    assert trials[0]["status"] == runner.READY
    assert timing["exact_original_source_json_replay_page_count"] == 0
    assert len(timing["lossless_original_source_json_replay_receipts"]) == 1
    cold = runner.replay_income_tax_trials_from_source_v1(
        source_page_database=db, selected_page_json_version_ids=document["ids"],
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"]), indexed_query_evidence=indexed)
    assert same_typed_json_v1(cold, trials)
    assert canonical_json_bytes_v1(original) + b"\n" in db.read_bytes()


@pytest.mark.parametrize("mutation", ["bytes", "sha", "content_id", "noncanonical", "duplicate_key", "status"])
def test_original_storage_tamper_is_never_admitted_as_compatibility(tmp_path, monkeypatch, mutation):
    db, stored, page = _legacy_store(tmp_path, monkeypatch)
    with sqlite3.connect(db) as connection:
        if mutation == "bytes":
            connection.execute("UPDATE page_json_version SET canonical_json_bytes=?", (b"{}",))
        elif mutation == "sha":
            connection.execute("UPDATE page_json_version SET canonical_json_sha256=?", ("0" * 64,))
        elif mutation == "content_id":
            connection.execute("UPDATE page_json_version SET page_id=?", ("gfpstorev1:page:" + "0" * 64,))
        elif mutation == "status":
            connection.execute("UPDATE page_json_version SET page_status=?", ("NO_RELEVANT_FINANCIAL_CONTENT",))
        else:
            raw = (json.dumps(page, ensure_ascii=False) + "\n").encode()
            if mutation == "duplicate_key":
                raw = raw.replace(b'{', b'{"status":"UNRESOLVED_PAGE",', 1)
            # Resealing a hash cannot make altered bytes the selected version.
            connection.execute("UPDATE page_json_version SET canonical_json_bytes=?, canonical_json_sha256=?",
                               (raw, sha256(raw).hexdigest()))
    with pytest.raises((GeminiIncomeTaxSourcePageReplayV1Error, shared.GeminiFinancialPageStoreV1Error)):
        load_income_tax_source_page_json_versions_v1(db, page_json_version_ids=[stored["page_json_version_id"]])


def test_batched_selected_order_and_duplicate_missing_or_invalid_provenance_fail(tmp_path):
    db = tmp_path / "source.sqlite3"
    shared.initialize_gemini_financial_page_store_v1(db)
    page = _primary_page(_primary_tax_rows())
    first = _ingest(db, page_json=page, physical_page=1)
    second = _ingest(db, page_json=page, physical_page=2, image_sha256="f" * 64)
    ids = [second["page_json_version_id"], first["page_json_version_id"]]
    loaded = load_income_tax_source_page_json_versions_v1(db, page_json_version_ids=ids)
    assert [row["physical_page"] for row in loaded] == [2, 1]
    assert all(row["source_json_replay_receipt"]["classification"] == "EXACT_REPLAY" for row in loaded)
    for bad in [[], [ids[0], ids[0]], ["gfpstorev1:json:" + "0" * 64]]:
        with pytest.raises(shared.GeminiFinancialPageStoreV1Error):
            load_income_tax_source_page_json_versions_v1(db, page_json_version_ids=bad)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE extraction_run SET prompt_variant=?", ("unregistered",))
    with pytest.raises(shared.GeminiFinancialPageStoreV1Error):
        load_income_tax_source_page_json_versions_v1(db, page_json_version_ids=ids)
