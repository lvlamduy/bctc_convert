#!/usr/bin/env python3
"""Run Family 40 over one authenticated selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
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

from bctc_ai.evaluation.gemini_json_cash_equivalents_family_v1 import (  # noqa: E402
    FAMILY_ID,
    adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1,
    bind_gemini_json_cash_equivalents_source_repairs_v1,
    build_gemini_json_cash_equivalents_region_query_receipt_v1,
    compile_gemini_json_cash_equivalents_family_specs_v1,
    evaluate_gemini_json_cash_equivalents_family_cluster_v1,
    validate_gemini_json_cash_equivalents_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
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

AUDIT_FORMAT_VERSION = "GEMINI_JSON_CASH_EQUIVALENTS_EXPERIMENTAL_AUDIT_V1"
PDF_RESIDUAL_FORMAT_VERSION = "CASH_EQUIVALENTS_PDF_RESIDUAL_AUDIT_SPEC_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-cash-equivalents-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-cash-equivalents-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = (
    ROOT / "config/families/tm-cash-equivalents-schema-binding-v1.json"
)
SOURCE_REPAIR_PATH = (
    ROOT / "data/registered/gemini_json_cash_equivalents_source_repairs_v1.json"
)
PDF_RESIDUAL_AUDIT_SPEC_PATH = (
    ROOT
    / "config/families/tm-cash-equivalents-pdf-residual-audit-full271-v1.json"
)
ADAPTER_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_cash_equivalents_family_v1.py"
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
_PDF_REVIEW_CONTRACT = {
    "mapping_rule": (
        "DIRECT_SOURCE_VISIBLE_FAMILY_TABLE_ONLY_NO_BLANK_ZERO_BACKSOLVE_OR_"
        "INEXACT_UNIT_SCALING"
    ),
    "page_scope": (
        "EVERY_SELECTED_ACCOUNTING_POLICY_TARGET_PAGE_FOR_NOT_OBSERVED_AND_"
        "EXACT_SELECTED_DETAIL_PAGE_FOR_UNRESOLVED"
    ),
    "render_contract": {
        "alpha": False,
        "colorspace": "RGB",
        "format": "PNG",
        "matrix": [1, 1],
        "renderer": "PyMuPDF",
    },
    "selected_json_scope": "EXHAUSTIVE_SELECTED_PAGE_SECTION_TABLE_SCAN",
    "source_scope": "FULL_BOUND_PDF_TEXT_SCAN_AND_BYTE_AUTHENTICATION",
}
_NOT_OBSERVED_DISPOSITION = (
    "ACCOUNTING_POLICY_ONLY_NO_TWO_PERIOD_DIRECT_COMPONENT_TABLE_IN_BOUND_REPORT"
)
_UNRESOLVED_DISPOSITION = (
    "DIRECT_COMPONENT_TABLE_PRESENT_BUT_SOURCE_VND_NOT_EXACT_INTEGER_MILLION_VND"
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_JSON_VERSION_ID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_PDF_TARGET_TERMS = (
    "cash and cash equivalents",
    "các khoản tương đương tiền cuối kỳ bao gồm",
    "tiền và các khoản tương đương tiền",
    "tiền và tương đương tiền",
)


class RunGeminiJsonCashEquivalentsV1Error(RuntimeError):
    """The Family-40 run, authentication, evidence, or replay drifted."""


def _error(message: str) -> RunGeminiJsonCashEquivalentsV1Error:
    return RunGeminiJsonCashEquivalentsV1Error(message)


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
        raise _error("Family-40 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-40 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-40 conclusion corpus is outside the current reporting scope")


def _validate_pdf_page_ref_v1(value: Any, *, rendered: bool) -> dict[str, Any]:
    expected = {"page_json_version_id", "physical_page"}
    if rendered:
        expected.add("pdf_page_render_sha256")
    if (
        type(value) is not dict
        or set(value) != expected
        or _PAGE_JSON_VERSION_ID.fullmatch(value.get("page_json_version_id", ""))
        is None
        or type(value.get("physical_page")) is not int
        or value["physical_page"] <= 0
        or (
            rendered
            and (
                _SHA256.fullmatch(value.get("pdf_page_render_sha256", "")) is None
            )
        )
    ):
        raise _error("Family-40 residual PDF page record is invalid")
    return canonical_clone_v1(value)


def _validate_pdf_residual_spec_v1(value: Any) -> dict[str, Any]:
    """Validate the immutable human-reviewed residual disposition frontier."""

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
        or type(value.get("corpus_manifest_index_id")) is not str
        or not value["corpus_manifest_index_id"]
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != PDF_RESIDUAL_FORMAT_VERSION
        or value.get("review_contract") != _PDF_REVIEW_CONTRACT
        or type(value.get("residuals")) is not list
        or value.get("residual_axis_sha256")
        != canonical_json_sha256_v1(value.get("residuals"))
    ):
        raise _error("Family-40 PDF residual audit spec is invalid")
    prior_ordinal = 0
    checked_residuals = []
    for residual in value["residuals"]:
        if (
            type(residual) is not dict
            or set(residual)
            != {
                "disposition",
                "document_ordinal",
                "pdf_page_count",
                "pdf_target_text_hit_axis",
                "reasons",
                "residual_audit_id",
                "review_page_axis",
                "selected_json_target_page_axis",
                "source_logical_name",
                "source_sha256",
                "source_size_bytes",
                "status",
            }
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior_ordinal
            or type(residual.get("source_logical_name")) is not str
            or not residual["source_logical_name"]
            or residual["source_logical_name"].startswith("/")
            or ".." in residual["source_logical_name"].split("/")
            or _SHA256.fullmatch(residual.get("source_sha256", "")) is None
            or type(residual.get("source_size_bytes")) is not int
            or residual["source_size_bytes"] <= 0
            or type(residual.get("pdf_page_count")) is not int
            or residual["pdf_page_count"] <= 0
            or residual.get("pdf_target_text_hit_axis") != []
            or type(residual.get("reasons")) is not list
            or type(residual.get("review_page_axis")) is not list
            or not residual["review_page_axis"]
            or type(residual.get("selected_json_target_page_axis")) is not list
            or not residual["selected_json_target_page_axis"]
        ):
            raise _error("Family-40 PDF residual record is invalid or unordered")
        if (
            residual["status"] == generic.NOT_OBSERVED
            and residual["reasons"] == []
            and residual["disposition"] == _NOT_OBSERVED_DISPOSITION
        ):
            pass
        elif (
            residual["status"] == generic.UNRESOLVED
            and residual["reasons"]
            and residual["disposition"] == _UNRESOLVED_DISPOSITION
        ):
            pass
        else:
            raise _error("Family-40 PDF residual status/disposition pairing is invalid")
        selected_axis = [
            _validate_pdf_page_ref_v1(page, rendered=False)
            for page in residual["selected_json_target_page_axis"]
        ]
        review_axis = [
            _validate_pdf_page_ref_v1(page, rendered=True)
            for page in residual["review_page_axis"]
        ]
        for name, axis in (
            ("selected JSON target", selected_axis),
            ("review", review_axis),
        ):
            numbers = [page["physical_page"] for page in axis]
            ids = [page["page_json_version_id"] for page in axis]
            if numbers != sorted(set(numbers)) or len(ids) != len(set(ids)):
                raise _error(f"Family-40 residual {name} page axis is not ordered and unique")
        if any(
            page["page_json_version_id"]
            not in {item["page_json_version_id"] for item in selected_axis}
            for page in review_axis
        ):
            raise _error("Family-40 residual review page is outside target JSON pages")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "gjcepdfv1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-40 PDF residual record identity drifted")
        prior_ordinal = residual["document_ordinal"]
        checked_residuals.append(canonical_clone_v1(residual))
    return {**canonical_clone_v1(value), "residuals": checked_residuals}


def _normalized_pdf_text_v1(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _pdf_target_text_hit_axis_v1(pdf: fitz.Document) -> list[int]:
    """Return every physical page containing an exact normalized F40 owner term."""

    normalized_terms = tuple(_normalized_pdf_text_v1(term) for term in _PDF_TARGET_TERMS)
    hits = []
    for physical_page, page in enumerate(pdf, start=1):
        text = _normalized_pdf_text_v1(page.get_text("text"))
        if any(term in text for term in normalized_terms):
            hits.append(physical_page)
    return hits


def _selected_json_target_page_axis_v1(
    *,
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    document_ordinal: int,
    source_sha256: str,
) -> list[dict[str, Any]]:
    """Find every selected JSON page with an F40 term on an audited surface."""

    selected = [
        item
        for item in selected_page_axis
        if item.get("document_ordinal") == document_ordinal
        and item.get("source_sha256") == source_sha256
    ]
    selected.sort(key=lambda item: item.get("physical_page"))
    selected_ids = [item.get("page_json_version_id") for item in selected]
    physical_pages = [item.get("physical_page") for item in selected]
    if (
        set(selected_ids) != set(page_json_by_version)
        or len(selected_ids) != len(page_json_by_version)
        or len(set(selected_ids)) != len(selected_ids)
        or physical_pages != sorted(set(physical_pages))
    ):
        raise _error("Family-40 selected JSON document frontier drifted")
    normalized_terms = tuple(_normalized_pdf_text_v1(term) for term in _PDF_TARGET_TERMS)

    def is_target(value: Any) -> bool:
        if type(value) is not str:
            return False
        normalized = _normalized_pdf_text_v1(value)
        return any(term in normalized for term in normalized_terms)

    result = []
    for item in selected:
        page = page_json_by_version[item["page_json_version_id"]]
        sections = page.get("sections")
        if type(sections) is not list:
            raise _error("Family-40 selected JSON page sections are invalid")
        target = False
        for section in sections:
            if type(section) is not dict:
                raise _error("Family-40 selected JSON section is invalid")
            surfaces = [section.get("title_exact")]
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                surfaces.extend(narratives)
            tables = section.get("tables")
            if type(tables) is list:
                for table in tables:
                    if type(table) is not dict:
                        raise _error("Family-40 selected JSON table is invalid")
                    surfaces.append(table.get("title_exact"))
                    rows = table.get("rows")
                    if type(rows) is list:
                        surfaces.extend(
                            row.get("label_exact")
                            for row in rows
                            if type(row) is dict
                        )
            if any(is_target(surface) for surface in surfaces):
                target = True
                break
        if target:
            result.append(
                {
                    "page_json_version_id": item["page_json_version_id"],
                    "physical_page": item["physical_page"],
                }
            )
    return result


def _authenticate_pdf_residuals_v1(
    *,
    spec: Mapping[str, Any],
    index: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, Mapping[str, Any]]],
    trials: Sequence[Mapping[str, Any]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    """Bind every residual to its exact trial, selected JSON, PDF, and render."""

    checked = _validate_pdf_residual_spec_v1(spec)
    if checked["corpus_manifest_index_id"] != index["corpus_manifest_index_id"]:
        raise _error("Family-40 PDF residual audit binds another corpus")
    expected_trials = [trial for trial in trials if trial["status"] != generic.READY]
    if [trial["document_ordinal"] for trial in expected_trials] != [
        residual["document_ordinal"] for residual in checked["residuals"]
    ]:
        raise _error("Family-40 PDF residual audit does not exhaust every N/U trial")
    document_by_ordinal = {
        document["source_ordinal"]: document for document in index["documents"]
    }
    selected_by_id = {
        page["page_json_version_id"]: page for page in selected_page_axis
    }
    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-40 PDF residual source root is unavailable")
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
            raise _error("Family-40 PDF residual source/trial binding drifted")
        document_pages = page_json_by_document.get(residual["document_ordinal"])
        if type(document_pages) is not dict:
            raise _error("Family-40 residual selected document pages are absent")
        for page in [
            *residual["selected_json_target_page_axis"],
            *residual["review_page_axis"],
        ]:
            selected = selected_by_id.get(page["page_json_version_id"])
            if (
                page["page_json_version_id"] not in document_pages
                or selected is None
                or selected.get("document_ordinal") != residual["document_ordinal"]
                or selected.get("physical_page") != page["physical_page"]
                or selected.get("source_sha256") != residual["source_sha256"]
            ):
                raise _error("Family-40 residual selected-page binding drifted")
        expected_target_axis = _selected_json_target_page_axis_v1(
            page_json_by_version=document_pages,
            selected_page_axis=selected_page_axis,
            document_ordinal=residual["document_ordinal"],
            source_sha256=residual["source_sha256"],
        )
        if expected_target_axis != residual["selected_json_target_page_axis"]:
            raise _error("Family-40 residual selected JSON target page axis drifted")
        path = (root / document["relative_path"]).resolve()
        if (
            not path.is_relative_to(root)
            or path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != document["source_size_bytes"]
            or _sha256(path) != document["source_sha256"]
        ):
            raise _error("Family-40 residual source PDF bytes drifted")
        render_axis = []
        with fitz.open(path) as pdf:
            if len(pdf) != residual["pdf_page_count"]:
                raise _error("Family-40 residual PDF page count drifted")
            if _pdf_target_text_hit_axis_v1(pdf) != residual[
                "pdf_target_text_hit_axis"
            ]:
                raise _error("Family-40 residual PDF target-text hit axis drifted")
            for page in residual["review_page_axis"]:
                if page["physical_page"] > len(pdf):
                    raise _error("Family-40 residual page is outside its source PDF")
                pixmap = pdf[page["physical_page"] - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                if sha256(pixmap.tobytes("png")).hexdigest() != page[
                    "pdf_page_render_sha256"
                ]:
                    raise _error("Family-40 residual PDF render drifted")
                render_axis.append(canonical_clone_v1(page))
        authenticated.append(
            {**canonical_clone_v1(residual), "review_page_axis": render_axis}
        )
    return authenticated


def _raw_repair_cell_v1(
    *, repair: Mapping[str, Any], pages: Mapping[str, Mapping[str, Any]]
) -> Any:
    locator = repair["locator"]
    try:
        page = pages[locator["page_json_version_id"]]
        section = page["sections"][int(locator["section_id"][1:]) - 1]
        table = section["tables"][int(locator["table_id"][1:]) - 1]
        row = table["rows"][locator["row_ordinal"] - 1]
        return row["values_exact"][locator["column_ordinal"] - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Family-40 source-repair selected JSON locator drifted") from exc


def _authenticate_source_repairs_v1(
    *,
    repairs: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
    selected_page_axis: Sequence[Mapping[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, Mapping[str, Any]]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    """Replay every registered full-page render and RGB crop binding."""

    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-40 source-PDF root is unavailable")
    document_by_sha = {
        document["source_sha256"]: document for document in index["documents"]
    }
    page_axis = {
        (page["source_sha256"], page["page_json_version_id"]): page
        for page in selected_page_axis
    }
    source_payloads: dict[tuple[str, str, int], bytes] = {}
    render_cache: dict[tuple[str, int], tuple[bytes, dict[str, Any]]] = {}
    checked = []
    for repair in repairs:
        source = repair["source"]
        locator = repair["locator"]
        document = document_by_sha.get(source["source_sha256"])
        if document is None:
            continue
        if (
            document["relative_path"] != source["source_logical_name"]
            or document["source_size_bytes"] != source["source_size_bytes"]
        ):
            raise _error("Family-40 source-repair document binding drifted")
        selected = page_axis.get(
            (source["source_sha256"], locator["page_json_version_id"])
        )
        if (
            selected is None
            or selected["physical_page"] != locator["physical_page"]
            or selected["document_ordinal"] != document["source_ordinal"]
            or _raw_repair_cell_v1(
                repair=repair,
                pages=page_json_by_document[document["source_ordinal"]],
            )
            is not repair["before_exact"]
        ):
            raise _error("Family-40 source-repair selected-page/cell binding drifted")
        logical_name = source["source_logical_name"]
        path = (root / logical_name).resolve()
        if (
            not path.is_relative_to(root)
            or path.is_symlink()
            or not path.is_file()
        ):
            raise _error("Family-40 source-repair PDF is unavailable")
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
                raise _error("Family-40 source-repair PDF bytes drifted")
            source_payloads[source_key] = payload
        render_key = (logical_name, locator["physical_page"])
        cached = render_cache.get(render_key)
        if cached is None:
            with fitz.open(stream=payload, filetype="pdf") as pdf:
                page_index = locator["physical_page"] - 1
                if not 0 <= page_index < len(pdf):
                    raise _error("Family-40 source-repair page is outside its PDF")
                rendered = render_full_pdf_page_v1(
                    pdf[page_index],
                    physical_page=locator["physical_page"],
                    dpi=300,
                    source_sha256=source["source_sha256"],
                )
            cached = rendered.image, rendered.receipt
            render_cache[render_key] = cached
        image_bytes, render_receipt = cached
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
        if actual_render != repair["render"] or actual_crop != repair["crop_evidence"]:
            raise _error("Family-40 source-repair render or crop evidence drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


def _build_trials_v1(
    *,
    indexed: Mapping[str, Any],
    pages: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_cash_equivalents_region_query_receipt_v1(regions)
        candidate = evaluate_gemini_json_cash_equivalents_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled_specs,
            query_receipt=receipt,
        )
        candidates_by_ordinal[ordinal] = (
            validate_gemini_json_cash_equivalents_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=pages[ordinal],
                compiled_specs=compiled_specs,
                query_receipt=receipt,
            )
        )
    return generic._trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)


def replay_cash_equivalents_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query and replay the complete Family-40 adapter from source JSON."""

    source_repairs = generic._json(SOURCE_REPAIR_PATH)
    family_compiled = bind_gemini_json_cash_equivalents_source_repairs_v1(
        compiled_specs, source_repairs
    )
    raw = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    pages = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=raw["selected_page_axis"],
    )
    indexed, _query_receipts = (
        adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1(
            raw,
            page_json_by_document=pages,
            compiled_specs=family_compiled,
        )
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-40 source replay rebuilt different query evidence")
    return _build_trials_v1(indexed=indexed, pages=pages, compiled_specs=family_compiled)


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
            raise _error("Family-40 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-40 historical oracle source identity is absent")
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
        raise _error("Family-40 historical corpus is not disjoint")
    return references, receipt


def _audit_axes_v1(
    *,
    trials: Sequence[dict[str, Any]],
    query_receipts: Sequence[Mapping[str, Any]],
    pdf_residuals: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "equations": [],
        "header_projections": [],
        "historical_comparator": [],
        "mappings": [],
        "partial_root_omissions": [],
        "pdf_residuals": canonical_clone_v1(list(pdf_residuals)),
        "primary_supplemental_projections": [],
        "query_recoveries": canonical_clone_v1(list(query_receipts)),
        "residuals": [],
        "source_repairs": [],
        "trials": canonical_clone_v1(list(trials)),
    }
    for trial in trials:
        if trial["status"] != generic.READY:
            axes["residuals"].append(
                {
                    "document_ordinal": trial["document_ordinal"],
                    "reasons": canonical_clone_v1(trial["reasons"]),
                    "source_logical_name": trial["source_logical_name"],
                    "source_sha256": trial["source_sha256"],
                    "status": trial["status"],
                }
            )
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        axes["mappings"].extend(canonical_clone_v1(candidate["mappings"]))
        axes["equations"].extend(
            canonical_clone_v1(candidate["closure_receipt"]["equations"])
        )
        adapter = candidate["closure_receipt"].get("cash_equivalents_adapter_receipt")
        if adapter is None:
            continue
        if type(adapter) is not dict:
            raise _error("Family-40 candidate adapter receipt is invalid")
        axes["source_repairs"].extend(
            canonical_clone_v1(adapter["authenticated_source_repairs"])
        )
        axes["header_projections"].extend(
            canonical_clone_v1(adapter["header_projection_receipts"])
        )
        partial = adapter["partial_root_omission_receipt"]
        if partial is not None:
            axes["partial_root_omissions"].append(canonical_clone_v1(partial))
        axes["primary_supplemental_projections"].extend(
            canonical_clone_v1(adapter["primary_supplemental_projection_receipts"])
        )
    return axes


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
        query_receipts=query_receipts,
        pdf_residuals=pdf_residuals,
    )
    oracle_refs, historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    expected_repairs = sorted(
        repair["repair_id"]
        for repair in compiled_specs["cash_equivalents_source_repairs"]
        if repair["locator"]["page_json_version_id"] in set(selected_ids)
    )
    applied_repairs = sorted(repair["repair_id"] for repair in axes["source_repairs"])
    authenticated_repairs = sorted(
        repair["repair_id"] for repair in source_authentications
    )
    if not (expected_repairs == applied_repairs == authenticated_repairs):
        raise _error("Family-40 repair application/authentication axis drifted")
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
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
        "source_observation_contract": canonical_clone_v1(observation_contract),
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
        "audit_id": "gjceauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _validate_audit_v1(value: Any) -> dict[str, Any]:
    axes = value.get("axes", {}) if type(value) is dict else {}
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or value.get("historical_comparator_policy_receipt", {}).get("policy")
        != DISJOINT_EXPANSION
        or value.get("historical_comparator_policy_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("source_observation_contract", {}).get("status") != "PASS"
        or value.get("source_observation_contract", {}).get("violation_count") != 0
        or value.get("axis_counts")
        != {name: len(axis) for name, axis in axes.items()}
        or value.get("axis_sha256")
        != {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
        or value.get("source_authentication_axis_sha256")
        != canonical_json_sha256_v1(value.get("source_authentication_axis", []))
        or len(axes.get("pdf_residuals", []))
        != sum(trial.get("status") != generic.READY for trial in axes.get("trials", []))
    ):
        raise _error("Family-40 audit content is invalid")
    material = {
        key: canonical_clone_v1(item) for key, item in value.items() if key != "audit_id"
    }
    if value.get("audit_id") != (
        "gjceauditv1:audit:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-40 audit identity drifted")
    return canonical_clone_v1(value)


def _implementation_refs(
    pdf_residual_audit_spec: Path,
    *,
    topology_spec: Path = TOPOLOGY_SPEC_PATH,
    evaluation_spec: Path = EVALUATION_SPEC_PATH,
    schema_binding_spec: Path = SCHEMA_BINDING_SPEC_PATH,
    source_repair_spec: Path = SOURCE_REPAIR_PATH,
) -> list[dict[str, Any]]:
    paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_cash_equivalents_accounting_family_v1.py",
        ADAPTER_PATH,
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        source_repair_spec,
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
    raw = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=raw["selected_page_axis"],
    )
    source_authentications = _authenticate_source_repairs_v1(
        repairs=compiled["cash_equivalents_source_repairs"],
        index=index,
        selected_page_axis=raw["selected_page_axis"],
        page_json_by_document=pages,
        source_pdf_root=args.source_pdf_root,
    )
    indexed, query_receipts = (
        adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1(
            raw,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )
    )
    trials = _build_trials_v1(indexed=indexed, pages=pages, compiled_specs=compiled)
    replayed = replay_cash_equivalents_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(selected_ids),
        compiled_specs=compile_gemini_json_flat_family_specs_v1(
            topology, evaluation, schema
        ),
        indexed_query_evidence=indexed,
    )
    if not same_typed_json_v1(replayed, trials):
        raise _error("Family-40 direct source replay returned different trials")
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
        raise _error("Family-40 sweep denominator drifted")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    pdf_residuals = _authenticate_pdf_residuals_v1(
        spec=generic._json(args.pdf_residual_audit_spec),
        index=index,
        selected_page_axis=raw["selected_page_axis"],
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
        / "scripts/experiments/run_gemini_json_cash_equivalents_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(
            args.pdf_residual_audit_spec,
            topology_spec=args.topology_spec,
            evaluation_spec=args.evaluation_spec,
            schema_binding_spec=args.schema_binding_spec,
            source_repair_spec=args.source_repair_spec,
        ),
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_cash_equivalents_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-40 sweep differs from authenticated evaluation")
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
    if args.historical_comparator_policy != DISJOINT_EXPANSION:
        raise _error("Family-40 current-corpus runner requires DISJOINT_EXPANSION")
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_spec)
    if not same_typed_json_v1(source_repairs, generic._json(SOURCE_REPAIR_PATH)):
        raise _error("Family-40 source-repair spec differs from its registered authority")
    compiled = compile_gemini_json_cash_equivalents_family_specs_v1(
        topology, evaluation, schema, source_repairs
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
    parser.add_argument(
        "--pdf-residual-audit-spec",
        type=Path,
        default=PDF_RESIDUAL_AUDIT_SPEC_PATH,
    )
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(DISJOINT_EXPANSION,),
        default=DISJOINT_EXPANSION,
    )
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
