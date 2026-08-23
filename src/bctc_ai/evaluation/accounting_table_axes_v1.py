"""Bank-blind helpers for accounting-table period, unit, and value axes.

The helpers consume only fresh semantic proposals plus bound geometry/source
text supplied by a family wrapper.  They do not know a bank, file, page, note,
family, or schema ID and grant no structural, numeric, or mapping authority on
their own.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)

__all__ = [
    "AccountingTableAxesV1Error",
    "accounting_unit_surface_v1",
    "center_x2_v1",
    "infer_document_accounting_unit_context_v1",
    "infer_document_reporting_period_context_v1",
    "is_accounting_value_surface_v1",
    "extract_period_axis_v1",
    "extract_period_observations_v1",
    "extract_row_aligned_typed_value_vector_v1",
    "extract_reporting_year_axis_v1",
    "extract_typed_value_vector_v1",
    "is_number_like_v1",
    "line_has_accounting_value_surface_v1",
    "money_integer_v1",
    "money_values_v1",
    "percentage_values_v1",
    "resolve_relative_period_axis_v1",
    "unit_kind_v1",
]


_NUMBER = re.compile(r"^[()]*[+-]?[0-9][0-9., ]*%?[()]*$")
_NUMBER_TOKEN = re.compile(r"\(?[+-]?[0-9]+(?:[.,][0-9]+)*%?\)?")
_VISIBLE_DASHES = {"-", "–", "—", "−"}
_FULL_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4})(?!\d)")
_DAY_MONTH = re.compile(r"\b(?:ngay\s+)?(\d{1,2})\s+thang\s+(\d{1,2})\b")
_DAY_ONLY = re.compile(r"^(?:ngay\s+)?(\d{1,2})\s+thang$")
_MONTH_YEAR = re.compile(r"^(\d{1,2})\s+nam\s+(\d{4})$")
_YEAR = re.compile(r"\bnam\s+(\d{4})\b")
_REPORTING_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_REPORTING_PERIOD_ENDS = {(3, 31), (6, 30), (9, 30), (12, 31)}
_MAX_DOCUMENT_DATE_EVIDENCE = 8
_MAX_DOCUMENT_UNIT_EVIDENCE = 12
_MIN_NUMERIC_PERIOD_READER_SCORE = 0.95
_RELATIVE_PERIOD_RESTATEMENT_SUFFIXES = {
    "",
    "da duoc trinh bay lai",
    "da trinh bay lai",
    "duoc trinh bay lai",
    "trinh bay lai",
}


class AccountingTableAxesV1Error(ValueError):
    """A semantic line, geometry, or typed numeric surface drifted."""


def _error(message: str) -> AccountingTableAxesV1Error:
    return AccountingTableAxesV1Error(message)


def _bbox(line: Mapping[str, Any], label: str) -> list[int]:
    value = line.get("bbox")
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} bbox drifted")
    return list(value)


def _text(line: Mapping[str, Any], label: str) -> str:
    value = line.get("vietocr_text")
    if type(value) is not str:
        raise _error(f"{label} VietOCR text drifted")
    return value


def _contains_period_surface(value: str) -> bool:
    """Return whether one OCR surface contains a syntactically valid date part.

    This deliberately does not decide which reporting period applies.  The
    local body-column projection and repeated document-period consensus remain
    the authority for that later decision.
    """

    for matched in _FULL_DATE.finditer(value):
        day, month, year = map(int, matched.groups())
        if _date_surface(day, month, year) is not None:
            return True
    normalized = normalize_vietnamese_anchor_v1(value)
    if matched := _DAY_MONTH.search(normalized):
        day, month = map(int, matched.groups())
        if 1 <= day <= 31 and 1 <= month <= 12:
            return True
    return _YEAR.search(normalized) is not None or _REPORTING_YEAR.search(value) is not None


def _relative_period_role(normalized: str) -> str | None:
    """Recognize a relative period label with an optional restatement qualifier."""

    for prefix, role in (
        ("so cuoi ky", "CURRENT_PERIOD_END"),
        ("so cuoi nam", "CURRENT_PERIOD_END"),
        ("so dau ky", "COMPARATIVE_PERIOD_START"),
        ("so dau nam", "COMPARATIVE_PERIOD_START"),
    ):
        if normalized == prefix:
            return role
        marker = f"{prefix} "
        if normalized.startswith(marker):
            suffix = normalized[len(marker) :]
            if suffix in _RELATIVE_PERIOD_RESTATEMENT_SUFFIXES:
                return role
    return None


def _join_split_day_month_year_fragments(
    day_only: Sequence[tuple[Mapping[str, Any], int]],
    month_year: Sequence[tuple[Mapping[str, Any], int, int]],
) -> list[tuple[Mapping[str, Any], Mapping[str, Any], int, int, int]]:
    """Join OCR-split ``Ngày DD tháng`` + ``MM năm YYYY`` column headers.

    Pairing is local in source order and horizontal geometry.  Ambiguous
    candidates fail closed instead of choosing a date by proximity alone.
    """

    joined: list[tuple[Mapping[str, Any], Mapping[str, Any], int, int, int]] = []
    remaining = list(month_year)
    for day_line, day in day_only:
        day_index = _source_line_index(day_line, "split period day fragment")
        day_box = _bbox(day_line, "split period day fragment")
        candidates: list[tuple[Mapping[str, Any], int, int]] = []
        for candidate in remaining:
            year_line = candidate[0]
            year_index = _source_line_index(year_line, "split period month/year fragment")
            year_box = _bbox(year_line, "split period month/year fragment")
            if 0 < year_index - day_index <= 3 and max(day_box[0], year_box[0]) < min(
                day_box[2], year_box[2]
            ):
                candidates.append(candidate)
        if len(candidates) != 1:
            continue
        year_line, month, year = candidates[0]
        remaining.remove(candidates[0])
        joined.append((day_line, year_line, day, month, year))
    return joined


def _period_text(line: Mapping[str, Any], label: str) -> str:
    """Select text only for period parsing, preferring the numeric challenger.

    VietOCR remains the semantic-text source.  A separately authenticated
    numeric reader may replace its surface here only when it has a high finite
    score and independently emits a valid date/year grammar.  This is useful
    for digit confusions such as ``B1``/``31`` or ``2626``/``2026``; it cannot
    inject a period from a filename, bank, page, family, or expected value.
    """

    semantic = _text(line, label)
    has_numeric_text = "numeric_text" in line
    has_numeric_score = "numeric_score" in line
    if not has_numeric_text and not has_numeric_score:
        return semantic
    numeric = line.get("numeric_text")
    score = line.get("numeric_score")
    if (
        type(numeric) is not str
        or type(score) is not float
        or not math.isfinite(score)
        or not 0 <= score <= 1
    ):
        raise _error(f"{label} numeric period challenger drifted")
    if (
        score >= _MIN_NUMERIC_PERIOD_READER_SCORE
        and normalize_vietnamese_anchor_v1(numeric) != normalize_vietnamese_anchor_v1(semantic)
        and _contains_period_surface(numeric)
    ):
        return numeric
    return semantic


def _source_line_index(line: Mapping[str, Any], label: str) -> int:
    value = line.get("source_line_index")
    if type(value) is not int or value < 0:
        raise _error(f"{label} source line index drifted")
    return value


def _date_surface(day: int, month: int, year: int) -> str | None:
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{day:02d}/{month:02d}/{year:04d}"


def _standalone_or_prefixed_year(value: str) -> int | None:
    """Parse a visible year fragment without treating narrative numbers as dates."""

    normalized = normalize_vietnamese_anchor_v1(value)
    if matched := _YEAR.search(normalized):
        return int(matched.group(1))
    if re.fullmatch(r"20\d{2}", normalized):
        return int(normalized)
    return None


def center_x2_v1(line: Mapping[str, Any]) -> int:
    """Return twice the horizontal center without floating-point rounding."""

    box = _bbox(line, "semantic line")
    return box[0] + box[2]


def is_number_like_v1(value: str) -> bool:
    if type(value) is not str:
        raise _error("numeric surface must be one exact string")
    compact = value.strip().replace("\u00a0", " ").replace("\u202f", " ")
    return bool(compact and _NUMBER.fullmatch(compact) and any(char.isdigit() for char in compact))


def is_accounting_value_surface_v1(value: str) -> bool:
    """Return whether a visible crop can occupy an accounting value cell.

    A printed dash is a real cell surface even though it is not a recognized
    number.  An empty OCR surface is not evidence of a zero-valued cell.
    Numeric parsing and the family dash-to-zero policy remain separate gates.
    """

    if type(value) is not str:
        raise _error("accounting value surface must be one exact string")
    compact = value.strip()
    return compact in _VISIBLE_DASHES or is_number_like_v1(value)


def line_has_accounting_value_surface_v1(line: Mapping[str, Any]) -> bool:
    """Return whether either bound reader exposes an accounting cell surface.

    VietOCR remains the semantic-label reader, but PP-OCRv6 can legitimately
    recognize a numeric cell whose Transformer proposal is empty or malformed.
    Treating the two observations as one *candidate* surface prevents provider
    serialization from hiding a cell; numeric authority is still granted only
    later by :func:`extract_typed_value_vector_v1` from ``source_text``.
    """

    semantic = _text(line, "accounting value line")
    source = line.get("source_text")
    if source is not None and type(source) is not str:
        raise _error("accounting value source surface drifted")
    return is_accounting_value_surface_v1(semantic) or (
        type(source) is str and is_accounting_value_surface_v1(source)
    )


def _split_bound_value_line_across_lanes(
    line: Mapping[str, Any],
    lane_centers_x2: Sequence[int],
    peer_lines: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Split one detector-merged numeric line only with exact geometric proof."""

    source = line.get("source_text")
    if type(source) is not str:
        return []
    tokens = _NUMBER_TOKEN.findall(source)
    if len(tokens) < 2 or _NUMBER_TOKEN.sub("", source).strip():
        return []
    box = _bbox(line, "merged accounting value line")
    covered = [
        lane_index
        for lane_index, center_x2 in enumerate(lane_centers_x2)
        if 2 * box[0] <= center_x2 <= 2 * box[2]
    ]
    semantic = _text(line, "merged accounting value line")
    semantic_tokens = _NUMBER_TOKEN.findall(semantic)
    if (
        len(tokens) == len(covered) + 1
        and covered
        and covered[0] > 0
        and re.fullmatch(r"\d{1,2}", tokens[0]) is not None
    ):
        # A detector seam can repeat the suffix of the immediately preceding
        # cell at the start of a multi-lane merged box.  Remove that fragment
        # only when a unique same-baseline, overlapping peer occupies the
        # preceding declared lane and visibly ends in the exact fragment.
        preceding_lane = covered[0] - 1
        minimum_gap = min(
            right - left for left, right in zip(lane_centers_x2, lane_centers_x2[1:], strict=False)
        )
        maximum_distance = max(8, minimum_gap * 2 // 5)
        seam_peers = []
        for peer in peer_lines:
            if _source_line_index(peer, "merged accounting peer") == _source_line_index(
                line, "merged accounting value line"
            ):
                continue
            peer_source = peer.get("source_text")
            if type(peer_source) is not str or not is_number_like_v1(peer_source):
                continue
            peer_tokens = _NUMBER_TOKEN.findall(peer_source)
            if len(peer_tokens) != 1:
                continue
            peer_box = _bbox(peer, "merged accounting peer")
            vertical_distance_x2 = abs((peer_box[1] + peer_box[3]) - (box[1] + box[3]))
            if vertical_distance_x2 > max(peer_box[3] - peer_box[1], box[3] - box[1]):
                continue
            if not (peer_box[0] < box[0] < peer_box[2] <= box[2]):
                continue
            if abs(center_x2_v1(peer) - lane_centers_x2[preceding_lane]) > maximum_distance:
                continue
            peer_digits = re.sub(r"\D", "", peer_tokens[0])
            if not peer_digits.endswith(tokens[0]):
                continue
            seam_peers.append(peer)
        if len(seam_peers) == 1:
            tokens = tokens[1:]
            if (
                len(semantic_tokens) == len(tokens) + 1
                and semantic_tokens[0] == _NUMBER_TOKEN.findall(source)[0]
            ):
                semantic_tokens = semantic_tokens[1:]
    if (
        len(covered) == 1
        and len(tokens) == 2
        and re.fullmatch(r"\(?\d{1,2}\)?", tokens[0]) is not None
        and re.fullmatch(r"\(?[+-]?\d{1,3}(?:[.,]\d{3})+\)?", tokens[1]) is not None
    ):
        # A detached numeric footnote marker can share one detector box with
        # the actual value.  It is not a second lane when the box covers only
        # one declared center.  Admit the grouped integer token while keeping
        # the original source-line locator available to the caller.
        semantic = _text(line, "annotated accounting value line")
        semantic_tokens = _NUMBER_TOKEN.findall(semantic)
        semantic_main = (
            semantic_tokens[1]
            if len(semantic_tokens) == 2
            and not _NUMBER_TOKEN.sub("", semantic).strip()
            and re.fullmatch(r"\(?\d{1,2}\)?", semantic_tokens[0]) is not None
            else ""
        )
        center_x = lane_centers_x2[covered[0]] // 2
        synthetic = dict(line)
        synthetic["bbox"] = [center_x - 1, box[1], center_x + 1, box[3]]
        synthetic["source_text"] = tokens[1]
        synthetic["vietocr_text"] = semantic_main
        return [synthetic]
    if len(tokens) != len(covered):
        return []
    semantic_exact = (
        len(semantic_tokens) == len(tokens) and not _NUMBER_TOKEN.sub("", semantic).strip()
    )
    result: list[dict[str, Any]] = []
    for token_offset, (lane_index, source_token) in enumerate(zip(covered, tokens, strict=True)):
        center_x = lane_centers_x2[lane_index] // 2
        synthetic = dict(line)
        synthetic["bbox"] = [center_x - 1, box[1], center_x + 1, box[3]]
        synthetic["source_text"] = source_token
        synthetic["vietocr_text"] = semantic_tokens[token_offset] if semantic_exact else ""
        result.append(synthetic)
    return result


def extract_row_aligned_typed_value_vector_v1(
    lines: Sequence[Mapping[str, Any]],
    label_bbox: Sequence[int],
    lane_types: Sequence[str],
    lane_centers_x2: Sequence[int],
    *,
    primary_numeric_authority: bool,
) -> list[dict[str, Any]] | None:
    """Bind a visual row to typed lanes, independent of provider line order.

    The label rectangle establishes the row band.  Candidate cells must lie to
    its right and overlap it vertically (or have a center within one cell
    height).  A detector-merged line may be split only when its exact ordered
    numeric token count equals the number of lane centers covered by its bbox.
    Blank cells are never synthesized and duplicate lane assignments fail
    closed.
    """

    label = _bbox({"bbox": list(label_bbox)}, "accounting row label")
    if (
        isinstance(lane_centers_x2, (str, bytes, bytearray))
        or list(lane_centers_x2) != sorted(set(lane_centers_x2))
        or len(lane_centers_x2) != len(lane_types)
    ):
        raise _error("accounting row lane centers drifted")
    label_center_y2 = label[1] + label[3]
    label_height = label[3] - label[1]
    candidates: list[Mapping[str, Any]] = []
    for line in lines:
        if not line_has_accounting_value_surface_v1(line):
            continue
        box = _bbox(line, "accounting row value candidate")
        if box[0] <= label[2]:
            continue
        overlap = min(label[3], box[3]) - max(label[1], box[1])
        center_distance = abs((box[1] + box[3]) - label_center_y2)
        if overlap <= 0 and center_distance > max(label_height, box[3] - box[1]):
            continue
        split = _split_bound_value_line_across_lanes(line, lane_centers_x2, lines)
        candidates.extend(split or [line])

    if len(lane_centers_x2) < 2:
        return None
    minimum_gap = min(
        right - left for left, right in zip(lane_centers_x2, lane_centers_x2[1:], strict=False)
    )
    maximum_distance = max(8, minimum_gap * 2 // 5)
    candidates_by_lane: dict[int, list[tuple[int, int, int, Mapping[str, Any]]]] = {}
    for line in candidates:
        center = center_x2_v1(line)
        distances = [abs(center - expected) for expected in lane_centers_x2]
        lane_index = min(range(len(distances)), key=distances.__getitem__)
        if distances[lane_index] > maximum_distance:
            continue
        box = _bbox(line, "accounting row value candidate")
        vertical_distance = abs((box[1] + box[3]) - label_center_y2)
        candidates_by_lane.setdefault(lane_index, []).append(
            (
                vertical_distance,
                distances[lane_index],
                _source_line_index(line, "accounting row value candidate"),
                line,
            )
        )
    by_lane: dict[int, Mapping[str, Any]] = {}
    for lane_index, lane_candidates in candidates_by_lane.items():
        lane_candidates.sort(key=lambda item: item[:3])
        if len(lane_candidates) > 1 and lane_candidates[1][0] - lane_candidates[0][0] <= 2:
            # Two observations on effectively the same baseline cannot be
            # assigned by horizontal proximity alone.  Keep the row
            # unresolved rather than selecting by provider order.
            return None
        by_lane[lane_index] = lane_candidates[0][3]
    if set(by_lane) != set(range(len(lane_types))):
        return None
    ordered = [by_lane[index] for index in range(len(lane_types))]
    vector = extract_typed_value_vector_v1(
        ordered,
        lane_types,
        primary_numeric_authority=primary_numeric_authority,
    )
    if vector is None:
        return None
    for lane_index, item in enumerate(vector):
        item["lane_index"] = lane_index
    return vector


def money_integer_v1(value: str) -> int | None:
    if type(value) is not str:
        raise _error("money surface must be one exact string")
    compact = value.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    if (
        compact.endswith("%")
        or not compact
        or not all(char.isdigit() or char in ".," for char in compact)
    ):
        return None
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        return None
    result = int(digits)
    return -result if negative else result


def _percentage(value: str) -> Decimal | None:
    compact = value.strip().replace(" ", "").rstrip("%").replace(",", ".")
    try:
        result = Decimal(compact)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def accounting_unit_surface_v1(value: str) -> dict[str, Any] | None:
    """Parse one explicit accounting unit without using a family or schema.

    Magnitudes are powers of ten in the stated currency.  The record is only a
    visible-text proposal: its scope still has to be established locally or by
    a document-wide inheritance gate.
    """

    if type(value) is not str:
        raise _error("accounting unit surface must be one exact string")
    normalized = normalize_vietnamese_anchor_v1(value)
    if "%" in normalized:
        words = set(normalized.replace("%", " ").split())
        if any(character.isdigit() for character in normalized) or not (
            normalized.startswith(("don vi ", "don vi tinh ", "dvt "))
            or words <= {"le", "phan", "tram", "ty"}
        ):
            return None
        return {
            "currency": None,
            "magnitude_power10": None,
            "normalized_surface": normalized,
            "unit_kind": "PERCENT",
        }
    words = set(normalized.split())
    currency = "VND" if words & {"dong", "vnd"} else None
    if currency is None:
        return None
    if "ty" in words:
        magnitude = 9
    elif "trieu" in words:
        magnitude = 6
    elif "nghin" in words:
        magnitude = 3
    elif normalized.startswith(("don vi ", "don vi tinh ", "dvt ")):
        magnitude = 0
    else:
        return None
    return {
        "currency": currency,
        "magnitude_power10": magnitude,
        "normalized_surface": normalized,
        "unit_kind": "MONEY",
    }


def unit_kind_v1(value: str) -> str | None:
    parsed = accounting_unit_surface_v1(value)
    if parsed is not None:
        return parsed["unit_kind"]
    return None


def _is_explicit_document_unit_surface(normalized: str) -> bool:
    if normalized.startswith(("don vi ", "don vi tinh ", "dvt ")):
        return True
    return normalized in {
        "dong",
        "nghin dong",
        "nghin vnd",
        "trieu dong",
        "trieu vnd",
        "ty dong",
        "ty vnd",
    }


def infer_document_accounting_unit_context_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Propose one repeated/unique explicit document money unit.

    The routine never reads a bank, path, filename, year, note or family.  It
    rejects conflicting explicit units and retains source locations so a later
    family gate can prove that inheritance does not cross a structural reset.
    """

    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)):
        raise _error("document unit pages must be one sequence of page records")
    observations: dict[tuple[str, str | None, int | None], list[dict[str, Any]]] = {}
    for expected_page_sequence, raw_page in enumerate(pages, 1):
        if not isinstance(raw_page, Mapping):
            raise _error("document unit page must be one mapping")
        page_sequence = raw_page.get("page_sequence")
        lines = raw_page.get("lines")
        if (
            type(page_sequence) is not int
            or page_sequence != expected_page_sequence
            or type(lines) is not list
        ):
            raise _error("document unit page identity or line axis drifted")
        seen_line_indices: set[int] = set()
        for line in lines:
            if not isinstance(line, Mapping):
                raise _error("document unit line must be one mapping")
            text = _text(line, "document unit line")
            source_line_index = _source_line_index(line, "document unit line")
            if source_line_index in seen_line_indices:
                raise _error("document unit source line axis repeats")
            seen_line_indices.add(source_line_index)
            _bbox(line, "document unit line")
            parsed = accounting_unit_surface_v1(text)
            normalized = normalize_vietnamese_anchor_v1(text)
            if parsed is None or not _is_explicit_document_unit_surface(normalized):
                continue
            key = (
                parsed["unit_kind"],
                parsed["currency"],
                parsed["magnitude_power10"],
            )
            observations.setdefault(key, []).append(
                {
                    "page_sequence": page_sequence,
                    "source_line_index": source_line_index,
                    "surface": text,
                }
            )
    if not observations:
        return {
            "currency": None,
            "evidence": [],
            "evidence_truncated": False,
            "magnitude_power10": None,
            "resolution": "UNRESOLVED_NO_EXPLICIT_DOCUMENT_UNIT",
            "supporting_page_count": 0,
            "unit_kind": None,
        }
    if len(observations) != 1:
        evidence = [
            {
                "currency": key[1],
                "magnitude_power10": key[2],
                "occurrence_count": len(items),
                "supporting_page_count": len({item["page_sequence"] for item in items}),
                "unit_kind": key[0],
            }
            for key, items in sorted(observations.items(), key=lambda item: str(item[0]))
        ]
        return {
            "currency": None,
            "evidence": evidence,
            "evidence_truncated": False,
            "magnitude_power10": None,
            "resolution": "UNRESOLVED_CONFLICTING_EXPLICIT_DOCUMENT_UNITS",
            "supporting_page_count": 0,
            "unit_kind": None,
        }
    (unit_kind, currency, magnitude), evidence = next(iter(observations.items()))
    ordered = sorted(evidence, key=lambda item: (item["page_sequence"], item["source_line_index"]))
    supporting_pages = len({item["page_sequence"] for item in ordered})
    return {
        "currency": currency,
        "evidence": ordered[:_MAX_DOCUMENT_UNIT_EVIDENCE],
        "evidence_truncated": len(ordered) > _MAX_DOCUMENT_UNIT_EVIDENCE,
        "magnitude_power10": magnitude,
        "resolution": (
            "REPEATED_EXPLICIT_DOCUMENT_UNIT_CONSENSUS"
            if supporting_pages >= 2
            else "UNIQUE_EXPLICIT_DOCUMENT_UNIT_PROPOSAL"
        ),
        "supporting_page_count": supporting_pages,
        "unit_kind": unit_kind,
    }


def extract_period_axis_v1(
    lines: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Resolve exact, split, or relative two-period headers."""

    full: list[dict[str, Any]] = []
    partial: list[tuple[Mapping[str, Any], int, int]] = []
    years: list[tuple[Mapping[str, Any], int]] = []
    day_only: list[tuple[Mapping[str, Any], int]] = []
    month_year: list[tuple[Mapping[str, Any], int, int]] = []
    relative: list[dict[str, Any]] = []
    for line in lines:
        text = _period_text(line, "period header")
        normalized = normalize_vietnamese_anchor_v1(text)
        if matched := _FULL_DATE.search(text):
            day, month, year = map(int, matched.groups())
            surface = _date_surface(day, month, year)
            if surface is None:
                continue
            full.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(line, "exact period header")
                    ],
                    "period": surface,
                    "x_center_x2": center_x2_v1(line),
                }
            )
            continue
        if matched := _DAY_MONTH.search(normalized):
            day = int(matched.group(1))
            month = int(matched.group(2))
            if year_match := _YEAR.search(normalized):
                surface = _date_surface(day, month, int(year_match.group(1)))
                if surface is not None:
                    full.append(
                        {
                            "evidence_source_line_indices": [
                                _source_line_index(line, "Vietnamese full period header")
                            ],
                            "period": surface,
                            "x_center_x2": center_x2_v1(line),
                        }
                    )
                continue
            partial.append((line, day, month))
            continue
        if matched := _DAY_ONLY.fullmatch(normalized):
            day = int(matched.group(1))
            if 1 <= day <= 31:
                day_only.append((line, day))
            continue
        if matched := _MONTH_YEAR.fullmatch(normalized):
            month = int(matched.group(1))
            year = int(matched.group(2))
            if 1 <= month <= 12:
                month_year.append((line, month, year))
            continue
        if (year := _standalone_or_prefixed_year(text)) is not None:
            years.append((line, year))
            continue
        relative_role = _relative_period_role(normalized)
        if relative_role is not None:
            relative.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(line, "relative period header")
                    ],
                    "period": relative_role,
                    "x_center_x2": center_x2_v1(line),
                }
            )
    exact_record_count = len(full)
    for day_line, year_line, day, month, year in _join_split_day_month_year_fragments(
        day_only, month_year
    ):
        surface = _date_surface(day, month, year)
        if surface is not None:
            full.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(day_line, "split period day fragment"),
                        _source_line_index(year_line, "split period month/year fragment"),
                    ],
                    "period": surface,
                    "x_center_x2": center_x2_v1(day_line),
                }
            )
    remaining = list(years)
    for line, day, month in sorted(partial, key=lambda item: center_x2_v1(item[0])):
        line_index = _source_line_index(line, "split period header")
        line_box = _bbox(line, "split period header")
        candidates = []
        for item in remaining:
            year_line = item[0]
            year_box = _bbox(year_line, "split period year")
            maximum_height = max(line_box[3] - line_box[1], year_box[3] - year_box[1])
            if (
                _source_line_index(year_line, "split period year") > line_index
                and max(line_box[0], year_box[0]) < min(line_box[2], year_box[2])
                and -maximum_height <= year_box[1] - line_box[3] <= 2 * maximum_height
            ):
                candidates.append(item)
        if not candidates:
            continue
        ranked = sorted(
            candidates,
            key=lambda item: (
                abs(center_x2_v1(item[0]) - center_x2_v1(line)),
                _source_line_index(item[0], "split period year"),
            ),
        )
        if len(ranked) > 1 and abs(center_x2_v1(ranked[0][0]) - center_x2_v1(line)) == abs(
            center_x2_v1(ranked[1][0]) - center_x2_v1(line)
        ):
            continue
        year_line, year = ranked[0]
        remaining.remove((year_line, year))
        surface = _date_surface(day, month, year)
        if surface is None:
            continue
        full.append(
            {
                "evidence_source_line_indices": [
                    line_index,
                    _source_line_index(year_line, "split period year"),
                ],
                "period": surface,
                "x_center_x2": center_x2_v1(line),
            }
        )
    if len(full) == 2:
        mode = "LOCAL_EXACT_DATES" if exact_record_count == 2 else "LOCAL_SPLIT_DATES"
        return sorted(full, key=lambda item: item["x_center_x2"]), mode
    if len(relative) == 2:
        return sorted(relative, key=lambda item: item["x_center_x2"]), "LOCAL_RELATIVE_PERIOD_ROLES"
    return [], "UNRESOLVED"


