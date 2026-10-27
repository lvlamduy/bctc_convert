"""UNRUN F36-only whole-run streaming persistence; EXPERIMENTAL proposals only.

No generic ingest/load/export path is called. The fixed cold source factory,
held input barriers and complete normalized readback are mandatory. This is a
cooperative single-owner route, not protection against an adversarial writer.
Byte ceilings bound allocations to one document, not a measured RAM-fit claim.
"""
from __future__ import annotations

import inspect
import json
import os
import re
import sqlite3
import stat
import sys
from contextlib import closing, contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.evaluation import gemini_json_f36_notes_stream_v1 as stream
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage import gemini_accounting_family_store_v1 as schema_store
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    validate_current_corpus_manifest_index_v1,
)

CLAIM = "F36_STREAMED_SQLITE_COLD_REPLAY_READBACK_EXPERIMENTAL_ONLY_NOT_ACCEPTANCE"
_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE = _ROOT / "src/bctc_ai"
_SIDECARS = ("-wal", "-shm", "-journal")
_need = stream._need


def _relative(root: Path, value: str) -> Path:
    part = Path(value)
    _need(not part.is_absolute() and ".." not in part.parts, "authority-relative path required")
    return stream._safe(root / part)


def _code_axis() -> list[str]:
    return sorted(str(stream._safe(p)) for p in _PACKAGE.rglob("*.py"))


def _module_axis() -> list[tuple[str, str]]:
    result = []
    for name, module in tuple(sys.modules.items()):
        if name == "bctc_ai" or name.startswith("bctc_ai."):
            origin = getattr(module, "__file__", None)
            if origin is not None:
                path = Path(origin).absolute()
                _need(path.suffix == ".py" and path.is_relative_to(_PACKAGE), "foreign producer import origin")
                result.append((name, str(path)))
    return sorted(result)


def _producer_bindings():
    """Capture real imported production entrypoints, not caller replacements.

    The route module's private IO seams are excluded; this is still a trusted
    fresh-process/cooperative owner API, not hostile in-process isolation.
    """
    result, seen = [], set()
    for name, module in tuple(sys.modules.items()):
        if module is None or not name.startswith("bctc_ai.") or name == __name__:
            continue
        for field, value in tuple(vars(module).items()):
            if not (inspect.isfunction(value) or inspect.isclass(value)):
                continue
            try:
                origin = inspect.getsourcefile(value)
            except TypeError:  # Builtin classes imported into a producer module.
                continue
            if origin is None or not Path(origin).absolute().is_relative_to(_PACKAGE):
                continue
            result.append((module, field, value))
            if inspect.isclass(value) and value not in seen:
                seen.add(value)
                for method, descriptor in tuple(vars(value).items()):
                    function = descriptor.__func__ if isinstance(descriptor, (classmethod, staticmethod)) else descriptor
                    if inspect.isfunction(function):
                        origin = inspect.getsourcefile(function)
                        if origin is not None and Path(origin).absolute().is_relative_to(_PACKAGE):
                            result.append((value, method, descriptor))
    return tuple(result)


def _check_bindings():
    _need(all(vars(owner).get(name) is original for owner, name, original in _PRODUCER_BINDINGS),
          "fresh cold producer callable binding changed")


@dataclass
class _File:
    ref: dict[str, Any]
    handle: BinaryIO
    identity: tuple[int, ...]
    database: bool


