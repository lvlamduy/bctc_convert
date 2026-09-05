#!/usr/bin/env python3
"""Run Family 24 over one authenticated current selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import sys
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

from bctc_ai.evaluation.gemini_json_entrusted_investment_risk_capital_family_v1 import (  # noqa: E402
    FAMILY_ID,
    build_gemini_json_entrusted_investment_risk_capital_indexed_query_evidence_v1,
    build_gemini_json_entrusted_investment_risk_capital_trials_v1,
    compile_gemini_json_entrusted_investment_risk_capital_family_specs_v1,
    validate_gemini_json_entrusted_investment_risk_capital_replay_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    FORMAT_VERSION as HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
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

AUDIT_FORMAT_VERSION = "GEMINI_JSON_ENTRUSTED_INVESTMENT_RISK_CAPITAL_EXPERIMENTAL_AUDIT_V1"
PDF_RESIDUAL_FORMAT_VERSION = "ENTRUSTED_INVESTMENT_RISK_CAPITAL_PDF_RESIDUAL_AUDIT_SPEC_V1"
PINNED_HISTORICAL_ORACLES = generic.PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_HISTORICAL_ORACLES
TOPOLOGY_SPEC_PATH = (
    ROOT / "config/families/tm-entrusted-investment-risk-capital-topology-v1.json"
)
EVALUATION_SPEC_PATH = (
    ROOT / "config/families/tm-entrusted-investment-risk-capital-evaluation-v1.json"
)
SCHEMA_BINDING_SPEC_PATH = (
    ROOT
    / "config/families/tm-entrusted-investment-risk-capital-schema-binding-v1.json"
)
SOURCE_REPAIR_SPEC_PATH = (
    ROOT
    / "config/families/tm-entrusted-investment-risk-capital-source-repair-v1.json"
)


class RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error(RuntimeError):
    """The Family-24 current-corpus run or its evidence drifted."""


def _error(message: str) -> RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error:
    return RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error(message)


def _sha256_bytes(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _source_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if not path.is_relative_to(resolved_root) or path.is_symlink() or not path.is_file():
        raise _error("Family-24 source PDF path is unavailable or escapes its root")
    return path


def _authenticate_source_repairs_v1(
    *,
    repairs: list[dict[str, Any]],
    index: dict[str, Any],
    selected_page_axis: list[dict[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    documents = {item["source_sha256"]: item for item in index["documents"]}
    selected_pages = {item["page_json_version_id"]: item for item in selected_page_axis}
    authenticated_sources: set[str] = set()
    rendered: dict[tuple[str, int], str] = {}
    checked = []
    for repair in repairs:
        source_sha256 = repair["source_sha256"]
        document = documents.get(source_sha256)
        if document is None:
            continue
        page = selected_pages.get(repair["locator"]["page_json_version_id"])
        if (
            page is None
            or page.get("source_sha256") != source_sha256
            or page.get("physical_page") != repair["locator"]["physical_page"]
        ):
            raise _error("Family-24 source repair is outside its current selected source")
        path = _source_path(source_pdf_root, document["relative_path"])
        if source_sha256 not in authenticated_sources:
            if (
                path.stat().st_size != document["source_size_bytes"]
                or _sha256_bytes(path) != source_sha256
            ):
                raise _error("Family-24 source-repair PDF bytes drifted")
            authenticated_sources.add(source_sha256)
        physical_page = repair["locator"]["physical_page"]
        cache_key = (source_sha256, physical_page)
        actual_render_sha256 = rendered.get(cache_key)
        if actual_render_sha256 is None:
            with fitz.open(path) as pdf:
                if physical_page > len(pdf):
                    raise _error("Family-24 source-repair page is outside its PDF")
                pixmap = pdf[physical_page - 1].get_pixmap(
                    matrix=fitz.Matrix(2, 2), colorspace=fitz.csRGB, alpha=False
                )
                actual_render_sha256 = sha256(pixmap.tobytes("png")).hexdigest()
            rendered[cache_key] = actual_render_sha256
        if actual_render_sha256 != repair["pdf_page_render_sha256"]:
            raise _error("Family-24 source-repair PDF page render drifted")
        checked.append(
            {
                "physical_page": physical_page,
                "repair_id": repair["repair_id"],
                "repair_kind": repair["repair_kind"],
                "source_logical_name": document["relative_path"],
                "source_sha256": source_sha256,
                "verified_pdf_page_render_sha256": actual_render_sha256,
            }
        )
    return checked


def replay_entrusted_investment_risk_capital_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query, adapt, evaluate, and replay the complete Family-24 axis."""

    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    base_compiled = compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, schema
    )
    if not same_typed_json_v1(base_compiled, compiled_specs):
        raise _error("Family-24 source replay declarative specs drifted")
    family_compiled = (
        compile_gemini_json_entrusted_investment_risk_capital_family_specs_v1(
            topology,
            evaluation,
            schema,
            generic._json(SOURCE_REPAIR_SPEC_PATH),
        )
    )
    base_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    page_json_by_document = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=base_indexed["selected_page_axis"],
    )
    adapted_indexed = (
        build_gemini_json_entrusted_investment_risk_capital_indexed_query_evidence_v1(
            base_indexed_query_evidence=base_indexed,
            page_json_by_document=page_json_by_document,
            compiled_specs=family_compiled,
        )
    )
    if not same_typed_json_v1(adapted_indexed, indexed_query_evidence):
        raise _error("Family-24 source replay rebuilt different indexed query evidence")
    trials = build_gemini_json_entrusted_investment_risk_capital_trials_v1(
        indexed_query_evidence=adapted_indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=family_compiled,
    )
    replayed = validate_gemini_json_entrusted_investment_risk_capital_replay_v1(
        base_indexed_query_evidence=base_indexed,
        indexed_query_evidence=adapted_indexed,
        trials=trials,
        page_json_by_document=page_json_by_document,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(replayed, trials):
        raise _error("Family-24 source replay returned a different trial axis")
    return replayed


def _validate_pdf_residual_spec_v1(value: Any) -> dict[str, Any]:
    expected_contract = {
        "alpha": False,
        "colorspace": "RGB",
        "format": "PNG",
        "matrix": [1, 1],
        "renderer": "PyMuPDF",
        "scope": ("EVERY_PRIMARY_BALANCE_STATEMENT_PAGE_FOR_EVERY_NOT_OBSERVED_DOCUMENT"),
        "visual_disposition_rule": ("NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY24_ROOT_ROW"),
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
        or value.get("review_contract") != expected_contract
        or type(value.get("residuals")) is not list
        or not value["residuals"]
    ):
        raise _error("Family-24 PDF residual audit spec is invalid")
    prior = 0
    sources: set[str] = set()
    for residual in value["residuals"]:
        fields = {
            "balance_sheet_page_axis",
            "disposition",
            "document_ordinal",
            "residual_audit_id",
            "source_logical_name",
            "source_sha256",
            "source_size_bytes",
        }
        if (
            type(residual) is not dict
            or set(residual) != fields
            or residual.get("disposition")
            != "TRUE_NOT_OBSERVED_NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY24_ROOT"
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior
            or type(residual.get("source_logical_name")) is not str
            or type(residual.get("source_sha256")) is not str
            or len(residual["source_sha256"]) != 64
            or residual["source_sha256"] in sources
            or type(residual.get("source_size_bytes")) is not int
            or residual["source_size_bytes"] <= 0
            or type(residual.get("balance_sheet_page_axis")) is not list
            or not residual["balance_sheet_page_axis"]
        ):
            raise _error("Family-24 PDF residual record is invalid or unordered")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "geircfav1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-24 PDF residual record identity drifted")
        page_numbers = []
        for page in residual["balance_sheet_page_axis"]:
            if (
                type(page) is not dict
                or set(page)
                != {
                    "page_json_version_id",
                    "pdf_page_render_sha256",
                    "physical_page",
                }
                or type(page.get("page_json_version_id")) is not str
                or type(page.get("pdf_page_render_sha256")) is not str
                or len(page["pdf_page_render_sha256"]) != 64
                or type(page.get("physical_page")) is not int
                or page["physical_page"] <= 0
            ):
                raise _error("Family-24 PDF residual page record is invalid")
            page_numbers.append(page["physical_page"])
        if page_numbers != sorted(set(page_numbers)):
            raise _error("Family-24 PDF residual page axis is not unique and ordered")
        prior = residual["document_ordinal"]
        sources.add(residual["source_sha256"])
    return canonical_clone_v1(value)


