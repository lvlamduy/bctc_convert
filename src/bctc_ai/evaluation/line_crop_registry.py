from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageOps

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file


class LineCropRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class CropPolicy:
    source_padding: tuple[int, int, int, int]
    white_border: tuple[int, int, int, int]
    color_mode: str


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, relative: str) -> Path:
    path = (project_root / relative).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise LineCropRegistryError(f"path escapes project root: {relative}") from exc
    return path


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise LineCropRegistryError(f"cannot read crop registry config: {path}") from exc
    if not isinstance(value, dict):
        raise LineCropRegistryError("crop registry config must be an object")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LineCropRegistryError(f"cannot read PP-OCR evidence: {path}") from exc
    if not isinstance(value, dict):
        raise LineCropRegistryError(f"PP-OCR evidence must be an object: {path}")
    return value


def _four_nonnegative_ints(value: Any, name: str) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(item, int) or item < 0 for item in value)
    ):
        raise LineCropRegistryError(f"{name} must contain four non-negative integers")
    return tuple(value)  # type: ignore[return-value]


def _validate_config(config: dict[str, Any]) -> CropPolicy:
    if (
        config.get("version") != 1
        or config.get("experiment_id") != "E-0024"
        or config.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or config.get("selection_policy")
        != "FROZEN_BEFORE_CHALLENGER_INFERENCE_SOURCE_VISIBLE_SINGLE_LINES"
    ):
        raise LineCropRegistryError("E-0024 identity, role, or selection policy drifted")
    authority = config.get("authority")
    required_true = {
        "source_render_is_ground_truth",
        "expected_text_is_evaluation_only",
        "expected_text_must_not_enter_decoder",
        "semantic_reader_may_read_headings_and_labels_only",
        "ppocrv6_remains_geometry_and_numeric_authority",
    }
    required_false = {
        "semantic_reader_may_create_numeric_geometry",
        "semantic_reader_may_replace_digits_periods_units_or_signs",
        "automatic_ocr_post_correction",
    }
    if not isinstance(authority, dict):
        raise LineCropRegistryError("E-0024 authority policy is missing")
    if any(authority.get(key) is not True for key in required_true) or any(
        authority.get(key) is not False for key in required_false
    ):
        raise LineCropRegistryError("E-0024 authority policy grants unsafe reader powers")
    crop = config.get("crop_policy")
    if not isinstance(crop, dict) or crop.get("image_format") != "PNG":
        raise LineCropRegistryError("E-0024 crop policy is missing or unsupported")
    color_mode = str(crop.get("color_mode", ""))
    if color_mode != "RGB":
        raise LineCropRegistryError("E-0024 crops must preserve RGB source evidence")
    return CropPolicy(
        source_padding=_four_nonnegative_ints(
            crop.get("source_padding_left_top_right_bottom"), "source padding"
        ),
        white_border=_four_nonnegative_ints(
            crop.get("white_border_left_top_right_bottom"), "white border"
        ),
        color_mode=color_mode,
    )


def _verify_file(path: Path, expected_sha256: str, *, expected_size: int | None = None) -> None:
    if not path.is_file():
        raise LineCropRegistryError(f"required source artifact is missing: {path}")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise LineCropRegistryError(f"source size drifted: {path}")
    if sha256_file(path) != expected_sha256:
        raise LineCropRegistryError(f"source hash drifted: {path}")


