"""Add-only contracts for projecting finalized full-reader V3 evidence.

V1 remains byte-frozen.  V2 wraps one validated V1 neutral atom projection with
the exact Full Page Record V2/result identities and the complete native V2
coordinate/order authority that V1 deliberately did not admit.  The wrapper is
still source evidence only: it cannot claim a statement, table, row, cell,
axis, value, hierarchy, mapping, blank, or absence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    SOURCE_STRUCTURE_SAFETY_V1,
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    make_empty_page_proposal_set_v1,
    same_typed_json_v1,
    validate_neutral_page_envelope_v1,
    validate_page_proposal_set_v1,
)

__all__ = [
    "PAGE_PROPOSAL_CLAIM_BOUNDARY_V2",
    "PAGE_PROPOSAL_FORMAT_VERSION_V2",
    "SOURCE_PROJECTION_CLAIM_BOUNDARY_V2",
    "SOURCE_PROJECTION_FORMAT_VERSION_V2",
    "SOURCE_PROJECTION_SAFETY_V2",
    "SourceStructureContractV2Error",
    "make_empty_page_proposal_set_v2",
    "make_page_proposal_set_v2",
    "validate_full_page_record_v2",
    "validate_page_proposal_set_v2",
    "validate_source_evidence_projection_v2",
]


class SourceStructureContractV2Error(ValueError):
    """A Full Page Record V2 projection crossed its closed boundary."""


SOURCE_PROJECTION_FORMAT_VERSION_V2 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_NEUTRAL_SOURCE_EVIDENCE_PROJECTION_V2"
)
SOURCE_PROJECTION_CLAIM_BOUNDARY_V2 = (
    "EXACT_FULL_PAGE_RECORD_V2_SOURCE_TEXT_GEOMETRY_AND_ORDER_EVIDENCE_ONLY_NO_SEMANTIC_PROMOTION"
)
PAGE_PROPOSAL_FORMAT_VERSION_V2 = "BANK_CORPUS_WAVE_1_ROLE_B_SOURCE_GEOMETRY_PROPOSAL_PROJECTION_V2"
PAGE_PROPOSAL_CLAIM_BOUNDARY_V2 = (
    "VALIDATED_V1_SOURCE_LOCAL_GEOMETRY_PROPOSALS_ONLY_NO_SEMANTIC_PROMOTION"
)

SOURCE_PROJECTION_SAFETY_V2: dict[str, bool] = {
    **SOURCE_STRUCTURE_SAFETY_V1,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "note_number_rules_used_for_routing": False,
    "network_used": False,
    "ocr_or_native_provider_invoked": False,
    "role_a_used_for_routing": False,
    "schema_used_for_routing": False,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_OBJECT_PATH_RE = re.compile(
    r"^objects/sha256/(?P<prefix>[0-9a-f]{2})/(?P<digest>[0-9a-f]{64})"
    r"(?P<suffix>\.json|\.png)$"
)
_PROJECTION_FIELDS = {
    "format_version",
    "claim_boundary",
    "source_local_page_id",
    "source_locator",
    "route",
    "upstream_status",
    "terminal",
    "terminal_reason",
    "page_record_format_version",
    "page_record_v2",
    "page_record_sha256",
    "page_result_format_version",
    "page_result",
    "page_result_ref",
    "page_result_sha256",
    "page_record_accounting",
    "coordinate_authority",
    "native_ordering_policy_identity",
    "native_ordering_policy_identity_sha256",
    "native_ordering_receipt",
    "native_ordering_receipt_sha256",
    "v1_compatibility_disposition",
    "v1_compatibility_view_authoritative",
    "neutral_page_v1",
    "neutral_page_v1_sha256",
    "safety",
}
_PROPOSAL_FIELDS = {
    "format_version",
    "claim_boundary",
    "source_local_page_id",
    "source_projection_sha256",
    "neutral_page_v1_sha256",
    "proposal_set_v1",
    "safety",
}
_SOURCE_LOCATOR_FIELDS = {
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "request_sha256",
}
_OBJECT_REF_FIELDS = {"path", "sha256", "size_bytes"}
_PAGE_RECORD_ACCOUNTING_FIELDS = {
    "line_axis_count",
    "nonempty_line_axis_count",
    "exact_empty_line_axis_count",
    "accepted_line_count",
    "word_token_count",
    "quarantined_span_count",
    "ordering_quarantined_raw_line_run_count",
    "ordering_quarantined_raw_word_count",
    "noncontiguous_line_identity_count",
    "word_box_correction_count",
    "word_box_corrected_edge_count",
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
}
_PAGE_RECORD_V2_FIELDS = {
    "format_version",
    "request_ordinal",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "status",
    "origin",
    "upstream_status",
    "upstream_origin",
    "upstream_unresolved",
    "render_ref",
    "backend_payload_ref",
    "result_ref",
    "upstream_v2_adoption",
    *_PAGE_RECORD_ACCOUNTING_FIELDS,
    "unresolved",
}
_REQUEST_FIELDS = {
    "format_version",
    "git_commit",
    "implementation_ledger_sha256",
    "input_ledger_sha256",
    "selection_receipt_sha256",
    "sentinel_sha256",
    "route_plan_sha256",
    "pre_ocr_feature_fingerprint_sha256",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "render_specification",
    "bank_identity_used",
    "filename_used",
    "role_a_used",
    "schema_used",
    "historical_values_used",
}
_REQUEST_FALSE_FIELDS = {
    "bank_identity_used",
    "filename_used",
    "role_a_used",
    "schema_used",
    "historical_values_used",
}
_RENDER_SPECIFICATION_FIELDS = {
    "dpi",
    "colorspace",
    "alpha",
    "annotations",
    "source",
}
_ADOPTION_FIELDS = {
    "format_version",
    "incident_identity_sha256",
    "archive_portable_manifest_sha256",
    "archive_live_manifest_sha256",
    "source_control_identity_sha256",
    "source_checkpoint_sha256",
    "source_checkpoint_size_bytes",
    "source_checkpoint_generation",
    "source_page_record_sha256",
    "source_status",
    "source_origin",
    "source_unresolved",
    "source_refs",
    "copy_semantics",
    "source_checkpoint_or_page_record_relabelled",
    "destination_control_identity_sha256",
}
_ADOPTION_REF_FIELDS = {"render_ref", "backend_payload_ref", "result_ref"}
_OCR_RESULT_V2_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "request_sha256",
    "request",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "input_render_ref",
    "backend_payload_ref",
    "word_box_normalization_ledger",
    "coordinate_authority",
    "lines",
    "words",
    "metrics",
    "source_blank_claimed",
    "safety",
}
_OCR_RESULT_V3_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "request_sha256",
    "request",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "input_render_ref",
    "backend_payload_ref",
    "normalization_failure",
    "coordinate_authority",
    "lines",
    "words",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_NATIVE_RESULT_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "full_control_identity_sha256",
    "provider_identity_sha256",
    "backend_payload_sha256",
    "ordering_policy_identity",
    "coordinate_authority",
    "failure_type",
    "native_text_quality",
    "corruption_markers",
    "lines",
    "words",
    "quarantined_spans",
    "ordering_receipt",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_UPSTREAM_SAFETY_FIELDS = {
    "statement_classified",
    "table_classified",
    "rows_reconstructed",
    "cells_interpreted",
    "absence_claimed",
    "bank_registry_metadata_used",
    "filename_metadata_used",
    "role_a_used",
    "schema_used",
    "mapping_used",
    "historical_values_used",
}
_NATIVE_RESULT_SAFETY_FIELDS = {
    *_UPSTREAM_SAFETY_FIELDS,
    "ocr_fallback_used",
    "network_used",
}
_ZERO_INTERPRETATION_FIELDS = {
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
}
_NATIVE_COORDINATE_FIELDS = {
    "canonical_coordinate_system",
    "coordinate_unit",
    "geometry_source",
    "pdf_rotation_applied_to_coordinates",
    "pdf_rotation_degrees",
    "canonical_cropbox_bounds_mpt",
    "source_cropbox_mpt",
    "source_mediabox_mpt",
}
_NATIVE_AUTHORITY_V1 = {
    "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
    "coordinate_unit": "MILLI_POINT",
    "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
    "pdf_rotation_applied_to_coordinates": False,
}
_OCR_RESULT_FORMATS = {
    "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
    "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
}
_NATIVE_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
_NATIVE_CONTIGUITY_STATUS = "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY"
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_OCR_COMPLETE = "OCR_WORD_BOX_READ_COMPLETE"
_OCR_TERMINAL = "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
_NATIVE_COMPLETE = "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
_NATIVE_STATUSES = {
    _NATIVE_COMPLETE,
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
    "UNRESOLVED_NATIVE_TEXT_QUALITY",
    _NATIVE_CONTIGUITY_STATUS,
}
_OCR_UPSTREAM_ORIGINS = {
    "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
    "PINNED_PPOCRV6_FULL_READER",
}
_ORDERING_POLICY_IDENTITY = {
    "path": "config/ocr/causal-native-text-evidence-v2.yaml",
    "sha256": "ec249629e83944f03d25b30d5df29ddfbcd9bc250b06d3ed9cc6d60e2533c309",
    "size_bytes": 1_305,
}
_ORDERING_RECEIPT_FIELDS = {
    "format_version",
    "policy",
    "ordering_policy_identity",
    "source_word_order",
    "line_projection",
    "status",
    "source_word_count",
    "line_run_count",
    "distinct_line_identity_count",
    "noncontiguous_line_identity_count",
    "source_words_sha256",
    "line_runs_sha256",
    "noncontiguous_line_identities_sha256",
}
_IDENTITY_DISPOSITION = "IDENTITY_PRESERVING_V1_NEUTRAL_ATOM_PROJECTION"
_CONTIGUITY_DISPOSITION = (
    "NATIVE_LINE_CONTIGUITY_TERMINAL_TO_V1_NO_PRIMARY_ATOMS_COMPATIBILITY_VIEW"
)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise SourceStructureContractV2Error(f"{label} fields drifted")
    return canonical_clone_v1(value)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise SourceStructureContractV2Error(f"{label} is not a lowercase SHA-256")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise SourceStructureContractV2Error(f"{label} is not a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise SourceStructureContractV2Error(f"{label} is not a nonnegative integer")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise SourceStructureContractV2Error(f"{label} is not a positive integer bbox")
    return value


def _object_ref(
    value: Any,
    *,
    suffix: str = ".json",
    label: str = "V2 result reference",
) -> dict[str, Any]:
    reference = _exact_dict(value, _OBJECT_REF_FIELDS, label)
    digest = _sha(reference["sha256"], f"{label} identity")
    _positive_int(reference["size_bytes"], f"{label} size")
    match = _OBJECT_PATH_RE.fullmatch(reference["path"])
    if (
        match is None
        or match.group("digest") != digest
        or match.group("prefix") != digest[:2]
        or match.group("suffix") != suffix
    ):
        raise SourceStructureContractV2Error(f"{label} path drifted")
    return reference


def _validate_request_v1(record: Mapping[str, Any]) -> dict[str, Any]:
    request = _exact_dict(record["request"], _REQUEST_FIELDS, "V2 page request")
    if (
        request["format_version"] != "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1"
        or canonical_json_sha256_v1(request) != record["request_sha256"]
        or any(request[field] is not False for field in _REQUEST_FALSE_FIELDS)
    ):
        raise SourceStructureContractV2Error("V2 page request identity/safety drifted")
    if (
        type(request["git_commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40}", request["git_commit"]) is None
    ):
        raise SourceStructureContractV2Error("V2 page request Git identity drifted")
    for field in (
        "implementation_ledger_sha256",
        "input_ledger_sha256",
        "selection_receipt_sha256",
        "sentinel_sha256",
        "route_plan_sha256",
        "pre_ocr_feature_fingerprint_sha256",
        "source_sha256",
        "provider_identity_sha256",
    ):
        _sha(request[field], f"V2 page request {field}")
    _positive_int(request["source_size_bytes"], "V2 page request source size")
    _positive_int(request["physical_page"], "V2 page request physical page")
    for field in ("source_sha256", "source_size_bytes", "physical_page", "route"):
        if not same_typed_json_v1(request[field], record[field]):
            raise SourceStructureContractV2Error(f"V2 page request {field} drifted")
    if request["route"] == _OCR_ROUTE:
        _sha(request["render_runtime_identity_sha256"], "OCR render runtime identity")
        render = _exact_dict(
            request["render_specification"],
            _RENDER_SPECIFICATION_FIELDS,
            "OCR render specification",
        )
        if (
            type(render["dpi"]) is not int
            or render["dpi"] not in {200, 300}
            or render["colorspace"] != "RGB"
            or render["alpha"] is not False
            or render["annotations"] != "INCLUDED"
            or render["source"] != "FULL_COMPOSITED_DISPLAYED_PDF_PAGE"
        ):
            raise SourceStructureContractV2Error("OCR render specification drifted")
    elif request["route"] == _NATIVE_ROUTE:
        if (
            request["render_runtime_identity_sha256"] is not None
            or request["render_specification"] is not None
        ):
            raise SourceStructureContractV2Error("native request selected a render")
    else:
        raise SourceStructureContractV2Error("V2 page request route drifted")
    return request


def _validate_adoption_v1(record: Mapping[str, Any]) -> dict[str, Any]:
    adoption = _exact_dict(
        record["upstream_v2_adoption"],
        _ADOPTION_FIELDS,
        "OCR V2 adoption",
    )
    if adoption["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FAILED_V2_OCR_ADOPTION_V1":
        raise SourceStructureContractV2Error("OCR V2 adoption format drifted")
    for field in (
        "incident_identity_sha256",
        "archive_portable_manifest_sha256",
        "archive_live_manifest_sha256",
        "source_control_identity_sha256",
        "source_checkpoint_sha256",
        "source_page_record_sha256",
        "destination_control_identity_sha256",
    ):
        _sha(adoption[field], f"OCR V2 adoption {field}")
    _positive_int(adoption["source_checkpoint_size_bytes"], "OCR source checkpoint size")
    _positive_int(adoption["source_checkpoint_generation"], "OCR checkpoint generation")
    source_refs = _exact_dict(
        adoption["source_refs"],
        _ADOPTION_REF_FIELDS,
        "OCR adoption refs",
    )
    for field, suffix in (
        ("render_ref", ".png"),
        ("backend_payload_ref", ".json"),
        ("result_ref", ".json"),
    ):
        _object_ref(source_refs[field], suffix=suffix, label=f"OCR adoption {field}")
        if not same_typed_json_v1(source_refs[field], record[field]):
            raise SourceStructureContractV2Error("OCR adoption reference binding drifted")
    if (
        adoption["source_status"] != record["status"]
        or adoption["source_origin"] != record["upstream_origin"]
        or adoption["source_unresolved"] != record["unresolved"]
        or adoption["copy_semantics"] != "BYTE_COPY_NEW_INODE_NO_HARDLINK_V1"
        or adoption["source_checkpoint_or_page_record_relabelled"] is not False
    ):
        raise SourceStructureContractV2Error("OCR V2 adoption authority drifted")
    return adoption


def validate_full_page_record_v2(value: Any) -> dict[str, Any]:
    """Validate the exact authoritative Full Page Record V2 envelope."""

    record = _exact_dict(value, _PAGE_RECORD_V2_FIELDS, "Full Page Record V2")
    if record["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2":
        raise SourceStructureContractV2Error("Full Page Record V2 format drifted")
    _positive_int(record["request_ordinal"], "request ordinal")
    source_sha = _sha(record["source_sha256"], "source identity")
    if record["document_id"] != f"sha256:{source_sha}":
        raise SourceStructureContractV2Error("document identity is not source-content-bound")
    _positive_int(record["source_size_bytes"], "source size")
    _positive_int(record["physical_page"], "physical page")
    _sha(record["request_sha256"], "request identity")
    for field in _PAGE_RECORD_ACCOUNTING_FIELDS:
        _nonnegative_int(record[field], f"page-record {field}")
    if (
        record["line_axis_count"]
        != record["nonempty_line_axis_count"] + record["exact_empty_line_axis_count"]
        or record["accepted_line_count"] != record["nonempty_line_axis_count"]
        or any(record[field] != 0 for field in _ZERO_INTERPRETATION_FIELDS)
        or type(record["unresolved"]) is not bool
    ):
        raise SourceStructureContractV2Error("Full Page Record V2 accounting drifted")
    _validate_request_v1(record)
    _object_ref(record["backend_payload_ref"], label="backend reference")
    _object_ref(record["result_ref"], label="result reference")
    if record["route"] == _OCR_ROUTE:
        _object_ref(record["render_ref"], suffix=".png", label="render reference")
        if (
            record["status"] not in {_OCR_COMPLETE, _OCR_TERMINAL}
            or record["origin"] != "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY"
            or record["upstream_status"] != record["status"]
            or record["upstream_origin"] not in _OCR_UPSTREAM_ORIGINS
            or record["upstream_unresolved"] != record["unresolved"]
            or record["quarantined_span_count"] != 0
            or record["ordering_quarantined_raw_line_run_count"] != 0
            or record["ordering_quarantined_raw_word_count"] != 0
            or record["noncontiguous_line_identity_count"] != 0
        ):
            raise SourceStructureContractV2Error("OCR Full Page Record V2 authority drifted")
        _validate_adoption_v1(record)
        if record["status"] == _OCR_TERMINAL and any(
            record[field] != 0
            for field in (
                "line_axis_count",
                "nonempty_line_axis_count",
                "exact_empty_line_axis_count",
                "accepted_line_count",
                "word_token_count",
                "word_box_correction_count",
                "word_box_corrected_edge_count",
            )
        ):
            raise SourceStructureContractV2Error("terminal OCR record exposed accepted geometry")
    elif record["route"] == _NATIVE_ROUTE:
        if (
            record["status"] not in _NATIVE_STATUSES
            or record["origin"] != "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2"
            or record["upstream_status"] is not None
            or record["upstream_origin"] is not None
            or record["upstream_unresolved"] is not None
            or record["upstream_v2_adoption"] is not None
            or record["render_ref"] is not None
            or record["exact_empty_line_axis_count"] != 0
            or record["word_box_correction_count"] != 0
            or record["word_box_corrected_edge_count"] != 0
        ):
            raise SourceStructureContractV2Error("native Full Page Record V2 authority drifted")
    else:
        raise SourceStructureContractV2Error("Full Page Record V2 route drifted")
    if record["unresolved"] != (record["status"] not in {_OCR_COMPLETE, _NATIVE_COMPLETE}):
        raise SourceStructureContractV2Error("Full Page Record V2 terminal accounting drifted")
    return record


def _validate_embedded_page_result(
    value: Any,
    *,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise SourceStructureContractV2Error("embedded page result is not an object")
    version = value.get("format_version")
    if version == "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2":
        fields = _OCR_RESULT_V2_FIELDS
    elif version == "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3":
        fields = _OCR_RESULT_V3_FIELDS
    elif version == _NATIVE_RESULT_FORMAT:
        fields = _NATIVE_RESULT_FIELDS
    else:
        raise SourceStructureContractV2Error("embedded page-result format drifted")
    result = _exact_dict(value, fields, "embedded page result")
    payload = canonical_json_bytes_v1(result)
    if (
        len(payload) != record["result_ref"]["size_bytes"]
        or canonical_json_sha256_v1(result) != record["result_ref"]["sha256"]
    ):
        raise SourceStructureContractV2Error("embedded page-result bytes drifted")
    for field in (
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "status",
    ):
        if not same_typed_json_v1(result[field], record[field]):
            raise SourceStructureContractV2Error(f"embedded page-result {field} binding drifted")
    if (
        result["provider_identity_sha256"] != record["request"]["provider_identity_sha256"]
        or result["source_blank_claimed"] is not False
        or type(result["lines"]) is not list
        or type(result["words"]) is not list
    ):
        raise SourceStructureContractV2Error("embedded page-result safety/axis drifted")
    if record["route"] == _OCR_ROUTE:
        expected_claim_boundary = (
            "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
            if version == "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
            else "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
        )
        if (
            version not in _OCR_RESULT_FORMATS
            or result["claim_boundary"] != expected_claim_boundary
            or not same_typed_json_v1(result["input_render_ref"], record["render_ref"])
            or not same_typed_json_v1(result["backend_payload_ref"], record["backend_payload_ref"])
            or result["render_runtime_identity_sha256"]
            != record["request"]["render_runtime_identity_sha256"]
            or type(result["safety"]) is not dict
            or set(result["safety"]) != _UPSTREAM_SAFETY_FIELDS
            or any(value is not False for value in result["safety"].values())
            or (
                version == "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
                and result["ocr_fallback_used"] is not False
            )
        ):
            raise SourceStructureContractV2Error("embedded OCR result authority drifted")
    else:
        metrics = _exact_dict(
            result["metrics"],
            {
                "line_count",
                "word_token_count",
                "ghost_quarantined_span_count",
                "ordering_quarantined_raw_line_run_count",
                "ordering_quarantined_raw_word_count",
                "noncontiguous_line_identity_count",
            },
            "embedded native metrics",
        )
        if (
            result["claim_boundary"]
            != "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_GEOMETRY_AND_VISUAL_ORDER_EVIDENCE_ONLY"
            or result["document_id"] != record["document_id"]
            or result["backend_payload_sha256"] != record["backend_payload_ref"]["sha256"]
            or result["ocr_fallback_used"] is not False
            or type(result["quarantined_spans"]) is not list
            or type(result["safety"]) is not dict
            or set(result["safety"]) != _NATIVE_RESULT_SAFETY_FIELDS
            or any(value is not False for value in result["safety"].values())
            or any(type(metrics[field]) is not int or metrics[field] < 0 for field in metrics)
            or metrics["line_count"] != record["line_axis_count"]
            or metrics["word_token_count"] != record["word_token_count"]
            or metrics["ghost_quarantined_span_count"] != record["quarantined_span_count"]
            or metrics["ordering_quarantined_raw_line_run_count"]
            != record["ordering_quarantined_raw_line_run_count"]
            or metrics["ordering_quarantined_raw_word_count"]
            != record["ordering_quarantined_raw_word_count"]
            or metrics["noncontiguous_line_identity_count"]
            != record["noncontiguous_line_identity_count"]
        ):
            raise SourceStructureContractV2Error("embedded native result authority drifted")
        _sha(result["full_control_identity_sha256"], "native full-control identity")
        _sha(result["backend_payload_sha256"], "native backend identity")
    return result


def _native_coordinate_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _NATIVE_COORDINATE_FIELDS, "native V2 coordinate authority")
    if any(authority[key] != expected for key, expected in _NATIVE_AUTHORITY_V1.items()):
        raise SourceStructureContractV2Error("native V2 coordinate authority identity drifted")
    if type(authority["pdf_rotation_degrees"]) is not int or authority[
        "pdf_rotation_degrees"
    ] not in {0, 90, 180, 270}:
        raise SourceStructureContractV2Error("native V2 rotation drifted")
    local = _bbox(authority["canonical_cropbox_bounds_mpt"], "canonical cropbox")
    crop = _bbox(authority["source_cropbox_mpt"], "source cropbox")
    media = _bbox(authority["source_mediabox_mpt"], "source mediabox")
    if local[:2] != [0, 0] or crop[2] - crop[0] != local[2] or crop[3] - crop[1] != local[3]:
        raise SourceStructureContractV2Error("native V2 cropbox dimensions drifted")
    if crop[0] < media[0] or crop[1] < media[1] or crop[2] > media[2] or crop[3] > media[3]:
        raise SourceStructureContractV2Error("native V2 cropbox falls outside the mediabox")
    return authority


def _validate_native_ordering_payloads(
    projection: Mapping[str, Any],
    accounting: Mapping[str, Any],
    page_result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    policy = _exact_dict(
        projection["native_ordering_policy_identity"],
        {"path", "sha256", "size_bytes"},
        "native ordering-policy identity",
    )
    if not same_typed_json_v1(policy, _ORDERING_POLICY_IDENTITY):
        raise SourceStructureContractV2Error("native ordering-policy identity drifted")
    if not same_typed_json_v1(policy, page_result["ordering_policy_identity"]):
        raise SourceStructureContractV2Error("native result/ordering-policy binding drifted")
    if projection["native_ordering_policy_identity_sha256"] != canonical_json_sha256_v1(policy):
        raise SourceStructureContractV2Error("native ordering-policy digest drifted")
    receipt = _exact_dict(
        projection["native_ordering_receipt"],
        _ORDERING_RECEIPT_FIELDS,
        "native ordering receipt",
    )
    if (
        receipt["format_version"]
        != "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_VISUAL_ORDER_RECEIPT_V1"
        or receipt["policy"] != "CAUSAL_NATIVE_TEXT_VISUAL_ORDER_EVIDENCE_V2"
        or receipt["source_word_order"] != "PYMUPDF_GET_TEXT_WORDS_SORT_TRUE"
        or receipt["line_projection"] != "CONTIGUOUS_FIRST_OCCURRENCE_LINE_RUNS"
        or not same_typed_json_v1(receipt["ordering_policy_identity"], policy)
        or not same_typed_json_v1(receipt, page_result["ordering_receipt"])
        or projection["native_ordering_receipt_sha256"] != canonical_json_sha256_v1(receipt)
    ):
        raise SourceStructureContractV2Error("native ordering receipt identity drifted")
    for field in (
        "source_words_sha256",
        "line_runs_sha256",
        "noncontiguous_line_identities_sha256",
    ):
        _sha(receipt[field], f"native ordering receipt {field}")
    for field in (
        "source_word_count",
        "line_run_count",
        "distinct_line_identity_count",
        "noncontiguous_line_identity_count",
    ):
        _nonnegative_int(receipt[field], f"native ordering receipt {field}")
    if (
        receipt["distinct_line_identity_count"] > receipt["line_run_count"]
        or receipt["noncontiguous_line_identity_count"] > receipt["distinct_line_identity_count"]
        or accounting["noncontiguous_line_identity_count"]
        != receipt["noncontiguous_line_identity_count"]
    ):
        raise SourceStructureContractV2Error("native ordering receipt counts drifted")
    empty_axis_sha = canonical_json_sha256_v1([])
    if (
        (receipt["source_word_count"] == 0 and receipt["source_words_sha256"] != empty_axis_sha)
        or (receipt["line_run_count"] == 0 and receipt["line_runs_sha256"] != empty_axis_sha)
        or (
            receipt["noncontiguous_line_identity_count"] == 0
            and receipt["noncontiguous_line_identities_sha256"] != empty_axis_sha
        )
    ):
        raise SourceStructureContractV2Error("native ordering empty-axis digest drifted")
    upstream_status = projection["upstream_status"]
    if upstream_status == _NATIVE_COMPLETE:
        if any(
            type(line) is not dict
            or type(line.get("words")) is not list
            or type(line.get("block_number")) is not int
            or type(line.get("line_number")) is not int
            for line in page_result["lines"]
        ):
            raise SourceStructureContractV2Error("native accepted line axis drifted")
        flattened_words = [word for line in page_result["lines"] for word in line.get("words", [])]
        line_run_projection = [
            {
                "line_identity_sha256": canonical_json_sha256_v1(
                    [line.get("block_number"), line.get("line_number")]
                ),
                "word_count": len(line.get("words", [])),
                "words_sha256": canonical_json_sha256_v1(line.get("words", [])),
            }
            for line in page_result["lines"]
        ]
        if (
            receipt["status"] != "CONTIGUOUS_SOURCE_ORDER_ACCEPTED"
            or not same_typed_json_v1(flattened_words, page_result["words"])
            or receipt["source_words_sha256"] != canonical_json_sha256_v1(page_result["words"])
            or receipt["line_runs_sha256"] != canonical_json_sha256_v1(line_run_projection)
            or receipt["source_word_count"] != accounting["word_token_count"]
            or receipt["line_run_count"] != accounting["line_axis_count"]
            or receipt["distinct_line_identity_count"] != accounting["line_axis_count"]
            or receipt["noncontiguous_line_identity_count"] != 0
            or accounting["ordering_quarantined_raw_line_run_count"] != 0
            or accounting["ordering_quarantined_raw_word_count"] != 0
        ):
            raise SourceStructureContractV2Error("accepted native ordering accounting drifted")
    elif upstream_status == _NATIVE_CONTIGUITY_STATUS:
        if (
            receipt["status"] != "NONCONTIGUOUS_LINE_ORDER_QUARANTINED"
            or receipt["source_word_count"] <= 0
            or receipt["line_run_count"] <= 0
            or receipt["noncontiguous_line_identity_count"] <= 0
            or receipt["distinct_line_identity_count"] >= receipt["line_run_count"]
            or accounting["line_axis_count"] != 0
            or accounting["word_token_count"] != 0
            or accounting["ordering_quarantined_raw_line_run_count"] != receipt["line_run_count"]
            or accounting["ordering_quarantined_raw_word_count"] != receipt["source_word_count"]
        ):
            raise SourceStructureContractV2Error("quarantined native ordering accounting drifted")
    elif (
        receipt["status"] != "SOURCE_ORDER_NOT_APPLICABLE_TO_UPSTREAM_TERMINAL"
        or any(
            receipt[field] != 0
            for field in (
                "source_word_count",
                "line_run_count",
                "distinct_line_identity_count",
                "noncontiguous_line_identity_count",
            )
        )
        or accounting["ordering_quarantined_raw_line_run_count"] != 0
        or accounting["ordering_quarantined_raw_word_count"] != 0
    ):
        raise SourceStructureContractV2Error("terminal native ordering accounting drifted")
    return policy, receipt


def _identity_payload(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_locator": projection["source_locator"],
        "route": projection["route"],
        "upstream_status": projection["upstream_status"],
        "terminal": projection["terminal"],
        "terminal_reason": projection["terminal_reason"],
        "page_record_format_version": projection["page_record_format_version"],
        "page_record_sha256": projection["page_record_sha256"],
        "page_result_format_version": projection["page_result_format_version"],
        "page_result_ref": projection["page_result_ref"],
        "page_result_sha256": projection["page_result_sha256"],
        "page_record_accounting": projection["page_record_accounting"],
        "coordinate_authority_sha256": canonical_json_sha256_v1(projection["coordinate_authority"]),
        "native_ordering_policy_identity_sha256": projection[
            "native_ordering_policy_identity_sha256"
        ],
        "native_ordering_receipt_sha256": projection["native_ordering_receipt_sha256"],
        "v1_compatibility_disposition": projection["v1_compatibility_disposition"],
        "v1_compatibility_view_authoritative": projection["v1_compatibility_view_authoritative"],
        "neutral_page_v1_sha256": projection["neutral_page_v1_sha256"],
    }


def validate_source_evidence_projection_v2(value: Any) -> dict[str, Any]:
    """Validate one exact V3-page-to-neutral-source projection."""

    projection = _exact_dict(value, _PROJECTION_FIELDS, "V2 source evidence projection")
    if projection["format_version"] != SOURCE_PROJECTION_FORMAT_VERSION_V2:
        raise SourceStructureContractV2Error("V2 source projection format drifted")
    if projection["claim_boundary"] != SOURCE_PROJECTION_CLAIM_BOUNDARY_V2:
        raise SourceStructureContractV2Error("V2 source projection claim boundary drifted")
    record = validate_full_page_record_v2(projection["page_record_v2"])
    if projection["page_record_format_version"] != record["format_version"]:
        raise SourceStructureContractV2Error("V2 page-record binding drifted")
    record_sha = _sha(projection["page_record_sha256"], "V2 page-record identity")
    if record_sha != canonical_json_sha256_v1(record):
        raise SourceStructureContractV2Error("V2 embedded page-record bytes drifted")
    result_reference = _object_ref(projection["page_result_ref"])
    result_sha = _sha(projection["page_result_sha256"], "V2 result identity")
    if result_reference["sha256"] != result_sha:
        raise SourceStructureContractV2Error("V2 result reference binding drifted")
    page_result = _validate_embedded_page_result(
        projection["page_result"],
        record=record,
    )
    if projection["page_result_format_version"] != page_result[
        "format_version"
    ] or result_sha != canonical_json_sha256_v1(page_result):
        raise SourceStructureContractV2Error("V2 embedded page-result binding drifted")
    accounting = _exact_dict(
        projection["page_record_accounting"],
        _PAGE_RECORD_ACCOUNTING_FIELDS,
        "V2 page-record accounting",
    )
    if any(type(accounting[field]) is not int or accounting[field] < 0 for field in accounting):
        raise SourceStructureContractV2Error("V2 page-record accounting types drifted")
    if (
        accounting["line_axis_count"]
        != accounting["nonempty_line_axis_count"] + accounting["exact_empty_line_axis_count"]
        or accounting["accepted_line_count"] != accounting["nonempty_line_axis_count"]
        or any(
            accounting[field] != 0
            for field in (
                "statement_classification_count",
                "table_classification_count",
                "row_reconstruction_count",
                "cell_interpretation_count",
                "absence_declaration_count",
            )
        )
    ):
        raise SourceStructureContractV2Error("V2 page-record accounting identity drifted")
    if not same_typed_json_v1(
        accounting,
        {field: record[field] for field in sorted(_PAGE_RECORD_ACCOUNTING_FIELDS)},
    ):
        raise SourceStructureContractV2Error("V2 embedded page-record accounting drifted")

    locator = _exact_dict(projection["source_locator"], _SOURCE_LOCATOR_FIELDS, "source locator")
    _sha(locator["source_sha256"], "source identity")
    _positive_int(locator["source_size_bytes"], "source size")
    _positive_int(locator["physical_page"], "physical page")
    _sha(locator["request_sha256"], "request identity")
    if type(projection["terminal"]) is not bool:
        raise SourceStructureContractV2Error("V2 terminal flag drifted")
    expected_locator = {
        "source_sha256": record["source_sha256"],
        "source_size_bytes": record["source_size_bytes"],
        "physical_page": record["physical_page"],
        "request_sha256": record["request_sha256"],
    }
    if (
        not same_typed_json_v1(locator, expected_locator)
        or projection["route"] != record["route"]
        or projection["upstream_status"] != record["status"]
        or projection["terminal"] != record["unresolved"]
        or not same_typed_json_v1(result_reference, record["result_ref"])
    ):
        raise SourceStructureContractV2Error("V2 embedded page-record authority drifted")

    neutral = validate_neutral_page_envelope_v1(projection["neutral_page_v1"])
    neutral_sha = _sha(projection["neutral_page_v1_sha256"], "neutral V1 projection identity")
    if neutral_sha != canonical_json_sha256_v1(neutral):
        raise SourceStructureContractV2Error("neutral V1 projection bytes drifted")
    if (
        not same_typed_json_v1(neutral["source_locator"], locator)
        or neutral["route"] != projection["route"]
        or neutral["terminal"] != projection["terminal"]
        or not same_typed_json_v1(
            projection["coordinate_authority"], page_result["coordinate_authority"]
        )
    ):
        raise SourceStructureContractV2Error("neutral V1 source binding drifted")
    neutral_result_reference = next(
        reference for reference in neutral["evidence_refs"] if reference["kind"] == "RESULT"
    )
    if (
        neutral_result_reference["sha256"] != result_sha
        or neutral_result_reference["size_bytes"] != result_reference["size_bytes"]
    ):
        raise SourceStructureContractV2Error("neutral V1 result binding drifted")
    neutral_receipt = neutral["projection_receipt"]
    page_quarantine_axis = page_result.get("quarantined_spans", [])
    if (
        neutral_receipt["result_projection_sha256"] != result_sha
        or neutral_receipt["upstream_line_axis_sha256"]
        != canonical_json_sha256_v1(page_result["lines"])
        or neutral_receipt["upstream_word_axis_sha256"]
        != canonical_json_sha256_v1(page_result["words"])
        or neutral_receipt["upstream_quarantine_axis_sha256"]
        != canonical_json_sha256_v1(page_quarantine_axis)
    ):
        raise SourceStructureContractV2Error("neutral V1/page-result axis binding drifted")
    neutral_metrics = neutral["metrics"]
    expected_neutral_accounting = {
        "line_axis_count": neutral_metrics["upstream_line_axis_count"],
        "nonempty_line_axis_count": neutral_metrics["primary_line_count"],
        "exact_empty_line_axis_count": neutral_metrics["excluded_empty_line_axis_count"],
        "accepted_line_count": neutral_metrics["primary_line_count"],
        "word_token_count": neutral_metrics["upstream_word_axis_count"],
        "quarantined_span_count": neutral_metrics["upstream_quarantined_span_axis_count"],
    }
    if any(
        accounting[field] != expected for field, expected in expected_neutral_accounting.items()
    ):
        raise SourceStructureContractV2Error("V2 page-record accounting/neutral projection drifted")

    if projection["route"] == "DOMINANT_RASTER_OCR":
        if projection["page_result_format_version"] not in _OCR_RESULT_FORMATS:
            raise SourceStructureContractV2Error("OCR result format drifted")
        if (
            projection["native_ordering_policy_identity"] is not None
            or projection["native_ordering_policy_identity_sha256"] is not None
            or projection["native_ordering_receipt"] is not None
            or projection["native_ordering_receipt_sha256"] is not None
            or projection["v1_compatibility_disposition"] != _IDENTITY_DISPOSITION
            or neutral["upstream_status"] != projection["upstream_status"]
            or neutral["terminal_reason"] != projection["terminal_reason"]
            or not same_typed_json_v1(
                neutral["coordinate_authority"], projection["coordinate_authority"]
            )
        ):
            raise SourceStructureContractV2Error("OCR V2 compatibility projection drifted")
    elif projection["route"] == "CAUSAL_NATIVE_TEXT":
        if projection["page_result_format_version"] != _NATIVE_RESULT_FORMAT:
            raise SourceStructureContractV2Error("native V2 result format drifted")
        _validate_native_ordering_payloads(projection, accounting, page_result)
        authority = _native_coordinate_authority(projection["coordinate_authority"])
        if not same_typed_json_v1(neutral["coordinate_authority"], _NATIVE_AUTHORITY_V1):
            raise SourceStructureContractV2Error("native V1 compatibility authority drifted")
        for atom in neutral["atoms"]:
            bbox = atom["canonical_bbox_mpt"]
            if bbox is not None:
                bounds = authority["canonical_cropbox_bounds_mpt"]
                if (
                    bbox[0] < bounds[0]
                    or bbox[1] < bounds[1]
                    or bbox[2] > bounds[2]
                    or bbox[3] > bounds[3]
                ):
                    raise SourceStructureContractV2Error("native atom falls outside V2 cropbox")
        if projection["upstream_status"] == _NATIVE_CONTIGUITY_STATUS:
            if (
                projection["v1_compatibility_disposition"] != _CONTIGUITY_DISPOSITION
                or neutral["upstream_status"] != "UNRESOLVED_NATIVE_TEXT_QUALITY"
                or neutral["terminal_reason"] != "CORRUPT_TEXT_LAYER"
                or any(
                    atom["kind"] in {"LINE", "WORD"}
                    and atom["authority"] == "AUTHENTICATED_PRIMARY"
                    for atom in neutral["atoms"]
                )
            ):
                raise SourceStructureContractV2Error(
                    "native contiguity-terminal compatibility projection drifted"
                )
        elif (
            projection["v1_compatibility_disposition"] != _IDENTITY_DISPOSITION
            or neutral["upstream_status"] != projection["upstream_status"]
            or neutral["terminal_reason"] != projection["terminal_reason"]
        ):
            raise SourceStructureContractV2Error("native V2 compatibility projection drifted")
    else:
        raise SourceStructureContractV2Error("V2 source route drifted")

    if projection["terminal"] != projection["upstream_status"].startswith("UNRESOLVED_"):
        raise SourceStructureContractV2Error("V2 terminal accounting drifted")
    if projection["v1_compatibility_view_authoritative"] is not False:
        raise SourceStructureContractV2Error("V1 compatibility view was promoted to authority")
    if not same_typed_json_v1(projection["safety"], SOURCE_PROJECTION_SAFETY_V2):
        raise SourceStructureContractV2Error("V2 source projection safety drifted")
    expected_id = f"ssv2:page:{canonical_json_sha256_v1(_identity_payload(projection))}"
    if (
        type(projection["source_local_page_id"]) is not str
        or _SOURCE_PAGE_ID_RE.fullmatch(projection["source_local_page_id"]) is None
        or projection["source_local_page_id"] != expected_id
    ):
        raise SourceStructureContractV2Error("V2 source page identity drifted")
    return canonical_clone_v1(projection)


def make_empty_page_proposal_set_v2(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Dispose every V2 evidence atom without making a structure claim."""

    source = validate_source_evidence_projection_v2(projection)
    return make_page_proposal_set_v2(
        source,
        proposal_set_v1=make_empty_page_proposal_set_v1(source["neutral_page_v1"]),
    )


