from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from test_gemini_financial_page_json_v1 import _page

from bctc_ai.evaluation.gemini_json_first_provider_v1 import ProviderResultV1
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    merge_region_repair_v1,
    region_repair_targets_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    _family_anchor_lookup_forms_v1,
    _parents,
    _visual_state,
    build_financial_document_manifest_v1,
    document_page_extraction_frontier_v1,
    document_page_image_frontier_v1,
    extraction_cache_key_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    initialize_region_repair_extension_v1,
    load_page_json_versions_v1,
    lookup_cached_page_json_v1,
    page_json_region_repair_lineages_v1,
    query_family_anchor_regions_v1,
    query_selected_family_anchor_hits_v1,
    query_selected_family_anchor_regions_v1,
    record_page_json_region_repair_v1,
    selected_page_extraction_receipts_v1,
    usage_summary_v1,
)


def test_region_repair_lineage_is_database_bound_and_idempotent(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    base = _ingest(path)
    page = _page()
    targets = region_repair_targets_v1(page, target_ids=["s1:t1:r2"])
    merged, receipt = merge_region_repair_v1(
        page,
        base_page_json_version_id=base["page_json_version_id"],
        targets=targets,
        repair={
            "all_targets_transcribed": True,
            "rows": [
                {
                    "label_exact": targets[0]["label_exact"],
                    "target_id": "s1:t1:r2",
                    "values_exact": ["21", "11"],
                }
            ],
            "uncertainty_exact": [],
        },
    )
    repaired = _ingest(
        path,
        prompt_sha256="f" * 64,
        prompt_variant="region-repair",
        page_json=merged,
    )
    initialize_region_repair_extension_v1(path)
    lineage = record_page_json_region_repair_v1(
        path,
        merged_page_json_version_id=repaired["page_json_version_id"],
        receipt=receipt,
    )
    assert lineage["base_page_json_version_id"] == base["page_json_version_id"]
    assert (
        record_page_json_region_repair_v1(
            path,
            merged_page_json_version_id=repaired["page_json_version_id"],
            receipt=receipt,
        )
        == lineage
    )
    loaded = load_page_json_versions_v1(
        path,
        page_json_version_ids=[repaired["page_json_version_id"]],
    )
    assert loaded[0]["page_json"] == merged
    replayed = page_json_region_repair_lineages_v1(
        path, observed_page_json_version_ids=[repaired["page_json_version_id"]]
    )
    assert replayed == [
        {
            "base_page_json_version_id": base["page_json_version_id"],
            "canonical_merged_page_json_version_id": repaired["page_json_version_id"],
            "observed_page_json_version_id": repaired["page_json_version_id"],
            "repair_id": receipt["repair_id"],
            "repair_receipt": receipt,
            "repair_receipt_sha256": lineage["repair_receipt_sha256"],
        }
    ]


def test_family_anchor_lookup_forms_cover_harmless_financial_label_punctuation() -> None:
    forms = _family_anchor_lookup_forms_v1(
        [
            "Tiền vàng gửi tại các TCTD khác",
            "Tiền gửi không kỳ hạn 1",
            "Cho vay các TCTD khác bằng VND",
            "Chứng khoán Chính phủ chính quyền địa phương",
        ]
    )
    assert "iii. tien, vang gui tai cac tctd khac" in forms
    assert "tien gui khong ky han (1)" in forms
    assert 'cho vay cac ("tctd") khac bang vnd' in forms
    assert "7. cho vay cac tctd khac bang vnd" in forms
    assert "chung khoan chinh phu, chinh quyen dia phuong" in forms


@pytest.mark.parametrize("source", ["-", "–", "—", "_", " _ "])
def test_accounting_dash_glyphs_project_to_dash_without_raw_repair(source: str) -> None:
    assert _visual_state(source) == "DASH"


@pytest.mark.parametrize("source", ["__", "1_000", "_1", "ABC_"])
def test_embedded_underscore_never_projects_to_accounting_dash(source: str) -> None:
    assert _visual_state(source) == "VALUE"


def test_parent_projection_supports_trailing_subtotal_and_abstains_on_duplicates() -> None:
    trailing = [
        {"label_exact": "Con", "hierarchy_path_exact": ["Mẹ", "Con"]},
        {"label_exact": "Mẹ", "hierarchy_path_exact": ["Mẹ"]},
    ]
    assert _parents(trailing) == {"r1": "r2", "r2": None}
    duplicate = trailing + [
        {"label_exact": "Mẹ", "hierarchy_path_exact": ["Mẹ"]},
    ]
    assert _parents(duplicate)["r1"] is None


def _result() -> ProviderResultV1:
    usage = {
        "billing_disposition": "ESTIMATED_LIST_PRICE",
        "cached_input_tokens": 0,
        "estimated_cost_usd": "0.003937500000",
        "input_tokens": 5000,
        "output_tokens": 1000,
        "thought_tokens": 100,
        "total_tokens": 6100,
    }
    attempt = {
        "attempt_ordinal": 1,
        "credential_slot": "GOOGLE_SLOT_1",
        "elapsed_seconds": "12.300",
        "http_status": 200,
        "outcome": "COMPLETED",
        "provider": "GOOGLE_GEMINI_API",
        "usage": usage,
    }
    return ProviderResultV1(
        output_text=json.dumps(_page(), ensure_ascii=False),
        raw_response_bytes=b'{"provider":"response"}',
        provider_name="GOOGLE_GEMINI_API",
        provider_model="gemini-3.7-flash-001",
        service_tier="flex",
        attempts=(attempt,),
        usage=usage,
        response_id_sha256="a" * 64,
    )


def _ingest(
    path: Path,
    *,
    physical_page: int = 7,
    image_sha256: str = "c" * 64,
    render_dpi: int = 200,
    source_logical_name: str = "report.pdf",
    source_sha256: str = "b" * 64,
    prompt_sha256: str = "d" * 64,
    prompt_variant: str = "compact",
    provider_result: ProviderResultV1 | None = None,
    page_json: dict[str, object] | None = None,
) -> dict[str, str]:
    return ingest_financial_page_extraction_v1(
        path,
        document={
            "source_logical_name": source_logical_name,
            "source_sha256": source_sha256,
            "source_size_bytes": 123,
        },
        page={
            "physical_page": physical_page,
            "image_sha256": image_sha256,
            "image_size_bytes": 456,
            "pixel_width": 1654,
            "pixel_height": 2339,
            "render_dpi": render_dpi,
            "media_type": "image/png",
        },
        prompt_variant=prompt_variant,
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=prompt_sha256,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        thinking_level="low",
        provider_result=provider_result or _result(),
        page_json=page_json or _page(),
    )


def test_store_is_append_only_indexed_and_cache_addressed(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    assert path.stat().st_mode & 0o777 == 0o600
    ids = _ingest(path)
    assert all(value.startswith("gfpstorev1:") for value in ids.values())
    cache = extraction_cache_key_v1(
        source_sha256="b" * 64,
        source_logical_name="report.pdf",
        image_sha256="c" * 64,
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        thinking_level="low",
        prompt_variant="compact",
        output_contract_mode="JSON_SCHEMA",
    )
    assert cache != extraction_cache_key_v1(
        source_sha256="b" * 64,
        source_logical_name="different-filing.pdf",
        image_sha256="c" * 64,
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        thinking_level="low",
        prompt_variant="compact",
        output_contract_mode="JSON_SCHEMA",
    )
    assert lookup_cached_page_json_v1(path, cache) == _page()
    assert _ingest(path) == ids
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="different immutable content"):
        _ingest(path, provider_result=replace(_result(), raw_response_bytes=b'{"changed":true}'))
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM section_node").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM table_node").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM row_node").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM value_cell").fetchone()[0] == 6
        assert (
            connection.execute("SELECT raw_response_bytes FROM page_json_version").fetchone()[0]
            == b'{"provider":"response"}\n'
        )
        assert (
            connection.execute("SELECT parent_row_id FROM row_node WHERE row_id='r2'").fetchone()[0]
            == "r1"
        )


