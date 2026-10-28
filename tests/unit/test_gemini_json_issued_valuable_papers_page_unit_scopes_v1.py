"""One original page's registered unit scope; no actual PDF/financial run claim."""
from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_issued_valuable_papers_original_source_lanes_v2 import _fixture
from test_gemini_json_issued_valuable_papers_source_total_lanes_v1 import _compiled

from bctc_ai.evaluation import gemini_json_issued_valuable_papers_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/source_structure/f25-page-unit-scope-20261029-v1"


def _catalog():
    raw = (ROOT / family.PAGE_UNIT_CATALOG_PATH).read_bytes()
    assert sha256(raw).hexdigest() == family.PAGE_UNIT_CATALOG_SHA256
    catalog = json.loads(raw)
    assert canonical_json_bytes_v1(catalog) == raw
    return catalog


def _context(*, claimed=True):
    provenance = json.loads((FIXTURE / "provenance.json").read_bytes())
    raw = (FIXTURE / "original-page-038.json").read_bytes()
    assert len(raw) == 7864 and sha256(raw).hexdigest() == provenance["raw_ref"]["sha256"]
    assert raw.endswith(b"\n\n") and not raw.endswith(b"\n\n\n")
    page = json.loads(raw)
    catalog = _catalog()
    compiled = family.bind_gemini_json_issued_valuable_papers_page_unit_scopes_v1(_compiled(), catalog)
    regions = copy.deepcopy(provenance["original_selected_regions"])
    # This is explicitly ONE selected original page, not an invented full55
    # document. No absolute/current date or PRIMARY authority is manufactured.
    for region in regions:
        region["document_ordinal"] = region["selected_page_ordinal"] = 1
    selected = {k: regions[0][k] for k in ("document_id", "document_ordinal", "source_logical_name",
        "source_sha256", "page_json_version_id", "physical_page", "selected_page_ordinal")}
    identity = provenance["original_sqlite_identity"]
    payload = {k: identity[k] for k in ("document_id", "source_logical_name", "source_sha256",
        "page_json_version_id", "physical_page", "canonical_json_sha256", "page_id", "extraction_run_id")}
    claims = ([family.build_gemini_json_issued_valuable_papers_page_unit_claim_v1(
        catalog["claims"][0], selected, payload)] if claimed else None)
    context = {"regions": regions, "page_json_by_version": {selected["page_json_version_id"]: page},
        "compiled_specs": compiled, "selected_page_axis": [selected], "selected_page_provenance": [payload],
        "authenticated_page_unit_claims": claims}
    _query(context)
    return catalog, context


def _query(context):
    context["query_receipt"] = family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        context["regions"], selected_page_axis=context["selected_page_axis"],
        selected_page_provenance=context["selected_page_provenance"],
        authenticated_page_unit_claims=context["authenticated_page_unit_claims"])


def _checked(candidate, context):
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(candidate, **context) == candidate