class _Held:
    """Hold descriptors, exact hashes and path identities through final barriers."""

    def __init__(self):
        self.files: dict[str, _File] = {}
        self.directories: dict[str, tuple[tuple[int, ...], list[str]]] = {}

    def directory(self, path: Path, *, json_axis: bool = False) -> None:
        path = stream._safe(path)
        status = path.lstat()
        _need(stat.S_ISDIR(status.st_mode), "authority directory required")
        axis = sorted(str(p) for p in path.glob("*.json")) if json_axis else []
        self.directories[str(path)] = (stream._identity(status), axis)

    def add(self, ref: dict[str, Any], *, database: bool = False, chunked: bool = False) -> BinaryIO:
        adapter._ref(ref)
        _need(database or chunked or ref["size_bytes"] <= stream.MAX_TRIAL_BYTES, "non-database authority byte bound")
        path = stream._safe(Path(ref["path"]))
        key = str(path)
        normalized_ref = {**ref, "path": key}
        if key in self.files:
            prior = self.files[key]
            _need(adapter._same(prior.ref, normalized_ref), "conflicting held references")
            prior.database = prior.database or database
            return prior.handle
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        fd = os.open(path, flags)
        handle = os.fdopen(fd, "rb", buffering=0)
        status = os.fstat(fd)
        self.files[key] = _File(canonical_clone_v1(normalized_ref), handle, stream._identity(status), database)
        self.check_one(self.files[key])
        return handle

    def observed(self, path: Path, *, database: bool = False) -> None:
        """Selection-history contents are authenticated by the pinned head loader."""
        path = stream._safe(path)
        with path.open("rb", buffering=0) as handle:
            status = os.fstat(handle.fileno())
            digest = sha256()
            for block in iter(lambda: handle.read(stream.CHUNK_BYTES), b""):
                digest.update(block)
            _need(stream._identity(status) == stream._identity(os.fstat(handle.fileno()))
                  == stream._identity(path.lstat()), "selection changed during capture")
        self.add({"path": str(path), "sha256": digest.hexdigest(), "size_bytes": status.st_size}, database=database)

    def check_one(self, item: _File) -> None:
        path = stream._safe(Path(item.ref["path"]))
        _need(stream._identity(os.fstat(item.handle.fileno())) == item.identity,
              "held input identity changed")
        _need(not item.database or not any(os.path.lexists(str(path) + s) for s in _SIDECARS),
              "held input database sidecar")
        stream._check_file(item.handle, path, item.ref["sha256"], item.ref["size_bytes"])
        _need(stream._identity(os.fstat(item.handle.fileno())) == item.identity,
              "held input identity changed after hash")

    def check(self) -> None:
        for path, (identity, axis) in self.directories.items():
            directory = stream._safe(Path(path))
            _need(stream._identity(directory.lstat()) == identity,
                  "selected authority directory identity changed")
            if axis:
                _need(sorted(str(p) for p in directory.glob("*.json")) == axis,
                      "selected history file axis changed")
        for item in self.files.values():
            self.check_one(item)

    def close(self) -> None:
        for item in self.files.values():
            item.handle.close()


def _integrity(path: Path) -> None:
    """Fresh SQL checks supplement, never replace, held byte hashes."""
    _need(not any(os.path.lexists(str(path) + s) for s in _SIDECARS), "source SQL sidecar")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        _need(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "source SQL integrity")
        _need(connection.execute("PRAGMA foreign_key_check").fetchone() is None, "source SQL foreign keys")


