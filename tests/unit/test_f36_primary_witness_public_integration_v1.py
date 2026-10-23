"""UNRUN synthetic public/runner protocol tests; no actual243 registration.

The SQLite source and PDF are created only inside a future unit-test tempdir.
No provider, actual source corpus, financial-admission mock or shared patch.
"""
from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
import test_gemini_json_operating_expense_family_v1 as fixture
from PIL import Image
from test_gemini_financial_page_store_v1 import _result

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation import (
    gemini_json_operating_expense_primary_witness_admission_v1 as admission,
)
from bctc_ai.evaluation import gemini_json_operating_expense_primary_witness_v1 as primitive
from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    build_financial_page_json_prompt_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import render_full_pdf_page_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage import gemini_financial_page_store_v1 as page_store
from bctc_ai.storage.gemini_accounting_family_store_v1 import _run_checked_source_replay_adapter_v1
from scripts.experiments import run_gemini_json_operating_expense_accounting_family_v1 as runner


def _seal(spec):
    for item in spec["witnesses"]:
        item["witness_id"] = "gjoepwv1:witness:" + canonical_json_sha256_v1(
            {k: v for k, v in item.items() if k != "witness_id"})
    spec["witness_axis_sha256"] = canonical_json_sha256_v1(spec["witnesses"])
    return spec


def _specs():
    return [fixture._json("tm-operating-expense-" + name + "-v1.json")
            for name in ("topology", "evaluation", "schema-binding", "source-repair")]


