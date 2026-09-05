"""Immutable SQLite store for Gemini JSON-first financial pages."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    FORMAT_VERSION as PAGE_FORMAT_VERSION,
)
from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    SEARCH_NORMALIZATION_VERSION,
    GeminiFinancialPageJsonV1Error,
    build_financial_page_json_prompt_v1,
    decode_financial_page_json_text_v1,
    financial_page_json_response_schema_v1,
    normalize_search_text_v1,
    validate_financial_page_json_v1,
)
from bctc_ai.evaluation.gemini_json_first_batch_v1 import (
    BatchSubmissionV1,
    summarize_google_batch_operation_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    GeminiJsonFirstProviderV1Error,
    ProviderResultV1,
    extract_completed_provider_response_text_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    TABLE_POPULATION_PROJECTION_FORMAT_VERSION,
    project_whole_page_table_population_v1,
    validate_whole_page_table_population_projection_v1,
)
from bctc_ai.evaluation.gemini_json_structural_context_v1 import (
    declared_surface_alias_match_v1,
    family_anchor_lookup_forms_v1,
    resolve_candidate_structural_context_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "GEMINI_FINANCIAL_PAGE_STORE_V9"
DEFAULT_DATABASE_PATH = Path("data/local/gemini_financial_page_store_v1.sqlite3")
_STANDARD_ITEMS_PROMPT_SHA256 = sha256(
    build_financial_page_json_prompt_v1(variant="items").encode("utf-8")
).hexdigest()
_STANDARD_PAGE_RESPONSE_SCHEMA_SHA256 = canonical_json_sha256_v1(
    financial_page_json_response_schema_v1()
)
_SELECTABLE_PROMPT_VARIANTS = frozenset(
    {
        "balanced",
        "compact",
        "items",
        "region-repair",
        "region-repair-row-label-and-values",
        "region-repair-row-values",
        "region-repair-section-narratives",
        "region-repair-structural-context-surfaces",
        "region-repair-table-period-axis",
        "region-repair-table-title-and-columns",
        "scope",
        "simple",
    }
)
_SPECIALIZED_EXTRACTION_AUTHORIZATION_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/registered/gemini_financial_page_specialized_extraction_authorizations_v1.json"
)
_SPECIALIZED_EXTRACTION_AUTHORIZATION_REGISTRY_SHA256 = (
    "f4e7d1ae36104dea06095e07c0af2eefedb5048b4a88c5b85fbe76951b969c75"
)
_SPECIALIZED_PROMPT_VARIANTS = frozenset({"schema_alignment"})
_SPECIALIZED_EXTRACTION_AUTHORIZED_PAGE_JSON_VERSION_IDS = frozenset(
    {"gfpstorev1:json:3616fa50e0c315fd8be626d678ec3a9d707ae9dd0bf0da95e99645b28046d7e5"}
)


class GeminiFinancialPageStoreV1Error(RuntimeError):
    """The immutable store contract or its content binding was violated."""


def _error(message: str) -> GeminiFinancialPageStoreV1Error:
    return GeminiFinancialPageStoreV1Error(message)


def _is_sha256_v1(value: Any) -> bool:
    return bool(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _specialized_extraction_authorizations_v1() -> dict[str, dict[str, Any]]:
    """Load the reviewed, exact-receipt allowlist for nonstandard prompts.

    A prompt-variant string is not sufficient authorization.  Every entry is
    content-bound to the selected JSON version, source/page/image, prompt and
    response schema, provider attempt, and the recovery claim provenance that
    produced it.  The registry bytes themselves are pinned here so an edited
    allowlist fails closed until code review deliberately updates the pin.
    """

    try:
        raw = _SPECIALIZED_EXTRACTION_AUTHORIZATION_REGISTRY_PATH.read_bytes()
    except OSError as exc:
        raise _error("specialized extraction authorization registry is unavailable") from exc
    if sha256(raw).hexdigest() != _SPECIALIZED_EXTRACTION_AUTHORIZATION_REGISTRY_SHA256:
        raise _error("specialized extraction authorization registry content drifted")
    try:
        registry = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("specialized extraction authorization registry is invalid") from exc
    if (
        type(registry) is not dict
        or set(registry) != {"authorizations", "format_version", "policy"}
        or registry.get("format_version")
        != "GEMINI_FINANCIAL_PAGE_SPECIALIZED_EXTRACTION_AUTHORIZATION_REGISTRY_V1"
        or registry.get("policy")
        != {
            "exact_page_json_version_only": True,
            "implicit_prompt_variants": False,
            "recovery_provenance_required": True,
        }
        or type(registry.get("authorizations")) is not list
        or not registry["authorizations"]
    ):
        raise _error("specialized extraction authorization registry is invalid")

    required_provenance = {
        "claim_format_version",
        "claim_receipt_sha256",
        "completion_format_version",
        "completion_receipt_sha256",
        "document_manifest_id",
        "provider_job_ref",
        "repair_instruction_sha256",
        "repair_registry_entry_sha256",
        "task_id",
    }
    result: dict[str, dict[str, Any]] = {}
    for raw_entry in registry["authorizations"]:
        if (
            type(raw_entry) is not dict
            or set(raw_entry) != {"authorization_id", "provenance", "store_receipt"}
            or type(raw_entry.get("provenance")) is not dict
            or set(raw_entry["provenance"]) != required_provenance
            or type(raw_entry.get("store_receipt")) is not dict
        ):
            raise _error("specialized extraction authorization entry is invalid")
        provenance = raw_entry["provenance"]
        store_receipt = raw_entry["store_receipt"]
        page_json_version_id = store_receipt.get("page_json_version_id")
        provider_attempts = store_receipt.get("provider_attempts")
        material = {"provenance": provenance, "store_receipt": store_receipt}
        expected_id = "gfpseav1:authorization:" + canonical_json_sha256_v1(material)
        if (
            raw_entry.get("authorization_id") != expected_id
            or type(page_json_version_id) is not str
            or re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", page_json_version_id) is None
            or store_receipt.get("prompt_variant") not in _SPECIALIZED_PROMPT_VARIANTS
            or store_receipt.get("output_contract_mode") != "JSON_SCHEMA"
            or store_receipt.get("response_schema_sha256") != _STANDARD_PAGE_RESPONSE_SCHEMA_SHA256
            or store_receipt.get("requested_model") != "gemini-3.7-flash"
            or store_receipt.get("requested_service_tier") != "agy-low"
            or store_receipt.get("thinking_level") != "low"
            or store_receipt.get("selected_provider") != "Agy"
            or store_receipt.get("selected_model") != "gemini-3.7-flash-low"
            or store_receipt.get("selected_service_tier") != "agy-low"
            or type(provider_attempts) is not list
            or len(provider_attempts) != 1
            or provider_attempts[0].get("attempt_ordinal") != 1
            or provider_attempts[0].get("provider") != "AGY_CLI"
            or provider_attempts[0].get("credential_slot") != "AGY_AUTHENTICATED_LOCAL_SESSION"
            or provider_attempts[0].get("outcome") != "COMPLETED"
            or provenance.get("claim_format_version")
            != "GEMINI_JSON_FIRST_AGY_SCHEMA_ALIGNMENT_RECOVERY_CLAIM_V1"
            or provenance.get("completion_format_version")
            != "GEMINI_JSON_FIRST_AGY_TASK_SUCCESS_V1"
            or type(provenance.get("task_id")) is not str
            or not provenance["task_id"].startswith("gjfptaskv1:")
            or type(provenance.get("provider_job_ref")) is not str
            or re.fullmatch(r"agyjobv1:[0-9a-f]{64}", provenance["provider_job_ref"]) is None
            or type(provenance.get("document_manifest_id")) is not str
            or re.fullmatch(r"gfdmv1:manifest:[0-9a-f]{64}", provenance["document_manifest_id"])
            is None
            or any(
                not _is_sha256_v1(provenance.get(field))
                for field in (
                    "claim_receipt_sha256",
                    "completion_receipt_sha256",
                    "repair_instruction_sha256",
                    "repair_registry_entry_sha256",
                )
            )
            or page_json_version_id in result
        ):
            raise _error("specialized extraction authorization entry is invalid")
        result[page_json_version_id] = canonical_clone_v1(raw_entry)
    if set(result) != set(_SPECIALIZED_EXTRACTION_AUTHORIZED_PAGE_JSON_VERSION_IDS):
        raise _error("specialized extraction authorization registry frontier drifted")
    return result


def _specialized_extraction_store_receipt_v1(
    path: Path, *, page_json_version_id: str
) -> dict[str, Any]:
    """Replay every immutable store field used by a specialized authorization."""

    with _connect(path, readonly=True) as connection:
        row = connection.execute(
            """
            SELECT v.page_json_version_id,v.raw_response_sha256,
                   v.canonical_json_sha256,
                   e.extraction_run_id,e.cache_key,e.prompt_variant,
                   e.output_contract_mode,e.prompt_sha256,
                   e.response_schema_sha256,e.requested_model,
                   e.requested_service_tier,e.thinking_level,
                   e.selected_provider,e.selected_model,e.selected_service_tier,
                   e.response_id_sha256,e.input_tokens,e.output_tokens,
                   e.thought_tokens,e.cached_input_tokens,e.total_tokens,
                   e.cost_usd,e.cost_disposition,e.status,
                   p.page_id,p.physical_page,p.image_sha256,p.image_size_bytes,
                   p.pixel_width,p.pixel_height,p.render_dpi,p.media_type,
                   d.source_sha256,d.source_size_bytes,d.source_logical_name
            FROM page_json_version AS v
            JOIN extraction_run AS e USING(extraction_run_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            WHERE v.page_json_version_id=?
            """,
            (page_json_version_id,),
        ).fetchall()
        attempts = connection.execute(
            """
            SELECT attempt_ordinal,provider,credential_slot,elapsed_seconds,
                   http_status,outcome,usage_json
            FROM provider_attempt
            WHERE extraction_run_id=(
                SELECT extraction_run_id FROM page_json_version
                WHERE page_json_version_id=?
            )
            ORDER BY attempt_ordinal
            """,
            (page_json_version_id,),
        ).fetchall()
    if (
        len(row) != 1
        or not attempts
        or [item["attempt_ordinal"] for item in attempts] != list(range(1, len(attempts) + 1))
    ):
        raise _error("specialized extraction store receipt is absent or ambiguous")
    receipt = dict(row[0])
    receipt["provider_attempts"] = [
        {
            "attempt_ordinal": item["attempt_ordinal"],
            "credential_slot": item["credential_slot"],
            "elapsed_seconds": item["elapsed_seconds"],
            "http_status": item["http_status"],
            "outcome": item["outcome"],
            "provider": item["provider"],
            "usage_sha256": (
                sha256(bytes(item["usage_json"])).hexdigest()
                if item["usage_json"] is not None
                else None
            ),
        }
        for item in attempts
    ]
    return receipt


def _is_selectable_extraction_receipt_v1(
    path: Path, *, page_json_version_id: str, prompt_variant: str
) -> bool:
    """Authorize ordinary prompts or one exact reviewed specialized receipt."""

    if page_json_version_id in _SPECIALIZED_EXTRACTION_AUTHORIZED_PAGE_JSON_VERSION_IDS:
        if prompt_variant not in _SPECIALIZED_PROMPT_VARIANTS:
            raise _error("specialized extraction receipt prompt variant drifted")
        authorizations = _specialized_extraction_authorizations_v1()
        authorization = authorizations.get(page_json_version_id)
        if authorization is None:
            raise _error("specialized extraction receipt is not registered")
        actual = _specialized_extraction_store_receipt_v1(
            path, page_json_version_id=page_json_version_id
        )
        if not same_typed_json_v1(actual, authorization["store_receipt"]):
            raise _error("specialized extraction store receipt does not match authorization")
        return True
    if prompt_variant in _SELECTABLE_PROMPT_VARIANTS:
        return True
    if prompt_variant not in _SPECIALIZED_PROMPT_VARIANTS:
        return False
    raise _error("specialized extraction receipt is not registered")


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

_REGION_REPAIR_EXTENSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS page_json_region_repair (
    repair_id TEXT PRIMARY KEY,
    base_page_json_version_id TEXT NOT NULL
      REFERENCES page_json_version(page_json_version_id),
    merged_page_json_version_id TEXT NOT NULL UNIQUE
      REFERENCES page_json_version(page_json_version_id),
    receipt_sha256 TEXT NOT NULL UNIQUE,
    receipt_json BLOB NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS idx_region_repair_base
  ON page_json_region_repair(base_page_json_version_id, repair_id);
CREATE TABLE IF NOT EXISTS page_json_region_repair_observation (
    repair_id TEXT NOT NULL REFERENCES page_json_region_repair(repair_id),
    merged_page_json_version_id TEXT NOT NULL UNIQUE
      REFERENCES page_json_version(page_json_version_id),
    PRIMARY KEY(repair_id, merged_page_json_version_id)
) STRICT;
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


def initialize_region_repair_extension_v1(path: Path) -> None:
    """Enable immutable base-to-repaired-version lineage in one writable V9 store."""

    with _connect(path) as connection:
        connection.executescript(_REGION_REPAIR_EXTENSION_SCHEMA)
        connection.commit()


def record_page_json_region_repair_v1(
    path: Path,
    *,
    merged_page_json_version_id: str,
    receipt: Mapping[str, Any],
) -> dict[str, str]:
    """Persist and replay one exact region-only repair lineage receipt."""

    required = {
        "base_page_json_sha256",
        "base_page_json_version_id",
        "changes",
        "format_version",
        "merged_page_json_sha256",
        "repair_id",
        "repair_response_sha256",
    }
    if (
        type(receipt) is not dict
        or set(receipt) != required
        or receipt.get("format_version") != "GEMINI_JSON_REGION_REPAIR_V1"
        or type(merged_page_json_version_id) is not str
        or not merged_page_json_version_id.startswith("gfpstorev1:json:")
        or receipt.get("repair_id")
        != "gjfrrv1:repair:"
        + canonical_json_sha256_v1({key: receipt[key] for key in required - {"repair_id"}})
    ):
        raise _error("region repair lineage receipt is invalid")
    receipt_bytes = canonical_json_bytes_v1(receipt) + b"\n"
    receipt_sha = sha256(receipt_bytes).hexdigest()
    base_id = receipt["base_page_json_version_id"]
    with _connect(path) as connection:
        connection.executescript(_REGION_REPAIR_EXTENSION_SCHEMA)
        rows = connection.execute(
            "SELECT page_json_version_id, page_id, canonical_json_bytes "
            "FROM page_json_version WHERE page_json_version_id IN (?,?) "
            "ORDER BY page_json_version_id",
            (base_id, merged_page_json_version_id),
        ).fetchall()
        by_id = {row["page_json_version_id"]: row for row in rows}
        if set(by_id) != {base_id, merged_page_json_version_id}:
            raise _error("region repair base or merged page version is absent")
        if by_id[base_id]["page_id"] != by_id[merged_page_json_version_id]["page_id"]:
            raise _error("region repair versions do not belong to the same page")
        try:
            base_json = validate_financial_page_json_v1(
                json.loads(by_id[base_id]["canonical_json_bytes"])
            )
            merged_json = validate_financial_page_json_v1(
                json.loads(by_id[merged_page_json_version_id]["canonical_json_bytes"])
            )
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("region repair page JSON does not replay") from exc
        if receipt["base_page_json_sha256"] != canonical_json_sha256_v1(base_json) or receipt[
            "merged_page_json_sha256"
        ] != canonical_json_sha256_v1(merged_json):
            raise _error("region repair page content hash does not replay")
        existing = connection.execute(
            "SELECT * FROM page_json_region_repair WHERE repair_id=?",
            (receipt["repair_id"],),
        ).fetchone()
        expected = (
            receipt["repair_id"],
            base_id,
            merged_page_json_version_id,
            receipt_sha,
            receipt_bytes,
        )
        if existing is not None:
            if (
                existing["repair_id"] != receipt["repair_id"]
                or existing["base_page_json_version_id"] != base_id
                or existing["receipt_sha256"] != receipt_sha
                or existing["receipt_json"] != receipt_bytes
            ):
                raise _error("region repair ID is already bound to different content")
        else:
            connection.execute(
                "INSERT INTO page_json_region_repair VALUES (?,?,?,?,?)",
                expected,
            )
            existing = connection.execute(
                "SELECT * FROM page_json_region_repair WHERE repair_id=?",
                (receipt["repair_id"],),
            ).fetchone()
        connection.execute(
            "INSERT OR IGNORE INTO page_json_region_repair_observation VALUES (?,?)",
            (receipt["repair_id"], merged_page_json_version_id),
        )
        connection.commit()
    return {
        "base_page_json_version_id": base_id,
        "merged_page_json_version_id": existing["merged_page_json_version_id"],
        "observed_page_json_version_id": merged_page_json_version_id,
        "repair_id": receipt["repair_id"],
        "repair_receipt_sha256": receipt_sha,
    }


def page_json_region_repair_lineages_v1(
    path: Path, *, observed_page_json_version_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Replay exact base-to-observed repair lineage in caller-selected order."""

    version_ids = list(observed_page_json_version_ids)
    if (
        not version_ids
        or len(version_ids) != len(set(version_ids))
        or any(
            type(version_id) is not str or not version_id.startswith("gfpstorev1:json:")
            for version_id in version_ids
        )
    ):
        raise _error("region repair lineage version frontier is invalid")
    with _connect(path, readonly=True) as connection:
        try:
            connection.execute(
                "CREATE TEMP TABLE selected_region_repair_lineage("
                "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
            )
            connection.executemany(
                "INSERT INTO selected_region_repair_lineage VALUES (?,?)",
                enumerate(version_ids, start=1),
            )
            rows = connection.execute(
                "SELECT s.selection_ordinal,o.merged_page_json_version_id AS observed_id,"
                "r.repair_id,r.base_page_json_version_id,r.merged_page_json_version_id,"
                "r.receipt_sha256,r.receipt_json,"
                "base.canonical_json_bytes AS base_page_json_bytes,"
                "merged.canonical_json_bytes AS merged_page_json_bytes,"
                "merged_run.prompt_variant AS merged_prompt_variant "
                "FROM selected_region_repair_lineage AS s "
                "JOIN page_json_region_repair_observation AS o "
                "ON o.merged_page_json_version_id=s.page_json_version_id "
                "JOIN page_json_region_repair AS r USING(repair_id) "
                "JOIN page_json_version AS base "
                "ON base.page_json_version_id=r.base_page_json_version_id "
                "JOIN page_json_version AS merged "
                "ON merged.page_json_version_id=r.merged_page_json_version_id "
                "JOIN extraction_run AS merged_run "
                "ON merged_run.extraction_run_id=merged.extraction_run_id "
                "ORDER BY s.selection_ordinal"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise _error("region repair lineage tables are absent") from exc
    if len(rows) != len(version_ids):
        raise _error("region repair lineage is absent for a selected page version")
    result = []
    for expected, row in zip(version_ids, rows, strict=True):
        try:
            receipt = json.loads(row["receipt_json"])
            base_page_json = validate_financial_page_json_v1(
                json.loads(row["base_page_json_bytes"])
            )
            merged_page_json = validate_financial_page_json_v1(
                json.loads(row["merged_page_json_bytes"])
            )
        except (TypeError, UnicodeDecodeError, ValueError) as exc:
            raise _error("region repair lineage receipt JSON is invalid") from exc
        required = {
            "base_page_json_sha256",
            "base_page_json_version_id",
            "changes",
            "format_version",
            "merged_page_json_sha256",
            "repair_id",
            "repair_response_sha256",
        }
        receipt_bytes = canonical_json_bytes_v1(receipt) + b"\n"
        material = {key: receipt[key] for key in receipt if key != "repair_id"}
        if (
            type(receipt) is not dict
            or set(receipt) != required
            or receipt.get("format_version") != "GEMINI_JSON_REGION_REPAIR_V1"
            or row["observed_id"] != expected
            or sha256(receipt_bytes).hexdigest() != row["receipt_sha256"]
            or receipt.get("repair_id") != row["repair_id"]
            or receipt.get("repair_id") != "gjfrrv1:repair:" + canonical_json_sha256_v1(material)
            or receipt.get("base_page_json_version_id") != row["base_page_json_version_id"]
            or canonical_json_bytes_v1(base_page_json) + b"\n" != row["base_page_json_bytes"]
            or canonical_json_bytes_v1(merged_page_json) + b"\n" != row["merged_page_json_bytes"]
            or receipt.get("base_page_json_sha256") != canonical_json_sha256_v1(base_page_json)
            or receipt.get("merged_page_json_sha256") != canonical_json_sha256_v1(merged_page_json)
        ):
            raise _error("region repair lineage receipt does not replay")
        changes = receipt["changes"]
        is_table_population_projection = (
            type(changes) is list
            and len(changes) == 1
            and type(changes[0]) is dict
            and changes[0].get("change_kind") == "WHOLE_PAGE_TABLE_POPULATION_PROJECTION"
        )
        if (row["merged_prompt_variant"] == "table-population-projection") != (
            is_table_population_projection
        ):
            raise _error("table-population lineage kind and merged version differ")
        if is_table_population_projection:
            change = changes[0]
            if set(change) != {
                "change_kind",
                "projection_receipt",
                "retry_provenance",
            }:
                raise _error("table-population lineage change fields drifted")
            projection = change["projection_receipt"]
            if (
                type(projection) is not dict
                or projection.get("format_version") != TABLE_POPULATION_PROJECTION_FORMAT_VERSION
            ):
                raise _error("table-population lineage projection is invalid")
            retry_id = projection.get("retry_page_json_version_id")
            retry_versions = load_page_json_versions_v1(path, page_json_version_ids=[retry_id])
            with _connect(path, readonly=True) as connection:
                retry_row = connection.execute(
                    "SELECT v.raw_response_sha256,r.extraction_run_id,r.prompt_variant,"
                    "r.output_contract_mode,"
                    "r.prompt_sha256,r.response_schema_sha256,r.requested_model,"
                    "r.requested_service_tier,r.selected_provider,p.physical_page,"
                    "p.image_sha256,d.source_logical_name,d.source_sha256 "
                    "FROM page_json_version AS v JOIN extraction_run AS r "
                    "USING(extraction_run_id) JOIN page AS p USING(page_id) "
                    "JOIN document AS d USING(document_id) "
                    "WHERE v.page_json_version_id=?",
                    (retry_id,),
                ).fetchone()
            if retry_row is None:
                raise _error("table-population retry provenance is absent")
            if (
                retry_row["prompt_variant"] != "items"
                or retry_row["output_contract_mode"] != "JSON_SCHEMA"
                or retry_row["prompt_sha256"] != _STANDARD_ITEMS_PROMPT_SHA256
                or retry_row["response_schema_sha256"] != _STANDARD_PAGE_RESPONSE_SCHEMA_SHA256
                or retry_row["requested_model"] != "gemini-3.7-flash"
                or retry_row["requested_service_tier"] != "flex"
            ):
                raise _error("table-population retry prompt contract drifted")
            expected_retry_provenance = {
                "extraction_run_id": retry_row["extraction_run_id"],
                "image_sha256": retry_row["image_sha256"],
                "physical_page": retry_row["physical_page"],
                "prompt_sha256": retry_row["prompt_sha256"],
                "prompt_variant": retry_row["prompt_variant"],
                "provider": retry_row["selected_provider"],
                "raw_response_sha256": retry_row["raw_response_sha256"],
                "requested_model": retry_row["requested_model"],
                "requested_service_tier": retry_row["requested_service_tier"],
                "response_schema_sha256": retry_row["response_schema_sha256"],
                "source_logical_name": retry_row["source_logical_name"],
                "source_sha256": retry_row["source_sha256"],
            }
            if (
                change["retry_provenance"] != expected_retry_provenance
                or receipt["repair_response_sha256"] != retry_row["raw_response_sha256"]
            ):
                raise _error("table-population retry provenance drifted")
            validate_whole_page_table_population_projection_v1(
                projection,
                base_page_json=base_page_json,
                retry_page_json=retry_versions[0]["page_json"],
                merged_page_json=merged_page_json,
            )
        result.append(
            {
                "base_page_json_version_id": row["base_page_json_version_id"],
                "canonical_merged_page_json_version_id": row["merged_page_json_version_id"],
                "observed_page_json_version_id": expected,
                "repair_id": row["repair_id"],
                "repair_receipt": receipt,
                "repair_receipt_sha256": row["receipt_sha256"],
            }
        )
    return result


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


def lookup_cached_page_extraction_v1(path: Path, cache_key: str) -> dict[str, Any] | None:
    """Return exact cached identities and JSON without issuing another provider call."""

    with _connect(path, readonly=True) as connection:
        row = connection.execute(
            """
            SELECT r.cache_key,r.extraction_run_id,r.page_id,
                   r.selected_provider,r.selected_model,r.selected_service_tier,
                   r.response_id_sha256,r.input_tokens,r.output_tokens,
                   r.thought_tokens,r.cached_input_tokens,r.total_tokens,
                   r.cost_usd,r.cost_disposition,
                   p.document_id,j.page_json_version_id,j.canonical_json_bytes
            FROM extraction_run AS r
            JOIN page AS p USING(page_id)
            JOIN page_json_version AS j USING(extraction_run_id)
            WHERE r.cache_key=? AND r.status='COMPLETE'
            """,
            (cache_key,),
        ).fetchone()
    if row is None:
        return None
    page_json = validate_financial_page_json_v1(json.loads(bytes(row["canonical_json_bytes"])))
    return {
        "database_identities": {
            "cache_key": row["cache_key"],
            "document_id": row["document_id"],
            "extraction_run_id": row["extraction_run_id"],
            "page_id": row["page_id"],
            "page_json_version_id": row["page_json_version_id"],
        },
        "page_json": page_json,
        "provider": {
            "model": row["selected_model"],
            "name": row["selected_provider"],
            "response_id_sha256": row["response_id_sha256"],
            "service_tier": row["selected_service_tier"],
        },
        "source_usage": {
            "actual_cost_usd": row["cost_usd"],
            "cached_input_tokens": row["cached_input_tokens"],
            "cost_disposition": row["cost_disposition"],
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "thought_tokens": row["thought_tokens"],
            "total_tokens": row["total_tokens"],
        },
    }


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
        existing = connection.execute(
            "SELECT extraction_run.extraction_run_id, extraction_run.page_id, "
            "page_json_version.page_json_version_id, "
            "page_json_version.raw_response_sha256, "
            "page_json_version.canonical_json_sha256 "
            "FROM extraction_run JOIN page_json_version "
            "ON page_json_version.extraction_run_id=extraction_run.extraction_run_id "
            "WHERE extraction_run.cache_key=?",
            (cache_key,),
        ).fetchone()
        if existing is not None:
            expected = (
                extraction_run_id,
                page_id,
                page_json_version_id,
                sha256(raw_bytes).hexdigest(),
                sha256(canonical_bytes).hexdigest(),
            )
            if tuple(existing) != expected:
                raise _error("cache key is already bound to different immutable content")
            return {
                "cache_key": cache_key,
                "document_id": document_id,
                "extraction_run_id": extraction_run_id,
                "page_id": page_id,
                "page_json_version_id": page_json_version_id,
            }
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


def ingest_whole_page_table_population_projection_v1(
    path: Path,
    *,
    base_page_json_version_id: str,
    retry_page_json_version_id: str,
    target_table_ref: Mapping[str, str],
    required_changed_target_ids: Sequence[str],
    require_added_rows: bool,
) -> dict[str, Any]:
    """Persist one local projection from an authenticated standard ``items`` retry.

    The billed retry remains an ordinary immutable page extraction.  This
    function adds a zero-cost local derived version and region-repair lineage;
    it does not call a provider and never selects the retry page wholesale.
    """

    version_ids = [base_page_json_version_id, retry_page_json_version_id]
    if len(set(version_ids)) != 2:
        raise _error("table-population projection version frontier is invalid")
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_table_population_projection("
            "selection_ordinal INTEGER PRIMARY KEY,page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_table_population_projection VALUES (?,?)",
            enumerate(version_ids, start=1),
        )
        rows = connection.execute(
            "SELECT selected.selection_ordinal,v.page_json_version_id,v.page_id,"
            "v.raw_response_sha256,v.canonical_json_bytes,r.extraction_run_id,"
            "r.prompt_variant,r.output_contract_mode,r.prompt_sha256,"
            "r.response_schema_sha256,r.requested_model,"
            "r.requested_service_tier,r.selected_provider,"
            "p.physical_page,p.image_sha256,p.image_size_bytes,p.pixel_width,p.pixel_height,"
            "p.render_dpi,p.media_type,d.source_logical_name,d.source_sha256,d.source_size_bytes "
            "FROM selected_table_population_projection AS selected "
            "JOIN page_json_version AS v USING(page_json_version_id) "
            "JOIN extraction_run AS r USING(extraction_run_id) "
            "JOIN page AS p USING(page_id) JOIN document AS d USING(document_id) "
            "ORDER BY selected.selection_ordinal"
        ).fetchall()
    if len(rows) != 2 or rows[0]["page_id"] != rows[1]["page_id"]:
        raise _error("table-population base and retry versions do not bind one page")
    if (
        rows[1]["prompt_variant"] != "items"
        or rows[1]["output_contract_mode"] != "JSON_SCHEMA"
        or rows[1]["prompt_sha256"] != _STANDARD_ITEMS_PROMPT_SHA256
        or rows[1]["response_schema_sha256"] != _STANDARD_PAGE_RESPONSE_SCHEMA_SHA256
        or rows[1]["requested_model"] != "gemini-3.7-flash"
        or rows[1]["requested_service_tier"] != "flex"
        or rows[1]["selected_provider"]
        not in {
            "Google",
            "OPENROUTER",
            "GOOGLE_GEMINI_API",
            "GOOGLE_GEMINI_BATCH_API",
        }
    ):
        raise _error("table-population retry is not an authenticated standard items read")
    try:
        base_page_json = json.loads(rows[0]["canonical_json_bytes"])
        retry_page_json = json.loads(rows[1]["canonical_json_bytes"])
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("table-population source page JSON is invalid") from exc
    merged, projection_receipt = project_whole_page_table_population_v1(
        base_page_json,
        retry_page_json,
        base_page_json_version_id=base_page_json_version_id,
        retry_page_json_version_id=retry_page_json_version_id,
        target_table_ref=target_table_ref,
        required_changed_target_ids=required_changed_target_ids,
        require_added_rows=require_added_rows,
    )
    retry_provenance = {
        "extraction_run_id": rows[1]["extraction_run_id"],
        "image_sha256": rows[1]["image_sha256"],
        "physical_page": rows[1]["physical_page"],
        "prompt_sha256": rows[1]["prompt_sha256"],
        "prompt_variant": rows[1]["prompt_variant"],
        "provider": rows[1]["selected_provider"],
        "raw_response_sha256": rows[1]["raw_response_sha256"],
        "requested_model": rows[1]["requested_model"],
        "requested_service_tier": rows[1]["requested_service_tier"],
        "response_schema_sha256": rows[1]["response_schema_sha256"],
        "source_logical_name": rows[1]["source_logical_name"],
        "source_sha256": rows[1]["source_sha256"],
    }
    local_record = {
        "projection_receipt": projection_receipt,
        "retry_provenance": retry_provenance,
    }
    local_bytes = canonical_json_bytes_v1(local_record)
    zero_usage = {
        "actual_cost_usd": "0.000000000000",
        "billing_disposition": "LOCAL_DERIVED_NO_PROVIDER_CALL",
        "cached_input_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "thought_tokens": 0,
        "total_tokens": 0,
    }
    provider_result = ProviderResultV1(
        output_text=local_bytes.decode("utf-8"),
        raw_response_bytes=local_bytes,
        provider_name="LOCAL_DETERMINISTIC_PROJECTION",
        provider_model=TABLE_POPULATION_PROJECTION_FORMAT_VERSION,
        service_tier="NOT_APPLICABLE",
        attempts=(
            {
                "attempt_ordinal": 1,
                "credential_slot": "NOT_APPLICABLE",
                "elapsed_seconds": "0.000",
                "http_status": None,
                "outcome": "LOCAL_DETERMINISTIC_PROJECTION",
                "provider": "LOCAL_DETERMINISTIC_PROJECTION",
                "usage": None,
            },
        ),
        usage=zero_usage,
        response_id_sha256=sha256(projection_receipt["projection_id"].encode("utf-8")).hexdigest(),
    )
    document = {
        "source_logical_name": rows[0]["source_logical_name"],
        "source_sha256": rows[0]["source_sha256"],
        "source_size_bytes": rows[0]["source_size_bytes"],
    }
    page = {
        "image_sha256": rows[0]["image_sha256"],
        "image_size_bytes": rows[0]["image_size_bytes"],
        "media_type": rows[0]["media_type"],
        "physical_page": rows[0]["physical_page"],
        "pixel_height": rows[0]["pixel_height"],
        "pixel_width": rows[0]["pixel_width"],
        "render_dpi": rows[0]["render_dpi"],
    }
    ingested = ingest_financial_page_extraction_v1(
        path,
        document=document,
        page=page,
        prompt_variant="table-population-projection",
        output_contract_mode="LOCAL_DETERMINISTIC_PROJECTION",
        prompt_sha256=canonical_json_sha256_v1(
            {
                "base_page_json_version_id": base_page_json_version_id,
                "required_changed_target_ids": list(required_changed_target_ids),
                "retry_page_json_version_id": retry_page_json_version_id,
                "target_table_ref": dict(target_table_ref),
            }
        ),
        response_schema_sha256=sha256(
            TABLE_POPULATION_PROJECTION_FORMAT_VERSION.encode("utf-8")
        ).hexdigest(),
        requested_model="LOCAL_DETERMINISTIC_PROJECTION",
        requested_service_tier="NOT_APPLICABLE",
        thinking_level="NOT_APPLICABLE",
        provider_result=provider_result,
        page_json=merged,
    )
    changes = [
        {
            "change_kind": "WHOLE_PAGE_TABLE_POPULATION_PROJECTION",
            "projection_receipt": projection_receipt,
            "retry_provenance": retry_provenance,
        }
    ]
    receipt_material = {
        "base_page_json_sha256": canonical_json_sha256_v1(base_page_json),
        "base_page_json_version_id": base_page_json_version_id,
        "changes": changes,
        "format_version": "GEMINI_JSON_REGION_REPAIR_V1",
        "merged_page_json_sha256": canonical_json_sha256_v1(merged),
        "repair_response_sha256": rows[1]["raw_response_sha256"],
    }
    region_receipt = {
        **receipt_material,
        "repair_id": "gjfrrv1:repair:" + canonical_json_sha256_v1(receipt_material),
    }
    lineage = record_page_json_region_repair_v1(
        path,
        merged_page_json_version_id=ingested["page_json_version_id"],
        receipt=region_receipt,
    )
    validate_whole_page_table_population_projection_v1(
        projection_receipt,
        base_page_json=base_page_json,
        retry_page_json=retry_page_json,
        merged_page_json=merged,
    )
    return {
        **ingested,
        "lineage": lineage,
        "projection_receipt": projection_receipt,
        "region_repair_receipt": region_receipt,
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


def batch_failed_page_requests_v1(path: Path, *, batch_name: str) -> list[dict[str, Any]]:
    """Return exact failed page bindings and typed errors for one terminal batch."""

    with _connect(path, readonly=True) as connection:
        rows = connection.execute(
            """
            SELECT r.request_id, p.physical_page, x.error_json
            FROM batch_job AS j
            JOIN batch_page_request AS r USING (batch_job_id)
            JOIN page AS p USING (page_id)
            JOIN batch_request_result AS x
              ON x.batch_job_id=r.batch_job_id AND x.request_id=r.request_id
            WHERE j.provider_batch_name=? AND x.disposition='FAILED'
            ORDER BY p.physical_page, r.request_id
            """,
            (batch_name,),
        ).fetchall()
    result = []
    for row in rows:
        try:
            error = json.loads(row["error_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise _error("failed batch request error receipt is invalid") from exc
        if type(error) is not dict:
            raise _error("failed batch request error receipt is not one object")
        result.append(
            {
                "error": error,
                "physical_page": row["physical_page"],
                "request_id": row["request_id"],
            }
        )
    return result


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


def document_page_image_frontier_v1(
    path: Path,
    *,
    source_sha256: str,
    source_logical_name: str,
    expected_physical_pages: Sequence[int],
    render_dpi: int,
) -> dict[int, str]:
    """Return the unique stored image axis for one content-bound document.

    Corpus freezing uses this immutable ingestion receipt instead of rendering
    every PDF page a second time.  The caller still authenticates the source
    PDF bytes; this query proves which exact 300-DPI image each successful JSON
    version was derived from and refuses ambiguous re-renders.
    """

    pages = list(expected_physical_pages)
    if (
        type(source_sha256) is not str
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
        or type(source_logical_name) is not str
        or not source_logical_name
        or not pages
        or pages != sorted(set(pages))
        or any(type(page) is not int or page <= 0 for page in pages)
        or render_dpi not in {200, 300}
    ):
        raise _error("stored document page image frontier request is invalid")
    with _connect(path, readonly=True) as connection:
        documents = connection.execute(
            """
            SELECT document_id FROM document
            WHERE source_sha256=? AND source_logical_name=?
            ORDER BY document_id
            """,
            (source_sha256, source_logical_name),
        ).fetchall()
        if len(documents) != 1:
            raise _error("stored document identity is absent or ambiguous")
        rows = connection.execute(
            """
            SELECT physical_page, image_sha256
            FROM page
            WHERE document_id=? AND render_dpi=?
            ORDER BY physical_page, image_sha256
            """,
            (documents[0]["document_id"], render_dpi),
        ).fetchall()
    grouped: dict[int, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["physical_page"], []).append(row["image_sha256"])
    if set(grouped) != set(pages) or any(
        len(image_sha256s) != 1 for image_sha256s in grouped.values()
    ):
        raise _error("stored document page image frontier is incomplete or ambiguous")
    return {page: grouped[page][0] for page in pages}


def document_page_extraction_frontier_v1(
    path: Path,
    *,
    source_sha256: str,
    source_logical_name: str,
    expected_physical_pages: Sequence[int],
    render_dpi: int,
) -> dict[int, dict[str, str]]:
    """Recover a unique successful image/prompt pair for every document page."""

    pages = list(expected_physical_pages)
    if (
        type(source_sha256) is not str
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
        or type(source_logical_name) is not str
        or not source_logical_name
        or not pages
        or pages != sorted(set(pages))
        or any(type(page) is not int or page <= 0 for page in pages)
        or render_dpi not in {200, 300}
    ):
        raise _error("stored document extraction frontier request is invalid")
    with _connect(path, readonly=True) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT p.physical_page, p.image_sha256,
                            e.prompt_variant, e.prompt_sha256,
                            v.page_json_version_id
            FROM document AS d
            JOIN page AS p USING(document_id)
            JOIN extraction_run AS e USING(page_id)
            JOIN page_json_version AS v USING(extraction_run_id)
            WHERE d.source_sha256=? AND d.source_logical_name=? AND p.render_dpi=?
            ORDER BY p.physical_page, p.image_sha256, e.prompt_variant
            """,
            (source_sha256, source_logical_name, render_dpi),
        ).fetchall()
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        if not _is_selectable_extraction_receipt_v1(
            path,
            page_json_version_id=row["page_json_version_id"],
            prompt_variant=row["prompt_variant"],
        ):
            raise _error("stored document extraction prompt variant is invalid")
        grouped.setdefault(row["physical_page"], []).append(
            {
                "image_sha256": row["image_sha256"],
                "prompt_sha256": row["prompt_sha256"],
                "prompt_variant": row["prompt_variant"],
            }
        )
    if set(grouped) != set(pages) or any(len(records) != 1 for records in grouped.values()):
        raise _error("stored document extraction frontier is incomplete or ambiguous")
    return {page: grouped[page][0] for page in pages}


def selected_page_extraction_receipts_v1(
    path: Path,
    *,
    page_json_version_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Replay exact extraction provenance for a manifest-selected page axis."""

    version_ids = list(page_json_version_ids)
    if (
        not version_ids
        or len(set(version_ids)) != len(version_ids)
        or any(
            type(version_id) is not str
            or not version_id.startswith("gfpstorev1:json:")
            or len(version_id) != len("gfpstorev1:json:") + 64
            or any(
                character not in "0123456789abcdef"
                for character in version_id.removeprefix("gfpstorev1:json:")
            )
            for version_id in version_ids
        )
    ):
        raise _error("selected page extraction receipt frontier is invalid")
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_extraction_receipt("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_extraction_receipt VALUES (?,?)",
            enumerate(version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT s.selection_ordinal, s.page_json_version_id,
                   d.source_sha256, d.source_logical_name,
                   p.physical_page, p.image_sha256, p.render_dpi,
                   e.prompt_variant, e.prompt_sha256
            FROM selected_extraction_receipt AS s
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN extraction_run AS e USING(extraction_run_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            ORDER BY s.selection_ordinal
            """
        ).fetchall()
    if len(rows) != len(version_ids):
        raise _error("selected page extraction receipt is absent")
    result = []
    for ordinal, row in enumerate(rows, start=1):
        if (
            row["selection_ordinal"] != ordinal
            or row["page_json_version_id"] != version_ids[ordinal - 1]
        ):
            raise _error("selected page extraction receipt order or prompt is invalid")
        if not _is_selectable_extraction_receipt_v1(
            path,
            page_json_version_id=row["page_json_version_id"],
            prompt_variant=row["prompt_variant"],
        ):
            raise _error("selected page extraction receipt order or prompt is invalid")
        result.append(dict(row))
    return result


def selected_page_json_provenance_receipts_v1(
    path: Path,
    *,
    page_json_version_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Replay page provenance through extraction or an exact repair lineage.

    A manifest-selected base version must still come from one of the fixed
    page-extraction prompt variants.  A derived version may use a local
    algorithmic observation prompt, but only when the store contains a unique,
    content-addressed region-repair lineage whose base recursively reaches a
    selectable page extraction.  This keeps family queries independent of the
    repair prompt serialization without treating an arbitrary extraction run as
    corpus evidence.
    """

    version_ids = list(page_json_version_ids)
    if (
        not version_ids
        or len(set(version_ids)) != len(version_ids)
        or any(
            type(version_id) is not str
            or re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", version_id) is None
            for version_id in version_ids
        )
    ):
        raise _error("selected page JSON provenance frontier is invalid")

    def receipts_for(selected_ids: list[str]) -> list[dict[str, Any]]:
        with _connect(path, readonly=True) as connection:
            connection.execute(
                "CREATE TEMP TABLE selected_page_provenance("
                "selection_ordinal INTEGER PRIMARY KEY, "
                "page_json_version_id TEXT NOT NULL UNIQUE)"
            )
            connection.executemany(
                "INSERT INTO selected_page_provenance VALUES (?,?)",
                enumerate(selected_ids, start=1),
            )
            rows = connection.execute(
                """
                SELECT s.selection_ordinal, s.page_json_version_id,
                       d.source_sha256, d.source_logical_name,
                       p.physical_page, p.image_sha256, p.render_dpi,
                       e.prompt_variant, e.prompt_sha256
                FROM selected_page_provenance AS s
                JOIN page_json_version AS v USING(page_json_version_id)
                JOIN extraction_run AS e USING(extraction_run_id)
                JOIN page AS p USING(page_id)
                JOIN document AS d USING(document_id)
                ORDER BY s.selection_ordinal
                """
            ).fetchall()
        if len(rows) != len(selected_ids):
            raise _error("selected page JSON provenance is absent")
        result = [dict(row) for row in rows]
        if any(
            record["selection_ordinal"] != ordinal
            or record["page_json_version_id"] != selected_ids[ordinal - 1]
            for ordinal, record in enumerate(result, start=1)
        ):
            raise _error("selected page JSON provenance order drifted")
        return result

    root_receipts = receipts_for(version_ids)
    pending = []
    for record in root_receipts:
        if not _is_selectable_extraction_receipt_v1(
            path,
            page_json_version_id=record["page_json_version_id"],
            prompt_variant=record["prompt_variant"],
        ):
            pending.append(record["page_json_version_id"])
    visited: set[str] = set()
    while pending:
        if len(pending) != len(set(pending)) or any(
            version_id in visited for version_id in pending
        ):
            raise _error("selected page JSON repair provenance is cyclic or duplicate")
        visited.update(pending)
        try:
            lineages = page_json_region_repair_lineages_v1(
                path,
                observed_page_json_version_ids=pending,
            )
        except GeminiFinancialPageStoreV1Error as exc:
            raise _error(
                "selected page JSON provenance lacks selectable extraction or exact repair lineage"
            ) from exc
        if any(
            lineage["observed_page_json_version_id"] != version_id
            or lineage["canonical_merged_page_json_version_id"] != version_id
            for version_id, lineage in zip(pending, lineages, strict=True)
        ):
            raise _error("selected page JSON repair lineage does not bind its selected version")
        base_ids = [lineage["base_page_json_version_id"] for lineage in lineages]
        base_receipts = receipts_for(base_ids)
        pending = []
        for record in base_receipts:
            if not _is_selectable_extraction_receipt_v1(
                path,
                page_json_version_id=record["page_json_version_id"],
                prompt_variant=record["prompt_variant"],
            ):
                pending.append(record["page_json_version_id"])
    return root_receipts


def load_page_json_versions_v1(
    path: Path,
    *,
    page_json_version_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Load exact validated page JSON objects in the caller's selected order."""

    receipts = selected_page_json_provenance_receipts_v1(
        path,
        page_json_version_ids=page_json_version_ids,
    )
    version_ids = [receipt["page_json_version_id"] for receipt in receipts]
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_page_json_load("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_page_json_load VALUES (?,?)",
            enumerate(version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT s.selection_ordinal, s.page_json_version_id,
                   v.canonical_json_sha256, v.canonical_json_bytes
            FROM selected_page_json_load AS s
            JOIN page_json_version AS v USING(page_json_version_id)
            ORDER BY s.selection_ordinal
            """
        ).fetchall()
    if len(rows) != len(version_ids):
        raise _error("selected page JSON version is absent")
    result = []
    for receipt, row in zip(receipts, rows, strict=True):
        try:
            decoded = json.loads(row["canonical_json_bytes"])
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("selected page canonical JSON bytes are invalid") from exc
        page_json = validate_financial_page_json_v1(decoded)
        canonical = canonical_json_bytes_v1(page_json) + b"\n"
        if (
            row["page_json_version_id"] != receipt["page_json_version_id"]
            or canonical != row["canonical_json_bytes"]
            or sha256(canonical).hexdigest() != row["canonical_json_sha256"]
        ):
            raise _error("selected page canonical JSON does not replay")
        result.append({**receipt, "page_json": page_json})
    return result


def _distinct_anchor_assignment_exists_v1(hit_groups: Sequence[Sequence[str]]) -> bool:
    """Return whether every anchor group can bind a distinct visible row."""

    ordered = sorted((tuple(group) for group in hit_groups), key=lambda group: (len(group), group))

    def assign(group_ordinal: int, used: frozenset[str]) -> bool:
        if group_ordinal == len(ordered):
            return True
        return any(
            row_id not in used and assign(group_ordinal + 1, used | {row_id})
            for row_id in ordered[group_ordinal]
        )

    return assign(0, frozenset())


def _family_anchor_lookup_forms_v1(aliases: Sequence[str]) -> list[str]:
    """Bind semantic aliases to exact labels with harmless list markers."""

    return family_anchor_lookup_forms_v1(aliases)


def query_selected_family_anchor_hits_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    anchor_aliases: Sequence[str],
    explicit_parent_aliases: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Return one-anchor near evidence without granting a family match."""

    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
        or type(anchor_aliases) not in {list, tuple}
        or not anchor_aliases
        or type(explicit_parent_aliases) not in {list, tuple}
    ):
        raise _error("selected family near-anchor request is invalid")
    folded = _family_anchor_lookup_forms_v1(anchor_aliases)
    folded_parents = _family_anchor_lookup_forms_v1(explicit_parent_aliases)
    if any(not alias for alias in folded):
        raise _error("selected family near-anchor normalization is empty")
    selected_page_extraction_receipts_v1(
        path,
        page_json_version_ids=selected_page_json_version_ids,
    )
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_near_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_near_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        connection.execute(
            "CREATE TEMP TABLE near_anchor_alias(label_ascii_folded TEXT PRIMARY KEY)"
        )
        connection.executemany(
            "INSERT INTO near_anchor_alias VALUES (?)",
            ((alias,) for alias in folded),
        )
        connection.execute(
            "CREATE TEMP TABLE near_parent_alias(label_ascii_folded TEXT PRIMARY KEY)"
        )
        connection.executemany(
            "INSERT INTO near_parent_alias VALUES (?)",
            ((alias,) for alias in folded_parents),
        )
        rows = connection.execute(
            """
            SELECT s.selection_ordinal, r.page_json_version_id,
                   d.source_logical_name, p.physical_page,
                   r.section_id, r.table_id, r.row_id,
                   r.source_order, r.label_exact,
                   r.hierarchy_path_exact_json,
                   sn.title_exact AS section_title_exact,
                   t.title_exact AS table_title_exact,
                   EXISTS(
                     SELECT 1
                     FROM row_node AS parent_row
                     JOIN near_parent_alias AS parent_alias
                       ON parent_row.label_ascii_folded=parent_alias.label_ascii_folded
                       OR parent_row.label_ascii_folded LIKE
                          parent_alias.label_ascii_folded || ' %'
                     WHERE parent_row.page_json_version_id=r.page_json_version_id
                       AND parent_row.section_id=r.section_id
                       AND parent_row.table_id=r.table_id
                   ) AS table_has_explicit_parent_row
            FROM row_node AS r
            JOIN selected_near_page AS s USING(page_json_version_id)
            JOIN near_anchor_alias AS a USING(label_ascii_folded)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN section_node AS sn
              ON sn.page_json_version_id=r.page_json_version_id
             AND sn.section_id=r.section_id
            JOIN table_node AS t
              ON t.page_json_version_id=r.page_json_version_id
             AND t.section_id=r.section_id AND t.table_id=r.table_id
            ORDER BY s.selection_ordinal, r.section_id, r.table_id,
                     r.source_order, r.row_id
            """
        ).fetchall()
    result = []
    for row in rows:
        record = dict(row)
        try:
            hierarchy_path = json.loads(record.pop("hierarchy_path_exact_json"))
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("selected family near-anchor hierarchy path is invalid") from exc
        if type(hierarchy_path) is not list or any(
            value is not None and type(value) is not str for value in hierarchy_path
        ):
            raise _error("selected family near-anchor hierarchy path is invalid")
        record["hierarchy_path_exact"] = hierarchy_path
        result.append(record)
    return result


def _declared_surface_alias_match_v1(value: Any, aliases: Sequence[str]) -> str | None:
    """Return the unique longest declared phrase on one authenticated surface."""

    return declared_surface_alias_match_v1(value, aliases)


ROLLFORWARD_INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_ROLLFORWARD_QUERY_EVIDENCE_V1"
)


def query_selected_dual_component_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Coalesce exact seed siblings under one bounded owner/reset frontier.

    The bounded SQLite probe inventories every declared role alias while the
    two seed roles remain the only admission anchors.  Every hit page is then
    decoded and reclassified from its canonical JSON before a fragment can be
    admitted.  Numeric values are not used by coalescing.
    """

    from bctc_ai.evaluation.gemini_json_dual_component_accounting_family_v1 import (
        ENGINE_FORMAT_VERSION,
        _apply_authenticated_source_repairs_v1,
        build_gemini_json_indexed_dual_component_query_evidence_v1,
        coalesce_gemini_json_dual_component_page_v1,
        validate_gemini_json_indexed_dual_component_query_evidence_v1,
    )

    version_ids = list(selected_page_json_version_ids)
    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not version_ids
        or len(version_ids) != len(set(version_ids))
        or any(
            type(version_id) is not str
            or re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", version_id) is None
            for version_id in version_ids
        )
        or type(compiled_specs) is not dict
        or compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or type(compiled_specs.get("aliases_by_role")) is not dict
        or type(compiled_specs.get("components")) is not dict
        or type(compiled_specs.get("query_policy")) is not dict
    ):
        raise _error("selected dual-component family query is invalid")
    selected_page_extraction_receipts_v1(path, page_json_version_ids=version_ids)
    seed_role_by_component = {
        component_role: compiled_specs["components"][component_role]["seed_role"]
        for component_role in ("BALANCE", "DETAIL")
    }
    component_by_role = {
        role: component_role
        for component_role in ("BALANCE", "DETAIL")
        for role in compiled_specs["components"][component_role]["required_roles"]
        + compiled_specs["components"][component_role]["optional_roles"]
    }
    role_aliases = [
        (
            component_by_role[role],
            1 if role == seed_role_by_component[component_by_role[role]] else 0,
            role,
            alias,
        )
        for role, aliases in compiled_specs["aliases_by_role"].items()
        for alias in family_anchor_lookup_forms_v1(aliases)
    ]
    if not role_aliases or len(role_aliases) != len(set(role_aliases)):
        raise _error("selected dual-component role alias axis is invalid")
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_dual_component_page("
            "selected_page_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_dual_component_page VALUES (?,?)",
            enumerate(version_ids, start=1),
        )
        connection.execute(
            "CREATE TEMP TABLE dual_component_role_alias("
            "component_role TEXT NOT NULL, is_seed INTEGER NOT NULL, "
            "role TEXT NOT NULL, label_ascii_folded TEXT NOT NULL, "
            "PRIMARY KEY(role,label_ascii_folded))"
        )
        connection.executemany(
            "INSERT INTO dual_component_role_alias VALUES (?,?,?,?)", role_aliases
        )
        selected_rows = connection.execute(
            """
            SELECT selected.selected_page_ordinal,
                   selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page
            FROM selected_dual_component_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selected_page_ordinal
            """
        ).fetchall()
        if len(selected_rows) != len(version_ids):
            raise _error("selected dual-component page frontier is incomplete")
        role_rows = connection.execute(
            """
            SELECT selected.selected_page_ordinal,
                   row.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   row.section_id, row.table_id, row.row_id,
                   row.source_order, row.label_exact, alias.component_role,
                   alias.is_seed, alias.role
            FROM row_node AS row INDEXED BY idx_row_label_ascii
            JOIN dual_component_role_alias AS alias
              ON alias.label_ascii_folded=row.label_ascii_folded
            JOIN selected_dual_component_page AS selected
              USING(page_json_version_id)
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selected_page_ordinal,
                     CAST(SUBSTR(row.section_id,2) AS INTEGER),
                     CAST(SUBSTR(row.table_id,2) AS INTEGER),
                     row.source_order, row.row_id,
                     alias.component_role, alias.role
            """
        ).fetchall()
        candidate_version_ids = sorted(
            {row["page_json_version_id"] for row in role_rows},
            key=version_ids.index,
        )
        canonical_page_by_version: dict[str, dict[str, Any]] = {}
        if candidate_version_ids:
            connection.execute(
                "CREATE TEMP TABLE dual_component_candidate_page("
                "candidate_ordinal INTEGER PRIMARY KEY, "
                "page_json_version_id TEXT NOT NULL UNIQUE)"
            )
            connection.executemany(
                "INSERT INTO dual_component_candidate_page VALUES (?,?)",
                enumerate(candidate_version_ids, start=1),
            )
            for row in connection.execute(
                "SELECT candidate.page_json_version_id,version.canonical_json_bytes "
                "FROM dual_component_candidate_page AS candidate "
                "JOIN page_json_version AS version USING(page_json_version_id) "
                "ORDER BY candidate.candidate_ordinal"
            ):
                try:
                    page_json = json.loads(row["canonical_json_bytes"])
                except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise _error("selected dual-component canonical JSON is invalid") from exc
                if type(page_json) is not dict:
                    raise _error("selected dual-component canonical JSON is invalid")
                canonical_page_by_version[row["page_json_version_id"]] = page_json

    document_ordinals: dict[str, int] = {}
    selected_document_axis = []
    selected_by_version: dict[str, dict[str, Any]] = {}
    for raw in selected_rows:
        row = dict(raw)
        document_ordinal = document_ordinals.get(row["document_id"])
        if document_ordinal is None:
            document_ordinal = len(document_ordinals) + 1
            document_ordinals[row["document_id"]] = document_ordinal
            selected_document_axis.append(
                {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
            )
        selected_by_version[row["page_json_version_id"]] = {
            **row,
            "document_ordinal": document_ordinal,
        }
    if len(document_ordinals) != len(selected_document_axis):
        raise _error("selected dual-component document axis is ambiguous")
    indexed_role_hits = []
    for raw in role_rows:
        row = dict(raw)
        metadata = selected_by_version[row["page_json_version_id"]]
        indexed_role_hits.append(
            {
                "component_role": row["component_role"],
                "document_id": row["document_id"],
                "document_ordinal": metadata["document_ordinal"],
                "label_exact": row["label_exact"],
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "is_seed": bool(row["is_seed"]),
                "role": row["role"],
                "row_id": row["row_id"],
                "section_id": row["section_id"],
                "selected_page_ordinal": row["selected_page_ordinal"],
                "source_logical_name": row["source_logical_name"],
                "source_order": row["source_order"],
                "source_sha256": row["source_sha256"],
                "table_id": row["table_id"],
            }
        )
    coalesced_by_document: dict[int, list[dict[str, Any]]] = {}
    coalesced_by_version: dict[str, dict[str, Any]] = {}
    for version_id in candidate_version_ids:
        metadata = selected_by_version[version_id]
        base_locator = {
            key: metadata[key]
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
        page_json = canonical_page_by_version[version_id]
        repair = next(
            (
                item
                for item in compiled_specs.get("source_repairs", [])
                if item["base_page_json_version_id"] == version_id
                and item["source"]["source_sha256"] == metadata["source_sha256"]
            ),
            None,
        )
        if repair is not None:
            repair_regions = [
                {
                    **base_locator,
                    "section_id": item["section_id"],
                    "table_id": item["table_id"],
                }
                for item in repair["table_refs"]
            ]
            page_json = _apply_authenticated_source_repairs_v1(
                regions=repair_regions,
                page_json_by_version={version_id: page_json},
                compiled_specs=compiled_specs,
            )[0][version_id]
        coalesced = coalesce_gemini_json_dual_component_page_v1(
            page_json=page_json,
            locator=base_locator,
            compiled_specs=compiled_specs,
        )
        page_record = {**coalesced, "page_json_version_id": version_id}
        coalesced_by_version[version_id] = page_record
        coalesced_by_document.setdefault(metadata["document_ordinal"], []).append(page_record)
    accepted_clusters = []
    candidate_dispositions = []
    hits_by_document: dict[int, list[dict[str, Any]]] = {}
    for hit in indexed_role_hits:
        hits_by_document.setdefault(hit["document_ordinal"], []).append(hit)
    for document in selected_document_axis:
        ordinal = document["document_ordinal"]
        hits = hits_by_document.get(ordinal, [])
        document_pages = coalesced_by_document.get(ordinal, [])
        pages = [
            page
            for page in document_pages
            if page["fragments"]
            or any(
                item["population_disposition"]
                in {
                    "DECLARED_ROLE_ONLY_POPULATION",
                    "DECLARED_ROLE_MIXED_WITH_FOREIGN_POPULATION",
                }
                and item["owner"] is not None
                for item in page["role_bearing_fragments"]
            )
        ]
        reason_codes = sorted({reason for page in pages for reason in page["reasons"]})
        accepted = [page for page in pages if page["status"] == "ACCEPTED"]
        document_level_cluster_accepted = False
        if compiled_specs["query_policy"].get("max_page_span") == 1:
            seed_fragments = [
                fragment
                for page in pages
                for fragment in page["fragments"]
                if fragment.get("component_role") in {"BALANCE", "DETAIL"}
            ]
            seed_by_component = {
                component_role: [
                    fragment
                    for fragment in seed_fragments
                    if fragment["component_role"] == component_role
                ]
                for component_role in ("BALANCE", "DETAIL")
            }
            if all(len(seed_by_component[role]) == 1 for role in ("BALANCE", "DETAIL")):
                balance_seed = seed_by_component["BALANCE"][0]
                detail_seed = seed_by_component["DETAIL"][0]
                selected_fragments = [balance_seed, detail_seed]
                selected_locations = {
                    (
                        item["locator"]["page_json_version_id"],
                        item["locator"]["section_id"],
                        item["locator"]["table_id"],
                    )
                    for item in selected_fragments
                }
                for page in document_pages:
                    for fragment in page["role_bearing_fragments"]:
                        location = (
                            fragment["locator"]["page_json_version_id"],
                            fragment["locator"]["section_id"],
                            fragment["locator"]["table_id"],
                        )
                        if (
                            location not in selected_locations
                            and fragment.get("component_role") in {"BALANCE", "DETAIL"}
                            and fragment.get("continuation")
                            == "CONTINUES_FROM_PREVIOUS_PAGE"
                        ):
                            prior = [
                                item
                                for item in selected_fragments
                                if item["component_role"] == fragment["component_role"]
                                and item["locator"]["physical_page"] + 1
                                == fragment["locator"]["physical_page"]
                                and item.get("continuation") == "CONTINUES_ON_NEXT_PAGE"
                            ]
                            if len(prior) == 1:
                                selected_fragments.append(fragment)
                                selected_locations.add(location)
                selected_fragments.sort(
                    key=lambda item: (
                        item["locator"]["physical_page"],
                        item["locator"]["selected_page_ordinal"],
                        int(item["locator"]["section_id"][1:]),
                        int(item["locator"]["table_id"][1:]),
                    )
                )
                physical_pages = {
                    item["locator"]["physical_page"] for item in selected_fragments
                }
                seed_order = [
                    (
                        item["locator"]["physical_page"],
                        int(item["locator"]["section_id"][1:]),
                        int(item["locator"]["table_id"][1:]),
                    )
                    for item in (balance_seed, detail_seed)
                ]
                balance_owner = balance_seed.get("owner")
                detail_owner = detail_seed.get("owner")
                explicit_boundary = any(
                    item.get("continuation")
                    in {"CONTINUES_ON_NEXT_PAGE", "CONTINUES_FROM_PREVIOUS_PAGE"}
                    for item in selected_fragments
                )
                detail_starts_next_page = (
                    len(selected_fragments) == 2
                    and detail_seed["locator"]["physical_page"]
                    == balance_seed["locator"]["physical_page"] + 1
                    and detail_seed["locator"]["section_id"] == "s1"
                    and detail_seed["locator"]["table_id"] == "t1"
                )
                if (
                    balance_owner is not None
                    and (detail_owner is None or detail_owner == balance_owner)
                    and seed_order[0] < seed_order[1]
                    and len(physical_pages) == 2
                    and max(physical_pages) - min(physical_pages) <= 1
                    and (explicit_boundary or detail_starts_next_page)
                    and all(
                        1
                        <= sum(
                            item["component_role"] == component_role
                            for item in selected_fragments
                        )
                        <= 2
                        for component_role in ("BALANCE", "DETAIL")
                    )
                ):
                    accepted = [
                        {
                            "component_regions": [
                                canonical_clone_v1(item["locator"])
                                for item in selected_fragments
                            ],
                            "owner": canonical_clone_v1(balance_owner),
                            "status": "ACCEPTED",
                        }
                    ]
                    reason_codes = []
                    document_level_cluster_accepted = True
        if not pages:
            disposition = "NOT_OBSERVED"
        elif (
            len(accepted) == 1
            and not reason_codes
            and (len(pages) == 1 or document_level_cluster_accepted)
        ):
            disposition = "ACCEPTED_CLUSTER"
            accepted_clusters.append(
                {
                    "component_regions": canonical_clone_v1(accepted[0]["component_regions"]),
                    "document_ordinal": ordinal,
                    "owner": canonical_clone_v1(accepted[0]["owner"]),
                }
            )
        else:
            disposition = "UNRESOLVED_CLUSTER"
            if len(pages) != 1 and not document_level_cluster_accepted:
                reason_codes.append("EXACTLY_ONE_CANDIDATE_PAGE_PER_DOCUMENT_REQUIRED")
            if len(accepted) > 1:
                reason_codes.append("MULTIPLE_ACCEPTED_COMPONENT_CLUSTERS")
            if not reason_codes:
                reason_codes.append("PARTIAL_OR_AMBIGUOUS_SEED_FRONTIER")
        consumed_locations = (
            {
                (
                    item["page_json_version_id"],
                    item["section_id"],
                    item["table_id"],
                )
                for item in accepted[0]["component_regions"]
            }
            if disposition == "ACCEPTED_CLUSTER"
            else set()
        )
        active_hits = []
        for hit in hits:
            page = coalesced_by_version[hit["page_json_version_id"]]
            location = (
                hit["page_json_version_id"],
                hit["section_id"],
                hit["table_id"],
            )
            role_fragment = next(
                (
                    item
                    for item in page["role_bearing_fragments"]
                    if item["locator"]["section_id"] == hit["section_id"]
                    and item["locator"]["table_id"] == hit["table_id"]
                ),
                None,
            )
            hit_is_active = bool(hit["is_seed"]) or (
                role_fragment is not None
                and role_fragment["owner"] is not None
                and role_fragment["population_disposition"]
                in {
                    "DECLARED_ROLE_ONLY_POPULATION",
                    "DECLARED_ROLE_MIXED_WITH_FOREIGN_POPULATION",
                }
            )
            if location in consumed_locations:
                hit["query_disposition"] = "CONSUMED_ACCEPTED_COMPONENT_FRAGMENT"
                hit_is_active = True
            elif hit_is_active:
                hit["query_disposition"] = "UNCONSUMED_FAMILY_INTERVAL_ROLE_HIT"
            else:
                hit["query_disposition"] = (
                    "INCIDENTAL_ROLE_IN_FOREIGN_POPULATION"
                    if role_fragment is not None
                    and role_fragment["population_disposition"]
                    == "INCIDENTAL_ROLE_IN_FOREIGN_POPULATION"
                    else "OUTSIDE_DECLARED_OWNER_FENCE"
                )
            if hit_is_active:
                active_hits.append(hit)
        hit_receipts = [
            {
                "component_role": hit["component_role"],
                "is_seed": hit["is_seed"],
                "page_json_version_id": hit["page_json_version_id"],
                "query_disposition": hit["query_disposition"],
                "role": hit["role"],
                "row_id": hit["row_id"],
                "section_id": hit["section_id"],
                "table_id": hit["table_id"],
            }
            for hit in active_hits
        ]
        candidate_dispositions.append(
            {
                **canonical_clone_v1(document),
                "disposition": disposition,
                "indexed_role_hit_count": len(active_hits),
                "indexed_role_hit_receipts": hit_receipts,
                "reason_codes": sorted(set(reason_codes)),
            }
        )
    indexed_seed_hits = [canonical_clone_v1(hit) for hit in indexed_role_hits if hit["is_seed"]]
    evidence = build_gemini_json_indexed_dual_component_query_evidence_v1(
        selected_document_axis=selected_document_axis,
        indexed_role_hits=indexed_role_hits,
        indexed_seed_hits=indexed_seed_hits,
        accepted_clusters=accepted_clusters,
        candidate_dispositions=candidate_dispositions,
        selected_page_json_version_ids=version_ids,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_dual_component_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_dual_component_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Replay the public SQLite projection and reject any persisted drift."""

    from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1

    replayed = query_selected_dual_component_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if type(indexed_query_evidence) is not dict or not same_typed_json_v1(
        indexed_query_evidence, replayed
    ):
        raise _error("selected dual-component query evidence does not replay")
    return replayed


def validate_selected_dual_component_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Rebuild every accepted candidate from authenticated SQLite page JSON."""

    from bctc_ai.evaluation.gemini_json_dual_component_accounting_family_v1 import (
        build_gemini_json_dual_component_region_query_receipt_v1,
        validate_gemini_json_dual_component_family_candidate_replay_v1,
        validate_gemini_json_dual_component_sweep_query_bindings_v1,
    )

    evidence = validate_selected_dual_component_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_dual_component_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    accepted_clusters = evidence["accepted_clusters"]
    version_ids = list(
        dict.fromkeys(
            region["page_json_version_id"]
            for cluster in accepted_clusters
            for region in cluster["component_regions"]
        )
    )
    loaded = load_page_json_versions_v1(path, page_json_version_ids=version_ids)
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in loaded
    }
    if set(page_json_by_version) != set(version_ids):
        raise _error("selected dual-component candidate page JSON axis is incomplete")
    trial_by_ordinal = {trial["document_ordinal"]: trial for trial in checked_trials}
    replayed_ordinals = []
    for cluster in accepted_clusters:
        trial = trial_by_ordinal[cluster["document_ordinal"]]
        candidate = trial["candidates"][0]
        regions = cluster["component_regions"]
        validate_gemini_json_dual_component_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            query_receipt=build_gemini_json_dual_component_region_query_receipt_v1(regions),
        )
        replayed_ordinals.append(cluster["document_ordinal"])
    if replayed_ordinals != [cluster["document_ordinal"] for cluster in accepted_clusters]:
        raise _error("selected dual-component accepted candidate replay axis drifted")
    return checked_trials


def query_selected_customer_deposit_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Coalesce every selected document into one exhaustive customer-deposit disposition."""

    from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
        ENGINE_FORMAT_VERSION as CUSTOMER_DEPOSIT_ENGINE_FORMAT_VERSION,
    )
    from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
        build_gemini_json_indexed_customer_deposit_query_evidence_v1,
        coalesce_gemini_json_customer_deposit_document_v1,
        validate_gemini_json_indexed_customer_deposit_query_evidence_v1,
    )

    if (
        compiled_specs.get("engine_format_version") != CUSTOMER_DEPOSIT_ENGINE_FORMAT_VERSION
        or type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
    ):
        raise _error("selected customer-deposit family query is invalid")
    selected_page_extraction_receipts_v1(path, page_json_version_ids=selected_page_json_version_ids)
    documents = []
    selected_page_axis = []
    clusters = []
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_customer_deposit_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_customer_deposit_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        cursor = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   version.canonical_json_bytes
            FROM selected_customer_deposit_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        )
        current_document_id = None
        current_document = None
        current_pages = []
        seen_document_ids = set()
        document_ordinal = 0

        def seal_document() -> None:
            if current_document is None:
                return
            documents.append(canonical_clone_v1(current_document))
            clusters.append(
                coalesce_gemini_json_customer_deposit_document_v1(
                    page_records=current_pages,
                    compiled_specs=compiled_specs,
                )
            )

        row_count = 0
        for row in cursor:
            row_count += 1
            if row["document_id"] != current_document_id:
                seal_document()
                if row["document_id"] in seen_document_ids:
                    raise _error("selected customer-deposit document pages are not contiguous")
                seen_document_ids.add(row["document_id"])
                document_ordinal += 1
                current_document_id = row["document_id"]
                current_document = {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
                current_pages = []
            selected_page_ordinal = len(current_pages) + 1
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected customer-deposit canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("selected customer-deposit canonical page is not an object")
            page_axis_record = {
                **current_document,
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "selected_page_ordinal": selected_page_ordinal,
            }
            selected_page_axis.append(canonical_clone_v1(page_axis_record))
            current_pages.append({**page_axis_record, "page_json": page_json})
        seal_document()
    if row_count != len(selected_page_json_version_ids):
        raise _error("selected customer-deposit page frontier is incomplete")
    evidence = build_gemini_json_indexed_customer_deposit_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_customer_deposit_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_customer_deposit_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Re-query the selected SQLite frontier and exact-compare its evidence."""

    from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
        validate_gemini_json_indexed_customer_deposit_query_evidence_v1,
    )

    supplied = validate_gemini_json_indexed_customer_deposit_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    replayed = query_selected_customer_deposit_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("selected customer-deposit query evidence does not replay exactly")
    return replayed


def validate_selected_customer_deposit_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every accepted customer-deposit candidate from canonical page JSON."""

    from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
        build_gemini_json_customer_deposit_region_query_receipt_v1,
        validate_gemini_json_customer_deposit_family_candidate_replay_v1,
        validate_gemini_json_customer_deposit_sweep_query_bindings_v1,
    )

    evidence = validate_selected_customer_deposit_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_customer_deposit_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    page_axis_by_version = {
        item["page_json_version_id"]: item for item in evidence["selected_page_axis"]
    }
    page_json_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE replay_customer_deposit_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO replay_customer_deposit_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM replay_customer_deposit_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        for row in rows:
            axis = page_axis_by_version.get(row["page_json_version_id"])
            if axis is None:
                raise _error("customer-deposit replay page is outside selected evidence")
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("customer-deposit replay page JSON is invalid") from exc
            page_json_by_document.setdefault(axis["document_ordinal"], {})[
                row["page_json_version_id"]
            ] = page_json
    cluster_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for trial in checked_trials:
        if not trial["candidates"]:
            continue
        cluster = cluster_by_ordinal[trial["document_ordinal"]]
        regions = cluster["component_regions"]
        validate_gemini_json_customer_deposit_family_candidate_replay_v1(
            trial["candidates"][0],
            regions=regions,
            page_json_by_version=page_json_by_document[trial["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(regions),
        )
    return checked_trials


def query_selected_investment_securities_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Coalesce every selected document into one exhaustive securities disposition."""

    from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
        ENGINE_FORMAT_VERSION as INVESTMENT_SECURITIES_ENGINE_FORMAT_VERSION,
    )
    from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
        build_gemini_json_indexed_investment_securities_query_evidence_v1,
        coalesce_gemini_json_investment_securities_document_v1,
        validate_gemini_json_indexed_investment_securities_query_evidence_v1,
    )

    if (
        compiled_specs.get("engine_format_version") != INVESTMENT_SECURITIES_ENGINE_FORMAT_VERSION
        or type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
    ):
        raise _error("selected investment-securities family query is invalid")
    selected_page_extraction_receipts_v1(path, page_json_version_ids=selected_page_json_version_ids)
    documents = []
    selected_page_axis = []
    clusters = []
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_investment_securities_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_investment_securities_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        cursor = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   version.canonical_json_bytes
            FROM selected_investment_securities_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        )
        current_document_id = None
        current_document = None
        current_pages = []
        seen_document_ids = set()
        document_ordinal = 0

        def seal_document() -> None:
            if current_document is None:
                return
            documents.append(canonical_clone_v1(current_document))
            clusters.append(
                coalesce_gemini_json_investment_securities_document_v1(
                    page_records=current_pages,
                    compiled_specs=compiled_specs,
                )
            )

        row_count = 0
        for row in cursor:
            row_count += 1
            if row["document_id"] != current_document_id:
                seal_document()
                if row["document_id"] in seen_document_ids:
                    raise _error("selected investment-securities document pages are not contiguous")
                seen_document_ids.add(row["document_id"])
                document_ordinal += 1
                current_document_id = row["document_id"]
                current_document = {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
                current_pages = []
            selected_page_ordinal = len(current_pages) + 1
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error(
                    "selected investment-securities canonical page JSON is invalid"
                ) from exc
            if type(page_json) is not dict:
                raise _error("selected investment-securities canonical page is not an object")
            page_axis_record = {
                **current_document,
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "selected_page_ordinal": selected_page_ordinal,
            }
            selected_page_axis.append(canonical_clone_v1(page_axis_record))
            current_pages.append({**page_axis_record, "page_json": page_json})
        seal_document()
    if row_count != len(selected_page_json_version_ids):
        raise _error("selected investment-securities page frontier is incomplete")
    evidence = build_gemini_json_indexed_investment_securities_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_investment_securities_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_investment_securities_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Re-query the selected SQLite frontier and exact-compare its evidence."""

    from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
        validate_gemini_json_indexed_investment_securities_query_evidence_v1,
    )

    supplied = validate_gemini_json_indexed_investment_securities_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    replayed = query_selected_investment_securities_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("selected investment-securities query evidence does not replay exactly")
    return replayed


def validate_selected_investment_securities_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every accepted securities candidate from canonical page JSON."""

    from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
        build_gemini_json_investment_securities_region_query_receipt_v1,
        validate_gemini_json_investment_securities_family_candidate_replay_v1,
        validate_gemini_json_investment_securities_sweep_query_bindings_v1,
    )

    evidence = validate_selected_investment_securities_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_investment_securities_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    page_axis_by_version = {
        item["page_json_version_id"]: item for item in evidence["selected_page_axis"]
    }
    page_json_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE replay_investment_securities_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO replay_investment_securities_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM replay_investment_securities_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        for row in rows:
            axis = page_axis_by_version.get(row["page_json_version_id"])
            if axis is None:
                raise _error("investment-securities replay page is outside selected evidence")
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("investment-securities replay page JSON is invalid") from exc
            page_json_by_document.setdefault(axis["document_ordinal"], {})[
                row["page_json_version_id"]
            ] = page_json
    cluster_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for trial in checked_trials:
        if not trial["candidates"]:
            continue
        cluster = cluster_by_ordinal[trial["document_ordinal"]]
        regions = cluster["component_regions"]
        validate_gemini_json_investment_securities_family_candidate_replay_v1(
            trial["candidates"][0],
            regions=regions,
            page_json_by_version=page_json_by_document[trial["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_investment_securities_region_query_receipt_v1(regions)
            ),
        )
    return checked_trials


def _sealed_raw_table_context_reprojection_v1(
    *,
    page_json_version_id: str,
    canonical_page_json: Mapping[str, Any],
    raw_response_bytes: bytes,
    raw_response_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Recover only table captions discarded by an older canonicalizer.

    The immutable provider envelope remains the source.  A projection is
    admitted only when re-decoding it with the current small page contract
    changes one or more ``title_exact`` fields from null to source text and
    every other typed page field is byte-semantically identical.
    """

    if sha256(raw_response_bytes).hexdigest() != raw_response_sha256:
        raise _error("equity-matrix raw response content reference drifted")
    try:
        response_text = extract_completed_provider_response_text_v1(raw_response_bytes)
        projected = decode_financial_page_json_text_v1(response_text)
    except (GeminiFinancialPageJsonV1Error, GeminiJsonFirstProviderV1Error):
        return None
    base = canonical_clone_v1(dict(canonical_page_json))
    replay_without_titles = canonical_clone_v1(projected)
    if (
        type(base.get("sections")) is not list
        or type(replay_without_titles.get("sections")) is not list
        or len(base["sections"]) != len(replay_without_titles["sections"])
    ):
        return None
    title_axis = []
    for section_ordinal, (base_section, replay_section) in enumerate(
        zip(base["sections"], replay_without_titles["sections"], strict=True), start=1
    ):
        base_tables = base_section.get("tables") if type(base_section) is dict else None
        replay_tables = replay_section.get("tables") if type(replay_section) is dict else None
        if (
            type(base_tables) is not list
            or type(replay_tables) is not list
            or len(base_tables) != len(replay_tables)
        ):
            return None
        for table_ordinal, (base_table, replay_table) in enumerate(
            zip(base_tables, replay_tables, strict=True), start=1
        ):
            if type(base_table) is not dict or type(replay_table) is not dict:
                return None
            base_title = base_table.get("title_exact")
            replay_title = replay_table.get("title_exact")
            if replay_title != base_title:
                if (
                    base_title is not None
                    or type(replay_title) is not str
                    or not replay_title.strip()
                ):
                    return None
                title_axis.append(
                    {
                        "base_title_exact": None,
                        "projected_title_exact": replay_title,
                        "section_id": f"s{section_ordinal}",
                        "table_id": f"t{table_ordinal}",
                    }
                )
            replay_table["title_exact"] = base_title
    if not title_axis or not same_typed_json_v1(base, replay_without_titles):
        return None
    material = {
        "base_page_json_sha256": canonical_json_sha256_v1(base),
        "format_version": "GEMINI_JSON_SEALED_RAW_TABLE_CONTEXT_PROJECTION_V1",
        "page_json_version_id": page_json_version_id,
        "projected_page_json_sha256": canonical_json_sha256_v1(projected),
        "raw_response_sha256": raw_response_sha256,
        "rule": "ONLY_NULL_TABLE_TITLES_PROMOTED_FROM_AUTHENTICATED_OMITTED_TEXT_HEADERS",
        "title_projection_axis": title_axis,
    }
    receipt = {
        **material,
        "projection_receipt_sha256": canonical_json_sha256_v1(material),
    }
    return projected, receipt


def query_selected_equity_matrix_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Coalesce every selected document into one exhaustive equity matrix."""

    from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
        ENGINE_FORMAT_VERSION as EQUITY_MATRIX_ENGINE_FORMAT_VERSION,
    )
    from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
        build_gemini_json_indexed_equity_matrix_query_evidence_v1,
        coalesce_gemini_json_equity_matrix_document_v1,
        validate_gemini_json_indexed_equity_matrix_query_evidence_v1,
    )

    if (
        compiled_specs.get("engine_format_version") != EQUITY_MATRIX_ENGINE_FORMAT_VERSION
        or type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
    ):
        raise _error("selected equity-matrix family query is invalid")
    selected_page_json_provenance_receipts_v1(
        path, page_json_version_ids=selected_page_json_version_ids
    )
    documents = []
    selected_page_axis = []
    clusters = []
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_equity_matrix_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_equity_matrix_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        cursor = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   version.canonical_json_bytes, version.raw_response_sha256,
                   version.raw_response_bytes
            FROM selected_equity_matrix_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        )
        current_document_id = None
        current_document = None
        current_pages = []
        current_raw_by_version = {}
        seen_document_ids = set()
        document_ordinal = 0

        def seal_document() -> None:
            if current_document is None:
                return
            documents.append(canonical_clone_v1(current_document))
            cluster = coalesce_gemini_json_equity_matrix_document_v1(
                page_records=current_pages,
                compiled_specs=compiled_specs,
            )
            if (
                cluster["status"] == "UNRESOLVED_GEMINI_JSON_FAMILY"
                and "MULTIPLE_UNDATED_COMPONENT_ROW_MATRICES_UNDER_OWNER" in cluster["reasons"]
            ):
                target_versions = {
                    item["page_json_version_id"] for item in cluster["declared_table_inventory"]
                }
                projected_pages = canonical_clone_v1(current_pages)
                projection_receipts = []
                for record in projected_pages:
                    version_id = record["page_json_version_id"]
                    if version_id not in target_versions:
                        continue
                    raw = current_raw_by_version[version_id]
                    projection = _sealed_raw_table_context_reprojection_v1(
                        page_json_version_id=version_id,
                        canonical_page_json=record["page_json"],
                        raw_response_bytes=raw["raw_response_bytes"],
                        raw_response_sha256=raw["raw_response_sha256"],
                    )
                    if projection is None:
                        continue
                    record["page_json"], receipt = projection
                    projection_receipts.append(receipt)
                if projection_receipts:
                    projected_cluster = coalesce_gemini_json_equity_matrix_document_v1(
                        page_records=projected_pages,
                        compiled_specs=compiled_specs,
                    )
                    if (
                        projected_cluster["status"]
                        == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
                    ):
                        owner_receipt = canonical_clone_v1(projected_cluster["owner_receipt"])
                        owner_receipt["context_projection_receipts"] = projection_receipts
                        projected_cluster["owner_receipt"] = owner_receipt
                        material = {
                            key: value
                            for key, value in projected_cluster.items()
                            if key != "cluster_id"
                        }
                        projected_cluster["cluster_id"] = (
                            "gjeqmfv1:cluster:" + canonical_json_sha256_v1(material)
                        )
                        cluster = projected_cluster
            clusters.append(cluster)

        row_count = 0
        for row in cursor:
            row_count += 1
            if row["document_id"] != current_document_id:
                seal_document()
                if row["document_id"] in seen_document_ids:
                    raise _error("selected equity-matrix document pages are not contiguous")
                seen_document_ids.add(row["document_id"])
                document_ordinal += 1
                current_document_id = row["document_id"]
                current_document = {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
                current_pages = []
                current_raw_by_version = {}
            selected_page_ordinal = len(current_pages) + 1
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected equity-matrix canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("selected equity-matrix canonical page is not an object")
            page_axis_record = {
                **current_document,
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "selected_page_ordinal": selected_page_ordinal,
            }
            selected_page_axis.append(canonical_clone_v1(page_axis_record))
            current_pages.append({**page_axis_record, "page_json": page_json})
            current_raw_by_version[row["page_json_version_id"]] = {
                "raw_response_bytes": bytes(row["raw_response_bytes"]),
                "raw_response_sha256": row["raw_response_sha256"],
            }
        seal_document()
    if row_count != len(selected_page_json_version_ids):
        raise _error("selected equity-matrix page frontier is incomplete")
    evidence = build_gemini_json_indexed_equity_matrix_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_equity_matrix_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_equity_matrix_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Re-query the selected SQLite frontier and exact-compare its evidence."""

    from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
        validate_gemini_json_indexed_equity_matrix_query_evidence_v1,
    )

    supplied = validate_gemini_json_indexed_equity_matrix_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    replayed = query_selected_equity_matrix_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("selected equity-matrix query evidence does not replay exactly")
    return replayed


def validate_selected_equity_matrix_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every accepted matrix candidate from canonical page JSON."""

    from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
        build_gemini_json_equity_matrix_region_query_receipt_v1,
        validate_gemini_json_equity_matrix_family_candidate_replay_v1,
        validate_gemini_json_equity_matrix_sweep_query_bindings_v1,
    )

    evidence = validate_selected_equity_matrix_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_equity_matrix_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    page_axis_by_version = {
        item["page_json_version_id"]: item for item in evidence["selected_page_axis"]
    }
    page_json_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE replay_equity_matrix_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO replay_equity_matrix_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM replay_equity_matrix_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        for row in rows:
            axis = page_axis_by_version.get(row["page_json_version_id"])
            if axis is None:
                raise _error("equity-matrix replay page is outside selected evidence")
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("equity-matrix replay page JSON is invalid") from exc
            page_json_by_document.setdefault(axis["document_ordinal"], {})[
                row["page_json_version_id"]
            ] = page_json
    cluster_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for trial in checked_trials:
        if not trial["candidates"]:
            continue
        cluster = cluster_by_ordinal[trial["document_ordinal"]]
        regions = cluster["component_regions"]
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            trial["candidates"][0],
            regions=regions,
            page_json_by_version=page_json_by_document[trial["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                regions, owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
    return checked_trials


def query_selected_other_long_term_investments_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Coalesce every selected document into one exhaustive Family 17 disposition."""

    from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
        ENGINE_FORMAT_VERSION as OTHER_LONG_TERM_INVESTMENTS_ENGINE_FORMAT_VERSION,
    )
    from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
        build_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
        coalesce_gemini_json_other_long_term_investments_document_v1,
        validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
    )

    if (
        compiled_specs.get("engine_format_version")
        != OTHER_LONG_TERM_INVESTMENTS_ENGINE_FORMAT_VERSION
        or type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
    ):
        raise _error("selected other-long-term-investment family query is invalid")
    selected_page_extraction_receipts_v1(path, page_json_version_ids=selected_page_json_version_ids)
    documents = []
    selected_page_axis = []
    clusters = []
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_other_long_term_investments_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_other_long_term_investments_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        cursor = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   version.canonical_json_bytes
            FROM selected_other_long_term_investments_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        )
        current_document_id = None
        current_document = None
        current_pages = []
        seen_document_ids = set()
        document_ordinal = 0

        def seal_document() -> None:
            if current_document is None:
                return
            documents.append(canonical_clone_v1(current_document))
            clusters.append(
                coalesce_gemini_json_other_long_term_investments_document_v1(
                    page_records=current_pages,
                    compiled_specs=compiled_specs,
                )
            )

        row_count = 0
        for row in cursor:
            row_count += 1
            if row["document_id"] != current_document_id:
                seal_document()
                if row["document_id"] in seen_document_ids:
                    raise _error("selected other-long-term-investment pages are not contiguous")
                seen_document_ids.add(row["document_id"])
                document_ordinal += 1
                current_document_id = row["document_id"]
                current_document = {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
                current_pages = []
            selected_page_ordinal = len(current_pages) + 1
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected other-long-term-investment page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("selected other-long-term-investment page is not an object")
            page_axis_record = {
                **current_document,
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "selected_page_ordinal": selected_page_ordinal,
            }
            selected_page_axis.append(canonical_clone_v1(page_axis_record))
            current_pages.append({**page_axis_record, "page_json": page_json})
        seal_document()
    if row_count != len(selected_page_json_version_ids):
        raise _error("selected other-long-term-investment page frontier is incomplete")
    evidence = build_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_other_long_term_investments_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Re-query SQLite and exact-compare the exhaustive Family 17 evidence."""

    from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
        validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1,
    )

    supplied = validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    replayed = query_selected_other_long_term_investments_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("selected other-long-term-investment query evidence does not replay")
    return replayed


def validate_selected_other_long_term_investments_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every accepted Family 17 candidate from canonical SQLite JSON."""

    from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
        build_gemini_json_other_long_term_investments_region_query_receipt_v1,
        validate_gemini_json_other_long_term_investments_family_candidate_replay_v1,
        validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1,
    )

    evidence = validate_selected_other_long_term_investments_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    page_axis_by_version = {
        item["page_json_version_id"]: item for item in evidence["selected_page_axis"]
    }
    page_json_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE replay_other_long_term_investments_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO replay_other_long_term_investments_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM replay_other_long_term_investments_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        for row in rows:
            axis = page_axis_by_version.get(row["page_json_version_id"])
            if axis is None:
                raise _error("other-long-term-investment replay page is outside selected evidence")
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("other-long-term-investment replay page JSON is invalid") from exc
            page_json_by_document.setdefault(axis["document_ordinal"], {})[
                row["page_json_version_id"]
            ] = page_json
    cluster_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for trial in checked_trials:
        if not trial["candidates"]:
            continue
        cluster = cluster_by_ordinal[trial["document_ordinal"]]
        regions = cluster["component_regions"]
        validate_gemini_json_other_long_term_investments_family_candidate_replay_v1(
            trial["candidates"][0],
            regions=regions,
            page_json_by_version=page_json_by_document[trial["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_other_long_term_investments_region_query_receipt_v1(regions)
            ),
        )
    return checked_trials


def query_selected_multitable_hierarchical_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Coalesce every selected document into one exhaustive multi-table disposition."""

    from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
        ENGINE_FORMAT_VERSION as MULTITABLE_HIERARCHICAL_ENGINE_FORMAT_VERSION,
    )
    from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
        build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
        coalesce_gemini_json_multitable_hierarchical_document_v1,
        validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    )

    if (
        compiled_specs.get("engine_format_version") != MULTITABLE_HIERARCHICAL_ENGINE_FORMAT_VERSION
        or type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
    ):
        raise _error("selected multi-table hierarchical family query is invalid")
    selected_page_json_provenance_receipts_v1(
        path, page_json_version_ids=selected_page_json_version_ids
    )
    documents = []
    selected_page_axis = []
    clusters = []
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_multitable_hierarchical_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_multitable_hierarchical_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        cursor = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   version.canonical_json_bytes
            FROM selected_multitable_hierarchical_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        )
        current_document_id = None
        current_document = None
        current_pages = []
        seen_document_ids = set()
        document_ordinal = 0

        def seal_document() -> None:
            if current_document is None:
                return
            documents.append(canonical_clone_v1(current_document))
            clusters.append(
                coalesce_gemini_json_multitable_hierarchical_document_v1(
                    page_records=current_pages,
                    compiled_specs=compiled_specs,
                )
            )

        row_count = 0
        for row in cursor:
            row_count += 1
            if row["document_id"] != current_document_id:
                seal_document()
                if row["document_id"] in seen_document_ids:
                    raise _error("selected multi-table hierarchical pages are not contiguous")
                seen_document_ids.add(row["document_id"])
                document_ordinal += 1
                current_document_id = row["document_id"]
                current_document = {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
                current_pages = []
            selected_page_ordinal = len(current_pages) + 1
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected multi-table hierarchical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("selected multi-table hierarchical page is not an object")
            page_axis_record = {
                **current_document,
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "selected_page_ordinal": selected_page_ordinal,
            }
            selected_page_axis.append(canonical_clone_v1(page_axis_record))
            current_pages.append({**page_axis_record, "page_json": page_json})
        seal_document()
    if row_count != len(selected_page_json_version_ids):
        raise _error("selected multi-table hierarchical page frontier is incomplete")
    evidence = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_multitable_hierarchical_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Re-query SQLite and exact-compare exhaustive multi-table evidence."""

    from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
        validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    )

    supplied = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    replayed = query_selected_multitable_hierarchical_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("selected multi-table hierarchical query evidence does not replay")
    return replayed


def validate_selected_multitable_hierarchical_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every accepted candidate from canonical selected SQLite JSON."""

    from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
        build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
        validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
    )

    evidence = validate_selected_multitable_hierarchical_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    page_axis_by_version = {
        item["page_json_version_id"]: item for item in evidence["selected_page_axis"]
    }
    page_json_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE replay_multitable_hierarchical_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO replay_multitable_hierarchical_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM replay_multitable_hierarchical_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        for row in rows:
            axis = page_axis_by_version.get(row["page_json_version_id"])
            if axis is None:
                raise _error("multi-table hierarchical replay page is outside evidence")
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("multi-table hierarchical replay page JSON is invalid") from exc
            page_json_by_document.setdefault(axis["document_ordinal"], {})[
                row["page_json_version_id"]
            ] = page_json
    cluster_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for trial in checked_trials:
        if not trial["candidates"]:
            continue
        cluster = cluster_by_ordinal[trial["document_ordinal"]]
        regions = cluster["component_regions"]
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            trial["candidates"][0],
            regions=regions,
            page_json_by_version=page_json_by_document[trial["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
            ),
        )
    return checked_trials


def query_selected_fixed_asset_rollforward_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild exhaustive fixed-asset document dispositions from SQLite JSON."""

    from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
        ENGINE_FORMAT_VERSION as FIXED_ASSET_ENGINE_FORMAT_VERSION,
    )
    from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
        build_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1,
        coalesce_gemini_json_fixed_asset_rollforward_document_v1,
        validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1,
    )

    if (
        compiled_specs.get("engine_format_version") != FIXED_ASSET_ENGINE_FORMAT_VERSION
        or type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
    ):
        raise _error("selected fixed-asset family query is invalid")
    selected_page_extraction_receipts_v1(path, page_json_version_ids=selected_page_json_version_ids)
    documents = []
    selected_page_axis = []
    clusters = []
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_fixed_asset_rollforward_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_fixed_asset_rollforward_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        cursor = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   version.canonical_json_bytes
            FROM selected_fixed_asset_rollforward_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        )
        current_document_id = None
        current_document = None
        current_pages = []
        seen_document_ids = set()
        document_ordinal = 0

        def seal_document() -> None:
            if current_document is None:
                return
            documents.append(canonical_clone_v1(current_document))
            clusters.append(
                coalesce_gemini_json_fixed_asset_rollforward_document_v1(
                    page_records=current_pages,
                    compiled_specs=compiled_specs,
                )
            )

        row_count = 0
        for row in cursor:
            row_count += 1
            if row["document_id"] != current_document_id:
                seal_document()
                if row["document_id"] in seen_document_ids:
                    raise _error("selected fixed-asset pages are not document-contiguous")
                seen_document_ids.add(row["document_id"])
                document_ordinal += 1
                current_document_id = row["document_id"]
                current_document = {
                    "document_id": row["document_id"],
                    "document_ordinal": document_ordinal,
                    "source_logical_name": row["source_logical_name"],
                    "source_sha256": row["source_sha256"],
                }
                current_pages = []
            selected_page_ordinal = len(current_pages) + 1
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected fixed-asset page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("selected fixed-asset page is not an object")
            page_axis_record = {
                **current_document,
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "selected_page_ordinal": selected_page_ordinal,
            }
            selected_page_axis.append(canonical_clone_v1(page_axis_record))
            current_pages.append({**page_axis_record, "page_json": page_json})
        seal_document()
    if row_count != len(selected_page_json_version_ids):
        raise _error("selected fixed-asset page frontier is incomplete")
    evidence = build_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
        evidence, compiled_specs=compiled_specs
    )


def validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Re-query SQLite and exact-compare fixed-asset indexed evidence."""

    from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
        validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1,
    )

    supplied = validate_gemini_json_indexed_fixed_asset_rollforward_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    replayed = query_selected_fixed_asset_rollforward_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("selected fixed-asset query evidence does not replay")
    return replayed


def validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every fixed-asset candidate from canonical selected page bytes."""

    from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
        build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1,
        validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1,
        validate_gemini_json_fixed_asset_rollforward_sweep_query_bindings_v1,
    )

    evidence = validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    checked_trials = validate_gemini_json_fixed_asset_rollforward_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )
    page_axis_by_version = {
        item["page_json_version_id"]: item for item in evidence["selected_page_axis"]
    }
    page_json_by_document: dict[int, dict[str, dict[str, Any]]] = {}
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE replay_fixed_asset_rollforward_page("
            "selection_ordinal INTEGER PRIMARY KEY, "
            "page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO replay_fixed_asset_rollforward_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM replay_fixed_asset_rollforward_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        for row in rows:
            axis = page_axis_by_version.get(row["page_json_version_id"])
            if axis is None:
                raise _error("fixed-asset replay page is outside selected evidence")
            try:
                page_json = json.loads(bytes(row["canonical_json_bytes"]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("fixed-asset replay page JSON is invalid") from exc
            page_json_by_document.setdefault(axis["document_ordinal"], {})[
                row["page_json_version_id"]
            ] = page_json
    cluster_by_ordinal = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for trial in checked_trials:
        if not trial["candidates"]:
            continue
        cluster = cluster_by_ordinal[trial["document_ordinal"]]
        regions = cluster["component_regions"]
        controls = cluster["control_regions"]
        validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1(
            trial["candidates"][0],
            regions=regions,
            control_regions=controls,
            page_json_by_version=page_json_by_document[trial["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
                regions, control_regions=controls
            ),
        )
    return checked_trials


def query_selected_rollforward_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Project exact roll-forward components from one selected SQLite frontier.

    Endpoint rows are the only broad indexed probe.  The query then reconstructs
    the candidate-local section title/narratives, table title, column-header and
    complete row-hierarchy axes needed by the public roll-forward classifier.
    Values are deliberately not read here: numeric authority remains with the
    later exact-page evaluator.  No source name, bank, page number, note number,
    or geometry participates in admission.
    """

    from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
        _DATE_DMY,
        _DATE_WORDS,
        ENGINE_FORMAT_VERSION,
        GeminiJsonRollforwardAccountingFamilyV1Error,
        _bounded_population_reset_fence_v1,
        _canonical_money_units_from_surface_v1,
        _date_token,
        _date_tokens,
        _normalized,
        _role_for_row,
        build_gemini_json_rollforward_complementary_continuation_v1,
        build_gemini_json_rollforward_following_owner_backbinding_v1,
        classify_gemini_json_rollforward_cluster_layout_v1,
        classify_gemini_json_rollforward_table_v1,
    )

    version_ids = list(selected_page_json_version_ids)
    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not version_ids
        or len(version_ids) != len(set(version_ids))
        or any(
            type(version_id) is not str
            or re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", version_id) is None
            for version_id in version_ids
        )
        or type(compiled_specs) is not dict
        or compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or type(compiled_specs.get("aliases_by_role")) is not dict
        or type(compiled_specs.get("layout")) is not dict
        or type(compiled_specs.get("topology")) is not dict
    ):
        raise _error("selected roll-forward family query is invalid")

    layout = compiled_specs["layout"]
    movement_specs = layout.get("movement_roles")
    if type(movement_specs) is not list:
        raise _error("selected roll-forward movement axis is invalid")
    endpoint_roles = {
        item["role"]
        for item in movement_specs
        if type(item) is dict and item.get("kind") in {"OPENING", "CLOSING"}
    }
    if len(endpoint_roles) != 2:
        raise _error("selected roll-forward endpoint axis is invalid")
    endpoint_prefixes = sorted(
        {
            "ngay",
            "tai",
            *(
                alias.split()[0]
                for role in endpoint_roles
                for alias in compiled_specs["aliases_by_role"].get(role, [])
                if type(alias) is str and alias.split()
            ),
        }
    )
    if any(not re.fullmatch(r"[a-z0-9]+", prefix) for prefix in endpoint_prefixes):
        raise _error("selected roll-forward endpoint prefix axis is invalid")

    query_policy = {
        "aliases_by_role": compiled_specs["aliases_by_role"],
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "family_id": compiled_specs["topology"]["family_id"],
        "layout": layout,
    }
    query_policy_sha256 = canonical_json_sha256_v1(query_policy)
    selected_page_json_provenance_receipts_v1(path, page_json_version_ids=version_ids)

    def decode_string_axis(raw: Any, *, label: str) -> list[Any]:
        try:
            value = json.loads(raw)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error(f"selected roll-forward {label} axis is invalid") from exc
        if type(value) is not list:
            raise _error(f"selected roll-forward {label} axis is invalid")
        return value

    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_rollforward_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_rollforward_page VALUES (?,?)",
            enumerate(version_ids, start=1),
        )
        selected_rows = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page
            FROM selected_rollforward_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        ).fetchall()
        if len(selected_rows) != len(version_ids):
            raise _error("selected roll-forward page JSON version is absent")
        canonical_page_by_version = {}
        for row in connection.execute(
            "SELECT page_json_version_id,canonical_json_bytes FROM page_json_version "
            "JOIN selected_rollforward_page USING(page_json_version_id)"
        ):
            try:
                page_json = json.loads(row["canonical_json_bytes"])
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected roll-forward canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("selected roll-forward canonical page JSON is invalid")
            canonical_page_by_version[row["page_json_version_id"]] = page_json
        if set(canonical_page_by_version) != set(version_ids):
            raise _error("selected roll-forward canonical page frontier is incomplete")
        locations = [(row["source_logical_name"], row["physical_page"]) for row in selected_rows]
        if len(locations) != len(set(locations)) or locations != sorted(locations):
            raise _error("selected roll-forward frontier is repeated or not in corpus order")

        document_ordinals: dict[str, int] = {}
        selected_document_axis: list[dict[str, Any]] = []
        selected_by_version: dict[str, dict[str, Any]] = {}
        selected_source_axis = []
        for row in selected_rows:
            record = dict(row)
            ordinal = document_ordinals.get(record["document_id"])
            if ordinal is None:
                ordinal = len(document_ordinals) + 1
                document_ordinals[record["document_id"]] = ordinal
                selected_document_axis.append(
                    {
                        "document_id": record["document_id"],
                        "document_ordinal": ordinal,
                        "source_logical_name": record["source_logical_name"],
                        "source_sha256": record["source_sha256"],
                    }
                )
            else:
                selected_document = selected_document_axis[ordinal - 1]
                if (
                    selected_document["source_logical_name"] != record["source_logical_name"]
                    or selected_document["source_sha256"] != record["source_sha256"]
                ):
                    raise _error("selected roll-forward document source identity drifted")
            record["document_ordinal"] = ordinal
            selected_by_version[record["page_json_version_id"]] = record
            selected_source_axis.append(record)

        endpoint_seed_by_identity: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for prefix in endpoint_prefixes:
            for row in connection.execute(
                """
                SELECT selected.selection_ordinal, rn.page_json_version_id,
                       rn.section_id, rn.table_id, rn.row_id, rn.source_order,
                       rn.label_exact, rn.hierarchy_path_exact_json, rn.row_kind,
                       rn.parent_row_id, rn.previous_row_id, rn.next_row_id
                FROM row_node AS rn INDEXED BY idx_row_label_ascii
                JOIN selected_rollforward_page AS selected USING(page_json_version_id)
                WHERE rn.label_ascii_folded GLOB ?
                ORDER BY selected.selection_ordinal, rn.section_id, rn.table_id,
                         rn.source_order, rn.row_id
                """,
                (prefix + "*",),
            ):
                record = dict(row)
                try:
                    role = _role_for_row(record, compiled_specs=compiled_specs)
                except GeminiJsonRollforwardAccountingFamilyV1Error:
                    role = "AMBIGUOUS_ENDPOINT_SEED"
                if (
                    role not in endpoint_roles | {"AMBIGUOUS_ENDPOINT_SEED"}
                    and _date_token(record.get("label_exact")) is None
                ):
                    continue
                identity = (
                    record["page_json_version_id"],
                    record["section_id"],
                    record["table_id"],
                    record["row_id"],
                )
                endpoint_seed_by_identity[identity] = record

        candidate_keys = sorted(
            {identity[:3] for identity in endpoint_seed_by_identity},
            key=lambda key: (
                selected_by_version[key[0]]["selection_ordinal"],
                int(key[1][1:]),
                int(key[2][1:]),
            ),
        )
        connection.execute(
            "CREATE TEMP TABLE rollforward_candidate_table("
            "page_json_version_id TEXT NOT NULL, section_id TEXT NOT NULL, "
            "table_id TEXT NOT NULL, PRIMARY KEY(page_json_version_id,section_id,table_id))"
        )
        connection.executemany(
            "INSERT INTO rollforward_candidate_table VALUES (?,?,?)",
            candidate_keys,
        )
        context_rows = connection.execute(
            """
            SELECT candidate.page_json_version_id, candidate.section_id,
                   candidate.table_id, section.source_order AS section_source_order,
                   section.content_kind, section.statement_type,
                   section.title_exact AS section_title_exact,
                   section.narratives_json,
                   table_node.source_order AS table_source_order,
                   table_node.title_exact AS table_title_exact,
                   table_node.unit_exact, table_node.continuation
            FROM rollforward_candidate_table AS candidate
            JOIN section_node AS section
              USING(page_json_version_id,section_id)
            JOIN table_node
              USING(page_json_version_id,section_id,table_id)
            ORDER BY candidate.page_json_version_id, section.source_order,
                     table_node.source_order, candidate.section_id, candidate.table_id
            """
        ).fetchall()
        column_rows = connection.execute(
            """
            SELECT column_node.page_json_version_id, column_node.section_id,
                   column_node.table_id, column_node.column_id,
                   column_node.column_ordinal, column_node.header_path_exact_json,
                   column_node.value_kind
            FROM column_node
            JOIN rollforward_candidate_table
              USING(page_json_version_id,section_id,table_id)
            ORDER BY column_node.page_json_version_id, column_node.section_id,
                     column_node.table_id, column_node.column_ordinal, column_node.column_id
            """
        ).fetchall()
        full_row_rows = connection.execute(
            """
            SELECT row_node.page_json_version_id, row_node.section_id,
                   row_node.table_id, row_node.row_id, row_node.source_order,
                   row_node.label_exact, row_node.hierarchy_path_exact_json,
                   row_node.row_kind, row_node.parent_row_id,
                   row_node.previous_row_id, row_node.next_row_id
            FROM row_node
            JOIN rollforward_candidate_table
              USING(page_json_version_id,section_id,table_id)
            ORDER BY row_node.page_json_version_id, row_node.section_id,
                     row_node.table_id, row_node.source_order, row_node.row_id
            """
        ).fetchall()
        document_table_unit_rows = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   table_node.section_id, table_node.table_id,
                   NULL AS column_id, 'TABLE_UNIT' AS source_kind,
                   table_node.unit_exact AS text_exact
            FROM selected_rollforward_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            JOIN table_node USING(page_json_version_id)
            WHERE table_node.unit_exact IS NOT NULL
            ORDER BY selected.selection_ordinal, table_node.section_id,
                     table_node.table_id
            """
        ).fetchall()
        document_section_title_rows = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   section_node.section_id, NULL AS table_id, NULL AS column_id,
                   'ANNUAL_REPORTING_SECTION_TITLE' AS source_kind,
                   section_node.title_exact AS text_exact
            FROM selected_rollforward_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            JOIN section_node USING(page_json_version_id)
            WHERE section_node.title_exact IS NOT NULL
            ORDER BY selected.selection_ordinal, section_node.source_order,
                     section_node.section_id
            """
        ).fetchall()
        document_balance_column_rows = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   section_node.section_id, column_node.table_id,
                   column_node.column_id, column_node.column_ordinal,
                   column_node.header_path_exact_json
            FROM selected_rollforward_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            JOIN section_node USING(page_json_version_id)
            JOIN column_node USING(page_json_version_id,section_id)
            WHERE version.page_status='PRIMARY_FINANCIAL_STATEMENT'
              AND section_node.content_kind='PRIMARY_STATEMENT'
              AND section_node.statement_type='BALANCE_SHEET'
              AND column_node.value_kind='MONEY'
            ORDER BY selected.selection_ordinal, section_node.source_order,
                     column_node.table_id, column_node.column_ordinal,
                     column_node.column_id
            """
        ).fetchall()

    context_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in context_rows:
        record = dict(row)
        record["narratives_exact"] = decode_string_axis(
            record.pop("narratives_json"), label="narrative"
        )
        if any(type(value) is not str for value in record["narratives_exact"]):
            raise _error("selected roll-forward narrative axis is invalid")
        key = (record["page_json_version_id"], record["section_id"], record["table_id"])
        context_by_key[key] = record
    columns_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in column_rows:
        record = dict(row)
        record["header_path_exact"] = decode_string_axis(
            record.pop("header_path_exact_json"), label="column-header"
        )
        if any(
            value is not None and type(value) is not str for value in record["header_path_exact"]
        ):
            raise _error("selected roll-forward column-header axis is invalid")
        key = (record.pop("page_json_version_id"), record.pop("section_id"), record.pop("table_id"))
        columns_by_key.setdefault(key, []).append(record)
    rows_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in full_row_rows:
        record = dict(row)
        record["hierarchy_path_exact"] = decode_string_axis(
            record.pop("hierarchy_path_exact_json"), label="row-hierarchy"
        )
        if any(
            value is not None and type(value) is not str for value in record["hierarchy_path_exact"]
        ):
            raise _error("selected roll-forward row-hierarchy axis is invalid")
        key = (record.pop("page_json_version_id"), record.pop("section_id"), record.pop("table_id"))
        rows_by_key.setdefault(key, []).append(record)

    candidate_dispositions: list[dict[str, Any]] = []
    dispositions_by_source: dict[str, list[dict[str, Any]]] = {}
    for key in candidate_keys:
        selected = selected_by_version[key[0]]
        context = context_by_key.get(key)
        columns = columns_by_key.get(key, [])
        rows = rows_by_key.get(key, [])
        if context is None:
            raise _error("selected roll-forward candidate context is absent")
        context_axis = {
            field: context[field]
            for field in (
                "content_kind",
                "continuation",
                "narratives_exact",
                "section_source_order",
                "section_title_exact",
                "statement_type",
                "table_source_order",
                "table_title_exact",
                "unit_exact",
            )
        }
        locator = {
            "document_id": selected["document_id"],
            "page_json_version_id": key[0],
            "physical_page": selected["physical_page"],
            "section_id": key[1],
            "source_logical_name": selected["source_logical_name"],
            "source_sha256": selected["source_sha256"],
            "table_id": key[2],
        }
        context_axis_sha256 = canonical_json_sha256_v1(context_axis)
        column_axis_sha256 = canonical_json_sha256_v1(columns)
        row_axis_sha256 = canonical_json_sha256_v1(rows)
        candidate_material = {
            "column_axis_sha256": column_axis_sha256,
            "context_axis_sha256": context_axis_sha256,
            "document_ordinal": selected["document_ordinal"],
            "locator": locator,
            "query_policy_sha256": query_policy_sha256,
            "row_axis_sha256": row_axis_sha256,
            "selected_page_ordinal": selected["selection_ordinal"],
        }
        candidate_evidence_sha256 = canonical_json_sha256_v1(candidate_material)
        page_json = canonical_page_by_version[key[0]]
        try:
            section = page_json["sections"][int(key[1][1:]) - 1]
            table = section["tables"][int(key[2][1:]) - 1]
        except (IndexError, KeyError, TypeError) as exc:
            raise _error("selected roll-forward canonical table locator is invalid") from exc
        classification: dict[str, Any] | None
        try:
            classification = classify_gemini_json_rollforward_table_v1(
                section=section,
                table=table,
                compiled_specs=compiled_specs,
            )
        except GeminiJsonRollforwardAccountingFamilyV1Error:
            classification = None
        if classification is None:
            disposition_kind = "LOCAL_TABLE_CLASSIFICATION_ERROR"
            reason_codes = ["ROLLFORWARD_LOCAL_TABLE_CLASSIFICATION_ERROR"]
        else:
            reason_codes = list(classification["reasons"])
            if (
                classification["context_reset_visible"]
                or classification["structural_hard_negative_visible"]
            ):
                disposition_kind = "RESET_OR_HARD_NEGATIVE_VETO"
            elif reason_codes:
                disposition_kind = (
                    "CORE_MOVEMENT_TOPOLOGY_INCOMPLETE"
                    if "ROLLFORWARD_CORE_MOVEMENT_ROLES_INCOMPLETE" in reason_codes
                    else "LANE_OR_PERIOD_AXIS_UNCLASSIFIED"
                )
            elif not classification["local_owner_visible"]:
                disposition_kind = "LOCAL_OWNER_NOT_VISIBLE"
            else:
                disposition_kind = "ACCEPTED_COMPONENT"
        disposition = {
            **locator,
            "candidate_evidence_sha256": candidate_evidence_sha256,
            "classification": canonical_clone_v1(classification),
            "column_axis_sha256": column_axis_sha256,
            "continuation_cluster_admission": None,
            "context_axis_sha256": context_axis_sha256,
            "disposition": disposition_kind,
            "document_ordinal": selected["document_ordinal"],
            "query_policy_sha256": query_policy_sha256,
            "reason_codes": reason_codes,
            "row_axis_sha256": row_axis_sha256,
            "selected_page_ordinal": selected["selection_ordinal"],
        }
        candidate_dispositions.append(disposition)
        dispositions_by_source.setdefault(locator["source_logical_name"], []).append(disposition)

    accepted_regions: list[dict[str, Any]] = []
    layout_counts = {
        "LANE_TABLES_PERIOD_COLUMNS": 0,
        "PERIOD_TABLES_LANE_COLUMNS": 0,
        "STACKED_PERIOD_BLOCKS": 0,
    }
    same_page_layout_counts = {
        "LANE_TABLES_PERIOD_COLUMNS": 0,
        "PERIOD_TABLES_LANE_COLUMNS": 0,
    }
    adjacent_page_layout_counts = {
        "LANE_TABLES_PERIOD_COLUMNS": 0,
        "PERIOD_TABLES_LANE_COLUMNS": 0,
    }
    for source in sorted(dispositions_by_source):
        source_dispositions = sorted(
            dispositions_by_source[source],
            key=lambda item: (
                item["selected_page_ordinal"],
                int(item["section_id"][1:]),
                int(item["table_id"][1:]),
            ),
        )
        components = [
            item for item in source_dispositions if item["disposition"] == "ACCEPTED_COMPONENT"
        ]
        complementary_pairs = []
        following_owner_backbinding_pairs = []
        for owner in source_dispositions:
            for continuation in source_dispositions:
                if (
                    continuation["selected_page_ordinal"]
                    != owner["selected_page_ordinal"] + 1
                    or continuation["physical_page"] != owner["physical_page"] + 1
                ):
                    continue
                owner_page = canonical_page_by_version[owner["page_json_version_id"]]
                continuation_page = canonical_page_by_version[
                    continuation["page_json_version_id"]
                ]
                try:
                    owner_section = owner_page["sections"][int(owner["section_id"][1:]) - 1]
                    owner_table = owner_section["tables"][int(owner["table_id"][1:]) - 1]
                    continuation_section = continuation_page["sections"][
                        int(continuation["section_id"][1:]) - 1
                    ]
                    continuation_table = continuation_section["tables"][
                        int(continuation["table_id"][1:]) - 1
                    ]
                except (IndexError, KeyError, TypeError) as exc:
                    raise _error(
                        "selected roll-forward continuation locator is invalid"
                    ) from exc
                logical = build_gemini_json_rollforward_complementary_continuation_v1(
                    owner_locator={
                        field: owner[field]
                        for field in (
                            "document_id",
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "source_logical_name",
                            "source_sha256",
                            "table_id",
                        )
                    },
                    owner_section=owner_section,
                    owner_table=owner_table,
                    continuation_locator={
                        field: continuation[field]
                        for field in (
                            "document_id",
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "source_logical_name",
                            "source_sha256",
                            "table_id",
                        )
                    },
                    continuation_section=continuation_section,
                    continuation_table=continuation_table,
                    compiled_specs=compiled_specs,
                )
                if logical is not None:
                    complementary_pairs.append((owner, continuation, logical))
                backbinding = build_gemini_json_rollforward_following_owner_backbinding_v1(
                    preceding_locator={
                        field: owner[field]
                        for field in (
                            "document_id",
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "source_logical_name",
                            "source_sha256",
                            "table_id",
                        )
                    },
                    preceding_section=owner_section,
                    preceding_table=owner_table,
                    following_locator={
                        field: continuation[field]
                        for field in (
                            "document_id",
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "source_logical_name",
                            "source_sha256",
                            "table_id",
                        )
                    },
                    following_section=continuation_section,
                    following_table=continuation_table,
                    compiled_specs=compiled_specs,
                )
                if backbinding is not None:
                    following_owner_backbinding_pairs.append(
                        (owner, continuation, backbinding)
                    )
        admitted_complementary = None
        if len(complementary_pairs) == 1:
            owner, continuation, logical = complementary_pairs[0]
            continuation_regions = [
                {
                    field: component[field]
                    for field in (
                        "document_id",
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "source_logical_name",
                        "source_sha256",
                        "table_id",
                    )
                }
                for component in (owner, continuation)
            ]
            reset_fence = _bounded_population_reset_fence_v1(
                continuation_regions,
                page_json_by_version=canonical_page_by_version,
                compiled_specs=compiled_specs,
                include_intervening_surfaces=True,
            )
            continuation["continuation_cluster_admission"] = {
                "logical_continuation_receipt": logical["receipt"],
                "owner_candidate_evidence_sha256": owner["candidate_evidence_sha256"],
                "reset_fence_receipt": reset_fence,
                "rule": (
                    "UNIQUE_IMMEDIATELY_ADJACENT_AUTHENTICATED_INCOMING_"
                    "COMPLEMENTARY_ROW_CONTINUATION_RESET_FENCED"
                ),
                "status": (
                    "RESET_FENCE_VETO"
                    if reset_fence["reset_hits"]
                    else "ADMITTED_COMPLEMENTARY_RESET_FENCE_CLEAR"
                ),
            }
            if not reset_fence["reset_hits"]:
                admitted_complementary = (owner, continuation, logical)
                for component in (owner, continuation):
                    if component not in components:
                        components.append(component)
        if len(following_owner_backbinding_pairs) == 1:
            preceding, following, backbinding = following_owner_backbinding_pairs[0]
            backbinding_regions = [
                {
                    field: component[field]
                    for field in (
                        "document_id",
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "source_logical_name",
                        "source_sha256",
                        "table_id",
                    )
                }
                for component in (preceding, following)
            ]
            reset_fence = _bounded_population_reset_fence_v1(
                backbinding_regions,
                page_json_by_version=canonical_page_by_version,
                compiled_specs=compiled_specs,
                include_intervening_surfaces=True,
            )
            preceding["continuation_cluster_admission"] = {
                "following_owner_backbinding_receipt": backbinding,
                "following_owner_candidate_evidence_sha256": following[
                    "candidate_evidence_sha256"
                ],
                "reset_fence_receipt": reset_fence,
                "rule": (
                    "UNIQUE_IMMEDIATELY_FOLLOWING_LOCAL_OWNER_EXPLICIT_INCOMING_"
                    "BACKBINDS_PRECEDING_COMPLETE_SAME_TOPOLOGY_COMPONENT_RESET_"
                    "FENCED"
                ),
                "status": (
                    "RESET_FENCE_VETO"
                    if reset_fence["reset_hits"]
                    else "ADMITTED_FOLLOWING_OWNER_BACKBIND_RESET_FENCE_CLEAR"
                ),
            }
            if not reset_fence["reset_hits"]:
                for component in (preceding, following):
                    if component not in components:
                        components.append(component)
        for ordinal, continuation in enumerate(source_dispositions):
            classification = continuation["classification"]
            if (
                ordinal == 0
                or continuation["disposition"] != "LOCAL_OWNER_NOT_VISIBLE"
                or classification is None
                or not classification["continuation_evidence"]
            ):
                continue
            owner = source_dispositions[ordinal - 1]
            owner_classification = owner["classification"]
            if (
                owner not in components
                or owner_classification is None
                or not owner_classification["local_owner_visible"]
                or owner_classification["orientation"] != classification["orientation"]
                or owner_classification["movement_roles_in_source_order"]
                != classification["movement_roles_in_source_order"]
                or owner_classification["column_lane_roles"] != classification["column_lane_roles"]
                or continuation["physical_page"] - owner["physical_page"] != 1
            ):
                continue
            continuation_regions = [
                {
                    field: component[field]
                    for field in (
                        "document_id",
                        "page_json_version_id",
                        "physical_page",
                        "section_id",
                        "source_logical_name",
                        "source_sha256",
                        "table_id",
                    )
                }
                for component in (owner, continuation)
            ]
            reset_fence = _bounded_population_reset_fence_v1(
                continuation_regions,
                page_json_by_version=canonical_page_by_version,
                compiled_specs=compiled_specs,
                include_intervening_surfaces=True,
            )
            continuation["continuation_cluster_admission"] = {
                "owner_candidate_evidence_sha256": owner["candidate_evidence_sha256"],
                "reset_fence_receipt": reset_fence,
                "rule": (
                    "IMMEDIATELY_PRECEDING_ACCEPTED_LOCAL_OWNER_SAME_EXACT_TOPOLOGY_"
                    "EXPLICIT_INCOMING_CONTINUATION_ONE_PAGE_RESET_FENCED"
                ),
                "status": (
                    "RESET_FENCE_VETO"
                    if reset_fence["reset_hits"]
                    else "ADMITTED_RESET_FENCE_CLEAR"
                ),
            }
            if reset_fence["reset_hits"]:
                continue
            components.append(continuation)
        components.sort(
            key=lambda item: (
                item["selected_page_ordinal"],
                int(item["section_id"][1:]),
                int(item["table_id"][1:]),
            )
        )
        if not components:
            continue
        pages = {item["physical_page"] for item in components}
        if admitted_complementary is not None:
            owner, continuation, logical = admitted_complementary
            logical_classifications = [
                logical["receipt"]["logical_classification"],
                *(
                    item["classification"]
                    for item in components
                    if item is not owner and item is not continuation
                ),
            ]
            logical_component_count = len(components) - 1
        else:
            logical_classifications = [item["classification"] for item in components]
            logical_component_count = len(components)
        layout_kind = classify_gemini_json_rollforward_cluster_layout_v1(
            logical_classifications
        )
        if (
            layout_kind is None
            or max(pages) - min(pages) > layout["max_page_span"]
            or logical_component_count > layout["max_component_tables"]
        ):
            for component in components:
                component["disposition"] = "DOCUMENT_CLUSTER_AMBIGUOUS"
                component["reason_codes"] = [
                    *component["reason_codes"],
                    "ROLLFORWARD_DOCUMENT_CLUSTER_AMBIGUOUS",
                ]
            continue
        layout_counts[layout_kind] += 1
        # Count logical period/lane components, not the physical table halves
        # retained for source replay.  One row-split table is one stacked
        # component even though its provenance spans two physical regions.
        if logical_component_count == 2:
            page_kind_counts = (
                same_page_layout_counts if len(pages) == 1 else adjacent_page_layout_counts
            )
            page_kind_counts[layout_kind] += 1
        for component in components:
            accepted_regions.append(
                {
                    **{
                        field: component[field]
                        for field in (
                            "document_id",
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "source_logical_name",
                            "source_sha256",
                            "table_id",
                        )
                    },
                    "candidate_evidence_sha256": component["candidate_evidence_sha256"],
                    "column_axis_sha256": component["column_axis_sha256"],
                    "context_axis_sha256": component["context_axis_sha256"],
                    "document_ordinal": component["document_ordinal"],
                    "layout_kind": layout_kind,
                    "orientation": (
                        "LANE_COLUMNS"
                        if admitted_complementary is not None
                        and component in admitted_complementary[:2]
                        else component["classification"]["orientation"]
                    ),
                    "row_axis_sha256": component["row_axis_sha256"],
                    "selected_page_ordinal": component["selected_page_ordinal"],
                }
            )

    disposition_counts = {
        kind: sum(item["disposition"] == kind for item in candidate_dispositions)
        for kind in sorted({item["disposition"] for item in candidate_dispositions})
    }
    accepted_regions.sort(
        key=lambda item: (
            item["document_ordinal"],
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
            item["page_json_version_id"],
        )
    )
    unit_binding_by_canonical = {item["canonical_unit"]: item for item in layout["unit_bindings"]}
    unit_evidence_by_document: dict[str, list[dict[str, Any]]] = {
        item["document_id"]: [] for item in selected_document_axis
    }

    def append_unit_evidence(row: Mapping[str, Any], *, source_exact: str) -> None:
        canonical_units = _canonical_money_units_from_surface_v1(
            source_exact,
            compiled_specs=compiled_specs,
            document_consensus_only=True,
        )
        for canonical_unit in sorted(canonical_units):
            binding = unit_binding_by_canonical[canonical_unit]
            record = {
                "canonical_unit": canonical_unit,
                "column_id": row["column_id"],
                "currency": binding["currency"],
                "magnitude_power10": binding["magnitude_power10"],
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
                "section_id": row["section_id"],
                "selected_page_ordinal": row["selection_ordinal"],
                "source_kind": row["source_kind"],
                "table_id": row["table_id"],
                "text_exact": source_exact,
            }
            target = unit_evidence_by_document[row["document_id"]]
            if record not in target:
                target.append(record)

    for raw in document_table_unit_rows:
        append_unit_evidence(dict(raw), source_exact=raw["text_exact"])

    document_unit_context_evidence = []
    for document in selected_document_axis:
        evidence = sorted(
            unit_evidence_by_document[document["document_id"]],
            key=lambda item: (
                item["selected_page_ordinal"],
                int(item["section_id"][1:]),
                int(item["table_id"][1:]),
                item["source_kind"],
                item["column_id"] or "",
                item["text_exact"],
                item["canonical_unit"],
            ),
        )
        canonical_units = sorted({item["canonical_unit"] for item in evidence})
        distinct_page_count = len(
            {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
        )
        status = (
            "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
            if len(canonical_units) == 1 and distinct_page_count >= 2
            else "CONFLICTING_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
            if len(canonical_units) > 1
            else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
        )
        document_unit_context_evidence.append(
            {
                "canonical_unit": canonical_units[0] if status.startswith("UNIQUE_") else None,
                "canonical_units": canonical_units,
                "distinct_page_count": distinct_page_count,
                "document_id": document["document_id"],
                "document_ordinal": document["document_ordinal"],
                "evidence": evidence,
                "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
                "minimum_distinct_page_count": 2,
                "rule": (
                    "SELECTED_PAGE_VERSION_ONLY_EXPLICIT_TABLE_UNIT_MAGNITUDE_AND_"
                    "CURRENCY_TWO_PAGE_UNIQUE_CANONICAL_MONEY_UNIT_CONSENSUS"
                ),
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )

    fiscal_evidence_by_document: dict[str, list[dict[str, Any]]] = {
        item["document_id"]: [] for item in selected_document_axis
    }

    def full_dates(value: Any) -> list[date]:
        folded = _normalized(value)
        if not folded or not (_DATE_DMY.search(folded) or _DATE_WORDS.search(folded)):
            return []
        return sorted({token[0] for token in _date_tokens(value)})

    def annual_reporting_surface(value: Any) -> bool:
        folded = _normalized(value)
        if not folded:
            return False
        annual = bool(
            ("nam tai chinh" in folded and "ket thuc" in folded)
            or re.search(r"\bnam (?:duoc )?ket thuc\b", folded)
            or "financial year ended" in folded
            or "year ended" in folded
        )
        reporting = any(
            marker in folded
            for marker in (
                "bao cao tai chinh",
                "thuyet minh bao cao",
                "financial statement",
            )
        )
        return annual and (reporting or "nam tai chinh" in folded)

    def annual_reporting_dates(value: Any) -> list[date]:
        folded = _normalized(value)
        if not folded or not annual_reporting_surface(value):
            return []
        governed = []
        grammar = re.compile(
            r"(?:nam tai chinh|nam(?: duoc)?|financial year|year)\s+"
            r"(?:duoc\s+)?(?:ket thuc(?:\s+vao)?(?:\s+ngay)?|ended(?:\s+on)?)\s*$"
        )
        for match in sorted(
            [*_DATE_DMY.finditer(folded), *_DATE_WORDS.finditer(folded)],
            key=lambda item: (item.start(), item.end()),
        ):
            if grammar.search(folded[: match.start()]) is None:
                continue
            try:
                parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue
            if parsed not in governed:
                governed.append(parsed)
        return governed

    def append_fiscal_evidence(row: Mapping[str, Any], *, parsed: date) -> None:
        record = {
            "column_id": row.get("column_id"),
            "date": parsed.isoformat(),
            "day": parsed.day,
            "month": parsed.month,
            "page_json_version_id": row["page_json_version_id"],
            "physical_page": row["physical_page"],
            "section_id": row["section_id"],
            "selected_page_ordinal": row["selection_ordinal"],
            "source_kind": row["source_kind"],
            "table_id": row.get("table_id"),
            "text_exact": row["text_exact"],
        }
        target = fiscal_evidence_by_document[row["document_id"]]
        if record not in target:
            target.append(record)

    for raw in document_section_title_rows:
        row = dict(raw)
        for parsed in annual_reporting_dates(row["text_exact"]):
            append_fiscal_evidence(row, parsed=parsed)

    balance_by_table: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for raw in document_balance_column_rows:
        row = dict(raw)
        row["header_path_exact"] = decode_string_axis(
            row.pop("header_path_exact_json"), label="balance-sheet column-header"
        )
        balance_by_table.setdefault(
            (
                row["document_id"],
                row["page_json_version_id"],
                row["section_id"],
                row["table_id"],
            ),
            [],
        ).append(row)
    for rows in balance_by_table.values():
        date_sources = []
        for row in rows:
            for source_exact in row["header_path_exact"]:
                for parsed in full_dates(source_exact):
                    date_sources.append((parsed, row, source_exact))
        distinct_dates = sorted({item[0] for item in date_sources})
        if len(distinct_dates) != 2:
            continue
        previous, current = distinct_dates
        if not (
            previous < current
            and current.year == previous.year + 1
            and (current - previous).days <= 366
        ):
            continue
        for parsed, raw_row, source_exact in date_sources:
            if parsed != previous:
                continue
            append_fiscal_evidence(
                {
                    **raw_row,
                    "source_kind": "BALANCE_SHEET_COMPARATIVE_DATE_COLUMN",
                    "text_exact": source_exact,
                },
                parsed=parsed,
            )

    document_fiscal_close_context_evidence = []
    for document in selected_document_axis:
        all_evidence = fiscal_evidence_by_document[document["document_id"]]
        year_contexts = []
        for evidence_year in sorted(
            {date.fromisoformat(item["date"]).year for item in all_evidence}
        ):
            evidence = sorted(
                (
                    item
                    for item in all_evidence
                    if date.fromisoformat(item["date"]).year == evidence_year
                ),
                key=lambda item: (
                    item["selected_page_ordinal"],
                    int(item["section_id"][1:]),
                    int(item["table_id"][1:]) if item["table_id"] is not None else 0,
                    item["column_id"] or "",
                    item["source_kind"],
                    item["date"],
                    item["text_exact"],
                ),
            )
            month_day_axis = sorted({(item["month"], item["day"]) for item in evidence})
            distinct_page_count = len(
                {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
            )
            status = (
                "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
                if len(month_day_axis) == 1 and distinct_page_count >= 2
                else "CONFLICTING_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_EVIDENCE"
                if len(month_day_axis) > 1
                else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_EVIDENCE"
            )
            year_contexts.append(
                {
                    "day": month_day_axis[0][1] if status.startswith("UNIQUE_") else None,
                    "distinct_page_count": distinct_page_count,
                    "evidence": evidence,
                    "evidence_axis_sha256": canonical_json_sha256_v1(evidence),
                    "minimum_distinct_page_count": 2,
                    "month": month_day_axis[0][0] if status.startswith("UNIQUE_") else None,
                    "month_day_axis": [
                        {"day": day, "month": month} for month, day in month_day_axis
                    ],
                    "status": status,
                    "year": evidence_year,
                }
            )
        document_fiscal_close_context_evidence.append(
            {
                "document_id": document["document_id"],
                "document_ordinal": document["document_ordinal"],
                "rule": (
                    "SELECTED_PAGE_VERSION_ONLY_ANNUAL_REPORTING_TITLE_OR_BALANCE_"
                    "SHEET_COMPARATIVE_DATE_EXACT_YEAR_TWO_PAGE_UNIQUE_FISCAL_"
                    "CLOSE_MONTH_DAY_CONSENSUS"
                ),
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "year_context_axis_sha256": canonical_json_sha256_v1(year_contexts),
                "year_contexts": year_contexts,
            }
        )
    accepted_sources = sorted({item["source_logical_name"] for item in accepted_regions})
    query_receipt = {
        "accepted_layout_counts": layout_counts,
        "accepted_layout_same_page_counts": same_page_layout_counts,
        "accepted_layout_adjacent_page_counts": adjacent_page_layout_counts,
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(candidate_dispositions),
        "candidate_disposition_count": len(candidate_dispositions),
        "candidate_disposition_counts": disposition_counts,
        "candidate_table_count": len(candidate_keys),
        "column_record_count": len(column_rows),
        "context_record_count": len(context_rows),
        "endpoint_prefixes": endpoint_prefixes,
        "endpoint_seed_row_count": len(endpoint_seed_by_identity),
        "exact_region_axis_sha256": canonical_json_sha256_v1(accepted_regions),
        "exact_region_count": len(accepted_regions),
        "document_unit_context_axis_sha256": canonical_json_sha256_v1(
            document_unit_context_evidence
        ),
        "document_unit_context_count": len(document_unit_context_evidence),
        "document_unit_qualifying_evidence_count": sum(
            len(item["evidence"]) for item in document_unit_context_evidence
        ),
        "document_fiscal_close_context_axis_sha256": canonical_json_sha256_v1(
            document_fiscal_close_context_evidence
        ),
        "document_fiscal_close_context_count": len(document_fiscal_close_context_evidence),
        "document_fiscal_close_qualifying_evidence_count": sum(
            len(year_context["evidence"])
            for item in document_fiscal_close_context_evidence
            for year_context in item["year_contexts"]
        ),
        "family_id": compiled_specs["topology"]["family_id"],
        "format_version": "GEMINI_JSON_INDEXED_ROLLFORWARD_QUERY_RECEIPT_V1",
        "query_policy_sha256": query_policy_sha256,
        "row_record_count": len(full_row_rows),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(version_ids),
        "selected_page_json_version_count": len(version_ids),
        "selected_document_axis_sha256": canonical_json_sha256_v1(selected_document_axis),
        "selected_document_count": len(selected_document_axis),
        "selected_source_axis_sha256": canonical_json_sha256_v1(selected_source_axis),
        "target_document_count": len(accepted_sources),
        "target_page_count": len({item["page_json_version_id"] for item in accepted_regions}),
    }
    return {
        "accepted_regions": accepted_regions,
        "candidate_dispositions": candidate_dispositions,
        "document_fiscal_close_context_evidence": (document_fiscal_close_context_evidence),
        "document_unit_context_evidence": document_unit_context_evidence,
        "format_version": ROLLFORWARD_INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "query_receipt": query_receipt,
        "selected_document_axis": selected_document_axis,
    }


def validate_selected_rollforward_family_candidate_replays_v1(
    path: Path,
    *,
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any,
) -> list[dict[str, Any]]:
    """Replay every accepted-source candidate from exact canonical page JSON."""

    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
        validate_gemini_json_rollforward_sweep_query_bindings_v1,
    )
    from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
        build_gemini_json_rollforward_region_query_receipt_v1,
        validate_gemini_json_rollforward_family_candidate_replay_v1,
    )

    try:
        checked_trials = validate_gemini_json_rollforward_sweep_query_bindings_v1(
            trials=trials,
            indexed_query_evidence=indexed_query_evidence,
            compiled_specs=dict(compiled_specs),
        )
    except ValueError as exc:
        raise _error("selected roll-forward sweep bindings do not replay exactly") from exc

    locator_fields = (
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    )
    regions_by_source: dict[str, list[dict[str, Any]]] = {}
    accepted_version_ids: list[str] = []
    seen_version_ids: set[str] = set()
    for accepted in indexed_query_evidence["accepted_regions"]:
        regions_by_source.setdefault(accepted["source_logical_name"], []).append(
            {field: accepted[field] for field in locator_fields}
        )
        version_id = accepted["page_json_version_id"]
        if version_id not in seen_version_ids:
            seen_version_ids.add(version_id)
            accepted_version_ids.append(version_id)
    loaded_pages = (
        load_page_json_versions_v1(path, page_json_version_ids=accepted_version_ids)
        if accepted_version_ids
        else []
    )
    loaded_by_version = {page["page_json_version_id"]: page for page in loaded_pages}
    unit_context_by_source = {
        item["source_logical_name"]: item
        for item in indexed_query_evidence["document_unit_context_evidence"]
    }
    fiscal_context_by_source = {
        item["source_logical_name"]: item
        for item in indexed_query_evidence["document_fiscal_close_context_evidence"]
    }
    if set(loaded_by_version) != set(accepted_version_ids):
        raise _error("selected roll-forward accepted page axis does not load exactly")
    for regions in regions_by_source.values():
        for region in regions:
            page = loaded_by_version.get(region["page_json_version_id"])
            if (
                page is None
                or page["physical_page"] != region["physical_page"]
                or page["source_logical_name"] != region["source_logical_name"]
                or page["source_sha256"] != region["source_sha256"]
            ):
                raise _error("selected roll-forward accepted page provenance drifted")
    try:
        for trial in checked_trials:
            if not trial["candidates"]:
                continue
            regions = regions_by_source[trial["source_logical_name"]]
            validate_gemini_json_rollforward_family_candidate_replay_v1(
                trial["candidates"][0],
                regions=regions,
                page_json_by_version={
                    region["page_json_version_id"]: loaded_by_version[
                        region["page_json_version_id"]
                    ]["page_json"]
                    for region in regions
                },
                compiled_specs=dict(compiled_specs),
                query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(regions),
                document_fiscal_close_context_evidence=fiscal_context_by_source.get(
                    trial["source_logical_name"]
                ),
                document_unit_context_evidence=unit_context_by_source.get(
                    trial["source_logical_name"]
                ),
            )
    except (KeyError, ValueError) as exc:
        raise _error("selected roll-forward candidate does not replay from SQLite") from exc
    return canonical_clone_v1(checked_trials)


def validate_selected_rollforward_family_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
    trials: Any | None = None,
) -> dict[str, Any]:
    """Rederive and exact-compare one public selected-frontier projection."""

    replayed = query_selected_rollforward_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    if type(indexed_query_evidence) is not dict or not same_typed_json_v1(
        indexed_query_evidence, replayed
    ):
        raise _error("selected roll-forward query evidence does not replay exactly")
    if trials is not None:
        validate_selected_rollforward_family_candidate_replays_v1(
            path,
            compiled_specs=compiled_specs,
            indexed_query_evidence=replayed,
            trials=trials,
        )
    return canonical_clone_v1(replayed)


def query_selected_hierarchical_title_axis_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    query_aliases_by_role: Mapping[str, Sequence[str]],
    required_child_roles: Sequence[str],
    minimum_distinct_child_roles: int,
    structural_branch_role: str,
    structural_branch_aliases: Sequence[str],
    structural_surface_kinds: Sequence[str],
    explicit_parent_role: str,
    explicit_parent_aliases: Sequence[str],
    hard_negative_aliases: Sequence[str],
    owner_reset_aliases: Sequence[str],
    adjacent_page_radius: int = 2,
    query_group_receipt: Mapping[str, Any] | None = None,
    structural_branch_fallback_group_aliases: Sequence[str] = (),
    unresolved_near_source_policy: str = "ANY_UNVETOED_STRUCTURAL_AXIS",
) -> dict[str, Any]:
    """Return row-qualified tables under one bounded title/narrative owner axis.

    The indexed row lookup is performed once over the caller's immutable
    selected-version allowlist.  Titles and section narratives can authenticate
    only a table that already has the declared minimum of distinct child roles;
    they are never promoted page-globally.  Parent carry is preceding-only and
    bounded to the current page plus two selected physical pages.
    """

    role_aliases_valid = (
        type(query_aliases_by_role) is dict
        and query_aliases_by_role
        and all(
            type(role) is str
            and role
            and type(aliases) in {list, tuple}
            and aliases
            and all(type(alias) is str and alias.strip() for alias in aliases)
            for role, aliases in query_aliases_by_role.items()
        )
    )
    required = list(required_child_roles) if type(required_child_roles) in {list, tuple} else []
    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
        or not role_aliases_valid
        or not required
        or len(required) != len(set(required))
        or any(role not in query_aliases_by_role for role in required)
        or type(structural_branch_role) is not str
        or not structural_branch_role
        or type(minimum_distinct_child_roles) is not int
        or not 2 <= minimum_distinct_child_roles <= len(required)
        or type(structural_branch_aliases) not in {list, tuple}
        or not structural_branch_aliases
        or type(structural_branch_fallback_group_aliases) not in {list, tuple}
        or any(
            type(alias) is not str or not alias.strip()
            for alias in structural_branch_fallback_group_aliases
        )
        or tuple(structural_surface_kinds)
        not in {
            ("TITLE",),
            ("TITLE", "SECTION_NARRATIVE"),
            ("TITLE", "SECTION_NARRATIVE", "GROUP_ROW"),
        }
        or type(explicit_parent_role) is not str
        or not explicit_parent_role
        or type(explicit_parent_aliases) not in {list, tuple}
        or not explicit_parent_aliases
        or type(hard_negative_aliases) not in {list, tuple}
        or type(owner_reset_aliases) not in {list, tuple}
        or type(adjacent_page_radius) is not int
        or not 0 <= adjacent_page_radius <= 2
        or (query_group_receipt is not None and type(query_group_receipt) is not dict)
        or unresolved_near_source_policy
        not in {
            "ANY_UNVETOED_STRUCTURAL_AXIS",
            "REQUIRE_UNVETOED_BRANCH_OWNER_AND_MINIMUM_CHILD_ROLES",
        }
    ):
        raise _error("selected hierarchical title-axis query is invalid")

    selected_page_extraction_receipts_v1(
        path,
        page_json_version_ids=selected_page_json_version_ids,
    )
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_title_axis_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_title_axis_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        selected_rows = connection.execute(
            """
            SELECT selected.selection_ordinal, selected.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page
            FROM selected_title_axis_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            ORDER BY selected.selection_ordinal
            """
        ).fetchall()
        if len(selected_rows) != len(selected_page_json_version_ids):
            raise _error("selected hierarchical title-axis page is absent")
        locations = [(row["source_logical_name"], row["physical_page"]) for row in selected_rows]
        if len(set(locations)) != len(locations):
            raise _error("selected hierarchical title-axis frontier repeats a page")
        if locations != sorted(locations):
            raise _error("selected hierarchical title-axis frontier is not in corpus order")

        connection.execute(
            "CREATE TEMP TABLE title_axis_role_alias("
            "role TEXT NOT NULL, label_ascii_folded TEXT NOT NULL,"
            "PRIMARY KEY(role,label_ascii_folded))"
        )
        connection.executemany(
            "INSERT INTO title_axis_role_alias VALUES (?,?)",
            (
                (role, alias)
                for role, aliases in sorted(query_aliases_by_role.items())
                for alias in _family_anchor_lookup_forms_v1(aliases)
            ),
        )
        role_hits = connection.execute(
            """
            SELECT selected.selection_ordinal, rn.page_json_version_id,
                   document.document_id, document.source_logical_name,
                   document.source_sha256, page.physical_page,
                   rn.section_id, rn.table_id, rn.row_id, rn.source_order,
                   rn.label_exact, alias.role,
                   sn.source_order AS section_source_order,
                   tn.source_order AS table_source_order
            FROM row_node AS rn INDEXED BY idx_row_label_ascii
            JOIN title_axis_role_alias AS alias
              ON alias.label_ascii_folded=rn.label_ascii_folded
            JOIN selected_title_axis_page AS selected USING(page_json_version_id)
            JOIN page_json_version AS version USING(page_json_version_id)
            JOIN page USING(page_id)
            JOIN document USING(document_id)
            JOIN section_node AS sn
              ON sn.page_json_version_id=rn.page_json_version_id
             AND sn.section_id=rn.section_id
            JOIN table_node AS tn
              ON tn.page_json_version_id=rn.page_json_version_id
             AND tn.section_id=rn.section_id AND tn.table_id=rn.table_id
            ORDER BY selected.selection_ordinal, sn.source_order,
                     tn.source_order, rn.source_order, rn.row_id, alias.role
            """
        ).fetchall()

        hits_by_table: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        for hit in role_hits:
            hits_by_table.setdefault(
                (hit["page_json_version_id"], hit["section_id"], hit["table_id"]), []
            ).append(hit)

        def distinct_child_assignment(hits: list[sqlite3.Row]) -> dict[str, str]:
            """Return one deterministic maximum role-to-distinct-row matching."""

            rows_by_role = {
                role: sorted({hit["row_id"] for hit in hits if hit["role"] == role})
                for role in required
                if any(hit["role"] == role for hit in hits)
            }
            ordered_roles = sorted(rows_by_role, key=lambda role: (len(rows_by_role[role]), role))
            role_by_row: dict[str, str] = {}

            def augment(role: str, visited_rows: set[str]) -> bool:
                for row_id in rows_by_role[role]:
                    if row_id in visited_rows:
                        continue
                    visited_rows.add(row_id)
                    prior_role = role_by_row.get(row_id)
                    if prior_role is None or augment(prior_role, visited_rows):
                        role_by_row[row_id] = role
                        return True
                return False

            for role in ordered_roles:
                augment(role, set())
            return {role: row_id for row_id, role in sorted(role_by_row.items())}

        candidate_keys = []
        child_assignment_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
        for key, hits in hits_by_table.items():
            assignment = distinct_child_assignment(hits)
            candidate_keys.append(key)
            child_assignment_by_key[key] = assignment

        candidate_document_pages = {
            (hits_by_table[key][0]["document_id"], hits_by_table[key][0]["physical_page"])
            for key in candidate_keys
        }
        context_version_ids = {
            row["page_json_version_id"]
            for row in selected_rows
            if any(
                row["document_id"] == document_id
                and 0 <= candidate_page - row["physical_page"] <= adjacent_page_radius
                for document_id, candidate_page in candidate_document_pages
            )
        }

    selected_by_version = {row["page_json_version_id"]: dict(row) for row in selected_rows}
    ordered_context_version_ids = [
        version_id
        for version_id in selected_page_json_version_ids
        if version_id in context_version_ids
    ]
    loaded_context_pages = (
        load_page_json_versions_v1(path, page_json_version_ids=ordered_context_version_ids)
        if ordered_context_version_ids
        else []
    )
    context_by_document: dict[str, list[dict[str, Any]]] = {}
    for loaded_page in loaded_context_pages:
        selected = selected_by_version[loaded_page["page_json_version_id"]]
        context_by_document.setdefault(selected["document_id"], []).append(
            {**loaded_page, "document_id": selected["document_id"]}
        )

    regions = []
    candidate_dispositions = []
    near_parent_sources: set[str] = set()
    unresolved_near_parent_sources: set[str] = set()
    for key in sorted(
        candidate_keys,
        key=lambda item: (
            hits_by_table[item][0]["selection_ordinal"],
            hits_by_table[item][0]["section_source_order"],
            hits_by_table[item][0]["table_source_order"],
            item,
        ),
    ):
        representative = hits_by_table[key][0]
        context_records = [
            record
            for record in context_by_document[representative["document_id"]]
            if 0
            <= representative["physical_page"] - record["physical_page"]
            <= adjacent_page_radius
        ]
        resolution = resolve_candidate_structural_context_v1(
            candidate_document_id=representative["document_id"],
            candidate_source_logical_name=representative["source_logical_name"],
            candidate_source_sha256=representative["source_sha256"],
            candidate_page_json_version_id=representative["page_json_version_id"],
            candidate_page_json=next(
                record["page_json"]
                for record in context_records
                if record["page_json_version_id"] == representative["page_json_version_id"]
            ),
            candidate_physical_page=representative["physical_page"],
            candidate_section_id=representative["section_id"],
            candidate_table_id=representative["table_id"],
            context_page_records=context_records,
            structural_branch_role=structural_branch_role,
            structural_branch_aliases=structural_branch_aliases,
            structural_branch_fallback_group_aliases=(
                structural_branch_fallback_group_aliases
            ),
            structural_surface_kinds=structural_surface_kinds,
            explicit_parent_role=explicit_parent_role,
            explicit_parent_aliases=explicit_parent_aliases,
            hard_negative_aliases=hard_negative_aliases,
            owner_reset_aliases=owner_reset_aliases,
            adjacent_page_radius=adjacent_page_radius,
        )
        child_assignment = child_assignment_by_key[key]
        disposition_kind = resolution["disposition"]
        if disposition_kind == "ACCEPTED" and len(child_assignment) < minimum_distinct_child_roles:
            disposition_kind = "INSUFFICIENT_DISTINCT_CHILD_ROLES"
        disposition = {
            "branch_evidence": resolution["branch_evidence"],
            "child_role_row_assignment": [
                {"role": role, "row_id": child_assignment[role]}
                for role in sorted(child_assignment)
            ],
            "context_pages": [
                {
                    "page_json_version_id": record["page_json_version_id"],
                    "physical_page": record["physical_page"],
                }
                for record in context_records
            ],
            "disposition": disposition_kind,
            "hard_negative_evidence": resolution["hard_negative_evidence"],
            "owner_evidence": resolution["owner_evidence"],
            "owner_failure_reason": resolution["owner_failure_reason"],
            "owner_mode": resolution["owner_mode"],
            "page_json_version_id": representative["page_json_version_id"],
            "physical_page": representative["physical_page"],
            "reset_evidence": resolution["reset_evidence"],
            "selected_page_ordinal": representative["selection_ordinal"],
            "section_id": representative["section_id"],
            "source_logical_name": representative["source_logical_name"],
            "source_sha256": representative["source_sha256"],
            "table_id": representative["table_id"],
        }
        candidate_dispositions.append(disposition)
        if resolution["hard_negative_evidence"] is None and (
            resolution["branch_evidence"] is not None or resolution["owner_evidence"] is not None
        ):
            near_parent_sources.add(representative["source_logical_name"])
            if (
                unresolved_near_source_policy == "ANY_UNVETOED_STRUCTURAL_AXIS"
                or (
                    resolution["branch_evidence"] is not None
                    and resolution["owner_evidence"] is not None
                    and len(child_assignment) >= minimum_distinct_child_roles
                )
            ):
                unresolved_near_parent_sources.add(representative["source_logical_name"])
        if disposition_kind != "ACCEPTED":
            continue
        context_pages = [
            {
                "physical_page": record["physical_page"],
                "page_json_version_id": record["page_json_version_id"],
            }
            for record in context_records
        ]
        regions.append(
            {
                "context_pages": context_pages,
                "document_id": representative["document_id"],
                "matched_child_roles": sorted(child_assignment),
                "page_json_version_id": representative["page_json_version_id"],
                "physical_page": representative["physical_page"],
                "section_id": representative["section_id"],
                "source_logical_name": representative["source_logical_name"],
                "source_sha256": representative["source_sha256"],
                "structural_context_receipt": resolution["structural_context_receipt"],
                "table_id": representative["table_id"],
            }
        )

    ordered_path_axis = [
        {
            key: region[key]
            for key in (
                "source_logical_name",
                "physical_page",
                "page_json_version_id",
                "section_id",
                "table_id",
            )
        }
        for region in regions
    ]
    unique_indexed_hits = {
        (hit["page_json_version_id"], hit["section_id"], hit["table_id"], hit["row_id"])
        for hit in role_hits
    }
    query_receipt_value = canonical_clone_v1(query_group_receipt or {})
    owner_mode_counts: dict[str, int] = {}
    for region in regions:
        mode = region["structural_context_receipt"]["owner_mode"]
        owner_mode_counts[mode] = owner_mode_counts.get(mode, 0) + 1
    disposition_counts: dict[str, int] = {}
    for disposition in candidate_dispositions:
        value = disposition["disposition"]
        disposition_counts[value] = disposition_counts.get(value, 0) + 1
    query_receipt_value.update(
        {
            "candidate_disposition_axis_sha256": canonical_json_sha256_v1(candidate_dispositions),
            "candidate_disposition_count": len(candidate_dispositions),
            "candidate_disposition_counts": [
                {"count": disposition_counts[value], "disposition": value}
                for value in sorted(disposition_counts)
            ],
            "candidate_surface_decode_count": len(candidate_keys),
            "candidate_table_count_before_structural_axis": len(candidate_keys),
            "context_page_json_decode_count": len(loaded_context_pages),
            "context_page_title_scan_count": len(context_version_ids),
            "exact_region_path_axis_sha256": canonical_json_sha256_v1(ordered_path_axis),
            "exact_region_count": len(regions),
            "indexed_row_hit_count": len(unique_indexed_hits),
            "indexed_row_hit_table_count": len(hits_by_table),
            "minimum_distinct_child_roles": minimum_distinct_child_roles,
            "near_structural_evidence_document_count": len(near_parent_sources),
            "owner_mode_counts": [
                {"count": owner_mode_counts[mode], "mode": mode}
                for mode in sorted(owner_mode_counts)
            ],
            "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
                list(selected_page_json_version_ids)
            ),
            "selected_page_json_version_count": len(selected_page_json_version_ids),
            "structural_surface_kinds": list(structural_surface_kinds),
            "target_document_count": len({region["source_logical_name"] for region in regions}),
        }
    )
    return {
        "candidate_dispositions": candidate_dispositions,
        "near_parent_sources": sorted(near_parent_sources),
        "unresolved_near_parent_sources": sorted(unresolved_near_parent_sources),
        "query_receipt": query_receipt_value,
        "regions": regions,
    }


