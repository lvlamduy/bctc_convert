from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/review/build_family_review_run_manifest.py"
SPEC = importlib.util.spec_from_file_location("build_family_review_run_manifest", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def _results(
    path: Path,
    *,
    family_id: str,
    run_id: str,
    source_sha256: str,
    source_name: str,
    current: bool,
) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE family_run (
                family_run_id TEXT PRIMARY KEY,
                family_id TEXT NOT NULL,
                document_count INTEGER NOT NULL
            );
            CREATE TABLE family_trial (
                family_run_id TEXT NOT NULL,
                document_ordinal INTEGER NOT NULL,
                source_sha256 TEXT NOT NULL,
                source_logical_name TEXT NOT NULL,
                status TEXT NOT NULL,
                candidate_count INTEGER NOT NULL,
                mapping_count INTEGER NOT NULL,
                reasons_json BLOB NOT NULL
            );
            CREATE TABLE family_current_selection (
                family_id TEXT PRIMARY KEY,
                family_run_id TEXT NOT NULL
            );
            """
        )
        connection.execute("INSERT INTO family_run VALUES (?, ?, 1)", (run_id, family_id))
        connection.execute(
            "INSERT INTO family_trial VALUES (?, 1, ?, ?, 'READY', 1, 1, ?)",
            (run_id, source_sha256, source_name, b"[]"),
        )
        if current:
            connection.execute(
                "INSERT INTO family_current_selection VALUES (?, ?)", (family_id, run_id)
            )


def _pages(path: Path, *, source_sha256: str, source_name: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE document (source_sha256 TEXT PRIMARY KEY, source_logical_name TEXT)"
        )
        connection.execute("INSERT INTO document VALUES (?, ?)", (source_sha256, source_name))


def _pdf(root: Path, source_name: str) -> None:
    logical = Path(source_name)
    if logical.parts[0] == "vietstock_bctc":
        logical = Path(*logical.parts[1:])
    path = root / logical
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.7\n% review fixture\n")


def _fixture_sources(tmp_path: Path, *, duplicate_pdf: bool = False) -> tuple[Namespace, str, str]:
    family_id = "LOAN_QUALITY_CLASSIFICATION"
    old_sha = "a" * 64
    new_sha = old_sha if duplicate_pdf else "b" * 64
    old_name = "vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf"
    new_name = (
        old_name if duplicate_pdf else "vietstock_bctc/ABB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf"
    )
    old_results = tmp_path / "old-results.sqlite3"
    old_pages = tmp_path / "old-pages.sqlite3"
    new_results = tmp_path / "new-results.sqlite3"
    new_pages = tmp_path / "new-pages.sqlite3"
    pdf_root = tmp_path / "vietstock_bctc"
    pdf_root.mkdir()
    _results(
        old_results,
        family_id=family_id,
        run_id="run-old",
        source_sha256=old_sha,
        source_name=old_name,
        current=True,
    )
    _pages(old_pages, source_sha256=old_sha, source_name=old_name)
    _results(
        new_results,
        family_id=family_id,
        run_id="run-new",
        source_sha256=new_sha,
        source_name=new_name,
        current=False,
    )
    _pages(new_pages, source_sha256=new_sha, source_name=new_name)
    _pdf(pdf_root, old_name)
    _pdf(pdf_root, new_name)
    receipt = tmp_path / "run-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "completed": [{"family_id": family_id, "family_run_id": "run-new"}],
                "deferred": [],
                "disposition": "SUCCEEDED",
                "format_version": builder.RUN_RECEIPT_FORMAT,
                "selected_family_count": 1,
            }
        ),
        encoding="utf-8",
    )
    return (
        Namespace(
            current_source=[[str(old_results), str(old_pages), str(pdf_root)]],
            receipt_source=[[str(receipt), str(new_results), str(new_pages), str(pdf_root)]],
            explicit_source=[],
            output=tmp_path / "manifest.json",
        ),
        old_sha,
        new_sha,
    )


def test_builder_joins_current_and_receipt_runs_without_mutating_sources(tmp_path: Path) -> None:
    args, old_sha, new_sha = _fixture_sources(tmp_path)

    manifest = builder.build_manifest(args)

    assert manifest["summary"] == {
        "family_count": 1,
        "family_document_observation_count": 2,
        "run_source_count": 2,
        "unique_document_count": 2,
    }
    assert {source["family_run_id"] for source in manifest["sources"]} == {
        "run-old",
        "run-new",
    }
    assert {old_sha, new_sha} == {"a" * 64, "b" * 64}
    with sqlite3.connect(args.current_source[0][0]) as connection:
        assert connection.execute("SELECT * FROM family_current_selection").fetchall() == [
            ("LOAN_QUALITY_CLASSIFICATION", "run-old")
        ]
    with sqlite3.connect(args.receipt_source[0][1]) as connection:
        assert connection.execute("SELECT * FROM family_current_selection").fetchall() == []


def test_builder_rejects_overlapping_pdf_frontiers_within_family(tmp_path: Path) -> None:
    args, _old_sha, _new_sha = _fixture_sources(tmp_path, duplicate_pdf=True)

    with pytest.raises(builder.BuildFamilyReviewRunManifestError, match="duplicate a PDF"):
        builder.build_manifest(args)


def test_builder_rejects_receipt_run_missing_from_results_database(tmp_path: Path) -> None:
    args, _old_sha, _new_sha = _fixture_sources(tmp_path)
    receipt = Path(args.receipt_source[0][0])
    value = json.loads(receipt.read_text())
    value["completed"][0]["family_run_id"] = "forged-run"
    receipt.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(builder.BuildFamilyReviewRunManifestError, match="absent"):
        builder.build_manifest(args)
