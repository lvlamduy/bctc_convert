"""Bank-blind graph for customer-loan geographic concentration.

The live TM interval is 759--765.  A qualifying source region must contain a
geographic-concentration heading, the domestic/foreign pair, and an axis whose
scope is exactly customer loans.  The same graph accepts both layouts seen in
real bank PDFs: geography as rows with accounting families as columns, or
geography as columns with accounting families as rows.  Consecutive
``(tiếp theo)`` pages are one logical region.

Text is fresh VietOCR Transformer anchor evidence only.  Numeric truth,
period/unit scope, schema equivalence and mapping require a later independent
pixel/source replay.  Generic total-loan axes that also contain interbank
loans, purchased debt or other credit are retained as near regions, never
silently narrowed to customer loans.  Geographic segment-report tables are
negative controls rather than aliases for this family.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanGeographyVariantGraphV1Error",
    "build_loan_geography_variant_graph_document_v1",
    "validate_loan_geography_variant_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_GEOGRAPHY_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "LOAN_GEOGRAPHIC_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_GEOGRAPHIC_CONCENTRATION_HEADING_"
    "EXACT_CUSTOMER_LOAN_AXIS_DOMESTIC_FOREIGN_PAIR_ROW_OR_COLUMN_LAYOUT_"
    "CONTINUATION_FIRST_LAST_NEXT_BOUNDARY_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_for_matching_or_routing": False,
    "broad_total_loan_axis_can_be_narrowed_to_customer_loans": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "geography_child_order_fixed": False,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "segment_report_is_negative_control": True,
    "text_similarity_alone_can_accept": False,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "metrics",
    "near_regions",
    "negative_controls",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_NUMBER = re.compile(r"^\(?[+-]?[0-9]+(?:[., ][0-9]+)*%?\)?$")
_DASH = re.compile(r"^[\-–—]+$")
_MAJOR_NOTE = re.compile(r"^\s*(?:[0-9]{1,3}[.)](?:\s+.*)?|[0-9]{1,2}\.[0-9]{1,2}(?:\s+.*)?)\s*$")
_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9]\s+nam\s+20[0-9]{2})"
)
_MAX_HEADING_LINE_SPAN = 3
_MAX_HEADING_TO_AXIS_LINES = 32
_MAX_CONTINUATION_PAGES = 2


class LoanGeographyVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed geography graph drifted."""


def _error(message: str) -> LoanGeographyVariantGraphV1Error:
    return LoanGeographyVariantGraphV1Error(message)


