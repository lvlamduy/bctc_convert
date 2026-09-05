from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_interest_income_family_v1 import (
    SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
    SOURCE_REPAIR_POLICY,
    GeminiJsonInterestIncomeFamilyV1Error,
    _apply_authenticated_source_repairs_v1,
    _compile_authenticated_source_repair_artifact_v1,
    _normalize_governed_duration_headers_v1,
    adapt_gemini_json_interest_income_indexed_query_evidence_v1,
    build_gemini_json_interest_income_region_query_receipt_v1,
    coalesce_gemini_json_interest_income_document_v1,
    compile_gemini_json_interest_income_family_specs_v1,
    evaluate_gemini_json_interest_income_family_cluster_v1,
    validate_gemini_json_interest_income_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "b" * 64
NOTE_VERSION = "gfpstorev1:json:" + "c" * 64
PRIMARY_VERSION = "gfpstorev1:json:" + "d" * 64
CROSS_FRAGMENT_SAME_ROLE_POLICY = (
    "EXACT_ADJACENT_PRIOR_TERMINAL_COLON_SAME_ROLE_PARENT_EQUALS_"
    "RECEIVER_LEADING_DETAIL_SUM_ALL_LANES"
)


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled(source_repair_spec: dict | None = None) -> dict:
    return compile_gemini_json_interest_income_family_specs_v1(
        _json("tm-interest-income-topology-v1.json"),
        _json("tm-interest-income-evaluation-v1.json"),
        _json("tm-interest-income-schema-binding-v1.json"),
        source_repair_spec,
    )


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


def _columns(
    current: list[str | None] | None = None,
    comparative: list[str | None] | None = None,
) -> list[dict]:
    return [
        {
            "header_path_exact": current or ["Từ ngày 01/01/2025 đến ngày 31/03/2025"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": comparative or ["Từ ngày 01/01/2024 đến ngày 31/03/2024"],
            "value_kind": "MONEY",
        },
    ]


def _table(
    rows: list[dict],
    *,
    columns: list[dict] | None = None,
    title: str | None = "Thu nhập lãi và các khoản thu nhập tương tự",
    unit: str | None = "Triệu đồng",
) -> dict:
    return {
        "columns": _columns() if columns is None else columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": unit,
    }


def _page(*tables: dict, status: str = "FINANCIAL_NOTE_CONTENT") -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": list(tables),
                "title_exact": "Thuyết minh",
            }
        ],
        "status": status,
    }


def _record(
    page: dict,
    *,
    version: str = NOTE_VERSION,
    physical_page: int = 2,
    selected_page_ordinal: int = 2,
) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": version,
        "physical_page": physical_page,
        "selected_page_ordinal": selected_page_ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _interest_rows(securities_comparative: str | None = "4") -> list[dict]:
    return [
        _row("Thu nhập lãi tiền gửi", ["10", "8"]),
        _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
        _row("Thu lãi từ đầu tư chứng khoán nợ", ["5", securities_comparative]),
        _row(None, ["35", "20"], kind="TOTAL"),
    ]


def _cluster_and_candidate(
    *,
    compiled: dict,
    pages: dict[str, dict],
    records: list[dict],
) -> tuple[dict, dict]:
    cluster = coalesce_gemini_json_interest_income_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_interest_income_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_interest_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return cluster, candidate