def validate_selected_hierarchical_title_axis_query_evidence_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    source_ordinal_and_sha256_by_logical_name: Mapping[str, tuple[int, str]],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    """Replay one persisted V8 title-axis query against the selected SQLite frontier."""

    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
        INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        _validate_indexed_query_evidence_v1,
    )

    if (
        type(compiled_specs) is not dict
        or type(source_ordinal_and_sha256_by_logical_name) is not dict
        or not source_ordinal_and_sha256_by_logical_name
        or any(
            type(source) is not str
            or not source
            or type(identity) is not tuple
            or len(identity) != 2
            or type(identity[0]) is not int
            or identity[0] <= 0
            or type(identity[1]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", identity[1]) is None
            for source, identity in source_ordinal_and_sha256_by_logical_name.items()
        )
    ):
        raise _error("selected title-axis evidence replay identity is invalid")
    policy = compiled_specs.get("title_axis_projection_policy")
    topology = compiled_specs.get("topology")
    if type(policy) is not dict or type(topology) is not dict:
        raise _error("selected title-axis evidence replay specs are invalid")
    branch_role = policy["structural_branch_role"]
    replayed = query_selected_hierarchical_title_axis_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        query_aliases_by_role={
            role: compiled_specs["query_presence_aliases_by_role"][role]
            for role in policy["required_child_roles"]
        },
        required_child_roles=policy["required_child_roles"],
        minimum_distinct_child_roles=policy["minimum_distinct_child_roles"],
        structural_branch_role=branch_role,
        structural_branch_aliases=compiled_specs["query_presence_aliases_by_role"][branch_role],
        structural_branch_fallback_group_aliases=[
            alias
            for role in policy.get("structural_branch_fallback_group_roles", [])
            for alias in compiled_specs["query_presence_aliases_by_role"][role]
        ],
        unresolved_near_source_policy=policy.get(
            "unresolved_near_source_policy", "ANY_UNVETOED_STRUCTURAL_AXIS"
        ),
        structural_surface_kinds=policy["structural_surface_kinds"],
        explicit_parent_role=topology["parent"]["role"],
        explicit_parent_aliases=compiled_specs["query_parent_aliases"],
        hard_negative_aliases=topology["hard_negative_aliases"],
        owner_reset_aliases=policy["owner_reset_aliases"],
        adjacent_page_radius=policy["owner_page_radius"],
        query_group_receipt=compiled_specs["query_group_compilation_receipt"],
    )
    ordinal_axis = []
    for region in replayed["regions"]:
        identity = source_ordinal_and_sha256_by_logical_name.get(region["source_logical_name"])
        if identity is None or identity[1] != region["source_sha256"]:
            raise _error("selected title-axis evidence source identity drifted")
        ordinal_axis.append(
            {
                "document_ordinal": identity[0],
                "source_sha256": identity[1],
                **{
                    key: region[key]
                    for key in (
                        "physical_page",
                        "page_json_version_id",
                        "section_id",
                        "table_id",
                    )
                },
            }
        )
    ordinal_axis.sort(
        key=lambda item: (
            item["document_ordinal"],
            item["physical_page"],
            item["section_id"],
            item["table_id"],
            item["page_json_version_id"],
        )
    )
    replayed["query_receipt"]["exact_region_ordinal_source_axis_sha256"] = canonical_json_sha256_v1(
        ordinal_axis
    )
    receipt_sha256 = canonical_json_sha256_v1(replayed["query_receipt"])
    expected = {
        "accepted_regions": [
            {
                **canonical_clone_v1(region),
                "document_ordinal": source_ordinal_and_sha256_by_logical_name[
                    region["source_logical_name"]
                ][0],
                "structural_context_receipt": {
                    **canonical_clone_v1(region["structural_context_receipt"]),
                    "title_axis_query_receipt_sha256": receipt_sha256,
                },
            }
            for region in replayed["regions"]
        ],
        "candidate_dispositions": canonical_clone_v1(replayed["candidate_dispositions"]),
        "format_version": INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "query_receipt": canonical_clone_v1(replayed["query_receipt"]),
    }
    checked = _validate_indexed_query_evidence_v1(
        indexed_query_evidence,
        compiled_specs=dict(compiled_specs),
    )
    if checked != expected:
        raise _error("selected title-axis indexed query evidence drifted from SQLite")
    return canonical_clone_v1(checked)


