"""UNRUN exact owner-packet F28 source-context controls; no IO replay claim.

Original global256/selected20..21 locators remain separate from the explicitly
declared two-page public test manifest (run1/selected1..2). No corpus, database,
PDF, provider, loader or financial-validator mock is used by these definitions.
"""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_interest_income_family_v1 import _compiled, _indexed_query_evidence

from bctc_ai.evaluation import gemini_json_interest_income_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/source_structure/f28-vbb-source-fragments-20261027-v1"


def _source_context():
    meta = json.loads((FIXTURE / "provenance.json").read_bytes())
    assert meta["packet_ref"]["sha256"] == "96e545ed21e0ab2f68da2c1e18b56b2fae6dc3155150ce101a7f50cb6296c1b8"
    excerpt_raw = (FIXTURE / meta["selected_axis_excerpt"]["file"]).read_bytes()
    assert sha256(excerpt_raw).hexdigest() == meta["selected_axis_excerpt"]["sha256"]
    excerpt = json.loads(excerpt_raw)
    assert excerpt["index"]["sha256"] == meta["corpus_index_sha256"]
    assert excerpt["document_manifest_ref"]["sha256"] == meta["document_manifest_ref"]["sha256"]
    assert excerpt["document"]["document_manifest_id"] == meta["document_manifest_ref"]["document_manifest_id"]
    assert excerpt["document"]["page_count"] == 26
    assert excerpt["document"]["source_ordinal"] == meta["original_document_ordinal"] == 256
    assert excerpt["document"]["source_sha256"] == meta["pdf"]["sha256"]
    assert excerpt["document"]["source_size_bytes"] == meta["pdf"]["size_bytes"] == 10174390
    assert excerpt["document"]["relative_path"] == meta["pdf"]["source_logical_name"]
    entries = {item["json_path"]: item for item in excerpt["document_manifest_ref_entries"]}
    pages, records = {}, []
    for slot, page in enumerate(meta["pages"]):
        raw = (FIXTURE / page["file"]).read_bytes()
        assert len(raw) == page["size_bytes"] and sha256(raw).hexdigest() == page["sha256"]
        selected = meta["original_sender_selected_page_ordinal"] + slot
        entry = entries[f"/pages[{selected - 1}]"]
        assert entry["page_json_version_id"] == page["page_json_version_id"]
        assert entry["canonical_json_sha256"] == page["sha256"] and entry["physical_page"] == page["physical_page"]
        parsed = json.loads(raw)
        pages[page["page_json_version_id"]] = parsed
        records.append({"document_id": meta["original_document_id"], "document_ordinal": 256,
            "source_logical_name": meta["pdf"]["source_logical_name"], "source_sha256": meta["pdf"]["sha256"],
            "page_json_version_id": page["page_json_version_id"], "physical_page": page["physical_page"],
            "selected_page_ordinal": selected, "page_json": parsed})
    assert {key: records[1][key] for key in meta["stored_candidate_region"] if key not in {"section_id", "table_id"}} == {
        key: value for key, value in meta["stored_candidate_region"].items() if key not in {"section_id", "table_id"}}
    return meta, records, pages


def _region(record, *, section_id, table_id, compiled, fragment):
    section, table = family._region_table({record["page_json_version_id"]: record["page_json"]},
        {"page_json_version_id": record["page_json_version_id"], "section_id": section_id, "table_id": table_id})
    classification = family.classify_gemini_json_multitable_hierarchical_table_v1(
        record["page_json"], section, table, compiled_specs=compiled)
    return {**{key: value for key, value in record.items() if key != "page_json"},
        "section_id": section_id, "table_id": table_id, "fragment_ordinal": fragment,
        "component_roles": family._classification_role_axis(classification)}


