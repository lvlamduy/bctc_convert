from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonOtherLongTermInvestmentsFamilyV1Error,
    _apply_authenticated_source_repair_artifact_v1,
    _global_records,
    build_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
    build_gemini_json_other_long_term_investments_region_query_receipt_v1,
    coalesce_gemini_json_other_long_term_investments_document_v1,
    compile_gemini_json_other_long_term_investments_family_specs_v1,
    evaluate_gemini_json_other_long_term_investments_family_cluster_v1,
    validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
    validate_gemini_json_other_long_term_investments_family_candidate_replay_v1,
    validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "b" * 64
SOURCE_SHA256 = "c" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_other_long_term_investments_family_specs_v1(
        _json("tm-other-long-term-investments-topology-v1.json"),
        _json("tm-other-long-term-investments-evaluation-v1.json"),
        _json("tm-other-long-term-investments-schema-binding-v1.json"),
    )


def _columns() -> list[dict]:
    return [
        {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    hierarchy: list[str | None] | None = None,
) -> dict:
    return {
        "hierarchy_path_exact": [label] if hierarchy is None else hierarchy,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(rows: list[dict], *, title: str | None = None, unit: str = "Triệu đồng") -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": unit,
    }


def _single_period_summary_table(period: str, other: str, provision: str, net: str) -> dict:
    table = _table(
        [
            _row("Đầu tư dài hạn khác", [other]),
            _row(None, [other], kind="SUBTOTAL", hierarchy=[None]),
            _row("Dự phòng giảm giá đầu tư dài hạn", [provision]),
            _row(None, [net], kind="TOTAL", hierarchy=[None]),
        ]
    )
    table["columns"] = [{"header_path_exact": [period, "Triệu đồng"], "value_kind": "MONEY"}]
    return table


def _two_period_reporting_currency_summary_table() -> dict:
    table = _table(
        [
            _row("Đầu tư dài hạn khác", ["2.500", "100", "2.000", "80"]),
            _row(None, ["2.500", "100", "2.000", "80"], kind="SUBTOTAL", hierarchy=[None]),
            _row(
                "Dự phòng giảm giá đầu tư dài hạn",
                ["(250)", "(10)", "(125)", "(5)"],
            ),
            _row(None, ["2.250", "90", "1.875", "75"], kind="TOTAL", hierarchy=[None]),
        ],
        unit="Triệu VND",
    )
    table["columns"] = [
        {
            "header_path_exact": ["31/12/2025", "USD", "Giá gốc"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2025", "Triệu", "VND", "Giá gốc quy đổi"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2024", "USD", "Giá gốc"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2024", "Triệu", "VND", "Giá gốc quy đổi"],
            "value_kind": "MONEY",
        },
    ]
    return table


def _section(title: str, *tables: dict, narratives: list[str] | None = None) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [] if narratives is None else narratives,
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _summary_rows(*, provision_label: str = "Dự phòng giảm giá") -> list[dict]:
    return [
        _row("Đầu tư dài hạn khác", ["100", "80"]),
        _row(None, ["100", "80"], kind="SUBTOTAL", hierarchy=[None]),
        _row(provision_label, ["(10)", "(5)"]),
        _row(None, ["90", "75"], kind="TOTAL", hierarchy=[None]),
    ]


def _detail_rows() -> list[dict]:
    return [
        _row("Đầu tư vào tổ chức kinh tế, dự án dài hạn", ["60", "50"]),
        _row("Đầu tư vào các Quỹ đầu tư", ["40", "30"]),
        _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
    ]


def _base_page(*, provision_label: str = "Dự phòng giảm giá") -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _table(_summary_rows(provision_label=provision_label)),
            ),
            _section("Đầu tư dài hạn khác", _table(_detail_rows())),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + f"{ordinal:064x}",
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict) -> tuple[dict, dict, dict]:
    compiled = _compiled()
    record = _record(page)
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_other_long_term_investments_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return compiled, cluster, candidate


