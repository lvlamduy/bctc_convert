"""Pure attachment of an authenticated F36 ledger, never financial admission.

The caller must authenticate the ledger summary/observations and their complete
producer/source closure BEFORE calling this module. Pinned refs here are retained
provenance declarations; this pure module performs no file/content authentication.
Records have the actual f36_strict_ledger_v1 classifier shape (no format field).
All original cell fields, order and non-OPEX cells survive exactly. Eligibility
is an opt-in export selection, not a replacement acceptance or canonical seal.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.notes.f36_strict_ledger_v1 import LEDGER_FORMAT
from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

FAMILY = "OPERATING_EXPENSE"
_ADDED = {"ledger_class", "ledger_evidence"}
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PREFIXES = ("ACCEPTED_LOCAL_NOT_ROOT_CLOSED:", "ACCEPTED_IDENTITY_UNPROVEN:", "HOLD:")
_CLASSES = {"CORE_CANDIDATE", "ACCEPTED_SOURCE_ONLY", "ACCEPTED_PRINTED_BLANK_OR_DASH",
            "DUPLICATE_IDENTICAL_CONTROL", "CONFLICT_REVIEW"}


class LedgerProjectionError(ValueError):
    """An incomplete, ambiguous or inconsistent ledger attachment."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerProjectionError(message)


def _refs_v1(refs: Any) -> dict[str, Any]:
    _need(type(refs) is dict and set(refs) == {"summary", "observations"}, "Ledger input refs incomplete")
    for ref in refs.values():
        _need(type(ref) is dict and set(ref) == {"path", "sha256", "size_bytes"}, "Malformed ledger input ref")
        _need(type(ref["path"]) is str and bool(ref["path"].strip())
              and type(ref["sha256"]) is str and _SHA256.fullmatch(ref["sha256"]) is not None
              and type(ref["size_bytes"]) is int and ref["size_bytes"] > 0, "Malformed ledger ref axes")
    return canonical_clone_v1(refs)


def _numeric_v1(cell: dict[str, Any]) -> bool:
    # Existing notes states; do not parse raw text, change values or infer zero.
    if cell.get("observation_state") not in {"VALUE", "PRINTED_ZERO"} or type(cell.get("value")) is not str:
        return False
    try:
        number = Decimal(cell["value"])
        return number.is_finite() and (cell["observation_state"] != "PRINTED_ZERO" or number.is_zero())
    except InvalidOperation:
        return False


def _record_v1(record: Any) -> tuple[bytes, str]:
    _need(type(record) is dict and {"cell", "class", "exact_rnid_binding"} <= set(record)
          and set(record) <= {"cell", "class", "exact_rnid_binding", "lane_closure", "legacy_conflict"},
          "Malformed observation classification record")
    cell, label = record["cell"], record["class"]
    _need(type(cell) is dict and cell.get("family") == FAMILY and not (_ADDED & set(cell)),
          "Classification is not an original OPEX cell")
    _need(type(label) is str and (label in _CLASSES or any(
        label.startswith(prefix) and len(label) > len(prefix) for prefix in _PREFIXES)), "Unknown ledger class")
    binding = record["exact_rnid_binding"]
    _need(binding is None or (type(binding) is int and binding > 0), "Malformed exact RNID binding")
    if "legacy_conflict" in record:
        _need(type(record["legacy_conflict"]) is bool and record["legacy_conflict"] is True
              and label == "CONFLICT_REVIEW", "Unexpected legacy conflict marker")
    acceptance = cell.get("acceptance")
    if label == "ACCEPTED_PRINTED_BLANK_OR_DASH":
        _need((acceptance, cell.get("observation_state")) in
              {("ACCEPTED_BLANK", "BLANK"), ("ACCEPTED_DASH", "DASH")}
              and cell.get("value") is None, "Blank/dash classification differs from cell")
    elif label == "DUPLICATE_IDENTICAL_CONTROL":
        _need(acceptance == label, "Control classification differs from cell")
    elif label.startswith("HOLD:"):
        reasons = cell.get("hold_reasons")
        _need(acceptance == "HOLD" and type(reasons) is list, "Hold classification differs from cell")
        first = str(reasons[0]).split(":")[0] if reasons else "NO_REASON_RECORDED"
        _need(label == "HOLD:" + first, "Hold reason differs from classifier record")
    else:
        _need(acceptance == "ACCEPTED", "Valued classification differs from cell acceptance")
    if label in {"CORE_CANDIDATE", "ACCEPTED_SOURCE_ONLY", "CONFLICT_REVIEW"}:
        _need(record.get("lane_closure") == "ROOT_CLOSED" and _numeric_v1(cell),
              "Closed valued classification lacks numeric/closure axes")
        _need(type(cell.get("report_norm_id")) is type(binding) and cell.get("report_norm_id") == binding,
              "Cell RNID differs from exact binding")
        _need((binding is None) == (label == "ACCEPTED_SOURCE_ONLY"), "Wrong source-only/core binding class")
        if label == "CONFLICT_REVIEW":
            _need(record.get("legacy_conflict") is True, "Conflict review lacks explicit conflict evidence")
    return canonical_json_bytes_v1(cell), label


