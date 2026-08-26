"""Immutable SQLite store for Gemini JSON-first financial pages."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    FORMAT_VERSION as PAGE_FORMAT_VERSION,
)
from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    SEARCH_NORMALIZATION_VERSION,
    normalize_search_text_v1,
    validate_financial_page_json_v1,
)
from bctc_ai.evaluation.gemini_json_first_batch_v1 import (
    BatchSubmissionV1,
    summarize_google_batch_operation_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import ProviderResultV1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_FINANCIAL_PAGE_STORE_V8"
DEFAULT_DATABASE_PATH = Path("data/local/gemini_financial_page_store_v1.sqlite3")


class GeminiFinancialPageStoreV1Error(RuntimeError):
    """The immutable store contract or its content binding was violated."""


def _error(message: str) -> GeminiFinancialPageStoreV1Error:
    return GeminiFinancialPageStoreV1Error(message)


_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE store_identity (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    format_version TEXT NOT NULL,
    page_format_version TEXT NOT NULL,
    search_normalization_version TEXT NOT NULL
) STRICT;
CREATE TABLE document (
    document_id TEXT PRIMARY KEY,
    source_sha256 TEXT NOT NULL,
    source_size_bytes INTEGER NOT NULL CHECK (source_size_bytes >= 0),
    source_logical_name TEXT NOT NULL,
    UNIQUE(source_sha256, source_size_bytes, source_logical_name)
) STRICT;
CREATE TABLE page (
    page_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES document(document_id),
    physical_page INTEGER NOT NULL CHECK (physical_page > 0),
    image_sha256 TEXT NOT NULL,
    image_size_bytes INTEGER NOT NULL CHECK (image_size_bytes > 0),
    pixel_width INTEGER NOT NULL CHECK (pixel_width > 0),
    pixel_height INTEGER NOT NULL CHECK (pixel_height > 0),
    render_dpi INTEGER NOT NULL CHECK (render_dpi IN (200, 300)),
    media_type TEXT NOT NULL CHECK (media_type IN ('image/png','image/jpeg')),
    UNIQUE(document_id, physical_page, image_sha256)
) STRICT;
CREATE TABLE extraction_run (
    extraction_run_id TEXT PRIMARY KEY,
    cache_key TEXT NOT NULL UNIQUE,
    page_id TEXT NOT NULL REFERENCES page(page_id),
    prompt_variant TEXT NOT NULL,
    output_contract_mode TEXT NOT NULL,
    prompt_sha256 TEXT NOT NULL,
    response_schema_sha256 TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    requested_service_tier TEXT NOT NULL,
    thinking_level TEXT NOT NULL,
    selected_provider TEXT NOT NULL,
    selected_model TEXT NOT NULL,
    selected_service_tier TEXT NOT NULL,
    response_id_sha256 TEXT NOT NULL,
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
    thought_tokens INTEGER NOT NULL CHECK (thought_tokens >= 0),
    cached_input_tokens INTEGER NOT NULL CHECK (cached_input_tokens >= 0),
    total_tokens INTEGER NOT NULL CHECK (total_tokens >= 0),
    cost_usd TEXT NOT NULL,
    cost_disposition TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'COMPLETE')
) STRICT;
CREATE TABLE provider_attempt (
    extraction_run_id TEXT NOT NULL REFERENCES extraction_run(extraction_run_id),
    attempt_ordinal INTEGER NOT NULL CHECK (attempt_ordinal > 0),
    provider TEXT NOT NULL,
    credential_slot TEXT NOT NULL,
    elapsed_seconds TEXT NOT NULL,
    http_status INTEGER,
    outcome TEXT NOT NULL,
    usage_json BLOB,
    PRIMARY KEY(extraction_run_id, attempt_ordinal)
) STRICT;
CREATE TABLE batch_job (
    batch_job_id TEXT PRIMARY KEY,
    provider_batch_name TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    credential_slot TEXT NOT NULL,
    display_name TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    requested_service_tier TEXT NOT NULL,
    request_count INTEGER NOT NULL CHECK (request_count > 0),
    submission_elapsed_seconds TEXT NOT NULL,
    submission_raw_sha256 TEXT NOT NULL,
    submission_raw_bytes BLOB NOT NULL
) STRICT;
CREATE TABLE batch_page_request (
    batch_job_id TEXT NOT NULL REFERENCES batch_job(batch_job_id),
    request_id TEXT NOT NULL,
    page_id TEXT NOT NULL REFERENCES page(page_id),
    cache_key TEXT NOT NULL,
    PRIMARY KEY(batch_job_id, request_id),
    UNIQUE(batch_job_id, page_id),
    UNIQUE(batch_job_id, cache_key)
) STRICT;
CREATE TABLE batch_event (
    batch_job_id TEXT NOT NULL REFERENCES batch_job(batch_job_id),
    event_ordinal INTEGER NOT NULL CHECK (event_ordinal > 0),
    state TEXT NOT NULL,
    done INTEGER NOT NULL CHECK (done IN (0,1)),
    request_count INTEGER NOT NULL CHECK (request_count >= 0),
    successful_request_count INTEGER NOT NULL CHECK (successful_request_count >= 0),
    failed_request_count INTEGER NOT NULL CHECK (failed_request_count >= 0),
    pending_request_count INTEGER NOT NULL CHECK (pending_request_count >= 0),
    raw_sha256 TEXT NOT NULL,
    raw_bytes BLOB NOT NULL,
    PRIMARY KEY(batch_job_id, event_ordinal),
    UNIQUE(batch_job_id, raw_sha256)
) STRICT;
CREATE TABLE batch_request_result (
    batch_job_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('INGESTED','FAILED')),
    extraction_run_id TEXT REFERENCES extraction_run(extraction_run_id),
    error_json BLOB,
    PRIMARY KEY(batch_job_id, request_id),
    FOREIGN KEY(batch_job_id, request_id)
      REFERENCES batch_page_request(batch_job_id, request_id),
    CHECK (
      (disposition='INGESTED' AND extraction_run_id IS NOT NULL AND error_json IS NULL)
      OR
      (disposition='FAILED' AND extraction_run_id IS NULL AND error_json IS NOT NULL)
    )
) STRICT;
CREATE TABLE page_json_version (
    page_json_version_id TEXT PRIMARY KEY,
    extraction_run_id TEXT NOT NULL UNIQUE REFERENCES extraction_run(extraction_run_id),
    page_id TEXT NOT NULL REFERENCES page(page_id),
    page_status TEXT NOT NULL,
    raw_response_sha256 TEXT NOT NULL,
    raw_response_bytes BLOB NOT NULL,
    canonical_json_sha256 TEXT NOT NULL,
    canonical_json_bytes BLOB NOT NULL
) STRICT;
CREATE TABLE section_node (
    page_json_version_id TEXT NOT NULL REFERENCES page_json_version(page_json_version_id),
    section_id TEXT NOT NULL,
    source_order INTEGER NOT NULL,
    content_kind TEXT NOT NULL,
    statement_type TEXT NOT NULL,
    title_exact TEXT,
    title_search_normalized TEXT,
    title_ascii_folded TEXT,
    narratives_json BLOB NOT NULL,
    PRIMARY KEY(page_json_version_id, section_id)
) STRICT;
CREATE TABLE table_node (
    page_json_version_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    table_id TEXT NOT NULL,
    source_order INTEGER NOT NULL,
    title_exact TEXT,
    title_search_normalized TEXT,
    title_ascii_folded TEXT,
    unit_exact TEXT,
    continuation TEXT NOT NULL,
    PRIMARY KEY(page_json_version_id, section_id, table_id),
    FOREIGN KEY(page_json_version_id, section_id)
      REFERENCES section_node(page_json_version_id, section_id)
) STRICT;
CREATE TABLE column_node (
    page_json_version_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    table_id TEXT NOT NULL,
    column_id TEXT NOT NULL,
    column_ordinal INTEGER NOT NULL,
    header_path_exact_json BLOB NOT NULL,
    value_kind TEXT NOT NULL,
    PRIMARY KEY(page_json_version_id, section_id, table_id, column_id),
    FOREIGN KEY(page_json_version_id, section_id, table_id)
      REFERENCES table_node(page_json_version_id, section_id, table_id)
) STRICT;
CREATE TABLE row_node (
    page_json_version_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    table_id TEXT NOT NULL,
    row_id TEXT NOT NULL,
    source_order INTEGER NOT NULL,
    label_exact TEXT,
    label_search_normalized TEXT,
    label_ascii_folded TEXT,
    hierarchy_path_exact_json BLOB NOT NULL,
    row_kind TEXT NOT NULL,
    parent_row_id TEXT,
    previous_row_id TEXT,
    next_row_id TEXT,
    PRIMARY KEY(page_json_version_id, section_id, table_id, row_id),
    FOREIGN KEY(page_json_version_id, section_id, table_id)
      REFERENCES table_node(page_json_version_id, section_id, table_id)
) STRICT;
CREATE TABLE value_cell (
    page_json_version_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    table_id TEXT NOT NULL,
    row_id TEXT NOT NULL,
    column_id TEXT NOT NULL,
    source_text TEXT,
    visual_state TEXT NOT NULL CHECK (visual_state IN ('BLANK','DASH','PRINTED_ZERO','VALUE')),
    PRIMARY KEY(page_json_version_id, section_id, table_id, row_id, column_id),
    FOREIGN KEY(page_json_version_id, section_id, table_id, row_id)
      REFERENCES row_node(page_json_version_id, section_id, table_id, row_id),
    FOREIGN KEY(page_json_version_id, section_id, table_id, column_id)
      REFERENCES column_node(page_json_version_id, section_id, table_id, column_id)
) STRICT;
CREATE INDEX idx_page_document_order ON page(document_id, physical_page);
CREATE INDEX idx_page_status ON page_json_version(page_status, page_id);
CREATE INDEX idx_section_kind ON section_node(content_kind, statement_type);
CREATE INDEX idx_table_title_normalized ON table_node(title_search_normalized);
CREATE INDEX idx_table_title_ascii ON table_node(title_ascii_folded);
CREATE INDEX idx_row_label_normalized ON row_node(label_search_normalized);
CREATE INDEX idx_row_label_ascii ON row_node(label_ascii_folded);
CREATE INDEX idx_row_local_order ON row_node(page_json_version_id, section_id, table_id, source_order);
CREATE INDEX idx_cell_source_text ON value_cell(source_text);
CREATE INDEX idx_batch_request_page ON batch_page_request(page_id, batch_job_id);
CREATE INDEX idx_batch_event_state ON batch_event(state, batch_job_id, event_ordinal);
CREATE INDEX idx_batch_result_disposition ON batch_request_result(disposition, batch_job_id);
"""


