from __future__ import annotations

import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.contracts import DatasetRole
from bctc_ai.core.environment import collect_environment
from bctc_ai.core.hashing import sha256_file, source_tree_hash, stable_records_hash
from bctc_ai.ingestion.dataset_roles import assign_dataset_role
from bctc_ai.preprocessing.quality import assess_image
from bctc_ai.preprocessing.variants import (
    generate_difficult_region_variants,
    generate_variants,
)
from bctc_ai.rendering.pdf import inspect_pdf, render_pages
from bctc_ai.storage.content_store import materialize_immutable


def _git(root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def preprocess_document(
    project_root: Path,
    source: Path,
    *,
    run_id: str,
    dataset_role: str,
    dpi: int = 300,
    page_numbers: set[int] | None = None,
) -> Path:
    started_at = datetime.now(UTC).isoformat()
    project_root = project_root.resolve()
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_hash = sha256_file(source)
    document_id = source_hash[:20]
    role = DatasetRole(dataset_role)
    source_relative = (
        source.relative_to(project_root).as_posix()
        if project_root in source.parents
        else str(source)
    )
    assign_dataset_role(
        project_root / "data" / "registered" / "dataset_roles.jsonl",
        document_id=f"sha256:{source_hash}",
        role=role,
        source_path=source_relative,
    )
    immutable_source = None
    processing_source = source
    if role in {DatasetRole.UNTOUCHED_HOLDOUT, DatasetRole.PRODUCTION_INPUT}:
        immutable_source, immutable_hash = materialize_immutable(
            source, project_root / "data" / "immutable"
        )
        if immutable_hash != source_hash:
            raise RuntimeError("immutable source hash mismatch")
        processing_source = immutable_source
    role_directory = {
        "LOGIC_DEVELOPMENT": "development",
        "CALIBRATION": "calibration",
        "UNTOUCHED_HOLDOUT": "holdout",
        "VALIDATION": "validation",
        "PRODUCTION_INPUT": "production",
    }[dataset_role]
    run_root = project_root / "output" / role_directory / run_id / document_id
    for name in (
        "logs",
        "source",
        "renders",
        "preprocess",
        "ocr",
        "layout",
        "tables",
        "rows",
        "axes",
        "mapping",
        "validation",
        "review",
        "questions",
        "workbooks",
        "experiments",
    ):
        (run_root / name).mkdir(parents=True, exist_ok=True)

    inspection = inspect_pdf(processing_source)
    atomic_write_json(run_root / "source" / "inspection.json", inspection.to_dict())
    rendered = render_pages(
        processing_source, run_root / "renders", dpi=dpi, page_numbers=page_numbers
    )
    page_results = []
    for render in rendered:
        render_path = Path(render.path)
        quality = assess_image(render_path)
        page_directory = run_root / "preprocess" / f"page-{render.page:04d}"
        variants = generate_variants(render_path, page_directory, quality)
        region_variants = generate_difficult_region_variants(
            render_path, page_directory / "regions", quality.difficult_regions
        )
        page_results.append(
            {
                "page": render.page,
                "render": asdict(render),
                "quality": quality.to_dict(),
                "variants": [asdict(variant) for variant in variants],
                "region_variants": [asdict(variant) for variant in region_variants],
            }
        )
    artifact_records = []
    for artifact in sorted((run_root / "renders").rglob("*")) + sorted(
        (run_root / "preprocess").rglob("*")
    ):
        if artifact.is_file():
            artifact_records.append(
                f"{sha256_file(artifact)}  {artifact.relative_to(run_root).as_posix()}"
            )
    manifest = {
        "format_version": 1,
        "run_id": run_id,
        "document_id": document_id,
        "dataset_role": dataset_role,
        "state": "PREPROCESSED",
        "source": source_relative,
        "source_sha256": source_hash,
        "immutable_source": str(immutable_source) if immutable_source else None,
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": bool(_git(project_root, "status", "--porcelain")),
        },
        "code_sha256": source_tree_hash(project_root / "src"),
        "config_sha256": source_tree_hash(project_root / "config"),
        "models": [],
        "environment": collect_environment(project_root),
        "output_artifacts_sha256": stable_records_hash(artifact_records),
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "pages": page_results,
        "errors": [],
    }
    atomic_write_json(run_root / "manifest.json", manifest)
    # Ensure the manifest itself can be independently identified without a
    # self-referential output hash field.
    atomic_write_json(
        run_root / "run_manifest.json",
        {
            "manifest": "manifest.json",
            "manifest_sha256": sha256_file(run_root / "manifest.json"),
            "source_sha256": source_hash,
            "state": "PREPROCESSED",
        },
    )
    return run_root
