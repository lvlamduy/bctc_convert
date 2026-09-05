from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as operating_expense_adapter
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_operating_expense_family_v1 import (
    GeminiJsonOperatingExpenseFamilyV1Error,
    build_gemini_json_operating_expense_indexed_query_evidence_v1,
    build_gemini_json_operating_expense_trials_v1,
    build_operating_expense_source_row_coverage_receipt_v1,
    compile_gemini_json_operating_expense_family_specs_v1,
    evaluate_gemini_json_operating_expense_family_cluster_v1,
    validate_gemini_json_operating_expense_candidate_replay_v1,
    validate_gemini_json_operating_expense_replay_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Chi phí hoạt động"
PRIMARY_VERSION_ID = "gfpstorev1:json:" + "d" * 64
CONTINUATION_VERSION_ID = "gfpstorev1:json:" + "e" * 64


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-operating-expense-topology-v1.json"),
        _json("tm-operating-expense-evaluation-v1.json"),
        _json("tm-operating-expense-schema-binding-v1.json"),
    )


def _source_repair_spec() -> dict[str, Any]:
    repair = {
        "after_exact": "-",
        "before_exact": None,
        "crop_evidence": {
            "bbox_pixels_xyxy": [10, 20, 40, 50],
            "pixel_height": 30,
            "pixel_width": 30,
            "rgb_sha256": "e" * 64,
        },
        "locator": {
            "column_ordinal": 2,
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "row_ordinal": 13,
            "section_id": "s1",
            "table_id": "t1",
        },
        "observed_pdf_glyph": "-",
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "render": {
            "image_sha256": "f" * 64,
            "image_size_bytes": 1234,
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": 100,
            "pixel_width": 100,
            "render_dpi": 300,
            "render_receipt_sha256": "1" * 64,
        },
        "source": {
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 999,
        },
    }
    repair["repair_id"] = "gjoefav1:source-repair:" + canonical_json_sha256_v1(repair)
    repairs = [repair]
    return {
        "family_id": "OPERATING_EXPENSE",
        "format_version": ("GEMINI_JSON_OPERATING_EXPENSE_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"),
        "policy": (
            "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_CORRECTS_NULL_OR_FALSE_NUMERIC_"
            "CELL_NO_BLANK_ZERO_INFERENCE"
        ),
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "render_dpi": 300,
            "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
        },
        "repair_axis_sha256": canonical_json_sha256_v1(repairs),
        "repairs": repairs,
    }


def _adapter_compiled(
    source_repair_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return compile_gemini_json_operating_expense_family_specs_v1(
        _json("tm-operating-expense-topology-v1.json"),
        _json("tm-operating-expense-evaluation-v1.json"),
        _json("tm-operating-expense-schema-binding-v1.json"),
        source_repair_spec,
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


def _source_row_coverage_inputs(
    page: dict[str, Any],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    dict[int, dict[str, dict[str, Any]]],
    dict[str, Any],
]:
    compiled = _adapter_compiled()
    record = _record(page)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    selected_document_axis = [
        {
            key: record[key]
            for key in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        }
    ]
    selected_page_axis = [
        {
            **selected_document_axis[0],
            **{
                key: record[key]
                for key in (
                    "page_json_version_id",
                    "physical_page",
                    "selected_page_ordinal",
                )
            },
        }
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    pages = {1: {VERSION_ID: page}}
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    return indexed, trials, pages, compiled


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


def _evaluate_adapter(
    page: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cluster = _cluster(page)
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[],
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
    assert "EMPLOYEE_SCHEMA_GAP_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert "FLAT_ASSET_RENT_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert "FLAT_ASSET_DEPRECIATION_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert "FLAT_ADMIN_PRINTING_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert "FLAT_ADMIN_TRAVEL_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert "FLAT_OTHER_OPERATING_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert compiled["owner_complete_population_policy"] == "EXACT_OWNER_WHOLE_MONEY_TABLE"
    assert set(compiled["aggregate_duplicate_roles"]) == set(compiled["bindings"])
    assert (
        compiled["source_presentation_rounding_policy"]
        == "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
    )
    assert (
        compiled["source_total_blank_lane_control_policy"] == "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
    )
    assert compiled["source_reference_identity_policy"] == "EXACT_UNIQUE_SOURCE_IDENTITIES"
    assert (
        compiled["continuation_period_axis_policy"]
        == "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
    )
    assert (
        compiled["duration_header_path_scope_policy"] == "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
    )
    assert "UNION_ACTIVITY_EXPENSE" not in compiled["root_component_roles"]
    assert {
        item["canonical_unit"] for item in compiled["unit_bindings"] if item["accepted"] is True
    } == {"MILLION_VND", "VND"}


def test_operating_expense_compile_rejects_preserved_duplicate_source_identity_policy() -> None:
    evaluation = _json("tm-operating-expense-evaluation-v1.json")
    evaluation["source_reference_identity_policy"] = "PRESERVE_SOURCE_PRESENTATIONS"
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="compiled family frontier is invalid",
    ):
        compile_gemini_json_operating_expense_family_specs_v1(
            _json("tm-operating-expense-topology-v1.json"),
            evaluation,
            _json("tm-operating-expense-schema-binding-v1.json"),
        )


def test_source_ref_backstop_rejects_duplicate_arithmetic_operand_state() -> None:
    source_ref = {
        "hierarchy_path_exact": ["Chi phí cho nhân viên"],
        "label_exact": "Chi phí cho nhân viên",
        "locator": {
            "page_json_version_id": VERSION_ID,
            "section_id": "s1",
            "table_id": "t1",
        },
        "money_column_ordinals": [1, 2],
        "row_id": "r2",
        "row_kind": "GROUP",
        "row_ordinal": 2,
    }
    candidate = {
        "mappings": [
            {
                "item_mapping_id": "gjmthfmv1:item:" + "1" * 64,
                "report_norm_id": 1207,
                "role": "EMPLOYEE_EXPENSE",
                "row_id": "corroborated:EMPLOYEE_EXPENSE",
                "source_refs": [copy.deepcopy(source_ref), copy.deepcopy(source_ref)],
                "state": "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE",
                "unit": "MILLION_VND",
                "values": [
                    {"coefficient": 2, "source_text": None, "state": "DERIVED"},
                    {"coefficient": 2, "source_text": None, "state": "DERIVED"},
                ],
            }
        ]
    }
    before = copy.deepcopy(candidate)
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="duplicate source provenance is unsafe",
    ):
        operating_expense_adapter._deduplicate_exact_mapping_source_refs(candidate)
    assert candidate == before


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
    assert candidate["status"] == READY
    union = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "UNION_ACTIVITY_EXPENSE"
    )
    assert union["values"] == [
        {"coefficient": 1, "source_text": "1", "state": "RAW_SIGNED_INTEGER"},
        {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
    ]
    assert union["state"] == "PARTIAL_SOURCE_OBSERVATION"
    control = next(
        receipt
        for receipt in candidate["closure_receipt"]["equations"]
        if receipt.get("result_source_refs", [{}])[0].get("row_id") == "r8"
    )
    assert control["lane_statuses"] == [
        "EXACT",
        "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
    ]
    assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0


@pytest.mark.parametrize(
    ("shape", "printed_current", "unit", "expected_status"),
    [
        ("SCALED_INTERVAL", "(457)", "Triệu đồng", READY),
        ("OUTSIDE_INTERVAL", "(455)", "Triệu đồng", UNRESOLVED),
        ("UNSCALED_VND", "(457)", "VND", UNRESOLVED),
    ],
)
def test_operating_expense_rounding_interval_is_scaled_complete_and_bounded(
    shape: str,
    printed_current: str,
    unit: str,
    expected_status: str,
) -> None:
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "(5)", "(6)"),
        _row("Chi phí cho nhân viên", "(257)", "(220)"),
        _row("Chi về tài sản", "(105)", "(70)"),
        _row("Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng", "(42)", "(34)"),
        _row("Chi cho hoạt động quản lý công vụ", "(50)", "(49)"),
        _row("Chi phí dự phòng (không tính chi phí dự phòng rủi ro)", "-", "-"),
        _row(None, printed_current, "(379)", kind="TOTAL", path=[None]),
    ]
    page = _operating_page(rows)
    table = page["sections"][0]["tables"][0]
    table["unit_exact"] = unit
    table["columns"] = [
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    before = copy.deepcopy(page)
    cluster = _cluster(page)
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    shared = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    assert shared["status"] == UNRESOLVED
    candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[],
        compiled_specs=_adapter_compiled(),
        query_receipt=receipt,
    )
    assert candidate["status"] == expected_status
    assert page == before
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    if shape == "SCALED_INTERVAL":
        assert len(adapter["root_closure_receipts"]) == 1
        equation = adapter["root_closure_receipts"][0]["equation"]
        assert equation["status"] == "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
        rounding = equation["source_presentation_rounding_receipt"]
        assert rounding["component_count"] == 6
        assert rounding["maximum_absolute_display_unit_residual"] == 3
        assert [item["residual"] for item in rounding["lane_receipts"]] == [2, 0]
        root = next(
            mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
        )
        assert [value["coefficient"] for value in root["values"]] == [-457, -379]
        for mapping in candidate["mappings"]:
            source_refs = mapping["source_refs"]
            assert len(source_refs) == len(
                {canonical_json_sha256_v1(source_ref) for source_ref in source_refs}
            )
            assert mapping["row_id"] == (
                source_refs[0]["row_id"]
                if len(source_refs) == 1
                else "corroborated:" + mapping["role"]
            )
        deduplications = adapter["source_ref_deduplication_receipts"]
        assert deduplications
        assert all(
            receipt["before_source_ref_count"] > receipt["after_source_ref_count"]
            for receipt in deduplications
        )
        assert all(
            receipt["result_mapping_row_id"] != receipt["prior_mapping_row_id"]
            for receipt in deduplications
        )
        assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0
    else:
        assert candidate["mappings"] == []
        assert adapter["root_closure_receipts"] == []


def test_all_blank_validation_only_role_is_omitted_from_exact_root_frontier() -> None:
    rows = _base_rows()
    rows.insert(
        -1,
        _row("Chi phí dự phòng giảm giá đầu tư dài hạn", None, None),
    )
    page = _operating_page(rows)
    before = copy.deepcopy(page)
    candidate, cluster, receipt = _evaluate_adapter(page)
    assert candidate["status"] == READY
    assert page == before
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    omissions = adapter["all_blank_validation_role_omission_receipts"]
    assert len(omissions) == 1
    assert omissions[0]["role"] == "GENERIC_PROVISION_SOURCE_ONLY"
    assert omissions[0]["original_role_kind"] == "ADDITIVE_CHILD"
    assert omissions[0]["private_retry_role_kind"] == "NONADDITIVE_CHILD"
    assert omissions[0]["source_observations"][0]["raw_values_exact"] == [None, None]
    assert "GENERIC_PROVISION_SOURCE_ONLY" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    for mapping in candidate["mappings"]:
        source_refs = mapping["source_refs"]
        assert len(source_refs) == len(
            {canonical_json_sha256_v1(source_ref) for source_ref in source_refs}
        )
        assert mapping["row_id"] == (
            source_refs[0]["row_id"]
            if len(source_refs) == 1
            else "corroborated:" + mapping["role"]
        )
    assert "source_ref_deduplication_receipts" not in adapter
    assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0
    validate_gemini_json_operating_expense_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[],
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


@pytest.mark.parametrize(
    ("values", "expected_status"),
    [(("1", None), UNRESOLVED), (("-", "-"), READY)],
)
def test_partial_or_dash_validation_role_is_never_omitted_as_blank(
    values: tuple[str | None, str | None],
    expected_status: str,
) -> None:
    rows = _base_rows()
    rows.insert(
        -1,
        _row("Chi phí dự phòng giảm giá đầu tư dài hạn", *values),
    )
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    assert adapter["all_blank_validation_role_omission_receipts"] == []
    assert candidate["status"] == expected_status
    if expected_status == UNRESOLVED:
        assert candidate["mappings"] == []


def test_corrupted_gemini_money_text_is_unresolved_not_backsolved() -> None:
    rows = _base_rows()
    rows[12]["values_exact"][0] = "494带有"
    candidate, _cluster_value, _receipt = _evaluate(_operating_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_flat_source_population_uses_printed_root_and_declared_complete_parents() -> None:
    rows = [
        _row("Lương và các chi phí liên quan", "30", "25"),
        _row("Chi phí in ấn, tiếp thị và khuyến mại", "5", "4"),
        _row("Chi phí thuê văn phòng và tài sản", "12", "10"),
        _row("Khấu hao và hao mòn tài sản cố định", "8", "5"),
        _row("Chi phí công nghệ thông tin (*)", "4", "3"),
        _row("Chi phí bảo dưỡng và sửa chữa tài sản", "3", "2"),
        _row("Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        _row("Chi phí dụng cụ và thiết bị", "2", "1"),
        _row("Chi phí thông tin liên lạc", "1", "1"),
        _row("Chi phí điện nước, vệ sinh văn phòng", "1", "1"),
        _row("Chi phí bảo hiểm cho các khoản tiền gửi khách hàng", "5", "4"),
        _row("Công tác phí", "1", "1"),
        _row("Chi phí dự phòng các tài sản Có khác", "2", "1"),
        _row("Chi phí dịch vụ tư vấn", "1", "1"),
        _row("Chi phí hoạt động khác", "2", "2"),
        _row(None, "87", "69", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    mapping_by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert {
        "ASSET_EXPENSE",
        "ADMIN_EXPENSE",
        "DEPRECIATION_EXPENSE",
        "TRAVEL_EXPENSE",
        "OTHER_OPERATING_EXPENSE",
    } <= set(mapping_by_role)
    assert [value["coefficient"] for value in mapping_by_role["ASSET_EXPENSE"]["values"]] == [
        25,
        18,
    ]
    assert [value["coefficient"] for value in mapping_by_role["ADMIN_EXPENSE"]["values"]] == [
        13,
        11,
    ]
    assert {
        "FLAT_ASSET_RENT_SOURCE_ONLY",
        "FLAT_ASSET_DEPRECIATION_SOURCE_ONLY",
        "FLAT_ASSET_MAINTENANCE_SOURCE_ONLY",
        "FLAT_ASSET_TOOLS_SOURCE_ONLY",
        "FLAT_ADMIN_PRINTING_SOURCE_ONLY",
        "FLAT_ADMIN_COMMUNICATION_SOURCE_ONLY",
        "FLAT_ADMIN_UTILITIES_SOURCE_ONLY",
        "FLAT_ADMIN_TRAVEL_SOURCE_ONLY",
        "FLAT_ADMIN_CONSULTING_SOURCE_ONLY",
        "FLAT_OTHER_OPERATING_SOURCE_ONLY",
    }.issubset(
        {row["declared_role"] for row in candidate["closure_receipt"]["source_only_unmapped_rows"]}
    )
    assert [value["coefficient"] for value in mapping_by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        87,
        69,
    ]
    assert mapping_by_role["FAMILY_ROOT_TOTAL"]["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER"
    )
    assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0


def test_unitless_note_uses_exact_same_document_primary_root_without_value_change() -> None:
    compiled = _adapter_compiled()
    note = _operating_page()
    note_table = note["sections"][0]["tables"][0]
    note_table["unit_exact"] = None
    note_table["columns"][0]["header_path_exact"] = ["Năm 2026"]
    note_table["columns"][1]["header_path_exact"] = ["Năm 2025"]
    note_record = _record(note)
    note_record["physical_page"] = 2
    note_record["selected_page_ordinal"] = 2
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[note_record], compiled_specs=compiled
    )
    assert cluster["status"] == READY

    primary = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm 2026"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2025"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [_row(OWNER, "83", "66")],
                        "title_exact": "Báo cáo kết quả hoạt động kinh doanh",
                        "unit_exact": None,
                    }
                ],
                "title_exact": "Báo cáo kết quả hoạt động kinh doanh",
            },
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "BALANCE_SHEET",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["31/12/2026"], "value_kind": "MONEY"},
                            {"header_path_exact": ["31/12/2025"], "value_kind": "MONEY"},
                        ],
                        "continuation": "NONE",
                        "rows": [_row("Tổng tài sản", "1", "1")],
                        "title_exact": "Bảng cân đối kế toán",
                        "unit_exact": "VND",
                    }
                ],
                "title_exact": "Bảng cân đối kế toán",
            },
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }
    pages = {VERSION_ID: note, PRIMARY_VERSION_ID: primary}
    before = copy.deepcopy(pages)
    selected_page_axis = [
        {
            "document_ordinal": 1,
            "page_json_version_id": PRIMARY_VERSION_ID,
            "physical_page": 1,
            "selected_page_ordinal": 1,
        },
        {
            "document_ordinal": 1,
            "page_json_version_id": VERSION_ID,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert pages == before
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    assert len(adapter["unit_corroboration_receipts"]) == 1
    unit_receipt = adapter["unit_corroboration_receipts"][0]
    assert unit_receipt["canonical_unit"] == "VND"
    primary_root = unit_receipt["matched_primary_roots"][0]
    assert primary_root["unit_receipt"]["rule"] == (
        "UNITLESS_PRIMARY_INCOME_STATEMENT_TABLE_USES_UNIQUE_"
        "SAME_DOCUMENT_PRIMARY_STATEMENT_UNIT_CONTEXT"
    )
    assert len(primary_root["unit_receipt"]["evidence"]["evidence_axis"]) == 1
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [83, 66]
    assert root["unit"] == "VND"
    validate_gemini_json_operating_expense_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    mismatched = copy.deepcopy(primary)
    mismatched["sections"][0]["tables"][0]["rows"][0]["values_exact"] = ["84", "66"]
    unresolved = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: note, PRIMARY_VERSION_ID: mismatched},
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert unresolved["status"] == UNRESOLVED
    assert unresolved["mappings"] == []
    assert (
        unresolved["closure_receipt"]["operating_expense_adapter_receipt"][
            "unit_corroboration_receipts"
        ]
        == []
    )

    conflicting = copy.deepcopy(primary)
    conflicting["sections"][1]["tables"].append(
        {
            "columns": [
                {"header_path_exact": ["31/12/2026"], "value_kind": "MONEY"},
                {"header_path_exact": ["31/12/2025"], "value_kind": "MONEY"},
            ],
            "continuation": "NONE",
            "rows": [_row("Tổng nguồn vốn", "1", "1")],
            "title_exact": "Bảng cân đối kế toán",
            "unit_exact": "Triệu đồng",
        }
    )
    conflict_candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: note, PRIMARY_VERSION_ID: conflicting},
        selected_page_axis=selected_page_axis,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert conflict_candidate["status"] == UNRESOLVED
    assert conflict_candidate["mappings"] == []
    assert (
        conflict_candidate["closure_receipt"]["operating_expense_adapter_receipt"][
            "unit_corroboration_receipts"
        ]
        == []
    )


