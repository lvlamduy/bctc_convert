"""Pure whole-table ROOT closure of one CONCEPT_LIST family table, per lane (Codex 0324-0326). No I/O.

It answers one question for the strict-core ledger: does the family's printed ROOT (labeled, or the reviewed unlabeled
T route) close over the COMPLETE printed source table in this lane? Inputs are only typed structure and null metadata:
- ``inventory``: the neutral ORIGINAL inventory records of ONE table (format F36_NEUTRAL_SELECTED_ORIGINAL_INVENTORY_V1):
  {"table": <table record>, "columns": [column records], "rows": [row records], "unsupported": [unsupported_shape
  records under this table's pointer]};
- ``disposition``: the notes ``dispositions.json`` record of the same table (rows, lanes, equations, source bridges);
- ``family``: the loaded notes family (root line, root terms, transparent-wrapper literals, axis).
No amount is read or reconstructed: a cell is BLANK exactly when its ORIGINAL value is JSON null (the store's
``_visual_state(None)``), which is the inventory's ``null_column_ordinals``.

A lane is ROOT_CLOSED only when ALL hold:
1. the table is evaluable here: notes EVALUATED, one EXACT single-table source bridge (no continuation merge, no
   proven column shift - both are named UNRESOLVED reasons, kept with their evidence), the page bound in ONE domain
   (inventory ``page.source_proof.stored_blob_two_lf_sha256`` == bridge ``original_blob_sha256``, same VID; the
   one-LF / no-LF table digests are never compared), no unsupported ORIGINAL shape, and the notes and inventory row
   axes agree positionally (row id rN = ORIGINAL row N, equal labels). Numeric presence is read ONLY in the ORIGINAL
   MONEY columns the notes lanes occupy through the bridge's proven column map (a TEXT note reference never makes a
   row valued); it must agree with the notes HEADING disposition. Parent edges are re-proven from the ORIGINAL
   hierarchy and labels (unique earlier row) and must agree with the notes parent ids;
2. exactly one ROOT row (a MEMBER of the family root line by label, or the T route), printed as the FINAL source row;
3. every earlier row is partitioned without refusal (the reviewed T prefix partition, generalized to any root):
   a valued source top-level root-term MEMBER is FRONTIER; a valued non-root MEMBER or SOURCE_ONLY row (never a
   ROW_VETO, never AMBIGUOUS) is DETAIL of a frontier row through its proven printed parent edge or through ONE exact
   transparent wrapper (family literal, GROUP, every ORIGINAL cell null, its own proven parent edge); a blank exact
   wrapper owned by a frontier row is WRAPPER; a blank row with a proven frontier owner is BLANK_DETAIL; a blank row
   naming the root line or a root term, a nested root term, and anything without a proven frontier owner refuse;
4. the family's root equation for that lane has a passing status (``PASS`` or the producer's own
   ``PASS_WITHIN_DECLARED_ROUNDING``; the rounding rule is neither tightened nor relaxed here) and its terms are
   exactly the frontier lines.
The result proves complete source topology for a table-lane only - not artifact authenticity, unit, period, scope,
mapping or acceptance; the caller binds both immutable inputs and their source axes.
"""

from __future__ import annotations

import re
from typing import Any

from bctc_ai.notes.concept_list_shape_v1 import T_ROUTE_REASON, _scoped_match, root_terms_v1
from bctc_ai.notes.config_v1 import Family
from bctc_ai.primary_statements.text_v1 import fold_vietnamese, label_key_v1

ROOT_CLOSURE_FORMAT = "NOTES_ROOT_CLOSURE_V1"
# The producer's own passing equation statuses (evaluate_equations_v1); its declared rounding rule is used as is.
PASSING_ROOT_EQUATION_STATUSES = frozenset({"PASS", "PASS_WITHIN_DECLARED_ROUNDING"})
_POINTER = re.compile(r"/sections/(\d+)/tables/(\d+)")
_ROW_POINTER = re.compile(r"/sections/(\d+)/tables/(\d+)/rows/(\d+)")


def family_root_line_v1(family: Family) -> str | None:
    """The family's ROOT total: the one equation target that is no equation's term (None when not unique)."""

    equations = family.raw.get("equations") or []
    targets = {e["equals"] for e in equations}
    terms = set().union(*(root_terms_v1(family, target) for target in targets)) if targets else set()
    roots = targets - terms
    return next(iter(roots)) if len(roots) == 1 else None


