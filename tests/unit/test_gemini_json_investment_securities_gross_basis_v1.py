from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonInvestmentSecuritiesFamilyV1Error,
    _child_records,
    _equation,
    _gross_frontier_source_proof_v1,
    build_gemini_json_investment_securities_region_query_receipt_v1,
    coalesce_gemini_json_investment_securities_document_v1,
    compile_gemini_json_investment_securities_family_specs_v1,
    evaluate_gemini_json_investment_securities_family_cluster_v1,
    validate_gemini_json_investment_securities_family_candidate_replay_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/source_structure/f16-gross-basis-20261028-v1"
MANIFEST_SHA256 = "bc3dc4707da6db217d1b0c61bf4ed6d20bdf818aaac53cac1dc5061373566fde"


def _compiled() -> dict:
    def load(name: str) -> dict:
        return json.loads((ROOT / "config/families" / name).read_bytes())

    return compile_gemini_json_investment_securities_family_specs_v1(
        load("tm-investment-securities-topology-v1.json"),
        load("tm-investment-securities-evaluation-v1.json"),
        load("tm-investment-securities-schema-binding-v1.json"),
    )


def _envelope(value: dict) -> object:
    data = value["canonical_json_utf8"].encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == value["sha256"]
    assert len(data) == value["size_bytes"]
    decoded = json.loads(data)
    assert data == canonical_json_bytes_v1(decoded)
    assert value["disposition"] == "INACTIVE_SOURCE_BEFOREIMAGE_NOT_SCHEMA_PERMISSION"
    return decoded


def _real(name: str) -> tuple[dict, list, dict, dict, dict]:
    payload = (FIXTURES / "manifest.json").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == MANIFEST_SHA256
    fixture = next(case for case in json.loads(payload)["cases"] if case["name"] == name)
    axis_bytes = (FIXTURES / name / "selected-axis.json").read_bytes()
    assert hashlib.sha256(axis_bytes).hexdigest() == fixture["selected_axis_ref"]["sha256"]
    assert len(axis_bytes) == fixture["selected_axis_ref"]["size_bytes"]
    axis = json.loads(axis_bytes)
    assert axis["document"]["source_sha256"] == fixture["pdf"]["sha256"]
    pages = {}
    selected_ordinals = {}
    for page in fixture["pages"]:
        version = page["version"]
        raw = (FIXTURES / name / version["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == version["canonical_json_sha256"]
        assert len(raw) == version["canonical_json_size_bytes"]
        selected = [
            entry
            for entry in axis["document_manifest_ref_entries"]
            if entry.get("page_json_version_id") == version["page_json_version_id"]
        ]
        assert len(selected) == 1
        assert selected[0]["canonical_json_sha256"] == version["canonical_json_sha256"]
        assert selected[0]["physical_page"] == page["physical_page"]
        match = re.fullmatch(r"/pages\[([0-9]+)\]", selected[0]["json_path"])
        assert match is not None
        selected_ordinals[version["page_json_version_id"]] = int(match[1]) + 1
        pages[version["page_json_version_id"]] = json.loads(raw)
    original = fixture["candidate_beforeimage"]
    assert original["candidate_id"] == "gjfiscv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in original.items() if key != "candidate_id"}
    )
    regions = copy.deepcopy(original["component_regions"])
    for region in regions:
        assert region["page_json_version_id"] in pages
        assert region["selected_page_ordinal"] == selected_ordinals[region["page_json_version_id"]]
        assert region["source_sha256"] == fixture["pdf"]["sha256"]
    compiled = _compiled()
    first = regions[0]
    page_records = [
        {
            **{key: first[key] for key in (
                "document_id", "document_ordinal", "source_logical_name", "source_sha256"
            )},
            "page_json": pages[page["version"]["page_json_version_id"]],
            "page_json_version_id": page["version"]["page_json_version_id"],
            "physical_page": page["physical_page"],
            "selected_page_ordinal": selected_ordinals[page["version"]["page_json_version_id"]],
        }
        for page in fixture["pages"]
    ]
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=page_records, compiled_specs=compiled
    )
    assert cluster["status"] == READY, cluster["reasons"]
    assert cluster["component_regions"] == regions
    candidate = _evaluate(compiled, regions, pages)
    return compiled, regions, pages, candidate, fixture


