from __future__ import annotations

import json
from copy import deepcopy

import pytest
from test_gemini_financial_page_json_v1 import _page

from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    GeminiJsonRegionRepairV1Error,
    build_region_repair_prompt_v1,
    build_section_narrative_repair_prompt_v1,
    build_table_axis_repair_prompt_v1,
    decode_region_repair_text_v1,
    decode_section_narrative_repair_text_v1,
    decode_table_axis_repair_text_v1,
    merge_region_repair_v1,
    merge_section_narrative_repair_v1,
    merge_table_axis_repair_v1,
    region_repair_response_schema_v1,
    region_repair_targets_v1,
    section_narrative_repair_response_schema_v1,
    section_narrative_repair_targets_v1,
    table_axis_repair_response_schema_v1,
    table_axis_repair_targets_v1,
)


def test_targeted_region_repair_changes_only_one_bound_row_value_axis() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"] = ["-ktCap-", None]
    targets = region_repair_targets_v1(page, target_ids=["s1:t1:r2"])
    prompt = build_region_repair_prompt_v1(
        base_page_json_version_id="gfpstorev1:json:" + "1" * 64,
        targets=targets,
    )
    assert "không dùng tổng để suy ra" in prompt.lower()
    assert "dấu âm" in prompt.lower()
    assert "bên trái/phải" in prompt.lower()
    assert [row["target_id"] for row in targets[0]["context_rows_exact"]] == [
        "s1:t1:r1",
        "s1:t1:r2",
        "s1:t1:r3",
    ]
    context_page = deepcopy(page)
    context_page["sections"][0]["tables"][0]["rows"].append(
        deepcopy(context_page["sections"][0]["tables"][0]["rows"][0])
    )
    wider = region_repair_targets_v1(context_page, target_ids=["s1:t1:r2"], context_radius=2)
    assert len(wider[0]["context_rows_exact"]) > len(targets[0]["context_rows_exact"])
    assert "context_rows_exact" in prompt
    assert region_repair_response_schema_v1()["additionalProperties"] is False
    repair = {
        "all_targets_transcribed": True,
        "rows": [
            {
                "label_exact": targets[0]["label_exact"],
                "target_id": "s1:t1:r2",
                "values_exact": ["-", None],
            }
        ],
        "uncertainty_exact": [],
    }
    merged, receipt = merge_region_repair_v1(
        page,
        base_page_json_version_id="gfpstorev1:json:" + "1" * 64,
        targets=targets,
        repair=repair,
    )
    expected = deepcopy(page)
    expected["sections"][0]["tables"][0]["rows"][1]["values_exact"] = ["-", None]
    assert merged == expected
    assert receipt["changes"] == [
        {
            "target_id": "s1:t1:r2",
            "values_after_exact": ["-", None],
            "values_before_exact": ["-ktCap-", None],
        }
    ]


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda value: value.update(all_targets_transcribed=False), "incomplete"),
        (lambda value: value["uncertainty_exact"].append("mờ"), "incomplete"),
        (lambda value: value["rows"][0].update(target_id="s1:t1:r3"), "identity"),
        (lambda value: value["rows"][0].update(label_exact="Dòng khác"), "does not bind"),
        (lambda value: value["rows"][0].update(values_exact=["-"]), "value axis"),
    ],
)
def test_targeted_region_repair_fails_closed_on_incomplete_or_wrong_row(
    mutation, match: str
) -> None:
    page = _page()
    targets = region_repair_targets_v1(page, target_ids=["s1:t1:r2"])
    value = {
        "all_targets_transcribed": True,
        "rows": [
            {
                "label_exact": targets[0]["label_exact"],
                "target_id": "s1:t1:r2",
                "values_exact": ["20", "10"],
            }
        ],
        "uncertainty_exact": [],
    }
    mutation(value)
    if "incomplete" in match:
        with pytest.raises(GeminiJsonRegionRepairV1Error, match=match):
            merge_region_repair_v1(
                page,
                base_page_json_version_id="gfpstorev1:json:" + "1" * 64,
                targets=targets,
                repair=value,
            )
    else:
        with pytest.raises(GeminiJsonRegionRepairV1Error, match=match):
            decode_region_repair_text_v1(json.dumps(value), targets=targets)


def test_targeted_region_repair_can_bind_an_unlabeled_visible_total_by_row_identity() -> None:
    page = _page()
    row = page["sections"][0]["tables"][0]["rows"][2]
    row["label_exact"] = None
    row["hierarchy_path_exact"] = [None]
    row["row_kind"] = "TOTAL"
    targets = region_repair_targets_v1(page, target_ids=["s1:t1:r3"])
    repair = {
        "all_targets_transcribed": True,
        "rows": [
            {
                "label_exact": None,
                "target_id": "s1:t1:r3",
                "values_exact": ["30", "20"],
            }
        ],
        "uncertainty_exact": [],
    }
    merged, _receipt = merge_region_repair_v1(
        page,
        base_page_json_version_id="gfpstorev1:json:" + "1" * 64,
        targets=targets,
        repair=repair,
    )
    assert merged["sections"][0]["tables"][0]["rows"][2]["values_exact"] == ["30", "20"]