def query_selected_family_anchor_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    anchor_aliases: Sequence[Sequence[str]],
    title_anchor_aliases: Sequence[str] = (),
    adjacent_page_radius: int = 1,
) -> list[dict[str, Any]]:
    """Shortlist local tables only within one manifest-selected page frontier.

    The selected version IDs must be supplied in corpus source/page order.  A
    temporary table makes that frontier authoritative for the query and keeps
    historical retry versions out of family matching.
    """

    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
        or any(
            type(version_id) is not str
            or not version_id.startswith("gfpstorev1:json:")
            or len(version_id) != len("gfpstorev1:json:") + 64
            or any(
                character not in "0123456789abcdef"
                for character in version_id.removeprefix("gfpstorev1:json:")
            )
            for version_id in selected_page_json_version_ids
        )
    ):
        raise _error("selected family query page JSON frontier is invalid")
    if (
        len(anchor_aliases) not in {2, 3}
        or any(not aliases for aliases in anchor_aliases)
        or type(adjacent_page_radius) is not int
        or not 0 <= adjacent_page_radius <= 2
        or type(title_anchor_aliases) not in {list, tuple}
    ):
        raise _error("selected family query anchors or page radius are invalid")
    folded_sets = [_family_anchor_lookup_forms_v1(aliases) for aliases in anchor_aliases]
    folded_title_aliases = set(_family_anchor_lookup_forms_v1(title_anchor_aliases))
    direct_folded_title_aliases = {
        normalize_search_text_v1(alias)["text_ascii_folded"]
        for alias in title_anchor_aliases
        if type(alias) is str and alias
    }
    narrative_anchor_aliases = sorted(
        {
            (anchor_ordinal, folded)
            for anchor_ordinal, aliases in enumerate(anchor_aliases, start=1)
            for alias in aliases
            if type(alias) is str
            and (folded := normalize_search_text_v1(alias)["text_ascii_folded"])
            in direct_folded_title_aliases
        }
    )
    if any(not aliases or any(not alias for alias in aliases) for aliases in folded_sets):
        raise _error("selected family query normalized anchor set is empty")

    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_page_version("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_page_version VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        selected_rows = connection.execute(
            """
            SELECT s.selection_ordinal, s.page_json_version_id,
                   d.document_id, d.source_logical_name, p.physical_page
            FROM selected_page_version AS s
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            ORDER BY s.selection_ordinal
            """
        ).fetchall()
        if len(selected_rows) != len(selected_page_json_version_ids):
            raise _error("selected family query page JSON version is absent")
        locations = [(row["source_logical_name"], row["physical_page"]) for row in selected_rows]
        if len(set(locations)) != len(locations):
            raise _error("selected family query frontier repeats one physical page")
        if locations != sorted(locations):
            raise _error("selected family query frontier is not in corpus source/page order")
        connection.execute(
            "CREATE TEMP TABLE anchor_alias("
            "anchor_ordinal INTEGER NOT NULL, label_ascii_folded TEXT NOT NULL, "
            "PRIMARY KEY(anchor_ordinal,label_ascii_folded))"
        )
        connection.executemany(
            "INSERT INTO anchor_alias VALUES (?,?)",
            (
                (anchor_ordinal, alias)
                for anchor_ordinal, aliases in enumerate(folded_sets, start=1)
                for alias in aliases
            ),
        )
        connection.execute(
            "CREATE TEMP TABLE title_anchor_alias("
            "anchor_ordinal INTEGER NOT NULL, label_ascii_folded TEXT NOT NULL, "
            "PRIMARY KEY(anchor_ordinal,label_ascii_folded))"
        )
        connection.executemany(
            "INSERT INTO title_anchor_alias VALUES (?,?)",
            (
                (anchor_ordinal, alias)
                for anchor_ordinal, aliases in enumerate(folded_sets, start=1)
                for alias in aliases
                if alias in folded_title_aliases
            ),
        )
        connection.execute(
            "CREATE TEMP TABLE narrative_anchor_alias("
            "anchor_ordinal INTEGER NOT NULL, label_ascii_folded TEXT NOT NULL, "
            "PRIMARY KEY(anchor_ordinal,label_ascii_folded))"
        )
        connection.executemany(
            "INSERT INTO narrative_anchor_alias VALUES (?,?)",
            narrative_anchor_aliases,
        )
        connection.create_function(
            "normalize_family_narrative_v1",
            1,
            lambda value: (
                normalize_search_text_v1(value)["text_ascii_folded"]
                if type(value) is str
                else ""
            ),
            deterministic=True,
        )
        candidates = connection.execute(
            """
            WITH anchor_hit AS (
              SELECT r.page_json_version_id, r.section_id, r.table_id,
                     a.anchor_ordinal, r.row_id, r.source_order
              FROM row_node AS r
              JOIN selected_page_version AS s USING(page_json_version_id)
              JOIN anchor_alias AS a ON a.label_ascii_folded=r.label_ascii_folded
              UNION ALL
              SELECT t.page_json_version_id, t.section_id, t.table_id,
                     a.anchor_ordinal,
                     '__TITLE_ANCHOR__:' || a.anchor_ordinal,
                     0
              FROM table_node AS t
              JOIN selected_page_version AS s USING(page_json_version_id)
              JOIN section_node AS sn
                ON sn.page_json_version_id=t.page_json_version_id
               AND sn.section_id=t.section_id
              JOIN title_anchor_alias AS a
                ON instr(COALESCE(sn.title_ascii_folded,''),a.label_ascii_folded)>0
                OR instr(COALESCE(t.title_ascii_folded,''),a.label_ascii_folded)>0
              UNION ALL
              SELECT t.page_json_version_id, t.section_id, t.table_id,
                     a.anchor_ordinal,
                     '__SECTION_NARRATIVE_ANCHOR__:' || a.anchor_ordinal,
                     0
              FROM table_node AS t
              JOIN selected_page_version AS s USING(page_json_version_id)
              JOIN section_node AS sn
                ON sn.page_json_version_id=t.page_json_version_id
               AND sn.section_id=t.section_id
              JOIN json_each(sn.narratives_json) AS narrative
              JOIN narrative_anchor_alias AS a
                ON instr(
                     normalize_family_narrative_v1(narrative.value),
                     a.label_ascii_folded
                   )>0
            )
            SELECT h.page_json_version_id, h.section_id, h.table_id,
                   s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, sn.source_order AS section_source_order,
                   t.source_order AS table_source_order
            FROM anchor_hit AS h
            JOIN selected_page_version AS s USING(page_json_version_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN section_node AS sn
              ON sn.page_json_version_id=h.page_json_version_id
             AND sn.section_id=h.section_id
            JOIN table_node AS t
              ON t.page_json_version_id=h.page_json_version_id
             AND t.section_id=h.section_id AND t.table_id=h.table_id
            GROUP BY h.page_json_version_id, h.section_id, h.table_id,
                     s.selection_ordinal, d.document_id, d.source_logical_name,
                     p.physical_page, sn.source_order, t.source_order
            HAVING COUNT(DISTINCT h.anchor_ordinal)=?
            ORDER BY s.selection_ordinal, sn.source_order, t.source_order,
                     h.section_id, h.table_id
            """,
            (len(folded_sets),),
        ).fetchall()
        matched_rows = connection.execute(
            """
            SELECT * FROM (
              SELECT r.page_json_version_id, r.section_id, r.table_id,
                     a.anchor_ordinal, r.row_id, r.source_order,
                     s.selection_ordinal
              FROM row_node AS r
              JOIN selected_page_version AS s USING(page_json_version_id)
              JOIN anchor_alias AS a ON a.label_ascii_folded=r.label_ascii_folded
              UNION ALL
              SELECT t.page_json_version_id, t.section_id, t.table_id,
                     a.anchor_ordinal,
                     '__TITLE_ANCHOR__:' || a.anchor_ordinal,
                     0, s.selection_ordinal
              FROM table_node AS t
              JOIN selected_page_version AS s USING(page_json_version_id)
              JOIN section_node AS sn
                ON sn.page_json_version_id=t.page_json_version_id
               AND sn.section_id=t.section_id
              JOIN title_anchor_alias AS a
                ON instr(COALESCE(sn.title_ascii_folded,''),a.label_ascii_folded)>0
                OR instr(COALESCE(t.title_ascii_folded,''),a.label_ascii_folded)>0
              UNION ALL
              SELECT t.page_json_version_id, t.section_id, t.table_id,
                     a.anchor_ordinal,
                     '__SECTION_NARRATIVE_ANCHOR__:' || a.anchor_ordinal,
                     0, s.selection_ordinal
              FROM table_node AS t
              JOIN selected_page_version AS s USING(page_json_version_id)
              JOIN section_node AS sn
                ON sn.page_json_version_id=t.page_json_version_id
               AND sn.section_id=t.section_id
              JOIN json_each(sn.narratives_json) AS narrative
              JOIN narrative_anchor_alias AS a
                ON instr(
                     normalize_family_narrative_v1(narrative.value),
                     a.label_ascii_folded
                   )>0
            )
            ORDER BY selection_ordinal, section_id, table_id,
                     anchor_ordinal, source_order, row_id
            """
        ).fetchall()
        hits_by_region_and_anchor: dict[tuple[str, str, str, int], list[str]] = {}
        for row in matched_rows:
            key = (
                row["page_json_version_id"],
                row["section_id"],
                row["table_id"],
                row["anchor_ordinal"],
            )
            hits = hits_by_region_and_anchor.setdefault(key, [])
            if row["row_id"] not in hits:
                hits.append(row["row_id"])
        selected_pages_by_document: dict[str, list[dict[str, Any]]] = {}
        for row in selected_rows:
            selected_pages_by_document.setdefault(row["document_id"], []).append(
                {
                    "physical_page": row["physical_page"],
                    "page_json_version_id": row["page_json_version_id"],
                }
            )
        result: list[dict[str, Any]] = []
        for candidate in candidates:
            hit_groups = [
                hits_by_region_and_anchor.get(
                    (
                        candidate["page_json_version_id"],
                        candidate["section_id"],
                        candidate["table_id"],
                        anchor_ordinal,
                    ),
                    [],
                )
                for anchor_ordinal in range(1, len(folded_sets) + 1)
            ]
            if not _distinct_anchor_assignment_exists_v1(hit_groups):
                continue
            context_pages = [
                page
                for page in selected_pages_by_document[candidate["document_id"]]
                if max(1, candidate["physical_page"] - adjacent_page_radius)
                <= page["physical_page"]
                <= candidate["physical_page"] + adjacent_page_radius
            ]
            result.append(
                {
                    "anchor_row_ids": hit_groups,
                    "context_pages": context_pages,
                    "document_id": candidate["document_id"],
                    "page_json_version_id": candidate["page_json_version_id"],
                    "physical_page": candidate["physical_page"],
                    "section_id": candidate["section_id"],
                    "source_logical_name": candidate["source_logical_name"],
                    "table_id": candidate["table_id"],
                }
            )
    return result