def test_identical_page_json_on_distinct_pages_has_distinct_bound_version_ids(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    first = _ingest(path)
    second = _ingest(path, physical_page=8, image_sha256="f" * 64)
    assert first["page_json_version_id"] != second["page_json_version_id"]
    with sqlite3.connect(path) as connection:
        records = connection.execute(
            "SELECT page_id, page_json_version_id, canonical_json_sha256 "
            "FROM page_json_version ORDER BY page_id"
        ).fetchall()
    assert len(records) == 2
    assert records[0][0] != records[1][0]
    assert records[0][1] != records[1][1]
    assert records[0][2] == records[1][2]


def test_two_and_three_anchor_sql_shortlist_and_usage_stats(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    ids = _ingest(path)
    assert query_family_anchor_regions_v1(
        path,
        anchor_aliases=[["Cho vay các TCKT"], ["Công ty Nhà nước"]],
    ) == [
        {
            "anchor_row_ids": [["r1"], ["r2"]],
            "page_json_version_id": ids["page_json_version_id"],
            "section_id": "s1",
            "table_id": "t1",
        }
    ]
    assert (
        query_family_anchor_regions_v1(
            path,
            anchor_aliases=[
                ["Cho vay các TCKT"],
                ["Công ty Nhà nước"],
                ["không có"],
            ],
        )
        == []
    )
    assert usage_summary_v1(path) == {
        "attempts": [
            {
                "provider": "GOOGLE_GEMINI_API",
                "credential_slot": "GOOGLE_SLOT_1",
                "outcome": "COMPLETED",
                "count": 1,
            }
        ],
        "cached_input_tokens": 0,
        "input_tokens": 5000,
        "output_tokens": 1000,
        "run_count": 1,
        "thought_tokens": 100,
        "total_cost_usd": "0.003937500000",
    }


def test_selected_family_query_excludes_retry_versions_and_returns_local_context(
    tmp_path,
) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    first = _ingest(path)
    retry = _ingest(path, prompt_sha256="f" * 64, prompt_variant="balanced")
    empty_page = {
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
        "sections": [],
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
    }
    context = _ingest(
        path,
        physical_page=8,
        image_sha256="1" * 64,
        page_json=empty_page,
    )
    three_anchor_page = deepcopy(_page())
    third_row = three_anchor_page["sections"][0]["tables"][0]["rows"][2]
    third_row["label_exact"] = "Tổng cộng"
    third_row["hierarchy_path_exact"] = ["Tổng cộng"]
    third = _ingest(
        path,
        physical_page=9,
        image_sha256="2" * 64,
        page_json=three_anchor_page,
    )
    marked_page = deepcopy(_page())
    for row, marker in zip(
        marked_page["sections"][0]["tables"][0]["rows"][:2],
        ("- ", "• "),
        strict=True,
    ):
        row["label_exact"] = marker + row["label_exact"]
        row["hierarchy_path_exact"] = [row["label_exact"]]
    marked = _ingest(
        path,
        physical_page=10,
        image_sha256="3" * 64,
        page_json=marked_page,
    )
    compound_page = deepcopy(_page())
    compound_rows = compound_page["sections"][0]["tables"][0]["rows"]
    compound_rows[0]["label_exact"] = "Tiền gửi tại NHNN - Bằng VND"
    compound_rows[0]["hierarchy_path_exact"] = [compound_rows[0]["label_exact"]]
    compound_rows[1]["label_exact"] = "Tiền gửi tại NHNNVN bằng ngoại tệ (i)"
    compound_rows[1]["hierarchy_path_exact"] = [compound_rows[1]["label_exact"]]
    compound = _ingest(
        path,
        physical_page=11,
        image_sha256="4" * 64,
        page_json=compound_page,
    )
    selected = [
        first["page_json_version_id"],
        context["page_json_version_id"],
        third["page_json_version_id"],
        marked["page_json_version_id"],
        compound["page_json_version_id"],
    ]

    two_anchor = query_selected_family_anchor_regions_v1(
        path,
        selected_page_json_version_ids=selected,
        anchor_aliases=[["Cho vay các TCKT"], ["Công ty Nhà nước"]],
    )
    assert [candidate["page_json_version_id"] for candidate in two_anchor] == [
        first["page_json_version_id"],
        third["page_json_version_id"],
        marked["page_json_version_id"],
    ]
    assert retry["page_json_version_id"] not in {
        candidate["page_json_version_id"] for candidate in two_anchor
    }
    assert [
        candidate["page_json_version_id"]
        for candidate in query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=selected,
            anchor_aliases=[
                ["Tiền gửi tại NHNN bằng VND"],
                ["Tiền gửi tại NHNNVN bằng ngoại tệ i"],
            ],
        )
    ] == [compound["page_json_version_id"]]
    assert two_anchor[0]["context_pages"] == [
        {"physical_page": 7, "page_json_version_id": first["page_json_version_id"]},
        {"physical_page": 8, "page_json_version_id": context["page_json_version_id"]},
    ]
    assert (
        query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=selected,
            anchor_aliases=[
                ["Cho vay các TCKT"],
                ["Công ty Nhà nước"],
                ["Tong cong"],
            ],
        )[0]["page_json_version_id"]
        == third["page_json_version_id"]
    )
    parent_title_page = deepcopy(_page())
    parent_title_page["sections"][0]["title_exact"] = "8.1 Chứng khoán kinh doanh"
    parent_title_page["sections"][0]["tables"][0]["rows"] = [
        parent_title_page["sections"][0]["tables"][0]["rows"][0]
    ]
    parent_title = _ingest(
        path,
        physical_page=12,
        image_sha256="5" * 64,
        page_json=parent_title_page,
    )
    assert query_selected_family_anchor_regions_v1(
        path,
        selected_page_json_version_ids=[parent_title["page_json_version_id"]],
        anchor_aliases=[
            ["Chứng khoán kinh doanh"],
            [parent_title_page["sections"][0]["tables"][0]["rows"][0]["label_exact"]],
        ],
        title_anchor_aliases=["Chứng khoán kinh doanh"],
    )[0]["anchor_row_ids"] == [
        ["__TITLE_ANCHOR__:1"],
        ["r1"],
    ]
    hits = query_selected_family_anchor_hits_v1(
        path,
        selected_page_json_version_ids=selected,
        anchor_aliases=["Cho vay các TCKT"],
    )
    assert [hit["page_json_version_id"] for hit in hits] == [
        first["page_json_version_id"],
        third["page_json_version_id"],
        marked["page_json_version_id"],
    ]
    assert retry["page_json_version_id"] not in {hit["page_json_version_id"] for hit in hits}


