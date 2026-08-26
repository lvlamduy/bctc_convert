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
    items = build_financial_page_json_prompt_v1(variant="items")
    compact = build_financial_page_json_prompt_v1(variant="compact")
    balanced = build_financial_page_json_prompt_v1(variant="balanced")
    assert len(simple) < 1_000
    assert len(compact) < 2_100
    assert len(balanced) < 3_000
    assert len(simple) < len(compact) < len(balanced)
    assert "Bảng cân đối kế toán" in compact
    assert "không dịch vector" in balanced
    for prompt in (simple, items, compact, balanced):
        assert "ReportNormId" not in prompt
        assert "Family12" not in prompt
        assert "NO_RELEVANT_FINANCIAL_CONTENT" in prompt
        assert 'chuỗi "0"' in prompt
    for prompt in (compact, balanced):
        assert 'gạch dưới "_"' in prompt
    assert "narratives_exact luôn là mảng rỗng" in items
    assert "Không chép các đoạn văn" in items
    assert "không bỏ sót hàng" in items
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


def test_redundant_printed_label_column_is_canonicalized_without_losing_cells() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"].insert(
        0,
        {
            "header_path_exact": ["Khoản mục"],
            "value_kind": "TEXT",
        },
    )
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["columns"] == table["columns"][1:]
    assert checked["sections"][0]["tables"][0]["rows"] == table["rows"]
    assert len(page["sections"][0]["tables"][0]["columns"]) == 3


def test_empty_label_and_merged_header_proxies_preserve_numeric_header_path() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Bên liên quan"], "value_kind": "TEXT"},
        {"header_path_exact": ["Số dư"], "value_kind": "TEXT"},
        {"header_path_exact": ["Phải thu"], "value_kind": "MONEY"},
        {"header_path_exact": ["Phải trả"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Các công ty con",
            "hierarchy_path_exact": ["Các công ty con"],
            "row_kind": "GROUP",
            "values_exact": [None, None, None],
        },
        {
            "label_exact": "- Tiền vay từ BIDV của các công ty con",
            "hierarchy_path_exact": [
                "Các công ty con",
                "- Tiền vay từ BIDV của các công ty con",
            ],
            "row_kind": "ITEM",
            "values_exact": ["1.741.711", None],
        },
    ]

    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert checked_table["columns"] == [
        {"header_path_exact": ["Số dư", "Phải thu"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư", "Phải trả"], "value_kind": "MONEY"},
    ]
    assert [row["values_exact"] for row in checked_table["rows"]] == [
        [None, None],
        ["1.741.711", None],
    ]


def test_primary_statement_label_column_is_removed_without_dropping_stt_or_note() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["STT"], "value_kind": "TEXT"},
        {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"},
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Lưu chuyển tiền từ hoạt động kinh doanh",
            "hierarchy_path_exact": ["Lưu chuyển tiền từ hoạt động kinh doanh"],
            "row_kind": "GROUP",
            "values_exact": [None, None, None],
        },
        {
            "label_exact": "Tiền thuế TNDN thực nộp trong kỳ",
            "hierarchy_path_exact": [
                "Lưu chuyển tiền từ hoạt động kinh doanh",
                "Tiền thuế TNDN thực nộp trong kỳ",
            ],
            "row_kind": "ITEM",
            "values_exact": ["8", "12", "(4,243,631)", "(4,753,960)"],
        },
    ]
    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert [column["header_path_exact"] for column in checked_table["columns"]] == [
        ["STT"],
        ["Thuyết minh"],
        ["Kỳ này"],
        ["Kỳ trước"],
    ]
    assert [row["values_exact"] for row in checked_table["rows"]] == [
        [None, None, None, None],
        ["8", "12", "(4,243,631)", "(4,753,960)"],
    ]