_DUAL_AXIS_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def _dual_axis_folded_label_v1(value: Any) -> str:
    if type(value) is not str:
        return ""
    # Some otherwise faithful Gemini pages retain the JSON escape spelling in
    # a header cell (for example ``"Cho vay\\nkhách hàng"``).  A literal
    # escaped line/tab separator carries no accounting semantics, exactly like
    # the decoded whitespace spelling on neighbouring pages.
    value = re.sub(r"\\[nrt]+", " ", value)
    folded = normalize_search_text_v1(value)["text_ascii_folded"]
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", folded).split())


def _dual_axis_header_leaf_v1(
    value: Any, *, declared_unit_suffixes: set[str]
) -> tuple[str, list[str]]:
    """Return an exact accounting-axis leaf after removing only a money unit."""

    if type(value) not in {str, bytes}:
        return "", []
    try:
        path = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return "", []
    if type(path) is not list or any(item is not None and type(item) is not str for item in path):
        return "", []
    exact_path = [item for item in path if type(item) is str and item]
    for exact in reversed(exact_path):
        folded = _dual_axis_folded_label_v1(exact)
        for suffix in sorted(declared_unit_suffixes, key=lambda item: (-len(item), item)):
            if folded == suffix:
                folded = ""
                break
            if folded.endswith(" " + suffix):
                folded = folded[: -(len(suffix) + 1)].strip()
                break
        if folded:
            return folded, exact_path
    return "", exact_path


