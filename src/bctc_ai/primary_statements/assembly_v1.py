"""Statement census, table classification, continuation assembly and logical rows.

Gemini metadata (``content_kind``/``statement_type``/``row_kind``/hierarchy) is
a retrieval hint only. A table belongs to a statement when its own rows carry
that statement's catalog fingerprint; metadata that contradicts strong content
is a veto. Tables are joined into one statement instance only when they are
the same statement, adjacent in document order, have the same number of value
lanes and do not restart a fingerprint already seen (a restart starts a new
instance: a duplicate presentation or another scope). Every source row is kept
with its exact locator; fragments are merged only when their cells are
byte-identical or one side is blank, and the merge is recorded.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.primary_statements.catalog_v1 import PrimaryCatalog
from bctc_ai.primary_statements.numbers_v1 import (
    SeparatorRoles,
    evidence_roles_v1,
    parse_money_cell_v1,
)
from bctc_ai.primary_statements.periods_v1 import (
    duration_lane_period_v1,
    instant_lane_period_v1,
    printed_dates_v1,
    statement_period_context_v1,
)
from bctc_ai.primary_statements.text_v1 import fold_vietnamese, label_key_v1
from bctc_ai.primary_statements.units_v1 import (
    PERCENT,
    VND_PER_SHARE,
    units_in_header_component_v1,
    units_in_prose_v1,
    units_in_unit_field_v1,
)

ASSEMBLY_VERSION = "PRIMARY_STATEMENT_ASSEMBLY_V1"
STATEMENT_OF_TYPE = {"BALANCE_SHEET": "CDKT", "INCOME_STATEMENT": "KQKD", "CASH_FLOW": "LCTT"}
_TITLE_HINTS = {
    "CDKT": ("bao cao tinh hinh tai chinh", "bang can doi ke toan", "ngoai bao cao tinh hinh tai chinh"),
    "KQKD": ("bao cao ket qua hoat dong", "bao cao ket qua kinh doanh"),
    "LCTT": ("bao cao luu chuyen tien te",),
}
_NOTE_TITLE = re.compile(r"\bthuyet minh\b")
_ENUM_PATTERNS = (
    ("SECTION_LETTER", re.compile(r"\A([A-H])(?:[.)\-:]\s*|\s+)(?=\S)")),
    ("ROMAN", re.compile(r"\A((?:X{0,3})(?:IX|IV|V?I{1,3}|V|X))(?:[.)\-:/]\s*|\s+)(?=\S)", re.IGNORECASE)),
    ("DOTTED", re.compile(r"\A(\d{1,2}\.\d{1,2}|[a-z]\.\d{1,2})(?:[.)\-:]\s*|\s+)(?=\S)")),
    ("ARABIC", re.compile(r"\A(\d{1,3})(?:[.)\-:/]\s*|\s+)(?=\S)")),
    ("LETTER", re.compile(r"\A([a-hk-z])(?:[.)\-:]\s*|\s+)(?=\S)")),
    ("BULLET", re.compile(r"\A([-+▪•·◦●–—])\s*(?=\S)")),
)
_STANDALONE_ENUM = re.compile(r"\A\s*\(?([A-Ha-h]|[IVXivx]{1,4}|\d{1,3}(?:\.\d{1,2})?)\)?[.)\-:]?\s*\Z")
_LEVEL = {"SECTION_LETTER": 0, "ROMAN": 1, "ARABIC": 2, "DOTTED": 3, "LETTER": 3, "BULLET": 4}


class AssemblyError(ValueError):
    """Assembly found a contradiction it cannot represent."""


def nfc(text: str | None) -> str | None:
    return None if text is None else unicodedata.normalize("NFC", text)


def enumerator_of(text: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (enumerator token, class, remainder) of a printed label."""

    if not text:
        return None, None, text
    stripped = nfc(text).strip()
    for kind, pattern in _ENUM_PATTERNS:
        match = pattern.match(stripped)
        if match:
            token = match.group(1)
            if kind == "ROMAN" and token.islower() and len(token) == 1 and token not in "iv":
                continue
            if kind == "LETTER" and token in "ivx":
                kind = "ROMAN"
            return token, kind, stripped[match.end():]
    return None, None, stripped


def standalone_enumerator(text: str | None) -> tuple[str | None, str | None]:
    if text is None:
        return None, None
    match = _STANDALONE_ENUM.match(nfc(text))
    if not match:
        return None, None
    token = match.group(1)
    if re.fullmatch(r"[A-H]", token):
        return token, "SECTION_LETTER"
    if re.fullmatch(r"[IVXivx]{1,4}", token):
        return token, "ROMAN"
    if re.fullmatch(r"\d{1,3}", token):
        return token, "ARABIC"
    if re.fullmatch(r"\d{1,3}\.\d{1,2}", token):
        return token, "DOTTED"
    return token, "LETTER"


def label_like(text: str | None) -> bool:
    """A printed row name (not a bare enumerator, code or note reference)."""

    if not text:
        return False
    words = [word for word in re.findall(r"[^\W\d_]{2,}", nfc(text))
             if not re.fullmatch(r"[IVXivx]{1,5}", word)]
    return len(words) >= 2 or (len(words) == 1 and len(words[0]) >= 3)


# --------------------------------------------------------------------------- tables


@dataclass
class SourceTable:
    document_ordinal: int
    physical_page: int
    page_json_version_id: str
    section_ordinal: int
    table_ordinal: int
    section: dict[str, Any]
    table: dict[str, Any]
    classification: dict[str, Any] = field(default_factory=dict)

    @property
    def locator(self) -> dict[str, Any]:
        return {
            "document_ordinal": self.document_ordinal,
            "physical_page": self.physical_page,
            "page_json_version_id": self.page_json_version_id,
            "section_ordinal": self.section_ordinal,
            "table_ordinal": self.table_ordinal,
        }

    def order_key(self) -> tuple[int, int, int]:
        return self.physical_page, self.section_ordinal, self.table_ordinal