def test_global_records_keeps_two_numeric_lanes_but_one_exact_source_identity() -> None:
    source_ref = {
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "table_id": "t1",
        },
        "row_id": "r1",
    }
    local_record = {
        "cells": [
            {"coefficient": 11, "source_text": "11", "state": "RAW_SIGNED_INTEGER"},
            {"coefficient": 7, "source_text": "7", "state": "RAW_SIGNED_INTEGER"},
        ],
        "lane_keys": [("DATE", "2025-12-31"), ("DATE", "2024-12-31")],
        "role": "OTHER_LONG_TERM",
        "source_refs": [source_ref],
        "state": "SOURCE_OBSERVED_ROLE_ROW",
        "valuation_basis": "GENERIC_AMOUNT",
    }

    records, partial, reasons, omissions = _global_records([local_record], proven_roles=set())

    assert partial == []
    assert reasons == []
    assert omissions == []
    assert [cell["coefficient"] for cell in records["OTHER_LONG_TERM"]["cells"]] == [11, 7]
    assert records["OTHER_LONG_TERM"]["state"] == "SOURCE_OBSERVED_ROLE_ROW"
    assert records["OTHER_LONG_TERM"]["source_refs"] == [source_ref]


def test_summary_detail_and_net_close_without_mapping_structural_root_twice() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_base_page())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert set(by_role) == {
        "INVESTMENT_FUND",
        "NET_TOTAL",
        "ORGANIZATION_PROJECT",
        "OTHER_LONG_TERM",
        "PROVISION",
    }
    assert [cell["coefficient"] for cell in by_role["OTHER_LONG_TERM"]["values"]] == [
        100,
        80,
    ]
    assert [cell["coefficient"] for cell in by_role["NET_TOTAL"]["values"]] == [90, 75]
    assert all(
        equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"]
    )


def test_gross_subtotal_does_not_make_provision_inclusive_net_ambiguous() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_base_page())
    root = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "NET_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [90, 75]
    assert root["source_refs"][0]["row_id"] == "r4"


def test_short_provision_alias_is_only_accepted_with_same_table_other_role() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_base_page())
    assert any(mapping["role"] == "PROVISION" for mapping in candidate["mappings"])

    page = {
        **_base_page(),
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _table(
                    [
                        _row("Dự phòng giảm giá", ["(10)", "(5)"]),
                        _row(None, ["(10)", "(5)"], kind="TOTAL"),
                    ]
                ),
            )
        ],
    }
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_accounting_less_prefix_is_normalized_locally() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(
        _base_page(provision_label="Trừ: Dự phòng giảm giá đầu tư dài hạn")
    )
    provision = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "PROVISION")
    assert [cell["coefficient"] for cell in provision["values"]] == [-10, -5]


def test_explicit_role_row_outranks_context_inferred_mixed_detail_total() -> None:
    page = _base_page()
    page["sections"].append(
        _section(
            "Danh sách các công ty liên kết, liên doanh quan trọng",
            _table(
                [
                    _row("Ngân hàng liên doanh A", ["30", "25"]),
                    _row("Công ty liên kết B", ["40", "35"]),
                    _row(None, ["70", "60"], kind="TOTAL"),
                ]
            ),
        )
    )
    page["sections"][0]["tables"][0]["rows"].insert(
        0, _row("Đầu tư vào công ty liên doanh", ["20", "15"])
    )
    # Update the visible summary controls after adding the direct child.
    page["sections"][0]["tables"][0]["rows"][2]["values_exact"] = ["120", "95"]
    page["sections"][0]["tables"][0]["rows"][4]["values_exact"] = ["110", "90"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    joint = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "JOINT_VENTURE")
    assert [cell["coefficient"] for cell in joint["values"]] == [20, 15]


