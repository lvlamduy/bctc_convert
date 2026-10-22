"""Synthetic pure evaluator handoff tests; not actual PDF/source acceptance."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from test_gemini_json_income_tax_comparative_flow_policy_v1 import _comparative_flow_records
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _page, _record, _row, _table
from test_gemini_json_income_tax_part_period_catalog_v1 import _variants
from test_gemini_json_income_tax_recognition_frontier_v1 import (
    _public_evaluate,
    _public_query,
    _reseal_public_receipt_ids,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1 as h


@pytest.fixture
def caption_fixture(monkeypatch):
    # This test-only loader is an independently installed test authority, never
    # a caller boolean/hash flag in production. Real loader tamper is separate.
    compiled = _adapter_compiled()
    records = _comparative_flow_records()
    pdf = {"logical_name": records[0]["source_logical_name"], "sha256": records[0]["source_sha256"], "size_bytes": 12345}
    document_id = family.section_caption_core._document_id(pdf)
    for record in records:
        record["document_id"] = document_id
    target = records[2]
    page = target["page_json"]
    section = page["sections"][0]
    after = section["title_exact"]
    before = after.replace("2026", "2023")
    section["title_exact"] = before
    modified = deepcopy(page)
    modified["sections"][0]["title_exact"] = after
    ref = {"path": "synthetic-test-only.json", "sha256": "1" * 64, "size_bytes": 1}
    repair = {
        "repair_id": "synthetic:caption", "repair_kind": "SECTION_TITLE_PDF_VISIBLE_EXACT",
        "locator": {"page_json_version_id": target["page_json_version_id"], "physical_page": target["physical_page"],
                    "selected_page_ordinal": target["selected_page_ordinal"], "section_id": "s1", "json_pointer": "/sections/0/title_exact"},
        "before_exact": before, "after_exact": after,
        "original_page_object_canonical_sha256": h(page), "evaluation_page_object_canonical_sha256": h(modified),
        "original_section_object_canonical_sha256": h(section), "evaluation_section_object_canonical_sha256": h(modified["sections"][0]),
        "review_evidence": {"manual_review_ref": ref, "pixel_candidate_ref": ref},
    }
    envelope = deepcopy(compiled["income_tax_section_caption_auth_envelope"])
    envelope["clone_registry"] = {"format_version": "INCOME_TAX_SECTION_CAPTION_REPAIR_REGISTRY_V1", "family_id": "INCOME_TAX",
                                 "sources": [{"document_id": document_id, "pdf_source": pdf, "repairs": [repair]}]}
    lineage = deepcopy(envelope["source_version_lineages"][0])
    lineage.update(document_id=document_id, pdf_source=deepcopy(pdf),
                   repair_evidence=[{"repair_id": repair["repair_id"], **repair["review_evidence"]}])
    lineage["pdf_object"].update(sha256=pdf["sha256"], size_bytes=pdf["size_bytes"],
                               key="bctc-ai/objects/sha256/" + pdf["sha256"][:2] + "/" + pdf["sha256"])
    envelope["source_version_lineages"] = [lineage]
    # The actual file-loader shape/lineage validation is not bypass evidence:
    # these tests exercise only consumers of its trusted result.
    compiled["income_tax_section_caption_auth_envelope"] = deepcopy(envelope)
    compiled["income_tax_section_caption_auth_envelope_ref"] = deepcopy(ref)
    monkeypatch.setattr(family, "_load_registered_section_caption_auth_envelope_v1", lambda: (deepcopy(envelope), deepcopy(ref)))
    return records, compiled, envelope, modified


def test_caption_preparation_is_original_first_disjoint_and_no_permission(caption_fixture):
    records, compiled, _, modified = caption_fixture
    before = deepcopy(records)
    evaluation, old, proof = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert old == []
    assert evaluation[2]["page_json"] == modified
    assert records == before
    assert proof["ordered_caption_repair_ids"] == ["synthetic:caption"]
    assert proof["ordered_legacy_repair_receipts"] == []
    assert proof["source_database_pdf_or_pixels_authenticated"] is False
    assert all(value is False for value in proof["permission_grants"].values())
    pure = proof["ordered_caption_clone_receipts"][0]
    assert all(value is False for value in pure["capabilities"].values())
    restored = deepcopy(evaluation)
    restored[2]["page_json"]["sections"][0]["title_exact"] = records[2]["page_json"]["sections"][0]["title_exact"]
    assert restored == records
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family._prepare_income_tax_evaluation_records_v1(evaluation, compiled_specs=compiled)


@pytest.mark.parametrize("field", ["income_tax_section_caption_auth_envelope", "income_tax_section_caption_auth_envelope_ref", "income_tax_section_caption_clone_core_ref"])
def test_compiled_self_reseal_cannot_replace_fresh_approved_caption_axis(caption_fixture, field):
    records, compiled, _, _ = caption_fixture
    compiled[field] = {}
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)


def test_public_query_and_eval_rebuild_caption_from_original_records(caption_fixture):
    records, compiled, _, _ = caption_fixture
    before = deepcopy(records)
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    assert query is not None
    projection = cluster["income_tax_section_caption_projection_receipt"]
    assert projection == query["source_context_receipt"]["section_caption_projection_receipt"]
    assert projection["ordered_caption_repair_ids"] == ["synthetic:caption"]
    candidate = _public_evaluate(records, compiled, cluster, query)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == before


@pytest.mark.parametrize("mutation", ["drop", "empty_axis", "evaluation_hash", "pure_occurrence", "envelope_ref", "part_disjointness"])
def test_public_receipt_self_reseal_cannot_launder_caption_replay(caption_fixture, mutation):
    records, compiled, _, _ = caption_fixture
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY
    forged = deepcopy(query)
    context = forged["source_context_receipt"]
    projection = context["section_caption_projection_receipt"]
    if mutation == "drop":
        del context["section_caption_projection_receipt"]
    elif mutation == "empty_axis":
        projection["ordered_caption_repair_ids"] = []
    elif mutation == "evaluation_hash":
        projection["evaluation_records_object_canonical_sha256"] = "2" * 64
    elif mutation == "pure_occurrence":
        projection["ordered_caption_clone_receipts"][0]["occurrences"] = []
    elif mutation == "envelope_ref":
        projection["envelope_ref"]["sha256"] = "2" * 64
    else:
        projection["part_period_disjointness_receipt"]["selected_registry_ref"] = {"caller": "forged"}
    _reseal_public_receipt_ids(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _public_evaluate(records, compiled, cluster, forged)


def test_untargeted_source_still_binds_exact_empty_approval_axis():
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    before = deepcopy(records)
    evaluation, old, proof = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert evaluation == records == before and old == []
    assert proof["status"] == "NOT_APPLICABLE_EXACT_EMPTY_CAPTION_AXIS"
    assert proof["ordered_caption_clone_receipts"] == proof["ordered_caption_repair_ids"] == []
    assert proof["envelope_ref"] == compiled["income_tax_section_caption_auth_envelope_ref"]


@pytest.mark.parametrize("field", ["income_tax_section_caption_auth_envelope", "income_tax_section_caption_auth_envelope_ref", "income_tax_section_caption_clone_core_ref"])
def test_untargeted_empty_axis_cannot_skip_fresh_approval_comparison(field):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    compiled[field] = {}
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)


@pytest.mark.parametrize("mutation", ["source_sha", "logical_name", "foreign_VID", "duplicate_selected", "duplicate_physical", "reordered", "cell", "header", "raw_kind", "substituted_legacy"])
def test_source_identity_or_noncaption_mutation_is_not_a_repair_permission(caption_fixture, mutation):
    records, compiled, _, _ = caption_fixture
    before = deepcopy(records)
    if mutation in {"source_sha", "logical_name"}:
        key, value = ("source_sha256", "7" * 64) if mutation == "source_sha" else ("source_logical_name", "foreign.pdf")
        for record in records:
            record[key] = value
    elif mutation == "foreign_VID":
        for record in records:
            record["document_id"] = "gfpstorev1:document:" + "7" * 64
            record["source_logical_name"] = "foreign.pdf"
    elif mutation == "duplicate_selected":
        records[-1]["selected_page_ordinal"] = records[-2]["selected_page_ordinal"]
    elif mutation == "duplicate_physical":
        records[-1]["physical_page"] = records[-2]["physical_page"]
    elif mutation == "reordered":
        records.reverse()
    elif mutation == "substituted_legacy":
        compiled["income_tax_source_repairs"] = []
    else:
        table = records[2]["page_json"]["sections"][0]["tables"][0]
        if mutation == "cell":
            table["rows"][0]["values_exact"][0] = "99"
        elif mutation == "header":
            table["columns"][0]["header_path_exact"] = ["Unprinted year"]
        else:
            table["columns"][0]["value_kind"] = "UNKNOWN"
    changed = deepcopy(records)
    if mutation == "reordered":
        expected, expected_legacy, expected_proof = family._prepare_income_tax_evaluation_records_v1(
            before, compiled_specs=compiled)
        evaluation, legacy, proof = family._prepare_income_tax_evaluation_records_v1(
            records, compiled_specs=compiled)
        assert evaluation == list(reversed(expected))
        assert legacy == expected_legacy == []
        assert proof == expected_proof
    else:
        with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
            family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert records == changed
    assert before != records or mutation == "substituted_legacy"


def test_source_context_requires_original_axis_for_already_projected_active_caption(caption_fixture):
    records, compiled, _, _ = caption_fixture
    evaluation, old, proof = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family._source_context_receipt(compiled_specs=compiled, repair_receipts=old, root_controls=[], page_records=evaluation)
    context = family._source_context_receipt(compiled_specs=compiled, repair_receipts=old, root_controls=[],
                                             page_records=evaluation, original_page_records=records)
    assert context["section_caption_projection_receipt"] == proof


def test_public_query_builder_does_not_omit_cluster_caption_binding(caption_fixture):
    records, compiled, _, _ = caption_fixture
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY and query is not None
    forged = deepcopy(cluster)
    del forged["income_tax_section_caption_projection_receipt"]
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family.build_gemini_json_income_tax_region_query_receipt_v1(forged["component_regions"], cluster=forged)


@pytest.mark.parametrize("name", ["_load_registered_section_caption_auth_envelope_v1", "_prepare_income_tax_evaluation_records_v1", "_section_caption_core_ref_v1", "_section_caption_part_span_disjointness_v1"])
def test_caption_callable_drift_after_last_inventory_cannot_leave_operation(caption_fixture, monkeypatch, name):
    records, compiled, _, _ = caption_fixture
    original = getattr(family, name)
    accepted = []
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1():
            result = family._document_statement_period_inventory(records, compiled_specs=compiled)
            monkeypatch.setattr(family, name, lambda *args, **kwargs: original(*args, **kwargs))
        accepted.append(result)
    assert accepted == []


@pytest.mark.parametrize("failure", ["absent", "byte_drift", "wrong_literal_pin"])
def test_actual_default_loader_requires_real_file_and_independent_literal_pin(monkeypatch, failure):
    # No source/config file is written. Exercise the REAL default loader with
    # controlled read failures, not a trusted-loader replacement.
    approved, reference = family._load_registered_section_caption_auth_envelope_v1()
    assert approved["family_id"] == "INCOME_TAX"
    assert reference["sha256"] == "dc80fc86b1e718117e5a6ea80bf9a45d5c7a04a6cf084db89daa8621f4a14c74"
    path = Path(family.__file__).resolve().parents[3] / family.DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH
    original_read = Path.read_bytes
    if failure == "wrong_literal_pin":
        monkeypatch.setattr(family, "_SECTION_CAPTION_AUTH_ENVELOPE_SHA256", "0" * 64)
    else:
        def read(candidate):
            if candidate == path:
                if failure == "absent":
                    raise FileNotFoundError("synthetic denied read; file unchanged")
                return original_read(candidate) + b" "
            return original_read(candidate)
        monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family._load_registered_section_caption_auth_envelope_v1()


@pytest.mark.parametrize("relative", [
    "config/families/tm-income-tax-section-caption-repair-auth-v2.json",
    "src/bctc_ai/evaluation/gemini_json_income_tax_section_caption_repair_v1.py",
    "config/families/tm-income-tax-source-repair-v1.json",
    "config/families/tm-income-tax-part-period-contexts-v1.json",
    "config/families/tm-income-tax-part-period-contexts-common204-v1.json",
])
def test_actual_dependency_read_drift_after_last_getter_blocks_owning_exit(monkeypatch, relative):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    target = Path(family.__file__).resolve().parents[3] / relative
    original_read = Path.read_bytes
    state = {"drift": False}
    def read(path):
        raw = original_read(path)
        return raw + b" " if path == target and state["drift"] else raw
    monkeypatch.setattr(Path, "read_bytes", read)
    accepted = []
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1():
            result = family._document_statement_period_inventory(records, compiled_specs=compiled)
            state["drift"] = True
        accepted.append(result)
    assert accepted == []


def test_caption_warm_and_cache_disabled_public_outputs_are_exact(caption_fixture):
    records, compiled, _, _ = caption_fixture
    before = deepcopy((records, compiled))
    with family.income_tax_document_period_evaluation_scope_v1() as warm:
        cluster, query = _public_query(records, compiled)
        first = _public_evaluate(records, compiled, cluster, query)
        second = _public_evaluate(records, compiled, cluster, query)
        assert warm["hits"] > 0 and warm["builds"] < warm["requests"]
    with family.income_tax_document_period_evaluation_scope_v1(enabled=False) as cold:
        cold_cluster, cold_query = _public_query(records, compiled)
        actual = _public_evaluate(records, compiled, cold_cluster, cold_query)
        assert cold["requests"] == cold["disabled_requests"] == cold["builds"] > 0
        assert cold["hits"] == cold["peak_entries"] == cold["peak_stored_bytes"] == 0
        assert cold["dependency_checks"] == 0 and cold["dependency_check_seconds"] == 0.0
    assert warm["dependency_checks"] == 2
    assert first["status"] == READY
    assert (cluster, query, first) == (cold_cluster, cold_query, actual)
    assert first == second and (records, compiled) == before


def _nonready_indexed_protocol_case(disposition):
    # Honest empty source. N/U here are explicitly protocol dispositions, not a
    # PDF absence/terminal claim; both carry the same complete ORIGINAL axis.
    page = {"status": "NO_RELEVANT_FINANCIAL_CONTENT", "sections": [],
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}
    records, compiled = [_record(page)], _adapter_compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    assert base["status"] == NOT_OBSERVED
    _, _, projection = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    cluster = family._reseal_cluster(base, status=disposition, component_regions=[],
        reasons=[] if disposition == NOT_OBSERVED else ["SYNTHETIC_PROTOCOL_HOLD_NOT_PDF_DISPOSITION"],
        income_tax_section_caption_projection_receipt=projection)
    return records, compiled, cluster


def _index_protocol(records, compiled, cluster):
    document = {key: records[0][key] for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")}
    pages = [{key: value for key, value in record.items() if key != "page_json"} for record in records]
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document], selected_page_axis=pages, document_clusters=[cluster],
        query_policy_sha256=h(compiled["query_policy"]))


@pytest.mark.parametrize("disposition", [NOT_OBSERVED, UNRESOLVED])
@pytest.mark.parametrize("mutation", ["missing", "stale_envelope", "empty_forged_stage", "forged_raw_axis"])
def test_nonready_indexed_query_cannot_omit_or_self_reseal_caption_axis(disposition, mutation):
    records, compiled, cluster = _nonready_indexed_protocol_case(disposition)
    original = deepcopy(records)
    # Positive protocol control, NOT semantic acceptance.
    good = _index_protocol(records, compiled, cluster)
    trials = family.build_gemini_json_income_tax_trials_v1(indexed_query_evidence=good,
        page_json_by_document={1: {record["page_json_version_id"]: record["page_json"] for record in records}},
        compiled_specs=compiled)
    assert trials[0]["status"] == disposition and trials[0]["mappings"] == []
    changed = deepcopy(cluster)
    if mutation == "missing":
        del changed["income_tax_section_caption_projection_receipt"]
    else:
        proof = changed["income_tax_section_caption_projection_receipt"]
        if mutation == "stale_envelope":
            proof["envelope_ref"]["sha256"] = "8" * 64
        elif mutation == "empty_forged_stage":
            proof["evaluation_records_object_canonical_sha256"] = "8" * 64
        else:
            proof["source_page_axis"][0]["source_logical_name"] = "foreign.pdf"
        _reseal_public_receipt_ids(changed)
    changed = family._reseal_cluster(changed)
    indexed = _index_protocol(records, compiled, changed)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="indexed caption axis"):
        family.build_gemini_json_income_tax_trials_v1(indexed_query_evidence=indexed,
            page_json_by_document={1: {record["page_json_version_id"]: record["page_json"] for record in records}},
            compiled_specs=compiled)
    assert records == original


def _composition_case(caption_fixture, *, same_page):
    _, compiled, envelope, _ = caption_fixture
    repairs = compiled["income_tax_source_repairs"]
    # Generic synthetic reconstruction of one real declared legacy before-image;
    # no actual PDF/DB authority and no issuer/page routing in production.
    old = next(repair for repair in repairs if sum(peer["pdf_source"] == repair["pdf_source"] for peer in repairs) == 1)
    pdf, locator = deepcopy(old["pdf_source"]), old["locator"]
    section_index, table_index, row_index = int(locator["section_id"][1:]) - 1, int(locator["table_id"][1:]) - 1, locator["row_ordinal"] - 1
    width = len(old["before_exact"]["values_exact"]) if old["repair_kind"] == "ROW_PDF_VISIBLE_EXACT" else old["column_ordinal"]
    table = _table([])
    table["columns"] = [{"header_path_exact": [f"Raw column {index}"], "value_kind": "MONEY"} for index in range(width)]
    table["rows"] = [{**_row("Raw retained operand", None, None), "values_exact": [None] * width} for _ in range(row_index + 1)]
    if old["repair_kind"] == "ROW_PDF_VISIBLE_EXACT":
        table["rows"][row_index] = deepcopy(old["before_exact"])
    else:
        table["rows"][row_index]["values_exact"][old["column_ordinal"] - 1] = old["before_exact"]
    page = _page([], tables=[])
    section_template = deepcopy(page["sections"][0])
    page["sections"] = [deepcopy(section_template) for _ in range(section_index + 1)]
    page["sections"][section_index]["tables"] = [deepcopy(_table([])) for _ in range(table_index + 1)]
    page["sections"][section_index]["tables"][table_index] = table
    document_id = family.section_caption_core._document_id(pdf)
    first = {**_record(page), "document_id": document_id, "source_logical_name": pdf["logical_name"],
             "source_sha256": pdf["sha256"], "page_json_version_id": locator["page_json_version_id"],
             "physical_page": locator["physical_page"]}
    if same_page:
        records, target, sid = [first], first, locator["section_id"]
    else:
        second = deepcopy(first)
        second.update(page_json=_page([], tables=[]), page_json_version_id="gfpstorev1:json:" + "f" * 64,
                      physical_page=first["physical_page"] + 1, selected_page_ordinal=2)
        records, target, sid = [first, second], second, "s1"
    si = int(sid[1:]) - 1
    target["page_json"]["sections"][si]["title_exact"] = "Original whole declared caption"
    after_page = deepcopy(target["page_json"])
    after_page["sections"][si]["title_exact"] = "Corrected whole declared caption"
    repair = deepcopy(envelope["clone_registry"]["sources"][0]["repairs"][0])
    repair.update(before_exact="Original whole declared caption", after_exact="Corrected whole declared caption",
        locator={"page_json_version_id": target["page_json_version_id"], "physical_page": target["physical_page"],
                 "selected_page_ordinal": target["selected_page_ordinal"], "section_id": sid, "json_pointer": f"/sections/{si}/title_exact"},
        original_page_object_canonical_sha256=h(target["page_json"]), evaluation_page_object_canonical_sha256=h(after_page),
        original_section_object_canonical_sha256=h(target["page_json"]["sections"][si]),
        evaluation_section_object_canonical_sha256=h(after_page["sections"][si]))
    envelope["clone_registry"]["sources"] = [{"document_id": document_id, "pdf_source": pdf, "repairs": [repair]}]
    envelope["source_version_lineages"][0].update(document_id=document_id, pdf_source=deepcopy(pdf),
        repair_evidence=[{"repair_id": repair["repair_id"], **repair["review_evidence"]}])
    envelope["source_version_lineages"][0]["pdf_object"].update(sha256=pdf["sha256"], size_bytes=pdf["size_bytes"],
        key="bctc-ai/objects/sha256/" + pdf["sha256"][:2] + "/" + pdf["sha256"])
    compiled["income_tax_section_caption_auth_envelope"] = deepcopy(envelope)
    return records, compiled, old


def test_disjoint_caption_then_legacy_preserves_three_explicit_hash_domains(caption_fixture):
    records, compiled, old = _composition_case(caption_fixture, same_page=False)
    before = deepcopy(records)
    evaluation, legacy, projection = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert records == before
    assert [item["repair"]["repair_id"] for item in legacy] == [old["repair_id"]]
    original, caption, final = (projection[key] for key in ("original_records_object_canonical_sha256",
        "caption_stage_records_object_canonical_sha256", "evaluation_records_object_canonical_sha256"))
    assert len({original, caption, final}) == 3
    assert projection["ordered_legacy_repair_receipts"] == legacy
    assert projection["ordered_caption_clone_receipts"][0]["original_records_object_canonical_sha256"] == original
    assert projection["ordered_caption_clone_receipts"][0]["evaluation_records_object_canonical_sha256"] == caption
    assert evaluation[1]["page_json"]["sections"][0]["title_exact"] == "Corrected whole declared caption"
    assert h(evaluation) == final


def test_same_page_caption_and_legacy_requires_separate_composition_approval(caption_fixture):
    records, compiled, _ = _composition_case(caption_fixture, same_page=True)
    before = deepcopy(records)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="caption original-source clone replay drifted"):
        family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert records == before


def test_private_original_basis_is_not_an_outer_caption_query_permission(caption_fixture):
    records, compiled, _, _ = caption_fixture
    original = deepcopy(records)
    locator = family._record_locator(records[0], section_id="s1", table_id="t1")
    receipt = family.build_gemini_json_income_tax_original_basis_receipt_v1(
        page_records=records, locator=locator, basis="RATE", compiled_specs=compiled)
    assert receipt["production_adapter_integrated"] is False and receipt["family_terminal_claimed"] is False
    assert receipt["selected_original_page_axis"][2]["original_page_json_sha256"] == h(records[2]["page_json"])
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY and query is not None
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _public_evaluate(records, compiled, cluster, receipt)
    assert records == original


@pytest.mark.parametrize("name", ["validate_section_caption_registry_v1", "apply_registered_section_caption_repairs_v1", "replay_registered_section_caption_repairs_v1"])
def test_core_callable_drift_after_last_inventory_cannot_leave_operation(caption_fixture, monkeypatch, name):
    records, compiled, _, _ = caption_fixture
    original = getattr(family.section_caption_core, name)
    accepted = []
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1():
            result = family._document_statement_period_inventory(records, compiled_specs=compiled)
            monkeypatch.setattr(family.section_caption_core, name, lambda *args, **kwargs: original(*args, **kwargs))
        accepted.append(result)
    assert accepted == []


@pytest.mark.parametrize("variant", [0, 1])
def test_caption_projection_selects_fresh_original_part_variant_without_merging(monkeypatch, variant):
    first, other, registries, compiled, _, _ = _variants(monkeypatch)
    records = deepcopy((first, other)[variant])
    before = deepcopy(records)
    evaluation, legacy, projection = family._prepare_income_tax_evaluation_records_v1(
        records, compiled_specs=compiled)
    assert evaluation == records == before and legacy == []
    disjoint = projection["part_period_disjointness_receipt"]
    expected = compiled["income_tax_part_period_registry_catalog"][variant]["registry_ref"]
    assert disjoint["selected_registry_ref"] == expected
    assert disjoint["selected_context_ids"] == [registries[variant]["contexts"][0]["context_id"]]
    assert len(disjoint["approved_catalog_refs"]) == 2
    assert disjoint["scope_entity_unit_period_value_or_acceptance_permission"] is False
    assert disjoint["pdf_pixels_or_source_database_authenticated"] is False


@pytest.mark.parametrize("variant", [0, 1])
@pytest.mark.parametrize("overlap", [False, True])
def test_caption_targets_require_disjoint_selected_part_span_on_same_original_pdf(
    caption_fixture, monkeypatch, variant, overlap,
):
    _, _, envelope, _ = caption_fixture
    first, other, registries, _, _, _ = _variants(monkeypatch)
    records = deepcopy((first, other)[variant])
    pdf = deepcopy(registries[variant]["contexts"][0]["pdf_source"])
    document_id = family.section_caption_core._document_id(pdf)
    # Synthetic registries are rebuilt against these exact original records.
    # This is test loader data, not approval inferred from a caller self-hash.
    for record in records:
        record["document_id"] = document_id
    for registry in registries:
        registry["contexts"][0]["document_id"] = document_id
    target = records[0] if overlap else records[-1]
    assert target["physical_page"] in ({1} if overlap else {3})
    section = target["page_json"]["sections"][0]
    after_page = deepcopy(target["page_json"])
    after_page["sections"][0]["title_exact"] = section["title_exact"] + " Corrected"
    repair = deepcopy(envelope["clone_registry"]["sources"][0]["repairs"][0])
    repair.update(
        locator={"page_json_version_id": target["page_json_version_id"],
                 "physical_page": target["physical_page"], "selected_page_ordinal": target["selected_page_ordinal"],
                 "section_id": "s1", "json_pointer": "/sections/0/title_exact"},
        before_exact=section["title_exact"], after_exact=after_page["sections"][0]["title_exact"],
        original_page_object_canonical_sha256=h(target["page_json"]),
        evaluation_page_object_canonical_sha256=h(after_page),
        original_section_object_canonical_sha256=h(section),
        evaluation_section_object_canonical_sha256=h(after_page["sections"][0]),
    )
    envelope["clone_registry"]["sources"] = [{
        "document_id": document_id, "pdf_source": pdf, "repairs": [repair],
    }]
    compiled = _adapter_compiled()
    before = deepcopy(records)
    if overlap:
        with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="caption target intersects registered part-period span"):
            family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    else:
        evaluation, legacy, projection = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
        assert legacy == []
        assert evaluation[-1]["page_json"] == after_page
        assert evaluation[:-1] == records[:-1]
        assert projection["ordered_caption_repair_ids"] == ["synthetic:caption"]
        disjoint = projection["part_period_disjointness_receipt"]
        assert disjoint["selected_registry_ref"] == compiled["income_tax_part_period_registry_catalog"][variant]["registry_ref"]
        assert disjoint["scope_entity_unit_period_value_or_acceptance_permission"] is False
    assert records == before


@pytest.mark.parametrize("field", [
    "income_tax_part_period_registry_catalog", "income_tax_part_period_registry",
    "income_tax_part_period_registry_ref",
])
def test_caption_projection_cannot_reseal_stale_part_catalog_axes(caption_fixture, field):
    records, compiled, _, _ = caption_fixture
    compiled[field] = [] if field.endswith("catalog") else {}
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="compiled part-period authority drifted"):
        family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)


@pytest.mark.parametrize("disposition", [NOT_OBSERVED, UNRESOLVED])
def test_nonready_protocol_preserves_original_record_order_and_exact_empty_axis(disposition):
    records, compiled, cluster = _nonready_indexed_protocol_case(disposition)
    second = deepcopy(records[0])
    second.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                  physical_page=2, selected_page_ordinal=2)
    records = [second, records[0]]
    before = deepcopy(records)
    evaluation, legacy, projection = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert evaluation == records == before and legacy == []
    assert [record["physical_page"] for record in evaluation] == [2, 1]
    assert [record["physical_page"] for record in projection["source_page_axis"]] == [1, 2]
    canonical_projection = family._prepare_income_tax_evaluation_records_v1(
        list(reversed(records)), compiled_specs=compiled)[2]
    assert projection == canonical_projection
    recovered = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=cluster, compiled_specs=compiled)
    assert recovered["income_tax_section_caption_projection_receipt"] == projection
    assert records == before




def test_disjoint_legacy_and_caption_reverse_input_preserves_raw_and_old13_order(caption_fixture):
    records, compiled, _ = _composition_case(caption_fixture, same_page=False)
    expected, expected_legacy, expected_proof = family._prepare_income_tax_evaluation_records_v1(
        records, compiled_specs=compiled)
    records.reverse()
    before = deepcopy(records)
    evaluation, legacy, projection = family._prepare_income_tax_evaluation_records_v1(records, compiled_specs=compiled)
    assert records == before
    assert evaluation == list(reversed(expected))
    assert legacy == expected_legacy
    assert projection == expected_proof
    # Canonical projection hashes must never be presented as hashes of the
    # differently ordered caller record list.
    assert h(records) != projection["original_records_object_canonical_sha256"]