def _evaluate(compiled: dict, regions: list, pages: dict) -> dict:
    return evaluate_gemini_json_investment_securities_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=build_gemini_json_investment_securities_region_query_receipt_v1(regions),
    )


def _fresh_modified(compiled: dict, original_regions: list, pages: dict) -> tuple[list, dict]:
    """Query the entire synthetic modified page axis, including added tables."""

    first = original_regions[0]
    positions = {item["page_json_version_id"]: item for item in original_regions}
    records = [
        {
            **{key: first[key] for key in (
                "document_id", "document_ordinal", "source_logical_name", "source_sha256"
            )},
            "page_json": page,
            "page_json_version_id": version,
            "physical_page": positions[version]["physical_page"],
            "selected_page_ordinal": positions[version]["selected_page_ordinal"],
        }
        for version, page in pages.items()
    ]
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY, cluster["reasons"]
    regions = cluster["component_regions"]
    return regions, _evaluate(compiled, regions, pages)


def _audit_and_replay(compiled: dict, regions: list, pages: dict, candidate: dict) -> None:
    audit = validate_source_observation_mapping_contract_v1(candidate)
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert validate_gemini_json_investment_securities_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=build_gemini_json_investment_securities_region_query_receipt_v1(regions),
    ) == candidate


def _values(mapping: dict) -> list:
    return [cell["coefficient"] for cell in mapping["values"]]


@pytest.mark.parametrize(
    ("name", "afs", "htm"),
    [
        ("bab-doc013", [12643232, 9400555], None),
        ("lpb-doc069", [52767786, 58080339], None),
        ("pgb-doc140", [5576114, 1937014], [2000000, 1600000]),
        ("stb-doc193", [33039340, 23545019], [57505166, 60415187]),
        ("abb-doc001", [30251302, 17767222], [150000, 150000]),
    ],
)
def test_real_original_selected_pages_bind_only_core_gross_totals(
    name: str, afs: list, htm: list | None
) -> None:
    compiled, regions, pages, candidate, fixture = _real(name)
    assert candidate["status"] == READY, candidate["reasons"]
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    for prefix, expected in (("AFS", afs), ("HTM", htm)):
        if expected is None:
            assert prefix + "_TOTAL" not in by_role
            continue
        total = by_role[prefix + "_TOTAL"]
        assert _values(total) == expected
        assert total["valuation_basis"] == "GROSS_BEFORE_PROVISIONS"
        assert total["population"] == prefix + "_CORE_EXCLUDING_VAMC"
        proof = next(
            item for item in candidate["closure_receipt"]["schema_basis_receipts"]
            if item["role"] == prefix + "_TOTAL"
        )
        assert proof["status"].startswith("BOUND_")
        assert proof["emitted_mapping"] is True
        assert total["schema_basis_receipt_id"] == proof["basis_receipt_id"]
        assert proof["basis_receipt_id"] == "gjfisgbv1:basis:" + canonical_json_sha256_v1(
            {key: value for key, value in proof.items() if key != "basis_receipt_id"}
        )
        assert proof["source_proof"]["basis"] == "GROSS_BEFORE_PROVISIONS"
        _envelope(proof["raw_total_beforeimages"])
    assert fixture["family_run"]["implementation_refs_json"][-1]["sha256"] == (
        "24e2f49e313f0150cea825fe1357bbe35c0f19b2f090d34f5a5d3ca8bb19582a"
    )
    # The historical producer mismatch is evidence, never a fresh-run waiver.
    _audit_and_replay(compiled, regions, pages, candidate)