def test_all_blank_provision_role_is_omitted_instead_of_inferred_as_zero() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]["rows"]
    summary[2]["values_exact"] = [None, None]
    summary[3]["values_exact"] = ["100", "80"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert "PROVISION" not in by_role
    assert [cell["coefficient"] for cell in by_role["NET_TOTAL"]["values"]] == [100, 80]
    structural_equations = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"]
        == "STRUCTURALLY_BOUND_VISIBLE_FAMILY_TOTAL_WITH_INCOMPLETE_BLANK_SOURCE_COMPONENTS"
    ]
    assert len(structural_equations) == 1
    assert structural_equations[0]["status"] == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
    omissions = candidate["closure_receipt"]["optional_conditional_omissions"]
    assert [(item["role"], item["reason"]) for item in omissions] == [
        ("PROVISION", "ALL_LANES_BLANK_SOURCE_ROLE_OMITTED")
    ]
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_partial_blank_provision_preserves_visible_dash_and_null_blank_lane() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]["rows"]
    summary[2]["values_exact"] = ["-", None]
    summary[3]["values_exact"] = ["100", "80"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    provision = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "PROVISION")
    assert [
        (cell["coefficient"], cell["source_text"], cell["state"]) for cell in provision["values"]
    ] == [
        (0, "-", "DASH_ZERO"),
        (None, None, "BLANK_SOURCE_CELL"),
    ]
    assert provision["state"] == "PARTIAL_SOURCE_OBSERVATION"
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_partial_blank_lanes_keep_visible_total_without_claiming_full_equation() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]["rows"]
    summary[0]["values_exact"] = ["100", None]
    summary[1]["values_exact"] = ["100", None]
    summary[2]["values_exact"] = ["-", None]
    summary[3]["values_exact"] = ["100", None]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [
        (cell["coefficient"], cell["source_text"], cell["state"])
        for cell in by_role["NET_TOTAL"]["values"]
    ] == [
        (100, "100", "RAW_SIGNED_INTEGER"),
        (None, None, "BLANK_SOURCE_CELL"),
    ]
    assert by_role["NET_TOTAL"]["state"] == "PARTIAL_SOURCE_OBSERVATION"
    matching = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "SOURCE_ROW"
        and equation["equation_kind"].startswith("OBSERVED_LANES_EXACT_REMAINDER_BLANK_")
    ]
    assert matching
    assert all(
        equation["status"] == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
        and equation["lane_statuses"] == ["EXACT", "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"]
        for equation in matching
    )
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_partial_blank_total_is_not_corroborated_when_observed_lane_mismatches() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]["rows"]
    summary[0]["values_exact"] = ["100", None]
    summary[1]["values_exact"] = ["100", None]
    summary[2]["values_exact"] = ["-", None]
    summary[3]["values_exact"] = ["99", None]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert "NET_TOTAL" not in {mapping["role"] for mapping in candidate["mappings"]}
    assert not any(
        equation["equation_kind"].startswith("OBSERVED_LANES_EXACT_REMAINDER_BLANK_")
        and any(source_ref["row_id"] == "r4" for source_ref in equation["result_source_refs"])
        for equation in candidate["closure_receipt"]["equations"]
    )


def test_observed_dash_and_printed_zero_remain_numeric_zero() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]["rows"]
    summary[2]["values_exact"] = ["-", "0"]
    summary[3]["values_exact"] = ["100", "80"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    provision = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "PROVISION")
    assert [
        (cell["coefficient"], cell["source_text"], cell["state"]) for cell in provision["values"]
    ] == [
        (0, "-", "DASH_ZERO"),
        (0, "0", "RAW_SIGNED_INTEGER"),
    ]
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_authenticated_dash_repair_is_clone_only_and_exactly_bound() -> None:
    page = _base_page()
    for table in [
        section_table for section in page["sections"] for section_table in section["tables"]
    ]:
        for ordinal, row in enumerate(table["rows"], start=1):
            row["row_id"] = f"r{ordinal}"
    target = page["sections"][0]["tables"][0]["rows"][2]
    target["values_exact"][1] = None
    compiled = _compiled()
    record = _record(page)
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    repair = {
        "base_page_json_sha256": canonical_json_sha256_v1(page),
        "base_table_sha256": canonical_json_sha256_v1(page["sections"][0]["tables"][0]),
        "cell_repairs": [
            {
                "column_ordinal": 2,
                "original_value_exact": None,
                "replacement_value_exact": "-",
                "row_hierarchy_path_exact": target["hierarchy_path_exact"],
                "row_id": target["row_id"],
                "row_kind": target["row_kind"],
                "row_label_exact": target["label_exact"],
                "visual_observation": "PDF_RENDER_VISIBLE_DASH",
            }
        ],
        "page_image": {
            "height": 200,
            "media_type": "image/png",
            "render_dpi": 300,
            "sha256": "d" * 64,
            "size_bytes": 123,
            "width": 100,
        },
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "reason": "PDF_RENDER_VISIBLE_DASH_OMITTED_FROM_SELECTED_JSON",
        "repair_id": "gjfoltisrv1:repair:" + "e" * 64,
        "section_id": "s1",
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": "t1",
    }
    compiled["source_repair_overlay"] = {
        "overlay_id": "gjfoltisrv1:overlay:" + "f" * 64,
        "repairs": [repair],
    }
    compiled["source_repair_artifact_ref"] = {
        "artifact_format_version": "fixture",
        "overlay_id": compiled["source_repair_overlay"]["overlay_id"],
        "path": "fixture.json",
        "sha256": "a" * 64,
        "size_bytes": 1,
    }
    effective, receipts = _apply_authenticated_source_repair_artifact_v1(
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        regions=cluster["component_regions"],
    )
    assert target["values_exact"][1] is None
    assert (
        effective[record["page_json_version_id"]]["sections"][0]["tables"][0]["rows"][2][
            "values_exact"
        ][1]
        == "-"
    )
    assert [item["repair_id"] for item in receipts] == [repair["repair_id"]]

    drifted = copy.deepcopy(page)
    drifted["sections"][0]["tables"][0]["rows"][2]["values_exact"][1] = "0"
    with pytest.raises(GeminiJsonOtherLongTermInvestmentsFamilyV1Error, match="base page drifted"):
        _apply_authenticated_source_repair_artifact_v1(
            page_json_by_version={record["page_json_version_id"]: drifted},
            compiled_specs=compiled,
            regions=cluster["component_regions"],
        )


