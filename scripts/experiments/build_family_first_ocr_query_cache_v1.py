#!/usr/bin/env python3
"""Build, inspect, search, or benchmark the disposable all-filing OCR SQLite cache."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation.family_first_ocr_query_cache_v1 import (  # noqa: E402
    DEFAULT_DATABASE_PATH,
    DEFAULT_FAMILY_DATABASE_PATH,
    DEFAULT_TOPOLOGY_DATABASE_PATH,
    build_family_first_ocr_query_cache_v1,
    family_trial_reason_counts_from_incremental_cache_v1,
    family_trial_reason_counts_v1,
    project_family_first_ocr_query_cache_v1,
    project_family_first_trial_query_cache_v1,
    read_cached_family_trials_from_incremental_cache_v1,
    read_cached_family_trials_v1,
    read_cached_topology_results_v1,
    refresh_cached_topology_results_v1,
    refresh_family_first_trial_query_cache_v1,
    scan_cached_accounting_family_topology_v1,
    search_cached_ocr_lines_v1,
    topology_scan_parity_v1,
)


def _object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--family-database", type=Path, default=DEFAULT_FAMILY_DATABASE_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--evidence", action="append", default=[], type=Path)
    sub.add_parser("stats")
    search = sub.add_parser("search")
    search.add_argument("text")
    search.add_argument("--limit", type=int, default=100)
    reasons = sub.add_parser("reasons")
    reasons.add_argument("family_id")
    trials = sub.add_parser("trials")
    trials.add_argument("family_id")
    trials.add_argument("--evidence-status")
    refresh = sub.add_parser("refresh-family")
    refresh.add_argument("--evidence", action="append", required=True, type=Path)
    sub.add_parser("family-stats")
    incremental_reasons = sub.add_parser("family-reasons")
    incremental_reasons.add_argument("family_id")
    incremental_trials = sub.add_parser("family-trials")
    incremental_trials.add_argument("family_id")
    incremental_trials.add_argument("--evidence-status")
    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument("--family-spec", required=True, type=Path)
    benchmark.add_argument("--jobs", default=min(12, os.cpu_count() or 1), type=int)
    benchmark.add_argument("--expected-evidence", type=Path)
    benchmark.add_argument(
        "--topology-cache",
        const=DEFAULT_TOPOLOGY_DATABASE_PATH,
        nargs="?",
        type=Path,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = args.database if args.database.is_absolute() else PROJECT_ROOT / args.database
    family_database = (
        args.family_database
        if args.family_database.is_absolute()
        else PROJECT_ROOT / args.family_database
    )
    if args.command == "build":
        result = build_family_first_ocr_query_cache_v1(
            PROJECT_ROOT,
            database,
            evidence_sweep_paths=tuple(args.evidence),
        )
    elif args.command == "stats":
        result = project_family_first_ocr_query_cache_v1(database)
    elif args.command == "search":
        started = time.perf_counter()
        hits = search_cached_ocr_lines_v1(database, args.text, limit=args.limit)
        result = {"elapsed_seconds": time.perf_counter() - started, "hits": hits}
    elif args.command == "reasons":
        started = time.perf_counter()
        counts = family_trial_reason_counts_v1(database, args.family_id)
        result = {"elapsed_seconds": time.perf_counter() - started, "reasons": counts}
    elif args.command == "trials":
        started = time.perf_counter()
        trials = read_cached_family_trials_v1(
            database,
            args.family_id,
            evidence_status=args.evidence_status,
        )
        result = {
            "elapsed_seconds": time.perf_counter() - started,
            "trial_count": len(trials),
            "trials": trials,
        }
    elif args.command == "refresh-family":
        result = refresh_family_first_trial_query_cache_v1(
            PROJECT_ROOT,
            database,
            family_database,
            evidence_sweep_paths=tuple(args.evidence),
        )
    elif args.command == "family-stats":
        result = project_family_first_trial_query_cache_v1(database, family_database)
    elif args.command == "family-reasons":
        started = time.perf_counter()
        counts = family_trial_reason_counts_from_incremental_cache_v1(
            database, family_database, args.family_id
        )
        result = {"elapsed_seconds": time.perf_counter() - started, "reasons": counts}
    elif args.command == "family-trials":
        started = time.perf_counter()
        trials = read_cached_family_trials_from_incremental_cache_v1(
            database,
            family_database,
            args.family_id,
            evidence_status=args.evidence_status,
        )
        result = {
            "elapsed_seconds": time.perf_counter() - started,
            "trial_count": len(trials),
            "trials": trials,
        }
    else:
        spec = _object(PROJECT_ROOT / args.family_spec)
        started = time.perf_counter()
        topology_cache = args.topology_cache
        if topology_cache is not None:
            topology_cache = (
                topology_cache if topology_cache.is_absolute() else PROJECT_ROOT / topology_cache
            )
            cache_refresh = refresh_cached_topology_results_v1(
                database, topology_cache, spec, jobs=args.jobs
            )
            scans = read_cached_topology_results_v1(database, topology_cache, spec)
        else:
            cache_refresh = None
            scans = scan_cached_accounting_family_topology_v1(database, spec, jobs=args.jobs)
        statuses = Counter(scan["status"] for scan in scans)
        projection = project_family_first_ocr_query_cache_v1(database)
        result = {
            "document_count": projection["document_count"],
            "elapsed_seconds": time.perf_counter() - started,
            "jobs": args.jobs,
            "statuses": dict(sorted(statuses.items())),
        }
        if cache_refresh is not None:
            result["topology_cache"] = cache_refresh
        if args.expected_evidence is not None:
            result["formal_parity"] = topology_scan_parity_v1(
                scans, _object(PROJECT_ROOT / args.expected_evidence)
            )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
