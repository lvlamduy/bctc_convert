"""Original-source current NET observations, public query/evaluation/replay."""
from __future__ import annotations

import copy
import json
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_issued_valuable_papers_source_total_lanes_v1 import _compiled

from bctc_ai.evaluation import gemini_json_issued_valuable_papers_family_v1 as family
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    _stored_candidate_repair_target_replays_v1,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/source_structure/f25-current-four-metric-20261028-v1"
PROVENANCE_SHA256 = "539028ed470b1e0c954ec0b995d5d6923e070640ed3f1301d02c8ac73bd23172"


def _original():
    payload = (FIXTURE / "provenance.json").read_bytes()
    assert sha256(payload).hexdigest() == PROVENANCE_SHA256
    provenance = json.loads(payload)
    manifest_raw = (FIXTURE / "original-document-manifest.json").read_bytes()
    selection_raw = (FIXTURE / "original-document-selection.json").read_bytes()
    assert sha256(manifest_raw).hexdigest() == provenance["original_document_manifest_sha256"]
    assert sha256(selection_raw).hexdigest() == provenance["original_document_selection_sha256"]
    manifest = json.loads(manifest_raw)
    selection = json.loads(selection_raw)
    assert manifest["document"] == provenance["source"]
    assert selection["document_manifest_id"] == manifest["document_manifest_id"]
    assert selection["document_manifest_ref"]["sha256"] == provenance["original_document_manifest_sha256"]
    assert selection["source_sha256"] == provenance["source"]["source_sha256"]
    assert [ref["physical_page"] for ref in provenance["pages"]] == list(range(1, 54))
    assert len(manifest["pages"]) == 53
    pages = []
    for ref, original in zip(provenance["pages"], manifest["pages"], strict=True):
        raw = (FIXTURE / ref["file"]).read_bytes()
        assert len(raw) == ref["size_bytes"]
        assert sha256(raw).hexdigest() == ref["stored_two_lf_sha256"]
        page = json.loads(raw)
        assert all(ref[field] == original[field] for field in ("physical_page", "page_json_version_id", "page_id", "extraction_run_id", "status"))
        assert ref["stored_two_lf_sha256"] == original["canonical_json_sha256"]
        assert canonical_json_bytes_v1(page) + b"\n" == raw
        assert ref["page_json_version_id"] == "gfpstorev1:json:" + canonical_json_sha256_v1({
            "canonical_json_sha256": ref["stored_two_lf_sha256"],
            "extraction_run_id": ref["extraction_run_id"], "page_id": ref["page_id"]})
        pages.append(page)
    return provenance, pages


def _context(pages=None, *, mutation=None, axis_mutation=None, with_indexed=False):
    provenance, original = _original()
    pages = original if pages is None else pages
    source = provenance["source"]
    document = {key: source[key] for key in ("document_id", "source_logical_name", "source_sha256")}
    document["document_ordinal"] = 1
    if mutation is not None:
        document.update(document_id="gfpstorev1:document:" + canonical_json_sha256_v1(["synthetic", mutation]),
            source_sha256=sha256(mutation.encode()).hexdigest(), source_logical_name=f"synthetic/{mutation}.pdf")
    records, payloads = [], []
    for ordinal, (ref, page) in enumerate(zip(provenance["pages"], pages, strict=True), 1):
        payload = {key: document[key] for key in ("document_id", "source_logical_name", "source_sha256")}
        payload.update(physical_page=ref["physical_page"], canonical_json_sha256=sha256(canonical_json_bytes_v1(page) + b"\n").hexdigest(),
            page_id=ref["page_id"] if mutation is None else "gfpstorev1:page:" + canonical_json_sha256_v1([mutation, ordinal, "page"]),
            extraction_run_id=ref["extraction_run_id"] if mutation is None else "gfpstorev1:run:" + canonical_json_sha256_v1([mutation, ordinal, "run"]))
        version = "gfpstorev1:json:" + canonical_json_sha256_v1({key: payload[key]
            for key in ("canonical_json_sha256", "extraction_run_id", "page_id")})
        payload["page_json_version_id"] = version
        payloads.append(payload)
        records.append({**document, "page_json": page, "page_json_version_id": version,
            "physical_page": ref["physical_page"], "selected_page_ordinal": ordinal})
    compiled = _compiled(registered_repairs=True)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    axis = [{key: value for key, value in record.items() if key != "page_json"} for record in records]
    indexed = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document], selected_page_axis=axis, document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]))
    page_map = {record["page_json_version_id"]: record["page_json"] for record in records}
    adapted, _receipts = family.adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
        indexed, page_json_by_document={1: page_map}, compiled_specs=compiled)
    disposition = adapted["candidate_dispositions"][0]
    cluster = disposition["cluster"]
    if disposition["disposition"] != READY:
        return cluster, None
    if axis_mutation is not None:
        axis_mutation(axis, page_map)
    regions = cluster["component_regions"]
    context = {"regions": regions, "page_json_by_version": page_map, "selected_page_axis": axis, "selected_page_provenance": payloads,
        "compiled_specs": compiled, "query_receipt": family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
            regions, selected_page_axis=axis, selected_page_provenance=payloads)}
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    return (candidate, context, adapted) if with_indexed else (candidate, context)


