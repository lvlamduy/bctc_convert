"""Replay-authenticate generic all-LINE VietOCR Transformer proposals.

The receipt is intentionally a proposal boundary, not a new reader.  It binds
the selected Transformer run to exact frozen crop pixels and, page by page, to
authenticated V3 LINE geometry.  PP-OCR transcripts are never consulted or
copied into this receipt; numeric, geometry, accounting and schema authority
remain outside this lane.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tomllib
import weakref
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageChops, ImageOps

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

FORMAT_VERSION = "GENERIC_VIETOCR_ALL_LINE_SEMANTIC_RECEIPT_V2"
PAGE_FORMAT_VERSION = "GENERIC_VIETOCR_ALL_LINE_PAGE_BINDING_V2"
EXPERIMENT_ID = "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1"
CLAIM_BOUNDARY = (
    "REPLAY_AUTHENTICATED_SOURCE_BOUND_VIETOCR_TEXT_PROPOSALS_ONLY_"
    "NO_NUMERIC_GEOMETRY_ACCOUNTING_OR_SCHEMA_AUTHORITY"
)
PAGE_CLAIM_BOUNDARY = (
    "EXACT_V3_LINE_GEOMETRY_TO_VIETOCR_CROP_PROPOSAL_BINDING_ONLY_"
    "NO_PPOCR_TEXT_IDENTITY_OR_STRUCTURE_PROMOTION"
)
TRANSFORMER_PROFILE_ID = "VIETOCR_0_3_13_VGG19_BN_TRANSFORMER_RTX4090_V1"
_SELECTED_RUN_GIT_COMMIT = "2f8cab8f8b352f4515c39809c2a826f0dc7a813e"
_TRANSFORMER_CONFIG_SHA256 = "aa007448e2ed4f940693c3b4c03ae47111cf1ed00580d13c05a41941e5094119"
_TRANSFORMER_ARTIFACT_IDENTITIES = {
    "wheel": ("07b3777e5176b0d733cb056b68bd817371605f4b3514795fbf91ad4e181b8ccf", 34641),
    "base_config": ("9c8283fadb950f06f5d3400475f80d5355700ff315c9c48b7875e6ea66647d1c", 1809),
    "model_config": ("0df9feee197754c7381871e5dfd07c6f3e292a4853eece6f1af240923e57c907", 505),
    "weights": ("380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59", 151815373),
}
_TRANSFORMER_RUNTIME_PACKAGES = {
    "vietocr": "0.3.13",
    "torch": "2.12.0+cu130",
    "torchvision": "0.27.0+cu130",
    "pillow": "12.3.0",
    "numpy": "2.3.5",
    "einops": "0.8.2",
    "pyyaml": "6.0.2",
}
_RUNNER_IMPLEMENTATION_REFS = {
    "cli": {
        "path": "scripts/models/run_vietocr_line_reader.py",
        "sha256": "0000d41962f8311c93c6817a0b9fb0f28b5405b9f5aefb876fbbfc1909d08df5",
        "size_bytes": 1169,
    },
    "reader": {
        "path": "src/bctc_ai/ocr/vietocr_line_reader.py",
        "sha256": "9b6a48d14eab452f97f80fbaeb157c625553bafee0a2411403ab1a3cf53200b6",
        "size_bytes": 21081,
    },
}


class VietOCRSemanticReceiptV2Error(ValueError):
    """The v2 artifact chain, model profile, or page binding drifted."""


class AuthenticatedVietOCRSemanticReceiptV2:
    """Opaque handle minted only after complete artifact replay."""

    __slots__ = ("__payload", "__weakref__")

    def __init__(self, payload: dict[str, Any], token: object) -> None:
        if token is not _AUTHENTICATION_TOKEN:
            raise _error("authenticated v2 receipts can only be created by artifact replay")
        self.__payload = canonical_clone_v1(payload)

    def __getitem__(self, key: str) -> Any:
        return canonical_clone_v1(self.__payload[key])

    def __eq__(self, other: object) -> bool:
        return type(other) is AuthenticatedVietOCRSemanticReceiptV2 and same_typed_json_v1(
            self.__payload, other.__payload
        )

    def _clone_for_internal_replay(self, token: object) -> dict[str, Any]:
        if token is not _AUTHENTICATION_TOKEN:
            raise _error("authenticated v2 receipt payload is opaque")
        return canonical_clone_v1(self.__payload)


_AUTHENTICATION_TOKEN = object()
_AUTHENTICATED_RECEIPTS: dict[
    int, tuple[weakref.ReferenceType[AuthenticatedVietOCRSemanticReceiptV2], str]
] = {}

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_RE = re.compile(r"^[0-9a-f]{40}$")
_PAGE_ID_RE = re.compile(r"^page-[0-9]{4,}$")
_SAMPLE_ID_RE = re.compile(r"^(page-[0-9]{4,})-line-([0-9]{4,})$")

_MANIFEST_FIELDS = {
    "authority",
    "dataset_role",
    "format_version",
    "git_commit",
    "git_dirty",
    "inference_firewall",
    "input_spec_ref",
    "page_count",
    "pages",
    "sample_count",
    "samples",
    "selection_rule",
    "state",
}
_MANIFEST_PAGE_FIELDS = {
    "authenticated_line_count",
    "page_id",
    "render_height",
    "render_ref",
    "render_width",
    "result_ref",
    "selected_line_count",
}
_MANIFEST_SAMPLE_FIELDS = {
    "category",
    "crop_height",
    "crop_path",
    "crop_sha256",
    "crop_width",
    "grouping",
    "padded_source_bbox_raw_pixels",
    "page_id",
    "sample_id",
    "source_bbox_raw_pixels",
    "source_line_index",
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
    *_REQUEST_SAMPLE_FIELDS,
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
_CONFIG_REF_FIELDS = {
    "path",
    "sha256",
    "network_policy",
    "cnn_pretrained_download",
    "beam_search",
    "reference_text_available_to_decoder",
}
_RUNTIME_FIELDS = {
    "external_root",
    "site_packages",
    "packages",
    "torch_cuda_build",
    "device",
    "compute_capability",
    "artifacts",
}
_RUNTIME_ARTIFACT_NAMES = {"wheel", "base_config", "model_config", "weights"}
_RUNTIME_ARTIFACT_FIELDS = {"path", "sha256", "size_bytes", "url"}
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
_INPUT_SPEC_FIELDS = {"dataset_role", "format_version", "pages"}
_INPUT_PAGE_FIELDS = {"render_ref", "result_ref"}

_RECEIPT_FIELDS = {
    "format_version",
    "claim_boundary",
    "experiment_id",
    "dataset_role",
    "evidence_role",
    "reader_profile",
    "inputs",
    "pages",
    "samples",
    "metrics",
    "safety",
}
_PROFILE_FIELDS = {
    "profile_id",
    "model_name",
    "architecture",
    "package_version",
    "configuration_ref",
    "runtime_identity_sha256",
    "runtime_artifact_sha256",
    "runner_implementation_refs",
    "selected_run_git_commit",
}
_RECEIPT_INPUT_FIELDS = {
    "input_spec",
    "crop_manifest",
    "reader_request",
    "ocr_result",
    "run_manifest",
}
_RECEIPT_PAGE_FIELDS = {
    "page_id",
    "result_ref",
    "render_ref",
    "authenticated_line_count",
    "line_sample_count",
}
_RECEIPT_SAMPLE_FIELDS = {
    "sample_id",
    "page_id",
    "source_line_index",
    "source_bbox_raw_pixels",
    "padded_source_bbox_raw_pixels",
    "crop_ref",
    "raw_prediction",
    "normalized_prediction",
    "mean_decoded_character_probability",
    "processed_dimensions",
}
_RECEIPT_METRIC_FIELDS = {"page_count", "sample_count", "all_line_denominator_complete"}
_RECEIPT_SAFETY = {
    "reader_output_is_proposal_only": True,
    "ppocr_transcript_used_for_semantic_identity": False,
    "geometry_authority": False,
    "numeric_authority": False,
    "period_authority": False,
    "unit_authority": False,
    "sign_authority": False,
    "scope_authority": False,
    "accounting_authority": False,
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
_PAGE_SOURCE_FIELDS = {"route", "page_result_sha256", "render_sha256"}
_BOUND_SAMPLE_FIELDS = _RECEIPT_SAMPLE_FIELDS | {"source_atom"}
_BOUND_ATOM_FIELDS = {"source_atom_id", "line_index", "pixel_bbox", "canonical_bbox_mpt"}
_PAGE_METRIC_FIELDS = {
    "sample_count",
    "authenticated_line_count",
    "unique_source_line_count",
    "all_line_denominator_complete",
}
_PAGE_SAFETY = {
    **_RECEIPT_SAFETY,
    "source_atom_text_replaced": False,
    "lag_observation_assembled": False,
}

_SELECTION_RULE = {
    "deskew": False,
    "grouping": "ONE_CROP_PER_AUTHENTICATED_V3_LINE",
    "line_order": "V3_RESULT_LINES_ARRAY_ORDER",
    "primary_atom_type": "V3_AUTHENTICATED_LINE_WITH_RAW_PIXEL_BBOX",
    "resize": False,
    "selection": "ALL_AUTHENTICATED_LINES_WITHOUT_TEXT_OR_GEOMETRY_FILTERING",
    "source_padding_left_top_right_bottom": [8, 4, 8, 4],
    "threshold": False,
    "unions": False,
    "white_border_left_top_right_bottom": [12, 8, 12, 8],
}


def _error(message: str) -> VietOCRSemanticReceiptV2Error:
    return VietOCRSemanticReceiptV2Error(message)


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _integer(value: Any, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise _error(f"{label} is not a valid integer")
    return value


def _finite(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if type(value) not in {int, float} or type(value) is bool or not math.isfinite(value):
        raise _error(f"{label} is not finite")
    result = float(value)
    if result < minimum:
        raise _error(f"{label} is below its minimum")
    return result


def _bbox(
    value: Any, label: str, *, width: int | None = None, height: int | None = None
) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
        or (width is not None and value[2] > width)
        or (height is not None and value[3] > height)
    ):
        raise _error(f"{label} is not a valid integer bbox")
    return list(value)


def _safe_relative(value: Any, label: str) -> Path:
    if type(value) is not str or not value or "\\" in value:
        raise _error(f"{label} is not a safe relative path")
    path = Path(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise _error(f"{label} is not a safe relative path")
    return path


def _resolve(root: Path, value: Path | str, label: str) -> Path:
    base = root.resolve()
    raw = Path(value)
    path = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    if not path.is_relative_to(base):
        raise _error(f"{label} escapes project root")
    return path


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
        raise _error(f"{label} changed while read")
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


def _file_ref(root: Path, path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _object_ref(value: Any, label: str, suffix: str | None = None) -> dict[str, Any]:
    reference = _exact(value, _OBJECT_REF_FIELDS, label)
    path = _safe_relative(reference["path"], f"{label} path")
    if suffix is not None and path.suffix != suffix:
        raise _error(f"{label} suffix drifted")
    _sha(reference["sha256"], f"{label} hash")
    _integer(reference["size_bytes"], f"{label} size", positive=True)
    return reference


def _verify_project_ref(root: Path, reference: dict[str, Any], label: str) -> tuple[Path, bytes]:
    path = _resolve(root, _safe_relative(reference["path"], f"{label} path"), label)
    payload = _stable_bytes(path, label)
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error(f"{label} is missing or hash/size drifted")
    return path, payload


def _path_has_suffix(path: str, suffix: str) -> bool:
    path_parts = Path(path).parts
    suffix_parts = Path(suffix).parts
    return len(path_parts) >= len(suffix_parts) and path_parts[-len(suffix_parts) :] == suffix_parts


def _runtime_path(external_root: Path, value: Any, label: str) -> Path:
    relative = _safe_relative(value, f"{label} path")
    path = (external_root / relative).resolve()
    if not path.is_relative_to(external_root):
        raise _error(f"{label} escapes runtime root")
    return path


def _validate_input_spec(
    root: Path, manifest: dict[str, Any]
) -> tuple[Path, bytes, list[dict[str, Any]]]:
    reference = _object_ref(manifest["input_spec_ref"], "input-spec ref", ".json")
    path, payload = _verify_project_ref(root, reference, "input spec")
    try:
        spec = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("input spec is not valid UTF-8 JSON") from exc
    _exact(spec, _INPUT_SPEC_FIELDS, "input spec")
    if (
        spec["format_version"] != "V3_AUTHENTICATED_LINE_MULTIPAGE_BATCH_INPUT_V1"
        or spec["dataset_role"] != "DEVELOPMENT_REPLAY"
    ):
        raise _error("input-spec identity drifted")
    pages = spec["pages"]
    if type(pages) is not list or not pages:
        raise _error("input-spec pages are invalid")
    for index, page in enumerate(pages):
        _exact(page, _INPUT_PAGE_FIELDS, f"input-spec page {index}")
        _object_ref(page["result_ref"], f"input-spec page {index} result", ".json")
        _object_ref(page["render_ref"], f"input-spec page {index} render", ".png")
    return path, payload, pages


def _validate_manifest(
    root: Path, manifest: dict[str, Any]
) -> tuple[
    Path,
    bytes,
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    _exact(manifest, _MANIFEST_FIELDS, "crop manifest")
    if (
        manifest["format_version"] != "V3_AUTHENTICATED_LINE_GEOMETRY_ONLY_CROP_MANIFEST_V2"
        or manifest["state"] != "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE"
        or manifest["dataset_role"] != "DEVELOPMENT_REPLAY"
        or manifest["git_dirty"] is not False
        or type(manifest["git_commit"]) is not str
        or _GIT_RE.fullmatch(manifest["git_commit"]) is None
    ):
        raise _error("crop-manifest identity or frozen state drifted")
    authority = _exact(
        manifest["authority"],
        {
            "geometry_change",
            "numeric_value_period_unit_sign_scope_schema_authority",
            "semantic_acceptance",
        },
        "crop authority",
    )
    if any(value is not False for value in authority.values()):
        raise _error("crop manifest grants forbidden authority")
    expected_firewall = {
        "bank_filename_physical_page_family_or_control_role_exposed_to_reader": False,
        "expected_labels_available_to_crop_selector": False,
        "ocr_transcript_field_consulted_by_crop_selector": False,
        "reader_receives_crop_pixels_only": True,
        "role_a_available_to_crop_selector": False,
    }
    if not same_typed_json_v1(manifest["inference_firewall"], expected_firewall):
        raise _error("crop inference firewall drifted")
    if not same_typed_json_v1(manifest["selection_rule"], _SELECTION_RULE):
        raise _error("all-LINE selection rule drifted")

    input_path, input_payload, input_pages = _validate_input_spec(root, manifest)
    pages = manifest["pages"]
    samples = manifest["samples"]
    if (
        type(pages) is not list
        or type(samples) is not list
        or len(pages) != _integer(manifest["page_count"], "manifest page count", positive=True)
        or len(samples)
        != _integer(manifest["sample_count"], "manifest sample count", positive=True)
        or len(pages) != len(input_pages)
    ):
        raise _error("crop-manifest denominators drifted")

    page_state: dict[str, tuple[dict[str, Any], dict[str, Any], bytes]] = {}
    for index, (raw_page, input_page) in enumerate(zip(pages, input_pages, strict=True), start=1):
        page = _exact(raw_page, _MANIFEST_PAGE_FIELDS, f"crop page {index}")
        page_id = page["page_id"]
        if page_id != f"page-{index:04d}" or page_id in page_state:
            raise _error("crop page IDs are not opaque sequential IDs")
        result_ref = _object_ref(page["result_ref"], f"{page_id} result", ".json")
        render_ref = _object_ref(page["render_ref"], f"{page_id} render", ".png")
        if not same_typed_json_v1(result_ref, input_page["result_ref"]) or not same_typed_json_v1(
            render_ref, input_page["render_ref"]
        ):
            raise _error(f"{page_id} input-spec page binding drifted")
        result_path, result_payload = _verify_project_ref(root, result_ref, f"{page_id} result")
        _render_path, render_payload = _verify_project_ref(root, render_ref, f"{page_id} render")
        try:
            result = json.loads(result_payload, object_pairs_hook=_reject_duplicate_keys)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error(f"{page_id} result is invalid JSON") from exc
        if type(result) is not dict:
            raise _error(f"{page_id} result is not an object")
        lines = result.get("lines")
        count = _integer(page["authenticated_line_count"], f"{page_id} line count", positive=True)
        embedded_render = result.get("input_render_ref") if type(result) is dict else None
        if (
            result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
            or type(lines) is not list
            or len(lines) != count
            or page["selected_line_count"] != count
            or type(embedded_render) is not dict
            or embedded_render.get("sha256") != render_ref["sha256"]
            or embedded_render.get("size_bytes") != render_ref["size_bytes"]
            or not _path_has_suffix(render_ref["path"], embedded_render.get("path", ""))
        ):
            raise _error(f"{page_id} authenticated all-LINE denominator drifted")
        width = _integer(page["render_width"], f"{page_id} render width", positive=True)
        height = _integer(page["render_height"], f"{page_id} render height", positive=True)
        try:
            with Image.open(BytesIO(render_payload)) as image:
                if image.size != (width, height):
                    raise _error(f"{page_id} render dimensions drifted")
        except OSError as exc:
            raise _error(f"cannot decode {page_id} render") from exc
        for line_index, line in enumerate(lines):
            if type(line) is not dict:
                raise _error(f"{page_id} line {line_index} is invalid")
            _bbox(
                line.get("raw_pixel_bbox"),
                f"{page_id} line {line_index} bbox",
                width=width,
                height=height,
            )
        page_state[page_id] = (page, result, render_payload)

    by_page: dict[str, list[int]] = {page_id: [] for page_id in page_state}
    verified_crop_refs: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()
    padding = _SELECTION_RULE["source_padding_left_top_right_bottom"]
    border = _SELECTION_RULE["white_border_left_top_right_bottom"]
    for index, raw_sample in enumerate(samples):
        sample = _exact(raw_sample, _MANIFEST_SAMPLE_FIELDS, f"crop sample {index}")
        match = (
            _SAMPLE_ID_RE.fullmatch(sample["sample_id"])
            if type(sample["sample_id"]) is str
            else None
        )
        page_id = sample["page_id"]
        line_index = sample["source_line_index"]
        if (
            match is None
            or match.group(1) != page_id
            or int(match.group(2)) != line_index
            or sample["sample_id"] in seen_ids
            or page_id not in page_state
            or sample["grouping"] != "LINE"
            or sample["category"] != "SOURCE_BOUND_AUTHENTICATED_LINE"
        ):
            raise _error("crop sample opaque identity/category/grouping drifted")
        seen_ids.add(sample["sample_id"])
        page, result, render_payload = page_state[page_id]
        if type(line_index) is not int or not 0 <= line_index < len(result["lines"]):
            raise _error(f"{sample['sample_id']} line index drifted")
        source_box = _bbox(
            result["lines"][line_index]["raw_pixel_bbox"],
            f"{sample['sample_id']} source bbox",
            width=page["render_width"],
            height=page["render_height"],
        )
        if sample["source_bbox_raw_pixels"] != source_box:
            raise _error(f"{sample['sample_id']} source bbox differs from exact V3 LINE")
        expected_padded = [
            max(0, source_box[0] - padding[0]),
            max(0, source_box[1] - padding[1]),
            min(page["render_width"], source_box[2] + padding[2]),
            min(page["render_height"], source_box[3] + padding[3]),
        ]
        if sample["padded_source_bbox_raw_pixels"] != expected_padded:
            raise _error(f"{sample['sample_id']} padding drifted")
        expected_size = (
            expected_padded[2] - expected_padded[0] + border[0] + border[2],
            expected_padded[3] - expected_padded[1] + border[1] + border[3],
        )
        if [sample["crop_width"], sample["crop_height"]] != list(expected_size):
            raise _error(f"{sample['sample_id']} crop dimensions drifted")
        crop_path = _resolve(
            root,
            _safe_relative(sample["crop_path"], f"{sample['sample_id']} crop path"),
            "crop",
        )
        crop_payload = _stable_bytes(crop_path, f"{sample['sample_id']} crop")
        if hashlib.sha256(crop_payload).hexdigest() != _sha(
            sample["crop_sha256"], f"{sample['sample_id']} crop hash"
        ):
            raise _error(f"{sample['sample_id']} crop hash drifted")
        verified_crop_refs[sample["sample_id"]] = _file_ref(root, crop_path, crop_payload)
        try:
            with (
                Image.open(BytesIO(render_payload)) as source,
                Image.open(BytesIO(crop_payload)) as actual,
            ):
                expected = ImageOps.expand(
                    source.convert("RGB").crop(tuple(expected_padded)),
                    border=tuple(border),
                    fill="white",
                )
                matches = (
                    actual.size == expected.size
                    and ImageChops.difference(actual.convert("RGB"), expected).getbbox() is None
                )
        except OSError as exc:
            raise _error(f"cannot decode {sample['sample_id']} crop") from exc
        if not matches:
            raise _error(f"{sample['sample_id']} crop pixels drifted from render")
        by_page[page_id].append(line_index)

    for page_id, (page, _result, _render_path) in page_state.items():
        expected = list(range(page["authenticated_line_count"]))
        if by_page[page_id] != expected:
            raise _error(f"{page_id} all-LINE sample denominator is incomplete or reordered")
    return input_path, input_payload, pages, samples, verified_crop_refs


def _validate_request(
    root: Path,
    request: dict[str, Any],
    manifest_path: Path,
    manifest_payload: bytes,
    samples: list[dict[str, Any]],
) -> None:
    _exact(request, _REQUEST_FIELDS, "reader request")
    if (
        request["format_version"] != 2
        or request["experiment_id"] != EXPERIMENT_ID
        or request["state"] != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or request["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or request["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or request["git_dirty"] is not False
        or request["reference_text_available_to_reader"] is not False
    ):
        raise _error("reader request identity or firewall drifted")
    manifest_ref = _exact(request["crop_manifest"], _HASH_REF_FIELDS, "request manifest ref")
    if manifest_ref != {
        "path": manifest_path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(manifest_payload).hexdigest(),
    }:
        raise _error("request-to-manifest binding drifted")
    raw = request["samples"]
    if type(raw) is not list or len(raw) != request["sample_count"] or len(raw) != len(samples):
        raise _error("request sample denominator drifted")
    for index, (item, source) in enumerate(zip(raw, samples, strict=True)):
        _exact(item, _REQUEST_SAMPLE_FIELDS, f"request sample {index}")
        expected = {key: source[key] for key in _REQUEST_SAMPLE_FIELDS}
        if not same_typed_json_v1(item, expected):
            raise _error(f"request sample {index} is not exact manifest projection")


def _validate_result(result: dict[str, Any], request: dict[str, Any]) -> list[dict[str, Any]]:
    _exact(result, _RESULT_FIELDS, "VietOCR result")
    if (
        result["format_version"] != 2
        or result["experiment_id"] != EXPERIMENT_ID
        or result["state"] != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or result["dataset_role"] != request["dataset_role"]
        or result["evidence_role"] != request["evidence_role"]
        or result["reference_text_available_to_reader"] is not False
    ):
        raise _error("VietOCR result identity or firewall drifted")
    samples = result["samples"]
    if (
        type(samples) is not list
        or len(samples) != result["sample_count"]
        or len(samples) != request["sample_count"]
    ):
        raise _error("VietOCR result denominator drifted")
    for index, (sample, requested) in enumerate(zip(samples, request["samples"], strict=True)):
        _exact(sample, _RESULT_SAMPLE_FIELDS, f"result sample {index}")
        if any(sample[field] != requested[field] for field in _REQUEST_SAMPLE_FIELDS):
            raise _error(f"result sample {index} request binding drifted")
        if type(sample["raw_prediction"]) is not str:
            raise _error(f"result sample {index} prediction is not text")
        _integer(sample["processed_width"], f"result sample {index} width", positive=True)
        _integer(sample["processed_height"], f"result sample {index} height", positive=True)
        probability = sample["mean_decoded_character_probability"]
        if probability is not None and not 0.0 <= _finite(probability, "probability") <= 1.0:
            raise _error(f"result sample {index} probability exceeds one")
        _finite(sample["wall_seconds"], f"result sample {index} wall time")
    return samples


def _timestamp(value: Any, label: str) -> datetime:
    if type(value) is not str:
        raise _error(f"{label} is not a timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _error(f"{label} is not a timestamp") from exc
    if timestamp.tzinfo is None:
        raise _error(f"{label} has no timezone")
    return timestamp


def _validate_transformer_run(
    root: Path,
    run: dict[str, Any],
    run_path: Path,
    request_path: Path,
    request_payload: bytes,
    result_path: Path,
    result_payload: bytes,
    sample_count: int,
) -> dict[str, Any]:
    _exact(run, _RUN_FIELDS, "run manifest")
    if (
        run["format_version"] != 2
        or run["experiment_id"] != EXPERIMENT_ID
        or run["state"] != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or run["git_dirty"] is not False
        or _timestamp(run["completed_at"], "run completion")
        < _timestamp(run["started_at"], "run start")
    ):
        raise _error("run identity/state drifted")
    if type(run["git_commit"]) is not str or _GIT_RE.fullmatch(run["git_commit"]) is None:
        raise _error("run Git identity drifted")
    if run["git_commit"] != _SELECTED_RUN_GIT_COMMIT:
        raise _error("run Git identity is not the selected Transformer freeze")
    request_ref = _exact(run["request"], _HASH_REF_FIELDS, "run request ref")
    if request_ref != {
        "path": request_path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(request_payload).hexdigest(),
    }:
        raise _error("run-to-request binding drifted")
    artifacts = _exact(run["artifacts"], {"ocr_result"}, "run artifacts")
    result_ref = _object_ref(artifacts["ocr_result"], "run OCR result", ".json")
    resolved_result = (
        run_path.parent / _safe_relative(result_ref["path"], "result path")
    ).resolve()
    if (
        resolved_result != result_path
        or hashlib.sha256(result_payload).hexdigest() != result_ref["sha256"]
        or len(result_payload) != result_ref["size_bytes"]
    ):
        raise _error("run-to-result binding drifted")

    config_ref = _exact(run["configuration"], _CONFIG_REF_FIELDS, "run configuration")
    config_path = _resolve(root, config_ref["path"], "configuration")
    config_payload = _stable_bytes(config_path, "configuration")
    if (
        hashlib.sha256(config_payload).hexdigest()
        != _sha(config_ref["sha256"], "configuration hash")
        or config_ref["sha256"] != _TRANSFORMER_CONFIG_SHA256
        or config_ref["network_policy"] != "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED"
        or any(
            config_ref[field] is not False
            for field in (
                "cnn_pretrained_download",
                "beam_search",
                "reference_text_available_to_decoder",
            )
        )
    ):
        raise _error("configuration hash/firewall drifted")
    try:
        config = tomllib.loads(config_payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _error("configuration is not valid UTF-8 TOML") from exc
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
        or not same_typed_json_v1(config.get("inference"), expected_inference)
        or not same_typed_json_v1(config.get("safety"), expected_config_safety)
    ):
        raise _error("selected Transformer configuration identity/safety drifted")

    runtime = _exact(run["runtime"], _RUNTIME_FIELDS, "run runtime")
    external_root = Path(runtime["external_root"])
    if not external_root.is_absolute():
        raise _error("runtime root is not absolute")
    external_root = external_root.resolve()
    runtime_artifacts = _exact(runtime["artifacts"], _RUNTIME_ARTIFACT_NAMES, "runtime artifacts")
    expected_config_runtime = {
        "site_packages": runtime["site_packages"],
        "python_major_minor": "3.11",
        "packages": _TRANSFORMER_RUNTIME_PACKAGES,
    }
    expected_compatibility = {
        "gpu_family": "NVIDIA_GEFORCE_RTX_4090_ADA",
        "minimum_compute_capability": [8, 9],
        "cuda_runtime": runtime["torch_cuda_build"],
        "bf16_required": False,
        "historical_blackwell_runtime_claimed": False,
    }
    if (
        config.get("artifacts") != runtime_artifacts
        or runtime["packages"] != _TRANSFORMER_RUNTIME_PACKAGES
        or not same_typed_json_v1(config.get("runtime"), expected_config_runtime)
        or not same_typed_json_v1(config.get("runtime_compatibility"), expected_compatibility)
    ):
        raise _error("configuration/runtime registry drifted")
    reusable_artifact_payloads: dict[str, bytes] = {}
    artifact_hashes: dict[str, str] = {}
    for name, raw in runtime_artifacts.items():
        artifact = _exact(raw, _RUNTIME_ARTIFACT_FIELDS, f"runtime artifact {name}")
        path = _runtime_path(external_root, artifact["path"], f"runtime artifact {name}")
        payload = _stable_bytes(path, f"runtime artifact {name}")
        if (
            len(payload) != artifact["size_bytes"]
            or hashlib.sha256(payload).hexdigest()
            != _sha(artifact["sha256"], f"runtime artifact {name} hash")
            or (artifact["sha256"], artifact["size_bytes"])
            != _TRANSFORMER_ARTIFACT_IDENTITIES[name]
        ):
            raise _error(f"runtime artifact {name} hash/size drifted")
        if type(artifact["url"]) is not str or not artifact["url"].startswith("https://"):
            raise _error(f"runtime artifact {name} URL drifted")
        if name in {"wheel", "base_config", "model_config"}:
            reusable_artifact_payloads[name] = payload
        artifact_hashes[name] = artifact["sha256"]
    site_packages = _runtime_path(external_root, runtime["site_packages"], "site-packages")
    if not site_packages.is_dir():
        raise _error("runtime site-packages is absent")
    try:
        with zipfile.ZipFile(BytesIO(reusable_artifact_payloads["wheel"])) as archive:
            for member in (item for item in archive.infolist() if not item.is_dir()):
                installed = site_packages / member.filename
                if (
                    not installed.is_file()
                    or hashlib.sha256(
                        _stable_bytes(installed, f"runtime wheel overlay {member.filename}")
                    ).hexdigest()
                    != hashlib.sha256(archive.read(member)).hexdigest()
                ):
                    raise _error(f"runtime wheel overlay drifted: {member.filename}")
    except zipfile.BadZipFile as exc:
        raise _error("runtime VietOCR wheel is invalid") from exc
    try:
        base = yaml.safe_load(reusable_artifact_payloads["base_config"].decode("utf-8"))
        model = yaml.safe_load(reusable_artifact_payloads["model_config"].decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise _error("runtime model configuration is invalid") from exc
    merged = {**base, **model} if type(base) is dict and type(model) is dict else {}
    if merged.get("seq_modeling") != "transformer" or merged.get("backbone") != "vgg19_bn":
        raise _error("runtime model artifacts are not the selected Transformer architecture")
    if (
        runtime["device"] != "NVIDIA GeForce RTX 4090"
        or runtime["compute_capability"] != "8.9"
        or runtime["torch_cuda_build"] != "13.0"
        or config.get("runtime_compatibility", {}).get("cuda_runtime")
        != runtime["torch_cuda_build"]
    ):
        raise _error("selected Transformer runtime profile drifted")

    metrics = _exact(run["metrics"], _RUN_METRIC_FIELDS, "run metrics")
    if metrics["sample_count"] != sample_count:
        raise _error("run sample denominator drifted")
    for field in _RUN_METRIC_FIELDS - {"sample_count"}:
        _finite(metrics[field], f"run metric {field}")
    safety = _exact(run["safety"], _RUN_SAFETY_FIELDS, "run safety")
    if any(value is not False for value in safety.values()):
        raise _error("run grants forbidden authority")
    runner_refs: dict[str, dict[str, Any]] = {}
    for name, expected in _RUNNER_IMPLEMENTATION_REFS.items():
        path, payload = _verify_project_ref(root, expected, f"runner implementation {name}")
        runner_refs[name] = _file_ref(root, path, payload)
    return {
        "profile_id": TRANSFORMER_PROFILE_ID,
        "model_name": config["model_name"],
        "architecture": config["architecture"],
        "package_version": config["package_version"],
        "configuration_ref": _file_ref(root, config_path, config_payload),
        "runtime_identity_sha256": canonical_json_sha256_v1(runtime),
        "runtime_artifact_sha256": artifact_hashes,
        "runner_implementation_refs": runner_refs,
        "selected_run_git_commit": _SELECTED_RUN_GIT_COMMIT,
    }


def _validate_receipt_payload(value: Any) -> dict[str, Any]:
    receipt = _exact(value, _RECEIPT_FIELDS, "v2 receipt")
    if (
        receipt["format_version"] != FORMAT_VERSION
        or receipt["claim_boundary"] != CLAIM_BOUNDARY
        or receipt["experiment_id"] != EXPERIMENT_ID
        or receipt["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or receipt["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
    ):
        raise _error("v2 receipt identity/role drifted")
    profile = _exact(receipt["reader_profile"], _PROFILE_FIELDS, "reader profile")
    if (
        profile["profile_id"] != TRANSFORMER_PROFILE_ID
        or profile["model_name"] != "VietOCR VGG Transformer"
        or profile["architecture"] != "vgg19_bn_transformer"
        or profile["package_version"] != "0.3.13"
        or profile["selected_run_git_commit"] != _SELECTED_RUN_GIT_COMMIT
    ):
        raise _error("receipt Transformer profile drifted")
    _object_ref(profile["configuration_ref"], "receipt configuration", ".toml")
    _sha(profile["runtime_identity_sha256"], "runtime identity")
    if (
        type(profile["runtime_artifact_sha256"]) is not dict
        or set(profile["runtime_artifact_sha256"]) != _RUNTIME_ARTIFACT_NAMES
    ):
        raise _error("receipt runtime artifact identities drifted")
    for name, digest in profile["runtime_artifact_sha256"].items():
        _sha(digest, f"receipt runtime artifact {name}")
    runner_refs = profile["runner_implementation_refs"]
    if type(runner_refs) is not dict or set(runner_refs) != set(_RUNNER_IMPLEMENTATION_REFS):
        raise _error("receipt runner implementation registry drifted")
    for name, reference in runner_refs.items():
        _object_ref(reference, f"receipt runner implementation {name}", ".py")
        if not same_typed_json_v1(reference, _RUNNER_IMPLEMENTATION_REFS[name]):
            raise _error(f"receipt runner implementation {name} identity drifted")
    inputs = _exact(receipt["inputs"], _RECEIPT_INPUT_FIELDS, "receipt inputs")
    for name, reference in inputs.items():
        _object_ref(reference, f"receipt input {name}", ".json")
    pages = receipt["pages"]
    samples = receipt["samples"]
    if type(pages) is not list or type(samples) is not list:
        raise _error("receipt axes are not lists")
    indices_by_page: dict[str, list[int]] = {}
    for index, raw in enumerate(pages, start=1):
        page = _exact(raw, _RECEIPT_PAGE_FIELDS, f"receipt page {index}")
        if page["page_id"] != f"page-{index:04d}" or page["page_id"] in indices_by_page:
            raise _error("receipt page IDs drifted")
        _object_ref(page["result_ref"], f"receipt page {index} result", ".json")
        _object_ref(page["render_ref"], f"receipt page {index} render", ".png")
        count = _integer(
            page["authenticated_line_count"], "authenticated line count", positive=True
        )
        if page["line_sample_count"] != count:
            raise _error("receipt page all-LINE denominator drifted")
        indices_by_page[page["page_id"]] = []
    seen: set[str] = set()
    for index, raw in enumerate(samples):
        sample = _exact(raw, _RECEIPT_SAMPLE_FIELDS, f"receipt sample {index}")
        match = (
            _SAMPLE_ID_RE.fullmatch(sample["sample_id"])
            if type(sample["sample_id"]) is str
            else None
        )
        if (
            match is None
            or match.group(1) != sample["page_id"]
            or int(match.group(2)) != sample["source_line_index"]
            or sample["sample_id"] in seen
            or sample["page_id"] not in indices_by_page
        ):
            raise _error("receipt sample opaque identity drifted")
        seen.add(sample["sample_id"])
        _bbox(sample["source_bbox_raw_pixels"], "receipt source bbox")
        _bbox(sample["padded_source_bbox_raw_pixels"], "receipt padded bbox")
        _object_ref(sample["crop_ref"], "receipt crop", ".png")
        if type(sample["raw_prediction"]) is not str or sample[
            "normalized_prediction"
        ] != normalize_text(sample["raw_prediction"]):
            raise _error("receipt prediction normalization drifted")
        probability = sample["mean_decoded_character_probability"]
        if (
            probability is not None
            and not 0.0 <= _finite(probability, "receipt probability") <= 1.0
        ):
            raise _error("receipt probability exceeds one")
        dimensions = sample["processed_dimensions"]
        if type(dimensions) is not list or len(dimensions) != 2:
            raise _error("receipt processed dimensions drifted")
        _integer(dimensions[0], "processed width", positive=True)
        _integer(dimensions[1], "processed height", positive=True)
        indices_by_page[sample["page_id"]].append(sample["source_line_index"])
    if any(
        indices_by_page[page["page_id"]] != list(range(page["authenticated_line_count"]))
        for page in pages
    ):
        raise _error("receipt per-page all-LINE denominator drifted")
    metrics = _exact(receipt["metrics"], _RECEIPT_METRIC_FIELDS, "receipt metrics")
    if metrics != {
        "page_count": len(pages),
        "sample_count": len(samples),
        "all_line_denominator_complete": True,
    }:
        raise _error("receipt aggregate denominator drifted")
    if not same_typed_json_v1(receipt["safety"], _RECEIPT_SAFETY):
        raise _error("receipt safety boundary drifted")
    return canonical_clone_v1(receipt)


def validate_vietocr_semantic_receipt_v2(
    project_root: Path,
    crop_manifest_path: Path,
    reader_request_path: Path,
    ocr_result_path: Path,
    run_manifest_path: Path,
    *,
    expected_ocr_result_sha256: str,
    expected_run_manifest_sha256: str,
) -> AuthenticatedVietOCRSemanticReceiptV2:
    """Replay and authenticate one complete generic all-LINE Transformer run."""

    root = project_root.resolve()
    manifest_path = _resolve(root, crop_manifest_path, "crop manifest")
    request_path = _resolve(root, reader_request_path, "reader request")
    result_path = _resolve(root, ocr_result_path, "OCR result")
    run_path = _resolve(root, run_manifest_path, "run manifest")
    manifest, manifest_payload = _load_json(manifest_path, "crop manifest")
    request, request_payload = _load_json(request_path, "reader request")
    result, result_payload = _load_json(result_path, "OCR result")
    run, run_payload = _load_json(run_path, "run manifest")
    if hashlib.sha256(result_payload).hexdigest() != _sha(
        expected_ocr_result_sha256, "expected OCR-result hash"
    ):
        raise _error("OCR result differs from the externally selected artifact identity")
    if hashlib.sha256(run_payload).hexdigest() != _sha(
        expected_run_manifest_sha256, "expected run-manifest hash"
    ):
        raise _error("run manifest differs from the externally selected artifact identity")
    input_path, input_payload, pages, crop_samples, verified_crop_refs = _validate_manifest(
        root, manifest
    )
    # The remaining validators operate on the exact in-memory snapshot loaded above.
    # Verify every project artifact once more immediately before minting authority;
    # a coordinated path swap at any point in replay therefore fails closed.
    snapshot_paths = {
        "crop manifest": (manifest_path, manifest_payload),
        "reader request": (request_path, request_payload),
        "OCR result": (result_path, result_payload),
        "run manifest": (run_path, run_payload),
        "input spec": (input_path, input_payload),
    }
    for label, (path, snapshot) in snapshot_paths.items():
        if _stable_bytes(path, f"final {label} snapshot") != snapshot:
            raise _error(f"{label} changed during receipt replay")
    _validate_request(root, request, manifest_path, manifest_payload, crop_samples)
    result_samples = _validate_result(result, request)
    profile = _validate_transformer_run(
        root,
        run,
        run_path,
        request_path,
        request_payload,
        result_path,
        result_payload,
        len(result_samples),
    )
    if not (manifest["git_commit"] == request["git_commit"] == run["git_commit"]):
        raise _error("freeze/request/run Git identities drifted")

    page_records = [
        {
            "page_id": page["page_id"],
            "result_ref": canonical_clone_v1(page["result_ref"]),
            "render_ref": canonical_clone_v1(page["render_ref"]),
            "authenticated_line_count": page["authenticated_line_count"],
            "line_sample_count": page["selected_line_count"],
        }
        for page in pages
    ]
    samples = []
    for crop, prediction in zip(crop_samples, result_samples, strict=True):
        samples.append(
            {
                "sample_id": crop["sample_id"],
                "page_id": crop["page_id"],
                "source_line_index": crop["source_line_index"],
                "source_bbox_raw_pixels": list(crop["source_bbox_raw_pixels"]),
                "padded_source_bbox_raw_pixels": list(crop["padded_source_bbox_raw_pixels"]),
                "crop_ref": canonical_clone_v1(verified_crop_refs[crop["sample_id"]]),
                "raw_prediction": prediction["raw_prediction"],
                "normalized_prediction": normalize_text(prediction["raw_prediction"]),
                "mean_decoded_character_probability": prediction[
                    "mean_decoded_character_probability"
                ],
                "processed_dimensions": [
                    prediction["processed_width"],
                    prediction["processed_height"],
                ],
            }
        )
    receipt = {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "experiment_id": EXPERIMENT_ID,
        "dataset_role": request["dataset_role"],
        "evidence_role": request["evidence_role"],
        "reader_profile": profile,
        "inputs": {
            "input_spec": _file_ref(root, input_path, input_payload),
            "crop_manifest": _file_ref(root, manifest_path, manifest_payload),
            "reader_request": _file_ref(root, request_path, request_payload),
            "ocr_result": _file_ref(root, result_path, result_payload),
            "run_manifest": _file_ref(root, run_path, run_payload),
        },
        "pages": page_records,
        "samples": samples,
        "metrics": {
            "page_count": len(page_records),
            "sample_count": len(samples),
            "all_line_denominator_complete": True,
        },
        "safety": canonical_clone_v1(_RECEIPT_SAFETY),
    }
    payload = _validate_receipt_payload(receipt)
    authenticated = AuthenticatedVietOCRSemanticReceiptV2(payload, _AUTHENTICATION_TOKEN)
    receipt_id = id(authenticated)

    def discard(reference: weakref.ReferenceType[AuthenticatedVietOCRSemanticReceiptV2]) -> None:
        current = _AUTHENTICATED_RECEIPTS.get(receipt_id)
        if current is not None and current[0] is reference:
            _AUTHENTICATED_RECEIPTS.pop(receipt_id, None)

    reference = weakref.ref(authenticated, discard)
    _AUTHENTICATED_RECEIPTS[receipt_id] = (reference, canonical_json_sha256_v1(payload))
    return authenticated


def _authenticated_payload(receipt: Any) -> dict[str, Any]:
    if type(receipt) is not AuthenticatedVietOCRSemanticReceiptV2:
        raise _error("page binding requires a replay-authenticated VietOCR v2 receipt")
    payload = receipt._clone_for_internal_replay(_AUTHENTICATION_TOKEN)
    authority = _AUTHENTICATED_RECEIPTS.get(id(receipt))
    if (
        authority is None
        or authority[0]() is not receipt
        or canonical_json_sha256_v1(payload) != authority[1]
    ):
        raise _error("VietOCR v2 receipt lost replay-authenticated authority")
    return _validate_receipt_payload(payload)


def replay_vietocr_semantic_receipt_v2(
    project_root: Path,
    crop_manifest_path: Path,
    reader_request_path: Path,
    ocr_result_path: Path,
    run_manifest_path: Path,
    receipt: Any,
    *,
    expected_ocr_result_sha256: str,
    expected_run_manifest_sha256: str,
) -> AuthenticatedVietOCRSemanticReceiptV2:
    expected = _authenticated_payload(receipt)
    rebuilt = validate_vietocr_semantic_receipt_v2(
        project_root,
        crop_manifest_path,
        reader_request_path,
        ocr_result_path,
        run_manifest_path,
        expected_ocr_result_sha256=expected_ocr_result_sha256,
        expected_run_manifest_sha256=expected_run_manifest_sha256,
    )
    if not same_typed_json_v1(_authenticated_payload(rebuilt), expected):
        raise _error("VietOCR v2 receipt does not replay exactly")
    return rebuilt


def _build_page_binding(source: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    if source["route"] != "DOMINANT_RASTER_OCR" or source["terminal"] is not False:
        raise _error("page binding requires a nonterminal OCR V2 source projection")
    render_ref = source["page_result"].get("input_render_ref")
    if type(render_ref) is not dict:
        raise _error("source projection lacks authenticated render")
    matches = [
        page
        for page in receipt["pages"]
        if page["result_ref"]["sha256"] == source["page_result_sha256"]
        and page["render_ref"]["sha256"] == render_ref.get("sha256")
    ]
    if len(matches) != 1:
        raise _error("receipt has no unique projection result/render match")
    page = matches[0]
    atoms: dict[int, dict[str, Any]] = {}
    for atom in source["neutral_page_v1"]["atoms"]:
        locator = atom["upstream_locator"]
        if (
            atom["kind"] == "LINE"
            and atom["authority"] == "AUTHENTICATED_PRIMARY"
            and type(locator) is dict
            and locator.get("kind") == "OCR_LINE_INDEX"
            and type(locator.get("line_index")) is int
        ):
            if locator["line_index"] in atoms:
                raise _error("projection has duplicate primary LINE indices")
            atoms[locator["line_index"]] = atom
    bound = []
    unique: set[str] = set()
    for sample in (item for item in receipt["samples"] if item["page_id"] == page["page_id"]):
        atom = atoms.get(sample["source_line_index"])
        if atom is None or atom["pixel_bbox"] is None:
            raise _error(f"{sample['sample_id']} lacks exact V3 LINE atom")
        if not same_typed_json_v1(atom["pixel_bbox"], sample["source_bbox_raw_pixels"]):
            raise _error(f"{sample['sample_id']} bbox differs from projection LINE")
        unique.add(atom["source_local_id"])
        bound.append(
            {
                **canonical_clone_v1(sample),
                "source_atom": {
                    "source_atom_id": atom["source_local_id"],
                    "line_index": sample["source_line_index"],
                    "pixel_bbox": canonical_clone_v1(atom["pixel_bbox"]),
                    "canonical_bbox_mpt": canonical_clone_v1(atom["canonical_bbox_mpt"]),
                },
            }
        )
    complete = (
        len(bound) == page["authenticated_line_count"]
        and sorted(item["source_line_index"] for item in bound)
        == list(range(page["authenticated_line_count"]))
        and len(unique) == page["authenticated_line_count"]
    )
    if not complete:
        raise _error("page binding does not cover every authenticated LINE exactly once")
    return {
        "format_version": PAGE_FORMAT_VERSION,
        "claim_boundary": PAGE_CLAIM_BOUNDARY,
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "global_receipt_sha256": canonical_json_sha256_v1(receipt),
        "page_id": page["page_id"],
        "page_source_binding": {
            "route": source["route"],
            "page_result_sha256": source["page_result_sha256"],
            "render_sha256": render_ref["sha256"],
        },
        "samples": bound,
        "metrics": {
            "sample_count": len(bound),
            "authenticated_line_count": page["authenticated_line_count"],
            "unique_source_line_count": len(unique),
            "all_line_denominator_complete": True,
        },
        "safety": canonical_clone_v1(_PAGE_SAFETY),
    }


def bind_vietocr_semantic_page_v2(source_projection_v2: Any, receipt: Any) -> dict[str, Any]:
    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except SourceStructureContractV2Error as exc:
        raise _error("source projection V2 is invalid") from exc
    payload = _authenticated_payload(receipt)
    return _build_page_binding(source, payload)


def validate_vietocr_semantic_page_binding_v2(
    value: Any, source_projection_v2: Any, receipt: Any
) -> dict[str, Any]:
    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except SourceStructureContractV2Error as exc:
        raise _error("source projection V2 is invalid") from exc
    payload = _authenticated_payload(receipt)
    binding = _exact(value, _PAGE_BINDING_FIELDS, "v2 page binding")
    if (
        binding["format_version"] != PAGE_FORMAT_VERSION
        or binding["claim_boundary"] != PAGE_CLAIM_BOUNDARY
    ):
        raise _error("page binding identity drifted")
    _exact(binding["page_source_binding"], _PAGE_SOURCE_FIELDS, "page source binding")
    if type(binding["samples"]) is not list:
        raise _error("page binding samples are not a list")
    for index, sample in enumerate(binding["samples"]):
        _exact(sample, _BOUND_SAMPLE_FIELDS, f"bound sample {index}")
        _exact(sample["source_atom"], _BOUND_ATOM_FIELDS, f"bound atom {index}")
    _exact(binding["metrics"], _PAGE_METRIC_FIELDS, "page binding metrics")
    if not same_typed_json_v1(binding["safety"], _PAGE_SAFETY):
        raise _error("page binding safety drifted")
    rebuilt = _build_page_binding(source, payload)
    if not same_typed_json_v1(binding, rebuilt):
        raise _error("page binding does not replay exactly")
    return canonical_clone_v1(binding)


__all__ = [
    "AuthenticatedVietOCRSemanticReceiptV2",
    "CLAIM_BOUNDARY",
    "EXPERIMENT_ID",
    "FORMAT_VERSION",
    "PAGE_CLAIM_BOUNDARY",
    "PAGE_FORMAT_VERSION",
    "TRANSFORMER_PROFILE_ID",
    "VietOCRSemanticReceiptV2Error",
    "bind_vietocr_semantic_page_v2",
    "replay_vietocr_semantic_receipt_v2",
    "validate_vietocr_semantic_page_binding_v2",
    "validate_vietocr_semantic_receipt_v2",
]