def _indexed_query_evidence(*, cluster: dict, records: list[dict], compiled: dict) -> dict:
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[
            {
                key: records[0][key]
                for key in (
                    "document_id",
                    "document_ordinal",
                    "source_logical_name",
                    "source_sha256",
                )
            }
        ],
        selected_page_axis=[
            {
                key: record[key]
                for key in (
                    "document_id",
                    "document_ordinal",
                    "page_json_version_id",
                    "physical_page",
                    "selected_page_ordinal",
                    "source_logical_name",
                    "source_sha256",
                )
            }
            for record in records
        ],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def _repair_artifact(page: dict, *, row_ordinal: int, column_ordinal: int) -> dict:
    table = page["sections"][0]["tables"][0]
    row = table["rows"][row_ordinal - 1]
    repair = {
        "base_page_json_sha256": canonical_json_sha256_v1(page),
        "base_table_sha256": canonical_json_sha256_v1(table),
        "cell_repairs": [
            {
                "column_ordinal": column_ordinal,
                "original_value_exact": row["values_exact"][column_ordinal - 1],
                "replacement_value_exact": "-",
                "row_hierarchy_path_exact": copy.deepcopy(row["hierarchy_path_exact"]),
                "row_id": f"r{row_ordinal}",
                "row_kind": row["row_kind"],
                "row_label_exact": row["label_exact"],
                "visual_observation": "PDF_RENDER_VISIBLE_DASH",
            }
        ],
        "page_image": {
            "height": 3000,
            "media_type": "image/png",
            "render_dpi": 300,
            "sha256": "e" * 64,
            "size_bytes": 1000,
            "width": 2000,
        },
        "page_json_version_id": NOTE_VERSION,
        "physical_page": 2,
        "reason": "PDF_RENDER_VISIBLE_DASH_SELECTED_JSON_TRANSCRIPTION_MISMATCH",
        "section_id": "s1",
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }
    repair["repair_id"] = "gjiifav1:repair:" + canonical_json_sha256_v1(repair)
    material = {
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "policy": SOURCE_REPAIR_POLICY,
        "repair_axis_sha256": canonical_json_sha256_v1([repair]),
        "repair_count": 1,
        "repairs": [repair],
    }
    return {
        **material,
        "overlay_id": "gjiifav1:overlay:" + canonical_json_sha256_v1(material),
    }


def test_registered_interest_income_repairs_compile_and_replay() -> None:
    compiled = _compiled()
    assert (
        compiled["cross_fragment_same_role_parent_equation_policy"]
        == CROSS_FRAGMENT_SAME_ROLE_POLICY
    )
    overlay = compiled["interest_income_source_repair_overlay"]
    assert overlay["repair_count"] == 30
    assert sum(len(item["cell_repairs"]) for item in overlay["repairs"]) == 64
    assert overlay["overlay_id"] == (
        "gjiifav1:overlay:21656d44f523f1271654aa18e59cede64babef968928529d6e4221b710a274bd"
    )

    broken = copy.deepcopy(overlay)
    broken["repairs"][0]["cell_repairs"][0]["original_value_exact"] = "forged"
    with pytest.raises(GeminiJsonInterestIncomeFamilyV1Error, match="artifact is invalid"):
        _compile_authenticated_source_repair_artifact_v1(broken)


def test_pdf_dash_repair_is_clone_only_and_candidate_replays() -> None:
    page = _page(_table(_interest_rows(securities_comparative=None)))
    overlay = _repair_artifact(page, row_ordinal=3, column_ordinal=2)
    compiled = _compiled(overlay)
    cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={NOTE_VERSION: page},
        records=[_record(page)],
    )
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "SECURITIES_INTEREST")
    assert [cell["coefficient"] for cell in mapping["values"]] == [5, 0]
    assert mapping["values"][1]["state"] == "DASH_ZERO"
    assert page["sections"][0]["tables"][0]["rows"][2]["values_exact"][1] is None
    adapter = candidate["closure_receipt"]["interest_income_adapter_receipt"]
    assert len(adapter["source_repair_receipts"]) == 1

    receipt = build_gemini_json_interest_income_region_query_receipt_v1(
        cluster["component_regions"]
    )
    validate_gemini_json_interest_income_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={NOTE_VERSION: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    forged = copy.deepcopy(candidate)
    forged["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(GeminiJsonInterestIncomeFamilyV1Error, match="candidate replay drifted"):
        validate_gemini_json_interest_income_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={NOTE_VERSION: page},
            compiled_specs=compiled,
            query_receipt=receipt,
        )


def test_unregistered_blank_lane_remains_unobserved_and_never_becomes_zero() -> None:
    page = _page(_table(_interest_rows(securities_comparative=None)))
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={NOTE_VERSION: page},
        records=[_record(page)],
    )
    mapping = next(item for item in candidate["mappings"] if item["role"] == "SECURITIES_INTEREST")
    assert mapping["values"][1] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert not any(item["role"] == "FAMILY_ROOT_TOTAL" for item in candidate["mappings"])


