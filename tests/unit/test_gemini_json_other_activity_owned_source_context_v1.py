"""UNRUN bounded original-source F38 controls; no FULL271/DB/PDF IO claim.

Each pair retains its actual global document/selected-page coordinates. This
is a non-indexed public per-document route over the declared two-page subset,
with the full manifest's selected positions authenticated by the owner excerpt.
"""
from __future__ import annotations

import json
import shutil
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_other_activity_family_v1 import _compiled

from bctc_ai.evaluation import gemini_json_other_activity_family_v1 as family
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/source_structure/f38-role-unit-source-20261028-v1"
METADATA_SHA256 = "9d0762fe595dfa3c76aa7bcca849b6e048769c16ceaf961e2a3fa06f4e8ae633"
CASES = ("abb-doc001", "bvb-doc023", "klb-doc053", "ocb-doc124", "ssb-doc177", "stb-doc193",
    "tcb-doc209", "tpb-doc225", "vab-doc241", "vbb-doc256")


def _source_context(case, fixture_root=FIXTURE):
    raw_meta = (fixture_root / "provenance.json").read_bytes()
    assert sha256(raw_meta).hexdigest() == METADATA_SHA256
    metadata = json.loads(raw_meta)
    assert metadata["historical_family_run_id"] == "gjfafstorev1:run:635e05c76edac90c783adda14fde86997698729bce7f4a91d8b3c4aa3e7dfcdb"
    refs = {item["path"]: item for item in metadata["historical_producer_refs"]}
    assert len(refs) == 15
    assert refs["src/bctc_ai/evaluation/gemini_json_other_activity_family_v1.py"]["sha256"] == "8277c454454f3030b251a9032cff70cf61f8e440155663dbe78134c8d97f2b9d"
    assert refs["src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"]["sha256"] == "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
    document = next(item for item in metadata["documents"] if item["case"] == case)
    excerpt_raw = (fixture_root / case / document["selected_axis_ref"]["file"]).read_bytes()
    assert sha256(excerpt_raw).hexdigest() == document["selected_axis_ref"]["sha256"]
    excerpt = json.loads(excerpt_raw)
    selected_document = excerpt["document"]
    assert excerpt["index"]["sha256"] == metadata["corpus_index_sha256"]
    assert selected_document["source_ordinal"] == document["original_document_ordinal"]
    assert selected_document["source_sha256"] == document["pdf"]["sha256"]
    assert selected_document["source_size_bytes"] == document["pdf"]["size_bytes"]
    assert selected_document["relative_path"] == document["pdf"]["source_logical_name"]
    entries = {item["json_path"]: item for item in excerpt["document_manifest_ref_entries"]}
    records, pages = [], {}
    for page in document["pages"]:
        source_raw = (fixture_root / case / page["file"]).read_bytes()
        assert len(source_raw) == page["size_bytes"] and sha256(source_raw).hexdigest() == page["sha256"]
        selected = page["selected_page_ordinal"]
        assert 1 <= selected <= selected_document["page_count"]
        entry = entries[f"/pages[{selected - 1}]"]
        assert entry["page_json_version_id"] == page["page_json_version_id"]
        assert entry["canonical_json_sha256"] == page["sha256"]
        assert entry["physical_page"] == page["physical_page"]
        parsed = json.loads(source_raw)
        pages[page["page_json_version_id"]] = parsed
        records.append({"document_id": document["original_document_id"],
            "document_ordinal": document["original_document_ordinal"],
            "source_logical_name": document["pdf"]["source_logical_name"], "source_sha256": document["pdf"]["sha256"],
            "page_json_version_id": page["page_json_version_id"], "physical_page": page["physical_page"],
            "selected_page_ordinal": selected, "page_json": parsed})
    assert len(records) == 2 and len(pages) == 2
    for region in document["original_candidate_regions"]:
        record = next(item for item in records if item["page_json_version_id"] == region["page_json_version_id"])
        assert all(record[key] == region[key] for key in family._SOURCE_IDENTITY_FIELDS_V1 if key not in {"section_id", "table_id"})
    return document, records, pages


def _public_actual_candidate(case):
    document, records, pages = _source_context(case)
    before = deepcopy(pages)
    compiled = _compiled()
    base = family.coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    cluster = family.recover_gemini_json_other_activity_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    assert pages == before
    assert {record["document_ordinal"] for record in records} == {document["original_document_ordinal"]}
    if cluster["status"] != family.READY:
        return cluster, None, None
    options = {"regions": cluster["component_regions"], "page_json_by_version": pages, "compiled_specs": compiled,
        "query_receipt": family.build_gemini_json_other_activity_region_query_receipt_v1(cluster["component_regions"], cluster=cluster)}
    candidate = family.evaluate_gemini_json_other_activity_family_cluster_v1(**options)
    assert pages == before
    assert family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options) == candidate
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == len(candidate["mappings"])
    return cluster, candidate, options


