from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.cross_reader_metrics import (
    aggregate_cross_reader_metrics,
    classify_cross_reader_error_classes,
)
from bctc_ai.evaluation.deepseek_output import parse_deepseek_ocr2_result_v2
from bctc_ai.evaluation.reader_outputs import (
    compare_reader_rows,
    reader_row_from_dict,
    reader_row_to_dict,
)
from bctc_ai.evaluation.reader_outputs_v2 import (
    load_vlm_table_parser_config,
    table_roles_to_dict,
)
from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.mapping.scope import load_scope_policy


class TargetedSemanticEvaluationError(RuntimeError):
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
        raise TargetedSemanticEvaluationError(f"cannot read JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise TargetedSemanticEvaluationError(f"JSON evidence is not an object: {path}")
    return payload


def _resolve(project_root: Path, path_text: str) -> Path:
    path = (project_root / path_text).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise TargetedSemanticEvaluationError(f"evidence escapes the project root: {path}") from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise TargetedSemanticEvaluationError(
            f"formal artifact path escapes the project root: {path}"
        ) from exc


def _load_config(project_root: Path, path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise TargetedSemanticEvaluationError(f"cannot read experiment config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise TargetedSemanticEvaluationError("targeted semantic config must be version 1")
    if payload.get("experiment_id") != "E-0018":
        raise TargetedSemanticEvaluationError("unexpected targeted semantic experiment ID")
    if payload.get("dataset_role") != "CALIBRATION":
        raise TargetedSemanticEvaluationError("E-0018 must remain calibration-only")
    if payload.get("selection_policy") != "PREDECLARED_E0017_MAIN_STRUCTURAL_FAILURE_ONLY":
        raise TargetedSemanticEvaluationError("E-0018 target selection policy drifted")
    safety = payload.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise TargetedSemanticEvaluationError("E-0018 config grants forbidden authority")
    fragment = payload.get("row_fragment_policy", {})
    if fragment.get("rule") != "ADJACENT_LABEL_ONLY_THEN_VALUE_ONLY_SAME_WIDTH":
        raise TargetedSemanticEvaluationError("E-0018 row-fragment rule drifted")
    if fragment.get("value_cells_may_be_repaired") is not False:
        raise TargetedSemanticEvaluationError("E-0018 permits value repair")
    for name, record in payload.get("upstream", {}).items():
        if not isinstance(record, dict):
            raise TargetedSemanticEvaluationError(f"invalid upstream record: {name}")
        evidence_path = _resolve(project_root, str(record.get("path", "")))
        if not evidence_path.is_file() or sha256_file(evidence_path) != record.get("sha256"):
            raise TargetedSemanticEvaluationError(f"upstream evidence drift: {name}")
    return payload


def _verify_deepseek_run(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    upstream = config["upstream"]
    manifest_path = _resolve(project_root, upstream["deepseek_run_manifest"]["path"])
    result_path = _resolve(project_root, upstream["deepseek_result"]["path"])
    manifest = _load_json(manifest_path)
    contract = config["inference_contract"]
    if manifest.get("state") != "OCR_COMPLETE":
        raise TargetedSemanticEvaluationError("DeepSeek run is incomplete")
    if manifest.get("dataset_role") != contract["dataset_role"]:
        raise TargetedSemanticEvaluationError("DeepSeek dataset role drifted")
    if manifest.get("evidence_role") != contract["evidence_role"]:
        raise TargetedSemanticEvaluationError("DeepSeek evidence role drifted")
    if manifest.get("code", {}).get("commit") != contract["git_commit"]:
        raise TargetedSemanticEvaluationError("DeepSeek inference commit drifted")
    if manifest.get("code", {}).get("dirty") is not contract["git_dirty"]:
        raise TargetedSemanticEvaluationError("DeepSeek inference dirty state drifted")
    if manifest.get("input", {}).get("sha256") != contract["input_sha256"]:
        raise TargetedSemanticEvaluationError("DeepSeek input identity drifted")
    if manifest.get("configuration", {}).get("network_policy") != contract["network_policy"]:
        raise TargetedSemanticEvaluationError("DeepSeek network policy drifted")
    artifact = manifest.get("artifacts", {}).get("ocr_result", {})
    if artifact.get("sha256") != sha256_file(result_path):
        raise TargetedSemanticEvaluationError("DeepSeek result differs from its run manifest")
    if artifact.get("size_bytes") != result_path.stat().st_size:
        raise TargetedSemanticEvaluationError("DeepSeek result size differs from its run manifest")
    return result_path, manifest


def _target_page(payload: dict[str, Any], key: str, page_number: int) -> dict[str, Any]:
    matches = [page for page in payload.get("pages", []) if int(page.get(key, -1)) == page_number]
    if len(matches) != 1:
        raise TargetedSemanticEvaluationError(
            f"expected one page record for {key}={page_number}, found {len(matches)}"
        )
    return matches[0]


def _rate_delta(before: dict[str, Any], after: dict[str, Any], key: str) -> float | None:
    before_value = before.get(key)
    after_value = after.get(key)
    if before_value is None or after_value is None:
        return None
    return round(float(after_value) - float(before_value), 6)


def evaluate_targeted_semantic_reader(
    project_root: Path,
    *,
    experiment_config: Path,
    output: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise TargetedSemanticEvaluationError("formal evaluation requires a clean Git worktree")
    config_path = _resolve(project_root, experiment_config.as_posix())
    output_path = _resolve(project_root, output.as_posix())
    if output_path.exists():
        raise TargetedSemanticEvaluationError(
            f"refusing to overwrite formal artifact: {output_path}"
        )
    config = _load_config(project_root, config_path)
    target = config["target"]
    reference_page_number = int(target["reference_page"])
    candidate_page_number = int(target["candidate_page"])
    upstream = config["upstream"]

    role_a_seal = _load_json(_resolve(project_root, upstream["role_a_seal"]["path"]))
    role_a = _load_json(_resolve(project_root, upstream["role_a_result"]["path"]))
    if role_a_seal.get("state") != "REFERENCE_COMPLETE":
        raise TargetedSemanticEvaluationError("Role A seal is incomplete")
    if role_a_seal.get("result_sha256") != upstream["role_a_result"]["sha256"]:
        raise TargetedSemanticEvaluationError("Role A seal/result identity drifted")
    baseline = _load_json(_resolve(project_root, upstream["baseline"]["path"]))
    reference_page = _target_page(role_a, "reference_page", reference_page_number)
    baseline_page = _target_page(baseline, "candidate_page", candidate_page_number)
    if baseline_page.get("reference_page") != reference_page_number:
        raise TargetedSemanticEvaluationError("baseline page pairing drifted")

    result_path, run_manifest = _verify_deepseek_run(project_root, config)
    parser_config = load_vlm_table_parser_config(
        _resolve(project_root, upstream["table_parser_config"]["path"])
    )
    parsed = parse_deepseek_ocr2_result_v2(
        result_path,
        parser_config,
        page_tag=f"deepseek-role-b-page-{candidate_page_number:04d}",
    )
    if parsed.page.unresolved_table_count:
        raise TargetedSemanticEvaluationError("DeepSeek output has unresolved table roles")
    if len(parsed.page.tables) != 1 or not parsed.page.tables[0].rows:
        raise TargetedSemanticEvaluationError("expected one parsed DeepSeek financial table")

    reference_rows = tuple(reader_row_from_dict(row) for row in reference_page["rows"])
    scope_policy = load_scope_policy(_resolve(project_root, upstream["scope_policy"]["path"]))
    comparison = compare_reader_rows(
        reference_rows,
        parsed.reader_rows,
        statement_type=str(target["statement_type"]),
        scope_policy=scope_policy,
        candidate_context_text=parsed.page.context_text,
    )
    before_comparison = baseline_page["comparison"]
    before_metrics = aggregate_cross_reader_metrics((before_comparison,))
    after_metrics = aggregate_cross_reader_metrics((comparison,))
    before_errors = classify_cross_reader_error_classes(
        before_metrics,
        (before_comparison,),
    )
    after_errors = classify_cross_reader_error_classes(after_metrics, (comparison,))
    cash_flow = classify_cash_flow_method(
        [row.label for row in parsed.reader_rows],
        load_cash_flow_rules(_resolve(project_root, upstream["cash_flow_rules"]["path"])),
    )
    table = parsed.page.tables[0]
    rate_keys = (
        "reference_financial_row_coverage_rate",
        "reference_financial_cell_coverage_rate",
        "conditional_exact_cell_agreement_rate",
        "conditional_exact_financial_row_agreement_rate",
        "strict_exact_reference_cell_agreement_rate",
        "strict_exact_reference_financial_row_agreement_rate",
        "semantic_key_exact_label_rate",
    )
    payload = {
        "format_version": 1,
        "experiment_id": config["experiment_id"],
        "status": "PASS_CALIBRATION_TARGETED_READER_WITH_NO_CONFIDENCE_PROMOTION",
        "dataset_role": config["dataset_role"],
        "selection_policy": config["selection_policy"],
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
        "target": target,
        "evidence_manifest": [
            {
                "kind": name.upper(),
                "path": record["path"],
                "sha256": record["sha256"],
            }
            for name, record in upstream.items()
        ]
        + [
            {
                "kind": "EXPERIMENT_CONFIG",
                "path": _relative(project_root, config_path),
                "sha256": sha256_file(config_path),
            }
        ],
        "reader_runtime": {
            "inference_git_commit": run_manifest["code"]["commit"],
            "model": run_manifest["runtime"]["model"],
            "packages": run_manifest["runtime"]["packages"],
            "metrics": run_manifest["metrics"],
            "network_policy": run_manifest["configuration"]["network_policy"],
        },
        "table_reconstruction": {
            "status": table.status,
            "bbox_coordinate_space": "MODEL_NORMALIZED_0_999_PROPOSAL_ONLY",
            "bbox": list(table.bbox),
            "header": list(table.header),
            "roles": table_roles_to_dict(table.roles),
            "raw_grid_row_count": len(table.raw_grid),
            "canonical_row_count": len(table.rows),
            "span_expansion_count": table.span_expansion_count,
            "fragment_merges": [asdict(item) for item in parsed.fragment_merges],
            "warnings": list(table.warnings),
        },
        "before": {
            "reader": "PaddleOCR-VL-1.6",
            "metrics": before_metrics,
            "error_analysis": before_errors,
        },
        "after": {
            "reader": "DeepSeek-OCR-2_PLUS_EXPLICIT_FRAGMENT_REASSEMBLY",
            "metrics": after_metrics,
            "error_analysis": after_errors,
            "comparison": comparison,
            "rows": [reader_row_to_dict(row) for row in parsed.reader_rows],
        },
        "delta": {key: _rate_delta(before_metrics, after_metrics, key) for key in rate_keys}
        | {
            "candidate_invalid_cells": (
                int(after_metrics["candidate_invalid_cells"])
                - int(before_metrics["candidate_invalid_cells"])
            ),
            "exact_reference_financial_cells": (
                int(after_metrics["exact_reference_financial_cells"])
                - int(before_metrics["exact_reference_financial_cells"])
            ),
            "structural_error_impact": (
                int(after_errors["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"]["impact_count"])
                - int(
                    before_errors["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"]["impact_count"]
                )
            ),
        },
        "cash_flow": {
            "baseline_method": baseline["cash_flow"]["method"],
            "targeted_reader_method": cash_flow.method.value,
            "direct_anchor_positions": cash_flow.direct_anchor_positions,
            "indirect_anchor_positions": cash_flow.indirect_anchor_positions,
            "reason": cash_flow.reason,
            "semantic_high_confidence_allowed": cash_flow.semantic_high_confidence_allowed,
        },
        "raw_semantic_output": parsed.raw_output,
        "acceptance": {
            "targeted_reader_eligible_for_geometry_fusion": True,
            "automatic_value_replacement": False,
            "automatic_schema_mapping": False,
            "automatic_period_assignment": False,
            "automatic_scope_assignment": False,
            "automatic_geometry_authority": False,
            "automatic_confidence_promotion": False,
            "historical_reference_invoked": False,
            "full_pipeline_or_production_claim": False,
        },
        "algorithm_files_sha256": {
            path: sha256_file(project_root / path)
            for path in (
                "src/bctc_ai/evaluation/reader_outputs_v2.py",
                "src/bctc_ai/evaluation/semantic_html_tables.py",
                "src/bctc_ai/evaluation/deepseek_output.py",
                "src/bctc_ai/evaluation/targeted_semantic_evaluation.py",
                "src/bctc_ai/evaluation/reader_outputs.py",
                "src/bctc_ai/evaluation/cross_reader_metrics.py",
                "src/bctc_ai/validation/reader_agreement.py",
                "src/bctc_ai/mapping/lctt.py",
                "src/bctc_ai/mapping/scope.py",
            )
        },
        "claim_boundary": (
            "Target-page calibration against an independent native-PDF machine reference; "
            "not human gold, not end-to-end schema accuracy, and not a production threshold. "
            "Reader agreement and arithmetic are supporting evidence only."
        ),
    }
    atomic_write_json(output_path, payload)
    return payload