def _strings(path: Any) -> list[str]:
    return [part for part in path or [] if isinstance(part, str) and part.strip()]


def _wrapper_literal(family: Family, label: Any) -> bool:
    literals = {fold_vietnamese(str(text)).strip() for text in (family.raw.get("transparent_wrappers") or {}).get("labels") or []}
    folded = fold_vietnamese(label or "").strip()
    folded = folded[:-1].rstrip() if folded.endswith(":") else folded
    return bool(literals) and folded in literals


def root_closure_v1(inventory: dict[str, Any], disposition: dict[str, Any], family: Family) -> dict[str, Any]:
    """Per-lane ROOT_CLOSED / NOT_ROOT_CLOSED:<why>, or UNRESOLVED:<why> for the whole table, plus the row partition."""

    result: dict[str, Any] = {"format": ROOT_CLOSURE_FORMAT, "family": family.name, "rows": [], "lanes": []}

    def unresolved(why: str) -> dict[str, Any]:
        return {**result, "status": "UNRESOLVED:" + why}

    root_line = family_root_line_v1(family)
    if root_line is None:
        return unresolved("FAMILY_ROOT_LINE_NOT_UNIQUE")
    terms = root_terms_v1(family, root_line)
    root_equations = {e["name"] for e in family.raw.get("equations") or [] if e.get("equals") == root_line}
    if disposition.get("status") != "EVALUATED":
        return unresolved("TABLE_NOT_EVALUATED:" + str(disposition.get("status")))
    if disposition.get("fragments"):
        return unresolved("CONTINUATION_MERGED_TABLE_NOT_SUPPORTED_V1")
    bridges = disposition.get("source_bridges") or []
    if len(bridges) != 1 or not isinstance(bridges[0], dict):
        return unresolved("NOT_ONE_SOURCE_BRIDGE")
    bridge = bridges[0]
    if bridge.get("status") != "EXACT":
        return unresolved("SOURCE_BRIDGE_NOT_EXACT:" + str(bridge.get("status")))
    table = inventory.get("table") or {}
    match = _POINTER.fullmatch(str(table.get("pointer", "")))
    if not match or (bridge.get("page_json_version_id"), bridge.get("section_ordinal"), bridge.get("table_ordinal")) != (
            table.get("page_json_version_id"), int(match.group(1)) + 1, int(match.group(2)) + 1):
        return unresolved("BRIDGE_AND_INVENTORY_NAME_DIFFERENT_TABLES")
    page = inventory.get("page") or {}
    if ((page.get("axis") or {}).get("page_json_version_id") != bridge.get("page_json_version_id")
            or not bridge.get("original_blob_sha256")
            or (page.get("source_proof") or {}).get("stored_blob_two_lf_sha256") != bridge.get("original_blob_sha256")):
        # One domain only: the actual stored two-LF page bytes on both sides (Codex 0326/0328).
        return unresolved("PAGE_BINDING_DIFFERS")
    if inventory.get("unsupported"):
        return unresolved("UNSUPPORTED_ORIGINAL_SHAPE:" + str(inventory["unsupported"][0].get("pointer")))

    columns, inv_rows, notes_rows = inventory.get("columns") or [], inventory.get("rows") or [], disposition.get("rows") or []
    if [c.get("column_ordinal") for c in columns] != list(range(1, len(columns) + 1)):
        return unresolved("COLUMN_AXIS_NOT_POSITIONAL")
    # Numeric presence is read ONLY in the ORIGINAL MONEY columns the notes lanes occupy through the proven bridge column
    # map; a non-null TEXT cell (e.g. a note reference "28") never makes a row valued (Codex 0328).
    lanes, column_map = disposition.get("lanes") or [], bridge.get("column_map") or {}
    if not lanes:
        return unresolved("NO_PROVEN_MONEY_LANES")
    money = set()
    for lane in lanes:
        ordinal = column_map.get(lane.get("column_id"))
        if not isinstance(ordinal, int) or not 1 <= ordinal <= len(columns):
            return unresolved("LANE_COLUMN_NOT_IN_PROVEN_COLUMN_MAP:" + str(lane.get("column_id")))
        exact = columns[ordinal - 1].get("column_exact")
        if not isinstance(exact, dict) or exact.get("value_kind") != "MONEY":
            return unresolved("LANE_COLUMN_NOT_ORIGINAL_MONEY:" + str(lane.get("column_id")))
        money.add(ordinal)
    if not (len(inv_rows) == len(notes_rows) == bridge.get("row_count")):
        return unresolved("ROW_COUNT_DIFFERS")
    rows = []
    for ordinal, (inv, note) in enumerate(zip(inv_rows, notes_rows, strict=True), 1):
        pointer = _ROW_POINTER.fullmatch(str(inv.get("pointer", "")))
        # The producer encodes every row field as {"present": bool, "value": raw}; a missing field is never read as an
        # explicit null, and a malformed envelope is never guessed at (Codex 0330).
        values = {}
        for key in ("label_exact", "row_kind", "hierarchy_path_exact"):
            envelope = (inv.get("fields") or {}).get(key)
            if not isinstance(envelope, dict) or set(envelope) != {"present", "value"} or type(envelope["present"]) is not bool:
                return unresolved(f"ORIGINAL_ROW_FIELD_ENVELOPE_MALFORMED:{key}:r{ordinal}")
            if not envelope["present"]:
                return unresolved(f"ORIGINAL_ROW_FIELD_ABSENT:{key}:r{ordinal}")
            values[key] = envelope["value"]
        axis = inv.get("value_axis")
        if (not pointer or int(pointer.group(3)) + 1 != ordinal or inv.get("row_ordinal") != ordinal
                or note.get("row_id") != f"r{ordinal}" or values["label_exact"] != note.get("label_exact")
                or not isinstance(axis, dict) or axis.get("count") != len(columns)):
            return unresolved(f"ROW_AXIS_DIFFERS:r{ordinal}")
        nulls = set(axis.get("null_column_ordinals") or [])
        valued = any(c not in nulls for c in money)
        if (note.get("disposition") == "HEADING") == valued:
            return unresolved(f"VALUE_STATE_DISAGREES:r{ordinal}")
        rows.append({"ordinal": ordinal, "label": values["label_exact"], "kind": values["row_kind"],
                     "path": values["hierarchy_path_exact"], "notes_parent": note.get("parent_row_id"),
                     "line": note.get("line"), "disposition": note.get("disposition"), "reason": note.get("reason") or "",
                     "valued": valued, "all_null": len(nulls) == len(columns)})
    # Parent edges are re-proven from the exact ORIGINAL hierarchy and labels: the parent is the UNIQUE earlier row whose
    # printed path is the child's path minus its own label and ends in that row's label. The notes parent_row_id is
    # only cross-checked against it (Codex 0328).
    for row in rows:
        path = _strings(row["path"])
        candidates = [] if len(path) < 2 or path[-1] != row["label"] else [
            earlier for earlier in rows[:row["ordinal"] - 1]
            if _strings(earlier["path"]) == path[:-1] and path[:-1] and path[:-1][-1] == earlier["label"]]
        row["parent"] = candidates[0] if len(candidates) == 1 else None
        expected = f"r{row['parent']['ordinal']}" if row["parent"] else None
        if (row["notes_parent"] or None) != expected and not (len(candidates) > 1 and row["notes_parent"] is None):
            return unresolved(f"PARENT_EDGE_DIFFERS_FROM_ORIGINAL:r{row['ordinal']}")

    def top_level(row: dict[str, Any]) -> bool:
        return row["parent"] is None and not row["notes_parent"] and _strings(row["path"]) in ([], [row["label"]])

    def frontier(row: dict[str, Any] | None) -> bool:
        return bool(row) and row["disposition"] == "MEMBER" and row["line"] in terms and top_level(row)

    def proven_parent(row: dict[str, Any]) -> dict[str, Any] | None:
        return row["parent"]

    def exact_wrapper_owner(wrapper: dict[str, Any]) -> dict[str, Any] | None:
        if wrapper["kind"] != "GROUP" or not wrapper["all_null"] or not _wrapper_literal(family, wrapper["label"]):
            return None
        owner = proven_parent(wrapper)
        return owner if frontier(owner) else None

    def frontier_owner(row: dict[str, Any]) -> dict[str, Any] | None:
        parent = proven_parent(row)
        if parent is None:
            return None
        if frontier(parent):
            return parent
        return exact_wrapper_owner(parent)

    roots = [r for r in rows if (r["disposition"] == "MEMBER" and r["line"] == root_line) or r["reason"].startswith(T_ROUTE_REASON)]
    lanes = disposition.get("lanes") or []

    def all_lanes(status: str) -> dict[str, Any]:
        result["lanes"] = [{"lane": lane.get("column_id"), "status": status} for lane in lanes]
        return {**result, "status": "EVALUATED"}

    if len(roots) != 1:
        return all_lanes(f"NOT_ROOT_CLOSED:ROOT_ROWS_{len(roots)}")
    root = roots[0]
    if root["ordinal"] != len(rows):
        return all_lanes(f"NOT_ROOT_CLOSED:ROOT_NOT_FINAL_SOURCE_ROW:r{root['ordinal']}")
    if not top_level(root):
        return all_lanes(f"NOT_ROOT_CLOSED:ROOT_NOT_AT_SOURCE_TOP_LEVEL:r{root['ordinal']}")
    for row in rows[:-1]:
        cls, owner, refusal = _partition(row, frontier, frontier_owner, exact_wrapper_owner, family, terms, root_line)
        result["rows"].append({"row_ordinal": row["ordinal"], "class": cls,
                               **({"owner_row_ordinal": owner["ordinal"]} if owner else {})})
        if refusal:
            return all_lanes(f"NOT_ROOT_CLOSED:{refusal}:r{row['ordinal']}")
    result["rows"].append({"row_ordinal": root["ordinal"], "class": "ROOT"})
    frontier_lines = {row["line"] for row in rows[:-1] if frontier(row)}
    statuses = {}
    for equation in disposition.get("equations") or []:
        if equation.get("name") in root_equations:
            statuses.setdefault(equation.get("lane"), []).append(equation)
    for lane in lanes:
        found = statuses.get(lane.get("column_id"), [])
        if len(found) != 1:
            status = f"NOT_ROOT_CLOSED:ROOT_EQUATIONS_{len(found)}"
        elif found[0].get("status") not in PASSING_ROOT_EQUATION_STATUSES:
            status = "NOT_ROOT_CLOSED:ROOT_EQUATION_" + str(found[0].get("status"))
        elif set(found[0].get("terms") or []) != frontier_lines:
            status = "NOT_ROOT_CLOSED:ROOT_EQUATION_TERMS_DIFFER_FROM_FRONTIER"
        else:
            status = "ROOT_CLOSED"
        result["lanes"].append({"lane": lane.get("column_id"), "status": status,
                                "root_equation_status": found[0].get("status") if len(found) == 1 else None})
    return {**result, "status": "EVALUATED"}


