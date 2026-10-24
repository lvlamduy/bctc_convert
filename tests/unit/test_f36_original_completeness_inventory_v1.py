"""UNRUN neutral inventory tests: real tiny stores, no mocked source authority."""
from __future__ import annotations

import inspect
import json
import sqlite3
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_income_tax_raw_money_census_v1 import _fixture, _put
from test_gemini_json_income_tax_family_v1 import _primary_page

from bctc_ai.evaluation import gemini_json_operating_expense_original_inventory_v1 as subject
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _pages():
    rows = [
        {"row_kind": "ITEM", "label_exact": "Unclassified literal", "hierarchy_path_exact": ["Unclassified literal"],
         "values_exact": [None, None, None, None]},
        {"row_kind": "GROUP", "label_exact": "Printed group", "hierarchy_path_exact": ["Printed group"],
         "values_exact": [None, None, None, None]},
        {"row_kind": "TOTAL", "label_exact": None, "hierarchy_path_exact": [None],
         "values_exact": ["1", "0", "-", "(1)"]},
    ]
    return [_primary_page(rows), {"status": "NO_RELEVANT_FINANCIAL_CONTENT", "sections": [],
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}]


def _records(report):
    return [json.loads(line) for line in Path(report["stream_path"]).read_bytes().splitlines()]


def _run(options, out, **kwargs):
    return subject.write_f36_original_completeness_inventory_v1(**options, out=out, **kwargs)


def _rebind_database(options, index):
    """Authorize changed synthetic DB bytes, but retain selected immutable VID/source identities."""
    database = options["database"]
    reference = {**options["database_ref"], "sha256": sha256(database.read_bytes()).hexdigest(),
                 "size_bytes": database.stat().st_size}
    changed = deepcopy(index)
    changed["database_ref"] = reference
    changed["corpus_manifest_index_id"] = "gjfccmiv1:index:" + canonical_json_sha256_v1(
        {k: v for k, v in changed.items() if k != "corpus_manifest_index_id"})
    return {**options, "database_ref": reference,
            "corpus_index_ref": _put(options["artifact_root"], options["corpus_index_ref"]["path"], changed)}


def test_complete_source_axes_include_null_item_group_unlabeled_total_and_no_relevant_page(tmp_path, monkeypatch):
    root = Path(subject.__file__).resolve().parents[3]
    for function, filename in ((_fixture, "test_gemini_income_tax_raw_money_census_v1.py"),
                               (_primary_page, "test_gemini_json_income_tax_family_v1.py"),
                               (_fixture.__globals__["_ingest"], "test_gemini_financial_page_store_v1.py")):
        assert Path(inspect.getfile(function)).resolve() == root / "tests/unit" / filename
    options, index, pages = _fixture(tmp_path, monkeypatch, pages=_pages(), documents=2, manifest_v4=True)
    before = sha256(options["database"].read_bytes()).hexdigest()
    report = _run(options, tmp_path / "inventory")
    assert report["status"] == "COMPLETE_NEUTRAL_INVENTORY_NOT_FAMILY_OR_PDF_PROOF", report["errors"]
    assert report["source_context_successfully_exited"] is True and report["errors"] == []
    assert report["complete_selected_page_frontier"] is True and report["status_filter_applied"] is False
    assert report["sql_integrity"] == [{"quick_check": "ok", "foreign_key_check": "EMPTY"}] * 2
    assert report["counts"]["document"] == 2 and report["counts"]["page"] == 4
    assert report["counts"]["row"] == 6 and report["counts"]["column"] == 8
    assert report["counts"]["value_slots"] == 24
    records = _records(report)
    rows = [row for row in records if row["record_type"] == "row"]
    assert {r["document_ordinal"] for r in rows} == {1, 2}
    assert all(r["page_json_version_id"].startswith("gfpstorev1:json:") for r in rows)
    assert rows[0]["fields"]["row_kind"]["value"] == "ITEM"
    assert rows[0]["value_axis"]["null_column_ordinals"] == [1, 2, 3, 4]
    assert rows[1]["fields"]["row_kind"]["value"] == "GROUP"
    assert rows[1]["value_axis"]["item_types"] == ["NoneType"] * 4
    assert rows[2]["fields"]["row_kind"]["value"] == "TOTAL"
    assert rows[2]["fields"]["label_exact"] == {"present": True, "value": None}
    assert rows[2]["value_axis"]["items_one_lf_sha256"] == [canonical_json_sha256_v1(v)
        for v in pages[0]["sections"][0]["tables"][0]["rows"][2]["values_exact"]]
    actual_axis = [r["axis"] for r in records if r["record_type"] == "page"]
    assert canonical_json_sha256_v1(actual_axis) == report["ordered_selected_page_axis_one_lf_sha256"]
    assert len(actual_axis) == index["summary"]["page_count"]
    assert sha256(options["database"].read_bytes()).hexdigest() == before
    assert all(report[key] is False for key in ("financial_acceptance", "family_seal", "pdf_absence_proved",
        "role_unit_period_or_value_permission_granted", "provider_or_reextraction_performed"))
    assert not any(key in r for r in records for key in ("acceptance", "report_norm_id", "coefficient", "family_disposition"))


def test_fresh_context_and_different_batch_sizes_have_identical_inventory_bytes_and_id(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch, pages=_pages(), manifest_v4=True)
    warm = _run(options, tmp_path / "first", batch_size=1)
    cold = _run(options, tmp_path / "fresh_context", batch_size=32)
    assert warm["errors"] == cold["errors"] == []
    assert warm["inventory_id"] == cold["inventory_id"]
    assert warm["stream_ref"] == cold["stream_ref"]
    assert _records(warm) == _records(cold)


