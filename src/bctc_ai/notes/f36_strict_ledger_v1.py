"""Pure F36 strict-ledger join (Codex 0343/0344): typed notes cells x actual root closure x neutral ORIGINAL inventory.

No I/O and no acceptance. A thin external runner binds the immutable inputs (notes store / closure results /
neutral inventory / legacy value proofs) and calls these functions; every output record is a classification with its
evidence, never a financial admission. ``CORE_CANDIDATE`` is the strictest class here and still precedes the canonical
export / persistence / replay and the PDF / residual / terminal gates.

Observation axis - every notes cell of the family gets exactly one class:
  CORE_CANDIDATE                     acceptance ACCEPTED (a valued cell) AND its table-lane is ROOT_CLOSED in the actual
                                     closure result AND its ORIGINAL coordinate joins exactly one inventory row / column
                                     whose item is a non-null str with the same one-LF raw hash AND unit / period_key /
                                     member are set and scope is SEPARATE or CONSOLIDATED AND report_norm_id equals the
                                     engine's exact crosswalk binding recomputed from all cells (basis rule + lane
                                     preference), and is not null
  ACCEPTED_SOURCE_ONLY               as CORE_CANDIDATE, but the exact binding is no RNID (RENT / OTHER_ASSET ...)
  ACCEPTED_PRINTED_BLANK_OR_DASH     ACCEPTED_BLANK / ACCEPTED_DASH: kept as printed, never a zero, never core
  DUPLICATE_IDENTICAL_CONTROL        the store's control state: kept, never core
  ACCEPTED_LOCAL_NOT_ROOT_CLOSED:<w> ACCEPTED, but the lane is NOT_ROOT_CLOSED or the table UNRESOLVED / without result
  ACCEPTED_IDENTITY_UNPROVEN:<w>     ACCEPTED and closed, but a coordinate / raw / type / null / axis / RNID proof fails
  HOLD:<reason prefix>               notes HOLD (all reasons kept in the record)
  UNKNOWN_ACCEPTANCE_STATE:<s>       anything else - a gate failure, never dropped
Source axis - every ORIGINAL table and every row of an assessed table:
  table ASSESSED_OPEX (a fragment of a retrieved target, with its closure status) or UNASSESSED (tagged
  POTENTIAL_CANDIDATE when a family subject phrase is printed in its own section / table title) - never "absent";
  row READ (some money position is a notes cell; every OTHER valued money position is listed as unread), its closure
  partition class, UNREAD_ORIGINAL (valued, no cell, no partition) or BLANK_ROW.
Legacy axis - every LEGACY_VALUE_PROOF_V1 record (one per legacy mapping value) once: LEGACY_NOT_JOINABLE:<proof>
unless the proof is a direct, complete lane -> ORIGINAL column proof; then LEGACY_AGREES / LEGACY_DIFFERS:<axes> on
RNID / raw / unit only (period never: LEGACY_PERIOD_UNPROVEN). A proven difference moves that CORE_CANDIDATE to
CONFLICT_REVIEW; absent legacy evidence never establishes or contradicts anything.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

LEDGER_FORMAT = "F36_STRICT_LEDGER_V1"
KNOWN_ACCEPTANCE = frozenset({"ACCEPTED", "ACCEPTED_BLANK", "ACCEPTED_DASH", "HOLD", "DUPLICATE_IDENTICAL_CONTROL"})
SCOPES = frozenset({"SEPARATE", "CONSOLIDATED"})
DIRECT_PROOF = "DIRECT_LANE_COLUMN_PROVEN"
_TABLE_POINTER = re.compile(r"/sections/(\d+)/tables/(\d+)")
_ROW_POINTER = re.compile(r"/sections/(\d+)/tables/(\d+)/rows/(\d+)")


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def target_key_v1(family: str, cell: dict[str, Any]) -> list[Any]:
    """The packet / closure target key of a cell's table: [family, document, VID, section_id, table_id]."""

    locator = cell.get("locator") or {}
    return [family, cell.get("document_ordinal"), locator.get("page_json_version_id"), locator.get("section_id"),
            locator.get("table_id")]


