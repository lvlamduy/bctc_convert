from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonOtherLongTermInvestmentsFamilyV1Error,
    build_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
    build_gemini_json_other_long_term_investments_region_query_receipt_v1,
    coalesce_gemini_json_other_long_term_investments_document_v1,
    compile_gemini_json_other_long_term_investments_family_specs_v1,
    evaluate_gemini_json_other_long_term_investments_family_cluster_v1,
    validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
    validate_gemini_json_other_long_term_investments_family_candidate_replay_v1,
    validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1,
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


def test_blank_provision_is_zero_only_after_net_equation_closes() -> None:
    page = _base_page()
    summary = page["sections"][0]["tables"][0]["rows"]
    summary[2]["values_exact"] = [None, None]
    summary[3]["values_exact"] = ["100", "80"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    provision = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "PROVISION")
    assert [cell["coefficient"] for cell in provision["values"]] == [0, 0]
    assert all(cell["state"].startswith("INFERRED_") for cell in provision["values"])


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
