"""Strict adapter from fixed eight-PDF VietOCR caches to family scanners.

Each cache is a semantic proposal axis, never numeric or mapping authority.
This module selects one closed denominator from the source format version,
validates its exact sample order, geometry shapes, and recomputed semantic-axis
digest, then projects the same bank-blind page/line contract to every accounting
family.  A separate projection derives one document-wide reporting-period
context from those same authenticated lines without changing the stable family
axis identity. Document codes remain provenance only and are not exposed inside
match lines.
"""

from __future__ import annotations

import math
import re
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    infer_document_reporting_period_context_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "EXPECTED_DOCUMENT_ORDER",
    "FORMAT_VERSION",
    "FullDocumentVietOCRAccountingAxisV1Error",
    "project_full_document_vietocr_accounting_axis_v1",
    "project_full_document_vietocr_reporting_period_contexts_v1",
    "validate_full_document_vietocr_accounting_axis_replay_v1",
    "validate_full_document_vietocr_reporting_period_contexts_replay_v1",
]


FORMAT_VERSION = "FULL_DOCUMENT_VIETOCR_ACCOUNTING_FAMILY_AXIS_V1"
SOURCE_FORMAT_VERSION = "WAVE1_8DOCUMENT_VIETOCR_TRANSFORMER_SEMANTIC_INDEX_V1"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
EXPECTED_PAGE_VECTOR = (33, 61, 91, 44, 55, 61, 37, 71)
EXPECTED_LINE_VECTOR = (2489, 4592, 6942, 3359, 4356, 4047, 3046, 5510)
EXPECTED_PAGE_COUNT = sum(EXPECTED_PAGE_VECTOR)
EXPECTED_SAMPLE_COUNT = sum(EXPECTED_LINE_VECTOR)
_SOURCE_PROFILES = {
    SOURCE_FORMAT_VERSION: {
        "line_vector": EXPECTED_LINE_VECTOR,
        "page_vector": EXPECTED_PAGE_VECTOR,
    },
}
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_FRESH_VIETOCR_TRANSFORMER_ORDERED_TEXT_AND_PIXEL_BBOX_"
    "PROJECTION_ONLY_NO_SOURCE_TRANSCRIPT_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accentless_text_is_anchor_evidence_only": True,
    "all_empty_predictions_preserved": True,
    "bank_identity_exposed_inside_family_match_lines": False,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ppocr_or_native_transcript_used_as_semantic_text": False,
    "ordered_semantic_proposal_authority": True,
    "persisted_projection_self_authenticating": False,
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
}
_SOURCE_AUTHORITY = {
    "all_empty_predictions_preserved": True,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ppocr_or_native_transcript_used_as_semantic_text": False,
    "ordered_semantic_proposal_authority": True,
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAMPLE_ID = re.compile(r"^sample-([0-9]{8})$")


class FullDocumentVietOCRAccountingAxisV1Error(ValueError):
    """The fixed semantic cache denominator, order, or content drifted."""


def _error(message: str) -> FullDocumentVietOCRAccountingAxisV1Error:
    return FullDocumentVietOCRAccountingAxisV1Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one non-negative integer")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _error(f"{label} SHA-256 drifted")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} bbox drifted")
    return list(value)


def _ref(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}:
        raise _error(f"{label} content ref fields drifted")
    if (
        type(value["path"]) is not str
        or not value["path"]
        or value["path"].startswith("/")
        or ".." in value["path"].split("/")
    ):
        raise _error(f"{label} content ref path drifted")
    _sha256(value["sha256"], label)
    _positive_int(value["size_bytes"], f"{label} size")
    return canonical_clone_v1(value)


def _source_pdf_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}:
        raise _error("semantic index source PDF ref fields drifted")
    return _ref(value, "semantic index source PDF")


def _source_profile(format_version: Any) -> dict[str, tuple[int, ...]]:
    if type(format_version) is not str or format_version not in _SOURCE_PROFILES:
        raise _error("full-document VietOCR semantic index format is not admitted")
    return _SOURCE_PROFILES[format_version]


