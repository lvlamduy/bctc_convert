from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_equity_matrix_accounting_family_v1 as engine
from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
    _duration_role_v1,
    classify_interest_rate_column_role_v1,
    classify_interest_rate_row_role_v1,
    normalize_interest_rate_money_cell_v1,
)
from bctc_ai.evaluation.gemini_json_rollforward_table_repair_v1 import (
    _interest_rate_risk_repair_frontier_v1,
    _source_graph_gate_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "8" * 64
SOURCE_SHA256 = "9" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-interest-rate-risk-topology-v1.json"),
        _json("tm-interest-rate-risk-evaluation-v1.json"),
        _json("tm-interest-rate-risk-schema-binding-v1.json"),
    )


def _column(label: str) -> dict:
    return {"header_path_exact": [label], "value_kind": "MONEY"}


def _row(label: str, values: list[str | None], *, kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(*, title: str | None = "Tại ngày 31/12/2025") -> dict:
    values = ["100"] * 9
    liabilities = ["40"] * 9
    internal = ["60"] * 9
    external = ["10"] * 9
    combined = ["70"] * 9
    return {
        "columns": [
            _column("Quá hạn"),
            _column("Không chịu lãi suất"),
            _column("Đến 01 tháng"),
            _column("Từ 01 - 03 tháng"),
            _column("Từ trên 03 tháng đến 06 tháng"),
            _column("Từ 06 đến 12 tháng"),
            _column("Từ 01 đến 05 năm"),
            _column("Trên 05 năm"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Tổng tài sản (1)", values, kind="TOTAL"),
            _row("Tổng nợ phải trả (2)", liabilities, kind="TOTAL"),
            _row("Mức chênh nhạy cảm với lãi suất nội bảng (3)", internal),
            _row("Mức chênh nhạy cảm với lãi suất ngoại bảng (4)", external),
            _row(
                "Mức chênh nhạy cảm với lãi suất nội, ngoại bảng (5)",
                combined,
                kind="TOTAL",
            ),
        ],
        "title_exact": title,
        "unit_exact": "Triệu VND",
    }


def _page(
    table: dict | None,
    *,
    title: str | None = "Rủi ro lãi suất",
    content_kind: str = "FINANCIAL_NOTE",
    statement_type: str = "NOT_APPLICABLE",
) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": content_kind,
                "narratives_exact": [],
                "statement_type": statement_type,
                "tables": [] if table is None else [table],
                "title_exact": title,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, *, ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(ordinal) * 64,
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "interest-rate-risk-fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(records: list[dict]) -> tuple[dict, dict]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        compiled_specs=compiled,
        query_receipt=query,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return cluster, candidate


def test_formula_suffixes_and_internal_external_label_close_exact_matrix() -> None:
    _cluster, candidate = _evaluate([_record(_page(_table()))])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 56
    assert all(item["status"] == "EXACT" for item in candidate["closure_receipt"]["equations"])
    roles = candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "mapped_component_roles"
    ]
    assert roles == [
        "ASSET_TOTAL",
        "LIABILITY_TOTAL",
        "STATE_COMBINED",
        "STATE_EXTERNAL",
        "STATE_INTERNAL",
    ]


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("Đến 01 tháng", "WITHIN_LE1M"),
        ("Từ 01 - 03 tháng", "WITHIN_1_3M"),
        ("Từ trên 03 tháng đến 06 tháng", "WITHIN_3_6M"),
        ("Từ 06 đến 12 tháng", "WITHIN_6_12M"),
        ("Từ 01 đến 05 năm", "WITHIN_1_5Y"),
        ("Trên 1 năm", "WITHIN_GT1Y"),
        ("Trên 05 năm", "WITHIN_GT5Y"),
        ("Từ 1T đến 3T", "WITHIN_1_3M"),
    ],
)
def test_duration_parser_canonicalizes_numeric_spelling(surface: str, expected: str) -> None:
    assert _duration_role_v1(engine._normalized(surface)) == expected


def test_column_with_multiple_duration_roles_fails_closed() -> None:
    compiled = _compiled()
    role, kind, matches = classify_interest_rate_column_role_v1(
        _column("Từ 1 đến 3 tháng / Từ 3 đến 6 tháng"), compiled_specs=compiled
    )
    assert role is None
    assert kind is None
    assert matches == ["WITHIN_1_3M", "WITHIN_3_6M"]


def test_off_balance_commitment_row_is_external_interest_state() -> None:
    role, matches = classify_interest_rate_row_role_v1(
        "Các cam kết ngoại bảng có tác động tới mức độ nhạy cảm với LS",
        aliases_by_role=_compiled()["aliases_by_role"],
    )
    assert role == "STATE_EXTERNAL"
    assert matches == ["STATE_EXTERNAL"]


@pytest.mark.parametrize(
    ("source", "normalized", "state"),
    [
        ("--", "-", "NORMALIZED_NOISY_DASH_ZERO"),
        ("-\n-", "-", "NORMALIZED_NOISY_DASH_ZERO"),
        ("-条/null", "-", "NORMALIZED_NOISY_DASH_ZERO"),
        ("null", None, "NORMALIZED_TEXT_NULL_BLANK"),
        (
            "(46.310) provider_annotation -> -",
            "(46.310)",
            "NORMALIZED_UNIQUE_NOISY_SIGNED_INTEGER",
        ),
        ("15.305带有-?", "15.305", "NORMALIZED_UNIQUE_NOISY_SIGNED_INTEGER"),
    ],
)
def test_money_observation_normalizer_accepts_one_unambiguous_value(
    source: str, normalized: str | None, state: str
) -> None:
    assert normalize_interest_rate_money_cell_v1(source) == (normalized, state)


