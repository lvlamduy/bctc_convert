from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from bctc_ai.core.hashing import sha256_file
from bctc_ai.document_phase.statement_locator import OCRLine, OCRPage


class StatementEvidenceError(RuntimeError):
    pass


_SHA256 = re.compile(r"[0-9a-f]{64}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StatementEvidenceError(f"cannot load JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise StatementEvidenceError(f"JSON artifact is not an object: {path}")
    return payload


def _resolve(project_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise StatementEvidenceError("artifact path is absent or invalid")
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def _safe_batch_artifact(batch_root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise StatementEvidenceError(f"{label} path must be relative to the batch root")
    root = batch_root.resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise StatementEvidenceError(f"{label} path escapes or is absent from the batch root")
    return path


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise StatementEvidenceError(f"{label} is not a lowercase SHA-256 identity")
    return value


def _indexed_records(records: object, label: str) -> dict[int, dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise StatementEvidenceError(f"{label} contains no page records")
    indexed: dict[int, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or isinstance(record.get("page"), bool):
            raise StatementEvidenceError(f"{label} has an invalid page record")
        try:
            page = int(record["page"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StatementEvidenceError(f"{label} has an invalid page identity") from exc
        if page < 1 or page in indexed:
            raise StatementEvidenceError(f"{label} has duplicate/non-positive page {page}")
        indexed[page] = record
    return indexed


def load_ocr_pages_from_batch(
    batch_root: Path,
    *,
    project_root: Path,
) -> tuple[dict[str, Any], tuple[OCRPage, ...]]:
    batch_root = batch_root.resolve()
    batch_path = batch_root / "batch_manifest.json"
    batch = _load_json(batch_path)
    if batch.get("state") not in {"PARTIAL", "OCR_COMPLETE"}:
        raise StatementEvidenceError("batch did not reach a readable checkpoint state")
    batch_identity = _require_sha256(batch.get("batch_identity"), "batch identity")
    dataset_role = batch.get("dataset_role")
    if not isinstance(dataset_role, str) or not dataset_role:
        raise StatementEvidenceError("batch has no dataset role")
    source = batch.get("source")
    if not isinstance(source, dict):
        raise StatementEvidenceError("batch has no source identity")
    source_sha256 = _require_sha256(source.get("sha256"), "batch source hash")
    source_path = _resolve(project_root, source.get("path"))
    if (
        not source_path.is_relative_to(project_root.resolve())
        or not source_path.is_file()
        or sha256_file(source_path) != source_sha256
    ):
        raise StatementEvidenceError("batch source is absent, external, or hash-drifted")
    registration = batch.get("dataset_registration")
    if (
        not isinstance(registration, dict)
        or registration.get("immutable") is not True
        or registration.get("dataset_role") != dataset_role
        or registration.get("document_id") != f"sha256:{source_sha256}"
        or registration.get("source_path") != source.get("path")
    ):
        raise StatementEvidenceError("batch dataset-role registration identity drift")
    code = batch.get("code")
    if not isinstance(code, dict) or code.get("dirty") is not False:
        raise StatementEvidenceError("batch was not produced from clean code")
    requested_pages = batch.get("requested_pages")
    if (
        not isinstance(requested_pages, list)
        or not requested_pages
        or any(isinstance(page, bool) or not isinstance(page, int) for page in requested_pages)
        or requested_pages != sorted(set(requested_pages))
    ):
        raise StatementEvidenceError("batch requested-page identity is invalid")
    input_manifest = batch.get("input_manifest")
    if not isinstance(input_manifest, dict):
        raise StatementEvidenceError("batch has no preprocess-manifest identity")
    preprocess_sha256 = _require_sha256(input_manifest.get("sha256"), "preprocess manifest hash")
    preprocess_path = _resolve(project_root, input_manifest.get("path"))
    if (
        not preprocess_path.is_relative_to(project_root.resolve())
        or not preprocess_path.is_file()
        or sha256_file(preprocess_path) != preprocess_sha256
    ):
        raise StatementEvidenceError("preprocess manifest is absent or hash-drifted")
    preprocess = _load_json(preprocess_path)
    preprocess_code = preprocess.get("code")
    if (
        preprocess.get("state") != "PREPROCESSED"
        or preprocess.get("dataset_role") != dataset_role
        or preprocess.get("source_sha256") != source_sha256
        or not isinstance(preprocess_code, dict)
        or preprocess_code.get("git_dirty") is not False
    ):
        raise StatementEvidenceError("preprocess manifest state/role/source/code drift")
    preprocess_pages = _indexed_records(preprocess.get("pages"), "preprocess manifest")
    batch_renders = _indexed_records(batch.get("renders"), "batch render manifest")
    completed_records = _indexed_records(batch.get("pages"), "batch checkpoint")
    completed_pages = list(completed_records)
    if completed_pages != sorted(completed_pages) or any(
        page not in requested_pages for page in completed_pages
    ):
        raise StatementEvidenceError("batch completed-page identity is invalid")

    pages = []
    render_identity_keys = (
        "page",
        "sha256",
        "dpi",
        "rotation",
        "width_pixels",
        "height_pixels",
    )
    for page, raw_record in completed_records.items():
        run_manifest_record = raw_record.get("run_manifest")
        result_record = raw_record.get("ocr_result")
        if not isinstance(run_manifest_record, dict) or not isinstance(result_record, dict):
            raise StatementEvidenceError(f"batch page {page} has incomplete artifacts")
        run_manifest_path = _safe_batch_artifact(
            batch_root, run_manifest_record.get("path"), f"batch page {page} manifest"
        )
        result_path = _safe_batch_artifact(
            batch_root, result_record.get("path"), f"batch page {page} result"
        )
        if sha256_file(run_manifest_path) != _require_sha256(
            run_manifest_record.get("sha256"), f"batch page {page} manifest hash"
        ):
            raise StatementEvidenceError(f"batch page {page} manifest hash drift")
        result_sha256 = _require_sha256(
            result_record.get("sha256"), f"batch page {page} result hash"
        )
        if sha256_file(result_path) != result_sha256:
            raise StatementEvidenceError(f"batch page {page} result hash drift")
        run_manifest = _load_json(run_manifest_path)
        if (
            run_manifest.get("state") != "OCR_COMPLETE"
            or run_manifest.get("batch_identity") != batch_identity
            or run_manifest.get("page") != page
            or run_manifest.get("dataset_role") != dataset_role
        ):
            raise StatementEvidenceError(f"batch page {page} identity drift")
        run_artifacts = run_manifest.get("artifacts")
        run_result = run_artifacts.get("ocr_result") if isinstance(run_artifacts, dict) else None
        if not isinstance(run_result, dict) or run_result.get("sha256") != result_sha256:
            raise StatementEvidenceError(f"batch page {page} result identity drift")
        run_result_path = _safe_batch_artifact(
            run_manifest_path.parent,
            run_result.get("path"),
            f"batch page {page} run-result",
        )
        if run_result_path != result_path:
            raise StatementEvidenceError(f"batch page {page} result path drift")

        preprocess_page = preprocess_pages.get(page)
        preprocess_render = (
            preprocess_page.get("render") if isinstance(preprocess_page, dict) else None
        )
        batch_render = batch_renders.get(page)
        run_render = run_manifest.get("input")
        if not all(
            isinstance(record, dict) for record in (preprocess_render, batch_render, run_render)
        ):
            raise StatementEvidenceError(f"batch page {page} has incomplete render identity")
        for key in render_identity_keys:
            if not (preprocess_render.get(key) == batch_render.get(key) == run_render.get(key)):
                raise StatementEvidenceError(f"batch page {page} render identity drift at {key}")
        render_sha256 = _require_sha256(
            batch_render.get("sha256"), f"batch page {page} render hash"
        )
        render_path = _resolve(project_root, batch_render.get("path"))
        preprocess_render_path = _resolve(project_root, preprocess_render.get("path"))
        if (
            not render_path.is_relative_to(project_root.resolve())
            or not render_path.is_file()
            or sha256_file(render_path) != render_sha256
        ):
            raise StatementEvidenceError(f"batch page {page} render path/hash drift")
        if (
            preprocess_render_path.is_file()
            and sha256_file(preprocess_render_path) != render_sha256
        ):
            raise StatementEvidenceError(
                f"batch page {page} stale preprocess render path has different content"
            )

        result = _load_json(result_path)
        texts = result.get("rec_texts")
        boxes = result.get("rec_boxes")
        scores = result.get("rec_scores")
        if (
            not isinstance(texts, list)
            or not isinstance(boxes, list)
            or not isinstance(scores, list)
            or len({len(texts), len(boxes), len(scores)}) != 1
        ):
            raise StatementEvidenceError(f"batch page {page} OCR axes are invalid")
        lines = []
        for text, box, score in zip(texts, boxes, scores, strict=True):
            if not isinstance(text, str) or not isinstance(box, list) or len(box) != 4:
                raise StatementEvidenceError(f"batch page {page} has an invalid line box")
            try:
                coordinates = tuple(float(value) for value in box)
                score_value = float(score)
            except (TypeError, ValueError) as exc:
                raise StatementEvidenceError(
                    f"batch page {page} has non-numeric OCR geometry/confidence"
                ) from exc
            x0, y0, x1, y1 = coordinates
            if (
                not all(math.isfinite(value) for value in (*coordinates, score_value))
                or not 0 <= x0 <= x1 <= int(batch_render["width_pixels"])
                or not 0 <= y0 <= y1 <= int(batch_render["height_pixels"])
                or not 0 <= score_value <= 1
            ):
                raise StatementEvidenceError(
                    f"batch page {page} has out-of-bounds OCR geometry/confidence"
                )
            lines.append(OCRLine(text=text, bbox=coordinates, score=score_value))
        pages.append(
            OCRPage(
                page=page,
                width=int(batch_render["width_pixels"]),
                height=int(batch_render["height_pixels"]),
                lines=tuple(lines),
            )
        )
    return batch, tuple(pages)