def query_selected_dual_axis_family_regions_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    metric_aliases: Sequence[str],
    role_aliases: Mapping[str, Sequence[str]],
    unit_aliases: Sequence[str],
    external_population_control: Mapping[str, Any] | None = None,
    adjacent_page_radius: int = 1,
) -> dict[str, Any]:
    """Query exact row/column-transposed accounting regions and bounded context.

    An indexed row hit narrows every lookup before column headers are decoded.
    A region is returned only when one orientation contains the two declared
    role anchors and one exact opposite-axis metric qualifier.  Row-oriented
    roles may occur twice only when they form two exact shared hierarchy-path
    groups with distinct local dates.  Header matching removes only a trailing
    money unit; it never uses a substring, bank, file, page number, note number,
    OCR geometry, or broad-population narrowing.
    """

    if (
        type(selected_page_json_version_ids) not in {list, tuple}
        or not selected_page_json_version_ids
        or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
        or any(
            type(version_id) is not str
            or not version_id.startswith("gfpstorev1:json:")
            or len(version_id) != len("gfpstorev1:json:") + 64
            or any(
                character not in "0123456789abcdef"
                for character in version_id.removeprefix("gfpstorev1:json:")
            )
            for version_id in selected_page_json_version_ids
        )
        or type(metric_aliases) not in {list, tuple}
        or not metric_aliases
        or not isinstance(role_aliases, Mapping)
        or len(role_aliases) != 2
        or any(type(role) is not str or not role for role in role_aliases)
        or any(
            type(aliases) not in {list, tuple} or not aliases for aliases in role_aliases.values()
        )
        or type(unit_aliases) not in {list, tuple}
        or not unit_aliases
        or external_population_control is not None
        and not isinstance(external_population_control, Mapping)
        or type(adjacent_page_radius) is not int
        or not 0 <= adjacent_page_radius <= 2
    ):
        raise _error("selected dual-axis family query is invalid")

    def folded_aliases(values: Sequence[str]) -> list[str]:
        folded = [_dual_axis_folded_label_v1(value) for value in values]
        if any(not value for value in folded) or len(folded) != len(set(folded)):
            raise _error("selected dual-axis family aliases are invalid or ambiguous")
        return folded

    folded_metrics = set(folded_aliases(metric_aliases))
    folded_roles = {role: set(folded_aliases(aliases)) for role, aliases in role_aliases.items()}
    folded_units = set(folded_aliases(unit_aliases))
    external_control_policy = (
        None
        if external_population_control is None
        else canonical_clone_v1(external_population_control)
    )
    if external_control_policy is not None:
        expected_control_fields = {
            "candidate_context",
            "control_report_norm_id",
            "control_source",
            "controlled_metric_aliases",
            "format_version",
            "match_rule",
            "query_gate_metric_aliases",
            "unit_decimal_magnitude_by_alias",
        }
        if (
            set(external_control_policy) != expected_control_fields
            or external_control_policy.get("format_version")
            != "GEMINI_JSON_DUAL_AXIS_EXTERNAL_POPULATION_CONTROL_V1"
            or external_control_policy.get("match_rule")
            != "EXACT_PERIOD_UNIT_MAGNITUDE_AND_INTEGER_EQUALITY"
            or type(external_control_policy.get("control_report_norm_id")) is not int
            or external_control_policy["control_report_norm_id"] <= 0
            or type(external_control_policy.get("control_source")) is not dict
            or type(external_control_policy.get("candidate_context")) is not dict
            or type(external_control_policy.get("controlled_metric_aliases")) is not list
            or type(external_control_policy.get("query_gate_metric_aliases")) is not list
            or not set(external_control_policy["query_gate_metric_aliases"])
            <= set(external_control_policy["controlled_metric_aliases"])
            <= folded_metrics
            or type(external_control_policy.get("unit_decimal_magnitude_by_alias"))
            is not dict
            or set(external_control_policy["unit_decimal_magnitude_by_alias"])
            != folded_units
        ):
            raise _error("selected dual-axis external population control is invalid")
    control_source_policy = (
        None if external_control_policy is None else external_control_policy["control_source"]
    )
    candidate_context_policy = (
        None
        if external_control_policy is None
        else external_control_policy["candidate_context"]
    )

    from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
        _header_dates,
        _money,
    )

    def decoded_row_hit(raw: Mapping[str, Any]) -> dict[str, Any]:
        record = dict(raw)
        try:
            path = json.loads(record.pop("hierarchy_path_exact_json"))
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("selected dual-axis row hierarchy path is invalid") from exc
        if type(path) is not list or any(
            value is not None and type(value) is not str for value in path
        ):
            raise _error("selected dual-axis row hierarchy path is invalid")
        record["hierarchy_path_exact"] = path
        return record

    def stacked_period_role_groups(
        row_roles: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> list[dict[str, Any]] | None:
        if not all(len(matches) == 2 for matches in row_roles.values()):
            return None
        grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
        for role, matches in row_roles.items():
            for hit in matches:
                path = canonical_clone_v1(hit["hierarchy_path_exact"])
                label = hit["label_exact"]
                if path and (
                    path[-1] is None
                    or (
                        type(label) is str
                        and _dual_axis_folded_label_v1(path[-1])
                        == _dual_axis_folded_label_v1(label)
                    )
                ):
                    path.pop()
                if not path:
                    return None
                key = tuple(path)
                group = grouped.setdefault(key, {"hierarchy_path_exact": path, "roles": {}})
                if role in group["roles"]:
                    return None
                group["roles"][role] = {
                    field: hit[field] for field in ("label_exact", "row_id", "source_order")
                }
        if len(grouped) != 2 or any(
            set(group["roles"]) != set(folded_roles) for group in grouped.values()
        ):
            return None
        result = []
        for group in grouped.values():
            dates = {
                parsed
                for surface in group["hierarchy_path_exact"]
                if type(surface) is str
                for parsed in _header_dates(surface)
            }
            if len(dates) != 1:
                return None
            result.append({**group, "period_end": next(iter(dates)).isoformat()})
        if len({group["period_end"] for group in result}) != 2:
            return None
        return sorted(
            result,
            key=lambda group: min(hit["source_order"] for hit in group["roles"].values()),
        )

    selected_page_json_provenance_receipts_v1(
        path,
        page_json_version_ids=selected_page_json_version_ids,
    )
    with _connect(path, readonly=True) as connection:
        connection.execute(
            "CREATE TEMP TABLE selected_dual_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_dual_page VALUES (?,?)",
            enumerate(selected_page_json_version_ids, start=1),
        )
        selected_pages = connection.execute(
            """
            SELECT s.selection_ordinal, s.page_json_version_id,
                   d.document_id, d.source_logical_name, p.physical_page
            FROM selected_dual_page AS s
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            ORDER BY s.selection_ordinal
            """
        ).fetchall()
        if len(selected_pages) != len(selected_page_json_version_ids):
            raise _error("selected dual-axis page JSON version is absent")
        locations = [(row["source_logical_name"], row["physical_page"]) for row in selected_pages]
        if len(locations) != len(set(locations)):
            raise _error("selected dual-axis frontier repeats one physical page")
        if locations != sorted(locations):
            raise _error("selected dual-axis frontier is not in corpus source/page order")

        connection.execute(
            "CREATE TEMP TABLE dual_row_alias("
            "axis_kind TEXT NOT NULL, role TEXT NOT NULL, label_ascii_folded TEXT NOT NULL, "
            "PRIMARY KEY(axis_kind,role,label_ascii_folded))"
        )
        connection.executemany(
            "INSERT INTO dual_row_alias VALUES (?,?,?)",
            [
                *(("METRIC", "METRIC", alias) for alias in sorted(folded_metrics)),
                *(
                    ("ROLE", role, alias)
                    for role, aliases in folded_roles.items()
                    for alias in sorted(aliases)
                ),
            ],
        )
        row_hits = [
            decoded_row_hit(row)
            for row in connection.execute(
                """
            SELECT r.page_json_version_id, r.section_id, r.table_id,
                   r.row_id, r.source_order, r.label_exact,
                   r.hierarchy_path_exact_json,
                   a.axis_kind, a.role
            FROM row_node AS r
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN dual_row_alias AS a USING(label_ascii_folded)
            ORDER BY s.selection_ordinal, r.section_id, r.table_id,
                     r.source_order, r.row_id, a.axis_kind, a.role
            """
            ).fetchall()
        ]
        # Frozen row indexes retain punctuation in ``label_ascii_folded`` while
        # the accounting alias compiler deliberately removes it.  Inventory
        # only those punctuation-bearing labels through the same canonicalizer
        # so row- and column-oriented variants have identical semantics.
        punctuation_rows = connection.execute(
            """
            SELECT r.page_json_version_id, r.section_id, r.table_id,
                   r.row_id, r.source_order, r.label_exact,
                   r.hierarchy_path_exact_json
            FROM row_node AS r
            JOIN selected_dual_page AS s USING(page_json_version_id)
            WHERE r.label_ascii_folded GLOB '*[^a-z0-9 %]*'
            ORDER BY s.selection_ordinal, r.section_id, r.table_id,
                     r.source_order, r.row_id
            """
        ).fetchall()
        seen_row_hits = {
            (
                row["page_json_version_id"],
                row["section_id"],
                row["table_id"],
                row["row_id"],
                row["axis_kind"],
                row["role"],
            )
            for row in row_hits
        }
        for raw in punctuation_rows:
            row = decoded_row_hit(raw)
            folded = _dual_axis_folded_label_v1(row["label_exact"])
            matches = []
            if folded in folded_metrics:
                matches.append(("METRIC", "METRIC"))
            matches.extend(
                ("ROLE", role) for role, aliases in folded_roles.items() if folded in aliases
            )
            for axis_kind, role in matches:
                identity = (
                    row["page_json_version_id"],
                    row["section_id"],
                    row["table_id"],
                    row["row_id"],
                    axis_kind,
                    role,
                )
                if identity in seen_row_hits:
                    continue
                seen_row_hits.add(identity)
                row_hits.append({**row, "axis_kind": axis_kind, "role": role})
        row_hits.sort(
            key=lambda row: (
                row["page_json_version_id"],
                row["section_id"],
                row["table_id"],
                row["source_order"],
                row["row_id"],
                row["axis_kind"],
                row["role"],
            )
        )
        hits_by_table: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for row in row_hits:
            key = (row["page_json_version_id"], row["section_id"], row["table_id"])
            hits_by_table.setdefault(key, []).append(row)
        candidate_keys = sorted(
            key
            for key, hits in hits_by_table.items()
            if any(hit["axis_kind"] == "ROLE" for hit in hits)
            or any(hit["axis_kind"] == "METRIC" for hit in hits)
        )
        connection.execute(
            "CREATE TEMP TABLE dual_candidate_table("
            "page_json_version_id TEXT NOT NULL, section_id TEXT NOT NULL, "
            "table_id TEXT NOT NULL, PRIMARY KEY(page_json_version_id,section_id,table_id))"
        )
        connection.executemany(
            "INSERT INTO dual_candidate_table VALUES (?,?,?)",
            candidate_keys,
        )
        column_rows = connection.execute(
            """
            SELECT c.page_json_version_id, c.section_id, c.table_id,
                   c.column_id, c.column_ordinal, c.header_path_exact_json,
                   c.value_kind
            FROM column_node AS c
            JOIN dual_candidate_table AS k
              USING(page_json_version_id,section_id,table_id)
            ORDER BY c.page_json_version_id, c.section_id, c.table_id,
                     c.column_ordinal, c.column_id
            """
        ).fetchall()
        candidate_context_rows = connection.execute(
            """
            SELECT k.page_json_version_id, k.section_id, k.table_id,
                   sn.title_exact AS section_title_exact,
                   sn.narratives_json, t.title_exact AS table_title_exact,
                   t.unit_exact
            FROM dual_candidate_table AS k
            JOIN section_node AS sn
              USING(page_json_version_id,section_id)
            JOIN table_node AS t
              USING(page_json_version_id,section_id,table_id)
            ORDER BY k.page_json_version_id, k.section_id, k.table_id
            """
        ).fetchall()
        candidate_context_by_key = {
            (row["page_json_version_id"], row["section_id"], row["table_id"]): row
            for row in candidate_context_rows
        }
        candidate_section_table_title_rows = connection.execute(
            """
            SELECT DISTINCT k.page_json_version_id, k.section_id,
                   t.title_exact AS table_title_exact
            FROM dual_candidate_table AS k
            JOIN table_node AS t
              ON t.page_json_version_id=k.page_json_version_id
             AND t.section_id=k.section_id
            WHERE t.title_exact IS NOT NULL
            ORDER BY k.page_json_version_id, k.section_id, t.source_order, t.table_id
            """
        ).fetchall()
        candidate_section_table_titles: dict[tuple[str, str], list[str]] = {}
        for row in candidate_section_table_title_rows:
            titles = candidate_section_table_titles.setdefault(
                (row["page_json_version_id"], row["section_id"]), []
            )
            if row["table_title_exact"] not in titles:
                titles.append(row["table_title_exact"])
        columns_by_table: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for row in column_rows:
            record = dict(row)
            leaf, exact_path = _dual_axis_header_leaf_v1(
                record["header_path_exact_json"],
                declared_unit_suffixes=folded_units,
            )
            record["header_leaf_ascii_folded"] = leaf
            record["header_path_exact"] = exact_path
            record.pop("header_path_exact_json")
            key = (record["page_json_version_id"], record["section_id"], record["table_id"])
            columns_by_table.setdefault(key, []).append(record)

        page_by_version = {row["page_json_version_id"]: row for row in selected_pages}
        selected_pages_by_document: dict[str, list[dict[str, Any]]] = {}
        for row in selected_pages:
            selected_pages_by_document.setdefault(row["document_id"], []).append(
                {
                    "physical_page": row["physical_page"],
                    "page_json_version_id": row["page_json_version_id"],
                }
            )
        regions: list[dict[str, Any]] = []
        for key in candidate_keys:
            hits = hits_by_table[key]
            columns = columns_by_table.get(key, [])
            row_roles = {
                role: [hit for hit in hits if hit["axis_kind"] == "ROLE" and hit["role"] == role]
                for role in folded_roles
            }
            metric_rows = [hit for hit in hits if hit["axis_kind"] == "METRIC"]
            metric_columns = [
                column
                for column in columns
                if column["value_kind"] == "MONEY"
                and column["header_leaf_ascii_folded"] in folded_metrics
            ]
            role_columns = {
                role: [
                    column
                    for column in columns
                    if column["value_kind"] == "MONEY"
                    and column["header_leaf_ascii_folded"] in aliases
                ]
                for role, aliases in folded_roles.items()
            }
            stacked_row_groups = stacked_period_role_groups(row_roles)
            orientations = []
            if (
                (
                    all(len(matches) <= 1 for matches in row_roles.values())
                    and any(len(matches) == 1 for matches in row_roles.values())
                )
                or stacked_row_groups is not None
            ) and len(metric_columns) == 1:
                orientations.append("ROW_ROLES_METRIC_COLUMN")
            if (
                len(metric_rows) == 1
                and all(len(matches) <= 1 for matches in role_columns.values())
                and any(len(matches) == 1 for matches in role_columns.values())
            ):
                orientations.append("METRIC_ROW_ROLE_COLUMNS")
            if len(orientations) != 1:
                continue
            if candidate_context_policy is not None:
                context_row = candidate_context_by_key[key]
                context_surfaces = [
                    context_row["section_title_exact"],
                    context_row["table_title_exact"],
                    *candidate_section_table_titles.get((key[0], key[1]), []),
                ]
                try:
                    narratives = json.loads(context_row["narratives_json"])
                except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise _error("selected dual-axis section narratives are invalid") from exc
                if type(narratives) is not list or any(type(item) is not str for item in narratives):
                    raise _error("selected dual-axis section narratives are invalid")
                context_surfaces.extend(narratives)
                folded_context = " ".join(
                    _dual_axis_folded_label_v1(surface)
                    for surface in context_surfaces
                    if type(surface) is str and surface
                )
                if any(
                    alias in folded_context
                    for alias in candidate_context_policy["hard_negative_aliases"]
                ):
                    continue
                partial_role_axis = (
                    any(not matches for matches in row_roles.values())
                    if orientations[0] == "ROW_ROLES_METRIC_COLUMN"
                    else any(not matches for matches in role_columns.values())
                )
                if partial_role_axis and not any(
                    alias in folded_context
                    for alias in candidate_context_policy["partial_axis_owner_aliases"]
                ):
                    continue
            page = page_by_version[key[0]]
            context_pages = [
                context
                for context in selected_pages_by_document[page["document_id"]]
                if max(1, page["physical_page"] - adjacent_page_radius)
                <= context["physical_page"]
                <= page["physical_page"] + adjacent_page_radius
            ]
            orientation = orientations[0]
            axis_evidence = {
                "metric": (
                    {k: v for k, v in metric_columns[0].items() if k != "value_kind"}
                    if orientation == "ROW_ROLES_METRIC_COLUMN"
                    else {
                        item_key: metric_rows[0][item_key]
                        for item_key in ("label_exact", "row_id", "source_order")
                    }
                ),
                "roles": {
                    role: (
                        {
                            item_key: row_roles[role][0][item_key]
                            for item_key in ("label_exact", "row_id", "source_order")
                        }
                        if orientation == "ROW_ROLES_METRIC_COLUMN"
                        and row_roles[role]
                        else {
                            item_key: role_columns[role][0][item_key]
                            for item_key in (
                                "column_id",
                                "column_ordinal",
                                "header_leaf_ascii_folded",
                                "header_path_exact",
                            )
                        }
                        if orientation == "METRIC_ROW_ROLE_COLUMNS"
                        and role_columns[role]
                        else {"presence": "ABSENT_SOURCE_AXIS_ROLE"}
                    )
                    for role in folded_roles
                },
            }
            if orientation == "ROW_ROLES_METRIC_COLUMN" and stacked_row_groups is not None:
                axis_evidence["stacked_period_role_groups"] = stacked_row_groups
            regions.append(
                {
                    "axis_evidence": axis_evidence,
                    "context_pages": context_pages,
                    "document_id": page["document_id"],
                    "orientation": orientation,
                    "page_json_version_id": key[0],
                    "physical_page": page["physical_page"],
                    "section_id": key[1],
                    "source_logical_name": page["source_logical_name"],
                    "table_id": key[2],
                }
            )

        control_cell_rows = []
        region_cell_rows = []
        if external_control_policy is not None:
            precontrol_documents = sorted({region["document_id"] for region in regions})
            connection.execute(
                "CREATE TEMP TABLE dual_control_document(document_id TEXT PRIMARY KEY)"
            )
            connection.executemany(
                "INSERT INTO dual_control_document VALUES (?)",
                ((document_id,) for document_id in precontrol_documents),
            )
            control_cell_rows = connection.execute(
                """
            SELECT s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, r.page_json_version_id,
                   r.section_id, r.table_id, r.row_id, r.label_exact,
                   r.row_kind, r.hierarchy_path_exact_json,
                   sn.title_exact AS section_title_exact,
                   t.title_exact AS table_title_exact, t.unit_exact,
                   c.column_id, c.column_ordinal, c.header_path_exact_json,
                   c.value_kind, vc.source_text, vc.visual_state
            FROM row_node AS r
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN section_node AS sn USING(page_json_version_id,section_id)
            JOIN table_node AS t USING(page_json_version_id,section_id,table_id)
            JOIN column_node AS c USING(page_json_version_id,section_id,table_id)
            JOIN value_cell AS vc
              USING(page_json_version_id,section_id,table_id,row_id,column_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN dual_control_document AS cd USING(document_id)
            WHERE sn.content_kind=?
              AND sn.statement_type=?
              AND r.row_kind=?
              AND c.value_kind='MONEY'
            ORDER BY s.selection_ordinal, r.section_id, r.table_id,
                     r.source_order, c.column_ordinal, c.column_id
            """,
                (
                    control_source_policy["content_kind"],
                    control_source_policy["statement_type"],
                    control_source_policy["row_kind"],
                ),
            ).fetchall()
            connection.execute(
                "CREATE TEMP TABLE dual_region_table("
                "page_json_version_id TEXT NOT NULL, section_id TEXT NOT NULL, "
                "table_id TEXT NOT NULL, "
                "PRIMARY KEY(page_json_version_id,section_id,table_id))"
            )
            connection.executemany(
                "INSERT INTO dual_region_table VALUES (?,?,?)",
                (
                    (
                        region["page_json_version_id"],
                        region["section_id"],
                        region["table_id"],
                    )
                    for region in regions
                ),
            )
            region_cell_rows = connection.execute(
                """
            SELECT vc.page_json_version_id, vc.section_id, vc.table_id,
                   vc.row_id, vc.column_id, vc.source_text, vc.visual_state,
                   r.label_exact, r.row_kind, c.column_ordinal,
                   c.header_path_exact_json, c.value_kind
            FROM value_cell AS vc
            JOIN dual_region_table AS k
              USING(page_json_version_id,section_id,table_id)
            JOIN row_node AS r
              USING(page_json_version_id,section_id,table_id,row_id)
            JOIN column_node AS c
              USING(page_json_version_id,section_id,table_id,column_id)
            ORDER BY vc.page_json_version_id, vc.section_id, vc.table_id,
                     r.source_order, c.column_ordinal, vc.row_id, vc.column_id
            """
            ).fetchall()

        def exact_reporting_dates(*surfaces: Any) -> set[date]:
            return {
                parsed
                for surface in surfaces
                if type(surface) is str and surface
                for parsed in _header_dates(surface)
                if (parsed.month, parsed.day) in {(3, 31), (6, 30), (9, 30), (12, 31)}
            }

        def decoded_header_path(raw: Any) -> list[str]:
            try:
                path_value = json.loads(raw)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected dual-axis control column header is invalid") from exc
            if type(path_value) is not list or any(
                value is not None and type(value) is not str for value in path_value
            ):
                raise _error("selected dual-axis control column header is invalid")
            return [value for value in path_value if type(value) is str and value]

        def declared_unit_alias(surface: Any) -> str | None:
            folded = _dual_axis_folded_label_v1(surface)
            matches = [
                alias
                for alias in folded_units
                if folded == alias or folded.endswith(" " + alias)
            ]
            longest = max((len(alias) for alias in matches), default=0)
            selected = sorted(alias for alias in matches if len(alias) == longest)
            return selected[0] if len(selected) == 1 else None

        external_controls_by_source: dict[str, list[dict[str, Any]]] = {}
        external_control_current_periods_by_source: dict[str, set[date]] = {}
        control_label_aliases = (
            set() if control_source_policy is None else set(control_source_policy["label_aliases"])
        )
        unit_magnitudes = (
            {}
            if external_control_policy is None
            else external_control_policy["unit_decimal_magnitude_by_alias"]
        )
        for row in control_cell_rows:
            label_tokens = _dual_axis_folded_label_v1(row["label_exact"]).split()
            numbered_control_leaf = label_tokens[:1] == ["1"]
            if numbered_control_leaf:
                label_tokens = label_tokens[1:]
            matched_control_label = " ".join(label_tokens)
            if matched_control_label not in control_label_aliases:
                continue
            try:
                hierarchy_path = json.loads(row["hierarchy_path_exact_json"])
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("selected dual-axis control row hierarchy is invalid") from exc
            if type(hierarchy_path) is not list or any(
                value is not None and type(value) is not str for value in hierarchy_path
            ):
                raise _error("selected dual-axis control row hierarchy is invalid")
            if not numbered_control_leaf and sum(
                _dual_axis_folded_label_v1(value) == matched_control_label
                for value in hierarchy_path
                if type(value) is str
            ) < 2:
                continue
            header_path = decoded_header_path(row["header_path_exact_json"])
            section_dates = exact_reporting_dates(row["section_title_exact"])
            table_dates = exact_reporting_dates(row["table_title_exact"])
            local_current_dates = section_dates or table_dates
            current = max(local_current_dates) if len(local_current_dates) == 1 else None
            if current is not None:
                external_control_current_periods_by_source.setdefault(
                    row["source_logical_name"], set()
                ).add(current)
            header_dates = exact_reporting_dates(*header_path)
            period = next(iter(header_dates)) if len(header_dates) == 1 else None
            header_folded = " ".join(
                _dual_axis_folded_label_v1(surface) for surface in header_path
            )
            if period is None and current is not None:
                if "so cuoi nam" in header_folded or "so cuoi ky" in header_folded:
                    period = current
                elif "so dau nam" in header_folded or "so dau ky" in header_folded:
                    period = date(current.year - 1, 12, 31)
            if period is None:
                continue
            try:
                coefficient = _money(row["source_text"])["coefficient"]
            except ValueError:
                continue
            unit_candidates = [
                (surface, alias, unit_magnitudes[alias])
                for surface in [*header_path, row["unit_exact"]]
                if (alias := declared_unit_alias(surface)) is not None
            ]
            candidate_magnitudes = {
                magnitude for _surface, _alias, magnitude in unit_candidates
            }
            unit_exact = (
                next(
                    surface
                    for surface, _alias, magnitude in unit_candidates
                    if magnitude == next(iter(candidate_magnitudes))
                )
                if len(candidate_magnitudes) == 1
                else None
            )
            record = {
                "coefficient": coefficient,
                "control_report_norm_id": external_control_policy[
                    "control_report_norm_id"
                ],
                "period": period.isoformat(),
                "source_ref": {
                    "column_id": row["column_id"],
                    "page_json_version_id": row["page_json_version_id"],
                    "physical_page": row["physical_page"],
                    "row_id": row["row_id"],
                    "section_id": row["section_id"],
                    "table_id": row["table_id"],
                },
                "source_text": row["source_text"],
                "unit_exact": unit_exact,
            }
            controls = external_controls_by_source.setdefault(
                row["source_logical_name"], []
            )
            if record not in controls:
                controls.append(record)
        for controls in external_controls_by_source.values():
            controls.sort(
                key=lambda record: (
                    record["period"],
                    record["source_ref"]["physical_page"],
                    record["source_ref"]["section_id"],
                    record["source_ref"]["table_id"],
                    record["source_ref"]["row_id"],
                    record["source_ref"]["column_id"],
                )
            )

        region_cells_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for raw in region_cell_rows:
            record = dict(raw)
            record["header_path_exact"] = decoded_header_path(
                record.pop("header_path_exact_json")
            )
            region_cells_by_key.setdefault(
                (record["page_json_version_id"], record["section_id"], record["table_id"]),
                [],
            ).append(record)

        def metric_leaf(region: Mapping[str, Any]) -> str:
            evidence = region["axis_evidence"]["metric"]
            if region["orientation"] == "ROW_ROLES_METRIC_COLUMN":
                return evidence["header_leaf_ascii_folded"]
            return _dual_axis_folded_label_v1(evidence["label_exact"])

        def cell_coefficient(record: Mapping[str, Any]) -> int | None:
            try:
                return _money(record["source_text"])["coefficient"]
            except ValueError:
                return None

        def region_population_coefficient(region: Mapping[str, Any]) -> int | None:
            key = (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            cells = region_cells_by_key.get(key, [])
            if region["orientation"] == "ROW_ROLES_METRIC_COLUMN":
                metric_column_id = region["axis_evidence"]["metric"]["column_id"]
                metric_cells = [cell for cell in cells if cell["column_id"] == metric_column_id]
                totals = [
                    coefficient
                    for cell in metric_cells
                    if (
                        cell["row_kind"] == "TOTAL"
                        or _dual_axis_folded_label_v1(cell["label_exact"])
                        in {"tong", "tong cong"}
                    )
                    and (coefficient := cell_coefficient(cell)) is not None
                ]
                if len(totals) == 1:
                    return totals[0]
                role_values = []
                for evidence in region["axis_evidence"]["roles"].values():
                    if "row_id" not in evidence:
                        continue
                    matches = [
                        cell_coefficient(cell)
                        for cell in metric_cells
                        if cell["row_id"] == evidence["row_id"]
                    ]
                    if len(matches) != 1 or matches[0] is None:
                        return None
                    role_values.append(matches[0])
            else:
                metric_row_id = region["axis_evidence"]["metric"]["row_id"]
                metric_cells = [cell for cell in cells if cell["row_id"] == metric_row_id]
                totals = [
                    coefficient
                    for cell in metric_cells
                    if _dual_axis_header_leaf_v1(
                        json.dumps(cell["header_path_exact"], ensure_ascii=False),
                        declared_unit_suffixes=folded_units,
                    )[0]
                    in {"tong", "tong cong"}
                    and (coefficient := cell_coefficient(cell)) is not None
                ]
                if len(totals) == 1:
                    return totals[0]
                role_values = []
                for evidence in region["axis_evidence"]["roles"].values():
                    if "column_id" not in evidence:
                        continue
                    matches = [
                        cell_coefficient(cell)
                        for cell in metric_cells
                        if cell["column_id"] == evidence["column_id"]
                    ]
                    if len(matches) != 1 or matches[0] is None:
                        return None
                    role_values.append(matches[0])
            return sum(role_values) if role_values else None

        def region_period(
            region: Mapping[str, Any], *, allow_document_current: bool
        ) -> date | None:
            key = (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            context_row = candidate_context_by_key[key]
            narratives = json.loads(context_row["narratives_json"])
            table_dates = exact_reporting_dates(context_row["table_title_exact"])
            section_dates = exact_reporting_dates(
                context_row["section_title_exact"], *narratives
            )
            dates = table_dates or section_dates
            if len(dates) == 1:
                return next(iter(dates))
            document_current_periods = external_control_current_periods_by_source.get(
                region["source_logical_name"], set()
            )
            return (
                next(iter(document_current_periods))
                if allow_document_current and len(document_current_periods) == 1
                else None
            )

        def region_unit_magnitude(region: Mapping[str, Any]) -> int | None:
            key = (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            context_row = candidate_context_by_key[key]
            surfaces = [context_row["unit_exact"]]
            surfaces.extend(
                surface
                for cell in region_cells_by_key.get(key, [])
                for surface in cell["header_path_exact"]
            )
            aliases = {
                alias
                for surface in surfaces
                if (alias := declared_unit_alias(surface)) is not None
            }
            magnitudes = {unit_magnitudes[alias] for alias in aliases}
            return next(iter(magnitudes)) if len(magnitudes) == 1 else None

        external_control_dispositions: list[dict[str, Any]] = []
        region_count_before_population_control = len(regions)
        if external_control_policy is not None:
            query_gate_metrics = set(
                external_control_policy["query_gate_metric_aliases"]
            )
            controlled_region_counts_by_source: dict[str, int] = {}
            for region in regions:
                if metric_leaf(region) in query_gate_metrics:
                    controlled_region_counts_by_source[region["source_logical_name"]] = (
                        controlled_region_counts_by_source.get(
                            region["source_logical_name"], 0
                        )
                        + 1
                    )
            controlled_regions = []
            for region in regions:
                metric = metric_leaf(region)
                if metric not in query_gate_metrics:
                    controlled_regions.append(region)
                    continue
                population = region_population_coefficient(region)
                period = region_period(
                    region,
                    allow_document_current=(
                        controlled_region_counts_by_source[region["source_logical_name"]]
                        == 1
                        and "stacked_period_role_groups"
                        not in region["axis_evidence"]
                    ),
                )
                magnitude = region_unit_magnitude(region)
                controls = external_controls_by_source.get(
                    region["source_logical_name"], []
                )
                matching_controls = [
                    control
                    for control in controls
                    if period is not None
                    and control["period"] == period.isoformat()
                    and magnitude is not None
                    and (
                        alias := declared_unit_alias(control["unit_exact"])
                    )
                    is not None
                    and unit_magnitudes[alias] == magnitude
                ]
                control_values = {control["coefficient"] for control in matching_controls}
                accepted = (
                    population is not None
                    and len(control_values) == 1
                    and population == next(iter(control_values))
                )
                disposition = {
                    "control_report_norm_id": external_control_policy[
                        "control_report_norm_id"
                    ],
                    "control_value": next(iter(control_values)) if len(control_values) == 1 else None,
                    "match_rule": external_control_policy["match_rule"],
                    "metric": metric,
                    "period": None if period is None else period.isoformat(),
                    "population_value": population,
                    "region_ref": {
                        key: region[key]
                        for key in (
                            "page_json_version_id",
                            "physical_page",
                            "section_id",
                            "table_id",
                        )
                    },
                    "status": (
                        "ACCEPTED_EXACT_EXTERNAL_POPULATION_CONTROL"
                        if accepted
                        else "DEFERRED_TO_EVALUATOR_EXACT_PERIOD_AXIS"
                        if period is None
                        else "REJECTED_EXTERNAL_POPULATION_CONTROL_CONFLICT"
                        if len(control_values) == 1 and population is not None
                        else "REJECTED_EXTERNAL_POPULATION_CONTROL_ABSENT_OR_AMBIGUOUS"
                    ),
                    "unit_decimal_magnitude": magnitude,
                }
                external_control_dispositions.append(disposition)
                region["external_population_control"] = {
                    **canonical_clone_v1(disposition),
                    "control_sources": canonical_clone_v1(matching_controls),
                }
                if accepted:
                    controlled_regions.append(region)
            gated_regions = [
                item for item in regions if metric_leaf(item) in query_gate_metrics
            ]
            rejected_query_gate_sources = {
                region["source_logical_name"]
                for region, disposition in zip(
                    gated_regions,
                    external_control_dispositions,
                    strict=True,
                )
                if disposition["status"]
                != "ACCEPTED_EXACT_EXTERNAL_POPULATION_CONTROL"
            }
            if rejected_query_gate_sources:
                for disposition, gated_region in zip(
                    external_control_dispositions,
                    gated_regions,
                    strict=True,
                ):
                    if gated_region["source_logical_name"] not in rejected_query_gate_sources:
                        continue
                    disposition["status"] = (
                        "REJECTED_DOCUMENT_HAS_UNMATCHED_CONTROLLED_PERIOD_LANE"
                        if disposition["status"]
                        == "ACCEPTED_EXACT_EXTERNAL_POPULATION_CONTROL"
                        else "REJECTED_DOCUMENT_CONTROLLED_PERIOD_AXIS_IS_NOT_EXACT"
                        if disposition["status"]
                        == "DEFERRED_TO_EVALUATOR_EXACT_PERIOD_AXIS"
                        else disposition["status"]
                    )
                controlled_regions = [
                    region
                    for region in controlled_regions
                    if metric_leaf(region) not in query_gate_metrics
                    or region["source_logical_name"]
                    not in rejected_query_gate_sources
                ]
            regions = controlled_regions

        target_documents = sorted({region["document_id"] for region in regions})
        connection.execute("CREATE TEMP TABLE dual_target_document(document_id TEXT PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO dual_target_document VALUES (?)",
            ((document_id,) for document_id in target_documents),
        )
        title_rows = connection.execute(
            """
            SELECT s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, sn.section_id, NULL AS table_id,
                   'SECTION_TITLE' AS source_kind, sn.title_exact AS text_exact,
                   NULL AS narrative_ordinal
            FROM section_node AS sn
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN dual_target_document AS td USING(document_id)
            WHERE sn.title_exact IS NOT NULL
            UNION ALL
            SELECT s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, t.section_id, t.table_id,
                   'TABLE_TITLE' AS source_kind, t.title_exact AS text_exact,
                   NULL AS narrative_ordinal
            FROM table_node AS t
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN dual_target_document AS td USING(document_id)
            WHERE t.title_exact IS NOT NULL
            ORDER BY selection_ordinal, section_id, table_id, source_kind
            """
        ).fetchall()
        narrative_rows = connection.execute(
            """
            SELECT s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, sn.section_id, NULL AS table_id,
                   'SECTION_NARRATIVE' AS source_kind,
                   narrative.value AS text_exact,
                   CAST(narrative.key AS INTEGER) + 1 AS narrative_ordinal
            FROM section_node AS sn
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN dual_target_document AS td USING(document_id)
            JOIN json_each(sn.narratives_json) AS narrative
            WHERE narrative.type='text'
            ORDER BY selection_ordinal, sn.section_id, narrative_ordinal
            """
        ).fetchall()
        unit_rows = connection.execute(
            """
            SELECT s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, t.section_id, t.table_id,
                   'TABLE_UNIT' AS source_kind, t.unit_exact AS text_exact
            FROM table_node AS t
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN dual_target_document AS td USING(document_id)
            WHERE t.unit_exact IS NOT NULL
            ORDER BY selection_ordinal, t.section_id, t.table_id
            """
        ).fetchall()
        header_rows = connection.execute(
            """
            SELECT s.selection_ordinal, d.document_id, d.source_logical_name,
                   p.physical_page, c.section_id, c.table_id, c.column_id,
                   c.header_path_exact_json
            FROM column_node AS c
            JOIN selected_dual_page AS s USING(page_json_version_id)
            JOIN page_json_version AS v USING(page_json_version_id)
            JOIN page AS p USING(page_id)
            JOIN document AS d USING(document_id)
            JOIN dual_target_document AS td USING(document_id)
            ORDER BY selection_ordinal, c.section_id, c.table_id,
                     c.column_ordinal, c.column_id
            """
        ).fetchall()

    context_by_source = {
        region["source_logical_name"]: {
            "period_evidence": [],
            "unit_evidence": [],
        }
        for region in regions
    }
    if external_control_policy is not None:
        for source, context in context_by_source.items():
            context["external_population_controls"] = canonical_clone_v1(
                external_controls_by_source.get(source, [])
            )

    def append_context(target: list[dict[str, Any]], row: Mapping[str, Any], text: str) -> None:
        record = {
            "physical_page": row["physical_page"],
            "section_id": row["section_id"],
            "source_kind": row["source_kind"],
            "table_id": row["table_id"],
            "text_exact": text,
        }
        if "narrative_ordinal" in row.keys() and type(row["narrative_ordinal"]) is int:
            record["narrative_ordinal"] = row["narrative_ordinal"]
        if record not in target:
            target.append(record)

    for row in narrative_rows:
        if _DUAL_AXIS_YEAR.search(row["text_exact"]):
            append_context(
                context_by_source[row["source_logical_name"]]["period_evidence"],
                row,
                row["text_exact"],
            )
    for row in title_rows:
        if _DUAL_AXIS_YEAR.search(row["text_exact"]):
            append_context(
                context_by_source[row["source_logical_name"]]["period_evidence"],
                row,
                row["text_exact"],
            )
    for row in unit_rows:
        folded = _dual_axis_folded_label_v1(row["text_exact"])
        if any(folded == unit or folded.endswith(" " + unit) for unit in folded_units):
            append_context(
                context_by_source[row["source_logical_name"]]["unit_evidence"],
                row,
                row["text_exact"],
            )
    for row in header_rows:
        try:
            header_path = json.loads(row["header_path_exact_json"])
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("selected dual-axis column header path is invalid") from exc
        if type(header_path) is not list or any(
            value is not None and type(value) is not str for value in header_path
        ):
            raise _error("selected dual-axis column header path is invalid")
        for text_exact in (value for value in header_path if type(value) is str and value):
            record = {
                **dict(row),
                "source_kind": "COLUMN_HEADER",
                "table_id": row["table_id"],
            }
            if _DUAL_AXIS_YEAR.search(text_exact):
                append_context(
                    context_by_source[row["source_logical_name"]]["period_evidence"],
                    record,
                    text_exact,
                )
            folded = _dual_axis_folded_label_v1(text_exact)
            if any(folded == unit or folded.endswith(" " + unit) for unit in folded_units):
                append_context(
                    context_by_source[row["source_logical_name"]]["unit_evidence"],
                    record,
                    text_exact,
                )
    ordered_region_axis = [
        {
            key: region[key]
            for key in (
                "source_logical_name",
                "physical_page",
                "page_json_version_id",
                "section_id",
                "table_id",
                "orientation",
            )
        }
        for region in sorted(
            regions,
            key=lambda item: (
                item["source_logical_name"],
                item["physical_page"],
                item["section_id"],
                item["table_id"],
                item["page_json_version_id"],
                item["orientation"],
            ),
        )
    ]
    query_receipt = {
        "candidate_table_count_before_column_decode": len(candidate_keys),
            "decoded_column_header_count": len(column_rows),
            "document_context_period_record_count": sum(
                len(context["period_evidence"]) for context in context_by_source.values()
            ),
            "document_context_unit_record_count": sum(
                len(context["unit_evidence"]) for context in context_by_source.values()
            ),
            "exact_region_count": len(regions),
            "exact_region_axis_sha256": canonical_json_sha256_v1(ordered_region_axis),
            "indexed_row_hit_count": len(row_hits),
            "orientation_counts": {
                orientation: sum(region["orientation"] == orientation for region in regions)
                for orientation in (
                    "METRIC_ROW_ROLE_COLUMNS",
                    "ROW_ROLES_METRIC_COLUMN",
                )
            },
            "stacked_period_row_region_count": sum(
                region["orientation"] == "ROW_ROLES_METRIC_COLUMN"
                and "stacked_period_role_groups" in region["axis_evidence"]
                for region in regions
            ),
            "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
                list(selected_page_json_version_ids)
            ),
            "selected_page_json_version_count": len(selected_page_json_version_ids),
            "target_document_count": len(target_documents),
            "target_document_header_record_count": len(header_rows),
            "target_document_title_record_count": len(title_rows),
    }
    if external_control_policy is not None:
        query_receipt["external_population_control"] = {
            "accepted_query_gate_count": sum(
                disposition["status"]
                == "ACCEPTED_EXACT_EXTERNAL_POPULATION_CONTROL"
                for disposition in external_control_dispositions
            ),
            "control_record_count": sum(
                len(records) for records in external_controls_by_source.values()
            ),
            "control_report_norm_id": external_control_policy[
                "control_report_norm_id"
            ],
            "deferred_query_gate_count": sum(
                disposition["status"] == "DEFERRED_TO_EVALUATOR_EXACT_PERIOD_AXIS"
                for disposition in external_control_dispositions
            ),
            "disposition_axis_sha256": canonical_json_sha256_v1(
                external_control_dispositions
            ),
            "match_rule": external_control_policy["match_rule"],
            "region_count_after_query_gate": len(regions),
            "region_count_before_query_gate": region_count_before_population_control,
            "rejected_query_gate_count": sum(
                disposition["status"].startswith("REJECTED_")
                for disposition in external_control_dispositions
            ),
        }
    query_receipt["target_document_narrative_record_count"] = len(narrative_rows)
    return {
        "document_context_by_source": context_by_source,
        "query_receipt": query_receipt,
        "regions": regions,
    }


def validate_selected_dual_axis_family_candidate_replays_v1(
    path: Path,
    *,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Rebuild every dual-axis trial from one authenticated selected frontier."""

    from bctc_ai.evaluation.gemini_json_dual_axis_accounting_family_v1 import (
        evaluate_gemini_json_dual_axis_family_cluster_v1,
    )
    from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
        NOT_OBSERVED,
        READY,
        UNRESOLVED,
    )
    from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1

    policy = compiled_specs.get("dual_axis_projection_policy")
    if type(policy) is not dict:
        raise _error("selected dual-axis candidate replay policy is absent")
    version_ids = list(selected_page_json_version_ids)
    provenance = selected_page_json_provenance_receipts_v1(
        path,
        page_json_version_ids=version_ids,
    )
    selected_documents = []
    seen_sources = set()
    for record in provenance:
        source = record["source_logical_name"]
        if selected_documents and selected_documents[-1]["source_logical_name"] == source:
            if selected_documents[-1]["source_sha256"] != record["source_sha256"]:
                raise _error("selected dual-axis document source hash drifted")
            continue
        if source in seen_sources:
            raise _error("selected dual-axis document page frontier is not contiguous")
        seen_sources.add(source)
        selected_documents.append(
            {
                "document_ordinal": len(selected_documents) + 1,
                "source_logical_name": source,
                "source_sha256": record["source_sha256"],
            }
        )

    queried = query_selected_dual_axis_family_regions_v1(
        path,
        selected_page_json_version_ids=version_ids,
        metric_aliases=policy["metric_aliases"],
        role_aliases={
            role: compiled_specs["query_aliases_by_role"][role]
            for role in policy["projected_role_order"]
        },
        unit_aliases=policy["unit_aliases"],
        external_population_control=policy.get("external_population_control"),
        adjacent_page_radius=1,
    )
    regions_by_source: dict[str, list[dict[str, Any]]] = {}
    for region in queried["regions"]:
        regions_by_source.setdefault(region["source_logical_name"], []).append(region)
    candidate_version_ids = list(
        dict.fromkeys(region["page_json_version_id"] for region in queried["regions"])
    )
    loaded = (
        load_page_json_versions_v1(path, page_json_version_ids=candidate_version_ids)
        if candidate_version_ids
        else []
    )
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in loaded
    }
    if set(page_json_by_version) != set(candidate_version_ids):
        raise _error("selected dual-axis candidate page JSON axis is incomplete")

    rebuilt_trials = []
    for document in selected_documents:
        source = document["source_logical_name"]
        regions = regions_by_source.get(source, [])
        candidates = []
        if regions:
            candidates.append(
                evaluate_gemini_json_dual_axis_family_cluster_v1(
                    regions=regions,
                    page_json_by_version=page_json_by_version,
                    document_context=queried["document_context_by_source"][source],
                    compiled_specs=dict(compiled_specs),
                    query_receipt=queried["query_receipt"],
                )
            )
        # The public runner retains an authenticated hard-negative candidate
        # in the trial receipt but excludes it from status arbitration.  Replay
        # the same distinction so a one-role dual-axis shortlist cannot turn a
        # report-segment table into an active F11 conflict.
        active_candidates = [
            candidate
            for candidate in candidates
            if not (
                candidate["status"] == UNRESOLVED
                and "HARD_NEGATIVE_FAMILY_TITLE_PRESENT" in candidate.get("reasons", [])
            )
        ]
        ready = [candidate for candidate in active_candidates if candidate["status"] == READY]
        unresolved = [
            candidate for candidate in active_candidates if candidate["status"] == UNRESOLVED
        ]
        if len(ready) == 1:
            status = READY
            selected_candidate_id = ready[0]["candidate_id"]
            mappings = ready[0]["mappings"]
            reasons = []
        elif not candidates:
            status = NOT_OBSERVED
            selected_candidate_id = None
            mappings = []
            reasons = []
        else:
            status = UNRESOLVED
            selected_candidate_id = None
            mappings = []
            reasons = sorted(
                {
                    *(["MULTIPLE_EXACT_GEMINI_JSON_FAMILY_REGIONS"] if len(ready) > 1 else []),
                    *(reason for candidate in unresolved for reason in candidate["reasons"]),
                }
            )
        rebuilt_trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                **document,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "status": status,
            }
        )
    supplied_trials = [dict(trial) for trial in trials]
    if not same_typed_json_v1(supplied_trials, rebuilt_trials):
        raise _error("selected dual-axis sweep trials do not replay from canonical page JSON")
    return rebuilt_trials


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
    prompt_sha256: str | Mapping[int, str],
    response_schema_sha256: str,
    requested_model: str,
    requested_service_tier: str | None = None,
    selected_provider: str | None = None,
    allowed_gateway_service_tiers: Sequence[Mapping[str, str]] | None = None,
    preferred_gateway_service_tiers: Sequence[Mapping[str, str]] | None = None,
    page_image_sha256s: Mapping[int, str] | None = None,
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
    page_prompt_sha256s: dict[int, str] | None = None
    if type(prompt_sha256) is str:
        if not prompt_sha256:
            raise _error("document manifest extraction contract is invalid")
        prompt_contract: dict[str, Any] = {"prompt_sha256": prompt_sha256}
    elif type(prompt_sha256) is dict:
        if (
            set(prompt_sha256) != set(pages)
            or any(type(key) is not int for key in prompt_sha256)
            or any(type(value) is not str or not value for value in prompt_sha256.values())
        ):
            raise _error("document manifest page prompt frontier is invalid")
        page_prompt_sha256s = dict(sorted(prompt_sha256.items()))
        prompt_contract = {
            "page_prompt_sha256s": [
                {"physical_page": page, "prompt_sha256": prompt}
                for page, prompt in page_prompt_sha256s.items()
            ]
        }
    else:
        raise _error("document manifest extraction contract is invalid")
    selected_page_images: dict[int, str] | None = None
    if page_image_sha256s is not None:
        if (
            type(page_image_sha256s) is not dict
            or set(page_image_sha256s) != set(pages)
            or any(type(key) is not int for key in page_image_sha256s)
            or any(
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
                for value in page_image_sha256s.values()
            )
        ):
            raise _error("document manifest page image frontier is invalid")
        selected_page_images = dict(sorted(page_image_sha256s.items()))
        prompt_contract["page_image_sha256s"] = [
            {"image_sha256": image_sha, "physical_page": page}
            for page, image_sha in selected_page_images.items()
        ]
    common_contract = {
        **prompt_contract,
        "response_schema_sha256": response_schema_sha256,
        "requested_model": requested_model,
    }
    if any(
        type(value) is not str or not value
        for key, value in common_contract.items()
        if key not in {"page_image_sha256s", "page_prompt_sha256s"}
    ):
        raise _error("document manifest extraction contract is invalid")
    if allowed_gateway_service_tiers is None:
        if preferred_gateway_service_tiers is not None:
            raise _error("document manifest provider preference requires mixed routes")
        if (
            type(requested_service_tier) is not str
            or not requested_service_tier
            or type(selected_provider) is not str
            or not selected_provider
        ):
            raise _error("document manifest extraction contract is invalid")
        allowed_routes = None
        extraction_contract = {
            **common_contract,
            "requested_service_tier": requested_service_tier,
            "selected_provider": selected_provider,
        }
    else:
        if requested_service_tier is not None or selected_provider is not None:
            raise _error("mixed document manifest cannot also select one provider")
        routes: list[dict[str, str]] = []
        for route in allowed_gateway_service_tiers:
            if type(route) is not dict or set(route) != {"gateway", "requested_service_tier"}:
                raise _error("mixed document provider route fields drifted")
            gateway = route["gateway"]
            service_tier = route["requested_service_tier"]
            if (
                type(gateway) is not str
                or not gateway
                or type(service_tier) is not str
                or not service_tier
            ):
                raise _error("mixed document provider route is invalid")
            routes.append({"gateway": gateway, "requested_service_tier": service_tier})
        routes.sort(key=lambda route: (route["gateway"], route["requested_service_tier"]))
        if not routes or len({tuple(route.values()) for route in routes}) != len(routes):
            raise _error("mixed document provider routes are empty or duplicate")
        allowed_routes = {(route["gateway"], route["requested_service_tier"]) for route in routes}
        extraction_contract = {
            **common_contract,
            "allowed_gateway_service_tiers": routes,
        }
        preferred_routes: list[dict[str, str]] | None = None
        if preferred_gateway_service_tiers is not None:
            preferred_routes = []
            for route in preferred_gateway_service_tiers:
                if type(route) is not dict or set(route) != {
                    "gateway",
                    "requested_service_tier",
                }:
                    raise _error("mixed document provider preference fields drifted")
                if any(type(value) is not str or not value for value in route.values()):
                    raise _error("mixed document provider preference is invalid")
                preferred_routes.append(dict(route))
            preferred_route_keys = [
                (route["gateway"], route["requested_service_tier"]) for route in preferred_routes
            ]
            if (
                len(preferred_route_keys) != len(set(preferred_route_keys))
                or set(preferred_route_keys) != allowed_routes
            ):
                raise _error("mixed document provider preference is not one route permutation")
            extraction_contract["preferred_gateway_service_tiers"] = preferred_routes
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
        prompt_clause = "AND r.prompt_sha256=?" if page_prompt_sha256s is None else ""
        prompt_parameters = (prompt_sha256,) if page_prompt_sha256s is None else ()
        records = connection.execute(
            f"""
            SELECT p.physical_page, p.page_id, p.image_sha256,
                   p.image_size_bytes, p.pixel_width, p.pixel_height,
                   p.render_dpi, p.media_type,
                   r.extraction_run_id, r.selected_model,
                   r.prompt_sha256,
                   r.requested_service_tier, r.selected_provider,
                   r.selected_service_tier, r.response_id_sha256,
                   r.input_tokens, r.output_tokens, r.thought_tokens,
                   r.cached_input_tokens, r.total_tokens, r.cost_usd,
                   r.cost_disposition,
                   (SELECT MIN(a.provider) FROM provider_attempt AS a
                    WHERE a.extraction_run_id=r.extraction_run_id) AS gateway,
                   (SELECT COUNT(DISTINCT a.provider) FROM provider_attempt AS a
                    WHERE a.extraction_run_id=r.extraction_run_id) AS gateway_count,
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
              {prompt_clause}
              AND r.response_schema_sha256=?
              AND r.requested_model=?
            ORDER BY p.physical_page
            """,
            (
                document["document_id"],
                *pages,
                *prompt_parameters,
                response_schema_sha256,
                requested_model,
            ),
        ).fetchall()
    if page_prompt_sha256s is not None:
        records = [
            record
            for record in records
            if record["prompt_sha256"] == page_prompt_sha256s[record["physical_page"]]
        ]
    if selected_page_images is not None:
        records = [
            record
            for record in records
            if record["image_sha256"] == selected_page_images[record["physical_page"]]
        ]
    if allowed_routes is None:
        records = [
            record
            for record in records
            if record["requested_service_tier"] == requested_service_tier
            and record["selected_provider"] == selected_provider
        ]
    else:
        records = [
            record
            for record in records
            if record["gateway_count"] == 1
            and (record["gateway"], record["requested_service_tier"]) in allowed_routes
        ]
        if preferred_routes is not None:
            route_rank = {
                (route["gateway"], route["requested_service_tier"]): rank
                for rank, route in enumerate(preferred_routes)
            }
            records_by_page: dict[int, list[Any]] = {}
            for record in records:
                records_by_page.setdefault(record["physical_page"], []).append(record)
            selected_records = []
            for page in pages:
                candidates = records_by_page.get(page, [])
                if not candidates:
                    continue
                best_rank = min(
                    route_rank[(record["gateway"], record["requested_service_tier"])]
                    for record in candidates
                )
                best = [
                    record
                    for record in candidates
                    if route_rank[(record["gateway"], record["requested_service_tier"])]
                    == best_rank
                ]
                if len(best) != 1:
                    raise _error("preferred document provider route is not unique")
                selected_records.append(best[0])
            records = selected_records
    returned_pages = [record["physical_page"] for record in records]
    if set(returned_pages) != set(pages):
        raise _error("document manifest page frontier is incomplete")
    if returned_pages != pages:
        raise _error("document manifest page frontier is duplicate")
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
        page_record = {
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
        if allowed_routes is not None:
            page_record["provider_route"] = {
                "gateway": record["gateway"],
                "requested_service_tier": record["requested_service_tier"],
                "selected_provider": record["selected_provider"],
            }
        if page_prompt_sha256s is not None:
            page_record["prompt_sha256"] = record["prompt_sha256"]
        page_records.append(page_record)
    material = {
        "document": {
            "document_id": document["document_id"],
            "source_logical_name": document["source_logical_name"],
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        },
        "extraction_contract": extraction_contract,
        "format_version": (
            "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
            if selected_page_images is not None
            else "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3"
            if page_prompt_sha256s is not None
            else "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V1"
            if allowed_routes is None
            else "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V2"
        ),
        "page_count": len(page_records),
        "pages": page_records,
        "status_counts": dict(sorted(status_counts.items())),
        "totals": {**totals, "cost_usd": format(total_cost, ".12f")},
    }
    return {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
