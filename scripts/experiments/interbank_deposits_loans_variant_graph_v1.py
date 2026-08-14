"""Bank-blind graph for deposits at and loans to other credit institutions.

The shared accounting-variant engine first resolves the outer owner and the
deposit/loan skeleton.  This family wrapper then retains the complete cluster
from that owner through the last loan subtotal or family total, binds visible
period/unit axes, and projects optional inline or trailing parent totals,
currency children, provisions and discount/rediscout disclosures.

An explicit deposit parent and an owner-direct demand-deposit layout are both
family-level variants.  Deposit sibling order may vary.  Bank, filename, page
and note number never participate in matching.  Fresh VietOCR text proposes
anchors only; this module grants no numeric, schema, mapping or export authority.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    build_accounting_variant_region_scan_v1,
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "InterbankDepositsLoansVariantGraphV1Error",
    "build_interbank_deposits_loans_variant_graph_document_v1",
    "validate_interbank_deposits_loans_variant_graph_replay_v1",
]


FORMAT_VERSION = "INTERBANK_DEPOSITS_LOANS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "INTERBANK_DEPOSITS_AND_LOANS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_SHARED_VARIANT_ENGINE_FRESH_VIETOCR_INTERBANK_"
    "DEPOSIT_LOAN_OWNER_PARENT_CHILD_FIRST_LAST_CLUSTER_BOUNDARY_LAYOUT_PERIOD_"
    "UNIT_SUBTOTAL_TOTAL_STRUCTURE_PROPOSAL_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "EXPORT_AUTHORITY"
)
_NUMBER = re.compile(r"^\(?-?[0-9]+(?:[.,][0-9]+)*\)?$")
_DASH = re.compile(r"^[\-–—]+$")
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "child_order_variants_are_family_level_not_bank_routed": True,
    "complete_pdf_region_enumeration_required": True,
    "document_unit_inheritance_requires_explicit_pdf_text": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_combinations_exhausted_before_triples": True,
    "parent_precedes_descendants_required": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "quality_risk_or_balance_sheet_surface_inside_family_cluster": False,
    "schema_authority": False,
    "text_similarity_alone_can_accept": False,
    "whole_pdf_uniqueness_required": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}


class InterbankDepositsLoansVariantGraphV1Error(ValueError):
    """The interbank-deposit/loan graph input or replay drifted."""


def _error(message: str) -> InterbankDepositsLoansVariantGraphV1Error:
    return InterbankDepositsLoansVariantGraphV1Error(message)


_OWNER_ALIASES = [
    "Tiền gửi và cho vay các TCTD khác",
    "Tiền gửi và vay các TCTD khác",
    "Tiền gửi và cho vay các tổ chức tín dụng khác",
    "Tiền, vàng gửi tại và cho vay các TCTD khác",
    "Tiền, vàng gửi và vay các TCTD khác",
    "Tiền gửi và cấp tín dụng cho các tổ chức tín dụng khác",
]
_GROUP_ALIASES = {
    "DEMAND_DEPOSIT": ["Tiền gửi không kỳ hạn", "Tiền vàng gửi không kỳ hạn"],
    "TERM_DEPOSIT": ["Tiền gửi có kỳ hạn", "Tiền vàng gửi có kỳ hạn"],
    "INTERBANK_LOAN": [
        "Cho vay các TCTD khác",
        "Vay các TCTD khác",
        "Cấp tín dụng cho TCTD khác",
        "Cấp tín dụng cho các tổ chức tín dụng khác",
    ],
}


def _family_spec(*, mode: str, deposit_order: tuple[str, str]) -> dict[str, Any]:
    if mode == "EXPLICIT_DEPOSIT_PARENT":
        branch_core_phrases = ["tiền gửi"]
        branch_variants = [
            {"anchor_phrase": "tại các TCTD khác", "variant_id": "AT_OTHER_CI"},
            {
                "anchor_phrase": "tại các tổ chức tín dụng khác",
                "variant_id": "AT_OTHER_CREDIT_INSTITUTIONS",
            },
        ]
        ordered_roles = (*deposit_order, "INTERBANK_LOAN")
    elif mode == "OWNER_DIRECT_DEMAND":
        branch_core_phrases = ["tiền"]
        branch_variants = [{"anchor_phrase": "không kỳ hạn", "variant_id": "DIRECT_DEMAND"}]
        ordered_roles = (deposit_order[1], "INTERBANK_LOAN")
        if deposit_order != ("DEMAND_DEPOSIT", "TERM_DEPOSIT"):
            raise _error("owner-direct mode supports only demand then term source order")
    else:
        raise _error("interbank family mode drifted")
    return {
        "branch_core_phrases": branch_core_phrases,
        "branch_variants": branch_variants,
        "family_id": FAMILY_ID,
        "format_version": "ACCOUNTING_VARIANT_FAMILY_SPEC_V1",
        "limits": {
            "max_branch_to_last_child_line_span": 55,
            "max_child_gap": 30,
            "min_numeric_followers_per_child": 1,
        },
        "optional_intermediate_aliases": ["Trong đó"],
        "ordered_children": [
            {"aliases": _GROUP_ALIASES[role], "role": role} for role in ordered_roles
        ],
        "owner_aliases": list(_OWNER_ALIASES),
    }


_MODE_SPECS = (
    (
        "EXPLICIT_DEPOSIT_PARENT_DEMAND_THEN_TERM",
        "EXPLICIT_DEPOSIT_PARENT",
        _family_spec(
            mode="EXPLICIT_DEPOSIT_PARENT",
            deposit_order=("DEMAND_DEPOSIT", "TERM_DEPOSIT"),
        ),
    ),
    (
        "EXPLICIT_DEPOSIT_PARENT_TERM_THEN_DEMAND",
        "EXPLICIT_DEPOSIT_PARENT",
        _family_spec(
            mode="EXPLICIT_DEPOSIT_PARENT",
            deposit_order=("TERM_DEPOSIT", "DEMAND_DEPOSIT"),
        ),
    ),
    (
        "OWNER_DIRECT_DEMAND_THEN_TERM",
        "OWNER_DIRECT_DEMAND",
        _family_spec(
            mode="OWNER_DIRECT_DEMAND",
            deposit_order=("DEMAND_DEPOSIT", "TERM_DEPOSIT"),
        ),
    ),
)


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
    if type(value) is not list or not value:
        raise _error("interbank matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("interbank matcher page fields drifted")
        sequence = raw_page["page_sequence"]
        if type(sequence) is not int or sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines = []
        previous_index = -1
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("interbank matcher line fields drifted")
            index = raw_line["source_line_index"]
            if type(index) is not int or index != previous_index + 1:
                raise _error("source line indices must be exact, gap-free and increasing")
            source_text = raw_line["source_text"]
            if source_text is not None and type(source_text) is not str:
                raise _error("source text must be null or one exact string")
            text = raw_line["vietocr_text"]
            if type(text) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "normalized_text": normalize_vietnamese_anchor_v1(text),
                    "source_line_index": index,
                    "source_text": source_text,
                    "vietocr_text": text,
                }
            )
            previous_index = index
        pages.append(
            {
                "lines": lines,
                "page_sequence": sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = sequence
    return pages


def _engine_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _document_unit_context(
    pages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    evidence = []
    for page in pages:
        for line in page["lines"]:
            text = line["normalized_text"]
            if "trinh bay theo don vi trieu" in text or text in {
                "don vi trieu dong",
                "don vi trieu vnd",
            }:
                evidence.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "source_line_index": line["source_line_index"],
                        "vietocr_text": line["vietocr_text"],
                    }
                )
    return evidence


def _token(line: Mapping[str, Any]) -> str:
    return line["vietocr_text"].strip().replace(" ", "")


def _is_money(line: Mapping[str, Any]) -> bool:
    token = _token(line)
    return _NUMBER.fullmatch(token) is not None or _DASH.fullmatch(token) is not None


def _page_width(lines: Sequence[Mapping[str, Any]]) -> int:
    return max((line["bbox"][2] for line in lines), default=1)


def _row_values(
    lines: Sequence[Mapping[str, Any]], label: Mapping[str, Any]
) -> list[dict[str, Any]]:
    center = (label["bbox"][1] + label["bbox"][3]) / 2
    tolerance = max(14.0, (label["bbox"][3] - label["bbox"][1]) * 0.55)
    width = _page_width(lines)
    values = [
        line
        for line in lines
        if line["bbox"][0] > width * 0.47
        and line["bbox"][0] < width * 0.94
        and abs((line["bbox"][1] + line["bbox"][3]) / 2 - center) <= tolerance
        and _is_money(line)
    ]
    return [
        {
            "bbox": list(line["bbox"]),
            "source_line_index": line["source_line_index"],
            "source_text": line["source_text"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in sorted(values, key=lambda item: (item["bbox"][0], item["source_line_index"]))
    ]


def _numeric_rows(
    lines: Sequence[Mapping[str, Any]], *, start_index: int, stop_index: int
) -> list[list[Mapping[str, Any]]]:
    width = _page_width(lines)
    numeric = [
        line
        for line in lines
        if start_index < line["source_line_index"] < stop_index
        and line["bbox"][0] > width * 0.47
        and line["bbox"][0] < width * 0.94
        and _is_money(line)
    ]
    rows: list[list[Mapping[str, Any]]] = []
    for line in sorted(numeric, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        center = (line["bbox"][1] + line["bbox"][3]) / 2
        for row in rows:
            prior = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in row) / len(row)
            if abs(center - prior) <= 14:
                row.append(line)
                break
        else:
            rows.append([line])
    return [sorted(row, key=lambda item: item["bbox"][0]) for row in rows]


def _proposal_axis(row: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bbox": list(item["bbox"]),
            "source_line_index": item["source_line_index"],
            "source_text": item["source_text"],
            "vietocr_text": item["vietocr_text"],
        }
        for item in row
    ]


def _trailing_subtotal(
    lines: Sequence[Mapping[str, Any]], *, after_label: Mapping[str, Any], stop_index: int
) -> list[dict[str, Any]]:
    minimum_y = after_label["bbox"][3] + 3
    rows = _numeric_rows(
        lines,
        start_index=after_label["source_line_index"],
        stop_index=stop_index,
    )
    for row in rows:
        if row[0]["bbox"][1] >= minimum_y:
            return _proposal_axis(row)
    return []


def _axis_groups(
    lines: Sequence[Mapping[str, Any]], start: int, stop: int, *, kind: str
) -> list[dict[str, Any]]:
    width = _page_width(lines)
    candidates = []
    for line in lines:
        index = line["source_line_index"]
        text = line["normalized_text"]
        if not start < index < stop or line["bbox"][0] <= width * 0.45:
            continue
        if kind == "PERIOD":
            matched = (
                re.search(r"(?:30|31)[ /.-](?:03|3|06|6|12)[ /.-]20(?:25|26)", text) is not None
                or "ngay 31 thang" in text
                or text in {"nam 2025", "nam 2026"}
            )
        else:
            matched = "trieu dong" in text or "trieu vnd" in text
        if matched:
            candidates.append(line)
    groups: list[list[Mapping[str, Any]]] = []
    for line in sorted(candidates, key=lambda item: item["bbox"][0]):
        center = (line["bbox"][0] + line["bbox"][2]) / 2
        for group in groups:
            prior = sum((item["bbox"][0] + item["bbox"][2]) / 2 for item in group) / len(group)
            if abs(center - prior) <= max(55, width * 0.055):
                group.append(line)
                break
        else:
            groups.append([line])
    return [
        {
            "bbox_union": [
                min(item["bbox"][0] for item in group),
                min(item["bbox"][1] for item in group),
                max(item["bbox"][2] for item in group),
                max(item["bbox"][3] for item in group),
            ],
            "source_line_indices": [item["source_line_index"] for item in group],
            "vietocr_text": [item["vietocr_text"] for item in group],
        }
        for group in groups
    ]


def _currency_role(text: str, surface: str) -> str | None:
    if (
        "ngoai te" in text
        or "ngoai hoi" in text
        or "vang va ngoai te" in text
        or match_vietnamese_anchor_alias_v1(surface, ["Bằng ngoại tệ", "Bằng ngoại hối"])
    ):
        return "FOREIGN_CURRENCY"
    if (
        "bang vnd" in text
        or "dong viet nam" in text
        or "bang tien dong" in text
        or match_vietnamese_anchor_alias_v1(
            surface, ["Bằng VND", "Bằng đồng Việt Nam", "Bằng tiền đồng"]
        )
    ):
        return "VND"
    return None


def _event(
    role: str,
    kind: str,
    line: Mapping[str, Any] | None,
    values: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "bbox": None if line is None else list(line["bbox"]),
        "role": role,
        "role_kind": kind,
        "source_label_present": line is not None,
        "source_line_index": None if line is None else line["source_line_index"],
        "value_proposals": canonical_clone_v1(list(values)),
        "vietocr_text": None if line is None else line["vietocr_text"],
    }


def _group_events(
    lines: Sequence[Mapping[str, Any]],
    *,
    group_role: str,
    group_line: Mapping[str, Any],
    stop_index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nested_labels = [
        line
        for line in lines
        if group_line["source_line_index"] < line["source_line_index"] < stop_index
        and _currency_role(line["normalized_text"], line["vietocr_text"]) is not None
    ]
    events = [_event(group_role, "GROUP_PARENT", group_line, _row_values(lines, group_line))]
    for line in nested_labels:
        currency = _currency_role(line["normalized_text"], line["vietocr_text"])
        assert currency is not None
        events.append(
            _event(
                f"{group_role}_{currency}",
                "CURRENCY_CHILD",
                line,
                _row_values(lines, line),
            )
        )
    auxiliary = []
    for line in lines:
        if not group_line["source_line_index"] < line["source_line_index"] < stop_index:
            continue
        text = line["normalized_text"]
        if "chiet khau" in text and "tai chiet khau" in text:
            auxiliary.append(
                _event(
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    "NON_ADDITIVE_DETAIL",
                    line,
                    _row_values(lines, line),
                )
            )
        elif "du phong" in text:
            role = (
                "INTERBANK_LOAN_PROVISION"
                if group_role == "INTERBANK_LOAN"
                else "INTERBANK_DEPOSIT_PROVISION"
            )
            auxiliary.append(_event(role, "PROVISION_CHILD", line, _row_values(lines, line)))
    structural_labels = [group_line, *nested_labels]
    structural_labels.extend(
        line
        for line in lines
        if any(event["source_line_index"] == line["source_line_index"] for event in auxiliary)
    )
    last_label = max(structural_labels, key=lambda line: line["source_line_index"])
    parent_values = events[0]["value_proposals"]
    if not parent_values:
        parent_values = _trailing_subtotal(lines, after_label=last_label, stop_index=stop_index)
        events[0]["value_proposals"] = parent_values
        events[0]["value_binding"] = (
            "TRAILING_UNLABELED_PARENT_SUBTOTAL" if parent_values else "NO_VISIBLE_PARENT_VALUE"
        )
    else:
        events[0]["value_binding"] = "INLINE_PARENT_VALUE"
    return events, auxiliary


def _family_total_event(
    lines: Sequence[Mapping[str, Any]],
    *,
    owner_index: int,
    after_index: int,
    stop_index: int,
) -> dict[str, Any] | None:
    explicit = [
        line
        for line in lines
        if owner_index < line["source_line_index"] < stop_index
        and "tong" in line["normalized_text"]
        and "tien gui" in line["normalized_text"]
        and ("cho vay" in line["normalized_text"] or "cap tin dung" in line["normalized_text"])
    ]
    if explicit:
        line = explicit[0]
        values = _row_values(lines, line)
        if values:
            event = _event("FAMILY_TOTAL", "EXPLICIT_TOTAL", line, values)
            event["value_binding"] = "INLINE_EXPLICIT_FAMILY_TOTAL"
            return event
    rows = _numeric_rows(lines, start_index=after_index, stop_index=stop_index)
    if rows:
        event = _event("FAMILY_TOTAL", "UNLABELED_TOTAL", None, _proposal_axis(rows[0]))
        event["source_line_index"] = min(item["source_line_index"] for item in rows[0])
        event["value_binding"] = "TRAILING_UNLABELED_FAMILY_TOTAL"
        return event
    return None


def _minimal_anchor(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    roles = ["PARENT:INTERBANK_DEPOSITS_AND_LOANS"] + [
        f"CHILD:{event['role']}"
        for event in events
        if event["role"] in {"DEMAND_DEPOSIT", "TERM_DEPOSIT", "INTERBANK_LOAN"}
    ]
    pairs = list(itertools.combinations(roles, 2))
    if not pairs:
        raise _error("complete interbank graph has no anchor pair")
    return {
        "combination_size": 2,
        "pair_search_order": "ALL_PARENT_CHILD_PAIRS_THEN_ALL_CHILD_CHILD_PAIRS",
        "selected_roles": list(pairs[0]),
        "tested_pair_count": len(pairs),
        "unique_within_complete_context_regions": True,
    }


def _candidate(
    page: Mapping[str, Any],
    engine_region: Mapping[str, Any],
    *,
    document_unit_context: Sequence[Mapping[str, Any]],
    mode_id: str,
    mode: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    lines = page["lines"]
    by_index = {line["source_line_index"]: line for line in lines}
    owner_record = engine_region.get("owner_context")
    branch_index = engine_region.get("branch_source_line_index")
    child_indices = engine_region.get("child_source_line_indices")
    child_records = engine_region.get("child_match_records")
    if (
        type(owner_record) is not dict
        or owner_record.get("page_sequence") != page["page_sequence"]
        or type(branch_index) is not int
        or type(child_indices) is not list
        or type(child_records) is not list
        or len(child_indices) != len(child_records)
    ):
        return None, {
            "mode_id": mode_id,
            "page_sequence": page["page_sequence"],
            "reasons": ["GENERIC_ENGINE_REGION_SHAPE_OR_OWNER_MODE_UNSUPPORTED"],
        }
    owner_index = owner_record.get("source_line_index")
    if type(owner_index) is not int or any(
        index not in by_index for index in (owner_index, branch_index, *child_indices)
    ):
        raise _error("generic engine/source line binding drifted")
    role_lines: dict[str, Mapping[str, Any]] = {}
    if mode == "EXPLICIT_DEPOSIT_PARENT":
        deposit_parent_line = by_index[branch_index]
    else:
        deposit_parent_line = None
        role_lines["DEMAND_DEPOSIT"] = by_index[branch_index]
    for index, record in zip(child_indices, child_records, strict=True):
        role = record.get("role")
        if role not in _GROUP_ALIASES or role in role_lines:
            raise _error("generic engine interbank child role drifted")
        role_lines[role] = by_index[index]
    if set(role_lines) != {"DEMAND_DEPOSIT", "TERM_DEPOSIT", "INTERBANK_LOAN"}:
        return None, {
            "mode_id": mode_id,
            "page_sequence": page["page_sequence"],
            "reasons": ["REQUIRED_DEPOSIT_OR_LOAN_GROUP_MISSING"],
        }
    ordered_groups = sorted(role_lines.items(), key=lambda item: item[1]["source_line_index"])
    quality_or_next = [
        line["source_line_index"]
        for line in lines
        if line["source_line_index"] > role_lines["INTERBANK_LOAN"]["source_line_index"]
        and (
            "phan tich chat luong" in line["normalized_text"]
            or "chung khoan kinh doanh" in line["normalized_text"]
            or "cong cu tai chinh phai sinh" in line["normalized_text"]
            or "tien gui cua khach hang" in line["normalized_text"]
            or "phat hanh giay to co gia" in line["normalized_text"]
        )
    ]
    cluster_stop = min(quality_or_next, default=len(lines))
    events: list[dict[str, Any]] = []
    group_event_axes: dict[str, list[dict[str, Any]]] = {}
    for ordinal, (role, line) in enumerate(ordered_groups):
        stop = (
            ordered_groups[ordinal + 1][1]["source_line_index"]
            if ordinal + 1 < len(ordered_groups)
            else cluster_stop
        )
        group_events, auxiliary = _group_events(
            lines,
            group_role=role,
            group_line=line,
            stop_index=stop,
        )
        events.extend(group_events)
        events.extend(auxiliary)
        group_event_axes[role] = group_events
    deposit_values: list[dict[str, Any]] = []
    deposit_binding = "NO_EXPLICIT_DEPOSIT_PARENT"
    if deposit_parent_line is not None:
        deposit_values = _row_values(lines, deposit_parent_line)
        deposit_binding = "INLINE_PARENT_VALUE" if deposit_values else "EXPLICIT_PARENT_NO_VALUE"
    if not deposit_values:
        term_last = max(
            (
                event
                for event in events
                if event["source_line_index"] is not None
                and event["source_line_index"] < role_lines["INTERBANK_LOAN"]["source_line_index"]
            ),
            key=lambda event: event["source_line_index"],
        )
        term_last_line = by_index[term_last["source_line_index"]]
        deposit_values = _trailing_subtotal(
            lines,
            after_label=term_last_line,
            stop_index=role_lines["INTERBANK_LOAN"]["source_line_index"],
        )
        if deposit_values:
            deposit_binding = "TRAILING_UNLABELED_DEPOSIT_SUBTOTAL"
    if mode == "OWNER_DIRECT_DEMAND":
        term_parent = group_event_axes["TERM_DEPOSIT"][0]
        if term_parent.get("value_binding") == "TRAILING_UNLABELED_PARENT_SUBTOTAL":
            if not deposit_values:
                deposit_values = canonical_clone_v1(term_parent["value_proposals"])
                deposit_binding = "TRAILING_UNLABELED_DEPOSIT_SUBTOTAL"
            term_parent["value_proposals"] = []
            term_parent["value_binding"] = "NO_VISIBLE_PARENT_VALUE"
        if not deposit_values and all(
            group_event_axes[role][0]["value_proposals"]
            for role in ("DEMAND_DEPOSIT", "TERM_DEPOSIT")
        ):
            deposit_binding = "COMPUTED_ONLY_FROM_VISIBLE_DEMAND_TERM_PARENTS"
    deposit_event = _event(
        "INTERBANK_DEPOSIT_PARENT",
        "INTERMEDIATE_PARENT",
        deposit_parent_line,
        deposit_values,
    )
    deposit_event["value_binding"] = deposit_binding
    events.append(deposit_event)
    events.sort(
        key=lambda event: (
            event["source_line_index"] is None,
            event["source_line_index"] if event["source_line_index"] is not None else 10**9,
        )
    )
    last_structural = max(
        (event for event in events if event["source_line_index"] is not None),
        key=lambda event: event["source_line_index"],
    )
    loan_last_value_index = max(
        [item["source_line_index"] for event in events for item in event["value_proposals"]]
        + [last_structural["source_line_index"]]
    )
    family_total = _family_total_event(
        lines,
        owner_index=owner_index,
        after_index=loan_last_value_index,
        stop_index=cluster_stop,
    )
    if family_total is not None:
        events.append(family_total)
    first_group_index = min(line["source_line_index"] for line in role_lines.values())
    periods = _axis_groups(lines, owner_index, first_group_index, kind="PERIOD")
    units = _axis_groups(lines, owner_index, first_group_index, kind="UNIT")
    effective_units = (
        units
        if units
        else [
            {
                "scope": "DOCUMENT_LEVEL_EXPLICIT_UNIT_DECLARATION",
                **canonical_clone_v1(item),
            }
            for item in document_unit_context
        ]
    )
    event_by_role = {event["role"]: event for event in events}
    reasons = []
    for role in (
        "DEMAND_DEPOSIT_VND",
        "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
        "TERM_DEPOSIT_VND",
        "TERM_DEPOSIT_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_VND",
    ):
        event = event_by_role.get(role)
        if event is None or not event["value_proposals"]:
            reasons.append(f"REQUIRED_ROLE_OR_VALUE_MISSING:{role}")
    for role in ("INTERBANK_DEPOSIT_PARENT", "INTERBANK_LOAN"):
        event = event_by_role.get(role)
        if (
            role == "INTERBANK_DEPOSIT_PARENT"
            and event is not None
            and event.get("value_binding") == "COMPUTED_ONLY_FROM_VISIBLE_DEMAND_TERM_PARENTS"
        ):
            continue
        if event is None or not event["value_proposals"]:
            reasons.append(f"VISIBLE_PARENT_SUBTOTAL_MISSING:{role}")
    if len(periods) < 2:
        reasons.append("FEWER_THAN_TWO_PERIOD_AXES")
    if len(effective_units) < 1:
        reasons.append("NO_MONETARY_UNIT_AXIS")
    near = {
        "mode_id": mode_id,
        "owner_source_line_index": owner_index,
        "page_sequence": page["page_sequence"],
        "reasons": reasons,
        "retained_roles": [event["role"] for event in events],
    }
    if reasons:
        return None, near
    boundary_end = max(
        item["source_line_index"] for event in events for item in event["value_proposals"]
    )
    material = {
        "cluster_boundary": {
            "first_item_role": "INTERBANK_DEPOSITS_AND_LOANS_OWNER",
            "first_page_sequence": page["page_sequence"],
            "first_source_line_index": owner_index,
            "last_item_role": "FAMILY_TOTAL" if family_total is not None else "INTERBANK_LOAN",
            "last_page_sequence": page["page_sequence"],
            "last_source_line_index": boundary_end,
            "selection_rule": (
                "OWNER_THROUGH_DEPOSIT_AND_LOAN_PARENTS_CHILDREN_AND_LAST_VISIBLE_"
                "SUBTOTAL_OR_FAMILY_TOTAL_BEFORE_QUALITY_RISK_OR_NEXT_NOTE_FAMILY"
            ),
        },
        "events": events,
        "generic_engine_binding": {
            "branch_match": canonical_clone_v1(engine_region["branch_match"]),
            "context_complete": engine_region["context_complete"],
            "mode": mode,
            "mode_id": mode_id,
            "owner_context": canonical_clone_v1(owner_record),
        },
        "layout": {
            "family_total_present": family_total is not None,
            "meaningful_axes": {
                "period_axes": periods,
                "period_header_count": len(periods),
                "unit_axes": effective_units,
                "unit_header_count": len(effective_units),
                "unit_scope": ("PAGE_LOCAL" if units else "DOCUMENT_LEVEL_EXPLICIT_INHERITANCE"),
            },
            "orientation": "ROW_LABELS_BY_PERIOD_COLUMNS",
            "presentation_mode": mode,
        },
        "minimal_anchor": _minimal_anchor(events),
        "owner": {
            "bbox": list(by_index[owner_index]["bbox"]),
            "source_line_index": owner_index,
            "vietocr_text": by_index[owner_index]["vietocr_text"],
        },
        "page_sequence": page["page_sequence"],
        "primary_numeric_authority": page["primary_numeric_authority"],
    }
    return {
        **material,
        "region_id": "idlgv1:region:" + canonical_json_sha256_v1(material),
    }, near


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("interbank graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
    ):
        raise _error("interbank graph result identity or authority drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if count == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        )
    )
    expected_uniqueness = {
        "complete_region_count": count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if count == 1
            else ("NO_FULL_MATCH" if count == 0 else "MULTIPLE_FULL_MATCHES")
        ),
    }
    expected_metrics = {
        "complete_interbank_deposit_loan_region_count": count,
        "near_region_count": len(value["near_regions"]),
        "page_count": value["metrics"].get("page_count"),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
        or type(value["metrics"].get("page_count")) is not int
        or value["metrics"]["page_count"] <= 0
    ):
        raise _error("interbank graph status or metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "idlgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("interbank graph result identity drifted")
    return canonical_clone_v1(value)


def build_interbank_deposits_loans_variant_graph_document_v1(
    document_pages: Any,
) -> dict[str, Any]:
    """Enumerate every complete interbank-deposit/loan region in one PDF."""

    pages = _pages(document_pages)
    engine_pages = _engine_pages(pages)
    document_unit_context = _document_unit_context(pages)
    by_page = {page["page_sequence"]: page for page in pages}
    regions_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    near_regions: list[dict[str, Any]] = []
    for mode_id, mode, spec in _MODE_SPECS:
        engine_scan = build_accounting_variant_region_scan_v1(engine_pages, spec)
        for near in engine_scan["near_regions"]:
            near_regions.append(
                {
                    "mode_id": mode_id,
                    "owner_source_line_index": near.get("owner_source_line_index"),
                    "page_sequence": near["page_sequence"],
                    "reasons": canonical_clone_v1(near["unresolved_reasons"]),
                }
            )
        for region in engine_scan["regions"]:
            if region["context_complete"] is not True:
                continue
            wrapped, near = _candidate(
                by_page[region["page_sequence"]],
                region,
                document_unit_context=document_unit_context,
                mode_id=mode_id,
                mode=mode,
            )
            if wrapped is None:
                near_regions.append(near)
                continue
            key = (wrapped["page_sequence"], wrapped["owner"]["source_line_index"])
            regions_by_key.setdefault(key, wrapped)
    regions = sorted(
        regions_by_key.values(),
        key=lambda item: (item["page_sequence"], item["owner"]["source_line_index"]),
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_interbank_deposit_loan_region_count": len(regions),
            "near_region_count": len(near_regions),
            "page_count": len(pages),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else (
                "UNRESOLVED_NO_COMPLETE_REGION"
                if not regions
                else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
            )
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": (
                "UNIQUE_FULL_MATCH"
                if len(regions) == 1
                else ("NO_FULL_MATCH" if not regions else "MULTIPLE_FULL_MATCHES")
            ),
        },
    }
    return _validate_result(
        {**material, "result_id": "idlgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_interbank_deposits_loans_variant_graph_replay_v1(
    value: Any, document_pages: Any
) -> dict[str, Any]:
    """Exact-rebuild one complete-PDF family graph."""

    persisted = _validate_result(value)
    expected = build_interbank_deposits_loans_variant_graph_document_v1(document_pages)
    if not same_typed_json_v1(persisted, expected):
        raise _error("interbank deposit/loan graph does not replay exactly")
    return persisted
