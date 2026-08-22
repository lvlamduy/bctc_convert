from __future__ import annotations

import json
import sqlite3

import pytest

from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1


def _database(tmp_path):
    path = tmp_path / "cache.sqlite3"
    connection = sqlite3.connect(path)
    cache_v1._create_schema(connection)
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            ("cache_id", json.dumps("ffoqcv1:cache:" + "1" * 64)),
            ("document_count", "1"),
            ("format_version", json.dumps(cache_v1.CACHE_FORMAT_VERSION)),
            ("line_count", "1"),
            ("page_count", "1"),
            ("schema_version", "1"),
            ("sources", "{}"),
            ("authority", "{}"),
        ],
    )
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "document-1", "ACB", 2026, "H1", "CONSOLIDATED", "a.pdf", "a" * 64, 1, 1, 1),
    )
    connection.execute(
        "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 1, 1, 1000, 1400, "b" * 64, 2, "page.json", "c" * 64, 3),
    )
    connection.execute(
        "INSERT INTO lines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            1,
            1,
            1,
            0,
            "sample-000000001",
            10,
            20,
            200,
            40,
            "crop.png",
            "d" * 64,
            4,
            "Tiền gửi tại các TCTD khác",
            "Tiền gửi tại các TCTD khác",
            "tien gui tai cac tctd khac",
            0.9,
            200,
            32,
            "123",
            0.8,
        ),
    )
    connection.execute(
        "INSERT INTO line_search(rowid, vietocr_text, accentless_text) "
        "SELECT line_id, vietocr_text, accentless_text FROM lines"
    )
    trial = {
        "document_ordinal": 1,
        "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
        "unresolved_reasons": ["COLUMN_CONTEXT:PERIOD_AXIS_NOT_BOUND"],
    }
    connection.execute(
        "INSERT INTO family_trials VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "INTERBANK",
            "sweep-1",
            1,
            trial["evidence_status"],
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
            "[1]",
            json.dumps(trial["unresolved_reasons"]),
            json.dumps(trial),
        ),
    )
    connection.execute(
        "INSERT INTO trial_reasons VALUES (?, ?, ?)",
        ("INTERBANK", 1, trial["unresolved_reasons"][0]),
    )
    connection.commit()
    connection.close()
    return path


def test_cache_projects_searches_and_reads_exact_document_axis(tmp_path) -> None:
    database = _database(tmp_path)

    projection = cache_v1.project_family_first_ocr_query_cache_v1(database)
    assert projection["document_count"] == 1
    assert projection["page_count"] == 1
    assert projection["line_count"] == 1

    hits = cache_v1.search_cached_ocr_lines_v1(database, "tctd khac")
    assert [
        (hit["document_ordinal"], hit["physical_page"], hit["numeric_text"]) for hit in hits
    ] == [(1, 1, "123")]
    blind = cache_v1.read_cached_blind_pages_v1(database, 1)
    assert blind[0]["lines"][0]["source_text"] is None
    joined = cache_v1.read_cached_joined_pages_v1(database, 1, selected_pages=(1,))
    assert joined[0]["page_width"] == 1000
    assert joined[0]["lines"][0]["numeric_recognition"]["raw_prediction"] == "123"


def test_cache_reads_family_trials_and_reason_counts(tmp_path) -> None:
    database = _database(tmp_path)

    assert cache_v1.family_trial_reason_counts_v1(database, "INTERBANK") == [
        {"reason": "COLUMN_CONTEXT:PERIOD_AXIS_NOT_BOUND", "document_count": 1}
    ]
    assert cache_v1.read_cached_family_trials_v1(
        database,
        "INTERBANK",
        evidence_status="UNRESOLVED_EVIDENCE_GATES",
    ) == [
        {
            "document_ordinal": 1,
            "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
            "unresolved_reasons": ["COLUMN_CONTEXT:PERIOD_AXIS_NOT_BOUND"],
        }
    ]
    assert (
        cache_v1.read_cached_family_trials_v1(
            database,
            "INTERBANK",
            evidence_status="READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        )
        == []
    )


def test_cache_query_arguments_fail_closed(tmp_path) -> None:
    database = _database(tmp_path)

    with pytest.raises(cache_v1.FamilyFirstOcrQueryCacheV1Error):
        cache_v1.search_cached_ocr_lines_v1(database, "ab")
    with pytest.raises(cache_v1.FamilyFirstOcrQueryCacheV1Error):
        cache_v1.read_cached_blind_pages_v1(database, True)
    with pytest.raises(cache_v1.FamilyFirstOcrQueryCacheV1Error):
        cache_v1.read_cached_joined_pages_v1(database, 1, selected_pages=())
