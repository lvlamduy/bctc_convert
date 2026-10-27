"""ASCII-only stdlib FILE AUTHOR, not the census tool or a test runner.

Writes explicitly invented UTF-8 fixtures under this owned additive packet.
No project import, real inventory, database, PDF, image or provider is opened.
Symbolic source/image identities are synthetic, not external attestations.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATUSES = ("FINANCIAL_NOTE_CONTENT", "MIXED_FINANCIAL_CONTENT", "NO_RELEVANT_FINANCIAL_CONTENT", "PRIMARY_FINANCIAL_STATEMENT")
INTEREST = "R\u1ee7i ro l\u00e3i su\u1ea5t"
LIQUIDITY = "R\u1ee7i ro thanh kho\u1ea3n"
NOTES = "Thuy\u1ebft minh"
UNIT = "Tri\u1ec7u \u0111\u1ed3ng"
WITHIN = "T\u1eeb 1 th\u00e1ng \u0111\u1ebfn 3 th\u00e1ng"
OVER = "Tr\u00ean 5 n\u0103m"
TOTAL = "T\u1ed5ng t\u00e0i s\u1ea3n"
OTHER = "Kh\u00e1c"
DOMESTIC = "Trong n\u01b0\u1edbc"
OTHER_TABLE = "B\u1ea3ng kh\u00e1c"


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)


def envelope(owner, key):
    return {"present": key in owner, "value": owner.get(key)}


def node(kind, pointer, value, **extra):
    return {"record_type": kind, "pointer": pointer, "original_json_type": type(value).__name__,
            "original_object_one_lf_sha256": sha(value), **extra}


def main():
    # Native Windows stdin cannot corrupt non-ASCII source: this author file is
    # required to be ASCII-only, and every Vietnamese string uses Unicode escapes.
    own = Path(__file__).read_bytes()
    own.decode("ascii")
    out = ROOT / "synthetic-fixtures"
    out.mkdir(exist_ok=False)
    records, axes, page_objects = [], [], []
    for ordinal in (1, 2):
        logical = f"issuer-path-only/2025/report-version-{ordinal}.pdf"
        source_material = {"source_logical_name": logical, "source_sha256": "a" * 64, "source_size_bytes": 100}
        source = {"document_id": "gfpstorev1:document:" + sha(source_material), **source_material}
        index = {"source_ordinal": ordinal, "relative_path": logical, "source_sha256": source["source_sha256"],
                 "source_size_bytes": source["source_size_bytes"], "page_count": 1,
                 "page_status_counts": {status: int(i == 0) for i, status in enumerate(STATUSES)}}
        columns = [{"header_path_exact": ["31/12/2025", WITHIN], "value_kind": "MONEY"},
                   {"header_path_exact": ["31/12/2024", OVER], "value_kind": "MONEY"}]
        tables = []
        for title in ((INTEREST, OTHER_TABLE) if ordinal == 1 else (LIQUIDITY,)):
            second_label = OTHER if ordinal == 1 else DOMESTIC
            rows = [{"row_kind": "DATA", "label_exact": TOTAL, "hierarchy_path_exact": [TOTAL], "values_exact": [None, "0"]},
                    {"row_kind": "DATA", "label_exact": second_label, "hierarchy_path_exact": [second_label], "values_exact": ["-", "1"]}]
            if ordinal == 2:
                del rows[1]["values_exact"]
            tables.append({"title_exact": title, "unit_exact": UNIT,
                           "continuation": "CONTINUATION" if ordinal == 2 else "NOT_CONTINUATION",
                           "columns": columns, "rows": rows})
        section = {"content_kind": "NOTES", "statement_type": None, "title_exact": NOTES, "tables": tables}
        page = {"status": STATUSES[0], "sections": [section]}
        stored = canonical(page) + b"\n"
        stored_sha = hashlib.sha256(stored).hexdigest()
        image = {"physical_page": 1, "image_sha256": "b" * 64, "image_size_bytes": 1,
                 "pixel_width": 1, "pixel_height": 1, "render_dpi": 144, "media_type": "image/png"}
        page_id = "gfpstorev1:page:" + sha({"document_id": source["document_id"], **image})
        run_id = "SYNTHETIC_RUN_" + str(ordinal)
        vid = "gfpstorev1:json:" + sha({"canonical_json_sha256": stored_sha, "page_id": page_id, "extraction_run_id": run_id})
        axis = {"document_ordinal": ordinal, "document_id": source["document_id"],
                "source_logical_name": logical, "source_sha256": source["source_sha256"],
                "page_json_version_id": vid, "physical_page": 1, "selected_page_ordinal": 1}
        proof = {"page_json_version_id": vid, "source_logical_name": logical, "source_sha256": source["source_sha256"],
                 "physical_page": 1, "image_sha256": image["image_sha256"], "image_size_bytes": image["image_size_bytes"],
                 "render_dpi": image["render_dpi"], "prompt_variant": "SYNTHETIC", "prompt_sha256": "c" * 64,
                 "page_id": page_id, "extraction_run_id": run_id, "canonical_json_sha256": stored_sha,
                 "page_status": STATUSES[0], "stored_blob_two_lf_sha256": stored_sha, "stored_blob_size_bytes": len(stored)}
        axes.append(axis)
        page_objects.append({"classification": "ENTIRELY_SYNTHETIC_NOT_A_PDF_IMAGE_OR_SOURCE_ATTESTATION",
                             "source_document": source, "symbolic_image_metadata": image, "page_id": page_id,
                             "extraction_run_id": run_id, "page_json_version_id": vid, "page_object": page,
                             "object_one_lf_sha256": sha(page), "stored_blob_two_lf_sha256": stored_sha,
                             "stored_blob_size_bytes": len(stored)})
        records.append({"record_type": "document", "index_document": index, "document": source})
        records.append({**node("page", "", page), "axis": axis, "source_proof": proof})
        context = {"document_ordinal": ordinal, "page_json_version_id": vid}
        records.append({**context, **node("section", "/sections/0", section, section_ordinal=1,
                                         fields={key: envelope(section, key) for key in ("content_kind", "statement_type", "title_exact")})})
        for t, table in enumerate(tables):
            pointer = f"/sections/0/tables/{t}"
            records.append({**context, **node("table", pointer, table, section_id="s1", table_id=f"t{t + 1}",
                                             fields={key: envelope(table, key) for key in ("title_exact", "unit_exact", "continuation")})})
            for c, column in enumerate(columns):
                records.append({**context, **node("column", pointer + f"/columns/{c}", column, column_ordinal=c + 1, column_exact=column)})
            for r, row in enumerate(table["rows"]):
                rp = pointer + f"/rows/{r}"
                record = {**context, **node("row", rp, row, row_ordinal=r + 1,
                                           fields={key: envelope(row, key) for key in ("row_kind", "label_exact", "hierarchy_path_exact")})}
                if "values_exact" in row:
                    values = row["values_exact"]
                    record["value_axis"] = {"count": len(values), "item_types": [type(v).__name__ for v in values],
                                            "null_column_ordinals": [c for c, v in enumerate(values, 1) if v is None],
                                            "items_one_lf_sha256": [sha(v) for v in values]}
                records.append(record)
                if "values_exact" not in row:
                    records.append({**context, **node("unsupported_shape", rp + "/values_exact", None, field_present=False)})
        records.append({"record_type": "document_frontier_verified", "document_ordinal": ordinal,
                        "page_status_counts": {STATUSES[0]: 1}, "registered_prompt_encoding_witness": None})
    counts = Counter()
    for record in records:
        counts[record["record_type"]] += 1
        if record["record_type"] == "row":
            counts["value_slots"] += record.get("value_axis", {}).get("count", 0)
    raw = b"".join(canonical(record) for record in records)
    contract = {"classification": "ENTIRELY_SYNTHETIC_NO_REAL_REPORT_VALUES_OR_SOURCE_REVIEW", "counts": dict(counts),
                "ordered_selected_page_axis_one_lf_sha256": sha(axes), "stream_sha256": hashlib.sha256(raw).hexdigest(),
                "stream_size_bytes": len(raw), "source_sha_shared_across_documents": True,
                "different_selected_VIDs_preserved": True, "expected_table_count": 3, "expected_row_count": 6,
                "expected_value_slot_count": 10, "expected_unsupported_shape_count": 1,
                "status_axis": "INDEX_EXACT_FOUR_CATEGORIES_INCLUDING_ZERO__FRONTIER_SPARSE_OBSERVED_COUNTER",
                "cryptographic_original_source_attestation": False,
                "encoding": "UTF8_BYTES_FROM_ASCII_ONLY_AUTHOR_UNICODE_ESCAPES",
                "expected_unicode_literals": [INTEREST, LIQUIDITY, NOTES, UNIT, WITHIN, OVER, TOTAL, OTHER, DOMESTIC],
                "page_objects_fixture_file": "SYNTHETIC_PAGE_OBJECTS_V3.json"}
    write(out / "selected-original-inventory.SYNTHETIC.jsonl", raw)
    write(out / "SYNTHETIC_FIXTURE_CONTRACT_V1.json", canonical(contract))
    write(out / "SYNTHETIC_PAGE_OBJECTS_V3.json", canonical({"classification": "SYNTHETIC_HASH_RECONSTRUCTION_ONLY_NOT_SOURCE_ATTESTATION", "pages": page_objects}))
    print(json.dumps({"status": "SYNTHETIC_FILE_AUTHORING_COMPLETE_NOT_TEST_EXECUTION", "counts": dict(counts),
                      "fixture_sha256": contract["stream_sha256"], "fixture_size_bytes": len(raw)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