def iter_source_tables(document_ordinal: int, page: Any, page_json: dict[str, Any]) -> list[SourceTable]:
    tables = []
    for section_index, section in enumerate(page_json.get("sections") or [], 1):
        for table_index, table in enumerate(section.get("tables") or [], 1):
            tables.append(SourceTable(
                document_ordinal, page.physical_page, page.page_json_version_id,
                section_index, table_index, section, table,
            ))
    return tables


def _row_keys(table: dict[str, Any]) -> list[str]:
    keys = []
    for row in table.get("rows") or []:
        text = row.get("label_exact")
        if not label_like(text):
            for value, column in zip(row.get("values_exact") or [], table.get("columns") or [], strict=False):
                if column.get("value_kind") == "TEXT" and label_like(value):
                    text = value
                    break
        keys.append(label_key_v1(text).key)
    return keys


def classify_table_v1(source: SourceTable, catalog: PrimaryCatalog) -> dict[str, Any]:
    """Content-first statement classification of one table with explicit vetoes."""

    keys = _row_keys(source.table)
    hits = {}
    # Only keys that identify an item in exactly one statement discriminate
    # (e.g. "vốn điều lệ" names a balance-sheet line and a cash-flow line).
    owners = {
        key: {statement for statement, sc in catalog.statements.items()
              if any(hit.kind == "ITEM" for hit in sc.lookup(key))}
        for key in set(keys)
    }
    for statement, statement_catalog in catalog.statements.items():
        targets = set()
        for key in keys:
            if owners[key] != {statement}:
                continue
            for hit in statement_catalog.lookup(key):
                if hit.kind == "ITEM":
                    targets.add(hit.target)
        hits[statement] = len(targets)
    metadata = STATEMENT_OF_TYPE.get(source.section.get("statement_type") or "")
    kind = source.section.get("content_kind")
    titles = " ".join(
        fold_vietnamese(text) for text in (source.section.get("title_exact"), source.table.get("title_exact")) if text
    )
    title_hint = [statement for statement, words in _TITLE_HINTS.items() if any(w in titles for w in words)]
    if _NOTE_TITLE.search(titles):
        # "Thuyết minh báo cáo tình hình tài chính" names a note, not the statement.
        title_hint = []
    money_columns = sum(1 for column in source.table.get("columns") or [] if column.get("value_kind") == "MONEY")
    ranked = sorted(hits.items(), key=lambda item: (-item[1], item[0]))
    best, best_hits = ranked[0]
    second_hits = ranked[1][1]
    decision, reason = None, None
    if money_columns == 0:
        decision, reason = "NOT_PRIMARY", "NO_MONEY_VALUE_COLUMN"
    elif best_hits >= 3 and second_hits * 2 < best_hits:
        if metadata and metadata != best and kind == "PRIMARY_STATEMENT" and hits[metadata] >= 3:
            decision, reason = "UNRESOLVED", "METADATA_AND_CONTENT_FINGERPRINT_DISAGREE"
        elif kind != "PRIMARY_STATEMENT" and not (best in title_hint and best_hits >= 5):
            # Note tables (risk matrices, breakdowns) reuse statement row labels;
            # outside PRIMARY metadata the statement's own title is also required.
            decision, reason = "NOT_PRIMARY", "NOTE_TABLE_WITHOUT_STATEMENT_TITLE"
        else:
            decision, reason = best, "CONTENT_FINGERPRINT"
    elif best_hits >= 3:
        decision, reason = "UNRESOLVED", "AMBIGUOUS_CONTENT_FINGERPRINT"
    elif kind == "PRIMARY_STATEMENT" and metadata and (title_hint == [metadata] or hits[metadata] >= 1):
        decision, reason = metadata, "WEAK_CONTENT_WITH_PRIMARY_METADATA_AND_TITLE_OR_ANCHOR"
    elif kind == "PRIMARY_STATEMENT" and (metadata or title_hint):
        decision, reason = "UNRESOLVED", "PRIMARY_METADATA_WITHOUT_CONTENT_FINGERPRINT"
    else:
        decision, reason = "NOT_PRIMARY", "NO_PRIMARY_FINGERPRINT"
    return {
        "decision": decision,
        "reason": reason,
        "fingerprint_hits": hits,
        "metadata_statement": metadata,
        "content_kind": kind,
        "title_hints": title_hint,
        "money_columns": money_columns,
        "row_count": len(source.table.get("rows") or []),
    }


# --------------------------------------------------------------------------- rows


@dataclass
class LaneCell:
    lane: int
    column_ordinal: int
    raw: str | None
    state: str = ""
    value: str | None = None  # exact Decimal text
    qualifiers: tuple[str, ...] = ()
    separator_basis: str | None = None
    reason: str | None = None
    # Original source cell of the value (table locator + 1-based row/column), kept through
    # fragment merging; origin_status says how the logical row obtained it.
    origin: dict[str, Any] | None = None
    origin_status: str = "DIRECT_SOURCE_CELL"


@dataclass
class LogicalRow:
    instance_row_ordinal: int
    locator: dict[str, Any]
    row_ordinal: int
    label_exact: str | None
    label_source: str
    label_key: str
    label_annotations: tuple[str, ...]
    enumerator: str | None
    enumerator_class: str | None
    code: str | None
    note_ref: str | None
    row_kind: str | None
    hierarchy_path_exact: list[Any]
    cells: list[LaneCell]
    merged_fragments: list[dict[str, Any]] = field(default_factory=list)
    text_cells: list[dict[str, Any]] = field(default_factory=list)
    measure_cells: list[dict[str, Any]] = field(default_factory=list)
    parent_row: int | None = None
    parent_basis: str | None = None
    parent_conflict: dict[str, Any] | None = None
    alt_parent_row: int | None = None

    @property
    def has_numeric(self) -> bool:
        """True when any value lane prints something (parsed or, before parsing, raw)."""

        for cell in self.cells:
            if cell.state:
                if cell.state != "BLANK":
                    return True
            elif cell.raw is not None and cell.raw.strip():
                return True
        return False

    @property
    def uid(self) -> str:
        loc = self.locator
        return f"{loc['document_ordinal']}:{loc['physical_page']}:{loc['section_ordinal']}:{loc['table_ordinal']}:{self.row_ordinal}"


