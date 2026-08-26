from __future__ import annotations

import copy
import json

import pytest

from bctc_ai.evaluation.hosted_gemma4_hierarchical_note_json_v1 import (
    HostedGemma4HierarchicalNoteJsonV1Error,
    build_hierarchical_note_json_prompt_v1,
    decode_hierarchical_note_json_text_v1,
    evaluate_direct_sum_v1,
    hierarchical_note_json_response_schema_v1,
    parse_vietnamese_numeric_surface_v1,
    select_family_table_v1,
    validate_hierarchical_note_json_v1,
)


def _columns() -> list[dict[str, object]]:
    return [
        {
            "column_id": "c1",
            "header_path": ["31/03/2025", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "column_id": "c2",
            "header_path": ["31/03/2025", "%"],
            "value_kind": "PERCENT",
        },
        {
            "column_id": "c3",
            "header_path": ["31/12/2024", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "column_id": "c4",
            "header_path": ["31/12/2024", "%"],
            "value_kind": "PERCENT",
        },
    ]


def _row(
    ordinal: int,
    label: str | None,
    path: list[str | None],
    values: list[str | None],
    *,
    kind: str = "ITEM",
) -> dict[str, object]:
    return {
        "hierarchy_path": path,
        "label": label,
        "row_id": f"r{ordinal + 1}",
        "row_kind": kind,
        "source_order": ordinal,
        "values": values,
    }


def _family_table() -> dict[str, object]:
    root = "Dư nợ cho vay khách hàng của Ngân hàng"
    tckt = "Cho vay các TCKT"
    return {
        "columns": _columns(),
        "rows": [
            _row(0, root, [root], [None, None, None, None], kind="GROUP"),
            _row(
                1,
                tckt,
                [root, tckt],
                ["434.609.559", "54,50", "425.746.734", "54,81"],
                kind="SUBTOTAL",
            ),
            _row(
                2,
                "Công ty Nhà nước",
                [root, tckt, "Công ty Nhà nước"],
                ["29.412.253", "3,69", "30.754.076", "3,96"],
            ),
            _row(
                3,
                "Công ty TNHH khác",
                [root, tckt, "Công ty TNHH khác"],
                ["130.161.162", "16,32", "130.491.477", "16,80"],
            ),
            _row(
                4,
                "Công ty cổ phần khác",
                [root, tckt, "Công ty cổ phần khác"],
                ["275.036.144", "34,49", "264.501.181", "34,05"],
            ),
            _row(
                5,
                None,
                [root, None],
                ["434.609.559", "54,50", "425.746.734", "54,81"],
                kind="TOTAL",
            ),
        ],
        "title": "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
        "unit": "Triệu đồng",
    }


def _other_table() -> dict[str, object]:
    return {
        "columns": _columns(),
        "rows": [
            _row(
                0,
                "Nông nghiệp, lâm nghiệp và thủy sản",
                ["Dư nợ theo ngành kinh tế", "Nông nghiệp, lâm nghiệp và thủy sản"],
                ["1.000", "1,00", "900", "0,90"],
            )
        ],
        "title": "Phân tích dư nợ cho vay theo ngành kinh tế",
        "unit": "Triệu đồng",
    }


def _output(*tables: dict[str, object]) -> dict[str, object]:
    return {"status": "HAS_NOTE_TABLES", "tables": list(tables)}


def _signature() -> dict[str, object]:
    return {
        "disambiguators": [
            {
                "left_aliases": ["Công ty Nhà nước"],
                "relation": "SIBLING_BEFORE",
                "right_aliases": ["Công ty TNHH khác"],
            }
        ],
        "family_id": "loan_enterprise_family12",
        "primary_relation": {
            "left_aliases": [
                "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp"
            ],
            "relation": "TABLE_HAS_DESCENDANT",
            "right_aliases": ["Công ty Nhà nước"],
        },
    }


def test_prompt_is_short_schema_blind_and_fixes_one_shape() -> None:
    prompt = build_hierarchical_note_json_prompt_v1()
    assert len(prompt) < 1_800
    assert "ReportNormId" not in prompt
    assert "schema" not in prompt.casefold()
    assert '"status":"NO_NOTE_TABLES"' in prompt
    assert "columns chỉ gồm các cột giá trị" in prompt


def test_response_schema_is_fixed_and_provider_neutral() -> None:
    schema = hierarchical_note_json_response_schema_v1()
    assert schema["required"] == ["status", "tables"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["status"]["enum"]) == {
        "HAS_NOTE_TABLES",
        "NO_NOTE_TABLES",
    }
    assert "model" not in str(schema).casefold()
    assert "family" not in str(schema).casefold()


def test_closed_json_decodes_plain_or_one_outer_fence() -> None:
    value = _output(_family_table())
    payload = json.dumps(value, ensure_ascii=False)
    assert decode_hierarchical_note_json_text_v1(payload) == value
    assert decode_hierarchical_note_json_text_v1(f"```json\n{payload}\n```") == value
    assert validate_hierarchical_note_json_v1({"status": "NO_NOTE_TABLES", "tables": []})


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra=True),
        lambda value: value["tables"][0]["columns"][0].update(column_id="c2"),
        lambda value: value["tables"][0]["rows"][0].update(source_order=1),
        lambda value: value["tables"][0]["rows"][1].update(hierarchy_path=["wrong"]),
        lambda value: value["tables"][0]["rows"][1].update(values=["1"]),
        lambda value: value.update(status="NO_NOTE_TABLES"),
    ],
)
def test_shape_drift_is_not_repaired(mutation) -> None:
    value = _output(_family_table())
    mutation(value)
    with pytest.raises(HostedGemma4HierarchicalNoteJsonV1Error):
        validate_hierarchical_note_json_v1(value)


