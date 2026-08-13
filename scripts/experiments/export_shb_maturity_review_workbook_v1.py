#!/usr/bin/env python3
"""Build the exact deterministic SHB page-24 review-only workbook pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from bctc_ai.export.shb_maturity_review_workbook_v1 import (
    E0042_RELATIVE_PATH,
    build_shb_maturity_review_workbook_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    build_semantic_local_accounting_schema_candidate_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    build_semantic_local_accounting_graph_v2,
)
from bctc_ai.source_structure.semantic_statement_context_v1 import (
    build_semantic_statement_context_v1,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    bind_vietocr_semantic_page_v2,
    validate_vietocr_semantic_receipt_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIRECTORY = Path("output/development/e0042-shb-maturity-review-workbook-v1")
WORKBOOK_NAME = "shb-maturity-review-only.xlsx"
PROVENANCE_NAME = "provenance.json"

_RUN_ROOT = Path("output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run")
_MANIFEST = _RUN_ROOT / "frozen/crop_manifest.json"
_REQUEST = _RUN_ROOT / "frozen/reader_request.json"
_RESULT = _RUN_ROOT / "outputs/vgg-transformer/ocr_result.json"
_RUN = _RUN_ROOT / "outputs/vgg-transformer/run_manifest.json"
_RESULT_SHA256 = "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
_RUN_SHA256 = "6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7"
_SHB_RESULT_SHA256 = "f66ec66cf70b85c07c877881daf7d207dec7b754efbcafc1c88507962b77a82b"
_SHB_RESULT = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/"
    "sha256/f6/f66ec66cf70b85c07c877881daf7d207dec7b754efbcafc1c88507962b77a82b.json"
)
_SHB_DOCUMENT_SHA256 = "ce257a25bb96b8d05f2437edc85dc3c7dcdd815d25551f7c731d60bd40058dd8"
_SHB_DOCUMENT = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/documents/"
    "3a66122194e4dd2e0ca18d584beeacb81279cf71e276eface59d17e72813dcfd.json"
)
_SHB_PAGE_RECORD_INDEX = 23
_SPECS = (LOAN_QUALITY_CLASSIFICATION_SPEC_V1, LOAN_MATURITY_BUCKETS_SPEC_V1)


def _read_exact_json(relative: Path, expected_sha256: str) -> dict:
    payload = (PROJECT_ROOT / relative).read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise RuntimeError(f"exact input hash drifted: {relative}")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError(f"exact input is not one JSON object: {relative}")
    return value


def _build_exact_inputs() -> tuple[dict, dict]:
    receipt = validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        _MANIFEST,
        _REQUEST,
        _RESULT,
        _RUN,
        expected_ocr_result_sha256=_RESULT_SHA256,
        expected_run_manifest_sha256=_RUN_SHA256,
    )
    manifest = json.loads((PROJECT_ROOT / _MANIFEST).read_bytes())
    page = manifest["pages"][0]
    if page["result_ref"]["sha256"] != _SHB_RESULT_SHA256:
        raise RuntimeError("frozen Transformer receipt first page is not exact SHB page 24")
    document = _read_exact_json(_SHB_DOCUMENT, _SHB_DOCUMENT_SHA256)
    page_result = _read_exact_json(_SHB_RESULT, _SHB_RESULT_SHA256)
    projection = project_authenticated_page_v2(
        page_record=document["page_records"][_SHB_PAGE_RECORD_INDEX],
        page_result=page_result,
    )
    binding = bind_vietocr_semantic_page_v2(projection, receipt)
    graph = build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        _SPECS,
    )
    candidate = build_semantic_local_accounting_schema_candidate_v1(
        PROJECT_ROOT,
        graph,
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        _SPECS,
    )
    context = build_semantic_statement_context_v1(projection, binding, receipt)
    return candidate, context


def _publish(output_directory: Path, workbook: bytes, provenance: bytes) -> tuple[Path, Path]:
    if output_directory.exists():
        raise RuntimeError(f"refusing to overwrite review output directory: {output_directory}")
    output_directory.mkdir(parents=True, exist_ok=False)
    workbook_path = output_directory / WORKBOOK_NAME
    provenance_path = output_directory / PROVENANCE_NAME
    created: list[Path] = []
    try:
        with provenance_path.open("xb") as stream:
            stream.write(provenance)
        created.append(provenance_path)
        with workbook_path.open("xb") as stream:
            stream.write(workbook)
        created.append(workbook_path)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        output_directory.rmdir()
        raise
    return workbook_path, provenance_path


def _safe_project_output_directory(value: Path) -> Path:
    raw = value
    if not raw.parts or ".." in raw.parts:
        raise RuntimeError("output directory must not contain parent traversal")
    if raw.is_absolute():
        candidate = raw
    else:
        candidate = PROJECT_ROOT / raw
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise RuntimeError("output directory must remain inside the project root") from exc
    current = PROJECT_ROOT
    for part in candidate.relative_to(PROJECT_ROOT).parts:
        current = current / part
        try:
            status = os.stat(current, follow_symlinks=False)
        except FileNotFoundError:
            break
        if not stat.S_ISDIR(status.st_mode):
            raise RuntimeError(f"output ancestor is not a real directory: {current}")
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="new project-relative or absolute directory; overwrite is refused",
    )
    arguments = parser.parse_args(argv)
    output_directory = _safe_project_output_directory(arguments.output_directory)
    candidate, context = _build_exact_inputs()
    verification_bytes = (PROJECT_ROOT / E0042_RELATIVE_PATH).read_bytes()
    artifacts = build_shb_maturity_review_workbook_v1(
        candidate,
        context,
        verification_bytes,
    )
    workbook_path, provenance_path = _publish(
        output_directory,
        artifacts.workbook_bytes,
        artifacts.provenance_bytes,
    )
    summary = {
        "artifact_role": "REVIEW_ONLY_NON_CANONICAL_NON_EXPORT_AUTHORITY",
        "workbook": {
            "path": workbook_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": artifacts.workbook_sha256,
            "size_bytes": len(artifacts.workbook_bytes),
        },
        "provenance": {
            "path": provenance_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": artifacts.provenance_sha256,
            "size_bytes": len(artifacts.provenance_bytes),
        },
        "projection_sha256": artifacts.projection_sha256,
    }
    sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
