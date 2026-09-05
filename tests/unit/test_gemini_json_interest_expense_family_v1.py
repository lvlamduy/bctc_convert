from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_interest_expense_family_v1 as subject
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "1" * 64
SOURCE_SHA256 = "2" * 64
PAGE_1 = "gfpstorev1:json:" + "3" * 64
PAGE_2 = "gfpstorev1:json:" + "4" * 64
PAGE_3 = "gfpstorev1:json:" + "5" * 64


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_bytes())


def _repair_spec(*repairs: dict) -> dict:
    return {
        "family_id": subject.FAMILY_ID,
        "format_version": subject.SOURCE_REPAIR_FORMAT_VERSION,
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        },
        "repairs": list(repairs),
    }


def _compiled(*repairs: dict) -> dict:
    repair_spec = (
        _repair_spec(*repairs)
        if repairs
        else _json("config/families/tm-interest-expense-source-repair-v1.json")
    )
    return subject.compile_gemini_json_interest_expense_family_specs_v1(
        _json("config/families/tm-interest-expense-topology-v1.json"),
        _json("config/families/tm-interest-expense-evaluation-v1.json"),
        _json("config/families/tm-interest-expense-schema-binding-v1.json"),
        repair_spec,
    )


def _region(*, page: str = PAGE_3, physical_page: int = 3) -> dict:
    return {
        "component_roles": [
            "BORROWING_INTEREST",
            "DEPOSIT_INTEREST",
            "FINANCE_LEASE_INTEREST",
            "ISSUED_PAPER_INTEREST",
            "OTHER_CREDIT_EXPENSE",
        ],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": page,
        "physical_page": physical_page,
        "section_id": "s1",
        "selected_page_ordinal": physical_page,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }


def _selected(*, page: str, physical_page: int) -> dict:
    return {
        key: value
        for key, value in _region(page=page, physical_page=physical_page).items()
        if key not in {"component_roles", "fragment_ordinal", "section_id", "table_id"}
    }


def _record(*, page_json: dict, page: str, physical_page: int) -> dict:
    return {
        **_selected(page=page, physical_page=physical_page),
        "page_json": page_json,
    }


def _row(label: str | None, values: list[str | None], kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(*, unit: str | None, rows: list[dict], four_lanes: bool = False) -> dict:
    headers = (
        ["Quý II/2025", "Quý II/2024", "6 tháng/2025", "6 tháng/2024"]
        if four_lanes
        else ["Năm nay", "Năm trước"]
    )
    return {
        "columns": [
            {"header_path_exact": [header], "value_kind": "MONEY"}
            for header in headers
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }


def _page(
    *,
    table: dict,
    title: str | None,
    status: str,
    content_kind: str,
    statement_type: str,
) -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": content_kind,
                "narratives_exact": [],
                "statement_type": statement_type,
                "tables": [{**table, "title_exact": title}],
                "title_exact": title,
            }
        ],
        "status": status,
    }


def _note_page(*, unit: str | None = None) -> dict:
    rows = [
        _row("Trả lãi tiền gửi", ["60", "50"]),
        _row("Trả lãi tiền vay", ["20", "20"]),
        _row("Trả lãi phát hành giấy tờ có giá", ["15", "15"]),
        _row("Trả lãi tiền thuê tài chính", ["-", "-"]),
        _row("Chi phí hoạt động tín dụng khác", ["5", "5"]),
        _row(None, ["100", "90"], "TOTAL"),
    ]
    return _page(
        table=_table(unit=unit, rows=rows),
        title="29. Chi phí lãi và các chi phí tương tự",
        status="FINANCIAL_NOTE_CONTENT",
        content_kind="FINANCIAL_NOTE",
        statement_type="INCOME_STATEMENT",
    )


def _primary_page(*, unit: str | None, values: list[str | None]) -> dict:
    return _page(
        table=_table(
            unit=unit,
            rows=[_row("2- Chi phí lãi và các chi phí tương tự", values)],
            four_lanes=len(values) == 4,
        ),
        title="BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH",
        status="PRIMARY_FINANCIAL_STATEMENT",
        content_kind="PRIMARY_STATEMENT",
        statement_type="INCOME_STATEMENT",
    )


def _unit_page(unit: str) -> dict:
    return _page(
        table=_table(unit=unit, rows=[_row("Tài sản", ["1", "1"])]),
        title="BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
        status="PRIMARY_FINANCIAL_STATEMENT",
        content_kind="PRIMARY_STATEMENT",
        statement_type="BALANCE_SHEET",
    )


