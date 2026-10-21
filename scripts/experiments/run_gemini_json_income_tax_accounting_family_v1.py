#!/usr/bin/env python3
"""Database-first Family 39 diagnostics, independent replay and fresh persistence.

This runner does not invoke extraction providers or claim terminal/final PDF
acceptance. NOT_OBSERVED/UNRESOLVED and every source-only row remain visible.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/experiments")]

import run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic  # noqa: E402

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (  # noqa: E402
    _PERIOD_INVENTORY_DEPENDENCY_PATHS,
    FAMILY_ID,
    build_gemini_json_income_tax_region_query_receipt_v1,
    compile_gemini_json_income_tax_family_specs_v1,
    evaluate_gemini_json_income_tax_family_cluster_v1,
    income_tax_document_period_evaluation_scope_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    _source_table,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (  # noqa: E402
    validate_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    load_page_json_versions_v1 as load_page_json_versions_v1,  # Original API for diagnostic comparison only.
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_multitable_hierarchical_family_regions_v1,
)
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (  # noqa: E402
    load_income_tax_source_page_json_versions_v1,
)

SHARED_PINS = {
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2",
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
}
SPEC_PATHS = {
    name: ROOT / ("config/families/tm-income-tax-" + suffix + "-v1.json")
    for name, suffix in (
        ("topology", "topology"),
        ("evaluation", "evaluation"),
        ("schema", "schema-binding"),
        ("adapter", "adapter"),
        ("repair", "source-repair"),
    )
}
PAGE_SCOPE_PATH = ROOT / "data/registered/gemini_json_first_27bank_vietnamese_page_scope_v2.json"
PAGE_SCOPE_SHA = "72431fa5e6bd5679a0c9701296da9a5b037b34ec2734da50c9b6bbefacec16be"
PAGE_SCOPE_ID = "gjfvietnamesev2:c8df0220081d5bcef4b4b6051be971430a126591cfbffb40ae8662f8951e5906"
PREFIX_CONCLUSION = "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX"
RENDER_BINDINGS_PATH = ROOT / "config/families/tm-income-tax-source-repair-render-bindings-v1.json"
RENDER_BINDINGS_SHA = "a714e256ad3b508fba5b331e27551433824b8db14d84ea9cade28a296b7cf249"
ORIGINAL_REPAIR_SPEC_SHA = "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4"
RENDER_PROFILES = {
    "DECLARED_MATRIX_2_RGB_PNG": (2, 2),
    "EXISTING_RENDERING_PDF_MATRIX_300_DPI_OVER_72_RGB_PNG": (300 / 72, 300 / 72),
}


class RunGeminiJsonIncomeTaxV1Error(RuntimeError):
    """An authenticated Family-39 diagnostic/replay/storage proof failed."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise RunGeminiJsonIncomeTaxV1Error(message)


def _json(path: Path) -> dict[str, Any]:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + str(path))
            result[key] = value
        return result

    value = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    require(type(value) is dict, "One JSON object required: " + str(path))
    return value


def _safe_path(path: Path) -> Path:
    require(path.is_absolute() and ".." not in path.parts, "Explicit safe absolute path required")
    for part in (path, *path.parents):
        require(not part.is_symlink(), "Symlink authority/output path prohibited")
    return path


def _assert_shared_pins_v1() -> None:
    for path, digest in SHARED_PINS.items():
        require(generic._sha256(ROOT / path) == digest, "Frozen shared pin differs: " + path)


def _compile_specs_v1():
    specs = {name: _json(path) for name, path in SPEC_PATHS.items()}
    compiled = compile_gemini_json_income_tax_family_specs_v1(
        specs["topology"], specs["evaluation"], specs["schema"], specs["adapter"], specs["repair"]
    )
    return specs, compiled


def _page_scope_v1(path):
    _safe_path(path)
    require(generic._sha256(path) == PAGE_SCOPE_SHA, "Registered language scope bytes differ")
    scope = _json(path)
    require(
        scope["scope_id"] == PAGE_SCOPE_ID
        and scope["format_version"] == "GEMINI_JSON_FIRST_VIETNAMESE_PAGE_SCOPE_V2",
        "Registered language scope identity differs",
    )
    rows = {row["relative_path"]: row for row in scope["documents"]}
    require(len(rows) == len(scope["documents"]), "Duplicate language scope source")
    return rows