def test_exact_original_page_unit_registration_keeps_values_and_original_bytes():
    _registered, context = _context()
    before = copy.deepcopy(context["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {m["role"]: m for m in candidate["mappings"]}
    expected = {"BOND": ["1.458.830.500.000", "1.000.000.000.000"],
        "CERTIFICATE_OF_DEPOSIT": ["3.500.000.000.000", "1.145.000.000.000"],
        "FAMILY_ROOT_TOTAL": ["4.958.830.500.000", "2.145.000.000.000"]}
    assert mappings.keys() == expected.keys()
    for role, strings in expected.items():
        assert mappings[role]["unit"] == "VND"
        assert [v["source_text"] for v in mappings[role]["values"]] == strings
        assert all(v["coefficient"] is not None for v in mappings[role]["values"])
    adapter = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    receipt = adapter["original_source_unit_ownership_receipt"]
    assert receipt["failures"] == []
    proofs = [c["original_source_unit_proof"] for c in receipt["checks"]]
    assert proofs and all(p["source_kind"] == family.PAGE_UNIT_SOURCE_KIND for p in proofs)
    assert all(p["raw_unit_exact"] is None and p["printed_unit_exact"] == "Đơn vị tính: VND" for p in proofs)
    assert context["page_json_by_version"] == before
    version = context["regions"][0]["page_json_version_id"]
    assert canonical_json_bytes_v1(before[version]) + b"\n" == (FIXTURE / "original-page-038.json").read_bytes()
    _checked(candidate, context)


def test_unrelated_t1_unit_and_pinned_catalog_without_authenticated_claim_cannot_donate():
    _catalog_value, context = _context(claimed=False)
    page = next(iter(context["page_json_by_version"].values()))
    assert page["sections"][0]["tables"][0]["unit_exact"] == "Đơn vị tính: VND"
    assert page["sections"][0]["tables"][3]["unit_exact"] is None
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert any("ORIGINAL_SOURCE_UNIT_NOT_PROVEN" in r for r in candidate["reasons"])
    _checked(candidate, context)


@pytest.mark.parametrize("field,value", [("catalog_sha256", "0" * 64),
    ("registration_id", "gjivppuv1:registration:" + "0" * 64), ("render_receipt_sha256", "0" * 64),
    ("document_id", "gfpstorev1:document:" + "0" * 64), ("source_sha256", "0" * 64),
    ("page_json_version_id", "gfpstorev1:json:" + "0" * 64), ("physical_page", 39),
    ("canonical_json_sha256", "0" * 64), ("selected_page_ordinal", 2),
    ("renderer_identity", {"pymupdf_version": "unknown"})])
def test_caller_resealed_claim_cannot_replace_registered_selected_source(field, value):
    _catalog_value, context = _context()
    claim = context["authenticated_page_unit_claims"][0]
    (claim if field in claim else claim["selected_source"])[field] = value
    claim["unit_claim_id"] = "gjivppuv1:claim:" + canonical_json_sha256_v1({
        k: v for k, v in claim.items() if k != "unit_claim_id"})
    _query(context)
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error):
        family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)


@pytest.mark.parametrize("mutation", ["unit_conflict", "unit_unknown", "blank_value", "dash_value", "wrong_target"])
def test_raw_beforeimage_or_target_change_never_acquires_registered_unit(mutation):
    _catalog_value, context = _context()
    table = next(iter(context["page_json_by_version"].values()))["sections"][0]["tables"][3]
    if mutation.startswith("unit"):
        table["unit_exact"] = "Triệu đồng" if mutation == "unit_conflict" else "unknown local unit"
    elif mutation == "wrong_target":
        context["regions"][0]["table_id"] = "t1"
    else:
        table["rows"][0]["values_exact"][0] = None if mutation == "blank_value" else "-"
    _query(context)
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error):
        family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)


def test_missing_selected_provenance_or_query_claim_binding_cannot_grant_permission():
    _catalog_value, context = _context()
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    context["selected_page_provenance"] = None
    _query(context)
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(candidate, **context)
    _catalog_value, context = _context()
    context["query_receipt"] = family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        context["regions"], selected_page_axis=context["selected_page_axis"],
        selected_page_provenance=context["selected_page_provenance"])
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="query receipt drifted"):
        family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    context["selected_page_axis"] = None
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="requires selected source axis"):
        _query(context)


def test_fresh_public_replay_rejects_self_resealed_unit_scope_proof():
    _catalog_value, context = _context()
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    adapter = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    receipt = adapter["original_source_unit_ownership_receipt"]
    receipt["checks"][0]["original_source_unit_proof"]["printed_unit_exact"] = "Triệu đồng"
    receipt["source_unit_ownership_receipt_id"] = "gjivpsuov1:receipt:" + canonical_json_sha256_v1({
        k: v for k, v in receipt.items() if k != "source_unit_ownership_receipt_id"})
    adapter["adapter_receipt_id"] = "gjivpfav1:receipt:" + canonical_json_sha256_v1({
        k: v for k, v in adapter.items() if k != "adapter_receipt_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({
        k: v for k, v in candidate.items() if k != "candidate_id"})
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(candidate, **context)