def _continuation_query_fixture() -> tuple[
    dict[str, Any], dict[int, dict[str, dict[str, Any]]], dict[str, Any]
]:
    compiled = _adapter_compiled()
    report_header = "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT\nQUÝ II NĂM 2026"
    prior_rows = [
        _row("1. Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        _row("2. Chi phí nhân viên", "30", "25", kind="GROUP"),
        _row(
            "Chi lương và phụ cấp",
            "20",
            "18",
            path=["2. Chi phí nhân viên", "Chi lương và phụ cấp"],
        ),
        _row(
            "Chi khác cho nhân viên",
            "10",
            "7",
            path=["2. Chi phí nhân viên", "Chi khác cho nhân viên"],
        ),
        _row("3. Chi về tài sản", "20", "15", kind="GROUP"),
        _row(
            "Chi phí khấu hao tài sản cố định",
            "12",
            "10",
            path=["3. Chi về tài sản", "Chi phí khấu hao tài sản cố định"],
        ),
        _row(
            "Chi phí thuê tài sản",
            "8",
            "5",
            path=["3. Chi về tài sản", "Chi phí thuê tài sản"],
        ),
        _row("4. Chi cho hoạt động quản lý và công vụ", "15", "12", kind="GROUP"),
        _row(
            "Công tác phí",
            "4",
            "3",
            path=["4. Chi cho hoạt động quản lý và công vụ", "Công tác phí"],
        ),
    ]
    prior_table = _table(prior_rows, title=OWNER)
    prior_table["columns"] = [
        {"header_path_exact": [OWNER, "Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": [OWNER, "Kỳ trước"], "value_kind": "MONEY"},
    ]
    prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    prior_table["unit_exact"] = "Đơn vị tính: triệu đồng"
    receiver_table = {
        "columns": [
            {"header_path_exact": [None], "value_kind": "MONEY"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            _row("Chi phí điện, nước, vệ sinh cơ quan", "4", "3"),
            _row("Chi phí thông tin liên lạc", "3", "2"),
            _row("Chi phí hội nghị, lễ tân, khánh tiết", "4", "4"),
            _row(
                "5. Chi nộp phí bảo hiểm tiền gửi của khách hàng",
                "5",
                "4",
            ),
            _row("Cộng", "80", "64", kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Đơn vị tính: triệu đồng",
    }
    prior_page = _page(_section(report_header, prior_table))
    receiver_page = _page(_section(report_header, receiver_table))
    prior_record = _record(prior_page)
    receiver_record = {
        **_record(receiver_page),
        "page_json_version_id": CONTINUATION_VERSION_ID,
        "physical_page": 2,
        "selected_page_ordinal": 2,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[prior_record, receiver_record],
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    assert [region["physical_page"] for region in cluster["component_regions"]] == [1]
    selected_document_axis = [
        {
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
        }
    ]
    selected_page_axis = [
        {
            **selected_document_axis[0],
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "selected_page_ordinal": 1,
        },
        {
            **selected_document_axis[0],
            "page_json_version_id": CONTINUATION_VERSION_ID,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    pages = {1: {VERSION_ID: prior_page, CONTINUATION_VERSION_ID: receiver_page}}
    return base, pages, compiled


def _rebuild_continuation_query_fixture(
    pages: dict[int, dict[str, dict[str, Any]]], compiled: dict[str, Any]
) -> dict[str, Any]:
    prior_page = pages[1][VERSION_ID]
    receiver_page = pages[1][CONTINUATION_VERSION_ID]
    prior_record = _record(prior_page)
    receiver_record = {
        **_record(receiver_page),
        "page_json_version_id": CONTINUATION_VERSION_ID,
        "physical_page": 2,
        "selected_page_ordinal": 2,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[prior_record, receiver_record],
        compiled_specs=compiled,
    )
    selected_document_axis = [
        {
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
        }
    ]
    selected_page_axis = [
        {
            **selected_document_axis[0],
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "selected_page_ordinal": 1,
        },
        {
            **selected_document_axis[0],
            "page_json_version_id": CONTINUATION_VERSION_ID,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def _internal_owner_continuation_query_fixture(
    *,
    duplicate_owner: bool = False,
    observed_owner: bool = False,
    receiver_marker: str = "CONTINUES_FROM_PREVIOUS_PAGE",
    receiver_physical_page: int = 2,
) -> tuple[dict[str, Any], dict[int, dict[str, dict[str, Any]]], dict[str, Any]]:
    compiled = _adapter_compiled()
    report_header = "THUYẾT MINH BÁO CÁO TÀI CHÍNH\nQUÝ I NĂM 2026"
    prior_rows = [
        _row("29. Lãi/lỗ thuần từ hoạt động khác", None, None, kind="GROUP"),
        _row(
            "Thu khác",
            "1",
            "1",
            path=["29. Lãi/lỗ thuần từ hoạt động khác", "Thu khác"],
        ),
        _row("Cộng", "1", "1", kind="TOTAL"),
        _row(
            "30. Chi phí hoạt động",
            "1" if observed_owner else None,
            None,
            kind="GROUP",
        ),
    ]
    if duplicate_owner:
        prior_rows.append(_row("Chi phí hoạt động", None, None, kind="GROUP"))
    for label, current, comparative in (
        ("1. Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        ("2. Chi phí nhân viên", "30", "25"),
        ("3. Chi về tài sản", "20", "15"),
        ("4. Chi cho hoạt động quản lý và công vụ", "15", "12"),
    ):
        prior_rows.append(
            _row(
                label,
                current,
                comparative,
                path=["30. Chi phí hoạt động", label],
            )
        )
    prior_table = _table(prior_rows)
    prior_table["columns"] = [
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    prior_table["continuation"] = "BOTH"
    receiver_table = _table(
        [
            _row(
                "5. Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng",
                "5",
                "4",
            ),
            _row("Cộng", "80", "64", kind="TOTAL"),
        ]
    )
    receiver_table["columns"] = [
        {"header_path_exact": [None], "value_kind": "MONEY"},
        {"header_path_exact": [None], "value_kind": "MONEY"},
    ]
    receiver_table["continuation"] = receiver_marker
    prior_page = _page(_section(report_header, prior_table))
    receiver_page = _page(_section(report_header, receiver_table))
    records = [
        _record(prior_page),
        {
            **_record(receiver_page),
            "page_json_version_id": CONTINUATION_VERSION_ID,
            "physical_page": receiver_physical_page,
            "selected_page_ordinal": 2,
        },
    ]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    selected_document_axis = [
        {
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
        }
    ]
    selected_page_axis = [
        {
            **selected_document_axis[0],
            "page_json_version_id": record["page_json_version_id"],
            "physical_page": record["physical_page"],
            "selected_page_ordinal": record["selected_page_ordinal"],
        }
        for record in records
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    return (
        base,
        {1: {VERSION_ID: prior_page, CONTINUATION_VERSION_ID: receiver_page}},
        compiled,
    )


def _titleless_primary_query_fixture(
    *, primary_root: tuple[str, str] = ("83", "66"), table_title: str | None = None
) -> tuple[dict[str, Any], dict[int, dict[str, dict[str, Any]]], dict[str, Any]]:
    compiled = _adapter_compiled()
    note_table = _table(_base_rows(), title=table_title)
    note_table["unit_exact"] = None
    note_table["columns"] = [
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    note_page = _page(
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [note_table],
            "title_exact": None,
        }
    )
    note_record = {
        **_record(note_page),
        "physical_page": 2,
        "selected_page_ordinal": 2,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[note_record], compiled_specs=compiled
    )
    primary_page = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
                            {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
                        ],
                        "continuation": "NONE",
                        "rows": [_row(OWNER, *primary_root)],
                        "title_exact": "Báo cáo kết quả hoạt động kinh doanh",
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Báo cáo kết quả hoạt động kinh doanh",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }
    selected_document_axis = [
        {
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
        }
    ]
    selected_page_axis = [
        {
            **selected_document_axis[0],
            "page_json_version_id": PRIMARY_VERSION_ID,
            "physical_page": 1,
            "selected_page_ordinal": 1,
        },
        {
            **selected_document_axis[0],
            "page_json_version_id": VERSION_ID,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    return base, {1: {PRIMARY_VERSION_ID: primary_page, VERSION_ID: note_page}}, compiled


def _owner_region_query_fixture(
    *, duplicate_owner: bool = False
) -> tuple[dict[str, Any], dict[int, dict[str, dict[str, Any]]], dict[str, Any]]:
    compiled = _adapter_compiled()
    provision = _table(
        [
            _row("Trích lập dự phòng rủi ro khác", "3", "2", kind="GROUP"),
            _row("Chi phí dự phòng các tài sản Có khác", "3", "2"),
            _row("Tổng", "3", "2", kind="TOTAL"),
        ]
    )
    sections = [
        _section("Trích lập dự phòng rủi ro khác", provision),
        _section(OWNER, _table(_base_rows(), title=OWNER)),
    ]
    if duplicate_owner:
        sections.append(_section(OWNER, _table(_base_rows(), title=OWNER)))
    page = _page(*sections)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    selected_document_axis = [
        {
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
        }
    ]
    selected_page_axis = [
        {
            **selected_document_axis[0],
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "selected_page_ordinal": 1,
        }
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    return base, {1: {VERSION_ID: page}}, compiled


def test_unique_complete_owner_region_recovery_is_structural_private_and_replays() -> None:
    base, pages, compiled = _owner_region_query_fixture()
    before_base = copy.deepcopy(base)
    before_pages = copy.deepcopy(pages)
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    replayed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert adapted == replayed
    assert base == before_base
    assert pages == before_pages
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert [
        (region["section_id"], region["table_id"]) for region in cluster["component_regions"]
    ] == [("s2", "t1")]
    receipt = cluster["operating_expense_owner_region_recovery_receipt"]
    assert receipt["selected_owner_evidence"]["terminal_total_row_ordinal"] == 14
    assert receipt["selected_owner_evidence"]["required_role_combinations"] == [
        ["TAX_FEES", "EMPLOYEE_EXPENSE", "ASSET_EXPENSE"]
    ]
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    assert trial["status"] == READY
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0


def test_owner_region_recovery_rejects_duplicate_complete_owner_tables() -> None:
    base, pages, compiled = _owner_region_query_fixture(duplicate_owner=True)
    before_regions = copy.deepcopy(
        base["candidate_dispositions"][0]["cluster"]["component_regions"]
    )
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert "operating_expense_owner_region_recovery_receipt" not in cluster
    assert cluster["component_regions"] == before_regions


def test_exact_adjacent_operating_expense_continuation_is_private_and_replays() -> None:
    base, pages, compiled = _continuation_query_fixture()
    before_base = copy.deepcopy(base)
    before_pages = copy.deepcopy(pages)
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    replayed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert adapted == replayed
    assert base == before_base
    assert pages == before_pages
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert [region["physical_page"] for region in cluster["component_regions"]] == [1, 2]
    assert "operating_expense_continuation_query_receipt" in cluster
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    assert trial["status"] == READY
    assert pages == before_pages
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    candidate = trial["candidates"][0]
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    assert len(adapter["continuation_projection_receipts"]) == 1
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [80, 64]
    assert [
        (source_ref["locator"]["physical_page"], source_ref["row_ordinal"])
        for source_ref in root["source_refs"]
    ] == [(2, 5)]
    assert {
        source_ref["locator"]["physical_page"]
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    } == {1, 2}


def test_internal_owner_reciprocal_continuation_recovers_only_source_suffix() -> None:
    base, pages, compiled = _internal_owner_continuation_query_fixture()
    assert base["candidate_dispositions"][0]["cluster"]["status"] != READY
    before_base = copy.deepcopy(base)
    before_pages = copy.deepcopy(pages)
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert base == before_base
    assert pages == before_pages
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert cluster["status"] == READY
    assert [region["physical_page"] for region in cluster["component_regions"]] == [1, 2]
    query_receipt = cluster["operating_expense_continuation_query_receipt"]
    internal = query_receipt["internal_owner_projection"]
    assert internal["owner_row_ordinal"] == 4
    assert [row["label_exact"] for row in internal["excluded_prefix_rows"]] == [
        "29. Lãi/lỗ thuần từ hoạt động khác",
        "Thu khác",
        "Cộng",
    ]
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    assert trial["status"] == READY
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    refs = [
        source_ref
        for mapping in trial["mappings"]
        for source_ref in mapping["source_refs"]
    ]
    assert min(
        source_ref["row_ordinal"]
        for source_ref in refs
        if source_ref["locator"]["physical_page"] == 1
    ) == 5
    assert not any(
        source_ref["row_ordinal"] <= 4
        for source_ref in refs
        if source_ref["locator"]["physical_page"] == 1
    )


@pytest.mark.parametrize(
    "mutation",
    ["DUPLICATE_OWNER", "OBSERVED_OWNER", "MISSING_RECIPROCAL", "NONADJACENT"],
)
def test_internal_owner_continuation_recovery_fails_closed(mutation: str) -> None:
    base, pages, compiled = _internal_owner_continuation_query_fixture(
        duplicate_owner=mutation == "DUPLICATE_OWNER",
        observed_owner=mutation == "OBSERVED_OWNER",
        receiver_marker=(
            "NONE" if mutation == "MISSING_RECIPROCAL" else "CONTINUES_FROM_PREVIOUS_PAGE"
        ),
        receiver_physical_page=3 if mutation == "NONADJACENT" else 2,
    )
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []
    assert "operating_expense_continuation_query_receipt" not in cluster


def test_titleless_complete_table_requires_exact_same_document_primary_root() -> None:
    base, pages, compiled = _titleless_primary_query_fixture()
    assert base["candidate_dispositions"][0]["cluster"]["status"] != READY
    before_base = copy.deepcopy(base)
    before_pages = copy.deepcopy(pages)
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert base == before_base
    assert pages == before_pages
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert cluster["status"] == READY
    receipt = cluster["operating_expense_titleless_primary_region_recovery_receipt"]
    evidence = receipt["selected_region_evidence"]
    assert evidence["target_total_observation"]["vector"] == [83, 66]
    assert evidence["unique_canonical_unit"] == "MILLION_VND"
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    assert trial["status"] == READY
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    assert next(
        mapping for mapping in trial["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )["source_refs"][0]["row_ordinal"] == 14


@pytest.mark.parametrize("mutation", ["MISMATCHED_ROOT", "VISIBLE_TABLE_TITLE", "NONTERMINAL_TOTAL"])
def test_titleless_primary_region_recovery_fails_closed(mutation: str) -> None:
    base, pages, compiled = _titleless_primary_query_fixture(
        primary_root=("84", "66") if mutation == "MISMATCHED_ROOT" else ("83", "66"),
        table_title="Chi phí khác" if mutation == "VISIBLE_TABLE_TITLE" else None,
    )
    if mutation == "NONTERMINAL_TOTAL":
        table = pages[1][VERSION_ID]["sections"][0]["tables"][0]
        table["rows"].append(_row("Dòng không xác định", "1", "1"))
        record = {
            **_record(pages[1][VERSION_ID]),
            "physical_page": 2,
            "selected_page_ordinal": 2,
        }
        cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=[record], compiled_specs=compiled
        )
        base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
            selected_document_axis=base["selected_document_axis"],
            selected_page_axis=base["selected_page_axis"],
            document_clusters=[cluster],
            query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
        )
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []
    assert "operating_expense_titleless_primary_region_recovery_receipt" not in cluster


@pytest.mark.parametrize(
    "shape",
    [
        "EQUIVALENT_EXPLICIT_HEADERS",
        "ONE_SIDED_PRIOR_MARKER",
        "DIFFERENT_RECEIVER_MONEY_ORDINALS",
        "DIRECT_DETAIL_MISLABELED_SUBTOTAL",
    ],
)
def test_operating_expense_continuation_bounded_source_shapes_replay(
    shape: str,
) -> None:
    _base, pages, compiled = _continuation_query_fixture()
    prior = pages[1][VERSION_ID]["sections"][0]["tables"][0]
    receiver = pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]
    if shape == "EQUIVALENT_EXPLICIT_HEADERS":
        receiver["columns"][0]["header_path_exact"] = ["Kỳ này"]
        receiver["columns"][1]["header_path_exact"] = ["Kỳ trước"]
    elif shape == "ONE_SIDED_PRIOR_MARKER":
        prior["continuation"] = "NONE"
    elif shape == "DIFFERENT_RECEIVER_MONEY_ORDINALS":
        receiver["columns"] = [
            {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"},
            *receiver["columns"],
        ]
        for row in receiver["rows"]:
            row["values_exact"] = [None, *row["values_exact"]]
    else:
        prior["rows"][2]["row_kind"] = "SUBTOTAL"
    before_pages = copy.deepcopy(pages)
    base = _rebuild_continuation_query_fixture(pages, compiled)
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    assert trial["status"] == READY
    assert pages == before_pages
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    projection = trial["candidates"][0]["closure_receipt"]["operating_expense_adapter_receipt"][
        "continuation_projection_receipts"
    ][0]
    if shape == "EQUIVALENT_EXPLICIT_HEADERS":
        assert (
            projection["receiver_header_axis_rule"]
            == "EXACT_EQUIVALENT_EXPLICIT_PERIOD_AXIS_NO_MUTATION"
        )
    elif shape == "ONE_SIDED_PRIOR_MARKER":
        assert projection["prior_marker"] == "NONE"
    elif shape == "DIFFERENT_RECEIVER_MONEY_ORDINALS":
        receiver_rows = [
            item
            for item in projection["row_projections"]
            if item["before_locator"]["physical_page"] == 2
        ]
        assert {tuple(item["before_money_column_ordinals"]) for item in receiver_rows} == {(2, 3)}
        assert {
            tuple(source_ref["money_column_ordinals"])
            for mapping in trial["mappings"]
            for source_ref in mapping["source_refs"]
            if source_ref["locator"]["physical_page"] == 2
        } == {(2, 3)}
    else:
        assert projection["partial_detail_subtotal_item_projections"] == [
            {
                "before_locator": {
                    "page_json_version_id": VERSION_ID,
                    "physical_page": 1,
                    "section_id": "s1",
                    "selected_page_ordinal": 1,
                    "table_id": "t1",
                },
                "before_row_ordinal": 3,
                "role": "SALARY_ALLOWANCE",
            }
        ]
        salary = next(
            mapping for mapping in trial["mappings"] if mapping["role"] == "SALARY_ALLOWANCE"
        )
        assert salary["source_refs"][0]["row_kind"] == "SUBTOTAL"


def test_unconsumed_receiver_empty_cluster_recovers_only_exact_reason_locator() -> None:
    base, pages, compiled = _continuation_query_fixture()
    cluster = copy.deepcopy(base["candidate_dispositions"][0]["cluster"])
    receiver = next(
        item for item in cluster["declared_money_table_inventory"] if item["physical_page"] == 2
    )
    receiver["disposition"] = "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE"
    cluster["component_regions"] = []
    cluster["reasons"] = [
        "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:"
        + ":".join(
            (
                receiver["page_json_version_id"],
                receiver["section_id"],
                receiver["table_id"],
            )
        )
    ]
    cluster["status"] = UNRESOLVED
    material = {key: value for key, value in cluster.items() if key != "cluster_id"}
    cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=base["selected_page_axis"],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    recovered = adapted["candidate_dispositions"][0]["cluster"]
    assert recovered["status"] == READY
    assert [region["physical_page"] for region in recovered["component_regions"]] == [
        1,
        2,
    ]
    assert (
        recovered["operating_expense_continuation_query_receipt"]["receiver_locator"][
            "page_json_version_id"
        ]
        == receiver["page_json_version_id"]
    )
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    assert trial["status"] == READY
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0


@pytest.mark.parametrize(
    "mutation",
    ["NONADJACENT", "MISSING_MARKER", "EXPLICIT_HEADER", "MEANINGFUL_SECTION", "UNIT_CONFLICT"],
)
def test_operating_expense_continuation_recovery_fails_closed(mutation: str) -> None:
    base, pages, compiled = _continuation_query_fixture()
    receiver = pages[1][CONTINUATION_VERSION_ID]
    table = receiver["sections"][0]["tables"][0]
    if mutation == "NONADJACENT":
        base["selected_page_axis"][1]["physical_page"] = 3
        disposition = base["candidate_dispositions"][0]
        disposition["cluster"]["declared_money_table_inventory"][-1]["physical_page"] = 3
        disposition["cluster"]["declared_money_table_inventory"][-1]["position"][0] = 3
        material = {
            key: value for key, value in disposition["cluster"].items() if key != "cluster_id"
        }
        disposition["cluster"]["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(
            material
        )
        base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
            selected_document_axis=base["selected_document_axis"],
            selected_page_axis=base["selected_page_axis"],
            document_clusters=[disposition["cluster"]],
            query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
        )
    elif mutation == "MISSING_MARKER":
        table["continuation"] = "NONE"
    elif mutation == "EXPLICIT_HEADER":
        table["columns"][0]["header_path_exact"] = ["Kỳ này"]
    elif mutation == "MEANINGFUL_SECTION":
        receiver["sections"][0]["title_exact"] = "31. Chi phí hoạt động khác"
    else:
        table["unit_exact"] = "VND"
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    assert [region["physical_page"] for region in cluster["component_regions"]] == [1]
    assert "operating_expense_continuation_query_receipt" not in cluster


def _adapt_continuation_pages_for_unit_test(
    pages: dict[int, dict[str, dict[str, Any]]], compiled: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = _rebuild_continuation_query_fixture(pages, compiled)
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    return adapted, trial


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("fragment", [VERSION_ID, CONTINUATION_VERSION_ID])
@pytest.mark.parametrize(
    "unit",
    [
        "USD", "Nghìn đồng", "Triệu đồng và VND", "Triệu đồng và eur", "VND", "Unit: XYZ",
        "Triệu đồng ₹", "Triệu đồng ₽",
    ],
)
def test_continuation_invalid_explicit_unit_never_becomes_missing(
    layout: str, fragment: str, unit: str
) -> None:
    fixture = (
        _continuation_query_fixture
        if layout == "COMPLETE_OWNER"
        else _internal_owner_continuation_query_fixture
    )
    _base, pages, compiled = fixture()
    pages[1][fragment]["sections"][0]["tables"][0]["unit_exact"] = unit
    before = copy.deepcopy(pages)
    adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert pages == before
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    assert "operating_expense_continuation_query_receipt" not in (
        adapted["candidate_dispositions"][0]["cluster"]
    )
    if layout == "INTERNAL_OWNER":
        receipts = adapted["candidate_dispositions"][0]["cluster"][
            "operating_expense_internal_owner_unit_rejection_receipts"
        ]
        assert len(receipts) == 1
        assert receipts[0]["owner_proof"]["owner_row_ordinal"] == 4
        assert [item["locator"]["physical_page"] for item in receipts[0]["unit_frontiers"]] == [1, 2]
        assert trial["reasons"] == ["OPERATING_EXPENSE_INTERNAL_OWNER_CONTINUATION_UNIT_REJECTED"]


@pytest.mark.parametrize("fragment", [VERSION_ID, CONTINUATION_VERSION_ID])
@pytest.mark.parametrize("affected_columns", [1, 2])
@pytest.mark.parametrize(
    "surface",
    [
        "USD",
        "EUR",
        "eur",
        "Eur",
        "Đơn vị tính: EUR",
        "Đơn vị tính: eur",
        "Triệu đồng và eur",
        "Unit: XYZ",
        "Nghìn đồng",
        "Triệu đồng, %",
        "Triệu đồng ₹",
        "Triệu đồng ₽",
    ],
)
def test_continuation_unexplained_money_header_unit_is_a_veto(
    fragment: str, affected_columns: int, surface: str
) -> None:
    _base, pages, compiled = _continuation_query_fixture()
    table = pages[1][fragment]["sections"][0]["tables"][0]
    # Keep a valid local table unit: an invalid header must still veto it.
    for ordinal, (column, period) in enumerate(
        zip(table["columns"], ("Kỳ này", "Kỳ trước"), strict=True), start=1
    ):
        prefix = [OWNER] if fragment == VERSION_ID else []
        column["header_path_exact"] = [
            *prefix,
            period,
            *([surface] if ordinal <= affected_columns else []),
        ]
    before = copy.deepcopy(pages)
    _adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    assert pages == before


@pytest.mark.parametrize("fragment", [VERSION_ID, CONTINUATION_VERSION_ID])
@pytest.mark.parametrize(
    "unit",
    [
        None,
        "Triệu Đồng Việt Nam",
        "Đơn vị tính: triệu đồng VN",
        "(Triệu VND)",
        "Unit: Million VND",
        "ĐVT: triệu đồng",
    ],
)
def test_continuation_missing_unit_and_bounded_currency_names_remain_source_bound(
    fragment: str, unit: str | None
) -> None:
    _base, pages, compiled = _continuation_query_fixture()
    pages[1][fragment]["sections"][0]["tables"][0]["unit_exact"] = unit
    before = copy.deepcopy(pages)
    _adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == READY
    assert {mapping["unit"] for mapping in trial["mappings"]} == {"MILLION_VND"}
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    assert pages == before


@pytest.mark.parametrize(
    "periods", [("Năm 2026", "Năm 2025"), ("Year 2026", "Year 2025")]
)
@pytest.mark.parametrize("surface", ["Triệu đồng Việt Nam", "Đơn vị tính: Triệu đồng VN"])
def test_continuation_explicit_header_units_preserve_period_parser_authority(
    periods: tuple[str, str], surface: str
) -> None:
    _base, pages, compiled = _continuation_query_fixture()
    for version in (VERSION_ID, CONTINUATION_VERSION_ID):
        table = pages[1][version]["sections"][0]["tables"][0]
        table["unit_exact"] = None
        prefix = [OWNER] if version == VERSION_ID else []
        for column, period in zip(table["columns"], periods, strict=True):
            column["header_path_exact"] = [*prefix, period, surface]
    before = copy.deepcopy(pages)
    _adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == READY
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    assert pages == before


def _roman_quarter_peer_continuation_fixture() -> tuple[
    dict[int, dict[str, dict[str, Any]]], dict[str, Any]
]:
    """A partial employee disclosure ends before the next numbered parent."""

    _base, pages, compiled = _continuation_query_fixture()
    prior = pages[1][VERSION_ID]["sections"][0]["tables"][0]
    receiver = pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]
    prior["rows"] = prior["rows"][:3]
    prior["rows"][2]["label_exact"] = "Trong đó: Chi lương và phụ cấp"
    prior["rows"][2]["hierarchy_path_exact"] = [
        "2. Chi phí nhân viên", "Trong đó: Chi lương và phụ cấp",
    ]
    prior["continuation"] = "NONE"
    receiver["rows"] = [
        _row("3. Chi về tài sản", "20", "15", kind="GROUP"),
        _row(
            "Trong đó: Chi phí khấu hao tài sản cố định", "12", "10",
            path=["3. Chi về tài sản", "Trong đó: Chi phí khấu hao tài sản cố định"],
        ),
        _row("4. Chi cho hoạt động quản lý và công vụ", "15", "12", kind="GROUP"),
        _row(
            "Trong đó: Công tác phí", "4", "3",
            path=["4. Chi cho hoạt động quản lý và công vụ", "Trong đó: Công tác phí"],
        ),
        _row("5. Chi nộp phí bảo hiểm tiền gửi của khách hàng", "5", "4"),
        _row("Cộng", "80", "64", kind="TOTAL"),
    ]
    for table in (prior, receiver):
        table["columns"] = [
            {"header_path_exact": ["Quý II/2026"], "value_kind": "MONEY"},
            {"header_path_exact": ["Quý II/2025"], "value_kind": "MONEY"},
        ]
    return pages, compiled


@pytest.mark.parametrize("quarter", ["I", "II", "III", "IV"])
@pytest.mark.parametrize("sender_marker", ["NONE", "CONTINUES_ON_NEXT_PAGE"])
def test_roman_quarter_continuation_maps_printed_root_and_partial_parent(
    quarter: str, sender_marker: str
) -> None:
    pages, compiled = _roman_quarter_peer_continuation_fixture()
    for version in (VERSION_ID, CONTINUATION_VERSION_ID):
        table = pages[1][version]["sections"][0]["tables"][0]
        for column, year in zip(table["columns"], (2026, 2025), strict=True):
            column["header_path_exact"] = [f"Quý {quarter}/{year}"]
    pages[1][VERSION_ID]["sections"][0]["tables"][0]["continuation"] = sender_marker
    before = copy.deepcopy(pages)
    adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == READY
    assert pages == before
    assert [
        region["physical_page"]
        for region in adapted["candidate_dispositions"][0]["cluster"]["component_regions"]
    ] == [1, 2]
    mappings = {mapping["role"]: mapping for mapping in trial["mappings"]}
    assert [cell["coefficient"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == [80, 64]
    assert [cell["source_text"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == ["80", "64"]
    assert [cell["coefficient"] for cell in mappings["EMPLOYEE_EXPENSE"]["values"]] == [30, 25]
    assert [cell["coefficient"] for cell in mappings["SALARY_ALLOWANCE"]["values"]] == [20, 18]
    assert "OTHER_EMPLOYEE_EXPENSE" not in mappings  # Never backsolve an undisclosed remainder.
    assert mappings["ASSET_EXPENSE"]["source_refs"][0]["locator"]["physical_page"] == 2
    root = mappings["FAMILY_ROOT_TOTAL"]
    assert all(ref["locator"]["physical_page"] == 2 for ref in root["source_refs"])
    receipt = trial["candidates"][0]["closure_receipt"]["operating_expense_adapter_receipt"]
    assert receipt["source_root_authority_veto_receipts"] == []
    assert len(receipt["continuation_projection_receipts"]) == 1
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=adapted, trials=[trial],
        page_json_by_document=pages, compiled_specs=compiled,
    )


@pytest.mark.parametrize("fragment", [VERSION_ID, CONTINUATION_VERSION_ID])
@pytest.mark.parametrize("surface", ["II", "Kỳ này II", "Quý EUR/2026", "Quý II/2026 eur"])
def test_roman_quarter_rule_does_not_allow_bare_or_currency_tokens(
    fragment: str, surface: str
) -> None:
    pages, compiled = _roman_quarter_peer_continuation_fixture()
    table = pages[1][fragment]["sections"][0]["tables"][0]
    table["columns"][0]["header_path_exact"] = [surface]
    _adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        "MISSING_RECEIVER_TABLE", "MISSING_RECEIVER_MARKER", "OUTGOING_RECEIVER",
        "DUPLICATE_PRINTED_ROOT", "ROOT_MISMATCH", "UNIT_CONFLICT",
    ],
)
def test_incomplete_sender_never_substitutes_derived_root_for_printed_total(
    mutation: str,
) -> None:
    pages, compiled = _roman_quarter_peer_continuation_fixture()
    receiver_section = pages[1][CONTINUATION_VERSION_ID]["sections"][0]
    receiver = receiver_section["tables"][0]
    if mutation == "MISSING_RECEIVER_TABLE":
        receiver_section["tables"] = []
    elif mutation == "MISSING_RECEIVER_MARKER":
        receiver["continuation"] = "NONE"
    elif mutation == "OUTGOING_RECEIVER":
        receiver["continuation"] = "BOTH"
    elif mutation == "DUPLICATE_PRINTED_ROOT":
        receiver["rows"].append(copy.deepcopy(receiver["rows"][-1]))
    elif mutation == "ROOT_MISMATCH":
        receiver["rows"][-1]["values_exact"] = ["100", "99"]
    else:
        receiver["unit_exact"] = "VND"
    before = copy.deepcopy(pages)
    adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    assert pages == before
    validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=adapted, trials=[trial],
        page_json_by_document=pages, compiled_specs=compiled,
    )
    if mutation != "ROOT_MISMATCH":
        candidate = trial["candidates"][0]
        assert "OPERATING_EXPENSE_REQUIRED_PRINTED_ROOT_IS_ONLY_DERIVED" in candidate["reasons"]
        receipts = candidate["closure_receipt"]["operating_expense_adapter_receipt"][
            "source_root_authority_veto_receipts"
        ]
        assert len(receipts) == 1
        rejected_root = receipts[0]["rejected_root_mappings"][0]
        assert [cell["coefficient"] for cell in rejected_root["values"]] == [40, 33]
        assert all(cell["source_text"] is None for cell in rejected_root["values"])
        assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False


@pytest.mark.parametrize("policy", ["OPTIONAL", "REQUIRED_SOURCE_VISIBLE_EXACT_ROOT"])
@pytest.mark.parametrize("marker", ["NONE", "CONTINUES_ON_NEXT_PAGE"])
def test_source_root_guard_distinguishes_optional_complete_sum_from_open_population(
    policy: str, marker: str
) -> None:
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        _row("Chi phí cho nhân viên", "30", "25"),
        _row("Chi về tài sản", "20", "15"),
    ]
    page = _operating_page(rows)
    page["sections"][0]["tables"][0]["continuation"] = marker
    compiled = _compiled()
    compiled["family_root_requirement"] = policy
    compiled["evaluation"]["family_root_requirement"] = policy
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled,
    )
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"], page_json_by_version={VERSION_ID: page},
        selected_page_axis=[], compiled_specs=compiled, query_receipt=receipt,
    )
    if policy == "OPTIONAL" and marker == "NONE":
        assert candidate["status"] == READY
        root = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL")
        assert root["state"] == "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
        assert all(cell["source_text"] is None for cell in root["values"])
    else:
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
        if marker != "NONE":
            assert "OPERATING_EXPENSE_SOURCE_CONTINUATION_NOT_CLOSED" in candidate["reasons"]
    validate_gemini_json_operating_expense_candidate_replay_v1(
        candidate, regions=cluster["component_regions"], page_json_by_version={VERSION_ID: page},
        selected_page_axis=[], compiled_specs=compiled, query_receipt=receipt,
    )


@pytest.mark.parametrize("mutation", ["DROP_RECEIPT", "FORGE_READY", "SOURCE_RECEIVER_DRIFT"])
def test_required_printed_root_veto_is_source_bound_and_replayed(mutation: str) -> None:
    pages, compiled = _roman_quarter_peer_continuation_fixture()
    receiver = pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]
    receiver["continuation"] = "NONE"
    adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    candidate = trial["candidates"][0]
    assert candidate["status"] == UNRESOLVED
    cluster = adapted["candidate_dispositions"][0]["cluster"]
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    forged = copy.deepcopy(candidate)
    adapter = forged["closure_receipt"]["operating_expense_adapter_receipt"]
    if mutation == "DROP_RECEIPT":
        adapter["source_root_authority_veto_receipts"] = []
    elif mutation == "FORGE_READY":
        forged["status"] = READY
        forged["reasons"] = []
        forged["mappings"] = adapter["source_root_authority_veto_receipts"][0]["rejected_root_mappings"]
        adapter["source_root_authority_veto_receipts"] = []
    else:
        receiver["rows"][-1]["values_exact"][0] = "81"
    material = {key: value for key, value in adapter.items() if key != "adapter_receipt_id"}
    adapter["adapter_receipt_id"] = "gjoefav1:receipt:" + canonical_json_sha256_v1(material)
    material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error, match="candidate replay drifted"):
        validate_gemini_json_operating_expense_candidate_replay_v1(
            forged, regions=cluster["component_regions"], page_json_by_version=pages[1],
            selected_page_axis=adapted["selected_page_axis"], compiled_specs=compiled,
            query_receipt=receipt,
        )


@pytest.mark.parametrize("marker", ["CONTINUES_ON_NEXT_PAGE", "BOTH"])
def test_printed_total_does_not_close_an_explicit_outgoing_fragment(marker: str) -> None:
    page = _operating_page()
    page["sections"][0]["tables"][0]["continuation"] = marker
    candidate, _cluster_value, _receipt = _evaluate_adapter(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["OPERATING_EXPENSE_SOURCE_CONTINUATION_NOT_CLOSED"]
    veto = candidate["closure_receipt"]["operating_expense_adapter_receipt"][
        "source_root_authority_veto_receipts"
    ][0]
    assert veto["open_evaluation_fragments"][0]["continuation"] == marker
    assert all(cell["source_text"] is not None for cell in veto["rejected_root_mappings"][0]["values"])


def test_primary_root_page_map_order_preserves_sealed_query_and_candidate_bytes() -> None:
    base, pages, compiled = _titleless_primary_query_fixture()
    # The hash sort is deliberately opposite to selected-source order.
    extra_version = "gfpstorev1:json:" + "a" * 64
    pages[1][extra_version] = copy.deepcopy(pages[1][PRIMARY_VERSION_ID])
    selected_page_axis = [
        *base["selected_page_axis"],
        {
            **base["selected_page_axis"][0],
            "page_json_version_id": extra_version,
            "physical_page": 3,
            "selected_page_ordinal": 3,
        },
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=base["selected_document_axis"],
        selected_page_axis=selected_page_axis,
        document_clusters=[item["cluster"] for item in base["candidate_dispositions"]],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    outputs = []
    for source_pages in (pages, {1: dict(reversed(list(pages[1].items())))}):
        adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
            base_indexed_query_evidence=base,
            page_json_by_document=source_pages,
            compiled_specs=compiled,
        )
        trials = build_gemini_json_operating_expense_trials_v1(
            indexed_query_evidence=adapted,
            page_json_by_document=source_pages,
            compiled_specs=compiled,
        )
        assert trials[0]["status"] == READY
        evidence = adapted["candidate_dispositions"][0]["cluster"][
            "operating_expense_titleless_primary_region_recovery_receipt"
        ]["selected_region_evidence"]
        assert [root["locator"]["physical_page"] for root in evidence["matched_primary_roots"]] == [
            1, 3
        ]
        owner_evidence = trials[0]["candidates"][0]["closure_receipt"][
            "document_unit_context"
        ]["owner_row_evidence"]
        assert [item["page_json_version_id"] for item in owner_evidence] == [
            PRIMARY_VERSION_ID, extra_version
        ]
        assert {
            (ref["locator"]["physical_page"], ref["locator"]["selected_page_ordinal"])
            for mapping in trials[0]["mappings"]
            for ref in mapping["source_refs"]
        } == {(2, 2)}
        outputs.append((adapted, trials))
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize(
    "mutation",
    ["DUPLICATE_VERSION", "DUPLICATE_ORDINAL", "GAPPED_ORDINAL", "REGION_DRIFT", "MISSING_PAGE"],
)
def test_page_order_frontier_metadata_tamper_fails_closed(mutation: str) -> None:
    base, pages, compiled = _titleless_primary_query_fixture()
    adapted = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    regions = adapted["candidate_dispositions"][0]["cluster"]["component_regions"]
    selected = copy.deepcopy(base["selected_page_axis"])
    if mutation == "DUPLICATE_VERSION":
        selected.append(copy.deepcopy(selected[0]))
    elif mutation == "DUPLICATE_ORDINAL":
        selected[1]["selected_page_ordinal"] = selected[0]["selected_page_ordinal"]
    elif mutation == "GAPPED_ORDINAL":
        selected[0]["selected_page_ordinal"] = 3
    elif mutation == "REGION_DRIFT":
        selected[0]["selected_page_ordinal"], selected[1]["selected_page_ordinal"] = 2, 1
    else:
        pages[1].pop(PRIMARY_VERSION_ID)
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error, match="page|source order"):
        evaluate_gemini_json_operating_expense_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[1],
            selected_page_axis=selected,
            compiled_specs=compiled,
            query_receipt=receipt,
        )


def test_unitless_sender_can_inherit_only_observed_receiver_header_unit() -> None:
    _base, pages, compiled = _continuation_query_fixture()
    for version in (VERSION_ID, CONTINUATION_VERSION_ID):
        pages[1][version]["sections"][0]["tables"][0]["unit_exact"] = None
    receiver = pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]
    for column, period in zip(receiver["columns"], ("Kỳ này", "Kỳ trước"), strict=True):
        column["header_path_exact"] = [period, "Triệu đồng Việt Nam"]
    before = copy.deepcopy(pages)
    _adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == READY
    projection = trial["candidates"][0]["closure_receipt"]["operating_expense_adapter_receipt"][
        "continuation_projection_receipts"
    ][0]
    assert projection["prior_unit"] is None
    assert projection["receiver_unit"]["canonical_unit"] == "MILLION_VND"
    assert projection["receiver_unit"]["evidence"]["source"] == (
        "LOCAL_UNIFORM_ALL_MONEY_COLUMN_UNITS"
    )
    assert pages == before


def test_valid_unit_never_repairs_an_unsupported_period_axis() -> None:
    _base, pages, compiled = _continuation_query_fixture()
    receiver = pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]
    for column, period in zip(
        receiver["columns"], ("Current period", "Previous period"), strict=True
    ):
        column["header_path_exact"] = [period, "Triệu đồng"]
    _adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []


def _internal_owner_invalid_unit_query() -> tuple[
    dict[str, Any], dict[int, dict[str, dict[str, Any]]], dict[str, Any], dict[str, Any]
]:
    _base, pages, compiled = _internal_owner_continuation_query_fixture()
    pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]["unit_exact"] = "USD"
    indexed, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    return indexed, pages, compiled, trial


def _reseal_family_query_cluster(
    indexed: dict[str, Any], compiled: dict[str, Any]
) -> dict[str, Any]:
    clusters = []
    for item in indexed["candidate_dispositions"]:
        cluster = copy.deepcopy(item["cluster"])
        material = {key: value for key, value in cluster.items() if key != "cluster_id"}
        cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
        clusters.append(cluster)
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=indexed["selected_document_axis"],
        selected_page_axis=indexed["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def test_internal_owner_unit_rejection_replays_exact_source_and_reverse_page_order() -> None:
    indexed, pages, compiled, trial = _internal_owner_invalid_unit_query()
    before = copy.deepcopy(pages)
    assert trial["status"] == UNRESOLVED
    assert trial["candidates"] == []
    assert trial["mappings"] == []
    assert validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed,
        trials=[trial],
        page_json_by_document=pages,
        compiled_specs=compiled,
    ) == [trial]
    reversed_pages = {1: dict(reversed(list(pages[1].items())))}
    replayed_indexed, replayed_trial = _adapt_continuation_pages_for_unit_test(
        reversed_pages, compiled
    )
    assert (indexed, trial) == (replayed_indexed, replayed_trial)
    assert pages == before


def test_internal_owner_rejection_partition_is_byte_identical_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base, template_pages, compiled = _internal_owner_continuation_query_fixture()
    template_pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0][
        "unit_exact"
    ] = "USD"
    documents = []
    selected_pages = []
    clusters = []
    pages_by_document = {}
    identities = (
        ("a", "c", ("b", "e")),
        ("3", "4", ("5", "6")),
    )
    for document_ordinal, (document_char, source_char, version_chars) in enumerate(
        identities, start=1
    ):
        document = {
            "document_id": "gfpstorev1:document:" + document_char * 64,
            "document_ordinal": document_ordinal,
            "source_logical_name": f"fixture-{document_ordinal}.pdf",
            "source_sha256": source_char * 64,
        }
        records = []
        pages_by_version = {}
        for selected_page_ordinal, (template_version, version_char) in enumerate(
            zip((VERSION_ID, CONTINUATION_VERSION_ID), version_chars, strict=True),
            start=1,
        ):
            page = copy.deepcopy(template_pages[1][template_version])
            version_id = "gfpstorev1:json:" + version_char * 64
            page_axis = {
                **document,
                "page_json_version_id": version_id,
                "physical_page": selected_page_ordinal,
                "selected_page_ordinal": selected_page_ordinal,
            }
            records.append({**page_axis, "page_json": page})
            selected_pages.append(page_axis)
            pages_by_version[version_id] = page
        documents.append(document)
        pages_by_document[document_ordinal] = pages_by_version
        clusters.append(
            coalesce_gemini_json_multitable_hierarchical_document_v1(
                page_records=records, compiled_specs=compiled
            )
        )
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_pages,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    original = operating_expense_adapter._internal_owner_rejection_axes
    observed_local_axes = []

    def local_axis_spy(**kwargs: Any) -> dict[str, list[dict[str, Any]]]:
        document_ordinal = kwargs["document"]["document_ordinal"]
        observed_local_axes.append(
            (
                document_ordinal,
                [item["document_ordinal"] for item in kwargs["selected_page_axis"]],
            )
        )
        return original(**kwargs)

    monkeypatch.setattr(
        operating_expense_adapter, "_internal_owner_rejection_axes", local_axis_spy
    )
    optimized_indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )
    assert observed_local_axes == [(1, [1, 1]), (2, [2, 2])]
    observed_local_axes.clear()
    optimized_trials = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=optimized_indexed,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )
    assert observed_local_axes == [(1, [1, 1]), (2, [2, 2])]

    def legacy_global_scan(**kwargs: Any) -> dict[str, list[dict[str, Any]]]:
        return original(**{**kwargs, "selected_page_axis": base["selected_page_axis"]})

    monkeypatch.setattr(
        operating_expense_adapter, "_internal_owner_rejection_axes", legacy_global_scan
    )
    legacy_indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )
    legacy_trials = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=legacy_indexed,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )

    def canonical_bytes(value: Any) -> bytes:
        return json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode()

    assert canonical_bytes(optimized_indexed) == canonical_bytes(legacy_indexed)
    assert canonical_bytes(optimized_trials) == canonical_bytes(legacy_trials)

    forged = copy.deepcopy(optimized_indexed)
    del forged["candidate_dispositions"][1]["cluster"][
        "operating_expense_internal_owner_unit_rejection_receipts"
    ]
    forged = _reseal_family_query_cluster(forged, compiled)
    monkeypatch.setattr(
        operating_expense_adapter, "_internal_owner_rejection_axes", original
    )
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="unit-rejection source replay drifted",
    ):
        build_gemini_json_operating_expense_trials_v1(
            indexed_query_evidence=forged,
            page_json_by_document=pages_by_document,
            compiled_specs=compiled,
        )