def _text_column_roles(table: dict[str, Any]) -> dict[int, str]:
    roles = {}
    rows = table.get("rows") or []
    for index, column in enumerate(table.get("columns") or []):
        if column.get("value_kind") != "TEXT":
            continue
        header = fold_vietnamese(" ".join(part or "" for part in column.get("header_path_exact") or []))
        cells = [row.get("values_exact")[index] for row in rows
                 if type(row.get("values_exact")) is list and len(row["values_exact"]) > index]
        present = [cell for cell in cells if cell not in (None, "")]
        labels = sum(1 for cell in present if label_like(cell))
        enums = sum(1 for cell in present if standalone_enumerator(cell)[0] is not None)
        if present and labels * 10 >= len(present) * 6:
            roles[index] = "LABEL"
        elif "thuyet minh" in header or header.strip() in {"tm", "minh", "thuyet"}:
            roles[index] = "NOTE"
        elif re.search(r"\bma\b", header):
            roles[index] = "CODE"
        elif present and enums * 10 >= len(present) * 6:
            roles[index] = "ENUMERATOR"
        elif "stt" in header or "so thu tu" in header:
            roles[index] = "ENUMERATOR"
        else:
            roles[index] = "OTHER_TEXT"
    return roles


def build_table_rows(source: SourceTable, *, start_ordinal: int) -> tuple[list[LogicalRow], list[int]]:
    """Logical rows of one table plus the source column ordinals of its value lanes."""

    table = source.table
    columns = table.get("columns") or []
    money = [index for index, column in enumerate(columns) if column.get("value_kind") == "MONEY"]
    roles = _text_column_roles(table)
    measures = [index for index, column in enumerate(columns)
                if column.get("value_kind") not in {"MONEY", "TEXT"}]
    rows: list[LogicalRow] = []
    for row_index, row in enumerate(table.get("rows") or [], 1):
        values = row.get("values_exact") if type(row.get("values_exact")) is list else []
        label_exact = nfc(row.get("label_exact"))
        label_source = "LABEL_EXACT"
        text_cells = []
        enumerator = enumerator_class = code = note = None
        label_column_text = None
        for index, role in roles.items():
            cell = nfc(values[index]) if index < len(values) else None
            text_cells.append({"column_ordinal": index + 1, "role": role, "raw": cell})
            if cell in (None, ""):
                continue
            if role == "LABEL" and label_like(cell) and label_column_text is None:
                label_column_text = cell
            elif role in {"ENUMERATOR", "LABEL", "OTHER_TEXT"} and enumerator is None:
                token, kind = standalone_enumerator(cell)
                if token:
                    enumerator, enumerator_class = token, kind
            elif role == "NOTE" and note is None:
                note = cell
            elif role == "CODE" and code is None:
                code = cell
        label = label_exact
        if not label_like(label_exact) and label_column_text:
            token, kind = standalone_enumerator(label_exact)
            if token and enumerator is None:
                enumerator, enumerator_class = token, kind
            label, label_source = label_column_text, "TEXT_COLUMN"
        prefix, prefix_class, _ = enumerator_of(label)
        if prefix and enumerator is None:
            enumerator, enumerator_class = prefix, prefix_class
        if enumerator is None and label_exact and not label_like(label_exact):
            token, kind = standalone_enumerator(label_exact)
            if token:
                enumerator, enumerator_class = token, kind
        key = label_key_v1(label) if label_like(label) else label_key_v1(None)
        cells = [LaneCell(lane, index + 1, nfc(values[index]) if index < len(values) else None,
                          origin={**source.locator, "row_ordinal": row_index, "column_ordinal": index + 1})
                 for lane, index in enumerate(money)]
        measure_cells = [
            {"column_ordinal": index + 1, "value_kind": columns[index].get("value_kind"),
             "raw": nfc(values[index]) if index < len(values) else None}
            for index in measures
        ]
        rows.append(LogicalRow(
            instance_row_ordinal=start_ordinal + len(rows),
            locator=source.locator,
            row_ordinal=row_index,
            label_exact=label,
            label_source=label_source if label_like(label) else "NONE",
            label_key=key.key,
            label_annotations=key.removed_annotations,
            enumerator=enumerator,
            enumerator_class=enumerator_class,
            code=code,
            note_ref=note,
            row_kind=row.get("row_kind"),
            hierarchy_path_exact=list(row.get("hierarchy_path_exact") or []),
            cells=cells,
            text_cells=text_cells,
            measure_cells=measure_cells,
        ))
    return _merge_fragments(rows), [index + 1 for index in money]


