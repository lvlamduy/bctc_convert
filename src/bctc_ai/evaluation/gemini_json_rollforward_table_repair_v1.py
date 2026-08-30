"""Bounded whole-table Gemini repair for typed roll-forward cells.

The primitive is deliberately provider-free.  It turns an authenticated,
declarative unresolved frontier into immutable sibling repair jobs, validates
one complete table transcription, and emits a region-repair receipt that can
be stored by the existing page/family stores.  It never calls a model, mutates
the base page, back-solves an OCR cell, or selects an OFFICIAL family run.
Every mutation boundary also requires an externally pinned repair-spec
authority.  Its self-hash detects drift but cannot authenticate the external
config/ref/SHA; that verification remains an explicit caller responsibility.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    FORMAT_VERSION as PAGE_FORMAT_VERSION,
)
from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    SEARCH_NORMALIZATION_VERSION,
    validate_financial_page_json_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_V1"
UNRESOLVED_FRONTIER_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_UNRESOLVED_FRONTIER_V1"
QUEUE_FORMAT_VERSION = "GEMINI_JSON_REGION_REPAIR_QUEUE_V1"
REPAIR_CONTRACT_VERSION = "TABLE_ROLLFORWARD_CELLS_ATOMIC_V1"
ATTEMPT_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_ATTEMPT_V1"
OVERLAY_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_OVERLAY_V1"
CROP_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_CROP_RECEIPT_V1"
PAGE_EVIDENCE_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_PAGE_EVIDENCE_V1"
TABLE_SPEC_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_SPEC_V1"
REPAIR_SPEC_AUTHORITY_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_REPAIR_SPEC_AUTHORITY_V1"
SOURCE_IMAGE_RESOLUTION_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_SOURCE_IMAGE_RESOLUTION_V1"
REPAIR_SCOPE = "TABLE_ROLLFORWARD_CELLS"
TARGET_OBSERVATION_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TARGET_OBSERVATIONS_V1"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FAMILY_CANDIDATE_ID = re.compile(r"^[a-z0-9]+:candidate:[0-9a-f]{64}$")
_NODE = re.compile(r"^([strc])([1-9][0-9]*)$")
_LOOSE_CELL = re.compile(r"^\s*[Rr]\s*0*([1-9][0-9]*)\s*:\s*[Cc]\s*0*([1-9][0-9]*)\s*$")
_CELL_REFERENCE = re.compile(
    r"(?i)(?<![A-Za-z0-9])R\s*0*([1-9][0-9]*)\s*:\s*C\s*0*([1-9][0-9]*)(?![A-Za-z0-9])"
)
_DASH = re.compile(r"^\s*[-−–—_](?:\s*[-−–—_])*\s*$")
_FENCE = re.compile(r"\A```(?:json)?\s*(.*?)\s*```\Z", re.DOTALL | re.IGNORECASE)
_VISUAL_STATES = frozenset({"BLANK", "DASH", "PRINTED_ZERO", "VALUE"})
_VISUAL_STATE_ALIASES = {
    "ACCOUNTING_DASH": "DASH",
    "BLANK": "BLANK",
    "DASH": "DASH",
    "EMPTY": "BLANK",
    "HYPHEN": "DASH",
    "NONE": "BLANK",
    "NUMBER": "VALUE",
    "NUMERIC": "VALUE",
    "NUMERIC_ZERO": "PRINTED_ZERO",
    "PRINTED_0": "PRINTED_ZERO",
    "PRINTED_ZERO": "PRINTED_ZERO",
    "VALUE": "VALUE",
    "ZERO": "PRINTED_ZERO",
}
_AFTER_POLICIES = frozenset({"DASH_ZERO", "SIGNED_INTEGER"})
_CHANGE_POLICIES = frozenset({"MAY_CHANGE", "MUST_CHANGE"})
_EVIDENCE_KINDS = frozenset({"ATOMIC_TABLE_COLLATERAL", "UNRESOLVED_FRONTIER"})
_THINKING_LEVELS = ("low", "medium", "high")
_ATTEMPT_OUTCOMES = frozenset(
    {
        "PROVIDER_OR_VALIDATION_FAILURE",
        "RESOLVED",
        "RETRYABLE_VALIDATION_FAILURE",
    }
)
_USAGE_FIELDS = {
    "actual_cost_usd",
    "cached_input_tokens",
    "cost_disposition",
    "input_tokens",
    "output_tokens",
    "thought_tokens",
    "total_tokens",
}
_PROVIDER_FIELDS = {
    "provider_model",
    "provider_name",
    "request_id_sha256",
    "response_id_sha256",
    "service_tier",
}
_PLAN_FIELDS = {
    "acceptance_policy",
    "base_page_json_sha256",
    "base_page_json_version_id",
    "candidate_id",
    "candidate_semantic_replay_sha256",
    "cell_allowlist",
    "compiled_spec_sources_sha256",
    "component_table_refs",
    "document_ordinal",
    "equation_inventory",
    "equation_inventory_sha256",
    "family_id",
    "format_version",
    "indexed_query_evidence_sha256",
    "page_evidence_id",
    "physical_page",
    "repair_contract_version",
    "repair_job_id",
    "repair_policy",
    "repair_scope",
    "repair_spec_sha256",
    "request_contract",
    "section_id",
    "selected_page_frontier_sha256",
    "shape_gate",
    "source_binding",
    "source_logical_name",
    "source_sha256",
    "sweep_id",
    "table_id",
    "target_ids",
    "target_table_refs",
    "trigger_kinds",
    "trigger_reasons",
}
_AUTHORITY_FIELDS = {
    "compiled_spec_sources",
    "family_sweep",
    "selected_page_json_version_ids",
    "table_repair_specs",
}
_REPAIR_SPEC_AUTHORITY_FIELDS = {
    "authority",
    "authenticity",
    "format_version",
    "manifest_sha256",
    "plan_axis_sha256",
    "repair_spec_axis_sha256",
    "source_image_bindings",
    "source_image_bindings_sha256",
    "source_image_resolver",
}
_EXTERNAL_AUTHORITY_FIELDS = {"authority_kind", "authority_ref", "authority_sha256"}
_SOURCE_IMAGE_RESOLVER_FIELDS = {
    "implementation_path",
    "implementation_sha256",
    "implementation_size_bytes",
    "mupdf_version",
    "pymupdf_version",
}
_AUTHENTICITY_BOUNDARY = {
    "caller_must_verify_and_pin_external_authority": True,
    "caller_must_verify_source_root_and_files": True,
    "self_hash_authenticates_external_authority": False,
}


class GeminiJsonRollforwardTableRepairV1Error(ValueError):
    """A bounded table repair is incomplete, ambiguous, or not source-bound."""


def _error(message: str) -> GeminiJsonRollforwardTableRepairV1Error:
    return GeminiJsonRollforwardTableRepairV1Error(message)


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise _error(f"{label} fields drifted")
    return value


def _hash(value: Any, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise _error(f"{label} is not one lowercase SHA-256")
    return value


def _prefixed_hash(value: Any, prefix: str, label: str) -> str:
    if (
        type(value) is not str
        or not value.startswith(prefix)
        or _HEX64.fullmatch(value.removeprefix(prefix)) is None
    ):
        raise _error(f"{label} is invalid")
    return value


def _node_ordinal(value: Any, prefix: str, label: str) -> int:
    if type(value) is not str:
        raise _error(f"{label} is invalid")
    match = _NODE.fullmatch(value)
    if match is None or match.group(1) != prefix:
        raise _error(f"{label} is invalid")
    return int(match.group(2)) - 1


def _cell_id(value: Any) -> tuple[int, int]:
    if type(value) is not str:
        raise _error("table repair cell ID is invalid")
    parts = value.split(":")
    if len(parts) != 2:
        raise _error("table repair cell ID is invalid")
    return (
        _node_ordinal(parts[0], "r", "repair row ID"),
        _node_ordinal(parts[1], "c", "repair column ID"),
    )


def _canonical_cell_id(value: Any) -> str | None:
    """Normalize harmless model spelling drift without widening the cell authority."""

    if type(value) is not str:
        return None
    match = _LOOSE_CELL.fullmatch(unicodedata.normalize("NFKC", value))
    if match is None:
        return None
    return f"r{int(match.group(1))}:c{int(match.group(2))}"


def _table(page_json: Any, section_id: str, table_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    checked = validate_financial_page_json_v1(page_json)
    section_index = _node_ordinal(section_id, "s", "repair section ID")
    table_index = _node_ordinal(table_id, "t", "repair table ID")
    try:
        return checked, checked["sections"][section_index]["tables"][table_index]
    except (IndexError, KeyError, TypeError) as exc:
        raise _error("table repair target lies outside the page JSON") from exc


def _signed_integer(value: Any) -> int | None:
    if type(value) is not str:
        return None
    text = unicodedata.normalize("NFKC", value).strip()
    if _DASH.fullmatch(text):
        return 0
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    elif text.startswith(("-", "−")) and text[1:].strip():
        negative = True
        text = text[1:].strip()
    digits = re.sub(r"[.,\s]", "", text)
    if not digits.isdigit():
        return None
    result = int(digits)
    return -result if negative else result


def _visual_state(source_text: Any) -> str:
    if source_text is None:
        return "BLANK"
    if type(source_text) is not str:
        raise _error("table repair cell source_text is invalid")
    if _DASH.fullmatch(unicodedata.normalize("NFKC", source_text)):
        return "DASH"
    coefficient = _signed_integer(source_text)
    if coefficient is None:
        raise _error("table repair money cell is not an exact signed integer")
    return "PRINTED_ZERO" if coefficient == 0 else "VALUE"


def _normalized_visual_state(value: Any) -> str | None:
    if type(value) is not str:
        return None
    key = re.sub(r"[\s-]+", "_", unicodedata.normalize("NFKC", value).strip().upper())
    return _VISUAL_STATE_ALIASES.get(key)


def _normalized_anchor(value: Any) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise _error("roll-forward legacy table anchor is invalid")
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()
    decomposed = unicodedata.normalize("NFD", normalized)
    folded = "".join(character for character in decomposed if not unicodedata.combining(character))
    return folded.replace("đ", "d")


def _normalized_header_anchor(value: Any, *, unit_exact: Any) -> str:
    """Flatten harmless legacy header segmentation and strip repeated unit suffixes."""

    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise _error("roll-forward legacy table header anchor is invalid")
    normalized = _normalized_anchor(" ".join(value))
    unit = _normalized_anchor(unit_exact)
    if normalized is None or not normalized:
        raise _error("roll-forward legacy table header anchor is invalid")
    if unit:
        while normalized == unit or normalized.endswith(" " + unit):
            normalized = normalized[: -len(unit)].rstrip()
    return normalized


def _cell_semantic(source_text: Any, visual_state: Any = None) -> tuple[str, int | None]:
    """Return the typed financial-cell meaning while preserving visual zero states."""

    derived = _visual_state(source_text)
    if visual_state is not None and visual_state != derived:
        raise _error("roll-forward table cell visual state conflicts with source_text")
    coefficient = _signed_integer(source_text)
    return derived, coefficient


def _normalized_observed_source_text(
    value: Any,
    *,
    declared_visual_state: Any = None,
) -> tuple[str | None, str, str | None]:
    """Return one stable financial-cell observation from tolerant JSON variants.

    JSON numbers are accepted for defensive replay even though the provider schema asks
    for strings.  Textual numbers remain source-exact (apart from surrounding whitespace),
    while JSON numbers and accounting-dash glyphs receive one canonical representation.
    A legacy ``visual_state`` may corroborate the derived state, but never overrides it.
    """

    declared = (
        None if declared_visual_state is None else _normalized_visual_state(declared_visual_state)
    )
    if declared_visual_state is not None and declared is None:
        raise _error("roll-forward target observation visual state is invalid")
    normalization = None
    if value is None and declared == "DASH":
        # Gemini occasionally emitted null while separately and correctly classifying the
        # visible accounting dash.  This is one harmless representation variant, not an
        # arithmetic inference; the local DASH_ZERO/equation gates still decide authority.
        source_text = "-"
        normalization = "LEGACY_NULL_WITH_DASH_STATE_TO_ASCII_DASH"
    elif value is None:
        source_text: str | None = None
    elif type(value) is bool:
        raise _error("roll-forward target observation source_text is invalid")
    elif type(value) is int:
        source_text = str(value)
        normalization = "JSON_INTEGER_TO_TEXT"
    elif type(value) is float:
        if not value.is_integer():
            raise _error("roll-forward target observation is not an exact integer")
        source_text = str(int(value))
        normalization = "JSON_INTEGRAL_NUMBER_TO_TEXT"
    elif type(value) is str:
        stripped = value.strip()
        source_text = stripped or None
        if source_text != value:
            normalization = "TRIMMED_SOURCE_TEXT"
        if (
            source_text is not None
            and unicodedata.normalize("NFKC", source_text) != source_text
            and not _DASH.fullmatch(unicodedata.normalize("NFKC", source_text))
        ):
            normalization = "NFKC_SEMANTIC_VARIANT_PRESERVED"
    else:
        raise _error("roll-forward target observation source_text is invalid")
    if source_text is not None and _DASH.fullmatch(unicodedata.normalize("NFKC", source_text)):
        if source_text != "-":
            normalization = "ACCOUNTING_DASH_TO_ASCII_DASH"
        source_text = "-"
    derived = _visual_state(source_text)
    if declared_visual_state is not None:
        if declared != derived:
            raise _error("roll-forward target observation visual state conflicts with source_text")
    return source_text, derived, normalization


def _source_binding(value: Any) -> dict[str, Any]:
    checked = _exact_keys(
        value,
        {
            "crop_bbox_pixels_xyxy",
            "document_id",
            "image_sha256",
            "image_size_bytes",
            "media_type",
            "page_id",
            "physical_page",
            "pixel_height",
            "pixel_width",
            "render_dpi",
            "source_logical_name",
            "source_sha256",
            "source_size_bytes",
        },
        "table repair source binding",
    )
    if type(checked["source_logical_name"]) is not str or not checked["source_logical_name"]:
        raise _error("table repair source logical name is invalid")
    _hash(checked["source_sha256"], "table repair source SHA-256")
    _prefixed_hash(checked["document_id"], "gfpstorev1:document:", "table repair document ID")
    _prefixed_hash(checked["page_id"], "gfpstorev1:page:", "table repair page ID")
    _hash(checked["image_sha256"], "table repair image SHA-256")
    if (
        type(checked["physical_page"]) is not int
        or checked["physical_page"] <= 0
        or type(checked["source_size_bytes"]) is not int
        or checked["source_size_bytes"] < 0
        or type(checked["image_size_bytes"]) is not int
        or checked["image_size_bytes"] <= 0
        or type(checked["pixel_width"]) is not int
        or checked["pixel_width"] <= 0
        or type(checked["pixel_height"]) is not int
        or checked["pixel_height"] <= 0
        or checked["render_dpi"] not in {200, 300}
        or checked["media_type"] != "image/png"
    ):
        raise _error("table repair page image metadata is invalid")
    document_material = {
        "source_logical_name": checked["source_logical_name"],
        "source_sha256": checked["source_sha256"],
        "source_size_bytes": checked["source_size_bytes"],
    }
    expected_document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(document_material)
    page_material = {
        "document_id": expected_document_id,
        "physical_page": checked["physical_page"],
        "image_sha256": checked["image_sha256"],
        "image_size_bytes": checked["image_size_bytes"],
        "pixel_width": checked["pixel_width"],
        "pixel_height": checked["pixel_height"],
        "render_dpi": checked["render_dpi"],
        "media_type": checked["media_type"],
    }
    if checked["document_id"] != expected_document_id or checked[
        "page_id"
    ] != "gfpstorev1:page:" + canonical_json_sha256_v1(page_material):
        raise _error("table repair document or page identity does not replay")
    bbox = checked["crop_bbox_pixels_xyxy"]
    if (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int for item in bbox)
        or not (0 <= bbox[0] < bbox[2] <= checked["pixel_width"])
        or not (0 <= bbox[1] < bbox[3] <= checked["pixel_height"])
    ):
        raise _error("table repair crop lies outside the bound image")
    return canonical_clone_v1(checked)


def _allowlist(value: Any, *, table: Mapping[str, Any]) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("table repair cell allowlist is empty")
    result = []
    seen = set()
    primary = 0
    for raw in value:
        item = _exact_keys(
            raw,
            {
                "after_policy",
                "before_exact",
                "cell_id",
                "change_policy",
                "evidence_kind",
            },
            "table repair allowlist item",
        )
        row_index, column_index = _cell_id(item["cell_id"])
        if item["cell_id"] in seen:
            raise _error("table repair cell allowlist is duplicate")
        seen.add(item["cell_id"])
        try:
            before = table["rows"][row_index]["values_exact"][column_index]
        except (IndexError, KeyError, TypeError) as exc:
            raise _error("table repair allowlisted cell lies outside the table") from exc
        if item["before_exact"] != before:
            raise _error("table repair allowlisted before value does not bind the base table")
        if (
            item["after_policy"] not in _AFTER_POLICIES
            or item["change_policy"] not in _CHANGE_POLICIES
            or item["evidence_kind"] not in _EVIDENCE_KINDS
        ):
            raise _error("table repair allowlist policy or evidence kind is invalid")
        if item["evidence_kind"] == "UNRESOLVED_FRONTIER":
            primary += 1
        result.append(canonical_clone_v1(item))
    if primary == 0:
        raise _error("table repair allowlist has no unresolved-frontier cell")
    return sorted(result, key=lambda item: _cell_id(item["cell_id"]))


def _equations(
    value: Any, *, row_count: int, column_count: int, allowlist: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("table repair equation inventory is empty")
    result = []
    identities = set()
    referenced_allowlist = set()
    allow_ids = {item["cell_id"] for item in allowlist}
    for raw in value:
        equation = _exact_keys(
            raw,
            {"equation_id", "result_cell_id", "terms"},
            "table repair equation",
        )
        if (
            type(equation["equation_id"]) is not str
            or not equation["equation_id"]
            or equation["equation_id"] in identities
            or type(equation["terms"]) is not list
            or not equation["terms"]
        ):
            raise _error("table repair equation identity or terms are invalid")
        identities.add(equation["equation_id"])
        coordinates = [equation["result_cell_id"]]
        checked_terms = []
        seen_terms = set()
        for raw_term in equation["terms"]:
            term = _exact_keys(
                raw_term,
                {"cell_id", "multiplier"},
                "table repair equation term",
            )
            if (
                term["cell_id"] in seen_terms
                or type(term["multiplier"]) is not int
                or term["multiplier"] == 0
            ):
                raise _error("table repair equation term is duplicate or invalid")
            seen_terms.add(term["cell_id"])
            coordinates.append(term["cell_id"])
            checked_terms.append(canonical_clone_v1(term))
        if equation["result_cell_id"] in seen_terms:
            raise _error("table repair equation result repeats a term")
        for coordinate in coordinates:
            row_index, column_index = _cell_id(coordinate)
            if row_index >= row_count or column_index >= column_count:
                raise _error("table repair equation lies outside the target table")
            if coordinate in allow_ids:
                referenced_allowlist.add(coordinate)
        result.append(
            {
                "equation_id": equation["equation_id"],
                "result_cell_id": equation["result_cell_id"],
                "terms": checked_terms,
            }
        )
    if referenced_allowlist != allow_ids:
        raise _error("table repair equation inventory does not cover the exact allowlist")
    return sorted(result, key=lambda item: item["equation_id"])


def _shape_gate(table: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "base_table_sha256": canonical_json_sha256_v1(table),
        "column_count": len(table["columns"]),
        "columns_exact": canonical_clone_v1(table["columns"]),
        "continuation_exact": table["continuation"],
        "row_axis_exact": [
            {
                "hierarchy_path_exact": canonical_clone_v1(row["hierarchy_path_exact"]),
                "label_exact": row["label_exact"],
                "row_kind": row["row_kind"],
            }
            for row in table["rows"]
        ],
        "row_count": len(table["rows"]),
        "table_title_exact": table["title_exact"],
        "unit_exact": table["unit_exact"],
    }


def load_rollforward_table_page_evidence_v1(
    page_store_path: Path, *, page_json_version_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Replay exact page/source/image provenance from one frozen V9 page store."""

    version_ids = list(page_json_version_ids)
    if (
        not version_ids
        or len(version_ids) != len(set(version_ids))
        or any(
            type(version_id) is not str
            or not version_id.startswith("gfpstorev1:json:")
            or _HEX64.fullmatch(version_id.removeprefix("gfpstorev1:json:")) is None
            for version_id in version_ids
        )
    ):
        raise _error("table repair page evidence version frontier is invalid")
    supplied_path = Path(page_store_path)
    descriptor_path = (
        len(supplied_path.parts) == 5
        and supplied_path.parts[:4] == ("/", "proc", "self", "fd")
        and supplied_path.parts[4].isdigit()
    )
    path = supplied_path if descriptor_path else supplied_path.resolve()
    if (supplied_path.is_symlink() and not descriptor_path) or not path.is_file():
        raise _error("table repair frozen page store is absent or not regular")
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        identity = connection.execute(
            "SELECT format_version,page_format_version,search_normalization_version "
            "FROM store_identity WHERE singleton=1"
        ).fetchone()
        if identity is None or tuple(identity) != (
            "GEMINI_FINANCIAL_PAGE_STORE_V9",
            PAGE_FORMAT_VERSION,
            SEARCH_NORMALIZATION_VERSION,
        ):
            raise _error("table repair frozen page store identity drifted")
        connection.execute(
            "CREATE TEMP TABLE selected_table_repair_page("
            "selection_ordinal INTEGER PRIMARY KEY,page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_table_repair_page VALUES (?,?)",
            enumerate(version_ids, start=1),
        )
        rows = connection.execute(
            "SELECT s.selection_ordinal,v.page_json_version_id,v.extraction_run_id,"
            "v.canonical_json_sha256,v.canonical_json_bytes,p.page_id,p.document_id,"
            "p.physical_page,p.image_sha256,p.image_size_bytes,p.pixel_width,p.pixel_height,"
            "p.render_dpi,p.media_type,d.source_logical_name,d.source_sha256,"
            "d.source_size_bytes FROM selected_table_repair_page AS s "
            "JOIN page_json_version AS v USING(page_json_version_id) "
            "JOIN page AS p USING(page_id) JOIN document AS d USING(document_id) "
            "ORDER BY s.selection_ordinal"
        ).fetchall()
    except (sqlite3.DatabaseError, OSError) as exc:
        raise _error("table repair frozen page store cannot be replayed") from exc
    finally:
        if "connection" in locals():
            connection.close()
    if len(rows) != len(version_ids):
        raise _error("table repair page version is absent from the frozen store")
    result = []
    for version_id, row in zip(version_ids, rows, strict=True):
        try:
            page_json = validate_financial_page_json_v1(json.loads(row["canonical_json_bytes"]))
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _error("table repair stored page JSON is invalid") from exc
        canonical = canonical_json_bytes_v1(page_json) + b"\n"
        canonical_sha = sha256(canonical).hexdigest()
        document_material = {
            "source_logical_name": row["source_logical_name"],
            "source_sha256": row["source_sha256"],
            "source_size_bytes": row["source_size_bytes"],
        }
        document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(document_material)
        page_material = {
            "document_id": document_id,
            "physical_page": row["physical_page"],
            "image_sha256": row["image_sha256"],
            "image_size_bytes": row["image_size_bytes"],
            "pixel_width": row["pixel_width"],
            "pixel_height": row["pixel_height"],
            "render_dpi": row["render_dpi"],
            "media_type": row["media_type"],
        }
        page_id = "gfpstorev1:page:" + canonical_json_sha256_v1(page_material)
        expected_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": canonical_sha,
                "extraction_run_id": row["extraction_run_id"],
                "page_id": page_id,
            }
        )
        if (
            row["page_json_version_id"] != version_id
            or row["canonical_json_sha256"] != canonical_sha
            or bytes(row["canonical_json_bytes"]) != canonical
            or row["document_id"] != document_id
            or row["page_id"] != page_id
            or expected_version_id != version_id
        ):
            raise _error("table repair page/source/version evidence does not replay")
        source_binding_without_crop = {
            "document_id": document_id,
            "image_sha256": row["image_sha256"],
            "image_size_bytes": row["image_size_bytes"],
            "media_type": row["media_type"],
            "page_id": page_id,
            "physical_page": row["physical_page"],
            "pixel_height": row["pixel_height"],
            "pixel_width": row["pixel_width"],
            "render_dpi": row["render_dpi"],
            "source_logical_name": row["source_logical_name"],
            "source_sha256": row["source_sha256"],
            "source_size_bytes": row["source_size_bytes"],
        }
        material = {
            "base_page_json_sha256": canonical_json_sha256_v1(page_json),
            "base_page_json_version_id": version_id,
            "format_version": PAGE_EVIDENCE_FORMAT_VERSION,
            "page_json": page_json,
            "source_binding_without_crop": source_binding_without_crop,
        }
        result.append(
            {
                **material,
                "page_evidence_id": "gjfrpev1:evidence:" + canonical_json_sha256_v1(material),
            }
        )
    return result