def _case(tmp_path, variant="READY", *, name="synthetic.pdf"):
    root = tmp_path / "pdfs"
    root.mkdir()
    pdf_path = root / name
    with fitz.open() as pdf:
        pdf.new_page(width=240, height=80).insert_text((15, 40), "SYNTHETIC NOTE " + name)
        page = pdf.new_page(width=240, height=80)
        for x, token in zip((25, 80, 135, 190), ("83", "66", "83", "66"), strict=True):
            page.insert_text((x, 45), token, fontsize=11)
        pdf.save(pdf_path)
    source = {"source_logical_name": name, "source_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
              "source_size_bytes": pdf_path.stat().st_size}
    note = fixture._operating_page()
    # The anonymous printed TOTAL retains label=None, with its explicit legal path.
    note["sections"][0]["tables"][0]["rows"][-1]["hierarchy_path_exact"] = [None]
    if variant == "NOT_OBSERVED":
        note["status"], note["sections"] = "NO_RELEVANT_FINANCIAL_CONTENT", []
    elif variant == "UNIT_HOLD":
        note["sections"][0]["tables"][0]["unit_exact"] = None
        for i, column in enumerate(note["sections"][0]["tables"][0]["columns"]):
            column["header_path_exact"] = ["Năm " + ("2026" if i == 0 else "2025")]
    elif variant == "PERIOD_HOLD":
        for i, column in enumerate(note["sections"][0]["tables"][0]["columns"]):
            column["header_path_exact"] = ["Unknown printed window " + str(i)]
    primary = {"status": "PRIMARY_FINANCIAL_STATEMENT",
        "completion": deepcopy(note["completion"]), "sections": [{
            "content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT",
            "title_exact": "Báo cáo kết quả hoạt động kinh doanh", "narratives_exact": [],
            "tables": [{"title_exact": "Báo cáo kết quả hoạt động kinh doanh",
                "unit_exact": None if variant == "UNIT_HOLD" else "Triệu đồng", "continuation": "NONE",
                "columns": [{"header_path_exact": [word], "value_kind": "MONEY"}
                            for word in ("Kỳ này", "Kỳ trước", "Lũy kế kỳ này", "Lũy kế kỳ trước")],
                "rows": [fixture._row(fixture.OWNER, "83", None, path=[fixture.OWNER])]}],
        }]}
    primary["sections"][0]["tables"][0]["rows"][0]["values_exact"] = ["83", None, None, None]
    database = tmp_path / "source.sqlite3"
    page_store.initialize_gemini_financial_page_store_v1(database)
    versions, rendered_pages = [], []
    with fitz.open(pdf_path) as pdf:
        for physical, obj in enumerate((note, primary), 1):
            rendered = render_full_pdf_page_v1(pdf[physical - 1], physical_page=physical,
                                               dpi=300, source_sha256=source["source_sha256"])
            with Image.open(BytesIO(rendered.image)) as image:
                width, height = image.size
            stored = page_store.ingest_financial_page_extraction_v1(
                database, document=source,
                page={"physical_page": physical, "image_sha256": sha256(rendered.image).hexdigest(),
                      "image_size_bytes": len(rendered.image), "pixel_width": width, "pixel_height": height,
                      "render_dpi": 300, "media_type": "image/png"},
                prompt_variant="compact", output_contract_mode="JSON_SCHEMA",
                prompt_sha256=sha256(build_financial_page_json_prompt_v1(variant="compact").encode()).hexdigest(),
                response_schema_sha256=canonical_json_sha256_v1(financial_page_json_response_schema_v1()),
                requested_model="gemini-3.7-flash", requested_service_tier="flex", thinking_level="low",
                provider_result=_result(), page_json=obj)
            versions.append(stored["page_json_version_id"])
            rendered_pages.append(rendered)
    # Use the exact stored ORIGINAL object, not assumptions about validator output.
    with sqlite3.connect(database) as connection:
        originals = {vid: json.loads(connection.execute(
            "SELECT canonical_json_bytes FROM page_json_version WHERE page_json_version_id=?", (vid,)).fetchone()[0])
                     for vid in versions}
    specs = _specs()
    legacy_compiled = family.compile_gemini_json_operating_expense_family_specs_v1(*specs)
    base = runner.query_selected_multitable_hierarchical_family_regions_v1(
        database, selected_page_json_version_ids=versions, compiled_specs=legacy_compiled)
    pages = {1: originals}
    target = originals[versions[1]]
    section, table = target["sections"][0], target["sections"][0]["tables"][0]
    row = table["rows"][0]
    hashes = {"original_page_json_sha256": canonical_json_sha256_v1(target),
              "original_section_json_sha256": canonical_json_sha256_v1(section),
              "original_table_json_sha256": canonical_json_sha256_v1(table),
              "original_row_json_sha256": canonical_json_sha256_v1(row)}
    rendered = rendered_pages[1]
    with Image.open(BytesIO(rendered.image)) as image:
        rgb = image.convert("RGB")
        render = {"image_sha256": sha256(rendered.image).hexdigest(), "image_size_bytes": len(rendered.image),
                  "media_type": "image/png", "physical_page": 2, "pixel_height": rgb.height, "pixel_width": rgb.width,
                  "render_dpi": 300, "render_receipt_sha256": canonical_json_sha256_v1(rendered.receipt)}
        records = []
        for column, token, x in zip((2, 3, 4), ("66", "83", "66"), (80, 135, 190), strict=True):
            box = [int((x - 4) * 300 / 72), int(30 * 300 / 72),
                   int((x + 28) * 300 / 72), int(50 * 300 / 72)]
            crop = rgb.crop(tuple(box))
            records.append({
                "witness_kind": primitive.KIND, "source": source,
                "locator": {"page_json_version_id": versions[1], "physical_page": 2, "selected_page_ordinal": 2,
                            "section_id": "s1", "table_id": "t1", "row_ordinal": 1, "column_ordinal": column},
                "original_object_hashes": hashes,
                "expected_context": {"page_status": target["status"], "content_kind": section["content_kind"],
                    "statement_type": section["statement_type"], "row_label_exact": row["label_exact"],
                    "hierarchy_path_exact": row["hierarchy_path_exact"], "row_kind": row["row_kind"],
                    "column_header_path_exact": table["columns"][column - 1]["header_path_exact"],
                    "column_value_kind": "MONEY"},
                "before_exact": None, "after_exact": token, "observed_pdf_glyph": token, "render": render,
                "crop_evidence": {"bbox_pixels_xyxy": box, "pixel_height": crop.height, "pixel_width": crop.width,
                                  "rgb_sha256": sha256(crop.tobytes()).hexdigest()},
            })
    spec = _seal({"family_id": "OPERATING_EXPENSE", "format_version": primitive.FORMAT,
                  "policy": primitive.POLICY, "render_contract": primitive.RENDER_CONTRACT, "witnesses": records})
    path = tmp_path / "witness.json"
    path.write_bytes(canonical_json_bytes_v1(spec))
    compiled = family.compile_gemini_json_operating_expense_family_specs_v1(*specs, spec)
    index = {"documents": [{"relative_path": source["source_logical_name"],
              "source_sha256": source["source_sha256"], "source_size_bytes": source["source_size_bytes"]}]}
    return SimpleNamespace(root=root, pdf=pdf_path, database=database, versions=versions,
        pages=pages, specs=specs, base=base, compiled=compiled, old=legacy_compiled,
        spec=spec, path=path, pin=sha256(path.read_bytes()).hexdigest(), index=index)