class _Proposal:
    def __init__(self, spool_report, compiled_specs, implementation_refs, producer_refs):
        self.controls = [spool_report, compiled_specs, implementation_refs, producer_refs]
        self.control_sha = canonical_json_sha256_v1(self.controls)
        self.report, self.compiled, self.implementations, self.producers = canonical_clone_v1(self.controls)
        c = self.compiled
        _need(adapter._same(c, adapter.compile_f36_notes_core_specs_v1(c["topology"], c["evaluation"], c["schema"])),
              "compiled proposal differs")
        _need(self.report.get("format_version") == "F36_NOTES_WHOLE_SWEEP_SPOOL_PROPOSAL_V1"
              and self.report.get("stage_boundary") == stream.STAGE_BOUNDARY
              and self.report.get("compiled_specs_sha256") == canonical_json_sha256_v1(c),
              "stage-1 proposal binding differs")
        _need(type(self.implementations) is list and bool(self.implementations)
              and type(self.producers) is list and bool(self.producers), "implementation and producer pins required")
        for ref in [*self.implementations, *self.producers]:
            adapter._ref(ref)
        for refs in (self.implementations, self.producers):
            _need(len({r["path"] for r in refs}) == len(refs), "duplicate code reference")
        self.implementations.sort(key=lambda r: r["path"])
        self.producers.sort(key=lambda r: r["path"])
        self.code_axis = _code_axis()
        _need([r["path"] for r in self.producers] == self.code_axis, "complete exact producer package pins required")
        adapter_ref = next((r for r in self.producers if r["path"] == str(Path(adapter.__file__).absolute())), None)
        _need(adapter_ref is not None and adapter_ref in self.implementations,
              "actual source-replay adapter must belong to implementation axis")
        self.modules = _module_axis()
        self.held = _Held()
        self.array = self.sweep = None

    def __enter__(self):
        try:
            self._open()
            self.check()
            return self
        except BaseException:
            self.held.close()
            raise

    def _open(self):
        c, report = self.compiled, self.report
        source, evaluation = c["topology"]["source"], c["evaluation"]
        for ref in [*self.implementations, *self.producers]:
            self.held.add(ref)
        for key in ("index_ref", "database_ref"):
            self.held.add(source[key], database=key == "database_ref")
        self.held.add(evaluation["primary_store_ref"], database=True)
        for key in ("production_policy_ref", "production_topology_ref", "production_schema_binding_ref"):
            self.held.add(evaluation[key])
        for ref in evaluation["frontier_receipt_refs"].values():
            self.held.add(ref, chunked=True)
        self.held.directory(_ROOT / "config/notes")
        self.held.directory(_ROOT / "config/notes/families")
        for key, pin in evaluation["notes_config_pins"].items():
            path = _ROOT / "config/notes" / key
            self.held.add({"path": str(path), "sha256": pin, "size_bytes": path.stat().st_size})
        # Load only the small index; selected page JSON stays in the source DB.
        index_handle = self.held.files[str(Path(source["index_ref"]["path"]))].handle
        index_handle.seek(0)
        _need(source["index_ref"]["size_bytes"] <= stream.MAX_TRIAL_BYTES, "index byte bound")
        index = validate_current_corpus_manifest_index_v1(json.loads(index_handle.read()))
        root = stream._safe(Path(source["artifact_root"]))
        for doc in index["documents"]:
            selection = _relative(root, doc["selection_ref"]["path"])
            self.held.add({**doc["selection_ref"], "path": str(selection)})
            self.held.directory(selection.parent, json_axis=True)
            for path in sorted(selection.parent.glob("*.json")):
                self.held.observed(path)
            manifest = _relative(root, doc["document_manifest_ref"]["path"])
            self.held.add({**doc["document_manifest_ref"], "path": str(manifest)})
        self.array = self.held.add(report["trial_array_ref"], chunked=True)
        self.sweep = self.held.add(report["sweep_ref"], chunked=True)
        _need(report["trial_array_ref"]["size_bytes"] <= stream.MAX_TOTAL_BYTES
              and report["sweep_ref"]["size_bytes"] <= stream.MAX_TOTAL_BYTES, "spool byte bounds")
        self.run_id = stream.derive_f36_notes_proposed_run_id_v1(
            corpus_index_sha256=source["index_ref"]["sha256"], implementation_refs=self.implementations,
            sweep_id=report["sweep_id"], sweep_sha256=report["sweep_ref"]["sha256"],
        )

    def check(self):
        _need(canonical_json_sha256_v1(self.controls) == self.control_sha, "late proposal/control mutation")
        _check_bindings()
        _need(_code_axis() == self.code_axis and _module_axis() == self.modules, "producer code/import frontier changed")
        self.held.check()

    def __exit__(self, *_exc):
        try:
            self.check()
        finally:
            self.held.close()

    def header(self, query, metrics):
        c = self.compiled
        return {"format_version": c["engine_format_version"], "family_id": adapter.FAMILY,
            "claim_boundary": adapter.CLAIM, "state": "COMPLETE_DOCUMENT_F36_NOTES_STRICT_CORE_PROPOSAL_ONLY",
            "corpus_manifest_index_id": c["topology"]["source"]["corpus_identity"]["corpus_manifest_index_id"],
            "specs": {name: {"value": value, "sha256": canonical_json_sha256_v1(value)} for name, value in (
                ("topology", c["topology"]), ("evaluation", c["evaluation"]), ("schema_binding", c["schema"]))},
            "indexed_query_evidence": query, "metrics": metrics}

    def whole(self, query, metrics):
        _need(adapter._same(query, self.report["indexed_query_evidence"])
              and adapter._same(metrics, self.report["metrics"]), "whole query/count equality failed")
        header = self.header(query, metrics)
        digest = sha256()
        for block in stream._object_chunks(header, self.array):
            digest.update(block)
        _need(self.report["sweep_id"] == "gjfafsv1:sweep:" + digest.hexdigest(), "whole material ID differs")
        header["sweep_id"] = self.report["sweep_id"]
        self.sweep.seek(0)
        for block in stream._object_chunks(header, self.array):
            _need(self.sweep.read(len(block)) == block, "whole canonical sweep bytes differ")
        _need(self.sweep.read(2) == b"\n", "whole stored two-LF domain differs")

    def expected(self):
        docs, offsets = self.compiled["topology"]["source"]["document_axis"], self.report["trial_offsets"]
        _need(type(offsets) is list and len(offsets) == len(docs), "full trial offset axis required")
        self.array.seek(0)
        _need(self.array.read(1) == b"[", "trial array opening")
        end = 1
        for ordinal, (doc, offset) in enumerate(zip(docs, offsets, strict=True), 1):
            _need(type(offset) is dict and set(offset) == {"document_ordinal", "offset", "size_bytes_without_lf",
                  "trial_one_lf_sha256"} and type(offset["document_ordinal"]) is int
                  and offset["document_ordinal"] == ordinal and type(offset["offset"]) is int
                  and offset["offset"] == end and type(offset["size_bytes_without_lf"]) is int
                  and 0 < offset["size_bytes_without_lf"] < stream.MAX_TRIAL_BYTES, "trial offsets/order/bounds differ")
            self.array.seek(end)
            raw = self.array.read(offset["size_bytes_without_lf"]) + b"\n"
            _need(sha256(raw).hexdigest() == offset["trial_one_lf_sha256"], "trial spool hash differs")
            trial = json.loads(raw)
            adapter._validate_f36_notes_trial_v1(trial=trial, doc=doc, compiled_specs=self.compiled)
            _need(canonical_json_bytes_v1(trial) == raw, "noncanonical trial spool")
            end += len(raw) - 1
            if ordinal < len(docs):
                _need(self.array.read(1) == b",", "trial array separator")
                end += 1
            else:
                _need(self.array.read(2) == b"]" and end + 1 == self.report["trial_array_ref"]["size_bytes"],
                      "trial array missing/extra tail")
            yield trial, raw
            del trial, raw


