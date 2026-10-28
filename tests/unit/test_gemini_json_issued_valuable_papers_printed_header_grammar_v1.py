"""Original printed header grammar: source-owned roles/units/periods and fresh public replay."""
from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_issued_valuable_papers_original_source_lanes_v2 import (
    _audit_replay,
    _compiled,
    _fixture,
    _receipt,
)
from test_gemini_json_issued_valuable_papers_source_total_lanes_v1 import _packet_context

from bctc_ai.evaluation import gemini_json_issued_valuable_papers_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/source_structure/f25-printed-header-grammar-20261028-v1"
PROVENANCE_SHA = "773ce1b72318265ddf4b4a5c00b5a321ba0702a9984b08053c6fdc42be2de1fc"
EXPECTED = {
    77: {"FAMILY_ROOT_TOTAL": [27098796, 21210596], "BOND": [18000000, 16800000],
         "CERTIFICATE_OF_DEPOSIT": [9098796, 4410596], "BOND_SHORT": [0], "BOND_MEDIUM": [17000000],
         "BOND_LONG": [1000000], "CD_SHORT": [5900000], "CD_MEDIUM": [3198796], "CD_LONG": [0]},
    163: {"FAMILY_ROOT_TOTAL": [54598314, 39248195], "BOND": [11798719, 6448100],
          "CERTIFICATE_OF_DEPOSIT": [42799595, 32800095], "BOND_SHORT": [0, 0], "BOND_MEDIUM": [4000000, 4000000],
          "BOND_LONG": [7798719, 2448100], "CD_SHORT": [22500000, 12500000], "CD_MEDIUM": [12, 12],
          "CD_LONG": [20299583, 20300083]},
    225: {"FAMILY_ROOT_TOTAL": [54497000, 36632200], "BOND": [26347000, 30632200],
          "CERTIFICATE_OF_DEPOSIT": [28150000, 6000000], "BOND_SHORT": [0, 0], "BOND_MEDIUM": [13500000, 21800000],
          "BOND_LONG": [12847000, 8832200], "CD_SHORT": [27750000, 6000000], "CD_MEDIUM": [400000, 0],
          "CD_LONG": [0, 0]},
}


def _original(ordinal):
    raw = (FIXTURES / "provenance.json").read_bytes()
    assert sha256(raw).hexdigest() == PROVENANCE_SHA
    provenance = json.loads(raw)
    assert provenance["source_receipt"]["sha256"] == "ffc52c4b6e784ae4e7f80cf4b9fa0218ff4266dd3742f4fe25f6479f72c69118"
    assert {item["document_ordinal"] for item in provenance["cases"]} == {77, 163, 225}
    case = next(item for item in provenance["cases"] if item["document_ordinal"] == ordinal)
    ref = case["raw_ref"]
    payload = (FIXTURES / ref["file"]).read_bytes()
    assert len(payload) == ref["size_bytes"] and sha256(payload).hexdigest() == ref["sha256"]
    assert payload.endswith(b"\n\n") and not payload.endswith(b"\n\n\n")
    page = json.loads(payload)
    version = case["original_sqlite_identity"]["page_json_version_id"]
    regions = copy.deepcopy(case["selected_regions"])
    context = {"regions": regions, "page_json_by_version": {version: page}, "compiled_specs": _compiled(),
               "query_receipt": family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(regions)}
    return case, context


def _assert_printed(candidate, context, ordinal):
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert mappings.keys() == EXPECTED[ordinal].keys()
    for role, expected in EXPECTED[ordinal].items():
        mapping = mappings[role]
        assert [cell["coefficient"] for cell in mapping["values"]] == expected
        assert mapping["unit"] == "MILLION_VND"

    receipt = _receipt(candidate)
    assert receipt["failures"] == []
    assert all(item["status"] == "SOURCE_OWNED" for item in receipt["source_lane_inventory"]["tables"])
    _audit_replay(candidate, context)


@pytest.mark.parametrize("ordinal", [77, 163, 225])
def test_actual_original_headers_recover_exact_printed_values_without_source_mutation(ordinal):
    case, context = _original(ordinal)
    before = copy.deepcopy(context["page_json_by_version"])
    payload_before = (FIXTURES / case["raw_ref"]["file"]).read_bytes()
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    _assert_printed(candidate, context, ordinal)
    inventory = _receipt(candidate)["source_lane_inventory"]
    assert all(item["original_printed_header_scope"]["source_values_used_as_header_authority"] is False
               for item in inventory["tables"])
    for item in inventory["tables"]:
        region = item["region"]
        original = before[region["page_json_version_id"]]["sections"][int(region["section_id"][1:]) - 1]["tables"][int(region["table_id"][1:]) - 1]
        assert [w["header_path_exact"] for w in item["original_printed_header_scope"]["source_header_witnesses"]] == [
            c["header_path_exact"] for c in original["columns"]]
    assert context["page_json_by_version"] == before
    assert (FIXTURES / case["raw_ref"]["file"]).read_bytes() == payload_before


