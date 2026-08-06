from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.cross_reader_metrics import (
    aggregate_cross_reader_metrics,
    classify_cross_reader_error_classes,
)
from bctc_ai.evaluation.reader_outputs import (
    compare_reader_rows,
    parse_paddle_vl_page,
    reader_row_from_dict,
)
from bctc_ai.evaluation.semantic_geometry_fusion_v2 import (
    fuse_ordered_semantic_labels_onto_geometry_rows_v2,
    load_semantic_geometry_fusion_v2_config,
    semantic_geometry_fusion_v2_to_dict,
)
from bctc_ai.evaluation.word_box_rows import (
    load_word_box_reconstruction_config,
    parse_ppocrv6_word_box_page,
)
from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.mapping.scope import load_scope_policy


class OrderedSegmentationEvaluationError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise OrderedSegmentationEvaluationError(f"cannot read JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise OrderedSegmentationEvaluationError(f"JSON evidence is not an object: {path}")
    return payload


def _resolve(project_root: Path, path_text: str) -> Path:
    path = (project_root / path_text).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise OrderedSegmentationEvaluationError(f"evidence escapes project root: {path}") from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise OrderedSegmentationEvaluationError(f"path escapes project root: {path}") from exc


def _verify_record(project_root: Path, record: dict[str, Any], label: str) -> Path:
    path = _resolve(project_root, str(record.get("path", "")))
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise OrderedSegmentationEvaluationError(f"{label} is absent or hash-drifted: {path}")
    if record.get("size_bytes") is not None and path.stat().st_size != record["size_bytes"]:
        raise OrderedSegmentationEvaluationError(f"{label} size drifted: {path}")
    return path


def _load_config(project_root: Path, path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise OrderedSegmentationEvaluationError(f"cannot read E-0020 config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise OrderedSegmentationEvaluationError("E-0020 config must be version 1")
    if payload.get("experiment_id") != "E-0020" or payload.get("dataset_role") != "CALIBRATION":
        raise OrderedSegmentationEvaluationError("E-0020 identity or role drifted")
    if payload.get("selection_policy") != "REPLAY_ALL_SIX_FROZEN_E0010_E0011_PAGES":
        raise OrderedSegmentationEvaluationError("E-0020 selection policy drifted")
    safety = payload.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise OrderedSegmentationEvaluationError("E-0020 grants forbidden authority")
    for name, record in payload.get("upstream", {}).items():
        if not isinstance(record, dict):
            raise OrderedSegmentationEvaluationError(f"invalid upstream record: {name}")
        evidence_path = _resolve(project_root, str(record.get("path", "")))
        if not evidence_path.is_file() or sha256_file(evidence_path) != record.get("sha256"):
            raise OrderedSegmentationEvaluationError(f"upstream evidence drift: {name}")
    pages = payload.get("target", {}).get("pages")
    if not isinstance(pages, list) or len(pages) != 6:
        raise OrderedSegmentationEvaluationError("E-0020 must retain all six frozen pages")
    return payload


def _target_page(payload: dict[str, Any], key: str, page_number: int) -> dict[str, Any]:
    matches = [page for page in payload.get("pages", []) if int(page.get(key, -1)) == page_number]
    if len(matches) != 1:
        raise OrderedSegmentationEvaluationError(
            f"expected one page for {key}={page_number}, found {len(matches)}"
        )
    return matches[0]


def _role_b_result(project_root: Path, page_record: dict[str, Any]) -> Path:
    page = int(page_record["page"])
    result_suffix = f"page-{page:04d}_res.json"
    matches = []
    for output in page_record.get("outputs", []):
        path = _verify_record(project_root, output, f"Role B page {page} output")
        if path.name == result_suffix:
            matches.append(path)
    if len(matches) != 1:
        raise OrderedSegmentationEvaluationError(f"Role B page {page} has no unique JSON result")
    _verify_record(project_root, page_record["metrics"], f"Role B page {page} metrics")
    _verify_record(project_root, page_record["render"], f"Role B page {page} render")
    return matches[0]


def _verify_seals(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    upstream = config["upstream"]
    role_a_seal = _load_json(_resolve(project_root, upstream["role_a_seal"]["path"]))
    role_a = _load_json(_resolve(project_root, upstream["role_a_result"]["path"]))
    role_b = _load_json(_resolve(project_root, upstream["role_b_seal"]["path"]))
    role_c = _load_json(_resolve(project_root, upstream["role_c_seal"]["path"]))
    if role_a_seal.get("state") != "REFERENCE_COMPLETE":
        raise OrderedSegmentationEvaluationError("Role A reference is not complete")
    if role_a_seal.get("result_sha256") != upstream["role_a_result"]["sha256"]:
        raise OrderedSegmentationEvaluationError("Role A seal/result identity drifted")
    if role_b.get("state") != "OCR_COMPLETE" or role_b.get("dataset_role") != "CALIBRATION":
        raise OrderedSegmentationEvaluationError("Role B seal is incomplete or unsafe")
    if (
        role_c.get("state") != "GEOMETRY_OCR_COMPLETE"
        or role_c.get("dataset_role") != "CALIBRATION"
        or role_c.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY"
    ):
        raise OrderedSegmentationEvaluationError("Role C seal is incomplete or unsafe")
    if role_b.get("source_sha256") != role_c.get("source_sha256"):
        raise OrderedSegmentationEvaluationError("Role B and Role C source identities differ")
    if role_c.get("upstream_role_b_seal", {}).get("sha256") != upstream["role_b_seal"]["sha256"]:
        raise OrderedSegmentationEvaluationError("Role C is not bound to the supplied Role B")
    return role_a, role_b, role_c


def _rate_delta(before: dict[str, Any], after: dict[str, Any], key: str) -> float | None:
    if before.get(key) is None or after.get(key) is None:
        return None
    return round(float(after[key]) - float(before[key]), 6)


def evaluate_ordered_label_segmentation(
    project_root: Path,
    *,
    experiment_config: Path,
    output: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise OrderedSegmentationEvaluationError("formal evaluation requires a clean Git worktree")
    config_path = _resolve(project_root, experiment_config.as_posix())
    output_path = _resolve(project_root, output.as_posix())
    if output_path.exists():
        raise OrderedSegmentationEvaluationError(f"refusing to overwrite artifact: {output_path}")
    config = _load_config(project_root, config_path)
    upstream = config["upstream"]
    baseline = _load_json(_resolve(project_root, upstream["baseline"]["path"]))
    geometry_recovery = _load_json(_resolve(project_root, upstream["geometry_recovery"]["path"]))
    role_a, role_b, role_c = _verify_seals(project_root, config)
    role_b_pages = {int(page["page"]): page for page in role_b["pages"]}
    role_c_pages = {int(page["page"]): page for page in role_c["pages"]}
    geometry_config = load_word_box_reconstruction_config(
        _resolve(project_root, upstream["geometry_parser_config"]["path"])
    )
    fusion_config = load_semantic_geometry_fusion_v2_config(
        _resolve(project_root, upstream["fusion_config"]["path"])
    )
    scope_policy = load_scope_policy(_resolve(project_root, upstream["scope_policy"]["path"]))

    before_comparisons = []
    after_comparisons = []
    page_records = []
    lctt_rows = []
    segmentation_actions: Counter[str] = Counter()
    for contract in config["target"]["pages"]:
        reference_page_number = int(contract["reference_page"])
        candidate_page_number = int(contract["candidate_page"])
        statement_type = str(contract["statement_type"])
        reference_page = _target_page(role_a, "reference_page", reference_page_number)
        baseline_page = _target_page(baseline, "candidate_page", candidate_page_number)
        before_comparisons.append(baseline_page["comparison"])
        role_b_record = role_b_pages[candidate_page_number]
        role_c_record = role_c_pages[candidate_page_number]
        semantic_path = _role_b_result(project_root, role_b_record)
        geometry_result_path = _verify_record(
            project_root,
            role_c_record["ocr_result"],
            f"Role C page {candidate_page_number} result",
        )
        _verify_record(
            project_root,
            role_c_record["run_manifest"],
            f"Role C page {candidate_page_number} manifest",
        )
        render_path = _verify_record(
            project_root,
            role_c_record["render"],
            f"Role C page {candidate_page_number} render",
        )
        semantic_page = parse_paddle_vl_page(semantic_path)
        semantic_rows = tuple(row for table in semantic_page.tables for row in table.rows)
        geometry_page = parse_ppocrv6_word_box_page(
            geometry_result_path,
            geometry_config,
            page_tag=f"e0020-geometry-page-{candidate_page_number:04d}",
            source_image_path=render_path,
        )
        geometry_rows = tuple(item.row for item in geometry_page.rows)
        fusion = fuse_ordered_semantic_labels_onto_geometry_rows_v2(
            geometry_rows,
            semantic_rows,
            fusion_config,
        )
        if fusion.status != "FUSED_ORDERED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID_V2":
            raise OrderedSegmentationEvaluationError(
                f"page {candidate_page_number} fusion unresolved: "
                + "; ".join(fusion.unresolved_reasons)
            )
        comparison = compare_reader_rows(
            tuple(reader_row_from_dict(row) for row in reference_page["rows"]),
            fusion.reader_rows,
            statement_type=statement_type,
            scope_policy=scope_policy,
            candidate_context_text=semantic_page.context_text,
        )
        after_comparisons.append(comparison)
        if statement_type == "LCTT":
            lctt_rows.extend(fusion.reader_rows)
        segmentation_actions.update(item.action for item in fusion.segmentations)
        page_records.append(
            {
                "reference_page": reference_page_number,
                "candidate_page": candidate_page_number,
                "statement_type": statement_type,
                "expected_scope": contract["expected_scope"],
                "semantic_row_count": len(semantic_rows),
                "geometry_row_count": len(geometry_rows),
                "fusion": semantic_geometry_fusion_v2_to_dict(fusion),
                "comparison": comparison,
            }
        )

    before_metrics = aggregate_cross_reader_metrics(before_comparisons)
    after_metrics = aggregate_cross_reader_metrics(after_comparisons)
    before_errors = classify_cross_reader_error_classes(before_metrics, before_comparisons)
    after_errors = classify_cross_reader_error_classes(after_metrics, after_comparisons)
    cash_flow = classify_cash_flow_method(
        [row.label for row in lctt_rows],
        load_cash_flow_rules(_resolve(project_root, upstream["cash_flow_rules"]["path"])),
    )
    rate_keys = (
        "reference_financial_row_coverage_rate",
        "reference_financial_cell_coverage_rate",
        "conditional_exact_cell_agreement_rate",
        "conditional_exact_financial_row_agreement_rate",
        "strict_exact_reference_cell_agreement_rate",
        "strict_exact_reference_financial_row_agreement_rate",
        "source_exact_label_rate",
        "semantic_key_exact_label_rate",
    )
    payload = {
        "format_version": 1,
        "experiment_id": "E-0020",
        "status": "PASS_CALIBRATION_ORDERED_LABEL_SEGMENTATION_NO_CONFIDENCE_PROMOTION",
        "dataset_role": "CALIBRATION",
        "selection_policy": config["selection_policy"],
        "code": {"git_commit": _git(project_root, "rev-parse", "HEAD"), "git_dirty": False},
        "target": config["target"],
        "evidence_manifest": [
            {"kind": name.upper(), "path": record["path"], "sha256": record["sha256"]}
            for name, record in upstream.items()
        ]
        + [
            {
                "kind": "EXPERIMENT_CONFIG",
                "path": _relative(project_root, config_path),
                "sha256": sha256_file(config_path),
            }
        ],
        "pages": page_records,
        "before": {
            "reader": "PADDLEOCR_VL_SEMANTIC_ROWS",
            "metrics": before_metrics,
            "error_analysis": before_errors,
        },
        "geometry_only_reference": {
            "experiment": "E-0011",
            "metrics": geometry_recovery["metrics"],
        },
        "after": {
            "reader": "E0011_FIXED_GEOMETRY_PLUS_E0010_ORDERED_SEMANTIC_LABELS_V2",
            "metrics": after_metrics,
            "error_analysis": after_errors,
        },
        "delta": {key: _rate_delta(before_metrics, after_metrics, key) for key in rate_keys}
        | {
            "candidate_invalid_cells": int(after_metrics["candidate_invalid_cells"])
            - int(before_metrics["candidate_invalid_cells"]),
            "exact_reference_financial_cells": int(after_metrics["exact_reference_financial_cells"])
            - int(before_metrics["exact_reference_financial_cells"]),
        },
        "fusion_summary": {
            "semantic_rows": sum(page["semantic_row_count"] for page in page_records),
            "geometry_rows": sum(page["geometry_row_count"] for page in page_records),
            "fused_rows": sum(len(page["fusion"]["rows"]) for page in page_records),
            "segmentation_actions": dict(sorted(segmentation_actions.items())),
            "ignored_blank_label_semantic_rows": sum(
                len(page["fusion"]["ignored_semantic_rows"]) for page in page_records
            ),
            "rows_with_semantic_numeric_fingerprint": sum(
                row["semantic_numeric_fingerprint_observed"]
                for page in page_records
                for row in page["fusion"]["rows"]
            ),
            "geometry_cells_unmodified": all(
                page["fusion"]["policy"]["geometry_cells_unmodified"]
                and all(row["geometry_cells_unmodified"] for row in page["fusion"]["rows"])
                for page in page_records
            ),
        },
        "cash_flow": {
            "baseline_method": baseline["cash_flow"]["method"],
            "fused_method": cash_flow.method.value,
            "direct_anchor_positions": cash_flow.direct_anchor_positions,
            "indirect_anchor_positions": cash_flow.indirect_anchor_positions,
            "reason": cash_flow.reason,
            "semantic_high_confidence_allowed": cash_flow.semantic_high_confidence_allowed,
        },
        "off_balance_gate": {
            "candidate_page": 12,
            "expected_excluded_rows": 20,
            "observed_excluded_rows": after_metrics["scope_excluded_candidate_rows"],
            "mapping_eligible": False,
        },
        "acceptance": {
            "ordered_segmentation_replay_complete": True,
            "automatic_value_replacement": False,
            "automatic_schema_mapping": False,
            "automatic_period_assignment": False,
            "automatic_scope_assignment": False,
            "automatic_geometry_replacement": False,
            "automatic_confidence_promotion": False,
            "historical_reference_invoked": False,
            "full_pipeline_or_production_claim": False,
        },
        "algorithm_files_sha256": {
            path: sha256_file(project_root / path)
            for path in (
                "src/bctc_ai/evaluation/semantic_geometry_fusion_v2.py",
                "src/bctc_ai/evaluation/ordered_segmentation_evaluation.py",
                "src/bctc_ai/evaluation/reader_outputs.py",
                "src/bctc_ai/evaluation/word_box_rows.py",
                "src/bctc_ai/evaluation/cross_reader_metrics.py",
                "src/bctc_ai/validation/reader_agreement.py",
                "src/bctc_ai/mapping/lctt.py",
                "src/bctc_ai/mapping/scope.py",
            )
        },
        "claim_boundary": (
            "Six-page post-failure calibration against the same native-PDF machine Role A; "
            "not human gold, not bank/period-disjoint, not schema mapping, and not a "
            "production threshold. Geometry cells remain unchanged and reader agreement "
            "does not promote confidence."
        ),
    }
    atomic_write_json(output_path, payload)
    return payload