def _partition(row, frontier, frontier_owner, exact_wrapper_owner, family, terms, root_line):
    """(class, owner row, refusal reason or None) of one pre-root row."""

    if row["valued"]:
        if frontier(row):
            return "FRONTIER", None, None
        if row["disposition"] == "MEMBER" and row["line"] in terms:
            return "NESTED_ROOT_TERM", None, "ROOT_TERM_NOT_AT_SOURCE_TOP_LEVEL"
        if row["disposition"] not in {"MEMBER", "SOURCE_ONLY"} or row["reason"].startswith("ROW_VETO:"):
            return "UNACCOUNTED", None, "UNACCOUNTED_VALUED_ROW:" + str(row["disposition"])
        owner = frontier_owner(row)
        return ("DETAIL", owner, None) if owner else ("UNACCOUNTED", None, "UNACCOUNTED_VALUED_ROW")
    key = label_key_v1(row["label"]).key if row["label"] else ""
    named = set(family.axis.match(key)) if key else set()
    named |= {m for m, spec in family.axis.members.items() if key and spec.get("scoped") and _scoped_match(spec, key)}
    if root_line in named:
        return "BLANK_PRINTED_ROOT", None, "BLANK_PRINTED_ROOT_LINE"
    if named & terms:
        return "BLANK_ROOT_OPERAND", None, "BLANK_ROOT_OPERAND"
    owner = exact_wrapper_owner(row)
    if owner:
        return "WRAPPER", owner, None
    owner = frontier_owner(row)
    return ("BLANK_DETAIL", owner, None) if owner else ("UNRESOLVED_BLANK", None, "UNRESOLVED_BLANK_ROW")
