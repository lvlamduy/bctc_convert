from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_bytes, sha256_file
from bctc_ai.document_phase.multisignal_statement_discovery import (
    discover_statement_pages,
    load_multisignal_statement_config,
)
from bctc_ai.document_phase.statement_evidence import load_ocr_pages_from_batch


class E0027RecoveryError(RuntimeError):
    """Raised when the E-0027 recovery reproduction is not evidence-equivalent."""


def _load_object(path: Path, *, yaml_input: bool = False) -> dict[str, Any]:
    try:
        payload = (
            yaml.safe_load(path.read_text(encoding="utf-8"))
            if yaml_input
            else json.loads(path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as error:
        raise E0027RecoveryError(f"cannot load recovery input: {path}") from error
    if not isinstance(payload, dict):
        raise E0027RecoveryError(f"recovery input must be an object: {path}")
    return payload


def _resolve(project_root: Path, value: str, *, allow_absolute: bool = False) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        if not allow_absolute:
            raise E0027RecoveryError(f"absolute recovery path is forbidden: {value}")
        return raw
    path = (project_root / raw).resolve()
    if not path.is_relative_to(project_root):
        raise E0027RecoveryError(f"recovery path escapes project root: {value}")
    return path


def _verify_file(project_root: Path, record: dict[str, Any]) -> Path:
    path = _resolve(project_root, str(record.get("path", "")))
    if not path.is_file():
        raise E0027RecoveryError(f"required recovery artifact is absent: {path}")
    if path.stat().st_size != int(record.get("size_bytes", path.stat().st_size)):
        raise E0027RecoveryError(f"recovery artifact size drifted: {path}")
    if sha256_file(path) != record.get("sha256"):
        raise E0027RecoveryError(f"recovery artifact SHA-256 drifted: {path}")
    return path


def canonicalize_ocr_input_path(payload: dict[str, Any], historical_path: str) -> bytes:
    if set(key for key in payload if key == "input_path") != {"input_path"}:
        raise E0027RecoveryError("OCR payload has no unique input_path provenance field")
    canonical = dict(payload)
    canonical["input_path"] = historical_path
    return (
        json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _git(project_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def capture_e0027_reproduction(
    project_root: Path,
    *,
    config_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise E0027RecoveryError("formal recovery capture requires clean Git code")
    config_path = _resolve(project_root, config_path.as_posix())
    output_path = _resolve(project_root, output_path.as_posix())
    recovery_root = (project_root / "docs" / "recovery").resolve()
    if not output_path.is_relative_to(recovery_root):
        raise E0027RecoveryError("recovery capture must remain below docs/recovery")
    if output_path.exists():
        raise E0027RecoveryError(f"refusing to overwrite recovery capture: {output_path}")
    config = _load_object(config_path, yaml_input=True)
    if (
        config.get("format_version") != 1
        or config.get("recovery_id") != "R-0001"
        or config.get("policy") != "LOST_BATCH_MANIFEST_FUNCTIONAL_REPRODUCTION_V1"
    ):
        raise E0027RecoveryError("unexpected recovery policy identity")

    lost = config["lost_artifact"]
    lost_path = _resolve(project_root, str(lost["path"]))
    if lost_path.exists():
        raise E0027RecoveryError("lost artifact unexpectedly exists; verify it directly instead")
    source = _verify_file(project_root, config["source"])
    historical_discovery_path = _verify_file(
        project_root, config["historical_seals"]["discovery"]
    )
    historical_numeric_path = _verify_file(
        project_root, config["historical_seals"]["numeric_grid"]
    )
    for record in config["frozen_runtime"].values():
        _verify_file(project_root, record)

    reproduction = config["reproduction"]
    preprocess_path = _verify_file(project_root, reproduction["preprocess_manifest"])
    batch_path = _verify_file(project_root, reproduction["batch_manifest"])
    batch_root = batch_path.parent
    batch, geometry_pages = load_ocr_pages_from_batch(batch_root, project_root=project_root)
    if batch.get("code") != {
        "commit": reproduction["generated_from_clean_commit"],
        "dirty": False,
    }:
        raise E0027RecoveryError("reproduction batch Git identity drifted")
    if batch.get("batch_identity") != reproduction["batch_manifest"]["batch_identity"]:
        raise E0027RecoveryError("reproduction batch identity drifted")
    if batch.get("source", {}).get("sha256") != config["source"]["sha256"]:
        raise E0027RecoveryError("reproduction batch source drifted")
    if batch.get("input_manifest", {}).get("sha256") != sha256_file(preprocess_path):
        raise E0027RecoveryError("reproduction preprocess binding drifted")

    historical_discovery = _load_object(historical_discovery_path)
    historical_numeric = _load_object(historical_numeric_path)
    historical_source_artifacts = {
        item["path"]: item
        for item in historical_numeric.get("source_artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    page_evidence: list[dict[str, Any]] = []
    for page_number, record in sorted(reproduction["pages"].items(), key=lambda item: int(item[0])):
        page = int(page_number)
        render = _resolve(project_root, record["render_path"])
        ocr = _resolve(project_root, record["ocr_path"])
        if not render.is_file() or not ocr.is_file():
            raise E0027RecoveryError(f"reproduction page artifacts are absent: {page}")
        if (
            render.stat().st_size != int(record["render_size_bytes"])
            or sha256_file(render) != record["render_sha256"]
            or ocr.stat().st_size != int(record["reproduced_ocr_size_bytes"])
            or sha256_file(ocr) != record["reproduced_ocr_sha256"]
        ):
            raise E0027RecoveryError(f"reproduction page artifact drifted: {page}")
        historical_render_relative = str(record["historical_render_path"]).removeprefix(
            f"{project_root.as_posix()}/"
        )
        historical_render = historical_source_artifacts.get(historical_render_relative)
        historical_ocr = next(
            (
                item
                for path, item in historical_source_artifacts.items()
                if path.endswith(f"ppocrv6-page-{page:04d}/ocr_result.json")
            ),
            None,
        )
        if (
            historical_render is None
            or historical_ocr is None
            or historical_render["sha256"] != record["render_sha256"]
            or int(historical_render["size_bytes"]) != int(record["render_size_bytes"])
        ):
            raise E0027RecoveryError(f"historical render binding drifted: {page}")
        canonical = canonicalize_ocr_input_path(
            _load_object(ocr), str(record["historical_render_path"])
        )
        canonical_sha256 = sha256_bytes(canonical)
        if (
            canonical_sha256 != record["historical_canonical_ocr_sha256"]
            or len(canonical) != int(record["historical_canonical_ocr_size_bytes"])
            or canonical_sha256 != historical_ocr["sha256"]
            or len(canonical) != int(historical_ocr["size_bytes"])
        ):
            raise E0027RecoveryError(f"canonical historical OCR mismatch: {page}")
        page_evidence.append(
            {
                "page": page,
                "render_byte_exact": True,
                "render_sha256": sha256_file(render),
                "reproduced_ocr_sha256": sha256_file(ocr),
                "canonical_historical_ocr_byte_exact": True,
                "canonical_historical_ocr_sha256": canonical_sha256,
                "only_canonicalized_field": "input_path",
            }
        )

    historical_metrics = historical_discovery["ocr_metrics"]
    reproduced_metrics = batch["metrics"]
    stable_fields = list(config["stable_metric_fields"])
    stable_metrics = {field: reproduced_metrics[field] for field in stable_fields}
    expected_stable_metrics = {field: historical_metrics[field] for field in stable_fields}
    if stable_metrics != expected_stable_metrics:
        raise E0027RecoveryError("stable OCR metrics differ from historical seal")

    locator_path = _verify_file(
        project_root, config["frozen_runtime"]["statement_discovery"]
    )
    discovery = discover_statement_pages(
        geometry_pages,
        load_multisignal_statement_config(locator_path),
    )
    discovery_json = _json_value(discovery)
    if discovery_json != historical_discovery["discovery_result"]:
        raise E0027RecoveryError("reproduced V3 discovery differs from historical seal")
    if batch_path.stat().st_size == int(lost["size_bytes"]) or sha256_file(batch_path) == lost["sha256"]:
        raise E0027RecoveryError("reproduction must not masquerade as the lost batch manifest")

    payload = {
        "format_version": 1,
        "recovery_id": "R-0001",
        "status": "PASS_FUNCTIONAL_REPRODUCTION_NOT_ORIGINAL_BATCH_MANIFEST",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "capture_git_dirty": False,
        "config": {
            "path": config_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_path),
        },
        "lost_artifact": dict(lost),
        "source": {
            "path": source.relative_to(project_root).as_posix(),
            "sha256": sha256_file(source),
            "size_bytes": source.stat().st_size,
        },
        "reproduction": {
            "preprocess_manifest": dict(reproduction["preprocess_manifest"]),
            "batch_manifest": dict(reproduction["batch_manifest"]),
            "original_batch_manifest_recovered": False,
            "batch_identity_matches_original": False,
        },
        "page_evidence": page_evidence,
        "stable_metrics_exact": True,
        "stable_metrics": stable_metrics,
        "observational_metrics": {
            field: {
                "historical": historical_metrics[field],
                "reproduced": reproduced_metrics[field],
            }
            for field in config["observational_metric_fields"]
        },
        "discovery_result_json_exact": True,
        "discovery_result": discovery_json,
        "role_isolation": {
            "human_review_loaded": False,
            "historical_values_loaded": False,
            "e0022_evidence_loaded": False,
            "schema_mapping_invoked": False,
            "numeric_value_selection_invoked": False,
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_write_json(output_path, payload)
    return payload
