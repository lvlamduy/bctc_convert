from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.core.atomic import atomic_write_json  # noqa: E402
from bctc_ai.core.hashing import sha256_file  # noqa: E402


class SourceOnlyLabelLaneRequestError(RuntimeError):
    pass


SELECTION_RULE = {
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


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(path: Path, label: str) -> Path:
    resolved = path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise SourceOnlyLabelLaneRequestError(f"{label} escapes project root")
    return resolved


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceOnlyLabelLaneRequestError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise SourceOnlyLabelLaneRequestError(f"{label} must be a JSON object")
    return value


def _bbox(raw: Any, *, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(raw, list) or len(raw) != 4 or any(type(value) is not int for value in raw):
        raise SourceOnlyLabelLaneRequestError("V3 line bbox is invalid")
    x0, y0, x1, y1 = raw
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise SourceOnlyLabelLaneRequestError("V3 line bbox lies outside the render")
    return x0, y0, x1, y1


def _selected(box: tuple[int, int, int, int], width: int, height: int) -> bool:
    x0, y0, x1, y1 = box
    return (
        4 * x0 <= width
        and 20 * x1 <= 13 * width
        and 8 <= y1 - y0
        and 100 * (y1 - y0) <= 6 * height
        and 100 * y0 >= 3 * height
        and 100 * y1 <= 97 * height
    )


def _envelope(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _padded(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    return max(0, box[0] - 8), max(0, box[1] - 4), min(width, box[2] + 8), min(height, box[3] + 4)


def build_request(*, render_path: Path, result_path: Path, output_root: Path) -> dict[str, Any]:
    if _git("status", "--porcelain"):
        raise SourceOnlyLabelLaneRequestError("formal crop freeze requires a clean Git worktree")
    render = _resolve(render_path, "render")
    result_file = _resolve(result_path, "V3 page result")
    destination = _resolve(output_root, "output root")
    if destination.exists():
        raise SourceOnlyLabelLaneRequestError(f"refusing to overwrite output: {destination}")
    if not render.is_file() or not result_file.is_file():
        raise SourceOnlyLabelLaneRequestError("render or V3 page result is missing")
    result = _load_object(result_file, "V3 page result")
    if result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2":
        raise SourceOnlyLabelLaneRequestError("input is not an authenticated V3 page result")
    render_ref = result.get("input_render_ref")
    lines = result.get("lines")
    if (
        not isinstance(render_ref, dict)
        or render_ref.get("sha256") != sha256_file(render)
        or not isinstance(lines, list)
    ):
        raise SourceOnlyLabelLaneRequestError("V3 result/render binding is absent or drifted")

    with Image.open(render) as source:
        source_rgb = source.convert("RGB")
        width, height = source_rgb.size
        boxes = [_bbox(line.get("raw_pixel_bbox"), width=width, height=height) for line in lines]
        selected_indices = [
            index for index, box in enumerate(boxes) if _selected(box, width, height)
        ]
        union_pairs = [
            (prior, following)
            for prior, following in zip(selected_indices, selected_indices[1:], strict=False)
            if -2 <= boxes[following][1] - boxes[prior][3] <= 0
            and 50 * abs(boxes[following][0] - boxes[prior][0]) <= width
        ]
        sample_specs = [
            (f"page-0001-line-{index:03d}", "LINE", [index]) for index in selected_indices
        ] + [
            (
                f"page-0001-union-{prior:03d}-{following:03d}",
                "STRICT_ADJACENT_UNION",
                [prior, following],
            )
            for prior, following in union_pairs
        ]

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
        try:
            frozen = temporary / "frozen"
            crop_root = frozen / "crops"
            crop_root.mkdir(parents=True)
            samples: list[dict[str, Any]] = []
            final_crop_root = destination / "frozen" / "crops"
            for sample_id, grouping, indices in sample_specs:
                source_box = _envelope([boxes[index] for index in indices])
                padded_box = _padded(source_box, width, height)
                crop = ImageOps.expand(
                    source_rgb.crop(padded_box), border=(12, 8, 12, 8), fill="white"
                )
                temporary_crop = crop_root / f"{sample_id}.png"
                crop.save(temporary_crop, format="PNG", optimize=False)
                final_crop = final_crop_root / temporary_crop.name
                samples.append(
                    {
                        "category": "SOURCE_BOUND_LABEL_LANE_CANDIDATE",
                        "crop_height": crop.height,
                        "crop_path": final_crop.relative_to(PROJECT_ROOT).as_posix(),
                        "crop_sha256": sha256_file(temporary_crop),
                        "crop_width": crop.width,
                        "grouping": grouping,
                        "padded_source_bbox_raw_pixels": list(padded_box),
                        "page_id": "page-0001",
                        "sample_id": sample_id,
                        "source_bbox_raw_pixels": list(source_box),
                        "source_line_indices": indices,
                    }
                )

            commit = _git("rev-parse", "HEAD")
            relative_render = render.relative_to(PROJECT_ROOT).as_posix()
            relative_result = result_file.relative_to(PROJECT_ROOT).as_posix()
            manifest = {
                "authority": {
                    "geometry_change": False,
                    "numeric_value_period_unit_sign_scope_schema_authority": False,
                    "semantic_acceptance": False,
                },
                "dataset_role": "DEVELOPMENT_REPLAY",
                "format_version": "LAG_V1_SOURCE_ONLY_SEMANTIC_CANARY_CROP_MANIFEST_V1",
                "git_commit": commit,
                "git_dirty": False,
                "inference_firewall": {
                    "bank_filename_physical_page_family_or_control_role_exposed_to_reader": False,
                    "expected_labels_available_to_crop_selector": False,
                    "ocr_raw_text_read_by_crop_selector": False,
                    "reader_receives_crop_pixels_only": True,
                    "role_a_available_to_crop_selector": False,
                },
                "page_count": 1,
                "pages": [
                    {
                        "authenticated_line_count": len(lines),
                        "page_id": "page-0001",
                        "render_height": height,
                        "render_path": relative_render,
                        "render_sha256": sha256_file(render),
                        "render_width": width,
                        "result_path": relative_result,
                        "result_sha256": sha256_file(result_file),
                        "selected_single_line_count": len(selected_indices),
                        "selected_strict_union_count": len(union_pairs),
                    }
                ],
                "sample_count": len(samples),
                "samples": samples,
                "selection_rule": SELECTION_RULE,
                "state": "FROZEN_BEFORE_ANY_SEMANTIC_MODEL_INFERENCE",
            }
            temporary_manifest = frozen / "crop_manifest.json"
            atomic_write_json(temporary_manifest, manifest)
            final_manifest = destination / "frozen" / "crop_manifest.json"
            request = {
                "crop_manifest": {
                    "path": final_manifest.relative_to(PROJECT_ROOT).as_posix(),
                    "sha256": sha256_file(temporary_manifest),
                },
                "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
                "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
                "experiment_id": "E-0024",
                "format_version": 1,
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
        .relative_to(PROJECT_ROOT)
        .as_posix(),
        "reader_request": (destination / "frozen" / "reader_request.json")
        .relative_to(PROJECT_ROOT)
        .as_posix(),
        "single_line_sample_count": len(selected_indices),
        "strict_union_sample_count": len(union_pairs),
        "sample_count": len(sample_specs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze text-blind V3 label-lane crops and a semantic-reader request"
    )
    parser.add_argument("--render", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build_request(
                render_path=args.render,
                result_path=args.result,
                output_root=args.output_root,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