@pytest.mark.parametrize(
    "mutation",
    ["UNIT_RECEIPT", "PAGE_VERSION", "OWNER_ROW", "REMOVE_RECEIPT", "FORGE_NOT_OBSERVED"],
)
def test_internal_owner_unit_rejection_rejects_self_resealed_query_tamper(mutation: str) -> None:
    indexed, pages, compiled, _trial = _internal_owner_invalid_unit_query()
    cluster = indexed["candidate_dispositions"][0]["cluster"]
    field = "operating_expense_internal_owner_unit_rejection_receipts"
    receipt = cluster[field][0]
    if mutation == "REMOVE_RECEIPT":
        del cluster[field]
    elif mutation == "FORGE_NOT_OBSERVED":
        del cluster[field]
        cluster["status"] = NOT_OBSERVED
        cluster["reasons"] = []
    else:
        if mutation == "UNIT_RECEIPT":
            receipt["unit_frontiers"][1]["raw_unit_exact"] = "VND"
        elif mutation == "PAGE_VERSION":
            receipt["original_regions"][1]["page_json_version_id"] = PRIMARY_VERSION_ID
        else:
            receipt["owner_proof"]["owner_row"]["label_exact"] = "Đơn vị tính: USD"
        receipt_material = {key: value for key, value in receipt.items() if key != "receipt_id"}
        receipt["receipt_id"] = "gjoefav1:internal-owner-unit-rejection:" + canonical_json_sha256_v1(
            receipt_material
        )
    forged = _reseal_family_query_cluster(indexed, compiled)
    with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error, match="unit-rejection source replay"):
        build_gemini_json_operating_expense_trials_v1(
            indexed_query_evidence=forged,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )


@pytest.mark.parametrize("mutation", ["STILL_INVALID_UNIT", "OWNER_REMOVED", "SOURCE_VALUE"])
def test_internal_owner_unit_rejection_rejects_source_drift(mutation: str) -> None:
    indexed, pages, compiled, trial = _internal_owner_invalid_unit_query()
    prior = pages[1][VERSION_ID]["sections"][0]["tables"][0]
    receiver = pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]
    if mutation == "STILL_INVALID_UNIT":
        receiver["unit_exact"] = "EUR"
    elif mutation == "OWNER_REMOVED":
        prior["rows"][3]["label_exact"] = "Các khoản khác"
        prior["rows"][3]["hierarchy_path_exact"] = ["Các khoản khác"]
    else:
        receiver["rows"][0]["values_exact"][0] = "6"
    with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error, match="unit-rejection source replay"):
        validate_gemini_json_operating_expense_replay_v1(
            indexed_query_evidence=indexed,
            trials=[trial],
            page_json_by_document=pages,
            compiled_specs=compiled,
        )


@pytest.mark.parametrize("title", ["Các khoản khác", "Đơn vị tính: USD", "Chi phí hoạt động dịch vụ"])
def test_invalid_unit_without_exact_internal_owner_preserves_not_observed(title: str) -> None:
    _base, pages, compiled = _internal_owner_continuation_query_fixture()
    prior = pages[1][VERSION_ID]["sections"][0]["tables"][0]
    owner = prior["rows"][3]
    old_owner = owner["label_exact"]
    owner["label_exact"] = title
    for row in prior["rows"]:
        row["hierarchy_path_exact"] = [
            title if item == old_owner else item for item in row["hierarchy_path_exact"]
        ]
    pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0]["unit_exact"] = "USD"
    indexed, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert trial["status"] == NOT_OBSERVED
    assert trial["mappings"] == []
    assert "operating_expense_internal_owner_unit_rejection_receipts" not in (
        indexed["candidate_dispositions"][0]["cluster"]
    )


def test_pdf_visible_dash_repair_is_cell_local_source_bound_and_replays() -> None:
    rows = _base_rows()
    rows[12]["values_exact"][1] = None
    rows[-1]["values_exact"][1] = "64"
    page = _operating_page(rows)
    before = copy.deepcopy(page)
    compiled = _adapter_compiled(_source_repair_spec())
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[
            {
                "document_ordinal": 1,
                "page_json_version_id": VERSION_ID,
                "physical_page": 1,
                "selected_page_ordinal": 1,
            }
        ],
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert page == before
    adapter = candidate["closure_receipt"]["operating_expense_adapter_receipt"]
    assert len(adapter["source_repair_receipts"]) == 1
    repaired = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_ASSET_PROVISION"
    )
    assert repaired["values"] == [
        {"coefficient": 3, "source_text": "3", "state": "RAW_SIGNED_INTEGER"},
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
    ]
    assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0
    validate_gemini_json_operating_expense_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[
            {
                "document_ordinal": 1,
                "page_json_version_id": VERSION_ID,
                "physical_page": 1,
                "selected_page_ordinal": 1,
            }
        ],
        compiled_specs=compiled,
        query_receipt=receipt,
    )


def test_pdf_visible_dash_can_replace_only_authenticated_false_numeric_cell() -> None:
    rows = _base_rows()
    rows[12]["values_exact"][1] = "3"
    rows[-1]["values_exact"][1] = "64"
    page = _operating_page(rows)
    before = copy.deepcopy(page)
    source_repairs = _source_repair_spec()
    repair = source_repairs["repairs"][0]
    repair["before_exact"] = "3"
    repair["repair_kind"] = "MONEY_CELL_FALSE_NUMERIC_PDF_VISIBLE_DASH"
    repair.pop("repair_id")
    repair["repair_id"] = "gjoefav1:source-repair:" + canonical_json_sha256_v1(repair)
    source_repairs["repair_axis_sha256"] = canonical_json_sha256_v1(source_repairs["repairs"])
    compiled = _adapter_compiled(source_repairs)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_operating_expense_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[
            {
                "document_ordinal": 1,
                "page_json_version_id": VERSION_ID,
                "physical_page": 1,
                "selected_page_ordinal": 1,
            }
        ],
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert page == before
    repaired = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_ASSET_PROVISION"
    )
    assert repaired["values"][1] == {
        "coefficient": 0,
        "source_text": "-",
        "state": "DASH_ZERO",
    }
    assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0


def test_source_repair_tamper_and_before_image_drift_fail_closed() -> None:
    source_repairs = _source_repair_spec()
    source_repairs["repairs"][0]["crop_evidence"]["rgb_sha256"] = "2" * 64
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="source-repair identity drifted",
    ):
        _adapter_compiled(source_repairs)

    compiled = _adapter_compiled(_source_repair_spec())
    page = _operating_page()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="before-image drifted",
    ):
        evaluate_gemini_json_operating_expense_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            selected_page_axis=[],
            compiled_specs=compiled,
            query_receipt=receipt,
        )


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


def test_source_row_coverage_is_exhaustive_deterministic_and_sealed() -> None:
    indexed, trials, pages, compiled = _source_row_coverage_inputs(
        _operating_page()
    )
    receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    replayed = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert receipt == replayed
    assert set(receipt) == {
        "candidate_table_total_disposition_counts",
        "candidate_table_total_row_axis",
        "candidate_table_total_row_axis_sha256",
        "family_id",
        "format_version",
        "raw_target_like_disposition_counts",
        "raw_target_like_row_axis",
        "raw_target_like_row_axis_sha256",
        "receipt_id",
        "source_row_disposition_counts",
        "source_row_axis",
        "source_row_axis_sha256",
        "violation_axis",
        "violation_count",
    }
    assert receipt["family_id"] == "OPERATING_EXPENSE"
    assert receipt["format_version"] == "OPERATING_EXPENSE_SOURCE_ROW_COVERAGE_V1"
    assert receipt["violation_axis"] == []
    assert receipt["violation_count"] == 0
    assert receipt["source_row_disposition_counts"] == {
        "EQUATION_CONSUMED_DECLARED_SOURCE_ONLY_ROLE_ROW": 1,
        "MAPPED_EXACT_SOURCE_ROLE_ROW": 12,
    }
    assert receipt["candidate_table_total_disposition_counts"] == {
        "MAPPED_EXACT_TERMINAL_FAMILY_TOTAL": 1
    }
    assert receipt["source_row_axis_sha256"] == canonical_json_sha256_v1(
        receipt["source_row_axis"]
    )
    assert receipt[
        "candidate_table_total_row_axis_sha256"
    ] == canonical_json_sha256_v1(receipt["candidate_table_total_row_axis"])
    assert receipt["raw_target_like_row_axis_sha256"] == canonical_json_sha256_v1(
        receipt["raw_target_like_row_axis"]
    )
    material = {key: value for key, value in receipt.items() if key != "receipt_id"}
    assert receipt["receipt_id"] == (
        "gjoefav1:source-row-coverage:" + canonical_json_sha256_v1(material)
    )
    required_locator_fields = {
        "coverage",
        "document_ordinal",
        "hierarchy_path_exact",
        "label_exact",
        "page_json_version_id",
        "physical_page",
        "report_norm_id",
        "role",
        "row_id",
        "row_ordinal",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
        "values_exact",
    }
    assert all(
        required_locator_fields <= set(item)
        for axis_name in (
            "source_row_axis",
            "candidate_table_total_row_axis",
            "raw_target_like_row_axis",
        )
        for item in receipt[axis_name]
    )

    attacked = copy.deepcopy(receipt)
    attacked["source_row_axis"][0]["label_exact"] = "tampered"
    attacked_material = {
        key: value for key, value in attacked.items() if key != "receipt_id"
    }
    assert attacked["receipt_id"] != (
        "gjoefav1:source-row-coverage:"
        + canonical_json_sha256_v1(attacked_material)
    )


def test_source_row_coverage_types_all_blank_primary_and_outside_rows() -> None:
    rows = _base_rows()
    rows.insert(
        -1,
        _row("Chi phí dự phòng giảm giá đầu tư dài hạn", None, None),
    )
    indexed, trials, pages, compiled = _source_row_coverage_inputs(
        _operating_page(rows)
    )
    blank_receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert any(
        item["role"] == "GENERIC_PROVISION_SOURCE_ONLY"
        and item["coverage"]
        == "ALL_BLANK_VALIDATION_ROLE_OMISSION_SOURCE_ONLY"
        for item in blank_receipt["source_row_axis"]
    )

    base, pages, compiled = _titleless_primary_query_fixture()
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    primary_receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert any(
        item["coverage"]
        == "PRIMARY_STATEMENT_FAMILY_ROOT_CONTROL_SOURCE_ONLY"
        and item["role"] == "OPERATING_EXPENSE"
        for item in primary_receipt["source_row_axis"]
    )

    base, pages, compiled = _owner_region_query_fixture()
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    outside_receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert any(
        item["coverage"]
        == "OUTSIDE_SELECTED_OPERATING_EXPENSE_CONTEXT_SOURCE_ONLY"
        for item in outside_receipt["source_row_axis"]
    )