def test_credit_fee_disclosure_is_source_only_beneath_mapped_other_income() -> None:
    rows = [
        _row("Thu nhập lãi tiền gửi", ["10", "8"]),
        _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
        _row("Thu lãi từ đầu tư chứng khoán nợ", ["5", "4"]),
        _row("Thu khác từ hoạt động tín dụng", ["1", "2"]),
        _row(
            "Trong đó: Phí liên quan đến tín dụng",
            ["1", "2"],
            hierarchy=[
                "Thu khác từ hoạt động tín dụng",
                "Trong đó: Phí liên quan đến tín dụng",
            ],
        ),
        _row(None, ["36", "26"], kind="TOTAL"),
    ]
    page = _page(_table(rows))
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={NOTE_VERSION: page},
        records=[_record(page)],
    )

    assert candidate["status"] == READY
    assert sum(mapping["role"] == "OTHER_CREDIT_INCOME" for mapping in candidate["mappings"]) == 1
    assert not any(
        mapping["role"] == "CREDIT_RELATED_FEE_DETAIL_SOURCE_ONLY"
        for mapping in candidate["mappings"]
    )
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert any(
        row.get("declared_validation_role") == "CREDIT_RELATED_FEE_DETAIL_SOURCE_ONLY"
        for row in source_only
    )


def test_explicit_adjacent_continuation_keeps_visible_second_page_roles() -> None:
    first_table = _table(
        [
            _row("Thu nhập lãi tiền gửi", ["10", "8"]),
            _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
            _row(
                "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ",
                ["5", "4"],
                kind="GROUP",
            ),
        ]
    )
    first_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second_table = _table(
        [
            _row("Thu lãi từ chứng khoán đầu tư", ["5", "4"]),
            _row("Thu phí từ nghiệp vụ bảo lãnh", ["1", "1"]),
            _row("Thu nhập lãi cho thuê tài chính", ["-", "-"]),
            _row("Thu khác từ hoạt động tín dụng", ["2", "2"]),
            _row(None, ["38", "27"], kind="TOTAL"),
        ],
        columns=_columns([None], [None]),
        title=None,
        unit=None,
    )
    second_table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    first = _page(first_table)
    second = _page(second_table)
    compiled = _compiled()
    cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={NOTE_VERSION: first, PRIMARY_VERSION: second},
        records=[
            _record(first),
            _record(
                second,
                version=PRIMARY_VERSION,
                physical_page=3,
                selected_page_ordinal=3,
            ),
        ],
    )

    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CUSTOMER_LOAN_INTEREST",
        "DEPOSIT_INTEREST",
        "FAMILY_ROOT_TOTAL",
        "FINANCE_LEASE_INTEREST",
        "GUARANTEE_FEE_INTEREST",
        "OTHER_CREDIT_INCOME",
        "SECURITIES_INTEREST",
    }


def _same_role_cross_fragment_candidate(
    *,
    parent_values: list[str | None],
    detail_values: list[list[str | None]],
    total_values: list[str | None],
    parent_is_terminal: bool = True,
) -> tuple[dict, dict, dict]:
    prior_rows = [
        _row("Thu nhập lãi tiền gửi", ["10", "8"]),
        _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
        _row(
            "Thu lãi từ kinh doanh, đầu tư chứng khoán nợ:",
            parent_values,
        ),
    ]
    if not parent_is_terminal:
        prior_rows.append(_row("Thu phí từ nghiệp vụ bảo lãnh", ["1", "1"]))
    first_table = _table(prior_rows)
    first_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    receiver_rows = [
        _row("Thu lãi từ chứng khoán kinh doanh", detail_values[0]),
        _row("Thu lãi từ chứng khoán đầu tư", detail_values[1]),
    ]
    if parent_is_terminal:
        receiver_rows.append(_row("Thu phí từ nghiệp vụ bảo lãnh", ["1", "1"]))
    receiver_rows.extend(
        [
            _row("Thu nhập lãi cho thuê tài chính", ["-", "-"]),
            _row("Thu khác từ hoạt động tín dụng", ["2", "2"]),
            _row(None, total_values, kind="TOTAL"),
        ]
    )
    second_table = _table(
        receiver_rows,
        columns=_columns([None], [None]),
        title=None,
        unit=None,
    )
    second_table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    first = _page(first_table)
    second = _page(second_table)
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={NOTE_VERSION: first, PRIMARY_VERSION: second},
        records=[
            _record(first),
            _record(
                second,
                version=PRIMARY_VERSION,
                physical_page=3,
                selected_page_ordinal=3,
            ),
        ],
    )
    return first, second, candidate


