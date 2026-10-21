from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _adapter_compiled_with_fixture_row_repair,
    _canonical_rows,
    _evaluate_supplemental_records,
    _honest_income_recognition_repair_records,
    _json,
    _page,
    _primary_page,
    _primary_record,
    _primary_tax_rows,
    _record,
    _row,
    _supplemental_records,
)

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    build_gemini_json_income_tax_region_query_receipt_v1,
    compile_gemini_json_income_tax_family_specs_v1,
    evaluate_gemini_json_income_tax_family_cluster_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _fixture(strategy: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    compiled = _adapter_compiled()
    if strategy == "note":
        records = [_record(_page(_canonical_rows()))]
    else:
        records = [_primary_record(_primary_page(_primary_tax_rows()))]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    query = build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    assert (query["adapter_receipt"] is None) == (strategy == "note")
    return compiled, cluster, query, records


def _evaluate(compiled: dict[str, Any], cluster: dict[str, Any], query: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        selected_page_axis=[{key: value for key, value in item.items() if key != "page_json"} for item in records],
        compiled_specs=compiled,
        query_receipt=query,
    )


def _reseal(query: dict[str, Any]) -> None:
    context = query["source_context_receipt"]
    context["receipt_id"] = "gjitfav1:source-context:" + canonical_json_sha256_v1(
        {key: value for key, value in context.items() if key != "receipt_id"}
    )
    query["query_receipt_id"] = "gjitfav1:query-receipt:" + canonical_json_sha256_v1(
        {key: value for key, value in query.items() if key != "query_receipt_id"}
    )


@pytest.mark.parametrize("strategy", ["note", "primary"])
def test_empty_repair_axis_binds_source_context_even_without_adapter(strategy: str) -> None:
    compiled, cluster, query, records = _fixture(strategy)
    context = query["source_context_receipt"]
    assert context["repair_receipt_ids"] == []
    assert context["source_repair_spec_sha256"] == compiled["income_tax_source_repair_spec_sha256"]
    assert context["adapter_spec_sha256"] == compiled["income_tax_adapter_spec_sha256"]
    candidate = _evaluate(compiled, cluster, query, records)
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["income_tax_source_control_receipt"]["source_context_receipt"] == context


@pytest.mark.parametrize("strategy", ["note", "primary"])
def test_real_unused_repair_spec_change_rejects_existing_query(strategy: str) -> None:
    compiled, cluster, query, records = _fixture(strategy)
    unused_repair = deepcopy(_adapter_compiled_with_fixture_row_repair()["income_tax_source_repairs"][0])
    unused_repair["pdf_source"]["sha256"] = "e" * 64
    unused_repair["repair_id"] = "gjitfav1:repair:" + canonical_json_sha256_v1(
        {key: value for key, value in unused_repair.items() if key != "repair_id"}
    )
    spec = _json("tm-income-tax-source-repair-v1.json")
    spec["repairs"] = [unused_repair]
    changed = compile_gemini_json_income_tax_family_specs_v1(
        _json("tm-income-tax-topology-v1.json"),
        _json("tm-income-tax-evaluation-v1.json"),
        _json("tm-income-tax-schema-binding-v1.json"),
        source_repair_spec=spec,
    )
    assert changed["income_tax_source_repair_spec_sha256"] != compiled["income_tax_source_repair_spec_sha256"]
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="source context query replay drifted"):
        _evaluate(changed, cluster, query, records)
    new_base = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=changed)
    new_cluster = recover_gemini_json_income_tax_query_cluster_v1(page_records=records, base_cluster=new_base, compiled_specs=changed)
    new_query = build_gemini_json_income_tax_region_query_receipt_v1(new_cluster["component_regions"], cluster=new_cluster)
    assert new_query["source_context_receipt"]["repair_receipt_ids"] == []
    assert _evaluate(changed, new_cluster, new_query, records)["status"] == READY


@pytest.mark.parametrize("strategy", ["note", "primary"])
@pytest.mark.parametrize("mutation", ["repair_spec", "adapter_spec", "repair_ids", "control_axis", "rule", "typed_empty"])
def test_self_resealed_source_context_tamper_is_rejected(strategy: str, mutation: str) -> None:
    compiled, cluster, query, records = _fixture(strategy)
    tampered = deepcopy(query)
    context = tampered["source_context_receipt"]
    if mutation == "repair_spec":
        context["source_repair_spec_sha256"] = "0" * 64
    elif mutation == "adapter_spec":
        context["adapter_spec_sha256"] = "0" * 64
    elif mutation == "repair_ids":
        context["repair_receipt_ids"] = ["gjitfav1:repair:" + "0" * 64]
    elif mutation == "control_axis":
        context["supplemental_root_controls"] = [{"control_id": "forged"}]
    elif mutation == "rule":
        context["rule"] = "CHANGED"
    else:
        context["repair_receipt_ids"] = {}
    _reseal(tampered)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="source context query replay drifted"):
        _evaluate(compiled, cluster, tampered, records)


@pytest.mark.parametrize("strategy", ["note", "primary"])
def test_unbound_query_cannot_be_created_from_base_cluster(strategy: str) -> None:
    _compiled, cluster, _query, _records = _fixture(strategy)
    unbound = deepcopy(cluster)
    unbound["owner_receipt"].pop("income_tax_source_context_receipt")
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="source context receipt is absent"):
        build_gemini_json_income_tax_region_query_receipt_v1(unbound["component_regions"], cluster=unbound)


