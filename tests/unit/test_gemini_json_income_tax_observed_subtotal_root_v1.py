"""Observed SUBTOTAL roots retain all existing source and replay controls."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _primary_page,
    _primary_tax_rows,
)
from test_gemini_json_income_tax_printed_total_root_binding_v1 import (
    REASON,
    _before_binding,
    _bind,
    _by_role,
    _public,
)
from test_gemini_json_income_tax_query_axis_handoff_v1 import _indexed_case, _primary
from test_gemini_json_income_tax_signed_display_v1 import _records

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


FIXTURE = Path(__file__).parents[1] / "fixtures/source_structure/f39-observed-subtotal-20261028-v1"


def _subtotal_page(*, raw=None):
    rows = _primary_tax_rows()
    rows[2]["row_kind"] = "SUBTOTAL"
    if raw is not None:
        rows[2]["values_exact"][2:] = raw
    return _primary_page(rows)


def _original_records(case):
    metadata = json.loads((FIXTURE / "provenance.json").read_text(encoding="utf-8"))
    item = next(value for value in metadata["cases"] if value["case"] == case)
    records = []
    for ordinal, page in enumerate(item["pages"], 1):
        payload = (FIXTURE / case / page["file"]).read_bytes()
        assert sha256(payload).hexdigest() == page["sha256"]
        assert len(payload) == page["size_bytes"]
        records.append({
            "document_id": item["document_id"], "document_ordinal": 1,
            "page_json": json.loads(payload),
            "page_json_version_id": page["page_json_version_id"],
            "physical_page": page["physical_page"], "selected_page_ordinal": ordinal,
            "source_logical_name": item["source_logical_name"],
            "source_sha256": item["source_sha256"],
        })
    return item, records


@pytest.mark.parametrize("case", ["bab-doc020", "eib-doc039"])
def test_original_printed_primary_subtotal_binds_its_own_cells_and_source(case):
    item, records = _original_records(case)
    original = deepcopy(records)
    selected, candidate = _primary(records, _adapter_compiled())
    assert candidate["status"] == READY, candidate.get("reasons")
    root = _by_role(candidate, "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == item["expected_root_coefficients"]
    source = root["source_refs"][0]
    assert source["row_kind"] == "SUBTOTAL"
    assert source["row_ordinal"] == item["root_row_ordinal"]
    assert source["locator"] == selected["descriptor"]["locator"]
    assert source["locator"]["page_json_version_id"] == records[0]["page_json_version_id"]
    row = records[0]["page_json"]["sections"][0]["tables"][0]["rows"][item["root_row_ordinal"] - 1]
    assert [cell["source_text"] for cell in root["values"]] == row["values_exact"][-2:]
    assert candidate["closure_receipt"]["income_tax_printed_primary_root_receipt"][
        "amounts_used_as_role_authority"
    ] is False
    assert records == original


def test_subtotal_uses_actual_public_indexed_binding_and_fresh_replay():
    records = _records()
    records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][3]["row_kind"] = "SUBTOTAL"
    original = deepcopy(records)
    options = _indexed_case(records)
    candidate = options["trials"][0]["candidates"][0]
    assert candidate["status"] == READY, candidate.get("reasons")
    root = _by_role(candidate, "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [-22, -17]
    assert root["source_refs"][0]["row_kind"] == "SUBTOTAL"
    assert root["source_refs"][0]["row_ordinal"] == 4
    assert audit_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"
    assert records == original


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_subtotal_blank_never_inherits_current_tax_or_zero(raw):
    _, candidate = _bind(_subtotal_page(raw=[raw, raw]))
    assert candidate["status"] == UNRESOLVED
    assert candidate["reasons"] == [REASON]
    assert candidate["mappings"] == []
    evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    assert evidence["ownership_failure"] == "PRINTED_TOTAL_SOURCE_MONEY_LANE_NOT_DIRECTLY_OBSERVED"
    assert evidence["source_values_exact"] == [raw, raw]


def test_subtotal_different_printed_population_still_holds():
    page = _subtotal_page()
    page["sections"][0]["tables"][0]["rows"][2]["hierarchy_path_exact"].insert(0, "Công ty con")
    _, candidate = _bind(page)
    assert candidate["status"] == UNRESOLVED and candidate["reasons"] == [REASON]
    assert candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"][
        "ownership_failure"
    ] == "PRINTED_TOTAL_AND_COMPONENT_POPULATION_NOT_PROVEN"


def test_duplicate_subtotal_cannot_become_a_public_ready_root():
    page = _subtotal_page()
    table = page["sections"][0]["tables"][0]
    table["rows"].append(deepcopy(table["rows"][2]))
    assert _public(page)["status"] != READY


def test_subtotal_public_final_controls_reject_observed_arithmetic_mismatch():
    page = _subtotal_page(raw=["41", "60"])
    candidate = _public(page)
    assert candidate["status"] != READY
    assert candidate["mappings"] == []


@pytest.mark.parametrize("field", ["unit", "period", "source"])
def test_subtotal_does_not_relax_unit_period_or_source_ownership(field):
    page = _subtotal_page()
    if field == "unit":
        page["sections"][0]["tables"][0]["unit_exact"] = None
        assert _public(page)["status"] != READY
    elif field == "period":
        table = page["sections"][0]["tables"][0]
        for column in table["columns"]:
            column["header_path_exact"] = ["Kỳ chưa xác định"]
        assert _public(page)["status"] != READY
    else:
        compiled, descriptor, candidate = _before_binding(page)
        page["sections"][0]["tables"][0]["rows"][2]["values_exact"][2] = "41"
        with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="source identity drifted"):
            family._bind_printed_primary_root_v1(
                candidate, source_page=page, descriptor=descriptor, compiled_specs=compiled,
            )


def test_resealed_subtotal_mapping_attack_fails_actual_fresh_trial_replay():
    records = _records()
    records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][3]["row_kind"] = "SUBTOTAL"
    options = _indexed_case(records)
    candidate = options["trials"][0]["candidates"][0]
    root = _by_role(candidate, "FAMILY_ROOT_TOTAL")
    root["values"][0]["coefficient"] -= 1
    root["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
        {key: value for key, value in root.items() if key != "item_mapping_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        family.validate_gemini_json_income_tax_replay_v1(**options)
