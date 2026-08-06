from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_vietnamese_dates,
    retrieval_key,
)
from bctc_ai.document_phase.statement_locator import OCRLine, OCRPage


class SemanticLineFusionError(RuntimeError):
    pass


class SemanticFieldRole(StrEnum):
    TITLE = "TITLE"
    LABEL = "LABEL"
    SECTION = "SECTION"
    METHOD = "METHOD"
    FORM_CODE = "FORM_CODE"
    SCOPE_WORDING = "SCOPE_WORDING"
    READING_ORDER_LABEL_GROUP = "READING_ORDER_LABEL_GROUP"


class SemanticProposalStatus(StrEnum):
    EMITTED = "SEMANTIC_PROPOSAL_EMITTED"
    REJECTED = "SEMANTIC_PROPOSAL_REJECTED"


@dataclass(frozen=True)
class SemanticLineFusionConfig:
    maximum_source_lines_per_proposal: int
    maximum_nonempty_output_lines: int
    minimum_missing_suffix_characters: int
    minimum_missing_suffix_fraction: float
    allowed_field_roles: tuple[SemanticFieldRole, ...]


@dataclass(frozen=True)
class SemanticLineProposal:
    proposal_id: str
    reader: str
    page: int
    source_line_indices: tuple[int, ...]
    source_texts: tuple[str, ...]
    source_bboxes: tuple[tuple[float, float, float, float], ...]
    field_role: SemanticFieldRole
    raw_proposal_text: str
    crop_sha256: str
    reader_score: float | None = None


@dataclass(frozen=True)
class SemanticLineDecision:
    proposal_id: str
    reader: str
    page: int
    source_line_indices: tuple[int, ...]
    source_texts: tuple[str, ...]
    source_bboxes: tuple[tuple[float, float, float, float], ...]
    field_role: str
    raw_proposal_text: str
    normalized_proposal_text: str
    crop_sha256: str
    reader_score: float | None
    status: str
    reason: str
    emitted_bbox: tuple[float, float, float, float] | None
    confidence_effect: str
    geometry_effect: str
    automatic_authority: bool


@dataclass(frozen=True)
class SemanticLineFusionResult:
    semantic_pages: tuple[OCRPage, ...]
    decisions: tuple[SemanticLineDecision, ...]
    emitted_count: int
    rejected_count: int
    geometry_pages_unchanged: bool
    numeric_period_unit_sign_authority: bool
    statement_scope_mapping_truth_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": "SOURCE_BOX_PRESERVING_MULTI_READER_SEMANTIC_FUSION_V1",
            "emitted_count": self.emitted_count,
            "rejected_count": self.rejected_count,
            "geometry_pages_unchanged": self.geometry_pages_unchanged,
            "numeric_period_unit_sign_authority": self.numeric_period_unit_sign_authority,
            "statement_scope_mapping_truth_authority": (
                self.statement_scope_mapping_truth_authority
            ),
            "decisions": [asdict(item) for item in self.decisions],
        }


_SHA256 = re.compile(r"[0-9a-f]{64}")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_FORM_CODE = re.compile(r"\bB[0O](?P<number>[2345])(?P<suffix>[A-Za-z]?)\b", re.IGNORECASE)
_MARKUP = re.compile(r"(?:<\|/?(?:ref|det|grounding)\|>|```|^\s*\|.*\|\s*$)", re.MULTILINE)
_FINANCIAL_OBSERVATIONS = {
    ObservationKind.VALUE,
    ObservationKind.ZERO,
    ObservationKind.DASH,
}


