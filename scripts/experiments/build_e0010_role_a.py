from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

from bctc_ai.axes.header_binding import bind_value_headers
from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    load_frozen_suite,
    validate_evidence_manifest,
)
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.ocr.pdf_text import extract_pdf_text
from bctc_ai.rows.pdf_statement import reconstruct_statement_rows
from bctc_ai.tables.geometry import analyze_page_geometry, load_geometry_config
from bctc_ai.validation.reader_agreement import ReaderRow


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and seal E-0010 Role A native reference")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--suite-config",
        type=Path,
        default=Path("config/experiments/e0009-frozen-paired-calibration.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/calibration/e0010-tcb-role-a"),
    )
    return parser.parse_args()


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _box(value) -> dict[str, float] | None:
    return asdict(value) if value is not None else None


def _date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _financial_span(rows):
    substantive = [index for index, row in enumerate(rows) if row.cells]
    if not substantive:
        return []
    start, end = substantive[0], substantive[-1]
    if start > 0 and not rows[start - 1].cells:
        start -= 1
    return rows[start : end + 1]


def main() -> int:
    args = _parse_args()
    project_root = args.project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise RuntimeError("Role A must start from a clean Git worktree")
    suite_config = (project_root / args.suite_config).resolve()
    suite = load_frozen_suite(project_root, suite_config)
    reference = suite.source(str(suite.pairing["reference_fixture_id"]))
    source_path = project_root / reference.path
    geometry_config_path = project_root / "config/tables/geometry.yaml"
    geometry_config = load_geometry_config(geometry_config_path)
    output_root = (project_root / args.output_root / reference.sha256[:20]).resolve()
    result_path = output_root / "role_a_rows.json"
    seal_path = output_root / "role_a_seal.json"
    if result_path.exists() or seal_path.exists():
        raise RuntimeError(f"refusing to overwrite existing Role A output: {output_root}")

    evidence = (
        EvidenceItem(EvidenceKind.ROLE_A_SOURCE_PDF, reference.path, reference.sha256),
        EvidenceItem(
            EvidenceKind.CONFIG,
            suite_config.relative_to(project_root).as_posix(),
            sha256_file(suite_config),
        ),
        EvidenceItem(
            EvidenceKind.CONFIG,
            geometry_config_path.relative_to(project_root).as_posix(),
            sha256_file(geometry_config_path),
        ),
    )
    validate_evidence_manifest(EvidenceStage.ROLE_A_BUILD, evidence)
    contracts = suite.pairing["target_page_contracts"]
    reference_pages = {int(contract["reference_page"]) for contract in contracts}
    extracted = {page.page: page for page in extract_pdf_text(source_path, reference_pages)}
    if set(extracted) != reference_pages:
        raise RuntimeError("Role A could not extract every target reference page")

    page_records = []
    for contract in contracts:
        reference_page = int(contract["reference_page"])
        page = extracted[reference_page]
        geometry = analyze_page_geometry(page, geometry_config)
        statement_rows = _financial_span(
            reconstruct_statement_rows(
                geometry,
                geometry_config,
                table_id=f"role-a-page-{reference_page:04d}",
            )
        )
        rows = []
        for row in statement_rows:
            reader_row = ReaderRow(
                source_row_ids=(row.row_id,),
                label=row.label,
                note_reference=row.note_reference,
                cells=tuple(cell.parsed for cell in row.cells),
            )
            record = reader_row_to_dict(reader_row)
            record.update(
                row_type=row.row_type.value,
                label_bboxes=[_box(box) for box in row.label_boxes],
                note_bbox=_box(row.note_bbox),
                value_bboxes=[_box(cell.bbox) for cell in row.cells],
                value_axis_ids=[cell.axis_id for cell in row.cells],
                warnings=list(row.warnings),
            )
            rows.append(record)
        bindings = []
        for binding in bind_value_headers(geometry, geometry_config):
            bindings.append(
                {
                    "axis_id": binding.axis_id,
                    "raw_header": binding.raw_header,
                    "header_bbox": _box(binding.header_bbox),
                    "unit": binding.unit,
                    "unit_multiplier": binding.unit_multiplier,
                    "unit_bbox": _box(binding.unit_bbox),
                    "period_start": _date(binding.period_start),
                    "period_end": _date(binding.period_end),
                    "period_type": binding.period_type,
                    "duration_months": binding.duration_months,
                    "current_or_comparative": binding.current_or_comparative,
                    "restated": binding.restated,
                    "confidence": binding.confidence,
                    "evidence": list(binding.evidence),
                }
            )
        page_records.append(
            {
                "reference_page": reference_page,
                "candidate_page": int(contract["candidate_page"]),
                "statement_type": contract["statement_type"],
                "expected_scope": contract["expected_scope"],
                "continuation": {
                    key: value
                    for key, value in contract.items()
                    if key.startswith("continued_")
                },
                "text_quality": page.text_quality,
                "corruption_markers": list(page.corruption_markers),
                "context_text": normalize_text_for_record(page),
                "headers": bindings,
                "rows": rows,
            }
        )

    implementation_paths = (
        Path("src/bctc_ai/ocr/pdf_text.py"),
        Path("src/bctc_ai/tables/geometry.py"),
        Path("src/bctc_ai/rows/pdf_statement.py"),
        Path("src/bctc_ai/axes/header_binding.py"),
        Path("scripts/experiments/build_e0010_role_a.py"),
    )
    result = {
        "format_version": 1,
        "experiment_id": "E-0010",
        "state": "REFERENCE_COMPLETE",
        "reference_kind": "ROLE_A_NATIVE_STRUCTURAL_REFERENCE_UNMAPPED",
        "dataset_role": suite.dataset_role.value,
        "source": reference.path,
        "source_sha256": reference.sha256,
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
        "suite_config": {
            "path": suite_config.relative_to(project_root).as_posix(),
            "sha256": sha256_file(suite_config),
        },
        "geometry_config": {
            "path": geometry_config_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(geometry_config_path),
        },
        "evidence_stage": EvidenceStage.ROLE_A_BUILD.value,
        "evidence_manifest": [
            {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}
            for item in evidence
        ],
        "algorithm_files_sha256": {
            path.as_posix(): sha256_file(project_root / path) for path in implementation_paths
        },
        "pages": page_records,
        "claim_boundary": (
            "Native searchable-PDF geometry is an independent machine reference, not human gold. "
            "Rows are not schema-mapped and cannot establish production full-tuple accuracy."
        ),
    }
    atomic_write_json(result_path, result)
    seal = {
        "format_version": 1,
        "state": "REFERENCE_COMPLETE",
        "sealed_at": datetime.now(UTC).isoformat(),
        "result_path": result_path.relative_to(project_root).as_posix(),
        "result_sha256": sha256_file(result_path),
        "source_sha256": reference.sha256,
        "code": result["code"],
        "page_count": len(page_records),
        "claim_boundary": result["claim_boundary"],
    }
    atomic_write_json(seal_path, seal)
    print(
        json.dumps(
            {
                "state": seal["state"],
                "result_path": seal["result_path"],
                "result_sha256": seal["result_sha256"],
                "seal_path": seal_path.relative_to(project_root).as_posix(),
                "seal_sha256": sha256_file(seal_path),
                "page_count": len(page_records),
            },
            sort_keys=True,
        )
    )
    return 0


def normalize_text_for_record(page) -> str:
    return " ".join(word.normalized_text for word in page.words)


if __name__ == "__main__":
    raise SystemExit(main())