def test_duplicate_json_key_rejects() -> None:
    with pytest.raises(HostedGemma4HierarchicalNoteJsonV1Error, match="duplicate JSON key"):
        decode_hierarchical_note_json_text_v1(
            '{"status":"NO_NOTE_TABLES","status":"NO_NOTE_TABLES","tables":[]}'
        )


def test_two_item_relation_selects_the_family_region_and_negative_page_abstains() -> None:
    selection = select_family_table_v1(_output(_other_table(), _family_table()), _signature())
    assert selection["status"] == "SELECTED"
    assert selection["stage"] == "PRIMARY_TWO_ITEM"
    assert selection["selected_table_index"] == 1
    assert select_family_table_v1(_output(_other_table()), _signature()) == {
        "candidate_table_indices": [],
        "stage": "PRIMARY_TWO_ITEM",
        "status": "NO_MATCH",
    }


def test_third_item_relation_is_used_only_after_two_item_ambiguity() -> None:
    partial = copy.deepcopy(_family_table())
    partial["rows"] = partial["rows"][:3]
    for ordinal, row in enumerate(partial["rows"], start=1):
        row["row_id"] = f"r{ordinal}"
        row["source_order"] = ordinal - 1
    selection = select_family_table_v1(_output(partial, _family_table()), _signature())
    assert selection["status"] == "SELECTED"
    assert selection["stage"] == "THIRD_ITEM_DISAMBIGUATION"
    assert selection["candidate_table_indices"] == [0, 1]
    assert selection["selected_table_index"] == 1


def test_two_equally_complete_regions_remain_ambiguous() -> None:
    selection = select_family_table_v1(
        _output(_family_table(), copy.deepcopy(_family_table())), _signature()
    )
    assert selection == {
        "candidate_table_indices": [0, 1],
        "stage": "THIRD_ITEM_DISAMBIGUATION",
        "status": "AMBIGUOUS",
    }


def test_direct_equation_uses_only_declared_rows_and_all_lanes() -> None:
    equation = evaluate_direct_sum_v1(
        _family_table(), result_row_id="r2", component_row_ids=["r3", "r4", "r5"]
    )
    assert equation["exact_all_numeric_lanes"] is True
    assert [lane["exact"] for lane in equation["lane_results"]] == [True] * 4
    changed = _family_table()
    changed["rows"][4]["values"][0] = "275.036.143"
    assert (
        evaluate_direct_sum_v1(changed, result_row_id="r2", component_row_ids=["r3", "r4", "r5"])[
            "exact_all_numeric_lanes"
        ]
        is False
    )


def test_numeric_parser_preserves_sign_scale_and_rejects_mixed_separator() -> None:
    assert parse_vietnamese_numeric_surface_v1("(1.234)", "MONEY").as_tuple().sign == 1
    assert parse_vietnamese_numeric_surface_v1("54,50", "PERCENT") == 54.50
    assert parse_vietnamese_numeric_surface_v1("-", "MONEY") == 0
    with pytest.raises(HostedGemma4HierarchicalNoteJsonV1Error, match="mixed separators"):
        parse_vietnamese_numeric_surface_v1("1,.43", "PERCENT")
    with pytest.raises(HostedGemma4HierarchicalNoteJsonV1Error):
        evaluate_direct_sum_v1(_family_table(), result_row_id="r2", component_row_ids=["r3", "r3"])
