"""Schema-blind full-page note-table JSON contract for hosted Gemma 4.

This module contains no provider call and no family-specific parser.  It fixes
one compact output shape, validates model output without repairing it, selects
one family region through declarative two-then-three item relationships, and
checks caller-declared direct accounting equations over the raw JSON values.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

FORMAT_VERSION = "HOSTED_GEMMA4_HIERARCHICAL_NOTE_JSON_V1"
MODEL_OUTPUT_FORMAT_VERSION = "HIERARCHICAL_NOTE_TABLE_JSON_V1"

_STATUS_VALUES = frozenset({"HAS_NOTE_TABLES", "NO_NOTE_TABLES"})
_ROW_KINDS = frozenset({"GROUP", "ITEM", "SUBTOTAL", "TOTAL", "UNKNOWN"})
_VALUE_KINDS = frozenset({"MONEY", "PERCENT", "COUNT", "TEXT", "UNKNOWN"})
_RELATIONS = frozenset(
    {
        "TABLE_HAS_DESCENDANT",
        "ANCESTOR_OF",
        "PARENT_OF",
        "SIBLING_BEFORE",
        "NEIGHBOR_BEFORE",
    }
)
_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_COLUMN_ID = re.compile(r"^c[1-9][0-9]*$")
_ROW_ID = re.compile(r"^r[1-9][0-9]*$")
_FENCE = re.compile(r"\A```(?:json)?\s*(.*?)\s*```\Z", re.DOTALL | re.IGNORECASE)
_SPACE = re.compile(r"\s+")
_INTEGER_DOTS = re.compile(r"^[0-9]{1,3}(?:\.[0-9]{3})+$")
_INTEGER_COMMAS = re.compile(r"^[0-9]{1,3}(?:,[0-9]{3})+$")
_UNSET = object()


class HostedGemma4HierarchicalNoteJsonV1Error(ValueError):
    """The model output or downstream declarative proof is not exact."""


def _error(message: str) -> HostedGemma4HierarchicalNoteJsonV1Error:
    return HostedGemma4HierarchicalNoteJsonV1Error(message)


def build_hierarchical_note_json_prompt_v1() -> str:
    """Return the single short, schema-blind prompt used by this contract."""

    return (
        "Chuyển các bảng thuyết minh khoản mục nhìn thấy trong ảnh thành đúng một JSON "
        "theo mẫu cố định sau:\n"
        '{"status":"HAS_NOTE_TABLES","tables":[{"title":"...","unit":null,'
        '"columns":[{"column_id":"c1","header_path":["..."],'
        '"value_kind":"MONEY"}],"rows":[{"row_id":"r1","source_order":0,'
        '"label":"...","hierarchy_path":["cha","con"],"row_kind":"ITEM",'
        '"values":["giá trị nguyên văn hoặc null"]}]}]}\n'
        "Chỉ trả JSON, không markdown và không giải thích. Giữ nguyên chính tả của "
        "khoản mục và giữ nguyên mọi chữ số, dấu chấm, dấu phẩy, ngoặc, dấu âm, dấu "
        "gạch. Không sửa, không suy diễn, không tính toán. columns chỉ gồm các cột giá "
        "trị, không gồm cột nhãn; mỗi hàng phải có đủ values theo đúng thứ tự columns, "
        "ô trống dùng null. hierarchy_path đi từ khoản mục cha ngoài cùng đến chính "
        "hàng đó; hàng không nhãn dùng null ở label và phần tử cuối hierarchy_path. "
        "value_kind chỉ là MONEY, PERCENT, COUNT, TEXT hoặc UNKNOWN. row_kind chỉ là "
        "GROUP, ITEM, SUBTOTAL, TOTAL hoặc UNKNOWN. row_id là r1,r2,... và "
        "source_order là 0,1,... theo thứ tự in trong bảng. Bỏ số trang, chữ ký, dấu "
        "mộc và nội dung ngoài bảng thuyết minh. Nếu ảnh không có bảng thuyết minh "
        'khoản mục thì trả đúng {"status":"NO_NOTE_TABLES","tables":[]}.'
    )


def hierarchical_note_json_response_schema_v1() -> dict[str, Any]:
    """Return the provider-neutral JSON Schema paired with the short prompt."""

    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    path = {"type": "array", "minItems": 1, "items": nullable_string}
    column = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "column_id": {"type": "string"},
            "header_path": path,
            "value_kind": {"type": "string", "enum": sorted(_VALUE_KINDS)},
        },
        "required": ["column_id", "header_path", "value_kind"],
    }
    row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "row_id": {"type": "string"},
            "source_order": {"type": "integer"},
            "label": nullable_string,
            "hierarchy_path": path,
            "row_kind": {"type": "string", "enum": sorted(_ROW_KINDS)},
            "values": {"type": "array", "items": nullable_string},
        },
        "required": [
            "row_id",
            "source_order",
            "label",
            "hierarchy_path",
            "row_kind",
            "values",
        ],
    }
    table = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "unit": nullable_string,
            "columns": {"type": "array", "minItems": 1, "items": column},
            "rows": {"type": "array", "minItems": 1, "items": row},
        },
        "required": ["title", "unit", "columns", "rows"],
    }
    return canonical_clone_v1(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {"type": "string", "enum": sorted(_STATUS_VALUES)},
                "tables": {"type": "array", "items": table},
            },
            "required": ["status", "tables"],
        }
    )


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise _error(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _nonfinite(token: str) -> None:
    raise _error(f"non-finite JSON number {token}")


def decode_hierarchical_note_json_text_v1(text: str) -> dict[str, Any]:
    """Decode one response, allowing only an optional outer JSON code fence."""

    if type(text) is not str or not text or len(text.encode("utf-8")) > 16 * 1024 * 1024:
        raise _error("model response must be one nonempty bounded UTF-8 string")
    stripped = text.strip()
    fenced = _FENCE.fullmatch(stripped)
    if fenced is not None:
        stripped = fenced.group(1)
    try:
        value = json.loads(stripped, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except HostedGemma4HierarchicalNoteJsonV1Error:
        raise
    except json.JSONDecodeError as exc:
        raise _error("model response is not one strict JSON object") from exc
    return validate_hierarchical_note_json_v1(value)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _raw_string(value: Any, label: str, *, empty: bool = False) -> str:
    if (
        type(value) is not str
        or (not empty and not value)
        or "\r" in value
        or value != unicodedata.normalize("NFC", value)
    ):
        raise _error(f"{label} must be one exact NFC string")
    return value


def _optional_raw_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _raw_string(value, label, empty=True)


def _path(value: Any, *, label: str, row_label: str | None | object = _UNSET) -> list[str | None]:
    if type(value) is not list or not value:
        raise _error(f"{label} must be one nonempty hierarchy path")
    result: list[str | None] = []
    for ordinal, item in enumerate(value):
        if item is None:
            if ordinal != len(value) - 1:
                raise _error(f"{label} may contain null only as its final item")
            result.append(None)
        else:
            result.append(_raw_string(item, f"{label}[{ordinal}]"))
    if row_label is not _UNSET:
        if row_label is not None and result[-1] != row_label:
            raise _error(f"{label} final item does not equal the exact row label")
        if row_label is None and result[-1] is not None:
            raise _error(f"{label} for an unlabeled row must end in null")
    return result


def validate_hierarchical_note_json_v1(value: Any) -> dict[str, Any]:
    """Validate the fixed model-output shape without repairing model content."""

    root = _exact_dict(value, {"status", "tables"}, "hierarchical note JSON")
    if type(root["status"]) is not str or root["status"] not in _STATUS_VALUES:
        raise _error("hierarchical note JSON status drifted")
    if type(root["tables"]) is not list:
        raise _error("hierarchical note JSON tables must be an array")
    if (root["status"] == "NO_NOTE_TABLES") != (root["tables"] == []):
        raise _error("status and table presence disagree")
    for table_ordinal, table in enumerate(root["tables"]):
        _exact_dict(table, {"columns", "rows", "title", "unit"}, "note table")
        _raw_string(table["title"], f"table[{table_ordinal}].title")
        _optional_raw_string(table["unit"], f"table[{table_ordinal}].unit")
        if type(table["columns"]) is not list or not table["columns"]:
            raise _error("a note table must contain at least one value column")
        if type(table["rows"]) is not list or not table["rows"]:
            raise _error("a note table must contain at least one row")
        for column_ordinal, column in enumerate(table["columns"], start=1):
            _exact_dict(column, {"column_id", "header_path", "value_kind"}, "value column")
            if column["column_id"] != f"c{column_ordinal}":
                raise _error("column IDs must be one-based and contiguous")
            _path(column["header_path"], label="column header path")
            if column["header_path"][-1] is None:
                raise _error("column header path cannot end in null")
            if type(column["value_kind"]) is not str or column["value_kind"] not in _VALUE_KINDS:
                raise _error("column value_kind drifted")
        width = len(table["columns"])
        for row_ordinal, row in enumerate(table["rows"], start=1):
            _exact_dict(
                row,
                {"hierarchy_path", "label", "row_id", "row_kind", "source_order", "values"},
                "note row",
            )
            if row["row_id"] != f"r{row_ordinal}" or _ROW_ID.fullmatch(row["row_id"]) is None:
                raise _error("row IDs must be one-based and contiguous")
            if type(row["source_order"]) is not int or row["source_order"] != row_ordinal - 1:
                raise _error("row source_order must be zero-based and contiguous")
            row_label = _optional_raw_string(row["label"], "row label")
            _path(row["hierarchy_path"], label="row hierarchy path", row_label=row_label)
            if type(row["row_kind"]) is not str or row["row_kind"] not in _ROW_KINDS:
                raise _error("row_kind drifted")
            if type(row["values"]) is not list or len(row["values"]) != width:
                raise _error("row values do not align exactly with the value columns")
            for cell_ordinal, cell in enumerate(row["values"]):
                _optional_raw_string(cell, f"row value[{cell_ordinal}]")
    return canonical_clone_v1(root)


def _match_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    accentless = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return _SPACE.sub(" ", accentless.replace("đ", "d")).strip()


def _aliases(value: Any, label: str) -> frozenset[str]:
    if type(value) is not list or not value:
        raise _error(f"{label} must contain one or more aliases")
    result = frozenset(_match_text(_raw_string(item, label)) for item in value)
    if len(result) != len(value):
        raise _error(f"{label} contains duplicate normalized aliases")
    return result


def _relation(value: Any, label: str) -> dict[str, Any]:
    relation = _exact_dict(value, {"left_aliases", "relation", "right_aliases"}, label)
    if type(relation["relation"]) is not str or relation["relation"] not in _RELATIONS:
        raise _error(f"{label}.relation drifted")
    _aliases(relation["left_aliases"], f"{label}.left_aliases")
    _aliases(relation["right_aliases"], f"{label}.right_aliases")
    return relation


def validate_family_region_signature_v1(value: Any) -> dict[str, Any]:
    """Validate a declarative two-item signature plus optional third-item gates."""

    signature = _exact_dict(
        value, {"disambiguators", "family_id", "primary_relation"}, "family region signature"
    )
    if type(signature["family_id"]) is not str or _ID.fullmatch(signature["family_id"]) is None:
        raise _error("family_id must be one lowercase identifier")
    _relation(signature["primary_relation"], "primary_relation")
    if type(signature["disambiguators"]) is not list:
        raise _error("signature disambiguators must be an array")
    for ordinal, relation in enumerate(signature["disambiguators"]):
        _relation(relation, f"disambiguators[{ordinal}]")
    return canonical_clone_v1(signature)


def _matches(value: str | None, aliases: frozenset[str]) -> bool:
    return value is not None and _match_text(value) in aliases


def _relation_witnesses(
    table: Mapping[str, Any], relation: Mapping[str, Any]
) -> list[dict[str, Any]]:
    left = _aliases(relation["left_aliases"], "left aliases")
    right = _aliases(relation["right_aliases"], "right aliases")
    kind = relation["relation"]
    rows = table["rows"]
    witnesses: list[dict[str, Any]] = []
    if kind == "TABLE_HAS_DESCENDANT":
        if _matches(table["title"], left):
            for row in rows:
                if _matches(row["label"], right):
                    witnesses.append({"left": "TABLE_TITLE", "right": row["row_id"]})
        return witnesses
    if kind in {"ANCESTOR_OF", "PARENT_OF"}:
        for row in rows:
            path = row["hierarchy_path"]
            for left_index, left_value in enumerate(path):
                if not _matches(left_value, left):
                    continue
                for right_index in range(left_index + 1, len(path)):
                    if _matches(path[right_index], right) and (
                        kind == "ANCESTOR_OF" or right_index == left_index + 1
                    ):
                        witnesses.append(
                            {
                                "left_path_index": left_index,
                                "relation_row_id": row["row_id"],
                                "right_path_index": right_index,
                            }
                        )
        return witnesses
    for left_row in rows:
        if not _matches(left_row["label"], left):
            continue
        for right_row in rows:
            if not _matches(right_row["label"], right):
                continue
            if left_row["hierarchy_path"][:-1] != right_row["hierarchy_path"][:-1]:
                continue
            distance = right_row["source_order"] - left_row["source_order"]
            if distance > 0 and (kind == "SIBLING_BEFORE" or distance == 1):
                witnesses.append(
                    {
                        "left": left_row["row_id"],
                        "right": right_row["row_id"],
                        "source_order_distance": distance,
                    }
                )
    return witnesses


def select_family_table_v1(output: Any, signature: Any) -> dict[str, Any]:
    """Select by a two-item relation; use third-item relations only on ambiguity."""

    checked = validate_hierarchical_note_json_v1(output)
    checked_signature = validate_family_region_signature_v1(signature)
    primary: list[tuple[int, list[dict[str, Any]]]] = []
    for table_index, table in enumerate(checked["tables"]):
        witnesses = _relation_witnesses(table, checked_signature["primary_relation"])
        if witnesses:
            primary.append((table_index, witnesses))
    if not primary:
        return {"candidate_table_indices": [], "stage": "PRIMARY_TWO_ITEM", "status": "NO_MATCH"}
    if len(primary) == 1:
        index, witnesses = primary[0]
        return {
            "candidate_table_indices": [index],
            "primary_witnesses": witnesses,
            "selected_table_index": index,
            "stage": "PRIMARY_TWO_ITEM",
            "status": "SELECTED",
        }
    filtered: list[tuple[int, list[list[dict[str, Any]]]]] = []
    for table_index, _ in primary:
        all_witnesses = [
            _relation_witnesses(checked["tables"][table_index], relation)
            for relation in checked_signature["disambiguators"]
        ]
        if all(all_witnesses):
            filtered.append((table_index, all_witnesses))
    if len(filtered) == 1:
        index, witnesses = filtered[0]
        return {
            "candidate_table_indices": [item[0] for item in primary],
            "disambiguator_witnesses": witnesses,
            "selected_table_index": index,
            "stage": "THIRD_ITEM_DISAMBIGUATION",
            "status": "SELECTED",
        }
    candidates = [item[0] for item in (filtered if filtered else primary)]
    return {
        "candidate_table_indices": candidates,
        "stage": "THIRD_ITEM_DISAMBIGUATION",
        "status": "AMBIGUOUS",
    }


def parse_vietnamese_numeric_surface_v1(surface: Any, value_kind: str) -> Decimal:
    """Parse one already-observed raw value without correcting its characters."""

    if type(value_kind) is not str or value_kind not in {"MONEY", "PERCENT", "COUNT"}:
        raise _error("numeric parsing requires MONEY, PERCENT, or COUNT")
    raw = _raw_string(surface, "numeric surface")
    text = raw.replace(" ", "")
    if text in {"-", "–", "—"}:
        return Decimal(0)
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if text.startswith("-"):
        negative = not negative
        text = text[1:]
    if not text:
        raise _error("numeric surface contains no digits")
    if value_kind == "PERCENT":
        if "." in text and "," in text:
            raise _error("percentage surface has mixed separators")
        normalized = text.replace(",", ".")
    else:
        if "." in text and "," in text:
            raise _error("integer surface has mixed separators")
        if "." in text:
            if _INTEGER_DOTS.fullmatch(text) is None:
                raise _error("money/count dot grouping is not exact")
            normalized = text.replace(".", "")
        elif "," in text:
            if _INTEGER_COMMAS.fullmatch(text) is None:
                raise _error("money/count comma grouping is not exact")
            normalized = text.replace(",", "")
        else:
            normalized = text
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise _error("numeric surface is not an exact decimal") from exc
    if not value.is_finite():
        raise _error("numeric surface is not finite")
    return -value if negative else value


def evaluate_direct_sum_v1(
    table: Any, *, result_row_id: str, component_row_ids: Sequence[str]
) -> dict[str, Any]:
    """Evaluate one declared direct frontier on every numeric column."""

    checked = validate_hierarchical_note_json_v1(
        {"status": "HAS_NOTE_TABLES", "tables": [canonical_clone_v1(table)]}
    )["tables"][0]
    if type(result_row_id) is not str or _ROW_ID.fullmatch(result_row_id) is None:
        raise _error("result_row_id drifted")
    if (
        type(component_row_ids) not in {list, tuple}
        or len(component_row_ids) < 1
        or any(
            type(item) is not str or _ROW_ID.fullmatch(item) is None for item in component_row_ids
        )
        or len(set(component_row_ids)) != len(component_row_ids)
        or result_row_id in component_row_ids
    ):
        raise _error("component row IDs must be one unique nonempty direct frontier")
    rows = {row["row_id"]: row for row in checked["rows"]}
    if result_row_id not in rows or any(row_id not in rows for row_id in component_row_ids):
        raise _error("equation references an absent row")
    lane_results: list[dict[str, Any]] = []
    for lane, column in enumerate(checked["columns"]):
        if column["value_kind"] not in {"MONEY", "PERCENT", "COUNT"}:
            continue
        result_surface = rows[result_row_id]["values"][lane]
        component_surfaces = [rows[row_id]["values"][lane] for row_id in component_row_ids]
        if result_surface is None or any(surface is None for surface in component_surfaces):
            raise _error("equation contains a blank numeric cell")
        result_value = parse_vietnamese_numeric_surface_v1(result_surface, column["value_kind"])
        component_values = [
            parse_vietnamese_numeric_surface_v1(surface, column["value_kind"])
            for surface in component_surfaces
        ]
        component_sum = sum(component_values, Decimal(0))
        lane_results.append(
            {
                "column_id": column["column_id"],
                "component_sum": str(component_sum),
                "exact": component_sum == result_value,
                "result": str(result_value),
            }
        )
    if not lane_results:
        raise _error("equation has no numeric lanes")
    return {
        "component_row_ids": list(component_row_ids),
        "exact_all_numeric_lanes": all(item["exact"] for item in lane_results),
        "lane_results": lane_results,
        "result_row_id": result_row_id,
    }
