from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json, atomic_write_jsonl, atomic_write_text
from bctc_ai.core.environment import collect_environment
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.ingestion.bank_registry import load_bank_registry
from bctc_ai.ingestion.discovery import discover_pdfs
from bctc_ai.ingestion.registry import register_sources
from bctc_ai.questions.bootstrap import bootstrap_questions, write_questions
from bctc_ai.reference.historical import verify_historical_weak_reference
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.storage.backup import create_backup


@dataclass(frozen=True)
class BootstrapResult:
    recovery_audit: str
    project_goal: str
    questions: str
    backup_status: str


def _git(project_root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments], cwd=project_root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _write_schema_artifacts(
    project_root: Path,
) -> tuple[list[dict[str, object]], int, str, dict[str, object]]:
    workbooks, items = load_all(project_root / "template", project_root)
    hierarchy, hierarchy_items = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        items,
    )
    apply_hierarchy_reference(items, hierarchy_items)
    hierarchy_record = hierarchy.to_dict()
    atomic_write_json(
        project_root / "data/registered/hierarchy_registry.json",
        hierarchy_record,
    )
    workbook_records = [asdict(workbook) for workbook in workbooks]
    graph_records = [item.to_dict() for item in items]
    atomic_write_jsonl(project_root / "reference/schemas/schema_graph.jsonl", graph_records)
    registry = {
        "format_version": 1,
        "authority": "SUPPLIED_WORKBOOKS",
        "append_only": True,
        "workbooks": workbook_records,
        "counts": {
            workbook["statement_type"]: workbook["item_count"] for workbook in workbook_records
        },
        "total_items": len(items),
        "contains_tm_1944": any(item.schema_id == 1944 for item in items),
        "lctt_semantics": "WORKBOOK_BLOCKS_VERIFIED_SEMANTIC_CONFLICT_REOPENED_2026_08_05",
        "hierarchy_reference": hierarchy_record,
    }
    atomic_write_json(project_root / "data/registered/schema_registry.json", registry)
    graph_hash = stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in graph_records
    )
    return workbook_records, len(items), graph_hash, hierarchy_record


def _write_schema_proposal(
    project_root: Path,
    historical_verification: dict[str, object] | None = None,
) -> None:
    dump_registry_path = project_root / "data/registered/mongodb_dump_registry.json"
    dump_registry = (
        json.loads(dump_registry_path.read_text(encoding="utf-8"))
        if dump_registry_path.is_file()
        else None
    )
    historical_registry_path = (
        project_root / "data/registered/historical_weak_reference_registry.json"
    )
    historical_registry = (
        json.loads(historical_registry_path.read_text(encoding="utf-8"))
        if historical_registry_path.is_file()
        else None
    )
    template_collision_safe = bool(
        dump_registry
        and dump_registry.get("collision_audit", {}).get(
            "append_safe_from_id_collision_perspective"
        )
    )
    historical_collision_safe = bool(
        historical_registry
        and historical_verification
        and historical_verification.get("status") == "PASS"
        and historical_registry.get("schema", {}).get(
            "append_safe_from_historical_key_collision_perspective"
        )
    )
    collision_safe = template_collision_safe and (
        historical_registry is None or historical_collision_safe
    )
    proposal = {
        "proposal_id": "SCHEMA-TM-1944",
        "pdf_name": None,
        "proposed_schema_id": 1944,
        "proposed_canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "statement_type": "TM",
        "section": None,
        "parent": None,
        "position_before": 1943,
        "position_after": None,
        "scope": None,
        "period": None,
        "unit": None,
        "mongodb_evidence": [],
        "reason": "Named append-only item in the master directive is absent from the supplied TM workbook.",
        "confidence": "PROPOSAL_REQUIRES_USER_CONFIRMATION",
        "question_id": "Q-BOOT-004",
        "collision_evidence": {
            "schema_hierarchy_and_mongodb_templates": (
                dump_registry.get("collision_audit") if dump_registry else None
            ),
            "historical_data_chart_keys": (
                {
                    "source_contains_proposed_id": historical_registry["schema"][
                        "source_contains_proposed_id"
                    ],
                    "append_safe_from_historical_key_collision_perspective": (
                        historical_collision_safe
                    ),
                    "selected_document_count": historical_registry["source"][
                        "selected_document_count"
                    ],
                    "cell_count": historical_registry["cells"]["count"],
                }
                if historical_registry
                else None
            ),
        },
        "status": (
            "COLLISION_CHECK_PASSED_APPEND_DECISION_OPEN"
            if collision_safe
            else "PENDING_COLLISION_CHECK"
        ),
    }
    atomic_write_jsonl(project_root / "proposed_schema_additions.jsonl", [proposal])


def _load_calibration_summary(project_root: Path) -> dict[str, object]:
    artifact_path = Path("docs/experiments/E-0010-tcb-cross-reader-calibration.json")
    absolute_artifact = project_root / artifact_path
    if not absolute_artifact.is_file():
        return {
            "integrity_status": "NOT_AVAILABLE",
            "artifact": artifact_path.as_posix(),
            "errors": ["tracked E-0010 artifact is absent"],
        }
    try:
        artifact = json.loads(absolute_artifact.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "integrity_status": "FAIL",
            "artifact": artifact_path.as_posix(),
            "errors": [f"cannot read E-0010 artifact: {exc}"],
        }

    errors: list[str] = []
    if artifact.get("format_version") != 2:
        errors.append("unexpected E-0010 format version")
    if artifact.get("experiment_id") != "E-0010":
        errors.append("unexpected calibration experiment ID")
    if artifact.get("dataset_role") != "CALIBRATION":
        errors.append("E-0010 dataset role is not CALIBRATION")
    if artifact.get("status") != "PASS_CALIBRATION_WITH_REQUIRED_ESCALATIONS":
        errors.append("E-0010 recorded status is not the accepted calibration state")
    code = artifact.get("code")
    if not isinstance(code, dict) or code.get("git_dirty") is not False:
        errors.append("E-0010 was not recorded from a clean code state")

    algorithm_files = artifact.get("algorithm_files_sha256")
    if not isinstance(algorithm_files, dict) or not algorithm_files:
        errors.append("E-0010 has no algorithm hash set")
    else:
        for relative_path, digest in algorithm_files.items():
            local_path = project_root / str(relative_path)
            if not local_path.is_file() or sha256_file(local_path) != digest:
                errors.append(f"algorithm hash drift: {relative_path}")

    suite = artifact.get("suite_config")
    if not isinstance(suite, dict):
        errors.append("E-0010 has no suite config identity")
    else:
        suite_path = project_root / str(suite.get("path", ""))
        if not suite_path.is_file() or sha256_file(suite_path) != suite.get("sha256"):
            errors.append("E-0010 suite config hash drift")

    local_seals = []
    sealed_inputs = artifact.get("sealed_inputs")
    if not isinstance(sealed_inputs, dict):
        errors.append("E-0010 has no sealed input identities")
    else:
        for role, seal in sealed_inputs.items():
            if not isinstance(seal, dict):
                errors.append(f"invalid sealed input record: {role}")
                continue
            seal_path = project_root / str(seal.get("path", ""))
            present = seal_path.is_file()
            verified = present and sha256_file(seal_path) == seal.get("sha256")
            local_seals.append({"role": role, "present": present, "verified": verified})
            if present and not verified:
                errors.append(f"local seal hash drift: {role}")

    metrics = artifact.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("E-0010 has no metrics")
        metrics = {}
    local_count = sum(bool(record["present"]) for record in local_seals)
    verified_count = sum(bool(record["verified"]) for record in local_seals)
    if errors:
        integrity_status = "FAIL"
    elif local_count:
        integrity_status = "PASS_TRACKED_AND_LOCAL_SEALS"
    else:
        integrity_status = "PASS_TRACKED_ARTIFACT"
    return {
        "integrity_status": integrity_status,
        "artifact": artifact_path.as_posix(),
        "artifact_sha256": sha256_file(absolute_artifact),
        "experiment_id": artifact.get("experiment_id"),
        "recorded_status": artifact.get("status"),
        "dataset_role": artifact.get("dataset_role"),
        "code_commit": code.get("git_commit") if isinstance(code, dict) else None,
        "claim_boundary": artifact.get("claim_boundary"),
        "metrics": metrics,
        "acceptance": artifact.get("acceptance"),
        "off_balance_gate": artifact.get("off_balance_gate"),
        "cash_flow": artifact.get("cash_flow"),
        "continuation_accepted": all(
            bool(record.get("accepted")) for record in artifact.get("continuation", [])
        ),
        "historical_weak_reference": artifact.get("historical_weak_reference"),
        "local_seals": local_seals,
        "local_seal_count": local_count,
        "verified_local_seal_count": verified_count,
        "errors": errors,
    }


