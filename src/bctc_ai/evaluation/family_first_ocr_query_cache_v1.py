"""Fast, non-authoritative SQLite index over the verified all-filing OCR axes.

The formal semantic and numeric capabilities remain the source of authority.
This module materializes their already-persisted, content-addressed projections
once so family development can search and replay a bounded document without
deserializing hundreds of megabytes or replaying the complete trust chain.
Every cache records the exact upstream identities and is disposable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as numeric_v3
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as numeric_runner_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

__all__ = [
    "CACHE_FORMAT_VERSION",
    "FamilyFirstOcrQueryCacheV1Error",
    "build_family_first_ocr_query_cache_v1",
    "family_trial_reason_counts_v1",
    "project_family_first_ocr_query_cache_v1",
    "read_cached_blind_pages_v1",
    "read_cached_family_trials_v1",
    "read_cached_joined_pages_v1",
    "search_cached_ocr_lines_v1",
]


CACHE_FORMAT_VERSION = "FAMILY_FIRST_OCR_QUERY_CACHE_V1"
DEFAULT_DATABASE_PATH = Path("data/local/family_first_ocr_query_cache_v1.sqlite3")
_CACHE_AUTHORITY = {
    "accounting_authority": False,
    "cache_disposable_and_rebuildable": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "upstream_formal_replay_required_before_publication": True,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_VERSION = 1


class FamilyFirstOcrQueryCacheV1Error(RuntimeError):
    """The disposable cache inputs, schema, source order, or query drifted."""


def _error(message: str) -> FamilyFirstOcrQueryCacheV1Error:
    return FamilyFirstOcrQueryCacheV1Error(message)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"cannot read stable {label}") from exc

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"{label} changed while being read")
    return payload


def _strict_object(
    payload: bytes, label: str, *, allow_legacy_extra_newline: bool = False
) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    expected = canonical_json_bytes_v1(value)
    permitted = {expected, expected + b"\n"} if allow_legacy_extra_newline else {expected}
    if type(value) is not dict or payload not in permitted:
        raise _error(f"{label} is not one canonical JSON object")
    return value


def _reference(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] < 0
    ):
        raise _error(f"{label} content reference drifted")
    return dict(value)


def _referenced_object(root: Path, value: Any, label: str) -> dict[str, Any]:
    reference = _reference(value, label)
    payload = _stable_bytes(root / reference["path"], label)
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error(f"{label} differs from its content reference")
    return _strict_object(payload, label)


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA application_id = 1179665233;
        PRAGMA user_version = 1;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) STRICT, WITHOUT ROWID;
        CREATE TABLE documents (
            document_ordinal INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL UNIQUE,
            bank TEXT NOT NULL,
            year INTEGER NOT NULL,
            period TEXT NOT NULL,
            scope TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_size_bytes INTEGER NOT NULL,
            page_count INTEGER NOT NULL,
            line_count INTEGER NOT NULL
        ) STRICT;
        CREATE TABLE pages (
            document_ordinal INTEGER NOT NULL,
            physical_page INTEGER NOT NULL,
            line_count INTEGER NOT NULL,
            pixel_width INTEGER NOT NULL,
            pixel_height INTEGER NOT NULL,
            render_sha256 TEXT NOT NULL,
            render_size_bytes INTEGER NOT NULL,
            page_artifact_path TEXT NOT NULL,
            page_artifact_sha256 TEXT NOT NULL,
            page_artifact_size_bytes INTEGER NOT NULL,
            PRIMARY KEY (document_ordinal, physical_page),
            FOREIGN KEY (document_ordinal) REFERENCES documents(document_ordinal)
        ) STRICT, WITHOUT ROWID;
        CREATE TABLE lines (
            line_id INTEGER PRIMARY KEY,
            document_ordinal INTEGER NOT NULL,
            physical_page INTEGER NOT NULL,
            line_ordinal INTEGER NOT NULL,
            sample_id TEXT NOT NULL UNIQUE,
            bbox_left INTEGER NOT NULL,
            bbox_top INTEGER NOT NULL,
            bbox_right INTEGER NOT NULL,
            bbox_bottom INTEGER NOT NULL,
            crop_path TEXT NOT NULL,
            crop_sha256 TEXT NOT NULL,
            crop_size_bytes INTEGER NOT NULL,
            vietocr_text TEXT NOT NULL,
            vietocr_text_nfc TEXT NOT NULL,
            accentless_text TEXT NOT NULL,
            semantic_probability REAL,
            processed_width INTEGER NOT NULL,
            processed_height INTEGER NOT NULL,
            numeric_text TEXT NOT NULL,
            numeric_score REAL NOT NULL,
            UNIQUE (document_ordinal, physical_page, line_ordinal),
            FOREIGN KEY (document_ordinal, physical_page)
                REFERENCES pages(document_ordinal, physical_page)
        ) STRICT;
        CREATE INDEX lines_document_page_idx
            ON lines(document_ordinal, physical_page, line_ordinal);
        CREATE INDEX lines_accentless_exact_idx ON lines(accentless_text);
        CREATE VIRTUAL TABLE line_search USING fts5(
            vietocr_text,
            accentless_text,
            content='lines',
            content_rowid='line_id',
            tokenize='trigram'
        );
        CREATE TABLE family_trials (
            family_id TEXT NOT NULL,
            sweep_id TEXT NOT NULL,
            document_ordinal INTEGER NOT NULL,
            evidence_status TEXT NOT NULL,
            topology_status TEXT NOT NULL,
            candidate_pages_json TEXT NOT NULL,
            unresolved_reasons_json TEXT NOT NULL,
            trial_json TEXT NOT NULL,
            PRIMARY KEY (family_id, document_ordinal),
            FOREIGN KEY (document_ordinal) REFERENCES documents(document_ordinal)
        ) STRICT, WITHOUT ROWID;
        CREATE TABLE trial_reasons (
            family_id TEXT NOT NULL,
            document_ordinal INTEGER NOT NULL,
            reason TEXT NOT NULL,
            PRIMARY KEY (family_id, document_ordinal, reason),
            FOREIGN KEY (family_id, document_ordinal)
                REFERENCES family_trials(family_id, document_ordinal)
        ) STRICT, WITHOUT ROWID;
        CREATE INDEX trial_reason_idx ON trial_reasons(family_id, reason);
        """
    )


