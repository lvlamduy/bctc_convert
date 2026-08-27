from __future__ import annotations

import json
from copy import deepcopy

import pytest
from test_gemini_financial_page_json_v1 import _page

from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    GeminiJsonRegionRepairV1Error,
    build_region_repair_prompt_v1,
    build_table_axis_repair_prompt_v1,
    decode_region_repair_text_v1,
    decode_table_axis_repair_text_v1,
    merge_region_repair_v1,
    merge_table_axis_repair_v1,
    region_repair_response_schema_v1,
    region_repair_targets_v1,
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
