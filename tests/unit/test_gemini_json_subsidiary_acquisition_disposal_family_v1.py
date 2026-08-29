from __future__ import annotations

import json
from copy import deepcopy
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

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Mua mới và thanh lý các công ty con"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-subsidiary-acquisition-disposal-topology-v1.json"),
        _json("tm-subsidiary-acquisition-disposal-evaluation-v1.json"),
        _json("tm-subsidiary-acquisition-disposal-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [] if label is None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _complete_rows(*, unknown: bool = False) -> list[dict[str, Any]]:
    rows = [
        _row("Tổng giá trị mua hoặc thanh lý", "100", "80", kind="TOTAL"),
        _row(
            "Phần giá trị mua hoặc thanh lý được thanh toán bằng tiền và các khoản tương đương tiền",
            "60",
            "50",
        ),
        _row(
            "Số tiền và các khoản tương đương tiền thực có trong công ty con hoặc đơn vị kinh doanh khác được mua hoặc thanh lý",
            "10",
            "8",
        ),
    ]
    if unknown:
        rows.append(_row("Khoản giao dịch không thuộc schema family", "1", "1"))
    return rows


def _table(
    rows: list[dict[str, Any]],
    *,
    unit: str = "Triệu đồng",
    current_header: str = "Năm 2025",
) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": [current_header, unit], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2024", unit], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }


def _page(
    rows: list[dict[str, Any]],
    *,
    owner: str | None = OWNER,
    unit: str = "Triệu đồng",
    current_header: str = "Năm 2025",
) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [_table(rows, unit=unit, current_header=current_header)],
                "title_exact": owner,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _cluster(page: dict[str, Any]) -> dict[str, Any]:
    return coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )


def _evaluate(page: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cluster = _cluster(page)
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, cluster, receipt


def test_config_binds_structural_root_and_three_required_numeric_roles() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "SUBSIDIARY_ACQUISITION_DISPOSAL"
    assert compiled["schema"]["family_root_report_norm_id"] == 1255
    assert compiled["schema"]["root_mapping_policy"] == "STRUCTURAL_CONTEXT_ONLY"
    assert compiled["bindings"] == {
        "TOTAL_CONSIDERATION": 1256,
        "CASH_SETTLEMENT": 1257,
        "ACQUIRED_DISPOSED_BUSINESS_CASH": 1258,
    }


def test_complete_three_role_table_maps_children_without_synthetic_root_or_sum() -> None:
    page = _page(_complete_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert [(item["role"], item["report_norm_id"]) for item in candidate["mappings"]] == [
        ("TOTAL_CONSIDERATION", 1256),
        ("CASH_SETTLEMENT", 1257),
        ("ACQUIRED_DISPOSED_BUSINESS_CASH", 1258),
    ]
    assert candidate["closure_receipt"]["structural_root_receipt"] == {
        "emitted_mapping": False,
        "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
        "report_norm_id": 1255,
        "role": "SUBSIDIARY_ACQUISITION_DISPOSAL_DISCLOSURE",
    }
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_policy_narrative_without_detailed_table_is_not_observed() -> None:
    page = _page([], owner="Hợp nhất kinh doanh và lợi thế thương mại")
    page["sections"][0]["narratives_exact"] = [
        "Hợp nhất kinh doanh được hạch toán theo phương pháp giá mua."
    ]
    cluster = _cluster(page)
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_broad_cash_flow_caption_is_not_a_detailed_family() -> None:
    page = _page(
        [_row("Mua công ty con, góp vốn liên doanh, liên kết", "(100)", "(80)")],
        owner="Báo cáo lưu chuyển tiền tệ",
    )
    cluster = _cluster(page)
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_incomplete_two_role_table_is_unresolved_not_backsolved() -> None:
    candidate, _cluster_value, _receipt = _evaluate(_page(_complete_rows()[:2]))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["REQUIRED_DECLARED_ROLE_COMBINATION_NOT_COMPLETE"]


def test_complete_owner_population_with_unknown_money_row_is_unresolved() -> None:
    candidate, _cluster_value, _receipt = _evaluate(_page(_complete_rows(unknown=True)))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("UNMAPPED" in reason for reason in candidate["reasons"])


def test_duplicate_required_role_is_unresolved() -> None:
    rows = _complete_rows()
    rows.insert(1, _row("Tổng giá trị mua hoặc bán", "100", "80"))
    candidate, _cluster_value, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


@pytest.mark.parametrize(
    ("unit", "current_header"),
    [
        ("Nghìn đồng", "Năm 2025"),
        ("Triệu đồng", "Năm 2025 và năm 2024"),
    ],
)
def test_unit_or_period_conflict_is_unresolved(unit: str, current_header: str) -> None:
    candidate, _cluster_value, _receipt = _evaluate(
        _page(_complete_rows(), unit=unit, current_header=current_header)
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_candidate_replay_rejects_coherent_mapping_value_tamper() -> None:
    page = _page(_complete_rows())
    candidate, cluster, receipt = _evaluate(page)
    tampered = deepcopy(candidate)
    tampered["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            tampered,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