def _auth(c):
    return runner._authenticate_primary_witness_admission_v1(
        path=c.path, expected_sha256=c.pin, index=c.index, base=c.base, pages=c.pages,
        compiled=c.compiled, source_pdf_root=c.root)


def _build(c, cap):
    indexed = family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=c.base, page_json_by_document=c.pages,
        compiled_specs=c.compiled, primary_witness_admission=cap)
    trials = family.build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed, page_json_by_document=c.pages,
        compiled_specs=c.compiled, primary_witness_admission=cap)
    return indexed, trials


def _reseal_indexed(indexed, compiled):
    for disposition in indexed["candidate_dispositions"]:
        cluster = disposition["cluster"]
        cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(
            {k: v for k, v in cluster.items() if k != "cluster_id"})
    return family.build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=indexed["selected_document_axis"], selected_page_axis=indexed["selected_page_axis"],
        document_clusters=[d["cluster"] for d in indexed["candidate_dispositions"]],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]))


def test_real_pixels_public_projection_replay_coverage_and_default_none(tmp_path):
    c = _case(tmp_path)
    original = canonical_json_bytes_v1(c.pages[1])
    legacy = family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=c.base, page_json_by_document=c.pages, compiled_specs=c.old)
    expected_old = family._without_witness_build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=c.base, page_json_by_document=c.pages, compiled_specs=c.old)
    assert same_typed_json_v1(legacy, expected_old)
    assert same_typed_json_v1(c.old, family.compile_gemini_json_operating_expense_family_specs_v1(*c.specs, None))
    assert admission.AXIS_FIELD not in legacy["candidate_dispositions"][0]["cluster"]
    cap = _auth(c)
    try:
        indexed, trials = _build(c, cap)
        assert trials[0]["status"] == fixture.READY
        fact = indexed["candidate_dispositions"][0]["cluster"][admission.AXIS_FIELD]
        assert len(fact["projection_receipts"]) == len(fact["pixel_verification_receipts"]) == 3
        assert fact["pdf_pixels_verified"] is True
        assert fact["unit_permission"] is fact["period_permission"] is fact["mapping_permission"] is False
        assert "identity" not in fact["spec_ref"]  # Runtime file metadata is never content-ID material.
        assert indexed["selected_document_axis"] == c.base["selected_document_axis"]
        assert indexed["selected_page_axis"] == c.base["selected_page_axis"]
        assert family.validate_gemini_json_operating_expense_replay_v1(
            indexed_query_evidence=indexed, trials=trials, page_json_by_document=c.pages,
            compiled_specs=c.compiled, primary_witness_admission=cap) == trials
        coverage = family.build_operating_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed, trials=trials, page_json_by_document=c.pages,
            compiled_specs=c.compiled, primary_witness_admission=cap, fail_on_violation=False)
        assert type(coverage["violation_count"]) is int
        assert canonical_json_bytes_v1(c.pages[1]) == original
        assert runner.validate_source_observation_mapping_contract_v1({"trials": trials})["violation_count"] == 0
        count = runner._primary_witness_application_receipt_v1(indexed=indexed, compiled=c.compiled)
        assert len(count["applied_witness_ids"]) == 3 and count["logical_document_application_count"] == 1
    finally:
        cap.close()


@pytest.mark.parametrize("variant,expected", [("UNIT_HOLD", fixture.UNRESOLVED),
                                              ("PERIOD_HOLD", fixture.UNRESOLVED),
                                              ("NOT_OBSERVED", fixture.NOT_OBSERVED)])
def test_all_status_document_application_axis_without_unit_period_grants(tmp_path, variant, expected):
    c = _case(tmp_path, variant)
    cap = _auth(c)
    try:
        indexed, trials = _build(c, cap)
        assert trials[0]["status"] == expected and trials[0]["mappings"] == []
        if expected == fixture.NOT_OBSERVED:
            assert trials[0]["candidates"] == []
        fact = indexed["candidate_dispositions"][0]["cluster"][admission.AXIS_FIELD]
        assert len(fact["projection_receipts"]) == 3
        assert runner._primary_witness_application_receipt_v1(
            indexed=indexed, compiled=c.compiled)["logical_document_application_count"] == 1
    finally:
        cap.close()