def _receipt(candidate):
    return candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]["original_source_mapping_lane_receipt"]


def _audit_replay(candidate, context):
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert candidate["component_regions"] == context["regions"]
    assert candidate["closure_receipt"]["query_receipt"] == context["query_receipt"]
    assert family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(candidate, **context) == candidate


def test_original_full53_pages_emit_only_observed_summary_and_current_net_tenors():
    provenance, before = _original()
    candidate, context = _context()
    assert context is not None
    assert len(context["selected_page_axis"]) == len(context["page_json_by_version"]) == 53
    assert sum(page["status"] == "PRIMARY_FINANCIAL_STATEMENT" for page in before) == 6
    assert candidate["status"] == READY, candidate["reasons"]
    expected = {"FAMILY_ROOT_TOTAL": (1100, [4100000000000, 2145000000000]),
        "CERTIFICATE_OF_DEPOSIT": (1101, [3100000000000, 1145000000000]),
        "BOND": (1109, [1000000000000, 1000000000000]),
        "CD_SHORT": (1102, [3100000000000]), "BOND_LONG": (1112, [1000000000000])}
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert mappings.keys() == expected.keys()
    for role, (rnid, values) in expected.items():
        mapping = mappings[role]
        assert mapping["report_norm_id"] == rnid
        assert mapping["unit"] == "VND"
        assert [cell["coefficient"] for cell in mapping["values"]] == values
        assert len(mapping["source_refs"]) == 1
        ref = mapping["source_refs"][0]
        assert ref["locator"]["physical_page"] == (38 if len(values) == 1 else 37)
        assert ref["money_column_ordinals"] == ([4] if len(values) == 1 else [1, 2])
    receipt = _receipt(candidate)
    assert receipt["failures"] == []
    proof = receipt["source_lane_inventory"]["tables"][0]
    assert proof["period_rule"] == "AUTHENTICATED_REPORT_CURRENT_DATE_FOUR_METRIC_CONTINUATION"
    assert proof["reporting_period_proof"]["current_date"] == "2025-06-30"
    assert proof["continuation_source"]["sender_original_marker"] == "NONE"
    assert proof["continuation_source"]["both_original_markers_asserted"] is False
    assert proof["blocks"][0]["lane_key"] == ["SEMANTIC_ALIAS", "CURRENT_PERIOD"]
    assert all(item["lane_keys"] == [["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]]
               for item in receipt["source_lane_inventory"]["direct_two_period_observations"])
    assert all(ref["locator"]["physical_page"] != 10 for mapping in candidate["mappings"] for ref in mapping["source_refs"])
    assert list(context["page_json_by_version"].values()) == before
    assert all((FIXTURE / ref["file"]).read_bytes().endswith(b"\n\n") for ref in provenance["pages"])
    _audit_replay(candidate, context)


def test_asymmetric_explicit_metrics_and_reordered_columns_select_printed_net_header():
    _provenance, pages = _original()
    detail = pages[37]["sections"][0]["tables"][0]
    for index in (1, 2):
        detail["rows"][index]["values_exact"] = ["1.200.000.000.000", "200.000.000.000", "-", "1.000.000.000.000"]
    for index in (4, 5):
        detail["rows"][index]["values_exact"] = ["3.300.000.000.000", "200.000.000.000", "-", "3.100.000.000.000"]
    order = [3, 0, 2, 1]
    detail["columns"] = [detail["columns"][index] for index in order]
    for row in detail["rows"]:
        row["values_exact"] = [row["values_exact"][index] for index in order]
    before = copy.deepcopy(pages)
    candidate, context = _context(pages, mutation="asymmetric-reordered-net")
    assert context is not None and candidate["status"] == READY, candidate["reasons"]
    for mapping in candidate["mappings"]:
        if mapping["role"] in {"CD_SHORT", "BOND_LONG"}:
            assert mapping["source_refs"][0]["money_column_ordinals"] == [1]
            assert mapping["values"][0]["coefficient"] in {1000000000000, 3100000000000}
    rows = _receipt(candidate)["source_lane_inventory"]["tables"][0]["source_metric_rows"]
    assert all(row["metric_ordinals"]["CARRYING_VALUE"] == 1 for row in rows)
    assert all(row["metric_cells"]["CARRYING_VALUE"]["coefficient"] != row["metric_cells"]["FACE_VALUE"]["coefficient"] for row in rows)
    assert list(context["page_json_by_version"].values()) == before
    _audit_replay(candidate, context)


def test_primary_amounts_and_unit_are_not_note_financial_or_unit_donors():
    _provenance, pages = _original()
    primary = pages[9]["sections"][0]["tables"][0]
    primary["unit_exact"] = None
    for row in primary["rows"]:
        for ordinal, column in enumerate(primary["columns"]):
            if column["value_kind"] == "MONEY" and row["values_exact"][ordinal] is not None:
                row["values_exact"][ordinal] = "123456789"
    candidate, context = _context(pages, mutation="primary-no-amount-or-unit-donation")
    assert context is not None and candidate["status"] == READY, candidate["reasons"]
    assert all(mapping["unit"] == "VND" for mapping in candidate["mappings"])
    assert all(ref["locator"]["physical_page"] in {37, 38} for mapping in candidate["mappings"] for ref in mapping["source_refs"])
    assert next(mapping for mapping in candidate["mappings"] if mapping["role"] == "BOND_LONG")["values"][0]["coefficient"] == 1000000000000
    _audit_replay(candidate, context)


@pytest.mark.parametrize("mutation", ["missing_net", "duplicate_net", "missing_date", "mismatched_date",
    "missing_primary_date", "conflicting_primary_date", "foreign_primary_scope", "foreign_primary_entity", "missing_notes_declaration",
    "continuation_break", "footnote_break", "blank_net", "blank_discount", "local_unit_break",
    "primary_current_header_break", "duplicate_tenor", "summary_current_date_conflict"])
def test_coherent_counterfactuals_hold_without_date_metric_scope_or_observed_net(mutation):
    _provenance, pages = _original()
    primary = pages[9]["sections"][0]
    detail = pages[37]["sections"][0]["tables"][0]
    summary_section = pages[36]["sections"][2]
    if mutation == "missing_net":
        detail["columns"][3]["header_path_exact"] = ["Giá trị khác"]
    elif mutation == "duplicate_net":
        detail["columns"][0]["header_path_exact"] = ["Giá trị thuần"]
    elif mutation == "missing_date":
        detail["title_exact"] = "(*) Chi tiết:"
    elif mutation == "mismatched_date":
        detail["title_exact"] = "(*) Chi tiết tại ngày 31/12/2024:"
    elif mutation == "missing_primary_date":
        for page in pages:
            for section in page["sections"]:
                if section["content_kind"] == "PRIMARY_STATEMENT" and section["statement_type"] == "BALANCE_SHEET":
                    section["title_exact"] = "Báo cáo tình hình tài chính hợp nhất"
                    for table in section["tables"]:
                        table["title_exact"] = section["title_exact"]
    elif mutation == "conflicting_primary_date":
        other = copy.deepcopy(primary)
        other["title_exact"] = other["tables"][0]["title_exact"] = "Báo cáo tình hình tài chính hợp nhất tại ngày 31/12/2024"
        pages[9]["sections"].append(other)
    elif mutation == "foreign_primary_scope":
        other = copy.deepcopy(primary)
        other["title_exact"] = other["tables"][0]["title_exact"] = "Báo cáo tình hình tài chính riêng tại ngày 30/06/2025"
        pages[9]["sections"].append(other)
    elif mutation == "foreign_primary_entity":
        other = copy.deepcopy(primary)
        other["title_exact"] += " của công ty con"
        other["tables"][0]["title_exact"] = other["title_exact"]
        pages[9]["sections"].append(other)
    elif mutation == "missing_notes_declaration":
        for page in pages:
            for section in page["sections"]:
                if section["content_kind"] == "PRIMARY_STATEMENT":
                    section["narratives_exact"] = []
    elif mutation == "continuation_break":
        detail["continuation"] = "NONE"
    elif mutation == "footnote_break":
        summary_section["tables"][0]["rows"][0]["label_exact"] = "Trái phiếu (**)"
        summary_section["tables"][0]["rows"][0]["hierarchy_path_exact"] = ["Trái phiếu (**)"]
    elif mutation == "blank_net":
        detail["rows"][1]["values_exact"][3] = None
    elif mutation == "blank_discount":
        detail["rows"][1]["values_exact"][1] = None
    elif mutation == "local_unit_break":
        detail["unit_exact"] = None
    elif mutation == "primary_current_header_break":
        for page in pages:
            for section in page["sections"]:
                if section["content_kind"] == "PRIMARY_STATEMENT" and section["statement_type"] == "BALANCE_SHEET":
                    for table in section["tables"]:
                        money = [column for column in table["columns"] if column["value_kind"] == "MONEY"]
                        if money:
                            money[0]["header_path_exact"] = ["Số đầu kỳ"]
    elif mutation == "duplicate_tenor":
        detail["rows"].insert(2, copy.deepcopy(detail["rows"][1]))
    elif mutation == "summary_current_date_conflict":
        summary_section["tables"][0]["columns"][0]["header_path_exact"] = ["Số cuối kỳ 31/12/2024"]
    candidate, context = _context(pages, mutation=mutation)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    if context is not None:
        _audit_replay(candidate, context)


def test_replacing_the_only_note_owner_with_customer_deposits_has_no_f25_anchor_or_permission():
    _provenance, pages = _original()
    section = pages[36]["sections"][2]
    section["title_exact"] = section["tables"][0]["title_exact"] = "4.14 Tiền gửi của khách hàng"
    candidate, context = _context(pages, mutation="owner_break")
    # The immutable source values still exist, but the foreign note owner
    # removes the F25 query anchor. This is not an evaluated financial HOLD.
    assert context is None and candidate["status"] == NOT_OBSERVED
    assert candidate["component_regions"] == [] and candidate["owner_receipt"] is None
    assert candidate.get("mappings", []) == []


@pytest.mark.parametrize("header", [[None], ["Giá trị thuần", None], ["Giá trị thuần", 7]],
                         ids=["null-only", "metric-with-null", "metric-with-number"])
def test_public_new_metric_permission_holds_for_incomplete_or_nonstring_source_header(header):
    _provenance, pages = _original()
    table = pages[37]["sections"][0]["tables"][0]
    table["columns"][3]["header_path_exact"] = copy.deepcopy(header)
    before = copy.deepcopy(pages)
    candidate, context = _context(pages, mutation="unsupported-net-header-" + canonical_json_sha256_v1(header))
    assert context is not None and candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    proof = _receipt(candidate)["source_lane_inventory"]["tables"][0]
    assert proof["period_rule"] == "AUTHENTICATED_REPORT_CURRENT_DATE_FOUR_METRIC_CONTINUATION"
    assert "FOUR_UNIQUE_EXACT_PRINTED_METRIC_HEADERS_NOT_PROVEN" in proof["failures"]
    assert proof["blocks"] == []
    assert list(context["page_json_by_version"].values()) == before
    _audit_replay(candidate, context)


def test_foreign_primary_same_version_cannot_replace_own_selected_membership():
    def foreign(axis, _page_map):
        axis[9]["source_sha256"] = "f" * 64
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="selected document page axis is invalid"):
        _context(axis_mutation=foreign)


def test_foreign_duplicate_does_not_poison_valid_own_primary_membership():
    original, _original_context = _context()
    def foreign_duplicate(axis, _page_map):
        foreign = copy.deepcopy(axis[9])
        foreign["document_id"] = "gfpstorev1:document:" + "f" * 64
        foreign["source_sha256"] = "f" * 64
        axis.append(foreign)
    candidate, context = _context(axis_mutation=foreign_duplicate)
    assert context is not None and candidate == original and candidate["status"] == READY
    _audit_replay(candidate, context)


def test_missing_provenance_or_unresealed_raw_payload_cannot_supply_primary_period():
    _candidate, context = _context()
    assert context is not None
    for mutation in ("missing_provenance", "payload_hash_drift"):
        changed = copy.deepcopy(context)
        if mutation == "missing_provenance":
            changed["selected_page_provenance"] = None
        else:
            primary = changed["page_json_by_version"][changed["selected_page_axis"][9]["page_json_version_id"]]
            primary["sections"][0]["title_exact"] += " tại ngày 31/12/2024"
        changed["query_receipt"] = family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
            changed["regions"], selected_page_axis=changed["selected_page_axis"],
            selected_page_provenance=changed["selected_page_provenance"])
        held = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**changed)
        assert held["status"] == UNRESOLVED and held["mappings"] == []
        _audit_replay(held, changed)