def _crop_box(
    bbox: tuple[int, int, int, int],
    padding: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    pad_left, pad_top, pad_right, pad_bottom = padding
    result = (
        max(0, left - pad_left),
        max(0, top - pad_top),
        min(width, right + pad_right),
        min(height, bottom + pad_bottom),
    )
    if result[0] >= result[2] or result[1] >= result[3]:
        raise LineCropRegistryError(f"invalid padded crop box: {result}")
    return result


def build_line_crop_registry(
    project_root: Path,
    *,
    config_path: Path = Path("config/experiments/e0024-vietnamese-line-recognizer.yaml"),
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise LineCropRegistryError("formal crop build requires a clean Git worktree")
    resolved_config = _resolve(project_root, config_path.as_posix())
    config = _load_yaml(resolved_config)
    policy = _validate_config(config)
    config_sha256 = sha256_file(resolved_config)
    documents = config.get("documents")
    samples = config.get("samples")
    if not isinstance(documents, dict) or not isinstance(samples, list):
        raise LineCropRegistryError("E-0024 documents or samples are missing")
    if len(samples) != int(config.get("expected_sample_count", -1)):
        raise LineCropRegistryError("E-0024 sample denominator drifted")
    sample_ids = [str(sample.get("id", "")) for sample in samples if isinstance(sample, dict)]
    if len(sample_ids) != len(samples) or len(set(sample_ids)) != len(sample_ids):
        raise LineCropRegistryError("E-0024 sample IDs must be unique objects")
    if any(not re.fullmatch(r"[a-z0-9-]+", sample_id) for sample_id in sample_ids):
        raise LineCropRegistryError("E-0024 sample IDs must be path-safe")

    forbidden = {str(value) for value in config.get("forbidden_holdout_sha256", [])}
    page_cache: dict[tuple[str, int], tuple[Path, dict[str, Any]]] = {}
    verified_documents: dict[str, dict[str, Any]] = {}
    for document_key, document in documents.items():
        if not isinstance(document, dict):
            raise LineCropRegistryError(f"invalid document record: {document_key}")
        source_sha256 = str(document.get("source_sha256", ""))
        if source_sha256 in forbidden:
            raise LineCropRegistryError("E-0024 attempts to reuse a forbidden holdout")
        source_path = _resolve(project_root, str(document.get("source_pdf", "")))
        _verify_file(
            source_path,
            source_sha256,
            expected_size=int(document.get("source_size_bytes", -1)),
        )
        verified_documents[str(document_key)] = {
            "source_pdf": source_path.relative_to(project_root).as_posix(),
            "source_sha256": source_sha256,
            "source_size_bytes": source_path.stat().st_size,
        }

    output_root = _resolve(project_root, str(config.get("output_root", "")))
    run_root = output_root / config_sha256[:20]
    manifest_path = run_root / "crop_manifest.json"
    if run_root.exists():
        raise LineCropRegistryError(f"refusing to overwrite crop run: {run_root}")
    crop_root = run_root / "crops"
    crop_root.mkdir(parents=True)

    records: list[dict[str, Any]] = []
    try:
        for sample in samples:
            assert isinstance(sample, dict)
            sample_id = str(sample["id"])
            document_key = str(sample.get("document", ""))
            document = documents.get(document_key)
            if not isinstance(document, dict):
                raise LineCropRegistryError(f"sample references unknown document: {sample_id}")
            page = int(sample.get("page", 0))
            raw_pages = document.get("pages")
            page_record = raw_pages.get(page) if isinstance(raw_pages, dict) else None
            if not isinstance(page_record, dict):
                raise LineCropRegistryError(f"sample references unregistered page: {sample_id}")
            cache_key = (document_key, page)
            if cache_key not in page_cache:
                render = _resolve(
                    project_root,
                    f"{document['render_root']}/page-{page:04d}.png",
                )
                ppocr = _resolve(
                    project_root,
                    f"{document['ppocr_root']}/ppocrv6-page-{page:04d}/ocr_result.json",
                )
                _verify_file(render, str(page_record.get("render_sha256", "")))
                _verify_file(ppocr, str(page_record.get("ppocr_sha256", "")))
                page_cache[cache_key] = (render, _load_json(ppocr))
            render_path, ppocr_result = page_cache[cache_key]
            index = int(sample.get("ppocr_index", -1))
            try:
                observed_box = tuple(int(value) for value in ppocr_result["rec_boxes"][index])
                observed_text = str(ppocr_result["rec_texts"][index])
                observed_score = float(ppocr_result["rec_scores"][index])
            except (IndexError, KeyError, TypeError, ValueError) as exc:
                raise LineCropRegistryError(f"invalid PP-OCR anchor: {sample_id}") from exc
            expected_box = tuple(int(value) for value in sample.get("bbox", []))
            if observed_box != expected_box:
                raise LineCropRegistryError(f"PP-OCR bbox drifted: {sample_id}")
            if observed_text != str(sample.get("ppocr_text", "")):
                raise LineCropRegistryError(f"PP-OCR text drifted: {sample_id}")
            expected_text = str(sample.get("expected", ""))
            if not expected_text.strip() or not any(char.isalpha() for char in expected_text):
                raise LineCropRegistryError(f"sample is empty or numeric-only: {sample_id}")

            with Image.open(render_path) as source:
                image = source.convert(policy.color_mode)
                source_box = _crop_box(expected_box, policy.source_padding, *image.size)
                crop = image.crop(source_box)
                border_left, border_top, border_right, border_bottom = policy.white_border
                crop = ImageOps.expand(
                    crop,
                    border=(border_left, border_top, border_right, border_bottom),
                    fill="white",
                )
                crop_path = crop_root / f"{sample_id}.png"
                crop.save(crop_path, format="PNG", optimize=False)
                crop_size = crop.size

            records.append(
                {
                    "sample_id": sample_id,
                    "document": document_key,
                    "page": page,
                    "category": str(sample.get("category", "")),
                    "expected_text": expected_text,
                    "source_render": render_path.relative_to(project_root).as_posix(),
                    "source_render_sha256": str(page_record["render_sha256"]),
                    "ppocr_result_index": index,
                    "ppocr_bbox": list(observed_box),
                    "ppocr_text": observed_text,
                    "ppocr_score": observed_score,
                    "source_crop_bbox": list(source_box),
                    "crop_path": crop_path.relative_to(project_root).as_posix(),
                    "crop_width": crop_size[0],
                    "crop_height": crop_size[1],
                    "crop_sha256": sha256_file(crop_path),
                }
            )
    except Exception:
        for path in sorted(run_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if run_root.exists():
            run_root.rmdir()
        raise

    categories = sorted({str(record["category"]) for record in records})
    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE",
        "dataset_role": config["dataset_role"],
        "selection_policy": config["selection_policy"],
        "git_commit": _git(project_root, "rev-parse", "HEAD"),
        "git_dirty": False,
        "config": {
            "path": resolved_config.relative_to(project_root).as_posix(),
            "sha256": config_sha256,
        },
        "authority": config["authority"],
        "crop_policy": config["crop_policy"],
        "documents": verified_documents,
        "sample_count": len(records),
        "categories": categories,
        "samples": records,
        "claim_boundary": config["claim_boundary"],
    }
    atomic_write_json(manifest_path, payload)
    return payload
