from __future__ import annotations

import subprocess
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from bctc_ai.axes.header_binding import bind_value_headers
from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    FrozenSuite,
    load_frozen_suite,
    validate_evidence_manifest,
)
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.ocr.pdf_text import extract_pdf_text
from bctc_ai.rows.pdf_statement import financial_table_span, reconstruct_statement_rows
from bctc_ai.tables.geometry import analyze_page_geometry, load_geometry_config
from bctc_ai.validation.reader_agreement import ReaderRow


class NativeReferenceError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeReferenceError(f"evidence path must be inside project root: {path}") from exc


def _box(value: Any) -> dict[str, float] | None:
    return asdict(value) if value is not None else None


def _date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def validate_native_reference_contracts(suite: FrozenSuite) -> tuple[dict[str, Any], ...]:
    raw_contracts = suite.pairing.get("target_page_contracts")
    if not isinstance(raw_contracts, list) or not raw_contracts:
        raise NativeReferenceError("suite has no target_page_contracts")
    contracts: list[dict[str, Any]] = []
    reference_pages: set[int] = set()
    candidate_pages: set[int] = set()
    for raw in raw_contracts:
        if not isinstance(raw, dict):
            raise NativeReferenceError("every target page contract must be a mapping")
        try:
            reference_page = int(raw["reference_page"])
            candidate_page = int(raw["candidate_page"])
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeReferenceError("page contract has invalid page numbers") from exc
        if reference_page < 1 or candidate_page < 1:
            raise NativeReferenceError("page contract page numbers must be positive")
        if reference_page in reference_pages or candidate_page in candidate_pages:
            raise NativeReferenceError("target page contracts must be one-to-one")
        statement_type = str(raw.get("statement_type", ""))
        if statement_type not in {"CDKT", "KQKD", "LCTT"}:
            raise NativeReferenceError(f"invalid statement_type: {statement_type!r}")
        expected_scope = str(raw.get("expected_scope", ""))
        if expected_scope not in {"MAIN_STATEMENT", "OFF_BALANCE_SHEET"}:
            raise NativeReferenceError(f"invalid expected_scope: {expected_scope!r}")
        reference_pages.add(reference_page)
        candidate_pages.add(candidate_page)
        contracts.append(dict(raw))
    return tuple(contracts)


