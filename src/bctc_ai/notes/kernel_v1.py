"""Stable kernel for notes digitization (public API used by every plugin).

* Source: the corpus selection is authenticated by ``primary_statements.source_v1``
  (index SHA, selection heads, manifests, database SHA). Note tables are then
  read from the normalized nodes of that pinned, immutable database with a few
  batched SQL queries: retrieval first (indexed folded labels), then only the
  candidate tables are loaded.
* Document context comes from the accepted PRIMARY result store (pinned SHA):
  scope, balance-sheet lane periods and accepted primary cells, so notes use
  the same scope/period identities as the statements they explain.
* Cells, units and periods reuse the PRIMARY parsers: no blank-to-zero, no
  unit from magnitude, no year arithmetic.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles, evidence_roles_v1, parse_money_cell_v1
from bctc_ai.primary_statements.periods_v1 import (
    instant_lane_period_v1,
    printed_dates_v1,
    statement_period_context_v1,
)
from bctc_ai.primary_statements.source_v1 import CorpusSelection, SourceMetrics, connect_readonly, sha256_file
from bctc_ai.primary_statements.text_v1 import fold_vietnamese, label_key_v1
from bctc_ai.primary_statements.units_v1 import (
    PERCENT,
    VND_PER_SHARE,
    units_in_header_component_v1,
    units_in_prose_v1,
    units_in_unit_field_v1,
)

KERNEL_VERSION = "NOTES_KERNEL_V1"


class NotesKernelError(ValueError):
    pass


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise NotesKernelError(message)


# --------------------------------------------------------------------------- primary context


@dataclass
class DocumentContext:
    """What the accepted primary statements of one document establish."""

    ordinal: int
    document_plan_id: str
    relative_path: str
    source_sha256: str
    scope: str | None
    scope_basis: str
    reporting_date: str | None
    balance_lanes: list[dict[str, Any]]
    context_texts: list[str]
    primary_cells: dict[tuple[str, int, str], tuple[Decimal, str]]
    separator_roles: SeparatorRoles = field(default_factory=SeparatorRoles)

    def balance_lane_keys(self, role: str) -> list[str]:
        return [lane["key"] for lane in self.balance_lanes if lane["role"] == role and lane["key"]]


def load_primary_context_v1(store_path: Path, expected_sha256: str) -> dict[int, DocumentContext]:
    _require(sha256_file(store_path) == expected_sha256, "PRIMARY result store SHA-256 drifted")
    contexts: dict[int, DocumentContext] = {}
    with closing(connect_readonly(store_path)) as connection:
        for row in connection.execute("SELECT document_ordinal, result_json FROM document_result ORDER BY document_ordinal"):
            result = json.loads(row["result_json"])
            document = result["document"]
            primary = [i for i in result["instances"] if i["presentation_role"] == "PRIMARY"]
            scopes = {i["scope"] for i in primary if i["scope"]}
            scope = next(iter(scopes)) if len(scopes) == 1 and all(i["scope"] for i in primary) else None
            balance = [i for i in primary if i["statement"] == "CDKT"]
            lanes, texts, dates = [], [], set()
            if len(balance) == 1:
                for lane in balance[0]["lanes"]:
                    period = lane.get("period") or {}
                    lanes.append({"key": period.get("key"), "role": period.get("role"), "header": lane.get("header_text")})
                    if period.get("role") == "CURRENT" and re.fullmatch(r"INSTANT:\d{4}-\d{2}-\d{2}", period.get("key") or ""):
                        dates.add(period["key"][8:])
                texts = list(balance[0]["period_context"].get("evidence") or [])
            roles = SeparatorRoles()
            for instance in primary:
                document_roles = (instance.get("separator_roles") or {}).get("document") or {}
                roles = roles.merge(SeparatorRoles(frozenset(document_roles.get("thousands", [])),
                                                   frozenset(document_roles.get("decimal", []))))
            cells = {}
            for cell in result["cells"]:
                if cell["acceptance"] == "ACCEPTED" and cell["value"] is not None and cell["period_key"]:
                    cells[(cell["statement"], cell["report_norm_id"], cell["period_key"])] = (Decimal(cell["value"]), cell["unit"])
            contexts[document["document_ordinal"]] = DocumentContext(
                ordinal=document["document_ordinal"], document_plan_id=document["document_plan_id"],
                relative_path=document["relative_path"], source_sha256=document["source_sha256"],
                scope=scope, scope_basis="PRIMARY_DOCUMENT_SCOPE" if scope else "PRIMARY_SCOPE_NOT_UNIQUE",
                reporting_date=next(iter(dates)) if len(dates) == 1 else None,
                balance_lanes=lanes, context_texts=texts, primary_cells=cells, separator_roles=roles,
            )
    return contexts


# --------------------------------------------------------------------------- note tables


@dataclass
class NoteColumn:
    column_id: str
    ordinal: int
    header_path: tuple[str, ...]
    value_kind: str

    @property
    def header_text(self) -> str:
        return "\n".join(part for part in self.header_path if part)


@dataclass
class NoteRow:
    row_id: str
    order: int
    label: str | None
    kind: str
    hierarchy: tuple[str, ...]
    parent_row_id: str | None

    @property
    def key(self) -> str:
        return label_key_v1(self.label).key if self.label else ""


@dataclass
class NoteTable:
    document_ordinal: int
    physical_page: int
    page_json_version_id: str
    section_id: str
    table_id: str
    section_order: int
    table_order: int
    content_kind: str
    section_title: str | None
    table_title: str | None
    unit_exact: str | None
    continuation: str
    narratives: list[str]
    columns: list[NoteColumn] = field(default_factory=list)
    rows: list[NoteRow] = field(default_factory=list)
    cells: dict[tuple[str, str], tuple[str | None, str]] = field(default_factory=dict)
    fragments: list[dict[str, Any]] = field(default_factory=list)
    section_table_count: int = 1
    sibling_unit: dict[str, Any] | None = None   # inherited-unit proof from an earlier table of the same section

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.page_json_version_id, self.section_id, self.table_id)

    def locator(self) -> dict[str, Any]:
        return {"document_ordinal": self.document_ordinal, "physical_page": self.physical_page,
                "page_json_version_id": self.page_json_version_id, "section_id": self.section_id,
                "table_id": self.table_id}

    def separator_roles(self) -> SeparatorRoles:
        roles = SeparatorRoles()
        for (row_id, column_id), (text, _state) in self.cells.items():
            roles = roles.merge(evidence_roles_v1(text))
        return roles


_NOTE_HEADING = re.compile(r"\A\s*(?:[ivxlc]+|\d+(?:\.\d+)*)\s*[.)]?\s+\S", re.IGNORECASE)


class NotesSource:
    """Batched, read-only access to the selected pages of one authenticated corpus."""

    def __init__(self, corpus: CorpusSelection, metrics: SourceMetrics | None = None):
        self.corpus = corpus
        self.metrics = metrics or SourceMetrics()
        self.page_of: dict[str, tuple[int, int]] = {
            page.page_json_version_id: (document.ordinal, page.physical_page)
            for document in corpus.documents for page in document.pages
        }
        self._outline: dict[int, list[dict[str, Any]]] | None = None

    def _connect(self):
        connection = connect_readonly(self.corpus.db_path)
        connection.execute("CREATE TEMP TABLE notes_selected(v TEXT PRIMARY KEY)")
        connection.executemany("INSERT INTO notes_selected VALUES (?)", [(v,) for v in self.page_of])
        return connection

    def candidate_tables(self, like_patterns: Iterable[str]) -> dict[tuple[str, str, str], int]:
        """Tables of selected pages having rows whose folded label matches a pattern."""

        patterns = list(like_patterns)
        _require(patterns, "retrieval needs at least one pattern")
        where = " OR ".join("r.label_ascii_folded LIKE ?" for _ in patterns)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""SELECT r.page_json_version_id, r.section_id, r.table_id, COUNT(*) AS hits
                    FROM row_node AS r JOIN notes_selected AS s ON s.v = r.page_json_version_id
                    WHERE {where} GROUP BY 1, 2, 3""", patterns,
            ).fetchall()
        self.metrics.sql_queries += 1
        self.metrics.rows_read += len(rows)
        return {(row[0], row[1], row[2]): row[3] for row in rows}

    def load_tables(self, keys: Iterable[tuple[str, str, str]]) -> list[NoteTable]:
        keys = sorted(set(keys), key=lambda k: (self.page_of[k[0]], k[1], k[2]))
        if not keys:
            return []
        tables: dict[tuple[str, str, str], NoteTable] = {}
        with closing(connect_readonly(self.corpus.db_path)) as connection:
            connection.execute("CREATE TEMP TABLE notes_keys(v TEXT, s TEXT, t TEXT, PRIMARY KEY (v, s, t))")
            connection.executemany("INSERT INTO notes_keys VALUES (?,?,?)", keys)
            for row in connection.execute(
                """SELECT t.page_json_version_id, t.section_id, t.table_id, n.source_order, t.source_order,
                          n.content_kind, n.title_exact, t.title_exact, t.unit_exact, t.continuation, n.narratives_json
                   FROM notes_keys AS k
                   JOIN table_node AS t ON t.page_json_version_id = k.v AND t.section_id = k.s AND t.table_id = k.t
                   JOIN section_node AS n ON n.page_json_version_id = t.page_json_version_id AND n.section_id = t.section_id"""
            ):
                ordinal, page = self.page_of[row[0]]
                narratives = [text for text in json.loads(row[10] or "[]") if isinstance(text, str)]
                tables[(row[0], row[1], row[2])] = NoteTable(
                    ordinal, page, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], narratives,
                )
            for row in connection.execute(
                """SELECT c.page_json_version_id, c.section_id, c.table_id, c.column_id, c.column_ordinal,
                          c.header_path_exact_json, c.value_kind
                   FROM notes_keys AS k JOIN column_node AS c
                     ON c.page_json_version_id = k.v AND c.section_id = k.s AND c.table_id = k.t
                   ORDER BY c.column_ordinal"""
            ):
                header = tuple(part for part in json.loads(row[5]) if isinstance(part, str))
                tables[(row[0], row[1], row[2])].columns.append(NoteColumn(row[3], row[4], header, row[6]))
            for row in connection.execute(
                """SELECT r.page_json_version_id, r.section_id, r.table_id, r.row_id, r.source_order, r.label_exact,
                          r.row_kind, r.hierarchy_path_exact_json, r.parent_row_id
                   FROM notes_keys AS k JOIN row_node AS r
                     ON r.page_json_version_id = k.v AND r.section_id = k.s AND r.table_id = k.t
                   ORDER BY r.source_order"""
            ):
                hierarchy = tuple(part for part in json.loads(row[7]) if isinstance(part, str))
                tables[(row[0], row[1], row[2])].rows.append(NoteRow(row[3], row[4], row[5], row[6], hierarchy, row[8]))
            cell_count = 0
            for row in connection.execute(
                """SELECT v.page_json_version_id, v.section_id, v.table_id, v.row_id, v.column_id, v.source_text, v.visual_state
                   FROM notes_keys AS k JOIN value_cell AS v
                     ON v.page_json_version_id = k.v AND v.section_id = k.s AND v.table_id = k.t"""
            ):
                tables[(row[0], row[1], row[2])].cells[(row[3], row[4])] = (row[5], row[6])
                cell_count += 1
        self.metrics.sql_queries += 4
        self.metrics.rows_read += len(tables) + sum(len(t.rows) + len(t.columns) for t in tables.values()) + cell_count
        return [tables[key] for key in keys if key in tables]

    def outline(self) -> dict[int, list[dict[str, Any]]]:
        """Every section and table title of every selected page, in reading order."""

        if self._outline is None:
            outline: dict[int, list[dict[str, Any]]] = defaultdict(list)
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    """SELECT n.page_json_version_id, n.section_id, n.source_order, n.content_kind, n.title_exact,
                              t.table_id, t.source_order, t.title_exact, t.continuation
                       FROM section_node AS n JOIN notes_selected AS s ON s.v = n.page_json_version_id
                       LEFT JOIN table_node AS t ON t.page_json_version_id = n.page_json_version_id AND t.section_id = n.section_id"""
                ).fetchall()
            self.metrics.sql_queries += 1
            self.metrics.rows_read += len(rows)
            seen = set()
            for row in rows:
                ordinal, page = self.page_of[row[0]]
                if (row[0], row[1]) not in seen:
                    seen.add((row[0], row[1]))
                    outline[ordinal].append({"page": page, "section_order": row[2], "table_order": -1,
                                             "kind": row[3], "title": row[4], "source": "SECTION_TITLE",
                                             "version": row[0], "section_id": row[1], "table_id": None})
                if row[5] is not None:
                    outline[ordinal].append({"page": page, "section_order": row[2], "table_order": row[6],
                                             "kind": row[3], "title": row[7], "source": "TABLE_TITLE",
                                             "version": row[0], "section_id": row[1], "table_id": row[5],
                                             "continuation": row[8]})
            for entries in outline.values():
                entries.sort(key=lambda e: (e["page"], e["section_order"], e["table_order"]))
            self._outline = dict(outline)
        return self._outline


