from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageOps

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file


class LogicalRowLabelCropError(RuntimeError):
    """Raised when a frozen logical-row label crop cannot be reproduced safely."""


@dataclass(frozen=True)
class LogicalRowLabelCropPolicy:
    source_padding: tuple[int, int, int, int]
    white_border: tuple[int, int, int, int]
    color_mode: str


_EXPECTED_AUTHORITY = {
    "source_render_is_pixel_authority": True,
    "e0033_is_row_and_label_geometry_authority": True,
    "e0034_numeric_cells_remain_immutable": True,
    "all_logical_rows_are_selected_before_semantic_inference": True,
    "reader_receives_crop_pixels_only": True,
    "reader_may_propose_vietnamese_label_text": True,
    "reader_may_change_geometry": False,
    "reader_may_change_numeric_value_or_status": False,
    "reader_may_assign_period_unit_scope_or_schema_id": False,
    "human_review_is_available_to_crop_builder": False,
    "template_or_history_is_available_to_crop_builder": False,
}


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise LogicalRowLabelCropError(f"unsafe project-relative path: {value!r}")
    path = (project_root / raw).resolve()
    if not path.is_relative_to(project_root):
        raise LogicalRowLabelCropError(f"path escapes project root: {value!r}")
    return path


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise LogicalRowLabelCropError(f"cannot load label-crop config: {path}") from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelCropError("label-crop config must be an object")
    return payload


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LogicalRowLabelCropError(f"cannot load {name}: {path}") from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelCropError(f"{name} must be an object")
    return payload


def _four_nonnegative_ints(value: Any, name: str) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value)
    ):
        raise LogicalRowLabelCropError(f"{name} must contain four non-negative integers")
    return tuple(value)  # type: ignore[return-value]


def _verify_file(path: Path, record: dict[str, Any], name: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise LogicalRowLabelCropError(f"required {name} is absent: {path}")
    if path.stat().st_size != int(record.get("size_bytes", -1)):
        raise LogicalRowLabelCropError(f"{name} size drifted: {path}")
    if sha256_file(path) != str(record.get("sha256", "")):
        raise LogicalRowLabelCropError(f"{name} SHA-256 drifted: {path}")


def _validate_config(config: dict[str, Any]) -> LogicalRowLabelCropPolicy:
    if (
        config.get("version") != 1
        or config.get("experiment_id") != "E-0035"
        or config.get("dataset_role") != "CALIBRATION"
        or config.get("design") != "REFERENCE_BLIND_ALL_FIXED_GRID_LOGICAL_ROW_LABEL_CROPS"
        or config.get("selection_policy")
        != "ALL_E0033_CDKT_ROWS_SELECTED_BEFORE_ANY_SEMANTIC_READER_OUTPUT"
        or config.get("authority") != _EXPECTED_AUTHORITY
    ):
        raise LogicalRowLabelCropError("E-0035 identity, selection, or authority drifted")
    statement = config.get("statement")
    expected_rows = statement.get("exact_rows_by_page") if isinstance(statement, dict) else None
    if (
        not isinstance(statement, dict)
        or statement.get("type") != "CDKT"
        or statement.get("instance_id") != "mbb-q1-2026-cdkt"
        or statement.get("target_pages") != [3, 4]
        or expected_rows != {3: 39, 4: 25}
        or statement.get("exact_row_count") != 64
    ):
        raise LogicalRowLabelCropError("E-0035 statement denominator drifted")
    policy = config.get("crop_policy")
    if (
        not isinstance(policy, dict)
        or policy.get("image_format") != "PNG"
        or policy.get("color_mode") != "RGB"
        or policy.get("resize") is not False
        or policy.get("threshold") is not False
        or policy.get("deskew") is not False
        or policy.get("horizontal_source") != "UNION_OF_E0033_LABEL_LINE_PP_OCRV6_BOXES"
        or policy.get("vertical_source") != "UNION_OF_E0033_LABEL_LINE_PP_OCRV6_BOXES"
        or policy.get("right_boundary_guard") != "STRICTLY_LEFT_OF_E0033_NOTE_RIGHT_EDGE"
    ):
        raise LogicalRowLabelCropError("E-0035 crop policy drifted")
    forbidden = config.get("forbidden_inputs")
    expected_forbidden = {
        "human_review_labels_ids_values_or_period_answers",
        "template_labels_aliases_or_report_norm_ids",
        "historical_or_mongodb_labels_or_values",
        "numeric_cell_text_value_sign_or_status",
        "period_unit_scope_or_statement_answer",
        "E_0022_source_artifacts_output_or_diagnosis",
        "off_balance_page_5",
    }
    if not isinstance(forbidden, list) or set(forbidden) != expected_forbidden:
        raise LogicalRowLabelCropError("E-0035 forbidden-input boundary drifted")
    return LogicalRowLabelCropPolicy(
        source_padding=_four_nonnegative_ints(
            policy.get("source_padding_left_top_right_bottom"), "source padding"
        ),
        white_border=_four_nonnegative_ints(
            policy.get("white_border_left_top_right_bottom"), "white border"
        ),
        color_mode="RGB",
    )


def union_label_bbox(boxes: list[Any], line_indices: list[Any]) -> tuple[int, int, int, int]:
    if not line_indices or any(
        isinstance(index, bool) or not isinstance(index, int) for index in line_indices
    ):
        raise LogicalRowLabelCropError("logical row has no valid label-line indices")
    if len(set(line_indices)) != len(line_indices):
        raise LogicalRowLabelCropError("logical row repeats a label-line index")
    selected: list[tuple[int, int, int, int]] = []
    for index in line_indices:
        try:
            raw = boxes[index]
        except (IndexError, TypeError) as error:
            raise LogicalRowLabelCropError(f"label-line index is out of range: {index}") from error
        if (
            not isinstance(raw, list)
            or len(raw) != 4
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in raw)
        ):
            raise LogicalRowLabelCropError(f"invalid PP-OCR label box at index {index}")
        box = tuple(int(round(float(value))) for value in raw)
        if box[0] >= box[2] or box[1] >= box[3]:
            raise LogicalRowLabelCropError(f"degenerate PP-OCR label box at index {index}")
        selected.append(box)  # type: ignore[arg-type]
    return (
        min(box[0] for box in selected),
        min(box[1] for box in selected),
        max(box[2] for box in selected),
        max(box[3] for box in selected),
    )


