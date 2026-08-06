from __future__ import annotations

import json
import subprocess
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
)
from bctc_ai.evaluation.reader_outputs_v2 import load_vlm_table_parser_config
from bctc_ai.evaluation.semantic_geometry_fusion import (
    fuse_semantic_labels_onto_geometry_rows,
    load_semantic_geometry_fusion_config,
    semantic_geometry_fusion_to_dict,
)
from bctc_ai.evaluation.word_box_rows_v2 import (
    load_word_box_reconstruction_v2_config,
    parse_ppocrv6_word_box_page_v2,
)
from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.mapping.scope import load_scope_policy


class TargetedFusionEvaluationError(RuntimeError):
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
        raise TargetedFusionEvaluationError(f"cannot read JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise TargetedFusionEvaluationError(f"JSON evidence is not an object: {path}")
    return payload


def _resolve(project_root: Path, path_text: str) -> Path:
    path = (project_root / path_text).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise TargetedFusionEvaluationError(f"evidence escapes project root: {path}") from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise TargetedFusionEvaluationError(f"path escapes project root: {path}") from exc


def _load_config(project_root: Path, config_path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise TargetedFusionEvaluationError(f"cannot read E-0019 config: {config_path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise TargetedFusionEvaluationError("E-0019 config must be version 1")
    if payload.get("experiment_id") != "E-0019":
        raise TargetedFusionEvaluationError("unexpected targeted fusion experiment ID")
    if payload.get("dataset_role") != "CALIBRATION":
        raise TargetedFusionEvaluationError("E-0019 must remain calibration-only")
    if payload.get("selection_policy") != "E0017_PREDECLARED_TWO_PAGE_LCTT_CONTINUATION":
        raise TargetedFusionEvaluationError("E-0019 page-selection policy drifted")
    safety = payload.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise TargetedFusionEvaluationError("E-0019 config grants forbidden authority")
    for name, record in payload.get("upstream", {}).items():
        if not isinstance(record, dict):
            raise TargetedFusionEvaluationError(f"invalid upstream record: {name}")
        evidence_path = _resolve(project_root, str(record.get("path", "")))
        if not evidence_path.is_file() or sha256_file(evidence_path) != record.get("sha256"):
            raise TargetedFusionEvaluationError(f"upstream evidence drift: {name}")
    pages = payload.get("target", {}).get("pages")
    if pages != [
        {"reference_page": 12, "candidate_page": 13},
        {"reference_page": 13, "candidate_page": 14},
    ]:
        raise TargetedFusionEvaluationError("E-0019 target page contract drifted")
    return payload


def _target_page(payload: dict[str, Any], key: str, page_number: int) -> dict[str, Any]:
    matches = [page for page in payload.get("pages", []) if int(page.get(key, -1)) == page_number]
    if len(matches) != 1:
        raise TargetedFusionEvaluationError(
            f"expected one page record for {key}={page_number}, found {len(matches)}"
        )
    return matches[0]


def _verify_reader_run(
    project_root: Path,
    config: dict[str, Any],
    *,
    page: int,
    reader: str,
) -> tuple[Path, dict[str, Any]]:
    upstream = config["upstream"]
    prefix = "deepseek" if reader == "deepseek" else "word_box"
    manifest_path = _resolve(project_root, upstream[f"{prefix}_page_{page}_manifest"]["path"])
    result_path = _resolve(project_root, upstream[f"{prefix}_page_{page}_result"]["path"])
    manifest = _load_json(manifest_path)
    contract = config["inference_contracts"][page]
    expected_role = (
        "SEMANTIC_AND_READING_ORDER_PROPOSAL_ONLY"
        if reader == "deepseek"
        else "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY"
    )
    expected_network = (
        "PROCESS_SOCKET_CONNECT_AND_DNS_DENIED"
        if reader == "deepseek"
        else "PROCESS_SOCKET_CONNECT_DENIED"
    )
    expected_commit = contract["deepseek_commit" if reader == "deepseek" else "word_box_commit"]
    if manifest.get("state") != "OCR_COMPLETE":
        raise TargetedFusionEvaluationError(f"{reader} page {page} run is incomplete")
    if manifest.get("dataset_role") != "CALIBRATION":
        raise TargetedFusionEvaluationError(f"{reader} page {page} dataset role drifted")
    if manifest.get("evidence_role") != expected_role:
        raise TargetedFusionEvaluationError(f"{reader} page {page} evidence role drifted")
    if manifest.get("code", {}).get("commit") != expected_commit:
        raise TargetedFusionEvaluationError(f"{reader} page {page} commit drifted")
    if manifest.get("code", {}).get("dirty") is not False:
        raise TargetedFusionEvaluationError(f"{reader} page {page} was not a clean run")
    if manifest.get("input", {}).get("sha256") != contract["input_sha256"]:
        raise TargetedFusionEvaluationError(f"{reader} page {page} input drifted")
    if manifest.get("configuration", {}).get("network_policy") != expected_network:
        raise TargetedFusionEvaluationError(f"{reader} page {page} network policy drifted")
    artifact = manifest.get("artifacts", {}).get("ocr_result", {})
    if artifact.get("sha256") != sha256_file(result_path):
        raise TargetedFusionEvaluationError(f"{reader} page {page} result hash drifted")
    if artifact.get("size_bytes") != result_path.stat().st_size:
        raise TargetedFusionEvaluationError(f"{reader} page {page} result size drifted")
    return result_path, manifest


def _rate_delta(before: dict[str, Any], after: dict[str, Any], key: str) -> float | None:
    if before.get(key) is None or after.get(key) is None:
        return None
    return round(float(after[key]) - float(before[key]), 6)


def evaluate_targeted_fixed_grid_fusion(
    project_root: Path,
    *,
    experiment_config: Path,
    output: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise TargetedFusionEvaluationError("formal evaluation requires a clean Git worktree")
    config_path = _resolve(project_root, experiment_config.as_posix())
    output_path = _resolve(project_root, output.as_posix())
    if output_path.exists():
        raise TargetedFusionEvaluationError(f"refusing to overwrite formal artifact: {output_path}")
    config = _load_config(project_root, config_path)
    upstream = config["upstream"]
    role_a_seal = _load_json(_resolve(project_root, upstream["role_a_seal"]["path"]))
    role_a = _load_json(_resolve(project_root, upstream["role_a_result"]["path"]))
    baseline = _load_json(_resolve(project_root, upstream["baseline"]["path"]))
    if role_a_seal.get("state") != "REFERENCE_COMPLETE":
        raise TargetedFusionEvaluationError("Role A reference is not sealed")
    if role_a_seal.get("result_sha256") != upstream["role_a_result"]["sha256"]:
        raise TargetedFusionEvaluationError("Role A seal/result identity drifted")

    semantic_config = load_vlm_table_parser_config(
        _resolve(project_root, upstream["semantic_parser_config"]["path"])
    )
    geometry_config = load_word_box_reconstruction_v2_config(
        _resolve(project_root, upstream["geometry_parser_config"]["path"])
    )
    fusion_config = load_semantic_geometry_fusion_config(
        _resolve(project_root, upstream["fusion_config"]["path"])
    )
    scope_policy = load_scope_policy(_resolve(project_root, upstream["scope_policy"]["path"]))

    before_comparisons = []
    after_comparisons = []
    page_records = []
    reader_runtime = []
    fused_rows = []
    for target_page in config["target"]["pages"]:
        reference_page_number = int(target_page["reference_page"])
        candidate_page_number = int(target_page["candidate_page"])
        reference_page = _target_page(role_a, "reference_page", reference_page_number)
        baseline_page = _target_page(baseline, "candidate_page", candidate_page_number)
        if baseline_page.get("reference_page") != reference_page_number:
            raise TargetedFusionEvaluationError("baseline page pairing drifted")
        before_comparisons.append(baseline_page["comparison"])

        semantic_result_path, semantic_manifest = _verify_reader_run(
            project_root,
            config,
            page=candidate_page_number,
            reader="deepseek",
        )
        geometry_result_path, geometry_manifest = _verify_reader_run(
            project_root,
            config,
            page=candidate_page_number,
            reader="word_box",
        )
        render_path = _resolve(
            project_root,
            upstream[f"render_page_{candidate_page_number}"]["path"],
        )
        semantic = parse_deepseek_ocr2_result_v2(
            semantic_result_path,
            semantic_config,
            page_tag=f"e0019-semantic-page-{candidate_page_number:04d}",
        )
        if semantic.page.unresolved_table_count or len(semantic.page.tables) != 1:
            raise TargetedFusionEvaluationError(
                f"page {candidate_page_number} semantic table structure is unresolved"
            )
        geometry = parse_ppocrv6_word_box_page_v2(
            geometry_result_path,
            geometry_config,
            page_tag=f"e0019-geometry-page-{candidate_page_number:04d}",
            source_image_path=render_path,
        )
        fusion = fuse_semantic_labels_onto_geometry_rows(
            geometry.reader_rows,
            semantic.reader_rows,
            fusion_config,
        )
        if fusion.status != "FUSED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID":
            raise TargetedFusionEvaluationError(
                f"page {candidate_page_number} fusion remained unresolved: "
                + "; ".join(fusion.unresolved_reasons)
            )
        reference_rows = tuple(reader_row_from_dict(row) for row in reference_page["rows"])
        comparison = compare_reader_rows(
            reference_rows,
            fusion.reader_rows,
            statement_type="LCTT",
            scope_policy=scope_policy,
            candidate_context_text=semantic.page.context_text,
        )
        after_comparisons.append(comparison)
        fused_rows.extend(fusion.reader_rows)
        page_records.append(
            {
                "reference_page": reference_page_number,
                "candidate_page": candidate_page_number,
                "geometry_axes": [
                    {
                        "axis_id": axis.axis_id,
                        "raw_header": axis.raw_header,
                        "right_edge": axis.right_edge,
                        "header_line_index": axis.header_line_index,
                    }
                    for axis in geometry.axes
                ],
                "geometry_row_count": len(geometry.rows),
                "semantic_raw_grid_row_count": len(semantic.page.tables[0].raw_grid),
                "semantic_canonical_row_count": len(semantic.reader_rows),
                "semantic_fragment_merges": [
                    {
                        "table_index": item.table_index,
                        "label_source_grid_row": item.label_source_grid_row,
                        "value_source_grid_row": item.value_source_grid_row,
                        "source_row_ids": list(item.source_row_ids),
                        "rule": item.rule,
                        "value_cells_unmodified": item.value_cells_unmodified,
                    }
                    for item in semantic.fragment_merges
                ],
                "fusion": semantic_geometry_fusion_to_dict(fusion),
                "comparison": comparison,
            }
        )
        reader_runtime.append(
            {
                "candidate_page": candidate_page_number,
                "deepseek": {
                    "inference_commit": semantic_manifest["code"]["commit"],
                    "metrics": semantic_manifest["metrics"],
                    "network_policy": semantic_manifest["configuration"]["network_policy"],
                },
                "word_box": {
                    "inference_commit": geometry_manifest["code"]["commit"],
                    "metrics": geometry_manifest["metrics"],
                    "network_policy": geometry_manifest["configuration"]["network_policy"],
                },
            }
        )

    before_metrics = aggregate_cross_reader_metrics(before_comparisons)
    after_metrics = aggregate_cross_reader_metrics(after_comparisons)
    before_errors = classify_cross_reader_error_classes(before_metrics, before_comparisons)
    after_errors = classify_cross_reader_error_classes(after_metrics, after_comparisons)
    cash_flow = classify_cash_flow_method(
        [row.label for row in fused_rows],
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
        "experiment_id": "E-0019",
        "status": "PASS_CALIBRATION_FIXED_GRID_FUSION_NO_CONFIDENCE_PROMOTION",
        "dataset_role": "CALIBRATION",
        "selection_policy": config["selection_policy"],
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
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
        "reader_runtime": reader_runtime,
        "pages": page_records,
        "before": {
            "reader": "PaddleOCR-VL-1.6",
            "metrics": before_metrics,
            "error_analysis": before_errors,
        },
        "after": {
            "reader": "PP_OCRV6_FIXED_GEOMETRY_PLUS_DEEPSEEK_OCR2_SEMANTIC_LABELS",
            "metrics": after_metrics,
            "error_analysis": after_errors,
        },
        "delta": {key: _rate_delta(before_metrics, after_metrics, key) for key in rate_keys}
        | {
            "candidate_rows": int(after_metrics["candidate_rows"])
            - int(before_metrics["candidate_rows"]),
            "candidate_invalid_cells": int(after_metrics["candidate_invalid_cells"])
            - int(before_metrics["candidate_invalid_cells"]),
            "exact_reference_financial_cells": int(after_metrics["exact_reference_financial_cells"])
            - int(before_metrics["exact_reference_financial_cells"]),
            "structural_error_impact": int(
                after_errors["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"]["impact_count"]
            )
            - int(before_errors["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"]["impact_count"]),
        },
        "fusion_summary": {
            "geometry_rows": sum(page["geometry_row_count"] for page in page_records),
            "semantic_rows_before_fusion": sum(
                page["semantic_canonical_row_count"] for page in page_records
            ),
            "fused_rows": sum(len(page["fusion"]["rows"]) for page in page_records),
            "overflow_repairs": sum(
                len(page["fusion"]["overflow_repairs"]) for page in page_records
            ),
            "exact_semantic_numeric_fingerprints": sum(
                row["semantic_value_fingerprint_exact"]
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
        "acceptance": {
            "fixed_grid_fusion_replay_complete": True,
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
                "src/bctc_ai/evaluation/semantic_geometry_fusion.py",
                "src/bctc_ai/evaluation/targeted_fusion_evaluation.py",
                "src/bctc_ai/evaluation/word_box_rows_v2.py",
                "src/bctc_ai/evaluation/semantic_html_tables.py",
                "src/bctc_ai/evaluation/deepseek_output.py",
                "src/bctc_ai/evaluation/reader_outputs.py",
                "src/bctc_ai/evaluation/cross_reader_metrics.py",
                "src/bctc_ai/validation/reader_agreement.py",
                "src/bctc_ai/mapping/lctt.py",
                "src/bctc_ai/mapping/scope.py",
            )
        },
        "claim_boundary": (
            "Two-page calibration against an independent native-PDF machine reference; "
            "not human gold, not a schema-mapping evaluation, not bank/period-disjoint, "
            "and not a production threshold. Numeric fingerprints gate structure only; "
            "fusion does not promote confidence or replace geometry cells."
        ),
    }
    atomic_write_json(output_path, payload)
    return payload