@contextmanager
def _fresh_source(proposal: _Proposal):
    """Fixed factory: opens fresh source/PRIMARY/config; no supplied callback."""
    _check_bindings()
    c = proposal.compiled
    source, evaluation = c["topology"]["source"], c["evaluation"]
    for key, filename in (("production_policy", "tm-operating-expense-evaluation-v1.json"),
                          ("production_topology", "tm-operating-expense-topology-v1.json"),
                          ("production_schema_binding", "tm-operating-expense-schema-binding-v1.json")):
        path = _ROOT / "config/families" / filename
        _need(Path(evaluation[key + "_ref"]["path"]) == path
              and adapter._same(json.loads(path.read_bytes()), evaluation[key]), "live production config differs")
    database, primary = Path(source["database_ref"]["path"]), Path(evaluation["primary_store_ref"]["path"])
    _integrity(database)
    _integrity(primary)
    corpus = adapter.load_corpus_selection_v1(name=source["corpus_name"], root=Path(source["artifact_root"]),
        index_relative_path=str(Path(source["index_ref"]["path"]).relative_to(source["artifact_root"])),
        expected_index_sha256=source["index_ref"]["sha256"], expected_db_sha256=source["database_ref"]["sha256"])
    _need(corpus.db_path == database and adapter._same(corpus.identity(), source["corpus_identity"])
          and adapter._same(adapter._document_axis(corpus), source["document_axis"]), "fresh complete source frontier differs")
    contexts = adapter.load_primary_context_v1(primary, evaluation["primary_store_ref"]["sha256"])
    config = adapter.load_notes_config_v1(_ROOT)
    _need(adapter._same(config.pins, evaluation["notes_config_pins"]), "fresh notes config differs")
    source_object = adapter.NotesSource(corpus, adapter.SourceMetrics())
    try:
        yield adapter.iter_rebuild_f36_notes_trials_v1(
            source=source_object, contexts=contexts, config=config, compiled_specs=c)
    finally:
        _integrity(database)
        _integrity(primary)
        proposal.check()


