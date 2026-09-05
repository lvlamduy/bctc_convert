from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_first_accounting_family_continuation_v1",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)


def _compiled() -> dict:
    paths = (
        "config/families/tm-loan-industry-classification-topology-v1.json",
        "config/families/tm-loan-industry-classification-evaluation-v1.json",
        "config/families/tm-loan-industry-classification-schema-binding-v1.json",
    )
    return target.compile_gemini_json_flat_family_specs_v1(
        *(json.loads((ROOT / path).read_text(encoding="utf-8")) for path in paths)
    )


def _currency_compiled() -> dict:
    paths = (
        "config/families/tm-loan-currency-classification-topology-v1.json",
        "config/families/tm-loan-currency-classification-evaluation-v1.json",
        "config/families/tm-loan-currency-classification-schema-binding-v1.json",
    )
    return target.compile_gemini_json_flat_family_specs_v1(
        *(json.loads((ROOT / path).read_text(encoding="utf-8")) for path in paths)
    )


def _row(label: str, values: list[str], *, kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(
    rows: list[dict],
    *,
    continuation: str,
    title: str | None,
    unit: str | None = "Triệu đồng",
    headers: tuple[str | None, str | None] = ("31.12.2025", "31.12.2024"),
) -> dict:
    return {
        "columns": [{"header_path_exact": [header], "value_kind": "MONEY"} for header in headers],
        "continuation": continuation,
        "rows": rows,
        "title_exact": title,
        "unit_exact": unit,
    }


def _page(table: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": "THUYẾT MINH BÁO CÁO TÀI CHÍNH",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _fixture() -> tuple[dict, dict, dict, dict, dict]:
    first_id = "gfpstorev1:json:" + "1" * 64
    second_id = "gfpstorev1:json:" + "2" * 64
    first = _page(
        _table(
            [
                _row("Nông nghiệp, lâm nghiệp và thủy sản", ["10", "8"]),
                _row("Xây dựng", ["20", "18"]),
            ],
            continuation="CONTINUES_ON_NEXT_PAGE",
            title="Phân tích dư nợ cho vay theo ngành",
        )
    )
    second = _page(
        _table(
            [
                _row("Công nghiệp chế biến, chế tạo", ["30", "24"]),
                _row("Cộng", ["60", "50"], kind="TOTAL"),
            ],
            continuation="CONTINUES_FROM_PREVIOUS_PAGE",
            title=None,
        )
    )
    region = {
        "context_pages": [
            {"page_json_version_id": second_id, "physical_page": 11},
        ],
        "page_json_version_id": first_id,
        "physical_page": 10,
        "section_id": "s1",
        "source_logical_name": "bank/report.pdf",
        "table_id": "t1",
    }
    pages = {
        first_id: {"page_json": first},
        second_id: {"page_json": second},
    }
    compiled = _compiled()
    base = target.evaluate_gemini_json_flat_family_table_v1(
        page_json=first,
        page_json_version_id=first_id,
        physical_page=10,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )
    return base, region, pages, compiled, second


def _stitch(
    base: dict,
    region: dict,
    pages: dict,
    compiled: dict,
) -> dict | None:
    return target._adjacent_continuation_candidate_v1(
        base_candidate=base,
        region=region,
        page_by_version=pages,
        compiled_specs=compiled,
    )


def test_directional_two_page_family_table_is_stitched_with_row_provenance() -> None:
    base, region, pages, compiled, _second = _fixture()
    assert base["status"] == target.UNRESOLVED

    stitched = _stitch(base, region, pages, compiled)

    assert stitched is not None
    assert stitched["status"] == target.READY
    assert {mapping["report_norm_id"] for mapping in stitched["mappings"]} == {
        727,
        728,
        732,
        733,
    }
    receipt = stitched["continuation_stitch_receipt"]
    assert [item["physical_page"] for item in receipt["component_regions"]] == [10, 11]
    assert len(receipt["row_provenance_axis"]) == 4
    assert all(mapping["source_row_refs"] for mapping in stitched["mappings"])


def test_next_page_from_previous_marker_is_sufficient_and_null_headers_inherit() -> None:
    base, region, pages, compiled, _second = _fixture()
    first = pages[region["page_json_version_id"]]["page_json"]
    first["sections"][0]["tables"][0]["continuation"] = "NONE"
    pages[region["context_pages"][0]["page_json_version_id"]]["page_json"]["sections"][0]["tables"][
        0
    ]["columns"] = [
        {"header_path_exact": [None], "value_kind": "MONEY"},
        {"header_path_exact": [None], "value_kind": "MONEY"},
    ]
    base = target.evaluate_gemini_json_flat_family_table_v1(
        page_json=first,
        page_json_version_id=region["page_json_version_id"],
        physical_page=10,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )

    stitched = _stitch(base, region, pages, compiled)

    assert stitched is not None and stitched["status"] == target.READY
    assert [column["header_path_exact"] for column in stitched["mappings"][0]["columns"]] == [
        ["31.12.2025"],
        ["31.12.2024"],
    ]


def test_parent_group_slice_is_carried_into_flat_continuation_rows() -> None:
    base, region, pages, compiled, _second = _fixture()
    first = pages[region["page_json_version_id"]]["page_json"]
    table = first["sections"][0]["tables"][0]
    table["title_exact"] = "Cho vay khách hàng"
    table["rows"] = [
        _row("Phân tích chất lượng nợ cho vay", ["30", "26"], kind="TOTAL"),
        _row("Phân tích dư nợ cho vay theo ngành", [None, None], kind="GROUP"),
        *table["rows"],
    ]
    base = target.evaluate_gemini_json_flat_family_table_v1(
        page_json=first,
        page_json_version_id=region["page_json_version_id"],
        physical_page=10,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )

    stitched = _stitch(base, region, pages, compiled)

    assert stitched is not None and stitched["status"] == target.READY
    provenance = stitched["continuation_stitch_receipt"]["row_provenance_axis"]
    assert provenance[0]["original_row_id"] == "r2"
    assert all(item["hierarchy_parent_prefix_added"] for item in provenance[-2:])


def test_unit_header_ambiguity_and_nonadjacent_context_fail_closed() -> None:
    for mutation in ("unit", "header", "distance"):
        base, region, pages, compiled, _second = _fixture()
        second_id = region["context_pages"][0]["page_json_version_id"]
        if mutation == "unit":
            pages[second_id]["page_json"]["sections"][0]["tables"][0]["unit_exact"] = "Nghìn đồng"
        elif mutation == "header":
            pages[second_id]["page_json"]["sections"][0]["tables"][0]["columns"][0][
                "header_path_exact"
            ] = ["30.06.2025"]
        else:
            region["context_pages"][0]["physical_page"] = 12

        assert _stitch(base, region, pages, compiled) is None


def test_ambiguous_or_hard_negative_continuation_fails_closed() -> None:
    for mutation in ("ambiguous", "hard_negative"):
        base, region, pages, compiled, second = _fixture()
        second_id = region["context_pages"][0]["page_json_version_id"]
        if mutation == "ambiguous":
            pages[second_id]["page_json"]["sections"][0]["tables"].append(
                deepcopy(second["sections"][0]["tables"][0])
            )
        else:
            pages[second_id]["page_json"]["sections"][0]["tables"][0]["rows"].insert(
                0,
                _row("Phân tích chất lượng nợ cho vay", [None, None], kind="GROUP"),
            )

        assert _stitch(base, region, pages, compiled) is None


def test_stitch_does_not_relax_visible_total_arithmetic() -> None:
    base, region, pages, compiled, _second = _fixture()
    second_id = region["context_pages"][0]["page_json_version_id"]
    pages[second_id]["page_json"]["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "58"

    stitched = _stitch(base, region, pages, compiled)

    assert stitched is not None
    assert stitched["status"] == target.UNRESOLVED
    assert stitched["mappings"] == []


def test_receiver_only_fragment_uses_exact_parent_and_headers_from_prior_page() -> None:
    first_id = "gfpstorev1:json:" + "3" * 64
    second_id = "gfpstorev1:json:" + "4" * 64
    first = _page(
        _table(
            [
                {
                    "hierarchy_path_exact": [None],
                    "label_exact": None,
                    "row_kind": "UNKNOWN",
                    "values_exact": [None, None],
                }
            ],
            continuation="CONTINUES_ON_NEXT_PAGE",
            title="Phân tích dư nợ theo tiền tệ",
            unit=None,
            headers=("Cuối kỳ", "Đầu kỳ"),
        )
    )
    second = _page(
        _table(
            [
                _row("Vay bằng VND", ["100", "90"]),
                _row("Vay bằng ngoại tệ", ["20", "10"]),
                _row("Vay bằng vàng (do biến động tỷ giá)", ["5", "4"]),
                _row("Tổng", ["125", "104"], kind="TOTAL"),
            ],
            continuation="CONTINUES_FROM_PREVIOUS_PAGE",
            title=None,
            unit=None,
            headers=(None, None),
        )
    )
    region = {
        "context_pages": [{"page_json_version_id": first_id, "physical_page": 10}],
        "page_json_version_id": second_id,
        "physical_page": 11,
        "section_id": "s1",
        "source_logical_name": "bank/report.pdf",
        "table_id": "t1",
    }
    pages = {first_id: {"page_json": first}, second_id: {"page_json": second}}
    compiled = _currency_compiled()
    base = target.evaluate_gemini_json_flat_family_table_v1(
        page_json=second,
        page_json_version_id=second_id,
        physical_page=11,
        section_id="s1",
        table_id="t1",
        compiled_specs=compiled,
    )

    assert set(base["reasons"]) == {
        "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW",
        "PERIOD_VALUE_COLUMN_HEADER_OR_MONEY_LANE_COUNT_IS_NOT_EXACT",
    }
    stitched = _stitch(base, region, pages, compiled)
    assert stitched is not None and stitched["status"] == target.READY
    assert [mapping["report_norm_id"] for mapping in stitched["mappings"]] == [757, 758]
    assert [
        [value["coefficient"] for value in mapping["values"]] for mapping in stitched["mappings"]
    ] == [[100, 90], [25, 14]]
    assert [
        component["physical_page"]
        for component in stitched["continuation_stitch_receipt"]["component_regions"]
    ] == [10, 11]

    no_parent = deepcopy(pages)
    no_parent[first_id]["page_json"]["sections"][0]["tables"][0]["title_exact"] = (
        "Bảng thông tin khác"
    )
    assert _stitch(base, region, no_parent, compiled) is None
