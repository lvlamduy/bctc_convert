#!/usr/bin/env python3
"""Benchmark authenticated region-first SQL retrieval against full hydration.

This command is read-only.  It validates the tracked document-store manifest
and exact SQLite content reference, then excludes that one-time authentication
hash from both compared timings.  The benchmark state is diagnostic only; all
production consumers must use the opaque authenticated store capability exposed
by ``retrieve_authenticated_family_first_regions_v2``. Its default query is the
exact adapter-owned Family 11 V2 spec, including the adapter content binding.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1  # noqa: E402
from bctc_ai.evaluation import family_first_region_retrieval_v1 as retrieval_v1  # noqa: E402
from bctc_ai.evaluation import loan_geography_scoped_table_adapter_v1 as adapter_v1  # noqa: E402
from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1  # noqa: E402

DEFAULT_QUERY_SPEC = adapter_v1.build_loan_geography_region_query_spec_v2(PROJECT_ROOT)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=cache_v1.DEFAULT_DATABASE_PATH,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=store_v1.REGISTRY_PATH,
    )
    parser.add_argument("--query-spec", type=Path)
    parser.add_argument("--repeat", type=int, default=3)
    return parser


def _object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if type(value) is not dict:
        raise RuntimeError(f"{label} must contain one JSON object")
    return value


def _timed(callable_: Any, repeat: int) -> tuple[list[float], Any]:
    timings = []
    result = None
    for _iteration in range(repeat):
        started = time.perf_counter()
        result = callable_()
        timings.append(time.perf_counter() - started)
    return timings, result


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "maximum_seconds": max(values),
        "median_seconds": statistics.median(values),
        "minimum_seconds": min(values),
    }


def _full_hydration(database: Path) -> int:
    with cache_v1._connect(database) as connection:
        rows = connection.execute(
            "SELECT document_ordinal, physical_page, line_ordinal, sample_id, "
            "bbox_left, bbox_top, bbox_right, bbox_bottom, vietocr_text, "
            "accentless_text, numeric_text FROM lines "
            "ORDER BY document_ordinal, physical_page, line_ordinal"
        ).fetchall()
    return len(rows)


def _selected_hydration(database: Path, receipt: dict[str, Any]) -> dict[str, int]:
    count = 0
    fallback_count = 0
    indexed_count = 0
    with cache_v1._connect(database) as connection:
        for document in receipt["documents"]:
            pages = document["selected_pages"]
            if not pages:
                continue
            placeholders = ",".join("?" for _page in pages)
            rows = connection.execute(
                "SELECT document_ordinal, physical_page, line_ordinal, sample_id, "
                "bbox_left, bbox_top, bbox_right, bbox_bottom, vietocr_text, "
                "accentless_text, numeric_text FROM lines "
                "WHERE document_ordinal = ? "
                f"AND physical_page IN ({placeholders}) "
                "ORDER BY physical_page, line_ordinal",
                (document["document_ordinal"], *pages),
            ).fetchall()
            count += len(rows)
            if document["selection_mode"].startswith("FULL_DOCUMENT_FALLBACK"):
                fallback_count += len(rows)
            else:
                indexed_count += len(rows)
    return {
        "fallback_line_count": fallback_count,
        "indexed_line_count": indexed_count,
        "line_count": count,
    }


def main() -> int:
    args = _parser().parse_args()
    if type(args.repeat) is not int or not 1 <= args.repeat <= 20:
        raise SystemExit("--repeat must be between 1 and 20")
    database = args.database if args.database.is_absolute() else PROJECT_ROOT / args.database
    manifest_path = args.manifest if args.manifest.is_absolute() else PROJECT_ROOT / args.manifest
    manifest = store_v1.validate_family_first_document_evidence_manifest_shape_v1(
        _object(manifest_path, "tracked document-store manifest")
    )
    observed_database_ref = store_v1._stream_ref(
        PROJECT_ROOT,
        database,
        "benchmark OCR SQLite database",
    )
    if not same_typed_json_v1(observed_database_ref, manifest["database_ref"]):
        raise SystemExit("benchmark database differs from tracked authenticated content reference")
    query_spec = (
        DEFAULT_QUERY_SPEC
        if args.query_spec is None
        else _object(PROJECT_ROOT / args.query_spec, "region query spec")
    )
    query_spec = retrieval_v1.validate_family_first_region_query_spec_v2(query_spec)
    state = SimpleNamespace(
        database_path=database,
        manifest=manifest,
        root=PROJECT_ROOT,
    )
    engine_ref = retrieval_v1._engine_ref(PROJECT_ROOT)

    # Warm the immutable SQLite page cache once before comparing both paths.
    with cache_v1._connect(database) as connection:
        connection.execute("SELECT COUNT(*) FROM documents").fetchone()
    indexed_timings, receipt = _timed(
        lambda: retrieval_v1._retrieve_from_state(
            state,
            query_spec,
            engine_ref=engine_ref,
        ),
        args.repeat,
    )
    replay_started = time.perf_counter()
    replayed = retrieval_v1._validate_receipt_shape(
        retrieval_v1._retrieve_from_state(
            state,
            query_spec,
            engine_ref=engine_ref,
        )
    )
    replay_seconds = time.perf_counter() - replay_started
    if not same_typed_json_v1(receipt, replayed):
        raise RuntimeError("region receipt did not replay from the exact SQLite source")
    if args.query_spec is None and not same_typed_json_v1(
        query_spec,
        adapter_v1.build_loan_geography_region_query_spec_v2(PROJECT_ROOT),
    ):
        raise RuntimeError("Family 11 adapter-bound query spec changed during benchmark")
    selected_timings, selected_hydration = _timed(
        lambda: _selected_hydration(database, receipt),
        args.repeat,
    )
    legacy_timings, legacy_line_count = _timed(
        lambda: _full_hydration(database),
        args.repeat,
    )
    indexed_total = [
        query + hydration
        for query, hydration in zip(indexed_timings, selected_timings, strict=True)
    ]
    fallback_selected_pages = sum(
        len(document["selected_pages"])
        for document in receipt["documents"]
        if document["selection_mode"].startswith("FULL_DOCUMENT_FALLBACK")
    )
    fallback_reason_counts: dict[str, int] = {}
    for document in receipt["documents"]:
        if not document["selection_mode"].startswith("FULL_DOCUMENT_FALLBACK"):
            continue
        reason = document["fallback_reason"]
        fallback_reason_counts[reason] = fallback_reason_counts.get(reason, 0) + 1
    indexed_selected_pages = receipt["metrics"]["selected_page_count"] - fallback_selected_pages
    result = {
        "authentication": {
            "database_content_reference_verified_before_timing": True,
            "manifest_id": manifest["manifest_id"],
            "mode": "READ_ONLY_DIAGNOSTIC_EXACT_TRACKED_SOURCE_PUBLICATION_REQUIRES_OPAQUE_CAPABILITY",
            "receipt_direct_sql_replay_verified": True,
            "receipt_replay_seconds": replay_seconds,
        },
        "before_full_python_hydration": {
            "line_count": legacy_line_count,
            "timing": _summary(legacy_timings),
        },
        "corpus": {
            "document_count": receipt["metrics"]["document_count"],
            "line_count": receipt["metrics"]["source_line_count"],
            "page_count": receipt["metrics"]["source_page_count"],
        },
        "query": {
            "family_id": query_spec["family_id"],
            "query_spec_id": receipt["source_binding"]["query_spec_id"],
            "receipt_id": receipt["receipt_id"],
            "runtime_determinants": receipt["source_binding"]["runtime_determinants"],
            "semantic_assignment_adapter_ref": query_spec["semantic_assignment_adapter_ref"],
        },
        "region_first": {
            "fallback_document_count": receipt["metrics"]["fallback_document_count"],
            "fallback_reason_counts": fallback_reason_counts,
            "indexed_document_count": (
                receipt["metrics"]["document_count"] - receipt["metrics"]["fallback_document_count"]
            ),
            "occurrence_count": receipt["metrics"]["occurrence_count"],
            "raw_fts_hit_line_count": receipt["metrics"]["raw_fts_hit_line_count"],
            "raw_rare_trigram_hit_line_count": receipt["metrics"][
                "raw_rare_trigram_hit_line_count"
            ],
            "selected_fallback_line_count": selected_hydration["fallback_line_count"],
            "selected_fallback_page_count": fallback_selected_pages,
            "selected_indexed_line_count": selected_hydration["indexed_line_count"],
            "selected_indexed_page_count": indexed_selected_pages,
            "selected_line_count": selected_hydration["line_count"],
            "selected_page_count": receipt["metrics"]["selected_page_count"],
            "timing_query_only": _summary(indexed_timings),
            "timing_query_plus_selected_hydration": _summary(indexed_total),
            "zero_validated_hit_document_count": receipt["metrics"][
                "zero_validated_hit_document_count"
            ],
        },
        "reduction": {
            "comparison_scope": ("RAW_HYDRATION_RATIO_ONLY_NOT_AN_END_TO_END_GRAPH_SPEEDUP_CLAIM"),
            "line_reduction_fraction": (1.0 - selected_hydration["line_count"] / legacy_line_count),
            "median_full_hydration_over_region_query_plus_hydration_ratio": (
                statistics.median(legacy_timings) / statistics.median(indexed_total)
            ),
        },
        "repeat": args.repeat,
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