def test_actual_original_manifest_selected_edge_is_proved_without_relabelling_global_coordinates():
    meta, records, pages = _source_context()
    compiled = _compiled()
    regions = [_region(record, section_id=page["section_id"], table_id=page["table_id"], compiled=compiled, fragment=slot + 1)
               for slot, (record, page) in enumerate(zip(records, meta["pages"], strict=True))]
    original = deepcopy(pages)
    proof = family._source_owned_paired_continuation_receipt_v1(
        prior_region=regions[0], receiver_region=regions[1], pages=pages, compiled_specs=compiled)
    assert proof is not None and proof["amounts_used_to_select_join"] is False
    assert proof["source_identity"]["document_ordinal"] == 256
    assert proof["prior_locator"]["selected_page_ordinal"] == 20
    assert proof["receiver_locator"]["selected_page_ordinal"] == 21
    assert proof["prior_locator"]["section_id"] == "s8" and proof["receiver_locator"]["section_id"] == "s1"
    assert proof["prior_source_unit_axis"]["canonical_unit"] == "MILLION_VND"
    assert proof["receiver_source_unit_axis"]["complete"] is False
    assert pages == original


def _projected_public_candidate(mutation=None):
    meta, originals, _original_pages = _source_context()
    records = deepcopy(originals)
    for ordinal, record in enumerate(records, 1):
        record["document_ordinal"], record["selected_page_ordinal"] = 1, ordinal
    sender = records[0]["page_json"]["sections"][7]["tables"][0]
    receiver = records[1]["page_json"]["sections"][0]["tables"][0]
    if mutation == "sender_marker":
        sender["continuation"] = "NONE"
    elif mutation == "receiver_marker":
        receiver["continuation"] = "NONE"
    elif mutation == "unit":
        sender["unit_exact"] = None
    elif mutation == "header":
        sender["columns"][0]["header_path_exact"] = ["Cùng kỳ năm trước"]
    elif mutation == "qualified_header":
        receiver["columns"][0]["header_path_exact"].append("Công ty con")
    elif mutation == "owner":
        sender["title_exact"] = "Khoản mục không thuộc họ thu nhập lãi"
    elif mutation == "receiver_qualified_title":
        receiver["title_exact"] = "Thu nhập lãi và các khoản thu nhập tương tự của công ty con"
    elif mutation == "ambiguity":
        records[0]["page_json"]["sections"][7]["tables"].append(deepcopy(sender))
    elif mutation == "amount":
        sender["rows"][0]["values_exact"] = ["1", "2"]
    pages = {record["page_json_version_id"]: record["page_json"] for record in records}
    if mutation == "vid":
        records[0]["page_json_version_id"] = "gfpstorev1:json:" + "1" * 64
    elif mutation == "pdf":
        records[0]["source_logical_name"] = "vietstock_bctc/OTHER/2025/other.pdf"
    elif mutation == "source_sha":
        records[0]["source_sha256"] = "2" * 64
    compiled = _compiled()
    raw = family.coalesce_gemini_json_interest_income_document_v1(page_records=[records[1]], compiled_specs=compiled)
    assert raw["status"] == READY
    full = family.coalesce_gemini_json_interest_income_document_v1(page_records=records, compiled_specs=compiled)
    raw["declared_money_table_inventory"] = full["declared_money_table_inventory"]
    raw["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1({key: value for key, value in raw.items() if key != "cluster_id"})
    indexed = _indexed_query_evidence(cluster=raw, records=records, compiled=compiled)
    before = deepcopy(pages)
    adapted, proofs = family.adapt_gemini_json_interest_income_indexed_query_evidence_v1(
        indexed, page_json_by_document={1: pages}, compiled_specs=compiled)
    cluster = adapted["accepted_clusters"][0]
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(
        regions=cluster["component_regions"], page_json_by_version=pages, compiled_specs=compiled,
        query_receipt=family.build_gemini_json_interest_income_region_query_receipt_v1(cluster["component_regions"]))
    assert pages == before
    assert originals[0]["document_ordinal"] == meta["original_document_ordinal"] == 256
    assert originals[0]["selected_page_ordinal"] == 20 and originals[1]["selected_page_ordinal"] == 21
    return actual, proofs, cluster


def test_public_adapter_on_labelled_projection_binds_actual_printed_total_and_source_sender():
    actual, proofs, cluster = _projected_public_candidate()
    assert len(proofs) == 1 and len(cluster["component_regions"]) == 2
    assert actual["status"] == READY
    root = next(item for item in actual["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [2739236, 2236509]
    assert [cell["source_text"] for cell in root["values"]] == ["2.739.236", "2.236.509"]
    assert len(root["source_refs"]) == 1 and root["source_refs"][0]["row_id"] == "r8"
    assert root["source_refs"][0]["locator"]["page_json_version_id"].endswith("a9c7d560bab43ee4")
    receiver_region = next(region for region in cluster["component_regions"] if region["physical_page"] == 21)
    assert root["source_refs"] == [{"hierarchy_path_exact": ["Tổng"], "label_exact": "Tổng",
        "locator": receiver_region, "money_column_ordinals": [1, 2],
        "row_id": "r8", "row_kind": "TOTAL", "row_ordinal": 8}]
    assert root["values"] == [
        {"coefficient": 2739236, "source_text": "2.739.236", "state": "RAW_SIGNED_INTEGER"},
        {"coefficient": 2236509, "source_text": "2.236.509", "state": "RAW_SIGNED_INTEGER"}]
    assert root["state"] == "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_F28_SOURCE_CONTROL"
    deposit = next(item for item in actual["mappings"] if item["role"] == "DEPOSIT_INTEREST")
    assert [cell["source_text"] for cell in deposit["values"]] == ["461.350", "180.819"]
    proof = actual["closure_receipt"]["interest_income_adapter_receipt"]["source_root_control_receipts"][0]
    assert proof["fragments"][1]["local_unit_axis"]["complete"] is False
    assert proof["fragments"][1]["source_unit_evidence"]["source_kind"] == "EXACT_SOURCE_OWNED_CONTINUATION_UNIT_INHERITANCE"
    assert validate_source_observation_mapping_contract_v1(actual)["mapping_count"] == len(actual["mappings"])


@pytest.mark.parametrize("mutation", ["sender_marker", "receiver_marker", "unit", "header", "qualified_header", "owner", "receiver_qualified_title", "ambiguity", "vid"])
def test_public_original_context_projection_rejects_missing_or_ambiguous_source_authority(mutation):
    actual, proofs, _cluster = _projected_public_candidate(mutation)
    assert proofs == [] and actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert validate_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0


@pytest.mark.parametrize("mutation", ["pdf", "source_sha"])
def test_public_original_context_projection_cannot_cross_source_identity(mutation):
    with pytest.raises(ValueError):
        _projected_public_candidate(mutation)


def test_amount_mismatch_does_not_choose_or_remove_the_source_edge_and_never_backsolves():
    actual, proofs, _cluster = _projected_public_candidate("amount")
    assert len(proofs) == 1  # Structural source proof is independent of arithmetic.
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert "F28_PRINTED_FAMILY_ROOT_DIFFERS_FROM_EMITTED_ROOT" in actual["reasons"]


@pytest.mark.parametrize("surface", ["table", "section", "header"])
def test_public_evaluator_does_not_inherit_ownership_or_unit_across_a_conflicting_receiver_scope(surface):
    meta, records, pages = _source_context()
    compiled = _compiled()
    receiver = records[1]["page_json"]["sections"][0]
    if surface == "table":
        receiver["tables"][0]["title_exact"] = "Thu nhập lãi và các khoản thu nhập tương tự của công ty con"
    elif surface == "section":
        receiver["title_exact"] = "Khoản mục của công ty con"
    else:
        receiver["tables"][0]["columns"][0]["header_path_exact"].append("Công ty con")
    before = deepcopy(pages)
    # Public evaluation at the original global coordinates: a caller's declared
    # two-region receipt cannot replace the source-owned receiver fence.
    regions = [_region(record, section_id=page["section_id"], table_id=page["table_id"], compiled=compiled, fragment=slot + 1)
               for slot, (record, page) in enumerate(zip(records, meta["pages"], strict=True))]
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(
        regions=regions, page_json_by_version=pages, compiled_specs=compiled,
        query_receipt=family.build_gemini_json_interest_income_region_query_receipt_v1(regions))
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert "F28_SOURCE_CONTINUATION_PREDECESSOR_NOT_PROVEN" in actual["reasons"]
    assert "F28_NOTE_UNIT_SOURCE_OWNERSHIP_NOT_PROVEN" in actual["reasons"]
    assert pages == before
