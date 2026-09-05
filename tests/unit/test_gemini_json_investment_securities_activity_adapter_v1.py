from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_investment_securities_activity_family_v1 import (
    GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
    _apply_source_repairs_v1,
    _primary_query_recovery_v1,
    build_gemini_json_investment_securities_activity_region_query_receipt_v1,
    compile_gemini_json_investment_securities_activity_family_specs_v1,
    evaluate_gemini_json_investment_securities_activity_family_cluster_v1,
    validate_gemini_json_investment_securities_activity_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
ROOT_LABEL = "Lãi thuần từ mua bán chứng khoán đầu tư"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_investment_securities_activity_family_specs_v1(
        _json("tm-investment-securities-activity-topology-v1.json"),
        _json("tm-investment-securities-activity-evaluation-v1.json"),
        _json("tm-investment-securities-activity-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    parent: str | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            [label]
            if parent is None and label == ROOT_LABEL
            else [ROOT_LABEL, label]
            if parent is None
            else [parent, label]
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _page(*, provision: bool = True, net: tuple[str, str] = ("70", "60")) -> dict[str, Any]:
    rows = [
        _row(ROOT_LABEL, list(net), kind="TOTAL"),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"]),
        _row(
            "Chi phí về mua bán chứng khoán đầu tư",
            ["(20)", "(15)"] if provision else ["(30)", "(20)"],
        ),
    ]
    if provision:
        rows.append(_row("Trích lập dự phòng rủi ro chứng khoán đầu tư", ["(10)", "(5)"]))
    table = {
        "columns": [
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": ROOT_LABEL,
        "unit_exact": "Triệu đồng",
    }
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": ROOT_LABEL,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate(page: dict[str, Any]) -> dict[str, Any]:
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    return evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_investment_securities_activity_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def _candidate_and_replay_inputs(
    page: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    page_json_by_version = {VERSION_ID: page}
    receipt = build_gemini_json_investment_securities_activity_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, regions, page_json_by_version, receipt


def test_investment_securities_optional_provision_and_net_close_exactly() -> None:
    candidate = _evaluate(_page())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(by_role) == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
        "PROVISION_INVESTMENT_SECURITIES",
    }
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        70,
        60,
    ]


def test_investment_securities_absent_optional_provision_does_not_create_mapping() -> None:
    candidate = _evaluate(_page(provision=False))
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
    }


def test_investment_securities_single_visible_component_can_prove_source_total() -> None:
    page = _page(provision=False, net=("100", "80"))
    page["sections"][0]["tables"][0]["rows"] = [
        _row(ROOT_LABEL, ["100", "80"], kind="TOTAL"),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"]),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
    }


@pytest.mark.parametrize(
    ("source_label", "surface_kind"),
    [(None, "UNLABELED_TOTAL"), ("Cộng", "GENERIC_TONG_OR_CONG")],
)
def test_investment_securities_terminal_source_result_is_projected_and_restored(
    source_label: str | None,
    surface_kind: str,
) -> None:
    page = _page()
    rows = page["sections"][0]["tables"][0]["rows"]
    page["sections"][0]["tables"][0]["rows"] = [
        *rows[1:],
        _row(source_label, ["70", "60"], kind="TOTAL"),
    ]

    candidate = _evaluate(page)

    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert {ref["label_exact"] for ref in root["source_refs"]} == {source_label}
    receipt = candidate["closure_receipt"][
        "investment_securities_activity_adapter_receipt"
    ]["terminal_result_projection_receipts"]
    assert len(receipt) == 1
    assert receipt[0]["source_result_surface_kind"] == surface_kind


def test_investment_securities_terminal_projection_and_root_requirement_fail_closed() -> None:
    no_result = _page()
    no_result["sections"][0]["tables"][0]["rows"] = no_result["sections"][0][
        "tables"
    ][0]["rows"][1:]
    candidate = _evaluate(no_result)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN" in candidate["reasons"]

    nonterminal = _page()
    rows = nonterminal["sections"][0]["tables"][0]["rows"]
    nonterminal["sections"][0]["tables"][0]["rows"] = [
        *rows[1:],
        _row("Cộng", ["70", "60"], kind="TOTAL"),
        _row("Khác", ["1", "1"]),
    ]
    candidate = _evaluate(nonterminal)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_investment_securities_source_result_sign_orientation_is_lane_local_veto() -> None:
    page = _page(net=("90", "(15)"))
    rows = page["sections"][0]["tables"][0]["rows"]
    rows[1]["values_exact"] = ["100", "-"]
    rows[2]["values_exact"] = ["20", "10"]
    rows[3]["values_exact"] = ["10", "5"]

    candidate = _evaluate(page)

    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"][
        "source_visible_family_result_direct_mapping_receipt"
    ]
    assert receipt["matching_multiplier_candidates"] == []
    assert receipt["matching_multiplier_candidates_by_lane"] == [
        {"lane_ordinal": 0, "matching_multiplier_candidates": [[1, -1, 1]]},
        {"lane_ordinal": 1, "matching_multiplier_candidates": [[1, -1, -1]]},
    ]

    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][1] = "(18)"
    rejected = _evaluate(page)
    assert rejected["status"] == UNRESOLVED
    assert rejected["mappings"] == []
    assert rejected["reasons"] == ["SOURCE_VISIBLE_FAMILY_RESULT_COMPONENT_VETO_MISMATCH"]


