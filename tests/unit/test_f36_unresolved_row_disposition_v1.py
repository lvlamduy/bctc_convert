"""Synthetic source/frontier and IO-protocol tests; no real visual/PDF authority."""
from __future__ import annotations

import copy
import json
import sqlite3
from hashlib import sha256

import pytest
from test_gemini_json_operating_expense_family_v1 import (
    VERSION_ID,
    _base_rows,
    _operating_page,
    _source_row_coverage_inputs,
)

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation import gemini_json_operating_expense_unresolved_rows_v1 as held
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1 as digest
from scripts.experiments import run_gemini_json_operating_expense_accounting_family_v1 as runner


def _fixture(kind="INCOMPLETE_PRINTED_FRONTIER"):
    rows = _base_rows()
    # Real source-shaped positive: printed ASCII1..N identifies the top-level
    # population, while the original raw parent paths retain all nested detail.
    rows[3]["label_exact"] = "Chi đóng góp theo lương"
    rows[3]["hierarchy_path_exact"][-1] = rows[3]["label_exact"]
    renamed = {}
    for row in rows[:-1]:
        if row["hierarchy_path_exact"] == [row["label_exact"]]:
            renamed[row["label_exact"]] = f"{len(renamed) + 1}. {row['label_exact']}"
    for row in rows[:-1]:
        row["label_exact"] = renamed.get(row["label_exact"], row["label_exact"])
        row["hierarchy_path_exact"] = [renamed.get(item, item) for item in row["hierarchy_path_exact"]]
    if kind == "INCOMPLETE_PRINTED_FRONTIER":
        rows[-2]["values_exact"] = [None, None]
    rows[-1]["values_exact"] = ["80" if kind == "INCOMPLETE_PRINTED_FRONTIER" else "83", "70"]
    indexed, trials, pages, compiled = _source_row_coverage_inputs(_operating_page(rows))
    assert len(trials) == 1 and trials[0]["status"] == family.UNRESOLVED
    assert trials[0]["mappings"] == [] and trials[0]["mapping_count"] == 0
    raw = family.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=pages,
        compiled_specs=compiled, fail_on_violation=False)
    assert raw["violation_count"] > 0
    page = pages[1][VERSION_ID]
    blob = canonical_json_bytes_v1(page) + b"\n"
    blob_refs = {VERSION_ID: {"page_json_version_id": VERSION_ID, "stored_blob_sha256": sha256(blob).hexdigest(),
                            "stored_blob_size_bytes": len(blob), "original_object_sha256": digest(page)}}
    cluster = indexed["candidate_dispositions"][0]["cluster"]
    frontier = held.build_printed_frontier_v1(document=indexed["selected_document_axis"][0],
        page_axis=indexed["selected_page_axis"], pages=pages[1], cluster=cluster,
        compiled_specs=compiled, source_page_blob_refs=blob_refs)
    assert frontier["finding_kind"] == kind
    ref = {"path": "/external/review.json", "sha256": "a" * 64, "size_bytes": 1}
    review = {"document": indexed["selected_document_axis"][0], "source_size_bytes": 123,
              "status": trials[0]["status"], "reasons": trials[0]["reasons"], "trial_sha256": digest(trials[0]),
              "query_cluster_sha256": digest(cluster), "pdf_residual_audit_id": "residual:1",
              "manual_review_ref": ref, "manual_finding_id": "finding:1", "finding_kind": kind,
              "printed_frontier": frontier, "disposition": held.DISPOSITION,
              "held_rows": [{"axis_name": axis, "raw_coverage_item_sha256": digest(item)}
                            for axis in held.AXES for item in raw[axis] if item["coverage"].startswith("VIOLATION_")]}
    declaration = {"format_version": held.FORMAT, "family_id": "OPERATING_EXPENSE",
                   "corpus_manifest_index_id": "fixture-index:1", "raw_coverage_receipt_id": raw["receipt_id"],
                   "pdf_residual_spec_ref": ref, "reviews": [review]}
    residual = {"document_ordinal": 1, "source_sha256": review["document"]["source_sha256"],
                "source_size_bytes": 123, "status": review["status"], "reasons": review["reasons"],
                "residual_audit_id": "residual:1"}
    return {"corpus_manifest_index_id": "fixture-index:1", "raw_coverage": raw,
            "indexed_query_evidence": indexed, "trials": trials, "page_json_by_document": pages,
            "compiled_specs": compiled, "declaration": declaration, "declaration_ref": ref,
            "authenticated_pdf_residuals": [residual], "source_page_blob_refs": blob_refs}