def _page_metadata(root: Path, document_ordinal: int, page_count: int) -> list[tuple[Any, ...]]:
    document_path = (
        root
        / "output/calibration/family-first-semantic-label-cache-v1/documents"
        / f"document-{document_ordinal:04d}/document.json"
    )
    document = _strict_object(
        _stable_bytes(document_path, "semantic detector document artifact"),
        "semantic detector document artifact",
        allow_legacy_extra_newline=True,
    )
    refs = document.get("page_artifact_refs")
    if (
        document.get("document_ordinal") != document_ordinal
        or type(refs) is not list
        or len(refs) != page_count
    ):
        raise _error("semantic detector document/page denominator drifted")
    result = []
    for physical_page, raw_reference in enumerate(refs, 1):
        reference = _reference(raw_reference, "semantic detector page artifact")
        page_payload = _stable_bytes(root / reference["path"], "semantic detector page artifact")
        if (
            len(page_payload) != reference["size_bytes"]
            or hashlib.sha256(page_payload).hexdigest() != reference["sha256"]
        ):
            raise _error("semantic detector page artifact differs from its content reference")
        page = _strict_object(
            page_payload,
            "semantic detector page artifact",
            allow_legacy_extra_newline=True,
        )
        freeze = page.get("page_freeze")
        render = freeze.get("render_ref") if type(freeze) is dict else None
        crops = freeze.get("crops") if type(freeze) is dict else None
        if (
            page.get("document_ordinal") != document_ordinal
            or page.get("physical_page") != physical_page
            or type(render) is not dict
            or set(render) != {"pixel_height", "pixel_width", "sha256", "size_bytes"}
            or type(render["pixel_width"]) is not int
            or type(render["pixel_height"]) is not int
            or render["pixel_width"] <= 0
            or render["pixel_height"] <= 0
            or type(crops) is not list
        ):
            raise _error("semantic detector page/render metadata drifted")
        result.append(
            (
                document_ordinal,
                physical_page,
                len(crops),
                render["pixel_width"],
                render["pixel_height"],
                render["sha256"],
                render["size_bytes"],
                reference["path"],
                reference["sha256"],
                reference["size_bytes"],
            )
        )
    return result


