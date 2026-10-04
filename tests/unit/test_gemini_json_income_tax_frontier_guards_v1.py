from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _canonical_rows,
    _evaluate_supplemental_records,
    _page,
    _record,
    _row,
    _supplemental_records,
)

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    _select_supplemental_role_mappings,
    _supplemental_negative_surface,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)


def _recover_rows(rows):
    compiled = _adapter_compiled()
    records, _note, _primary = _supplemental_records(rows)
    original = deepcopy(records)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert records == original
    return cluster


@pytest.mark.parametrize("kind", ["ITEM", "GROUP", "SUBTOTAL", "TOTAL", None])
def test_negative_label_fences_supplemental_rows_independently_of_row_kind(kind):
    cluster = _recover_rows(
        [
            _row("1. Tài sản thuế thu nhập hoãn lại", None, None, kind=kind),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"),
        ]
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["SUPPLEMENTAL_ROLE_AFTER_STRUCTURAL_RESET"]


@pytest.mark.parametrize("kind", ["ITEM", "GROUP", "SUBTOTAL", "TOTAL", None])
def test_hierarchy_only_negative_ancestor_fences_candidate_on_same_row(kind):
    row = _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1", kind=kind)
    row["hierarchy_path_exact"] = ["Tài sản thuế thu nhập hoãn lại", row["label_exact"]]
    cluster = _recover_rows([row])
    assert cluster["status"] == UNRESOLVED
    assert cluster["reasons"] == ["SUPPLEMENTAL_ROLE_AFTER_STRUCTURAL_RESET"]


def test_negative_surface_guard_preserves_positive_expense_hierarchy():
    row = _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1")
    row["hierarchy_path_exact"] = ["Chi phí thuế thu nhập doanh nghiệp", row["label_exact"]]
    assert not _supplemental_negative_surface(row, ["Tài sản thuế thu nhập hoãn lại"])
    cluster = _recover_rows([row])
    assert cluster["status"] == READY


def test_generic_direct_note_cannot_hide_consumed_role_under_negative_ancestor():
    compiled = _adapter_compiled()
    rows = _canonical_rows()
    rows[0]["hierarchy_path_exact"] = [
        "Tài sản thuế thu nhập hoãn lại", rows[0]["label_exact"]
    ]
    record = _record(_page(rows))
    original = deepcopy(record)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert base["status"] == READY
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["SUPPLEMENTAL_ROLE_AFTER_STRUCTURAL_RESET"]
    assert record == original


def _rate_records(parent_label, *, ancestor=None):
    parent = _row(parent_label, "21", "18", kind="TOTAL")
    if ancestor is not None:
        parent["hierarchy_path_exact"] = [ancestor] + (
            [] if parent_label is None else [parent_label]
        )
    records, _note, _primary = _supplemental_records(
        [], primary_current=("21", "18"), primary_root=("23", "19")
    )
    records[0]["page_json"] = _page(
        [
            _row("Chi phí thuế TNDN theo thuế suất", "20", "16"),
            _row("Điều chỉnh thuế TNDN năm trước", "1", "2"),
            parent,
        ]
    )
    return records


@pytest.mark.parametrize("label", ["Chi phí thuế TNDN hiện hành", "Cộng", None])
def test_rate_frontier_accepts_exact_parent_or_generic_under_current_tax_hierarchy(label):
    compiled = _adapter_compiled()
    records = _rate_records(label, ancestor="Chi phí thuế TNDN hiện hành")
    original = deepcopy(records)
    cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert cluster["status"] == candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["CURRENT_TAX_PARENT"]["values"]] == [21, 18]
    assert records == original


@pytest.mark.parametrize(
    "label",
    [
        "Thu nhập chịu thuế",
        "Lợi nhuận kế toán trước thuế",
        "Chi phí thuế thu nhập doanh nghiệp hoãn lại",
        "Chi phí thuế thu nhập doanh nghiệp",
    ],
)
def test_rate_frontier_vetoes_wrong_semantic_parent_even_when_arithmetic_closes(label):
    compiled = _adapter_compiled()
    records = _rate_records(label, ancestor="Chi phí thuế TNDN hiện hành")
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["SUPPLEMENTAL_CURRENT_TAX_PARENT_SEMANTIC_CONFLICT"]


@pytest.mark.parametrize("label", ["Cộng", None])
def test_generic_rate_parent_without_current_tax_ancestry_is_unresolved(label):
    compiled = _adapter_compiled()
    records = _rate_records(label)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["reasons"] == ["SUPPLEMENTAL_CURRENT_TAX_PARENT_SEMANTIC_CONFLICT"]


def _presentation(unit, values, identity, *, ordinal=1):
    descriptor = {
        "descriptor_id": identity,
        "locator": {"selected_page_ordinal": ordinal, "section_id": "s1", "table_id": "t1"},
    }
    mapping = {
        "role": "PROFIT_BEFORE_TAX",
        "unit": unit,
        "values": [{"coefficient": value} for value in values],
        "source_refs": [{"locator": {"page_json_version_id": identity}}],
    }
    return descriptor, {"status": READY, "mappings": [mapping]}


def test_unique_vnd_supplemental_presentation_wins_in_both_arrival_orders():
    million = _presentation("MILLION_VND", [10, 8], "million", ordinal=1)
    vnd = _presentation("VND", [10_000_000, 8_000_000], "vnd", ordinal=2)
    original = deepcopy([million, vnd])
    forward = _select_supplemental_role_mappings([million, vnd])
    reverse = _select_supplemental_role_mappings([vnd, million])
    assert forward == reverse
    selected, suppressed, reason = forward
    assert reason is None
    assert selected["PROFIT_BEFORE_TAX"][0]["unit"] == "VND"
    assert selected["PROFIT_BEFORE_TAX"][0]["source_refs"] == vnd[1]["mappings"][0]["source_refs"]
    assert [item["unit"] for item in suppressed] == ["MILLION_VND"]
    assert [million, vnd] == original


