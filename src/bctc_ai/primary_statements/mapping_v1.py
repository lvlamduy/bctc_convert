"""Row-to-ReportNormId mapping with explicit dispositions for every source row.

A candidate identity comes from the catalog index; it survives only if its
statement, cash-flow branch, structural constraints and schema scope agree with
the source row. Exactly one survivor maps; none or several never fall back to a
nearest label. A ReportNormId mapped twice in one instance is accepted only as
an identical repetition (all lane raws equal), otherwise both rows are
unresolved. Equal values never justify first-wins/last-wins between different
presentations: a duplicate presentation is retired only by a rounding proof
against a higher-precision unit of the same statement, period and scope.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from bctc_ai.primary_statements.assembly_v1 import LogicalRow, StatementInstance
from bctc_ai.primary_statements.catalog_v1 import PrimaryCatalog
from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.primary_statements.units_v1 import (
    SCALE,
    VND,
    VND_PER_SHARE,
    units_in_header_component_v1,
    units_in_row_label_annotation_v1,
)

MAPPING_VERSION = "PRIMARY_ROW_MAPPING_V1"
DASH_ZERO_POLICY = "GEMINI_JSON_FIRST_ACCOUNTING_DASH_AS_NUMERIC_ZERO_V1"
PER_SHARE_IDS = {4381}

MAPPED = "MAPPED"
MAPPED_HEADING = "MAPPED_HEADING_NO_VALUES"
STRUCTURAL = "STRUCTURAL"
SOURCE_ONLY = "SOURCE_ONLY"
DUPLICATE_CONTROL = "DUPLICATE_IDENTICAL_CONTROL"
PRESENTATION_CONTROL = "DUPLICATE_PRESENTATION_CONTROL"
UNRESOLVED = "UNRESOLVED"
AMBIGUOUS = "AMBIGUOUS"
OPEN_DISPOSITIONS = {UNRESOLVED, AMBIGUOUS}


@dataclass
class RowDisposition:
    row: LogicalRow
    disposition: str
    reason: str
    report_norm_id: int | None = None
    candidates: list[int] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    section: str | None = None
    parent_report_norm_id: str | None = None


def _parent_mapping(rows: list[RowDisposition], row: LogicalRow) -> str | None:
    if row.parent_row is None:
        return None
    parent = rows[row.parent_row]
    if parent.report_norm_id is not None:
        return str(parent.report_norm_id)
    if parent.disposition == STRUCTURAL and parent.reason.startswith("PSEUDO_HEADING:"):
        return parent.reason.split(":", 1)[1]
    return None


def map_instance_rows_v1(instance: StatementInstance, catalog: PrimaryCatalog) -> list[RowDisposition]:
    statement_catalog = catalog.statements[instance.statement]
    headings = statement_catalog.section_headings
    dispositions: list[RowDisposition] = []
    current_section: str | None = None
    for row in instance.rows:
        disposition = _map_one(row, dispositions, instance, catalog, current_section)
        if disposition.report_norm_id is not None:
            item = statement_catalog.items[disposition.report_norm_id]
            current_section = headings.get(str(item.report_norm_id), item.section)
        elif disposition.reason.startswith("PSEUDO_HEADING:"):
            current_section = headings.get(disposition.reason.split(":", 1)[1], current_section)
        disposition.section = current_section
        dispositions.append(disposition)
    _resolve_duplicate_targets(dispositions)
    return dispositions


def _map_one(
    row: LogicalRow,
    done: list[RowDisposition],
    instance: StatementInstance,
    catalog: PrimaryCatalog,
    current_section: str | None,
) -> RowDisposition:
    statement_catalog = catalog.statements[instance.statement]
    if not row.label_key:
        if row.has_numeric:
            return RowDisposition(row, UNRESOLVED, "UNLABELED_VALUE_ROW")
        return RowDisposition(row, STRUCTURAL, "EMPTY_OR_ENUMERATOR_ONLY_ROW_WITHOUT_VALUES")
    hits = statement_catalog.lookup(row.label_key)
    if not hits:
        if row.has_numeric:
            return RowDisposition(row, UNRESOLVED, "UNRECOGNIZED_VALUE_ROW_NO_CATALOG_IDENTITY")
        return RowDisposition(row, STRUCTURAL, "UNRECOGNIZED_HEADING_WITHOUT_VALUES")
    kinds = {hit.kind for hit in hits}
    if kinds == {"SOURCE_ONLY"}:
        return RowDisposition(row, SOURCE_ONLY, hits[0].target)
    if kinds == {"STRUCTURAL"}:
        if row.has_numeric:
            return RowDisposition(row, UNRESOLVED, "STRUCTURAL_LEAD_IN_CARRIES_VALUES")
        return RowDisposition(row, STRUCTURAL, hits[0].target)
    parent_id = _parent_mapping(done, row)
    parent_row = done[row.parent_row].row if row.parent_row is not None else None
    survivors, rejected = [], []
    for hit in hits:
        if hit.kind != "ITEM":
            continue
        item = statement_catalog.items[int(hit.target)]
        reason = None
        if instance.statement == "LCTT" and item.branch != instance.branch:
            reason = "CASH_FLOW_BRANCH"
        elif item.requires_values and not row.has_numeric:
            reason = "REQUIRES_VALUES"
        elif item.requires_parent and parent_id not in item.requires_parent:
            reason = f"REQUIRES_PARENT:{','.join(item.requires_parent)}:GOT:{parent_id}"
        elif item.requires_top_level and not _is_top_level(row, parent_row, parent_id, statement_catalog):
            reason = "REQUIRES_TOP_LEVEL"
        elif item.requires_section and current_section != item.requires_section:
            reason = f"REQUIRES_SECTION:{item.requires_section}:GOT:{current_section}"
        if reason:
            rejected.append({"report_norm_id": item.report_norm_id, "reason": reason})
        else:
            survivors.append(item)
    pseudo = [hit for hit in hits if hit.kind == "PSEUDO_HEADING"]
    if not survivors and pseudo and not row.has_numeric:
        return RowDisposition(row, STRUCTURAL, f"PSEUDO_HEADING:{pseudo[0].target}", rejected=rejected)
    if len(survivors) > 1:
        return RowDisposition(row, AMBIGUOUS, "MULTIPLE_IDENTITIES_SURVIVE_CONSTRAINTS",
                              candidates=sorted(item.report_norm_id for item in survivors), rejected=rejected)
    if not survivors:
        if not rejected:
            reason = "NO_ITEM_CANDIDATE_FOR_VALUED_HEADING_ALIAS"
        elif all(item["reason"] == "CASH_FLOW_BRANCH" for item in rejected):
            reason = "CASH_FLOW_BRANCH_UNRESOLVED" if instance.branch not in {"DIRECT", "INDIRECT"} else "IDENTITY_ONLY_IN_OTHER_CASH_FLOW_BRANCH"
        else:
            reason = "STRUCTURAL_CONSTRAINT_UNSATISFIED"
        if not row.has_numeric:
            return RowDisposition(row, STRUCTURAL, f"HEADING_WITHOUT_VALUES:{reason}", rejected=rejected)
        return RowDisposition(row, UNRESOLVED, reason, rejected=rejected)
    item = survivors[0]
    if instance.scope is not None and instance.scope not in item.scope:
        return RowDisposition(row, SOURCE_ONLY, f"POSSIBLE_SCHEMA_GAP_SCOPE:{item.report_norm_id}_IS_{'/'.join(item.scope)}_ONLY",
                              candidates=[item.report_norm_id], rejected=rejected)
    if instance.scope is None and tuple(item.scope) != ("SEPARATE", "CONSOLIDATED"):
        return RowDisposition(row, UNRESOLVED, "SCOPE_RESTRICTED_IDENTITY_WITH_UNRESOLVED_SCOPE",
                              candidates=[item.report_norm_id], rejected=rejected)
    if not row.has_numeric:
        return RowDisposition(row, MAPPED_HEADING, "IDENTITY_WITHOUT_PRINTED_VALUES",
                              report_norm_id=item.report_norm_id, rejected=rejected, parent_report_norm_id=parent_id)
    return RowDisposition(row, MAPPED, "UNIQUE_SURVIVING_IDENTITY", report_norm_id=item.report_norm_id,
                          rejected=rejected, parent_report_norm_id=parent_id)


def _is_top_level(row: LogicalRow, parent_row: LogicalRow | None, parent_id: str | None, statement_catalog) -> bool:
    if parent_row is None:
        return True
    if parent_row.enumerator_class == "SECTION_LETTER":
        return True
    return parent_id is not None and parent_id in statement_catalog.section_headings


def _resolve_duplicate_targets(dispositions: list[RowDisposition]) -> None:
    by_id: dict[int, list[RowDisposition]] = defaultdict(list)
    for item in dispositions:
        if item.disposition in {MAPPED, MAPPED_HEADING} and item.report_norm_id is not None:
            by_id[item.report_norm_id].append(item)
    for rnid, group in by_id.items():
        if len(group) < 2:
            continue
        valued = [item for item in group if item.disposition == MAPPED]
        if len(valued) == 1:
            # A heading that repeats the label of the one valued row (e.g. a section
            # title "Lưu chuyển tiền thuần từ ..." above its own total) is structure.
            for item in group:
                if item is not valued[0]:
                    item.disposition = STRUCTURAL
                    item.reason = f"HEADING_REPEATS_LABEL_OF_VALUED_ROW_{valued[0].row.uid}"
                    item.report_norm_id = None
            continue
        if not valued:
            for item in group[1:]:
                item.disposition = STRUCTURAL
                item.reason = f"HEADING_REPEATS_LABEL_OF_ROW_{group[0].row.uid}"
                item.report_norm_id = None
            continue
        group = valued
        raws = {tuple(cell.raw for cell in item.row.cells) for item in group}
        if len(raws) == 1:
            # A row "brought forward from the previous page" repeats the original;
            # the original is unannotated or "carried to the next page".
            plain = [item for item in group if not any(
                re.search(r"\b(?:tu|tu trang)\s+truoc\b|\btrang truoc\b", fold_vietnamese(annotation))
                for annotation in item.row.label_annotations
            )]
            keep = plain[0] if len(plain) == 1 else None
            if keep is None and len({item.row.label_key for item in group}) == 1 and group[0].disposition == MAPPED_HEADING:
                keep = group[0]
            if keep is None:
                for item in group:
                    item.disposition, item.reason = UNRESOLVED, "DUPLICATE_TARGET_WITHOUT_UNIQUE_PRIMARY_OCCURRENCE"
                continue
            for item in group:
                if item is not keep:
                    item.disposition = DUPLICATE_CONTROL
                    item.reason = f"IDENTICAL_REPETITION_OF_ROW_{keep.row.uid}"
        else:
            for item in group:
                item.disposition, item.reason = UNRESOLVED, f"DUPLICATE_TARGET_CONFLICT:{rnid}"


# --------------------------------------------------------------------------- cells


def row_measure_unit_v1(row: LogicalRow, report_norm_id: int, lane) -> tuple[str | None, str, list[dict[str, Any]]]:
    """Unit of one mapped cell: lane money unit, or per-share evidence for EPS rows."""

    if report_norm_id in PER_SHARE_IDS:
        evidence = [{"unit": u.unit, "source_kind": u.source_kind, "source_text": u.source_text}
                    for u in units_in_row_label_annotation_v1(row.label_annotations)]
        for item in lane.headers:
            for part in item["header_path_exact"]:
                evidence += [{"unit": u.unit, "source_kind": u.source_kind, "source_text": u.source_text}
                             for u in units_in_header_component_v1(part) if u.unit == VND_PER_SHARE]
        units = {VND_PER_SHARE if item["unit"] in {VND, VND_PER_SHARE} else item["unit"] for item in evidence}
        if units == {VND_PER_SHARE}:
            return VND_PER_SHARE, "RESOLVED", evidence
        return None, "UNRESOLVED_PER_SHARE_UNIT" if not units else "CONFLICT_PER_SHARE_UNIT", evidence
    return lane.unit, lane.unit_status, lane.unit_evidence


def cell_observation_v1(cell) -> tuple[str, str | None, str]:
    """(observation state, exact numeric text or None, numeric policy)."""

    if cell.state in {"VALUE", "PRINTED_ZERO"}:
        return ("OBSERVED_ZERO" if cell.state == "PRINTED_ZERO" else "OBSERVED_VALUE"), cell.value, "AS_PRINTED"
    if cell.state == "DASH":
        return "DASH_ZERO", "0", DASH_ZERO_POLICY
    if cell.state == "BLANK":
        return "BLANK", None, "NO_NUMERIC_VALUE"
    return "UNRESOLVED_CELL", None, f"CELL_{cell.state}:{cell.reason}"


# --------------------------------------------------------------------------- presentations


def _lane_values(instance: StatementInstance, dispositions: list[RowDisposition]) -> dict[tuple[int, str], Decimal]:
    values = {}
    for item in dispositions:
        if item.disposition != MAPPED or item.report_norm_id in PER_SHARE_IDS:
            continue
        for cell, lane in zip(item.row.cells, instance.lanes, strict=False):
            key = lane.period.get("key") if lane.period else None
            if key and cell.value is not None and cell.state in {"VALUE", "PRINTED_ZERO"}:
                values[(item.report_norm_id, key)] = Decimal(cell.value)
    return values


PRESENTATION_ROUNDING_POLICY = "LOWER_PRECISION_WITHIN_ONE_UNIT_OF_HIGHER_PRECISION_V1"


def _fail_group(group: list[StatementInstance], receipt: dict[str, Any], reason: str) -> None:
    receipt["status"] = "UNRESOLVED_DUPLICATE_PRESENTATION"
    receipt["reason"] = reason
    for instance in group:
        instance.status = "UNRESOLVED"
        instance.reasons.append(reason)


def resolve_duplicate_presentations_v1(
    instances: list[StatementInstance], dispositions: dict[str, list[RowDisposition]]
) -> list[dict[str, Any]]:
    """Retire a duplicate presentation only with an explicit cell-level proof.

    * Different units: the higher-precision presentation is primary; every
      overlapping cell must satisfy |high - low*ratio| < ratio (truncation or
      rounding of the same figure). A cell outside the tolerance is vetoed in
      the primary presentation and held; a cell only in the lower-precision
      copy is held as an unconfirmed lower-precision observation.
    * Same unit: retired only when every overlapping cell is exactly equal.
    * Anything else (missing units/periods, partial overlaps, three copies)
      holds every copy.
    """

    receipts = []
    groups: dict[tuple[str, str | None, tuple[str, ...]], list[StatementInstance]] = defaultdict(list)
    for instance in instances:
        keys = tuple(sorted(lane.period.get("key") or "?" for lane in instance.lanes))
        groups[(instance.statement, instance.scope, keys)].append(instance)
    for (statement, scope, keys), group in groups.items():
        if len(group) < 2:
            continue
        units = [{lane.unit for lane in instance.lanes} for instance in group]
        single = [next(iter(u)) if len(u) == 1 and None not in u else None for u in units]
        receipt = {"statement": statement, "scope": scope, "period_keys": list(keys),
                   "instances": [instance.key for instance in group], "units": single,
                   "policy": PRESENTATION_ROUNDING_POLICY}
        if None in single or "?" in keys or len(group) != 2:
            _fail_group(group, receipt, "DUPLICATE_PRESENTATION_WITHOUT_PRECISION_PROOF")
            receipts.append(receipt)
            continue
        ordered = sorted(zip(group, single, strict=True), key=lambda pair: (SCALE[pair[1]], pair[0].tables[0].order_key()))
        (high, high_unit), (low, low_unit) = ordered
        high_values = _lane_values(high, dispositions[high.key])
        low_values = _lane_values(low, dispositions[low.key])
        ratio = Decimal(SCALE[low_unit]) / Decimal(SCALE[high_unit])
        same_unit = ratio == 1
        mismatches, low_only, compared = [], [], 0
        for key, low_value in low_values.items():
            if key not in high_values:
                low_only.append(list(key))
                continue
            compared += 1
            residual = high_values[key] - low_value * ratio
            if (same_unit and residual != 0) or (not same_unit and abs(residual) >= ratio):
                mismatches.append({"key": list(key), "high": str(high_values[key]), "low": str(low_value),
                                   "residual_in_high_unit": str(residual)})
        receipt.update({
            "primary_presentation": high.key, "control_presentation": low.key, "ratio": str(ratio),
            "compared_cells": compared, "mismatch_count": len(mismatches), "mismatches": mismatches,
            "lower_precision_only_cells": low_only, "higher_precision_only_cells": len(set(high_values) - set(low_values)),
        })
        if compared == 0 or (same_unit and (mismatches or low_only)):
            _fail_group(group, receipt, "DUPLICATE_PRESENTATION_PROOF_FAILED")
            receipts.append(receipt)
            continue
        receipt["status"] = "CONTROL_RETIRED_WITH_CELL_VETOES" if mismatches or low_only else "CONTROL_RETIRED"
        low.presentation_role = "DUPLICATE_PRESENTATION_CONTROL"
        low.reasons.append(f"CONTROL_OF_{high.key}")
        vetoed = {tuple(item["key"]) for item in mismatches}
        for key in vetoed:
            high.cell_vetoes[key] = "CROSS_PRESENTATION_CONFLICT_WITH_" + low.key
        held_low = {tuple(key) for key in low_only} | vetoed
        for item in dispositions[low.key]:
            if item.disposition in {MAPPED, MAPPED_HEADING}:
                rows_keys = {(item.report_norm_id, lane.period.get("key")) for lane in low.lanes}
                if rows_keys & held_low:
                    item.disposition = UNRESOLVED
                    item.reason = f"LOWER_PRECISION_CELL_NOT_CONFIRMED_BY_{high.key}"
                else:
                    item.disposition = PRESENTATION_CONTROL
                    item.reason = f"CONSISTENT_PRESENTATION_OF_{high.key}"
        receipts.append(receipt)
    return receipts