def _numeric_line(stream: Any, ordinal: int, digest: Any) -> dict[str, Any]:
    line = stream.readline()
    if not line or not line.endswith(b"\n"):
        raise _error("numeric proposal JSONL ended before the semantic axis")
    digest.update(line)
    try:
        raw = json.loads(line.decode("utf-8", errors="strict"))
        value = numeric_runner_v1._validate_result(raw, ordinal)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        raise _error("numeric proposal JSONL record drifted") from exc
    if line != canonical_json_bytes_v1(value):
        raise _error("numeric proposal JSONL record is not canonical")
    return value


def _trial_rows(
    root: Path, paths: Sequence[Path]
) -> tuple[list[tuple[Any, ...]], list[tuple[str, int, str]], list[dict[str, Any]]]:
    trials: list[tuple[Any, ...]] = []
    reasons: list[tuple[str, int, str]] = []
    references = []
    for relative in paths:
        payload = _stable_bytes(root / relative, "family evidence sweep")
        value = _strict_object(
            payload,
            "family evidence sweep",
            allow_legacy_extra_newline=True,
        )
        family_id = value.get("family_id")
        sweep_id = value.get("sweep_id")
        raw_trials = value.get("trials")
        if type(family_id) is not str or type(sweep_id) is not str or type(raw_trials) is not list:
            raise _error("family evidence sweep identity/trials drifted")
        references.append(
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "sweep_id": sweep_id,
            }
        )
        for trial in raw_trials:
            document_ordinal = trial.get("document_ordinal") if type(trial) is dict else None
            topology = trial.get("topology_scan") if type(trial) is dict else None
            regions = topology.get("regions") if type(topology) is dict else None
            unresolved = trial.get("unresolved_reasons") if type(trial) is dict else None
            if (
                type(document_ordinal) is not int
                or type(regions) is not list
                or type(unresolved) is not list
                or any(type(reason) is not str for reason in unresolved)
            ):
                raise _error("family evidence trial shape drifted")
            pages = sorted(
                {
                    region["page_sequence"]
                    for region in regions
                    if type(region) is dict and type(region.get("page_sequence")) is int
                }
            )
            trials.append(
                (
                    family_id,
                    sweep_id,
                    document_ordinal,
                    trial["evidence_status"],
                    topology["status"],
                    _json_text(pages),
                    _json_text(unresolved),
                    _json_text(trial),
                )
            )
            reasons.extend((family_id, document_ordinal, reason) for reason in unresolved)
    return trials, reasons, references


