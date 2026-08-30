from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
    GeminiJsonCurrencyRiskMatrixV1Error,
)
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
DOCUMENT_ID = "gfpstorev1:document:" + "5" * 64
SOURCE_SHA256 = "6" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-currency-risk-topology-v1.json"),
        _json("tm-currency-risk-evaluation-v1.json"),
        _json("tm-currency-risk-schema-binding-v1.json"),
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


def _table() -> dict:
    return {
        "columns": [
            _column("EUR được quy đổi"),
            _column("USD được quy đổi"),
            _column("Các ngoại tệ khác được quy đổi"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Tổng tài sản", ["100", "200", "300", "600"], kind="TOTAL"),
            _row("Nợ phải trả và vốn chủ sở hữu", [None, None, None, None], kind="GROUP"),
            _row(
                "Tổng nợ phải trả và vốn chủ sở hữu",
                ["40", "120", "100", "260"],
                kind="TOTAL",
            ),
            _row("Trạng thái tiền tệ nội bảng", ["60", "80", "200", "340"]),
            _row("Trạng thái tiền tệ ngoại bảng", ["10", "(20)", "30", "20"]),
            _row("Trạng thái tiền tệ nội, ngoại bảng", ["70", "60", "230", "360"]),
        ],
        "title_exact": "Tại ngày 31/12/2025",
        "unit_exact": "Triệu đồng",
    }


def _page(table: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": "Rủi ro tiền tệ",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + "7" * 64,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "currency-risk-fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(table: dict) -> tuple[dict, dict, dict, dict]:
    compiled = _compiled()
    page = _page(table)
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
        for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
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


def test_exact_matrix_maps_raw_currency_cells_and_closes_equations() -> None:
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(_table())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["nonclosing_currency_frontiers"] == []
    assert by_role["EUR:ASSET_TOTAL"]["values"][0]["coefficient"] == 100
    assert by_role["USD:STATE_COMBINED"]["values"][0]["coefficient"] == 60
    assert all(
        equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"]
    )


def test_source_residual_is_retained_without_rewriting_or_blocking_other_axes() -> None:
    table = _table()
    table["rows"][3]["values_exact"][0] = "61"
    table["rows"][5]["values_exact"][0] = "71"
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    frontiers = candidate["closure_receipt"]["nonclosing_currency_frontiers"]
    assert candidate["status"] == READY
    assert by_role["EUR:STATE_INTERNAL"]["values"][0]["coefficient"] == 61
    assert [(item["currency_role"], item["equation_status"]) for item in frontiers] == [
        ("EUR", "MISMATCH")
    ]


def test_nonzero_blank_is_not_backsolved_but_other_visible_cells_still_map() -> None:
    table = _table()
    table["rows"][0]["values_exact"][0] = None
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert "EUR:ASSET_TOTAL" not in by_role
    assert by_role["EUR:LIABILITY_TOTAL"]["values"][0]["coefficient"] == 40
    assert any(
        item["currency_role"] == "EUR" and item["equation_status"] == "NOT_TESTABLE"
        for item in candidate["closure_receipt"]["nonclosing_currency_frontiers"]
    )


def test_blank_zero_is_promoted_only_when_one_unknown_equation_closes_at_zero() -> None:
    table = _table()
    table["rows"][0]["values_exact"][0] = "40"
    table["rows"][3]["values_exact"][0] = None
    table["rows"][5]["values_exact"][0] = "10"
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(table)
    internal = {mapping["role"]: mapping for mapping in candidate["mappings"]}[
        "EUR:STATE_INTERNAL"
    ]["values"][0]
    assert internal["coefficient"] == 0
    assert internal["state"] == "BLANK_ZERO_AFTER_ONE_UNKNOWN_EQUATION_EXACT"


def test_unsupported_currency_is_receipted_but_never_collapsed_into_other() -> None:
    table = _table()
    table["columns"].insert(3, _column("Vàng"))
    for row, value in zip(table["rows"], ["20", None, "5", "15", "1", "16"], strict=True):
        row["values_exact"].insert(3, value)
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(table)
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert any(
        column["role"] == "GOLD_SOURCE" and column["kind"] == "SOURCE_ONLY_CURRENCY"
        for column in receipt["classification"]["column_axis"]
    )
    assert all(not mapping["role"].startswith("GOLD_SOURCE:") for mapping in candidate["mappings"])


def test_less_than_two_exact_equation_columns_stays_unresolved_without_mapping() -> None:
    table = _table()
    for column_index in range(3):
        table["rows"][0]["values_exact"][column_index] = None
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["CURRENCY_RISK_REQUIRED_EQUATION_COVERAGE_INCOMPLETE"]


def test_conflicting_declared_unit_magnitudes_have_no_mapping() -> None:
    table = _table()
    table["unit_exact"] = "Triệu đồng / Nghìn đồng"
    _compiled_specs, _record_value, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("CONFLICTING_DECLARED_UNIT_ALIASES" in reason for reason in candidate["reasons"])


@pytest.mark.parametrize("kind", ["DUPLICATE", "UNCLASSIFIED"])
def test_duplicate_or_unclassified_active_currency_column_fails_closed(kind: str) -> None:
    table = _table()
    label = "EUR" if kind == "DUPLICATE" else "Đơn vị thử nghiệm"
    table["columns"].insert(1, _column(label))
    for row in table["rows"]:
        row["values_exact"].insert(1, "1")
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    expected = (
        "DUPLICATE_DECLARED_CURRENCY_COLUMN_ROLE"
        if kind == "DUPLICATE"
        else "ACTIVE_MONEY_COLUMN_HAS_NO_DECLARED_CURRENCY_ROLE"
    )
    assert expected in cluster["reasons"]


def test_duplicate_active_core_row_fails_closed() -> None:
    table = _table()
    table["rows"].insert(1, _row("Tổng tài sản", ["1", "1", "1", "3"], kind="TOTAL"))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "DUPLICATE_DECLARED_CURRENCY_CORE_ROW" in cluster["reasons"]


def test_partial_strong_currency_sibling_cannot_be_hidden_below_role_threshold() -> None:
    partial = {
        "columns": [_column("EUR"), _column("Tổng cộng")],
        "continuation": "NONE",
        "rows": [
            _row("Tổng tài sản", ["1", "1"], kind="TOTAL"),
            _row("Tổng nợ phải trả", ["1", "1"], kind="TOTAL"),
        ],
        "title_exact": "Tại ngày 31/12/2025",
        "unit_exact": "Triệu đồng",
    }
    page = _page(_table())
    page["sections"][0]["tables"].append(partial)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "INCOMPLETE_DECLARED_CURRENCY_RISK_TABLE_PRESENT" in cluster["reasons"]


def test_bare_other_business_segment_column_is_not_currency_evidence() -> None:
    segment = {
        "columns": [_column("Ngân hàng"), _column("Khác"), _column("Tổng cộng")],
        "continuation": "NONE",
        "rows": [
            _row("Tổng tài sản", ["1", "2", "3"], kind="TOTAL"),
            _row("Tổng nợ phải trả", ["1", "2", "3"], kind="TOTAL"),
        ],
        "title_exact": "Báo cáo bộ phận",
        "unit_exact": "Triệu đồng",
    }
    page = _page(_table())
    page["sections"][0]["tables"].append(segment)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_owner_to_matrix_reset_fence_fails_closed() -> None:
    page = _page(_table())
    table = page["sections"][0]["tables"].pop()
    page["sections"].extend(
        [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [],
                "title_exact": "Rủi ro lãi suất",
            },
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": "Bảng chi tiết",
            },
        ]
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "OWNER_TO_CURRENCY_RISK_MATRIX_INTERVAL_CONTAINS_RESET" in cluster["reasons"]


def test_multiple_dates_on_one_matrix_table_fail_closed() -> None:
    table = _table()
    table["title_exact"] = "Tại ngày 31/12/2025 và 30/06/2025"
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "TABLE_TITLE_PERIOD_DATE_NOT_UNIQUE" in cluster["reasons"]


def test_coherent_mapping_deletion_is_rejected_by_flat_rebuild() -> None:
    compiled, record, cluster, candidate = _evaluate(_table())
    forged = copy.deepcopy(candidate)
    forged["mappings"].pop()
    _rehash_candidate(forged)
    with pytest.raises(GeminiJsonCurrencyRiskMatrixV1Error, match="schema mapping axis drifted"):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-currency-risk-topology-v1.json"),
            evaluation_spec=_json("tm-currency-risk-evaluation-v1.json"),
            schema_binding_spec=_json("tm-currency-risk-schema-binding-v1.json"),
            indexed_query_evidence=_evidence(record, cluster, compiled),
            trials=[_trial(forged)],
        )