def test_uniform_omitted_stt_and_label_prefix_preserves_note_and_money_cells() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["STT"], "value_kind": "TEXT"},
        {"header_path_exact": ["CHỈ TIÊU"], "value_kind": "TEXT"},
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
        {"header_path_exact": ["Số cuối kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số đầu kỳ"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "B. NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU",
            "hierarchy_path_exact": ["B. NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU"],
            "row_kind": "GROUP",
            "values_exact": [None, None, None],
        },
        {
            "label_exact": "I. Các khoản nợ Chính phủ và Ngân hàng Trung ương",
            "hierarchy_path_exact": [
                "B. NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU",
                "I. Các khoản nợ Chính phủ và Ngân hàng Trung ương",
            ],
            "row_kind": "ITEM",
            "values_exact": ["12", "162.609.396", "168.388.958"],
        },
    ]

    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert [column["header_path_exact"] for column in checked_table["columns"]] == [
        ["Thuyết minh"],
        ["Số cuối kỳ"],
        ["Số đầu kỳ"],
    ]
    assert [row["values_exact"] for row in checked_table["rows"]] == [
        [None, None, None],
        ["12", "162.609.396", "168.388.958"],
    ]


def test_uniform_omitted_stt_prefix_preserves_descriptive_table_cells() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["STT"], "value_kind": "UNKNOWN"},
        {"header_path_exact": ["Tên công ty"], "value_kind": "TEXT"},
        {"header_path_exact": ["Giấy phép hoạt động số"], "value_kind": "TEXT"},
        {"header_path_exact": ["Lĩnh vực hoạt động"], "value_kind": "TEXT"},
        {"header_path_exact": ["Tỷ lệ sở hữu"], "value_kind": "PERCENT"},
    ]
    table["rows"] = [
        {
            "label_exact": "1",
            "hierarchy_path_exact": ["1"],
            "row_kind": "ITEM",
            "values_exact": ["Công ty A", "01/GP", "Ngân hàng", "49,50%"],
        },
        {
            "label_exact": "2",
            "hierarchy_path_exact": ["2"],
            "row_kind": "ITEM",
            "values_exact": ["Công ty B", "02/GP", "Bảo hiểm", "37,25%"],
        },
    ]

    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert checked_table["columns"] == table["columns"][1:]
    assert checked_table["rows"] == table["rows"]


def test_uniform_anonymous_count_prefix_is_bound_by_numeric_row_labels() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [None], "value_kind": "COUNT"},
        {"header_path_exact": [None], "value_kind": "TEXT"},
        {"header_path_exact": [None], "value_kind": "TEXT"},
        {"header_path_exact": [None], "value_kind": "TEXT"},
        {"header_path_exact": [None], "value_kind": "PERCENT"},
    ]
    table["rows"] = [
        {
            "label_exact": "6",
            "hierarchy_path_exact": ["6"],
            "row_kind": "ITEM",
            "values_exact": ["Công ty A", "077-08/ĐT", "Bảo hiểm", "33,15%"],
        },
        {
            "label_exact": "7",
            "hierarchy_path_exact": ["7"],
            "row_kind": "ITEM",
            "values_exact": ["Công ty B", "985-326", "Ngân hàng", "65,00%"],
        },
    ]

    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert checked_table["columns"] == table["columns"][1:]
    assert checked_table["rows"] == table["rows"]


def test_anonymous_count_prefix_requires_every_numeric_row_label() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [None], "value_kind": "COUNT"},
        *table["columns"],
    ]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(page)


def test_omitted_nonstructural_prefix_stays_unresolved() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Mã hợp đồng"], "value_kind": "TEXT"},
        *table["columns"],
    ]
    table["rows"][0]["hierarchy_path_exact"] = ["Sai nhãn"]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(page)


