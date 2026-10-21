"""PRIMARY_ONLY document result contract with per-cell acceptance.

Only final, selected mappings of PRIMARY presentations are exported. Every
source row of every assembled instance keeps a disposition; every schema item
of every found statement/scope gets an item status. A value is ACCEPTED only
when its row identity is unique, the instance, scope, cash-flow branch, lane
period and unit are resolved, the cell is a printed value/zero/validated dash
or an observed blank, no cross-presentation veto applies and no complete
accounting check involving it fails. Everything else is HOLD with reasons.
The write key (document, scope, statement, period, ReportNormId) must be
unique; a collision holds every colliding cell instead of choosing one.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from bctc_ai.primary_statements.catalog_v1 import PrimaryCatalog
from bctc_ai.primary_statements.mapping_v1 import (
    AMBIGUOUS,
    MAPPED,
    MAPPED_HEADING,
    OPEN_DISPOSITIONS,
    SOURCE_ONLY,
    cell_observation_v1,
    row_measure_unit_v1,
)
from bctc_ai.primary_statements.validation_v1 import PASS_STATES
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

RESULT_FORMAT_VERSION = "PRIMARY_ONLY_DOCUMENT_RESULT_V1"
PRODUCT_LABEL = "PRIMARY_ONLY"
PRODUCT_NOTICE = (
    "PRIMARY_ONLY: CDKT/KQKD/LCTT only. Financial-statement notes (TM) are not "
    "included and were not evaluated; absence of TM data is not NOT_OBSERVED."
)


def _cell_dict(cell) -> dict[str, Any]:
    return {
        "lane": cell.lane, "column_ordinal": cell.column_ordinal, "raw": cell.raw, "parse_state": cell.state,
        "value": cell.value, "qualifiers": list(cell.qualifiers), "separator_basis": cell.separator_basis,
        "parse_reason": cell.reason,
    }


def _row_dict(row, disposition, uid_by_index) -> dict[str, Any]:
    return {
        "row_uid": row.uid,
        "locator": {**row.locator, "row_ordinal": row.row_ordinal},
        "instance_row_ordinal": row.instance_row_ordinal,
        "label_exact": row.label_exact,
        "label_source": row.label_source,
        "label_key": row.label_key,
        "label_annotations": list(row.label_annotations),
        "enumerator": row.enumerator,
        "enumerator_class": row.enumerator_class,
        "code": row.code,
        "note_ref": row.note_ref,
        "row_kind": row.row_kind,
        "hierarchy_path_exact": row.hierarchy_path_exact,
        "parent_row_uid": uid_by_index.get(row.parent_row),
        "parent_basis": row.parent_basis,
        "parent_conflict": row.parent_conflict,
        "merged_fragments": row.merged_fragments,
        "text_cells": row.text_cells,
        "measure_cells": row.measure_cells,
        "cells": [_cell_dict(cell) for cell in row.cells],
        "disposition": disposition.disposition,
        "reason": disposition.reason,
        "report_norm_id": disposition.report_norm_id,
        "candidates": disposition.candidates,
        "rejected_candidates": disposition.rejected,
        "section": disposition.section,
    }


def _lane_dict(lane) -> dict[str, Any]:
    return {
        "lane": lane.index, "headers": lane.headers, "header_text": lane.header_text, "period": lane.period,
        "unit": lane.unit, "unit_status": lane.unit_status, "unit_evidence": lane.unit_evidence,
        "status": lane.status, "reasons": lane.reasons,
    }


def build_document_result_v1(run, catalog: PrimaryCatalog, *, corpus_identity: dict[str, Any],
                             pins: dict[str, Any]) -> dict[str, Any]:
    document = run.document
    instances = []
    cells = []
    for instance in run.instances:
        dispositions = run.dispositions[instance.key]
        uid_by_index = {index: item.row.uid for index, item in enumerate(dispositions)}
        validations = run.validations.get(instance.key, [])
        failing = defaultdict(list)
        for result in validations:
            if result.status == "FAIL":
                for rnid in result.participants():
                    failing[(rnid, result.lane)].append(result.equation_id)
        instance_hold = []
        if instance.status != "ASSEMBLED":
            instance_hold.append("INSTANCE_UNRESOLVED:" + ",".join(sorted(set(instance.reasons))))
        if instance.scope is None:
            instance_hold.append("SCOPE_UNRESOLVED")
        if instance.statement == "LCTT" and instance.branch not in {"DIRECT", "INDIRECT"}:
            instance_hold.append("CASH_FLOW_BRANCH_UNRESOLVED")
        exported = instance.presentation_role == "PRIMARY"
        for item in dispositions if exported else []:
            if item.disposition != MAPPED:
                continue
            for cell, lane in zip(item.row.cells, instance.lanes, strict=False):
                state, value, policy = cell_observation_v1(cell)
                if (item.report_norm_id, cell.lane) in instance.dash_unvalidated:
                    state, value, policy = "DASH", None, "DASH_CONTRADICTED_BY_VALUED_COMPONENTS"
                unit, unit_status, unit_evidence = row_measure_unit_v1(item.row, item.report_norm_id, lane)
                period_key = lane.period.get("key") if lane.period else None
                reasons = list(instance_hold)
                if lane.period is None or not period_key:
                    reasons.append("PERIOD_UNRESOLVED:" + str((lane.period or {}).get("reason")))
                if "DUPLICATE_PERIOD_LANE" in lane.reasons:
                    reasons.append("DUPLICATE_PERIOD_LANE")
                if unit_status != "RESOLVED":
                    reasons.append(f"UNIT_{unit_status}")
                if state in {"UNRESOLVED_CELL", "DASH"}:
                    reasons.append(f"CELL_{state}:{policy}")
                veto = instance.cell_vetoes.get((item.report_norm_id, period_key)) if period_key else None
                if veto:
                    reasons.append(veto)
                for equation in failing.get((item.report_norm_id, cell.lane), []):
                    reasons.append(f"VALIDATION_FAIL:{equation}")
                acceptance = "HOLD" if reasons else ("ACCEPTED_BLANK" if state == "BLANK" else "ACCEPTED")
                cells.append({
                    "write_key": [document.document_plan_id, instance.scope, instance.statement, period_key,
                                  item.report_norm_id],
                    "statement": instance.statement,
                    "scope": instance.scope,
                    "report_norm_id": item.report_norm_id,
                    "instance_key": instance.key,
                    "row_uid": item.row.uid,
                    "lane": cell.lane,
                    "period_key": period_key,
                    "period": lane.period,
                    "unit": unit,
                    "unit_evidence": unit_evidence,
                    "observation_state": state,
                    "value": value,
                    "raw": cell.raw,
                    "numeric_policy": policy,
                    "locator": {**item.row.locator, "row_ordinal": item.row.row_ordinal,
                                "column_ordinal": cell.column_ordinal},
                    "label_exact": item.row.label_exact,
                    "acceptance": acceptance,
                    "hold_reasons": reasons,
                    "validation": [
                        {"equation_id": r.equation_id, "status": r.status}
                        for r in validations if r.lane == cell.lane and item.report_norm_id in r.participants()
                    ],
                })
        instances.append({
            "instance_key": instance.key,
            "statement": instance.statement,
            "presentation_role": instance.presentation_role,
            "status": instance.status,
            "reasons": sorted(set(instance.reasons)),
            "scope": instance.scope,
            "scope_basis": instance.scope_basis,
            "entity_text": instance.entity_text,
            "cash_flow_branch": instance.branch,
            "cash_flow_branch_evidence": instance.branch_evidence,
            "separator_roles": instance.separator_roles,
            "period_context": instance.period_context,
            "tables": [{**source.locator, "classification": source.classification} for source in instance.tables],
            "lanes": [_lane_dict(lane) for lane in instance.lanes],
            "cell_vetoes": [[rnid, key, reason] for (rnid, key), reason in sorted(instance.cell_vetoes.items())],
            "dash_unvalidated": sorted([list(item) for item in instance.dash_unvalidated]),
            "source_rows": [_row_dict(item.row, item, uid_by_index) for item in dispositions],
            "validations": [result.to_dict() for result in validations],
        })
    _reject_write_key_collisions(cells)
    item_status = _item_status(run, catalog)
    result = {
        "format_version": RESULT_FORMAT_VERSION,
        "product_label": PRODUCT_LABEL,
        "product_notice": PRODUCT_NOTICE,
        "corpus": corpus_identity,
        "document": document.identity(),
        "pins": pins,
        "page_census": run.page_census,
        "non_primary_tables": [
            {**source.locator, "classification": source.classification} for source in run.other_tables
        ],
        "statement_status": run.statement_status,
        "presentation_receipts": run.presentation_receipts,
        "instances": instances,
        "cells": cells,
        "item_status": item_status,
    }
    result["result_id"] = "primaryresultv1:" + canonical_json_sha256_v1(result)
    return result


def _reject_write_key_collisions(cells: list[dict[str, Any]]) -> None:
    by_key = defaultdict(list)
    for cell in cells:
        if cell["period_key"] is not None and cell["scope"] is not None:
            by_key[tuple(cell["write_key"])].append(cell)
    for key, group in by_key.items():
        if len(group) > 1:
            for cell in group:
                cell["acceptance"] = "HOLD"
                cell["hold_reasons"].append("WRITE_KEY_COLLISION")


def _item_status(run, catalog: PrimaryCatalog) -> list[dict[str, Any]]:
    """One status per schema item for every found statement presentation/scope."""

    rows = []
    for instance in run.instances:
        if instance.presentation_role != "PRIMARY":
            continue
        statement_catalog = catalog.statements[instance.statement]
        dispositions = run.dispositions[instance.key]
        mapped = defaultdict(list)
        ambiguous = defaultdict(list)
        open_sections = defaultdict(int)
        scope_gaps = defaultdict(list)
        for item in dispositions:
            if item.disposition in {MAPPED, MAPPED_HEADING} and item.report_norm_id is not None:
                mapped[item.report_norm_id].append(item)
            if item.disposition == AMBIGUOUS:
                for rnid in item.candidates:
                    ambiguous[rnid].append(item)
            if item.disposition in OPEN_DISPOSITIONS and item.row.has_numeric:
                open_sections[item.section] += 1
            if item.disposition == SOURCE_ONLY and item.reason.startswith("POSSIBLE_SCHEMA_GAP_SCOPE"):
                for rnid in item.candidates:
                    scope_gaps[rnid].append(item)
        for rnid in statement_catalog.ordered_ids:
            spec = statement_catalog.items[rnid]
            status, reason, uids = None, None, []
            if instance.statement == "LCTT" and instance.branch in {"DIRECT", "INDIRECT"} and spec.branch != instance.branch:
                status, reason = "NOT_APPLICABLE", f"OTHER_CASH_FLOW_BRANCH:{instance.branch}"
            elif rnid in mapped:
                status = "MAPPED" if any(item.disposition == MAPPED for item in mapped[rnid]) else "MAPPED_HEADING_NO_VALUES"
                uids = [item.row.uid for item in mapped[rnid]]
            elif rnid in ambiguous:
                status, reason = "AMBIGUOUS", "ROW_WITH_MULTIPLE_SURVIVING_IDENTITIES"
                uids = [item.row.uid for item in ambiguous[rnid]]
            elif rnid in scope_gaps:
                status, reason = "SCHEMA_SCOPE_GAP", "SOURCE_ROW_PRESENT_BUT_IDENTITY_SCOPE_EXCLUDES_DOCUMENT_SCOPE"
                uids = [item.row.uid for item in scope_gaps[rnid]]
            elif instance.scope is not None and instance.scope not in spec.scope:
                status, reason = "NOT_APPLICABLE", f"IDENTITY_SCOPE_{'/'.join(spec.scope)}"
            elif instance.status != "ASSEMBLED" or (instance.statement == "LCTT" and instance.branch not in {"DIRECT", "INDIRECT"}):
                status, reason = "UNRESOLVED", "INSTANCE_UNRESOLVED"
            elif open_sections.get(spec.section) or open_sections.get(None):
                status, reason = "UNRESOLVED", "OPEN_SOURCE_RESIDUAL_IN_SECTION"
            else:
                status, reason = "NOT_OBSERVED", "BOUNDED_STATEMENT_SCAN_FOUND_NO_ROW"
            rows.append({
                "statement": instance.statement, "scope": instance.scope, "instance_key": instance.key,
                "report_norm_id": rnid, "display_order": spec.display_order, "status": status,
                "reason": reason, "row_uids": uids,
            })
    return rows
