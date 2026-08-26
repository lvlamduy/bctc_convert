from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from test_gemini_financial_page_json_v1 import _page

from bctc_ai.evaluation.gemini_json_first_provider_v1 import ProviderResultV1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    _parents,
    _visual_state,
    extraction_cache_key_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    lookup_cached_page_json_v1,
    query_family_anchor_regions_v1,
    usage_summary_v1,
)


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


def _ingest(path: Path) -> dict[str, str]:
    return ingest_financial_page_extraction_v1(
        path,
        document={
            "source_logical_name": "report.pdf",
            "source_sha256": "b" * 64,
            "source_size_bytes": 123,
        },
        page={
            "physical_page": 7,
            "image_sha256": "c" * 64,
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
        requested_service_tier="flex",
        thinking_level="low",
        provider_result=_result(),
        page_json=_page(),
    )


def test_store_is_append_only_indexed_and_cache_addressed(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    assert path.stat().st_mode & 0o777 == 0o600
    ids = _ingest(path)
    assert all(value.startswith("gfpstorev1:") for value in ids.values())
    cache = extraction_cache_key_v1(
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
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="already"):
        _ingest(path)
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


def test_store_refuses_overwrite_and_identity_tamper(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="overwrite"):
        initialize_gemini_financial_page_store_v1(path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE store_identity SET format_version='FORGED'")
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="identity drifted"):
        lookup_cached_page_json_v1(path, "missing")
