#!/usr/bin/env python3
"""Run Family 31 over one authenticated current selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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
from bctc_ai.evaluation.gemini_json_fx_gold_activity_family_v1 import (  # noqa: E402
    FAMILY_ID,
    _apply_authenticated_source_repairs_v1,
    _exact_root_vector,
    adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1,
    build_gemini_json_fx_gold_activity_trials_v1,
    compile_gemini_json_fx_gold_activity_family_specs_v1,
    validate_gemini_json_fx_gold_activity_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    _unit_axis,
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

AUDIT_FORMAT_VERSION = "GEMINI_JSON_FX_GOLD_ACTIVITY_EXPERIMENTAL_AUDIT_V1"
SOURCE_ROW_COVERAGE_FORMAT_VERSION = "FAMILY31_SOURCE_ROW_COVERAGE_V1"
PRIMARY_PRESENTATION_FORMAT_VERSION = "FAMILY31_PRIMARY_ROOT_PRESENTATION_AUDIT_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-fx-gold-activity-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-fx-gold-activity-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = ROOT / "config/families/tm-fx-gold-activity-schema-binding-v1.json"
SOURCE_REPAIR_PATH = ROOT / "data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json"
ADAPTER_PATH = ROOT / "src/bctc_ai/evaluation/gemini_json_fx_gold_activity_family_v1.py"
SHARED_EVALUATOR_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"
)
SHARED_RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
PINNED_SHARED_EVALUATOR_SHA256 = "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
PINNED_SHARED_RUNNER_SHA256 = "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"


class RunGeminiJsonFxGoldActivityV1Error(RuntimeError):
    """The Family-31 run, authentication, evidence, or replay drifted."""


def _error(message: str) -> RunGeminiJsonFxGoldActivityV1Error:
    return RunGeminiJsonFxGoldActivityV1Error(message)


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
        raise _error("Family-31 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-31 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-31 conclusion corpus is outside the current reporting scope")


def _crop_rgb_sha256(pixmap: fitz.Pixmap, bbox: Sequence[int]) -> str:
    x0, y0, x1, y1 = bbox
    if (
        pixmap.alpha
        or pixmap.n != 3
        or not (0 <= x0 < x1 <= pixmap.width)
        or not (0 <= y0 < y1 <= pixmap.height)
    ):
        raise _error("Family-31 source-repair crop boundary drifted")
    samples = memoryview(pixmap.samples)
    row_width = (x1 - x0) * pixmap.n
    digest = sha256()
    for y in range(y0, y1):
        start = y * pixmap.stride + x0 * pixmap.n
        digest.update(samples[start : start + row_width])
    return digest.hexdigest()


def _authenticate_source_repair_images_v1(
    *, repairs: Sequence[Mapping[str, Any]], source_pdf_root: Path
) -> list[dict[str, Any]]:
    """Replay PDF bytes, exact 300-DPI pages, and every registered RGB crop."""

    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-31 source-PDF root is unavailable")
    payloads: dict[tuple[str, str], bytes] = {}
    rendered_pages: dict[tuple[str, int], fitz.Pixmap] = {}
    checked = []
    for repair in repairs:
        source = repair["source_binding"]
        logical_name = source["source_logical_name"]
        source_sha256 = source["source_sha256"]
        path = (root / logical_name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise _error("Family-31 source-repair PDF path is unavailable")
        source_key = (logical_name, source_sha256)
        payload = payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != source["source_size_bytes"]
                or sha256(payload).hexdigest() != source_sha256
            ):
                raise _error("Family-31 source-repair PDF bytes drifted")
            payloads[source_key] = payload
        page_key = (logical_name, source["physical_page"])
        pixmap = rendered_pages.get(page_key)
        if pixmap is None:
            try:
                with fitz.open(stream=payload, filetype="pdf") as document:
                    page_index = source["physical_page"] - 1
                    if not 0 <= page_index < len(document):
                        raise _error("Family-31 source-repair page is outside its PDF")
                    pixmap = document[page_index].get_pixmap(
                        dpi=source["render_dpi"],
                        colorspace=fitz.csRGB,
                        alpha=False,
                    )
            except (RuntimeError, ValueError) as exc:
                raise _error("Family-31 source-repair PDF cannot be rendered") from exc
            rendered_pages[page_key] = pixmap
        image = pixmap.tobytes("png")
        actual_image = {
            "image_sha256": sha256(image).hexdigest(),
            "image_size_bytes": len(image),
            "media_type": "image/png",
            "pixel_height": pixmap.height,
            "pixel_width": pixmap.width,
            "render_dpi": source["render_dpi"],
        }
        if any(source[key] != value for key, value in actual_image.items()):
            raise _error("Family-31 source-repair page render drifted")
        visual = repair["visual_evidence"]
        if (
            _crop_rgb_sha256(pixmap, visual["table_crop_bbox_pixels_xyxy"])
            != visual["table_crop_rgb_sha256"]
        ):
            raise _error("Family-31 source-repair table crop drifted")
        for cell in repair["cell_repairs"]:
            if _crop_rgb_sha256(pixmap, cell["crop_bbox_pixels_xyxy"]) != cell["crop_rgb_sha256"]:
                raise _error("Family-31 source-repair cell crop drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


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
            raise _error("Family-31 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-31 historical oracle source identity is absent")
            rows.append({"oracle_ref_index": reference_index, "source_sha256": source_sha256})
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
            trial["source_sha256"] for trial in trials if trial["candidate_count"] == 1
        ],
        current_selected_page_json_version_ids=list(selected_ids),
        strict_compare=None,
    )


def _source_ref_key(value: Any) -> tuple[str, str, str, int] | None:
    if type(value) is not dict or type(value.get("locator")) is not dict:
        return None
    locator = value["locator"]
    key = (
        locator.get("page_json_version_id"),
        locator.get("section_id"),
        locator.get("table_id"),
        value.get("row_ordinal"),
    )
    if all(type(item) is str and item for item in key[:3]) and type(key[3]) is int and key[3] > 0:
        return key
    return None


def _source_ref_paths(
    value: Any, path: tuple[Any, ...] = ()
) -> list[tuple[tuple[str, str, str, int], str]]:
    result = []
    if type(value) is dict:
        key = _source_ref_key(value)
        if key is not None:
            result.append((key, ":".join(str(item) for item in path if type(item) is str)))
        before_locator = value.get("before_locator")
        before_row_ordinal = value.get("before_row_ordinal")
        before_key = (
            (
                before_locator.get("page_json_version_id"),
                before_locator.get("section_id"),
                before_locator.get("table_id"),
                before_row_ordinal,
            )
            if type(before_locator) is dict
            else None
        )
        if (
            before_key is not None
            and all(type(item) is str and item for item in before_key[:3])
            and type(before_key[3]) is int
            and before_key[3] > 0
        ):
            result.append(
                (
                    before_key,
                    ":".join(str(item) for item in path if type(item) is str),
                )
            )
        for name, item in value.items():
            result.extend(_source_ref_paths(item, (*path, name)))
    elif type(value) is list:
        for ordinal, item in enumerate(value):
            result.extend(_source_ref_paths(item, (*path, ordinal)))
    return result


def _source_row_coverage_receipt_v1(
    *,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify every role, root, and unbound MONEY row in query inventory."""

    trial_by_ordinal = {item["document_ordinal"]: item for item in trials}
    inventory_by_ordinal = {item["document_ordinal"]: item for item in indexed["accepted_clusters"]}
    row_axis = []
    counts: Counter[str] = Counter()
    violations = []
    for document_ordinal in sorted(inventory_by_ordinal):
        trial = trial_by_ordinal.get(document_ordinal)
        document_inventory = inventory_by_ordinal[document_ordinal]
        pages = page_json_by_document.get(document_ordinal)
        if (
            type(trial) is not dict
            or type(pages) is not dict
            or type(trial.get("candidates")) is not list
            or len(trial["candidates"]) != 1
        ):
            raise _error("Family-31 source-row coverage trial axis is incomplete")
        candidate = trial["candidates"][0]
        target_inventory = [
            item
            for item in document_inventory["declared_money_table_inventory"]
            if item.get("classification", {}).get("role_hits")
            or item.get("classification", {}).get("family_root_row_ordinals")
        ]
        version_axis = {item["page_json_version_id"] for item in target_inventory}
        if not version_axis.issubset(pages):
            raise _error("Family-31 source-row coverage page axis is incomplete")
        effective_pages, _repair_receipts = _apply_authenticated_source_repairs_v1(
            pages={version_id: pages[version_id] for version_id in version_axis},
            compiled_specs=compiled_specs,
        )
        mapped_roles: defaultdict[tuple[str, str, str, int], set[str]] = defaultdict(set)
        for mapping in candidate["mappings"]:
            for ref in mapping.get("source_refs", []):
                key = _source_ref_key(ref)
                if key is not None:
                    mapped_roles[key].add(mapping["role"])
        evidence: defaultdict[tuple[str, str, str, int], set[str]] = defaultdict(set)
        for key, path in _source_ref_paths(candidate["closure_receipt"]):
            evidence[key].add(path)
        selected_tables = {
            (item["page_json_version_id"], item["section_id"], item["table_id"])
            for item in candidate["component_regions"]
        }
        validation_only = set(candidate["closure_receipt"].get("validation_only_roles", []))
        adapter_receipt = candidate["closure_receipt"].get("fx_gold_activity_adapter_receipt", {})
        continuation_receipt = (
            adapter_receipt.get("terminal_cong_continuation_projection_receipt")
            if type(adapter_receipt) is dict
            else None
        )
        continuation_boundary = None
        if type(continuation_receipt) is dict:
            receiver_table = continuation_receipt.get("receiver_table")
            if type(receiver_table) is dict and type(receiver_table.get("locator")) is dict:
                receiver_locator = receiver_table["locator"]
                continuation_boundary = (
                    (
                        receiver_locator.get("page_json_version_id"),
                        receiver_locator.get("section_id"),
                        receiver_locator.get("table_id"),
                    ),
                    receiver_table.get("leading_total_ordinal"),
                    receiver_table.get("first_following_row"),
                )
        for item in target_inventory:
            classification = item.get("classification")
            if type(classification) is not dict:
                raise _error("Family-31 declared table classification is absent")
            hits = list(classification.get("role_hits", []))
            classified_ordinals = {
                hit["row_ordinal"]
                for hit in hits
                if type(hit) is dict and type(hit.get("row_ordinal")) is int
            }
            hits.extend(
                {
                    "role": "FAMILY_ROOT_TOTAL",
                    "row_kind": None,
                    "row_ordinal": ordinal,
                }
                for ordinal in classification.get("family_root_row_ordinals", [])
                if ordinal not in classified_ordinals
            )
            classified_ordinals.update(
                hit["row_ordinal"]
                for hit in hits
                if type(hit) is dict and type(hit.get("row_ordinal")) is int
            )
            hits.extend(
                {
                    "role": "UNBOUND_MONEY_ROW",
                    "row_kind": None,
                    "row_ordinal": ordinal,
                }
                for ordinal in classification.get("unbound_money_row_ordinals", [])
                if ordinal not in classified_ordinals
            )
            if not hits:
                continue
            locator = (
                item["page_json_version_id"],
                item["section_id"],
                item["table_id"],
            )
            page = effective_pages[item["page_json_version_id"]]
            try:
                section = page["sections"][int(item["section_id"][1:]) - 1]
                table = section["tables"][int(item["table_id"][1:]) - 1]
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise _error("Family-31 source-row coverage locator drifted") from exc
            money_ordinals = classification["money_column_ordinals"]
            for hit in hits:
                row_ordinal = hit["row_ordinal"]
                try:
                    row = table["rows"][row_ordinal - 1]
                    cells = [
                        {
                            "column_ordinal": ordinal,
                            "source_text": row["values_exact"][ordinal - 1],
                        }
                        for ordinal in money_ordinals
                    ]
                except (KeyError, IndexError, TypeError) as exc:
                    raise _error("Family-31 source-row coverage row drifted") from exc
                key = (*locator, row_ordinal)
                source_visible = any(cell["source_text"] is not None for cell in cells)
                paths = sorted(evidence[key])
                roles = sorted(mapped_roles[key])
                query_disposition = item["disposition"]
                role = hit["role"]
                typed_control = classification.get("typed_control_disposition")
                if role in mapped_roles[key]:
                    disposition = "DIRECT_MAPPING_SOURCE"
                elif role in validation_only and locator in selected_tables:
                    disposition = "SELECTED_VALIDATION_ONLY_SOURCE"
                elif paths and locator in selected_tables:
                    disposition = "SELECTED_EXACT_PROOF_SOURCE"
                elif not source_visible and (hit.get("row_kind") or row.get("row_kind")) == "GROUP":
                    disposition = "ALL_BLANK_STRUCTURAL_GROUP_NONOBSERVATION"
                elif typed_control == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY":
                    disposition = "PRIMARY_STATEMENT_ALTERNATE_SOURCE_RESULT"
                elif query_disposition == "EXCLUDED_TYPED_CONTROL":
                    disposition = "TYPED_CONTROL_OUTSIDE_F31"
                elif query_disposition == "OUTSIDE_SELECTED_OWNER_FENCE":
                    disposition = "OUTSIDE_SELECTED_F31_OWNER_FENCE"
                elif (
                    query_disposition
                    == "SELECTED_RECIPROCAL_TERMINAL_CONG_RECEIVER_AFTER_FAMILY31_RECEIPT"
                    and continuation_boundary is not None
                    and locator == continuation_boundary[0]
                    and type(continuation_boundary[1]) is int
                    and row_ordinal > continuation_boundary[1]
                    and type(continuation_boundary[2]) is dict
                    and continuation_boundary[2].get("row_kind") == "GROUP"
                ):
                    disposition = "AFTER_EXPLICIT_F31_TERMINAL_STRUCTURAL_RESET"
                elif paths:
                    disposition = "UNSELECTED_EXACT_PROOF_SOURCE"
                else:
                    disposition = "UNACCOUNTED_F31_SOURCE_ROW"
                    violations.append(
                        {
                            "document_ordinal": document_ordinal,
                            "label_exact": row.get("label_exact"),
                            "locator": list(locator),
                            "query_disposition": query_disposition,
                            "role": role,
                            "row_ordinal": row_ordinal,
                            "source_visible": source_visible,
                        }
                    )
                counts[disposition] += 1
                row_axis.append(
                    {
                        "coverage_disposition": disposition,
                        "document_ordinal": document_ordinal,
                        "hierarchy_path_exact": row.get("hierarchy_path_exact"),
                        "label_exact": row.get("label_exact"),
                        "locator": {
                            "page_json_version_id": locator[0],
                            "physical_page": item["physical_page"],
                            "section_id": locator[1],
                            "table_id": locator[2],
                        },
                        "mapped_roles": roles,
                        "query_disposition": query_disposition,
                        "receipt_paths": paths,
                        "role": role,
                        "row_kind": hit.get("row_kind") or row.get("row_kind"),
                        "row_ordinal": row_ordinal,
                        "source_cells": cells,
                        "source_visible": source_visible,
                        "table_selected": locator in selected_tables,
                    }
                )
    material = {
        "claim_boundary": (
            "EVERY_CONFIGURED_ROLE_FAMILY_ROOT_OR_UNBOUND_MONEY_ROW_IN_EVERY_"
            "DECLARED_MONEY_TABLE_IS_MAPPED_PROOF_ONLY_TYPED_NONOBSERVATION_OR_"
            "EXPLICIT_QUERY_SCOPE_EXCLUDED_WITH_SOURCE_CELLS_RETAINED"
        ),
        "disposition_counts": dict(sorted(counts.items())),
        "format_version": SOURCE_ROW_COVERAGE_FORMAT_VERSION,
        "indexed_query_evidence_id": indexed["query_evidence_id"],
        "row_axis": row_axis,
        "row_axis_sha256": canonical_json_sha256_v1(row_axis),
        "trial_axis_sha256": canonical_json_sha256_v1(trials),
        "violation_count": len(violations),
        "violations": violations,
    }
    return {
        **material,
        "receipt_id": "f31srcrowv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _exact_million_scale_relation(
    *,
    source_vector: Sequence[Any],
    source_unit: str,
    mapped_vector: Sequence[Any],
    mapped_unit: str,
) -> bool:
    if (
        {source_unit, mapped_unit} != {"VND", "MILLION_VND"}
        or len(source_vector) != len(mapped_vector)
        or any(type(value) is not int for value in [*source_vector, *mapped_vector])
    ):
        return False
    if source_unit == "VND":
        return all(value % 1_000_000 == 0 for value in source_vector) and [
            value // 1_000_000 for value in source_vector
        ] == list(mapped_vector)
    return all(value % 1_000_000 == 0 for value in mapped_vector) and [
        value // 1_000_000 for value in mapped_vector
    ] == list(source_vector)


