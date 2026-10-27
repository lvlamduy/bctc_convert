from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_issued_valuable_papers_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/source_structure/f25-source-owned-lanes-20261028-v2"
MANIFEST_SHA256 = "da324871a606bd70418f0fcaa1f806be6703c07ccdf28b40641969741815b7e6"


def _compiled():
    values = [json.loads((ROOT / f"config/families/tm-issued-valuable-papers-{kind}-v1.json").read_bytes())
              for kind in ("topology", "evaluation", "schema-binding")]
    return family.compile_gemini_json_issued_valuable_papers_family_specs_v1(
        *values, json.loads((ROOT / "data/registered/gemini_json_issued_valuable_papers_source_repairs_v1.json").read_bytes())
    )


def _decode(evidence):
    payload = evidence["canonical_json"].encode("utf-8")
    assert len(payload) == evidence["size_bytes"]
    assert sha256(payload).hexdigest() == evidence["sha256"]
    value = json.loads(payload)
    assert canonical_json_bytes_v1(value) == payload
    return value


def _fixture(name):
    raw = (FIXTURES / "manifest.json").read_bytes()
    assert sha256(raw).hexdigest() == MANIFEST_SHA256
    entry = next(item for item in json.loads(raw)["cases"] if item["name"] == name)
    loaded = {}
    for ref in entry["json_refs"]:
        payload = (FIXTURES / name / ref["file"]).read_bytes()
        assert sha256(payload).hexdigest() == ref["sha256"]
        assert len(payload) == ref["size_bytes"]
        loaded[ref["file"]] = json.loads(payload)
    publication = loaded["packet.json"]
    capture = loaded["new-6d4-trial.json"]
    assert capture["producer"] == "6d4a0d7babb3c90985b038d2830423d425ed0743"
    assert publication["pdf"] == entry["source"]
    old = capture["trial"]["candidates"][0]
    regions = copy.deepcopy(old["component_regions"])
    versions = {region["page_json_version_id"] for region in regions}
    assert len(versions) == 1
    version = next(iter(versions))
    pages = {version: next(value for filename, value in loaded.items() if filename.startswith("page-"))}
    assert all(region["source_sha256"] == publication["pdf"]["sha256"] for region in regions)
    assert {region["document_ordinal"] for region in regions} == {publication["index_document"]["source_ordinal"]}
    context = {"regions": regions, "page_json_by_version": pages, "compiled_specs": _compiled(),
        "query_receipt": build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)}
    expected = _decode(old["closure_receipt"]["issued_valuable_papers_adapter_receipt"]["source_local_lane_binding_receipt"]["withheld_mappings"])
    assert len(expected) == 9
    return entry, context, expected


def _receipt(candidate):
    return candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]["original_source_mapping_lane_receipt"]


def _audit_replay(candidate, context):
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert candidate["component_regions"] == context["regions"]
    assert candidate["closure_receipt"]["query_receipt"] == context["query_receipt"]
    assert family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(candidate, **context) == candidate