def test_real_bab_net_beforeimages_remain_controls_without_provision_addback() -> None:
    compiled, regions, pages, candidate, fixture = _real("bab-doc013")
    assert candidate["status"] == READY, candidate["reasons"]
    old = {item["role"]: item for item in fixture["candidate_beforeimage"]["mappings"]}
    new = {item["role"]: item for item in candidate["mappings"]}
    assert _values(old["AFS_TOTAL"]) == [12631155, 9380559]
    assert _values(new["AFS_TOTAL"]) == [12643232, 9400555]
    for role in old.keys() - {"AFS_TOTAL"}:
        assert new[role] == old[role]
    receipt = candidate["closure_receipt"]
    assert any(
        item["result_role"] == "AFS_NET_TOTAL_CONTROL"
        and item["result_coefficients"] == [12631155, 9380559]
        for item in receipt["equations"]
    )
    gross = next(item for item in receipt["equations"] if item["result_role"] == "AFS_TOTAL")
    assert gross["component_roles"] == ["AFS_DEBT", "AFS_EQUITY"]
    assert "PROVISION" not in " ".join(gross["component_roles"])
    _audit_and_replay(compiled, regions, pages, candidate)


@pytest.mark.parametrize("name", ["pgb-doc140", "stb-doc193"])
def test_real_vamc_parent_summary_is_not_a_second_core_provision(name: str) -> None:
    compiled, regions, pages, candidate, _fixture = _real(name)
    assert candidate["status"] == READY, candidate["reasons"]
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert by_role["VAMC_PROVISION"]["population"] == "VAMC_ONLY"
    if name == "pgb-doc140":
        assert _values(by_role["HTM_PROVISION"]) == [0, 0]
        assert all(cell["state"] == "DASH_ZERO" for cell in by_role["HTM_PROVISION"]["values"])
        assert by_role["HTM_PROVISION"]["source_refs"][0]["row_ordinal"] == 25
        assert by_role["HTM_TOTAL"]["source_refs"][0]["row_ordinal"] == 12
    else:
        assert "HTM_PROVISION" not in by_role
    receipts = candidate["closure_receipt"]["provision_population_receipts"]
    assert len(receipts) == 1
    before = _envelope(receipts[0]["parent_beforeimage"])
    assert before["role"] == "HTM_PROVISION"
    assert receipts[0]["disposition"] == "COMBINED_SOURCE_PARENT_NOT_CORE_HTM_PROVISION"
    proof = receipts[0]
    assert proof["failures"] == []
    assert proof["printed_parent_occurrences"] == [proof["parent_source_occurrence"][3]]
    assert proof["unit_axis"]["complete"] and proof["period_axis"]["complete"]
    assert proof["source_money_column_ordinals"] == [1, 2]
    frontier = _envelope(proof["frontier_beforeimage"])
    assert len(frontier) == (2 if name == "pgb-doc140" else 1)
    assert all(
        ref["locator"][key] == before["source_refs"][0]["locator"][key]
        for item in frontier for ref in item["source_refs"]
        for key in ("page_json_version_id", "section_id", "table_id")
    )
    assert proof["population_receipt_id"] == "gjfispopv1:local:" + canonical_json_sha256_v1(
        {key: value for key, value in proof.items() if key != "population_receipt_id"}
    )
    local_equations = [
        item for item in candidate["closure_receipt"]["equations"]
        if item["result_role"] == "HTM_VAMC_PROVISION_CONTROL"
    ]
    assert len(local_equations) == 1 and local_equations[0]["status"] == "EXACT"
    assert local_equations[0]["component_source_refs"] == [item["source_refs"] for item in frontier]
    assert any(
        item["result_role"] == "HTM_VAMC_PROVISION_CONTROL"
        for item in candidate["closure_receipt"]["equations"]
    )
    assert not any(
        item["result_role"] == "HTM_PROVISION" and "VAMC_PROVISION" in item["component_roles"]
        for item in candidate["closure_receipt"]["equations"]
    )
    _audit_and_replay(compiled, regions, pages, candidate)


def test_real_abb_positive_component_values_and_sources_are_preserved() -> None:
    compiled, regions, pages, candidate, fixture = _real("abb-doc001")
    assert candidate["status"] == READY, candidate["reasons"]
    old = {item["role"]: item for item in fixture["candidate_beforeimage"]["mappings"]}
    new = {item["role"]: item for item in candidate["mappings"]}
    assert new.keys() == old.keys()
    for role in old:
        for field in ("values", "source_refs", "unit", "state"):
            assert new[role][field] == old[role][field]
    _audit_and_replay(compiled, regions, pages, candidate)