def _within_explicit_million_display_interval(
    *,
    source_vector: Sequence[Any],
    source_unit: str,
    mapped_vector: Sequence[Any],
    mapped_unit: str,
) -> bool:
    """Describe, but never select by, an explicit VND/million display relation."""

    return (
        source_unit == "VND"
        and mapped_unit == "MILLION_VND"
        and len(source_vector) == len(mapped_vector)
        and all(type(value) is int for value in [*source_vector, *mapped_vector])
        and all(
            abs(source - mapped * 1_000_000) < 500_000
            for source, mapped in zip(source_vector, mapped_vector, strict=True)
        )
    )


def _primary_root_presentation_receipt_v1(
    *,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind every primary income-statement FX/gold presentation without routing by value."""

    trial_by_ordinal = {item["document_ordinal"]: item for item in trials}
    inventory_by_ordinal = {item["document_ordinal"]: item for item in indexed["accepted_clusters"]}
    axis = []
    counts: Counter[str] = Counter()
    violations = []
    for document_ordinal in sorted(inventory_by_ordinal):
        trial = trial_by_ordinal.get(document_ordinal)
        pages = page_json_by_document.get(document_ordinal)
        if type(trial) is not dict or type(pages) is not dict:
            raise _error("Family-31 primary-root audit trial/page axis is incomplete")
        root_mappings = [
            mapping for mapping in trial["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
        ]
        if len(root_mappings) != 1:
            raise _error("Family-31 root mapping is not unique")
        root_mapping = root_mappings[0]
        mapped_vector = [cell.get("coefficient") for cell in root_mapping["values"]]
        mapped_unit = root_mapping["unit"]
        primary_items = [
            item
            for item in inventory_by_ordinal[document_ordinal]["declared_money_table_inventory"]
            if item.get("classification", {}).get("typed_control_disposition")
            == "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
            and item.get("classification", {}).get("family_root_row_ordinals")
        ]
        if not primary_items:
            violations.append(
                {
                    "document_ordinal": document_ordinal,
                    "reason": "PRIMARY_FX_GOLD_RESULT_PRESENTATION_ABSENT",
                }
            )
            continue
        effective_pages, _repair_receipts = _apply_authenticated_source_repairs_v1(
            pages={
                item["page_json_version_id"]: pages[item["page_json_version_id"]]
                for item in primary_items
            },
            compiled_specs=compiled_specs,
        )
        for item in primary_items:
            page = effective_pages[item["page_json_version_id"]]
            try:
                section = page["sections"][int(item["section_id"][1:]) - 1]
                table = section["tables"][int(item["table_id"][1:]) - 1]
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise _error("Family-31 primary-root presentation locator drifted") from exc
            root = _exact_root_vector(
                section=section,
                table=table,
                compiled_specs=compiled_specs,
            )
            unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
            if root is None:
                disposition = "PRIMARY_ROOT_VECTOR_NOT_LOCALLY_EXACT"
            elif unit_axis.get("complete") is True:
                source_unit = unit_axis["canonical_unit"]
                if source_unit == mapped_unit and root["vector"] == mapped_vector:
                    disposition = "EXACT_SAME_UNIT_AND_VECTOR"
                elif _exact_million_scale_relation(
                    source_vector=root["vector"],
                    source_unit=source_unit,
                    mapped_vector=mapped_vector,
                    mapped_unit=mapped_unit,
                ):
                    disposition = "EXPLICIT_VND_MILLION_ALTERNATE_PRESENTATION_EXACT_SCALE"
                elif _within_explicit_million_display_interval(
                    source_vector=root["vector"],
                    source_unit=source_unit,
                    mapped_vector=mapped_vector,
                    mapped_unit=mapped_unit,
                ):
                    disposition = (
                        "EXPLICIT_VND_PRIMARY_PRESENTATION_WITHIN_SELECTED_"
                        "MILLION_DISPLAY_INTERVAL_NOT_USED_FOR_ROUTING"
                    )
                else:
                    disposition = "EXPLICIT_PRIMARY_PRESENTATION_DIFFERS_FROM_SELECTED_GRAPH"
            elif (
                not unit_axis.get("evidence")
                and not unit_axis.get("undeclared_evidence")
                and root["vector"] == mapped_vector
            ):
                disposition = "EXACT_VECTOR_WITHOUT_LOCAL_PRIMARY_UNIT"
            else:
                disposition = "PRIMARY_PRESENTATION_UNIT_OR_VECTOR_UNRESOLVED"
            counts[disposition] += 1
            record = {
                "disposition": disposition,
                "document_ordinal": document_ordinal,
                "locator": {
                    "page_json_version_id": item["page_json_version_id"],
                    "physical_page": item["physical_page"],
                    "section_id": item["section_id"],
                    "table_id": item["table_id"],
                },
                "mapped_root_state": root_mapping["state"],
                "mapped_unit": mapped_unit,
                "mapped_vector": mapped_vector,
                "primary_root": root,
                "primary_unit_axis": unit_axis,
                "source_logical_name": trial["source_logical_name"],
                "source_sha256": trial["source_sha256"],
            }
            axis.append(record)
            if disposition in {
                "PRIMARY_ROOT_VECTOR_NOT_LOCALLY_EXACT",
                "PRIMARY_PRESENTATION_UNIT_OR_VECTOR_UNRESOLVED",
            }:
                violations.append(record)
    material = {
        "claim_boundary": (
            "EVERY_PRIMARY_INCOME_STATEMENT_FX_GOLD_ROOT_PRESENTATION_IS_BOUND_"
            "TO_ITS_EXACT_SOURCE_VECTOR_AND_LOCAL_UNIT_WITH_ALTERNATE_"
            "PRESENTATIONS_RECORDED_BUT_NEVER_USED_FOR_SCALE_INFERENCE_OR_"
            "VALUE_SELECTION"
        ),
        "disposition_counts": dict(sorted(counts.items())),
        "format_version": PRIMARY_PRESENTATION_FORMAT_VERSION,
        "indexed_query_evidence_id": indexed["query_evidence_id"],
        "presentation_axis": axis,
        "presentation_axis_sha256": canonical_json_sha256_v1(axis),
        "trial_axis_sha256": canonical_json_sha256_v1(trials),
        "violation_count": len(violations),
        "violations": violations,
    }
    return {
        **material,
        "receipt_id": "f31prpav1:receipt:" + canonical_json_sha256_v1(material),
    }


def _audit_axes(
    *,
    trials: Sequence[dict[str, Any]],
    query_adapter_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "adapter_receipts": [],
        "equations": [],
        "mappings": [],
        "query_adapter_receipts": canonical_clone_v1(list(query_adapter_receipts)),
        "source_repairs": [],
        "trials": canonical_clone_v1(list(trials)),
    }
    for trial in trials:
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        axes["mappings"].extend(canonical_clone_v1(candidate.get("mappings", [])))
        closure = candidate.get("closure_receipt", {})
        axes["equations"].extend(canonical_clone_v1(closure.get("equations", [])))
        adapter = closure.get("fx_gold_activity_adapter_receipt")
        if type(adapter) is not dict:
            continue
        axes["adapter_receipts"].append(canonical_clone_v1(adapter))
        axes["source_repairs"].extend(canonical_clone_v1(adapter.get("source_repair_receipts", [])))
    return axes


def build_fx_gold_activity_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    output: Path,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    query_adapter_receipts: Sequence[Mapping[str, Any]],
    historical_receipt: Mapping[str, Any],
    observation_contract: Mapping[str, Any],
    source_authentications: Sequence[Mapping[str, Any]],
    source_row_coverage: Mapping[str, Any],
    primary_presentations: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    axes = _audit_axes(
        trials=trials,
        query_adapter_receipts=query_adapter_receipts,
    )
    material = {
        "axis_counts": {key: len(value) for key, value in axes.items()},
        "axis_sha256": {key: canonical_json_sha256_v1(value) for key, value in axes.items()},
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": canonical_clone_v1(historical_receipt),
        "indexed_query_receipt": canonical_clone_v1(indexed["query_receipt"]),
        "primary_root_presentation_receipt": canonical_clone_v1(primary_presentations),
        "source_authentication_axis": canonical_clone_v1(list(source_authentications)),
        "source_authentication_axis_sha256": canonical_json_sha256_v1(source_authentications),
        "source_authentication_count": len(source_authentications),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "source_row_coverage_receipt": canonical_clone_v1(source_row_coverage),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_output": str(output),
    }
    return {
        **material,
        "audit_id": "gjfgaauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_fx_gold_activity_experimental_audit_v1(value: Any) -> dict[str, Any]:
    source_coverage = value.get("source_row_coverage_receipt") if type(value) is dict else None
    primary_presentations = (
        value.get("primary_root_presentation_receipt") if type(value) is dict else None
    )
    source_coverage_material = (
        {key: item for key, item in source_coverage.items() if key != "receipt_id"}
        if type(source_coverage) is dict
        else None
    )
    primary_material = (
        {key: item for key, item in primary_presentations.items() if key != "receipt_id"}
        if type(primary_presentations) is dict
        else None
    )
    axis_counts = value.get("axis_counts") if type(value) is dict else None
    axis_sha256 = value.get("axis_sha256") if type(value) is dict else None
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or type(axis_counts) is not dict
        or type(axis_sha256) is not dict
        or set(axis_counts) != set(axis_sha256)
        or any(type(item) is not int or item < 0 for item in axis_counts.values())
        or any(type(item) is not str or len(item) != 64 for item in axis_sha256.values())
        or value.get("historical_comparator_policy_receipt", {}).get("policy") != DISJOINT_EXPANSION
        or value.get("historical_comparator_policy_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("historical_comparator_policy_receipt", {})
        .get("corpus_relation", {})
        .get("overlap_count")
        != 0
        or value.get("source_observation_contract", {}).get("violation_count") != 0
        or type(source_coverage) is not dict
        or source_coverage.get("format_version") != SOURCE_ROW_COVERAGE_FORMAT_VERSION
        or source_coverage.get("violation_count") != 0
        or source_coverage.get("row_axis_sha256")
        != canonical_json_sha256_v1(source_coverage.get("row_axis"))
        or source_coverage.get("receipt_id")
        != "f31srcrowv1:receipt:" + canonical_json_sha256_v1(source_coverage_material)
        or type(primary_presentations) is not dict
        or primary_presentations.get("format_version") != PRIMARY_PRESENTATION_FORMAT_VERSION
        or primary_presentations.get("violation_count") != 0
        or primary_presentations.get("presentation_axis_sha256")
        != canonical_json_sha256_v1(primary_presentations.get("presentation_axis"))
        or primary_presentations.get("receipt_id")
        != "f31prpav1:receipt:" + canonical_json_sha256_v1(primary_material)
        or type(value.get("source_authentication_axis")) is not list
        or type(value.get("source_authentication_count")) is not int
        or value["source_authentication_count"] != len(value["source_authentication_axis"])
        or value.get("source_authentication_axis_sha256")
        != canonical_json_sha256_v1(value["source_authentication_axis"])
    ):
        raise _error("Family-31 experimental audit content is invalid")
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "audit_id"}
    if value.get("audit_id") != "gjfgaauditv1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family-31 experimental audit identity drifted")
    return canonical_clone_v1(value)


def replay_fx_gold_activity_trials_from_source_v1(
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
    generic_compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if not same_typed_json_v1(generic_compiled, compiled_specs):
        raise _error("Family-31 source replay declarative specs drifted")
    family_compiled = compile_gemini_json_fx_gold_activity_family_specs_v1(
        topology,
        evaluation,
        schema,
        generic._json(SOURCE_REPAIR_PATH),
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
    indexed, _query_receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        base,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-31 source replay rebuilt different query evidence")
    trials = build_gemini_json_fx_gold_activity_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    validate_gemini_json_fx_gold_activity_replay_v1(
        base_indexed_query_evidence=base,
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    return trials


def _implementation_refs() -> list[dict[str, Any]]:
    paths = (
        ROOT / "scripts/experiments/run_gemini_json_fx_gold_activity_accounting_family_v1.py",
        ADAPTER_PATH,
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
        SOURCE_REPAIR_PATH,
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
    checked_source_repairs = _authenticate_source_repair_images_v1(
        repairs=compiled["fx_gold_activity_source_repair_overlay"]["repairs"],
        source_pdf_root=args.source_pdf_root,
    )
    if not same_typed_json_v1(
        checked_source_repairs,
        compiled["fx_gold_activity_source_repair_overlay"]["repairs"],
    ):
        raise _error("Family-31 source-repair authentication axis drifted")
    indexed, query_adapter_receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_fx_gold_activity_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    replay_receipt = validate_gemini_json_fx_gold_activity_replay_v1(
        base_indexed_query_evidence=base,
        indexed_query_evidence=indexed,
        trials=trials,
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
    if sweep["metrics"].get("document_count") != len(index["documents"]) or any(
        sweep["metrics"].get(key) != expected
        for key, expected in (
            ("ready_count", len(index["documents"])),
            ("not_observed_count", 0),
            ("unresolved_count", 0),
        )
    ):
        raise _error("Family-31 current corpus is not completely schema-mappable")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled,
    )
    source_row_coverage = _source_row_coverage_receipt_v1(
        indexed=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    primary_presentations = _primary_root_presentation_receipt_v1(
        indexed=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    if source_row_coverage["violation_count"] or primary_presentations["violation_count"]:
        raise _error("Family-31 source inventory or primary presentation is incomplete")
    audit = build_fx_gold_activity_experimental_audit_v1(
        sweep=sweep,
        output=args.output,
        indexed=indexed,
        trials=trials,
        query_adapter_receipts=query_adapter_receipts,
        historical_receipt=historical_receipt,
        observation_contract=observation_contract,
        source_authentications=checked_source_repairs,
        source_row_coverage=source_row_coverage,
        primary_presentations=primary_presentations,
        spec_refs={**spec_refs, "replay_receipt": replay_receipt},
    )
    validate_fx_gold_activity_experimental_audit_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    runner_ref = generic._file_ref(
        ROOT / "scripts/experiments/run_gemini_json_fx_gold_activity_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(),
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_fx_gold_activity_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-31 sweep differs from authenticated evaluation")
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
        "primary_root_presentation_receipt_id": primary_presentations["receipt_id"],
        "results_database": str(args.results_database),
        "run_kind": "EXPERIMENTAL",
        "source_authentication_axis_sha256": audit["source_authentication_axis_sha256"],
        "source_authentication_count": audit["source_authentication_count"],
        "source_row_coverage_receipt_id": source_row_coverage["receipt_id"],
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.historical_comparator_policy != DISJOINT_EXPANSION:
        raise _error("Family-31 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_spec)
    compiled = compile_gemini_json_fx_gold_activity_family_specs_v1(
        topology, evaluation, schema, source_repairs
    )
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
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
    parser.add_argument("--schema-binding-spec", type=Path, default=SCHEMA_BINDING_SPEC_PATH)
    parser.add_argument("--source-repair-spec", type=Path, default=SOURCE_REPAIR_PATH)
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
