from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.core.atomic import atomic_write_json  # noqa: E402
from bctc_ai.core.hashing import sha256_file  # noqa: E402


class MultibankAllLineRequestError(RuntimeError):
    pass


INPUT_FORMAT = "V3_AUTHENTICATED_LINE_MULTIPAGE_BATCH_INPUT_V1"
MANIFEST_FORMAT = "V3_AUTHENTICATED_LINE_GEOMETRY_ONLY_CROP_MANIFEST_V2"
RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
SOURCE_PADDING = (8, 4, 8, 4)
WHITE_BORDER = (12, 8, 12, 8)

_INPUT_KEYS = {"dataset_role", "format_version", "pages"}
_INPUT_PAGE_KEYS = {"render_ref", "result_ref"}
_OBJECT_REF_KEYS = {"path", "sha256", "size_bytes"}

SELECTION_RULE = {
    "deskew": False,
    "grouping": "ONE_CROP_PER_AUTHENTICATED_V3_LINE",
    "line_order": "V3_RESULT_LINES_ARRAY_ORDER",
    "primary_atom_type": "V3_AUTHENTICATED_LINE_WITH_RAW_PIXEL_BBOX",
    "resize": False,
    "selection": "ALL_AUTHENTICATED_LINES_WITHOUT_TEXT_OR_GEOMETRY_FILTERING",
    "source_padding_left_top_right_bottom": list(SOURCE_PADDING),
    "threshold": False,
    "unions": False,
    "white_border_left_top_right_bottom": list(WHITE_BORDER),
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(path: Path | str, label: str) -> Path:
    candidate = Path(path)
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
    )
    if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
        raise MultibankAllLineRequestError(f"{label} escapes project root")
    return resolved


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MultibankAllLineRequestError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise MultibankAllLineRequestError(f"{label} must be a JSON object")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise MultibankAllLineRequestError(f"{label} SHA-256 is invalid")
    return value


