from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Chi phí hoạt động"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-operating-expense-topology-v1.json"),
        _json("tm-operating-expense-evaluation-v1.json"),
        _json("tm-operating-expense-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
    path: list[str | None] | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            [value for value in path if value is not None]
            if path is not None
            else ([label] if label is not None else [])
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _table(rows: list[dict[str, Any]], *, title: str | None = None) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["Năm 2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _section(
    title: str,
    *tables: dict[str, Any],
    narratives: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [] if narratives is None else narratives,
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _page(*sections: dict[str, Any]) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": list(sections),
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


def _base_rows() -> list[dict[str, Any]]:
    return [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        _row("Chi phí cho nhân viên", "30", "25", kind="GROUP"),
        _row(
            "Chi lương và phụ cấp",
            "20",
            "18",
            path=["Chi phí cho nhân viên", "Chi lương và phụ cấp"],
        ),
        _row(
            "Chi khác cho nhân viên",
            "10",
            "7",
            path=["Chi phí cho nhân viên", "Chi khác cho nhân viên"],
        ),
        _row("Chi về tài sản", "20", "15", kind="GROUP"),
        _row(
            "Chi khấu hao tài sản cố định",
            "12",
            "10",
            path=["Chi về tài sản", "Chi khấu hao tài sản cố định"],
        ),
        _row(
            "Chi thuê tài sản",
            "8",
            "5",
            path=["Chi về tài sản", "Chi thuê tài sản"],
        ),
        _row("Chi cho hoạt động quản lý công vụ", "15", "12", kind="GROUP"),
        _row(
            "Công tác phí",
            "4",
            "3",
            path=["Chi cho hoạt động quản lý công vụ", "Công tác phí"],
        ),
        _row(
            "Chi về các hoạt động đoàn thể của TCTD",
            "1",
            "1",
            path=[
                "Chi cho hoạt động quản lý công vụ",
                "Chi về các hoạt động đoàn thể của TCTD",
            ],
        ),
        _row(
            "Chi khác cho hoạt động quản lý",
            "10",
            "8",
            path=[
                "Chi cho hoạt động quản lý công vụ",
                "Chi khác cho hoạt động quản lý",
            ],
        ),
        _row("Chi nộp phí bảo hiểm tiền gửi của khách hàng", "5", "4"),
        _row("(Hoàn nhập)/trích lập dự phòng khác", "3", "2"),
        _row(None, "83", "66", kind="TOTAL", path=[None]),
    ]


def _operating_page(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return _page(_section(OWNER, _table(_base_rows() if rows is None else rows)))


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


def test_operating_expense_config_maps_declared_schema_and_keeps_source_gaps_local() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "OPERATING_EXPENSE"
    assert compiled["schema"]["family_root_report_norm_id"] == 1205
    assert set(compiled["bindings"].values()) == set(range(1206, 1221))
    assert "ADMIN_SCHEMA_GAP_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert "ADMIN_SCHEMA_GAP_SOURCE_ONLY" not in compiled["bindings"]


def test_complete_operating_expense_hierarchy_maps_and_replays() -> None:
    page = _operating_page()
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == {
        1205,
        1206,
        1207,
        1208,
        1211,
        1212,
        1213,
        1214,
        1215,
        1216,
        1217,
        1219,
        1220,
    }
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_visible_root_component_may_map_when_source_discloses_partial_children() -> None:
    rows = _base_rows()
    rows.pop(3)  # Employee subtotal remains source-visible; detail disclosure is partial.
    candidate, _cluster_value, _receipt = _evaluate(_operating_page(rows))
    assert candidate["status"] == READY
    assert "EMPLOYEE_EXPENSE" in {mapping["role"] for mapping in candidate["mappings"]}
    receipts = candidate["closure_receipt"]["root_component_sum_receipts"]
    assert any(item.get("result_role") == "EMPLOYEE_EXPENSE" for item in receipts)


def test_blank_disclosure_wrapper_scopes_shared_chi_khac_to_nearest_root() -> None:
    rows = _base_rows()
    rows[3] = _row("Trong đó", None, None, kind="GROUP", path=["Trong đó"])
    rows.insert(
        4,
        _row(
            "Chi khác",
            "10",
            "7",
            path=["Trong đó", "Chi khác"],
        ),
    )
    candidate, _cluster_value, _receipt = _evaluate(_operating_page(rows))
    assert candidate["status"] == READY
    assert "OTHER_EMPLOYEE_EXPENSE" in {mapping["role"] for mapping in candidate["mappings"]}
    table_receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert any(
        item["resolved_role"] == "OTHER_EMPLOYEE_EXPENSE"
        for item in table_receipt["classification"]["hierarchy_path_scope_resolutions"]
    )


def test_bounded_multi_note_suffix_matches_but_arbitrary_suffix_does_not() -> None:
    table = _table(
        [
            _row(
                "Chi nộp thuế và các khoản phí, lệ phí (xem Thuyết minh số 14.4 và 16.3)",
                "10",
                "8",
            ),
            _row("Chi phí cho nhân viên", "30", "25"),
            _row("Chi về tài sản", "20", "15"),
            _row(None, "60", "48", kind="TOTAL", path=[None]),
        ]
    )
    page = _page(_section(OWNER, table))
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, page["sections"][0], table, compiled_specs=_compiled()
    )
    assert "TAX_FEES" in {item["role"] for item in classification["role_hits"]}

    bad = copy.deepcopy(table)
    bad["rows"][0]["label_exact"] += " do kiểm toán viên điều chỉnh"
    bad["rows"][0]["hierarchy_path_exact"] = [bad["rows"][0]["label_exact"]]
    bad_page = _page(_section(OWNER, bad))
    bad_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        bad_page, bad_page["sections"][0], bad, compiled_specs=_compiled()
    )
    assert "TAX_FEES" not in {item["role"] for item in bad_classification["role_hits"]}


def test_supplemental_provision_detail_does_not_create_second_family_root() -> None:
    base = _table(_base_rows())
    supplemental = _table(
        [
            _row("Trích lập dự phòng rủi ro khác", "3", "2", kind="GROUP"),
            _row(
                "(Hoàn nhập)/trích lập dự phòng cho các tài sản Có nội bảng khác",
                "3",
                "2",
                path=[
                    "Trích lập dự phòng rủi ro khác",
                    "(Hoàn nhập)/trích lập dự phòng cho các tài sản Có nội bảng khác",
                ],
            ),
        ],
        title="Chi tiết dự phòng rủi ro khác",
    )
    candidate, _cluster_value, _receipt = _evaluate(_page(_section(OWNER, base, supplemental)))
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]].count("FAMILY_ROOT_TOTAL") == 1