_ON_NEXT = {"CONTINUES_ON_NEXT_PAGE", "BOTH"}
_FROM_PREVIOUS = {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}


def continuation_neighbors_v1(source: "NotesSource", keys) -> set[tuple[str, str, str]]:
    """Keys of the tables printed just before/after each key across a page break."""

    outline = source.outline()
    wanted = set()
    for key in keys:
        ordinal, page = source.page_of[key[0]]
        tables = [e for e in outline.get(ordinal, []) if e["table_id"] is not None]
        for neighbor_page, pick in ((page + 1, 0), (page - 1, -1)):
            on_page = [e for e in tables if e["page"] == neighbor_page]
            if on_page:
                entry = on_page[pick]
                wanted.add((entry["version"], entry["section_id"], entry["table_id"]))
    return wanted - set(keys)


def _money_columns(table: NoteTable) -> list[NoteColumn]:
    return [c for c in table.columns if c.value_kind == "MONEY"]


_CONTINUED_MARKER = re.compile(r"\(?\s*tiep theo\s*\)?")
_GENERIC_REPORT_HEADER = re.compile(r"\bthuyet minh bao cao tai chinh\b")


def _note_identity(title: str | None) -> str:
    """A section title without the "(tiếp theo)" marker; a generic report page header has no identity."""

    folded = re.sub(r"\s+", " ", _CONTINUED_MARKER.sub(" ", fold_vietnamese(title or ""))).strip()
    if not folded or (_GENERIC_REPORT_HEADER.search(folded) and not _NOTE_HEADING.match(folded)):
        return ""
    return folded


