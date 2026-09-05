#!/usr/bin/env python3
"""Run Family 34 over one authenticated current selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts/experiments") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/experiments"))

import run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic  # noqa: E402

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    READY,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
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
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_multitable_hierarchical_family_regions_v1,
)

FAMILY_ID = "COMBINED_SECURITIES_NET"
AUDIT_FORMAT_VERSION = "GEMINI_JSON_COMBINED_SECURITIES_NET_EXPERIMENTAL_AUDIT_V1"
PDF_RESIDUAL_FORMAT_VERSION = "COMBINED_SECURITIES_NET_PDF_RESIDUAL_AUDIT_SPEC_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-combined-securities-net-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-combined-securities-net-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = (
    ROOT / "config/families/tm-combined-securities-net-schema-binding-v1.json"
)
SHARED_EVALUATOR_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"
)
SHARED_RUNNER_PATH = (
    ROOT
    / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
PINNED_SHARED_EVALUATOR_SHA256 = (
    "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
)
PINNED_SHARED_RUNNER_SHA256 = (
    "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"
)


class RunGeminiJsonCombinedSecuritiesNetV1Error(RuntimeError):
    """The Family-34 run, source evidence, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonCombinedSecuritiesNetV1Error:
    return RunGeminiJsonCombinedSecuritiesNetV1Error(message)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _assert_shared_pins_v1() -> None:
    expected = {
        SHARED_EVALUATOR_PATH: PINNED_SHARED_EVALUATOR_SHA256,
        SHARED_RUNNER_PATH: PINNED_SHARED_RUNNER_SHA256,
    }
    drifted = [str(path) for path, digest in expected.items() if _sha256(path) != digest]
    if drifted:
        raise _error("Family-34 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus_v1(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-34 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-34 conclusion corpus is outside the current reporting scope")


def _selected_region_page_axis_v1(
    indexed: Mapping[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    needed = {
        region["page_json_version_id"]
        for cluster in indexed["accepted_clusters"]
        for region in cluster["component_regions"]
    }
    axis = [
        canonical_clone_v1(item)
        for item in indexed["selected_page_axis"]
        if item["page_json_version_id"] in needed
    ]
    return [item["page_json_version_id"] for item in axis], axis


def _build_trials_from_indexed_v1(
    *,
    database: Path,
    indexed: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    region_ids, region_axis = _selected_region_page_axis_v1(indexed)
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=region_ids,
        selected_page_axis=region_axis,
    )
    candidates_by_ordinal: dict[int, dict[str, Any]] = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            regions
        )
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled_specs,
            query_receipt=receipt,
        )
        candidates_by_ordinal[ordinal] = (
            validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=pages[ordinal],
                compiled_specs=compiled_specs,
                query_receipt=receipt,
            )
        )
    return generic._trials(
        indexed=indexed, candidates_by_ordinal=candidates_by_ordinal
    )