def test_investment_securities_net_mismatch_is_unresolved_without_mappings() -> None:
    candidate = _evaluate(_page(net=("72", "62")))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_investment_securities_scaled_display_rounding_is_explicit_and_vnd_is_exact() -> None:
    rounded = _evaluate(_page(net=("71", "61")))
    assert rounded["status"] == READY
    root = next(mapping for mapping in rounded["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [71, 61]
    assert any(
        equation["status"] == "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"
        for equation in rounded["closure_receipt"]["equations"]
    )

    vnd_page = _page(net=("71", "61"))
    table = vnd_page["sections"][0]["tables"][0]
    table["unit_exact"] = "VND"
    for column in table["columns"]:
        column["header_path_exact"][-1] = "VND"
    vnd = _evaluate(vnd_page)
    assert vnd["status"] == UNRESOLVED
    assert vnd["mappings"] == []


def test_investment_securities_partial_blank_lanes_stay_null_and_parent_does_not_infer() -> None:
    page = _page()
    rows = page["sections"][0]["tables"][0]["rows"]
    rows[0]["values_exact"] = ["70", None]
    rows[1]["values_exact"] = ["100", "80"]
    rows[2]["values_exact"] = ["(20)", None]
    rows[3]["values_exact"] = ["(10)", None]

    candidate = _evaluate(page)

    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["EXPENSE_INVESTMENT_SECURITIES"]["values"][1] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert by_role["FAMILY_ROOT_TOTAL"]["values"][1] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert validate_source_observation_mapping_contract_v1(candidate)["violation_count"] == 0

    parent_visible = _page()
    parent_rows = parent_visible["sections"][0]["tables"][0]["rows"]
    parent_rows[2]["values_exact"] = ["(20)", None]
    parent_candidate = _evaluate(parent_visible)
    expense = next(
        mapping
        for mapping in parent_candidate["mappings"]
        if mapping["role"] == "EXPENSE_INVESTMENT_SECURITIES"
    )
    assert expense["values"][1]["coefficient"] is None
    assert expense["values"][1]["state"] == "BLANK_SOURCE_CELL"


def test_investment_securities_all_blank_role_is_omitted_but_visible_dash_maps_zero() -> None:
    all_blank = _page(net=("80", "65"))
    all_blank["sections"][0]["tables"][0]["rows"][3]["values_exact"] = [None, None]
    blank_candidate = _evaluate(all_blank)
    assert blank_candidate["status"] == READY
    assert "PROVISION_INVESTMENT_SECURITIES" not in {
        mapping["role"] for mapping in blank_candidate["mappings"]
    }

    dash = _page(net=("80", "65"))
    dash["sections"][0]["tables"][0]["rows"][3]["values_exact"] = ["-", "—"]
    dash_candidate = _evaluate(dash)
    provision = next(
        mapping
        for mapping in dash_candidate["mappings"]
        if mapping["role"] == "PROVISION_INVESTMENT_SECURITIES"
    )
    assert [(cell["coefficient"], cell["state"]) for cell in provision["values"]] == [
        (0, "DASH_ZERO"),
        (0, "DASH_ZERO"),
    ]


def test_investment_securities_source_vocabulary_variants_map_by_declared_roles() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [
        _row(
            "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán đầu tư", ["70", "60"], kind="TOTAL"
        ),
        _row("Lãi từ mua bán chứng khoán đầu tư", ["100", "80"]),
        _row("Lỗ về mua bán chứng khoán đầu tư", ["(20)", "(15)"]),
        _row(
            "(Trích lập)/Hoàn nhập dự phòng chứng khoán đầu tư (Thuyết minh 8.1)",
            ["(10)", "(5)"],
        ),
    ]
    page["sections"][0]["title_exact"] = (
        "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán đầu tư"
    )
    page["sections"][0]["tables"][0]["title_exact"] = (
        "Lãi/(Lỗ) thuần từ hoạt động mua bán chứng khoán đầu tư"
    )
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
        "PROVISION_INVESTMENT_SECURITIES",
    }


def test_investment_securities_primary_root_recovery_ignores_balance_note_provision() -> None:
    primary_version = "gfpstorev1:json:" + "d" * 64
    note_version = "gfpstorev1:json:" + "e" * 64
    primary = _page(provision=False, net=("42", "7"))
    primary["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    primary_section = primary["sections"][0]
    primary_section["content_kind"] = "PRIMARY_STATEMENT"
    primary_section["statement_type"] = "INCOME_STATEMENT"
    primary_section["tables"][0]["rows"] = [
        _row(ROOT_LABEL, ["42", "7"], kind="ITEM")
    ]

    note = _page(provision=False)
    note_table = note["sections"][0]["tables"][0]
    note_table["title_exact"] = "Chứng khoán đầu tư"
    note_table["rows"] = [
        _row("Dự phòng rủi ro chứng khoán đầu tư", ["(2)", "(3)"])
    ]
    inventory = [
        {
            "classification": {
                "ambiguous_rows": [],
                "family_root_row_ordinals": [1],
                "role_hits": [],
                "typed_control_disposition": "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
            },
            "page_json_version_id": primary_version,
            "physical_page": 2,
            "section_id": "s1",
            "table_id": "t1",
        },
        {
            "classification": {
                "ambiguous_rows": [],
                "family_root_row_ordinals": [],
                "role_hits": [
                    {"role": "PROVISION_INVESTMENT_SECURITIES", "row_ordinal": 1}
                ],
                "typed_control_disposition": None,
            },
            "page_json_version_id": note_version,
            "physical_page": 20,
            "section_id": "s1",
            "table_id": "t1",
        },
    ]
    cluster = {
        "declared_money_table_inventory": inventory,
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "reasons": [],
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "status": NOT_OBSERVED,
    }
    selected_page_axis = [
        {
            "document_ordinal": 1,
            "page_json_version_id": primary_version,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
        {
            "document_ordinal": 1,
            "page_json_version_id": note_version,
            "physical_page": 20,
            "selected_page_ordinal": 20,
        },
    ]
    pages = {primary_version: primary, note_version: note}

    recovered = _primary_query_recovery_v1(
        cluster=cluster,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=_compiled(),
    )
    assert recovered is not None
    assert len(recovered[0]) == 1
    assert recovered[1]["vector"] == [42, 7]


def test_investment_securities_primary_root_recovery_keeps_exact_direct_note_components() -> None:
    primary_version = "gfpstorev1:json:" + "d" * 64
    note_version = "gfpstorev1:json:" + "e" * 64
    primary = _page(provision=False, net=("42", "7"))
    primary["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    primary_section = primary["sections"][0]
    primary_section["content_kind"] = "PRIMARY_STATEMENT"
    primary_section["statement_type"] = "INCOME_STATEMENT"
    primary_section["tables"][0]["rows"] = [_row(ROOT_LABEL, ["42", "7"], kind="ITEM")]

    note = _page(provision=False)
    note_table = note["sections"][0]["tables"][0]
    note_table["rows"] = [
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["50", "10"]),
        _row("Chi phí về mua bán chứng khoán đầu tư", ["(8)", "(3)"]),
    ]
    inventory = [
        {
            "classification": {
                "ambiguous_rows": [],
                "family_root_row_ordinals": [1],
                "role_hits": [],
                "typed_control_disposition": "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
            },
            "page_json_version_id": primary_version,
            "physical_page": 2,
            "section_id": "s1",
            "table_id": "t1",
        },
        {
            "classification": {
                "ambiguous_rows": [],
                "family_root_row_ordinals": [],
                "role_hits": [
                    {"role": "INCOME_INVESTMENT_SECURITIES", "row_ordinal": 1},
                    {"role": "EXPENSE_INVESTMENT_SECURITIES", "row_ordinal": 2},
                ],
                "typed_control_disposition": None,
            },
            "page_json_version_id": note_version,
            "physical_page": 20,
            "section_id": "s1",
            "table_id": "t1",
        },
    ]
    cluster = {
        "declared_money_table_inventory": inventory,
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "reasons": [],
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "status": NOT_OBSERVED,
    }
    selected_page_axis = [
        {
            "document_ordinal": 1,
            "page_json_version_id": primary_version,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
        {
            "document_ordinal": 1,
            "page_json_version_id": note_version,
            "physical_page": 20,
            "selected_page_ordinal": 20,
        },
    ]
    pages = {primary_version: primary, note_version: note}

    recovered = _primary_query_recovery_v1(
        cluster=cluster,
        selected_page_axis=selected_page_axis,
        pages=pages,
        compiled_specs=_compiled(),
    )
    assert recovered is not None
    regions, primary_receipt = recovered
    assert [region["page_json_version_id"] for region in regions] == [
        primary_version,
        note_version,
    ]
    assert primary_receipt["direct_note_region_axis"] == [
        {
            "component_roles": [
                "EXPENSE_INVESTMENT_SECURITIES",
                "INCOME_INVESTMENT_SECURITIES",
            ],
            "page_json_version_id": note_version,
            "physical_page": 20,
            "section_id": "s1",
            "selected_page_ordinal": 20,
            "table_id": "t1",
        }
    ]
    candidate = evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_investment_securities_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
    }

    note_table["rows"][1]["values_exact"][0] = "(11)"
    rejected = evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_investment_securities_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert rejected["status"] == UNRESOLVED
    assert rejected["mappings"] == []


def test_investment_securities_combined_table_consumes_only_explicit_root_subtree() -> None:
    trading_root = "Lãi/(lỗ) thuần từ mua bán chứng khoán kinh doanh"
    page = _page()
    page["sections"][0]["title_exact"] = (
        "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư"
    )
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = None
    table["rows"] = [
        _row(ROOT_LABEL, [None, None], kind="GROUP"),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"], parent=ROOT_LABEL),
        _row("Chi về mua bán chứng khoán đầu tư", ["(20)", "(15)"], parent=ROOT_LABEL),
        _row(
            "(Trích lập)/Hoàn nhập dự phòng rủi ro chứng khoán đầu tư",
            ["(10)", "(5)"],
            parent=ROOT_LABEL,
        ),
        _row(None, ["70", "60"], kind="SUBTOTAL", parent=ROOT_LABEL),
        _row(trading_root, [None, None], kind="GROUP", parent=trading_root),
        _row(
            "Thu nhập từ mua bán chứng khoán kinh doanh",
            ["40", "30"],
            parent=trading_root,
        ),
        _row(
            "Chi phí về mua bán chứng khoán kinh doanh",
            ["(10)", "(5)"],
            parent=trading_root,
        ),
        _row(None, ["30", "25"], kind="SUBTOTAL", parent=trading_root),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 4
    assert all(
        "chứng khoán kinh doanh" not in str(source_ref.get("label_exact", "")).lower()
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    )


def test_investment_securities_foreign_dimension_root_row_is_not_observed() -> None:
    page = _page()
    page["sections"][0]["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    table["rows"] = [
        _row(ROOT_LABEL, ["70", "60"]),
        _row("Lãi thuần từ hoạt động dịch vụ", ["20", "15"]),
    ]
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_investment_securities_unmapped_direct_child_fails_closed() -> None:
    page = _page(net=("71", "61"))
    page["sections"][0]["tables"][0]["rows"].append(
        _row("Khoản chứng khoán đầu tư chưa khai báo", ["1", "1"])
    )
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_investment_securities_duplicate_population_and_axis_conflicts_fail_closed() -> None:
    duplicate = _page()
    duplicate["sections"][0]["tables"].append(copy.deepcopy(duplicate["sections"][0]["tables"][0]))
    duplicate_candidate = _evaluate(duplicate)
    assert duplicate_candidate["status"] == UNRESOLVED
    assert duplicate_candidate["mappings"] == []

    optional_drift = _page(net=("80", "65"))
    optional_drift["sections"][0]["tables"][0]["rows"][3]["values_exact"] = ["-", "-"]
    second = copy.deepcopy(optional_drift["sections"][0]["tables"][0])
    second["rows"] = second["rows"][:3]
    optional_drift["sections"][0]["tables"].append(second)
    optional_drift_candidate = _evaluate(optional_drift)
    assert optional_drift_candidate["status"] == UNRESOLVED
    assert optional_drift_candidate["mappings"] == []

    unit = _page()
    unit["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    unit_candidate = _evaluate(unit)
    assert unit_candidate["status"] == UNRESOLVED
    assert unit_candidate["mappings"] == []

    period = _page()
    period["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Năm 2025",
        "Năm trước",
        "Triệu đồng",
    ]
    period_candidate = _evaluate(period)
    assert period_candidate["status"] == UNRESOLVED
    assert period_candidate["mappings"] == []


def test_investment_securities_candidate_replay_rejects_coherent_receipt_drift() -> None:
    candidate, regions, page_json_by_version, receipt = _candidate_and_replay_inputs(_page())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["equations"][0]["status"] = "MISMATCH"
    material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
        match="investment-securities candidate replay drifted",
    ):
        validate_gemini_json_investment_securities_activity_family_candidate_replay_v1(
            forged,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def _source_repair_fixture(page: dict[str, Any]) -> dict[str, Any]:
    table = page["sections"][0]["tables"][0]
    row = table["rows"][3]
    return {
        "family_id": "INVESTMENT_SECURITIES_ACTIVITY",
        "format_version": (
            "GEMINI_JSON_INVESTMENT_SECURITIES_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
        ),
        "policy": (
            "TRANSCRIBE_ONLY_PDF_VISIBLE_MONEY_TOKENS_NO_EQUATION_BACKSOLVE_"
            "NO_BLANK_TO_ZERO_NO_PROVIDER"
        ),
        "repairs": [
            {
                "base_page_json_sha256": canonical_json_sha256_v1(page),
                "base_table_sha256": canonical_json_sha256_v1(table),
                "cell_repairs": [
                    {
                        "column_ordinal": 1,
                        "original_value_exact": None,
                        "replacement_value_exact": "-",
                        "row_hierarchy_path_exact": copy.deepcopy(
                            row["hierarchy_path_exact"]
                        ),
                        "row_id": "r4",
                        "row_kind": row["row_kind"],
                        "row_label_exact": row["label_exact"],
                        "visual_observation": "PDF_RENDER_VISIBLE_MONEY_TOKEN",
                    }
                ],
                "column_repairs": [],
                "page_image": {
                    "height": 100,
                    "media_type": "image/png",
                    "render_dpi": 300,
                    "sha256": "d" * 64,
                    "size_bytes": 100,
                    "width": 100,
                },
                "page_json_version_id": VERSION_ID,
                "physical_page": 1,
                "reviewed_utc_date": "2026-09-04",
                "section_id": "s1",
                "source_logical_name": "fixture.pdf",
                "source_sha256": SOURCE_SHA256,
                "source_size_bytes": 1,
                "table_id": "t1",
            }
        ],
    }


def test_investment_securities_source_repair_is_hash_bound_and_never_infers_blank() -> None:
    page = _page(net=("80", "65"))
    page["sections"][0]["tables"][0]["rows"][3]["values_exact"] = [None, "(5)"]
    source_repair = _source_repair_fixture(page)
    compiled = compile_gemini_json_investment_securities_activity_family_specs_v1(
        _json("tm-investment-securities-activity-topology-v1.json"),
        _json("tm-investment-securities-activity-evaluation-v1.json"),
        _json("tm-investment-securities-activity-schema-binding-v1.json"),
        source_repair,
    )
    record = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    projected, receipts = _apply_source_repairs_v1(
        pages={VERSION_ID: page},
        regions=cluster["component_regions"],
        compiled_specs=compiled,
    )
    assert projected[VERSION_ID]["sections"][0]["tables"][0]["rows"][3][
        "values_exact"
    ] == ["-", "(5)"]
    assert len(receipts) == 1

    tampered = copy.deepcopy(page)
    tampered["sections"][0]["tables"][0]["rows"][0]["label_exact"] += " drift"
    with pytest.raises(
        GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
        match="source-repair base content drifted",
    ):
        _apply_source_repairs_v1(
            pages={VERSION_ID: tampered},
            regions=cluster["component_regions"],
            compiled_specs=compiled,
        )


def test_investment_securities_registered_source_repair_axis_is_exact() -> None:
    overlay = _compiled()["investment_securities_activity_source_repair_overlay"]
    assert len(overlay["repairs"]) == 7
    assert sum(len(repair["cell_repairs"]) for repair in overlay["repairs"]) == 8
    assert all(repair["column_repairs"] == [] for repair in overlay["repairs"])
    assert {
        cell["replacement_value_exact"]
        for repair in overlay["repairs"]
        for cell in repair["cell_repairs"]
    } == {"-"}
    assert {
        (
            repair["source_logical_name"],
            repair["physical_page"],
            tuple(
                (cell["row_id"], cell["column_ordinal"])
                for cell in repair["cell_repairs"]
            ),
        )
        for repair in overlay["repairs"]
        if "/SGB/" in repair["source_logical_name"]
    } == {
        (
            "vietstock_bctc/SGB/2025/"
            "BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf",
            7,
            (("r9", 5),),
        ),
        (
            "vietstock_bctc/SGB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf",
            6,
            (("r9", 4),),
        ),
    }


def test_investment_securities_source_repair_compiler_rejects_malformed_contract() -> None:
    page = _page()
    malformed = _source_repair_fixture(page)
    malformed["repairs"][0]["reviewed_utc_date"] = "2026-09-03"
    with pytest.raises(
        GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
        match="source-repair binding is invalid",
    ):
        compile_gemini_json_investment_securities_activity_family_specs_v1(
            _json("tm-investment-securities-activity-topology-v1.json"),
            _json("tm-investment-securities-activity-evaluation-v1.json"),
            _json("tm-investment-securities-activity-schema-binding-v1.json"),
            malformed,
        )


def test_investment_securities_duration_scope_is_explicit_and_malformed_policy_fails() -> None:
    assert (
        _compiled()["duration_header_path_scope_policy"]
        == "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
    )
    evaluation = _json("tm-investment-securities-activity-evaluation-v1.json")
    evaluation["duration_header_path_scope_policy"] = "WHOLE_HEADER_PATH"
    with pytest.raises(
        GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
        match="declarative adapter boundary is invalid",
    ):
        compile_gemini_json_investment_securities_activity_family_specs_v1(
            _json("tm-investment-securities-activity-topology-v1.json"),
            evaluation,
            _json("tm-investment-securities-activity-schema-binding-v1.json"),
        )
