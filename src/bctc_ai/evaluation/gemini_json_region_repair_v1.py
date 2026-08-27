"""Targeted Gemini repair for one immutable financial-page JSON version."""

from __future__ import annotations

import json
from collections.abc import Sequence
from hashlib import sha256
from typing import Any

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (
    normalize_search_text_v1,
    validate_financial_page_json_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_REGION_REPAIR_V1"


class GeminiJsonRegionRepairV1Error(ValueError):
    """One targeted repair is incomplete, ambiguous, or not source-bound."""


def _error(message: str) -> GeminiJsonRegionRepairV1Error:
    return GeminiJsonRegionRepairV1Error(message)


def _target_id(value: Any) -> tuple[int, int, int]:
    if type(value) is not str:
        raise _error("region repair target ID is invalid")
    parts = value.split(":")
    if len(parts) != 3:
        raise _error("region repair target ID is invalid")
    result = []
    for part, prefix in zip(parts, ("s", "t", "r"), strict=True):
        suffix = part.removeprefix(prefix)
        if not suffix.isdigit() or suffix.startswith("0"):
            raise _error("region repair target ID is invalid")
        result.append(int(suffix) - 1)
    return result[0], result[1], result[2]


def region_repair_targets_v1(
    page_json: Any, *, target_ids: Sequence[str], context_radius: int = 1
) -> list[dict[str, Any]]:
    """Resolve exact row targets without scanning unrelated page content downstream."""

    checked = validate_financial_page_json_v1(page_json)
    if (
        type(target_ids) not in {list, tuple}
        or not target_ids
        or len(set(target_ids)) != len(target_ids)
        or type(context_radius) is not int
        or not 1 <= context_radius <= 3
    ):
        raise _error("region repair target frontier is empty or duplicate")
    result = []
    for target_id in target_ids:
        section_index, table_index, row_index = _target_id(target_id)
        try:
            table = checked["sections"][section_index]["tables"][table_index]
            row = table["rows"][row_index]
        except (IndexError, KeyError, TypeError) as exc:
            raise _error("region repair target lies outside the page JSON") from exc
        if type(row["label_exact"]) is not str or not row["label_exact"].strip():
            raise _error("region repair target must bind one labeled row")
        context_rows = []
        for context_index in range(
            max(0, row_index - context_radius),
            min(len(table["rows"]), row_index + context_radius + 1),
        ):
            context = table["rows"][context_index]
            context_rows.append(
                {
                    "hierarchy_path_exact": context["hierarchy_path_exact"],
                    "label_exact": context["label_exact"],
                    "target_id": f"s{section_index + 1}:t{table_index + 1}:r{context_index + 1}",
                }
            )
        result.append(
            {
                "column_headers_exact": [
                    column["header_path_exact"] for column in table["columns"]
                ],
                "context_rows_exact": context_rows,
                "label_exact": row["label_exact"],
                "target_id": target_id,
                "value_count": len(row["values_exact"]),
                "values_before_exact": row["values_exact"],
            }
        )
    return result


def build_region_repair_prompt_v1(
    *, base_page_json_version_id: str, targets: Sequence[dict[str, Any]]
) -> str:
    """Build one concise source-only prompt for selected rows on a full page image."""

    if (
        type(base_page_json_version_id) is not str
        or not base_page_json_version_id.startswith("gfpstorev1:json:")
        or type(targets) not in {list, tuple}
        or not targets
    ):
        raise _error("region repair prompt input is invalid")
    target_material = [
        {
            "column_headers_exact": target["column_headers_exact"],
            "context_rows_exact": target["context_rows_exact"],
            "label_exact": target["label_exact"],
            "target_id": target["target_id"],
            "value_count": target["value_count"],
        }
        for target in targets
    ]
    return (
        "Đọc trực tiếp ảnh trang báo cáo tài chính. Chỉ chép lại các dòng mục tiêu trong "
        "target_rows bên dưới; không trả nội dung khác. context_rows_exact là các dòng trước/sau "
        "để định vị đúng block và hiểu header/cha-con, không phải đáp án để sao chép. Giữ đúng, "
        "đủ nhãn và từng giá trị theo "
        "thứ tự cột. Không dùng tổng để suy ra hoặc sửa số. Ô trống trả null; dấu gạch ngang có "
        "thể trả '-' hoặc '0'. Mỗi target_id phải xuất hiện đúng một lần. Nếu không đọc chắc một "
        "ô, vẫn giữ target nhưng ghi null và mô tả ngắn trong uncertainty_exact. Trả đúng JSON "
        "theo schema.\nbase_page_json_version_id="
        + base_page_json_version_id
        + "\ntarget_rows="
        + canonical_json_bytes_v1(target_material).decode("utf-8")
    )


def region_repair_response_schema_v1() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "all_targets_transcribed": {"type": "boolean"},
            "rows": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "label_exact": {"type": "string"},
                        "target_id": {"type": "string"},
                        "values_exact": {
                            "items": {"type": ["string", "null"]},
                            "type": "array",
                        },
                    },
                    "required": ["label_exact", "target_id", "values_exact"],
                    "type": "object",
                },
                "type": "array",
            },
            "uncertainty_exact": {"items": {"type": "string"}, "type": "array"},
        },
        "required": ["all_targets_transcribed", "rows", "uncertainty_exact"],
        "type": "object",
    }