def _authenticate_pdf_residuals_v1(
    *,
    spec: dict[str, Any],
    index: dict[str, Any],
    selected_page_axis: list[dict[str, Any]],
    trials: list[dict[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    checked_spec = _validate_pdf_residual_spec_v1(spec)
    if checked_spec["corpus_manifest_index_id"] != index["corpus_manifest_index_id"]:
        raise _error("Family-24 PDF residual audit is bound to another corpus")
    documents = {item["source_ordinal"]: item for item in index["documents"]}
    selected_pages = {item["page_json_version_id"]: item for item in selected_page_axis}
    expected_sources = {
        trial["source_sha256"] for trial in trials if trial["status"] == NOT_OBSERVED
    }
    actual_sources = {residual["source_sha256"] for residual in checked_spec["residuals"]}
    if any(trial["status"] == UNRESOLVED for trial in trials) or actual_sources != expected_sources:
        raise _error("Family-24 PDF residual axis does not exhaust current N/U trials")
    authenticated = []
    for residual in checked_spec["residuals"]:
        document = documents.get(residual["document_ordinal"])
        if (
            document is None
            or document["relative_path"] != residual["source_logical_name"]
            or document["source_sha256"] != residual["source_sha256"]
            or document["source_size_bytes"] != residual["source_size_bytes"]
        ):
            raise _error("Family-24 PDF residual source binding drifted")
        path = _source_path(source_pdf_root, document["relative_path"])
        if (
            path.stat().st_size != residual["source_size_bytes"]
            or _sha256_bytes(path) != residual["source_sha256"]
        ):
            raise _error("Family-24 PDF residual source PDF bytes drifted")
        render_axis = []
        with fitz.open(path) as pdf:
            for page in residual["balance_sheet_page_axis"]:
                if page["physical_page"] > len(pdf):
                    raise _error("Family-24 PDF residual page is outside its PDF")
                selected = selected_pages.get(page["page_json_version_id"])
                if (
                    selected is None
                    or selected.get("source_sha256") != residual["source_sha256"]
                    or selected.get("physical_page") != page["physical_page"]
                ):
                    raise _error("Family-24 PDF residual selected-page binding drifted")
                pixmap = pdf[page["physical_page"] - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                digest = sha256(pixmap.tobytes("png")).hexdigest()
                if digest != page["pdf_page_render_sha256"]:
                    raise _error("Family-24 PDF residual page render drifted")
                render_axis.append(canonical_clone_v1(page))
        authenticated.append(
            {
                "balance_sheet_page_axis": render_axis,
                "disposition": residual["disposition"],
                "document_ordinal": residual["document_ordinal"],
                "residual_audit_id": residual["residual_audit_id"],
                "source_logical_name": residual["source_logical_name"],
                "source_sha256": residual["source_sha256"],
            }
        )
    return authenticated


def _historical_policy_receipt_v1(
    *,
    index: dict[str, Any],
    selected_page_json_version_ids: list[str],
    indexed_query_evidence: dict[str, Any],
    trials: list[dict[str, Any]],
) -> dict[str, Any]:
    references = []
    rows = []
    for reference_index, reference in enumerate(PINNED_HISTORICAL_ORACLES):
        artifact = generic._json(ROOT / reference["path"])
        oracle_trials = artifact.get("trials")
        if type(oracle_trials) is not list or len(oracle_trials) != 8:
            raise _error("Family-24 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-24 historical oracle source identity is absent")
            rows.append(
                {
                    "oracle_ref_index": reference_index,
                    "source_sha256": source_sha256,
                }
            )
    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed_query_evidence["selected_document_axis"]
    }
    candidate_sources = [
        source_by_ordinal[cluster["document_ordinal"]]
        for cluster in indexed_query_evidence["accepted_clusters"]
    ]
    replay_sources = [trial["source_sha256"] for trial in trials if trial["candidate_count"] == 1]
    return audit_historical_comparator_policy_v1(
        policy=DISJOINT_EXPANSION,
        pinned_oracle_refs=references,
        normalized_oracle_rows=rows,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        current_manifest_page_json_version_ids=selected_page_json_version_ids,
        current_trials=trials,
        current_candidate_source_sha256s=candidate_sources,
        current_replay_source_sha256s=replay_sources,
        current_selected_page_json_version_ids=selected_page_json_version_ids,
        strict_compare=None,
    )


def _query_recovery_axis(indexed_query_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    source_by_ordinal = {
        document["document_ordinal"]: document
        for document in indexed_query_evidence["selected_document_axis"]
    }
    axis = []
    for cluster in indexed_query_evidence["accepted_clusters"]:
        receipt = cluster.get("entrusted_investment_risk_capital_query_adapter_receipt")
        if receipt is None:
            continue
        document = source_by_ordinal[cluster["document_ordinal"]]
        axis.append(
            {
                "adapter_query_receipt": canonical_clone_v1(receipt),
                "document_ordinal": cluster["document_ordinal"],
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
            }
        )
    return axis


def _semantic_axes(trials: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    clusters = []
    equations = []
    mappings = []
    for trial in trials:
        if trial["status"] != READY:
            continue
        candidates = trial["candidates"]
        if type(candidates) is not list or len(candidates) != 1:
            raise _error("Family-24 ready trial does not bind one candidate")
        candidate = candidates[0]
        identity = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        clusters.append(
            {
                **identity,
                "candidate_id": candidate["candidate_id"],
                "component_regions": canonical_clone_v1(candidate["component_regions"]),
                "query_receipt_sha256": canonical_json_sha256_v1(
                    candidate["closure_receipt"]["query_receipt"]
                ),
            }
        )
        for mapping in candidate["mappings"]:
            mappings.append({**identity, "mapping": canonical_clone_v1(mapping)})
        for equation in candidate["closure_receipt"].get("equations", []):
            equations.append({**identity, "equation": canonical_clone_v1(equation)})
    return {"clusters": clusters, "equations": equations, "mappings": mappings}


def build_experimental_audit_v1(
    *,
    sweep: dict[str, Any],
    sweep_output: Path,
    index: dict[str, Any],
    selected_page_json_version_ids: list[str],
    base_indexed_query_evidence: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
    trials: list[dict[str, Any]],
    query_recoveries: list[dict[str, Any]],
    source_repairs: list[dict[str, Any]],
    pdf_residuals: list[dict[str, Any]],
    source_observation_contract: dict[str, Any],
    historical_policy_receipt: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    axes = _semantic_axes(trials)
    axes.update(
        {
            "historical_comparator": [],
            "pdf_residuals": canonical_clone_v1(pdf_residuals),
            "query_recoveries": canonical_clone_v1(query_recoveries),
            "source_repairs": canonical_clone_v1(source_repairs),
        }
    )
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": {
            "mapping_count": axis_counts["mappings"],
            "pdf_residual_count": axis_counts["pdf_residuals"],
            "query_recovery_count": axis_counts["query_recoveries"],
            "source_repair_count": axis_counts["source_repairs"],
        },
        "base_query_evidence_id": base_indexed_query_evidence["query_evidence_id"],
        "claim_boundary": (
            "AUTHENTICATED_CURRENT_SELECTED_JSON_AND_PDF_VISIBLE_FAMILY24_"
            "SCHEMA_MAPPING_PROPOSAL_ONLY_NO_PROVIDER_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": historical_policy_receipt,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            selected_page_json_version_ids
        ),
        "source_observation_contract": canonical_clone_v1(source_observation_contract),
        "spec_refs": canonical_clone_v1(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_metrics": canonical_clone_v1(sweep["metrics"]),
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "geircfav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "base_query_evidence_id",
        "claim_boundary",
        "format_version",
        "historical_comparator_policy_receipt",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "source_observation_contract",
        "spec_refs",
        "state",
        "sweep_metrics",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "equations",
        "historical_comparator",
        "mappings",
        "pdf_residuals",
        "query_recoveries",
        "source_repairs",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != axis_names
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("Family-24 experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    receipt = value.get("historical_comparator_policy_receipt")
    contract = value.get("source_observation_contract")
    metrics = value.get("audit_metrics")
    sweep_metrics = value.get("sweep_metrics")
    if (
        value.get("axis_counts") != counts
        or value.get("axis_sha256") != hashes
        or type(receipt) is not dict
        or receipt.get("format_version") != HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION
        or receipt.get("policy") != DISJOINT_EXPANSION
        or receipt.get("disposition") != NOT_APPLICABLE_DISJOINT_CORPUS
        or receipt.get("corpus_relation", {}).get("overlap_count") != 0
        or receipt.get("comparison_axis") != []
        or value["axes"]["historical_comparator"] != []
        or type(contract) is not dict
        or contract.get("status") != "PASS"
        or contract.get("violation_count") != 0
        or type(metrics) is not dict
        or type(sweep_metrics) is not dict
        or metrics.get("mapping_count") != counts["mappings"]
        or metrics.get("pdf_residual_count") != counts["pdf_residuals"]
        or metrics.get("query_recovery_count") != counts["query_recoveries"]
        or metrics.get("source_repair_count") != counts["source_repairs"]
        or sweep_metrics.get("mapping_count") != counts["mappings"]
        or sweep_metrics.get("not_observed_count") != counts["pdf_residuals"]
        or sweep_metrics.get("unresolved_count") != 0
    ):
        raise _error("Family-24 audit semantic gate drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != ("geircfav1:audit:" + canonical_json_sha256_v1(material)):
        raise _error("Family-24 experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def _assert_current_corpus(index: dict[str, Any]) -> None:
    if not index["documents"] or any(
        not ({"2025", "2026"} & set(Path(document["relative_path"]).parts))
        for document in index["documents"]
    ):
        raise _error("Family-24 conclusion corpus includes a pre-2025 document")


def _run_with_database(
    args: argparse.Namespace,
    *,
    index: dict[str, Any],
    database_guard: Any,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    base_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    page_json_by_document = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=base_indexed["selected_page_axis"],
    )
    indexed = build_gemini_json_entrusted_investment_risk_capital_indexed_query_evidence_v1(
        base_indexed_query_evidence=base_indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_entrusted_investment_risk_capital_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled,
    )
    replayed = validate_gemini_json_entrusted_investment_risk_capital_replay_v1(
        base_indexed_query_evidence=base_indexed,
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled,
    )
    if not same_typed_json_v1(replayed, trials):
        raise _error("Family-24 specialized replay returned a different trial axis")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    repairs = _authenticate_source_repairs_v1(
        repairs=compiled["entrusted_investment_risk_capital_source_repairs"],
        index=index,
        selected_page_axis=indexed["selected_page_axis"],
        source_pdf_root=args.source_pdf_root,
    )
    residuals = _authenticate_pdf_residuals_v1(
        spec=generic._json(args.pdf_residual_audit_spec),
        index=index,
        selected_page_axis=indexed["selected_page_axis"],
        trials=trials,
        source_pdf_root=args.source_pdf_root,
    )
    historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        index=index,
        selected_page_json_version_ids=selected_ids,
        base_indexed_query_evidence=base_indexed,
        indexed_query_evidence=indexed,
        trials=trials,
        query_recoveries=_query_recovery_axis(indexed),
        source_repairs=repairs,
        pdf_residuals=residuals,
        source_observation_contract=observation_contract,
        historical_policy_receipt=historical_receipt,
        spec_refs=spec_refs,
    )
    validate_experimental_audit_content_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    implementation_paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_entrusted_investment_risk_capital_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_entrusted_investment_risk_capital_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
        SOURCE_REPAIR_SPEC_PATH,
    )
    implementation_refs = [
        generic._file_ref(path, root=ROOT) for path in implementation_paths
    ]
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_entrusted_investment_risk_capital_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=implementation_refs,
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=(
            replay_entrusted_investment_risk_capital_trials_from_source_v1
        ),
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("Stored Family-24 sweep differs from authenticated evaluation")
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
        raise _error("Family-24 current-corpus runner requires DISJOINT_EXPANSION")
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_spec)
    compiled = compile_gemini_json_entrusted_investment_risk_capital_family_specs_v1(
        topology, evaluation, schema, source_repairs
    )
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "pdf_residual_audit": generic._file_ref(args.pdf_residual_audit_spec, root=ROOT),
        "schema_binding": generic._file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair": generic._file_ref(args.source_repair_spec, root=ROOT),
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
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--source-repair-spec", type=Path, required=True)
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
