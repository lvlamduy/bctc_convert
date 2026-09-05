from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _compiled() -> dict:
    paths = (
        "config/families/tm-loan-industry-classification-topology-v1.json",
        "config/families/tm-loan-industry-classification-evaluation-v1.json",
        "config/families/tm-loan-industry-classification-schema-binding-v1.json",
    )
    topology, evaluation, schema = (
        json.loads((ROOT / path).read_text(encoding="utf-8")) for path in paths
    )
    return compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)


def _page() -> dict:
    return {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "CHO VAY KHÁCH HÀNG",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31.12.2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31.12.2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Cho vay các tổ chức kinh tế"],
                                "label_exact": "Cho vay các tổ chức kinh tế",
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["100", "90"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Cho vay các tổ chức kinh tế",
                                    "Nông nghiệp và lâm nghiệp và thủy sản",
                                ],
                                "label_exact": "Nông nghiệp và lâm nghiệp và thủy sản",
                                "row_kind": "ITEM",
                                "values_exact": ["60", "50"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Cho vay các tổ chức kinh tế",
                                    "Xây dựng",
                                ],
                                "label_exact": "Xây dựng",
                                "row_kind": "ITEM",
                                "values_exact": ["40", "40"],
                            },
                            {
                                "hierarchy_path_exact": ["Cho vay cá nhân"],
                                "label_exact": "Cho vay cá nhân",
                                "row_kind": "ITEM",
                                "values_exact": ["20", "10"],
                            },
                            {
                                # Some providers retain the previous structural owner in
                                # the path even though this is the whole-table total.
                                "hierarchy_path_exact": [
                                    "Cho vay các tổ chức kinh tế",
                                    "Tổng cộng",
                                ],
                                "label_exact": "Tổng cộng",
                                "row_kind": "TOTAL",
                                "values_exact": ["120", "100"],
                            },
                        ],
                        "title_exact": "Phân tích dư nợ theo ngành nghề kinh doanh",
                        "unit_exact": "Triệu đồng",
                    }
                ],
            }
        ],
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
    }


def _evaluate(page: dict) -> dict:
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "7" * 64,
        physical_page=31,
        section_id="s1",
        table_id="t1",
        compiled_specs=_compiled(),
    )


def test_generic_labeled_total_closes_core_plus_unmapped_personal_population() -> None:
    result = _evaluate(_page())

    assert result["status"] == READY
    mappings = {mapping["report_norm_id"]: mapping for mapping in result["mappings"]}
    assert set(mappings) == {727, 728, 732}
    assert [value["coefficient"] for value in mappings[727]["values"]] == [120, 100]
    assert "SOURCE_ONLY_PERSONAL_LOANS" not in {mapping["role"] for mapping in result["mappings"]}
    assert result["closure_receipt"]["used_anonymous_result_row_ids"] == ["r5"]


def test_generic_labeled_total_does_not_override_nonclosing_source_values() -> None:
    page = deepcopy(_page())
    page["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "122"

    result = _evaluate(page)

    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []


def test_international_organizations_is_distinct_from_other_industries() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Nông nghiệp, lâm nghiệp và thủy sản"],
            "label_exact": "Nông nghiệp, lâm nghiệp và thủy sản",
            "row_kind": "ITEM",
            "values_exact": ["10", "8"],
        },
        {
            "hierarchy_path_exact": ["Hoạt động của các tổ chức và cơ quan quốc tế"],
            "label_exact": "Hoạt động của các tổ chức và cơ quan quốc tế",
            "row_kind": "ITEM",
            "values_exact": ["2", "1"],
        },
        {
            "hierarchy_path_exact": ["Các ngành khác"],
            "label_exact": "Các ngành khác",
            "row_kind": "ITEM",
            "values_exact": ["3", "4"],
        },
        {
            "hierarchy_path_exact": ["Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["15", "13"],
        },
    ]

    result = _evaluate(page)

    assert result["status"] == READY
    assert {mapping["report_norm_id"] for mapping in result["mappings"]} == {
        727,
        728,
        744,
        745,
    }


def _explicit_group_with_flat_trailing_total_page() -> dict:
    page = _page()
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = None
    table["rows"] = [
        {
            "hierarchy_path_exact": ["Phân tích dư nợ cho vay theo ngành"],
            "label_exact": "Phân tích dư nợ cho vay theo ngành",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [
                "Phân tích dư nợ cho vay theo ngành",
                "Nông nghiệp, lâm nghiệp và thủy sản",
            ],
            "label_exact": "Nông nghiệp, lâm nghiệp và thủy sản",
            "row_kind": "ITEM",
            "values_exact": ["60", "50"],
        },
        {
            "hierarchy_path_exact": ["Phân tích dư nợ cho vay theo ngành", "Xây dựng"],
            "label_exact": "Xây dựng",
            "row_kind": "ITEM",
            "values_exact": ["40", "40"],
        },
        {
            # Gemini occasionally flattens this immediate closing row out of
            # the otherwise exact hierarchy path.
            "hierarchy_path_exact": ["Cộng"],
            "label_exact": "Cộng",
            "row_kind": "TOTAL",
            "values_exact": ["100", "90"],
        },
    ]
    return page