def _verified_ref(raw: Any, label: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(raw, dict) or set(raw) != _OBJECT_REF_KEYS:
        raise MultibankAllLineRequestError(f"{label} must be an exact object reference")
    relative_path = raw.get("path")
    size_bytes = raw.get("size_bytes")
    if not isinstance(relative_path, str) or not relative_path:
        raise MultibankAllLineRequestError(f"{label} path is invalid")
    if type(size_bytes) is not int or size_bytes < 0:
        raise MultibankAllLineRequestError(f"{label} size is invalid")
    expected_sha256 = _validate_sha256(raw.get("sha256"), label)
    path = _resolve(relative_path, label)
    if (
        not path.is_file()
        or path.stat().st_size != size_bytes
        or sha256_file(path) != expected_sha256
    ):
        raise MultibankAllLineRequestError(f"{label} is missing or hash-drifted")
    return path, {
        "path": path.relative_to(PROJECT_ROOT.resolve()).as_posix(),
        "sha256": expected_sha256,
        "size_bytes": size_bytes,
    }


def _bbox(raw: Any, *, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(raw, list) or len(raw) != 4 or any(type(value) is not int for value in raw):
        raise MultibankAllLineRequestError("V3 line bbox is invalid")
    x0, y0, x1, y1 = raw
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise MultibankAllLineRequestError("V3 line bbox lies outside the render")
    return x0, y0, x1, y1


def _line_boxes(
    lines: Sequence[Mapping[str, Any]], *, width: int, height: int
) -> list[tuple[int, int, int, int]]:
    """Project authenticated LINE geometry without consulting any transcript field."""

    return [_bbox(line.get("raw_pixel_bbox"), width=width, height=height) for line in lines]


def _padded(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = SOURCE_PADDING
    return (
        max(0, box[0] - left),
        max(0, box[1] - top),
        min(width, box[2] + right),
        min(height, box[3] + bottom),
    )


def _validated_input_pages(
    input_spec: dict[str, Any],
) -> list[tuple[dict[str, Any], Path, dict[str, Any], Path, dict[str, Any]]]:
    if set(input_spec) != _INPUT_KEYS:
        raise MultibankAllLineRequestError("batch input contains non-allowlisted fields")
    if (
        input_spec.get("format_version") != INPUT_FORMAT
        or input_spec.get("dataset_role") != "DEVELOPMENT_REPLAY"
    ):
        raise MultibankAllLineRequestError("batch input identity or role is invalid")
    raw_pages = input_spec.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise MultibankAllLineRequestError("batch input pages must be a non-empty list")

    validated = []
    seen_results: set[str] = set()
    seen_renders: set[str] = set()
    for ordinal, raw_page in enumerate(raw_pages, start=1):
        label = f"input page {ordinal:04d}"
        if not isinstance(raw_page, dict) or set(raw_page) != _INPUT_PAGE_KEYS:
            raise MultibankAllLineRequestError(f"{label} contains non-allowlisted fields")
        result_path, result_ref = _verified_ref(raw_page["result_ref"], f"{label} V3 result")
        render_path, render_ref = _verified_ref(raw_page["render_ref"], f"{label} render")
        if result_ref["sha256"] in seen_results or render_ref["sha256"] in seen_renders:
            raise MultibankAllLineRequestError("batch input contains a duplicate page")
        seen_results.add(result_ref["sha256"])
        seen_renders.add(render_ref["sha256"])

        result = _load_object(result_path, f"{label} V3 result")
        render_binding = result.get("input_render_ref")
        lines = result.get("lines")
        if result.get("format_version") != RESULT_FORMAT:
            raise MultibankAllLineRequestError(f"{label} is not an authenticated V3 page result")
        if (
            not isinstance(render_binding, dict)
            or render_binding.get("sha256") != render_ref["sha256"]
            or render_binding.get("size_bytes") != render_ref["size_bytes"]
        ):
            raise MultibankAllLineRequestError(f"{label} result/render binding is drifted")
        if not isinstance(lines, list):
            raise MultibankAllLineRequestError(f"{label} lines are invalid")
        if any(not isinstance(line, dict) for line in lines):
            raise MultibankAllLineRequestError(f"{label} contains a non-LINE record")
        validated.append((result, result_path, result_ref, render_path, render_ref))
    return validated


def build_request(*, input_spec_path: Path, output_root: Path) -> dict[str, Any]:
    if _git("status", "--porcelain"):
        raise MultibankAllLineRequestError("formal crop freeze requires a clean Git worktree")

    input_path = _resolve(input_spec_path, "batch input")
    destination = _resolve(output_root, "output root")
    if destination.exists():
        raise MultibankAllLineRequestError(f"refusing to overwrite output: {destination}")
    input_spec = _load_object(input_path, "batch input")
    pages = _validated_input_pages(input_spec)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        frozen = temporary / "frozen"
        temporary_crop_root = frozen / "crops"
        temporary_crop_root.mkdir(parents=True)
        final_crop_root = destination / "frozen" / "crops"
        page_records: list[dict[str, Any]] = []
        samples: list[dict[str, Any]] = []

        for page_ordinal, (result, _result_path, result_ref, render_path, render_ref) in enumerate(
            pages, start=1
        ):
            page_id = f"page-{page_ordinal:04d}"
            with Image.open(render_path) as source:
                source_rgb = source.convert("RGB")
                width, height = source_rgb.size
                lines = result["lines"]
                boxes = _line_boxes(lines, width=width, height=height)
                for line_index, source_box in enumerate(boxes):
                    sample_id = f"{page_id}-line-{line_index:04d}"
                    padded_box = _padded(source_box, width, height)
                    crop = ImageOps.expand(
                        source_rgb.crop(padded_box), border=WHITE_BORDER, fill="white"
                    )
                    temporary_crop = temporary_crop_root / f"{sample_id}.png"
                    crop.save(
                        temporary_crop,
                        format="PNG",
                        optimize=False,
                        compress_level=6,
                    )
                    final_crop = final_crop_root / temporary_crop.name
                    samples.append(
                        {
                            "category": "SOURCE_BOUND_AUTHENTICATED_LINE",
                            "crop_height": crop.height,
                            "crop_path": final_crop.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                            "crop_sha256": sha256_file(temporary_crop),
                            "crop_width": crop.width,
                            "grouping": "LINE",
                            "padded_source_bbox_raw_pixels": list(padded_box),
                            "page_id": page_id,
                            "sample_id": sample_id,
                            "source_bbox_raw_pixels": list(source_box),
                            "source_line_index": line_index,
                        }
                    )

            page_records.append(
                {
                    "authenticated_line_count": len(result["lines"]),
                    "page_id": page_id,
                    "render_height": height,
                    "render_ref": render_ref,
                    "render_width": width,
                    "result_ref": result_ref,
                    "selected_line_count": len(result["lines"]),
                }
            )

        commit = _git("rev-parse", "HEAD")
        manifest = {
            "authority": {
                "geometry_change": False,
                "numeric_value_period_unit_sign_scope_schema_authority": False,
                "semantic_acceptance": False,
            },
            "dataset_role": "DEVELOPMENT_REPLAY",
            "format_version": MANIFEST_FORMAT,
            "git_commit": commit,
            "git_dirty": False,
            "inference_firewall": {
                "bank_filename_physical_page_family_or_control_role_exposed_to_reader": False,
                "expected_labels_available_to_crop_selector": False,
                "ocr_transcript_field_consulted_by_crop_selector": False,
                "reader_receives_crop_pixels_only": True,
                "role_a_available_to_crop_selector": False,
            },
            "input_spec_ref": {
                "path": input_path.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                "sha256": sha256_file(input_path),
                "size_bytes": input_path.stat().st_size,
            },
            "page_count": len(page_records),
            "pages": page_records,
            "sample_count": len(samples),
            "samples": samples,
            "selection_rule": SELECTION_RULE,
            "state": "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE",
        }
        temporary_manifest = frozen / "crop_manifest.json"
        atomic_write_json(temporary_manifest, manifest)
        final_manifest = destination / "frozen" / "crop_manifest.json"

        # The reader sees only the generic benchmark identity, opaque sample IDs, and crops.
        # Source page/bank/family/control metadata stays outside its request boundary.
        request = {
            "crop_manifest": {
                "path": final_manifest.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                "sha256": sha256_file(temporary_manifest),
            },
            "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
            "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
            "experiment_id": "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1",
            "format_version": 2,
            "git_commit": commit,
            "git_dirty": False,
            "reference_text_available_to_reader": False,
            "sample_count": len(samples),
            "samples": [
                {
                    "category": sample["category"],
                    "crop_path": sample["crop_path"],
                    "crop_sha256": sample["crop_sha256"],
                    "sample_id": sample["sample_id"],
                }
                for sample in samples
            ],
            "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        }
        atomic_write_json(frozen / "reader_request.json", request)
        os.replace(temporary, destination)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

    return {
        "crop_manifest": (destination / "frozen" / "crop_manifest.json")
        .relative_to(PROJECT_ROOT.resolve())
        .as_posix(),
        "page_count": len(pages),
        "reader_request": (destination / "frozen" / "reader_request.json")
        .relative_to(PROJECT_ROOT.resolve())
        .as_posix(),
        "sample_count": sum(len(result["lines"]) for result, *_ in pages),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze every authenticated V3 LINE as an opaque VietOCR crop batch"
    )
    parser.add_argument("--input-spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_request(input_spec_path=args.input_spec, output_root=args.output_root),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