def _load_geometry_recovery_summary(project_root: Path) -> dict[str, object]:
    artifact_path = Path("docs/experiments/E-0011-tcb-geometry-recovery.json")
    absolute_artifact = project_root / artifact_path
    if not absolute_artifact.is_file():
        return {
            "integrity_status": "NOT_AVAILABLE",
            "artifact": artifact_path.as_posix(),
            "errors": ["tracked E-0011 artifact is absent"],
        }
    try:
        artifact = json.loads(absolute_artifact.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "integrity_status": "FAIL",
            "artifact": artifact_path.as_posix(),
            "errors": [f"cannot read E-0011 artifact: {exc}"],
        }

    errors: list[str] = []
    if artifact.get("format_version") != 1:
        errors.append("unexpected E-0011 format version")
    if artifact.get("experiment_id") != "E-0011":
        errors.append("unexpected geometry-recovery experiment ID")
    if artifact.get("dataset_role") != "CALIBRATION":
        errors.append("E-0011 dataset role is not CALIBRATION")
    if artifact.get("design") != "TARGETED_POST_FAILURE_ANALYSIS":
        errors.append("E-0011 design is not targeted post-failure analysis")
    if artifact.get("content_inspected_before_design") is not True:
        errors.append("E-0011 does not disclose post-inspection design")
    if artifact.get("status") != "PASS_TARGETED_GEOMETRY_RECOVERY_CALIBRATION":
        errors.append("E-0011 recorded status is not the accepted targeted state")
    code = artifact.get("code")
    if not isinstance(code, dict) or code.get("git_dirty") is not False:
        errors.append("E-0011 was not recorded from a clean code state")

    algorithm_files = artifact.get("algorithm_files_sha256")
    if not isinstance(algorithm_files, dict) or not algorithm_files:
        errors.append("E-0011 has no algorithm hash set")
    else:
        for relative_path, digest in algorithm_files.items():
            local_path = project_root / str(relative_path)
            if not local_path.is_file() or sha256_file(local_path) != digest:
                errors.append(f"algorithm hash drift: {relative_path}")

    for key in ("experiment_config", "suite_config", "reconstruction_config"):
        record = artifact.get(key)
        if not isinstance(record, dict):
            errors.append(f"E-0011 has no {key} identity")
            continue
        local_path = project_root / str(record.get("path", ""))
        if not local_path.is_file() or sha256_file(local_path) != record.get("sha256"):
            errors.append(f"E-0011 {key} hash drift")

    local_seals = []
    sealed_inputs = artifact.get("sealed_inputs")
    if not isinstance(sealed_inputs, dict):
        errors.append("E-0011 has no sealed input identities")
    else:
        for role, seal in sealed_inputs.items():
            if not isinstance(seal, dict):
                errors.append(f"invalid E-0011 sealed input record: {role}")
                continue
            seal_path = project_root / str(seal.get("path", ""))
            present = seal_path.is_file()
            verified = present and sha256_file(seal_path) == seal.get("sha256")
            local_seals.append({"role": role, "present": present, "verified": verified})
            if present and not verified:
                errors.append(f"local E-0011 seal hash drift: {role}")

    metrics = artifact.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("E-0011 has no metrics")
        metrics = {}
    else:
        required_metrics = {
            "reference_financial_row_coverage_rate": 1.0,
            "strict_exact_reference_financial_row_agreement_rate": 1.0,
            "reference_financial_cell_coverage_rate": 1.0,
            "strict_exact_reference_cell_agreement_rate": 1.0,
            "candidate_invalid_cells": 0,
            "exact_note_references": 50,
        }
        if any(metrics.get(key) != value for key, value in required_metrics.items()):
            errors.append("E-0011 required metric gate drift")
    acceptance = artifact.get("acceptance")
    if (
        not isinstance(acceptance, dict)
        or acceptance.get("auto_verified_high") != 0
        or acceptance.get("configured") != acceptance.get("observed")
    ):
        errors.append("E-0011 automatic high-confidence gate drift")
    off_balance = artifact.get("off_balance_gate")
    if (
        not isinstance(off_balance, dict)
        or off_balance.get("eligible_rows_on_off_balance_pages") != 0
    ):
        errors.append("E-0011 off-balance exclusion gate drift")
    arithmetic = artifact.get("arithmetic_validation")
    if (
        not isinstance(arithmetic, dict)
        or arithmetic.get("value_generation_or_overwrite") is not False
        or not isinstance(arithmetic.get("counts"), dict)
        or arithmetic["counts"].get("FAIL", 0) != 0
    ):
        errors.append("E-0011 arithmetic safety gate drift")
    cash_flow = artifact.get("cash_flow")
    if (
        not isinstance(cash_flow, dict)
        or cash_flow.get("schema_branch_assignment_permitted") is not False
    ):
        errors.append("E-0011 cash-flow fail-closed gate drift")
    continuation = artifact.get("continuation")
    if (
        not isinstance(continuation, list)
        or not continuation
        or not all(bool(record.get("accepted")) for record in continuation)
    ):
        errors.append("E-0011 continuation gate drift")
    recovery = artifact.get("recovery_evidence")
    if (
        not isinstance(recovery, dict)
        or len(recovery.get("pixel_dash_recoveries", [])) != 3
        or len(recovery.get("ocr_dash_alias_recoveries", [])) != 1
        or recovery.get("trailing_context_rows_preserved_but_mapping_ineligible") != 14
        or recovery.get("automatic_confidence_effect") != "NONE"
    ):
        errors.append("E-0011 recovery-evidence gate drift")
    historical = artifact.get("historical_weak_reference")
    if not isinstance(historical, dict) or historical.get("invoked") is not False:
        errors.append("E-0011 historical-reference gate drift")
    report_norm = artifact.get("report_norm_id")
    if not isinstance(report_norm, dict) or report_norm.get("ids_proposed_or_added") != 0:
        errors.append("E-0011 unexpectedly proposes ReportNormID changes")

    local_count = sum(bool(record["present"]) for record in local_seals)
    verified_count = sum(bool(record["verified"]) for record in local_seals)
    if errors:
        integrity_status = "FAIL"
    elif local_count:
        integrity_status = "PASS_TRACKED_AND_LOCAL_SEALS"
    else:
        integrity_status = "PASS_TRACKED_ARTIFACT"
    return {
        "integrity_status": integrity_status,
        "artifact": artifact_path.as_posix(),
        "artifact_sha256": sha256_file(absolute_artifact),
        "experiment_id": artifact.get("experiment_id"),
        "recorded_status": artifact.get("status"),
        "dataset_role": artifact.get("dataset_role"),
        "design": artifact.get("design"),
        "code_commit": code.get("git_commit") if isinstance(code, dict) else None,
        "claim_boundary": artifact.get("claim_boundary"),
        "metrics": metrics,
        "acceptance": acceptance,
        "off_balance_gate": off_balance,
        "cash_flow": cash_flow,
        "arithmetic_validation": arithmetic,
        "recovery_evidence": recovery,
        "continuation_accepted": all(bool(record.get("accepted")) for record in continuation),
        "historical_weak_reference": historical,
        "report_norm_id": report_norm,
        "local_seals": local_seals,
        "local_seal_count": local_count,
        "verified_local_seal_count": verified_count,
        "errors": errors,
    }


