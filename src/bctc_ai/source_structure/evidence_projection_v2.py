"""Project finalized Full Page Record V2 evidence without widening V1.

The caller supplies already-authenticated immutable page-record/result objects.
This module performs an exact local schema/content binding, constructs the
frozen V1 neutral atom view, and wraps it in the authoritative V2 receipt from
``contracts_v2``.  It performs no filesystem traversal, source read, network
access, OCR/native inference, statement discovery, or schema lookup.
"""

from __future__ import annotations

import re
from typing import Any

from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    _PUBLIC_PAYLOAD_FIELDS,
    LINE_CONTIGUITY_FAILURE_TYPE,
    LINE_CONTIGUITY_STATUS,
    CausalNativeTextEvidenceError,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    RESULT_FIELDS as NATIVE_RESULT_FIELDS,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    RESULT_FORMAT_VERSION as NATIVE_RESULT_FORMAT_VERSION,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    RESULT_METRIC_FIELDS as NATIVE_RESULT_METRIC_FIELDS,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    TERMINAL_STATUSES as NATIVE_RESULT_STATUSES,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    _safety_boundary as _native_safety_boundary,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    _validate_coordinate_authority as _validate_native_coordinate_authority,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    _validate_public_payload as _validate_native_public_payload,
)
from bctc_ai.source_structure.contracts_v1 import (
    NEUTRAL_PAGE_CLAIM_BOUNDARY,
    NEUTRAL_PAGE_FORMAT_VERSION,
    PROJECTION_RECEIPT_FORMAT_VERSION,
    SOURCE_STRUCTURE_SAFETY_V1,
    AtomAuthority,
    AtomKind,
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
    validate_neutral_page_envelope_v1,
)
from bctc_ai.source_structure.contracts_v2 import (
    SOURCE_PROJECTION_CLAIM_BOUNDARY_V2,
    SOURCE_PROJECTION_FORMAT_VERSION_V2,
    SOURCE_PROJECTION_SAFETY_V2,
    _identity_payload,
    validate_full_page_record_v2,
    validate_source_evidence_projection_v2,
)
from bctc_ai.source_structure.evidence_projection_v1 import (
    _NATIVE_AUTHORITY,
    SourceEvidenceProjectionError,
    _native_atoms,
    _neutral_ref,
    _validate_request,
    project_authenticated_page_v1,
)

__all__ = ["SourceEvidenceProjectionV2Error", "project_authenticated_page_v2"]


class SourceEvidenceProjectionV2Error(ValueError):
    """Finalized V3 evidence cannot enter the neutral V2 projection."""


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_NATIVE_COMPLETE = "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
_NATIVE_CONTIGUITY_STATUS = LINE_CONTIGUITY_STATUS
_ZERO_INTERPRETATION_FIELDS = {
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
}
_ACCOUNTING_FIELDS = {
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
    *_ZERO_INTERPRETATION_FIELDS,
}
_OCR_RESULT_FORMATS = {
    "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
    "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
}
_NATIVE_RESULT_CLAIM_BOUNDARY = (
    "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_GEOMETRY_AND_VISUAL_ORDER_EVIDENCE_ONLY"
)
_IDENTITY_DISPOSITION = "IDENTITY_PRESERVING_V1_NEUTRAL_ATOM_PROJECTION"
_CONTIGUITY_DISPOSITION = (
    "NATIVE_LINE_CONTIGUITY_TERMINAL_TO_V1_NO_PRIMARY_ATOMS_COMPATIBILITY_VIEW"
)


def _error(message: str) -> SourceEvidenceProjectionV2Error:
    return SourceEvidenceProjectionV2Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return canonical_clone_v1(value)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _legacy_ocr_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1",
        **{
            key: canonical_clone_v1(record[key])
            for key in (
                "request_ordinal",
                "document_id",
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "route",
                "request_sha256",
                "request",
                "status",
                "render_ref",
                "backend_payload_ref",
                "result_ref",
                "word_token_count",
                "unresolved",
                "quarantined_span_count",
                "word_box_correction_count",
                "word_box_corrected_edge_count",
                *_ZERO_INTERPRETATION_FIELDS,
            )
        },
        "origin": record["upstream_origin"],
        "line_count": record["line_axis_count"],
    }


