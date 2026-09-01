"""Deterministic 27-bank, Q1/2025-current universe for Gemini JSON-first.

The source survey deliberately treats filename metadata as a routing hint, not
as accounting evidence.  This module therefore keeps every Vietnamese full-
financial-statement candidate in the requested year window.  It removes only
byte-identical copies and records ambiguous filename hints for later
source-visible authentication by Gemini.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import date
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1"
SOURCE_FORMAT_VERSION = "BANK_CORPUS_SURVEY_INVENTORY_RESULT_V1"


class BankFilingUniverseV1Error(ValueError):
    """The registered source inventory cannot support the requested universe."""


def _error(message: str) -> BankFilingUniverseV1Error:
    return BankFilingUniverseV1Error(message)


def _checked_date(value: str) -> date:
    if not isinstance(value, str):
        raise _error("as-of date must be one ISO date string")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise _error("as-of date is invalid") from exc
    if result.isoformat() != value:
        raise _error("as-of date is not canonical ISO format")
    return result


def _checked_banks(values: tuple[str, ...]) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or len(values) != 27
        or tuple(sorted(values)) != values
        or len(set(values)) != len(values)
        or any(type(value) is not str or not value or value != value.upper() for value in values)
    ):
        raise _error("bank universe must contain 27 sorted unique uppercase codes")
    return values


def _checked_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise _error("source inventory document is not an object")
    required = {
        "bank",
        "dataset_role",
        "document_id",
        "duplicate_content_path_count",
        "filename_metadata",
        "relative_path",
        "sha256",
        "size_bytes",
        "source_survey_status",
        "year",
    }
    if set(value) != required:
        raise _error("source inventory document fields drifted")
    metadata = value["filename_metadata"]
    if not isinstance(metadata, Mapping):
        raise _error("filename metadata is not an object")
    required_metadata = {
        "assurance_hint",
        "document_kind",
        "document_kind_evidence",
        "language_hint",
        "metadata_authority",
        "normalized_filename",
        "reporting_period_hint",
        "reporting_year",
        "scope_hint",
        "source_type_hint",
    }
    if set(metadata) != required_metadata:
        raise _error("filename metadata fields drifted")
    path = value["relative_path"]
    digest = value["sha256"]
    size = value["size_bytes"]
    year = value["year"]
    bank = value["bank"]
    if (
        type(path) is not str
        or not path.startswith(f"vietstock_bctc/{bank}/{year}/")
        or not path.casefold().endswith(".pdf")
        or path.startswith("/")
        or ".." in path.split("/")
        or "\\" in path
    ):
        raise _error("source inventory path is unsafe or disagrees with bank/year")
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or value["document_id"] != f"sha256:{digest}"
    ):
        raise _error("source inventory content identity is invalid")
    if type(size) is not int or size <= 0 or type(year) is not int or type(bank) is not str:
        raise _error("source inventory document scalar fields are invalid")
    if metadata["reporting_year"] != year:
        raise _error("filename reporting year disagrees with source registry year")
    if metadata["metadata_authority"] != "FILENAME_DERIVED_NON_AUTHORITATIVE":
        raise _error("filename metadata must remain non-authoritative")
    return canonical_clone_v1(dict(value))


def _duplicate_preference(document: Mapping[str, Any]) -> tuple[Any, ...]:
    metadata = document["filename_metadata"]
    source_type_rank = 1 if metadata["source_type_hint"] == "SEARCHABLE_FILENAME_HINT" else 0
    basename = document["relative_path"].rsplit("/", 1)[-1]
    return (source_type_rank, len(basename), document["relative_path"])


def build_bank_filing_universe_v1(
    source_inventory: Mapping[str, Any],
    *,
    bank_codes: tuple[str, ...],
    from_year: int,
    as_of_date: str,
    source_inventory_ref: Mapping[str, Any],
    source_snapshot_manifest_uri: str,
    already_processed_bank_codes: tuple[str, ...] = (),
    already_processed_corpus_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the exhaustive content-unique Vietnamese BCTC candidate universe."""

    banks = _checked_banks(bank_codes)
    if (
        type(already_processed_bank_codes) is not tuple
        or tuple(sorted(already_processed_bank_codes)) != already_processed_bank_codes
        or len(set(already_processed_bank_codes)) != len(already_processed_bank_codes)
        or not set(already_processed_bank_codes).issubset(banks)
    ):
        raise _error("already-processed bank axis is invalid")
    processed_banks = frozenset(already_processed_bank_codes)
    if (
        not isinstance(already_processed_corpus_ref, Mapping)
        or set(already_processed_corpus_ref)
        != {"bank_codes", "document_count", "manifest_index_id", "page_count"}
        or already_processed_corpus_ref.get("bank_codes") != list(already_processed_bank_codes)
        or type(already_processed_corpus_ref.get("document_count")) is not int
        or already_processed_corpus_ref["document_count"] <= 0
        or type(already_processed_corpus_ref.get("page_count")) is not int
        or already_processed_corpus_ref["page_count"] <= 0
        or type(already_processed_corpus_ref.get("manifest_index_id")) is not str
        or not already_processed_corpus_ref["manifest_index_id"].startswith("gjfccmiv1:index:")
    ):
        raise _error("already-processed Gemini corpus reference is invalid")
    through = _checked_date(as_of_date)
    if type(from_year) is not int or not 2000 <= from_year <= through.year:
        raise _error("from year lies outside the supported range")
    if (
        not isinstance(source_inventory, Mapping)
        or source_inventory.get("format_version") != SOURCE_FORMAT_VERSION
        or source_inventory.get("status") != "COMPLETE_REGISTERED_BANK_PDF_METADATA_INVENTORY"
        or not isinstance(source_inventory.get("documents"), list)
    ):
        raise _error("source inventory identity or completion state drifted")
    if not isinstance(source_inventory_ref, Mapping) or set(source_inventory_ref) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        raise _error("source inventory reference fields drifted")
    if (
        type(source_snapshot_manifest_uri) is not str
        or not source_snapshot_manifest_uri.startswith("s3://")
        or "/snapshots/" not in source_snapshot_manifest_uri
        or not source_snapshot_manifest_uri.endswith(".json")
    ):
        raise _error("source snapshot manifest URI is invalid")

    checked = [_checked_document(item) for item in source_inventory["documents"]]
    requested = [
        item
        for item in checked
        if item["bank"] in banks and from_year <= item["year"] <= through.year
    ]
    represented = {item["bank"] for item in requested}
    if represented != set(banks):
        raise _error("requested year window does not represent all 27 banks")

    eligible = [
        item
        for item in requested
        if item["filename_metadata"]["document_kind"] == "FULL_FINANCIAL_STATEMENT_CANDIDATE"
        and item["filename_metadata"]["language_hint"] == "VI"
    ]
    eligible_by_digest: dict[str, list[dict[str, Any]]] = {}
    for item in eligible:
        eligible_by_digest.setdefault(item["sha256"], []).append(item)

    selected: list[dict[str, Any]] = []
    exact_duplicates: list[dict[str, Any]] = []
    for digest, group in sorted(eligible_by_digest.items()):
        ranked = sorted(group, key=_duplicate_preference)
        kept = ranked[0]
        metadata = kept["filename_metadata"]
        flags = []
        if metadata["scope_hint"] in {"UNKNOWN", "AMBIGUOUS"}:
            flags.append("SCOPE_REQUIRES_SOURCE_AUTHENTICATION")
        if metadata["reporting_period_hint"] in {"UNKNOWN", "AMBIGUOUS"}:
            flags.append("PERIOD_REQUIRES_SOURCE_AUTHENTICATION")
        if metadata["assurance_hint"] in {"UNKNOWN", "AMBIGUOUS"}:
            flags.append("ASSURANCE_REQUIRES_SOURCE_AUTHENTICATION")
        selected.append(
            {
                "bank": kept["bank"],
                "content_ref": {
                    "path": kept["relative_path"],
                    "sha256": digest,
                    "size_bytes": kept["size_bytes"],
                },
                "filename_hints_non_authoritative": {
                    "assurance": metadata["assurance_hint"],
                    "period": metadata["reporting_period_hint"],
                    "scope": metadata["scope_hint"],
                },
                "provider_disposition": (
                    "REUSE_EXISTING_GEMINI_JSON"
                    if kept["bank"] in processed_banks
                    else "NEW_VERTEX_FLEX_FRONTIER"
                ),
                "source_authentication_flags": flags,
                "year": kept["year"],
            }
        )
        for duplicate in ranked[1:]:
            exact_duplicates.append(
                {
                    "kept_path": kept["relative_path"],
                    "omitted_path": duplicate["relative_path"],
                    "sha256": digest,
                }
            )

    selected.sort(key=lambda item: (item["bank"], item["year"], item["content_ref"]["path"]))
    if {item["bank"] for item in selected} != set(banks):
        raise _error("eligible Vietnamese BCTC candidates do not represent all 27 banks")
    selected_paths = {item["content_ref"]["path"] for item in selected}
    excluded_counts = Counter()
    for item in requested:
        if item["relative_path"] in selected_paths:
            continue
        metadata = item["filename_metadata"]
        if metadata["document_kind"] != "FULL_FINANCIAL_STATEMENT_CANDIDATE":
            excluded_counts[metadata["document_kind"]] += 1
        elif metadata["language_hint"] != "VI":
            excluded_counts["NON_VI_FULL_FINANCIAL_STATEMENT"] += 1
        elif any(
            duplicate["omitted_path"] == item["relative_path"] for duplicate in exact_duplicates
        ):
            excluded_counts["EXACT_DUPLICATE_CONTENT"] += 1
        else:
            raise _error("one requested source lacks an exhaustive disposition")

    material = {
        "as_of_date": through.isoformat(),
        "already_processed_bank_codes": list(already_processed_bank_codes),
        "already_processed_corpus_ref": canonical_clone_v1(dict(already_processed_corpus_ref)),
        "authority": {
            "already_processed_bank_paid_calls_allowed": False,
            "filename_hints_used_as_accounting_evidence": False,
            "source_visible_metadata_authentication_required": True,
            "selection_rule": (
                "ALL_VIETNAMESE_FULL_FINANCIAL_STATEMENT_CANDIDATES_EXACT_CONTENT_DEDUPLICATED"
            ),
        },
        "bank_codes": list(banks),
        "exact_duplicate_contents": exact_duplicates,
        "excluded_counts": dict(sorted(excluded_counts.items())),
        "filings": selected,
        "format_version": FORMAT_VERSION,
        "from_year": from_year,
        "new_bank_codes": sorted(set(banks) - processed_banks),
        "source_inventory_ref": canonical_clone_v1(dict(source_inventory_ref)),
        "source_snapshot_manifest_uri": source_snapshot_manifest_uri,
        "summary": {
            "bank_count": len(banks),
            "already_processed_bank_count": len(processed_banks),
            "already_processed_corpus_filing_count": already_processed_corpus_ref["document_count"],
            "already_processed_corpus_page_count": already_processed_corpus_ref["page_count"],
            "candidate_filing_count": len(selected),
            "candidate_source_bytes": sum(item["content_ref"]["size_bytes"] for item in selected),
            "exact_duplicate_path_count": len(exact_duplicates),
            "new_bank_count": len(banks) - len(processed_banks),
            "provider_call_candidate_filing_count": sum(
                item["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER" for item in selected
            ),
            "provider_call_candidate_source_bytes": sum(
                item["content_ref"]["size_bytes"]
                for item in selected
                if item["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER"
            ),
            "provider_call_source_authentication_required_count": sum(
                bool(item["source_authentication_flags"])
                for item in selected
                if item["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER"
            ),
            "requested_registered_pdf_path_count": len(requested),
            "reuse_existing_candidate_filing_count": sum(
                item["provider_disposition"] == "REUSE_EXISTING_GEMINI_JSON" for item in selected
            ),
            "source_authentication_required_count": sum(
                bool(item["source_authentication_flags"]) for item in selected
            ),
        },
    }
    return {
        **material,
        "universe_id": "bankfilinguniversev1:" + canonical_json_sha256_v1(material),
    }
