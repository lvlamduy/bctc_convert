from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from test_gemini_json_income_tax_family_v1 import (
    SOURCE_SHA256,
    VERSION_ID,
    _adapter_compiled,
    _adapter_compiled_with_fixture_row_repair,
    _collapsed_current_tax_row,
    _evaluate_supplemental_records,
    _page,
    _record,
    _row,
    _supplemental_records,
)

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    _post_merge_root_closure,
    _supplemental_root_controls,
    build_gemini_json_income_tax_region_query_receipt_v1,
    evaluate_gemini_json_income_tax_family_cluster_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _root_row(current: str | None = "12", comparative: str | None = "9") -> dict[str, Any]:
    return _row("Chi phí thuế TNDN", current, comparative, kind="TOTAL")


def _assert_identity(value: dict[str, Any], key: str, prefix: str) -> None:
    material = {name: item for name, item in value.items() if name != key}
    assert value[key] == prefix + canonical_json_sha256_v1(material)


def _query(records: list[dict[str, Any]], compiled: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    receipt = build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    return cluster, receipt


def _evaluate_query(
    records: list[dict[str, Any]],
    compiled: dict[str, Any],
    cluster: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    return evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: record["page_json"] for record in records},
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"} for record in records
        ],
        compiled_specs=compiled,
        query_receipt=receipt,
    )


def _reseal_query(receipt: dict[str, Any]) -> None:
    context = receipt["source_context_receipt"]
    for control in context["supplemental_root_controls"]:
        material = {key: value for key, value in control.items() if key != "control_id"}
        control["control_id"] = "gjitfav1:supplemental-root-control:" + canonical_json_sha256_v1(material)
    material = {key: value for key, value in context.items() if key != "receipt_id"}
    context["receipt_id"] = "gjitfav1:source-context:" + canonical_json_sha256_v1(material)
    material = {key: value for key, value in receipt.items() if key != "query_receipt_id"}
    receipt["query_receipt_id"] = "gjitfav1:query-receipt:" + canonical_json_sha256_v1(material)


def test_supplemental_root_control_preserves_exact_source_context_without_mutation() -> None:
    compiled = _adapter_compiled()
    records, note, _ = _supplemental_records([_root_row()])
    original = deepcopy(records)
    issues: list[str] = []
    controls = _supplemental_root_controls(records, compiled_specs=compiled, issues=issues)
    assert issues == []
    assert len(controls) == 1
    control = controls[0]
    _assert_identity(control, "control_id", "gjitfav1:supplemental-root-control:")
    assert control["locator"]["source_sha256"] == SOURCE_SHA256
    assert control["locator"]["page_json_version_id"] == VERSION_ID
    assert control["original_page_json_sha256"] == canonical_json_sha256_v1(note)
    assert control["original_table_json_sha256"] == canonical_json_sha256_v1(note["sections"][0]["tables"][0])
    assert control["canonical_unit"] == "MILLION_VND"
    assert control["lane_axis"]["complete"] is True
    assert control["money_column_ordinals"] == [1, 2]
    assert control["root_source_row"]["coefficients"] == [12, 9]
    assert control["root_source_row"]["values_exact"] == ["12", "9"]
    assert control["root_source_row"]["source_ref"]["row_id"] == "r1"
    assert control["root_source_row"]["source_ref"]["locator"] == control["locator"]
    assert len(control["source_table_row_axis"]) == 1
    assert records == original


@pytest.mark.parametrize("values", [(None, None), ("12", None), ("?", "9")])
def test_supplemental_root_control_cannot_discard_blank_partial_or_invalid_source(
    values: tuple[str | None, str | None],
) -> None:
    records, _, _ = _supplemental_records([_root_row(*values)])
    original = deepcopy(records)
    issues: list[str] = []
    controls = _supplemental_root_controls(records, compiled_specs=_adapter_compiled(), issues=issues)
    assert issues == ["SUPPLEMENTAL_ROOT_FRONTIER_NOT_COMPLETE"]
    assert len(controls) == 1
    assert controls[0]["root_source_row"]["values_exact"] == list(values)
    _assert_identity(controls[0], "control_id", "gjitfav1:supplemental-root-control:")
    assert records == original


@pytest.mark.parametrize("duplicate", [_root_row(), _root_row(None, None)])
def test_supplemental_root_duplicate_counts_unusable_surfaces(duplicate: dict[str, Any]) -> None:
    records, _, _ = _supplemental_records([_root_row(), deepcopy(duplicate)])
    issues: list[str] = []
    controls = _supplemental_root_controls(records, compiled_specs=_adapter_compiled(), issues=issues)
    assert "SUPPLEMENTAL_ROOT_AXIS_NOT_UNIQUE" in issues
    assert len(controls) == 2