def test_actual_header_dates_are_owned_by_every_column_not_borrowed_from_summary_or_title():
    _case, context = _original(225)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    _assert_printed(candidate, context, 225)
    tables = _receipt(candidate)["source_lane_inventory"]["tables"]
    assert [table["source_date"] for table in tables] == ["2025-12-31", "2024-12-31"]
    for table in tables:
        witnesses = table["original_printed_header_scope"]["source_header_witnesses"]
        assert len(witnesses) == 3
        assert {w["explicit_date_atoms"][0]["source_date"] for w in witnesses} == {table["source_date"]}
    assert tables[0]["paired_source_dates"] == tables[1]["paired_source_dates"] == ["2025-12-31", "2024-12-31"]


def test_actual_interim_group_markers_and_current_only_narrative_do_not_gain_new_periods():
    for ordinal in (77, 163):
        _case, context = _original(ordinal)
        candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
        _assert_printed(candidate, context, ordinal)
        table = _receipt(candidate)["source_lane_inventory"]["tables"][0]
        if ordinal == 163:
            assert [b["period_marker_exact"] for b in table["blocks"]] == ["Số dư cuối kỳ", "Số dư đầu kỳ"]
        else:
            assert len(table["blocks"]) == 1
            assert table["blocks"][0]["lane_key"] == ["SEMANTIC_ALIAS", "CURRENT_PERIOD"]
            assert "tại thời điểm cuối kỳ" in table["period_narrative_exact"]
            assert all(len(m["values"]) == 1 for m in candidate["mappings"]
                       if m["role"] not in {"FAMILY_ROOT_TOTAL", "BOND", "CERTIFICATE_OF_DEPOSIT"})