@pytest.mark.parametrize("physical_page,statement_type", [(13, "INCOME_STATEMENT"), (14, "CASH_FLOW")])
@pytest.mark.parametrize("mutation", ["reporting_window_end", "current_column_end", "foreign_entity"])
def test_all_primary_flow_current_end_and_entity_contradictions_veto_balance_sheet_anchor(physical_page, statement_type, mutation):
    _provenance, pages = _original()
    section = pages[physical_page - 1]["sections"][0]
    assert section["content_kind"] == "PRIMARY_STATEMENT" and section["statement_type"] == statement_type
    if mutation == "reporting_window_end":
        section["title_exact"] += "\nCho kỳ kế toán kỳ này kết thúc ngày 31/12/2024"
        section["tables"][0]["title_exact"] = section["title_exact"]
    elif mutation == "current_column_end":
        money = [column for column in section["tables"][0]["columns"] if column["value_kind"] == "MONEY"]
        money[0]["header_path_exact"] = ["Kỳ này kết thúc ngày 31/12/2024"]
    else:
        section["title_exact"] += " của công ty con"
        section["tables"][0]["title_exact"] = section["title_exact"]
    candidate, context = _context(pages, mutation=f"{statement_type}-{mutation}")
    assert context is not None and candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    proof = _receipt(candidate)["source_lane_inventory"]["tables"][0]["reporting_period_proof"]
    assert proof["current_date"] == "2025-06-30"
    assert all(anchor["selected_page"]["physical_page"] in {10, 11} for anchor in proof["anchors"])
    expected = "PRIMARY_ENTITY_QUALIFIER_NOT_BOUND_TO_BALANCE_SHEET_SCOPE" if mutation == "foreign_entity" else "CONFLICTING_PRIMARY_EXPLICIT_CURRENT_END"
    assert expected in proof["failures"]
    witnesses = [observation for observation in proof["all_primary_veto_observations"]
                 if observation["statement_type"] == statement_type and observation["selected_page"]["physical_page"] == physical_page]
    if mutation == "foreign_entity":
        assert any(observation["entity_qualifier"] == "cua cong ty con" for observation in witnesses)
    else:
        conflicting = [observation for observation in witnesses
                       if "2024-12-31" in observation["explicit_current_end_dates"]]
        assert conflicting
        assert all("31/12/2024" in observation["surface_exact"] for observation in conflicting)
    _audit_replay(candidate, context)