def _continuation_compatible(head: NoteTable, follower: NoteTable) -> bool:
    """Owner/reset fence and column bijection for a page continuation.

    The follower prints no title of its own; its section, once "(tiếp theo)"
    is removed, is the head's note or carries no note identity (untitled or a
    generic report page header) — another note "(tiếp theo)" is a reset; any
    unit printed on both fragments agrees; and each follower money column has
    the head's header or no header at all.
    """

    head_money, follower_money = _money_columns(head), _money_columns(follower)
    if not head_money or len(head_money) != len(follower_money):
        return False
    if follower.table_title or follower.narratives:
        # Own title or narratives are owner evidence of the follower itself
        # (e.g. "Phân tích chất lượng dư nợ tiền gửi … các TCTD khác"): not a
        # continuation of the head, whose owner context they could contradict.
        return False
    follower_note = _note_identity(follower.section_title)
    if follower_note and follower_note != _note_identity(head.section_title):
        return False
    head_units = {u.unit for u in units_in_unit_field_v1(head.unit_exact, source_kind="TABLE_UNIT_FIELD")}
    follower_units = {u.unit for u in units_in_unit_field_v1(follower.unit_exact, source_kind="TABLE_UNIT_FIELD")}
    if head_units and follower_units and head_units != follower_units:
        return False
    return all(not f.header_text or f.header_text == h.header_text for h, f in zip(head_money, follower_money))


