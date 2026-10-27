"""F36 proposal spooling only; streamed persistence/cold replay are NOT implemented.

The output is byte-compatible with the existing whole sweep. Structural trial
validation is reused, not replaced by caller approval. An IO owner must still
authenticate/hold every source/code input and complete the future streamed
SQLite, fresh cold replay and exact persisted readback route. No OFFICIAL or
family acceptance operation is exposed here.
"""
from __future__ import annotations

import os
import stat
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO, Iterable

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

CHUNK_BYTES = 1024 * 1024
MAX_TRIAL_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024 - 1
STAGE_BOUNDARY = "SPOOL_PROPOSAL_ONLY_STREAMED_PERSISTENCE_COLD_REPLAY_READBACK_NOT_IMPLEMENTED"


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise adapter.F36NotesCoreAdapterError("F36 stream: " + message)


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return tuple(getattr(value, field) for field in (
        "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns",
    ))


def _safe(path: Path) -> Path:
    _need(path.is_absolute() and ".." not in path.parts, "absolute path without parent traversal required")
    _need(not any(p.is_symlink() for p in (path, *path.parents)), "symlink path is not permitted")
    return path


def _new_directory(path: Path, compiled: dict[str, Any]) -> Path:
    path = _safe(Path(path))
    _need(not os.path.lexists(path) and path.parent.is_dir(), "new directory with existing parent required")
    _need(not any(os.path.lexists(parent / ".git") for parent in path.parents), "scratch must be outside Git")
    source = compiled["topology"]["source"]
    authorities = [Path(source["artifact_root"]), Path(source["index_ref"]["path"]),
                   Path(source["database_ref"]["path"]), Path(compiled["evaluation"]["primary_store_ref"]["path"])]
    for authority in authorities:
        authority = _safe(authority)
        _need(not path.is_relative_to(authority) and not authority.is_relative_to(path), "scratch overlaps source authority")
    path.mkdir(mode=0o700)
    return path


def _check_file(stream: BinaryIO, path: Path, expected_sha: str, expected_bytes: int) -> dict[str, Any]:
    before = os.fstat(stream.fileno())
    _need(stat.S_ISREG(before.st_mode) and before.st_size == expected_bytes
          and _identity(before) == _identity(_safe(path).lstat()), "held spool path/size differs")
    value = sha256()
    stream.seek(0)
    for block in iter(lambda: stream.read(CHUNK_BYTES), b""):
        value.update(block)
    _need(value.hexdigest() == expected_sha
          and _identity(before) == _identity(os.fstat(stream.fileno())) == _identity(_safe(path).lstat()),
          "held spool bytes or identity changed")
    return {"path": str(path), "sha256": expected_sha, "size_bytes": expected_bytes}


def _object_chunks(header: dict[str, Any], trials: BinaryIO):
    """Exact canonical JSON grammar; the trial array was individually validated."""
    yield b"{"
    for index, key in enumerate(sorted([*header, "trials"])):
        if index:
            yield b","
        yield canonical_json_bytes_v1(key)[:-1]
        yield b":"
        if key == "trials":
            trials.seek(0)
            yield from iter(lambda: trials.read(CHUNK_BYTES), b"")
        else:
            yield canonical_json_bytes_v1(header[key])[:-1]
    yield b"}\n"


def _query(frontier: list[dict[str, Any]], compiled: dict[str, Any]) -> dict[str, Any]:
    material = {
        "format_version": adapter.COMPACT_QUERY_FORMAT if adapter._compact(compiled) else adapter.QUERY_FORMAT,
        "family_id": adapter.FAMILY,
        "selected_document_axis": compiled["topology"]["source"]["document_axis"],
        "frontier_receipt_refs": compiled["evaluation"]["frontier_receipt_refs"],
        "trial_frontier": frontier,
    }
    return {**canonical_clone_v1(material),
            "query_evidence_id": "gjf36nieqv1:evidence:" + canonical_json_sha256_v1(material)}