@pytest.mark.parametrize("change", ["blob", "image", "prompt", "missing_version", "foreign_key"])
def test_resealed_synthetic_database_cannot_waive_original_content_provenance_or_sql_checks(tmp_path, monkeypatch, change):
    options, index, _ = _fixture(tmp_path, monkeypatch, pages=_pages(), manifest_v4=True)
    with sqlite3.connect(options["database"]) as connection:
        if change == "blob":
            blob = connection.execute("SELECT canonical_json_bytes FROM page_json_version LIMIT 1").fetchone()[0]
            connection.execute("UPDATE page_json_version SET canonical_json_bytes=?", (blob.replace(b'Unclassified literal', b'Changed literal'),))
        elif change == "image":
            connection.execute("UPDATE page SET image_sha256=?", ("0" * 64,))
        elif change == "prompt":
            connection.execute("UPDATE extraction_run SET prompt_variant='unregistered-test-prompt'")
        elif change == "missing_version":
            connection.execute("DELETE FROM page_json_version")
        else:
            connection.execute("UPDATE extraction_run SET page_id='absent-page'")
    report = _run(_rebind_database(options, index), tmp_path / "bad_source")
    assert report["status"] == "FAIL" and report["errors"]
    assert report["source_context_successfully_exited"] is False and "inventory_id" not in report
    assert report["complete_selected_page_frontier"] is False
    assert report["financial_acceptance"] is False


@pytest.mark.parametrize("authority", ["index", "manifest", "selection", "database", "sidecar"])
def test_late_authority_change_prevents_complete_inventory_without_discarding_partial_denominator(tmp_path, monkeypatch, authority):
    options, index, _ = _fixture(tmp_path, monkeypatch, pages=_pages(), manifest_v4=True)
    actual = subject._nodes
    changed = False

    def mutate_after_read(page):
        nonlocal changed
        yield from actual(page)
        if not changed:
            changed = True
            if authority == "sidecar":
                Path(str(options["database"]) + "-wal").write_bytes(b"late synthetic sidecar")
            else:
                relative = (options["corpus_index_ref"]["path"] if authority == "index" else
                            index["documents"][0]["document_manifest_ref" if authority == "manifest" else "selection_ref"]["path"] if authority in {"manifest", "selection"} else
                            options["database_ref"]["path"])
                path = options["artifact_root"] / relative
                with path.open("ab") as stream:
                    stream.write(b" ")

    # Mutation hook only; real source context/provenance/SQL/late guards run unchanged.
    monkeypatch.setattr(subject, "_nodes", mutate_after_read)
    report = _run(options, tmp_path / "late_change")
    assert report["status"] == "FAIL" and report["errors"]
    assert report["counts"]["page"] >= 1 and report["partial_stream_bytes"] > 0
    assert not report["source_context_successfully_exited"] and "inventory_id" not in report


def test_plain_typed_document_ordinal_is_not_bool_even_in_resealed_index(tmp_path, monkeypatch):
    options, index, _ = _fixture(tmp_path, monkeypatch, pages=_pages())
    changed = deepcopy(index)
    changed["documents"][0]["source_ordinal"] = True
    changed["corpus_manifest_index_id"] = "gjfccmiv1:index:" + canonical_json_sha256_v1(
        {k: v for k, v in changed.items() if k != "corpus_manifest_index_id"})
    options["corpus_index_ref"] = _put(options["artifact_root"], options["corpus_index_ref"]["path"], changed)
    report = _run(options, tmp_path / "bad_axis")
    assert report["status"] == "FAIL" and "inventory_id" not in report


def test_structure_only_retains_unknown_shapes_extra_cells_and_exact_null_types_without_grant():
    page = {"sections": [{"tables": [{"columns": [{}], "rows": [
        {"row_kind": "ITEM", "label_exact": None, "hierarchy_path_exact": None,
         "values_exact": [None, 0, 0.0, False]}, "unrecognized-original-row"]}]}, None]}
    before = deepcopy(page)
    records = list(subject._nodes(page))
    row = next(r for r in records if r["record_type"] == "row")
    assert row["value_axis"]["item_types"] == ["NoneType", "int", "float", "bool"]
    assert row["value_axis"]["null_column_ordinals"] == [1]
    assert len(set(row["value_axis"]["items_one_lf_sha256"])) == 4
    assert len([r for r in records if r["record_type"] == "unsupported_shape"]) >= 3
    assert page == before


def test_existing_output_is_never_reused_or_overwritten(tmp_path, monkeypatch):
    options, _, _ = _fixture(tmp_path, monkeypatch, pages=_pages())
    out = tmp_path / "occupied"
    out.mkdir()
    sentinel = out / "selected-original-inventory.jsonl"
    sentinel.write_bytes(b"prior immutable output\n")
    with pytest.raises(ValueError, match="Fresh exclusive"):
        _run(options, out)
    assert sentinel.read_bytes() == b"prior immutable output\n"


@pytest.mark.parametrize("batch_size", [True, 0, 33])
def test_no_invalid_batch_or_implicit_frontier_trimming(tmp_path, batch_size):
    with pytest.raises(ValueError, match="Batch size"):
        subject.write_f36_original_completeness_inventory_v1(database=tmp_path / "not_opened",
            database_ref={}, artifact_root=tmp_path, corpus_index_ref={}, out=tmp_path / "out", batch_size=batch_size)
    assert not (tmp_path / "out").exists()
