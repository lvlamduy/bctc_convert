#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.numeric_cell_crops import (
    NumericCellCropError,
    build_numeric_cell_crop_registry,
    load_numeric_cell_crop_policy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _project_path(value: Path, name: str) -> Path:
    path = (PROJECT_ROOT / value).resolve() if not value.is_absolute() else value.resolve()
    if not path.is_relative_to(PROJECT_ROOT):
        raise NumericCellCropError(f"{name} escapes project root")
    return path


def _load_json(path: Path, name: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NumericCellCropError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise NumericCellCropError(f"{name} must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build reference-blind fixed-grid numeric-cell crops"
    )
    parser.add_argument("--row-contract", type=Path, required=True)
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("config/tables/numeric-cell-crops-v1.yaml"),
    )
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    if _git("status", "--porcelain") and not args.allow_dirty:
        raise NumericCellCropError("refusing numeric-cell crops from a dirty worktree")
    row_contract = _project_path(args.row_contract, "row contract")
    batch_root = _project_path(args.batch_root, "OCR batch root")
    batch_path = batch_root / "batch_manifest.json"
    batch = _load_json(batch_path, "OCR batch manifest")
    contract = _load_json(row_contract, "row contract")
    target_pages = [int(record["page"]) for record in contract.get("after", [])]
    if not target_pages or len(target_pages) != len(set(target_pages)):
        raise NumericCellCropError("row contract must contain unique target pages")

    page_records = {
        int(record["page"]): record
        for record in batch.get("pages", [])
        if int(record.get("page", -1)) in target_pages
    }
    render_records = {
        int(record["page"]): record
        for record in batch.get("renders", [])
        if int(record.get("page", -1)) in target_pages
    }
    if set(page_records) != set(target_pages) or set(render_records) != set(target_pages):
        raise NumericCellCropError("OCR batch does not contain the exact target pages")

    ocr_paths: dict[int, Path] = {}
    render_paths: dict[int, Path] = {}
    for page in target_pages:
        ocr_record = page_records[page]["ocr_result"]
        ocr_path = (batch_root / str(ocr_record["path"])).resolve()
        render_path = _project_path(Path(render_records[page]["path"]), "render")
        for path, record in ((ocr_path, ocr_record), (render_path, render_records[page])):
            if (
                not path.is_file()
                or path.stat().st_size != int(record["size_bytes"])
                or sha256_file(path) != record["sha256"]
            ):
                raise NumericCellCropError(f"source artifact drifted: {path}")
        ocr_paths[page] = ocr_path
        render_paths[page] = render_path

    output = _project_path(args.output_directory, "numeric crop output")
    registry = build_numeric_cell_crop_registry(
        row_contract_path=row_contract,
        ocr_paths_by_page=ocr_paths,
        render_paths_by_page=render_paths,
        output_directory=output,
        policy=load_numeric_cell_crop_policy(_project_path(args.policy, "crop policy")),
    )
    print(json.dumps(registry["metrics"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