def test_source_repair_artifact_ref_rejects_byte_hash_tamper() -> None:
    evaluation = _json("tm-other-long-term-investments-evaluation-v1.json")
    evaluation["authenticated_source_repair_artifact_ref"]["sha256"] = "0" * 64
    with pytest.raises(
        GeminiJsonOtherLongTermInvestmentsFamilyV1Error,
        match="artifact bytes drifted",
    ):
        compile_gemini_json_other_long_term_investments_family_specs_v1(
            _json("tm-other-long-term-investments-topology-v1.json"),
            evaluation,
            _json("tm-other-long-term-investments-schema-binding-v1.json"),
        )


def test_registered_source_repair_axis_is_dash_only_and_exhaustive() -> None:
    overlay = _compiled()["source_repair_overlay"]
    assert overlay["repair_count"] == 14
    cells = [cell for repair in overlay["repairs"] for cell in repair["cell_repairs"]]
    assert len(cells) == 34
    assert {
        (
            cell["original_value_exact"],
            cell["replacement_value_exact"],
            cell["visual_observation"],
        )
        for cell in cells
    } == {(None, "-", "PDF_RENDER_VISIBLE_DASH")}


def test_owner_to_component_reset_requires_new_explicit_owner() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]
    page["sections"] = [
        _section("Góp vốn, đầu tư dài hạn"),
        _section("Tài sản cố định hữu hình"),
        _section("Chi tiết", summary),
    ]
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_multiple_complete_reset_fenced_owners_are_ambiguous() -> None:
    page = _base_page()
    page["sections"].extend(
        [
            _section("Tài sản cố định hữu hình"),
            _section("Góp vốn, đầu tư dài hạn", _table(_summary_rows())),
        ]
    )
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["reasons"] == ["MULTIPLE_COMPLETE_OWNER_CLUSTERS"]


def test_conflicting_period_dates_fail_closed_without_mappings() -> None:
    page = _base_page()
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "31/12/2025",
        "30/06/2025",
        "Triệu đồng",
    ]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_repeated_one_period_tables_bind_ordered_narrative_headings() -> None:
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _single_period_summary_table("Giá trị ghi sổ", "100", "(10)", "90"),
                _single_period_summary_table("Giá trị ghi sổ", "80", "(5)", "75"),
                narratives=["Tại ngày 31/12/2025", "Tại ngày 31/12/2024"],
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    other = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_LONG_TERM"
    )
    assert [cell["coefficient"] for cell in other["values"]] == [100, 80]


def test_split_metric_headers_select_reporting_currency_without_usd_unit_conflict() -> None:
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _two_period_reporting_currency_summary_table(),
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    other = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_LONG_TERM"
    )
    assert [cell["coefficient"] for cell in other["values"]] == [100, 80]