def test_real_pgb_missing_vamc_child_ownership_holds_without_amount_join() -> None:
    compiled, regions, pages, _candidate, _fixture = _real("pgb-doc140")
    page = next(iter(pages.values()))
    row = page["sections"][0]["tables"][0]["rows"][25]
    row["hierarchy_path_exact"] = [row["label_exact"]]
    candidate = _evaluate(compiled, regions, pages)
    assert candidate["status"] == UNRESOLVED
    assert "HOLD_AMBIGUOUS_CORE_OR_COMBINED_HTM_PROVISION" in candidate["reasons"]
    assert candidate["mappings"] == []
    _envelope(candidate["closure_receipt"]["withheld_record_beforeimages"])
    _audit_and_replay(compiled, regions, pages, candidate)


@pytest.mark.parametrize("mutation", ["basis", "population", "envelope_hash", "envelope_text"])
def test_fresh_replay_rejects_coherently_resealed_basis_or_evidence_tamper(mutation: str) -> None:
    compiled, regions, pages, candidate, _fixture = _real("bab-doc013")
    forged = copy.deepcopy(candidate)
    if mutation in {"basis", "population"}:
        total = next(item for item in forged["mappings"] if item["role"] == "AFS_TOTAL")
        total["valuation_basis" if mutation == "basis" else "population"] = "NET_INCLUDING_PROVISION"
        total["item_mapping_id"] = "gjfismv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in total.items() if key != "item_mapping_id"}
        )
    else:
        envelope = forged["closure_receipt"]["schema_basis_receipts"][0]["raw_total_beforeimages"]
        if mutation == "envelope_hash":
            envelope["sha256"] = "0" * 64
        else:
            envelope["canonical_json_utf8"] = "[]\n"
            envelope["sha256"] = hashlib.sha256(b"[]\n").hexdigest()
            envelope["size_bytes"] = 3
    forged["candidate_id"] = "gjfiscv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "candidate_id"}
    )
    with pytest.raises(GeminiJsonInvestmentSecuritiesFamilyV1Error, match="does not replay"):
        validate_gemini_json_investment_securities_family_candidate_replay_v1(
            forged, regions=regions, page_json_by_version=pages, compiled_specs=compiled,
            query_receipt=build_gemini_json_investment_securities_region_query_receipt_v1(regions),
        )


@pytest.mark.parametrize(
    "mutation", ["blank", "wrong_coefficient", "duplicate", "population", "table", "unit", "period"]
)
def test_component_gross_proof_rejects_incomplete_or_foreign_source_axes(mutation: str) -> None:
    _compiled_specs, _regions, pages, candidate, _fixture = _real("bab-doc013")
    components = [
        {"role": item["role"], "cells": item["values"], "source_refs": item["source_refs"], "state": item["state"]}
        for item in copy.deepcopy(candidate["mappings"])
        if item["role"] in {"AFS_DEBT", "AFS_EQUITY"}
    ]
    receipts = copy.deepcopy(candidate["closure_receipt"]["table_receipts"])
    assert _gross_frontier_source_proof_v1(
        "AFS", components, table_receipts=receipts, page_json_by_version=pages
    ) is not None
    if mutation == "blank":
        components[0]["cells"][0]["coefficient"] = None
    elif mutation == "wrong_coefficient":
        components[0]["cells"][0]["coefficient"] += 1
    elif mutation == "duplicate":
        components.append(copy.deepcopy(components[0]))
    elif mutation == "population":
        components[0]["role"] = "VAMC_FACE_VALUE"
    elif mutation == "table":
        components[0]["source_refs"][0]["locator"]["table_id"] = "t2"
    elif mutation == "unit":
        receipts[0]["unit_axis"]["source"] = "PRIMARY_STATEMENT_UNIT_DONOR"
    else:
        receipts[0]["period_axis"]["complete"] = False
    assert _gross_frontier_source_proof_v1(
        "AFS", components, table_receipts=receipts, page_json_by_version=pages
    ) is None