def table_coordinate_v1(record: dict[str, Any]) -> tuple[Any, int, int] | None:
    """(VID, section ordinal, table ordinal) of an inventory table / column / row record, from its pointer."""

    match = _TABLE_POINTER.match(str(record.get("pointer", "")))
    if not match:
        return None
    return record.get("page_json_version_id"), int(match.group(1)) + 1, int(match.group(2)) + 1


def row_coordinate_v1(record: dict[str, Any]) -> tuple[Any, int, int, int] | None:
    match = _ROW_POINTER.fullmatch(str(record.get("pointer", "")))
    if not match or record.get("row_ordinal") != int(match.group(3)) + 1:
        return None
    return record.get("page_json_version_id"), int(match.group(1)) + 1, int(match.group(2)) + 1, int(match.group(3)) + 1


def exact_rnid_bindings_v1(cells: list[dict[str, Any]], crosswalk: dict[tuple[str, str, tuple[str, ...]], int]) -> list[int | None]:
    """The engine's crosswalk binding for every cell, recomputed independently from ALL cells (engine_v1 L225-245).

    A document printing several classification bases for one concept / axis binds only AS_PRESENTED cells; a member of
    a preference tuple binds only when it is the first member of that tuple present in its own lane.
    """

    bases, lanes = defaultdict(set), defaultdict(set)
    for cell in cells:
        bases[(cell.get("document_ordinal"), cell.get("concept"), cell.get("axis"))].add(cell.get("classification_basis"))
        locator = cell.get("locator") or {}
        lanes[(locator.get("page_json_version_id"), locator.get("section_id"), locator.get("table_id"),
               locator.get("column_id"))].add(cell.get("member"))
    bindings = []
    for cell in cells:
        bound = None
        if not (len(bases[(cell.get("document_ordinal"), cell.get("concept"), cell.get("axis"))]) > 1
                and cell.get("classification_basis") != "AS_PRESENTED"):
            locator = cell.get("locator") or {}
            present = lanes[(locator.get("page_json_version_id"), locator.get("section_id"), locator.get("table_id"),
                             locator.get("column_id"))]
            for (concept, axis, members), rnid in crosswalk.items():
                if concept == cell.get("concept") and axis == cell.get("axis") and cell.get("member") in members \
                        and next((m for m in members if m in present), None) == cell.get("member"):
                    bound = rnid
        bindings.append(bound)
    return bindings


def _original_proof(cell: dict[str, Any], inventory_rows: dict[tuple, dict[str, Any]]) -> str | None:
    """None when the cell's ORIGINAL coordinate / raw / type / null evidence holds, else the first failing proof."""

    origin = cell.get("original_cell")
    if not isinstance(origin, dict) or not all(_positive(origin.get(k)) for k in
                                               ("section_ordinal", "table_ordinal", "row_ordinal", "column_ordinal")):
        return "ORIGINAL_COORDINATE_ABSENT"
    row = inventory_rows.get((origin.get("page_json_version_id"), origin["section_ordinal"], origin["table_ordinal"],
                              origin["row_ordinal"]))
    if row is None:
        return "ORIGINAL_ROW_NOT_IN_INVENTORY"
    axis = row.get("value_axis") or {}
    column = origin["column_ordinal"]
    types, hashes = axis.get("item_types"), axis.get("items_one_lf_sha256")
    if not isinstance(axis.get("count"), int) or not 1 <= column <= axis["count"] \
            or not isinstance(types, list) or not isinstance(hashes, list) or not len(types) == len(hashes) == axis["count"]:
        return "ORIGINAL_COLUMN_OUTSIDE_ROW_VALUE_AXIS"
    if column in (axis.get("null_column_ordinals") or []) or types[column - 1] != "str":
        return "ORIGINAL_ITEM_NOT_A_NON_NULL_STRING"
    if not isinstance(cell.get("raw"), str) or hashes[column - 1] != canonical_json_sha256_v1(cell["raw"]):
        return "RAW_ONE_LF_HASH_DIFFERS_FROM_ORIGINAL_ITEM"
    return None


