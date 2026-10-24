"""Exact parsing of printed money cells without coercion.

Separator roles are evidence, never guessed from magnitude: a character is a
thousands separator only when some cell in the same evidence scope uses it in
an unambiguous multi-group number, and a decimal separator only when it
follows a different thousands separator. If one character holds both roles in
the scope, every cell that depends on it is ambiguous. Blank never becomes
zero. A clean printed dash is ``DASH``; whether it may be projected as a
numeric zero is a separate policy decision made by the caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

PARSER_VERSION = "PRIMARY_MONEY_CELL_PARSER_V1"

BLANK = "BLANK"
DASH = "DASH"
PRINTED_ZERO = "PRINTED_ZERO"
VALUE = "VALUE"
MALFORMED = "MALFORMED"
AMBIGUOUS_SEPARATOR = "AMBIGUOUS_SEPARATOR"

_DASH = re.compile(r"\A\s*[-–—‐_]\s*\Z")
_QUALIFIER = re.compile(r"\(\s*(?:trình bày|điều chỉnh)\s*lại\s*\)", re.IGNORECASE)
_NUMBER = re.compile(r"\A(?P<neg>\()?\s*(?P<minus>-)?\s*(?P<body>\d[\d.,]*)\s*(?P<close>\))?\Z")


@dataclass(frozen=True)
class SeparatorRoles:
    """Roles of '.' and ',' proven inside one evidence scope."""

    thousands: frozenset[str] = frozenset()
    decimal: frozenset[str] = frozenset()

    @property
    def conflicted(self) -> frozenset[str]:
        return self.thousands & self.decimal

    def merge(self, other: SeparatorRoles) -> SeparatorRoles:
        return SeparatorRoles(self.thousands | other.thousands, self.decimal | other.decimal)

    def to_dict(self) -> dict[str, list[str]]:
        return {"thousands": sorted(self.thousands), "decimal": sorted(self.decimal)}


@dataclass(frozen=True)
class ParsedCell:
    raw: str | None
    state: str
    value: Decimal | None = None
    qualifiers: tuple[str, ...] = ()
    separator_basis: str | None = None
    reason: str | None = None
    extra: dict = field(default_factory=dict, compare=False)


def _strip_qualifiers(raw: str) -> tuple[str, tuple[str, ...]]:
    qualifiers = tuple(match.group(0) for match in _QUALIFIER.finditer(raw))
    return _QUALIFIER.sub(" ", raw).strip(), qualifiers


def evidence_roles_v1(raw: str | None) -> SeparatorRoles:
    """Separator roles proven by one cell on its own (empty when ambiguous)."""

    if raw is None:
        return SeparatorRoles()
    text, _ = _strip_qualifiers(raw)
    match = _NUMBER.match(text)
    if not match:
        return SeparatorRoles()
    body = match.group("body")
    for thousand, decimal in ((".", ","), (",", ".")):
        if re.fullmatch(rf"\d{{1,3}}(?:\{thousand}\d{{3}}){{2,}}", body):
            return SeparatorRoles(frozenset({thousand}))
        if re.fullmatch(rf"\d{{1,3}}(?:\{thousand}\d{{3}})+\{decimal}\d+", body):
            return SeparatorRoles(frozenset({thousand}), frozenset({decimal}))
    return SeparatorRoles()


def parse_money_cell_v1(raw: str | None, roles: SeparatorRoles) -> ParsedCell:
    """Parse one printed cell under separator roles proven for its scope."""

    if raw is None:
        return ParsedCell(raw, BLANK)
    if raw.strip() == "":
        return ParsedCell(raw, BLANK, reason="EMPTY_OR_WHITESPACE_STRING")
    if _DASH.match(raw):
        return ParsedCell(raw, DASH)
    text, qualifiers = _strip_qualifiers(raw)
    if "\n" in text or not text:
        return ParsedCell(raw, MALFORMED, qualifiers=qualifiers, reason="NOT_ONE_PRINTED_NUMBER")
    match = _NUMBER.match(text)
    if not match or bool(match.group("neg")) != bool(match.group("close")):
        return ParsedCell(raw, MALFORMED, qualifiers=qualifiers, reason="UNPARSEABLE_OR_UNBALANCED")
    if match.group("neg") and match.group("minus"):
        return ParsedCell(raw, MALFORMED, qualifiers=qualifiers, reason="DOUBLE_NEGATIVE_MARK")
    body = match.group("body")
    negative = bool(match.group("neg") or match.group("minus"))
    digits, basis = _resolve_body(body, roles)
    if digits is None:
        state = AMBIGUOUS_SEPARATOR if basis == "AMBIGUOUS" else MALFORMED
        return ParsedCell(raw, state, qualifiers=qualifiers, reason=basis)
    value = Decimal(digits)
    if negative:
        value = -value
    state = PRINTED_ZERO if value == 0 else VALUE
    return ParsedCell(raw, state, value, qualifiers, basis)


def _resolve_body(body: str, roles: SeparatorRoles) -> tuple[str | None, str]:
    if re.fullmatch(r"\d+", body):
        return body, "NO_SEPARATOR"
    for thousand, decimal in ((".", ","), (",", ".")):
        grouped = rf"\d{{1,3}}(?:\{thousand}\d{{3}})+"
        if re.fullmatch(grouped, body) and body.count(thousand) >= 2:
            return body.replace(thousand, ""), "SELF_EVIDENT_MULTI_GROUP"
        if re.fullmatch(grouped + rf"\{decimal}\d+", body):
            integer, fraction = body.replace(thousand, "").split(decimal)
            return f"{integer}.{fraction}", "SELF_EVIDENT_GROUP_AND_DECIMAL"
    separators = set(re.findall(r"[.,]", body))
    if roles.conflicted & separators:
        return None, "AMBIGUOUS"
    if re.fullmatch(r"\d{1,3}[.,]\d{3}", body):
        separator = "." if "." in body else ","
        if separator in roles.thousands:
            return body.replace(separator, ""), "SCOPE_PROVEN_THOUSANDS"
        if separator in roles.decimal:
            return body.replace(",", "."), "SCOPE_PROVEN_DECIMAL"
        return None, "AMBIGUOUS"
    if re.fullmatch(r"\d+[.,]\d+", body):
        separator = "." if "." in body else ","
        if separator in roles.decimal:
            return body.replace(",", "."), "SCOPE_PROVEN_DECIMAL"
        if separator in roles.thousands:
            return None, "MALFORMED_GROUPING"
        return None, "AMBIGUOUS"
    return None, "MALFORMED_GROUPING"
