from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
ROOT_LABEL = "Lãi thuần từ mua bán chứng khoán kinh doanh"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-trading-securities-activity-topology-v1.json"),
        _json("tm-trading-securities-activity-evaluation-v1.json"),
        _json("tm-trading-securities-activity-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    parent: str | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            [label]
            if parent is None and label == ROOT_LABEL
            else [ROOT_LABEL, label]
            if parent is None
            else [parent, label]
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _page(*, provision: bool = True, net: tuple[str, str] = ("70", "60")) -> dict[str, Any]:
    rows = [
        _row(ROOT_LABEL, list(net), kind="TOTAL"),
        _row("Thu nhập từ mua bán chứng khoán kinh doanh", ["100", "80"]),
        _row(
            "Chi phí về mua bán chứng khoán kinh doanh",
            ["(20)", "(15)"] if provision else ["(30)", "(20)"],
        ),
    ]
    if provision:
        rows.append(_row("Trích lập dự phòng rủi ro chứng khoán kinh doanh", ["(10)", "(5)"]))
    table = {
        "columns": [
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": ROOT_LABEL,
        "unit_exact": "Triệu đồng",
    }
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": ROOT_LABEL,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate(page: dict[str, Any]) -> dict[str, Any]:
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def _candidate_and_replay_inputs(
    page: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    page_json_by_version = {VERSION_ID: page}
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, regions, page_json_by_version, receipt


def test_trading_securities_optional_provision_and_net_close_exactly() -> None:
    candidate = _evaluate(_page())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(by_role) == {
        "EXPENSE_TRADING_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_TRADING_SECURITIES",
        "PROVISION_TRADING_SECURITIES",
    }
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        70,
        60,
    ]


def test_trading_securities_absent_optional_provision_does_not_create_mapping() -> None:
    candidate = _evaluate(_page(provision=False))
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_TRADING_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_TRADING_SECURITIES",
    }


def test_trading_securities_single_visible_component_can_prove_source_total() -> None:
    page = _page(provision=False, net=("100", "80"))
    page["sections"][0]["tables"][0]["rows"] = [
        _row(ROOT_LABEL, ["100", "80"], kind="TOTAL"),
        _row("Thu nhập từ mua bán chứng khoán kinh doanh", ["100", "80"]),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "FAMILY_ROOT_TOTAL",
        "INCOME_TRADING_SECURITIES",
    }


def test_trading_securities_net_mismatch_is_unresolved_without_mappings() -> None:
    candidate = _evaluate(_page(net=("71", "61")))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_trading_securities_source_vocabulary_variants_map_by_declared_roles() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [
        _row(
            "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán kinh doanh", ["70", "60"], kind="TOTAL"
        ),
        _row("Lãi từ mua bán chứng khoán kinh doanh", ["100", "80"]),
        _row("Lỗ về mua bán chứng khoán kinh doanh", ["(20)", "(15)"]),
        _row(
            "(Trích lập)/Hoàn nhập dự phòng chứng khoán kinh doanh (Thuyết minh 8.1)",
            ["(10)", "(5)"],
        ),
    ]
    page["sections"][0]["title_exact"] = (
        "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán kinh doanh"
    )
    page["sections"][0]["tables"][0]["title_exact"] = (
        "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán kinh doanh"
    )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_TRADING_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_TRADING_SECURITIES",
        "PROVISION_TRADING_SECURITIES",
    }


def test_trading_securities_combined_table_consumes_only_explicit_root_subtree() -> None:
    investment_root = "Lãi/(lỗ) thuần từ mua bán chứng khoán đầu tư"
    page = _page()
    page["sections"][0]["title_exact"] = "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư"
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = None
    table["rows"] = [
        _row(ROOT_LABEL, [None, None], kind="GROUP"),
        _row("Thu nhập từ mua bán chứng khoán kinh doanh", ["100", "80"], parent=ROOT_LABEL),
        _row("Chi về mua bán chứng khoán kinh doanh", ["(20)", "(15)"], parent=ROOT_LABEL),
        _row(
            "(Trích lập)/Hoàn nhập dự phòng rủi ro chứng khoán kinh doanh",
            ["(10)", "(5)"],
            parent=ROOT_LABEL,
        ),
        _row(None, ["70", "60"], kind="SUBTOTAL", parent=ROOT_LABEL),
        _row(investment_root, [None, None], kind="GROUP", parent=investment_root),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["40", "30"], parent=investment_root),
        _row("Chi phí về mua bán chứng khoán đầu tư", ["(10)", "(5)"], parent=investment_root),
        _row(None, ["30", "25"], kind="SUBTOTAL", parent=investment_root),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 4
    assert all(
        "chứng khoán đầu tư" not in str(source_ref.get("label_exact", "")).lower()
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    )


def test_trading_securities_foreign_dimension_root_row_is_not_observed() -> None:
    page = _page()
    page["sections"][0]["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    table["rows"] = [
        _row(ROOT_LABEL, ["70", "60"]),
        _row("Lãi thuần từ hoạt động dịch vụ", ["20", "15"]),
    ]
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_trading_securities_unmapped_direct_child_fails_closed() -> None:
    page = _page(net=("71", "61"))
    page["sections"][0]["tables"][0]["rows"].append(
        _row("Khoản chứng khoán kinh doanh chưa khai báo", ["1", "1"])
    )
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_trading_securities_duplicate_population_and_axis_conflicts_fail_closed() -> None:
    duplicate = _page()
    duplicate["sections"][0]["tables"].append(copy.deepcopy(duplicate["sections"][0]["tables"][0]))
    duplicate_candidate = _evaluate(duplicate)
    assert duplicate_candidate["status"] == UNRESOLVED
    assert duplicate_candidate["mappings"] == []

    optional_drift = _page(net=("80", "65"))
    optional_drift["sections"][0]["tables"][0]["rows"][3]["values_exact"] = ["-", "-"]
    second = copy.deepcopy(optional_drift["sections"][0]["tables"][0])
    second["rows"] = second["rows"][:3]
    optional_drift["sections"][0]["tables"].append(second)
    optional_drift_candidate = _evaluate(optional_drift)
    assert optional_drift_candidate["status"] == UNRESOLVED
    assert optional_drift_candidate["mappings"] == []

    unit = _page()
    unit["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    unit_candidate = _evaluate(unit)
    assert unit_candidate["status"] == UNRESOLVED
    assert unit_candidate["mappings"] == []

    period = _page()
    period["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Năm 2025",
        "Năm trước",
        "Triệu đồng",
    ]
    period_candidate = _evaluate(period)
    assert period_candidate["status"] == UNRESOLVED
    assert period_candidate["mappings"] == []


def test_trading_securities_candidate_replay_rejects_coherent_receipt_drift() -> None:
    candidate, regions, page_json_by_version, receipt = _candidate_and_replay_inputs(_page())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["equations"][0]["status"] = "MISMATCH"
    material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