def test_generic_text_row_key_allows_an_exact_blank_continuation_label() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Họ và tên"], "value_kind": "TEXT"},
        {"header_path_exact": ["Chức vụ"], "value_kind": "TEXT"},
    ]
    table["rows"] = [
        {
            "label_exact": "Bà Nguyễn Thị A",
            "hierarchy_path_exact": ["Bà Nguyễn Thị A"],
            "row_kind": "ITEM",
            "values_exact": ["Trưởng ban"],
        },
        {
            "label_exact": None,
            "hierarchy_path_exact": [None],
            "row_kind": "ITEM",
            "values_exact": ["(tiếp theo từ trang trước)"],
        },
    ]
    checked = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert checked["columns"] == [{"header_path_exact": ["Chức vụ"], "value_kind": "TEXT"}]
    assert checked["rows"] == table["rows"]


def test_generic_text_row_key_accepts_cosmetic_bullets_and_parent_joined_leaf() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [None], "value_kind": "TEXT"},
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "- Tiền gửi không kỳ hạn bằng VND",
            "hierarchy_path_exact": ["Tiền, vàng gửi không kỳ hạn- Tiền gửi không kỳ hạn bằng VND"],
            "row_kind": "ITEM",
            "values_exact": ["313.034.765", "321.102.773"],
        },
        {
            "label_exact": "- Chứng khoán Chính phủ",
            "hierarchy_path_exact": ["Chứng khoán Chính phủ"],
            "row_kind": "ITEM",
            "values_exact": ["85.069.336", "80.284.569"],
        },
    ]
    checked = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert checked["columns"] == table["columns"][1:]
    assert checked["rows"] == table["rows"]


def test_explicit_label_column_places_one_missing_null_by_unique_value_kind() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["STT"], "value_kind": "TEXT"},
        {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"},
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
        {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Lưu chuyển tiền từ hoạt động đầu tư",
            "hierarchy_path_exact": ["Lưu chuyển tiền từ hoạt động đầu tư"],
            "row_kind": "GROUP",
            "values_exact": [None, "-", None],
        },
        {
            "label_exact": "Tiền chi mua sắm tài sản cố định",
            "hierarchy_path_exact": ["Tiền chi mua sắm tài sản cố định"],
            "row_kind": "ITEM",
            "values_exact": ["21", None, "(2.100)", "(1.900)"],
        },
    ]
    checked = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert [column["header_path_exact"] for column in checked["columns"]] == [
        ["STT"],
        ["Thuyết minh"],
        ["Kỳ này"],
        ["Kỳ trước"],
    ]
    assert checked["rows"][0]["values_exact"] == [None, None, "-", None]


def test_explicit_label_column_does_not_guess_ambiguous_missing_null() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"},
        {"header_path_exact": ["Cột A"], "value_kind": "UNKNOWN"},
        {"header_path_exact": ["Cột B"], "value_kind": "UNKNOWN"},
    ]
    table["rows"] = [
        {
            "label_exact": "Hàng",
            "hierarchy_path_exact": ["Hàng"],
            "row_kind": "ITEM",
            "values_exact": ["1"],
        }
    ]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(page)


def test_noisy_two_dash_cell_pack_expands_only_without_letters_or_digits() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["rows"][0]["values_exact"] = ["-毀-"]
    table["rows"] = [table["rows"][0]]
    checked = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert checked["rows"][0]["values_exact"] == ["-", "-"]

    page = _page()
    table = page["sections"][0]["tables"][0]
    table["rows"][0]["values_exact"] = ["-2-"]
    table["rows"] = [table["rows"][0]]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(page)


def test_numeric_group_column_already_carried_by_label_is_removed() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Nhóm"], "value_kind": "COUNT"},
        {"header_path_exact": ["Loại"], "value_kind": "TEXT"},
        {"header_path_exact": ["Tỷ lệ dự phòng cụ thể"], "value_kind": "PERCENT"},
    ]
    table["rows"] = [
        {
            "label_exact": "1",
            "hierarchy_path_exact": ["1"],
            "row_kind": "ITEM",
            "values_exact": ["Nợ đủ tiêu chuẩn", "0%"],
        },
        {
            "label_exact": "2",
            "hierarchy_path_exact": ["2"],
            "row_kind": "ITEM",
            "values_exact": ["Nợ cần chú ý", "5%"],
        },
    ]
    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert [column["header_path_exact"] for column in checked_table["columns"]] == [
        ["Loại"],
        ["Tỷ lệ dự phòng cụ thể"],
    ]
    assert checked_table["rows"] == table["rows"]


