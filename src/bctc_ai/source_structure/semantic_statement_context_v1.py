"""Replay-authenticated statement/scope context from a visible page heading.

The contract consumes the exact all-LINE VietOCR Transformer page binding and
recognizes only frozen full-heading surfaces.  It does not use PP-OCR text,
filename/bank/page metadata, Role A, or schema context as semantic authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    validate_vietocr_semantic_page_binding_v2,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "SAFETY",
    "SemanticStatementContextV1Error",
    "build_semantic_statement_context_v1",
    "validate_semantic_statement_context_replay_v1",
]


FORMAT_VERSION = "BANK_CORPUS_SEMANTIC_STATEMENT_CONTEXT_V1"
CLAIM_BOUNDARY = (
    "SOURCE_BOUND_EXACT_VIETOCR_VISIBLE_PAGE_HEADING_TO_LOCAL_STATEMENT_SCOPE_CONTEXT_ONLY_"
    "NO_DOCUMENT_COMPLETION_SCHEMA_MAPPING_NUMERIC_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
RESOLVED_STATUS = "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
UNRESOLVED_STATUS = "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
_HEADING_RULES = {
    "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT": ("TM", "CONSOLIDATED", False),
    "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT (TIẾP THEO)": (
        "TM",
        "CONSOLIDATED",
        True,
    ),
    "THUYẾT MINH BÁO CÁO TÀI CHÍNH RIÊNG": ("TM", "SEPARATE", False),
    "THUYẾT MINH BÁO CÁO TÀI CHÍNH RIÊNG (TIẾP THEO)": ("TM", "SEPARATE", True),
}
_SAFETY_ITEMS: tuple[tuple[str, bool], ...] = (
    ("exact_full_heading_surface_required", True),
    ("accentless_key_used_for_acceptance", False),
    ("ppocr_text_used_for_statement_or_scope", False),
    ("filename_bank_page_metadata_used_for_statement_or_scope", False),
    ("role_a_used_for_statement_or_scope", False),
    ("schema_used_for_statement_or_scope", False),
    ("page_local_context_only", True),
    ("document_statement_page_completion_claimed", False),
    ("numeric_authority", False),
    ("schema_mapping_authority", False),
    ("canonicalization_authority", False),
    ("export_authority", False),
)
SAFETY: Mapping[str, bool] = MappingProxyType(dict(_SAFETY_ITEMS))


class SemanticStatementContextV1Error(ValueError):
    """The page binding, statement context, or exact replay drifted."""


def _error(message: str) -> SemanticStatementContextV1Error:
    return SemanticStatementContextV1Error(message)


def _fixed_safety() -> dict[str, bool]:
    return dict(_SAFETY_ITEMS)


def _build(binding: dict[str, Any]) -> dict[str, Any]:
    matches: list[tuple[dict[str, Any], tuple[str, str, bool]]] = []
    for sample in binding["samples"]:
        raw = sample["raw_prediction"]
        if raw in _HEADING_RULES:
            matches.append((sample, _HEADING_RULES[raw]))
    unique_semantics = {semantics for _, semantics in matches}
    if len(matches) == 1 and len(unique_semantics) == 1:
        sample, (statement_type, report_scope, continuation) = matches[0]
        status = RESOLVED_STATUS
        evidence = {
            "sample_id": sample["sample_id"],
            "source_atom_id": sample["source_atom"]["source_atom_id"],
            "source_line_index": sample["source_line_index"],
            "raw_transformer_text_utf8": sample["raw_prediction"],
            "normalized_transformer_text_nfc": normalize_text(sample["raw_prediction"]),
            "accentless_diagnostic_key": retrieval_key(sample["raw_prediction"]),
            "crop_ref": canonical_clone_v1(sample["crop_ref"]),
            "source_bbox_raw_pixels": canonical_clone_v1(sample["source_bbox_raw_pixels"]),
            "canonical_bbox_mpt": canonical_clone_v1(sample["source_atom"]["canonical_bbox_mpt"]),
        }
        unresolved_reasons: list[str] = []
    else:
        status = UNRESOLVED_STATUS
        statement_type = None
        report_scope = None
        continuation = None
        evidence = None
        unresolved_reasons = [
            "NO_EXACT_SUPPORTED_VISIBLE_PAGE_HEADING"
            if not matches
            else "MULTIPLE_OR_CONFLICTING_VISIBLE_PAGE_HEADINGS"
        ]
    payload = {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": status,
        "source_local_page_id": binding["source_local_page_id"],
        "source_projection_sha256": binding["source_projection_sha256"],
        "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
        "statement_type": statement_type,
        "report_scope": report_scope,
        "continuation": continuation,
        "heading_evidence": evidence,
        "unresolved_reasons": unresolved_reasons,
        "readiness": {
            "page_statement_context_resolved": status == RESOLVED_STATUS,
            "document_statement_page_completion_claimed": False,
            "schema_mapping_ready": False,
            "export_eligible": False,
        },
        "safety": _fixed_safety(),
    }
    payload["context_id"] = f"sscxtv1:context:{canonical_json_sha256_v1(payload)}"
    return payload


def _validate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error("statement context must be one object")
    expected = {
        "format_version",
        "claim_boundary",
        "context_id",
        "status",
        "source_local_page_id",
        "source_projection_sha256",
        "semantic_page_binding_sha256",
        "statement_type",
        "report_scope",
        "continuation",
        "heading_evidence",
        "unresolved_reasons",
        "readiness",
        "safety",
    }
    if (
        set(value) != expected
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["safety"] != _fixed_safety()
    ):
        raise _error("statement context contract or safety drifted")
    clone = canonical_clone_v1(value)
    context_id = clone.pop("context_id")
    if context_id != f"sscxtv1:context:{canonical_json_sha256_v1(clone)}":
        raise _error("statement context identity drifted")
    return canonical_clone_v1(value)


def build_semantic_statement_context_v1(
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
) -> dict[str, Any]:
    """Resolve one local visible page heading or emit explicit unresolved."""

    try:
        binding = validate_vietocr_semantic_page_binding_v2(
            semantic_page_binding_v2,
            source_projection_v2,
            authenticated_transformer_receipt_v2,
        )
    except ValueError as exc:
        raise _error("statement context requires an exact replayed page binding") from exc
    return _validate(_build(binding))


def validate_semantic_statement_context_replay_v1(
    value: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
) -> dict[str, Any]:
    """Rebuild and typed-compare a persisted statement context."""

    persisted = _validate(value)
    rebuilt = build_semantic_statement_context_v1(
        source_projection_v2,
        semantic_page_binding_v2,
        authenticated_transformer_receipt_v2,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("statement context does not replay from exact authenticated inputs")
    return canonical_clone_v1(rebuilt)
