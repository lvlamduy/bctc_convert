from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.row_reconstruction_benchmark import (
    summarize_reconstructed_page,
)
from bctc_ai.evaluation.word_box_rows_v4 import (
    geometry_row_v4_to_dict,
    load_word_box_reconstruction_v4_config,
    parse_ppocrv6_word_box_page_v4,
)


class NoteRowSplitBenchmarkError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _resolve(project_root: Path, value: str | Path, name: str) -> Path:
    raw = Path(value)
    path = (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if not path.is_relative_to(project_root):
        raise NoteRowSplitBenchmarkError(f"{name} escapes project root")
    return path


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NoteRowSplitBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise NoteRowSplitBenchmarkError(f"{name} must be an object")
    return payload


def _load_yaml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NoteRowSplitBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise NoteRowSplitBenchmarkError(f"{name} must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise NoteRowSplitBenchmarkError(f"required artifact is absent: {path}")
    return {
        "path": path.relative_to(project_root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _verify_record(
    project_root: Path, record: object, name: str
) -> tuple[Path, dict[str, Any]]:
    if not isinstance(record, dict):
        raise NoteRowSplitBenchmarkError(f"invalid frozen record: {name}")
    path = _resolve(project_root, str(record.get("path", "")), name)
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise NoteRowSplitBenchmarkError(f"frozen input drifted: {name}")
    return path, _artifact(project_root, path)


def _cell_fingerprint(row: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            cell.get("raw_text"),
            cell.get("normalized_text"),
            cell.get("observation"),
            cell.get("value"),
            cell.get("sign_evidence"),
        )
        for cell in row.get("cells", [])
    )


def compare_row_contracts(
    before_pages: list[dict[str, Any]], after_pages: list[dict[str, Any]]
) -> dict[str, Any]:
    before_rows = [row for page in before_pages for row in page.get("rows", [])]
    after_rows = [row for page in after_pages for row in page.get("rows", [])]
    before = {tuple(row["source_row_ids"]): row for row in before_rows}
    after = {tuple(row["source_row_ids"]): row for row in after_rows}
    if len(before) != len(before_rows) or len(after) != len(after_rows):
        raise NoteRowSplitBenchmarkError("row source identities are duplicated")
    common = sorted(before.keys() & after.keys())
    removed = sorted(before.keys() - after.keys())
    replacements = sorted(after.keys() - before.keys())
    unchanged = [key for key in common if before[key] == after[key]]
    before_lines = {source for key in before for source in key}
    after_lines = {source for key in after for source in key}

    partitions = []
    preserved_value_partitions = 0
    for removed_key in removed:
        removed_set = set(removed_key)
        members = [key for key in replacements if set(key).issubset(removed_set)]
        member_union = {source for key in members for source in key}
        if len(members) == 2 and member_union == removed_set:
            preserved = sum(
                _cell_fingerprint(after[key]) == _cell_fingerprint(before[removed_key])
                for key in members
            )
            preserved_value_partitions += preserved == 1
            partitions.append(
                {
                    "removed_source_row_ids": list(removed_key),
                    "replacement_source_row_ids": [list(key) for key in members],
                    "exactly_one_replacement_preserves_old_cells": preserved == 1,
                }
            )
    return {
        "before_row_count": len(before_rows),
        "after_row_count": len(after_rows),
        "common_row_count": len(common),
        "unchanged_common_row_count": len(unchanged),
        "changed_common_row_count": len(common) - len(unchanged),
        "removed_composite_row_count": len(removed),
        "replacement_row_count": len(replacements),
        "partitioned_split_count": len(partitions),
        "preserved_value_cell_split_count": preserved_value_partitions,
        "before_source_line_count": len(before_lines),
        "after_source_line_count": len(after_lines),
        "source_line_coverage_delta_count": len(before_lines ^ after_lines),
        "partitions": partitions,
        "removed_rows": [before[key] for key in removed],
        "replacement_rows": [after[key] for key in replacements],
    }


def capture_e0032_note_row_split_benchmark(
    project_root: Path,
    *,
    experiment_config_path: Path,
    batch_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise NoteRowSplitBenchmarkError("formal E-0032 capture requires clean Git code")
    output = _resolve(project_root, output_path, "output")
    if not output.is_relative_to((project_root / "docs" / "experiments").resolve()):
        raise NoteRowSplitBenchmarkError("output must remain in docs/experiments")
    if output.exists():
        raise NoteRowSplitBenchmarkError(f"refusing to overwrite capture: {output}")

    experiment_path = _resolve(project_root, experiment_config_path, "experiment config")
    experiment = _load_yaml(experiment_path, "E-0032 experiment config")
    if (
        experiment.get("version") != 1
        or experiment.get("experiment_id") != "E-0032"
        or experiment.get("dataset_role") != "CALIBRATION"
        or experiment.get("design") != "REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT_BEFORE_AFTER"
    ):
        raise NoteRowSplitBenchmarkError("E-0032 experiment identity drifted")
    source = experiment.get("source")
    frozen = experiment.get("frozen_inputs")
    candidate = experiment.get("candidate")
    acceptance = experiment.get("acceptance_policy")
    if not all(isinstance(item, dict) for item in (source, frozen, candidate, acceptance)):
        raise NoteRowSplitBenchmarkError("E-0032 controls are incomplete")
    source_path = _resolve(project_root, source["path"], "source")
    if (
        not source_path.is_file()
        or source_path.stat().st_size != int(source["size_bytes"])
        or sha256_file(source_path) != source["sha256"]
    ):
        raise NoteRowSplitBenchmarkError("E-0032 source identity drifted")

    paths: dict[str, Path] = {}
    verified: dict[str, dict[str, Any]] = {}
    for name, record in frozen.items():
        paths[name], verified[name] = _verify_record(project_root, record, name)
    for name in ("config", "algorithm", "inherited_v3_algorithm"):
        paths[name], verified[name] = _verify_record(project_root, candidate.get(name), name)
    before = _load_json(paths["e0029_row_contract"], "E-0029 row contract")
    if (
        before.get("status") != "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION"
        or [page.get("page") for page in before.get("after", [])] != source["target_pages"]
    ):
        raise NoteRowSplitBenchmarkError("E-0029 row contract drifted")

    batch_path = _resolve(project_root, batch_root, "OCR batch")
    if batch_path / "batch_manifest.json" != paths["ocr_batch"]:
        raise NoteRowSplitBenchmarkError("E-0032 batch path differs from frozen input")
    batch = _load_json(paths["ocr_batch"], "OCR batch manifest")
    page_records = {int(record["page"]): record for record in batch.get("pages", [])}
    render_records = {int(record["page"]): record for record in batch.get("renders", [])}
    target_pages = [int(page) for page in source["target_pages"]]
    config = load_word_box_reconstruction_v4_config(paths["config"])
    target_artifacts = []
    after_pages = []
    for page in target_pages:
        page_record = page_records.get(page)
        render_record = render_records.get(page)
        if not isinstance(page_record, dict) or not isinstance(render_record, dict):
            raise NoteRowSplitBenchmarkError("E-0032 target artifacts are incomplete")
        ocr_path = batch_path / page_record["ocr_result"]["path"]
        render_path = _resolve(project_root, render_record["path"], "render")
        for path, record in ((ocr_path, page_record["ocr_result"]), (render_path, render_record)):
            if (
                not path.is_file()
                or path.stat().st_size != int(record["size_bytes"])
                or sha256_file(path) != record["sha256"]
            ):
                raise NoteRowSplitBenchmarkError(f"page artifact drifted: {path}")
            target_artifacts.append(_artifact(project_root, path))
        parsed = parse_ppocrv6_word_box_page_v4(
            ocr_path,
            config,
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
        rows = [geometry_row_v4_to_dict(row) for row in parsed.rows]
        after_pages.append(
            {
                "page": page,
                "axes": axes,
                "note_right_edge": parsed.note_right_edge,
                "index_band": asdict(parsed.index_band) if parsed.index_band else None,
                "table_bbox": list(parsed.table_bbox),
                "line_height": parsed.line_height,
                "summary": summarize_reconstructed_page(
                    page=page,
                    axes=axes,
                    rows=rows,
                    trailing_row_count=len(parsed.trailing_context_rows),
                    unassigned_numeric_line_indices=list(
                        parsed.unassigned_numeric_line_indices
                    ),
                ),
                "rows": rows,
                "trailing_rows": [
                    geometry_row_v4_to_dict(row) for row in parsed.trailing_context_rows
                ],
                "excluded_after_table_line_indices": list(
                    parsed.excluded_after_table_line_indices
                ),
            }
        )

    comparison = compare_row_contracts(before["after"], after_pages)
    by_page = {str(page["page"]): page["summary"] for page in after_pages}
    expected_observations = {
        str(page): value
        for page, value in acceptance["exact_observation_counts_by_page"].items()
    }
    gates = {
        "exact_page_set": [page["page"] for page in after_pages]
        == acceptance["exact_page_set"],
        "exact_rows_by_page": all(
            by_page[str(page)]["row_count"] == int(acceptance["exact_rows_by_page"][page])
            for page in target_pages
        ),
        "exact_cells_by_page": all(
            by_page[str(page)]["cell_count"] == int(acceptance["exact_cells_by_page"][page])
            for page in target_pages
        ),
        "exact_observation_counts_by_page": all(
            by_page[str(page)]["observation_counts"] == expected_observations[str(page)]
            for page in target_pages
        ),
        "exact_common_row_count": comparison["common_row_count"]
        == int(acceptance["exact_common_row_count"]),
        "all_common_rows_unchanged": comparison["unchanged_common_row_count"]
        == int(acceptance["exact_unchanged_common_row_count"]),
        "exact_removed_composite_row_count": comparison["removed_composite_row_count"]
        == int(acceptance["exact_removed_composite_row_count"]),
        "exact_replacement_row_count": comparison["replacement_row_count"]
        == int(acceptance["exact_replacement_row_count"]),
        "exact_partitioned_split_count": comparison["partitioned_split_count"]
        == int(acceptance["exact_partitioned_split_count"]),
        "exact_preserved_value_cell_split_count": comparison[
            "preserved_value_cell_split_count"
        ]
        == int(acceptance["exact_preserved_value_cell_split_count"]),
        "zero_source_line_coverage_delta": comparison["source_line_coverage_delta_count"]
        == int(acceptance["source_line_coverage_delta_count"]),
        "zero_invalid_cells": sum(item["invalid_cell_count"] for item in by_page.values())
        == int(acceptance["invalid_cell_count"]),
        "zero_duplicate_source_lines": sum(
            item["duplicate_source_line_assignment_count"] for item in by_page.values()
        )
        == int(acceptance["duplicate_source_line_assignment_count"]),
        "off_balance_page_not_reconstructed": 5 not in [page["page"] for page in after_pages],
    }
    result = {
        "format_version": 1,
        "experiment_id": "E-0032",
        "dataset_role": "CALIBRATION",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "experiment_config": _artifact(project_root, experiment_path),
        "source": _artifact(project_root, source_path),
        "verified_inputs": verified,
        "target_artifacts": target_artifacts,
        "before": before["after"],
        "after": after_pages,
        "comparison": comparison,
        "gates": gates,
        "reference_isolation": {
            "human_review_loaded": False,
            "historical_or_mongodb_values_loaded": False,
            "template_labels_or_report_norm_ids_loaded": False,
            "label_text_or_semantics_used_as_split_feature": False,
            "numeric_value_or_magnitude_used_as_split_feature": False,
            "e0022_evidence_loaded": False,
            "off_balance_page_5_loaded": False,
            "semantic_reader_invoked": False,
            "period_role_assignment_invoked": False,
            "schema_mapping_invoked": False,
            "accounting_validation_invoked": False,
            "excel_export_invoked": False,
        },
        "development_note": experiment["development_note"],
        "claim_boundary": experiment["claim_boundary"],
        "status": (
            "PASS_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT"
            if all(gates.values())
            else "FAIL_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT"
        ),
    }
    atomic_write_json(output, result)
    return result


__all__ = [
    "NoteRowSplitBenchmarkError",
    "capture_e0032_note_row_split_benchmark",
    "compare_row_contracts",
]