def test_leading_text_header_proxy_with_visible_cell_or_short_row_rejects() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Bên liên quan"], "value_kind": "TEXT"},
        {"header_path_exact": ["Số dư"], "value_kind": "TEXT"},
        {"header_path_exact": ["Phải thu"], "value_kind": "MONEY"},
        {"header_path_exact": ["Phải trả"], "value_kind": "MONEY"},
    ]
    table["rows"][0]["values_exact"] = ["visible", None, None]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(page)

    short = copy.deepcopy(page)
    short["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [None]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(short)


def test_hierarchy_path_is_a_soft_model_proposal() -> None:
    page = _page()
    row = page["sections"][0]["tables"][0]["rows"][1]
    row["hierarchy_path_exact"] = ["Cho vay các TCKT", "Công ty nha nước"]
    assert validate_financial_page_json_v1(page) == page


def test_exact_model_cell_pack_expands_only_when_declared_width_closes() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["rows"][0]["values_exact"] = ["434.609.559凸425.746.734"]
    table["rows"][1]["values_exact"] = ["29.412.253凸30.754.076"]
    table["rows"][2]["values_exact"] = ["434.609.559凸425.746.734"]

    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        "434.609.559",
        "425.746.734",
    ]
    # Input/raw-shaped value remains untouched by canonicalization.
    assert page["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        "434.609.559凸425.746.734"
    ]

    partial = copy.deepcopy(page)
    partial["sections"][0]["tables"][0]["rows"][0]["values_exact"] = ["434.609.559凸425.746.734凸1"]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(partial)


def test_merged_header_blanks_and_same_cell_dash_pack_are_soft_conventions() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"][0]["header_path_exact"] = [None, "Quá hạn", "Trên 3 tháng"]
    table["rows"][0]["values_exact"][0] = "-凸-"

    checked = validate_financial_page_json_v1(page)
    checked_table = checked["sections"][0]["tables"][0]
    assert checked_table["columns"][0]["header_path_exact"] == [
        "Quá hạn",
        "Trên 3 tháng",
    ]
    assert checked_table["rows"][0]["values_exact"][0] == "-"

    multiline = _page()
    multiline["sections"][0]["tables"][0]["rows"][0]["values_exact"] = ["-\n-"]
    multiline_checked = validate_financial_page_json_v1(multiline)
    assert multiline_checked["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        "-",
        "-",
    ]


def test_label_only_text_table_receives_one_null_cell_without_losing_narrative() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [{"header_path_exact": ["Nội dung"], "value_kind": "TEXT"}]
    table["rows"] = [
        {
            "label_exact": "Nợ được phân loại vào nhóm nợ có rủi ro thấp hơn khi:",
            "hierarchy_path_exact": ["Nợ được phân loại vào nhóm nợ có rủi ro thấp hơn khi:"],
            "row_kind": "ITEM",
            "values_exact": [],
        }
    ]
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [None]


def test_signed_derivative_leg_uniquely_inserts_missing_asset_or_liability_cell() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Giá trị hợp đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Tài sản"], "value_kind": "MONEY"},
        {"header_path_exact": ["Công nợ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Tổng cộng"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Giao dịch hoán đổi tiền tệ",
            "hierarchy_path_exact": ["Giao dịch hoán đổi tiền tệ"],
            "row_kind": "ITEM",
            "values_exact": ["80.034.373", "350.144", "350.144"],
        },
        {
            "label_exact": "Giao dịch kỳ hạn tiền tệ",
            "hierarchy_path_exact": ["Giao dịch kỳ hạn tiền tệ"],
            "row_kind": "ITEM",
            "values_exact": ["3.646.093", "(31.284)", "(31.284)"],
        },
    ]
    checked_rows = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]["rows"]
    assert checked_rows[0]["values_exact"] == ["80.034.373", "350.144", None, "350.144"]
    assert checked_rows[1]["values_exact"] == ["3.646.093", None, "(31.284)", "(31.284)"]


