"""Authenticated plan for the all-filing family-first semantic-label cache.

The plan is private provenance and coverage metadata.  Detector/reader workers
receive anonymous document/page/sample ordinals; bank, period, scope, path and
year are never family-matching inputs.  The plan binds the exact 140 selected
filings, their live PDF page denominators, the render policy, implementation
bytes and the complete executable PP-OCRv6 detector model file set.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.family_first_filing_inventory_v1 import (
    INVENTORY_PATH,
    read_family_first_filing_inventory_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "RUNTIME_CONFIG_PATH",
    "FamilyFirstSemanticLabelPlanV1Error",
    "build_family_first_semantic_label_plan_v1",
    "validate_family_first_semantic_label_plan_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_SEMANTIC_LABEL_CACHE_PLAN_V1"
RUNTIME_CONFIG_PATH = Path("config/models/family-first-ocr-runtime-v1.toml")
_PLAN_FIELDS = {
    "authority",
    "claim_boundary",
    "detector",
    "documents",
    "format_version",
    "git_binding",
    "input_refs",
    "metrics",
    "missing_filings",
    "plan_id",
    "render_policy",
}
_AUTHORITY = {
    "bank_path_period_scope_used_for_family_matching": False,
    "detector_recognition_text_enabled": False,
    "family_authority": False,
    "inventory_is_private_provenance_and_coverage_only": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "related_party_family_in_scope": False,
    "schema_authority": False,
    "semantic_authority": False,
}
_CLAIM_BOUNDARY = (
    "EXACT_ALL_SELECTED_FILING_AND_PAGE_DENOMINATOR_RENDER_DETECTOR_MODEL_AND_"
    "IMPLEMENTATION_PLAN_ONLY_NO_OCR_SEMANTIC_NUMERIC_PERIOD_UNIT_STRUCTURE_"
    "FAMILY_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/build_family_first_semantic_label_cache_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_filing_inventory_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_semantic_label_freeze_v1.py"),
    Path("src/bctc_ai/evaluation/family_first_semantic_label_plan_v1.py"),
)
_RUNTIME_FIELDS = {
    "all_detected_lines_retained",
    "detector",
    "detector_recognition_text_enabled",
    "format_version",
    "gemma_rescue",
    "numeric_recognizer",
    "paddle_device",
    "paddleocr_version",
    "paddlepaddle_version",
    "pymupdf_version",
    "render_colorspace",
    "render_dpi",
    "semantic_reader",
    "state",
}
_MODEL_FIELDS = {"cache_directory", "enable_mkldnn", "repo_id", "required_files", "revision"}
_FILE_FIELDS = {"path", "sha256", "size_bytes"}


class FamilyFirstSemanticLabelPlanV1Error(ValueError):
    """The filing denominator, runtime, model, code, or plan replay drifted."""


def _error(message: str) -> FamilyFirstSemanticLabelPlanV1Error:
    return FamilyFirstSemanticLabelPlanV1Error(message)


def _run_git(root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise _error("Git trust-closure query failed") from exc


def _resolve_root(project_root: Any) -> Path:
    if not isinstance(project_root, Path):
        raise _error("project root must be one pathlib Path")
    root = project_root.resolve()
    raw = _run_git(root, "rev-parse", "--show-toplevel")
    try:
        top = Path(raw.decode("utf-8", errors="strict").strip()).resolve()
    except UnicodeDecodeError as exc:
        raise _error("Git project root is not strict UTF-8") from exc
    if top != root:
        raise _error("project root must be the exact Git toplevel")
    return root


def _stable_bytes(path: Path, label: str) -> tuple[bytes, os.stat_result]:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise _error(f"{label} must be one single-link regular file")
    payload = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or len(payload) != before.st_size:
        raise _error(f"{label} changed while being read")
    return payload, before


def _content_ref(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}


def _git_binding(root: Path) -> dict[str, Any]:
    if _run_git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise _error("family-first plan requires one clean Git worktree")
    head = _run_git(root, "rev-parse", "HEAD").decode("ascii", errors="strict").strip()
    source_tree = (
        _run_git(root, "rev-parse", "HEAD:src/bctc_ai").decode("ascii", errors="strict").strip()
    )
    refs = []
    for relative in (*_IMPLEMENTATION_PATHS, RUNTIME_CONFIG_PATH, INVENTORY_PATH):
        disk, _metadata = _stable_bytes(root / relative, f"tracked trust file {relative}")
        committed = _run_git(root, "show", f"HEAD:{relative.as_posix()}")
        if disk != committed:
            raise _error(f"tracked trust file differs from HEAD: {relative}")
        refs.append(_content_ref(relative.as_posix(), disk))
    return {
        "commit": head,
        "implementation_refs": refs,
        "source_tree_oid": source_tree,
        "worktree_clean": True,
    }


def _runtime(root: Path) -> tuple[dict[str, Any], bytes]:
    payload, _metadata = _stable_bytes(root / RUNTIME_CONFIG_PATH, "family-first OCR runtime")
    try:
        parsed = tomllib.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _error("family-first OCR runtime is not strict TOML") from exc
    if type(parsed) is not dict or set(parsed) != _RUNTIME_FIELDS:
        raise _error("family-first OCR runtime fields drifted")
    if (
        parsed["format_version"] != "FAMILY_FIRST_OCR_RUNTIME_V1"
        or parsed["state"] != "PINNED_LOCAL_NO_NETWORK"
        or parsed["paddle_device"] != "cpu"
        or type(parsed["render_dpi"]) is not int
        or parsed["render_dpi"] != 200
        or parsed["render_colorspace"] != "RGB"
        or type(parsed["detector_recognition_text_enabled"]) is not bool
        or parsed["detector_recognition_text_enabled"] is not False
        or type(parsed["all_detected_lines_retained"]) is not bool
        or parsed["all_detected_lines_retained"] is not True
    ):
        raise _error("family-first OCR runtime policy drifted")
    for name in ("detector", "numeric_recognizer"):
        model = parsed[name]
        if type(model) is not dict or set(model) != _MODEL_FIELDS:
            raise _error(f"family-first {name} model fields drifted")
        if type(model["enable_mkldnn"]) is not bool or model["enable_mkldnn"] is not False:
            raise _error(f"family-first {name} oneDNN policy drifted")
        files = model["required_files"]
        if type(files) is not list or len(files) != 3:
            raise _error(f"family-first {name} executable file denominator drifted")
        for file_ref in files:
            if (
                type(file_ref) is not dict
                or set(file_ref) != _FILE_FIELDS
                or type(file_ref["path"]) is not str
                or Path(file_ref["path"]).name != file_ref["path"]
                or type(file_ref["size_bytes"]) is not int
                or file_ref["size_bytes"] <= 0
                or type(file_ref["sha256"]) is not str
                or len(file_ref["sha256"]) != 64
            ):
                raise _error(f"family-first {name} executable file reference drifted")
    return canonical_clone_v1(parsed), payload


def _model_projection(model_cache: Any, detector: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(model_cache, Path):
        raise _error("model cache must be one pathlib Path")
    cache = model_cache.resolve()
    model_directory = cache / "official_models" / detector["cache_directory"]
    metadata = model_directory.stat(follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode):
        raise _error("pinned detector model directory is not one nofollow directory")
    live_refs = []
    for expected in detector["required_files"]:
        path = model_directory / expected["path"]
        payload, _file_stat = _stable_bytes(path, f"detector model file {expected['path']}")
        actual = _content_ref(
            f"MODEL_CACHE/official_models/{detector['cache_directory']}/{expected['path']}",
            payload,
        )
        if actual["sha256"] != expected["sha256"] or actual["size_bytes"] != expected["size_bytes"]:
            raise _error(f"detector model file differs from runtime pin: {expected['path']}")
        live_refs.append(actual)
    return {
        "cache_directory": detector["cache_directory"],
        "enable_mkldnn": detector["enable_mkldnn"],
        "repo_id": detector["repo_id"],
        "required_files": live_refs,
        "revision": detector["revision"],
    }


def _page_count(pdf_bytes: bytes, label: str) -> int:
    try:
        import fitz

        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            count = document.page_count
    except (ImportError, RuntimeError, ValueError) as exc:
        raise _error(f"selected filing cannot be opened for page counting: {label}") from exc
    if type(count) is not int or count <= 0:
        raise _error(f"selected filing has no positive page denominator: {label}")
    return count


def _validate_plan(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PLAN_FIELDS:
        raise _error("family-first semantic-label plan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["documents"]) is not list
        or type(value["missing_filings"]) is not list
    ):
        raise _error("family-first semantic-label plan contract drifted")
    material = canonical_clone_v1(value)
    plan_id = material.pop("plan_id")
    if plan_id != "ffslpv1:plan:" + canonical_json_sha256_v1(material):
        raise _error("family-first semantic-label plan hash identity drifted")
    return canonical_clone_v1(value)


def build_family_first_semantic_label_plan_v1(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Build the clean-Git exact 140-filing/8,947-page detector plan."""

    root = _resolve_root(project_root)
    git_binding = _git_binding(root)
    inventory = read_family_first_filing_inventory_v1(root)
    runtime, runtime_bytes = _runtime(root)
    detector = _model_projection(model_cache, runtime["detector"])
    documents = []
    total_pages = 0
    for document_ordinal, filing in enumerate(inventory["filings"], start=1):
        source_ref = filing["content_ref"]
        pdf_bytes, _metadata = _stable_bytes(
            root / source_ref["path"],
            f"selected filing {document_ordinal}",
        )
        if (
            len(pdf_bytes) != source_ref["size_bytes"]
            or hashlib.sha256(pdf_bytes).hexdigest() != source_ref["sha256"]
        ):
            raise _error(f"selected filing content drifted: {document_ordinal}")
        count = _page_count(pdf_bytes, source_ref["path"])
        total_pages += count
        documents.append(
            {
                "document_ordinal": document_ordinal,
                "page_count": count,
                "private_provenance": {
                    "bank": filing["bank_provenance"],
                    "period": filing["period"],
                    "scope": filing["scope"],
                    "year": filing["year"],
                },
                "source_pdf_ref": canonical_clone_v1(source_ref),
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": _CLAIM_BOUNDARY,
        "detector": detector,
        "documents": documents,
        "format_version": FORMAT_VERSION,
        "git_binding": git_binding,
        "input_refs": {
            "inventory_ref": inventory["inventory_ref"],
            "runtime_config_ref": _content_ref(RUNTIME_CONFIG_PATH.as_posix(), runtime_bytes),
            "s3_snapshot_prefix": inventory["s3_snapshot_prefix"],
        },
        "metrics": {
            "document_count": len(documents),
            "explicit_missing_filing_count": len(inventory["missing_filings"]),
            "page_count": total_pages,
        },
        "missing_filings": inventory["missing_filings"],
        "render_policy": {
            "colorspace": runtime["render_colorspace"],
            "content_orientation_rescue_required_when_primary_unresolved": True,
            "dpi": runtime["render_dpi"],
            "pdf_page_rotation_applied_before_detection": True,
        },
    }
    return _validate_plan(
        {**material, "plan_id": "ffslpv1:plan:" + canonical_json_sha256_v1(material)}
    )


def validate_family_first_semantic_label_plan_replay_v1(
    value: Any, project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Rebuild the plan from clean live trust inputs and compare exact JSON types."""

    persisted = _validate_plan(value)
    expected = build_family_first_semantic_label_plan_v1(project_root, model_cache=model_cache)
    if not same_typed_json_v1(persisted, expected):
        raise _error("family-first semantic-label plan does not replay exactly")
    return persisted