def test_multi_metric_date_and_semantic_period_conflict_fails_closed() -> None:
    table = _two_period_reporting_currency_summary_table()
    table["columns"][1]["header_path_exact"].append("Kỳ trước")
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [_section("Góp vốn, đầu tư dài hạn", table)],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_titleless_cross_section_period_continuation_inherits_exact_context_role() -> None:
    current = _table(
        [
            _row("Công ty A", ["100"]),
            _row(None, ["100"], kind="TOTAL", hierarchy=[None]),
        ],
        title="Đầu tư dài hạn khác",
    )
    current["columns"] = [
        {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"}
    ]
    comparative = _table(
        [
            _row("Công ty A", ["80"]),
            _row(None, ["80"], kind="TOTAL", hierarchy=[None]),
        ]
    )
    comparative["columns"] = [
        {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"}
    ]
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section("Góp vốn, đầu tư dài hạn", current),
            _section(None, comparative),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert len(cluster["component_regions"]) == 2
    other = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "OTHER_LONG_TERM"
    )
    assert [cell["coefficient"] for cell in other["values"]] == [100, 80]


def test_period_only_sibling_title_continues_preceding_explicit_role() -> None:
    current = _table(
        [
            _row("Công ty Liên doanh hữu hạn A", ["100"]),
            _row(None, ["100"], kind="TOTAL", hierarchy=[None]),
        ],
        title="Đầu tư vào các công ty liên kết\nTại ngày 31 tháng 12 năm 2025",
    )
    current["columns"] = [
        {"header_path_exact": ["Giá trị ghi sổ", "Triệu đồng"], "value_kind": "MONEY"}
    ]
    comparative = _table(
        [
            _row("Công ty Liên doanh hữu hạn A", ["80"]),
            _row(None, ["80"], kind="TOTAL", hierarchy=[None]),
        ],
        title="Tại ngày 31 tháng 12 năm 2024",
    )
    comparative["columns"] = [
        {"header_path_exact": ["Giá trị ghi sổ", "Triệu đồng"], "value_kind": "MONEY"}
    ]
    page = {
        **_base_page(),
        "sections": [_section("Góp vốn, đầu tư dài hạn", current, comparative)],
    }
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert [region["component_roles"] for region in cluster["component_regions"]] == [
        ["ASSOCIATE"],
        ["ASSOCIATE"],
    ]
    associate = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "ASSOCIATE")
    assert [cell["coefficient"] for cell in associate["values"]] == [100, 80]


def test_conflicting_money_magnitudes_fail_closed_without_mappings() -> None:
    page = _base_page()
    page["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_typed_control_is_inventoried_but_not_selected_as_family_evidence() -> None:
    page = _base_page()
    page["sections"].append(
        _section(
            "Chi phí hoạt động",
            _table([_row("Đầu tư dài hạn khác", ["999", "998"])]),
        )
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    excluded = [
        item
        for item in cluster["declared_role_table_inventory"]
        if item["classification"]["typed_control_disposition"] is not None
    ]
    assert len(excluded) == 1
    assert excluded[0]["disposition"] == "EXCLUDED_TYPED_CONTROL"


def test_subsidiary_only_owner_table_is_source_only_not_unresolved_family() -> None:
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _table(
                    [
                        _row("Đầu tư vào công ty con", ["100", "80"]),
                        _row("Dự phòng đầu tư vào công ty con", ["(10)", "(5)"]),
                        _row(None, ["90", "75"], kind="TOTAL", hierarchy=[None]),
                    ]
                ),
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }

    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )

    assert cluster["status"] == NOT_OBSERVED
    assert cluster["reasons"] == []
    assert cluster["component_regions"] == []
    assert cluster["declared_role_table_inventory"][0]["disposition"] == ("EXCLUDED_TYPED_CONTROL")
    assert (
        cluster["declared_role_table_inventory"][0]["classification"]["typed_control_disposition"]
        == "SUBSIDIARY_ONLY_INVESTMENT_VIEW"
    )


def test_subsidiary_detail_does_not_exclude_visible_family_roles() -> None:
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _table(
                    [
                        _row("Đầu tư vào công ty con", ["100", "80"]),
                        _row("Đầu tư dài hạn khác", ["40", "30"]),
                        _row("Dự phòng giảm giá đầu tư dài hạn", ["(4)", "(3)"]),
                        _row(None, ["136", "107"], kind="TOTAL", hierarchy=[None]),
                    ]
                ),
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }

    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )

    assert cluster["status"] == READY


def test_alternate_other_alias_maps_without_using_subsidiary_inclusive_total() -> None:
    page = {
        **_base_page(),
        "sections": [
            _section(
                "Góp vốn, đầu tư dài hạn",
                _table(
                    [
                        _row("Đầu tư vào công ty con", ["100", "80"]),
                        _row("Các khoản góp vốn đầu tư dài hạn khác", ["30", "20"]),
                        _row("Dự phòng giảm giá đầu tư dài hạn", ["(5)", "(4)"]),
                        _row(None, ["125", "96"], kind="TOTAL", hierarchy=[None]),
                    ]
                ),
            )
        ],
    }
    _compiled_specs, _cluster, candidate = _evaluate(page)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["OTHER_LONG_TERM"]["values"]] == [30, 20]
    assert [cell["coefficient"] for cell in by_role["PROVISION"]["values"]] == [-5, -4]
    assert "NET_TOTAL" not in by_role


