"""Neutral, streaming ORIGINAL denominator for F36 experiments, not acceptance.

Only selected source bytes and positional structure are inventoried. No family
retrieval, classifier, role, number, unit, period, equation or PDF is evaluated.
The existing original-census context owns live source/authority authentication;
the existing store API owns selectable extraction/repair provenance. Financial
page validation is deliberately not called: unsupported raw shapes stay visible.
Partial JSONL is retained on failure and has no complete inventory authority.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage import gemini_income_tax_raw_money_census_v1 as original_source
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    _source_identities,
    selected_page_json_provenance_receipts_v1,
)

FORMAT = "F36_NEUTRAL_SELECTED_ORIGINAL_INVENTORY_V1"
MAX_PAGE_BYTES = 4 * 1024**2
MAX_STREAM_BYTES = 1024**3
UNASSESSED = "UNASSESSED_NO_FAMILY_RELEVANCE_OR_FINANCIAL_PERMISSION"
_SQL = """SELECT v.canonical_json_bytes,v.canonical_json_sha256,v.page_json_version_id,
 v.page_id,v.extraction_run_id,v.page_status,p.physical_page,p.image_sha256,
 p.image_size_bytes,p.pixel_width,p.pixel_height,p.render_dpi,p.media_type,
 p.document_id,r.prompt_variant,r.prompt_sha256,d.source_logical_name,d.source_sha256,d.source_size_bytes
 FROM page_json_version v JOIN page p ON p.page_id=v.page_id
 JOIN extraction_run r ON r.extraction_run_id=v.extraction_run_id AND r.page_id=p.page_id
 JOIN document d ON d.document_id=p.document_id WHERE v.page_json_version_id=?"""


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _pairs(items):
    value = {}
    for key, item in items:
        _need(key not in value, "Duplicate ORIGINAL JSON key")
        value[key] = item
    return value


def _fields(value, keys):
    return {key: {"present": key in value, "value": value.get(key)} for key in keys}


def _node(kind, pointer, value, **extra):
    return {"record_type": kind, "pointer": pointer, "original_json_type": type(value).__name__,
            "original_object_one_lf_sha256": canonical_json_sha256_v1(value), **extra}


def _nodes(page):
    """Enumerate every positional list item; malformed axes are explicit unresolved records."""
    def axis(owner, field, pointer):
        value = owner.get(field) if type(owner) is dict else None
        if type(value) is not list:
            yield _node("unsupported_shape", pointer, value, field_present=type(owner) is dict and field in owner)
        else:
            for number, item in enumerate(value):
                yield number, item

    for section_item in axis(page, "sections", "/sections"):
        if type(section_item) is dict:
            yield section_item
            continue
        s, section = section_item
        sp = f"/sections/{s}"
        yield _node("section", sp, section, section_ordinal=s + 1,
                    fields=_fields(section, ("content_kind", "statement_type", "title_exact")) if type(section) is dict else {})
        if type(section) is not dict:
            yield _node("unsupported_shape", sp, section)
            continue
        for table_item in axis(section, "tables", sp + "/tables"):
            if type(table_item) is dict:
                yield table_item
                continue
            t, table = table_item
            tp = sp + f"/tables/{t}"
            yield _node("table", tp, table, section_id=f"s{s + 1}", table_id=f"t{t + 1}",
                        fields=_fields(table, ("title_exact", "unit_exact", "continuation")) if type(table) is dict else {})
            if type(table) is not dict:
                yield _node("unsupported_shape", tp, table)
                continue
            columns = table.get("columns")
            for column_item in axis(table, "columns", tp + "/columns"):
                if type(column_item) is dict:
                    yield column_item
                    continue
                c, column = column_item
                yield _node("column", tp + f"/columns/{c}", column, column_ordinal=c + 1,
                            column_exact=column)
                if type(column) is not dict:
                    yield _node("unsupported_shape", tp + f"/columns/{c}", column)
            for row_item in axis(table, "rows", tp + "/rows"):
                if type(row_item) is dict:
                    yield row_item
                    continue
                r, row = row_item
                rp = tp + f"/rows/{r}"
                record = _node("row", rp, row, row_ordinal=r + 1,
                               fields=_fields(row, ("row_kind", "label_exact", "hierarchy_path_exact")) if type(row) is dict else {})
                values = row.get("values_exact") if type(row) is dict else None
                if type(values) is list:
                    record["value_axis"] = {"count": len(values), "item_types": [type(v).__name__ for v in values],
                        "null_column_ordinals": [c for c, v in enumerate(values, 1) if v is None],
                        "items_one_lf_sha256": [canonical_json_sha256_v1(v) for v in values]}
                yield record
                if type(row) is not dict or type(values) is not list:
                    yield _node("unsupported_shape", rp + "/values_exact", values,
                                field_present=type(row) is dict and "values_exact" in row)
                elif type(columns) is not list or len(values) != len(columns):
                    yield _node("unsupported_shape", rp + "/values_exact", values,
                                reason="ROW_WIDTH_DIFFERS_FROM_ORIGINAL_COLUMN_AXIS")


def _integrity(connection):
    _need(connection.execute("PRAGMA quick_check").fetchall() == [("ok",)], "Source quick_check failed")
    _need(connection.execute("PRAGMA foreign_key_check").fetchone() is None, "Source foreign_key_check failed")
    return {"quick_check": "ok", "foreign_key_check": "EMPTY"}


def _original_page(connection, document, selected, provenance):
    version = selected["page_json_version_id"]
    length = connection.execute("SELECT length(canonical_json_bytes) FROM page_json_version WHERE page_json_version_id=?", (version,)).fetchone()
    _need(length is not None and type(length[0]) is int and 0 < length[0] <= MAX_PAGE_BYTES,
          "Selected ORIGINAL BLOB absent/oversized")
    rows = connection.execute(_SQL, (version,)).fetchall()
    _need(len(rows) == 1 and type(rows[0][0]) is bytes, "ORIGINAL BLOB source join not unique")
    row = rows[0]
    blob = row[0]
    _need(sha256(blob).hexdigest() == row[1] and version == row[2] == "gfpstorev1:json:" + canonical_json_sha256_v1(
        {"canonical_json_sha256": row[1], "page_id": row[3], "extraction_run_id": row[4]}), "ORIGINAL BLOB/VID hash differs")
    source = {"source_logical_name": row[16], "source_sha256": row[17], "source_size_bytes": row[18]}
    image = dict(zip(("physical_page", "image_sha256", "image_size_bytes", "pixel_width", "pixel_height", "render_dpi", "media_type"), row[6:13], strict=True))
    doc_id, page_id = _source_identities(source, image)
    _need({**source, "document_id": doc_id} == document["manifest"]["document"] and page_id == row[3]
          and row[13] == doc_id and type(selected["physical_page"]) is int and row[6] == selected["physical_page"],
          "ORIGINAL document/page source identity differs")
    actual = dict(zip(("page_json_version_id", "source_logical_name", "source_sha256", "physical_page", "image_sha256", "render_dpi", "prompt_variant", "prompt_sha256"),
                      (version, row[16], row[17], row[6], row[7], row[11], row[14], row[15]), strict=True))
    _need(actual == {k: provenance[k] for k in actual}, "ORIGINAL selectable provenance differs")
    for key, value in (("page_id", row[3]), ("extraction_run_id", row[4]), ("canonical_json_sha256", row[1]), ("status", row[5]), ("prompt_sha256", row[15])):
        _need(key not in selected or type(selected[key]) is type(value) and selected[key] == value, "Manifest page field differs: " + key)
    if "image" in selected:
        _need(type(selected["image"]) is dict and type(selected["image"].get("size_bytes")) is int
              and selected["image"]["sha256"] == row[7] and selected["image"]["size_bytes"] == row[8], "Manifest image differs")
    page = json.loads(blob, object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite ORIGINAL JSON: " + value)))
    _need(type(page) is dict and canonical_json_bytes_v1(page) + b"\n" == blob and page.get("status") == row[5],
          "ORIGINAL stored-two-LF serialization/status differs")
    return page, {**actual, "page_id": row[3], "extraction_run_id": row[4], "page_status": row[5],
                  "stored_blob_two_lf_sha256": row[1], "stored_blob_size_bytes": len(blob), "image_size_bytes": row[8]}


def write_f36_original_completeness_inventory_v1(*, database: Path, database_ref: dict[str, Any],
        artifact_root: Path, corpus_index_ref: dict[str, Any], out: Path, batch_size: int = 32) -> dict[str, Any]:
    """Write one neutral inventory, with COMPLETE identity only after all final guards.

    Caller pins a reviewed corpus authority; this does not grant family relevance.
    A reviewed runtime caller must pin and restrict real FULL271/COMMON204 profiles;
    no CLI is implemented here. Tests may use tiny genuine stores.
    No generator/capability escapes. Provisional JSONL remains explicitly unsealed on FAIL.
    """
    _need(type(batch_size) is int and 1 <= batch_size <= 32, "Batch size must be plain int1..32")
    database_ref = original_source._reference(database_ref)
    corpus_index_ref = original_source._reference(corpus_index_ref)
    out = Path(out)
    original_source._safe_absolute(out.parent)
    _need(out.is_absolute() and ".." not in out.parts and not out.is_symlink(), "Explicit safe output path required")
    source_root = original_source._safe_absolute(artifact_root)
    _need(not out.is_relative_to(source_root) and not out.is_relative_to(Path(__file__).resolve().parents[3]),
          "Inventory output must be outside repository and source authority roots")
    _need(not os.path.lexists(out), "Fresh exclusive output directory required")
    out.mkdir(mode=0o700)
    report = {"format_version": FORMAT, "status": "FAIL", "errors": [], "source_context_successfully_exited": False,
              "sql_integrity": [], "counts": {}, "status_filter_applied": False,
              "complete_selected_page_frontier": False, "relevance": UNASSESSED,
              "financial_acceptance": False, "family_seal": False, "pdf_absence_proved": False,
              "role_unit_period_or_value_permission_granted": False, "provider_or_reextraction_performed": False,
              "hash_domains": {"stored_blob": "ACTUAL_STORED_TWO_LF_BYTES", "object_table_row_and_values": "CANONICAL_JSON_ONE_LF"}}
    counts, stream_hash, stream_bytes = Counter(), sha256(), 0
    stream_path = out / "selected-original-inventory.jsonl"
    page_axis_hash = sha256(b"[")
    try:
        with stream_path.open("x+b") as stream:
            def emit(record):
                nonlocal stream_bytes
                value = canonical_json_bytes_v1(record)
                _need(stream_bytes + len(value) <= MAX_STREAM_BYTES, "Inventory exceeds1GiB; no truncation/cap increase")
                _need(stream.write(value) == len(value), "Short inventory write")
                stream_hash.update(value)
                stream_bytes += len(value)
                counts[record["record_type"]] += 1

            with original_source.open_income_tax_original_census_source_v1(database, database_ref=database_ref,
                    artifact_root=artifact_root, corpus_index_ref=corpus_index_ref) as source:
                index, authorities = source.corpus_index, source.document_authorities
                report.update(corpus_manifest_index_id=index["corpus_manifest_index_id"], database_ref=database_ref,
                              corpus_index_ref=corpus_index_ref, expected_documents=len(authorities),
                              expected_pages=index["summary"]["page_count"])
                # SAME held source FD; no huge snapshot copy or normalized SQL row dependency.
                connection = sqlite3.connect(f"file:/proc/self/fd/{source._descriptor}?mode=ro&immutable=1", uri=True)
                try:
                    connection.execute("PRAGMA query_only=ON")
                    connection.execute("PRAGMA cache_size=-1024")
                    connection.execute("PRAGMA mmap_size=0")
                    report["sql_integrity"].append(_integrity(connection))
                    for document in authorities:
                        indexed, pages = document["index_document"], document["manifest"]["pages"]
                        emit({"record_type": "document", "index_document": indexed, "document": document["manifest"]["document"]})
                        frontier, statuses = [], Counter()
                        for first in range(0, len(pages), batch_size):
                            source._active()
                            source._check_database(full_hash=False)
                            selected_batch = pages[first:first + batch_size]
                            provenance = selected_page_json_provenance_receipts_v1(database,
                                page_json_version_ids=[p["page_json_version_id"] for p in selected_batch])
                            _need(len(provenance) == len(selected_batch), "Provenance batch incomplete")
                            for offset, (selected, proof) in enumerate(zip(selected_batch, provenance, strict=True), first + 1):
                                page, metadata = _original_page(connection, document, selected, proof)
                                axis = {"document_ordinal": indexed["source_ordinal"], "document_id": document["manifest"]["document"]["document_id"],
                                    "source_logical_name": indexed["relative_path"], "source_sha256": indexed["source_sha256"],
                                    "page_json_version_id": selected["page_json_version_id"], "physical_page": selected["physical_page"],
                                    "selected_page_ordinal": offset}
                                if counts["page"]:
                                    page_axis_hash.update(b",")
                                page_axis_hash.update(canonical_json_bytes_v1(axis)[:-1])
                                emit({**_node("page", "", page), "axis": axis, "source_proof": metadata})
                                for node in _nodes(page):
                                    if node["record_type"] == "row":
                                        counts["value_slots"] += node.get("value_axis", {}).get("count", 0)
                                    emit({"document_ordinal": indexed["source_ordinal"],
                                          "page_json_version_id": selected["page_json_version_id"], **node})
                                statuses[metadata["page_status"]] += 1
                                frontier.append({k: metadata[k] for k in ("physical_page", "image_sha256", "prompt_variant", "prompt_sha256")})
                                del page, metadata
                        _need(all(statuses[status] == count for status, count in indexed["page_status_counts"].items())
                              and sum(statuses.values()) == indexed["page_count"], "Original all-status document denominator differs")
                        _need(canonical_json_sha256_v1([{k: p[k] for k in ("physical_page", "image_sha256")} for p in frontier])
                              == document["selection"]["page_image_frontier_sha256"], "Original image frontier differs")
                        contract = document["manifest"].get("extraction_contract")
                        if contract is not None:
                            _need(type(contract) is dict and ("prompt_sha256" in contract) != ("page_prompt_sha256s" in contract),
                                  "Unsupported manifest prompt contract")
                            if "prompt_sha256" in contract:
                                _need(type(contract["prompt_sha256"]) is str and all(p["prompt_sha256"] == contract["prompt_sha256"] for p in frontier),
                                      "Manifest prompt body SHA differs")
                            else:
                                _need(same_typed_json_v1(contract["page_prompt_sha256s"],
                                    [{k: p[k] for k in ("physical_page", "prompt_sha256")} for p in frontier]), "Manifest per-page prompt bodies differ")
                            if "page_image_sha256s" in contract:
                                _need(same_typed_json_v1(contract["page_image_sha256s"],
                                    [{k: p[k] for k in ("physical_page", "image_sha256")} for p in frontier]), "Manifest per-page images differ")
                        witness = original_source._registered_prompt_encoding_witness(source, document, frontier,
                            variant_frontier_sha256=canonical_json_sha256_v1([{k: p[k] for k in ("physical_page", "prompt_variant")} for p in frontier]))
                        emit({"record_type": "document_frontier_verified", "document_ordinal": indexed["source_ordinal"],
                              "page_status_counts": dict(statuses), "registered_prompt_encoding_witness": witness})
                    _need(counts["page"] == index["summary"]["page_count"] and counts["document"] == len(index["documents"]),
                          "Selected ORIGINAL inventory denominator incomplete")
                finally:
                    try:
                        report["sql_integrity"].append(_integrity(connection))
                    finally:
                        connection.close()
                stream.flush()
                os.fsync(stream.fileno())
            report["source_context_successfully_exited"] = True
            output_identity = original_source._identity(os.fstat(stream.fileno()))
            _need(not stream_path.is_symlink() and output_identity == original_source._identity(
                os.stat(stream_path, follow_symlinks=False)), "Inventory output path identity differs")
            stream.seek(0)
            actual = sha256()
            while block := stream.read(1024**2):
                actual.update(block)
            _need(actual.hexdigest() == stream_hash.hexdigest() and stream.tell() == stream_bytes,
                  "Written inventory bytes differ from streaming hash")
            _need(output_identity == original_source._identity(os.fstat(stream.fileno()))
                  == original_source._identity(os.stat(stream_path, follow_symlinks=False)),
                  "Inventory output changed during final hashing")
        page_axis_hash.update(b"]\n")
        report.update(status="COMPLETE_NEUTRAL_INVENTORY_NOT_FAMILY_OR_PDF_PROOF", counts=dict(counts),
                      complete_selected_page_frontier=True,
                      ordered_selected_page_axis_one_lf_sha256=page_axis_hash.hexdigest(),
                      stream_ref={"sha256": stream_hash.hexdigest(), "size_bytes": stream_bytes})
        material = {k: v for k, v in report.items() if k not in {"errors", "sql_integrity"}}
        report["inventory_id"] = "f36originalinventoryv1:" + canonical_json_sha256_v1(material)
    except BaseException as error:
        report["errors"].append(type(error).__name__ + ": " + str(error))
        report["counts"] = dict(counts)
        report["partial_stream_bytes"] = stream_bytes
    report["stream_path"] = str(stream_path)
    with (out / "F36_NEUTRAL_SELECTED_ORIGINAL_INVENTORY_V1.json").open("xb") as stream:
        value = canonical_json_bytes_v1(report)
        _need(stream.write(value) == len(value), "Short inventory receipt write")
        stream.flush()
        os.fsync(stream.fileno())
    return report