def test_nonapplicable_selected_source_retains_explicit_empty_document_axis(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    declared = _case(first)
    c = _case(second, "NOT_OBSERVED", name="other.pdf")
    c.spec, c.path, c.pin, c.compiled = declared.spec, declared.path, declared.pin, declared.compiled
    cap = _auth(c)
    try:
        indexed, trials = _build(c, cap)
        assert trials[0]["status"] == fixture.NOT_OBSERVED and trials[0]["mappings"] == []
        fact = indexed["candidate_dispositions"][0]["cluster"][admission.AXIS_FIELD]
        assert fact["projection_receipts"] == fact["pixel_verification_receipts"] == []
        assert fact["pdf_pixels_verified"] is False
        application = runner._primary_witness_application_receipt_v1(indexed=indexed, compiled=c.compiled)
        assert application["expected_witness_ids"] == application["applied_witness_ids"] == []
        assert application["logical_document_application_count"] == 0
        assert application["document_axis_receipt_ids"] == [fact["receipt_id"]]
    finally:
        cap.close()


@pytest.mark.parametrize("fake", [None, True, {"authenticated": True}, {"receipt_id": "self-resealed"}])
def test_metadata_or_caller_approval_cannot_activate_public_projection(tmp_path, fake):
    c = _case(tmp_path)
    before = canonical_json_bytes_v1(c.pages[1])
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        _build(c, fake)
    assert canonical_json_bytes_v1(c.pages[1]) == before
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        admission.PrimaryWitnessAdmissionV1()


@pytest.mark.parametrize("attack", ["drop", "duplicate", "forge", "pixel", "remove_whole_axis"])
def test_resealed_indexed_witness_axis_rejected_before_public_trial_and_coverage(tmp_path, attack):
    c = _case(tmp_path)
    cap = _auth(c)
    try:
        indexed, trials = _build(c, cap)
        bad = deepcopy(indexed)
        cluster = bad["candidate_dispositions"][0]["cluster"]
        fact = cluster[admission.AXIS_FIELD]
        if attack == "drop":
            fact["projection_receipts"].pop()
        elif attack == "duplicate":
            fact["projection_receipts"].append(deepcopy(fact["projection_receipts"][0]))
        elif attack == "forge":
            fact["projection_receipts"][0]["witness"]["after_exact"] = "999"
        elif attack == "pixel":
            fact["pixel_verification_receipts"][0]["actual_crop"]["rgb_sha256"] = "9" * 64
        else:
            del cluster[admission.AXIS_FIELD]
        if attack != "remove_whole_axis":
            fact["receipt_id"] = "gjoepwa1:document:" + canonical_json_sha256_v1(
                {k: v for k, v in fact.items() if k != "receipt_id"})
        bad = _reseal_indexed(bad, c.compiled)
        with pytest.raises(ValueError):
            family.build_gemini_json_operating_expense_trials_v1(
                indexed_query_evidence=bad, page_json_by_document=c.pages,
                compiled_specs=c.compiled, primary_witness_admission=cap)
        with pytest.raises(ValueError):
            family.build_operating_expense_source_row_coverage_receipt_v1(
                indexed_query_evidence=bad, trials=trials, page_json_by_document=c.pages,
                compiled_specs=c.compiled, primary_witness_admission=cap, fail_on_violation=False)
        with pytest.raises(runner.RunGeminiJsonOperatingExpenseV1Error):
            runner._primary_witness_application_receipt_v1(indexed=bad, compiled=c.compiled)
    finally:
        cap.close()


@pytest.mark.parametrize("attack", ["pdf", "crop", "render", "expected_pin"])
def test_runner_factory_uses_actual_pdf_render_crop_and_external_pin(tmp_path, attack):
    c = _case(tmp_path)
    if attack == "pdf":
        c.pdf.write_bytes(c.pdf.read_bytes() + b"changed")
    elif attack in {"crop", "render"}:
        for record in c.spec["witnesses"]:
            if attack == "crop":
                record["crop_evidence"]["rgb_sha256"] = "9" * 64
            else:
                record["render"]["image_sha256"] = "9" * 64
        _seal(c.spec)
        c.path.write_bytes(canonical_json_bytes_v1(c.spec))
        c.pin = sha256(c.path.read_bytes()).hexdigest()
        c.compiled = family.compile_gemini_json_operating_expense_family_specs_v1(*c.specs, c.spec)
    else:
        c.pin = "9" * 64
    with pytest.raises(ValueError):
        _auth(c)


def test_admission_closed_wrong_original_scope_and_fresh_deterministic_facts(tmp_path):
    c = _case(tmp_path)
    cap1, cap2 = _auth(c), _auth(c)
    try:
        first = _build(c, cap1)
        second = _build(c, cap2)
        assert cap1 is not cap2 and same_typed_json_v1(first, second)
        bad = deepcopy(c.pages)
        bad[1][c.versions[0]]["completion"]["uncertainty_exact"].append("changed")
        with pytest.raises(ValueError):
            family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
                base_indexed_query_evidence=c.base, page_json_by_document=bad,
                compiled_specs=c.compiled, primary_witness_admission=cap1)
    finally:
        cap1.close()
        cap2.close()
    with pytest.raises(ValueError):
        _build(c, cap1)


