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
    build_gemini_json_indexed_equity_matrix_query_evidence_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
    validate_gemini_json_equity_matrix_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "7" * 64
SOURCE_SHA256 = "8" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-financial-instruments-topology-v1.json"),
        _json("tm-financial-instruments-evaluation-v1.json"),
        _json("tm-financial-instruments-schema-binding-v1.json"),
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


def _table(*, date: str = "31/12/2025") -> dict:
    return {
        "columns": [
            _column("Cho vay và phải thu - Giá trị ghi sổ"),
            _column("Sẵn sàng để bán - Giá trị ghi sổ"),
            _column("Tổng giá trị ghi sổ"),
            _column("Giá trị hợp lý"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Tiền mặt và vàng", ["60", None, "60", "61"]),
            _row("Cho vay khách hàng", [None, "40", "40", "(*)"]),
            _row("Tổng tài sản tài chính", ["60", "40", "100", "101"], kind="TOTAL"),
            _row("Tiền gửi của khách hàng", [None, "70", "70", "70"]),
            _row("Phát hành giấy tờ có giá", ["30", None, "30", "29"]),
            _row("Tổng nợ phải trả tài chính", ["30", "70", "100", "99"], kind="TOTAL"),
        ],
        "title_exact": f"Tại ngày {date}",
        "unit_exact": "Triệu đồng",
    }


def _page(*tables: dict, narratives: list[str] | None = None) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": narratives or [],
                "statement_type": "NOT_APPLICABLE",
                "tables": list(tables),
                "title_exact": "Tài sản tài chính và nợ phải trả tài chính",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, *, page_ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + f"{page_ordinal:064x}",
        "physical_page": page_ordinal,
        "selected_page_ordinal": page_ordinal,
        "source_logical_name": "financial-instruments-fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict) -> tuple[dict, dict, dict, dict]:
    compiled = _compiled()
    record = _record(page)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=query,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return compiled, record, cluster, candidate


def _trial(candidate: dict) -> dict:
    return {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": candidate["reasons"],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": candidate["source_logical_name"],
        "source_sha256": candidate["source_sha256"],
        "status": candidate["status"],
    }


def _rehash_candidate(candidate: dict) -> None:
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )


def _evidence(record: dict, cluster: dict, compiled: dict) -> dict:
    document = {
        key: record[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    page = {
        **document,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "selected_page_ordinal": record["selected_page_ordinal"],
    }
    return build_gemini_json_indexed_equity_matrix_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=[page],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def test_fixed_matrix_maps_book_and_only_source_numeric_fair_values() -> None:
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(_table()))
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert by_role["BOOK_ASSET_CASH"]["values"][0]["coefficient"] == 60
    assert by_role["FAIR_ASSET_CASH"]["values"][0]["coefficient"] == 61
    assert by_role["FAIR_TOTAL_ASSETS"]["values"][0]["coefficient"] == 101
    assert by_role["FAIR_TOTAL_LIABILITIES"]["values"][0]["coefficient"] == 99
    assert "FAIR_ASSET_LOANS" not in by_role
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} >= {
        1305,
        1306,
        1329,
    }
    assert all(
        equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"]
    )


def test_compiled_schema_covers_interest_receivable_and_payable_children() -> None:
    bindings = _compiled()["valuation_component_bindings_by_role"]
    assert bindings["BOOK_ASSET_INTEREST_RECEIVABLE"] == {
        "book_report_norm_id": 1317,
        "fair_report_norm_id": 1340,
    }
    assert bindings["BOOK_LIABILITY_INTEREST_PAYABLE"] == {
        "book_report_norm_id": 1327,
        "fair_report_norm_id": 1350,
    }


def test_blank_categories_become_zero_only_after_row_equation_closes() -> None:
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(_table()))
    cash = candidate["closure_receipt"]["table_receipts"][0]["resolved_rows"][0]
    assert cash["classification_cells"][1]["coefficient"] == 0
    assert cash["classification_cells"][1]["state"] == "BLANK_ZERO_AFTER_ROW_EQUATION_EXACT"


