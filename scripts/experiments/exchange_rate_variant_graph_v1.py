"""Bank-blind structural matcher for disclosed end-period exchange-rate tables."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "EXCHANGE_RATE_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TEXT_OWNER_PERIOD_UNIT_CURRENCY_ROW_GEOMETRY_PAIR_FIRST_"
    "BANK_BLIND_COMPLETE_DOCUMENT_STRUCTURAL_LOCALIZATION_ONLY_NO_NUMERIC_"
    "SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
SUPPORTED_CODES = ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "THB", "SEK")
KNOWN_SOURCE_CODES = tuple(
    sorted({*SUPPORTED_CODES, "CNY", "DKK", "NZD", "NOK", "HKD", "KRW", "LAK", "XAU"})
)
_NUMERIC = re.compile(r"^[0-9]{1,3}(?:[.,][0-9]{1,3}){0,3}$")
_DATE = re.compile(r"(?:^|\D)([0-3]?\d)[/.-]([01]?\d)[/.-](20\d{2})(?:\D|$)")
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "graph_id",
    "metrics",
    "regions",
    "state",
    "uniqueness",
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "complete_document_input_required": True,
    "currency_code_pair_or_owner_alone_sufficient": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "pair_first_search": True,
    "period_axis_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unit_or_vnd_context_required": True,
}


class ExchangeRateVariantGraphV1Error(ValueError):
    """The bank-blind exchange-rate structural contract drifted."""


def _error(message: str) -> ExchangeRateVariantGraphV1Error:
    return ExchangeRateVariantGraphV1Error(message)


def _accentless(value: str) -> str:
    value = value.translate(str.maketrans({"đ": "d", "Đ": "D"}))
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", folded.casefold()))


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
        raise _error("line bbox drifted")
    return list(value)


def _line(value: Any, expected_index: int) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "bbox",
            "source_line_index",
            "source_text",
            "vietocr_text",
            "vietocr_text_accentless",
        }
        or value["source_line_index"] != expected_index
        or type(value["vietocr_text"]) is not str
        or (value["source_text"] is not None and type(value["source_text"]) is not str)
        or type(value["vietocr_text_accentless"]) is not str
    ):
        raise _error("fresh VietOCR line shape drifted")
    return {**canonical_clone_v1(value), "bbox": _bbox(value["bbox"])}


def _pages(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("document pages must be one nonempty list")
    pages: list[dict[str, Any]] = []
    expected_page = 1
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != {"lines", "page_sequence", "primary_numeric_authority"}
            or raw["page_sequence"] != expected_page
            or type(raw["primary_numeric_authority"]) is not bool
            or type(raw["lines"]) is not list
        ):
            raise _error("document page axis drifted")
        pages.append(
            {
                "lines": [_line(line, index) for index, line in enumerate(raw["lines"])],
                "page_sequence": expected_page,
                "primary_numeric_authority": raw["primary_numeric_authority"],
            }
        )
        expected_page += 1
    return pages


def _is_owner(window: str) -> bool:
    return (
        "ty gia" in window
        and "ngoai te" in window
        and any(
            token in window
            for token in ("thoi diem", "cuoi ky", "lap bao cao", "ket thuc giai doan")
        )
    )


def _dates(lines: Sequence[Mapping[str, Any]], start: int) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for line in lines[start : min(len(lines), start + 22)]:
        for day, month, year in _DATE.findall(line["vietocr_text"]):
            found.append(
                {
                    "day": int(day),
                    "line_index": line["source_line_index"],
                    "month": int(month),
                    "raw_text": line["vietocr_text"],
                    "year": int(year),
                }
            )
    stop = min(len(lines), start + 22)
    for index in range(start, stop):
        window = " ".join(
            _accentless(line["vietocr_text"]) for line in lines[index : min(stop, index + 2)]
        )
        match = re.search(r"(?:ngay )?(\d{1,2}) thang (\d{1,2})(?: nam)? (20\d{2})", window)
        if match is not None:
            day, month, year = (int(item) for item in match.groups())
            if not any(
                item["day"] == day and item["month"] == month and item["year"] == year
                for item in found
            ):
                found.append(
                    {
                        "day": day,
                        "line_index": lines[index]["source_line_index"],
                        "month": month,
                        "raw_text": " ".join(
                            line["vietocr_text"] for line in lines[index : min(stop, index + 2)]
                        ),
                        "year": year,
                    }
                )
        head = _accentless(lines[index]["vietocr_text"])
        if "ngay" not in head or "thang" not in head:
            continue
        for tail_line in lines[index + 1 : min(stop, index + 5)]:
            tail = _accentless(tail_line["vietocr_text"])
            if re.search(r"20\d{2}", tail) is None:
                continue
            left = max(lines[index]["bbox"][0], tail_line["bbox"][0])
            right = min(lines[index]["bbox"][2], tail_line["bbox"][2])
            if right <= left:
                continue
            geometry_match = re.search(
                r"(?:ngay )?(\d{1,2}) thang (\d{1,2})(?: nam)? (20\d{2})",
                f"{head} {tail}",
            )
            if geometry_match is None:
                continue
            day, month, year = (int(item) for item in geometry_match.groups())
            if not any(
                item["day"] == day and item["month"] == month and item["year"] == year
                for item in found
            ):
                found.append(
                    {
                        "day": day,
                        "line_index": lines[index]["source_line_index"],
                        "month": month,
                        "raw_text": f"{lines[index]['vietocr_text']} {tail_line['vietocr_text']}",
                        "year": year,
                    }
                )
    return found


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _code(line: Mapping[str, Any]) -> tuple[str, str] | None:
    if _accentless(line["vietocr_text"]).startswith("vang"):
        return "XAU", "GENERIC_VISIBLE_GOLD_LABEL"
    token = re.sub(r"[^A-Za-z]", "", line["vietocr_text"]).upper()
    if token in KNOWN_SOURCE_CODES:
        return token, "EXACT_FRESH_VIETOCR_CODE"
    if not 2 <= len(token) <= 4:
        return None
    matches = [code for code in KNOWN_SOURCE_CODES if _edit_distance(token, code) == 1]
    return (
        (matches[0], "UNIQUE_EDIT_DISTANCE_ONE_FRESH_VIETOCR_CODE") if len(matches) == 1 else None
    )


def _looks_numeric(line: Mapping[str, Any]) -> bool:
    return _NUMERIC.fullmatch(line["vietocr_text"].strip()) is not None


def _row(lines: Sequence[Mapping[str, Any]], index: int) -> dict[str, Any] | None:
    label = lines[index]
    code_match = _code(label)
    if code_match is None:
        return None
    code, match_status = code_match
    candidates = [
        line
        for line in lines[index + 1 : min(len(lines), index + 5)]
        if _looks_numeric(line) and line["bbox"][0] > label["bbox"][2]
    ]
    if len(candidates) < 2:
        return None
    current, comparative = sorted(candidates[:2], key=lambda item: item["bbox"][0])
    label_y = (label["bbox"][1] + label["bbox"][3]) / 2
    if any(
        abs((item["bbox"][1] + item["bbox"][3]) / 2 - label_y) > 75
        for item in (current, comparative)
    ):
        return None
    return {
        "code": code,
        "comparative_line_index": comparative["source_line_index"],
        "current_line_index": current["source_line_index"],
        "label_bbox": list(label["bbox"]),
        "fresh_label_match_status": match_status,
        "label_line_index": label["source_line_index"],
        "supported_schema_code": code in SUPPORTED_CODES,
    }


def _unit_context(
    lines: Sequence[Mapping[str, Any]], owner_index: int, rows: Sequence[Any]
) -> dict[str, Any]:
    stop = min(len(lines), (rows[0][0] if rows else owner_index + 22) + 1)
    unit_lines = [
        line
        for line in lines[owner_index:stop]
        if line["vietocr_text_accentless"] in {"dong", "vnd"}
        or "so voi vnd" in line["vietocr_text_accentless"]
    ]
    owner_window = " ".join(
        line["vietocr_text_accentless"] for line in lines[owner_index : owner_index + 2]
    )
    implicit_policy_link_allowed = "ty gia" in owner_window and "ngoai te" in owner_window
    return {
        "implicit_vnd_policy_link_required": not unit_lines and implicit_policy_link_allowed,
        "unit_line_indices": [line["source_line_index"] for line in unit_lines],
    }


def _regions(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    regions: list[dict[str, Any]] = []
    for page in pages:
        lines = page["lines"]
        for index in range(len(lines)):
            if "ty gia" not in _accentless(lines[index]["vietocr_text"]):
                continue
            window = " ".join(line["vietocr_text_accentless"] for line in lines[index : index + 2])
            if not _is_owner(window):
                continue
            dates = _dates(lines, index)
            current = [item for item in dates if item["year"] == 2026]
            comparative = [item for item in dates if item["year"] == 2025]
            row_pairs = [
                (line_index, matched)
                for line_index in range(index + 1, len(lines))
                if (matched := _row(lines, line_index)) is not None
            ]
            unit = _unit_context(lines, index, row_pairs)
            status = (
                "COMPLETE"
                if current
                and comparative
                and len(row_pairs) >= 2
                and (unit["unit_line_indices"] or unit["implicit_vnd_policy_link_required"])
                else "NEAR"
            )
            regions.append(
                {
                    "comparative_period": comparative[:1],
                    "current_period": current[:1],
                    "owner_line_indices": [
                        line["source_line_index"] for line in lines[index : index + 2]
                    ],
                    "page_sequence": page["page_sequence"],
                    "primary_numeric_authority": page["primary_numeric_authority"],
                    "rows": [item for _, item in row_pairs],
                    "status": status,
                    "unit_context": unit,
                }
            )
    return regions


def _metrics(regions: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    complete = [item for item in regions if item["status"] == "COMPLETE"]
    return {
        "complete_region_count": len(complete),
        "complete_source_row_count": sum(len(item["rows"]) for item in complete),
        "near_region_count": len(regions) - len(complete),
        "region_count": len(regions),
        "supported_schema_row_count": sum(
            row["supported_schema_code"] for item in complete for row in item["rows"]
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("exchange-rate graph fields drifted")
    regions = value["regions"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "EXCHANGE_RATE_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(regions) is not list
        or not same_typed_json_v1(value["metrics"], _metrics(regions))
    ):
        raise _error("exchange-rate graph identity drifted")
    complete = [item for item in regions if item.get("status") == "COMPLETE"]
    expected_uniqueness = {
        "complete_region_count": len(complete),
        "status": "UNIQUE_FULL_MATCH" if len(complete) == 1 else "NO_UNIQUE_FULL_MATCH",
    }
    if not same_typed_json_v1(value["uniqueness"], expected_uniqueness):
        raise _error("exchange-rate graph uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("graph_id")
    if identity != "ervgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("exchange-rate graph ID drifted")
    return canonical_clone_v1(value)


def build_exchange_rate_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    authenticated_pages = _pages(pages)
    regions = _regions(authenticated_pages)
    complete_count = sum(item["status"] == "COMPLETE" for item in regions)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions),
        "regions": regions,
        "state": "EXCHANGE_RATE_STRUCTURE_SCAN_COMPLETE",
        "uniqueness": {
            "complete_region_count": complete_count,
            "status": "UNIQUE_FULL_MATCH" if complete_count == 1 else "NO_UNIQUE_FULL_MATCH",
        },
    }
    return _validate({**material, "graph_id": "ervgv1:graph:" + canonical_json_sha256_v1(material)})


def validate_exchange_rate_variant_graph_document_v1(value: Any) -> dict[str, Any]:
    return _validate(value)