def test_real_source_store_adapter_reauthenticates_after_warm_admission_closed(tmp_path):
    c = _case(tmp_path)
    cap = _auth(c)
    indexed, trials = _build(c, cap)
    cap.close()
    callback = runner._make_primary_witness_source_replay_adapter_v1(
        path=c.path, expected_sha256=c.pin, index=c.index, source_pdf_root=c.root)
    reference = runner.generic._file_ref(Path(runner.__file__))
    flat = runner.compile_gemini_json_flat_family_specs_v1(*c.specs[:3])
    source_before = sha256(c.database.read_bytes()).hexdigest()
    _run_checked_source_replay_adapter_v1(
        callback, adapter_ref=reference, implementation_refs=[reference],
        source_page_database=c.database, selected_page_json_version_ids=c.versions,
        compiled_specs=flat, indexed_query_evidence=indexed, expected_trials=trials)
    assert sha256(c.database.read_bytes()).hexdigest() == source_before
    # A fresh source-store callback must actually re-read PDF authority.
    c.pdf.write_bytes(c.pdf.read_bytes() + b"changed")
    with pytest.raises(ValueError):
        _run_checked_source_replay_adapter_v1(
            callback, adapter_ref=reference, implementation_refs=[reference],
            source_page_database=c.database, selected_page_json_version_ids=c.versions,
            compiled_specs=flat, indexed_query_evidence=indexed, expected_trials=trials)


def test_late_recheck_cannot_skip_authority_files_by_mutating_capability_data(tmp_path):
    c = _case(tmp_path)
    cap = _auth(c)
    cap._data["authority_refs"].clear()
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        cap.recheck()
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        cap.close()
    with pytest.raises(admission.PrimaryWitnessAdmissionError):
        _build(c, cap)


def test_optional_implementation_closure_adds_exact_modules_and_spec_once(tmp_path):
    c = _case(tmp_path)
    audit = tmp_path / "audit.json"
    audit.write_text("{}\n", encoding="utf-8")
    keywords = {"pdf_residual_audit_spec": audit, "pdf_visible_source_row_audit": audit}
    old = runner._implementation_refs(**keywords)
    active = runner._implementation_refs(**keywords, primary_witness_spec=c.path)
    assert same_typed_json_v1(active[:-3], old)
    assert len(active) == len(old) + 3
    assert [Path(ref["path"]).name for ref in active[-3:]] == [
        "gemini_json_operating_expense_primary_witness_v1.py",
        "gemini_json_operating_expense_primary_witness_admission_v1.py", "witness.json"]
    assert active[-1]["sha256"] == c.pin


@pytest.mark.parametrize("path,pin", [(None, None), (None, "a" * 64),
                                     (Path("/missing.json"), None), (Path("relative.json"), "a" * 64)])
def test_optional_runner_arguments_are_paired_and_default_none_unchanged(path, pin):
    args = SimpleNamespace(primary_witness_spec=path, expected_primary_witness_sha256=pin)
    if path is pin is None:
        assert runner._primary_witness_options_v1(args) == (None, None)
    else:
        with pytest.raises(runner.RunGeminiJsonOperatingExpenseV1Error):
            runner._primary_witness_options_v1(args)