def test_component_semantics_win_over_soft_gemini_subtotal_row_kind() -> None:
    table = _table()
    table["rows"][1]["row_kind"] = "SUBTOTAL"
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(table))
    assert candidate["status"] == READY
    assert any(mapping["role"] == "BOOK_ASSET_LOANS" for mapping in candidate["mappings"])


def test_left_compacted_gemini_row_uses_unique_arithmetic_pivot() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = ["60", "60", "61", None]
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(table))
    cash = candidate["closure_receipt"]["table_receipts"][0]["resolved_rows"][0]
    assert candidate["status"] == READY
    assert cash["alignment_mode"] == "PACKED_SPARSE_ROW_UNIQUE_ARITHMETIC_PIVOT"
    assert cash["book_total_cell"]["coefficient"] == 60
    assert cash["fair_value_cell"]["coefficient"] == 61


def test_duplicate_investment_rows_are_declaratively_aggregated() -> None:
    table = _table()
    table["rows"][2:2] = [
        _row("Chứng khoán đầu tư sẵn sàng để bán", ["10", None, "10", "11"]),
        _row("Chứng khoán giữ đến ngày đáo hạn", [None, "5", "5", "6"]),
    ]
    table["rows"][4]["values_exact"] = ["70", "45", "115", "118"]
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(table))
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["BOOK_ASSET_INVESTMENT"]["values"][0]["coefficient"] == 15
    assert by_role["FAIR_ASSET_INVESTMENT"]["values"][0]["coefficient"] == 17
    assert (
        by_role["BOOK_ASSET_INVESTMENT"]["values"][0]["state"]
        == "AGGREGATED_SOURCE_CELLS_GRAPH_EXACT"
    )


def test_two_explicit_period_tables_map_current_and_comparative() -> None:
    current = _table(date="31/12/2025")
    comparative = _table(date="31/12/2024")
    comparative["rows"][0]["values_exact"] = ["50", None, "50", "51"]
    comparative["rows"][2]["values_exact"] = ["50", "40", "90", "91"]
    compiled, record, cluster, candidate = _evaluate(_page(current, comparative))
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [
        (value["period_role"], value["period_date"], value["coefficient"])
        for value in by_role["BOOK_ASSET_CASH"]["values"]
    ] == [
        ("CURRENT_PERIOD", "2025-12-31", 60),
        ("COMPARATIVE_PERIOD", "2024-12-31", 50),
    ]
    assert len(cluster["component_regions"]) == 2
    assert (
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"]},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
        == candidate
    )


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda table: table["rows"].insert(
                2, _row("Khoản mục ngoại lai", ["1", None, "1", "1"])
            ),
            "UNCLASSIFIED_ACTIVE_VALUATION_ROW_PRESENT",
        ),
        (
            lambda table: table["rows"].insert(1, _row("Tiền mặt và vàng", ["1", None, "1", "1"])),
            "DUPLICATE_VALUATION_COMPONENT_ROLE",
        ),
    ],
)
def test_unconsumed_or_duplicate_declared_rows_fail_closed(mutate, reason: str) -> None:
    table = _table()
    mutate(table)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert reason in cluster["reasons"]


def test_row_or_branch_mismatch_has_no_mapping() -> None:
    table = _table()
    table["rows"][2]["values_exact"] = ["60", "40", "101", "101"]
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(table))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        "VALUATION_ROW_CLASSIFICATION_TOTAL_NOT_EXACT" in item for item in candidate["reasons"]
    )


def test_conflicting_declared_units_have_no_mapping() -> None:
    table = _table()
    table["unit_exact"] = "Triệu đồng / Nghìn đồng"
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(table))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("CONFLICTING_DECLARED_UNIT_ALIASES" in item for item in candidate["reasons"])


def test_fully_blank_mapped_row_is_unknown_not_silently_zero() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = [None, None, None, None]
    table["rows"][2]["values_exact"] = [None, "40", "40", "101"]
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_page(table))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        "VALUATION_ROW_CLASSIFICATION_TOTAL_NOT_EXACT" in item for item in candidate["reasons"]
    )


def test_owner_interval_reset_is_not_carried_into_later_table() -> None:
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(_table(), narratives=["Rủi ro thị trường"]))],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "OWNER_TO_VALUATION_MATRIX_INTERVAL_CONTAINS_RESET" in cluster["reasons"]