def _money_repair(*, before: str | None = None, after: str = "-") -> dict:
    material = {
        "after_exact": after,
        "before_exact": before,
        "column_ordinal": 2,
        "locator": {
            "page_json_version_id": PAGE_3,
            "physical_page": 3,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "6" * 64,
        "repair_kind": "MONEY_CELL_PDF_VISIBLE_EXACT",
        "row_ordinal": 4,
        "source_sha256": SOURCE_SHA256,
    }
    return {
        **material,
        "repair_id": "gjiefav1:repair:" + canonical_json_sha256_v1(material),
    }


def test_real_specs_compile_exact_source_repair_frontier() -> None:
    compiled = _compiled()

    assert compiled["topology"]["family_id"] == subject.FAMILY_ID
    assert len(compiled["interest_expense_source_repairs"]) == 30
    assert {
        item["canonical_unit"]
        for item in compiled["unit_bindings"]
        if item["accepted"] is True
    } == {"MILLION_VND", "VND"}
    assert compiled["source_total_blank_lane_control_policy"] == (
        "OBSERVED_LANES_EXACT_REMAINDER_BLANK"
    )
    assert compiled["family_root_terminal_scope_policy"] == (
        "LAST_SOURCE_TOTAL_WITHIN_EXPLICIT_FAMILY_ROOT_SUBTREE"
    )
    assert compiled["source_presentation_rounding_policy"] == (
        "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS"
    )
    assert compiled["duration_header_path_scope_policy"] == (
        "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
    )
    assert compiled["adjacent_continuation_family_root_policy"] == (
        "EXACT_UNION_OF_DECLARED_ROOT_COMPONENTS_EQUALS_RECEIVER_TERMINAL_TOTAL"
    )
    assert set(compiled["bindings"]) == {
        "BORROWING_INTEREST",
        "DEPOSIT_INTEREST",
        "FINANCE_LEASE_INTEREST",
        "ISSUED_PAPER_INTEREST",
        "OTHER_CREDIT_EXPENSE",
    }
    aliases = {
        role: {
            alias
            for matcher in compiled["matchers_by_role"][role]
            for alias in matcher["aliases"]
        }
        for role in (
            "DEPOSIT_INTEREST",
            "FINANCE_LEASE_INTEREST",
            "OTHER_CREDIT_EXPENSE",
        )
    }
    assert "tra lai huy dong" in aliases["DEPOSIT_INTEREST"]
    assert "tra lai thue tai chinh" in aliases["FINANCE_LEASE_INTEREST"]
    assert "chi phi khac tu hoat dong tin dung khac" in aliases[
        "OTHER_CREDIT_EXPENSE"
    ]


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("source_total_blank_lane_control_policy", "PERMIT_BLANK_AS_ZERO"),
        ("family_root_terminal_scope_policy", "FIRST_TOTAL_ANYWHERE"),
        ("source_presentation_rounding_policy", "GLOBAL_PLUS_OR_MINUS_ONE"),
        ("duration_header_path_scope_policy", "DROP_ANY_SHARED_WORDS"),
        ("adjacent_continuation_family_root_policy", "ANY_CONTINUATION_TOTAL"),
    ],
)
def test_family29_optional_policies_are_strictly_compiled(
    field: str, invalid: str
) -> None:
    evaluation = _json("config/families/tm-interest-expense-evaluation-v1.json")
    evaluation[field] = invalid

    with pytest.raises(
        subject.GeminiJsonInterestExpenseFamilyV1Error,
        match="declarative family specs are invalid",
    ):
        subject.compile_gemini_json_interest_expense_family_specs_v1(
            _json("config/families/tm-interest-expense-topology-v1.json"),
            evaluation,
            _json("config/families/tm-interest-expense-schema-binding-v1.json"),
            _json("config/families/tm-interest-expense-source-repair-v1.json"),
        )


def test_duration_header_uses_only_distinct_suffix_after_exact_common_prefix() -> None:
    compiled = _compiled()
    note = _note_page(unit="Triệu đồng")
    columns = note["sections"][0]["tables"][0]["columns"]
    common = "Luỹ kế từ đầu năm đến cuối kỳ này"
    columns[0]["header_path_exact"] = [common, "Năm nay"]
    columns[1]["header_path_exact"] = [common, "Năm trước"]
    region = _region()
    receipt = subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [region]
    )

    result = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=[region],
        page_json_by_version={PAGE_3: note},
        selected_page_axis=[_selected(page=PAGE_3, physical_page=3)],
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert result["status"] == subject.READY
    assert result["closure_receipt"]["table_receipts"][0]["lane_axis"][
        "lane_keys"
    ] == [
        ["SEMANTIC_ALIAS", "CURRENT_PERIOD"],
        ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
    ]
    validate_source_observation_mapping_contract_v1(result)


