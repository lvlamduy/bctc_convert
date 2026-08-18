"""Bank-blind graph for the combined trading/investment-securities net row.

The schema contains one optional summary item immediately after the two
securities-sale families.  A complete region is a combined-net label (possibly
wrapped) followed by exactly two monetary values on the same page.  A section
heading with the same words is retained as a near control because it is
followed by period/unit axes rather than values.

Fresh VietOCR is used only to locate the label.  Numeric, schema, mapping and
export authority are deliberately outside this graph.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "CombinedSecuritiesNetVariantGraphV1Error",
    "build_combined_securities_net_variant_graph_document_v1",
    "validate_combined_securities_net_variant_graph_replay_v1",
]

FORMAT_VERSION = "COMBINED_SECURITIES_NET_VARIANT_GRAPH_DOCUMENT_V1"
_NET_PREFIXES = (
    "lai thuan tu ",
    "lai lo thuan tu ",
    "lo lai thuan tu ",
)
_RESULT_FIELDS = {
    "claim_boundary",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_COMBINED_TRADING_AND_INVESTMENT_"
    "SECURITIES_NET_LABEL_ONE_OR_TWO_LINES_FOLLOWED_BY_TWO_PERIOD_VALUES_"
    "STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "section_heading_without_values_can_accept": False,
    "text_similarity_alone_can_accept": False,
}


class CombinedSecuritiesNetVariantGraphV1Error(ValueError):
    """The complete-PDF input or combined-securities graph drifted."""


def _error(message: str) -> CombinedSecuritiesNetVariantGraphV1Error:
    return CombinedSecuritiesNetVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_combined_securities_net"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name("interest_income_variant_graph_v1.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error("cannot load common accounting graph support")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _is_owner_text(text: str) -> bool:
    """Recognize the family label without fixing optional connector words.

    Annual reports may insert ``mua bán``, ``hoạt động`` or ``và`` between the
    net-income prefix and the two securities families.  Both family anchors
    remain mandatory, and the text must start with the accounting-result
    prefix after stripping a note enumerator.  The start constraint rejects
    explanatory prose such as ``mục lãi/(lỗ) thuần ...``.
    """

    value = _support()._strip_enumerator(text)
    return (
        len(value.split()) <= 20
        and value.startswith(_NET_PREFIXES)
        and "chung khoan kinh doanh" in value
        and "chung khoan dau tu" in value
    )


def _owner_width(lines: Sequence[Mapping[str, Any]], start: int) -> int | None:
    first = lines[start]
    if _is_owner_text(first["normalized_text"]):
        return 1
    if start + 1 >= len(lines) or lines[start + 1]["page_sequence"] != first["page_sequence"]:
        return None
    first_fragment = _support()._strip_enumerator(first["normalized_text"])
    if not first_fragment.startswith(_NET_PREFIXES):
        return None
    combined = f"{first['normalized_text']} {lines[start + 1]['normalized_text']}".strip()
    return 2 if _is_owner_text(combined) else None


def _region(lines: Sequence[Mapping[str, Any]], start: int, width: int) -> dict[str, Any]:
    support = _support()
    owner_lines = lines[start : start + width]
    page_sequence = owner_lines[0]["page_sequence"]
    owner_top = min(line["bbox"][1] for line in owner_lines)
    owner_bottom = max(line["bbox"][3] for line in owner_lines)
    after = [
        line
        for line in lines[start + width : start + width + 4]
        if line["page_sequence"] == page_sequence
    ]
    values = []
    for line in after:
        text = line["normalized_text"]
        if support._axis_role(text) is not None:
            break
        if support._NUMBER.fullmatch(text):
            overlap = min(owner_bottom, line["bbox"][3]) - max(owner_top, line["bbox"][1])
            if overlap > 0:
                values.append(line)
        elif values:
            break
    complete = len(values) == 2
    return {
        "complete": complete,
        "label_line_count": width,
        "owner": [support._line_ref(line, "OWNER") for line in owner_lines],
        "page_span": [page_sequence, page_sequence],
        "presentation": (
            "WRAPPED_LABEL_THEN_TWO_PERIOD_VALUES"
            if width == 2
            else "INLINE_LABEL_THEN_TWO_PERIOD_VALUES"
        ),
        "value_lines": [support._line_ref(line, "VALUE_POSITION") for line in values],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "two_value_region_count": sum(len(item["value_lines"]) == 2 for item in regions),
        "wrapped_complete_region_count": sum(item["label_line_count"] == 2 for item in regions),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("combined-securities graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("combined-securities graph identity or metrics drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    expected_uniqueness = {
        "complete_region_count": count,
        "status": "UNIQUE_FULL_MATCH" if count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("combined-securities graph uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "csnvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("combined-securities graph identity drifted")
    return canonical_clone_v1(value)


def build_combined_securities_net_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every numeric-bearing combined-net row in one complete PDF."""

    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = []
    for index in range(len(lines)):
        width = _owner_width(lines, index)
        if width is not None:
            candidates.append(_region(lines, index, width))
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH" if len(regions) == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": "csnvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_combined_securities_net_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_combined_securities_net_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("combined-securities graph does not replay exactly")
    return supplied