def _metric_add(metrics, trial):
    metrics["document_count"] += 1
    metrics["mapping_count"] += len(trial["mappings"])
    metrics["ready_count"] += trial["status"] == "READY"
    metrics["unresolved_count"] += trial["status"] == "UNRESOLVED"


def _cold(proposal, connection=None):
    with _fresh_source(proposal) as fresh:
        _compare_cold(proposal, fresh, connection)


def _compare_cold(proposal, fresh, connection=None):
    """Pure comparison seam; public admission always uses the fixed factory."""
    frontier = []
    metrics = {k: 0 for k in ("document_count", "mapping_count", "ready_count", "not_observed_count", "unresolved_count")}
    iterator = iter(fresh)
    for trial, expected_raw in proposal.expected():
        rebuilt = next(iterator, None)
        _need(rebuilt is not None and canonical_json_bytes_v1(rebuilt) == expected_raw,
              "fresh cold original trial differs or is missing")
        if connection is not None:
            _insert_trial(connection, proposal.run_id, rebuilt, expected_raw)
        frontier.append({"document_ordinal": rebuilt["document_ordinal"], "trial_sha256": sha256(expected_raw).hexdigest()})
        _metric_add(metrics, rebuilt)
        del rebuilt, trial, expected_raw
    _need(next(iterator, None) is None, "fresh cold extra original trial")
    proposal.whole(stream._query(frontier, proposal.compiled), metrics)


def _trial_values(run_id, trial, raw):
    return (run_id, trial["document_ordinal"], trial["source_logical_name"], trial["source_sha256"], trial["status"],
        trial["candidate_count"], trial["selected_candidate_id"], len(trial["mappings"]),
        canonical_json_bytes_v1(trial["reasons"]), sha256(raw).hexdigest(), raw)


def _candidate_values(run_id, ordinal, candidate):
    raw = canonical_json_bytes_v1(candidate)
    return (run_id, ordinal, candidate["candidate_id"], candidate["page_json_version_id"], candidate["physical_page"],
        candidate["section_id"], candidate["table_id"], candidate["status"], len(candidate["reasons"]),
        len(candidate["mappings"]), sha256(raw).hexdigest(), raw)


def _mapping_values(run_id, ordinal, index, mapping):
    role = mapping.get("role", mapping.get("movement_role"))
    _need(type(role) is str and bool(role) and ("role" not in mapping or "movement_role" not in mapping
          or mapping["role"] == mapping["movement_role"]), "typed mapping role required")
    raw = canonical_json_bytes_v1(mapping)
    return (run_id, ordinal, index, mapping["report_norm_id"], role, mapping["row_id"], sha256(raw).hexdigest(), raw)