@pytest.mark.parametrize("delta", [0, 1])
def test_multiple_vnd_presentations_are_unresolved_without_value_based_tiebreak(delta):
    left = _presentation("VND", [10_000_000, 8_000_000], "left")
    right = _presentation("VND", [10_000_000 + delta, 8_000_000], "right")
    for presentations in ([left, right], [right, left]):
        selected, suppressed, reason = _select_supplemental_role_mappings(presentations)
        assert selected == {} and suppressed == []
        assert reason == (
            "CONFLICTING_DIRECT_SUPPLEMENTAL_INCOME_TAX_PRESENTATIONS"
            if delta else "MULTIPLE_HIGH_PRECISION_DIRECT_SUPPLEMENTAL_PRESENTATIONS"
        )


def test_partial_vnd_cannot_discard_complete_million_lane_evidence():
    million = _presentation("MILLION_VND", [10, 8], "million")
    vnd = _presentation("VND", [10_000_000, None], "vnd")
    forward = _select_supplemental_role_mappings([million, vnd])
    assert forward == _select_supplemental_role_mappings([vnd, million])
    assert forward[2] is None
    assert forward[0]["PROFIT_BEFORE_TAX"][0]["unit"] == "MILLION_VND"
    assert forward[0]["PROFIT_BEFORE_TAX"][0]["values"][1]["coefficient"] == 8
    assert forward[1][0]["values"][1]["coefficient"] is None


def test_duplicate_partial_vnd_is_not_hidden_by_complete_million_presentation():
    million = _presentation("MILLION_VND", [10, 8], "million")
    left = _presentation("VND", [10_000_000, None], "left")
    right = _presentation("VND", [10_000_000, None], "right")
    for ordered in ([million, left, right], [right, left, million]):
        selected, suppressed, reason = _select_supplemental_role_mappings(ordered)
        assert selected == {} and suppressed == []
        assert reason == "MULTIPLE_HIGH_PRECISION_DIRECT_SUPPLEMENTAL_PRESENTATIONS"


def test_complementary_partial_supplemental_lanes_fail_closed():
    left = _presentation("VND", [10_000_000, None], "left")
    right = _presentation("MILLION_VND", [None, 8], "right")
    selected, suppressed, reason = _select_supplemental_role_mappings([left, right])
    assert selected == {} and suppressed == []
    assert reason in {
        "CONFLICTING_DIRECT_SUPPLEMENTAL_INCOME_TAX_PRESENTATIONS",
        "INCOMPARABLE_PARTIAL_DIRECT_SUPPLEMENTAL_PRESENTATIONS",
    }


def test_equivalent_million_supplemental_control_is_stable_in_reverse_order():
    first = _presentation("MILLION_VND", [10, 8], "first", ordinal=1)
    second = _presentation("MILLION_VND", [10, 8], "second", ordinal=2)
    forward = _select_supplemental_role_mappings([first, second])
    assert forward == _select_supplemental_role_mappings([second, first])
    assert forward[2] is None
    assert forward[0]["PROFIT_BEFORE_TAX"][1]["descriptor_id"] == "first"


def _million_and_vnd_records():
    records, _note, _primary = _supplemental_records(
        [_row("Lợi nhuận kế toán trước thuế", "10", "8")]
    )
    million, primary = records
    vnd = deepcopy(million)
    vnd["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
    vnd["physical_page"] = vnd["selected_page_ordinal"] = 2
    table = vnd["page_json"]["sections"][0]["tables"][0]
    table["unit_exact"] = "VND"
    for column in table["columns"]:
        column["header_path_exact"][-1] = "VND"
    table["rows"][0]["values_exact"] = ["10000000", "8000000"]
    primary["physical_page"] = primary["selected_page_ordinal"] = 3
    return [million, vnd, primary]


def test_public_supplemental_evaluation_selects_vnd_and_replays_reverse_order():
    compiled = _adapter_compiled()
    records = _million_and_vnd_records()
    original = deepcopy(records)
    forward_cluster, forward = _evaluate_supplemental_records(records, compiled=compiled)
    reverse_cluster, reverse = _evaluate_supplemental_records(
        [records[1], records[0], records[2]], compiled=compiled
    )
    assert forward_cluster["status"] == reverse_cluster["status"] == READY
    assert forward["status"] == reverse["status"] == READY
    assert forward == reverse
    profit = next(item for item in forward["mappings"] if item["role"] == "PROFIT_BEFORE_TAX")
    assert profit["unit"] == "VND"
    assert [value["coefficient"] for value in profit["values"]] == [10_000_000, 8_000_000]
    assert profit["source_refs"][0]["locator"]["page_json_version_id"] == records[1][
        "page_json_version_id"
    ]
    assert records == original


def test_public_duplicate_vnd_supplemental_evaluation_fails_closed():
    compiled = _adapter_compiled()
    records = _million_and_vnd_records()
    duplicate = deepcopy(records[1])
    duplicate["page_json_version_id"] = "gfpstorev1:json:" + "f" * 64
    duplicate["physical_page"] = duplicate["selected_page_ordinal"] = 3
    records[-1]["physical_page"] = records[-1]["selected_page_ordinal"] = 4
    inputs = [records[0], records[1], duplicate, records[-1]]
    for ordered in (inputs, [duplicate, records[1], records[0], records[-1]]):
        _cluster, candidate = _evaluate_supplemental_records(ordered, compiled=compiled)
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
        assert candidate["reasons"] == ["MULTIPLE_HIGH_PRECISION_DIRECT_SUPPLEMENTAL_PRESENTATIONS"]