def write_f36_notes_sweep_spool_v1(
    *, trials: Iterable[dict[str, Any]], compiled_specs: dict[str, Any],
    corpus_manifest_index_id: str, scratch_directory: Path,
    max_trial_bytes: int = MAX_TRIAL_BYTES, max_total_bytes: int = MAX_TOTAL_BYTES,
    expected_query_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exhaust one full original axis into an exclusive, unaccepted scratch spool.

    A public iterable is NOT an authenticated run/session capability. This API
    performs only the same pure per-trial consistency checks as the old sweep
    builder. It cannot persist, select, resume or claim a fresh source replay.
    Partial scratch files are deliberately retained on failure.
    """
    _need(type(max_trial_bytes) is int and 0 < max_trial_bytes <= MAX_TRIAL_BYTES
          and type(max_total_bytes) is int and 0 < max_total_bytes <= MAX_TOTAL_BYTES,
          "reviewed positive byte bounds required")
    compiled = adapter.compile_f36_notes_core_specs_v1(
        compiled_specs["topology"], compiled_specs["evaluation"], compiled_specs["schema"],
    )
    original_compiled_sha = canonical_json_sha256_v1(compiled)
    _need(canonical_json_sha256_v1(compiled_specs) == original_compiled_sha, "compiled authority differs")
    _need(expected_query_evidence is None or type(expected_query_evidence) is dict, "expected query must be an object")
    expected_query_snapshot = None if expected_query_evidence is None else canonical_clone_v1(expected_query_evidence)

    def check_controls() -> None:
        _need(canonical_json_sha256_v1(compiled_specs) == original_compiled_sha, "late compiled input change")
        _need(expected_query_snapshot is None or adapter._same(expected_query_evidence, expected_query_snapshot),
              "late expected query input change")

    _need(type(corpus_manifest_index_id) is str and corpus_manifest_index_id.startswith("gjfccmiv1:index:")
          and corpus_manifest_index_id == compiled["topology"]["source"]["corpus_identity"].get("corpus_manifest_index_id"),
          "corpus identity differs")
    docs = compiled["topology"]["source"]["document_axis"]
    scratch = _new_directory(scratch_directory, compiled)
    array_path, sweep_path = scratch / "trials-array.json", scratch / "f36-whole-sweep.json"
    frontier, offsets = [], []
    metrics = {"document_count": 0, "mapping_count": 0, "ready_count": 0,
               "not_observed_count": 0, "unresolved_count": 0}
    array_sha, array_size = sha256(), 0
    with array_path.open("x+b", buffering=0) as spool:
        def append(raw: bytes) -> None:
            nonlocal array_size
            _need(array_size + len(raw) <= max_total_bytes, "trial array exceeds byte budget")
            _need(spool.write(raw) == len(raw), "trial array write was incomplete")
            array_sha.update(raw)
            array_size += len(raw)

        append(b"[")
        for ordinal, trial in enumerate(trials, 1):
            _need(ordinal <= len(docs), "extra original trial")
            check_controls()
            adapter._validate_f36_notes_trial_v1(trial=trial, doc=docs[ordinal - 1], compiled_specs=compiled)
            raw = canonical_json_bytes_v1(trial)
            _need(0 < len(raw) <= max_trial_bytes and raw.endswith(b"\n"), "trial exceeds byte bound or canonical LF missing")
            if ordinal > 1:
                append(b",")
            offsets.append({"document_ordinal": ordinal, "offset": array_size, "size_bytes_without_lf": len(raw) - 1,
                            "trial_one_lf_sha256": sha256(raw).hexdigest()})
            append(raw[:-1])  # Exactly ONE protocol LF, never arbitrary whitespace.
            frontier.append({"document_ordinal": ordinal, "trial_sha256": sha256(raw).hexdigest()})
            metrics["document_count"] += 1
            metrics["mapping_count"] += len(trial["mappings"])
            metrics["ready_count"] += trial["status"] == "READY"
            metrics["unresolved_count"] += trial["status"] == "UNRESOLVED"
            del trial, raw
        _need(metrics["document_count"] == len(docs), "missing original trial; full denominator required")
        check_controls()
        append(b"]")
        spool.flush()
        os.fsync(spool.fileno())
        array_ref = _check_file(spool, array_path, array_sha.hexdigest(), array_size)
        query = _query(frontier, compiled)
        _need(expected_query_snapshot is None or adapter._same(expected_query_snapshot, query), "complete query/frontier differs")
        header = {
            "format_version": compiled["engine_format_version"], "family_id": adapter.FAMILY,
            "claim_boundary": adapter.CLAIM, "state": "COMPLETE_DOCUMENT_F36_NOTES_STRICT_CORE_PROPOSAL_ONLY",
            "corpus_manifest_index_id": corpus_manifest_index_id,
            "specs": {name: {"value": canonical_clone_v1(value), "sha256": canonical_json_sha256_v1(value)}
                      for name, value in (("topology", compiled["topology"]), ("evaluation", compiled["evaluation"]),
                                          ("schema_binding", compiled["schema"]))},
            "indexed_query_evidence": query, "metrics": metrics,
        }
        material_sha = sha256()
        for block in _object_chunks(header, spool):
            material_sha.update(block)
        _check_file(spool, array_path, array_sha.hexdigest(), array_size)
        sweep_id = "gjfafsv1:sweep:" + material_sha.hexdigest()
        header["sweep_id"] = sweep_id
        sweep_sha, sweep_size = sha256(), 0
        with sweep_path.open("x+b", buffering=0) as output:
            for block in _object_chunks(header, spool):
                _need(sweep_size + len(block) <= max_total_bytes, "whole sweep exceeds byte budget")
                _need(output.write(block) == len(block), "whole sweep write was incomplete")
                sweep_sha.update(block)
                sweep_size += len(block)
            _need(sweep_size + 1 <= max_total_bytes, "whole sweep exceeds byte budget")
            _need(output.write(b"\n") == 1, "store-domain LF write incomplete")
            sweep_sha.update(b"\n")
            sweep_size += 1
            output.flush()
            os.fsync(output.fileno())
            sweep_ref = _check_file(output, sweep_path, sweep_sha.hexdigest(), sweep_size)
            _check_file(spool, array_path, array_sha.hexdigest(), array_size)
            check_controls()
    return {
        "format_version": "F36_NOTES_WHOLE_SWEEP_SPOOL_PROPOSAL_V1", "stage_boundary": STAGE_BOUNDARY,
        "sweep_id": sweep_id, "sweep_ref": sweep_ref, "trial_array_ref": array_ref,
        "trial_offsets": offsets, "metrics": metrics, "indexed_query_evidence": query,
        "compiled_specs_sha256": original_compiled_sha,
        "source_authentication": "CALLER_IO_FRONTIER_BARRIERS_REQUIRED_NOT_CLAIMED_BY_SPOOL_WRITER",
        "sqlite_ingest_cold_replay_and_persisted_readback": "NOT_IMPLEMENTED",
    }


def derive_f36_notes_proposed_run_id_v1(*, corpus_index_sha256: str,
                                       implementation_refs: list[dict[str, Any]],
                                       sweep_id: str, sweep_sha256: str) -> str:
    """Pure old store ID grammar; declarations are not authenticated by this API."""
    _need(type(implementation_refs) is list and bool(implementation_refs), "implementation declarations required")
    for ref in implementation_refs:
        adapter._ref(ref)
    _need(len({ref["path"] for ref in implementation_refs}) == len(implementation_refs),
          "duplicate implementation declaration")
    implementations = sorted(implementation_refs, key=lambda ref: ref["path"])
    _need(type(corpus_index_sha256) is str and adapter._SHA.fullmatch(corpus_index_sha256) is not None
          and type(sweep_sha256) is str and adapter._SHA.fullmatch(sweep_sha256) is not None
          and type(sweep_id) is str and sweep_id.startswith("gjfafsv1:sweep:")
          and adapter._SHA.fullmatch(sweep_id.removeprefix("gjfafsv1:sweep:")) is not None,
          "typed ID declaration required")
    material = {"corpus_index_sha256": corpus_index_sha256,
                "implementation_axis_sha256": canonical_json_sha256_v1(implementations),
                "sweep_id": sweep_id, "sweep_sha256": sweep_sha256}
    return "gjfafstorev1:run:" + canonical_json_sha256_v1(material)