def test_cross_page_owner_requires_explicit_incoming_continuation() -> None:
    owner_page = _page()
    table = _table()
    detail_page = _page(table)
    detail_page["sections"][0]["title_exact"] = "Bảng chi tiết"
    records = [_record(owner_page), _record(detail_page, page_ordinal=2)]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "EXPLICIT_BOUNDED_VALUATION_MATRIX_OWNER_NOT_VISIBLE" in cluster["reasons"]

    owner_page["sections"][0]["narratives_exact"] = [
        "Bảng sau trình bày giá trị ghi sổ và giá trị hợp lý của các công cụ tài chính."
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert (
        cluster["owner_receipt"]["continuation_evidence"]["source_kind"]
        == "EXPLICIT_FORWARD_TABLE_NARRATIVE"
    )

    owner_page["sections"][0]["narratives_exact"] = []
    table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert cluster["owner_receipt"]["owner_position"][0] == 1
    assert (
        cluster["owner_receipt"]["continuation_evidence"]["source_kind"]
        == "STRUCTURED_TABLE_CONTINUATION"
    )


def test_partial_declared_sibling_fragment_cannot_be_hidden_below_role_threshold() -> None:
    partial = _table(date="31/12/2025")
    partial["rows"] = [
        _row("Tiền mặt và vàng", ["1", None, "1", "1"]),
        _row("Tổng tài sản tài chính", ["1", None, "1", "1"], kind="TOTAL"),
        _row("Tổng nợ phải trả tài chính", [None, None, "0", "0"], kind="TOTAL"),
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(_table(), partial))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "INCOMPLETE_DECLARED_VALUATION_TABLE_PRESENT" in cluster["reasons"]


def test_flat_sweep_rebuild_rejects_coherent_mapping_deletion() -> None:
    compiled, record, cluster, candidate = _evaluate(_page(_table()))
    forged = copy.deepcopy(candidate)
    forged["mappings"].pop()
    _rehash_candidate(forged)
    trial = _trial(forged)
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="schema mapping axis drifted",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-financial-instruments-topology-v1.json"),
            evaluation_spec=_json("tm-financial-instruments-evaluation-v1.json"),
            schema_binding_spec=_json("tm-financial-instruments-schema-binding-v1.json"),
            trials=[trial],
            indexed_query_evidence=_evidence(record, cluster, compiled),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda candidate: candidate["closure_receipt"]["equations"].pop(),
            "closure equation axis drifted",
        ),
        (
            lambda candidate: candidate["closure_receipt"]["table_receipts"][0]["classification"][
                "component_axis"
            ][0].update({"label_exact": "forged label"}),
            "table receipt drifted",
        ),
        (
            lambda candidate: candidate["closure_receipt"]["period_assignments"][0].update(
                {"period_date": "2099-12-31"}
            ),
            "period assignments drifted",
        ),
    ],
)
def test_flat_sweep_rejects_coherently_rehashed_redundant_receipt_drift(
    mutation, message: str
) -> None:
    compiled, record, cluster, candidate = _evaluate(_page(_table()))
    forged = copy.deepcopy(candidate)
    mutation(forged)
    _rehash_candidate(forged)
    with pytest.raises(GeminiJsonEquityMatrixAccountingFamilyV1Error, match=message):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-financial-instruments-topology-v1.json"),
            evaluation_spec=_json("tm-financial-instruments-evaluation-v1.json"),
            schema_binding_spec=_json("tm-financial-instruments-schema-binding-v1.json"),
            trials=[_trial(forged)],
            indexed_query_evidence=_evidence(record, cluster, compiled),
        )


def test_candidate_replay_rejects_coherently_rehashed_source_cell_drift() -> None:
    compiled, record, cluster, candidate = _evaluate(_page(_table()))
    forged = copy.deepcopy(candidate)
    row = forged["closure_receipt"]["table_receipts"][0]["resolved_rows"][0]
    row["classification_cells"][0]["source_text"] = "999"
    _rehash_candidate(forged)
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="does not replay",
    ):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"]},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