def test_supplemental_root_cannot_infer_an_explicit_unsupported_unit() -> None:
    records, note, _ = _supplemental_records([_root_row()])
    table = note["sections"][0]["tables"][0]
    table["unit_exact"] = "Nghìn VND"
    for column in table["columns"]:
        column["header_path_exact"][-1] = "Nghìn VND"
    issues: list[str] = []
    controls = _supplemental_root_controls(records, compiled_specs=_adapter_compiled(), issues=issues)
    assert controls == []
    assert issues == ["SUPPLEMENTAL_ROOT_UNIT_AXIS_NOT_COMPLETE"]


@pytest.mark.parametrize("hierarchy_only", [False, True])
def test_supplemental_root_respects_negative_reset_without_row_kind_dependency(hierarchy_only: bool) -> None:
    root = _root_row()
    if hierarchy_only:
        root["hierarchy_path_exact"] = ["Tài sản thuế thu nhập hoãn lại", root["label_exact"]]
        rows = [root]
    else:
        rows = [_row("Tài sản thuế thu nhập hoãn lại", None, None), root]
    records, _, _ = _supplemental_records(rows)
    issues: list[str] = []
    controls = _supplemental_root_controls(records, compiled_specs=_adapter_compiled(), issues=issues)
    assert len(controls) == 1
    assert "SUPPLEMENTAL_ROOT_AFTER_STRUCTURAL_RESET" in issues