def assemble_continuations_v1(source: "NotesSource", tables: list[NoteTable]) -> tuple[list[NoteTable], list[dict[str, Any]]]:
    """Join a table with its continuation on the next page.

    Two fragments join only when (a) the earlier is the last table of its page
    and the later the first table of the next page, (b) at least one of them
    declares the page continuation, and (c) they have the same number of money
    columns. Rows keep their own identity (prefixed by page); the head's
    column headers are used. Returns the joined tables and join receipts.
    """

    outline = source.outline()
    by_key = {t.key: t for t in tables}
    flags, position = {}, {}
    for ordinal, entries in outline.items():
        pages: dict[int, list[dict[str, Any]]] = {}
        for entry in entries:
            if entry["table_id"] is not None:
                pages.setdefault(entry["page"], []).append(entry)
        for page, on_page in pages.items():
            for index, entry in enumerate(on_page):
                key = (entry["version"], entry["section_id"], entry["table_id"])
                flags[key] = entry.get("continuation")
                position[key] = (ordinal, page, index == 0, index == len(on_page) - 1)
    next_of = {}
    for key, table in by_key.items():
        ordinal, page, _first, last = position[key]
        if not last:
            continue
        follower = next((k for k in by_key if position[k][0] == ordinal and position[k][1] == page + 1 and position[k][2]), None)
        if follower is None:
            continue
        # Both fragments must declare the page break (head: continues on next page;
        # follower: continues from previous page); a single flag is not proof.
        declared = flags.get(key) in _ON_NEXT and flags.get(follower) in _FROM_PREVIOUS
        if declared and _continuation_compatible(table, by_key[follower]):
            next_of[key] = follower
    followers = set(next_of.values())
    joined, receipts = [], []
    for key, table in by_key.items():
        if key in followers:
            continue
        chain = [table]
        while chain[-1].key in next_of and len(chain) < 4:
            chain.append(by_key[next_of[chain[-1].key]])
        if len(chain) == 1:
            joined.append(table)
            continue
        head = chain[0]
        merged = NoteTable(
            head.document_ordinal, head.physical_page, head.page_json_version_id, head.section_id, head.table_id,
            head.section_order, head.table_order, head.content_kind, head.section_title, head.table_title,
            head.unit_exact or next((t.unit_exact for t in chain if t.unit_exact), None), head.continuation,
            list(head.narratives), list(head.columns),
        )
        head_money = _money_columns(head)
        for fragment in chain:
            column_map = {c.column_id: h.column_id for c, h in zip(_money_columns(fragment), head_money)}
            for row in fragment.rows:
                row_id = f"p{fragment.physical_page}:{row.row_id}"
                parent = f"p{fragment.physical_page}:{row.parent_row_id}" if row.parent_row_id else None
                merged.rows.append(NoteRow(row_id, len(merged.rows), row.label, row.kind, row.hierarchy, parent))
            for (cell_row, cell_column), value in fragment.cells.items():
                if cell_column in column_map:
                    merged.cells[(f"p{fragment.physical_page}:{cell_row}", column_map[cell_column])] = value
        merged.fragments = [t.locator() for t in chain]
        receipts.append({"head": head.locator(), "fragments": merged.fragments, "basis": "PAGE_CONTINUATION_DECLARED"})
        joined.append(merged)
    return joined, receipts