def test_immediate_flat_total_closes_one_explicit_contiguous_family_group() -> None:
    result = _evaluate(_explicit_group_with_flat_trailing_total_page())

    assert result["status"] == READY
    assert {mapping["report_norm_id"] for mapping in result["mappings"]} == {727, 728, 732}
    assert result["closure_receipt"]["used_anonymous_result_row_ids"] == ["r4"]


def test_parent_scoped_total_is_not_mistaken_for_an_unrelated_group() -> None:
    page = _explicit_group_with_flat_trailing_total_page()
    total = page["sections"][0]["tables"][0]["rows"][-1]
    total["hierarchy_path_exact"] = ["Phân tích dư nợ cho vay theo ngành", "Cộng"]

    result = _evaluate(page)

    assert result["status"] == READY
    assert {mapping["report_norm_id"] for mapping in result["mappings"]} == {727, 728, 732}
    assert result["closure_receipt"]["used_anonymous_result_row_ids"] == ["r4"]


def test_intervening_numeric_row_prevents_flat_total_carry() -> None:
    page = _explicit_group_with_flat_trailing_total_page()
    page["sections"][0]["tables"][0]["rows"].insert(
        -1,
        {
            "hierarchy_path_exact": ["Bảng khác"],
            "label_exact": "Dòng ngoài phạm vi",
            "row_kind": "ITEM",
            "values_exact": ["1", "1"],
        },
    )

    result = _evaluate(page)

    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []


_MSB_MANUFACTURING_LABELS = [
    "Chế biến thủy hải sản",
    "Sản xuất, chế biến lương thực, thực phẩm, đồ uống, thức ăn chăn nuôi",
    "Dệt may, sản xuất da giày, sản xuất trang phục",
    "Khai thác và sơ chế gỗ, chế biến gỗ, sản xuất sản phẩm từ gỗ và lâm sản khác",
    "Sản xuất giấy và các sản phẩm từ giấy và in ấn",
    "Sản xuất thuốc, hóa dược, dược liệu, cao su, nhựa, phân bón, hóa chất",
    "Sản xuất vật liệu xây dựng (trừ thép, Inox, sơn, matit và các chất tương tự)",
    "Sản xuất thép thành phẩm",
    "Sản xuất phôi thép",
    "Sản xuất Inox và luyện kim khác",
    "Cơ khí, lắp ráp, chế tạo máy móc, ô tô, xe máy",
    "Sản xuất điện tử, thiết bị điện, máy vi tính quang học, thiết bị viễn thông",
    "Đóng tàu, thuyền",
    "Sản xuất thiết bị văn phòng, đồ gia dụng, thiết bị y tế, giáo dục, thể dục thể thao",
]


def _msb_manufacturing_detail_page(*, include_steel_billet: bool) -> dict:
    page = _page()
    labels = [
        label
        for label in _MSB_MANUFACTURING_LABELS
        if include_steel_billet or label != "Sản xuất phôi thép"
    ]
    table = page["sections"][0]["tables"][0]
    table["rows"] = (
        [
            {
                "hierarchy_path_exact": ["Nông nghiệp, lâm nghiệp và thủy sản"],
                "label_exact": "Nông nghiệp, lâm nghiệp và thủy sản",
                "row_kind": "ITEM",
                "values_exact": ["10", "20"],
            },
            {
                "hierarchy_path_exact": ["Xây dựng"],
                "label_exact": "Xây dựng",
                "row_kind": "ITEM",
                "values_exact": ["5", "10"],
            },
        ]
        + [
            {
                "hierarchy_path_exact": [label],
                "label_exact": label,
                "row_kind": "ITEM",
                "values_exact": ["1", "2"],
            }
            for label in labels
        ]
        + [
            {
                "hierarchy_path_exact": ["Tổng cộng"],
                "label_exact": "Tổng cộng",
                "row_kind": "TOTAL",
                "values_exact": [str(len(labels) + 15), str(2 * len(labels) + 30)],
            }
        ]
    )
    return page


def test_msb_manufacturing_detail_rows_derive_one_schema_industry_mapping() -> None:
    for include_steel_billet, expected in ((True, 14), (False, 13)):
        result = _evaluate(
            _msb_manufacturing_detail_page(
                include_steel_billet=include_steel_billet,
            )
        )

        assert result["status"] == READY
        mappings = {mapping["report_norm_id"]: mapping for mapping in result["mappings"]}
        assert set(mappings) == {727, 728, 732, 733}
        assert [value["coefficient"] for value in mappings[733]["values"]] == [
            expected,
            2 * expected,
        ]
        assert not {
            mapping["role"]
            for mapping in result["mappings"]
            if mapping["role"].startswith("SOURCE_ONLY_MANUFACTURING_")
        }
