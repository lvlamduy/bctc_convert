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
    with pytest.raises(cache_v1.FamilyFirstOcrQueryCacheV1Error):
        cache_v1.scan_cached_accounting_family_topology_v1(database, {}, jobs=True)


def test_cached_topology_scan_balances_documents_and_preserves_source_order(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = _database(tmp_path)
    family_spec = {"family_id": "TEST_FAMILY", "format_version": "test"}
    monkeypatch.setattr(cache_v1.topology_v1, "_spec", lambda value: value)
    monkeypatch.setattr(
        cache_v1.topology_v1,
        "build_accounting_family_topology_scan_v1",
        lambda pages, spec: {
            "format": spec["format_version"],
            "scan_id": "scan-test",
            "surface": pages[0]["lines"][0]["vietocr_text"],
        },
    )

    assert cache_v1._balanced_document_chunks(((1, 100), (2, 50), (3, 25)), 2) == (
        (1,),
        (2, 3),
    )
    assert cache_v1.scan_cached_accounting_family_topology_v1(database, family_spec, jobs=1) == (
        {
            "format": "test",
            "scan_id": "scan-test",
            "surface": "Tiền gửi tại các TCTD khác",
        },
    )

    scans = ({"status": "UNIQUE", "count": 1},)
    assert cache_v1.topology_scan_parity_v1(
        scans,
        {
            "trials": [
                {
                    "document_ordinal": 1,
                    "topology_scan": {"status": "UNIQUE", "count": 1},
                }
            ]
        },
    ) == {
        "mismatch_document_ordinals": [],
        "scan_count": 1,
        "typed_equal_count": 1,
    }
    assert cache_v1.topology_scan_parity_v1(
        scans,
        {
            "trials": [
                {
                    "document_ordinal": 1,
                    "topology_scan": {"status": "UNIQUE", "count": 1.0},
                }
            ]
        },
    )["mismatch_document_ordinals"] == [1]

    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (2, "document-2", "MBB", 2026, "H1", "CONSOLIDATED", "b.pdf", "e" * 64, 1, 1, 1),
    )
    connection.execute(
        "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (2, 1, 1, 1000, 1400, "f" * 64, 2, "page-2.json", "a" * 64, 3),
    )
    connection.execute(
        "INSERT INTO lines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            2,
            2,
            1,
            0,
            "sample-000000002",
            10,
            20,
            200,
            40,
            "crop-2.png",
            "b" * 64,
            4,
            "Cho vay các TCTD khác",
            "Cho vay các TCTD khác",
            "cho vay cac tctd khac",
            0.9,
            200,
            32,
            "456",
            0.8,
        ),
    )
    connection.executemany(
        "UPDATE metadata SET value = ? WHERE key = ?",
        [("2", "document_count"), ("2", "page_count"), ("2", "line_count")],
    )
    connection.commit()
    connection.close()

    topology_database = tmp_path / "topology.sqlite3"
    first = cache_v1.refresh_cached_topology_results_v1(
        database, topology_database, family_spec, jobs=1
    )
    assert first["cache_hit_count"] == 0
    assert first["recomputed_count"] == 2
    second = cache_v1.refresh_cached_topology_results_v1(
        database, topology_database, family_spec, jobs=1
    )
    assert second["cache_hit_count"] == 2
    assert second["recomputed_count"] == 0
    assert cache_v1.read_cached_topology_results_v1(database, topology_database, family_spec) == (
        {
            "format": "test",
            "scan_id": "scan-test",
            "surface": "Tiền gửi tại các TCTD khác",
        },
        {
            "format": "test",
            "scan_id": "scan-test",
            "surface": "Cho vay các TCTD khác",
        },
    )

    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE documents SET document_id = ? WHERE document_ordinal = 1",
        ("document-1-revised",),
    )
    connection.commit()
    connection.close()
    revised = cache_v1.refresh_cached_topology_results_v1(
        database, topology_database, family_spec, jobs=1
    )
    assert revised["cache_hit_count"] == 1
    assert revised["recomputed_count"] == 1


def _evidence(tmp_path, *, sweep_id: str, reason: str) -> None:
    trial = {
        "document_ordinal": 1,
        "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
        "topology_scan": {
            "regions": [{"page_sequence": 1}],
            "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
        },
        "unresolved_reasons": [reason],
    }
    value = {
        "family_id": "INTERBANK",
        "sweep_id": sweep_id,
        "trials": [trial],
    }
    (tmp_path / "evidence.json").write_bytes(cache_v1.canonical_json_bytes_v1(value) + b"\n")


def test_incremental_family_cache_replaces_only_small_trial_sidecar(tmp_path) -> None:
    database = _database(tmp_path)
    family_database = tmp_path / "family.sqlite3"
    _evidence(tmp_path, sweep_id="sweep-1", reason="OLD_REASON")

    first = cache_v1.refresh_family_first_trial_query_cache_v1(
        tmp_path,
        database,
        family_database,
        evidence_sweep_paths=(tmp_path / "evidence.json",),
    )
    assert first["trial_count"] == 1
    assert first["refreshed_families"] == ["INTERBANK"]
    assert cache_v1.family_trial_reason_counts_from_incremental_cache_v1(
        database, family_database, "INTERBANK"
    ) == [{"reason": "OLD_REASON", "document_count": 1}]

    _evidence(tmp_path, sweep_id="sweep-2", reason="NEW_REASON")
    second = cache_v1.refresh_family_first_trial_query_cache_v1(
        tmp_path,
        database,
        family_database,
        evidence_sweep_paths=(tmp_path / "evidence.json",),
    )
    assert second["cache_id"] != first["cache_id"]
    assert cache_v1.family_trial_reason_counts_from_incremental_cache_v1(
        database, family_database, "INTERBANK"
    ) == [{"reason": "NEW_REASON", "document_count": 1}]
    assert cache_v1.read_cached_family_trials_from_incremental_cache_v1(
        database,
        family_database,
        "INTERBANK",
        evidence_status="UNRESOLVED_EVIDENCE_GATES",
    )[0]["unresolved_reasons"] == ["NEW_REASON"]
