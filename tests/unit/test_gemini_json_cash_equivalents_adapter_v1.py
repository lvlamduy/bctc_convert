from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_cash_equivalents_family_v1 import (
    GeminiJsonCashEquivalentsFamilyV1Error,
    _project_ambiguous_period_headers_v1,
    _project_primary_supplemental_pages_v1,
    adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1,
    build_gemini_json_cash_equivalents_region_query_receipt_v1,
    compile_gemini_json_cash_equivalents_family_specs_v1,
    evaluate_gemini_json_cash_equivalents_family_cluster_v1,
    validate_gemini_json_cash_equivalents_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
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
OWNER = "Tiền và các khoản tương đương tiền"


def _json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_bytes())


def _empty_repairs() -> dict[str, Any]:
    repairs: list[dict[str, Any]] = []
    return {
        "family_id": "CASH_EQUIVALENTS",
        "format_version": (
            "GEMINI_JSON_CASH_EQUIVALENTS_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
        ),
        "policy": (
            "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_MISSING_AS_NULL_"
            "NO_BLANK_ZERO_INFERENCE"
        ),
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "render_dpi": 300,
            "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
        },
        "repair_axis_sha256": canonical_json_sha256_v1(repairs),
        "repairs": repairs,
    }


def _compiled(repairs: dict[str, Any] | None = None) -> dict[str, Any]:
    return compile_gemini_json_cash_equivalents_family_specs_v1(
        _json("config/families/tm-cash-equivalents-topology-v1.json"),
        _json("config/families/tm-cash-equivalents-evaluation-v1.json"),
        _json("config/families/tm-cash-equivalents-schema-binding-v1.json"),
        _empty_repairs() if repairs is None else repairs,
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
    hierarchy: list[str | None] | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            ([] if label is None else [label]) if hierarchy is None else hierarchy
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _rows(*, current_delta: int = 0) -> list[dict[str, Any]]:
    return [
        _row("Tiền mặt, vàng bạc, đá quý", str(10 + current_delta), "9"),
        _row("Tiền gửi tại NHNN", "20", "18"),
        _row(
            "Tiền gửi tại các TCTD khác (gồm tiền gửi không kỳ hạn và "
            "tiền gửi có kỳ hạn không quá ba tháng)",
            "30",
            "27",
        ),
        _row(None, str(60 + current_delta), "54", kind="TOTAL"),
    ]


def _split_blank_rows() -> list[dict[str, Any]]:
    parent = "Tiền gửi tại các TCTD khác"
    return [
        _row("Tiền mặt, vàng", "10", "9"),
        _row("Tiền gửi tại Ngân hàng Nhà nước", "20", "18"),
        _row(parent, "30", "27", kind="GROUP"),
        _row("- Không kỳ hạn", "10", "9", hierarchy=[parent, "- Không kỳ hạn"]),
        _row(
            "- Có kỳ hạn không quá 3 tháng",
            "20",
            "18",
            hierarchy=[parent, "- Có kỳ hạn không quá 3 tháng"],
        ),
        _row(
            "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá 3 tháng "
            "kể từ ngày mua",
            None,
            "4",
        ),
        _row(None, "60", "58", kind="TOTAL"),
    ]


def _table(
    rows: list[dict[str, Any]],
    *,
    headers: tuple[str, str] = ("31/12/2025", "31/12/2024"),
    title: str | None = None,
) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": [headers[0]], "value_kind": "MONEY"},
            {"header_path_exact": [headers[1]], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _page(
    rows: list[dict[str, Any]],
    *,
    owner: str | None = OWNER,
    headers: tuple[str, str] = ("31/12/2025", "31/12/2024"),
    tables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
                "tables": tables if tables is not None else [_table(rows, headers=headers)],
                "title_exact": owner,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _primary_supplemental_page() -> dict[str, Any]:
    anchor = _table(
        [
            _row("Lưu chuyển tiền thuần trong kỳ", "1", "1", kind="SUBTOTAL"),
            _row(
                "Tiền và các khoản tương đương tiền tại thời điểm đầu kỳ",
                "59",
                "53",
                kind="SUBTOTAL",
            ),
            _row(
                "Tiền và các khoản tương đương tiền tại thời điểm cuối kỳ",
                "60",
                "54",
                kind="TOTAL",
            ),
        ],
        headers=("Năm nay", "Năm Trước"),
    )
    detail = _table(
        _rows(),
        headers=("Năm nay", "Năm Trước"),
        title="Các khoản tiền tương đương tiền cuối kỳ bao gồm",
    )
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "CASH_FLOW",
                "tables": [anchor, detail],
                "title_exact": None,
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
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


def _force_unresolved(
    page: dict[str, Any], compiled: dict[str, Any]
) -> dict[str, Any]:
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    cluster["component_regions"] = []
    cluster["owner_receipt"] = None
    cluster["reasons"] = ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"]
    cluster["status"] = UNRESOLVED
    for item in cluster["declared_money_table_inventory"]:
        item["disposition"] = "OUTSIDE_SELECTED_OWNER_FENCE"
    material = {key: value for key, value in cluster.items() if key != "cluster_id"}
    cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
    return cluster


def _indexed(cluster: dict[str, Any], compiled: dict[str, Any]) -> dict[str, Any]:
    document = {
        key: _record({})[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    selected_page = {
        **document,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
    }
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=[selected_page],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def _adapt(
    page: dict[str, Any], compiled: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cluster = _force_unresolved(page, compiled)
    return adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1(
        _indexed(cluster, compiled),
        page_json_by_document={1: {VERSION_ID: page}},
        compiled_specs=compiled,
    )


def _evaluate(
    page: dict[str, Any], compiled: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_cash_equivalents_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, cluster, receipt


def _dash_repair_spec() -> dict[str, Any]:
    spec = _empty_repairs()
    repair = {
        "after_exact": "-",
        "before_exact": None,
        "crop_evidence": {
            "bbox_pixels_xyxy": [10, 10, 20, 20],
            "pixel_height": 10,
            "pixel_width": 10,
            "rgb_sha256": "1" * 64,
        },
        "locator": {
            "column_ordinal": 1,
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "row_ordinal": 6,
            "section_id": "s1",
            "table_id": "t1",
        },
        "observed_pdf_glyph": "-",
        "render": {
            "image_sha256": "2" * 64,
            "image_size_bytes": 100,
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": 100,
            "pixel_width": 100,
            "render_dpi": 300,
            "render_receipt_sha256": "3" * 64,
        },
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "source": {
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 100,
        },
    }
    repair["repair_id"] = "gjcefav1:source-repair:" + canonical_json_sha256_v1(
        repair
    )
    spec["repairs"] = [repair]
    spec["repair_axis_sha256"] = canonical_json_sha256_v1(spec["repairs"])
    return spec


def test_registered_source_repairs_compile_with_exact_axis_seal() -> None:
    registered = _json(
        "data/registered/gemini_json_cash_equivalents_source_repairs_v1.json"
    )
    compiled = _compiled(registered)
    assert len(compiled["cash_equivalents_source_repairs"]) == 9
    assert compiled["cash_equivalents_source_repair_spec_sha256"] == (
        canonical_json_sha256_v1(registered)
    )


def test_unique_exact_local_owner_table_is_recovered_and_replayed() -> None:
    page = _page(_rows())
    compiled = _compiled()
    adapted, receipts = _adapt(page, compiled)
    assert len(receipts) == 1
    assert receipts[0]["rule"].endswith("NO_RESET_VALUE_INDEPENDENT")
    cluster = adapted["accepted_clusters"][0]
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_cash_equivalents_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )


def test_exact_narrative_owner_recovers_one_unique_family_shape_only() -> None:
    page = _page(_rows(), owner="Thuyết minh báo cáo tài chính")
    page["sections"][0]["narratives_exact"] = [
        "30. Tiền và các khoản tương đương tiền"
    ]
    page["sections"][0]["tables"].insert(
        0,
        _table(
            [
                _row("Khoản mục thuế khác", "1", "1"),
                _row(None, "1", "1", kind="TOTAL"),
            ],
            title=None,
        ),
    )
    compiled = _compiled()
    assert compiled["query_policy"]["owner_surface_kinds"] == [
        "SECTION_TITLE",
        "TABLE_TITLE",
    ]
    adapted, receipts = _adapt(page, compiled)
    assert len(receipts) == 1
    assert receipts[0]["owner_source_kind"] == "SECTION_NARRATIVE"
    assert "UNIQUE_DECLARED_FAMILY_SHAPE_IN_SECTION" in receipts[0]["rule"]
    assert adapted["accepted_clusters"][0]["component_regions"][0]["table_id"] == "t2"


@pytest.mark.parametrize("failure_kind", ["ambiguous_shape", "mismatched_narrative"])
def test_narrative_owner_recovery_fails_closed(
    failure_kind: str,
) -> None:
    page = _page(_rows(), owner="Thuyết minh báo cáo tài chính")
    page["sections"][0]["narratives_exact"] = [
        "30. Tiền và các khoản tương đương tiền"
    ]
    if failure_kind == "ambiguous_shape":
        page["sections"][0]["tables"].append(
            deepcopy(page["sections"][0]["tables"][0])
        )
    else:
        page["sections"][0]["narratives_exact"] = ["30. Khoản mục khác"]
    adapted, receipts = _adapt(page, _compiled())
    assert receipts == []
    assert adapted["accepted_clusters"] == []


@pytest.mark.parametrize(
    "failure_kind", ["mismatched_owner", "ambiguous", "reset", "nonterminal", "control"]
)
def test_local_owner_recovery_fails_closed_on_unsafe_shape(
    failure_kind: str,
) -> None:
    page = _page(_rows())
    compiled = _compiled()
    if failure_kind == "ambiguous":
        page["sections"][0]["tables"].append(deepcopy(page["sections"][0]["tables"][0]))
    elif failure_kind == "reset":
        page["sections"][0]["tables"][0]["rows"][-1]["label_exact"] = (
            "Tiền và các khoản tương đương tiền cuối kỳ"
        )
    elif failure_kind == "nonterminal":
        page["sections"][0]["tables"][0]["rows"].append(
            _row("Tiền mặt tại quỹ", "1", "1")
        )
    cluster = _force_unresolved(page, compiled)
    pages = {VERSION_ID: page}
    if failure_kind == "mismatched_owner":
        pages = {VERSION_ID: deepcopy(page)}
        pages[VERSION_ID]["sections"][0]["title_exact"] = "Khoản mục khác"
    elif failure_kind == "control":
        owner_item = next(
            item
            for item in cluster["declared_money_table_inventory"]
            if item["classification"]["owner_visible"] is True
        )
        owner_item["classification"]["typed_control_disposition"] = (
            "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
        )
        owner_item["classification"]["classification_id"] = (
            "gjmthfcv1:classification:" + "9" * 64
        )
        material = {
            key: value for key, value in cluster.items() if key != "cluster_id"
        }
        cluster["cluster_id"] = (
            "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
        )
    adapted, receipts = adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1(
        _indexed(cluster, compiled),
        page_json_by_document={1: pages},
        compiled_specs=compiled,
    )
    assert adapted["accepted_clusters"] == []
    assert receipts == []


def test_local_owner_selection_does_not_depend_on_money_values() -> None:
    compiled = _compiled()
    first, first_receipts = _adapt(_page(_rows(current_delta=0)), compiled)
    second, second_receipts = _adapt(_page(_rows(current_delta=7)), compiled)
    assert first["accepted_clusters"][0]["component_regions"] == (
        second["accepted_clusters"][0]["component_regions"]
    )
    assert first_receipts[0]["classification_id"] == second_receipts[0][
        "classification_id"
    ]


def test_primary_cash_flow_supplemental_detail_is_recovered_and_replayed() -> None:
    page = _primary_supplemental_page()
    compiled = _compiled()
    adapted, receipts = _adapt(page, compiled)
    assert len(receipts) == 1
    assert receipts[0]["format_version"].endswith(
        "PRIMARY_SUPPLEMENTAL_QUERY_RECEIPT_V1"
    )
    cluster = adapted["accepted_clusters"][0]
    assert cluster["component_regions"][0]["table_id"] == "t2"
    receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_cash_equivalents_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    adapter_receipt = candidate["closure_receipt"][
        "cash_equivalents_adapter_receipt"
    ]
    projections = adapter_receipt["primary_supplemental_projection_receipts"]
    assert len(projections) == 1
    assert projections[0]["before_page_status"] == "PRIMARY_FINANCIAL_STATEMENT"
    validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )


@pytest.mark.parametrize(
    "failure_kind", ["mismatched_owner", "ambiguous", "missing_anchor", "nonterminal"]
)
def test_primary_supplemental_recovery_fails_closed_on_unsafe_shape(
    failure_kind: str,
) -> None:
    page = _primary_supplemental_page()
    if failure_kind == "mismatched_owner":
        page["sections"][0]["tables"][1]["title_exact"] = "Khoản mục khác"
    elif failure_kind == "ambiguous":
        page["sections"][0]["tables"].append(
            deepcopy(page["sections"][0]["tables"][1])
        )
    elif failure_kind == "missing_anchor":
        page["sections"][0]["tables"][0]["rows"][-1]["label_exact"] = (
            "Số dư cuối kỳ khác"
        )
    else:
        page["sections"][0]["tables"][1]["rows"][-1]["row_kind"] = "ITEM"
    adapted, receipts = _adapt(page, _compiled())
    assert adapted["accepted_clusters"] == []
    assert receipts == []


def test_primary_supplemental_selection_is_value_independent() -> None:
    compiled = _compiled()
    first = _primary_supplemental_page()
    second = deepcopy(first)
    second["sections"][0]["tables"][1]["rows"][0]["values_exact"][0] = "999"
    first_adapted, first_receipts = _adapt(first, compiled)
    second_adapted, second_receipts = _adapt(second, compiled)
    assert first_adapted["accepted_clusters"][0]["component_regions"] == (
        second_adapted["accepted_clusters"][0]["component_regions"]
    )
    assert first_receipts[0]["rule"] == second_receipts[0]["rule"]


def test_primary_supplemental_projects_exact_adjacent_unit_and_period_prefix() -> None:
    compiled = _compiled()
    target = _primary_supplemental_page()
    target_table = target["sections"][0]["tables"][1]
    target_table["unit_exact"] = None
    target_table["columns"][0]["header_path_exact"] = [
        "Lũy kế từ đầu năm đến cuối quý này",
        "Năm nay",
    ]
    target_table["columns"][1]["header_path_exact"] = [
        "Lũy kế từ đầu năm đến cuối quý này",
        "Năm Trước",
    ]
    prior = _primary_supplemental_page()
    prior["sections"][0]["tables"] = [prior["sections"][0]["tables"][0]]
    prior_table = prior["sections"][0]["tables"][0]
    prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    prior_table["unit_exact"] = "Triệu đồng VN"
    prior_table["columns"][0]["header_path_exact"] = ["Năm nay"]
    prior_table["columns"][1]["header_path_exact"] = ["Năm Trước"]
    region = {
        "component_roles": ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": VERSION_ID,
        "physical_page": 2,
        "section_id": "s1",
        "selected_page_ordinal": 2,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t2",
    }
    receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1([region])
    projected, projections = _project_primary_supplemental_pages_v1(
        regions=[region],
        page_json_by_version={"gfpstorev1:json:" + "d" * 64: prior, VERSION_ID: target},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    projected_table = projected[VERSION_ID]["sections"][0]["tables"][1]
    assert projected_table["unit_exact"] == "Triệu đồng VN"
    assert [column["header_path_exact"] for column in projected_table["columns"]] == [
        ["Năm nay"],
        ["Năm Trước"],
    ]
    assert projections[0]["unit_projection"]["source_locator"]["physical_page"] == 1


@pytest.mark.parametrize("failure_kind", ["nonadjacent", "period_mismatch", "reset"])
def test_primary_supplemental_adjacent_unit_projection_fails_closed(
    failure_kind: str,
) -> None:
    compiled = _compiled()
    target = _primary_supplemental_page()
    target["sections"][0]["tables"][1]["unit_exact"] = None
    prior = _primary_supplemental_page()
    prior["sections"][0]["tables"] = [prior["sections"][0]["tables"][0]]
    prior_table = prior["sections"][0]["tables"][0]
    prior_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    prior_table["unit_exact"] = "Triệu đồng VN"
    if failure_kind == "period_mismatch":
        prior_table["columns"][0]["header_path_exact"] = ["Kỳ này"]
    elif failure_kind == "reset":
        prior_table["continuation"] = "NONE"
    physical_page = 3 if failure_kind == "nonadjacent" else 2
    region = {
        "component_roles": ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": VERSION_ID,
        "physical_page": physical_page,
        "section_id": "s1",
        "selected_page_ordinal": physical_page,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t2",
    }
    receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1([region])
    projected, projections = _project_primary_supplemental_pages_v1(
        regions=[region],
        page_json_by_version={"gfpstorev1:json:" + "d" * 64: prior, VERSION_ID: target},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert projected[VERSION_ID]["sections"][0]["tables"][1]["unit_exact"] is None
    assert projections[0]["unit_projection"] is None


def test_exact_ambiguous_vietnamese_period_pair_is_projected_and_restored() -> None:
    page = _page(
        _rows(), headers=("Số cuối kỳ này", "Số cuối kỳ trước")
    )
    compiled = _compiled()
    candidate, cluster, receipt = _evaluate(page, compiled)
    assert candidate["status"] == READY
    adapter_receipt = candidate["closure_receipt"][
        "cash_equivalents_adapter_receipt"
    ]
    assert len(adapter_receipt["header_projection_receipts"]) == 1
    assert candidate["closure_receipt"]["table_receipts"][0]["lane_axis"][
        "source_period_axis"
    ]["headers_exact"] == ["Số cuối kỳ này", "Số cuối kỳ trước"]
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"
    validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )


@pytest.mark.parametrize("failure_kind", ["swapped", "owner", "reset"])
def test_period_header_projection_rejects_non_exact_or_unowned_surfaces(
    failure_kind: str,
) -> None:
    page = _page(_rows(), headers=("Số cuối kỳ này", "Số cuối kỳ trước"))
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    if failure_kind == "swapped":
        columns = page["sections"][0]["tables"][0]["columns"]
        columns[0]["header_path_exact"], columns[1]["header_path_exact"] = (
            columns[1]["header_path_exact"],
            columns[0]["header_path_exact"],
        )
    elif failure_kind == "owner":
        page["sections"][0]["title_exact"] = "Khoản mục khác"
    else:
        page["sections"][0]["tables"][0]["title_exact"] = (
            "Tiền và các khoản tương đương tiền cuối kỳ"
        )
    query_receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1(
        cluster["component_regions"]
    )
    _pages, receipts = _project_ambiguous_period_headers_v1(
        regions=cluster["component_regions"],
        pages={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert receipts == []


def test_authenticated_visible_dash_repairs_only_the_exact_registered_cell() -> None:
    page = _page(_split_blank_rows())
    compiled = _compiled(_dash_repair_spec())
    candidate, cluster, receipt = _evaluate(page, compiled)
    assert candidate["status"] == READY
    securities = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "SECURITIES"
    )
    assert [cell["coefficient"] for cell in securities["values"]] == [0, 4]
    assert securities["values"][0]["source_text"] == "-"
    adapter_receipt = candidate["closure_receipt"][
        "cash_equivalents_adapter_receipt"
    ]
    assert len(adapter_receipt["authenticated_source_repairs"]) == 1
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"
    validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )


def test_unregistered_blank_is_never_promoted_from_matching_total() -> None:
    candidate, _cluster, _receipt = _evaluate(_page(_split_blank_rows()), _compiled())
    assert candidate["status"] == READY
    assert all(mapping["role"] != "FAMILY_ROOT_TOTAL" for mapping in candidate["mappings"])
    securities = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "SECURITIES"
    )
    assert securities["values"] == [
        {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
        {"coefficient": 4, "source_text": "4", "state": "RAW_SIGNED_INTEGER"},
    ]
    assert candidate["closure_receipt"]["cash_equivalents_adapter_receipt"][
        "partial_root_omission_receipt"
    ]["rule"].endswith("BLANKS_REMAIN_NULL")
    assert "INFERRED_BLANK_ZERO" not in json.dumps(candidate, ensure_ascii=False)
    audit = validate_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS"
    assert audit["partial_mapping_count"] == 1


def test_fully_observed_total_mismatch_cannot_use_partial_root_omission() -> None:
    rows = _rows()
    rows[-1]["values_exact"][0] = "61"
    candidate, _cluster, _receipt = _evaluate(_page(rows), _compiled())
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "cash_equivalents_adapter_receipt" not in candidate["closure_receipt"]


def test_source_repair_identity_and_before_image_tampering_fail_closed() -> None:
    repair_spec = _dash_repair_spec()
    tampered = deepcopy(repair_spec)
    tampered["repairs"][0]["locator"]["row_ordinal"] = 5
    with pytest.raises(GeminiJsonCashEquivalentsFamilyV1Error, match="identity drifted"):
        _compiled(tampered)

    page = _page(_split_blank_rows())
    page["sections"][0]["tables"][0]["rows"][5]["values_exact"][0] = "0"
    compiled = _compiled(repair_spec)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1(
        cluster["component_regions"]
    )
    with pytest.raises(GeminiJsonCashEquivalentsFamilyV1Error, match="before-image"):
        evaluate_gemini_json_cash_equivalents_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=compiled,
            query_receipt=receipt,
        )


def test_adapter_replay_rejects_mapping_tamper() -> None:
    page = _page(_rows(), headers=("Số cuối kỳ này", "Số cuối kỳ trước"))
    compiled = _compiled()
    candidate, cluster, receipt = _evaluate(page, compiled)
    tampered = deepcopy(candidate)
    tampered["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(GeminiJsonCashEquivalentsFamilyV1Error, match="replay drifted"):
        validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
            tampered,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=compiled,
            query_receipt=receipt,
        )
