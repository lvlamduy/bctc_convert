from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import duckdb
import yaml
from bson import BSON
from pymongo import MongoClient

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.schema.registry import SchemaItem, load_all

SOURCE_COLLECTION = "data_chart"
REFERENCE_AUTHORITY = "HISTORICAL_WEAK_REFERENCE_ONLY"
RAW_SERIES = "UPSTREAM_NUMERIC_SERIES"
YTD_SERIES = "UPSTREAM_DERIVED_YTD"
_YEARLY_TERM = re.compile(r"N/(?P<year>\d{4})")
_QUARTERLY_TERM = re.compile(r"Q(?P<quarter>[1-4])/(?P<year>\d{4})")
_YTD_FEATURE = re.compile(r"YTD_(?P<report_norm_id>\d+)")
_CSV_NULL = "__BCTC_DUCKDB_NULL_72F296E1__"


def load_historical_reference_policy(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source = payload.get("source")
    series = payload.get("series")
    safety = payload.get("safety")
    if payload.get("version") != 1 or payload.get("authority") != REFERENCE_AUTHORITY:
        raise ValueError(f"invalid historical reference policy identity: {path}")
    if not isinstance(source, dict) or not isinstance(series, dict) or not isinstance(safety, dict):
        raise ValueError(f"invalid historical reference policy sections: {path}")
    expected_source = {
        "archive_registry": "data/registered/mongodb_dump_registry.json",
        "collection": SOURCE_COLLECTION,
        "industry_field": "stock_industry",
        "allowed_industry_value": "bank",
        "stock_id_field": "stock_id",
        "term_type_field": "term_type",
        "data_field": "data",
        "norm_term_feature": "NormTerm",
    }
    if any(source.get(key) != value for key, value in expected_source.items()):
        raise ValueError(f"unsupported historical Mongo source contract: {path}")
    if source.get("allowed_term_types") != {
        "yearly": "ANNUAL",
        "quaterly": "QUARTERLY",
    }:
        raise ValueError(f"unsupported historical term-type contract: {path}")
    if (
        series.get("numeric_feature_is_report_norm_id") is not True
        or series.get("upstream_ytd_prefix") != "YTD_"
        or series.get("identity_features") != ["NormTerm", "Q", "Y", "Stock_ID"]
        or series.get("unknown_numeric_feature_action") != "EXCLUDE_AND_AUDIT"
        or series.get("unknown_named_feature_action") != "EXCLUDE_AND_AUDIT"
    ):
        raise ValueError(f"unsupported historical series contract: {path}")
    forbidden_true = (
        "mapping_candidate_generation_allowed",
        "pdf_confidence_promotion_allowed",
        "pdf_value_overwrite_allowed",
        "upstream_ytd_can_supply_pdf_derivation_operand",
    )
    if any(safety.get(key) is not False for key in forbidden_true):
        raise ValueError(f"historical reference policy weakens a forbidden safety gate: {path}")
    if safety.get("lookup_requires_resolved_report_norm_id") is not True:
        raise ValueError(f"historical reference lookup must require a resolved ID: {path}")
    if safety.get("can_trigger_targeted_reread_or_review") is not True:
        raise ValueError(f"historical reference must remain review-only: {path}")
    if safety.get("unit") != "UNKNOWN" or safety.get("scope") != "UNKNOWN":
        raise ValueError(f"historical reference cannot infer unit or scope: {path}")
    return payload


class HistoricalValueState(StrEnum):
    VALUE = "VALUE"
    ZERO = "ZERO"
    NULL = "NULL"
    NAN = "NAN"
    POSITIVE_INFINITY = "POSITIVE_INFINITY"
    NEGATIVE_INFINITY = "NEGATIVE_INFINITY"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"
    INVALID_TYPE = "INVALID_TYPE"


@dataclass(frozen=True)
class HistoricalReferenceCell:
    stock_id: str
    source_document_id: str
    source_collection: str
    source_term_type: str
    normalized_term_type: str
    norm_term: str
    calendar_year: int
    calendar_quarter: int | None
    source_index: int
    source_feature: str
    series_kind: str
    report_norm_id: int
    statement_type: str
    schema_order: int
    canonical_name: str
    value_state: str
    raw_value: str
    numeric_value: float | None
    negative_zero: bool
    period_semantics: str
    unit_status: str = "UNKNOWN"
    scope_status: str = "UNKNOWN"
    authority: str = REFERENCE_AUTHORITY
    can_map_pdf: bool = False
    can_promote_pdf: bool = False

    def sql_values(self, archive_sha256: str) -> tuple[object, ...]:
        return (
            self.stock_id,
            self.source_document_id,
            self.source_collection,
            self.source_term_type,
            self.normalized_term_type,
            self.norm_term,
            self.calendar_year,
            self.calendar_quarter,
            self.source_index,
            self.source_feature,
            self.series_kind,
            self.report_norm_id,
            self.statement_type,
            self.schema_order,
            self.canonical_name,
            self.value_state,
            self.raw_value,
            self.numeric_value,
            self.negative_zero,
            self.period_semantics,
            self.unit_status,
            self.scope_status,
            self.authority,
            self.can_map_pdf,
            self.can_promote_pdf,
            archive_sha256,
        )


@dataclass(frozen=True)
class DocumentExtraction:
    cells: tuple[HistoricalReferenceCell, ...]
    mapped_raw_ids: tuple[int, ...]
    mapped_ytd_ids: tuple[int, ...]
    unknown_numeric_features: tuple[int, ...]
    unknown_ytd_features: tuple[str, ...]
    excluded_named_features: tuple[str, ...]
    source_contains_proposed_id: bool


@dataclass(frozen=True)
class HistoricalReferenceMatch:
    stock_id: str
    report_norm_id: int
    norm_term: str
    source_feature: str
    series_kind: str
    statement_type: str
    canonical_name: str
    period_semantics: str
    unit_status: str
    scope_status: str
    value_state: str
    raw_value: str
    numeric_value: float | None
    negative_zero: bool
    source_document_id: str
    authority: str
    can_map_pdf: bool
    can_promote_pdf: bool


def _parse_term(source_term_type: str, norm_term: object) -> tuple[str, int, int | None, str]:
    if not isinstance(norm_term, str):
        raise ValueError(f"historical NormTerm must be text, got {type(norm_term).__name__}")
    if source_term_type == "yearly":
        match = _YEARLY_TERM.fullmatch(norm_term)
        if match is None:
            raise ValueError(f"invalid yearly NormTerm: {norm_term!r}")
        return "ANNUAL", int(match.group("year")), None, "UPSTREAM_ANNUAL_UNVERIFIED"
    if source_term_type == "quaterly":
        match = _QUARTERLY_TERM.fullmatch(norm_term)
        if match is None:
            raise ValueError(f"invalid quarterly NormTerm: {norm_term!r}")
        return (
            "QUARTERLY",
            int(match.group("year")),
            int(match.group("quarter")),
            "UPSTREAM_QUARTER_UNVERIFIED",
        )
    raise ValueError(f"unsupported historical term_type: {source_term_type!r}")


def _classify_value(value: object) -> tuple[HistoricalValueState, str, float | None, bool]:
    if value is None:
        return HistoricalValueState.NULL, "null", None, False
    if isinstance(value, bool):
        return HistoricalValueState.BOOLEAN, str(value).lower(), None, False
    if isinstance(value, int):
        state = HistoricalValueState.ZERO if value == 0 else HistoricalValueState.VALUE
        return state, str(value), float(value), False
    if isinstance(value, float):
        if math.isnan(value):
            return HistoricalValueState.NAN, "nan", None, False
        if math.isinf(value):
            state = (
                HistoricalValueState.POSITIVE_INFINITY
                if value > 0
                else HistoricalValueState.NEGATIVE_INFINITY
            )
            return state, repr(value), None, False
        negative_zero = value == 0 and math.copysign(1.0, value) < 0
        state = HistoricalValueState.ZERO if value == 0 else HistoricalValueState.VALUE
        return state, repr(value), value, negative_zero
    if isinstance(value, str):
        return HistoricalValueState.TEXT, value, None, False
    return HistoricalValueState.INVALID_TYPE, repr(value), None, False


def _feature_descriptor(
    feature: str, schema_by_id: Mapping[int, SchemaItem]
) -> tuple[str, int, SchemaItem] | None:
    if feature.isdigit():
        report_norm_id = int(feature)
        item = schema_by_id.get(report_norm_id)
        return (RAW_SERIES, report_norm_id, item) if item is not None else None
    match = _YTD_FEATURE.fullmatch(feature)
    if match is None:
        return None
    report_norm_id = int(match.group("report_norm_id"))
    item = schema_by_id.get(report_norm_id)
    return (YTD_SERIES, report_norm_id, item) if item is not None else None


def extract_historical_document(
    document: Mapping[str, object],
    schema_by_id: Mapping[int, SchemaItem],
    *,
    proposed_id: int = 1944,
) -> DocumentExtraction:
    if document.get("stock_industry") != "bank":
        raise ValueError("historical document is outside the bank allowlist")
    stock_id = str(document.get("stock_id", "")).strip().upper()
    if not stock_id:
        raise ValueError("historical document has no stock_id")
    source_document_id = str(document.get("_id", ""))
    if not source_document_id:
        raise ValueError(f"historical document {stock_id} has no _id")
    source_term_type = str(document.get("term_type", ""))
    data = document.get("data")
    if not isinstance(data, Mapping):
        raise ValueError(f"historical document {stock_id}/{source_term_type} data is not an object")
    norm_terms = data.get("NormTerm")
    if not isinstance(norm_terms, list) or not norm_terms:
        raise ValueError(f"historical document {stock_id}/{source_term_type} has no NormTerm list")
    if len({str(term) for term in norm_terms}) != len(norm_terms):
        raise ValueError(f"historical document {stock_id}/{source_term_type} repeats NormTerm")
    for feature, values in data.items():
        if not isinstance(feature, str) or not isinstance(values, list):
            raise ValueError(
                f"historical series {stock_id}/{source_term_type}/{feature!r} is not a list"
            )
        if len(values) != len(norm_terms):
            raise ValueError(
                f"historical series {stock_id}/{source_term_type}/{feature} length "
                f"{len(values)} does not match NormTerm length {len(norm_terms)}"
            )

    parsed_terms = [_parse_term(source_term_type, term) for term in norm_terms]
    unknown_numeric: set[int] = set()
    unknown_ytd: set[str] = set()
    excluded_named: set[str] = set()
    descriptors: list[tuple[str, str, int, SchemaItem]] = []
    for feature in data:
        if feature in {"NormTerm", "Q", "Y", "Stock_ID"}:
            continue
        descriptor = _feature_descriptor(feature, schema_by_id)
        if descriptor is not None:
            series_kind, report_norm_id, item = descriptor
            descriptors.append((feature, series_kind, report_norm_id, item))
        elif feature.isdigit():
            unknown_numeric.add(int(feature))
        elif _YTD_FEATURE.fullmatch(feature):
            unknown_ytd.add(feature)
        else:
            excluded_named.add(feature)
    descriptors.sort(key=lambda row: (row[1], row[3].statement_type, row[3].display_order, row[0]))

    cells: list[HistoricalReferenceCell] = []
    for feature, series_kind, report_norm_id, item in descriptors:
        for index, (norm_term, parsed) in enumerate(zip(norm_terms, parsed_terms, strict=True)):
            normalized_term_type, year, quarter, raw_period_semantics = parsed
            period_semantics = (
                "UPSTREAM_DERIVED_YTD_UNVERIFIED"
                if series_kind == YTD_SERIES
                else raw_period_semantics
            )
            state, raw_value, numeric_value, negative_zero = _classify_value(data[feature][index])
            cells.append(
                HistoricalReferenceCell(
                    stock_id=stock_id,
                    source_document_id=source_document_id,
                    source_collection=SOURCE_COLLECTION,
                    source_term_type=source_term_type,
                    normalized_term_type=normalized_term_type,
                    norm_term=str(norm_term),
                    calendar_year=year,
                    calendar_quarter=quarter,
                    source_index=index,
                    source_feature=feature,
                    series_kind=series_kind,
                    report_norm_id=report_norm_id,
                    statement_type=item.statement_type,
                    schema_order=item.display_order,
                    canonical_name=item.canonical_name,
                    value_state=state.value,
                    raw_value=raw_value,
                    numeric_value=numeric_value,
                    negative_zero=negative_zero,
                    period_semantics=period_semantics,
                )
            )
    return DocumentExtraction(
        cells=tuple(cells),
        mapped_raw_ids=tuple(
            sorted(
                {report_norm_id for _, kind, report_norm_id, _ in descriptors if kind == RAW_SERIES}
            )
        ),
        mapped_ytd_ids=tuple(
            sorted(
                {report_norm_id for _, kind, report_norm_id, _ in descriptors if kind == YTD_SERIES}
            )
        ),
        unknown_numeric_features=tuple(sorted(unknown_numeric)),
        unknown_ytd_features=tuple(sorted(unknown_ytd)),
        excluded_named_features=tuple(sorted(excluded_named)),
        source_contains_proposed_id=(str(proposed_id) in data or f"YTD_{proposed_id}" in data),
    )


_CREATE_SQL = """
CREATE TABLE build_metadata (
    key VARCHAR PRIMARY KEY,
    value_json VARCHAR NOT NULL
);
CREATE TABLE weak_reference_cells (
    stock_id VARCHAR NOT NULL,
    source_document_id VARCHAR NOT NULL,
    source_collection VARCHAR NOT NULL,
    source_term_type VARCHAR NOT NULL,
    normalized_term_type VARCHAR NOT NULL,
    norm_term VARCHAR NOT NULL,
    calendar_year INTEGER NOT NULL,
    calendar_quarter INTEGER,
    source_index INTEGER NOT NULL,
    source_feature VARCHAR NOT NULL,
    series_kind VARCHAR NOT NULL,
    report_norm_id INTEGER NOT NULL,
    statement_type VARCHAR NOT NULL,
    schema_order INTEGER NOT NULL,
    canonical_name VARCHAR NOT NULL,
    value_state VARCHAR NOT NULL,
    raw_value VARCHAR NOT NULL,
    numeric_value DOUBLE,
    negative_zero BOOLEAN NOT NULL,
    period_semantics VARCHAR NOT NULL,
    unit_status VARCHAR NOT NULL CHECK (unit_status = 'UNKNOWN'),
    scope_status VARCHAR NOT NULL CHECK (scope_status = 'UNKNOWN'),
    authority VARCHAR NOT NULL CHECK (authority = 'HISTORICAL_WEAK_REFERENCE_ONLY'),
    can_map_pdf BOOLEAN NOT NULL CHECK (can_map_pdf = false),
    can_promote_pdf BOOLEAN NOT NULL CHECK (can_promote_pdf = false),
    source_archive_sha256 VARCHAR NOT NULL
);
"""


def write_historical_reference_database(
    output_path: Path,
    cells: Sequence[HistoricalReferenceCell],
    *,
    archive_sha256: str,
    metadata: Mapping[str, object],
    replace: bool = False,
) -> dict[str, object]:
    started_at = time.perf_counter()
    output_path = output_path.resolve()
    if not cells:
        raise ValueError("historical reference has no cells")
    if output_path.exists() and not replace:
        raise FileExistsError(f"historical reference already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".duckdb", dir=output_path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    bulk_descriptor, bulk_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".csv", dir=output_path.parent
    )
    bulk_path = Path(bulk_name)
    connection: duckdb.DuckDBPyConnection | None = None
    try:
        with os.fdopen(bulk_descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            for cell in cells:
                writer.writerow(
                    [
                        _CSV_NULL
                        if value is None
                        else str(value).lower()
                        if isinstance(value, bool)
                        else value
                        for value in cell.sql_values(archive_sha256)
                    ]
                )
            stream.flush()
            os.fsync(stream.fileno())
        connection = duckdb.connect(str(temporary))
        connection.execute(_CREATE_SQL)
        connection.execute("BEGIN TRANSACTION")
        try:
            metadata_rows = [
                (key, json.dumps(value, ensure_ascii=False, sort_keys=True))
                for key, value in sorted(metadata.items())
            ]
            if metadata_rows:
                connection.executemany("INSERT INTO build_metadata VALUES (?, ?)", metadata_rows)
            escaped_bulk_path = str(bulk_path).replace("'", "''")
            connection.execute(
                f"COPY weak_reference_cells FROM '{escaped_bulk_path}' "
                f"(FORMAT CSV, HEADER false, NULL '{_CSV_NULL}')"
            )
        except Exception:
            connection.execute("ROLLBACK")
            raise
        else:
            connection.execute("COMMIT")
        connection.execute(
            "CREATE UNIQUE INDEX weak_reference_identity ON weak_reference_cells "
            "(stock_id, source_term_type, norm_term, source_feature)"
        )
        connection.execute(
            "CREATE INDEX weak_reference_lookup ON weak_reference_cells "
            "(stock_id, report_norm_id, norm_term, series_kind)"
        )
        actual_count = connection.execute("SELECT count(*) FROM weak_reference_cells").fetchone()[0]
        forbidden = connection.execute(
            "SELECT count(*) FROM weak_reference_cells WHERE can_map_pdf OR can_promote_pdf"
        ).fetchone()[0]
        if actual_count != len(cells) or forbidden:
            raise RuntimeError("historical reference database failed acceptance checks")
        connection.execute("CHECKPOINT")
        connection.close()
        connection = None
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, output_path)
        directory_fd = os.open(output_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)
        temporary.with_suffix(temporary.suffix + ".wal").unlink(missing_ok=True)
        bulk_path.unlink(missing_ok=True)
    return {
        "path": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
        "row_count": len(cells),
        "write_elapsed_seconds": round(time.perf_counter() - started_at, 6),
        "bulk_load_method": "DUCKDB_COPY_CSV_SINGLE_TRANSACTION",
    }


def historical_documents_hash(documents: Sequence[Mapping[str, object]]) -> str:
    digest = hashlib.sha256()
    for document in documents:
        payload = BSON.encode(dict(document))
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


def build_historical_weak_reference(
    project_root: Path,
    *,
    mongo_uri: str,
    output_path: Path,
    registry_path: Path,
    replace: bool = False,
    proposed_id: int = 1944,
) -> dict[str, object]:
    project_root = project_root.resolve()
    output_path = output_path if output_path.is_absolute() else project_root / output_path
    registry_path = registry_path if registry_path.is_absolute() else project_root / registry_path
    archive_registry_path = project_root / "data/registered/mongodb_dump_registry.json"
    policy_path = project_root / "config/reference/historical-weak-reference.yaml"
    policy = load_historical_reference_policy(policy_path)
    archive_registry = json.loads(archive_registry_path.read_text(encoding="utf-8"))
    archive_record = archive_registry["archive"]
    archive_path = project_root / archive_record["path"]
    if sha256_file(archive_path) != archive_record["sha256"]:
        raise ValueError("MongoDB archive hash does not match its registered identity")

    bank_registry_path = project_root / "data/registered/bank_registry.json"
    bank_registry = json.loads(bank_registry_path.read_text(encoding="utf-8"))
    bank_source = project_root / bank_registry["source"]
    if sha256_file(bank_source) != bank_registry["source_sha256"]:
        raise ValueError("bank registry source hash has changed")
    bank_codes = sorted(
        entity["code"] for entity in bank_registry["entities"] if entity["category"] == "BANK"
    )
    _, schema = load_all(project_root / "template", project_root)
    schema_by_id = {item.schema_id: item for item in schema}

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        database_name = archive_record["header"]["database"]
        collection = client[database_name][SOURCE_COLLECTION]
        all_bank_documents = list(
            collection.find({"stock_industry": "bank"}).sort(
                [("stock_id", 1), ("term_type", 1), ("_id", 1)]
            )
        )
        total_collection_documents = collection.count_documents({})
    finally:
        client.close()
    if not all_bank_documents:
        raise ValueError(f"{SOURCE_COLLECTION} has no bank documents")
    unexpected_bank_codes = sorted(
        {str(document.get("stock_id", "")).strip().upper() for document in all_bank_documents}
        - set(bank_codes)
    )
    selected_documents = [
        document
        for document in all_bank_documents
        if str(document.get("stock_id", "")).strip().upper() in bank_codes
    ]
    pairs = [
        (str(document.get("stock_id", "")).strip().upper(), str(document.get("term_type", "")))
        for document in selected_documents
    ]
    duplicate_pairs = sorted(pair for pair, count in Counter(pairs).items() if count > 1)
    if duplicate_pairs:
        raise ValueError(f"duplicate bank/term documents in {SOURCE_COLLECTION}: {duplicate_pairs}")

    cells: list[HistoricalReferenceCell] = []
    raw_ids: set[int] = set()
    ytd_ids: set[int] = set()
    unknown_numeric: set[int] = set()
    unknown_ytd: set[str] = set()
    excluded_named: set[str] = set()
    source_contains_proposed_id = False
    for document in selected_documents:
        extracted = extract_historical_document(document, schema_by_id, proposed_id=proposed_id)
        cells.extend(extracted.cells)
        raw_ids.update(extracted.mapped_raw_ids)
        ytd_ids.update(extracted.mapped_ytd_ids)
        unknown_numeric.update(extracted.unknown_numeric_features)
        unknown_ytd.update(extracted.unknown_ytd_features)
        excluded_named.update(extracted.excluded_named_features)
        source_contains_proposed_id |= extracted.source_contains_proposed_id
    cells.sort(
        key=lambda cell: (
            cell.stock_id,
            cell.normalized_term_type,
            cell.norm_term,
            cell.series_kind,
            cell.statement_type,
            cell.schema_order,
            cell.source_feature,
        )
    )
    expected_pairs = {(code, term) for code in bank_codes for term in ("yearly", "quaterly")}
    missing_pairs = sorted(expected_pairs - set(pairs))
    record_hash = stable_records_hash(
        json.dumps(asdict(cell), ensure_ascii=False, sort_keys=True) for cell in cells
    )
    metadata = {
        "format_version": 1,
        "authority": REFERENCE_AUTHORITY,
        "source_archive_sha256": archive_record["sha256"],
        "source_collection": SOURCE_COLLECTION,
        "selected_documents_sha256": historical_documents_hash(selected_documents),
        "cell_records_sha256": record_hash,
        "mapping_candidate_generation_allowed": False,
        "pdf_confidence_promotion_allowed": False,
    }
    database = write_historical_reference_database(
        output_path,
        cells,
        archive_sha256=archive_record["sha256"],
        metadata=metadata,
        replace=replace,
    )
    database["path"] = _relative_or_absolute(output_path.resolve(), project_root)
    manifest = {
        "format_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASS_WEAK_REFERENCE_ONLY",
        "authority": REFERENCE_AUTHORITY,
        "source": {
            "archive": archive_record,
            "collection": SOURCE_COLLECTION,
            "collection_document_count": total_collection_documents,
            "bank_document_count": len(all_bank_documents),
            "selected_document_count": len(selected_documents),
            "selected_documents_sha256": metadata["selected_documents_sha256"],
            "mongo_uri_persisted": False,
        },
        "scope": {
            "registered_bank_count": len(bank_codes),
            "registered_bank_codes": bank_codes,
            "unexpected_bank_codes": unexpected_bank_codes,
            "missing_bank_term_pairs": [list(pair) for pair in missing_pairs],
            "cell_count_by_source_term_type": dict(
                Counter(cell.source_term_type for cell in cells)
            ),
        },
        "schema": {
            "registered_item_count": len(schema),
            "schema_graph_sha256": sha256_file(
                project_root / "reference/schemas/schema_graph.jsonl"
            ),
            "mapped_raw_report_norm_ids": sorted(raw_ids),
            "mapped_ytd_report_norm_ids": sorted(ytd_ids),
            "unknown_numeric_features_excluded": sorted(unknown_numeric),
            "unknown_ytd_features_excluded": sorted(unknown_ytd),
            "named_or_formula_features_excluded": sorted(excluded_named),
            "proposed_id": proposed_id,
            "source_contains_proposed_id": source_contains_proposed_id,
            "append_safe_from_historical_key_collision_perspective": (
                not source_contains_proposed_id
            ),
            "semantic_or_parent_approval_still_required": True,
        },
        "cells": {
            "count": len(cells),
            "records_sha256": record_hash,
            "by_series_kind": dict(Counter(cell.series_kind for cell in cells)),
            "by_statement_type": dict(Counter(cell.statement_type for cell in cells)),
            "by_value_state": dict(Counter(cell.value_state for cell in cells)),
            "unique_report_norm_id_count": len({cell.report_norm_id for cell in cells}),
        },
        "database": database,
        "safety_contract": {
            **policy["safety"],
        },
        "implementation": {
            "module": "src/bctc_ai/reference/historical.py",
            "module_sha256": sha256_file(Path(__file__)),
            "policy": "config/reference/historical-weak-reference.yaml",
            "policy_sha256": sha256_file(policy_path),
            "duckdb_version": duckdb.__version__,
        },
    }
    atomic_write_json(registry_path, manifest)
    return manifest


def verify_historical_weak_reference(
    project_root: Path,
    registry_path: Path | None = None,
) -> dict[str, object]:
    """Verify the local index and its non-authoritative gates without contacting MongoDB."""

    project_root = project_root.resolve()
    registry_path = registry_path or (
        project_root / "data/registered/historical_weak_reference_registry.json"
    )
    registry_path = registry_path.resolve()
    relative_registry = _relative_or_absolute(registry_path, project_root)
    if not registry_path.is_file():
        return {
            "status": "NOT_CONFIGURED",
            "registry": relative_registry,
            "database_present": False,
            "checks": {},
        }
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        database_record = registry["database"]
        database_path = Path(database_record["path"])
        if not database_path.is_absolute():
            database_path = project_root / database_path
        database_path = database_path.resolve()
        base_result: dict[str, object] = {
            "registry": relative_registry,
            "registry_sha256": sha256_file(registry_path),
            "database": _relative_or_absolute(database_path, project_root),
            "database_present": database_path.is_file(),
            "declared_status": registry.get("status"),
        }
        if not database_path.is_file():
            return {**base_result, "status": "ABSENT_REBUILD_REQUIRED", "checks": {}}

        implementation = registry["implementation"]
        module_path = project_root / implementation["module"]
        policy_path = project_root / implementation["policy"]
        archive_registry_path = project_root / "data/registered/mongodb_dump_registry.json"
        archive_registry = json.loads(archive_registry_path.read_text(encoding="utf-8"))
        safety = registry["safety_contract"]
        checks = {
            "declared_weak_status": registry.get("status") == "PASS_WEAK_REFERENCE_ONLY",
            "database_sha256": sha256_file(database_path) == database_record["sha256"],
            "module_sha256": (
                module_path.is_file()
                and sha256_file(module_path) == implementation["module_sha256"]
            ),
            "policy_sha256": (
                policy_path.is_file()
                and sha256_file(policy_path) == implementation["policy_sha256"]
            ),
            "archive_identity": (
                registry["source"]["archive"]["sha256"] == archive_registry["archive"]["sha256"]
            ),
            "historical_1944_collision_clear": (
                registry["schema"]["append_safe_from_historical_key_collision_perspective"]
                and not registry["schema"]["source_contains_proposed_id"]
            ),
            "mapping_candidate_generation_forbidden": (
                safety["mapping_candidate_generation_allowed"] is False
            ),
            "pdf_confidence_promotion_forbidden": (
                safety["pdf_confidence_promotion_allowed"] is False
            ),
            "pdf_value_overwrite_forbidden": (safety["pdf_value_overwrite_allowed"] is False),
            "upstream_ytd_operand_forbidden": (
                safety["upstream_ytd_can_supply_pdf_derivation_operand"] is False
            ),
            "lookup_requires_resolved_id": (
                safety["lookup_requires_resolved_report_norm_id"] is True
            ),
            "unit_and_scope_unknown": (
                safety["unit"] == "UNKNOWN" and safety["scope"] == "UNKNOWN"
            ),
        }
        if not checks["database_sha256"]:
            return {**base_result, "status": "FAIL", "checks": checks}

        connection = duckdb.connect(str(database_path), read_only=True)
        try:
            row_count = connection.execute("SELECT count(*) FROM weak_reference_cells").fetchone()[
                0
            ]
            forbidden_count = connection.execute(
                "SELECT count(*) FROM weak_reference_cells WHERE can_map_pdf OR can_promote_pdf"
            ).fetchone()[0]
            duplicate_count = connection.execute(
                """
                SELECT count(*) FROM (
                    SELECT stock_id, source_term_type, norm_term, source_feature
                    FROM weak_reference_cells GROUP BY ALL HAVING count(*) > 1
                )
                """
            ).fetchone()[0]
            bank_count = connection.execute(
                "SELECT count(DISTINCT stock_id) FROM weak_reference_cells"
            ).fetchone()[0]
            collision_count = connection.execute(
                "SELECT count(*) FROM weak_reference_cells WHERE report_norm_id = ?",
                [registry["schema"]["proposed_id"]],
            ).fetchone()[0]
        finally:
            connection.close()
        checks.update(
            row_count_matches=row_count == registry["cells"]["count"],
            forbidden_row_count_zero=forbidden_count == 0,
            duplicate_identity_count_zero=duplicate_count == 0,
            registered_bank_count_matches=(
                bank_count == registry["scope"]["registered_bank_count"]
            ),
            proposed_id_row_count_zero=collision_count == 0,
        )
        return {
            **base_result,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "row_count": row_count,
            "bank_count": bank_count,
            "forbidden_row_count": forbidden_count,
            "duplicate_identity_count": duplicate_count,
        }
    except Exception as error:
        return {
            "status": "FAIL",
            "registry": relative_registry,
            "database_present": False,
            "checks": {},
            "error": str(error),
        }


def lookup_resolved_historical_reference(
    database_path: Path,
    *,
    stock_id: str,
    report_norm_id: int,
    norm_term: str,
    include_upstream_ytd: bool = False,
) -> tuple[HistoricalReferenceMatch, ...]:
    """Look up only after mapping resolved an ID; labels and PDF values are not inputs."""

    connection = duckdb.connect(str(database_path.resolve()), read_only=True)
    try:
        forbidden = connection.execute(
            "SELECT count(*) FROM weak_reference_cells WHERE can_map_pdf OR can_promote_pdf"
        ).fetchone()[0]
        if forbidden:
            raise RuntimeError("historical reference violates its non-authoritative contract")
        series = [RAW_SERIES, YTD_SERIES] if include_upstream_ytd else [RAW_SERIES]
        placeholders = ", ".join("?" for _ in series)
        cursor = connection.execute(
            f"""
            SELECT stock_id, report_norm_id, norm_term, source_feature, series_kind,
                   statement_type, canonical_name, period_semantics, unit_status, scope_status,
                   value_state, raw_value, numeric_value, negative_zero, source_document_id,
                   authority, can_map_pdf, can_promote_pdf
            FROM weak_reference_cells
            WHERE stock_id = ? AND report_norm_id = ? AND norm_term = ?
              AND series_kind IN ({placeholders})
            ORDER BY CASE series_kind WHEN '{RAW_SERIES}' THEN 0 ELSE 1 END, source_feature
            """,
            [stock_id.strip().upper(), int(report_norm_id), norm_term, *series],
        )
        return tuple(HistoricalReferenceMatch(*row) for row in cursor.fetchall())
    finally:
        connection.close()
