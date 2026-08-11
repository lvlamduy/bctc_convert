"""Build document-local statement-block hypotheses from neutral V2 evidence.

This module is deliberately a candidate-only adapter around the existing V2
page classifier and ordered-block scorer.  It authenticates every source
projection, presents only primary line evidence to those two pure helpers, and
immediately closes their rich transient decisions into a text-free receipt.
It performs no source discovery, provider invocation, semantic acceptance, or
publication.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import pairwise
from math import isfinite
from typing import Any

from bctc_ai.document_phase.statement_locator import (
    OCRLine,
    OCRPage,
    PageDecision,
    StatementLocatorError,
    StatementPageType,
    StatementScope,
    _candidate_blocks,
)
from bctc_ai.document_phase.statement_locator_v2 import classify_statement_page_v2
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import validate_source_evidence_projection_v2

__all__ = [
    "DOCUMENT_STATEMENT_HYPOTHESES_CLAIM_BOUNDARY_V1",
    "DOCUMENT_STATEMENT_HYPOTHESES_FORMAT_VERSION_V1",
    "DocumentStatementHypothesesV1Error",
    "build_document_statement_block_hypotheses_v1",
    "validate_document_statement_block_hypotheses_v1",
]


class DocumentStatementHypothesesV1Error(ValueError):
    """Document-local statement hypotheses crossed their closed boundary."""


DOCUMENT_STATEMENT_HYPOTHESES_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_DOCUMENT_STATEMENT_BLOCK_HYPOTHESES_V1"
)
DOCUMENT_STATEMENT_HYPOTHESES_CLAIM_BOUNDARY_V1 = (
    "ORDERED_DOCUMENT_STATEMENT_FAMILY_AND_BLOCK_HYPOTHESES_ONLY_NO_SEMANTIC_ACCEPTANCE"
)
_POLICY_RECEIPT_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_STATEMENT_HYPOTHESIS_POLICY_RECEIPT_V1"
_ARTIFACT_ID_PREFIX = "ssdv1:document:"
_PAGE_HYPOTHESIS_ID_PREFIX = "ssdv1:page-hypothesis:"
_BLOCK_HYPOTHESIS_ID_PREFIX = "ssdv1:block-hypothesis:"
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_PRIMARY = "AUTHENTICATED_PRIMARY"
_LINE = "LINE"
_FAMILIES = ("CDKT", "KQKD", "LCTT", "TM")
_PAGE_FAMILIES = (
    "CDKT",
    "KQKD",
    "LCTT",
    "TM",
    "AUDIT_REPORT",
    "TABLE_OF_CONTENTS",
    "AMBIGUOUS",
    "OTHER",
    "UPSTREAM_TERMINAL",
)
_PAGE_DISPOSITIONS = (
    "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS",
    "RETAINED_UNRESOLVED",
    "UPSTREAM_TERMINAL_UNRESOLVED",
)
_EVIDENCE_CODES = (
    "AMBIGUOUS_FAMILY_SIGNAL_HYPOTHESIS",
    "AUDIT_SUPPRESSION_SIGNAL_HYPOTHESIS",
    "CONTINUATION_MARKER_SIGNAL_HYPOTHESIS",
    "FORM_FAMILY_SIGNAL_HYPOTHESIS",
    "NO_FAMILY_SIGNAL_RETAINED",
    "NUMERIC_TOKEN_DENSITY_SIGNAL_HYPOTHESIS",
    "OFF_BALANCE_SIGNAL_HYPOTHESIS",
    "TITLE_DISCRIMINATOR_SIGNAL_HYPOTHESIS",
    "TITLE_SIGNAL_HYPOTHESIS",
    "TOC_SUPPRESSION_SIGNAL_HYPOTHESIS",
    "UPSTREAM_TERMINAL_BARRIER",
)
_POLICY_ANCHOR_MAP_KEYS = (
    "form_anchors",
    "title_anchors",
    "title_discriminator_anchors",
)
_POLICY_ANCHOR_LIST_KEYS = (
    "audit_anchors",
    "toc_anchors",
    "continuation_anchors",
    "off_balance_heading_anchors",
    "off_balance_item_anchors",
)
_POLICY_FLOAT_KEYS = (
    "header_fraction",
    "title_min_similarity",
    "title_min_margin",
    "continuation_title_min_similarity",
    "continuation_anchor_min_similarity",
    "title_only_min_numeric_line_fraction",
    "title_discriminator_min_similarity",
    "audit_min_similarity",
    "toc_min_similarity",
    "off_balance_heading_min_similarity",
    "off_balance_item_min_similarity",
)
_POLICY_INTEGER_KEYS = (
    "toc_min_distinct_statement_titles",
    "off_balance_min_item_hits",
    "max_interstitial_pages",
)
_WEIGHT_KEYS = (
    "start_form_anchor",
    "form_anchor_page",
    "average_confidence",
)
_USED_POLICY_KEYS = (
    "version",
    "policy",
    "v2",
    *_POLICY_ANCHOR_MAP_KEYS,
    *_POLICY_ANCHOR_LIST_KEYS,
    *_POLICY_FLOAT_KEYS,
    *_POLICY_INTEGER_KEYS,
    "candidate_score_weights",
)
_POLICY_NAME = "GENERAL_ORDERED_STATEMENT_BLOCK_UNICODE_FORM_FAMILY_V2"
_USED_POLICY_SHA256 = "a55cb6fb9281fff6d20d7883b0fc761111a88406e6398d3ab8af8a9aefa61fe5"
_V2_IDENTITY = {
    "configuration_name": "statement-locator-v2.yaml",
    "base_configuration_name": "statement-locator-v1.yaml",
    "base_configuration_sha256": (
        "d25ff6da2a1ce48428b4ab1ac20a31b989a27849d93326ae839507dce2ff107e"
    ),
    "form_family_matching": {
        "strategy": "REGEX_CANONICAL_FAMILY_WITH_OPTIONAL_SINGLE_ASCII_SUFFIX",
        "normalized_families": ["B02", "B03", "B04", "B05"],
        "required_context_token": "TCTD",
        "permit_optional_hn_token": True,
    },
    "title_matching": {
        "strategy": "TOKEN_BOUNDARY_CORE_CONTAINMENT_THEN_FULL_EDIT_RATIO",
        "exact_containment_score": 1.0,
        "require_existing_discriminator_and_table_gates": True,
    },
    "forbidden_inputs": [
        "bank_identity",
        "filename_identity",
        "page_number_rules",
        "numeric_values_for_page_type",
        "historical_values",
        "report_norm_id_numeric_order",
    ],
}
_SAFETY = {
    "candidate_hypotheses_only": True,
    "source_text_persisted": False,
    "semantic_acceptance_claimed": False,
    "statement_identity_claimed": False,
    "statement_block_accepted": False,
    "statement_family_accepted": False,
    "table_claimed": False,
    "row_claimed": False,
    "cell_claimed": False,
    "axis_claimed": False,
    "hierarchy_claimed": False,
    "scope_truth_claimed": False,
    "mapping_claimed": False,
    "cash_flow_method_claimed": False,
    "schema_used_for_routing": False,
    "absence_claimed": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "note_number_rules_used_for_routing": False,
    "exact_page_number_used_for_routing": False,
    "role_a_used_for_routing": False,
    "historical_values_used_for_routing": False,
    "external_identity_routing_used": False,
    "source_location_used_for_family_classification": False,
    "exact_sequence_number_used_for_routing": False,
    "numeric_magnitude_used_for_family_classification": False,
    "role_a_or_schema_reference_data_used": False,
    "upstream_provider_invoked": False,
}


def _error(message: str) -> DocumentStatementHypothesesV1Error:
    return DocumentStatementHypothesesV1Error(message)


def _plain_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(f"{label} must be a mapping")
    return value


def _anchor_list(value: Any, label: str) -> list[str]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not str or not item for item in value)
    ):
        raise _error(f"{label} must be a nonempty string list")
    return list(value)


def _finite_float(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(f"{label} must be numeric")
    result = float(value)
    if not isfinite(result) or (positive and result <= 0):
        raise _error(f"{label} is outside its finite domain")
    return result


def _normalized_policy(locator_policy: Mapping[str, Any]) -> dict[str, Any]:
    policy = _plain_mapping(locator_policy, "locator policy")
    if (
        policy.get("version") != 2
        or policy.get("policy") != _POLICY_NAME
        or not isinstance(policy.get("v2"), Mapping)
        or not same_typed_json_v1(policy["v2"], _V2_IDENTITY)
    ):
        raise _error("locator policy must expose the V2 classifier contract")
    normalized: dict[str, Any] = {
        "version": 2,
        "policy": _POLICY_NAME,
        "v2": canonical_clone_v1(_V2_IDENTITY),
    }
    for key in _POLICY_ANCHOR_MAP_KEYS:
        raw = _plain_mapping(policy.get(key), f"locator policy {key}")
        if set(raw) != set(_FAMILIES):
            raise _error(f"locator policy {key} family axis drifted")
        normalized[key] = {
            family: _anchor_list(raw[family], f"locator policy {key}.{family}")
            for family in _FAMILIES
        }
    for key in _POLICY_ANCHOR_LIST_KEYS:
        normalized[key] = _anchor_list(policy.get(key), f"locator policy {key}")
    for key in _POLICY_FLOAT_KEYS:
        value = _finite_float(policy.get(key), f"locator policy {key}")
        if not 0.0 <= value <= 1.0:
            raise _error(f"locator policy {key} lies outside [0, 1]")
        normalized[key] = value
    for key in _POLICY_INTEGER_KEYS:
        value = policy.get(key)
        if type(value) is not int or value < 0:
            raise _error(f"locator policy {key} must be a nonnegative integer")
        normalized[key] = value
    if normalized["max_interstitial_pages"] != 0:
        raise _error("statement hypotheses may not skip an interstitial page")
    if not 1 <= normalized["toc_min_distinct_statement_titles"] <= len(_FAMILIES):
        raise _error("contents-title gate is outside the family axis")
    if (
        not 1
        <= normalized["off_balance_min_item_hits"]
        <= len(normalized["off_balance_item_anchors"])
    ):
        raise _error("off-balance signal gate is outside its anchor axis")
    raw_weights = _plain_mapping(
        policy.get("candidate_score_weights"),
        "locator policy candidate-score weights",
    )
    if set(raw_weights) != set(_WEIGHT_KEYS):
        raise _error("locator policy candidate-score weight axis drifted")
    normalized["candidate_score_weights"] = {
        key: _finite_float(
            raw_weights[key],
            f"locator policy candidate-score weight {key}",
            positive=True,
        )
        for key in _WEIGHT_KEYS
    }
    if canonical_json_sha256_v1(normalized) != _USED_POLICY_SHA256:
        raise _error("locator policy keys used by statement hypotheses drifted")
    return normalized


def _policy_receipt(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "format_version": _POLICY_RECEIPT_FORMAT_VERSION,
        "classifier_revision": "STATEMENT_PAGE_CLASSIFIER_V2",
        "block_scorer_revision": "ORDERED_CANDIDATE_BLOCK_SCORER_V1",
        "used_keys": list(_USED_POLICY_KEYS),
        "used_policy_sha256": canonical_json_sha256_v1(policy),
    }


def _dimensions(projection: Mapping[str, Any]) -> tuple[int, int]:
    authority = projection["coordinate_authority"]
    route = projection["route"]
    if route == _OCR_ROUTE:
        dimensions = authority["unrotated_dimensions_mpt"]
        width, height = dimensions
    elif route == _NATIVE_ROUTE:
        x0, y0, x1, y1 = authority["canonical_cropbox_bounds_mpt"]
        width, height = x1 - x0, y1 - y0
    else:  # validated V2 projections make this unreachable
        raise _error("source projection route is unsupported")
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise _error("source projection dimensions are not positive integers")
    return width, height


def _ocr_page(
    projection: Mapping[str, Any],
    *,
    input_ordinal: int,
) -> OCRPage:
    width, height = _dimensions(projection)
    lines: list[OCRLine] = []
    if projection["terminal"] is False:
        for atom in projection["neutral_page_v1"]["atoms"]:
            if atom["kind"] != _LINE or atom["authority"] != _PRIMARY:
                continue
            box = atom["canonical_bbox_mpt"]
            if (
                type(box) is not list
                or len(box) != 4
                or any(type(item) is not int for item in box)
                or not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)
            ):
                raise _error("primary line geometry drifted")
            text = atom["raw_text"]
            if type(text) is not str or not text:
                raise _error("primary line source text drifted")
            score = atom["score"] if atom["score"] is not None else 0.0
            if type(score) is not float or not isfinite(score) or not 0.0 <= score <= 1.0:
                raise _error("primary line transport score drifted")
            lines.append(
                OCRLine(
                    text=text,
                    bbox=tuple(float(item) for item in box),
                    score=score,
                )
            )
    return OCRPage(
        page=input_ordinal,
        width=width,
        height=height,
        lines=tuple(lines),
    )


def _terminal_decision(input_ordinal: int) -> PageDecision:
    zero_scores = {family: 0.0 for family in _FAMILIES}
    return PageDecision(
        page=input_ordinal,
        page_type=StatementPageType.OTHER,
        scope=StatementScope.NOT_APPLICABLE,
        mapping_eligible=False,
        confidence=0.0,
        form_hits=(),
        title_scores=zero_scores,
        title_discriminator_scores=dict(zero_scores),
        evidence=(),
        off_balance_item_hits=(),
        numeric_line_fraction=0.0,
        is_continuation=False,
    )


def _evidence_codes(
    decision: PageDecision,
    *,
    terminal: bool,
    policy: Mapping[str, Any],
) -> list[str]:
    if terminal:
        return ["UPSTREAM_TERMINAL_BARRIER"]
    codes: set[str] = set()
    if decision.form_hits:
        codes.add("FORM_FAMILY_SIGNAL_HYPOTHESIS")
    if max(decision.title_scores.values(), default=0.0) >= policy["title_min_similarity"]:
        codes.add("TITLE_SIGNAL_HYPOTHESIS")
    if (
        max(decision.title_discriminator_scores.values(), default=0.0)
        >= policy["title_discriminator_min_similarity"]
    ):
        codes.add("TITLE_DISCRIMINATOR_SIGNAL_HYPOTHESIS")
    if decision.numeric_line_fraction >= policy["title_only_min_numeric_line_fraction"]:
        codes.add("NUMERIC_TOKEN_DENSITY_SIGNAL_HYPOTHESIS")
    if decision.is_continuation:
        codes.add("CONTINUATION_MARKER_SIGNAL_HYPOTHESIS")
    if decision.off_balance_item_hits or decision.scope is StatementScope.OFF_BALANCE_SHEET:
        codes.add("OFF_BALANCE_SIGNAL_HYPOTHESIS")
    if decision.page_type is StatementPageType.TABLE_OF_CONTENTS:
        codes.add("TOC_SUPPRESSION_SIGNAL_HYPOTHESIS")
    elif decision.page_type is StatementPageType.AUDIT_REPORT:
        codes.add("AUDIT_SUPPRESSION_SIGNAL_HYPOTHESIS")
    elif decision.page_type is StatementPageType.AMBIGUOUS:
        codes.add("AMBIGUOUS_FAMILY_SIGNAL_HYPOTHESIS")
    if not codes:
        codes.add("NO_FAMILY_SIGNAL_RETAINED")
    if not codes <= set(_EVIDENCE_CODES):  # pragma: no cover - local vocabulary guard
        raise _error("page hypothesis evidence vocabulary drifted")
    return sorted(codes)


def _page_hypothesis(
    *,
    binding: Mapping[str, Any],
    decision: PageDecision,
    policy: Mapping[str, Any],
    policy_sha256: str,
) -> dict[str, Any]:
    terminal = binding["terminal"]
    payload = {
        "input_ordinal": binding["input_ordinal"],
        "source_local_page_id": binding["source_local_page_id"],
        "source_projection_sha256": binding["source_projection_sha256"],
        "upstream_status": binding["upstream_status"],
        "terminal": terminal,
        "family_hypothesis": ("UPSTREAM_TERMINAL" if terminal else decision.page_type.value),
        "diagnostic_score": 0.0 if terminal else decision.confidence,
        "evidence_codes": _evidence_codes(decision, terminal=terminal, policy=policy),
        "continuation_marker_hypothesis": False if terminal else decision.is_continuation,
    }
    identity = {
        "used_policy_sha256": policy_sha256,
        **payload,
    }
    return {
        "page_hypothesis_id": (_PAGE_HYPOTHESIS_ID_PREFIX + canonical_json_sha256_v1(identity)),
        **payload,
    }


def _block_hypotheses(
    raw_candidates: Sequence[Mapping[str, Any]],
    *,
    page_hypotheses_by_ordinal: Mapping[int, Mapping[str, Any]],
    source_sha256: str,
    policy_sha256: str,
) -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []
    for rank, candidate in enumerate(raw_candidates, start=1):
        members = [page_hypotheses_by_ordinal[item.page] for item in candidate["pages"]]
        boundary = page_hypotheses_by_ordinal[candidate["notes_boundary_page"]]
        payload = {
            "start_input_ordinal": candidate["start_page"],
            "end_input_ordinal": candidate["end_page"],
            "member_page_hypothesis_ids": [item["page_hypothesis_id"] for item in members],
            "family_sequence_hypothesis": [item["family_hypothesis"] for item in members],
            "family_evidence_codes": [item["evidence_codes"] for item in members],
            "tm_boundary_hypothesis_id": boundary["page_hypothesis_id"],
            "diagnostic_score": candidate["score"],
            "diagnostic_score_components": {
                "start_form_signal": candidate["score_components"]["start_form_anchor"],
                "form_signal_page_count": candidate["score_components"]["form_anchor_page_count"],
                "average_family_confidence": candidate["score_components"]["average_confidence"],
            },
        }
        candidate_identity = {
            "source_sha256": source_sha256,
            "used_policy_sha256": policy_sha256,
            **payload,
        }
        hypotheses.append(
            {
                "block_hypothesis_id": (
                    _BLOCK_HYPOTHESIS_ID_PREFIX + canonical_json_sha256_v1(candidate_identity)
                ),
                "rank": rank,
                **payload,
            }
        )
    return hypotheses


def _validated_sources(
    page_projections: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    if isinstance(page_projections, (str, bytes)) or not isinstance(page_projections, Sequence):
        raise _error("page projections must be a nonstring sequence")
    if not page_projections:
        raise _error("document hypotheses require at least one page projection")
    sources: list[dict[str, Any]] = []
    try:
        for projection in page_projections:
            sources.append(validate_source_evidence_projection_v2(projection))
    except ValueError as exc:
        raise _error("document source projection authority drifted") from exc
    source_sha256 = sources[0]["source_locator"]["source_sha256"]
    if any(source["source_locator"]["source_sha256"] != source_sha256 for source in sources):
        raise _error("document source projections do not share one source identity")
    page_ids = [source["source_local_page_id"] for source in sources]
    if len(page_ids) != len(set(page_ids)):
        raise _error("document source page identities are not unique")
    source_axis = [source["source_locator"]["physical_page"] for source in sources]
    if any(current != prior + 1 for prior, current in pairwise(source_axis)):
        raise _error("document source page axis is not contiguous in authenticated input order")
    return sources, source_sha256


def _build_expected(
    page_projections: Sequence[Mapping[str, Any]],
    *,
    locator_policy: Mapping[str, Any],
) -> dict[str, Any]:
    sources, source_sha256 = _validated_sources(page_projections)
    policy = _normalized_policy(locator_policy)
    receipt = _policy_receipt(policy)
    bindings = [
        {
            "input_ordinal": ordinal,
            "source_local_page_id": source["source_local_page_id"],
            "source_projection_sha256": canonical_json_sha256_v1(source),
            "route": source["route"],
            "upstream_status": source["upstream_status"],
            "terminal": source["terminal"],
        }
        for ordinal, source in enumerate(sources, start=1)
    ]
    decisions: list[PageDecision] = []
    try:
        for ordinal, source in enumerate(sources, start=1):
            if source["terminal"]:
                decisions.append(_terminal_decision(ordinal))
            else:
                decisions.append(
                    classify_statement_page_v2(
                        _ocr_page(source, input_ordinal=ordinal),
                        policy,
                    )
                )
        raw_candidates = _candidate_blocks(tuple(decisions), policy)
    except (KeyError, TypeError, ValueError, StatementLocatorError) as exc:
        raise _error("statement-family hypothesis core rejected neutral evidence") from exc
    page_hypotheses = [
        _page_hypothesis(
            binding=binding,
            decision=decision,
            policy=policy,
            policy_sha256=receipt["used_policy_sha256"],
        )
        for binding, decision in zip(bindings, decisions, strict=True)
    ]
    by_ordinal = {item["input_ordinal"]: item for item in page_hypotheses}
    block_hypotheses = _block_hypotheses(
        raw_candidates,
        page_hypotheses_by_ordinal=by_ordinal,
        source_sha256=source_sha256,
        policy_sha256=receipt["used_policy_sha256"],
    )
    candidate_ids_by_ordinal: dict[int, list[str]] = {
        ordinal: [] for ordinal in range(1, len(sources) + 1)
    }
    for block in block_hypotheses:
        cited = [
            *block["member_page_hypothesis_ids"],
            block["tm_boundary_hypothesis_id"],
        ]
        cited_set = set(cited)
        for hypothesis in page_hypotheses:
            if hypothesis["page_hypothesis_id"] in cited_set:
                candidate_ids_by_ordinal[hypothesis["input_ordinal"]].append(
                    block["block_hypothesis_id"]
                )
    page_dispositions = []
    for hypothesis in page_hypotheses:
        ordinal = hypothesis["input_ordinal"]
        candidate_ids = candidate_ids_by_ordinal[ordinal]
        disposition = (
            "UPSTREAM_TERMINAL_UNRESOLVED"
            if hypothesis["terminal"]
            else ("SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS" if candidate_ids else "RETAINED_UNRESOLVED")
        )
        page_dispositions.append(
            {
                "input_ordinal": ordinal,
                "source_local_page_id": hypothesis["source_local_page_id"],
                "page_hypothesis_id": hypothesis["page_hypothesis_id"],
                "primary_disposition": disposition,
                "block_hypothesis_ids": candidate_ids,
            }
        )
    disposition_counts = Counter(item["primary_disposition"] for item in page_dispositions)
    family_counts = Counter(item["family_hypothesis"] for item in page_hypotheses)
    evidence_counts = Counter(code for item in page_hypotheses for code in item["evidence_codes"])
    artifact = {
        "format_version": DOCUMENT_STATEMENT_HYPOTHESES_FORMAT_VERSION_V1,
        "claim_boundary": DOCUMENT_STATEMENT_HYPOTHESES_CLAIM_BOUNDARY_V1,
        "status": (
            "CANDIDATES_EMITTED"
            if block_hypotheses
            else "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS"
        ),
        "source_sha256": source_sha256,
        "locator_policy_receipt": receipt,
        "page_projection_bindings": bindings,
        "page_hypotheses": page_hypotheses,
        "block_hypotheses": block_hypotheses,
        "page_dispositions": page_dispositions,
        "metrics": {
            "page_count": len(sources),
            "terminal_page_count": sum(source["terminal"] for source in sources),
            "block_hypothesis_count": len(block_hypotheses),
            "page_disposition_counts": {key: disposition_counts[key] for key in _PAGE_DISPOSITIONS},
            "family_hypothesis_counts": {key: family_counts[key] for key in _PAGE_FAMILIES},
            "evidence_code_counts": {key: evidence_counts[key] for key in _EVIDENCE_CODES},
        },
        "safety": canonical_clone_v1(_SAFETY),
        "document_hypotheses_identity": _ARTIFACT_ID_PREFIX + "0" * 64,
    }
    identity_payload = {
        key: artifact[key] for key in artifact if key != "document_hypotheses_identity"
    }
    artifact["document_hypotheses_identity"] = _ARTIFACT_ID_PREFIX + canonical_json_sha256_v1(
        identity_payload
    )
    return canonical_clone_v1(artifact)


def build_document_statement_block_hypotheses_v1(
    page_projections: Sequence[Mapping[str, Any]],
    *,
    locator_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one canonical, candidate-only document hypothesis artifact."""

    artifact = _build_expected(page_projections, locator_policy=locator_policy)
    return validate_document_statement_block_hypotheses_v1(
        artifact,
        page_projections,
        locator_policy=locator_policy,
    )


def validate_document_statement_block_hypotheses_v1(
    value: Mapping[str, Any],
    page_projections: Sequence[Mapping[str, Any]],
    *,
    locator_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute and validate every authority, hypothesis, and disposition."""

    if type(value) is not dict:
        raise _error("document statement hypotheses must be a plain object")
    expected = _build_expected(page_projections, locator_policy=locator_policy)
    if not same_typed_json_v1(value, expected):
        raise _error("document statement hypotheses drifted from authenticated inputs")
    return canonical_clone_v1(expected)
