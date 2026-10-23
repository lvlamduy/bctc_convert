"""Stable kernel for notes digitization (public API used by every plugin).

* Source: the corpus selection is authenticated by ``primary_statements.source_v1``
  (index SHA, selection heads, manifests, database SHA). Note tables are then
  read from the normalized nodes of that pinned, immutable database with a few
  batched SQL queries: retrieval first (indexed folded labels), then only the
  candidate tables are loaded. Every loaded table is then proven against its
  ORIGINAL page through the authenticated loader (source_bridge_v1); a table
  without an exact bridge is rejected, never read from the normalized rows.
* Document context comes from the accepted PRIMARY result store (pinned SHA):
  scope, balance-sheet lane periods and accepted primary cells, so notes use
  the same scope/period identities as the statements they explain.
* Cells, units and periods reuse the PRIMARY parsers: no blank-to-zero, no
  unit from magnitude, no year arithmetic.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles, evidence_roles_v1, parse_money_cell_v1
from bctc_ai.primary_statements.periods_v1 import (
    duration_lane_period_v1,
    instant_lane_period_v1,
    printed_dates_v1,
    statement_period_context_v1,
)
from bctc_ai.primary_statements.source_v1 import CorpusSelection, SourceMetrics, connect_readonly, sha256_file
from bctc_ai.primary_statements.text_v1 import fold_vietnamese, label_key_v1
from bctc_ai.evaluation.gemini_financial_page_json_v1 import validate_financial_page_json_v1
from bctc_ai.notes.source_bridge_v1 import bridge_table_v1, table_fingerprint_v1
from bctc_ai.notes.source_bridge_v1 import EXACT as BRIDGE_EXACT
from bctc_ai.notes.source_bridge_v1 import EXACT_SHIFT as BRIDGE_EXACT_SHIFT
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import load_income_tax_source_page_json_versions_v1
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
    # Printed period context of the income statement (title, narratives) and
    # its resolved lane keys; pages holding primary statements; first note page.
    income_context_texts: list[str] = field(default_factory=list)
    income_lane_keys: list[str] = field(default_factory=list)
    statement_pages: frozenset[str] = frozenset()
    notes_start_page: int | None = None
    # Identity of the PRIMARY result this context came from: the notes run must bind the same
    # source document AND the same corpus before using any scope/period/unit/anchor from it.
    corpus_identity: dict[str, Any] = field(default_factory=dict)

    def identity_mismatch(self, document, corpus_identity: dict[str, Any]) -> str | None:
        """Why this PRIMARY context must not be used for ``document`` of the given corpus, else None."""

        if (self.relative_path, self.source_sha256, self.document_plan_id) != (
                document.relative_path, document.source_sha256, document.document_plan_id):
            return "PRIMARY_CONTEXT_DOCUMENT_IDENTITY_MISMATCH"
        keys = ("corpus_name", "index_sha256", "corpus_manifest_index_id", "database_sha256")
        if any(self.corpus_identity.get(key) != corpus_identity.get(key) for key in keys):
            return "PRIMARY_CONTEXT_CORPUS_IDENTITY_MISMATCH"
        return None

    def balance_lane_keys(self, role: str) -> list[str]:
        return [lane["key"] for lane in self.balance_lanes if lane["role"] == role and lane["key"]]

    def primary_value_for_period(self, statement: str, report_norm_id: int, period_key: str) -> tuple[Decimal, str] | None:
        """The accepted primary cell of the same printed duration (None when absent or not unique)."""

        found = {value for (s, rnid, key), value in self.primary_cells.items()
                 if s == statement and rnid == report_norm_id and canonical_period_key_v1(key) == period_key}
        return next(iter(found)) if len(found) == 1 else None


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
            income = [i for i in primary if i["statement"] == "KQKD"]
            income_texts, income_keys = [], []
            if len(income) == 1:
                income_texts = list(income[0]["period_context"].get("evidence") or [])
                income_keys = [(lane.get("period") or {}).get("key") for lane in income[0]["lanes"]]
                income_keys = [key for key in income_keys if key]
            statement_pages = frozenset(t["page_json_version_id"] for i in result["instances"] for t in i["tables"])
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
                income_context_texts=income_texts, income_lane_keys=income_keys, statement_pages=statement_pages,
                notes_start_page=result.get("notes_start_page"), corpus_identity=dict(result.get("corpus") or {}),
            )
    return contexts


# --------------------------------------------------------------------------- note tables


@dataclass
class NoteColumn:
    column_id: str
    ordinal: int
    header_path: tuple[str, ...]
    value_kind: str
    header_raw: Any = None  # the stored header JSON before string filtering (source bridge input)

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
    hierarchy_raw: Any = None  # the stored hierarchy JSON before string filtering (source bridge input)

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
    narratives_raw: Any = None
    # ORIGINAL-source bridge (source_bridge_v1): one for a single table; a continuation-merged
    # table keeps every fragment's bridge plus its head-column -> fragment-column map per page.
    bridge: dict[str, Any] | None = None
    fragment_bridges: list[dict[str, Any]] = field(default_factory=list)
    fragment_column_maps: dict[int, dict[str, str]] = field(default_factory=dict)

    def bridge_failure(self) -> str | None:
        """None when every source fragment is bridged exactly to its ORIGINAL, else the first failure."""

        bridges = self.fragment_bridges if self.fragments else [self.bridge]
        for bridge in bridges:
            status = (bridge or {}).get("status") or "MISSING"
            if status not in (BRIDGE_EXACT, BRIDGE_EXACT_SHIFT):
                return "SOURCE_BRIDGE:" + status
        return None

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

    def __init__(self, corpus: CorpusSelection, metrics: SourceMetrics | None = None, original_loader=None):
        self.corpus = corpus
        self.metrics = metrics or SourceMetrics()
        self.page_of: dict[str, tuple[int, int]] = {
            page.page_json_version_id: (document.ordinal, page.physical_page)
            for document in corpus.documents for page in document.pages
        }
        self._outline: dict[int, list[dict[str, Any]]] | None = None
        self._documents = {document.ordinal: document for document in corpus.documents}
        self._bridges: dict[tuple[tuple[str, str, str], str], dict[str, Any]] = {}
        self._original_loader = original_loader or load_income_tax_source_page_json_versions_v1

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
                narratives_raw = json.loads(row[10] or "[]")
                narratives = [text for text in narratives_raw if isinstance(text, str)]
                tables[(row[0], row[1], row[2])] = NoteTable(
                    ordinal, page, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], narratives,
                    narratives_raw=narratives_raw,
                )
            for row in connection.execute(
                """SELECT c.page_json_version_id, c.section_id, c.table_id, c.column_id, c.column_ordinal,
                          c.header_path_exact_json, c.value_kind
                   FROM notes_keys AS k JOIN column_node AS c
                     ON c.page_json_version_id = k.v AND c.section_id = k.s AND c.table_id = k.t
                   ORDER BY c.column_ordinal"""
            ):
                header_raw = json.loads(row[5])
                header = tuple(part for part in header_raw if isinstance(part, str))
                tables[(row[0], row[1], row[2])].columns.append(NoteColumn(row[3], row[4], header, row[6], header_raw))
            for row in connection.execute(
                """SELECT r.page_json_version_id, r.section_id, r.table_id, r.row_id, r.source_order, r.label_exact,
                          r.row_kind, r.hierarchy_path_exact_json, r.parent_row_id
                   FROM notes_keys AS k JOIN row_node AS r
                     ON r.page_json_version_id = k.v AND r.section_id = k.s AND r.table_id = k.t
                   ORDER BY r.source_order"""
            ):
                hierarchy_raw = json.loads(row[7])
                hierarchy = tuple(part for part in hierarchy_raw if isinstance(part, str))
                tables[(row[0], row[1], row[2])].rows.append(
                    NoteRow(row[3], row[4], row[5], row[6], hierarchy, row[8], hierarchy_raw))
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
        _require(set(tables) == set(keys), "a requested note table is absent from the selected pages")
        self._attach_bridges(list(tables.values()))
        return [tables[key] for key in keys]

    def _load_originals(self, version_ids: list[str]) -> dict[str, dict[str, Any]]:
        """ORIGINAL pages through the authenticated loader. Any loader failure (missing input, BLOB/VID
        replay, provenance, SQLite, unsupported transform) propagates and fails the run: never retried
        in smaller batches, never turned into a table outcome."""

        loaded = self._original_loader(self.corpus.db_path, page_json_version_ids=version_ids)
        _require([item.get("page_json_version_id") for item in loaded] == list(version_ids),
                 "authenticated original page load differs from the selected versions")
        self.metrics.sql_queries += 3
        self.metrics.pages_loaded += len(loaded)
        return {item["page_json_version_id"]: item for item in loaded}

    def _attach_bridges(self, tables: list[NoteTable]) -> None:
        """Prove every loaded table against its ORIGINAL page; reuse a proof only for the identical SQL payload.

        The cache key is the table key plus a typed fingerprint of every raw field the bridge
        compares; each table receives a detached copy, so a caller cannot poison the cache.
        """

        fingerprints = {id(t): table_fingerprint_v1(t) for t in tables}
        pending = [t for t in tables if (t.key, fingerprints[id(t)]) not in self._bridges]
        version_ids = sorted({t.page_json_version_id for t in pending}, key=lambda v: (self.page_of[v], v))
        for start in range(0, len(version_ids), 200):
            chunk = version_ids[start: start + 200]
            originals, validated = self._load_originals(chunk), {}
            for table in pending:
                if table.page_json_version_id in originals:
                    proof = self._bridge_one(table, originals[table.page_json_version_id], validated)
                    self._bridges[(table.key, fingerprints[id(table)])] = proof
            del originals, validated
        for table in tables:
            table.bridge = copy.deepcopy(self._bridges[(table.key, fingerprints[id(table)])])

    def _bridge_one(self, table: NoteTable, item: dict[str, Any], validated: dict[str, Any]) -> dict[str, Any]:
        ordinal, physical_page = self.page_of[table.page_json_version_id]
        document = self._documents[ordinal]
        # The loader's provenance must be the selected corpus page itself, not merely the same VID.
        _require((item.get("page_json_version_id"), item.get("source_logical_name"), item.get("source_sha256"),
                  item.get("physical_page")) == (table.page_json_version_id, document.relative_path,
                                                 document.source_sha256, physical_page),
                 f"original page provenance is not the selected page {table.page_json_version_id}")
        receipt = item["source_json_replay_receipt"]
        if table.page_json_version_id not in validated:  # once per page, shared by its tables
            validated[table.page_json_version_id] = validate_financial_page_json_v1(item["page_json"])
        bridge = bridge_table_v1(table, item["page_json"], validated[table.page_json_version_id],
                                 list(receipt.get("changed_tables") or []))
        bridge.update({"physical_page": physical_page, "source_logical_name": document.relative_path,
                       "source_sha256": document.source_sha256,
                       "original_blob_sha256": receipt.get("canonical_json_sha256"),
                       "replay_receipt_id": receipt.get("replay_receipt_id")})
        return bridge

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
            merged.fragment_column_maps[fragment.physical_page] = {h: c for c, h in column_map.items()}
            for row in fragment.rows:
                row_id = f"p{fragment.physical_page}:{row.row_id}"
                parent = f"p{fragment.physical_page}:{row.parent_row_id}" if row.parent_row_id else None
                merged.rows.append(NoteRow(row_id, len(merged.rows), row.label, row.kind, row.hierarchy, parent))
            for (cell_row, cell_column), value in fragment.cells.items():
                if cell_column in column_map:
                    merged.cells[(f"p{fragment.physical_page}:{cell_row}", column_map[cell_column])] = value
        merged.fragments = [t.locator() for t in chain]
        merged.fragment_bridges = [dict(t.bridge or {}, physical_page=t.physical_page, derivation="CONTINUATION_FRAGMENT")
                                   for t in chain]
        receipts.append({"head": head.locator(), "fragments": merged.fragments, "basis": "PAGE_CONTINUATION_DECLARED"})
        joined.append(merged)
    return joined, receipts


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
    candidates: list[str] = field(default_factory=list)


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
    unit_sources = _unit_sources(table, page_texts)
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
        _resolve_lane_unit(lane, header_units, unit_sources)
        lanes.append(lane)
    keys = [(lane.period_key, lane.measure) for lane in lanes if lane.period_key]
    for lane in lanes:
        if lane.period_key and keys.count((lane.period_key, lane.measure)) > 1:
            lane.reasons.append("DUPLICATE_PERIOD_LANE")
    return lanes


def _unit_sources(table: NoteTable, page_texts: list[str]) -> tuple[set[str], list[Any], list[Any], set[str]]:
    all_header_units = {u.unit for column in table.columns if column.value_kind == "MONEY"
                        for part in column.header_path for u in units_in_header_component_v1(part)
                        if u.unit not in {PERCENT, VND_PER_SHARE}}
    table_units = units_in_unit_field_v1(table.unit_exact, source_kind="TABLE_UNIT_FIELD")
    prose_units = []
    for text in [table.section_title, table.table_title, *table.narratives, *page_texts]:
        prose_units += units_in_prose_v1(text, source_kind="NOTE_PAGE_TEXT")
    # Units the table itself owns outside its headers: its own unit field and its own title. Section
    # titles/narratives and page text may be shared by other tables, so they never contradict a header.
    owned = {u.unit for u in [*table_units, *units_in_prose_v1(table.table_title, source_kind="TABLE_TITLE")]
             if u.unit not in {PERCENT, VND_PER_SHARE}}
    return all_header_units, table_units, prose_units, owned


def _resolve_lane_unit(lane: NoteLane, header_units: list[Any], sources: tuple[set[str], list[Any], list[Any], set[str]]) -> None:
    """Printed unit only: own header, one unit shared by the table's headers, table unit field, page text.

    A header-derived unit must agree with every money unit the table itself owns (its unit field and its
    own title): "VND" in a header under a printed "Triệu đồng" table field is a conflict, never a choice.
    """

    all_header_units, table_units, prose_units, owned = sources
    money = {u.unit for u in header_units if u.unit not in {PERCENT, VND_PER_SHARE}}
    basis = "HEADER"
    if not money and len(all_header_units) == 1:
        money, basis = set(all_header_units), "SAME_TABLE_HEADER"
    if money and owned and owned != money:
        lane.reasons.append("UNIT_CONFLICT_HEADER_VS_TABLE_OWNED_UNIT")
        return
    if not money:
        money, basis = {u.unit for u in table_units if u.unit not in {PERCENT, VND_PER_SHARE}}, "TABLE_UNIT_FIELD"
    if not money:
        money, basis = {u.unit for u in prose_units if u.unit not in {PERCENT, VND_PER_SHARE}}, "NOTE_PAGE_TEXT"
    if len(money) == 1:
        lane.unit, lane.unit_basis = next(iter(money)), basis
    else:
        lane.reasons.append("UNIT_CONFLICT" if money else "UNIT_UNRESOLVED")


# --------------------------------------------------------------------------- duration lanes

_MONTH_END = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _same_day_previous_year(date: str) -> str:
    """The printed date one year earlier, for comparing two printed dates (29 Feb -> 28 Feb)."""

    year, month, day = int(date[:4]) - 1, int(date[5:7]), int(date[8:10])
    if month == 2 and day == 29 and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        day = 28
    return f"{year:04d}-{month:02d}-{day:02d}"


def _year_value(token: str) -> str | None:
    match = re.fullmatch(r"(PRIOR_YEAR_OF\()?((?:19|20)\d{2})\)?", token)
    if not match:
        return None
    return str(int(match.group(2)) - (1 if match.group(1) else 0))


_KEPT_AS_PRINTED = {"RANGE", "MONTHS_ENDED", "CUMULATIVE_FROM_START_OF_YEAR_TO", "CORRESPONDING_PRIOR_YEAR_RANGE",
                    "CORRESPONDING_PRIOR_YEAR_MONTHS_ENDED"}


def canonical_period_key_v1(key: str | None) -> str | None:
    """One key per printed duration, by definitional identities only.

    The year-to-date through the first quarter is the first quarter, and
    through the fourth quarter is the year, by the meaning of the words;
    "PRIOR_YEAR_OF(2025)" is the printed relation "năm trước" of 2025. No
    calendar convention is used: no start date is computed, and ranges and
    months-ended keys stay exactly as printed. Instants and unparsed keys
    return None.
    """

    if not key or not key.startswith("DURATION:"):
        return None
    parts = key.split(":")
    kind = parts[1] if len(parts) > 1 else ""
    if kind == "QUARTER" and len(parts) == 4 and parts[2].isdigit() and _year_value(parts[3]):
        return f"DURATION:QUARTER:{int(parts[2])}:{_year_value(parts[3])}"
    if kind == "YEAR" and len(parts) == 3 and _year_value(parts[2]):
        return f"DURATION:YEAR:{_year_value(parts[2])}"
    if kind == "YTD" and len(parts) == 4 and _year_value(parts[3]):
        through, year = parts[2], _year_value(parts[3])
        if through == "Q1":
            return f"DURATION:QUARTER:1:{year}"
        if through == "Q4":
            return f"DURATION:YEAR:{year}"
        return f"DURATION:YTD:{through}:{year}"
    if kind in _KEPT_AS_PRINTED:
        return key
    return None


_LITERAL_NEWLINE = re.compile(r"\\n")
_THIS_PERIOD = re.compile(r"\bky nay\b")
_ANY_RELATIVE = re.compile(r"\b(?:ky nay|nam nay|quy nay|ky truoc|nam truoc|quy truoc|cung ky)\b")
_SEGMENT_OR_SCOPE = re.compile(r"\b(?:mien bac|mien trung|mien nam|bo phan|khu vuc|dieu chinh|loai tru|hop nhat|rieng le|ngan hang me)\b")


def resolve_duration_lanes_v1(
    table: NoteTable, document: DocumentContext, page_texts: list[str], own_texts: list[str],
) -> list[NoteLane]:
    """Money lanes of a flow-type note table, keyed by the printed duration.

    Period evidence, in order: (1) a duration printed in the column header
    itself; (2) a relative header bound by the PRIMARY parser to the period
    printed in the table's own caption, else in the same report's income
    statement title (text only, never its numbers); a different report end
    printed by the two holds; (3) "Năm YYYY" printed alone, in an annual or
    fourth-quarter report. (4) A header printing only the report end date (or
    the same day of the previous year) or only "Kỳ này" leaves "quarter or
    year-to-date" open: it resolves only in a first-quarter report, where the
    two are the same period by definition; otherwise the lane keeps both
    candidates and is unresolved. "Kỳ trước"/"Năm trước" never get candidates.
    (5) In an annual report, a header printing only the report end date (or
    the same day one year earlier), optionally as "Năm (tài chính) kết thúc
    ngày D", is that reported year. Units as printed.
    """

    own_context = statement_period_context_v1(own_texts)
    report_context = statement_period_context_v1(document.income_context_texts)
    has_own = bool(own_context.reporting_date or own_context.year) and not own_context.conflict
    contexts_disagree = bool(own_context.conflict) or _windows_disagree(own_context, report_context)
    full_year_report = report_context.quarter in (None, 4) and report_context.months in (None, 12) and not report_context.conflict
    unit_sources = _unit_sources(table, page_texts)
    lanes = []
    for column in table.columns:
        if column.value_kind != "MONEY":
            continue
        header_units = [u for part in column.header_path for u in units_in_header_component_v1(part)]
        if any(u.unit == PERCENT for u in header_units):
            continue
        header = _LITERAL_NEWLINE.sub(" ", column.header_text)
        folded = fold_vietnamese(header)
        lane = NoteLane(column, None, "UNRESOLVED", None, "UNRESOLVED")
        if _SEGMENT_OR_SCOPE.search(folded):
            lane.reasons.append("HEADER_NAMES_SEGMENT_OR_SCOPE")
        elif not _raw_digits_and_marks_ok(header):
            # A date-bearing header with non-ASCII digits or a stray combining mark is never parsed
            # (folding would silently drop the annotation before any PRIMARY parser call).
            lane.reasons.append("HEADER_RAW_DIGIT_OR_MARK_NOT_PLAIN")
        else:
            own = duration_lane_period_v1(header, own_context) if has_own else None
            report = duration_lane_period_v1(header, report_context)
            own_key = canonical_period_key_v1(own.key) if own else None
            report_key = canonical_period_key_v1(report.key)
            explicit = next((d for d in (own, report) if d and d.key and d.resolution == "EXPLICIT"), None)
            year_only = re.fullmatch(r"nam\s+((?:19|20)\d{2})", _header_core(folded))
            calendar_ok = _calendar_year_compatible(own_context) and _calendar_year_compatible(report_context)
            explicit_key = canonical_period_key_v1(explicit.key) if explicit else None
            if explicit_key and explicit_key.startswith("DURATION:YEAR:") and not calendar_ok:
                # "Năm 2025" under a printed non-calendar fiscal window (e.g. ending 30/06): not relabelled.
                lane.reasons.append("NON_CALENDAR_FISCAL_WINDOW_NOT_RELABELLED_AS_YEAR")
            elif explicit_key:
                lane.period_key, lane.period_basis = explicit_key, "HEADER_PRINTED:" + explicit.key
            elif contexts_disagree or (own_key and report_key and own_key != report_key):
                lane.reasons.append("OWN_AND_REPORT_CONTEXT_DISAGREE")
            elif year_only and full_year_report and calendar_ok:
                lane.period_key, lane.period_basis = f"DURATION:YEAR:{year_only.group(1)}", "HEADER_PRINTED_YEAR"
            elif (own_key or report_key or "").startswith("DURATION:YEAR:") and not calendar_ok:
                lane.reasons.append("NON_CALENDAR_FISCAL_WINDOW_NOT_RELABELLED_AS_YEAR")
            elif own_key:
                lane.period_key, lane.period_basis = own_key, "OWN_CAPTION_BOUND:" + own.key
            elif report_key:
                lane.period_key, lane.period_basis = report_key, "REPORT_TITLE_BOUND:" + report.key
            else:
                lane.candidates = _quarter_or_ytd_candidates(header, folded, report_context, own_context)
                if lane.candidates and len(set(lane.candidates)) == 1:
                    basis = "ANNUAL_REPORT_END_DATE" if len(lane.candidates) == 1 else "FIRST_QUARTER_IS_YEAR_TO_DATE"
                    lane.period_key, lane.period_basis = lane.candidates[0], basis
                    lane.candidates = []
                elif lane.candidates:
                    lane.reasons.append("PERIOD_QUARTER_OR_YEAR_TO_DATE_NOT_PRINTED")
                else:
                    lane.reasons.append("PERIOD_UNRESOLVED:" + str(report.reason))
        _resolve_lane_unit(lane, header_units, unit_sources)
        lanes.append(lane)
    keys = [lane.period_key for lane in lanes if lane.period_key]
    for lane in lanes:
        if lane.period_key and keys.count(lane.period_key) > 1:
            lane.reasons.append("DUPLICATE_PERIOD_LANE")
    return lanes


def _windows_disagree(own, report) -> bool:
    """The table's own caption prints a reporting window that contradicts the income statement's.

    A more specific own window ("9 tháng kết thúc 30/09/2025" under a third-quarter
    statement) is not a contradiction; a different end, fiscal-year end,
    quarter, months, first-N-months or range start printed by both is, and so
    is an annual caption against a quarterly/interim statement (or vice versa).
    """

    def both_differ(a, b):
        return a is not None and b is not None and a != b

    report_end = report.reporting_date or (report.fiscal_year_end if report.annual else None)
    own_end = own.reporting_date or (own.fiscal_year_end if own.annual else None)
    if both_differ(own_end, report_end) or both_differ(own.fiscal_year_end, report.fiscal_year_end):
        return True
    if both_differ(own.quarter, report.quarter) or both_differ(own.months, report.months):
        return True
    if both_differ(own.first_months_of_fiscal_year, report.first_months_of_fiscal_year) or both_differ(own.range_start, report.range_start):
        return True
    report_interim = bool(report.quarter or (report.months and report.months != 12) or report.first_months_of_fiscal_year)
    own_interim = bool(own.quarter or (own.months and own.months != 12) or own.first_months_of_fiscal_year)
    return bool((own.annual and report_interim) or (report.annual and own_interim))


def _calendar_year_compatible(context) -> bool:
    """No printed window evidence contradicts a full calendar year (1/1 to 31/12)."""

    if context.fiscal_year_end and context.fiscal_year_end[5:] != "12-31":
        return False
    if context.annual and context.reporting_date and context.reporting_date[5:] != "12-31":
        return False
    if context.range_start and context.range_start[5:] != "01-01":
        return False
    return not context.first_months_of_fiscal_year and context.months in (None, 12)


_NUMERIC_DATE = r"([0-9]{1,2})[/.\-]([0-9]{1,2})[/.\-]((?:19|20)[0-9]{2})"
_WORDED_DATE = r"(?:ngay )?([0-9]{1,2}) thang ([0-9]{1,2}) nam ((?:19|20)[0-9]{2})"
_ANNUAL_PREFIX = r"(?:(?:cho )?nam (?:tai chinh )?ket thuc (?:vao )?ngay |(?:tai )?ngay )?"
_PLAIN_PREFIX = r"(?:(?:tai )?ngay )?"


def _raw_digits_and_marks_ok(raw_header: str) -> bool:
    """Raw (unfolded) header: only ASCII digits and no stray combining mark.

    Folding drops combining marks and Unicode digits would match a generic
    digit class, so the raw text is checked before any folded grammar.
    """

    raw = unicodedata.normalize("NFC", raw_header)
    if any(unicodedata.category(c) == "Mn" for c in raw):
        return False
    return all(c in "0123456789" for c in raw if unicodedata.category(c) == "Nd")


def _single_date_header(core: str, raw_header: str, *, annual_prefix: bool) -> str | None:
    """The one valid date of a header that prints nothing else (finite grammar), else None.

    The raw header must pass ``_raw_digits_and_marks_ok``; then the whole
    folded header must be an optional fixed prefix and exactly one ASCII date
    token; any extra number, word or a second/invalid date rejects it.
    """

    if not _raw_digits_and_marks_ok(raw_header):
        return None
    prefix = _ANNUAL_PREFIX if annual_prefix else _PLAIN_PREFIX
    match = re.fullmatch(prefix + f"(?:{_NUMERIC_DATE}|{_WORDED_DATE})", core, flags=re.ASCII)
    if not match:
        return None
    day, month, year = [g for g in match.groups() if g is not None]
    iso = _iso_date(int(day), int(month), int(year))
    return iso if iso and printed_dates_v1(core) == [iso] else None


def _iso_date(day: int, month: int, year: int) -> str | None:
    if not 1 <= month <= 12:
        return None
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    last = 29 if month == 2 and leap else _MONTH_END[month]
    return f"{year:04d}-{month:02d}-{day:02d}" if 1 <= day <= last else None


_UNIT_WORDS = re.compile(r"\(?\b(?:trieu|nghin|ngan|ty)?\s*(?:dong(?: viet nam)?|vnd|vn dong)\b\)?|\bdon vi(?: tinh)?\s*:?")


def _header_core(folded: str) -> str:
    """A folded header without unit words and line breaks."""

    return re.sub(r"\s+", " ", _UNIT_WORDS.sub(" ", folded)).strip(" /")


def _quarter_or_ytd_candidates(header: str, folded: str, context, own=None) -> list[str]:
    """The periods a header can mean when it prints only an end date or "Kỳ này".

    Quarterly report (printed quarter and end date): a header that is exactly
    the report end date (or the same day one year earlier), or only "Kỳ
    này", is the quarter or the year-to-date — two candidates, one when they
    coincide (first quarter). Annual report: the only candidate is the
    reported calendar year, and only when the printed fiscal year ends on
    31/12 with no contrary range/months/first-N-months evidence; any other
    fiscal end holds, and so does any window the table's own caption prints
    (range start, months, quarter, first-N-months, another end) that is not
    that full year. Headers must match a finite grammar (one valid date and
    nothing else, raw digits ASCII). Returns [] otherwise, including "Kỳ trước".
    """

    if context.conflict:
        return []
    core = _header_core(folded)
    annual = context.annual and not context.quarter and not context.months and not context.first_months_of_fiscal_year
    if annual:
        end = context.reporting_date or context.fiscal_year_end
        if not end or (context.fiscal_year_end and context.reporting_date and context.fiscal_year_end != context.reporting_date):
            return []
        if end[5:] != "12-31" or (context.range_start and context.range_start != end[:4] + "-01-01"):
            return []  # a non-calendar fiscal window is not relabelled as a calendar year
        if own is not None:
            own_end = own.reporting_date or own.fiscal_year_end
            if (own.range_start not in (None, end[:4] + "-01-01") or own.months not in (None, 12)
                    or own.first_months_of_fiscal_year or own.quarter or own_end not in (None, end)):
                return []  # every owned window constraint is enforced, not only the ones PRIMARY also prints
        date = _single_date_header(core, header, annual_prefix=True)
        if date and date[5:] == "12-31" and date in (end, _same_day_previous_year(end)):
            return [f"DURATION:YEAR:{date[:4]}"]
        return []
    if not context.quarter or not context.reporting_date:
        return []
    quarter = context.quarter
    date = _single_date_header(core, header, annual_prefix=False)
    if date is not None:
        if date not in (context.reporting_date, _same_day_previous_year(context.reporting_date)):
            return []
        year = date[:4]
    elif printed_dates_v1(header):
        return []
    elif _THIS_PERIOD.search(folded) and len(set(_ANY_RELATIVE.findall(folded))) == 1 and re.fullmatch(r"ky nay", core):
        year = context.reporting_date[:4]
    else:
        return []
    return [f"DURATION:QUARTER:{quarter}:{year}", canonical_period_key_v1(f"DURATION:YTD:Q{quarter}:{year}")]


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