def load_semantic_line_fusion_config(path: Path) -> SemanticLineFusionConfig:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SemanticLineFusionError(f"cannot load semantic-line fusion config: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy")
        != "SOURCE_BOX_PRESERVING_MULTI_READER_SEMANTIC_FUSION_V1"
        or payload.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or payload.get("semantic_authority")
        != "TITLE_LABEL_READING_ORDER_PROPOSAL_ONLY"
    ):
        raise SemanticLineFusionError("semantic-line fusion identity or authority drifted")
    binding = payload.get("source_binding")
    safety = payload.get("proposal_safety")
    forbidden = payload.get("forbidden_authority")
    if not all(isinstance(item, dict) for item in (binding, safety, forbidden)):
        raise SemanticLineFusionError("semantic-line fusion policy is incomplete")
    assert isinstance(binding, dict)
    assert isinstance(safety, dict)
    assert isinstance(forbidden, dict)
    required_binding = {
        "exact_source_text": True,
        "exact_source_bbox": True,
        "require_monotone_unique_line_indices": True,
        "union_bbox_must_be_derived_from_source_boxes": True,
    }
    if any(binding.get(key) is not value for key, value in required_binding.items()):
        raise SemanticLineFusionError("source binding no longer preserves exact PP-OCR geometry")
    required_safety = {
        "reject_markdown_or_layout_serialization": True,
        "reject_numeric_fields": True,
        "reject_period_fields": True,
        "reject_unit_fields": True,
        "reject_sign_only_fields": True,
        "form_code_family_must_match_source": True,
        "reader_probability_is_not_an_acceptance_gate": True,
    }
    if any(safety.get(key) is not value for key, value in required_safety.items()):
        raise SemanticLineFusionError("semantic proposal safety policy drifted")
    if not forbidden or any(bool(value) for value in forbidden.values()):
        raise SemanticLineFusionError("semantic-line fusion grants forbidden authority")

    allowed_values = payload.get("allowed_field_roles")
    if not isinstance(allowed_values, list) or set(allowed_values) != {
        role.value for role in SemanticFieldRole
    }:
        raise SemanticLineFusionError("semantic field-role allowlist is incomplete")

    def positive_integer(mapping: dict[str, Any], key: str) -> int:
        value = mapping.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise SemanticLineFusionError(f"invalid semantic-line fusion integer: {key}")
        return value

    fraction = safety.get("minimum_missing_suffix_fraction")
    if (
        isinstance(fraction, bool)
        or not isinstance(fraction, (int, float))
        or not 0 < float(fraction) < 1
    ):
        raise SemanticLineFusionError("invalid semantic-line truncation fraction")
    return SemanticLineFusionConfig(
        maximum_source_lines_per_proposal=positive_integer(
            binding, "maximum_source_lines_per_proposal"
        ),
        maximum_nonempty_output_lines=positive_integer(
            safety, "maximum_nonempty_output_lines"
        ),
        minimum_missing_suffix_characters=positive_integer(
            safety, "minimum_missing_suffix_characters"
        ),
        minimum_missing_suffix_fraction=float(fraction),
        allowed_field_roles=tuple(SemanticFieldRole(value) for value in allowed_values),
    )


def _union_bbox(
    boxes: tuple[tuple[float, float, float, float], ...],
) -> tuple[float, float, float, float]:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _form_families(text: str) -> tuple[str, ...]:
    return tuple(sorted({f"B0{match.group('number')}" for match in _FORM_CODE.finditer(text)}))


def _digits_outside_form_codes(text: str) -> bool:
    return bool(re.search(r"\d", _FORM_CODE.sub("", text)))


def _is_unit_field(text: str) -> bool:
    key = retrieval_key(text)
    if not key:
        return False
    phrases = (
        "trieu dong",
        "nghin dong",
        "ngan dong",
        "ty dong",
        "trieu vnd",
        "nghin vnd",
        "vnd million",
        "dong viet nam",
    )
    return (
        key in {"vnd", "dong", *phrases}
        or any(phrase in key for phrase in phrases)
        or key.startswith("don vi tinh")
    )


def _protected_field_reason(
    source_text: str,
    proposal_text: str,
    role: SemanticFieldRole,
) -> str | None:
    for name, text in (("SOURCE", source_text), ("PROPOSAL", proposal_text)):
        parsed = parse_financial_number(text)
        if parsed.observation in _FINANCIAL_OBSERVATIONS:
            return f"{name}_IS_NUMERIC_OR_SIGN_FIELD"
        if parse_vietnamese_dates(text) or _YEAR.search(text):
            return f"{name}_IS_PERIOD_FIELD"
        if _is_unit_field(text):
            return f"{name}_IS_UNIT_FIELD"

    if role is SemanticFieldRole.FORM_CODE:
        source_families = _form_families(source_text)
        proposal_families = _form_families(proposal_text)
        if not source_families or source_families != proposal_families:
            return "FORM_CODE_FAMILY_NOT_SOURCE_VERIFIED"
        if _digits_outside_form_codes(source_text) or _digits_outside_form_codes(proposal_text):
            return "DIGITS_OUTSIDE_VERIFIED_FORM_CODE"
        return None
    if re.search(r"\d", source_text) or re.search(r"\d", proposal_text):
        return "DIGIT_BEARING_NON_FORM_TEXT"
    return None