def test_zero_duplicate_source_occurrence_cannot_close_an_equation() -> None:
    _compiled_specs, _regions, _pages, candidate, _fixture = _real("pgb-doc140")
    mapping = next(item for item in candidate["mappings"] if item["role"] == "HTM_PROVISION")
    record = {"role": mapping["role"], "cells": mapping["values"], "source_refs": mapping["source_refs"]}
    equation = _equation(equation_kind="ZERO_DUPLICATE_TRAP", components=[record, record], result=record)
    assert equation["component_sums"] == [0, 0]
    assert equation["status"] == "DUPLICATE_COMPONENT_SOURCE_OCCURRENCE"


def test_nonadditive_guaranteed_role_never_becomes_a_peer_when_marker_is_missing() -> None:
    compiled, _regions, _pages, candidate, _fixture = _real("lpb-doc069")
    records = {
        item["role"]: {"role": item["role"], "cells": item["values"], "source_refs": item["source_refs"]}
        for item in copy.deepcopy(candidate["mappings"])
    }
    guaranteed = records["AFS_DEBT_GOVERNMENT_GUARANTEED"]
    for ref in guaranteed["source_refs"]:
        ref["label_exact"] = "Trái phiếu được Chính phủ bảo lãnh"
        ref["hierarchy_path_exact"] = [ref["label_exact"]]
    assert "AFS_DEBT_GOVERNMENT_GUARANTEED" not in {
        item["role"] for item in _child_records("AFS_DEBT", records, compiled_specs=compiled)
    }


def test_incomplete_net_only_frontier_cannot_manufacture_gross_from_provision() -> None:
    compiled, regions, pages, _candidate, _fixture = _real("bab-doc013")
    table = next(iter(pages.values()))["sections"][1]["tables"][0]
    table["rows"][7]["values_exact"][0] = None
    table["rows"][8]["values_exact"][0] = None
    table["rows"][9]["values_exact"][0] = None
    candidate = _evaluate(compiled, regions, pages)
    assert candidate["status"] == UNRESOLVED
    assert "AFS_GROSS_TOTAL_BASIS_NOT_PROVEN" in candidate["reasons"]
    assert candidate["mappings"] == []
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0
    _audit_and_replay(compiled, regions, pages, candidate)