def initialize_gemini_financial_page_store_v1(path: Path) -> None:
    """Create a new store atomically; refuse replacement of any existing path."""

    destination = path.resolve()
    if destination.exists():
        raise _error("refusing to overwrite an existing Gemini page store")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(
        prefix=destination.name + ".stage-", suffix=".sqlite3", dir=destination.parent
    )
    os.close(descriptor)
    stage = Path(stage_name)
    try:
        with sqlite3.connect(stage) as connection:
            connection.executescript(_SCHEMA)
            connection.execute(
                "INSERT INTO store_identity VALUES (1, ?, ?, ?)",
                (FORMAT_VERSION, PAGE_FORMAT_VERSION, SEARCH_NORMALIZATION_VERSION),
            )
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.commit()
        os.chmod(stage, 0o600)
        os.replace(stage, destination)
    finally:
        if stage.exists():
            stage.unlink()


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if not path.is_file():
        raise _error("Gemini page store is absent")
    uri = f"file:{path.resolve()}?mode={'ro' if readonly else 'rw'}"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    identity = connection.execute("SELECT * FROM store_identity WHERE singleton=1").fetchone()
    expected = (FORMAT_VERSION, PAGE_FORMAT_VERSION, SEARCH_NORMALIZATION_VERSION)
    if identity is None or tuple(identity)[1:] != expected:
        connection.close()
        raise _error("Gemini page store identity drifted")
    return connection