def validate_rollforward_table_repair_plan_page_store_v1(
    plan: Mapping[str, Any], *, page_store_path: Path
) -> dict[str, Any]:
    """Cross-bind one immutable plan to its current frozen-store source row."""

    checked = _validated_plan(plan)
    evidence = load_rollforward_table_page_evidence_v1(
        page_store_path,
        page_json_version_ids=[checked["base_page_json_version_id"]],
    )[0]
    expected_binding = {
        **evidence["source_binding_without_crop"],
        "crop_bbox_pixels_xyxy": checked["source_binding"]["crop_bbox_pixels_xyxy"],
    }
    if (
        evidence["base_page_json_sha256"] != checked["base_page_json_sha256"]
        or _source_binding(expected_binding) != checked["source_binding"]
        or evidence["page_evidence_id"] != checked["page_evidence_id"]
    ):
        raise _error("table repair plan does not replay against the frozen page store")
    target = rollforward_table_repair_target_v1(evidence["page_json"], plan=checked)
    prompt = build_rollforward_table_repair_prompt_v1(
        base_page_json_version_id=checked["base_page_json_version_id"],
        target=target,
    )
    if checked["request_contract"]["prompt_sha256"] != sha256(prompt.encode("utf-8")).hexdigest():
        raise _error("table repair prompt does not replay from frozen page evidence")
    return evidence


