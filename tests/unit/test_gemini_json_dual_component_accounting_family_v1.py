from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_dual_component_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonDualComponentAccountingFamilyV1Error,
    build_gemini_json_dual_component_region_query_receipt_v1,
    coalesce_gemini_json_dual_component_page_v1,
    compile_gemini_json_dual_component_family_specs_v1,
    evaluate_gemini_json_dual_component_family_cluster_v1,
    validate_gemini_json_dual_component_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION = "gfpstorev1:json:" + "a" * 64
DOCUMENT = "gfpstorev1:document:" + "b" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _compiled() -> dict:
    return compile_gemini_json_dual_component_family_specs_v1(
        _json("tm-purchased-debt-activity-topology-v1.json"),
        _json("tm-purchased-debt-activity-evaluation-v1.json"),
        _json("tm-purchased-debt-activity-schema-binding-v1.json"),
    )


def _columns(*, missing: bool = False, partial_unit: bool = False) -> list[dict]:
    if missing:
        return [
            {"header_path_exact": [None], "value_kind": "MONEY"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ]
    return [
        {
            "header_path_exact": ["30/06/2026", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2025", None if partial_unit else "Triệu đồng"],
            "value_kind": "MONEY",
        },
    ]


def _row(label: str | None, values: list[str | None], kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [] if label is None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _balance(*, fx: bool = True, unit: str | None = "Triệu đồng") -> dict:
    rows = [_row("Mua nợ bằng VND", ["100", "80"])]
    if fx:
        rows.append(_row("Mua nợ bằng ngoại tệ", ["10", "5"]))
    rows.extend(
        [
            _row("Dự phòng rủi ro", ["(20)", "(15)"]),
            _row(None, ["90" if fx else "80", "70" if fx else "65"], "TOTAL"),
        ]
    )
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }


def _detail(
    *,
    interest: bool = True,
    missing_axes: bool = False,
    total: bool = True,
    unit: str | None = "Triệu đồng",
) -> dict:
    rows = [_row("Nợ gốc đã mua", ["70", "60"])]
    if interest:
        rows.append(_row("Lãi từ các khoản nợ đã mua", ["5", "4"]))
    if total:
        rows.append(_row(None, ["75" if interest else "70", "64" if interest else "60"], "TOTAL"))
    return {
        "columns": _columns(missing=missing_axes),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": "Giá trị nợ gốc và lãi của các khoản nợ đã mua",
        "unit_exact": unit,
    }


def _section(title: str | None, *tables: dict, narratives: list[str] | None = None) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": narratives or [],
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _page(*sections: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": list(sections),
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _base_page() -> dict:
    return _page(_section("11. Hoạt động mua nợ", _balance(), _detail()))


def _locator(section_id: str, table_id: str) -> dict:
    return {
        "document_id": DOCUMENT,
        "document_ordinal": 1,
        "page_json_version_id": VERSION,
        "physical_page": 9,
        "section_id": section_id,
        "selected_page_ordinal": 9,
        "source_logical_name": "report.pdf",
        "source_sha256": "c" * 64,
        "table_id": table_id,
    }


def _regions(section_ids: tuple[str, str] = ("s1", "s1")) -> list[dict]:
    return [
        _locator(section_ids[0], "t1"),
        _locator(section_ids[1], "t2" if section_ids[1] == "s1" else "t1"),
    ]


def _evaluate(page: dict, regions: list[dict] | None = None) -> dict:
    checked_regions = regions or _regions()
    return evaluate_gemini_json_dual_component_family_cluster_v1(
        regions=checked_regions,
        page_json_by_version={VERSION: page},
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_dual_component_region_query_receipt_v1(checked_regions),
    )


def _coalesce(page: dict) -> dict:
    return coalesce_gemini_json_dual_component_page_v1(
        page_json=page,
        locator={
            key: value
            for key, value in _locator("s1", "t1").items()
            if key not in {"section_id", "table_id"}
        },
        compiled_specs=_compiled(),
    )


def test_independent_totals_optional_roles_and_structural_root() -> None:
    candidate = _evaluate(_base_page())
    assert candidate["status"] == READY
    assert [mapping["report_norm_id"] for mapping in candidate["mappings"]] == [
        801,
        802,
        803,
        5738,
        5739,
    ]
    assert len(candidate["closure_receipt"]["equations"]) == 4
    assert candidate["closure_receipt"]["equations"][0]["result_coefficient"] == 90
    assert candidate["closure_receipt"]["equations"][2]["result_coefficient"] == 75
    root = candidate["closure_receipt"]["structural_root_receipt"]
    assert root == {
        "emitted_mapping": False,
        "mapping_policy": "STRUCTURAL_CONTEXT_ONLY",
        "report_norm_id": 800,
        "role": "PURCHASED_DEBT_ACTIVITY_ROOT",
    }
    assert 800 not in {mapping["report_norm_id"] for mapping in candidate["mappings"]}


def test_exact_sibling_period_and_unit_inheritance() -> None:
    page = _page(
        _section(
            "Hoạt động mua nợ",
            _balance(),
            _detail(missing_axes=True, unit=None),
        )
    )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    axes = candidate["closure_receipt"]["axes_by_component"]["DETAIL"]
    assert axes["period"]["source"] == "EXACT_SAME_PAGE_BALANCE_SIBLING_INHERITANCE"
    assert axes["unit"]["source"] == "EXACT_SAME_PAGE_BALANCE_SIBLING_INHERITANCE"


def test_partial_or_wrong_period_and_unit_evidence_cannot_inherit() -> None:
    page = _base_page()
    page["sections"][0]["tables"][1]["unit_exact"] = None
    page["sections"][0]["tables"][1]["columns"] = _columns(partial_unit=True)
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "DETAIL:MONEY_COLUMN_UNITS_ARE_NOT_UNIFORMLY_EXPLICIT" in candidate["reasons"]

    wrong = _base_page()
    wrong["sections"][0]["tables"][1]["columns"][0]["header_path_exact"][0] = "30/09/2026"
    candidate = _evaluate(wrong)
    assert candidate["status"] == UNRESOLVED
    assert "EXPLICIT_SIBLING_PERIOD_AXES_DIFFER" in candidate["reasons"]


def test_blank_zero_is_promoted_only_after_all_equations_close() -> None:
    exact_page = _base_page()
    balance = exact_page["sections"][0]["tables"][0]
    balance["rows"][1]["values_exact"][1] = None
    balance["rows"][-1]["values_exact"][1] = "65"
    exact = _evaluate(exact_page)
    assert exact["status"] == READY
    fx = next(mapping for mapping in exact["mappings"] if mapping["report_norm_id"] == 802)
    assert fx["values"][1]["state"] == "INFERRED_BLANK_ZERO_EQUATION_EXACT"

    mismatch_page = _base_page()
    mismatch_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = None
    mismatch = _evaluate(mismatch_page)
    assert mismatch["status"] == UNRESOLVED
    assert mismatch["mappings"] == []
    balance_inventory = mismatch["closure_receipt"]["source_inventory"][0]
    assert balance_inventory["row_axis"][0]["values_exact"][0] is None
    equation_cell = mismatch["closure_receipt"]["equations"][0]["component_role_coefficients"][0]
    assert equation_cell["state"] == "BLANK_ZERO_IF_EQUATION_EXACT"


def test_structural_gross_fallback_is_narrow_and_visible_total_vetoes_mismatch() -> None:
    balance = _balance(fx=False)
    detail = _detail(interest=False, total=False)
    detail["rows"][0]["values_exact"] = ["100", "80"]
    fallback = _evaluate(_page(_section("Hoạt động mua nợ", balance, detail)))
    assert fallback["status"] == READY
    assert fallback["closure_receipt"]["fallback_used"] is True

    ambiguous = _page(_section("Hoạt động mua nợ", _balance(), copy.deepcopy(detail)))
    candidate = _evaluate(ambiguous)
    assert candidate["status"] == UNRESOLVED
    assert "DETAIL_VISIBLE_TOTAL_ABSENT_AND_GROSS_FALLBACK_NOT_STRUCTURAL" in candidate["reasons"]

    visible = _base_page()
    visible["sections"][0]["tables"][1]["rows"][-1]["values_exact"][0] = "74"
    candidate = _evaluate(visible)
    assert candidate["status"] == UNRESOLVED
    assert "DETAIL_LANE_EQUATION_MISMATCH:CURRENT_PERIOD" in candidate["reasons"]


def test_visible_total_must_trail_every_component_role() -> None:
    page = _base_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    rows[-1], rows[-2] = rows[-2], rows[-1]
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert any("COMPONENT_ROLE_AFTER_VISIBLE_TOTAL" in reason for reason in candidate["reasons"])


def test_candidate_replay_rejects_tamper() -> None:
    page = _base_page()
    candidate = _evaluate(page)
    tampered = copy.deepcopy(candidate)
    tampered["mappings"][0]["values"][0]["coefficient"] += 1
    regions = _regions()
    with pytest.raises(
        GeminiJsonDualComponentAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        validate_gemini_json_dual_component_family_candidate_replay_v1(
            tampered,
            regions=regions,
            page_json_by_version={VERSION: page},
            compiled_specs=_compiled(),
            query_receipt=build_gemini_json_dual_component_region_query_receipt_v1(regions),
        )


def test_coalescer_rejects_duplicate_and_extra_declared_role_populations() -> None:
    duplicate = _page(_section("Hoạt động mua nợ", _balance(), _balance(), _detail()))
    assert "EXACTLY_TWO_SEED_BEARING_FRAGMENTS_REQUIRED" in _coalesce(duplicate)["reasons"]

    extra = _page(
        _section(
            "Hoạt động mua nợ",
            _balance(),
            _detail(),
            {
                "columns": _columns(),
                "continuation": "NONE",
                "rows": [_row("Lãi của khoản nợ đã mua", ["1", "1"])],
                "title_exact": "Chi tiết bổ sung",
                "unit_exact": "Triệu đồng",
            },
        )
    )
    assert "UNCONSUMED_ROLE_BEARING_FRAGMENT_UNDER_OWNER_FENCE" in _coalesce(extra)["reasons"]

    mixed_extra = _page(
        _section(
            "Hoạt động mua nợ",
            _balance(),
            _detail(),
            {
                "columns": _columns(),
                "continuation": "NONE",
                "rows": [
                    _row("Lãi từ các khoản nợ đã mua", ["1", "1"]),
                    _row("Khoản mục ngoài gia đình", ["2", "2"]),
                ],
                "title_exact": "Chi tiết bổ sung",
                "unit_exact": "Triệu đồng",
            },
        )
    )
    mixed_result = _coalesce(mixed_extra)
    assert "UNCONSUMED_ROLE_BEARING_FRAGMENT_UNDER_OWNER_FENCE" in mixed_result["reasons"]
    assert mixed_result["role_bearing_fragments"][-1]["population_disposition"] == (
        "DECLARED_ROLE_MIXED_WITH_FOREIGN_POPULATION"
    )

    mixed_provision = copy.deepcopy(mixed_extra)
    mixed_provision["sections"][0]["tables"][-1]["rows"][0] = _row("Dự phòng rủi ro", ["1", "1"])
    mixed_result = _coalesce(mixed_provision)
    assert "UNCONSUMED_ROLE_BEARING_FRAGMENT_UNDER_OWNER_FENCE" in mixed_result["reasons"]
    assert mixed_result["role_bearing_fragments"][-1]["population_disposition"] == (
        "DECLARED_ROLE_MIXED_WITH_FOREIGN_POPULATION"
    )


def test_foreign_population_incidental_role_does_not_compete_with_seed_fragments() -> None:
    historical = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Giá trị nợ gốc bằng VND", ["200", "200"]),
            _row("Lãi dự thu", ["2", "2"]),
            _row("Dự phòng rủi ro", ["(1)", "(1)"]),
            _row(None, ["201", "201"], "TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    result = _coalesce(_page(_section("Hoạt động mua nợ", historical, _balance(), _detail())))
    assert result["status"] == "ACCEPTED"
    assert result["role_bearing_fragments"][0]["population_disposition"] == (
        "INCIDENTAL_ROLE_IN_FOREIGN_POPULATION"
    )

    movement = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ", ["1", "1"]),
            _row("Dự phòng chung", ["1", "1"]),
            _row("Số dư cuối kỳ", ["2", "2"], "TOTAL"),
        ],
        "title_exact": "Thay đổi dự phòng rủi ro mua nợ trong kỳ như sau:",
        "unit_exact": "Triệu đồng",
    }
    result = _coalesce(_page(_section("Hoạt động mua nợ", _balance(), _detail(), movement)))
    assert result["status"] == "ACCEPTED"
    assert result["role_bearing_fragments"][-1]["owner"] is None


def test_cross_section_owner_interval_and_resets_are_fail_closed() -> None:
    accepted = _page(
        _section("Hoạt động mua nợ", _balance()),
        _section("Chi tiết nợ đã mua", _detail()),
    )
    result = _coalesce(accepted)
    assert result["status"] == "ACCEPTED"
    assert [item["section_id"] for item in result["component_regions"]] == ["s1", "s2"]

    reset = _page(
        _section("Hoạt động mua nợ", _balance()),
        _section("12. Chứng khoán đầu tư"),
        _section("Chi tiết nợ đã mua", _detail()),
    )
    assert "COMPONENT_FRAGMENTS_CROSS_OWNER_OR_RESET_FENCE" in _coalesce(reset)["reasons"]

    narrative_reset = _page(
        _section("Hoạt động mua nợ", _balance()),
        _section(None, narratives=["12. Chứng khoán đầu tư"]),
        _section("Chi tiết nợ đã mua", _detail()),
    )
    result = _coalesce(narrative_reset)
    assert "NONORDERABLE_NARRATIVE_RESET_OR_HARD_NEGATIVE_IN_INTERVAL" in result["reasons"]

    reset_after_owner_before_components = _page(
        _section("Hoạt động mua nợ"),
        _section(None, narratives=["12. Chứng khoán đầu tư"]),
        _section("Chi tiết nợ đã mua", _balance(), _detail()),
    )
    result = _coalesce(reset_after_owner_before_components)
    assert "NONORDERABLE_NARRATIVE_RESET_OR_HARD_NEGATIVE_IN_INTERVAL" in result["reasons"]


def test_multiple_distinct_dates_in_one_header_are_unresolved() -> None:
    page = _base_page()
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"][0] = (
        "30/06/2026 / 31/12/2025"
    )
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert "BALANCE:MULTIPLE_DISTINCT_DATES_IN_ONE_PERIOD_HEADER" in candidate["reasons"]


def test_owner_can_be_exact_section_narrative_heading() -> None:
    page = _page(
        _section(
            "Thuyết minh báo cáo tài chính (tiếp theo)",
            _balance(),
            _detail(),
            narratives=["11. HOẠT ĐỘNG MUA NỢ"],
        )
    )
    assert _coalesce(page)["status"] == "ACCEPTED"