def decode_region_repair_text_v1(text: str, *, targets: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Validate a model response against the exact requested row frontier."""

    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _error("region repair response is not JSON") from exc
    if type(value) is not dict or set(value) != {
        "all_targets_transcribed",
        "rows",
        "uncertainty_exact",
    }:
        raise _error("region repair response fields drifted")
    if type(value["all_targets_transcribed"]) is not bool:
        raise _error("region repair completion flag is invalid")
    if type(value["uncertainty_exact"]) is not list or any(
        type(item) is not str or not item for item in value["uncertainty_exact"]
    ):
        raise _error("region repair uncertainty frontier is invalid")
    rows = value["rows"]
    if type(rows) is not list or any(
        type(row) is not dict or set(row) != {"label_exact", "target_id", "values_exact"}
        for row in rows
    ):
        raise _error("region repair row frontier is invalid")
    targets_by_id = {target["target_id"]: target for target in targets}
    if len(targets_by_id) != len(targets) or [row.get("target_id") for row in rows] != list(
        targets_by_id
    ):
        raise _error("region repair row order or identity drifted")
    checked_rows = []
    for row in rows:
        target = targets_by_id[row["target_id"]]
        values = row["values_exact"]
        if (
            type(row["label_exact"]) is not str
            or type(values) is not list
            or len(values) != target["value_count"]
            or any(type(item) not in {str, type(None)} for item in values)
        ):
            raise _error("region repair label or value axis is invalid")
        expected_label = normalize_search_text_v1(target["label_exact"])["text_ascii_folded"]
        observed_label = normalize_search_text_v1(row["label_exact"])["text_ascii_folded"]
        if expected_label != observed_label:
            raise _error("region repair label does not bind the requested row")
        checked_rows.append(canonical_clone_v1(row))
    return {
        "all_targets_transcribed": value["all_targets_transcribed"],
        "rows": checked_rows,
        "uncertainty_exact": list(value["uncertainty_exact"]),
    }


def merge_region_repair_v1(
    page_json: Any,
    *,
    base_page_json_version_id: str,
    targets: Sequence[dict[str, Any]],
    repair: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create one immutable effective page version by changing only target values."""

    checked = validate_financial_page_json_v1(page_json)
    decoded = decode_region_repair_text_v1(
        canonical_json_bytes_v1(repair).decode("utf-8"), targets=targets
    )
    if not decoded["all_targets_transcribed"] or decoded["uncertainty_exact"]:
        raise _error("region repair is incomplete or uncertain")
    merged = canonical_clone_v1(checked)
    before_sha = canonical_json_sha256_v1(checked)
    changes = []
    for target, row in zip(targets, decoded["rows"], strict=True):
        section_index, table_index, row_index = _target_id(target["target_id"])
        destination = merged["sections"][section_index]["tables"][table_index]["rows"][row_index]
        before = canonical_clone_v1(destination["values_exact"])
        destination["values_exact"] = canonical_clone_v1(row["values_exact"])
        changes.append(
            {
                "target_id": target["target_id"],
                "values_after_exact": row["values_exact"],
                "values_before_exact": before,
            }
        )
    merged = validate_financial_page_json_v1(merged)
    receipt_material = {
        "base_page_json_sha256": before_sha,
        "base_page_json_version_id": base_page_json_version_id,
        "changes": changes,
        "format_version": FORMAT_VERSION,
        "merged_page_json_sha256": canonical_json_sha256_v1(merged),
        "repair_response_sha256": canonical_json_sha256_v1(decoded),
    }
    return merged, {
        **receipt_material,
        "repair_id": "gjfrrv1:repair:" + canonical_json_sha256_v1(receipt_material),
    }


def repair_prompt_sha256_v1(prompt: str) -> str:
    return sha256(prompt.encode("utf-8")).hexdigest()