@pytest.mark.parametrize("current_header", ["Kỳ này từ ngày 01/01/2025 đến ngày 30/06/2025", "Kỳ này từ ngày 01/01/2025"])
def test_primary_flow_starts_and_explicit_comparative_2024_are_not_current_endpoint_conflicts(current_header):
    original, _original_context = _context()
    _provenance, pages = _original()
    for physical_page in (13, 14, 15):
        section = pages[physical_page - 1]["sections"][0]
        assert section["statement_type"] in {"INCOME_STATEMENT", "CASH_FLOW"}
        for table in section["tables"]:
            money = [column for column in table["columns"] if column["value_kind"] == "MONEY"]
            money[0]["header_path_exact"] = [current_header]
            money[1]["header_path_exact"] = ["Kỳ trước từ ngày 01/01/2024 đến ngày 30/06/2024"]
        section["narratives_exact"].append("Số liệu so sánh kỳ trước cho kỳ kế toán kết thúc ngày 30/06/2024")
    candidate, context = _context(pages, mutation=current_header)
    assert context is not None and candidate["status"] == READY, candidate["reasons"]
    proof = _receipt(candidate)["source_lane_inventory"]["tables"][0]["reporting_period_proof"]
    assert proof["failures"] == [] and proof["current_date"] == "2025-06-30"
    flow_witnesses = [observation for observation in proof["all_primary_veto_observations"]
                      if observation["statement_type"] in {"INCOME_STATEMENT", "CASH_FLOW"}]
    assert flow_witnesses
    assert all(observation["explicit_current_end_dates"] == ["2025-06-30"] for observation in flow_witnesses)
    assert {mapping["role"]: (mapping["unit"], mapping["values"]) for mapping in candidate["mappings"]} == {
        mapping["role"]: (mapping["unit"], mapping["values"]) for mapping in original["mappings"]}
    _audit_replay(candidate, context)