def build_family_first_ocr_query_cache_v1(
    project_root: Path,
    database_path: Path = DEFAULT_DATABASE_PATH,
    *,
    evidence_sweep_paths: Sequence[Path] = (),
) -> dict[str, Any]:
    """Build one disposable SQLite cache from fixed verified-index artifacts."""

    started = time.perf_counter()
    root = project_root.resolve()
    destination = database_path if database_path.is_absolute() else root / database_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise _error("fixed OCR query cache already exists")
    manifest_payload = _stable_bytes(root / semantic_v1.MANIFEST_PATH, "semantic index manifest")
    manifest = semantic_v1._validate_manifest(
        _strict_object(manifest_payload, "semantic index manifest")
    )
    receipt_payload = _stable_bytes(root / numeric_v3.RECEIPT_PATH, "numeric index receipt")
    receipt = numeric_v3._validate_receipt(_strict_object(receipt_payload, "numeric index receipt"))
    if (
        receipt["batch_id"] != manifest["batch_id"]
        or receipt["plan_id"] != manifest["plan_id"]
        or receipt["metrics"]["document_count"] != manifest["metrics"]["document_count"]
        or receipt["metrics"]["page_count"] != manifest["metrics"]["page_count"]
        or receipt["metrics"]["sample_count"] != manifest["metrics"]["sample_count"]
    ):
        raise _error("semantic and numeric verified-index denominators differ")
    proposal_ref = _reference(receipt["proposal_ref"], "numeric proposal axis")
    proposal_path = root / proposal_ref["path"]
    proposal_before = proposal_path.lstat()
    if proposal_path.is_symlink() or not stat.S_ISREG(proposal_before.st_mode):
        raise _error("numeric proposal axis is not one regular nofollow file")

    stage_fd, stage_name = tempfile.mkstemp(
        prefix=".family-first-ocr-cache-", dir=destination.parent
    )
    os.close(stage_fd)
    stage = Path(stage_name)
    try:
        connection = sqlite3.connect(stage)
        try:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute("PRAGMA temp_store=MEMORY")
            connection.execute("PRAGMA foreign_keys=ON")
            _create_schema(connection)
            sample_ordinal = 0
            proposal_digest = hashlib.sha256()
            with proposal_path.open("rb") as numeric_stream:
                for expected_document in manifest["documents"]:
                    document = _referenced_object(
                        root,
                        expected_document["content_ref"],
                        "semantic verified document",
                    )
                    document = semantic_v1._validate_document(
                        document,
                        {
                            "document_ordinal": expected_document["document_ordinal"],
                            "page_count": expected_document["page_count"],
                            "private_provenance": document.get("private_provenance"),
                            "source_pdf_ref": document.get("source_pdf_ref"),
                        },
                    )
                    if document["line_count"] != expected_document["line_count"]:
                        raise _error("semantic manifest/document line denominator drifted")
                    provenance = document["private_provenance"]
                    source = _reference(document["source_pdf_ref"], "source PDF")
                    connection.execute(
                        """
                        INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            document["document_ordinal"],
                            document["document_id"],
                            provenance["bank"],
                            provenance["year"],
                            provenance["period"],
                            provenance["scope"],
                            source["path"],
                            source["sha256"],
                            source["size_bytes"],
                            document["page_count"],
                            document["line_count"],
                        ),
                    )
                    page_rows = _page_metadata(
                        root, document["document_ordinal"], document["page_count"]
                    )
                    if [item[2] for item in page_rows] != [
                        page["line_count"] for page in document["pages"]
                    ]:
                        raise _error("semantic page and detector page line denominators differ")
                    connection.executemany(
                        "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        page_rows,
                    )
                    line_rows = []
                    for page in document["pages"]:
                        for semantic_line in page["lines"]:
                            sample_ordinal += 1
                            numeric_line = _numeric_line(
                                numeric_stream, sample_ordinal, proposal_digest
                            )
                            crop = _reference(semantic_line["crop_ref"], "semantic crop")
                            bbox = semantic_line["source_bbox_raw_pixels"]
                            if (
                                numeric_line["sample_id"] != semantic_line["sample_id"]
                                or numeric_line["crop_sha256"] != crop["sha256"]
                                or type(bbox) is not list
                                or len(bbox) != 4
                                or any(type(item) is not int for item in bbox)
                            ):
                                raise _error("semantic/numeric/source sample axes differ")
                            line_rows.append(
                                (
                                    sample_ordinal,
                                    document["document_ordinal"],
                                    page["physical_page"],
                                    semantic_line["line_ordinal"],
                                    semantic_line["sample_id"],
                                    *bbox,
                                    crop["path"],
                                    crop["sha256"],
                                    crop["size_bytes"],
                                    semantic_line["vietocr_text"],
                                    semantic_line["vietocr_text_nfc"],
                                    semantic_line["accentless_text"],
                                    semantic_line["mean_decoded_character_probability"],
                                    semantic_line["processed_width"],
                                    semantic_line["processed_height"],
                                    numeric_line["raw_prediction"],
                                    numeric_line["reader_score"],
                                )
                            )
                    connection.executemany(
                        """
                        INSERT INTO lines VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                        """,
                        line_rows,
                    )
                if numeric_stream.read(1):
                    raise _error("numeric proposal axis retains trailing records")
            proposal_after = proposal_path.lstat()
            if (
                (
                    proposal_before.st_dev,
                    proposal_before.st_ino,
                    proposal_before.st_size,
                    proposal_before.st_mtime_ns,
                )
                != (
                    proposal_after.st_dev,
                    proposal_after.st_ino,
                    proposal_after.st_size,
                    proposal_after.st_mtime_ns,
                )
                or proposal_before.st_size != proposal_ref["size_bytes"]
                or proposal_digest.hexdigest() != proposal_ref["sha256"]
                or sample_ordinal != manifest["metrics"]["sample_count"]
            ):
                raise _error("numeric proposal axis changed or differs from its receipt")
            connection.execute(
                "INSERT INTO line_search(rowid, vietocr_text, accentless_text) "
                "SELECT line_id, vietocr_text, accentless_text FROM lines"
            )
            trials, reasons, evidence_refs = _trial_rows(root, evidence_sweep_paths)
            connection.executemany(
                "INSERT INTO family_trials VALUES (?, ?, ?, ?, ?, ?, ?, ?)", trials
            )
            connection.executemany("INSERT INTO trial_reasons VALUES (?, ?, ?)", reasons)
            sources = {
                "evidence_sweeps": evidence_refs,
                "numeric_receipt_id": receipt["receipt_id"],
                "numeric_axis_sha256": receipt["numeric_axis_sha256"],
                "semantic_index_id": manifest["index_id"],
            }
            material = {
                "authority": _CACHE_AUTHORITY,
                "document_count": manifest["metrics"]["document_count"],
                "format_version": CACHE_FORMAT_VERSION,
                "line_count": sample_ordinal,
                "page_count": manifest["metrics"]["page_count"],
                "schema_version": _SCHEMA_VERSION,
                "sources": sources,
            }
            cache_id = (
                "ffoqcv1:cache:" + hashlib.sha256(canonical_json_bytes_v1(material)).hexdigest()
            )
            metadata = {
                **material,
                "cache_id": cache_id,
            }
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                [(key, _json_text(value)) for key, value in metadata.items()],
            )
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise _error("completed OCR query cache failed SQLite integrity check")
        finally:
            connection.close()
        os.chmod(stage, 0o444)
        try:
            os.link(stage, destination)
        except FileExistsError as exc:
            raise _error("fixed OCR query cache appeared during publication") from exc
        stage.unlink()
    finally:
        if stage.exists():
            stage.unlink()
    return {
        "build_seconds": time.perf_counter() - started,
        "cache_id": cache_id,
        "database_path": os.fspath(destination),
        "document_count": manifest["metrics"]["document_count"],
        "line_count": sample_ordinal,
        "page_count": manifest["metrics"]["page_count"],
        "size_bytes": destination.stat().st_size,
    }


def _connect(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    format_row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'format_version'"
    ).fetchone()
    if (
        application_id != 1179665233
        or user_version != _SCHEMA_VERSION
        or format_row is None
        or json.loads(format_row[0]) != CACHE_FORMAT_VERSION
    ):
        connection.close()
        raise _error("OCR query cache schema/format identity drifted")
    return connection


def project_family_first_ocr_query_cache_v1(database_path: Path) -> dict[str, Any]:
    with _connect(database_path) as connection:
        metadata = {
            row["key"]: json.loads(row["value"])
            for row in connection.execute("SELECT key, value FROM metadata")
        }
        observed = {
            "document_count": connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "line_count": connection.execute("SELECT COUNT(*) FROM lines").fetchone()[0],
            "page_count": connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0],
        }
    if any(metadata.get(key) != value for key, value in observed.items()):
        raise _error("OCR query cache denominators differ from metadata")
    return {**metadata, "size_bytes": database_path.stat().st_size}


def _fts_phrase(value: str) -> str:
    if type(value) is not str or len(value.strip()) < 3:
        raise _error("OCR cache search fragment must contain at least three characters")
    return '"' + value.strip().replace('"', '""') + '"'


def search_cached_ocr_lines_v1(
    database_path: Path, accentless_fragment: str, *, limit: int = 1000
) -> list[dict[str, Any]]:
    if type(limit) is not int or not 1 <= limit <= 100_000:
        raise _error("OCR cache search limit drifted")
    query = _fts_phrase(accentless_fragment)
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT l.document_ordinal, d.bank, d.year, d.period, d.scope,
                   l.physical_page, l.line_ordinal, l.sample_id,
                   l.vietocr_text, l.accentless_text, l.numeric_text,
                   l.bbox_left, l.bbox_top, l.bbox_right, l.bbox_bottom
              FROM line_search s
              JOIN lines l ON l.line_id = s.rowid
              JOIN documents d ON d.document_ordinal = l.document_ordinal
             WHERE line_search MATCH ?
             ORDER BY l.document_ordinal, l.physical_page, l.line_ordinal
             LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _line_records(connection: sqlite3.Connection, document_ordinal: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT * FROM lines WHERE document_ordinal = ?
        ORDER BY physical_page, line_ordinal
        """,
        (document_ordinal,),
    ).fetchall()