def _load_batch_mechanism_summary(project_root: Path) -> dict[str, object]:
    artifact_path = Path("docs/experiments/E-0012-ppocrv6-batch-mechanism.json")
    absolute_artifact = project_root / artifact_path
    if not absolute_artifact.is_file():
        return {
            "integrity_status": "NOT_AVAILABLE",
            "artifact": artifact_path.as_posix(),
            "errors": ["tracked E-0012 artifact is absent"],
        }
    try:
        artifact = json.loads(absolute_artifact.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "integrity_status": "FAIL",
            "artifact": artifact_path.as_posix(),
            "errors": [f"cannot read E-0012 artifact: {exc}"],
        }

    errors: list[str] = []
    expected_header = {
        "format_version": 1,
        "experiment_id": "E-0012",
        "dataset_role": "CALIBRATION",
        "design": "CLEAN_COMMIT_BATCH_MECHANISM_REGRESSION",
        "status": "PASS_BATCH_EQUIVALENCE_RESUME_AND_SEAL",
    }
    for key, value in expected_header.items():
        if artifact.get(key) != value:
            errors.append(f"unexpected E-0012 {key}")
    code = artifact.get("code")
    if not isinstance(code, dict) or code.get("git_dirty") is not False:
        errors.append("E-0012 was not recorded from clean code")

    algorithm_files = artifact.get("algorithm_files_sha256")
    if not isinstance(algorithm_files, dict) or not algorithm_files:
        errors.append("E-0012 has no algorithm hash set")
    else:
        for relative_path, digest in algorithm_files.items():
            local_path = project_root / str(relative_path)
            if not local_path.is_file() or sha256_file(local_path) != digest:
                errors.append(f"E-0012 algorithm hash drift: {relative_path}")

    identities = [artifact.get("configuration")]
    runtime = artifact.get("runtime")
    if isinstance(runtime, dict):
        identities.extend((runtime.get("manifest"), runtime.get("package_freeze")))
    else:
        errors.append("E-0012 has no runtime identity")
    for record in identities:
        if not isinstance(record, dict):
            errors.append("E-0012 config/runtime identity is invalid")
            continue
        local_path = project_root / str(record.get("path", ""))
        if not local_path.is_file() or sha256_file(local_path) != record.get("sha256"):
            errors.append(f"E-0012 config/runtime hash drift: {record.get('path')}")

    batch = artifact.get("batch")
    metrics: dict[str, object] = {}
    if not isinstance(batch, dict) or batch.get("state") != "OCR_COMPLETE":
        errors.append("E-0012 batch completion state drift")
    else:
        raw_metrics = batch.get("metrics")
        if isinstance(raw_metrics, dict):
            metrics = raw_metrics
        required_metrics = {
            "completed_page_count": 1,
            "line_count": 50,
            "word_token_count": 380,
            "model_load_session_count": 1,
        }
        if any(metrics.get(key) != value for key, value in required_metrics.items()):
            errors.append("E-0012 batch metric gate drift")

    equivalence = artifact.get("equivalence")
    if (
        not isinstance(equivalence, dict)
        or equivalence.get("byte_identical") is not True
        or equivalence.get("batch_ocr_result_sha256")
        != equivalence.get("baseline_ocr_result_sha256")
    ):
        errors.append("E-0012 byte-equivalence gate drift")
    resume = artifact.get("resume")
    if (
        not isinstance(resume, dict)
        or resume.get("status") != "PASS_ALREADY_COMPLETE"
        or resume.get("model_reloaded") is not False
        or resume.get("model_load_sessions_before") != 1
        or resume.get("model_load_sessions_after") != 1
    ):
        errors.append("E-0012 no-op resume gate drift")
    sealing = artifact.get("sealing")
    if (
        not isinstance(sealing, dict)
        or sealing.get("status") != "GEOMETRY_OCR_COMPLETE"
        or sealing.get("batch_runner_verified") is not True
        or sealing.get("single_page_helper_verified") is not True
        or sealing.get("automatic_truth_promotion") is not False
        or sealing.get("automatic_schema_promotion") is not False
        or sealing.get("automatic_pdf_confidence_promotion") is not False
    ):
        errors.append("E-0012 sealing safety gate drift")
    acceptance = artifact.get("acceptance")
    if (
        not isinstance(acceptance, dict)
        or acceptance.get("new_accuracy_sample") is not False
        or acceptance.get("production_accuracy_approved") is not False
    ):
        errors.append("E-0012 claim boundary drift")
    if artifact.get("software_or_model_change") is not False:
        errors.append("E-0012 unexpectedly records a software/model change")
    historical = artifact.get("historical_weak_reference")
    report_norm = artifact.get("report_norm_id")
    ytd = artifact.get("ytd_derivation")
    if not isinstance(historical, dict) or historical.get("invoked") is not False:
        errors.append("E-0012 historical-reference gate drift")
    if not isinstance(report_norm, dict) or report_norm.get("ids_proposed_or_added") != 0:
        errors.append("E-0012 unexpectedly proposes ReportNormID changes")
    if not isinstance(ytd, dict) or ytd.get("invoked") is not False:
        errors.append("E-0012 unexpectedly invokes YTD derivation")

    local_artifacts = []
    candidate_records: list[tuple[str, object]] = [
        ("source", artifact.get("source")),
        ("input_manifest", artifact.get("input_manifest")),
        ("upstream_role_b_seal", artifact.get("upstream_role_b_seal")),
        (
            "render",
            artifact.get("source", {}).get("render")
            if isinstance(artifact.get("source"), dict)
            else None,
        ),
        ("page_manifest", batch.get("page_manifest") if isinstance(batch, dict) else None),
        ("ocr_result", batch.get("ocr_result") if isinstance(batch, dict) else None),
        ("seal", sealing),
    ]
    if isinstance(equivalence, dict):
        candidate_records.append(
            (
                "baseline_ocr_result",
                {
                    "path": equivalence.get("baseline_ocr_result_path"),
                    "sha256": equivalence.get("baseline_ocr_result_sha256"),
                },
            )
        )
    if isinstance(batch, dict):
        candidate_records.append(
            (
                "batch_manifest",
                {
                    "path": f"{batch.get('path', '')}/batch_manifest.json",
                    "sha256": batch.get("manifest_sha256_after_resume"),
                },
            )
        )
    for name, record in candidate_records:
        if not isinstance(record, dict):
            errors.append(f"E-0012 has no {name} identity")
            continue
        local_path = project_root / str(record.get("path", ""))
        present = local_path.is_file()
        verified = present and sha256_file(local_path) == record.get("sha256")
        local_artifacts.append({"name": name, "present": present, "verified": verified})
        if present and not verified:
            errors.append(f"local E-0012 artifact hash drift: {name}")

    local_count = sum(bool(record["present"]) for record in local_artifacts)
    verified_count = sum(bool(record["verified"]) for record in local_artifacts)
    if errors:
        integrity_status = "FAIL"
    elif local_count:
        integrity_status = "PASS_TRACKED_AND_LOCAL_ARTIFACTS"
    else:
        integrity_status = "PASS_TRACKED_ARTIFACT"
    return {
        "integrity_status": integrity_status,
        "artifact": artifact_path.as_posix(),
        "artifact_sha256": sha256_file(absolute_artifact),
        "experiment_id": artifact.get("experiment_id"),
        "recorded_status": artifact.get("status"),
        "dataset_role": artifact.get("dataset_role"),
        "design": artifact.get("design"),
        "code_commit": code.get("git_commit") if isinstance(code, dict) else None,
        "claim_boundary": artifact.get("claim_boundary"),
        "metrics": metrics,
        "equivalence": equivalence,
        "resume": resume,
        "sealing": sealing,
        "acceptance": acceptance,
        "local_artifacts": local_artifacts,
        "local_artifact_count": local_count,
        "verified_local_artifact_count": verified_count,
        "errors": errors,
    }