def _insert_trial(connection, run_id, trial, raw):
    ordinal = trial["document_ordinal"]
    connection.execute("INSERT INTO family_trial VALUES (?,?,?,?,?,?,?,?,?,?,?)", _trial_values(run_id, trial, raw))
    for candidate in trial["candidates"]:
        connection.execute("INSERT INTO family_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           _candidate_values(run_id, ordinal, candidate))
    for index, mapping in enumerate(trial["mappings"], 1):
        connection.execute("INSERT INTO family_mapping VALUES (?,?,?,?,?,?,?,?)",
                           _mapping_values(run_id, ordinal, index, mapping))


def _run_values(proposal):
    c, report = proposal.compiled, proposal.report
    m, source = report["metrics"], c["topology"]["source"]
    return (proposal.run_id, report["sweep_id"], adapter.FAMILY, c["engine_format_version"],
        source["corpus_identity"]["corpus_manifest_index_id"], source["index_ref"]["sha256"],
        canonical_json_sha256_v1(c["topology"]), canonical_json_sha256_v1(c["evaluation"]),
        canonical_json_sha256_v1(c["schema"]), canonical_json_sha256_v1(proposal.implementations),
        canonical_json_bytes_v1(proposal.implementations), report["sweep_ref"]["sha256"],
        m["document_count"], m["ready_count"], m["not_observed_count"], m["unresolved_count"], m["mapping_count"])


_RUN_COLUMNS = ("family_run_id,sweep_id,family_id,sweep_format_version,corpus_manifest_index_id,corpus_index_sha256,"
    "topology_spec_sha256,evaluation_spec_sha256,schema_binding_spec_sha256,implementation_axis_sha256,"
    "implementation_refs_json,sweep_sha256,document_count,ready_count,not_observed_count,unresolved_count,mapping_count")


def _schema(connection):
    expected = {}
    for statement in schema_store._SCHEMA.split(";"):
        match = re.fullmatch(r"\s*CREATE (TABLE|INDEX) (\w+)[\s\S]*", statement)
        if match:
            expected[match[2]] = (match[1].lower(), statement.strip())
    _need(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")
          .fetchone() == (len(expected),), "exact derived schema object count differs")
    for name, (kind, sql) in expected.items():
        _need(connection.execute("SELECT type,length(CAST(sql AS BLOB)) FROM sqlite_master WHERE name=?", (name,)).fetchone()
              == (kind, len(sql.encode("utf-8"))), "exact derived schema byte size differs")
        _need(connection.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone() == (sql,),
              "exact derived schema differs")


def _size_guard(connection, table, predicate, parameters, values):
    # Text as UTF-8 bytes also preserves embedded NULs in SQLite length checks.
    variable = [(name, value) for name, value in values if type(value) in {str, bytes}]
    lengths = connection.execute("SELECT " + ",".join("length(CAST(" + name + " AS BLOB))" for name, _ in variable)
        + " FROM " + table + " WHERE " + predicate, parameters).fetchmany(2)
    _need(lengths == [tuple(len(value.encode("utf-8") if type(value) is str else value)
                           for _, value in variable)], "stored trace byte sizes differ")


def _exact_row(connection, table, predicate, parameters, expected):
    # Check every variable field before Python can allocate an untrusted trace.
    columns = [row[1] for row in connection.execute("PRAGMA table_info(" + table + ")")]
    _size_guard(connection, table, predicate, parameters, zip(columns, expected, strict=True))
    actual = connection.execute("SELECT * FROM " + table + " WHERE " + predicate, parameters).fetchone()
    _need(actual is not None and tuple(actual) == expected, "stored " + table + " complete trace differs")


def _verify_store(connection, proposal):
    """No whole-BLOB SELECT; every normalized column and content byte is checked."""
    _schema(connection)
    _size_guard(connection, "store_identity", "1", (), (("format_version", schema_store.FORMAT_VERSION),))
    _need(connection.execute("SELECT * FROM store_identity").fetchmany(2) == [(1, schema_store.FORMAT_VERSION)],
          "derived store identity differs")
    _size_guard(connection, "family_run", "1", (), zip(_RUN_COLUMNS.split(","), _run_values(proposal), strict=True))
    rows = connection.execute("SELECT rowid," + _RUN_COLUMNS + ",length(sweep_bytes) FROM family_run").fetchmany(2)
    _need(len(rows) == 1 and tuple(rows[0][1:-1]) == _run_values(proposal)
          and rows[0][-1] == proposal.report["sweep_ref"]["size_bytes"], "stored run metadata/counts differ")
    proposal.sweep.seek(0)
    digest = sha256()
    with connection.blobopen("family_run", "sweep_bytes", rows[0][0], readonly=True) as blob:
        while block := blob.read(stream.CHUNK_BYTES):
            digest.update(block)
            _need(proposal.sweep.read(len(block)) == block, "stored whole BLOB byte mismatch")
    _need(proposal.sweep.read(1) == b"" and digest.hexdigest() == proposal.report["sweep_ref"]["sha256"],
          "stored whole BLOB hash differs")
    counts = {"family_trial": 0, "family_candidate": 0, "family_mapping": 0}
    for trial, raw in proposal.expected():
        ordinal = trial["document_ordinal"]
        _exact_row(connection, "family_trial", "family_run_id=? AND document_ordinal=?", (proposal.run_id, ordinal),
                   _trial_values(proposal.run_id, trial, raw))
        counts["family_trial"] += 1
        for candidate in trial["candidates"]:
            _exact_row(connection, "family_candidate", "family_run_id=? AND document_ordinal=? AND candidate_id=?",
                       (proposal.run_id, ordinal, candidate["candidate_id"]),
                       _candidate_values(proposal.run_id, ordinal, candidate))
            counts["family_candidate"] += 1
        for index, mapping in enumerate(trial["mappings"], 1):
            _exact_row(connection, "family_mapping", "family_run_id=? AND document_ordinal=? AND mapping_ordinal=?",
                       (proposal.run_id, ordinal, index), _mapping_values(proposal.run_id, ordinal, index, mapping))
            counts["family_mapping"] += 1
    for table, count in counts.items():
        _need(connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == count, "stored complete trace count differs")
    for table in ("family_current_selection", "family_selection_event", "family_export"):
        _need(connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0, "selection/export forbidden in streamed proposal")
    _size_guard(connection, "family_run_execution", "1", (), (("family_run_id", proposal.run_id), ("run_kind", "EXPERIMENTAL")))
    _need(connection.execute("SELECT family_run_id,run_kind FROM family_run_execution").fetchmany(2)
          == [(proposal.run_id, "EXPERIMENTAL")], "single experimental execution required")
    _need(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "derived SQL integrity")
    _need(connection.execute("PRAGMA foreign_key_check").fetchone() is None, "derived SQL foreign keys")


def _destination(path, proposal):
    path = stream._safe(Path(path))
    _need(path.parent.is_dir() and not os.path.lexists(path)
          and not any(os.path.lexists(str(path) + s) for s in _SIDECARS), "new exclusive destination required")
    _need(not any(os.path.lexists(p / ".git") for p in path.parents), "derived destination must be outside Git")
    root = Path(proposal.compiled["topology"]["source"]["artifact_root"])
    _need(not path.is_relative_to(root), "derived destination overlaps source authority")
    _need(str(path) not in proposal.held.files, "derived destination overlaps held input")
    return path


def _connect(path, *, readonly=False):
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro&immutable=1" if readonly else "?mode=rw"), uri=True)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA cache_size=-8192")
    connection.execute("PRAGMA mmap_size=0")
    if readonly:
        connection.execute("PRAGMA query_only=ON")
    return connection