def test_targeted_region_repair_can_reread_one_truncated_label_and_its_values() -> None:
    page = _page()
    row = page["sections"][0]["tables"][0]["rows"][1]
    row["label_exact"] = "Cho vay chiết khấu công cụ chuyển nhượng và các"
    row["hierarchy_path_exact"] = [row["label_exact"]]
    row["values_exact"] = ["625.084", "1.745.674"]
    targets = region_repair_targets_v1(
        page,
        target_ids=["s1:t1:r2"],
        allow_label_change=True,
    )
    prompt = build_region_repair_prompt_v1(
        base_page_json_version_id="gfpstorev1:json:" + "3" * 64,
        targets=targets,
    )
    assert "đọc lại toàn bộ nhãn" in prompt
    repaired_label = "Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá"
    repair = {
        "all_targets_transcribed": True,
        "rows": [
            {
                "label_exact": repaired_label,
                "target_id": "s1:t1:r2",
                "values_exact": ["625.084", "1.745.674"],
            }
        ],
        "uncertainty_exact": [],
    }
    decoded = decode_region_repair_text_v1(json.dumps(repair), targets=targets)
    merged, receipt = merge_region_repair_v1(
        page,
        base_page_json_version_id="gfpstorev1:json:" + "3" * 64,
        targets=targets,
        repair=decoded,
    )
    merged_row = merged["sections"][0]["tables"][0]["rows"][1]
    assert merged_row["label_exact"] == repaired_label
    assert merged_row["hierarchy_path_exact"] == [repaired_label]
    assert receipt["changes"][0]["label_before_exact"].endswith("và các")
    assert receipt["changes"][0]["label_after_exact"] == repaired_label


def test_table_axis_repair_changes_only_bound_title_and_column_headers() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    targets = table_axis_repair_targets_v1(
        page, table_refs=[{"section_id": "s1", "table_id": "t1"}]
    )
    prompt = build_table_axis_repair_prompt_v1(
        base_page_json_version_id="gfpstorev1:json:" + "2" * 64,
        targets=targets,
    )
    assert "mọi ngày/kỳ" in prompt
    assert "tiêu đề tiểu mục" in prompt
    assert "không rút gọn chỉ còn dòng tiểu mục" in prompt
    assert table_axis_repair_response_schema_v1()["additionalProperties"] is False
    repair = {
        "all_targets_transcribed": True,
        "tables": [
            {
                "columns_header_path_exact": [
                    ["Tại ngày 30/06/2025", *column["header_path_exact"]]
                    for column in table["columns"]
                ],
                "table_title_exact": "Tại ngày 30/06/2025",
                "target_id": "s1:t1",
            }
        ],
        "uncertainty_exact": [],
    }
    assert decode_table_axis_repair_text_v1(json.dumps(repair), targets=targets) == repair
    merged, receipt = merge_table_axis_repair_v1(
        page,
        base_page_json_version_id="gfpstorev1:json:" + "2" * 64,
        targets=targets,
        repair=repair,
    )
    assert merged["sections"][0]["tables"][0]["title_exact"] == "Tại ngày 30/06/2025"
    assert merged["sections"][0]["tables"][0]["rows"] == table["rows"]
    assert receipt["changes"][0]["target_id"] == "s1:t1"


def test_table_axis_repair_rejects_missing_or_shifted_columns() -> None:
    page = _page()
    targets = table_axis_repair_targets_v1(
        page, table_refs=[{"section_id": "s1", "table_id": "t1"}]
    )
    repair = {
        "all_targets_transcribed": True,
        "tables": [
            {
                "columns_header_path_exact": [["31/12/2025"]],
                "table_title_exact": None,
                "target_id": "s1:t1",
            }
        ],
        "uncertainty_exact": [],
    }
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="column axis"):
        decode_table_axis_repair_text_v1(json.dumps(repair), targets=targets)


def test_section_narrative_repair_replaces_only_bound_section_narratives() -> None:
    page = _page()
    section = page["sections"][0]
    section["narratives_exact"] = []
    targets = section_narrative_repair_targets_v1(
        page, table_refs=[{"section_id": "s1", "table_id": "t1"}]
    )
    prompt = build_section_narrative_repair_prompt_v1(
        base_page_json_version_id="gfpstorev1:json:" + "4" * 64,
        targets=targets,
    )
    assert "nằm ngoài các ô của bảng" in prompt
    assert "không chép lại dòng hoặc số trong bảng" in prompt.lower()
    assert section_narrative_repair_response_schema_v1()["additionalProperties"] is False
    narrative = (
        "(*) Không bao gồm 9.423.424 triệu đồng (31.12.2024: 8.689.759 triệu đồng) "
        "cho vay giao dịch ký quỹ."
    )
    repair = {
        "all_targets_transcribed": True,
        "sections": [{"narratives_exact": [narrative], "target_id": "s1"}],
        "uncertainty_exact": [],
    }
    assert decode_section_narrative_repair_text_v1(json.dumps(repair), targets=targets) == repair
    merged, receipt = merge_section_narrative_repair_v1(
        page,
        base_page_json_version_id="gfpstorev1:json:" + "4" * 64,
        targets=targets,
        repair=repair,
    )
    assert merged["sections"][0]["narratives_exact"] == [narrative]
    assert merged["sections"][0]["tables"] == page["sections"][0]["tables"]
    assert receipt["changes"] == [
        {
            "narratives_after_exact": [narrative],
            "narratives_before_exact": [],
            "target_id": "s1",
        }
    ]

    uncertain = deepcopy(repair)
    uncertain["uncertainty_exact"] = ["Không đọc chắc chú thích"]
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="incomplete or uncertain"):
        merge_section_narrative_repair_v1(
            page,
            base_page_json_version_id="gfpstorev1:json:" + "4" * 64,
            targets=targets,
            repair=uncertain,
        )