def test_stored_document_page_image_frontier_is_exact_and_ambiguous_safe(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    _ingest(path, render_dpi=300)
    _ingest(path, physical_page=8, image_sha256="1" * 64, render_dpi=300)
    assert document_page_image_frontier_v1(
        path,
        source_sha256="b" * 64,
        source_logical_name="report.pdf",
        expected_physical_pages=[7, 8],
        render_dpi=300,
    ) == {7: "c" * 64, 8: "1" * 64}

    _ingest(
        path,
        physical_page=8,
        image_sha256="2" * 64,
        prompt_sha256="e" * 64,
        render_dpi=300,
    )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="incomplete or ambiguous"):
        document_page_image_frontier_v1(
            path,
            source_sha256="b" * 64,
            source_logical_name="report.pdf",
            expected_physical_pages=[7, 8],
            render_dpi=300,
        )


def test_stored_document_extraction_frontier_binds_unique_prompt_per_page(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    _ingest(path, render_dpi=300, prompt_variant="simple")
    _ingest(
        path,
        physical_page=8,
        image_sha256="1" * 64,
        prompt_sha256="f" * 64,
        prompt_variant="scope",
        render_dpi=300,
    )
    assert document_page_extraction_frontier_v1(
        path,
        source_sha256="b" * 64,
        source_logical_name="report.pdf",
        expected_physical_pages=[7, 8],
        render_dpi=300,
    ) == {
        7: {
            "image_sha256": "c" * 64,
            "prompt_sha256": "d" * 64,
            "prompt_variant": "simple",
        },
        8: {
            "image_sha256": "1" * 64,
            "prompt_sha256": "f" * 64,
            "prompt_variant": "scope",
        },
    }

    _ingest(
        path,
        physical_page=8,
        image_sha256="1" * 64,
        prompt_sha256="9" * 64,
        prompt_variant="items",
        render_dpi=300,
    )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="incomplete or ambiguous"):
        document_page_extraction_frontier_v1(
            path,
            source_sha256="b" * 64,
            source_logical_name="report.pdf",
            expected_physical_pages=[7, 8],
            render_dpi=300,
        )