def _check_page_scope_v1(document, physical_count, scope_rows):
    """Keep source physical pages separate from the immutable selected prefix."""
    source = document["manifest"]["document"]
    selected = len(document["ids"])
    row = scope_rows.get(source["source_logical_name"])
    if row is not None:
        require(
            row["source_sha256"] == source["source_sha256"]
            and row["source_page_count"] == physical_count
            and row["included_last_physical_page"] == selected
            and row["review_conclusion"] in {PREFIX_CONCLUSION, "FULL_DOCUMENT_VIETNAMESE"},
            "Registered language scope source/count/conclusion differs",
        )
    if selected != physical_count:
        require(
            row is not None
            and row["review_conclusion"] == PREFIX_CONCLUSION
            and 0 < selected < physical_count,
            "Selected/physical page difference lacks exact prefix authorization",
        )
    return {
        "selected_page_count": selected,
        "source_physical_page_count": physical_count,
        "excluded_non_vietnamese_appendix_page_count": physical_count - selected,
        "language_prefix_authorization": row if selected != physical_count else None,
        "language_scope_id": PAGE_SCOPE_ID,
    }


@contextmanager
def _authenticated_source_v1(path: Path, reference: dict[str, Any]):
    """Read original bytes without copying a multi-GB store; detect any mutation."""
    _safe_path(path)
    generic._assert_no_sqlite_sidecars(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        identity = generic._file_identity(os.fstat(descriptor))

        def check():
            generic._assert_no_sqlite_sidecars(path)
            require(
                generic._file_identity(os.fstat(descriptor))
                == identity
                == generic._file_identity(os.stat(path, follow_symlinks=False))
                and os.fstat(descriptor).st_size == reference["size_bytes"]
                and generic._fd_sha256(descriptor) == reference["sha256"],
                "Source SQLite bytes/identity changed",
            )

        check()
        try:
            yield path
        finally:
            check()
    finally:
        os.close(descriptor)


def _documents_v1(index: dict[str, Any], root: Path):
    """Authenticate source, immutable manifest/selection and ordered frontier."""
    result, all_ids = [], []
    current_year = datetime.now(UTC).year
    for document in index["documents"]:
        logical = document["relative_path"]
        years = [int(p) for p in Path(logical).parts if p.isdigit() and len(p) == 4]
        require(
            len(years) == 1 and 2025 <= years[0] <= current_year,
            "2024/non-current source prohibited",
        )
        manifest_path = generic._content_ref(root, document["document_manifest_ref"])
        manifest = _json(manifest_path)
        selection = validate_current_document_manifest_selection_v1(
            _json(generic._content_ref(root, document["selection_ref"]))
        )
        material = {k: v for k, v in manifest.items() if k != "document_manifest_id"}
        source = {
            "source_logical_name": logical,
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        }
        source_id = "gfpstorev1:document:" + canonical_json_sha256_v1(source)
        pages = manifest["pages"]
        require(
            manifest["document_manifest_id"]
            == document["document_manifest_id"]
            == "gfdmv1:manifest:" + canonical_json_sha256_v1(material)
            and same_typed_json_v1(manifest["document"], {**source, "document_id": source_id})
            and manifest["page_count"] == document["page_count"] == len(pages)
            and canonical_json_sha256_v1(pages) == document["page_json_frontier_sha256"],
            "Immutable source/manifest frontier differs",
        )
        require(
            selection["selection_id"] == document["selection_id"]
            and selection["document_manifest_id"] == manifest["document_manifest_id"]
            and generic._content_ref(manifest_path.parent.parent, selection["document_manifest_ref"])
            == manifest_path
            and selection["source_sha256"] == source["source_sha256"],
            "Selected manifest binding differs",
        )
        physical = [p["physical_page"] for p in pages]
        ids = [p["page_json_version_id"] for p in pages]
        require(
            physical == list(range(1, len(pages) + 1)) and len(set(ids)) == len(ids),
            "Selected page frontier is noncontiguous/duplicate",
        )
        result.append(
            {"index_document": document, "manifest": manifest, "selection": selection, "ids": ids}
        )
        all_ids.extend(ids)
    require(
        len(all_ids) == len(set(all_ids)) == index["summary"]["page_count"],
        "Selected corpus page denominator differs",
    )
    return result, all_ids


def _diagnostic_documents_v1(documents, *, document_limit=None, document_ordinals=None):
    require(document_limit is None or document_ordinals is None, "Choose only one diagnostic subset")
    if document_limit is not None:
        require(type(document_limit) is int and 0 < document_limit <= len(documents), "Invalid bounded document limit")
        ordinals = list(range(1, document_limit + 1))
    elif document_ordinals is not None:
        require(
            type(document_ordinals) is list and bool(document_ordinals)
            and all(type(value) is int and 1 <= value <= len(documents) for value in document_ordinals)
            and document_ordinals == sorted(set(document_ordinals)),
            "Diagnostic document ordinals must be unique, ascending and in the immutable index",
        )
        ordinals = document_ordinals
    else:
        return documents, None
    return [documents[ordinal - 1] for ordinal in ordinals], ordinals


def base_cluster_cache_key_v1(records, compiled, implementation_refs):
    """Complete ordered source/JSON/context/spec/implementation key; no filename routing."""
    return canonical_json_sha256_v1(
        {
            "records": records,
            "compiled_specs": compiled,
            "implementation_refs": list(implementation_refs),
            "family_id": FAMILY_ID,
            "cache_format": "F39_BASE_CLUSTER_CACHE_V1",
        }
    )


class BaseClusterCache:
    """Optional append-only content cache; never used by authoritative cold replay."""

    def __init__(self, path: Path | None):
        self.connection = None
        if path is not None:
            _safe_path(path)
            self.connection = sqlite3.connect(path)
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS f39_base_cluster_cache (cache_key TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL, content BLOB NOT NULL)"
            )
            self.connection.commit()

    def get_or_build(self, key, build):
        if self.connection is not None:
            row = self.connection.execute(
                "SELECT content_sha256,content FROM f39_base_cluster_cache WHERE cache_key=?",
                (key,),
            ).fetchone()
            if row is not None:
                require(
                    sha256(row[1]).hexdigest() == row[0], "Base-cluster cache content hash differs"
                )
                value = json.loads(row[1])
                require(
                    canonical_json_bytes_v1(value) == row[1], "Base-cluster cache is noncanonical"
                )
                return value, True
        value = build()
        if self.connection is not None:
            raw = canonical_json_bytes_v1(value)
            self.connection.execute(
                "INSERT INTO f39_base_cluster_cache VALUES (?,?,?)",
                (key, sha256(raw).hexdigest(), raw),
            )
            self.connection.commit()
        return value, False

    def close(self):
        if self.connection is not None:
            self.connection.close()


