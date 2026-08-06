from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.ocr.vietnamese_label_correction import (
    OrderedObservedLabel,
    load_vietnamese_label_correction_config,
    propose_vietnamese_label_corrections,
    vietnamese_label_correction_to_dict,
    vocabulary_labels_from_schema_items,
)
from bctc_ai.schema.registry import load_all


class VietnameseLabelCorrectionEvaluationError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, path_text: str) -> Path:
    path = (project_root / path_text).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise VietnameseLabelCorrectionEvaluationError(
            f"evaluation path escapes project root: {path}"
        ) from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise VietnameseLabelCorrectionEvaluationError(
            f"evaluation path escapes project root: {path}"
        ) from exc


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise VietnameseLabelCorrectionEvaluationError(
            f"cannot read JSON evidence: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise VietnameseLabelCorrectionEvaluationError(f"JSON evidence is not an object: {path}")
    return payload


def _verify_record(project_root: Path, record: dict[str, Any], name: str) -> Path:
    path = _resolve(project_root, str(record.get("path", "")))
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise VietnameseLabelCorrectionEvaluationError(f"{name} is missing or hash-drifted")
    return path


def _load_config(project_root: Path, path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise VietnameseLabelCorrectionEvaluationError(
            f"cannot read E-0021 config: {path}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise VietnameseLabelCorrectionEvaluationError("E-0021 config must be version 1")
    if payload.get("experiment_id") != "E-0021" or payload.get("dataset_role") != "CALIBRATION":
        raise VietnameseLabelCorrectionEvaluationError("E-0021 identity or role drifted")
    if payload.get("selection_policy") != (
        "REPLAY_ALL_140_E0020_ROWS_WITHOUT_REFERENCE_LABELS_AS_INPUT_FEATURES"
    ):
        raise VietnameseLabelCorrectionEvaluationError("E-0021 selection policy drifted")
    safety = payload.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise VietnameseLabelCorrectionEvaluationError("E-0021 grants forbidden authority")
    upstream = payload.get("upstream")
    if not isinstance(upstream, dict) or len(upstream) != 7:
        raise VietnameseLabelCorrectionEvaluationError("E-0021 upstream evidence is incomplete")
    for name, record in upstream.items():
        if not isinstance(record, dict):
            raise VietnameseLabelCorrectionEvaluationError(f"invalid E-0021 record: {name}")
        _verify_record(project_root, record, name)
    return payload


def _casefold_exact(left: str, right: str) -> bool:
    return normalize_text(left).casefold() == normalize_text(right).casefold()


def _semantic_exact(left: str, right: str) -> bool:
    return retrieval_key(left) == retrieval_key(right)


def _canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate_vietnamese_label_correction(
    project_root: Path,
    *,
    experiment_config: Path,
    output: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise VietnameseLabelCorrectionEvaluationError(
            "formal evaluation requires a clean Git worktree"
        )
    config_path = _resolve(project_root, experiment_config.as_posix())
    output_path = _resolve(project_root, output.as_posix())
    if output_path.exists():
        raise VietnameseLabelCorrectionEvaluationError(
            f"refusing to overwrite artifact: {output_path}"
        )
    config = _load_config(project_root, config_path)
    upstream = config["upstream"]
    e0020_path = _verify_record(project_root, upstream["e0020_result"], "E-0020 result")
    correction_config_path = _verify_record(
        project_root, upstream["correction_config"], "correction config"
    )
    e0020 = _load_json(e0020_path)
    if (
        e0020.get("experiment_id") != "E-0020"
        or e0020.get("status")
        != "PASS_CALIBRATION_ORDERED_LABEL_SEGMENTATION_NO_CONFIDENCE_PROMOTION"
    ):
        raise VietnameseLabelCorrectionEvaluationError("E-0020 is not a sealed passing input")

    ordered_rows = []
    references = []
    locations = []
    for page in e0020.get("pages", []):
        candidate_page = int(page["candidate_page"])
        statement_type = str(page["statement_type"])
        for alignment_index, alignment in enumerate(page["comparison"]["alignment"]):
            if alignment.get("action") != "MATCH":
                raise VietnameseLabelCorrectionEvaluationError(
                    "E-0021 requires the complete 140-row E-0020 MATCH grid"
                )
            raw_label = str(alignment["candidate_label"])
            row_id = f"page-{candidate_page:04d}:alignment-{alignment_index:04d}"
            ordered_rows.append(OrderedObservedLabel(row_id, statement_type, raw_label))
            references.append(str(alignment["reference_label"]))
            locations.append(
                {
                    "candidate_page": candidate_page,
                    "alignment_index": alignment_index,
                    "statement_type": statement_type,
                }
            )
    target = config["target"]
    if len(ordered_rows) != int(target["upstream_rows"]):
        raise VietnameseLabelCorrectionEvaluationError("E-0020 row denominator drifted")
    if sorted({row.statement_type for row in ordered_rows}) != sorted(
        target["expected_statement_types"]
    ):
        raise VietnameseLabelCorrectionEvaluationError("statement-type coverage drifted")

    workbooks, schema_items = load_all(project_root / "template", project_root)
    tm_1944 = [item for item in schema_items if item.schema_id == 1944]
    if len(tm_1944) != 1 or tm_1944[0].statement_type != "TM":
        raise VietnameseLabelCorrectionEvaluationError("approved TM ReportNormId 1944 is absent")
    correction = propose_vietnamese_label_corrections(
        ordered_rows,
        vocabulary_labels_from_schema_items(schema_items),
        load_vietnamese_label_correction_config(correction_config_path),
    )
    if len(correction.proposals) != len(ordered_rows):
        raise VietnameseLabelCorrectionEvaluationError("correction changed the row denominator")

    correction_records = []
    raw_casefold_exact = 0
    corrected_casefold_exact = 0
    raw_semantic_exact = 0
    corrected_semantic_exact = 0
    semantic_regressions = 0
    non_improving_proposals = 0
    for row, proposal, reference, location in zip(
        ordered_rows,
        correction.proposals,
        references,
        locations,
        strict=True,
    ):
        before_casefold = _casefold_exact(row.raw_label, reference)
        after_casefold = _casefold_exact(proposal.corrected_label, reference)
        before_semantic = _semantic_exact(row.raw_label, reference)
        after_semantic = _semantic_exact(proposal.corrected_label, reference)
        raw_casefold_exact += before_casefold
        corrected_casefold_exact += after_casefold
        raw_semantic_exact += before_semantic
        corrected_semantic_exact += after_semantic
        semantic_regressions += before_semantic and not after_semantic
        if proposal.replacements and not after_casefold:
            non_improving_proposals += 1
        if proposal.replacements:
            correction_records.append(
                location
                | {
                    "row_id": proposal.row_id,
                    "reference_label": reference,
                    "before_casefold_exact": before_casefold,
                    "after_casefold_exact": after_casefold,
                    "before_semantic_key_exact": before_semantic,
                    "after_semantic_key_exact": after_semantic,
                    "proposal": vietnamese_label_correction_to_dict(correction)["proposals"][
                        proposal.row_position
                    ],
                }
            )

    expected = {
        "raw_semantic": int(target["expected_raw_semantic_key_exact_labels"]),
        "corrected_semantic": int(target["expected_corrected_semantic_key_exact_labels"]),
        "proposed": int(target["expected_proposed_rows"]),
    }
    observed = {
        "raw_semantic": raw_semantic_exact,
        "corrected_semantic": corrected_semantic_exact,
        "proposed": correction.corrected_count,
    }
    if observed != expected or semantic_regressions or non_improving_proposals:
        raise VietnameseLabelCorrectionEvaluationError(
            f"E-0021 acceptance failed: expected={expected}, observed={observed}, "
            f"semantic_regressions={semantic_regressions}, "
            f"non_improving_proposals={non_improving_proposals}"
        )

    schema_order = {
        workbook.statement_type: [
            item.schema_id
            for item in schema_items
            if item.statement_type == workbook.statement_type
        ]
        for workbook in workbooks
    }
    metrics = {
        "rows": len(ordered_rows),
        "proposed_rows": correction.corrected_count,
        "unchanged_rows": correction.unchanged_count,
        "raw_casefold_exact_labels": raw_casefold_exact,
        "corrected_casefold_exact_labels": corrected_casefold_exact,
        "raw_semantic_key_exact_labels": raw_semantic_exact,
        "corrected_semantic_key_exact_labels": corrected_semantic_exact,
        "semantic_key_regressions": semantic_regressions,
        "non_improving_proposals": non_improving_proposals,
        "proposal_casefold_precision": round(
            (correction.corrected_count - non_improving_proposals) / correction.corrected_count,
            6,
        ),
    }
    payload = {
        "format_version": 1,
        "experiment_id": "E-0021",
        "status": "PASS_CALIBRATION_VIETNAMESE_LABEL_CORRECTION_NO_CONFIDENCE_PROMOTION",
        "dataset_role": "CALIBRATION",
        "selection_policy": config["selection_policy"],
        "code": {"git_commit": _git(project_root, "rev-parse", "HEAD"), "git_dirty": False},
        "target": target,
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
        "metrics": metrics,
        "delta": {
            "casefold_exact_labels": corrected_casefold_exact - raw_casefold_exact,
            "semantic_key_exact_labels": corrected_semantic_exact - raw_semantic_exact,
        },
        "corrections": correction_records,
        "safety": {
            "raw_labels_preserved": correction.raw_labels_preserved,
            "row_order_preserved": correction.row_order_preserved,
            "numeric_or_note_fields_present": correction.numeric_or_note_fields_present,
            "automatic_output_authority": correction.automatic_output_authority,
            "automatic_schema_mapping_authority": (correction.automatic_schema_mapping_authority),
            "role_a_labels_used_as_correction_features": False,
            "period_or_scope_fields_present": False,
            "confidence_promoted": False,
        },
        "upstream_numeric_structure": {
            "e0020_after_metrics_sha256": _canonical_json_sha256(e0020["after"]["metrics"]),
            "financial_cells": e0020["after"]["metrics"]["reference_financial_cells"],
            "exact_financial_cells": e0020["after"]["metrics"]["exact_reference_financial_cells"],
            "candidate_invalid_cells": e0020["after"]["metrics"]["candidate_invalid_cells"],
            "correction_layer_received_numeric_or_note_fields": False,
        },
        "schema_vocabulary": {
            "item_count": len(schema_items),
            "workbook_display_order_preserved": True,
            "numeric_report_norm_id_sort_used": False,
            "ordered_ids_sha256": _canonical_json_sha256(schema_order),
            "tm_1944_present": True,
            "tm_1944_name": tm_1944[0].canonical_name,
            "report_norm_id_output_or_mapping_emitted": False,
        },
        "acceptance": {
            "all_140_rows_replayed": True,
            "all_four_semantic_residuals_corrected": True,
            "non_target_proposal_count": 0,
            "automatic_value_replacement": False,
            "automatic_schema_mapping": False,
            "automatic_period_assignment": False,
            "automatic_scope_assignment": False,
            "automatic_confidence_promotion": False,
            "historical_reference_invoked": False,
            "full_pipeline_or_production_claim": False,
        },
        "algorithm_files_sha256": {
            path: sha256_file(project_root / path)
            for path in (
                "src/bctc_ai/ocr/vietnamese_label_correction.py",
                "src/bctc_ai/evaluation/vietnamese_label_correction_evaluation.py",
                "src/bctc_ai/core/text.py",
                "src/bctc_ai/schema/registry.py",
            )
        },
        "claim_boundary": (
            "Whole-six-page calibration replay against the same native-PDF machine Role A; "
            "not human gold, not bank/period-disjoint, not a schema mapping decision, and "
            "not a production threshold. Reference labels are used only after proposal "
            "generation for scoring. Raw OCR labels remain immutable evidence."
        ),
    }
    atomic_write_json(output_path, payload)
    return payload