def test_owner_only_anonymous_investees_bind_to_controlled_other_total() -> None:
    page = {
        **_base_page(),
        "sections": [
            _section(
                "Đầu tư dài hạn khác",
                _table(
                    [
                        _row("Công ty A", ["60", "50"]),
                        _row("Công ty B", ["40", "30"]),
                        _row(None, ["100", "80"], kind="SUBTOTAL", hierarchy=[None]),
                        _row("Dự phòng giảm giá đầu tư dài hạn", ["(10)", "(5)"]),
                        _row(None, ["90", "75"], kind="TOTAL", hierarchy=[None]),
                    ]
                ),
            )
        ],
    }
    _compiled_specs, cluster, candidate = _evaluate(page)
    classification = cluster["declared_role_table_inventory"][0]["classification"]
    assert classification["table_context_role"] == "OTHER_LONG_TERM"
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["OTHER_LONG_TERM"]["values"]] == [100, 80]
    assert [cell["coefficient"] for cell in by_role["NET_TOTAL"]["values"]] == [90, 75]


def test_later_owner_heading_in_same_section_follows_earlier_reset_heading() -> None:
    page = {
        **_base_page(),
        "sections": [
            _section(
                None,
                _table(_summary_rows()),
                narratives=["10. Chứng khoán đầu tư", "11. Góp vốn, đầu tư dài hạn"],
            )
        ],
    }
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert cluster["owner_receipt"]["source_exact"] == "11. Góp vốn, đầu tư dài hạn"
    assert candidate["status"] == READY


def test_compound_other_row_uses_role_specific_cost_and_provision_lanes() -> None:
    table = _table(
        [
            _row("Các khoản đầu tư góp vốn dài hạn khác", ["100", "(10)", "80", "(5)"]),
            _row(None, ["90", None, "75", None], kind="TOTAL", hierarchy=[None]),
        ]
    )
    table["columns"] = [
        {"header_path_exact": ["31/12/2025", "Giá gốc"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2025", "Dự phòng"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Giá gốc"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Dự phòng"], "value_kind": "MONEY"},
    ]
    page = {**_base_page(), "sections": [_section("Góp vốn, đầu tư dài hạn", table)]}
    _compiled_specs, _cluster, candidate = _evaluate(page)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["OTHER_LONG_TERM"]["values"]] == [100, 80]
    assert [cell["coefficient"] for cell in by_role["PROVISION"]["values"]] == [-10, -5]
    assert "NET_TOTAL" not in by_role


def test_group_row_can_supply_the_exact_family_owner() -> None:
    page = {
        **_base_page(),
        "sections": [
            _section(
                None,
                _table(
                    [
                        _row("Đầu tư dài hạn khác", [None, None], kind="GROUP"),
                        _row("Đầu tư vào doanh nghiệp khác", ["100", "80"]),
                        _row(None, ["100", "80"], kind="TOTAL", hierarchy=[None]),
                    ]
                ),
            )
        ],
    }
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert cluster["owner_receipt"]["source_exact"] == "Đầu tư dài hạn khác"
    organization = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "ORGANIZATION_PROJECT"
    )
    assert [cell["coefficient"] for cell in organization["values"]] == [100, 80]


def test_exact_vnd_is_retained_as_the_mapping_unit() -> None:
    page = _base_page()
    for section in page["sections"]:
        for table in section["tables"]:
            table["unit_exact"] = "Đồng"
            for column in table["columns"]:
                column["header_path_exact"] = [column["header_path_exact"][0]]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}