def bind_sibling_units_v1(source: "NotesSource", tables: list[NoteTable]) -> None:
    """Inherit a unit printed once for the note on an earlier table of the same section.

    A table that prints no unit takes the unit of a sibling only when: the
    sibling is in the same page section and precedes it, prints a unit in its
    unit field, has exactly the same money column headers (same lanes), and
    every sibling of the section that prints a unit prints the same one. The
    proof (sibling locator, unit text) is recorded on the table.
    """

    needy = [t for t in tables if not units_in_unit_field_v1(t.unit_exact, source_kind="TABLE_UNIT_FIELD")]
    if not needy:
        return
    outline = source.outline()
    keys = set()
    for table in needy:
        for entry in outline.get(table.document_ordinal, []):
            if entry["table_id"] is not None and entry["version"] == table.page_json_version_id \
                    and entry["section_id"] == table.section_id and entry["table_id"] != table.table_id:
                keys.add((entry["version"], entry["section_id"], entry["table_id"]))
    siblings = {}
    for sibling in source.load_tables(keys):
        siblings.setdefault((sibling.page_json_version_id, sibling.section_id), []).append(sibling)
    for table in needy:
        group = siblings.get((table.page_json_version_id, table.section_id), [])
        printed = {s.key: {u.unit for u in units_in_unit_field_v1(s.unit_exact, source_kind="TABLE_UNIT_FIELD")
                           if u.unit not in {PERCENT, VND_PER_SHARE}} for s in group}
        units = {u for found in printed.values() for u in found}
        if len(units) != 1:
            continue
        headers = [c.header_text for c in _money_columns(table)]
        donors = [s for s in group if printed[s.key] and s.table_order < table.table_order
                  and [c.header_text for c in _money_columns(s)] == headers]
        if donors:
            donor = donors[-1]
            table.sibling_unit = {"unit": next(iter(units)), "unit_text": donor.unit_exact, "donor": donor.locator()}


