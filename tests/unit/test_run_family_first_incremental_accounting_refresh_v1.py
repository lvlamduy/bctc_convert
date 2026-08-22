from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/run_family_first_incremental_accounting_refresh_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "run_family_first_incremental_accounting_refresh_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
subject = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(subject)


def _trial(ordinal: int, start: int, stop: int) -> dict:
    return {
        "document_ordinal": ordinal,
        "topology_scan": {
            "regions": [
                {
                    "cluster_end_document_line_ordinal_exclusive": stop,
                    "cluster_start_document_line_ordinal": start,
                }
            ]
        },
    }


def test_mixed_candidate_scope_uses_document_offsets_and_family_regions() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE pages (
            document_ordinal INTEGER,
            physical_page INTEGER,
            line_count INTEGER
        );
        CREATE TABLE lines (
            document_ordinal INTEGER,
            physical_page INTEGER,
            line_ordinal INTEGER,
            numeric_text TEXT
        );
        """
    )
    connection.executemany(
        "INSERT INTO pages VALUES (?, ?, ?)",
        [(1, 1, 5), (1, 2, 5), (2, 1, 5)],
    )
    connection.executemany(
        "INSERT INTO lines VALUES (?, ?, ?, ?)",
        [
            (1, 1, 2, "1.460,873"),
            (1, 2, 4, "9,999.999"),
            (2, 1, 2, "55.307.732"),
        ],
    )

    trials = [_trial(1, 1, 5), _trial(2, 0, 5)]

    assert subject._mixed_candidate_documents(connection, trials) == (1,)
    assert subject._selected_pages(connection, trials[0]) == (1,)