def test_explicit_sibling_root_continuation_selects_only_marked_blank_receiver() -> None:
    compiled = _compiled()
    first = _page(
        table=_table(
            unit="Triệu đồng",
            rows=[_row("Trả lãi tiền gửi", ["60", "50"])],
        ),
        title="29. Chi phí lãi và các chi phí tương tự",
        status="FINANCIAL_NOTE_CONTENT",
        content_kind="FINANCIAL_NOTE",
        statement_type="INCOME_STATEMENT",
    )
    first_table = first["sections"][0]["tables"][0]
    first_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second = _page(
        table=_table(
            unit=None,
            rows=[
                _row("Trả lãi tiền vay", ["20", "20"]),
                _row("Trả lãi phát hành giấy tờ có giá", ["15", "15"]),
                _row("Trả lãi tiền thuê tài chính", ["-", "-"]),
                _row("Chi phí hoạt động tín dụng khác", ["5", "5"]),
                _row(None, ["100", "90"], "TOTAL"),
            ],
        ),
        title=None,
        status="FINANCIAL_NOTE_CONTENT",
        content_kind="FINANCIAL_NOTE",
        statement_type="INCOME_STATEMENT",
    )
    second_table = second["sections"][0]["tables"][0]
    second_table["columns"] = [
        {"header_path_exact": [None], "value_kind": "MONEY"},
        {"header_path_exact": [None], "value_kind": "MONEY"},
    ]
    second_table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    records = [
        _record(page_json=first, page=PAGE_1, physical_page=1),
        _record(page_json=second, page=PAGE_2, physical_page=2),
    ]

    selected = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )

    assert selected["status"] == subject.READY
    assert [
        region["page_json_version_id"]
        for region in selected["component_regions"]
    ] == [PAGE_1, PAGE_2]
    receipt = subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        selected["component_regions"]
    )
    candidate = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=selected["component_regions"],
        page_json_by_version={PAGE_1: first, PAGE_2: second},
        selected_page_axis=[
            _selected(page=PAGE_1, physical_page=1),
            _selected(page=PAGE_2, physical_page=2),
        ],
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert candidate["status"] == subject.READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == {
        1151,
        1152,
        1153,
        1154,
        1155,
        1156,
    }
    root = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert len(root["source_refs"]) == 1
    assert root["source_refs"][0]["row_ordinal"] == 5
    assert root["source_refs"][0]["row_kind"] == "TOTAL"
    assert root["source_refs"][0]["locator"]["page_json_version_id"] == PAGE_2
    continuation_receipt = candidate["closure_receipt"]["table_receipts"][1][
        "adjacent_continuation_family_root_receipt"
    ]
    assert set(continuation_receipt) == {
        "component_roles",
        "prior_region",
        "receiver_region",
        "receiver_total_row_ordinal",
        "rule",
        "source_equation_id",
    }
    assert continuation_receipt["prior_region"] == selected["component_regions"][0]
    assert continuation_receipt["receiver_region"] == selected["component_regions"][1]
    assert continuation_receipt["receiver_total_row_ordinal"] == 5
    assert continuation_receipt["component_roles"] == [
        "DEPOSIT_INTEREST",
        "BORROWING_INTEREST",
        "ISSUED_PAPER_INTEREST",
        "FINANCE_LEASE_INTEREST",
        "OTHER_CREDIT_EXPENSE",
    ]
    continuation_equation = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_id"] == continuation_receipt["source_equation_id"]
    )
    assert continuation_equation["result_source_refs"] == root["source_refs"]
    assert {
        source_ref["locator"]["page_json_version_id"]
        for source_refs in continuation_equation["component_source_refs"]
        for source_ref in source_refs
    } == {PAGE_1, PAGE_2}
    validate_source_observation_mapping_contract_v1(candidate)

    blank_detail = copy.deepcopy(records)
    blank_detail[1]["page_json"]["sections"][0]["tables"][0]["rows"][3][
        "values_exact"
    ][1] = None
    blank_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=blank_detail,
        compiled_specs=compiled,
    )
    blank_receipt = (
        subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            blank_cluster["component_regions"]
        )
    )
    blank_candidate = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=blank_cluster["component_regions"],
        page_json_by_version={
            PAGE_1: blank_detail[0]["page_json"],
            PAGE_2: blank_detail[1]["page_json"],
        },
        selected_page_axis=[
            _selected(page=PAGE_1, physical_page=1),
            _selected(page=PAGE_2, physical_page=2),
        ],
        compiled_specs=compiled,
        query_receipt=blank_receipt,
    )

    assert blank_candidate["status"] == subject.UNRESOLVED
    assert blank_candidate["mappings"] == []
    blank_cells: list[dict] = []

    def collect_blank_cells(value: object) -> None:
        if isinstance(value, dict):
            if value.get("state") == "BLANK_SOURCE_CELL":
                blank_cells.append(value)
            for child in value.values():
                collect_blank_cells(child)
        elif isinstance(value, list):
            for child in value:
                collect_blank_cells(child)

    collect_blank_cells(blank_candidate["closure_receipt"])
    assert blank_cells
    assert all(
        cell.get("coefficient") is None and cell.get("source_text") is None
        for cell in blank_cells
    )

    mismatched = copy.deepcopy(records)
    mismatched[1]["page_json"]["sections"][0]["tables"][0]["rows"][-1][
        "values_exact"
    ][0] = "110"
    mismatched_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=mismatched,
        compiled_specs=compiled,
    )
    mismatched_receipt = (
        subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            mismatched_cluster["component_regions"]
        )
    )
    mismatched_candidate = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=mismatched_cluster["component_regions"],
        page_json_by_version={
            PAGE_1: mismatched[0]["page_json"],
            PAGE_2: mismatched[1]["page_json"],
        },
        selected_page_axis=[
            _selected(page=PAGE_1, physical_page=1),
            _selected(page=PAGE_2, physical_page=2),
        ],
        compiled_specs=compiled,
        query_receipt=mismatched_receipt,
    )

    assert mismatched_candidate["status"] == subject.UNRESOLVED
    assert mismatched_candidate["mappings"] == []

    unmarked = copy.deepcopy(records)
    unmarked[1]["page_json"]["sections"][0]["tables"][0]["continuation"] = "NONE"
    rejected_receiver = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=unmarked,
        compiled_specs=compiled,
    )

    assert rejected_receiver["status"] == subject.UNRESOLVED
    assert rejected_receiver["component_regions"] == []