def make_page_proposal_set_v2(
    projection: Mapping[str, Any],
    *,
    proposal_set_v1: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one validated V1 source-geometry proposal set to V2 authority."""

    source = validate_source_evidence_projection_v2(projection)
    validated_v1 = validate_page_proposal_set_v1(
        proposal_set_v1,
        envelope=source["neutral_page_v1"],
    )
    proposal = {
        "format_version": PAGE_PROPOSAL_FORMAT_VERSION_V2,
        "claim_boundary": PAGE_PROPOSAL_CLAIM_BOUNDARY_V2,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "neutral_page_v1_sha256": source["neutral_page_v1_sha256"],
        "proposal_set_v1": validated_v1,
        "safety": canonical_clone_v1(SOURCE_PROJECTION_SAFETY_V2),
    }
    return validate_page_proposal_set_v2(proposal, projection=source)


def validate_page_proposal_set_v2(
    value: Any,
    *,
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    source = validate_source_evidence_projection_v2(projection)
    proposal = _exact_dict(value, _PROPOSAL_FIELDS, "V2 empty source disposition")
    if (
        proposal["format_version"] != PAGE_PROPOSAL_FORMAT_VERSION_V2
        or proposal["claim_boundary"] != PAGE_PROPOSAL_CLAIM_BOUNDARY_V2
        or proposal["source_local_page_id"] != source["source_local_page_id"]
        or proposal["source_projection_sha256"] != canonical_json_sha256_v1(source)
        or proposal["neutral_page_v1_sha256"] != source["neutral_page_v1_sha256"]
        or not same_typed_json_v1(proposal["safety"], SOURCE_PROJECTION_SAFETY_V2)
    ):
        raise SourceStructureContractV2Error("V2 empty source disposition binding drifted")
    validated_v1 = validate_page_proposal_set_v1(
        proposal["proposal_set_v1"],
        envelope=source["neutral_page_v1"],
    )
    if len(validated_v1["dispositions"]) != len(source["neutral_page_v1"]["atoms"]):
        raise SourceStructureContractV2Error("V2 source proposal disposition accounting drifted")
    return canonical_clone_v1(proposal)