def _records_v1(document, loaded, ordinal):
    source = document["manifest"]["document"]
    source_material = {
        k: source[k] for k in ("source_logical_name", "source_sha256", "source_size_bytes")
    }
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(source_material)
    require(source.get("document_id", document_id) == document_id, "Source document ID differs")
    axis_document = {
        "document_id": document_id,
        "document_ordinal": ordinal,
        "source_logical_name": source["source_logical_name"],
        "source_sha256": source["source_sha256"],
    }
    require(len(loaded) == len(document["ids"]), "Selected JSON rows omitted")
    records = []
    for selected_ordinal, (receipt, page) in enumerate(
        zip(loaded, document["manifest"]["pages"], strict=True), 1
    ):
        require(
            receipt["page_json_version_id"] == page["page_json_version_id"]
            and receipt["physical_page"] == page["physical_page"]
            and receipt["source_logical_name"] == source["source_logical_name"]
            and receipt["source_sha256"] == source["source_sha256"],
            "Selected JSON/source/physical page differs",
        )
        records.append(
            {
                **axis_document,
                "page_json_version_id": receipt["page_json_version_id"],
                "physical_page": receipt["physical_page"],
                "selected_page_ordinal": selected_ordinal,
                "page_json": receipt["page_json"],
            }
        )
    return axis_document, records


def _trial_v1(cluster, records, compiled):
    candidates, mappings, reasons, selected = [], [], [], None
    status = cluster["status"]
    if status == READY:
        regions = cluster["component_regions"]
        candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
            regions=regions,
            page_json_by_version={r["page_json_version_id"]: r["page_json"] for r in records},
            selected_page_axis=[{k: v for k, v in r.items() if k != "page_json"} for r in records],
            compiled_specs=compiled,
            query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
                regions, cluster=cluster
            ),
        )
        candidates = [candidate]
        status = candidate["status"]
        if status == READY:
            mappings, selected = candidate["mappings"], candidate["candidate_id"]
        else:
            reasons = candidate["reasons"]
    elif status == UNRESOLVED:
        reasons = cluster["reasons"]
    else:
        require(status == NOT_OBSERVED, "Unknown family query disposition")
    return {
        "document_ordinal": cluster["document_ordinal"],
        "source_logical_name": cluster["source_logical_name"],
        "source_sha256": cluster["source_sha256"],
        "candidate_count": len(candidates),
        "candidates": candidates,
        "mappings": mappings,
        "reasons": reasons,
        "selected_candidate_id": selected,
        "status": status,
    }