def test_selected_page_extraction_receipts_preserve_source_prompt_and_order(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    first = _ingest(path, render_dpi=300, prompt_variant="simple")
    second = _ingest(
        path,
        physical_page=8,
        image_sha256="1" * 64,
        prompt_sha256="f" * 64,
        prompt_variant="scope",
        render_dpi=300,
    )
    receipts = selected_page_extraction_receipts_v1(
        path,
        page_json_version_ids=[
            first["page_json_version_id"],
            second["page_json_version_id"],
        ],
    )
    assert [receipt["physical_page"] for receipt in receipts] == [7, 8]
    assert [receipt["prompt_variant"] for receipt in receipts] == ["simple", "scope"]
    assert [receipt["prompt_sha256"] for receipt in receipts] == ["d" * 64, "f" * 64]
    assert all(receipt["source_sha256"] == "b" * 64 for receipt in receipts)
    loaded = load_page_json_versions_v1(
        path,
        page_json_version_ids=[
            first["page_json_version_id"],
            second["page_json_version_id"],
        ],
    )
    assert [record["physical_page"] for record in loaded] == [7, 8]
    assert all(record["page_json"] == _page() for record in loaded)


def test_selected_family_query_fails_closed_on_invalid_frontier_or_anchor_assignment(
    tmp_path,
) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    first = _ingest(path)
    retry = _ingest(path, prompt_sha256="f" * 64, prompt_variant="balanced")
    second = _ingest(path, physical_page=8, image_sha256="1" * 64)

    assert (
        query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=[first["page_json_version_id"]],
            anchor_aliases=[["Cho vay các TCKT"], ["Cho vay các TCKT"]],
        )
        == []
    )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="repeats one physical page"):
        query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=[
                first["page_json_version_id"],
                retry["page_json_version_id"],
            ],
            anchor_aliases=[["Cho vay các TCKT"], ["Công ty Nhà nước"]],
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="corpus source/page order"):
        query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=[
                second["page_json_version_id"],
                first["page_json_version_id"],
            ],
            anchor_aliases=[["Cho vay các TCKT"], ["Công ty Nhà nước"]],
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="version is absent"):
        query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=["gfpstorev1:json:" + "0" * 64],
            anchor_aliases=[["Cho vay các TCKT"], ["Công ty Nhà nước"]],
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="frontier is invalid"):
        query_selected_family_anchor_regions_v1(
            path,
            selected_page_json_version_ids=["gfpstorev1:json:" + "z" * 64],
            anchor_aliases=[["Cho vay các TCKT"], ["Công ty Nhà nước"]],
        )


