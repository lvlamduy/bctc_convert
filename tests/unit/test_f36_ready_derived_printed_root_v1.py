"""INACTIVE, unexecuted tests for the external READY-derived root proposal.

Run only in a root-reviewed isolated checkout after applying that proposal and
obtaining the runtime lease. No source DB/PDF/corpus fixtures or producer mocks.
V1 actual root smoke retained 15PASS/5FAIL, including the two positive source
cases: trace b84aace96c4e5bcbb8b40ed2bb80fbdc223e4d096977b35fedbb99e05e6f4574
isolated exact duplicated record refs versus unique pre-retry refs. V2 uses only
the existing exact-typed deduper on private comparison copies; no source guard
or positive precondition is relaxed. These V2 tests remain unexecuted.
The positive explicitly requires the frozen shared engine to be READY-derived
on the SAME source/specs; a failed precondition is a failing draft, not a reason
to fabricate that state. Actual corpus applicability remains NOT_INSPECTED.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(family.__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "_f36_ready_root_existing_fixtures",
    _ROOT / "tests/unit/test_gemini_json_operating_expense_family_v1.py",
)
assert _SPEC is not None and _SPEC.loader is not None
fixture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture)
DERIVED = "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
PRINTED = "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_OPERATING_EXPENSE_DIRECT_FRONTIER"


def _page(label=None):
    # Three numbered peers followed by one unnumbered peer. The frozen
    # numbered-frontier selector can miss the fourth peer for its local total;
    # the new route must prove the complete declared direct source frontier.
    return fixture._operating_page([
        fixture._row("1. Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        fixture._row("2. Chi phí cho nhân viên", "30", "25"),
        fixture._row("3. Chi về tài sản", "20", "15"),
        fixture._row("Chi nộp phí bảo hiểm tiền gửi của khách hàng", "5", "4"),
        fixture._row(label, "65", "52", kind="TOTAL", path=[label]),
    ])


def _inputs(page, compiled=None):
    if compiled is None:
        compiled = fixture._adapter_compiled()
    pages = {fixture.VERSION_ID: page}
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[fixture._record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    query = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    private_specs, _guards, _parents = family._mapping_max_private_specs(
        pages=pages, regions=regions, compiled_specs=compiled
    )
    shared = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions, page_json_by_version=pages,
        compiled_specs=private_specs, query_receipt=query,
    )
    return pages, regions, query, compiled, private_specs, shared


def _public(pages, regions, query, compiled):
    return family.evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=regions, page_json_by_version=pages, selected_page_axis=[],
        compiled_specs=compiled, query_receipt=query,
    )


def _root(candidate):
    roots = [item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"]
    assert len(roots) == 1
    return roots[0]


def _assert_seed(shared):
    assert shared["status"] == READY and shared["reasons"] == []
    assert _root(shared)["state"] == DERIVED
    assert all(item["source_text"] is None for item in _root(shared)["values"])


@pytest.mark.parametrize("label", [None, "Tổng"])
def test_same_source_shared_ready_derived_becomes_fresh_printed_root_and_replays(label):
    page = _page(label)
    pages, regions, query, compiled, private_specs, shared = _inputs(page)
    _assert_seed(shared)  # Never mock or rewrite the producer's status/state.
    before = canonical_json_bytes_v1([pages, compiled, private_specs, shared])
    actual = _public(pages, regions, query, compiled)
    assert actual["status"] == READY and actual["reasons"] == []
    root = _root(actual)
    assert root["state"] == PRINTED
    assert [item for item in actual["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"] == [
        item for item in shared["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"
    ]
    assert root["row_id"] == "r5"
    assert len(root["source_refs"]) == 1
    assert root["source_refs"][0]["row_ordinal"] == 5
    assert root["source_refs"][0]["label_exact"] == label
    assert [cell["source_text"] for cell in root["values"]] == ["65", "52"]
    assert [cell["coefficient"] for cell in root["values"]] == [65, 52]
    adapter = actual["closure_receipt"]["operating_expense_adapter_receipt"]
    assert adapter["source_root_authority_veto_receipts"] == []
    proof = adapter["root_closure_receipts"][0]
    prior = proof["prior_ready_derived_root"]
    assert prior["original_status"] == READY and prior["original_reasons"] == []
    assert prior["superseded_root_mapping"] == _root(shared)
    assert prior["equation_authority"] == "FRESH_TABLE_LOCAL_SOURCE_EXTRACTION"
    comparison = prior["nonroot_comparison"]
    assert comparison["prior_deduplication_receipts"] == []
    rebuilt_dedup = comparison["reconstructed_deduplication_receipts"]
    assert len(rebuilt_dedup) == 4
    assert all(item["before_source_ref_count"] == 2 and item["after_source_ref_count"] == 1 for item in rebuilt_dedup)
    assert [item for item in adapter["source_ref_deduplication_receipts"] if item["role"] != "FAMILY_ROOT_TOTAL"] == rebuilt_dedup
    assert proof["original_reasons"] == []
    assert proof["equation"]["status"] == "EXACT"
    for row in actual["closure_receipt"]["source_only_unmapped_rows"]:
        if family._source_ref_key(row.get("source_ref", {})) == family._source_ref_key(root["source_refs"][0]):
            assert row["consumed_by_exact_equation"] is True
    assert validate_source_observation_mapping_contract_v1(actual)["violation_count"] == 0
    replayed = family.validate_gemini_json_operating_expense_candidate_replay_v1(
        actual, regions=regions, page_json_by_version=pages, selected_page_axis=[],
        compiled_specs=compiled, query_receipt=query,
    )
    assert canonical_json_bytes_v1(replayed) == canonical_json_bytes_v1(actual)
    assert canonical_json_bytes_v1([pages, compiled, private_specs, shared]) == before


@pytest.mark.parametrize("attack", [
    "missing_total", "duplicate_total", "nonterminal_total", "blank_total", "mismatch",
    "period", "unit", "outgoing", "both",
])
def test_public_missing_invalid_or_open_source_never_gains_printed_root(attack):
    page = _page()
    table = page["sections"][0]["tables"][0]
    if attack == "missing_total":
        table["rows"].pop()
    elif attack == "duplicate_total":
        table["rows"].append(copy.deepcopy(table["rows"][-1]))
    elif attack == "nonterminal_total":
        table["rows"].append(fixture._row("Note text", None, None))
    elif attack == "blank_total":
        table["rows"][-1]["values_exact"] = [None, None]
    elif attack == "mismatch":
        table["rows"][-1]["values_exact"] = ["80", "90"]
    elif attack == "period":
        table["columns"][0]["header_path_exact"] = ["Kỳ không xác định"]
    elif attack == "unit":
        table["unit_exact"] = "USD"
    else:
        table["continuation"] = "BOTH" if attack == "both" else "CONTINUES_ON_NEXT_PAGE"
    pages, regions, query, compiled, _private, _shared = _inputs(page)
    before = canonical_json_bytes_v1([pages, compiled])
    actual = _public(pages, regions, query, compiled)
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    if attack in {"outgoing", "both"}:
        assert "OPERATING_EXPENSE_SOURCE_CONTINUATION_NOT_CLOSED" in actual["reasons"]
    assert canonical_json_bytes_v1([pages, compiled]) == before


@pytest.mark.parametrize("attack", ["optional", "reasons", "nonroot_change", "nonroot_drop", "distinct_ref", "alias_collision", "wrong_owner"])
def test_narrow_retry_failure_preserves_candidate_and_never_grants_other_authority(attack):
    pages, regions, _query, _compiled, private_specs, shared = _inputs(_page())
    _assert_seed(shared)
    if attack == "optional":
        private_specs["family_root_requirement"] = "OPTIONAL"
    elif attack == "reasons":
        shared["reasons"] = ["SOME_OTHER_UNRESOLVED_AUTHORITY"]
    elif attack == "nonroot_change":
        next(item for item in shared["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL")["unit"] = "VND"
    elif attack == "nonroot_drop":
        shared["mappings"] = [item for item in shared["mappings"] if item["role"] != "TAX_FEES"]
    elif attack == "distinct_ref":
        mapping = next(item for item in shared["mappings"] if item["role"] == "TAX_FEES")
        distinct = copy.deepcopy(mapping["source_refs"][0])
        distinct["row_ordinal"] += 1
        distinct["row_id"] = "r2"
        mapping["source_refs"].append(distinct)
        mapping["row_id"] = "corroborated:" + mapping["role"]
        body = {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(body)
        body = {key: value for key, value in shared.items() if key != "candidate_id"}
        shared["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(body)
    elif attack == "alias_collision":
        rows = pages[fixture.VERSION_ID]["sections"][0]["tables"][0]["rows"]
        rows.insert(-1, fixture._row("Chi phí quản lý chung", "-", "-"))
    else:
        pages[fixture.VERSION_ID]["sections"][0]["title_exact"] = "Thông tin khác"
    before = canonical_json_bytes_v1([pages, private_specs, shared])
    assert family._operating_expense_root_closure_retry(
        candidate=shared, pages=pages, regions=regions, compiled_specs=private_specs
    ) == (None, [], [])
    assert canonical_json_bytes_v1([pages, private_specs, shared]) == before


@pytest.mark.parametrize("attack", ["drop_receipt", "prior_mapping", "equation"])
def test_resealed_promotion_receipt_cannot_replace_fresh_public_replay(attack):
    pages, regions, query, compiled, _private, shared = _inputs(_page())
    _assert_seed(shared)
    actual = _public(pages, regions, query, compiled)
    assert actual["status"] == READY
    forged = copy.deepcopy(actual)
    adapter = forged["closure_receipt"]["operating_expense_adapter_receipt"]
    if attack == "drop_receipt":
        adapter["root_closure_receipts"] = []
    else:
        receipt = adapter["root_closure_receipts"][0]
        if attack == "prior_mapping":
            receipt["prior_ready_derived_root"]["superseded_root_mapping"]["values"][0]["coefficient"] = 999
        else:
            receipt["equation"]["component_sums"][0] = 999
        body = {key: value for key, value in receipt.items() if key != "receipt_id"}
        receipt["receipt_id"] = "gjoefav1:root-closure:" + canonical_json_sha256_v1(body)
    body = {key: value for key, value in adapter.items() if key != "adapter_receipt_id"}
    adapter["adapter_receipt_id"] = "gjoefav1:receipt:" + canonical_json_sha256_v1(body)
    body = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(body)
    with pytest.raises(family.GeminiJsonOperatingExpenseFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_operating_expense_candidate_replay_v1(
            forged, regions=regions, page_json_by_version=pages, selected_page_axis=[],
            compiled_specs=compiled, query_receipt=query,
        )
