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
from bctc_ai.document_phase.multisignal_statement_discovery_v4 import (
    discover_statement_pages_v4,
    load_multisignal_statement_config_v4,
)
from bctc_ai.document_phase.statement_evidence import load_ocr_pages_from_batch


class OrderedAnchorLocatorBenchmarkError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, value: str | Path, name: str) -> Path:
    value_path = Path(value)
    path = (
        (project_root / value_path).resolve()
        if not value_path.is_absolute()
        else value_path.resolve()
    )
    if not path.is_relative_to(project_root):
        raise OrderedAnchorLocatorBenchmarkError(f"{name} escapes project root")
    return path


def _load_json(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OrderedAnchorLocatorBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise OrderedAnchorLocatorBenchmarkError(f"{name} must be an object")
    return payload


def _load_yaml(path: Path, name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise OrderedAnchorLocatorBenchmarkError(f"cannot load {name}: {path}") from exc
    if not isinstance(payload, dict):
        raise OrderedAnchorLocatorBenchmarkError(f"{name} must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise OrderedAnchorLocatorBenchmarkError(f"required artifact is absent: {path}")
    return {
        "path": path.resolve().relative_to(project_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def structural_statement_summary(result: dict[str, Any]) -> dict[str, Any]:
    block = result.get("block") if isinstance(result.get("block"), dict) else {}
    cash_flow = result.get("cash_flow") if isinstance(result.get("cash_flow"), dict) else {}
    return {
        "status": result.get("status"),
        "mapping_eligible_pages_by_statement_type": block.get(
            "mapping_eligible_pages_by_statement_type"
        ),
        "off_balance_excluded_pages": block.get("off_balance_excluded_pages"),
        "notes_boundary_page": block.get("notes_boundary_page"),
        "runner_up_margin": result.get("runner_up_margin"),
        "cash_flow_method": cash_flow.get("method"),
    }


def _json_canonical(value: Any) -> Any:
    """Compare in-memory tuples with their immutable JSON artifact form."""

    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _verify_hash_record(
    project_root: Path, record: object, name: str
) -> tuple[Path, dict[str, Any]]:
    if not isinstance(record, dict):
        raise OrderedAnchorLocatorBenchmarkError(f"invalid frozen record: {name}")
    path = _resolve(project_root, str(record.get("path", "")), name)
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise OrderedAnchorLocatorBenchmarkError(f"frozen input drifted: {name}")
    return path, _artifact(project_root, path)


def _page_9_tm_added_anchor(result: dict[str, Any], anchor: str) -> dict[str, Any] | None:
    evidence = result.get("ordered_anchor_matching")
    if not isinstance(evidence, dict):
        return None
    for page in evidence.get("incremental_evidence", []):
        if not isinstance(page, dict) or page.get("page") != 9:
            continue
        for statement in page.get("statement_types", []):
            if not isinstance(statement, dict) or statement.get("statement_type") != "TM":
                continue
            if any(
                isinstance(hit, dict) and hit.get("anchor") == anchor
                for hit in statement.get("added_hits", [])
            ):
                return statement
    return None


def capture_e0028_ordered_anchor_benchmark(
    project_root: Path,
    *,
    experiment_config_path: Path,
    batch_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise OrderedAnchorLocatorBenchmarkError("formal E-0028 capture requires clean Git code")
    output = _resolve(project_root, output_path, "output")
    if not output.is_relative_to((project_root / "docs" / "experiments").resolve()):
        raise OrderedAnchorLocatorBenchmarkError("output must remain in docs/experiments")
    if output.exists():
        raise OrderedAnchorLocatorBenchmarkError(f"refusing to overwrite capture: {output}")

    experiment_path = _resolve(project_root, experiment_config_path, "experiment config")
    experiment = _load_yaml(experiment_path, "E-0028 experiment config")
    if (
        experiment.get("version") != 1
        or experiment.get("experiment_id") != "E-0028"
        or experiment.get("dataset_role") != "CALIBRATION"
    ):
        raise OrderedAnchorLocatorBenchmarkError("E-0028 experiment identity drifted")
    source = experiment.get("source")
    if not isinstance(source, dict):
        raise OrderedAnchorLocatorBenchmarkError("E-0028 source is absent")
    source_path = _resolve(project_root, str(source.get("path", "")), "source")
    if (
        not source_path.is_file()
        or source_path.stat().st_size != int(source.get("size_bytes", -1))
        or sha256_file(source_path) != source.get("sha256")
    ):
        raise OrderedAnchorLocatorBenchmarkError("E-0028 source identity drifted")

    verified: dict[str, dict[str, Any]] = {}
    frozen = experiment.get("frozen_inputs")
    candidate = experiment.get("candidate")
    if not isinstance(frozen, dict) or not isinstance(candidate, dict):
        raise OrderedAnchorLocatorBenchmarkError("E-0028 controls are incomplete")
    paths: dict[str, Path] = {}
    for name, record in frozen.items():
        paths[name], verified[name] = _verify_hash_record(project_root, record, name)
    for name in ("base_config", "config", "algorithm"):
        paths[name], verified[name] = _verify_hash_record(project_root, candidate.get(name), name)
    if candidate.get("only_change") != "ACCOUNTING_ROW_ANCHOR_SCORER_ONLY":
        raise OrderedAnchorLocatorBenchmarkError("E-0028 candidate change scope drifted")

    batch_path = _resolve(project_root, batch_root, "E-0027 OCR batch")
    if (batch_path / "batch_manifest.json").resolve() != paths["e0027_ocr_batch"]:
        raise OrderedAnchorLocatorBenchmarkError("E-0028 batch path differs from frozen input")
    batch, geometry_pages = load_ocr_pages_from_batch(batch_path, project_root=project_root)
    expected_pages = source.get("input_pages")
    if (
        batch.get("state") != "OCR_COMPLETE"
        or batch.get("dataset_role") != "CALIBRATION"
        or batch.get("requested_pages") != expected_pages
        or [page.page for page in geometry_pages] != expected_pages
        or batch.get("source")
        != {
            "path": source["path"],
            "sha256": source["sha256"],
            "size_bytes": source["size_bytes"],
        }
    ):
        raise OrderedAnchorLocatorBenchmarkError("E-0028 OCR batch identity drifted")

    baseline_artifact = _load_json(paths["e0027_v3_baseline"], "E-0027 baseline")
    if baseline_artifact.get("role_b_policy") != {
        "human_review_loaded": False,
        "historical_values_loaded": False,
        "e0022_evidence_loaded": False,
        "semantic_reader_invoked": False,
        "mapping_invoked": False,
        "numeric_extraction_invoked": False,
        "excel_export_invoked": False,
    }:
        raise OrderedAnchorLocatorBenchmarkError("E-0027 baseline isolation drifted")

    v3_config = load_multisignal_statement_config(paths["base_config"])
    v4_config = load_multisignal_statement_config_v4(paths["config"])
    before = discover_statement_pages(geometry_pages, v3_config)
    if _json_canonical(before) != baseline_artifact.get("discovery_result"):
        raise OrderedAnchorLocatorBenchmarkError("E-0027 V3 replay differs from sealed result")
    after = discover_statement_pages_v4(geometry_pages, v4_config)

    expected = experiment["expected_structure_from_reference_blind_v3_signals"]
    after_summary = structural_statement_summary(after)
    added = _page_9_tm_added_anchor(after, str(expected["added_page_9_tm_anchor"]))
    target_gates = {
        "v3_replay_equals_sealed_baseline": True,
        "v4_status_accepted": after.get("status") == experiment["acceptance_policy"]["v4_status"],
        "mapping_eligible_pages_exact": after_summary["mapping_eligible_pages_by_statement_type"]
        == expected["mapping_eligible_pages_by_statement_type"],
        "off_balance_exclusion_exact": after_summary["off_balance_excluded_pages"]
        == expected["off_balance_excluded_pages"],
        "notes_boundary_exact": after_summary["notes_boundary_page"]
        == expected["notes_boundary_page"],
        "runner_up_margin_clear": (
            after_summary["runner_up_margin"] is None
            or float(after_summary["runner_up_margin"])
            >= float(experiment["acceptance_policy"]["document_runner_up_margin_at_least"])
        ),
        "page_9_tm_anchor_added": isinstance(added, dict),
        "page_9_tm_has_minimum_anchor_count": (
            isinstance(added, dict)
            and int(added.get("extended_hit_count", 0))
            >= int(expected["page_9_tm_minimum_anchor_count"])
        ),
    }

    e0013 = _load_json(paths["e0013_no_regression"], "E-0013 no-regression source")
    no_regression = []
    for document in e0013.get("documents", []):
        if not isinstance(document, dict):
            raise OrderedAnchorLocatorBenchmarkError("E-0013 document record is invalid")
        ocr = document.get("ocr_batch")
        if not isinstance(ocr, dict):
            raise OrderedAnchorLocatorBenchmarkError("E-0013 OCR record is absent")
        document_batch = _resolve(project_root, str(ocr.get("path", "")), "E-0013 batch")
        if sha256_file(document_batch / "batch_manifest.json") != ocr.get("manifest_sha256"):
            raise OrderedAnchorLocatorBenchmarkError("E-0013 batch manifest drifted")
        loaded_batch, pages = load_ocr_pages_from_batch(document_batch, project_root=project_root)
        if loaded_batch.get("batch_identity") != ocr.get("identity_sha256"):
            raise OrderedAnchorLocatorBenchmarkError("E-0013 batch identity drifted")
        baseline_result = discover_statement_pages(pages, v3_config)
        candidate_result = discover_statement_pages_v4(pages, v4_config)
        baseline_summary = structural_statement_summary(baseline_result)
        candidate_summary = structural_statement_summary(candidate_result)
        no_regression.append(
            {
                "document": document.get("key"),
                "baseline": baseline_summary,
                "candidate": candidate_summary,
                "structural_exact_match": candidate_summary == baseline_summary,
            }
        )
    target_gates["e0013_mbb_vcb_structural_no_regression"] = all(
        item["structural_exact_match"] for item in no_regression
    )
    passed = all(target_gates.values())

    payload = {
        "format_version": 1,
        "experiment_id": "E-0028",
        "status": (
            "PASS_BOUNDED_ORDERED_ANCHOR_LOCATOR"
            if passed
            else "FAIL_BOUNDED_ORDERED_ANCHOR_LOCATOR"
        ),
        "dataset_role": "CALIBRATION",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "experiment_config": _artifact(project_root, experiment_path),
        "verified_inputs": verified,
        "source": _artifact(project_root, source_path),
        "ocr_batch_identity_sha256": batch.get("batch_identity"),
        "before": structural_statement_summary(before),
        "after": after_summary,
        "target_gates": target_gates,
        "page_9_tm_incremental_evidence": added,
        "cross_document_no_regression": no_regression,
        "candidate_result": after,
        "reference_isolation": {
            "human_review_loaded": False,
            "historical_values_loaded": False,
            "e0022_evidence_loaded": False,
            "semantic_reader_invoked": False,
            "mapping_invoked": False,
            "numeric_extraction_invoked": False,
            "excel_export_invoked": False,
        },
        "benchmark_implementation": _artifact(project_root, Path(__file__).resolve()),
        "claim_boundary": experiment["claim_boundary"],
    }
    atomic_write_json(output, payload)
    return payload