def extraction_cache_key_v1(
    *,
    source_sha256: str,
    source_logical_name: str,
    image_sha256: str,
    prompt_sha256: str,
    response_schema_sha256: str,
    requested_model: str,
    requested_service_tier: str,
    thinking_level: str,
    prompt_variant: str,
    output_contract_mode: str,
) -> str:
    material = {
        "format_version": FORMAT_VERSION,
        "source_logical_name": source_logical_name,
        "source_sha256": source_sha256,
        "image_sha256": image_sha256,
        "prompt_sha256": prompt_sha256,
        "prompt_variant": prompt_variant,
        "output_contract_mode": output_contract_mode,
        "requested_model": requested_model,
        "requested_service_tier": requested_service_tier,
        "response_schema_sha256": response_schema_sha256,
        "thinking_level": thinking_level,
    }
    return "gfpstorev1:cache:" + canonical_json_sha256_v1(material)


def _source_identities(document: Mapping[str, Any], page: Mapping[str, Any]) -> tuple[str, str]:
    required_document = {"source_logical_name", "source_sha256", "source_size_bytes"}
    required_page = {
        "physical_page",
        "image_sha256",
        "image_size_bytes",
        "pixel_width",
        "pixel_height",
        "render_dpi",
        "media_type",
    }
    if set(document) != required_document or set(page) != required_page:
        raise _error("document or page input fields drifted")
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(dict(document))
    page_id = "gfpstorev1:page:" + canonical_json_sha256_v1(
        {"document_id": document_id, **dict(page)}
    )
    return document_id, page_id


def _insert_source_rows(
    connection: sqlite3.Connection,
    *,
    document: Mapping[str, Any],
    page: Mapping[str, Any],
) -> tuple[str, str]:
    document_id, page_id = _source_identities(document, page)
    connection.execute(
        "INSERT OR IGNORE INTO document VALUES (?,?,?,?)",
        (
            document_id,
            document["source_sha256"],
            document["source_size_bytes"],
            document["source_logical_name"],
        ),
    )
    connection.execute(
        "INSERT OR IGNORE INTO page VALUES (?,?,?,?,?,?,?,?,?)",
        (
            page_id,
            document_id,
            page["physical_page"],
            page["image_sha256"],
            page["image_size_bytes"],
            page["pixel_width"],
            page["pixel_height"],
            page["render_dpi"],
            page["media_type"],
        ),
    )
    return document_id, page_id


def lookup_cached_page_json_v1(path: Path, cache_key: str) -> dict[str, Any] | None:
    """Return the exact prior canonical page JSON, or None before any provider call."""

    with _connect(path, readonly=True) as connection:
        row = connection.execute(
            """
            SELECT p.canonical_json_bytes
            FROM extraction_run AS r
            JOIN page_json_version AS p USING (extraction_run_id)
            WHERE r.cache_key=? AND r.status='COMPLETE'
            """,
            (cache_key,),
        ).fetchone()
    if row is None:
        return None
    return validate_financial_page_json_v1(json.loads(bytes(row[0])))