@pytest.mark.parametrize("kind", sorted(held.KINDS))
def test_real_family_unresolved_rows_reconcile_without_numeric_mapping_or_raw_mutation(kind):
    kwargs = _fixture(kind)
    before = copy.deepcopy(kwargs)
    result = held.reconcile_unresolved_rows_v1(**kwargs)
    assert result["held_row_axis"] and result["unjoined_violation_count"] == 0
    assert kwargs == before
    assert kwargs["trials"][0]["mappings"] == []
    raw = kwargs["raw_coverage"]
    assert raw["violation_count"] > 0
    assert runner._validate_source_row_coverage_receipt_v1(raw, reconciliation=result) == raw
    with pytest.raises(ValueError, match="coverage gate failed"):
        runner._validate_source_row_coverage_receipt_v1(raw)
    proof = kwargs["declaration"]["reviews"][0]["printed_frontier"]
    if kind == "INCOMPLETE_PRINTED_FRONTIER":
        assert proof["unknown_operand_axis"] and not proof["contradiction_proven"]
        assert proof["equation"] == {"status": "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
        assert "component_sums" not in proof["equation"]
        assert proof["rows_exact"][-2]["values_exact"] == [None, None]
    else:
        assert proof["unknown_operand_axis"] == [] and proof["contradiction_proven"]
        assert proof["equation"]["status"] == "MISMATCH"


@pytest.mark.parametrize("attack", [
    "status-ready", "status-n", "reasons", "source", "trial-hash", "cluster", "raw-id",
    "finding-kind", "frontier-value", "frontier-column", "frontier-null-mask", "held-missing", "held-extra",
    "held-duplicate", "residual", "boolean-doc", "float-doc", "boolean-row", "blob-domain",
])
def test_declaration_or_source_tamper_never_becomes_a_hold_waiver(attack):
    kw = _fixture()
    review = kw["declaration"]["reviews"][0]
    if attack.startswith("status-"):
        review["status"] = family.READY if attack == "status-ready" else family.NOT_OBSERVED
    elif attack == "reasons":
        review["reasons"] = ["different-reason"]
    elif attack == "source":
        review["document"]["source_sha256"] = "d" * 64
    elif attack == "trial-hash":
        review["trial_sha256"] = "0" * 64
    elif attack == "cluster":
        review["query_cluster_sha256"] = "0" * 64
    elif attack == "raw-id":
        kw["declaration"]["raw_coverage_receipt_id"] = "wrong"
    elif attack == "finding-kind":
        review["finding_kind"] = "PRINTED_CONTRADICTION"
    elif attack == "frontier-value":
        review["printed_frontier"]["rows_exact"][-2]["values_exact"] = ["0", "0"]
    elif attack == "frontier-column":
        review["printed_frontier"]["money_column_ordinals"].reverse()
    elif attack == "frontier-null-mask":
        review["printed_frontier"]["unknown_operand_axis"].pop()
    elif attack == "held-missing":
        review["held_rows"].pop()
    elif attack == "held-extra":
        review["held_rows"].append({"axis_name": held.AXES[0], "raw_coverage_item_sha256": "0" * 64})
    elif attack == "held-duplicate":
        review["held_rows"].append(copy.deepcopy(review["held_rows"][0]))
    elif attack == "residual":
        kw["authenticated_pdf_residuals"] = []
    elif attack in {"boolean-doc", "float-doc"}:
        review["document"]["document_ordinal"] = True if attack == "boolean-doc" else 1.0
    elif attack == "boolean-row":
        kw["raw_coverage"]["source_row_axis"][0]["row_ordinal"] = True
    else:
        kw["source_page_blob_refs"][VERSION_ID]["stored_blob_sha256"] = "0" * 64
    with pytest.raises((ValueError, KeyError)):
        held.reconcile_unresolved_rows_v1(**kw)


@pytest.mark.parametrize("mutation", ["dash", "blank-without-review", "open", "unit", "wrong-owner", "unknown-row"])
def test_fresh_frontier_does_not_hide_unsupported_or_open_source(mutation):
    kw = _fixture("PRINTED_CONTRADICTION")
    page = kw["page_json_by_document"][1][VERSION_ID]
    table = page["sections"][0]["tables"][0]
    if mutation == "dash":
        table["rows"][0]["values_exact"][0] = "-"
    elif mutation == "blank-without-review":
        table["rows"][0]["values_exact"][0] = None
    elif mutation == "open":
        table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    elif mutation == "unit":
        table["unit_exact"] = "unknown unit"
    elif mutation == "wrong-owner":
        page["sections"][0]["content_kind"] = "PRIMARY_STATEMENT"
    else:
        table["rows"][0]["label_exact"] = "Khoản chưa được phân loại"
    # Updating a BLOB metadata packet is not approval: the fresh source/role,
    # type and complete reviewed frontier must still match independently.
    blob = canonical_json_bytes_v1(page) + b"\n"
    kw["source_page_blob_refs"][VERSION_ID].update(stored_blob_sha256=sha256(blob).hexdigest(),
        stored_blob_size_bytes=len(blob), original_object_sha256=digest(page))
    with pytest.raises((ValueError, KeyError)):
        held.reconcile_unresolved_rows_v1(**kw)


@pytest.mark.parametrize("attack", ["flat-salary", "flat-depreciation", "duplicate-role", "number-hole", "number-duplicate",
                                   "number-reversed", "number-unicode", "wrong-payroll-parent", "primary", "other", "unknown"])
def test_numbered_population_and_existing_local_scope_are_positive_admission_gates(attack):
    kw = _fixture()
    page = kw["page_json_by_document"][1][VERSION_ID]
    section, table = page["sections"][0], page["sections"][0]["tables"][0]
    rows = table["rows"]
    if attack in {"primary", "other", "unknown"}:
        section["statement_type"] = {"primary": "INCOME_STATEMENT", "other": "OTHER", "unknown": "UNKNOWN"}[attack]
    elif attack == "flat-salary":
        rows[2]["hierarchy_path_exact"] = [rows[2]["label_exact"]]
    elif attack == "flat-depreciation":
        rows[5]["hierarchy_path_exact"] = [rows[5]["label_exact"]]
    elif attack == "duplicate-role":
        # The text differs, numbering stays valid, but both claim one role.
        rows[11]["label_exact"] = "5. Chi nộp thuế và các khoản phí, lệ phí"
        rows[11]["hierarchy_path_exact"] = [rows[11]["label_exact"]]
    elif attack == "wrong-payroll-parent":
        rows[3]["hierarchy_path_exact"][0] = rows[4]["label_exact"]
        region = kw["indexed_query_evidence"]["candidate_dispositions"][0]["cluster"]["component_regions"][0]
        scopes = family._literal_payroll_scope_receipts_v1(table=table, original_table=table,
            locator=region, compiled_specs=kw["compiled_specs"])
        assert scopes and any(not item["complete"] for item in scopes)
    else:
        old = rows[0]["label_exact"]
        prefix = {"number-hole": "2", "number-duplicate": "2", "number-reversed": "6", "number-unicode": "１"}[attack]
        rows[0]["label_exact"] = prefix + old[1:]
        rows[0]["hierarchy_path_exact"] = [rows[0]["label_exact"]]
    blob = canonical_json_bytes_v1(page) + b"\n"
    kw["source_page_blob_refs"][VERSION_ID].update(stored_blob_sha256=sha256(blob).hexdigest(),
        stored_blob_size_bytes=len(blob), original_object_sha256=digest(page))
    with pytest.raises((ValueError, KeyError)):
        held.build_printed_frontier_v1(document=kw["indexed_query_evidence"]["selected_document_axis"][0],
            page_axis=kw["indexed_query_evidence"]["selected_page_axis"], pages=kw["page_json_by_document"][1],
            cluster=kw["indexed_query_evidence"]["candidate_dispositions"][0]["cluster"],
            compiled_specs=kw["compiled_specs"], source_page_blob_refs=kw["source_page_blob_refs"])


@pytest.mark.parametrize("attack", [None, "wrong-image", "wrong-page", "wrong-dpi"])
def test_actual_300dpi_pdf_render_binds_reviewed_png_without_mock_authentication(attack):
    """Actual synthetic PDF/render/PIL boundary only, no financial/source approval."""
    with runner.fitz.open() as pdf:
        for text in ("synthetic one", "synthetic two"):
            page = pdf.new_page(width=72, height=72)
            page.insert_text((5, 30), text, fontsize=6)
        pdf_bytes = pdf.tobytes()
    source_sha = sha256(pdf_bytes).hexdigest()
    with runner.fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        rendered = runner.render_full_pdf_page_v1(pdf[0], physical_page=1, dpi=300, source_sha256=source_sha)
        other = runner.render_full_pdf_page_v1(pdf[1], physical_page=2, dpi=300, source_sha256=source_sha)
    image_bytes = other.image if attack == "wrong-image" else rendered.image
    with runner.Image.open(runner.BytesIO(image_bytes)) as png:
        image = {"sha256": sha256(image_bytes).hexdigest(), "size_bytes": len(image_bytes),
                 "width": png.width, "height": png.height, "dpi": 200 if attack == "wrong-dpi" else 300}
    kwargs = {"pdf_bytes": pdf_bytes, "image_bytes": image_bytes, "image": image,
              "source_sha256": source_sha, "physical_page": 2 if attack == "wrong-page" else 1}
    if attack is None:
        runner._verify_reviewed_png_from_pdf_v1(**kwargs)
    else:
        with pytest.raises(ValueError):
            runner._verify_reviewed_png_from_pdf_v1(**kwargs)


@pytest.mark.parametrize("suffix", [None, "", " và chi phí khác", " theo tỷ lệ", " (Thuyết minh 15)"])
def test_fresh_qualified_literal_guard_is_not_absorbed_by_an_incomplete_frontier(suffix):
    kw = _fixture()
    page = kw["page_json_by_document"][1][VERSION_ID]
    table = page["sections"][0]["tables"][0]
    row = table["rows"][-2]
    if suffix is not None:
        row["label_exact"] = (
            "6. Trích lập/(hoàn nhập) dự phòng giảm giá đầu tư tài chính dài hạn "
            "(Thuyết minh 11)" + suffix)
        row["hierarchy_path_exact"] = [row["label_exact"]]
    # Rebuild actual public query/coalesced roles after changing a source role;
    # the pre-mutation cluster is not authority for the new printed literal.
    indexed, trials, pages, compiled = _source_row_coverage_inputs(copy.deepcopy(page))
    kw.update(indexed_query_evidence=indexed, trials=trials,
              page_json_by_document=pages, compiled_specs=compiled)
    page = pages[1][VERSION_ID]
    table = page["sections"][0]["tables"][0]
    row = table["rows"][-2]
    cluster = kw["indexed_query_evidence"]["candidate_dispositions"][0]["cluster"]
    region = cluster["component_regions"][0]
    receipts = family._qualified_provision_literal_receipts_v1(
        table=table, original_table=table, locator=region, compiled_specs=kw["compiled_specs"])
    assert bool(receipts) is (suffix is not None)
    if receipts:
        assert receipts[0]["complete"] is (suffix == "")
        assert receipts[0]["original_row_exact"] == row
        assert receipts[0]["evaluation_row_exact"] == row
        assert receipts[0]["parent_unit_period_value_or_mapping_permission_granted"] is False
    blob = canonical_json_bytes_v1(page) + b"\n"
    kw["source_page_blob_refs"][VERSION_ID].update(stored_blob_sha256=sha256(blob).hexdigest(),
        stored_blob_size_bytes=len(blob), original_object_sha256=digest(page))
    before = copy.deepcopy(kw)
    args = dict(document=kw["indexed_query_evidence"]["selected_document_axis"][0],
        page_axis=kw["indexed_query_evidence"]["selected_page_axis"], pages=kw["page_json_by_document"][1],
        cluster=cluster, compiled_specs=kw["compiled_specs"], source_page_blob_refs=kw["source_page_blob_refs"])
    if suffix not in (None, ""):
        with pytest.raises(ValueError, match="unproven whole qualified provision literal"):
            held.build_printed_frontier_v1(**args)
    else:
        proof = held.build_printed_frontier_v1(**args)
        assert proof["finding_kind"] == "INCOMPLETE_PRINTED_FRONTIER"
        assert proof["contradiction_proven"] is False
        if suffix is None:
            assert "qualified_provision_literal_receipts" not in proof
        else:
            assert proof["qualified_provision_literal_receipts"] == receipts
            assert proof["unknown_operand_axis"]
    assert kw == before


def test_resealed_caller_qualified_policy_does_not_authorize_a_frontier():
    kw = _fixture()
    compiled = kw["compiled_specs"]
    policy = compiled["operating_expense_qualified_provision_literal_policy"]
    policy["declarations"] = []
    compiled["operating_expense_qualified_provision_literal_policy_sha256"] = digest(policy)
    with pytest.raises(ValueError, match="qualified provision literal policy drifted"):
        held.build_printed_frontier_v1(document=kw["indexed_query_evidence"]["selected_document_axis"][0],
            page_axis=kw["indexed_query_evidence"]["selected_page_axis"], pages=kw["page_json_by_document"][1],
            cluster=kw["indexed_query_evidence"]["candidate_dispositions"][0]["cluster"],
            compiled_specs=compiled, source_page_blob_refs=kw["source_page_blob_refs"])


def test_resealed_reconciliation_cannot_drop_an_unjoined_violation():
    kw = _fixture()
    result = held.reconcile_unresolved_rows_v1(**kw)
    result["held_row_axis"].pop()
    result["held_row_axis_sha256"] = digest(result["held_row_axis"])
    result["receipt_id"] = "gjoeurd1:reconciliation:" + digest({k: v for k, v in result.items() if k != "receipt_id"})
    with pytest.raises(ValueError):
        held.validate_reconciliation_v1(kw["raw_coverage"], result)


def test_visible_review_uses_explicit_held_category_without_rewriting_raw_coverage():
    kw = _fixture()
    result = held.reconcile_unresolved_rows_v1(**kw)
    raw = copy.deepcopy(kw["raw_coverage"])
    viewed = runner._expected_pdf_visible_audit_rows_v1(raw, reconciliation=result)
    assert any(held.DISPOSITION in row["coverage"] for row in viewed)
    assert raw == kw["raw_coverage"] and raw["violation_axis"]


@pytest.mark.parametrize("attack", [None, "wrong-stored-sha", "different-object", "sidecar"])
def test_selected_original_blob_binding_is_read_only_and_rejects_validator_projection(tmp_path, attack):
    kw = _fixture()
    page = kw["page_json_by_document"][1][VERSION_ID]
    blob = canonical_json_bytes_v1(page) + b"\n"
    database = tmp_path / "synthetic.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE page_json_version(page_json_version_id TEXT PRIMARY KEY,canonical_json_bytes BLOB,canonical_json_sha256 TEXT)")
    connection.execute("INSERT INTO page_json_version VALUES(?,?,?)", (VERSION_ID, blob,
                       "0" * 64 if attack == "wrong-stored-sha" else sha256(blob).hexdigest()))
    connection.commit()
    connection.close()
    before = database.read_bytes()
    if attack == "different-object":
        kw["page_json_by_document"][1][VERSION_ID]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"
    if attack == "sidecar":
        database.with_name(database.name + "-wal").write_bytes(b"must not be ignored")
    if attack is None:
        actual = runner._row_original_blob_refs_v1(database, kw["indexed_query_evidence"], kw["page_json_by_document"], kw["declaration"])
        assert actual == kw["source_page_blob_refs"]
    else:
        with pytest.raises(ValueError):
            runner._row_original_blob_refs_v1(database, kw["indexed_query_evidence"], kw["page_json_by_document"], kw["declaration"])
    assert database.read_bytes() == before