def test_store_refuses_overwrite_and_identity_tamper(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="overwrite"):
        initialize_gemini_financial_page_store_v1(path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE store_identity SET format_version='FORGED'")
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="identity drifted"):
        lookup_cached_page_json_v1(path, "missing")


def test_document_manifest_binds_exact_policy_page_frontier_and_usage(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    ids = _ingest(path)
    manifest = build_financial_document_manifest_v1(
        path,
        source_sha256="b" * 64,
        expected_physical_pages=[7],
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        selected_provider="GOOGLE_GEMINI_API",
    )
    assert manifest["document_manifest_id"].startswith("gfdmv1:manifest:")
    assert manifest["page_count"] == 1
    assert manifest["status_counts"] == {"FINANCIAL_NOTE_CONTENT": 1}
    assert manifest["pages"][0]["page_json_version_id"] == ids["page_json_version_id"]
    assert manifest["pages"][0]["content_counts"] == {
        "cell_count": 6,
        "row_count": 3,
        "section_count": 1,
        "table_count": 1,
    }
    assert manifest["totals"] == {
        "cached_input_tokens": 0,
        "cell_count": 6,
        "cost_usd": "0.003937500000",
        "input_tokens": 5000,
        "output_tokens": 1000,
        "row_count": 3,
        "section_count": 1,
        "table_count": 1,
        "thought_tokens": 100,
        "total_tokens": 6100,
    }
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            expected_physical_pages=[6, 7],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
        )


