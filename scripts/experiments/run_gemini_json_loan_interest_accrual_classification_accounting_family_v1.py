#!/usr/bin/env python3
"""Run Family 26 over one authenticated current selected-JSON corpus."""

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

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_loan_interest_accrual_classification_family_v1 import (  # noqa: E402
    FAMILY_ID,
    build_gemini_json_loan_interest_accrual_classification_indexed_query_evidence_v1,
    build_gemini_json_loan_interest_accrual_classification_trials_v1,
    build_loan_interest_accrual_cross_family_disjointness_receipt_v1,
    build_loan_interest_accrual_source_row_coverage_receipt_v1,
    compile_gemini_json_loan_interest_accrual_classification_family_specs_v1,
    validate_gemini_json_loan_interest_accrual_classification_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    UNRESOLVED,
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

AUDIT_FORMAT_VERSION = (
    "GEMINI_JSON_LOAN_INTEREST_ACCRUAL_CLASSIFICATION_EXPERIMENTAL_AUDIT_V1"
)
PDF_RESIDUAL_FORMAT_VERSION = (
    "LOAN_INTEREST_ACCRUAL_CLASSIFICATION_PDF_RESIDUAL_AUDIT_SPEC_V1"
)
PDF_VISIBLE_SOURCE_ROW_AUDIT_FORMAT_VERSION = (
    "LOAN_INTEREST_ACCRUAL_CLASSIFICATION_PDF_VISIBLE_SOURCE_ROW_RENDER_AUDIT_V2"
)
PDF_RENDER_CONTRACT = {
    "alpha": False,
    "colorspace": "RGB",
    "format": "PNG",
    "matrix": [1, 1],
    "renderer": "PyMuPDF",
}
TOPOLOGY_SPEC_PATH = (
    ROOT
    / "config/families/tm-loan-interest-accrual-classification-topology-v1.json"
)
EVALUATION_SPEC_PATH = (
    ROOT
    / "config/families/tm-loan-interest-accrual-classification-evaluation-v1.json"
)
SCHEMA_BINDING_SPEC_PATH = (
    ROOT
    / "config/families/tm-loan-interest-accrual-classification-schema-binding-v1.json"
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
PINNED_HISTORICAL_ORACLES = generic.PINNED_HISTORICAL_ORACLES


class RunGeminiJsonLoanInterestAccrualClassificationV1Error(RuntimeError):
    """The Family-26 run, evidence, or ownership boundary drifted."""


def _error(
    message: str,
) -> RunGeminiJsonLoanInterestAccrualClassificationV1Error:
    return RunGeminiJsonLoanInterestAccrualClassificationV1Error(message)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _assert_shared_implementation_pins_v1() -> None:
    actual = {
        SHARED_EVALUATOR_PATH: _sha256(SHARED_EVALUATOR_PATH),
        SHARED_RUNNER_PATH: _sha256(SHARED_RUNNER_PATH),
    }
    expected = {
        SHARED_EVALUATOR_PATH: PINNED_SHARED_EVALUATOR_SHA256,
        SHARED_RUNNER_PATH: PINNED_SHARED_RUNNER_SHA256,
    }
    drifted = [str(path) for path in expected if actual[path] != expected[path]]
    if drifted:
        raise _error("Family-26 shared implementation pin drifted: " + ",".join(drifted))


def _source_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if not path.is_relative_to(resolved_root) or path.is_symlink() or not path.is_file():
        raise _error("Family-26 source PDF path is unavailable or escapes its root")
    return path


def _assert_current_corpus(index: dict[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-26 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-26 conclusion corpus includes a pre-2025 document")


def _pdf_visible_audit_row_v1(
    item: dict[str, Any], *, axis_kind: str
) -> dict[str, Any]:
    material = {
        "axis_kind": axis_kind,
        "coverage": item["coverage"],
        "document_ordinal": item["document_ordinal"],
        "hierarchy_path_exact": canonical_clone_v1(
            item.get("hierarchy_path_exact", [])
        ),
        "label_exact": item.get("label_exact"),
        "page_json_version_id": item["page_json_version_id"],
        "physical_page": item["physical_page"],
        "report_norm_id": item.get("report_norm_id"),
        "role": item.get("role"),
        "row_id": item.get("row_id"),
        "row_ordinal": item["row_ordinal"],
        "section_id": item["section_id"],
        "source_logical_name": item["source_logical_name"],
        "source_sha256": item["source_sha256"],
        "table_id": item["table_id"],
        "values_exact": canonical_clone_v1(item.get("values_exact")),
    }
    return {
        **material,
        "coverage_row_id": canonical_json_sha256_v1(material),
    }


def _expected_pdf_visible_audit_rows_v1(
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    classified = coverage.get("source_row_axis")
    candidate_totals = coverage.get("candidate_table_total_row_axis")
    raw_target = coverage.get("raw_target_like_row_axis")
    if (
        type(classified) is not list
        or type(candidate_totals) is not list
        or type(raw_target) is not list
        or coverage.get("violation_count") != 0
    ):
        raise _error("Family-26 PDF-visible coverage receipt is invalid")
    rows = [
        _pdf_visible_audit_row_v1(item, axis_kind="CLASSIFIED_SOURCE_ROW")
        for item in classified
    ]
    covered_locators = {
        (
            item.get("source_sha256"),
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
            item.get("row_ordinal"),
        )
        for item in classified
    }
    rows.extend(
        _pdf_visible_audit_row_v1(
            item, axis_kind="CANDIDATE_TABLE_TOTAL_DISPOSITION"
        )
        for item in candidate_totals
        if (
            item.get("source_sha256"),
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
            item.get("row_ordinal"),
        )
        not in covered_locators
    )
    covered_locators.update(
        (
            item.get("source_sha256"),
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
            item.get("row_ordinal"),
        )
        for item in candidate_totals
    )
    rows.extend(
        _pdf_visible_audit_row_v1(
            item, axis_kind="RAW_TARGET_LIKE_SOURCE_ROW"
        )
        for item in raw_target
        if (
            item.get("source_sha256"),
            item.get("page_json_version_id"),
            item.get("section_id"),
            item.get("table_id"),
            item.get("row_ordinal"),
        )
        not in covered_locators
    )
    return sorted(rows, key=canonical_json_sha256_v1)


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
        if type(oracle_trials) is not list or not oracle_trials:
            raise _error("Family-26 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-26 historical oracle source identity is absent")
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
    replay_sources = [
        trial["source_sha256"]
        for trial in trials
        if trial["candidate_count"] == 1
    ]
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


def _validate_pdf_residual_spec_v1(value: Any) -> dict[str, Any]:
    expected_contract = {
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [1, 1],
            "renderer": "PyMuPDF",
        },
        "scope": "EVERY_PDF_PAGE_FOR_EVERY_NOT_OBSERVED_OR_UNRESOLVED_DOCUMENT",
        "visual_disposition_rule": (
            "NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY26_ROW_OR_EXPLICIT_SOURCE_AMBIGUITY"
        ),
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
    ):
        raise _error("Family-26 PDF residual audit spec is invalid")
    prior = 0
    for residual in value["residuals"]:
        fields = {
            "disposition",
            "document_ordinal",
            "pdf_page_axis",
            "residual_audit_id",
            "source_logical_name",
            "source_sha256",
            "source_size_bytes",
            "trial_status",
        }
        if (
            type(residual) is not dict
            or set(residual) != fields
            or residual.get("trial_status") not in {NOT_OBSERVED, UNRESOLVED}
            or type(residual.get("disposition")) is not str
            or not residual["disposition"].startswith("TRUE_")
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior
            or type(residual.get("pdf_page_axis")) is not list
            or not residual["pdf_page_axis"]
        ):
            raise _error("Family-26 PDF residual record is invalid or unordered")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "glicafv1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-26 PDF residual record identity drifted")
        prior = residual["document_ordinal"]
    return canonical_clone_v1(value)


def _authenticate_pdf_residuals_v1(
    *,
    spec: dict[str, Any],
    index: dict[str, Any],
    selected_page_axis: list[dict[str, Any]],
    trials: list[dict[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    checked = _validate_pdf_residual_spec_v1(spec)
    if checked["corpus_manifest_index_id"] != index["corpus_manifest_index_id"]:
        raise _error("Family-26 PDF residual audit binds another corpus")
    expected = {
        trial["source_sha256"]
        for trial in trials
        if trial["status"] in {NOT_OBSERVED, UNRESOLVED}
    }
    actual = {residual["source_sha256"] for residual in checked["residuals"]}
    if actual != expected:
        raise _error("Family-26 PDF residual audit does not exhaust every N/U trial")
    documents = {item["source_ordinal"]: item for item in index["documents"]}
    selected_by_source: dict[str, dict[int, str]] = {}
    for page in selected_page_axis:
        selected_by_source.setdefault(page["source_sha256"], {})[
            page["physical_page"]
        ] = page["page_json_version_id"]
    authenticated = []
    for residual in checked["residuals"]:
        document = documents.get(residual["document_ordinal"])
        trial = trials[residual["document_ordinal"] - 1]
        if (
            document is None
            or document["relative_path"] != residual["source_logical_name"]
            or document["source_sha256"] != residual["source_sha256"]
            or document["source_size_bytes"] != residual["source_size_bytes"]
            or trial["status"] != residual["trial_status"]
        ):
            raise _error("Family-26 PDF residual source/trial binding drifted")
        path = _source_path(source_pdf_root, document["relative_path"])
        if path.stat().st_size != document["source_size_bytes"] or _sha256(path) != document[
            "source_sha256"
        ]:
            raise _error("Family-26 PDF residual source bytes drifted")
        rendered = []
        with fitz.open(path) as pdf:
            if len(residual["pdf_page_axis"]) != len(pdf):
                raise _error("Family-26 residual does not cover every PDF page")
            for ordinal, page in enumerate(residual["pdf_page_axis"], start=1):
                if (
                    type(page) is not dict
                    or set(page)
                    != {
                        "page_json_version_id",
                        "pdf_page_render_sha256",
                        "physical_page",
                    }
                    or page.get("physical_page") != ordinal
                    or selected_by_source.get(residual["source_sha256"], {}).get(ordinal)
                    != page.get("page_json_version_id")
                ):
                    raise _error("Family-26 residual PDF page axis drifted")
                pixmap = pdf[ordinal - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                digest = sha256(pixmap.tobytes("png")).hexdigest()
                if digest != page.get("pdf_page_render_sha256"):
                    raise _error("Family-26 residual PDF render drifted")
                rendered.append(canonical_clone_v1(page))
        authenticated.append(
            {
                "disposition": residual["disposition"],
                "document_ordinal": residual["document_ordinal"],
                "pdf_page_axis": rendered,
                "residual_audit_id": residual["residual_audit_id"],
                "source_logical_name": residual["source_logical_name"],
                "source_sha256": residual["source_sha256"],
                "trial_status": residual["trial_status"],
            }
        )
    return authenticated


def _authenticate_pdf_visible_source_row_audit_v1(
    *,
    value: Any,
    index: dict[str, Any],
    source_row_coverage: dict[str, Any],
    source_pdf_root: Path,
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "corpus_manifest_index_id",
        "counts",
        "coverage_receipt_id",
        "format_version",
        "manual_exception_category_review_axis",
        "manual_exception_category_review_axis_sha256",
        "pdf_page_render_axis",
        "pdf_page_render_axis_sha256",
        "source_pdf_authentication_axis",
        "source_pdf_authentication_axis_sha256",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version")
        != PDF_VISIBLE_SOURCE_ROW_AUDIT_FORMAT_VERSION
        or value.get("corpus_manifest_index_id")
        != index["corpus_manifest_index_id"]
        or value.get("coverage_receipt_id")
        != source_row_coverage.get("receipt_id")
    ):
        raise _error("Family-26 PDF-visible source-row audit envelope drifted")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "audit_id"
    }
    if value.get("audit_id") != (
        "glicafv1:pdf-visible:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-26 PDF-visible source-row audit identity drifted")

    source_axis = value.get("source_pdf_authentication_axis")
    expected_source_axis = [
        {
            "document_ordinal": document["source_ordinal"],
            "source_logical_name": document["relative_path"],
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        }
        for document in index["documents"]
    ]
    if (
        not same_typed_json_v1(source_axis, expected_source_axis)
        or value.get("source_pdf_authentication_axis_sha256")
        != canonical_json_sha256_v1(expected_source_axis)
    ):
        raise _error("Family-26 PDF-visible source PDF axis drifted")
    expected_rows = _expected_pdf_visible_audit_rows_v1(source_row_coverage)
    expected_grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in expected_rows:
        key = (
            row["document_ordinal"],
            row["physical_page"],
            row["page_json_version_id"],
        )
        expected_grouped.setdefault(key, []).append(row)
    expected_grouped = {
        key: sorted(rows, key=canonical_json_sha256_v1)
        for key, rows in expected_grouped.items()
    }

    page_axis = value.get("pdf_page_render_axis")
    if (
        type(page_axis) is not list
        or value.get("pdf_page_render_axis_sha256")
        != canonical_json_sha256_v1(page_axis)
    ):
        raise _error("Family-26 PDF-visible page-render axis drifted")
    documents = {item["source_ordinal"]: item for item in index["documents"]}
    actual_keys = []
    rendered_by_source_page: dict[tuple[str, int], dict[str, Any]] = {}
    for page in page_axis:
        key = (
            page.get("document_ordinal") if type(page) is dict else None,
            page.get("physical_page") if type(page) is dict else None,
            page.get("page_json_version_id") if type(page) is dict else None,
        )
        document = documents.get(key[0])
        expected_page_rows = expected_grouped.get(key)
        if (
            type(page) is not dict
            or set(page)
            != {
                "document_ordinal",
                "page_json_version_id",
                "physical_page",
                "pixel_height",
                "pixel_width",
                "render_contract",
                "render_sha256",
                "source_logical_name",
                "source_row_axis",
                "source_row_axis_sha256",
                "source_sha256",
            }
            or document is None
            or expected_page_rows is None
            or not same_typed_json_v1(page.get("source_row_axis"), expected_page_rows)
            or page.get("source_row_axis_sha256")
            != canonical_json_sha256_v1(expected_page_rows)
            or page.get("render_contract") != PDF_RENDER_CONTRACT
            or page.get("source_logical_name") != document["relative_path"]
            or page.get("source_sha256") != document["source_sha256"]
            or type(key[1]) is not int
            or key[1] <= 0
        ):
            raise _error("Family-26 PDF-visible page source-row binding drifted")
        actual_keys.append(key)
        rendered_by_source_page[(document["source_sha256"], key[1])] = page
    if actual_keys != sorted(expected_grouped):
        raise _error("Family-26 PDF-visible page axis is incomplete or unordered")

    resolved_root = source_pdf_root.resolve()
    pages_by_ordinal: dict[int, list[dict[str, Any]]] = {}
    for page in page_axis:
        pages_by_ordinal.setdefault(page["document_ordinal"], []).append(page)
    for source in expected_source_axis:
        path = _source_path(resolved_root, source["source_logical_name"])
        if (
            path.stat().st_size != source["source_size_bytes"]
            or _sha256(path) != source["source_sha256"]
        ):
            raise _error("Family-26 PDF-visible source bytes drifted")
        pages = pages_by_ordinal.get(source["document_ordinal"], [])
        if not pages:
            continue
        with fitz.open(path) as pdf:
            for page in pages:
                physical_page = page["physical_page"]
                if physical_page > len(pdf):
                    raise _error("Family-26 PDF-visible page is outside source PDF")
                pixmap = pdf[physical_page - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                if (
                    pixmap.width != page.get("pixel_width")
                    or pixmap.height != page.get("pixel_height")
                    or sha256(pixmap.tobytes("png")).hexdigest()
                    != page.get("render_sha256")
                ):
                    raise _error("Family-26 PDF-visible page render drifted")

    manual_axis = value.get("manual_exception_category_review_axis")
    if (
        type(manual_axis) is not list
        or not manual_axis
        or value.get("manual_exception_category_review_axis_sha256")
        != canonical_json_sha256_v1(manual_axis)
    ):
        raise _error("Family-26 manual PDF review axis is absent or drifted")
    review_kinds = set()
    for item in manual_axis:
        page = rendered_by_source_page.get(
            (item.get("source_sha256", ""), item.get("physical_page", 0))
            if type(item) is dict
            else ("", 0)
        )
        if (
            type(item) is not dict
            or set(item)
            != {
                "document_ordinal",
                "evidence",
                "page_json_version_id",
                "physical_page",
                "render_sha256",
                "review_kind",
                "source_logical_name",
                "source_sha256",
            }
            or page is None
            or type(item.get("evidence")) is not str
            or not item["evidence"]
            or type(item.get("review_kind")) is not str
            or not item["review_kind"]
            or item["review_kind"] in review_kinds
            or item["document_ordinal"] != page["document_ordinal"]
            or item["page_json_version_id"] != page["page_json_version_id"]
            or item["render_sha256"] != page["render_sha256"]
            or item["source_logical_name"] != page["source_logical_name"]
        ):
            raise _error("Family-26 manual PDF review binding drifted")
        review_kinds.add(item["review_kind"])

    expected_counts = {
        "authenticated_source_pdfs": len(expected_source_axis),
        "manual_exception_category_pages": len(manual_axis),
        "rendered_source_row_pages": len(page_axis),
        "source_rows_bound_to_renders": len(expected_rows),
    }
    if value.get("counts") != expected_counts:
        raise _error("Family-26 PDF-visible source-row audit counts drifted")
    return {
        "audit_id": value["audit_id"],
        "authenticated": True,
        "counts": canonical_clone_v1(expected_counts),
        "coverage_receipt_id": value["coverage_receipt_id"],
        "manual_exception_category_review_axis_sha256": value[
            "manual_exception_category_review_axis_sha256"
        ],
        "pdf_page_render_axis_sha256": value["pdf_page_render_axis_sha256"],
        "source_pdf_authentication_axis_sha256": value[
            "source_pdf_authentication_axis_sha256"
        ],
        "uncovered_source_row_count": 0,
    }


def build_experimental_audit_v1(
    *,
    sweep: dict[str, Any],
    sweep_output: Path,
    indexed_query_evidence: dict[str, Any],
    observation_contract: dict[str, Any],
    source_row_coverage: dict[str, Any],
    cross_family_receipt: dict[str, Any],
    historical_receipt: dict[str, Any],
    pdf_visible_source_row_audit: dict[str, Any],
    pdf_residuals: list[dict[str, Any]],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    axes = {
        "mappings": [
            mapping for trial in sweep["trials"] for mapping in trial["mappings"]
        ],
        "residuals": pdf_residuals,
        "trials": sweep["trials"],
    }
    material = {
        "axis_counts": {key: len(value) for key, value in axes.items()},
        "axis_sha256": {
            key: canonical_json_sha256_v1(value) for key, value in axes.items()
        },
        "cross_family_disjointness_receipt": canonical_clone_v1(
            cross_family_receipt
        ),
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_receipt": canonical_clone_v1(historical_receipt),
        "indexed_query_receipt": canonical_clone_v1(
            indexed_query_evidence["query_receipt"]
        ),
        "pdf_residuals": canonical_clone_v1(pdf_residuals),
        "pdf_visible_source_row_audit_receipt": canonical_clone_v1(
            pdf_visible_source_row_audit
        ),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "source_row_coverage_receipt": canonical_clone_v1(source_row_coverage),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_output": str(sweep_output),
    }
    return {
        **material,
        "audit_id": "glicafauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("historical_comparator_receipt", {}).get("policy")
        != DISJOINT_EXPANSION
        or value.get("historical_comparator_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("cross_family_disjointness_receipt", {}).get("overlap_count") != 0
        or value.get("source_observation_contract", {}).get("violation_count") != 0
        or value.get("source_row_coverage_receipt", {}).get("violation_count") != 0
        or value.get("pdf_visible_source_row_audit_receipt", {}).get(
            "authenticated"
        )
        is not True
        or value.get("pdf_visible_source_row_audit_receipt", {}).get(
            "uncovered_source_row_count"
        )
        != 0
        or value.get("pdf_visible_source_row_audit_receipt", {}).get(
            "coverage_receipt_id"
        )
        != value.get("source_row_coverage_receipt", {}).get("receipt_id")
    ):
        raise _error("Family-26 experimental audit content is invalid")
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "audit_id"}
    if value.get("audit_id") != "glicafauditv1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family-26 experimental audit identity drifted")
    return canonical_clone_v1(value)


def replay_loan_interest_accrual_classification_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query, adapt, evaluate, and replay the complete Family-26 axis."""

    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    base_compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if not same_typed_json_v1(base_compiled, compiled_specs):
        raise _error("Family-26 source replay declarative specs drifted")
    family_compiled = (
        compile_gemini_json_loan_interest_accrual_classification_family_specs_v1(
            topology, evaluation, schema
        )
    )
    base_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    pages = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=base_indexed["selected_page_axis"],
    )
    indexed = (
        build_gemini_json_loan_interest_accrual_classification_indexed_query_evidence_v1(
            base_indexed_query_evidence=base_indexed,
            page_json_by_document=pages,
            compiled_specs=family_compiled,
        )
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-26 source replay rebuilt different query evidence")
    trials = build_gemini_json_loan_interest_accrual_classification_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    return validate_gemini_json_loan_interest_accrual_classification_replay_v1(
        trials=trials,
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )


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
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=base_indexed["selected_page_axis"],
    )
    indexed = (
        build_gemini_json_loan_interest_accrual_classification_indexed_query_evidence_v1(
            base_indexed_query_evidence=base_indexed,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )
    )
    trials = build_gemini_json_loan_interest_accrual_classification_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    validate_gemini_json_loan_interest_accrual_classification_replay_v1(
        trials=trials,
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
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
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    source_row_coverage = (
        build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )
    )
    other_assets_sweep = generic._json(args.other_assets_sweep)
    validate_gemini_json_flat_family_sweep_v1(other_assets_sweep)
    cross_family_receipt = (
        build_loan_interest_accrual_cross_family_disjointness_receipt_v1(
            f26_sweep=sweep, other_assets_sweep=other_assets_sweep
        )
    )
    pdf_visible_source_row_audit = (
        _authenticate_pdf_visible_source_row_audit_v1(
            value=generic._json(args.pdf_visible_source_row_audit),
            index=index,
            source_row_coverage=source_row_coverage,
            source_pdf_root=args.source_pdf_root,
        )
    )
    pdf_residuals = _authenticate_pdf_residuals_v1(
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
        indexed_query_evidence=indexed,
        observation_contract=observation_contract,
        source_row_coverage=source_row_coverage,
        cross_family_receipt=cross_family_receipt,
        historical_receipt=historical_receipt,
        pdf_visible_source_row_audit=pdf_visible_source_row_audit,
        pdf_residuals=pdf_residuals,
        spec_refs=spec_refs,
    )
    validate_experimental_audit_content_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    implementation_paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_loan_interest_accrual_classification_accounting_family_v1.py",
        ROOT
        / "src/bctc_ai/evaluation/gemini_json_loan_interest_accrual_classification_family_v1.py",
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_variant_graph_engine_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_customer_deposit_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
    )
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_loan_interest_accrual_classification_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=[
            generic._file_ref(path, root=ROOT) for path in implementation_paths
        ],
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=(
            replay_loan_interest_accrual_classification_trials_from_source_v1
        ),
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("Stored Family-26 sweep differs from authenticated evaluation")
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
        raise _error("Family-26 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_implementation_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    compiled = (
        compile_gemini_json_loan_interest_accrual_classification_family_specs_v1(
            topology, evaluation, schema
        )
    )
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "other_assets_sweep": generic._file_ref(args.other_assets_sweep),
        "pdf_residual_audit": generic._file_ref(
            args.pdf_residual_audit_spec, root=ROOT
        ),
        "pdf_visible_source_row_audit": generic._file_ref(
            args.pdf_visible_source_row_audit
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
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--other-assets-sweep", type=Path, required=True)
    parser.add_argument("--pdf-residual-audit-spec", type=Path, required=True)
    parser.add_argument("--pdf-visible-source-row-audit", type=Path, required=True)
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