def _suffix_truncated(
    source_text: str,
    proposal_text: str,
    config: SemanticLineFusionConfig,
) -> bool:
    source = retrieval_key(source_text)
    proposal = retrieval_key(proposal_text)
    if not source or not proposal or len(proposal) >= len(source):
        return False
    if not source.startswith(proposal):
        return False
    missing = len(source) - len(proposal)
    return (
        missing >= config.minimum_missing_suffix_characters
        and missing / len(source) >= config.minimum_missing_suffix_fraction
    )


def _decision(
    proposal: SemanticLineProposal,
    *,
    status: SemanticProposalStatus,
    reason: str,
    normalized_text: str,
    bbox: tuple[float, float, float, float] | None,
) -> SemanticLineDecision:
    return SemanticLineDecision(
        proposal_id=proposal.proposal_id,
        reader=proposal.reader,
        page=proposal.page,
        source_line_indices=proposal.source_line_indices,
        source_texts=proposal.source_texts,
        source_bboxes=proposal.source_bboxes,
        field_role=proposal.field_role.value,
        raw_proposal_text=proposal.raw_proposal_text,
        normalized_proposal_text=normalized_text,
        crop_sha256=proposal.crop_sha256,
        reader_score=proposal.reader_score,
        status=status.value,
        reason=reason,
        emitted_bbox=bbox,
        confidence_effect="NONE_READER_SCORE_RETAINED_FOR_DIAGNOSTICS_ONLY",
        geometry_effect=(
            "DERIVED_UNION_OF_IMMUTABLE_PP_OCRV6_SOURCE_BOXES"
            if bbox is not None
            else "NONE"
        ),
        automatic_authority=False,
    )


