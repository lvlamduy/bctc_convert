from __future__ import annotations

import copy
import json

import pytest

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    GeminiFinancialPageJsonV1Error,
    build_financial_page_json_prompt_v1,
    count_financial_page_content_v1,
    decode_financial_page_json_text_v1,
    family_relation_candidates_v1,
    financial_page_json_response_schema_v1,
    normalize_search_text_v1,
    validate_financial_page_json_v1,
)


def _page() -> dict[str, object]:
    return {
        "status": "FINANCIAL_NOTE_CONTENT",
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "Cho vay khách hàng",
                "narratives_exact": [],
                "tables": [
                    {
                        "title_exact": "Phân tích theo loại hình doanh nghiệp",
                        "unit_exact": "Triệu đồng",
                        "continuation": "NONE",
                        "columns": [
                            {
                                "header_path_exact": ["31/12/2025"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31/12/2024"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "rows": [
                            {
                                "label_exact": "Cho vay các TCKT",
                                "hierarchy_path_exact": ["Cho vay các TCKT"],
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["434.609.559", "425.746.734"],
                            },
                            {
                                "label_exact": "Công ty Nhà nước",
                                "hierarchy_path_exact": [
                                    "Cho vay các TCKT",
                                    "Công ty Nhà nước",
                                ],
                                "row_kind": "ITEM",
                                "values_exact": ["29.412.253", "30.754.076"],
                            },
                            {
                                "label_exact": None,
                                "hierarchy_path_exact": [None],
                                "row_kind": "TOTAL",
                                "values_exact": ["434.609.559", "425.746.734"],
                            },
                        ],
                    }
                ],
            }
        ],
    }


def test_prompt_variants_share_one_schema_blind_contract() -> None:
    simple = build_financial_page_json_prompt_v1(variant="simple")
    compact = build_financial_page_json_prompt_v1(variant="compact")
    balanced = build_financial_page_json_prompt_v1(variant="balanced")
    assert len(simple) < 1_000
    assert len(compact) < 2_100
    assert len(balanced) < 3_000
    assert len(simple) < len(compact) < len(balanced)
    assert "Bảng cân đối kế toán" in compact
    assert "không dịch vector" in balanced
    for prompt in (simple, compact, balanced):
        assert "ReportNormId" not in prompt
        assert "Family12" not in prompt
        assert "NO_RELEVANT_FINANCIAL_CONTENT" in prompt
        assert 'chuỗi "0"' in prompt
    for prompt in (compact, balanced):
        assert 'gạch dưới "_"' in prompt
    schema = financial_page_json_response_schema_v1()
    assert schema["required"] == ["status", "sections", "completion"]
    assert list(schema["properties"]) == ["status", "sections", "completion"]
    assert schema["additionalProperties"] is False


def test_exact_page_validation_and_content_counts() -> None:
    assert validate_financial_page_json_v1(_page()) == _page()
    payload = json.dumps(_page(), ensure_ascii=False)
    assert decode_financial_page_json_text_v1(payload) == _page()
    assert decode_financial_page_json_text_v1(f"```json\n{payload}\n```") == _page()
    assert count_financial_page_content_v1(_page()) == {
        "cell_count": 6,
        "populated_cell_count": 6,
        "row_count": 3,
        "section_count": 1,
        "table_count": 1,
    }


def test_minimal_irrelevant_page_is_closed_and_cheap_on_output() -> None:
    empty = {
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
        "sections": [],
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
    }
    assert validate_financial_page_json_v1(empty) == empty
    invalid = copy.deepcopy(_page())
    invalid["status"] = "NO_RELEVANT_FINANCIAL_CONTENT"
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="disagree"):
        validate_financial_page_json_v1(invalid)


def test_unlabeled_column_and_titled_parent_section_are_preserved() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [None]
    page["sections"].append(
        {
            "content_kind": "FINANCIAL_NOTE",
            "statement_type": "NOT_APPLICABLE",
            "title_exact": "11. Thuế thu nhập doanh nghiệp",
            "narratives_exact": [],
            "tables": [],
        }
    )
    assert validate_financial_page_json_v1(page) == page