def classify_observation_v1(cell: dict[str, Any], binding: int | None, closure: dict[str, Any] | None,
                            inventory_rows: dict[tuple, dict[str, Any]]) -> dict[str, Any]:
    """One observation record: class, its proofs and the evidence it rests on."""

    record = {"cell": cell, "exact_rnid_binding": binding}
    acceptance = cell.get("acceptance")
    if acceptance not in KNOWN_ACCEPTANCE:
        return {**record, "class": f"UNKNOWN_ACCEPTANCE_STATE:{acceptance}"}
    if acceptance == "HOLD":
        reasons = cell.get("hold_reasons") or []
        return {**record, "class": "HOLD:" + (str(reasons[0]).split(":")[0] if reasons else "NO_REASON_RECORDED")}
    if acceptance in {"ACCEPTED_BLANK", "ACCEPTED_DASH"}:
        return {**record, "class": "ACCEPTED_PRINTED_BLANK_OR_DASH"}
    if acceptance == "DUPLICATE_IDENTICAL_CONTROL":
        return {**record, "class": "DUPLICATE_IDENTICAL_CONTROL"}
    if closure is None:
        return {**record, "class": "ACCEPTED_LOCAL_NOT_ROOT_CLOSED:NO_CLOSURE_RESULT"}
    if str(closure.get("status", "")).startswith("UNRESOLVED:"):
        return {**record, "class": "ACCEPTED_LOCAL_NOT_ROOT_CLOSED:" + closure["status"]}
    column = (cell.get("locator") or {}).get("column_id")
    lanes = [lane for lane in closure.get("lanes") or [] if lane.get("lane") == column]
    lane_status = lanes[0].get("status") if len(lanes) == 1 else f"LANES_{len(lanes)}"
    record["lane_closure"] = lane_status
    if lane_status != "ROOT_CLOSED":
        return {**record, "class": f"ACCEPTED_LOCAL_NOT_ROOT_CLOSED:{lane_status}"}
    failed = _original_proof(cell, inventory_rows)
    if failed is None and not (cell.get("unit") and cell.get("period_key") and cell.get("member") and cell.get("scope") in SCOPES):
        failed = "UNIT_PERIOD_SCOPE_OR_ROLE_AXIS_MISSING"
    if failed is None and cell.get("report_norm_id") != binding:
        failed = "RNID_IS_NOT_THE_EXACT_CROSSWALK_BINDING"
    if failed:
        return {**record, "class": f"ACCEPTED_IDENTITY_UNPROVEN:{failed}"}
    return {**record, "class": "CORE_CANDIDATE" if binding is not None else "ACCEPTED_SOURCE_ONLY"}