@pytest.mark.parametrize("attack", [None, "warm-receipt", "residual-file"])
def test_cold_adapter_reopens_inputs_and_cannot_use_warm_receipt_as_authority(tmp_path, monkeypatch, attack):
    """Protocol-only spies; no source database, PDF or visual authentication claim."""
    kw = _fixture()
    result = held.reconcile_unresolved_rows_v1(**kw)
    index = {"corpus_manifest_index_id": "fixture-index:1"}
    paths = {}
    for name, value in (("index", index), ("residual", {"marker": "fresh-residual"})):
        path = tmp_path / (name + ".json")
        path.write_bytes(canonical_json_bytes_v1(value))
        paths[name] = path
    context = {"index_path": paths["index"], "index_ref": runner.generic._file_ref(paths["index"]),
               "residual_spec_path": paths["residual"], "residual_spec_ref": runner.generic._file_ref(paths["residual"]),
               "path": tmp_path / "declared.json", "pin": "a" * 64, "source_pdf_root": tmp_path,
               "expected_reconciliation": copy.deepcopy(result)}
    compiled = runner.compile_gemini_json_flat_family_specs_v1(
        runner.generic._json(runner.TOPOLOGY_SPEC_PATH), runner.generic._json(runner.EVALUATION_SPEC_PATH),
        runner.generic._json(runner.SCHEMA_BINDING_SPEC_PATH))
    seen = []
    monkeypatch.setattr(runner, "validate_current_corpus_manifest_index_v1", lambda value: value)
    monkeypatch.setattr(runner, "query_selected_multitable_hierarchical_family_regions_v1", lambda *args, **kwargs: kw["indexed_query_evidence"])
    monkeypatch.setattr(runner.generic, "_load_selected_pages_by_document", lambda *args, **kwargs: kw["page_json_by_document"])
    monkeypatch.setattr(runner, "build_gemini_json_operating_expense_indexed_query_evidence_v1", lambda **kwargs: kw["indexed_query_evidence"])
    monkeypatch.setattr(runner, "build_gemini_json_operating_expense_trials_v1", lambda **kwargs: kw["trials"])
    monkeypatch.setattr(runner, "build_operating_expense_source_row_coverage_receipt_v1", lambda **kwargs: kw["raw_coverage"])

    def fresh_pdf(**kwargs):
        assert kwargs["spec"] == {"marker": "fresh-residual"}
        seen.append("fresh-pdf-residual")
        return kw["authenticated_pdf_residuals"]

    def fresh_join(**kwargs):
        assert kwargs["pages"] == kw["page_json_by_document"]
        assert kwargs["coverage"] == kw["raw_coverage"]
        assert kwargs["source_page_database"] == tmp_path / "source.sqlite3"
        seen.append("fresh-row-IO-boundary")
        # Independent deterministic test result, never context's expected object.
        return copy.deepcopy(result), {}

    monkeypatch.setattr(runner, "_authenticate_pdf_residuals_v1", fresh_pdf)
    monkeypatch.setattr(runner, "_authenticate_source_repairs_v1", lambda **kwargs: {"test_only": True})
    monkeypatch.setattr(runner, "_authenticate_unresolved_rows_v1", fresh_join)
    if attack == "warm-receipt":
        context["expected_reconciliation"]["held_row_axis"][0]["manual_finding_id"] = "forged"
        material = {k: v for k, v in context["expected_reconciliation"].items() if k != "receipt_id"}
        context["expected_reconciliation"]["receipt_id"] = "gjoeurd1:reconciliation:" + digest(material)
    elif attack == "residual-file":
        paths["residual"].write_text(json.dumps({"marker": "changed-after-warm"}), encoding="utf-8")
    def call():
        return runner.replay_operating_expense_trials_from_source_v1(
            source_page_database=tmp_path / "source.sqlite3", selected_page_json_version_ids=(VERSION_ID,),
            compiled_specs=compiled, indexed_query_evidence=kw["indexed_query_evidence"],
            unresolved_row_disposition_context=context)
    if attack is None:
        assert call() == kw["trials"]
        assert seen == ["fresh-pdf-residual", "fresh-row-IO-boundary"]
    else:
        with pytest.raises(ValueError):
            call()
        if attack == "residual-file":
            assert seen == []


