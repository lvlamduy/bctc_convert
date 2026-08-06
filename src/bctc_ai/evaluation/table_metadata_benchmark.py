from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.axes.period_propagation_v1 import (
    PeriodBindingMode,
    PeriodTableInput,
    ValueAxisPosition,
    load_period_propagation_policy,
    propagate_table_periods,
)
from bctc_ai.axes.word_box_header_binding import (
    BoundWordBoxAxis,
    bind_word_box_visible_headers,
    load_word_box_header_binding_policy,
)
from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.word_box_rows_v3 import (
    load_word_box_reconstruction_v3_config,
    parse_ppocrv6_word_box_page_v3,
)


class TableMetadataBenchmarkError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _resolve(project_root: Path, value: str | Path, name: str) -> Path:
    raw = Path(value)
    path = (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if not path.is_relative_to(project_root):
        raise TableMetadataBenchmarkError(f"{name} escapes project root")
    return path


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TableMetadataBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise TableMetadataBenchmarkError(f"{name} must be an object")
    return payload


def _load_yaml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TableMetadataBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise TableMetadataBenchmarkError(f"{name} must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise TableMetadataBenchmarkError(f"required artifact is absent: {path}")
    return {
        "path": path.relative_to(project_root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _verify_record(project_root: Path, record: object, name: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(record, dict):
        raise TableMetadataBenchmarkError(f"invalid frozen record: {name}")
    path = _resolve(project_root, str(record.get("path", "")), name)
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise TableMetadataBenchmarkError(f"frozen input drifted: {name}")
    return path, _artifact(project_root, path)


def _axis_record(axis: BoundWordBoxAxis) -> dict[str, Any]:
    return {
        "ordinal": axis.ordinal,
        "axis_id": axis.axis_id,
        "axis_right_edge": axis.axis_right_edge,
        "header_line_index": axis.header_line_index,
        "raw_period_header": axis.raw_period_header,
        "header_bbox": list(asdict(axis.header_bbox).values()),
        "period_start": axis.period_start.isoformat(),
        "period_end": axis.period_end.isoformat(),
        "period_type": axis.period_type,
        "current_or_comparative": axis.current_or_comparative,
        "raw_unit_text": axis.raw_unit_text,
        "unit_line_index": axis.unit_line_index,
        "unit_bbox": list(asdict(axis.unit_bbox).values()),
        "canonical_unit": axis.canonical_unit,
        "unit_multiplier": axis.unit_multiplier,
        "matched_unit_anchor": axis.matched_unit_anchor,
        "unit_similarity": axis.unit_similarity,
        "distinct_semantics_margin": axis.distinct_semantics_margin,
        "evidence": list(axis.evidence),
    }


def _expected_axis_projection(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "axis_id": record["axis_id"],
        "raw_period_header": record["raw_period_header"],
        "period_end": record["period_end"],
        "role": record["current_or_comparative"],
        "raw_unit_text": record["raw_unit_text"],
        "canonical_unit": record["canonical_unit"],
        "unit_multiplier": record["unit_multiplier"],
    }


def capture_e0030_table_metadata_benchmark(
    project_root: Path,
    *,
    experiment_config_path: Path,
    batch_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise TableMetadataBenchmarkError("formal E-0030 capture requires clean Git code")
    output = _resolve(project_root, output_path, "output")
    if not output.is_relative_to((project_root / "docs" / "experiments").resolve()):
        raise TableMetadataBenchmarkError("output must remain in docs/experiments")
    if output.exists():
        raise TableMetadataBenchmarkError(f"refusing to overwrite capture: {output}")

    experiment_path = _resolve(project_root, experiment_config_path, "experiment config")
    experiment = _load_yaml(experiment_path, "E-0030 experiment config")
    if (
        experiment.get("version") != 1
        or experiment.get("experiment_id") != "E-0030"
        or experiment.get("dataset_role") != "CALIBRATION"
    ):
        raise TableMetadataBenchmarkError("E-0030 experiment identity drifted")
    source = experiment.get("source")
    frozen = experiment.get("frozen_inputs")
    candidate = experiment.get("candidate")
    if not all(isinstance(value, dict) for value in (source, frozen, candidate)):
        raise TableMetadataBenchmarkError("E-0030 controls are incomplete")

    paths: dict[str, Path] = {}
    verified: dict[str, dict[str, Any]] = {}
    for name, record in frozen.items():
        paths[name], verified[name] = _verify_record(project_root, record, name)
    for name in ("config", "algorithm"):
        paths[name], verified[name] = _verify_record(project_root, candidate.get(name), name)

    e0029 = _load_json(paths["e0029_row_contract"], "E-0029 row contract")
    if (
        e0029.get("status") != "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION"
        or [record.get("page") for record in e0029.get("after", [])] != source["target_pages"]
        or e0029.get("reference_isolation", {}).get("off_balance_page_5_loaded") is not False
    ):
        raise TableMetadataBenchmarkError("E-0029 page/row contract drifted")

    batch_path = _resolve(project_root, batch_root, "OCR batch")
    if (batch_path / "batch_manifest.json").resolve() != paths["ocr_batch"]:
        raise TableMetadataBenchmarkError("E-0030 batch path differs from frozen input")
    batch = _load_json(paths["ocr_batch"], "OCR batch manifest")
    target_pages = [int(value) for value in source["target_pages"]]
    page_records = {
        int(record["page"]): record
        for record in batch.get("pages", [])
        if isinstance(record, dict) and int(record.get("page", -1)) in target_pages
    }
    render_records = {
        int(record["page"]): record
        for record in batch.get("renders", [])
        if isinstance(record, dict) and int(record.get("page", -1)) in target_pages
    }
    if set(page_records) != set(target_pages) or set(render_records) != set(target_pages):
        raise TableMetadataBenchmarkError("E-0030 target artifacts are incomplete")

    row_policy = load_word_box_reconstruction_v3_config(paths["row_config"])
    header_policy = load_word_box_header_binding_policy(paths["config"])
    propagation_policy = load_period_propagation_policy(paths["period_propagation_policy"])
    target_artifacts = []
    page_outputs = []
    table_inputs = []
    for table_order, page in enumerate(target_pages):
        page_record = page_records[page]
        render_record = render_records[page]
        ocr_path = (batch_path / page_record["ocr_result"]["path"]).resolve()
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
                raise TableMetadataBenchmarkError(f"page {page} artifact drifted: {path}")
            target_artifacts.append(_artifact(project_root, path))
        geometry = parse_ppocrv6_word_box_page_v3(
            ocr_path,
            row_policy,
            page_tag=f"page-{page:04d}",
            source_image_path=render_path,
        )
        bound = bind_word_box_visible_headers(
            ocr_path,
            geometry,
            header_policy,
            statement_type=str(source["statement_type"]),
        )
        image = cv2.imread(str(render_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise TableMetadataBenchmarkError(f"cannot read page {page} render")
        width = image.shape[1]
        table_id = f"mbb-cdkt-p{page}"
        table_inputs.append(
            PeriodTableInput(
                table_id=table_id,
                page=page,
                table_order=table_order,
                statement_instance_id=str(source["statement_instance_id"]),
                statement_type=str(source["statement_type"]),
                scope=str(source["scope"]),
                value_axes=tuple(
                    ValueAxisPosition(axis.axis_id, axis.axis_right_edge / width)
                    for axis in bound.axes
                ),
                local_bindings=bound.header_bindings,
            )
        )
        page_outputs.append(
            {
                "page": page,
                "table_id": table_id,
                "axes": [_axis_record(axis) for axis in bound.axes],
                "table_evidence": list(bound.evidence),
            }
        )

    propagation = propagate_table_periods(
        table_inputs,
        accepted_continuations=set(),
        policy=propagation_policy,
    )
    maps = propagation.by_table_id()
    for page_record in page_outputs:
        table_map = maps.get(page_record["table_id"])
        page_record["binding_mode"] = (
            table_map.binding_mode.value if table_map is not None else None
        )
        page_record["period_map_columns"] = (
            [
                {
                    "ordinal": column.ordinal,
                    "axis_id": column.axis_id,
                    "period_end": column.period_end.isoformat(),
                    "current_or_comparative": column.current_or_comparative,
                    "unit": column.unit,
                    "unit_multiplier": column.unit_multiplier,
                    "source_header_page": column.source_header_page,
                }
                for column in table_map.columns
            ]
            if table_map is not None
            else []
        )

    expected = experiment.get("expected_visible_bindings")
    if not isinstance(expected, dict):
        raise TableMetadataBenchmarkError("E-0030 expected visible bindings are absent")
    actual_projection = {
        str(record["page"]): [_expected_axis_projection(axis) for axis in record["axes"]]
        for record in page_outputs
    }
    expected_projection = {str(page): records for page, records in expected.items()}
    all_axes = [axis for page in page_outputs for axis in page["axes"]]
    gates = {
        "exact_page_set": [record["page"] for record in page_outputs]
        == experiment["acceptance_policy"]["exact_page_set"],
        "exact_axis_count": len(all_axes)
        == int(experiment["acceptance_policy"]["exact_axis_count"]),
        "exact_visible_bindings": actual_projection == expected_projection,
        "minimum_unit_similarity": all(
            axis["unit_similarity"]
            >= float(experiment["acceptance_policy"]["minimum_unit_similarity"])
            for axis in all_axes
        ),
        "minimum_distinct_semantics_margin": all(
            axis["distinct_semantics_margin"]
            >= float(experiment["acceptance_policy"]["minimum_distinct_semantics_margin"])
            for axis in all_axes
        ),
        "local_visible_header_binding_only": all(
            record["binding_mode"] == PeriodBindingMode.LOCAL_VISIBLE_HEADERS.value
            for record in page_outputs
        ),
        "zero_propagation_issues": len(propagation.unresolved)
        == int(experiment["acceptance_policy"]["propagation_issue_count"]),
        "off_balance_page_not_loaded": 5 not in [record["page"] for record in page_outputs],
    }
    isolation = {
        "human_review_loaded": False,
        "historical_or_mongodb_values_loaded": False,
        "template_labels_or_report_norm_ids_loaded": False,
        "numeric_cell_text_or_value_used_as_period_unit_feature": False,
        "numeric_value_magnitude_used": False,
        "horizontal_position_used_as_period_role": False,
        "continuation_inheritance_used": False,
        "e0022_evidence_loaded": False,
        "off_balance_page_5_loaded": False,
        "schema_mapping_invoked": False,
        "accounting_validation_invoked": False,
        "excel_export_invoked": False,
    }
    result = {
        "format_version": 1,
        "experiment_id": "E-0030",
        "dataset_role": "CALIBRATION",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "experiment_config": _artifact(project_root, experiment_path),
        "verified_inputs": verified,
        "target_artifacts": target_artifacts,
        "before": {
            "status": "NO_WORD_BOX_VISIBLE_HEADER_BINDING_CONTRACT",
            "resolved_axis_count": 0,
        },
        "after": page_outputs,
        "propagation_issues": [asdict(issue) for issue in propagation.unresolved],
        "gates": gates,
        "reference_isolation": isolation,
        "claim_boundary": experiment["claim_boundary"],
        "status": (
            "PASS_REFERENCE_BLIND_VISIBLE_HEADER_BINDING"
            if all(gates.values())
            else "FAIL_REFERENCE_BLIND_VISIBLE_HEADER_BINDING"
        ),
    }
    atomic_write_json(output, result)
    return result