def test_source_row_coverage_fails_closed_on_unknown_selected_role() -> None:
    rows = _base_rows()
    rows.insert(-1, _row("Chi phí lượng tử chưa khai báo", "1", "1"))
    rows[-1]["values_exact"] = ["84", "67"]
    indexed, trials, pages, compiled = _source_row_coverage_inputs(
        _operating_page(rows)
    )
    receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
        fail_on_violation=False,
    )
    assert any(
        item["label_exact"] == "Chi phí lượng tử chưa khai báo"
        and item["coverage"]
        == "VIOLATION_UNCLASSIFIED_VISIBLE_OPERATING_EXPENSE_ROW"
        for item in receipt["violation_axis"]
    )
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="source-row coverage has .* violation",
    ):
        build_operating_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=trials,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )


def test_source_row_coverage_fails_closed_on_unmapped_selected_root() -> None:
    rows = _base_rows()
    rows[-1] = _row(OWNER, "83", "66", kind="TOTAL")
    page = _operating_page(rows)
    indexed, trials, pages, compiled = _source_row_coverage_inputs(page)
    attacked = copy.deepcopy(trials)
    attacked[0]["mappings"] = [
        mapping
        for mapping in attacked[0]["mappings"]
        if mapping["role"] != "FAMILY_ROOT_TOTAL"
    ]
    receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=attacked,
        page_json_by_document=pages,
        compiled_specs=compiled,
        fail_on_violation=False,
    )
    assert {
        item["coverage"] for item in receipt["violation_axis"]
    } == {
        "VIOLATION_UNMAPPED_SELECTED_FAMILY_ROOT_ROW",
        "VIOLATION_UNMAPPED_VISIBLE_TERMINAL_TOTAL",
    }


def _alignment_tables(pages):
    return tuple(
        pages[1][version]["sections"][0]["tables"][0]
        for version in (VERSION_ID, CONTINUATION_VERSION_ID)
    )


def _alignment_headers(table, current, comparative):
    for column, surface in zip(table["columns"], (current, comparative), strict=True):
        column["header_path_exact"] = [surface]


def _run_alignment_fixture(pages, compiled):
    before = copy.deepcopy(pages)
    adapted, trial = _adapt_continuation_pages_for_unit_test(pages, compiled)
    assert pages == before
    operating_expense_adapter.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=adapted, trials=[trial],
        page_json_by_document=pages, compiled_specs=compiled,
    )
    assert pages == before
    return adapted, trial


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("conflict", ["END_DATE", "RANGE_START", "ROMAN_QUARTER", "PRECISION"])
def test_explicit_period_conflict_is_unresolved_not_absent(layout, conflict):
    source_fixture = (
        _continuation_query_fixture
        if layout == "COMPLETE_OWNER"
        else _internal_owner_continuation_query_fixture
    )
    _base, pages, compiled = source_fixture()
    prior, receiver = _alignment_tables(pages)
    if conflict == "END_DATE":
        _alignment_headers(prior, "30/06/2026", "30/06/2025")
        _alignment_headers(receiver, "31/03/2026", "31/03/2025")
    elif conflict == "RANGE_START":
        _alignment_headers(prior, "Từ 01/04/2026 đến 30/06/2026", "Từ 01/04/2025 đến 30/06/2025")
        _alignment_headers(receiver, "Từ 01/01/2026 đến 30/06/2026", "Từ 01/01/2025 đến 30/06/2025")
    elif conflict == "ROMAN_QUARTER":
        _alignment_headers(prior, "Quý II/2026", "Quý II/2025")
        _alignment_headers(receiver, "Quý III/2026", "Quý III/2025")
    else:
        _alignment_headers(prior, "Từ 01/01/2026 đến 30/06/2026", "Từ 01/01/2025 đến 30/06/2025")
        _alignment_headers(receiver, "30/06/2026", "30/06/2025")
    adapted, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    if layout == "INTERNAL_OWNER":
        cluster = adapted["candidate_dispositions"][0]["cluster"]
        assert cluster["status"] == UNRESOLVED
        assert cluster["operating_expense_internal_owner_period_rejection_receipts"]


def _reverse_alignment_columns_and_values(table, *, keep_headers_blank=False):
    if not keep_headers_blank:
        table["columns"].reverse()
    for row in table["rows"]:
        row["values_exact"].reverse()


def _alignment_root_with_exact_source_ref(trial, pages, expected=(80, 64)):
    assert trial["status"] == READY
    root = next(mapping for mapping in trial["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == list(expected)
    # These controlled fixtures use direct observations, not aggregate-role
    # sums; check every mapped role so a symmetric root cannot hide child drift.
    for mapping in trial["mappings"]:
        for ref in mapping["source_refs"]:
            locator = ref["locator"]
            page = pages[1][locator["page_json_version_id"]]
            _section, table = operating_expense_adapter._source_table(
                page, section_id=locator["section_id"], table_id=locator["table_id"]
            )
            row = table["rows"][ref["row_ordinal"] - 1]
            source_cells = [row["values_exact"][ordinal - 1] for ordinal in ref["money_column_ordinals"]]
            assert source_cells == [cell["source_text"] for cell in mapping["values"]]
    return root


@pytest.mark.parametrize(
    "shape",
    ["RECEIVER", "SENDER", "BOTH", "REVERSED_SENDER_BLANK_RECEIVER", "RECEIVER_WITH_TEXT_COLUMN"],
)
def test_semantic_permutation_preserves_values_and_exact_source_columns(shape):
    _base, pages, compiled = _continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    _alignment_headers(prior, "Kỳ này", "Kỳ trước")
    if shape != "REVERSED_SENDER_BLANK_RECEIVER":
        _alignment_headers(receiver, "Kỳ này", "Kỳ trước")
    if shape in {"SENDER", "BOTH", "REVERSED_SENDER_BLANK_RECEIVER"}:
        _reverse_alignment_columns_and_values(prior)
    if shape in {"RECEIVER", "BOTH", "RECEIVER_WITH_TEXT_COLUMN"}:
        _reverse_alignment_columns_and_values(receiver)
    if shape == "REVERSED_SENDER_BLANK_RECEIVER":
        _reverse_alignment_columns_and_values(receiver, keep_headers_blank=True)
    if shape == "RECEIVER_WITH_TEXT_COLUMN":
        receiver["columns"].insert(0, {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"})
        for row in receiver["rows"]:
            row["values_exact"].insert(0, None)
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


def test_header_reversal_without_values_cannot_be_ignored_for_arithmetic():
    _base, pages, compiled = _continuation_query_fixture()
    _prior, receiver = _alignment_tables(pages)
    _alignment_headers(receiver, "Kỳ trước", "Kỳ này")
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []


def test_blank_source_stays_blank_after_semantic_permutation():
    _base, pages, compiled = _continuation_query_fixture()
    _prior, receiver = _alignment_tables(pages)
    _alignment_headers(receiver, "Kỳ này", "Kỳ trước")
    receiver["rows"][-2]["values_exact"][0] = None
    _reverse_alignment_columns_and_values(receiver)
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)
    deposit = next(mapping for mapping in trial["mappings"] if mapping["role"] == "DEPOSIT_INSURANCE_EXPENSE")
    assert deposit["values"][0] == {
        "coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL",
    }


def test_internal_owner_duplicate_receiver_semantic_lanes_are_unresolved():
    _base, pages, compiled = _internal_owner_continuation_query_fixture()
    _prior, receiver = _alignment_tables(pages)
    _alignment_headers(receiver, "Kỳ này", "Kỳ này")
    adapted, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    assert adapted["candidate_dispositions"][0]["cluster"]["status"] == UNRESOLVED


def test_generic_nonowner_remains_not_observed_despite_period_conflict():
    _base, pages, compiled = _internal_owner_continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    prior["rows"][3]["label_exact"] = "Thông tin không thuộc chi phí hoạt động"
    prior["rows"][3]["hierarchy_path_exact"] = [prior["rows"][3]["label_exact"]]
    _alignment_headers(prior, "30/06/2026", "30/06/2025")
    _alignment_headers(receiver, "31/03/2026", "31/03/2025")
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == NOT_OBSERVED
    assert trial["mappings"] == []


@pytest.mark.parametrize(
    ("prior_headers", "receiver_headers"),
    [
        (("30/06/2026", "30/06/2025"), ("30/06/2026", "30/06/2025")),
        (
            ("Từ 01/01/2026 đến 30/06/2026", "Từ 01/01/2025 đến 30/06/2025"),
            ("Từ 01/01/2026 đến 30/06/2026", "Từ 01/01/2025 đến 30/06/2025"),
        ),
        (("Quý II/2026", "Quý II/2025"), ("Quý 2/2026", "Quý 2/2025")),
        (("6 tháng năm 2026", "6 tháng năm 2025"), ("6 tháng năm 2026", "6 tháng năm 2025")),
        (
            ("Lũy kế quý II năm 2026", "Lũy kế quý II năm 2025"),
            ("Lũy kế quý 2 năm 2026", "Lũy kế quý 2 năm 2025"),
        ),
    ],
)
def test_continuation_equivalent_source_period_and_qualifier_axes_map(prior_headers, receiver_headers):
    _base, pages, compiled = _continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    _alignment_headers(prior, *prior_headers)
    _alignment_headers(receiver, *receiver_headers)
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


@pytest.mark.parametrize(
    ("sender", "receiver"),
    [
        ("Quý II năm {year}", "Lũy kế quý II năm {year}"),
        ("3 tháng năm {year}", "6 tháng năm {year}"),
        ("Quý II năm {year}", "Năm {year}"),
        ("Quý II năm {year}", "Quý II và quý III năm {year}"),
        ("Quý II năm {year}", "Quý 5 năm {year}"),
    ],
)
def test_one_lane_conflicting_or_invalid_duration_qualifier_is_a_veto(sender, receiver):
    _base, pages, compiled = _continuation_query_fixture()
    prior, receiving = _alignment_tables(pages)
    _alignment_headers(prior, sender.format(year=2026), sender.format(year=2025))
    _alignment_headers(receiving, receiver.format(year=2026), sender.format(year=2025))
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []


@pytest.mark.parametrize("sender_text_position", [0, 1, 2])
@pytest.mark.parametrize("receiver_text_position", [0, 1, 2])
def test_reversed_receiver_with_nonmoney_columns_keeps_semantic_source_identity(
    sender_text_position, receiver_text_position
):
    _base, pages, compiled = _continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    _alignment_headers(receiver, "Kỳ này", "Kỳ trước")
    _reverse_alignment_columns_and_values(receiver)
    for table, position in ((prior, sender_text_position), (receiver, receiver_text_position)):
        table["columns"].insert(position, {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"})
        for row in table["rows"]:
            row["values_exact"].insert(position, None)
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


def test_symmetric_parent_totals_do_not_hide_asymmetric_child_column_order():
    _base, pages, compiled = _continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    prior["rows"][0]["values_exact"] = ["10", "10"]
    prior["rows"][1]["values_exact"] = ["30", "30"]
    prior["rows"][3]["values_exact"] = ["10", "12"]
    prior["rows"][4]["values_exact"] = ["20", "20"]
    prior["rows"][6]["values_exact"] = ["8", "10"]
    prior["rows"][7]["values_exact"] = ["15", "15"]
    travel = prior["rows"].pop()
    travel["hierarchy_path_exact"] = [travel["label_exact"]]
    receiver["rows"][0]["values_exact"] = ["4", "5"]
    receiver["rows"][1]["values_exact"] = ["3", "3"]
    receiver["rows"][-2]["values_exact"] = ["5", "5"]
    receiver["rows"][-1]["values_exact"] = ["80", "80"]
    receiver["rows"].insert(0, travel)
    _alignment_headers(receiver, "Kỳ này", "Kỳ trước")
    _reverse_alignment_columns_and_values(receiver)
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages, expected=(80, 80))
    mapped_travel = next(mapping for mapping in trial["mappings"] if mapping["role"] == "TRAVEL_EXPENSE")
    assert [cell["coefficient"] for cell in mapped_travel["values"]] == [4, 3]


def test_legacy_blank_receiver_projection_restores_reversed_source_columns(monkeypatch):
    _base, pages, compiled = _continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    _reverse_alignment_columns_and_values(prior)
    _reverse_alignment_columns_and_values(receiver, keep_headers_blank=True)
    # Exercise the independently retained blank-header fallback, rather than
    # letting the broader complete-owner branch shadow it in this fixture.
    monkeypatch.setattr(operating_expense_adapter, "_complete_owner_continuation_projection", lambda **_kwargs: None)
    _adapted, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)
    projection = trial["candidates"][0]["closure_receipt"]["operating_expense_adapter_receipt"][
        "continuation_projection_receipts"
    ][0]
    assert "boundary_ordinal" in projection
    assert projection["period_alignment_receipt"]["receiver_money_column_ordinals"] == [2, 1]


@pytest.mark.parametrize("fragment", [VERSION_ID, CONTINUATION_VERSION_ID])
def test_internal_owner_invalid_period_in_either_fragment_is_typed_unresolved(fragment):
    _base, pages, compiled = _internal_owner_continuation_query_fixture()
    table = pages[1][fragment]["sections"][0]["tables"][0]
    _alignment_headers(table, "Kỳ này", "Kỳ này")
    indexed, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["reasons"] == ["OPERATING_EXPENSE_INTERNAL_OWNER_CONTINUATION_PERIOD_REJECTED"]
    receipts = indexed["candidate_dispositions"][0]["cluster"][
        "operating_expense_internal_owner_period_rejection_receipts"
    ]
    assert len(receipts) == 1
    assert receipts[0]["owner_proof"]["owner_row_ordinal"] == 4


@pytest.mark.parametrize(
    "mutation", ["REMOVE_RECEIPT", "FORGE_NOT_OBSERVED", "DUPLICATE_RECEIPT", "PERIOD_AXIS", "SOURCE_PREFIX"]
)
def test_internal_owner_period_veto_rejects_tampered_query_or_source(mutation):
    _base, pages, compiled = _internal_owner_continuation_query_fixture()
    prior, receiver = _alignment_tables(pages)
    _alignment_headers(prior, "Quý II/2026", "Quý II/2025")
    _alignment_headers(receiver, "Quý III/2026", "Quý III/2025")
    indexed, _trial = _run_alignment_fixture(pages, compiled)
    cluster = indexed["candidate_dispositions"][0]["cluster"]
    field = "operating_expense_internal_owner_period_rejection_receipts"
    receipt = cluster[field][0]
    if mutation == "REMOVE_RECEIPT":
        del cluster[field]
    elif mutation == "FORGE_NOT_OBSERVED":
        del cluster[field]
        cluster["status"] = NOT_OBSERVED
        cluster["reasons"] = []
    elif mutation == "DUPLICATE_RECEIPT":
        cluster[field].append(copy.deepcopy(receipt))
    elif mutation == "SOURCE_PREFIX":
        prior["rows"][1]["values_exact"][0] = "2"
    else:
        receipt["period_alignment_receipt"]["compatible"] = True
        material = {key: value for key, value in receipt.items() if key != "receipt_id"}
        receipt["receipt_id"] = "gjoefav1:internal-owner-period-rejection:" + canonical_json_sha256_v1(material)
    forged = _reseal_family_query_cluster(indexed, compiled)
    with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error, match="period-rejection source replay"):
        build_gemini_json_operating_expense_trials_v1(
            indexed_query_evidence=forged, page_json_by_document=pages, compiled_specs=compiled,
        )


@pytest.mark.parametrize("mutation", ["ONE_LANE_SUBSET", "DUPLICATE_BEFORE", "DUPLICATE_AFTER", "UNKNOWN_COLUMN"])
def test_continuation_inverse_column_map_preserves_selected_subset_or_rejects_tamper(mutation):
    _base, pages, compiled = _continuation_query_fixture()
    _prior, receiver = _alignment_tables(pages)
    _alignment_headers(receiver, "Kỳ này", "Kỳ trước")
    _reverse_alignment_columns_and_values(receiver)
    indexed, _trial = _run_alignment_fixture(pages, compiled)
    regions = indexed["candidate_dispositions"][0]["cluster"]["component_regions"]
    projected_pages, projected_regions, receipt = operating_expense_adapter._continuation_projection(
        pages=pages[1], regions=regions, compiled_specs=compiled,
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=projected_regions, page_json_by_version=projected_pages,
        compiled_specs=compiled, query_receipt=receipt["projected_query_receipt"],
    )
    root = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL")
    candidate["mappings"] = [root]
    projection = next(item for item in receipt["row_projections"] if item["projected_row_ordinal"] == root["source_refs"][0]["row_ordinal"])
    if mutation == "ONE_LANE_SUBSET":
        root["values"] = root["values"][:1]
        root["source_refs"][0]["money_column_ordinals"] = [1]
        operating_expense_adapter._restore_continuation_mapping_source_refs(candidate, receipt=receipt)
        assert root["source_refs"][0]["money_column_ordinals"] == [2]
    else:
        if mutation == "DUPLICATE_BEFORE":
            projection["before_money_column_ordinals"] = [1, 1]
        elif mutation == "DUPLICATE_AFTER":
            projection["after_money_column_ordinals"] = [1, 1]
        else:
            root["source_refs"][0]["money_column_ordinals"] = [999]
        with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error, match="inverse source column map drifted"):
            operating_expense_adapter._restore_continuation_mapping_source_refs(candidate, receipt=receipt)


def _calendar_count_fixture(layout):
    fixture = _continuation_query_fixture if layout == "COMPLETE_OWNER" else _internal_owner_continuation_query_fixture
    _base, pages, compiled = fixture()
    return pages, compiled, _alignment_tables(pages)


def _calendar_count_headers(table, pattern):
    _alignment_headers(table, pattern.format(year=2026), pattern.format(year=2025))


def _assert_calendar_count_rejection(pages, compiled, layout):
    indexed, trial = _run_alignment_fixture(pages, compiled)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    if layout == "INTERNAL_OWNER":
        assert trial["reasons"] == ["OPERATING_EXPENSE_INTERNAL_OWNER_CONTINUATION_PERIOD_REJECTED"]
        receipt = indexed["candidate_dispositions"][0]["cluster"][
            "operating_expense_internal_owner_period_rejection_receipts"
        ][0]
        assert receipt["period_alignment_receipt"]["compatible"] is False
    return indexed, trial


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("count", range(1, 13))
def test_every_equal_explicit_month_count_in_bounded_policy_remains_ready(layout, count):
    pages, compiled, tables = _calendar_count_fixture(layout)
    for table in tables:
        _calendar_count_headers(table, f"{count} tháng đầu năm {{year}}")
    _indexed, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("counts", [(2, 5), (1, 11), (7, 12)])
def test_unlisted_but_explicit_month_counts_cannot_disappear_into_year(layout, counts):
    pages, compiled, tables = _calendar_count_fixture(layout)
    for table, count in zip(tables, counts, strict=True):
        _calendar_count_headers(table, f"{count} tháng đầu năm {{year}}")
    _assert_calendar_count_rejection(pages, compiled, layout)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("fragment", [0, 1])
@pytest.mark.parametrize("count", ["- 2", "− 2", "-\t2", "-\n2", "-   2"])
def test_spaced_negative_count_is_observed_in_either_fragment_and_exact_replay(layout, fragment, count):
    pages, compiled, tables = _calendar_count_fixture(layout)
    for table in tables:
        _calendar_count_headers(table, "2 tháng đầu năm {year}")
    _calendar_count_headers(tables[fragment], f"{count} tháng đầu năm {{year}}")
    indexed, _trial = _assert_calendar_count_rejection(pages, compiled, layout)
    if layout == "INTERNAL_OWNER":
        receipt = indexed["candidate_dispositions"][0]["cluster"][
            "operating_expense_internal_owner_period_rejection_receipts"
        ][0]
        key = "prior_period_qualifiers" if fragment == 0 else "receiver_period_qualifiers"
        for qualifier in receipt["period_alignment_receipt"][key]:
            frontier = qualifier["duration_month_frontier"]
            assert frontier["valid"] is False
            assert frontier["evidence"][0]["count_token"] == "- 2"
            assert frontier["evidence"][0]["count"] is None


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("count", ["0", "-2", "−2", "13", "22", "2.5", "2,5", "2/5", "hai muoi"])
def test_invalid_count_is_not_absent_positive_or_suffix_truncated(layout, count):
    pages, compiled, tables = _calendar_count_fixture(layout)
    for table in tables:
        _calendar_count_headers(table, f"{count} tháng đầu năm {{year}}")
    _assert_calendar_count_rejection(pages, compiled, layout)


@pytest.mark.parametrize(
    ("numeric", "words"),
    [(1, "một"), (2, "hai"), (5, "năm"), (7, "bảy"), (11, "mười một"), (12, "mười hai")],
)
def test_governed_vietnamese_written_month_count_matches_numeric_count(numeric, words):
    pages, compiled, (prior, receiver) = _calendar_count_fixture("COMPLETE_OWNER")
    _calendar_count_headers(prior, f"{numeric} tháng đầu năm {{year}}")
    _calendar_count_headers(receiver, f"{words} tháng đầu năm {{year}}")
    _indexed, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


@pytest.mark.parametrize(("numeric", "words"), [(1, "one"), (2, "two"), (5, "five"), (10, "ten"), (11, "eleven"), (12, "twelve")])
def test_governed_english_written_month_count_matches_numeric_count(numeric, words):
    pages, compiled, (prior, receiver) = _calendar_count_fixture("COMPLETE_OWNER")
    _calendar_count_headers(prior, f"{numeric} months ended {{year}}")
    _calendar_count_headers(receiver, f"{words} months ended {{year}}")
    _indexed, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize(
    "pattern",
    [
        "31/02/{year}", "29/02/{year}", "00/06/{year}", "32/06/{year}", "30/00/{year}",
        "31/99/{year}", "ngày 31 tháng 2 năm {year}",
        "12345/02/{year}", "03/12345/{year}", "ngày 12345 tháng 2 năm {year}",
        "12345 02 {year}",
        "Từ 31/02/{year} đến 30/06/{year}", "Từ 01/01/{year} đến 31/04/{year}",
        "Năm {year}, ngày 03/06/26", "Năm {year}, ngày 3 tháng 6 năm 26",
    ],
)
def test_every_visible_invalid_or_short_year_date_blocks_bare_year_fallback(layout, pattern):
    pages, compiled, tables = _calendar_count_fixture(layout)
    for table in tables:
        _calendar_count_headers(table, pattern)
    _assert_calendar_count_rejection(pages, compiled, layout)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize(
    ("prior_pattern", "receiver_pattern"),
    [
        ("03/06/{year}", "ngày 3 tháng 6 năm {year}"),
        ("09/06/{year}", "ngày 9 tháng 6 năm {year}"),
        ("13/06/{year}", "06/13/{year}"),
        ("28/02/{year}", "ngày 28 tháng 2 năm {year}"),
        ("03 06 {year}", "ngày 3 tháng 6 năm {year}"),
        (
            "Từ 01/01/{year} đến 30/06/{year}",
            "Từ ngày 1 tháng 1 năm {year} đến ngày 30 tháng 6 năm {year}",
        ),
        (
            "2 tháng kết thúc 03/06/{year}",
            "2 tháng kết thúc ngày 3 tháng 6 năm {year}",
        ),
    ],
)
def test_calendar_equivalence_has_no_phantom_month_duration(layout, prior_pattern, receiver_pattern):
    pages, compiled, (prior, receiver) = _calendar_count_fixture(layout)
    _calendar_count_headers(prior, prior_pattern)
    _calendar_count_headers(receiver, receiver_pattern)
    _indexed, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
def test_valid_leap_days_are_observed_not_blanket_february_rejection(layout):
    pages, compiled, (prior, receiver) = _calendar_count_fixture(layout)
    _alignment_headers(prior, "29/02/2024", "29/02/2020")
    _alignment_headers(receiver, "ngày 29 tháng 2 năm 2024", "ngày 29 tháng 2 năm 2020")
    _indexed, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
def test_masking_written_date_does_not_mask_real_conflicting_month_count(layout):
    pages, compiled, (prior, receiver) = _calendar_count_fixture(layout)
    _calendar_count_headers(prior, "2 tháng kết thúc ngày 3 tháng 6 năm {year}")
    _calendar_count_headers(receiver, "5 tháng kết thúc ngày 3 tháng 6 năm {year}")
    _assert_calendar_count_rejection(pages, compiled, layout)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
@pytest.mark.parametrize("fragment", [0, 1])
@pytest.mark.parametrize("pattern", ["31/02/{year}", "-2 tháng đầu năm {year}"])
def test_invalid_explicit_calendar_or_count_in_either_fragment_is_typed_veto(layout, fragment, pattern):
    pages, compiled, tables = _calendar_count_fixture(layout)
    _calendar_count_headers(tables[fragment], pattern)
    _assert_calendar_count_rejection(pages, compiled, layout)


@pytest.mark.parametrize("layout", ["COMPLETE_OWNER", "INTERNAL_OWNER"])
def test_explicit_iso_date_omitted_by_shared_axis_cannot_be_bare_year(layout):
    pages, compiled, tables = _calendar_count_fixture(layout)
    for table in tables:
        _calendar_count_headers(table, "{year}-06-03")
    _assert_calendar_count_rejection(pages, compiled, layout)


def test_unexplained_month_surface_and_huge_count_are_not_missing_qualifiers():
    for surface in ("tháng 6 năm 2026", "13 months 2026", "9" * 5000 + " tháng năm 2026"):
        masked, _dates = operating_expense_adapter._continuation_calendar_frontier(surface)
        frontier = operating_expense_adapter._continuation_duration_month_frontier(masked)
        assert frontier["valid"] is False


@pytest.mark.parametrize("field", ["day", "month", "year"])
def test_overlong_calendar_field_is_observed_and_rejected_without_integer_conversion(field):
    values = {"day": "03", "month": "06", "year": "2026"}
    values[field] = "9" * 5000
    masked, evidence = operating_expense_adapter._continuation_calendar_frontier(
        "{day}/{month}/{year}".format(**values)
    )
    assert len(evidence) == 1
    assert evidence[0]["calendar_valid"] is False
    assert not masked.strip()


def test_source_row_coverage_rejects_tampered_mapping_locator() -> None:
    indexed, trials, pages, compiled = _source_row_coverage_inputs(
        _operating_page()
    )
    attacked = copy.deepcopy(trials)
    attacked[0]["mappings"][0]["source_refs"][0]["row_ordinal"] = 999
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="coverage source-row locator is invalid",
    ):
        build_operating_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=attacked,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )


# F36 mapping-maximization case axis.  The real cases are immutable transcriptions
# of the PDF rows cited by the semantic review; the synthetic axis attacks each
# generic structural rule without routing on a bank, filename, page, or value.
_F36_MAPPING_MAX_REAL_CASE_IDS = (
    "R01_TCB212_FLAT_EXACT_PARTITION",
    "R02_VBB261_OTHER_PARENT_VS_RESIDUAL_LEAF",
    "R03_SGB157_WRAPPER_FLATTENED_UNIFORM",
    "R04_STB195_UNIFORM_SIBLING_NOT_SALARY_DESCENDANT",
    "R05_STB197_TRUE_CONTINUATION_SOURCE_ORIGIN",
    "R06_STB204_COMPOSITE_AND_PROVISION_NEGATIVES",
)
_F36_MAPPING_MAX_SYNTHETIC_CASE_IDS = tuple(f"S{ordinal:02d}" for ordinal in range(1, 19))


def _mapping_by_role(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {mapping["role"]: mapping for mapping in candidate["mappings"]}


def _coefficients(mapping: dict[str, Any]) -> list[int | None]:
    return [value["coefficient"] for value in mapping["values"]]


def _mapping_max_flat_rows(*, consulting: bool = True) -> list[dict[str, Any]]:
    rows = [
        _row("Lương và các chi phí liên quan", "30", "25"),
        _row("Chi phí in ấn, tiếp thị và khuyến mại", "5", "4"),
        _row("Chi phí thuê văn phòng và tài sản", "12", "10"),
        _row("Khấu hao và hao mòn tài sản cố định", "8", "5"),
        _row("Chi phí công nghệ thông tin (*)", "4", "3"),
        _row("Chi phí bảo dưỡng và sửa chữa tài sản", "3", "2"),
        _row("Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        _row("Chi phí dụng cụ và thiết bị", "2", "1"),
        _row("Chi phí thông tin liên lạc", "1", "1"),
        _row("Chi phí điện nước, vệ sinh văn phòng", "1", "1"),
        _row("Chi phí bảo hiểm cho các khoản tiền gửi khách hàng", "5", "4"),
        _row("Công tác phí", "1", "1"),
        _row("Chi phí dự phòng các tài sản Có khác", "2", "1"),
    ]
    if consulting:
        rows.append(_row("Chi phí dịch vụ tư vấn", "1", "1"))
    rows.extend(
        [
            _row("Chi phí hoạt động khác", "2", "2"),
            _row(None, "87" if consulting else "86", "69" if consulting else "68", kind="TOTAL", path=[None]),
        ]
    )
    return rows


def test_f36_mapping_max_case_axis_is_exactly_six_real_and_eighteen_synthetic() -> None:
    assert len(_F36_MAPPING_MAX_REAL_CASE_IDS) == 6
    assert len(set(_F36_MAPPING_MAX_REAL_CASE_IDS)) == 6
    assert len(_F36_MAPPING_MAX_SYNTHETIC_CASE_IDS) == 18
    assert len(set(_F36_MAPPING_MAX_SYNTHETIC_CASE_IDS)) == 18


def test_f36_mapping_max_compiled_leaf_and_parent_axes_are_declarative() -> None:
    compiled = _adapter_compiled()
    assert {
        ("FLAT_ASSET_DEPRECIATION_SOURCE_ONLY", "DEPRECIATION_EXPENSE"),
        ("FLAT_ADMIN_TRAVEL_SOURCE_ONLY", "TRAVEL_EXPENSE"),
        ("FLAT_OTHER_OPERATING_SOURCE_ONLY", "OTHER_OPERATING_EXPENSE"),
        ("EMPLOYEE_UNIFORM_SOURCE_ONLY", "OTHER_EMPLOYEE_EXPENSE"),
        ("EMPLOYEE_OTHER_ALLOWANCE_SOURCE_ONLY", "EMPLOYEE_BENEFIT"),
    } <= {
        (item["source_role"], item["target_role"])
        for item in compiled["validation_role_leaf_projections"]
    }
    assert {
        (
            ("FLAT_ASSET_RENT_SOURCE_ONLY", "FLAT_ASSET_DEPRECIATION_SOURCE_ONLY", "FLAT_ASSET_MAINTENANCE_SOURCE_ONLY", "FLAT_ASSET_TOOLS_SOURCE_ONLY"),
            "ASSET_EXPENSE",
        ),
        (
            ("FLAT_ADMIN_PRINTING_SOURCE_ONLY", "IT_EXPENSE_SOURCE_ONLY", "FLAT_ADMIN_COMMUNICATION_SOURCE_ONLY", "FLAT_ADMIN_UTILITIES_SOURCE_ONLY", "FLAT_ADMIN_TRAVEL_SOURCE_ONLY"),
            "ADMIN_EXPENSE",
        ),
    } <= {
        (tuple(item["component_roles"]), item["result_role"])
        for item in compiled["derived_role_equations"]
    }


def test_r01_tcb212_flat_exact_partition_maps_leaves_and_complete_parents() -> None:
    # Real labels and coefficients from TCB212 physical page 53.  Rows unrelated
    # to the two parent equations are retained so the printed family total is exact.
    rows = [
        _row("Lương và các chi phí liên quan", "2.880.512", "3.382.246"),
        _row("Chi phí in ấn, tiếp thị và khuyến mại", "546.351", "600.842"),
        _row("Chi phí thuê văn phòng và tài sản", "213.190", "205.667"),
        _row("Khấu hao và hao mòn tài sản cố định", "896.589", "707.390"),
        _row("Chi phí công nghệ thông tin (*)", "634.421", "506.166"),
        _row("Chi phí bảo dưỡng và sửa chữa tài sản", "197.472", "184.040"),
        _row("Chi nộp thuế và các khoản phí, lệ phí", "144.121", "101.056"),
        _row("Chi phí dụng cụ và thiết bị", "31.562", "73.873"),
        _row("Chi phí thông tin liên lạc", "25.455", "23.567"),
        _row("Chi phí điện nước, vệ sinh văn phòng", "55.614", "60.174"),
        _row("Chi phí bảo hiểm cho các khoản tiền gửi khách hàng", "313.933", "250.595"),
        _row("Công tác phí", "27.618", "16.042"),
        # Authenticated PDF-visible-dash repair after-images for the two raw
        # Gemini null cells; this test starts after the independent repair gate.
        _row("Chi phí dự phòng giảm giá góp vốn, đầu tư dài hạn", "4.634", "-"),
        _row("Trích lập dự phòng các tài sản Có khác", "-", "599"),
        _row("Chi phí dịch vụ tư vấn", "92.539", "151.008"),
        _row("Chi phí hoạt động khác", "471.436", "470.580"),
        _row(None, "6.535.447", "6.733.845", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["ASSET_EXPENSE"]) == [1_338_813, 1_170_970]
    assert _coefficients(by_role["DEPRECIATION_EXPENSE"]) == [896_589, 707_390]
    assert _coefficients(by_role["ADMIN_EXPENSE"]) == [1_381_998, 1_357_799]
    assert _coefficients(by_role["TRAVEL_EXPENSE"]) == [27_618, 16_042]
    assert _coefficients(by_role["OTHER_OPERATING_EXPENSE"]) == [471_436, 470_580]


def _vbb261_rows() -> list[dict[str, Any]]:
    employee = "Chi phí cho nhân viên"
    asset = "Chi về tài sản"
    other = "Chi phí hoạt động khác"
    provision = "Chi phí dự phòng (không bao dự phòng rủi ro tín dụng, rủi ro chứng khoán đầu tư)"
    return [
        _row(employee, "398.795", "341.126", kind="SUBTOTAL"),
        _row("- Chi lương và phụ cấp", "317.355", "276.306", path=[employee, "- Chi lương và phụ cấp"]),
        _row("- Các khoản chi đóng góp theo lương", "36.274", "29.913", path=[employee, "- Các khoản chi đóng góp theo lương"]),
        _row("- Chi trợ cấp khác", "45.166", "34.907", path=[employee, "- Chi trợ cấp khác"]),
        _row(asset, "206.402", "208.463", kind="SUBTOTAL"),
        _row("- Chi phí thuê tài sản", "101.319", "95.812", path=[asset, "- Chi phí thuê tài sản"]),
        _row("- Khấu hao và hao mòn tài sản cố định", "51.363", "51.139", path=[asset, "- Khấu hao và hao mòn tài sản cố định"]),
        _row("- Bảo dưỡng và sửa chữa tài sản", "45.280", "54.888", path=[asset, "- Bảo dưỡng và sửa chữa tài sản"]),
        _row("- Mua sắm công cụ lao động", "7.411", "6.019", path=[asset, "- Mua sắm công cụ lao động"]),
        _row("- Chi phí bảo hiểm tài sản", "1.029", "605", path=[asset, "- Chi phí bảo hiểm tài sản"]),
        _row(other, "192.731", "175.463", kind="SUBTOTAL"),
        _row("- Chi nộp phí bảo hiểm tiền gửi của khách hàng", "67.956", "60.770", path=[other, "- Chi nộp phí bảo hiểm tiền gửi của khách hàng"]),
        _row("- Chi phí lễ tân, khánh tiết, hội nghị", "18.711", "12.634", path=[other, "- Chi phí lễ tân, khánh tiết, hội nghị"]),
        _row("- Chi phí quảng cáo, tiếp thị", "15.349", "16.945", path=[other, "- Chi phí quảng cáo, tiếp thị"]),
        _row("- Chi phí điện nước, vệ sinh cơ quan", "13.544", "13.304", path=[other, "- Chi phí điện nước, vệ sinh cơ quan"]),
        _row("- Chi phí bưu phí, điện thoại", "10.579", "10.025", path=[other, "- Chi phí bưu phí, điện thoại"]),
        _row("- Chi phí thuế GTGT không được khấu trừ", "6.191", "6.279", path=[other, "- Chi phí thuế GTGT không được khấu trừ"]),
        _row("- Công tác phí", "3.494", "3.077", path=[other, "- Công tác phí"]),
        _row("- Chi vật liệu văn phòng, giấy tờ in ấn", "2.951", "2.786", path=[other, "- Chi vật liệu văn phòng, giấy tờ in ấn"]),
        _row("- Chi phí xăng dầu", "2.177", "2.377", path=[other, "- Chi phí xăng dầu"]),
        _row("- Chi phí hoạt động khác", "51.779", "47.266", path=[other, "- Chi phí hoạt động khác"]),
        _row(provision, "421", "1.309", kind="SUBTOTAL"),
        _row("- Trích lập dự phòng giảm giá đầu tư dài hạn", "421", "1.309", path=[provision, "- Trích lập dự phòng giảm giá đầu tư dài hạn"]),
        _row(None, "798.349", "726.361", kind="TOTAL", path=[None]),
    ]


def test_r02_vbb261_broad_other_parent_never_shadows_residual_leaf() -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(_vbb261_rows()))
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["EMPLOYEE_BENEFIT"]) == [45_166, 34_907]
    assert _coefficients(by_role["TRAVEL_EXPENSE"]) == [3_494, 3_077]
    other = by_role["OTHER_OPERATING_EXPENSE"]
    assert _coefficients(other) == [51_779, 47_266]
    assert {ref["row_ordinal"] for ref in other["source_refs"]} == {21}
    assert 11 not in {ref["row_ordinal"] for ref in other["source_refs"]}


def test_r03_sgb157_blank_wrapper_preserves_uniform_employee_leaf() -> None:
    employee = "2. Chi phí cho nhân viên"
    rows = [
        _row("1. Chi nộp thuế và các khoản phí, lệ phí", "1.516", "1.125"),
        _row(employee, "217.869", "203.505", kind="SUBTOTAL"),
        _row("Trong đó:", None, None, kind="GROUP", path=["Trong đó:"]),
        _row("Chi lương và phụ cấp", "160.783", "139.046", path=["Trong đó:", "Chi lương và phụ cấp"]),
        _row("Các khoản chi đóng góp theo lương", "33.313", "31.222", path=["Trong đó:", "Các khoản chi đóng góp theo lương"]),
        _row("Đồng phục và các chi phí liên quan", "12.585", "11.774", path=["Trong đó:", "Đồng phục và các chi phí liên quan"]),
        _row("Chi trợ cấp", "11.188", "21.463", path=["Trong đó:", "Chi trợ cấp"]),
        _row("3. Chi về tài sản", "10", "8"),
        _row("4. Chi cho hoạt động quản lý công vụ", "9", "7"),
        _row("5. Chi nộp phí bảo hiểm tiền gửi của khách hàng", "5", "4"),
        _row("6. Chi phí hoạt động khác", "2", "1"),
        _row(None, "219.411", "204.650", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    uniform = _mapping_by_role(candidate)["OTHER_EMPLOYEE_EXPENSE"]
    assert _coefficients(uniform) == [12_585, 11_774]
    assert uniform["source_refs"][0]["row_ordinal"] == 6
    assert all(value["coefficient"] is None for value in candidate["closure_receipt"]["table_receipts"][0]["classification"]["role_hits"][0].get("values", []))


def _stb195_rows() -> list[dict[str, Any]]:
    employee = "2 Chi phí cho nhân viên:"
    salary = "Trong đó: - Chi lương và phụ cấp"
    asset = "3 Chi về tài sản :"
    admin = "4 Chi cho hoạt động quản lý công vụ:"
    return [
        _row("1 Chi nộp thuế và các khoản phí, lệ phí", "312,735", "60,599"),
        _row(employee, "1,976,895", "1,876,087", kind="GROUP"),
        _row(salary, "1,664,299", "1,728,466", path=[employee, salary]),
        _row("- Các khoản chi đóng góp theo lương", "97,449", "96,753", path=[employee, salary, "- Các khoản chi đóng góp theo lương"]),
        _row("- Chi trợ cấp", "192,593", "27,792", path=[employee, salary, "- Chi trợ cấp"]),
        _row("- Chi trang phục giao dịch", "22,554", "23,076", path=[employee, salary, "- Chi trang phục giao dịch"]),
        _row(asset, "638,528", "633,921", kind="GROUP"),
        _row("- Trong đó: khấu hao tài sản cố định", "217,772", "242,598", path=[asset, "- Trong đó: khấu hao tài sản cố định"]),
        _row(admin, "499,440", "478,991", kind="GROUP"),
        _row("Trong đó: - Công tác phí", "40,326", "33,588", path=[admin, "Trong đó: - Công tác phí"]),
        _row("5 Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng", "348,096", "161,193"),
        _row("6 (Hoàn nhập)/chi phí dự phòng giảm giá đầu tư dài hạn", "-", None),
        _row("7 (Hoàn nhập)/chi phí dự phòng rủi ro tài sản có khác", "(192)", "208,015"),
        _row("Tổng", "3,775,502", "3,418,806", kind="TOTAL", path=["Tổng"]),
    ]


def test_r04_stb195_uniform_is_employee_sibling_despite_stale_concatenated_path() -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(_stb195_rows()))
    assert candidate["status"] == READY
    uniform = _mapping_by_role(candidate)["OTHER_EMPLOYEE_EXPENSE"]
    assert _coefficients(uniform) == [22_554, 23_076]
    assert uniform["source_refs"][0]["row_ordinal"] == 6


def _stb197_continuation_trial() -> tuple[dict[str, Any], dict[int, dict[str, dict[str, Any]]], dict[str, Any]]:
    compiled = _adapter_compiled()
    employee = "Chi phí cho nhân viên:"
    salary = "Trong đó: - Chi lương và phụ cấp"
    prior_rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "448,794", "337,406"),
        _row(employee, "6,179,222", "5,634,192", kind="GROUP"),
        _row(salary, "5,545,797", "5,110,211", path=[employee, salary]),
        _row("- Các khoản chi đóng góp theo lương", "283,973", "294,137", path=[employee, salary, "- Các khoản chi đóng góp theo lương"]),
    ]
    prior_table = _table(prior_rows, title=OWNER)
    prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    receiver_rows = [
        _row("- Chi trợ cấp", "258,772", "159,605"),
        _row("- Chi trang phục giao dịch", "90,680", "70,239"),
        _row("3 Chi về tài sản :", "2,126,784", "1,940,418", kind="GROUP"),
        _row("- Trong đó: khấu hao tài sản cố định", "641,342", "716,936", path=["3 Chi về tài sản :", "- Trong đó: khấu hao tài sản cố định"]),
        _row("4 Chi cho hoạt động quản lý công vụ:", "1,264,205", "1,401,438", kind="GROUP"),
        _row("Trong đó: - Công tác phí", "122,787", "105,726", path=["4 Chi cho hoạt động quản lý công vụ:", "Trong đó: - Công tác phí"]),
        _row("- Chi về các hoạt động đoàn thể của TCTD", "-", "-", path=["4 Chi cho hoạt động quản lý công vụ:", "- Chi về các hoạt động đoàn thể của TCTD"]),
        _row("5 Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng", "708,298", "489,343"),
        _row("6 (Hoàn nhập)/chi phí dự phòng giảm giá đầu tư dài hạn", "(38,617)", "10,264"),
        _row("7 (Hoàn nhập)/chi phí dự phòng rủi ro tài sản có khác", "28,519", "643,611"),
        _row("Tổng", "10,717,205", "10,456,672", kind="TOTAL", path=["Tổng"]),
    ]
    receiver_table = _table(receiver_rows)
    receiver_table["columns"] = [
        {"header_path_exact": [None], "value_kind": "MONEY"},
        {"header_path_exact": [None], "value_kind": "MONEY"},
    ]
    receiver_table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    prior_page = _page(_section("THUYẾT MINH BÁO CÁO TÀI CHÍNH", prior_table))
    receiver_page = _page(_section("THUYẾT MINH BÁO CÁO TÀI CHÍNH", receiver_table))
    records = [
        _record(prior_page),
        {**_record(receiver_page), "page_json_version_id": CONTINUATION_VERSION_ID, "physical_page": 2, "selected_page_ordinal": 2},
    ]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    selected_document_axis = [{"document_id": DOCUMENT_ID, "document_ordinal": 1, "source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA256}]
    selected_page_axis = [
        {**selected_document_axis[0], "page_json_version_id": record["page_json_version_id"], "physical_page": record["physical_page"], "selected_page_ordinal": record["selected_page_ordinal"]}
        for record in records
    ]
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        selected_page_axis=selected_page_axis,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    pages = {1: {VERSION_ID: prior_page, CONTINUATION_VERSION_ID: receiver_page}}
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trial = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )[0]
    return trial, pages, compiled


def test_r05_stb197_continuation_mapping_keeps_true_receiver_row_origin() -> None:
    trial, _pages, _compiled_specs = _stb197_continuation_trial()
    assert trial["status"] == READY
    uniform = _mapping_by_role(trial)["OTHER_EMPLOYEE_EXPENSE"]
    assert _coefficients(uniform) == [90_680, 70_239]
    assert len(uniform["source_refs"]) == 1
    ref = uniform["source_refs"][0]
    assert ref["locator"]["page_json_version_id"] == CONTINUATION_VERSION_ID
    assert ref["locator"]["physical_page"] == 2
    assert ref["locator"]["section_id"] == "s1"
    assert ref["locator"]["table_id"] == "t1"
    assert ref["row_ordinal"] == 2
    assert ref["row_id"] == "r2"
    adapter_receipt = trial["candidates"][0]["closure_receipt"][
        "operating_expense_adapter_receipt"
    ]
    guard = next(
        item
        for receipt in adapter_receipt["mapping_max_parent_guard_receipts"]
        for item in receipt["guarded_source_axis"]
        if item["role"] == "EMPLOYEE_UNIFORM_SOURCE_ONLY"
    )
    assert guard["locator"]["page_json_version_id"] == CONTINUATION_VERSION_ID
    assert guard["locator"]["physical_page"] == 2
    assert guard["locator"]["section_id"] == "s1"
    assert guard["locator"]["table_id"] == "t1"
    assert guard["row_ordinal"] == 2
    assert guard["label_exact"] == "- Chi trang phục giao dịch"
    assert guard["money_column_ordinals"] == [1, 2]
    assert guard["values_exact"] == ["90,680", "70,239"]
    assert adapter_receipt["flat_parent_projection_receipts"] == []


def _stb204_rows() -> list[dict[str, Any]]:
    employee = "2 Chi phí cho nhân viên:"
    asset = "3 Chi về tài sản :"
    admin = "4 Chi cho hoạt động quản lý công vụ:"
    return [
        _row("1 Chi nộp thuế và các khoản phí, lệ phí", "560,972", "431,066"),
        _row(employee, "6,985,597", "7,419,161", kind="GROUP"),
        _row("Trong đó: - Chi lương và phụ cấp", "6,182,606", "6,695,462", path=[employee, "Trong đó: - Chi lương và phụ cấp"]),
        _row("- Các khoản chi đóng góp theo lương, chi trang phục giao dịch, phương tiện bảo hộ lao động", "481,714", "497,781", path=[employee, "- Các khoản chi đóng góp theo lương, chi trang phục giao dịch, phương tiện bảo hộ lao động"]),
        _row("- Chi trợ cấp", "321,276", "225,917", path=[employee, "- Chi trợ cấp"]),
        _row("- Chi khác cho nhân viên", "-", "-", path=[employee, "- Chi khác cho nhân viên"]),
        _row(asset, "2,742,993", "2,728,478", kind="GROUP"),
        _row("- Trong đó khấu hao tài sản cố định", "899,583", "980,725", path=[asset, "- Trong đó khấu hao tài sản cố định"]),
        _row(admin, "1,886,684", "2,094,104", kind="GROUP"),
        _row("Trong đó: - Công tác phí", "178,556", "153,911", path=[admin, "Trong đó: - Công tác phí"]),
        _row("- Chi về các hoạt động đoàn thể của TCTD", "180", "180", path=[admin, "- Chi về các hoạt động đoàn thể của TCTD"]),
        _row("5 Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng", "726,043", "661,041"),
        _row("6 Chi phí dự phòng phải thu(không tính chi phí dự phòng rủi ro tín dụng nội và ngoại bảng; chi phí dự phòng giảm giá chứng khoán)", "29,035", "648,473"),
        _row("7 Chi phí dự phòng đầu tư (không tính chi phí dự phòng rủi ro tín dụng nội và ngoại bảng; chi phí dự phòng giảm giá chứng khoán)", "233", "66"),
        _row("8 Chi phí dự phòng rủi ro khác", "113,322", "-"),
        _row("9 Chi phí hoạt động khác", "-", "-"),
        _row("Tổng", "13,044,879", "13,982,389", kind="TOTAL", path=["Tổng"]),
    ]


def test_r06_stb204_composites_stay_source_only_and_printed_other_dash_maps() -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(_stb204_rows()))
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["OTHER_OPERATING_EXPENSE"]) == [0, 0]
    assert "LONG_TERM_BAD_DEBT_PROVISION" not in by_role
    assert all(
        not ({4} & {ref["row_ordinal"] for ref in mapping["source_refs"]})
        for role, mapping in by_role.items()
        if role in {"PAYROLL_CONTRIBUTIONS", "OTHER_EMPLOYEE_EXPENSE"}
    )