def _merge_fragments(rows: list[LogicalRow]) -> list[LogicalRow]:
    """Merge an enumerator-only row into the following named row when cells agree."""

    merged: list[LogicalRow] = []
    skip = False
    for index, row in enumerate(rows):
        if skip:
            skip = False
            continue
        following = rows[index + 1] if index + 1 < len(rows) else None
        if (
            following is not None
            and not row.label_key
            and row.enumerator is not None
            and following.label_key
            and following.enumerator is None
        ):
            raws_a = [cell.raw for cell in row.cells]
            raws_b = [cell.raw for cell in following.cells]
            blank_a = all(raw in (None, "") for raw in raws_a)
            blank_b = all(raw in (None, "") for raw in raws_b)
            notes_ok = row.note_ref in (None, following.note_ref) or following.note_ref is None
            if notes_ok and (raws_a == raws_b or blank_a or blank_b):
                keep = following
                keep.enumerator, keep.enumerator_class = row.enumerator, row.enumerator_class
                if blank_b and not blank_a:
                    # The values are printed on the enumerator fragment: each cell keeps that
                    # fragment's own source-cell origin, never the label row's coordinates.
                    keep.cells = row.cells
                    for cell in keep.cells:
                        cell.origin_status = "MERGED_FROM_ENUMERATOR_FRAGMENT"
                elif raws_a == raws_b and not blank_a:
                    # Both fragments print the same values: two candidate source cells for one
                    # logical cell. Not a bijection - held until proven, never chosen.
                    for cell in keep.cells:
                        if cell.raw not in (None, ""):
                            cell.origin_status = "COMPETING_IDENTICAL_FRAGMENT_CELLS"
                keep.note_ref = keep.note_ref or row.note_ref
                keep.merged_fragments.append({
                    "row_ordinal": row.row_ordinal,
                    "label_exact": row.label_exact,
                    "relation": "ENUMERATOR_FRAGMENT_IDENTICAL_CELLS" if raws_a == raws_b else "ENUMERATOR_FRAGMENT_ONE_SIDE_BLANK",
                    "cells": raws_a,
                })
                merged.append(keep)
                skip = True
                continue
        merged.append(row)
    for ordinal, row in enumerate(merged):
        row.instance_row_ordinal = rows[0].instance_row_ordinal + ordinal if rows else ordinal
    return merged


# --------------------------------------------------------------------------- instances


@dataclass
class Lane:
    index: int
    headers: list[dict[str, Any]]
    header_text: str | None
    period: dict[str, Any] | None = None
    unit: str | None = None
    unit_evidence: list[dict[str, Any]] = field(default_factory=list)
    unit_status: str | None = None
    status: str = "PENDING"
    reasons: list[str] = field(default_factory=list)


@dataclass
class StatementInstance:
    document_ordinal: int
    statement: str
    instance_ordinal: int
    tables: list[SourceTable]
    rows: list[LogicalRow] = field(default_factory=list)
    lanes: list[Lane] = field(default_factory=list)
    lane_columns: list[list[int]] = field(default_factory=list)
    scope: str | None = None
    scope_basis: dict[str, Any] = field(default_factory=dict)
    entity_text: str | None = None
    branch: str | None = None
    branch_evidence: dict[str, Any] = field(default_factory=dict)
    separator_roles: dict[str, Any] = field(default_factory=dict)
    period_context: dict[str, Any] = field(default_factory=dict)
    status: str = "ASSEMBLED"
    reasons: list[str] = field(default_factory=list)
    presentation_role: str = "PRIMARY"
    cell_vetoes: dict[tuple[int, str], str] = field(default_factory=dict)
    dash_unvalidated: set[tuple[int, int]] = field(default_factory=set)

    @property
    def key(self) -> str:
        return f"{self.document_ordinal}:{self.statement}:{self.instance_ordinal}"


def _is_carry_forward(row: LogicalRow) -> bool:
    return any(re.search(r"\b(?:mang|chuyen)\s+(?:sang|tu)\b", fold_vietnamese(item)) for item in row.label_annotations)


def _opening_candidates(rows: list[LogicalRow], catalog: PrimaryCatalog, statement: str, limit: int) -> list[set[str]]:
    """Candidate identity sets of the first valued, non-carry-forward rows."""

    found = []
    for row in rows:
        if not row.has_numeric or _is_carry_forward(row):
            continue
        targets = {hit.target for hit in catalog.statements[statement].lookup(row.label_key) if hit.kind == "ITEM"}
        if targets:
            found.append(targets)
            if len(found) >= limit:
                break
    return found


MIN_HITS_TO_START_INSTANCE = 5


def assemble_document_instances_v1(
    tables: list[SourceTable], catalog: PrimaryCatalog, *, notes_start_page: int | None = None
) -> tuple[list[StatementInstance], list[SourceTable]]:
    """Group classified tables into statement instances in document order.

    A statement-like table printed after the notes section has started is a
    note (commitment schedules, restated comparatives), not the statement. A
    table with a weak fingerprint may only continue an instance of the same
    statement on the same or the previous page; it never starts one.
    """

    tables = sorted(tables, key=SourceTable.order_key)
    instances: list[StatementInstance] = []
    others: list[SourceTable] = []
    current: dict[str, StatementInstance] = {}
    opening: dict[str, set[str]] = {}
    last_statement = None
    counts: Counter[str] = Counter()
    for source in tables:
        decision = source.classification["decision"]
        if decision in catalog.statements and notes_start_page is not None and source.physical_page > notes_start_page:
            source.classification = {**source.classification, "decision": "NOT_PRIMARY",
                                     "reason": "STATEMENT_LIKE_TABLE_AFTER_NOTES_START",
                                     "statement_candidate": decision, "notes_start_page": notes_start_page}
            decision = "NOT_PRIMARY"
        if decision in catalog.statements and source.classification["fingerprint_hits"][decision] < MIN_HITS_TO_START_INSTANCE:
            open_instance = current.get(decision)
            if open_instance is None or source.physical_page - open_instance.tables[-1].physical_page > 1:
                source.classification = {**source.classification, "decision": "NOT_PRIMARY",
                                         "reason": "WEAK_FINGERPRINT_WITHOUT_ADJACENT_INSTANCE",
                                         "statement_candidate": decision}
                decision = "NOT_PRIMARY"
        if decision not in catalog.statements:
            others.append(source)
            continue
        rows, lanes = build_table_rows(source, start_ordinal=0)
        first = _opening_candidates(rows, catalog, decision, 1)
        instance = current.get(decision)
        # A continuation page never begins with the statement's opening lines; a
        # table that does is a new presentation (another unit, scope or copy).
        restart = bool(first) and instance is not None and bool(first[0] & opening.get(instance.key, set()))
        lane_mismatch = instance is not None and instance.lane_columns and len(lanes) != len(instance.lane_columns[-1])
        interleaved = instance is not None and last_statement not in (None, decision) and _statement_complete(instance, catalog)
        if instance is None or restart or lane_mismatch or interleaved:
            counts[decision] += 1
            instance = StatementInstance(source.document_ordinal, decision, counts[decision], [])
            instances.append(instance)
            current[decision] = instance
            if lane_mismatch:
                instance.reasons.append("NEW_INSTANCE_ON_VALUE_LANE_COUNT_CHANGE")
            if restart:
                instance.reasons.append("NEW_INSTANCE_ON_FINGERPRINT_RESTART")
        offset = len(instance.rows)
        for row in rows:
            row.instance_row_ordinal += offset
        instance.tables.append(source)
        instance.rows.extend(rows)
        instance.lane_columns.append(lanes)
        opening[instance.key] = set().union(*_opening_candidates(instance.rows, catalog, decision, 3))
        last_statement = decision
    return instances, others