def test_cross_fragment_same_role_parent_uses_exact_leading_detail_sum() -> None:
    first, second, candidate = _same_role_cross_fragment_candidate(
        parent_values=["5", "4"],
        detail_values=[["2", "1"], ["3", "3"]],
        total_values=["38", "27"],
    )

    assert candidate["status"] == READY
    securities = [
        mapping for mapping in candidate["mappings"] if mapping["role"] == "SECURITIES_INTEREST"
    ]
    assert len(securities) == 1
    assert [cell["coefficient"] for cell in securities[0]["values"]] == [5, 4]
    assert {
        ref["locator"]["page_json_version_id"] for ref in securities[0]["source_refs"]
    } == {
        NOTE_VERSION
    }
    cross_fragment_receipts = candidate["closure_receipt"][
        "cross_fragment_same_role_parent_equation_receipts"
    ]
    assert len(cross_fragment_receipts) == 1
    assert cross_fragment_receipts[0]["role"] == "SECURITIES_INTEREST"
    assert cross_fragment_receipts[0]["parent_row_ordinal"] == 3
    assert cross_fragment_receipts[0]["detail_row_ordinals"] == [1, 2]
    assert first["sections"][0]["tables"][0]["rows"][-1]["row_kind"] == "ITEM"
    assert second["sections"][0]["tables"][0]["rows"][0]["hierarchy_path_exact"] == [
        "Thu lãi từ chứng khoán kinh doanh"
    ]


@pytest.mark.parametrize(
    ("parent_values", "detail_values", "total_values", "parent_is_terminal"),
    [
        (["5", "4"], [["2", None], ["3", "3"]], ["38", "27"], True),
        (["6", "4"], [["2", "1"], ["3", "3"]], ["39", "27"], True),
        (["5", "4"], [["2", "1"], ["3", "3"]], ["38", "27"], False),
    ],
    ids=["blank-detail-lane", "mismatched-parent", "nonterminal-parent"],
)
def test_cross_fragment_same_role_parent_fails_closed_without_exact_contract(
    parent_values: list[str | None],
    detail_values: list[list[str | None]],
    total_values: list[str | None],
    parent_is_terminal: bool,
) -> None:
    _first, _second, candidate = _same_role_cross_fragment_candidate(
        parent_values=parent_values,
        detail_values=detail_values,
        total_values=total_values,
        parent_is_terminal=parent_is_terminal,
    )

    assert candidate["status"] != READY


def test_one_sided_explicit_receiver_is_recovered_without_value_selection() -> None:
    first_table = _table(
        [
            _row("Thu nhập lãi tiền gửi", ["10", "8"]),
            _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
            _row("Thu lãi từ kinh doanh, đầu tư chứng khoán nợ", ["5", "4"]),
        ]
    )
    second_table = _table(
        [
            _row("Thu lãi từ chứng khoán đầu tư", ["5", "4"]),
            _row("Thu phí từ nghiệp vụ bảo lãnh", ["1", "1"]),
            _row("Thu nhập lãi cho thuê tài chính", ["-", "-"]),
            _row("Thu khác từ hoạt động tín dụng", ["2", "2"]),
            _row(None, ["38", "27"], kind="TOTAL"),
        ],
        columns=_columns([None], [None]),
        title=None,
        unit=None,
    )
    second_table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    first = _page(first_table)
    second = _page(second_table)
    second["sections"][0]["title_exact"] = None
    records = [
        _record(first, selected_page_ordinal=1),
        _record(
            second,
            version=PRIMARY_VERSION,
            physical_page=3,
            selected_page_ordinal=2,
        ),
    ]
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_interest_income_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    assert raw_cluster["status"] == READY
    assert len(raw_cluster["component_regions"]) == 1
    adapted, receipts = adapt_gemini_json_interest_income_indexed_query_evidence_v1(
        _indexed_query_evidence(
            cluster=raw_cluster,
            records=records,
            compiled=compiled,
        ),
        page_json_by_document={1: {NOTE_VERSION: first, PRIMARY_VERSION: second}},
        compiled_specs=compiled,
    )
    cluster = adapted["accepted_clusters"][0]
    assert len(receipts) == 1
    assert len(cluster["component_regions"]) == 2
    receipt = build_gemini_json_interest_income_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_interest_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={NOTE_VERSION: first, PRIMARY_VERSION: second},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CUSTOMER_LOAN_INTEREST",
        "DEPOSIT_INTEREST",
        "FAMILY_ROOT_TOTAL",
        "FINANCE_LEASE_INTEREST",
        "GUARANTEE_FEE_INTEREST",
        "OTHER_CREDIT_INCOME",
        "SECURITIES_INTEREST",
    }