@pytest.mark.parametrize("name,rule", [
    ("shb-doc162", "EXPLICIT_CURRENT_COMPARATIVE_GROUP_BLOCKS"),
    ("tpb-doc231", "EXPLICIT_DATED_SAME_POPULATION_TABLE_PAIR"),
    ("msb-doc084", "EXPLICIT_UNIQUE_CURRENT_ONLY_MATURITY_NARRATIVE"),
])
def test_actual_original_source_lanes_keep_every_observed_role_without_donated_periods(name, rule):
    _entry, context, expected = _fixture(name)
    original = copy.deepcopy(context["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY, candidate["reasons"]
    assert candidate["reasons"] == []
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert mappings.keys() == {item["role"] for item in expected}
    for previous in expected:
        assert mappings[previous["role"]]["values"] == previous["values"]
        assert mappings[previous["role"]]["unit"] == previous["unit"]
    receipt = _receipt(candidate)
    assert receipt["failures"] == []
    assert all(table["status"] == "SOURCE_OWNED" and table["period_rule"] == rule
               for table in receipt["source_lane_inventory"]["tables"])
    assert all(check["failures"] == [] for check in receipt["checks"])
    retired = _decode(receipt["retired_financial_permissions"])
    assert retired["structural_root_receipt"]
    assert not any(item["equation_kind"] == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
                   for item in candidate["closure_receipt"]["equations"])
    assert candidate["closure_receipt"]["structural_root_receipt"]["source_mapping_id"] == mappings["FAMILY_ROOT_TOTAL"]["item_mapping_id"]
    assert context["page_json_by_version"] == original
    _audit_replay(candidate, context)


def test_actual_shb_anonymous_terminal_totals_have_block_proof_without_invented_ancestry():
    _entry, context, _expected = _fixture("shb-doc162")
    page = next(iter(context["page_json_by_version"].values()))
    table = page["sections"][2]["tables"][1]
    assert table["rows"][7]["hierarchy_path_exact"] == [None]
    assert table["rows"][15]["hierarchy_path_exact"] == [None]
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY
    proof = _receipt(candidate)["source_lane_inventory"]["tables"][0]
    assert [block["source_end_row"] for block in proof["blocks"]] == [8, 16]
    assert [block["period_marker_exact"] for block in proof["blocks"]] == ["Số dư cuối năm", "Số dư đầu năm"]
    assert all(equation["status"] == "EXACT" for block in proof["blocks"] for equation in block["equations"])
    assert table["rows"][7]["hierarchy_path_exact"] == [None]
    _audit_replay(candidate, context)


def test_actual_msb_summary_financial_refs_and_current_only_tenors_remain_distinct():
    _entry, context, _expected = _fixture("msb-doc084")
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY
    for mapping in candidate["mappings"]:
        if mapping["role"] in {"FAMILY_ROOT_TOTAL", "CERTIFICATE_OF_DEPOSIT", "BOND"}:
            assert len(mapping["values"]) == 2
            assert len(mapping["source_refs"]) == 1
            assert mapping["source_refs"][0]["locator"]["table_id"] == "t1"
            assert mapping["source_refs"][0]["money_column_ordinals"] == [1, 2]
        else:
            assert len(mapping["values"]) == 1
            assert mapping["source_refs"][0]["locator"]["table_id"] == "t2"
    receipt = _receipt(candidate)
    assert len(_decode(receipt["comparison_only_evidence"])) == 3
    block = receipt["source_lane_inventory"]["tables"][0]["blocks"][0]
    assert block["lane_key"] == ["SEMANTIC_ALIAS", "CURRENT_PERIOD"]
    assert "source_date" not in receipt["source_lane_inventory"]["tables"][0]
    _audit_replay(candidate, context)


def test_actual_undated_tpb_roles_stay_held_and_printed_root_is_only_inert_evidence():
    _entry, context, _expected = _fixture("tpb-doc227")
    original = copy.deepcopy(context["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    receipt = _receipt(candidate)
    assert "TRANSPOSED_ORIGINAL_SOURCE_PERIOD_OWNER_UNPROVEN" in receipt["failures"]
    assert receipt["known_root_controls_grant_schema_mapping"] is False
    roots = _decode(receipt["known_printed_root_controls"])
    assert len(roots) == 1
    assert [cell["coefficient"] for cell in roots[0]["cells"]] == [38602200, 36632200]
    assert roots[0]["source_ref"]["locator"]["table_id"] == "t1"
    assert candidate["closure_receipt"]["equations"] == []
    assert candidate["closure_receipt"]["root_component_sum_receipts"] == []
    assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    assert receipt["financial_permission_granted_to_preexisting_unresolved"] is False
    assert context["page_json_by_version"] == original
    assert next(iter(original.values()))["sections"][0]["tables"][1]["rows"][3]["values_exact"][1] == "_"
    _audit_replay(candidate, context)


def _counterfactual(name, mutation):
    """Separate synthetic identities from the original FULL271 coordinates."""
    _entry, original, _expected = _fixture(name)
    page = copy.deepcopy(next(iter(original["page_json_by_version"].values())))
    section = page["sections"][2 if name == "shb-doc162" else (1 if name == "tpb-doc231" else 0)]
    detail = section["tables"][1]
    rows = detail["rows"]
    if mutation == "missing_marker":
        rows[8]["label_exact"] = "Một dân số khác"
        rows[8]["hierarchy_path_exact"] = [rows[8]["label_exact"]]
    elif mutation == "duplicate_total":
        rows.insert(7, copy.deepcopy(rows[7]))
    elif mutation == "duplicate_carrier":
        rows.insert(7, copy.deepcopy(rows[3]))
    elif mutation == "wrong_ancestry":
        rows[3]["hierarchy_path_exact"][0] = "Một dân số khác"
    elif mutation == "blank_source":
        rows[3]["values_exact"][0] = None
    elif mutation == "blank_carrier_and_leaf":
        rows[3]["values_exact"][1] = None
        rows[4]["values_exact"][1] = None
    elif mutation == "reset":
        rows.insert(4, {"row_kind": "ITEM", "label_exact": "Các khoản nợ khác",
            "hierarchy_path_exact": ["Các khoản nợ khác"], "values_exact": [None, None, None]})
    elif mutation == "duplicate_date":
        section["tables"][2]["title_exact"] = detail["title_exact"]
    elif mutation == "missing_date":
        detail["title_exact"] = None
    elif mutation == "swapped_dates":
        detail["title_exact"], section["tables"][2]["title_exact"] = (
            section["tables"][2]["title_exact"], detail["title_exact"])
    elif mutation == "contradictory_summary_date":
        section["tables"][0]["columns"][0]["header_path_exact"] = ["31/12/2026"]
    elif mutation == "extra_tenor":
        rows.insert(6, {"row_kind": "ITEM", "label_exact": "Kỳ hạn đặc biệt",
            "hierarchy_path_exact": ["Kỳ hạn đặc biệt"], "values_exact": ["-", "-", "-"]})
    elif mutation == "different_currency":
        row = section["tables"][2]["rows"][1]
        row["label_exact"] = "Bằng ngoại tệ"
        row["hierarchy_path_exact"][-1] = row["label_exact"]
    elif mutation == "qualified_header":
        detail["columns"][0]["header_path_exact"][0] += " của công ty con"
    elif mutation == "foreign_owner":
        section["title_exact"] += " của công ty con"
    elif mutation == "raw_unit":
        detail["unit_exact"] = "VND"
    elif mutation == "missing_narrative":
        section["narratives_exact"] = []
    elif mutation == "conflicting_narrative":
        section["narratives_exact"].append(
            "Chi tiết kỳ hạn của các giấy tờ có giá phát hành theo mệnh giá tại thời điểm đầu kỳ như sau:")
    elif mutation == "duplicate_narrative":
        section["narratives_exact"].append(section["narratives_exact"][0])
    elif mutation == "ambiguous_narrative":
        section["tables"].append(copy.deepcopy(detail))
    elif mutation == "amount_conflict":
        rows[-1]["values_exact"][0] = "999"
    elif mutation == "equal_amount_donor":
        section["tables"].append(copy.deepcopy(section["tables"][0]))
    else:
        raise AssertionError(mutation)
    version = "gfpstorev1:json:" + canonical_json_sha256_v1(page)
    record = {"document_id": "gfpstorev1:document:" + canonical_json_sha256_v1([name, mutation]),
        "document_ordinal": 1, "page_json": page, "page_json_version_id": version,
        "physical_page": 1, "selected_page_ordinal": 1,
        "source_logical_name": f"counterfactual/{name}/{mutation}.pdf", "source_sha256": "e" * 64}
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=[record], compiled_specs=compiled)
    if cluster["status"] != READY:
        assert cluster["status"] == UNRESOLVED and cluster["component_regions"] == []
        return cluster, None
    context = {"regions": cluster["component_regions"], "page_json_by_version": {version: page},
        "compiled_specs": compiled, "query_receipt": build_gemini_json_multitable_hierarchical_region_query_receipt_v1(cluster["component_regions"])}
    return family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context), context


@pytest.mark.parametrize("name,mutation", [
    ("shb-doc162", "missing_marker"), ("shb-doc162", "duplicate_total"),
    ("shb-doc162", "duplicate_carrier"),
    ("shb-doc162", "wrong_ancestry"), ("shb-doc162", "blank_source"),
    ("shb-doc162", "blank_carrier_and_leaf"), ("shb-doc162", "reset"),
    ("tpb-doc231", "duplicate_date"), ("tpb-doc231", "missing_date"),
    ("tpb-doc231", "swapped_dates"), ("tpb-doc231", "extra_tenor"),
    ("tpb-doc231", "contradictory_summary_date"),
    ("tpb-doc231", "different_currency"), ("tpb-doc231", "qualified_header"),
    ("tpb-doc231", "foreign_owner"), ("tpb-doc231", "raw_unit"),
    ("msb-doc084", "missing_narrative"), ("msb-doc084", "ambiguous_narrative"),
    ("msb-doc084", "conflicting_narrative"), ("msb-doc084", "duplicate_narrative"),
    ("msb-doc084", "amount_conflict"), ("tpb-doc227", "equal_amount_donor"),
])
def test_counterfactual_source_scopes_never_gain_lanes_from_amounts_or_unowned_population(name, mutation):
    candidate, context = _counterfactual(name, mutation)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    if context is not None:
        _audit_replay(candidate, context)
        assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False


def test_current_only_period_permission_is_unchanged_when_source_amount_control_fails():
    candidate, context = _counterfactual("msb-doc084", "amount_conflict")
    assert context is not None
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    table = _receipt(candidate)["source_lane_inventory"]["tables"][0]
    assert table["period_rule"] == "EXPLICIT_UNIQUE_CURRENT_ONLY_MATURITY_NARRATIVE"
    assert table["period_narrative_exact"] == (
        "Chi tiết kỳ hạn của các giấy tờ có giá phát hành theo mệnh giá tại thời điểm cuối kỳ như sau:")
    assert "RAW_CURRENT_ONLY_POPULATION_OR_CONTROL_NOT_EXACT" in table["failures"]
    assert "TRANSPOSED_ORIGINAL_SOURCE_PERIOD_OWNER_UNPROVEN" not in table["failures"]
    _audit_replay(candidate, context)


def test_matching_amounts_cannot_join_dated_detail_to_a_different_printed_summary_year():
    candidate, context = _counterfactual("tpb-doc231", "contradictory_summary_date")
    assert context is not None
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    tables = _receipt(candidate)["source_lane_inventory"]["tables"]
    assert len(tables) == 2
    assert all("DATED_TABLE_PERIODS_CONFLICT_WITH_PRINTED_SUMMARY_AXIS" in table["failures"] for table in tables)
    assert all(table["paired_source_dates"] == ["2025-12-31", "2024-12-31"] for table in tables)
    assert all(table["printed_summary_date_axes_for_conflict_veto_only"] == [["2026-12-31", "2024-12-31"]] for table in tables)
    _audit_replay(candidate, context)


@pytest.mark.parametrize("mutation", ["lane", "source", "qualifier", "envelope", "root_permission"])
def test_fresh_replay_rejects_coherently_resealed_original_lane_permission_tampering(mutation):
    _entry, context, _expected = _fixture("msb-doc084")
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY
    forged = copy.deepcopy(candidate)
    receipt = _receipt(forged)
    if mutation == "lane":
        receipt["source_lane_inventory"]["tables"][0]["blocks"][0]["lane_key"][1] = "COMPARATIVE_PERIOD"
    elif mutation == "source":
        receipt["checks"][0]["financial_source_refs"][0]["locator"]["table_id"] = "t99"
    elif mutation == "qualifier":
        receipt["source_lane_inventory"]["tables"][0]["blocks"][0]["population"][0]["currency"] = "USD"
    elif mutation == "envelope":
        envelope = receipt["retired_financial_permissions"]
        envelope["canonical_json"] = "{}\n"
        envelope["sha256"] = sha256(b"{}\n").hexdigest()
        envelope["size_bytes"] = 3
    else:
        receipt["known_root_controls_grant_schema_mapping"] = True
    inventory = receipt["source_lane_inventory"]
    table_ids = {}
    for table in inventory["tables"]:
        previous = table["source_lane_table_proof_id"]
        table["source_lane_table_proof_id"] = "gjivpsltv2:proof:" + canonical_json_sha256_v1({
            key: value for key, value in table.items() if key != "source_lane_table_proof_id"})
        table_ids[previous] = table["source_lane_table_proof_id"]
    inventory["source_lane_inventory_id"] = "gjivpsliv2:inventory:" + canonical_json_sha256_v1({
        key: value for key, value in inventory.items() if key != "source_lane_inventory_id"})
    for check in receipt["checks"]:
        for binding in check["source_lane_bindings"]:
            if binding.get("table_proof_id") in table_ids:
                binding["table_proof_id"] = table_ids[binding["table_proof_id"]]
    receipt["source_mapping_lane_receipt_id"] = "gjivpsmlv2:receipt:" + canonical_json_sha256_v1({
        key: value for key, value in receipt.items() if key != "source_mapping_lane_receipt_id"})
    adapter = forged["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    adapter["adapter_receipt_id"] = "gjivpfav1:receipt:" + canonical_json_sha256_v1({
        key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    forged["closure_receipt"]["structural_root_receipt"]["source_mapping_lane_receipt_id"] = receipt["source_mapping_lane_receipt_id"]
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in forged.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(forged, **context)


def test_known_undated_root_evidence_cannot_be_resealed_into_partial_ready_permission():
    _entry, context, _expected = _fixture("tpb-doc227")
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    forged = copy.deepcopy(candidate)
    receipt = _receipt(forged)
    root = _decode(receipt["known_printed_root_controls"])[0]
    material = {"report_norm_id": 1100, "role": "FAMILY_ROOT_TOTAL", "row_id": root["source_ref"]["row_id"],
        "source_refs": [root["source_ref"]], "values": root["cells"], "unit": root["source_unit_proof"]["canonical_unit"],
        "state": "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL"}
    mapping = {**material, "item_mapping_id": "gjmthfmv1:item:" + canonical_json_sha256_v1(material)}
    forged["mappings"] = [mapping]
    forged["status"] = READY
    forged["reasons"] = []
    receipt["known_root_controls_grant_schema_mapping"] = True
    receipt["source_mapping_lane_receipt_id"] = "gjivpsmlv2:receipt:" + canonical_json_sha256_v1({
        key: value for key, value in receipt.items() if key != "source_mapping_lane_receipt_id"})
    forged["closure_receipt"]["structural_root_receipt"].update({"emitted_mapping": True,
        "source_mapping_id": mapping["item_mapping_id"], "source_mapping_lane_receipt_id": receipt["source_mapping_lane_receipt_id"]})
    adapter = forged["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    adapter["adapter_receipt_id"] = "gjivpfav1:receipt:" + canonical_json_sha256_v1({
        key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in forged.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(forged, **context)
