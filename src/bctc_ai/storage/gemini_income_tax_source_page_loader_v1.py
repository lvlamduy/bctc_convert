"""Family-local replay of immutable page JSON without changing source ordinals.

The current mechanical validator can remove a redundant TEXT label column from
previously stored canonical JSON. Admit ONLY that lossless transformation as a
validation witness, and return the original JSON, never the transformed copy.
The shared loader/evaluator and the source database remain unchanged.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_financial_page_json_v1 import validate_financial_page_json_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    selected_page_json_provenance_receipts_v1,
)


class GeminiIncomeTaxSourcePageReplayV1Error(ValueError):
    """A selected original page cannot be authenticated and losslessly replayed."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise GeminiIncomeTaxSourcePageReplayV1Error(message)


def _duplicate_free_object(items):
    result = {}
    for key, value in items:
        _require(key not in result, "Original page JSON contains duplicate keys")
        result[key] = value
    return result


def prove_lossless_text_label_validation_v1(
    original: dict[str, Any], validated: dict[str, Any]
) -> list[dict[str, Any]]:
    """Prove the ONLY difference is unique per-table duplicate TEXT label removal.

    No trimming, padding, value/sign change, hierarchy/header repair, reordered
    row, or null-to-zero equivalence is admitted. The current validator must
    independently produce precisely this projection. All source cells remain
    present in the original object returned to the evaluator.
    """
    _require(type(original) is dict and type(validated) is dict, "Page objects required")
    if same_typed_json_v1(original, validated):
        return []
    sections = original.get("sections")
    target_sections = validated.get("sections")
    _require(
        type(sections) is list and type(target_sections) is list
        and len(sections) == len(target_sections),
        "Page section axis changed during validation",
    )
    projected = deepcopy(original)
    proofs = []
    for section_index, (section, target_section) in enumerate(
        zip(sections, target_sections, strict=True)
    ):
        tables, target_tables = section.get("tables"), target_section.get("tables")
        _require(
            type(tables) is list and type(target_tables) is list
            and len(tables) == len(target_tables),
            "Page table axis changed during validation",
        )
        for table_index, (table, target_table) in enumerate(zip(tables, target_tables, strict=True)):
            if same_typed_json_v1(table, target_table):
                continue
            columns, rows = table.get("columns"), table.get("rows")
            _require(
                type(columns) is list and len(columns) > 1 and type(rows) is list and rows,
                "Changed table has no complete original column/row axis",
            )
            candidates = []
            for column_index, column in enumerate(columns):
                if column.get("value_kind") != "TEXT":
                    continue
                clone = deepcopy(table)
                clone["columns"].pop(column_index)
                valid, observed_label = True, False
                for row, clone_row in zip(rows, clone["rows"], strict=True):
                    values = row.get("values_exact")
                    if type(values) is not list or len(values) != len(columns):
                        valid = False
                        break
                    cell, label = values[column_index], row.get("label_exact")
                    duplicate = type(label) is str and bool(label) and same_typed_json_v1(cell, label)
                    group_blank = cell is None and row.get("row_kind") == "GROUP"
                    if not (duplicate or group_blank):
                        valid = False
                        break
                    observed_label |= duplicate
                    clone_row["values_exact"].pop(column_index)
                if valid and observed_label and same_typed_json_v1(clone, target_table):
                    candidates.append(column_index)
            _require(len(candidates) == 1, "Validation changed more than one unique redundant TEXT label column")
            column_index = candidates[0]
            clone = projected["sections"][section_index]["tables"][table_index]
            clone["columns"].pop(column_index)
            for row in clone["rows"]:
                row["values_exact"].pop(column_index)
            proofs.append({
                "section_ordinal": section_index + 1,
                "table_ordinal": table_index + 1,
                "redundant_text_column_ordinal": column_index + 1,
                "original_column": deepcopy(columns[column_index]),
                "row_count": len(rows),
                "original_table_sha256": canonical_json_sha256_v1(table),
                "validated_table_sha256": canonical_json_sha256_v1(target_table),
                "all_other_cells_labels_hierarchy_and_metadata_exact": True,
            })
    _require(
        proofs and same_typed_json_v1(projected, validated),
        "Validation changed page/section metadata or unrelated source evidence",
    )
    return proofs


