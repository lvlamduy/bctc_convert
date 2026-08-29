"""Targeted Gemini repair for one immutable financial-page JSON version."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
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
TABLE_POPULATION_PROJECTION_FORMAT_VERSION = "GEMINI_JSON_WHOLE_PAGE_TABLE_POPULATION_PROJECTION_V1"


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
    page_json: Any,
    *,
    target_ids: Sequence[str],
    context_radius: int = 1,
    allow_label_change: bool = False,
) -> list[dict[str, Any]]:
    """Resolve exact row targets without scanning unrelated page content downstream."""

    checked = validate_financial_page_json_v1(page_json)
    if (
        type(target_ids) not in {list, tuple}
        or not target_ids
        or len(set(target_ids)) != len(target_ids)
        or type(context_radius) is not int
        or not 1 <= context_radius <= 3
        or type(allow_label_change) is not bool
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
        if row["label_exact"] is not None and (
            type(row["label_exact"]) is not str or not row["label_exact"].strip()
        ):
            raise _error("region repair target label is invalid")
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
                **({"allow_label_change": True} if allow_label_change else {}),
            }
        )
    return result


def table_axis_repair_targets_v1(
    page_json: Any, *, table_refs: Sequence[dict[str, str]]
) -> list[dict[str, Any]]:
    """Resolve exact tables whose printed period/header axis needs rereading."""

    checked = validate_financial_page_json_v1(page_json)
    if (
        type(table_refs) not in {list, tuple}
        or not table_refs
        or any(
            type(ref) is not dict or set(ref) != {"section_id", "table_id"} for ref in table_refs
        )
    ):
        raise _error("table-axis repair frontier is invalid")
    result = []
    seen = set()
    for ref in table_refs:
        target_id = f"{ref['section_id']}:{ref['table_id']}"
        if target_id in seen:
            raise _error("table-axis repair frontier is duplicate")
        seen.add(target_id)
        section_index = int(ref["section_id"].removeprefix("s")) - 1
        table_index = int(ref["table_id"].removeprefix("t")) - 1
        try:
            section = checked["sections"][section_index]
            table = section["tables"][table_index]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("table-axis repair target lies outside the page JSON") from exc
        if ref["section_id"] != f"s{section_index + 1}" or ref["table_id"] != f"t{table_index + 1}":
            raise _error("table-axis repair target ID is invalid")
        labels = [row["label_exact"] for row in table["rows"] if row["label_exact"] is not None]
        result.append(
            {
                "columns_before_exact": [
                    canonical_clone_v1(column["header_path_exact"]) for column in table["columns"]
                ],
                "row_labels_context_exact": labels[:3] + labels[-2:] if len(labels) > 5 else labels,
                "section_title_exact": section["title_exact"],
                "table_title_before_exact": table["title_exact"],
                "target_id": target_id,
            }
        )
    return result


def structural_context_repair_targets_v1(
    page_json: Any, *, table_refs: Sequence[dict[str, str]]
) -> list[dict[str, Any]]:
    """Resolve exact candidate-local title and narrative surfaces for rereading."""

    checked = validate_financial_page_json_v1(page_json)
    if (
        type(table_refs) not in {list, tuple}
        or not table_refs
        or any(
            type(ref) is not dict or set(ref) != {"section_id", "table_id"} for ref in table_refs
        )
    ):
        raise _error("structural-context repair frontier is invalid")
    result = []
    seen = set()
    for ref in table_refs:
        target_id = f"{ref['section_id']}:{ref['table_id']}"
        if target_id in seen:
            raise _error("structural-context repair frontier is duplicate")
        seen.add(target_id)
        try:
            section_index = int(ref["section_id"].removeprefix("s")) - 1
            table_index = int(ref["table_id"].removeprefix("t")) - 1
            section = checked["sections"][section_index]
            table = section["tables"][table_index]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("structural-context repair target lies outside page JSON") from exc
        if ref["section_id"] != f"s{section_index + 1}" or ref["table_id"] != f"t{table_index + 1}":
            raise _error("structural-context repair target ID is invalid")
        labels = [row["label_exact"] for row in table["rows"] if row["label_exact"]]
        result.append(
            {
                "narratives_before_exact": canonical_clone_v1(section["narratives_exact"]),
                "row_labels_context_exact": labels[:3] + labels[-2:] if len(labels) > 5 else labels,
                "section_title_before_exact": section["title_exact"],
                "table_title_before_exact": table["title_exact"],
                "target_id": target_id,
            }
        )
    return result


def build_structural_context_repair_prompt_v1(
    *, base_page_json_version_id: str, targets: Sequence[dict[str, Any]]
) -> str:
    if (
        type(base_page_json_version_id) is not str
        or not base_page_json_version_id.startswith("gfpstorev1:json:")
        or type(targets) not in {list, tuple}
        or not targets
    ):
        raise _error("structural-context repair prompt input is invalid")
    return (
        "Đọc trực tiếp ảnh nguyên trang báo cáo tài chính. Với mỗi target_table, chép lại "
        "đồng thời và đầy đủ đúng ba trục cấu trúc dùng để xác định ngữ cảnh bảng: "
        "section_title_exact, table_title_exact và toàn bộ narratives_exact của section theo "
        "thứ tự xuất hiện. Không chép lại các ô số hoặc tự suy luận tiêu đề từ nhãn dòng. "
        "Các giá trị *_before_exact và row_labels_context_exact chỉ để định vị, không phải "
        "đáp án. Giữ nguyên chính tả, dấu câu, số thứ tự và ký hiệu chú thích. Nếu một tiêu "
        "đề thực sự không có thì trả null; nếu section không có narrative thì trả mảng rỗng. "
        "Nếu không đọc chắc bất kỳ trục nào thì ghi uncertainty_exact. Mỗi target_id đúng một "
        "lần. Trả đúng JSON theo schema.\nbase_page_json_version_id="
        + base_page_json_version_id
        + "\ntarget_tables="
        + canonical_json_bytes_v1(list(targets)).decode("utf-8")
    )


def structural_context_repair_response_schema_v1() -> dict[str, Any]:
    nullable_string = {"type": ["string", "null"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "all_targets_transcribed": {"type": "boolean"},
            "targets": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "narratives_exact": {"items": {"type": "string"}, "type": "array"},
                        "section_title_exact": nullable_string,
                        "table_title_exact": nullable_string,
                        "target_id": {"type": "string"},
                    },
                    "required": [
                        "narratives_exact",
                        "section_title_exact",
                        "table_title_exact",
                        "target_id",
                    ],
                    "type": "object",
                },
                "type": "array",
            },
            "uncertainty_exact": {"items": {"type": "string"}, "type": "array"},
        },
        "required": ["all_targets_transcribed", "targets", "uncertainty_exact"],
        "type": "object",
    }


def decode_structural_context_repair_text_v1(
    text: str, *, targets: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _error("structural-context repair response is not JSON") from exc
    if type(value) is not dict or set(value) != {
        "all_targets_transcribed",
        "targets",
        "uncertainty_exact",
    }:
        raise _error("structural-context repair response fields drifted")
    expected_ids = [target["target_id"] for target in targets]
    repaired = value["targets"]
    if (
        type(value["all_targets_transcribed"]) is not bool
        or type(value["uncertainty_exact"]) is not list
        or any(type(item) is not str or not item for item in value["uncertainty_exact"])
        or type(repaired) is not list
        or [item.get("target_id") for item in repaired] != expected_ids
    ):
        raise _error("structural-context repair completion or identity is invalid")
    for item in repaired:
        if (
            type(item) is not dict
            or set(item)
            != {
                "narratives_exact",
                "section_title_exact",
                "table_title_exact",
                "target_id",
            }
            or type(item["section_title_exact"]) not in {str, type(None)}
            or type(item["table_title_exact"]) not in {str, type(None)}
            or type(item["narratives_exact"]) is not list
            or any(
                type(narrative) is not str or not narrative.strip()
                for narrative in item["narratives_exact"]
            )
        ):
            raise _error("structural-context repair target is invalid")
    return canonical_clone_v1(value)


def merge_structural_context_repair_v1(
    page_json: Any,
    *,
    base_page_json_version_id: str,
    targets: Sequence[dict[str, Any]],
    repair: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    checked = validate_financial_page_json_v1(page_json)
    decoded = decode_structural_context_repair_text_v1(
        canonical_json_bytes_v1(repair).decode("utf-8"), targets=targets
    )
    if not decoded["all_targets_transcribed"] or decoded["uncertainty_exact"]:
        raise _error("structural-context repair is incomplete or uncertain")
    merged = canonical_clone_v1(checked)
    before_sha = canonical_json_sha256_v1(checked)
    changes = []
    for target, repaired in zip(targets, decoded["targets"], strict=True):
        section_id, table_id = target["target_id"].split(":")
        section = merged["sections"][int(section_id[1:]) - 1]
        table = section["tables"][int(table_id[1:]) - 1]
        before = {
            "narratives_exact": canonical_clone_v1(section["narratives_exact"]),
            "section_title_exact": section["title_exact"],
            "table_title_exact": table["title_exact"],
        }
        section["title_exact"] = repaired["section_title_exact"]
        section["narratives_exact"] = canonical_clone_v1(repaired["narratives_exact"])
        table["title_exact"] = repaired["table_title_exact"]
        changes.append(
            {
                "axis_after_exact": {
                    "narratives_exact": repaired["narratives_exact"],
                    "section_title_exact": repaired["section_title_exact"],
                    "table_title_exact": repaired["table_title_exact"],
                },
                "axis_before_exact": before,
                "target_id": target["target_id"],
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


def build_table_axis_repair_prompt_v1(
    *, base_page_json_version_id: str, targets: Sequence[dict[str, Any]]
) -> str:
    if (
        type(base_page_json_version_id) is not str
        or not base_page_json_version_id.startswith("gfpstorev1:json:")
        or type(targets) not in {list, tuple}
        or not targets
    ):
        raise _error("table-axis repair prompt input is invalid")
    return (
        "Đọc trực tiếp ảnh nguyên trang báo cáo tài chính. Chỉ chép lại tiêu đề bảng và "
        "header cột của từng target_table; không chép lại các dòng số. Phải giữ đầy đủ mọi "
        "ngày/kỳ, đơn vị và nhãn cột nhìn thấy, đúng thứ tự từ header ngoài đến header trong. "
        "Một tiêu đề tiểu mục có đánh số (ví dụ '10.4 Phân tích ...') nằm ngay phía trên "
        "header cột chính là table_title_exact; không trả null chỉ vì đó là tiêu đề tiểu mục. "
        "section_title_exact, header cũ và row_labels_context_exact chỉ giúp định vị đúng bảng, "
        "không phải đáp án. Không suy ra ngày từ tên file hay phép tính. Mỗi target_id xuất hiện "
        "đúng một lần và số cột phải giữ nguyên. Nếu một tiêu đề bảng thực sự không có thì trả "
        "null; nếu không đọc chắc thì ghi uncertainty_exact. Trả đúng JSON theo schema.\n"
        "base_page_json_version_id="
        + base_page_json_version_id
        + "\ntarget_tables="
        + canonical_json_bytes_v1(list(targets)).decode("utf-8")
    )


def table_axis_repair_response_schema_v1() -> dict[str, Any]:
    nullable_string = {"type": ["string", "null"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "all_targets_transcribed": {"type": "boolean"},
            "tables": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "columns_header_path_exact": {
                            "items": {
                                "items": nullable_string,
                                "minItems": 1,
                                "type": "array",
                            },
                            "type": "array",
                        },
                        "table_title_exact": nullable_string,
                        "target_id": {"type": "string"},
                    },
                    "required": [
                        "columns_header_path_exact",
                        "table_title_exact",
                        "target_id",
                    ],
                    "type": "object",
                },
                "type": "array",
            },
            "uncertainty_exact": {"items": {"type": "string"}, "type": "array"},
        },
        "required": ["all_targets_transcribed", "tables", "uncertainty_exact"],
        "type": "object",
    }


def decode_table_axis_repair_text_v1(
    text: str, *, targets: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _error("table-axis repair response is not JSON") from exc
    if type(value) is not dict or set(value) != {
        "all_targets_transcribed",
        "tables",
        "uncertainty_exact",
    }:
        raise _error("table-axis repair response fields drifted")
    if (
        type(value["all_targets_transcribed"]) is not bool
        or type(value["uncertainty_exact"]) is not list
    ):
        raise _error("table-axis repair completion evidence is invalid")
    if any(type(item) is not str or not item for item in value["uncertainty_exact"]):
        raise _error("table-axis repair uncertainty frontier is invalid")
    tables = value["tables"]
    expected_ids = [target["target_id"] for target in targets]
    if type(tables) is not list or [table.get("target_id") for table in tables] != expected_ids:
        raise _error("table-axis repair order or identity drifted")
    checked_tables = []
    for table, target in zip(tables, targets, strict=True):
        if type(table) is not dict or set(table) != {
            "columns_header_path_exact",
            "table_title_exact",
            "target_id",
        }:
            raise _error("table-axis repair table fields drifted")
        columns = table["columns_header_path_exact"]
        if (
            type(table["table_title_exact"]) not in {str, type(None)}
            or type(columns) is not list
            or len(columns) != len(target["columns_before_exact"])
            or any(
                type(path) is not list
                or not path
                or any(type(item) not in {str, type(None)} for item in path)
                for path in columns
            )
        ):
            raise _error("table-axis repair title or column axis is invalid")
        checked_tables.append(canonical_clone_v1(table))
    return {
        "all_targets_transcribed": value["all_targets_transcribed"],
        "tables": checked_tables,
        "uncertainty_exact": list(value["uncertainty_exact"]),
    }


def merge_table_axis_repair_v1(
    page_json: Any,
    *,
    base_page_json_version_id: str,
    targets: Sequence[dict[str, Any]],
    repair: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    checked = validate_financial_page_json_v1(page_json)
    decoded = decode_table_axis_repair_text_v1(
        canonical_json_bytes_v1(repair).decode("utf-8"), targets=targets
    )
    if not decoded["all_targets_transcribed"] or decoded["uncertainty_exact"]:
        raise _error("table-axis repair is incomplete or uncertain")
    merged = canonical_clone_v1(checked)
    before_sha = canonical_json_sha256_v1(checked)
    changes = []
    for target, table_repair in zip(targets, decoded["tables"], strict=True):
        section_id, table_id = target["target_id"].split(":")
        table = merged["sections"][int(section_id[1:]) - 1]["tables"][int(table_id[1:]) - 1]
        before = {
            "columns_header_path_exact": [
                canonical_clone_v1(column["header_path_exact"]) for column in table["columns"]
            ],
            "table_title_exact": table["title_exact"],
        }
        table["title_exact"] = table_repair["table_title_exact"]
        for column, header in zip(
            table["columns"], table_repair["columns_header_path_exact"], strict=True
        ):
            column["header_path_exact"] = canonical_clone_v1(header)
        changes.append(
            {
                "axis_after_exact": {
                    "columns_header_path_exact": table_repair["columns_header_path_exact"],
                    "table_title_exact": table_repair["table_title_exact"],
                },
                "axis_before_exact": before,
                "target_id": target["target_id"],
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


def section_narrative_repair_targets_v1(
    page_json: Any, *, table_refs: Sequence[dict[str, str]]
) -> list[dict[str, Any]]:
    """Resolve exact sections whose narrative/footnote axis needs rereading."""

    checked = validate_financial_page_json_v1(page_json)
    if (
        type(table_refs) not in {list, tuple}
        or not table_refs
        or any(
            type(ref) is not dict or set(ref) != {"section_id", "table_id"} for ref in table_refs
        )
    ):
        raise _error("section-narrative repair frontier is invalid")
    result = []
    seen_sections = set()
    for ref in table_refs:
        section_index = int(ref["section_id"].removeprefix("s")) - 1
        table_index = int(ref["table_id"].removeprefix("t")) - 1
        try:
            section = checked["sections"][section_index]
            table = section["tables"][table_index]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("section-narrative repair target lies outside the page JSON") from exc
        if (
            ref["section_id"] != f"s{section_index + 1}"
            or ref["table_id"] != f"t{table_index + 1}"
            or ref["section_id"] in seen_sections
        ):
            raise _error("section-narrative repair target ID is invalid or duplicate")
        seen_sections.add(ref["section_id"])
        labels = [row["label_exact"] for row in table["rows"] if row["label_exact"] is not None]
        result.append(
            {
                "column_headers_exact": [
                    canonical_clone_v1(column["header_path_exact"]) for column in table["columns"]
                ],
                "narratives_before_exact": canonical_clone_v1(section["narratives_exact"]),
                "row_labels_context_exact": labels[:3] + labels[-2:] if len(labels) > 5 else labels,
                "section_title_exact": section["title_exact"],
                "table_title_exact": table["title_exact"],
                "target_id": ref["section_id"],
            }
        )
    return result


def build_section_narrative_repair_prompt_v1(
    *, base_page_json_version_id: str, targets: Sequence[dict[str, Any]]
) -> str:
    """Build one bounded prompt for the complete visible narrative axis of a section."""

    if (
        type(base_page_json_version_id) is not str
        or not base_page_json_version_id.startswith("gfpstorev1:json:")
        or type(targets) not in {list, tuple}
        or not targets
    ):
        raise _error("section-narrative repair prompt input is invalid")
    return (
        "Đọc trực tiếp ảnh nguyên trang báo cáo tài chính. Với mỗi target_section, chép nguyên "
        "văn và đầy đủ tất cả đoạn thuyết minh/chú thích thuộc section đó nhưng nằm ngoài các "
        "ô của bảng, đặc biệt đoạn có dấu chú thích như (*), (**). Không chép lại dòng hoặc số "
        "trong bảng. Giữ nguyên chính tả, dấu câu, ngày, đơn vị và mọi con số; mỗi đoạn là một "
        "phần tử narratives_exact theo thứ tự xuất hiện. table_title_exact, header và nhãn dòng "
        "chỉ giúp định vị section, không phải đáp án. narratives_before_exact có thể thiếu hoặc "
        "sai và chỉ là evidence cũ. Nếu section thực sự không có đoạn ngoài bảng thì trả mảng "
        "rỗng. Nếu không đọc chắc thì ghi uncertainty_exact. Mỗi target_id xuất hiện đúng một "
        "lần. Trả đúng JSON theo schema.\nbase_page_json_version_id="
        + base_page_json_version_id
        + "\ntarget_sections="
        + canonical_json_bytes_v1(list(targets)).decode("utf-8")
    )


def section_narrative_repair_response_schema_v1() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "all_targets_transcribed": {"type": "boolean"},
            "sections": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "narratives_exact": {"items": {"type": "string"}, "type": "array"},
                        "target_id": {"type": "string"},
                    },
                    "required": ["narratives_exact", "target_id"],
                    "type": "object",
                },
                "type": "array",
            },
            "uncertainty_exact": {"items": {"type": "string"}, "type": "array"},
        },
        "required": ["all_targets_transcribed", "sections", "uncertainty_exact"],
        "type": "object",
    }


def decode_section_narrative_repair_text_v1(
    text: str, *, targets: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _error("section-narrative repair response is not JSON") from exc
    if type(value) is not dict or set(value) != {
        "all_targets_transcribed",
        "sections",
        "uncertainty_exact",
    }:
        raise _error("section-narrative repair response fields drifted")
    expected_ids = [target["target_id"] for target in targets]
    sections = value["sections"]
    if (
        type(value["all_targets_transcribed"]) is not bool
        or type(value["uncertainty_exact"]) is not list
        or any(type(item) is not str or not item for item in value["uncertainty_exact"])
        or type(sections) is not list
        or [section.get("target_id") for section in sections] != expected_ids
    ):
        raise _error("section-narrative repair completion or identity is invalid")
    checked_sections = []
    for section in sections:
        if type(section) is not dict or set(section) != {"narratives_exact", "target_id"}:
            raise _error("section-narrative repair section fields drifted")
        narratives = section["narratives_exact"]
        if type(narratives) is not list or any(
            type(narrative) is not str or not narrative.strip() for narrative in narratives
        ):
            raise _error("section-narrative repair narrative axis is invalid")
        checked_sections.append(canonical_clone_v1(section))
    return {
        "all_targets_transcribed": value["all_targets_transcribed"],
        "sections": checked_sections,
        "uncertainty_exact": list(value["uncertainty_exact"]),
    }


def merge_section_narrative_repair_v1(
    page_json: Any,
    *,
    base_page_json_version_id: str,
    targets: Sequence[dict[str, Any]],
    repair: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    checked = validate_financial_page_json_v1(page_json)
    decoded = decode_section_narrative_repair_text_v1(
        canonical_json_bytes_v1(repair).decode("utf-8"), targets=targets
    )
    if not decoded["all_targets_transcribed"] or decoded["uncertainty_exact"]:
        raise _error("section-narrative repair is incomplete or uncertain")
    merged = canonical_clone_v1(checked)
    before_sha = canonical_json_sha256_v1(checked)
    changes = []
    for target, section_repair in zip(targets, decoded["sections"], strict=True):
        section_id = target["target_id"]
        section = merged["sections"][int(section_id[1:]) - 1]
        before = canonical_clone_v1(section["narratives_exact"])
        section["narratives_exact"] = canonical_clone_v1(section_repair["narratives_exact"])
        changes.append(
            {
                "narratives_after_exact": section_repair["narratives_exact"],
                "narratives_before_exact": before,
                "target_id": section_id,
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
            **(
                {"label_change_policy": "REREAD_FULL_EXACT_SOURCE_LABEL"}
                if target.get("allow_label_change") is True
                else {}
            ),
        }
        for target in targets
    ]
    return (
        "Đọc trực tiếp ảnh trang báo cáo tài chính. Chỉ chép lại các dòng mục tiêu trong "
        "target_rows bên dưới; không trả nội dung khác. context_rows_exact là các dòng trước/sau "
        "để định vị đúng block và hiểu header/cha-con, không phải đáp án để sao chép. Giữ đúng, "
        "đủ nhãn và từng giá trị theo "
        "thứ tự cột. Kiểm tra kỹ dấu âm, ngoặc đơn hoặc dấu gạch có thể nằm lệch về "
        "bên trái/phải của con số nhưng vẫn thuộc cùng ô; phải chép cả dấu và số. "
        "Nếu target có label_change_policy, phải đọc lại toàn bộ nhãn từ ảnh, gồm cả phần "
        "quấn sang dòng kế tiếp; label_exact cũ chỉ là gợi ý định vị và có thể bị cắt. "
        "Nếu không có policy này thì giữ nguyên nhãn. Header và các dòng lân cận chỉ dùng "
        "để gán đúng cột. Không dùng tổng để suy ra "
        "hoặc sửa số, và không dùng phép tính để đoán nội dung ô. Ô trống trả null; dấu gạch ngang độc lập có "
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
                        "label_exact": {"type": ["string", "null"]},
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
            type(row["label_exact"]) not in {str, type(None)}
            or type(values) is not list
            or len(values) != target["value_count"]
            or any(type(item) not in {str, type(None)} for item in values)
        ):
            raise _error("region repair label or value axis is invalid")
        expected_label = target["label_exact"]
        observed_label = row["label_exact"]
        if (expected_label is None) != (observed_label is None):
            raise _error("region repair label does not bind the requested row")
        if (
            not target.get("allow_label_change", False)
            and expected_label is not None
            and (
                normalize_search_text_v1(expected_label)["text_ascii_folded"]
                != normalize_search_text_v1(observed_label)["text_ascii_folded"]
            )
        ):
            raise _error("region repair label does not bind the requested row")
        if target.get("allow_label_change", False) and (
            type(observed_label) is not str or not observed_label.strip()
        ):
            raise _error("region repair source label reread is empty")
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
        label_before = destination["label_exact"]
        destination["values_exact"] = canonical_clone_v1(row["values_exact"])
        label_change = target.get("allow_label_change", False)
        path_before = canonical_clone_v1(destination["hierarchy_path_exact"])
        if label_change:
            if not path_before or path_before[-1] != label_before:
                raise _error("region repair source label is not the hierarchy leaf")
            destination["label_exact"] = row["label_exact"]
            destination["hierarchy_path_exact"][-1] = row["label_exact"]
        changes.append(
            {
                "target_id": target["target_id"],
                "values_after_exact": row["values_exact"],
                "values_before_exact": before,
                **(
                    {
                        "hierarchy_path_after_exact": destination["hierarchy_path_exact"],
                        "hierarchy_path_before_exact": path_before,
                        "label_after_exact": row["label_exact"],
                        "label_before_exact": label_before,
                    }
                    if label_change
                    else {}
                ),
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


def _normalized_surface(value: Any) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value.strip():
        raise _error("table-population projection surface is invalid")
    normalized = normalize_search_text_v1(value)["text_search_normalized"]
    if type(normalized) is not str or not normalized:
        raise _error("table-population projection surface has no normalized identity")
    return normalized


def _normalized_path(value: Any) -> tuple[str | None, ...]:
    if type(value) is not list or not value:
        raise _error("table-population projection path is invalid")
    return tuple(_normalized_surface(item) for item in value)


def _column_axis(table: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    result = []
    for column in table["columns"]:
        header = " ".join(item for item in column["header_path_exact"] if item is not None)
        normalized = _normalized_surface(header)
        if normalized is None:
            raise _error("table-population projection column header is absent")
        result.append((column["value_kind"], normalized))
    return tuple(result)


def _row_anchor(row: Mapping[str, Any]) -> tuple[str, tuple[str | None, ...]]:
    label = _normalized_surface(row["label_exact"])
    hierarchy = _normalized_path(row["hierarchy_path_exact"])
    if label is None:
        visible_hierarchy = tuple(item for item in hierarchy if item is not None)
        if not visible_hierarchy:
            raise _error("base table row has no stable textual anchor")
        label = visible_hierarchy[-1]
    return label, hierarchy


def _table_ref(value: Any, *, field: str) -> tuple[int, int, dict[str, str]]:
    if type(value) is not dict or set(value) != {"section_id", "table_id"}:
        raise _error(f"{field} table reference is invalid")
    section = value["section_id"]
    table = value["table_id"]
    if (
        type(section) is not str
        or type(table) is not str
        or not section.startswith("s")
        or not table.startswith("t")
        or not section[1:].isdigit()
        or not table[1:].isdigit()
        or section[1:].startswith("0")
        or table[1:].startswith("0")
    ):
        raise _error(f"{field} table reference is invalid")
    return int(section[1:]) - 1, int(table[1:]) - 1, dict(value)


def project_whole_page_table_population_v1(
    base_page_json: Any,
    retry_page_json: Any,
    *,
    base_page_json_version_id: str,
    retry_page_json_version_id: str,
    target_table_ref: Mapping[str, str],
    required_changed_target_ids: Sequence[str],
    require_added_rows: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project one uniquely anchored table population from a standard page retry.

    The retry is still the ordinary whole-page reader response.  This local
    projection never selects the retry page wholesale: it keeps every base
    section/table/header byte and replaces only one row population after the
    column, period, unit, title and ordered row-anchor axes match uniquely.
    Existing non-target rows must be semantically unchanged.  Added rows are
    source observations, not inferred values; the consuming family evaluator
    remains responsible for exhaustive role inventory and exact equations.
    """

    base = validate_financial_page_json_v1(base_page_json)
    retry = validate_financial_page_json_v1(retry_page_json)
    if (
        type(base_page_json_version_id) is not str
        or not base_page_json_version_id.startswith("gfpstorev1:json:")
        or type(retry_page_json_version_id) is not str
        or not retry_page_json_version_id.startswith("gfpstorev1:json:")
        or base_page_json_version_id == retry_page_json_version_id
        or type(required_changed_target_ids) not in {list, tuple}
        or not required_changed_target_ids
        or len(set(required_changed_target_ids)) != len(required_changed_target_ids)
        or type(require_added_rows) is not bool
    ):
        raise _error("table-population projection authority is invalid")
    section_index, table_index, checked_target_ref = _table_ref(target_table_ref, field="base")
    try:
        base_section = base["sections"][section_index]
        base_table = base_section["tables"][table_index]
    except (IndexError, KeyError, TypeError) as exc:
        raise _error("table-population base target lies outside the page") from exc
    if checked_target_ref != {
        "section_id": f"s{section_index + 1}",
        "table_id": f"t{table_index + 1}",
    }:
        raise _error("table-population base target identity drifted")

    required_targets = list(required_changed_target_ids)
    required_row_indexes = []
    for target_id in required_targets:
        target_section, target_table, target_row = _target_id(target_id)
        if (target_section, target_table) != (section_index, table_index):
            raise _error("changed row target is outside the selected base table")
        if not 0 <= target_row < len(base_table["rows"]):
            raise _error("changed row target lies outside the base row population")
        required_row_indexes.append(target_row)

    base_anchors = [_row_anchor(row) for row in base_table["rows"]]
    if len(set(base_anchors)) != len(base_anchors):
        raise _error("base table row anchors are duplicate")
    base_context = _normalized_surface(base_table["title_exact"])
    if base_context is None:
        base_context = _normalized_surface(base_section["title_exact"])
    if base_context is None:
        raise _error("base table has no explicit title context")
    base_column_axis = _column_axis(base_table)
    base_unit = _normalized_surface(base_table["unit_exact"])

    matches: list[tuple[int, int, dict[str, Any]]] = []
    for retry_section_index, retry_section in enumerate(retry["sections"]):
        for retry_table_index, retry_table in enumerate(retry_section["tables"]):
            if _column_axis(retry_table) != base_column_axis:
                continue
            if _normalized_surface(retry_table["unit_exact"]) != base_unit:
                continue
            retry_contexts = {
                item
                for item in (
                    _normalized_surface(retry_table["title_exact"]),
                    _normalized_surface(retry_section["title_exact"]),
                )
                if item is not None
            }
            if base_context not in retry_contexts:
                continue
            retry_anchor_positions: dict[tuple[str, tuple[str | None, ...]], list[int]] = {}
            for retry_row_index, retry_row in enumerate(retry_table["rows"]):
                try:
                    anchor = _row_anchor(retry_row)
                except GeminiJsonRegionRepairV1Error:
                    continue
                retry_anchor_positions.setdefault(anchor, []).append(retry_row_index)
            if any(len(retry_anchor_positions.get(anchor, [])) != 1 for anchor in base_anchors):
                continue
            positions = [retry_anchor_positions[anchor][0] for anchor in base_anchors]
            if positions != sorted(positions):
                continue
            matches.append(
                (
                    retry_section_index,
                    retry_table_index,
                    {
                        "base_row_to_retry_row": positions,
                        "retry_table": retry_table,
                    },
                )
            )
    if len(matches) != 1:
        raise _error("standard page retry does not expose one unique table population")
    retry_section_index, retry_table_index, selected = matches[0]
    retry_table = selected["retry_table"]
    positions = selected["base_row_to_retry_row"]
    target_indexes = set(required_row_indexes)
    changed_target_ids = []
    matched_receipts = []
    for base_row_index, retry_row_index in enumerate(positions):
        base_row = base_table["rows"][base_row_index]
        retry_row = retry_table["rows"][retry_row_index]
        if base_row["row_kind"] != retry_row["row_kind"]:
            raise _error("matched row kind changed in the page retry")
        if _row_anchor(base_row) != _row_anchor(retry_row):
            raise _error("matched row anchor changed in the page retry")
        values_changed = base_row["values_exact"] != retry_row["values_exact"]
        if values_changed and base_row_index not in target_indexes:
            raise _error("page retry changed a non-target existing row")
        target_id = f"s{section_index + 1}:t{table_index + 1}:r{base_row_index + 1}"
        if values_changed:
            changed_target_ids.append(target_id)
        matched_receipts.append(
            {
                "base_target_id": target_id,
                "retry_target_id": (
                    f"s{retry_section_index + 1}:t{retry_table_index + 1}:r{retry_row_index + 1}"
                ),
                "values_changed": values_changed,
            }
        )
    if changed_target_ids != required_targets:
        raise _error("required changed row axis is incomplete or reordered")
    matched_retry_indexes = set(positions)
    added_retry_row_ids = [
        f"s{retry_section_index + 1}:t{retry_table_index + 1}:r{row_index + 1}"
        for row_index in range(len(retry_table["rows"]))
        if row_index not in matched_retry_indexes
    ]
    if require_added_rows != bool(added_retry_row_ids):
        raise _error("page retry row-extension contract does not match the observed population")
    if any(
        retry_table["rows"][row_index]["row_kind"] not in {"GROUP", "SUBTOTAL", "TOTAL"}
        for row_index in range(len(retry_table["rows"]))
        if row_index not in matched_retry_indexes
    ):
        raise _error("page retry added a non-structural source row")

    merged = canonical_clone_v1(base)
    base_by_retry_index = {
        retry_row_index: base_row_index for base_row_index, retry_row_index in enumerate(positions)
    }
    projected_rows = []
    for retry_row_index, retry_row in enumerate(retry_table["rows"]):
        base_row_index = base_by_retry_index.get(retry_row_index)
        if base_row_index is None:
            projected_rows.append(canonical_clone_v1(retry_row))
            continue
        projected = canonical_clone_v1(base_table["rows"][base_row_index])
        if base_row_index in target_indexes:
            projected["values_exact"] = canonical_clone_v1(retry_row["values_exact"])
        projected_rows.append(projected)
    merged["sections"][section_index]["tables"][table_index]["rows"] = projected_rows
    merged = validate_financial_page_json_v1(merged)
    material = {
        "added_retry_row_ids": added_retry_row_ids,
        "base_page_json_sha256": canonical_json_sha256_v1(base),
        "base_page_json_version_id": base_page_json_version_id,
        "base_table_ref": checked_target_ref,
        "column_axis_sha256": canonical_json_sha256_v1([list(item) for item in base_column_axis]),
        "format_version": TABLE_POPULATION_PROJECTION_FORMAT_VERSION,
        "matched_rows": matched_receipts,
        "merged_page_json_sha256": canonical_json_sha256_v1(merged),
        "required_changed_target_ids": required_targets,
        "retry_page_json_sha256": canonical_json_sha256_v1(retry),
        "retry_page_json_version_id": retry_page_json_version_id,
        "retry_table_ref": {
            "section_id": f"s{retry_section_index + 1}",
            "table_id": f"t{retry_table_index + 1}",
        },
        "rule": "UNIQUE_EXACT_AXIS_ORDERED_ROW_POPULATION_PROJECTION",
    }
    receipt = {
        **material,
        "projection_id": "gjfwtppv1:projection:" + canonical_json_sha256_v1(material),
    }
    return merged, receipt


def validate_whole_page_table_population_projection_v1(
    value: Any,
    *,
    base_page_json: Any,
    retry_page_json: Any,
    merged_page_json: Any,
) -> dict[str, Any]:
    """Rebuild and exact-compare one table-population projection receipt."""

    if type(value) is not dict:
        raise _error("table-population projection receipt is invalid")
    rebuilt_merged, rebuilt = project_whole_page_table_population_v1(
        base_page_json,
        retry_page_json,
        base_page_json_version_id=value.get("base_page_json_version_id"),
        retry_page_json_version_id=value.get("retry_page_json_version_id"),
        target_table_ref=value.get("base_table_ref"),
        required_changed_target_ids=value.get("required_changed_target_ids"),
        require_added_rows=bool(value.get("added_retry_row_ids")),
    )
    if rebuilt != value or not canonical_json_bytes_v1(rebuilt_merged) == canonical_json_bytes_v1(
        validate_financial_page_json_v1(merged_page_json)
    ):
        raise _error("table-population projection does not replay exactly")
    return rebuilt