def _build_rollforward_table_cell_repair_plans_v1(
    *,
    unresolved_frontier: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build deterministic whole-table sibling jobs from declarative frontiers."""

    if type(unresolved_frontier) not in {list, tuple} or not unresolved_frontier:
        raise _error("roll-forward table repair unresolved frontier is empty")
    plans = []
    locations = set()
    for raw in unresolved_frontier:
        frontier = _exact_keys(
            raw,
            {
                "base_page_json_sha256",
                "base_page_json_version_id",
                "candidate_id",
                "candidate_semantic_replay_sha256",
                "cell_allowlist",
                "compiled_spec_sources_sha256",
                "document_ordinal",
                "equations",
                "family_id",
                "format_version",
                "indexed_query_evidence_sha256",
                "page_evidence_id",
                "repair_spec_sha256",
                "selected_page_frontier_sha256",
                "section_id",
                "source_binding",
                "sweep_id",
                "table_id",
                "trigger_reasons",
            },
            "roll-forward table repair unresolved frontier",
        )
        if frontier["format_version"] != UNRESOLVED_FRONTIER_FORMAT_VERSION:
            raise _error("roll-forward table repair frontier version drifted")
        if (
            type(frontier["family_id"]) is not str
            or not frontier["family_id"]
            or type(frontier["sweep_id"]) is not str
            or not frontier["sweep_id"]
            or type(frontier["document_ordinal"]) is not int
            or frontier["document_ordinal"] <= 0
            or type(frontier["candidate_id"]) is not str
            or _FAMILY_CANDIDATE_ID.fullmatch(frontier["candidate_id"]) is None
            or type(frontier["trigger_reasons"]) is not list
            or not frontier["trigger_reasons"]
            or any(type(reason) is not str or not reason for reason in frontier["trigger_reasons"])
        ):
            raise _error("roll-forward table repair frontier identity is invalid")
        version_id = _prefixed_hash(
            frontier["base_page_json_version_id"],
            "gfpstorev1:json:",
            "table repair base page version",
        )
        page_json = page_json_by_version.get(version_id)
        if type(page_json) is not dict:
            raise _error("table repair base page JSON is absent")
        checked_page, table = _table(page_json, frontier["section_id"], frontier["table_id"])
        if frontier["base_page_json_sha256"] != canonical_json_sha256_v1(checked_page):
            raise _error("table repair base page JSON SHA-256 does not replay")
        source_binding = _source_binding(frontier["source_binding"])
        allowlist = _allowlist(frontier["cell_allowlist"], table=table)
        equations = _equations(
            frontier["equations"],
            row_count=len(table["rows"]),
            column_count=len(table["columns"]),
            allowlist=allowlist,
        )
        location = (version_id, frontier["section_id"], frontier["table_id"])
        if location in locations:
            raise _error("table repair frontier repeats one base table")
        locations.add(location)
        shape_gate = _shape_gate(table)
        target_cells = []
        for allowed in allowlist:
            row_index, column_index = _cell_id(allowed["cell_id"])
            target_cells.append(
                {
                    "after_policy": allowed["after_policy"],
                    "cell_id": allowed["cell_id"],
                    "change_policy": allowed["change_policy"],
                    "column_header_exact": canonical_clone_v1(
                        table["columns"][column_index]["header_path_exact"]
                    ),
                    "evidence_kind": allowed["evidence_kind"],
                    "row_label_exact": table["rows"][row_index]["label_exact"],
                }
            )
        target = {
            "column_headers_exact": [
                canonical_clone_v1(column["header_path_exact"]) for column in table["columns"]
            ],
            "column_value_kinds": [column["value_kind"] for column in table["columns"]],
            "row_labels_exact": [row["label_exact"] for row in table["rows"]],
            "target_cells": target_cells,
            "target_id": f"{frontier['section_id']}:{frontier['table_id']}",
            "table_title_exact": table["title_exact"],
            "unit_exact": table["unit_exact"],
        }
        prompt = build_rollforward_table_repair_prompt_v1(
            base_page_json_version_id=version_id,
            target=target,
        )
        response_schema = rollforward_table_repair_response_schema_v1()
        material = {
            "acceptance_policy": {
                "all_other_cells_byte_equal": True,
                "forbid_arithmetic_backsolve": True,
                "ignore_non_authoritative_observations": True,
                "preserve_omitted_may_change_cells": True,
                "require_must_change_and_collateral_observations": True,
                "require_all_declared_equations_exact": True,
                "require_immutable_shape_period_and_unit": True,
            },
            "base_page_json_sha256": frontier["base_page_json_sha256"],
            "base_page_json_version_id": version_id,
            "candidate_id": frontier["candidate_id"],
            "candidate_semantic_replay_sha256": frontier["candidate_semantic_replay_sha256"],
            "cell_allowlist": allowlist,
            "compiled_spec_sources_sha256": frontier["compiled_spec_sources_sha256"],
            "component_table_refs": [
                {"section_id": frontier["section_id"], "table_id": frontier["table_id"]}
            ],
            "document_ordinal": frontier["document_ordinal"],
            "equation_inventory": equations,
            "equation_inventory_sha256": canonical_json_sha256_v1(equations),
            "family_id": frontier["family_id"],
            "format_version": QUEUE_FORMAT_VERSION,
            "indexed_query_evidence_sha256": frontier["indexed_query_evidence_sha256"],
            "physical_page": source_binding["physical_page"],
            "page_evidence_id": frontier["page_evidence_id"],
            "repair_spec_sha256": frontier["repair_spec_sha256"],
            "selected_page_frontier_sha256": frontier["selected_page_frontier_sha256"],
            "repair_contract_version": REPAIR_CONTRACT_VERSION,
            "repair_policy": {
                "attempt_lineage": "SIBLINGS_FROM_IMMUTABLE_BASE",
                "initial_thinking_level": "low",
                "max_attempts": 3,
                "thinking_escalation": ["medium", "high"],
            },
            "repair_scope": REPAIR_SCOPE,
            "request_contract": {
                "output_contract_mode": "JSON_SCHEMA",
                "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
                "prompt_variant": "rollforward-table-cells",
                "response_schema_sha256": canonical_json_sha256_v1(response_schema),
            },
            "section_id": frontier["section_id"],
            "shape_gate": shape_gate,
            "source_binding": source_binding,
            "source_logical_name": source_binding["source_logical_name"],
            "source_sha256": source_binding["source_sha256"],
            "sweep_id": frontier["sweep_id"],
            "table_id": frontier["table_id"],
            "target_ids": [
                f"{frontier['section_id']}:{frontier['table_id']}:{item['cell_id']}"
                for item in allowlist
            ],
            "target_table_refs": [
                {"section_id": frontier["section_id"], "table_id": frontier["table_id"]}
            ],
            "trigger_kinds": ["ROLLFORWARD_TYPED_CELL_EVIDENCE_INCOMPLETE"],
            "trigger_reasons": canonical_clone_v1(frontier["trigger_reasons"]),
        }
        plans.append(
            {
                **material,
                "repair_job_id": "gjfrrqv1:job:" + canonical_json_sha256_v1(material),
            }
        )
    return sorted(plans, key=lambda item: (item["document_ordinal"], item["repair_job_id"]))


def _vector_cell_id(vector: Mapping[str, Any]) -> str:
    row_id = vector.get("row_id")
    column_ordinal = vector.get("column_ordinal")
    _node_ordinal(row_id, "r", "roll-forward source vector row")
    if type(column_ordinal) is not int or column_ordinal <= 0:
        raise _error("roll-forward source vector column is invalid")
    return f"{row_id}:c{column_ordinal}"


def _frontier_vector(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    frontier: Mapping[str, Any],
    source_record: Mapping[str, Any],
) -> dict[str, Any]:
    matches = [
        vector
        for vector in role_vectors
        if vector.get("period_role") == frontier.get("period_role")
        and vector.get("lane_role") == frontier.get("lane_role")
        and vector.get("movement_role") == source_record.get("movement_role")
        and vector.get("row_id") == source_record.get("row_id")
        and vector.get("locator") == source_record.get("locator")
    ]
    if len(matches) != 1:
        raise _error("unresolved frontier does not bind one exact role vector")
    return canonical_clone_v1(matches[0])


def _closure_equation_v1(
    *,
    closure: Mapping[str, Any],
    frontier: Mapping[str, Any],
    closing_role: str,
) -> dict[str, Any]:
    equations = [
        equation
        for equation in closure.get("equations", [])
        if equation.get("period_role") == frontier.get("period_role")
        and equation.get("lane_role") == frontier.get("lane_role")
    ]
    if len(equations) != 1:
        raise _error("unresolved frontier does not bind one exact closure equation")
    equation = equations[0]
    role_coefficients = equation.get("role_coefficients")
    if type(role_coefficients) is not list or not role_coefficients:
        raise _error("roll-forward closure equation role axis is invalid")
    by_role = {item.get("role"): item for item in role_coefficients}
    if len(by_role) != len(role_coefficients) or closing_role not in by_role:
        raise _error("roll-forward closure equation has no unique closing role")
    closing_coefficient = by_role[closing_role].get("equation_coefficient")
    if closing_coefficient not in {-1, 1}:
        raise _error("roll-forward closing equation coefficient is invalid")
    vectors = closure.get("role_vectors")
    if type(vectors) is not list:
        raise _error("roll-forward closure role vectors are invalid")
    vector_by_role = {}
    for role in by_role:
        matches = [
            vector
            for vector in vectors
            if vector.get("period_role") == frontier.get("period_role")
            and vector.get("lane_role") == frontier.get("lane_role")
            and vector.get("movement_role") == role
        ]
        if len(matches) != 1:
            raise _error("roll-forward closure equation role vector is not unique")
        vector_by_role[role] = matches[0]
    terms = []
    for role, item in sorted(by_role.items()):
        if role == closing_role:
            continue
        coefficient = item.get("equation_coefficient")
        if type(coefficient) is not int or coefficient == 0:
            raise _error("roll-forward closure equation coefficient is invalid")
        numerator = -coefficient
        if numerator % closing_coefficient:
            raise _error("roll-forward closure equation cannot be expressed exactly")
        terms.append(
            {
                "cell_id": _vector_cell_id(vector_by_role[role]),
                "multiplier": numerator // closing_coefficient,
            }
        )
    result_cell_id = _vector_cell_id(vector_by_role[closing_role])
    material = {
        "lane_role": frontier["lane_role"],
        "period_role": frontier["period_role"],
        "result_cell_id": result_cell_id,
        "terms": terms,
    }
    return {
        "equation_id": "rollforward:" + canonical_json_sha256_v1(material),
        "result_cell_id": result_cell_id,
        "terms": terms,
    }


def _collateral_equation_signature(equation: Mapping[str, Any]) -> tuple[Any, ...] | None:
    result_row, result_column = _cell_id(equation["result_cell_id"])
    term_coordinates = [
        (*_cell_id(term["cell_id"]), term["multiplier"]) for term in equation["terms"]
    ]
    if any(row != result_row for row, _column, _multiplier in term_coordinates):
        return None
    return (
        result_column,
        tuple(sorted((column, multiplier) for _row, column, multiplier in term_coordinates)),
    )


def _validate_collateral_equation_corroboration(
    table: Mapping[str, Any],
    *,
    collateral_equations: Sequence[Mapping[str, Any]],
    collateral_cell_ids: set[str],
) -> None:
    by_signature: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for equation in collateral_equations:
        signature = _collateral_equation_signature(equation)
        if signature is None:
            raise _error("table repair collateral equation is not one row-local pattern")
        by_signature.setdefault(signature, []).append(equation)
    covered = set()
    for equations in by_signature.values():
        closed_siblings = 0
        group_covered = set()
        for equation in equations:
            referenced = {
                equation["result_cell_id"],
                *(term["cell_id"] for term in equation["terms"]),
            }
            group_covered.update(referenced & collateral_cell_ids)
            result_row, result_column = _cell_id(equation["result_cell_id"])
            result = _signed_integer(table["rows"][result_row]["values_exact"][result_column])
            terms = []
            for term in equation["terms"]:
                row, column = _cell_id(term["cell_id"])
                terms.append(
                    (
                        term["multiplier"],
                        _signed_integer(table["rows"][row]["values_exact"][column]),
                    )
                )
            if result is not None and all(value is not None for _multiplier, value in terms):
                expected = sum(multiplier * value for multiplier, value in terms)
                if result == expected:
                    closed_siblings += 1
        covered.update(group_covered)
        if group_covered and closed_siblings < 2:
            raise _error("table repair collateral equation lacks two exact sibling rows")
    if covered != collateral_cell_ids:
        raise _error("table repair collateral equations do not cover exact collateral cells")


def build_rollforward_table_cell_repair_plans_v1(
    *,
    compiled_specs: Mapping[str, Any],
    family_sweep: Mapping[str, Any],
    page_store_path: Path,
    selected_page_json_version_ids: Sequence[str],
    table_repair_specs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Derive jobs after exact page-DB query and semantic candidate replay.

    ``selected_page_json_version_ids`` is the caller's already-authenticated corpus
    or effective frontier.  The function replays the sweep's indexed query evidence
    against that exact ordered frontier and then rebuilds every selected candidate
    from page JSON before it derives a repair cell.
    """

    sweep = validate_gemini_json_flat_family_sweep_v1(family_sweep)
    compiled_spec_sources = {
        "evaluation": canonical_clone_v1(sweep["specs"]["evaluation"]["value"]),
        "schema_binding": canonical_clone_v1(sweep["specs"]["schema_binding"]["value"]),
        "topology": canonical_clone_v1(sweep["specs"]["topology"]["value"]),
    }
    rebuilt_specs = compile_gemini_json_flat_family_specs_v1(
        compiled_spec_sources["topology"],
        compiled_spec_sources["evaluation"],
        compiled_spec_sources["schema_binding"],
    )
    if not same_typed_json_v1(dict(compiled_specs), rebuilt_specs):
        raise _error("roll-forward table repair compiled specs do not replay the sweep")
    selected_ids = list(selected_page_json_version_ids)
    if (
        not selected_ids
        or len(selected_ids) != len(set(selected_ids))
        or any(
            type(version_id) is not str or not version_id.startswith("gfpstorev1:json:")
            for version_id in selected_ids
        )
    ):
        raise _error("roll-forward table repair selected page frontier is invalid")
    indexed_query_evidence = sweep.get("indexed_query_evidence")
    if type(indexed_query_evidence) is not dict:
        raise _error("roll-forward table repair sweep has no indexed query evidence")
    from bctc_ai.storage.gemini_financial_page_store_v1 import (
        validate_selected_rollforward_family_query_evidence_v1,
    )

    validate_selected_rollforward_family_query_evidence_v1(
        page_store_path,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=rebuilt_specs,
        indexed_query_evidence=indexed_query_evidence,
        trials=sweep["trials"],
    )
    specs = list(table_repair_specs)
    if not specs:
        raise _error("roll-forward table repair spec axis is empty")
    version_ids = []
    checked_specs = []
    spec_fields = {
        "base_page_json_version_id",
        "collateral_cell_ids",
        "collateral_equations",
        "crop_bbox_pixels_xyxy",
        "dash_zero_cell_ids",
        "format_version",
        "section_id",
        "table_id",
    }
    for raw in specs:
        spec = _exact_keys(raw, spec_fields, "roll-forward table repair spec")
        if (
            spec["format_version"] != TABLE_SPEC_FORMAT_VERSION
            or type(spec["collateral_cell_ids"]) is not list
            or len(spec["collateral_cell_ids"]) != len(set(spec["collateral_cell_ids"]))
            or type(spec["dash_zero_cell_ids"]) is not list
            or len(spec["dash_zero_cell_ids"]) != len(set(spec["dash_zero_cell_ids"]))
            or type(spec["collateral_equations"]) is not list
        ):
            raise _error("roll-forward table repair spec is invalid")
        _node_ordinal(spec["section_id"], "s", "table repair spec section")
        _node_ordinal(spec["table_id"], "t", "table repair spec table")
        for cell_id in [*spec["collateral_cell_ids"], *spec["dash_zero_cell_ids"]]:
            _cell_id(cell_id)
        version_ids.append(
            _prefixed_hash(
                spec["base_page_json_version_id"],
                "gfpstorev1:json:",
                "table repair spec page version",
            )
        )
        checked_specs.append(canonical_clone_v1(spec))
    if len(version_ids) != len(set(version_ids)):
        raise _error("roll-forward table repair spec repeats one base page")
    evidence_axis = load_rollforward_table_page_evidence_v1(
        page_store_path, page_json_version_ids=version_ids
    )
    evidence_by_version = {item["base_page_json_version_id"]: item for item in evidence_axis}
    evaluation_spec = sweep["specs"]["evaluation"]["value"]
    layout_spec = evaluation_spec.get("layout_spec", evaluation_spec.get("layout", {}))
    movement_roles = layout_spec.get("movement_roles")
    closing = [item.get("role") for item in movement_roles or [] if item.get("kind") == "CLOSING"]
    if len(closing) != 1:
        raise _error("roll-forward repair sweep has no unique closing movement role")
    frontiers = []
    pages = {}
    for spec in checked_specs:
        version_id = spec["base_page_json_version_id"]
        evidence = evidence_by_version[version_id]
        page_json = evidence["page_json"]
        _checked_page, table = _table(page_json, spec["section_id"], spec["table_id"])
        matches = []
        for trial in sweep["trials"]:
            for candidate in trial.get("candidates", []):
                regions = [
                    region
                    for region in candidate.get("component_regions", [])
                    if region.get("page_json_version_id") == version_id
                    and region.get("section_id") == spec["section_id"]
                    and region.get("table_id") == spec["table_id"]
                ]
                if regions:
                    matches.append((trial, candidate, regions[0]))
        if len(matches) != 1:
            raise _error("table repair spec does not bind one swept candidate region")
        trial, candidate, region = matches[0]
        component_regions = candidate.get("component_regions")
        if type(component_regions) is not list or not component_regions:
            raise _error("table repair candidate component region axis is invalid")
        component_version_ids = list(
            dict.fromkeys(item.get("page_json_version_id") for item in component_regions)
        )
        if any(version not in selected_ids for version in component_version_ids):
            raise _error("table repair candidate lies outside the selected page frontier")
        binding_without_crop = evidence["source_binding_without_crop"]
        if (
            trial["status"] != UNRESOLVED
            or candidate["status"] != UNRESOLVED
            or candidate["family_id"] != sweep["family_id"]
            or region["document_id"] != binding_without_crop["document_id"]
            or region["physical_page"] != binding_without_crop["physical_page"]
            or region["source_logical_name"] != binding_without_crop["source_logical_name"]
            or region["source_sha256"] != binding_without_crop["source_sha256"]
        ):
            raise _error("table repair swept candidate/source binding drifted")
        closure = candidate["closure_receipt"]
        role_vectors = closure.get("role_vectors")
        unresolved = closure.get("unresolved_frontiers")
        if type(role_vectors) is not list or type(unresolved) is not list:
            raise _error("table repair candidate has no typed unresolved closure")
        relevant = []
        primary: dict[str, dict[str, Any]] = {}
        mismatch_rows = set()
        equations = []
        for unresolved_item in unresolved:
            reason = unresolved_item.get("reason")
            if type(reason) is not str or not (
                "ROLLFORWARD_LANE_EQUATION_RANK_DEFICIENT_MULTIPLE_UNKNOWNS:" in reason
                or "ROLLFORWARD_LANE_EQUATION_MISMATCH:" in reason
            ):
                continue
            source_records = unresolved_item.get("source_records")
            if type(source_records) is not list:
                raise _error("table repair unresolved source record axis is invalid")
            records = [record for record in source_records if record.get("locator") == region]
            if not records:
                continue
            relevant.append(unresolved_item)
            mismatch = "_MISMATCH:" in reason
            unknown_roles = unresolved_item.get("unknown_roles")
            if type(unknown_roles) is not list:
                raise _error("table repair unresolved role axis is invalid")
            selected_records = (
                records
                if mismatch
                else [record for record in records if record.get("movement_role") in unknown_roles]
            )
            if not selected_records:
                raise _error("table repair unresolved frontier selects no repair cell")
            for record in selected_records:
                vector = _frontier_vector(
                    role_vectors,
                    frontier=unresolved_item,
                    source_record=record,
                )
                cell_id = _vector_cell_id(vector)
                row_index, column_index = _cell_id(cell_id)
                before = table["rows"][row_index]["values_exact"][column_index]
                if not mismatch and before is not None:
                    raise _error("rank-deficient repair primary is not one source BLANK")
                if mismatch:
                    mismatch_rows.add(row_index)
                prior = primary.get(cell_id)
                change_policy = "MAY_CHANGE" if mismatch else "MUST_CHANGE"
                if prior is not None and prior["change_policy"] != change_policy:
                    raise _error("table repair cell has conflicting unresolved semantics")
                primary[cell_id] = {
                    "after_policy": "SIGNED_INTEGER",
                    "before_exact": before,
                    "cell_id": cell_id,
                    "change_policy": change_policy,
                    "evidence_kind": "UNRESOLVED_FRONTIER",
                }
            equations.append(
                _closure_equation_v1(
                    closure=closure,
                    frontier=unresolved_item,
                    closing_role=closing[0],
                )
            )
        if not relevant or not primary:
            raise _error("table repair spec is not backed by a typed unresolved equation")
        collateral_ids = set(spec["collateral_cell_ids"])
        if collateral_ids & set(primary):
            raise _error("table repair collateral repeats one primary cell")
        for cell_id in collateral_ids:
            row_index, column_index = _cell_id(cell_id)
            if (
                row_index >= len(table["rows"])
                or column_index >= len(table["columns"])
                or row_index not in mismatch_rows
            ):
                raise _error("table repair collateral is not local to a mismatch row")
            primary[cell_id] = {
                "after_policy": "SIGNED_INTEGER",
                "before_exact": table["rows"][row_index]["values_exact"][column_index],
                "cell_id": cell_id,
                "change_policy": "MAY_CHANGE",
                "evidence_kind": "ATOMIC_TABLE_COLLATERAL",
            }
        dash_zero_ids = set(spec["dash_zero_cell_ids"])
        if not dash_zero_ids <= set(primary):
            raise _error("table repair dash-zero policy lies outside derived cells")
        for cell_id in dash_zero_ids:
            primary[cell_id]["after_policy"] = "DASH_ZERO"
        collateral_equations = canonical_clone_v1(spec["collateral_equations"])
        if collateral_ids:
            checked_collateral = _equations(
                collateral_equations,
                row_count=len(table["rows"]),
                column_count=len(table["columns"]),
                allowlist=[primary[cell_id] for cell_id in sorted(collateral_ids)],
            )
            _validate_collateral_equation_corroboration(
                table,
                collateral_equations=checked_collateral,
                collateral_cell_ids=collateral_ids,
            )
            equations.extend(checked_collateral)
        elif collateral_equations:
            raise _error("table repair collateral equations have no collateral cells")
        repair_spec_sha = canonical_json_sha256_v1(spec)
        source_binding = _source_binding(
            {
                **binding_without_crop,
                "crop_bbox_pixels_xyxy": spec["crop_bbox_pixels_xyxy"],
            }
        )
        frontiers.append(
            {
                "base_page_json_sha256": evidence["base_page_json_sha256"],
                "base_page_json_version_id": version_id,
                "candidate_id": candidate["candidate_id"],
                "candidate_semantic_replay_sha256": canonical_json_sha256_v1(candidate),
                "cell_allowlist": sorted(
                    primary.values(), key=lambda item: _cell_id(item["cell_id"])
                ),
                "compiled_spec_sources_sha256": canonical_json_sha256_v1(compiled_spec_sources),
                "document_ordinal": trial["document_ordinal"],
                "equations": equations,
                "family_id": sweep["family_id"],
                "format_version": UNRESOLVED_FRONTIER_FORMAT_VERSION,
                "indexed_query_evidence_sha256": canonical_json_sha256_v1(indexed_query_evidence),
                "page_evidence_id": evidence["page_evidence_id"],
                "repair_spec_sha256": repair_spec_sha,
                "selected_page_frontier_sha256": canonical_json_sha256_v1(selected_ids),
                "section_id": spec["section_id"],
                "source_binding": source_binding,
                "sweep_id": sweep["sweep_id"],
                "table_id": spec["table_id"],
                "trigger_reasons": sorted({item["reason"] for item in relevant}),
            }
        )
        pages[version_id] = page_json
    return _build_rollforward_table_cell_repair_plans_v1(
        unresolved_frontier=frontiers,
        page_json_by_version=pages,
    )


def _equity_matrix_repair_equations_v1(
    *, table: Mapping[str, Any], closure: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    """Rebuild exact horizontal and vertical identities from the typed matrix graph."""

    component_axis = closure.get("component_axis")
    movement_axis = closure.get("movement_axis")
    if (
        closure.get("orientation") != "COMPONENT_ROWS"
        or type(component_axis) is not list
        or not component_axis
        or type(movement_axis) is not list
        or len(movement_axis) != 4
    ):
        raise _error("equity-matrix repair requires one ordinary component-row matrix")
    rows = {item.get("axis_id"): item for item in component_axis if type(item) is dict}
    columns = {item.get("axis_role"): item.get("axis_id") for item in movement_axis}
    if (
        len(rows) != len(component_axis)
        or set(columns) != {"OPENING", "INCREASE", "DECREASE", "CLOSING"}
        or len(set(columns.values())) != 4
    ):
        raise _error("equity-matrix repair movement/component axes are ambiguous")
    totals = [axis_id for axis_id, item in rows.items() if item.get("kind") == "GRAND_TOTAL"]
    if len(totals) != 1:
        raise _error("equity-matrix repair has no unique visible grand total")
    grand_total = totals[0]
    child_ids = set()
    group_axes = []
    for axis_id, item in rows.items():
        if item.get("kind") != "MAPPED_COMPONENT_GROUP_TOTAL":
            continue
        hierarchy = item.get("hierarchy_resolution")
        children = hierarchy.get("child_axis_ids") if type(hierarchy) is dict else None
        if (
            type(children) is not list
            or not children
            or any(child not in rows for child in children)
        ):
            raise _error("equity-matrix repair group-total frontier is invalid")
        child_ids.update(children)
        group_axes.append((axis_id, children))
    direct_rows = [
        axis_id
        for axis_id, item in rows.items()
        if axis_id != grand_total
        and axis_id not in child_ids
        and item.get("kind") != "SOURCE_ONLY_COMPONENT"
    ]
    if not direct_rows:
        raise _error("equity-matrix repair horizontal frontier is empty")

    equations = []
    mismatch_rows = set()
    mismatch_columns = set()

    def coefficient(cell_id: str) -> int | None:
        row_index, column_index = _cell_id(cell_id)
        return _signed_integer(table["rows"][row_index]["values_exact"][column_index])

    def add_equation(
        equation_id: str,
        *,
        result_cell_id: str,
        terms: list[dict[str, Any]],
        row_axis_id: str | None = None,
        column_axis_id: str | None = None,
    ) -> None:
        equation = {
            "equation_id": equation_id,
            "result_cell_id": result_cell_id,
            "terms": terms,
        }
        equations.append(equation)
        result = coefficient(result_cell_id)
        values = [(term["multiplier"], coefficient(term["cell_id"])) for term in terms]
        if result is None or any(value is None for _multiplier, value in values):
            return
        expected = sum(multiplier * value for multiplier, value in values if value is not None)
        if result != expected:
            if row_axis_id is not None:
                mismatch_rows.add(row_axis_id)
            if column_axis_id is not None:
                mismatch_columns.add(column_axis_id)

    for column_axis_id in columns.values():
        add_equation(
            f"horizontal-grand-{column_axis_id}",
            result_cell_id=f"{grand_total}:{column_axis_id}",
            terms=[
                {"cell_id": f"{row_axis_id}:{column_axis_id}", "multiplier": 1}
                for row_axis_id in direct_rows
            ],
            column_axis_id=column_axis_id,
        )
        for group_axis_id, children in group_axes:
            add_equation(
                f"horizontal-group-{group_axis_id}-{column_axis_id}",
                result_cell_id=f"{group_axis_id}:{column_axis_id}",
                terms=[
                    {"cell_id": f"{child}:{column_axis_id}", "multiplier": 1} for child in children
                ],
                column_axis_id=column_axis_id,
            )
    for row_axis_id in rows:
        add_equation(
            f"vertical-rollforward-{row_axis_id}",
            result_cell_id=f"{row_axis_id}:{columns['CLOSING']}",
            terms=[
                {"cell_id": f"{row_axis_id}:{columns['OPENING']}", "multiplier": 1},
                {"cell_id": f"{row_axis_id}:{columns['INCREASE']}", "multiplier": 1},
                {"cell_id": f"{row_axis_id}:{columns['DECREASE']}", "multiplier": -1},
            ],
            row_axis_id=row_axis_id,
        )
    return equations, mismatch_rows, mismatch_columns


def build_equity_matrix_table_cell_repair_plans_v1(
    *,
    compiled_specs: Mapping[str, Any],
    family_sweep: Mapping[str, Any],
    page_store_path: Path,
    selected_page_json_version_ids: Sequence[str],
    table_repair_specs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Derive minimal cell observations from an authenticated matrix failure graph.

    The caller declares only source crops and cells whose printed dash state must
    be preserved.  Candidate replay, invalid-cell coordinates, graph mismatch
    intersections and every accounting equation are rebuilt locally.
    """

    sweep = validate_gemini_json_flat_family_sweep_v1(family_sweep)
    compiled_spec_sources = {
        "evaluation": canonical_clone_v1(sweep["specs"]["evaluation"]["value"]),
        "schema_binding": canonical_clone_v1(sweep["specs"]["schema_binding"]["value"]),
        "topology": canonical_clone_v1(sweep["specs"]["topology"]["value"]),
    }
    rebuilt_specs = compile_gemini_json_flat_family_specs_v1(
        compiled_spec_sources["topology"],
        compiled_spec_sources["evaluation"],
        compiled_spec_sources["schema_binding"],
    )
    if rebuilt_specs.get(
        "engine_format_version"
    ) != "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1" or not same_typed_json_v1(
        dict(compiled_specs), rebuilt_specs
    ):
        raise _error("equity-matrix repair compiled specs do not replay the sweep")
    selected_ids = list(selected_page_json_version_ids)
    if (
        not selected_ids
        or len(selected_ids) != len(set(selected_ids))
        or any(
            type(version_id) is not str or not version_id.startswith("gfpstorev1:json:")
            for version_id in selected_ids
        )
    ):
        raise _error("equity-matrix repair selected page frontier is invalid")
    indexed_query_evidence = sweep.get("indexed_query_evidence")
    if type(indexed_query_evidence) is not dict:
        raise _error("equity-matrix repair sweep has no indexed query evidence")
    from bctc_ai.storage.gemini_financial_page_store_v1 import (
        validate_selected_equity_matrix_family_candidate_replays_v1,
        validate_selected_equity_matrix_family_query_evidence_v1,
    )

    validate_selected_equity_matrix_family_query_evidence_v1(
        page_store_path,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=rebuilt_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    validate_selected_equity_matrix_family_candidate_replays_v1(
        page_store_path,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=rebuilt_specs,
        indexed_query_evidence=indexed_query_evidence,
        trials=sweep["trials"],
    )
    specs = list(table_repair_specs)
    spec_fields = {
        "base_page_json_version_id",
        "collateral_cell_ids",
        "collateral_equations",
        "crop_bbox_pixels_xyxy",
        "dash_zero_cell_ids",
        "format_version",
        "section_id",
        "table_id",
    }
    checked_specs = []
    version_ids = []
    for raw in specs:
        spec = _exact_keys(raw, spec_fields, "equity-matrix table repair spec")
        if (
            spec["format_version"] != TABLE_SPEC_FORMAT_VERSION
            or spec["collateral_cell_ids"] != []
            or spec["collateral_equations"] != []
            or type(spec["dash_zero_cell_ids"]) is not list
            or len(spec["dash_zero_cell_ids"]) != len(set(spec["dash_zero_cell_ids"]))
        ):
            raise _error("equity-matrix table repair spec is invalid")
        _node_ordinal(spec["section_id"], "s", "equity-matrix repair section")
        _node_ordinal(spec["table_id"], "t", "equity-matrix repair table")
        for cell_id in spec["dash_zero_cell_ids"]:
            _cell_id(cell_id)
        version_ids.append(
            _prefixed_hash(
                spec["base_page_json_version_id"],
                "gfpstorev1:json:",
                "equity-matrix repair base page version",
            )
        )
        checked_specs.append(canonical_clone_v1(spec))
    if not checked_specs or len(version_ids) != len(set(version_ids)):
        raise _error("equity-matrix repair spec axis is empty or duplicate")
    evidence_axis = load_rollforward_table_page_evidence_v1(
        page_store_path, page_json_version_ids=version_ids
    )
    evidence_by_version = {item["base_page_json_version_id"]: item for item in evidence_axis}
    frontiers = []
    pages = {}
    invalid_reason = re.compile(
        r"^MONEY_CELL_INVALID:(gfpstorev1:json:[0-9a-f]{64}):(r[1-9][0-9]*:c[1-9][0-9]*)$"
    )
    for spec in checked_specs:
        version_id = spec["base_page_json_version_id"]
        evidence = evidence_by_version[version_id]
        page_json = evidence["page_json"]
        _checked_page, table = _table(page_json, spec["section_id"], spec["table_id"])
        matches = []
        for trial in sweep["trials"]:
            for candidate in trial.get("candidates", []):
                regions = [
                    region
                    for region in candidate.get("component_regions", [])
                    if region.get("page_json_version_id") == version_id
                    and region.get("section_id") == spec["section_id"]
                    and region.get("table_id") == spec["table_id"]
                ]
                if regions:
                    matches.append((trial, candidate, regions[0]))
        if len(matches) != 1:
            raise _error("equity-matrix repair spec does not bind one candidate region")
        trial, candidate, region = matches[0]
        binding_without_crop = evidence["source_binding_without_crop"]
        if (
            trial.get("status") != UNRESOLVED
            or candidate.get("status") != UNRESOLVED
            or candidate.get("family_id") != sweep["family_id"]
            or region.get("document_id") != binding_without_crop["document_id"]
            or region.get("physical_page") != binding_without_crop["physical_page"]
            or region.get("source_logical_name") != binding_without_crop["source_logical_name"]
            or region.get("source_sha256") != binding_without_crop["source_sha256"]
        ):
            raise _error("equity-matrix repair candidate/source binding drifted")
        closure = candidate.get("closure_receipt")
        if type(closure) is not dict:
            raise _error("equity-matrix repair candidate closure is absent")
        equations, mismatch_rows, mismatch_columns = _equity_matrix_repair_equations_v1(
            table=table, closure=closure
        )
        invalid_cells = set()
        for reason in candidate.get("reasons", []):
            match = invalid_reason.fullmatch(reason)
            if match is not None:
                if match.group(1) != version_id:
                    raise _error("equity-matrix invalid-cell reason crosses page versions")
                invalid_cells.add(match.group(2))
        if invalid_cells:
            primary_ids = invalid_cells
        else:
            primary_ids = {
                f"{row_axis_id}:{column_axis_id}"
                for row_axis_id in mismatch_rows
                for column_axis_id in mismatch_columns
            }
            if len(primary_ids) != 1:
                raise _error("equity-matrix mismatch graph does not isolate one source cell")
        dash_ids = set(spec["dash_zero_cell_ids"])
        if not dash_ids <= primary_ids:
            raise _error("equity-matrix dash policy lies outside graph-derived target cells")
        allowlist = []
        for cell_id in sorted(primary_ids, key=_cell_id):
            row_index, column_index = _cell_id(cell_id)
            if row_index >= len(table["rows"]) or column_index >= len(table["columns"]):
                raise _error("equity-matrix repair target lies outside the source table")
            allowlist.append(
                {
                    "after_policy": "DASH_ZERO" if cell_id in dash_ids else "SIGNED_INTEGER",
                    "before_exact": table["rows"][row_index]["values_exact"][column_index],
                    "cell_id": cell_id,
                    "change_policy": "MUST_CHANGE",
                    "evidence_kind": "UNRESOLVED_FRONTIER",
                }
            )
        checked_equations = _equations(
            equations,
            row_count=len(table["rows"]),
            column_count=len(table["columns"]),
            allowlist=allowlist,
        )
        source_binding = _source_binding(
            {
                **binding_without_crop,
                "crop_bbox_pixels_xyxy": spec["crop_bbox_pixels_xyxy"],
            }
        )
        frontiers.append(
            {
                "base_page_json_sha256": evidence["base_page_json_sha256"],
                "base_page_json_version_id": version_id,
                "candidate_id": candidate["candidate_id"],
                "candidate_semantic_replay_sha256": canonical_json_sha256_v1(candidate),
                "cell_allowlist": allowlist,
                "compiled_spec_sources_sha256": canonical_json_sha256_v1(compiled_spec_sources),
                "document_ordinal": trial["document_ordinal"],
                "equations": checked_equations,
                "family_id": sweep["family_id"],
                "format_version": UNRESOLVED_FRONTIER_FORMAT_VERSION,
                "indexed_query_evidence_sha256": canonical_json_sha256_v1(indexed_query_evidence),
                "page_evidence_id": evidence["page_evidence_id"],
                "repair_spec_sha256": canonical_json_sha256_v1(spec),
                "selected_page_frontier_sha256": canonical_json_sha256_v1(selected_ids),
                "section_id": spec["section_id"],
                "source_binding": source_binding,
                "sweep_id": sweep["sweep_id"],
                "table_id": spec["table_id"],
                "trigger_reasons": candidate["reasons"],
            }
        )
        pages[version_id] = page_json
    return _build_rollforward_table_cell_repair_plans_v1(
        unresolved_frontier=frontiers,
        page_json_by_version=pages,
    )


def build_accounting_table_cell_repair_plans_v1(
    *,
    compiled_specs: Mapping[str, Any],
    family_sweep: Mapping[str, Any],
    page_store_path: Path,
    selected_page_json_version_ids: Sequence[str],
    table_repair_specs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Dispatch the one minimal observation contract to a typed family graph adapter."""

    if (
        compiled_specs.get("engine_format_version")
        == "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1"
    ):
        return build_equity_matrix_table_cell_repair_plans_v1(
            compiled_specs=compiled_specs,
            family_sweep=family_sweep,
            page_store_path=page_store_path,
            selected_page_json_version_ids=selected_page_json_version_ids,
            table_repair_specs=table_repair_specs,
        )
    return build_rollforward_table_cell_repair_plans_v1(
        compiled_specs=compiled_specs,
        family_sweep=family_sweep,
        page_store_path=page_store_path,
        selected_page_json_version_ids=selected_page_json_version_ids,
        table_repair_specs=table_repair_specs,
    )


def rollforward_table_repair_plan_authority_v1(
    *,
    compiled_spec_sources: Mapping[str, Any],
    family_sweep: Mapping[str, Any],
    selected_page_json_version_ids: Sequence[str],
    table_repair_specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Package the complete replay inputs; the package itself grants no authority."""

    checked_sources = _exact_keys(
        dict(compiled_spec_sources),
        {"evaluation", "schema_binding", "topology"},
        "table repair compiled-spec sources",
    )
    sweep = validate_gemini_json_flat_family_sweep_v1(family_sweep)
    expected_sources = {
        "evaluation": sweep["specs"]["evaluation"]["value"],
        "schema_binding": sweep["specs"]["schema_binding"]["value"],
        "topology": sweep["specs"]["topology"]["value"],
    }
    if not same_typed_json_v1(checked_sources, expected_sources):
        raise _error("table repair compiled-spec sources do not replay the family sweep")
    return {
        "compiled_spec_sources": canonical_clone_v1(checked_sources),
        "family_sweep": canonical_clone_v1(dict(family_sweep)),
        "selected_page_json_version_ids": canonical_clone_v1(list(selected_page_json_version_ids)),
        "table_repair_specs": canonical_clone_v1(list(table_repair_specs)),
    }


def _source_image_binding_axis(plans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for plan in plans:
        binding = plan["source_binding"]
        result.append(
            {
                "image_sha256": binding["image_sha256"],
                "image_size_bytes": binding["image_size_bytes"],
                "media_type": binding["media_type"],
                "physical_page": binding["physical_page"],
                "pixel_height": binding["pixel_height"],
                "pixel_width": binding["pixel_width"],
                "render_dpi": binding["render_dpi"],
                "repair_job_id": plan["repair_job_id"],
                "source_logical_name": binding["source_logical_name"],
                "source_sha256": binding["source_sha256"],
                "source_size_bytes": binding["source_size_bytes"],
            }
        )
    return result


def build_rollforward_table_repair_spec_authority_v1(
    *,
    authority_kind: str,
    authority_ref: str,
    authority_sha256: str,
    source_image_resolver_implementation_path: str,
    source_image_resolver_implementation_sha256: str,
    source_image_resolver_implementation_size_bytes: int,
    source_image_resolver_mupdf_version: str,
    source_image_resolver_pymupdf_version: str,
    table_repair_specs: Sequence[Mapping[str, Any]],
    plans: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind spec/plan axes to an external authority verified by the caller.

    The manifest self-hash detects drift only.  This library cannot authenticate
    ``authority_ref`` or ``authority_sha256``; a production runner must verify and
    pin that external config/evidence artifact before calling any repair boundary.
    """

    if (
        authority_kind not in {"PINNED_CONFIG", "PINNED_EVIDENCE"}
        or type(authority_ref) is not str
        or not authority_ref
        or _hash(authority_sha256, "external repair-spec authority SHA-256") != authority_sha256
        or type(source_image_resolver_implementation_path) is not str
        or not source_image_resolver_implementation_path
        or source_image_resolver_implementation_path.startswith("/")
        or ".." in PurePosixPath(source_image_resolver_implementation_path).parts
        or _hash(
            source_image_resolver_implementation_sha256,
            "source-image resolver implementation SHA-256",
        )
        != source_image_resolver_implementation_sha256
        or type(source_image_resolver_implementation_size_bytes) is not int
        or source_image_resolver_implementation_size_bytes <= 0
        or type(source_image_resolver_mupdf_version) is not str
        or not source_image_resolver_mupdf_version
        or type(source_image_resolver_pymupdf_version) is not str
        or not source_image_resolver_pymupdf_version
        or not table_repair_specs
        or not plans
    ):
        raise _error("external repair-spec authority contract drifted")
    source_image_bindings = _source_image_binding_axis(plans)
    material = {
        "authority": {
            "authority_kind": authority_kind,
            "authority_ref": authority_ref,
            "authority_sha256": authority_sha256,
        },
        "authenticity": canonical_clone_v1(_AUTHENTICITY_BOUNDARY),
        "format_version": REPAIR_SPEC_AUTHORITY_FORMAT_VERSION,
        "plan_axis_sha256": canonical_json_sha256_v1(list(plans)),
        "repair_spec_axis_sha256": canonical_json_sha256_v1(list(table_repair_specs)),
        "source_image_bindings": source_image_bindings,
        "source_image_bindings_sha256": canonical_json_sha256_v1(source_image_bindings),
        "source_image_resolver": {
            "implementation_path": source_image_resolver_implementation_path,
            "implementation_sha256": source_image_resolver_implementation_sha256,
            "implementation_size_bytes": source_image_resolver_implementation_size_bytes,
            "mupdf_version": source_image_resolver_mupdf_version,
            "pymupdf_version": source_image_resolver_pymupdf_version,
        },
    }
    return {**material, "manifest_sha256": canonical_json_sha256_v1(material)}


def _repair_spec_authority(
    value: Any,
    *,
    table_repair_specs: Sequence[Mapping[str, Any]],
    plans: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checked = _exact_keys(
        value,
        _REPAIR_SPEC_AUTHORITY_FIELDS,
        "external repair-spec authority manifest",
    )
    external = _exact_keys(
        checked["authority"],
        _EXTERNAL_AUTHORITY_FIELDS,
        "external repair-spec authority",
    )
    resolver = _exact_keys(
        checked["source_image_resolver"],
        _SOURCE_IMAGE_RESOLVER_FIELDS,
        "source-image resolver implementation authority",
    )
    source_image_bindings = _source_image_binding_axis(plans)
    material = {key: checked[key] for key in checked if key != "manifest_sha256"}
    if (
        checked["format_version"] != REPAIR_SPEC_AUTHORITY_FORMAT_VERSION
        or external["authority_kind"] not in {"PINNED_CONFIG", "PINNED_EVIDENCE"}
        or type(external["authority_ref"]) is not str
        or not external["authority_ref"]
        or _hash(external["authority_sha256"], "external repair-spec authority SHA-256")
        != external["authority_sha256"]
        or checked["authenticity"] != _AUTHENTICITY_BOUNDARY
        or type(resolver["implementation_path"]) is not str
        or not resolver["implementation_path"]
        or resolver["implementation_path"].startswith("/")
        or ".." in PurePosixPath(resolver["implementation_path"]).parts
        or _hash(
            resolver["implementation_sha256"],
            "source-image resolver implementation SHA-256",
        )
        != resolver["implementation_sha256"]
        or type(resolver["implementation_size_bytes"]) is not int
        or resolver["implementation_size_bytes"] <= 0
        or type(resolver["mupdf_version"]) is not str
        or not resolver["mupdf_version"]
        or type(resolver["pymupdf_version"]) is not str
        or not resolver["pymupdf_version"]
        or checked["repair_spec_axis_sha256"] != canonical_json_sha256_v1(list(table_repair_specs))
        or checked["plan_axis_sha256"] != canonical_json_sha256_v1(list(plans))
        or checked["source_image_bindings"] != source_image_bindings
        or checked["source_image_bindings_sha256"]
        != canonical_json_sha256_v1(source_image_bindings)
        or checked["manifest_sha256"] != canonical_json_sha256_v1(material)
    ):
        raise _error("external repair-spec authority does not bind exact spec/plan axes")
    return canonical_clone_v1(checked)


def _authoritative_plan_axis(
    authority: Mapping[str, Any],
    *,
    repair_spec_authority: Mapping[str, Any],
    page_store_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rebuild the queue from the public DB/query/candidate replay at every boundary."""

    checked = _exact_keys(dict(authority), _AUTHORITY_FIELDS, "table repair plan authority")
    sources = _exact_keys(
        checked["compiled_spec_sources"],
        {"evaluation", "schema_binding", "topology"},
        "table repair compiled-spec sources",
    )
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(checked["family_sweep"])
    sweep_sources = {
        "evaluation": checked_sweep["specs"]["evaluation"]["value"],
        "schema_binding": checked_sweep["specs"]["schema_binding"]["value"],
        "topology": checked_sweep["specs"]["topology"]["value"],
    }
    if not same_typed_json_v1(sources, sweep_sources):
        raise _error("table repair compiled-spec sources drifted from the family sweep")
    compiled_specs = compile_gemini_json_flat_family_specs_v1(
        sources["topology"],
        sources["evaluation"],
        sources["schema_binding"],
    )
    plans = build_accounting_table_cell_repair_plans_v1(
        compiled_specs=compiled_specs,
        family_sweep=checked_sweep,
        page_store_path=page_store_path,
        selected_page_json_version_ids=checked["selected_page_json_version_ids"],
        table_repair_specs=checked["table_repair_specs"],
    )
    external = _repair_spec_authority(
        repair_spec_authority,
        table_repair_specs=checked["table_repair_specs"],
        plans=plans,
    )
    return plans, external


def _authoritative_plan(
    plan: Mapping[str, Any],
    *,
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
    page_store_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    checked = _validated_plan(plan)
    plans, external = _authoritative_plan_axis(
        authority,
        repair_spec_authority=repair_spec_authority,
        page_store_path=page_store_path,
    )
    matches = [candidate for candidate in plans if same_typed_json_v1(candidate, checked)]
    if len(matches) != 1:
        raise _error("table repair plan is not the exact authoritative replay")
    return matches[0], external


def _pinned_source_image_renderer_v1(
    workspace_root: Path, *, resolver: Mapping[str, Any]
) -> tuple[Any, dict[str, Any]]:
    checked = _exact_keys(
        dict(resolver),
        _SOURCE_IMAGE_RESOLVER_FIELDS,
        "source-image resolver implementation authority",
    )
    root_input = Path(workspace_root)
    root = root_input.resolve()
    if root_input.is_symlink() or not root.is_dir():
        raise _error("roll-forward source-image workspace root is not trusted or present")
    relative = PurePosixPath(checked["implementation_path"])
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or _hash(
            checked["implementation_sha256"],
            "source-image resolver implementation SHA-256",
        )
        != checked["implementation_sha256"]
        or type(checked["implementation_size_bytes"]) is not int
        or checked["implementation_size_bytes"] <= 0
    ):
        raise _error("roll-forward source-image resolver implementation pin is invalid")
    pinned_path = root.joinpath(*relative.parts).resolve()
    if (
        not pinned_path.is_relative_to(root)
        or pinned_path.is_symlink()
        or not pinned_path.is_file()
    ):
        raise _error("roll-forward source-image resolver implementation is absent")
    from bctc_ai.evaluation import gemini_json_first_page_render_v1 as renderer_module

    module_file = getattr(renderer_module, "__file__", None)
    if type(module_file) is not str or Path(module_file).resolve() != pinned_path:
        raise _error("roll-forward source-image executed module differs from the pinned file")
    executed_bytes = pinned_path.read_bytes()
    if (
        sha256(executed_bytes).hexdigest() != checked["implementation_sha256"]
        or len(executed_bytes) != checked["implementation_size_bytes"]
    ):
        raise _error("roll-forward source-image executed implementation pin drifted")
    import fitz

    if (
        getattr(fitz, "__version__", None) != checked["pymupdf_version"]
        or getattr(fitz, "mupdf_version", None) != checked["mupdf_version"]
    ):
        raise _error("roll-forward source-image PyMuPDF or MuPDF runtime pin drifted")
    return renderer_module, canonical_clone_v1(checked)


def validate_rollforward_source_image_resolver_implementation_v1(
    workspace_root: Path, *, resolver: Mapping[str, Any]
) -> dict[str, Any]:
    """Verify that the manifest-pinned file is the module Python will execute."""

    _module, checked = _pinned_source_image_renderer_v1(workspace_root, resolver=resolver)
    return checked


def resolve_rollforward_table_source_image_v1(
    workspace_root: Path,
    *,
    plan: Mapping[str, Any],
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
    page_store_path: Path,
) -> tuple[bytes, dict[str, Any]]:
    """Render the exact source PDF page declared by one authenticated plan.

    The caller remains responsible for authenticating ``workspace_root`` and the
    externally pinned resolver/config authority.  This function verifies their
    bytes against the manifest before rendering and exact-compares the PNG to the
    frozen page-store binding.
    """

    checked_plan, checked_external = _authoritative_plan(
        plan,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
        page_store_path=page_store_path,
    )
    root_input = Path(workspace_root)
    root = root_input.resolve()
    if root_input.is_symlink() or not root.is_dir():
        raise _error("roll-forward source-image workspace root is not trusted or present")
    logical_name = checked_plan["source_binding"]["source_logical_name"]
    logical = PurePosixPath(logical_name)
    if logical.is_absolute() or not logical.parts or ".." in logical.parts:
        raise _error("roll-forward source-image logical path is invalid")
    source_path = root.joinpath(*logical.parts).resolve()
    if (
        not source_path.is_relative_to(root)
        or source_path.is_symlink()
        or not source_path.is_file()
    ):
        raise _error("roll-forward source PDF is absent or crosses the workspace root")
    renderer_module, resolver = _pinned_source_image_renderer_v1(
        root,
        resolver=checked_external["source_image_resolver"],
    )
    source_bytes = source_path.read_bytes()
    binding = checked_plan["source_binding"]
    if (
        sha256(source_bytes).hexdigest() != binding["source_sha256"]
        or len(source_bytes) != binding["source_size_bytes"]
    ):
        raise _error("roll-forward source PDF bytes do not bind the page store")
    try:
        import fitz

        with fitz.open(stream=source_bytes, filetype="pdf") as document:
            if binding["physical_page"] > document.page_count:
                raise _error("roll-forward source PDF physical page is absent")
            rendered = renderer_module.render_full_pdf_page_v1(
                document[binding["physical_page"] - 1],
                physical_page=binding["physical_page"],
                dpi=binding["render_dpi"],
                source_sha256=binding["source_sha256"],
            )
    except GeminiJsonRollforwardTableRepairV1Error:
        raise
    except Exception as exc:
        raise _error("roll-forward source PDF page cannot be rendered") from exc
    expected_page = {
        "physical_page": binding["physical_page"],
        "image_sha256": binding["image_sha256"],
        "image_size_bytes": binding["image_size_bytes"],
        "pixel_width": binding["pixel_width"],
        "pixel_height": binding["pixel_height"],
        "render_dpi": binding["render_dpi"],
        "media_type": binding["media_type"],
    }
    if (
        rendered.page != expected_page
        or sha256(rendered.image).hexdigest() != binding["image_sha256"]
    ):
        raise _error("roll-forward rendered source image does not bind the frozen page")
    material = {
        "format_version": SOURCE_IMAGE_RESOLUTION_FORMAT_VERSION,
        "render_receipt": rendered.receipt,
        "render_receipt_sha256": canonical_json_sha256_v1(rendered.receipt),
        "repair_job_id": checked_plan["repair_job_id"],
        "repair_spec_authority_manifest_sha256": checked_external["manifest_sha256"],
        "resolver_implementation": canonical_clone_v1(resolver),
        "source_artifact_ref": {
            "path": logical.as_posix(),
            "sha256": binding["source_sha256"],
            "size_bytes": binding["source_size_bytes"],
        },
        "source_image": canonical_clone_v1(expected_page),
    }
    return rendered.image, {
        **material,
        "resolution_receipt_id": "gjfrsirv1:resolution:" + canonical_json_sha256_v1(material),
    }


def _validated_plan(plan: Any) -> dict[str, Any]:
    if (
        type(plan) is not dict
        or set(plan) != _PLAN_FIELDS
        or plan.get("format_version") != QUEUE_FORMAT_VERSION
        or plan.get("repair_contract_version") != REPAIR_CONTRACT_VERSION
        or plan.get("repair_scope") != REPAIR_SCOPE
        or type(plan.get("repair_job_id")) is not str
    ):
        raise _error("roll-forward table repair plan is invalid")
    material = {key: plan[key] for key in plan if key != "repair_job_id"}
    if plan["repair_job_id"] != "gjfrrqv1:job:" + canonical_json_sha256_v1(material):
        raise _error("roll-forward table repair plan identity does not replay")
    _hash(plan.get("base_page_json_sha256"), "table repair base page SHA-256")
    _prefixed_hash(
        plan.get("base_page_json_version_id"),
        "gfpstorev1:json:",
        "table repair base version",
    )
    if (
        type(plan.get("candidate_id")) is not str
        or _FAMILY_CANDIDATE_ID.fullmatch(plan["candidate_id"]) is None
    ):
        raise _error("table repair candidate identity is invalid")
    _prefixed_hash(plan.get("sweep_id"), "gjfafsv1:sweep:", "table repair sweep")
    _prefixed_hash(
        plan.get("page_evidence_id"),
        "gjfrpev1:evidence:",
        "table repair page evidence",
    )
    _hash(plan.get("repair_spec_sha256"), "table repair spec SHA-256")
    _hash(
        plan.get("candidate_semantic_replay_sha256"),
        "table repair semantic candidate SHA-256",
    )
    _hash(
        plan.get("compiled_spec_sources_sha256"),
        "table repair compiled-spec sources SHA-256",
    )
    _hash(
        plan.get("indexed_query_evidence_sha256"),
        "table repair indexed query evidence SHA-256",
    )
    _hash(
        plan.get("selected_page_frontier_sha256"),
        "table repair selected page frontier SHA-256",
    )
    binding = _source_binding(plan.get("source_binding"))
    if (
        plan.get("source_logical_name") != binding["source_logical_name"]
        or plan.get("source_sha256") != binding["source_sha256"]
        or plan.get("physical_page") != binding["physical_page"]
        or type(plan.get("family_id")) is not str
        or not plan["family_id"]
        or type(plan.get("document_ordinal")) is not int
        or plan["document_ordinal"] <= 0
        or plan.get("acceptance_policy")
        != {
            "all_other_cells_byte_equal": True,
            "forbid_arithmetic_backsolve": True,
            "ignore_non_authoritative_observations": True,
            "preserve_omitted_may_change_cells": True,
            "require_must_change_and_collateral_observations": True,
            "require_all_declared_equations_exact": True,
            "require_immutable_shape_period_and_unit": True,
        }
        or plan.get("repair_policy")
        != {
            "attempt_lineage": "SIBLINGS_FROM_IMMUTABLE_BASE",
            "initial_thinking_level": "low",
            "max_attempts": 3,
            "thinking_escalation": ["medium", "high"],
        }
    ):
        raise _error("roll-forward table repair plan policy or source axis drifted")
    section_id = plan.get("section_id")
    table_id = plan.get("table_id")
    _node_ordinal(section_id, "s", "table repair plan section")
    _node_ordinal(table_id, "t", "table repair plan table")
    table_ref = {"section_id": section_id, "table_id": table_id}
    if plan.get("component_table_refs") != [table_ref] or plan.get("target_table_refs") != [
        table_ref
    ]:
        raise _error("roll-forward table repair table reference axis drifted")
    shape = _exact_keys(
        plan.get("shape_gate"),
        {
            "base_table_sha256",
            "column_count",
            "columns_exact",
            "continuation_exact",
            "row_axis_exact",
            "row_count",
            "table_title_exact",
            "unit_exact",
        },
        "table repair shape gate",
    )
    _hash(shape["base_table_sha256"], "table repair base table SHA-256")
    if (
        type(shape["column_count"]) is not int
        or shape["column_count"] <= 0
        or type(shape["row_count"]) is not int
        or shape["row_count"] <= 0
        or type(shape["columns_exact"]) is not list
        or len(shape["columns_exact"]) != shape["column_count"]
        or type(shape["row_axis_exact"]) is not list
        or len(shape["row_axis_exact"]) != shape["row_count"]
        or any(column.get("value_kind") != "MONEY" for column in shape["columns_exact"])
    ):
        raise _error("table repair shape gate is invalid")
    raw_allowlist = plan.get("cell_allowlist")
    if type(raw_allowlist) is not list or not raw_allowlist:
        raise _error("table repair plan allowlist is invalid")
    allowlist = []
    for item in raw_allowlist:
        checked_item = _exact_keys(
            item,
            {
                "after_policy",
                "before_exact",
                "cell_id",
                "change_policy",
                "evidence_kind",
            },
            "table repair plan allowlist item",
        )
        row, column = _cell_id(checked_item["cell_id"])
        if (
            row >= shape["row_count"]
            or column >= shape["column_count"]
            or checked_item["after_policy"] not in _AFTER_POLICIES
            or checked_item["change_policy"] not in _CHANGE_POLICIES
            or checked_item["evidence_kind"] not in _EVIDENCE_KINDS
        ):
            raise _error("table repair plan allowlist item is invalid")
        allowlist.append(checked_item)
    if (
        raw_allowlist != sorted(raw_allowlist, key=lambda item: _cell_id(item["cell_id"]))
        or len({item["cell_id"] for item in allowlist}) != len(allowlist)
        or not any(item["evidence_kind"] == "UNRESOLVED_FRONTIER" for item in allowlist)
        or plan.get("target_ids")
        != [f"{section_id}:{table_id}:{item['cell_id']}" for item in allowlist]
    ):
        raise _error("table repair plan allowlist or target axis drifted")
    equations = _equations(
        plan.get("equation_inventory"),
        row_count=shape["row_count"],
        column_count=shape["column_count"],
        allowlist=allowlist,
    )
    if equations != plan["equation_inventory"] or canonical_json_sha256_v1(equations) != plan.get(
        "equation_inventory_sha256"
    ):
        raise _error("table repair plan equation inventory drifted")
    request = _exact_keys(
        plan.get("request_contract"),
        {
            "output_contract_mode",
            "prompt_sha256",
            "prompt_variant",
            "response_schema_sha256",
        },
        "table repair request contract",
    )
    if (
        request["output_contract_mode"] != "JSON_SCHEMA"
        or request["prompt_variant"] != "rollforward-table-cells"
        or _hash(request["prompt_sha256"], "table repair prompt SHA-256")
        != request["prompt_sha256"]
        or request["response_schema_sha256"]
        != canonical_json_sha256_v1(rollforward_table_repair_response_schema_v1())
        or plan.get("trigger_kinds") != ["ROLLFORWARD_TYPED_CELL_EVIDENCE_INCOMPLETE"]
        or type(plan.get("trigger_reasons")) is not list
        or not plan["trigger_reasons"]
        or plan["trigger_reasons"] != sorted(set(plan["trigger_reasons"]))
    ):
        raise _error("table repair request or trigger contract drifted")
    return canonical_clone_v1(plan)


def rollforward_table_repair_target_v1(
    page_json: Any, *, plan: Mapping[str, Any]
) -> dict[str, Any]:
    """Return response-blind labels plus the exact cells the model may observe."""

    checked_plan = _validated_plan(plan)
    checked_page, table = _table(page_json, checked_plan["section_id"], checked_plan["table_id"])
    if (
        canonical_json_sha256_v1(checked_page) != checked_plan["base_page_json_sha256"]
        or _shape_gate(table) != checked_plan["shape_gate"]
    ):
        raise _error("roll-forward table repair plan does not bind the base table")
    target_cells = []
    for allowed in checked_plan["cell_allowlist"]:
        row_index, column_index = _cell_id(allowed["cell_id"])
        target_cells.append(
            {
                "after_policy": allowed["after_policy"],
                "cell_id": allowed["cell_id"],
                "change_policy": allowed["change_policy"],
                "column_header_exact": canonical_clone_v1(
                    table["columns"][column_index]["header_path_exact"]
                ),
                "evidence_kind": allowed["evidence_kind"],
                "row_label_exact": table["rows"][row_index]["label_exact"],
            }
        )
    return {
        "column_headers_exact": [
            canonical_clone_v1(column["header_path_exact"]) for column in table["columns"]
        ],
        "column_value_kinds": [column["value_kind"] for column in table["columns"]],
        "row_labels_exact": [row["label_exact"] for row in table["rows"]],
        "target_cells": target_cells,
        "target_id": f"{checked_plan['section_id']}:{checked_plan['table_id']}",
        "table_title_exact": table["title_exact"],
        "unit_exact": table["unit_exact"],
    }


def build_rollforward_table_repair_prompt_v1(
    *, base_page_json_version_id: str, target: Mapping[str, Any]
) -> str:
    """Build one concise prompt; prior cell values are intentionally excluded."""

    _prefixed_hash(
        base_page_json_version_id,
        "gfpstorev1:json:",
        "roll-forward table repair base version",
    )
    required = {
        "column_headers_exact",
        "column_value_kinds",
        "row_labels_exact",
        "table_title_exact",
        "target_cells",
        "target_id",
        "unit_exact",
    }
    checked = _exact_keys(dict(target), required, "roll-forward table repair target")
    context = {
        "table_title_exact": checked["table_title_exact"],
        "target_cells": [
            {
                "cell_id": item["cell_id"],
                "column_header_exact": item["column_header_exact"],
                "row_label_exact": item["row_label_exact"],
            }
            for item in checked["target_cells"]
        ],
        "unit_exact": checked["unit_exact"],
    }
    return (
        "Ảnh chứa một bảng tài chính. Chỉ đọc các ô được liệt kê trong target_cells. "
        "Với mỗi ô nhìn thấy rõ, trả một phần tử {cell_id, source_text}; giữ source_text "
        "đúng như ảnh, gồm ngoặc, dấu âm hoặc dấu gạch kế toán. Dùng null chỉ khi ô thật sự "
        "trống. Không chép lại tiêu đề, đơn vị, nhãn dòng, toàn bảng hay ô ngoài danh sách; "
        "không tính toán hoặc suy ra giá trị. Trả duy nhất JSON theo schema.\n"
        f"base_page_json_version_id={base_page_json_version_id}\n"
        "target_table_context=" + canonical_json_bytes_v1(context).decode("utf-8")
    )


def rollforward_table_repair_response_schema_v1() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "observations": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "cell_id": {"type": "string"},
                        "source_text": {"type": ["string", "null"]},
                    },
                    "required": ["cell_id", "source_text"],
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["observations"],
        "type": "object",
    }


def decode_rollforward_table_repair_text_v1(
    text: str, *, target: Mapping[str, Any]
) -> dict[str, Any]:
    """Project one tolerant response onto the immutable authoritative target-cell axis."""

    if type(text) is not str:
        raise _error("roll-forward table repair response is not text")
    match = _FENCE.fullmatch(text.strip())
    payload = match.group(1) if match is not None else text
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise _error("roll-forward table repair response is not JSON") from exc
    if type(value) is not dict:
        raise _error("roll-forward table repair response is not one JSON object")
    required_target = {
        "column_headers_exact",
        "column_value_kinds",
        "row_labels_exact",
        "table_title_exact",
        "target_cells",
        "target_id",
        "unit_exact",
    }
    checked_target = _exact_keys(dict(target), required_target, "roll-forward table repair target")
    target_ids = []
    for item in checked_target["target_cells"]:
        if type(item) is not dict or type(item.get("cell_id")) is not str:
            raise _error("roll-forward table repair target-cell axis is invalid")
        canonical = _canonical_cell_id(item["cell_id"])
        if canonical != item["cell_id"] or canonical in target_ids:
            raise _error("roll-forward table repair target-cell axis is invalid")
        target_ids.append(canonical)
    target_id_set = set(target_ids)
    if value.get("all_cells_transcribed") is False:
        raise _error("roll-forward response declares incomplete target evidence")
    for uncertainty_field in ("uncertainty_exact", "uncertain_refs"):
        uncertainty = value.get(uncertainty_field)
        if uncertainty in (None, []):
            continue
        uncertainty_text = canonical_json_bytes_v1(uncertainty).decode("utf-8")
        uncertain_cell_ids = {
            f"r{int(match.group(1))}:c{int(match.group(2))}"
            for match in _CELL_REFERENCE.finditer(unicodedata.normalize("NFKC", uncertainty_text))
        }
        if not uncertain_cell_ids:
            raise _error("roll-forward response declares unscoped incomplete evidence")
        if target_id_set & uncertain_cell_ids:
            raise _error("roll-forward response declares uncertainty for a target cell")

    # Idempotent canonical projections are used internally by merge/attempt replay.
    if set(value) == {
        "format_version",
        "observations",
        "projection_diagnostics",
        "projection_sha256",
        "source_response",
    }:
        source_response = value["source_response"]
        if type(source_response) is not dict or set(source_response) == set(value):
            raise _error("roll-forward target-observation projection identity drifted")
        replayed = decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(source_response).decode("utf-8"),
            target=checked_target,
        )
        if not same_typed_json_v1(replayed, value):
            raise _error("roll-forward target-observation projection identity drifted")
        return replayed

    ignored_top_level_fields = []
    if type(value.get("observations")) is list:
        input_contract = "TARGET_OBSERVATIONS_V1"
        raw_observations = value["observations"]
        ignored_top_level_fields = sorted(key for key in value if key != "observations")
    elif type(value.get("rows")) is list:
        input_contract = "LEGACY_FULL_TABLE_V1"
        raw_observations = []
        ignored_top_level_fields = sorted(key for key in value if key != "rows")
        legacy_uncertainty = value.get("uncertainty_exact")
        legacy_uncertainty_refs = (
            set()
            if legacy_uncertainty in (None, [])
            else {
                f"r{int(match.group(1))}:c{int(match.group(2))}"
                for match in _CELL_REFERENCE.finditer(
                    unicodedata.normalize(
                        "NFKC", canonical_json_bytes_v1(legacy_uncertainty).decode("utf-8")
                    )
                )
            }
        )
        if value.get("all_cells_transcribed") is False or (
            legacy_uncertainty not in (None, []) and not legacy_uncertainty_refs
        ):
            raise _error("roll-forward legacy response declares incomplete target evidence")
        expected_row_count = len(checked_target["row_labels_exact"])
        expected_column_count = len(checked_target["column_headers_exact"])
        columns = value.get("columns")
        if (
            ("target_id" in value and value["target_id"] != checked_target["target_id"])
            or len(value["rows"]) != expected_row_count
            or type(columns) is not list
            or len(columns) != expected_column_count
            or any(
                type(row) is not dict
                or type(row.get("cells")) is not list
                or len(row["cells"]) != expected_column_count
                for row in value["rows"]
            )
        ):
            raise _error("roll-forward legacy full-table shape or target identity drifted")
        for cell_id in target_ids:
            row_index, column_index = _cell_id(cell_id)
            row = value["rows"][row_index]
            column = columns[column_index]
            if (
                _normalized_anchor(row.get("label_exact"))
                != _normalized_anchor(checked_target["row_labels_exact"][row_index])
                or type(column) is not dict
                or type(column.get("header_path_exact")) is not list
                or _normalized_header_anchor(
                    column["header_path_exact"], unit_exact=checked_target["unit_exact"]
                )
                != _normalized_header_anchor(
                    checked_target["column_headers_exact"][column_index],
                    unit_exact=checked_target["unit_exact"],
                )
            ):
                raise _error("roll-forward legacy target row/column anchors drifted")
        for row_ordinal, row in enumerate(value["rows"], start=1):
            for column_ordinal, cell in enumerate(row["cells"], start=1):
                if type(cell) is not dict:
                    raw_observations.append(
                        {
                            "cell_id": f"r{row_ordinal}:c{column_ordinal}",
                            "source_text": cell,
                        }
                    )
                    continue
                raw_observations.append(
                    {
                        "cell_id": f"r{row_ordinal}:c{column_ordinal}",
                        **({"source_text": cell["source_text"]} if "source_text" in cell else {}),
                        **(
                            {"visual_state": cell["visual_state"]} if "visual_state" in cell else {}
                        ),
                    }
                )
    else:
        raise _error("roll-forward table repair response has no observations")

    authoritative: dict[str, dict[str, Any]] = {}
    authoritative_raw_hashes: dict[str, str] = {}
    corroborated = 0
    corroborated_observations = []
    ignored = []
    normalized = []
    for raw in raw_observations:
        raw_hash = canonical_json_sha256_v1(raw)
        raw_cell_id = raw.get("cell_id") if type(raw) is dict else None
        cell_id = _canonical_cell_id(raw_cell_id)
        if cell_id not in target_id_set:
            ignored.append(
                {
                    "cell_id_exact": raw_cell_id if type(raw_cell_id) is str else None,
                    "observation_sha256": raw_hash,
                }
            )
            continue
        if type(raw) is not dict or "source_text" not in raw:
            raise _error("roll-forward target observation omits source_text")
        source_text, visual_state, normalization = _normalized_observed_source_text(
            raw["source_text"],
            declared_visual_state=raw.get("visual_state"),
        )
        if normalization is not None:
            normalized.append(
                {
                    "cell_id": cell_id,
                    "normalization_kind": normalization,
                    "observation_sha256": raw_hash,
                }
            )
        observation = {
            "cell_id": cell_id,
            "source_text": source_text,
            "visual_state": visual_state,
        }
        prior = authoritative.get(cell_id)
        if prior is not None:
            if _cell_semantic(prior["source_text"], prior["visual_state"]) != _cell_semantic(
                observation["source_text"], observation["visual_state"]
            ):
                raise _error("roll-forward target observations conflict for one cell")
            prior_hash = authoritative_raw_hashes[cell_id]
            chosen = min(
                (prior, observation),
                key=lambda item: canonical_json_bytes_v1(item),
            )
            chosen_hash = raw_hash if chosen is observation else prior_hash
            authoritative[cell_id] = chosen
            authoritative_raw_hashes[cell_id] = chosen_hash
            corroborated_observations.append(
                {
                    "cell_id": cell_id,
                    "chosen_observation_sha256": chosen_hash,
                    "observation_sha256_axis": sorted([prior_hash, raw_hash]),
                    "semantic_equivalence": {
                        "signed_integer": _signed_integer(observation["source_text"]),
                        "visual_state": observation["visual_state"],
                    },
                }
            )
            corroborated += 1
            continue
        authoritative[cell_id] = observation
        authoritative_raw_hashes[cell_id] = raw_hash
    observations = sorted(authoritative.values(), key=lambda item: _cell_id(item["cell_id"]))
    diagnostics = {
        "corroborated_duplicate_count": corroborated,
        "corroborated_observations": corroborated_observations,
        "ignored_observation_count": len(ignored),
        "ignored_observations": ignored,
        "ignored_top_level_fields": ignored_top_level_fields,
        "input_contract": input_contract,
        "normalized_observation_count": len(normalized),
        "normalized_observations": normalized,
        "raw_response_sha256": canonical_json_sha256_v1(value),
        "target_axis_sha256": canonical_json_sha256_v1(checked_target["target_cells"]),
    }
    material = {
        "format_version": TARGET_OBSERVATION_FORMAT_VERSION,
        "observations": observations,
        "projection_diagnostics": diagnostics,
        "source_response": canonical_clone_v1(value),
    }
    return {**material, "projection_sha256": canonical_json_sha256_v1(material)}


def _matrix_rank(rows: Sequence[Sequence[int]]) -> int:
    matrix = [[Fraction(value) for value in row] for row in rows]
    if not matrix:
        return 0
    row_count = len(matrix)
    column_count = len(matrix[0])
    rank = 0
    for column in range(column_count):
        pivot = next((index for index in range(rank, row_count) if matrix[index][column]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        scale = matrix[rank][column]
        matrix[rank] = [value / scale for value in matrix[rank]]
        for index in range(row_count):
            if index == rank or not matrix[index][column]:
                continue
            factor = matrix[index][column]
            matrix[index] = [
                value - factor * pivot_value
                for value, pivot_value in zip(matrix[index], matrix[rank], strict=True)
            ]
        rank += 1
        if rank == row_count:
            break
    return rank


def _equation_gate(
    table: Mapping[str, Any],
    *,
    equations: Sequence[Mapping[str, Any]],
    allowlist: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    allow_ids = [item["cell_id"] for item in allowlist]
    matrix = []
    receipts = []
    for equation in equations:
        result_row, result_column = _cell_id(equation["result_cell_id"])
        result = _signed_integer(table["rows"][result_row]["values_exact"][result_column])
        terms = []
        for term in equation["terms"]:
            row_index, column_index = _cell_id(term["cell_id"])
            coefficient = _signed_integer(table["rows"][row_index]["values_exact"][column_index])
            terms.append((term["multiplier"], coefficient))
        if result is None or any(coefficient is None for _, coefficient in terms):
            raise _error("roll-forward table repair equation contains an unknown cell")
        expected = sum(
            multiplier * coefficient for multiplier, coefficient in terms if coefficient is not None
        )
        if result != expected:
            raise _error("roll-forward table repair equation does not close")
        row = []
        for cell_id in allow_ids:
            value = 1 if equation["result_cell_id"] == cell_id else 0
            value -= sum(
                term["multiplier"] for term in equation["terms"] if term["cell_id"] == cell_id
            )
            row.append(value)
        matrix.append(row)
        receipts.append(
            {
                "equation_id": equation["equation_id"],
                "expected_result": expected,
                "observed_result": result,
                "status": "EXACT",
            }
        )
    return {
        "allowlist_equation_rank": _matrix_rank(matrix),
        "allowlisted_cell_count": len(allow_ids),
        "closed_equation_count": len(receipts),
        "equation_receipts": receipts,
        "forbid_arithmetic_backsolve": True,
    }


def _after_policy(cell: Mapping[str, Any], policy: str) -> None:
    coefficient = _signed_integer(cell["source_text"])
    if policy == "DASH_ZERO":
        if cell["visual_state"] != "DASH" or coefficient != 0:
            raise _error("roll-forward table repair expected one source-transcribed dash zero")
        return
    if policy == "SIGNED_INTEGER":
        if cell["visual_state"] == "BLANK" or coefficient is None:
            raise _error("roll-forward table repair expected one source-transcribed integer")
        return
    raise _error("roll-forward table repair after policy drifted")


def merge_rollforward_table_repair_v1(
    page_json: Any,
    *,
    plan: Mapping[str, Any],
    repair: Mapping[str, Any],
    page_store_path: Path,
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Atomically merge only allowlisted cells after every table/equation gate."""

    checked_plan, checked_spec_authority = _authoritative_plan(
        plan,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
        page_store_path=page_store_path,
    )
    page_evidence = validate_rollforward_table_repair_plan_page_store_v1(
        checked_plan, page_store_path=page_store_path
    )
    checked_page, table = _table(page_json, checked_plan["section_id"], checked_plan["table_id"])
    if (
        checked_page != page_evidence["page_json"]
        or canonical_json_sha256_v1(checked_page) != checked_plan["base_page_json_sha256"]
        or _shape_gate(table) != checked_plan["shape_gate"]
    ):
        raise _error("roll-forward table repair base page or table drifted")
    target = rollforward_table_repair_target_v1(checked_page, plan=checked_plan)
    decoded = decode_rollforward_table_repair_text_v1(
        canonical_json_bytes_v1(dict(repair)).decode("utf-8"), target=target
    )
    allow_by_id = {item["cell_id"]: item for item in checked_plan["cell_allowlist"]}
    observed_by_id = {item["cell_id"]: item for item in decoded["observations"]}
    required_ids = {
        item["cell_id"]
        for item in checked_plan["cell_allowlist"]
        if item["change_policy"] == "MUST_CHANGE"
        or item["evidence_kind"] == "ATOMIC_TABLE_COLLATERAL"
    }
    missing_required = sorted(required_ids - set(observed_by_id), key=_cell_id)
    if missing_required:
        raise _error("roll-forward target observations omit a required repair or collateral cell")
    merged = canonical_clone_v1(checked_page)
    merged_table = merged["sections"][_node_ordinal(checked_plan["section_id"], "s", "section")][
        "tables"
    ][_node_ordinal(checked_plan["table_id"], "t", "table")]
    changes = []
    for cell_id, response_cell in observed_by_id.items():
        allowed = allow_by_id[cell_id]
        row_index, column_index = _cell_id(cell_id)
        before = table["rows"][row_index]["values_exact"][column_index]
        _after_policy(response_cell, allowed["after_policy"])
        before_semantic = _cell_semantic(before)
        after_semantic = _cell_semantic(response_cell["source_text"], response_cell["visual_state"])
        if after_semantic == before_semantic:
            if allowed["change_policy"] == "MUST_CHANGE":
                raise _error(
                    "roll-forward table repair left a must-change cell semantically unchanged"
                )
            continue
        merged_table["rows"][row_index]["values_exact"][column_index] = response_cell["source_text"]
        changes.append(
            {
                "after_exact": response_cell["source_text"],
                "after_policy": allowed["after_policy"],
                "after_visual_state": response_cell["visual_state"],
                "before_exact": before,
                "before_visual_state": _visual_state(before),
                "cell_id": cell_id,
                "change_policy": allowed["change_policy"],
                "evidence_kind": allowed["evidence_kind"],
                "semantic_delta": {
                    "after": {
                        "signed_integer": after_semantic[1],
                        "visual_state": after_semantic[0],
                    },
                    "before": {
                        "signed_integer": before_semantic[1],
                        "visual_state": before_semantic[0],
                    },
                },
            }
        )
    changed_ids = {item["cell_id"] for item in changes}
    must_change_ids = {
        item["cell_id"]
        for item in checked_plan["cell_allowlist"]
        if item["change_policy"] == "MUST_CHANGE"
    }
    if not changes or not must_change_ids <= changed_ids:
        raise _error("roll-forward table repair did not satisfy its change policy")
    merged = validate_financial_page_json_v1(merged)
    merged_table = merged["sections"][_node_ordinal(checked_plan["section_id"], "s", "section")][
        "tables"
    ][_node_ordinal(checked_plan["table_id"], "t", "table")]
    gate = _equation_gate(
        merged_table,
        equations=checked_plan["equation_inventory"],
        allowlist=checked_plan["cell_allowlist"],
    )
    change = {
        "all_other_cells_byte_equal": True,
        "base_table_sha256": checked_plan["shape_gate"]["base_table_sha256"],
        "cell_changes": sorted(changes, key=lambda item: _cell_id(item["cell_id"])),
        "changed_cell_count": len(changes),
        "equation_gate": gate,
        "equation_inventory_sha256": checked_plan["equation_inventory_sha256"],
        "merged_table_sha256": canonical_json_sha256_v1(merged_table),
        "repair_scope": REPAIR_SCOPE,
        "repair_spec_authority_manifest_sha256": checked_spec_authority["manifest_sha256"],
        "response_projection": canonical_clone_v1(decoded["projection_diagnostics"]),
        "shape_gate": canonical_clone_v1(checked_plan["shape_gate"]),
        "source_binding": canonical_clone_v1(checked_plan["source_binding"]),
        "target_id": f"{checked_plan['section_id']}:{checked_plan['table_id']}",
        "validated_allowlist_cell_count": len(checked_plan["cell_allowlist"]),
    }
    receipt_material = {
        "base_page_json_sha256": canonical_json_sha256_v1(checked_page),
        "base_page_json_version_id": checked_plan["base_page_json_version_id"],
        "changes": [change],
        "format_version": "GEMINI_JSON_REGION_REPAIR_V1",
        "merged_page_json_sha256": canonical_json_sha256_v1(merged),
        "repair_response_sha256": canonical_json_sha256_v1(decoded),
    }
    return merged, {
        **receipt_material,
        "repair_id": "gjfrrv1:repair:" + canonical_json_sha256_v1(receipt_material),
    }


def crop_rollforward_table_image_v1(
    image_bytes: bytes,
    *,
    plan: Mapping[str, Any],
    page_store_path: Path,
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """Crop one immutable image by its receipt-bound, declarative table box."""

    checked_plan, checked_spec_authority = _authoritative_plan(
        plan,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
        page_store_path=page_store_path,
    )
    validate_rollforward_table_repair_plan_page_store_v1(
        checked_plan, page_store_path=page_store_path
    )
    binding = checked_plan["source_binding"]
    if (
        type(image_bytes) is not bytes
        or sha256(image_bytes).hexdigest() != binding["image_sha256"]
        or len(image_bytes) != binding["image_size_bytes"]
    ):
        raise _error("roll-forward table repair image bytes do not bind the plan")
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except Exception as exc:
        raise _error("roll-forward table repair image cannot be decoded") from exc
    if image.size != (binding["pixel_width"], binding["pixel_height"]):
        raise _error("roll-forward table repair image dimensions drifted")
    crop = image.crop(tuple(binding["crop_bbox_pixels_xyxy"]))
    output = BytesIO()
    crop.save(output, format="PNG")
    payload = output.getvalue()
    material = {
        "crop_bbox_pixels_xyxy": binding["crop_bbox_pixels_xyxy"],
        "crop_height": crop.height,
        "crop_image_sha256": sha256(payload).hexdigest(),
        "crop_size_bytes": len(payload),
        "crop_width": crop.width,
        "full_image_sha256": binding["image_sha256"],
        "format_version": CROP_RECEIPT_FORMAT_VERSION,
        "page_id": binding["page_id"],
        "prompt_sha256": checked_plan["request_contract"]["prompt_sha256"],
        "repair_job_id": checked_plan["repair_job_id"],
        "repair_spec_authority_manifest_sha256": checked_spec_authority["manifest_sha256"],
        "response_schema_sha256": checked_plan["request_contract"]["response_schema_sha256"],
        "source_binding_sha256": canonical_json_sha256_v1(binding),
    }
    return payload, {
        **material,
        "crop_receipt_id": "gjfrtcv1:crop:" + canonical_json_sha256_v1(material),
    }


def _replay_crop_artifact(
    *,
    plan: Mapping[str, Any],
    crop_receipt: Mapping[str, Any],
    source_image_bytes: bytes,
    crop_image_bytes: bytes,
    page_store_path: Path,
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
) -> dict[str, Any]:
    if type(crop_image_bytes) is not bytes:
        raise _error("roll-forward table repair crop artifact bytes are invalid")
    expected_bytes, expected_receipt = crop_rollforward_table_image_v1(
        source_image_bytes,
        plan=plan,
        page_store_path=page_store_path,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
    )
    if crop_image_bytes != expected_bytes or not same_typed_json_v1(
        dict(crop_receipt), expected_receipt
    ):
        raise _error("roll-forward table repair crop artifact does not replay source pixels")
    return expected_receipt


def validate_rollforward_table_repair_usage_v1(value: Any) -> dict[str, Any]:
    checked = _exact_keys(value, _USAGE_FIELDS, "roll-forward table repair usage")
    if (
        any(
            type(checked[field]) is not int or checked[field] < 0
            for field in _USAGE_FIELDS
            if field.endswith("_tokens")
        )
        or type(checked["cost_disposition"]) is not str
        or not checked["cost_disposition"]
    ):
        raise _error("roll-forward table repair token or cost disposition is invalid")
    try:
        cost = Decimal(checked["actual_cost_usd"])
    except (InvalidOperation, TypeError) as exc:
        raise _error("roll-forward table repair actual cost is invalid") from exc
    if cost < 0 or not cost.is_finite():
        raise _error("roll-forward table repair actual cost is invalid")
    if checked["cached_input_tokens"] > checked["input_tokens"]:
        raise _error("roll-forward table repair cached input exceeds input tokens")
    return canonical_clone_v1(checked)


def _crop_receipt(value: Any, *, plan: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "crop_bbox_pixels_xyxy",
        "crop_height",
        "crop_image_sha256",
        "crop_receipt_id",
        "crop_size_bytes",
        "crop_width",
        "format_version",
        "full_image_sha256",
        "page_id",
        "prompt_sha256",
        "repair_job_id",
        "repair_spec_authority_manifest_sha256",
        "response_schema_sha256",
        "source_binding_sha256",
    }
    checked = _exact_keys(value, fields, "roll-forward table crop receipt")
    material = {key: checked[key] for key in checked if key != "crop_receipt_id"}
    binding = plan["source_binding"]
    bbox = binding["crop_bbox_pixels_xyxy"]
    if (
        checked["format_version"] != CROP_RECEIPT_FORMAT_VERSION
        or checked["crop_receipt_id"] != "gjfrtcv1:crop:" + canonical_json_sha256_v1(material)
        or checked["repair_job_id"] != plan["repair_job_id"]
        or _hash(
            checked["repair_spec_authority_manifest_sha256"],
            "table repair crop repair-spec authority manifest SHA-256",
        )
        != checked["repair_spec_authority_manifest_sha256"]
        or checked["page_id"] != binding["page_id"]
        or checked["full_image_sha256"] != binding["image_sha256"]
        or checked["source_binding_sha256"] != canonical_json_sha256_v1(binding)
        or checked["crop_bbox_pixels_xyxy"] != bbox
        or checked["crop_width"] != bbox[2] - bbox[0]
        or checked["crop_height"] != bbox[3] - bbox[1]
        or type(checked["crop_size_bytes"]) is not int
        or checked["crop_size_bytes"] <= 0
        or _hash(checked["crop_image_sha256"], "table repair crop SHA-256")
        != checked["crop_image_sha256"]
        or checked["prompt_sha256"] != plan["request_contract"]["prompt_sha256"]
        or checked["response_schema_sha256"] != plan["request_contract"]["response_schema_sha256"]
    ):
        raise _error("roll-forward table crop receipt does not replay the plan")
    return canonical_clone_v1(checked)


def _content_ref(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    checked = _exact_keys(value, {"path", "sha256", "size_bytes"}, label)
    if (
        type(checked["path"]) is not str
        or not checked["path"]
        or checked["path"].startswith("/")
        or ".." in checked["path"].split("/")
        or _hash(checked["sha256"], f"{label} SHA-256") != checked["sha256"]
        or type(checked["size_bytes"]) is not int
        or checked["size_bytes"] <= 0
    ):
        raise _error(f"{label} is invalid")
    return canonical_clone_v1(checked)


def _artifact_bytes(
    artifacts_by_sha256: Mapping[str, bytes],
    *,
    sha256_value: str,
    size_bytes: int,
    label: str,
) -> bytes:
    if type(artifacts_by_sha256) is not dict:
        raise _error(f"{label} artifact frontier is invalid")
    payload = artifacts_by_sha256.get(sha256_value)
    if (
        type(payload) is not bytes
        or len(payload) != size_bytes
        or sha256(payload).hexdigest() != sha256_value
    ):
        raise _error(f"{label} artifact bytes are absent or do not replay")
    return payload


def _validation_record(value: Any) -> dict[str, Any]:
    checked = _exact_keys(
        value,
        {"reason_codes", "status"},
        "roll-forward table repair validation record",
    )
    if (
        checked["status"] not in {"FAIL", "PASS"}
        or type(checked["reason_codes"]) is not list
        or checked["reason_codes"] != sorted(set(checked["reason_codes"]))
        or any(type(reason) is not str or not reason for reason in checked["reason_codes"])
        or (checked["status"] == "PASS") != (not checked["reason_codes"])
    ):
        raise _error("roll-forward table repair validation record is invalid")
    return canonical_clone_v1(checked)


def _provider(value: Any) -> dict[str, Any]:
    checked = _exact_keys(value, _PROVIDER_FIELDS, "roll-forward table repair provider")
    if any(
        type(checked[field]) is not str or not checked[field]
        for field in ("provider_model", "provider_name", "service_tier")
    ) or type(checked["response_id_sha256"]) not in {str, type(None)}:
        raise _error("roll-forward table repair provider identity is invalid")
    _hash(checked["request_id_sha256"], "roll-forward table repair request ID SHA-256")
    if checked["response_id_sha256"] is not None:
        _hash(checked["response_id_sha256"], "roll-forward table repair response ID SHA-256")
    return canonical_clone_v1(checked)


def _provider_usage_gate(provider: Mapping[str, Any], usage: Mapping[str, Any]) -> None:
    name = provider["provider_name"].casefold()
    input_tokens = usage["input_tokens"]
    output_tokens = usage["output_tokens"]
    thought_tokens = usage["thought_tokens"]
    total_tokens = usage["total_tokens"]
    if name == "openrouter":
        if total_tokens != input_tokens + output_tokens or thought_tokens > output_tokens:
            raise _error("OpenRouter table repair token equation does not close")
        return
    if name == "google":
        if total_tokens != input_tokens + output_tokens + thought_tokens:
            raise _error("Google table repair token equation does not close")
        return
    raise _error("roll-forward table repair provider usage semantics are undeclared")


def _validated_attempt(value: Any) -> dict[str, Any]:
    fields = {
        "attempt_id",
        "attempt_ordinal",
        "crop_receipt",
        "decoded_response_sha256",
        "elapsed_seconds",
        "format_version",
        "next_status",
        "observed_page_json_version_id",
        "outcome",
        "provider",
        "repair_id",
        "repair_job_id",
        "repair_receipt_sha256",
        "repair_spec_authority_manifest_sha256",
        "request_contract_sha256",
        "response_artifact_ref",
        "sibling_base_page_json_version_id",
        "thinking_level",
        "usage",
        "validation",
    }
    checked = _exact_keys(value, fields, "roll-forward table repair attempt")
    material = {key: checked[key] for key in checked if key != "attempt_id"}
    if checked["format_version"] != ATTEMPT_FORMAT_VERSION or checked[
        "attempt_id"
    ] != "gjfrtav1:attempt:" + canonical_json_sha256_v1(material):
        raise _error("roll-forward table repair attempt identity does not replay")
    if (
        type(checked["attempt_ordinal"]) is not int
        or checked["attempt_ordinal"] not in {1, 2, 3}
        or checked["thinking_level"] != _THINKING_LEVELS[checked["attempt_ordinal"] - 1]
        or checked["outcome"] not in _ATTEMPT_OUTCOMES
        or checked["next_status"] not in {"ABSTAINED", "PENDING", "RESOLVED"}
        or type(checked["repair_job_id"]) is not str
        or not checked["repair_job_id"].startswith("gjfrrqv1:job:")
    ):
        raise _error("roll-forward table repair attempt state is invalid")
    _prefixed_hash(
        checked["sibling_base_page_json_version_id"],
        "gfpstorev1:json:",
        "table repair attempt sibling base version",
    )
    if checked["observed_page_json_version_id"] is not None:
        _prefixed_hash(
            checked["observed_page_json_version_id"],
            "gfpstorev1:json:",
            "table repair attempt observed version",
        )
    _hash(checked["request_contract_sha256"], "table repair request contract SHA-256")
    _hash(
        checked["repair_spec_authority_manifest_sha256"],
        "table repair attempt repair-spec authority manifest SHA-256",
    )
    if checked["decoded_response_sha256"] is not None:
        _hash(
            checked["decoded_response_sha256"],
            "table repair decoded response SHA-256",
        )
    provider = _provider(checked["provider"])
    usage = validate_rollforward_table_repair_usage_v1(checked["usage"])
    _provider_usage_gate(provider, usage)
    _content_ref(checked["response_artifact_ref"], "table repair raw response reference")
    validation = _validation_record(checked["validation"])
    try:
        elapsed = Decimal(checked["elapsed_seconds"])
    except (InvalidOperation, TypeError) as exc:
        raise _error("roll-forward table repair attempt elapsed time is invalid") from exc
    if elapsed < 0 or not elapsed.is_finite():
        raise _error("roll-forward table repair attempt elapsed time is invalid")
    resolved = checked["outcome"] == "RESOLVED"
    if (
        resolved
        != (
            checked["next_status"] == "RESOLVED"
            and checked["observed_page_json_version_id"] is not None
            and checked["repair_id"] is not None
            and checked["repair_receipt_sha256"] is not None
            and validation["status"] == "PASS"
            and checked["response_artifact_ref"] is not None
            and checked["decoded_response_sha256"] is not None
        )
        or (not resolved and validation["status"] != "FAIL")
        or (
            not resolved
            and any(
                checked[field] is not None
                for field in (
                    "observed_page_json_version_id",
                    "repair_id",
                    "repair_receipt_sha256",
                )
            )
        )
        or (checked["attempt_ordinal"] < 3 and not resolved and checked["next_status"] != "PENDING")
        or (
            checked["attempt_ordinal"] == 3
            and not resolved
            and checked["next_status"] != "ABSTAINED"
        )
    ):
        raise _error("roll-forward table repair attempt outcome lineage is invalid")
    if checked["repair_id"] is not None:
        _prefixed_hash(checked["repair_id"], "gjfrrv1:repair:", "table repair ID")
        _hash(checked["repair_receipt_sha256"], "table repair receipt SHA-256")
    return canonical_clone_v1(checked)


def _repair_receipt_for_plan(
    value: Any,
    *,
    plan: Mapping[str, Any],
    repair_spec_authority_manifest_sha256: str,
) -> dict[str, Any]:
    fields = {
        "base_page_json_sha256",
        "base_page_json_version_id",
        "changes",
        "format_version",
        "merged_page_json_sha256",
        "repair_id",
        "repair_response_sha256",
    }
    receipt = _exact_keys(value, fields, "roll-forward table repair receipt")
    material = {key: receipt[key] for key in receipt if key != "repair_id"}
    if (
        receipt["format_version"] != "GEMINI_JSON_REGION_REPAIR_V1"
        or receipt["repair_id"] != "gjfrrv1:repair:" + canonical_json_sha256_v1(material)
        or receipt["base_page_json_version_id"] != plan["base_page_json_version_id"]
        or receipt["base_page_json_sha256"] != plan["base_page_json_sha256"]
        or type(receipt["changes"]) is not list
        or len(receipt["changes"]) != 1
    ):
        raise _error("resolved roll-forward table repair receipt identity drifted")
    _hash(receipt["merged_page_json_sha256"], "table repair merged page SHA-256")
    _hash(receipt["repair_response_sha256"], "table repair response SHA-256")
    change = receipt["changes"][0]
    required_change_fields = {
        "all_other_cells_byte_equal",
        "base_table_sha256",
        "cell_changes",
        "changed_cell_count",
        "equation_gate",
        "equation_inventory_sha256",
        "merged_table_sha256",
        "repair_scope",
        "repair_spec_authority_manifest_sha256",
        "response_projection",
        "shape_gate",
        "source_binding",
        "target_id",
        "validated_allowlist_cell_count",
    }
    if (
        type(change) is not dict
        or set(change) != required_change_fields
        or change["all_other_cells_byte_equal"] is not True
        or change["repair_scope"] != REPAIR_SCOPE
        or change["repair_spec_authority_manifest_sha256"] != repair_spec_authority_manifest_sha256
        or change["base_table_sha256"] != plan["shape_gate"]["base_table_sha256"]
        or change["shape_gate"] != plan["shape_gate"]
        or change["source_binding"] != plan["source_binding"]
        or change["equation_inventory_sha256"] != plan["equation_inventory_sha256"]
        or change["target_id"] != f"{plan['section_id']}:{plan['table_id']}"
        or type(change["response_projection"]) is not dict
        or set(change["response_projection"])
        != {
            "corroborated_duplicate_count",
            "corroborated_observations",
            "ignored_observation_count",
            "ignored_observations",
            "ignored_top_level_fields",
            "input_contract",
            "normalized_observation_count",
            "normalized_observations",
            "raw_response_sha256",
            "target_axis_sha256",
        }
        or change["response_projection"]["ignored_observation_count"]
        != len(change["response_projection"]["ignored_observations"])
        or change["response_projection"]["corroborated_duplicate_count"]
        != len(change["response_projection"]["corroborated_observations"])
        or change["response_projection"]["normalized_observation_count"]
        != len(change["response_projection"]["normalized_observations"])
        or change["validated_allowlist_cell_count"] != len(plan["cell_allowlist"])
        or type(change["cell_changes"]) is not list
        or change["changed_cell_count"] != len(change["cell_changes"])
        or change["changed_cell_count"] <= 0
        or not {
            item["cell_id"]
            for item in plan["cell_allowlist"]
            if item["change_policy"] == "MUST_CHANGE"
        }
        <= {item.get("cell_id") for item in change["cell_changes"]}
        or any(
            item.get("cell_id") not in {allowed["cell_id"] for allowed in plan["cell_allowlist"]}
            for item in change["cell_changes"]
        )
    ):
        raise _error("resolved roll-forward table repair receipt contract drifted")
    return canonical_clone_v1(receipt)


def build_rollforward_table_repair_attempt_v1(
    *,
    plan: Mapping[str, Any],
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
    page_store_path: Path,
    prior_attempts: Sequence[Mapping[str, Any]],
    thinking_level: str,
    outcome: str,
    observed_page_json_version_id: str | None,
    repair_receipt: Mapping[str, Any] | None,
    crop_receipt: Mapping[str, Any],
    source_image_bytes: bytes,
    crop_image_bytes: bytes,
    response_artifact_ref: Mapping[str, Any] | None,
    raw_response_bytes: bytes | None,
    validation: Mapping[str, Any],
    usage: Mapping[str, Any],
    provider: Mapping[str, Any],
    elapsed_seconds: str,
) -> dict[str, Any]:
    """Append one typed low/medium/high sibling attempt ledger record."""

    checked_plan, checked_spec_authority = _authoritative_plan(
        plan,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
        page_store_path=page_store_path,
    )
    prior = [_validated_attempt(item) for item in prior_attempts]
    if any(
        item["repair_job_id"] != checked_plan["repair_job_id"]
        or item["sibling_base_page_json_version_id"] != checked_plan["base_page_json_version_id"]
        or item["attempt_ordinal"] != index
        or item["thinking_level"] != _THINKING_LEVELS[index - 1]
        for index, item in enumerate(prior, start=1)
    ) or (prior and prior[-1]["next_status"] != "PENDING"):
        raise _error("roll-forward table repair prior attempt frontier does not replay")
    ordinal = len(prior) + 1
    if (
        ordinal > 3
        or thinking_level != _THINKING_LEVELS[ordinal - 1]
        or outcome not in _ATTEMPT_OUTCOMES
    ):
        raise _error("roll-forward table repair thinking escalation is invalid")
    try:
        elapsed = Decimal(elapsed_seconds)
    except (InvalidOperation, TypeError) as exc:
        raise _error("roll-forward table repair elapsed time is invalid") from exc
    if elapsed < 0 or not elapsed.is_finite():
        raise _error("roll-forward table repair elapsed time is invalid")
    checked_usage = validate_rollforward_table_repair_usage_v1(dict(usage))
    checked_provider = _provider(provider)
    _provider_usage_gate(checked_provider, checked_usage)
    checked_crop = _replay_crop_artifact(
        plan=checked_plan,
        crop_receipt=crop_receipt,
        source_image_bytes=source_image_bytes,
        crop_image_bytes=crop_image_bytes,
        page_store_path=page_store_path,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
    )
    if any(
        _crop_receipt(item["crop_receipt"], plan=checked_plan) != checked_crop
        or item["repair_spec_authority_manifest_sha256"]
        != checked_spec_authority["manifest_sha256"]
        or item["request_contract_sha256"]
        != canonical_json_sha256_v1(checked_plan["request_contract"])
        for item in prior
    ):
        raise _error("roll-forward table repair prior request/crop lineage drifted")
    checked_response_ref = _content_ref(
        response_artifact_ref, "table repair raw response reference"
    )
    if raw_response_bytes is not None and type(raw_response_bytes) is not bytes:
        raise _error("roll-forward table repair raw response bytes are invalid")
    if (raw_response_bytes is None) != (checked_response_ref is None):
        raise _error("roll-forward table repair raw response bytes/ref presence differs")
    if raw_response_bytes is not None and (
        sha256(raw_response_bytes).hexdigest() != checked_response_ref["sha256"]
        or len(raw_response_bytes) != checked_response_ref["size_bytes"]
    ):
        raise _error("roll-forward table repair raw response bytes do not bind their ref")
    decoded = None
    decoded_response_sha = None
    if raw_response_bytes is not None:
        try:
            response_text = raw_response_bytes.decode("utf-8")
            base_evidence = load_rollforward_table_page_evidence_v1(
                page_store_path,
                page_json_version_ids=[checked_plan["base_page_json_version_id"]],
            )[0]
            decoded = decode_rollforward_table_repair_text_v1(
                response_text,
                target=rollforward_table_repair_target_v1(
                    base_evidence["page_json"], plan=checked_plan
                ),
            )
            decoded_response_sha = canonical_json_sha256_v1(decoded)
        except (UnicodeDecodeError, GeminiJsonRollforwardTableRepairV1Error):
            decoded_response_sha = None
    checked_validation = _validation_record(validation)
    resolved = outcome == "RESOLVED"
    if resolved:
        checked_receipt = _repair_receipt_for_plan(
            repair_receipt,
            plan=checked_plan,
            repair_spec_authority_manifest_sha256=checked_spec_authority["manifest_sha256"],
        )
        if (
            type(observed_page_json_version_id) is not str
            or checked_response_ref is None
            or decoded is None
            or checked_validation != {"reason_codes": [], "status": "PASS"}
            or decoded_response_sha != checked_receipt["repair_response_sha256"]
        ):
            raise _error("resolved roll-forward table repair lineage is invalid")
        _prefixed_hash(
            observed_page_json_version_id,
            "gfpstorev1:json:",
            "roll-forward table repair observed version",
        )
        base_evidence = load_rollforward_table_page_evidence_v1(
            page_store_path,
            page_json_version_ids=[checked_plan["base_page_json_version_id"]],
        )[0]
        expected_merged, expected_receipt = merge_rollforward_table_repair_v1(
            base_evidence["page_json"],
            plan=checked_plan,
            repair=decoded,
            page_store_path=page_store_path,
            authority=authority,
            repair_spec_authority=repair_spec_authority,
        )
        if not same_typed_json_v1(expected_receipt, checked_receipt):
            raise _error("resolved roll-forward table repair receipt does not exact-replay")
        from bctc_ai.storage.gemini_financial_page_store_v1 import (
            page_json_region_repair_lineages_v1,
        )

        lineage = page_json_region_repair_lineages_v1(
            page_store_path,
            observed_page_json_version_ids=[observed_page_json_version_id],
        )[0]
        merged_evidence = load_rollforward_table_page_evidence_v1(
            page_store_path,
            page_json_version_ids=[lineage["canonical_merged_page_json_version_id"]],
        )[0]
        if (
            lineage["base_page_json_version_id"] != checked_plan["base_page_json_version_id"]
            or not same_typed_json_v1(lineage["repair_receipt"], expected_receipt)
            or lineage["repair_receipt_sha256"]
            != sha256(canonical_json_bytes_v1(expected_receipt) + b"\n").hexdigest()
            or merged_evidence["source_binding_without_crop"]
            != base_evidence["source_binding_without_crop"]
            or not same_typed_json_v1(merged_evidence["page_json"], expected_merged)
        ):
            raise _error("resolved roll-forward table repair stored lineage does not exact-replay")
        repair_id = checked_receipt["repair_id"]
        receipt_sha = sha256(canonical_json_bytes_v1(checked_receipt) + b"\n").hexdigest()
        next_status = "RESOLVED"
    else:
        if (
            observed_page_json_version_id is not None
            or repair_receipt is not None
            or checked_validation["status"] != "FAIL"
            or (outcome == "RETRYABLE_VALIDATION_FAILURE" and checked_response_ref is None)
        ):
            raise _error("failed roll-forward table repair cannot select a sibling version")
        repair_id = None
        receipt_sha = None
        next_status = "ABSTAINED" if ordinal == 3 else "PENDING"
    material = {
        "attempt_ordinal": ordinal,
        "crop_receipt": checked_crop,
        "decoded_response_sha256": decoded_response_sha,
        "elapsed_seconds": str(elapsed_seconds),
        "format_version": ATTEMPT_FORMAT_VERSION,
        "next_status": next_status,
        "observed_page_json_version_id": observed_page_json_version_id,
        "outcome": outcome,
        "provider": checked_provider,
        "repair_id": repair_id,
        "repair_job_id": checked_plan["repair_job_id"],
        "repair_receipt_sha256": receipt_sha,
        "repair_spec_authority_manifest_sha256": checked_spec_authority["manifest_sha256"],
        "request_contract_sha256": canonical_json_sha256_v1(checked_plan["request_contract"]),
        "response_artifact_ref": checked_response_ref,
        "sibling_base_page_json_version_id": checked_plan["base_page_json_version_id"],
        "thinking_level": thinking_level,
        "usage": checked_usage,
        "validation": checked_validation,
    }
    return {
        **material,
        "attempt_id": "gjfrtav1:attempt:" + canonical_json_sha256_v1(material),
    }


def build_rollforward_table_repair_overlay_v1(
    *,
    family_run_id: str,
    plans: Sequence[Mapping[str, Any]],
    attempts: Sequence[Mapping[str, Any]],
    page_store_path: Path,
    authority: Mapping[str, Any],
    repair_spec_authority: Mapping[str, Any],
    source_image_artifacts_by_sha256: Mapping[str, bytes],
    crop_image_artifacts_by_sha256: Mapping[str, bytes],
    response_artifacts_by_sha256: Mapping[str, bytes],
) -> dict[str, Any]:
    """Build standard replacement rows for a later family effective frontier."""

    _prefixed_hash(family_run_id, "gjfafstorev1:run:", "repair source family run ID")
    checked_plans = [_validated_plan(plan) for plan in plans]
    checked_attempts = [_validated_attempt(attempt) for attempt in attempts]
    if not checked_plans or len({plan["repair_job_id"] for plan in checked_plans}) != len(
        checked_plans
    ):
        raise _error("roll-forward table repair overlay plan frontier is empty or duplicate")
    rebuilt_plans, checked_spec_authority = _authoritative_plan_axis(
        authority,
        repair_spec_authority=repair_spec_authority,
        page_store_path=page_store_path,
    )
    rebuilt_by_job = {plan["repair_job_id"]: plan for plan in rebuilt_plans}
    if any(
        plan["repair_job_id"] not in rebuilt_by_job
        or not same_typed_json_v1(plan, rebuilt_by_job[plan["repair_job_id"]])
        for plan in checked_plans
    ):
        raise _error("table repair overlay plan is not the exact authoritative replay")
    plan_by_job = {plan["repair_job_id"]: plan for plan in checked_plans}
    if any(attempt["repair_job_id"] not in plan_by_job for attempt in checked_attempts):
        raise _error("roll-forward table repair overlay contains an unplanned attempt")
    for attempt in checked_attempts:
        plan = plan_by_job[attempt["repair_job_id"]]
        if (
            attempt["sibling_base_page_json_version_id"] != plan["base_page_json_version_id"]
            or attempt["request_contract_sha256"]
            != canonical_json_sha256_v1(plan["request_contract"])
            or attempt["repair_spec_authority_manifest_sha256"]
            != checked_spec_authority["manifest_sha256"]
        ):
            raise _error("roll-forward table repair overlay attempt crosses one plan")
        source_image_bytes = _artifact_bytes(
            source_image_artifacts_by_sha256,
            sha256_value=plan["source_binding"]["image_sha256"],
            size_bytes=plan["source_binding"]["image_size_bytes"],
            label="table repair source image",
        )
        crop_receipt = attempt["crop_receipt"]
        crop_image_bytes = _artifact_bytes(
            crop_image_artifacts_by_sha256,
            sha256_value=crop_receipt["crop_image_sha256"],
            size_bytes=crop_receipt["crop_size_bytes"],
            label="table repair crop image",
        )
        _replay_crop_artifact(
            plan=plan,
            crop_receipt=crop_receipt,
            source_image_bytes=source_image_bytes,
            crop_image_bytes=crop_image_bytes,
            page_store_path=page_store_path,
            authority=authority,
            repair_spec_authority=repair_spec_authority,
        )
        response_ref = attempt["response_artifact_ref"]
        if response_ref is not None:
            _artifact_bytes(
                response_artifacts_by_sha256,
                sha256_value=response_ref["sha256"],
                size_bytes=response_ref["size_bytes"],
                label="table repair response",
            )
    resolved_attempts = [
        attempt for attempt in checked_attempts if attempt["next_status"] == "RESOLVED"
    ]
    lineages_by_observed = {}
    if resolved_attempts:
        from bctc_ai.storage.gemini_financial_page_store_v1 import (
            page_json_region_repair_lineages_v1,
        )

        lineages = page_json_region_repair_lineages_v1(
            page_store_path,
            observed_page_json_version_ids=[
                item["observed_page_json_version_id"] for item in resolved_attempts
            ],
        )
        lineages_by_observed = {item["observed_page_json_version_id"]: item for item in lineages}
    family_ids = {plan["family_id"] for plan in checked_plans}
    replacements = []
    statuses = []
    for plan in checked_plans:
        job_attempts = sorted(
            (
                attempt
                for attempt in checked_attempts
                if attempt["repair_job_id"] == plan["repair_job_id"]
            ),
            key=lambda item: item["attempt_ordinal"],
        )
        if (
            not job_attempts
            or [item["attempt_ordinal"] for item in job_attempts]
            != list(range(1, len(job_attempts) + 1))
            or any(
                item["next_status"] != "PENDING" or item["outcome"] == "RESOLVED"
                for item in job_attempts[:-1]
            )
            or job_attempts[-1]["next_status"] not in {"RESOLVED", "ABSTAINED"}
        ):
            raise _error("roll-forward table repair overlay contains a nonterminal job")
        terminal = job_attempts[-1]
        statuses.append(terminal["next_status"])
        if terminal["next_status"] == "ABSTAINED":
            continue
        lineage = lineages_by_observed.get(terminal["observed_page_json_version_id"])
        if (
            lineage is None
            or lineage["base_page_json_version_id"] != plan["base_page_json_version_id"]
            or lineage["repair_id"] != terminal["repair_id"]
            or lineage["repair_receipt_sha256"] != terminal["repair_receipt_sha256"]
            or lineage["repair_receipt"].get("repair_response_sha256")
            != terminal["decoded_response_sha256"]
        ):
            raise _error("roll-forward table repair overlay page-store lineage drifted")
        response_ref = terminal["response_artifact_ref"]
        if response_ref is None:
            raise _error("resolved roll-forward table repair response artifact is absent")
        raw_response = _artifact_bytes(
            response_artifacts_by_sha256,
            sha256_value=response_ref["sha256"],
            size_bytes=response_ref["size_bytes"],
            label="table repair response",
        )
        base_evidence = load_rollforward_table_page_evidence_v1(
            page_store_path,
            page_json_version_ids=[plan["base_page_json_version_id"]],
        )[0]
        target = rollforward_table_repair_target_v1(base_evidence["page_json"], plan=plan)
        try:
            decoded = decode_rollforward_table_repair_text_v1(
                raw_response.decode("utf-8"), target=target
            )
        except UnicodeDecodeError as exc:
            raise _error("resolved roll-forward response artifact is not UTF-8") from exc
        expected_merged, expected_receipt = merge_rollforward_table_repair_v1(
            base_evidence["page_json"],
            plan=plan,
            repair=decoded,
            page_store_path=page_store_path,
            authority=authority,
            repair_spec_authority=repair_spec_authority,
        )
        merged_evidence = load_rollforward_table_page_evidence_v1(
            page_store_path,
            page_json_version_ids=[lineage["canonical_merged_page_json_version_id"]],
        )[0]
        if (
            not same_typed_json_v1(lineage["repair_receipt"], expected_receipt)
            or not same_typed_json_v1(merged_evidence["page_json"], expected_merged)
            or merged_evidence["source_binding_without_crop"]
            != base_evidence["source_binding_without_crop"]
        ):
            raise _error("roll-forward table repair overlay exact page diff does not replay")
        _repair_receipt_for_plan(
            expected_receipt,
            plan=plan,
            repair_spec_authority_manifest_sha256=checked_spec_authority["manifest_sha256"],
        )
        replacements.append(
            {
                "base_page_json_version_id": plan["base_page_json_version_id"],
                "candidate_id": plan["candidate_id"],
                "document_ordinal": plan["document_ordinal"],
                "physical_page": plan["physical_page"],
                "repair_id": terminal["repair_id"],
                "repair_job_id": plan["repair_job_id"],
                "repair_receipt_sha256": terminal["repair_receipt_sha256"],
                "selected_page_json_version_id": lineage["canonical_merged_page_json_version_id"],
            }
        )
    if len(family_ids) != 1:
        raise _error("roll-forward table repair overlay crosses family identities")
    if len({item["base_page_json_version_id"] for item in replacements}) != len(replacements):
        raise _error("roll-forward table repair overlay replaces a base page twice")
    material = {
        "attempt_ledger_sha256": canonical_json_sha256_v1(checked_attempts),
        "family_id": next(iter(family_ids)),
        "format_version": OVERLAY_FORMAT_VERSION,
        "job_status_counts": {
            "ABSTAINED": statuses.count("ABSTAINED"),
            "RESOLVED": statuses.count("RESOLVED"),
        },
        "repair_source_family_run_id": family_run_id,
        "repair_spec_authority": checked_spec_authority,
        "replacements": sorted(
            replacements,
            key=lambda item: (item["document_ordinal"], item["physical_page"]),
        ),
    }
    return {
        **material,
        "overlay_id": "gjfrtov1:overlay:" + canonical_json_sha256_v1(material),
    }