def _reseal(candidate):
    for mapping in candidate["mappings"]:
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1({
            key: value for key, value in mapping.items() if key != "item_mapping_id"})
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    candidate["closure_receipt"]["structural_root_receipt"]["source_mapping_id"] = root["item_mapping_id"]
    adapter = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    receipt = adapter["original_source_mapping_lane_receipt"]
    inventory = receipt["source_lane_inventory"]
    table_ids = {}
    for table in inventory["tables"]:
        previous = table["source_lane_table_proof_id"]
        table["source_lane_table_proof_id"] = "gjivpsltv2:proof:" + canonical_json_sha256_v1({key: value for key, value in table.items() if key != "source_lane_table_proof_id"})
        table_ids[previous] = table["source_lane_table_proof_id"]
    for check in receipt["checks"]:
        for binding in check["source_lane_bindings"]:
            if binding.get("table_proof_id") in table_ids:
                binding["table_proof_id"] = table_ids[binding["table_proof_id"]]
    inventory["source_lane_inventory_id"] = "gjivpsliv2:inventory:" + canonical_json_sha256_v1({key: value for key, value in inventory.items() if key != "source_lane_inventory_id"})
    receipt["source_mapping_lane_receipt_id"] = "gjivpsmlv2:receipt:" + canonical_json_sha256_v1({key: value for key, value in receipt.items() if key != "source_mapping_lane_receipt_id"})
    candidate["closure_receipt"]["structural_root_receipt"]["source_mapping_lane_receipt_id"] = receipt["source_mapping_lane_receipt_id"]
    adapter["adapter_receipt_id"] = "gjivpfav1:receipt:" + canonical_json_sha256_v1({key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in candidate.items() if key != "candidate_id"})


