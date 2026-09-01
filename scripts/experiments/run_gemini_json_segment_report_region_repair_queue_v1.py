#!/usr/bin/env python3
"""Derive and enqueue bounded Family54 region-repair jobs from one stored EXP run."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    READY,
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_queue_v1 import (  # noqa: E402
    FORMAT_VERSION as REPAIR_QUEUE_FORMAT_VERSION,
)
from bctc_ai.evaluation.gemini_json_region_repair_queue_v1 import (  # noqa: E402
    REPAIR_CONTRACT_VERSION,
)
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (  # noqa: E402
    region_repair_targets_v1,
    table_axis_repair_targets_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage import gemini_accounting_family_store_v1 as family_store  # noqa: E402
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    enqueue_gemini_family_region_repair_plans_v1,
    load_gemini_accounting_family_sweep_v1,
    resolved_gemini_family_region_repair_candidate_replacements_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (  # noqa: E402
    effective_page_frontier_stages_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    load_page_json_versions_v1,
    page_json_region_repair_lineages_v1,
    validate_selected_equity_matrix_family_candidate_replays_v1,
)
from scripts.experiments.run_gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    _authenticated_sqlite_snapshot,
)

FAMILY_ID = "CONSOLIDATED_SEGMENT_REPORT"
FORMAT_VERSION = "GEMINI_JSON_SEGMENT_REPORT_REGION_REPAIR_QUEUE_RUNNER_V1"
_TABLE_PERIOD_AXIS_REASONS = frozenset(
    {
        "SEGMENT_COLUMN_PERIOD_AMBIGUOUS",
        "SEGMENT_PERIOD_NOT_RESOLVED",
        "SEGMENT_TABLE_TITLE_PERIOD_AMBIGUOUS",
    }
)
_PERIOD_REASONS = _TABLE_PERIOD_AXIS_REASONS | {"SEGMENT_PERIOD_END_NOT_RESOLVED"}
_MONEY_REASONS = frozenset(
    {
        "SEGMENT_MONEY_CELL_AMBIGUOUS",
        "SEGMENT_MONEY_CELL_INVALID",
    }
)
_REPAIR_POLICY = {
    "context_radius_by_thinking_level": {"high": 3, "low": 1, "medium": 2},
    "initial_thinking_level": "low",
    "max_attempts": 3,
    "thinking_escalation": ["medium", "high"],
}
_ACCEPTANCE_POLICY = {
    "candidate_identity_must_replay": True,
    "forbid_arithmetic_backsolve": True,
    "forbid_new_unresolved_reasons": True,
    "promote_when_targeted_ocr_reason_is_removed": True,
}
_AUTHENTICATED_BASE_SWEEP_FRONTIERS: set[tuple[int, int, str, str, str]] = set()


class RunGeminiJsonSegmentReportRegionRepairQueueV1Error(RuntimeError):
    """The Family54 sweep, source frontier, or bounded repair lineage drifted."""


def _error(message: str) -> RunGeminiJsonSegmentReportRegionRepairQueueV1Error:
    return RunGeminiJsonSegmentReportRegionRepairQueueV1Error(message)


def _assert_disjoint_databases(*, source_database: Path, results_database: Path) -> None:
    if source_database.is_symlink() or not source_database.is_file():
        raise _error("Family54 page database is absent or not a regular non-symlink file")
    if results_database.is_symlink() or not results_database.is_file():
        raise _error("Family54 results database is absent or not a regular non-symlink file")
    if source_database.resolve() == results_database.resolve() or os.path.samefile(
        source_database, results_database
    ):
        raise _error("Family54 repair queue would mutate its authenticated page database")


def _stored_run_binding(results_database: Path, *, family_run_id: str) -> dict[str, Any]:
    if type(family_run_id) is not str or not family_run_id.startswith("gjfafstorev1:run:"):
        raise _error("Family54 family run ID is invalid")
    if results_database.is_symlink() or not results_database.is_file():
        raise _error("Family54 results database is absent or not a regular non-symlink file")
    connection = sqlite3.connect(f"file:{results_database.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        identity = connection.execute(
            "SELECT format_version FROM store_identity WHERE singleton=1"
        ).fetchone()
        row = connection.execute(
            "SELECT family_id,sweep_id,corpus_manifest_index_id,corpus_index_sha256,"
            "topology_spec_sha256,evaluation_spec_sha256,schema_binding_spec_sha256,"
            "sweep_sha256,sweep_bytes,unresolved_count "
            "FROM family_run WHERE family_run_id=?",
            (family_run_id,),
        ).fetchone()
        experimental_count = connection.execute(
            "SELECT count(*) FROM family_run_execution "
            "WHERE family_run_id=? AND run_kind='EXPERIMENTAL'",
            (family_run_id,),
        ).fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise _error("Family54 results database cannot replay its stored run") from exc
    finally:
        connection.close()
    if identity is None or identity["format_version"] != "GEMINI_ACCOUNTING_FAMILY_STORE_V1":
        raise _error("Family54 results database identity drifted")
    if row is None or row["family_id"] != FAMILY_ID or experimental_count < 1:
        raise _error("Family54 repair planning requires one stored EXPERIMENTAL family run")
    payload = bytes(row["sweep_bytes"])
    if sha256(payload).hexdigest() != row["sweep_sha256"] or row["unresolved_count"] <= 0:
        raise _error("Family54 stored unresolved sweep bytes drifted")
    return dict(row)


def _repair_target_key(plan: Mapping[str, Any]) -> tuple[str, int, str, str]:
    source_sha256 = plan.get("source_sha256")
    physical_page = plan.get("physical_page")
    repair_scope = plan.get("repair_scope")
    targets = (
        plan.get("target_table_refs")
        if repair_scope == "TABLE_PERIOD_AXIS"
        else plan.get("target_cell_refs")
    )
    if (
        type(source_sha256) is not str
        or len(source_sha256) != 64
        or type(physical_page) is not int
        or physical_page <= 0
        or repair_scope not in {"ROW_VALUES", "TABLE_PERIOD_AXIS"}
        or type(targets) is not list
        or not targets
    ):
        raise _error("Family54 repair target identity is invalid")
    return source_sha256, physical_page, repair_scope, canonical_json_sha256_v1(targets)


def _terminal_repair_target_keys(
    results_database: Path,
    *,
    family_run_id: str,
) -> set[tuple[str, int, str, str]]:
    """Authenticate terminal prior-stage plans so an effective rerun cannot loop them."""

    if results_database.is_symlink() or not results_database.is_file():
        raise _error("Family54 prior repair results database is absent")
    connection = sqlite3.connect(f"file:{results_database.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        identity = connection.execute(
            "SELECT format_version FROM store_identity WHERE singleton=1"
        ).fetchone()
        run = connection.execute(
            "SELECT family_id FROM family_run WHERE family_run_id=?",
            (family_run_id,),
        ).fetchone()
        experimental_count = connection.execute(
            "SELECT count(*) FROM family_run_execution "
            "WHERE family_run_id=? AND run_kind='EXPERIMENTAL'",
            (family_run_id,),
        ).fetchone()[0]
        rows = connection.execute(
            "SELECT repair_job_id,plan_sha256,plan_bytes,status "
            "FROM family_region_repair_job WHERE family_run_id=? "
            "AND status IN ('RESOLVED','ABSTAINED') ORDER BY repair_job_id",
            (family_run_id,),
        ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise _error("Family54 prior repair terminal axis cannot replay") from exc
    finally:
        connection.close()
    if (
        identity is None
        or identity["format_version"] != "GEMINI_ACCOUNTING_FAMILY_STORE_V1"
        or run is None
        or run["family_id"] != FAMILY_ID
        or experimental_count < 1
    ):
        raise _error("Family54 prior repair run authority drifted")
    keys = set()
    for row in rows:
        payload = bytes(row["plan_bytes"])
        try:
            plan = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("Family54 prior repair plan bytes are invalid") from exc
        if (
            type(plan) is not dict
            or sha256(payload).hexdigest() != row["plan_sha256"]
            or plan.get("repair_job_id") != row["repair_job_id"]
            or plan.get("family_id") != FAMILY_ID
        ):
            raise _error("Family54 prior repair plan identity drifted")
        material = {key: plan[key] for key in plan if key != "repair_job_id"}
        if plan["repair_job_id"] != "gjfrrqv1:job:" + canonical_json_sha256_v1(material):
            raise _error("Family54 prior repair plan ID drifted")
        keys.add(_repair_target_key(plan))
    return keys


def _node_ordinal(identifier: Any, *, prefix: str) -> int:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error("Family54 repair node ID is invalid")
    suffix = identifier.removeprefix(prefix)
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error("Family54 repair node ID is invalid")
    return int(suffix)


def _table_key(region: Mapping[str, Any]) -> tuple[str, str, str]:
    version_id = region.get("page_json_version_id")
    section_id = region.get("section_id")
    table_id = region.get("table_id")
    if (
        type(version_id) is not str
        or not version_id.startswith("gfpstorev1:json:")
        or _node_ordinal(section_id, prefix="s") <= 0
        or _node_ordinal(table_id, prefix="t") <= 0
    ):
        raise _error("Family54 component table locator is invalid")
    return version_id, section_id, table_id


def _target_sort_key(target_id: str) -> tuple[int, int, int]:
    section_id, table_id, row_id = target_id.split(":")
    return (
        _node_ordinal(section_id, prefix="s"),
        _node_ordinal(table_id, prefix="t"),
        _node_ordinal(row_id, prefix="r"),
    )


def _table_ref_sort_key(ref: Mapping[str, str]) -> tuple[int, int]:
    return (
        _node_ordinal(ref["section_id"], prefix="s"),
        _node_ordinal(ref["table_id"], prefix="t"),
    )


def _candidate_region_axis(
    candidate: Mapping[str, Any], *, trial: Mapping[str, Any]
) -> dict[tuple[str, str, str], dict[str, Any]]:
    regions = candidate.get("component_regions")
    if type(regions) is not list or not regions:
        raise _error("Family54 unresolved candidate component region axis is absent")
    result = {}
    for source in regions:
        if type(source) is not dict:
            raise _error("Family54 unresolved candidate component region is invalid")
        region = canonical_clone_v1(source)
        key = _table_key(region)
        if (
            key in result
            or region.get("source_logical_name") != trial["source_logical_name"]
            or region.get("source_sha256") != trial["source_sha256"]
            or region.get("document_ordinal") != trial["document_ordinal"]
            or type(region.get("physical_page")) is not int
            or region["physical_page"] <= 0
        ):
            raise _error("Family54 unresolved candidate component provenance drifted")
        result[key] = region
    return result


def _candidate_table_receipts(
    candidate: Mapping[str, Any],
    *,
    regions: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    receipts = candidate.get("closure_receipt", {}).get("table_receipts")
    if type(receipts) is not list or not receipts:
        raise _error("Family54 unresolved candidate table receipts are absent")
    result = {}
    for source in receipts:
        if type(source) is not dict or type(source.get("region")) is not dict:
            raise _error("Family54 unresolved candidate table receipt is invalid")
        receipt = canonical_clone_v1(source)
        key = _table_key(receipt["region"])
        if key in result or key not in regions or receipt["region"] != regions[key]:
            raise _error("Family54 table receipt does not bind one component region")
        if type(receipt.get("cell_axis")) is not list:
            raise _error("Family54 table receipt cell axis is invalid")
        result[key] = receipt
    return result


def _page_table(
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    *,
    key: tuple[str, str, str],
) -> Mapping[str, Any]:
    version_id, section_id, table_id = key
    page_json = page_json_by_version.get(version_id)
    if type(page_json) is not dict:
        raise _error("Family54 repair target page JSON is absent")
    try:
        return page_json["sections"][_node_ordinal(section_id, prefix="s") - 1]["tables"][
            _node_ordinal(table_id, prefix="t") - 1
        ]
    except (IndexError, KeyError, TypeError) as exc:
        raise _error("Family54 repair target table lies outside its page JSON") from exc


def _period_table_keys(
    candidate: Mapping[str, Any],
    *,
    receipts: Mapping[tuple[str, str, str], Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> set[tuple[str, str, str]]:
    mapped_roles = compiled_specs.get("metric_offset_by_role")
    if type(mapped_roles) is not dict or not mapped_roles:
        raise _error("Family54 mapped metric role axis is invalid")
    reasons = set(candidate["reasons"])
    locally_incomplete = set()
    all_cell_refs = set()
    declared_mapping_cell_refs = set()
    for key, receipt in receipts.items():
        cells = receipt["cell_axis"]
        if any(type(cell) is not dict or type(cell.get("cell_ref")) is not dict for cell in cells):
            raise _error("Family54 period cell lineage is invalid")
        all_cell_refs.update(canonical_json_sha256_v1(cell["cell_ref"]) for cell in cells)
        for cell in cells:
            branch_binding = compiled_specs.get("branch_bindings_by_role", {}).get(
                cell.get("branch")
            )
            if (
                cell.get("metric_role") in mapped_roles
                and type(branch_binding) is dict
                and cell.get("axis_role")
                in branch_binding.get("axis_parent_report_norm_id_by_role", {})
            ):
                declared_mapping_cell_refs.add(canonical_json_sha256_v1(cell["cell_ref"]))
        # Receipt-wide null is valid for a local multi-period table, and null
        # cells are valid when a sealed structural carrier assigned this table.
        # Only mapped cells lacking both authorities form an exact repair origin.
        if receipt.get("period_assignment_evidence") is None and any(
            cell.get("metric_role") in mapped_roles and cell.get("period_year") is None
            for cell in cells
        ):
            locally_incomplete.add(key)
    if reasons & _TABLE_PERIOD_AXIS_REASONS and not locally_incomplete:
        raise _error("Family54 period failure has no exact bounded table frontier")

    missing_period_end = set()
    if "SEGMENT_PERIOD_END_NOT_RESOLVED" in reasons:
        period_receipt = candidate.get("closure_receipt", {}).get("period_receipt")
        assignments = (
            period_receipt.get("period_assignment_axis") if type(period_receipt) is dict else None
        )
        if type(assignments) is not list:
            raise _error("Family54 period-end assignment receipt is absent")
        for assignment in assignments:
            if (
                type(assignment) is not dict
                or type(assignment.get("cell_ref")) is not dict
                or type(assignment.get("region")) is not dict
            ):
                raise _error("Family54 period-end assignment lineage is invalid")
            ref = assignment["cell_ref"]
            key = _table_key(ref)
            receipt = receipts.get(key)
            if (
                receipt is None
                or not same_typed_json_v1(assignment["region"], receipt["region"])
                or canonical_json_sha256_v1(ref) not in all_cell_refs
            ):
                raise _error("Family54 period-end assignment escapes table lineage")
            if (
                canonical_json_sha256_v1(ref) in declared_mapping_cell_refs
                and assignment.get("period_end") is None
            ):
                missing_period_end.add(key)
        if not missing_period_end:
            raise _error("Family54 period-end failure has no exact bounded table frontier")
    result = locally_incomplete | missing_period_end
    if not result:
        raise _error("Family54 period failure has no exact bounded table frontier")
    return result


def _money_cell_frontier(
    candidate: Mapping[str, Any],
    *,
    receipts: Mapping[tuple[str, str, str], Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reasons = set(candidate["reasons"])
    invalid_required = "SEGMENT_MONEY_CELL_INVALID" in reasons
    ambiguous_required = "SEGMENT_MONEY_CELL_AMBIGUOUS" in reasons
    invalid_count = 0
    ambiguous_count = 0
    mapped_roles = compiled_specs.get("metric_offset_by_role")
    if type(mapped_roles) is not dict or not mapped_roles:
        raise _error("Family54 mapped metric role axis is invalid")
    for key, receipt in receipts.items():
        table = _page_table(page_json_by_version, key=key)
        columns = table.get("columns")
        rows = table.get("rows")
        if type(columns) is not list or type(rows) is not list:
            raise _error("Family54 money repair table axis is invalid")
        for cell in receipt["cell_axis"]:
            if type(cell) is not dict or type(cell.get("cell_ref")) is not dict:
                raise _error("Family54 money repair cell lineage is invalid")
            invalid = cell.get("state") == "INVALID_MONEY_SOURCE"
            ambiguous = "coefficient_candidates" in cell
            if cell.get("metric_role") not in mapped_roles or (not invalid and not ambiguous):
                continue
            ref = cell["cell_ref"]
            if (
                set(ref)
                != {
                    "column_id",
                    "page_json_version_id",
                    "physical_page",
                    "row_id",
                    "section_id",
                    "table_id",
                }
                or _table_key(ref) != key
                or ref["physical_page"] != receipt["region"]["physical_page"]
                or cell.get("coefficient") is not None
            ):
                raise _error("Family54 money repair cell reference drifted")
            row_ordinal = _node_ordinal(ref["row_id"], prefix="r")
            column_ordinal = _node_ordinal(ref["column_id"], prefix="c")
            if not 1 <= row_ordinal <= len(rows) or not 1 <= column_ordinal <= len(columns):
                raise _error("Family54 money repair cell lies outside its source table")
            if not same_typed_json_v1(
                rows[row_ordinal - 1]["values_exact"][column_ordinal - 1], cell.get("source_text")
            ):
                raise _error("Family54 money repair cell no longer matches source JSON")
            if invalid:
                invalid_count += 1
            if ambiguous:
                candidates = cell.get("coefficient_candidates")
                if (
                    type(candidates) is not list
                    or len(candidates) < 2
                    or any(type(value) is not int for value in candidates)
                ):
                    raise _error("Family54 ambiguous money cell candidates are invalid")
                ambiguous_count += 1
            result[key[0]].append(canonical_clone_v1(ref))
    if (invalid_required and invalid_count == 0) or (ambiguous_required and ambiguous_count == 0):
        raise _error("Family54 typed money failure has no exact cell frontier")
    for version_id, refs in result.items():
        unique = {canonical_json_sha256_v1(ref): ref for ref in refs}
        result[version_id] = sorted(
            unique.values(),
            key=lambda ref: (
                _node_ordinal(ref["section_id"], prefix="s"),
                _node_ordinal(ref["table_id"], prefix="t"),
                _node_ordinal(ref["row_id"], prefix="r"),
                _node_ordinal(ref["column_id"], prefix="c"),
            ),
        )
    return dict(result)


def _table_row_target_ids(
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    *,
    version_id: str,
    table_refs: Sequence[Mapping[str, str]],
) -> list[str]:
    target_ids = []
    for ref in table_refs:
        table = _page_table(
            page_json_by_version, key=(version_id, ref["section_id"], ref["table_id"])
        )
        rows = table.get("rows")
        if type(rows) is not list or not rows:
            raise _error("Family54 period repair table has no row context")
        target_ids.extend(
            f"{ref['section_id']}:{ref['table_id']}:r{ordinal}"
            for ordinal in range(1, len(rows) + 1)
        )
    return sorted(set(target_ids), key=_target_sort_key)


def _repair_plan(
    *,
    sweep: Mapping[str, Any],
    trial: Mapping[str, Any],
    candidate: Mapping[str, Any],
    regions: Mapping[tuple[str, str, str], Mapping[str, Any]],
    version_id: str,
    repair_scope: str,
    target_ids: list[str],
    target_table_refs: list[dict[str, str]],
    target_cell_refs: list[dict[str, Any]],
    target_axis: Sequence[Mapping[str, Any]],
    repair_frontier_base_page_json_version_ids: list[str],
) -> dict[str, Any]:
    target_keys = {
        (version_id, ref["section_id"], ref["table_id"]) for ref in target_table_refs
    } or {(version_id, *target_id.split(":")[:2]) for target_id in target_ids}
    selected_regions = [regions[key] for key in sorted(target_keys)]
    if not selected_regions:
        raise _error("Family54 repair plan has no component region")
    physical_pages = {region["physical_page"] for region in selected_regions}
    if len(physical_pages) != 1:
        raise _error("Family54 one-page repair plan spans multiple physical pages")
    primary = min(
        selected_regions,
        key=lambda region: (
            _node_ordinal(region["section_id"], prefix="s"),
            _node_ordinal(region["table_id"], prefix="t"),
        ),
    )
    component_refs = sorted(
        [
            {"section_id": region["section_id"], "table_id": region["table_id"]}
            for region in selected_regions
        ],
        key=_table_ref_sort_key,
    )
    targeted_reason_family = (
        _PERIOD_REASONS if repair_scope == "TABLE_PERIOD_AXIS" else _MONEY_REASONS
    )
    targeted_trigger_reasons = sorted(set(candidate["reasons"]) & targeted_reason_family)
    if not targeted_trigger_reasons:
        raise _error("Family54 repair plan has no scope-specific typed trigger reason")
    acceptance_policy = canonical_clone_v1(_ACCEPTANCE_POLICY)
    required_status = (
        UNRESOLVED if set(candidate["reasons"]) - set(targeted_trigger_reasons) else READY
    )
    if len(repair_frontier_base_page_json_version_ids) == 1:
        acceptance_policy["require_candidate_status"] = required_status
    else:
        acceptance_policy["allowed_candidate_statuses"] = [UNRESOLVED, READY]
        acceptance_policy["require_local_period_scope_resolution"] = True
    material = {
        "acceptance_policy": acceptance_policy,
        "base_page_json_version_id": version_id,
        "candidate_component_region_axis_sha256": canonical_json_sha256_v1(
            candidate["component_regions"]
        ),
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_replay_sha256": canonical_json_sha256_v1(candidate),
        "component_table_refs": component_refs,
        "document_ordinal": trial["document_ordinal"],
        "family_id": FAMILY_ID,
        "format_version": REPAIR_QUEUE_FORMAT_VERSION,
        "physical_page": primary["physical_page"],
        "repair_contract_version": REPAIR_CONTRACT_VERSION,
        "repair_policy": canonical_clone_v1(_REPAIR_POLICY),
        "repair_scope": repair_scope,
        "repair_frontier_base_page_json_version_ids": canonical_clone_v1(
            repair_frontier_base_page_json_version_ids
        ),
        "repair_target_axis_sha256": canonical_json_sha256_v1(list(target_axis)),
        "section_id": primary["section_id"],
        "source_logical_name": trial["source_logical_name"],
        "source_sha256": trial["source_sha256"],
        "sweep_id": sweep["sweep_id"],
        "table_id": primary["table_id"],
        "target_cell_refs": canonical_clone_v1(target_cell_refs),
        "target_ids": target_ids,
        "target_table_refs": target_table_refs,
        "targeted_trigger_reasons": targeted_trigger_reasons,
        "trigger_kinds": [
            "TABLE_PERIOD_AXIS_INCOMPLETE"
            if repair_scope == "TABLE_PERIOD_AXIS"
            else "INVALID_MONEY_CELL"
        ],
        "trigger_reasons": canonical_clone_v1(candidate["reasons"]),
    }
    return {
        **material,
        "repair_job_id": "gjfrrqv1:job:" + canonical_json_sha256_v1(material),
    }


def build_segment_report_region_repair_plans_v1(
    *,
    sweep: Mapping[str, Any],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build exact Family54 table-axis or row-value plans from typed U candidates."""

    checked = validate_gemini_json_flat_family_sweep_v1(dict(sweep))
    embedded_compiled = compile_gemini_json_flat_family_specs_v1(
        checked["specs"]["topology"]["value"],
        checked["specs"]["evaluation"]["value"],
        checked["specs"]["schema_binding"]["value"],
    )
    if (
        checked["family_id"] != FAMILY_ID
        or embedded_compiled.get("segment_report_mode") is not True
        or embedded_compiled.get("engine_format_version")
        != "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1"
        or not same_typed_json_v1(dict(compiled_specs), embedded_compiled)
    ):
        raise _error("repair planner requires the exact embedded Family54 compiled triplet")
    plans = []
    for trial in checked["trials"]:
        if trial["status"] != UNRESOLVED:
            continue
        for candidate in trial["candidates"]:
            if candidate["status"] != UNRESOLVED:
                continue
            reasons = set(candidate["reasons"])
            period_reasons = reasons & _PERIOD_REASONS
            all_period_reasons = {
                reason for reason in reasons if reason.startswith("SEGMENT_") and "PERIOD" in reason
            }
            money_reasons = reasons & _MONEY_REASONS
            if not period_reasons and not money_reasons:
                continue
            regions = _candidate_region_axis(candidate, trial=trial)
            receipts = _candidate_table_receipts(candidate, regions=regions)
            period_by_version: dict[str, list[dict[str, str]]] = defaultdict(list)
            if period_reasons:
                for version_id, section_id, table_id in _period_table_keys(
                    candidate,
                    receipts=receipts,
                    compiled_specs=embedded_compiled,
                ):
                    period_by_version[version_id].append(
                        {"section_id": section_id, "table_id": table_id}
                    )
            # Period authority is a prerequisite for interpreting row values.
            # Defer every money job for this candidate, including other pages,
            # until an authenticated rerun has removed its period reasons.
            money_by_version = (
                _money_cell_frontier(
                    candidate,
                    receipts=receipts,
                    page_json_by_version=page_json_by_version,
                    compiled_specs=embedded_compiled,
                )
                if money_reasons and not all_period_reasons
                else {}
            )
            scoped_versions = set(period_by_version) | set(money_by_version)
            if len(scoped_versions) > 1 and not period_by_version:
                raise _error(
                    "Family54 one-candidate repair frontier spans multiple base pages "
                    "without a composable replay authority"
                )
            ordered_versions = sorted(
                scoped_versions,
                key=lambda version_id: (
                    min(
                        region["physical_page"]
                        for key, region in regions.items()
                        if key[0] == version_id
                    ),
                    version_id,
                ),
            )
            for version_id in ordered_versions:
                page_json = page_json_by_version.get(version_id)
                if type(page_json) is not dict:
                    raise _error("Family54 repair page JSON frontier is incomplete")
                # One queue row is unique by candidate and base page.  Header/period
                # evidence is a prerequisite axis, so repair it first and let the
                # authenticated rerun emit a later row-only job if the cell still fails.
                if period_by_version.get(version_id):
                    table_refs = sorted(
                        {
                            (ref["section_id"], ref["table_id"])
                            for ref in period_by_version[version_id]
                        },
                        key=lambda item: (
                            _node_ordinal(item[0], prefix="s"),
                            _node_ordinal(item[1], prefix="t"),
                        ),
                    )
                    checked_refs = [
                        {"section_id": section_id, "table_id": table_id}
                        for section_id, table_id in table_refs
                    ]
                    target_axis = table_axis_repair_targets_v1(page_json, table_refs=checked_refs)
                    plans.append(
                        _repair_plan(
                            sweep=checked,
                            trial=trial,
                            candidate=candidate,
                            regions=regions,
                            version_id=version_id,
                            repair_scope="TABLE_PERIOD_AXIS",
                            target_ids=_table_row_target_ids(
                                page_json_by_version,
                                version_id=version_id,
                                table_refs=checked_refs,
                            ),
                            target_table_refs=checked_refs,
                            target_cell_refs=[],
                            target_axis=target_axis,
                            repair_frontier_base_page_json_version_ids=ordered_versions,
                        )
                    )
                    continue
                cell_refs = money_by_version[version_id]
                target_ids = sorted(
                    {f"{ref['section_id']}:{ref['table_id']}:{ref['row_id']}" for ref in cell_refs},
                    key=_target_sort_key,
                )
                target_axis = region_repair_targets_v1(
                    page_json,
                    target_ids=target_ids,
                    context_radius=1,
                )
                plans.append(
                    _repair_plan(
                        sweep=checked,
                        trial=trial,
                        candidate=candidate,
                        regions=regions,
                        version_id=version_id,
                        repair_scope="ROW_VALUES",
                        target_ids=target_ids,
                        target_table_refs=[],
                        target_cell_refs=cell_refs,
                        target_axis=target_axis,
                        repair_frontier_base_page_json_version_ids=ordered_versions,
                    )
                )
    ordered = sorted(
        plans,
        key=lambda plan: (
            plan["document_ordinal"],
            plan["physical_page"],
            plan["repair_scope"],
            plan["repair_job_id"],
        ),
    )
    identities = [(plan["candidate_id"], plan["base_page_json_version_id"]) for plan in ordered]
    if len(identities) != len(set(identities)):
        raise _error("Family54 repair planner emitted duplicate candidate/page jobs")
    return ordered