def build_native_role_a_reference(
    project_root: Path,
    *,
    suite_config: Path,
    output_root: Path,
    geometry_config: Path = Path("config/tables/geometry-v2.yaml"),
) -> dict[str, Any]:
    """Build a sealed machine reference from native searchable-PDF geometry."""

    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise NativeReferenceError("Role A must start from a clean Git worktree")
    suite_path = (project_root / suite_config).resolve() if not suite_config.is_absolute() else suite_config
    geometry_path = (
        (project_root / geometry_config).resolve()
        if not geometry_config.is_absolute()
        else geometry_config.resolve()
    )
    suite = load_frozen_suite(project_root, suite_path)
    contracts = validate_native_reference_contracts(suite)
    reference = suite.source(str(suite.pairing["reference_fixture_id"]))
    if reference.fixture_role != "ROLE_A_SOURCE":
        raise NativeReferenceError("reference fixture must be frozen as ROLE_A_SOURCE")
    source_path = project_root / reference.path
    geometry = load_geometry_config(geometry_path)
    root = (
        (project_root / output_root).resolve()
        if not output_root.is_absolute()
        else output_root.resolve()
    )
    run_root = root / reference.sha256[:20]
    result_path = run_root / "role_a_rows.json"
    seal_path = run_root / "role_a_seal.json"
    if result_path.exists() or seal_path.exists():
        raise NativeReferenceError(f"refusing to overwrite Role A output: {run_root}")

    evidence = (
        EvidenceItem(EvidenceKind.ROLE_A_SOURCE_PDF, reference.path, reference.sha256),
        EvidenceItem(EvidenceKind.CONFIG, _relative(project_root, suite_path), sha256_file(suite_path)),
        EvidenceItem(
            EvidenceKind.CONFIG,
            _relative(project_root, geometry_path),
            sha256_file(geometry_path),
        ),
    )
    validate_evidence_manifest(EvidenceStage.ROLE_A_BUILD, evidence)
    reference_pages = {int(contract["reference_page"]) for contract in contracts}
    extracted = {page.page: page for page in extract_pdf_text(source_path, reference_pages)}
    if set(extracted) != reference_pages:
        missing = sorted(reference_pages - set(extracted))
        raise NativeReferenceError(f"Role A could not extract target pages: {missing}")

    page_records = []
    for contract in contracts:
        reference_page = int(contract["reference_page"])
        page = extracted[reference_page]
        page_geometry = analyze_page_geometry(page, geometry)
        statement_rows = financial_table_span(
            reconstruct_statement_rows(
                page_geometry,
                geometry,
                table_id=f"{suite.experiment_id.casefold()}-role-a-page-{reference_page:04d}",
            )
        )
        rows = []
        for row in statement_rows:
            serialized = reader_row_to_dict(
                ReaderRow(
                    source_row_ids=(row.row_id,),
                    label=row.label,
                    note_reference=row.note_reference,
                    cells=tuple(cell.parsed for cell in row.cells),
                )
            )
            serialized.update(
                row_type=row.row_type.value,
                label_bboxes=[_box(box) for box in row.label_boxes],
                note_bbox=_box(row.note_bbox),
                value_bboxes=[_box(cell.bbox) for cell in row.cells],
                value_axis_ids=[cell.axis_id for cell in row.cells],
                warnings=list(row.warnings),
            )
            rows.append(serialized)
        bindings = [
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
            for binding in bind_value_headers(page_geometry, geometry)
        ]
        page_records.append(
            {
                "reference_page": reference_page,
                "candidate_page": int(contract["candidate_page"]),
                "statement_type": contract["statement_type"],
                "expected_scope": contract["expected_scope"],
                "continuation": {
                    key: value for key, value in contract.items() if key.startswith("continued_")
                },
                "text_quality": page.text_quality,
                "corruption_markers": list(page.corruption_markers),
                "context_text": " ".join(word.normalized_text for word in page.words),
                "headers": bindings,
                "rows": rows,
            }
        )

    implementation_paths = (
        Path("src/bctc_ai/core/text.py"),
        Path("src/bctc_ai/ocr/pdf_text.py"),
        Path("src/bctc_ai/tables/geometry.py"),
        Path("src/bctc_ai/rows/pdf_statement.py"),
        Path("src/bctc_ai/axes/header_binding.py"),
        Path("src/bctc_ai/evaluation/native_reference.py"),
    )
    result = {
        "format_version": 2,
        "experiment_id": suite.experiment_id,
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
            "path": _relative(project_root, suite_path),
            "sha256": sha256_file(suite_path),
        },
        "geometry_config": {
            "path": _relative(project_root, geometry_path),
            "sha256": sha256_file(geometry_path),
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
            "Native searchable-PDF geometry is an independent machine reference, not human "
            "gold. Rows are not schema-mapped and cannot establish production full-tuple accuracy."
        ),
    }
    atomic_write_json(result_path, result)
    seal = {
        "format_version": 2,
        "experiment_id": suite.experiment_id,
        "state": "REFERENCE_COMPLETE",
        "sealed_at": datetime.now(UTC).isoformat(),
        "result_path": _relative(project_root, result_path),
        "result_sha256": sha256_file(result_path),
        "source_sha256": reference.sha256,
        "code": result["code"],
        "page_count": len(page_records),
        "claim_boundary": result["claim_boundary"],
    }
    atomic_write_json(seal_path, seal)
    return {
        "state": seal["state"],
        "experiment_id": suite.experiment_id,
        "result_path": seal["result_path"],
        "result_sha256": seal["result_sha256"],
        "seal_path": _relative(project_root, seal_path),
        "seal_sha256": sha256_file(seal_path),
        "page_count": len(page_records),
    }