def table_context_v1(table: NoteTable, outline: list[dict[str, Any]], *, max_headings: int = 4) -> list[tuple[str, str]]:
    """Printed context of a table, nearest first: (source, text).

    Own table title, own section title and narratives, then preceding titles
    in reading order back to (and including) the nearest numbered note heading.
    Only printed titles are used; no page position or file name.
    """

    context: list[tuple[str, str]] = []
    if table.table_title:
        context.append(("TABLE_TITLE", table.table_title))
    if table.section_title:
        context.append(("SECTION_TITLE", table.section_title))
    for narrative in table.narratives:
        context.append(("SECTION_NARRATIVE", narrative))
    position = next((i for i, e in enumerate(outline) if e["version"] == table.page_json_version_id
                     and e["section_id"] == table.section_id and e["table_id"] == table.table_id), None)
    headings = 0
    if position is not None:
        for entry in reversed(outline[:position]):
            title = entry["title"]
            if not title or (entry["version"] == table.page_json_version_id and entry["section_id"] == table.section_id
                             and entry["source"] == "SECTION_TITLE"):
                continue
            context.append(("PRECEDING_" + entry["source"], title))
            if _NOTE_HEADING.match(fold_vietnamese(title)):
                headings += 1
                if headings >= max_headings or re.match(r"\A\s*\d+\s*[.)]?\s+\S", fold_vietnamese(title)):
                    break
            if len(context) > 12:
                break
    return context


# --------------------------------------------------------------------------- lanes and cells


@dataclass
class NoteLane:
    column: NoteColumn
    period_key: str | None
    period_basis: str
    unit: str | None
    unit_basis: str
    reasons: list[str] = field(default_factory=list)
    measure: str | None = None
    subject: str | None = None


_REPORTING_POINT = re.compile(r"\b(?:tai ngay|den ngay|tinh den ngay|ket thuc ngay|ket thuc vao ngay|vao ngay ket thuc)\b\s*")
_CLOSING_WORDS = re.compile(r"\b(?:cuoi ky|cuoi nam|cuoi quy|so cuoi|ky nay|nam nay)\b")
_OPENING_WORDS = re.compile(r"\b(?:dau ky|dau nam|so dau|ky truoc|nam truoc)\b")


