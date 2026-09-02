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
_MODEL_CELL_PACK_SEPARATOR = "凸"
_MODEL_DASH_ANNOTATION = re.compile(
    r"\A\s*(.*?)\s+paradise_missing_here_dash_handled_as_dash_or_zero\s*->\s*[-–—_]\s*\Z",
    re.IGNORECASE | re.DOTALL,
)
_DASH_PACK = re.compile(r"\A\s*[-–—_](?:\s+[-–—_])+\s*\Z")
_DASH_NOISE_PACK = re.compile(r"\A\s*[-–—_]\s*[^0-9A-Za-z\s.,()%]{1,3}\s*[-–—_]\s*\Z")
_EXPLICIT_CALENDAR_DATE = re.compile(
    r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])\s*[/.-]\s*(?:0?[1-9]|1[0-2])"
    r"\s*[/.-]\s*(?:19|20)\d{2}(?!\d)"
)
_ROW_LABEL_HEADER_ANCHORS = frozenset(
    {
        "ben lien quan",
        "chi tieu",
        "dien giai",
        "khoan muc",
        "noi dung",
    }
)
_STRUCTURAL_ROW_KEY_HEADER_ANCHORS = _ROW_LABEL_HEADER_ANCHORS | frozenset(
    {
        "stt",
        "so thu tu",
    }
)


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

    items = (
        "Đọc duy nhất ảnh này và trả đúng một JSON theo JSON Schema được cung cấp. "
        "Chỉ số hóa: (1) các báo cáo tài chính chính; (2) bảng thuyết minh "
        "hoặc danh sách khoản mục tài chính có nhãn hàng và giá trị. Không chép "
        "các đoạn văn diễn giải, giới thiệu, pháp lý hoặc chính sách thuần túy; "
        "narratives_exact luôn là mảng rỗng. Giữ đủ và đúng thứ tự mọi tiêu đề, "
        "khoản mục, cột và giá trị nhìn thấy trong các bảng/danh sách đó; giữ "
        "nguyên chính tả và chữ số, không sửa, tính lại hoặc suy đoán. Dấu gạch kế "
        'toán có thể chép nguyên văn hoặc ghi chuỗi "0". hierarchy_path_exact mô tả '
        "các cấp cha-con nhìn thấy. Nếu trang không có bảng/danh sách khoản mục "
        "thuộc phạm vi trên, trả NO_RELEVANT_FINANCIAL_CONTENT với sections rỗng. Nếu "
        "có nhưng không thể đọc đủ phần thiết yếu, trả UNRESOLVED_PAGE. Trước khi "
        "kết thúc, kiểm tra không bỏ sót hàng hoặc phần cuối bảng. Không trả Markdown "
        "hay nội dung ngoài JSON."
    )

    scope = (
        "Đọc duy nhất ảnh này và trả đúng một JSON theo JSON Schema được cung cấp. "
        "Chỉ coi là nội dung cần số hóa khi trang có: (1) Bảng cân đối kế toán, "
        "Báo cáo kết quả kinh doanh hoặc Báo cáo lưu chuyển tiền tệ; hoặc (2) bảng "
        "thuyết minh có số dư hay giá trị tài chính thực tế của các khoản mục theo "
        "một hay nhiều kỳ. Trang chỉ mô tả chính sách kế toán, phương pháp, tỷ lệ quy "
        "định, tỷ lệ dự phòng, tỷ lệ khấu trừ, ngưỡng, điều kiện, pháp lý hoặc văn "
        "xuôi mà không có số dư/giá trị tài chính thực tế thì trả "
        "NO_RELEVANT_FINANCIAL_CONTENT với sections rỗng; không chép lại nội dung đó. "
        "Nếu trang thuộc phạm vi cần số hóa, giữ đủ và đúng thứ tự mọi tiêu đề, khoản "
        "mục, cột và giá trị nhìn thấy; giữ nguyên chính tả và chữ số, không sửa, tính "
        "lại hoặc suy đoán. Dấu gạch kế toán có thể chép nguyên văn hoặc ghi chuỗi "
        '"0". Nếu không thể đọc đủ phần thiết yếu, trả UNRESOLVED_PAGE. Không trả '
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
    if variant == "items":
        return items + contract
    if variant == "scope":
        return scope + contract
    if variant == "compact":
        return common + contract
    if variant != "balanced":
        raise _error("prompt variant must be simple, items, scope, compact, or balanced")
    return (
        common + "\n\nMỗi section và table theo đúng thứ tự từ trên xuống. columns chỉ gồm cột "
        "giá trị; header_path_exact đi từ header ngoài đến header trong. Mỗi hàng "
        "ảnh xuất hiện đúng một lần, values_exact đọc ngang đúng hàng và có đúng số "
        "phần tử bằng columns; ô thật sự trống dùng null. Riêng ở lượt kiểm tra này, "
        'mọi ô chỉ có dấu gạch kế toán phải trả chính xác chuỗi "0"; tuyệt đối không '
        "chép ký tự của dấu gạch và không nối dấu gạch vào số ở ô bên cạnh. Giữ cả "
        "hàng cha không có số và subtotal/total "
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


def _fill_merged_hierarchy_path_v1(row: dict[str, Any], prior_row: dict[str, Any] | None) -> None:
    """Replay only vertically merged hierarchy cells from the preceding row.

    Gemini can preserve a visibly merged table cell as ``null`` in a later
    hierarchy level while retaining both the outer owner and the current row
    label.  Fill such internal nulls only from the immediately preceding row,
    only under an identical already-visible prefix, and never fill the leaf.
    This keeps the projection source ordered and prevents a distant row from
    manufacturing ancestry.
    """

    path = row.get("hierarchy_path_exact")
    label = row.get("label_exact")
    if (
        type(path) is not list
        or len(path) < 3
        or type(label) is not str
        or path[-1] != label
        or prior_row is None
    ):
        return
    prior_path = prior_row.get("hierarchy_path_exact")
    if type(prior_path) is not list or len(prior_path) != len(path):
        return

    rebuilt = list(path)
    visible_prefix_matches = True
    changed = False
    for index, item in enumerate(path[:-1]):
        prior_item = prior_path[index]
        if item is None:
            if not visible_prefix_matches or type(prior_item) is not str:
                return
            rebuilt[index] = prior_item
            changed = True
            continue
        if type(item) is not str or item != prior_item:
            visible_prefix_matches = False
    if changed:
        row["hierarchy_path_exact"] = rebuilt


def _bind_empty_internal_hierarchy_to_active_group_v1(
    row: dict[str, Any], active_group_label: str | None
) -> None:
    """Bind ``[group, null, leaf]`` to the exact preceding visible group.

    A provider response can insert one empty hierarchy level and a short CJK
    connective after the already-transcribed group label.  Normalize only this
    bounded convention: the active source-visible GROUP must be known, the path
    must contain exactly one parent/null/leaf triple, and any suffix after the
    exact group label must consist solely of one to eight CJK characters.  This
    rejects unrelated or stale parents while avoiding another paid page call.
    Raw provider bytes remain retained separately by the caller.
    """

    path = row.get("hierarchy_path_exact")
    label = row.get("label_exact")
    if (
        type(path) is not list
        or len(path) != 3
        or type(active_group_label) is not str
        or type(label) is not str
        or path[-1] != label
        or path[1] is not None
        or type(path[0]) is not str
        or not path[0].startswith(active_group_label)
    ):
        return
    suffix = path[0][len(active_group_label) :]
    if suffix and re.fullmatch(r"[\u3400-\u9fff]{1,8}", suffix) is None:
        return
    row["hierarchy_path_exact"] = [active_group_label, label]


def _path(
    value: Any,
    label: str,
    *,
    final: str | None | object = ...,
    omit_null_components: bool = False,
) -> list[str | None]:
    if type(value) is not list or not value:
        raise _error(f"{label} must be one nonempty path")
    result: list[str | None] = []
    for ordinal, item in enumerate(value):
        if item is None:
            if omit_null_components:
                continue
            if ordinal != len(value) - 1:
                raise _error(f"{label} may contain null only at the end")
            result.append(None)
        else:
            result.append(_raw(item, f"{label}[{ordinal}]"))
    if not result and omit_null_components and all(item is None for item in value):
        return [None]
    if not result:
        raise _error(f"{label} must retain at least one nonblank component")
    if final is not ... and result[-1] != final:
        raise _error(f"{label} final item differs from the row label")
    return result


def _expand_exact_model_cell_pack_v1(values: list[Any], *, width: int) -> list[Any] | None:
    """Expand one deterministic model cell pack only when it closes the row width.

    Gemini occasionally emits multiple adjacent numeric cells inside one string,
    separated by the literal sentinel ``凸``.  This is not source punctuation.
    Expansion is admitted only for a deficient row, only when every segment is
    nonblank, and only when the ordered expansion yields the declared width
    exactly.  Raw provider bytes remain unchanged in the store.
    """

    if len(values) >= width:
        return None
    expanded: list[Any] = []
    for value in values:
        if type(value) is str and _MODEL_CELL_PACK_SEPARATOR in value:
            parts = value.split(_MODEL_CELL_PACK_SEPARATOR)
            if any(not part.strip() for part in parts):
                return None
            expanded.extend(parts)
        elif type(value) is str and (match := _MODEL_DASH_ANNOTATION.fullmatch(value)):
            prefix = match.group(1).strip()
            if prefix in {"-", "–", "—", "_"}:
                expanded.append("-")
            elif prefix:
                expanded.extend((prefix, "-"))
            else:
                return None
        elif type(value) is str and _DASH_PACK.fullmatch(value):
            parts = re.findall(r"[-–—_]", value)
            expanded.extend("-" for _part in parts)
        elif type(value) is str and _DASH_NOISE_PACK.fullmatch(value):
            expanded.extend(("-", "-"))
        else:
            expanded.append(value)
    return expanded if len(expanded) == width else None


def _canonical_cell_pack_dash_v1(value: Any) -> Any:
    """Project a same-cell pack consisting solely of accounting dashes to one dash."""

    if type(value) is str and (match := _MODEL_DASH_ANNOTATION.fullmatch(value)):
        if match.group(1).strip() in {"-", "–", "—", "_"}:
            return "-"
    if type(value) is not str or _MODEL_CELL_PACK_SEPARATOR not in value:
        return value
    parts = value.split(_MODEL_CELL_PACK_SEPARATOR)
    if parts and all(part.strip() in {"-", "–", "—", "_"} for part in parts):
        return "-"
    return value


def _search_fold_v1(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).replace("đ", "d")


def _fill_signed_asset_liability_gap_v1(
    values: list[Any], columns: list[dict[str, Any]]
) -> list[Any] | None:
    """Insert one uniquely implied blank asset/liability cell before a visible total."""

    width = len(columns)
    if width < 4 or len(values) != width - 1 or values[-1] != values[-2]:
        return None
    leaves = [
        _search_fold_v1(" ".join(str(item or "") for item in column["header_path_exact"]))
        for column in columns[-3:]
    ]
    if not (
        "tai san" in leaves[0]
        and ("cong no" in leaves[1] or "no phai tra" in leaves[1])
        and "tong" in leaves[2]
    ):
        return None
    signed = _signed_integer_cell_v1(values[-1])
    if signed is None or signed == 0:
        return None
    insertion = width - 3 if signed < 0 else width - 2
    return [*values[:insertion], None, *values[insertion:]]


def _signed_integer_cell_v1(value: Any) -> int | None:
    if type(value) is not str:
        return None
    text = value.strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    if text.startswith("-") and text[1:].strip():
        negative = True
        text = text[1:].strip()
    digits = re.sub(r"[.,\s]", "", text)
    if not digits.isdigit():
        return None
    number = int(digits)
    return -number if negative else number


def _accounting_integer_cell_v1(value: Any) -> int | None:
    """Parse one printed integer while treating an accounting dash as exact zero."""

    if type(value) is str and re.fullmatch(r"\s*[-–—_](?:\s*[-–—_])*\s*", value):
        return 0
    return _signed_integer_cell_v1(value)


def _normalize_two_detail_total_omitted_zero_v1(table: dict[str, Any]) -> bool:
    """Restore one omitted blank/dash from an exact two-row subtotal equation.

    The raw provider response remains retained separately.  Here all printed
    dash variants are intentionally projected to the accounting value ``0``;
    this removes an otherwise meaningless ambiguity about which dash in one
    consecutive zero run was omitted.  No nonzero value is synthesized: the
    complete total and the other complete detail row must determine the exact
    deficient-row vector in every declared numeric column.
    """

    columns = table["columns"]
    rows = table["rows"]
    width = len(columns)
    if (
        width < 2
        or len(rows) != 3
        or any(column["value_kind"] not in {"MONEY", "COUNT"} for column in columns)
    ):
        return False
    totals = [row for row in rows if row["row_kind"] == "TOTAL"]
    details = [row for row in rows if row["row_kind"] != "TOTAL"]
    short = [row for row in details if len(row["values_exact"]) == width - 1]
    complete = [row for row in details if len(row["values_exact"]) == width]
    if len(totals) != 1 or len(short) != 1 or len(complete) != 1:
        return False
    total_values = totals[0]["values_exact"]
    complete_values = complete[0]["values_exact"]
    if len(total_values) != width:
        return False
    total_numbers = [_accounting_integer_cell_v1(value) for value in total_values]
    complete_numbers = [_accounting_integer_cell_v1(value) for value in complete_values]
    short_numbers = [_accounting_integer_cell_v1(value) for value in short[0]["values_exact"]]
    if any(number is None for number in [*total_numbers, *complete_numbers, *short_numbers]):
        return False
    expected = [
        total - detail for total, detail in zip(total_numbers, complete_numbers, strict=True)
    ]
    if not any(
        [*short_numbers[:index], 0, *short_numbers[index:]] == expected for index in range(width)
    ):
        return False

    nonzero_source = iter(
        value
        for value, number in zip(short[0]["values_exact"], short_numbers, strict=True)
        if number != 0
    )
    rebuilt: list[Any] = []
    for number in expected:
        rebuilt.append("0" if number == 0 else next(nonzero_source))
    try:
        next(nonzero_source)
    except StopIteration:
        short[0]["values_exact"] = rebuilt
        return True
    return False


def _row_label_matches_hierarchy_leaf_v1(row: dict[str, Any]) -> bool:
    """Bind cosmetic bullet variants without changing either source string."""

    path = row["hierarchy_path_exact"]
    label = row["label_exact"]
    if not path:
        return False
    leaf = path[-1]
    if leaf == label:
        return True
    if type(leaf) is not str or type(label) is not str:
        return False

    def normalized(value: str) -> str:
        return _SPACE.sub(" ", value).strip()

    label_without_bullet = re.sub(r"\A[-–—_•]\s*", "", normalized(label), count=1)
    leaf_normalized = normalized(leaf)
    if leaf_normalized == label_without_bullet:
        return True
    return any(
        leaf_normalized.endswith(f"{separator}{label_without_bullet}")
        or leaf_normalized.endswith(f"{separator} {label_without_bullet}")
        for separator in ("-", "–", "—")
    )


def _cell_matches_value_kind_v1(value: Any, value_kind: str) -> bool:
    """Check one candidate cell placement against its declared value kind."""

    if value is None or value_kind == "UNKNOWN":
        return True
    if type(value) is not str:
        return False
    if value_kind == "TEXT":
        return _accounting_integer_cell_v1(value) is None
    if value_kind in {"MONEY", "COUNT"}:
        return _accounting_integer_cell_v1(value) is not None
    if value_kind == "PERCENT":
        text = value.strip()
        return _accounting_integer_cell_v1(text) is not None or bool(
            re.fullmatch(r"\(?\s*[+-]?[0-9]+(?:[.,][0-9]+)?\s*%\s*\)?", text)
        )
    return False


def _unique_null_padding_by_value_kind_v1(
    values: list[Any], columns: list[dict[str, Any]]
) -> list[Any] | None:
    """Insert one omitted null only when column kinds locate it uniquely."""

    if len(values) + 1 != len(columns):
        return None
    candidates: list[list[Any]] = []
    for index in range(len(columns)):
        candidate = [*values[:index], None, *values[index:]]
        if (
            all(
                _cell_matches_value_kind_v1(cell, column["value_kind"])
                for cell, column in zip(candidate, columns, strict=True)
            )
            and candidate not in candidates
        ):
            candidates.append(candidate)
    return candidates[0] if len(candidates) == 1 else None


def _normalize_four_column_movement_table_v1(table: dict[str, Any]) -> bool:
    """Drop one redundant label header and place omitted dash cells uniquely.

    Gemini occasionally emits the visible row-label header as a TEXT value
    column, then omits printed dash cells from the four numeric movement
    columns.  This projection is accepted only for the exact
    opening/increase/decrease/closing header shape and only when every short
    row is uniquely reconstructed by the printed accounting equation.  Raw
    provider bytes and every nonblank cell remain unchanged.
    """

    columns = table["columns"]
    rows = table["rows"]
    if len(columns) != 5 or columns[0]["value_kind"] != "TEXT":
        return False
    value_columns = columns[1:]
    headers = [
        _search_fold_v1(" ".join(str(item or "") for item in column["header_path_exact"]))
        for column in value_columns
    ]
    opening = any(anchor in headers[0] for anchor in ("so du", "du dau", "dau ky"))
    increase = any(anchor in headers[1] for anchor in ("tang", "trich lap"))
    decrease = any(anchor in headers[2] for anchor in ("giam", "su dung", "dieu chinh"))
    closing = any(anchor in headers[3] for anchor in ("so du", "du cuoi", "cuoi ky"))
    if not (opening and increase and decrease and closing):
        return False
    if any(column["value_kind"] not in {"MONEY", "COUNT", "UNKNOWN"} for column in value_columns):
        return False

    normalized_rows: list[list[Any]] = []
    for row in rows:
        values = row["values_exact"]
        if len(values) == 4:
            normalized_rows.append(list(values))
            continue
        parsed = [_accounting_integer_cell_v1(value) for value in values]
        if any(number is None for number in parsed):
            return False
        if len(values) == 2 and parsed[0] == parsed[1]:
            normalized_rows.append([values[0], None, None, values[1]])
            continue
        if len(values) == 3 and parsed[0] + parsed[1] == parsed[2] and parsed[1] != 0:
            if parsed[1] > 0:
                normalized_rows.append([values[0], values[1], None, values[2]])
            else:
                normalized_rows.append([values[0], None, values[1], values[2]])
            continue
        return False

    table["columns"] = value_columns
    for row, normalized in zip(rows, normalized_rows, strict=True):
        row["values_exact"] = normalized
    return True


def _normalize_dual_period_preferred_share_blanks_v1(table: dict[str, Any]) -> bool:
    """Restore omitted preferred-share blanks under two exact period triplets.

    A visible equity table can have ``total/common/preferred`` columns for each
    of two periods.  Gemini sometimes retains the anonymous row-label column
    but emits only the two equal ``total/common`` cells when the preferred cell
    is a printed dash.  The two missing positions are unique only for this
    exact repeated header shape and only when each retained pair is equal.
    """

    columns = table["columns"]
    rows = table["rows"]
    if (
        len(columns) != 7
        or columns[0]["value_kind"] != "TEXT"
        or any(item is not None for item in columns[0]["header_path_exact"])
        or any(not _row_label_matches_hierarchy_leaf_v1(row) for row in rows)
    ):
        return False
    value_columns = columns[1:]
    if any(column["value_kind"] not in {"MONEY", "COUNT"} for column in value_columns):
        return False
    leaves = [
        _search_fold_v1(" ".join(str(item or "") for item in column["header_path_exact"][-1:]))
        for column in value_columns
    ]
    if not (
        all(anchor in leaves[index] for index, anchor in ((0, "tong"), (3, "tong")))
        and all("thuong" in leaves[index] for index in (1, 4))
        and all("uu dai" in leaves[index] for index in (2, 5))
    ):
        return False
    period_paths = [column["header_path_exact"][:-1] for column in value_columns]
    if not (
        period_paths[0] == period_paths[1] == period_paths[2]
        and period_paths[3] == period_paths[4] == period_paths[5]
        and period_paths[0] != period_paths[3]
    ):
        return False

    normalized_rows: list[list[Any]] = []
    for row in rows:
        values = row["values_exact"]
        if len(values) == 6:
            normalized_rows.append(list(values))
            continue
        if (
            len(values) == 4
            and values[0] == values[1]
            and values[2] == values[3]
            and all(_accounting_integer_cell_v1(value) is not None for value in values)
        ):
            normalized_rows.append([values[0], values[1], None, values[2], values[3], None])
            continue
        return False

    table["columns"] = value_columns
    for row, normalized in zip(rows, normalized_rows, strict=True):
        row["values_exact"] = normalized
    return True


def _normalize_leading_text_header_proxies_v1(table: dict[str, Any]) -> bool:
    """Remove empty label/header proxies while preserving their merged header text.

    A constrained model can serialize a visible row-label column and a merged
    numeric parent header as flat TEXT value columns.  The convention is
    harmless only when the remaining suffix is entirely non-TEXT, every row
    already carries that suffix width, and every surplus leading cell is null.
    Intermediate header text is retained as a prefix on each real value
    column; the first leading header is the row-label header represented by
    ``label_exact``.
    """

    columns = table["columns"]
    rows = table["rows"]
    leading_count = 0
    for column in columns:
        if column["value_kind"] != "TEXT":
            break
        leading_count += 1
    if leading_count == 0 or leading_count == len(columns):
        return False
    first_header = _search_fold_v1(
        " ".join(str(item or "") for item in columns[0]["header_path_exact"])
    )
    if first_header not in _ROW_LABEL_HEADER_ANCHORS:
        return False
    if any(
        not row["hierarchy_path_exact"] or row["hierarchy_path_exact"][-1] != row["label_exact"]
        for row in rows
    ):
        return False
    value_columns = columns[leading_count:]
    value_width = len(value_columns)
    row_values = [row["values_exact"] for row in table["rows"]]
    if not all(value_width <= len(values) <= len(columns) for values in row_values):
        return False
    if not any(len(values) < len(columns) for values in row_values):
        return False
    for values in row_values:
        excess = len(values) - value_width
        if any(value is not None for value in values[:excess]):
            return False

    parent_path: list[Any] = []
    for column in columns[1:leading_count]:
        parent_path.extend(column["header_path_exact"])
    if parent_path:
        for column in value_columns:
            column["header_path_exact"] = [*parent_path, *column["header_path_exact"]]
    table["columns"] = value_columns
    for row in table["rows"]:
        excess = len(row["values_exact"]) - value_width
        row["values_exact"] = row["values_exact"][excess:]
    return True


def _normalize_leading_row_label_proxy_v1(table: dict[str, Any]) -> bool:
    """Drop one leading label proxy and close exact packed value rows.

    Some constrained responses keep the visible row-label column in
    ``columns`` even though its text is already represented by ``label_exact``
    and ``hierarchy_path_exact``.  Admit the convention only when the first
    column is textual, every row binds its exact label as the hierarchy leaf,
    and every row either already has the suffix width or expands to that width
    using the existing exact model-cell-pack grammar.  A nonblank proxy header
    must also be visible in every row hierarchy, as in a merged group label.
    No provided value is discarded or synthesized.
    """

    columns = table["columns"]
    rows = table["rows"]
    if len(columns) < 2 or columns[0]["value_kind"] != "TEXT":
        return False
    if not all(_row_label_matches_hierarchy_leaf_v1(row) for row in rows):
        return False

    header_members = [
        item for item in columns[0]["header_path_exact"] if type(item) is str and item.strip()
    ]
    header_folded = _search_fold_v1(" ".join(header_members)).strip()
    if header_folded:
        for row in rows:
            hierarchy_folded = _search_fold_v1(
                " ".join(
                    item
                    for item in row["hierarchy_path_exact"]
                    if type(item) is str and item.strip()
                )
            )
            if header_folded not in hierarchy_folded:
                return False

    value_width = len(columns) - 1
    normalized_rows: list[list[Any]] = []
    for row in rows:
        values = list(row["values_exact"])
        if len(values) == value_width:
            normalized_rows.append(values)
            continue
        expanded = _expand_exact_model_cell_pack_v1(values, width=value_width)
        if expanded is None:
            return False
        normalized_rows.append(expanded)

    table["columns"] = columns[1:]
    for row, normalized in zip(rows, normalized_rows, strict=True):
        row["values_exact"] = normalized
    return True


def _normalize_explicit_row_label_column_v1(table: dict[str, Any]) -> bool:
    """Remove one explicit label column already represented by ``label_exact``.

    Primary statements often retain STT and note-reference columns while the
    visible ``Chỉ tiêu`` column is serialized only as ``label_exact``.  A debt
    classification table similarly uses its numeric ``Nhóm`` cell as the row
    label.  Only one exact label-header candidate is admitted.  Short rows can
    be padded only when one null position is uniquely implied by the remaining
    declared value kinds, so no visible value is discarded or invented.
    """

    columns = table["columns"]
    candidates = []
    for index, column in enumerate(columns):
        header = _search_fold_v1(" ".join(str(item or "") for item in column["header_path_exact"]))
        if header in _ROW_LABEL_HEADER_ANCHORS:
            candidates.append(index)
            continue
        if (
            header == "nhom"
            and index == 0
            and all(
                _signed_integer_cell_v1(row["label_exact"]) is not None for row in table["rows"]
            )
        ):
            candidates.append(index)
    if len(candidates) != 1:
        return False
    label_index = candidates[0]
    old_width = len(columns)
    new_width = old_width - 1
    if new_width <= 0:
        return False

    normalized_rows: list[list[Any]] = []
    for row in table["rows"]:
        values = row["values_exact"]
        if len(values) == new_width:
            normalized_rows.append(list(values))
            continue
        if len(values) == old_width and values[label_index] == row["label_exact"]:
            normalized_rows.append([*values[:label_index], *values[label_index + 1 :]])
            continue
        transaction_header = (
            _search_fold_v1(" ".join(str(item or "") for item in columns[1]["header_path_exact"]))
            if label_index == 0 and len(columns) > 1
            else ""
        )
        if (
            label_index == 0
            and transaction_header in {"giao dich", "loai giao dich"}
            and columns[1]["value_kind"] == "TEXT"
            and len(values) + 1 == new_width
            and row["label_exact"] is not None
            and _row_label_matches_hierarchy_leaf_v1(row)
            and all(
                _cell_matches_value_kind_v1(cell, column["value_kind"])
                for cell, column in zip(values, columns[2:], strict=True)
            )
        ):
            normalized_rows.append([row["label_exact"], *values])
            continue
        padded = (
            _unique_null_padding_by_value_kind_v1(
                list(values), [*columns[:label_index], *columns[label_index + 1 :]]
            )
            if label_index > 0
            else None
        )
        if padded is not None:
            normalized_rows.append(padded)
            continue
        return False

    table["columns"] = [*columns[:label_index], *columns[label_index + 1 :]]
    for row, normalized in zip(table["rows"], normalized_rows, strict=True):
        row["values_exact"] = normalized
    return True


def _normalize_omitted_leading_structural_columns_v1(table: dict[str, Any]) -> bool:
    """Drop a complete leading row-key prefix already represented by each row.

    Some otherwise complete Gemini tables retain ``STT`` and/or the printed
    label header in ``columns`` while placing those visible row keys only in
    ``label_exact`` and ``hierarchy_path_exact``.  Admit that convention only
    when every row has one identical shorter width, the omitted columns form a
    leading structural-key prefix, and every row binds its exact label as the
    final hierarchy component.  No provided cell is moved, synthesized, or
    discarded.
    """

    columns = table["columns"]
    rows = table["rows"]
    row_widths = {len(row["values_exact"]) for row in rows}
    if len(row_widths) != 1:
        return False
    value_width = next(iter(row_widths))
    missing_count = len(columns) - value_width
    if missing_count <= 0 or value_width <= 0:
        return False
    omitted = columns[:missing_count]
    anonymous_numeric_key = (
        missing_count == 1
        and omitted[0]["value_kind"] in {"COUNT", "UNKNOWN"}
        and all(item is None for item in omitted[0]["header_path_exact"])
        and all(_signed_integer_cell_v1(row["label_exact"]) is not None for row in rows)
    )
    anonymous_row_label_key = (
        missing_count == 1
        and omitted[0]["value_kind"] == "UNKNOWN"
        and all(item is None for item in omitted[0]["header_path_exact"])
        and all(_row_label_matches_hierarchy_leaf_v1(row) for row in rows)
        and all(
            all(
                _cell_matches_value_kind_v1(cell, column["value_kind"])
                for cell, column in zip(row["values_exact"], columns[missing_count:], strict=True)
            )
            for row in rows
        )
    )
    generic_text_key = (
        missing_count == 1
        and omitted[0]["value_kind"] == "TEXT"
        and all(_row_label_matches_hierarchy_leaf_v1(row) for row in rows)
        and all(
            all(
                _cell_matches_value_kind_v1(cell, column["value_kind"])
                for cell, column in zip(row["values_exact"], columns[missing_count:], strict=True)
            )
            for row in rows
        )
    )
    contextual_source_exact = "\n".join(
        item for item in omitted[0]["header_path_exact"] if type(item) is str and item.strip()
    )
    contextual_text_header = (
        generic_text_key
        and table["title_exact"] is None
        and bool(contextual_source_exact)
        and _EXPLICIT_CALENDAR_DATE.search(contextual_source_exact) is not None
    )
    for column in omitted:
        header = _search_fold_v1(" ".join(str(item or "") for item in column["header_path_exact"]))
        if (
            header not in _STRUCTURAL_ROW_KEY_HEADER_ANCHORS
            and not anonymous_numeric_key
            and not anonymous_row_label_key
            and not generic_text_key
        ):
            return False
    if any(not _row_label_matches_hierarchy_leaf_v1(row) for row in rows):
        return False
    if contextual_text_header:
        # A model may serialize a merged period/table caption as a leading
        # TEXT value column while every row already contains only the actual
        # numeric suffix.  Do not silently discard that source-visible
        # context: promote the exact ordered header members to ``title_exact``
        # before removing the proxy column.  This is schema normalization;
        # no date, period, family, or accounting role is inferred here.
        table["title_exact"] = contextual_source_exact
    table["columns"] = columns[missing_count:]
    return True


def _move_unique_arithmetic_total_v1(
    values: list[Any], columns: list[dict[str, Any]], *, model_annotation_present: bool
) -> list[Any]:
    """Move one displaced total only when exact integer arithmetic proves its position."""

    if not model_annotation_present or not values or values[-1] is not None:
        return values
    last_header = _search_fold_v1(
        " ".join(str(item or "") for item in columns[-1]["header_path_exact"])
    )
    if "tong" not in last_header and "total" not in last_header:
        return values
    parsed = [_signed_integer_cell_v1(value) for value in values[:-1]]
    candidates: list[int] = []
    for index, candidate in enumerate(parsed):
        if candidate is None:
            continue
        others = [number for offset, number in enumerate(parsed) if offset != index and number]
        if others and candidate == sum(others):
            candidates.append(index)
    if len(candidates) != 1:
        return values
    result = list(values)
    result[-1] = result[candidates[0]]
    result[candidates[0]] = None
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
                column["header_path_exact"] = _path(
                    column["header_path_exact"],
                    "column header path",
                    omit_null_components=True,
                )
                if column["value_kind"] not in _VALUE_KINDS:
                    raise _error("column value_kind drifted")
            width = len(table["columns"])
            row_widths: list[int] = []
            prior_row: dict[str, Any] | None = None
            active_group_label: str | None = None
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
                _fill_merged_hierarchy_path_v1(row, prior_row)
                _bind_empty_internal_hierarchy_to_active_group_v1(row, active_group_label)
                _path(row["hierarchy_path_exact"], "row hierarchy path")
                if row["row_kind"] not in _ROW_KINDS:
                    raise _error("row_kind drifted")
                if type(row["values_exact"]) is not list:
                    raise _error("row values must be an array")
                row["values_exact"] = [
                    None if value == "" else value for value in row["values_exact"]
                ]
                row_widths.append(len(row["values_exact"]))
                if row["row_kind"] == "GROUP" and type(row["label_exact"]) is str:
                    active_group_label = row["label_exact"]
                prior_row = row
            if (
                _normalize_explicit_row_label_column_v1(table)
                or _normalize_leading_row_label_proxy_v1(table)
                or _normalize_omitted_leading_structural_columns_v1(table)
                or _normalize_leading_text_header_proxies_v1(table)
                or _normalize_four_column_movement_table_v1(table)
                or _normalize_dual_period_preferred_share_blanks_v1(table)
                or _normalize_two_detail_total_omitted_zero_v1(table)
            ):
                width = len(table["columns"])
                row_widths = [len(row["values_exact"]) for row in table["rows"]]
            if all(row_width == width for row_width in row_widths):
                pass
            elif (
                width == 1
                and table["columns"][0]["value_kind"] == "TEXT"
                and all(row_width == 0 for row_width in row_widths)
            ):
                for row in table["rows"]:
                    row["values_exact"] = [None]
            else:
                for row in table["rows"]:
                    if (
                        row["row_kind"] == "GROUP"
                        and row["label_exact"] is not None
                        and _row_label_matches_hierarchy_leaf_v1(row)
                        and row["values_exact"] == []
                    ):
                        row["values_exact"] = [None] * width
                        continue
                    model_annotation_present = any(
                        type(value) is str and _MODEL_DASH_ANNOTATION.fullmatch(value)
                        for value in row["values_exact"]
                    )
                    expanded = _expand_exact_model_cell_pack_v1(row["values_exact"], width=width)
                    if expanded is not None:
                        row["values_exact"] = _move_unique_arithmetic_total_v1(
                            expanded,
                            table["columns"],
                            model_annotation_present=model_annotation_present,
                        )
                        continue
                    filled = _fill_signed_asset_liability_gap_v1(
                        row["values_exact"], table["columns"]
                    )
                    if filled is not None:
                        row["values_exact"] = filled
                if any(len(row["values_exact"]) != width for row in table["rows"]):
                    raise _error("row values do not align with table value columns")
            for row in table["rows"]:
                row["values_exact"] = [
                    _canonical_cell_pack_dash_v1(cell) for cell in row["values_exact"]
                ]
                for cell in row["values_exact"]:
                    _cell_raw(cell)

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
