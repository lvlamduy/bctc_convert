#!/usr/bin/env python3
"""Run Family 22 over one authenticated current selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping
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
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
)
from bctc_ai.evaluation.gemini_json_other_assets_family_v1 import (  # noqa: E402
    adapt_gemini_json_other_assets_indexed_query_evidence_v1,
    evaluate_gemini_json_other_assets_family_cluster_v1,
    validate_gemini_json_other_assets_family_candidate_replay_v1,
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

FAMILY_ID = "OTHER_ASSETS"
AUDIT_FORMAT_VERSION = "GEMINI_JSON_OTHER_ASSETS_CURRENT_CORPUS_AUDIT_V1"
PDF_RESIDUAL_FORMAT_VERSION = "OTHER_ASSETS_PDF_RESIDUAL_AUDIT_SPEC_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-other-assets-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-other-assets-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = (
    ROOT / "config/families/tm-other-assets-schema-binding-v1.json"
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
F26_REPORT_NORM_IDS = frozenset({982, 983, 984, 985, 986})


class RunGeminiJsonOtherAssetsAccountingFamilyV1Error(RuntimeError):
    """The Family-22 current-corpus run or its evidence drifted."""


def _error(message: str) -> RunGeminiJsonOtherAssetsAccountingFamilyV1Error:
    return RunGeminiJsonOtherAssetsAccountingFamilyV1Error(message)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _assert_shared_implementation_pins_v1() -> None:
    expected = {
        SHARED_EVALUATOR_PATH: PINNED_SHARED_EVALUATOR_SHA256,
        SHARED_RUNNER_PATH: PINNED_SHARED_RUNNER_SHA256,
    }
    drifted = [str(path) for path, digest in expected.items() if _sha256(path) != digest]
    if drifted:
        raise _error("Family-22 shared implementation pin drifted: " + ",".join(drifted))


def _source_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if not path.is_relative_to(resolved_root) or path.is_symlink() or not path.is_file():
        raise _error("Family-22 source PDF path is unavailable or escapes its root")
    return path


def _assert_current_corpus(index: dict[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-22 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-22 conclusion corpus includes a pre-2025 document")


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
            raise _error("Family-22 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-22 historical oracle source identity is absent")
            rows.append(
                {"oracle_ref_index": reference_index, "source_sha256": source_sha256}
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
        trial["source_sha256"] for trial in trials if trial["candidate_count"] == 1
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
        "alpha": False,
        "colorspace": "RGB",
        "format": "PNG",
        "matrix": [1, 1],
        "renderer": "PyMuPDF",
        "scope": (
            "EVERY_PRIMARY_BALANCE_STATEMENT_PAGE_FOR_EVERY_NOT_OBSERVED_DOCUMENT"
        ),
        "visual_disposition_rule": (
            "NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY22_ROOT_OR_DETAIL_ROW"
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
        raise _error("Family-22 PDF residual audit spec is invalid")
    prior = 0
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
            != "TRUE_NOT_OBSERVED_NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY22_ROW"
            or type(residual.get("document_ordinal")) is not int
            or residual["document_ordinal"] <= prior
            or type(residual.get("balance_sheet_page_axis")) is not list
            or not residual["balance_sheet_page_axis"]
        ):
            raise _error("Family-22 PDF residual record is invalid or unordered")
        material = {
            key: canonical_clone_v1(item)
            for key, item in residual.items()
            if key != "residual_audit_id"
        }
        if residual.get("residual_audit_id") != (
            "goaav1:residual:" + canonical_json_sha256_v1(material)
        ):
            raise _error("Family-22 PDF residual record identity drifted")
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
                or type(page.get("physical_page")) is not int
                or type(page.get("page_json_version_id")) is not str
                or type(page.get("pdf_page_render_sha256")) is not str
                or len(page["pdf_page_render_sha256"]) != 64
            ):
                raise _error("Family-22 residual PDF page record is invalid")
            page_numbers.append(page["physical_page"])
        if page_numbers != sorted(set(page_numbers)):
            raise _error("Family-22 residual balance-page axis is not ordered and unique")
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
        raise _error("Family-22 PDF residual audit binds another corpus")
    unresolved = [
        {
            "document_ordinal": trial["document_ordinal"],
            "reasons": canonical_clone_v1(trial.get("reasons", [])),
        }
        for trial in trials
        if trial["status"] == UNRESOLVED
    ]
    if unresolved:
        raise _error(
            "Family-22 current sweep retains unresolved documents:"
            + json.dumps(unresolved, ensure_ascii=False, sort_keys=True)
        )
    expected = {
        trial["source_sha256"] for trial in trials if trial["status"] == NOT_OBSERVED
    }
    actual = {residual["source_sha256"] for residual in checked["residuals"]}
    if actual != expected:
        raise _error("Family-22 PDF residual audit does not exhaust every N trial")
    documents = {item["source_ordinal"]: item for item in index["documents"]}
    selected_pages = {item["page_json_version_id"]: item for item in selected_page_axis}
    authenticated = []
    for residual in checked["residuals"]:
        document = documents.get(residual["document_ordinal"])
        if (
            document is None
            or document["relative_path"] != residual["source_logical_name"]
            or document["source_sha256"] != residual["source_sha256"]
            or document["source_size_bytes"] != residual["source_size_bytes"]
        ):
            raise _error("Family-22 PDF residual source binding drifted")
        path = _source_path(source_pdf_root, document["relative_path"])
        if path.stat().st_size != document["source_size_bytes"] or _sha256(path) != document[
            "source_sha256"
        ]:
            raise _error("Family-22 PDF residual source bytes drifted")
        render_axis = []
        with fitz.open(path) as pdf:
            for page in residual["balance_sheet_page_axis"]:
                selected = selected_pages.get(page["page_json_version_id"])
                if (
                    page["physical_page"] > len(pdf)
                    or selected is None
                    or selected.get("source_sha256") != residual["source_sha256"]
                    or selected.get("physical_page") != page["physical_page"]
                ):
                    raise _error("Family-22 residual selected-page binding drifted")
                pixmap = pdf[page["physical_page"] - 1].get_pixmap(
                    matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
                )
                digest = sha256(pixmap.tobytes("png")).hexdigest()
                if digest != page["pdf_page_render_sha256"]:
                    raise _error("Family-22 residual PDF render drifted")
                render_axis.append(canonical_clone_v1(page))
        authenticated.append(
            {
                **{
                    key: canonical_clone_v1(item)
                    for key, item in residual.items()
                    if key != "source_size_bytes"
                },
                "balance_sheet_page_axis": render_axis,
            }
        )
    return authenticated


def _semantic_axes(trials: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    clusters = []
    equations = []
    mappings = []
    for trial in trials:
        if trial["status"] != READY:
            continue
        candidates = trial["candidates"]
        if type(candidates) is not list or len(candidates) != 1:
            raise _error("Family-22 ready trial does not bind exactly one candidate")
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
            }
        )
        mappings.extend(
            {**identity, "mapping": canonical_clone_v1(mapping)}
            for mapping in candidate["mappings"]
        )
        equations.extend(
            {**identity, "equation": canonical_clone_v1(equation)}
            for equation in candidate["closure_receipt"].get("equations", [])
        )
    return {"clusters": clusters, "equations": equations, "mappings": mappings}


def _coverage_source_ref_key_v1(value: Any) -> tuple[str, str, str, int] | None:
    if type(value) is not dict or type(value.get("locator")) is not dict:
        return None
    locator = value["locator"]
    key = (
        locator.get("page_json_version_id"),
        locator.get("section_id"),
        locator.get("table_id"),
        value.get("row_ordinal"),
    )
    if not (
        all(type(item) is str and item for item in key[:3])
        and type(key[3]) is int
        and key[3] > 0
    ):
        return None
    return key


def _coverage_source_ref_paths_v1(
    value: Any, *, path: tuple[str | int, ...] = ()
) -> list[tuple[tuple[str, str, str, int], str]]:
    result = []
    if type(value) is dict:
        key = _coverage_source_ref_key_v1(value)
        if key is not None:
            named_path = [str(item) for item in path if type(item) is str]
            result.append((key, ":".join(named_path) or "SOURCE_REF"))
        for name, item in value.items():
            result.extend(
                _coverage_source_ref_paths_v1(item, path=(*path, name))
            )
    elif type(value) is list:
        for ordinal, item in enumerate(value):
            result.extend(
                _coverage_source_ref_paths_v1(item, path=(*path, ordinal))
            )
    return result


def _coverage_source_table_v1(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> dict[str, Any]:
    try:
        section = page_json["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Family-22 source-role coverage locator does not resolve") from exc
    if type(section) is not dict or type(table) is not dict:
        raise _error("Family-22 source-role coverage table is invalid")
    return table


def build_source_role_coverage_receipt_v1(
    *,
    indexed_query_evidence: dict[str, Any],
    trials: list[dict[str, Any]],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Account for every configured role hit without treating blanks as zero."""

    trial_by_ordinal = {trial["document_ordinal"]: trial for trial in trials}
    row_axis = []
    adapter_table_axis = []
    violations = []
    disposition_counts: dict[str, int] = defaultdict(int)
    selected_dispositions = {
        "SELECTED_FAMILY_COMPONENT",
        "SELECTED_EXACT_FAMILY22_ONE_SIDED_CONTINUATION",
    }
    allowed_query_dispositions = selected_dispositions | {
        "EXCLUDED_EXACT_FAMILY22_PROVISION_CONTROL",
        "EXCLUDED_TYPED_CONTROL",
        "OUTSIDE_SELECTED_OWNER_FENCE",
    }

    for cluster in indexed_query_evidence.get("accepted_clusters", []):
        document_ordinal = cluster["document_ordinal"]
        trial = trial_by_ordinal.get(document_ordinal)
        pages = page_json_by_document.get(document_ordinal)
        if (
            type(trial) is not dict
            or trial.get("status") != READY
            or type(trial.get("candidates")) is not list
            or len(trial["candidates"]) != 1
            or type(pages) is not dict
        ):
            raise _error("Family-22 source-role coverage lacks one ready source trial")
        candidate = trial["candidates"][0]
        closure = candidate.get("closure_receipt")
        if type(closure) is not dict:
            raise _error("Family-22 source-role coverage closure receipt is absent")

        mapping_roles: dict[tuple[str, str, str, int], set[str]] = defaultdict(set)
        receipt_kinds: dict[tuple[str, str, str, int], set[str]] = defaultdict(set)
        for mapping in candidate.get("mappings", []):
            for source_ref in mapping.get("source_refs", []):
                key = _coverage_source_ref_key_v1(source_ref)
                if key is not None:
                    mapping_roles[key].add(mapping["role"])
        for key, receipt_kind in _coverage_source_ref_paths_v1(closure):
            receipt_kinds[key].add(receipt_kind)

        validation_only_roles = set(closure.get("validation_only_roles", []))
        for table_receipt in closure.get("table_receipts", []):
            region = table_receipt.get("region")
            if type(region) is not dict:
                raise _error("Family-22 source-role coverage region is absent")
            table_key = (
                region.get("page_json_version_id"),
                region.get("section_id"),
                region.get("table_id"),
            )
            if not all(type(item) is str and item for item in table_key):
                raise _error("Family-22 source-role coverage region is invalid")
            for duplicate in table_receipt.get(
                "hierarchical_duplicate_receipts", []
            ):
                receipt_kinds[(*table_key, duplicate["carrier_row_ordinal"])].add(
                    "HIERARCHICAL_DUPLICATE_CARRIER"
                )
                for row_ordinal in duplicate["detail_row_ordinals"]:
                    receipt_kinds[(*table_key, row_ordinal)].add(
                        "HIERARCHICAL_DUPLICATE_DETAIL"
                    )

        adapter_receipt = cluster.get("other_assets_query_adapter_receipt")
        provision_by_locator = {}
        continuation_by_locator = {}
        if type(adapter_receipt) is dict:
            for receipt in adapter_receipt.get("provision_control_receipts", []):
                locator = receipt["locator"]
                key = (
                    locator["page_json_version_id"],
                    locator["section_id"],
                    locator["table_id"],
                )
                if key in provision_by_locator:
                    raise _error("Family-22 provision coverage locator is duplicate")
                provision_by_locator[key] = receipt
                adapter_table_axis.append(
                    {
                        "adapter_kind": "PROVISION_CONTROL_SOURCE_ONLY",
                        "document_ordinal": document_ordinal,
                        "locator": canonical_clone_v1(locator),
                        "receipt_id": receipt["receipt_id"],
                    }
                )
            for receipt in adapter_receipt.get("continuation_receipts", []):
                locator = receipt["receiver_locator"]
                key = (
                    locator["page_json_version_id"],
                    locator["section_id"],
                    locator["table_id"],
                )
                if key in continuation_by_locator:
                    raise _error("Family-22 continuation coverage locator is duplicate")
                continuation_by_locator[key] = receipt
                adapter_table_axis.append(
                    {
                        "adapter_kind": "ONE_SIDED_CONTINUATION",
                        "document_ordinal": document_ordinal,
                        "locator": canonical_clone_v1(locator),
                        "receipt_id": receipt["receipt_id"],
                    }
                )

        inventory = cluster.get("declared_money_table_inventory")
        if type(inventory) is not list:
            raise _error("Family-22 source-role coverage inventory is absent")
        selected_locator_axis = {
            (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
            for region in candidate["component_regions"]
        }
        inventory_selected_locator_axis = {
            (item["page_json_version_id"], item["section_id"], item["table_id"])
            for item in inventory
            if item.get("disposition") in selected_dispositions
        }
        if selected_locator_axis != inventory_selected_locator_axis:
            raise _error("Family-22 selected table coverage axis drifted")

        for item in inventory:
            query_disposition = item.get("disposition")
            if query_disposition not in allowed_query_dispositions:
                raise _error("Family-22 source-role coverage disposition is unknown")
            table_locator = (
                item["page_json_version_id"],
                item["section_id"],
                item["table_id"],
            )
            if (
                query_disposition == "EXCLUDED_EXACT_FAMILY22_PROVISION_CONTROL"
                and table_locator not in provision_by_locator
            ):
                violations.append(
                    {
                        "reason": "EXCLUDED_PROVISION_TABLE_LACKS_RECEIPT",
                        "table_locator": list(table_locator),
                    }
                )
            if (
                query_disposition
                == "SELECTED_EXACT_FAMILY22_ONE_SIDED_CONTINUATION"
                and table_locator not in continuation_by_locator
            ):
                violations.append(
                    {
                        "reason": "SELECTED_CONTINUATION_TABLE_LACKS_RECEIPT",
                        "table_locator": list(table_locator),
                    }
                )
            classification = item.get("classification")
            if type(classification) is not dict:
                raise _error("Family-22 source-role coverage classification is absent")
            role_hits = classification.get("role_hits")
            money_ordinals = classification.get("money_column_ordinals")
            page = pages.get(item["page_json_version_id"])
            if (
                type(role_hits) is not list
                or type(money_ordinals) is not list
                or type(page) is not dict
            ):
                raise _error("Family-22 source-role coverage source axis is absent")
            table = _coverage_source_table_v1(
                page, section_id=item["section_id"], table_id=item["table_id"]
            )
            rows = table.get("rows")
            columns = table.get("columns")
            if type(rows) is not list or type(columns) is not list:
                raise _error("Family-22 source-role coverage row axis is absent")
            for hit in role_hits:
                row_ordinal = hit.get("row_ordinal")
                if (
                    type(row_ordinal) is not int
                    or row_ordinal <= 0
                    or row_ordinal > len(rows)
                ):
                    raise _error("Family-22 source-role coverage row ordinal is invalid")
                row = rows[row_ordinal - 1]
                values = row.get("values_exact") if type(row) is dict else None
                if type(values) is not list or len(values) != len(columns):
                    raise _error("Family-22 source-role coverage source cells are invalid")
                source_cells = []
                for ordinal in money_ordinals:
                    if type(ordinal) is not int or ordinal <= 0 or ordinal > len(values):
                        raise _error(
                            "Family-22 source-role coverage MONEY ordinal is invalid"
                        )
                    source_text = values[ordinal - 1]
                    if source_text is not None and type(source_text) is not str:
                        raise _error(
                            "Family-22 source-role coverage source text is invalid"
                        )
                    source_cells.append(
                        {
                            "column_ordinal": ordinal,
                            "observation_state": (
                                "BLANK_SOURCE_CELL"
                                if source_text is None
                                else "OBSERVED_SOURCE_CELL"
                            ),
                            "source_text": source_text,
                        }
                    )
                row_key = (*table_locator, row_ordinal)
                role = hit.get("role")
                evidence = sorted(receipt_kinds.get(row_key, set()))
                mapped_roles = sorted(mapping_roles.get(row_key, set()))
                source_visible = any(
                    cell["source_text"] is not None for cell in source_cells
                )
                if query_disposition == "OUTSIDE_SELECTED_OWNER_FENCE":
                    coverage_disposition = "QUERY_OWNER_FENCE_EXCLUDED"
                elif query_disposition == "EXCLUDED_TYPED_CONTROL":
                    coverage_disposition = "QUERY_TYPED_CONTROL_EXCLUDED"
                elif query_disposition == "EXCLUDED_EXACT_FAMILY22_PROVISION_CONTROL":
                    coverage_disposition = (
                        "AUTHENTICATED_PROVISION_CONTROL_SOURCE_ONLY"
                    )
                elif role in mapping_roles.get(row_key, set()):
                    coverage_disposition = "DIRECT_SCHEMA_MAPPING_SOURCE"
                elif role in validation_only_roles:
                    coverage_disposition = "VALIDATION_ONLY_SOURCE_BRIDGE"
                elif any("optional_conditional_omissions" in kind for kind in evidence):
                    coverage_disposition = "TYPED_ALL_BLANK_OPTIONAL_OMISSION"
                elif any("source_only" in kind.lower() for kind in evidence):
                    coverage_disposition = "SOURCE_ONLY_UNMAPPED_RECEIPT"
                elif any("equation" in kind.lower() for kind in evidence):
                    coverage_disposition = "EXACT_EQUATION_SOURCE_OR_RESULT"
                elif any("HIERARCHICAL_DUPLICATE" in kind for kind in evidence):
                    coverage_disposition = "HIERARCHICAL_DUPLICATE_PROOF_ONLY"
                elif evidence:
                    coverage_disposition = "OTHER_TYPED_CORROBORATION_RECEIPT"
                elif not source_visible and hit.get("row_kind") == "GROUP":
                    coverage_disposition = (
                        "ALL_BLANK_STRUCTURAL_GROUP_NON_OBSERVATION"
                    )
                else:
                    coverage_disposition = "UNACCOUNTED_SCHEMA_ROLE_HIT"
                    violations.append(
                        {
                            "reason": coverage_disposition,
                            "role": role,
                            "row_ordinal": row_ordinal,
                            "source_visible": source_visible,
                            "table_locator": list(table_locator),
                        }
                    )
                disposition_counts[coverage_disposition] += 1
                row_axis.append(
                    {
                        "coverage_disposition": coverage_disposition,
                        "document_ordinal": document_ordinal,
                        "hierarchy_path_exact": canonical_clone_v1(
                            row.get("hierarchy_path_exact")
                        ),
                        "label_exact": row.get("label_exact"),
                        "locator": {
                            "page_json_version_id": item["page_json_version_id"],
                            "physical_page": item["physical_page"],
                            "section_id": item["section_id"],
                            "table_id": item["table_id"],
                        },
                        "mapped_roles": mapped_roles,
                        "query_disposition": query_disposition,
                        "receipt_kinds": evidence,
                        "role": role,
                        "row_kind": hit.get("row_kind"),
                        "row_ordinal": row_ordinal,
                        "source_cells": source_cells,
                        "source_visible": source_visible,
                    }
                )

    if violations:
        raise _error(
            f"Family-22 source-role coverage has {len(violations)} violation(s)"
        )
    material = {
        "adapter_table_axis": adapter_table_axis,
        "claim_boundary": (
            "EVERY_CONFIGURED_ROLE_HIT_IN_EVERY_DECLARED_MONEY_TABLE_IS_"
            "MAPPED_PROOF_ONLY_TYPED_NONOBSERVATION_OR_QUERY_SCOPE_EXCLUDED_"
            "WITHOUT_BLANK_TO_ZERO_INFERENCE"
        ),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "format_version": "FAMILY22_SOURCE_ROLE_COVERAGE_RECEIPT_V1",
        "row_axis": row_axis,
        "row_axis_sha256": canonical_json_sha256_v1(row_axis),
        "status": "PASS",
        "violation_count": 0,
    }
    return {
        **material,
        "receipt_id": "f22srcrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def build_experimental_audit_v1(
    *,
    sweep: dict[str, Any],
    sweep_output: Path,
    indexed_query_evidence: dict[str, Any],
    historical_receipt: dict[str, Any],
    observation_contract: dict[str, Any],
    pdf_residuals: list[dict[str, Any]],
    source_role_coverage_contract: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    axes = _semantic_axes(sweep["trials"])
    continuation_recoveries = []
    provision_controls = []
    for cluster in indexed_query_evidence.get("accepted_clusters", []):
        receipt = cluster.get("other_assets_query_adapter_receipt")
        if type(receipt) is not dict:
            continue
        identity = {
            "document_ordinal": cluster["document_ordinal"],
            "source_logical_name": cluster["source_logical_name"],
            "source_sha256": cluster["source_sha256"],
        }
        continuation_recoveries.extend(
            {**identity, "receipt": canonical_clone_v1(item)}
            for item in receipt["continuation_receipts"]
        )
        provision_controls.extend(
            {**identity, "receipt": canonical_clone_v1(item)}
            for item in receipt["provision_control_receipts"]
        )
    axes.update(
        {
            "continuation_recoveries": continuation_recoveries,
            "historical_comparator": [],
            "pdf_residuals": canonical_clone_v1(pdf_residuals),
            "provision_controls": provision_controls,
            "source_role_coverage": canonical_clone_v1(
                source_role_coverage_contract["row_axis"]
            ),
        }
    )
    axis_counts = {key: len(value) for key, value in axes.items()}
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": {
            key: canonical_json_sha256_v1(value) for key, value in axes.items()
        },
        "claim_boundary": (
            "AUTHENTICATED_CURRENT_SELECTED_JSON_AND_PDF_VISIBLE_FAMILY22_"
            "SCHEMA_MAPPING_PROPOSAL_ONLY_NO_PROVIDER_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_receipt": canonical_clone_v1(historical_receipt),
        "indexed_query_receipt": canonical_clone_v1(
            indexed_query_evidence["query_receipt"]
        ),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "source_role_coverage_contract": canonical_clone_v1(
            source_role_coverage_contract
        ),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_metrics": canonical_clone_v1(sweep["metrics"]),
        "sweep_output": str(sweep_output),
    }
    return {
        **material,
        "audit_id": "goaav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("Family-22 experimental audit is not one object")
    material = {
        key: canonical_clone_v1(item) for key, item in value.items() if key != "audit_id"
    }
    axes = value.get("axes")
    metrics = value.get("sweep_metrics")
    receipt = value.get("historical_comparator_receipt")
    contract = value.get("source_observation_contract")
    role_coverage = value.get("source_role_coverage_contract")
    if (
        value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or type(axes) is not dict
        or set(axes)
        != {
            "clusters",
            "continuation_recoveries",
            "equations",
            "historical_comparator",
            "mappings",
            "pdf_residuals",
            "provision_controls",
            "source_role_coverage",
        }
        or value.get("axis_counts") != {key: len(axis) for key, axis in axes.items()}
        or value.get("axis_sha256")
        != {key: canonical_json_sha256_v1(axis) for key, axis in axes.items()}
        or axes["historical_comparator"] != []
        or type(metrics) is not dict
        or metrics.get("ready_count") != len(axes["clusters"])
        or metrics.get("mapping_count") != len(axes["mappings"])
        or metrics.get("not_observed_count") != len(axes["pdf_residuals"])
        or metrics.get("unresolved_count") != 0
        or type(receipt) is not dict
        or receipt.get("policy") != DISJOINT_EXPANSION
        or receipt.get("disposition") != NOT_APPLICABLE_DISJOINT_CORPUS
        or receipt.get("corpus_relation", {}).get("overlap_count") != 0
        or receipt.get("comparison_axis") != []
        or type(contract) is not dict
        or contract.get("status") != "PASS"
        or contract.get("violation_count") != 0
        or type(role_coverage) is not dict
        or role_coverage.get("status") != "PASS"
        or role_coverage.get("violation_count") != 0
        or role_coverage.get("row_axis_sha256")
        != canonical_json_sha256_v1(axes["source_role_coverage"])
        or not same_typed_json_v1(
            role_coverage.get("row_axis"), axes["source_role_coverage"]
        )
        or any(
            item["mapping"]["report_norm_id"] in F26_REPORT_NORM_IDS
            for item in axes["mappings"]
        )
        or value.get("audit_id")
        != "goaav1:audit:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family-22 experimental audit semantic gate drifted")
    return canonical_clone_v1(value)


def _build_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: list[str],
    compiled_specs: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    source_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
    )
    pages = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=selected_page_json_version_ids,
        selected_page_axis=source_indexed["selected_page_axis"],
    )
    indexed, adapter_receipts = adapt_gemini_json_other_assets_indexed_query_evidence_v1(
        source_indexed,
        page_json_by_document=pages,
        compiled_specs=compiled_specs,
    )
    replayed_indexed, replayed_adapter_receipts = (
        adapt_gemini_json_other_assets_indexed_query_evidence_v1(
            source_indexed,
            page_json_by_document=pages,
            compiled_specs=compiled_specs,
        )
    )
    if not same_typed_json_v1(indexed, replayed_indexed) or not same_typed_json_v1(
        adapter_receipts, replayed_adapter_receipts
    ):
        raise _error("Family-22 indexed query adapter is not deterministic")
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        query_receipt = (
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
        )
        candidate = evaluate_gemini_json_other_assets_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[cluster["document_ordinal"]],
            compiled_specs=compiled_specs,
            query_receipt=query_receipt,
        )
        candidates[cluster["document_ordinal"]] = (
            validate_gemini_json_other_assets_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=pages[cluster["document_ordinal"]],
                compiled_specs=compiled_specs,
                query_receipt=query_receipt,
            )
        )
    trials = generic._trials(indexed=indexed, candidates_by_ordinal=candidates)
    source_role_coverage = build_source_role_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
    )
    return indexed, trials, source_role_coverage


