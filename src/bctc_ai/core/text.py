from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from bctc_ai.core.contracts import ObservationKind

_ZERO_WIDTH = re.compile(r"[\u200b-\u200d\ufeff]")
_WHITESPACE = re.compile(r"\s+")
_DASH_TRANSLATION = str.maketrans({"–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-"})
_QUOTE_TRANSLATION = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."})
_DATE_PATTERN = re.compile(
    r"(?:ngày\s*)?(?P<day>\d{1,2})\s*(?:/|-|\. |\s+tháng\s+)\s*"
    r"(?P<month>\d{1,2})\s*(?:/|-|\. |\s+năm\s+)\s*(?P<year>\d{4})",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = _ZERO_WIDTH.sub("", value)
    value = value.translate(_DASH_TRANSLATION).translate(_QUOTE_TRANSLATION)
    return _WHITESPACE.sub(" ", value).strip()


def retrieval_key(value: str) -> str:
    normalized = normalize_text(value).casefold()
    decomposed = unicodedata.normalize("NFD", normalized)
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    without_marks = without_marks.replace("đ", "d")
    return re.sub(r"[^0-9a-z]+", " ", without_marks).strip()


@dataclass(frozen=True)
class ParsedNumber:
    raw_text: str
    normalized_text: str
    value: Decimal | None
    observation: ObservationKind
    sign_evidence: str | None
    reason: str | None = None


def parse_financial_number(raw_text: str | None) -> ParsedNumber:
    raw = "" if raw_text is None else raw_text
    text = normalize_text(raw).replace("\u00a0", " ")
    if not text:
        return ParsedNumber(raw, text, None, ObservationKind.BLANK, None)
    if text.casefold() in {"n/a", "na", "không áp dụng", "k/a"}:
        return ParsedNumber(raw, text, None, ObservationKind.NOT_APPLICABLE, None)
    if text in {"-", "--"}:
        return ParsedNumber(raw, text, None, ObservationKind.DASH, "dash")

    negative = False
    sign_evidence: str | None = None
    if text.startswith("(") and text.endswith(")"):
        negative = True
        sign_evidence = "parentheses"
        text = text[1:-1].strip()
    elif text.startswith("-"):
        negative = True
        sign_evidence = "leading_minus"
        text = text[1:].strip()
    elif text.endswith("-"):
        negative = True
        sign_evidence = "trailing_minus"
        text = text[:-1].strip()

    compact = text.replace(" ", "")
    if not compact or not re.fullmatch(r"\d[\d.,]*", compact):
        return ParsedNumber(
            raw,
            normalize_text(raw),
            None,
            ObservationKind.INVALID,
            sign_evidence,
            "unsupported characters",
        )

    if "." in compact and "," in compact:
        decimal_mark = "." if compact.rfind(".") > compact.rfind(",") else ","
        thousands_mark = "," if decimal_mark == "." else "."
        canonical = compact.replace(thousands_mark, "").replace(decimal_mark, ".")
    elif "." in compact or "," in compact:
        mark = "." if "." in compact else ","
        groups = compact.split(mark)
        if len(groups) > 2 or (len(groups) == 2 and len(groups[1]) == 3):
            canonical = "".join(groups)
        else:
            canonical = ".".join(groups)
    else:
        canonical = compact

    try:
        value = Decimal(canonical)
    except InvalidOperation:
        return ParsedNumber(
            raw,
            normalize_text(raw),
            None,
            ObservationKind.INVALID,
            sign_evidence,
            "invalid numeric format",
        )
    if negative:
        value = -value
    observation = ObservationKind.ZERO if value == 0 else ObservationKind.VALUE
    return ParsedNumber(raw, str(value), value, observation, sign_evidence)


def parse_vietnamese_dates(text: str) -> tuple[date, ...]:
    normalized = normalize_text(text).replace(".", ". ")
    candidates = [
        tuple(int(match.group(name)) for name in ("day", "month", "year"))
        for match in _DATE_PATTERN.finditer(normalized)
    ]
    if not candidates:
        candidates = [
            tuple(map(int, match.groups()))
            for match in re.finditer(
                r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)",
                text,
            )
        ]
    parsed = []
    for day, month, year in candidates:
        try:
            parsed.append(date(year, month, day))
        except ValueError:
            continue
    return tuple(parsed)


def parse_vietnamese_date(text: str) -> date | None:
    parsed = parse_vietnamese_dates(text)
    return parsed[0] if parsed else None


@dataclass(frozen=True)
class ParsedUnit:
    raw_text: str
    canonical: str | None
    multiplier: int | None


def parse_unit(text: str) -> ParsedUnit:
    normalized = retrieval_key(text)
    if "trieu vnd" in normalized or "vnd million" in normalized or "trieu dong" in normalized:
        return ParsedUnit(text, "VND", 1_000_000)
    if "nghin vnd" in normalized or "ngan vnd" in normalized or "nghin dong" in normalized:
        return ParsedUnit(text, "VND", 1_000)
    if re.search(r"\b(vnd|dong)\b", normalized):
        return ParsedUnit(text, "VND", 1)
    return ParsedUnit(text, None, None)
