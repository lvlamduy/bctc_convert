"""Authenticated, read-only access to the selected Gemini corpus.

The chain is: pinned corpus index (SHA) -> validated index -> per-document
append-only selection head -> content-addressed document manifest -> ordered
page JSON version ids -> original stored JSON replayed through the read-only
lossless loader. Loose JSON files, newest-version shortcuts and unselected
versions are never used. All SQL is batched through temporary selection tables
and every query is counted for the run manifest.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    load_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (
    load_income_tax_source_page_json_versions_v1,
)

SOURCE_ACCESS_VERSION = "PRIMARY_AUTHENTICATED_SOURCE_ACCESS_V1"


class PrimarySourceError(ValueError):
    """The selected corpus cannot be authenticated exactly."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise PrimarySourceError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class SourceMetrics:
    """Read-volume and latency counters reported in the run manifest."""

    sql_queries: int = 0
    rows_read: int = 0
    json_bytes_read: int = 0
    pages_loaded: int = 0
    stage_seconds: dict[str, float] = field(default_factory=dict)

    def timed(self, stage: str):
        metrics = self

        class _Timer:
            def __enter__(self):
                self.start = time.perf_counter()

            def __exit__(self, *exc):
                metrics.stage_seconds[stage] = metrics.stage_seconds.get(stage, 0.0) + (
                    time.perf_counter() - self.start
                )

        return _Timer()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sql_queries": self.sql_queries,
            "rows_read": self.rows_read,
            "json_bytes_read": self.json_bytes_read,
            "pages_loaded": self.pages_loaded,
            "stage_seconds": {key: round(value, 3) for key, value in sorted(self.stage_seconds.items())},
        }


@dataclass(frozen=True)
class SelectedPage:
    physical_page: int
    page_json_version_id: str
    page_id: str
    status: str
    image_sha256: str


@dataclass(frozen=True)
class SelectedDocument:
    ordinal: int
    relative_path: str
    source_sha256: str
    source_size_bytes: int
    page_count: int
    document_plan_id: str
    document_manifest_id: str
    selection_id: str
    pages: tuple[SelectedPage, ...]

    def identity(self) -> dict[str, Any]:
        return {
            "document_ordinal": self.ordinal,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_size_bytes": self.source_size_bytes,
            "page_count": self.page_count,
            "document_plan_id": self.document_plan_id,
            "document_manifest_id": self.document_manifest_id,
            "selection_id": self.selection_id,
        }


@dataclass(frozen=True)
class CorpusSelection:
    name: str
    root: Path
    index_path: Path
    index_sha256: str
    corpus_manifest_index_id: str
    db_path: Path
    db_sha256: str
    documents: tuple[SelectedDocument, ...]

    def identity(self) -> dict[str, Any]:
        return {
            "corpus_name": self.name,
            "index_relative_path": str(self.index_path.relative_to(self.root)),
            "index_sha256": self.index_sha256,
            "corpus_manifest_index_id": self.corpus_manifest_index_id,
            "database_sha256": self.db_sha256,
            "document_count": len(self.documents),
            "page_count": sum(len(document.pages) for document in self.documents),
        }


