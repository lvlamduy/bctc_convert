"""Project caller-authenticated selected pages into semantic-region input.

This bridge validates and canonicalizes the selected-page snapshot shape.  It
does not authenticate a self-hashed snapshot: callers must obtain that object
through the public authenticated document-store capability.  Numeric-reader
text is retained only as the shared graph's value-cell challenger; it grants
no numeric or mapping authority.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AuthenticatedSemanticRegionSnapshotV1Error",
    "FamilyFirstRegionReceiptContractV2Error",
    "build_authenticated_semantic_region_snapshot_v1",
    "validate_authenticated_semantic_region_snapshot_replay_v1",
    "validate_family_first_region_retrieval_receipt_v2",
]


FORMAT_VERSION = "AUTHENTICATED_SEMANTIC_REGION_SNAPSHOT_PROJECTION_V1"
CLAIM_BOUNDARY = (
    "CALLER_AUTHENTICATED_SELECTED_PAGE_TO_SHARED_SEMANTIC_REGION_INPUT_"
    "PROJECTION_ONLY_NO_SNAPSHOT_AUTHENTICATION_NUMERIC_MAPPING_OR_SCHEMA_AUTHORITY"
)
_AUTHORITY = {
    "caller_authenticated_selected_snapshot_required": True,
    "input_snapshot_self_hash_is_authentication_authority": False,
    "mapping_authority": False,
    "numeric_reader_surface_is_numeric_authority": False,
    "schema_authority": False,
}
_RETRIEVAL_CLAIM_BOUNDARY = (
    "AUTHENTICATED_IMMUTABLE_SQLITE_EXACT_ACCENTLESS_FTS5_TRIGRAM_AND_"
    "BOUNDED_EDIT_REGION_SHORTLIST_COMPLETE_DOCUMENT_DENOMINATOR_ONLY_NO_"
    "ABSENCE_MAPPING_NUMERIC_ACCOUNTING_SCHEMA_OR_EXPORT_AUTHORITY"
)
_RETRIEVAL_AUTHORITY = {
    "absence_authority": False,
    "accounting_authority": False,
    "cache_or_receipt_self_authenticating": False,
    "complete_document_outcome_denominator": True,
    "historical_variant_semantic_assignment_authority": False,
    "historical_variant_support_presence_is_mapping_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "shortlist_authority": True,
    "source_database_must_be_authenticated": True,
}
_RETRIEVAL_METRIC_FIELDS = {
    "document_count",
    "fallback_document_count",
    "occurrence_count",
    "raw_fts_hit_line_count",
    "raw_rare_trigram_hit_line_count",
    "selected_page_count",
    "seed_occurrence_count",
    "source_line_count",
    "source_page_count",
    "zero_validated_hit_document_count",
}
_SNAPSHOT_FIELDS = {
    "document_packet",
    "joined_pages",
    "manifest_id",
    "query_selection_id",
    "selected_page_dimensions",
    "snapshot_id",
    "state",
}
_PACKET_FIELDS = {
    "assurance",
    "bank_provenance",
    "document_evidence_root_sha256",
    "document_id",
    "document_ordinal",
    "line_count",
    "packet_id",
    "page_count",
    "period",
    "scope",
    "source_pdf_ref",
    "year",
}
_PAGE_FIELDS = {"lines", "page_sequence", "page_width"}
_DIMENSION_FIELDS = {
    "physical_page",
    "pixel_height",
    "pixel_width",
    "render_sha256",
    "render_size_bytes",
}
_LINE_FIELDS = {
    "bbox",
    "crop_ref",
    "line_ordinal",
    "numeric_recognition",
    "sample_id",
    "vietocr_text",
}
_CONTENT_REF_FIELDS = {"path", "sha256", "size_bytes"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AuthenticatedSemanticRegionSnapshotV1Error(ValueError):
    """Selected-page projection identity or exact replay drifted."""


class FamilyFirstRegionReceiptContractV2Error(ValueError):
    """Generic V2 retrieval receipt identity or denominator drifted."""


def _error(message: str) -> AuthenticatedSemanticRegionSnapshotV1Error:
    return AuthenticatedSemanticRegionSnapshotV1Error(message)


def _receipt_error(message: str) -> FamilyFirstRegionReceiptContractV2Error:
    return FamilyFirstRegionReceiptContractV2Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise _error(f"{label} must be one exact string")
    if value != unicodedata.normalize("NFC", value):
        raise _error(f"{label} must already be NFC-normalized")
    return value


def _content_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _CONTENT_REF_FIELDS
        or type(value["path"]) is not str
        or not value["path"]
        or Path(value["path"]).is_absolute()
        or ".." in Path(value["path"]).parts
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] < 0
    ):
        raise _error(f"{label} content reference drifted")
    return canonical_clone_v1(value)


def _packet(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PACKET_FIELDS:
        raise _error("selected snapshot document packet fields drifted")
    packet = canonical_clone_v1(value)
    if (
        type(packet["document_id"]) is not str
        or not packet["document_id"]
        or type(packet["document_ordinal"]) is not int
        or packet["document_ordinal"] <= 0
        or type(packet["document_evidence_root_sha256"]) is not str
        or _SHA256.fullmatch(packet["document_evidence_root_sha256"]) is None
        or type(packet["packet_id"]) is not str
        or type(packet["page_count"]) is not int
        or packet["page_count"] <= 0
        or type(packet["line_count"]) is not int
        or packet["line_count"] < 0
    ):
        raise _error("selected snapshot document packet identity drifted")
    packet["source_pdf_ref"] = _content_ref(packet["source_pdf_ref"], "source PDF")
    material = canonical_clone_v1(packet)
    packet_id = material.pop("packet_id")
    if packet_id != "ffdesv1:document:" + canonical_json_sha256_v1(material):
        raise _error("selected snapshot document packet content identity drifted")
    return packet


def _dimension(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _DIMENSION_FIELDS:
        raise _error("selected snapshot page dimension fields drifted")
    if type(value["render_sha256"]) is not str or _SHA256.fullmatch(value["render_sha256"]) is None:
        raise _error("selected snapshot render identity drifted")
    return {
        "physical_page": _positive_int(value["physical_page"], "physical page"),
        "pixel_height": _positive_int(value["pixel_height"], "pixel height"),
        "pixel_width": _positive_int(value["pixel_width"], "pixel width"),
        "render_sha256": value["render_sha256"],
        "render_size_bytes": _positive_int(value["render_size_bytes"], "render size"),
    }


def _line(
    value: Any,
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _LINE_FIELDS:
        raise _error("selected snapshot line fields drifted")
    bbox = value["bbox"]
    numeric = value["numeric_recognition"]
    if (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int for item in bbox)
        or bbox[0] < 0
        or bbox[1] < 0
        or bbox[0] >= bbox[2]
        or bbox[1] >= bbox[3]
        or bbox[2] > width
        or bbox[3] > height
        or type(numeric) is not dict
        or set(numeric) != {"raw_prediction", "reader_score"}
        or type(numeric["reader_score"]) not in {int, float}
        or not math.isfinite(float(numeric["reader_score"]))
    ):
        raise _error("selected snapshot line geometry or numeric binding drifted")
    source_index = _nonnegative_int(value["line_ordinal"], "line ordinal")
    sample_id = _string(value["sample_id"], "sample ID")
    vietocr_text = _string(value["vietocr_text"], "VietOCR text", allow_empty=True)
    source_text = _string(
        numeric["raw_prediction"],
        "numeric-reader source text",
        allow_empty=True,
    )
    crop_ref = _content_ref(value["crop_ref"], "line crop")
    return {
        "bbox": list(bbox),
        "crop_ref": crop_ref,
        "line_ordinal": source_index,
        "numeric_recognition": {
            "raw_prediction": source_text,
            "reader_score": float(numeric["reader_score"]),
        },
        "sample_id": sample_id,
        "vietocr_text": vietocr_text,
    }


def _canonical_snapshot(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SNAPSHOT_FIELDS:
        raise _error("selected snapshot fields drifted")
    if value["state"] != "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE":
        raise _error("selected snapshot state drifted")
    packet = _packet(value["document_packet"])
    manifest_id = _string(value["manifest_id"], "manifest ID")
    selection_id = _string(value["query_selection_id"], "query selection ID")
    snapshot_id = _string(value["snapshot_id"], "snapshot ID")
    raw_dimensions = value["selected_page_dimensions"]
    raw_pages = value["joined_pages"]
    if (
        type(raw_dimensions) is not list
        or not raw_dimensions
        or type(raw_pages) is not list
        or not raw_pages
    ):
        raise _error("selected snapshot page axes drifted")
    dimensions = sorted(
        (_dimension(item) for item in raw_dimensions), key=lambda item: item["physical_page"]
    )
    dimension_ids = [item["physical_page"] for item in dimensions]
    if dimension_ids != sorted(set(dimension_ids)) or any(
        page > packet["page_count"] for page in dimension_ids
    ):
        raise _error("selected snapshot dimension page axis drifted")
    dimension_by_page = {item["physical_page"]: item for item in dimensions}
    parsed_pages = []
    for value_page in raw_pages:
        if type(value_page) is not dict or set(value_page) != _PAGE_FIELDS:
            raise _error("selected snapshot joined-page fields drifted")
        page_sequence = _positive_int(value_page["page_sequence"], "page sequence")
        dimension = dimension_by_page.get(page_sequence)
        if dimension is None or value_page["page_width"] != dimension["pixel_width"]:
            raise _error("selected snapshot page dimension binding drifted")
        if type(value_page["lines"]) is not list:
            raise _error("selected snapshot line axis drifted")
        parsed_lines = [
            _line(
                item,
                width=dimension["pixel_width"],
                height=dimension["pixel_height"],
            )
            for item in value_page["lines"]
        ]
        parsed_lines.sort(key=lambda item: (item["line_ordinal"], item["sample_id"]))
        indices = [item["line_ordinal"] for item in parsed_lines]
        if indices != list(range(len(indices))):
            raise _error("selected snapshot line ordinals are not exact and contiguous")
        parsed_pages.append(
            {
                "lines": parsed_lines,
                "page_sequence": page_sequence,
                "page_width": dimension["pixel_width"],
            }
        )
    parsed_pages.sort(key=lambda item: item["page_sequence"])
    page_ids = [item["page_sequence"] for item in parsed_pages]
    if page_ids != dimension_ids:
        raise _error("selected snapshot joined-page and dimension axes differ")
    sample_ids = [line["sample_id"] for page in parsed_pages for line in page["lines"]]
    if len(sample_ids) != len(set(sample_ids)) or len(sample_ids) > packet["line_count"]:
        raise _error("selected snapshot sample or line denominator drifted")
    selection_material = {
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "joined_pages": parsed_pages,
        "selected_page_dimensions": dimensions,
    }
    if selection_id != "ffoqcv1:selection:" + canonical_json_sha256_v1(selection_material):
        raise _error("selected snapshot query selection content identity drifted")
    snapshot_material = {
        "document_packet": packet,
        "joined_pages": parsed_pages,
        "manifest_id": manifest_id,
        "query_selection_id": selection_id,
        "selected_page_dimensions": dimensions,
        "state": value["state"],
    }
    if snapshot_id != "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material):
        raise _error("selected snapshot content identity drifted")
    return {**snapshot_material, "snapshot_id": snapshot_id}


def _build(selected_snapshot: Any) -> dict[str, Any]:
    snapshot = _canonical_snapshot(selected_snapshot)
    dimensions = {item["physical_page"]: item for item in snapshot["selected_page_dimensions"]}
    region_pages = []
    page_bindings = []
    line_bindings = []
    for page in snapshot["joined_pages"]:
        page_sequence = page["page_sequence"]
        dimension = dimensions[page_sequence]
        region_lines = []
        for line in page["lines"]:
            numeric = line["numeric_recognition"]
            region_lines.append(
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": line["numeric_recognition"]["raw_prediction"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
            line_bindings.append(
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "crop_ref": canonical_clone_v1(line["crop_ref"]),
                    "page_sequence": page_sequence,
                    "ppocrv6_reader_score": numeric["reader_score"],
                    "ppocrv6_surface": numeric["raw_prediction"],
                    "sample_id": line["sample_id"],
                    "source_line_index": line["line_ordinal"],
                    "vietocr_transformer_surface": line["vietocr_text"],
                }
            )
        region_pages.append(
            {
                "lines": region_lines,
                "page_height": dimension["pixel_height"],
                "page_sequence": page_sequence,
                "page_width": dimension["pixel_width"],
            }
        )
        page_bindings.append(
            {
                "line_count": len(region_lines),
                "page_height": dimension["pixel_height"],
                "page_sequence": page_sequence,
                "page_width": dimension["pixel_width"],
                "render_ref": {
                    "sha256": dimension["render_sha256"],
                    "size_bytes": dimension["render_size_bytes"],
                },
            }
        )
    packet = snapshot["document_packet"]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "line_bindings": line_bindings,
        "metrics": {
            "line_count": len(line_bindings),
            "page_count": len(region_pages),
            "zero_line_page_count": sum(not page["lines"] for page in region_pages),
        },
        "page_bindings": page_bindings,
        "region_pages": region_pages,
        "source_binding": {
            "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
            "document_id": packet["document_id"],
            "document_line_count": packet["line_count"],
            "document_ordinal": packet["document_ordinal"],
            "document_packet_id": packet["packet_id"],
            "document_page_count": packet["page_count"],
            "manifest_id": snapshot["manifest_id"],
            "query_selection_id": snapshot["query_selection_id"],
            "selected_pages": [page["page_sequence"] for page in region_pages],
            "snapshot_id": snapshot["snapshot_id"],
        },
        "state": "CALLER_AUTHENTICATED_SELECTED_SNAPSHOT_PROJECTED_FOR_SEMANTIC_GRAPH",
    }
    return {
        **material,
        "projection_id": "asrsv1:projection:" + canonical_json_sha256_v1(material),
    }


def _receipt_content_ref_shape(value: Any) -> bool:
    return (
        type(value) is dict
        and set(value) == _CONTENT_REF_FIELDS
        and type(value["path"]) is str
        and bool(value["path"])
        and not Path(value["path"]).is_absolute()
        and ".." not in Path(value["path"]).parts
        and type(value["sha256"]) is str
        and _SHA256.fullmatch(value["sha256"]) is not None
        and type(value["size_bytes"]) is int
        and value["size_bytes"] > 0
    )


def validate_family_first_region_retrieval_receipt_v2(
    value: Any,
    expected_query_spec: Mapping[str, Any],
    expected_family_id: str,
) -> dict[str, Any]:
    """Validate generic V2 receipt identity without granting authentication."""

    fields = {
        "authority",
        "claim_boundary",
        "documents",
        "family_id",
        "format_version",
        "metrics",
        "planner",
        "query_spec",
        "receipt_id",
        "source_binding",
        "state",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or type(expected_family_id) is not str
        or not expected_family_id
    ):
        raise _receipt_error("region retrieval receipt fields drifted")
    from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
        family_first_region_query_spec_id_v2,
        validate_family_first_region_query_spec_v2,
    )

    try:
        query = validate_family_first_region_query_spec_v2(expected_query_spec)
        query_id = family_first_region_query_spec_id_v2(query)
    except ValueError as error:
        raise _receipt_error("expected region query spec drifted") from error
    metrics = value["metrics"]
    planner = value["planner"]
    source = value["source_binding"]
    if (
        value["family_id"] != expected_family_id
        or value["format_version"] != "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2"
        or value["state"] != "DIRECT_RECOMPUTED_COMPLETE_DOCUMENT_REGION_SHORTLIST"
        or value["claim_boundary"] != _RETRIEVAL_CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _RETRIEVAL_AUTHORITY)
        or not same_typed_json_v1(value["query_spec"], query)
        or type(value["documents"]) is not list
        or not value["documents"]
        or type(metrics) is not dict
        or set(metrics) != _RETRIEVAL_METRIC_FIELDS
        or any(type(item) is not int or item < 0 for item in metrics.values())
        or metrics["document_count"] != len(value["documents"])
        or type(planner) is not dict
        or set(planner)
        != {
            "anchor_statistics",
            "historical_variant_support_verifications",
            "seed_anchor_ids",
            "strategy",
        }
        or type(planner["anchor_statistics"]) is not list
        or type(planner["historical_variant_support_verifications"]) is not list
        or type(planner["seed_anchor_ids"]) is not list
        or planner["strategy"]
        != "DECLARATIVE_ALL_SATISFIED_SEED_GROUP_COVERAGE_THEN_LOCAL_VALIDATION"
        or type(source) is not dict
        or set(source)
        != {
            "database_ref",
            "engine_ref",
            "manifest_id",
            "query_spec_id",
            "runtime_determinants",
        }
        or not _receipt_content_ref_shape(source["database_ref"])
        or not _receipt_content_ref_shape(source["engine_ref"])
        or type(source["manifest_id"]) is not str
        or not source["manifest_id"]
        or source["query_spec_id"] != query_id
        or type(source["runtime_determinants"]) is not dict
    ):
        raise _receipt_error("region retrieval receipt identity drifted")
    expected_seed_ids = sorted(
        {anchor_id for group in query["seed_groups"] for anchor_id in group["anchor_ids"]}
    )
    if planner["seed_anchor_ids"] != expected_seed_ids:
        raise _receipt_error("region retrieval receipt query binding drifted")
    derived = {
        "fallback_document_count": 0,
        "occurrence_count": 0,
        "selected_page_count": 0,
        "source_line_count": 0,
        "source_page_count": 0,
        "zero_validated_hit_document_count": 0,
    }
    for ordinal, outcome in enumerate(value["documents"], 1):
        if (
            type(outcome) is not dict
            or outcome.get("document_ordinal") != ordinal
            or outcome.get("coverage_status") != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
            or type(outcome.get("selected_pages")) is not list
            or not outcome["selected_pages"]
            or outcome["selected_pages"] != sorted(set(outcome["selected_pages"]))
            or any(type(page) is not int or page <= 0 for page in outcome["selected_pages"])
            or type(outcome.get("local_occurrences")) is not list
            or type(outcome.get("seed_occurrences")) is not list
            or type(outcome.get("blocked_expansions")) is not list
            or type(outcome.get("structural_reset_pages")) is not list
            or type(outcome.get("document_line_count")) is not int
            or outcome["document_line_count"] < 0
            or type(outcome.get("document_page_count")) is not int
            or outcome["document_page_count"] <= 0
            or type(outcome.get("requires_full_document_review")) is not bool
            or type(outcome.get("selection_mode")) is not str
            or type(outcome.get("index_outcome")) is not str
        ):
            raise _receipt_error("region retrieval outcome identity drifted")
        outcome_material = canonical_clone_v1(outcome)
        outcome_id = outcome_material.pop("outcome_id", None)
        if outcome_id != "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material):
            raise _receipt_error("region retrieval outcome content identity drifted")
        derived["fallback_document_count"] += outcome["selection_mode"].startswith(
            "FULL_DOCUMENT_FALLBACK"
        )
        derived["occurrence_count"] += len(outcome["local_occurrences"])
        derived["selected_page_count"] += len(outcome["selected_pages"])
        derived["source_line_count"] += outcome["document_line_count"]
        derived["source_page_count"] += outcome["document_page_count"]
        derived["zero_validated_hit_document_count"] += (
            outcome["index_outcome"] == "ZERO_VALID_SEED_GROUP"
        )
    if any(metrics[key] != count for key, count in derived.items()):
        raise _receipt_error("region retrieval receipt derived metrics drifted")
    receipt_material = canonical_clone_v1(value)
    receipt_id = receipt_material.pop("receipt_id", None)
    if receipt_id != "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material):
        raise _receipt_error("region retrieval receipt content identity drifted")
    return canonical_clone_v1(value)


def build_authenticated_semantic_region_snapshot_v1(
    selected_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one caller-authenticated selected snapshot into graph input."""

    return _build(selected_snapshot)


def validate_authenticated_semantic_region_snapshot_replay_v1(
    value: Any,
    selected_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild one selected-snapshot projection and compare it exactly."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("semantic-region snapshot projection identity drifted")
    material = canonical_clone_v1(value)
    projection_id = material.pop("projection_id", None)
    if projection_id != "asrsv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("semantic-region snapshot projection content identity drifted")
    rebuilt = _build(selected_snapshot)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("semantic-region snapshot projection does not replay exactly")
    return rebuilt