def test_family_root_stops_at_visible_family_total_before_net_interest() -> None:
    compiled = _compiled()
    note = _note_page(unit="Triệu đồng")
    note["sections"][0]["tables"][0]["rows"].append(
        _row("Thu nhập lãi thuần", ["40", "30"], "SUBTOTAL")
    )
    region = _region()
    receipt = subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [region]
    )

    result = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=[region],
        page_json_by_version={PAGE_3: note},
        selected_page_axis=[_selected(page=PAGE_3, physical_page=3)],
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert result["status"] == subject.READY
    root = next(mapping for mapping in result["mappings"] if mapping["report_norm_id"] == 1151)
    assert [cell["coefficient"] for cell in root["values"]] == [100, 90]
    assert all(mapping["row_id"] != "r7" for mapping in result["mappings"])
    validate_source_observation_mapping_contract_v1(result)


def test_display_rounding_is_opt_in_and_never_applies_to_vnd() -> None:
    compiled = _compiled()
    region = _region()
    receipt = subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [region]
    )

    million = _note_page(unit="Triệu đồng")
    million["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "59"
    accepted = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=[region],
        page_json_by_version={PAGE_3: million},
        selected_page_axis=[_selected(page=PAGE_3, physical_page=3)],
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert accepted["status"] == subject.READY
    assert any(
        equation["status"] == "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
        for equation in accepted["closure_receipt"]["equations"]
    )
    assert [
        cell["coefficient"]
        for cell in next(
            mapping
            for mapping in accepted["mappings"]
            if mapping["role"] == "DEPOSIT_INTEREST"
        )["values"]
    ] == [59, 50]
    assert [
        cell["coefficient"]
        for cell in next(
            mapping
            for mapping in accepted["mappings"]
            if mapping["report_norm_id"] == 1151
        )["values"]
    ] == [100, 90]

    vnd = _note_page(unit="VND")
    vnd["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "59"
    rejected = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=[region],
        page_json_by_version={PAGE_3: vnd},
        selected_page_axis=[_selected(page=PAGE_3, physical_page=3)],
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert rejected["status"] == subject.UNRESOLVED
    assert rejected["mappings"] == []


def test_source_repair_identity_and_before_image_tampering_fail_closed() -> None:
    repair = _money_repair()
    tampered = copy.deepcopy(repair)
    tampered["row_ordinal"] = 3
    with pytest.raises(
        subject.GeminiJsonInterestExpenseFamilyV1Error, match="identity drifted"
    ):
        _compiled(tampered)

    compiled = _compiled(repair)
    page = _note_page()
    page["sections"][0]["tables"][0]["rows"][3]["values_exact"][1] = "0"
    with pytest.raises(
        subject.GeminiJsonInterestExpenseFamilyV1Error, match="before-image drifted"
    ):
        subject._document_repairs(
            regions=[_region()],
            page_json_by_version={PAGE_3: page},
            compiled_specs=compiled,
        )


def test_pdf_visible_dash_repair_preserves_source_zero_not_blank_zero() -> None:
    repair = _money_repair(before=None)
    compiled = _compiled(repair)
    page = _note_page()
    page["sections"][0]["tables"][0]["rows"][3]["values_exact"][1] = None

    pages, receipts = subject._document_repairs(
        regions=[_region()],
        page_json_by_version={PAGE_3: page},
        compiled_specs=compiled,
    )

    assert pages[PAGE_3]["sections"][0]["tables"][0]["rows"][3][
        "values_exact"
    ][1] == "-"
    assert len(receipts) == 1


def test_appended_pdf_rows_reclassify_other_role_without_bank_routing() -> None:
    page = _note_page()
    table = page["sections"][0]["tables"][0]
    table["rows"] = table["rows"][:4]
    material = {
        "after_rows_exact": [
            _row("Chi phí hoạt động tín dụng khác", ["5", "5"]),
            _row("Tổng", ["100", "90"], "TOTAL"),
        ],
        "before_row_count": 4,
        "locator": {
            "page_json_version_id": PAGE_3,
            "physical_page": 3,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "6" * 64,
        "repair_kind": "APPEND_ROWS_PDF_VISIBLE_EXACT",
        "source_sha256": SOURCE_SHA256,
    }
    repair = {
        **material,
        "repair_id": "gjiefav1:repair:" + canonical_json_sha256_v1(material),
    }
    compiled = _compiled(repair)
    region = _region()
    region["component_roles"] = [
        "BORROWING_INTEREST",
        "DEPOSIT_INTEREST",
        "FINANCE_LEASE_INTEREST",
        "ISSUED_PAPER_INTEREST",
    ]
    pages, _receipts = subject._document_repairs(
        regions=[region],
        page_json_by_version={PAGE_3: page},
        compiled_specs=compiled,
    )
    regions, changes = subject._reclassified_regions(
        regions=[region], pages=pages, compiled_specs=compiled
    )

    assert "OTHER_CREDIT_EXPENSE" in regions[0]["component_roles"]
    assert changes[0]["before_component_roles"] != changes[0][
        "after_component_roles"
    ]


def test_unitless_note_binds_unique_primary_unit_by_exact_visible_total() -> None:
    pages = {
        PAGE_1: _primary_page(
            unit="Triệu đồng", values=["(11)", "(12)", "(100)", "(90)"]
        ),
        PAGE_3: _note_page(),
    }
    receipts = subject._bind_exact_primary_statement_unit(
        pages=pages,
        regions=[_region()],
        selected_page_axis=[
            _selected(page=PAGE_1, physical_page=1),
            _selected(page=PAGE_3, physical_page=3),
        ],
        compiled_specs=_compiled(),
    )

    assert pages[PAGE_3]["sections"][0]["tables"][0]["unit_exact"] == "Triệu đồng"
    assert receipts[0]["canonical_unit"] == "MILLION_VND"
    assert receipts[0]["matched_primary_roots"][0]["match_kind"] == (
        "EXACT_MAGNITUDE_VECTOR_WITH_SOURCE_PRESENTATION_SIGN_DIFFERENCE"
    )


def test_unitless_note_uses_only_contiguous_preceding_primary_page_unit() -> None:
    pages = {
        PAGE_1: _unit_page("VND"),
        PAGE_2: _primary_page(unit=None, values=["(100)", "(90)"]),
        PAGE_3: _note_page(),
    }
    selected = [
        _selected(page=PAGE_1, physical_page=1),
        _selected(page=PAGE_2, physical_page=2),
        _selected(page=PAGE_3, physical_page=3),
    ]
    receipts = subject._bind_exact_primary_statement_unit(
        pages=pages,
        regions=[_region()],
        selected_page_axis=selected,
        compiled_specs=_compiled(),
    )

    assert pages[PAGE_3]["sections"][0]["tables"][0]["unit_exact"] == "VND"
    assert receipts[0]["matched_primary_roots"][0]["unit_receipt"]["rule"] == (
        "IMMEDIATELY_PRECEDING_CONTIGUOUS_PRIMARY_STATEMENT_PAGE_EXPLICIT_UNIT"
    )

    noncontiguous_pages = copy.deepcopy(pages)
    noncontiguous_pages[PAGE_3]["sections"][0]["tables"][0]["unit_exact"] = None
    noncontiguous = copy.deepcopy(selected)
    noncontiguous[1]["physical_page"] = 4
    noncontiguous[1]["selected_page_ordinal"] = 2
    assert subject._bind_exact_primary_statement_unit(
        pages=noncontiguous_pages,
        regions=[_region()],
        selected_page_axis=noncontiguous,
        compiled_specs=_compiled(),
    ) == []


@pytest.mark.parametrize("case", ["mismatch", "conflicting_units"])
def test_unit_corroboration_fails_closed_without_one_exact_canonical_unit(
    case: str,
) -> None:
    primary = _primary_page(
        unit="Triệu đồng",
        values=["(101)", "(91)" if case == "mismatch" else "(90)"],
    )
    pages = {PAGE_1: primary, PAGE_3: _note_page()}
    selected = [
        _selected(page=PAGE_1, physical_page=1),
        _selected(page=PAGE_3, physical_page=3),
    ]
    if case == "conflicting_units":
        primary["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [
            "(100)",
            "(90)",
        ]
        pages[PAGE_2] = _primary_page(unit="VND", values=["(100)", "(90)"])
        selected.insert(1, _selected(page=PAGE_2, physical_page=2))

    assert subject._bind_exact_primary_statement_unit(
        pages=pages,
        regions=[_region()],
        selected_page_axis=selected,
        compiled_specs=_compiled(),
    ) == []
    assert pages[PAGE_3]["sections"][0]["tables"][0]["unit_exact"] is None


def test_evaluation_is_deterministic_and_source_observation_contract_valid() -> None:
    compiled = _compiled()
    pages = {
        PAGE_1: _primary_page(unit="Triệu đồng", values=["(100)", "(90)"]),
        PAGE_3: _note_page(),
    }
    region = _region()
    selected = [
        _selected(page=PAGE_1, physical_page=1),
        _selected(page=PAGE_3, physical_page=3),
    ]
    receipt = subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [region]
    )

    first = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=[region],
        page_json_by_version=pages,
        selected_page_axis=selected,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    second = subject.validate_gemini_json_interest_expense_candidate_replay_v1(
        first,
        regions=[region],
        page_json_by_version=pages,
        selected_page_axis=selected,
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert first == second
    assert first["status"] == subject.READY
    assert {mapping["unit"] for mapping in first["mappings"]} == {"MILLION_VND"}
    validate_source_observation_mapping_contract_v1(first)


@pytest.mark.parametrize(
    ("finance_values", "expected"),
    [
        ([None, None], None),
        (["-", None], [0, None]),
    ],
)
def test_exact_parent_never_infers_blank_child_but_visible_sister_lane_survives(
    finance_values: list[str | None], expected: list[int | None] | None
) -> None:
    compiled = _compiled()
    note = _note_page(unit="Triệu đồng")
    note["sections"][0]["tables"][0]["rows"][3]["values_exact"] = finance_values
    region = _region()
    receipt = subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        [region]
    )

    result = subject.evaluate_gemini_json_interest_expense_family_cluster_v1(
        regions=[region],
        page_json_by_version={PAGE_3: note},
        selected_page_axis=[_selected(page=PAGE_3, physical_page=3)],
        compiled_specs=compiled,
        query_receipt=receipt,
    )

    assert result["status"] == subject.READY
    finance = next(
        (
            mapping
            for mapping in result["mappings"]
            if mapping["role"] == "FINANCE_LEASE_INTEREST"
        ),
        None,
    )
    if expected is None:
        assert finance is None
    else:
        assert [cell["coefficient"] for cell in finance["values"]] == expected
        assert finance["values"][0]["state"] == "DASH_ZERO"
        assert finance["values"][1] == {
            "coefficient": None,
            "source_text": None,
            "state": "BLANK_SOURCE_CELL",
        }
    validate_source_observation_mapping_contract_v1(result)