def replay_other_assets_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query and replay every Family-22 current-corpus candidate."""

    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    expected = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if not same_typed_json_v1(expected, compiled_specs):
        raise _error("Family-22 source replay declarative specs drifted")
    indexed, trials, _source_role_coverage = _build_trials_from_source_v1(
        source_page_database=source_page_database,
        selected_page_json_version_ids=list(selected_page_json_version_ids),
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-22 source replay rebuilt different indexed query evidence")
    return trials


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
    indexed, trials, source_role_coverage = _build_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
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
        indexed_query_evidence=indexed,
        historical_receipt=historical_receipt,
        observation_contract=observation_contract,
        pdf_residuals=residuals,
        source_role_coverage_contract=source_role_coverage,
        spec_refs=spec_refs,
    )
    validate_experimental_audit_content_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    runner_path = ROOT / "scripts/experiments/run_gemini_json_other_assets_accounting_family_v1.py"
    implementation_paths = (
        runner_path,
        SHARED_EVALUATOR_PATH,
        ROOT / "src/bctc_ai/evaluation/gemini_json_other_assets_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
    )
    runner_ref = generic._file_ref(runner_path, root=ROOT)
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
        source_replay_adapter=replay_other_assets_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("Stored Family-22 sweep differs from authenticated evaluation")
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
        raise _error("Family-22 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_implementation_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "pdf_residual_audit": generic._file_ref(args.pdf_residual_audit_spec, root=ROOT),
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
