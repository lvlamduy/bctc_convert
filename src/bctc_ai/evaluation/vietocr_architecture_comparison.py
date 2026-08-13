"""Post-freeze VietOCR Transformer/Seq2Seq comparison on one opaque crop batch.

The evaluator deliberately loads human transcript truth only after both model
runs, their manifests, the common request, and every crop have been authenticated.
It compares semantic text proposals only.  PP-OCR/V3 remains the authority for
geometry, numeric values, periods, signs, and source locators.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import tomllib
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json, atomic_write_text
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import parse_unit
from bctc_ai.evaluation.line_recognition_metrics import (
    normalize_evaluation_line,
    score_line,
    score_reader,
)
from bctc_ai.ocr.vietocr_line_reader import validate_reference_blind_request


class VietOCRArchitectureComparisonError(RuntimeError):
    """The frozen comparison chain or post-freeze truth join is invalid."""


FORMAT_VERSION = "VIETOCR_TRANSFORMER_SEQ2SEQ_COMPARISON_V1"
TRUTH_FORMAT_VERSION = "VIETOCR_TRANSFORMER_SEQ2SEQ_POSTFREEZE_TRUTH_V1"
CLAIM_BOUNDARY = (
    "FROZEN_MULTI_BANK_VIETNAMESE_SEMANTIC_LINE_PROPOSAL_COMPARISON_ONLY_"
    "NO_NUMERIC_PERIOD_UNIT_SIGN_GEOMETRY_STRUCTURE_SCHEMA_OR_MAPPING_AUTHORITY"
)
_CROP_FORMAT = "V3_AUTHENTICATED_LINE_GEOMETRY_ONLY_CROP_MANIFEST_V2"
_REQUEST_IDENTITY = (2, "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1")
_COMPLETE_STATE = "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
_TRUTH_STATE = "FROZEN_AFTER_BOTH_ARCHITECTURE_OUTPUTS"
_ARCHITECTURES = {
    "transformer": "vgg19_bn_transformer",
    "seq2seq": "vgg19_bn_seq2seq",
}
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ROLE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PRESENTATION_PREFIX_RE = re.compile(
    r"^(?:(?:[0-9]+|[ivxlcdm]+)\s+)+(?:nhóm\s+[0-9]+\s+)?",
    re.IGNORECASE,
)
_GROUP_PREFIX_RE = re.compile(r"^nhóm\s+[0-9]+\s+")

SEMANTIC_TEXT_POLICY = {
    "transcript_storage": "UTF8_NFC_ACCENT_PRESERVING",
    "acceptance_comparison_key": "NFC_CASEFOLD_ACCENT_PRESERVING",
    "accentless_comparison_key_use": "CANDIDATE_SHORTLIST_ONLY",
    "accentless_comparison_key_alone_can_accept": False,
    "unique_collision_free_accentless_candidate_may_be_promoted_downstream": True,
    "downstream_promotion_requires": [
        "OWNER_BRANCH_ORDERED_SIBLINGS",
        "AXIS_UNIT_VALUE_TOTAL_CLOSURE",
        "UNIQUE_COLLISION_FREE_ROLE",
    ],
    "accentless_collision_or_ambiguity": "UNRESOLVED",
    "fuzzy_or_nearest_role_can_accept": False,
    "this_evaluator_performs_downstream_promotion": False,
}


def _error(message: str) -> VietOCRArchitectureComparisonError:
    return VietOCRArchitectureComparisonError(message)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} SHA-256 is invalid")
    return value


def _resolve(project_root: Path, value: Path | str, label: str) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    if not resolved.is_relative_to(project_root):
        raise _error(f"{label} escapes project root")
    return resolved


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _error(f"cannot read {label}: {path}") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be a JSON object")
    return value


def _verified_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or sha256_file(path) != _sha(expected_sha256, label):
        raise _error(f"{label} is missing or hash-drifted")


def _verified_object_ref(project_root: Path, value: Any, label: str) -> Path:
    if type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}:
        raise _error(f"{label} is not an exact object reference")
    path = _resolve(project_root, value["path"], label)
    if (
        type(value["size_bytes"]) is not int
        or value["size_bytes"] < 0
        or not path.is_file()
        or path.stat().st_size != value["size_bytes"]
        or sha256_file(path) != _sha(value["sha256"], label)
    ):
        raise _error(f"{label} is missing, size-drifted, or hash-drifted")
    return path


def _verify_crop_request(
    project_root: Path,
    crop_manifest_path: Path,
    reader_request_path: Path,
) -> dict[str, Any]:
    manifest_path = _resolve(project_root, crop_manifest_path, "crop manifest")
    request_path = _resolve(project_root, reader_request_path, "reader request")
    manifest = _load_json(manifest_path, "crop manifest")
    request = _load_json(request_path, "reader request")
    if (
        manifest.get("format_version") != _CROP_FORMAT
        or manifest.get("state") != "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE"
        or manifest.get("dataset_role") != "DEVELOPMENT_REPLAY"
        or manifest.get("git_dirty") is not False
    ):
        raise _error("crop manifest identity, state, or role drifted")
    pages = manifest.get("pages")
    samples = manifest.get("samples")
    if (
        type(pages) is not list
        or not pages
        or type(samples) is not list
        or len(pages) != manifest.get("page_count")
        or len(samples) != manifest.get("sample_count")
    ):
        raise _error("crop manifest denominator drifted")

    page_by_id: dict[str, dict[str, Any]] = {}
    for page in pages:
        if type(page) is not dict:
            raise _error("crop manifest page is not an object")
        page_id = page.get("page_id")
        line_count = page.get("authenticated_line_count")
        if (
            type(page_id) is not str
            or page_id in page_by_id
            or type(line_count) is not int
            or line_count < 0
            or page.get("selected_line_count") != line_count
        ):
            raise _error("crop manifest page identity or all-LINE denominator drifted")
        _verified_object_ref(project_root, page.get("result_ref"), f"{page_id} result")
        _verified_object_ref(project_root, page.get("render_ref"), f"{page_id} render")
        page_by_id[page_id] = page

    manifest_sample_by_id: dict[str, dict[str, Any]] = {}
    line_indices: dict[str, list[int]] = defaultdict(list)
    for sample in samples:
        if type(sample) is not dict:
            raise _error("crop sample is not an object")
        sample_id = sample.get("sample_id")
        page_id = sample.get("page_id")
        line_index = sample.get("source_line_index")
        crop_path = _resolve(project_root, str(sample.get("crop_path", "")), "crop")
        if (
            type(sample_id) is not str
            or sample_id in manifest_sample_by_id
            or page_id not in page_by_id
            or type(line_index) is not int
            or line_index < 0
            or sample.get("grouping") != "LINE"
            or sample.get("category") != "SOURCE_BOUND_AUTHENTICATED_LINE"
            or not crop_path.is_file()
            or sha256_file(crop_path) != _sha(sample.get("crop_sha256"), f"{sample_id} crop")
        ):
            raise _error(f"crop sample identity or source binding drifted: {sample_id}")
        manifest_sample_by_id[sample_id] = sample
        line_indices[page_id].append(line_index)
    for page_id, page in page_by_id.items():
        if sorted(line_indices[page_id]) != list(range(page["authenticated_line_count"])):
            raise _error(f"{page_id} does not contain every authenticated LINE exactly once")

    request_samples = validate_reference_blind_request(request)
    if (request.get("format_version"), request.get("experiment_id")) != _REQUEST_IDENTITY:
        raise _error("reader request is not the frozen architecture benchmark")
    if request.get("crop_manifest") != {
        "path": manifest_path.relative_to(project_root).as_posix(),
        "sha256": sha256_file(manifest_path),
    }:
        raise _error("reader request is not bound to the exact crop manifest")
    if len(request_samples) != len(samples):
        raise _error("reader request/crop denominator drifted")
    for request_sample, manifest_sample in zip(request_samples, samples, strict=True):
        if request_sample != {
            "sample_id": manifest_sample["sample_id"],
            "category": manifest_sample["category"],
            "crop_path": manifest_sample["crop_path"],
            "crop_sha256": manifest_sample["crop_sha256"],
        }:
            raise _error("reader request and crop sample axes differ")
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "request": request,
        "request_path": request_path,
        "request_sha256": sha256_file(request_path),
        "request_samples": request_samples,
        "page_by_id": page_by_id,
        "manifest_sample_by_id": manifest_sample_by_id,
    }


def _verify_architecture_run(
    project_root: Path,
    *,
    crop_request: Mapping[str, Any],
    architecture_label: str,
    output_directory: Path,
    expected_result_sha256: str,
    expected_run_manifest_sha256: str,
) -> dict[str, Any]:
    expected_architecture = _ARCHITECTURES[architecture_label]
    output_root = _resolve(project_root, output_directory, f"{architecture_label} output")
    result_path = output_root / "ocr_result.json"
    run_path = output_root / "run_manifest.json"
    _verified_file(result_path, expected_result_sha256, f"{architecture_label} result")
    _verified_file(run_path, expected_run_manifest_sha256, f"{architecture_label} run manifest")
    result = _load_json(result_path, f"{architecture_label} result")
    run = _load_json(run_path, f"{architecture_label} run manifest")
    request = crop_request["request"]
    request_path = crop_request["request_path"]
    if any(
        payload.get("format_version") != request["format_version"]
        or payload.get("experiment_id") != request["experiment_id"]
        or payload.get("state") != _COMPLETE_STATE
        for payload in (result, run)
    ):
        raise _error(f"{architecture_label} completion identity drifted")
    if (
        run.get("git_dirty") is not False
        or result.get("reference_text_available_to_reader") is not False
    ):
        raise _error(f"{architecture_label} run crossed the reference-blind boundary")
    if run.get("request") != {
        "path": request_path.relative_to(project_root).as_posix(),
        "sha256": crop_request["request_sha256"],
    }:
        raise _error(f"{architecture_label} run used a different request")
    result_artifact = run.get("artifacts", {}).get("ocr_result")
    if result_artifact != {
        "path": "ocr_result.json",
        "size_bytes": result_path.stat().st_size,
        "sha256": expected_result_sha256,
    }:
        raise _error(f"{architecture_label} result/run binding drifted")

    configuration = run.get("configuration")
    if type(configuration) is not dict:
        raise _error(f"{architecture_label} run has no model configuration binding")
    config_path = _resolve(
        project_root,
        str(configuration.get("path", "")),
        f"{architecture_label} model config",
    )
    _verified_file(
        config_path,
        configuration.get("sha256"),
        f"{architecture_label} model config",
    )
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise _error(f"cannot read {architecture_label} model config") from exc
    if (
        config.get("architecture") != expected_architecture
        or config.get("package_version") != "0.3.13"
        or config.get("inference", {}).get("network_permitted") is not False
        or config.get("inference", {}).get("reference_text_available_to_decoder") is not False
    ):
        raise _error(f"{architecture_label} model identity or safety policy drifted")

    predictions = result.get("samples")
    request_samples = crop_request["request_samples"]
    if (
        type(predictions) is not list
        or len(predictions) != result.get("sample_count")
        or len(predictions) != len(request_samples)
    ):
        raise _error(f"{architecture_label} result denominator drifted")
    prediction_by_id: dict[str, dict[str, Any]] = {}
    for request_sample, prediction in zip(request_samples, predictions, strict=True):
        if type(prediction) is not dict:
            raise _error(f"{architecture_label} prediction is not an object")
        sample_id = prediction.get("sample_id")
        wall_seconds = prediction.get("wall_seconds")
        if (
            sample_id != request_sample["sample_id"]
            or sample_id in prediction_by_id
            or prediction.get("category") != request_sample["category"]
            or prediction.get("crop_path") != request_sample["crop_path"]
            or prediction.get("crop_sha256") != request_sample["crop_sha256"]
            or type(prediction.get("raw_prediction")) is not str
            or type(wall_seconds) not in {int, float}
            or not math.isfinite(float(wall_seconds))
            or float(wall_seconds) < 0
        ):
            raise _error(f"{architecture_label} prediction binding drifted: {sample_id}")
        prediction_by_id[sample_id] = prediction
    metrics = run.get("metrics")
    if (
        type(metrics) is not dict
        or metrics.get("sample_count") != len(predictions)
        or any(
            type(metrics.get(field)) not in {int, float}
            or not math.isfinite(float(metrics[field]))
            or float(metrics[field]) < 0
            for field in ("model_load_seconds", "total_wall_seconds")
        )
    ):
        raise _error(f"{architecture_label} timing metrics drifted")
    return {
        "architecture": expected_architecture,
        "config_path": config_path,
        "config_relative_path": config_path.relative_to(project_root).as_posix(),
        "config_sha256": configuration["sha256"],
        "output_root": output_root,
        "result_path": result_path,
        "result_sha256": expected_result_sha256,
        "run_path": run_path,
        "run_sha256": expected_run_manifest_sha256,
        "result": result,
        "run": run,
        "prediction_by_id": prediction_by_id,
    }


def _semantic_normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFC", normalize_evaluation_line(value)).casefold()
    normalized = " ".join(re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).split())
    normalized = _PRESENTATION_PREFIX_RE.sub("", normalized)
    return _GROUP_PREFIX_RE.sub("", normalized)


def accentless_semantic_shortlist_key(value: str) -> str:
    """Return a lossy key that is never sufficient for semantic acceptance."""

    decomposed = unicodedata.normalize("NFD", _semantic_normalize(value))
    stripped = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return stripped.replace("đ", "d")


def resolve_vietnamese_semantic_role(
    text: str,
    role_aliases: Mapping[str, Sequence[str]],
    *,
    allow_suffix: bool = False,
) -> dict[str, Any]:
    """Resolve only unique accent-preserving aliases; expose accentless candidates.

    The accentless key is intentionally a recall aid.  Within this text resolver,
    even one accentless candidate remains unresolved because the key alone has no
    authority.  A later structural stage may promote a unique, collision-free
    candidate only with independent owner/sibling/axis/value/total/closure evidence.
    Accentless collisions remain unresolved and fuzzy nearest-role acceptance is
    prohibited.
    """

    normalized = _semantic_normalize(text)
    shortlist_key = accentless_semantic_shortlist_key(text)
    exact_roles = []
    accentless_roles = []
    for role, aliases in role_aliases.items():
        normalized_aliases = tuple(_semantic_normalize(alias) for alias in aliases)
        accentless_aliases = tuple(accentless_semantic_shortlist_key(alias) for alias in aliases)
        if any(
            normalized == alias or (allow_suffix and normalized.startswith(f"{alias} "))
            for alias in normalized_aliases
        ):
            exact_roles.append(role)
        if any(
            shortlist_key == alias or (allow_suffix and shortlist_key.startswith(f"{alias} "))
            for alias in accentless_aliases
        ):
            accentless_roles.append(role)
    if len(exact_roles) == 1:
        status = "UNIQUE_ACCENT_PRESERVING_ROLE"
        accepted_role = exact_roles[0]
    elif len(exact_roles) > 1:
        status = "FULL_TEXT_COLLISION_UNRESOLVED"
        accepted_role = None
    elif len(accentless_roles) == 1:
        status = "ACCENTLESS_SHORTLIST_ONLY_UNRESOLVED"
        accepted_role = None
    elif len(accentless_roles) > 1:
        status = "ACCENTLESS_COLLISION_UNRESOLVED"
        accepted_role = None
    else:
        status = "NO_CANDIDATE"
        accepted_role = None
    return {
        "status": status,
        "accepted_role": accepted_role,
        "accentless_shortlisted_roles": sorted(set(accentless_roles)),
    }


def _validated_aliases(value: Any, label: str) -> tuple[str, ...]:
    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise _error(f"{label} aliases must be a non-empty string list")
    normalized = tuple(_semantic_normalize(item) for item in value)
    if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
        raise _error(f"{label} aliases are empty or duplicate after normalization")
    return normalized


def _validate_truth(
    project_root: Path,
    *,
    truth_path: Path,
    expected_truth_sha256: str,
    crop_request: Mapping[str, Any],
    runs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    # This is intentionally the first truth-file access in the public workflow.
    path = _resolve(project_root, truth_path, "post-freeze truth")
    _verified_file(path, expected_truth_sha256, "post-freeze truth")
    truth = _load_json(path, "post-freeze truth")
    required_fields = {
        "format_version",
        "state",
        "dataset_role",
        "claim_boundary",
        "input_bindings",
        "pages",
        "family_matchers",
        "samples",
        "cases",
    }
    if set(truth) != required_fields:
        raise _error("post-freeze truth contains missing or non-allowlisted fields")
    if (
        truth["format_version"] != TRUTH_FORMAT_VERSION
        or truth["state"] != _TRUTH_STATE
        or truth["dataset_role"] != "DEVELOPMENT_REPLAY"
        or type(truth["claim_boundary"]) is not str
        or not truth["claim_boundary"]
    ):
        raise _error("post-freeze truth identity, state, or role drifted")
    expected_bindings = {
        "crop_manifest_sha256": crop_request["manifest_sha256"],
        "reader_request_sha256": crop_request["request_sha256"],
        "transformer_result_sha256": runs["transformer"]["result_sha256"],
        "transformer_run_manifest_sha256": runs["transformer"]["run_sha256"],
        "seq2seq_result_sha256": runs["seq2seq"]["result_sha256"],
        "seq2seq_run_manifest_sha256": runs["seq2seq"]["run_sha256"],
    }
    if truth["input_bindings"] != expected_bindings:
        raise _error("post-freeze truth was not frozen against both exact model outputs")

    manifest_pages = crop_request["page_by_id"]
    truth_pages = truth["pages"]
    if type(truth_pages) is not list or len(truth_pages) != len(manifest_pages):
        raise _error("post-freeze truth page denominator drifted")
    truth_page_by_result: dict[str, dict[str, Any]] = {}
    page_id_by_result: dict[str, str] = {}
    for page_id, page in manifest_pages.items():
        result_sha = page["result_ref"]["sha256"]
        page_id_by_result[result_sha] = page_id
    for page in truth_pages:
        if type(page) is not dict or set(page) != {"bank", "source_result_sha256"}:
            raise _error("post-freeze truth page record drifted")
        result_sha = _sha(page["source_result_sha256"], "truth page result")
        if (
            result_sha not in page_id_by_result
            or result_sha in truth_page_by_result
            or type(page["bank"]) is not str
            or not page["bank"]
        ):
            raise _error("post-freeze truth page binding is missing or duplicate")
        truth_page_by_result[result_sha] = page
    if set(truth_page_by_result) != set(page_id_by_result):
        raise _error("post-freeze truth does not bind the exact page set")

    matchers: dict[str, dict[str, Any]] = {}
    if type(truth["family_matchers"]) is not list or not truth["family_matchers"]:
        raise _error("post-freeze truth has no family matchers")
    for matcher in truth["family_matchers"]:
        fields = {"family_id", "owner_aliases", "branch_aliases", "ordered_children", "unit"}
        if type(matcher) is not dict or set(matcher) != fields:
            raise _error("family matcher fields drifted")
        family_id = matcher["family_id"]
        if type(family_id) is not str or _ROLE_RE.fullmatch(family_id) is None:
            raise _error("family matcher identity drifted")
        children = matcher["ordered_children"]
        if type(children) is not list or not children:
            raise _error(f"{family_id} has no ordered children")
        child_roles = []
        for child in children:
            if type(child) is not dict or set(child) != {"role", "aliases"}:
                raise _error(f"{family_id} child matcher fields drifted")
            if type(child["role"]) is not str or _ROLE_RE.fullmatch(child["role"]) is None:
                raise _error(f"{family_id} child role drifted")
            _validated_aliases(child["aliases"], f"{family_id} {child['role']}")
            child_roles.append(child["role"])
        unit = matcher["unit"]
        if (
            type(unit) is not dict
            or set(unit) != {"canonical", "multiplier"}
            or type(unit["canonical"]) is not str
            or type(unit["multiplier"]) is not int
            or unit["multiplier"] <= 0
            or family_id in matchers
            or len(set(child_roles)) != len(child_roles)
        ):
            raise _error(f"{family_id} unit, child, or uniqueness binding drifted")
        _validated_aliases(matcher["owner_aliases"], f"{family_id} owner")
        _validated_aliases(matcher["branch_aliases"], f"{family_id} branch")
        matchers[family_id] = matcher

    sample_by_truth_id: dict[str, dict[str, Any]] = {}
    locator_to_truth_id: dict[tuple[str, int], str] = {}
    manifest_samples = crop_request["manifest_sample_by_id"]
    sample_id_by_locator = {
        (
            manifest_pages[sample["page_id"]]["result_ref"]["sha256"],
            sample["source_line_index"],
        ): sample_id
        for sample_id, sample in manifest_samples.items()
    }
    if type(truth["samples"]) is not list or not truth["samples"]:
        raise _error("post-freeze truth has no transcript samples")
    for sample in truth["samples"]:
        fields = {
            "truth_id",
            "source_result_sha256",
            "source_line_index",
            "expected_text",
            "category",
            "semantic_role",
            "case_ids",
        }
        if type(sample) is not dict or set(sample) != fields:
            raise _error("truth transcript sample fields drifted")
        truth_id = sample["truth_id"]
        locator = (sample["source_result_sha256"], sample["source_line_index"])
        expected = sample["expected_text"]
        if (
            type(truth_id) is not str
            or not truth_id
            or truth_id in sample_by_truth_id
            or type(locator[0]) is not str
            or type(locator[1]) is not int
            or locator not in sample_id_by_locator
            or locator in locator_to_truth_id
            or type(expected) is not str
            or not expected
            or expected != unicodedata.normalize("NFC", expected)
            or expected != normalize_evaluation_line(expected)
            or type(sample["category"]) is not str
            or _ROLE_RE.fullmatch(sample["category"]) is None
            or type(sample["semantic_role"]) is not str
            or _ROLE_RE.fullmatch(sample["semantic_role"]) is None
            or type(sample["case_ids"]) is not list
            or not sample["case_ids"]
            or any(type(item) is not str or not item for item in sample["case_ids"])
        ):
            raise _error(f"truth transcript sample binding drifted: {truth_id}")
        sample_by_truth_id[truth_id] = sample
        locator_to_truth_id[locator] = truth_id

    case_by_id: dict[str, dict[str, Any]] = {}
    if type(truth["cases"]) is not list or not truth["cases"]:
        raise _error("post-freeze truth has no cases")
    for case in truth["cases"]:
        fields = {
            "case_id",
            "bank",
            "case_role",
            "family_id",
            "source_result_sha256",
            "source_line_start",
            "source_line_end",
            "required_truth_ids",
            "required_unit_count",
        }
        if type(case) is not dict or set(case) != fields:
            raise _error("truth case fields drifted")
        case_id = case["case_id"]
        result_sha = case["source_result_sha256"]
        if (
            type(case_id) is not str
            or not case_id
            or case_id in case_by_id
            or case["case_role"] not in {"POSITIVE", "HARD_CONTROL"}
            or case["family_id"] not in matchers
            or result_sha not in truth_page_by_result
            or case["bank"] != truth_page_by_result[result_sha]["bank"]
            or type(case["source_line_start"]) is not int
            or type(case["source_line_end"]) is not int
            or not 0 <= case["source_line_start"] <= case["source_line_end"]
            or type(case["required_unit_count"]) is not int
            or case["required_unit_count"] < 0
            or type(case["required_truth_ids"]) is not list
            or len(set(case["required_truth_ids"])) != len(case["required_truth_ids"])
        ):
            raise _error(f"truth case binding drifted: {case_id}")
        required = case["required_truth_ids"]
        if case["case_role"] == "HARD_CONTROL" and required:
            raise _error(f"hard control {case_id} cannot define an accepted truth topology")
        if case["case_role"] == "POSITIVE" and not required:
            raise _error(f"positive case {case_id} has no strict topology truth")
        for truth_id in required:
            sample = sample_by_truth_id.get(truth_id)
            if (
                sample is None
                or case_id not in sample["case_ids"]
                or sample["source_result_sha256"] != result_sha
                or not case["source_line_start"]
                <= sample["source_line_index"]
                <= case["source_line_end"]
            ):
                raise _error(f"{case_id} required truth locator drifted: {truth_id}")
        case_by_id[case_id] = case
    for truth_id, sample in sample_by_truth_id.items():
        if any(case_id not in case_by_id for case_id in sample["case_ids"]):
            raise _error(f"truth sample cites an unknown case: {truth_id}")

    truth["_path"] = path
    truth["_sha256"] = expected_truth_sha256
    truth["_truth_page_by_result"] = truth_page_by_result
    truth["_page_id_by_result"] = page_id_by_result
    truth["_sample_id_by_locator"] = sample_id_by_locator
    truth["_sample_by_truth_id"] = sample_by_truth_id
    truth["_case_by_id"] = case_by_id
    truth["_matchers"] = matchers
    return truth


def _prediction_lines(
    *,
    result_sha: str,
    truth: Mapping[str, Any],
    run: Mapping[str, Any],
) -> dict[int, str]:
    page_id = truth["_page_id_by_result"][result_sha]
    manifest_samples = run["prediction_by_id"]
    lines = {}
    for (candidate_sha, line_index), sample_id in truth["_sample_id_by_locator"].items():
        if candidate_sha == result_sha:
            lines[line_index] = manifest_samples[sample_id]["raw_prediction"]
    expected_count = sum(
        candidate_sha == result_sha for candidate_sha, _ in truth["_sample_id_by_locator"]
    )
    if len(lines) != expected_count:
        raise _error(f"prediction line reconstruction drifted: {page_id}")
    return lines


def _aliases_match(text: str, aliases: Sequence[str], *, allow_suffix: bool) -> bool:
    resolved = resolve_vietnamese_semantic_role(
        text,
        {"ROLE": aliases},
        allow_suffix=allow_suffix,
    )
    return resolved["accepted_role"] == "ROLE"


def _accentless_aliases_shortlist_match(
    text: str, aliases: Sequence[str], *, allow_suffix: bool
) -> bool:
    text_key = accentless_semantic_shortlist_key(text)
    alias_keys = tuple(accentless_semantic_shortlist_key(alias) for alias in aliases)
    return any(
        text_key == alias or (allow_suffix and text_key.startswith(f"{alias} "))
        for alias in alias_keys
    )


def _topology_scan(
    ordered: Sequence[tuple[int, str]],
    *,
    case: Mapping[str, Any],
    matcher: Mapping[str, Any],
    accentless_shortlist: bool,
) -> dict[str, Any]:
    match = _accentless_aliases_shortlist_match if accentless_shortlist else _aliases_match
    owner_indices = [
        index
        for index, text in ordered
        if match(text, matcher["owner_aliases"], allow_suffix=False)
    ]
    branch_indices = [
        index
        for index, text in ordered
        if match(text, matcher["branch_aliases"], allow_suffix=True)
    ]
    complete_candidates = []
    for branch_index in branch_indices:
        previous = branch_index
        child_matches = []
        for child in matcher["ordered_children"]:
            candidates = [
                index
                for index, text in ordered
                if index > previous and match(text, child["aliases"], allow_suffix=False)
            ]
            if not candidates:
                break
            previous = candidates[0]
            child_matches.append({"role": child["role"], "source_line_index": previous})
        if len(child_matches) == len(matcher["ordered_children"]):
            complete_candidates.append(
                {"branch_source_line_index": branch_index, "children": child_matches}
            )
    unit_indices = []
    for index, text in ordered:
        parsed = parse_unit(text)
        if (
            parsed.canonical == matcher["unit"]["canonical"]
            and parsed.multiplier == matcher["unit"]["multiplier"]
        ):
            unit_indices.append(index)
    context_complete_candidates = [
        candidate
        for candidate in complete_candidates
        if any(index < candidate["branch_source_line_index"] for index in owner_indices)
        and len(unit_indices) >= case["required_unit_count"]
    ]
    return {
        "owner_source_line_indices": owner_indices,
        "branch_source_line_indices": branch_indices,
        "complete_semantic_core_candidates": complete_candidates,
        "matching_unit_source_line_indices": unit_indices,
        "semantic_merge_detected": bool(complete_candidates),
        "context_complete_shape_detected": bool(context_complete_candidates),
    }


def _detect_family_topology(
    lines: Mapping[int, str],
    *,
    case: Mapping[str, Any],
    matcher: Mapping[str, Any],
) -> dict[str, Any]:
    start = case["source_line_start"]
    end = case["source_line_end"]
    ordered = [(index, lines[index]) for index in range(start, end + 1) if index in lines]
    exact = _topology_scan(
        ordered,
        case=case,
        matcher=matcher,
        accentless_shortlist=False,
    )
    accentless = _topology_scan(
        ordered,
        case=case,
        matcher=matcher,
        accentless_shortlist=True,
    )
    return {
        "owner_source_line_indices": exact["owner_source_line_indices"],
        "branch_source_line_indices": exact["branch_source_line_indices"],
        "complete_semantic_core_candidates": exact["complete_semantic_core_candidates"],
        "matching_unit_source_line_indices": exact["matching_unit_source_line_indices"],
        "semantic_merge_detected": exact["semantic_merge_detected"],
        "acceptance_shape_detected": exact["context_complete_shape_detected"],
        "accentless_owner_source_line_indices": accentless["owner_source_line_indices"],
        "accentless_branch_source_line_indices": accentless["branch_source_line_indices"],
        "accentless_complete_semantic_core_candidates": accentless[
            "complete_semantic_core_candidates"
        ],
        "accentless_semantic_merge_shortlist_detected": accentless["semantic_merge_detected"],
        "accentless_topology_shortlist_detected": accentless["context_complete_shape_detected"],
        "accentless_shortlist_alone_can_accept": False,
    }


def _timing_summary(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {
            "sample_count": 0,
            "sum_seconds": 0.0,
            "mean_seconds": None,
            "median_seconds": None,
            "p95_seconds": None,
        }
    return {
        "sample_count": len(ordered),
        "sum_seconds": sum(ordered),
        "mean_seconds": statistics.fmean(ordered),
        "median_seconds": statistics.median(ordered),
        "p95_seconds": ordered[math.ceil(len(ordered) * 0.95) - 1],
    }


def _score_architecture(
    label: str,
    *,
    run: Mapping[str, Any],
    truth: Mapping[str, Any],
) -> dict[str, Any]:
    transcript_inputs = []
    exact_by_truth_id: dict[str, bool] = {}
    unit_exact = 0
    unit_parse_correct = 0
    core_exact = 0
    core_count = 0
    for truth_id, sample in truth["_sample_by_truth_id"].items():
        locator = (sample["source_result_sha256"], sample["source_line_index"])
        sample_id = truth["_sample_id_by_locator"][locator]
        prediction = run["prediction_by_id"][sample_id]["raw_prediction"]
        exact = normalize_evaluation_line(prediction) == sample["expected_text"]
        exact_by_truth_id[truth_id] = exact
        bank = truth["_truth_page_by_result"][locator[0]]["bank"]
        transcript_inputs.append(
            {
                "sample_id": truth_id,
                "document": bank,
                "category": sample["category"],
                "reference": sample["expected_text"],
                "prediction": prediction,
            }
        )
        if sample["semantic_role"] == "UNIT":
            unit_exact += int(exact)
            expected_unit = parse_unit(sample["expected_text"])
            predicted_unit = parse_unit(prediction)
            unit_parse_correct += int(
                predicted_unit.canonical == expected_unit.canonical
                and predicted_unit.multiplier == expected_unit.multiplier
            )
        else:
            core_count += 1
            core_exact += int(exact)
    scored = score_reader(transcript_inputs, title_categories=set())

    case_results = []
    strict_positive = 0
    semantic_positive = 0
    accentless_shortlist_positive = 0
    control_false_merge = 0
    control_false_accept = 0
    control_accentless_false_merge = 0
    for case in truth["cases"]:
        lines = _prediction_lines(
            result_sha=case["source_result_sha256"],
            truth=truth,
            run=run,
        )
        topology = _detect_family_topology(
            lines,
            case=case,
            matcher=truth["_matchers"][case["family_id"]],
        )
        strict_exact = case["case_role"] == "POSITIVE" and all(
            exact_by_truth_id[truth_id] for truth_id in case["required_truth_ids"]
        )
        if case["case_role"] == "POSITIVE":
            strict_positive += int(strict_exact)
            semantic_positive += int(topology["acceptance_shape_detected"])
            accentless_shortlist_positive += int(topology["accentless_topology_shortlist_detected"])
        else:
            control_false_merge += int(topology["semantic_merge_detected"])
            control_false_accept += int(topology["acceptance_shape_detected"])
            control_accentless_false_merge += int(
                topology["accentless_semantic_merge_shortlist_detected"]
            )
        case_results.append(
            {
                "case_id": case["case_id"],
                "bank": case["bank"],
                "case_role": case["case_role"],
                "family_id": case["family_id"],
                "strict_exact_topology": strict_exact,
                **topology,
            }
        )

    sample_bank: dict[str, str] = {}
    manifest = truth["_sample_id_by_locator"]
    for (result_sha, _line_index), sample_id in manifest.items():
        sample_bank[sample_id] = truth["_truth_page_by_result"][result_sha]["bank"]
    timing_by_bank: dict[str, list[float]] = defaultdict(list)
    all_times = []
    for sample_id, prediction in run["prediction_by_id"].items():
        seconds = float(prediction["wall_seconds"])
        all_times.append(seconds)
        timing_by_bank[sample_bank[sample_id]].append(seconds)
    aggregate = scored["aggregate"]
    metrics = {
        "truth_transcript_count": aggregate["line_count"],
        "exact_vietnamese_transcript_count": aggregate["exact_line_count"],
        "character_error_rate": aggregate["character_error_rate"],
        "word_error_rate": aggregate["word_error_rate"],
        "core_role_count": core_count,
        "core_role_exact_count": core_exact,
        "unit_label_count": sum(sample["semantic_role"] == "UNIT" for sample in truth["samples"]),
        "unit_label_exact_count": unit_exact,
        "unit_parse_correct_count": unit_parse_correct,
        "strict_family_topology_positive_count": strict_positive,
        "semantic_family_topology_positive_count": semantic_positive,
        "accentless_topology_shortlist_positive_count": accentless_shortlist_positive,
        "control_false_semantic_merge_count": control_false_merge,
        "control_false_acceptance_shape_count": control_false_accept,
        "control_accentless_false_merge_count": control_accentless_false_merge,
        "empty_prediction_count": aggregate["empty_prediction_count"],
        "suffix_truncated_count": aggregate["suffix_truncated_count"],
        "insertion_error_count_hallucination_proxy": aggregate["insertion_count"],
        "deletion_error_count": aggregate["deletion_count"],
        "substitution_error_count": aggregate["substitution_count"],
        "diacritic_only_error_count": aggregate["diacritic_only_error_count"],
    }
    return {
        "architecture": run["architecture"],
        "model_binding": {
            "config_path": run["config_relative_path"],
            "config_sha256": run["config_sha256"],
            "result_sha256": run["result_sha256"],
            "run_manifest_sha256": run["run_sha256"],
        },
        "metrics": metrics,
        "transcript_score": {
            "aggregate": aggregate,
            "by_category": scored["by_category"],
        },
        "cases": case_results,
        "timing": {
            "model_load_seconds": run["run"]["metrics"]["model_load_seconds"],
            "total_wall_seconds": run["run"]["metrics"]["total_wall_seconds"],
            "all_lines": _timing_summary(all_times),
            "by_bank": {
                bank: _timing_summary(values) for bank, values in sorted(timing_by_bank.items())
            },
        },
    }


def _delta(seq2seq: Mapping[str, Any], transformer: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "exact_vietnamese_transcript_count",
        "core_role_exact_count",
        "unit_label_exact_count",
        "unit_parse_correct_count",
        "strict_family_topology_positive_count",
        "semantic_family_topology_positive_count",
        "accentless_topology_shortlist_positive_count",
        "control_false_semantic_merge_count",
        "control_false_acceptance_shape_count",
        "control_accentless_false_merge_count",
        "character_error_rate",
        "word_error_rate",
        "empty_prediction_count",
        "suffix_truncated_count",
        "insertion_error_count_hallucination_proxy",
        "deletion_error_count",
        "substitution_error_count",
    )
    return {field: seq2seq["metrics"][field] - transformer["metrics"][field] for field in fields}


def _selection_rank(score: Mapping[str, Any]) -> tuple[Any, ...] | None:
    metrics = score["metrics"]
    if (
        metrics["control_false_semantic_merge_count"]
        or metrics["control_false_acceptance_shape_count"]
    ):
        return None
    return (
        metrics["strict_family_topology_positive_count"],
        metrics["core_role_exact_count"],
        metrics["unit_label_exact_count"],
        metrics["unit_parse_correct_count"],
        -metrics["character_error_rate"],
        -metrics["suffix_truncated_count"],
        -metrics["insertion_error_count_hallucination_proxy"],
        -float(score["timing"]["total_wall_seconds"]),
    )


def _line_comparisons(
    truth: Mapping[str, Any], runs: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    records = []
    for truth_id, sample in truth["_sample_by_truth_id"].items():
        locator = (sample["source_result_sha256"], sample["source_line_index"])
        sample_id = truth["_sample_id_by_locator"][locator]
        transformer = runs["transformer"]["prediction_by_id"][sample_id]["raw_prediction"]
        seq2seq = runs["seq2seq"]["prediction_by_id"][sample_id]["raw_prediction"]
        bank = truth["_truth_page_by_result"][locator[0]]["bank"]
        records.append(
            {
                "truth_id": truth_id,
                "bank": bank,
                "category": sample["category"],
                "semantic_role": sample["semantic_role"],
                "source_result_sha256": locator[0],
                "source_line_index": locator[1],
                "expected_text": sample["expected_text"],
                "transformer_prediction": transformer,
                "seq2seq_prediction": seq2seq,
                "transformer_metrics": score_line(sample["expected_text"], transformer),
                "seq2seq_metrics": score_line(sample["expected_text"], seq2seq),
            }
        )
    return records


def _per_bank_deltas(
    comparisons: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in comparisons:
        grouped[record["bank"]].append(record)
    output = {}
    for bank, records in sorted(grouped.items()):
        transformer_inputs = [
            {
                "sample_id": item["truth_id"],
                "document": bank,
                "category": item["category"],
                "reference": item["expected_text"],
                "prediction": item["transformer_prediction"],
            }
            for item in records
        ]
        seq2seq_inputs = [
            {**item, "prediction": record["seq2seq_prediction"]}
            for item, record in zip(transformer_inputs, records, strict=True)
        ]
        transformer = score_reader(transformer_inputs, title_categories=set())["aggregate"]
        seq2seq = score_reader(seq2seq_inputs, title_categories=set())["aggregate"]
        output[bank] = {
            "truth_line_count": len(records),
            "transformer_exact_line_count": transformer["exact_line_count"],
            "seq2seq_exact_line_count": seq2seq["exact_line_count"],
            "seq2seq_minus_transformer_exact_line_count": (
                seq2seq["exact_line_count"] - transformer["exact_line_count"]
            ),
            "transformer_character_error_rate": transformer["character_error_rate"],
            "seq2seq_character_error_rate": seq2seq["character_error_rate"],
            "seq2seq_minus_transformer_character_error_rate": (
                seq2seq["character_error_rate"] - transformer["character_error_rate"]
            ),
        }
    return output


def build_frozen_vietocr_architecture_comparison(
    project_root: Path,
    *,
    crop_manifest_path: Path,
    reader_request_path: Path,
    transformer_output_directory: Path,
    transformer_result_sha256: str,
    transformer_run_manifest_sha256: str,
    seq2seq_output_directory: Path,
    seq2seq_result_sha256: str,
    seq2seq_run_manifest_sha256: str,
    truth_path: Path,
    truth_sha256: str,
) -> dict[str, Any]:
    """Authenticate both opaque runs before loading and joining transcript truth."""

    root = project_root.resolve()
    crop_request = _verify_crop_request(root, crop_manifest_path, reader_request_path)
    transformer_root = _resolve(root, transformer_output_directory, "transformer output")
    seq2seq_root = _resolve(root, seq2seq_output_directory, "seq2seq output")
    if transformer_root == seq2seq_root:
        raise _error("Transformer and Seq2Seq outputs must be distinct frozen directories")

    # Do not move truth loading above this complete two-run authentication barrier.
    runs = {
        "transformer": _verify_architecture_run(
            root,
            crop_request=crop_request,
            architecture_label="transformer",
            output_directory=transformer_root,
            expected_result_sha256=transformer_result_sha256,
            expected_run_manifest_sha256=transformer_run_manifest_sha256,
        ),
        "seq2seq": _verify_architecture_run(
            root,
            crop_request=crop_request,
            architecture_label="seq2seq",
            output_directory=seq2seq_root,
            expected_result_sha256=seq2seq_result_sha256,
            expected_run_manifest_sha256=seq2seq_run_manifest_sha256,
        ),
    }
    truth = _validate_truth(
        root,
        truth_path=truth_path,
        expected_truth_sha256=truth_sha256,
        crop_request=crop_request,
        runs=runs,
    )
    architecture_scores = {
        label: _score_architecture(label, run=run, truth=truth) for label, run in runs.items()
    }
    ranks = {label: _selection_rank(score) for label, score in architecture_scores.items()}
    eligible = {label: rank for label, rank in ranks.items() if rank is not None}
    if not eligible:
        selected = None
        selection_status = "NO_SAFE_ARCHITECTURE_CONTROL_REGRESSION"
    else:
        best = max(eligible.values())
        winners = [label for label, rank in eligible.items() if rank == best]
        selected = architecture_scores[winners[0]]["architecture"] if len(winners) == 1 else None
        selection_status = (
            "SELECTED_SEMANTIC_PROPOSAL_ARCHITECTURE"
            if selected is not None
            else "NO_UNIQUE_ACCURACY_WINNER"
        )
    comparisons = _line_comparisons(truth, runs)
    return {
        "format_version": FORMAT_VERSION,
        "state": "COMPLETE_POSTFREEZE_TRUTH_JOIN",
        "dataset_role": "DEVELOPMENT_REPLAY",
        "claim_boundary": CLAIM_BOUNDARY,
        "inputs": {
            "crop_manifest": {
                "path": crop_request["manifest_path"].relative_to(root).as_posix(),
                "sha256": crop_request["manifest_sha256"],
            },
            "reader_request": {
                "path": crop_request["request_path"].relative_to(root).as_posix(),
                "sha256": crop_request["request_sha256"],
            },
            "postfreeze_truth": {
                "path": truth["_path"].relative_to(root).as_posix(),
                "sha256": truth["_sha256"],
            },
            "transformer_result_sha256": runs["transformer"]["result_sha256"],
            "transformer_run_manifest_sha256": runs["transformer"]["run_sha256"],
            "seq2seq_result_sha256": runs["seq2seq"]["result_sha256"],
            "seq2seq_run_manifest_sha256": runs["seq2seq"]["run_sha256"],
        },
        "denominators": {
            "page_count": len(truth["pages"]),
            "all_line_crop_count": len(crop_request["request_samples"]),
            "truth_transcript_count": len(truth["samples"]),
            "positive_family_case_count": sum(
                case["case_role"] == "POSITIVE" for case in truth["cases"]
            ),
            "hard_control_case_count": sum(
                case["case_role"] == "HARD_CONTROL" for case in truth["cases"]
            ),
        },
        "architectures": architecture_scores,
        "comparison": {
            "selection_status": selection_status,
            "selected_architecture": selected,
            "user_decision": "USE_OFFICIAL_VIETOCR_TRANSFORMER_AS_SEMANTIC_READER",
            "benchmark_corroborates_user_decision": selected == _ARCHITECTURES["transformer"],
            "seq2seq_disposition": "BENCHMARK_ONLY",
            "selection_order": [
                "ZERO_CONTROL_FALSE_MERGE_AND_FALSE_ACCEPT",
                "MAX_STRICT_FAMILY_TOPOLOGY",
                "MAX_CORE_ROLE_EXACT",
                "MAX_UNIT_EXACT",
                "MAX_UNIT_PARSE_CORRECT",
                "MIN_CHARACTER_ERROR_RATE",
                "MIN_SUFFIX_TRUNCATION",
                "MIN_INSERTION_ERROR_PROXY",
                "MIN_TOTAL_WALL_SECONDS_ONLY_AFTER_ACCURACY_TIE",
            ],
            "seq2seq_minus_transformer": _delta(
                architecture_scores["seq2seq"], architecture_scores["transformer"]
            ),
            "per_bank_deltas": _per_bank_deltas(comparisons),
            "line_comparisons": comparisons,
        },
        "safety": {
            "both_model_outputs_authenticated_before_truth_file_access": True,
            "truth_available_to_either_model": False,
            "ppocr_v3_geometry_and_source_locator_authority_retained": True,
            "ppocr_v3_numeric_period_sign_authority_retained": True,
            "vietocr_unit_authority_granted": False,
            "accepted_structure_claimed": False,
            "schema_or_mapping_authority_granted": False,
            "insertion_count_is_hallucination_proxy_not_proof": True,
            "onnx_model_evaluated_or_selected": False,
            "accentless_topology_metrics_are_diagnostic_only": True,
            "semantic_text_policy": SEMANTIC_TEXT_POLICY,
        },
    }


def render_vietocr_architecture_comparison_text(payload: Mapping[str, Any]) -> str:
    """Render the frozen comparison as inspectable UTF-8 Vietnamese text."""

    lines = [
        "SO SÁNH VIETOCR TRANSFORMER VÀ SEQ2SEQ — HẬU KIỂM SAU FREEZE",
        "",
        f"Kết luận: {payload['comparison']['selection_status']}",
        f"Kiến trúc được chọn: {payload['comparison']['selected_architecture'] or 'CHƯA CHỌN'}",
        "Quyết định: official VietOCR Transformer là semantic reader; Seq2Seq chỉ benchmark.",
        f"Giới hạn kết luận: {payload['claim_boundary']}",
        "",
        "TỔNG HỢP",
    ]
    for label in ("transformer", "seq2seq"):
        score = payload["architectures"][label]
        metrics = score["metrics"]
        lines.extend(
            [
                f"[{label}] {score['architecture']}",
                "  Văn bản đúng tuyệt đối: "
                f"{metrics['exact_vietnamese_transcript_count']}/"
                f"{metrics['truth_transcript_count']}",
                f"  Core role đúng: {metrics['core_role_exact_count']}/"
                f"{metrics['core_role_count']}",
                f"  Unit đúng tuyệt đối: {metrics['unit_label_exact_count']}/"
                f"{metrics['unit_label_count']}",
                "  Strict family topology: "
                f"{metrics['strict_family_topology_positive_count']}/"
                f"{payload['denominators']['positive_family_case_count']}",
                "  Accentless topology shortlist (diagnostic-only): "
                f"{metrics['accentless_topology_shortlist_positive_count']}/"
                f"{payload['denominators']['positive_family_case_count']}",
                "  Control false merge / false accept: "
                f"{metrics['control_false_semantic_merge_count']} / "
                f"{metrics['control_false_acceptance_shape_count']} "
                f"(trên {payload['denominators']['hard_control_case_count']} controls)",
                "  Control accentless false-merge shortlist: "
                f"{metrics['control_accentless_false_merge_count']}/"
                f"{payload['denominators']['hard_control_case_count']}",
                f"  CER / WER: {metrics['character_error_rate']:.6f} / "
                f"{metrics['word_error_rate']:.6f}",
                "  Empty / truncation / insertion-proxy: "
                f"{metrics['empty_prediction_count']} / "
                f"{metrics['suffix_truncated_count']} / "
                f"{metrics['insertion_error_count_hallucination_proxy']}",
                f"  Tổng thời gian: {score['timing']['total_wall_seconds']:.6f} giây",
            ]
        )
    lines.extend(["", "DELTA THEO NGÂN HÀNG (SEQ2SEQ - TRANSFORMER)"])
    for bank, delta in payload["comparison"]["per_bank_deltas"].items():
        lines.append(
            f"{bank}: exact {delta['seq2seq_minus_transformer_exact_line_count']:+d}; "
            "CER "
            f"{delta['seq2seq_minus_transformer_character_error_rate']:+.6f}"
        )
    lines.extend(["", "CHI TIẾT CÁC DÒNG ĐỐI CHIẾU"])
    for record in payload["comparison"]["line_comparisons"]:
        lines.extend(
            [
                f"{record['truth_id']} | {record['bank']} | {record['semantic_role']}",
                f"  Chuẩn:       {record['expected_text']}",
                f"  Transformer: {record['transformer_prediction']}",
                f"  Seq2Seq:     {record['seq2seq_prediction']}",
            ]
        )
    lines.extend(
        [
            "",
            "LƯU Ý",
            "Insertion count chỉ là proxy cho hallucination, không phải bằng chứng hallucination.",
            "VietOCR không được cấp quyền số, kỳ, dấu, geometry, structure, schema hoặc mapping.",
            "Transcript luôn giữ UTF-8/NFC và dấu tiếng Việt. Key bỏ dấu một mình",
            "không được accept; scorer này chỉ shortlist. Downstream chỉ được promote",
            "candidate duy nhất, không collision khi có đủ owner/siblings/axes/unit/value/total/closure;",
            "collision/ambiguity luôn UNRESOLVED và không fuzzy nearest-role.",
        ]
    )
    return "\n".join(lines) + "\n"


def capture_frozen_vietocr_architecture_comparison(
    project_root: Path,
    *,
    json_output_path: Path,
    text_output_path: Path,
    **comparison_arguments: Any,
) -> dict[str, Any]:
    """Build once and atomically publish paired UTF-8 JSON/TXT artifacts."""

    root = project_root.resolve()
    json_path = _resolve(root, json_output_path, "JSON output")
    text_path = _resolve(root, text_output_path, "text output")
    if json_path == text_path or json_path.exists() or text_path.exists():
        raise _error("comparison output paths collide or already exist")
    payload = build_frozen_vietocr_architecture_comparison(
        root,
        **comparison_arguments,
    )
    atomic_write_json(json_path, payload)
    atomic_write_text(text_path, render_vietocr_architecture_comparison_text(payload))
    return payload


__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "TRUTH_FORMAT_VERSION",
    "SEMANTIC_TEXT_POLICY",
    "VietOCRArchitectureComparisonError",
    "accentless_semantic_shortlist_key",
    "build_frozen_vietocr_architecture_comparison",
    "capture_frozen_vietocr_architecture_comparison",
    "render_vietocr_architecture_comparison_text",
    "resolve_vietnamese_semantic_role",
]