def _evaluate_stream_v1(
    database, documents, compiled, *, cache=None, implementation_refs=(), independent_base=None
):
    doc_axis, page_axis, clusters, trials, source_replay_receipts = [], [], [], [], []
    timing = {
        "selected_json_load_seconds": 0.0,
        "base_cluster_seconds": 0.0,
        "family_evaluation_seconds": 0.0,
        "selected_json_sql_rows": 0,
        "selected_json_sql_payload_bytes": 0,
        "selected_json_api_calls": 0,
        "base_cache_hits": 0,
        "peak_document_selected_pages": 0,
        "sql_total_statements_claimed": False,
        "document_period_inventory_cache": {
            "requests": 0, "hits": 0, "builds": 0, "disabled_requests": 0,
            "key_seconds": 0.0, "build_seconds": 0.0, "clone_seconds": 0.0,
            "dependency_checks": 0, "dependency_check_seconds": 0.0,
            "peak_entries": 0, "peak_stored_bytes": 0,
        },
    }
    bases = (
        None
        if independent_base is None
        else {
            d["document_ordinal"]: d["cluster"] for d in independent_base["candidate_dispositions"]
        }
    )
    for ordinal, document in enumerate(documents, 1):
        started = time.perf_counter()
        loaded = load_income_tax_source_page_json_versions_v1(
            database, page_json_version_ids=document["ids"]
        )
        source_replay_receipts.extend(r["source_json_replay_receipt"] for r in loaded)
        axis, records = _records_v1(document, loaded, ordinal)
        timing["selected_json_load_seconds"] += time.perf_counter() - started
        timing["selected_json_api_calls"] += 1
        timing["selected_json_sql_rows"] += len(loaded)
        timing["selected_json_sql_payload_bytes"] += sum(
            len(canonical_json_bytes_v1(r["page_json"])) + 1 for r in loaded
        )
        timing["peak_document_selected_pages"] = max(
            timing["peak_document_selected_pages"], len(records)
        )
        doc_axis.append(axis)
        page_axis.extend({k: v for k, v in r.items() if k != "page_json"} for r in records)
        started = time.perf_counter()
        if bases is not None:
            base_cluster, hit = bases[ordinal], False
        else:

            def build(records=records):
                return coalesce_gemini_json_multitable_hierarchical_document_v1(
                    page_records=records, compiled_specs=compiled
                )

            if cache is None:
                base_cluster, hit = build(), False
            else:
                key = base_cluster_cache_key_v1(records, compiled, implementation_refs)
                base_cluster, hit = cache.get_or_build(key, build)
        timing["base_cache_hits"] += int(hit)
        timing["base_cluster_seconds"] += time.perf_counter() - started
        started = time.perf_counter()
        with income_tax_document_period_evaluation_scope_v1(enabled=independent_base is None) as period_metrics:
            cluster = recover_gemini_json_income_tax_query_cluster_v1(
                page_records=records, base_cluster=base_cluster, compiled_specs=compiled
            )
            clusters.append(cluster)
            trials.append(_trial_v1(cluster, records, compiled))
        for key, value in period_metrics.items():
            if key.startswith("peak_"):
                timing["document_period_inventory_cache"][key] = max(timing["document_period_inventory_cache"][key], value)
            else:
                timing["document_period_inventory_cache"][key] += value
        timing["family_evaluation_seconds"] += time.perf_counter() - started
    indexed = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=doc_axis,
        selected_page_axis=page_axis,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed, compiled_specs=compiled
    )
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials, indexed_query_evidence=indexed, compiled_specs=compiled
    )
    timing["source_json_replay_receipt_axis_sha256"] = canonical_json_sha256_v1(source_replay_receipts)
    timing["exact_original_source_json_replay_page_count"] = sum(
        r["classification"] == "EXACT_REPLAY" for r in source_replay_receipts
    )
    timing["lossless_original_source_json_replay_receipts"] = [
        r for r in source_replay_receipts if r["classification"] != "EXACT_REPLAY"
    ]
    return indexed, trials, timing


