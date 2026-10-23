"""LIST_BY_AXIS shape: rows are members of one axis (plus totals), columns are periods.

The matcher never chooses between competing readings: a row that matches two
members, a member printed twice, an unresolved subject or a failed equation
holds the affected cells with an explicit reason.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

from bctc_ai.notes.config_v1 import Family, all_phrases
from bctc_ai.notes.kernel_v1 import (
    DocumentContext,
    NoteLane,
    NoteTable,
    parse_cell_v1,
    resolve_instant_lanes_v1,
)
from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.primary_statements.units_v1 import SCALE

# "Cộng" only alone: "Công ty …" folds to the same "cong" and is not a total.
TOTAL_KEYS = re.compile(r"\A(?:tong\b.*|cong)\Z")
FIVE_TOTAL = "TOTAL_FIVE_GROUPS"
GRAND_TOTAL = "GRAND_TOTAL"


@dataclass
class RowRole:
    row_index: int
    role: str | None            # member, FIVE_TOTAL, GRAND_TOTAL or None
    disposition: str            # MEMBER | TOTAL | SOURCE_ONLY | HEADING | AMBIGUOUS
    reason: str
    candidates: list[str] = field(default_factory=list)


@dataclass
class TableEvaluation:
    table: NoteTable
    status: str                 # EVALUATED | REJECTED | UNRESOLVED
    reasons: list[str]
    subject: str | None = None
    subject_basis: dict[str, Any] = field(default_factory=dict)
    basis: str = "AS_PRESENTED"
    roles: list[RowRole] = field(default_factory=list)
    lanes: list[NoteLane] = field(default_factory=list)
    equations: list[dict[str, Any]] = field(default_factory=list)
    corroboration: list[dict[str, Any]] = field(default_factory=list)
    cells: list[dict[str, Any]] = field(default_factory=list)
    context: list[tuple[str, str]] = field(default_factory=list)
    block: dict[str, Any] | None = None


def _has_values(table: NoteTable, row) -> bool:
    return any(table.cells.get((row.row_id, column.column_id), (None, "BLANK"))[1] != "BLANK"
               for column in table.columns if column.value_kind == "MONEY")


def _is_composite(key: str, family: Family, member: str) -> bool:
    """'Nợ có khả năng mất vốn và các khoản nợ chờ xử lý' is G5 plus something else."""

    if member not in family.axis.members or not re.search(r"\b(?:va|cung)\b", key):
        return False
    spec = family.axis.members.get(member) or {}
    covered = key
    for alias in sorted(spec.get("aliases", []), key=len, reverse=True):
        covered = re.sub(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", covered)
    rest = re.sub(r"\s+", " ", covered).strip()
    return bool(re.search(r"\b(?:va|cung)\b\s+\S", rest))


def assign_roles_v1(table: NoteTable, family: Family) -> list[RowRole]:
    roles = []
    seen_outside = False
    seen_member = False
    for index, row in enumerate(table.rows):
        key = row.key
        matches = family.axis.match(key) if key else []
        if len(matches) > 1:
            roles.append(RowRole(index, None, "AMBIGUOUS", "ROW_MATCHES_SEVERAL_MEMBERS", matches))
            continue
        if matches and _is_composite(key, family, matches[0]):
            roles.append(RowRole(index, None, "SOURCE_ONLY", "COMPOSITE_ROW_MEMBER_PLUS_OTHER", matches))
            continue
        if matches:
            member = matches[0]
            if member in family.axis.outside_members:
                seen_outside = True
            else:
                seen_member = True
            roles.append(RowRole(index, member, "MEMBER", "AXIS_ALIAS"))
            continue
        is_total = row.kind == "TOTAL" or (key and TOTAL_KEYS.match(key))
        if is_total and seen_member:
            role = GRAND_TOTAL if seen_outside else FIVE_TOTAL
            roles.append(RowRole(index, role, "TOTAL", "TOTAL_AFTER_" + ("OUTSIDE_MEMBERS" if seen_outside else "GROUPS")))
            continue
        if not _has_values(table, row):
            roles.append(RowRole(index, None, "HEADING", "NO_VALUES"))
            continue
        roles.append(RowRole(index, None, "SOURCE_ONLY", "NO_AXIS_MEMBER_OR_TOTAL"))
    # A member or total printed twice makes the table ambiguous (no first-wins).
    counts: dict[str, int] = {}
    for role in roles:
        if role.role:
            counts[role.role] = counts.get(role.role, 0) + 1
    for role in roles:
        if role.role and counts[role.role] > 1:
            role.disposition, role.reason = "AMBIGUOUS", "MEMBER_PRINTED_MORE_THAN_ONCE"
            role.candidates, role.role = [role.role], None
    return roles


OWNER_SOURCES = {"BLOCK_HEADING", "TABLE_TITLE", "SECTION_TITLE", "SECTION_NARRATIVE"}


def resolve_subject_v1(family: Family, context: list[tuple[str, str]]) -> tuple[str | None, dict[str, Any]]:
    """The subject named by the table's own printed context, else by its note heading.

    All owner context (block heading, table title, section title, section
    narratives) is read, not the first hit: one distinct subject decides,
    two different subjects hold. Only without any owner evidence are the
    preceding titles up to the nearest numbered note heading read, with the
    same uniqueness rule. No first-wins, no equation-wins.
    """

    def subjects(entries):
        found = {}
        for source, text in entries:
            for subject in family.subjects_in(fold_vietnamese(text)):
                found.setdefault(subject, (source, text))
        return found

    owner = subjects([(s, t) for s, t in context if s in OWNER_SOURCES])
    tier, found = "OWNER_CONTEXT", owner
    if not owner:
        tier, found = "PRECEDING_NOTE_HEADING", subjects([(s, t) for s, t in context if s.startswith("PRECEDING_")])
    if len(found) == 1:
        subject, (source, text) = next(iter(found.items()))
        return subject, {"basis": source, "tier": tier, "text": text}
    if len(found) > 1:
        return None, {"basis": "AMBIGUOUS_SUBJECT", "tier": tier, "candidates": sorted(found)}
    return None, {"basis": "NO_PRINTED_SUBJECT"}


def owned_date_texts_v1(table: NoteTable, context: list[tuple[str, str]]) -> list[str]:
    """Texts that belong to this table for a date caption: its own title and
    block heading, its section title, and section narratives only when the
    section holds this table alone (a shared narrative date has no owner)."""

    keep = {"BLOCK_HEADING", "TABLE_TITLE", "SECTION_TITLE"}
    if table.section_table_count == 1:
        keep.add("SECTION_NARRATIVE")
    return [text for source, text in context if source in keep]


def classification_basis_v1(context: list[tuple[str, str]]) -> str:
    for source, text in context[:3]:
        folded = fold_vietnamese(text)
        if re.search(r"\btt\s*31\b|thong tu\s*(?:so\s*)?31\b", folded):
            return "TT31_2024"
        if re.search(r"\btt\s*11\b|thong tu\s*(?:so\s*)?11\b", folded):
            return "TT11_2021"
    return "AS_PRESENTED"


def _tolerance(unit: str | None, terms: int) -> Decimal:
    if unit and SCALE.get(unit, 1) >= 1_000_000:
        return Decimal(max(1, math.ceil(terms / 2)))
    return Decimal(0)


def axis_blocks_v1(table: NoteTable, family: Family) -> list[tuple[list[str], list[int]]]:
    """Runs of rows that belong to one axis breakdown inside a wider table.

    A run is a maximal sequence of axis members, outside members, totals,
    "Trong đó" sub-rows and value-less headings; any other valued row ends it.
    A regular member printed again starts a new run. Each run carries the
    value-less heading rows printed just above it (its printed caption).
    """

    blocks, current, seen, headings = [], [], set(), []
    pending_headings: list[str] = []

    def close():
        nonlocal current, seen, headings
        if current:
            blocks.append((headings, current))
        current, seen, headings = [], set(), []

    for index, row in enumerate(table.rows):
        key = row.key
        matches = family.axis.match(key) if key else []
        valued = _has_values(table, row)
        is_total = row.kind in {"TOTAL", "SUBTOTAL"} or bool(key and TOTAL_KEYS.match(key))
        if not valued:
            if row.label:
                if current:
                    close()
                pending_headings.append(row.label)
            continue
        regular = [m for m in matches if m in family.axis.members]
        if regular and regular[0] in seen:
            close()
        # A run starts only at a regular member; outside members and totals only extend one.
        if regular or (current and (matches or is_total or key.startswith("trong do"))):
            if not current:
                headings, pending_headings = pending_headings[-3:], []
            current.append(index)
            seen.update(regular)
            continue
        close()
        pending_headings = []
    close()
    return blocks


def _sub_table(table: NoteTable, indices: list[int]) -> NoteTable:
    # Same table (metadata, cells, fragments), restricted to one block's rows. The derivation is
    # explicit: the block carries detached copies of the parent's proofs marked as a row subset,
    # and original_cell_v1 admits only rows that are members of the block itself.
    def derived(proof):
        return dict(proof, derivation="AXIS_BLOCK_ROW_SUBSET") if proof else proof
    return replace(table, rows=[table.rows[i] for i in indices], bridge=derived(table.bridge),
                   fragment_bridges=[derived(b) for b in table.fragment_bridges])


def evaluate_table_v1(
    table: NoteTable, family: Family, document: DocumentContext, context: list[tuple[str, str]], page_texts: list[str]
) -> list[TableEvaluation]:
    """Evaluate every axis block of a table (usually exactly one)."""

    blocks = axis_blocks_v1(table, family)
    if not blocks or (len(blocks) == 1 and len(blocks[0][1]) == len(table.rows)):
        return [_evaluate_block(table, family, document, context, page_texts)]
    evaluations = []
    for headings, indices in blocks:
        block_context = [("BLOCK_HEADING", text) for text in reversed(headings)] + context
        evaluation = _evaluate_block(_sub_table(table, indices), family, document, block_context, page_texts)
        evaluation.block = {"rows": [table.rows[i].row_id for i in indices], "headings": headings}
        evaluations.append(evaluation)
    return evaluations


def _evaluate_block(
    table: NoteTable, family: Family, document: DocumentContext, context: list[tuple[str, str]], page_texts: list[str]
) -> TableEvaluation:
    evaluation = TableEvaluation(table, "EVALUATED", [], context=context)
    own = " ".join(fold_vietnamese(text) for source, text in context[:3])
    if family.rejects(own):
        evaluation.status, evaluation.reasons = "REJECTED", ["CONTEXT_IS_NOT_A_BALANCE_BREAKDOWN"]
        return evaluation
    roles = assign_roles_v1(table, family)
    members = {r.role for r in roles if r.disposition == "MEMBER" and r.role in family.axis.members}
    titled = any(source in {"BLOCK_HEADING", "TABLE_TITLE", "SECTION_TITLE", "SECTION_NARRATIVE"} and
                 all_phrases(family.raw["retrieval"].get("explicit_title_phrases", []), fold_vietnamese(text))
                 for source, text in context[:3])
    minimum = family.raw["retrieval"].get("min_distinct_members_with_explicit_title", family.min_distinct_members) \
        if titled else family.min_distinct_members
    if len(members) < minimum:
        evaluation.status, evaluation.reasons = "REJECTED", [f"ONLY_{len(members)}_AXIS_MEMBERS"]
        return evaluation
    evaluation.roles = roles
    column_subjects = {s for column in table.columns if column.value_kind == "MONEY"
                       for s in family.subjects_in(fold_vietnamese(column.header_text))}
    matrix = len(column_subjects) >= 2
    if matrix:
        # Columns name the subjects ("Cho vay khách hàng | Chứng khoán | Tiền gửi
        # TCTD | Tổng cộng"): each subject column is its own lane.
        evaluation.subject, evaluation.subject_basis = None, {"basis": "COLUMN_HEADER_SUBJECTS"}
    else:
        evaluation.subject, evaluation.subject_basis = resolve_subject_v1(family, context)
    evaluation.basis = classification_basis_v1(context)
    own = owned_date_texts_v1(table, context)
    declared = family.raw.get("column_measures") or {}
    measures = {m: [fold_vietnamese(a) for a in spec["aliases"]] for m, spec in declared.items() if not spec.get("not_gross_balance")}
    evaluation.lanes = resolve_instant_lanes_v1(table, document, page_texts, own, measures,
                                                family.raw["retrieval"].get("explicit_title_phrases", []))
    for lane in evaluation.lanes:
        # A net / after-provision / interest qualifier printed in the header is a different basis than the gross balance
        # its "dư nợ" alias names; it keeps that meaning and holds, whatever the amounts sum to (Codex 0210).
        header = fold_vietnamese(lane.column.header_text)
        not_gross = sorted(m for m, spec in declared.items() if spec.get("not_gross_balance")
                           and all_phrases([[fold_vietnamese(a)] for a in spec["aliases"]], header))
        if not_gross:
            lane.measure = not_gross[0] if len(not_gross) == 1 else lane.measure
            lane.reasons.append("COLUMN_MEASURE_NOT_GROSS_BALANCE:" + ",".join(not_gross))
    if not matrix:
        # Each explicit column subject is honored on its own (Codex 0210), not only when two or more differ; a column
        # subject contradicting the table's owned context subject holds the table (no first-wins, no amount choice).
        for lane in evaluation.lanes:
            named = family.subjects_in(fold_vietnamese(lane.column.header_text))
            if len(named) == 1:
                lane.subject = named[0]
        named = {lane.subject for lane in evaluation.lanes if lane.subject}
        if named and evaluation.subject is not None and named != {evaluation.subject}:
            for lane in evaluation.lanes:
                lane.reasons.append("SUBJECT_CONFLICT_COLUMN_VS_OWNED_CONTEXT:" + ",".join(sorted(named | {evaluation.subject})))
    if matrix:
        kept = []
        for lane in evaluation.lanes:
            subjects = family.subjects_in(fold_vietnamese(lane.column.header_text))
            if len(subjects) != 1:
                continue  # the "Tổng cộng" column or an unnamed column: not a subject lane
            lane.subject = subjects[0]
            kept.append(lane)
        evaluation.lanes = kept
    if not evaluation.lanes:
        evaluation.status, evaluation.reasons = "REJECTED", ["NO_MONEY_LANES"]
        return evaluation
    roles_by_member = {r.role: r for r in roles if r.role}
    roles_obj = table.separator_roles()
    for lane in evaluation.lanes:
        values: dict[str, Any] = {}
        for role in roles:
            if role.role is None:
                continue
            parsed = parse_cell_v1(table, table.rows[role.row_index], lane.column, roles_obj, document.separator_roles)
            values[role.role] = parsed
        measure_spec = (family.raw.get("column_measures") or {}).get(lane.measure or "", {})
        corroboration = None
        if not measure_spec.get("concept_suffix") and not any(r.startswith("COLUMN_MEASURE_NOT_GROSS_BALANCE") for r in lane.reasons):
            corroboration = _corroborate(family, lane.subject or evaluation.subject, document, lane, values)
        if corroboration:
            evaluation.corroboration.append(corroboration)
        lane_equations = []
        for equation in family.raw.get("equations", []):
            if equation["equals"] not in values:
                continue
            terms = [values[m] for m in equation["sum_of"] if m in values]
            if any(t.state not in {"VALUE", "PRINTED_ZERO", "DASH", "BLANK"} for t in terms + [values[equation["equals"]]]):
                lane_equations.append({"name": equation["name"], "lane": lane.column.column_id, "status": "NOT_EVALUABLE",
                                       "reason": "UNPARSED_CELL"})
                continue
            total = values[equation["equals"]]
            # A dash enters the check as zero; the check then validates (or
            # vetoes) reading it as zero. Blank terms are absent, never zero.
            total_value = Decimal(0) if total.state == "DASH" else total.value
            if total_value is None:
                lane_equations.append({"name": equation["name"], "lane": lane.column.column_id, "status": "NOT_EVALUABLE",
                                       "reason": "TOTAL_NOT_VALUED"})
                continue
            blank = [m for m in equation["sum_of"] if m in values and values[m].state == "BLANK"]
            if blank:
                # A printed row with an unknown (blank) cell leaves the frontier open: the equation proves nothing,
                # in particular not another component's dash as zero (Codex 0209).
                lane_equations.append({"name": equation["name"], "lane": lane.column.column_id,
                                       "status": "INCOMPLETE_BLANK_OPERAND", "blank_terms": blank,
                                       "terms": [m for m in equation["sum_of"] if m in values]})
                continue
            summed = sum((Decimal(0) if t.state == "DASH" else t.value for t in terms if t.state == "DASH" or t.value is not None),
                         Decimal(0))
            residual = total_value - summed
            tolerance = _tolerance(lane.unit, len(terms))
            status = "PASS" if residual == 0 else ("PASS_WITHIN_DECLARED_ROUNDING" if abs(residual) <= tolerance else "FAIL")
            lane_equations.append({"name": equation["name"], "lane": lane.column.column_id, "status": status,
                                   "residual": str(residual), "terms": [m for m in equation["sum_of"] if m in values],
                                   "equals": equation["equals"]})
        evaluation.equations += lane_equations
        _emit_cells(evaluation, family, document, lane, values, lane_equations, roles_by_member)
    return evaluation


def _corroborate(family: Family, subject, document: DocumentContext, lane: NoteLane, values) -> dict[str, Any] | None:
    """Compare a printed note total with the accepted primary line of the same period.

    Corroboration only: it can support or veto the note's arithmetic, never
    supply a unit or a period (Codex 0009). Both units must be printed.
    """

    spec = (family.raw.get("primary_corroboration") or {}).get(subject)
    if not spec or not lane.period_key:
        return None
    primary = document.primary_cells.get((spec["statement"], spec["report_norm_id"], lane.period_key))
    if primary is None:
        return {"lane": lane.column.column_id, "status": "PRIMARY_CELL_ABSENT"}
    primary_value, primary_unit = primary
    if lane.unit not in SCALE or primary_unit not in SCALE:
        return {"lane": lane.column.column_id, "status": "NOT_COMPARABLE_UNIT_NOT_PRINTED"}
    for role in spec["compare_to"]:
        cell = values.get(role)
        if cell is None or cell.value is None or cell.value == 0:
            continue
        base = {"lane": lane.column.column_id, "role": role, "primary_report_norm_id": spec["report_norm_id"],
                "primary_unit": primary_unit, "value": str(cell.value), "primary_value": str(primary_value)}
        if lane.unit == primary_unit and cell.value == primary_value:
            return {**base, "status": "EXACT_EQUAL_TO_PRIMARY"}
        coarse = max(SCALE[lane.unit], SCALE[primary_unit])
        if abs(cell.value * SCALE[lane.unit] - primary_value * SCALE[primary_unit]) < coarse:
            return {**base, "status": "EQUAL_TO_PRIMARY_WITHIN_ONE_UNIT"}
    return {"lane": lane.column.column_id, "status": "DIFFERS_FROM_PRIMARY",
            "primary_value": str(primary_value), "primary_unit": primary_unit}


def _emit_cells(evaluation: TableEvaluation, family: Family, document: DocumentContext, lane: NoteLane,
                values, lane_equations, roles_by_member) -> None:
    table = evaluation.table
    five = next((e for e in lane_equations if e["name"] == family.raw["equations"][0]["name"]), None)
    corroborated = any(c.get("lane") == lane.column.column_id and c.get("status", "").startswith(("EXACT", "EQUAL"))
                       for c in evaluation.corroboration)
    for member, parsed in values.items():
        role = roles_by_member[member]
        reasons = []
        if document.scope is None:
            reasons.append("SCOPE_UNRESOLVED")
        subject = lane.subject or evaluation.subject
        if subject is None:
            reasons.append("SUBJECT_UNRESOLVED:" + evaluation.subject_basis.get("basis", ""))
        reasons += lane.reasons
        failed = [e["name"] for e in lane_equations if e["status"] == "FAIL" and (member in e.get("terms", []) or member in (FIVE_TOTAL, GRAND_TOTAL))]
        reasons += ["VALIDATION_FAIL:" + name for name in failed]
        complete = five is not None and five["status"].startswith("PASS")
        proven = complete or corroborated
        state = parsed.state
        value = parsed.value
        if state == "DASH":
            # Only a complete, passing equation the dash takes part in reads it as zero; a total-only primary
            # agreement corroborates printed amounts but never proves an unresolved component's zero (Codex 0209).
            if any(e["status"].startswith("PASS") and (member in e.get("terms", []) or member == e.get("equals"))
                   for e in lane_equations):
                state, value = "DASH_ZERO", Decimal(0)
            else:
                reasons.append("DASH_WITHOUT_PROOF")
        if state in {"MALFORMED", "AMBIGUOUS_SEPARATOR"}:
            reasons.append("CELL_" + state)
        if not proven and state not in {"BLANK"}:
            reasons.append("NO_EQUATION_OR_PRIMARY_PROOF")
        acceptance = "HOLD" if reasons else ("ACCEPTED_BLANK" if state == "BLANK" else "ACCEPTED")
        row = table.rows[role.row_index]
        suffix = ((family.raw.get("column_measures") or {}).get(lane.measure or "", {}) or {}).get("concept_suffix")
        concept = f"{subject}__{suffix}" if subject and suffix else subject
        evaluation.cells.append({
            "document_ordinal": document.ordinal, "document_plan_id": document.document_plan_id,
            "scope": document.scope, "family": family.name, "concept": concept, "measure": lane.measure,
            "axis": family.axis.name, "member": member, "classification_basis": evaluation.basis,
            "period_key": lane.period_key, "period_basis": lane.period_basis,
            "unit": lane.unit, "unit_basis": lane.unit_basis,
            "observation_state": state, "value": None if value is None else format(value, "f"), "raw": parsed.raw,
            "acceptance": acceptance, "hold_reasons": reasons,
            "locator": {**table.locator(), "row_id": row.row_id, "row_order": row.order, "column_id": lane.column.column_id},
            "label_exact": row.label, "header_text": lane.column.header_text,
        })