def test_missing_note_unit_does_not_borrow_primary_or_document_consensus() -> None:
    compiled, regions, pages, _candidate, _fixture = _real("bab-doc013")
    note = next(iter(pages.values()))
    note["sections"][1]["tables"][0]["unit_exact"] = None
    primary = copy.deepcopy(note)
    primary["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    for suffix in ("a", "b"):
        pages["gfpstorev1:json:" + suffix * 64] = copy.deepcopy(primary)
    candidate = _evaluate(compiled, regions, pages)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["closure_receipt"]["document_unit_context"]["status"] == "NOT_UNIQUE"
    assert "MONEY_UNIT_NOT_EXACTLY_RESOLVED" in candidate["reasons"]
    _audit_and_replay(compiled, regions, pages, candidate)


def test_unrelated_exclusion_does_not_authorize_core_vamc_provision_alias() -> None:
    compiled, regions, pages, _candidate, _fixture = _real("pgb-doc140")
    row = next(iter(pages.values()))["sections"][0]["tables"][0]["rows"][24]
    row["label_exact"] = (
        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn "
        "(không bao gồm dự phòng khác của VAMC)"
    )
    row["hierarchy_path_exact"][-1] = row["label_exact"]
    candidate = _evaluate(compiled, regions, pages)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    _audit_and_replay(compiled, regions, pages, candidate)


def test_schema_basis_contract_cannot_be_changed_to_net_by_the_caller() -> None:
    specs = [
        json.loads((ROOT / "config/families" / name).read_bytes())
        for name in (
            "tm-investment-securities-topology-v1.json",
            "tm-investment-securities-evaluation-v1.json",
            "tm-investment-securities-schema-binding-v1.json",
        )
    ]
    specs[2]["basis_policy"]["AFS_TOTAL"] = "NET_AFTER_PROVISIONS"
    with pytest.raises(GeminiJsonInvestmentSecuritiesFamilyV1Error, match="schema binding spec"):
        compile_gemini_json_investment_securities_family_specs_v1(*specs)


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        ("cross_table_sum", None),
        ("repeated_parent", "PRINTED_PARENT_OCCURRENCE_NOT_UNIQUE"),
        ("duplicate_equal_child", "OWNED_VAMC_PROVISION_OCCURRENCE_NOT_UNIQUE"),
        ("reset", "OWNED_VAMC_PROVISION_OCCURRENCE_NOT_UNIQUE"),
        ("partial_with_global_complete", "LOCAL_CHILD_LANES_NOT_DIRECTLY_OBSERVED"),
    ],
)
def test_local_provision_control_never_uses_global_or_ambiguous_source_populations(
    mutation: str, failure: str | None
) -> None:
    compiled, old_regions, pages, _candidate, _fixture = _real("stb-doc193")
    version = next(item["page_json_version_id"] for item in old_regions if item["physical_page"] == 47)
    page = pages[version]
    table = page["sections"][0]["tables"][0]
    original_child = copy.deepcopy(table["rows"][7])
    if mutation in {"cross_table_sum", "partial_with_global_complete"}:
        donor = copy.deepcopy(table)
        donor["title_exact"] = "Trái phiếu đặc biệt do VAMC phát hành"
        donor["rows"] = [copy.deepcopy(original_child)]
        donor["rows"][0]["hierarchy_path_exact"] = [
            "Trái phiếu đặc biệt do VAMC phát hành", original_child["label_exact"]
        ]
        if mutation == "cross_table_sum":
            # Two DIFFERENT populations add to the old global value. The
            # local parent must still fail against its own observed child.
            table["rows"][7]["values_exact"] = ["(8.070.176)", "(13.257.858)"]
            donor["rows"][0]["values_exact"] = ["(1)", "(1)"]
        else:
            # A complete equal-valued observation elsewhere cannot fill this
            # local child's blank lane or establish the parent's population.
            table["rows"][7]["values_exact"][0] = None
        page["sections"][0]["tables"].append(donor)
    elif mutation == "repeated_parent":
        table["rows"].insert(7, copy.deepcopy(table["rows"][6]))
    elif mutation == "duplicate_equal_child":
        table["rows"].insert(8, copy.deepcopy(original_child))
    else:
        table["rows"].insert(7, {
            "label_exact": "Chứng khoán kinh doanh", "row_kind": "ITEM",
            "hierarchy_path_exact": ["Chứng khoán kinh doanh"], "values_exact": [None, None],
        })
    regions, candidate = _fresh_modified(compiled, old_regions, pages)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    proofs = candidate["closure_receipt"]["provision_population_receipts"]
    if failure is not None:
        assert any(failure in proof["failures"] for proof in proofs)
        assert "HOLD_AMBIGUOUS_CORE_OR_COMBINED_HTM_PROVISION" in candidate["reasons"]
    else:
        local = [
            item for item in candidate["closure_receipt"]["equations"]
            if item["result_role"] == "HTM_VAMC_PROVISION_CONTROL"
        ]
        assert local and all(item["status"] == "MISMATCH" for item in local)
        assert all(
            ref["locator"]["table_id"] == "t1"
            for item in local for refs in item["component_source_refs"] for ref in refs
        )
        assert all(item["component_roles"] == ["VAMC_PROVISION"] for item in local)
    _envelope(candidate["closure_receipt"]["withheld_record_beforeimages"])
    _audit_and_replay(compiled, regions, pages, candidate)


def test_unobserved_printed_core_child_cannot_be_omitted_from_combined_control() -> None:
    compiled, old_regions, pages, _candidate, _fixture = _real("pgb-doc140")
    row = next(iter(pages.values()))["sections"][0]["tables"][0]["rows"][24]
    row["values_exact"] = [None, None]
    regions, candidate = _fresh_modified(compiled, old_regions, pages)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert any(
        "UNBOUND_VALUE_OR_SCOPE_ROW_INSIDE_LOCAL_PROVISION_PARENT" in proof["failures"]
        for proof in candidate["closure_receipt"]["provision_population_receipts"]
    )
    _audit_and_replay(compiled, regions, pages, candidate)