def test_movement_table_omitted_dashes_are_placed_by_exact_header_and_equation() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Vốn chủ sở hữu"], "value_kind": "TEXT"},
        {"header_path_exact": ["Số dư 1.1.2026"], "value_kind": "MONEY"},
        {"header_path_exact": ["Tăng trong kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Giảm trong kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư 31.3.2026"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Vốn điều lệ",
            "hierarchy_path_exact": ["Vốn điều lệ"],
            "row_kind": "ITEM",
            "values_exact": ["51.366.566", "51.366.566"],
        },
        {
            "label_exact": "Chênh lệch tỷ giá hối đoái",
            "hierarchy_path_exact": ["Chênh lệch tỷ giá hối đoái"],
            "row_kind": "ITEM",
            "values_exact": ["-", "(89.008)", "(89.008)"],
        },
        {
            "label_exact": "Lợi nhuận chưa phân phối",
            "hierarchy_path_exact": ["Lợi nhuận chưa phân phối"],
            "row_kind": "ITEM",
            "values_exact": ["22.272.006", "3.933.827", "26.205.833"],
        },
        {
            "label_exact": "Tổng",
            "hierarchy_path_exact": ["Tổng"],
            "row_kind": "TOTAL",
            "values_exact": ["91.005.607", "3.933.827", "(89.008)", "94.850.426"],
        },
    ]

    checked = validate_financial_page_json_v1(page)
    checked_table = checked["sections"][0]["tables"][0]
    assert len(checked_table["columns"]) == 4
    assert [row["values_exact"] for row in checked_table["rows"]] == [
        ["51.366.566", None, None, "51.366.566"],
        ["-", None, "(89.008)", "(89.008)"],
        ["22.272.006", "3.933.827", None, "26.205.833"],
        ["91.005.607", "3.933.827", "(89.008)", "94.850.426"],
    ]


def test_movement_table_accepts_opening_closing_and_use_adjustment_headers() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Tên chỉ tiêu"], "value_kind": "TEXT"},
        {"header_path_exact": ["Dư đầu"], "value_kind": "MONEY"},
        {"header_path_exact": ["Trích lập/Tăng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Sử dụng/ Điều chỉnh"], "value_kind": "MONEY"},
        {"header_path_exact": ["Dư cuối"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Vốn điều lệ",
            "hierarchy_path_exact": ["Vốn điều lệ"],
            "row_kind": "ITEM",
            "values_exact": ["53.063.241", "27.486.758", "80.549.999"],
        },
        {
            "label_exact": "Thặng dư vốn cổ phần",
            "hierarchy_path_exact": ["Thặng dư vốn cổ phần"],
            "row_kind": "ITEM",
            "values_exact": ["1.304.334", "1.304.334"],
        },
        {
            "label_exact": "Quỹ khác",
            "hierarchy_path_exact": ["Quỹ khác"],
            "row_kind": "ITEM",
            "values_exact": ["957.973", "556.625", "(477.961)", "1.036.637"],
        },
    ]

    checked = validate_financial_page_json_v1(page)
    checked_table = checked["sections"][0]["tables"][0]
    assert len(checked_table["columns"]) == 4
    assert [row["values_exact"] for row in checked_table["rows"]] == [
        ["53.063.241", "27.486.758", None, "80.549.999"],
        ["1.304.334", None, None, "1.304.334"],
        ["957.973", "556.625", "(477.961)", "1.036.637"],
    ]


