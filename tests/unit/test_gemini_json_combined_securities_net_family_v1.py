from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
COMBINED = "Lãi thuần từ chứng khoán kinh doanh và chứng khoán đầu tư"
TRADING = "Lãi thuần từ mua bán chứng khoán kinh doanh"
INVESTMENT = "Lãi thuần từ mua bán chứng khoán đầu tư"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-combined-securities-net-topology-v1.json"),
        _json("tm-combined-securities-net-evaluation-v1.json"),
        _json("tm-combined-securities-net-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    parent: str | None = None,
) -> dict[str, Any]:
    path = [value for value in (parent, label) if value is not None]
    return {
        "hierarchy_path_exact": path,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _combined_table() -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["Năm 2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(TRADING, [None, None], kind="GROUP"),
            _row("Thu nhập từ mua bán chứng khoán kinh doanh", ["100", "80"], parent=TRADING),
            _row("Chi về mua bán chứng khoán kinh doanh", ["(10)", "(5)"], parent=TRADING),
            _row(None, ["90", "75"], kind="SUBTOTAL", parent=TRADING),
            _row(INVESTMENT, [None, None], kind="GROUP"),
            _row("Thu nhập từ mua bán chứng khoán đầu tư", ["50", "40"], parent=INVESTMENT),
            _row("Chi về chứng khoán đầu tư", ["(20)", "(10)"], parent=INVESTMENT),
            _row("Trích lập dự phòng chứng khoán đầu tư", ["(5)", "(5)"], parent=INVESTMENT),
            _row(None, ["25", "25"], kind="SUBTOTAL", parent=INVESTMENT),
            _row(COMBINED, ["115", "100"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _page(*, title: str | None = COMBINED) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [_combined_table()],
                "title_exact": title,
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


def _cluster(page: dict[str, Any]) -> dict[str, Any]:
    return coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )


def _evaluate(page: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    cluster = _cluster(page)
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, regions, receipt


def test_combined_source_result_maps_only_visible_root_and_proves_components() -> None:
    candidate, _regions, _receipt = _evaluate(_page())
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 1
    mapping = candidate["mappings"][0]
    assert mapping["report_norm_id"] == 5990
    assert mapping["role"] == "FAMILY_ROOT_TOTAL"
    assert [cell["coefficient"] for cell in mapping["values"]] == [115, 100]
    assert len(mapping["source_refs"]) == 1
    assert mapping["row_id"] == "r10"
    assert (
        candidate["closure_receipt"]["validation_only_roles"]
        == _compiled()["validation_only_roles"]
    )
    assert all(
        mapping["report_norm_id"] not in {1188, 1189, 1190, 1191, 1193, 1194, 1195, 1196}
        for mapping in candidate["mappings"]
    )


def test_combined_source_result_row_is_its_own_owner_when_heading_is_absent() -> None:
    cluster = _cluster(_page(title=None))
    assert cluster["status"] == READY
    assert cluster["owner_receipt"]["alias"] == "EXACT_SOURCE_RESULT_ROW"


def test_combined_heading_without_exact_source_result_is_a_bounded_absence() -> None:
    page = _page()
    page["sections"][0]["tables"] = [
        {
            **_combined_table(),
            "rows": _combined_table()["rows"][:4],
            "title_exact": TRADING,
        },
        {
            **_combined_table(),
            "rows": _combined_table()["rows"][4:9],
            "title_exact": INVESTMENT,
        },
    ]
    cluster = _cluster(page)
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == []
    assert {item["disposition"] for item in cluster["declared_money_table_inventory"]} == {
        "SOURCE_RESULT_OWNER_WITHOUT_EXACT_RESULT_ROW"
    }


def test_combined_cash_flow_change_row_is_not_a_source_result() -> None:
    page = _page(title="LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG KINH DOANH")
    page["sections"][0]["statement_type"] = "CASH_FLOW"
    table = page["sections"][0]["tables"][0]
    table["rows"] = [_row(COMBINED, ["1", "2"], kind="TOTAL")]
    cluster = _cluster(page)
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_combined_source_result_mismatch_fails_closed_without_mapping() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "116"
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason.startswith("SOURCE_RESULT_DECLARED_COMPONENT_") for reason in candidate["reasons"]
    )


def test_combined_missing_component_population_fails_closed() -> None:
    page = _page()
    rows = page["sections"][0]["tables"][0]["rows"]
    page["sections"][0]["tables"][0]["rows"] = rows[:4] + [rows[-1]]
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_exact_source_result_maps_without_component_population_or_row_kind_dependency() -> None:
    page = _page(title=None)
    page["sections"][0]["tables"][0]["rows"] = [
        _row("Khoản mục ngoài graph family", ["not-an-integer", "7"]),
        _row(COMBINED, ["115", "100"], kind="ITEM"),
    ]
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 1
    mapping = candidate["mappings"][0]
    assert mapping["row_id"] == "r2"
    assert [cell["coefficient"] for cell in mapping["values"]] == [115, 100]
    assert mapping["state"] == "SOURCE_VISIBLE_EXACT_RESULT_ROW_WITHOUT_COMPONENT_EVIDENCE"
    assert candidate["closure_receipt"]["root_component_sum_receipts"][0]["component_roles"] == []


def test_heading_free_source_result_does_not_absorb_unrelated_following_table() -> None:
    page = _page(title=None)
    page["sections"][0]["tables"] = [
        {
            **_combined_table(),
            "rows": [_row(COMBINED, ["115", "100"], kind="ITEM")],
            "title_exact": None,
        },
        {
            **_combined_table(),
            "rows": [_row("Khoản mục không thuộc family", ["invalid", "7"])],
            "title_exact": None,
        },
    ]
    cluster = _cluster(page)
    assert cluster["status"] == READY
    assert [(item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        ("s1", "t1")
    ]
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 1


def test_heading_free_duplicate_source_result_tables_fail_closed() -> None:
    page = _page(title=None)
    page["sections"][0]["tables"] = [
        {
            **_combined_table(),
            "rows": [_row(COMBINED, ["115", "100"], kind="ITEM")],
            "title_exact": None,
        },
        {
            **_combined_table(),
            "rows": [_row(COMBINED, ["115", "100"], kind="TOTAL")],
            "title_exact": None,
        },
    ]
    cluster = _cluster(page)
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "MULTIPLE_COMPLETE_OWNER_CLUSTERS" in cluster["reasons"]


def test_partial_component_evidence_vetoes_standalone_source_result() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [
        _row(TRADING, ["90", "75"], kind="SUBTOTAL"),
        _row(COMBINED, ["115", "100"], kind="ITEM"),
    ]
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason.startswith("SOURCE_RESULT_DECLARED_COMPONENT_POPULATION_NOT_EXACT:")
        for reason in candidate["reasons"]
    )


def test_duplicate_or_blank_source_result_rows_fail_closed() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [
        _row(COMBINED, ["115", "100"], kind="TOTAL"),
        _row(COMBINED, ["115", "100"], kind="ITEM"),
    ]
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "EXACT_SOURCE_RESULT_ROW_NOT_UNIQUE" in candidate["reasons"]

    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [_row(COMBINED, [None, "100"], kind="TOTAL")]
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_combined_candidate_replay_rejects_source_row_drift() -> None:
    page = _page()
    candidate, regions, receipt = _evaluate(page)
    forged = copy.deepcopy(candidate)
    forged["mappings"][0]["source_refs"][0]["label_exact"] = "forged"
    try:
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=regions,
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("candidate replay accepted source drift")


def test_combined_period_and_unit_conflicts_fail_closed() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"].append("Năm trước")
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []

    page = _page()
    page["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
