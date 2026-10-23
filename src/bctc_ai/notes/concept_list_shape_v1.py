"""CONCEPT_LIST shape: each row is one line of a closed line axis, each money column one printed duration.

Used for reconciliation/breakdown notes with duration lanes (income tax,
operating expense, credit-risk provision expense). Prototype/development
status: results are NOTES_PILOT_EXPERIMENTAL, never acceptance by themselves.

The shape never chooses between competing readings:

* a row matching two lines, or a line printed twice (whatever the values),
  is held; a parent-scoped rule ("Chi khác" under "Chi phí cho nhân viên")
  applies only under a printed parent (parent_row_id or hierarchy path);
* a lane's period comes from printed evidence only (kernel
  ``resolve_duration_lanes_v1``); a header leaving "quarter or year-to-date"
  open keeps both candidates and the lane is held — the income statement
  never selects a period (DECISIONS #5); per-candidate comparisons are kept
  as diagnostics only;
* a lane is accepted only when proven: a note equation with a fixed,
  declared structure passes, or a line equals the same-period line of the
  report's income statement exactly in the same printed unit. A differing
  income-statement line vetoes the lane; a failing equation holds the lines
  it involves;
* deductions in an equation follow the line's declared role and the printed
  sign (printed negative: added as printed; printed positive: subtracted) —
  never "whichever variant passes"; values are stored as printed;
* a printed dash stays a DASH observation with no value (no zero policy).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from bctc_ai.notes.config_v1 import Family, all_phrases
from bctc_ai.notes.kernel_v1 import (
    DocumentContext,
    NoteLane,
    NoteTable,
    parse_cell_v1,
    resolve_duration_lanes_v1,
)
from bctc_ai.notes.list_shape_v1 import (
    OWNER_SOURCES,
    RowRole,
    TableEvaluation,
    _has_values,
    _tolerance,
    owned_date_texts_v1,
    resolve_subject_v1,
)
from bctc_ai.primary_statements.text_v1 import fold_vietnamese, label_key_v1
from bctc_ai.primary_statements.units_v1 import SCALE

NUMERIC = {"VALUE", "PRINTED_ZERO"}


def _printed_parent_key(table: NoteTable, index: int) -> str | None:
    """The label key of the row's printed parent (parent_row_id, else hierarchy path), never a position."""

    row = table.rows[index]
    if row.parent_row_id:
        parent = next((r for r in table.rows if r.row_id == row.parent_row_id), None)
        if parent is not None and parent.label:
            return parent.key
    path = [part for part in row.hierarchy if part]
    if path and path[-1] == row.label:
        path = path[:-1]
    return label_key_v1(path[-1]).key if path else None


def _scoped_match(spec: dict[str, Any], key: str) -> bool:
    scoped = spec.get("scoped") or {}
    exact = [fold_vietnamese(str(a)) for a in scoped.get("exact", [])]
    groups = [[fold_vietnamese(str(p)) for p in g] for g in scoped.get("all_of", [])]
    return key in exact or all_phrases(groups, key)