def _bbox(value: Any) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("line bbox must be four exact positive-bound integers")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("loan-geography matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    previous_page = 0
    ordinal = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("loan-geography matcher page fields drifted")
        sequence = raw_page["page_sequence"]
        if type(sequence) is not int or sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        for expected_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("loan-geography matcher line fields drifted")
            if raw_line["source_line_index"] != expected_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if type(raw_line["vietocr_text"]) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            bbox = _bbox(raw_line["bbox"])
            lines.append(
                {
                    "bbox": bbox,
                    "center_x": (bbox[0] + bbox[2]) / 2,
                    "center_y": (bbox[1] + bbox[3]) / 2,
                    "global_ordinal": ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["vietocr_text"]),
                    "page_sequence": sequence,
                    "source_line_index": expected_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            ordinal += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = sequence
    return pages


def _union_bbox(lines: Sequence[Mapping[str, Any]]) -> list[int]:
    return [
        min(line["bbox"][0] for line in lines),
        min(line["bbox"][1] for line in lines),
        max(line["bbox"][2] for line in lines),
        max(line["bbox"][3] for line in lines),
    ]


def _surface(lines: Sequence[Mapping[str, Any]]) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines).strip()


def _record(lines: Sequence[Mapping[str, Any]], kind: str) -> dict[str, Any]:
    ordered = sorted(lines, key=lambda line: (line["center_y"], line["center_x"]))
    surface = _surface(ordered)
    return {
        "bbox": _union_bbox(ordered),
        "end_source_line_index": max(line["source_line_index"] for line in ordered),
        "global_ordinal": min(line["global_ordinal"] for line in ordered),
        "match_kind": kind,
        "normalized_surface": normalize_vietnamese_anchor_v1(surface),
        "page_sequence": ordered[0]["page_sequence"],
        "source_line_index": min(line["source_line_index"] for line in ordered),
        "surface": surface,
    }


def _heading_kind(value: str) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(value)
    if (
        "muc do tap trung" in normalized
        and ("khu vuc dia ly" in normalized or "theo vung" in normalized)
        and any(token in normalized for token in ("tai san", "cong no", "no phai tra"))
    ):
        return "GEOGRAPHIC_CONCENTRATION"
    return None


def _heading_matches(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    lines = page["lines"]
    matches: list[dict[str, Any]] = []
    for start in range(len(lines)):
        for width in range(1, min(_MAX_HEADING_LINE_SPAN, len(lines) - start) + 1):
            window = lines[start : start + width]
            kind = _heading_kind(_surface(window))
            if kind is not None:
                matches.append(_record(window, kind))
                break
    selected: dict[int, dict[str, Any]] = {}
    for match in matches:
        end = match["end_source_line_index"]
        current = selected.get(end)
        if current is None or match["source_line_index"] > current["source_line_index"]:
            selected[end] = match
    return [selected[key] for key in sorted(selected)]


def _segment_negative_controls(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    lines = page["lines"]
    controls: list[dict[str, Any]] = []
    for start in range(len(lines)):
        for width in range(1, min(3, len(lines) - start) + 1):
            window = lines[start : start + width]
            normalized = normalize_vietnamese_anchor_v1(_surface(window))
            if "bao cao bo phan" in normalized and (
                "khu vuc dia ly" in normalized or "theo khu vuc" in normalized
            ):
                record = _record(window, "GEOGRAPHIC_SEGMENT_REPORT")
                record["unresolved_reason"] = "SEGMENT_REPORT_NOT_CUSTOMER_LOAN_GEOGRAPHY"
                controls.append(record)
                break
    selected: dict[int, dict[str, Any]] = {}
    for control in controls:
        end = control["end_source_line_index"]
        current = selected.get(end)
        if current is None or control["source_line_index"] > current["source_line_index"]:
            selected[end] = control
    return [selected[key] for key in sorted(selected)]


def _standalone_geography_matches(page: Mapping[str, Any], expected: str) -> list[dict[str, Any]]:
    matches = []
    for line in page["lines"]:
        normalized = line["normalized_text"].strip()
        if normalized == expected:
            matches.append(_record([line], expected.upper().replace(" ", "_")))
    return matches


def _x_overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    start = max(left["bbox"][0], right["bbox"][0])
    stop = min(left["bbox"][2], right["bbox"][2])
    width = min(left["bbox"][2] - left["bbox"][0], right["bbox"][2] - right["bbox"][0])
    return max(0, stop - start) / max(1, width)


def _loan_scope(normalized: str) -> str | None:
    if "cho vay" not in normalized and "vay khach hang" not in normalized:
        return None
    if any(
        token in normalized
        for token in (
            "tong tien gui",
            "cam ket",
            "chung khoan theo khu vuc",
        )
    ):
        return None
    if "cho vay khach hang" in normalized or "vay khach hang" in normalized:
        if any(
            token in normalized
            for token in (
                "bao gom",
                "mua",
                "tctd",
                "to chuc tin",
                "to chuc tin dung",
                "cap tin dung",
            )
        ):
            return "BROAD_MIXED_LOAN_POPULATION"
        return "EXACT_CUSTOMER_LOANS"
    if "du no cho vay" in normalized or normalized in {"cho vay", "tong cho vay"}:
        return "BROAD_TOTAL_LOANS"
    return None


def _loan_label_specificity(match: Mapping[str, Any]) -> tuple[int, int]:
    normalized = match["normalized_surface"]
    footnote_penalty = int("bao gom" in normalized)
    if "tong du no cho vay khach hang" in normalized:
        return footnote_penalty, 0
    if "tong du no cho vay" in normalized:
        return footnote_penalty, 1
    if normalized.startswith("cho vay khach hang"):
        return footnote_penalty, 2
    if "vay khach hang" in normalized:
        return footnote_penalty, 3
    return footnote_penalty, 4


def _loan_axis_matches(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    lines = page["lines"]
    matches: list[dict[str, Any]] = []
    for line in lines:
        candidates: list[list[Mapping[str, Any]]] = [[line]]
        for other in lines:
            if other is line or other["center_y"] == line["center_y"]:
                continue
            if abs(other["center_y"] - line["center_y"]) > 100 or _x_overlap(line, other) < 0.35:
                continue
            if not any(
                token in other["normalized_text"]
                for token in ("cho vay", "vay", "du no", "khach hang", "mua", "tctd", "tin dung")
            ):
                continue
            candidates.append([line, other])
        for window in candidates:
            ordered = sorted(window, key=lambda item: item["center_y"])
            normalized = normalize_vietnamese_anchor_v1(_surface(ordered))
            scope = _loan_scope(normalized)
            if scope is None:
                continue
            matches.append(_record(ordered, scope))
    selected: dict[tuple[int, int, str], dict[str, Any]] = {}
    priority = {"EXACT_CUSTOMER_LOANS": 0, "BROAD_MIXED_LOAN_POPULATION": 1, "BROAD_TOTAL_LOANS": 2}
    for match in matches:
        key = (match["source_line_index"], match["end_source_line_index"], match["match_kind"])
        current = selected.get(key)
        if current is None or len(match["normalized_surface"]) < len(current["normalized_surface"]):
            selected[key] = match
    ordered = sorted(
        selected.values(),
        key=lambda item: (
            item["source_line_index"],
            priority[item["match_kind"]],
            len(item["normalized_surface"]),
        ),
    )
    deduped: list[dict[str, Any]] = []
    for match in ordered:
        if any(
            match["match_kind"] == existing["match_kind"]
            and abs(match["bbox"][0] - existing["bbox"][0]) < 20
            and abs(match["bbox"][1] - existing["bbox"][1]) < 20
            for existing in deduped
        ):
            continue
        deduped.append(match)
    return deduped


def _is_money(value: str) -> bool:
    compact = value.strip().replace("\u00a0", " ").replace("\u202f", " ").replace(" ", "")
    if _DASH.fullmatch(compact) is not None:
        return True
    if _NUMBER.fullmatch(compact) is not None and any(char.isdigit() for char in compact):
        return True
    body = compact.strip("()")
    digits = sum(char.isdigit() for char in body)
    letters = [char.lower() for char in body if char.isalpha()]
    return (
        digits >= 4
        and 1 <= len(letters) <= 2
        and all(char in {"b", "i", "l", "o", "s", "z"} for char in letters)
        and all(char.isdigit() or char in ".,-" or char.isalpha() for char in body)
        and digits / (digits + len(letters)) >= 0.70
    )


def _money_record(line: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "source_line_index": line["source_line_index"],
        "source_text": line["source_text"],
        "vietocr_text": line["vietocr_text"],
    }


def _layout(
    domestic: Mapping[str, Any], foreign: Mapping[str, Any], loan: Mapping[str, Any]
) -> str:
    domestic_y = sum(domestic["bbox"][1::2]) / 2
    foreign_y = sum(foreign["bbox"][1::2]) / 2
    loan_y = sum(loan["bbox"][1::2]) / 2
    if abs(domestic_y - foreign_y) <= 55 and loan_y > domestic_y:
        return "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS"
    return "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS"


def _nearest_row_value(
    page: Mapping[str, Any], label: Mapping[str, Any], loan: Mapping[str, Any]
) -> dict[str, Any] | None:
    label_y = sum(label["bbox"][1::2]) / 2
    loan_x = sum(loan["bbox"][::2]) / 2
    candidates = [
        line
        for line in page["lines"]
        if _is_money(line["vietocr_text"])
        and abs(line["center_y"] - label_y) <= 24
        and line["bbox"][0] > label["bbox"][2]
    ]
    if not candidates:
        return None
    selected = min(candidates, key=lambda line: abs(line["center_x"] - loan_x))
    if abs(selected["center_x"] - loan_x) > 100:
        return None
    return _money_record(selected)


def _nearest_column_value(
    page: Mapping[str, Any], header: Mapping[str, Any], loan: Mapping[str, Any]
) -> dict[str, Any] | None:
    header_x = sum(header["bbox"][::2]) / 2
    loan_y = sum(loan["bbox"][1::2]) / 2
    candidates = [
        line
        for line in page["lines"]
        if _is_money(line["vietocr_text"])
        and abs(line["center_y"] - loan_y) <= 24
        and line["bbox"][0] > loan["bbox"][0]
    ]
    if not candidates:
        return None
    selected = min(candidates, key=lambda line: abs(line["center_x"] - header_x))
    if abs(selected["center_x"] - header_x) > 90:
        return None
    return _money_record(selected)


def _periods_and_units(
    page: Mapping[str, Any], start: int, stop: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    periods: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    for line in page["lines"][max(0, start - 6) : min(len(page["lines"]), stop + 6)]:
        normalized = line["normalized_text"]
        record = {
            "bbox": list(line["bbox"]),
            "page_sequence": line["page_sequence"],
            "source_line_index": line["source_line_index"],
            "vietocr_text": line["vietocr_text"],
        }
        if _DATE.search(normalized):
            periods.append(record)
        if normalized in {"trieu dong", "trieu vnd"}:
            units.append(record)
    return periods, units


def _segment(
    page: Mapping[str, Any], heading: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    domestic = [
        item
        for item in _standalone_geography_matches(page, "trong nuoc")
        if heading["end_source_line_index"] < item["source_line_index"]
    ]
    foreign = [
        item
        for item in _standalone_geography_matches(page, "nuoc ngoai")
        if heading["end_source_line_index"] < item["source_line_index"]
    ]
    loans = [
        item
        for item in _loan_axis_matches(page)
        if heading["end_source_line_index"]
        < item["source_line_index"]
        <= heading["end_source_line_index"] + _MAX_HEADING_TO_AXIS_LINES
    ]
    reasons = []
    if not domestic:
        reasons.append("MISSING_DOMESTIC_GEOGRAPHY_CHILD")
    if not foreign:
        reasons.append("MISSING_FOREIGN_GEOGRAPHY_CHILD")
    if not loans:
        reasons.append("MISSING_CUSTOMER_LOAN_OR_TOTAL_LOAN_AXIS")
    near = {
        "heading_match": canonical_clone_v1(heading),
        "page_sequence": page["page_sequence"],
        "unresolved_reasons": reasons,
    }
    if reasons:
        return None, near
    domestic_match = min(domestic, key=lambda item: item["source_line_index"])
    foreign_match = min(foreign, key=lambda item: item["source_line_index"])
    loan = min(
        loans,
        key=lambda item: (
            0 if item["match_kind"] == "EXACT_CUSTOMER_LOANS" else 1,
            _loan_label_specificity(item),
            len(item["normalized_surface"]),
            item["source_line_index"],
        ),
    )
    layout = _layout(domestic_match, foreign_match, loan)
    if layout == "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS":
        domestic_value = _nearest_row_value(page, domestic_match, loan)
        foreign_value = _nearest_row_value(page, foreign_match, loan)
    else:
        domestic_value = _nearest_column_value(page, domestic_match, loan)
        foreign_value = _nearest_column_value(page, foreign_match, loan)
    periods, units = _periods_and_units(
        page,
        heading["source_line_index"],
        max(loan["end_source_line_index"], foreign_match["end_source_line_index"]),
    )
    segment_material = {
        "axis_scope": loan["match_kind"],
        "domestic": {**canonical_clone_v1(domestic_match), "value_proposal": domestic_value},
        "foreign": {**canonical_clone_v1(foreign_match), "value_proposal": foreign_value},
        "heading_match": canonical_clone_v1(heading),
        "layout": layout,
        "loan_axis": canonical_clone_v1(loan),
        "period_headings": periods,
        "unit_headings": units,
    }
    segment = {
        **segment_material,
        "segment_id": "lgvgv1:segment:" + canonical_json_sha256_v1(segment_material),
    }
    if loan["match_kind"] != "EXACT_CUSTOMER_LOANS":
        near.update(
            {
                "axis_scope": loan["match_kind"],
                "domestic": canonical_clone_v1(domestic_match),
                "foreign": canonical_clone_v1(foreign_match),
                "loan_axis": canonical_clone_v1(loan),
                "unresolved_reasons": ["LOAN_AXIS_SCOPE_BROADER_THAN_CUSTOMER_LOANS"],
            }
        )
        return None, near
    return segment, near


def _heading_key(segment: Mapping[str, Any]) -> str:
    value = segment["heading_match"]["normalized_surface"]
    value = re.sub(r"\b(?:tiep theo|continued)\b", "", value)
    value = re.sub(r"^\s*[0-9]+\s+", "", value)
    return " ".join(value.split())


def _next_boundary(
    pages: Sequence[Mapping[str, Any]], page_sequence: int, source_line_index: int
) -> dict[str, Any] | None:
    for page in pages[page_sequence - 1 :]:
        start = source_line_index + 1 if page["page_sequence"] == page_sequence else 0
        for line in page["lines"][start:]:
            if _MAJOR_NOTE.match(line["vietocr_text"]):
                return {
                    "page_sequence": page["page_sequence"],
                    "source_line_index": line["source_line_index"],
                    "surface": line["vietocr_text"],
                }
    return None


def _regions(
    pages: Sequence[Mapping[str, Any]], segments: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    clusters: list[list[Mapping[str, Any]]] = []
    for segment in sorted(segments, key=lambda item: item["heading_match"]["page_sequence"]):
        if (
            clusters
            and segment["heading_match"]["page_sequence"]
            == clusters[-1][-1]["heading_match"]["page_sequence"] + 1
            and _heading_key(segment) == _heading_key(clusters[-1][-1])
            and len(clusters[-1]) < _MAX_CONTINUATION_PAGES
        ):
            clusters[-1].append(segment)
        else:
            clusters.append([segment])
    regions = []
    for cluster in clusters:
        first = cluster[0]
        last = cluster[-1]
        last_indices = [
            last["loan_axis"]["end_source_line_index"],
            last["domestic"]["end_source_line_index"],
            last["foreign"]["end_source_line_index"],
        ]
        for role in ("domestic", "foreign"):
            value = last[role]["value_proposal"]
            if value is not None:
                last_indices.append(value["source_line_index"])
        last_index = max(last_indices)
        material = {
            "cluster_boundary": {
                "first_item_role": "GEOGRAPHIC_CONCENTRATION_HEADING",
                "first_page_sequence": first["heading_match"]["page_sequence"],
                "first_source_line_index": first["heading_match"]["source_line_index"],
                "last_item_role": "FOREIGN_CUSTOMER_LOAN_GEOGRAPHY_VALUE_OR_SLOT",
                "last_page_sequence": last["heading_match"]["page_sequence"],
                "last_source_line_index": last_index,
                "next_numbered_boundary": _next_boundary(
                    pages, last["heading_match"]["page_sequence"], last_index
                ),
                "selection_rule": (
                    "GEOGRAPHIC_HEADING_PLUS_EXACT_CUSTOMER_LOAN_AXIS_PAIR_THEN_"
                    "DOMESTIC_FOREIGN_STRUCTURE_THROUGH_CONTINUATION_BEFORE_NEXT_NOTE"
                ),
            },
            "minimal_anchor": {
                "combination_size": 2,
                "pair_search_exhausted_before_larger_combinations": True,
                "roles": ["GEOGRAPHIC_CONCENTRATION_HEADING", "EXACT_CUSTOMER_LOAN_AXIS"],
            },
            "segments": canonical_clone_v1(cluster),
        }
        regions.append(
            {**material, "region_id": "lgvgv1:region:" + canonical_json_sha256_v1(material)}
        )
    return regions


def _build(value: Any) -> dict[str, Any]:
    pages = _pages(value)
    segments: list[dict[str, Any]] = []
    near_regions: list[dict[str, Any]] = []
    negative_controls: list[dict[str, Any]] = []
    heading_count = 0
    for page in pages:
        negative_controls.extend(_segment_negative_controls(page))
        for heading in _heading_matches(page):
            heading_count += 1
            segment, near = _segment(page, heading)
            if segment is None:
                near_regions.append(near)
            else:
                segments.append(segment)
    regions = _regions(pages, segments)
    uniqueness_status = (
        "UNIQUE_FULL_MATCH"
        if len(regions) == 1
        else "NO_FULL_MATCH"
        if not regions
        else "MULTIPLE_FULL_MATCHES"
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_customer_loan_geography_region_count": len(regions),
            "complete_pdf_page_count": len(pages),
            "exact_customer_loan_segment_count": len(segments),
            "geographic_concentration_heading_count": heading_count,
            "near_region_count": len(near_regions),
            "segment_report_negative_control_count": len(negative_controls),
        },
        "near_regions": near_regions,
        "negative_controls": negative_controls,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if not regions
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        ),
        "uniqueness": {"complete_region_count": len(regions), "status": uniqueness_status},
    }
    return {**material, "result_id": "lgvgv1:result:" + canonical_json_sha256_v1(material)}


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-geography graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["negative_controls"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("loan-geography graph identity, authority or axes drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lgvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-geography graph identity drifted")
    return canonical_clone_v1(value)


def build_loan_geography_variant_graph_document_v1(document_pages: Any) -> dict[str, Any]:
    """Scan one complete PDF for the shared customer-loan geography graph."""

    return _validate_shape(_build(document_pages))


def validate_loan_geography_variant_graph_replay_v1(
    value: Any, document_pages: Any
) -> dict[str, Any]:
    """Rebuild the complete-PDF graph and reject coordinated self-rehashes."""

    checked = _validate_shape(value)
    rebuilt = _build(document_pages)
    if not same_typed_json_v1(checked, rebuilt):
        raise _error("loan-geography graph does not replay exactly")
    return checked