def read_cached_blind_pages_v1(database_path: Path, document_ordinal: int) -> list[dict[str, Any]]:
    if type(document_ordinal) is not int or document_ordinal <= 0:
        raise _error("cached document ordinal drifted")
    with _connect(database_path) as connection:
        records = _line_records(connection, document_ordinal)
    if not records:
        raise _error("cached document is absent")
    pages: dict[int, list[dict[str, Any]]] = {}
    for row in records:
        pages.setdefault(row["physical_page"], []).append(
            {
                "bbox": [row["bbox_left"], row["bbox_top"], row["bbox_right"], row["bbox_bottom"]],
                "source_line_index": row["line_ordinal"],
                "source_text": None,
                "vietocr_text": row["vietocr_text"],
            }
        )
    return [{"lines": lines, "page_sequence": page} for page, lines in sorted(pages.items())]


def read_cached_joined_pages_v1(
    database_path: Path,
    document_ordinal: int,
    *,
    selected_pages: Iterable[int],
) -> list[dict[str, Any]]:
    selected = tuple(selected_pages)
    if (
        not selected
        or any(type(page) is not int or page <= 0 for page in selected)
        or len(selected) != len(set(selected))
    ):
        raise _error("cached selected-page axis drifted")
    with _connect(database_path) as connection:
        dimensions = {
            row["physical_page"]: row["pixel_width"]
            for row in connection.execute(
                "SELECT physical_page, pixel_width FROM pages WHERE document_ordinal = ?",
                (document_ordinal,),
            )
        }
        records = _line_records(connection, document_ordinal)
    if not records or any(page not in dimensions for page in selected):
        raise _error("cached document or selected page is absent")
    pages: dict[int, list[dict[str, Any]]] = {}
    for row in records:
        crop_ref = {
            "path": row["crop_path"],
            "sha256": row["crop_sha256"],
            "size_bytes": row["crop_size_bytes"],
        }
        pages.setdefault(row["physical_page"], []).append(
            {
                "bbox": [row["bbox_left"], row["bbox_top"], row["bbox_right"], row["bbox_bottom"]],
                "crop_ref": crop_ref,
                "line_ordinal": row["line_ordinal"],
                "numeric_recognition": {
                    "raw_prediction": row["numeric_text"],
                    "reader_score": row["numeric_score"],
                },
                "sample_id": row["sample_id"],
                "vietocr_text": row["vietocr_text"],
            }
        )
    return [
        {
            "lines": lines,
            "page_sequence": page,
            "page_width": dimensions[page] if page in selected else None,
        }
        for page, lines in sorted(pages.items())
    ]


