#!/usr/bin/env python3
"""Run Family 36 over one authenticated current selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts/experiments") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/experiments"))

import run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic  # noqa: E402

from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_operating_expense_family_v1 import (  # noqa: E402
    FAMILY_ID,
    build_gemini_json_operating_expense_indexed_query_evidence_v1,
    build_gemini_json_operating_expense_trials_v1,
    build_operating_expense_source_row_coverage_receipt_v1,
    compile_gemini_json_operating_expense_family_specs_v1,
    validate_gemini_json_operating_expense_replay_v1,
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

AUDIT_FORMAT_VERSION = "GEMINI_JSON_OPERATING_EXPENSE_EXPERIMENTAL_AUDIT_V1"
PDF_RESIDUAL_FORMAT_VERSION = "OPERATING_EXPENSE_PDF_RESIDUAL_AUDIT_SPEC_V1"
PDF_VISIBLE_SOURCE_ROW_AUDIT_FORMAT_VERSION = (
    "OPERATING_EXPENSE_PDF_VISIBLE_SOURCE_ROW_RENDER_AUDIT_V1"
)
PDF_RENDER_CONTRACT = {
    "alpha": False,
    "colorspace": "RGB",
    "format": "PNG",
    "matrix": [1, 1],
    "renderer": "PyMuPDF",
}
PDF_RESIDUAL_REVIEW_CONTRACT = {
    "render_contract": PDF_RENDER_CONTRACT,
    "scope": "EVERY_PDF_PAGE_FOR_EVERY_NOT_OBSERVED_OR_UNRESOLVED_DOCUMENT",
    "visual_disposition_rule": (
        "NO_PDF_VISIBLE_SCHEMA_MAPPABLE_OPERATING_EXPENSE_RESOLUTION_WITHOUT_INFERENCE"
    ),
}
PDF_RESIDUAL_DISPOSITION = (
    "GENUINE_SOURCE_AMBIGUITY_NO_EXACT_OPERATING_EXPENSE_MAPPING_WITHOUT_INFERENCE"
)
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-operating-expense-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-operating-expense-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = (
    ROOT / "config/families/tm-operating-expense-schema-binding-v1.json"
)
SOURCE_REPAIR_SPEC_PATH = (
    ROOT / "config/families/tm-operating-expense-source-repair-v1.json"
)
ADAPTER_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_operating_expense_family_v1.py"
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

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_JSON_VERSION_ID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")


class RunGeminiJsonOperatingExpenseV1Error(RuntimeError):
    """The Family-36 run, authentication, evidence, or replay drifted."""


def _error(message: str) -> RunGeminiJsonOperatingExpenseV1Error:
    return RunGeminiJsonOperatingExpenseV1Error(message)


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
        raise _error("Family-36 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-36 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-36 conclusion corpus is outside the current reporting scope")


def _source_path(source_pdf_root: Path, logical_name: str) -> Path:
    root = source_pdf_root.resolve()
    candidate = source_pdf_root / logical_name
    path = candidate.resolve()
    if (
        source_pdf_root.is_symlink()
        or not root.is_dir()
        or not path.is_relative_to(root)
        or candidate.is_symlink()
        or not path.is_file()
    ):
        raise _error("Family-36 source PDF path is unavailable or escapes its root")
    return path


def _authenticate_source_repairs_v1(
    *,
    compiled_specs: Mapping[str, Any],
    index: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    source_pdf_root: Path,
) -> dict[str, Any]:
    """Authenticate applicable repairs and type the out-of-corpus frontier."""

    repairs = compiled_specs.get("operating_expense_source_repairs")
    documents = {
        document["source_sha256"]: document for document in index.get("documents", [])
    }
    selected = {
        page["page_json_version_id"]: page for page in selected_page_axis
    }
    if type(repairs) is not list or not repairs or not documents or not selected:
        raise _error("Family-36 source-repair authentication frontier is absent")
    source_payloads: dict[tuple[str, str, int], bytes] = {}
    render_cache: dict[tuple[str, int], tuple[bytes, dict[str, Any]]] = {}
    checked: list[dict[str, Any]] = []
    out_of_corpus: list[dict[str, Any]] = []
    for repair in repairs:
        source = repair["source"]
        locator = repair["locator"]
        document = documents.get(source["source_sha256"])
        if document is None:
            out_of_corpus.append(
                {
                    "disposition": (
                        "DECLARED_SOURCE_REPAIR_OUTSIDE_SELECTED_CORPUS_NOT_APPLIED"
                    ),
                    "locator": canonical_clone_v1(locator),
                    "repair_id": repair["repair_id"],
                    "repair_kind": repair["repair_kind"],
                    "source_sha256": source["source_sha256"],
                }
            )
            continue
        page_axis = selected.get(locator["page_json_version_id"])
        if (
            document.get("relative_path") != source["source_logical_name"]
            or document.get("source_size_bytes") != source["source_size_bytes"]
            or page_axis is None
            or page_axis.get("source_sha256") != source["source_sha256"]
            or page_axis.get("physical_page") != locator["physical_page"]
        ):
            raise _error("Family-36 repair corpus/page binding drifted")
        logical_name = source["source_logical_name"]
        path = _source_path(source_pdf_root, logical_name)
        source_key = (
            logical_name,
            source["source_sha256"],
            source["source_size_bytes"],
        )
        payload = source_payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != source["source_size_bytes"]
                or sha256(payload).hexdigest() != source["source_sha256"]
            ):
                raise _error("Family-36 repair source artifact drifted")
            source_payloads[source_key] = payload
        cache_key = (logical_name, locator["physical_page"])
        cached = render_cache.get(cache_key)
        if cached is None:
            with fitz.open(stream=payload, filetype="pdf") as document:
                if locator["physical_page"] > len(document):
                    raise _error("Family-36 repair physical page is outside its PDF")
                rendered = render_full_pdf_page_v1(
                    document[locator["physical_page"] - 1],
                    physical_page=locator["physical_page"],
                    dpi=300,
                    source_sha256=source["source_sha256"],
                )
            cached = rendered.image, rendered.receipt
            render_cache[cache_key] = cached
        image_bytes, render_receipt = cached
        expected_render = repair["render"]
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            rgb = image.convert("RGB")
            bbox = repair["crop_evidence"]["bbox_pixels_xyxy"]
            crop = rgb.crop(tuple(bbox))
            actual_render = {
                "image_sha256": sha256(image_bytes).hexdigest(),
                "image_size_bytes": len(image_bytes),
                "media_type": "image/png",
                "physical_page": locator["physical_page"],
                "pixel_height": rgb.height,
                "pixel_width": rgb.width,
                "render_dpi": 300,
                "render_receipt_sha256": canonical_json_sha256_v1(render_receipt),
            }
            actual_crop = {
                "bbox_pixels_xyxy": bbox,
                "pixel_height": crop.height,
                "pixel_width": crop.width,
                "rgb_sha256": sha256(crop.tobytes()).hexdigest(),
            }
        if actual_render != expected_render or actual_crop != repair["crop_evidence"]:
            raise _error("Family-36 repair render or crop evidence drifted")
        checked.append(canonical_clone_v1(repair))
    checked.sort(key=lambda item: item["repair_id"])
    out_of_corpus.sort(key=lambda item: item["repair_id"])
    material = {
        "applicable_repair_count": len(checked),
        "authenticated": True,
        "declared_repair_count": len(repairs),
        "out_of_corpus_repair_axis": out_of_corpus,
        "out_of_corpus_repair_axis_sha256": canonical_json_sha256_v1(out_of_corpus),
        "out_of_corpus_repair_count": len(out_of_corpus),
        "repair_axis": checked,
        "repair_axis_sha256": canonical_json_sha256_v1(checked),
        "repair_count": len(checked),
        "source_pdf_count": len(source_payloads),
        "unverified_repair_count": 0,
    }
    receipt = {
        **material,
        "receipt_id": "gjoerunv1:source-repair-auth:"
        + canonical_json_sha256_v1(material),
    }
    return _validate_source_repair_authentication_receipt_v1(receipt)


def _validate_source_repair_authentication_receipt_v1(
    value: Any,
) -> dict[str, Any]:
    fields = {
        "applicable_repair_count",
        "authenticated",
        "declared_repair_count",
        "out_of_corpus_repair_axis",
        "out_of_corpus_repair_axis_sha256",
        "out_of_corpus_repair_count",
        "receipt_id",
        "repair_axis",
        "repair_axis_sha256",
        "repair_count",
        "source_pdf_count",
        "unverified_repair_count",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("Family-36 source-repair authentication receipt is invalid")
    repairs = value.get("repair_axis")
    outside = value.get("out_of_corpus_repair_axis")
    if (
        type(repairs) is not list
        or type(outside) is not list
        or value.get("authenticated") is not True
        or value.get("unverified_repair_count") != 0
        or value.get("applicable_repair_count") != len(repairs)
        or value.get("repair_count") != len(repairs)
        or value.get("out_of_corpus_repair_count") != len(outside)
        or value.get("declared_repair_count") != len(repairs) + len(outside)
        or value.get("repair_axis_sha256") != canonical_json_sha256_v1(repairs)
        or value.get("out_of_corpus_repair_axis_sha256")
        != canonical_json_sha256_v1(outside)
        or type(value.get("source_pdf_count")) is not int
        or not 0 <= value["source_pdf_count"] <= len(repairs)
        or any(
            type(repair) is not dict
            or type(repair.get("repair_id")) is not str
            for repair in repairs
        )
        or any(
            type(item) is not dict
            or item.get("disposition")
            != "DECLARED_SOURCE_REPAIR_OUTSIDE_SELECTED_CORPUS_NOT_APPLIED"
            or type(item.get("repair_id")) is not str
            for item in outside
        )
        or len(
            {
                repair["repair_id"] for repair in repairs
            }
            | {item["repair_id"] for item in outside}
        )
        != len(repairs) + len(outside)
    ):
        raise _error("Family-36 source-repair authentication gate failed")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "receipt_id"
    }
    if value.get("receipt_id") != (
        "gjoerunv1:source-repair-auth:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-36 source-repair authentication identity drifted")
    return canonical_clone_v1(value)


def _validate_pdf_residual_spec_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "corpus_manifest_index_id",
            "family_id",
            "format_version",
            "residual_axis_sha256",
            "residuals",
            "review_contract",
        }
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != PDF_RESIDUAL_FORMAT_VERSION
        or value.get("review_contract") != PDF_RESIDUAL_REVIEW_CONTRACT
        or type(value.get("residuals")) is not list
        or value.get("residual_axis_sha256")
        != canonical_json_sha256_v1(value.get("residuals"))
    ):
        raise _error("Family-36 PDF residual audit spec is invalid")
    prior_ordinal = 0
    for residual in value["residuals"]:
        if (
            type(residual) is not dict
            or set(residual)
            != {
                "disposition",
                "document_ordinal",
                "pdf_page_axis",
                "reasons",
                "residual_audit_id",
                "source_logical_name",
                "source_sha256",
                "source_size_bytes",
                "status",
            }
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior_ordinal
            or residual.get("disposition") != PDF_RESIDUAL_DISPOSITION
            or residual.get("status") not in {generic.NOT_OBSERVED, generic.UNRESOLVED}
            or type(residual.get("reasons")) is not list
            or any(
                type(reason) is not str or not reason
                for reason in residual.get("reasons", [])
            )
            or len(residual.get("reasons", []))
            != len(set(residual.get("reasons", [])))
            or (
                residual.get("status") == generic.NOT_OBSERVED
                and residual.get("reasons") != []
            )
            or (
                residual.get("status") == generic.UNRESOLVED
                and not residual.get("reasons")
            )
            or type(residual.get("source_logical_name")) is not str
            or not residual["source_logical_name"]
            or residual["source_logical_name"].startswith("/")
            or ".." in residual["source_logical_name"].split("/")
            or _SHA256.fullmatch(residual.get("source_sha256", "")) is None
            or type(residual.get("source_size_bytes")) is not int
            or residual["source_size_bytes"] <= 0
            or type(residual.get("pdf_page_axis")) is not list
            or not residual["pdf_page_axis"]
        ):
            raise _error("Family-36 PDF residual record is invalid or unordered")
        page_numbers = []
        page_ids = []
        for page in residual["pdf_page_axis"]:
            if (
                type(page) is not dict
                or set(page)
                != {
                    "page_json_version_id",
                    "pdf_page_render_sha256",
                    "physical_page",
                }
                or _PAGE_JSON_VERSION_ID.fullmatch(
                    page.get("page_json_version_id", "")
                )
                is None
                or _SHA256.fullmatch(page.get("pdf_page_render_sha256", ""))
                is None
                or type(page.get("physical_page")) is not int
                or page["physical_page"] <= 0
            ):
                raise _error("Family-36 residual PDF page record is invalid")
            page_numbers.append(page["physical_page"])
            page_ids.append(page["page_json_version_id"])
        if page_numbers != list(range(1, len(page_numbers) + 1)) or len(
            page_ids
        ) != len(set(page_ids)):
            raise _error("Family-36 residual PDF page axis is not complete and ordered")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "gjoepdfv1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-36 PDF residual record identity drifted")
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
    """Bind every non-ready trial to every page of its exact source PDF."""

    checked = _validate_pdf_residual_spec_v1(spec)
    if checked["corpus_manifest_index_id"] != index["corpus_manifest_index_id"]:
        raise _error("Family-36 PDF residual audit binds another corpus")
    expected_trials = [trial for trial in trials if trial["status"] != generic.READY]
    if [trial["document_ordinal"] for trial in expected_trials] != [
        residual["document_ordinal"] for residual in checked["residuals"]
    ]:
        raise _error("Family-36 PDF residual audit does not exhaust every N/U trial")
    documents = {document["source_ordinal"]: document for document in index["documents"]}
    selected_by_source_page = {
        (page["source_sha256"], page["physical_page"]): page
        for page in selected_page_axis
    }
    authenticated = []
    for trial, residual in zip(expected_trials, checked["residuals"], strict=True):
        document = documents.get(residual["document_ordinal"])
        document_pages = page_json_by_document.get(residual["document_ordinal"])
        if (
            document is None
            or type(document_pages) is not dict
            or trial["source_logical_name"] != residual["source_logical_name"]
            or trial["source_sha256"] != residual["source_sha256"]
            or trial["status"] != residual["status"]
            or trial["reasons"] != residual["reasons"]
            or document["relative_path"] != residual["source_logical_name"]
            or document["source_sha256"] != residual["source_sha256"]
            or document["source_size_bytes"] != residual["source_size_bytes"]
        ):
            raise _error("Family-36 PDF residual source/trial binding drifted")
        path = _source_path(source_pdf_root, residual["source_logical_name"])
        if (
            path.stat().st_size != residual["source_size_bytes"]
            or _sha256(path) != residual["source_sha256"]
        ):
            raise _error("Family-36 PDF residual source bytes drifted")
        with fitz.open(path) as pdf:
            if len(residual["pdf_page_axis"]) != len(pdf):
                raise _error("Family-36 residual does not cover every PDF page")
            for page in residual["pdf_page_axis"]:
                physical_page = page["physical_page"]
                selected = selected_by_source_page.get(
                    (residual["source_sha256"], physical_page)
                )
                if (
                    selected is None
                    or selected.get("document_ordinal") != residual["document_ordinal"]
                    or selected.get("page_json_version_id")
                    != page["page_json_version_id"]
                    or page["page_json_version_id"] not in document_pages
                ):
                    raise _error("Family-36 residual selected-page binding drifted")
                pixmap = pdf[physical_page - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                if (
                    sha256(pixmap.tobytes("png")).hexdigest()
                    != page["pdf_page_render_sha256"]
                ):
                    raise _error("Family-36 residual PDF render drifted")
        authenticated.append(canonical_clone_v1(residual))
    return authenticated


def _coverage_row_locator(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("source_sha256"),
        item.get("page_json_version_id"),
        item.get("section_id"),
        item.get("table_id"),
        item.get("row_ordinal"),
    )


def _pdf_visible_audit_row_v1(
    item: Mapping[str, Any], *, axis_kind: str
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
    coverage: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected_fields = {
        "source_row_axis": "CLASSIFIED_SOURCE_ROW",
        "candidate_table_total_row_axis": "CANDIDATE_TABLE_TOTAL_DISPOSITION",
        "raw_target_like_row_axis": "RAW_TARGET_LIKE_SOURCE_ROW",
    }
    if (
        coverage.get("family_id") != FAMILY_ID
        or coverage.get("violation_count") != 0
        or any(type(coverage.get(name)) is not list for name in expected_fields)
        or any(
            coverage.get(name + "_sha256")
            != canonical_json_sha256_v1(coverage.get(name))
            for name in expected_fields
        )
    ):
        raise _error("Family-36 PDF-visible coverage receipt is invalid")
    rows: list[dict[str, Any]] = []
    covered_locators: set[tuple[Any, ...]] = set()
    for axis_name, axis_kind in expected_fields.items():
        for item in coverage[axis_name]:
            locator = _coverage_row_locator(item)
            if axis_name != "source_row_axis" and locator in covered_locators:
                continue
            rows.append(_pdf_visible_audit_row_v1(item, axis_kind=axis_kind))
        covered_locators.update(
            _coverage_row_locator(item) for item in coverage[axis_name]
        )
    return sorted(rows, key=canonical_json_sha256_v1)


def _validate_manual_pdf_review_category_frontier_v1(
    *,
    manual_axis: Sequence[Mapping[str, Any]],
    expected_rows: Sequence[Mapping[str, Any]],
    rendered_by_source_page: Mapping[tuple[str, int], Mapping[str, Any]],
) -> None:
    required_review_kinds = {
        f"{row['axis_kind']}__{row['coverage']}" for row in expected_rows
    }
    review_kinds = set()
    for item in manual_axis:
        page = (
            rendered_by_source_page.get(
                (item.get("source_sha256", ""), item.get("physical_page", 0))
            )
            if type(item) is dict
            else None
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
            or not any(
                item["review_kind"]
                == f"{row['axis_kind']}__{row['coverage']}"
                for row in page["source_row_axis"]
            )
        ):
            raise _error("Family-36 manual PDF review binding drifted")
        review_kinds.add(item["review_kind"])
    if review_kinds != required_review_kinds:
        raise _error("Family-36 manual PDF review category frontier is incomplete")


def _authenticate_pdf_visible_source_row_audit_v1(
    *,
    value: Any,
    index: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    source_row_coverage: Mapping[str, Any],
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
        or value.get("coverage_receipt_id") != source_row_coverage.get("receipt_id")
    ):
        raise _error("Family-36 PDF-visible source-row audit envelope drifted")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "audit_id"
    }
    if value.get("audit_id") != (
        "gjoefav1:pdf-visible:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-36 PDF-visible source-row audit identity drifted")

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
        raise _error("Family-36 PDF-visible source PDF axis drifted")
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
        raise _error("Family-36 PDF-visible page-render axis drifted")
    documents = {document["source_ordinal"]: document for document in index["documents"]}
    selected_by_id = {
        page["page_json_version_id"]: page for page in selected_page_axis
    }
    actual_keys = []
    rendered_by_source_page: dict[tuple[str, int], dict[str, Any]] = {}
    for page in page_axis:
        key = (
            page.get("document_ordinal") if type(page) is dict else None,
            page.get("physical_page") if type(page) is dict else None,
            page.get("page_json_version_id") if type(page) is dict else None,
        )
        document = documents.get(key[0])
        selected = selected_by_id.get(key[2])
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
            or selected is None
            or selected.get("document_ordinal") != key[0]
            or selected.get("physical_page") != key[1]
            or selected.get("source_sha256") != document["source_sha256"]
            or expected_page_rows is None
            or not same_typed_json_v1(page.get("source_row_axis"), expected_page_rows)
            or page.get("source_row_axis_sha256")
            != canonical_json_sha256_v1(expected_page_rows)
            or page.get("render_contract") != PDF_RENDER_CONTRACT
            or page.get("source_logical_name") != document["relative_path"]
            or page.get("source_sha256") != document["source_sha256"]
            or type(key[1]) is not int
            or key[1] <= 0
            or type(page.get("pixel_width")) is not int
            or page["pixel_width"] <= 0
            or type(page.get("pixel_height")) is not int
            or page["pixel_height"] <= 0
            or _SHA256.fullmatch(page.get("render_sha256", "")) is None
        ):
            raise _error("Family-36 PDF-visible page source-row binding drifted")
        actual_keys.append(key)
        rendered_by_source_page[(document["source_sha256"], key[1])] = page
    if actual_keys != sorted(expected_grouped):
        raise _error("Family-36 PDF-visible page axis is incomplete or unordered")

    pages_by_ordinal: dict[int, list[dict[str, Any]]] = {}
    for page in page_axis:
        pages_by_ordinal.setdefault(page["document_ordinal"], []).append(page)
    for source in expected_source_axis:
        path = _source_path(source_pdf_root, source["source_logical_name"])
        if (
            path.stat().st_size != source["source_size_bytes"]
            or _sha256(path) != source["source_sha256"]
        ):
            raise _error("Family-36 PDF-visible source bytes drifted")
        pages = pages_by_ordinal.get(source["document_ordinal"], [])
        if not pages:
            continue
        with fitz.open(path) as pdf:
            for page in pages:
                physical_page = page["physical_page"]
                if physical_page > len(pdf):
                    raise _error("Family-36 PDF-visible page is outside source PDF")
                pixmap = pdf[physical_page - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                if (
                    pixmap.width != page["pixel_width"]
                    or pixmap.height != page["pixel_height"]
                    or sha256(pixmap.tobytes("png")).hexdigest()
                    != page["render_sha256"]
                ):
                    raise _error("Family-36 PDF-visible page render drifted")

    manual_axis = value.get("manual_exception_category_review_axis")
    if (
        type(manual_axis) is not list
        or not manual_axis
        or value.get("manual_exception_category_review_axis_sha256")
        != canonical_json_sha256_v1(manual_axis)
    ):
        raise _error("Family-36 manual PDF review axis is absent or drifted")
    _validate_manual_pdf_review_category_frontier_v1(
        manual_axis=manual_axis,
        expected_rows=expected_rows,
        rendered_by_source_page=rendered_by_source_page,
    )
    expected_counts = {
        "authenticated_source_pdfs": len(expected_source_axis),
        "manual_exception_category_pages": len(manual_axis),
        "rendered_source_row_pages": len(page_axis),
        "source_rows_bound_to_renders": len(expected_rows),
    }
    if value.get("counts") != expected_counts:
        raise _error("Family-36 PDF-visible source-row audit counts drifted")
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


def _validate_pdf_visible_source_row_audit_receipt_v1(
    value: Any, *, source_row_coverage: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "authenticated",
        "counts",
        "coverage_receipt_id",
        "manual_exception_category_review_axis_sha256",
        "pdf_page_render_axis_sha256",
        "source_pdf_authentication_axis_sha256",
        "uncovered_source_row_count",
    }
    counts = value.get("counts") if type(value) is dict else None
    expected_rows = _expected_pdf_visible_audit_rows_v1(source_row_coverage)
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("authenticated") is not True
        or value.get("uncovered_source_row_count") != 0
        or value.get("coverage_receipt_id")
        != source_row_coverage.get("receipt_id")
        or type(value.get("audit_id")) is not str
        or not value["audit_id"].startswith("gjoefav1:pdf-visible:")
        or _SHA256.fullmatch(value["audit_id"].removeprefix("gjoefav1:pdf-visible:"))
        is None
        or any(
            _SHA256.fullmatch(value.get(name, "")) is None
            for name in (
                "manual_exception_category_review_axis_sha256",
                "pdf_page_render_axis_sha256",
                "source_pdf_authentication_axis_sha256",
            )
        )
        or type(counts) is not dict
        or set(counts)
        != {
            "authenticated_source_pdfs",
            "manual_exception_category_pages",
            "rendered_source_row_pages",
            "source_rows_bound_to_renders",
        }
        or any(type(count) is not int or count < 0 for count in counts.values())
        or counts.get("source_rows_bound_to_renders") != len(expected_rows)
        or counts.get("rendered_source_row_pages", 0) > len(expected_rows)
        or (bool(expected_rows) != bool(counts.get("rendered_source_row_pages")))
        or (bool(expected_rows) != bool(counts.get("manual_exception_category_pages")))
    ):
        raise _error("Family-36 PDF-visible source-row audit receipt is invalid")
    return canonical_clone_v1(value)


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
            raise _error("Family-36 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-36 historical oracle source identity is absent")
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


def _validate_source_row_coverage_receipt_v1(value: Any) -> dict[str, Any]:
    fields = {
        "candidate_table_total_disposition_counts",
        "candidate_table_total_row_axis",
        "candidate_table_total_row_axis_sha256",
        "family_id",
        "format_version",
        "raw_target_like_disposition_counts",
        "raw_target_like_row_axis",
        "raw_target_like_row_axis_sha256",
        "receipt_id",
        "source_row_axis",
        "source_row_axis_sha256",
        "source_row_disposition_counts",
        "violation_axis",
        "violation_count",
    }

    def disposition_counts(axis: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        return {
            disposition: sum(item.get("coverage") == disposition for item in axis)
            for disposition in sorted(
                {
                    item.get("coverage")
                    for item in axis
                    if type(item) is dict and type(item.get("coverage")) is str
                }
            )
        }

    if type(value) is not dict or set(value) != fields:
        raise _error("Family-36 source-row coverage receipt is invalid")
    source_rows = value.get("source_row_axis")
    total_rows = value.get("candidate_table_total_row_axis")
    raw_rows = value.get("raw_target_like_row_axis")
    violations = value.get("violation_axis")
    if (
        value.get("family_id") != FAMILY_ID
        or value.get("format_version") != "OPERATING_EXPENSE_SOURCE_ROW_COVERAGE_V1"
        or any(type(axis) is not list for axis in (source_rows, total_rows, raw_rows, violations))
        or value.get("source_row_axis_sha256")
        != canonical_json_sha256_v1(source_rows)
        or value.get("candidate_table_total_row_axis_sha256")
        != canonical_json_sha256_v1(total_rows)
        or value.get("raw_target_like_row_axis_sha256")
        != canonical_json_sha256_v1(raw_rows)
        or value.get("source_row_disposition_counts")
        != disposition_counts(source_rows)
        or value.get("candidate_table_total_disposition_counts")
        != disposition_counts(total_rows)
        or value.get("raw_target_like_disposition_counts")
        != disposition_counts(raw_rows)
        or value.get("violation_count") != len(violations)
        or violations
    ):
        raise _error("Family-36 source-row coverage gate failed")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "receipt_id"
    }
    if value.get("receipt_id") != (
        "gjoefav1:source-row-coverage:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-36 source-row coverage identity drifted")
    return canonical_clone_v1(value)


_AUDIT_AXIS_NAMES = {
    "all_blank_validation_role_omissions",
    "continuation_projections",
    "equations",
    "mappings",
    "nonexhaustive_parents",
    "partial_role_observations",
    "pdf_residuals",
    "query_continuation_recoveries",
    "query_owner_region_recoveries",
    "query_titleless_primary_recoveries",
    "residuals",
    "root_closures",
    "root_component_sums",
    "source_only_rows",
    "source_repairs",
    "trials",
    "unit_corroborations",
}


def _audit_axes(
    *,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    pdf_residuals: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "all_blank_validation_role_omissions": [],
        "continuation_projections": [],
        "equations": [],
        "mappings": [],
        "nonexhaustive_parents": [],
        "partial_role_observations": [],
        "pdf_residuals": canonical_clone_v1(list(pdf_residuals)),
        "query_continuation_recoveries": [],
        "query_owner_region_recoveries": [],
        "query_titleless_primary_recoveries": [],
        "root_closures": [],
        "root_component_sums": [],
        "source_only_rows": [],
        "source_repairs": [],
        "trials": canonical_clone_v1(list(trials)),
        "unit_corroborations": [],
        "residuals": [],
    }
    dispositions = indexed.get("candidate_dispositions", [])
    if type(dispositions) is not list or len(dispositions) != len(axes["trials"]):
        raise _error("Family-36 audit trial/query denominator drifted")
    for disposition in dispositions:
        cluster = disposition.get("cluster") if type(disposition) is dict else None
        if type(cluster) is not dict:
            raise _error("Family-36 audit query cluster is invalid")
        for key, axis_name in (
            (
                "operating_expense_continuation_query_receipt",
                "query_continuation_recoveries",
            ),
            (
                "operating_expense_owner_region_recovery_receipt",
                "query_owner_region_recoveries",
            ),
            (
                "operating_expense_titleless_primary_region_recovery_receipt",
                "query_titleless_primary_recoveries",
            ),
        ):
            receipt = cluster.get(key)
            if receipt is not None:
                if type(receipt) is not dict:
                    raise _error("Family-36 query recovery receipt is invalid")
                axes[axis_name].append(canonical_clone_v1(receipt))
    for trial in trials:
        if trial.get("status") != generic.READY:
            axes["residuals"].append(
                {
                    "document_ordinal": trial.get("document_ordinal"),
                    "reasons": canonical_clone_v1(trial.get("reasons", [])),
                    "source_logical_name": trial.get("source_logical_name"),
                    "source_sha256": trial.get("source_sha256"),
                    "status": trial.get("status"),
                }
            )
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        if type(candidate) is not dict or type(candidate.get("closure_receipt")) is not dict:
            raise _error("Family-36 candidate audit receipt is invalid")
        mappings = trial.get("mappings")
        closure = candidate["closure_receipt"]
        if type(mappings) is not list:
            raise _error("Family-36 accepted mapping axis is invalid")
        axes["mappings"].extend(canonical_clone_v1(mappings))
        for key, axis_name in (
            ("equations", "equations"),
            ("partial_role_observations", "partial_role_observations"),
            ("root_component_sum_receipts", "root_component_sums"),
            ("source_only_unmapped_rows", "source_only_rows"),
        ):
            receipts = closure.get(key, [])
            if type(receipts) is not list:
                raise _error("Family-36 closure audit axis is invalid")
            axes[axis_name].extend(canonical_clone_v1(receipts))
        adapter = closure.get("operating_expense_adapter_receipt")
        if type(adapter) is not dict:
            raise _error("Family-36 candidate adapter receipt is absent")
        for key, axis_name in (
            (
                "all_blank_validation_role_omission_receipts",
                "all_blank_validation_role_omissions",
            ),
            ("continuation_projection_receipts", "continuation_projections"),
            ("nonexhaustive_parent_receipts", "nonexhaustive_parents"),
            ("root_closure_receipts", "root_closures"),
            ("source_repair_receipts", "source_repairs"),
            ("unit_corroboration_receipts", "unit_corroborations"),
        ):
            receipts = adapter.get(key)
            if type(receipts) is not list:
                raise _error("Family-36 candidate adapter audit axis is invalid")
            axes[axis_name].extend(canonical_clone_v1(receipts))
    if set(axes) != _AUDIT_AXIS_NAMES:
        raise _error("Family-36 audit axis schema drifted")
    return axes


def build_operating_expense_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    output: Path,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    historical_receipt: Mapping[str, Any],
    observation_contract: Mapping[str, Any],
    source_repair_application: Mapping[str, Any],
    source_repair_authentication: Mapping[str, Any],
    source_row_coverage: Mapping[str, Any],
    pdf_visible_source_row_audit: Mapping[str, Any],
    pdf_residuals: Sequence[Mapping[str, Any]],
    selected_ids: Sequence[str],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = _validate_source_row_coverage_receipt_v1(source_row_coverage)
    source_repair_application = _validate_source_repair_application_receipt_v1(
        source_repair_application
    )
    source_repair_authentication = (
        _validate_source_repair_authentication_receipt_v1(
            source_repair_authentication
        )
    )
    pdf_visible_source_row_audit = (
        _validate_pdf_visible_source_row_audit_receipt_v1(
            pdf_visible_source_row_audit,
            source_row_coverage=coverage,
        )
    )
    axes = _audit_axes(
        indexed=indexed,
        trials=trials,
        pdf_residuals=pdf_residuals,
    )
    expected_repairs = sorted(source_repair_application["expected_repair_ids"])
    applied_repairs = sorted(source_repair_application["applied_repair_ids"])
    authenticated_repairs = sorted(
        repair["repair_id"] for repair in source_repair_authentication["repair_axis"]
    )
    if not (expected_repairs == applied_repairs == authenticated_repairs):
        raise _error("Family-36 repair application/authentication axis drifted")
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
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
        "pdf_visible_source_row_audit_receipt": canonical_clone_v1(
            pdf_visible_source_row_audit
        ),
        "query_evidence_id": indexed["query_evidence_id"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_ids)
        ),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "source_repair_application": canonical_clone_v1(source_repair_application),
        "source_repair_authentication_receipt": canonical_clone_v1(
            source_repair_authentication
        ),
        "source_row_coverage_receipt": coverage,
        "spec_refs": canonical_clone_v1(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_id": sweep["sweep_id"],
        "sweep_output": str(output),
        "sweep_ref": {
            "path": output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjoefauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_operating_expense_experimental_audit_v1(
    value: Any,
) -> dict[str, Any]:
    expected_fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "family_id",
        "format_version",
        "historical_comparator_policy_receipt",
        "indexed_query_receipt",
        "pdf_visible_source_row_audit_receipt",
        "query_evidence_id",
        "selected_page_json_frontier_sha256",
        "source_observation_contract",
        "source_repair_application",
        "source_repair_authentication_receipt",
        "source_row_coverage_receipt",
        "spec_refs",
        "state",
        "sweep_id",
        "sweep_output",
        "sweep_ref",
    }
    axes = value.get("axes", {}) if type(value) is dict else {}
    sweep_ref = value.get("sweep_ref", {}) if type(value) is dict else {}
    source_auth_value = (
        value.get("source_repair_authentication_receipt")
        if type(value) is dict
        else None
    )
    source_auth = source_auth_value if type(source_auth_value) is dict else {}
    source_application_value = (
        value.get("source_repair_application") if type(value) is dict else None
    )
    source_application = (
        source_application_value if type(source_application_value) is dict else {}
    )
    pdf_visible_value = (
        value.get("pdf_visible_source_row_audit_receipt")
        if type(value) is dict
        else None
    )
    pdf_visible = pdf_visible_value if type(pdf_visible_value) is dict else {}
    coverage_value = (
        value.get("source_row_coverage_receipt") if type(value) is dict else None
    )
    coverage = coverage_value if type(coverage_value) is dict else {}
    spec_refs_value = value.get("spec_refs") if type(value) is dict else None
    spec_refs = spec_refs_value if type(spec_refs_value) is dict else {}
    if (
        type(value) is not dict
        or set(value) != expected_fields
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
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
        or source_application.get("violation_count") != 0
        or source_auth.get("authenticated") is not True
        or source_auth.get("unverified_repair_count") != 0
        or type(source_auth.get("repair_axis")) is not list
        or source_auth.get("repair_axis_sha256")
        != canonical_json_sha256_v1(source_auth.get("repair_axis", []))
        or source_auth.get("repair_count") != len(source_auth.get("repair_axis", []))
        or any(
            type(repair) is not dict or type(repair.get("repair_id")) is not str
            for repair in source_auth.get("repair_axis", [])
        )
        or type(source_application.get("expected_repair_ids")) is not list
        or type(source_application.get("applied_repair_ids")) is not list
        or any(
            type(repair_id) is not str or not repair_id
            for repair_id in source_application.get("expected_repair_ids", [])
        )
        or any(
            type(repair_id) is not str or not repair_id
            for repair_id in source_application.get("applied_repair_ids", [])
        )
        or pdf_visible.get("authenticated") is not True
        or pdf_visible.get("uncovered_source_row_count") != 0
        or pdf_visible.get("coverage_receipt_id") != coverage.get("receipt_id")
        or set(pdf_visible)
        != {
            "audit_id",
            "authenticated",
            "counts",
            "coverage_receipt_id",
            "manual_exception_category_review_axis_sha256",
            "pdf_page_render_axis_sha256",
            "source_pdf_authentication_axis_sha256",
            "uncovered_source_row_count",
        }
        or any(
            _SHA256.fullmatch(pdf_visible.get(name, "")) is None
            for name in (
                "manual_exception_category_review_axis_sha256",
                "pdf_page_render_axis_sha256",
                "source_pdf_authentication_axis_sha256",
            )
        )
        or type(value.get("indexed_query_receipt")) is not dict
        or not value["indexed_query_receipt"]
        or type(spec_refs) is not dict
        or set(spec_refs)
        != {
            "evaluation",
            "pdf_residual_audit",
            "pdf_visible_source_row_audit",
            "schema_binding",
            "source_repair",
            "topology",
        }
        or any(
            type(reference) is not dict
            or set(reference) != {"path", "sha256", "size_bytes"}
            or type(reference.get("path")) is not str
            or not reference["path"]
            or _SHA256.fullmatch(reference.get("sha256", "")) is None
            or type(reference.get("size_bytes")) is not int
            or reference["size_bytes"] <= 0
            for reference in spec_refs.values()
        )
        or type(axes) is not dict
        or set(axes) != _AUDIT_AXIS_NAMES
        or any(type(axis) is not list for axis in axes.values())
        or value.get("axis_counts")
        != {name: len(axis) for name, axis in axes.items()}
        or value.get("axis_sha256")
        != {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
        or len(axes.get("pdf_residuals", [])) != len(axes.get("residuals", []))
        or any(
            type(residual) is not dict
            for residual in axes.get("pdf_residuals", [])
        )
        or any(
            type(residual) is not dict for residual in axes.get("residuals", [])
        )
        or any(
            {
                key: canonical_clone_v1(residual.get(key))
                for key in (
                    "document_ordinal",
                    "reasons",
                    "source_logical_name",
                    "source_sha256",
                    "status",
                )
            }
            != trial_residual
            for residual, trial_residual in zip(
                axes.get("pdf_residuals", []),
                axes.get("residuals", []),
                strict=True,
            )
        )
        or sorted(source_application.get("expected_repair_ids", []))
        != sorted(source_application.get("applied_repair_ids", []))
        or sorted(source_application.get("expected_repair_ids", []))
        != sorted(
            repair.get("repair_id") for repair in source_auth.get("repair_axis", [])
        )
        or _SHA256.fullmatch(
            value.get("selected_page_json_frontier_sha256", "")
        )
        is None
        or type(value.get("query_evidence_id")) is not str
        or not value["query_evidence_id"]
        or type(sweep_ref) is not dict
        or set(sweep_ref) != {"path", "sha256", "size_bytes", "sweep_id"}
        or type(sweep_ref.get("path")) is not str
        or not sweep_ref["path"]
        or _SHA256.fullmatch(sweep_ref.get("sha256", "")) is None
        or type(sweep_ref.get("size_bytes")) is not int
        or sweep_ref["size_bytes"] <= 0
        or sweep_ref.get("sweep_id") != value.get("sweep_id")
    ):
        raise _error("Family-36 experimental audit content is invalid")
    _validate_source_repair_application_receipt_v1(source_application)
    _validate_source_repair_authentication_receipt_v1(source_auth)
    _validate_source_row_coverage_receipt_v1(coverage)
    _validate_pdf_visible_source_row_audit_receipt_v1(
        pdf_visible,
        source_row_coverage=coverage,
    )
    _validate_pdf_residual_spec_v1(
        {
            "corpus_manifest_index_id": "AUDIT_EMBEDDED_AXIS",
            "family_id": FAMILY_ID,
            "format_version": PDF_RESIDUAL_FORMAT_VERSION,
            "residual_axis_sha256": canonical_json_sha256_v1(
                axes["pdf_residuals"]
            ),
            "residuals": canonical_clone_v1(axes["pdf_residuals"]),
            "review_contract": PDF_RESIDUAL_REVIEW_CONTRACT,
        }
    )
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "audit_id"
    }
    if value.get("audit_id") != "gjoefauditv1:audit:" + canonical_json_sha256_v1(
        material
    ):
        raise _error("Family-36 experimental audit identity drifted")
    return canonical_clone_v1(value)


def _source_repair_application_receipt_v1(
    *,
    index: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    corpus_sources = {document["source_sha256"] for document in index["documents"]}
    expected = [
        repair["repair_id"]
        for repair in compiled_specs["operating_expense_source_repairs"]
        if repair["source"]["source_sha256"] in corpus_sources
    ]
    applied = []
    for trial in trials:
        for candidate in trial.get("candidates", []):
            adapter = candidate.get("closure_receipt", {}).get(
                "operating_expense_adapter_receipt"
            )
            if type(adapter) is not dict:
                continue
            applied.extend(
                receipt["repair"]["repair_id"]
                for receipt in adapter["source_repair_receipts"]
            )
    violations = []
    if len(applied) != len(set(applied)):
        violations.append("DUPLICATE_SOURCE_REPAIR_APPLICATION")
    if sorted(applied) != sorted(expected):
        violations.append("SOURCE_REPAIR_APPLICATION_AXIS_MISMATCH")
    material = {
        "applied_repair_ids": applied,
        "expected_repair_ids": expected,
        "rule": "EVERY_IN_CORPUS_AUTHENTICATED_SOURCE_REPAIR_APPLIED_EXACTLY_ONCE",
        "source_repair_spec_sha256": compiled_specs[
            "operating_expense_source_repair_spec_sha256"
        ],
        "violation_count": len(violations),
        "violations": violations,
    }
    receipt = {
        **material,
        "receipt_id": "gjoerunv1:source-repair-application:"
        + canonical_json_sha256_v1(material),
    }
    if violations:
        raise _error("Family-36 source-repair application gate failed")
    return _validate_source_repair_application_receipt_v1(receipt)


def _validate_source_repair_application_receipt_v1(value: Any) -> dict[str, Any]:
    fields = {
        "applied_repair_ids",
        "expected_repair_ids",
        "receipt_id",
        "rule",
        "source_repair_spec_sha256",
        "violation_count",
        "violations",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("Family-36 source-repair application receipt is invalid")
    applied = value.get("applied_repair_ids")
    expected = value.get("expected_repair_ids")
    violations = value.get("violations")
    if (
        type(applied) is not list
        or type(expected) is not list
        or type(violations) is not list
        or any(type(repair_id) is not str or not repair_id for repair_id in applied)
        or any(type(repair_id) is not str or not repair_id for repair_id in expected)
        or any(type(violation) is not str or not violation for violation in violations)
        or value.get("rule")
        != "EVERY_IN_CORPUS_AUTHENTICATED_SOURCE_REPAIR_APPLIED_EXACTLY_ONCE"
        or _SHA256.fullmatch(value.get("source_repair_spec_sha256", "")) is None
        or value.get("violation_count") != len(violations)
        or violations
        or len(applied) != len(set(applied))
        or sorted(applied) != sorted(expected)
    ):
        raise _error("Family-36 source-repair application gate failed")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "receipt_id"
    }
    if value.get("receipt_id") != (
        "gjoerunv1:source-repair-application:"
        + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-36 source-repair application identity drifted")
    return canonical_clone_v1(value)


def replay_operating_expense_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query and replay every candidate through the byte-bound adapter."""

    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    source_repairs = generic._json(SOURCE_REPAIR_SPEC_PATH)
    base_compiled = compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, schema
    )
    if not same_typed_json_v1(base_compiled, compiled_specs):
        raise _error("Family-36 source replay declarative specs drifted")
    family_compiled = compile_gemini_json_operating_expense_family_specs_v1(
        topology, evaluation, schema, source_repairs
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
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-36 source replay rebuilt different query evidence")
    return build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )


def _implementation_refs(
    *,
    topology_spec: Path = TOPOLOGY_SPEC_PATH,
    evaluation_spec: Path = EVALUATION_SPEC_PATH,
    schema_binding_spec: Path = SCHEMA_BINDING_SPEC_PATH,
    source_repair_spec: Path = SOURCE_REPAIR_SPEC_PATH,
    pdf_residual_audit_spec: Path,
    pdf_visible_source_row_audit: Path,
) -> list[dict[str, Any]]:
    paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_operating_expense_accounting_family_v1.py",
        ADAPTER_PATH,
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        source_repair_spec,
        pdf_residual_audit_spec,
        pdf_visible_source_row_audit,
    )
    root = ROOT.resolve()
    return [
        generic._file_ref(
            path,
            root=ROOT if path.resolve().is_relative_to(root) else None,
        )
        for path in paths
    ]


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
    indexed = build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    replayed = replay_operating_expense_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(selected_ids),
        compiled_specs=compile_gemini_json_flat_family_specs_v1(
            topology, evaluation, schema
        ),
        indexed_query_evidence=indexed,
    )
    if not same_typed_json_v1(replayed, trials):
        raise _error("Family-36 direct source replay returned different trials")
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
        raise _error("Family-36 current corpus denominator drifted")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    source_row_coverage = build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
        fail_on_violation=True,
    )
    source_row_coverage = _validate_source_row_coverage_receipt_v1(
        source_row_coverage
    )
    source_repair_authentication = _authenticate_source_repairs_v1(
        compiled_specs=compiled,
        index=index,
        selected_page_axis=base["selected_page_axis"],
        source_pdf_root=args.source_pdf_root,
    )
    source_repair_application = _source_repair_application_receipt_v1(
        index=index, compiled_specs=compiled, trials=trials
    )
    pdf_visible_source_row_audit = _authenticate_pdf_visible_source_row_audit_v1(
        value=generic._json(args.pdf_visible_source_row_audit),
        index=index,
        selected_page_axis=base["selected_page_axis"],
        source_row_coverage=source_row_coverage,
        source_pdf_root=args.source_pdf_root,
    )
    pdf_residuals = _authenticate_pdf_residuals_v1(
        spec=generic._json(args.pdf_residual_audit_spec),
        index=index,
        selected_page_axis=base["selected_page_axis"],
        page_json_by_document=pages,
        trials=trials,
        source_pdf_root=args.source_pdf_root,
    )
    historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled,
    )
    audit = build_operating_expense_experimental_audit_v1(
        sweep=sweep,
        output=args.output,
        indexed=indexed,
        trials=trials,
        historical_receipt=historical_receipt,
        observation_contract=observation_contract,
        source_repair_application=source_repair_application,
        source_repair_authentication=source_repair_authentication,
        source_row_coverage=source_row_coverage,
        pdf_visible_source_row_audit=pdf_visible_source_row_audit,
        pdf_residuals=pdf_residuals,
        selected_ids=selected_ids,
        spec_refs=spec_refs,
    )
    validate_operating_expense_experimental_audit_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_operating_expense_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(
            topology_spec=args.topology_spec,
            evaluation_spec=args.evaluation_spec,
            schema_binding_spec=args.schema_binding_spec,
            source_repair_spec=args.source_repair_spec,
            pdf_residual_audit_spec=args.pdf_residual_audit_spec,
            pdf_visible_source_row_audit=args.pdf_visible_source_row_audit,
        ),
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_operating_expense_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-36 sweep differs from authenticated evaluation")
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
        "pdf_residual_count": len(pdf_residuals),
        "pdf_visible_source_row_audit_id": pdf_visible_source_row_audit[
            "audit_id"
        ],
        "results_database": str(args.results_database),
        "run_kind": "EXPERIMENTAL",
        "source_row_coverage_receipt_id": source_row_coverage["receipt_id"],
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.historical_comparator_policy != DISJOINT_EXPANSION:
        raise _error("Family-36 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    registered_specs = (
        (args.topology_spec.resolve(), TOPOLOGY_SPEC_PATH.resolve()),
        (args.evaluation_spec.resolve(), EVALUATION_SPEC_PATH.resolve()),
        (args.schema_binding_spec.resolve(), SCHEMA_BINDING_SPEC_PATH.resolve()),
        (args.source_repair_spec.resolve(), SOURCE_REPAIR_SPEC_PATH.resolve()),
    )
    if any(actual != expected for actual, expected in registered_specs):
        raise _error("Family-36 run requires its registered declarative artifacts")
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_spec)
    compiled = compile_gemini_json_operating_expense_family_specs_v1(
        topology, evaluation, schema, source_repairs
    )
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "pdf_residual_audit": generic._file_ref(
            args.pdf_residual_audit_spec,
            root=(
                ROOT
                if args.pdf_residual_audit_spec.resolve().is_relative_to(ROOT.resolve())
                else None
            ),
        ),
        "pdf_visible_source_row_audit": generic._file_ref(
            args.pdf_visible_source_row_audit,
            root=(
                ROOT
                if args.pdf_visible_source_row_audit.resolve().is_relative_to(
                    ROOT.resolve()
                )
                else None
            ),
        ),
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
    parser.add_argument("--topology-spec", type=Path, default=TOPOLOGY_SPEC_PATH)
    parser.add_argument("--evaluation-spec", type=Path, default=EVALUATION_SPEC_PATH)
    parser.add_argument(
        "--schema-binding-spec", type=Path, default=SCHEMA_BINDING_SPEC_PATH
    )
    parser.add_argument(
        "--source-repair-spec", type=Path, default=SOURCE_REPAIR_SPEC_PATH
    )
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