def fuse_semantic_line_proposals(
    geometry_pages: tuple[OCRPage, ...],
    proposals: tuple[SemanticLineProposal, ...],
    config: SemanticLineFusionConfig,
) -> SemanticLineFusionResult:
    if not geometry_pages:
        raise SemanticLineFusionError("semantic-line fusion requires geometry pages")
    by_page = {page.page: page for page in geometry_pages}
    if len(by_page) != len(geometry_pages):
        raise SemanticLineFusionError("geometry page identities must be unique")
    if len({item.proposal_id for item in proposals}) != len(proposals):
        raise SemanticLineFusionError("semantic proposal IDs must be unique")
    targets: set[tuple[str, int, tuple[int, ...]]] = set()
    emitted: dict[int, list[tuple[str, OCRLine]]] = {page.page: [] for page in geometry_pages}
    decisions: list[SemanticLineDecision] = []

    for proposal in proposals:
        if not proposal.proposal_id or not proposal.reader:
            raise SemanticLineFusionError("semantic proposal identity/reader is empty")
        if proposal.reader == "PP_OCRV6_WORD_BOXES":
            raise SemanticLineFusionError("geometry reader cannot masquerade as semantic reader")
        if proposal.field_role not in config.allowed_field_roles:
            raise SemanticLineFusionError("semantic proposal field role is not allowed")
        if _SHA256.fullmatch(proposal.crop_sha256) is None:
            raise SemanticLineFusionError("semantic proposal crop identity is not SHA-256")
        if proposal.reader_score is not None and (
            isinstance(proposal.reader_score, bool)
            or not math.isfinite(proposal.reader_score)
            or not 0 <= proposal.reader_score <= 1
        ):
            raise SemanticLineFusionError("semantic reader score must be finite in [0, 1]")
        page = by_page.get(proposal.page)
        if page is None:
            raise SemanticLineFusionError("semantic proposal references an absent geometry page")
        indices = proposal.source_line_indices
        if (
            not indices
            or len(indices) > config.maximum_source_lines_per_proposal
            or indices != tuple(sorted(set(indices)))
            or len(indices) != len(proposal.source_texts)
            or len(indices) != len(proposal.source_bboxes)
        ):
            raise SemanticLineFusionError("semantic proposal source binding is invalid")
        target = (proposal.reader, proposal.page, indices)
        if target in targets:
            raise SemanticLineFusionError("one reader emitted competing proposals for one target")
        targets.add(target)

        for index, expected_text, expected_bbox in zip(
            indices, proposal.source_texts, proposal.source_bboxes, strict=True
        ):
            if index < 0 or index >= len(page.lines):
                raise SemanticLineFusionError("semantic proposal source line index is invalid")
            observed = page.lines[index]
            if observed.text != expected_text or observed.bbox != expected_bbox:
                raise SemanticLineFusionError("semantic proposal source text/bbox drifted")

        normalized = normalize_text(proposal.raw_proposal_text)
        bbox = _union_bbox(proposal.source_bboxes)
        nonempty_lines = [line.strip() for line in proposal.raw_proposal_text.splitlines() if line.strip()]
        rejection: str | None = None
        if not normalized:
            rejection = "EMPTY_OR_NON_TEXTUAL_PROPOSAL"
        elif len(nonempty_lines) > config.maximum_nonempty_output_lines:
            rejection = "TOO_MANY_OUTPUT_LINES"
        elif _MARKUP.search(proposal.raw_proposal_text):
            rejection = "MARKDOWN_OR_LAYOUT_SERIALIZATION"
        else:
            source_text = normalize_text(" ".join(proposal.source_texts))
            rejection = _protected_field_reason(source_text, normalized, proposal.field_role)
            if rejection is None and not any(char.isalpha() for char in normalized):
                rejection = "EMPTY_OR_NON_TEXTUAL_PROPOSAL"
            if rejection is None and _suffix_truncated(source_text, normalized, config):
                rejection = "SUFFIX_TRUNCATED_RELATIVE_TO_SOURCE"

        if rejection is not None:
            decisions.append(
                _decision(
                    proposal,
                    status=SemanticProposalStatus.REJECTED,
                    reason=rejection,
                    normalized_text=normalized,
                    bbox=None,
                )
            )
            continue
        decisions.append(
            _decision(
                proposal,
                status=SemanticProposalStatus.EMITTED,
                reason="SAFE_SEMANTIC_PROPOSAL_NO_AUTHORITY_PROMOTION",
                normalized_text=normalized,
                bbox=bbox,
            )
        )
        emitted[proposal.page].append(
            (
                proposal.proposal_id,
                OCRLine(
                    text=normalized,
                    bbox=bbox,
                    score=proposal.reader_score if proposal.reader_score is not None else 0.0,
                ),
            )
        )

    semantic_pages = tuple(
        OCRPage(
            page=page.page,
            width=page.width,
            height=page.height,
            lines=tuple(
                line
                for _, line in sorted(
                    emitted[page.page],
                    key=lambda item: (
                        item[1].bbox[1],
                        item[1].bbox[0],
                        item[1].bbox[3],
                        item[0],
                    ),
                )
            ),
        )
        for page in geometry_pages
    )
    emitted_count = sum(
        item.status == SemanticProposalStatus.EMITTED.value for item in decisions
    )
    return SemanticLineFusionResult(
        semantic_pages=semantic_pages,
        decisions=tuple(decisions),
        emitted_count=emitted_count,
        rejected_count=len(decisions) - emitted_count,
        geometry_pages_unchanged=True,
        numeric_period_unit_sign_authority=False,
        statement_scope_mapping_truth_authority=False,
    )


__all__ = [
    "SemanticFieldRole",
    "SemanticLineDecision",
    "SemanticLineFusionConfig",
    "SemanticLineFusionError",
    "SemanticLineFusionResult",
    "SemanticLineProposal",
    "SemanticProposalStatus",
    "fuse_semantic_line_proposals",
    "load_semantic_line_fusion_config",
]