def family_trial_reason_counts_v1(database_path: Path, family_id: str) -> list[dict[str, Any]]:
    if type(family_id) is not str or not family_id:
        raise _error("family trial query identifier drifted")
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT reason, COUNT(*) AS document_count
              FROM trial_reasons
             WHERE family_id = ?
             GROUP BY reason
             ORDER BY document_count DESC, reason
            """,
            (family_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def read_cached_family_trials_v1(
    database_path: Path,
    family_id: str,
    *,
    evidence_status: str | None = None,
) -> list[dict[str, Any]]:
    """Read persisted development trials without replaying formal OCR authority."""

    if type(family_id) is not str or not family_id:
        raise _error("family trial query identifier drifted")
    if evidence_status is not None and (type(evidence_status) is not str or not evidence_status):
        raise _error("family trial evidence-status filter drifted")
    sql = """
        SELECT trial_json FROM family_trials
         WHERE family_id = ?
    """
    parameters: tuple[Any, ...] = (family_id,)
    if evidence_status is not None:
        sql += " AND evidence_status = ?"
        parameters += (evidence_status,)
    sql += " ORDER BY document_ordinal"
    with _connect(database_path) as connection:
        rows = connection.execute(sql, parameters).fetchall()
    result = []
    for row in rows:
        try:
            trial = json.loads(row["trial_json"])
        except json.JSONDecodeError as exc:
            raise _error("cached family trial JSON drifted") from exc
        if type(trial) is not dict:
            raise _error("cached family trial is not one JSON object")
        result.append(trial)
    return result