def _text_projection(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    projection = normalize_search_text_v1(value)
    return projection["text_search_normalized"], projection["text_ascii_folded"]


def _visual_state(source: str | None) -> str:
    if source is None:
        return "BLANK"
    compact = source.replace(" ", "")
    # Gemini Batch occasionally renders one isolated accounting dash as an
    # underscore.  Preserve the raw source byte-for-byte, but project that
    # single glyph as DASH so downstream arithmetic may treat it as zero.  Do
    # not generalize to strings containing underscores: those stay VALUE.
    if compact in {"-", "–", "—", "_"}:
        return "DASH"
    zero_candidate = compact.strip("()")
    if zero_candidate.startswith("-"):
        zero_candidate = zero_candidate[1:]
    if zero_candidate and set(zero_candidate.replace(".", "").replace(",", "")) == {"0"}:
        return "PRINTED_ZERO"
    return "VALUE"


def _parents(rows: Sequence[Mapping[str, Any]]) -> dict[str, str | None]:
    """Resolve only one exact hierarchy-path parent, regardless of printed order."""

    result: dict[str, str | None] = {}
    for index, row in enumerate(rows):
        row_id = f"r{index + 1}"
        path = row["hierarchy_path_exact"]
        parent_label = path[-2] if len(path) > 1 else None
        candidates = [
            candidate_index
            for candidate_index, candidate in enumerate(rows)
            if candidate_index != index
            and candidate["label_exact"] == parent_label
            and candidate["hierarchy_path_exact"] == path[:-1]
        ]
        result[row_id] = f"r{candidates[0] + 1}" if len(candidates) == 1 else None
    return result


def ingest_financial_page_extraction_v1(
    path: Path,
    *,
    document: Mapping[str, Any],
    page: Mapping[str, Any],
    prompt_variant: str,
    output_contract_mode: str,
    prompt_sha256: str,
    response_schema_sha256: str,
    requested_model: str,
    requested_service_tier: str,
    thinking_level: str,
    provider_result: ProviderResultV1,
    page_json: Any,
) -> dict[str, str]:
    """Append one complete immutable extraction and all indexed projections."""

    checked = validate_financial_page_json_v1(page_json)
    document_id, page_id = _source_identities(document, page)
    cache_key = extraction_cache_key_v1(
        source_sha256=document["source_sha256"],
        source_logical_name=document["source_logical_name"],
        image_sha256=page["image_sha256"],
        prompt_sha256=prompt_sha256,
        response_schema_sha256=response_schema_sha256,
        requested_model=requested_model,
        requested_service_tier=requested_service_tier,
        thinking_level=thinking_level,
        prompt_variant=prompt_variant,
        output_contract_mode=output_contract_mode,
    )
    canonical_bytes = canonical_json_bytes_v1(checked) + b"\n"
    raw_bytes = provider_result.raw_response_bytes
    if not raw_bytes.endswith(b"\n"):
        raw_bytes += b"\n"
    usage = provider_result.usage
    cost = usage.get("actual_cost_usd", usage.get("estimated_cost_usd"))
    if type(cost) is not str:
        raise _error("provider usage has no exact cost string")
    run_material = {
        "attempts": list(provider_result.attempts),
        "cache_key": cache_key,
        "page_id": page_id,
        "provider_model": provider_result.provider_model,
        "provider_name": provider_result.provider_name,
        "raw_response_sha256": sha256(raw_bytes).hexdigest(),
        "response_id_sha256": provider_result.response_id_sha256,
        "usage": usage,
    }
    extraction_run_id = "gfpstorev1:run:" + canonical_json_sha256_v1(run_material)
    page_json_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
        {
            "canonical_json_sha256": sha256(canonical_bytes).hexdigest(),
            "extraction_run_id": extraction_run_id,
            "page_id": page_id,
        }
    )
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM extraction_run WHERE cache_key=?", (cache_key,)
        ).fetchone():
            raise _error("cache key already has a complete immutable extraction")
        inserted_document_id, inserted_page_id = _insert_source_rows(
            connection, document=document, page=page
        )
        if (inserted_document_id, inserted_page_id) != (document_id, page_id):
            raise _error("document or page identity changed inside transaction")
        connection.execute(
            "INSERT INTO extraction_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                extraction_run_id,
                cache_key,
                page_id,
                prompt_variant,
                output_contract_mode,
                prompt_sha256,
                response_schema_sha256,
                requested_model,
                requested_service_tier,
                thinking_level,
                provider_result.provider_name,
                provider_result.provider_model,
                provider_result.service_tier,
                provider_result.response_id_sha256,
                usage["input_tokens"],
                usage["output_tokens"],
                usage["thought_tokens"],
                usage["cached_input_tokens"],
                usage["total_tokens"],
                cost,
                usage["billing_disposition"],
                "COMPLETE",
            ),
        )
        for attempt in provider_result.attempts:
            connection.execute(
                "INSERT INTO provider_attempt VALUES (?,?,?,?,?,?,?,?)",
                (
                    extraction_run_id,
                    attempt["attempt_ordinal"],
                    attempt["provider"],
                    attempt["credential_slot"],
                    attempt["elapsed_seconds"],
                    attempt["http_status"],
                    attempt["outcome"],
                    (
                        canonical_json_bytes_v1(attempt["usage"])
                        if attempt["usage"] is not None
                        else None
                    ),
                ),
            )
        connection.execute(
            "INSERT INTO page_json_version VALUES (?,?,?,?,?,?,?,?)",
            (
                page_json_version_id,
                extraction_run_id,
                page_id,
                checked["status"],
                sha256(raw_bytes).hexdigest(),
                raw_bytes,
                sha256(canonical_bytes).hexdigest(),
                canonical_bytes,
            ),
        )
        for section_index, section in enumerate(checked["sections"]):
            section_id = f"s{section_index + 1}"
            section_normalized, section_folded = _text_projection(section["title_exact"])
            connection.execute(
                "INSERT INTO section_node VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    page_json_version_id,
                    section_id,
                    section_index,
                    section["content_kind"],
                    section["statement_type"],
                    section["title_exact"],
                    section_normalized,
                    section_folded,
                    canonical_json_bytes_v1(section["narratives_exact"]),
                ),
            )
            for table_index, table in enumerate(section["tables"]):
                table_id = f"t{table_index + 1}"
                table_normalized, table_folded = _text_projection(table["title_exact"])
                connection.execute(
                    "INSERT INTO table_node VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        page_json_version_id,
                        section_id,
                        table_id,
                        table_index,
                        table["title_exact"],
                        table_normalized,
                        table_folded,
                        table["unit_exact"],
                        table["continuation"],
                    ),
                )
                for column_index, column in enumerate(table["columns"]):
                    column_id = f"c{column_index + 1}"
                    connection.execute(
                        "INSERT INTO column_node VALUES (?,?,?,?,?,?,?)",
                        (
                            page_json_version_id,
                            section_id,
                            table_id,
                            column_id,
                            column_index,
                            canonical_json_bytes_v1(column["header_path_exact"]),
                            column["value_kind"],
                        ),
                    )
                parents = _parents(table["rows"])
                for row_index, row in enumerate(table["rows"]):
                    row_id = f"r{row_index + 1}"
                    normalized, folded = _text_projection(row["label_exact"])
                    previous = f"r{row_index}" if row_index else None
                    following = f"r{row_index + 2}" if row_index + 1 < len(table["rows"]) else None
                    connection.execute(
                        "INSERT INTO row_node VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            page_json_version_id,
                            section_id,
                            table_id,
                            row_id,
                            row_index,
                            row["label_exact"],
                            normalized,
                            folded,
                            canonical_json_bytes_v1(row["hierarchy_path_exact"]),
                            row["row_kind"],
                            parents[row_id],
                            previous,
                            following,
                        ),
                    )
                    for column_index, source in enumerate(row["values_exact"]):
                        connection.execute(
                            "INSERT INTO value_cell VALUES (?,?,?,?,?,?,?)",
                            (
                                page_json_version_id,
                                section_id,
                                table_id,
                                row_id,
                                f"c{column_index + 1}",
                                source,
                                _visual_state(source),
                            ),
                        )
        connection.commit()
    return {
        "cache_key": cache_key,
        "document_id": document_id,
        "extraction_run_id": extraction_run_id,
        "page_id": page_id,
        "page_json_version_id": page_json_version_id,
    }


