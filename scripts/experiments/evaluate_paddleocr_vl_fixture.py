from __future__ import annotations

import argparse
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, parse_financial_number
from bctc_ai.ocr.pdf_text import extract_pdf_text
from bctc_ai.rows.pdf_statement import reconstruct_statement_rows
from bctc_ai.tables.geometry import analyze_page_geometry, load_geometry_config
from bctc_ai.validation.reader_agreement import ReaderRow, align_ordered_reader_rows


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(normalize_text(" ".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--geometry-config", type=Path, required=True)
    parser.add_argument("--input-image", type=Path, required=True)
    parser.add_argument("--vlm-result", type=Path, required=True)
    parser.add_argument("--benchmark-metric", type=Path, action="append", default=[])
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--package-freeze", type=Path, required=True)
    parser.add_argument("--inference-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _native_rows(source_pdf: Path, page_number: int, geometry_config: Path) -> tuple[ReaderRow, ...]:
    config = load_geometry_config(geometry_config)
    pages = list(extract_pdf_text(source_pdf, {page_number}))
    if len(pages) != 1:
        raise RuntimeError(f"expected exactly one native PDF page, found {len(pages)}")
    rows = reconstruct_statement_rows(analyze_page_geometry(pages[0], config), config)
    return tuple(
        ReaderRow(
            source_row_ids=(row.row_id,),
            label=row.label,
            note_reference=row.note_reference,
            cells=tuple(cell.parsed for cell in row.cells),
        )
        for row in rows
        if row.cells
    )


def _vlm_rows(result_path: Path) -> tuple[list[str], tuple[ReaderRow, ...], list[list[str]]]:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    table_blocks = [
        block for block in payload["parsing_res_list"] if block["block_label"] == "table"
    ]
    if len(table_blocks) != 1:
        raise RuntimeError(f"expected exactly one VLM table block, found {len(table_blocks)}")
    parser = _TableParser()
    parser.feed(table_blocks[0]["block_content"])
    if len(parser.rows) < 2:
        raise RuntimeError("VLM table has no data rows")
    width = max(len(row) for row in parser.rows)
    padded = [row + [""] * (width - len(row)) for row in parser.rows]
    header = padded[0]
    converted = [
        ReaderRow(
            source_row_ids=(f"vlm-row-{index}",),
            label=row[0],
            note_reference=row[1] or None,
            cells=tuple(parse_financial_number(value) for value in row[2:]),
        )
        for index, row in enumerate(padded[1:], start=1)
    ]
    substantive = [
        index
        for index, row in enumerate(converted)
        if any(cell.observation.value in {"VALUE", "ZERO", "DASH"} for cell in row.cells)
    ]
    if not substantive:
        raise RuntimeError("VLM table has no rows with visible financial values")
    start, end = substantive[0], substantive[-1]
    excluded = padded[1 : start + 1] + padded[end + 2 :]
    return header, tuple(converted[start : end + 1]), excluded


def _cell_record(reference, candidate) -> dict[str, object]:
    return {
        "reference_raw": reference.raw_text,
        "candidate_raw": candidate.raw_text,
        "reference_observation": reference.observation.value,
        "candidate_observation": candidate.observation.value,
        "reference_value": str(reference.value) if reference.value is not None else None,
        "candidate_value": str(candidate.value) if candidate.value is not None else None,
        "exact": reference.observation is candidate.observation
        and reference.value == candidate.value,
    }


def main() -> int:
    args = _parse_args()
    native_rows = _native_rows(args.source_pdf, args.page, args.geometry_config)
    header, vlm_rows, excluded_rows = _vlm_rows(args.vlm_result)
    alignment = align_ordered_reader_rows(native_rows, vlm_rows)
    actions = Counter(step.action for step in alignment)
    comparisons = []
    for step in alignment:
        record: dict[str, object] = {
            "action": step.action,
            "reference_indices": list(step.reference_indices),
            "candidate_indices": list(step.candidate_indices),
        }
        if step.reference is not None:
            record["reference_label"] = step.reference.label
        if step.candidate is not None:
            record["candidate_label"] = step.candidate.label
        if step.reference is not None and step.candidate is not None:
            cells = [
                _cell_record(reference, candidate)
                for reference, candidate in zip(step.reference.cells, step.candidate.cells, strict=False)
            ]
            record.update(
                label_exact=step.label_exact,
                semantic_key_exact=step.semantic_key_exact,
                semantic_similarity=step.semantic_similarity,
                reference_note=step.reference.note_reference,
                candidate_note=step.candidate.note_reference,
                note_exact=step.reference.note_reference == step.candidate.note_reference,
                cells=cells,
                cell_width_exact=len(step.reference.cells) == len(step.candidate.cells),
            )
        comparisons.append(record)

    matched = [record for record in comparisons if "label_exact" in record]
    cells = [cell for record in matched for cell in record["cells"]]
    note_records = [
        record
        for record in matched
        if record["reference_note"] is not None or record["candidate_note"] is not None
    ]
    metric_payloads = [
        {
            "path": metric_path.as_posix(),
            "sha256": sha256_file(metric_path),
            "result": json.loads(metric_path.read_text(encoding="utf-8")),
        }
        for metric_path in args.benchmark_metric
    ]
    payload = {
        "experiment_id": "E-0007",
        "status": "PASS_RUNTIME_WITH_READER_DISAGREEMENTS",
        "dataset_role": "LOGIC_DEVELOPMENT",
        "source": {
            "path": args.source_pdf.as_posix(),
            "sha256": sha256_file(args.source_pdf),
            "page": args.page,
        },
        "input_image": {
            "path": args.input_image.as_posix(),
            "sha256": sha256_file(args.input_image),
            "dpi": 200,
            "width": 1700,
            "height": 2200,
        },
        "runtime_manifest": {
            "path": args.runtime_manifest.as_posix(),
            "sha256": sha256_file(args.runtime_manifest),
        },
        "package_freeze": {
            "path": args.package_freeze.as_posix(),
            "sha256": sha256_file(args.package_freeze),
        },
        "inference_config": {
            "path": args.inference_config.as_posix(),
            "sha256": sha256_file(args.inference_config),
        },
        "geometry_config": {
            "path": args.geometry_config.as_posix(),
            "sha256": sha256_file(args.geometry_config),
        },
        "vlm_result": {
            "path": args.vlm_result.as_posix(),
            "sha256": sha256_file(args.vlm_result),
            "header": header,
        },
        "benchmark_attempts": metric_payloads,
        "algorithm_files_sha256": {
            "src/bctc_ai/validation/reader_agreement.py": sha256_file(
                Path("src/bctc_ai/validation/reader_agreement.py")
            ),
            "scripts/experiments/evaluate_paddleocr_vl_fixture.py": sha256_file(
                Path("scripts/experiments/evaluate_paddleocr_vl_fixture.py")
            ),
        },
        "counts": {
            "native_financial_rows": len(native_rows),
            "vlm_rows_inside_financial_span": len(vlm_rows),
            "vlm_rows_excluded_outside_financial_span": len(excluded_rows),
            "alignment_actions": dict(sorted(actions.items())),
            "matched_logical_rows": len(matched),
            "source_exact_labels": sum(record["label_exact"] for record in matched),
            "semantic_key_exact_labels": sum(record["semantic_key_exact"] for record in matched),
            "reference_or_candidate_note_rows": len(note_records),
            "exact_note_references": sum(record["note_exact"] for record in note_records),
            "compared_cells": len(cells),
            "exact_cells": sum(cell["exact"] for cell in cells),
        },
        "excluded_vlm_rows": excluded_rows,
        "alignment": comparisons,
        "interpretation": [
            "The complete PP-DocLayoutV3 plus PaddleOCR-VL-1.6 Transformers pipeline runs on the RTX 5070 Ti.",
            "Ordered alignment proposed one two-row-to-one-row merge for a wrapped financial label; values and notes were excluded from the alignment score.",
            "Diacritic-sensitive label comparison remains separate from accent-stripped semantic matching so OCR spelling errors cannot disappear during normalization.",
            "This is a logic-development cross-reader experiment, not ground-truth accuracy or model approval.",
        ],
    }
    atomic_write_json(args.output, payload)
    print(json.dumps(payload["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