def assign_lines_v1(table: NoteTable, family: Family) -> list[RowRole]:
    """One line per valued row, or an explicit reason why not.

    A member's ``scoped`` rule (bare "Chi khác", "Dự phòng chung") matches
    only under a printed parent of one of ``scoped.within``; without a printed
    parent it never matches. ``not_within`` excludes a member under those parents.
    """

    members = family.axis.members
    roles = []
    for index, row in enumerate(table.rows):
        key = row.key
        if not _has_values(table, row):
            roles.append(RowRole(index, None, "HEADING", "NO_VALUES"))
            continue
        matches = family.axis.match(key) if key else []
        scoped = [m for m, spec in members.items() if spec.get("scoped") and key and _scoped_match(spec, key)]
        if scoped or any(members.get(m, {}).get("not_within") for m in matches):
            parent_key = _printed_parent_key(table, index)
            parents = family.axis.match(parent_key) if parent_key else []
            parent_line = parents[0] if len(parents) == 1 else None
            matches = [m for m in matches if not (parent_line and parent_line in members.get(m, {}).get("not_within", []))]
            matches += [m for m in scoped if parent_line in members[m]["scoped"]["within"] and m not in matches]
        if len(matches) > 1:
            roles.append(RowRole(index, None, "AMBIGUOUS", "ROW_MATCHES_SEVERAL_LINES", matches))
        elif matches:
            roles.append(RowRole(index, matches[0], "MEMBER", "LINE_RULE"))
        else:
            roles.append(RowRole(index, None, "SOURCE_ONLY", "NO_LINE_RULE"))
    printed: dict[str, list[RowRole]] = {}
    for role in roles:
        if role.role:
            printed.setdefault(role.role, []).append(role)
    for line, repeats in printed.items():
        if len(repeats) > 1:
            # Same label twice may be another population or basis: never merged, never chosen.
            for repeat in repeats:
                repeat.disposition, repeat.reason, repeat.candidates, repeat.role = "AMBIGUOUS", "LINE_PRINTED_MORE_THAN_ONCE", [line], None
    return roles


def _number(parsed) -> Decimal | None:
    if parsed is None or parsed.state not in NUMERIC:
        return None
    return parsed.value


def _first_present(groups: list[list[str]], values: dict[str, Any]) -> list[str] | None:
    """The first declared group whose lines are all printed (a printed total before its components)."""

    for group in groups:
        if all(line in values for line in group):
            return group
    return None


def evaluate_equations_v1(family: Family, values: dict[str, Any], unit: str | None, lane_id: str,
                          line_rows: dict[str, int] | None = None, unmatched_rows: list[int] | None = None) -> list[dict[str, Any]]:
    """Note arithmetic with a fixed structure per family (see ``equations``); proof or hold, never membership.

    An equation whose printed span (first to last involved row) contains a
    valued row that no line rule reads is INCOMPLETE: no proof and no hold.
    """

    results = []
    for equation in family.raw.get("equations", []):
        if equation["equals"] not in values:
            continue
        plus = list(equation.get("plus", []))
        if any(line not in values for line in plus):
            continue
        plus += _first_present(equation.get("plus_first_present", []), values) or []
        minus = _first_present(equation.get("minus_first_present", []), values) or []
        plus += [line for line in equation.get("plus_present", []) if line in values]
        terms = plus + minus
        if not terms or (equation.get("plus_present") and len(terms) < 2):
            continue
        record = {"name": equation["name"], "lane": lane_id, "equals": equation["equals"], "terms": terms}
        if line_rows:
            span = [line_rows[line] for line in [equation["equals"], *terms] if line in line_rows]
            inside = [i for i in unmatched_rows or [] if min(span) < i < max(span)]
            if inside:
                results.append({**record, "status": "INCOMPLETE_UNREAD_ROWS_IN_SPAN", "rows": inside})
                continue
        involved = [values[line] for line in [equation["equals"], *terms]]
        if any(p.state not in NUMERIC for p in involved):
            # A blank, dash or unparsed cell never completes an equation.
            results.append({**record, "status": "NOT_EVALUABLE", "reason": "BLANK_DASH_OR_UNPARSED_CELL"})
            continue
        target = _number(values[equation["equals"]])
        total = sum((_number(values[line]) for line in plus), Decimal(0))
        for line in minus:
            amount = _number(values[line])
            if amount is not None:
                # Declared deduction: printed negative is already signed, printed positive is subtracted.
                total += amount if amount < 0 else -amount
        residual = target - total
        status = "PASS" if residual == 0 else ("PASS_WITHIN_DECLARED_ROUNDING" if abs(residual) <= _tolerance(unit, len(terms)) else "FAIL")
        results.append({**record, "status": status, "residual": str(residual)})
    return results