def _safe_project_file(project_root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    relative = Path(value)
    if relative.is_absolute():
        return None
    root = project_root.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        return None
    return candidate


def _load_statement_location_summary(project_root: Path) -> dict[str, object]:
    artifact_path = Path("docs/experiments/E-0013-mbb-vcb-statement-location.json")
    absolute_artifact = project_root / artifact_path
    if not absolute_artifact.is_file():
        return {
            "integrity_status": "NOT_AVAILABLE",
            "artifact": artifact_path.as_posix(),
            "errors": ["tracked E-0013 artifact is absent"],
        }
    try:
        artifact = json.loads(absolute_artifact.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "integrity_status": "FAIL",
            "artifact": artifact_path.as_posix(),
            "errors": [f"cannot read E-0013 artifact: {exc}"],
        }

    errors: list[str] = []
    expected_header = {
        "format_version": 1,
        "experiment_id": "E-0013",
        "dataset_role": "CALIBRATION",
        "design": "CLEAN_MULTI_INSTITUTION_COARSE_STATEMENT_LOCATION_CALIBRATION",
        "status": "PASS_ORDERED_STATEMENT_LOCATION_AND_SCOPE_EXCLUSION",
    }
    for key, value in expected_header.items():
        if artifact.get(key) != value:
            errors.append(f"unexpected E-0013 {key}")
    code = artifact.get("code")
    if not isinstance(code, dict) or code.get("git_dirty") is not False:
        errors.append("E-0013 was not recorded from clean code")
    recorded_commit = code.get("git_commit") if isinstance(code, dict) else None

    algorithm_files = artifact.get("algorithm_files_sha256")
    if not isinstance(algorithm_files, dict) or not algorithm_files:
        errors.append("E-0013 has no algorithm hash set")
    else:
        for relative_path, digest in algorithm_files.items():
            local_path = _safe_project_file(project_root, relative_path)
            if local_path is None or not local_path.is_file() or sha256_file(local_path) != digest:
                errors.append(f"E-0013 algorithm hash drift: {relative_path}")

    upstream = artifact.get("upstream_reader")
    identities: list[tuple[str, object]] = [("configuration", artifact.get("configuration"))]
    if isinstance(upstream, dict):
        identities.extend(
            (
                ("ocr_configuration", upstream.get("ocr_configuration")),
                ("runtime_manifest", upstream.get("runtime_manifest")),
                ("package_freeze", upstream.get("package_freeze")),
            )
        )
        if any(
            upstream.get(key) is not False
            for key in (
                "automatic_truth_promotion",
                "automatic_schema_promotion",
                "automatic_pdf_confidence_promotion",
            )
        ):
            errors.append("E-0013 upstream promotion safety gate drift")
    else:
        errors.append("E-0013 has no upstream reader identity")
    for name, record in identities:
        if not isinstance(record, dict):
            errors.append(f"E-0013 {name} identity is invalid")
            continue
        local_path = _safe_project_file(project_root, record.get("path"))
        if (
            local_path is None
            or not local_path.is_file()
            or sha256_file(local_path) != record.get("sha256")
        ):
            errors.append(f"E-0013 {name} hash drift")

    # Immutable E-0013 calibration expectations; these are audit assertions,
    # never document-routing rules for an unseen filing.
    expected_contracts = {
        "MBB_2025_CONSOLIDATED": {
            "eligible": {"CDKT": [10, 11], "KQKD": [13], "LCTT": [14, 15]},
            "excluded": [12],
            "notes_boundary": 16,
        },
        "VCB_2025_CONSOLIDATED": {
            "eligible": {"CDKT": [8, 9], "KQKD": [11, 12], "LCTT": [13, 14]},
            "excluded": [10],
            "notes_boundary": 15,
        },
    }
    documents = artifact.get("documents")
    if not isinstance(documents, list) or len(documents) != len(expected_contracts):
        errors.append("E-0013 document set drift")
        documents = []
    elif {record.get("key") for record in documents if isinstance(record, dict)} != set(
        expected_contracts
    ):
        errors.append("E-0013 document identity set drift")

    local_artifacts: list[dict[str, object]] = []
    document_summaries: list[dict[str, object]] = []
    for document in documents:
        if not isinstance(document, dict):
            errors.append("E-0013 document record is invalid")
            continue
        key = str(document.get("key", ""))
        contract = expected_contracts.get(key)
        if contract is None:
            continue
        source = document.get("source")
        preprocess = document.get("preprocess_manifest")
        batch = document.get("ocr_batch")
        location = document.get("location_output")
        result = document.get("result")
        if not all(
            isinstance(record, dict) for record in (source, preprocess, batch, location, result)
        ):
            errors.append(f"E-0013 {key} identity/result structure drift")
            continue
        assert isinstance(source, dict)
        assert isinstance(preprocess, dict)
        assert isinstance(batch, dict)
        assert isinstance(location, dict)
        assert isinstance(result, dict)

        if source.get("dataset_role_frozen") is not True:
            errors.append(f"E-0013 {key} dataset-role gate drift")
        if preprocess.get("dpi") != 120:
            errors.append(f"E-0013 {key} coarse-render DPI drift")
        if (
            batch.get("checkpoint_state") != "PARTIAL"
            or batch.get("completed_pages") != 18
            or not isinstance(batch.get("requested_pages"), int)
            or batch["requested_pages"] <= batch["completed_pages"]
        ):
            errors.append(f"E-0013 {key} adaptive-batch boundary drift")
        if location.get("state") != "STATEMENT_LOCATION_COMPLETE":
            errors.append(f"E-0013 {key} location state drift")

        eligible = result.get("mapping_eligible_pages_by_statement_type")
        excluded = result.get("off_balance_excluded_pages")
        cash_flow = result.get("cash_flow")
        if (
            eligible != contract["eligible"]
            or excluded != contract["excluded"]
            or result.get("notes_boundary_page") != contract["notes_boundary"]
            or result.get("interstitial_pages") != []
            or result.get("candidate_count") != 2
            or result.get("winner_runner_up_margin") != 2.0
        ):
            errors.append(f"E-0013 {key} page/scope contract drift")
        ordered_anchors = cash_flow.get("ordered_anchors") if isinstance(cash_flow, dict) else None
        if not isinstance(cash_flow, dict) or (
            cash_flow.get("pdf_method") != "DIRECT"
            or cash_flow.get("indirect_sequence_complete") is not False
            or cash_flow.get("schema_branch_assignment_permitted") is not False
            or not isinstance(ordered_anchors, list)
            or len(ordered_anchors) != 2
        ):
            errors.append(f"E-0013 {key} cash-flow evidence gate drift")

        candidate_records: list[tuple[str, dict[str, object]]] = [
            (f"{key}:source", source),
            (f"{key}:preprocess_manifest", preprocess),
            (
                f"{key}:batch_manifest",
                {
                    "path": f"{batch.get('path', '')}/batch_manifest.json",
                    "sha256": batch.get("manifest_sha256"),
                },
            ),
            (f"{key}:location_output", location),
        ]
        for name, record in candidate_records:
            local_path = _safe_project_file(project_root, record.get("path"))
            if local_path is None:
                errors.append(f"E-0013 local artifact path is invalid: {name}")
            present = local_path is not None and local_path.is_file()
            verified = present and sha256_file(local_path) == record.get("sha256")
            local_artifacts.append({"name": name, "present": present, "verified": verified})
            if present and not verified:
                errors.append(f"local E-0013 artifact hash drift: {name}")

        location_path = _safe_project_file(project_root, location.get("path"))
        if location_path is not None and location_path.is_file():
            try:
                local_output = json.loads(location_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                errors.append(f"cannot read local E-0013 output {key}: {exc}")
            else:
                local_result = local_output.get("result", {})
                local_block = (
                    local_result.get("block", {}) if isinstance(local_result, dict) else {}
                )
                local_cash_flow = (
                    local_result.get("cash_flow", {}) if isinstance(local_result, dict) else {}
                )
                if (
                    local_output.get("state") != "STATEMENT_LOCATION_COMPLETE"
                    or local_output.get("code") != {"commit": recorded_commit, "dirty": False}
                    or local_result.get("errors") != []
                    or local_result.get("runner_up_margin") != 2.0
                    or local_block.get("mapping_eligible_pages_by_statement_type")
                    != contract["eligible"]
                    or local_block.get("off_balance_excluded_pages") != contract["excluded"]
                    or local_cash_flow.get("method") != "DIRECT"
                    or local_cash_flow.get("schema_branch_assignment_permitted") is not False
                ):
                    errors.append(f"local E-0013 output contract drift: {key}")

        document_summaries.append(
            {
                "key": key,
                "eligible_pages": eligible,
                "off_balance_excluded_pages": excluded,
                "notes_boundary_page": result.get("notes_boundary_page"),
                "cash_flow_method": (
                    cash_flow.get("pdf_method") if isinstance(cash_flow, dict) else None
                ),
            }
        )

    checks = artifact.get("cross_document_checks")
    required_checks = {
        "same_algorithm_and_configuration": True,
        "bank_name_or_page_rule_in_algorithm": False,
        "ordered_form_sequence_passed": True,
        "unknown_interstitial_pages": 0,
        "off_balance_pages_mapping_eligible": 0,
        "scope_crossing_continuation_links": 0,
        "direct_title_and_ordered_anchor_agreement": 2,
        "cash_flow_schema_assignment_attempts": 0,
        "historical_reference_invoked": False,
        "arithmetic_value_generation_invoked": False,
        "ytd_derivation_invoked": False,
    }
    if not isinstance(checks, dict) or any(
        checks.get(key) != value for key, value in required_checks.items()
    ):
        errors.append("E-0013 cross-document safety gate drift")
    acceptance = artifact.get("acceptance")
    if not isinstance(acceptance, dict) or (
        acceptance.get("cash_flow_schema_branch_assignment") != "BLOCKED_BY_Q_BOOT_001"
        or acceptance.get("row_or_schema_mapping_evaluated") is not False
        or acceptance.get("human_gold_evaluated") is not False
        or acceptance.get("production_accuracy_approved") is not False
    ):
        errors.append("E-0013 claim boundary drift")
    report_norm = artifact.get("report_norm_id")
    if artifact.get("software_or_model_change") is not False:
        errors.append("E-0013 unexpectedly records a software/model change")
    if not isinstance(report_norm, dict) or report_norm.get("ids_proposed_or_added") != 0:
        errors.append("E-0013 unexpectedly proposes ReportNormID changes")

    local_count = sum(bool(record["present"]) for record in local_artifacts)
    verified_count = sum(bool(record["verified"]) for record in local_artifacts)
    if errors:
        integrity_status = "FAIL"
    elif local_count:
        integrity_status = "PASS_TRACKED_AND_LOCAL_ARTIFACTS"
    else:
        integrity_status = "PASS_TRACKED_ARTIFACT"
    return {
        "integrity_status": integrity_status,
        "artifact": artifact_path.as_posix(),
        "artifact_sha256": sha256_file(absolute_artifact),
        "experiment_id": artifact.get("experiment_id"),
        "recorded_status": artifact.get("status"),
        "dataset_role": artifact.get("dataset_role"),
        "design": artifact.get("design"),
        "code_commit": recorded_commit,
        "claim_boundary": artifact.get("claim_boundary"),
        "documents": document_summaries,
        "document_count": len(document_summaries),
        "cross_document_checks": checks,
        "acceptance": acceptance,
        "local_artifacts": local_artifacts,
        "local_artifact_count": local_count,
        "verified_local_artifact_count": verified_count,
        "errors": errors,
    }


def _write_dynamic_audits(
    project_root: Path,
    environment: dict[str, object],
    manifest: dict[str, object],
    backup: dict[str, object],
    questions: list[dict[str, object]],
) -> None:
    gpu = environment["gpu"]
    devices = gpu.get("devices", []) if isinstance(gpu, dict) else []
    gpu_text = (
        ", ".join(
            f"{item['name']} ({item['memory_total_mib']} MiB, compute {item['compute_capability']})"
            for item in devices
        )
        or "Not detected"
    )
    memory = environment.get("memory", {})
    total_ram = int(memory.get("MemTotal", 0)) if isinstance(memory, dict) else 0
    disk = environment.get("disk", {})
    torch = environment.get("torch", {})
    torch_available = isinstance(torch, dict) and bool(torch.get("available"))
    torch_text = (
        f"{torch.get('version')} (build CUDA {torch.get('cuda_build')})"
        if torch_available
        else "not installed in the control-plane interpreter"
    )
    torch_finding = (
        f"The control-plane interpreter exposes architectures `{torch.get('architectures', [])}`. "
        "It is not the document-model environment of record."
        if torch_available
        else "The control-plane environment intentionally has no PyTorch; model dependencies "
        "remain isolated from orchestration and validation code."
    )
    gpu_runtime = environment.get("gpu_model_runtime", {})
    gpu_runtime = gpu_runtime if isinstance(gpu_runtime, dict) else {}
    runtime_status = str(gpu_runtime.get("local_acceptance", "NOT_CONFIGURED"))
    runtime_smoke = gpu_runtime.get("smoke", {})
    runtime_smoke = runtime_smoke if isinstance(runtime_smoke, dict) else {}
    runtime_freeze = gpu_runtime.get("freeze", {})
    runtime_freeze = runtime_freeze if isinstance(runtime_freeze, dict) else {}
    runtime_packages = gpu_runtime.get("declared_packages", {})
    runtime_packages = runtime_packages if isinstance(runtime_packages, dict) else {}
    if runtime_status == "PASS":
        runtime_text = (
            f"PASS — PyTorch {runtime_packages.get('torch', 'unknown')}, "
            f"CUDA {runtime_smoke.get('torch_cuda_build', 'unknown')}, "
            f"native {gpu_runtime.get('required_native_arch', 'unknown')}, "
            f"{runtime_freeze.get('installed_package_count', 'unknown')}-package exact freeze"
        )
        runtime_finding = (
            "The isolated runtime was revalidated on this host: imports and dependency "
            "compatibility passed, the installed freeze exactly matched the tracked freeze, "
            "and a real CUDA matrix kernel ran on the detected GPU."
        )
    elif runtime_status == "ABSENT":
        runtime_text = "ABSENT — rebuild required from the tracked runtime manifest"
        runtime_finding = (
            "The isolated runtime is not present on this host. Rebuild and rerun the acceptance "
            "commands in `docs/environment/GPU_RUNTIME_RUNBOOK.md` before model inference."
        )
    else:
        runtime_text = f"{runtime_status} — local acceptance did not pass"
        runtime_finding = (
            "The isolated runtime did not satisfy every fail-closed acceptance check. Inspect "
            "`environment.gpu_model_runtime` in `BOOTSTRAP_MANIFEST.json` before inference."
        )
    schema_counts = manifest["schemas"]["counts"]
    resolved_questions = sum(
        str(question.get("resolution_status", "")).startswith("RESOLVED") for question in questions
    )
    dump_registry = manifest.get("mongodb", {}).get("dump_registry")
    historical_reference = manifest.get("mongodb", {}).get("historical_weak_reference", {})
    historical_reference = historical_reference if isinstance(historical_reference, dict) else {}
    if isinstance(dump_registry, dict):
        if historical_reference.get("status") == "PASS":
            history_finding = (
                "The local historical weak-reference index was revalidated at "
                f"{historical_reference.get('row_count')} cells across "
                f"{historical_reference.get('bank_count')} banks. Its database constraints "
                "forbid mapping and confidence promotion."
            )
            mongo_progress = (
                f"PASS weak-reference-only ({historical_reference.get('row_count')} cells; "
                f"{historical_reference.get('bank_count')} banks)"
            )
        else:
            history_finding = (
                "The historical weak-reference index status is "
                f"`{historical_reference.get('status', 'NOT_CONFIGURED')}` and it is disabled."
            )
            mongo_progress = (
                "disabled; local historical weak-reference verification status="
                f"{historical_reference.get('status', 'NOT_CONFIGURED')}"
            )
        mongo_finding = (
            "The uploaded MongoDB archive is hash-registered. The allowlisted "
            f"financial template audit contains {dump_registry['restored_scope']['document_count']} "
            "documents and found no ReportNormID 1944 collision. "
            f"{history_finding}"
        )
    else:
        mongo_finding = (
            "No registered MongoDB archive audit is available; Mongo-assisted mode is disabled."
        )
        mongo_progress = "unavailable; MongoDB archive not audited"
    calibration = manifest.get("calibration", {})
    calibration = calibration if isinstance(calibration, dict) else {}
    calibration_metrics = calibration.get("metrics", {})
    calibration_metrics = calibration_metrics if isinstance(calibration_metrics, dict) else {}
    calibration_status = str(calibration.get("integrity_status", "NOT_AVAILABLE"))
    if calibration_status.startswith("PASS"):
        strict_rows = float(
            calibration_metrics.get("strict_exact_reference_financial_row_agreement_rate", 0.0)
        )
        strict_cells = float(
            calibration_metrics.get("strict_exact_reference_cell_agreement_rate", 0.0)
        )
        coverage = float(calibration_metrics.get("reference_financial_row_coverage_rate", 0.0))
        calibration_progress = (
            f"E-0010 {calibration_status}; strict rows={strict_rows:.2%}, "
            f"strict cells={strict_cells:.2%}, reference coverage={coverage:.2%}, "
            f"auto-high={calibration.get('acceptance', {}).get('auto_verified_high', 'unknown')}"
        )
        calibration_finding = (
            f"Tracked E-0010 calibration integrity is **{calibration_status}**; "
            f"{calibration.get('verified_local_seal_count', 0)}/"
            f"{calibration.get('local_seal_count', 0)} locally present seals verify. "
            "It remains machine-reference calibration, not production accuracy."
        )
    else:
        calibration_progress = f"{calibration_status}; errors={calibration.get('errors', [])}"
        calibration_finding = (
            f"Tracked E-0010 calibration integrity is **{calibration_status}**; "
            "its metrics are disabled until the recorded hashes verify."
        )
    geometry_recovery = manifest.get("geometry_recovery", {})
    geometry_recovery = geometry_recovery if isinstance(geometry_recovery, dict) else {}
    geometry_metrics = geometry_recovery.get("metrics", {})
    geometry_metrics = geometry_metrics if isinstance(geometry_metrics, dict) else {}
    geometry_status = str(geometry_recovery.get("integrity_status", "NOT_AVAILABLE"))
    if geometry_status.startswith("PASS"):
        strict_geometry_rows = float(
            geometry_metrics.get("strict_exact_reference_financial_row_agreement_rate", 0.0)
        )
        strict_geometry_cells = float(
            geometry_metrics.get("strict_exact_reference_cell_agreement_rate", 0.0)
        )
        geometry_coverage = float(
            geometry_metrics.get("reference_financial_row_coverage_rate", 0.0)
        )
        geometry_progress = (
            f"E-0011 {geometry_status}; strict rows={strict_geometry_rows:.2%}, "
            f"strict cells={strict_geometry_cells:.2%}, "
            f"reference coverage={geometry_coverage:.2%}, "
            f"auto-high={geometry_recovery.get('acceptance', {}).get('auto_verified_high', 'unknown')}"
        )
        geometry_finding = (
            f"Tracked E-0011 targeted geometry-recovery integrity is **{geometry_status}**; "
            f"{geometry_recovery.get('verified_local_seal_count', 0)}/"
            f"{geometry_recovery.get('local_seal_count', 0)} locally present seals verify. "
            "It remains post-failure machine-reference calibration, not production accuracy."
        )
    else:
        geometry_progress = f"{geometry_status}; errors={geometry_recovery.get('errors', [])}"
        geometry_finding = (
            f"Tracked E-0011 targeted geometry-recovery integrity is **{geometry_status}**; "
            "its metrics are disabled until the recorded hashes verify."
        )
    batch_mechanism = manifest.get("batch_mechanism", {})
    batch_mechanism = batch_mechanism if isinstance(batch_mechanism, dict) else {}
    batch_metrics = batch_mechanism.get("metrics", {})
    batch_metrics = batch_metrics if isinstance(batch_metrics, dict) else {}
    batch_status = str(batch_mechanism.get("integrity_status", "NOT_AVAILABLE"))
    if batch_status.startswith("PASS"):
        batch_progress = (
            f"E-0012 {batch_status}; pages={batch_metrics.get('completed_page_count', 0)}, "
            f"lines={batch_metrics.get('line_count', 0)}, "
            f"words={batch_metrics.get('word_token_count', 0)}, "
            f"model-load sessions={batch_metrics.get('model_load_session_count', 0)}, "
            f"byte-identical={batch_mechanism.get('equivalence', {}).get('byte_identical')}"
        )
        batch_finding = (
            f"Tracked E-0012 batch/checkpoint integrity is **{batch_status}**; "
            f"{batch_mechanism.get('verified_local_artifact_count', 0)}/"
            f"{batch_mechanism.get('local_artifact_count', 0)} locally present artifacts "
            "verify. It is a mechanism regression on an existing page, not a new accuracy "
            "sample."
        )
    else:
        batch_progress = f"{batch_status}; errors={batch_mechanism.get('errors', [])}"
        batch_finding = (
            f"Tracked E-0012 batch/checkpoint integrity is **{batch_status}**; "
            "batch evidence is disabled until the recorded hashes verify."
        )
    statement_location = manifest.get("statement_location", {})
    statement_location = statement_location if isinstance(statement_location, dict) else {}
    location_status = str(statement_location.get("integrity_status", "NOT_AVAILABLE"))
    location_documents = statement_location.get("documents", [])
    location_documents = location_documents if isinstance(location_documents, list) else []
    if location_status.startswith("PASS"):
        location_contracts = []
        for document in location_documents:
            if not isinstance(document, dict):
                continue
            short_key = str(document.get("key", "unknown")).split("_")[0]
            eligible = document.get("eligible_pages", {})
            eligible = eligible if isinstance(eligible, dict) else {}
            location_contracts.append(
                f"{short_key} CDKT={eligible.get('CDKT', [])}, "
                f"KQKD={eligible.get('KQKD', [])}, LCTT={eligible.get('LCTT', [])}, "
                f"excluded={document.get('off_balance_excluded_pages', [])}"
            )
        location_progress = f"E-0013 {location_status}; " + "; ".join(location_contracts)
        location_finding = (
            f"Tracked E-0013 ordered statement-location integrity is "
            f"**{location_status}**; "
            f"{statement_location.get('verified_local_artifact_count', 0)}/"
            f"{statement_location.get('local_artifact_count', 0)} locally present "
            "source/preprocess/batch/result artifacts verify. It remains page/scope "
            "calibration, not row/schema/numeric or production accuracy."
        )
    else:
        location_progress = f"{location_status}; errors={statement_location.get('errors', [])}"
        location_finding = (
            f"Tracked E-0013 ordered statement-location integrity is "
            f"**{location_status}**; its page contracts are disabled until the "
            "recorded hashes and safety gates verify."
        )
    hardware = f"""# Hardware audit

Captured: {environment["captured_at"]}

- Host: `{environment["hostname"]}`
- OS: {environment["os"].get("PRETTY_NAME", "unknown")}; kernel `{environment["kernel"]}`
- CPU: {environment["cpu"].get("model")} ({environment["cpu"].get("logical_count")} logical CPUs)
- RAM: {total_ram / (1024**3):.2f} GiB; swap: {int(memory.get("SwapTotal", 0)) / (1024**3):.2f} GiB
- Workspace disk: {int(disk.get("total_bytes", 0)) / (1024**3):.2f} GiB total, {int(disk.get("free_bytes", 0)) / (1024**3):.2f} GiB free
- GPU: {gpu_text}
- NVIDIA driver: {devices[0]["driver_version"] if devices else "not detected"}
- Driver-reported CUDA: {gpu.get("reported_cuda") if isinstance(gpu, dict) else None}
- CUDA toolkit (`nvcc`): {"available" if environment["tools"]["nvcc"]["available"] else "not installed"}
- Python: {environment["tools"]["python"]["version"]}
- PyTorch: {torch_text}
- Isolated GPU runtime: {runtime_text}
- Recorded document-model status: `{gpu_runtime.get("declared_status", "NOT_CONFIGURED")}`

## Compatibility and approval finding

{torch_finding} {runtime_finding} This accepts the runtime for logic development; production model approval remains blocked until frozen multi-institution, scan/distortion, cross-page, and holdout accuracy gates pass.
"""
    atomic_write_text(project_root / "HARDWARE_AUDIT.md", hardware)

    recovery = f"""# Recovery audit

Captured: {environment["captured_at"]}

## Authoritative starting state

- The old server/GPU state is treated as unrecoverable and was not searched.
- Existing repository history contains only the newly supplied input workbooks; no prior Python implementation or OCR artifacts were present.
- Inputs found: **{manifest["sources"]["pdf_count"]} PDFs** ({manifest["sources"]["total_bytes"]} bytes), four schema workbooks, four supporting hierarchy workbooks, and one bank-list workbook.
- PDF registry hash: `{manifest["sources"]["registry_hash"]}`.
- SchemaGraph hash: `{manifest["schemas"]["graph_hash"]}`.
- Supporting hierarchy status: `{manifest["schemas"]["hierarchy_reference"]["status"]}` with {manifest["schemas"]["hierarchy_reference"]["item_count"]} validated edges/items; LCTT coverage is explicitly direct-branch-only.
- Source files were read and hashed only; none were overwritten.
- Inventory stable across registration: **{manifest["sources"]["inventory_stable"]}** (attempts: {manifest["sources"]["inventory_attempts"]}).
- Isolated GPU runtime local acceptance: **{runtime_status}**; production model approval remains separate and pending.

## Material discrepancies

- Actual schema counts are CDKT={schema_counts["CDKT"]}, KQKD={schema_counts["KQKD"]}, LCTT={schema_counts["LCTT"]}, TM={schema_counts["TM"]} (total {manifest["schemas"]["total_items"]}), not the historical 1,773-item count.
- The supplied TM workbook does not contain ID 1944. It remains a proposal in `proposed_schema_additions.jsonl`.
- Q-BOOT-001 is resolved: LCTT membership uses contiguous workbook positions, never numeric ID ranges. Template-order block 4155→4168 is INDIRECT and 4104→4116 is DIRECT; historical frozen artifacts retain their earlier fail-closed flag.
- {mongo_finding}
- {calibration_finding}
- {geometry_finding}
- {batch_finding}
- {location_finding}
- A local control-plane backup restored successfully: `{backup["restored_and_verified"]}`. Per the user's development policy, development backup status is **{backup["development_status"]}**. It is not off-machine and does not protect against total VPS loss; production status remains `{backup["production_status"]}`.

## Recovery posture

Generated artifacts use atomic write, fsync, rename, and post-write hash verification. Source identity is recorded in `data/registered/source_registry.jsonl`; content-addressed artifact materialization and off-machine versioning remain required before production.
"""
    atomic_write_text(project_root / "RECOVERY_AUDIT.md", recovery)

    progress = f"""# Progress report

- Date/time: {environment["captured_at"]}
- Hardware: {gpu_text}; {total_ram / (1024**3):.2f} GiB RAM
- Isolated GPU runtime: {runtime_status}; recorded model state: `{gpu_runtime.get("declared_status", "NOT_CONFIGURED")}`
- Code hash: bootstrap is on `{manifest["git"]["branch"]}` at `{manifest["git"]["commit"]}` with dirty state `{manifest["git"]["dirty"]}`
- Schema count: {manifest["schemas"]["total_items"]} (CDKT {schema_counts["CDKT"]}; KQKD {schema_counts["KQKD"]}; LCTT {schema_counts["LCTT"]}; TM {schema_counts["TM"]})
- PDFs registered: {manifest["sources"]["pdf_count"]}
- ROLE A completed: 0 documents
- ROLE B completed: 0 documents
- Reference IDs / values: 0 / 0
- CDKT, KQKD, applicable LCTT, TM coverage: not measurable before MACHINE_REFERENCE
- PDF_ONLY metrics: not yet measured
- Frozen cross-reader calibration: {calibration_progress}
- Targeted independent geometry recovery: {geometry_progress}
- Batch/checkpoint mechanism: {batch_progress}
- Ordered statement location: {location_progress}
- Mongo-assisted metrics: {mongo_progress}
- Questions created / resolved: {len(questions)} / {resolved_questions}
- Autonomous decisions: preserve supplied schema unchanged; keep 1944 as a collision-cleared proposal; apply the user-confirmed LCTT branch names by workbook position through policy v2
- Not applicable / not observed / unresolved: 0 / 0 / 0 (no production records yet)
- Workbooks: 0
- Largest error: no frozen end-to-end multi-institution accuracy result or production-calibrated acceptance threshold yet
- Last change: locked and bootstrap-audited clean E-0013 MBB/VCB page/type/scope evidence without claiming row/schema/numeric or production accuracy
- Before/after on the targeted TCB calibration: strict reference coverage/cell agreement 94.70%/92.42% -> 100%/100%; Role C label exactness remains only 3/140
- Regression: run separately with `.venv/bin/pytest`; latest verified count is recorded in `PROJECT_MEMORY.md`
- Backup status: development={backup["development_status"]}; production={backup["production_status"]} (local restore verified={backup["restored_and_verified"]}, off-machine={backup["off_machine"]})
- Next bounded action: rerender only the E-0013 eligible pages plus exclusion boundaries at 200 DPI, run the frozen Role B/Role C row gates unchanged, then continue to controlled distortions and an untouched holdout
"""
    atomic_write_text(project_root / "PROGRESS_REPORT.md", progress)


def run_bootstrap(project_root: Path, *, workers: int = 4) -> BootstrapResult:
    project_root = project_root.resolve()
    git_state = {
        "commit": _git(project_root, "rev-parse", "HEAD"),
        "branch": _git(project_root, "branch", "--show-current"),
        "dirty": bool(_git(project_root, "status", "--porcelain")),
        "remotes": (_git(project_root, "remote") or "").splitlines(),
    }
    environment = collect_environment(project_root)
    historical_weak_reference = verify_historical_weak_reference(project_root)
    source_root = project_root / "vietstock_bctc"
    inventory_stable = False
    inventory_attempts = 0
    added_during_registration: list[str] = []
    removed_during_registration: list[str] = []
    source_records = []
    registry_hash = ""
    for attempt in range(1, 4):
        inventory_attempts = attempt
        sources = discover_pdfs(source_root)
        source_records, registry_hash = register_sources(
            sources,
            project_root,
            project_root / "data/registered/source_registry.jsonl",
            workers=workers,
        )
        after = discover_pdfs(source_root)
        before_paths = {source.path.resolve() for source in sources}
        after_paths = {source.path.resolve() for source in after}
        added_during_registration = sorted(
            path.relative_to(project_root).as_posix() for path in after_paths - before_paths
        )
        removed_during_registration = sorted(
            path.relative_to(project_root).as_posix() for path in before_paths - after_paths
        )
        inventory_stable = (
            not added_during_registration
            and not removed_during_registration
            and all(record.hash_verified_stable for record in source_records)
        )
        if inventory_stable:
            break
    workbooks, schema_count, graph_hash, hierarchy_reference = _write_schema_artifacts(project_root)
    _write_schema_proposal(project_root, historical_weak_reference)
    questions = bootstrap_questions()
    write_questions(project_root, questions)

    bank_list = project_root / "Bank_list_id.xlsx"
    bank_registry = load_bank_registry(bank_list, project_root)
    atomic_write_json(project_root / "data/registered/bank_registry.json", bank_registry)
    manifest: dict[str, object] = {
        "format_version": 1,
        "project": "bctc-ai",
        "captured_at": datetime.now(UTC).isoformat(),
        "git": git_state,
        "environment": environment,
        "sources": {
            "pdf_count": len(source_records),
            "unique_content_count": len({record.sha256 for record in source_records}),
            "total_bytes": sum(record.size_bytes for record in source_records),
            "registry": "data/registered/source_registry.jsonl",
            "registry_hash": registry_hash,
            "inventory_stable": inventory_stable,
            "inventory_attempts": inventory_attempts,
            "added_during_registration": added_during_registration,
            "removed_during_registration": removed_during_registration,
            "unstable_file_count": sum(
                not record.hash_verified_stable for record in source_records
            ),
        },
        "schemas": {
            "workbooks": workbooks,
            "counts": {record["statement_type"]: record["item_count"] for record in workbooks},
            "total_items": schema_count,
            "graph": "reference/schemas/schema_graph.jsonl",
            "graph_hash": graph_hash,
            "contains_tm_1944": False,
            "lctt_semantics": "WORKBOOK_BLOCKS_VERIFIED_SEMANTIC_CONFLICT_REOPENED_2026_08_05",
            "hierarchy_reference": hierarchy_reference,
        },
        "bank_list": {
            "path": "Bank_list_id.xlsx",
            "sha256": sha256_file(bank_list),
            "size_bytes": bank_list.stat().st_size,
            "registry": "data/registered/bank_registry.json",
            "counts": bank_registry["counts"],
        },
        "mongodb": {
            "runtime": environment["mongodb"],
            "dump_registry": (
                json.loads(
                    (project_root / "data/registered/mongodb_dump_registry.json").read_text(
                        encoding="utf-8"
                    )
                )
                if (project_root / "data/registered/mongodb_dump_registry.json").is_file()
                else None
            ),
            "historical_weak_reference": historical_weak_reference,
        },
        "calibration": _load_calibration_summary(project_root),
        "geometry_recovery": _load_geometry_recovery_summary(project_root),
        "batch_mechanism": _load_batch_mechanism_summary(project_root),
        "statement_location": _load_statement_location_summary(project_root),
    }
    atomic_write_json(project_root / "BOOTSTRAP_MANIFEST.json", manifest)

    backup_root = project_root.parent / "bctc-ai-backups"
    backup_result = create_backup(project_root, backup_root, off_machine=False)
    backup = {
        **asdict(backup_result),
        "development_status": backup_result.development_status,
        "production_status": backup_result.production_status,
    }
    manifest["backup"] = backup
    atomic_write_json(project_root / "BOOTSTRAP_MANIFEST.json", manifest)
    _write_dynamic_audits(project_root, environment, manifest, backup, questions)
    return BootstrapResult(
        recovery_audit=str((project_root / "RECOVERY_AUDIT.md").resolve()),
        project_goal=str((project_root / "PROJECT_GOAL.md").resolve()),
        questions=str((project_root / "questions_for_user.md").resolve()),
        backup_status=f"{backup_result.development_status}_DEVELOPMENT",
    )
