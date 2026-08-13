"""Reference-blind, hash-pinned scoring for the bounded TATR structure panel.

The scorer deliberately authenticates every crop and TATR run before it opens
the post-freeze source gold.  It scores geometry only: OCR text, bank identity,
accounting-family identity, expected row counts, and gold labels never enter
model inference or threshold selection.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import subprocess
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from bctc_ai.core.hashing import sha256_file


class TatrStructureCalibrationError(RuntimeError):
    """A frozen input, run binding, or scoring contract is invalid."""


MANIFEST_FORMAT = "MULTIBANK_TABLE_STRUCTURE_CROP_MANIFEST_V1"
REQUEST_FORMAT = "MULTIBANK_TABLE_STRUCTURE_MODEL_REQUEST_V1"
TRUTH_FORMAT = "MULTIBANK_TABLE_STRUCTURE_SOURCE_GOLD_V1"
BASELINE_FORMAT = "SOURCE_PPOCRV6_GEOMETRY_BASELINE_V1"
DOWNSTREAM_FORMAT = "TATR_STRUCTURE_DOWNSTREAM_ASSESSMENT_V1"

FROZEN_STATE = "FROZEN_BEFORE_ANY_STRUCTURE_MODEL_INFERENCE"
REQUEST_STATE = "REFERENCE_BLIND_REQUEST_FROZEN"
RUN_STATE = "STRUCTURE_INFERENCE_COMPLETE"
TATR_MODEL_KEY = "TATR_V1_1_ALL"
TATR_REPO_ID = "microsoft/table-transformer-structure-recognition-v1.1-all"
TATR_REVISION = "7587a7ef111d9dcbf8ac695f1376ab7014340a0c"
TATR_WEIGHTS_SHA256 = "9df416575a3a36ebd0129342d4f597f14d6e5170268f3d52d28584ab4466a501"
TATR_CONFIG_PATH = "config/models/tatr-v1.1-all.toml"
TATR_CONFIG_SHA256 = "b0328237e4e694f1a6325d01dca914a5c832e709963beaa86ee5ba435887b9ec"
TATR_RUNNER_PATH = "scripts/models/run_tatr_structure.py"
TATR_RUNNER_SHA256 = "dd920f6021f52cfe5cece49b17d60e5ebfd6702c889a55a864a7e98113014aa1"
TATR_HELPER_PATH = "src/bctc_ai/evaluation/tatr_structure.py"
TATR_HELPER_SHA256 = "165940c21afcf8a3d588772f503e20a6237f9e8664b43ec4b98db92221719e50"
TATR_RUNTIME_MANIFEST_PATH = "config/models/gpu-runtime.toml"
TATR_RUNTIME_MANIFEST_SHA256 = "9141e0a4177f66f152bdb9eecbbfdbdd3add566dbabb81b43207a018c1ba18d8"
TATR_QUERY_COUNT = 125
TATR_LOADED_PARAMETER_COUNT = 28_828_619
TATR_LOADED_STATE_ELEMENT_COUNT = 28_847_819
TATR_ARTIFACT_IDENTITIES = {
    "config_json": {
        "path": "config.json",
        "size_bytes": 76_761,
        "sha256": "17a8a6edfb9e394263fa6ba9b82176ebccdfcc5d6cd29121ec91572c7d6be22c",
    },
    "preprocessor_config": {
        "path": "preprocessor_config.json",
        "size_bytes": 374,
        "sha256": "eead409bb80e36ae85b8377642c54550f0504f65688ba3a4967950cafe461df2",
    },
    "weights": {
        "path": "model.safetensors",
        "size_bytes": 115_437_156,
        "sha256": TATR_WEIGHTS_SHA256,
    },
}
OPAQUE_SAMPLE_ID_RE = re.compile(r"^table-[0-9]{4}$")

MANIFEST_AUTHORITY_POLICY = {
    "mapping_value_period_scope_semantic_authority": False,
    "structure_proposal_only": True,
}
MANIFEST_INFERENCE_FIREWALL = {
    "bank_family_page_control_or_expected_truth_exposed_to_model": False,
    "ocr_transcript_consulted_by_crop_selector": False,
    "role_a_schema_history_or_values_consulted_by_crop_selector": False,
}
MANIFEST_KEYS = {
    "authority",
    "dataset_role",
    "design_checkpoint_git_commit",
    "format_version",
    "git_commit",
    "git_dirty",
    "inference_firewall",
    "sample_count",
    "samples",
    "selected_source_line_count",
    "source_page_count",
    "source_spec_ref",
    "state",
}
MANIFEST_SAMPLE_KEYS = {
    "crop_height",
    "crop_path",
    "crop_sha256",
    "crop_source_bbox_raw_pixels",
    "crop_width",
    "padding_pixels",
    "sample_id",
    "selected_line_count",
    "source_line_indices",
    "source_render_ref",
    "source_result_ref",
    "table_source_bbox_raw_pixels",
}
TRUTH_KEYS = {
    "crop_manifest",
    "design_checkpoint_git_commit",
    "format_version",
    "gold_input_ref",
    "sample_count",
    "samples",
    "state",
}
SOURCE_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"

TATR_LABELS = (
    "table",
    "table column",
    "table row",
    "table column header",
    "table projected row header",
    "table spanning cell",
)
TATR_ID2LABEL = dict(enumerate(TATR_LABELS))
FIXED_OBJECT_SCORE_THRESHOLDS = (0.05, 0.3, 0.5, 0.7, 0.9)
FIXED_IOU_THRESHOLDS = (0.5, 0.75)
ANCHOR_ASSIGNMENT_MIN_MATCHED_IOU = 2.0 / 3.0
ANCHOR_ASSIGNMENT_MIN_ANCHOR_COVERAGE = 0.8
ANCHOR_ASSIGNMENT_MIN_AREA_RATIO = 2.0 / 3.0
ANCHOR_ASSIGNMENT_MAX_AREA_RATIO = 1.5
ANCHOR_ASSIGNMENT_MAX_NORMALIZED_CENTER_OFFSET = 0.2
CLASS_COVERAGE_STATES = {
    "SCORABLE_WITH_INSTANCES",
    "SCORABLE_ZERO_INSTANCE",
    "UNSCORABLE",
}
VISIBLE_UNSCORED_DASH_REASON = "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE"
VISIBLE_UNSCORED_DASH_CELL_KEYS = {
    "logical_row_ordinal",
    "numeric_lane_ordinal",
    "reason",
}
VALUE_CELL_COVERAGE_SUMMARY_KEYS = {
    "cell_slot_count",
    "source_anchored_value_cell_count",
    "visible_unscored_dash_cell_count",
    "other_unanchored_cell_count",
}
TRUTH_SAMPLE_KEYS = {
    "bank",
    "class_coverage",
    "control_kind",
    "crop_ref",
    "expected_control_disposition",
    "expected_structural_family_merge",
    "family",
    "gold_content_table_source_bbox_raw_pixels",
    "gold_objects",
    "header_row_count",
    "ignored_noncontent_line_count",
    "ignored_noncontent_line_indices",
    "ignored_noncontent_reason",
    "logical_row_count",
    "nested_row_required",
    "numeric_lane_count",
    "optional_row_behavior",
    "physical_page",
    "sample_id",
    "spanning_cell_required",
    "value_anchors",
    "value_cell_coverage_summary",
    "visible_unscored_dash_cells",
}
GOLD_OBJECT_KEYS = {"bbox_crop_pixels_xyxy", "label", "object_id"}
VALUE_ANCHOR_KEYS = {
    "anchor_id",
    "bbox_crop_pixels_xyxy",
    "expected_column_object_id",
    "expected_row_object_id",
    "logical_row_ordinal",
    "numeric_lane_ordinal",
    "source_line_index",
}
IGNORED_NONCONTENT_REASONS = {
    "NONE",
    "PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION",
}

THRESHOLD_POLICY = {
    "object_score_thresholds": list(FIXED_OBJECT_SCORE_THRESHOLDS),
    "thresholds_declared_before_truth_join": True,
    "expected_row_count_available_to_threshold_selection": False,
    "best_threshold_selected_from_sweep": False,
    "selected_threshold": None,
    "report_every_threshold": True,
}

VALUE_ASSIGNMENT_POLICY = {
    "candidate_source": "ONE_TO_ONE_SAME_CLASS_IOU_MATCH_AT_REPORTED_SCORING_THRESHOLD",
    "choose_by_anchor_coverage_or_object_score": False,
    "minimum_prediction_gold_iou": ANCHOR_ASSIGNMENT_MIN_MATCHED_IOU,
    "minimum_value_anchor_coverage_by_prediction": ANCHOR_ASSIGNMENT_MIN_ANCHOR_COVERAGE,
    "prediction_to_gold_area_ratio_inclusive": [
        ANCHOR_ASSIGNMENT_MIN_AREA_RATIO,
        ANCHOR_ASSIGNMENT_MAX_AREA_RATIO,
    ],
    "maximum_normalized_prediction_gold_center_offset": (
        ANCHOR_ASSIGNMENT_MAX_NORMALIZED_CENTER_OFFSET
    ),
    "huge_or_shifted_box_can_assign_value": False,
}


@dataclass(frozen=True)
class ArtifactPin:
    """An externally supplied digest; the artifact cannot authenticate itself."""

    path: Path
    sha256: str


@dataclass(frozen=True)
class TatrRunPin:
    """Externally pinned output pair for one opaque crop sample."""

    sample_id: str
    result: ArtifactPin
    run_manifest: ArtifactPin


def _error(message: str) -> TatrStructureCalibrationError:
    return TatrStructureCalibrationError(message)


def _valid_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _resolve(project_root: Path, value: Path | str, label: str) -> Path:
    candidate = Path(value)
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    )
    if not resolved.is_relative_to(project_root):
        raise _error(f"{label} escapes project root")
    return resolved


def _verified_json(project_root: Path, pin: ArtifactPin, label: str) -> tuple[Path, dict[str, Any]]:
    if not _valid_sha256(pin.sha256):
        raise _error(f"{label} expected SHA-256 is invalid")
    path = _resolve(project_root, pin.path, label)
    if not path.is_file() or sha256_file(path) != pin.sha256:
        raise _error(f"{label} is missing or hash-drifted")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _error(f"cannot read {label}") from exc
    if type(payload) is not dict:
        raise _error(f"{label} must be a JSON object")
    return path, payload


def _verify_object_ref(project_root: Path, value: object, label: str) -> Path:
    if type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}:
        raise _error(f"{label} must be an exact path/size/hash object reference")
    path = _resolve(project_root, value["path"], label)
    size = value["size_bytes"]
    digest = value["sha256"]
    if (
        type(size) is not int
        or size < 0
        or not _valid_sha256(digest)
        or not path.is_file()
        or path.stat().st_size != size
        or sha256_file(path) != digest
    ):
        raise _error(f"{label} is missing, size-drifted, or hash-drifted")
    return path


def _verify_git_blob(
    project_root: Path,
    *,
    commit: str,
    path: Path,
    expected_sha256: str,
    expected_size_bytes: int,
    label: str,
) -> None:
    """Prove an exact artifact blob was tracked at a pre-inference commit."""

    relative = path.relative_to(project_root).as_posix()
    shown = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if shown.returncode != 0:
        raise _error(f"{label} was missing or untracked at declared commit {commit}")
    payload = shown.stdout
    if (
        len(payload) != expected_size_bytes
        or hashlib.sha256(payload).hexdigest() != expected_sha256
    ):
        raise _error(f"{label} did not match its frozen blob at declared commit {commit}")


def _binding(path: Path, digest: str, project_root: Path) -> dict[str, str]:
    return {"path": path.relative_to(project_root).as_posix(), "sha256": digest}


def _sized_binding(path: Path, digest: str, project_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(project_root).as_posix(),
        "sha256": digest,
        "size_bytes": path.stat().st_size,
    }


def _finite_number(value: object, label: str, *, minimum: float | None = None) -> float:
    if type(value) not in {int, float}:
        raise _error(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        raise _error(f"{label} is outside its finite range")
    return number


def _bbox(
    value: object, label: str, *, width: int, height: int
) -> tuple[float, float, float, float]:
    if type(value) not in {list, tuple} or len(value) != 4:
        raise _error(f"{label} must contain four xyxy coordinates")
    x0, y0, x1, y1 = (
        _finite_number(coordinate, f"{label}[{index}]") for index, coordinate in enumerate(value)
    )
    tolerance = 1e-4
    if (
        x0 < -tolerance
        or y0 < -tolerance
        or x1 > width + tolerance
        or y1 > height + tolerance
        or x1 <= x0
        or y1 <= y0
    ):
        raise _error(f"{label} is degenerate or outside the crop")
    return (max(0.0, x0), max(0.0, y0), min(float(width), x1), min(float(height), y1))


def _exact_int_bbox(
    value: object, label: str, *, width: int, height: int
) -> tuple[int, int, int, int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise _error(f"{label} must be an exact integer xyxy bbox")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise _error(f"{label} is outside the source render")
    return x0, y0, x1, y1


def _replay_manifest_crop(
    project_root: Path,
    sample: Mapping[str, Any],
    *,
    crop_path: Path,
    result_path: Path,
    render_path: Path,
) -> None:
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _error(f"{sample['sample_id']} source result cannot be replayed") from exc
    if type(result) is not dict or result.get("format_version") != SOURCE_RESULT_FORMAT:
        raise _error(f"{sample['sample_id']} source result identity drifted")
    lines = result.get("lines")
    if type(lines) is not list or any(type(line) is not dict for line in lines):
        raise _error(f"{sample['sample_id']} source LINE geometry is absent")
    render_ref = sample["source_render_ref"]
    input_render_ref = result.get("input_render_ref")
    if (
        type(input_render_ref) is not dict
        or input_render_ref.get("sha256") != render_ref["sha256"]
        or input_render_ref.get("size_bytes") != render_ref["size_bytes"]
    ):
        raise _error(f"{sample['sample_id']} source result/render binding drifted")
    try:
        with Image.open(render_path) as opened:
            render = opened.convert("RGB")
        with Image.open(crop_path) as opened:
            crop = opened.convert("RGB")
    except (OSError, ValueError) as exc:
        raise _error(f"{sample['sample_id']} source/crop image cannot be replayed") from exc
    width, height = render.size
    indices = sample["source_line_indices"]
    if any(index >= len(lines) for index in indices):
        raise _error(f"{sample['sample_id']} source LINE locator is outside its result")
    line_boxes = [
        _exact_int_bbox(
            lines[index].get("raw_pixel_bbox"),
            f"{sample['sample_id']} source LINE {index}",
            width=width,
            height=height,
        )
        for index in indices
    ]
    table_bbox = (
        min(box[0] for box in line_boxes),
        min(box[1] for box in line_boxes),
        max(box[2] for box in line_boxes),
        max(box[3] for box in line_boxes),
    )
    if list(table_bbox) != sample["table_source_bbox_raw_pixels"]:
        raise _error(
            f"{sample['sample_id']} source table bbox is not replayable from LINE geometry"
        )
    padding = sample["padding_pixels"]
    crop_bbox = (
        max(0, table_bbox[0] - padding),
        max(0, table_bbox[1] - padding),
        min(width, table_bbox[2] + padding),
        min(height, table_bbox[3] + padding),
    )
    if list(crop_bbox) != sample["crop_source_bbox_raw_pixels"]:
        raise _error(f"{sample['sample_id']} padded crop bbox is not replayable")
    replayed = render.crop(crop_bbox)
    if replayed.size != crop.size or ImageChops.difference(replayed, crop).getbbox() is not None:
        raise _error(f"{sample['sample_id']} crop pixels do not equal the registered source region")


def _verify_manifest_and_request(
    project_root: Path,
    manifest_pin: ArtifactPin,
    request_pin: ArtifactPin,
) -> dict[str, Any]:
    manifest_path, manifest = _verified_json(project_root, manifest_pin, "crop manifest")
    request_path, request = _verified_json(project_root, request_pin, "model request")
    if set(manifest) != MANIFEST_KEYS:
        raise _error("crop manifest contains non-allowlisted source or truth fields")
    if (
        manifest.get("format_version") != MANIFEST_FORMAT
        or manifest.get("state") != FROZEN_STATE
        or manifest.get("dataset_role") != "CALIBRATION"
        or manifest.get("git_dirty") is not False
        or manifest.get("authority") != MANIFEST_AUTHORITY_POLICY
        or manifest.get("inference_firewall") != MANIFEST_INFERENCE_FIREWALL
    ):
        raise _error("crop manifest identity, role, state, or clean-code seal drifted")
    manifest_commit = manifest.get("git_commit")
    design_commit = manifest.get("design_checkpoint_git_commit")
    if (
        type(manifest_commit) is not str
        or len(manifest_commit) != 40
        or any(character not in "0123456789abcdef" for character in manifest_commit)
    ):
        raise _error("crop manifest Git commit is invalid")
    if (
        type(design_commit) is not str
        or len(design_commit) != 40
        or any(character not in "0123456789abcdef" for character in design_commit)
    ):
        raise _error("crop manifest design checkpoint is invalid")
    source_spec_path = _verify_object_ref(
        project_root, manifest.get("source_spec_ref"), "source panel spec"
    )
    _verify_git_blob(
        project_root,
        commit=manifest_commit,
        path=source_spec_path,
        expected_sha256=manifest["source_spec_ref"]["sha256"],
        expected_size_bytes=manifest["source_spec_ref"]["size_bytes"],
        label="source panel spec",
    )
    samples = manifest.get("samples")
    if type(samples) is not list or not samples or manifest.get("sample_count") != len(samples):
        raise _error("crop manifest has an invalid sample denominator")

    sample_by_id: dict[str, dict[str, Any]] = {}
    selected_line_total = 0
    source_result_hashes: set[str] = set()
    for index, sample in enumerate(samples):
        if type(sample) is not dict or set(sample) != MANIFEST_SAMPLE_KEYS:
            raise _error(f"crop manifest sample {index} is not an object")
        sample_id = sample.get("sample_id")
        if (
            type(sample_id) is not str
            or OPAQUE_SAMPLE_ID_RE.fullmatch(sample_id) is None
            or sample_id in sample_by_id
        ):
            raise _error(f"missing or duplicate crop sample identity: {sample_id!r}")
        crop_path = _resolve(project_root, str(sample.get("crop_path", "")), f"{sample_id} crop")
        crop_sha = sample.get("crop_sha256")
        crop_width = sample.get("crop_width")
        crop_height = sample.get("crop_height")
        if (
            not _valid_sha256(crop_sha)
            or not crop_path.is_file()
            or sha256_file(crop_path) != crop_sha
            or type(crop_width) is not int
            or crop_width < 1
            or type(crop_height) is not int
            or crop_height < 1
        ):
            raise _error(f"{sample_id} crop identity or dimensions drifted")
        result_path = _verify_object_ref(
            project_root, sample.get("source_result_ref"), f"{sample_id} source result"
        )
        render_path = _verify_object_ref(
            project_root, sample.get("source_render_ref"), f"{sample_id} source render"
        )
        source_lines = sample.get("source_line_indices")
        if (
            type(source_lines) is not list
            or not source_lines
            or any(type(value) is not int or value < 0 for value in source_lines)
            or sorted(set(source_lines)) != source_lines
            or sample.get("selected_line_count") != len(source_lines)
            or type(sample.get("padding_pixels")) is not int
            or not 0 <= sample["padding_pixels"] <= 5
        ):
            raise _error(f"{sample_id} source line locators are invalid")
        crop_source_bbox = sample.get("crop_source_bbox_raw_pixels")
        table_source_bbox = sample.get("table_source_bbox_raw_pixels")
        if (
            type(crop_source_bbox) is not list
            or len(crop_source_bbox) != 4
            or any(type(value) is not int for value in crop_source_bbox)
            or type(table_source_bbox) is not list
            or len(table_source_bbox) != 4
            or any(type(value) is not int for value in table_source_bbox)
            or crop_source_bbox[2] - crop_source_bbox[0] != crop_width
            or crop_source_bbox[3] - crop_source_bbox[1] != crop_height
        ):
            raise _error(f"{sample_id} crop dimensions and source bbox disagree")
        _replay_manifest_crop(
            project_root,
            sample,
            crop_path=crop_path,
            result_path=result_path,
            render_path=render_path,
        )
        selected_line_total += len(source_lines)
        source_result_hashes.add(sample["source_result_ref"]["sha256"])
        sample_by_id[sample_id] = sample
    if manifest.get("selected_source_line_count") != selected_line_total or manifest.get(
        "source_page_count"
    ) != len(source_result_hashes):
        raise _error("crop manifest aggregate denominator drifted")

    request_keys = {
        "crop_manifest",
        "dataset_role",
        "evidence_role",
        "expected_structure_available_to_reader",
        "format_version",
        "git_commit",
        "git_dirty",
        "reference_text_available_to_reader",
        "sample_count",
        "samples",
        "state",
    }
    if set(request) != request_keys:
        raise _error("model request contains non-allowlisted source or truth fields")
    if (
        request.get("format_version") != REQUEST_FORMAT
        or request.get("state") != REQUEST_STATE
        or request.get("dataset_role") != "CALIBRATION"
        or request.get("evidence_role") != "TABLE_STRUCTURE_PROPOSAL_ONLY"
        or request.get("git_dirty") is not False
        or request.get("reference_text_available_to_reader") is not False
        or request.get("expected_structure_available_to_reader") is not False
        or request.get("git_commit") != manifest_commit
    ):
        raise _error("model request crossed the reference-blind boundary")
    if request.get("crop_manifest") != _sized_binding(
        manifest_path, manifest_pin.sha256, project_root
    ):
        raise _error("model request is not bound to the exact crop manifest")
    request_samples = request.get("samples")
    if type(request_samples) is not list or request.get("sample_count") != len(samples):
        raise _error("model request denominator drifted")
    permitted_request_keys = {"sample_id", "category", "crop_path", "crop_sha256"}
    for source_sample, model_sample in zip(samples, request_samples, strict=True):
        if type(model_sample) is not dict or set(model_sample) != permitted_request_keys:
            raise _error("model request sample contains structural truth or source identity fields")
        if model_sample != {
            "sample_id": source_sample["sample_id"],
            "category": "TABLE_STRUCTURE",
            "crop_path": source_sample["crop_path"],
            "crop_sha256": source_sample["crop_sha256"],
        }:
            raise _error("model request and crop manifest axes differ")
    return {
        "manifest_path": manifest_path,
        "manifest": manifest,
        "manifest_sha256": manifest_pin.sha256,
        "request_path": request_path,
        "request": request,
        "request_sha256": request_pin.sha256,
        "sample_by_id": sample_by_id,
        "source_spec_path": source_spec_path,
    }


def _close(left: float, right: float, *, tolerance: float = 1e-5) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def _raw_bbox(
    value: object, label: str, *, width: int, height: int
) -> tuple[tuple[float, float, float, float], str]:
    """Validate a clipped raw-query box, including legitimate degenerate boxes."""

    if type(value) not in {list, tuple} or len(value) != 4:
        raise _error(f"{label} must contain four xyxy coordinates")
    x0, y0, x1, y1 = (
        _finite_number(coordinate, f"{label}[{index}]") for index, coordinate in enumerate(value)
    )
    tolerance = 1e-4
    if (
        x0 < -tolerance
        or y0 < -tolerance
        or x1 > width + tolerance
        or y1 > height + tolerance
        or x1 < x0
        or y1 < y0
    ):
        raise _error(f"{label} is outside the crop or has reversed coordinates")
    clipped = (
        max(0.0, x0),
        max(0.0, y0),
        min(float(width), x1),
        min(float(height), y1),
    )
    status = "VALID" if clipped[2] > clipped[0] and clipped[3] > clipped[1] else "DEGENERATE"
    return clipped, status


def _verify_query_predictions(
    result: Mapping[str, Any], *, sample_id: str, width: int, height: int
) -> list[dict[str, Any]]:
    raw_predictions = result.get("query_predictions")
    if type(raw_predictions) is not list or not raw_predictions:
        raise _error(f"{sample_id} result contains no raw query predictions")
    predictions: list[dict[str, Any]] = []
    for expected_index, raw in enumerate(raw_predictions):
        if type(raw) is not dict or raw.get("query_index") != expected_index:
            raise _error(f"{sample_id} query axis is not contiguous and source ordered")
        scores = raw.get("scores_by_label")
        if type(scores) is not dict or set(scores) != set(TATR_LABELS):
            raise _error(f"{sample_id} query {expected_index} class-score axis drifted")
        score_values = {
            label: _finite_number(scores[label], f"{sample_id} query {expected_index} {label}")
            for label in TATR_LABELS
        }
        no_object = _finite_number(
            raw.get("no_object_score"), f"{sample_id} query {expected_index} no-object"
        )
        if any(value < 0.0 or value > 1.0 for value in (*score_values.values(), no_object)):
            raise _error(f"{sample_id} query {expected_index} probability is outside [0, 1]")
        if not _close(sum(score_values.values()) + no_object, 1.0, tolerance=2e-4):
            raise _error(f"{sample_id} query {expected_index} probabilities do not sum to one")
        predicted_label = max(TATR_LABELS, key=score_values.__getitem__)
        predicted_class = TATR_LABELS.index(predicted_label)
        if (
            raw.get("predicted_label") != predicted_label
            or raw.get("predicted_class_id") != predicted_class
            or not _close(
                _finite_number(raw.get("object_score"), "object score"),
                score_values[predicted_label],
            )
        ):
            raise _error(f"{sample_id} query {expected_index} argmax record drifted")
        pixels, expected_status = _raw_bbox(
            raw.get("bbox_source_pixels_xyxy"),
            f"{sample_id} query {expected_index} pixel box",
            width=width,
            height=height,
        )
        normalized = raw.get("bbox_normalized_xyxy")
        if type(normalized) not in {list, tuple} or len(normalized) != 4:
            raise _error(f"{sample_id} query {expected_index} normalized box is invalid")
        expected_normalized = (
            pixels[0] / width,
            pixels[1] / height,
            pixels[2] / width,
            pixels[3] / height,
        )
        for coordinate, expected in zip(normalized, expected_normalized, strict=True):
            if not _close(_finite_number(coordinate, "normalized coordinate"), expected):
                raise _error(f"{sample_id} query {expected_index} coordinate systems disagree")
        if raw.get("bbox_status") != expected_status:
            raise _error(f"{sample_id} query {expected_index} box-status record drifted")
        predictions.append(
            {
                "query_index": expected_index,
                "label": predicted_label,
                "object_score": score_values[predicted_label],
                "no_object_score": no_object,
                "bbox": pixels,
                "bbox_status": expected_status,
            }
        )
    return predictions


def _verify_tatr_execution_identity(
    project_root: Path, run: Mapping[str, Any], sample_id: str, run_commit: str
) -> None:
    config_path = _resolve(project_root, TATR_CONFIG_PATH, "pinned TATR config")
    runner_path = _resolve(project_root, TATR_RUNNER_PATH, "pinned TATR runner")
    runtime_manifest_path = _resolve(
        project_root, TATR_RUNTIME_MANIFEST_PATH, "pinned TATR runtime manifest"
    )
    for path, expected_sha, label in (
        (config_path, TATR_CONFIG_SHA256, "TATR config"),
        (runner_path, TATR_RUNNER_SHA256, "TATR runner"),
        (
            _resolve(project_root, TATR_HELPER_PATH, "pinned TATR helper"),
            TATR_HELPER_SHA256,
            "TATR helper",
        ),
        (runtime_manifest_path, TATR_RUNTIME_MANIFEST_SHA256, "TATR runtime manifest"),
    ):
        if not path.is_file() or sha256_file(path) != expected_sha:
            raise _error(f"{sample_id} {label} is missing or hash-drifted")
        _verify_git_blob(
            project_root,
            commit=run_commit,
            path=path,
            expected_sha256=expected_sha,
            expected_size_bytes=path.stat().st_size,
            label=label,
        )
    try:
        config_payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise _error(f"{sample_id} pinned TATR config cannot be read") from exc
    model_compatibility = config_payload["compatibility"]
    processor_compatibility = config_payload["processor_compatibility"]
    expected_configuration = {
        "path": TATR_CONFIG_PATH,
        "sha256": TATR_CONFIG_SHA256,
        "runner_path": TATR_RUNNER_PATH,
        "runner_sha256": TATR_RUNNER_SHA256,
        "checkpoint_processor_size": {"longest_edge": 800},
        "runtime_processor_size": {"shortest_edge": 800, "longest_edge": 800},
        "processor_compatibility_applied": True,
        "experimental_processor_size_override": False,
        "implicit_orientation_or_unwarp": False,
        "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
        "checkpoint_compatibility": {
            "model_config": {
                "mode": model_compatibility["mode"],
                "field": model_compatibility["field"],
                "checkpoint_value": None,
                "resolved_value": model_compatibility["resolved_value"],
                "runtime_transformers": model_compatibility["runtime_transformers"],
                "checkpoint_artifact_mutated": False,
                "reason": model_compatibility["reason"],
            },
            "image_processor": {
                "mode": processor_compatibility["mode"],
                "checkpoint_size": {"longest_edge": 800},
                "resolved_size": {"shortest_edge": 800, "longest_edge": 800},
                "runtime_transformers": processor_compatibility["runtime_transformers"],
                "aspect_ratio_preserved": True,
                "checkpoint_artifact_mutated": False,
                "reason": processor_compatibility["reason"],
            },
        },
    }
    if run.get("configuration") != expected_configuration:
        raise _error(f"{sample_id} TATR config, processor, or runner identity drifted")

    runtime = run.get("runtime")
    if (
        type(runtime) is not dict
        or runtime.get("base_manifest_path") != TATR_RUNTIME_MANIFEST_PATH
        or runtime.get("base_manifest_sha256") != TATR_RUNTIME_MANIFEST_SHA256
        or runtime.get("transformers") != model_compatibility["runtime_transformers"]
    ):
        raise _error(f"{sample_id} TATR runtime identity drifted")
    runtime_model = runtime.get("model")
    if (
        type(runtime_model) is not dict
        or runtime_model.get("repo_id") != TATR_REPO_ID
        or runtime_model.get("revision") != TATR_REVISION
        or runtime_model.get("license") != "MIT"
        or runtime_model.get("loaded_parameter_count") != TATR_LOADED_PARAMETER_COUNT
        or runtime_model.get("loaded_state_element_count") != TATR_LOADED_STATE_ELEMENT_COUNT
    ):
        raise _error(f"{sample_id} TATR checkpoint identity is invalid")
    raw_artifacts = runtime_model.get("artifacts")
    if type(raw_artifacts) is not list or len(raw_artifacts) != len(TATR_ARTIFACT_IDENTITIES):
        raise _error(f"{sample_id} TATR artifact denominator drifted")
    artifacts_by_key: dict[str, Mapping[str, Any]] = {}
    for artifact in raw_artifacts:
        if type(artifact) is not dict or type(artifact.get("key")) is not str:
            raise _error(f"{sample_id} TATR artifact record is invalid")
        key = artifact["key"]
        if key in artifacts_by_key:
            raise _error(f"{sample_id} TATR artifact key is duplicated")
        artifacts_by_key[key] = artifact
    if set(artifacts_by_key) != set(TATR_ARTIFACT_IDENTITIES):
        raise _error(f"{sample_id} TATR artifact key axis drifted")
    for key, expected in TATR_ARTIFACT_IDENTITIES.items():
        artifact = artifacts_by_key[key]
        path = artifact.get("path")
        if (
            type(path) is not str
            or not path.replace("\\", "/").endswith(
                "/official_models/table-transformer-structure-recognition-v1.1-all/"
                + expected["path"]
            )
            or artifact.get("size_bytes") != expected["size_bytes"]
            or artifact.get("sha256") != expected["sha256"]
        ):
            raise _error(f"{sample_id} TATR {key} artifact identity drifted")


def _verify_clean_descendant_run_commit(
    project_root: Path, *, frozen_commit: str, run_commit: object, sample_id: str
) -> None:
    if (
        type(run_commit) is not str
        or len(run_commit) != 40
        or any(character not in "0123456789abcdef" for character in run_commit)
    ):
        raise _error(f"{sample_id} TATR run commit is invalid")
    for commit, label in ((frozen_commit, "frozen manifest"), (run_commit, "TATR run")):
        resolved = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=project_root,
            check=False,
            capture_output=True,
        )
        if resolved.returncode != 0:
            raise _error(f"{sample_id} {label} commit is absent from the repository")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", frozen_commit, run_commit],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise _error(f"{sample_id} TATR run commit is not a descendant of the frozen manifest")


def _verify_one_tatr_run(
    project_root: Path,
    run_pin: TatrRunPin,
    crop_request: Mapping[str, Any],
) -> dict[str, Any]:
    sample = crop_request["sample_by_id"].get(run_pin.sample_id)
    if sample is None:
        raise _error(f"TATR run has an unknown sample identity: {run_pin.sample_id}")
    result_path, result = _verified_json(
        project_root, run_pin.result, f"{run_pin.sample_id} result"
    )
    run_path, run = _verified_json(
        project_root, run_pin.run_manifest, f"{run_pin.sample_id} run manifest"
    )
    if (
        result.get("schema_version") != 1
        or result.get("model_key") != TATR_MODEL_KEY
        or run.get("schema_version") != 1
        or run.get("state") != RUN_STATE
        or run.get("dataset_role") != "CALIBRATION"
        or run.get("evidence_role") != "NON_GENERATIVE_TABLE_STRUCTURE_PROPOSAL_ONLY"
        or run.get("confidence_policy") != "NO_AUTOMATIC_TRUTH_SCHEMA_OR_VALUE_PROMOTION"
    ):
        raise _error(f"{run_pin.sample_id} TATR result/run identity drifted")
    model_labels = result.get("model_labels")
    normalized_labels = (
        {int(key): value for key, value in model_labels.items()}
        if type(model_labels) is dict
        else None
    )
    if normalized_labels != TATR_ID2LABEL:
        raise _error(f"{run_pin.sample_id} TATR label map drifted")
    image = result.get("image")
    if (
        type(image) is not dict
        or type(image.get("width")) is not int
        or type(image.get("height")) is not int
    ):
        raise _error(f"{run_pin.sample_id} result image dimensions are invalid")
    width, height = image["width"], image["height"]
    if width < 1 or height < 1:
        raise _error(f"{run_pin.sample_id} result image dimensions are not positive")
    input_record = run.get("input")
    crop_path = _resolve(project_root, sample["crop_path"], f"{run_pin.sample_id} crop")
    if (
        type(input_record) is not dict
        or _resolve(project_root, str(input_record.get("path", "")), "TATR input") != crop_path
        or input_record.get("size_bytes") != crop_path.stat().st_size
        or input_record.get("sha256") != sample["crop_sha256"]
        or input_record.get("width") != width
        or input_record.get("height") != height
        or sample.get("crop_width") != width
        or sample.get("crop_height") != height
    ):
        raise _error(f"{run_pin.sample_id} TATR input/crop binding drifted")
    artifact = run.get("artifacts", {}).get("structure_result")
    if artifact != {
        "path": "structure_result.json",
        "size_bytes": result_path.stat().st_size,
        "sha256": run_pin.result.sha256,
    }:
        raise _error(f"{run_pin.sample_id} result/run mutual binding drifted")
    try:
        pinned_config = tomllib.loads(
            _resolve(project_root, TATR_CONFIG_PATH, "pinned TATR config").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise _error(f"{run_pin.sample_id} pinned TATR safety cannot be read") from exc
    if run.get("safety") != pinned_config.get("safety"):
        raise _error(f"{run_pin.sample_id} TATR safety authority drifted")
    code = run.get("code")
    if type(code) is not dict or set(code) != {"commit", "dirty"} or code.get("dirty") is not False:
        raise _error(f"{run_pin.sample_id} TATR inference did not use clean code")
    _verify_clean_descendant_run_commit(
        project_root,
        frozen_commit=crop_request["manifest"]["git_commit"],
        run_commit=code.get("commit"),
        sample_id=run_pin.sample_id,
    )
    _verify_tatr_execution_identity(project_root, run, run_pin.sample_id, code["commit"])
    metrics = run.get("metrics")
    if type(metrics) is not dict:
        raise _error(f"{run_pin.sample_id} TATR metrics are absent")
    wall_seconds = _finite_number(metrics.get("wall_seconds"), "wall_seconds", minimum=0.0)
    peak_allocated = _finite_number(
        metrics.get("peak_gpu_allocated_mib"), "peak_gpu_allocated_mib", minimum=0.0
    )
    peak_reserved = _finite_number(
        metrics.get("peak_gpu_reserved_mib"), "peak_gpu_reserved_mib", minimum=0.0
    )
    predictions = _verify_query_predictions(
        result, sample_id=run_pin.sample_id, width=width, height=height
    )
    if metrics.get("query_count") != len(predictions) or len(predictions) != TATR_QUERY_COUNT:
        raise _error(f"{run_pin.sample_id} raw query denominator drifted")
    tensor_shape = metrics.get("processed_tensor_shape")
    if (
        type(tensor_shape) is not list
        or len(tensor_shape) != 4
        or tensor_shape[:2] != [1, 3]
        or any(type(value) is not int or value < 1 for value in tensor_shape)
    ):
        raise _error(f"{run_pin.sample_id} processed tensor shape is invalid")
    return {
        "sample_id": run_pin.sample_id,
        "result_path": result_path,
        "result_sha256": run_pin.result.sha256,
        "run_path": run_path,
        "run_sha256": run_pin.run_manifest.sha256,
        "width": width,
        "height": height,
        "predictions": predictions,
        "runtime": {
            "wall_seconds": wall_seconds,
            "peak_gpu_allocated_mib": peak_allocated,
            "peak_gpu_reserved_mib": peak_reserved,
        },
        "run_commit": code["commit"],
    }


def _verify_all_runs(
    project_root: Path,
    run_pins: Sequence[TatrRunPin],
    crop_request: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    sample_ids = list(crop_request["sample_by_id"])
    pin_ids = [pin.sample_id for pin in run_pins]
    if len(set(pin_ids)) != len(pin_ids) or set(pin_ids) != set(sample_ids):
        raise _error("TATR run pins do not cover every frozen crop exactly once")
    return {
        pin.sample_id: _verify_one_tatr_run(project_root, pin, crop_request) for pin in run_pins
    }


def _verify_truth(
    project_root: Path,
    truth_pin: ArtifactPin,
    crop_request: Mapping[str, Any],
    runs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    # This function is intentionally called only after `_verify_all_runs`.
    truth_path, truth = _verified_json(project_root, truth_pin, "source gold")
    if set(truth) != TRUTH_KEYS:
        raise _error("source gold contains non-allowlisted fields")
    if (
        truth.get("format_version") != TRUTH_FORMAT
        or truth.get("state") != FROZEN_STATE
        or truth.get("design_checkpoint_git_commit")
        != crop_request["manifest"]["design_checkpoint_git_commit"]
    ):
        raise _error("source gold identity or pre-inference freeze state drifted")
    if truth.get("crop_manifest") != _sized_binding(
        crop_request["manifest_path"], crop_request["manifest_sha256"], project_root
    ):
        raise _error("source gold is not bound to the exact crop manifest")
    gold_input_path = _verify_object_ref(
        project_root, truth.get("gold_input_ref"), "source-gold input"
    )
    source_spec_ref = crop_request["manifest"]["source_spec_ref"]
    gold_input_ref = truth["gold_input_ref"]
    _verify_git_blob(
        project_root,
        commit=crop_request["manifest"]["git_commit"],
        path=gold_input_path,
        expected_sha256=gold_input_ref["sha256"],
        expected_size_bytes=gold_input_ref["size_bytes"],
        label="source-gold input",
    )
    for run_commit in sorted({run["run_commit"] for run in runs.values()}):
        _verify_git_blob(
            project_root,
            commit=run_commit,
            path=crop_request["source_spec_path"],
            expected_sha256=source_spec_ref["sha256"],
            expected_size_bytes=source_spec_ref["size_bytes"],
            label="source panel spec",
        )
        _verify_git_blob(
            project_root,
            commit=run_commit,
            path=gold_input_path,
            expected_sha256=gold_input_ref["sha256"],
            expected_size_bytes=gold_input_ref["size_bytes"],
            label="source-gold input",
        )
        _verify_git_blob(
            project_root,
            commit=run_commit,
            path=truth_path,
            expected_sha256=truth_pin.sha256,
            expected_size_bytes=truth_path.stat().st_size,
            label="source gold",
        )
    raw_samples = truth.get("samples")
    if type(raw_samples) is not list or truth.get("sample_count") != len(raw_samples):
        raise _error("source gold denominator is invalid")
    truth_by_id: dict[str, dict[str, Any]] = {}
    for raw in raw_samples:
        if type(raw) is not dict or set(raw) != TRUTH_SAMPLE_KEYS:
            raise _error("source-gold sample contains non-allowlisted fields")
        sample_id = raw.get("sample_id")
        if sample_id not in runs or sample_id in truth_by_id:
            raise _error(f"source-gold sample axis drifted: {sample_id!r}")
        run = runs[sample_id]
        bank = raw.get("bank")
        if type(bank) is not str or not bank.strip():
            raise _error(f"{sample_id} source gold must identify its post-run bank stratum")
        control_kind = raw.get("control_kind")
        if control_kind not in {"POSITIVE", "HARD_CONTROL"}:
            raise _error(f"{sample_id} has an invalid control kind")
        expected_merge = raw.get("expected_structural_family_merge")
        if type(expected_merge) is not bool or (control_kind == "HARD_CONTROL" and expected_merge):
            raise _error(f"{sample_id} hard-control merge expectation is unsafe")
        if (
            raw.get("expected_control_disposition") not in {"ACCEPT", "REJECT"}
            or (control_kind == "POSITIVE") != (raw["expected_control_disposition"] == "ACCEPT")
            or type(raw.get("family")) is not str
            or not raw["family"].strip()
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] < 1
            or type(raw.get("optional_row_behavior")) is not str
            or not raw["optional_row_behavior"].strip()
        ):
            raise _error(f"{sample_id} source-gold stratum or disposition is invalid")
        ignored_indices = raw.get("ignored_noncontent_line_indices")
        ignored_count = raw.get("ignored_noncontent_line_count")
        ignored_reason = raw.get("ignored_noncontent_reason")
        if (
            type(ignored_indices) is not list
            or any(type(index) is not int or index < 0 for index in ignored_indices)
            or ignored_indices != sorted(set(ignored_indices))
            or ignored_count != len(ignored_indices)
            or ignored_reason not in IGNORED_NONCONTENT_REASONS
            or bool(ignored_indices)
            != (ignored_reason == "PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION")
        ):
            raise _error(f"{sample_id} ignored noncontent audit is invalid")
        content_bbox = raw.get("gold_content_table_source_bbox_raw_pixels")
        source_sample = crop_request["sample_by_id"][sample_id]
        crop_ref = raw.get("crop_ref")
        crop_path = _resolve(project_root, source_sample["crop_path"], f"{sample_id} crop")
        if crop_ref != {
            "path": source_sample["crop_path"],
            "sha256": source_sample["crop_sha256"],
            "size_bytes": crop_path.stat().st_size,
        }:
            raise _error(f"{sample_id} source gold crop binding drifted")
        selected_source_indices = set(source_sample["source_line_indices"])
        if not set(ignored_indices) <= selected_source_indices:
            raise _error(f"{sample_id} ignored noncontent locator escapes the selected crop")
        source_result_path = _resolve(
            project_root,
            source_sample["source_result_ref"]["path"],
            f"{sample_id} source result",
        )
        source_result = json.loads(source_result_path.read_text(encoding="utf-8"))
        source_lines = source_result["lines"]
        content_line_indices = [
            index
            for index in source_sample["source_line_indices"]
            if index not in set(ignored_indices)
        ]
        if not content_line_indices:
            raise _error(f"{sample_id} gold content table has no authenticated source lines")
        content_line_boxes = [
            source_lines[index]["raw_pixel_bbox"] for index in content_line_indices
        ]
        replayed_content_bbox = [
            min(box[0] for box in content_line_boxes),
            min(box[1] for box in content_line_boxes),
            max(box[2] for box in content_line_boxes),
            max(box[3] for box in content_line_boxes),
        ]
        if content_bbox != replayed_content_bbox:
            raise _error(f"{sample_id} gold content table bbox is not replayable")
        coverage = raw.get("class_coverage")
        if type(coverage) is not dict or set(coverage) != set(TATR_LABELS):
            raise _error(f"{sample_id} class coverage must enumerate all TATR labels")
        if any(value not in CLASS_COVERAGE_STATES for value in coverage.values()):
            raise _error(f"{sample_id} class coverage state is invalid")
        objects = raw.get("gold_objects")
        if type(objects) is not list:
            raise _error(f"{sample_id} gold objects are absent")
        object_by_id: dict[str, dict[str, Any]] = {}
        count_by_label = {label: 0 for label in TATR_LABELS}
        normalized_objects: list[dict[str, Any]] = []
        for obj in objects:
            if type(obj) is not dict or set(obj) != GOLD_OBJECT_KEYS:
                raise _error(f"{sample_id} gold object contains non-allowlisted fields")
            object_id = obj.get("object_id")
            label = obj.get("label")
            if type(object_id) is not str or not object_id or object_id in object_by_id:
                raise _error(f"{sample_id} gold object identity is missing or duplicated")
            if label not in TATR_LABELS or coverage[label] != "SCORABLE_WITH_INSTANCES":
                raise _error(f"{sample_id} gold object conflicts with class coverage")
            normalized = {
                "object_id": object_id,
                "label": label,
                "bbox": _bbox(
                    obj.get("bbox_crop_pixels_xyxy"),
                    f"{sample_id} gold {object_id}",
                    width=run["width"],
                    height=run["height"],
                ),
            }
            object_by_id[object_id] = normalized
            normalized_objects.append(normalized)
            count_by_label[label] += 1
        for label, state in coverage.items():
            if state == "SCORABLE_WITH_INSTANCES" and count_by_label[label] == 0:
                raise _error(f"{sample_id} {label} coverage claims missing instances")
            if state in {"SCORABLE_ZERO_INSTANCE", "UNSCORABLE"} and count_by_label[label] != 0:
                raise _error(f"{sample_id} {label} coverage conflicts with gold instances")
        table_objects = [item for item in normalized_objects if item["label"] == "table"]
        crop_source_bbox = source_sample["crop_source_bbox_raw_pixels"]
        expected_table_crop_bbox = (
            float(content_bbox[0] - crop_source_bbox[0]),
            float(content_bbox[1] - crop_source_bbox[1]),
            float(content_bbox[2] - crop_source_bbox[0]),
            float(content_bbox[3] - crop_source_bbox[1]),
        )
        if len(table_objects) != 1 or table_objects[0]["bbox"] != expected_table_crop_bbox:
            raise _error(f"{sample_id} table object does not equal replayed gold content bbox")
        for field in ("logical_row_count", "numeric_lane_count", "header_row_count"):
            if type(raw.get(field)) is not int or raw[field] < 0:
                raise _error(f"{sample_id} {field} is invalid")
        if (
            type(raw.get("spanning_cell_required")) is not bool
            or type(raw.get("nested_row_required")) is not bool
        ):
            raise _error(f"{sample_id} structural requirement flags are invalid")
        dash_cells = raw.get("visible_unscored_dash_cells")
        if type(dash_cells) is not list:
            raise _error(f"{sample_id} visible unscored dash-cell register is absent")
        normalized_dash_cells = []
        dash_axes: set[tuple[int, int]] = set()
        for cell in dash_cells:
            if type(cell) is not dict or set(cell) != VISIBLE_UNSCORED_DASH_CELL_KEYS:
                raise _error(f"{sample_id} visible unscored dash cell is invalid")
            row_ordinal = cell.get("logical_row_ordinal")
            lane_ordinal = cell.get("numeric_lane_ordinal")
            axis = (row_ordinal, lane_ordinal)
            if (
                type(row_ordinal) is not int
                or type(lane_ordinal) is not int
                or not 1 <= row_ordinal <= raw["logical_row_count"]
                or not 1 <= lane_ordinal <= raw["numeric_lane_count"]
                or cell.get("reason") != VISIBLE_UNSCORED_DASH_REASON
                or axis in dash_axes
            ):
                raise _error(f"{sample_id} visible unscored dash cell is invalid")
            dash_axes.add(axis)
            normalized_dash_cells.append(dict(cell))
        cell_coverage = raw.get("value_cell_coverage_summary")
        if type(cell_coverage) is not dict or set(cell_coverage) != (
            VALUE_CELL_COVERAGE_SUMMARY_KEYS
        ):
            raise _error(f"{sample_id} value-cell coverage summary is invalid")
        if any(
            type(cell_coverage[key]) is not int or cell_coverage[key] < 0 for key in cell_coverage
        ):
            raise _error(f"{sample_id} value-cell coverage counts are invalid")
        cell_slot_count = raw["logical_row_count"] * raw["numeric_lane_count"]
        if (
            cell_coverage["cell_slot_count"] != cell_slot_count
            or cell_coverage["visible_unscored_dash_cell_count"] != len(normalized_dash_cells)
            or sum(
                cell_coverage[key]
                for key in (
                    "source_anchored_value_cell_count",
                    "visible_unscored_dash_cell_count",
                    "other_unanchored_cell_count",
                )
            )
            != cell_slot_count
        ):
            raise _error(f"{sample_id} value-cell coverage denominator drifted")
        anchors = raw.get("value_anchors")
        if type(anchors) is not list:
            raise _error(f"{sample_id} value anchors are absent")
        normalized_anchors = []
        anchor_ids: set[str] = set()
        anchor_source_indices: set[int] = set()
        anchored_axes: set[tuple[int, int]] = set()
        row_owner_by_ordinal: dict[int, str] = {}
        column_owner_by_ordinal: dict[int, str] = {}
        for anchor in anchors:
            if type(anchor) is not dict or set(anchor) != VALUE_ANCHOR_KEYS:
                raise _error(f"{sample_id} value anchor contains non-allowlisted fields")
            anchor_id = anchor.get("anchor_id")
            row_id = anchor.get("expected_row_object_id")
            column_id = anchor.get("expected_column_object_id")
            row_ordinal = anchor.get("logical_row_ordinal")
            lane_ordinal = anchor.get("numeric_lane_ordinal")
            source_line_index = anchor.get("source_line_index")
            owner_axis = (row_ordinal, lane_ordinal)
            if type(anchor_id) is not str or not anchor_id or anchor_id in anchor_ids:
                raise _error(f"{sample_id} value anchor identity is missing or duplicated")
            if (
                row_id not in object_by_id
                or object_by_id[row_id]["label"] != "table row"
                or column_id not in object_by_id
                or object_by_id[column_id]["label"] != "table column"
            ):
                raise _error(f"{sample_id} value anchor owner IDs are invalid")
            if (
                type(row_ordinal) is not int
                or type(lane_ordinal) is not int
                or not 1 <= row_ordinal <= raw["logical_row_count"]
                or not 1 <= lane_ordinal <= raw["numeric_lane_count"]
                or owner_axis in anchored_axes
                or type(source_line_index) is not int
                or source_line_index not in selected_source_indices
                or source_line_index in set(ignored_indices)
                or source_line_index in anchor_source_indices
                or (
                    row_ordinal in row_owner_by_ordinal
                    and row_owner_by_ordinal[row_ordinal] != row_id
                )
                or (
                    lane_ordinal in column_owner_by_ordinal
                    and column_owner_by_ordinal[lane_ordinal] != column_id
                )
            ):
                raise _error(f"{sample_id} value anchor source/axis binding is invalid")
            anchor_bbox = _bbox(
                anchor.get("bbox_crop_pixels_xyxy"),
                f"{sample_id} anchor {anchor_id}",
                width=run["width"],
                height=run["height"],
            )
            source_line_bbox = source_lines[source_line_index]["raw_pixel_bbox"]
            expected_anchor_bbox = (
                float(source_line_bbox[0] - crop_source_bbox[0]),
                float(source_line_bbox[1] - crop_source_bbox[1]),
                float(source_line_bbox[2] - crop_source_bbox[0]),
                float(source_line_bbox[3] - crop_source_bbox[1]),
            )
            if anchor_bbox != expected_anchor_bbox:
                raise _error(f"{sample_id} value anchor bbox is not replayable from its LINE")
            if (
                _intersection_fraction(anchor_bbox, object_by_id[row_id]["bbox"])
                < ANCHOR_ASSIGNMENT_MIN_ANCHOR_COVERAGE
                or _intersection_fraction(anchor_bbox, object_by_id[column_id]["bbox"])
                < ANCHOR_ASSIGNMENT_MIN_ANCHOR_COVERAGE
            ):
                raise _error(f"{sample_id} value anchor is not localized in its gold row/column")
            anchor_ids.add(anchor_id)
            anchor_source_indices.add(source_line_index)
            anchored_axes.add(owner_axis)
            row_owner_by_ordinal[row_ordinal] = row_id
            column_owner_by_ordinal[lane_ordinal] = column_id
            normalized_anchors.append(
                {
                    "anchor_id": anchor_id,
                    "bbox": anchor_bbox,
                    "expected_row_object_id": row_id,
                    "expected_column_object_id": column_id,
                    "logical_row_ordinal": row_ordinal,
                    "numeric_lane_ordinal": lane_ordinal,
                    "source_line_index": source_line_index,
                }
            )
        if dash_axes & anchored_axes:
            raise _error(f"{sample_id} visible dash cell overlaps a source-anchored cell")
        if len(set(row_owner_by_ordinal.values())) != len(row_owner_by_ordinal) or len(
            set(column_owner_by_ordinal.values())
        ) != len(column_owner_by_ordinal):
            raise _error(f"{sample_id} value anchor ordinal-to-owner mapping is not one-to-one")
        if len(anchored_axes) != cell_coverage["source_anchored_value_cell_count"]:
            raise _error(f"{sample_id} source-anchored value-cell denominator drifted")
        truth_by_id[sample_id] = {
            **raw,
            "gold_objects": normalized_objects,
            "gold_object_by_id": object_by_id,
            "value_anchors": normalized_anchors,
            "value_cell_coverage_summary": dict(cell_coverage),
            "visible_unscored_dash_cells": normalized_dash_cells,
        }
    if set(truth_by_id) != set(runs):
        raise _error("source gold does not cover every authenticated TATR run")
    return {
        "truth_path": truth_path,
        "truth_sha256": truth_pin.sha256,
        "truth": truth,
        "truth_by_id": truth_by_id,
    }


def intersection_over_union(left: Sequence[float], right: Sequence[float]) -> float:
    """Return axis-aligned IoU for two already validated xyxy boxes."""

    x0 = max(left[0], right[0])
    y0 = max(left[1], right[1])
    x1 = min(left[2], right[2])
    y1 = min(left[3], right[3])
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def _maximum_weight_assignment(weights: Sequence[Sequence[float]]) -> list[tuple[int, int]]:
    """Hungarian assignment; positive weights make cardinality primary."""

    row_count = len(weights)
    column_count = len(weights[0]) if row_count else 0
    if row_count == 0 or column_count == 0:
        return []
    size = max(row_count, column_count)
    square = [
        [
            weights[row][column] if row < row_count and column < column_count else 0.0
            for column in range(size)
        ]
        for row in range(size)
    ]
    # Standard O(n^3) minimization form; negate weights for maximization.
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for row in range(1, size + 1):
        p[0] = row
        column0 = 0
        minimum = [math.inf] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[column0] = True
            row0 = p[column0]
            delta = math.inf
            column1 = 0
            for column in range(1, size + 1):
                if used[column]:
                    continue
                current = -square[row0 - 1][column - 1] - u[row0] - v[column]
                if current < minimum[column]:
                    minimum[column] = current
                    way[column] = column0
                if minimum[column] < delta:
                    delta = minimum[column]
                    column1 = column
            for column in range(size + 1):
                if used[column]:
                    u[p[column]] += delta
                    v[column] -= delta
                else:
                    minimum[column] -= delta
            column0 = column1
            if p[column0] == 0:
                break
        while True:
            column1 = way[column0]
            p[column0] = p[column1]
            column0 = column1
            if column0 == 0:
                break
    assignment = []
    for column in range(1, size + 1):
        row = p[column] - 1
        actual_column = column - 1
        if row < row_count and actual_column < column_count:
            assignment.append((row, actual_column))
    return assignment


def _cardinality_primary_weights(
    ious: Sequence[Sequence[float]], iou_threshold: float
) -> list[list[float]]:
    row_count = len(ious)
    column_count = len(ious[0]) if row_count else 0
    if any(len(row) != column_count for row in ious):
        raise _error("IoU matching matrix is ragged")
    assignment_size = max(row_count, column_count)
    cardinality_weight = float(assignment_size + 1)
    return [
        [cardinality_weight + value if value >= iou_threshold else 0.0 for value in row]
        for row in ious
    ]


def _match_class(
    predictions: Sequence[Mapping[str, Any]],
    gold: Sequence[Mapping[str, Any]],
    iou_threshold: float,
) -> list[dict[str, Any]]:
    ious = [
        [intersection_over_union(prediction["bbox"], item["bbox"]) for item in gold]
        for prediction in predictions
    ]
    # One extra valid edge must outweigh the greatest possible aggregate IoU
    # advantage of every other edge.  `size + 1` gives a true lexicographic
    # maximum-cardinality, then maximum-total-IoU assignment.
    weights = _cardinality_primary_weights(ious, iou_threshold)
    matches = []
    for prediction_index, gold_index in _maximum_weight_assignment(weights):
        value = ious[prediction_index][gold_index]
        if value >= iou_threshold:
            matches.append(
                {
                    "prediction_index": prediction_index,
                    "query_index": predictions[prediction_index]["query_index"],
                    "gold_index": gold_index,
                    "gold_object_id": gold[gold_index]["object_id"],
                    "iou": value,
                }
            )
    return sorted(matches, key=lambda item: item["query_index"])


def _prf(true_positive: int, predicted: int, gold: int) -> dict[str, Any]:
    false_positive = predicted - true_positive
    false_negative = gold - true_positive
    if predicted == 0 and gold == 0:
        precision = recall = f1 = 1.0
    else:
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / gold if gold else 1.0
        f1 = 2.0 * precision * recall / (precision + recall) if precision + recall > 0.0 else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _intersection_fraction(inner: Sequence[float], outer: Sequence[float]) -> float:
    x0 = max(inner[0], outer[0])
    y0 = max(inner[1], outer[1])
    x1 = min(inner[2], outer[2])
    y1 = min(inner[3], outer[3])
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return intersection / area if area > 0.0 else 0.0


def _box_area(box: Sequence[float]) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def _normalized_center_offset(
    prediction: Sequence[float], gold: Sequence[float]
) -> dict[str, float]:
    gold_width = gold[2] - gold[0]
    gold_height = gold[3] - gold[1]
    prediction_center_x = (prediction[0] + prediction[2]) / 2.0
    prediction_center_y = (prediction[1] + prediction[3]) / 2.0
    gold_center_x = (gold[0] + gold[2]) / 2.0
    gold_center_y = (gold[1] + gold[3]) / 2.0
    return {
        "x": abs(prediction_center_x - gold_center_x) / gold_width,
        "y": abs(prediction_center_y - gold_center_y) / gold_height,
    }


def _assign_anchor_to_expected_match(
    anchor: Mapping[str, Any],
    *,
    expected_gold_object_id: str,
    expected_label: str,
    matched_by_gold_object_id: Mapping[str, Mapping[str, Any]],
    gold_object_by_id: Mapping[str, Mapping[str, Any]],
    scoring_iou_threshold: float,
) -> dict[str, Any]:
    gold = gold_object_by_id[expected_gold_object_id]
    if gold["label"] != expected_label:
        raise _error("value-anchor expected object has the wrong structure label")
    matched = matched_by_gold_object_id.get(expected_gold_object_id)
    if matched is None:
        return {
            "expected_gold_object_id": expected_gold_object_id,
            "query_index": None,
            "matched_gold_object_id": None,
            "prediction_gold_iou": None,
            "required_prediction_gold_iou": max(
                scoring_iou_threshold, ANCHOR_ASSIGNMENT_MIN_MATCHED_IOU
            ),
            "anchor_coverage": 0.0,
            "prediction_to_gold_area_ratio": None,
            "normalized_center_offset": None,
            "localized_to_expected_gold_object": False,
            "failure_reasons": ["EXPECTED_GOLD_OBJECT_HAS_NO_MATCHED_PREDICTION"],
        }
    prediction = matched["prediction"]
    prediction_gold_iou = float(matched["iou"])
    anchor_coverage = _intersection_fraction(anchor["bbox"], prediction["bbox"])
    area_ratio = _box_area(prediction["bbox"]) / _box_area(gold["bbox"])
    center_offset = _normalized_center_offset(prediction["bbox"], gold["bbox"])
    required_iou = max(scoring_iou_threshold, ANCHOR_ASSIGNMENT_MIN_MATCHED_IOU)
    failure_reasons = []
    if prediction_gold_iou < required_iou:
        failure_reasons.append("PREDICTION_GOLD_IOU_TOO_LOW_FOR_VALUE_ASSIGNMENT")
    if anchor_coverage < ANCHOR_ASSIGNMENT_MIN_ANCHOR_COVERAGE:
        failure_reasons.append("VALUE_ANCHOR_NOT_STRONGLY_COVERED_BY_PREDICTION")
    if not ANCHOR_ASSIGNMENT_MIN_AREA_RATIO <= area_ratio <= ANCHOR_ASSIGNMENT_MAX_AREA_RATIO:
        failure_reasons.append("PREDICTION_GOLD_AREA_RATIO_OUTSIDE_STRICT_BOUNDS")
    if max(center_offset.values()) > ANCHOR_ASSIGNMENT_MAX_NORMALIZED_CENTER_OFFSET:
        failure_reasons.append("PREDICTION_CENTER_TOO_FAR_FROM_EXPECTED_GOLD_CENTER")
    return {
        "expected_gold_object_id": expected_gold_object_id,
        "query_index": prediction["query_index"],
        "matched_gold_object_id": expected_gold_object_id,
        "prediction_gold_iou": prediction_gold_iou,
        "required_prediction_gold_iou": required_iou,
        "anchor_coverage": anchor_coverage,
        "prediction_to_gold_area_ratio": area_ratio,
        "normalized_center_offset": center_offset,
        "localized_to_expected_gold_object": not failure_reasons,
        "failure_reasons": failure_reasons,
    }


def _score_sample(
    predictions: Sequence[Mapping[str, Any]],
    truth: Mapping[str, Any],
    *,
    object_threshold: float,
    iou_threshold: float,
) -> dict[str, Any]:
    retained = [
        prediction
        for prediction in predictions
        if prediction["bbox_status"] == "VALID"
        and prediction["object_score"] >= object_threshold
        and prediction["object_score"] > prediction["no_object_score"]
    ]
    class_metrics: dict[str, Any] = {}
    matched_by_gold_object_id: dict[str, dict[str, Any]] = {}
    micro_tp = micro_predicted = micro_gold = 0
    all_scorable_counts_exact = True
    all_scorable_geometry_exact = True
    for label in TATR_LABELS:
        coverage = truth["class_coverage"][label]
        if coverage == "UNSCORABLE":
            class_metrics[label] = {"coverage": coverage, "metrics": None, "matches": []}
            continue
        predicted_class = [item for item in retained if item["label"] == label]
        gold_class = [item for item in truth["gold_objects"] if item["label"] == label]
        matches = _match_class(predicted_class, gold_class, iou_threshold)
        metrics = _prf(len(matches), len(predicted_class), len(gold_class))
        mean_iou = statistics.fmean(match["iou"] for match in matches) if matches else None
        metrics.update(
            {
                "predicted_count": len(predicted_class),
                "gold_count": len(gold_class),
                "count_exact": len(predicted_class) == len(gold_class),
                "mean_matched_iou": mean_iou,
            }
        )
        class_metrics[label] = {"coverage": coverage, "metrics": metrics, "matches": matches}
        for match in matches:
            matched_by_gold_object_id[match["gold_object_id"]] = {
                "prediction": predicted_class[match["prediction_index"]],
                "gold": gold_class[match["gold_index"]],
                "iou": match["iou"],
            }
        micro_tp += len(matches)
        micro_predicted += len(predicted_class)
        micro_gold += len(gold_class)
        all_scorable_counts_exact &= metrics["count_exact"]
        all_scorable_geometry_exact &= (
            metrics["true_positive"] == len(predicted_class) == len(gold_class)
        )

    anchor_results = []
    for anchor in truth["value_anchors"]:
        row = _assign_anchor_to_expected_match(
            anchor,
            expected_gold_object_id=anchor["expected_row_object_id"],
            expected_label="table row",
            matched_by_gold_object_id=matched_by_gold_object_id,
            gold_object_by_id=truth["gold_object_by_id"],
            scoring_iou_threshold=iou_threshold,
        )
        column = _assign_anchor_to_expected_match(
            anchor,
            expected_gold_object_id=anchor["expected_column_object_id"],
            expected_label="table column",
            matched_by_gold_object_id=matched_by_gold_object_id,
            gold_object_by_id=truth["gold_object_by_id"],
            scoring_iou_threshold=iou_threshold,
        )
        row_correct = row["localized_to_expected_gold_object"]
        column_correct = column["localized_to_expected_gold_object"]
        anchor_results.append(
            {
                "anchor_id": anchor["anchor_id"],
                "row": row,
                "column": column,
                "row_correct": row_correct,
                "column_correct": column_correct,
                "row_and_column_correct": row_correct and column_correct,
            }
        )
    assignment_total = len(anchor_results)
    row_correct_count = sum(result["row_correct"] for result in anchor_results)
    column_correct_count = sum(result["column_correct"] for result in anchor_results)
    pair_correct_count = sum(result["row_and_column_correct"] for result in anchor_results)
    cell_assignment_results: dict[tuple[str, str], bool] = {}
    for anchor, result in zip(truth["value_anchors"], anchor_results, strict=True):
        owner_axis = (
            anchor["expected_row_object_id"],
            anchor["expected_column_object_id"],
        )
        cell_assignment_results[owner_axis] = (
            cell_assignment_results.get(owner_axis, True) and (result["row_and_column_correct"])
        )
    source_anchored_cell_count = truth["value_cell_coverage_summary"][
        "source_anchored_value_cell_count"
    ]
    source_anchored_cell_correct_count = sum(cell_assignment_results.values())
    assignment_exact = (
        len(cell_assignment_results) == source_anchored_cell_count
        and source_anchored_cell_correct_count == source_anchored_cell_count
    )

    row_count = sum(item["label"] == "table row" for item in retained)
    gold_table_row_count = sum(item["label"] == "table row" for item in truth["gold_objects"])
    column_count = sum(item["label"] == "table column" for item in retained)
    column_header_count = sum(item["label"] == "table column header" for item in retained)
    gold_column_header_count = sum(
        item["label"] == "table column header" for item in truth["gold_objects"]
    )
    span_count = sum(item["label"] == "table spanning cell" for item in retained)
    row_exact = row_count == gold_table_row_count
    column_header_exact = column_header_count == gold_column_header_count
    span_scorable = truth["class_coverage"]["table spanning cell"] != "UNSCORABLE"
    span_presence_exact = (
        (span_count > 0) == truth["spanning_cell_required"] if span_scorable else None
    )
    # Columns may include the label column.  Value anchors are the source of
    # truth for numeric lanes; never tune the object threshold to this count.
    expected_numeric_columns = {
        anchor["expected_column_object_id"] for anchor in truth["value_anchors"]
    }
    assigned_numeric_columns = {
        result["column"]["matched_gold_object_id"]
        for result in anchor_results
        if result["column"]["localized_to_expected_gold_object"]
    }
    numeric_lane_exact = (
        len(expected_numeric_columns) == truth["numeric_lane_count"]
        and assigned_numeric_columns == expected_numeric_columns
    )
    exact_topology = (
        all_scorable_counts_exact
        and all_scorable_geometry_exact
        and row_exact
        and column_header_exact
        and span_presence_exact is True
        and numeric_lane_exact
        and assignment_exact
    )
    return {
        "retained_query_count": len(retained),
        "retained_counts_by_label": {
            label: sum(item["label"] == label for item in retained) for label in TATR_LABELS
        },
        "class_metrics": class_metrics,
        "micro": _prf(micro_tp, micro_predicted, micro_gold),
        "topology": {
            "predicted_row_count": row_count,
            "expected_table_row_object_count": gold_table_row_count,
            "declared_body_logical_row_count": truth["logical_row_count"],
            "exact_table_row_object_count": row_exact,
            "predicted_column_count": column_count,
            "expected_numeric_lane_count": truth["numeric_lane_count"],
            "source_anchored_numeric_lane_count": len(expected_numeric_columns),
            "exact_numeric_lane_assignment": numeric_lane_exact,
            "exact_numeric_lane_assignment_scope": "SOURCE_ANCHORED_VALUE_CELLS_ONLY",
            "exact_numeric_lane_assignment_implies_full_cell_coverage": False,
            "declared_header_row_count": truth["header_row_count"],
            "predicted_column_header_object_count": column_header_count,
            "expected_column_header_object_count": gold_column_header_count,
            "exact_column_header_object_count": column_header_exact,
            "predicted_spanning_cell_count": span_count,
            "spanning_cell_required": truth["spanning_cell_required"],
            "spanning_cell_presence_exact": span_presence_exact,
            "nested_row_required": truth["nested_row_required"],
            "nested_row_semantics_scored": False,
            "all_scorable_class_counts_exact": all_scorable_counts_exact,
            "all_scorable_geometry_exact_at_iou_threshold": all_scorable_geometry_exact,
            "exact_topology": exact_topology,
        },
        "value_assignment": {
            "scope": "SOURCE_LINE_ANCHORS_ONLY_NOT_FULL_VISIBLE_CELL_COVERAGE",
            "anchor_count": assignment_total,
            "source_anchor_box_count": assignment_total,
            "row_correct_count": row_correct_count,
            "column_correct_count": column_correct_count,
            "row_and_column_correct_count": pair_correct_count,
            "source_anchored_value_assignment_exact": assignment_exact,
            "full_visible_cell_coverage_claimed": False,
            "cell_coverage": {
                **truth["value_cell_coverage_summary"],
                "source_anchored_value_cell_assignment_correct_count": (
                    source_anchored_cell_correct_count
                ),
                "source_anchored_value_cell_assignment_exact": assignment_exact,
                "visible_unscored_dash_cells_scored_or_penalized": False,
                "full_value_cell_coverage_scored": (
                    source_anchored_cell_count
                    == truth["value_cell_coverage_summary"]["cell_slot_count"]
                ),
            },
            "visible_unscored_dash_cells": truth["visible_unscored_dash_cells"],
            "anchors": anchor_results,
        },
    }


def _score_threshold_grid(
    runs: Mapping[str, Mapping[str, Any]], truth_by_id: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    grid: dict[str, Any] = {}
    for object_threshold in FIXED_OBJECT_SCORE_THRESHOLDS:
        object_key = f"{object_threshold:.6f}"
        by_iou: dict[str, Any] = {}
        for iou_threshold in FIXED_IOU_THRESHOLDS:
            iou_key = f"{iou_threshold:.2f}"
            sample_scores = {
                sample_id: _score_sample(
                    runs[sample_id]["predictions"],
                    truth,
                    object_threshold=object_threshold,
                    iou_threshold=iou_threshold,
                )
                for sample_id, truth in truth_by_id.items()
            }
            micro_tp = sum(score["micro"]["true_positive"] for score in sample_scores.values())
            micro_predicted = sum(
                score["micro"]["true_positive"] + score["micro"]["false_positive"]
                for score in sample_scores.values()
            )
            micro_gold = sum(
                score["micro"]["true_positive"] + score["micro"]["false_negative"]
                for score in sample_scores.values()
            )
            positive = [
                score
                for sample_id, score in sample_scores.items()
                if truth_by_id[sample_id]["control_kind"] == "POSITIVE"
            ]
            by_iou[iou_key] = {
                "samples": sample_scores,
                "aggregate": {
                    "sample_count": len(sample_scores),
                    "positive_sample_count": len(positive),
                    "micro": _prf(micro_tp, micro_predicted, micro_gold),
                    "exact_topology_count": sum(
                        score["topology"]["exact_topology"] for score in sample_scores.values()
                    ),
                    "positive_exact_topology_count": sum(
                        score["topology"]["exact_topology"] for score in positive
                    ),
                    "source_anchored_value_assignment_exact_count": sum(
                        score["value_assignment"]["source_anchored_value_assignment_exact"]
                        for score in sample_scores.values()
                    ),
                    "value_cell_coverage": {
                        "cell_slot_count": sum(
                            score["value_assignment"]["cell_coverage"]["cell_slot_count"]
                            for score in sample_scores.values()
                        ),
                        "source_anchored_value_cell_count": sum(
                            score["value_assignment"]["cell_coverage"][
                                "source_anchored_value_cell_count"
                            ]
                            for score in sample_scores.values()
                        ),
                        "source_anchored_value_cell_assignment_correct_count": sum(
                            score["value_assignment"]["cell_coverage"][
                                "source_anchored_value_cell_assignment_correct_count"
                            ]
                            for score in sample_scores.values()
                        ),
                        "visible_unscored_dash_cell_count": sum(
                            score["value_assignment"]["cell_coverage"][
                                "visible_unscored_dash_cell_count"
                            ]
                            for score in sample_scores.values()
                        ),
                        "other_unanchored_cell_count": sum(
                            score["value_assignment"]["cell_coverage"][
                                "other_unanchored_cell_count"
                            ]
                            for score in sample_scores.values()
                        ),
                        "visible_unscored_dash_cells_scored_or_penalized": False,
                        "full_value_cell_coverage_claimed": False,
                    },
                },
            }
        grid[object_key] = {"iou_thresholds": by_iou}
    return grid


def _verify_optional_baseline(
    project_root: Path,
    baseline_pin: ArtifactPin | None,
    crop_request: Mapping[str, Any],
    truth: Mapping[str, Any],
) -> dict[str, Any]:
    """Score the optional, source-bound PP-OCRv6 geometry baseline."""

    if baseline_pin is None:
        return {"status": "NOT_PROVIDED", "comparison": None}
    path, baseline = _verified_json(project_root, baseline_pin, "source-geometry baseline")
    # V1 has no separately pinned, pre-truth generator/run/config provenance.
    # A self-declared JSON could be fabricated after reading gold, so it must
    # never be called authenticated or used to claim an improvement.
    return {
        "status": "REJECTED_UNTRUSTED_SELF_DECLARED_BASELINE_V1",
        "artifact": _binding(path, baseline_pin.sha256, project_root),
        "declared_format_version": baseline.get("format_version"),
        "comparison": None,
        "reason": (
            "No pinned pre-truth PP-OCRv6/source-geometry baseline generator, configuration, "
            "clean-code receipt, or reference-blind run provenance exists in baseline V1."
        ),
    }


def _verify_downstream_assessment(
    project_root: Path,
    assessment_pin: ArtifactPin | None,
    crop_request: Mapping[str, Any],
    truth: Mapping[str, Any],
    runs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if assessment_pin is None:
        return {
            "status": "NOT_PROVIDED",
            "downstream_gate_pass_by_threshold": {
                f"{threshold:.6f}": False for threshold in FIXED_OBJECT_SCORE_THRESHOLDS
            },
            "reason": "Geometry alone cannot establish accounting-family merges or downstream graph gain.",
        }
    path, assessment = _verified_json(project_root, assessment_pin, "downstream assessment")
    expected_runs = [
        {
            "sample_id": sample_id,
            "result_sha256": run["result_sha256"],
            "run_manifest_sha256": run["run_sha256"],
        }
        for sample_id, run in sorted(runs.items())
    ]
    if (
        assessment.get("format_version") != DOWNSTREAM_FORMAT
        or assessment.get("state") != "FROZEN_DOWNSTREAM_REPLAY_COMPLETE"
        or assessment.get("crop_manifest")
        != _binding(crop_request["manifest_path"], crop_request["manifest_sha256"], project_root)
        or assessment.get("truth")
        != _binding(truth["truth_path"], truth["truth_sha256"], project_root)
        or assessment.get("tatr_runs") != expected_runs
        or assessment.get("object_score_thresholds") != list(FIXED_OBJECT_SCORE_THRESHOLDS)
    ):
        raise _error("downstream assessment identity, input bindings, or threshold axis drifted")
    records = assessment.get("records")
    expected_count = len(runs) * len(FIXED_OBJECT_SCORE_THRESHOLDS)
    if type(records) is not list or len(records) != expected_count:
        raise _error("downstream assessment denominator drifted")
    record_by_axis: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if type(record) is not dict:
            raise _error("downstream assessment record is invalid")
        sample_id = record.get("sample_id")
        threshold = record.get("object_score_threshold")
        axis = (sample_id, threshold)
        if (
            sample_id not in runs
            or threshold not in {f"{value:.6f}" for value in FIXED_OBJECT_SCORE_THRESHOLDS}
            or axis in record_by_axis
            or type(record.get("candidate_structural_family_merge")) is not bool
            or type(record.get("accepted_graph_delta")) is not int
            or type(record.get("unresolved_delta")) is not int
            or type(record.get("date_number_ownership_regressed")) is not bool
        ):
            raise _error("downstream assessment record axis or metrics are invalid")
        record_by_axis[axis] = record
    downstream_gate_pass: dict[str, bool] = {}
    gates: dict[str, Any] = {}
    for threshold in FIXED_OBJECT_SCORE_THRESHOLDS:
        key = f"{threshold:.6f}"
        subset = [record_by_axis[(sample_id, key)] for sample_id in runs]
        hard_control_zero_false_merge = all(
            not record["candidate_structural_family_merge"]
            for record in subset
            if truth["truth_by_id"][record["sample_id"]]["control_kind"] == "HARD_CONTROL"
        )
        accepted_graph_delta = sum(record["accepted_graph_delta"] for record in subset)
        no_ownership_regression = not any(
            record["date_number_ownership_regressed"] for record in subset
        )
        unresolved_delta = sum(record["unresolved_delta"] for record in subset)
        no_unresolved_increase = all(record["unresolved_delta"] <= 0 for record in subset)
        positive_gain_banks = {
            truth["truth_by_id"][record["sample_id"]]["bank"]
            for record in subset
            if truth["truth_by_id"][record["sample_id"]]["control_kind"] == "POSITIVE"
            and record["accepted_graph_delta"] > 0
        }
        threshold_gates = {
            "hard_controls_zero_false_structural_family_merge": hard_control_zero_false_merge,
            "net_downstream_accepted_graph_gain": accepted_graph_delta > 0,
            "positive_graph_gain_bank_count": len(positive_gain_banks),
            "positive_graph_gain_on_at_least_three_banks": len(positive_gain_banks) >= 3,
            "date_number_ownership_not_regressed": no_ownership_regression,
            "unresolved_delta": unresolved_delta,
            "no_sample_or_net_unresolved_increase": (
                no_unresolved_increase and unresolved_delta <= 0
            ),
        }
        gates[key] = threshold_gates
        downstream_gate_pass[key] = all(
            value
            for gate, value in threshold_gates.items()
            if gate not in {"positive_graph_gain_bank_count", "unresolved_delta"}
        )
    return {
        "status": "AUTHENTICATED_AND_EVALUATED",
        "artifact": _binding(path, assessment_pin.sha256, project_root),
        "gates_by_threshold": gates,
        "downstream_gate_pass_by_threshold": downstream_gate_pass,
    }


def _exact_positive_banks(
    sample_scores: Mapping[str, Mapping[str, Any]],
    truth_by_id: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    sample_ids_by_bank: dict[str, list[str]] = {}
    for sample_id, sample_truth in truth_by_id.items():
        if sample_truth["control_kind"] == "POSITIVE":
            sample_ids_by_bank.setdefault(sample_truth["bank"], []).append(sample_id)
    return {
        bank
        for bank, sample_ids in sample_ids_by_bank.items()
        if sample_ids
        and all(sample_scores[sample_id]["topology"]["exact_topology"] for sample_id in sample_ids)
    }


def _evaluate_promotion_candidates(
    threshold_grid: Mapping[str, Any],
    baseline: Mapping[str, Any],
    downstream: Mapping[str, Any],
    truth_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Combine independent gates; never claim eligibility without a frozen runtime budget."""

    strict_iou_key = "0.75"
    baseline_authenticated = baseline.get("status") == "AUTHENTICATED_AND_SCORED"
    downstream_authenticated = downstream.get("status") == "AUTHENTICATED_AND_EVALUATED"
    baseline_scores = (
        baseline["comparison"]["iou_thresholds"][strict_iou_key]["samples"]
        if baseline_authenticated
        else None
    )
    baseline_exact_banks = (
        _exact_positive_banks(baseline_scores, truth_by_id)
        if baseline_scores is not None
        else set()
    )
    gates_by_threshold: dict[str, Any] = {}
    candidate_thresholds = []
    for object_threshold in FIXED_OBJECT_SCORE_THRESHOLDS:
        key = f"{object_threshold:.6f}"
        candidate_scores = threshold_grid[key]["iou_thresholds"][strict_iou_key]["samples"]
        exact_banks = _exact_positive_banks(candidate_scores, truth_by_id)
        improved_banks = exact_banks - baseline_exact_banks if baseline_authenticated else set()
        downstream_pass = bool(
            downstream.get("downstream_gate_pass_by_threshold", {}).get(key, False)
        )
        gates = {
            "strict_iou_threshold": float(strict_iou_key),
            "authenticated_source_geometry_baseline_present": baseline_authenticated,
            "authenticated_downstream_assessment_present": downstream_authenticated,
            "positive_exact_topology_banks": sorted(exact_banks),
            "positive_exact_topology_bank_count": len(exact_banks),
            "exact_topology_on_at_least_three_positive_banks": len(exact_banks) >= 3,
            "baseline_positive_exact_topology_banks": sorted(baseline_exact_banks),
            "strict_exact_topology_improvement_banks": sorted(improved_banks),
            "strict_exact_topology_improvement_bank_count": len(improved_banks),
            "strict_exact_topology_improves_at_least_three_banks": len(improved_banks) >= 3,
            "downstream_zero_false_merge_no_regression_no_unresolved_increase_and_gain": (
                downstream_pass
            ),
            "runtime_budget_predeclared_before_inference": False,
            "runtime_budget_pass": False,
        }
        candidate_gate_names = {
            "authenticated_source_geometry_baseline_present",
            "authenticated_downstream_assessment_present",
            "exact_topology_on_at_least_three_positive_banks",
            "strict_exact_topology_improves_at_least_three_banks",
            "downstream_zero_false_merge_no_regression_no_unresolved_increase_and_gain",
        }
        calibration_candidate = all(bool(gates[name]) for name in candidate_gate_names)
        gates["calibration_candidate_before_runtime_budget"] = calibration_candidate
        gates["promotion_eligible"] = False
        gates_by_threshold[key] = gates
        if calibration_candidate:
            candidate_thresholds.append(key)
    return {
        "automatic_promotion": False,
        "selected_threshold": None,
        "dataset_role": "CALIBRATION",
        "untouched_holdout_evaluation_present": False,
        "strict_iou_threshold": float(strict_iou_key),
        "candidate_thresholds_before_runtime_budget": candidate_thresholds,
        "eligible_thresholds": [],
        "gates_by_threshold": gates_by_threshold,
        "decision": "NO_PROMOTION_CALIBRATION_ONLY_NO_TRUSTED_BASELINE_HOLDOUT_OR_RUNTIME_BUDGET",
    }


