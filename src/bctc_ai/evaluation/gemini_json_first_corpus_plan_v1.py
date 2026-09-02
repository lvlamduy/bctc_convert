"""Deterministic whole-document routing plan for Gemini JSON-first ingestion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_CORPUS_PLAN_V1"
GOOGLE_ROUTE = "GOOGLE_GEMINI_BATCH_API"
OPENROUTER_ROUTE = "OPENROUTER_VERTEX_FLEX"


class GeminiJsonFirstCorpusPlanV1Error(ValueError):
    """The corpus inventory or routing policy is not deterministic and exhaustive."""


def _error(message: str) -> GeminiJsonFirstCorpusPlanV1Error:
    return GeminiJsonFirstCorpusPlanV1Error(message)


def _document(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"relative_path", "source_sha256", "source_size_bytes", "page_count"}
    language_scope_fields = {"source_page_count", "page_selection"}
    if type(value) is not dict or set(value) not in {
        frozenset(required),
        frozenset(required | language_scope_fields),
    }:
        raise _error("corpus document fields drifted")
    relative_path = value["relative_path"]
    digest = value["source_sha256"]
    size = value["source_size_bytes"]
    pages = value["page_count"]
    if (
        type(relative_path) is not str
        or not relative_path
        or relative_path.startswith("/")
        or ".." in relative_path.split("/")
        or "\\" in relative_path
    ):
        raise _error("corpus document path is not one safe relative POSIX path")
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise _error("corpus document SHA-256 is invalid")
    if type(size) is not int or size <= 0 or type(pages) is not int or pages <= 0:
        raise _error("corpus document size or page count is invalid")
    if set(value) == required | language_scope_fields:
        source_pages = value["source_page_count"]
        selection = value["page_selection"]
        if (
            type(source_pages) is not int
            or source_pages < pages
            or type(selection) is not dict
            or set(selection)
            != {
                "included_first_physical_page",
                "included_last_physical_page",
                "review_basis",
                "selection_kind",
            }
            or selection["included_first_physical_page"] != 1
            or selection["included_last_physical_page"] != pages
            or selection["review_basis"] != "HUMAN_VISUAL_LANGUAGE_BOUNDARY"
            or selection["selection_kind"]
            not in {
                "FULL_DOCUMENT_VIETNAMESE",
                "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX",
            }
            or (selection["selection_kind"] == "FULL_DOCUMENT_VIETNAMESE" and pages != source_pages)
            or (
                selection["selection_kind"] == "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX"
                and pages >= source_pages
            )
        ):
            raise _error("corpus document language page selection is invalid")
    return canonical_clone_v1(dict(value))


def _openrouter_documents(
    documents: Sequence[dict[str, Any]], *, target_pages: int
) -> frozenset[str]:
    """Select one deterministic SHA-ranked whole-document prefix near the target."""

    ranked = sorted(documents, key=lambda item: (item["source_sha256"], item["relative_path"]))
    selected: list[str] = []
    total = 0
    for item in ranked:
        candidate = total + item["page_count"]
        if candidate <= target_pages or abs(candidate - target_pages) < abs(total - target_pages):
            selected.append(item["relative_path"])
            total = candidate
        if total >= target_pages:
            break
    return frozenset(selected)


def build_gemini_json_first_corpus_plan_v1(
    documents: Sequence[Mapping[str, Any]],
    *,
    dpi: int = 300,
    google_batch_chunk_pages: int = 30,
    openrouter_page_fraction: str = "0.20",
    openrouter_workers: int = 5,
) -> dict[str, Any]:
    """Build one exhaustive plan; a document never crosses provider contracts."""

    if not documents:
        raise _error("corpus plan requires at least one document")
    if dpi not in {200, 300}:
        raise _error("corpus render DPI must be 200 or 300")
    if (
        type(google_batch_chunk_pages) is not int
        or google_batch_chunk_pages <= 0
        or google_batch_chunk_pages > 100
    ):
        raise _error("Google batch chunk size lies outside 1..100 pages")
    if type(openrouter_workers) is not int or not 1 <= openrouter_workers <= 32:
        raise _error("OpenRouter worker count lies outside 1..32")
    try:
        fraction = float(openrouter_page_fraction)
    except (TypeError, ValueError) as exc:
        raise _error("OpenRouter page fraction is invalid") from exc
    if not 0.0 <= fraction <= 1.0:
        raise _error("OpenRouter page fraction lies outside 0..1")
    checked = [_document(item) for item in documents]
    paths = [item["relative_path"] for item in checked]
    if len(set(paths)) != len(paths):
        raise _error("corpus document paths must be unique")
    checked.sort(key=lambda item: item["relative_path"])
    total_pages = sum(item["page_count"] for item in checked)
    target_openrouter_pages = round(total_pages * fraction)
    openrouter_sources = _openrouter_documents(checked, target_pages=target_openrouter_pages)
    planned_documents = []
    task_count = 0
    route_pages = {GOOGLE_ROUTE: 0, OPENROUTER_ROUTE: 0}
    for item in checked:
        route = OPENROUTER_ROUTE if item["relative_path"] in openrouter_sources else GOOGLE_ROUTE
        if route == GOOGLE_ROUTE:
            tasks = [
                {
                    "first_physical_page": first,
                    "last_physical_page": min(
                        first + google_batch_chunk_pages - 1, item["page_count"]
                    ),
                    "route": route,
                    "task_kind": "GOOGLE_BATCH_CHUNK",
                }
                for first in range(1, item["page_count"] + 1, google_batch_chunk_pages)
            ]
        else:
            tasks = [
                {
                    "first_physical_page": 1,
                    "last_physical_page": item["page_count"],
                    "route": route,
                    "task_kind": "OPENROUTER_FLEX_DOCUMENT",
                    "workers": openrouter_workers,
                }
            ]
        for ordinal, task in enumerate(tasks, start=1):
            task["task_id"] = "gjfptaskv1:" + canonical_json_sha256_v1(
                {
                    "document": item,
                    "dpi": dpi,
                    "ordinal": ordinal,
                    "task": task,
                }
            )
        document_plan = {
            "document": item,
            "route": route,
            "tasks": tasks,
        }
        document_plan["document_plan_id"] = "gjfpdocv1:" + canonical_json_sha256_v1(document_plan)
        planned_documents.append(document_plan)
        route_pages[route] += item["page_count"]
        task_count += len(tasks)
    material = {
        "documents": planned_documents,
        "format_version": FORMAT_VERSION,
        "policy": {
            "dpi": dpi,
            "google_batch_chunk_pages": google_batch_chunk_pages,
            "openrouter_page_fraction": format(fraction, ".6f"),
            "openrouter_workers": openrouter_workers,
            "provider_partition": "WHOLE_DOCUMENT_ONLY",
        },
        "summary": {
            "document_count": len(planned_documents),
            "page_count": total_pages,
            "route_pages": route_pages,
            "task_count": task_count,
        },
    }
    return {
        **material,
        "corpus_plan_id": "gjfpcorpusv1:" + canonical_json_sha256_v1(material),
    }