def replay_combined_securities_net_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query and re-evaluate every Family-34 trial from source SQLite."""

    family_compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        generic._json(TOPOLOGY_SPEC_PATH),
        generic._json(EVALUATION_SPEC_PATH),
        generic._json(SCHEMA_BINDING_SPEC_PATH),
    )
    if not same_typed_json_v1(family_compiled, compiled_specs):
        raise _error("Family-34 source replay declarative specs drifted")
    indexed = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-34 source replay rebuilt different query evidence")
    return _build_trials_from_indexed_v1(
        database=source_page_database,
        indexed=indexed,
        compiled_specs=family_compiled,
    )


def _historical_policy_receipt_v1(
    *,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    references = []
    rows = []
    for reference_index, (reference, oracle) in enumerate(
        generic._historical_oracles(compiled_specs=compiled_specs)
    ):
        oracle_trials = oracle.get("trials")
        if type(oracle_trials) is not list or not oracle_trials:
            raise _error("Family-34 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-34 historical oracle source identity is absent")
            rows.append(
                {"oracle_ref_index": reference_index, "source_sha256": source_sha256}
            )
    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed["selected_document_axis"]
    }
    return audit_historical_comparator_policy_v1(
        policy=DISJOINT_EXPANSION,
        pinned_oracle_refs=references,
        normalized_oracle_rows=rows,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        current_manifest_page_json_version_ids=list(selected_ids),
        current_trials=list(trials),
        current_candidate_source_sha256s=[
            source_by_ordinal[cluster["document_ordinal"]]
            for cluster in indexed["accepted_clusters"]
        ],
        current_replay_source_sha256s=[
            trial["source_sha256"]
            for trial in trials
            if trial["candidate_count"] == 1
        ],
        current_selected_page_json_version_ids=list(selected_ids),
        strict_compare=None,
    )


def _normalize_pdf_text_v1(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", value.replace("đ", "d"))


_PDF_TARGET_PATTERNS = (
    re.compile(
        r"lai.{0,80}(?:lo.{0,20})?thuan.{0,160}chung khoan kinh doanh"
        r".{0,180}chung khoan dau tu"
    ),
    re.compile(r"net.{0,100}trading.{0,160}investment securit"),
)


def _pdf_text_summary_v1(pdf: fitz.Document) -> dict[str, Any]:
    hit_pages = []
    extractable = 0
    for page_ordinal, page in enumerate(pdf, start=1):
        text = page.get_text("text", sort=True)
        if text.strip():
            extractable += 1
        normalized = _normalize_pdf_text_v1(text)
        if any(pattern.search(normalized) is not None for pattern in _PDF_TARGET_PATTERNS):
            hit_pages.append(page_ordinal)
    return {
        "extractable_text_page_count": extractable,
        "pdf_page_count": len(pdf),
        "pdf_text_target_hit_pages": hit_pages,
    }


def _validate_pdf_residual_spec_v1(value: Any) -> dict[str, Any]:
    review_contract = {
        "mapping_rule": (
            "DIRECT_SOURCE_VISIBLE_COMBINED_RESULT_ONLY_NEVER_ADD_FAMILY32_AND_FAMILY33"
        ),
        "page_scope": (
            "EVERY_SELECTED_PRIMARY_INCOME_STATEMENT_PAGE_FOR_EVERY_NOT_OBSERVED_"
            "OR_UNRESOLVED_DOCUMENT"
        ),
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [1, 1],
            "renderer": "PyMuPDF",
        },
        "source_scope": "EVERY_SOURCE_PDF_FULL_DOCUMENT_TEXT_SCAN_AND_BYTE_AUTHENTICATION",
    }
    if (
        type(value) is not dict
        or set(value)
        != {
            "corpus_manifest_index_id",
            "family_id",
            "format_version",
            "residuals",
            "review_contract",
        }
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != PDF_RESIDUAL_FORMAT_VERSION
        or value.get("review_contract") != review_contract
        or type(value.get("residuals")) is not list
    ):
        raise _error("Family-34 PDF residual audit spec is invalid")
    prior_ordinal = 0
    for residual in value["residuals"]:
        if (
            type(residual) is not dict
            or set(residual)
            != {
                "disposition",
                "document_ordinal",
                "extractable_text_page_count",
                "pdf_page_count",
                "pdf_text_target_hit_pages",
                "reasons",
                "residual_audit_id",
                "review_page_axis",
                "source_logical_name",
                "source_sha256",
                "source_size_bytes",
                "status",
            }
            or residual.get("disposition")
            != "NO_DIRECT_COMBINED_SECURITIES_NET_RESULT_ROW_IN_BOUND_REPORT"
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior_ordinal
            or residual.get("status") != generic.NOT_OBSERVED
            or residual.get("reasons") != []
            or type(residual.get("pdf_page_count")) is not int
            or residual["pdf_page_count"] <= 0
            or type(residual.get("extractable_text_page_count")) is not int
            or not 0
            <= residual["extractable_text_page_count"]
            <= residual["pdf_page_count"]
            or residual.get("pdf_text_target_hit_pages") != []
            or type(residual.get("review_page_axis")) is not list
            or not residual["review_page_axis"]
        ):
            raise _error("Family-34 PDF residual record is invalid or unordered")
        page_numbers = []
        page_ids = []
        for page in residual["review_page_axis"]:
            if (
                type(page) is not dict
                or set(page)
                != {
                    "page_json_version_id",
                    "pdf_page_render_sha256",
                    "physical_page",
                }
                or type(page.get("page_json_version_id")) is not str
                or type(page.get("physical_page")) is not int
                or page["physical_page"] <= 0
                or type(page.get("pdf_page_render_sha256")) is not str
                or re.fullmatch(r"[0-9a-f]{64}", page["pdf_page_render_sha256"])
                is None
            ):
                raise _error("Family-34 PDF residual review page is invalid")
            page_numbers.append(page["physical_page"])
            page_ids.append(page["page_json_version_id"])
        if page_numbers != sorted(set(page_numbers)) or len(page_ids) != len(set(page_ids)):
            raise _error("Family-34 PDF residual review page axis is not ordered and unique")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "gjcsnpdfv1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-34 PDF residual record identity drifted")
        prior_ordinal = residual["document_ordinal"]
    return canonical_clone_v1(value)


def _primary_income_page_axis_v1(
    database: Path,
    *,
    selected_ids: Sequence[str],
    selected_page_axis: Sequence[Mapping[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    axis_by_version = {
        item["page_json_version_id"]: item for item in selected_page_axis
    }
    primary: dict[int, list[dict[str, Any]]] = defaultdict(list)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_family34_review_page("
            "selection_ordinal INTEGER PRIMARY KEY,page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_family34_review_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_family34_review_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            WHERE instr(CAST(version.canonical_json_bytes AS TEXT),
                        '\"statement_type\":\"INCOME_STATEMENT\"') > 0
            ORDER BY selected.selection_ordinal
            """
        )
        for page_json_version_id, payload in rows:
            page_json = json.loads(bytes(payload))
            sections = page_json.get("sections")
            if type(sections) is not list or not any(
                type(section) is dict
                and section.get("content_kind") == "PRIMARY_STATEMENT"
                and section.get("statement_type") == "INCOME_STATEMENT"
                for section in sections
            ):
                continue
            item = axis_by_version.get(page_json_version_id)
            if item is None:
                raise _error("Family-34 review page is outside selected frontier")
            primary[item["document_ordinal"]].append(
                {
                    "page_json_version_id": page_json_version_id,
                    "physical_page": item["physical_page"],
                }
            )
    finally:
        connection.close()
    for pages in primary.values():
        pages.sort(key=lambda item: item["physical_page"])
    return dict(primary)