def test_post_merge_observed_deferred_cannot_silently_break_primary_root() -> None:
    records, _, _ = _supplemental_records(
        [_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1")],
        primary_deferred=(None, None), primary_root=("10", "8"),
    )
    original = deepcopy(records)
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    _assert_identity(candidate, "candidate_id", "gjmthfcv1:candidate:")
    assert records == original


@pytest.mark.parametrize("deferred", [("0", "0"), ("0", None)])
def test_post_merge_exact_or_partial_source_does_not_impute_blank(
    deferred: tuple[str | None, str | None],
) -> None:
    records, _, _ = _supplemental_records(
        [_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", *deferred)],
        primary_deferred=(None, None), primary_root=("10", "8"),
    )
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "DEFERRED_TAX_NET")
    assert [cell["source_text"] for cell in mapping["values"]] == list(deferred)
    assert [cell["coefficient"] for cell in mapping["values"]] == [0, 0 if deferred[1] is not None else None]
    receipt, mismatch = _post_merge_root_closure(candidate)
    assert mismatch is False
    assert receipt["lane_receipts"][0]["status"] == "EXACT_OBSERVED_SOURCE_LANE"
    assert receipt["lane_receipts"][1]["status"] == (
        "EXACT_OBSERVED_SOURCE_LANE" if deferred[1] is not None
        else "INCOMPLETE_DUE_TO_UNOBSERVED_SOURCE_LANE"
    )
    _assert_identity(receipt, "receipt_id", "gjitfav1:post-merge-root-closure:")


def test_post_merge_partial_source_still_vetoes_an_observed_conflicting_lane() -> None:
    records, _, _ = _supplemental_records(
        [_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", None)],
        primary_deferred=(None, None), primary_root=("10", "8"),
    )
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_post_merge_closure_receipt_binds_source_mappings_and_explicit_units() -> None:
    records, _, _ = _supplemental_records([])
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    original = deepcopy(candidate)
    receipt, mismatch = _post_merge_root_closure(candidate)
    assert mismatch is False
    assert receipt["status"] == "EXACT_ALL_OBSERVED_LANES"
    assert receipt["missing_roles"] == []
    assert receipt["mappings"] == candidate["mappings"]
    assert receipt["lane_receipts"][0]["component_sum_vnd"] == 12_000_000
    assert receipt["lane_receipts"][1]["component_sum_vnd"] == 9_000_000
    assert candidate == original
    _assert_identity(receipt, "receipt_id", "gjitfav1:post-merge-root-closure:")


def test_post_merge_closure_compares_only_explicit_million_and_vnd_scales() -> None:
    records, _, primary = _supplemental_records(
        [_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"), _root_row()],
        primary_current=("10000000", "8000000"),
        primary_deferred=("2000000", "1000000"),
        primary_root=("12000000", "9000000"),
    )
    primary["sections"][0]["tables"][0]["unit_exact"] = "VND"
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"VND", "MILLION_VND"}
    receipt, mismatch = _post_merge_root_closure(candidate)
    assert mismatch is False
    assert receipt["status"] == "EXACT_ALL_OBSERVED_LANES"
    assert [lane["residual_vnd"] for lane in receipt["lane_receipts"]] == [0, 0]


def test_post_merge_closure_masks_legacy_blank_zero_without_changing_source_mapping() -> None:
    records, _, _ = _supplemental_records([])
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    candidate = deepcopy(candidate)
    deferred = next(item for item in candidate["mappings"] if item["role"] == "DEFERRED_TAX_NET")
    deferred["values"][0] = {"state": "BLANK_ZERO", "coefficient": 0, "source_text": None}
    original = deepcopy(candidate)
    receipt, mismatch = _post_merge_root_closure(candidate)
    assert mismatch is False
    assert receipt["lane_receipts"][0]["operands_vnd"]["DEFERRED_TAX_NET"] is None
    assert receipt["lane_receipts"][0]["component_sum_vnd"] is None
    assert receipt["lane_receipts"][0]["status"] == "INCOMPLETE_DUE_TO_UNOBSERVED_SOURCE_LANE"
    assert candidate == original


@pytest.mark.parametrize("mutation", ["duplicate", "unsupported_unit", "invalid_cell", "wrong_lane_count"])
def test_post_merge_closure_fails_closed_for_malformed_mapping_axis(mutation: str) -> None:
    records, _, _ = _supplemental_records([])
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    candidate = deepcopy(candidate)
    mapping = candidate["mappings"][0]
    if mutation == "duplicate":
        candidate["mappings"].append(deepcopy(mapping))
    elif mutation == "unsupported_unit":
        mapping["unit"] = "THOUSAND_VND"
    elif mutation == "invalid_cell":
        mapping["values"][0]["coefficient"] = True
    else:
        mapping["values"].pop()
    receipt, mismatch = _post_merge_root_closure(candidate)
    assert mismatch is True
    assert receipt["status"] == "MISMATCH"
    assert receipt["reasons"]


@pytest.mark.parametrize("with_deferred", [False, True])
def test_equal_supplemental_root_is_only_authenticated_control(with_deferred: bool) -> None:
    rows = [_root_row()]
    if with_deferred:
        rows.insert(0, _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"))
    records, _, _ = _supplemental_records(rows)
    original = deepcopy(records)
    cluster, receipt = _query(records, _adapter_compiled())
    assert cluster["status"] == READY
    controls = receipt["source_context_receipt"]["supplemental_root_controls"]
    assert len(controls) == 1
    candidate = _evaluate_query(records, _adapter_compiled(), cluster, receipt)
    assert candidate["status"] == READY
    root_mappings = [item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"]
    assert len(root_mappings) == 1
    assert root_mappings[0]["source_refs"][0]["locator"]["page_json_version_id"] != VERSION_ID
    proof = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    assert proof["source_context_receipt"]["supplemental_root_controls"] == controls
    _assert_identity(proof["post_merge_root_closure"], "receipt_id", "gjitfav1:post-merge-root-closure:")
    _assert_identity(candidate, "candidate_id", "gjmthfcv1:candidate:")
    assert records == original


@pytest.mark.parametrize("with_deferred", [False, True])
def test_conflicting_supplemental_root_cannot_be_discarded_even_when_root_only(with_deferred: bool) -> None:
    rows = [_root_row("99", "99")]
    if with_deferred:
        rows.insert(0, _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"))
    records, _, _ = _supplemental_records(rows)
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    _assert_identity(candidate, "candidate_id", "gjmthfcv1:candidate:")


def test_supplemental_root_same_values_in_different_source_periods_cannot_compare_equal() -> None:
    records, note, _ = _supplemental_records([_root_row()])
    for column, year in zip(note["sections"][0]["tables"][0]["columns"], ("2025", "2024"), strict=True):
        column["header_path_exact"][0] = "Năm " + year
    _, candidate = _evaluate_supplemental_records(records, compiled=_adapter_compiled())
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_supplemental_root_column_order_is_bound_by_explicit_source_periods() -> None:
    records, note, _ = _supplemental_records([_root_row("9", "12")])
    columns = note["sections"][0]["tables"][0]["columns"]
    columns[0]["header_path_exact"][0] = "Năm 2025"
    columns[1]["header_path_exact"][0] = "Năm 2026"
    cluster, receipt = _query(records, _adapter_compiled())
    control = receipt["source_context_receipt"]["supplemental_root_controls"][0]
    assert control["money_column_ordinals"] == [2, 1]
    assert control["root_source_row"]["coefficients"] == [12, 9]
    assert _evaluate_query(records, _adapter_compiled(), cluster, receipt)["status"] == READY


def test_authenticated_root_without_final_root_mapping_is_retained_not_exported_or_compared() -> None:
    compiled = _adapter_compiled_with_fixture_row_repair()
    record = _record(_page([
        _row("Lợi nhuận kế toán trước thuế TNDN", "100", "80"),
        _row("Thu nhập chịu thuế", "100", "80", kind="SUBTOTAL"),
        _row("Thu nhập không chịu thuế", "-", "-"),
        _row("Chi phí không được khấu trừ", "1", "2"),
        _row("Chi phí thuế TNDN tính trên thu nhập chịu thuế kỳ hiện hành", "20", "15", kind="SUBTOTAL"),
        _collapsed_current_tax_row(),
        _row("Thu nhập thuế TNDN - hoãn lại", "-", "-"),
        _root_row("20", "15"),
    ], owner="29 THUẾ TNDN"))
    original = deepcopy(record)
    cluster, query = _query([record], compiled)
    candidate = _evaluate_query([record], compiled, cluster, query)
    assert candidate["status"] == READY
    assert all(item["role"] != "FAMILY_ROOT_TOTAL" for item in candidate["mappings"])
    proof = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    comparisons = proof["supplemental_root_lane_receipts"]
    assert len(comparisons) == 1
    assert comparisons[0]["root_mapping"] is None
    assert [lane["status"] for lane in comparisons[0]["lanes"]] == [
        "NO_FINAL_ROOT_MAPPING_CONTROL_RETAINED_NOT_EXPORTED",
        "NO_FINAL_ROOT_MAPPING_CONTROL_RETAINED_NOT_EXPORTED",
    ]
    assert [lane["final_root_vnd"] for lane in comparisons[0]["lanes"]] == [None, None]
    assert [lane["source_root_vnd"] for lane in comparisons[0]["lanes"]] == [20_000_000, 15_000_000]
    _assert_identity(proof, "receipt_id", "gjitfav1:source-controls:")
    assert record == original


@pytest.mark.parametrize("values", [(None, None), ("12", None), ("?", "9")])
def test_unusable_supplemental_root_blocks_recovery_without_primary_fallback(
    values: tuple[str | None, str | None],
) -> None:
    records, _, _ = _supplemental_records([_root_row(*values)])
    compiled = _adapter_compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert "SUPPLEMENTAL_ROOT_FRONTIER_NOT_COMPLETE" in cluster["reasons"]


def test_supplemental_root_query_rejects_raw_source_change_after_query() -> None:
    compiled = _adapter_compiled()
    records, _, _ = _supplemental_records([_root_row()])
    cluster, receipt = _query(records, compiled)
    changed = deepcopy(records)
    changed[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "99"
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(changed, compiled, cluster, receipt)


@pytest.mark.parametrize("mutation", ["delete", "source", "unit", "coefficients", "raw", "row", "page_hash", "lane"])
@pytest.mark.parametrize("reseal", [False, True])
def test_supplemental_root_query_rejects_tamper_even_after_complete_reseal(mutation: str, reseal: bool) -> None:
    compiled = _adapter_compiled()
    records, _, _ = _supplemental_records([_root_row()])
    cluster, receipt = _query(records, compiled)
    tampered = deepcopy(receipt)
    controls = tampered["source_context_receipt"]["supplemental_root_controls"]
    assert len(controls) == 1
    control = controls[0]
    if mutation == "delete":
        controls.clear()
    elif mutation == "source":
        control["locator"]["source_sha256"] = "f" * 64
    elif mutation == "unit":
        control["canonical_unit"] = "VND"
    elif mutation == "coefficients":
        control["root_source_row"]["coefficients"][0] = 99
    elif mutation == "raw":
        control["root_source_row"]["values_exact"][0] = "99"
    elif mutation == "row":
        control["root_source_row"]["source_ref"]["row_ordinal"] = 2
    elif mutation == "page_hash":
        control["original_page_json_sha256"] = "f" * 64
    else:
        control["lane_axis"]["money_column_ordinals"] = [2, 1]
    if reseal:
        _reseal_query(tampered)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, tampered)