@pytest.mark.parametrize("case", CASES)
def test_all_ten_original_source_packets_keep_their_exact_selected_global_identity(case):
    document, records, _pages = _source_context(case)
    assert document["packet_ref"]["sha256"] and document["original_candidate_sha256"]
    assert all(record["document_ordinal"] == document["original_document_ordinal"] for record in records)
    assert [record["selected_page_ordinal"] for record in records] == [page["selected_page_ordinal"] for page in document["pages"]]


@pytest.mark.parametrize("case,role,tokens", [
    ("bvb-doc023", "INCOME_DEBT_RECOVERY", ["605", "1.632"]),
    ("ssb-doc177", "INCOME_DERIVATIVE", ["118.100", "164.141"]),
    ("ssb-doc177", "EXPENSE_DERIVATIVE", ["(139.594)", "(172.560)"]),
    ("tpb-doc225", "INCOME_DEBT_RECOVERY", ["594.474", "669.540"]),
    ("tpb-doc225", "EXPENSE_ASSET_DISPOSAL", ["(639)", "(136)"]),
])
def test_public_original_source_routes_bind_new_nonmixed_roles_to_the_same_printed_cells(case, role, tokens):
    cluster, candidate, _options = _public_actual_candidate(case)
    assert cluster["status"] == family.READY and candidate["status"] == family.READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == role)
    assert [cell["source_text"] for cell in mapping["values"]] == tokens
    assert len(mapping["source_refs"]) == 1
    assert all(fragment["scoped_local_unit_axis"]["complete"] for fragment in candidate["closure_receipt"]["other_activity_source_role_unit_control_receipt"]["fragments"])


def test_abb_original_specific_role_positive_stays_source_owned():
    cluster, candidate, _options = _public_actual_candidate("abb-doc001")
    assert cluster["status"] == family.READY and candidate["status"] == family.READY
    assert {"INCOME_DEBT_RECOVERY", "INCOME_DERIVATIVE", "INCOME_ASSET_DISPOSAL", "EXPENSE_SOCIAL"} <= {item["role"] for item in candidate["mappings"]}


@pytest.mark.parametrize("case", ["klb-doc053", "ocb-doc124", "tcb-doc209", "vab-doc241", "vbb-doc256"])
def test_original_mixed_or_unowned_unit_sources_remain_held_without_amount_splitting(case):
    cluster, candidate, _options = _public_actual_candidate(case)
    if candidate is None:
        assert cluster["status"] == family.UNRESOLVED
    else:
        assert candidate["status"] == family.UNRESOLVED and candidate["mappings"] == []
        control = candidate["closure_receipt"]["other_activity_source_role_unit_control_receipt"]
        assert "F38_SOURCE_TEMPLATE_ROLE_GRANULARITY_NOT_PROVEN" in control["reasons"]
        if case == "vbb-doc256":
            assert "F38_SOURCE_UNIT_NOT_LOCALLY_PROVEN" in control["reasons"]
            row = next(item for item in control["unproven_role_source_rows"] if item["row_ordinal"] == 3)
            assert row["locator"]["section_id"] == "s6" and row["locator"]["table_id"] == "t1"
            assert row["source_row"]["values_exact"] == ["1.704", "494"]


def test_stb_fixed_asset_alias_is_bound_even_while_other_undeclared_fee_rows_remain_held():
    document, records, pages = _source_context("stb-doc193")
    region = next(item for item in document["original_candidate_regions"] if item["physical_page"] == 68)
    section, table = family._source_table(pages[region["page_json_version_id"]], section_id=region["section_id"], table_id=region["table_id"])
    classification = family.classify_gemini_json_multitable_hierarchical_table_v1(records[1]["page_json"], section, table, compiled_specs=_compiled())
    assert any(hit["row_ordinal"] == 6 and hit["role"] == "INCOME_ASSET_DISPOSAL" for hit in classification["role_hits"])
    cluster, candidate, _options = _public_actual_candidate("stb-doc193")
    assert cluster["status"] == family.UNRESOLVED or candidate["status"] == family.UNRESOLVED
    if candidate is not None:
        assert candidate["mappings"] == []


@pytest.mark.parametrize("changed", ["raw_page", "selected_vid", "source_sha", "pdf_name"])
def test_original_context_packet_tamper_cannot_replace_the_pinned_source_identity(tmp_path, changed):
    case = "bvb-doc023"
    shutil.copytree(FIXTURE / case, tmp_path / case)
    shutil.copyfile(FIXTURE / "provenance.json", tmp_path / "provenance.json")
    document, _records, _pages = _source_context(case)
    if changed == "raw_page":
        path = tmp_path / case / document["pages"][1]["file"]
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = tmp_path / case / "selected-axis.json"
        value = json.loads(path.read_bytes())
        if changed == "selected_vid":
            next(item for item in value["document_manifest_ref_entries"] if "page_json_version_id" in item)["page_json_version_id"] = "gfpstorev1:json:" + "f" * 64
        elif changed == "source_sha":
            value["document"]["source_sha256"] = "f" * 64
        else:
            value["document"]["relative_path"] = "vietstock_bctc/OTHER/2025/other.pdf"
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(AssertionError):
        _source_context(case, fixture_root=tmp_path)