def resolve_instant_lanes_v1(
    table: NoteTable, document: DocumentContext, page_texts: list[str],
    own_context: list[str] | None = None, measures: dict[str, list[str]] | None = None,
    date_intro_phrases: list[list[str]] | None = None,
) -> list[NoteLane]:
    """Money lanes of a balance-type note table with period and unit evidence.

    Explicit dates are taken as printed. Relative headers ("Cuối kỳ", "Đầu
    kỳ", "Số đầu năm") are aligned to the accepted balance-sheet lanes of the
    same document: closing -> the single CURRENT lane, opening -> the single
    COMPARATIVE lane. A header naming a measure (e.g. "Dự phòng cụ thể")
    instead of a period takes the single date printed in the table's own
    context ("Kết quả phân loại nợ tại ngày 31/12/2025"). Anything else stays
    unresolved.
    """

    context = statement_period_context_v1(document.context_texts)
    def reporting_dates(text: str) -> set[str]:
        # Only a date printed right after a reporting-point phrase ("tại ngày",
        # "đến ngày", "kết thúc ngày" …). A bare "ngày" — "Hà Nội, ngày …",
        # "Báo cáo được ký ngày …" — is never a reporting point here.
        folded = fold_vietnamese(text)
        found = set()
        for marker in _REPORTING_POINT.finditer(folded):
            dates = printed_dates_v1(folded[marker.end(): marker.end() + 40])
            if dates:
                found.add(dates[0])
        return found

    own_dates = sorted({d for text in own_context or [] for d in reporting_dates(text)})
    if len(own_dates) > 1 and date_intro_phrases:
        # Prefer the date of the sentence that introduces the breakdown
        # ("Kết quả phân loại nợ tại ngày ..."), when exactly one does.
        introduced = sorted({d for text in own_context or []
                             if any(all(p in fold_vietnamese(text) for p in g) for g in date_intro_phrases)
                             for d in reporting_dates(text)})
        if len(introduced) == 1:
            own_dates = introduced
    all_header_units = {u.unit for column in table.columns if column.value_kind == "MONEY"
                        for part in column.header_path for u in units_in_header_component_v1(part)
                        if u.unit not in {PERCENT, VND_PER_SHARE}}
    table_units = units_in_unit_field_v1(table.unit_exact, source_kind="TABLE_UNIT_FIELD")
    prose_units = []
    for text in [table.section_title, table.table_title, *table.narratives, *page_texts]:
        prose_units += units_in_prose_v1(text, source_kind="NOTE_PAGE_TEXT")
    lanes = []
    for column in table.columns:
        if column.value_kind != "MONEY":
            continue
        header_units = [u for part in column.header_path for u in units_in_header_component_v1(part)]
        if any(u.unit == PERCENT for u in header_units):
            continue
        lane = NoteLane(column, None, "UNRESOLVED", None, "UNRESOLVED")
        folded = fold_vietnamese(column.header_text)
        hits = {m: max((a for a in aliases if re.search(rf"\b{re.escape(a)}\b", folded)), key=len, default=None)
                for m, aliases in (measures or {}).items()}
        hits = {m: a for m, a in hits.items() if a}
        # The most specific alias wins: "tổng số dự phòng" is not the "số dư" of BALANCE.
        named = [m for m, a in hits.items() if not any(a != b and a in b for b in hits.values())]
        if len(named) > 1:
            lane.reasons.append("MEASURE_AMBIGUOUS")
        elif named:
            lane.measure = named[0]
        dates = printed_dates_v1(column.header_text)
        if not dates and lane.measure and not (_CLOSING_WORDS.search(folded) or _OPENING_WORDS.search(folded)):
            if len(own_dates) == 1:
                lane.period_key, lane.period_basis = f"INSTANT:{own_dates[0]}", "OWN_CAPTION_PRINTED_DATE"
            else:
                lane.reasons.append("PERIOD_UNRESOLVED:MEASURE_COLUMN_WITHOUT_UNIQUE_CONTEXT_DATE")
        elif len(dates) == 1:
            lane.period_key, lane.period_basis = f"INSTANT:{dates[0]}", "EXPLICIT_HEADER_DATE"
        elif len(dates) > 1:
            lane.reasons.append("PERIOD_MULTIPLE_DATES_IN_HEADER")
        else:
            current, comparative = document.balance_lane_keys("CURRENT"), document.balance_lane_keys("COMPARATIVE")
            closing_word, opening_word = bool(_CLOSING_WORDS.search(folded)), bool(_OPENING_WORDS.search(folded))
            if closing_word and not opening_word and len(current) == 1:
                lane.period_key, lane.period_basis = current[0], "ALIGNED_TO_PRIMARY_BALANCE_CURRENT_LANE"
            elif opening_word and not closing_word and len(comparative) == 1:
                lane.period_key, lane.period_basis = comparative[0], "ALIGNED_TO_PRIMARY_BALANCE_COMPARATIVE_LANE"
            else:
                descriptor = instant_lane_period_v1(column.header_text, context)
                if descriptor.key:
                    lane.period_key, lane.period_basis = descriptor.key, "PRIMARY_PERIOD_PARSER_" + descriptor.resolution
                else:
                    lane.reasons.append("PERIOD_UNRESOLVED:" + str(descriptor.reason))
        if lane.period_key is None and not lane.reasons:
            lane.reasons.append("PERIOD_UNRESOLVED")
        money = {u.unit for u in header_units if u.unit not in {PERCENT, VND_PER_SHARE}}
        basis = "HEADER"
        if not money and len(all_header_units) == 1:
            money, basis = set(all_header_units), "SAME_TABLE_HEADER"
        if not money:
            money, basis = {u.unit for u in table_units if u.unit not in {PERCENT, VND_PER_SHARE}}, "TABLE_UNIT_FIELD"
        if not money:
            money, basis = {u.unit for u in prose_units if u.unit not in {PERCENT, VND_PER_SHARE}}, "NOTE_PAGE_TEXT"
        if not money and table.sibling_unit:
            money, basis = {table.sibling_unit["unit"]}, "SAME_SECTION_SIBLING_UNIT"
        if len(money) == 1:
            lane.unit, lane.unit_basis = next(iter(money)), basis
        else:
            lane.reasons.append("UNIT_CONFLICT" if money else "UNIT_UNRESOLVED")
        lanes.append(lane)
    keys = [(lane.period_key, lane.measure) for lane in lanes if lane.period_key]
    for lane in lanes:
        if lane.period_key and keys.count((lane.period_key, lane.measure)) > 1:
            lane.reasons.append("DUPLICATE_PERIOD_LANE")
    return lanes


@dataclass
class ParsedValue:
    state: str
    value: Decimal | None
    raw: str | None
    reason: str | None


def parse_cell_v1(table: NoteTable, row: NoteRow, column: NoteColumn, roles: SeparatorRoles,
                  document_roles: SeparatorRoles | None = None) -> ParsedValue:
    """Parse with the table's separator evidence, then the document's (as PRIMARY does)."""

    text, visual = table.cells.get((row.row_id, column.column_id), (None, "BLANK"))
    parsed = parse_money_cell_v1(text, roles)
    if parsed.state == "AMBIGUOUS_SEPARATOR" and document_roles is not None and not roles.conflicted             and not document_roles.conflicted:
        parsed = parse_money_cell_v1(text, document_roles)
    return ParsedValue(parsed.state, parsed.value, text, parsed.reason)


def page_texts_v1(source: NotesSource, table: NoteTable) -> list[str]:
    """Titles printed on the same page as the table (for page-level unit lines)."""

    outline = source.outline().get(table.document_ordinal, [])
    return [entry["title"] for entry in outline if entry["page"] == table.physical_page and entry["title"]]


def stable_json_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
