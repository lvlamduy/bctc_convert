"""Bank-blind variable graph for customer-loan provision roll-forwards.

The family is identified by accounting structure, not by a fixed row template:
one customer-loan provision owner, opening balance, provision charge/reversal,
one or more optional movement roles, and closing balance.  The same graph admits
flat two-lane tables, overall/subtotal lanes, geographic subaxes, margin-loan or
deferred-LC companion populations, separate general/specific panels, and a
continuation on the immediately following page.

Fresh VietOCR text is used only to locate semantic anchors.  Numeric proposals
and geometry are retained for later pixel/accounting review; this module grants
no numeric, schema, mapping, canonicalization, or export authority.  Bank code,
filename, note number, and page number are never matcher inputs.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
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
    "ProvisionMovementVariantGraphV1Error",
    "build_provision_movement_variant_graph_document_v1",
    "validate_provision_movement_variant_graph_replay_v1",
]


FORMAT_VERSION = "PROVISION_MOVEMENT_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "PROVISION_MOVEMENT_ROLLFORWARD"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CUSTOMER_LOAN_PROVISION_MOVEMENT_"
    "VARIABLE_STRUCTURE_OPENING_MOVEMENTS_CLOSING_GEOMETRY_AND_ACCOUNTING_"
    "PROPOSAL_ONLY_NO_SOURCE_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

_ROLE_ORDER = ("OPENING", "PROVISION", "USE", "FX", "OTHER", "CLOSING")
_REQUIRED_ROLES = frozenset({"OPENING", "PROVISION", "CLOSING"})
_OPTIONAL_MOVEMENT_ROLES = frozenset({"USE", "FX", "OTHER"})
_PARENT_ANCHOR = "PARENT:PROVISION_MOVEMENT_ROLLFORWARD"
_NUMBER = re.compile(r"^\(?-?[0-9]+(?:[.,][0-9]+)*\)?$")
_DASH = re.compile(r"^[\-–—]+$")

_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "blank_or_missing_companion_cells_imputed_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "continuation_requires_repeated_family_owner_on_adjacent_page": True,
    "fresh_vietocr_transformer_text_required": True,
    "geographic_margin_deferred_lc_and_combined_lanes_optional": True,
    "legacy_ocr_used_for_semantic_anchors": False,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "opening_precedes_closing_required": True,
    "optional_movement_roles_fixed_or_required": False,
    "pair_combinations_exhausted_before_triples": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "qwen_or_gemma_used_for_semantic_anchors": False,
    "schema_authority": False,
    "text_similarity_alone_can_accept": False,
    "whole_pdf_uniqueness_required": True,
}

_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "graphs",
    "metrics",
    "near_regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}


class ProvisionMovementVariantGraphV1Error(ValueError):
    """The provision family input, graph, or exact replay drifted."""


def _error(message: str) -> ProvisionMovementVariantGraphV1Error:
    return ProvisionMovementVariantGraphV1Error(message)


def _norm(value: Any, label: str = "text") -> str:
    if type(value) is not str:
        raise _error(f"{label} must be one exact string")
    return normalize_vietnamese_anchor_v1(value)


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


def _line(value: Any, prior_index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "bbox",
        "source_line_index",
        "source_text",
        "vietocr_text",
    }:
        raise _error("provision matcher line fields drifted")
    index = value["source_line_index"]
    if type(index) is not int or index <= prior_index:
        raise _error("source line indices must be exact and strictly increasing")
    source = value["source_text"]
    if source is not None and type(source) is not str:
        raise _error("source text must be null or one exact string")
    text = value["vietocr_text"]
    if type(text) is not str:
        raise _error("fresh VietOCR line text must be one exact string")
    return {
        "bbox": _bbox(value["bbox"]),
        "normalized_text": _norm(text),
        "source_line_index": index,
        "source_text": source,
        "vietocr_text": text,
    }


def _pages(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("provision matcher requires one nonempty complete PDF page list")
    pages: list[dict[str, Any]] = []
    prior_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("provision matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != prior_page + 1:
            raise _error("complete PDF page sequence must be exact and gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        raw_lines = raw_page["lines"]
        if type(raw_lines) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        prior_line = -1
        for raw_line in raw_lines:
            line = _line(raw_line, prior_line)
            lines.append(line)
            prior_line = line["source_line_index"]
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        prior_page = page_sequence
    return pages


def _page_width(lines: Sequence[Mapping[str, Any]]) -> int:
    return max((line["bbox"][2] for line in lines), default=1)


def _short_owner_anchor(text: str) -> bool:
    if not text or "du phong" not in text:
        return False
    forbidden = (
        "chi phi",
        "chinh sach",
        "phan loai no",
        "duoc hach toan",
        "duoc trich lap",
        "trinh bay tai",
        "thuyet minh so",
    )
    if any(token in text for token in forbidden):
        return False
    if "du phong rui ro cho vay khach hang" in text and len(text.split()) <= 14:
        return True
    if "bien dong" in text and "du phong" in text and "cho vay khach hang" in text:
        return True
    if (
        "thay doi" in text
        and "du phong" in text
        and ("cho vay khach hang" in text or "rui ro tin dung" in text)
    ):
        return True
    return False


def _continuation_anchor(text: str) -> bool:
    return _short_owner_anchor(text) and "tiep theo" in text


def _label_side(line: Mapping[str, Any], width: int) -> bool:
    return line["bbox"][0] <= width * 0.62


def _joined_label(
    lines: Sequence[Mapping[str, Any]], start: int, width: int, size: int
) -> tuple[str, tuple[int, ...]] | None:
    selected: list[Mapping[str, Any]] = []
    prior_bottom: int | None = None
    for offset in range(size):
        position = start + offset
        if position >= len(lines):
            return None
        line = lines[position]
        if not _label_side(line, width):
            return None
        if prior_bottom is not None and line["bbox"][1] > prior_bottom + 30:
            return None
        selected.append(line)
        prior_bottom = line["bbox"][3]
    text = " ".join(line["normalized_text"] for line in selected).strip()
    if not text:
        return None
    return text, tuple(line["source_line_index"] for line in selected)


def _movement_role(text: str) -> str | None:
    if text.startswith(("so du dau ky", "so du dau nam")) or text.startswith(
        ("tai ngay 01", "tai ngay 1 thang 1", "tai 01 01")
    ):
        return "OPENING"
    if text.startswith(("so du cuoi ky", "so du cuoi nam")) or text.startswith(
        ("tai ngay 30 thang", "tai ngay 31 thang 12", "tai 30 06", "tai 31 12")
    ):
        return "CLOSING"
    if ("trich lap" in text or "hoan nhap" in text) and (
        "du phong" in text
        or text.startswith(("so trich lap", "trich lap trong ky", "trich lap trong nam"))
    ):
        return "PROVISION"
    if (
        (
            "su dung" in text
            and (
                "du phong" in text
                or "quy" in text
                or text.startswith(("su dung trong ky", "su dung trong nam"))
            )
        )
        or ("xu ly" in text and ("nguon du phong" in text or "khoan no" in text))
        or ("du phong giam do xu ly" in text)
    ):
        return "USE"
    if "chenh lech ty gia" in text:
        return "FX"
    if text.startswith(("tang khac", "giam khac", "dieu chinh")):
        return "OTHER"
    return None


def _events(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    width = _page_width(lines)
    result: list[dict[str, Any]] = []
    consumed: set[int] = set()
    for position in range(len(lines)):
        if position in consumed:
            continue
        match: tuple[str, tuple[int, ...], int] | None = None
        for size in (3, 2, 1):
            joined = _joined_label(lines, position, width, size)
            if joined is None:
                continue
            text, indices = joined
            role = _movement_role(text)
            if role is not None:
                match = role, indices, size
                break
        if match is None:
            continue
        role, indices, size = match
        selected = lines[position : position + size]
        top = min(line["bbox"][1] for line in selected)
        bottom = max(line["bbox"][3] for line in selected)
        left = min(line["bbox"][0] for line in selected)
        right = max(line["bbox"][2] for line in selected)
        value_proposals = []
        for line in lines:
            token = line["vietocr_text"].strip().replace(" ", "")
            center_y = (line["bbox"][1] + line["bbox"][3]) / 2
            if (
                line["bbox"][0] > width * 0.34
                and top - 16 <= center_y <= bottom + 22
                and (_NUMBER.fullmatch(token) or _DASH.fullmatch(token))
            ):
                value_proposals.append(
                    {
                        "bbox": list(line["bbox"]),
                        "parsed_decimal": _decimal_text(token),
                        "raw_text": line["vietocr_text"],
                        "source_line_index": line["source_line_index"],
                    }
                )
        result.append(
            {
                "bbox": [left, top, right, bottom],
                "label_line_indices": list(indices),
                "normalized_label": " ".join(line["normalized_text"] for line in selected).strip(),
                "role": role,
                "value_proposals": sorted(
                    value_proposals,
                    key=lambda item: (item["bbox"][0], item["source_line_index"]),
                ),
                "vietocr_label": " ".join(line["vietocr_text"] for line in selected).strip(),
            }
        )
        consumed.update(range(position, position + size))
    return result


def _decimal_text(token: str) -> str | None:
    raw = token.strip().replace(" ", "")
    if _DASH.fullmatch(raw):
        return None
    if not _NUMBER.fullmatch(raw):
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    raw = raw.replace(".", "").replace(",", "")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if negative:
        value = -value
    return format(value, "f")


def _panels(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    position = 0
    while position < len(events):
        if events[position]["role"] != "OPENING":
            position += 1
            continue
        closing: int | None = None
        next_opening: int | None = None
        for candidate in range(position + 1, len(events)):
            role = events[candidate]["role"]
            if role == "OPENING":
                next_opening = candidate
                break
            if role == "CLOSING" and any(
                item["role"] == "PROVISION" for item in events[position : candidate + 1]
            ):
                closing = candidate
                break
        if closing is None:
            position = next_opening if next_opening is not None else position + 1
            continue
        rows = [canonical_clone_v1(item) for item in events[position : closing + 1]]
        roles = [item["role"] for item in rows]
        if _REQUIRED_ROLES.issubset(roles):
            result.append(
                {
                    "accounting_checks": _accounting_checks(rows),
                    "movement_roles": roles,
                    "rows": rows,
                    "status": "STRUCTURALLY_COMPLETE_MOVEMENT_PANEL",
                }
            )
        position = closing + 1
    return result


def _accounting_checks(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_role: dict[str, list[Decimal]] = {role: [] for role in _ROLE_ORDER}
    for row in rows:
        for proposal in row["value_proposals"]:
            raw = proposal["parsed_decimal"]
            if raw is not None:
                by_role[row["role"]].append(Decimal(raw))
    opening = by_role["OPENING"]
    closing = by_role["CLOSING"]
    checks: list[dict[str, Any]] = []
    lane_count = min(len(opening), len(closing))
    movement_roles = ("PROVISION", "USE", "FX", "OTHER")
    for lane in range(lane_count):
        movements = [by_role[role][lane] for role in movement_roles if lane < len(by_role[role])]
        computed = opening[lane] + sum(movements, Decimal(0))
        checks.append(
            {
                "closing": format(closing[lane], "f"),
                "computed": format(computed, "f"),
                "lane_ordinal": lane + 1,
                "status": (
                    "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
                    if computed == closing[lane]
                    else "UNRESOLVED_SEMANTIC_NUMERIC_OR_SPARSE_LANE"
                ),
            }
        )
    return checks


def _headers(lines: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    terms = (
        "du phong chung",
        "du phong cu the",
        "tong cong",
        "tai viet nam",
        "tai nuoc ngoai",
        "giao dich ky quy",
        "ung truoc",
        "thu tin dung tra cham",
    )
    result = []
    width = _page_width(lines)
    for position in range(len(lines)):
        for size in (2, 1):
            joined = _joined_label(lines, position, width, size)
            if joined is None:
                continue
            text, indices = joined
            matched = next((term for term in terms if term in text), None)
            if matched is None:
                continue
            selected = lines[position : position + size]
            result.append(
                {
                    "header_role": matched.upper().replace(" ", "_"),
                    "line_indices": list(indices),
                    "vietocr_text": " ".join(line["vietocr_text"] for line in selected).strip(),
                }
            )
            break
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for item in result:
        key = item["header_role"], tuple(item["line_indices"])
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _candidate_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for page in pages:
        roots = [line for line in page["lines"] if _short_owner_anchor(line["normalized_text"])]
        if not roots:
            continue
        root = roots[0]
        start = next(
            index
            for index, line in enumerate(page["lines"])
            if line["source_line_index"] == root["source_line_index"]
        )
        region_lines = page["lines"][start:]
        candidates.append(
            {
                "continuation": _continuation_anchor(root["normalized_text"]),
                "events": _events(region_lines),
                "headers": _headers(region_lines),
                "page_sequence": page["page_sequence"],
                "primary_numeric_authority": page["primary_numeric_authority"],
                "root": {
                    "bbox": list(root["bbox"]),
                    "normalized_text": root["normalized_text"],
                    "source_line_index": root["source_line_index"],
                    "vietocr_text": root["vietocr_text"],
                },
            }
        )
    return candidates


def _group_candidates(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for candidate in candidates:
        if (
            candidate["continuation"]
            and groups
            and candidate["page_sequence"] == groups[-1]["page_sequences"][-1] + 1
        ):
            groups[-1]["page_sequences"].append(candidate["page_sequence"])
            groups[-1]["page_records"].append(canonical_clone_v1(candidate))
        else:
            groups.append(
                {
                    "page_records": [canonical_clone_v1(candidate)],
                    "page_sequences": [candidate["page_sequence"]],
                }
            )
    for group in groups:
        events = [event for page in group["page_records"] for event in page["events"]]
        group["panels"] = _panels(events)
        group["roles"] = sorted({event["role"] for event in events}, key=_ROLE_ORDER.index)
        group["headers"] = [header for page in group["page_records"] for header in page["headers"]]
        group["complete"] = bool(group["panels"])
    return groups


def _anchor_set(group: Mapping[str, Any]) -> set[str]:
    return {_PARENT_ANCHOR, *(f"ROLE:{role}" for role in group["roles"])}


def _minimal_anchor(
    selected: Mapping[str, Any], groups: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    selected_anchors = sorted(_anchor_set(selected))
    for size in (2, 3):
        for combination in itertools.combinations(selected_anchors, size):
            matches = sum(set(combination).issubset(_anchor_set(group)) for group in groups)
            if matches == 1:
                return {
                    "anchors": list(combination),
                    "combination_size": size,
                    "full_document_match_count": 1,
                    "status": "UNIQUE_MINIMAL_ANCHOR_COMBINATION",
                }
    return {
        "anchors": selected_anchors,
        "combination_size": len(selected_anchors),
        "full_document_match_count": sum(
            set(selected_anchors).issubset(_anchor_set(group)) for group in groups
        ),
        "status": "UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE",
    }


def _scan(pages: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups = _group_candidates(_candidate_pages(pages))
    complete_groups = [group for group in groups if group["complete"]]
    graphs: list[dict[str, Any]] = []
    for ordinal, group in enumerate(complete_groups, 1):
        material = {
            "family_id": FAMILY_ID,
            "headers": canonical_clone_v1(group["headers"]),
            "minimal_anchor": _minimal_anchor(group, groups),
            "page_records": canonical_clone_v1(group["page_records"]),
            "page_sequences": list(group["page_sequences"]),
            "panels": canonical_clone_v1(group["panels"]),
            "region_ordinal": ordinal,
            "roles": list(group["roles"]),
            "status": "STRUCTURALLY_COMPLETE_PROVISION_MOVEMENT_REGION",
        }
        graphs.append(
            {
                **material,
                "graph_id": "pmvgv1:graph:" + canonical_json_sha256_v1(material),
            }
        )
    near = []
    for group in groups:
        if group["complete"]:
            continue
        root = group["page_records"][0]["root"]
        material = {
            "page_sequences": list(group["page_sequences"]),
            "root": canonical_clone_v1(root),
            "roles": list(group["roles"]),
            "status": "UNRESOLVED_PROVISION_LIKE_REGION_MISSING_COMPLETE_ROLLFORWARD",
        }
        near.append(
            {
                **material,
                "near_region_id": "pmvgv1:near:" + canonical_json_sha256_v1(material),
            }
        )
    return graphs, near


def _metrics(graphs: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]):
    return {
        "accounting_corroborated_lane_count": sum(
            check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
            for graph in graphs
            for panel in graph["panels"]
            for check in panel["accounting_checks"]
        ),
        "complete_provision_region_count": len(graphs),
        "continuation_region_count": sum(len(graph["page_sequences"]) > 1 for graph in graphs),
        "movement_panel_count": sum(len(graph["panels"]) for graph in graphs),
        "near_region_count": len(near),
        "numeric_authority_count": 0,
        "schema_mapping_count": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("provision graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["graphs"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("provision graph identity or safety drifted")
    graph_count = len(value["graphs"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if graph_count == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if graph_count == 0
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    expected_uniqueness = {
        "full_match_count": graph_count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if graph_count == 1
            else "NO_FULL_MATCH"
            if graph_count == 0
            else "AMBIGUOUS_MULTIPLE_FULL_MATCHES"
        ),
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("provision graph status or uniqueness drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["graphs"], value["near_regions"])):
        raise _error("provision graph metrics drifted")
    for graph in value["graphs"]:
        if (
            type(graph) is not dict
            or graph.get("family_id") != FAMILY_ID
            or graph.get("status") != "STRUCTURALLY_COMPLETE_PROVISION_MOVEMENT_REGION"
            or type(graph.get("page_sequences")) is not list
            or not graph["page_sequences"]
            or any(type(page) is not int for page in graph["page_sequences"])
            or type(graph.get("panels")) is not list
            or not graph["panels"]
            or type(graph.get("minimal_anchor")) is not dict
        ):
            raise _error("provision complete graph shape drifted")
        material = canonical_clone_v1(graph)
        identity = material.pop("graph_id", None)
        if identity != "pmvgv1:graph:" + canonical_json_sha256_v1(material):
            raise _error("provision graph identity drifted")
        for panel in graph["panels"]:
            roles = panel.get("movement_roles")
            if (
                type(panel) is not dict
                or panel.get("status") != "STRUCTURALLY_COMPLETE_MOVEMENT_PANEL"
                or type(roles) is not list
                or not _REQUIRED_ROLES.issubset(roles)
                or type(panel.get("rows")) is not list
                or type(panel.get("accounting_checks")) is not list
            ):
                raise _error("provision movement panel shape drifted")
    for near in value["near_regions"]:
        if (
            type(near) is not dict
            or near.get("status") != "UNRESOLVED_PROVISION_LIKE_REGION_MISSING_COMPLETE_ROLLFORWARD"
        ):
            raise _error("provision near-region shape drifted")
        material = canonical_clone_v1(near)
        identity = material.pop("near_region_id", None)
        if identity != "pmvgv1:near:" + canonical_json_sha256_v1(material):
            raise _error("provision near-region identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "pmvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("provision graph result identity drifted")
    return canonical_clone_v1(value)


def build_provision_movement_variant_graph_document_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Scan one complete PDF with the bank-blind provision graph."""

    normalized_pages = _pages(pages)
    graphs, near = _scan(normalized_pages)
    count = len(graphs)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": _metrics(graphs, near),
        "near_regions": near,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if count == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        ),
        "uniqueness": {
            "full_match_count": count,
            "status": (
                "UNIQUE_FULL_MATCH"
                if count == 1
                else "NO_FULL_MATCH"
                if count == 0
                else "AMBIGUOUS_MULTIPLE_FULL_MATCHES"
            ),
        },
    }
    return _validate_result(
        {**material, "result_id": "pmvgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_provision_movement_variant_graph_replay_v1(
    value: Any, pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Exact-rebuild one document result from the complete fresh-text page list."""

    persisted = _validate_result(value)
    rebuilt = build_provision_movement_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("provision graph does not replay exactly")
    return rebuilt