def test_unitless_note_in_mixed_unit_document_requires_exact_owner_row_match() -> None:
    million_table = _table(
        [_row("Góp vốn, đầu tư dài hạn", ["90", "75"], kind="SUBTOTAL")],
        unit="Triệu đồng",
    )
    million_table["columns"] = [
        {"header_path_exact": ["Số dư cuối quý"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư đầu năm"], "value_kind": "MONEY"},
    ]
    million_page = {
        **_base_page(),
        "sections": [_section("Báo cáo tình hình tài chính", million_table)],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }
    vnd_table = _table([_row("Tổng tài sản", ["90000000", "75000000"])], unit="VND")
    vnd_page = {
        **_base_page(),
        "sections": [_section("Báo cáo tình hình tài chính", vnd_table)],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }
    note_table = _table(_summary_rows(), unit=None)
    for column in note_table["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0]]
    note_page = {
        **_base_page(),
        "sections": [_section("Góp vốn, đầu tư dài hạn", note_table)],
    }
    records = [_record(million_page, 1), _record(vnd_page, 2), _record(note_page, 3)]
    compiled = _compiled()
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_other_long_term_investments_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}
    unit_axis = candidate["closure_receipt"]["table_receipts"][0]["unit_axis"]
    assert unit_axis["source"] == "DOCUMENT_OWNER_ROW_EXACT_VALUE_PERIOD_UNIT_CORROBORATION"


def test_non_monetary_policy_table_does_not_compete_with_actual_note() -> None:
    policy = _table([], unit=None)
    policy["columns"] = [{"header_path_exact": ["Công thức dự phòng"], "value_kind": "TEXT"}]
    policy["rows"] = [_row(None, [None])]
    page = {
        **_base_page(),
        "sections": [
            _section("Đầu tư dài hạn khác", policy),
            _section("Góp vốn, đầu tư dài hạn", _table(_summary_rows())),
        ],
    }
    _compiled_specs, cluster, candidate = _evaluate(page)
    excluded = [
        item
        for item in cluster["declared_role_table_inventory"]
        if item["disposition"] == "EXCLUDED_TYPED_CONTROL"
    ]
    assert len(excluded) == 1
    assert (
        excluded[0]["classification"]["typed_control_disposition"]
        == "NON_MONETARY_POLICY_OR_FORMULA_VIEW"
    )
    assert candidate["status"] == READY


def test_titleless_income_tables_do_not_inherit_investment_role_context() -> None:
    family_page = {
        **_base_page(),
        "sections": [_section("Góp vốn, đầu tư dài hạn", _table(_summary_rows()))],
    }
    flow_page = {
        **_base_page(),
        "sections": [
            _section(
                None,
                _table(
                    [
                        _row(
                            "Phân chia lãi lỗ của các khoản đầu tư vào công ty liên doanh",
                            ["10", "5"],
                        ),
                        _row("Các khoản thu nhập khác", ["2", "1"]),
                        _row(None, ["12", "6"], kind="TOTAL", hierarchy=[None]),
                    ]
                ),
            )
        ],
    }
    cluster = coalesce_gemini_json_other_long_term_investments_document_v1(
        page_records=[_record(family_page, 1), _record(flow_page, 5)],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert [(item["physical_page"], item["table_id"]) for item in cluster["component_regions"]] == [
        (1, "t1")
    ]
    assert cluster["component_regions"]
    assert (
        cluster["declared_role_table_inventory"][0]["classification"]["typed_control_disposition"]
        is None
    )


def test_candidate_replay_rejects_source_receipt_drift() -> None:
    compiled, cluster, candidate = _evaluate(_base_page())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["classification"]["role_hits"][0]["role"] = (
        "ASSOCIATE"
    )
    with pytest.raises(
        GeminiJsonOtherLongTermInvestmentsFamilyV1Error,
        match="candidate does not replay exactly",
    ):
        validate_gemini_json_other_long_term_investments_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={_record(_base_page())["page_json_version_id"]: _base_page()},
            compiled_specs=compiled,
            query_receipt=(
                build_gemini_json_other_long_term_investments_region_query_receipt_v1(
                    cluster["component_regions"]
                )
            ),
        )


def test_indexed_evidence_and_trial_bindings_are_exact() -> None:
    compiled, cluster, candidate = _evaluate(_base_page())
    document = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    page = {
        **document,
        "page_json_version_id": _record(_base_page())["page_json_version_id"],
        "physical_page": 1,
        "selected_page_ordinal": 1,
    }
    evidence = build_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=[page],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        evidence, compiled_specs=compiled
    )
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "status": READY,
    }
    assert validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1(
        trials=[trial], indexed_query_evidence=evidence, compiled_specs=compiled
    ) == [trial]
    forged = copy.deepcopy(evidence)
    forged["accepted_clusters"][0]["component_regions"][0]["table_id"] = "t9"
    with pytest.raises(GeminiJsonOtherLongTermInvestmentsFamilyV1Error):
        validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
            forged, compiled_specs=compiled
        )