@pytest.mark.parametrize("mutation", ["equal_face_for_net", "period", "primary_anchor", "query_binding", "component_descriptor", "financial_amount"])
def test_public_fresh_replay_rejects_resealed_financial_and_source_proof_tampering(mutation):
    candidate, context = _context()
    assert context is not None and candidate["status"] == READY
    forged = copy.deepcopy(candidate)
    proof = _receipt(forged)["source_lane_inventory"]["tables"][0]
    if mutation == "equal_face_for_net":
        mapping = next(item for item in forged["mappings"] if item["role"] == "BOND_LONG")
        mapping["source_refs"][0]["money_column_ordinals"] = [1]
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1({key: value for key, value in mapping.items() if key != "item_mapping_id"})
        for observation in proof["blocks"][0]["observations"]:
            if observation["role"] == "BOND_LONG":
                observation["source_ref"]["money_column_ordinals"] = [1]
        for check in _receipt(forged)["checks"]:
            if check["role"] == "BOND_LONG":
                check["financial_source_refs"][0]["money_column_ordinals"] = [1]
                check["source_lane_bindings"][0]["source_ref"]["money_column_ordinals"] = [1]
                check["source_lane_bindings"][0]["economic_qualifier"]["metric_role"] = "FACE_VALUE"
                check["source_lane_bindings"][0]["economic_qualifier"]["metric_header_exact"] = ["Mệnh giá"]
    elif mutation == "period":
        proof["blocks"][0]["lane_key"][1] = "COMPARATIVE_PERIOD"
    elif mutation == "primary_anchor":
        proof["reporting_period_proof"]["anchors"][0]["selected_page"]["source_sha256"] = "e" * 64
    elif mutation == "query_binding":
        query = forged["closure_receipt"]["query_receipt"]
        query["selected_document_page_axis_sha256"] = "e" * 64
        query["query_receipt_id"] = "gjivpsqv1:receipt:" + canonical_json_sha256_v1({key: value for key, value in query.items() if key != "query_receipt_id"})
    elif mutation == "component_descriptor":
        query = forged["closure_receipt"]["query_receipt"]
        query["component_regions"][-1]["table_id"] = "t99"
        query["query_receipt_id"] = "gjivpsqv1:receipt:" + canonical_json_sha256_v1({key: value for key, value in query.items() if key != "query_receipt_id"})
    else:
        forged["mappings"][0]["values"][0]["coefficient"] += 1
    _reseal(forged)
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(forged, **context)