def _authenticate_pdf_residuals_v1(
    *,
    spec: Mapping[str, Any],
    index: Mapping[str, Any],
    database: Path,
    selected_ids: Sequence[str],
    selected_page_axis: Sequence[Mapping[str, Any]],
    trials: Sequence[Mapping[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    checked = _validate_pdf_residual_spec_v1(spec)
    if checked["corpus_manifest_index_id"] != index["corpus_manifest_index_id"]:
        raise _error("Family-34 PDF residual audit binds another corpus")
    residual_trials = [trial for trial in trials if trial["status"] != READY]
    if [trial["document_ordinal"] for trial in residual_trials] != [
        residual["document_ordinal"] for residual in checked["residuals"]
    ]:
        raise _error("Family-34 PDF residual audit does not exhaust every N/U trial")
    document_by_ordinal = {
        document["source_ordinal"]: document for document in index["documents"]
    }
    expected_pages = _primary_income_page_axis_v1(
        database,
        selected_ids=selected_ids,
        selected_page_axis=selected_page_axis,
    )
    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-34 PDF residual source root is unavailable")
    authenticated = []
    for trial, residual in zip(residual_trials, checked["residuals"], strict=True):
        document = document_by_ordinal.get(residual["document_ordinal"])
        expected_axis = expected_pages.get(residual["document_ordinal"], [])
        actual_axis = [
            {
                "page_json_version_id": page["page_json_version_id"],
                "physical_page": page["physical_page"],
            }
            for page in residual["review_page_axis"]
        ]
        if (
            document is None
            or trial["source_logical_name"] != residual["source_logical_name"]
            or trial["source_sha256"] != residual["source_sha256"]
            or trial["status"] != residual["status"]
            or trial["reasons"] != residual["reasons"]
            or document["relative_path"] != residual["source_logical_name"]
            or document["source_sha256"] != residual["source_sha256"]
            or document["source_size_bytes"] != residual["source_size_bytes"]
            or actual_axis != expected_axis
        ):
            raise _error("Family-34 PDF residual source/trial/page binding drifted")
        path = (root / document["relative_path"]).resolve()
        if (
            not path.is_relative_to(root)
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != document["source_size_bytes"]
            or _sha256(path) != document["source_sha256"]
        ):
            raise _error("Family-34 PDF residual source bytes drifted")
        with fitz.open(path) as pdf:
            if _pdf_text_summary_v1(pdf) != {
                "extractable_text_page_count": residual[
                    "extractable_text_page_count"
                ],
                "pdf_page_count": residual["pdf_page_count"],
                "pdf_text_target_hit_pages": residual["pdf_text_target_hit_pages"],
            }:
                raise _error("Family-34 PDF residual full-document text scan drifted")
            render_axis = []
            for page in residual["review_page_axis"]:
                if page["physical_page"] > len(pdf):
                    raise _error("Family-34 review page is outside its source PDF")
                pixmap = pdf[page["physical_page"] - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                if (
                    sha256(pixmap.tobytes("png")).hexdigest()
                    != page["pdf_page_render_sha256"]
                ):
                    raise _error("Family-34 PDF residual render drifted")
                render_axis.append(canonical_clone_v1(page))
        authenticated.append(
            {
                **{
                    key: canonical_clone_v1(item)
                    for key, item in residual.items()
                    if key != "source_size_bytes"
                },
                "review_page_axis": render_axis,
            }
        )
    return authenticated


def _audit_axes_v1(
    *, trials: Sequence[dict[str, Any]], pdf_residuals: Sequence[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "clusters": [],
        "equations": [],
        "mappings": [],
        "pdf_residuals": canonical_clone_v1(list(pdf_residuals)),
        "source_only_rows": [],
        "trials": canonical_clone_v1(list(trials)),
    }
    for trial in trials:
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        axes["clusters"].append(canonical_clone_v1(candidate))
        axes["mappings"].extend(canonical_clone_v1(candidate.get("mappings", [])))
        closure = candidate.get("closure_receipt", {})
        axes["equations"].extend(canonical_clone_v1(closure.get("equations", [])))
        axes["source_only_rows"].extend(
            canonical_clone_v1(closure.get("source_only_rows", []))
        )
    return axes


def build_combined_securities_net_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    output: Path,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    pdf_residuals: Sequence[dict[str, Any]],
    historical_receipt: Mapping[str, Any],
    observation_contract: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    axes = _audit_axes_v1(trials=trials, pdf_residuals=pdf_residuals)
    material = {
        "axis_counts": {key: len(value) for key, value in axes.items()},
        "axis_sha256": {
            key: canonical_json_sha256_v1(value) for key, value in axes.items()
        },
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": canonical_clone_v1(
            historical_receipt
        ),
        "indexed_query_receipt": canonical_clone_v1(indexed["query_receipt"]),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_metrics": canonical_clone_v1(sweep["metrics"]),
        "sweep_output": str(output),
    }
    return {
        **material,
        "audit_id": "gjcsnauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_combined_securities_net_experimental_audit_v1(
    value: Any,
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axis_counts",
        "axis_sha256",
        "family_id",
        "format_version",
        "historical_comparator_policy_receipt",
        "indexed_query_receipt",
        "source_observation_contract",
        "spec_refs",
        "sweep_id",
        "sweep_metrics",
        "sweep_output",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("historical_comparator_policy_receipt", {}).get("policy")
        != DISJOINT_EXPANSION
        or value.get("historical_comparator_policy_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("historical_comparator_policy_receipt", {})
        .get("corpus_relation", {})
        .get("overlap_count")
        != 0
        or value.get("source_observation_contract", {}).get("status") != "PASS"
        or value.get("source_observation_contract", {}).get("violation_count") != 0
        or type(value.get("axis_counts")) is not dict
        or type(value.get("axis_sha256")) is not dict
        or set(value["axis_counts"])
        != {
            "clusters",
            "equations",
            "mappings",
            "pdf_residuals",
            "source_only_rows",
            "trials",
        }
        or set(value["axis_sha256"]) != set(value["axis_counts"])
        or any(
            type(count) is not int or count < 0
            for count in value["axis_counts"].values()
        )
        or any(
            type(digest) is not str
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for digest in value["axis_sha256"].values()
        )
        or value["axis_counts"]["pdf_residuals"]
        != value["sweep_metrics"]["not_observed_count"]
        + value["sweep_metrics"]["unresolved_count"]
        or value["axis_counts"]["trials"]
        != value["sweep_metrics"]["document_count"]
        or value["axis_counts"]["mappings"]
        != value["sweep_metrics"]["mapping_count"]
        or value["sweep_metrics"]["document_count"]
        != value["indexed_query_receipt"]["selected_document_count"]
    ):
        raise _error("Family-34 experimental audit content is invalid")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "audit_id"
    }
    if value.get("audit_id") != (
        "gjcsnauditv1:audit:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-34 experimental audit identity drifted")
    return canonical_clone_v1(value)


def _implementation_refs(pdf_residual_spec: Path) -> list[dict[str, Any]]:
    paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_combined_securities_net_accounting_family_v1.py",
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
        pdf_residual_spec,
    )
    return [generic._file_ref(path, root=ROOT) for path in paths]


def _run_with_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: Any,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    trials = _build_trials_from_indexed_v1(
        database=database, indexed=indexed, compiled_specs=compiled
    )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    if sweep["metrics"].get("document_count") != len(index["documents"]):
        raise _error("Family-34 current corpus denominator drifted")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled,
    )
    pdf_residuals = _authenticate_pdf_residuals_v1(
        spec=generic._json(args.pdf_residual_audit_spec),
        index=index,
        database=database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
        trials=trials,
        source_pdf_root=args.source_pdf_root,
    )
    audit = build_combined_securities_net_experimental_audit_v1(
        sweep=sweep,
        output=args.output,
        indexed=indexed,
        trials=trials,
        pdf_residuals=pdf_residuals,
        historical_receipt=historical_receipt,
        observation_contract=observation_contract,
        spec_refs=spec_refs,
    )
    validate_combined_securities_net_experimental_audit_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_combined_securities_net_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(args.pdf_residual_audit_spec),
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_combined_securities_net_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-34 sweep differs from authenticated evaluation")
    validate_source_observation_mapping_contract_v1(stored_sweep)
    output_ref = record_gemini_accounting_family_export_v1(
        args.results_database,
        family_run_id=stored["family_run_id"],
        output_path=args.output,
    )
    database_guard.validate()
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "family_run_id": stored["family_run_id"],
        "historical_comparator_policy": DISJOINT_EXPANSION,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": "EXPERIMENTAL",
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.historical_comparator_policy != DISJOINT_EXPANSION:
        raise _error("Family-34 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus_v1(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology, evaluation, schema
    )
    if compiled["topology"]["family_id"] != FAMILY_ID:
        raise _error("Family-34 runner received a different family")
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "pdf_residual_audit": generic._file_ref(
            args.pdf_residual_audit_spec, root=ROOT
        ),
        "schema_binding": generic._file_ref(args.schema_binding_spec, root=ROOT),
        "topology": generic._file_ref(args.topology_spec, root=ROOT),
    }
    with generic._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as database_guard:
        return _run_with_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
            spec_refs=spec_refs,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, default=TOPOLOGY_SPEC_PATH)
    parser.add_argument("--evaluation-spec", type=Path, default=EVALUATION_SPEC_PATH)
    parser.add_argument(
        "--schema-binding-spec", type=Path, default=SCHEMA_BINDING_SPEC_PATH
    )
    parser.add_argument("--pdf-residual-audit-spec", type=Path, required=True)
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(DISJOINT_EXPANSION,),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