def _validate_native_result_v2(record: dict[str, Any], value: Any) -> dict[str, Any]:
    result = _exact_dict(value, set(NATIVE_RESULT_FIELDS), "causal-native Result V2")
    if (
        result["format_version"] != NATIVE_RESULT_FORMAT_VERSION
        or result["claim_boundary"] != _NATIVE_RESULT_CLAIM_BOUNDARY
        or result["status"] not in NATIVE_RESULT_STATUSES
        or result["status"] != record["status"]
        or result["route"] != _NATIVE_ROUTE
    ):
        raise _error("causal-native Result V2 identity drifted")
    for field in (
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
    ):
        if not same_typed_json_v1(result[field], record[field]):
            raise _error(f"causal-native Result V2 {field} binding drifted")
    try:
        _validate_request(record, result)
    except SourceEvidenceProjectionError as error:
        raise _error("causal-native Result V2 request drifted") from error
    _sha(result["full_control_identity_sha256"], "native full-control identity")
    _sha(result["provider_identity_sha256"], "native provider identity")
    _sha(result["backend_payload_sha256"], "native backend identity")
    if (
        result["provider_identity_sha256"] != record["request"]["provider_identity_sha256"]
        or result["backend_payload_sha256"] != record["backend_payload_ref"]["sha256"]
        or result["ocr_fallback_used"] is not False
        or result["source_blank_claimed"] is not False
        or not same_typed_json_v1(result["safety"], _native_safety_boundary())
    ):
        raise _error("causal-native Result V2 safety/provider binding drifted")
    try:
        authority = _validate_native_coordinate_authority(result["coordinate_authority"])
        public = _validate_native_public_payload(
            {key: result[key] for key in _PUBLIC_PAYLOAD_FIELDS},
            physical_page=record["physical_page"],
            authority=authority,
            ordering_policy_identity=result["ordering_policy_identity"],
        )
    except CausalNativeTextEvidenceError as error:
        raise _error("causal-native Result V2 public evidence drifted") from error
    expected_metrics = {
        "line_count": len(public["lines"]),
        "word_token_count": len(public["words"]),
        "ghost_quarantined_span_count": len(public["quarantined_spans"]),
        "ordering_quarantined_raw_line_run_count": (
            public["ordering_receipt"]["line_run_count"]
            if public["status"] == _NATIVE_CONTIGUITY_STATUS
            else 0
        ),
        "ordering_quarantined_raw_word_count": (
            public["ordering_receipt"]["source_word_count"]
            if public["status"] == _NATIVE_CONTIGUITY_STATUS
            else 0
        ),
        "noncontiguous_line_identity_count": public["ordering_receipt"][
            "noncontiguous_line_identity_count"
        ],
    }
    if (
        type(result["metrics"]) is not dict
        or set(result["metrics"]) != set(NATIVE_RESULT_METRIC_FIELDS)
        or not same_typed_json_v1(result["metrics"], expected_metrics)
    ):
        raise _error("causal-native Result V2 metrics drifted")
    record_bindings = {
        "line_axis_count": result["metrics"]["line_count"],
        "nonempty_line_axis_count": result["metrics"]["line_count"],
        "accepted_line_count": result["metrics"]["line_count"],
        "word_token_count": result["metrics"]["word_token_count"],
        "quarantined_span_count": result["metrics"]["ghost_quarantined_span_count"],
        "ordering_quarantined_raw_line_run_count": result["metrics"][
            "ordering_quarantined_raw_line_run_count"
        ],
        "ordering_quarantined_raw_word_count": result["metrics"][
            "ordering_quarantined_raw_word_count"
        ],
        "noncontiguous_line_identity_count": result["metrics"]["noncontiguous_line_identity_count"],
    }
    if any(record[field] != expected for field, expected in record_bindings.items()):
        raise _error("causal-native Result V2 page-record accounting drifted")
    payload = canonical_json_bytes_v1(result)
    if (
        len(payload) != record["result_ref"]["size_bytes"]
        or canonical_json_sha256_v1(result) != record["result_ref"]["sha256"]
    ):
        raise _error("causal-native Result V2 object/reference identity drifted")
    return result


def _native_terminal_reason(result: dict[str, Any]) -> str | None:
    if result["status"] == _NATIVE_COMPLETE:
        return None
    if result["status"] == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        return result["failure_type"]
    if result["status"] == _NATIVE_CONTIGUITY_STATUS:
        if result["failure_type"] != LINE_CONTIGUITY_FAILURE_TYPE:
            raise _error("native line-contiguity failure type drifted")
        return result["failure_type"]
    return result["native_text_quality"]