def extract_period_observations_v1(
    lines: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return every visible exact or relative period in source-line order.

    Unlike :func:`extract_period_axis_v1`, this helper does not require two
    horizontal columns.  It is intended for tables that repeat the same row
    roles in vertically stacked period blocks.  It only parses the supplied
    local header band and grants no current/comparative selection authority.
    """

    if isinstance(lines, (str, bytes, bytearray)) or not isinstance(lines, Sequence):
        raise _error("period observation lines must be one sequence")
    observations: list[dict[str, Any]] = []
    partial: list[tuple[Mapping[str, Any], int, int]] = []
    years: list[tuple[Mapping[str, Any], int]] = []
    day_only: list[tuple[Mapping[str, Any], int]] = []
    month_year: list[tuple[Mapping[str, Any], int, int]] = []
    for line in lines:
        if not isinstance(line, Mapping):
            raise _error("period observation line must be one mapping")
        text = _period_text(line, "period observation")
        normalized = normalize_vietnamese_anchor_v1(text)
        source_index = _source_line_index(line, "period observation")
        if matched := _FULL_DATE.search(text):
            day, month, year = map(int, matched.groups())
            surface = _date_surface(day, month, year)
            if surface is not None:
                observations.append(
                    {
                        "evidence_source_line_indices": [source_index],
                        "period": surface,
                        "source_line_index": source_index,
                        "x_center_x2": center_x2_v1(line),
                    }
                )
            continue
        if matched := _DAY_MONTH.search(normalized):
            day, month = map(int, matched.groups())
            if year_match := _YEAR.search(normalized):
                surface = _date_surface(day, month, int(year_match.group(1)))
                if surface is not None:
                    observations.append(
                        {
                            "evidence_source_line_indices": [source_index],
                            "period": surface,
                            "source_line_index": source_index,
                            "x_center_x2": center_x2_v1(line),
                        }
                    )
                continue
            partial.append((line, day, month))
            continue
        if matched := _DAY_ONLY.fullmatch(normalized):
            day = int(matched.group(1))
            if 1 <= day <= 31:
                day_only.append((line, day))
            continue
        if matched := _MONTH_YEAR.fullmatch(normalized):
            month = int(matched.group(1))
            year = int(matched.group(2))
            if 1 <= month <= 12:
                month_year.append((line, month, year))
            continue
        if (year := _standalone_or_prefixed_year(text)) is not None:
            years.append((line, year))
            continue
        relative_role = _relative_period_role(normalized)
        if relative_role is not None:
            observations.append(
                {
                    "evidence_source_line_indices": [source_index],
                    "period": relative_role,
                    "source_line_index": source_index,
                    "x_center_x2": center_x2_v1(line),
                }
            )
    for day_line, year_line, day, month, year in _join_split_day_month_year_fragments(
        day_only, month_year
    ):
        surface = _date_surface(day, month, year)
        if surface is None:
            continue
        evidence = sorted(
            {
                _source_line_index(day_line, "split period day fragment"),
                _source_line_index(year_line, "split period month/year fragment"),
            }
        )
        observations.append(
            {
                "evidence_source_line_indices": evidence,
                "period": surface,
                "source_line_index": min(evidence),
                "x_center_x2": center_x2_v1(day_line),
            }
        )
    remaining = list(years)
    for line, day, month in partial:
        candidates = [
            item
            for item in remaining
            if abs(
                _source_line_index(item[0], "split period year")
                - _source_line_index(line, "split period day/month")
            )
            <= 3
        ]
        if not candidates:
            continue
        year_line, year = min(
            candidates, key=lambda item: abs(center_x2_v1(item[0]) - center_x2_v1(line))
        )
        remaining.remove((year_line, year))
        surface = _date_surface(day, month, year)
        if surface is None:
            continue
        evidence = sorted(
            {
                _source_line_index(line, "split period day/month"),
                _source_line_index(year_line, "split period year"),
            }
        )
        observations.append(
            {
                "evidence_source_line_indices": evidence,
                "period": surface,
                "source_line_index": min(evidence),
                "x_center_x2": center_x2_v1(line),
            }
        )
    observations.sort(key=lambda item: (item["source_line_index"], item["x_center_x2"]))
    return observations


def extract_reporting_year_axis_v1(
    lines: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Resolve a current/comparative axis from exactly two visible years.

    The later year is the current reporting axis and the earlier year is the
    comparative axis.  More or fewer than two visible years fail closed so a
    narrative year or a second table cannot silently choose the period.
    """

    by_year: dict[int, list[Mapping[str, Any]]] = {}
    for line in lines:
        text = _period_text(line, "reporting-year header")
        for matched in _REPORTING_YEAR.finditer(text):
            by_year.setdefault(int(matched.group(1)), []).append(line)
    if len(by_year) != 2:
        return [], "UNRESOLVED"
    comparative_year, current_year = sorted(by_year)
    records = []
    for role, year in (
        ("COMPARATIVE_PERIOD", comparative_year),
        ("CURRENT_PERIOD", current_year),
    ):
        line = by_year[year][0]
        records.append(
            {
                "evidence_source_line_indices": [_source_line_index(line, "reporting-year header")],
                "role": role,
                "x_center_x2": center_x2_v1(line),
                "year": year,
            }
        )
    return records, "VISIBLE_TWO_YEAR_REPORTING_AXIS"


def _document_date_observations(
    pages: Sequence[Mapping[str, Any]],
) -> dict[date, list[dict[str, Any]]]:
    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)):
        raise _error("document pages must be one sequence of page records")
    observations: dict[date, list[dict[str, Any]]] = {}
    for expected_page_sequence, raw_page in enumerate(pages, 1):
        if not isinstance(raw_page, Mapping):
            raise _error("document period page must be one mapping")
        page_sequence = raw_page.get("page_sequence")
        lines = raw_page.get("lines")
        if (
            type(page_sequence) is not int
            or page_sequence != expected_page_sequence
            or type(lines) is not list
        ):
            raise _error("document period page identity or line axis drifted")
        partial: list[tuple[Mapping[str, Any], int, int]] = []
        year_only: list[tuple[Mapping[str, Any], int]] = []
        day_only: list[tuple[Mapping[str, Any], int]] = []
        month_year: list[tuple[Mapping[str, Any], int, int]] = []
        page_observations: set[tuple[date, tuple[int, ...]]] = set()
        seen_line_indices: set[int] = set()
        for line in lines:
            if not isinstance(line, Mapping):
                raise _error("document period line must be one mapping")
            text = _period_text(line, "document period line")
            source_line_index = _source_line_index(line, "document period line")
            if source_line_index in seen_line_indices:
                raise _error("document period source line axis repeats")
            seen_line_indices.add(source_line_index)
            _bbox(line, "document period line")
            normalized = normalize_vietnamese_anchor_v1(text)
            found_full = False
            for matched in _FULL_DATE.finditer(text):
                day, month, year = map(int, matched.groups())
                surface = _date_surface(day, month, year)
                if surface is None:
                    continue
                parsed = date(year, month, day)
                page_observations.add((parsed, (source_line_index,)))
                found_full = True
            if found_full:
                continue
            day_month_match = _DAY_MONTH.search(normalized)
            year_match = _YEAR.search(normalized)
            if day_month_match is not None and year_match is not None:
                day = int(day_month_match.group(1))
                month = int(day_month_match.group(2))
                year = int(year_match.group(1))
                surface = _date_surface(day, month, year)
                if surface is not None:
                    page_observations.add((date(year, month, day), (source_line_index,)))
                continue
            if day_month_match is not None:
                partial.append((line, int(day_month_match.group(1)), int(day_month_match.group(2))))
                continue
            if matched := _DAY_ONLY.fullmatch(normalized):
                day = int(matched.group(1))
                if 1 <= day <= 31:
                    day_only.append((line, day))
                continue
            if matched := _MONTH_YEAR.fullmatch(normalized):
                month = int(matched.group(1))
                year = int(matched.group(2))
                if 1 <= month <= 12:
                    month_year.append((line, month, year))
                continue
            if year_match is not None:
                year_only.append((line, int(year_match.group(1))))

        for day_line, year_line, day, month, year in _join_split_day_month_year_fragments(
            day_only, month_year
        ):
            surface = _date_surface(day, month, year)
            if surface is None:
                continue
            indices = tuple(
                sorted(
                    (
                        _source_line_index(day_line, "split document period day fragment"),
                        _source_line_index(year_line, "split document period month/year fragment"),
                    )
                )
            )
            page_observations.add((date(year, month, day), indices))

        remaining_years = list(year_only)
        for line, day, month in partial:
            line_index = _source_line_index(line, "split document period")
            candidates = [
                item
                for item in remaining_years
                if abs(_source_line_index(item[0], "split document period year") - line_index) <= 3
            ]
            if not candidates:
                continue
            year_line, year = min(
                candidates,
                key=lambda item: (
                    abs(_source_line_index(item[0], "split document period year") - line_index),
                    abs(center_x2_v1(item[0]) - center_x2_v1(line)),
                ),
            )
            remaining_years.remove((year_line, year))
            surface = _date_surface(day, month, year)
            if surface is None:
                continue
            indices = tuple(
                sorted(
                    (
                        line_index,
                        _source_line_index(year_line, "split document period year"),
                    )
                )
            )
            page_observations.add((date(year, month, day), indices))

        for parsed, indices in sorted(page_observations):
            observations.setdefault(parsed, []).append(
                {
                    "page_sequence": page_sequence,
                    "source_line_indices": list(indices),
                }
            )
    return observations


