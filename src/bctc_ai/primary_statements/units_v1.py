"""Printed monetary unit evidence for PRIMARY statements.

A unit is read only from explicit unit phrases: a table ``unit_exact``, a
column header component, a row-level parenthetical (e.g. EPS "(VND/cổ phiếu)")
or a section title/narrative fragment introduced by "Đơn vị"/"ĐVT". Magnitude
is never used, and the bare word "đồng" counts only inside such a phrase so
that "hợp đồng" in prose cannot become a VND unit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bctc_ai.primary_statements.text_v1 import fold_vietnamese

UNIT_PARSER_VERSION = "PRIMARY_UNIT_EVIDENCE_V1"

MILLION_VND = "MILLION_VND"
THOUSAND_VND = "THOUSAND_VND"
BILLION_VND = "BILLION_VND"
VND = "VND"
PERCENT = "PERCENT"
VND_PER_SHARE = "VND_PER_SHARE"

SCALE = {VND: 1, THOUSAND_VND: 1_000, MILLION_VND: 1_000_000, BILLION_VND: 1_000_000_000}

_CURRENCY = r"(?:vnd|dong(?:\s+viet\s+nam)?|dong\s+vn|vn\s*dong)"
_SCALED = (
    (BILLION_VND, re.compile(rf"\b(?:ty|billion)\s*{_CURRENCY}\b|\bbillion\s+vnd\b")),
    (MILLION_VND, re.compile(rf"\b(?:trieu|million|mil)\s*{_CURRENCY}\b|\bmillion\s+vnd\b")),
    (THOUSAND_VND, re.compile(rf"\b(?:nghin|ngan|thousand)\s*{_CURRENCY}\b")),
)
_PER_SHARE = re.compile(rf"\b{_CURRENCY}\s*/\s*(?:1\s*)?co\s*phieu\b|\bdong\s*/\s*cp\b")
_INTRODUCED = re.compile(r"(?:\bdon vi(?: tinh)?|\bdvt|\bunit)\s*:\s*(?P<phrase>[^;\n]{1,60})")
_BARE_UNIT = re.compile(rf"\A\(?\s*(?:{_CURRENCY}|trieu|%)\s*\)?\Z")


@dataclass(frozen=True)
class UnitEvidence:
    unit: str
    source_kind: str
    source_text: str


def _phrase_units(phrase: str) -> list[str]:
    folded = fold_vietnamese(phrase)
    units = []
    remaining = folded
    for unit, pattern in _SCALED:
        if pattern.search(remaining):
            units.append(unit)
            remaining = pattern.sub(" ", remaining)
    if _PER_SHARE.search(remaining):
        units.append(VND_PER_SHARE)
        remaining = _PER_SHARE.sub(" ", remaining)
    if re.search(rf"\b{_CURRENCY}\b", remaining):
        units.append(VND)
    if "%" in remaining:
        units.append(PERCENT)
    return units


def units_in_unit_field_v1(text: str | None, *, source_kind: str) -> list[UnitEvidence]:
    """Units printed in a field whose role is a unit (``unit_exact``)."""

    if not text:
        return []
    folded = fold_vietnamese(text)
    introduced = _INTRODUCED.search(folded)
    phrase = introduced.group("phrase") if introduced else folded
    return [UnitEvidence(unit, source_kind, text) for unit in _phrase_units(phrase)]


def units_in_header_component_v1(text: str | None) -> list[UnitEvidence]:
    """Units printed inside one column-header component, e.g. "31/12/2024 Triệu VND"."""

    if not text:
        return []
    folded = fold_vietnamese(text)
    introduced = _INTRODUCED.search(folded)
    if introduced:
        return [UnitEvidence(u, "COLUMN_HEADER", text) for u in _phrase_units(introduced.group("phrase"))]
    found = []
    for unit, pattern in _SCALED:
        if pattern.search(folded):
            found.append(unit)
    if _PER_SHARE.search(folded):
        found.append(VND_PER_SHARE)
    stripped = re.sub(r"[\d/.\-]+|ngay|thang|nam|tai|so|cuoi|dau|ky|quy", " ", folded)
    if not found and _BARE_UNIT.match(stripped.strip()):
        found.extend(_phrase_units(stripped))
    return [UnitEvidence(unit, "COLUMN_HEADER", text) for unit in found]


def units_in_prose_v1(text: str | None, *, source_kind: str) -> list[UnitEvidence]:
    """Units in a title/narrative only when introduced by "Đơn vị"/"ĐVT"/"Unit"."""

    if not text:
        return []
    folded = fold_vietnamese(text)
    result = []
    for match in _INTRODUCED.finditer(folded):
        result.extend(UnitEvidence(u, source_kind, text) for u in _phrase_units(match.group("phrase")))
    return result


def units_in_row_label_annotation_v1(annotations: tuple[str, ...]) -> list[UnitEvidence]:
    """Units printed in a row-label parenthetical such as "(VND/cổ phiếu)"."""

    result = []
    for annotation in annotations:
        for unit in _phrase_units(annotation):
            result.append(UnitEvidence(unit, "ROW_LABEL_ANNOTATION", annotation))
    return result