def _projection_profile(metrics: Any) -> dict[str, tuple[int, ...]]:
    if type(metrics) is not dict:
        raise _error("full-document accounting axis projection metrics drifted")
    matches = []
    for profile in _SOURCE_PROFILES.values():
        page_vector = profile["page_vector"]
        line_vector = profile["line_vector"]
        expected = {
            "document_count": len(EXPECTED_DOCUMENT_ORDER),
            "line_count_vector": list(line_vector),
            "page_count": sum(page_vector),
            "page_count_vector": list(page_vector),
            "sample_count": sum(line_vector),
        }
        if same_typed_json_v1(metrics, expected):
            matches.append(profile)
    if len(matches) != 1:
        raise _error("full-document accounting axis projection metrics drifted")
    return matches[0]


def _source_index(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "authority",
        "documents",
        "format_version",
        "input_refs",
        "metrics",
        "reader",
        "state",
    }:
        raise _error("full-document VietOCR semantic index fields drifted")
    profile = _source_profile(value["format_version"])
    expected_page_vector = profile["page_vector"]
    expected_line_vector = profile["line_vector"]
    expected_page_count = sum(expected_page_vector)
    expected_sample_count = sum(expected_line_vector)
    expected_state = "VERIFIED_COMPLETE_ORDERED_VIETOCR_TRANSFORMER_PROPOSALS"
    if value["state"] != expected_state or not same_typed_json_v1(
        value["authority"], _SOURCE_AUTHORITY
    ):
        raise _error("full-document VietOCR semantic index identity/authority drifted")
    if type(value["input_refs"]) is not dict or set(value["input_refs"]) != {
        "crop_manifest",
        "ocr_result",
        "reader_request",
        "run_manifest",
    }:
        raise _error("full-document VietOCR input refs drifted")
    input_refs = {
        key: _ref(value["input_refs"][key], f"VietOCR input {key}")
        for key in sorted(value["input_refs"])
    }
    if type(value["reader"]) is not dict:
        raise _error("full-document VietOCR reader record drifted")

    documents = value["documents"]
    if type(documents) is not list or len(documents) != len(EXPECTED_DOCUMENT_ORDER):
        raise _error("full-document VietOCR document denominator drifted")
    projected_documents: list[dict[str, Any]] = []
    semantic_axis: list[dict[str, str]] = []
    page_vector: list[int] = []
    line_vector: list[int] = []
    global_sample_ordinal = 0
    empty_prediction_count = 0
    terminal_page_count = 0
    for document_ordinal, (raw_document, expected_code) in enumerate(
        zip(documents, EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(raw_document) is not dict or set(raw_document) != {
            "bank_code",
            "document_ordinal",
            "page_count",
            "pages",
            "source_pdf",
        }:
            raise _error("full-document VietOCR document fields drifted")
        if (
            type(raw_document["bank_code"]) is not str
            or type(raw_document["document_ordinal"]) is not int
            or raw_document["bank_code"] != expected_code
            or raw_document["document_ordinal"] != document_ordinal
        ):
            raise _error("full-document VietOCR provenance order drifted")
        pages = raw_document["pages"]
        page_count = _positive_int(raw_document["page_count"], "document page count")
        if (
            page_count != expected_page_vector[document_ordinal - 1]
            or type(pages) is not list
            or len(pages) != page_count
        ):
            raise _error("full-document VietOCR page denominator drifted")
        projected_pages: list[dict[str, Any]] = []
        document_line_count = 0
        for physical_page, raw_page in enumerate(pages, 1):
            if type(raw_page) is not dict or set(raw_page) != {
                "geometry_mode",
                "line_count",
                "lines",
                "physical_page",
                "route",
                "source_projection",
                "terminal_status_preserved",
                "upstream_status",
            }:
                raise _error("full-document VietOCR page fields drifted")
            if (
                type(raw_page["physical_page"]) is not int
                or raw_page["physical_page"] != physical_page
                or type(raw_page["terminal_status_preserved"]) is not bool
                or type(raw_page["geometry_mode"]) is not str
                or not raw_page["geometry_mode"]
                or type(raw_page["route"]) is not str
                or not raw_page["route"]
                or type(raw_page["upstream_status"]) is not str
                or not raw_page["upstream_status"]
                or type(raw_page["source_projection"]) is not dict
            ):
                raise _error("full-document VietOCR page identity/state drifted")
            terminal_page_count += raw_page["terminal_status_preserved"]
            lines = raw_page["lines"]
            line_count = _nonnegative_int(raw_page["line_count"], "page line count")
            if type(lines) is not list or len(lines) != line_count:
                raise _error("full-document VietOCR page line denominator drifted")
            projected_lines: list[dict[str, Any]] = []
            for line_index, raw_line in enumerate(lines):
                if type(raw_line) is not dict or set(raw_line) != {
                    "crop_ref",
                    "line_axis_role",
                    "mean_decoded_character_probability",
                    "padded_source_bbox_raw_pixels",
                    "processed_height",
                    "processed_width",
                    "sample_id",
                    "source_bbox_raw_pixels",
                    "source_line_index",
                    "vietocr_text",
                }:
                    raise _error("full-document VietOCR line fields drifted")
                global_sample_ordinal += 1
                matched_sample = (
                    _SAMPLE_ID.fullmatch(raw_line["sample_id"])
                    if type(raw_line["sample_id"]) is str
                    else None
                )
                probability = raw_line["mean_decoded_character_probability"]
                if (
                    type(raw_line["source_line_index"]) is not int
                    or raw_line["source_line_index"] != line_index
                    or matched_sample is None
                    or int(matched_sample.group(1)) != global_sample_ordinal
                    or type(raw_line["line_axis_role"]) is not str
                    or not raw_line["line_axis_role"]
                    or type(raw_line["vietocr_text"]) is not str
                    or (
                        probability is not None
                        and (
                            type(probability) not in {int, float}
                            or not math.isfinite(probability)
                            or not 0 <= probability <= 1
                        )
                    )
                ):
                    raise _error("full-document VietOCR line identity/text/probability drifted")
                _positive_int(raw_line["processed_height"], "processed crop height")
                _positive_int(raw_line["processed_width"], "processed crop width")
                _ref(raw_line["crop_ref"], "full-document VietOCR crop")
                bbox = _bbox(raw_line["source_bbox_raw_pixels"], "source line")
                _bbox(raw_line["padded_source_bbox_raw_pixels"], "padded source line")
                semantic_axis.append(
                    {
                        "sample_id": raw_line["sample_id"],
                        "vietocr_text": raw_line["vietocr_text"],
                    }
                )
                empty_prediction_count += raw_line["vietocr_text"] == ""
                projected_lines.append(
                    {
                        "bbox": bbox,
                        "source_line_index": line_index,
                        "source_text": None,
                        "vietocr_text": raw_line["vietocr_text"],
                        "vietocr_text_accentless": normalize_vietnamese_anchor_v1(
                            raw_line["vietocr_text"]
                        ),
                    }
                )
            document_line_count += line_count
            projected_pages.append(
                {
                    "lines": projected_lines,
                    "page_sequence": physical_page,
                    "primary_numeric_authority": False,
                }
            )
        if document_line_count != expected_line_vector[document_ordinal - 1]:
            raise _error("full-document VietOCR document line denominator drifted")
        page_vector.append(page_count)
        line_vector.append(document_line_count)
        projected_documents.append(
            {
                "document_ordinal": document_ordinal,
                "document_provenance": expected_code,
                "pages": projected_pages,
                "source_pdf": _source_pdf_ref(raw_document["source_pdf"]),
            }
        )

    metrics = value["metrics"]
    if type(metrics) is not dict or set(metrics) != {
        "document_count",
        "empty_prediction_count",
        "line_count_vector",
        "page_count",
        "page_count_vector",
        "sample_count",
        "semantic_axis_sha256",
        "terminal_page_count",
    }:
        raise _error("full-document VietOCR semantic index metric fields drifted")
    if (
        type(metrics["document_count"]) is not int
        or metrics["document_count"] != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(metrics["page_count_vector"], list(expected_page_vector))
        or not same_typed_json_v1(metrics["line_count_vector"], list(expected_line_vector))
        or type(metrics["page_count"]) is not int
        or metrics["page_count"] != expected_page_count
        or type(metrics["sample_count"]) is not int
        or metrics["sample_count"] != expected_sample_count
        or global_sample_ordinal != expected_sample_count
        or type(metrics["empty_prediction_count"]) is not int
        or metrics["empty_prediction_count"] != empty_prediction_count
        or type(metrics["terminal_page_count"]) is not int
        or metrics["terminal_page_count"] != terminal_page_count
    ):
        raise _error("full-document VietOCR semantic index fixed metrics drifted")
    semantic_axis_sha256 = canonical_json_sha256_v1(semantic_axis)
    if metrics["semantic_axis_sha256"] != semantic_axis_sha256:
        raise _error("full-document VietOCR semantic axis digest drifted")
    return {
        "documents": projected_documents,
        "input_refs": input_refs,
        "profile": profile,
        "semantic_axis_sha256": semantic_axis_sha256,
        "source_index_sha256": canonical_json_sha256_v1(value),
    }


def _validate_projection(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "authority",
        "claim_boundary",
        "documents",
        "format_version",
        "input_refs",
        "metrics",
        "projection_id",
        "semantic_axis_sha256",
        "source_index_sha256",
    }:
        raise _error("full-document accounting axis projection fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["documents"]) is not list
        or len(value["documents"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("full-document accounting axis projection identity drifted")
    _sha256(value["semantic_axis_sha256"], "accounting semantic axis")
    _sha256(value["source_index_sha256"], "source semantic index")
    _projection_profile(value["metrics"])
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if identity != "fdvaav1:projection:" + canonical_json_sha256_v1(material):
        raise _error("full-document accounting axis projection ID drifted")
    return canonical_clone_v1(value)


def project_full_document_vietocr_accounting_axis_v1(value: Any) -> dict[str, Any]:
    """Project the one fixed semantic cache into family-neutral page records."""

    source = _source_index(value)
    profile = source["profile"]
    page_vector = profile["page_vector"]
    line_vector = profile["line_vector"]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": source["documents"],
        "format_version": FORMAT_VERSION,
        "input_refs": source["input_refs"],
        "metrics": {
            "document_count": len(EXPECTED_DOCUMENT_ORDER),
            "line_count_vector": list(line_vector),
            "page_count": sum(page_vector),
            "page_count_vector": list(page_vector),
            "sample_count": sum(line_vector),
        },
        "semantic_axis_sha256": source["semantic_axis_sha256"],
        "source_index_sha256": source["source_index_sha256"],
    }
    return _validate_projection(
        {
            **material,
            "projection_id": "fdvaav1:projection:" + canonical_json_sha256_v1(material),
        }
    )


def validate_full_document_vietocr_accounting_axis_replay_v1(
    value: Any, source_semantic_index: Any
) -> dict[str, Any]:
    """Exact-rebuild the family-neutral axis from the verified source index."""

    persisted = _validate_projection(value)
    rebuilt = project_full_document_vietocr_accounting_axis_v1(source_semantic_index)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("full-document accounting axis does not replay exactly")
    return rebuilt


_PERIOD_CONTEXT_FORMAT_VERSION = "FULL_DOCUMENT_VIETOCR_REPORTING_PERIOD_CONTEXTS_V1"
_PERIOD_CONTEXT_CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_REPEATED_DATE_"
    "REPORTING_PERIOD_CONTEXT_PROPOSAL_ONLY_LOCAL_TABLE_SEMANTICS_STILL_REQUIRED_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_PERIOD_CONTEXT_AUTHORITY = {
    "bank_filename_note_or_page_used_for_period_inference": False,
    "complete_document_date_consensus_required": True,
    "local_table_period_semantics_still_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_projection_self_authenticating": False,
    "reporting_period_context_is_proposal_only": True,
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
}
_PERIOD_CONTEXT_KEYS = {
    "balance_comparative_period_end",
    "current_period_end",
    "current_period_start",
    "flow_comparative_period_end",
    "flow_comparative_period_start",
    "observed_dates",
    "period_kind",
    "reporting_year",
    "resolution",
    "supporting_page_count",
}


def _validate_period_context_projection(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "authority",
        "claim_boundary",
        "contexts",
        "format_version",
        "projection_id",
        "semantic_axis_sha256",
        "source_index_sha256",
    }:
        raise _error("full-document reporting-period projection fields drifted")
    if (
        value["format_version"] != _PERIOD_CONTEXT_FORMAT_VERSION
        or value["claim_boundary"] != _PERIOD_CONTEXT_CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _PERIOD_CONTEXT_AUTHORITY)
        or type(value["contexts"]) is not list
        or len(value["contexts"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("full-document reporting-period projection identity drifted")
    _sha256(value["semantic_axis_sha256"], "period-context semantic axis")
    _sha256(value["source_index_sha256"], "period-context source index")
    for ordinal, (record, expected_code) in enumerate(
        zip(value["contexts"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(record) is not dict or set(record) != {
            "document_ordinal",
            "document_provenance",
            "reporting_period_context",
            "source_pdf_sha256",
        }:
            raise _error("document reporting-period record fields drifted")
        context = record["reporting_period_context"]
        if (
            type(record["document_ordinal"]) is not int
            or record["document_ordinal"] != ordinal
            or record["document_provenance"] != expected_code
            or type(context) is not dict
            or set(context) != _PERIOD_CONTEXT_KEYS
            or type(context["observed_dates"]) is not list
            or type(context["supporting_page_count"]) is not int
            or context["supporting_page_count"] < 0
        ):
            raise _error("document reporting-period record identity drifted")
        _sha256(record["source_pdf_sha256"], "period-context source PDF")
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if identity != "fdvrpcv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("full-document reporting-period projection ID drifted")
    return canonical_clone_v1(value)


def project_full_document_vietocr_reporting_period_contexts_v1(value: Any) -> dict[str, Any]:
    """Derive one complete-PDF period context per authenticated document."""

    source = _source_index(value)
    material = {
        "authority": canonical_clone_v1(_PERIOD_CONTEXT_AUTHORITY),
        "claim_boundary": _PERIOD_CONTEXT_CLAIM_BOUNDARY,
        "contexts": [
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "reporting_period_context": infer_document_reporting_period_context_v1(
                    document["pages"]
                ),
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
            for document in source["documents"]
        ],
        "format_version": _PERIOD_CONTEXT_FORMAT_VERSION,
        "semantic_axis_sha256": source["semantic_axis_sha256"],
        "source_index_sha256": source["source_index_sha256"],
    }
    return _validate_period_context_projection(
        {
            **material,
            "projection_id": "fdvrpcv1:projection:" + canonical_json_sha256_v1(material),
        }
    )


def validate_full_document_vietocr_reporting_period_contexts_replay_v1(
    value: Any, source_semantic_index: Any
) -> dict[str, Any]:
    """Exact-rebuild all period contexts from the authenticated text axis."""

    persisted = _validate_period_context_projection(value)
    rebuilt = project_full_document_vietocr_reporting_period_contexts_v1(source_semantic_index)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("full-document reporting-period contexts do not replay exactly")
    return rebuilt
