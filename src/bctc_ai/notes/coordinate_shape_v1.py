"""COORDINATE_LIST shape: each row is a coordinate over one or more axes.

"Tiền gửi không kỳ hạn" -> {DEPOSIT_TYPE: DEMAND}; the "Bằng VND" printed under
it -> {DEPOSIT_TYPE: DEMAND, CURRENCY: VND}; "Tiền gửi có kỳ hạn bằng ngoại tệ"
carries both axes in one label. An axis missing from a row is inherited only
from the open parent row (the last row naming the first axis, closed by a
total, a subject heading or another first-axis row). A heading that names a
subject starts a new subject block inside the table.

Equations are generated from the coordinates: a parent equals the sum of its
printed children, and a block total equals the sum of its first-axis rows.
A cell is accepted only when an equation it takes part in passes (or the
block total equals the primary statement line) and no equation it takes part
in fails. Nothing is derived, back-solved or signed to close a check.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from bctc_ai.notes.config_v1 import Family, all_phrases
from bctc_ai.notes.kernel_v1 import DocumentContext, NoteLane, NoteTable, parse_cell_v1, resolve_instant_lanes_v1
from bctc_ai.notes.list_shape_v1 import TOTAL_KEYS, classification_basis_v1, owned_date_texts_v1, resolve_subject_v1
from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.primary_statements.units_v1 import SCALE

TOTAL = "TOTAL"


def coordinate_key(coordinate: dict[str, str], axes: list[str]) -> str:
    return TOTAL if not coordinate else ";".join(f"{axis}={coordinate[axis]}" for axis in axes if axis in coordinate)


@dataclass
class CoordinateRow:
    row_index: int
    coordinate: dict[str, str] | None
    disposition: str            # COORDINATE | TOTAL | HEADING | SOURCE_ONLY | AMBIGUOUS
    reason: str
    subject: str | None = None
    block: int = 0


@dataclass
class CoordinateEvaluation:
    table: NoteTable
    status: str
    reasons: list[str]
    context: list[tuple[str, str]] = field(default_factory=list)
    rows: list[CoordinateRow] = field(default_factory=list)
    lanes: list[NoteLane] = field(default_factory=list)
    equations: list[dict[str, Any]] = field(default_factory=list)
    corroboration: list[dict[str, Any]] = field(default_factory=list)
    cells: list[dict[str, Any]] = field(default_factory=list)
    subject: str | None = None
    subject_basis: dict[str, Any] = field(default_factory=dict)
    block: dict[str, Any] | None = None

    @property
    def roles(self):
        return self.rows


def _has_values(table: NoteTable, row) -> bool:
    return any(table.cells.get((row.row_id, c.column_id), (None, "BLANK"))[1] != "BLANK"
               for c in table.columns if c.value_kind == "MONEY")


def _row_subjects(family: Family, label: str) -> set[str]:
    """Subjects a row label itself prints: the family subject phrases, plus its declared ``row_subject_markers``."""

    folded = fold_vietnamese(label)
    found = set(family.subjects_in(folded))
    for subject, groups in (family.raw.get("row_subject_markers") or {}).items():
        if all_phrases([[fold_vietnamese(str(p)) for p in group] for group in groups], folded):
            found.add(subject)
    return found


def assign_coordinates_v1(table: NoteTable, family: Family, axes, table_subject: str | None) -> list[CoordinateRow]:
    axis_names = [axis.name for axis in axes]
    rows: list[CoordinateRow] = []
    parent: dict[str, str] | None = None
    subject, block, closed = table_subject, 0, False
    for index, row in enumerate(table.rows):
        key = row.key
        valued = _has_values(table, row)
        is_total_label = bool(key and TOTAL_KEYS.match(key))
        heading_subjects = family.subjects_in(fold_vietnamese(row.label or "")) if row.label and not is_total_label else []
        matches = {axis.name: axis.match(key) for axis in axes} if key else {}
        own = {name: found[0] for name, found in matches.items() if len(found) == 1}
        ambiguous = [name for name, found in matches.items() if len(found) > 1]
        if closed and (own or heading_subjects):
            # After a total, axis rows start another breakdown of the same subject.
            block, parent, closed = block + 1, None, False
        named = _row_subjects(family, row.label) if (own or ambiguous) and row.label and not is_total_label else set()
        if named and subject is not None and named != {subject}:
            # An axis match never erases the population the row prints ("Tiền gửi tại các TCTD không kỳ hạn" under
            # customer deposits; "Tiền gửi của Công ty TNHH" under loans): no member, and the table is held (Codex 0206).
            rows.append(CoordinateRow(index, None, "SOURCE_ONLY", "ROW_SUBJECT_CONFLICT:" + ",".join(sorted(named)), subject, block))
            continue
        if len(heading_subjects) == 1 and not own:
            # "Tiền gửi tại các TCTD khác" / "Cho vay các TCTD khác" heading: new subject block.
            subject, parent, block = heading_subjects[0], None, block + 1
            if not valued:
                rows.append(CoordinateRow(index, None, "HEADING", "SUBJECT_HEADING", subject, block))
                continue
            rows.append(CoordinateRow(index, {}, "TOTAL", "SUBJECT_ROW_IS_ITS_BLOCK_TOTAL", subject, block))
            continue
        if ambiguous:
            rows.append(CoordinateRow(index, None, "AMBIGUOUS", "ROW_MATCHES_SEVERAL_MEMBERS:" + ",".join(ambiguous), subject, block))
            continue
        first = axis_names[0]
        if not valued and own and row.kind == "GROUP":
            # A value-less source GROUP row only opens the parent its first-axis member names. Any other printed
            # axis row with all-null money cells stays a coordinate: an unknown component (Codex 0213).
            if first in own:
                parent = {first: own[first]}
            rows.append(CoordinateRow(index, None, "HEADING", "NO_VALUES", subject, block))
            continue
        if first in own:
            parent = {first: own[first]}
            coordinate = dict(own)
        elif own and parent is not None:
            coordinate = {**parent, **own}
        elif own:
            coordinate = dict(own)
        else:
            is_total = row.kind in {"TOTAL", "SUBTOTAL"} and not row.label or is_total_label
            if is_total and valued:
                rows.append(CoordinateRow(index, {}, "TOTAL", "TOTAL_ROW", subject, block))
                parent, closed = None, True
                continue
            if not valued:
                rows.append(CoordinateRow(index, None, "HEADING", "NO_VALUES", subject, block))
                continue
            rows.append(CoordinateRow(index, None, "SOURCE_ONLY", "NO_AXIS_MEMBER", subject, block))
            if closed:
                block, closed = block + 1, False
            continue
        rows.append(CoordinateRow(index, coordinate, "COORDINATE", "AXIS_ALIASES", subject, block))
    # A coordinate or total printed twice in one block cannot be told apart.
    seen: dict[tuple[int, str], int] = {}
    for row in rows:
        if row.coordinate is not None:
            seen[(row.block, coordinate_key(row.coordinate, axis_names))] = seen.get((row.block, coordinate_key(row.coordinate, axis_names)), 0) + 1
    for row in rows:
        if row.coordinate is not None and seen[(row.block, coordinate_key(row.coordinate, axis_names))] > 1:
            row.disposition, row.reason, row.coordinate = "AMBIGUOUS", "COORDINATE_PRINTED_MORE_THAN_ONCE", None
    return rows


def _tolerance(unit: str | None, terms: int) -> Decimal:
    if unit and SCALE.get(unit, 1) >= 1_000_000:
        return Decimal(max(1, math.ceil(terms / 2)))
    return Decimal(0)


def evaluate_coordinate_table_v1(
    table: NoteTable, family: Family, document: DocumentContext, context: list[tuple[str, str]], page_texts: list[str],
    axes=None,
) -> list[CoordinateEvaluation]:
    axes = axes or [family.axis]
    axis_names = [axis.name for axis in axes]
    evaluation = CoordinateEvaluation(table, "EVALUATED", [], context=context)
    own_text = " ".join(fold_vietnamese(text) for source, text in context[:3])
    if family.rejects(own_text):
        evaluation.status, evaluation.reasons = "REJECTED", ["CONTEXT_IS_NOT_A_BALANCE_BREAKDOWN"]
        return [evaluation]
    evaluation.subject, evaluation.subject_basis = resolve_subject_v1(family, context)
    rows = assign_coordinates_v1(table, family, axes, evaluation.subject)
    first_members = {r.coordinate.get(axis_names[0]) for r in rows if r.coordinate}
    first_members.discard(None)
    if len(first_members) < family.min_distinct_members:
        evaluation.status, evaluation.reasons = "REJECTED", [f"ONLY_{len(first_members)}_FIRST_AXIS_MEMBERS"]
        return [evaluation]
    evaluation.rows = rows
    own = owned_date_texts_v1(table, context)
    # A column naming a measure other than the gross balance keeps that meaning (Codex 0206); see ``_cell``.
    measures = {m: [fold_vietnamese(str(a)) for a in spec["aliases"]]
                for m, spec in (family.raw.get("non_balance_column_measures") or {}).items()}
    evaluation.lanes = resolve_instant_lanes_v1(table, document, page_texts, own, measures or None)
    if not evaluation.lanes:
        evaluation.status, evaluation.reasons = "REJECTED", ["NO_MONEY_LANES"]
        return [evaluation]
    basis = classification_basis_v1(context)
    separator_roles = table.separator_roles()
    for lane in evaluation.lanes:
        values = {}
        for row in rows:
            if row.coordinate is None:
                continue
            parsed = parse_cell_v1(table, table.rows[row.row_index], lane.column, separator_roles, document.separator_roles)
            values[(row.block, coordinate_key(row.coordinate, axis_names))] = (row, parsed)
        proven, failed = set(), set()
        # A valued row printing another subject's population puts the whole table's population in doubt, wherever
        # it is printed; no total, equation or primary agreement excludes it without a proven source partition.
        foreign = any(row.reason.startswith("ROW_SUBJECT_CONFLICT:")
                      and table.cells.get((table.rows[row.row_index].row_id, lane.column.column_id), (None, "BLANK"))[1] != "BLANK"
                      for row in rows)
        for block in sorted({row.block for row in rows}):
            block_values = {k[1]: v for k, v in values.items() if k[0] == block}
            subject = next((r.subject for r, _ in block_values.values() if r.subject), evaluation.subject)
            _corroborate_block(evaluation, family, document, lane, subject, block, block_values, proven)
            for parent_key, children in _equations_for(block_values, axis_names, axes[0], table):
                _check(evaluation, lane, block, parent_key, children, block_values, proven, failed)
        for (block, key), (row, parsed) in values.items():
            evaluation.cells.append(_cell(evaluation, family, document, lane, row, parsed, key, basis,
                                          proven, failed, block, foreign))
    return [evaluation]


def _member_ancestors(member: str, first_axis) -> set[str]:
    found, current = set(), (first_axis.members.get(member) or {}).get("parent")
    while current:
        found.add(current)
        current = (first_axis.members.get(current) or {}).get("parent")
    return found


def _is_ancestor(a: dict[str, str], c: dict[str, str], first: str, first_axis, nested: bool = True) -> bool:
    """a covers c: every axis of a is in c with the same member or a parent member.

    A parent *member* (e.g. LLC over LLC_OTHER) covers only when the source
    prints the child nested under the parent row (``nested``); banks often
    list the same members flat, as siblings.
    """

    if a == c or not set(a) <= set(c):
        return False
    for axis, member in a.items():
        if c[axis] == member:
            continue
        if not (axis == first and nested and member in _member_ancestors(c[axis], first_axis)):
            return False
    return True


def _source_nested(table, child_index: int, parent_index: int) -> bool:
    """The printed hierarchy puts the child row under the parent row."""

    child, parent = table.rows[child_index], table.rows[parent_index]
    seen, current, by_id = set(), child.parent_row_id, {row.row_id: row for row in table.rows}
    while current and current not in seen:
        if current == parent.row_id:
            return True
        seen.add(current)
        current = by_id[current].parent_row_id if current in by_id else None
    return bool(parent.label) and parent.label in child.hierarchy[:-1]


def _equations_for(block_values, axis_names, first_axis, table):
    """(parent, children) pairs generated from the printed coordinate tree.

    * the block total equals the sum of the frontier: printed coordinates
      with no printed ancestor (parents when printed, else their children);
    * each printed coordinate equals the sum of the printed coordinates whose
      nearest printed ancestor it is.
    Value-less headings are not printed coordinates, so their children move
    up to the frontier instead of being summed into a missing parent.
    """

    first = axis_names[0]
    coordinates = {key: block_values[key][0].coordinate for key in block_values if key != TOTAL}
    index = {key: block_values[key][0].row_index for key in coordinates}
    ancestors = {k: [a for a, ca in coordinates.items()
                     if _is_ancestor(ca, c, first, first_axis, _source_nested(table, index[k], index[a]))]
                 for k, c in coordinates.items()}
    frontier = [k for k, found in ancestors.items() if not found]
    if TOTAL in block_values and len(frontier) >= 2:
        yield TOTAL, frontier
    nearest = {}
    for key, found in ancestors.items():
        direct = [a for a in found if not any(b in ancestors and a in ancestors[b] for b in found if b != a)]
        if len(direct) == 1:
            nearest.setdefault(direct[0], []).append(key)
    for parent_key, children in nearest.items():
        yield parent_key, children


def _check(evaluation, lane, block, parent_key, children, block_values, proven, failed):
    parent = block_values[parent_key][1]
    terms = [block_values[k][1] for k in children]
    if any(t.state not in {"VALUE", "PRINTED_ZERO", "DASH", "BLANK"} for t in terms + [parent]):
        evaluation.equations.append({"lane": lane.column.column_id, "block": block, "parent": parent_key, "children": children,
                                     "status": "NOT_EVALUABLE", "reason": "UNPARSED_CELL"})
        return
    parent_value = Decimal(0) if parent.state == "DASH" else parent.value
    if parent_value is None or all(t.state == "BLANK" for t in terms):
        evaluation.equations.append({"lane": lane.column.column_id, "block": block, "parent": parent_key, "children": children,
                                     "status": "NOT_EVALUABLE", "reason": "TOTAL_OR_ALL_TERMS_BLANK"})
        return
    if any(t.state == "BLANK" for t in terms):
        # A printed coordinate with an unknown (blank) cell leaves the frontier open: no proof, and never another
        # child's dash read as zero (Codex 0209).
        evaluation.equations.append({"lane": lane.column.column_id, "block": block, "parent": parent_key, "children": children,
                                     "status": "INCOMPLETE_BLANK_OPERAND",
                                     "blank_children": [k for k in children if block_values[k][1].state == "BLANK"]})
        return
    summed = sum((Decimal(0) if t.state == "DASH" else t.value for t in terms if t.state == "DASH" or t.value is not None), Decimal(0))
    residual = parent_value - summed
    status = "PASS" if residual == 0 else ("PASS_WITHIN_DECLARED_ROUNDING" if abs(residual) <= _tolerance(lane.unit, len(terms)) else "FAIL")
    evaluation.equations.append({"lane": lane.column.column_id, "block": block, "parent": parent_key, "children": children,
                                 "status": status, "residual": str(residual)})
    target = proven if status.startswith("PASS") else failed
    for key in [parent_key, *children]:
        target.add((block, key))


def _corroborate_block(evaluation, family, document, lane, subject, block, block_values, proven):
    spec = (family.raw.get("primary_corroboration") or {}).get(subject or "")
    if not spec or TOTAL not in block_values or not lane.period_key or lane.measure is not None:
        return  # a provision/net/other measure column is never compared with a balance-sheet balance
    parsed = block_values[TOTAL][1]
    primary = document.primary_cells.get((spec["statement"], spec["report_norm_id"], lane.period_key))
    if primary is None or parsed.value is None:
        evaluation.corroboration.append({"lane": lane.column.column_id, "block": block, "status": "PRIMARY_CELL_ABSENT"})
        return
    value, unit = primary
    if lane.unit not in SCALE or unit not in SCALE:
        # Corroboration never supplies a unit (Codex 0009): nothing to compare.
        evaluation.corroboration.append({"lane": lane.column.column_id, "block": block, "status": "NOT_COMPARABLE_UNIT_NOT_PRINTED"})
        return
    agrees = (lane.unit == unit and parsed.value == value) or         abs(parsed.value * SCALE[lane.unit] - value * SCALE[unit]) < max(SCALE[lane.unit], SCALE[unit])
    evaluation.corroboration.append({"lane": lane.column.column_id, "block": block, "subject": subject,
                                     "status": "AGREES_WITH_PRIMARY" if agrees else "DIFFERS_FROM_PRIMARY",
                                     "primary_report_norm_id": spec["report_norm_id"], "primary_value": str(value)})
    if agrees:
        proven.add((block, TOTAL))


def _cell(evaluation, family, document, lane, row, parsed, key, basis, proven, failed, block, foreign=False):
    reasons = []
    subject = row.subject or evaluation.subject
    if document.scope is None:
        reasons.append("SCOPE_UNRESOLVED")
    if subject is None:
        reasons.append("SUBJECT_UNRESOLVED")
    reasons += lane.reasons
    if lane.measure is not None:
        reasons.append("COLUMN_MEASURE_NOT_A_BALANCE:" + lane.measure)
    if foreign:
        reasons.append("TABLE_CONTAINS_ROW_OF_ANOTHER_SUBJECT")
    if (block, key) in failed:
        reasons.append("VALIDATION_FAIL")
    state, value = parsed.state, parsed.value
    if (block, key) not in proven and state != "BLANK":
        reasons.append("NO_EQUATION_OR_PRIMARY_PROOF")
    if state == "DASH":
        if (block, key) in proven and (block, key) not in failed:
            state, value = "DASH_ZERO", Decimal(0)
        else:
            reasons.append("DASH_WITHOUT_PROOF")
    if state in {"MALFORMED", "AMBIGUOUS_SEPARATOR"}:
        reasons.append("CELL_" + state)
    acceptance = "HOLD" if reasons else ("ACCEPTED_BLANK" if state == "BLANK" else "ACCEPTED")
    source_row = evaluation.table.rows[row.row_index]
    return {
        "document_ordinal": document.ordinal, "document_plan_id": document.document_plan_id, "scope": document.scope,
        "family": family.name, "concept": subject, "measure": lane.measure, "axis": "x".join(family.raw.get("axes") or [family.axis.name]),
        "member": key, "classification_basis": basis, "period_key": lane.period_key, "period_basis": lane.period_basis,
        "unit": lane.unit, "unit_basis": lane.unit_basis, "observation_state": state,
        "value": None if value is None else format(value, "f"), "raw": parsed.raw, "acceptance": acceptance,
        "hold_reasons": reasons,
        "locator": {**evaluation.table.locator(), "row_id": source_row.row_id, "row_order": source_row.order,
                    "column_id": lane.column.column_id},
        "label_exact": source_row.label, "header_text": lane.column.header_text,
    }