def replay_income_tax_trials_from_source_v1(
    *, source_page_database, selected_page_json_version_ids, compiled_specs, indexed_query_evidence,
    replay_metrics=None,
):
    """Independent storage query, fresh per-document JSON, no cache access."""
    require(replay_metrics is None or type(replay_metrics) is dict and not replay_metrics,
            "Cold replay metrics sink must be a fresh empty object")
    specs, family_compiled = _compile_specs_v1()
    require(
        same_typed_json_v1(
            compiled_specs,
            compile_gemini_json_flat_family_specs_v1(
                specs["topology"], specs["evaluation"], specs["schema"]
            ),
        ),
        "Cold replay declarative specs differ",
    )
    base = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    documents = []
    for document in base["selected_document_axis"]:
        pages = [
            p
            for p in base["selected_page_axis"]
            if p["document_ordinal"] == document["document_ordinal"]
        ]
        source = {k: document[k] for k in ("source_logical_name", "source_sha256")}
        # Document IDs are authenticated by the independent storage query. Size
        # is recovered from its exact stored identity, not guessed from content.
        with sqlite3.connect(f"file:{source_page_database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT source_size_bytes FROM document WHERE document_id=?",
                (document["document_id"],),
            ).fetchone()
        require(row is not None, "Cold replay source document absent")
        source["source_size_bytes"] = row[0]
        documents.append(
            {
                "manifest": {"document": source, "pages": pages},
                "ids": [p["page_json_version_id"] for p in pages],
            }
        )
    indexed, trials, _timing = _evaluate_stream_v1(
        source_page_database, documents, family_compiled, independent_base=base
    )
    require(
        same_typed_json_v1(indexed, indexed_query_evidence),
        "Cold replay indexed source query differs",
    )
    if replay_metrics is not None:
        replay_metrics.update(json.loads(canonical_json_bytes_v1(_timing)))
    return trials


def _validate_repair_render_bindings_v1(value, compiled):
    """An additive metadata correction cannot replace any registered source evidence."""
    require(
        type(value) is dict
        and set(value) == {
            "format_version", "family_id", "classification", "base_git_commit",
            "original_source_repair_spec_sha256", "original_render_contract",
            "diagnostic_ref", "correction_scope", "family_terminal_claimed", "bindings",
        }
        and value["format_version"] == "INCOME_TAX_REGISTERED_SOURCE_REPAIR_RENDER_BINDINGS_V1"
        and value["family_id"] == FAMILY_ID
        and value["classification"] == "REGISTERED_RENDER_PROFILE_METADATA_ERROR"
        and value["base_git_commit"] == "8efd618b6c77f0cdbb402a440e7ba3b3549184f1"
        and value["original_source_repair_spec_sha256"] == ORIGINAL_REPAIR_SPEC_SHA
        and value["family_terminal_claimed"] is False,
        "Registered render bindings identity/scope differs",
    )
    original = _json(SPEC_PATHS["repair"])
    require(
        generic._sha256(SPEC_PATHS["repair"]) == ORIGINAL_REPAIR_SPEC_SHA
        and same_typed_json_v1(value["original_render_contract"], original["render_contract"])
        and same_typed_json_v1(compiled["income_tax_source_repairs"], original["repairs"])
        and compiled["income_tax_source_repair_spec_sha256"] == canonical_json_sha256_v1(original),
        "Original registered repair specification differs",
    )
    bindings = value["bindings"]
    require(
        type(bindings) is list
        and all(type(b) is dict and set(b) == {"repair_id", "profile"} for b in bindings)
        and [b["repair_id"] for b in bindings] == [r["repair_id"] for r in original["repairs"]]
        and all(type(b["profile"]) is str and b["profile"] in RENDER_PROFILES for b in bindings),
        "Registered render bindings repair frontier/profile differs",
    )
    return {b["repair_id"]: RENDER_PROFILES[b["profile"]] for b in bindings}


def _repair_render_bindings_v1(compiled):
    _safe_path(RENDER_BINDINGS_PATH)
    require(
        generic._sha256(RENDER_BINDINGS_PATH) == RENDER_BINDINGS_SHA,
        "Registered render bindings bytes differ",
    )
    return _validate_repair_render_bindings_v1(_json(RENDER_BINDINGS_PATH), compiled)