def test_noisy_dash_and_text_null_are_closed_only_by_equations() -> None:
    table = _table()
    table["rows"][3]["values_exact"][0] = "--"
    table["rows"][4]["values_exact"][0] = "60"
    table["rows"][3]["values_exact"][1] = "null"
    table["rows"][4]["values_exact"][1] = "60"
    _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["table_receipts"][0]["resolved_columns"]
    assert receipt[0]["core_cells_by_role"]["STATE_EXTERNAL"]["state"] == (
        "NORMALIZED_NOISY_DASH_ZERO"
    )
    assert receipt[1]["core_cells_by_role"]["STATE_EXTERNAL"]["state"] == (
        "BLANK_ZERO_AFTER_ONE_UNKNOWN_EQUATION_EXACT"
    )


def test_two_numeric_observations_in_one_cell_remain_unresolved() -> None:
    table = _table()
    table["rows"][3]["values_exact"][0] = "10 or 20"
    _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["INVALID_CURRENCY_RISK_CORE_CELL:OVERDUE:STATE_EXTERNAL"]


def test_typed_primary_balance_title_supplies_single_undated_matrix_period() -> None:
    reporting = _record(
        _page(
            None,
            title="BÁO CÁO TÌNH HÌNH TÀI CHÍNH - Tại ngày 30 tháng 06 năm 2026",
            content_kind="PRIMARY_STATEMENT",
            statement_type="BALANCE_SHEET",
        )
    )
    reporting["page_json"]["sections"].append(
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "Rủi ro lãi suất",
        }
    )
    matrix = _record(_page(_table(title=None), title=None), ordinal=2)
    cluster, candidate = _evaluate([reporting, matrix])
    assert cluster["owner_receipt"]["period_assignments"][0]["period_date"] == "2026-06-30"
    assert candidate["status"] == READY


def test_reset_after_owner_prevents_unrelated_maturity_table_admission() -> None:
    owner = _record(_page(None))
    reset = _record(_page(None, title="Rủi ro thanh khoản"), ordinal=2)
    matrix = _record(_page(_table(), title=None), ordinal=3)
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[owner, reset, matrix], compiled_specs=compiled
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_required_equation_mismatch_never_emits_partial_mapping() -> None:
    table = copy.deepcopy(_table())
    table["rows"][2]["values_exact"] = ["61"] * 9
    _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["CURRENCY_RISK_REQUIRED_EQUATION_COVERAGE_INCOMPLETE"]


def test_single_required_mismatch_repair_reads_only_three_visible_cells() -> None:
    table = copy.deepcopy(_table())
    table["rows"][2]["values_exact"][0] = "61"
    _cluster, candidate = _evaluate([_record(_page(table))])
    equations, target_ids, reasons = _interest_rate_risk_repair_frontier_v1(
        candidate=candidate,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        section_id="s1",
        table_id="t1",
    )
    assert target_ids == {"r1:c1", "r2:c1", "r3:c1"}
    assert len(equations) == 1
    assert reasons == ["INTEREST_RATE_RISK_REQUIRED_EQUATION_MISMATCH:OVERDUE:STATE_INTERNAL"]


def test_direct_target_observations_must_close_visible_row_grand_totals() -> None:
    table = _table()
    for row in table["rows"]:
        row["values_exact"][-1] = str(sum(int(value) for value in row["values_exact"][:-1]))
    plan = {
        "cell_allowlist": [
            {"cell_id": "r1:c1"},
            {"cell_id": "r2:c1"},
            {"cell_id": "r3:c1"},
        ],
        "family_id": "INTEREST_RATE_RISK",
    }
    exact = _source_graph_gate_v1(table, plan=plan)
    assert exact is not None
    assert exact["status"] == "EXACT"
    assert [item["status"] for item in exact["row_equations"]] == ["EXACT"] * 3

    drifted = copy.deepcopy(table)
    drifted["rows"][0]["values_exact"][0] = "101"
    nonclosing = _source_graph_gate_v1(drifted, plan=plan)
    assert nonclosing is not None
    assert nonclosing["status"] == "SOURCE_VISIBLE_NONCLOSING"
    assert nonclosing["row_equations"][0]["status"] == "SOURCE_VISIBLE_NONCLOSING"


def test_multi_column_required_mismatch_repair_reads_complete_core_matrix() -> None:
    table = copy.deepcopy(_table())
    table["rows"][2]["values_exact"][:2] = ["61", "61"]
    _cluster, candidate = _evaluate([_record(_page(table))])
    equations, target_ids, _reasons = _interest_rate_risk_repair_frontier_v1(
        candidate=candidate,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        section_id="s1",
        table_id="t1",
    )
    assert len(equations) == 18
    assert target_ids == {f"r{row}:c{column}" for row in range(1, 6) for column in range(1, 10)}