def ingest_f36_notes_streamed_sweep_v1(path: Path, *, spool_report: dict[str, Any], compiled_specs: dict[str, Any],
        implementation_refs: list[dict[str, Any]], producer_refs: list[dict[str, Any]],
        run_kind: str = "EXPERIMENTAL") -> dict[str, Any]:
    """Persist ONE full original axis or roll back; existing destinations rejected.

    Owner must budget SSD for two spools, whole BLOB, repeated normalized traces,
    SQLite journal and source inputs. No memory/disk availability is inferred.
    Failed new stores are retained for diagnosis and must never be resumed here.
    """
    _need(run_kind == "EXPERIMENTAL", "only EXPERIMENTAL proposals permitted")
    connection, output_fd = None, None
    try:
        with _Proposal(spool_report, compiled_specs, implementation_refs, producer_refs) as proposal:
            path = _destination(path, proposal)
            output_fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_BINARY", 0), 0o600)
            output_identity = stream._identity(os.fstat(output_fd))[:3]
            connection = _connect(path)
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.executescript(schema_store._SCHEMA)
            connection.execute("INSERT INTO store_identity VALUES (1,?)", (schema_store.FORMAT_VERSION,))
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
            values = _run_values(proposal)
            connection.execute("INSERT INTO family_run(" + _RUN_COLUMNS + ",sweep_bytes) VALUES ("
                + ",".join("?" for _ in values) + ",zeroblob(?))", (*values, proposal.report["sweep_ref"]["size_bytes"]))
            rowid = connection.execute("SELECT rowid FROM family_run WHERE family_run_id=?", (proposal.run_id,)).fetchone()[0]
            proposal.sweep.seek(0)
            with connection.blobopen("family_run", "sweep_bytes", rowid) as blob:
                for block in iter(lambda: proposal.sweep.read(stream.CHUNK_BYTES), b""):
                    blob.write(block)
            _cold(proposal, connection)
            connection.execute("INSERT INTO family_run_execution(family_run_id,run_kind) VALUES (?,?)",
                               (proposal.run_id, "EXPERIMENTAL"))
            _verify_store(connection, proposal)
            proposal.check()
            _need(stream._identity(os.fstat(output_fd)) == stream._identity(stream._safe(path).lstat())
                  and stream._identity(os.fstat(output_fd))[:3] == output_identity, "new output path/identity changed")
            result = {"family_run_id": proposal.run_id, "family_id": adapter.FAMILY, "run_kind": "EXPERIMENTAL",
                "sweep_id": proposal.report["sweep_id"], "sweep_sha256": proposal.report["sweep_ref"]["sha256"],
                "claim_boundary": CLAIM}
        # All source/spool/control final checks completed before transaction commit.
        connection.commit()
    except BaseException:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()
        if output_fd is not None:
            os.close(output_fd)
    # Reopen the committed database and independently check every persisted byte.
    with _Proposal(spool_report, compiled_specs, implementation_refs, producer_refs) as proposal:
        with _held_store(path) as (readback, _held):
            proposal.whole(proposal.report["indexed_query_evidence"], proposal.report["metrics"])
            _verify_store(readback, proposal)
    return result