def test_no_selected_source_axis_preserves_the_original_held_route():
    _candidate, context = _context()
    assert context is not None
    context.pop("selected_page_axis")
    context["query_receipt"] = family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(context["regions"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    _audit_replay(candidate, context)


def test_actual_stored_repair_consumer_binds_nonroot_detail_to_compact_query_components_and_semantic_pin():
    candidate, context = _context()
    assert context is not None and candidate["status"] == READY
    query = candidate["closure_receipt"]["query_receipt"]
    fields = ("page_json_version_id", "physical_page", "section_id", "table_id", "source_logical_name", "source_sha256")
    assert query["format_version"] == "ISSUED_PAPERS_SELECTED_SOURCE_QUERY_RECEIPT_V1"
    assert query["component_regions"] == [{key: region[key] for key in fields} for region in query["shared_query_receipt"]["region_axis"]]
    assert all(set(region) == set(fields) for region in query["component_regions"])
    detail = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "BOND_LONG")["source_refs"][0]["locator"]
    plan = {"base_page_json_version_id": detail["page_json_version_id"],
        "physical_page": detail["physical_page"], "section_id": detail["section_id"], "table_id": detail["table_id"],
        "source_logical_name": detail["source_logical_name"], "source_sha256": detail["source_sha256"],
        "candidate_semantic_replay_sha256": canonical_json_sha256_v1(candidate)}
    row = tuple(candidate[key] for key in ("page_json_version_id", "physical_page", "section_id", "table_id", "status")) + (
        detail["source_logical_name"], detail["source_sha256"])
    assert row[:4] != (plan["base_page_json_version_id"], plan["physical_page"], plan["section_id"], plan["table_id"])
    options = {"candidate_row": row, "stored_trial": {"status": candidate["status"]}, "stored_candidate": candidate}
    assert _stored_candidate_repair_target_replays_v1(plan=plan, **options)
    for change in ({"table_id": "t99"}, {"base_page_json_version_id": "gfpstorev1:json:" + "f" * 64},
                   {"source_sha256": "f" * 64}, {"candidate_semantic_replay_sha256": "f" * 64}):
        assert not _stored_candidate_repair_target_replays_v1(plan={**plan, **change}, **options)
    unpinned = {key: value for key, value in plan.items() if key != "candidate_semantic_replay_sha256"}
    assert not _stored_candidate_repair_target_replays_v1(plan=unpinned, **options)
    # Even a freshly pinned semantic candidate cannot bind a non-root target
    # when its wrapper omits the legacy locator descriptors the consumer reads.
    unbound = copy.deepcopy(candidate)
    unbound_query = unbound["closure_receipt"]["query_receipt"]
    del unbound_query["component_regions"]
    unbound_query["query_receipt_id"] = "gjivpsqv1:receipt:" + canonical_json_sha256_v1({
        key: value for key, value in unbound_query.items() if key != "query_receipt_id"})
    _reseal(unbound)
    assert not _stored_candidate_repair_target_replays_v1(
        plan={**plan, "candidate_semantic_replay_sha256": canonical_json_sha256_v1(unbound)},
        **{**options, "stored_candidate": unbound})
    _audit_replay(candidate, context)


def test_public_sweep_query_binding_and_observation_contract_keep_five_roles():
    from test_run_gemini_json_issued_valuable_papers_accounting_family_v1 import runner

    candidate, context, indexed = _context(with_indexed=True)
    assert context is not None and candidate["status"] == READY
    trials = runner.generic._trials(indexed=indexed, candidates_by_ordinal={1: candidate})
    specs = [json.loads((ROOT / f"config/families/tm-issued-valuable-papers-{kind}-v1.json").read_bytes())
             for kind in ("topology", "evaluation", "schema-binding")]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=specs[0], evaluation_spec=specs[1], schema_binding_spec=specs[2],
        trials=trials, indexed_query_evidence=indexed)
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    audit = audit_source_observation_mapping_contract_v1(sweep)
    assert audit["status"] == "PASS", audit["violations"]
    # The real sweep contract contains both the selected trial mappings and
    # its candidate mapping list; the audit deliberately walks both copies.
    assert audit["mapping_count"] == 2 * len(candidate["mappings"]) == 10
    _audit_replay(candidate, context)