def test_anonymous_empty_relevant_section_rejects() -> None:
    page = _page()
    page["sections"].append(
        {
            "content_kind": "FINANCIAL_NOTE",
            "statement_type": "NOT_APPLICABLE",
            "title_exact": None,
            "narratives_exact": [],
            "tables": [],
        }
    )
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="must retain its title"):
        validate_financial_page_json_v1(page)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra=True),
        lambda value: value["sections"][0].update(source_order=0),
        lambda value: value["sections"][0]["tables"][0].update(table_id="t2"),
        lambda value: value["sections"][0]["tables"][0]["columns"][0].update(column_id="c2"),
        lambda value: value["sections"][0]["tables"][0]["rows"][1].update(
            hierarchy_path_exact=["Sai"]
        ),
        lambda value: value["sections"][0]["tables"][0]["rows"][1].update(values_exact=["1"]),
    ],
)
def test_model_shape_drift_is_never_repaired(mutation) -> None:
    value = copy.deepcopy(_page())
    mutation(value)
    with pytest.raises(GeminiFinancialPageJsonV1Error):
        validate_financial_page_json_v1(value)


def test_duplicate_keys_and_nonfinite_json_reject() -> None:
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="duplicate JSON key"):
        decode_financial_page_json_text_v1(
            '{"status":"NO_RELEVANT_FINANCIAL_CONTENT","status":'
            '"NO_RELEVANT_FINANCIAL_CONTENT","sections":[]}'
        )
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="non-finite"):
        decode_financial_page_json_text_v1('{"status":NaN,"sections":[]}')


def test_completion_receipt_is_simple_and_false_completion_rejects() -> None:
    bookkeeping = copy.deepcopy(_page())
    bookkeeping["completion"]["row_count"] = 3
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="fields drifted"):
        validate_financial_page_json_v1(bookkeeping)

    incomplete = copy.deepcopy(_page())
    incomplete["status"] = "UNRESOLVED_PAGE"
    incomplete["completion"]["all_relevant_content_transcribed"] = False
    incomplete["completion"]["uncertainty_exact"] = ["Phần cuối bảng không đọc chắc chắn"]
    assert validate_financial_page_json_v1(incomplete) == incomplete

    incomplete["completion"]["uncertainty_exact"] = []
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="requires"):
        validate_financial_page_json_v1(incomplete)


def test_cell_whitespace_is_preserved_and_derived_counts_ignore_formatting() -> None:
    dash = copy.deepcopy(_page())
    dash["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = " -"
    assert (
        validate_financial_page_json_v1(dash)["sections"][0]["tables"][0]["rows"][1][
            "values_exact"
        ][0]
        == " -"
    )

    numeric = copy.deepcopy(_page())
    numeric["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = " 29.412.253"
    assert (
        validate_financial_page_json_v1(numeric)["sections"][0]["tables"][0]["rows"][1][
            "values_exact"
        ][0]
        == " 29.412.253"
    )


def test_accentless_text_is_a_versioned_search_projection_only() -> None:
    projection = normalize_search_text_v1("  CÔNG TY   Nhà nước  ")
    assert projection["text_exact"] == "  CÔNG TY   Nhà nước  "
    assert projection["text_search_normalized"] == "công ty nhà nước"
    assert projection["text_ascii_folded"] == "cong ty nha nuoc"
    assert projection["normalization_version"]


def test_two_then_three_anchor_retrieval_stays_within_one_table() -> None:
    candidates = family_relation_candidates_v1(
        _page(),
        anchor_aliases=[["Cho vay các TCKT"], ["Cong ty Nha nuoc"]],
    )
    assert candidates == [
        {
            "anchor_row_ids": [["r1"], ["r2"]],
            "section_id": "s1",
            "table_id": "t1",
        }
    ]
    assert (
        family_relation_candidates_v1(
            _page(),
            anchor_aliases=[
                ["Cho vay các TCKT"],
                ["Công ty Nhà nước"],
                ["không tồn tại"],
            ],
        )
        == []
    )