def test_one_sided_receiver_with_visible_header_is_not_recovered() -> None:
    first = _page(
        _table(
            [
                _row("Thu nhập lãi tiền gửi", ["10", "8"]),
                _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
            ]
        )
    )
    receiver = _table(
        [
            _row("Thu phí từ nghiệp vụ bảo lãnh", ["1", "1"]),
            _row(None, ["31", "21"], kind="TOTAL"),
        ],
        columns=_columns(["Kỳ này"], [None]),
        title=None,
        unit=None,
    )
    receiver["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    second = _page(receiver)
    second["sections"][0]["title_exact"] = None
    records = [
        _record(first, selected_page_ordinal=1),
        _record(
            second,
            version=PRIMARY_VERSION,
            physical_page=3,
            selected_page_ordinal=2,
        ),
    ]
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_interest_income_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    adapted, receipts = adapt_gemini_json_interest_income_indexed_query_evidence_v1(
        _indexed_query_evidence(
            cluster=raw_cluster,
            records=records,
            compiled=compiled,
        ),
        page_json_by_document={1: {NOTE_VERSION: first, PRIMARY_VERSION: second}},
        compiled_specs=compiled,
    )
    assert receipts == []
    assert len(adapted["accepted_clusters"][0]["component_regions"]) == 1


def test_source_repair_rejects_runtime_page_or_cell_drift() -> None:
    page = _page(_table(_interest_rows(securities_comparative=None)))
    compiled = _compiled(_repair_artifact(page, row_ordinal=3, column_ordinal=2))
    cluster = coalesce_gemini_json_interest_income_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    drifted = copy.deepcopy(page)
    drifted["sections"][0]["tables"][0]["rows"][2]["values_exact"][1] = "0"
    with pytest.raises(GeminiJsonInterestIncomeFamilyV1Error, match="base page drifted"):
        _apply_authenticated_source_repairs_v1(
            regions=cluster["component_regions"],
            page_json_by_version={NOTE_VERSION: drifted},
            compiled_specs=compiled,
        )


def test_exact_governed_duration_header_is_narrowly_normalized() -> None:
    page = _page(
        _table(
            _interest_rows(),
            columns=_columns(
                ["Luỹ kế từ đầu năm đến cuối kỳ này", "Năm nay"],
                ["Luỹ kế từ đầu năm đến cuối kỳ này", "Năm trước"],
            ),
        )
    )
    compiled = _compiled()
    cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={NOTE_VERSION: page},
        records=[_record(page)],
    )
    assert candidate["status"] == READY
    adapter = candidate["closure_receipt"]["interest_income_adapter_receipt"]
    assert len(adapter["period_normalization_receipts"]) == 1
    assert page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] == [
        "Luỹ kế từ đầu năm đến cuối kỳ này",
        "Năm nay",
    ]

    negative_page = _page(
        _table(
            _interest_rows(),
            columns=_columns(["Số dư đầu kỳ", "Năm nay"], ["Số dư đầu kỳ", "Năm trước"]),
        )
    )
    pages = {NOTE_VERSION: copy.deepcopy(negative_page)}
    receipts = _normalize_governed_duration_headers_v1(
        pages=pages,
        regions=cluster["component_regions"],
    )
    assert receipts == []
    assert pages[NOTE_VERSION] == negative_page


def _primary_page(*, million_values: list[str], vnd_values: list[str]) -> dict:
    root = "1- Thu nhập lãi và các khoản thu nhập tương tự"
    raw = _table(
        [_row(root, vnd_values)],
        title="Báo cáo kết quả hoạt động kinh doanh",
        unit="VND",
    )
    million = _table(
        [_row(root, million_values)],
        title="Báo cáo kết quả hoạt động kinh doanh",
        unit="Triệu đồng",
    )
    return _page(raw, million, status="PRIMARY_FINANCIAL_STATEMENT")