def score_tatr_structure_panel(
    project_root: Path,
    *,
    crop_manifest: ArtifactPin,
    model_request: ArtifactPin,
    source_gold: ArtifactPin,
    tatr_runs: Sequence[TatrRunPin],
    deterministic_baseline: ArtifactPin | None = None,
    downstream_assessment: ArtifactPin | None = None,
) -> dict[str, Any]:
    """Authenticate and score one fixed TATR sweep without selecting a threshold."""

    root = project_root.resolve()
    crop_request = _verify_manifest_and_request(root, crop_manifest, model_request)
    runs = _verify_all_runs(root, tatr_runs, crop_request)
    # Truth is opened only after all result/run hashes and crop bindings pass.
    truth = _verify_truth(root, source_gold, crop_request, runs)
    crop_request["sample_dimensions"] = {
        sample_id: (run["width"], run["height"]) for sample_id, run in runs.items()
    }
    threshold_grid = _score_threshold_grid(runs, truth["truth_by_id"])
    baseline = _verify_optional_baseline(root, deterministic_baseline, crop_request, truth)
    downstream = _verify_downstream_assessment(
        root, downstream_assessment, crop_request, truth, runs
    )
    promotion_decision = _evaluate_promotion_candidates(
        threshold_grid, baseline, downstream, truth["truth_by_id"]
    )
    wall_seconds = [run["runtime"]["wall_seconds"] for run in runs.values()]
    result_bindings = [
        {
            "sample_id": sample_id,
            "result": _binding(run["result_path"], run["result_sha256"], root),
            "run_manifest": _binding(run["run_path"], run["run_sha256"], root),
        }
        for sample_id, run in sorted(runs.items())
    ]
    return {
        "format_version": "TATR_STRUCTURE_CALIBRATION_SCORE_V1",
        "status": "SCORED_NO_THRESHOLD_SELECTED",
        "claim_boundary": (
            "FROZEN_VIETNAMESE_BANK_REPORT_TABLE_STRUCTURE_CALIBRATION_ONLY_"
            "NO_TEXT_VALUE_PERIOD_SCHEMA_FAMILY_MAPPING_OR_EXPORT_AUTHORITY"
        ),
        "reference_isolation": {
            "truth_loaded_only_after_all_tatr_runs_authenticated": True,
            "request_contains_bank_family_page_or_expected_structure": False,
            "ocr_text_scored_or_used": False,
            "threshold_selected_from_expected_row_count": False,
        },
        "inputs": {
            "crop_manifest": _binding(
                crop_request["manifest_path"], crop_request["manifest_sha256"], root
            ),
            "model_request": _binding(
                crop_request["request_path"], crop_request["request_sha256"], root
            ),
            "source_gold": _binding(truth["truth_path"], truth["truth_sha256"], root),
            "tatr_runs": result_bindings,
        },
        "threshold_policy": THRESHOLD_POLICY,
        "value_assignment_policy": VALUE_ASSIGNMENT_POLICY,
        "iou_thresholds": list(FIXED_IOU_THRESHOLDS),
        "threshold_grid": threshold_grid,
        "source_ppocrv6_geometry_baseline": baseline,
        "downstream_promotion": downstream,
        "runtime": {
            "sample_count": len(runs),
            "wall_seconds_total": sum(wall_seconds),
            "wall_seconds_mean": statistics.fmean(wall_seconds),
            "wall_seconds_median": statistics.median(wall_seconds),
            "wall_seconds_max": max(wall_seconds),
            "peak_gpu_allocated_mib_max": max(
                run["runtime"]["peak_gpu_allocated_mib"] for run in runs.values()
            ),
            "peak_gpu_reserved_mib_max": max(
                run["runtime"]["peak_gpu_reserved_mib"] for run in runs.values()
            ),
            "by_sample": {sample_id: run["runtime"] for sample_id, run in sorted(runs.items())},
        },
        "promotion_decision": promotion_decision,
    }