def register_batch_submission_v1(
    path: Path,
    *,
    submission: BatchSubmissionV1,
    display_name: str,
    requests: Sequence[Mapping[str, Any]],
    prompt_variant: str,
    output_contract_mode: str,
    prompt_sha256: str,
    response_schema_sha256: str,
    requested_model: str,
    thinking_level: str,
    provider: str = "GOOGLE_GEMINI_BATCH_API",
    requested_service_tier: str = "batch",
    operation_summary: Mapping[str, Any] | None = None,
) -> str:
    """Register one submitted batch and every document/page request before polling."""

    if not requests:
        raise _error("batch submission has no page requests")
    request_ids = [request.get("request_id") for request in requests]
    if any(type(value) is not str or not value for value in request_ids):
        raise _error("batch request ID is invalid")
    if len(set(request_ids)) != len(request_ids):
        raise _error("batch request IDs must be unique")
    summary = (
        dict(operation_summary)
        if operation_summary is not None
        else summarize_google_batch_operation_v1(submission.raw_response_bytes)
    )
    required_summary = {
        "batch_name",
        "done",
        "failed_request_count",
        "pending_request_count",
        "request_count",
        "state",
        "successful_request_count",
    }
    if set(summary) != required_summary:
        raise _error("batch operation summary fields drifted")
    if summary["batch_name"] != submission.batch_name or summary["state"] != submission.state:
        raise _error("batch submission receipt identity drifted")
    if summary["request_count"] not in {0, len(requests)}:
        raise _error("batch submission request count drifted")
    raw = submission.raw_response_bytes
    if not raw.endswith(b"\n"):
        raw += b"\n"
    batch_job_id = "gfpstorev1:batch:" + canonical_json_sha256_v1(
        {
            "batch_name": submission.batch_name,
            "credential_slot": submission.credential_slot,
            "raw_sha256": sha256(raw).hexdigest(),
        }
    )
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM batch_job WHERE provider_batch_name=?", (submission.batch_name,)
        ).fetchone():
            raise _error("batch submission is already registered")
        connection.execute(
            "INSERT INTO batch_job VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                batch_job_id,
                submission.batch_name,
                provider,
                submission.credential_slot,
                display_name,
                requested_model,
                requested_service_tier,
                len(requests),
                submission.elapsed_seconds,
                sha256(raw).hexdigest(),
                raw,
            ),
        )
        for request in requests:
            if set(request) != {"request_id", "document", "page"}:
                raise _error("batch page request fields drifted")
            _, page_id = _insert_source_rows(
                connection, document=request["document"], page=request["page"]
            )
            cache_key = extraction_cache_key_v1(
                source_sha256=request["document"]["source_sha256"],
                source_logical_name=request["document"]["source_logical_name"],
                image_sha256=request["page"]["image_sha256"],
                prompt_sha256=prompt_sha256,
                response_schema_sha256=response_schema_sha256,
                requested_model=requested_model,
                requested_service_tier=requested_service_tier,
                thinking_level=thinking_level,
                prompt_variant=prompt_variant,
                output_contract_mode=output_contract_mode,
            )
            connection.execute(
                "INSERT INTO batch_page_request VALUES (?,?,?,?)",
                (batch_job_id, request["request_id"], page_id, cache_key),
            )
        connection.execute(
            "INSERT INTO batch_event VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                batch_job_id,
                1,
                summary["state"],
                int(summary["done"]),
                len(requests),
                summary["successful_request_count"],
                summary["failed_request_count"],
                summary["pending_request_count"] or len(requests),
                sha256(raw).hexdigest(),
                raw,
            ),
        )
        connection.commit()
    return batch_job_id


