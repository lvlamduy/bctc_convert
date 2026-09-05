#!/usr/bin/env python3
"""Run Family 32 over one authenticated selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import sys
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
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_trading_securities_activity_family_v1 import (  # noqa: E402
    FAMILY_ID,
    adapt_gemini_json_trading_securities_activity_indexed_query_evidence_v1,
    build_gemini_json_trading_securities_activity_region_query_receipt_v1,
    compile_gemini_json_trading_securities_activity_family_specs_v1,
    evaluate_gemini_json_trading_securities_activity_family_cluster_v1,
    validate_gemini_json_trading_securities_activity_family_candidate_replay_v1,
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
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_multitable_hierarchical_family_regions_v1,
)

AUDIT_FORMAT_VERSION = (
    "GEMINI_JSON_TRADING_SECURITIES_ACTIVITY_EXPERIMENTAL_AUDIT_V1"
)
PDF_RESIDUAL_FORMAT_VERSION = (
    "TRADING_SECURITIES_ACTIVITY_PDF_RESIDUAL_AUDIT_SPEC_V1"
)
TOPOLOGY_SPEC_PATH = (
    ROOT / "config/families/tm-trading-securities-activity-topology-v1.json"
)
EVALUATION_SPEC_PATH = (
    ROOT / "config/families/tm-trading-securities-activity-evaluation-v1.json"
)
SCHEMA_BINDING_SPEC_PATH = (
    ROOT / "config/families/tm-trading-securities-activity-schema-binding-v1.json"
)
SOURCE_REPAIR_PATH = (
    ROOT
    / "data/registered/gemini_json_trading_securities_activity_source_repairs_v1.json"
)
ADAPTER_PATH = (
    ROOT
    / "src/bctc_ai/evaluation/gemini_json_trading_securities_activity_family_v1.py"
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


class RunGeminiJsonTradingSecuritiesActivityV1Error(RuntimeError):
    """The Family-32 run, authentication, evidence, or replay drifted."""


def _error(message: str) -> RunGeminiJsonTradingSecuritiesActivityV1Error:
    return RunGeminiJsonTradingSecuritiesActivityV1Error(message)


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
        raise _error("Family-32 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-32 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-32 conclusion corpus is outside the current reporting scope")


def _validate_pdf_residual_spec_v1(value: Any) -> dict[str, Any]:
    expected_review_contract = {
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [1, 1],
            "renderer": "PyMuPDF",
        },
        "scope": (
            "EVERY_SELECTED_PRIMARY_INCOME_STATEMENT_PAGE_FOR_EVERY_"
            "NOT_OBSERVED_OR_UNRESOLVED_DOCUMENT"
        ),
        "visual_disposition_rule": (
            "DIRECT_SOURCE_PRESENTATION_ONLY_BLANK_PRESERVED_ABSENT_OMITTED_"
            "GENUINE_SOURCE_CONFLICT_UNRESOLVED"
        ),
    }
    allowed_dispositions = {
        "SOURCE_VISIBLE_FAMILY_ROOT_ALL_VALUE_LANES_TRULY_BLANK",
        "FAMILY_ROOT_NOT_PRESENT_IN_PRIMARY_INCOME_STATEMENT",
        "GENUINE_SOURCE_CONFLICT_ROOT_DASH_COMPONENT_PROVISION_NONZERO",
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
        or value.get("review_contract") != expected_review_contract
        or type(value.get("residuals")) is not list
    ):
        raise _error("Family-32 PDF residual audit spec is invalid")
    prior_ordinal = 0
    for residual in value["residuals"]:
        if (
            type(residual) is not dict
            or set(residual)
            != {
                "disposition",
                "document_ordinal",
                "primary_income_statement_page_axis",
                "reasons",
                "residual_audit_id",
                "source_logical_name",
                "source_sha256",
                "source_size_bytes",
                "status",
            }
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior_ordinal
            or residual.get("disposition") not in allowed_dispositions
            or type(residual.get("reasons")) is not list
            or type(residual.get("primary_income_statement_page_axis")) is not list
            or not residual["primary_income_statement_page_axis"]
        ):
            raise _error("Family-32 PDF residual record is invalid or unordered")
        if (
            residual["status"] == generic.NOT_OBSERVED
            and residual["reasons"] == []
            and residual["disposition"]
            in {
                "SOURCE_VISIBLE_FAMILY_ROOT_ALL_VALUE_LANES_TRULY_BLANK",
                "FAMILY_ROOT_NOT_PRESENT_IN_PRIMARY_INCOME_STATEMENT",
            }
        ):
            pass
        elif (
            residual["status"] == generic.UNRESOLVED
            and residual["reasons"]
            == ["SOURCE_VISIBLE_FAMILY_RESULT_COMPONENT_VETO_MISMATCH"]
            and residual["disposition"]
            == "GENUINE_SOURCE_CONFLICT_ROOT_DASH_COMPONENT_PROVISION_NONZERO"
        ):
            pass
        else:
            raise _error("Family-32 PDF residual status/disposition pairing is invalid")
        page_numbers = []
        page_ids = []
        for page in residual["primary_income_statement_page_axis"]:
            if (
                type(page) is not dict
                or set(page)
                != {
                    "page_json_version_id",
                    "pdf_page_render_sha256",
                    "physical_page",
                }
                or type(page.get("physical_page")) is not int
                or page["physical_page"] <= 0
                or type(page.get("page_json_version_id")) is not str
                or type(page.get("pdf_page_render_sha256")) is not str
                or len(page["pdf_page_render_sha256"]) != 64
            ):
                raise _error("Family-32 residual PDF page record is invalid")
            page_numbers.append(page["physical_page"])
            page_ids.append(page["page_json_version_id"])
        if page_numbers != sorted(set(page_numbers)) or len(page_ids) != len(
            set(page_ids)
        ):
            raise _error("Family-32 residual PDF page axis is not ordered and unique")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "gjtsapdfv1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-32 PDF residual record identity drifted")
        prior_ordinal = residual["document_ordinal"]
    return canonical_clone_v1(value)


def _authenticate_pdf_residuals_v1(
    *,
    spec: Mapping[str, Any],
    index: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, Mapping[str, Any]]],
    trials: Sequence[Mapping[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    checked = _validate_pdf_residual_spec_v1(spec)
    if checked["corpus_manifest_index_id"] != index["corpus_manifest_index_id"]:
        raise _error("Family-32 PDF residual audit binds another corpus")
    expected_trials = [trial for trial in trials if trial["status"] != generic.READY]
    if [trial["document_ordinal"] for trial in expected_trials] != [
        residual["document_ordinal"] for residual in checked["residuals"]
    ]:
        raise _error("Family-32 PDF residual audit does not exhaust every N/U trial")
    document_by_ordinal = {
        document["source_ordinal"]: document for document in index["documents"]
    }
    selected_by_id = {
        page["page_json_version_id"]: page for page in selected_page_axis
    }
    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-32 PDF residual source root is unavailable")
    authenticated = []
    for trial, residual in zip(expected_trials, checked["residuals"], strict=True):
        document = document_by_ordinal.get(residual["document_ordinal"])
        if (
            document is None
            or trial["source_logical_name"] != residual["source_logical_name"]
            or trial["source_sha256"] != residual["source_sha256"]
            or trial["status"] != residual["status"]
            or trial["reasons"] != residual["reasons"]
            or document["relative_path"] != residual["source_logical_name"]
            or document["source_sha256"] != residual["source_sha256"]
            or document["source_size_bytes"] != residual["source_size_bytes"]
        ):
            raise _error("Family-32 PDF residual source/trial binding drifted")
        expected_page_axis = []
        for page_json_version_id, page_json in page_json_by_document[
            residual["document_ordinal"]
        ].items():
            sections = page_json.get("sections")
            if type(sections) is not list or not any(
                type(section) is dict
                and section.get("content_kind") == "PRIMARY_STATEMENT"
                and section.get("statement_type") == "INCOME_STATEMENT"
                for section in sections
            ):
                continue
            selected = selected_by_id.get(page_json_version_id)
            if (
                selected is None
                or selected.get("source_sha256") != residual["source_sha256"]
            ):
                raise _error("Family-32 residual selected-page binding drifted")
            expected_page_axis.append(
                {
                    "page_json_version_id": page_json_version_id,
                    "physical_page": selected["physical_page"],
                }
            )
        expected_page_axis.sort(key=lambda item: item["physical_page"])
        actual_page_axis = [
            {
                "page_json_version_id": page["page_json_version_id"],
                "physical_page": page["physical_page"],
            }
            for page in residual["primary_income_statement_page_axis"]
        ]
        if actual_page_axis != expected_page_axis:
            raise _error(
                "Family-32 residual audit does not exhaust the primary income pages"
            )
        path = (root / document["relative_path"]).resolve()
        if (
            not path.is_relative_to(root)
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != document["source_size_bytes"]
            or _sha256(path) != document["source_sha256"]
        ):
            raise _error("Family-32 residual source PDF bytes drifted")
        render_axis = []
        with fitz.open(path) as pdf:
            for page in residual["primary_income_statement_page_axis"]:
                if page["physical_page"] > len(pdf):
                    raise _error("Family-32 residual page is outside its source PDF")
                pixmap = pdf[page["physical_page"] - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                digest = sha256(pixmap.tobytes("png")).hexdigest()
                if digest != page["pdf_page_render_sha256"]:
                    raise _error("Family-32 residual PDF render drifted")
                render_axis.append(canonical_clone_v1(page))
        authenticated.append(
            {
                **{
                    key: canonical_clone_v1(item)
                    for key, item in residual.items()
                    if key != "source_size_bytes"
                },
                "primary_income_statement_page_axis": render_axis,
            }
        )
    return authenticated


def _authenticate_source_repairs_v1(
    *,
    repairs: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-32 source-PDF root is unavailable")
    document_by_sha = {document["source_sha256"]: document for document in index["documents"]}
    page_axis = {
        (page["source_sha256"], page["page_json_version_id"]): page
        for page in selected_page_axis
    }
    payload_cache: dict[str, bytes] = {}
    render_cache: dict[tuple[str, int], dict[str, Any]] = {}
    checked = []
    for repair in repairs:
        document = document_by_sha.get(repair["source_sha256"])
        if document is None:
            continue
        if (
            document["relative_path"] != repair["source_logical_name"]
            or document["source_size_bytes"] != repair["source_size_bytes"]
        ):
            raise _error("Family-32 source-repair document binding drifted")
        selected_page = page_axis.get(
            (repair["source_sha256"], repair["page_json_version_id"])
        )
        if (
            selected_page is None
            or selected_page["physical_page"] != repair["physical_page"]
        ):
            raise _error("Family-32 source-repair selected page binding drifted")
        path = (root / document["relative_path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise _error("Family-32 source-repair PDF is unavailable")
        payload = payload_cache.get(repair["source_sha256"])
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != repair["source_size_bytes"]
                or sha256(payload).hexdigest() != repair["source_sha256"]
            ):
                raise _error("Family-32 source-repair PDF bytes drifted")
            payload_cache[repair["source_sha256"]] = payload
        render_key = (repair["source_sha256"], repair["physical_page"])
        rendered = render_cache.get(render_key)
        if rendered is None:
            try:
                with fitz.open(stream=payload, filetype="pdf") as pdf:
                    page_index = repair["physical_page"] - 1
                    if not 0 <= page_index < len(pdf):
                        raise _error("Family-32 source-repair page is outside its PDF")
                    pixmap = pdf[page_index].get_pixmap(
                        dpi=repair["page_image"]["render_dpi"],
                        colorspace=fitz.csRGB,
                        alpha=False,
                    )
                    image = pixmap.tobytes("png")
            except (RuntimeError, ValueError) as exc:
                raise _error("Family-32 source-repair PDF cannot be rendered") from exc
            rendered = {
                "height": pixmap.height,
                "media_type": "image/png",
                "render_dpi": repair["page_image"]["render_dpi"],
                "sha256": sha256(image).hexdigest(),
                "size_bytes": len(image),
                "width": pixmap.width,
            }
            render_cache[render_key] = rendered
        if not same_typed_json_v1(rendered, repair["page_image"]):
            raise _error("Family-32 source-repair PDF render drifted")
        material = {
            "page_image": canonical_clone_v1(rendered),
            "page_json_version_id": repair["page_json_version_id"],
            "repair_id": repair["repair_id"],
            "source_logical_name": repair["source_logical_name"],
            "source_sha256": repair["source_sha256"],
        }
        checked.append(
            {
                **material,
                "authentication_id": "gjtsarv1:auth:"
                + canonical_json_sha256_v1(material),
            }
        )
    return checked


def _build_trials_v1(
    *,
    indexed: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        candidates_by_ordinal[cluster["document_ordinal"]] = (
            evaluate_gemini_json_trading_securities_activity_family_cluster_v1(
                regions=regions,
                page_json_by_version=pages[cluster["document_ordinal"]],
                compiled_specs=compiled_specs,
                query_receipt=(
                    build_gemini_json_trading_securities_activity_region_query_receipt_v1(
                        regions
                    )
                ),
            )
        )
    return generic._trials(
        indexed=indexed, candidates_by_ordinal=candidates_by_ordinal
    )


def replay_trading_securities_activity_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    generic_compiled = compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, schema
    )
    if not same_typed_json_v1(generic_compiled, compiled_specs):
        raise _error("Family-32 source replay declarative specs drifted")
    family_compiled = compile_gemini_json_trading_securities_activity_family_specs_v1(
        topology, evaluation, schema, generic._json(SOURCE_REPAIR_PATH)
    )
    base = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    pages = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=base["selected_page_axis"],
    )
    indexed, _query_receipts = (
        adapt_gemini_json_trading_securities_activity_indexed_query_evidence_v1(
            base,
            page_json_by_document=pages,
            compiled_specs=family_compiled,
        )
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-32 source replay rebuilt different query evidence")
    trials = _build_trials_v1(
        indexed=indexed, pages=pages, compiled_specs=family_compiled
    )
    for trial, disposition in zip(
        trials, indexed["candidate_dispositions"], strict=True
    ):
        candidates = trial["candidates"]
        if candidates:
            cluster = disposition["cluster"]
            validate_gemini_json_trading_securities_activity_family_candidate_replay_v1(
                candidates[0],
                regions=cluster["component_regions"],
                page_json_by_version=pages[trial["document_ordinal"]],
                compiled_specs=family_compiled,
                query_receipt=(
                    build_gemini_json_trading_securities_activity_region_query_receipt_v1(
                        cluster["component_regions"]
                    )
                ),
            )
    return trials


def _audit_axes_v1(
    *,
    trials: Sequence[dict[str, Any]],
    indexed: Mapping[str, Any],
    query_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    pdf_residuals: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "equations": [],
        "mappings": [],
        "pdf_residuals": canonical_clone_v1(list(pdf_residuals)),
        "primary_query_recoveries": canonical_clone_v1(list(query_receipts)),
        "residuals": [],
        "source_repairs": [],
        "terminal_result_projections": [],
        "trials": canonical_clone_v1(list(trials)),
        "unit_corroborations": [],
    }
    disposition_by_ordinal = {
        item["document_ordinal"]: item for item in indexed["candidate_dispositions"]
    }
    for trial in trials:
        candidates = trial["candidates"]
        if trial["status"] != generic.READY:
            disposition = disposition_by_ordinal[trial["document_ordinal"]]
            axes["residuals"].append(
                {
                    "declared_money_table_inventory": canonical_clone_v1(
                        disposition["cluster"].get(
                            "declared_money_table_inventory", []
                        )
                    ),
                    "document_ordinal": trial["document_ordinal"],
                    "reasons": canonical_clone_v1(trial["reasons"]),
                    "source_logical_name": trial["source_logical_name"],
                    "source_sha256": trial["source_sha256"],
                    "status": trial["status"],
                }
            )
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        axes["mappings"].extend(canonical_clone_v1(candidate["mappings"]))
        axes["equations"].extend(
            canonical_clone_v1(candidate["closure_receipt"]["equations"])
        )
        adapter = candidate["closure_receipt"].get(
            "trading_securities_activity_adapter_receipt"
        )
        if type(adapter) is not dict:
            raise _error("Family-32 candidate adapter receipt is absent")
        axes["source_repairs"].extend(
            canonical_clone_v1(adapter["source_repair_receipts"])
        )
        axes["terminal_result_projections"].extend(
            canonical_clone_v1(adapter["terminal_result_projection_receipts"])
        )
        axes["unit_corroborations"].extend(
            canonical_clone_v1(adapter["unit_corroboration_receipts"])
        )
    axes["historical_comparator"] = []
    return axes


def _historical_policy_receipt_v1(
    *,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    references = []
    rows = []
    for reference_index, (reference, oracle) in enumerate(
        generic._historical_oracles(compiled_specs=compiled_specs)
    ):
        oracle_trials = oracle.get("trials")
        if type(oracle_trials) is not list or not oracle_trials:
            raise _error("Family-32 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-32 historical oracle source identity is absent")
            rows.append(
                {"oracle_ref_index": reference_index, "source_sha256": source_sha256}
            )
    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed["selected_document_axis"]
    }
    receipt = audit_historical_comparator_policy_v1(
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
            trial["source_sha256"] for trial in trials if trial["candidate_count"] == 1
        ],
        current_selected_page_json_version_ids=list(selected_ids),
        strict_compare=None,
    )
    if (
        receipt["disposition"] != NOT_APPLICABLE_DISJOINT_CORPUS
        or receipt["comparison_axis"] != []
    ):
        raise _error("Family-32 historical corpus is not disjoint")
    return references, receipt


def _build_audit_v1(
    *,
    sweep: Mapping[str, Any],
    index: Mapping[str, Any],
    output: Path,
    selected_ids: Sequence[str],
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    query_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
    source_authentications: Sequence[Mapping[str, Any]],
    observation_contract: Mapping[str, Any],
    pdf_residuals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    axes = _audit_axes_v1(
        trials=trials,
        indexed=indexed,
        query_receipts=query_receipts,
        compiled_specs=compiled_specs,
        pdf_residuals=pdf_residuals,
    )
    oracle_refs, historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {
        name: canonical_json_sha256_v1(axis) for name, axis in axes.items()
    }
    expected_repairs = sorted(
        repair["repair_id"]
        for repair in compiled_specs[
            "trading_securities_activity_source_repair_overlay"
        ]["repairs"]
        if repair["page_json_version_id"] in set(selected_ids)
    )
    applied_repairs = sorted(receipt["repair_id"] for receipt in axes["source_repairs"])
    authenticated_repairs = sorted(
        item["repair_id"] for item in source_authentications
    )
    if not (expected_repairs == applied_repairs == authenticated_repairs):
        raise _error("Family-32 repair application/authentication axis drifted")
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": canonical_clone_v1(
            historical_receipt
        ),
        "historical_oracle_refs": oracle_refs,
        "observation_contract": canonical_clone_v1(observation_contract),
        "query_evidence_id": indexed["query_evidence_id"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_ids)
        ),
        "source_authentication_axis": canonical_clone_v1(
            list(source_authentications)
        ),
        "source_authentication_axis_sha256": canonical_json_sha256_v1(
            source_authentications
        ),
        "spec_refs": canonical_clone_v1(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjtsaauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _validate_audit_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or value.get("historical_comparator_policy_receipt", {}).get("policy")
        != DISJOINT_EXPANSION
        or value.get("historical_comparator_policy_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("observation_contract", {}).get("violation_count") != 0
        or value.get("axis_counts")
        != {name: len(axis) for name, axis in value.get("axes", {}).items()}
        or value.get("axis_sha256")
        != {
            name: canonical_json_sha256_v1(axis)
            for name, axis in value.get("axes", {}).items()
        }
        or value.get("source_authentication_axis_sha256")
        != canonical_json_sha256_v1(value.get("source_authentication_axis", []))
        or len(value.get("axes", {}).get("pdf_residuals", []))
        != sum(
            trial.get("status") != generic.READY
            for trial in value.get("axes", {}).get("trials", [])
        )
    ):
        raise _error("Family-32 audit content is invalid")
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "audit_id"}
    if value["audit_id"] != "gjtsaauditv1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family-32 audit identity drifted")
    return canonical_clone_v1(value)


def _implementation_refs(pdf_residual_audit_spec: Path) -> list[dict[str, Any]]:
    paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_trading_securities_activity_accounting_family_v1.py",
        ADAPTER_PATH,
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
        SOURCE_REPAIR_PATH,
        pdf_residual_audit_spec,
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
    base = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=base["selected_page_axis"],
    )
    source_authentications = _authenticate_source_repairs_v1(
        repairs=compiled["trading_securities_activity_source_repair_overlay"]["repairs"],
        index=index,
        selected_page_axis=base["selected_page_axis"],
        source_pdf_root=args.source_pdf_root,
    )
    indexed, query_receipts = (
        adapt_gemini_json_trading_securities_activity_indexed_query_evidence_v1(
            base, page_json_by_document=pages, compiled_specs=compiled
        )
    )
    trials = _build_trials_v1(indexed=indexed, pages=pages, compiled_specs=compiled)
    replayed = replay_trading_securities_activity_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(selected_ids),
        compiled_specs=compile_gemini_json_flat_family_specs_v1(
            topology, evaluation, schema
        ),
        indexed_query_evidence=indexed,
    )
    if not same_typed_json_v1(replayed, trials):
        raise _error("Family-32 direct source replay returned different trials")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    if sweep["metrics"]["document_count"] != len(index["documents"]):
        raise _error("Family-32 sweep denominator drifted")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    pdf_residuals = _authenticate_pdf_residuals_v1(
        spec=generic._json(args.pdf_residual_audit_spec),
        index=index,
        selected_page_axis=base["selected_page_axis"],
        page_json_by_document=pages,
        trials=trials,
        source_pdf_root=args.source_pdf_root,
    )
    audit = _build_audit_v1(
        sweep=sweep,
        index=index,
        output=args.output,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        query_receipts=query_receipts,
        compiled_specs=compiled,
        spec_refs=spec_refs,
        source_authentications=source_authentications,
        observation_contract=observation_contract,
        pdf_residuals=pdf_residuals,
    )
    _validate_audit_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_trading_securities_activity_accounting_family_v1.py",
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
        source_replay_adapter=replay_trading_securities_activity_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-32 sweep differs from authenticated evaluation")
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
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": "EXPERIMENTAL",
        "source_authentication_axis_sha256": audit[
            "source_authentication_axis_sha256"
        ],
        "source_authentication_count": len(source_authentications),
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    compiled = compile_gemini_json_trading_securities_activity_family_specs_v1(
        topology, evaluation, schema, generic._json(args.source_repair_spec)
    )
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "pdf_residual_audit": generic._file_ref(
            args.pdf_residual_audit_spec, root=ROOT
        ),
        "schema_binding": generic._file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair_spec": generic._file_ref(args.source_repair_spec, root=ROOT),
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
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, default=TOPOLOGY_SPEC_PATH)
    parser.add_argument("--evaluation-spec", type=Path, default=EVALUATION_SPEC_PATH)
    parser.add_argument(
        "--schema-binding-spec", type=Path, default=SCHEMA_BINDING_SPEC_PATH
    )
    parser.add_argument("--source-repair-spec", type=Path, default=SOURCE_REPAIR_PATH)
    parser.add_argument("--pdf-residual-audit-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