def test_new_registration_does_not_grant_undated_tpb227_or_other_source_permission():
    _entry, context, _expected = _fixture("tpb-doc227")
    context["compiled_specs"] = family.bind_gemini_json_issued_valuable_papers_page_unit_scopes_v1(
        context["compiled_specs"], _catalog())
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    _checked(candidate, context)
    catalog = _catalog()
    assert len(catalog["claims"]) == 1  # No VAB255 or other unit-HOLD registration.
    assert catalog["claims"][0]["locator"]["table_id"] == "t4"


def test_caller_resealed_catalog_cannot_approve_a_different_unit_or_source():
    catalog = _catalog()
    catalog["claims"][0]["canonical_unit"] = "MILLION_VND"
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="catalog drifted"):
        family.bind_gemini_json_issued_valuable_papers_page_unit_scopes_v1(_compiled(), catalog)


@pytest.mark.parametrize("scope", ["same_page_other_table", "next_page_continuation"])
def test_registered_page_target_never_donates_to_another_null_unit_scope(scope):
    _catalog_value, context = _context()
    target = context["regions"][0]
    page = context["page_json_by_version"][target["page_json_version_id"]]
    other = copy.deepcopy(target)
    if scope == "same_page_other_table":
        other["table_id"] = "t3"
        assert page["sections"][0]["tables"][2]["unit_exact"] is None
        target["fragment_ordinal"] = 2
        context["regions"] = [other, target]
    else:
        # Separate coherent synthetic continuation page. Original physical38,
        # including sender marker NONE, is unchanged; no original39 is claimed.
        following = copy.deepcopy(page)
        following["sections"][0]["tables"] = [copy.deepcopy(page["sections"][0]["tables"][3])]
        following["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
        payload = copy.deepcopy(context["selected_page_provenance"][0])
        payload.update(physical_page=39, canonical_json_sha256=sha256(canonical_json_bytes_v1(following) + b"\n").hexdigest(),
                       page_id="gfpstorev1:page:" + "a" * 64, extraction_run_id="gfpstorev1:run:" + "b" * 64)
        version = "gfpstorev1:json:" + canonical_json_sha256_v1({
            k: payload[k] for k in ("canonical_json_sha256", "extraction_run_id", "page_id")})
        payload["page_json_version_id"] = version
        selected = copy.deepcopy(context["selected_page_axis"][0])
        selected.update(page_json_version_id=version, physical_page=39, selected_page_ordinal=2)
        other.update(page_json_version_id=version, physical_page=39, selected_page_ordinal=2, table_id="t1", fragment_ordinal=2)
        context["page_json_by_version"][version] = following
        context["selected_page_axis"].append(selected)
        context["selected_page_provenance"].append(payload)
        context["regions"].append(other)
    _query(context)
    claims = family._registered_page_unit_claims_v1(pages=context["page_json_by_version"],
        regions=context["regions"], compiled_specs=context["compiled_specs"],
        selected_page_axis=context["selected_page_axis"], selected_page_provenance=context["selected_page_provenance"],
        authenticated_page_unit_claims=context["authenticated_page_unit_claims"])
    proofs = family._original_source_unit_proofs_v1(pages=context["page_json_by_version"],
        regions=context["regions"], compiled_specs=context["compiled_specs"], authenticated_page_unit_claims=claims)
    assert proofs[family._source_unit_scope_key_v1(target)]["source_kind"] == family.PAGE_UNIT_SOURCE_KIND
    assert family._source_unit_scope_key_v1(other) not in proofs
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    _checked(candidate, context)


@pytest.mark.parametrize("shape,expected_kind", [
    ("continuation", "EXPLICIT_RAW_CONTINUATION_OF_SOURCE_OWNED_UNIT"),
    ("numbered", "EXISTING_RAW_EXPLICIT_OWNER_NUMBERED_SUBSECTION"),
])
def test_private_unit_scope_twin_local_donor_inherits_but_page_only_kind_cannot(shape, expected_kind):
    from test_gemini_json_issued_valuable_papers_family_v1 import (
        _adjacent_generic_root_fixture,
        _family_compiled_without_repairs,
    )
    from test_gemini_json_issued_valuable_papers_original_source_units_v1 import _numbered_context

    if shape == "continuation":
        pages, regions = _adjacent_generic_root_fixture()
        compiled = _family_compiled_without_repairs()
    else:
        _page, context = _numbered_context()
        pages, regions, compiled = context["page_json_by_version"], context["regions"], context["compiled_specs"]
    positive = family._original_source_unit_proofs_v1(pages=pages, regions=regions, compiled_specs=compiled)
    sender, receiver = regions
    sender_key, receiver_key = map(family._source_unit_scope_key_v1, regions)
    assert positive[sender_key]["source_kind"] == "ORIGINAL_TABLE_OR_ALL_MONEY_COLUMN_UNIT"
    assert positive[receiver_key]["source_kind"] == expected_kind  # genuine permitting twin
    table = family._region_table(pages, sender)
    structural_before = copy.deepcopy(table)
    table["unit_exact"] = None
    assert {k: v for k, v in table.items() if k != "unit_exact"} == {
        k: v for k, v in structural_before.items() if k != "unit_exact"}
    # Deliberately UNREGISTERED synthetic private-boundary proof: it isolates
    # source_kind inheritance after the public boundary has validated claims.
    # It cannot enter the real public pinned catalog or approve any financial IO.
    registration = copy.deepcopy(_catalog()["claims"][0])
    registration["source"] = {**{k: sender[k] for k in ("document_id", "source_logical_name", "source_sha256")},
                              "source_size_bytes": 1}
    registration["locator"] = {k: sender[k] for k in ("page_json_version_id", "physical_page", "section_id", "table_id")}
    registration["canonical_unit"] = positive[sender_key]["canonical_unit"]
    registration["printed_unit_exact"] = structural_before["unit_exact"]
    registration["registration_id"] = "gjivppuv1:registration:" + canonical_json_sha256_v1({
        k: v for k, v in registration.items() if k != "registration_id"})
    synthetic = {**compiled, "issued_valuable_papers_page_unit_catalog": {"claims": [registration]}}
    claim = {"registration_id": registration["registration_id"], "unit_claim_id": "synthetic-private-unit-scope-only"}
    negative = family._original_source_unit_proofs_v1(pages=pages, regions=regions, compiled_specs=synthetic,
                                                     authenticated_page_unit_claims=[claim])
    assert negative[sender_key]["source_kind"] == family.PAGE_UNIT_SOURCE_KIND
    assert receiver_key not in negative
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="catalog drifted"):
        family.bind_gemini_json_issued_valuable_papers_page_unit_scopes_v1(compiled,
            synthetic["issued_valuable_papers_page_unit_catalog"])


def test_valid_foreign_global_claim_does_not_change_other_document_ready_bytes():
    from test_gemini_json_issued_valuable_papers_current_four_metric_v1 import _context as four_metric_context

    baseline, context = four_metric_context()
    assert baseline["status"] == READY
    catalog, foreign = _context()
    selected = copy.deepcopy(foreign["selected_page_axis"][0])
    selected["document_ordinal"] = 2
    payload = foreign["selected_page_provenance"][0]
    claim = family.build_gemini_json_issued_valuable_papers_page_unit_claim_v1(catalog["claims"][0], selected, payload)
    context["compiled_specs"] = family.bind_gemini_json_issued_valuable_papers_page_unit_scopes_v1(
        context["compiled_specs"], catalog)
    baseline = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert baseline["status"] == READY
    context["selected_page_axis"].append(selected)
    context["selected_page_provenance"].append(payload)
    context["authenticated_page_unit_claims"] = [claim]
    _query(context)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert canonical_json_bytes_v1(candidate) == canonical_json_bytes_v1(baseline)
    _checked(candidate, context)
