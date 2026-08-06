from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.word_box_rows import WordBoxReconstructionError
from bctc_ai.evaluation.word_box_rows_v2 import (
    load_word_box_reconstruction_v2_config,
    parse_ppocrv6_word_box_page_v2,
)
from bctc_ai.evaluation.word_box_rows_v3 import (
    geometry_row_v3_to_dict,
    load_word_box_reconstruction_v3_config,
    parse_ppocrv6_word_box_page_v3,
)


class RowReconstructionBenchmarkError(RuntimeError):
    pass


_NOTE_PREFIX = re.compile(
    r"^(?:(?:[ivxlcdm]+|[iIlL1/|]{1,8})[.]\d+(?:[.]\d+)*|\d+(?:[.]\d+)*)\s+",
    re.IGNORECASE,
)


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _resolve(project_root: Path, value: str | Path, name: str) -> Path:
    value_path = Path(value)
    path = (
        (project_root / value_path).resolve()
        if not value_path.is_absolute()
        else value_path.resolve()
    )
    if not path.is_relative_to(project_root):
        raise RowReconstructionBenchmarkError(f"{name} escapes project root")
    return path


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RowReconstructionBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise RowReconstructionBenchmarkError(f"{name} must be an object")
    return payload


def _load_yaml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RowReconstructionBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise RowReconstructionBenchmarkError(f"{name} must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RowReconstructionBenchmarkError(f"required artifact is absent: {path}")
    return {
        "path": path.resolve().relative_to(project_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _verify_record(project_root: Path, record: object, name: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(record, dict):
        raise RowReconstructionBenchmarkError(f"invalid frozen record: {name}")
    path = _resolve(project_root, str(record.get("path", "")), name)
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise RowReconstructionBenchmarkError(f"frozen input drifted: {name}")
    return path, _artifact(project_root, path)


def summarize_reconstructed_page(
    *,
    page: int,
    axes: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    trailing_row_count: int,
    unassigned_numeric_line_indices: list[int],
) -> dict[str, Any]:
    observations = Counter(cell["observation"] for row in rows for cell in row.get("cells", []))
    source_ids = [source_id for row in rows for source_id in row.get("source_row_ids", [])]
    note_count = sum(bool(row.get("note_reference")) for row in rows)
    header_leaks = sum(
        retrieval_key(str(row.get("label", ""))) in {"minh", "thuyet", "thuyet minh"}
        for row in rows
    )
    note_prefix_leaks = sum(bool(_NOTE_PREFIX.match(str(row.get("label", "")))) for row in rows)
    return {
        "page": page,
        "axis_headers_left_to_right": [axis["raw_header"] for axis in axes],
        "row_count": len(rows),
        "trailing_row_count": trailing_row_count,
        "cell_count": sum(len(row.get("cells", [])) for row in rows),
        "rows_with_exactly_two_cells": sum(len(row.get("cells", [])) == 2 for row in rows),
        "note_reference_count": note_count,
        "observation_counts": dict(sorted(observations.items())),
        "invalid_cell_count": observations.get("INVALID", 0),
        "dash_cell_count": observations.get("DASH", 0),
        "blank_cell_count": observations.get("BLANK", 0),
        "duplicate_source_line_assignment_count": len(source_ids) - len(set(source_ids)),
        "header_companion_leak_count": header_leaks,
        "note_reference_prefix_leak_count": note_prefix_leaks,
        "unassigned_numeric_line_indices": unassigned_numeric_line_indices,
        "unassigned_numeric_line_count": len(unassigned_numeric_line_indices),
    }


def capture_e0029_row_reconstruction_benchmark(
    project_root: Path,
    *,
    experiment_config_path: Path,
    batch_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise RowReconstructionBenchmarkError("formal E-0029 capture requires clean Git code")
    output = _resolve(project_root, output_path, "output")
    if not output.is_relative_to((project_root / "docs" / "experiments").resolve()):
        raise RowReconstructionBenchmarkError("output must remain in docs/experiments")
    if output.exists():
        raise RowReconstructionBenchmarkError(f"refusing to overwrite capture: {output}")

    experiment_path = _resolve(project_root, experiment_config_path, "experiment config")
    experiment = _load_yaml(experiment_path, "E-0029 experiment config")
    if (
        experiment.get("version") != 1
        or experiment.get("experiment_id") != "E-0029"
        or experiment.get("dataset_role") != "CALIBRATION"
    ):
        raise RowReconstructionBenchmarkError("E-0029 experiment identity drifted")
    source = experiment.get("source")
    if not isinstance(source, dict):
        raise RowReconstructionBenchmarkError("E-0029 source is absent")
    source_path = _resolve(project_root, str(source.get("path", "")), "source")
    if (
        not source_path.is_file()
        or source_path.stat().st_size != int(source.get("size_bytes", -1))
        or sha256_file(source_path) != source.get("sha256")
    ):
        raise RowReconstructionBenchmarkError("E-0029 source identity drifted")

    frozen = experiment.get("frozen_inputs")
    candidate = experiment.get("candidate")
    if not isinstance(frozen, dict) or not isinstance(candidate, dict):
        raise RowReconstructionBenchmarkError("E-0029 controls are incomplete")
    paths = {}
    verified = {}
    for name, record in frozen.items():
        paths[name], verified[name] = _verify_record(project_root, record, name)
    for name in ("config", "algorithm"):
        paths[name], verified[name] = _verify_record(project_root, candidate.get(name), name)

    page_contract = _load_json(paths["accepted_page_contract"], "E-0028 page contract")
    after = page_contract.get("after")
    isolation = page_contract.get("reference_isolation")
    if (
        not isinstance(after, dict)
        or after.get("mapping_eligible_pages_by_statement_type", {}).get("CDKT")
        != source["target_pages"]
        or after.get("off_balance_excluded_pages") != source["excluded_off_balance_pages"]
        or not isinstance(isolation, dict)
        or any(isolation.values())
    ):
        raise RowReconstructionBenchmarkError("E-0028 page/isolation contract drifted")

    batch_path = _resolve(project_root, batch_root, "OCR batch")
    if (batch_path / "batch_manifest.json").resolve() != paths["ocr_batch"]:
        raise RowReconstructionBenchmarkError("E-0029 batch path differs from frozen input")
    batch = _load_json(paths["ocr_batch"], "OCR batch manifest")
    if batch.get("source") != {
        "path": source["path"],
        "sha256": source["sha256"],
        "size_bytes": source["size_bytes"],
    }:
        raise RowReconstructionBenchmarkError("E-0029 OCR source identity drifted")
    page_records = {
        int(record["page"]): record
        for record in batch.get("pages", [])
        if isinstance(record, dict) and int(record.get("page", -1)) in source["target_pages"]
    }
    render_records = {
        int(record["page"]): record
        for record in batch.get("renders", [])
        if isinstance(record, dict) and int(record.get("page", -1)) in source["target_pages"]
    }
    if set(page_records) != set(source["target_pages"]) or set(render_records) != set(
        source["target_pages"]
    ):
        raise RowReconstructionBenchmarkError("E-0029 target page artifacts are incomplete")

    v2_config = load_word_box_reconstruction_v2_config(paths["v2_config"])
    v3_config = load_word_box_reconstruction_v3_config(paths["config"])
    before_records = []
    after_records = []
    target_artifacts = []
    for page in source["target_pages"]:
        page_record = page_records[page]
        render_record = render_records[page]
        ocr_path = batch_path / page_record["ocr_result"]["path"]
        render_path = _resolve(project_root, render_record["path"], f"page {page} render")
        for path, expected_sha, expected_size in (
            (
                ocr_path,
                page_record["ocr_result"]["sha256"],
                page_record["ocr_result"]["size_bytes"],
            ),
            (render_path, render_record["sha256"], render_record["size_bytes"]),
        ):
            if (
                not path.is_file()
                or path.stat().st_size != int(expected_size)
                or sha256_file(path) != expected_sha
            ):
                raise RowReconstructionBenchmarkError(f"page {page} artifact drifted: {path}")
            target_artifacts.append(_artifact(project_root, path))
        try:
            parse_ppocrv6_word_box_page_v2(
                ocr_path,
                v2_config,
                page_tag=f"page-{page:04d}",
                source_image_path=render_path,
            )
        except WordBoxReconstructionError as exc:
            before_records.append({"page": page, "status": "FAILED_CLOSED", "error": str(exc)})
        else:
            before_records.append({"page": page, "status": "PARSED", "error": None})

        parsed = parse_ppocrv6_word_box_page_v3(
            ocr_path,
            v3_config,
            page_tag=f"page-{page:04d}",
            source_image_path=render_path,
        )
        axes = [
            {
                "axis_id": axis.axis_id,
                "raw_header": axis.raw_header,
                "right_edge": axis.right_edge,
                "header_line_index": axis.header_line_index,
            }
            for axis in parsed.axes
        ]
        rows = [geometry_row_v3_to_dict(row) for row in parsed.rows]
        summary = summarize_reconstructed_page(
            page=page,
            axes=axes,
            rows=rows,
            trailing_row_count=len(parsed.trailing_context_rows),
            unassigned_numeric_line_indices=list(parsed.unassigned_numeric_line_indices),
        )
        after_records.append(
            {
                "page": page,
                "axes": axes,
                "note_right_edge": parsed.note_right_edge,
                "index_band": asdict(parsed.index_band) if parsed.index_band else None,
                "table_bbox": list(parsed.table_bbox),
                "line_height": parsed.line_height,
                "summary": summary,
                "rows": rows,
                "trailing_rows": [
                    geometry_row_v3_to_dict(row) for row in parsed.trailing_context_rows
                ],
                "excluded_after_table_line_indices": list(parsed.excluded_after_table_line_indices),
            }
        )

    acceptance = experiment["acceptance_policy"]
    by_page = {record["page"]: record["summary"] for record in after_records}
    gates = {
        "v2_failed_closed_on_both_pages": all(
            record["status"] == "FAILED_CLOSED"
            and record["error"] == acceptance["v2_failure_on_both_pages"]
            for record in before_records
        ),
        "axis_headers_exact": all(
            by_page[page]["axis_headers_left_to_right"]
            == acceptance["exact_axis_headers_left_to_right"]
            for page in source["target_pages"]
        ),
        "minimum_rows_met": all(
            by_page[page]["row_count"] >= int(acceptance["minimum_rows_by_page"][page])
            for page in source["target_pages"]
        ),
        "minimum_note_references_met": all(
            by_page[page]["note_reference_count"]
            >= int(acceptance["minimum_note_references_by_page"][page])
            for page in source["target_pages"]
        ),
        "unassigned_numeric_within_bound": all(
            by_page[page]["unassigned_numeric_line_count"]
            <= int(acceptance["maximum_unassigned_numeric_lines_by_page"][page])
            for page in source["target_pages"]
        ),
        "exactly_two_cells_per_row": all(
            summary["rows_with_exactly_two_cells"] == summary["row_count"]
            for summary in by_page.values()
        ),
        "zero_invalid_cells": sum(summary["invalid_cell_count"] for summary in by_page.values())
        == int(acceptance["invalid_cell_count"]),
        "zero_duplicate_source_lines": sum(
            summary["duplicate_source_line_assignment_count"] for summary in by_page.values()
        )
        == int(acceptance["duplicate_source_line_assignment_count"]),
        "zero_header_companion_leaks": sum(
            summary["header_companion_leak_count"] for summary in by_page.values()
        )
        == int(acceptance["header_companion_leak_count"]),
        "zero_note_prefix_leaks": sum(
            summary["note_reference_prefix_leak_count"] for summary in by_page.values()
        )
        == int(acceptance["note_reference_prefix_leak_count"]),
        "off_balance_page_not_reconstructed": all(
            record["page"] not in source["excluded_off_balance_pages"] for record in after_records
        ),
    }
    passed = all(gates.values())
    payload = {
        "format_version": 1,
        "experiment_id": "E-0029",
        "status": (
            "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION"
            if passed
            else "FAIL_REFERENCE_BLIND_ROW_RECONSTRUCTION"
        ),
        "dataset_role": "CALIBRATION",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "experiment_config": _artifact(project_root, experiment_path),
        "source": _artifact(project_root, source_path),
        "verified_inputs": verified,
        "target_artifacts": target_artifacts,
        "before": before_records,
        "after": after_records,
        "gates": gates,
        "reference_isolation": {
            "human_review_loaded": False,
            "historical_values_loaded": False,
            "template_labels_loaded": False,
            "report_norm_ids_loaded": False,
            "e0022_evidence_loaded": False,
            "off_balance_page_5_loaded": False,
            "semantic_reader_invoked": False,
            "period_role_assignment_invoked": False,
            "mapping_invoked": False,
            "accounting_validation_invoked": False,
            "excel_export_invoked": False,
        },
        "benchmark_implementation": _artifact(project_root, Path(__file__).resolve()),
        "claim_boundary": experiment["claim_boundary"],
    }
    atomic_write_json(output, payload)
    return payload
