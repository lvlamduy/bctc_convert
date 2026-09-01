#!/usr/bin/env python3
"""Build one read-only exact-run manifest for the 27-bank review application."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

FORMAT_VERSION = "BCTC_FAMILY_REVIEW_RUN_MANIFEST_V1"
RUN_RECEIPT_FORMAT = "GEMINI_JSON_ALL_ACCOUNTING_FAMILIES_RUN_RECEIPT_V1"


class BuildFamilyReviewRunManifestError(RuntimeError):
    """A run, corpus source, or human-visible PDF binding is incomplete."""


def _error(message: str) -> BuildFamilyReviewRunManifestError:
    return BuildFamilyReviewRunManifestError(message)


def _file(value: str | Path, label: str) -> Path:
    unresolved = Path(value).expanduser()
    if unresolved.is_symlink() or not unresolved.is_file():
        raise _error(f"{label} is not a regular nonsymlink file")
    return unresolved.resolve()


def _directory(value: str | Path, label: str) -> Path:
    unresolved = Path(value).expanduser()
    if unresolved.is_symlink() or not unresolved.is_dir():
        raise _error(f"{label} is not a regular nonsymlink directory")
    return unresolved.resolve()


def _connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _pdf_path(root: Path, source_logical_name: str) -> Path:
    logical = Path(source_logical_name.replace("\\", "/"))
    if logical.parts and logical.parts[0] == "vietstock_bctc":
        logical = Path(*logical.parts[1:])
    candidate = root / logical
    if candidate.is_symlink() or not candidate.is_file():
        raise _error(f"PDF is absent under configured root: {source_logical_name}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise _error("PDF logical path escapes its configured root") from exc
    return resolved


def _run_documents(
    results_database: Path, family_id: str, family_run_id: str
) -> list[tuple[str, str]]:
    with _connection(results_database) as connection:
        run = connection.execute(
            """
            SELECT family_id, document_count
            FROM family_run
            WHERE family_run_id = ?
            """,
            (family_run_id,),
        ).fetchone()
        if run is None or run["family_id"] != family_id:
            raise _error("family run is absent or belongs to another family")
        rows = connection.execute(
            """
            SELECT source_sha256, source_logical_name
            FROM family_trial
            WHERE family_run_id = ?
            ORDER BY document_ordinal
            """,
            (family_run_id,),
        ).fetchall()
    documents = [(row["source_sha256"], row["source_logical_name"]) for row in rows]
    if len(documents) != run["document_count"] or len({item[0] for item in documents}) != len(
        documents
    ):
        raise _error("family run document frontier is incomplete or duplicated")
    return documents


def _assert_page_frontier(page_database: Path, documents: Iterable[tuple[str, str]]) -> None:
    expected = dict(documents)
    with _connection(page_database) as connection:
        for source_sha256, source_logical_name in expected.items():
            row = connection.execute(
                """
                SELECT source_logical_name
                FROM document
                WHERE source_sha256 = ?
                """,
                (source_sha256,),
            ).fetchone()
            if row is None or row["source_logical_name"] != source_logical_name:
                raise _error("family trial does not join its configured page store")


def _source_entry(
    *,
    family_id: str,
    family_run_id: str,
    results_database: Path,
    page_database: Path,
    pdf_root: Path,
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    documents = _run_documents(results_database, family_id, family_run_id)
    _assert_page_frontier(page_database, documents)
    for _source_sha256, source_logical_name in documents:
        _pdf_path(pdf_root, source_logical_name)
    return (
        {
            "family_id": family_id,
            "family_run_id": family_run_id,
            "page_database": str(page_database),
            "pdf_root": str(pdf_root),
            "results_database": str(results_database),
        },
        documents,
    )


def _current_runs(results_database: Path) -> list[tuple[str, str]]:
    with _connection(results_database) as connection:
        rows = connection.execute(
            """
            SELECT family_id, family_run_id
            FROM family_current_selection
            ORDER BY family_id
            """
        ).fetchall()
    if not rows:
        raise _error("current-selection source contains no selected family run")
    return [(row["family_id"], row["family_run_id"]) for row in rows]


def _receipt_runs(path: Path) -> list[tuple[str, str]]:
    try:
        receipt = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("all-family receipt is not valid JSON") from exc
    completed = receipt.get("completed") if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or receipt.get("format_version") != RUN_RECEIPT_FORMAT
        or receipt.get("disposition") != "SUCCEEDED"
        or receipt.get("deferred") != []
        or not isinstance(completed, list)
        or len(completed) != receipt.get("selected_family_count")
        or not completed
    ):
        raise _error("all-family receipt is incomplete")
    result: list[tuple[str, str]] = []
    for item in completed:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("family_id"), str)
            or not item["family_id"]
            or not isinstance(item.get("family_run_id"), str)
            or not item["family_run_id"]
        ):
            raise _error("all-family receipt contains an invalid run identity")
        result.append((item["family_id"], item["family_run_id"]))
    if len(set(result)) != len(result) or len({item[0] for item in result}) != len(result):
        raise _error("all-family receipt duplicates a family run")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--current-source",
        action="append",
        default=[],
        nargs=3,
        metavar=("RESULTS_DB", "PAGE_DB", "PDF_ROOT"),
    )
    parser.add_argument(
        "--receipt-source",
        action="append",
        default=[],
        nargs=4,
        metavar=("RUN_RECEIPT", "RESULTS_DB", "PAGE_DB", "PDF_ROOT"),
    )
    parser.add_argument(
        "--explicit-source",
        action="append",
        default=[],
        nargs=5,
        metavar=("FAMILY_ID", "FAMILY_RUN_ID", "RESULTS_DB", "PAGE_DB", "PDF_ROOT"),
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    requested: list[tuple[str, str, Path, Path, Path]] = []
    for results_value, pages_value, pdf_value in args.current_source:
        results = _file(results_value, "results database")
        pages = _file(pages_value, "page database")
        pdf_root = _directory(pdf_value, "PDF root")
        requested.extend(
            (family_id, family_run_id, results, pages, pdf_root)
            for family_id, family_run_id in _current_runs(results)
        )
    for receipt_value, results_value, pages_value, pdf_value in args.receipt_source:
        receipt = _file(receipt_value, "all-family receipt")
        results = _file(results_value, "results database")
        pages = _file(pages_value, "page database")
        pdf_root = _directory(pdf_value, "PDF root")
        requested.extend(
            (family_id, family_run_id, results, pages, pdf_root)
            for family_id, family_run_id in _receipt_runs(receipt)
        )
    for family_id, family_run_id, results_value, pages_value, pdf_value in args.explicit_source:
        requested.append(
            (
                family_id,
                family_run_id,
                _file(results_value, "results database"),
                _file(pages_value, "page database"),
                _directory(pdf_value, "PDF root"),
            )
        )
    if not requested:
        raise _error("at least one run source is required")

    sources: list[dict[str, str]] = []
    identities: set[tuple[str, str]] = set()
    documents_by_family: dict[str, set[str]] = defaultdict(set)
    all_documents: set[str] = set()
    family_document_observation_count = 0
    for family_id, family_run_id, results, pages, pdf_root in requested:
        identity = (family_id, family_run_id)
        if identity in identities:
            raise _error("the same exact family run was requested more than once")
        identities.add(identity)
        source, documents = _source_entry(
            family_id=family_id,
            family_run_id=family_run_id,
            results_database=results,
            page_database=pages,
            pdf_root=pdf_root,
        )
        source_shas = {item[0] for item in documents}
        if documents_by_family[family_id] & source_shas:
            raise _error("two review runs duplicate a PDF within one family")
        documents_by_family[family_id].update(source_shas)
        all_documents.update(source_shas)
        family_document_observation_count += len(source_shas)
        sources.append(source)

    sources.sort(key=lambda item: (item["family_id"], item["family_run_id"]))
    return {
        "format_version": FORMAT_VERSION,
        "sources": sources,
        "summary": {
            "family_count": len(documents_by_family),
            "family_document_observation_count": family_document_observation_count,
            "run_source_count": len(sources),
            "unique_document_count": len(all_documents),
        },
    }


def main() -> int:
    args = _parser().parse_args()
    manifest = build_manifest(args)
    payload = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )
    if args.output.exists():
        if (
            args.output.is_symlink()
            or not args.output.is_file()
            or args.output.read_bytes() != payload
        ):
            raise _error("write-once review manifest output drifted")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
