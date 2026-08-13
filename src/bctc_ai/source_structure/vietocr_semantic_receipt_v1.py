"""Bind a frozen E-0024 VietOCR run to exact source-page line evidence.

This module is deliberately narrower than a semantic parser.  The global
receipt authenticates the crop registry, reference-blind request, VietOCR
output, and run manifest.  A page binding then proves which exact OCR LINE
atoms supplied the pixels for each proposal.  Neither artifact grants the
reader geometry, numeric, period, unit, scope, schema, or acceptance authority.

Strict adjacent-line unions are retained for diagnostics only.  Consumers may
inspect them, but must not treat their transcript as a source-line replacement.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tomllib
import weakref
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageOps

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import (
    SourceStructureContractV2Error,
    validate_source_evidence_projection_v2,
)

FORMAT_VERSION = "E0024_VIETOCR_GLOBAL_SEMANTIC_RECEIPT_V1"
PAGE_FORMAT_VERSION = "E0024_VIETOCR_PAGE_SEMANTIC_BINDING_V1"

CLAIM_BOUNDARY = (
    "SOURCE_BOUND_VIETOCR_SEMANTIC_TEXT_PROPOSALS_ONLY_NO_STRUCTURE_OR_ACCOUNTING_AUTHORITY"
)
PAGE_CLAIM_BOUNDARY = (
    "EXACT_V2_OCR_LINE_TO_VIETOCR_PIXEL_PROPOSAL_BINDING_ONLY_NO_TEXT_OR_STRUCTURE_PROMOTION"
)


class VietOCRSemanticReceiptV1Error(ValueError):
    """The E-0024 artifact chain or exact page binding drifted."""


class AuthenticatedVietOCRSemanticReceiptV1:
    """Opaque authority produced only by exact E-0024 artifact replay.

    A plain receipt dictionary is deliberately insufficient for page binding:
    its syntax is public and therefore cannot authenticate OCR predictions.
    """

    __slots__ = ("__payload", "__weakref__")

    def __init__(self, payload: dict[str, Any], token: object) -> None:
        if token is not _AUTHENTICATION_TOKEN:
            raise _error("authenticated VietOCR receipts can only be created by artifact replay")
        self.__payload = canonical_clone_v1(payload)

    def __getitem__(self, key: str) -> Any:
        return canonical_clone_v1(self.__payload[key])

    def __eq__(self, other: object) -> bool:
        return type(other) is AuthenticatedVietOCRSemanticReceiptV1 and same_typed_json_v1(
            self.__payload, other.__payload
        )

    def _clone_for_internal_replay(self, token: object) -> dict[str, Any]:
        if token is not _AUTHENTICATION_TOKEN:
            raise _error("authenticated VietOCR receipt payload is opaque")
        return canonical_clone_v1(self.__payload)


_AUTHENTICATION_TOKEN = object()
_AUTHENTICATED_RECEIPTS: dict[
    int, tuple[weakref.ReferenceType[AuthenticatedVietOCRSemanticReceiptV1], str]
] = {}


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PAGE_ID_RE = re.compile(r"^page-[0-9]{4,}$")
_SAMPLE_ID_RE = re.compile(r"^page-[0-9]{4,}-(?:line|union)-[0-9]{3,}(?:-[0-9]{3,})?$")

_CROP_MANIFEST_FIELDS = {
    "format_version",
    "state",
    "dataset_role",
    "git_commit",
    "git_dirty",
    "authority",
    "inference_firewall",
    "selection_rule",
    "page_count",
    "pages",
    "sample_count",
    "samples",
}
_CROP_AUTHORITY_FIELDS = {
    "geometry_change",
    "numeric_value_period_unit_sign_scope_schema_authority",
    "semantic_acceptance",
}
_FIREWALL_FIELDS = {
    "bank_filename_physical_page_family_or_control_role_exposed_to_reader",
    "expected_labels_available_to_crop_selector",
    "ocr_raw_text_read_by_crop_selector",
    "reader_receives_crop_pixels_only",
    "role_a_available_to_crop_selector",
}
_SELECTION_FIELDS = {
    "deskew",
    "primary_atom_type",
    "resize",
    "single_line_predicates",
    "source_padding_left_top_right_bottom",
    "strict_union_predicates",
    "threshold",
    "white_border_left_top_right_bottom",
}
_CROP_PAGE_FIELDS = {
    "page_id",
    "authenticated_line_count",
    "render_path",
    "render_sha256",
    "render_width",
    "render_height",
    "result_path",
    "result_sha256",
    "selected_single_line_count",
    "selected_strict_union_count",
}
_CROP_SAMPLE_FIELDS = {
    "sample_id",
    "page_id",
    "category",
    "grouping",
    "source_line_indices",
    "source_bbox_raw_pixels",
    "padded_source_bbox_raw_pixels",
    "crop_path",
    "crop_sha256",
    "crop_width",
    "crop_height",
}
_REQUEST_FIELDS = {
    "format_version",
    "experiment_id",
    "state",
    "dataset_role",
    "evidence_role",
    "git_commit",
    "git_dirty",
    "crop_manifest",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
}
_REQUEST_SAMPLE_FIELDS = {"sample_id", "category", "crop_path", "crop_sha256"}
_RESULT_FIELDS = {
    "format_version",
    "experiment_id",
    "state",
    "dataset_role",
    "evidence_role",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
}
_RESULT_SAMPLE_FIELDS = {
    "sample_id",
    "category",
    "crop_path",
    "crop_sha256",
    "processed_width",
    "processed_height",
    "raw_prediction",
    "mean_decoded_character_probability",
    "wall_seconds",
}
_RUN_FIELDS = {
    "format_version",
    "experiment_id",
    "state",
    "started_at",
    "completed_at",
    "git_commit",
    "git_dirty",
    "request",
    "configuration",
    "runtime",
    "metrics",
    "safety",
    "artifacts",
}
_RUN_CONFIGURATION_FIELDS = {
    "path",
    "sha256",
    "network_policy",
    "cnn_pretrained_download",
    "beam_search",
    "reference_text_available_to_decoder",
}
_RUN_RUNTIME_FIELDS = {
    "external_root",
    "site_packages",
    "packages",
    "torch_cuda_build",
    "device",
    "compute_capability",
    "artifacts",
}
_RUN_RUNTIME_ARTIFACTS = {"wheel", "base_config", "model_config", "weights"}
_RUN_RUNTIME_ARTIFACT_FIELDS = {"path", "sha256", "size_bytes", "url"}
_RUN_METRIC_FIELDS = {
    "sample_count",
    "model_load_seconds",
    "total_wall_seconds",
    "peak_gpu_memory_allocated_mib",
    "peak_gpu_memory_reserved_mib",
}
_RUN_SAFETY_FIELDS = {
    "numeric_authority",
    "period_authority",
    "unit_authority",
    "sign_authority",
    "geometry_authority",
    "mapping_authority",
    "automatic_truth_promotion",
}
_OBJECT_REF_FIELDS = {"path", "sha256", "size_bytes"}
_HASH_REF_FIELDS = {"path", "sha256"}

_PAGE_RESULT_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "request_sha256",
    "request",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "input_render_ref",
    "backend_payload_ref",
    "word_box_normalization_ledger",
    "coordinate_authority",
    "lines",
    "words",
    "metrics",
    "source_blank_claimed",
    "safety",
}
_PAGE_RESULT_LINE_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "raw_pixel_bbox",
    "raw_pixel_polygon",
    "canonical_bbox_mpt",
    "canonical_polygon_mpt",
    "words",
}

_RECEIPT_FIELDS = {
    "format_version",
    "claim_boundary",
    "experiment_id",
    "dataset_role",
    "evidence_role",
    "inputs",
    "pages",
    "samples",
    "metrics",
    "safety",
}
_RECEIPT_INPUT_FIELDS = {"crop_manifest", "reader_request", "ocr_result", "run_manifest"}
_RECEIPT_PAGE_FIELDS = {
    "page_id",
    "result_ref",
    "render_ref",
    "authenticated_line_count",
    "single_line_sample_count",
    "diagnostic_union_sample_count",
}
_RECEIPT_SAMPLE_FIELDS = {
    "sample_id",
    "page_id",
    "grouping",
    "category",
    "source_line_indices",
    "source_bbox_raw_pixels",
    "padded_source_bbox_raw_pixels",
    "crop_ref",
    "raw_prediction",
    "normalized_prediction",
    "mean_decoded_character_probability",
    "processed_dimensions",
    "diagnostic_only",
}
_RECEIPT_METRIC_FIELDS = {
    "page_count",
    "sample_count",
    "single_line_sample_count",
    "diagnostic_union_sample_count",
}
_RECEIPT_SAFETY = {
    "reader_output_is_proposal_only": True,
    "union_samples_diagnostic_only": True,
    "geometry_authority": False,
    "numeric_authority": False,
    "period_authority": False,
    "unit_authority": False,
    "sign_authority": False,
    "scope_authority": False,
    "schema_authority": False,
    "semantic_acceptance": False,
    "automatic_truth_promotion": False,
}

_PAGE_BINDING_FIELDS = {
    "format_version",
    "claim_boundary",
    "source_local_page_id",
    "source_projection_sha256",
    "global_receipt_sha256",
    "page_id",
    "page_source_binding",
    "samples",
    "metrics",
    "safety",
}
_PAGE_SOURCE_BINDING_FIELDS = {"route", "page_result_sha256", "render_sha256"}
_BOUND_SAMPLE_FIELDS = _RECEIPT_SAMPLE_FIELDS | {"source_atoms"}
_BOUND_ATOM_FIELDS = {
    "source_atom_id",
    "line_index",
    "raw_text",
    "pixel_bbox",
    "canonical_bbox_mpt",
}
_PAGE_METRIC_FIELDS = {
    "sample_count",
    "single_line_sample_count",
    "diagnostic_union_sample_count",
    "bound_source_line_occurrence_count",
    "unique_source_line_count",
}
_PAGE_SAFETY = {
    **_RECEIPT_SAFETY,
    "source_atom_text_replaced": False,
    "lag_observation_assembled": False,
}

_SELECTION_RULE = {
    "deskew": False,
    "primary_atom_type": "V3_AUTHENTICATED_LINE_WITH_RAW_PIXEL_BBOX",
    "resize": False,
    "single_line_predicates": [
        "x0 <= 0.25 * render_width",
        "x1 <= 0.65 * render_width",
        "8 <= bbox_height <= 0.06 * render_height",
        "y0 >= 0.03 * render_height",
        "y1 <= 0.97 * render_height",
        "bbox inside render",
    ],
    "source_padding_left_top_right_bottom": [8, 4, 8, 4],
    "strict_union_predicates": [
        "consecutive selected candidates",
        "-2 <= next.y0 - prior.y1 <= 0",
        "abs(next.x0-prior.x0) <= 0.02 * render_width",
    ],
    "threshold": False,
    "white_border_left_top_right_bottom": [12, 8, 12, 8],
}


def _error(message: str) -> VietOCRSemanticReceiptV1Error:
    return VietOCRSemanticReceiptV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _git_sha(value: Any, label: str) -> str:
    if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a 40-character lowercase Git SHA")
    return value


def _integer(value: Any, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or (positive and value <= 0) or (not positive and value < 0):
        raise _error(f"{label} is not a valid integer")
    return value


def _finite(value: Any, label: str, *, minimum: float | None = None) -> float:
    if type(value) not in {int, float} or type(value) is bool or not math.isfinite(value):
        raise _error(f"{label} is not finite")
    result = float(value)
    if minimum is not None and result < minimum:
        raise _error(f"{label} is below its minimum")
    return result


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error(f"{label} is not a positive integer bbox")
    return list(value)


def _safe_relative(path: Any, label: str) -> Path:
    if type(path) is not str or not path or "\\" in path:
        raise _error(f"{label} is not a safe relative path")
    value = Path(path)
    if (
        value.is_absolute()
        or value.as_posix() != path
        or any(part in {"", ".", ".."} for part in value.parts)
    ):
        raise _error(f"{label} is not a safe relative path")
    return value


def _resolve(project_root: Path, path: Path | str, label: str) -> Path:
    root = project_root.resolve()
    raw = Path(path)
    value = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        value.relative_to(root)
    except ValueError as exc:
        raise _error(f"{label} escapes project root") from exc
    return value


def _project_relative(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def _runtime_resolve(runtime_root: Path, path: Any, label: str) -> Path:
    relative = _safe_relative(path, f"{label} path")
    root = runtime_root.resolve()
    value = (root / relative).resolve()
    try:
        value.relative_to(root)
    except ValueError as exc:
        raise _error(f"{label} escapes runtime root") from exc
    return value


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.stat()
        first = path.read_bytes()
        second = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise _error(f"cannot read {label}: {path}") from exc
    if (
        not path.is_file()
        or first != second
        or before.st_size != len(first)
        or after.st_size != len(first)
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise _error(f"{label} changed while it was read")
    return first


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    payload = _stable_bytes(path, label)
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not valid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be a JSON object")
    return value, payload


def _file_ref(project_root: Path, path: Path, payload: bytes | None = None) -> dict[str, Any]:
    data = payload if payload is not None else _stable_bytes(path, "artifact")
    return {
        "path": _project_relative(project_root, path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def _validate_object_ref(value: Any, label: str, *, suffix: str | None = None) -> dict[str, Any]:
    item = _exact_dict(value, _OBJECT_REF_FIELDS, label)
    path = _safe_relative(item["path"], f"{label} path")
    if suffix is not None and path.suffix != suffix:
        raise _error(f"{label} suffix drifted")
    _sha(item["sha256"], f"{label} hash")
    _integer(item["size_bytes"], f"{label} size", positive=True)
    return item


def _validate_hash_ref(value: Any, label: str) -> dict[str, Any]:
    item = _exact_dict(value, _HASH_REF_FIELDS, label)
    _safe_relative(item["path"], f"{label} path")
    _sha(item["sha256"], f"{label} hash")
    return item


def _path_has_suffix(path: str, suffix: str) -> bool:
    path_parts = Path(path).parts
    suffix_parts = Path(suffix).parts
    return len(path_parts) >= len(suffix_parts) and path_parts[-len(suffix_parts) :] == suffix_parts


def _verify_ref_file(
    project_root: Path,
    reference: dict[str, Any],
    *,
    base: Path | None = None,
    label: str,
) -> Path:
    relative = _safe_relative(reference["path"], f"{label} path")
    path = ((base or project_root) / relative).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise _error(f"{label} escapes project root") from exc
    payload = _stable_bytes(path, label)
    if sha256_file(path) != reference["sha256"] or (
        "size_bytes" in reference and len(payload) != reference["size_bytes"]
    ):
        raise _error(f"{label} is missing or hash/size drifted")
    return path


def _selected_line_indices(lines: list[dict[str, Any]], *, width: int, height: int) -> list[int]:
    selected: list[int] = []
    for index, line in enumerate(lines):
        x0, y0, x1, y1 = _bbox(line["raw_pixel_bbox"], f"line {index} bbox")
        if (
            4 * x0 <= width
            and 20 * x1 <= 13 * width
            and 8 <= y1 - y0
            and 100 * (y1 - y0) <= 6 * height
            and 100 * y0 >= 3 * height
            and 100 * y1 <= 97 * height
        ):
            selected.append(index)
    return selected


def _strict_union_pairs(
    selected: list[int], lines: list[dict[str, Any]], *, width: int
) -> list[tuple[int, int]]:
    boxes = [line["raw_pixel_bbox"] for line in lines]
    return [
        (prior, following)
        for prior, following in zip(selected, selected[1:], strict=False)
        if -2 <= boxes[following][1] - boxes[prior][3] <= 0
        and 50 * abs(boxes[following][0] - boxes[prior][0]) <= width
    ]


def _validate_crop_manifest(
    project_root: Path, manifest: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _exact_dict(manifest, _CROP_MANIFEST_FIELDS, "crop manifest")
    if (
        manifest["format_version"] != "LAG_V1_SOURCE_ONLY_SEMANTIC_CANARY_CROP_MANIFEST_V1"
        or manifest["state"] != "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE"
        or manifest["dataset_role"] != "DEVELOPMENT_REPLAY"
        or manifest["git_dirty"] is not False
    ):
        raise _error("crop-manifest identity or frozen state drifted")
    _git_sha(manifest["git_commit"], "crop-manifest Git commit")
    authority = _exact_dict(manifest["authority"], _CROP_AUTHORITY_FIELDS, "crop authority")
    if any(value is not False for value in authority.values()):
        raise _error("crop manifest grants forbidden authority")
    firewall = _exact_dict(manifest["inference_firewall"], _FIREWALL_FIELDS, "crop firewall")
    expected_firewall = {key: False for key in _FIREWALL_FIELDS}
    expected_firewall["reader_receives_crop_pixels_only"] = True
    if not same_typed_json_v1(firewall, expected_firewall):
        raise _error("crop inference firewall drifted")
    selection = _exact_dict(manifest["selection_rule"], _SELECTION_FIELDS, "selection rule")
    if not same_typed_json_v1(selection, _SELECTION_RULE):
        raise _error("crop selection rule drifted")

    raw_pages = manifest["pages"]
    raw_samples = manifest["samples"]
    if (
        type(raw_pages) is not list
        or type(raw_samples) is not list
        or len(raw_pages) != _integer(manifest["page_count"], "crop page count", positive=True)
        or len(raw_samples)
        != _integer(manifest["sample_count"], "crop sample count", positive=True)
    ):
        raise _error("crop manifest denominators drifted")

    pages: list[dict[str, Any]] = []
    page_by_id: dict[str, dict[str, Any]] = {}
    page_results: dict[str, dict[str, Any]] = {}
    for page_index, raw_page in enumerate(raw_pages):
        page = _exact_dict(raw_page, _CROP_PAGE_FIELDS, f"crop page {page_index}")
        page_id = page["page_id"]
        if (
            type(page_id) is not str
            or _PAGE_ID_RE.fullmatch(page_id) is None
            or page_id in page_by_id
        ):
            raise _error("crop page IDs are invalid or duplicated")
        render_width = _integer(page["render_width"], f"{page_id} render width", positive=True)
        render_height = _integer(page["render_height"], f"{page_id} render height", positive=True)
        authenticated_count = _integer(
            page["authenticated_line_count"], f"{page_id} authenticated line count", positive=True
        )
        _integer(page["selected_single_line_count"], f"{page_id} single-line count")
        _integer(page["selected_strict_union_count"], f"{page_id} union count")
        render_path = _resolve(
            project_root, _safe_relative(page["render_path"], "render path"), "render"
        )
        result_path = _resolve(
            project_root, _safe_relative(page["result_path"], "result path"), "result"
        )
        render_sha = _sha(page["render_sha256"], f"{page_id} render hash")
        result_sha = _sha(page["result_sha256"], f"{page_id} result hash")
        if (
            render_path.suffix != ".png"
            or result_path.suffix != ".json"
            or render_path.stem != render_sha
            or result_path.stem != result_sha
            or sha256_file(render_path) != render_sha
            or sha256_file(result_path) != result_sha
        ):
            raise _error(f"{page_id} render/result object identity drifted")
        result, _ = _load_json(result_path, f"{page_id} page result")
        _exact_dict(result, _PAGE_RESULT_FIELDS, f"{page_id} page result")
        if (
            result["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
            or result["route"] != "DOMINANT_RASTER_OCR"
            or result["status"] != "OCR_WORD_BOX_READ_COMPLETE"
            or result["source_blank_claimed"] is not False
        ):
            raise _error(f"{page_id} is not an authenticated nonterminal OCR V2 result")
        render_ref = _validate_object_ref(
            result["input_render_ref"], f"{page_id} render ref", suffix=".png"
        )
        if (
            render_ref["sha256"] != render_sha
            or not _path_has_suffix(page["render_path"], render_ref["path"])
            or render_ref["size_bytes"] != render_path.stat().st_size
        ):
            raise _error(f"{page_id} result-to-render binding drifted")
        lines = result["lines"]
        if (
            type(lines) is not list
            or len(lines) != authenticated_count
            or type(result["metrics"]) is not dict
            or result["metrics"].get("line_count") != authenticated_count
        ):
            raise _error(f"{page_id} authenticated line denominator drifted")
        for line_index, line in enumerate(lines):
            _exact_dict(line, _PAGE_RESULT_LINE_FIELDS, f"{page_id} line {line_index}")
            bbox = _bbox(line["raw_pixel_bbox"], f"{page_id} line {line_index} bbox")
            if bbox[2] > render_width or bbox[3] > render_height:
                raise _error(f"{page_id} line {line_index} falls outside render")
        coordinate = result["coordinate_authority"]
        if type(coordinate) is not dict or coordinate.get("pixel_dimensions") != [
            render_width,
            render_height,
        ]:
            raise _error(f"{page_id} coordinate authority/render dimensions drifted")
        try:
            with Image.open(render_path) as image:
                if image.size != (render_width, render_height):
                    raise _error(f"{page_id} rendered pixel dimensions drifted")
        except OSError as exc:
            raise _error(f"cannot decode {page_id} render") from exc
        page_by_id[page_id] = page
        page_results[page_id] = result
        pages.append(page)

    samples: list[dict[str, Any]] = []
    seen_sample_ids: set[str] = set()
    grouping_counts: dict[str, dict[str, int]] = {
        page_id: {"LINE": 0, "STRICT_ADJACENT_UNION": 0} for page_id in page_by_id
    }
    observed_line_indices: dict[str, list[int]] = {page_id: [] for page_id in page_by_id}
    observed_union_pairs: dict[str, list[tuple[int, int]]] = {page_id: [] for page_id in page_by_id}
    for page in pages:
        page_id = page["page_id"]
        expected_lines = _selected_line_indices(
            page_results[page_id]["lines"],
            width=page["render_width"],
            height=page["render_height"],
        )
        declared_lines = [
            raw.get("source_line_indices", [None])[0]
            for raw in raw_samples
            if type(raw) is dict
            and raw.get("page_id") == page_id
            and raw.get("grouping") == "LINE"
            and type(raw.get("source_line_indices")) is list
            and len(raw["source_line_indices"]) == 1
        ]
        if declared_lines != expected_lines:
            raise _error(f"{page_id} eligible LINE selection is incomplete or ineligible")
        expected_unions = _strict_union_pairs(
            expected_lines,
            page_results[page_id]["lines"],
            width=page["render_width"],
        )
        declared_unions = [
            tuple(raw["source_line_indices"])
            for raw in raw_samples
            if type(raw) is dict
            and raw.get("page_id") == page_id
            and raw.get("grouping") == "STRICT_ADJACENT_UNION"
            and type(raw.get("source_line_indices")) is list
            and len(raw["source_line_indices"]) == 2
        ]
        if declared_unions != expected_unions:
            raise _error(f"{page_id} strict-union selection is incomplete or invalid")
    padding = selection["source_padding_left_top_right_bottom"]
    border = selection["white_border_left_top_right_bottom"]
    for sample_index, raw_sample in enumerate(raw_samples):
        sample = _exact_dict(raw_sample, _CROP_SAMPLE_FIELDS, f"crop sample {sample_index}")
        sample_id = sample["sample_id"]
        page_id = sample["page_id"]
        grouping = sample["grouping"]
        if (
            type(sample_id) is not str
            or _SAMPLE_ID_RE.fullmatch(sample_id) is None
            or sample_id in seen_sample_ids
            or type(page_id) is not str
            or page_id not in page_by_id
            or not sample_id.startswith(f"{page_id}-")
            or sample["category"] != "SOURCE_BOUND_LABEL_LANE_CANDIDATE"
            or grouping not in {"LINE", "STRICT_ADJACENT_UNION"}
        ):
            raise _error("crop sample identity, page, category, or grouping drifted")
        seen_sample_ids.add(sample_id)
        page = page_by_id[page_id]
        result = page_results[page_id]
        indices = sample["source_line_indices"]
        expected_length = 1 if grouping == "LINE" else 2
        if (
            type(indices) is not list
            or len(indices) != expected_length
            or any(
                type(item) is not int or item < 0 or item >= len(result["lines"])
                for item in indices
            )
            or indices != sorted(set(indices))
        ):
            raise _error(f"{sample_id} source line indices drifted")
        if grouping == "STRICT_ADJACENT_UNION" and indices[1] <= indices[0]:
            raise _error(f"{sample_id} union source order drifted")
        expected_sample_id = (
            f"{page_id}-line-{indices[0]:03d}"
            if grouping == "LINE"
            else f"{page_id}-union-{indices[0]:03d}-{indices[1]:03d}"
        )
        if sample_id != expected_sample_id:
            raise _error(f"{sample_id} does not encode its exact frozen line selection")
        if grouping == "LINE":
            observed_line_indices[page_id].append(indices[0])
        else:
            observed_union_pairs[page_id].append((indices[0], indices[1]))
        line_boxes = [result["lines"][index]["raw_pixel_bbox"] for index in indices]
        source_bbox = [
            min(box[0] for box in line_boxes),
            min(box[1] for box in line_boxes),
            max(box[2] for box in line_boxes),
            max(box[3] for box in line_boxes),
        ]
        if sample["source_bbox_raw_pixels"] != source_bbox:
            raise _error(f"{sample_id} source bbox is not the exact line envelope")
        width = page["render_width"]
        height = page["render_height"]
        expected_padded = [
            max(0, source_bbox[0] - padding[0]),
            max(0, source_bbox[1] - padding[1]),
            min(width, source_bbox[2] + padding[2]),
            min(height, source_bbox[3] + padding[3]),
        ]
        if sample["padded_source_bbox_raw_pixels"] != expected_padded:
            raise _error(f"{sample_id} source padding drifted")
        expected_size = (
            expected_padded[2] - expected_padded[0] + border[0] + border[2],
            expected_padded[3] - expected_padded[1] + border[1] + border[3],
        )
        if sample["crop_width"] != expected_size[0] or sample["crop_height"] != expected_size[1]:
            raise _error(f"{sample_id} crop dimensions drifted")
        crop_path = _resolve(project_root, _safe_relative(sample["crop_path"], "crop path"), "crop")
        crop_sha = _sha(sample["crop_sha256"], f"{sample_id} crop hash")
        if crop_path.suffix != ".png" or sha256_file(crop_path) != crop_sha:
            raise _error(f"{sample_id} crop file/hash drifted")
        render_path = _resolve(project_root, page["render_path"], "render")
        try:
            with Image.open(render_path) as source_image, Image.open(crop_path) as crop_image:
                expected_crop = ImageOps.expand(
                    source_image.convert("RGB").crop(tuple(expected_padded)),
                    border=tuple(border),
                    fill="white",
                )
                actual_crop = crop_image.convert("RGB")
                pixels_equal = (
                    actual_crop.size == expected_crop.size
                    and ImageChops.difference(actual_crop, expected_crop).getbbox() is None
                )
        except OSError as exc:
            raise _error(f"cannot decode {sample_id} crop/render") from exc
        if not pixels_equal:
            raise _error(f"{sample_id} crop pixels are not bound to the declared render region")
        grouping_counts[page_id][grouping] += 1
        samples.append(sample)

    for page in pages:
        page_id = page["page_id"]
        counts = grouping_counts[page_id]
        if (
            page["selected_single_line_count"] != counts["LINE"]
            or page["selected_strict_union_count"] != counts["STRICT_ADJACENT_UNION"]
        ):
            raise _error(f"{page_id} selected sample denominators drifted")
        expected_lines = _selected_line_indices(
            page_results[page_id]["lines"],
            width=page["render_width"],
            height=page["render_height"],
        )
        if observed_line_indices[page_id] != expected_lines:
            raise _error(f"{page_id} eligible LINE selection is incomplete or ineligible")
        expected_unions = _strict_union_pairs(
            expected_lines,
            page_results[page_id]["lines"],
            width=page["render_width"],
        )
        if observed_union_pairs[page_id] != expected_unions:
            raise _error(f"{page_id} strict-union selection is incomplete or invalid")
    return pages, samples


def _validate_request(
    project_root: Path,
    request: dict[str, Any],
    *,
    manifest_path: Path,
    manifest_payload: bytes,
    manifest_samples: list[dict[str, Any]],
) -> None:
    _exact_dict(request, _REQUEST_FIELDS, "reader request")
    if (
        request["format_version"] != 1
        or request["experiment_id"] != "E-0024"
        or request["state"] != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or request["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or request["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or request["git_dirty"] is not False
        or request["reference_text_available_to_reader"] is not False
    ):
        raise _error("reader request identity, role, or firewall drifted")
    _git_sha(request["git_commit"], "request Git commit")
    manifest_ref = _validate_hash_ref(request["crop_manifest"], "request crop-manifest ref")
    if (
        manifest_ref["path"] != _project_relative(project_root, manifest_path)
        or manifest_ref["sha256"] != sha256_file(manifest_path)
        or manifest_ref["sha256"] != hashlib.sha256(manifest_payload).hexdigest()
    ):
        raise _error("request-to-crop-manifest binding drifted")
    raw_samples = request["samples"]
    if (
        type(raw_samples) is not list
        or len(raw_samples) != request["sample_count"]
        or len(raw_samples) != len(manifest_samples)
    ):
        raise _error("reader request sample denominator drifted")
    for index, (raw, source) in enumerate(zip(raw_samples, manifest_samples, strict=True)):
        sample = _exact_dict(raw, _REQUEST_SAMPLE_FIELDS, f"request sample {index}")
        expected = {
            key: source[key] for key in ("sample_id", "category", "crop_path", "crop_sha256")
        }
        if not same_typed_json_v1(sample, expected):
            raise _error(f"request sample {index} is not the exact crop-manifest projection")


def _validate_reader_result(
    result: dict[str, Any],
    *,
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    _exact_dict(result, _RESULT_FIELDS, "VietOCR result")
    if (
        result["format_version"] != 1
        or result["experiment_id"] != "E-0024"
        or result["state"] != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or result["dataset_role"] != request["dataset_role"]
        or result["evidence_role"] != request["evidence_role"]
        or result["reference_text_available_to_reader"] is not False
    ):
        raise _error("VietOCR result identity, role, or reference firewall drifted")
    raw_samples = result["samples"]
    request_samples = request["samples"]
    if (
        type(raw_samples) is not list
        or len(raw_samples) != result["sample_count"]
        or len(raw_samples) != request["sample_count"]
    ):
        raise _error("VietOCR result sample denominator drifted")
    samples: list[dict[str, Any]] = []
    for index, (raw, request_sample) in enumerate(zip(raw_samples, request_samples, strict=True)):
        sample = _exact_dict(raw, _RESULT_SAMPLE_FIELDS, f"VietOCR sample {index}")
        for field in ("sample_id", "category", "crop_path", "crop_sha256"):
            if not same_typed_json_v1(sample[field], request_sample[field]):
                raise _error(f"VietOCR sample {index} {field} binding drifted")
        if type(sample["raw_prediction"]) is not str:
            raise _error(f"VietOCR sample {index} raw prediction is not text")
        _integer(
            sample["processed_width"], f"VietOCR sample {index} processed width", positive=True
        )
        _integer(
            sample["processed_height"], f"VietOCR sample {index} processed height", positive=True
        )
        probability = sample["mean_decoded_character_probability"]
        if probability is not None:
            value = _finite(probability, f"VietOCR sample {index} probability", minimum=0.0)
            if value > 1.0:
                raise _error(f"VietOCR sample {index} probability exceeds one")
        _finite(sample["wall_seconds"], f"VietOCR sample {index} wall seconds", minimum=0.0)
        samples.append(sample)
    return samples


def _parse_timestamp(value: Any, label: str) -> datetime:
    if type(value) is not str:
        raise _error(f"{label} is not an ISO timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _error(f"{label} is not an ISO timestamp") from exc
    if timestamp.tzinfo is None:
        raise _error(f"{label} has no timezone")
    return timestamp


def _validate_run_manifest(
    project_root: Path,
    run: dict[str, Any],
    *,
    run_path: Path,
    request_path: Path,
    result_path: Path,
    sample_count: int,
) -> None:
    _exact_dict(run, _RUN_FIELDS, "VietOCR run manifest")
    if (
        run["format_version"] != 1
        or run["experiment_id"] != "E-0024"
        or run["state"] != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or run["git_dirty"] is not False
    ):
        raise _error("VietOCR run identity or state drifted")
    _git_sha(run["git_commit"], "run Git commit")
    if _parse_timestamp(run["completed_at"], "run completion") < _parse_timestamp(
        run["started_at"], "run start"
    ):
        raise _error("VietOCR run completion precedes its start")

    request_ref = _validate_hash_ref(run["request"], "run request ref")
    if request_ref["path"] != _project_relative(project_root, request_path) or request_ref[
        "sha256"
    ] != sha256_file(request_path):
        raise _error("run-to-request binding drifted")
    artifacts = _exact_dict(run["artifacts"], {"ocr_result"}, "run artifacts")
    result_ref = _validate_object_ref(artifacts["ocr_result"], "run OCR-result ref", suffix=".json")
    resolved_result = _verify_ref_file(
        project_root,
        result_ref,
        base=run_path.parent,
        label="run OCR result",
    )
    if resolved_result != result_path.resolve():
        raise _error("run OCR-result path differs from supplied result")

    configuration = _exact_dict(
        run["configuration"], _RUN_CONFIGURATION_FIELDS, "run configuration"
    )
    config_path = _resolve(
        project_root, _safe_relative(configuration["path"], "configuration path"), "configuration"
    )
    _sha(configuration["sha256"], "configuration hash")
    config_payload = _stable_bytes(config_path, "VietOCR pinned configuration")
    if (
        hashlib.sha256(config_payload).hexdigest() != configuration["sha256"]
        or configuration["network_policy"] != "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED"
        or configuration["cnn_pretrained_download"] is not False
        or configuration["beam_search"] is not False
        or configuration["reference_text_available_to_decoder"] is not False
    ):
        raise _error("VietOCR configuration file or inference firewall drifted")
    try:
        config = tomllib.loads(config_payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _error("VietOCR pinned configuration is not valid UTF-8 TOML") from exc

    runtime = _exact_dict(run["runtime"], _RUN_RUNTIME_FIELDS, "run runtime")
    if any(
        type(runtime[field]) is not str or not runtime[field]
        for field in (
            "external_root",
            "site_packages",
            "torch_cuda_build",
            "device",
            "compute_capability",
        )
    ):
        raise _error("run runtime identity is incomplete")
    if (
        type(runtime["packages"]) is not dict
        or not runtime["packages"]
        or any(
            type(key) is not str or not key or type(value) is not str or not value
            for key, value in runtime["packages"].items()
        )
    ):
        raise _error("run runtime package identity drifted")
    runtime_artifacts = _exact_dict(
        runtime["artifacts"], _RUN_RUNTIME_ARTIFACTS, "runtime artifacts"
    )
    external_root = Path(runtime["external_root"])
    if not external_root.is_absolute():
        raise _error("run external runtime root is not absolute")
    external_root = external_root.resolve()
    site_packages_path = _runtime_resolve(
        external_root, runtime["site_packages"], "runtime site-packages"
    )
    if not site_packages_path.is_dir():
        raise _error("runtime site-packages directory is absent")
    for name, raw in runtime_artifacts.items():
        artifact = _exact_dict(raw, _RUN_RUNTIME_ARTIFACT_FIELDS, f"runtime artifact {name}")
        _sha(artifact["sha256"], f"runtime artifact {name} hash")
        _integer(artifact["size_bytes"], f"runtime artifact {name} size", positive=True)
        if type(artifact["url"]) is not str or not artifact["url"].startswith("https://"):
            raise _error(f"runtime artifact {name} URL drifted")
        artifact_path = _runtime_resolve(
            external_root, artifact["path"], f"runtime artifact {name}"
        )
        artifact_payload = _stable_bytes(artifact_path, f"runtime artifact {name}")
        if (
            len(artifact_payload) != artifact["size_bytes"]
            or hashlib.sha256(artifact_payload).hexdigest() != artifact["sha256"]
        ):
            raise _error(f"runtime artifact {name} is absent or hash/size drifted")

    expected_config_keys = {
        "version",
        "status",
        "model_name",
        "package_version",
        "architecture",
        "license",
        "metadata_license_note",
        "inference",
        "runtime",
        "runtime_compatibility",
        "artifacts",
        "safety",
    }
    if type(config) is not dict or set(config) != expected_config_keys:
        raise _error("VietOCR pinned configuration identity drifted")
    inference = config.get("inference")
    compatibility = config.get("runtime_compatibility")
    configured_runtime = config.get("runtime")
    configured_artifacts = config.get("artifacts")
    configured_safety = config.get("safety")
    expected_inference = {
        "device": "cuda:0",
        "beam_search": False,
        "cnn_pretrained_download": False,
        "network_permitted": False,
        "reference_text_available_to_decoder": False,
        "random_seed": 20260807,
        "max_sequence_length": 128,
        "input_color_mode": "RGB",
        "upstream_image_height": 32,
        "upstream_image_min_width": 32,
        "upstream_image_max_width": 512,
    }
    expected_config_safety = {
        "numeric_authority": False,
        "period_authority": False,
        "unit_authority": False,
        "sign_authority": False,
        "geometry_authority": False,
        "mapping_authority": False,
        "automatic_truth_promotion": False,
        "automatic_post_correction": False,
        "history_access": False,
        "human_review_access": False,
        "template_access": False,
    }
    if (
        config.get("version") != 2
        or config.get("status") != "CALIBRATION_ONLY_RTX4090_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL"
        or config.get("model_name") != "VietOCR VGG Transformer"
        or config.get("package_version") != "0.3.13"
        or config.get("architecture") != "vgg19_bn_transformer"
        or not same_typed_json_v1(inference, expected_inference)
        or not same_typed_json_v1(configured_safety, expected_config_safety)
    ):
        raise _error("VietOCR pinned configuration safety/identity drifted")
    expected_compatibility = {
        "gpu_family": "NVIDIA_GEFORCE_RTX_4090_ADA",
        "minimum_compute_capability": [8, 9],
        "cuda_runtime": runtime["torch_cuda_build"],
        "bf16_required": False,
        "historical_blackwell_runtime_claimed": False,
    }
    expected_configured_runtime = {
        "site_packages": runtime["site_packages"],
        "python_major_minor": "3.11",
        "packages": runtime["packages"],
    }
    if (
        not same_typed_json_v1(compatibility, expected_compatibility)
        or runtime["device"] != "NVIDIA GeForce RTX 4090"
        or runtime["compute_capability"] != "8.9"
        or not same_typed_json_v1(configured_runtime, expected_configured_runtime)
    ):
        raise _error("VietOCR pinned runtime identity drifted")
    if (
        type(configured_artifacts) is not dict
        or set(configured_artifacts) != _RUN_RUNTIME_ARTIFACTS
    ):
        raise _error("VietOCR pinned artifact registry drifted")
    for name in _RUN_RUNTIME_ARTIFACTS:
        if not same_typed_json_v1(configured_artifacts[name], runtime_artifacts[name]):
            raise _error(f"VietOCR pinned runtime artifact {name} identity drifted")

    metrics = _exact_dict(run["metrics"], _RUN_METRIC_FIELDS, "run metrics")
    if metrics["sample_count"] != sample_count:
        raise _error("run sample denominator drifted")
    for field in _RUN_METRIC_FIELDS - {"sample_count"}:
        _finite(metrics[field], f"run metric {field}", minimum=0.0)
    safety = _exact_dict(run["safety"], _RUN_SAFETY_FIELDS, "run safety")
    if any(value is not False for value in safety.values()):
        raise _error("VietOCR run grants forbidden pipeline authority")


def validate_vietocr_semantic_receipt_payload_v1(value: Any) -> dict[str, Any]:
    """Validate a closed, self-contained global receipt payload."""

    receipt = _exact_dict(value, _RECEIPT_FIELDS, "VietOCR semantic receipt")
    if (
        receipt["format_version"] != FORMAT_VERSION
        or receipt["claim_boundary"] != CLAIM_BOUNDARY
        or receipt["experiment_id"] != "E-0024"
        or receipt["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or receipt["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
    ):
        raise _error("VietOCR semantic receipt identity or role drifted")
    inputs = _exact_dict(receipt["inputs"], _RECEIPT_INPUT_FIELDS, "receipt inputs")
    for name, raw in inputs.items():
        _validate_object_ref(raw, f"receipt input {name}", suffix=".json")
    pages = receipt["pages"]
    samples = receipt["samples"]
    metrics = _exact_dict(receipt["metrics"], _RECEIPT_METRIC_FIELDS, "receipt metrics")
    if type(pages) is not list or type(samples) is not list:
        raise _error("receipt pages/samples are not lists")
    page_ids: set[str] = set()
    page_counts: dict[str, dict[str, int]] = {}
    result_hashes: set[str] = set()
    render_hashes: set[str] = set()
    for index, raw in enumerate(pages):
        page = _exact_dict(raw, _RECEIPT_PAGE_FIELDS, f"receipt page {index}")
        page_id = page["page_id"]
        if (
            type(page_id) is not str
            or _PAGE_ID_RE.fullmatch(page_id) is None
            or page_id in page_ids
        ):
            raise _error("receipt page IDs are invalid or duplicated")
        result_ref = _validate_object_ref(
            page["result_ref"], f"receipt page {page_id} result", suffix=".json"
        )
        render_ref = _validate_object_ref(
            page["render_ref"], f"receipt page {page_id} render", suffix=".png"
        )
        if result_ref["sha256"] in result_hashes or render_ref["sha256"] in render_hashes:
            raise _error("receipt page result/render identities are duplicated")
        result_hashes.add(result_ref["sha256"])
        render_hashes.add(render_ref["sha256"])
        _integer(
            page["authenticated_line_count"], f"{page_id} authenticated line count", positive=True
        )
        line_count = _integer(page["single_line_sample_count"], f"{page_id} line sample count")
        union_count = _integer(
            page["diagnostic_union_sample_count"], f"{page_id} union sample count"
        )
        page_counts[page_id] = {"LINE": line_count, "STRICT_ADJACENT_UNION": union_count}
        page_ids.add(page_id)
    sample_ids: set[str] = set()
    observed_counts = {page_id: {"LINE": 0, "STRICT_ADJACENT_UNION": 0} for page_id in page_ids}
    for index, raw in enumerate(samples):
        sample = _exact_dict(raw, _RECEIPT_SAMPLE_FIELDS, f"receipt sample {index}")
        sample_id = sample["sample_id"]
        page_id = sample["page_id"]
        grouping = sample["grouping"]
        if (
            type(sample_id) is not str
            or _SAMPLE_ID_RE.fullmatch(sample_id) is None
            or sample_id in sample_ids
            or page_id not in page_ids
            or sample["category"] != "SOURCE_BOUND_LABEL_LANE_CANDIDATE"
            or grouping not in {"LINE", "STRICT_ADJACENT_UNION"}
        ):
            raise _error("receipt sample identity/category/grouping drifted")
        indices = sample["source_line_indices"]
        expected_length = 1 if grouping == "LINE" else 2
        if (
            type(indices) is not list
            or len(indices) != expected_length
            or any(type(item) is not int or item < 0 for item in indices)
            or indices != sorted(set(indices))
        ):
            raise _error(f"receipt sample {sample_id} line indices drifted")
        _bbox(sample["source_bbox_raw_pixels"], f"receipt sample {sample_id} source bbox")
        _bbox(sample["padded_source_bbox_raw_pixels"], f"receipt sample {sample_id} padded bbox")
        _validate_object_ref(sample["crop_ref"], f"receipt sample {sample_id} crop", suffix=".png")
        if type(sample["raw_prediction"]) is not str or sample[
            "normalized_prediction"
        ] != normalize_text(sample["raw_prediction"]):
            raise _error(f"receipt sample {sample_id} prediction normalization drifted")
        probability = sample["mean_decoded_character_probability"]
        if probability is not None:
            score = _finite(probability, f"receipt sample {sample_id} probability", minimum=0.0)
            if score > 1.0:
                raise _error(f"receipt sample {sample_id} probability exceeds one")
        dimensions = sample["processed_dimensions"]
        if type(dimensions) is not list or len(dimensions) != 2:
            raise _error(f"receipt sample {sample_id} processed dimensions drifted")
        _integer(dimensions[0], f"receipt sample {sample_id} processed width", positive=True)
        _integer(dimensions[1], f"receipt sample {sample_id} processed height", positive=True)
        if sample["diagnostic_only"] is not (grouping == "STRICT_ADJACENT_UNION"):
            raise _error(f"receipt sample {sample_id} diagnostic disposition drifted")
        observed_counts[page_id][grouping] += 1
        sample_ids.add(sample_id)
    if observed_counts != page_counts:
        raise _error("receipt per-page sample denominators drifted")
    expected_metrics = {
        "page_count": len(pages),
        "sample_count": len(samples),
        "single_line_sample_count": sum(item["LINE"] for item in observed_counts.values()),
        "diagnostic_union_sample_count": sum(
            item["STRICT_ADJACENT_UNION"] for item in observed_counts.values()
        ),
    }
    if not same_typed_json_v1(metrics, expected_metrics):
        raise _error("receipt aggregate denominators drifted")
    if not same_typed_json_v1(receipt["safety"], _RECEIPT_SAFETY):
        raise _error("receipt safety boundary drifted")
    return canonical_clone_v1(receipt)


def validate_vietocr_semantic_receipt_v1(
    project_root: Path,
    crop_manifest_path: Path,
    reader_request_path: Path,
    ocr_result_path: Path,
    run_manifest_path: Path,
) -> AuthenticatedVietOCRSemanticReceiptV1:
    """Authenticate one complete global E-0024 artifact chain and build its receipt."""

    project_root = project_root.resolve()
    manifest_path = _resolve(project_root, crop_manifest_path, "crop manifest")
    request_path = _resolve(project_root, reader_request_path, "reader request")
    result_path = _resolve(project_root, ocr_result_path, "VietOCR result")
    run_path = _resolve(project_root, run_manifest_path, "VietOCR run manifest")
    manifest, manifest_payload = _load_json(manifest_path, "crop manifest")
    request, request_payload = _load_json(request_path, "reader request")
    result, result_payload = _load_json(result_path, "VietOCR result")
    run, run_payload = _load_json(run_path, "VietOCR run manifest")

    pages, crop_samples = _validate_crop_manifest(project_root, manifest)
    _validate_request(
        project_root,
        request,
        manifest_path=manifest_path,
        manifest_payload=manifest_payload,
        manifest_samples=crop_samples,
    )
    reader_samples = _validate_reader_result(result, request=request)
    _validate_run_manifest(
        project_root,
        run,
        run_path=run_path,
        request_path=request_path,
        result_path=result_path,
        sample_count=len(reader_samples),
    )

    page_records = []
    for page in pages:
        render_path = _resolve(project_root, page["render_path"], "render")
        result_object_path = _resolve(project_root, page["result_path"], "page result")
        page_records.append(
            {
                "page_id": page["page_id"],
                "result_ref": _file_ref(project_root, result_object_path),
                "render_ref": _file_ref(project_root, render_path),
                "authenticated_line_count": page["authenticated_line_count"],
                "single_line_sample_count": page["selected_single_line_count"],
                "diagnostic_union_sample_count": page["selected_strict_union_count"],
            }
        )
    samples = []
    for crop, prediction in zip(crop_samples, reader_samples, strict=True):
        crop_path = _resolve(project_root, crop["crop_path"], "crop")
        samples.append(
            {
                "sample_id": crop["sample_id"],
                "page_id": crop["page_id"],
                "grouping": crop["grouping"],
                "category": crop["category"],
                "source_line_indices": list(crop["source_line_indices"]),
                "source_bbox_raw_pixels": list(crop["source_bbox_raw_pixels"]),
                "padded_source_bbox_raw_pixels": list(crop["padded_source_bbox_raw_pixels"]),
                "crop_ref": _file_ref(project_root, crop_path),
                "raw_prediction": prediction["raw_prediction"],
                "normalized_prediction": normalize_text(prediction["raw_prediction"]),
                "mean_decoded_character_probability": prediction[
                    "mean_decoded_character_probability"
                ],
                "processed_dimensions": [
                    prediction["processed_width"],
                    prediction["processed_height"],
                ],
                "diagnostic_only": crop["grouping"] == "STRICT_ADJACENT_UNION",
            }
        )
    line_count = sum(item["grouping"] == "LINE" for item in samples)
    union_count = len(samples) - line_count
    receipt = {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "experiment_id": "E-0024",
        "dataset_role": request["dataset_role"],
        "evidence_role": request["evidence_role"],
        "inputs": {
            "crop_manifest": _file_ref(project_root, manifest_path, manifest_payload),
            "reader_request": _file_ref(project_root, request_path, request_payload),
            "ocr_result": _file_ref(project_root, result_path, result_payload),
            "run_manifest": _file_ref(project_root, run_path, run_payload),
        },
        "pages": page_records,
        "samples": samples,
        "metrics": {
            "page_count": len(page_records),
            "sample_count": len(samples),
            "single_line_sample_count": line_count,
            "diagnostic_union_sample_count": union_count,
        },
        "safety": canonical_clone_v1(_RECEIPT_SAFETY),
    }
    authenticated = AuthenticatedVietOCRSemanticReceiptV1(
        validate_vietocr_semantic_receipt_payload_v1(receipt),
        _AUTHENTICATION_TOKEN,
    )
    receipt_id = id(authenticated)

    def discard(reference: weakref.ReferenceType[AuthenticatedVietOCRSemanticReceiptV1]) -> None:
        current = _AUTHENTICATED_RECEIPTS.get(receipt_id)
        if current is not None and current[0] is reference:
            _AUTHENTICATED_RECEIPTS.pop(receipt_id, None)

    reference = weakref.ref(authenticated, discard)
    _AUTHENTICATED_RECEIPTS[receipt_id] = (
        reference,
        canonical_json_sha256_v1(receipt),
    )
    return authenticated


def _authenticated_payload(
    receipt: Any,
) -> dict[str, Any]:
    if type(receipt) is not AuthenticatedVietOCRSemanticReceiptV1:
        raise _error("page binding requires a replay-authenticated VietOCR receipt")
    payload = receipt._clone_for_internal_replay(_AUTHENTICATION_TOKEN)
    authority = _AUTHENTICATED_RECEIPTS.get(id(receipt))
    if (
        authority is None
        or authority[0]() is not receipt
        or canonical_json_sha256_v1(payload) != authority[1]
    ):
        raise _error("VietOCR receipt lost its replay-authenticated authority")
    return validate_vietocr_semantic_receipt_payload_v1(payload)


def replay_vietocr_semantic_receipt_v1(
    project_root: Path,
    crop_manifest_path: Path,
    reader_request_path: Path,
    ocr_result_path: Path,
    run_manifest_path: Path,
    receipt: Any,
) -> AuthenticatedVietOCRSemanticReceiptV1:
    """Rebuild a receipt from its source artifacts and require typed equality."""

    expected = _authenticated_payload(receipt)
    rebuilt = validate_vietocr_semantic_receipt_v1(
        project_root,
        crop_manifest_path,
        reader_request_path,
        ocr_result_path,
        run_manifest_path,
    )
    if not same_typed_json_v1(_authenticated_payload(rebuilt), expected):
        raise _error("VietOCR semantic receipt does not replay exactly")
    return rebuilt


def _build_page_binding(source: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    if source["route"] != "DOMINANT_RASTER_OCR" or source["terminal"] is not False:
        raise _error("VietOCR semantic page binding requires a nonterminal OCR V2 source")
    result_sha = source["page_result_sha256"]
    render_ref = source["page_result"].get("input_render_ref")
    if type(render_ref) is not dict:
        raise _error("source projection has no authenticated input render")
    render_sha = render_ref.get("sha256")
    candidates = [
        page
        for page in receipt["pages"]
        if page["result_ref"]["sha256"] == result_sha and page["render_ref"]["sha256"] == render_sha
    ]
    if len(candidates) != 1:
        raise _error("global receipt does not contain exactly one matching result/render page")
    page = candidates[0]
    page_id = page["page_id"]
    atoms_by_line: dict[int, dict[str, Any]] = {}
    for atom in source["neutral_page_v1"]["atoms"]:
        locator = atom["upstream_locator"]
        if (
            atom["kind"] == "LINE"
            and atom["authority"] == "AUTHENTICATED_PRIMARY"
            and type(locator) is dict
            and locator.get("kind") == "OCR_LINE_INDEX"
            and type(locator.get("line_index")) is int
        ):
            line_index = locator["line_index"]
            if line_index in atoms_by_line:
                raise _error("source projection contains duplicate primary OCR line indices")
            atoms_by_line[line_index] = atom
    page_samples = [item for item in receipt["samples"] if item["page_id"] == page_id]
    bound_samples = []
    unique_atom_ids: set[str] = set()
    occurrence_count = 0
    for sample in page_samples:
        source_atoms = []
        line_boxes = []
        for line_index in sample["source_line_indices"]:
            atom = atoms_by_line.get(line_index)
            if atom is None:
                raise _error(f"{sample['sample_id']} has no exact primary OCR LINE atom")
            if atom["pixel_bbox"] is None:
                raise _error(f"{sample['sample_id']} source LINE atom has no pixel bbox")
            line_boxes.append(atom["pixel_bbox"])
            source_atoms.append(
                {
                    "source_atom_id": atom["source_local_id"],
                    "line_index": line_index,
                    "raw_text": atom["raw_text"],
                    "pixel_bbox": canonical_clone_v1(atom["pixel_bbox"]),
                    "canonical_bbox_mpt": canonical_clone_v1(atom["canonical_bbox_mpt"]),
                }
            )
            unique_atom_ids.add(atom["source_local_id"])
            occurrence_count += 1
        expected_box = [
            min(box[0] for box in line_boxes),
            min(box[1] for box in line_boxes),
            max(box[2] for box in line_boxes),
            max(box[3] for box in line_boxes),
        ]
        if not same_typed_json_v1(expected_box, sample["source_bbox_raw_pixels"]):
            raise _error(f"{sample['sample_id']} receipt bbox differs from exact V2 LINE atoms")
        bound_samples.append({**canonical_clone_v1(sample), "source_atoms": source_atoms})
    line_count = sum(not item["diagnostic_only"] for item in bound_samples)
    union_count = len(bound_samples) - line_count
    return {
        "format_version": PAGE_FORMAT_VERSION,
        "claim_boundary": PAGE_CLAIM_BOUNDARY,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "global_receipt_sha256": canonical_json_sha256_v1(receipt),
        "page_id": page_id,
        "page_source_binding": {
            "route": source["route"],
            "page_result_sha256": result_sha,
            "render_sha256": render_sha,
        },
        "samples": bound_samples,
        "metrics": {
            "sample_count": len(bound_samples),
            "single_line_sample_count": line_count,
            "diagnostic_union_sample_count": union_count,
            "bound_source_line_occurrence_count": occurrence_count,
            "unique_source_line_count": len(unique_atom_ids),
        },
        "safety": canonical_clone_v1(_PAGE_SAFETY),
    }


def validate_vietocr_semantic_page_binding_v1(
    value: Any,
    source_projection_v2: Any,
    receipt: Any,
) -> dict[str, Any]:
    """Validate and exactly replay one page-local semantic binding."""

    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except SourceStructureContractV2Error as exc:
        raise _error("source projection V2 is invalid") from exc
    global_receipt = _authenticated_payload(receipt)
    binding = _exact_dict(value, _PAGE_BINDING_FIELDS, "VietOCR page binding")
    if (
        binding["format_version"] != PAGE_FORMAT_VERSION
        or binding["claim_boundary"] != PAGE_CLAIM_BOUNDARY
    ):
        raise _error("VietOCR page binding identity drifted")
    _exact_dict(binding["page_source_binding"], _PAGE_SOURCE_BINDING_FIELDS, "page source binding")
    raw_samples = binding["samples"]
    if type(raw_samples) is not list:
        raise _error("page binding samples are not a list")
    for index, raw in enumerate(raw_samples):
        sample = _exact_dict(raw, _BOUND_SAMPLE_FIELDS, f"bound sample {index}")
        atoms = sample["source_atoms"]
        if type(atoms) is not list or not atoms:
            raise _error(f"bound sample {index} has no source atoms")
        for atom_index, atom in enumerate(atoms):
            _exact_dict(atom, _BOUND_ATOM_FIELDS, f"bound sample {index} atom {atom_index}")
    _exact_dict(binding["metrics"], _PAGE_METRIC_FIELDS, "page binding metrics")
    if not same_typed_json_v1(binding["safety"], _PAGE_SAFETY):
        raise _error("page binding safety boundary drifted")
    rebuilt = _build_page_binding(source, global_receipt)
    if not same_typed_json_v1(binding, rebuilt):
        raise _error("VietOCR semantic page binding does not replay exactly")
    return canonical_clone_v1(binding)


def bind_vietocr_semantic_page_v1(
    source_projection_v2: Any,
    receipt: Any,
) -> dict[str, Any]:
    """Bind the matching global proposal subset to exact V2 OCR LINE atoms."""

    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except SourceStructureContractV2Error as exc:
        raise _error("source projection V2 is invalid") from exc
    global_receipt = _authenticated_payload(receipt)
    binding = _build_page_binding(source, global_receipt)
    return validate_vietocr_semantic_page_binding_v1(binding, source, receipt)


__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "PAGE_CLAIM_BOUNDARY",
    "PAGE_FORMAT_VERSION",
    "VietOCRSemanticReceiptV1Error",
    "AuthenticatedVietOCRSemanticReceiptV1",
    "bind_vietocr_semantic_page_v1",
    "replay_vietocr_semantic_receipt_v1",
    "validate_vietocr_semantic_page_binding_v1",
    "validate_vietocr_semantic_receipt_payload_v1",
    "validate_vietocr_semantic_receipt_v1",
]
