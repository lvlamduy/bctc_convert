"""Single-load ORIGINAL source boundary and raw-MONEY denominator for Family 39.

The operation context authenticates actual read-only database bytes and pinned
index/manifest/selection files. Only this boundary calls the original loader;
callers cannot supply page objects or approval flags. Returned values remain
provisional until the owning context exits successfully. This is a denominator,
not a family disposition, PDF verification, or permission to export a value.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import stat
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    validate_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (
    load_income_tax_source_page_json_versions_v1,
)

FORMAT_VERSION = "F39_AUTHENTICATED_ORIGINAL_RAW_MONEY_CELL_CENSUS_V1"
RELEVANCE = "UNASSESSED_NO_FAMILY_OWNER_ROLE_LANE_OR_ACCEPTANCE_DECISION"
_LOCATOR_KEYS = (
    "document_id", "document_ordinal", "source_logical_name", "source_sha256",
    "page_json_version_id", "physical_page", "selected_page_ordinal",
)
_VALUE_KINDS = {"MONEY", "PERCENT", "COUNT", "TEXT", "UNKNOWN"}
_PROMPT_ENCODING_SCOPE_RELATIVE = "config/families/tm-income-tax-common204-prompt-frontier-encoding-v1.json"
_PROMPT_ENCODING_SCOPE_PATH = Path(__file__).resolve().parents[3] / _PROMPT_ENCODING_SCOPE_RELATIVE
_PROMPT_ENCODING_SCOPE_SHA256 = "2e23473ce9246764d3a37d112f6f42a567824ebd053834e8299641f8b5bdd479"
_PROMPT_ENCODING_SCOPE_SIZE_BYTES = 56250
_PROMPT_ENCODING_DIAGNOSTIC_SCOPE_SHA256 = "218e69be9ccf1f620a3a4552f9f1d824b22b1aecee32a9641273285161b53151"


class GeminiIncomeTaxRawMoneyCensusV1Error(ValueError):
    """The original source or exact denominator cannot be authenticated."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise GeminiIncomeTaxRawMoneyCensusV1Error(message)


def _safe_absolute(path: Path) -> Path:
    path = Path(path)
    _require(path.is_absolute() and ".." not in path.parts, "Explicit absolute authority path required")
    for part in (path, *path.parents):
        _require(not part.is_symlink(), "Symlink authority path prohibited")
    _require(path.resolve(strict=True) == path, "Authority path is not its resolved path")
    return path