def test_candidate_replay_rejects_coherently_rehashed_nonclosing_drift() -> None:
    table = _table()
    table["rows"][3]["values_exact"][0] = "61"
    table["rows"][5]["values_exact"][0] = "71"
    compiled, record, cluster, candidate = _evaluate(table)
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["nonclosing_currency_frontiers"][0]["equation_status"] = (
        "NOT_TESTABLE"
    )
    _rehash_candidate(forged)
    with pytest.raises(GeminiJsonCurrencyRiskMatrixV1Error, match="non-closing axis drifted"):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-currency-risk-topology-v1.json"),
            evaluation_spec=_json("tm-currency-risk-evaluation-v1.json"),
            schema_binding_spec=_json("tm-currency-risk-schema-binding-v1.json"),
            indexed_query_evidence=_evidence(record, cluster, compiled),
            trials=[_trial(forged)],
        )


def test_source_replay_rejects_coherently_rehashed_cell_drift() -> None:
    compiled, record, cluster, candidate = _evaluate(_table())
    forged = copy.deepcopy(candidate)
    resolved = forged["closure_receipt"]["table_receipts"][0]["resolved_columns"][0]
    resolved["core_cells_by_role"]["ASSET_TOTAL"]["source_text"] = "999"
    _rehash_candidate(forged)
    with pytest.raises(GeminiJsonEquityMatrixAccountingFamilyV1Error, match="does not replay"):
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