def test_unitless_note_binds_only_to_exact_primary_statement_unit() -> None:
    note = _page(
        _table(
            _interest_rows(),
            columns=_columns(["Kỳ này"], ["Kỳ trước"]),
            unit=None,
        )
    )
    primary = _primary_page(
        million_values=["35", "20"],
        vnd_values=["35.000.000", "20.000.000"],
    )
    compiled = _compiled()
    cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        records=[
            _record(
                primary,
                version=PRIMARY_VERSION,
                physical_page=1,
                selected_page_ordinal=1,
            ),
            _record(note),
        ],
    )
    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"MILLION_VND"}
    adapter = candidate["closure_receipt"]["interest_income_adapter_receipt"]
    assert len(adapter["unit_corroboration_receipts"]) == 1
    unit = adapter["unit_corroboration_receipts"][0]
    assert unit["canonical_unit"] == "MILLION_VND"
    assert unit["target_vector"] == [35, 20]
    assert note["sections"][0]["tables"][0]["unit_exact"] is None
    validate_gemini_json_interest_income_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_interest_income_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def test_unitless_note_does_not_bind_when_two_primary_units_match() -> None:
    note = _page(
        _table(
            _interest_rows(),
            columns=_columns(["Kỳ này"], ["Kỳ trước"]),
            unit=None,
        )
    )
    primary = _primary_page(
        million_values=["35", "20"],
        vnd_values=["35", "20"],
    )
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        records=[
            _record(
                primary,
                version=PRIMARY_VERSION,
                physical_page=1,
                selected_page_ordinal=1,
            ),
            _record(note),
        ],
    )
    assert candidate["status"] != READY
    assert candidate["mappings"] == []
    assert "interest_income_adapter_receipt" not in candidate["closure_receipt"]


def test_unitless_note_does_not_ignore_a_partially_observed_component() -> None:
    note = _page(
        _table(
            [
                _row("Thu nhập lãi tiền gửi", ["10", "8"]),
                _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
                _row("Thu lãi từ đầu tư chứng khoán nợ", ["5", None]),
            ],
            columns=_columns(["Kỳ này"], ["Kỳ trước"]),
            unit=None,
        )
    )
    primary = _primary_page(
        million_values=["30", "20"],
        vnd_values=["30.000.000", "20.000.000"],
    )
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        records=[
            _record(
                primary,
                version=PRIMARY_VERSION,
                physical_page=1,
                selected_page_ordinal=1,
            ),
            _record(note),
        ],
    )

    assert candidate["status"] != READY
    assert candidate["mappings"] == []
    assert "interest_income_adapter_receipt" not in candidate["closure_receipt"]


def test_unitless_note_does_not_bypass_a_partially_observed_printed_total() -> None:
    rows = _interest_rows()
    rows[-1] = _row(None, ["35", None], kind="TOTAL")
    note = _page(
        _table(
            rows,
            columns=_columns(["Kỳ này"], ["Kỳ trước"]),
            unit=None,
        )
    )
    primary = _primary_page(
        million_values=["35", "20"],
        vnd_values=["35.000.000", "20.000.000"],
    )
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        records=[
            _record(
                primary,
                version=PRIMARY_VERSION,
                physical_page=1,
                selected_page_ordinal=1,
            ),
            _record(note),
        ],
    )

    assert candidate["status"] != READY
    assert candidate["mappings"] == []
    assert "interest_income_adapter_receipt" not in candidate["closure_receipt"]


def test_unitless_note_does_not_choose_one_of_multiple_printed_totals() -> None:
    rows = _interest_rows()
    rows.append(_row("Tổng cộng khác", ["35", None], kind="TOTAL"))
    note = _page(
        _table(
            rows,
            columns=_columns(["Kỳ này"], ["Kỳ trước"]),
            unit=None,
        )
    )
    primary = _primary_page(
        million_values=["35", "20"],
        vnd_values=["35.000.000", "20.000.000"],
    )
    compiled = _compiled()
    _cluster, candidate = _cluster_and_candidate(
        compiled=compiled,
        pages={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        records=[
            _record(
                primary,
                version=PRIMARY_VERSION,
                physical_page=1,
                selected_page_ordinal=1,
            ),
            _record(note),
        ],
    )

    assert candidate["status"] != READY
    assert candidate["mappings"] == []
    assert "interest_income_adapter_receipt" not in candidate["closure_receipt"]
