from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonEquityMatrixAccountingFamilyV1Error,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    classify_gemini_json_equity_matrix_table_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
    validate_gemini_json_equity_matrix_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "b" * 64
SOURCE_SHA256 = "c" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-capital-and-funds-topology-v1.json"),
        _json("tm-capital-and-funds-evaluation-v1.json"),
        _json("tm-capital-and-funds-schema-binding-v1.json"),
    )


def _column(label: str) -> dict:
    return {"header_path_exact": [label], "value_kind": "MONEY"}


def _row(label: str | None, values: list[str | None], *, kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _component_column_table(
    *,
    opening: list[str | None] | None = None,
    details: list[list[str | None]] | None = None,
    closing: list[str | None] | None = None,
    unit: str | None = "Triệu đồng",
) -> dict:
    return {
        "columns": [
            _column("Vốn điều lệ"),
            _column("Thặng dư vốn cổ phần"),
            _column("Lợi ích cổ đông không kiểm soát"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ tại ngày 01/01/2025", opening or ["100", "20", "30", "150"]),
            *[
                _row(f"Biến động {ordinal}", values)
                for ordinal, values in enumerate(
                    details or [["10", " — ", "5", "15"], ["(5)", "_", "(2)", "(7)"]],
                    start=1,
                )
            ],
            _row("Số dư cuối kỳ tại ngày 31/12/2025", closing or ["105", "20", "33", "158"]),
        ],
        "title_exact": None,
        "unit_exact": unit,
    }


def _component_row_table() -> dict:
    return {
        "columns": [
            _column("Số dư đầu kỳ"),
            _column("Tăng trong kỳ"),
            _column("Giảm trong kỳ"),
            _column("Số dư cuối kỳ"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["100", "10", "5", "105"]),
            _row("Thặng dư vốn cổ phần", ["20", "-", "-", "20"]),
            _row("Lợi nhuận sau thuế chưa phân phối", ["30", "5", "2", "33"]),
            _row("Tổng cộng", ["150", "15", "7", "158"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _section(title: str, *tables: dict) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _page(*sections: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": list(sections),
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, *, ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + f"{ordinal:064x}",
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate_records(records: list[dict]) -> tuple[dict, dict, dict]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    pages = {record["page_json_version_id"]: record["page_json"] for record in records}
    receipt = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=receipt,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return compiled, cluster, candidate


def _evaluate_table(table: dict) -> tuple[dict, dict, dict]:
    return _evaluate_records([_record(_page(_section("Vốn chủ sở hữu", table)))])


def test_component_columns_close_without_exposing_graph_logic_to_gemini() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(_component_column_table())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["orientation"] == "COMPONENT_COLUMNS"
    assert [item["coefficient"] for item in by_role["CHARTER_CAPITAL"]["values"]] == [
        100,
        105,
    ]
    assert all(
        equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"]
    )


def test_component_rows_resolve_positive_decrease_presentation_locally() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(_component_row_table())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["orientation"] == "COMPONENT_ROWS"
    assert by_role["DECREASE_TOTAL"]["values"][0]["equation_multiplier"] == -1
    assert [item["coefficient"] for item in by_role["RETAINED_EARNINGS"]["values"]] == [
        30,
        5,
        2,
        33,
    ]


def test_component_columns_map_only_source_visible_explicit_movement_totals() -> None:
    table = _component_column_table()
    table["rows"][2]["label_exact"] = "Giảm trong kỳ"
    table["rows"][2]["hierarchy_path_exact"] = ["Giảm trong kỳ"]
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert by_role["DECREASE_TOTAL"]["values"][0]["coefficient"] == -7
    assert [item["axis_role"] for item in by_role["CHARTER_CAPITAL"]["values"]] == [
        "OPENING",
        "DECREASE",
        "CLOSING",
    ]
    assert "INCREASE_TOTAL" not in by_role


def test_latest_dated_block_wins_even_when_comparative_block_is_printed_after_it() -> None:
    table = _component_column_table()
    table["rows"].extend(
        [
            _row("Số dư đầu kỳ tại ngày 01/01/2024", ["80", "20", "20", "120"]),
            _row("Biến động năm trước", ["5", "-", "-", "5"]),
            _row("Số dư cuối kỳ tại ngày 31/12/2024", ["85", "20", "20", "125"]),
        ]
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [item["coefficient"] for item in by_role["OPENING_TOTAL"]["values"]] == [150]
    assert [item["coefficient"] for item in by_role["CLOSING_TOTAL"]["values"]] == [158]
    receipt = candidate["closure_receipt"]["period_block_receipt"]
    assert receipt["rule"] == "UNIQUE_LATEST_SOURCE_DATED_COMPLETE_BALANCE_BLOCK"
    assert len(receipt["candidate_blocks"]) == 2


def test_multiple_undated_complete_blocks_do_not_use_source_order_as_period_authority() -> None:
    table = _component_column_table()
    table["rows"][0]["label_exact"] = "Số dư đầu kỳ"
    table["rows"][0]["hierarchy_path_exact"] = ["Số dư đầu kỳ"]
    table["rows"][-1]["label_exact"] = "Số dư cuối kỳ"
    table["rows"][-1]["hierarchy_path_exact"] = ["Số dư cuối kỳ"]
    table["rows"].extend(
        [
            _row("Số dư đầu kỳ", ["80", "20", "20", "120"]),
            _row("Biến động trước", ["5", "-", "-", "5"]),
            _row("Số dư cuối kỳ", ["85", "20", "20", "125"]),
        ]
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "CURRENT_MOVEMENT_BLOCK_PERIOD_NOT_UNIQUE" in candidate["reasons"]


def test_equal_row_and_column_role_populations_are_orientation_ambiguous() -> None:
    table = _component_row_table()
    table["columns"] = [
        _column("Vốn điều lệ"),
        _column("Thặng dư vốn cổ phần"),
        _column("Lợi nhuận sau thuế chưa phân phối"),
        _column("Tổng cộng"),
    ]
    classification = classify_gemini_json_equity_matrix_table_v1(table, compiled_specs=_compiled())
    assert classification["status"] == "NOT_MATRIX"
    assert "BOTH_MATRIX_ORIENTATIONS_MATCH" in classification["reasons"]


def test_unique_monotone_row_alignment_uses_existing_digits_only() -> None:
    table = _component_column_table(
        details=[["5", "5", None, None], ["3", "3", None, None]],
        closing=["105", "20", "33", "158"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    receipts = [
        item
        for item in candidate["closure_receipt"]["alignment_receipts"]
        if item["rule"].startswith("UNIQUE_MONOTONE_DIGIT_PRESERVING")
    ]
    assert candidate["status"] == READY
    assert {tuple(item["effective_vector"]) for item in receipts} == {
        (5, 0, 0, 5),
        (0, 0, 3, 3),
    }
    for receipt in receipts:
        assert [item["coefficient"] for item in receipt["assignments"]] == [
            int(item["source_text"]) for item in receipt["assignments"]
        ]
        assert len({item["source_column_id"] for item in receipt["assignments"]}) == len(
            receipt["assignments"]
        )
        assert len({item["effective_component_axis_id"] for item in receipt["assignments"]}) == len(
            receipt["assignments"]
        )


def test_nonunique_row_alignment_remains_unresolved() -> None:
    table = _component_column_table(
        details=[["5", "5", None, None], ["5", "5", None, None]],
        closing=["105", "25", "30", "160"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROW_ALIGNMENT_EXACT_PLACEMENT_IS_NOT_UNIQUE" in candidate["reasons"]


def test_row_alignment_without_horizontal_exact_placement_remains_unresolved() -> None:
    table = _component_column_table(
        details=[["5", "6", None, None]],
        closing=["105", "20", "30", "155"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT" in candidate["reasons"]


def test_row_alignment_never_reorders_visible_numeric_tokens() -> None:
    table = _component_column_table(
        details=[["5", "3", "8", None]],
        closing=["103", "25", "30", "158"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROW_ALIGNMENT_HAS_NO_VERTICAL_EXACT_PLACEMENT" in candidate["reasons"]


def test_unconsumed_declared_role_table_after_selected_matrix_fails_closed() -> None:
    foreign = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page(_section("Vốn chủ sở hữu", _component_column_table(), foreign))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "UNCONSUMED_DECLARED_COMPONENT_EVIDENCE_IN_OWNER_INTERVAL" in cluster["reasons"]


def test_reset_ends_owner_scope_before_later_declared_role_table() -> None:
    foreign = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page(
        _section("Vốn chủ sở hữu", _component_column_table()),
        _section("Cổ phiếu", foreign),
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_explicit_same_section_detail_reset_fences_only_later_table() -> None:
    detail = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn góp của cổ đông", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
            _row("Cổ phiếu quỹ", ["-", "-"]),
            _row(None, ["2", "2"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    section = _section("Vốn chủ sở hữu", _component_column_table(), detail)
    section["narratives_exact"] = ["Chi tiết phần vốn của TCTD như sau:"]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(section))], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_adjacent_continuation_fragments_form_one_complete_graph() -> None:
    first = _component_column_table()
    second = copy.deepcopy(first)
    first["rows"] = first["rows"][:2]
    second["rows"] = second["rows"][2:]
    first["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    records = [
        _record(_page(_section("Vốn chủ sở hữu", first)), ordinal=1),
        _record(_page(_section("Tiếp theo", second)), ordinal=2),
    ]
    _compiled_specs, cluster, candidate = _evaluate_records(records)
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == READY


def test_conflicting_money_magnitudes_fail_closed() -> None:
    table = _component_column_table(unit="Triệu đồng; Nghìn đồng")
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("UNIT" in reason for reason in candidate["reasons"])


def test_candidate_replay_rejects_coherent_receipt_drift() -> None:
    compiled, cluster, candidate = _evaluate_table(_component_column_table())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["component_axis"][0]["members_exact"] = ["Vốn giả"]
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="does not replay",
    ):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={
                cluster["component_regions"][0]["page_json_version_id"]: _page(
                    _section("Vốn chủ sở hữu", _component_column_table())
                )
            },
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
