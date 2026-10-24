"""CONCEPT_LIST shape: each row is one line of a closed line axis, each money column one printed duration.

Used for reconciliation/breakdown notes with duration lanes (income tax,
operating expense, credit-risk provision expense). Prototype/development
status: results are NOTES_PILOT_EXPERIMENTAL, never acceptance by themselves.

The shape never chooses between competing readings:

* a row matching two lines, or a line printed twice (whatever the values),
  is held; a parent-scoped rule ("Chi khác" under "Chi phí cho nhân viên")
  applies only under a proven printed parent (parent_row_id re-proven by the
  raw hierarchy paths, printed before the row; no hierarchy-component fallback);
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

import re
from decimal import Decimal
from typing import Any

from bctc_ai.notes.config_v1 import Family, all_phrases, phrase_in
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
from bctc_ai.notes.source_bridge_v1 import EXACT
from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.primary_statements.units_v1 import SCALE

NUMERIC = {"VALUE", "PRINTED_ZERO"}


def proven_parent_index_v1(table: NoteTable, index: int) -> tuple[int | None, str]:
    """The row's printed parent, proven, else (None, reason).

    ``parent_row_id`` must name a unique row of this table printed BEFORE the row, and the raw
    hierarchy paths must agree: the child's path minus its own label equals the parent's path, which
    ends in the parent's printed label. No fallback to a hierarchy component, a position or an amount.

    Known, deliberate coverage gap (Codex 0127): an owner reached only through an intermediate wrapper
    (e.g. an all-NULL GROUP "Trong đó" row between the employee line and payroll) is not the immediate
    parent and is held. A later transparent-wrapper rule must use the recorded source proof of that
    wrapper; never a numeric or PRIMARY-equality owner grant.
    """

    ids = [row.row_id for row in table.rows]
    if len(set(ids)) != len(ids):
        return None, "DUPLICATE_ROW_IDS"
    row = table.rows[index]
    if not row.parent_row_id:
        return None, "NO_PRINTED_PARENT"
    if row.parent_row_id == row.row_id:
        return None, "SELF_PARENT"
    if row.parent_row_id not in ids:
        return None, "PARENT_NOT_IN_TABLE"
    parent_index = ids.index(row.parent_row_id)
    if parent_index >= index:
        return None, "PARENT_PRINTED_AFTER_CHILD"
    parent = table.rows[parent_index]
    child_path, parent_path = list(row.hierarchy), list(parent.hierarchy)
    if (len(child_path) < 2 or child_path[-1] != row.label or child_path[:-1] != parent_path
            or not parent_path or parent_path[-1] != parent.label):
        return None, "RAW_HIERARCHY_PATH_DOES_NOT_PROVE_PARENT"
    return parent_index, "PROVEN_PRINTED_PARENT"


def _proven_parent_line(table: NoteTable, index: int, family: Family) -> tuple[str | None, str, int | None]:
    """(line, reason, parent index) of the row's proven printed parent; line None unless it is one axis line.

    This is the parent's label match only; ``assign_lines_v1`` additionally requires the parent's FINAL
    role to be an unambiguous MEMBER of that line (after duplicate-line resolution).
    """

    parent_index, reason = proven_parent_index_v1(table, index)
    if parent_index is None:
        return None, reason, None
    parent = table.rows[parent_index]
    veto = family.row_veto(parent.key) if parent.key else None
    if veto:
        return None, "PARENT_ROW_VETO:" + veto, parent_index
    lines = family.axis.match(parent.key) if parent.key else []
    if len(lines) != 1:
        return None, "PARENT_LINE_AMBIGUOUS" if lines else "PARENT_IS_NOT_A_LINE", parent_index
    return lines[0], "PROVEN_PARENT_LINE", parent_index


WRAPPER_SOURCE_DOMAIN = "ORIGINAL_EXACT_UNSHIFTED_SINGLE_TABLE"


def _original_axis_domain(table: NoteTable) -> str | None:
    """WRAPPER_SOURCE_DOMAIN when the SQL columns ARE the complete ORIGINAL column axis, else None (Codex 0155).

    Only a single (not continuation-merged) table whose source bridge is EXACT with the identity column map
    over every SQL column: then a SQL row's cells are every ORIGINAL value cell of that row. A proven TEXT
    shift (EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT) removed an original cell, so "all SQL cells null" would not
    prove "every original cell null"; merged and shifted domains stay outside this rule (HOLD).
    """

    bridge = table.bridge or {}
    if table.fragments or bridge.get("status") != EXACT:
        return None
    columns = sorted(table.columns, key=lambda column: column.ordinal)
    column_map = bridge.get("column_map") or {}
    if set(column_map) != {column.column_id for column in columns} or any(
            column_map[column.column_id] != position for position, column in enumerate(columns, 1)):
        return None
    return WRAPPER_SOURCE_DOMAIN


def _owner_through_wrapper(table: NoteTable, wrapper_index: int, family: Family) -> tuple[str, int] | None:
    """(owner line, owner row) when ``wrapper_index`` is ONE source-proven transparent wrapper, else None.

    Family opt-in only (``transparent_wrappers``). The wrapper is a GROUP row whose folded label is exactly one
    declared literal (an optional trailing colon aside); EVERY original value cell of it is JSON null (no DASH,
    no blank string, no number); and its own parent edge is proven (``proven_parent_index_v1``: unique, printed
    earlier, raw paths agree) to a row matching exactly one axis line. One level only: a wrapper's parent that is
    itself a wrapper matches no line, so nesting never resolves. The wrapper is never a value or a zero; the
    owner row's FINAL role must still be an unambiguous MEMBER (fixed point in ``assign_lines_v1``).
    """

    spec = family.raw.get("transparent_wrappers") or {}
    literals = {fold_vietnamese(str(text)).strip() for text in spec.get("labels") or []}
    wrapper = table.rows[wrapper_index]
    label = fold_vietnamese(wrapper.label or "").strip()
    label = label[:-1].rstrip() if label.endswith(":") else label
    if not literals or wrapper.kind != "GROUP" or label not in literals:
        return None
    if _original_axis_domain(table) is None:
        return None
    cells = [table.cells.get((wrapper.row_id, column.column_id)) for column in table.columns]
    if not cells or any(cell is None or cell[0] is not None for cell in cells):
        return None
    owner_line, _reason, owner_index = _proven_parent_line(table, wrapper_index, family)
    return (owner_line, owner_index) if owner_line is not None and owner_index is not None else None


def _claims_parent(row) -> bool:
    return bool(row.parent_row_id) or len([part for part in row.hierarchy if part]) > 1


def _scoped_match(spec: dict[str, Any], key: str) -> bool:
    scoped = spec.get("scoped") or {}
    exact = [fold_vietnamese(str(a)) for a in scoped.get("exact", [])]
    groups = [[fold_vietnamese(str(p)) for p in g] for g in scoped.get("all_of", [])]
    return key in exact or all_phrases(groups, key)


def assign_lines_v1(table: NoteTable, family: Family, *, owned_subject: bool = False) -> list[RowRole]:
    """One line per valued row, or an explicit reason why not.

    A member's ``scoped`` rule (bare "Chi khác", "Dự phòng chung") matches
    only under a PROVEN printed parent (``proven_parent_index_v1``) of one of
    ``scoped.within``; without one it never matches. ``owner`` binds a line to
    its proven printed owner (e.g. payroll contributions under the employee
    expense line); ``not_within`` excludes a member under those parents and
    also when the row claims a parent that cannot be proven.
    """

    members = family.axis.members
    roles = []
    depends: dict[int, tuple[int, str]] = {}  # child row -> (parent row, parent line) its reading relies on
    for index, row in enumerate(table.rows):
        key = row.key
        if not _has_values(table, row):
            roles.append(RowRole(index, None, "HEADING", "NO_VALUES"))
            continue
        veto = family.row_veto(key) if key else None
        if veto:
            # A printed stock/movement basis or a foreign population is never one of the family's lines, before any
            # role, owner or equation participates; arithmetic cannot grant it (Codex 0199). Kept as source only.
            roles.append(RowRole(index, None, "SOURCE_ONLY", "ROW_VETO:" + veto, family.axis.match(key)))
            continue
        matches = family.axis.match(key) if key else []
        direct = list(matches)  # competing DIRECT axis matches, before any owner/not_within filtering
        scoped = [m for m, spec in members.items() if spec.get("scoped") and key and _scoped_match(spec, key)]
        owned = [m for m in matches if members.get(m, {}).get("owner")]
        blocked: list[str] = []
        parent_index, by_parent = None, set()  # by_parent: members read only because of the proven parent
        owner_index, via_wrapper = None, None
        if scoped or owned or any(members.get(m, {}).get("not_within") for m in matches):
            parent_line, parent_reason, parent_index = _proven_parent_line(table, index, family)
            owner_line, owner_index = parent_line, parent_index
            if owned and parent_line is None and parent_index is not None:
                # F36 opt-in (Codex 0150): an owner reached through ONE source-proven transparent wrapper row.
                # Only the owner rule may look through it; scoped / not_within keep the immediate parent.
                through = _owner_through_wrapper(table, parent_index, family)
                if through is not None:
                    owner_line, owner_index, via_wrapper = through[0], through[1], parent_index
            excluded = [m for m in matches if members.get(m, {}).get("not_within")
                        and (parent_line in members[m]["not_within"] or (parent_line is None and _claims_parent(row)))]
            # An owner-bound line is read only under its proven printed owner (never by amount or position).
            blocked = [m for m in owned if owner_line not in members[m]["owner"]] + excluded
            matches = [m for m in matches if m not in blocked]
            # Only an explicit owner, or a member ADDED by the proven scoped fallback, depends on the parent;
            # a fully qualified direct label (e.g. "Dự phòng chung cho vay khách hàng") reads on its own.
            by_owner = {m for m in owned if m in matches}
            added = [m for m in scoped if parent_line in members[m]["scoped"]["within"] and m not in matches]
            matches += added
            by_parent = set(added)
            if not by_owner:
                via_wrapper = None
            if blocked and len(direct) > 1:
                # A label matching several lines DIRECTLY stays ambiguous: a missing owner (or not_within) is not
                # evidence selecting the remaining direct meaning (Codex 0151/0152: payroll + uniform composite).
                # Scoped phrases are not counted here; they still need their own proven parent.
                roles.append(RowRole(index, None, "AMBIGUOUS", "ROW_MATCHES_SEVERAL_LINES", direct))
                continue
            if blocked and not matches:
                why = parent_reason if owner_line is None else "PARENT_LINE_" + owner_line
                roles.append(RowRole(index, None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:" + why, blocked))
                continue
        else:
            by_owner = set()
        if len(matches) > 1:
            roles.append(RowRole(index, None, "AMBIGUOUS", "ROW_MATCHES_SEVERAL_LINES", matches))
        elif matches and not owned_subject and members.get(matches[0], {}).get("needs_owned_subject_unless") is not None \
                and not all_phrases(members[matches[0]]["needs_owned_subject_unless"], key):
            # A bare generic line ("Dự phòng khác") names no population of its own: it is read only under the family's
            # subject printed in the table's OWN context (Codex 0203), never from arithmetic or a preceding heading.
            roles.append(RowRole(index, None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:NO_OWNED_FLOW_SUBJECT", matches))
        elif matches:
            # The wrapper is recorded as the source proof of the owner edge, never as a value.
            reason = "LINE_RULE" if via_wrapper is None else (
                f"LINE_RULE_VIA_TRANSPARENT_WRAPPER:{table.rows[via_wrapper].row_id}:{WRAPPER_SOURCE_DOMAIN}")
            roles.append(RowRole(index, matches[0], "MEMBER", reason))
            if matches[0] in by_owner and owner_index is not None:
                depends[index] = (owner_index, owner_line)
                roles[-1].depends_on = owner_index
            elif matches[0] in by_parent and parent_index is not None:
                depends[index] = (parent_index, parent_line)
                roles[-1].depends_on = parent_index
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
    # An owner/scoped child is read only while its parent's FINAL role is an unambiguous MEMBER of the
    # owner line (Codex 0128): a parent made AMBIGUOUS by a duplicate population releases the child too.
    changed = True
    while changed:
        changed = False
        for child, (parent_index, parent_line) in depends.items():
            child_role, parent_role = roles[child], roles[parent_index]
            if child_role.disposition == "MEMBER" and (parent_role.disposition != "MEMBER" or parent_role.role != parent_line):
                child_role.disposition, child_role.reason = "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER"
                child_role.candidates, child_role.role = [child_role.role], None
                changed = True
    index, reason = unlabeled_total_row_v1(table, family, roles, owned_subject=owned_subject)
    if index is not None:
        roles[index] = RowRole(index, family.raw["unlabeled_total_line"], "MEMBER", reason)
    return roles


def unlabeled_total_row_v1(table: NoteTable, family: Family, roles: list[RowRole], *,
                           owned_subject: bool) -> tuple[int | None, str]:
    """(row index, reason) of the table's printed UNLABELED total, else (None, why not) (Codex 0292/0296, proposal T).

    Family opt-in only (``unlabeled_total_line``; OPERATING_EXPENSE). The identity comes from ORIGINAL source
    structure, never from an amount, a position alone or an equation:
    - the table's subject is printed in its OWN context;
    - exactly one row of the table has ORIGINAL ``row_kind`` TOTAL (SUBTOTAL may close a partial block: never);
    - that row prints no label (a JSON null and an empty string are kept apart in the reason) and has values;
    - it claims no parent: no ``parent_row_id`` and no printed hierarchy component;
    - it is the last valued row, so every top-level line is printed before it;
    - it was left SOURCE_ONLY / NO_LINE_RULE, and no row is or could be the printed total line already.
    The family's equations then validate it like any printed total (PASS proves, FAIL / INCOMPLETE hold); they
    never decide membership.
    """

    line = family.raw.get("unlabeled_total_line")
    if not line:
        return None, "NOT_OPTED_IN"
    if not owned_subject:
        return None, "SUBJECT_NOT_IN_OWN_CONTEXT"
    totals = [i for i, row in enumerate(table.rows) if row.kind == "TOTAL"]
    if len(totals) != 1:
        return None, f"TOTAL_KIND_ROWS_{len(totals)}_NOT_ONE"
    index = totals[0]
    row = table.rows[index]
    if row.label is not None and row.label.strip():
        return None, "TOTAL_ROW_PRINTS_A_LABEL"
    if not _has_values(table, row):
        return None, "TOTAL_ROW_HAS_NO_VALUES"
    hierarchy = row.hierarchy_raw if row.hierarchy_raw is not None else row.hierarchy
    if row.parent_row_id or any(isinstance(part, str) and part.strip() for part in hierarchy or ()):
        return None, "TOTAL_ROW_CLAIMS_A_PARENT"
    if any(_has_values(table, later) for later in table.rows[index + 1:]):
        return None, "TOTAL_ROW_NOT_THE_LAST_VALUED_ROW"
    if (roles[index].disposition, roles[index].reason) != ("SOURCE_ONLY", "NO_LINE_RULE"):
        return None, "TOTAL_ROW_ALREADY_DISPOSED:" + roles[index].reason
    if any(role.role == line or line in (role.candidates or []) for role in roles):
        return None, "PRINTED_TOTAL_LINE_ALREADY_PRESENT"
    # Codex 0302/0304: the equation's unread-row span starts at its first recognized term, and recognition alone does
    # not place a row in the root population. The unlabeled total is admitted only when EVERY valued pre-total row is
    # a source top-level root-frontier term, or proven detail of one; a root-term label printed nested is refused.
    terms = root_terms_v1(family, line)
    for earlier, other in enumerate(table.rows[:index]):
        if not _has_values(table, other):
            continue
        if roles[earlier].disposition == "MEMBER" and roles[earlier].role in terms and not _source_top_level_v1(other):
            return None, "ROOT_TERM_NOT_AT_SOURCE_TOP_LEVEL:" + other.row_id
        if _root_frontier_owner_v1(table, family, roles, earlier, terms) is None:
            return None, "UNACCOUNTED_VALUED_ROW_BEFORE_TOTAL:" + other.row_id
    return index, "UNLABELED_ORIGINAL_ROW_KIND_TOTAL:" + ("NULL_LABEL" if row.label is None else "EMPTY_LABEL")


T_ROUTE_REASON = "UNLABELED_ORIGINAL_ROW_KIND_TOTAL:"


def root_terms_v1(family: Family, line: str) -> set[str]:
    """The terms of the family equation(s) whose target is ``line``: the configured root frontier (Codex 0304)."""

    return {term for equation in family.raw.get("equations") or [] if equation.get("equals") == line
            for term in _equation_terms(equation)}


def _source_top_level_v1(row) -> bool:
    """No printed parent: no ``parent_row_id`` and no printed hierarchy component other than the row's own label."""

    hierarchy = row.hierarchy_raw if row.hierarchy_raw is not None else row.hierarchy
    parts = [part for part in hierarchy or () if isinstance(part, str) and part.strip()]
    return not row.parent_row_id and parts in ([], [row.label])