def anchor_checks_v1(family: Family, document: DocumentContext, values: dict[str, Any], unit: str | None,
                     period_key: str) -> list[dict[str, Any]]:
    """Same-period income-statement lines: exact equality in the same printed unit supports, a difference vetoes."""

    checks = []
    for line, spec in (family.raw.get("primary_anchors") or {}).items():
        note = _number(values.get(line))
        if note is None:
            continue
        primary = document.primary_value_for_period(spec["statement"], spec["report_norm_id"], period_key)
        base = {"line": line, "period_key": period_key, "primary_report_norm_id": spec["report_norm_id"], "value": str(note)}
        if primary is None:
            checks.append({**base, "status": "PRIMARY_ABSENT"})
            continue
        primary_value, primary_unit = primary
        base.update(primary_value=str(primary_value), primary_unit=primary_unit)
        if unit not in SCALE or unit != primary_unit:
            checks.append({**base, "status": "NOT_COMPARED_DIFFERENT_OR_UNKNOWN_UNIT"})
        elif note == 0 and primary_value == 0:
            checks.append({**base, "status": "BOTH_ZERO_NO_PROOF"})
        elif note == primary_value:
            checks.append({**base, "status": "EXACT"})
        elif note == -primary_value:
            checks.append({**base, "status": "OPPOSITE_SIGN_NO_PROOF"})
        else:
            checks.append({**base, "status": "DIFFERS"})
    return checks


def evaluate_concept_table_v1(
    table: NoteTable, family: Family, document: DocumentContext, context: list[tuple[str, str]], page_texts: list[str],
) -> list[TableEvaluation]:
    evaluation = TableEvaluation(table, "EVALUATED", [], context=context)
    retrieval = family.raw["retrieval"]
    pages = {f["page_json_version_id"] for f in (table.fragments or [table.locator()])}
    if pages & document.statement_pages:
        evaluation.status, evaluation.reasons = "REJECTED", ["PRIMARY_STATEMENT_PAGE"]
        return [evaluation]
    if document.notes_start_page and table.physical_page < document.notes_start_page:
        evaluation.status, evaluation.reasons = "REJECTED", ["BEFORE_NOTES_START_PAGE"]
        return [evaluation]
    owner = " ".join(fold_vietnamese(text) for source, text in context[:3] if source in OWNER_SOURCES)
    if family.rejects(owner):
        evaluation.status, evaluation.reasons = "REJECTED", ["OWNER_CONTEXT_IS_ANOTHER_NOTE"]
        return [evaluation]
    roles = assign_lines_v1(table, family)
    evaluation.roles = roles
    members = {r.role for r in roles if r.disposition == "MEMBER"}
    evaluation.subject, evaluation.subject_basis = resolve_subject_v1(family, context)
    anchors = members & set(retrieval["anchor_lines"])
    if evaluation.subject is None and len(anchors) < int(retrieval["min_anchor_lines_without_title"]):
        evaluation.status, evaluation.reasons = "REJECTED", [f"NO_TITLE_AND_ONLY_{len(anchors)}_ANCHOR_LINES"]
        return [evaluation]
    emitted = members & set(family.raw["emit_lines"])
    if len(emitted) < int(retrieval["min_emitted_lines"]):
        evaluation.status, evaluation.reasons = "REJECTED", [f"ONLY_{len(emitted)}_LINES"]
        return [evaluation]
    evaluation.lanes = resolve_duration_lanes_v1(table, document, page_texts, owned_date_texts_v1(table, context))
    if not evaluation.lanes:
        evaluation.status, evaluation.reasons = "REJECTED", ["NO_MONEY_LANES"]
        return [evaluation]
    separators = table.separator_roles()
    for lane in evaluation.lanes:
        values = {role.role: parse_cell_v1(table, table.rows[role.row_index], lane.column, separators, document.separator_roles)
                  for role in roles if role.disposition == "MEMBER"}
        line_rows = {role.role: role.row_index for role in roles if role.disposition == "MEMBER"}
        unmatched = [role.row_index for role in roles if role.disposition in {"SOURCE_ONLY", "AMBIGUOUS"}
                     and table.cells.get((table.rows[role.row_index].row_id, lane.column.column_id), (None, "BLANK"))[1] != "BLANK"]
        equations = evaluate_equations_v1(family, values, lane.unit, lane.column.column_id, line_rows, unmatched)
        evaluation.equations += equations
        checks = anchor_checks_v1(family, document, values, lane.unit, lane.period_key) if lane.period_key else []
        evaluation.corroboration += [{**c, "lane": lane.column.column_id} for c in checks]
        for candidate in lane.candidates:
            # Diagnostic only: shows what the income statement would say; it never selects the period.
            evaluation.corroboration += [{**c, "lane": lane.column.column_id, "diagnostic_only": True}
                                         for c in anchor_checks_v1(family, document, values, lane.unit, candidate)]
        proven = any(c["status"] == "EXACT" for c in checks) or any(e["status"].startswith("PASS") for e in equations)
        vetoed = any(c["status"] == "DIFFERS" for c in checks)
        failed = {line for e in equations if e["status"] == "FAIL" for line in [e["equals"], *e["terms"]]}
        # Lines of an equation with unread rows in its span: population closure is not proven, so no
        # other proof (an income-statement anchor) may accept them.
        open_lines = {line for e in equations if e["status"] == "INCOMPLETE_UNREAD_ROWS_IN_SPAN" for line in [e["equals"], *e["terms"]]}
        _emit(evaluation, family, document, lane, values, roles, proven=proven, vetoed=vetoed, failed=failed, open_lines=open_lines)
    return [evaluation]