def test_dual_period_share_table_restores_only_exact_preferred_blanks() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [None, None], "value_kind": "TEXT"},
        {"header_path_exact": ["30/09/2025", "Tổng số"], "value_kind": "MONEY"},
        {"header_path_exact": ["30/09/2025", "Vốn CP thường"], "value_kind": "MONEY"},
        {"header_path_exact": ["30/09/2025", "Vốn CP ưu đãi"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Tổng số"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Vốn CP thường"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Vốn CP ưu đãi"], "value_kind": "MONEY"},
    ]
    table["rows"] = [
        {
            "label_exact": "Vốn góp của cổ đông",
            "hierarchy_path_exact": ["Vốn góp của cổ đông"],
            "row_kind": "ITEM",
            "values_exact": ["80.549.999", "80.549.999", "53.063.241", "53.063.241"],
        },
        {
            "label_exact": "Cổ phiếu quỹ",
            "hierarchy_path_exact": ["Cổ phiếu quỹ"],
            "row_kind": "ITEM",
            "values_exact": [None, None, None, None, None, None],
        },
    ]

    checked_table = validate_financial_page_json_v1(page)["sections"][0]["tables"][0]
    assert len(checked_table["columns"]) == 6
    assert checked_table["rows"][0]["values_exact"] == [
        "80.549.999",
        "80.549.999",
        None,
        "53.063.241",
        "53.063.241",
        None,
    ]
    assert checked_table["rows"][1]["values_exact"] == [None] * 6

    attack = copy.deepcopy(page)
    attack["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [
        "80.549.999",
        "79.000.000",
        "53.063.241",
        "53.063.241",
    ]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(attack)


def test_complete_group_heading_without_value_cells_gets_exact_null_width() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["rows"][0] = {
        "label_exact": "Nguyên giá:",
        "hierarchy_path_exact": ["Nguyên giá:"],
        "row_kind": "GROUP",
        "values_exact": [],
    }
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [None, None]

    attack = copy.deepcopy(page)
    attack["sections"][0]["tables"][0]["rows"][0]["row_kind"] = "ITEM"
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(attack)


def test_anonymous_unknown_row_label_proxy_is_removed_only_with_exact_suffix() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [None], "value_kind": "UNKNOWN"},
        {"header_path_exact": ["31/03/2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/03/2024"], "value_kind": "MONEY"},
    ]
    checked = validate_financial_page_json_v1(page)
    checked_table = checked["sections"][0]["tables"][0]
    assert len(checked_table["columns"]) == 2
    assert checked_table["rows"][0]["values_exact"] == [
        "434.609.559",
        "425.746.734",
    ]

    named = copy.deepcopy(page)
    named["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = ["Mã số"]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(named)

    wrong_suffix = copy.deepcopy(page)
    wrong_suffix["sections"][0]["tables"][0]["columns"][1]["value_kind"] = "TEXT"
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(wrong_suffix)

    wrong_owner = copy.deepcopy(page)
    wrong_owner["sections"][0]["tables"][0]["rows"][0]["hierarchy_path_exact"][-1] = (
        "Khoản mục khác"
    )
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(wrong_owner)


def test_exact_empty_model_cell_replays_as_blank_without_relaxing_whitespace() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = ""
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][1]["values_exact"] == [
        None,
        "30.754.076",
    ]

    attack = _page()
    attack["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "   "
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="nonempty exact NFC"):
        validate_financial_page_json_v1(attack)


def test_immediately_merged_hierarchy_cell_replays_from_same_visible_owner() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["rows"] = [
        {
            "label_exact": "Giảm tiền gửi",
            "hierarchy_path_exact": ["NHNN Việt Nam", "Chủ sở hữu", "Giảm tiền gửi"],
            "row_kind": "ITEM",
            "values_exact": ["10", "8"],
        },
        {
            "label_exact": "Tăng tiền vay",
            "hierarchy_path_exact": ["NHNN Việt Nam", None, "Tăng tiền vay"],
            "row_kind": "ITEM",
            "values_exact": ["12", "9"],
        },
    ]
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][1]["hierarchy_path_exact"] == [
        "NHNN Việt Nam",
        "Chủ sở hữu",
        "Tăng tiền vay",
    ]

    attack = copy.deepcopy(page)
    attack["sections"][0]["tables"][0]["rows"][1]["hierarchy_path_exact"] = [
        "Ngân hàng khác",
        None,
        "Tăng tiền vay",
    ]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="null only at the end"):
        validate_financial_page_json_v1(attack)


