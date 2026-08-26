"""Schema-blind Gemini page-to-financial-JSON contract.

The reader sees one immutable page image and this contract only.  It does not
receive a bank, family, schema node, expected value, or OCR/geometry result.
The module validates exact model output and builds deterministic search
projections; it never repairs source spelling or digits.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

FORMAT_VERSION = "GEMINI_FINANCIAL_PAGE_JSON_V7"
MODEL_OUTPUT_FORMAT_VERSION = "FINANCIAL_PAGE_JSON_V6"
SEARCH_NORMALIZATION_VERSION = "VIETNAMESE_FINANCIAL_SEARCH_V1"

_STATUSES = frozenset(
    {
        "NO_RELEVANT_FINANCIAL_CONTENT",
        "PRIMARY_FINANCIAL_STATEMENT",
        "FINANCIAL_NOTE_CONTENT",
        "MIXED_FINANCIAL_CONTENT",
        "UNRESOLVED_PAGE",
    }
)
_CONTENT_KINDS = frozenset(
    {
        "PRIMARY_STATEMENT",
        "FINANCIAL_NOTE",
        "OTHER_FINANCIAL_TABLE",
        "FINANCIAL_NARRATIVE",
    }
)
_STATEMENT_TYPES = frozenset(
    {
        "BALANCE_SHEET",
        "INCOME_STATEMENT",
        "CASH_FLOW",
        "OTHER",
        "NOT_APPLICABLE",
        "UNKNOWN",
    }
)
_ROW_KINDS = frozenset({"GROUP", "ITEM", "SUBTOTAL", "TOTAL", "UNKNOWN"})
_VALUE_KINDS = frozenset({"MONEY", "PERCENT", "COUNT", "TEXT", "UNKNOWN"})
_CONTINUATION_KINDS = frozenset(
    {"NONE", "CONTINUES_FROM_PREVIOUS_PAGE", "CONTINUES_ON_NEXT_PAGE", "BOTH", "UNKNOWN"}
)
_FENCE = re.compile(r"\A```(?:json)?\s*(.*?)\s*```\Z", re.DOTALL | re.IGNORECASE)
_SPACE = re.compile(r"\s+")


class GeminiFinancialPageJsonV1Error(ValueError):
    """The page JSON is not an exact instance of the frozen contract."""


def _error(message: str) -> GeminiFinancialPageJsonV1Error:
    return GeminiFinancialPageJsonV1Error(message)


def build_financial_page_json_prompt_v1(
    *, variant: str = "compact", include_contract_template: bool = False
) -> str:
    """Return one schema-blind Vietnamese page transcription prompt."""

    simple = (
        "Đọc duy nhất ảnh này và trả đúng một JSON theo JSON Schema được cung cấp. "
        "Chỉ chép nội dung thuộc báo cáo tài chính: Bảng cân đối kế toán, Báo cáo "
        "kết quả kinh doanh, Báo cáo lưu chuyển tiền tệ và các thuyết minh tài chính. "
        "Giữ đủ và đúng thứ tự mọi tiêu đề, khoản mục, cột và giá trị nhìn thấy; giữ "
        "nguyên chính tả và chữ số, không sửa, tính lại hoặc suy đoán. Dấu gạch kế toán "
        'có thể chép nguyên văn hoặc ghi chuỗi "0". hierarchy_path_exact mô tả các cấp '
        "cha-con nhìn thấy; nếu không chắc loại hàng hoặc cột thì dùng UNKNOWN. Nếu trang "
        "không có nội dung trên, trả NO_RELEVANT_FINANCIAL_CONTENT với sections rỗng. "
        "Nếu có nội dung nhưng không thể đọc đủ phần thiết yếu, trả UNRESOLVED_PAGE. "
        "Trước khi kết thúc, kiểm tra không bỏ sót hàng hoặc phần cuối trang. Không trả "
        "Markdown hay nội dung ngoài JSON."
    )

    common = (
        "Chuyển nội dung báo cáo tài chính nhìn thấy trong ảnh thành JSON theo "
        "JSON Schema được cung cấp. Chỉ lấy Bảng cân đối kế toán, Báo cáo kết quả "
        "kinh doanh, Báo cáo lưu chuyển tiền tệ, bảng và nội dung thuyết minh tài "
        "chính. Giữ nguyên chính tả, thứ tự, mọi chữ số, dấu chấm, dấu phẩy, ngoặc, "
        "dấu âm, dấu phần trăm và dấu gạch. Không sửa, không tính lại, không suy ra "
        "giá trị và không trả nội dung ngoài JSON. Chép đầy đủ mọi khoản mục, hàng và "
        "cột giá trị nhìn thấy; không bỏ, gộp, tách hoặc đổi thứ tự. Mỗi values_exact "
        "phải đọc ngang đúng hàng và có đúng số phần tử bằng columns. Nếu có nội dung "
        "tài chính nhưng không thể chép chắc chắn và đầy đủ, trả UNRESOLVED_PAGE thay vì "
        'đoán. Ô dấu gạch có thể giữ dấu gạch nguyên văn hoặc trả chuỗi "0"; không '
        'được dùng dấu gạch dưới "_" để thay cho dấu gạch kế toán. Không '
        "được suy ra hay thay đổi các giá trị khác. Nếu "
        "trang không có nội dung tài "
        "chính thuộc các loại trên, trả status NO_RELEVANT_FINANCIAL_CONTENT và "
        "sections rỗng. hierarchy_path_exact đi từ các nhãn cha nhìn thấy đến đúng "
        "label_exact của hàng; nếu hàng không có nhãn thì phần tử cuối phải là null, "
        "tuyệt đối không tự đặt tên cho hàng. columns gồm mọi cột dữ liệu ngoài cột "
        "nhãn khoản mục; giữ cả cột Mã số/Thuyết minh dưới value_kind TEXT nhưng không "
        "tạo một column riêng cho label_exact. Chỉ điền completion sau khi đã đọc lại "
        "toàn trang. all_relevant_content_transcribed chỉ được là true khi mọi nội dung "
        "tài chính nhìn thấy đã được chép đủ; khóa completion phải nằm sau sections và "
        "chỉ được điền cuối cùng. Phải kiểm tra toàn bộ sections và mọi tables, kể cả "
        "bảng/phần tiếp nối ở cuối trang. "
        "Không dừng chép khi gặp subtotal/total nếu phía dưới còn hàng tài chính. "
        "Nếu đầu ra có nguy cơ bị cắt, thiếu phần cuối, hoặc không "
        "thể xác nhận đủ, trả UNRESOLVED_PAGE, đặt cờ false và ghi lý do nguyên văn ngắn "
        "trong uncertainty_exact. Không được giảm số hàng để làm JSON ngắn hơn."
    )
    contract = ""
    if include_contract_template:
        contract = (
            "\n\nTrả đúng một object JSON có dạng: "
            '{"status":"...","sections":[...],"completion":{...}}. Mỗi section có '
            "đúng các khóa "
            "content_kind, statement_type, title_exact, narratives_exact, tables. Mỗi table "
            "có đúng các khóa title_exact, unit_exact, continuation, columns, rows. Mỗi "
            "column chỉ có header_path_exact, value_kind. Mỗi row chỉ có label_exact, "
            "hierarchy_path_exact, row_kind, values_exact. Thứ tự phần tử trong mảng chính "
            "là thứ tự nguồn; không tạo ID hoặc số thứ tự. Dùng null cho nhãn hoặc ô thật "
            "sự trống. completion có đúng all_relevant_content_transcribed và "
            "uncertainty_exact; code sẽ tự đếm cấu trúc sau khi nhận JSON."
        )
    if variant == "simple":
        return simple + contract
    if variant == "compact":
        return common + contract
    if variant != "balanced":
        raise _error("prompt variant must be simple, compact, or balanced")
    return (
        common + "\n\nMỗi section và table theo đúng thứ tự từ trên xuống. columns chỉ gồm cột "
        "giá trị; header_path_exact đi từ header ngoài đến header trong. Mỗi hàng "
        "ảnh xuất hiện đúng một lần, values_exact đọc ngang đúng hàng và có đúng số "
        "phần tử bằng columns; ô thật sự trống dùng null, còn dấu gạch và số 0 phải "
        "giữ thành chuỗi nguyên văn. Giữ cả hàng cha không có số và subtotal/total "
        "không có nhãn. hierarchy_path_exact đi từ cha ngoài cùng đến chính hàng; "
        "phần tử cuối phải bằng label_exact, hoặc null nếu hàng không nhãn. Dùng "
        "UNKNOWN khi không chắc loại hàng/cột; không bỏ hàng và không dịch vector "
        "giá trị sang hàng trước hoặc sau. Phép cộng chỉ được dùng để tự kiểm tra "
        "quan hệ nhìn thấy, không được sửa digit hay trộn subtotal với các descendants "
        "của nó." + contract
    )


def financial_page_json_response_schema_v1() -> dict[str, Any]:
    """Return the provider-neutral JSON Schema used by every prompt variant."""

    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    exact_path = {"type": "array", "minItems": 1, "items": nullable_string}
    column = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "header_path_exact": exact_path,
            "value_kind": {"type": "string", "enum": sorted(_VALUE_KINDS)},
        },
        "required": ["header_path_exact", "value_kind"],
    }
    row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "label_exact": nullable_string,
            "hierarchy_path_exact": {
                **exact_path,
                "description": (
                    "Exact visible ancestor labels followed by label_exact; append null "
                    "when the current row has no visible label. Never invent a label."
                ),
            },
            "row_kind": {"type": "string", "enum": sorted(_ROW_KINDS)},
            "values_exact": {"type": "array", "items": nullable_string},
        },
        "required": [
            "label_exact",
            "hierarchy_path_exact",
            "row_kind",
            "values_exact",
        ],
    }
    table = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title_exact": nullable_string,
            "unit_exact": nullable_string,
            "continuation": {"type": "string", "enum": sorted(_CONTINUATION_KINDS)},
            "columns": {"type": "array", "minItems": 1, "items": column},
            "rows": {"type": "array", "minItems": 1, "items": row},
        },
        "required": [
            "title_exact",
            "unit_exact",
            "continuation",
            "columns",
            "rows",
        ],
    }
    section = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "content_kind": {"type": "string", "enum": sorted(_CONTENT_KINDS)},
            "statement_type": {"type": "string", "enum": sorted(_STATEMENT_TYPES)},
            "title_exact": nullable_string,
            "narratives_exact": {"type": "array", "items": {"type": "string"}},
            "tables": {"type": "array", "items": table},
        },
        "required": [
            "content_kind",
            "statement_type",
            "title_exact",
            "narratives_exact",
            "tables",
        ],
    }
    completion = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "all_relevant_content_transcribed": {"type": "boolean"},
            "uncertainty_exact": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "all_relevant_content_transcribed",
            "uncertainty_exact",
        ],
    }
    # Preserve this property order for constrained generation.  In particular,
    # completion is intentionally last so the model cannot fill its receipt
    # before emitting the complete section/table/row arrays.  Canonical hashing
    # at the persistence boundary remains key-order independent.
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": sorted(_STATUSES)},
            "sections": {"type": "array", "items": section},
            "completion": completion,
        },
        "required": ["status", "sections", "completion"],
    }


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise _error(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _nonfinite(token: str) -> None:
    raise _error(f"non-finite JSON number {token}")


def decode_financial_page_json_text_v1(text: str) -> dict[str, Any]:
    """Decode strict JSON, tolerating only one outer Markdown JSON fence."""

    if type(text) is not str or not text or len(text.encode("utf-8")) > 32 * 1024 * 1024:
        raise _error("model response must be one nonempty bounded UTF-8 string")
    stripped = text.strip()
    match = _FENCE.fullmatch(stripped)
    if match is not None:
        stripped = match.group(1)
    try:
        value = json.loads(stripped, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except GeminiFinancialPageJsonV1Error:
        raise
    except json.JSONDecodeError as exc:
        raise _error("model response is not one strict JSON object") from exc
    return validate_financial_page_json_v1(value)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _raw(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if (
        type(value) is not str
        or not value.strip()
        or "\r" in value
        or value != unicodedata.normalize("NFC", value)
    ):
        raise _error(f"{label} must be one nonempty exact NFC string")
    return value


def _cell_raw(value: Any) -> str | None:
    """Preserve one nonblank cell exactly; whitespace is not semantic authority."""

    if value is None:
        return None
    if type(value) is not str or not value.strip() or "\r" in value:
        raise _error("cell source text must be one nonempty exact NFC string")
    if value != unicodedata.normalize("NFC", value):
        raise _error("cell source text must be one nonempty exact NFC string")
    return value


def _path(value: Any, label: str, *, final: str | None | object = ...) -> list[str | None]:
    if type(value) is not list or not value:
        raise _error(f"{label} must be one nonempty path")
    result: list[str | None] = []
    for ordinal, item in enumerate(value):
        if item is None:
            if ordinal != len(value) - 1:
                raise _error(f"{label} may contain null only at the end")
            result.append(None)
        else:
            result.append(_raw(item, f"{label}[{ordinal}]"))
    if final is not ... and result[-1] != final:
        raise _error(f"{label} final item differs from the row label")
    return result


def validate_financial_page_json_v1(value: Any) -> dict[str, Any]:
    """Validate one model response and canonicalize one harmless table convention.

    The model sometimes emits the printed row-label column in ``columns`` while
    keeping its cells solely in ``label_exact``.  When every row follows that
    convention and the leading column is textual, the redundant column is
    removed from the canonical projection.  The immutable raw response remains
    untouched in storage.  Semantic proposals such as hierarchy and row kind
    are deliberately not treated as transcription authority here.
    """

    root = canonical_clone_v1(
        _exact_dict(value, {"status", "sections", "completion"}, "financial page JSON")
    )
    if type(root["status"]) is not str or root["status"] not in _STATUSES:
        raise _error("page status drifted")
    if type(root["sections"]) is not list:
        raise _error("sections must be an array")
    empty_status = root["status"] == "NO_RELEVANT_FINANCIAL_CONTENT"
    unresolved_status = root["status"] == "UNRESOLVED_PAGE"
    if empty_status and root["sections"] != []:
        raise _error("NO_RELEVANT status and section presence disagree")
    if not empty_status and not unresolved_status and root["sections"] == []:
        raise _error("relevant complete status requires at least one section")
    for section in root["sections"]:
        _exact_dict(
            section,
            {
                "content_kind",
                "statement_type",
                "title_exact",
                "narratives_exact",
                "tables",
            },
            "section",
        )
        if section["content_kind"] not in _CONTENT_KINDS:
            raise _error("section content_kind drifted")
        if section["statement_type"] not in _STATEMENT_TYPES:
            raise _error("section statement_type drifted")
        _raw(section["title_exact"], "section title", nullable=True)
        if type(section["narratives_exact"]) is not list:
            raise _error("section narratives must be an array")
        for narrative in section["narratives_exact"]:
            _raw(narrative, "financial narrative")
        if type(section["tables"]) is not list:
            raise _error("section tables must be an array")
        if (
            not section["tables"]
            and not section["narratives_exact"]
            and section["title_exact"] is None
        ):
            raise _error("a relevant section without a table or narrative must retain its title")
        for table in section["tables"]:
            _exact_dict(
                table,
                {
                    "title_exact",
                    "unit_exact",
                    "continuation",
                    "columns",
                    "rows",
                },
                "table",
            )
            _raw(table["title_exact"], "table title", nullable=True)
            _raw(table["unit_exact"], "table unit", nullable=True)
            if table["continuation"] not in _CONTINUATION_KINDS:
                raise _error("table continuation drifted")
            if type(table["columns"]) is not list or not table["columns"]:
                raise _error("table must contain value columns")
            if type(table["rows"]) is not list or not table["rows"]:
                raise _error("table must contain rows")
            for column in table["columns"]:
                _exact_dict(
                    column,
                    {"header_path_exact", "value_kind"},
                    "column",
                )
                _path(column["header_path_exact"], "column header path")
                if column["value_kind"] not in _VALUE_KINDS:
                    raise _error("column value_kind drifted")
            width = len(table["columns"])
            row_widths: list[int] = []
            for row in table["rows"]:
                _exact_dict(
                    row,
                    {
                        "label_exact",
                        "hierarchy_path_exact",
                        "row_kind",
                        "values_exact",
                    },
                    "row",
                )
                _raw(row["label_exact"], "row label", nullable=True)
                _path(row["hierarchy_path_exact"], "row hierarchy path")
                if row["row_kind"] not in _ROW_KINDS:
                    raise _error("row_kind drifted")
                if type(row["values_exact"]) is not list:
                    raise _error("row values must be an array")
                row_widths.append(len(row["values_exact"]))
                for cell in row["values_exact"]:
                    _cell_raw(cell)
            if all(row_width == width for row_width in row_widths):
                pass
            elif (
                width > 1
                and table["columns"][0]["value_kind"] == "TEXT"
                and all(row_width == width - 1 for row_width in row_widths)
            ):
                del table["columns"][0]
            else:
                raise _error("row values do not align with table value columns")

    completion = _exact_dict(
        root["completion"],
        {
            "all_relevant_content_transcribed",
            "uncertainty_exact",
        },
        "completion",
    )
    if type(completion["all_relevant_content_transcribed"]) is not bool:
        raise _error("completion flag must be boolean")
    if type(completion["uncertainty_exact"]) is not list:
        raise _error("completion uncertainty must be an array")
    for item in completion["uncertainty_exact"]:
        _raw(item, "completion uncertainty")
    completed = completion["all_relevant_content_transcribed"]
    if unresolved_status:
        if completed or not completion["uncertainty_exact"]:
            raise _error("UNRESOLVED_PAGE requires an incomplete receipt and uncertainty")
    elif not completed or completion["uncertainty_exact"]:
        raise _error("complete page status requires an exact complete receipt")
    return root


def _content_counts_from_checked_v1(checked: dict[str, Any]) -> dict[str, int]:
    tables = sum(len(section["tables"]) for section in checked["sections"])
    rows = sum(len(table["rows"]) for section in checked["sections"] for table in section["tables"])
    cells = sum(
        len(row["values_exact"])
        for section in checked["sections"]
        for table in section["tables"]
        for row in table["rows"]
    )
    populated = sum(
        cell is not None
        for section in checked["sections"]
        for table in section["tables"]
        for row in table["rows"]
        for cell in row["values_exact"]
    )
    return {
        "cell_count": cells,
        "populated_cell_count": populated,
        "row_count": rows,
        "section_count": len(checked["sections"]),
        "table_count": tables,
    }


def normalize_search_text_v1(value: str) -> dict[str, str]:
    """Build deterministic NFC, normalized, and accentless search projections."""

    if type(value) is not str or not value or "\r" in value:
        raise _error("search text must be one nonempty string")
    exact = value
    nfc = unicodedata.normalize("NFC", exact)
    normalized = _SPACE.sub(" ", nfc.casefold()).strip()
    decomposed = unicodedata.normalize("NFD", normalized)
    folded = "".join(character for character in decomposed if not unicodedata.combining(character))
    folded = folded.replace("đ", "d")
    return {
        "normalization_version": SEARCH_NORMALIZATION_VERSION,
        "text_ascii_folded": folded,
        "text_exact": exact,
        "text_nfc": nfc,
        "text_search_normalized": normalized,
    }


def iter_financial_page_rows_v1(value: Any) -> list[dict[str, Any]]:
    """Return deterministic flattened row projections for indexed storage."""

    checked = validate_financial_page_json_v1(value)
    result: list[dict[str, Any]] = []
    for section_index, section in enumerate(checked["sections"], start=1):
        for table_index, table in enumerate(section["tables"], start=1):
            for row_index, row in enumerate(table["rows"], start=1):
                result.append(
                    {
                        "content_kind": section["content_kind"],
                        "section_id": f"s{section_index}",
                        "section_title_exact": section["title_exact"],
                        "statement_type": section["statement_type"],
                        "table_id": f"t{table_index}",
                        "table_title_exact": table["title_exact"],
                        "unit_exact": table["unit_exact"],
                        "row_id": f"r{row_index}",
                        "source_order": row_index - 1,
                        **canonical_clone_v1(row),
                    }
                )
    return result


def count_financial_page_content_v1(value: Any) -> dict[str, int]:
    """Return small benchmark counts without interpreting source content."""

    checked = validate_financial_page_json_v1(value)
    return _content_counts_from_checked_v1(checked)


def family_relation_candidates_v1(
    value: Any,
    *,
    anchor_aliases: list[list[str]],
) -> list[dict[str, Any]]:
    """Find bounded two/three-anchor row neighborhoods within individual tables.

    This is retrieval only.  Accent-folded aliases increase recall but never
    establish mapping authority.
    """

    if type(anchor_aliases) is not list or len(anchor_aliases) not in {2, 3}:
        raise _error("family retrieval requires exactly two or three anchor sets")
    normalized_anchors: list[set[str]] = []
    for aliases in anchor_aliases:
        if type(aliases) is not list or not aliases:
            raise _error("each anchor must contain one or more aliases")
        normalized_anchors.append(
            {normalize_search_text_v1(alias)["text_ascii_folded"] for alias in aliases}
        )
    checked = validate_financial_page_json_v1(value)
    candidates: list[dict[str, Any]] = []
    for section_index, section in enumerate(checked["sections"], start=1):
        for table_index, table in enumerate(section["tables"], start=1):
            hits: list[list[tuple[int, dict[str, Any]]]] = []
            for aliases in normalized_anchors:
                hit_rows = [
                    (row_index, row)
                    for row_index, row in enumerate(table["rows"], start=1)
                    if row["label_exact"] is not None
                    and normalize_search_text_v1(row["label_exact"])["text_ascii_folded"] in aliases
                ]
                hits.append(hit_rows)
            if all(hits):
                candidates.append(
                    {
                        "anchor_row_ids": [
                            [f"r{row_index}" for row_index, _row in group] for group in hits
                        ],
                        "section_id": f"s{section_index}",
                        "table_id": f"t{table_index}",
                    }
                )
    return candidates