def _statement_complete(instance: StatementInstance, catalog: PrimaryCatalog) -> bool:
    """A statement whose closing total was already seen cannot absorb a later table."""

    closing = {"CDKT": {"4305"}, "KQKD": {"4378", "4380", "4381"}, "LCTT": {"4116", "4168"}}[instance.statement]
    for row in instance.rows:
        for hit in catalog.statements[instance.statement].lookup(row.label_key):
            if hit.kind == "ITEM" and hit.target in closing:
                return True
    return False


# --------------------------------------------------------------------------- lanes


def instance_page_sections(instance: StatementInstance, page_sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Sections printed on the instance's pages other than the statement's own sections."""

    own = {(source.page_json_version_id, source.section_ordinal) for source in instance.tables}
    result = []
    for version in dict.fromkeys(source.page_json_version_id for source in instance.tables):
        for section in page_sections.get(version, []):
            if (version, section["section_ordinal"]) not in own:
                result.append(section)
    return result


def resolve_instance_lanes_v1(
    instance: StatementInstance,
    catalog: PrimaryCatalog,
    document_roles: SeparatorRoles,
    other_page_sections: list[dict[str, Any]] | None = None,
    document_context_texts: list[str] | None = None,
) -> None:
    """Separator roles, cell parsing, lane headers, units and periods of one instance.

    Besides the statement's own sections, other non-note sections printed on
    the same pages may contribute (a) a statement title naming the period and
    (b) a unit phrase introduced by "Đơn vị"/"ĐVT". Note sections never do.
    """

    other_page_sections = [
        section for section in other_page_sections or []
        if section["content_kind"] != "FINANCIAL_NOTE"
        and STATEMENT_OF_TYPE.get(section["statement_type"] or "", instance.statement) == instance.statement
    ]

    statement_catalog = catalog.statements[instance.statement]
    lane_count = len(instance.lane_columns[0]) if instance.lane_columns else 0
    if any(len(columns) != lane_count for columns in instance.lane_columns) or lane_count == 0:
        instance.status = "UNRESOLVED"
        instance.reasons.append("INCONSISTENT_OR_ABSENT_VALUE_LANES")
    table_roles: dict[tuple[int, int, int], SeparatorRoles] = {}
    for source in instance.tables:
        roles = SeparatorRoles()
        for row in source.table.get("rows") or []:
            for value, column in zip(row.get("values_exact") or [], source.table.get("columns") or [], strict=False):
                if column.get("value_kind") == "MONEY":
                    roles = roles.merge(evidence_roles_v1(value))
        table_roles[source.order_key()] = roles
    instance_roles = SeparatorRoles()
    for roles in table_roles.values():
        instance_roles = instance_roles.merge(roles)
    instance.separator_roles = {
        "instance": instance_roles.to_dict(),
        "tables": {f"{k[0]}:{k[1]}:{k[2]}": v.to_dict() for k, v in table_roles.items()},
        "document": document_roles.to_dict(),
    }
    for row in instance.rows:
        key = (row.locator["physical_page"], row.locator["section_ordinal"], row.locator["table_ordinal"])
        roles = table_roles[key]
        for cell in row.cells:
            parsed = parse_money_cell_v1(cell.raw, roles)
            basis_scope = "TABLE"
            if parsed.state == "AMBIGUOUS_SEPARATOR" and not roles.conflicted:
                parsed = parse_money_cell_v1(cell.raw, instance_roles)
                basis_scope = "INSTANCE"
                if parsed.state == "AMBIGUOUS_SEPARATOR" and not instance_roles.conflicted:
                    parsed = parse_money_cell_v1(cell.raw, document_roles)
                    basis_scope = "DOCUMENT"
            cell.state = parsed.state
            cell.value = None if parsed.value is None else format(parsed.value, "f")
            cell.qualifiers = parsed.qualifiers
            cell.separator_basis = None if parsed.separator_basis is None else f"{basis_scope}:{parsed.separator_basis}"
            cell.reason = parsed.reason
    context_texts = []
    for source in instance.tables:
        for text in (source.table.get("title_exact"), source.section.get("title_exact")):
            if text and text not in context_texts:
                context_texts.append(text)
        for narrative in source.section.get("narratives_exact") or []:
            if narrative and narrative not in context_texts and re.search(
                r"cho\s+(?:ky|nam|quy)|tai\s+ngay|ket\s+thuc|quy\s+(?:i|ii|iii|iv|[1-4])\b", fold_vietnamese(narrative)
            ):
                context_texts.append(narrative)
    for section in other_page_sections:
        for text in [section["title"], *section["narratives"], *section["table_titles"]]:
            folded = fold_vietnamese(text or "")
            if text and text not in context_texts and re.search(r"\bbao cao\b|\bbang\b", folded) and any(
                word in folded for words in _TITLE_HINTS.values() for word in words
            ):
                context_texts.append(text)
    for text in document_context_texts or []:
        if text not in context_texts:
            context_texts.append(text)
    context = statement_period_context_v1(context_texts)
    instance.period_context = {
        "reporting_date": context.reporting_date, "months": context.months, "quarter": context.quarter,
        "year": context.year, "annual": context.annual, "range_start": context.range_start,
        "evidence": list(context.evidence), "conflict": context.conflict,
    }
    prose_units = []
    for source in instance.tables:
        prose_units += [("TABLE_UNIT_FIELD", u) for u in units_in_unit_field_v1(source.table.get("unit_exact"), source_kind="TABLE_UNIT_FIELD")]
        prose_units += [("SECTION_TITLE", u) for u in units_in_prose_v1(source.section.get("title_exact"), source_kind="SECTION_TITLE")]
        for narrative in source.section.get("narratives_exact") or []:
            prose_units += [("SECTION_NARRATIVE", u) for u in units_in_prose_v1(narrative, source_kind="SECTION_NARRATIVE")]
    for section in other_page_sections:
        for text in [section["title"], *section["narratives"]]:
            prose_units += [("PAGE_SECTION_TEXT", u) for u in units_in_prose_v1(text, source_kind="PAGE_SECTION_TEXT")]
        for text in section["table_units"]:
            prose_units += [("PAGE_TABLE_UNIT_FIELD", u) for u in units_in_prose_v1(text, source_kind="PAGE_TABLE_UNIT_FIELD")]
    def read_period(text):
        if statement_catalog.period_basis == "INSTANT":
            return instant_lane_period_v1(text, context)
        return duration_lane_period_v1(text, context)

    def header_text(source, columns, lane_index):
        column = source.table["columns"][columns[lane_index] - 1]
        return "\n".join(nfc(part) for part in column.get("header_path_exact") or [] if part) or None

    # A table whose own lane headers name the same period twice cannot say
    # which lane is which: its cells are held and its headers do not vote.
    ambiguous_tables = set()
    for source, columns in zip(instance.tables, instance.lane_columns, strict=True):
        if len(columns) != lane_count:
            continue
        keys = [read_period(text).key for text in (header_text(source, columns, i) for i in range(lane_count)) if text]
        keys = [key for key in keys if key]
        if len(keys) != len(set(keys)):
            ambiguous_tables.add(source.order_key())
    if ambiguous_tables and len(ambiguous_tables) == len({source.order_key() for source in instance.tables}):
        ambiguous_tables = set()
    instance.lanes = []
    for lane_index in range(lane_count):
        headers = []
        for source, columns in zip(instance.tables, instance.lane_columns, strict=True):
            column = source.table["columns"][columns[lane_index] - 1]
            parts = [nfc(part) for part in column.get("header_path_exact") or [] if part]
            headers.append({"table": source.locator, "column_ordinal": columns[lane_index], "header_path_exact": parts,
                            "period_ambiguous_table": source.order_key() in ambiguous_tables})
        texts = ["\n".join(item["header_path_exact"]) for item in headers
                 if item["header_path_exact"] and not item["period_ambiguous_table"]]
        lane = Lane(lane_index, headers, texts[0] if texts else None)
        descriptors = []
        for text in dict.fromkeys(texts):
            descriptors.append(read_period(text))
        keys = {d.key for d in descriptors}
        if not descriptors:
            lane.period = {"basis": "UNRESOLVED", "key": None, "resolution": "UNRESOLVED", "reason": "NO_PRINTED_LANE_HEADER"}
            lane.reasons.append("PERIOD_UNRESOLVED")
        elif None in keys:
            lane.period = next(d.to_dict() for d in descriptors if d.key is None)
            lane.reasons.append("PERIOD_UNRESOLVED")
        elif len(keys) > 1:
            lane.period = {"basis": "UNRESOLVED", "key": None, "resolution": "UNRESOLVED",
                           "reason": "CONTINUATION_HEADERS_DISAGREE", "candidates": sorted(keys)}
            lane.reasons.append("PERIOD_CONFLICT")
        else:
            lane.period = descriptors[0].to_dict()
            if len(texts) < len(headers):
                lane.period["continuation_inherited_tables"] = len(headers) - len(texts)
        header_units = []
        for item in headers:
            for part in item["header_path_exact"]:
                header_units += [{"unit": u.unit, "source_kind": u.source_kind, "source_text": u.source_text}
                                 for u in units_in_header_component_v1(part)]
        evidence = header_units + [
            {"unit": u.unit, "source_kind": kind, "source_text": u.source_text} for kind, u in prose_units
        ]
        lane.unit_evidence = evidence
        money_units = {item["unit"] for item in evidence if item["unit"] not in {PERCENT, VND_PER_SHARE}}
        if len(money_units) == 1:
            lane.unit, lane.unit_status = next(iter(money_units)), "RESOLVED"
        elif len(money_units) > 1:
            lane.unit_status = "CONFLICT"
            lane.reasons.append("UNIT_CONFLICT")
        else:
            lane.unit_status = "UNRESOLVED"
            lane.reasons.append("UNIT_UNRESOLVED")
        lane.status = "RESOLVED" if not lane.reasons else "UNRESOLVED"
        instance.lanes.append(lane)
    for row in instance.rows:
        key = (row.locator["physical_page"], row.locator["section_ordinal"], row.locator["table_ordinal"])
        if key in ambiguous_tables:
            for cell in row.cells:
                if cell.state in {"VALUE", "PRINTED_ZERO", "DASH"}:
                    cell.state, cell.value = "PERIOD_AMBIGUOUS", None
                    cell.reason = "SOURCE_TABLE_LANE_HEADERS_NAME_ONE_PERIOD_TWICE"
    keys = [lane.period.get("key") for lane in instance.lanes if lane.period and lane.period.get("key")]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    for lane in instance.lanes:
        if lane.period and lane.period.get("key") in duplicates:
            lane.status = "UNRESOLVED"
            lane.reasons.append("DUPLICATE_PERIOD_LANE")


def rebind_document_period_context_v1(
    instances: list[StatementInstance],
    catalog: PrimaryCatalog,
    document_roles: SeparatorRoles,
    page_sections_of,
) -> None:
    """Bind a statement whose own pages print no reporting year to the report's date.

    Applies only when the statement's own printed context has no date, year,
    range or conflict, and every other statement of the document that prints
    a reporting date prints the same single date. Lanes are re-read with those
    printed statement titles as context; the result is kept only if it
    resolves more lanes, without conflict, and every quarter in the lane keys
    is the calendar quarter of that date. The instance records the donors.
    """

    donors = [i for i in instances if i.period_context.get("reporting_date") and not i.period_context.get("conflict")]
    dates = {i.period_context["reporting_date"] for i in donors}
    if len(dates) != 1:
        return
    date = next(iter(dates))
    quarter = (int(date[5:7]) + 2) // 3
    for instance in instances:
        context = instance.period_context
        if any(context.get(key) for key in ("reporting_date", "year", "conflict", "range_start")):
            continue
        unresolved = sum("PERIOD_UNRESOLVED" in lane.reasons for lane in instance.lanes)
        donor_texts = [text for donor in donors if donor.statement != instance.statement
                       for text in donor.period_context["evidence"] if date in printed_dates_v1(text)]
        if not unresolved or not donor_texts:
            continue
        before = (instance.lanes, instance.period_context, list(instance.reasons))
        resolve_instance_lanes_v1(instance, catalog, document_roles, page_sections_of(instance), list(dict.fromkeys(donor_texts)))
        keys = [(lane.period or {}).get("key") or "" for lane in instance.lanes]
        quarters = {int(m.group(1)) for key in keys for m in re.finditer(r"(?:QUARTER:|YTD:Q)(\d)", key)}
        if (instance.period_context.get("conflict") or quarters - {quarter}
                or sum("PERIOD_UNRESOLVED" in lane.reasons for lane in instance.lanes) >= unresolved):
            instance.lanes, instance.period_context, instance.reasons = before
            continue
        instance.period_context["document_context"] = {
            "basis": "DOCUMENT_PRIMARY_STATEMENT_REPORTING_DATE", "reporting_date": date,
            "donor_instances": sorted({d.key for d in donors if d.statement != instance.statement}),
        }


_FORM_CODE = re.compile(r"\bb0[1-5]a?\s*/\s*tctd(?P<hn>\s*[-–]\s*hn)?\b")


def resolve_instance_scope_v1(
    instance: StatementInstance, document_titles: list[str], page_texts: list[str] | None = None
) -> None:
    """Consolidated/separate scope from printed titles or the printed form code.

    Order of evidence: the statement's own titles; the printed statement form
    code on the statement pages ("B02a/TCTD-HN" consolidated, "B02a/TCTD"
    separate); the document's financial-statement titles. Contradictions veto.
    """

    def scopes_in(texts: list[str]) -> set[str]:
        found = set()
        for text in texts:
            folded = fold_vietnamese(text)
            if "hop nhat" in folded:
                found.add("CONSOLIDATED")
            if re.search(r"\brieng(?: le)?\b", folded) or "cong ty me" in folded or "ngan hang me" in folded:
                found.add("SEPARATE")
        return found

    own = [text for source in instance.tables for text in (source.section.get("title_exact"), source.table.get("title_exact")) if text]
    found = scopes_in(own)
    basis = "STATEMENT_TITLE"
    if not found and page_texts:
        forms = set()
        form_texts = []
        for text in page_texts:
            for match in _FORM_CODE.finditer(fold_vietnamese(text)):
                forms.add("CONSOLIDATED" if match.group("hn") else "SEPARATE")
                form_texts.append(text)
        if forms:
            found, basis, own = forms, "PRINTED_STATEMENT_FORM_CODE", form_texts
    if not found:
        doc = [text for text in document_titles if "bao cao tai chinh" in fold_vietnamese(text) or "bctc" in fold_vietnamese(text)]
        found = scopes_in(doc)
        basis = "DOCUMENT_FINANCIAL_STATEMENT_TITLES"
        own = doc
    if len(found) == 1:
        instance.scope = next(iter(found))
        instance.scope_basis = {"basis": basis, "evidence": own[:6]}
    else:
        instance.scope = None
        instance.scope_basis = {"basis": basis, "evidence": own[:6], "found": sorted(found),
                                "reason": "SCOPE_CONFLICT" if found else "NO_PRINTED_SCOPE"}
        instance.reasons.append("SCOPE_UNRESOLVED")
    for source in instance.tables:
        for text in [source.section.get("title_exact"), *(source.section.get("narratives_exact") or [])]:
            if text and fold_vietnamese(text).startswith("ngan hang"):
                instance.entity_text = nfc(text.split("\n")[0])
                return


def resolve_document_scope_v1(instances: list[StatementInstance], document_titles: list[str]) -> None:
    """Propagate one report's scope to its statements lacking their own evidence.

    1. Statements of one document form one report: a single scope proven by
       another statement's own title or printed form code applies to the rest.
    2. If no title anywhere in the document mentions consolidation ("hợp
       nhất") after scanning every section title, and the document prints
       financial-statement or note titles, the report is not consolidated; the
       scope is SEPARATE with an explicit absence basis. Contradictions veto.
    """

    proven = {i.scope for i in instances
              if i.scope and i.scope_basis.get("basis") in {"STATEMENT_TITLE", "PRINTED_STATEMENT_FORM_CODE"}}
    folded_titles = [fold_vietnamese(text) for text in document_titles]
    for instance in instances:
        if instance.scope is not None:
            continue
        if instance.scope_basis.get("reason") == "SCOPE_CONFLICT":
            # Propagation fills absent evidence only; the statement's own
            # contradictory titles stay a veto.
            continue
        if len(proven) == 1:
            instance.scope = next(iter(proven))
            instance.scope_basis = {"basis": "DOCUMENT_PRIMARY_STATEMENT_SCOPE",
                                    "evidence": sorted({i.key for i in instances if i.scope == instance.scope and i is not instance})}
        elif not proven and not any("hop nhat" in text for text in folded_titles) and any(
            "bao cao tai chinh" in text or "thuyet minh" in text for text in folded_titles
        ):
            instance.scope = "SEPARATE"
            instance.scope_basis = {"basis": "NO_CONSOLIDATION_MARKER_AFTER_FULL_DOCUMENT_TITLE_SCAN",
                                    "titles_scanned": len(folded_titles)}
        else:
            continue
        instance.reasons = [reason for reason in instance.reasons if reason != "SCOPE_UNRESOLVED"]


def resolve_cash_flow_branch_v1(instance: StatementInstance, rules_path, catalog: PrimaryCatalog) -> None:
    """DIRECT/INDIRECT from the lctt-v2 ordered ReportNormId anchor sequences.

    Rows are matched to anchor identities through the catalog (any branch), so
    wording variants of the anchors are recognized; the configured order and
    maximum distance still apply. The legacy substring classifier is recorded
    as corroboration. Both or neither branch observed is a hold.
    """

    if instance.statement != "LCTT":
        return
    import yaml

    rules_payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    distance = rules_payload["maximum_anchor_distance"]
    statement_catalog = catalog.statements["LCTT"]
    candidates = [
        {int(hit.target) for hit in statement_catalog.lookup(row.label_key) if hit.kind == "ITEM"}
        for row in instance.rows
    ]

    def ordered(sequence: list[int]) -> list[int] | None:
        for start, ids in enumerate(candidates):
            if sequence[0] not in ids:
                continue
            positions, previous = [start], start
            for anchor in sequence[1:]:
                found = next((i for i in range(previous + 1, min(len(candidates), previous + distance + 1))
                              if anchor in candidates[i]), None)
                if found is None:
                    break
                positions.append(found)
                previous = found
            if len(positions) == len(sequence):
                return positions
        return None

    observed = {}
    for branch in ("DIRECT", "INDIRECT"):
        for sequence in rules_payload["branches"][branch]["ordered_anchor_sequences"]:
            positions = ordered(list(sequence))
            if positions is not None:
                observed[branch] = {"sequence": list(sequence), "row_positions": positions}
                break
    legacy = classify_cash_flow_method([row.label_exact or "" for row in instance.rows], load_cash_flow_rules(rules_path))
    if len(observed) == 1:
        instance.branch = next(iter(observed))
    else:
        instance.branch = "BOTH" if observed else "UNKNOWN"
        instance.reasons.append("CASH_FLOW_BRANCH_UNRESOLVED")
    instance.branch_evidence = {
        "method": instance.branch,
        "ordered_reportnormid_anchors": observed,
        "legacy_label_substring_classifier": legacy.method.value,
        "rules_path": "config/mapping/lctt-v2.yaml",
    }


# --------------------------------------------------------------------------- hierarchy


def assign_parents_v1(instance: StatementInstance) -> None:
    """Source parent of every row: printed numbering first, Gemini path second.

    Income statements print subtotals below their components, so printed
    numbering there is not a header hierarchy; only an explicit Gemini path is
    used and it is recorded as a proposal.
    """

    # The parent is the nearest preceding row whose own full path is this row's
    # path prefix; matching only the parent label would confuse a parent with a
    # same-named child ("Cho vay khách hàng" > "Cho vay khách hàng").
    by_path: dict[tuple[str, ...], int] = {}
    stack: list[tuple[int, int]] = []  # (level, row index)
    numbering_is_header_hierarchy = instance.statement in {"CDKT", "LCTT"}
    for index, row in enumerate(instance.rows):
        path = tuple(label_key_v1(str(part)).key or fold_vietnamese(str(part)) for part in row.hierarchy_path_exact if part)
        path_parent = None
        for cut in range(len(path) - 1, 0, -1):
            if path[:cut] in by_path:
                path_parent = by_path[path[:cut]]
                break
        enum_parent = None
        level = _LEVEL.get(row.enumerator_class or "")
        if numbering_is_header_hierarchy and level is not None:
            while stack and stack[-1][0] >= level:
                stack.pop()
            enum_parent = stack[-1][1] if stack else None
            stack.append((level, index))
        if enum_parent is not None or (numbering_is_header_hierarchy and level is not None):
            row.parent_row, row.parent_basis = enum_parent, "PRINTED_NUMBERING"
            if path_parent is not None and path_parent != enum_parent:
                row.parent_conflict = {"gemini_path_parent": path_parent, "numbering_parent": enum_parent}
                row.alt_parent_row = path_parent
        elif path_parent is not None:
            row.parent_row, row.parent_basis = path_parent, "GEMINI_HIERARCHY_PATH"
        elif numbering_is_header_hierarchy and stack and not _heading_or_total(row) \
                and _sibling_follows(instance.rows, index, stack[-1][1]):
            # An unnumbered run printed between two same-level numbered siblings
            # belongs to the preceding numbered row (e.g. "Cam kết mua ngoại tệ"
            # between "2 Cam kết giao dịch hối đoái" and "3 ...").
            row.parent_row, row.parent_basis = stack[-1][1], "UNNUMBERED_BETWEEN_NUMBERED_SIBLINGS"
        else:
            row.parent_row, row.parent_basis = None, "TOP_LEVEL_OR_UNSTATED"
        if path:
            by_path[path] = index


def _heading_or_total(row: LogicalRow) -> bool:
    """Upper-case headings and "Tổng ..." totals never hang under a numbered item."""

    letters = [ch for ch in (row.label_exact or "") if ch.isalpha()]
    upper = bool(letters) and sum(ch.isupper() for ch in letters) >= 0.8 * len(letters)
    return upper or row.label_key.startswith("tong ") or row.label_key == "tong cong"


def _sibling_follows(rows: list[LogicalRow], index: int, numbered: int) -> bool:
    kind = rows[numbered].enumerator_class
    if kind not in {"ROMAN", "ARABIC", "LETTER", "DOTTED"}:
        return False
    for following in rows[index + 1:]:
        if following.enumerator_class is not None:
            return following.enumerator_class == kind
    return False