@pytest.mark.parametrize("mutation", [None, "missing_selected_version", "changed_payload_sha"])
def test_runner_exact_metadata_join_rejects_missing_or_hash_drifted_selected_source(tmp_path, monkeypatch, mutation):
    from test_run_gemini_json_issued_valuable_papers_accounting_family_v1 import runner

    _candidate, context = _context()
    assert context is not None
    rows = context["selected_page_provenance"]
    database = tmp_path / "metadata.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE document(document_id TEXT PRIMARY KEY,source_logical_name TEXT,source_sha256 TEXT)")
        connection.execute("CREATE TABLE page(page_id TEXT PRIMARY KEY,document_id TEXT,physical_page INTEGER)")
        connection.execute("CREATE TABLE page_json_version(page_json_version_id TEXT PRIMARY KEY,page_id TEXT,extraction_run_id TEXT,canonical_json_sha256 TEXT)")
        connection.execute("INSERT INTO document VALUES (?,?,?)", tuple(rows[0][field] for field in ("document_id", "source_logical_name", "source_sha256")))
        for ordinal, row in enumerate(rows):
            connection.execute("INSERT INTO page VALUES (?,?,?)", tuple(row[field] for field in ("page_id", "document_id", "physical_page")))
            if mutation == "missing_selected_version" and ordinal == 0:
                continue
            connection.execute("INSERT INTO page_json_version VALUES (?,?,?,?)", (
                row["page_json_version_id"], row["page_id"], row["extraction_run_id"],
                "e" * 64 if mutation == "changed_payload_sha" and ordinal == 0 else row["canonical_json_sha256"]))
    # The existing extraction/repair-lineage validator remains a separate
    # authority. This focused control supplies its exact shape and exercises
    # the new real SQLite exact-key join and version formula, not a fake query.
    receipts = [{key: row[key] for key in ("page_json_version_id", "source_sha256", "source_logical_name", "physical_page")} for row in rows]
    calls = []
    def existing_validator(path, *, page_json_version_ids):
        calls.append((path, list(page_json_version_ids)))
        return receipts
    monkeypatch.setattr(runner, "selected_page_json_provenance_receipts_v1", existing_validator)
    selected = [row["page_json_version_id"] for row in rows]
    before = database.read_bytes()
    if mutation is None:
        assert runner._selected_payload_provenance_v1(database, selected_ids=selected) == rows
    else:
        with pytest.raises(runner.RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error, match="payload provenance"):
            runner._selected_payload_provenance_v1(database, selected_ids=selected)
    assert calls == [(database, selected)]
    assert database.read_bytes() == before