def infer_document_reporting_period_context_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Infer a document-wide period context from repeated visible full dates.

    This is a bank-, filename-, note- and family-blind context proposal.  A
    family must still bind the applicable local table headers and must not use
    this record alone as numeric, mapping, or schema authority.
    """

    observations = _document_date_observations(pages)
    summaries: list[dict[str, Any]] = []
    for parsed in sorted(observations):
        evidence = sorted(
            observations[parsed],
            key=lambda item: (item["page_sequence"], item["source_line_indices"]),
        )
        page_count = len({item["page_sequence"] for item in evidence})
        summaries.append(
            {
                "date": parsed.strftime("%d/%m/%Y"),
                "evidence": evidence[:_MAX_DOCUMENT_DATE_EVIDENCE],
                "evidence_truncated": len(evidence) > _MAX_DOCUMENT_DATE_EVIDENCE,
                "occurrence_count": len(evidence),
                "page_count": page_count,
            }
        )

    candidates = [
        (parsed, evidence)
        for parsed, evidence in observations.items()
        if (parsed.month, parsed.day) in _REPORTING_PERIOD_ENDS
        and _REPORTING_YEAR.fullmatch(f"{parsed.year:04d}") is not None
        and len({item["page_sequence"] for item in evidence}) >= 2
    ]
    if not candidates:
        return {
            "balance_comparative_period_end": None,
            "current_period_end": None,
            "current_period_start": None,
            "flow_comparative_period_end": None,
            "flow_comparative_period_start": None,
            "observed_dates": summaries,
            "period_kind": None,
            "reporting_year": None,
            "resolution": "UNRESOLVED_NO_REPEATED_REPORTING_END_DATE",
            "supporting_page_count": 0,
        }

    maximum_page_support = max(
        len({evidence["page_sequence"] for evidence in candidate_evidence})
        for _candidate, candidate_evidence in candidates
    )
    dominant_candidates = [
        (candidate, candidate_evidence)
        for candidate, candidate_evidence in candidates
        if len({evidence["page_sequence"] for evidence in candidate_evidence}) * 4
        >= maximum_page_support
    ]
    current, current_evidence = max(
        dominant_candidates,
        key=lambda item: (
            item[0],
            len({evidence["page_sequence"] for evidence in item[1]}),
            len(item[1]),
        ),
    )
    previous_year = current.year - 1

    def observed_surface(day: int, month: int, year: int) -> str | None:
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        return candidate.strftime("%d/%m/%Y") if candidate in observations else None

    balance_comparative = observed_surface(31, 12, previous_year)
    flow_comparative = observed_surface(current.day, current.month, previous_year)
    current_start = observed_surface(1, 1, current.year)
    flow_comparative_start = observed_surface(1, 1, previous_year)
    period_kind = {
        (3, 31): "FIRST_QUARTER",
        (6, 30): "HALF_YEAR_OR_SECOND_QUARTER",
        (9, 30): "NINE_MONTH_OR_THIRD_QUARTER",
        (12, 31): "ANNUAL",
    }[(current.month, current.day)]
    return {
        "balance_comparative_period_end": balance_comparative,
        "current_period_end": current.strftime("%d/%m/%Y"),
        "current_period_start": current_start,
        "flow_comparative_period_end": flow_comparative,
        "flow_comparative_period_start": flow_comparative_start,
        "observed_dates": summaries,
        "period_kind": period_kind,
        "reporting_year": current.year,
        "resolution": "DOMINANT_REPEATED_FULL_DATE_CONSENSUS",
        "supporting_page_count": len({evidence["page_sequence"] for evidence in current_evidence}),
    }


def resolve_relative_period_axis_v1(
    relative_axis: Any,
    document_context: Any,
    *,
    period_semantics: str,
) -> tuple[list[dict[str, Any]], str]:
    """Bind local end/start labels to document dates for one table semantics.

    Balance tables resolve ``Số đầu kỳ`` to the comparative balance-sheet end;
    rollforwards resolve the same surface to the current reporting-period start.
    The caller must explicitly declare which accounting structure it validated.
    """

    if period_semantics not in {"BALANCE_COMPARATIVE", "CURRENT_ROLLFORWARD"}:
        raise _error("relative period accounting semantics drifted")
    if type(relative_axis) is not list or len(relative_axis) != 2:
        return [], "UNRESOLVED"
    if type(document_context) is not dict or set(document_context) != {
        "balance_comparative_period_end",
        "current_period_end",
        "current_period_start",
        "flow_comparative_period_end",
        "flow_comparative_period_start",
        "observed_dates",
        "period_kind",
        "reporting_year",
        "resolution",
        "supporting_page_count",
    }:
        raise _error("document reporting-period context fields drifted")
    if document_context["resolution"] != "DOMINANT_REPEATED_FULL_DATE_CONSENSUS":
        return [], "UNRESOLVED"

    by_local_role: dict[str, Mapping[str, Any]] = {}
    for item in relative_axis:
        if not isinstance(item, Mapping) or set(item) != {
            "evidence_source_line_indices",
            "period",
            "x_center_x2",
        }:
            raise _error("relative period axis item fields drifted")
        role = item["period"]
        evidence = item["evidence_source_line_indices"]
        x_center = item["x_center_x2"]
        if (
            role not in {"CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"}
            or role in by_local_role
            or type(evidence) is not list
            or not evidence
            or any(type(index) is not int or index < 0 for index in evidence)
            or type(x_center) is not int
        ):
            raise _error("relative period axis item identity drifted")
        by_local_role[role] = item
    if set(by_local_role) != {"CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"}:
        return [], "UNRESOLVED"

    second_context_field, second_resolved_role = (
        ("balance_comparative_period_end", "BALANCE_COMPARATIVE_PERIOD_END")
        if period_semantics == "BALANCE_COMPARATIVE"
        else ("current_period_start", "CURRENT_PERIOD_START")
    )
    bindings = (
        (
            "CURRENT_PERIOD_END",
            "current_period_end",
            "CURRENT_PERIOD_END",
        ),
        (
            "COMPARATIVE_PERIOD_START",
            second_context_field,
            second_resolved_role,
        ),
    )
    resolved: list[dict[str, Any]] = []
    for local_role, context_field, resolved_role in bindings:
        period = document_context[context_field]
        if type(period) is not str or _FULL_DATE.fullmatch(period) is None:
            return [], "UNRESOLVED"
        item = by_local_role[local_role]
        resolved.append(
            {
                "evidence_source_line_indices": list(item["evidence_source_line_indices"]),
                "local_period_role": local_role,
                "resolved_period": period,
                "resolved_role": resolved_role,
                "x_center_x2": item["x_center_x2"],
            }
        )
    return sorted(resolved, key=lambda item: item["x_center_x2"]), (
        "DOCUMENT_CONTEXT_BALANCE_COMPARATIVE"
        if period_semantics == "BALANCE_COMPARATIVE"
        else "DOCUMENT_CONTEXT_CURRENT_ROLLFORWARD"
    )


def extract_typed_value_vector_v1(
    lines: Sequence[Mapping[str, Any]],
    lane_types: Sequence[str],
    *,
    primary_numeric_authority: bool,
) -> list[dict[str, Any]] | None:
    """Take the first ordered numeric surface for each declared lane."""

    if type(primary_numeric_authority) is not bool:
        raise _error("primary numeric authority flag drifted")
    if (
        isinstance(lane_types, (str, bytes))
        or not lane_types
        or any(type(item) is not str or item not in {"MONEY", "PERCENT"} for item in lane_types)
    ):
        raise _error("typed lane declaration drifted")
    numeric = sorted(
        (
            line
            for line in lines
            if is_number_like_v1(_text(line, "value line"))
            or (type(line.get("source_text")) is str and is_number_like_v1(line["source_text"]))
        ),
        key=center_x2_v1,
    )
    if len(numeric) != len(lane_types):
        return None
    result: list[dict[str, Any]] = []
    for lane_index, (line, lane_type) in enumerate(
        zip(numeric[: len(lane_types)], lane_types, strict=True)
    ):
        semantic_surface = _text(line, "value line")
        source = line.get("source_text")
        source_authoritative = (
            primary_numeric_authority and type(source) is str and is_number_like_v1(source)
        )
        result.append(
            {
                "lane_index": lane_index,
                "lane_type": lane_type,
                "semantic_surface": semantic_surface,
                "source_authoritative": source_authoritative,
                "source_line_index": _source_line_index(line, "value line"),
                "surface": source if source_authoritative else semantic_surface,
                "x_center_x2": center_x2_v1(line),
            }
        )
    return result


def money_values_v1(vector: Sequence[Mapping[str, Any]]) -> list[int] | None:
    result: list[int] = []
    for item in vector:
        if item.get("lane_type") != "MONEY":
            continue
        value = money_integer_v1(item.get("surface"))
        if value is None or item.get("source_authoritative") is not True:
            return None
        result.append(value)
    return result


def percentage_values_v1(vector: Sequence[Mapping[str, Any]]) -> list[Decimal] | None:
    result: list[Decimal] = []
    for item in vector:
        if item.get("lane_type") != "PERCENT":
            continue
        surface = item.get("surface")
        if type(surface) is not str or item.get("source_authoritative") is not True:
            return None
        value = _percentage(surface)
        if value is None:
            return None
        result.append(value)
    return result