def classify_rows_v1(rows: list[dict[str, Any]], columns: list[dict[str, Any]], cells: list[dict[str, Any]],
                     closure: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Every row of one assessed ORIGINAL table: READ (with every OTHER valued money position listed), its closure
    partition class, UNREAD_ORIGINAL or BLANK_ROW. A notes cell accounts only for its own (row, column) position."""

    money = {c.get("column_ordinal") for c in columns
             if isinstance(c.get("column_exact"), dict) and c["column_exact"].get("value_kind") == "MONEY"}
    owned = defaultdict(set)
    for cell in cells:
        origin = cell.get("original_cell") or {}
        if _positive(origin.get("row_ordinal")) and _positive(origin.get("column_ordinal")):
            owned[origin["row_ordinal"]].add(origin["column_ordinal"])
    partition = {r.get("row_ordinal"): r.get("class") for r in (closure or {}).get("rows") or []}
    out = []
    for row in rows:
        ordinal = row.get("row_ordinal")
        nulls = set((row.get("value_axis") or {}).get("null_column_ordinals") or [])
        valued = sorted(c for c in money if c not in nulls)
        if owned.get(ordinal):
            out.append({"row_ordinal": ordinal, "class": "READ", "read_money_positions": sorted(owned[ordinal] & set(valued)),
                        "unread_money_positions": [c for c in valued if c not in owned[ordinal]]})
        elif ordinal in partition:
            out.append({"row_ordinal": ordinal, "class": partition[ordinal], "unread_money_positions": valued})
        else:
            out.append({"row_ordinal": ordinal, "class": "UNREAD_ORIGINAL" if valued else "BLANK_ROW",
                        "unread_money_positions": valued})
    return out


def classify_table_v1(table: dict[str, Any], section: dict[str, Any] | None, assessed: dict[tuple, Any],
                      subject_phrases: list[list[str]]) -> dict[str, Any]:
    """ASSESSED_OPEX (with its target and closure status) or UNASSESSED with a caption tag; never absent."""

    coordinate = table_coordinate_v1(table)
    if coordinate in assessed:
        return {"table": list(coordinate), "class": "ASSESSED_OPEX", "target": assessed[coordinate]}
    titles = [((table.get("fields") or {}).get("title_exact") or {}).get("value"),
              (((section or {}).get("fields") or {}).get("title_exact") or {}).get("value")]
    folded = " ".join(fold_vietnamese(t) for t in titles if isinstance(t, str))
    hit = any(all(fold_vietnamese(p) in folded for p in group) for group in subject_phrases)
    return {"table": list(coordinate) if coordinate else None, "class": "UNASSESSED",
            "tag": "POTENTIAL_CANDIDATE" if hit else "NOT_SCANNED_AS_CANDIDATE"}


def classify_legacy_value_v1(proof: dict[str, Any], observations_by_coordinate: dict[tuple, dict[str, Any]],
                             inventory_rows: dict[tuple, dict[str, Any]]) -> dict[str, Any]:
    """One legacy mapping value: not joinable unless directly proven; else agree / differ on RNID, raw and unit only."""

    record = {"item_mapping_id": proof.get("item_mapping_id"), "value_index": proof.get("value_index"),
              "proof_status": proof.get("proof_status"), "period": "LEGACY_PERIOD_UNPROVEN"}
    if proof.get("proof_status") != DIRECT_PROOF:
        return {**record, "class": "LEGACY_NOT_JOINABLE:" + str(proof.get("proof_status"))}
    origin = proof.get("original_cell") or {}
    key = (origin.get("page_json_version_id"), origin.get("section_ordinal"), origin.get("table_ordinal"),
           origin.get("row_ordinal"), origin.get("column_ordinal"))
    observation = observations_by_coordinate.get(key)
    if observation is None:
        return {**record, "class": "LEGACY_NO_CURRENT_OBSERVATION", "original_cell": origin}
    row = inventory_rows.get(key[:4]) or {}
    hashes = (row.get("value_axis") or {}).get("items_one_lf_sha256") or []
    item_hash = hashes[key[4] - 1] if _positive(key[4]) and key[4] <= len(hashes) else None
    differs = [axis for axis, same in (
        ("RNID", proof.get("report_norm_id") == observation["cell"].get("report_norm_id")),
        ("RAW", proof.get("source_text_one_lf_sha256") is not None and proof.get("source_text_one_lf_sha256") == item_hash),
        ("UNIT", proof.get("unit") == observation["cell"].get("unit"))) if not same]
    return {**record, "class": "LEGACY_DIFFERS:" + ",".join(differs) if differs else "LEGACY_AGREES", "original_cell": origin}


def apply_legacy_conflicts_v1(observations: list[dict[str, Any]], legacy: list[dict[str, Any]]) -> None:
    """A proven legacy difference moves the CORE_CANDIDATE at that ORIGINAL coordinate to CONFLICT_REVIEW."""

    differing = {tuple((r.get("original_cell") or {}).get(k) for k in
                       ("page_json_version_id", "section_ordinal", "table_ordinal", "row_ordinal", "column_ordinal"))
                 for r in legacy if str(r.get("class", "")).startswith("LEGACY_DIFFERS:")}
    for observation in observations:
        origin = observation["cell"].get("original_cell") or {}
        key = tuple(origin.get(k) for k in ("page_json_version_id", "section_ordinal", "table_ordinal", "row_ordinal", "column_ordinal"))
        if observation["class"] == "CORE_CANDIDATE" and key in differing:
            observation["class"], observation["legacy_conflict"] = "CONFLICT_REVIEW", True