def test_two_detail_total_equation_replays_one_omitted_accounting_zero() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [name], "value_kind": "MONEY"}
        for name in ["Dư nợ", "Tiền gửi", "Cam kết", "Phái sinh", "Chứng khoán"]
    ]
    table["rows"] = [
        {
            "label_exact": "Trong nước",
            "hierarchy_path_exact": ["Trong nước"],
            "row_kind": "ITEM",
            "values_exact": [
                "555.822.273",
                "691.687.371",
                "44.197.532",
                "88.979.176",
                "77.435.184",
            ],
        },
        {
            "label_exact": "Nước ngoài",
            "hierarchy_path_exact": ["Nước ngoài"],
            "row_kind": "ITEM",
            "values_exact": ["-", "--", "21.381", "--"],
        },
        {
            "label_exact": None,
            "hierarchy_path_exact": [None],
            "row_kind": "TOTAL",
            "values_exact": [
                "555.822.273",
                "691.687.371",
                "44.197.532",
                "89.000.557",
                "77.435.184",
            ],
        },
    ]
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][1]["values_exact"] == [
        "0",
        "0",
        "0",
        "21.381",
        "0",
    ]

    attack = copy.deepcopy(page)
    attack["sections"][0]["tables"][0]["rows"][2]["values_exact"][3] = "89.000.558"
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(attack)


@pytest.mark.parametrize(
    "headers,values",
    [
        (["Số dư đầu kỳ", "Tăng", "Khác", "Số dư cuối kỳ"], ["1", "2", "3"]),
        (["Số dư đầu kỳ", "Tăng", "Giảm", "Số dư cuối kỳ"], ["1", "2", "4"]),
        (["Số dư đầu kỳ", "Tăng", "Giảm", "Số dư cuối kỳ"], ["1", "2"]),
    ],
)
def test_movement_table_soft_replay_rejects_ambiguous_or_nonexact_rows(headers, values) -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Khoản mục"], "value_kind": "TEXT"},
        *[{"header_path_exact": [header], "value_kind": "MONEY"} for header in headers],
    ]
    table["rows"] = [
        {
            "label_exact": "Hàng",
            "hierarchy_path_exact": ["Hàng"],
            "row_kind": "ITEM",
            "values_exact": values,
        }
    ]
    with pytest.raises(GeminiFinancialPageJsonV1Error, match="do not align"):
        validate_financial_page_json_v1(page)


def test_dash_annotation_pack_and_arithmetic_total_close_one_nine_cell_row() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": [name], "value_kind": "MONEY"}
        for name in [
            "Quá hạn",
            "Không chịu lãi suất",
            "Dưới 1 tháng",
            "Từ 1 đến 3 tháng",
            "Từ 3 đến 6 tháng",
            "Từ 6 đến 12 tháng",
            "Từ 1 đến 5 năm",
            "Trên 5 năm",
            "Tổng cộng",
        ]
    ]
    table["rows"] = [
        {
            "label_exact": "Tiền gửi của khách hàng",
            "hierarchy_path_exact": ["Tiền gửi của khách hàng"],
            "row_kind": "ITEM",
            "values_exact": [
                "- paradise_missing_here_dash_handled_as_dash_or_zero -> -",
                "128.791.054",
                "171.834.972",
                "116.669.771",
                "89.027.381",
                "30.981.400 paradise_missing_here_dash_handled_as_dash_or_zero -> -",
                "537.304.578",
                None,
            ],
        }
    ]
    checked = validate_financial_page_json_v1(page)
    assert checked["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        "-",
        "128.791.054",
        "171.834.972",
        "116.669.771",
        "89.027.381",
        "30.981.400",
        "-",
        None,
        "537.304.578",
    ]


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