def attach_f36_ledger_v1(cells: list[dict[str, Any]], classifications: list[dict[str, Any]], *,
                         ledger_input_refs: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach exactly one full-cell-matching classifier record per OPEX cell.

    Record order may differ; output order always follows the entire input store.
    Missing/duplicate/extra records and reserved-field collisions fail atomically.
    Returned trees borrow no mutable input containers. Ref validation is structural
    only and must not be described as authentication of the referenced bytes.
    """

    _need(type(cells) is list and type(classifications) is list, "Cell/classification axes must be lists")
    refs = _refs_v1(ledger_input_refs)
    by_cell = {}
    for record in classifications:
        key, label = _record_v1(record)
        _need(key not in by_cell, "Duplicate ledger classification")
        by_cell[key] = (record, label)
    out, seen = [], set()
    for cell in cells:
        _need(type(cell) is dict and not (_ADDED & set(cell)), "Preexisting ledger fields or malformed cell")
        key = canonical_json_bytes_v1(cell)
        result = canonical_clone_v1(cell)
        if cell.get("family") == FAMILY:
            _need(key not in seen, "Duplicate OPEX store cell")
            _need(key in by_cell, "Missing exact full-cell ledger classification")
            seen.add(key)
            record, label = by_cell.pop(key)
            result.update(ledger_class=label, ledger_evidence={
                "ledger_format": LEDGER_FORMAT,
                "classification": canonical_clone_v1(record),
                "input_refs": canonical_clone_v1(refs),
                "authentication_performed": False,
            })
        out.append(result)
    _need(not by_cell, "Extra ledger classifications outside the store OPEX axis")
    return out


def strict_f36_core_eligibility_v1(cells: list[dict[str, Any]]) -> list[bool]:
    """Aligned opt-in TM-value eligibility; not acceptance and no cells are dropped.

    Every OPEX cell must have an intact attachment. All non-core classes remain
    visible to the caller as distinct ledger classes; none gains a numeric grant.
    Non-OPEX cells return False and retain their separate exporter policy.
    """

    _need(type(cells) is list, "Projected cell axis must be a list")
    eligible = []
    for cell in cells:
        _need(type(cell) is dict, "Malformed projected cell")
        if cell.get("family") != FAMILY:
            _need(not (_ADDED & set(cell)), "Non-OPEX cell has an unexpected F36 attachment")
            eligible.append(False)
            continue
        evidence = cell.get("ledger_evidence")
        _need(type(evidence) is dict and set(evidence) == {
            "ledger_format", "classification", "input_refs", "authentication_performed"}, "Missing/malformed attachment")
        _need(evidence["ledger_format"] == LEDGER_FORMAT and evidence["authentication_performed"] is False,
              "Unexpected ledger format or authentication claim")
        _refs_v1(evidence["input_refs"])
        key, label = _record_v1(evidence["classification"])
        original = {name: value for name, value in cell.items() if name not in _ADDED}
        _need(key == canonical_json_bytes_v1(original) and cell.get("ledger_class") == label,
              "Attachment or original cell changed after joining")
        eligible.append(label == "CORE_CANDIDATE")
    return eligible