def _native_v1_compatibility_view(
    record: dict[str, Any], result: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    actual_status = result["status"]
    actual_reason = _native_terminal_reason(result)
    if actual_status == _NATIVE_CONTIGUITY_STATUS:
        compatibility_status = "UNRESOLVED_NATIVE_TEXT_QUALITY"
        compatibility_reason = "CORRUPT_TEXT_LAYER"
        disposition = _CONTIGUITY_DISPOSITION
    else:
        compatibility_status = actual_status
        compatibility_reason = actual_reason
        disposition = _IDENTITY_DISPOSITION
    references = [
        _neutral_ref(
            record["backend_payload_ref"], kind="BACKEND_PAYLOAD", media_type="application/json"
        ),
        _neutral_ref(record["result_ref"], kind="RESULT", media_type="application/json"),
    ]
    locator = {
        "source_sha256": record["source_sha256"],
        "source_size_bytes": record["source_size_bytes"],
        "physical_page": record["physical_page"],
        "request_sha256": record["request_sha256"],
    }
    receipt = {
        "format_version": PROJECTION_RECEIPT_FORMAT_VERSION,
        "result_ref_sha256": record["result_ref"]["sha256"],
        "result_projection_sha256": canonical_json_sha256_v1(result),
        "coordinate_authority_sha256": canonical_json_sha256_v1(_NATIVE_AUTHORITY),
        "upstream_line_axis_sha256": canonical_json_sha256_v1(result["lines"]),
        "upstream_word_axis_sha256": canonical_json_sha256_v1(result["words"]),
        "upstream_quarantine_axis_sha256": canonical_json_sha256_v1(result["quarantined_spans"]),
        "atom_sequence_sha256": "0" * 64,
        "atom_id_sequence_sha256": "0" * 64,
        "supplement_ref_sha256": None,
        "supplement_projection_sha256": None,
        "supplement_evidence_projection_sha256": canonical_json_sha256_v1(None),
        "upstream_line_axis_count": len(result["lines"]),
        "upstream_word_axis_count": len(result["words"]),
        "upstream_quarantined_span_axis_count": len(result["quarantined_spans"]),
        "excluded_empty_line_axis_count": 0,
        "excluded_empty_word_axis_count": 0,
        "supplement_validated_line_axis_count": 0,
        "supplement_accepted_line_count": 0,
        "supplement_excluded_empty_line_axis_count": 0,
        "supplement_quarantined_subdivision_count": 0,
    }
    identity_payload = {
        **locator,
        "route": record["route"],
        "upstream_status": compatibility_status,
        "terminal_reason": compatibility_reason,
        "evidence_refs": references,
        "coordinate_authority_sha256": receipt["coordinate_authority_sha256"],
        "projection_source_receipt": {
            key: receipt[key]
            for key in sorted(set(receipt) - {"atom_sequence_sha256", "atom_id_sequence_sha256"})
        },
    }
    page_id = f"ssv1:page:{canonical_json_sha256_v1(identity_payload)}"
    atoms = _native_atoms(result, page_id=page_id, request_sha256=record["request_sha256"])
    receipt["atom_sequence_sha256"] = canonical_json_sha256_v1(atoms)
    receipt["atom_id_sequence_sha256"] = canonical_json_sha256_v1(
        [atom["source_local_id"] for atom in atoms]
    )
    envelope = {
        "format_version": NEUTRAL_PAGE_FORMAT_VERSION,
        "claim_boundary": NEUTRAL_PAGE_CLAIM_BOUNDARY,
        "source_locator": locator,
        "source_local_page_id": page_id,
        "route": record["route"],
        "upstream_status": compatibility_status,
        "terminal": record["unresolved"],
        "terminal_reason": compatibility_reason,
        "coordinate_authority": canonical_clone_v1(_NATIVE_AUTHORITY),
        "evidence_refs": references,
        "atoms": atoms,
        "projection_receipt": receipt,
        "metrics": {
            "atom_count": len(atoms),
            "upstream_line_axis_count": len(result["lines"]),
            "upstream_word_axis_count": len(result["words"]),
            "upstream_quarantined_span_axis_count": len(result["quarantined_spans"]),
            "primary_line_count": sum(
                atom["kind"] == AtomKind.LINE
                and atom["authority"] == AtomAuthority.AUTHENTICATED_PRIMARY
                for atom in atoms
            ),
            "primary_word_count": sum(
                atom["kind"] == AtomKind.WORD
                and atom["authority"] == AtomAuthority.AUTHENTICATED_PRIMARY
                for atom in atoms
            ),
            "excluded_empty_line_axis_count": 0,
            "excluded_empty_word_axis_count": 0,
            "supplemental_line_count": 0,
            "supplement_validated_line_axis_count": 0,
            "supplement_excluded_empty_line_axis_count": 0,
            "supplement_quarantined_subdivision_count": 0,
            "quarantined_atom_count": sum(
                atom["authority"] == AtomAuthority.UPSTREAM_QUARANTINE for atom in atoms
            ),
        },
        "safety": canonical_clone_v1(SOURCE_STRUCTURE_SAFETY_V1),
    }
    return validate_neutral_page_envelope_v1(envelope), disposition


def _page_record_accounting(record: dict[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in sorted(_ACCOUNTING_FIELDS)}


def project_authenticated_page_v2(
    *,
    page_record: dict[str, Any],
    page_result: dict[str, Any],
) -> dict[str, Any]:
    """Return one authoritative V2 wrapper and internal neutral V1 atom view."""

    try:
        record = validate_full_page_record_v2(page_record)
    except ValueError as error:
        raise _error(f"Full Page Record V2 authority drifted: {error}") from error
    if record["route"] == _OCR_ROUTE:
        if (
            type(page_result) is not dict
            or page_result.get("format_version") not in _OCR_RESULT_FORMATS
        ):
            raise _error("OCR result format is unsupported")
        try:
            neutral = project_authenticated_page_v1(
                page_record=_legacy_ocr_record(record),
                page_result=page_result,
            )
        except SourceEvidenceProjectionError as error:
            raise _error("OCR Result V2/V3 projection drifted") from error
        result = canonical_clone_v1(page_result)
        disposition = _IDENTITY_DISPOSITION
        native_policy = None
        native_receipt = None
    else:
        result = _validate_native_result_v2(record, page_result)
        neutral, disposition = _native_v1_compatibility_view(record, result)
        native_policy = canonical_clone_v1(result["ordering_policy_identity"])
        native_receipt = canonical_clone_v1(result["ordering_receipt"])
    result_sha = canonical_json_sha256_v1(result)
    terminal_reason = (
        neutral["terminal_reason"]
        if record["route"] == _OCR_ROUTE
        else _native_terminal_reason(result)
    )
    projection = {
        "format_version": SOURCE_PROJECTION_FORMAT_VERSION_V2,
        "claim_boundary": SOURCE_PROJECTION_CLAIM_BOUNDARY_V2,
        "source_local_page_id": "ssv2:page:" + "0" * 64,
        "source_locator": {
            "source_sha256": record["source_sha256"],
            "source_size_bytes": record["source_size_bytes"],
            "physical_page": record["physical_page"],
            "request_sha256": record["request_sha256"],
        },
        "route": record["route"],
        "upstream_status": record["status"],
        "terminal": record["unresolved"],
        "terminal_reason": terminal_reason,
        "page_record_format_version": record["format_version"],
        "page_record_v2": canonical_clone_v1(record),
        "page_record_sha256": canonical_json_sha256_v1(record),
        "page_result_format_version": result["format_version"],
        "page_result": canonical_clone_v1(result),
        "page_result_ref": canonical_clone_v1(record["result_ref"]),
        "page_result_sha256": result_sha,
        "page_record_accounting": _page_record_accounting(record),
        "coordinate_authority": canonical_clone_v1(result["coordinate_authority"]),
        "native_ordering_policy_identity": native_policy,
        "native_ordering_policy_identity_sha256": (
            canonical_json_sha256_v1(native_policy) if native_policy is not None else None
        ),
        "native_ordering_receipt": native_receipt,
        "native_ordering_receipt_sha256": (
            canonical_json_sha256_v1(native_receipt) if native_receipt is not None else None
        ),
        "v1_compatibility_disposition": disposition,
        "v1_compatibility_view_authoritative": False,
        "neutral_page_v1": neutral,
        "neutral_page_v1_sha256": canonical_json_sha256_v1(neutral),
        "safety": canonical_clone_v1(SOURCE_PROJECTION_SAFETY_V2),
    }
    projection["source_local_page_id"] = (
        f"ssv2:page:{canonical_json_sha256_v1(_identity_payload(projection))}"
    )
    return validate_source_evidence_projection_v2(projection)