def _root_frontier_owner_v1(table: NoteTable, family: Family, roles: list[RowRole], index: int,
                            terms: set[str]) -> int | None:
    """Row index of the ROOT-FRONTIER term whose printed population contains valued row ``index``, else None.

    Codex 0302/0304. The frontier is a MEMBER of one of the root equation's ``terms`` printed at SOURCE top level
    (``_source_top_level_v1``); it accounts for itself. Any other valued row - a non-root MEMBER (a flat "Khấu hao"
    row is recognized, but not in the root population) or a SOURCE_ONLY row (never a ROW_VETO foreign row, never
    AMBIGUOUS) - is accounted for only as detail of a frontier row by proven printed edges: its immediate proven parent
    (``proven_parent_index_v1``) is a frontier row, or that parent is ONE source-proven transparent wrapper
    (``_owner_through_wrapper``: family literal, GROUP, every ORIGINAL value cell null, EXACT single-table domain, its
    own proven parent edge) whose owner row is a frontier row of exactly that line. No longer chains. Detail is inside
    its owner's amount: accounted for once, never a component of the total.
    """

    def frontier(i: int) -> bool:
        return roles[i].disposition == "MEMBER" and roles[i].role in terms and _source_top_level_v1(table.rows[i])

    role = roles[index]
    if frontier(index):
        return index
    if role.disposition not in {"MEMBER", "SOURCE_ONLY"} or role.reason.startswith("ROW_VETO:") or role.role in terms:
        return None
    parent_index, _reason = proven_parent_index_v1(table, index)
    if parent_index is None:
        return None
    if frontier(parent_index):
        return parent_index
    through = _owner_through_wrapper(table, parent_index, family)
    if through is not None and roles[through[1]].role == through[0] and frontier(through[1]):
        return through[1]
    return None