def _authenticate_repairs_v1(document, loaded, compiled, pdf_path):
    """Replay registered source pixels and literal pre-repair rows, never infer values."""
    import fitz
    from PIL import Image

    source = document["manifest"]["document"]
    repairs = [
        r
        for r in compiled["income_tax_source_repairs"]
        if r["pdf_source"]["sha256"] == source["source_sha256"]
    ]
    if not repairs:
        return []
    profiles = _repair_render_bindings_v1(compiled)
    by_id = {r["page_json_version_id"]: r for r in loaded}
    checked, rendered = [], {}
    with fitz.open(pdf_path) as pdf:
        for repair in repairs:
            require(
                same_typed_json_v1(
                    repair["pdf_source"],
                    {
                        "logical_name": source["source_logical_name"],
                        "sha256": source["source_sha256"],
                        "size_bytes": source["source_size_bytes"],
                    },
                ),
                "Repair PDF source binding differs",
            )
            locator = repair["locator"]
            page = by_id.get(locator["page_json_version_id"])
            require(
                page is not None and page["physical_page"] == locator["physical_page"],
                "Repair page is not selected",
            )
            _, table = _source_table(
                page["page_json"], section_id=locator["section_id"], table_id=locator["table_id"]
            )
            require(1 <= locator["row_ordinal"] <= len(table["rows"]), "Repair row locator absent")
            row = table["rows"][locator["row_ordinal"] - 1]
            before = (
                row["values_exact"][repair["column_ordinal"] - 1]
                if repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH"
                else {
                    k: row[k]
                    for k in ("hierarchy_path_exact", "label_exact", "row_kind", "values_exact")
                }
            )
            require(
                same_typed_json_v1(before, repair["before_exact"]),
                "Repair before-exact source differs",
            )
            physical = locator["physical_page"]
            matrix = profiles[repair["repair_id"]]
            render_key = (physical, matrix)
            if render_key not in rendered:
                require(1 <= physical <= len(pdf), "Repair physical page outside PDF")
                pix = pdf[physical - 1].get_pixmap(
                    matrix=fitz.Matrix(*matrix), colorspace=fitz.csRGB, alpha=False
                )
                rendered[render_key] = pix.tobytes("png")
            raw = rendered[render_key]
            with Image.open(BytesIO(raw)) as image:
                rgb = image.convert("RGB")
                visual = repair["visual_evidence"]
                actual = {
                    "sha256": sha256(raw).hexdigest(),
                    "width_pixels": rgb.width,
                    "height_pixels": rgb.height,
                }
                require(
                    same_typed_json_v1(actual, visual["page_render"])
                    and sha256(rgb.crop(tuple(visual["crop_bbox_pixels"])).tobytes()).hexdigest()
                    == visual["crop_rgb_sha256"],
                    "Repair PDF render/crop differs",
                )
            checked.append(repair["repair_id"])
    return checked


