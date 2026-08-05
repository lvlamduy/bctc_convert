from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    validate_evidence_manifest,
)


class RoleBSealError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RoleBSealError(f"required artifact is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RoleBSealError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise RoleBSealError(f"JSON artifact is not an object: {path}")
    return value


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise RoleBSealError(f"artifact escapes project root: {path}") from exc


def _verify_model_artifacts(
    project_root: Path, model_cache_root: Path, runtime_path: Path
) -> list[dict[str, object]]:
    runtime = tomllib.loads(runtime_path.read_text(encoding="utf-8"))
    models = runtime.get("models")
    if not isinstance(models, dict) or not models:
        raise RoleBSealError("GPU runtime manifest contains no model records")
    records = []
    for model_key, raw_model in sorted(models.items()):
        if not isinstance(raw_model, dict):
            raise RoleBSealError(f"invalid model record: {model_key}")
        weights = (
            model_cache_root
            / "official_models"
            / str(raw_model["cache_directory"])
            / str(raw_model["weights_file"])
        )
        expected_size = int(raw_model["weights_size_bytes"])
        expected_digest = str(raw_model["weights_sha256"])
        if not weights.is_file() or weights.stat().st_size != expected_size:
            raise RoleBSealError(f"model weights are absent or size-drifted: {weights}")
        actual_digest = sha256_file(weights)
        if actual_digest != expected_digest:
            raise RoleBSealError(f"model weights hash drift: {weights}")
        records.append(
            {
                "model_key": model_key,
                "repo_id": raw_model["repo_id"],
                "revision": raw_model["revision"],
                "weights_path": weights.as_posix(),
                "weights_size_bytes": expected_size,
                "weights_sha256": actual_digest,
            }
        )
    return records


def seal_role_b_ocr_run(
    project_root: Path,
    run_root: Path,
    *,
    pages: tuple[int, ...],
    model_cache_root: Path,
    runtime_manifest: Path = Path("config/models/gpu-runtime.toml"),
    inference_config: Path = Path("config/models/paddleocr-vl-1.6-transformers.yaml"),
    package_freeze: Path = Path("config/models/gpu-requirements.freeze.txt"),
    seal_name: str = "role_b_ocr_seal.json",
    seal_implementation_path: Path | None = None,
) -> dict[str, object]:
    project_root = project_root.resolve()
    run_root = run_root.resolve()
    if not pages or tuple(sorted(set(pages))) != pages or min(pages) < 1:
        raise RoleBSealError("pages must be sorted unique positive integers")
    try:
        run_root.relative_to(project_root / "output")
    except ValueError as exc:
        raise RoleBSealError("Role B run must be inside the project output directory") from exc
    seal_path = run_root / seal_name
    if seal_path.exists():
        raise RoleBSealError(f"refusing to overwrite an existing Role B seal: {seal_path}")

    preprocess_manifest_path = run_root / "manifest.json"
    preprocess_manifest = _load_json(preprocess_manifest_path)
    if preprocess_manifest.get("dataset_role") not in {
        "CALIBRATION",
        "VALIDATION",
        "UNTOUCHED_HOLDOUT",
    }:
        raise RoleBSealError("Role B benchmark run has an invalid dataset role")
    if preprocess_manifest.get("state") != "PREPROCESSED":
        raise RoleBSealError("Role B run did not reach PREPROCESSED")
    code = preprocess_manifest.get("code")
    if not isinstance(code, dict) or code.get("git_dirty") is not False:
        raise RoleBSealError("Role B preprocessing did not start from a clean Git state")
    raw_pages = preprocess_manifest.get("pages")
    if not isinstance(raw_pages, list):
        raise RoleBSealError("preprocess manifest contains no pages")
    page_manifests = {
        int(record["page"]): record for record in raw_pages if isinstance(record, dict)
    }
    if any(page not in page_manifests for page in pages):
        raise RoleBSealError("one or more requested pages were not preprocessed")

    runtime_path = (project_root / runtime_manifest).resolve()
    inference_path = (project_root / inference_config).resolve()
    freeze_path = (project_root / package_freeze).resolve()
    for path in (runtime_path, inference_path, freeze_path):
        if not path.is_file():
            raise RoleBSealError(f"runtime artifact is missing: {path}")
    runtime = tomllib.loads(runtime_path.read_text(encoding="utf-8"))
    if sha256_file(freeze_path) != runtime.get("freeze_sha256"):
        raise RoleBSealError("package freeze hash does not match GPU runtime manifest")
    models = _verify_model_artifacts(project_root, model_cache_root.resolve(), runtime_path)

    evidence = (
        EvidenceItem(
            EvidenceKind.ROLE_B_SOURCE_PDF,
            str(preprocess_manifest.get("source", "")),
            str(preprocess_manifest.get("source_sha256", "")),
        ),
        EvidenceItem(
            EvidenceKind.CONFIG,
            _relative(inference_path, project_root),
            sha256_file(inference_path),
        ),
        *(EvidenceItem(EvidenceKind.MODEL, str(model["repo_id"])) for model in models),
    )
    validate_evidence_manifest(EvidenceStage.ROLE_B_READ, evidence)

    page_records = []
    artifact_lines: list[str] = []
    wall_seconds = 0.0
    peak_memory_mib = 0.0
    for page in pages:
        page_code = f"{page:04d}"
        render_record = page_manifests[page].get("render")
        if not isinstance(render_record, dict):
            raise RoleBSealError(f"page {page} has no render record")
        render_path = Path(str(render_record["path"]))
        if not render_path.is_absolute():
            render_path = project_root / render_path
        if not render_path.is_file() or sha256_file(render_path) != render_record.get("sha256"):
            raise RoleBSealError(f"page {page} render is absent or hash-drifted")

        metric_path = run_root / "experiments" / f"paddleocr-vl-page-{page_code}-metrics.json"
        result_directory = run_root / "ocr" / f"paddleocr-vl-page-{page_code}"
        result_path = result_directory / f"page-{page_code}_res.json"
        metric = _load_json(metric_path)
        result = _load_json(result_path)
        if metric.get("status") != "PASS" or metric.get("return_code") != 0:
            raise RoleBSealError(f"page {page} inference metrics did not pass")
        input_path = Path(str(result.get("input_path", "")))
        if not input_path.is_absolute():
            input_path = project_root / input_path
        if input_path.resolve() != render_path.resolve():
            raise RoleBSealError(f"page {page} model input differs from the registered render")
        output_files = sorted(path for path in result_directory.rglob("*") if path.is_file())
        if not output_files:
            raise RoleBSealError(f"page {page} has no OCR output files")
        output_records = []
        for path in output_files:
            relative_path = _relative(path, project_root)
            digest = sha256_file(path)
            artifact_lines.append(f"{digest}  {relative_path}")
            output_records.append(
                {"path": relative_path, "size_bytes": path.stat().st_size, "sha256": digest}
            )
        render_relative = _relative(render_path, project_root)
        render_digest = sha256_file(render_path)
        metric_relative = _relative(metric_path, project_root)
        metric_digest = sha256_file(metric_path)
        artifact_lines.extend(
            (f"{render_digest}  {render_relative}", f"{metric_digest}  {metric_relative}")
        )
        wall_seconds += float(metric["wall_seconds"])
        gpu = metric.get("gpu")
        if not isinstance(gpu, dict):
            raise RoleBSealError(f"page {page} metrics contain no GPU record")
        peak_memory_mib = max(peak_memory_mib, float(gpu["peak_memory_used_mib"]))
        page_records.append(
            {
                "page": page,
                "render": {
                    "path": render_relative,
                    "sha256": render_digest,
                    "dpi": render_record["dpi"],
                    "rotation": render_record["rotation"],
                },
                "metrics": {
                    "path": metric_relative,
                    "sha256": metric_digest,
                    "wall_seconds": metric["wall_seconds"],
                    "peak_memory_used_mib": gpu["peak_memory_used_mib"],
                },
                "outputs": output_records,
            }
        )

    implementation_path = (seal_implementation_path or Path(__file__)).resolve()
    if not implementation_path.is_file():
        raise RoleBSealError(f"seal implementation is missing: {implementation_path}")
    payload: dict[str, object] = {
        "format_version": 1,
        "state": "OCR_COMPLETE",
        "sealed_at": datetime.now(UTC).isoformat(),
        "run_root": _relative(run_root, project_root),
        "dataset_role": preprocess_manifest["dataset_role"],
        "source": preprocess_manifest["source"],
        "source_sha256": preprocess_manifest["source_sha256"],
        "inference_code": code,
        "preprocess_manifest": {
            "path": _relative(preprocess_manifest_path, project_root),
            "sha256": sha256_file(preprocess_manifest_path),
        },
        "runtime": {
            "manifest_path": _relative(runtime_path, project_root),
            "manifest_sha256": sha256_file(runtime_path),
            "inference_config_path": _relative(inference_path, project_root),
            "inference_config_sha256": sha256_file(inference_path),
            "package_freeze_path": _relative(freeze_path, project_root),
            "package_freeze_sha256": sha256_file(freeze_path),
            "models": models,
        },
        "evidence_stage": EvidenceStage.ROLE_B_READ.value,
        "evidence_manifest": [
            {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}
            for item in evidence
        ],
        "pages": page_records,
        "metrics": {
            "page_count": len(page_records),
            "total_wall_seconds_sequential_processes": round(wall_seconds, 6),
            "peak_memory_used_mib": peak_memory_mib,
        },
        "artifact_set_sha256": stable_records_hash(sorted(artifact_lines)),
        "seal_implementation": {
            "path": _relative(implementation_path, project_root),
            "sha256": sha256_file(implementation_path),
        },
        "claim_boundary": (
            "This seal proves Role B input/output identity and runtime completion only; "
            "it is not an accuracy result."
        ),
    }
    atomic_write_json(seal_path, payload)
    payload["seal_path"] = _relative(seal_path, project_root)
    payload["seal_sha256"] = sha256_file(seal_path)
    return payload
