from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.evaluation.reader_outputs_v2 import ParsedVLMPageV2, VLMTableParserConfig
from bctc_ai.evaluation.semantic_html_tables import (
    ParsedHTMLDocumentV2,
    RowFragmentMerge,
    parse_html_document_v2,
)
from bctc_ai.validation.reader_agreement import ReaderRow


class DeepSeekOutputV2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedDeepSeekOutputV2:
    input_path: str
    raw_output: str
    page: ParsedVLMPageV2
    fragment_merges: tuple[RowFragmentMerge, ...]
    table_bboxes_normalized_0_999: tuple[tuple[int, int, int, int], ...]

    @property
    def reader_rows(self) -> tuple[ReaderRow, ...]:
        return self.page.reader_rows


_REFERENCE_BLOCK = re.compile(
    r"<\|ref\|>.*?<\|/ref\|>\s*<\|det\|>.*?<\|/det\|>",
    flags=re.DOTALL,
)


def _load_result(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise DeepSeekOutputV2Error(f"cannot read DeepSeek-OCR-2 result: {path}") from exc
    if not isinstance(payload, dict):
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 result must be a JSON object")
    return payload


def _table_bboxes(payload: dict[str, Any]) -> tuple[tuple[int, int, int, int], ...]:
    references = payload.get("layout_references")
    if not isinstance(references, list):
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 result has no layout references")
    boxes: list[tuple[int, int, int, int]] = []
    for reference in references:
        if not isinstance(reference, dict):
            raise DeepSeekOutputV2Error("DeepSeek-OCR-2 layout reference is not an object")
        if retrieval_key(str(reference.get("label", ""))) != "table":
            continue
        if reference.get("status") != "PROPOSAL_ONLY":
            raise DeepSeekOutputV2Error("DeepSeek table box is not explicitly proposal-only")
        if reference.get("authority") != "NONE_GEOMETRY_PROPOSAL_ONLY":
            raise DeepSeekOutputV2Error("DeepSeek table box was granted geometry authority")
        raw_boxes = reference.get("normalized_0_999_boxes")
        if not isinstance(raw_boxes, list) or not raw_boxes:
            raise DeepSeekOutputV2Error("DeepSeek table reference contains no normalized box")
        for raw_box in raw_boxes:
            if not isinstance(raw_box, list) or len(raw_box) != 4:
                raise DeepSeekOutputV2Error("DeepSeek table box does not have four coordinates")
            values = []
            for raw_value in raw_box:
                if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
                    raise DeepSeekOutputV2Error("DeepSeek table coordinate is not numeric")
                value = float(raw_value)
                if not value.is_integer() or not 0 <= value <= 999:
                    raise DeepSeekOutputV2Error(
                        "DeepSeek table coordinate is outside the integral 0-999 contract"
                    )
                values.append(int(value))
            box = tuple(values)
            if box[2] <= box[0] or box[3] <= box[1]:
                raise DeepSeekOutputV2Error("DeepSeek table box is degenerate")
            boxes.append(box)
    if not boxes:
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 result has no table-box proposal")
    return tuple(boxes)


def parse_deepseek_ocr2_result_v2(
    path: Path,
    config: VLMTableParserConfig,
    *,
    page_tag: str,
) -> ParsedDeepSeekOutputV2:
    payload = _load_result(path)
    if payload.get("state") != "SEMANTIC_OCR_PROPOSAL_COMPLETE":
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 result is incomplete")
    if payload.get("evidence_role") != "SEMANTIC_AND_READING_ORDER_PROPOSAL_ONLY":
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 evidence role is not proposal-only")
    authority = payload.get("authority")
    if (
        not isinstance(authority, dict)
        or not authority
        or any(bool(value) for value in authority.values())
    ):
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 result grants forbidden authority")
    raw_output = payload.get("raw_output")
    if not isinstance(raw_output, str) or not raw_output.strip():
        raise DeepSeekOutputV2Error("DeepSeek-OCR-2 result has no raw output")
    bboxes = _table_bboxes(payload)
    prefix = raw_output.split("<table", maxsplit=1)[0]
    context = normalize_text(_REFERENCE_BLOCK.sub(" ", prefix))
    try:
        parsed: ParsedHTMLDocumentV2 = parse_html_document_v2(
            raw_output,
            config,
            page_tag=page_tag,
            input_path=path.as_posix(),
            context_text=context,
            table_bboxes=bboxes,
            reassemble_fragments=True,
        )
    except RuntimeError as exc:
        raise DeepSeekOutputV2Error(str(exc)) from exc
    return ParsedDeepSeekOutputV2(
        input_path=path.as_posix(),
        raw_output=raw_output,
        page=parsed.page,
        fragment_merges=parsed.fragment_merges,
        table_bboxes_normalized_0_999=bboxes,
    )