def run(args):
    require(args.repo_root.resolve() == ROOT, "Runner checkout differs from explicit repo root")
    _assert_shared_pins_v1()
    for path in (
        args.repo_root,
        args.corpus_index,
        args.artifact_root,
        args.source_page_database,
        args.source_pdf_root,
        args.output_dir,
        args.results_database,
    ):
        _safe_path(path)
    require(
        not args.output_dir.exists()
        and not args.results_database.exists()
        and args.results_database.parent == args.output_dir,
        "Fresh output directory and contained results DB required",
    )
    authorities = [
        args.repo_root,
        args.artifact_root,
        args.source_pdf_root,
        args.corpus_index.parent,
        args.source_page_database.parent,
    ]
    require(
        not any(
            args.output_dir == p
            or args.output_dir.is_relative_to(p)
            or p.is_relative_to(args.output_dir)
            for p in authorities
        ),
        "Output overlaps source authority",
    )
    if args.base_cluster_cache is not None:
        _safe_path(args.base_cluster_cache)
        require(
            not any(args.base_cluster_cache.is_relative_to(p) for p in authorities)
            and args.base_cluster_cache != args.results_database,
            "Cache overlaps source/results authority",
        )
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    documents, selected_ids = _documents_v1(index, args.artifact_root)
    scope_path = getattr(args, "source_page_scope", PAGE_SCOPE_PATH)
    scope_rows = _page_scope_v1(scope_path)
    document_limit = getattr(args, "document_limit", None)
    documents, diagnostic_ordinals = _diagnostic_documents_v1(
        documents, document_limit=document_limit,
        document_ordinals=getattr(args, "document_ordinals", None),
    )
    specs, compiled = _compile_specs_v1()
    _repair_render_bindings_v1(compiled)
    implementation_paths = [
        Path(__file__).resolve(),
        ROOT / "src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py",
        *(ROOT / p for p in SHARED_PINS),
        *SPEC_PATHS.values(),
        RENDER_BINDINGS_PATH,
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_income_tax_source_page_loader_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_financial_page_json_v1.py",
        ROOT / "src/bctc_ai/source_structure/contracts_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        scope_path,
    ]
    implementation_paths = list(dict.fromkeys([
        *implementation_paths,
        *(ROOT / "src/bctc_ai" / relative for relative in _PERIOD_INVENTORY_DEPENDENCY_PATHS),
    ]))
    implementation_refs = [generic._file_ref(p) for p in implementation_paths]
    authority_paths = [args.corpus_index]
    for document in documents:
        authority_paths.extend(
            generic._content_ref(args.artifact_root, document["index_document"][name])
            for name in ("document_manifest_ref", "selection_ref")
        )
    authority_refs = [generic._file_ref(p) for p in authority_paths]
    pdf_checked, repair_ids = [], []
    cache = BaseClusterCache(args.base_cluster_cache)
    try:
        with _authenticated_source_v1(args.source_page_database, index["database_ref"]) as database:
            for document in documents:
                source = document["manifest"]["document"]
                path = _safe_path(args.source_pdf_root / source["source_logical_name"])
                require(
                    path.is_file()
                    and path.stat().st_size == source["source_size_bytes"]
                    and generic._sha256(path) == source["source_sha256"],
                    "Source PDF missing/hash/byte mismatch: " + str(path),
                )
                import fitz

                with fitz.open(path) as source_pdf:
                    coverage = _check_page_scope_v1(document, len(source_pdf), scope_rows)
                pdf_checked.append(
                    {**source, **coverage, "status": "PASS_BYTES_ONLY_NOT_VISUAL_AUDIT"}
                )
                if any(
                    r["pdf_source"]["sha256"] == source["source_sha256"]
                    for r in compiled["income_tax_source_repairs"]
                ):
                    loaded = load_income_tax_source_page_json_versions_v1(
                        database, page_json_version_ids=document["ids"]
                    )
                    repair_ids.extend(_authenticate_repairs_v1(document, loaded, compiled, path))
            indexed, trials, timing = _evaluate_stream_v1(
                database, documents, compiled, cache=cache, implementation_refs=implementation_refs
            )
            sweep = build_gemini_json_flat_family_sweep_v1(
                corpus_manifest_index_id=index["corpus_manifest_index_id"],
                topology_spec=specs["topology"],
                evaluation_spec=specs["evaluation"],
                schema_binding_spec=specs["schema"],
                trials=trials,
                indexed_query_evidence=indexed,
            )
            validate_gemini_json_flat_family_sweep_v1(sweep)
            observation = validate_source_observation_mapping_contract_v1(sweep)
            require(
                sweep["metrics"]["document_count"] == len(documents),
                "Sweep document denominator differs",
            )
            if diagnostic_ordinals is None:
                args.output_dir.mkdir(mode=0o700)
                started = time.perf_counter()
                stored = ingest_gemini_accounting_family_sweep_v1(
                    args.results_database,
                    sweep=sweep,
                    corpus_index_ref=generic._file_ref(args.corpus_index),
                    implementation_refs=implementation_refs,
                    run_kind="EXPERIMENTAL",
                    source_page_database=database,
                    selected_page_json_version_ids=selected_ids,
                    corpus_artifact_root=args.artifact_root,
                    source_replay_adapter=replay_income_tax_trials_from_source_v1,
                    source_replay_adapter_ref=generic._file_ref(Path(__file__).resolve()),
                )
                timing["cold_source_replay_and_persistence_seconds"] = time.perf_counter() - started
                reloaded = load_gemini_accounting_family_sweep_v1(
                    args.results_database, stored["family_run_id"]
                )
                require(
                    same_typed_json_v1(reloaded, sweep), "Persisted sweep does not reload exactly"
                )
                validate_source_observation_mapping_contract_v1(reloaded)
                with sqlite3.connect(args.results_database) as connection:
                    require(
                        connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
                        and connection.execute("PRAGMA foreign_key_check").fetchall() == [],
                        "Results SQLite integrity failed",
                    )
            for source in pdf_checked:
                path = _safe_path(args.source_pdf_root / source["source_logical_name"])
                require(
                    path.stat().st_size == source["source_size_bytes"]
                    and generic._sha256(path) == source["source_sha256"],
                    "Source PDF bytes changed during replay: " + str(path),
                )
    finally:
        cache.close()
    _assert_shared_pins_v1()
    require(
        implementation_refs == [generic._file_ref(p) for p in implementation_paths],
        "Family/spec/storage bytes changed during run",
    )
    require(
        authority_refs == [generic._file_ref(p) for p in authority_paths],
        "Index/immutable manifest/selection bytes changed during run",
    )
    if diagnostic_ordinals is not None:
        material = {
            "format_version": "INCOME_TAX_BOUNDED_DIAGNOSTIC_V1",
            "family_id": FAMILY_ID,
            "declared_corpus_manifest_index_id": index["corpus_manifest_index_id"],
            "complete_corpus_execution": False,
            "evaluated_corpus_document_ordinals": diagnostic_ordinals,
            "persistence_performed": False,
            "independent_cold_source_replay_performed": False,
            "terminal_or_final_acceptance_claimed": False,
            "pdf_visual_residual_audit": "REQUIRED_NOT_PERFORMED",
            "metrics": sweep["metrics"],
            "trials": trials,
            "indexed_query_evidence": indexed,
            "timing": timing,
            "source_observation_contract": observation,
            "pdf_source_byte_bindings": pdf_checked,
            "authenticated_repair_ids": repair_ids,
            "implementation_refs": implementation_refs,
            "immutable_input_refs": authority_refs,
        }
        material["diagnostic_id"] = "gjitfarunv1:bounded:" + canonical_json_sha256_v1(material)
        args.output_dir.mkdir(mode=0o700)
        generic._write_once(args.output_dir / "income-tax-bounded-diagnostic.json", material)
        return {
            "disposition": "SUCCEEDED_BOUNDED_DIAGNOSTIC_NOT_ACCEPTANCE",
            "diagnostic_id": material["diagnostic_id"],
            "metrics": sweep["metrics"],
            "timing": timing,
            "persistence_performed": False,
            "diagnostic_ref": generic._file_ref(args.output_dir / "income-tax-bounded-diagnostic.json"),
        }
    output = args.output_dir / "income-tax-sweep.json"
    generic._write_once(output, sweep)
    export = record_gemini_accounting_family_export_v1(
        args.results_database, family_run_id=stored["family_run_id"], output_path=output
    )
    audit = {
        "family_id": FAMILY_ID,
        "format_version": "INCOME_TAX_OFFLINE_DIAGNOSTIC_AUDIT_V1",
        "run_kind": "EXPERIMENTAL",
        "sweep_id": sweep["sweep_id"],
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "timing": timing,
        "source_observation_contract": observation,
        "pdf_source_byte_bindings": pdf_checked,
        "authenticated_repair_ids": repair_ids,
        "selected_page_ids_sha256": canonical_json_sha256_v1(selected_ids),
        "implementation_refs": implementation_refs,
        "immutable_input_refs": authority_refs,
        "cold_source_replay": "PASS_EXACT_INDEPENDENT_STORAGE_QUERY_NO_CACHE",
        "results_reload": "PASS_EXACT",
        "pdf_visual_residual_audit": "REQUIRED_NOT_PERFORMED",
        "terminal_or_final_acceptance_claimed": False,
        "provider_calls_performed": False,
        "cache_is_acceptance_authority": False,
        "residuals": [
            {
                k: t[k]
                for k in (
                    "document_ordinal",
                    "source_logical_name",
                    "source_sha256",
                    "status",
                    "reasons",
                )
            }
            for t in trials
            if t["status"] != READY
        ],
    }
    audit["audit_id"] = "gjitfarunv1:audit:" + canonical_json_sha256_v1(audit)
    generic._write_once(args.output_dir / "income-tax-audit.json", audit)
    return {
        "disposition": "SUCCEEDED_DIAGNOSTIC_NOT_TERMINAL",
        "sweep_id": sweep["sweep_id"],
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "output_ref": export,
        "audit_id": audit["audit_id"],
        "timing": timing,
    }


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repo-root",
        "corpus-index",
        "source-page-database",
        "artifact-root",
        "source-pdf-root",
        "output-dir",
        "results-database",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--base-cluster-cache", type=Path)
    parser.add_argument("--source-page-scope", type=Path, default=PAGE_SCOPE_PATH)
    subset = parser.add_mutually_exclusive_group()
    subset.add_argument(
        "--document-limit",
        type=int,
        help="Evaluate the first N documents only; no persistence, cold replay or corpus acceptance claim",
    )
    subset.add_argument(
        "--document-ordinals", type=int, nargs="+",
        help="Evaluate these ascending immutable-index positions only; diagnostic without persistence or corpus acceptance",
    )
    return parser


def main():
    require(
        sys.platform.startswith("linux")
        and sys.version_info[:2] == (3, 12)
        and sys.dont_write_bytecode,
        "Linux Python3.12-B required",
    )
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