def _reference(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(type(value) is dict and set(value) == {"path", "sha256", "size_bytes"}, "Content reference fields differ")
    result = canonical_clone_v1(value)
    _require(type(result["path"]) is str and bool(result["path"]), "Content reference path missing")
    _require(type(result["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", result["sha256"]) is not None, "Invalid content SHA")
    _require(type(result["size_bytes"]) is int and result["size_bytes"] > 0, "Invalid content byte count")
    return result


def _content_path(root: Path, reference: Mapping[str, Any]) -> Path:
    ref = _reference(reference)
    relative = ref["path"]
    _require(
        "\\" not in relative and not PurePosixPath(relative).is_absolute()
        and not PureWindowsPath(relative).drive and ".." not in relative.split("/")
        and all(part not in {"", "."} for part in relative.split("/")),
        "Content reference escapes artifact root",
    )
    path = _safe_absolute(root / relative)
    _require(path.is_relative_to(root) and path.is_file(), "Content reference outside artifact root")
    return path


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _fd_sha256(descriptor: int) -> str:
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    digest = sha256()
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest()


def _no_sidecars(path: Path) -> None:
    _require(not any(os.path.lexists(str(path) + suffix) for suffix in ("-journal", "-shm", "-wal")), "Source SQLite sidecar present")


def _current_task():
    try:
        return asyncio.current_task()
    except RuntimeError:
        return None


def _json_object(raw: bytes) -> dict[str, Any]:
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "Duplicate authority JSON key")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    _require(type(value) is dict, "Authority JSON must be an object")
    canonical_json_bytes_v1(value)
    return value


def _load_registered_prompt_encoding_scope(source) -> dict[str, Any]:
    """Read one independently pinned encoding scope, not a caller exception.

    The restore evidence proves only an exact SHA-body versus variant encoding
    distinction. It grants no financial, PDF, period, unit or export authority.
    The actual file joins the source context's before/finally authority barriers.
    """
    path = _PROMPT_ENCODING_SCOPE_PATH
    value = source._read_authority(path.parent, {
        "path": path.name, "sha256": _PROMPT_ENCODING_SCOPE_SHA256,
        "size_bytes": _PROMPT_ENCODING_SCOPE_SIZE_BYTES,
    })
    _require(set(value) == {
        "format_version", "family_id", "authority", "corpus_manifest_index_id",
        "corpus_index_ref", "database_ref", "diagnostic_scope_sha256",
        "simple_prompt_sha256", "scope", "source_bindings", "lineage",
    } and value["format_version"] == "F39_REGISTERED_COMMON204_PROMPT_FRONTIER_ENCODING_V1"
       and value["family_id"] == "INCOME_TAX"
       and value["authority"] == "RESTORE_AUTHENTICATED_EXACT_SCOPE_PROMPT_DIGEST_ENCODING_ONLY",
       "Registered prompt encoding scope fields differ")
    scope, bindings = value["scope"], value["source_bindings"]
    _require(type(scope) is list and bool(scope) and type(bindings) is list
             and len(scope) == len(bindings)
             and value["diagnostic_scope_sha256"] == _PROMPT_ENCODING_DIAGNOSTIC_SCOPE_SHA256
             == canonical_json_sha256_v1(scope), "Registered prompt encoding scope digest differs")
    ordinals = [item["source_ordinal"] for item in scope]
    _require(all(type(ordinal) is int and ordinal > 0 for ordinal in ordinals)
             and ordinals == sorted(set(ordinals))
             and all(type(item["source_ordinal"]) is int for item in bindings)
             and [item["source_ordinal"] for item in bindings] == ordinals
             and all(type(item["page_count"]) is int and item["page_count"] > 0
                     and item["selected_page_json_version_ids_exactly_equal_full271"] is True
                     and item["page_image_frontier_replays_from_sqlite"] is True for item in scope),
             "Registered prompt encoding source axis differs")
    _reference(value["corpus_index_ref"])
    _reference(value["database_ref"])
    return value


def _registered_prompt_encoding_witness(source, document, loaded, *, variant_frontier_sha256):
    """Admit SHA-body encoding only for the pinned original corpus/selection.

    Every other corpus/document retains the variant-only rule. All inputs here
    came from this context's official single load, never a supplied receipt.
    """
    scope = json.loads(source._prompt_encoding_scope_bytes)
    selection, indexed = document["selection"], document["index_document"]
    recorded = selection["page_prompt_frontier_sha256"]
    corpus_matches = (
        source._index_id == scope["corpus_manifest_index_id"]
        and same_typed_json_v1(source._index_ref, scope["corpus_index_ref"])
        and same_typed_json_v1(source._database_ref, scope["database_ref"])
    )
    matches = [item for item in scope["scope"]
               if item["source_ordinal"] == indexed["source_ordinal"]] if corpus_matches else []
    if not matches:
        _require(recorded == variant_frontier_sha256,
                 "Selected image/prompt frontier differs from original source")
        return None
    _require(len(matches) == 1, "Registered prompt encoding source is not unique")
    expected = matches[0]
    binding = next(item for item in scope["source_bindings"]
                   if item["source_ordinal"] == indexed["source_ordinal"])
    _require(same_typed_json_v1({key: indexed.get(key) for key in binding}, binding)
             and expected["relative_path"] == indexed["relative_path"]
             and expected["page_count"] == indexed["page_count"] == len(loaded)
             and same_typed_json_v1(expected["common_selection_ref"], indexed["selection_ref"])
             and canonical_json_sha256_v1(document["ids"])
             == expected["selected_page_json_version_ids_sha256"],
             "Registered prompt encoding document/selection frontier differs")
    manifest = document["manifest"]
    contract = manifest.get("extraction_contract")
    simple_sha = scope["simple_prompt_sha256"]
    _require(manifest.get("format_version") == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
             and type(contract) is dict and contract.get("prompt_sha256") == simple_sha
             and "page_prompt_sha256s" not in contract
             and all(row["prompt_variant"] == "simple" and row["prompt_sha256"] == simple_sha
                     for row in loaded), "Registered prompt encoding body/manifest contract differs")
    digest_frontier_sha256 = canonical_json_sha256_v1([
        {"physical_page": row["physical_page"], "prompt_sha256": row["prompt_sha256"]}
        for row in loaded
    ])
    _require(recorded == expected["selection_prompt_frontier_sha256"] == digest_frontier_sha256
             and variant_frontier_sha256 == expected["replayed_prompt_frontier_sha256"]
             and recorded != variant_frontier_sha256,
             "Registered prompt encoding does not replay from original source")
    material = {
        "format_version": "F39_REGISTERED_PROMPT_FRONTIER_ENCODING_WITNESS_V1",
        "encoding": "PHYSICAL_PAGE_PROMPT_SHA256_OBSERVED",
        "registered_scope_ref": {"path": _PROMPT_ENCODING_SCOPE_RELATIVE,
                                 "sha256": _PROMPT_ENCODING_SCOPE_SHA256,
                                 "size_bytes": _PROMPT_ENCODING_SCOPE_SIZE_BYTES},
        "diagnostic_scope_sha256": scope["diagnostic_scope_sha256"],
        "corpus_manifest_index_id": source._index_id,
        "source_ordinal": indexed["source_ordinal"],
        "selection_ref": canonical_clone_v1(indexed["selection_ref"]),
        "selected_page_json_version_ids_sha256": canonical_json_sha256_v1(document["ids"]),
        "recorded_sha256": recorded,
        "recomputed_sha256": digest_frontier_sha256,
        "variant_encoding_sha256": variant_frontier_sha256,
        "prompt_body_sha256": simple_sha,
        "source_values_or_period_keys_modified": False,
        "financial_or_pdf_or_export_permission_granted": False,
    }
    return {**material, "witness_id": "f39promptencodingv1:" + canonical_json_sha256_v1(material)}


class IncomeTaxOriginalCensusSourceV1:
    """Owned operation capability; construct with the public context factory.

    The trusted Python runtime must not mutate this private state. JSON receipts
    cannot instantiate an authenticated source. No source-dependent READY or
    census result is cached. Each document may be loaded once per context.
    """

    def __init__(self) -> None:
        raise GeminiIncomeTaxRawMoneyCensusV1Error("Use open_income_tax_original_census_source_v1")

    def _active(self) -> None:
        _require(not self._closed and not self._invalidated, "Source context closed or invalidated")
        if threading.get_ident() != self._owner or _current_task() is not self._task:
            self._invalidated = True
            raise GeminiIncomeTaxRawMoneyCensusV1Error("Source context crossed its owning thread/task")

    @property
    def corpus_index(self) -> dict[str, Any]:
        self._active()
        return json.loads(self._index_bytes)

    @property
    def document_authorities(self) -> list[dict[str, Any]]:
        self._active()
        return [json.loads(raw) for raw in self._document_bytes]

    def _read_authority(self, root: Path, reference: Mapping[str, Any]) -> dict[str, Any]:
        ref = _reference(reference)
        path = _content_path(root, ref)
        before = _identity(path.stat())
        raw = path.read_bytes()
        _require(before == _identity(path.stat()) and len(raw) == ref["size_bytes"]
                 and sha256(raw).hexdigest() == ref["sha256"], "Authority content bytes differ")
        self._authority_files.append((path, before, ref))
        return _json_object(raw)

    def _check_database(self, *, full_hash: bool) -> None:
        _safe_absolute(self._database)
        _no_sidecars(self._database)
        current = os.fstat(self._descriptor)
        _require(stat.S_ISREG(current.st_mode) and _identity(current) == self._database_identity
                 == _identity(os.stat(self._database, follow_symlinks=False))
                 and current.st_size == self._database_ref["size_bytes"], "Source SQLite identity/size changed")
        if full_hash:
            _require(_fd_sha256(self._descriptor) == self._database_ref["sha256"], "Source SQLite SHA changed")
            _no_sidecars(self._database)
            _require(_identity(os.fstat(self._descriptor)) == self._database_identity
                     == _identity(os.stat(self._database, follow_symlinks=False)), "Source SQLite identity changed during hashing")

    def _check_authorities(self) -> None:
        for path, identity, ref in self._authority_files:
            _safe_absolute(path)
            _require(_identity(path.stat()) == identity, "Authority file identity changed")
            raw = path.read_bytes()
            _require(len(raw) == ref["size_bytes"] and sha256(raw).hexdigest() == ref["sha256"]
                     and _identity(path.stat()) == identity, "Authority file bytes changed")


def _load_document_authorities(source: IncomeTaxOriginalCensusSourceV1, index: dict[str, Any]) -> list[dict[str, Any]]:
    documents, all_ids = [], []
    summary = index["summary"]
    _require(all(type(summary[key]) is int and summary[key] > 0 for key in ("document_count", "page_count"))
             and summary["document_count"] == len(index["documents"])
             and all(type(value) is int and value >= 0 for value in summary["page_status_counts"].values())
             and all(type(item["count"]) is int and item["count"] > 0 for item in summary["provider_counts"]),
             "Corpus summary counts must be plain integers")
    for corpus_ordinal, item in enumerate(index["documents"], 1):
        _require(type(item["source_ordinal"]) is int and item["source_ordinal"] == corpus_ordinal,
                 "Corpus source ordinal must be a plain ordered integer")
        logical = item["relative_path"]
        years = [int(part) for part in PurePosixPath(logical).parts if re.fullmatch(r"[0-9]{4}", part)]
        _require(len(years) == 1 and 2025 <= years[0] <= datetime.now(UTC).year, "2024/non-current source prohibited")
        manifest_path = _content_path(source._artifact_root, item["document_manifest_ref"])
        manifest = source._read_authority(source._artifact_root, item["document_manifest_ref"])
        selection = validate_current_document_manifest_selection_v1(
            source._read_authority(source._artifact_root, item["selection_ref"])
        )
        material = {key: value for key, value in manifest.items() if key != "document_manifest_id"}
        document_material = {"source_logical_name": logical, "source_sha256": item["source_sha256"],
                             "source_size_bytes": item["source_size_bytes"]}
        expected_document = {**document_material, "document_id": "gfpstorev1:document:" + canonical_json_sha256_v1(document_material)}
        pages = manifest.get("pages")
        _require(type(pages) is list and bool(pages), "Manifest page axis empty")
        _require(manifest.get("document_manifest_id") == item["document_manifest_id"]
                 == "gfdmv1:manifest:" + canonical_json_sha256_v1(material)
                 and same_typed_json_v1(manifest.get("document"), expected_document)
                 and type(manifest.get("page_count")) is int
                 and manifest["page_count"] == item["page_count"] == len(pages)
                 and canonical_json_sha256_v1(pages) == item["page_json_frontier_sha256"], "Immutable source/manifest frontier differs")
        _require(selection["selection_id"] == item["selection_id"]
                 and selection["document_plan_id"] == item["document_plan_id"]
                 and selection["document_manifest_id"] == manifest["document_manifest_id"]
                 and selection["source_sha256"] == item["source_sha256"]
                 and all(selection["document_manifest_ref"][key] == item["document_manifest_ref"][key]
                         for key in ("sha256", "size_bytes"))
                 and _content_path(manifest_path.parent.parent, selection["document_manifest_ref"]) == manifest_path,
                 "Selected manifest binding differs")
        physical, ids = [], []
        for page in pages:
            _require(type(page) is dict and type(page.get("physical_page")) is int
                     and type(page.get("page_json_version_id")) is str
                     and re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", page["page_json_version_id"]) is not None, "Invalid selected page identity")
            physical.append(page["physical_page"])
            ids.append(page["page_json_version_id"])
        _require(physical == list(range(1, len(pages) + 1)) and len(set(ids)) == len(ids), "Selected page frontier noncontiguous/duplicate")
        documents.append({"index_document": item, "manifest": manifest, "selection": selection, "ids": ids})
        all_ids.extend(ids)
    _require(len(all_ids) == len(set(all_ids)) == index["summary"]["page_count"], "Selected corpus denominator differs")
    return documents


@contextmanager
def open_income_tax_original_census_source_v1(
    database: Path, *, database_ref: dict[str, Any], artifact_root: Path,
    corpus_index_ref: dict[str, Any],
) -> Iterator[IncomeTaxOriginalCensusSourceV1]:
    """Authenticate actual immutable source/authority bytes before and finally.

    ``corpus_index_ref.path`` is relative to ``artifact_root``. The explicit
    database path may be relocated; its byte pins must equal index.database_ref.
    No PDF is opened here; PDF byte/page/visual gates remain the runner's job.
    Never persist or export provisional results before this context succeeds.
    """
    source = object.__new__(IncomeTaxOriginalCensusSourceV1)
    source._closed, source._invalidated = False, False
    source._owner = threading.get_ident()
    source._task = _current_task()
    source._database = _safe_absolute(database)
    source._database_ref = _reference(database_ref)
    source._artifact_root = _safe_absolute(artifact_root)
    source._index_ref = _reference(corpus_index_ref)
    source._authority_files = []
    source._loaded_ordinals = set()
    source._run_ordinals = set()
    _no_sidecars(source._database)
    source._descriptor = os.open(source._database, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        source._database_identity = _identity(os.fstat(source._descriptor))
        source._check_database(full_hash=True)
        body_error = None
        try:
            index = validate_current_corpus_manifest_index_v1(source._read_authority(source._artifact_root, source._index_ref))
            _require(all(index["database_ref"][key] == source._database_ref[key] for key in ("sha256", "size_bytes")), "Database pins differ from corpus index")
            source._index_bytes = canonical_json_bytes_v1(index)
            source._index_id = index["corpus_manifest_index_id"]
            source._prompt_encoding_scope_bytes = canonical_json_bytes_v1(
                _load_registered_prompt_encoding_scope(source)
            )
            source._document_bytes = tuple(canonical_json_bytes_v1(document)
                                           for document in _load_document_authorities(source, index))
            source._check_authorities()
            yield source
        except BaseException as error:
            body_error = error
            raise
        finally:
            try:
                source._check_database(full_hash=True)
                source._check_authorities()
                _require(threading.get_ident() == source._owner and _current_task() is source._task,
                         "Source context exited outside owning thread/task")
                if body_error is None:
                    _require(not source._invalidated, "Source context invalidated during loading")
            finally:
                source._closed = True
    finally:
        source._closed = True
        os.close(source._descriptor)


def original_income_tax_records_from_loaded_v1(document, loaded, *, run_document_ordinal: int):
    """Pure record construction only; supplied loaded JSON is NOT authentication.

    The authenticated boundary below is the sole production caller. This helper
    also permits a runner compatibility shim without importing the runner here.
    """
    _require(type(run_document_ordinal) is int and run_document_ordinal > 0, "Invalid run document ordinal")
    source = document["manifest"]["document"]
    material = {key: source[key] for key in ("source_logical_name", "source_sha256", "source_size_bytes")}
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(material)
    _require(source.get("document_id", document_id) == document_id, "Source document ID differs")
    axis = {"document_id": document_id, "document_ordinal": run_document_ordinal,
            "source_logical_name": source["source_logical_name"], "source_sha256": source["source_sha256"]}
    pages, ids = document["manifest"]["pages"], document["ids"]
    _require(type(loaded) is list and len(loaded) == len(pages) == len(ids), "Selected JSON rows omitted/extra")
    records = []
    for ordinal, (item, page) in enumerate(zip(loaded, pages, strict=True), 1):
        _require(item["page_json_version_id"] == page["page_json_version_id"] == ids[ordinal - 1]
                 and type(item["physical_page"]) is int and item["physical_page"] == page["physical_page"]
                 and item["source_logical_name"] == source["source_logical_name"]
                 and item["source_sha256"] == source["source_sha256"], "Selected JSON/source/physical page differs")
        records.append({**axis, "page_json_version_id": item["page_json_version_id"],
                        "physical_page": item["physical_page"], "selected_page_ordinal": ordinal,
                        "page_json": canonical_clone_v1(item["page_json"])})
    return canonical_clone_v1(axis), records


def _enumerate_original_cells(records: list[dict[str, Any]], loaded: list[dict[str, Any]], binding: dict[str, Any]) -> dict[str, Any]:
    """Private exact-position enumerator; never parses financial values."""
    pages, sections, tables, rows, cells = [], [], [], [], []
    nonmoney = raw_positions = unknown_positions = 0
    for record, item in zip(records, loaded, strict=True):
        page = record["page_json"]
        locator = {key: record[key] for key in _LOCATOR_KEYS}
        replay = item["source_json_replay_receipt"]
        raw = canonical_json_bytes_v1(page) + b"\n"
        _require(sha256(raw).hexdigest() == replay["canonical_json_sha256"]
                 and len(raw) == replay["canonical_json_size_bytes"]
                 and replay["replay_receipt_id"] == "f39sourcejsonv1:" + canonical_json_sha256_v1({key: value for key, value in replay.items() if key != "replay_receipt_id"})
                 and replay["mapping_input"] == "ORIGINAL_STORED_JSON_UNMODIFIED"
                 and replay["all_original_cells_and_ordinals_retained"] is True
                 and same_typed_json_v1(replay["provenance"], {key: value for key, value in item.items() if key not in {"page_json", "source_json_replay_receipt"}}),
                 "Official original source receipt differs")
        page_hash = canonical_json_sha256_v1(page)
        page_id = "f39rawcellv1:page:" + canonical_json_sha256_v1({"locator": locator, "original_object_canonical_sha256": page_hash})
        page_row = {"page_census_id": page_id, "locator": locator,
                    "original_object_canonical_sha256": page_hash,
                    "stored_blob_sha256": replay["canonical_json_sha256"],
                    "stored_blob_size_bytes": replay["canonical_json_size_bytes"],
                    "validated_object_canonical_sha256": replay["validated_json_sha256"],
                    "official_source_replay_receipt": canonical_clone_v1(replay),
                    "status_exact": page["status"], "completion_exact": canonical_clone_v1(page["completion"]),
                    "section_count": len(page["sections"]), "raw_money_cell_count": 0}
        pages.append(page_row)
        for section_ordinal, section in enumerate(page["sections"], 1):
            section_id = "s" + str(section_ordinal)
            sections.append({"page_census_id": page_id, "section_id": section_id,
                             "source_section_sha256": canonical_json_sha256_v1(section),
                             "content_kind_exact": section["content_kind"], "statement_type_exact": section["statement_type"],
                             "title_exact": section["title_exact"], "narratives_exact": canonical_clone_v1(section["narratives_exact"]),
                             "table_count": len(section["tables"])})
            for table_ordinal, table in enumerate(section["tables"], 1):
                table_locator = {**locator, "section_id": section_id, "table_id": "t" + str(table_ordinal)}
                table_hash = canonical_json_sha256_v1(table)
                table_id = "f39rawcellv1:table:" + canonical_json_sha256_v1({"locator": table_locator, "page_sha256": page_hash, "table_sha256": table_hash})
                money = []
                unknown = []
                for ordinal, column in enumerate(table["columns"], 1):
                    _require(column["value_kind"] in _VALUE_KINDS, "Unknown raw value-kind token")
                    if column["value_kind"] == "MONEY":
                        money.append(ordinal)
                    elif column["value_kind"] == "UNKNOWN":
                        unknown.append(ordinal)
                tables.append({"table_census_id": table_id, "page_census_id": page_id, "locator": table_locator,
                               "original_table_canonical_sha256": table_hash,
                               "title_exact": table["title_exact"], "unit_exact": table["unit_exact"],
                               "continuation_exact": table["continuation"], "columns_exact": canonical_clone_v1(table["columns"]),
                               "raw_money_column_ordinals": money, "unassessed_unknown_column_ordinals": unknown,
                               "row_count": len(table["rows"])})
                for row_ordinal, row in enumerate(table["rows"], 1):
                    values = row["values_exact"]
                    _require(type(values) is list and len(values) == len(table["columns"]), "Raw row width differs; no padding permitted")
                    _require(all(value is None or type(value) is str for value in values), "Original raw cells must be strings/null")
                    row_id = "f39rawcellv1:row:" + canonical_json_sha256_v1({"table_census_id": table_id, "original_row_ordinal": row_ordinal})
                    rows.append({"row_census_id": row_id, "table_census_id": table_id, "original_row_ordinal": row_ordinal,
                                 "row_exact": canonical_clone_v1(row)})
                    raw_positions += len(values)
                    nonmoney += len(values) - len(money)
                    unknown_positions += len(unknown)
                    for ordinal in money:
                        value = values[ordinal - 1]
                        identity = {"row_census_id": row_id, "original_raw_column_ordinal": ordinal}
                        cells.append({"cell_census_id": "f39rawcellv1:cell:" + canonical_json_sha256_v1(identity),
                                      **identity, "table_census_id": table_id, "raw_value_exact": value,
                                      "raw_lexical_state": "RAW_NULL" if value is None else "RAW_EMPTY_STRING" if value == "" else "RAW_NONEMPTY_STRING"})
                        page_row["raw_money_cell_count"] += 1
    material = {"format_version": FORMAT_VERSION, "source_binding": binding,
                "relevance": RELEVANCE, "family_acceptance_claimed": False,
                "dispositions_classified": False, "source_values_modified": False,
                "pdf_bytes_or_visuals_verified": False,
                "pages": pages, "sections": sections, "tables": tables, "rows": rows, "raw_money_cells": cells,
                "counts": {"pages": len(pages), "sections": len(sections), "tables": len(tables), "rows": len(rows),
                           "raw_money_cells": len(cells), "all_raw_cell_positions": raw_positions,
                           "unassessed_nonmoney_raw_cell_positions": nonmoney,
                           "unassessed_unknown_raw_cell_positions": unknown_positions,
                           "zero_money_pages": sum(page["raw_money_cell_count"] == 0 for page in pages)},
                "input_records_sha256": canonical_json_sha256_v1(records)}
    return {**material, "census_id": "f39rawcellv1:census:" + canonical_json_sha256_v1(material)}


def load_income_tax_original_document_census_v1(
    source: IncomeTaxOriginalCensusSourceV1, *, corpus_document_ordinal: int,
    run_document_ordinal: int,
) -> dict[str, Any]:
    """One official original load, records and full raw-MONEY census per document.

    This function takes no caller-provided pages, loaded rows or approval flag.
    Cold replay opens a new source context and calls this function independently.
    """
    _require(type(source) is IncomeTaxOriginalCensusSourceV1, "An active original source context is required")
    source._active()
    try:
        _require(type(corpus_document_ordinal) is int and 1 <= corpus_document_ordinal <= len(source._document_bytes), "Invalid corpus document ordinal")
        _require(type(run_document_ordinal) is int and run_document_ordinal > 0, "Invalid run document ordinal")
        _require(corpus_document_ordinal not in source._loaded_ordinals, "Document already loaded in this source pass")
        _require(run_document_ordinal not in source._run_ordinals, "Run document ordinal already identifies another document")
        source._check_database(full_hash=False)
        document = json.loads(source._document_bytes[corpus_document_ordinal - 1])
        loaded = load_income_tax_source_page_json_versions_v1(source._database, page_json_version_ids=document["ids"])
        axis, records = original_income_tax_records_from_loaded_v1(document, loaded, run_document_ordinal=run_document_ordinal)
        _require(document["selection"]["page_image_frontier_sha256"] == canonical_json_sha256_v1([
            {"physical_page": row["physical_page"], "image_sha256": row["image_sha256"]} for row in loaded
        ]), "Selected image/prompt frontier differs from original source")
        encoding_witness = _registered_prompt_encoding_witness(
            source, document, loaded, variant_frontier_sha256=canonical_json_sha256_v1([
                {"physical_page": row["physical_page"], "prompt_variant": row["prompt_variant"]} for row in loaded
            ]),
        )
        source._check_database(full_hash=False)
        page_axis = [{key: record[key] for key in _LOCATOR_KEYS} for record in records]
        binding = {"corpus_index_ref": source._index_ref,
                   "corpus_manifest_index_id": source._index_id,
                   "database_ref": source._database_ref,
                   "corpus_document_ordinal": corpus_document_ordinal, "run_document_ordinal": run_document_ordinal,
                   "index_document": document["index_document"], "document_source_axis": document["manifest"]["document"],
                   "document_manifest_id": document["manifest"]["document_manifest_id"],
                   "selection_id": document["selection"]["selection_id"],
                   "ordered_selected_page_axis": page_axis,
                   "ordered_selected_page_axis_sha256": canonical_json_sha256_v1(page_axis),
                   "official_source_replay_receipt_axis_sha256": canonical_json_sha256_v1([row["source_json_replay_receipt"] for row in loaded]),
                   "source_scope": "SELECTED_ORIGINAL_DOCUMENT_NOT_PHYSICAL_PDF_COMPLETENESS",
                   "operation_scope": "PROVISIONAL_UNTIL_AUTHENTICATED_SOURCE_CONTEXT_EXIT"}
        if encoding_witness is not None:
            binding["registered_prompt_frontier_encoding_witness"] = encoding_witness
        census = _enumerate_original_cells(records, loaded, binding)
        source._loaded_ordinals.add(corpus_document_ordinal)
        source._run_ordinals.add(run_document_ordinal)
        # Separate clones ensure downstream private repair cannot mutate census,
        # loaded receipts, or original records through a shared Python alias.
        return {"axis_document": canonical_clone_v1(axis), "records": canonical_clone_v1(records),
                "loaded": canonical_clone_v1(loaded), "census": canonical_clone_v1(census),
                "corpus_document_ordinal": corpus_document_ordinal, "run_document_ordinal": run_document_ordinal}
    except BaseException:
        source._invalidated = True
        raise
