from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation import gemini_json_region_repair_queue_v1 as repair_queue
from bctc_ai.evaluation.gemini_json_investment_securities_activity_family_v1 import (
    GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
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
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    GeminiJsonRegionRepairV1Error,
    project_whole_page_table_population_v1,
    validate_whole_page_table_population_projection_v1,
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


def _page(
    *,
    provision: bool = True,
    long_term: bool = True,
    net: tuple[str, str] = ("65", "58"),
) -> dict[str, Any]:
    rows = [
        _row(ROOT_LABEL, list(net), kind="TOTAL"),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"]),
        _row(
            "Chi phí về mua bán chứng khoán đầu tư",
            ["(20)", "(15)"] if provision else ["(30)", "(20)"],
        ),
    ]
    if provision:
        rows.append(_row("Trích lập dự phòng chứng khoán đầu tư", ["(10)", "(5)"]))
    if long_term:
        rows.append(
            _row(
                "(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn",
                ["(5)", "(2)"],
            )
        )
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


def _record(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _candidate_and_replay_inputs(
    page: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    pages = {VERSION_ID: page}
    receipt = build_gemini_json_investment_securities_activity_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, regions, pages, receipt


def _evaluate(page: dict[str, Any]) -> dict[str, Any]:
    return _candidate_and_replay_inputs(page)[0]


def test_investment_securities_all_declared_components_close_exactly() -> None:
    candidate = _evaluate(_page())
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
        "LONG_TERM_INVESTMENT_PROVISION",
        "PROVISION_INVESTMENT_SECURITIES",
    }


def test_investment_securities_optional_components_are_not_invented() -> None:
    candidate = _evaluate(_page(provision=False, long_term=False, net=("70", "60")))
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
    }


def test_investment_securities_single_visible_component_proves_total() -> None:
    page = _page(provision=False, long_term=False, net=("100", "80"))
    page["sections"][0]["tables"][0]["rows"] = [
        _row(ROOT_LABEL, ["100", "80"], kind="TOTAL"),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"]),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 2


def test_investment_securities_vocabulary_and_other_role_are_declarative() -> None:
    page = _page(net=("64", "57"))
    page["sections"][0]["tables"][0]["rows"] = [
        _row(ROOT_LABEL, ["64", "57"], kind="TOTAL"),
        _row("Thu nhập do mua bán chứng khoán đầu tư", ["100", "80"]),
        _row("Chi về chứng khoán đầu tư", ["(20)", "(15)"]),
        _row("Dự phòng rủi ro chứng khoán đầu tư", ["(10)", "(5)"]),
        _row("Hoàn nhập/(Trích lập) dự phòng rủi ro đầu tư dài hạn", ["(5)", "(2)"]),
        _row("Khác", ["(1)", "(1)"]),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_INVESTMENT_SECURITIES",
        "FAMILY_ROOT_TOTAL",
        "INCOME_INVESTMENT_SECURITIES",
        "LONG_TERM_INVESTMENT_PROVISION",
        "OTHER_INVESTMENT_SECURITIES",
        "PROVISION_INVESTMENT_SECURITIES",
    }


@pytest.mark.parametrize(
    ("row_index", "label", "role"),
    [
        (0, "Lỗ thuần từ mua bán chứng khoán đầu tư", "FAMILY_ROOT_TOTAL"),
        (0, "(Lỗ) thuần từ mua bán chứng khoán đầu tư", "FAMILY_ROOT_TOTAL"),
        (0, "Lỗ thuần từ mua bán CK đầu tư", "FAMILY_ROOT_TOTAL"),
        (0, "(Lỗ)/ lãi thuần từ mua bán CK đầu tư", "FAMILY_ROOT_TOTAL"),
        (
            1,
            "Thu nhập từ mua bán chứng khoán sẵn sàng để bán",
            "INCOME_INVESTMENT_SECURITIES",
        ),
        (
            2,
            "(Chi phí) về mua bán chứng khoán sẵn sàng để bán",
            "EXPENSE_INVESTMENT_SECURITIES",
        ),
        (2, "Chi cho kinh doanh chứng khoán đầu tư", "EXPENSE_INVESTMENT_SECURITIES"),
        (2, "Lỗ từ mua bán chứng khoán đầu tư", "EXPENSE_INVESTMENT_SECURITIES"),
        (
            3,
            "(Chi phí)/Hoàn nhập dự phòng rủi ro chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "(Chi phí)/Hoàn nhập dự phòng chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Dự phòng / (hoàn nhập dự phòng) rủi ro chứr",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Dự phòng/ (Hoàn nhập) dự phòng chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Dự phòng / (hoàn nhập dự phòng) rủi ro chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Hoàn nhập/Trích lập dự phòng giảm giá chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "(Trích lập)/hoàn nhập dự phòng giảm giá chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Trích lập dự phòng rủi ro chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Dự phòng chung chứng khoán đầu tư hoàn nhập trong kỳ",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Dự phòng cụ thể chứng khoán đầu tư trích lập trong kỳ",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Hoàn nhập dự phòng chung chứng khoán đầu tư",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Trích lập/(hoàn nhập) dự phòng rủi ro chứng khoán sẵn sàng để bán",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "(Trích lập)/hoàn nhập dự phòng rủi ro chứng khoán sẵn sàng để bán",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (3, "Hoàn nhập dự phòng rủi ro", "PROVISION_INVESTMENT_SECURITIES"),
        (
            3,
            "Hoàn nhập/(trích lập) dự phòng chung cho trái phiếu doanh nghiệp "
            "chưa niêm yết (Thuyết minh 12.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "(Trích lập)/Hoàn nhập dự phòng chung cho trái phiếu doanh nghiệp "
            "chưa niêm yết (Thuyết minh 12.2)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Hoàn nhập dự phòng chung\ncho trái phiếu doanh nghiệp chưa niêm yết\n"
            "(Thuyết minh 12.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Trích lập dự phòng cụ thể\ncho trái phiếu doanh nghiệp chưa niêm "
            "yết\n(Thuyết minh 12.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Hoàn nhập dự phòng chung chứng khoán nợ sẵn sàng để bán "
            "(Thuyết minh 13.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Trích lập dự phòng giảm giá chứng khoán nợ sẵn sàng để bán\n"
            "(Thuyết minh 15.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Hoàn nhập dự phòng cụ thể chứng khoán đầu tư nắm giữ đến\n"
            "ngày đáo hạn (Thuyết minh 15.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Trích lập dự phòng cụ thể chứng khoán đầu tư nắm giữ đến ngày "
            "đáo hạn(Thuyết minh 13.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Trích lập dự phòng cụ thể chứng khoán nợ đầu tư nắm giữ\n"
            "đến ngày đáo hạn (Thuyết minh 13.3)",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "(Trích lập)/hoàn nhập dự phòng chung chứng khoán đầu tư sẵn sàng\n"
            "để bán (Thuyết minh 11(i))",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "Hoàn nhập/ (trích lập) dự phòng rủi ro",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
        (
            3,
            "(Trích)/ hoàn nhập dự phòng rủi ro",
            "PROVISION_INVESTMENT_SECURITIES",
        ),
    ],
)
def test_investment_securities_current_source_aliases_map_exact_roles(
    row_index: int,
    label: str,
    role: str,
) -> None:
    page = _page()
    row = page["sections"][0]["tables"][0]["rows"][row_index]
    row["label_exact"] = label
    row["hierarchy_path_exact"] = [label] if row_index == 0 else [ROOT_LABEL, label]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert role in {mapping["role"] for mapping in candidate["mappings"]}


def test_investment_securities_source_visible_vnd_unit_maps_without_rescaling() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["unit_exact"] = "VND"
    table["columns"][0]["header_path_exact"] = ["Năm 2025", "VND"]
    table["columns"][1]["header_path_exact"] = ["Năm 2024", "VND"]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert all(mapping["unit"] == "VND" for mapping in candidate["mappings"])
    assert candidate["mappings"][0]["values"][0]["coefficient"] == 100


def test_investment_securities_combined_umbrella_consumes_only_its_subtree() -> None:
    trading_root = "Lãi thuần từ mua bán chứng khoán kinh doanh"
    page = _page()
    page["sections"][0]["title_exact"] = "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư"
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = None
    table["rows"] = [
        _row(trading_root, [None, None], kind="GROUP", parent=trading_root),
        _row("Thu nhập từ mua bán chứng khoán kinh doanh", ["100", "80"], parent=trading_root),
        _row(None, ["100", "80"], kind="SUBTOTAL", parent=trading_root),
        _row(ROOT_LABEL, [None, None], kind="GROUP", parent=ROOT_LABEL),
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"], parent=ROOT_LABEL),
        _row("Chi phí về mua bán chứng khoán đầu tư", ["(20)", "(15)"], parent=ROOT_LABEL),
        _row("Trích lập dự phòng chứng khoán đầu tư", ["(10)", "(5)"], parent=ROOT_LABEL),
        _row(
            "(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn",
            ["(5)", "(2)"],
            parent=ROOT_LABEL,
        ),
        _row(None, ["65", "58"], kind="SUBTOTAL", parent=ROOT_LABEL),
    ]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert all(
        "chứng khoán kinh doanh" not in str(source_ref.get("label_exact", "")).lower()
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    )


def test_investment_securities_foreign_dimension_is_not_observed() -> None:
    page = _page()
    page["sections"][0]["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    table["rows"] = [_row(ROOT_LABEL, ["65", "58"])]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_investment_securities_unmapped_direct_child_fails_closed() -> None:
    page = _page(net=("66", "59"))
    page["sections"][0]["tables"][0]["rows"].append(
        _row("Khoản chứng khoán đầu tư chưa khai báo", ["1", "1"])
    )
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_investment_securities_duplicate_period_and_unit_conflicts_fail_closed() -> None:
    duplicate = _page()
    duplicate["sections"][0]["tables"].append(copy.deepcopy(duplicate["sections"][0]["tables"][0]))
    assert _evaluate(duplicate)["status"] == UNRESOLVED

    unit = _page()
    unit["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    assert _evaluate(unit)["status"] == UNRESOLVED

    period = _page()
    period["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Năm 2025",
        "Năm trước",
        "Triệu đồng",
    ]
    assert _evaluate(period)["status"] == UNRESOLVED


def test_investment_securities_net_mismatch_is_unresolved_without_mappings() -> None:
    candidate = _evaluate(_page(net=("68", "61")))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_investment_securities_candidate_replay_rejects_coherent_drift() -> None:
    candidate, regions, pages, receipt = _candidate_and_replay_inputs(_page())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["equations"][0]["status"] = "MISMATCH"
    material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        GeminiJsonInvestmentSecuritiesActivityFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_investment_securities_activity_family_candidate_replay_v1(
            forged,
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def _missing_total_retry_pages() -> tuple[dict[str, Any], dict[str, Any]]:
    base = _page(net=("65", "58"))
    base_table = base["sections"][0]["tables"][0]
    base_table["rows"] = [
        _row("Thu nhập từ mua bán chứng khoán đầu tư", ["100", "80"]),
        _row("Chi phí về mua bán chứng khoán đầu tư", ["(20)", "(15)"]),
        _row("Trích lập dự phòng chứng khoán đầu tư", ["10 lỗi", "(5)"]),
    ]
    retry_table = copy.deepcopy(base_table)
    retry_table["title_exact"] = None
    retry_table["columns"][0]["header_path_exact"] = ["Năm 2025", "Triệu đồng"]
    retry_table["columns"][1]["header_path_exact"] = ["Năm 2024", "Triệu đồng"]
    retry_table["rows"][2]["values_exact"] = ["(10)", "(5)"]
    retry_table["rows"].append(_row(None, ["70", "60"], kind="TOTAL"))
    retry = copy.deepcopy(base)
    retry["sections"] = [
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [retry_table],
            "title_exact": ROOT_LABEL,
        }
    ]
    return base, retry


def _project_missing_total(
    base: dict[str, Any], retry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    return project_whole_page_table_population_v1(
        base,
        retry,
        base_page_json_version_id=VERSION_ID,
        retry_page_json_version_id="gfpstorev1:json:" + "d" * 64,
        target_table_ref={"section_id": "s1", "table_id": "t1"},
        required_changed_target_ids=["s1:t1:r3"],
        require_added_rows=True,
    )


def test_standard_page_retry_projects_only_one_exact_table_population() -> None:
    base, retry = _missing_total_retry_pages()
    merged, receipt = _project_missing_total(base, retry)
    assert merged["sections"][0]["tables"][0]["title_exact"] == ROOT_LABEL
    assert (
        merged["sections"][0]["tables"][0]["columns"]
        == (base["sections"][0]["tables"][0]["columns"])
    )
    assert receipt["added_retry_row_ids"] == ["s1:t1:r4"]
    assert receipt["required_changed_target_ids"] == ["s1:t1:r3"]
    assert _evaluate(merged)["status"] == READY
    validate_whole_page_table_population_projection_v1(
        receipt,
        base_page_json=base,
        retry_page_json=retry,
        merged_page_json=merged,
    )


def test_page_retry_projection_rejects_non_target_drift_and_ambiguity() -> None:
    base, retry = _missing_total_retry_pages()
    retry["sections"][0]["tables"][0]["rows"][0]["values_exact"] = ["101", "80"]
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="non-target"):
        _project_missing_total(base, retry)

    base, retry = _missing_total_retry_pages()
    retry["sections"][0]["tables"].append(copy.deepcopy(retry["sections"][0]["tables"][0]))
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="one unique"):
        _project_missing_total(base, retry)

    base, retry = _missing_total_retry_pages()
    retry["sections"][0]["tables"][0]["rows"][:2] = reversed(
        retry["sections"][0]["tables"][0]["rows"][:2]
    )
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="one unique"):
        _project_missing_total(base, retry)


def test_page_retry_projection_rejects_unscoped_added_item_rows() -> None:
    base, retry = _missing_total_retry_pages()
    rows = retry["sections"][0]["tables"][0]["rows"]
    rows.insert(-1, _row("Khoản chứng khoán đầu tư chưa khai báo", ["1", "1"]))
    rows[-1]["values_exact"] = ["71", "61"]
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="non-structural"):
        _project_missing_total(base, retry)


def test_page_retry_projection_receipt_and_merged_content_replay_exactly() -> None:
    base, retry = _missing_total_retry_pages()
    merged, receipt = _project_missing_total(base, retry)
    forged_receipt = copy.deepcopy(receipt)
    forged_receipt["matched_rows"][0]["values_changed"] = True
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="replay exactly"):
        validate_whole_page_table_population_projection_v1(
            forged_receipt,
            base_page_json=base,
            retry_page_json=retry,
            merged_page_json=merged,
        )

    forged_merged = copy.deepcopy(merged)
    forged_merged["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"
    with pytest.raises(GeminiJsonRegionRepairV1Error, match="replay exactly"):
        validate_whole_page_table_population_projection_v1(
            receipt,
            base_page_json=base,
            retry_page_json=retry,
            merged_page_json=forged_merged,
        )


def test_page_retry_projection_plan_binds_one_typed_unresolved_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base, retry = _missing_total_retry_pages()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(base)], compiled_specs=_compiled()
    )
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_investment_securities_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: base},
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_investment_securities_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == UNRESOLVED
    checked_sweep = {
        "family_id": "INVESTMENT_SECURITIES_ACTIVITY",
        "trials": [
            {
                "candidate_count": 1,
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [],
                "reasons": candidate["reasons"],
                "selected_candidate_id": None,
                "source_logical_name": "fixture.pdf",
                "source_sha256": SOURCE_SHA256,
                "status": UNRESOLVED,
            }
        ],
    }
    monkeypatch.setattr(
        repair_queue,
        "validate_gemini_json_flat_family_sweep_v1",
        lambda _value: checked_sweep,
    )
    _merged, receipt = _project_missing_total(base, retry)
    plan = repair_queue.build_whole_page_table_population_projection_repair_plan_v1(
        sweep={"sealed": True}, projection_receipt=receipt
    )
    assert plan["candidate_id"] == candidate["candidate_id"]
    assert plan["target_ids"] == ["s1:t1:r3"]
    assert plan["retry_page_json_version_id"] == receipt["retry_page_json_version_id"]

    forged = copy.deepcopy(receipt)
    forged["required_changed_target_ids"] = ["s1:t1:r2"]
    with pytest.raises(repair_queue.GeminiJsonRegionRepairQueueV1Error, match="identity drifted"):
        repair_queue.build_whole_page_table_population_projection_repair_plan_v1(
            sweep={"sealed": True}, projection_receipt=forged
        )