@contextmanager
def _held_store(path):
    path = stream._safe(Path(path))
    held = _Held()
    connection = None
    try:
        held.observed(path, database=True)
        held.check()
        connection = _connect(path, readonly=True)
        _schema(connection)
        _size_guard(connection, "store_identity", "1", (), (("format_version", schema_store.FORMAT_VERSION),))
        _need(connection.execute("SELECT * FROM store_identity").fetchmany(2) == [(1, schema_store.FORMAT_VERSION)],
              "derived store identity differs")
        yield connection, held
    finally:
        try:
            held.check()
        finally:
            if connection is not None:
                connection.close()
            held.close()


class _Reader:
    def __init__(self, connection, proposal):
        self.connection, self.proposal, self.active = connection, proposal, True

    def original_trial(self, document_ordinal: int) -> dict[str, Any]:
        """One original slot only, within an authenticated live context."""
        _need(self.active and type(document_ordinal) is int
              and 1 <= document_ordinal <= len(self.proposal.report["trial_offsets"]), "live original-trial ordinal required")
        offset = self.proposal.report["trial_offsets"][document_ordinal - 1]
        parameters = (self.proposal.run_id, document_ordinal)
        _need(self.connection.execute("SELECT length(trial_bytes) FROM family_trial WHERE family_run_id=? AND document_ordinal=?",
              parameters).fetchone() == (offset["size_bytes_without_lf"] + 1,), "bounded stored original trial required")
        row = self.connection.execute("SELECT trial_bytes FROM family_trial WHERE family_run_id=? AND document_ordinal=?",
                                      parameters).fetchone()
        self.proposal.array.seek(offset["offset"])
        expected = self.proposal.array.read(offset["size_bytes_without_lf"]) + b"\n"
        _need(row[0] == expected, "stored original trial changed")
        return adapter.validate_f36_notes_trial_v1(trial=json.loads(row[0]), document_ordinal=document_ordinal,
                                                 compiled_specs=self.proposal.compiled)


@contextmanager
def open_f36_notes_streamed_run_v1(path: Path, *, spool_report: dict[str, Any], compiled_specs: dict[str, Any],
        implementation_refs: list[dict[str, Any]], producer_refs: list[dict[str, Any]]):
    """Full fresh cold replay + committed readback, then bounded original accessor.

    The reader expires at context exit. No persisted PASS flag or arbitrary
    replay callback can replace these source and complete-content checks.
    """
    with _Proposal(spool_report, compiled_specs, implementation_refs, producer_refs) as proposal:
        with _held_store(path) as (connection, held):
            _cold(proposal)
            _verify_store(connection, proposal)
            reader = _Reader(connection, proposal)
            try:
                yield reader
            finally:
                reader.active = False
                _verify_store(connection, proposal)
                held.check()


_PRODUCER_BINDINGS = _producer_bindings()
