from __future__ import annotations

import json
import math
import subprocess
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.document_phase.statement_evidence import load_ocr_pages_from_batch


class HoldoutDiscoverySealError(RuntimeError):
    pass


@dataclass(frozen=True)
class UnresolvedDiscoveryValidation:
    source_path: str
    source_sha256: str
    source_size_bytes: int
    preprocess_manifest_path: str
    preprocess_manifest_sha256: str
    preprocess_git_commit: str
    preprocess_page_count: int
    preprocess_dpi: int
    batch_root: str
    batch_manifest_sha256: str
    batch_identity_sha256: str
    batch_page_count: int
    batch_line_count: int
    batch_word_token_count: int
    batch_mean_line_score: float
    batch_minimum_line_score: float
    batch_lines_below_0_8: int
    batch_lines_below_0_9: int
    location_path: str
    location_sha256: str
    location_state: str
    location_candidate_count: int
    location_mapping_eligible_page_count: int
    semantic_reader_invoked: bool
    downstream_extraction_file_count: int
    role_a_path: str
    role_a_locally_present: bool
    role_a_immutable_path: str
    role_a_immutable_locally_present: bool
    role_a_holdout_output_count: int
    sealed_artifact_file_count: int
    sealed_artifact_set_sha256: str


_EXECUTION_CONTROL_PATH = Path("docs/experiments/E-0022-role-b-execution-control.json")
_EXECUTION_CONTROL_SHA256 = "c56721c3164c42e5ddd869778134b0196a914d04144b7a591524b0a6bc200d81"
_RUN_ROOT = Path("output/holdout/e0022-acb-q1-2026-role-b/a85402445a34e80dd424")
_BATCH_RELATIVE = Path("ocr/ppocrv6-full-document")
_LOCATION_RELATIVE = Path("layout/statement-location.json")


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HoldoutDiscoverySealError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise HoldoutDiscoverySealError(f"JSON artifact is not an object: {path}")
    return payload


def _safe_path(project_root: Path, value: str) -> Path:
    path = (project_root / value).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise HoldoutDiscoverySealError(f"path escapes project root: {value}") from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise HoldoutDiscoverySealError(f"artifact escapes project root: {path}") from exc


