from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    GOOGLE_ROUTE,
    OPENROUTER_ROUTE,
    GeminiJsonFirstCorpusPlanV1Error,
    build_gemini_json_first_corpus_plan_v1,
)


def _documents() -> list[dict[str, object]]:
    return [
        {
            "relative_path": "MBB/2025/a.pdf",
            "source_sha256": "1" * 64,
            "source_size_bytes": 100,
            "page_count": 61,
        },
        {
            "relative_path": "VCB/2025/b.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 200,
            "page_count": 35,
        },
        {
            "relative_path": "VPB/2025/c.pdf",
            "source_sha256": "3" * 64,
            "source_size_bytes": 300,
            "page_count": 24,
        },
    ]


def test_plan_is_order_independent_and_covers_each_document_page_once() -> None:
    documents = _documents()
    plan = build_gemini_json_first_corpus_plan_v1(
        documents,
        openrouter_page_fraction="0.30",
        google_batch_chunk_pages=30,
        openrouter_workers=5,
    )
    assert plan == build_gemini_json_first_corpus_plan_v1(
        list(reversed(documents)),
        openrouter_page_fraction="0.30",
        google_batch_chunk_pages=30,
        openrouter_workers=5,
    )
    assert plan["summary"]["document_count"] == 3
    assert plan["summary"]["page_count"] == 120
    assert sum(plan["summary"]["route_pages"].values()) == 120
    assert set(plan["summary"]["route_pages"]) == {GOOGLE_ROUTE, OPENROUTER_ROUTE}
    seen = set()
    for document in plan["documents"]:
        routes = {task["route"] for task in document["tasks"]}
        assert routes == {document["route"]}
        page_count = document["document"]["page_count"]
        pages = []
        for task in document["tasks"]:
            pages.extend(range(task["first_physical_page"], task["last_physical_page"] + 1))
            assert task["task_id"] not in seen
            seen.add(task["task_id"])
        assert pages == list(range(1, page_count + 1))


def test_plan_identity_changes_with_source_or_execution_policy() -> None:
    first = build_gemini_json_first_corpus_plan_v1(_documents())
    changed = copy.deepcopy(_documents())
    changed[0]["source_sha256"] = "f" * 64
    assert (
        build_gemini_json_first_corpus_plan_v1(changed)["corpus_plan_id"] != first["corpus_plan_id"]
    )
    assert (
        build_gemini_json_first_corpus_plan_v1(_documents(), dpi=200)["corpus_plan_id"]
        != first["corpus_plan_id"]
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dpi": 150},
        {"google_batch_chunk_pages": 0},
        {"openrouter_page_fraction": "1.1"},
        {"openrouter_workers": 0},
    ],
)
def test_invalid_routing_policy_rejects(kwargs) -> None:
    with pytest.raises(GeminiJsonFirstCorpusPlanV1Error):
        build_gemini_json_first_corpus_plan_v1(_documents(), **kwargs)


def test_duplicate_source_bytes_are_distinct_filings_but_duplicate_path_rejects() -> None:
    duplicate_bytes = _documents()
    duplicate_bytes[1]["source_sha256"] = duplicate_bytes[0]["source_sha256"]
    assert build_gemini_json_first_corpus_plan_v1(duplicate_bytes)["summary"]["document_count"] == 3
    duplicated = _documents()
    same_path = copy.deepcopy(duplicated[0])
    same_path["source_sha256"] = "f" * 64
    duplicated.append(same_path)
    with pytest.raises(GeminiJsonFirstCorpusPlanV1Error, match="unique"):
        build_gemini_json_first_corpus_plan_v1(duplicated)