def detail_parent_line_v1(table: NoteTable, roles: list[RowRole], index: int) -> tuple[str | None, str]:
    """The read line an unread row is printed detail of, or (None, reason).

    Finite policy: only the IMMEDIATE parent (no walk through intermediate
    rows); row ids unique in the table; no self-parent; the parent row exists
    and is a MEMBER (never AMBIGUOUS/SOURCE_ONLY/HEADING); and the link is
    re-proven from the raw ``hierarchy_path_exact`` fields: the child's path
    minus its own last element equals the parent's path, whose last element is
    the parent's printed label. ``parent_row_id`` alone (an ETL-derived link)
    is not accepted as proof.
    """

    ids = [row.row_id for row in table.rows]
    if len(set(ids)) != len(ids):
        return None, "DUPLICATE_ROW_IDS"
    row = table.rows[index]
    if not row.parent_row_id:
        return None, "NO_PRINTED_PARENT"
    if row.parent_row_id == row.row_id:
        return None, "SELF_PARENT"
    if row.parent_row_id not in ids:
        return None, "PARENT_NOT_IN_TABLE"
    parent_index = ids.index(row.parent_row_id)
    parent = table.rows[parent_index]
    role = next((r for r in roles if r.row_index == parent_index), None)
    if role is None or role.disposition != "MEMBER":
        return None, "PARENT_NOT_A_READ_LINE"
    child_path, parent_path = list(row.hierarchy), list(parent.hierarchy)
    if (len(child_path) < 2 or child_path[-1] != row.label or child_path[:-1] != parent_path
            or not parent_path or parent_path[-1] != parent.label):
        return None, "RAW_HIERARCHY_PATH_DOES_NOT_PROVE_PARENT"
    return role.role, "PRINTED_DETAIL_OF_READ_LINE"


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
                          line_rows: dict[str, int] | None = None,
                          unread_rows: list[tuple[int, str | None]] | None = None) -> list[dict[str, Any]]:
    """Note arithmetic with a fixed structure per family (see ``equations``); proof or hold, never membership.

    An equation whose printed span (first to last involved row) contains a
    valued unread row is INCOMPLETE: no proof and no hold - unless that row is
    proven printed detail (``detail_parent_line_v1``) of a line that is itself
    this equation's target or one of its terms; excused rows are recorded.
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
            lines = {equation["equals"], *terms}
            span = [line_rows[line] for line in lines if line in line_rows]
            inside = [(i, parent) for i, parent in unread_rows or [] if min(span) < i < max(span)]
            excused = [i for i, parent in inside if parent in lines]
            blocking = [i for i, parent in inside if parent not in lines]
            if excused:
                record["excused_detail_rows"] = excused
            if blocking:
                results.append({**record, "status": "INCOMPLETE_UNREAD_ROWS_IN_SPAN", "rows": blocking})
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


_POSITION_MEASURE = ("gia tri dau tu", "menh gia", "gia tri ghi so", "so du")
_SCHEDULE_TEXT = ("ngay dao han", "ky han", "lai suat")
_FLOW_PERIOD = re.compile(r"\b(?:nam|quy|ky|giai doan|luy ke|thang)\b")


def position_schedule_reason_v1(table: NoteTable) -> str | None:
    """REJECT reason when the table ITSELF is a position schedule, not a flow breakdown (Codex 0233/0234 E1).

    All three own-table conditions, over every MONEY header: (a) some MONEY header names a position measure (giá trị
    đầu tư, mệnh giá, giá trị ghi sổ, số dư); (b) the table has its own schedule column (COUNT, PERCENT, or a TEXT
    maturity / term / rate column); (c) no MONEY header prints a flow period word (năm, quý, kỳ, giai đoạn, lũy kế,
    tháng). A "Thuyết minh" TEXT column alone is not a schedule; no other section or page text is read.
    """

    money = [c for c in table.columns if c.value_kind == "MONEY"]
    headers = {c.column_id: fold_vietnamese(c.header_text) for c in table.columns}
    position = [c.column_id for c in money if any(phrase_in(p, headers[c.column_id]) for p in _POSITION_MEASURE)]
    schedule = [c.column_id for c in table.columns if c.value_kind in {"COUNT", "PERCENT"}
                or (c.value_kind == "TEXT" and any(phrase_in(p, headers[c.column_id]) for p in _SCHEDULE_TEXT))]
    flow = [c.column_id for c in money if _FLOW_PERIOD.search(headers[c.column_id])]
    if position and schedule and not flow:
        return f"OWN_TABLE_IS_A_POSITION_SCHEDULE:money={','.join(position)};schedule={','.join(schedule)}"
    return None


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
    schedule = position_schedule_reason_v1(table)
    if schedule:
        # Kept in the dispositions audit with its locator and the deciding columns; the source rows are not dropped.
        evaluation.status, evaluation.reasons = "REJECTED", [schedule]
        return [evaluation]
    evaluation.subject, evaluation.subject_basis = resolve_subject_v1(family, context)
    owned_subject = evaluation.subject is not None and evaluation.subject_basis.get("tier") == "OWNER_CONTEXT"
    roles = assign_lines_v1(table, family, owned_subject=owned_subject)
    evaluation.roles = roles
    members = {r.role for r in roles if r.disposition == "MEMBER"}
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
    for lane in evaluation.lanes:
        # Shadow-only period evidence (Codex 0232): measured with its source header, never used below.
        evaluation.corroboration += [{**evidence, "lane": lane.column.column_id, "diagnostic_only": True}
                                     for evidence in lane.shadow_evidence]
    separators = table.separator_roles()
    vetoed_rows = [role.row_index for role in roles if role.reason.startswith("ROW_VETO:")]
    # Only a table closed by the unlabeled-total route (proposal T) also excuses detail reached through one proven
    # transparent wrapper; every other table keeps the immediate-parent rule unchanged (Codex 0302).
    t_route = any(role.reason.startswith(T_ROUTE_REASON) for role in roles)
    t_terms = root_terms_v1(family, family.raw["unlabeled_total_line"]) if t_route else set()
    for lane in evaluation.lanes:
        values = {role.role: parse_cell_v1(table, table.rows[role.row_index], lane.column, separators, document.separator_roles)
                  for role in roles if role.disposition == "MEMBER"}
        line_rows = {role.role: role.row_index for role in roles if role.disposition == "MEMBER"}
        unread = []
        for role in roles:
            if role.disposition not in {"SOURCE_ONLY", "AMBIGUOUS"}:
                continue
            if table.cells.get((table.rows[role.row_index].row_id, lane.column.column_id), (None, "BLANK"))[1] == "BLANK":
                continue
            parent = None
            # A vetoed (foreign) row is never excused as printed detail of a read line.
            if role.disposition == "SOURCE_ONLY" and role.row_index not in vetoed_rows:
                parent, _reason = detail_parent_line_v1(table, roles, role.row_index)
                if parent is None and t_route:
                    owner = _root_frontier_owner_v1(table, family, roles, role.row_index, t_terms)
                    parent = roles[owner].role if owner is not None and owner != role.row_index else None
                # The parent must itself carry a parsed amount in this lane to contain its detail.
                if parent is not None and (parent not in values or values[parent].state not in NUMERIC):
                    parent = None
            unread.append((role.row_index, parent))
        equations = evaluate_equations_v1(family, values, lane.unit, lane.column.column_id, line_rows, unread)
        evaluation.equations += equations
        checks = anchor_checks_v1(family, document, values, lane.unit, lane.period_key) if lane.period_key else []
        evaluation.corroboration += [{**c, "lane": lane.column.column_id} for c in checks]
        for candidate in lane.candidates:
            # Diagnostic only: shows what the income statement would say; it never selects the period.
            evaluation.corroboration += [{**c, "lane": lane.column.column_id, "diagnostic_only": True}
                                         for c in anchor_checks_v1(family, document, values, lane.unit, candidate)]
        proven = any(c["status"] == "EXACT" for c in checks) or any(e["status"].startswith("PASS") for e in equations)
        # A line that belongs to a declared equation or has a primary anchor must be proven by ITS OWN passing equation
        # or exact anchor; it never inherits the lane's proof from unrelated arithmetic (Codex 0196).
        own_proven = ({line for e in equations if e["status"].startswith("PASS") for line in [e["equals"], *e["terms"]]}
                      | {c["line"] for c in checks if c["status"] == "EXACT"})
        vetoed = any(c["status"] == "DIFFERS" for c in checks)
        failed = {line for e in equations if e["status"] == "FAIL" for line in [e["equals"], *e["terms"]]}
        # Lines of an equation with unread rows in its span: population closure is not proven, so no
        # other proof (an income-statement anchor) may accept them.
        open_lines = {line for e in equations if e["status"] == "INCOMPLETE_UNREAD_ROWS_IN_SPAN" for line in [e["equals"], *e["terms"]]}
        foreign = [i for i in vetoed_rows
                   if table.cells.get((table.rows[i].row_id, lane.column.column_id), (None, "BLANK"))[1] != "BLANK"]
        _emit(evaluation, family, document, lane, values, roles, proven=proven, vetoed=vetoed, failed=failed, open_lines=open_lines,
              own_proven=own_proven, foreign_held=foreign_population_lines_v1(table, family, roles, foreign))
    return [evaluation]


def _equation_terms(equation: dict[str, Any]) -> set[str]:
    terms = set(equation.get("plus", [])) | set(equation.get("minus", [])) | set(equation.get("plus_present", []))
    for key in ("plus_first_present", "minus_first_present"):
        for group in equation.get(key, []):
            terms.update(group)
    return terms


def foreign_population_lines_v1(table: NoteTable, family: Family, roles: list[RowRole], foreign_rows: list[int]) -> set[str]:
    """Lines whose printed population may contain a valued vetoed row (Codex 0203); nothing can accept them.

    Held: the family's generic-population lines (``foreign_row_holds``, e.g. the note total) wherever the
    foreign row is printed; every read line on the foreign row's CLAIMED parent chain (a claim suffices to
    doubt the population); and, to a fixed point, every equation target summing a held line. An exact
    income-statement anchor or a passing equation never overrides this, and no position, amount or
    arithmetic excludes a foreign row: excluding one would need a positive source partition (not in V1).
    Lines with their own printed population that the row does not claim (e.g. customer loans) keep their proofs;
    a contextual child of a held line (its ``depends_on`` edge from ``assign_lines_v1``) is held with it.
    """

    if not foreign_rows:
        return set()
    held = set(family.raw.get("foreign_row_holds") or [])
    line_of_row = {role.row_index: role.role for role in roles if role.disposition == "MEMBER"}
    index_of = {row.row_id: i for i, row in enumerate(table.rows)}
    for index in foreign_rows:
        seen = {index}
        current = table.rows[index].parent_row_id
        while current in index_of and index_of[current] not in seen:
            parent = index_of[current]
            seen.add(parent)
            if parent in line_of_row:
                held.add(line_of_row[parent])
            current = table.rows[parent].parent_row_id
    changed = True
    while changed:
        changed = False
        for equation in family.raw.get("equations") or []:
            if equation["equals"] not in held and _equation_terms(equation) & held:
                held.add(equation["equals"])
                changed = True
        for role in roles:
            # Downward (Codex 0208): a contextual child read only because of its proven owner / scoped parent
            # ("Dự phòng chung" under the customer line) depends on that parent's population; a fully qualified
            # direct label has no such edge and keeps its own proof.
            if (role.disposition == "MEMBER" and role.depends_on is not None and role.role not in held
                    and line_of_row.get(role.depends_on) in held):
                held.add(role.role)
                changed = True
    return held


def proof_bound_lines_v1(family: Family) -> set[str]:
    """Lines whose acceptance needs their own proof: every line named by a declared equation or a primary anchor."""

    bound: set[str] = set(family.raw.get("primary_anchors") or {})
    for equation in family.raw.get("equations") or []:
        bound.add(equation["equals"])
        bound.update(equation.get("plus", []), equation.get("minus", []), equation.get("plus_present", []))
        for key in ("plus_first_present", "minus_first_present"):
            for group in equation.get(key, []):
                bound.update(group)
    return bound


def _emit(evaluation: TableEvaluation, family: Family, document: DocumentContext, lane: NoteLane, values, roles,
          *, proven: bool, vetoed: bool, failed: set[str], open_lines: set[str], own_proven: set[str],
          foreign_held: set[str] = frozenset()) -> None:
    bound = proof_bound_lines_v1(family)
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
        if role.role in foreign_held:
            reasons.append("POPULATION_MAY_INCLUDE_VETOED_ROW")
        if parsed.state in {"MALFORMED", "AMBIGUOUS_SEPARATOR"}:
            reasons.append("CELL_" + parsed.state)
        if not proven and parsed.state != "BLANK":
            reasons.append("NO_EQUATION_OR_PRIMARY_PROOF")
        elif role.role in bound and role.role not in own_proven and parsed.state not in {"BLANK", "DASH"}:
            reasons.append("LINE_NOT_PROVEN_BY_ITS_OWN_EQUATION_OR_ANCHOR")
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
            # A line whose legacy meaning is not proven by its label alone (e.g. base vs tax effect).
            "semantic_state": family.axis.members.get(role.role, {}).get("semantic_state"),
        })
