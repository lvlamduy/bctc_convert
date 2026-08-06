from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.preprocessing.targeted_render import render_targeted_reread_page
from bctc_ai.preprocessing.targeted_reread import (
    TargetedRereadError,
    load_targeted_reread_policy,
    plan_page_targeted_rereads,
)


class TargetedRereadRunError(RuntimeError):
    pass


_EXPECTED_METRIC_KEYS = {
    "document_count",
    "page_count",
    "planned_page_count",
    "planned_region_count",
    "full_table_structural_region_count",
    "row_band_structural_region_count",
    "numeric_cell_strip_region_count",
    "skipped_mapping_ineligible_page_count",
    "no_reread_trigger_page_count",
    "unsupported_escalation_count",
    "source_pdf_rerendered_region_count",
    "report_norm_ids_proposed_or_added",
}
_REGION_METRICS = {
    "FULL_TABLE_STRUCTURAL_RECOVERY": "full_table_structural_region_count",
    "ROW_BAND_STRUCTURAL_RECOVERY": "row_band_structural_region_count",
    "NUMERIC_CELL_STRIP_REREAD": "numeric_cell_strip_region_count",
}
_SAFE_KEY = re.compile(r"^[A-Z0-9][A-Z0-9_]*$")


def _directory_fsync(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _resolve(project_root: Path, raw_path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise TargetedRereadRunError("artifact path must be a non-empty string")
    path = (project_root / raw_path).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise TargetedRereadRunError(f"artifact path escapes project root: {raw_path}") from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise TargetedRereadRunError(f"path escapes project root: {path}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise TargetedRereadRunError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise TargetedRereadRunError(f"JSON artifact is not an object: {path}")
    return payload


def _verify_identity(project_root: Path, identity: dict[str, Any], label: str) -> Path:
    if not isinstance(identity, dict):
        raise TargetedRereadRunError(f"{label} identity is not an object")
    raw_path = identity.get("path")
    expected_hash = identity.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
        raise TargetedRereadRunError(f"{label} lacks path/hash identity")
    path = _resolve(project_root, raw_path)
    if not path.is_file():
        raise TargetedRereadRunError(f"{label} is absent: {path}")
    if sha256_file(path) != expected_hash:
        raise TargetedRereadRunError(f"{label} hash drift: {path}")
    size = identity.get("size_bytes")
    if size is not None and (not isinstance(size, int) or path.stat().st_size != size):
        raise TargetedRereadRunError(f"{label} size drift: {path}")
    return path


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise TargetedRereadRunError(f"cannot read E-0016 config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise TargetedRereadRunError("E-0016 config must be version 1")
    if payload.get("experiment_id") != "E-0016" or payload.get("dataset_role") != "CALIBRATION":
        raise TargetedRereadRunError("E-0016 identity or dataset role drifted")
    expected = payload.get("expected_input_contract")
    if (
        not isinstance(expected, dict)
        or set(expected) != _EXPECTED_METRIC_KEYS
        or any(not isinstance(value, int) or value < 0 for value in expected.values())
    ):
        raise TargetedRereadRunError("E-0016 expected input contract is invalid")
    safety = payload.get("safety")
    if (
        not isinstance(safety, dict)
        or not safety
        or any(value is not False for value in safety.values())
    ):
        raise TargetedRereadRunError("E-0016 safety permissions must all be false")
    claim = payload.get("claim_boundary")
    if not isinstance(claim, str) or not claim.strip():
        raise TargetedRereadRunError("E-0016 claim boundary is absent")
    return payload


def _verify_ocr_render_binding(
    project_root: Path,
    ocr_payload: dict[str, Any],
    render_identity: dict[str, Any],
    render_path: Path,
) -> None:
    raw_input = ocr_payload.get("input_path")
    render_relative = render_identity.get("path")
    if not isinstance(raw_input, str) or not isinstance(render_relative, str):
        raise TargetedRereadRunError("Role C OCR/render binding lacks paths")
    normalized_input = Path(raw_input).as_posix()
    if not (
        normalized_input == render_relative or normalized_input.endswith(f"/{render_relative}")
    ):
        raise TargetedRereadRunError("Role C OCR input path is not the sealed baseline render")
    input_path = Path(raw_input)
    if input_path.is_file() and sha256_file(input_path) != render_identity["sha256"]:
        raise TargetedRereadRunError("Role C absolute OCR input has drifted from its seal")
    if sha256_file(render_path) != render_identity["sha256"]:
        raise TargetedRereadRunError("sealed baseline render hash drift")
    if ocr_payload.get("return_word_box") is not True:
        raise TargetedRereadRunError("Role C baseline omitted required word-box evidence")
    fields = ("rec_texts", "rec_scores", "rec_boxes", "rec_polys", "text_word_boxes")
    lengths = {name: len(ocr_payload.get(name, [])) for name in fields}
    if len(set(lengths.values())) != 1:
        raise TargetedRereadRunError(f"Role C baseline axes disagree: {lengths}")
    if not render_path.samefile(_resolve(project_root, render_relative)):
        raise TargetedRereadRunError("baseline render resolver is inconsistent")


def _page_seal_records(seal: dict[str, Any]) -> dict[int, dict[str, Any]]:
    pages = seal.get("pages")
    if not isinstance(pages, list) or not pages:
        raise TargetedRereadRunError("Role C seal has no pages")
    records: dict[int, dict[str, Any]] = {}
    for record in pages:
        page = record.get("page") if isinstance(record, dict) else None
        if not isinstance(page, int) or page < 1 or page in records:
            raise TargetedRereadRunError("Role C seal has invalid or duplicate pages")
        records[page] = record
    return records


def _validate_upstream(upstream: dict[str, Any]) -> list[dict[str, Any]]:
    if upstream.get("experiment_id") != "E-0015":
        raise TargetedRereadRunError("targeted reread upstream is not E-0015")
    if upstream.get("dataset_role") != "CALIBRATION":
        raise TargetedRereadRunError("E-0015 dataset role drifted")
    if upstream.get("status") != (
        "PASS_STRUCTURAL_COMPARISON_WITH_RETAINED_DISAGREEMENTS_NO_ACCURACY_CLAIM"
    ):
        raise TargetedRereadRunError("E-0015 did not pass its structural contract")
    documents = upstream.get("documents")
    if not isinstance(documents, list) or not documents:
        raise TargetedRereadRunError("E-0015 has no documents")
    return documents


def _status_metrics(statuses: Counter[str]) -> dict[str, int]:
    return {
        "planned_page_count": statuses["PLANNED"]
        + statuses["PLANNED_WITH_UNSUPPORTED_ESCALATIONS"],
        "skipped_mapping_ineligible_page_count": statuses["SKIPPED_UPSTREAM_MAPPING_INELIGIBLE"],
        "no_reread_trigger_page_count": statuses["NO_REREAD_TRIGGER"],
    }


def build_targeted_reread_inputs(
    *,
    project_root: Path,
    config_path: Path,
    output_directory: Path,
    git_state: dict[str, Any],
    allow_dirty: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    config_path = config_path.resolve()
    output_directory = output_directory.resolve()
    try:
        config_path.relative_to(project_root)
        output_directory.relative_to(project_root)
    except ValueError as exc:
        raise TargetedRereadRunError("config and output must stay inside the project root") from exc
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite targeted-reread run: {output_directory}")
    if not isinstance(git_state.get("commit"), str) or not isinstance(git_state.get("dirty"), bool):
        raise TargetedRereadRunError("invalid Git state")
    if git_state["dirty"] and not allow_dirty:
        raise TargetedRereadRunError("refusing formal E-0016 from a dirty worktree")

    config = _load_config(config_path)
    upstream_config = config.get("upstream")
    if not isinstance(upstream_config, dict):
        raise TargetedRereadRunError("E-0016 upstream configuration is absent")
    upstream_identity = upstream_config.get("structural_fusion_artifact")
    policy_identity = upstream_config.get("targeted_reread_policy")
    upstream_path = _verify_identity(
        project_root, upstream_identity, "E-0015 structural-fusion artifact"
    )
    policy_path = _verify_identity(project_root, policy_identity, "targeted-reread policy")
    upstream = _read_json(upstream_path)
    upstream_documents = _validate_upstream(upstream)
    try:
        policy = load_targeted_reread_policy(policy_path)
    except (OSError, yaml.YAMLError, TargetedRereadError) as exc:
        raise TargetedRereadRunError("cannot load targeted-reread policy") from exc

    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    statuses: Counter[str] = Counter()
    region_kinds: Counter[str] = Counter()
    unsupported_count = 0
    source_rerendered_regions = 0
    variant_count = 0
    documents: list[dict[str, Any]] = []
    try:
        for upstream_document in upstream_documents:
            if not isinstance(upstream_document, dict):
                raise TargetedRereadRunError("E-0015 document is not an object")
            key = upstream_document.get("key")
            if not isinstance(key, str) or not _SAFE_KEY.fullmatch(key):
                raise TargetedRereadRunError(f"unsafe E-0015 document key: {key}")
            source_identity = upstream_document.get("source")
            source_path = _verify_identity(project_root, source_identity, f"{key} source PDF")
            reader_seals = upstream_document.get("reader_seals")
            role_c_identity = reader_seals.get("role_c") if isinstance(reader_seals, dict) else None
            role_c_seal_path = _verify_identity(project_root, role_c_identity, f"{key} Role C seal")
            role_c_seal = _read_json(role_c_seal_path)
            if role_c_seal.get("state") != "GEOMETRY_OCR_COMPLETE":
                raise TargetedRereadRunError(f"{key} Role C seal is incomplete")
            if role_c_seal.get("source_sha256") != source_identity.get("sha256"):
                raise TargetedRereadRunError(f"{key} source/Role C seal drift")
            sealed_pages = _page_seal_records(role_c_seal)
            raw_pages = upstream_document.get("pages")
            if not isinstance(raw_pages, list) or not raw_pages:
                raise TargetedRereadRunError(f"{key} has no E-0015 pages")
            page_numbers = [
                page.get("page") if isinstance(page, dict) else None for page in raw_pages
            ]
            if any(not isinstance(page, int) or page < 1 for page in page_numbers):
                raise TargetedRereadRunError(f"{key} has invalid E-0015 page numbers")
            if page_numbers != sorted(set(page_numbers)):
                raise TargetedRereadRunError(f"{key} E-0015 pages are duplicate or unordered")
            document_slug = key.casefold().replace("_", "-")
            page_records = []
            for page_record in raw_pages:
                page = page_record["page"]
                sealed_page = sealed_pages.get(page)
                if not isinstance(sealed_page, dict):
                    raise TargetedRereadRunError(f"{key} page {page} is absent from Role C seal")
                role_c = page_record.get("role_c")
                e0015_result_identity = role_c.get("result") if isinstance(role_c, dict) else None
                sealed_result_identity = sealed_page.get("ocr_result")
                if e0015_result_identity != sealed_result_identity:
                    raise TargetedRereadRunError(f"{key} page {page} E-0015/Role C result drift")
                result_path = _verify_identity(
                    project_root, sealed_result_identity, f"{key} page {page} Role C result"
                )
                render_identity = sealed_page.get("render")
                render_path = _verify_identity(
                    project_root, render_identity, f"{key} page {page} baseline render"
                )
                ocr_payload = _read_json(result_path)
                _verify_ocr_render_binding(project_root, ocr_payload, render_identity, render_path)
                image = cv2.imread(str(render_path), cv2.IMREAD_COLOR)
                if image is None:
                    raise TargetedRereadRunError(f"cannot decode baseline render: {render_path}")
                height, width = image.shape[:2]
                try:
                    plan = plan_page_targeted_rereads(
                        page_record,
                        ocr_payload,
                        baseline_width=width,
                        baseline_height=height,
                        policy=policy,
                    )
                except TargetedRereadError as exc:
                    raise TargetedRereadRunError(
                        f"cannot plan {key} page {page} targeted reread"
                    ) from exc
                statuses[plan["status"]] += 1
                unsupported_count += len(plan["unsupported_escalations"])
                for region in plan["regions"]:
                    kind = region.get("region_kind")
                    if kind not in _REGION_METRICS:
                        raise TargetedRereadRunError(f"unknown planned region kind: {kind}")
                    region_kinds[kind] += 1
                page_output = None
                if plan["regions"]:
                    page_directory = temporary / "documents" / document_slug / f"page-{page:04d}"
                    try:
                        rendered = render_targeted_reread_page(
                            source_path,
                            plan,
                            page_directory,
                            expected_source_sha256=source_identity["sha256"],
                            source_identity_path=source_identity["path"],
                        )
                    except (OSError, TargetedRereadError) as exc:
                        raise TargetedRereadRunError(
                            f"cannot render {key} page {page} targeted regions"
                        ) from exc
                    source_rerendered_regions += len(rendered["regions"])
                    variant_count += sum(len(region["variants"]) for region in rendered["regions"])
                    manifest_path = page_directory / "manifest.json"
                    page_output = {
                        "path": manifest_path.relative_to(temporary).as_posix(),
                        "sha256": sha256_file(manifest_path),
                    }
                page_records.append(
                    {
                        "page": page,
                        "statement_type": page_record.get("statement_type"),
                        "mapping_eligible": page_record.get("mapping_eligible"),
                        "baseline_render": render_identity,
                        "baseline_role_c_result": sealed_result_identity,
                        "plan": plan,
                        "render_manifest": page_output,
                    }
                )
            documents.append(
                {
                    "key": key,
                    "source": source_identity,
                    "role_c_seal": role_c_identity,
                    "pages": page_records,
                }
            )

        metrics = {
            "document_count": len(documents),
            "page_count": sum(len(document["pages"]) for document in documents),
            **_status_metrics(statuses),
            "planned_region_count": sum(region_kinds.values()),
            **{metric: region_kinds[kind] for kind, metric in _REGION_METRICS.items()},
            "unsupported_escalation_count": unsupported_count,
            "source_pdf_rerendered_region_count": source_rerendered_regions,
            "report_norm_ids_proposed_or_added": 0,
        }
        expected = config["expected_input_contract"]
        if metrics != expected:
            raise TargetedRereadRunError(
                f"E-0016 input contract mismatch: observed={metrics}, expected={expected}"
            )
        algorithm_paths = [
            Path("scripts/experiments/build_e0016_targeted_reread_inputs.py"),
            Path("src/bctc_ai/preprocessing/targeted_run.py"),
            Path("src/bctc_ai/preprocessing/targeted_reread.py"),
            Path("src/bctc_ai/preprocessing/targeted_render.py"),
            Path("src/bctc_ai/preprocessing/quality.py"),
            Path("src/bctc_ai/core/atomic.py"),
            Path("src/bctc_ai/core/hashing.py"),
        ]
        for path in algorithm_paths:
            if not (project_root / path).is_file():
                raise TargetedRereadRunError(f"algorithm file is absent: {path}")
        payload = {
            "format_version": 1,
            "experiment_id": "E-0016",
            "state": "TARGETED_REREAD_INPUTS_RENDERED_NO_VARIANT_SELECTED",
            "status": (
                "PASS_INPUT_CONTRACT_NO_VALUE_SELECTION"
                if not git_state["dirty"]
                else "DEVELOPMENT_SMOKE_DIRTY_WORKTREE"
            ),
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset_role": "CALIBRATION",
            "design": config["design"],
            "code": dict(git_state),
            "configuration": {
                "experiment": {
                    "path": _relative(project_root, config_path),
                    "sha256": sha256_file(config_path),
                },
                "targeted_reread_policy": policy_identity,
            },
            "upstream": {
                "structural_fusion_artifact": upstream_identity,
                "structural_fusion_status": upstream["status"],
            },
            "algorithm_files_sha256": {
                path.as_posix(): sha256_file(project_root / path) for path in algorithm_paths
            },
            "metrics": metrics,
            "diagnostics": {
                "page_statuses": dict(sorted(statuses.items())),
                "region_kinds": dict(sorted(region_kinds.items())),
                "generated_variant_image_count": variant_count,
                "variant_selection_status": "PENDING_OCR_EVIDENCE",
            },
            "acceptance": {
                "configured": expected,
                "observed": metrics,
                "contract_exact": True,
                "accuracy_threshold_evaluated": False,
                "human_gold_evaluated": False,
                "production_accuracy_approved": False,
            },
            "safety": {
                "configured_permissions": config["safety"],
                "role_a_or_searchable_reference_used": False,
                "historical_reference_invoked": False,
                "arithmetic_variant_selection_invoked": False,
                "schema_variant_selection_invoked": False,
                "automatic_variant_selection": False,
                "automatic_value_replacement": False,
                "automatic_confidence_promotion": False,
                "mapping_ineligible_page_crops": 0,
                "cross_page_crops": 0,
                "source_or_upstream_overwrite": False,
                "ytd_derivation_invoked": False,
            },
            "report_norm_id": {
                "ids_proposed_or_added": 0,
                "collision_check_invoked": False,
                "reason": "E-0016 input acquisition performs no schema mutation or mapping.",
            },
            "documents": documents,
            "claim_boundary": config["claim_boundary"],
        }
        atomic_write_json(temporary / "manifest.json", payload)
        if output_directory.exists():
            raise FileExistsError(f"output appeared during E-0016: {output_directory}")
        os.replace(temporary, output_directory)
        _directory_fsync(output_directory.parent)
        return payload
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
