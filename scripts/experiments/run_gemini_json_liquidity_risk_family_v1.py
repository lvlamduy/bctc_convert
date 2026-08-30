#!/usr/bin/env python3
"""Run Family50 liquidity risk over the authenticated 140-document corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    READY,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
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
    query_selected_equity_matrix_family_regions_v1,
    validate_selected_equity_matrix_family_candidate_replays_v1,
)
from scripts.experiments.run_gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    _authenticated_sqlite_snapshot,
    _content_ref,
    _file_ref,
    _json,
    _load_selected_pages_by_document,
    _selected_page_axis,
    _trials,
    _write_once,
)


class RunGeminiJsonLiquidityRiskFamilyV1Error(RuntimeError):
    """The Family50 source, graph, comparator, or persistence boundary drifted."""


def _error(message: str) -> RunGeminiJsonLiquidityRiskFamilyV1Error:
    return RunGeminiJsonLiquidityRiskFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_LIQUIDITY_RISK_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 4638,
    "not_observed_count": 2,
    "ready_count": 138,
    "unresolved_count": 0,
}
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "a5459d53c210a1dd263d3cbf102648d225d63c3e87bd4233ff7fb3a54279293f"
    ),
    "accepted_cluster_count": 138,
    "accepted_fragment_count": 172,
    "candidate_disposition_axis_sha256": (
        "047d850762a6dcb0a9a0633b3123fb76b5565f1bf32c068158ec2c080ff7b0e3"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {
        "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY": 2,
        "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY": 138,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    },
    "query_policy_sha256": "e5044739f6486329df5a3d30c92f978f6076a350af63024a50f9e5f182aa7324",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_AUDIT_METRICS = {
    "equation_count": 1364,
    "historical_comparator_mismatch_count": 0,
    "historical_equation_match_count": 82,
    "historical_mapping_match_count": 264,
    "historical_mapping_source_superseded_count": 1,
    "historical_source_only_match_count": 12,
    "historical_source_only_superseded_count": 7,
    "mapping_count": 4638,
    "mapping_value_count": 4074,
    "nonclosing_document_count": 2,
    "nonclosing_frontier_count": 6,
    "period_assignment_count": 172,
    "row_alignment_no_unique_count": 2,
    "row_alignment_raw_exact_count": 151,
    "row_alignment_receipt_count": 172,
    "row_alignment_unique_projection_count": 19,
    "source_only_column_count": 0,
    "table_receipt_count": 172,
    "unit_receipt_count": 138,
    "unresolved_document_count": 2,
}
PINNED_AXIS_COUNTS = {
    "clusters": 138,
    "equations": 1364,
    "historical_documents": 16,
    "historical_equations": 82,
    "historical_mappings": 265,
    "historical_source_only": 19,
    "mappings": 4638,
    "nonclosing_frontiers": 6,
    "period_assignments": 172,
    "row_alignment_receipts": 172,
    "source_only_columns": 0,
    "table_receipts": 172,
    "unit_receipts": 138,
    "unresolved_documents": 2,
}
PINNED_AXIS_SHA256 = {
    "clusters": "a5459d53c210a1dd263d3cbf102648d225d63c3e87bd4233ff7fb3a54279293f",
    "equations": "0d898effebcdbcf7bf0a3e409adb50f59ddc17eaf3819ce7e25420ee70ad8dac",
    "historical_documents": "c519d9ed3b6ed7d840c9b19c90a594b0ac9d205c610e9c3298eb9cf7182d626c",
    "historical_equations": "7f1a77dab50e88c28fabdd8be398a4461e749be06c0413890ba0cea511987591",
    "historical_mappings": "1df9a819459844cfb2e468dd0283a7deda1f1d39b07ad2e6e186a7ecce274073",
    "historical_source_only": "8caf8dcaa805dfe5bbbcceaca66dd1ef687d05704a712a244b9a300d62a8820d",
    "mappings": "e2fd2fb5ef4582f56f423c97d62513726df3ca690ff946e396db0b07b79730e4",
    "nonclosing_frontiers": "453edcbca8881552395e8e9bee0bcdb79b370d4f78d0e6a2383876311cd9b06e",
    "period_assignments": "6f624b4fe5fbf627aec40f21766b6017f70cb49fc05ffa12252eca9a298f6b3a",
    "row_alignment_receipts": "ad39f5f5cd7b1f4f6508d9b9ed9fb0abeec0488de88d2871f06d2162a7e87024",
    "source_only_columns": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "table_receipts": "c18663b09f3d5608211e190bc15d1a81eff2d500d9be9d5767d6267133fcb1e0",
    "unit_receipts": "ddabbf0cebe0827dbf64d65757cad2ad14a47530452586018fa46cedfd973596",
    "unresolved_documents": "cc75330f557ad658f73f65faff0677e6fa37bac091af0b77fe3dfd15c6606a9a",
}
PINNED_HISTORICAL_ORACLES = [
    {
        "format_version": "LIQUIDITY_RISK_8BANK_CODEX_VERIFIED_ACCOUNTING_CORE_V1",
        "path": "docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json",
        "sha256": "f2f4ea1e78abab4468e0cfe328c31fcd66e27f0b8a1aa07f59696c9048d42921",
        "size_bytes": 209167,
    },
    {
        "format_version": "ANNUAL_2025_LIQUIDITY_RISK_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/E-0157-annual-2025-liquidity-risk-8bank-"
            "codex-verified-mapping-v1.json"
        ),
        "sha256": "89d8c9f4bbfd11a7440a7ecadda390bc64d3bd140ba625be91951e8c564a2bbf",
        "size_bytes": 429023,
    },
]
_HISTORICAL_EQUATION_RESULT_ROLE = {
    "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_NET_LIQUIDITY_GAP": "NET_LIQUIDITY_GAP",
}


def _historical_oracles() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for reference in PINNED_HISTORICAL_ORACLES:
        path = ROOT / reference["path"]
        value = _json(path)
        if (
            _file_ref(path, root=ROOT)["sha256"] != reference["sha256"]
            or path.stat().st_size != reference["size_bytes"]
            or value.get("format_version") != reference["format_version"]
            or type(value.get("trials")) is not list
            or len(value["trials"]) != 8
        ):
            raise _error("pinned liquidity-risk historical oracle drifted")
        result.append((canonical_clone_v1(reference), value))
    return result


def _candidate_by_source(trials: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("liquidity-risk current source axis is ambiguous")
        result[source_sha256] = trial
    return result


def _current_cell_axis(candidate: Mapping[str, Any]) -> dict[tuple[str, str, str, str], dict]:
    result = {}
    closure = candidate["closure_receipt"]
    for receipt in closure["table_receipts"]:
        period = receipt["period_assignment"]
        for resolved in receipt["resolved_columns"]:
            currency_role = resolved["column_axis"]["role"]
            for row_role, cell in resolved["core_cells_by_role"].items():
                if type(cell.get("coefficient")) is not int:
                    continue
                key = (
                    currency_role,
                    row_role,
                    period["period_role"],
                    period["period_date"],
                )
                if key in result:
                    raise _error("liquidity-risk current source cell axis is duplicate")
                result[key] = canonical_clone_v1(cell)
    return result


def _current_equation_axis(candidate: Mapping[str, Any]) -> dict[tuple[str, str, str, str], dict]:
    period_by_region = {
        (
            item["page_json_version_id"],
            item["section_id"],
            item["table_id"],
        ): item
        for item in candidate["closure_receipt"]["period_assignments"]
    }
    result = {}
    for equation in candidate["closure_receipt"]["equations"]:
        ref = equation["result_cell"].get("cell_ref")
        if type(ref) is not dict or type(ref.get("locator")) is not dict:
            continue
        locator = ref["locator"]
        period = period_by_region[
            (locator["page_json_version_id"], locator["section_id"], locator["table_id"])
        ]
        key = (
            equation["currency_role"],
            equation["result_role"],
            period["period_role"],
            period["period_date"],
        )
        if key in result:
            raise _error("liquidity-risk current equation axis is duplicate")
        result[key] = canonical_clone_v1(equation)
    return result


def _historical_value_axis(values: Any) -> list[dict[str, Any]]:
    if type(values) is not list or not values:
        raise _error("historical liquidity-risk value axis is absent")
    result = []
    for value in values:
        period_axis = value.get("period_axis") if type(value) is dict else None
        coefficient = value.get("normalized_value") if type(value) is dict else None
        date = value.get("source_period_date") if type(value) is dict else None
        if period_axis not in {"CURRENT", "COMPARATIVE"} or type(coefficient) is not int:
            raise _error("historical liquidity-risk value is invalid")
        if type(date) is not str:
            raise _error("historical liquidity-risk period date is absent")
        result.append(
            {
                "coefficient": coefficient,
                "period_date": date,
                "period_role": period_axis + "_PERIOD",
            }
        )
    return sorted(result, key=lambda item: (item["period_role"], item["period_date"]))


def _historical_comparator_axes(
    trials: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    current_by_source = _candidate_by_source(trials)
    document_axis = []
    mapping_axis = []
    equation_axis = []
    source_only_axis = []
    oracle_refs = []
    for oracle_ref, oracle in _historical_oracles():
        oracle_refs.append(oracle_ref)
        for historical in oracle["trials"]:
            source_sha256 = historical.get("source_pdf_sha256")
            current = current_by_source.get(source_sha256)
            if current is None:
                raise _error("historical liquidity-risk source does not join one current trial")
            current_candidate = current["candidates"][0] if current["candidates"] else None
            legacy_present = bool(
                historical.get("verified_mappings") or historical.get("verified_source_only_rows")
            )
            disposition = (
                "EXACT_READY_SOURCE_JOIN"
                if legacy_present and current["status"] == READY
                else "LEGACY_ABSENCE_SUPERSEDED_BY_SELECTED_GEMINI_JSON"
                if not legacy_present and current["status"] == READY
                else "CURRENT_UNRESOLVED"
            )
            document_axis.append(
                {
                    "current_status": current["status"],
                    "disposition": disposition,
                    "historical_document_ordinal": historical["document_ordinal"],
                    "historical_format_version": oracle["format_version"],
                    "historical_status": historical["status"],
                    "source_sha256": source_sha256,
                }
            )
            if current_candidate is None:
                if legacy_present:
                    raise _error("historical mapped liquidity-risk source is unresolved")
                continue
            mapping_by_report_norm_id = {
                item["report_norm_id"]: item for item in current_candidate["mappings"]
            }
            if len(mapping_by_report_norm_id) != len(current_candidate["mappings"]):
                raise _error("current liquidity-risk report norm axis is duplicate")
            current_cells = _current_cell_axis(current_candidate)
            current_equations = _current_equation_axis(current_candidate)
            for item in historical.get("verified_mappings", []):
                binding = item.get("schema_binding") if type(item) is dict else None
                report_norm_id = binding.get("report_norm_id") if type(binding) is dict else None
                expected_values = _historical_value_axis(item.get("values"))
                current_mapping = mapping_by_report_norm_id.get(report_norm_id)
                current_values = [] if current_mapping is None else current_mapping["values"]
                projected_current = sorted(
                    [
                        {
                            "coefficient": value["coefficient"],
                            "period_date": value["period_date"],
                            "period_role": value["period_role"],
                        }
                        for value in current_values
                        if any(
                            value["period_role"] == expected["period_role"]
                            and value["period_date"] == expected["period_date"]
                            for expected in expected_values
                        )
                    ],
                    key=lambda value: (value["period_role"], value["period_date"]),
                )
                current_axis_complete = [
                    (value["period_role"], value["period_date"]) for value in projected_current
                ] == [(value["period_role"], value["period_date"]) for value in expected_values]
                current_equations_exact = current_axis_complete and all(
                    (
                        equation := current_equations.get(
                            (
                                item.get("maturity_axis"),
                                "NET_LIQUIDITY_GAP",
                                value["period_role"],
                                value["period_date"],
                            )
                        )
                    )
                    is not None
                    and equation["status"] == "EXACT"
                    for value in expected_values
                )
                disposition = (
                    "EXACT"
                    if projected_current == expected_values
                    else "CURRENT_SOURCE_EXACT_LEGACY_VALUE_SUPERSEDED"
                    if current_equations_exact
                    else "MISMATCH"
                )
                mapping_axis.append(
                    {
                        "axis_role": item["maturity_axis"],
                        "current_values": projected_current,
                        "disposition": disposition,
                        "historical_values": expected_values,
                        "report_norm_id": report_norm_id,
                        "source_role": item["source_role"],
                        "source_sha256": source_sha256,
                    }
                )
            for item in historical.get("verified_accounting_equations", []):
                result_role = _HISTORICAL_EQUATION_RESULT_ROLE.get(item.get("equation_kind"))
                period_role = item.get("period_axis", "") + "_PERIOD"
                current_currency_role = item.get("maturity_axis")
                key = (
                    current_currency_role,
                    result_role,
                    period_role,
                    item.get("source_period_date"),
                )
                current_equation = current_equations.get(key)
                exact = (
                    current_equation is not None
                    and current_equation["status"] == "EXACT"
                    and current_equation["computed_value"] == item.get("computed_value")
                    and current_equation["result_cell"]["coefficient"] == item.get("visible_value")
                )
                equation_axis.append(
                    {
                        "axis_role": item.get("maturity_axis"),
                        "current_currency_role": current_currency_role,
                        "current_equation": current_equation,
                        "disposition": "EXACT" if exact else "MISMATCH",
                        "equation_kind": item.get("equation_kind"),
                        "historical_computed_value": item.get("computed_value"),
                        "historical_visible_value": item.get("visible_value"),
                        "period_date": item.get("source_period_date"),
                        "period_role": period_role,
                        "source_sha256": source_sha256,
                    }
                )
            nonclosing_roles = {
                item["currency_role"]
                for item in current_candidate["closure_receipt"]["nonclosing_currency_frontiers"]
            }
            for item in historical.get("verified_source_only_rows", []):
                historical_role = item.get("maturity_axis")
                current_currency_role = historical_role
                expected_values = []
                current_values = []
                for value in item.get("values", []):
                    period_role = value.get("period_axis", "") + "_PERIOD"
                    key = (
                        current_currency_role,
                        value.get("source_role"),
                        period_role,
                        value.get("source_period_date"),
                    )
                    expected = {
                        "coefficient": value.get("normalized_value"),
                        "period_date": value.get("source_period_date"),
                        "period_role": period_role,
                        "row_role": value.get("source_role"),
                    }
                    expected_values.append(expected)
                    current_cell = current_cells.get(key)
                    if current_cell is not None:
                        current_values.append(
                            {
                                **{
                                    key: expected[key]
                                    for key in ("period_date", "period_role", "row_role")
                                },
                                "coefficient": current_cell["coefficient"],
                            }
                        )
                expected_values.sort(key=lambda value: (value["period_role"], value["row_role"]))
                current_values.sort(key=lambda value: (value["period_role"], value["row_role"]))
                residual_expected = (
                    item.get("reason") == "SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL"
                )
                residual_bound = not residual_expected or current_currency_role in nonclosing_roles
                current_axis_complete = [
                    (value["period_role"], value["period_date"], value["row_role"])
                    for value in current_values
                ] == [
                    (value["period_role"], value["period_date"], value["row_role"])
                    for value in expected_values
                ]
                current_equations_exact = current_axis_complete and all(
                    (
                        equation := current_equations.get(
                            (
                                current_currency_role,
                                "NET_LIQUIDITY_GAP",
                                value["period_role"],
                                value["period_date"],
                            )
                        )
                    )
                    is not None
                    and equation["status"] == "EXACT"
                    for value in expected_values
                )
                disposition = (
                    "EXACT"
                    if current_values == expected_values and residual_bound
                    else "CURRENT_GEMINI_SOURCE_EXACT_LEGACY_ROTATED_CHALLENGER_SUPERSEDED"
                    if item.get("reason")
                    == "ROTATED_SOURCE_NUMERIC_AXIS_REQUIRES_INDEPENDENT_CHALLENGER"
                    and current_equations_exact
                    else "MISMATCH"
                )
                source_only_axis.append(
                    {
                        "current_currency_role": current_currency_role,
                        "current_values": current_values,
                        "disposition": disposition,
                        "historical_axis_role": historical_role,
                        "historical_reason": item.get("reason"),
                        "historical_values": expected_values,
                        "source_sha256": source_sha256,
                    }
                )
    axes = {
        "historical_documents": document_axis,
        "historical_equations": equation_axis,
        "historical_mappings": mapping_axis,
        "historical_source_only": source_only_axis,
    }
    return axes, oracle_refs


def _audit_axes(
    *, trials: Sequence[Mapping[str, Any]], indexed_query_evidence: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "clusters": canonical_clone_v1(indexed_query_evidence["accepted_clusters"]),
        "equations": [],
        "mappings": [],
        "nonclosing_frontiers": [],
        "period_assignments": [],
        "row_alignment_receipts": [],
        "source_only_columns": [],
        "table_receipts": [],
        "unresolved_documents": [],
        "unit_receipts": [],
    }
    for trial in trials:
        if trial["status"] != READY:
            axes["unresolved_documents"].append(
                {
                    "document_ordinal": trial["document_ordinal"],
                    "reasons": canonical_clone_v1(trial["reasons"]),
                    "source_sha256": trial["source_sha256"],
                    "status": trial["status"],
                }
            )
        for mapping in trial["mappings"]:
            axes["mappings"].append(
                {
                    "document_ordinal": trial["document_ordinal"],
                    "mapping": canonical_clone_v1(mapping),
                    "source_sha256": trial["source_sha256"],
                }
            )
        for candidate in trial["candidates"]:
            closure = candidate["closure_receipt"]
            axes["unit_receipts"].append(
                {
                    "document_ordinal": trial["document_ordinal"],
                    "source_sha256": trial["source_sha256"],
                    "unit_receipt": canonical_clone_v1(closure["unit_receipt"]),
                }
            )
            for assignment in closure["period_assignments"]:
                axes["period_assignments"].append(
                    {
                        "document_ordinal": trial["document_ordinal"],
                        "period_assignment": canonical_clone_v1(assignment),
                        "source_sha256": trial["source_sha256"],
                    }
                )
            for equation in closure["equations"]:
                axes["equations"].append(
                    {
                        "document_ordinal": trial["document_ordinal"],
                        "equation": canonical_clone_v1(equation),
                        "source_sha256": trial["source_sha256"],
                    }
                )
            for frontier in closure["nonclosing_currency_frontiers"]:
                axes["nonclosing_frontiers"].append(
                    {
                        "document_ordinal": trial["document_ordinal"],
                        "frontier": canonical_clone_v1(frontier),
                        "source_sha256": trial["source_sha256"],
                    }
                )
            for receipt in closure["table_receipts"]:
                axes["table_receipts"].append(
                    {
                        "document_ordinal": trial["document_ordinal"],
                        "source_sha256": trial["source_sha256"],
                        "table_receipt": canonical_clone_v1(receipt),
                    }
                )
                alignment = receipt["classification"].get("liquidity_row_alignment_receipt")
                if type(alignment) is dict:
                    axes["row_alignment_receipts"].append(
                        {
                            "document_ordinal": trial["document_ordinal"],
                            "period_assignment": canonical_clone_v1(receipt["period_assignment"]),
                            "region": canonical_clone_v1(receipt["region"]),
                            "row_alignment_receipt": canonical_clone_v1(alignment),
                            "source_sha256": trial["source_sha256"],
                        }
                    )
                for resolved in receipt["resolved_columns"]:
                    if resolved["column_axis"]["kind"] != "SOURCE_ONLY_CURRENCY":
                        continue
                    axes["source_only_columns"].append(
                        {
                            "column_axis": canonical_clone_v1(resolved["column_axis"]),
                            "core_cells_by_role": canonical_clone_v1(
                                resolved["core_cells_by_role"]
                            ),
                            "document_ordinal": trial["document_ordinal"],
                            "period_assignment": canonical_clone_v1(receipt["period_assignment"]),
                            "region": canonical_clone_v1(receipt["region"]),
                            "source_sha256": trial["source_sha256"],
                        }
                    )
    comparator, oracle_refs = _historical_comparator_axes(trials)
    axes.update(comparator)
    return axes, oracle_refs


def _audit_metrics(axes: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, int]:
    return {
        "equation_count": len(axes["equations"]),
        "historical_equation_match_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_equations"]
        ),
        "historical_mapping_match_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_mappings"]
        ),
        "historical_mapping_source_superseded_count": sum(
            item["disposition"] == "CURRENT_SOURCE_EXACT_LEGACY_VALUE_SUPERSEDED"
            for item in axes["historical_mappings"]
        ),
        "historical_source_only_match_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_source_only"]
        ),
        "historical_source_only_superseded_count": sum(
            item["disposition"]
            == "CURRENT_GEMINI_SOURCE_EXACT_LEGACY_ROTATED_CHALLENGER_SUPERSEDED"
            for item in axes["historical_source_only"]
        ),
        "historical_comparator_mismatch_count": sum(
            item["disposition"] == "MISMATCH"
            for name in (
                "historical_equations",
                "historical_mappings",
                "historical_source_only",
            )
            for item in axes[name]
        ),
        "mapping_count": len(axes["mappings"]),
        "mapping_value_count": sum(len(item["mapping"]["values"]) for item in axes["mappings"]),
        "nonclosing_document_count": len(
            {item["document_ordinal"] for item in axes["nonclosing_frontiers"]}
        ),
        "nonclosing_frontier_count": len(axes["nonclosing_frontiers"]),
        "period_assignment_count": len(axes["period_assignments"]),
        "row_alignment_no_unique_count": sum(
            item["row_alignment_receipt"]["status"] == "NO_UNIQUE_EXACT_ALIGNMENT"
            for item in axes["row_alignment_receipts"]
        ),
        "row_alignment_raw_exact_count": sum(
            item["row_alignment_receipt"]["status"] == "RAW_AXIS_EXACT"
            for item in axes["row_alignment_receipts"]
        ),
        "row_alignment_receipt_count": len(axes["row_alignment_receipts"]),
        "row_alignment_unique_projection_count": sum(
            item["row_alignment_receipt"]["status"] == "UNIQUE_BOUNDARY_BLANK_OFFSET_EXACT"
            for item in axes["row_alignment_receipts"]
        ),
        "source_only_column_count": len(axes["source_only_columns"]),
        "table_receipt_count": len(axes["table_receipts"]),
        "unresolved_document_count": len(axes["unresolved_documents"]),
        "unit_receipt_count": len(axes["unit_receipts"]),
    }


def build_liquidity_risk_experimental_audit_v1(
    *, sweep: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    validate_gemini_json_flat_family_sweep_v1(sweep)
    axes, oracle_refs = _audit_axes(
        trials=sweep["trials"], indexed_query_evidence=sweep["indexed_query_evidence"]
    )
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    audit_metrics = _audit_metrics(axes)
    material = {
        "audit_metrics": audit_metrics,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "claim_boundary": compiled_specs["claim_boundary"],
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": sweep["indexed_query_evidence"]["query_evidence_id"],
        "sweep_id": sweep["sweep_id"],
        **axes,
    }
    return {
        "audit_id": "gjflrreav1:audit:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_liquidity_risk_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    axis_names = {
        "clusters",
        "equations",
        "historical_documents",
        "historical_equations",
        "historical_mappings",
        "historical_source_only",
        "mappings",
        "nonclosing_frontiers",
        "period_assignments",
        "row_alignment_receipts",
        "source_only_columns",
        "table_receipts",
        "unresolved_documents",
        "unit_receipts",
    }
    fields = {
        "audit_id",
        "audit_metrics",
        "axis_counts",
        "axis_sha256",
        "claim_boundary",
        "format_version",
        "historical_oracle_refs",
        "query_evidence_id",
        "sweep_id",
        *axis_names,
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or type(value.get("axis_counts")) is not dict
        or type(value.get("axis_sha256")) is not dict
        or set(value["axis_counts"]) != axis_names
        or set(value["axis_sha256"]) != axis_names
        or any(type(value.get(name)) is not list for name in axis_names)
    ):
        raise _error("liquidity-risk experimental audit shape drifted")
    if value["axis_counts"] != {name: len(value[name]) for name in axis_names} or value[
        "axis_sha256"
    ] != {name: canonical_json_sha256_v1(value[name]) for name in axis_names}:
        raise _error("liquidity-risk experimental audit axis seal drifted")
    if value.get("audit_metrics") != _audit_metrics(value):
        raise _error("liquidity-risk experimental audit metrics drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value["audit_id"] != "gjflrreav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("liquidity-risk experimental audit identity drifted")
    return canonical_clone_v1(value)


def validate_liquidity_risk_experimental_audit_replay_v1(
    value: Any,
    *,
    sweep: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    source_database: Path,
    selected_page_json_version_ids: Sequence[str],
) -> dict[str, Any]:
    validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        sweep["specs"]["topology"]["value"],
        sweep["specs"]["evaluation"]["value"],
        sweep["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("liquidity-risk caller and embedded compiled specs differ")
    validate_selected_equity_matrix_family_candidate_replays_v1(
        source_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=sweep["indexed_query_evidence"],
        trials=sweep["trials"],
    )
    expected = build_liquidity_risk_experimental_audit_v1(sweep=sweep, compiled_specs=embedded)
    validate_liquidity_risk_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("liquidity-risk experimental audit does not replay exactly")
    return expected


def build_liquidity_risk_experimental_bundle_v1(
    *,
    corpus_manifest_index_id: str,
    database: Path,
    selected_ids: Sequence[str],
    topology: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if compiled.get("family_id") != "LIQUIDITY_RISK":
        raise _error("Family50 runner received a different family triplet")
    indexed = query_selected_equity_matrix_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    pages = _load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        candidates[ordinal] = evaluate_gemini_json_equity_matrix_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                regions, owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=corpus_manifest_index_id,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    audit = build_liquidity_risk_experimental_audit_v1(sweep=sweep, compiled_specs=compiled)
    validate_liquidity_risk_experimental_audit_replay_v1(
        audit,
        sweep=sweep,
        compiled_specs=compiled,
        source_database=database,
        selected_page_json_version_ids=selected_ids,
    )
    return sweep, audit, compiled


def _assert_release_pins(
    *, sweep: Mapping[str, Any], audit: Mapping[str, Any], selected_ids: Sequence[str]
) -> None:
    actual_frontier = canonical_json_sha256_v1(list(selected_ids))
    if (
        sweep["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID
        or actual_frontier != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256
        or not same_typed_json_v1(sweep["metrics"], PINNED_RELEASE_METRICS)
        or not same_typed_json_v1(
            sweep["indexed_query_evidence"]["query_receipt"], PINNED_QUERY_RECEIPT
        )
        or not same_typed_json_v1(audit["audit_metrics"], PINNED_AUDIT_METRICS)
        or not same_typed_json_v1(audit["axis_counts"], PINNED_AXIS_COUNTS)
        or not same_typed_json_v1(audit["axis_sha256"], PINNED_AXIS_SHA256)
    ):
        raise _error("Family50 frozen corpus release pins drifted")


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    with _authenticated_sqlite_snapshot(
        source_database, reference=index["database_ref"]
    ) as database_guard:
        database = database_guard.path
        sweep, audit, _compiled = build_liquidity_risk_experimental_bundle_v1(
            corpus_manifest_index_id=index["corpus_manifest_index_id"],
            database=database,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
        )
        _assert_release_pins(sweep=sweep, audit=audit, selected_ids=selected_ids)
        _write_once(args.output, sweep)
        audit_output = args.output.with_suffix(".audit.json")
        _write_once(audit_output, audit)
        implementation_paths = (
            ROOT / "scripts/experiments/run_gemini_json_liquidity_risk_family_v1.py",
            ROOT / "src/bctc_ai/evaluation/gemini_json_liquidity_risk_matrix_v1.py",
            ROOT / "src/bctc_ai/evaluation/gemini_json_equity_matrix_accounting_family_v1.py",
            ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
            ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
            ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        )
        stored = ingest_gemini_accounting_family_sweep_v1(
            args.results_database,
            sweep=sweep,
            corpus_index_ref=_file_ref(args.corpus_index),
            implementation_refs=[_file_ref(path, root=ROOT) for path in implementation_paths],
            run_kind=args.run_kind,
            source_page_database=database,
            selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=artifact_root,
        )
        stored_sweep = load_gemini_accounting_family_sweep_v1(
            args.results_database, stored["family_run_id"]
        )
        if not same_typed_json_v1(stored_sweep, sweep):
            raise _error("stored Family50 sweep differs from authenticated evaluation")
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
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