def test_unrelated_table_from_different_owner_interval_does_not_contaminate_inventory() -> None:
    service = _table([_row("Chi phí hoạt động dịch vụ", "9", "8")])
    page = _page(
        _section("Chi phí hoạt động dịch vụ", service),
        _section("19. " + OWNER, _table(_base_rows())),
    )
    candidate, cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    dispositions = {item["disposition"] for item in cluster["declared_money_table_inventory"]}
    assert "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE" not in dispositions


def test_narrative_outline_reset_excludes_following_unrelated_money_table() -> None:
    operating = _table(_base_rows())
    unrelated = _table([_row("Giao dịch với bên liên quan", "9", "8")])
    page = _page(
        _section("19. " + OWNER, operating),
        _section(
            "Thông tin bổ sung",
            unrelated,
            narratives=["20. Giao dịch với các bên liên quan"],
        ),
    )
    candidate, cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_unproven_blank_detail_never_becomes_zero_from_parent_total_alone() -> None:
    rows = _base_rows()
    rows[9]["values_exact"][1] = None
    candidate, _cluster_value, _receipt = _evaluate(_operating_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("UNPROVEN_CONDITIONAL" in reason for reason in candidate["reasons"])


def test_corrupted_gemini_money_text_is_unresolved_not_backsolved() -> None:
    rows = _base_rows()
    rows[12]["values_exact"][0] = "494带有"
    candidate, _cluster_value, _receipt = _evaluate(_operating_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_missing_mapped_root_binding_is_rejected_but_validation_roles_need_none() -> None:
    schema = _json("tm-operating-expense-schema-binding-v1.json")
    schema["role_bindings"] = [
        item for item in schema["role_bindings"] if item["role"] != "TAX_FEES"
    ]
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="schema frontier is incomplete",
    ):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-operating-expense-topology-v1.json"),
            _json("tm-operating-expense-evaluation-v1.json"),
            schema,
        )