def record_batch_poll_v1(
    path: Path,
    *,
    raw_operation_bytes: bytes,
    operation_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one immutable batch-state observation and return its compact summary."""

    summary = (
        dict(operation_summary)
        if operation_summary is not None
        else summarize_google_batch_operation_v1(raw_operation_bytes)
    )
    if set(summary) != {
        "batch_name",
        "done",
        "failed_request_count",
        "pending_request_count",
        "request_count",
        "state",
        "successful_request_count",
    }:
        raise _error("batch operation summary fields drifted")
    raw = raw_operation_bytes
    if not raw.endswith(b"\n"):
        raw += b"\n"
    raw_sha = sha256(raw).hexdigest()
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        job = connection.execute(
            "SELECT batch_job_id, request_count FROM batch_job WHERE provider_batch_name=?",
            (summary["batch_name"],),
        ).fetchone()
        if job is None:
            raise _error("polled batch is not registered")
        if summary["request_count"] != job["request_count"]:
            raise _error("polled batch request count drifted")
        existing = connection.execute(
            "SELECT event_ordinal FROM batch_event WHERE batch_job_id=? AND raw_sha256=?",
            (job["batch_job_id"], raw_sha),
        ).fetchone()
        if existing is None:
            ordinal = connection.execute(
                "SELECT COALESCE(MAX(event_ordinal),0)+1 FROM batch_event WHERE batch_job_id=?",
                (job["batch_job_id"],),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO batch_event VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    job["batch_job_id"],
                    ordinal,
                    summary["state"],
                    int(summary["done"]),
                    summary["request_count"],
                    summary["successful_request_count"],
                    summary["failed_request_count"],
                    summary["pending_request_count"],
                    raw_sha,
                    raw,
                ),
            )
        connection.commit()
    return summary


def record_batch_request_result_v1(
    path: Path,
    *,
    batch_name: str,
    request_id: str,
    disposition: str,
    extraction_run_id: str | None = None,
    error: Mapping[str, Any] | None = None,
) -> None:
    """Seal one page as ingested or failed; refuse replacement of a final result."""

    if disposition not in {"INGESTED", "FAILED"}:
        raise _error("batch request disposition is invalid")
    if disposition == "INGESTED" and (not extraction_run_id or error is not None):
        raise _error("ingested batch result fields drifted")
    if disposition == "FAILED" and (extraction_run_id is not None or error is None):
        raise _error("failed batch result fields drifted")
    error_bytes = canonical_json_bytes_v1(dict(error)) if error is not None else None
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT j.batch_job_id, r.page_id, r.cache_key
            FROM batch_job AS j
            JOIN batch_page_request AS r USING (batch_job_id)
            WHERE j.provider_batch_name=? AND r.request_id=?
            """,
            (batch_name, request_id),
        ).fetchone()
        if row is None:
            raise _error("batch page request is not registered")
        if disposition == "INGESTED":
            run = connection.execute(
                "SELECT page_id, cache_key FROM extraction_run WHERE extraction_run_id=?",
                (extraction_run_id,),
            ).fetchone()
            if run is None or (run["page_id"], run["cache_key"]) != (
                row["page_id"],
                row["cache_key"],
            ):
                raise _error("batch extraction does not bind to its registered page/cache")
        try:
            connection.execute(
                "INSERT INTO batch_request_result VALUES (?,?,?,?,?)",
                (
                    row["batch_job_id"],
                    request_id,
                    disposition,
                    extraction_run_id,
                    error_bytes,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise _error("batch page request already has a final result") from exc
        connection.commit()


def batch_progress_v1(path: Path) -> list[dict[str, Any]]:
    """List batch and per-document completion counts for safe resumable operation."""

    with _connect(path, readonly=True) as connection:
        jobs = connection.execute(
            """
            SELECT j.*,
                   e.state, e.done, e.successful_request_count,
                   e.failed_request_count, e.pending_request_count
            FROM batch_job AS j
            JOIN batch_event AS e ON e.batch_job_id=j.batch_job_id
            WHERE e.event_ordinal=(
              SELECT MAX(e2.event_ordinal) FROM batch_event AS e2
              WHERE e2.batch_job_id=j.batch_job_id
            )
            ORDER BY j.batch_job_id
            """
        ).fetchall()
        output: list[dict[str, Any]] = []
        for job in jobs:
            results = connection.execute(
                """
                SELECT disposition, COUNT(*) AS count
                FROM batch_request_result WHERE batch_job_id=?
                GROUP BY disposition ORDER BY disposition
                """,
                (job["batch_job_id"],),
            ).fetchall()
            documents = connection.execute(
                """
                SELECT d.document_id, d.source_logical_name,
                       COUNT(*) AS requested_pages,
                       SUM(CASE WHEN x.disposition='INGESTED' THEN 1 ELSE 0 END) AS ingested_pages,
                       SUM(CASE WHEN x.disposition='FAILED' THEN 1 ELSE 0 END) AS failed_pages
                FROM batch_page_request AS r
                JOIN page AS p USING (page_id)
                JOIN document AS d USING (document_id)
                LEFT JOIN batch_request_result AS x
                  ON x.batch_job_id=r.batch_job_id AND x.request_id=r.request_id
                WHERE r.batch_job_id=?
                GROUP BY d.document_id, d.source_logical_name
                ORDER BY d.source_logical_name, d.document_id
                """,
                (job["batch_job_id"],),
            ).fetchall()
            final_counts = {row["disposition"]: row["count"] for row in results}
            output.append(
                {
                    "batch_job_id": job["batch_job_id"],
                    "batch_name": job["provider_batch_name"],
                    "credential_slot": job["credential_slot"],
                    "documents": [dict(row) for row in documents],
                    "failed_pages": final_counts.get("FAILED", 0),
                    "ingested_pages": final_counts.get("INGESTED", 0),
                    "provider": job["provider"],
                    "request_count": job["request_count"],
                    "state": job["state"],
                    "unfinalized_pages": job["request_count"] - sum(final_counts.values()),
                }
            )
    return output


def batch_finalized_requests_v1(path: Path, *, batch_name: str) -> dict[str, str]:
    """Return request dispositions already sealed for one provider batch."""

    with _connect(path, readonly=True) as connection:
        rows = connection.execute(
            """
            SELECT r.request_id, x.disposition
            FROM batch_job AS j
            JOIN batch_page_request AS r USING (batch_job_id)
            LEFT JOIN batch_request_result AS x
              ON x.batch_job_id=r.batch_job_id AND x.request_id=r.request_id
            WHERE j.provider_batch_name=?
            ORDER BY r.request_id
            """,
            (batch_name,),
        ).fetchall()
    if not rows:
        raise _error("batch is not registered")
    return {row["request_id"]: row["disposition"] for row in rows if row["disposition"]}


def query_family_anchor_regions_v1(
    path: Path,
    *,
    anchor_aliases: Sequence[Sequence[str]],
) -> list[dict[str, Any]]:
    """Shortlist tables containing all two or three accent-folded anchor sets."""

    if len(anchor_aliases) not in {2, 3} or any(not aliases for aliases in anchor_aliases):
        raise _error("family query requires two or three nonempty anchor sets")
    folded_sets = [
        sorted({normalize_search_text_v1(alias)["text_ascii_folded"] for alias in aliases})
        for aliases in anchor_aliases
    ]
    with _connect(path, readonly=True) as connection:
        tables = connection.execute(
            """
            SELECT DISTINCT page_json_version_id, section_id, table_id
            FROM row_node
            ORDER BY page_json_version_id, section_id, table_id
            """
        ).fetchall()
        result: list[dict[str, Any]] = []
        for table in tables:
            hit_groups: list[list[str]] = []
            for aliases in folded_sets:
                placeholders = ",".join("?" for _ in aliases)
                rows = connection.execute(
                    f"""
                    SELECT row_id FROM row_node
                    WHERE page_json_version_id=? AND section_id=? AND table_id=?
                      AND label_ascii_folded IN ({placeholders})
                    ORDER BY source_order
                    """,
                    (*tuple(table), *aliases),
                ).fetchall()
                hit_groups.append([row[0] for row in rows])
            if all(hit_groups):
                result.append(
                    {
                        "anchor_row_ids": hit_groups,
                        "page_json_version_id": table["page_json_version_id"],
                        "section_id": table["section_id"],
                        "table_id": table["table_id"],
                    }
                )
    return result


def usage_summary_v1(path: Path) -> dict[str, Any]:
    """Aggregate token, cost, provider, and retry statistics for later reporting."""

    with _connect(path, readonly=True) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS runs,
                   COALESCE(SUM(input_tokens),0) AS input_tokens,
                   COALESCE(SUM(output_tokens),0) AS output_tokens,
                   COALESCE(SUM(thought_tokens),0) AS thought_tokens,
                   COALESCE(SUM(cached_input_tokens),0) AS cached_input_tokens
            FROM extraction_run
            """
        ).fetchone()
        attempts = connection.execute(
            """
            SELECT provider, credential_slot, outcome, COUNT(*) AS count
            FROM provider_attempt
            GROUP BY provider, credential_slot, outcome
            ORDER BY provider, credential_slot, outcome
            """
        ).fetchall()
        costs = connection.execute("SELECT cost_usd FROM extraction_run").fetchall()
    total_cost = sum((Decimal(item[0]) for item in costs), start=Decimal(0))
    return {
        "attempts": [dict(item) for item in attempts],
        "cached_input_tokens": row["cached_input_tokens"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "run_count": row["runs"],
        "thought_tokens": row["thought_tokens"],
        "total_cost_usd": format(total_cost, ".12f"),
    }


def build_financial_document_manifest_v1(
    path: Path,
    *,
    source_sha256: str,
    source_logical_name: str | None = None,
    expected_physical_pages: Sequence[int],
    prompt_sha256: str,
    response_schema_sha256: str,
    requested_model: str,
    requested_service_tier: str,
    selected_provider: str,
) -> dict[str, Any]:
    """Bind one complete document to an exact immutable extraction contract.

    The manifest is deliberately an index of page JSON versions rather than a
    second copy of every large JSON object.  Consumers can retrieve exact page
    content by ``page_json_version_id`` while cheaply proving full page coverage,
    provider/prompt provenance, status counts, tokens, and cost.
    """

    if (
        type(source_sha256) is not str
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
    ):
        raise _error("document manifest source SHA-256 is invalid")
    if source_logical_name is not None and (
        type(source_logical_name) is not str or not source_logical_name
    ):
        raise _error("document manifest source logical name is invalid")
    pages = list(expected_physical_pages)
    if (
        not pages
        or any(type(page) is not int or page <= 0 for page in pages)
        or pages != sorted(set(pages))
    ):
        raise _error("document manifest page frontier is invalid")
    exact_strings = {
        "prompt_sha256": prompt_sha256,
        "response_schema_sha256": response_schema_sha256,
        "requested_model": requested_model,
        "requested_service_tier": requested_service_tier,
        "selected_provider": selected_provider,
    }
    if any(type(value) is not str or not value for value in exact_strings.values()):
        raise _error("document manifest extraction contract is invalid")
    placeholders = ",".join("?" for _ in pages)
    with _connect(path, readonly=True) as connection:
        if source_logical_name is None:
            document_rows = connection.execute(
                "SELECT * FROM document WHERE source_sha256=?", (source_sha256,)
            ).fetchall()
        else:
            document_rows = connection.execute(
                "SELECT * FROM document WHERE source_sha256=? AND source_logical_name=?",
                (source_sha256, source_logical_name),
            ).fetchall()
        if len(document_rows) != 1:
            raise _error("document manifest source is not unique in the store")
        document = document_rows[0]
        records = connection.execute(
            f"""
            SELECT p.physical_page, p.page_id, p.image_sha256,
                   p.image_size_bytes, p.pixel_width, p.pixel_height,
                   p.render_dpi, p.media_type,
                   r.extraction_run_id, r.selected_model,
                   r.selected_service_tier, r.response_id_sha256,
                   r.input_tokens, r.output_tokens, r.thought_tokens,
                   r.cached_input_tokens, r.total_tokens, r.cost_usd,
                   r.cost_disposition,
                   j.page_json_version_id, j.page_status,
                   j.canonical_json_sha256,
                   (SELECT COUNT(*) FROM section_node AS s
                    WHERE s.page_json_version_id=j.page_json_version_id) AS section_count,
                   (SELECT COUNT(*) FROM table_node AS t
                    WHERE t.page_json_version_id=j.page_json_version_id) AS table_count,
                   (SELECT COUNT(*) FROM row_node AS n
                    WHERE n.page_json_version_id=j.page_json_version_id) AS row_count,
                   (SELECT COUNT(*) FROM value_cell AS v
                    WHERE v.page_json_version_id=j.page_json_version_id) AS cell_count
            FROM page AS p
            JOIN extraction_run AS r USING (page_id)
            JOIN page_json_version AS j USING (extraction_run_id)
            WHERE p.document_id=?
              AND p.physical_page IN ({placeholders})
              AND r.prompt_sha256=?
              AND r.response_schema_sha256=?
              AND r.requested_model=?
              AND r.requested_service_tier=?
              AND r.selected_provider=?
            ORDER BY p.physical_page
            """,
            (
                document["document_id"],
                *pages,
                prompt_sha256,
                response_schema_sha256,
                requested_model,
                requested_service_tier,
                selected_provider,
            ),
        ).fetchall()
    returned_pages = [record["physical_page"] for record in records]
    if returned_pages != pages:
        raise _error("document manifest page frontier is incomplete or duplicate")
    page_records: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    total_cost = Decimal(0)
    totals = {
        "cached_input_tokens": 0,
        "cell_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "row_count": 0,
        "section_count": 0,
        "table_count": 0,
        "thought_tokens": 0,
        "total_tokens": 0,
    }
    for record in records:
        status = record["page_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        total_cost += Decimal(record["cost_usd"])
        for field in totals:
            totals[field] += record[field]
        page_records.append(
            {
                "canonical_json_sha256": record["canonical_json_sha256"],
                "content_counts": {
                    "cell_count": record["cell_count"],
                    "row_count": record["row_count"],
                    "section_count": record["section_count"],
                    "table_count": record["table_count"],
                },
                "cost_disposition": record["cost_disposition"],
                "cost_usd": record["cost_usd"],
                "extraction_run_id": record["extraction_run_id"],
                "image": {
                    "height": record["pixel_height"],
                    "media_type": record["media_type"],
                    "render_dpi": record["render_dpi"],
                    "sha256": record["image_sha256"],
                    "size_bytes": record["image_size_bytes"],
                    "width": record["pixel_width"],
                },
                "page_id": record["page_id"],
                "page_json_version_id": record["page_json_version_id"],
                "physical_page": record["physical_page"],
                "response_id_sha256": record["response_id_sha256"],
                "selected_model": record["selected_model"],
                "selected_service_tier": record["selected_service_tier"],
                "status": status,
                "usage": {
                    "cached_input_tokens": record["cached_input_tokens"],
                    "input_tokens": record["input_tokens"],
                    "output_tokens": record["output_tokens"],
                    "thought_tokens": record["thought_tokens"],
                    "total_tokens": record["total_tokens"],
                },
            }
        )
    material = {
        "document": {
            "document_id": document["document_id"],
            "source_logical_name": document["source_logical_name"],
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        },
        "extraction_contract": exact_strings,
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V1",
        "page_count": len(page_records),
        "pages": page_records,
        "status_counts": dict(sorted(status_counts.items())),
        "totals": {**totals, "cost_usd": format(total_cost, ".12f")},
    }
    return {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