@pytest.mark.parametrize("mutation", ["reverse", "truncate", "duplicate"])
def test_actual_nonempty_repair_receipt_order_cannot_be_resealed(mutation: str) -> None:
    first = deepcopy(_adapter_compiled_with_fixture_row_repair()["income_tax_source_repairs"][0])
    second = deepcopy(first)
    second.update({"repair_kind": "MONEY_CELL_PDF_VISIBLE_DASH", "before_exact": None,
                   "after_exact": "-", "column_ordinal": 1})
    second["locator"]["row_ordinal"] = 7
    second["repair_id"] = "gjitfav1:repair:" + canonical_json_sha256_v1(
        {key: value for key, value in second.items() if key != "repair_id"}
    )
    spec = _json("tm-income-tax-source-repair-v1.json")
    spec["repairs"] = [first, second]
    compiled = compile_gemini_json_income_tax_family_specs_v1(
        _json("tm-income-tax-topology-v1.json"), _json("tm-income-tax-evaluation-v1.json"),
        _json("tm-income-tax-schema-binding-v1.json"), source_repair_spec=spec,
    )
    records = _honest_income_recognition_repair_records(deferred_current=None)
    original = deepcopy(records)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    cluster = recover_gemini_json_income_tax_query_cluster_v1(page_records=records, base_cluster=base, compiled_specs=compiled)
    assert cluster["status"] == READY
    query = build_gemini_json_income_tax_region_query_receipt_v1(cluster["component_regions"], cluster=cluster)
    ids = query["source_context_receipt"]["repair_receipt_ids"]
    assert len(ids) == 2 and ids[0] != ids[1]
    candidate = _evaluate(compiled, cluster, query, records)
    assert candidate["status"] == READY
    inventory = query["source_context_receipt"]["tax_population_inventory"][0]
    assert inventory["source_table_rows_exact"][4]["row_kind"] == "GROUP"
    assert inventory["source_table_rows_exact"][5]["values_exact"] == ["20", "15"]
    assert inventory["source_table_rows_exact"][6]["values_exact"] == ["-", "-"]
    assert inventory["recognition_expense_frontier"]["status"] == "PASS"
    tampered = deepcopy(query)
    tampered["source_context_receipt"]["repair_receipt_ids"] = (
        list(reversed(ids)) if mutation == "reverse" else ids[:1] if mutation == "truncate" else [ids[0], ids[0]]
    )
    _reseal(tampered)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="source context query replay drifted"):
        _evaluate(compiled, cluster, tampered, records)
    assert records == original


@pytest.mark.parametrize("root", [("12", "9"), ("99", "99"), ("(12)", "9")])
def test_root_presentation_orientation_requires_same_table_independent_source_roles(root: tuple[str, str]) -> None:
    records, _, _ = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"),
            _row("Chi phí thuế TNDN", *root, kind="TOTAL"),
        ],
        primary_current=("(10)", "(8)"), primary_deferred=("(2)", "(1)"),
        primary_root=("(12)", "(9)"),
    )
    originals = deepcopy(records)
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert records == originals
    if root != ("12", "9"):
        assert candidate["status"] != READY
        assert candidate["mappings"] == []
        return
    assert candidate["status"] == READY
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == [-12, -9]
    assert [cell["source_text"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == ["(12)", "(9)"]
    receipt = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    comparison = receipt["supplemental_root_lane_receipts"][0]
    assert comparison["presentation_orientation_receipt"]["orientation"] == -1
    assert comparison["presentation_orientation_receipt"]["matched_same_source_table_proofs"]
    assert {lane["status"] for lane in comparison["lanes"]} == {
        "EXACT_AUTHENTICATED_OPPOSITE_SIGN_PRESENTATION_CONTROL"
    }
    assert receipt["source_context_receipt"]["supplemental_root_controls"][0]["root_source_row"]["coefficients"] == [12, 9]


def test_root_only_opposite_sign_cannot_establish_its_own_orientation() -> None:
    records, _, _ = _supplemental_records(
        [_row("Chi phí thuế TNDN", "12", "9", kind="TOTAL")],
        primary_current=("(10)", "(8)"), primary_deferred=("(2)", "(1)"),
        primary_root=("(12)", "(9)"),
    )
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] != READY
    evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    comparison = evidence["supplemental_root_lane_receipts"][0]
    assert comparison["presentation_orientation_receipt"]["orientation"] == 1
    assert comparison["presentation_orientation_receipt"]["matched_same_source_table_proofs"] == []


def test_root_control_cannot_borrow_opposite_sign_proof_from_a_different_table() -> None:
    records, _, _ = _supplemental_records(
        [_row("Ngân hàng", "7", "5"),
         _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
         _row("Cộng", "10", "8", kind="TOTAL")],
        primary_current=("(10)", "(8)"), primary_deferred=("(2)", "(1)"),
        primary_root=("(12)", "(9)"),
    )
    other_table = _page([_row("Chi phí thuế TNDN", "12", "9", kind="TOTAL")])["sections"][0]["tables"][0]
    records[0]["page_json"]["sections"][0]["tables"].append(other_table)
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] != READY
    evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    comparison = evidence["supplemental_root_lane_receipts"][0]
    assert comparison["presentation_orientation_receipt"]["orientation"] == 1
    assert comparison["presentation_orientation_receipt"]["matched_same_source_table_proofs"] == []
