from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.document_phase.multisignal_statement_discovery import (
    discover_statement_pages,
    load_multisignal_statement_config,
)
from bctc_ai.document_phase.statement_evidence import load_ocr_pages_from_batch


class CalibrationDiscoveryControlError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationDiscoveryControlError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise CalibrationDiscoveryControlError(f"{name} must be an object")
    return payload


def _load_yaml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CalibrationDiscoveryControlError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise CalibrationDiscoveryControlError(f"{name} must be an object")
    return payload


def _resolve(project_root: Path, value: str | Path, name: str) -> Path:
    path = (project_root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    if not path.is_relative_to(project_root):
        raise CalibrationDiscoveryControlError(f"{name} escapes project root")
    return path


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CalibrationDiscoveryControlError(f"required artifact is absent: {path}")
    return {
        "path": path.resolve().relative_to(project_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def summarize_discovery_result(result: dict[str, Any]) -> dict[str, Any]:
    local_acceptances: list[dict[str, Any]] = []
    for page_record in result.get("page_signals", []):
        if not isinstance(page_record, dict):
            continue
        for candidate in page_record.get("candidates", []):
            if not isinstance(candidate, dict) or not candidate.get("locally_accepted"):
                continue
            local_acceptances.append(
                {
                    "page": page_record.get("page"),
                    "statement_type": candidate.get("page_type"),
                    "scope": candidate.get("scope"),
                    "score": candidate.get("score"),
                    "independent_signal_groups": candidate.get(
                        "independent_signal_groups", []
                    ),
                    "accounting_hit_count": len(candidate.get("accounting_hits", [])),
                }
            )
    notes_candidates = []
    for page_record in result.get("page_signals", []):
        if not isinstance(page_record, dict):
            continue
        candidate = next(
            (
                item
                for item in page_record.get("candidates", [])
                if isinstance(item, dict) and item.get("page_type") == "TM"
            ),
            None,
        )
        if isinstance(candidate, dict) and float(candidate.get("score", 0.0)) > 0.0:
            notes_candidates.append(
                {
                    "page": page_record.get("page"),
                    "score": candidate.get("score"),
                    "locally_accepted": bool(candidate.get("locally_accepted")),
                    "independent_signal_groups": candidate.get(
                        "independent_signal_groups", []
                    ),
                    "accounting_hit_count": len(candidate.get("accounting_hits", [])),
                }
            )
    return {
        "status": result.get("status"),
        "algorithm_revision": result.get("algorithm_revision"),
        "candidate_path_count": result.get("candidate_path_count"),
        "runner_up_margin": result.get("runner_up_margin"),
        "errors": result.get("errors", []),
        "local_acceptances": local_acceptances,
        "notes_candidates": notes_candidates,
        "mapping_eligible_page_count": sum(
            len(pages)
            for pages in (
                result.get("block", {}).get(
                    "mapping_eligible_pages_by_statement_type", {}
                ).values()
                if isinstance(result.get("block"), dict)
                else []
            )
        ),
    }


def capture_e0027_role_b_discovery(
    project_root: Path,
    *,
    experiment_config_path: Path,
    batch_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise CalibrationDiscoveryControlError(
            "formal E-0027 Role B discovery capture requires clean Git code"
        )
    output = _resolve(project_root, output_path, "output")
    experiments_root = (project_root / "docs" / "experiments").resolve()
    if not output.is_relative_to(experiments_root):
        raise CalibrationDiscoveryControlError("output must remain in docs/experiments")
    if output.exists():
        raise CalibrationDiscoveryControlError(f"refusing to overwrite capture: {output}")

    experiment_path = _resolve(project_root, experiment_config_path, "experiment config")
    experiment = _load_yaml(experiment_path, "E-0027 experiment config")
    if (
        experiment.get("version") != 1
        or experiment.get("experiment_id") != "E-0027"
        or experiment.get("dataset_role") != "CALIBRATION"
    ):
        raise CalibrationDiscoveryControlError("E-0027 experiment identity drifted")

    source_record = experiment.get("source")
    if not isinstance(source_record, dict):
        raise CalibrationDiscoveryControlError("E-0027 source record is absent")
    source_path = _resolve(project_root, str(source_record.get("path", "")), "source")
    if (
        not source_path.is_file()
        or source_path.stat().st_size != int(source_record.get("size_bytes", -1))
        or sha256_file(source_path) != source_record.get("sha256")
    ):
        raise CalibrationDiscoveryControlError("E-0027 source identity drifted")

    frozen = experiment.get("frozen_components")
    if not isinstance(frozen, dict):
        raise CalibrationDiscoveryControlError("E-0027 frozen components are absent")
    component_records: dict[str, dict[str, Any]] = {}
    for name, record in frozen.items():
        if not isinstance(record, dict):
            raise CalibrationDiscoveryControlError(f"invalid frozen component: {name}")
        path = _resolve(project_root, str(record.get("path", "")), name)
        if not path.is_file() or sha256_file(path) != record.get("sha256"):
            raise CalibrationDiscoveryControlError(f"frozen component drifted: {name}")
        component_records[name] = _artifact(project_root, path)

    batch_path = _resolve(project_root, batch_root, "OCR batch")
    batch, geometry_pages = load_ocr_pages_from_batch(batch_path, project_root=project_root)
    expected_pages = list(
        range(
            int(source_record["input_page_window"]["start"]),
            int(source_record["input_page_window"]["end"]) + 1,
        )
    )
    if (
        batch.get("state") != "OCR_COMPLETE"
        or batch.get("dataset_role") != "CALIBRATION"
        or batch.get("requested_pages") != expected_pages
        or [page.page for page in geometry_pages] != expected_pages
        or batch.get("source")
        != {
            "path": source_record["path"],
            "sha256": source_record["sha256"],
            "size_bytes": source_record["size_bytes"],
        }
    ):
        raise CalibrationDiscoveryControlError("E-0027 OCR batch identity drifted")
    code = batch.get("code")
    if not isinstance(code, dict) or code.get("dirty") is not False:
        raise CalibrationDiscoveryControlError("E-0027 OCR batch was not generated cleanly")
    input_manifest = batch.get("input_manifest")
    if not isinstance(input_manifest, dict):
        raise CalibrationDiscoveryControlError("E-0027 preprocess manifest is absent")
    preprocess_path = _resolve(
        project_root, str(input_manifest.get("path", "")), "preprocess manifest"
    )
    if (
        not preprocess_path.is_file()
        or preprocess_path.stat().st_size != int(input_manifest.get("size_bytes", -1))
        or sha256_file(preprocess_path) != input_manifest.get("sha256")
    ):
        raise CalibrationDiscoveryControlError("E-0027 preprocess manifest drifted")

    locator_component = frozen.get("statement_discovery")
    if not isinstance(locator_component, dict):
        raise CalibrationDiscoveryControlError("statement-discovery component is absent")
    locator_path = _resolve(
        project_root, str(locator_component.get("path", "")), "statement-discovery config"
    )
    locator_config = load_multisignal_statement_config(locator_path)
    result = discover_statement_pages(geometry_pages, locator_config)
    if result.get("status") != "UNRESOLVED" or result.get("candidate_path_count") != 0:
        raise CalibrationDiscoveryControlError(
            "E-0027 v3 baseline is no longer the frozen unresolved outcome"
        )
    summary = summarize_discovery_result(result)

    payload = {
        "format_version": 1,
        "experiment_id": "E-0027",
        "state": "ROLE_B_DISCOVERY_V3_SEALED_UNRESOLVED",
        "dataset_role": "CALIBRATION",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "experiment_config": _artifact(project_root, experiment_path),
        "source": _artifact(project_root, source_path),
        "preprocess_manifest": _artifact(project_root, preprocess_path),
        "ocr_batch_manifest": _artifact(project_root, batch_path / "batch_manifest.json"),
        "ocr_batch_identity_sha256": batch.get("batch_identity"),
        "ocr_metrics": batch.get("metrics"),
        "frozen_components": component_records,
        "role_b_policy": {
            "human_review_loaded": False,
            "historical_values_loaded": False,
            "e0022_evidence_loaded": False,
            "semantic_reader_invoked": False,
            "mapping_invoked": False,
            "numeric_extraction_invoked": False,
            "excel_export_invoked": False,
        },
        "summary": summary,
        "discovery_result": result,
        "seal_implementation": _artifact(project_root, Path(__file__).resolve()),
        "allowed_next_action": (
            "PREDECLARE_BOUNDED_ORDERED_CORE_WINDOW_LOCATOR_CALIBRATION"
        ),
        "claim_boundary": (
            "This calibration seal records the reference-blind PP-OCRv6 geometry-only "
            "statement-discovery v3 result on the frozen E-0027 page prefix. It is a "
            "before-measurement, not a holdout or production accuracy claim."
        ),
    }
    atomic_write_json(output, payload)
    return payload