def _emit(evaluation: TableEvaluation, family: Family, document: DocumentContext, lane: NoteLane, values, roles,
          *, proven: bool, vetoed: bool, failed: set[str], open_lines: set[str]) -> None:
    table = evaluation.table
    emit = set(family.raw["emit_lines"])
    for role in roles:
        if role.disposition != "MEMBER" or role.role not in emit:
            continue
        parsed = values[role.role]
        reasons = []
        if document.scope is None:
            reasons.append("SCOPE_UNRESOLVED")
        reasons += lane.reasons
        if vetoed:
            reasons.append("PRIMARY_LINE_DIFFERS_FOR_PERIOD")
        if role.role in failed:
            reasons.append("VALIDATION_FAIL")
        if role.role in open_lines:
            reasons.append("EQUATION_SPAN_HAS_UNREAD_ROWS")
        if parsed.state in {"MALFORMED", "AMBIGUOUS_SEPARATOR"}:
            reasons.append("CELL_" + parsed.state)
        if not proven and parsed.state != "BLANK":
            reasons.append("NO_EQUATION_OR_PRIMARY_PROOF")
        if reasons:
            acceptance = "HOLD"
        elif parsed.state == "BLANK":
            acceptance = "ACCEPTED_BLANK"
        elif parsed.state == "DASH":
            acceptance = "ACCEPTED_DASH"
        else:
            acceptance = "ACCEPTED"
        row = table.rows[role.row_index]
        evaluation.cells.append({
            "document_ordinal": document.ordinal, "document_plan_id": document.document_plan_id,
            "scope": document.scope, "family": family.name, "concept": family.raw["concept"], "measure": None,
            "axis": family.axis.name, "member": role.role, "classification_basis": "AS_PRESENTED",
            "period_key": lane.period_key, "period_basis": lane.period_basis, "period_candidates": list(lane.candidates),
            "unit": lane.unit, "unit_basis": lane.unit_basis,
            "observation_state": parsed.state, "value": None if parsed.value is None or parsed.state == "DASH" else format(parsed.value, "f"),
            "raw": parsed.raw, "acceptance": acceptance, "hold_reasons": reasons, "product_status": "PROTOTYPE_NOT_ACCEPTANCE",
            "locator": {**table.locator(), "row_id": row.row_id, "row_order": row.order, "column_id": lane.column.column_id},
            "label_exact": row.label, "header_text": lane.column.header_text,
        })