def test_document_manifest_disambiguates_byte_identical_logical_filings(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    first = _ingest(path, source_logical_name="first.pdf", image_sha256="1" * 64)
    second = _ingest(path, source_logical_name="second.pdf", image_sha256="2" * 64)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="not unique"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            expected_physical_pages=[7],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
        )
    selected = build_financial_document_manifest_v1(
        path,
        source_sha256="b" * 64,
        source_logical_name="second.pdf",
        expected_physical_pages=[7],
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        selected_provider="GOOGLE_GEMINI_API",
    )
    assert selected["document"]["source_logical_name"] == "second.pdf"
    assert selected["pages"][0]["page_json_version_id"] == second["page_json_version_id"]
    assert selected["pages"][0]["page_json_version_id"] != first["page_json_version_id"]


def test_document_manifest_can_bind_one_unique_route_per_page_for_typed_fallback(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    openrouter_result = replace(
        _result(),
        provider_name="Google",
        provider_model="google/gemini-3.7-flash",
        attempts=(
            {
                "attempt_ordinal": 1,
                "credential_slot": "OPENROUTER_SLOT_1",
                "elapsed_seconds": "10.000",
                "http_status": 200,
                "outcome": "COMPLETED",
                "provider": "OPENROUTER",
                "usage": _result().usage,
            },
        ),
    )
    _ingest(
        path,
        physical_page=7,
        image_sha256="c" * 64,
        provider_result=openrouter_result,
    )
    batch_result = replace(
        _result(),
        provider_name="GOOGLE_GEMINI_BATCH_API",
        provider_model="gemini-3.7-flash",
        service_tier="batch",
        attempts=(
            {
                "attempt_ordinal": 1,
                "credential_slot": "GOOGLE_SLOT_2",
                "elapsed_seconds": "30.000",
                "http_status": 200,
                "outcome": "COMPLETED_BATCH",
                "provider": "GOOGLE_GEMINI_BATCH_API",
                "usage": _result().usage,
            },
        ),
    )
    ingest_financial_page_extraction_v1(
        path,
        document={
            "source_logical_name": "report.pdf",
            "source_sha256": "b" * 64,
            "source_size_bytes": 123,
        },
        page={
            "physical_page": 8,
            "image_sha256": "f" * 64,
            "image_size_bytes": 456,
            "pixel_width": 1654,
            "pixel_height": 2339,
            "render_dpi": 200,
            "media_type": "image/png",
        },
        prompt_variant="compact",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="batch",
        thinking_level="low",
        provider_result=batch_result,
        page_json=_page(),
    )
    routes = [
        {"gateway": "GOOGLE_GEMINI_BATCH_API", "requested_service_tier": "batch"},
        {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
    ]
    manifest = build_financial_document_manifest_v1(
        path,
        source_sha256="b" * 64,
        source_logical_name="report.pdf",
        expected_physical_pages=[7, 8],
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        allowed_gateway_service_tiers=routes,
    )
    assert manifest["format_version"] == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V2"
    assert [page["provider_route"]["gateway"] for page in manifest["pages"]] == [
        "OPENROUTER",
        "GOOGLE_GEMINI_BATCH_API",
    ]

    _ingest(
        path,
        physical_page=8,
        image_sha256="f" * 64,
        provider_result=openrouter_result,
    )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            source_logical_name="report.pdf",
            expected_physical_pages=[7, 8],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            allowed_gateway_service_tiers=routes,
        )

    preferred = [routes[1], routes[0]]
    selected = build_financial_document_manifest_v1(
        path,
        source_sha256="b" * 64,
        source_logical_name="report.pdf",
        expected_physical_pages=[7, 8],
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        allowed_gateway_service_tiers=routes,
        preferred_gateway_service_tiers=preferred,
    )
    assert selected["extraction_contract"]["preferred_gateway_service_tiers"] == preferred
    assert [page["provider_route"]["gateway"] for page in selected["pages"]] == [
        "OPENROUTER",
        "OPENROUTER",
    ]

    with pytest.raises(GeminiFinancialPageStoreV1Error, match="route permutation"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            source_logical_name="report.pdf",
            expected_physical_pages=[7, 8],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            allowed_gateway_service_tiers=routes,
            preferred_gateway_service_tiers=[routes[1]],
        )


def test_document_manifest_v3_binds_one_explicit_prompt_hash_per_page(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    simple = _ingest(path, physical_page=7, image_sha256="c" * 64)
    items = _ingest(
        path,
        physical_page=8,
        image_sha256="f" * 64,
        prompt_sha256="9" * 64,
        prompt_variant="items",
    )
    prompt_frontier = {7: "d" * 64, 8: "9" * 64}
    manifest = build_financial_document_manifest_v1(
        path,
        source_sha256="b" * 64,
        source_logical_name="report.pdf",
        expected_physical_pages=[7, 8],
        prompt_sha256=prompt_frontier,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        selected_provider="GOOGLE_GEMINI_API",
    )
    assert manifest["format_version"] == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3"
    assert manifest["extraction_contract"]["page_prompt_sha256s"] == [
        {"physical_page": 7, "prompt_sha256": "d" * 64},
        {"physical_page": 8, "prompt_sha256": "9" * 64},
    ]
    assert [page["page_json_version_id"] for page in manifest["pages"]] == [
        simple["page_json_version_id"],
        items["page_json_version_id"],
    ]
    assert [page["prompt_sha256"] for page in manifest["pages"]] == [
        "d" * 64,
        "9" * 64,
    ]

    with pytest.raises(GeminiFinancialPageStoreV1Error, match="page prompt frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            source_logical_name="report.pdf",
            expected_physical_pages=[7, 8],
            prompt_sha256={7: "d" * 64},
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            source_logical_name="report.pdf",
            expected_physical_pages=[7, 8],
            prompt_sha256={7: "9" * 64, 8: "d" * 64},
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
        )


def test_document_manifest_v4_binds_one_exact_full_page_image_per_page(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    original = _ingest(path, image_sha256="c" * 64)
    expanded = _ingest(path, image_sha256="f" * 64)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            expected_physical_pages=[7],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
        )
    selected = build_financial_document_manifest_v1(
        path,
        source_sha256="b" * 64,
        expected_physical_pages=[7],
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        selected_provider="GOOGLE_GEMINI_API",
        page_image_sha256s={7: "f" * 64},
    )
    assert selected["format_version"] == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
    assert selected["extraction_contract"]["page_image_sha256s"] == [
        {"image_sha256": "f" * 64, "physical_page": 7}
    ]
    assert selected["pages"][0]["page_json_version_id"] == expanded["page_json_version_id"]
    assert selected["pages"][0]["page_json_version_id"] != original["page_json_version_id"]

    with pytest.raises(GeminiFinancialPageStoreV1Error, match="page image frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            expected_physical_pages=[7],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
            page_image_sha256s={},
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="frontier"):
        build_financial_document_manifest_v1(
            path,
            source_sha256="b" * 64,
            expected_physical_pages=[7],
            prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API",
            page_image_sha256s={7: "9" * 64},
        )