@pytest.mark.parametrize("name", ["shb-doc162", "msb-doc084", "tpb-doc231"])
def test_previous_original_presentations_stay_ready_with_exact_existing_values(name):
    _entry, context, expected = _fixture(name)
    before = copy.deepcopy(context["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    for prior in expected:
        assert mappings[prior["role"]]["values"] == prior["values"]
        assert mappings[prior["role"]]["unit"] == prior["unit"]
    assert context["page_json_by_version"] == before
    _audit_replay(candidate, context)


def test_previous_original_msb76_current_only_source_stays_ready():
    _case, context = _packet_context("f25-msb-doc076")
    before = copy.deepcopy(context["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY, candidate["reasons"]
    root = next(m for m in candidate["mappings"] if m["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [32634109, 21210596]
    assert context["page_json_by_version"] == before
    _audit_replay(candidate, context)


def _counterfactual(ordinal, mutation):
    _case, context = _original(ordinal)
    page = copy.deepcopy(next(iter(context["page_json_by_version"].values())))
    section = page["sections"][{77: 1, 163: 2, 225: 1}[ordinal]]
    detail = section["tables"][1]
    if mutation == "unknown_qualifier":
        detail["columns"][0]["header_path_exact"].append("Giá trị hợp lý")
    elif mutation == "null_part":
        detail["columns"][0]["header_path_exact"].append(None)
    elif mutation == "numeric_part":
        detail["columns"][0]["header_path_exact"].append(7)  # Defensive direct-family-API input; not stored schema admission.
    elif mutation == "duplicate_role":
        # SHB repeats BOND itself: mixing BOND/CD instead exercises the frozen
        # engine's multi-column aggregation of a legitimately blank child.
        detail["columns"][0]["header_path_exact"].append("Trái phiếu" if ordinal == 163 else "Chứng chỉ tiền gửi")
    elif mutation == "duplicate_unit":
        detail["columns"][0]["header_path_exact"].append("Triệu VND")
        if ordinal == 163:  # Its original column has no unit atom; one addition is valid.
            detail["columns"][0]["header_path_exact"].append("Triệu VND")
    elif mutation == "conflicting_unit":
        detail["columns"][0]["header_path_exact"].append("VND")
    elif mutation == "partial_axis_heading":
        detail["columns"][0]["header_path_exact"].pop(0)
    elif mutation == "header_date_on_two_group_periods":
        for column in detail["columns"]:
            column["header_path_exact"].append("Tại ngày 30 tháng 06 năm 2025")
    elif mutation == "column_date_conflict":
        detail["columns"][0]["header_path_exact"][0] = "Tại ngày 31 tháng 12 năm 2023"
    elif mutation == "title_date_conflict":
        detail["title_exact"] = "Tại ngày 31 tháng 12 năm 2023"
    elif mutation == "missing_header_date":
        for column in detail["columns"]:
            column["header_path_exact"].pop(0)
    elif mutation == "one_missing_header_date":
        detail["columns"][0]["header_path_exact"].pop(0)
    elif mutation == "same_date_twice":
        for column in section["tables"][2]["columns"]:
            column["header_path_exact"][0] = "Tại ngày 31 tháng 12 năm 2025"
    elif mutation == "summary_date_conflict":
        section["tables"][0]["columns"][0]["header_path_exact"][0] = "31/12/2026"
    elif mutation == "missing_narrative":
        section["narratives_exact"] = []
    elif mutation == "duplicate_narrative":
        section["narratives_exact"].append(section["narratives_exact"][0])
    else:
        raise AssertionError(mutation)
    version = "gfpstorev1:json:" + canonical_json_sha256_v1(page)
    record = {"document_id": "gfpstorev1:document:" + canonical_json_sha256_v1([ordinal, mutation]),
              "document_ordinal": 1, "page_json": page, "page_json_version_id": version,
              "physical_page": 1, "selected_page_ordinal": 1,
              "source_logical_name": f"counterfactual/printed-header-{ordinal}-{mutation}.pdf", "source_sha256": "e" * 64}
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=[record], compiled_specs=compiled)
    if cluster["status"] != READY:
        assert cluster["status"] == UNRESOLVED and cluster["component_regions"] == []
        return cluster, None
    context = {"regions": cluster["component_regions"], "page_json_by_version": {version: page}, "compiled_specs": compiled,
               "query_receipt": family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(cluster["component_regions"])}
    return family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context), context


@pytest.mark.parametrize("ordinal,mutation", [
    (ordinal, mutation) for ordinal in (77, 163, 225)
    for mutation in ("unknown_qualifier", "null_part", "numeric_part", "duplicate_role", "duplicate_unit", "conflicting_unit")
] + [(163, "partial_axis_heading"), (163, "header_date_on_two_group_periods"), (225, "column_date_conflict"), (225, "title_date_conflict"),
     (225, "missing_header_date"), (225, "one_missing_header_date"), (225, "same_date_twice"),
     (225, "summary_date_conflict"), (77, "missing_narrative"), (77, "duplicate_narrative")])
def test_coherent_source_counterfactuals_cannot_gain_header_or_period_permission(ordinal, mutation):
    candidate, context = _counterfactual(ordinal, mutation)
    assert candidate["status"] == UNRESOLVED, candidate["reasons"]
    assert candidate.get("mappings", []) == []  # A query-level rejection has no financial mapping payload.
    if context is not None:
        assert candidate["closure_receipt"]["equations"] == []
        _audit_replay(candidate, context)


def test_original_undated_tpb227_stays_held_without_summary_period_donation():
    _entry, context, _expected = _fixture("tpb-doc227")
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert _receipt(candidate)["known_root_controls_grant_schema_mapping"] is False
    _audit_replay(candidate, context)


def test_header_witness_reseal_does_not_replace_fresh_public_source_replay():
    _case, context = _original(225)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY
    forged = copy.deepcopy(candidate)
    receipt = _receipt(forged)
    inventory = receipt["source_lane_inventory"]
    inventory["tables"][0]["original_printed_header_scope"]["source_header_witnesses"][0]["explicit_date_atoms"][0]["source_date"] = "2023-12-31"
    replaced = {}
    for table in inventory["tables"]:
        old_id = table["source_lane_table_proof_id"]
        table["source_lane_table_proof_id"] = "gjivpsltv2:proof:" + canonical_json_sha256_v1({k: v for k, v in table.items() if k != "source_lane_table_proof_id"})
        replaced[old_id] = table["source_lane_table_proof_id"]
    inventory["source_lane_inventory_id"] = "gjivpsliv2:inventory:" + canonical_json_sha256_v1({k: v for k, v in inventory.items() if k != "source_lane_inventory_id"})
    for check in receipt["checks"]:
        for binding in check["source_lane_bindings"]:
            if binding.get("table_proof_id") in replaced:
                binding["table_proof_id"] = replaced[binding["table_proof_id"]]
    receipt["source_mapping_lane_receipt_id"] = "gjivpsmlv2:receipt:" + canonical_json_sha256_v1({k: v for k, v in receipt.items() if k != "source_mapping_lane_receipt_id"})
    adapter = forged["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    adapter["adapter_receipt_id"] = "gjivpfav1:receipt:" + canonical_json_sha256_v1({k: v for k, v in adapter.items() if k != "adapter_receipt_id"})
    forged["closure_receipt"]["structural_root_receipt"]["source_mapping_lane_receipt_id"] = receipt["source_mapping_lane_receipt_id"]
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({k: v for k, v in forged.items() if k != "candidate_id"})
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(forged, **context)
