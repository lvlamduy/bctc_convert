from __future__ import annotations

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import ParsedNumber, normalize_text, parse_financial_number


def parse_financial_number_strict_grouping(text: str | None) -> ParsedNumber:
    """Parse a cell while rejecting separator patterns caused by row concatenation."""

    parsed = parse_financial_number(text)
    raw = "" if text is None else text
    normalized = normalize_text(raw).strip("-+() ")
    separators = {separator for separator in (".", ",") if separator in normalized}
    if parsed.observation in {ObservationKind.VALUE, ObservationKind.ZERO} and len(separators) == 1:
        separator = next(iter(separators))
        groups = normalized.split(separator)
        if len(groups) >= 3 and any(len(group) != 3 for group in groups[1:]):
            return ParsedNumber(
                raw_text=raw,
                normalized_text=normalize_text(raw),
                value=None,
                observation=ObservationKind.INVALID,
                sign_evidence=parsed.sign_evidence,
                reason="inconsistent grouped-digit widths; possible concatenated values",
            )
    return parsed
