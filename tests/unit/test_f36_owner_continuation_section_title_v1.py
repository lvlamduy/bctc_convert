"""INACTIVE proposed tests; no source/PDF/corpus or measured-gain claim.

Materialize only in a root-reviewed isolated checkout with the separate owner
section-title patch and an explicit runtime lease. Reuse existing real public
F36 query/trial/replay APIs and synthetic fixtures; do not mock their decisions.
V3 retains all31 prior cases and adds actual F36-compiler literal-alias and
shared-only-spec regressions. The actual multitable compiler normalizes parent
aliases and has no query_parent_aliases key; that other compiler's interface
must never be assumed here. The new F36-local literal snapshot grants only the
finite title match, never source/PDF/financial authority.
V2 rejects EVERY non-None unparsed prior owner title. The common public fixture
therefore has an exact owned prior section, as actual149 does. Control/new runs
still differ only in the receiver section title. The original generic fixture
has its own unchanged-route compatibility test. All tests remain unexecuted.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from unicodedata import normalize

import pytest

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1


_ROOT = Path(family.__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "_f36_owner_title_existing_fixtures",
    _ROOT / "tests/unit/test_gemini_json_operating_expense_family_v1.py",
)
assert _SPEC is not None and _SPEC.loader is not None
fixture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture)
TITLE = "28. Chi phí hoạt động (tiếp theo)"
FIELD = "receiver_owner_continuation_section_title_receipt"


def _owned_fixture():
    base, pages, compiled = fixture._continuation_query_fixture()
    prior, _receiver = _sections(pages)
    prior["title_exact"] = "28. Chi phí hoạt động"
    return base, pages, compiled


def _snapshot(pages, compiled):
    return canonical_json_bytes_v1([
        [{"document_ordinal": ordinal, "pages": pages[ordinal]} for ordinal in sorted(pages)],
        compiled,
    ])


def _run(pages, compiled):
    base = fixture._rebuild_continuation_query_fixture(pages, compiled)
    adapted = family.build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base, page_json_by_document=pages, compiled_specs=compiled,
    )
    trial = family.build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted, page_json_by_document=pages, compiled_specs=compiled,
    )[0]
    return adapted, trial


def _sections(pages):
    prior = pages[1][fixture.VERSION_ID]["sections"][0]
    receiver = pages[1][fixture.CONTINUATION_VERSION_ID]["sections"][0]
    return prior, receiver


def _title_evidence(pages, compiled):
    prior, receiver = _sections(pages)
    return family._receiver_owner_continuation_section_title(
        prior_section=prior, prior_table=prior["tables"][0],
        receiver_section=receiver, receiver_table=receiver["tables"][0],
        compiled_specs=compiled,
    )


def test_only_receiver_section_title_changes_public_continuation_and_replays():
    _base, pages, compiled = _owned_fixture()
    control_pages = copy.deepcopy(pages)
    _control_indexed, control = _run(control_pages, compiled)
    assert control["status"] == READY
    old_adapter = control["candidates"][0]["closure_receipt"]["operating_expense_adapter_receipt"]
    assert all(FIELD not in item for item in old_adapter["continuation_projection_receipts"])
    _prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE  # The sole source change from the valid fixture.
    before = _snapshot(pages, compiled)
    indexed, trial = _run(pages, compiled)
    assert trial["status"] == READY and trial["mappings"] == control["mappings"]
    candidate = trial["candidates"][0]
    receipt = candidate["closure_receipt"]["operating_expense_adapter_receipt"]["continuation_projection_receipts"][0]
    evidence = receipt[FIELD]
    assert evidence["receiver_section_title_exact"] == TITLE
    assert evidence["receiver_section_title_canonical_json_sha256"] == canonical_json_sha256_v1(TITLE)
    assert evidence["configured_owner_alias_exact"] == fixture.OWNER
    assert evidence["printed_note_ordinal_exact"] == "28"
    assert evidence["continuation_marker_normalized"] == "(tiếp theo)"
    root = next(item for item in trial["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [80, 64]
    assert [(ref["locator"]["physical_page"], ref["row_ordinal"]) for ref in root["source_refs"]] == [(2, 5)]
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    replayed = family.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed, trials=[trial],
        page_json_by_document=pages, compiled_specs=compiled,
    )
    assert canonical_json_bytes_v1(replayed) == canonical_json_bytes_v1([trial])
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("title", [
    "Chi phí hoạt động (tiếp theo)",
    "28. CHI PHÍ HOẠT ĐỘNG (TIẾP THEO)",
    normalize("NFD", TITLE),
])
def test_finite_owner_title_layout_retains_full_raw_source(title):
    _base, pages, compiled = _owned_fixture()
    _prior, receiver = _sections(pages)
    receiver["title_exact"] = title
    before = _snapshot(pages, compiled)
    evidence = _title_evidence(pages, compiled)
    assert evidence is not None and evidence["receiver_section_title_exact"] == title
    assert evidence["receiver_section_title_canonical_json_sha256"] == canonical_json_sha256_v1(title)
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("title", [
    "28. Thuế thu nhập doanh nghiệp (tiếp theo)",
    "28. Chi phí hoạt động",  # No printed continuation marker.
    "28. Chi phí hoạt động tiếp theo",  # Parentheses are part of the finite grammar.
    "28. Chi phí hoạt động (tiếp theo); số liệu riêng của công ty con",
    "28. Chi phí hoạt động (tiếp theo) / 29. Chi phí hoạt động",
    "Ngân hàng ABC: 28. Chi phí hoạt động (tiếp theo)",
    "0. Chi phí hoạt động (tiếp theo)",
    "28\u0301. Chi phí hoạt động (tiếp theo)",
    "28. Chi phí hoạt động\x0b(tiếp theo)",
])
def test_other_owners_assertions_missing_marker_and_raw_faults_are_not_evidence(title):
    _base, pages, compiled = _owned_fixture()
    _prior, receiver = _sections(pages)
    receiver["title_exact"] = title
    before = _snapshot(pages, compiled)
    assert _title_evidence(pages, compiled) is None
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("attack", ["prior_ordinal", "table_owner", "table_ordinal", "wrong_kind"])
def test_conflicting_owned_title_surfaces_never_establish_continuation(attack):
    _base, pages, compiled = _owned_fixture()
    prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE
    if attack == "prior_ordinal":
        prior["tables"][0]["title_exact"] = "27. Chi phí hoạt động"
    elif attack == "table_owner":
        receiver["tables"][0]["title_exact"] = "28. Chi phí quản lý chung (tiếp theo)"
    elif attack == "table_ordinal":
        receiver["tables"][0]["title_exact"] = "29. Chi phí hoạt động (tiếp theo)"
    else:
        receiver["content_kind"] = "PRIMARY_STATEMENT"
    before = _snapshot(pages, compiled)
    assert _title_evidence(pages, compiled) is None
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("attack", ["other_family", "extra_assertion", "missing_marker", "competing_owner"])
def test_public_unrecognized_or_competing_owner_heading_cannot_close_sender(attack):
    _base, pages, compiled = _owned_fixture()
    _prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE
    if attack == "other_family":
        receiver["title_exact"] = "28. Thuế thu nhập doanh nghiệp (tiếp theo)"
    elif attack == "extra_assertion":
        receiver["title_exact"] = TITLE + "; số liệu riêng của công ty con"
    elif attack == "missing_marker":
        receiver["title_exact"] = "28. Chi phí hoạt động"
    else:
        receiver["tables"][0]["title_exact"] = "28. Chi phí quản lý chung (tiếp theo)"
    before = _snapshot(pages, compiled)
    _indexed, trial = _run(pages, compiled)
    assert trial["status"] == UNRESOLVED and trial["mappings"] == []
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("attack", ["unit", "period", "outgoing_receiver", "missing_receiver_marker"])
def test_public_owner_title_does_not_override_existing_unit_period_or_marker_veto(attack):
    _base, pages, compiled = _owned_fixture()
    prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE
    if attack == "unit":
        receiver["tables"][0]["unit_exact"] = "VND"
    elif attack == "period":
        receiver["tables"][0]["columns"][0]["header_path_exact"] = ["Quý II năm 2024"]
        receiver["tables"][0]["columns"][1]["header_path_exact"] = ["Quý II năm 2023"]
    elif attack == "outgoing_receiver":
        receiver["tables"][0]["continuation"] = "BOTH"
    else:
        receiver["tables"][0]["continuation"] = "NONE"
    before = _snapshot(pages, compiled)
    _indexed, trial = _run(pages, compiled)
    assert trial["status"] == UNRESOLVED and trial["mappings"] == []
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("attack", ["drop", "change_title"])
def test_resealed_new_title_receipt_still_requires_fresh_candidate_replay(attack):
    _base, pages, compiled = _owned_fixture()
    _prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE
    indexed, trial = _run(pages, compiled)
    assert trial["status"] == READY
    forged = copy.deepcopy(trial["candidates"][0])
    adapter = forged["closure_receipt"]["operating_expense_adapter_receipt"]
    receipt = adapter["continuation_projection_receipts"][0]
    if attack == "drop":
        receipt.pop(FIELD)
    else:
        receipt[FIELD]["receiver_section_title_exact"] = "29. Chi phí hoạt động (tiếp theo)"
    body = {key: value for key, value in receipt.items() if key != "receipt_id"}
    receipt["receipt_id"] = "gjoefav1:continuation-projection:" + canonical_json_sha256_v1(body)
    body = {key: value for key, value in adapter.items() if key != "adapter_receipt_id"}
    adapter["adapter_receipt_id"] = "gjoefav1:receipt:" + canonical_json_sha256_v1(body)
    body = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(body)
    regions = indexed["candidate_dispositions"][0]["cluster"]["component_regions"]
    query = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    with pytest.raises(family.GeminiJsonOperatingExpenseFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_operating_expense_candidate_replay_v1(
            forged, regions=regions, page_json_by_version=pages[1],
            selected_page_axis=indexed["selected_page_axis"],
            compiled_specs=compiled, query_receipt=query,
        )



def test_original_generic_prior_and_receiver_route_has_no_new_title_receipt():
    _base, pages, compiled = fixture._continuation_query_fixture()
    before = _snapshot(pages, compiled)
    _indexed, trial = _run(pages, compiled)
    assert trial["status"] == READY
    adapter = trial["candidates"][0]["closure_receipt"]["operating_expense_adapter_receipt"]
    assert adapter["continuation_projection_receipts"]
    assert all(FIELD not in item for item in adapter["continuation_projection_receipts"])
    assert _snapshot(pages, compiled) == before


@pytest.mark.parametrize("attack", ["prior_section_other_family", "prior_section_extra_scope", "prior_table_unrecognized"])
def test_any_unparsed_prior_title_is_retained_as_a_veto_not_silently_ignored(attack):
    _base, pages, compiled = _owned_fixture()
    prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE
    if attack == "prior_section_other_family":
        prior["title_exact"] = "29. Thuế thu nhập doanh nghiệp"
    elif attack == "prior_section_extra_scope":
        prior["title_exact"] = "28. Chi phí hoạt động; số liệu riêng của công ty con"
    else:
        prior["tables"][0]["title_exact"] = "Chi phí hoạt động; phạm vi khác"
    before = _snapshot(pages, compiled)
    assert _title_evidence(pages, compiled) is None
    _indexed, trial = _run(pages, compiled)
    assert trial["status"] != READY and trial["mappings"] == []
    assert _snapshot(pages, compiled) == before



def test_actual_f36_compiler_preserves_literal_aliases_and_all_raw_shape_gates():
    topology = fixture._json("tm-operating-expense-topology-v1.json")
    evaluation = fixture._json("tm-operating-expense-evaluation-v1.json")
    schema = fixture._json("tm-operating-expense-schema-binding-v1.json")
    before = canonical_json_bytes_v1(topology)
    compiled = family.compile_gemini_json_operating_expense_family_specs_v1(topology, evaluation, schema)
    literal = compiled["operating_expense_owner_title_aliases_exact"]
    assert literal == topology["parent"]["aliases"]
    assert literal != compiled["topology"]["parent"]["aliases"]
    assert "Chi phí hoạt động" in literal
    assert canonical_json_bytes_v1(topology) == before
    expected = copy.deepcopy(literal)
    topology["parent"]["aliases"].append("tampered caller input")
    assert compiled["operating_expense_owner_title_aliases_exact"] == expected
    # Invalid raw source shapes still go through the real compiler; no
    # caller-supplied literal field or success boolean substitutes for it.
    for attack in ("missing_parent", "parent_none", "empty_aliases", "tuple_aliases"):
        malformed = fixture._json("tm-operating-expense-topology-v1.json")
        if attack == "missing_parent":
            malformed.pop("parent")
        elif attack == "parent_none":
            malformed["parent"] = None
        elif attack == "empty_aliases":
            malformed["parent"]["aliases"] = []
        else:
            malformed["parent"]["aliases"] = tuple(malformed["parent"]["aliases"])
        with pytest.raises(family.GeminiJsonOperatingExpenseFamilyV1Error, match="declarative family specs are invalid"):
            family.compile_gemini_json_operating_expense_family_specs_v1(malformed, evaluation, schema)



def test_shared_only_compiled_specs_cannot_manufacture_literal_title_authority():
    _base, pages, _adapter_specs = _owned_fixture()
    shared_specs = fixture._compiled()  # Actual shared compiler, no injected key.
    assert "operating_expense_owner_title_aliases_exact" not in shared_specs
    _prior, receiver = _sections(pages)
    receiver["title_exact"] = TITLE
    before = _snapshot(pages, shared_specs)
    assert _title_evidence(pages, shared_specs) is None  # No KeyError and no fallback grant.
    _indexed, trial = _run(pages, shared_specs)
    assert trial["status"] == UNRESOLVED and trial["mappings"] == []
    assert _snapshot(pages, shared_specs) == before


def test_new_owner_title_preserves_existing_one_sided_sender_none_contract():
    """Prior NONE is an old supported case, not a missing-receiver veto.

    Frozen baseline tests ONE_SIDED_PRIOR_MARKER and the Roman-quarter matrix
    already require this complete-owner behavior. A new whole owner title must
    retain it, while receiver FROM_PREVIOUS and every independent proof remain
    mandatory. The retained 719PASS/1FAIL witness exposed the bad V3 expectation;
    production is unchanged by this test correction.
    """
    _base, pages, compiled = _owned_fixture()
    prior, receiver = _sections(pages)
    prior["tables"][0]["continuation"] = "NONE"
    receiver["title_exact"] = TITLE
    assert receiver["tables"][0]["continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE"
    before = _snapshot(pages, compiled)
    indexed, trial = _run(pages, compiled)
    assert trial["status"] == READY
    candidate = trial["candidates"][0]
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    assert adapter["source_root_authority_veto_receipts"] == []
    assert len(adapter["continuation_projection_receipts"]) == 1
    proof = adapter["continuation_projection_receipts"][0]
    assert proof["prior_marker"] == "NONE"
    assert proof["prior_locator"]["page_json_version_id"] == fixture.VERSION_ID
    assert proof["receiver_locator"]["page_json_version_id"] == fixture.CONTINUATION_VERSION_ID
    assert proof["receiver_header_axis_rule"] == "INHERITED_ONLY_FROM_COMPLETE_PRIOR_AXIS"
    assert proof["period_alignment_receipt"]["compatible"] is True
    assert proof["prior_unit"]["canonical_unit"] == proof["receiver_unit"]["canonical_unit"] == "MILLION_VND"
    assert proof[FIELD]["receiver_section_title_exact"] == TITLE
    assert proof[FIELD]["receiver_section_title_canonical_json_sha256"] == canonical_json_sha256_v1(TITLE)
    root = next(item for item in trial["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["source_text"] for cell in root["values"]] == ["80", "64"]
    assert [(ref["locator"]["physical_page"], ref["row_ordinal"]) for ref in root["source_refs"]] == [(2, 5)]
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    rebuilt = family.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed, trials=[trial],
        page_json_by_document=pages, compiled_specs=compiled,
    )
    assert canonical_json_bytes_v1(rebuilt) == canonical_json_bytes_v1([trial])
    assert _snapshot(pages, compiled) == before