def _artifact_record(project_root: Path, path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise HoldoutDiscoverySealError(f"sealed artifact is absent: {path}")
    return {
        "path": _relative(project_root, path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _verify_models(project_root: Path, model_cache_root: Path) -> list[dict[str, Any]]:
    runtime_path = project_root / "config/models/gpu-runtime.toml"
    runtime = tomllib.loads(runtime_path.read_text(encoding="utf-8"))
    models = runtime.get("models")
    if not isinstance(models, dict):
        raise HoldoutDiscoverySealError("GPU runtime contains no model identities")
    verified = []
    for key in ("pp_ocrv6_medium_det", "pp_ocrv6_medium_rec"):
        model = models.get(key)
        if not isinstance(model, dict):
            raise HoldoutDiscoverySealError(f"PP-OCRv6 model identity is absent: {key}")
        weights = (
            model_cache_root
            / "official_models"
            / str(model["cache_directory"])
            / str(model["weights_file"])
        )
        expected_size = int(model["weights_size_bytes"])
        expected_digest = str(model["weights_sha256"])
        if (
            not weights.is_file()
            or weights.stat().st_size != expected_size
            or sha256_file(weights) != expected_digest
        ):
            raise HoldoutDiscoverySealError(f"PP-OCRv6 model weights drifted: {weights}")
        verified.append(
            {
                "model_key": key,
                "repo_id": model["repo_id"],
                "revision": model["revision"],
                "weights_size_bytes": expected_size,
                "weights_sha256": expected_digest,
            }
        )
    return verified


def _verify_role_a_absent(
    project_root: Path,
    execution_control: dict[str, Any],
) -> tuple[str, Path, int]:
    validation = execution_control.get("validation")
    if not isinstance(validation, dict):
        raise HoldoutDiscoverySealError("execution control has no validation evidence")
    role_a_value = str(validation.get("role_a_path", ""))
    role_a_path = _safe_path(project_root, role_a_value)
    immutable_value = str(validation.get("role_a_immutable_path", ""))
    immutable_path = _safe_path(project_root, immutable_value)
    if role_a_path.exists() or immutable_path.exists():
        raise HoldoutDiscoverySealError("Role A source exists before unresolved Role B seal")
    digest = Path(immutable_value).stem
    holdout_root = project_root / "output" / "holdout"
    outputs = sorted(holdout_root.glob(f"*/{digest[:20]}")) if holdout_root.is_dir() else []
    if outputs:
        raise HoldoutDiscoverySealError("Role A output exists before unresolved Role B seal")
    return role_a_value, immutable_path, len(outputs)


def _verify_location(
    project_root: Path,
    location_path: Path,
    batch_root: Path,
    batch: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    location = _load_json(location_path)
    expected_identity = {
        "state": "UNRESOLVED",
        "dataset_role": "UNTOUCHED_HOLDOUT",
    }
    if any(location.get(key) != value for key, value in expected_identity.items()):
        raise HoldoutDiscoverySealError("statement-location state or dataset role drifted")
    if location.get("source") != batch.get("source"):
        raise HoldoutDiscoverySealError("statement location source differs from OCR batch")
    batch_evidence = location.get("batch")
    expected_batch_evidence = {
        "path": _relative(project_root, batch_root),
        "sha256": sha256_file(batch_root / "batch_manifest.json"),
        "identity_sha256": batch.get("batch_identity"),
        "checkpoint_state": "OCR_COMPLETE",
        "completed_pages": 33,
        "requested_pages": 33,
    }
    if not isinstance(batch_evidence, dict) or any(
        batch_evidence.get(key) != value for key, value in expected_batch_evidence.items()
    ):
        raise HoldoutDiscoverySealError("statement location is not bound to the full OCR batch")
    configuration = location.get("configuration")
    algorithm = location.get("algorithm")
    required_files = {
        "config/document_phase/statement-locator-v1.yaml": "d25ff6da2a1ce48428b4ab1ac20a31b989a27849d93326ae839507dce2ff107e",
        "scripts/experiments/locate_statement_pages.py": "a274aad0b7090fd1d0a162608d4240e64a6356573ed0e24519537e0321f2bd79",
        "src/bctc_ai/document_phase/statement_locator.py": "8b4b283cb3eeaa3e2457e84950574cc79502143e09ae4b3b712e93e1dde8b35c",
    }
    for value, digest in required_files.items():
        if sha256_file(project_root / value) != digest:
            raise HoldoutDiscoverySealError(f"frozen statement locator file drifted: {value}")
    if configuration != {
        "path": "config/document_phase/statement-locator-v1.yaml",
        "sha256": required_files["config/document_phase/statement-locator-v1.yaml"],
    }:
        raise HoldoutDiscoverySealError("statement locator configuration identity drifted")
    if not isinstance(algorithm, dict) or algorithm != {
        "path": "scripts/experiments/locate_statement_pages.py",
        "sha256": required_files["scripts/experiments/locate_statement_pages.py"],
        "locator_path": "src/bctc_ai/document_phase/statement_locator.py",
        "locator_sha256": required_files["src/bctc_ai/document_phase/statement_locator.py"],
    }:
        raise HoldoutDiscoverySealError("statement locator algorithm identity drifted")
    if location.get("code") != batch.get("code"):
        raise HoldoutDiscoverySealError("statement locator and OCR batch used different code state")
    result = location.get("result")
    if not isinstance(result, dict):
        raise HoldoutDiscoverySealError("statement locator has no result")
    expected_result = {
        "status": "UNRESOLVED",
        "candidate_count": 0,
        "candidate_summaries": [],
        "errors": ["no complete ordered CDKT->KQKD->LCTT->TM block"],
        "observed_pages": list(range(1, 34)),
        "runner_up_margin": None,
    }
    if any(result.get(key) != value for key, value in expected_result.items()):
        raise HoldoutDiscoverySealError("unresolved statement-location contract drifted")
    decisions = result.get("page_decisions")
    if (
        not isinstance(decisions, list)
        or [decision.get("page") for decision in decisions if isinstance(decision, dict)]
        != list(range(1, 34))
        or any(
            not isinstance(decision, dict) or decision.get("mapping_eligible") is not False
            for decision in decisions
        )
    ):
        raise HoldoutDiscoverySealError("unresolved page decisions are incomplete or eligible")
    return result, [
        _artifact_record(project_root, project_root / relative) for relative in required_files
    ]


def validate_e0022_unresolved_role_b_discovery(
    project_root: Path,
    *,
    model_cache_root: Path,
) -> tuple[UnresolvedDiscoveryValidation, dict[str, Any]]:
    project_root = project_root.resolve()
    run_root = (project_root / _RUN_ROOT).resolve()
    batch_root = run_root / _BATCH_RELATIVE
    location_path = run_root / _LOCATION_RELATIVE
    execution_path = project_root / _EXECUTION_CONTROL_PATH
    if sha256_file(execution_path) != _EXECUTION_CONTROL_SHA256:
        raise HoldoutDiscoverySealError("E-0022 execution-control artifact hash drifted")
    execution = _load_json(execution_path)
    if (
        execution.get("state") != "ROLE_B_EXECUTION_READY"
        or execution.get("role_a_access_permitted") is not False
        or execution.get("allowed_next_action") != "PREPROCESS_ROLE_B_FULL_DOCUMENT"
    ):
        raise HoldoutDiscoverySealError("E-0022 execution-control contract drifted")
    role_a_value, role_a_immutable, role_a_output_count = _verify_role_a_absent(
        project_root, execution
    )

    batch, pages = load_ocr_pages_from_batch(batch_root, project_root=project_root)
    if (
        batch.get("state") != "OCR_COMPLETE"
        or batch.get("dataset_role") != "UNTOUCHED_HOLDOUT"
        or batch.get("requested_pages") != list(range(1, 34))
        or [page.page for page in pages] != list(range(1, 34))
    ):
        raise HoldoutDiscoverySealError("Role B OCR is not complete for all 33 pages")
    source = batch.get("source")
    if not isinstance(source, dict):
        raise HoldoutDiscoverySealError("Role B OCR batch has no source")
    expected_source = {
        "path": execution["validation"]["role_b_path"],
        "sha256": execution["validation"]["role_b_sha256"],
        "size_bytes": execution["validation"]["role_b_size_bytes"],
    }
    if source != expected_source:
        raise HoldoutDiscoverySealError("Role B source differs from execution control")

    preprocess_record = batch.get("input_manifest")
    if not isinstance(preprocess_record, dict):
        raise HoldoutDiscoverySealError("Role B batch has no preprocess manifest")
    preprocess_path = _safe_path(project_root, str(preprocess_record.get("path", "")))
    preprocess = _load_json(preprocess_path)
    preprocess_pages = preprocess.get("pages")
    if (
        preprocess.get("state") != "PREPROCESSED"
        or preprocess.get("dataset_role") != "UNTOUCHED_HOLDOUT"
        or preprocess.get("source_sha256") != source["sha256"]
        or not isinstance(preprocess_pages, list)
        or [page.get("page") for page in preprocess_pages if isinstance(page, dict)]
        != list(range(1, 34))
        or any(
            not isinstance(page, dict)
            or not isinstance(page.get("render"), dict)
            or page["render"].get("dpi") != 300
            for page in preprocess_pages
        )
    ):
        raise HoldoutDiscoverySealError("Role B preprocess full-document contract drifted")
    preprocess_code = preprocess.get("code")
    if not isinstance(preprocess_code, dict) or preprocess_code.get("git_dirty") is not False:
        raise HoldoutDiscoverySealError("Role B preprocessing did not use clean code")
    batch_code = batch.get("code")
    if batch_code != {"commit": preprocess_code.get("git_commit"), "dirty": False}:
        raise HoldoutDiscoverySealError("Role B preprocessing and OCR used different code states")

    expected_ocr_configuration = {
        "path": "config/models/pp-ocrv6-word-box.yaml",
        "sha256": "a200fbbc8ba85460c9233875a7a025e8d08d892172d353ed820f69fd258e997b",
        "runner_path": "scripts/models/run_ppocrv6_word_boxes_batch.py",
        "runner_sha256": "7a716b0aa47dacc0b95454a46371721cc0af613892767f6e58e97035602322cb",
        "single_page_helper_path": "scripts/models/run_ppocrv6_word_boxes.py",
        "single_page_helper_sha256": "bbbf2f101cec88ae99727393397df463623d47c2b31ef888e565fbe42c05d4b9",
        "implicit_orientation_or_unwarp": False,
        "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
        "mkldnn": False,
        "precision": "fp32",
        "cpu_threads": 8,
    }
    if batch.get("configuration") != expected_ocr_configuration:
        raise HoldoutDiscoverySealError("Role B PP-OCRv6 configuration identity drifted")

    scores = [line.score for page in pages for line in page.lines]
    metrics = batch.get("metrics")
    if not isinstance(metrics, dict):
        raise HoldoutDiscoverySealError("Role B OCR batch has no metrics")
    expected_integer_metrics = {
        "completed_page_count": 33,
        "line_count": len(scores),
        "lines_below_0_8": sum(score < 0.8 for score in scores),
        "lines_below_0_9": sum(score < 0.9 for score in scores),
    }
    if any(int(metrics.get(key, -1)) != value for key, value in expected_integer_metrics.items()):
        raise HoldoutDiscoverySealError("Role B OCR aggregate count metrics drifted")
    mean_score = sum(scores) / len(scores)
    minimum_score = min(scores)
    if not math.isclose(float(metrics.get("mean_line_score", -1)), mean_score, abs_tol=1e-12):
        raise HoldoutDiscoverySealError("Role B OCR mean confidence drifted")
    if not math.isclose(float(metrics.get("minimum_line_score", -1)), minimum_score, abs_tol=1e-12):
        raise HoldoutDiscoverySealError("Role B OCR minimum confidence drifted")

    location_result, locator_records = _verify_location(
        project_root, location_path, batch_root, batch
    )
    semantic_outputs = sorted((run_root / "ocr").glob("paddleocr-vl-page-*"))
    semantic_metrics = sorted((run_root / "experiments").glob("paddleocr-vl-page-*-metrics.json"))
    if semantic_outputs or semantic_metrics:
        raise HoldoutDiscoverySealError("semantic reader ran without a discovered statement block")
    downstream_files = [
        path
        for directory in ("tables", "rows", "axes", "mapping", "validation", "workbooks")
        for path in (run_root / directory).rglob("*")
        if path.is_file()
    ]
    if downstream_files:
        raise HoldoutDiscoverySealError("downstream extraction ran after unresolved discovery")

    model_records = _verify_models(project_root, model_cache_root.resolve())
    artifact_records = [
        _artifact_record(project_root, execution_path),
        _artifact_record(project_root, _safe_path(project_root, source["path"])),
        _artifact_record(project_root, preprocess_path),
        _artifact_record(project_root, preprocess_path.with_name("run_manifest.json")),
        _artifact_record(project_root, batch_root / "batch_manifest.json"),
        _artifact_record(project_root, location_path),
        *locator_records,
    ]
    for render in batch["renders"]:
        artifact_records.append(
            _artifact_record(project_root, _safe_path(project_root, render["path"]))
        )
    for page_record in batch["pages"]:
        for key in ("run_manifest", "ocr_result"):
            artifact_records.append(
                _artifact_record(project_root, batch_root / page_record[key]["path"])
            )
    unique_records = {record["path"]: record for record in artifact_records}
    if len(unique_records) != len(artifact_records):
        raise HoldoutDiscoverySealError("sealed artifact paths are duplicated")
    artifact_lines = [f"{record['sha256']}  {record['path']}" for record in unique_records.values()]
    validation = UnresolvedDiscoveryValidation(
        source_path=str(source["path"]),
        source_sha256=str(source["sha256"]),
        source_size_bytes=int(source["size_bytes"]),
        preprocess_manifest_path=_relative(project_root, preprocess_path),
        preprocess_manifest_sha256=sha256_file(preprocess_path),
        preprocess_git_commit=str(preprocess_code["git_commit"]),
        preprocess_page_count=33,
        preprocess_dpi=300,
        batch_root=_relative(project_root, batch_root),
        batch_manifest_sha256=sha256_file(batch_root / "batch_manifest.json"),
        batch_identity_sha256=str(batch["batch_identity"]),
        batch_page_count=33,
        batch_line_count=int(metrics["line_count"]),
        batch_word_token_count=int(metrics["word_token_count"]),
        batch_mean_line_score=float(metrics["mean_line_score"]),
        batch_minimum_line_score=float(metrics["minimum_line_score"]),
        batch_lines_below_0_8=int(metrics["lines_below_0_8"]),
        batch_lines_below_0_9=int(metrics["lines_below_0_9"]),
        location_path=_relative(project_root, location_path),
        location_sha256=sha256_file(location_path),
        location_state="UNRESOLVED",
        location_candidate_count=int(location_result["candidate_count"]),
        location_mapping_eligible_page_count=sum(
            bool(decision["mapping_eligible"]) for decision in location_result["page_decisions"]
        ),
        semantic_reader_invoked=False,
        downstream_extraction_file_count=0,
        role_a_path=role_a_value,
        role_a_locally_present=False,
        role_a_immutable_path=_relative(project_root, role_a_immutable),
        role_a_immutable_locally_present=False,
        role_a_holdout_output_count=role_a_output_count,
        sealed_artifact_file_count=len(unique_records),
        sealed_artifact_set_sha256=stable_records_hash(sorted(artifact_lines)),
    )
    supporting = {
        "models": model_records,
        "artifact_records": [unique_records[path] for path in sorted(unique_records)],
    }
    return validation, supporting


def capture_e0022_unresolved_role_b_discovery(
    project_root: Path,
    *,
    model_cache_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise HoldoutDiscoverySealError("formal unresolved Role B seal requires a clean worktree")
    output = output_path if output_path.is_absolute() else project_root / output_path
    output = output.resolve()
    try:
        output.relative_to(project_root / "docs" / "experiments")
    except ValueError as exc:
        raise HoldoutDiscoverySealError(
            "formal Role B seal must remain in docs/experiments"
        ) from exc
    if output.exists():
        raise HoldoutDiscoverySealError(f"refusing to overwrite Role B discovery seal: {output}")
    validation, supporting = validate_e0022_unresolved_role_b_discovery(
        project_root,
        model_cache_root=model_cache_root,
    )
    implementation = Path(__file__).resolve()
    payload = {
        "format_version": 1,
        "experiment_id": "E-0022",
        "state": "ROLE_B_DISCOVERY_SEALED_UNRESOLVED",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "validation": asdict(validation),
        "models": supporting["models"],
        "artifact_records": supporting["artifact_records"],
        "semantic_reader": {
            "invoked": False,
            "reason": "NO_DISCOVERED_MAIN_STATEMENT_BLOCK",
        },
        "mapping": {"invoked": False},
        "historical_reference": {"invoked": False},
        "threshold_or_page_selection_tuning_performed": False,
        "role_a_access_permitted_during_role_b": False,
        "seal_implementation": {
            "path": _relative(project_root, implementation),
            "sha256": sha256_file(implementation),
        },
        "allowed_next_action": "HYDRATE_ROLE_A_AND_BUILD_MACHINE_REFERENCE_FOR_ONE_SHOT_DIAGNOSIS",
        "claim_boundary": (
            "This seal proves the exact unresolved Role B full-document discovery/OCR outcome. "
            "It contains no manually selected pages, no threshold change, no Role A evidence, "
            "no schema mapping, and no accuracy claim."
        ),
    }
    atomic_write_json(output, payload)
    return payload