def load_income_tax_source_page_json_versions_v1(
    path: Path, *, page_json_version_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Batched read-only load with original bytes, CAS and full provenance replay."""
    provenance = selected_page_json_provenance_receipts_v1(
        path, page_json_version_ids=page_json_version_ids
    )
    ids = list(page_json_version_ids)
    _require(
        [item["page_json_version_id"] for item in provenance] == ids,
        "Selected provenance order differs",
    )
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            "CREATE TEMP TABLE f39_selected_source_json("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany("INSERT INTO f39_selected_source_json VALUES (?,?)", enumerate(ids, 1))
        rows = connection.execute(
            "SELECT s.selection_ordinal, s.page_json_version_id, v.page_id, v.extraction_run_id, "
            "v.page_status, v.canonical_json_sha256, v.canonical_json_bytes "
            "FROM f39_selected_source_json AS s JOIN page_json_version AS v USING(page_json_version_id) "
            "ORDER BY s.selection_ordinal"
        ).fetchall()
    _require(len(rows) == len(ids), "Selected original page is absent")
    result = []
    for ordinal, (source, row) in enumerate(zip(provenance, rows, strict=True), 1):
        _require(
            row["selection_ordinal"] == ordinal and row["page_json_version_id"] == ids[ordinal - 1],
            "Selected original page order differs",
        )
        _require(type(row["canonical_json_bytes"]) is bytes, "Original canonical JSON must be a BLOB")
        raw = row["canonical_json_bytes"]
        _require(sha256(raw).hexdigest() == row["canonical_json_sha256"], "Original canonical JSON SHA mismatch")
        expected_id = "gfpstorev1:json:" + canonical_json_sha256_v1({
            "canonical_json_sha256": row["canonical_json_sha256"],
            "extraction_run_id": row["extraction_run_id"], "page_id": row["page_id"],
        })
        _require(expected_id == row["page_json_version_id"], "Original JSON content ID does not replay")
        try:
            original = json.loads(raw, object_pairs_hook=_duplicate_free_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GeminiIncomeTaxSourcePageReplayV1Error("Original canonical JSON is invalid") from exc
        _require(type(original) is dict, "Original page must be an object")
        # Preserve the existing store's exact two-LF canonical byte convention.
        _require(canonical_json_bytes_v1(original) + b"\n" == raw, "Original stored serialization is noncanonical")
        _require(original.get("status") == row["page_status"], "Original stored page status differs")
        validated = validate_financial_page_json_v1(original)
        changes = prove_lossless_text_label_validation_v1(original, validated)
        # Validator purity is required; never return a mutated source object.
        _require(canonical_json_bytes_v1(original) + b"\n" == raw, "Validator mutated original source JSON")
        material = {
            "schema": "bctc-ai-f39-original-source-json-replay-v1",
            "provenance": source,
            "canonical_json_sha256": row["canonical_json_sha256"],
            "canonical_json_size_bytes": len(raw),
            "validated_json_sha256": canonical_json_sha256_v1(validated),
            "classification": "LOSSLESS_REDUNDANT_TEXT_LABEL_COLUMN_NORMALIZATION" if changes else "EXACT_REPLAY",
            "changed_tables": changes,
            "mapping_input": "ORIGINAL_STORED_JSON_UNMODIFIED",
            "all_original_cells_and_ordinals_retained": True,
        }
        receipt = {**material, "replay_receipt_id": "f39sourcejsonv1:" + canonical_json_sha256_v1(material)}
        result.append({**source, "page_json": original, "source_json_replay_receipt": receipt})
    return result
