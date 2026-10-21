"""Versioned Vietnamese label normalization for PRIMARY statement retrieval.

The normalized key is a retrieval aid only. It never replaces ``label_exact``
and never decides an identity by itself: mapping still checks statement,
section, branch, parent context and uniqueness. Every transformation here is
symmetric (applied to schema aliases and to source labels alike) so a catalog
collision is detected at catalog load time instead of silently merging rows.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

NORMALIZATION_VERSION = "PRIMARY_LABEL_KEY_V1"

_ROMAN = r"(?:x{0,3})(?:ix|iv|v?i{0,3})"
# Leading enumerators such as "A.", "I.", "IV-", "1.", "01.", "2)", "a.", "x.1".
_ENUMERATOR = re.compile(
    r"\A\s*(?:"
    rf"(?:{_ROMAN})(?=[\s.\-)/:])"  # roman numerals
    r"|\d{1,3}(?:\.\d{1,3})*"  # arabic, optionally dotted
    r"|[a-hk-z](?=[\s.)])"  # single latin letters (not roman i/j when ambiguous)
    r"|[a-z]\.\d{1,2}"  # x.1
    r")(?:\s*[.\-)/:]+\s*|\s+)"
)
_BULLET = re.compile(r"\A\s*[-+*•–—▪·◦●○]+\s*")
# Inline acronym definitions such as 'Ngân hàng Nhà nước ("NHNN")'.
_ACRONYM_DEFINITION = re.compile(
    r"\(\s*[\"“”'‘’]\s*[a-z]{2,8}\s*[\"“”'‘’]\s*\)"
    r"|\(\s*(?:nhnn|nhnnvn|tctd|tctc|tscd|kbnn|tndn|gtcg|bdsdt|ckkd|ckdt)\s*\)"
)
# Trailing presentation annotations that never change the accounting identity.
_TRAILING_ANNOTATIONS = (
    re.compile(r"\s*\((?:\*+|\d{1,2})\)\s*\Z"),
    re.compile(r"\s*\*+\s*\Z"),
    re.compile(r"\s*\((?:[ivxlc]+\s*[+\-]\s*)+[ivxlc]+\)\s*\Z"),  # (I+II-III)
    re.compile(r"\s*=\s*[ivxlc0-9+\- ]+\Z"),
    re.compile(r"\s*\((?:mang sang|chuyen sang|chuyen tu|mang tu|mang sang tu)[^)]*\)\s*\Z"),
    re.compile(r"\s*\((?:trinh bay lai|dieu chinh lai)\)\s*\Z"),
    # Printed per-row units such as "(VND/cổ phiếu)"; kept as unit evidence by callers.
    re.compile(r"\s*\((?:[^()]*\b(?:vnd|dong|trieu|eps)\b[^()]*)\)\s*\Z"),
)
_ABBREVIATIONS = (
    (r"\bnhnnvn\b", "ngan hang nha nuoc"),
    (r"\bngan hang nha nuoc viet nam\b", "ngan hang nha nuoc"),
    (r"\bqui\b", "quy"),
    (r"\btc\b", "tai chinh"),
    (r"\btndn\b", "thu nhap doanh nghiep"),
    (r"\btctd\b", "to chuc tin dung"),
    (r"\btctc\b", "to chuc tai chinh"),
    (r"\bnhnn\b", "ngan hang nha nuoc"),
    (r"\bkbnn\b", "kho bac nha nuoc"),
    (r"\btscd\b", "tai san co dinh"),
    (r"\bbdsdt\b", "bat dong san dau tu"),
    (r"\bgtcg\b", "giay to co gia"),
    (r"\bhdkd\b", "hoat dong kinh doanh"),
    (r"\bkd\b", "kinh doanh"),
    (r"\bck\b", "chung khoan"),
    (r"\bdn\b", "doanh nghiep"),
    (r"\bxdcb\b", "xay dung co ban"),
    (r"\bvcsh\b", "von chu so huu"),
)
# Direction words printed in front of movement lines carry the printed sign
# convention, not a different identity ("(Tăng)/giảm X" == "Tăng X" == "X").
_DIRECTION_PREFIX = re.compile(
    r"\A(?:(?:tang|giam)\s*(?:/\s*)?(?:\(?\s*(?:tang|giam)\s*\)?)?\s+)"
)
_GAIN_LOSS_PREFIX = re.compile(r"\A(?:lai|lo)(?:\s*/?\s*\(?\s*(?:lai|lo)\s*\)?)?\s+thuan\b")
_INCOME_EXPENSE_PAIR = re.compile(
    r"\b(?:chi phi|thu nhap|hoan nhap)\s*/?\s*\(?\s*(?:chi phi|thu nhap|hoan nhap)\s*\)?(?=\s)"
)
_PUNCTUATION = re.compile(r"[\"'“”‘’`´.,;:!?()\[\]{}<>/\\|_~^=+*#%&@$]")
_SPACE = re.compile(r"\s+")


def fold_vietnamese(text: str) -> str:
    """Accent-fold for retrieval only (đ -> d), lower-case, collapse whitespace."""

    decomposed = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text))
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return _SPACE.sub(" ", stripped.lower()).strip()


@dataclass(frozen=True)
class LabelKey:
    """Normalized retrieval key plus the structural tokens removed from the label."""

    key: str
    folded: str
    enumerator: str | None
    removed_annotations: tuple[str, ...]


def _strip_enumerator(folded: str) -> tuple[str, str | None]:
    text = _BULLET.sub("", folded)
    match = _ENUMERATOR.match(text)
    if match and match.end() < len(text):
        return text[match.end():], match.group(0).strip()
    return text, None


def label_key_v1(label: str | None) -> LabelKey:
    """Return the deterministic normalized key of one printed label."""

    if label is None:
        return LabelKey("", "", None, ())
    # Some transcriptions contain a literal backslash-n instead of a line break.
    folded = fold_vietnamese(label.replace("\\n", " "))
    text, enumerator = _strip_enumerator(folded)
    # Two-level enumerators such as "I. 1." are rare but legal; strip once more.
    again, second = _strip_enumerator(text)
    if second is not None and enumerator is not None:
        text, enumerator = again, f"{enumerator} {second}"
    removed = []
    changed = True
    while changed:
        changed = False
        for pattern in _TRAILING_ANNOTATIONS:
            match = pattern.search(text)
            if match and match.start() > 0:
                removed.append(text[match.start():].strip())
                text = text[: match.start()]
                changed = True
    text = _ACRONYM_DEFINITION.sub(" ", text)
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    text = _PUNCTUATION.sub(" ", text.replace("-", " "))
    text = _SPACE.sub(" ", text).strip()
    text = _GAIN_LOSS_PREFIX.sub("lai lo thuan", text)
    text = _INCOME_EXPENSE_PAIR.sub(lambda m: _pair(m.group(0)), text)
    text = _DIRECTION_PREFIX.sub("", text)
    # "Lưu chuyển tiền thuần từ/(sử dụng vào) ..." and "... sử dụng vào ..." are one line.
    text = re.sub(r"\b(?:tu\s+)?su dung vao(?:\s+tu)?\b", "tu", text)
    text = _SPACE.sub(" ", text).strip()
    return LabelKey(text, folded, enumerator, tuple(removed))


def _pair(value: str) -> str:
    words = sorted({word for word in ("chi phi", "thu nhap", "hoan nhap") if word in value})
    return " ".join(words)


def enumerator_level_v1(enumerator: str | None) -> str | None:
    """Classify a stripped enumerator into a presentation level token."""

    if not enumerator:
        return None
    token = enumerator.split()[-1].strip(".-)/:")
    if re.fullmatch(r"\d{1,3}", token):
        return "ARABIC"
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3})+|[a-z]\.\d{1,2}", token):
        return "DOTTED"
    if token and re.fullmatch(_ROMAN, token):
        return "ROMAN"
    if re.fullmatch(r"[a-z]", token):
        return "LETTER"
    return None