def _padded_box(
    bbox: tuple[int, int, int, int],
    padding: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    pad_left, pad_top, pad_right, pad_bottom = padding
    result = (
        max(0, left - pad_left),
        max(0, top - pad_top),
        min(image_width, right + pad_right),
        min(image_height, bottom + pad_bottom),
    )
    if result[0] >= result[2] or result[1] >= result[3]:
        raise LogicalRowLabelCropError(f"invalid padded label crop: {result}")
    return result


def _verify_recovery_seal(project_root: Path, record: dict[str, Any]) -> dict[str, Any]:
    path = _resolve(project_root, str(record.get("path", "")))
    _verify_file(path, record, "R-0001 recovery seal")
    seal = _load_json(path, "R-0001 recovery seal")
    page_evidence = seal.get("page_evidence")
    if (
        seal.get("recovery_id") != "R-0001"
        or seal.get("status") != "PASS_FUNCTIONAL_REPRODUCTION_NOT_ORIGINAL_BATCH_MANIFEST"
        or seal.get("reproduction", {}).get("original_batch_manifest_recovered") is not False
        or not isinstance(page_evidence, list)
        or {item.get("page") for item in page_evidence if isinstance(item, dict)} != {3, 4}
        or not all(
            item.get("render_byte_exact") is True
            and item.get("canonical_historical_ocr_byte_exact") is True
            for item in page_evidence
            if isinstance(item, dict)
        )
    ):
        raise LogicalRowLabelCropError("R-0001 equivalence boundary drifted")
    return {
        "path": path.relative_to(project_root).as_posix(),
        "sha256": sha256_file(path),
        "status": seal["status"],
        "original_batch_manifest_recovered": False,
    }


def capture_e0035_logical_row_label_crops(
    project_root: Path,
    *,
    config_path: Path = Path("config/experiments/e0035-mbb-cdkt-logical-row-label-crops.yaml"),
) -> dict[str, Any]:
    """Freeze one source-pixel label crop for every E-0033 logical row.

    No expected label, template, value, period, scope, history, or human-review field is
    loaded. The resulting manifest retains PP-OCR text only as primary-reader provenance;
    a downstream inference request must expose only each registered crop image.
    """

    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise LogicalRowLabelCropError("formal E-0035 crop capture requires clean Git code")
    resolved_config = _resolve(project_root, config_path.as_posix())
    config = _load_yaml(resolved_config)
    policy = _validate_config(config)
    config_sha256 = sha256_file(resolved_config)

    source_record = config.get("source")
    if not isinstance(source_record, dict):
        raise LogicalRowLabelCropError("E-0035 source identity is missing")
    source_path = _resolve(project_root, str(source_record.get("path", "")))
    _verify_file(source_path, source_record, "source PDF")

    frozen_inputs = config.get("frozen_inputs")
    if not isinstance(frozen_inputs, dict):
        raise LogicalRowLabelCropError("E-0035 frozen inputs are missing")
    required_frozen = {"e0033_row_contract", "e0034_numeric_verification", "recovery_seal"}
    if set(frozen_inputs) != required_frozen:
        raise LogicalRowLabelCropError("E-0035 frozen-input set drifted")
    row_record = frozen_inputs["e0033_row_contract"]
    numeric_record = frozen_inputs["e0034_numeric_verification"]
    if not isinstance(row_record, dict) or not isinstance(numeric_record, dict):
        raise LogicalRowLabelCropError("E-0035 frozen artifact record is invalid")
    row_path = _resolve(project_root, str(row_record.get("path", "")))
    numeric_path = _resolve(project_root, str(numeric_record.get("path", "")))
    _verify_file(row_path, row_record, "E-0033 row contract")
    _verify_file(numeric_path, numeric_record, "E-0034 numeric verification")
    recovery = _verify_recovery_seal(project_root, frozen_inputs["recovery_seal"])

    algorithm = config.get("candidate", {}).get("crop_algorithm")
    if not isinstance(algorithm, dict):
        raise LogicalRowLabelCropError("E-0035 crop algorithm identity is missing")
    algorithm_path = _resolve(project_root, str(algorithm.get("path", "")))
    _verify_file(algorithm_path, algorithm, "E-0035 crop algorithm")

    row_contract = _load_json(row_path, "E-0033 row contract")
    numeric_contract = _load_json(numeric_path, "E-0034 numeric verification")
    pages = row_contract.get("after")
    if (
        row_contract.get("experiment_id") != "E-0033"
        or row_contract.get("status") != "PASS_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT"
        or not isinstance(pages, list)
        or {item.get("page") for item in pages if isinstance(item, dict)} != {3, 4}
        or numeric_contract.get("experiment_id") != "E-0034"
        or numeric_contract.get("status") != "PASS_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
        or numeric_contract.get("after", {}).get("metrics", {}).get("cell_count") != 128
    ):
        raise LogicalRowLabelCropError("E-0033/E-0034 fixed-grid contract drifted")

    page_sources = config.get("page_sources")
    if not isinstance(page_sources, dict) or set(page_sources) != {3, 4}:
        raise LogicalRowLabelCropError("E-0035 page-source set drifted")
    resolved_sources: dict[int, dict[str, Any]] = {}
    for page in (3, 4):
        record = page_sources[page]
        if not isinstance(record, dict) or set(record) != {"render", "ocr"}:
            raise LogicalRowLabelCropError(f"invalid E-0035 page source: {page}")
        render_record = record["render"]
        ocr_record = record["ocr"]
        if not isinstance(render_record, dict) or not isinstance(ocr_record, dict):
            raise LogicalRowLabelCropError(f"invalid E-0035 page artifact: {page}")
        render_path = _resolve(project_root, str(render_record.get("path", "")))
        ocr_path = _resolve(project_root, str(ocr_record.get("path", "")))
        _verify_file(render_path, render_record, f"page {page} render")
        _verify_file(ocr_path, ocr_record, f"page {page} OCR")
        resolved_sources[page] = {
            "render_path": render_path,
            "ocr_path": ocr_path,
            "render_record": render_record,
            "ocr_record": ocr_record,
        }

    output_root = _resolve(project_root, str(config.get("output_root", "")))
    run_root = output_root / config_sha256[:20]
    if run_root.exists():
        raise LogicalRowLabelCropError(f"refusing to overwrite E-0035 crop run: {run_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{run_root.name}.", dir=output_root))
    records: list[dict[str, Any]] = []
    page_manifests: list[dict[str, Any]] = []
    try:
        crop_root = temporary / "crops"
        crop_root.mkdir()
        used_label_lines: dict[int, set[int]] = {3: set(), 4: set()}
        expected_rows = config["statement"]["exact_rows_by_page"]
        for page_record in pages:
            if not isinstance(page_record, dict):
                raise LogicalRowLabelCropError("E-0033 page record is not an object")
            page = int(page_record["page"])
            rows = page_record.get("rows")
            note_right_edge = page_record.get("note_right_edge")
            if (
                not isinstance(rows, list)
                or len(rows) != int(expected_rows[page])
                or not isinstance(note_right_edge, (int, float))
            ):
                raise LogicalRowLabelCropError(f"E-0033 row denominator drifted on page {page}")
            source = resolved_sources[page]
            ocr = _load_json(source["ocr_path"], f"page {page} PP-OCR")
            boxes = ocr.get("rec_boxes")
            texts = ocr.get("rec_texts")
            scores = ocr.get("rec_scores")
            if (
                not isinstance(boxes, list)
                or not isinstance(texts, list)
                or not isinstance(scores, list)
                or len(boxes) != len(texts)
                or len(texts) != len(scores)
            ):
                raise LogicalRowLabelCropError(f"page {page} PP-OCR arrays are incomplete")
            with Image.open(source["render_path"]) as opened:
                image = opened.convert(policy.color_mode)
                image_width, image_height = image.size
                for row_ordinal, row in enumerate(rows):
                    if not isinstance(row, dict) or not isinstance(row.get("geometry"), dict):
                        raise LogicalRowLabelCropError(
                            f"invalid E-0033 row geometry: page {page} row {row_ordinal}"
                        )
                    line_indices = row["geometry"].get("label_line_indices")
                    if not isinstance(line_indices, list):
                        raise LogicalRowLabelCropError(
                            f"invalid label-line list: page {page} row {row_ordinal}"
                        )
                    label_indices = [int(value) for value in line_indices]
                    overlap = used_label_lines[page].intersection(label_indices)
                    if overlap:
                        raise LogicalRowLabelCropError(
                            f"label lines assigned to multiple rows on page {page}: {sorted(overlap)}"
                        )
                    used_label_lines[page].update(label_indices)
                    label_bbox = union_label_bbox(boxes, label_indices)
                    crop_bbox = _padded_box(
                        label_bbox,
                        policy.source_padding,
                        image_width,
                        image_height,
                    )
                    if crop_bbox[2] >= float(note_right_edge):
                        raise LogicalRowLabelCropError(
                            f"label crop reaches note/value context: page {page} row {row_ordinal}"
                        )
                    observed_texts = [str(texts[index]) for index in label_indices]
                    observed_text = " ".join(
                        text.strip() for text in observed_texts if text.strip()
                    )
                    if observed_text != str(row.get("label", "")):
                        raise LogicalRowLabelCropError(
                            f"E-0033 label provenance drifted: page {page} row {row_ordinal}"
                        )
                    crop = image.crop(crop_bbox)
                    crop = ImageOps.expand(
                        crop,
                        border=policy.white_border,
                        fill="white",
                    )
                    sample_id = f"page-{page:04d}-row-{row_ordinal:03d}-label"
                    crop_path = crop_root / f"{sample_id}.png"
                    crop.save(crop_path, format="PNG", optimize=False)
                    records.append(
                        {
                            "sample_id": sample_id,
                            "category": "LOGICAL_ROW_LABEL",
                            "page": page,
                            "row_ordinal": row_ordinal,
                            "source_row_ids": list(row.get("source_row_ids", [])),
                            "label_line_indices": label_indices,
                            "ppocr_boxes": [list(boxes[index]) for index in label_indices],
                            "ppocr_text": observed_text,
                            "ppocr_scores": [float(scores[index]) for index in label_indices],
                            "label_union_bbox": list(label_bbox),
                            "source_crop_bbox": list(crop_bbox),
                            "note_right_edge": float(note_right_edge),
                            "crop_path": (run_root / "crops" / crop_path.name)
                            .relative_to(project_root)
                            .as_posix(),
                            "crop_width": crop.width,
                            "crop_height": crop.height,
                            "crop_sha256": sha256_file(crop_path),
                        }
                    )
            page_manifests.append(
                {
                    "page": page,
                    "row_count": len(rows),
                    "label_crop_count": sum(record["page"] == page for record in records),
                    "render": dict(source["render_record"]),
                    "ocr": dict(source["ocr_record"]),
                }
            )
        if len(records) != int(config["statement"]["exact_row_count"]):
            raise LogicalRowLabelCropError("E-0035 exact crop denominator was not met")
        if len({record["sample_id"] for record in records}) != len(records):
            raise LogicalRowLabelCropError("E-0035 sample IDs are not unique")

        manifest_path = temporary / "crop_manifest.json"
        manifest: dict[str, Any] = {
            "format_version": 1,
            "experiment_id": "E-0035",
            "state": "FROZEN_ALL_LOGICAL_ROW_LABEL_CROPS_NO_SEMANTIC_INFERENCE",
            "dataset_role": "CALIBRATION",
            "selection_policy": config["selection_policy"],
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
            "config": {
                "path": resolved_config.relative_to(project_root).as_posix(),
                "sha256": config_sha256,
            },
            "source": dict(source_record),
            "statement": dict(config["statement"]),
            "authority": dict(config["authority"]),
            "crop_policy": dict(config["crop_policy"]),
            "frozen_inputs": {
                "e0033_row_contract": dict(row_record),
                "e0034_numeric_verification": dict(numeric_record),
                "recovery_seal": recovery,
            },
            "page_sources": page_manifests,
            "sample_count": len(records),
            "samples": records,
            "decoder_visible_sample_fields": ["sample_id", "category", "crop_path", "crop_sha256"],
            "reference_text_available_to_decoder": False,
            "claim_boundary": config["claim_boundary"],
        }
        atomic_write_json(manifest_path, manifest)
        if run_root.exists():
            raise LogicalRowLabelCropError(f"E-0035 output appeared during capture: {run_root}")
        temporary.replace(run_root)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


__all__ = [
    "LogicalRowLabelCropError",
    "LogicalRowLabelCropPolicy",
    "capture_e0035_logical_row_label_crops",
    "union_label_bbox",
]