@pytest.mark.parametrize("attack", [None, "wrong-pin", "duplicate-key", "late-byte-drift", "same-byte-replacement"])
def test_real_review_file_reader_requires_pin_and_stable_identity(tmp_path, attack):
    """File protocol only: arbitrary JSON is not a source/visual approval."""
    path = tmp_path / "review.json"
    path.write_bytes(b'{"finding":"fixture"}\n')
    pin = sha256(path.read_bytes()).hexdigest()
    refs = {}
    if attack == "wrong-pin":
        with pytest.raises(ValueError):
            runner._row_json_v1(path, refs, pin="0" * 64)
        return
    if attack == "duplicate-key":
        path.write_bytes(b'{"finding":1,"finding":2}\n')
        with pytest.raises(ValueError):
            runner._row_json_v1(path, refs, pin=sha256(path.read_bytes()).hexdigest())
        return
    assert runner._row_json_v1(path, refs, pin=pin) == {"finding": "fixture"}
    if attack == "late-byte-drift":
        path.write_bytes(b'{"finding":"different"}\n')
    elif attack == "same-byte-replacement":
        replacement = tmp_path / "replacement.json"
        replacement.write_bytes(path.read_bytes())
        replacement.replace(path)
    if attack is None:
        runner._recheck_row_inputs_v1(refs)
    else:
        with pytest.raises(ValueError):
            runner._recheck_row_inputs_v1(refs)