@pytest.mark.parametrize("consulting", [False, True], ids=["S03_NO_CONSULTING", "S03_WITH_CONSULTING"])
def test_s03_flat_parent_axes_are_selected_from_complete_role_sets(consulting: bool) -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(
        _operating_page(_mapping_max_flat_rows(consulting=consulting))
    )
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["ASSET_EXPENSE"]) == [25, 18]
    assert _coefficients(by_role["ADMIN_EXPENSE"]) == (
        [13, 11] if consulting else [12, 10]
    )


@pytest.mark.parametrize(
    ("label", "target_role"),
    [
        ("Đồng phục và các chi phí liên quan", "OTHER_EMPLOYEE_EXPENSE"),
        ("Chi trang phục và phương tiện bảo hộ lao động", "OTHER_EMPLOYEE_EXPENSE"),
        ("Chi trang phục giao dịch", "OTHER_EMPLOYEE_EXPENSE"),
        ("Chi trang phục giao dịch và phương tiện bảo hộ lao động", "OTHER_EMPLOYEE_EXPENSE"),
        ("Chi trợ cấp khác", "EMPLOYEE_BENEFIT"),
    ],
)
def test_s04_narrow_employee_leaf_aliases_project_only_inside_exact_employee_owner(
    label: str, target_role: str
) -> None:
    employee = "Chi phí cho nhân viên"
    rows = [
        _row(employee, "100", "90", kind="SUBTOTAL"),
        _row("Chi lương và phụ cấp", "80", "72", path=[employee, "Chi lương và phụ cấp"]),
        _row(label, "20", "18", path=[employee, label]),
        _row("Chi về tài sản", "10", "9"),
        _row("Chi cho hoạt động quản lý công vụ", "5", "4"),
        _row(None, "115", "103", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    assert _coefficients(_mapping_by_role(candidate)[target_role]) == [20, 18]


@pytest.mark.parametrize(
    "label",
    [
        "Các khoản chi đóng góp theo lương, chi trang phục giao dịch, phương tiện bảo hộ lao động",
        "Chi trang phục, ăn ca, y tế, trợ cấp thôi việc",
        "Chi trợ cấp và chi khác",
        "Chi thưởng",
        "Chi công tác xã hội",
    ],
)
def test_s05_mixed_employee_rows_are_never_split_or_wholly_assigned(label: str) -> None:
    employee = "Chi phí cho nhân viên"
    rows = [
        _row(employee, "100", "90", kind="SUBTOTAL"),
        _row("Chi lương và phụ cấp", "80", "72", path=[employee, "Chi lương và phụ cấp"]),
        _row(label, "20", "18", path=[employee, label]),
        _row("Chi về tài sản", "10", "9"),
        _row("Chi cho hoạt động quản lý công vụ", "5", "4"),
        _row(None, "115", "103", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    mapped_refs = {
        ref["row_ordinal"]
        for role, mapping in _mapping_by_role(candidate).items()
        if role in {"PAYROLL_CONTRIBUTIONS", "EMPLOYEE_BENEFIT", "OTHER_EMPLOYEE_EXPENSE"}
        for ref in mapping["source_refs"]
    }
    assert 3 not in mapped_refs


def _synthetic_other_parent_leaf_rows() -> list[dict[str, Any]]:
    parent = "Chi phí hoạt động khác"
    return [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        _row("Chi phí cho nhân viên", "2", "2"),
        _row("Chi về tài sản", "3", "3"),
        _row(parent, "100", "80", kind="SUBTOTAL"),
        _row("Chi nộp phí bảo hiểm tiền gửi của khách hàng", "30", "20", path=[parent, "Chi nộp phí bảo hiểm tiền gửi của khách hàng"]),
        _row("Công tác phí", "10", "8", path=[parent, "Công tác phí"]),
        _row("Chi phí hoạt động khác", "60", "52", path=[parent, "Chi phí hoạt động khác"]),
        _row(None, "106", "86", kind="TOTAL", path=[None]),
    ]


def test_s01_structural_leaf_beats_identically_named_source_parent() -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(
        _operating_page(_synthetic_other_parent_leaf_rows())
    )
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["TRAVEL_EXPENSE"]) == [10, 8]
    other = by_role["OTHER_OPERATING_EXPENSE"]
    assert _coefficients(other) == [60, 52]
    assert {ref["row_ordinal"] for ref in other["source_refs"]} == {7}


def test_s02_flat_exact_leaf_projections_preserve_printed_source_refs() -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(
        _operating_page(_mapping_max_flat_rows(consulting=False))
    )
    by_role = _mapping_by_role(candidate)
    expected = {
        "DEPRECIATION_EXPENSE": (4, [8, 5]),
        "TRAVEL_EXPENSE": (12, [1, 1]),
        "OTHER_OPERATING_EXPENSE": (14, [2, 2]),
    }
    for role, (row_ordinal, coefficients) in expected.items():
        assert _coefficients(by_role[role]) == coefficients
        assert {ref["row_ordinal"] for ref in by_role[role]["source_refs"]} == {
            row_ordinal
        }


def test_s06_complete_disjoint_same_target_leaves_aggregate_once() -> None:
    employee = "Chi phí cho nhân viên"
    rows = [
        _row(employee, "100", "90", kind="SUBTOTAL"),
        _row("Chi lương và phụ cấp", "80", "72", path=[employee, "Chi lương và phụ cấp"]),
        _row("Đồng phục và các chi phí liên quan", "12", "10", path=[employee, "Đồng phục và các chi phí liên quan"]),
        _row("Chi trang phục giao dịch", "8", "8", path=[employee, "Chi trang phục giao dịch"]),
        _row("Chi về tài sản", "10", "9"),
        _row("Chi cho hoạt động quản lý công vụ", "5", "4"),
        _row(None, "115", "103", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    other_employee = _mapping_by_role(candidate)["OTHER_EMPLOYEE_EXPENSE"]
    assert _coefficients(other_employee) == [20, 18]
    assert {ref["row_ordinal"] for ref in other_employee["source_refs"]} == {3, 4}
    assert len(
        {
            (ref["locator"]["page_json_version_id"], ref["locator"]["table_id"], ref["row_ordinal"])
            for ref in other_employee["source_refs"]
        }
    ) == 2


def test_s07_duplicate_or_overlapping_flat_role_axis_fails_closed() -> None:
    rows = _mapping_max_flat_rows(consulting=False)
    rows.insert(3, _row("Chi phí thuê văn phòng và tài sản", "1", "1"))
    rows[-1]["values_exact"] = ["87", "69"]
    page = _operating_page(rows)
    compiled = _adapter_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    private, guards, receipts = operating_expense_adapter._mapping_max_private_specs(
        pages={VERSION_ID: page},
        regions=cluster["component_regions"],
        compiled_specs=compiled,
    )
    assert private is not compiled
    assert len(guards) == 1
    assert [receipt["result_role"] for receipt in receipts] == ["ADMIN_EXPENSE"]

    candidate, _cluster_value, _receipt = _evaluate_adapter(page)
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert "ASSET_EXPENSE" not in by_role
    assert _coefficients(by_role["ADMIN_EXPENSE"]) == [12, 10]


@pytest.mark.parametrize(
    ("retained_axis", "expected_role", "expected_coefficients"),
    [
        ("asset", "ASSET_EXPENSE", [25, 18]),
        ("admin", "ADMIN_EXPENSE", [12, 10]),
    ],
)
def test_mapping_max_complete_parent_axes_are_independent(
    retained_axis: str,
    expected_role: str,
    expected_coefficients: list[int],
) -> None:
    rows = _mapping_max_flat_rows(consulting=False)
    removed_labels = (
        {
            "Chi phí in ấn, tiếp thị và khuyến mại",
            "Chi phí công nghệ thông tin (*)",
            "Chi phí thông tin liên lạc",
            "Chi phí điện nước, vệ sinh văn phòng",
            "Công tác phí",
        }
        if retained_axis == "asset"
        else {
            "Chi phí thuê văn phòng và tài sản",
            "Khấu hao và hao mòn tài sản cố định",
            "Chi phí bảo dưỡng và sửa chữa tài sản",
            "Chi phí dụng cụ và thiết bị",
        }
    )
    rows = [row for row in rows if row["label_exact"] not in removed_labels]
    rows[-1]["values_exact"] = (
        ["74", "58"] if retained_axis == "asset" else ["61", "50"]
    )

    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role[expected_role]) == expected_coefficients
    absent_role = "ADMIN_EXPENSE" if retained_axis == "asset" else "ASSET_EXPENSE"
    assert absent_role not in by_role
    flat_receipts = candidate["closure_receipt"][
        "operating_expense_adapter_receipt"
    ]["flat_parent_projection_receipts"]
    assert [receipt["result_role"] for receipt in flat_receipts] == [expected_role]


def test_mapping_max_component_with_visible_descendant_vetoes_flat_parent() -> None:
    rows = _mapping_max_flat_rows(consulting=False)
    tools_ordinal = next(
        ordinal
        for ordinal, row in enumerate(rows)
        if row["label_exact"] == "Chi phí dụng cụ và thiết bị"
    )
    tools = rows[tools_ordinal]
    rows.insert(
        tools_ordinal + 1,
        _row(
            "Trong đó: Công cụ công nghệ thông tin",
            "1",
            "1",
            path=[tools["label_exact"], "Trong đó: Công cụ công nghệ thông tin"],
        ),
    )

    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert "ASSET_EXPENSE" not in _mapping_by_role(candidate)
    flat_receipts = candidate["closure_receipt"][
        "operating_expense_adapter_receipt"
    ]["flat_parent_projection_receipts"]
    assert all(
        receipt["result_role"] != "ASSET_EXPENSE"
        for receipt in flat_receipts
    )


def test_mapping_max_continuation_selector_never_enables_flat_parent_axis() -> None:
    page = _operating_page(_mapping_max_flat_rows(consulting=False))
    compiled = _adapter_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    private, guards, receipts = operating_expense_adapter._mapping_max_private_specs(
        pages={VERSION_ID: page},
        regions=cluster["component_regions"],
        compiled_specs=compiled,
        allow_flat_parent_axes=False,
    )
    assert private["derived_role_equations"] == []
    assert len(guards) == 1
    assert receipts == []


def test_mapping_max_split_table_axis_never_derives_cross_region_parent() -> None:
    rows = _mapping_max_flat_rows(consulting=False)
    page = _page(
        _section(OWNER, _table(rows[:8], title=OWNER)),
        _section(OWNER, _table(rows[8:], title=OWNER)),
    )
    candidate, cluster, _receipt = _evaluate_adapter(page)
    assert len(cluster["component_regions"]) == 2
    assert not ({"ASSET_EXPENSE", "ADMIN_EXPENSE"} & _mapping_by_role(candidate).keys())
    adapter_receipt = candidate["closure_receipt"][
        "operating_expense_adapter_receipt"
    ]
    assert adapter_receipt["flat_parent_projection_receipts"] == []


def test_mapping_max_printed_parent_vetoes_derived_flat_parent() -> None:
    asset = "Chi về tài sản"
    rows = _mapping_max_flat_rows(consulting=False)
    asset_labels = {
        "Chi phí thuê văn phòng và tài sản",
        "Khấu hao và hao mòn tài sản cố định",
        "Chi phí bảo dưỡng và sửa chữa tài sản",
        "Chi phí dụng cụ và thiết bị",
    }
    admin_labels = {
        "Chi phí in ấn, tiếp thị và khuyến mại",
        "Chi phí công nghệ thông tin (*)",
        "Chi phí thông tin liên lạc",
        "Chi phí điện nước, vệ sinh văn phòng",
        "Công tác phí",
    }
    rows = [row for row in rows if row["label_exact"] not in admin_labels]
    for row in rows:
        if row["label_exact"] in asset_labels:
            row["hierarchy_path_exact"] = [asset, row["label_exact"]]
    rows.insert(2, _row(asset, "25", "18", kind="SUBTOTAL"))
    rows[-1]["values_exact"] = ["74", "58"]

    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["ASSET_EXPENSE"]) == [25, 18]
    assert by_role["ASSET_EXPENSE"]["source_refs"][0]["row_ordinal"] == 3
    assert by_role["ASSET_EXPENSE"]["state"] != (
        "DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM"
    )
    flat_receipts = candidate["closure_receipt"][
        "operating_expense_adapter_receipt"
    ]["flat_parent_projection_receipts"]
    assert all(
        receipt["result_role"] != "ASSET_EXPENSE" for receipt in flat_receipts
    )


@pytest.mark.parametrize(
    "other_label",
    [
        "Chi khác cho hoạt động quản lý",
        "Chi phí hoạt động khác",
        "Chi khác",
    ],
)
def test_mapping_max_other_leaf_survives_nonexhaustive_printed_admin_parent(
    other_label: str,
) -> None:
    admin = "Chi cho hoạt động quản lý công vụ"
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        _row("Chi phí cho nhân viên", "2", "2"),
        _row("Chi về tài sản", "3", "3"),
        _row(admin, "100", "90", kind="SUBTOTAL"),
        _row("Công tác phí", "10", "8", path=[admin, "Công tác phí"]),
        _row(other_label, "20", "18", path=[admin, other_label]),
        _row(None, "106", "96", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == READY
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["ADMIN_EXPENSE"]) == [100, 90]
    other = by_role["OTHER_OPERATING_EXPENSE"]
    assert _coefficients(other) == [20, 18]
    assert {ref["row_ordinal"] for ref in other["source_refs"]} == {6}
    assert all(
        mapping["role"] != "ADMIN_EXPENSE"
        or mapping["state"] != "DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM"
        for mapping in candidate["mappings"]
    )


@pytest.mark.parametrize(
    "other_label",
    [
        "Chi khác cho hoạt động quản lý",
        "Chi phí hoạt động khác",
        "Chi khác",
    ],
)
def test_mapping_max_broad_other_carrier_with_children_fails_closed(
    other_label: str,
) -> None:
    admin = "Chi cho hoạt động quản lý công vụ"
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        _row("Chi phí cho nhân viên", "2", "2"),
        _row("Chi về tài sản", "3", "3"),
        _row(admin, "100", "90", kind="SUBTOTAL"),
        _row(other_label, "60", "50", kind="SUBTOTAL", path=[admin, other_label]),
        _row("Công tác phí", "10", "8", path=[admin, other_label, "Công tác phí"]),
        _row(
            "Chi phí hoạt động khác",
            "50",
            "42",
            path=[admin, other_label, "Chi phí hoạt động khác"],
        ),
        _row(None, "106", "96", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "OPERATING_EXPENSE_BROAD_OTHER_CARRIER_IS_NOT_EXACT_RESIDUAL_LEAF" in (
        candidate["reasons"]
    )


def test_mapping_max_printed_other_subtotal_without_nested_paths_fails_closed() -> None:
    admin = "Chi cho hoạt động quản lý công vụ"
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        _row("Chi phí cho nhân viên", "2", "2"),
        _row("Chi về tài sản", "3", "3"),
        _row(admin, "100", "90", kind="SUBTOTAL"),
        _row(
            "Chi phí hoạt động khác",
            "60",
            "50",
            kind="SUBTOTAL",
            path=[admin, "Chi phí hoạt động khác"],
        ),
        _row("Công tác phí", "10", "8", path=[admin, "Công tác phí"]),
        _row(
            "Chi khác cho hoạt động quản lý",
            "50",
            "42",
            path=[admin, "Chi khác cho hoạt động quản lý"],
        ),
        _row(None, "106", "96", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "OPERATING_EXPENSE_BROAD_OTHER_CARRIER_IS_NOT_EXACT_RESIDUAL_LEAF" in (
        candidate["reasons"]
    )


def test_s08_blank_is_not_zero_and_blocks_incomplete_flat_parent_derivation() -> None:
    rows = _mapping_max_flat_rows(consulting=False)
    rows[2]["values_exact"] = ["-", None]
    rows[-1]["values_exact"] = ["74", "58"]
    page = _operating_page(rows)
    before = copy.deepcopy(page)
    candidate, _cluster_value, _receipt = _evaluate_adapter(page)
    assert page == before
    assert candidate["status"] == READY
    assert "ASSET_EXPENSE" not in _mapping_by_role(candidate)
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    rent = next(
        item
        for item in source_only
        if item["declared_role"] == "FLAT_ASSET_RENT_SOURCE_ONLY"
    )
    assert rent["source_ref"]["row_ordinal"] == 3
    assert page["sections"][0]["tables"][0]["rows"][2]["values_exact"] == [
        "-",
        None,
    ]


def test_s09_continuation_requires_reciprocal_adjacent_structural_proof() -> None:
    base, pages, compiled = _continuation_query_fixture()
    positive = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    assert "operating_expense_continuation_query_receipt" in positive[
        "candidate_dispositions"
    ][0]["cluster"]

    broken_pages = copy.deepcopy(pages)
    broken_pages[1][CONTINUATION_VERSION_ID]["sections"][0]["tables"][0][
        "continuation"
    ] = "NONE"
    broken_base = _rebuild_continuation_query_fixture(broken_pages, compiled)
    broken = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=broken_base,
        page_json_by_document=broken_pages,
        compiled_specs=compiled,
    )
    assert "operating_expense_continuation_query_receipt" not in broken[
        "candidate_dispositions"
    ][0]["cluster"]


def test_s10_reversed_physical_columns_keep_semantic_lane_and_origin() -> None:
    _base, pages, compiled = _continuation_query_fixture()
    _prior, receiver = _alignment_tables(pages)
    _alignment_headers(receiver, "Kỳ này", "Kỳ trước")
    _reverse_alignment_columns_and_values(receiver)
    _indexed, trial = _run_alignment_fixture(pages, compiled)
    _alignment_root_with_exact_source_ref(trial, pages)
    mapping_refs = [
        ref
        for mapping in trial["mappings"]
        for ref in mapping["source_refs"]
        if ref["locator"]["physical_page"] == 2
    ]
    assert mapping_refs
    assert all(ref["money_column_ordinals"] == [2, 1] for ref in mapping_refs)


def test_s11_rnid1218_aggregates_only_explicit_long_term_and_bad_debt_union() -> None:
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        _row("Chi phí cho nhân viên", "2", "2"),
        _row("Chi về tài sản", "3", "3"),
        _row("Chi cho hoạt động quản lý công vụ", "4", "4"),
        _row("Trích lập dự phòng giảm giá đầu tư dài hạn", "5", "7"),
        _row("Trích lập dự phòng nợ phải thu khó đòi", "6", "8"),
        _row(None, "21", "25", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    provision = _mapping_by_role(candidate)["LONG_TERM_BAD_DEBT_PROVISION"]
    assert _coefficients(provision) == [11, 15]
    assert {ref["row_ordinal"] for ref in provision["source_refs"]} == {5, 6}

    negative = _row(
        "Chi phí dự phòng đầu tư (không tính chi phí dự phòng rủi ro tín dụng nội và ngoại bảng; chi phí dự phòng giảm giá chứng khoán)",
        "5",
        "7",
    )
    table = _table([negative], title=OWNER)
    page = _page(_section(OWNER, table))
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, page["sections"][0], table, compiled_specs=_adapter_compiled()
    )
    assert "LONG_TERM_BAD_DEBT_PROVISION" not in {
        hit["role"] for hit in classification["role_hits"]
    }


def test_s12_printed_parent_wins_and_partial_child_never_backsolves_residual() -> None:
    asset = "Chi về tài sản"
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        _row("Chi phí cho nhân viên", "2", "2"),
        _row(asset, "100", "90", kind="SUBTOTAL"),
        _row("Trong đó: Khấu hao tài sản cố định", "40", "30", path=[asset, "Trong đó: Khấu hao tài sản cố định"]),
        _row("Chi cho hoạt động quản lý công vụ", "3", "3"),
        _row(None, "106", "96", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    by_role = _mapping_by_role(candidate)
    assert _coefficients(by_role["ASSET_EXPENSE"]) == [100, 90]
    assert _coefficients(by_role["DEPRECIATION_EXPENSE"]) == [40, 30]
    assert _coefficients(by_role["FAMILY_ROOT_TOTAL"]) == [106, 96]
    assert not any(
        mapping["state"] == "DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM"
        and mapping["role"] == "ASSET_EXPENSE"
        for mapping in candidate["mappings"]
    )


def test_s13_continuation_origin_receipt_rejects_locator_substitution() -> None:
    _base, pages, compiled = _continuation_query_fixture()
    prior = pages[1]
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=_base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    regions = indexed["candidate_dispositions"][0]["cluster"]["component_regions"]
    projected_pages, projected_regions, receipt = operating_expense_adapter._continuation_projection(
        pages=prior,
        regions=regions,
        compiled_specs=compiled,
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=projected_regions,
        page_json_by_version=projected_pages,
        compiled_specs=compiled,
        query_receipt=receipt["projected_query_receipt"],
    )
    attacked = copy.deepcopy(receipt)
    attacked["row_projections"][0]["before_locator"]["page_json_version_id"] = "gfpstorev1:json:" + "9" * 64
    with pytest.raises(
        GeminiJsonOperatingExpenseFamilyV1Error,
        match="source locator drifted",
    ):
        operating_expense_adapter._restore_continuation_mapping_source_refs(
            candidate, receipt=attacked
        )


def test_s14_numbered_neighbor_resets_wrapper_scope_before_asset_other() -> None:
    employee = "2. Chi phí cho nhân viên"
    asset = "3. Chi về tài sản"
    rows = [
        _row(employee, "100", "90", kind="SUBTOTAL"),
        _row("Trong đó:", None, None, kind="GROUP", path=["Trong đó:"]),
        _row("Chi lương và phụ cấp", "80", "72", path=["Trong đó:", "Chi lương và phụ cấp"]),
        _row("Chi trang phục giao dịch", "20", "18", path=["Trong đó:", "Chi trang phục giao dịch"]),
        _row(asset, "10", "9", kind="SUBTOTAL"),
        _row("Chi khác", "10", "9", path=[asset, "Chi khác"]),
        _row("4. Chi cho hoạt động quản lý công vụ", "5", "4"),
        _row(None, "115", "103", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster_value, _receipt = _evaluate_adapter(_operating_page(rows))
    by_role = _mapping_by_role(candidate)
    assert {ref["row_ordinal"] for ref in by_role["OTHER_EMPLOYEE_EXPENSE"]["source_refs"]} == {4}
    assert "OTHER_OPERATING_EXPENSE" not in by_role


def test_s15_mapping_and_receipts_are_deterministic_and_source_tamper_fails() -> None:
    page = _operating_page(_mapping_max_flat_rows(consulting=True))
    first, cluster, receipt = _evaluate_adapter(page)
    second, _cluster_value, _receipt = _evaluate_adapter(copy.deepcopy(page))
    assert first == second
    attacked = copy.deepcopy(first)
    attacked["mappings"][0]["source_refs"][0]["row_ordinal"] = 999
    with pytest.raises(GeminiJsonOperatingExpenseFamilyV1Error):
        validate_gemini_json_operating_expense_candidate_replay_v1(
            attacked,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            selected_page_axis=[],
            compiled_specs=_adapter_compiled(),
            query_receipt=receipt,
        )


def test_s16_schema_less_child_is_coverage_not_a_false_scalar() -> None:
    asset = "Chi về tài sản"
    rows = [
        _row("Chi nộp thuế và các khoản phí, lệ phí", "10", "8"),
        _row("Chi phí cho nhân viên", "30", "25"),
        _row(asset, "20", "15", kind="SUBTOTAL"),
        _row("Chi khấu hao tài sản cố định", "12", "10", path=[asset, "Chi khấu hao tài sản cố định"]),
        _row("Chi thuê tài sản", "8", "5", path=[asset, "Chi thuê tài sản"]),
        _row("Chi cho hoạt động quản lý công vụ", "15", "12"),
        _row("Chi nộp phí bảo hiểm tiền gửi của khách hàng", "5", "4"),
        _row(None, "80", "64", kind="TOTAL", path=[None]),
    ]
    page = _operating_page(rows)
    indexed, trials, pages, compiled = _source_row_coverage_inputs(page)
    receipt = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    rent = next(
        row
        for row in receipt["source_row_axis"]
        if row["label_exact"] == "Chi thuê tài sản"
    )
    assert rent["coverage"] == "EQUATION_CONSUMED_DECLARED_SOURCE_ONLY_ROLE_ROW"
    assert rent["report_norm_id"] is None
    assert not any(
        ref["row_ordinal"] == 5
        for mapping in trials[0]["mappings"]
        for ref in mapping["source_refs"]
        if mapping["role"] != "FAMILY_ROOT_TOTAL"
    )


def test_s17_root_partition_counts_parents_not_mapped_details_twice() -> None:
    candidate, _cluster_value, _receipt = _evaluate_adapter(
        _operating_page(_mapping_max_flat_rows(consulting=False))
    )
    by_role = _mapping_by_role(candidate)
    root_roles = (
        "EMPLOYEE_EXPENSE",
        "ASSET_EXPENSE",
        "ADMIN_EXPENSE",
        "TAX_FEES",
        "DEPOSIT_INSURANCE_EXPENSE",
        "OTHER_OPERATING_EXPENSE",
        "OTHER_ASSET_PROVISION",
    )
    assert sum(_coefficients(by_role[role])[0] for role in root_roles) == 86
    assert _coefficients(by_role["FAMILY_ROOT_TOTAL"]) == [86, 68]
    assert _coefficients(by_role["DEPRECIATION_EXPENSE"]) == [8, 5]
    assert _coefficients(by_role["TRAVEL_EXPENSE"]) == [1, 1]


def test_s18_same_label_in_unrelated_note_never_enters_f36_population() -> None:
    unrelated = _table([_row("Chi phí hoạt động khác", "999", "888")])
    page = _page(
        _section("Giao dịch với các bên liên quan", unrelated),
        _section(OWNER, _table(_base_rows())),
    )
    candidate, cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    other = _mapping_by_role(candidate)["OTHER_OPERATING_EXPENSE"]
    assert _coefficients(other) == [10, 8]
    assert {ref["locator"]["section_id"] for ref in other["source_refs"]} == {"s2"}
    assert {region["section_id"] for region in cluster["component_regions"]} == {"s2"}