def load_corpus_selection_v1(
    *,
    name: str,
    root: Path,
    index_relative_path: str,
    expected_index_sha256: str,
    expected_db_sha256: str,
    verify_db_bytes: bool = True,
    metrics: SourceMetrics | None = None,
) -> CorpusSelection:
    """Authenticate the index, every selection head and every manifest."""

    metrics = metrics or SourceMetrics()
    index_path = root / index_relative_path
    raw = index_path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected_index_sha256, "corpus index SHA-256 drifted")
    index = validate_current_corpus_manifest_index_v1(json.loads(raw))
    db_ref = index["database_ref"]
    _require(db_ref["sha256"] == expected_db_sha256, "corpus index binds a different database")
    db_path = root / db_ref["path"]
    _require(db_path.is_file() and db_path.stat().st_size == db_ref["size_bytes"], "corpus database size drifted")
    if verify_db_bytes:
        with metrics.timed("authenticate_database_bytes"):
            _require(sha256_file(db_path) == expected_db_sha256, "corpus database SHA-256 drifted")
    documents = []
    with metrics.timed("authenticate_document_selections"):
        for document in index["documents"]:
            selection_path = Path(document["selection_ref"]["path"])
            document_root = root / selection_path.parent.parent
            loaded = load_current_document_manifest_selection_v1(
                document_root,
                document_plan_id=document["document_plan_id"],
                source_sha256=document["source_sha256"],
            )
            _require(loaded is not None, "document selection head is absent")
            head, manifest_path = loaded
            _require(
                head["selection_id"] == document["selection_id"]
                and head["document_manifest_id"] == document["document_manifest_id"]
                and manifest_path == root / document["document_manifest_ref"]["path"],
                "document selection head differs from the corpus index",
            )
            manifest = json.loads(manifest_path.read_bytes())
            pages = manifest.get("pages")
            _require(
                type(pages) is list and len(pages) == document["page_count"] == manifest.get("page_count"),
                "document manifest page axis drifted",
            )
            selected = tuple(
                SelectedPage(
                    physical_page=page["physical_page"],
                    page_json_version_id=page["page_json_version_id"],
                    page_id=page["page_id"],
                    status=page["status"],
                    image_sha256=page["image"]["sha256"],
                )
                for page in pages
            )
            _require(
                [page.physical_page for page in selected] == list(range(1, len(selected) + 1))
                and len({page.page_json_version_id for page in selected}) == len(selected),
                "document manifest page order or identity is invalid",
            )
            documents.append(
                SelectedDocument(
                    ordinal=document["source_ordinal"],
                    relative_path=document["relative_path"],
                    source_sha256=document["source_sha256"],
                    source_size_bytes=document["source_size_bytes"],
                    page_count=document["page_count"],
                    document_plan_id=document["document_plan_id"],
                    document_manifest_id=document["document_manifest_id"],
                    selection_id=document["selection_id"],
                    pages=selected,
                )
            )
    all_ids = [page.page_json_version_id for document in documents for page in document.pages]
    _require(len(all_ids) == len(set(all_ids)) == index["summary"]["page_count"], "corpus page frontier is not exact")
    return CorpusSelection(
        name=name,
        root=root,
        index_path=index_path,
        index_sha256=expected_index_sha256,
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        db_path=db_path,
        db_sha256=expected_db_sha256,
        documents=tuple(documents),
    )


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def selected_table_label_census_v1(
    db_path: Path, *, page_json_version_ids: Sequence[str], metrics: SourceMetrics
) -> list[dict[str, Any]]:
    """One batched query: section metadata and row labels of every selected table.

    This is the bounded whole-document scan used both to retrieve PRIMARY
    candidates and to prove that no primary-looking table outside the
    candidate set was left behind.
    """

    with closing(connect_readonly(db_path)) as connection:
        connection.execute(
            "CREATE TEMP TABLE primary_selected_page(ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO primary_selected_page VALUES (?,?)", enumerate(page_json_version_ids, 1)
        )
        rows = connection.execute(
            """
            SELECT s.page_json_version_id, n.section_id, n.source_order AS section_order,
                   n.content_kind, n.statement_type, t.table_id, t.source_order AS table_order,
                   r.source_order AS row_order, r.label_exact
            FROM primary_selected_page AS s
            JOIN section_node AS n ON n.page_json_version_id = s.page_json_version_id
            JOIN table_node AS t ON t.page_json_version_id = n.page_json_version_id AND t.section_id = n.section_id
            JOIN row_node AS r ON r.page_json_version_id = t.page_json_version_id
                 AND r.section_id = t.section_id AND r.table_id = t.table_id
            ORDER BY s.ordinal, n.source_order, t.source_order, r.source_order
            """
        ).fetchall()
    metrics.sql_queries += 1
    metrics.rows_read += len(rows)
    return [dict(row) for row in rows]


def selected_section_titles_v1(
    db_path: Path, *, page_json_version_ids: Sequence[str], metrics: SourceMetrics
) -> list[dict[str, Any]]:
    """Every selected section title (cover, statements, notes) for scope evidence."""

    with closing(connect_readonly(db_path)) as connection:
        connection.execute(
            "CREATE TEMP TABLE primary_selected_title_page(ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO primary_selected_title_page VALUES (?,?)", enumerate(page_json_version_ids, 1)
        )
        rows = connection.execute(
            """
            SELECT s.page_json_version_id, n.source_order AS section_order, n.content_kind,
                   n.statement_type, n.title_exact
            FROM primary_selected_title_page AS s
            JOIN section_node AS n ON n.page_json_version_id = s.page_json_version_id
            ORDER BY s.ordinal, n.source_order
            """
        ).fetchall()
    metrics.sql_queries += 1
    metrics.rows_read += len(rows)
    return [dict(row) for row in rows]


def load_original_pages_v1(
    db_path: Path, *, page_json_version_ids: Sequence[str], metrics: SourceMetrics, batch: int = 400
) -> dict[str, dict[str, Any]]:
    """Authenticated original JSON (provenance + CAS + lossless replay) by version id."""

    result: dict[str, dict[str, Any]] = {}
    ids = list(page_json_version_ids)
    for start in range(0, len(ids), batch):
        chunk = ids[start: start + batch]
        loaded = load_income_tax_source_page_json_versions_v1(db_path, page_json_version_ids=chunk)
        metrics.sql_queries += 3
        for item in loaded:
            receipt = item["source_json_replay_receipt"]
            metrics.json_bytes_read += receipt["canonical_json_size_bytes"]
            result[item["page_json_version_id"]] = item
        metrics.pages_loaded += len(loaded)
    _require(list(result) == ids, "authenticated page load order differs")
    return result