def enqueue_segment_report_region_repair_plans_v1(
    results_database: Path,
    *,
    family_run_id: str,
    sweep: Mapping[str, Any],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    prior_terminal_repair_target_keys: set[tuple[str, int, str, str]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    stored_sweep = load_gemini_accounting_family_sweep_v1(results_database, family_run_id)
    if not same_typed_json_v1(stored_sweep, dict(sweep)):
        raise _error("Family54 repair planning sweep differs from its stored family run")
    plans = build_segment_report_region_repair_plans_v1(
        sweep=stored_sweep,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
    )
    suppressed = prior_terminal_repair_target_keys or set()
    plans = [plan for plan in plans if _repair_target_key(plan) not in suppressed]
    if not plans:
        return [], []
    identifiers = enqueue_gemini_family_region_repair_plans_v1(
        results_database,
        family_run_id=family_run_id,
        plans=plans,
        required_run_kind="EXPERIMENTAL",
    )
    if identifiers != [plan["repair_job_id"] for plan in plans]:
        raise _error("Family54 enqueued repair job axis drifted")
    return plans, identifiers


def _target_period_scope_is_resolved_v1(
    *,
    plan: Mapping[str, Any],
    candidate: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> bool:
    mapped_roles = compiled_specs.get("metric_offset_by_role")
    branch_bindings = compiled_specs.get("branch_bindings_by_role")
    receipts = candidate.get("closure_receipt", {}).get("table_receipts")
    targets = plan.get("target_table_refs")
    if (
        type(mapped_roles) is not dict
        or not mapped_roles
        or type(branch_bindings) is not dict
        or type(receipts) is not list
        or type(targets) is not list
        or not targets
    ):
        return False
    target_keys = {(ref.get("section_id"), ref.get("table_id")) for ref in targets}
    matched = []
    for receipt in receipts:
        region = receipt.get("region") if type(receipt) is dict else None
        if (
            type(region) is dict
            and region.get("physical_page") == plan.get("physical_page")
            and (region.get("section_id"), region.get("table_id")) in target_keys
        ):
            matched.append(receipt)
    if len(matched) != len(target_keys):
        return False
    assignment_axis = (
        candidate.get("closure_receipt", {}).get("period_receipt", {}).get("period_assignment_axis")
    )
    if type(assignment_axis) is not list:
        return False
    assignments_by_ref = {
        canonical_json_sha256_v1(item["cell_ref"]): item
        for item in assignment_axis
        if type(item) is dict and type(item.get("cell_ref")) is dict
    }
    require_end = "SEGMENT_PERIOD_END_NOT_RESOLVED" in set(plan.get("trigger_reasons", []))
    for receipt in matched:
        cells = receipt.get("cell_axis")
        if type(cells) is not list:
            return False
        for cell in cells:
            if type(cell) is not dict or type(cell.get("cell_ref")) is not dict:
                return False
            branch_binding = branch_bindings.get(cell.get("branch"))
            declared = (
                cell.get("metric_role") in mapped_roles
                and type(branch_binding) is dict
                and cell.get("axis_role")
                in branch_binding.get("axis_parent_report_norm_id_by_role", {})
            )
            if not declared or cell.get("coefficient") is None:
                continue
            if cell.get("period_year") is None:
                return False
            assignment = assignments_by_ref.get(canonical_json_sha256_v1(cell["cell_ref"]))
            if assignment is None or (require_end and assignment.get("period_end") is None):
                return False
    return True


def segment_targeted_repair_is_accepted_v1(
    plan: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any] | None = None,
) -> bool:
    """Accept only an authenticated Family54 scope whose typed reasons disappeared."""

    scope = plan.get("repair_scope")
    trigger_kinds = plan.get("trigger_kinds")
    if scope == "ROW_VALUES" and trigger_kinds == ["INVALID_MONEY_CELL"]:
        applicable = _MONEY_REASONS
    elif scope == "TABLE_PERIOD_AXIS" and trigger_kinds == ["TABLE_PERIOD_AXIS_INCOMPLETE"]:
        applicable = _PERIOD_REASONS
    else:
        return False
    before_axis = plan.get("trigger_reasons")
    after_axis = candidate.get("reasons")
    policy = plan.get("acceptance_policy")
    if (
        type(before_axis) is not list
        or any(type(reason) is not str for reason in before_axis)
        or type(after_axis) is not list
        or any(type(reason) is not str for reason in after_axis)
        or type(policy) is not dict
        or policy.get("candidate_identity_must_replay") is not True
        or policy.get("forbid_arithmetic_backsolve") is not True
        or policy.get("forbid_new_unresolved_reasons") is not True
        or policy.get("promote_when_targeted_ocr_reason_is_removed") is not True
    ):
        return False
    before = set(before_axis)
    after = set(after_axis)
    targeted = before & applicable
    allowed_statuses = policy.get("allowed_candidate_statuses")
    partial_period = policy.get("require_local_period_scope_resolution") is True
    if (
        not targeted
        or plan.get("targeted_trigger_reasons") != sorted(targeted)
        or not after <= (before if partial_period else before - targeted)
        or (not partial_period and after & applicable)
    ):
        return False
    if partial_period:
        if (
            scope != "TABLE_PERIOD_AXIS"
            or type(compiled_specs) is not dict
            or allowed_statuses != [UNRESOLVED, READY]
            or candidate.get("status") not in allowed_statuses
            or not _target_period_scope_is_resolved_v1(
                plan=plan,
                candidate=candidate,
                compiled_specs=compiled_specs,
            )
        ):
            return False
    elif (
        allowed_statuses is not None
        or "require_local_period_scope_resolution" in policy
        or candidate.get("status") != policy.get("require_candidate_status")
        or after & applicable
    ):
        return False
    return not (
        candidate["status"] == READY and after or candidate["status"] == UNRESOLVED and not after
    )


def _validate_stored_segment_repair_plan_v1(
    *,
    sweep: Mapping[str, Any],
    plan: Mapping[str, Any],
    trial: Mapping[str, Any],
    candidate: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
) -> None:
    regions = _candidate_region_axis(candidate, trial=trial)
    receipts = _candidate_table_receipts(candidate, regions=regions)
    base_id = plan.get("base_page_json_version_id")
    reasons = set(candidate["reasons"])
    scope = plan.get("repair_scope")
    if scope == "ROW_VALUES":
        if reasons & _PERIOD_REASONS:
            raise _error("Family54 money repair was planned before period authority")
        applicable = _MONEY_REASONS
        expected_trigger_kinds = ["INVALID_MONEY_CELL"]
        money_frontier = _money_cell_frontier(
            candidate,
            receipts=receipts,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
        expected_cells = money_frontier.get(base_id, [])
        expected_frontier_ids = sorted(
            money_frontier,
            key=lambda version_id: (
                min(
                    region["physical_page"]
                    for key, region in regions.items()
                    if key[0] == version_id
                ),
                version_id,
            ),
        )
        if not expected_cells:
            raise _error("Family54 stored money repair has no exact page cell frontier")
        expected_table_refs = sorted(
            {(ref["section_id"], ref["table_id"]) for ref in expected_cells},
            key=lambda item: (
                _node_ordinal(item[0], prefix="s"),
                _node_ordinal(item[1], prefix="t"),
            ),
        )
        checked_refs = [
            {"section_id": section_id, "table_id": table_id}
            for section_id, table_id in expected_table_refs
        ]
        expected_target_ids = sorted(
            {f"{ref['section_id']}:{ref['table_id']}:{ref['row_id']}" for ref in expected_cells},
            key=_target_sort_key,
        )
        base_page = page_json_by_version.get(base_id)
        if type(base_page) is not dict:
            raise _error("Family54 stored repair base page JSON is absent")
        target_axis = region_repair_targets_v1(
            base_page,
            target_ids=expected_target_ids,
            context_radius=1,
        )
        if (
            plan.get("target_cell_refs") != expected_cells
            or plan.get("target_ids") != expected_target_ids
            or plan.get("target_table_refs") != []
        ):
            raise _error("Family54 stored money repair target frontier drifted")
    elif scope == "TABLE_PERIOD_AXIS":
        applicable = _PERIOD_REASONS
        expected_trigger_kinds = ["TABLE_PERIOD_AXIS_INCOMPLETE"]
        all_expected_table_keys = _period_table_keys(
            candidate,
            receipts=receipts,
            compiled_specs=compiled_specs,
        )
        expected_table_keys = sorted(
            (key for key in all_expected_table_keys if key[0] == base_id),
            key=lambda key: (
                _node_ordinal(key[1], prefix="s"),
                _node_ordinal(key[2], prefix="t"),
            ),
        )
        expected_frontier_ids = sorted(
            {key[0] for key in all_expected_table_keys},
            key=lambda version_id: (
                min(
                    region["physical_page"]
                    for key, region in regions.items()
                    if key[0] == version_id
                ),
                version_id,
            ),
        )
        if not expected_table_keys:
            raise _error("Family54 stored period repair has no exact page table frontier")
        checked_refs = [
            {"section_id": section_id, "table_id": table_id}
            for _version_id, section_id, table_id in expected_table_keys
        ]
        expected_target_ids = _table_row_target_ids(
            page_json_by_version,
            version_id=base_id,
            table_refs=checked_refs,
        )
        base_page = page_json_by_version[base_id]
        target_axis = table_axis_repair_targets_v1(base_page, table_refs=checked_refs)
        if (
            plan.get("target_table_refs") != checked_refs
            or plan.get("target_ids") != expected_target_ids
            or plan.get("target_cell_refs") != []
        ):
            raise _error("Family54 stored period repair target frontier drifted")
        expected_cells = []
    else:
        raise _error("Family54 stored repair scope is unsupported")

    targeted = sorted(reasons & applicable)
    expected_policy = canonical_clone_v1(_ACCEPTANCE_POLICY)
    required_status = UNRESOLVED if reasons - set(targeted) else READY
    if len(expected_frontier_ids) == 1:
        expected_policy["require_candidate_status"] = required_status
    else:
        expected_policy["allowed_candidate_statuses"] = [UNRESOLVED, READY]
        expected_policy["require_local_period_scope_resolution"] = True
    target_regions = [
        regions[(base_id, ref["section_id"], ref["table_id"])] for ref in checked_refs
    ]
    primary = min(
        target_regions,
        key=lambda region: _table_ref_sort_key(region),
    )
    if (
        plan.get("format_version") != REPAIR_QUEUE_FORMAT_VERSION
        or plan.get("repair_contract_version") != REPAIR_CONTRACT_VERSION
        or plan.get("family_id") != FAMILY_ID
        or plan.get("candidate_id") != candidate["candidate_id"]
        or plan.get("trigger_reasons") != candidate["reasons"]
        or plan.get("targeted_trigger_reasons") != targeted
        or plan.get("trigger_kinds") != expected_trigger_kinds
        or not same_typed_json_v1(plan.get("acceptance_policy"), expected_policy)
        or not same_typed_json_v1(plan.get("repair_policy"), _REPAIR_POLICY)
        or plan.get("component_table_refs") != checked_refs
        or plan.get("repair_frontier_base_page_json_version_ids") != expected_frontier_ids
        or plan.get("repair_target_axis_sha256") != canonical_json_sha256_v1(target_axis)
        or plan.get("physical_page") != primary["physical_page"]
        or plan.get("section_id") != primary["section_id"]
        or plan.get("table_id") != primary["table_id"]
        or plan.get("source_logical_name") != candidate["source_logical_name"]
        or plan.get("source_sha256") != candidate["source_sha256"]
    ):
        raise _error("Family54 repair plan does not replay its exact stored scope")
    expected_plan = _repair_plan(
        sweep=sweep,
        trial=trial,
        candidate=candidate,
        regions=regions,
        version_id=base_id,
        repair_scope=scope,
        target_ids=expected_target_ids,
        target_table_refs=checked_refs if scope == "TABLE_PERIOD_AXIS" else [],
        target_cell_refs=expected_cells,
        target_axis=target_axis,
        repair_frontier_base_page_json_version_ids=expected_frontier_ids,
    )
    if not same_typed_json_v1(dict(plan), expected_plan):
        raise _error("Family54 repair plan does not replay its exact stored scope")


def _coalesce_segment_document_frontier_v1(
    *,
    sweep: Mapping[str, Any],
    plan: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    page_database: Path,
    replacement_by_base: Mapping[str, str],
) -> dict[str, Any]:
    selected_axis = sweep.get("indexed_query_evidence", {}).get("selected_page_axis")
    if type(selected_axis) is not list:
        raise _error("Family54 stored selected page frontier is absent")
    document_axis = [
        canonical_clone_v1(item)
        for item in selected_axis
        if type(item) is dict and item.get("document_ordinal") == plan["document_ordinal"]
    ]
    if not document_axis:
        raise _error("Family54 stored repair document page frontier is absent")
    replacement_counts = {base_id: 0 for base_id in replacement_by_base}
    for item in document_axis:
        base_id = item.get("page_json_version_id")
        if base_id in replacement_by_base:
            item["page_json_version_id"] = replacement_by_base[base_id]
            replacement_counts[base_id] += 1
    if set(replacement_counts.values()) - {1}:
        raise _error("Family54 document replay replacement axis drifted")
    loaded = load_page_json_versions_v1(
        page_database,
        page_json_version_ids=[item["page_json_version_id"] for item in document_axis],
    )
    if len(loaded) != len(document_axis):
        raise _error("Family54 repair document page JSON frontier is incomplete")
    page_records = []
    for axis, page in zip(document_axis, loaded, strict=True):
        if (
            page.get("page_json_version_id") != axis["page_json_version_id"]
            or page.get("physical_page") != axis["physical_page"]
            or page.get("source_logical_name") != axis["source_logical_name"]
            or page.get("source_sha256") != axis["source_sha256"]
        ):
            raise _error("Family54 repair document page provenance drifted")
        page_records.append({**axis, "page_json": page["page_json"]})
    return coalesce_gemini_json_equity_matrix_document_v1(
        page_records=page_records,
        compiled_specs=compiled_specs,
    )


def stored_segment_repair_authority_v1(
    *,
    results_database: Path,
    family_run_id: str,
    plan: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    page_database: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load and authenticate one stored Family54 plan before provider use."""

    sweep = load_gemini_accounting_family_sweep_v1(results_database, family_run_id)
    embedded = compile_gemini_json_flat_family_specs_v1(
        sweep["specs"]["topology"]["value"],
        sweep["specs"]["evaluation"]["value"],
        sweep["specs"]["schema_binding"]["value"],
    )
    if (
        sweep.get("family_id") != FAMILY_ID
        or embedded.get("segment_report_mode") is not True
        or embedded.get("engine_format_version") != "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1"
        or not same_typed_json_v1(embedded, dict(compiled_specs))
        or plan.get("sweep_id") != sweep.get("sweep_id")
    ):
        raise _error("Family54 worker specs or stored sweep authority drifted")
    selected_axis = sweep.get("indexed_query_evidence", {}).get("selected_page_axis")
    selected_ids = (
        [item.get("page_json_version_id") for item in selected_axis]
        if type(selected_axis) is list and all(type(item) is dict for item in selected_axis)
        else []
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise _error("Family54 stored worker selected page frontier is invalid")
    database_stat = page_database.stat()
    cache_key = (
        database_stat.st_dev,
        database_stat.st_ino,
        family_run_id,
        sweep["sweep_id"],
        canonical_json_sha256_v1(dict(compiled_specs)),
    )
    if cache_key not in _AUTHENTICATED_BASE_SWEEP_FRONTIERS:
        validate_selected_equity_matrix_family_candidate_replays_v1(
            page_database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled_specs,
            indexed_query_evidence=sweep["indexed_query_evidence"],
            trials=sweep["trials"],
        )
        _AUTHENTICATED_BASE_SWEEP_FRONTIERS.add(cache_key)
    trials = [
        trial
        for trial in sweep["trials"]
        if trial["document_ordinal"] == plan.get("document_ordinal")
    ]
    candidates = (
        [
            candidate
            for candidate in trials[0]["candidates"]
            if candidate["candidate_id"] == plan.get("candidate_id")
        ]
        if len(trials) == 1
        else []
    )
    if len(candidates) != 1:
        raise _error("Family54 stored repair candidate is not unique")
    candidate = candidates[0]
    if (
        candidate.get("status") != UNRESOLVED
        or plan.get("candidate_semantic_replay_sha256") != canonical_json_sha256_v1(candidate)
        or plan.get("candidate_component_region_axis_sha256")
        != canonical_json_sha256_v1(candidate.get("component_regions"))
    ):
        raise _error("Family54 stored repair candidate identity drifted")
    document_clusters = [
        cluster
        for cluster in sweep["indexed_query_evidence"]["accepted_clusters"]
        if cluster.get("document_ordinal") == plan["document_ordinal"]
    ]
    clusters = [
        cluster
        for cluster in document_clusters
        if same_typed_json_v1(cluster.get("component_regions"), candidate["component_regions"])
    ]
    if len(document_clusters) != 1 or len(clusters) != 1:
        raise _error("Family54 stored repair query cluster does not replay")
    replayed_base_cluster = _coalesce_segment_document_frontier_v1(
        sweep=sweep,
        plan=plan,
        compiled_specs=compiled_specs,
        page_database=page_database,
        replacement_by_base={},
    )
    if not same_typed_json_v1(replayed_base_cluster, clusters[0]):
        raise _error("Family54 stored repair document cluster drifted")
    expected_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        clusters[0]["component_regions"], owner_receipt=clusters[0]["owner_receipt"]
    )
    if not same_typed_json_v1(
        candidate.get("closure_receipt", {}).get("query_receipt"), expected_query
    ):
        raise _error("Family54 stored repair candidate query receipt drifted")
    component_ids = list(
        dict.fromkeys(region["page_json_version_id"] for region in candidate["component_regions"])
    )
    loaded = load_page_json_versions_v1(page_database, page_json_version_ids=component_ids)
    page_json_by_version = {item["page_json_version_id"]: item["page_json"] for item in loaded}
    if set(page_json_by_version) != set(component_ids):
        raise _error("Family54 stored repair component page frontier is incomplete")
    _validate_stored_segment_repair_plan_v1(
        sweep=sweep,
        plan=plan,
        trial=trials[0],
        candidate=candidate,
        compiled_specs=compiled_specs,
        page_json_by_version=page_json_by_version,
    )
    base_page = page_json_by_version.get(plan["base_page_json_version_id"])
    if type(base_page) is not dict:
        raise _error("Family54 stored repair base page is outside its component frontier")
    return sweep, candidate, clusters[0], base_page


def authenticate_segment_repair_observation_v1(
    *, plan: Mapping[str, Any], observation: Mapping[str, Any], page_database: Path
) -> str:
    """Require one direct base-to-observed lineage with only planned targets changed."""

    identities = observation.get("database_identities")
    observed_lineage = observation.get("lineage")
    if type(identities) is not dict or type(observed_lineage) is not dict:
        raise _error("Family54 repair observation lineage is absent")
    version_id = identities.get("page_json_version_id")
    if type(version_id) is not str:
        raise _error("Family54 repair observation page identity is invalid")
    replayed = page_json_region_repair_lineages_v1(
        page_database, observed_page_json_version_ids=[version_id]
    )[0]
    expected_lineage = {
        "base_page_json_version_id": replayed["base_page_json_version_id"],
        "merged_page_json_version_id": replayed["canonical_merged_page_json_version_id"],
        "observed_page_json_version_id": replayed["observed_page_json_version_id"],
        "repair_id": replayed["repair_id"],
        "repair_receipt_sha256": replayed["repair_receipt_sha256"],
    }
    expected_change_ids = (
        plan["target_ids"]
        if plan["repair_scope"] == "ROW_VALUES"
        else [f"{ref['section_id']}:{ref['table_id']}" for ref in plan["target_table_refs"]]
    )
    changes = replayed["repair_receipt"].get("changes")
    merged_version_id = replayed["canonical_merged_page_json_version_id"]
    if (
        replayed["base_page_json_version_id"] != plan["base_page_json_version_id"]
        or replayed["observed_page_json_version_id"] != version_id
        or type(merged_version_id) is not str
        or not merged_version_id.startswith("gfpstorev1:json:")
        or not same_typed_json_v1(observed_lineage, expected_lineage)
        or type(changes) is not list
        or [change.get("target_id") for change in changes if type(change) is dict]
        != expected_change_ids
        or len(changes) != len(expected_change_ids)
    ):
        raise _error("Family54 repair direct lineage or changed target axis drifted")
    loaded = load_page_json_versions_v1(
        page_database,
        page_json_version_ids=list(
            dict.fromkeys([plan["base_page_json_version_id"], merged_version_id])
        ),
    )
    pages = {item["page_json_version_id"]: item["page_json"] for item in loaded}
    if set(pages) != {plan["base_page_json_version_id"], merged_version_id}:
        raise _error("Family54 repair surface page lineage is incomplete")
    expected_page = canonical_clone_v1(pages[plan["base_page_json_version_id"]])
    if plan["repair_scope"] == "ROW_VALUES":
        target_columns: dict[str, set[int]] = defaultdict(set)
        for ref in plan["target_cell_refs"]:
            target_id = f"{ref['section_id']}:{ref['table_id']}:{ref['row_id']}"
            target_columns[target_id].add(_node_ordinal(ref["column_id"], prefix="c") - 1)
        if set(target_columns) != set(expected_change_ids):
            raise _error("Family54 repair cell frontier does not cover its target rows")
        for change in changes:
            if type(change) is not dict or set(change) != {
                "target_id",
                "values_after_exact",
                "values_before_exact",
            }:
                raise _error("Family54 row repair lineage fields drifted")
            section_id, table_id, row_id = change["target_id"].split(":")
            row = expected_page["sections"][_node_ordinal(section_id, prefix="s") - 1]["tables"][
                _node_ordinal(table_id, prefix="t") - 1
            ]["rows"][_node_ordinal(row_id, prefix="r") - 1]
            before = change["values_before_exact"]
            after = change["values_after_exact"]
            if (
                type(before) is not list
                or type(after) is not list
                or len(before) != len(after)
                or not same_typed_json_v1(before, row["values_exact"])
                or any(index >= len(before) for index in target_columns[change["target_id"]])
                or any(
                    index not in target_columns[change["target_id"]]
                    and not same_typed_json_v1(before[index], after[index])
                    for index in range(len(before))
                )
            ):
                raise _error("Family54 row repair changed values outside planned cells")
            row["values_exact"] = canonical_clone_v1(after)
    else:
        for change in changes:
            if type(change) is not dict or set(change) != {
                "axis_after_exact",
                "axis_before_exact",
                "target_id",
            }:
                raise _error("Family54 table-axis repair lineage fields drifted")
            section_id, table_id = change["target_id"].split(":")
            table = expected_page["sections"][_node_ordinal(section_id, prefix="s") - 1]["tables"][
                _node_ordinal(table_id, prefix="t") - 1
            ]
            before = {
                "columns_header_path_exact": [
                    column["header_path_exact"] for column in table["columns"]
                ],
                "table_title_exact": table["title_exact"],
            }
            after = change["axis_after_exact"]
            if (
                not same_typed_json_v1(change["axis_before_exact"], before)
                or type(after) is not dict
                or set(after) != {"columns_header_path_exact", "table_title_exact"}
                or type(after["columns_header_path_exact"]) is not list
                or len(after["columns_header_path_exact"]) != len(table["columns"])
            ):
                raise _error("Family54 table-axis repair surface does not replay")
            table["title_exact"] = canonical_clone_v1(after["table_title_exact"])
            for column, header in zip(
                table["columns"], after["columns_header_path_exact"], strict=True
            ):
                column["header_path_exact"] = canonical_clone_v1(header)
    if not same_typed_json_v1(expected_page, pages[merged_version_id]):
        raise _error("Family54 repair changed page content outside its planned surface")
    return merged_version_id


def evaluate_segment_report_repair_observation_v1(
    *,
    plan: Mapping[str, Any],
    repaired_page_json_version_id: str,
    compiled_specs: Mapping[str, Any],
    page_database: Path,
    results_database: Path,
    family_run_id: str,
) -> dict[str, Any]:
    """Requery the full selected corpus and evaluate the repaired Family54 cluster."""

    sweep, stored_candidate, _stored_cluster, _base_page = stored_segment_repair_authority_v1(
        results_database=results_database,
        family_run_id=family_run_id,
        plan=plan,
        compiled_specs=compiled_specs,
        page_database=page_database,
    )
    prior_replacements = resolved_gemini_family_region_repair_candidate_replacements_v1(
        results_database,
        family_run_id=family_run_id,
        candidate_id=plan["candidate_id"],
        exclude_repair_job_id=plan["repair_job_id"],
    )
    permitted_bases = set(plan["repair_frontier_base_page_json_version_ids"])
    if plan["base_page_json_version_id"] not in permitted_bases or any(
        replacement["base_page_json_version_id"] not in permitted_bases
        or replacement["document_ordinal"] != plan["document_ordinal"]
        for replacement in prior_replacements
    ):
        raise _error("Family54 composed repair escaped its candidate page frontier")
    stored_trials = [
        trial for trial in sweep["trials"] if trial["document_ordinal"] == plan["document_ordinal"]
    ]
    original_component_ids = list(
        dict.fromkeys(
            region["page_json_version_id"] for region in stored_candidate["component_regions"]
        )
    )
    original_loaded = load_page_json_versions_v1(
        page_database, page_json_version_ids=original_component_ids
    )
    original_pages = {item["page_json_version_id"]: item["page_json"] for item in original_loaded}
    if len(stored_trials) != 1 or set(original_pages) != set(original_component_ids):
        raise _error("Family54 composed repair source frontier is incomplete")
    for replacement in prior_replacements:
        prior_plan = replacement["plan"]
        _validate_stored_segment_repair_plan_v1(
            sweep=sweep,
            plan=prior_plan,
            trial=stored_trials[0],
            candidate=stored_candidate,
            compiled_specs=compiled_specs,
            page_json_by_version=original_pages,
        )
        replayed = page_json_region_repair_lineages_v1(
            page_database,
            observed_page_json_version_ids=[replacement["selected_page_json_version_id"]],
        )[0]
        observed_lineage = {
            "base_page_json_version_id": replayed["base_page_json_version_id"],
            "merged_page_json_version_id": replayed["canonical_merged_page_json_version_id"],
            "observed_page_json_version_id": replayed["observed_page_json_version_id"],
            "repair_id": replayed["repair_id"],
            "repair_receipt_sha256": replayed["repair_receipt_sha256"],
        }
        authenticated = authenticate_segment_repair_observation_v1(
            plan=prior_plan,
            observation={
                "database_identities": {
                    "page_json_version_id": replacement["selected_page_json_version_id"]
                },
                "lineage": observed_lineage,
            },
            page_database=page_database,
        )
        if authenticated != replacement["selected_page_json_version_id"]:
            raise _error("Family54 composed repair lineage drifted")
    replacement_by_base = {
        replacement["base_page_json_version_id"]: replacement["selected_page_json_version_id"]
        for replacement in prior_replacements
    }
    if plan["base_page_json_version_id"] in replacement_by_base:
        raise _error("Family54 current repair page was already replaced")
    replacement_by_base[plan["base_page_json_version_id"]] = repaired_page_json_version_id
    cluster = _coalesce_segment_document_frontier_v1(
        sweep=sweep,
        plan=plan,
        compiled_specs=compiled_specs,
        page_database=page_database,
        replacement_by_base=replacement_by_base,
    )
    expected_regions = canonical_clone_v1(stored_candidate["component_regions"])
    component_replacement_counts = {base_id: 0 for base_id in replacement_by_base}
    for region in expected_regions:
        base_id = region["page_json_version_id"]
        if base_id in replacement_by_base:
            region["page_json_version_id"] = replacement_by_base[base_id]
            component_replacement_counts[base_id] += 1
    if any(count < 1 for count in component_replacement_counts.values()) or not same_typed_json_v1(
        cluster.get("component_regions"), expected_regions
    ):
        raise _error("Family54 repaired full component cluster drifted")
    component_ids = list(
        dict.fromkeys(region["page_json_version_id"] for region in cluster["component_regions"])
    )
    loaded = load_page_json_versions_v1(page_database, page_json_version_ids=component_ids)
    page_json_by_version = {item["page_json_version_id"]: item["page_json"] for item in loaded}
    if set(page_json_by_version) != set(component_ids):
        raise _error("Family54 repaired component page frontier is incomplete")
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    from bctc_ai.evaluation.gemini_json_segment_report_matrix_v1 import (
        validate_gemini_json_segment_report_candidate_binding_v1,
    )

    return validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={
            "source_logical_name": plan["source_logical_name"],
            "source_sha256": plan["source_sha256"],
        },
        cluster=cluster,
        compiled_specs=compiled_specs,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--effective-page-artifact-root", type=Path)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--family-run-id", required=True)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    binding = _stored_run_binding(args.results_database, family_run_id=args.family_run_id)
    try:
        sweep = validate_gemini_json_flat_family_sweep_v1(json.loads(bytes(binding["sweep_bytes"])))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("stored Family54 sweep does not validate") from exc
    if args.corpus_index.is_symlink() or not args.corpus_index.is_file():
        raise _error("Family54 corpus index authority is absent or a symlink")
    try:
        corpus_index_path = args.corpus_index.resolve(strict=True)
    except OSError as exc:
        raise _error("Family54 corpus index authority is absent") from exc
    corpus_index_ref = {
        "path": str(corpus_index_path),
        "sha256": binding["corpus_index_sha256"],
        "size_bytes": corpus_index_path.stat().st_size,
    }
    try:
        index = validate_current_corpus_manifest_index_v1(
            json.loads(
                family_store._authenticated_file_bytes_v1(  # noqa: SLF001
                    corpus_index_path, corpus_index_ref
                )
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        raise _error("Family54 corpus index authority does not authenticate") from exc
    if (
        index["corpus_manifest_index_id"] != binding["corpus_manifest_index_id"]
        or sweep["sweep_id"] != binding["sweep_id"]
    ):
        raise _error("stored Family54 run does not bind the supplied base corpus frontier")
    for name, field in (
        ("topology", "topology_spec_sha256"),
        ("evaluation", "evaluation_spec_sha256"),
        ("schema_binding", "schema_binding_spec_sha256"),
    ):
        if sweep["specs"][name]["sha256"] != binding[field]:
            raise _error("stored Family54 run spec hashes drifted")
    compiled = compile_gemini_json_flat_family_specs_v1(
        sweep["specs"]["topology"]["value"],
        sweep["specs"]["evaluation"]["value"],
        sweep["specs"]["schema_binding"]["value"],
    )
    if (
        not args.artifact_root.is_absolute()
        or args.artifact_root.is_symlink()
        or not args.artifact_root.is_dir()
    ):
        raise _error("Family54 artifact root is not an absolute regular directory")
    artifact_root = args.artifact_root.resolve()
    effective_frontier = sweep.get("effective_page_frontier")
    effective_artifact_root = None
    source_database_ref = index["database_ref"]
    source_database_root = artifact_root
    if effective_frontier is not None:
        stages = effective_page_frontier_stages_v1(effective_frontier)
        source_database_ref = stages[-1]["database_ref"]
        root_arg = args.effective_page_artifact_root
        effective_artifact_root = artifact_root if root_arg is None else root_arg
        if (
            not effective_artifact_root.is_absolute()
            or effective_artifact_root.is_symlink()
            or not effective_artifact_root.is_dir()
        ):
            raise _error("Family54 effective page artifact root is not trusted")
        effective_artifact_root = effective_artifact_root.resolve()
        source_database_root = effective_artifact_root
    elif args.effective_page_artifact_root is not None:
        raise _error("effective page artifact root requires an effective Family54 sweep")
    try:
        source_database = family_store._artifact_content_path_v1(  # noqa: SLF001
            source_database_root, source_database_ref
        )
        family_store._authenticate_file_ref_v1(  # noqa: SLF001
            source_database, source_database_ref
        )
    except (RuntimeError, ValueError) as exc:
        raise _error("Family54 page database authority does not authenticate") from exc
    _assert_disjoint_databases(
        source_database=source_database, results_database=args.results_database
    )
    try:
        selected_ids = family_store._selected_corpus_page_frontier_v1(  # noqa: SLF001
            corpus_index_ref=corpus_index_ref,
            corpus_artifact_root=artifact_root,
            effective_page_artifact_root=effective_artifact_root,
            checked_sweep=sweep,
            source_page_database=source_database,
        )
    except (RuntimeError, ValueError) as exc:
        raise _error("Family54 selected corpus frontier does not authenticate") from exc
    with _authenticated_sqlite_snapshot(source_database, reference=source_database_ref) as guard:
        validate_selected_equity_matrix_family_candidate_replays_v1(
            guard.path,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=sweep["indexed_query_evidence"],
            trials=sweep["trials"],
        )
        component_ids = sorted(
            {
                region["page_json_version_id"]
                for trial in sweep["trials"]
                if trial["status"] == UNRESOLVED
                for candidate in trial["candidates"]
                if candidate["status"] == UNRESOLVED
                and set(candidate["reasons"]) & (_PERIOD_REASONS | _MONEY_REASONS)
                for region in candidate["component_regions"]
            }
        )
        if not set(component_ids) <= set(selected_ids):
            raise _error("Family54 repair components escape the selected corpus frontier")
        loaded_pages = (
            load_page_json_versions_v1(guard.path, page_json_version_ids=component_ids)
            if component_ids
            else []
        )
        page_json_by_version = {
            page["page_json_version_id"]: page["page_json"] for page in loaded_pages
        }
        guard.validate()
    prior_terminal_target_keys: set[tuple[str, int, str, str]] = set()
    if effective_frontier is not None:
        for stage in effective_page_frontier_stages_v1(effective_frontier):
            prior_results_database = family_store._artifact_content_path_v1(  # noqa: SLF001
                effective_artifact_root, stage["results_database_ref"]
            )
            family_store._authenticate_file_ref_v1(  # noqa: SLF001
                prior_results_database, stage["results_database_ref"]
            )
            prior_terminal_target_keys.update(
                _terminal_repair_target_keys(
                    prior_results_database,
                    family_run_id=stage["repair_source_family_run_id"],
                )
            )
    plans, identifiers = enqueue_segment_report_region_repair_plans_v1(
        args.results_database,
        family_run_id=args.family_run_id,
        sweep=sweep,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled,
        prior_terminal_repair_target_keys=prior_terminal_target_keys,
    )
    scope_counts = {
        scope: sum(plan["repair_scope"] == scope for plan in plans)
        for scope in ("ROW_VALUES", "TABLE_PERIOD_AXIS")
    }
    return {
        "disposition": "SUCCEEDED",
        "family_id": FAMILY_ID,
        "family_run_id": args.family_run_id,
        "format_version": FORMAT_VERSION,
        "pending_region_repair_job_count": len(identifiers),
        "prior_terminal_repair_suppressed_count": sum(
            _repair_target_key(plan) in prior_terminal_target_keys
            for plan in build_segment_report_region_repair_plans_v1(
                sweep=sweep,
                page_json_by_version=page_json_by_version,
                compiled_specs=compiled,
            )
        ),
        "repair_job_ids": identifiers,
        "repair_plan_axis_sha256": canonical_json_sha256_v1(plans),
        "repair_scope_counts": scope_counts,
        "sweep_id": sweep["sweep_id"],
    }


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
