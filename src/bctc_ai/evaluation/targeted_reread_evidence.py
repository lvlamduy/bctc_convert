from __future__ import annotations

import json
import math
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.evaluation.reader_outputs_v2 import (
    ReaderOutputV2Error,
    load_vlm_table_parser_config,
    parse_paddle_vl_page_v2,
    table_roles_to_dict,
)
from bctc_ai.evaluation.structural_fusion_v2 import (
    StructuredReaderRow,
    compare_structural_readers_v2,
)
from bctc_ai.evaluation.word_box_rows import WordBoxReconstructionError
from bctc_ai.evaluation.word_box_rows_v2 import (
    geometry_row_v2_to_dict,
    load_word_box_reconstruction_v2_config,
    parse_ppocrv6_word_box_page_v2,
)
from bctc_ai.mapping.scope import load_scope_policy


class TargetedRereadEvidenceError(RuntimeError):
    pass


_REQUIRED_DEPENDENCIES = {
    "gpu_package_freeze",
    "gpu_runtime_manifest",
    "paddleocr_vl_model_config",
    "paddleocr_vl_runner",
    "ppocrv6_model_config",
    "ppocrv6_runner",
    "scope_policy",
    "vlm_table_parser_config",
    "word_box_reconstruction_config",
}
_REQUIRED_SAFETY = {
    "automatic_confidence_promotion_permitted": False,
    "automatic_value_replacement_permitted": False,
    "automatic_variant_selection_permitted": False,
    "history_permitted": False,
    "human_gold_claim_permitted": False,
    "production_accuracy_claim_permitted": False,
    "report_norm_id_mapping_permitted": False,
    "schema_mutation_permitted": False,
}
_EXPECTED_PAGE_SAFETY = {
    "arithmetic_selects_variant": False,
    "automatic_confidence_promotion": False,
    "automatic_value_replacement": False,
    "cross_page_region": False,
    "history_selects_variant": False,
    "preserve_original": True,
    "require_upstream_mapping_eligible": True,
    "schema_selects_variant": False,
}
_OBSERVED = {
    ObservationKind.VALUE,
    ObservationKind.ZERO,
    ObservationKind.DASH,
}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise TargetedRereadEvidenceError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise TargetedRereadEvidenceError(f"{label} is not a JSON object: {path}")
    return payload


def _resolve_within(base: Path, raw_path: str, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise TargetedRereadEvidenceError(f"{label} path must be a non-empty string")
    path = (base / raw_path).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError as exc:
        raise TargetedRereadEvidenceError(f"{label} path escapes its root: {raw_path}") from exc
    return path


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise TargetedRereadEvidenceError(f"path escapes project root: {path}") from exc


def _file_record(project_root: Path, path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise TargetedRereadEvidenceError(f"artifact is absent or is a symlink: {path}")
    return {
        "path": _project_relative(project_root, path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _verify_identity(
    project_root: Path,
    identity: dict[str, Any],
    label: str,
    *,
    base: Path | None = None,
) -> Path:
    if not isinstance(identity, dict):
        raise TargetedRereadEvidenceError(f"{label} identity is not an object")
    raw_path = identity.get("path")
    expected_hash = identity.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
        raise TargetedRereadEvidenceError(f"{label} lacks a path/SHA-256 identity")
    path = _resolve_within(base or project_root, raw_path, label)
    if path.is_symlink() or not path.is_file():
        raise TargetedRereadEvidenceError(f"{label} is absent or is a symlink: {path}")
    if sha256_file(path) != expected_hash:
        raise TargetedRereadEvidenceError(f"{label} hash drift: {path}")
    expected_size = identity.get("size_bytes")
    if expected_size is not None and (
        not isinstance(expected_size, int) or path.stat().st_size != expected_size
    ):
        raise TargetedRereadEvidenceError(f"{label} size drift: {path}")
    return path


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise TargetedRereadEvidenceError(f"cannot read evidence config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise TargetedRereadEvidenceError("targeted-reread evidence config must be version 1")
    if payload.get("experiment_id") != "E-0016":
        raise TargetedRereadEvidenceError("unexpected targeted-reread experiment ID")
    if payload.get("phase") != "ORIGINAL_VARIANT_OCR_EVIDENCE":
        raise TargetedRereadEvidenceError("unexpected targeted-reread evidence phase")
    if payload.get("dataset_role") != "CALIBRATION":
        raise TargetedRereadEvidenceError("E-0016 evidence must remain CALIBRATION")
    if payload.get("evaluated_variants") != ["original"]:
        raise TargetedRereadEvidenceError("this evidence phase must evaluate only original crops")
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict) or set(dependencies) != _REQUIRED_DEPENDENCIES:
        raise TargetedRereadEvidenceError("E-0016 dependency set is incomplete or unexpected")
    expected = payload.get("expected_evidence_contract")
    if (
        not isinstance(expected, dict)
        or not expected
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in expected.values()
        )
    ):
        raise TargetedRereadEvidenceError(
            "expected evidence contract must contain nonnegative integers"
        )
    if payload.get("safety") != _REQUIRED_SAFETY:
        raise TargetedRereadEvidenceError("E-0016 evidence safety contract drifted")
    claim = payload.get("claim_boundary")
    if not isinstance(claim, str) or not claim.strip():
        raise TargetedRereadEvidenceError("E-0016 evidence claim boundary is absent")
    return payload


def _path_matches(project_root: Path, raw_path: Any, expected: Path) -> bool:
    if not isinstance(raw_path, str) or not raw_path:
        return False
    raw = Path(raw_path)
    if raw.is_absolute():
        return raw.resolve() == expected.resolve()
    candidate = (project_root / raw).resolve()
    return candidate == expected.resolve()


def _verify_input_chain(
    project_root: Path,
    input_manifest_path: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    if payload.get("format_version") != 1 or payload.get("experiment_id") != "E-0016":
        raise TargetedRereadEvidenceError("input manifest is not E-0016 format version 1")
    if payload.get("dataset_role") != "CALIBRATION":
        raise TargetedRereadEvidenceError("input manifest dataset role drifted")
    if payload.get("status") != "PASS_INPUT_CONTRACT_NO_VALUE_SELECTION":
        raise TargetedRereadEvidenceError("E-0016 input contract did not pass")
    if payload.get("state") != "TARGETED_REREAD_INPUTS_RENDERED_NO_VARIANT_SELECTED":
        raise TargetedRereadEvidenceError("E-0016 input state permits an unsupported selection")
    code = payload.get("code")
    if not isinstance(code, dict) or code.get("dirty") is not False:
        raise TargetedRereadEvidenceError("E-0016 input manifest was not built from clean code")
    acceptance = payload.get("acceptance")
    if not isinstance(acceptance, dict) or acceptance.get("contract_exact") is not True:
        raise TargetedRereadEvidenceError("E-0016 input manifest did not meet its exact contract")
    if acceptance.get("production_accuracy_approved") is not False:
        raise TargetedRereadEvidenceError("input manifest improperly claims production accuracy")
    diagnostics = payload.get("diagnostics")
    if (
        not isinstance(diagnostics, dict)
        or diagnostics.get("variant_selection_status") != "PENDING_OCR_EVIDENCE"
    ):
        raise TargetedRereadEvidenceError("input manifest already selected a variant")
    safety = payload.get("safety")
    if not isinstance(safety, dict):
        raise TargetedRereadEvidenceError("input manifest safety evidence is absent")
    false_flags = (
        "arithmetic_variant_selection_invoked",
        "automatic_confidence_promotion",
        "automatic_value_replacement",
        "automatic_variant_selection",
        "historical_reference_invoked",
        "role_a_or_searchable_reference_used",
        "schema_variant_selection_invoked",
        "source_or_upstream_overwrite",
        "ytd_derivation_invoked",
    )
    if any(safety.get(name) is not False for name in false_flags):
        raise TargetedRereadEvidenceError("input manifest contains a prohibited action")
    if safety.get("cross_page_crops") != 0 or safety.get("mapping_ineligible_page_crops") != 0:
        raise TargetedRereadEvidenceError("input manifest contains an unsafe crop")
    configured_permissions = safety.get("configured_permissions")
    if not isinstance(configured_permissions, dict) or any(
        value is not False for value in configured_permissions.values()
    ):
        raise TargetedRereadEvidenceError("input manifest safety permissions drifted")

    verified = 1
    for relative, expected_hash in payload.get("algorithm_files_sha256", {}).items():
        path = _resolve_within(project_root, relative, "input algorithm")
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise TargetedRereadEvidenceError(f"input algorithm hash drift: {relative}")
        verified += 1
    configurations = payload.get("configuration")
    if not isinstance(configurations, dict):
        raise TargetedRereadEvidenceError("input manifest configuration identities are absent")
    for name, identity in configurations.items():
        _verify_identity(project_root, identity, f"input configuration {name}")
        verified += 1
    upstream_identity = payload.get("upstream", {}).get("structural_fusion_artifact")
    upstream_path = _verify_identity(project_root, upstream_identity, "E-0015 upstream")
    verified += 1
    upstream = _read_json(upstream_path, "E-0015 upstream")
    if upstream.get("experiment_id") != "E-0015" or upstream.get("dataset_role") != "CALIBRATION":
        raise TargetedRereadEvidenceError("targeted-reread upstream is not E-0015 CALIBRATION")

    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        raise TargetedRereadEvidenceError("E-0016 input manifest has no documents")
    for document in documents:
        if not isinstance(document, dict):
            raise TargetedRereadEvidenceError("input document is not an object")
        _verify_identity(project_root, document.get("source"), "input source PDF")
        _verify_identity(project_root, document.get("role_c_seal"), "input Role C seal")
        verified += 2
        pages = document.get("pages")
        if not isinstance(pages, list) or not pages:
            raise TargetedRereadEvidenceError("input document has no page records")
        for page in pages:
            if not isinstance(page, dict):
                raise TargetedRereadEvidenceError("input page is not an object")
            _verify_identity(project_root, page.get("baseline_render"), "baseline render")
            _verify_identity(project_root, page.get("baseline_role_c_result"), "baseline Role C")
            verified += 2
            render_identity = page.get("render_manifest")
            if render_identity is not None:
                _verify_identity(
                    project_root,
                    render_identity,
                    "targeted page render manifest",
                    base=input_manifest_path.parent,
                )
                verified += 1
    return upstream, verified


def _runtime_records(
    runtime_path: Path, freeze_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        runtime = tomllib.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise TargetedRereadEvidenceError("cannot read pinned GPU runtime manifest") from exc
    if runtime.get("freeze_sha256") != sha256_file(freeze_path):
        raise TargetedRereadEvidenceError("GPU runtime/package-freeze hash drift")
    raw_models = runtime.get("models")
    if not isinstance(raw_models, dict):
        raise TargetedRereadEvidenceError("GPU runtime has no model identities")
    required = (
        "paddleocr_vl_1_6",
        "pp_doclayout_v3_safetensors",
        "pp_ocrv6_medium_det",
        "pp_ocrv6_medium_rec",
    )
    models = []
    for key in required:
        record = raw_models.get(key)
        if not isinstance(record, dict):
            raise TargetedRereadEvidenceError(f"GPU runtime model is absent: {key}")
        fields = ("repo_id", "revision", "weights_sha256", "weights_size_bytes")
        if any(field not in record for field in fields):
            raise TargetedRereadEvidenceError(f"GPU runtime model identity is incomplete: {key}")
        models.append({"key": key, **{field: record[field] for field in fields}})
    packages = runtime.get("packages")
    if not isinstance(packages, dict):
        raise TargetedRereadEvidenceError("GPU runtime package identities are absent")
    return dict(packages), models


def _portable_geometry_row(project_root: Path, row: Any) -> dict[str, Any]:
    record = geometry_row_v2_to_dict(row)
    for evidence in record["geometry"]["visual_cell_evidence"]:
        if evidence is None:
            continue
        raw_path = Path(evidence["source_image_path"])
        if raw_path.is_absolute():
            evidence["source_image_path"] = _project_relative(project_root, raw_path)
    return record


def _table_record(table: Any) -> dict[str, Any]:
    return {
        "table_index": table.table_index,
        "bbox": list(table.bbox),
        "status": table.status,
        "roles": table_roles_to_dict(table.roles),
        "header": list(table.header),
        "context_rows": [list(row) for row in table.context_rows],
        "raw_grid": [list(row) for row in table.raw_grid],
        "row_count": len(table.rows),
        "span_expansion_count": table.span_expansion_count,
        "warnings": list(table.warnings),
        "rows": [
            {
                "row_code": row.row_code,
                "source_grid_row": row.source_grid_row,
                "row": reader_row_to_dict(row.row),
                "warnings": list(row.warnings),
            }
            for row in table.rows
        ],
    }


def _strict_financial_line_count(texts: list[Any]) -> int:
    return sum(
        parse_financial_number_strict_grouping(str(text)).observation in _OBSERVED for text in texts
    )


def _validate_ppocrv6_result(payload: dict[str, Any]) -> tuple[int, int, int]:
    axes = ("rec_texts", "rec_scores", "rec_boxes", "rec_polys", "text_word_boxes")
    if payload.get("return_word_box") is not True:
        raise TargetedRereadEvidenceError("PP-OCRv6 result omitted word-box evidence")
    settings = payload.get("model_settings")
    if not isinstance(settings, dict):
        raise TargetedRereadEvidenceError("PP-OCRv6 result model settings are absent")
    if (
        settings.get("use_doc_preprocessor") is not False
        or settings.get("use_textline_orientation") is not False
    ):
        raise TargetedRereadEvidenceError("PP-OCRv6 result used implicit geometry processing")
    if any(not isinstance(payload.get(name), list) for name in axes):
        raise TargetedRereadEvidenceError("PP-OCRv6 result has a missing evidence axis")
    lengths = {name: len(payload[name]) for name in axes}
    if len(set(lengths.values())) != 1:
        raise TargetedRereadEvidenceError(f"PP-OCRv6 evidence axes disagree: {lengths}")
    texts = payload["rec_texts"]
    scores = payload["rec_scores"]
    if any(
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not math.isfinite(score)
        or not 0 <= score <= 1
        for score in scores
    ):
        raise TargetedRereadEvidenceError("PP-OCRv6 confidence axis is invalid")
    for box in payload["rec_boxes"]:
        if (
            not isinstance(box, list)
            or len(box) != 4
            or any(not isinstance(value, (int, float)) for value in box)
            or box[2] <= box[0]
            or box[3] <= box[1]
        ):
            raise TargetedRereadEvidenceError("PP-OCRv6 contains an invalid line box")
    raw_words = payload.get("text_word")
    if not isinstance(raw_words, list) or len(raw_words) != len(texts):
        raise TargetedRereadEvidenceError("PP-OCRv6 word/text axes disagree")
    word_count = sum(len(words) for words in raw_words if isinstance(words, list))
    if any(not isinstance(words, list) for words in raw_words):
        raise TargetedRereadEvidenceError("PP-OCRv6 word axis contains a non-list row")
    return len(texts), word_count, _strict_financial_line_count(texts)


def _verify_ppocrv6_run(
    *,
    project_root: Path,
    run_root: Path,
    original_path: Path,
    dependencies: dict[str, dict[str, Any]],
    runtime_models: dict[str, dict[str, Any]],
    runtime_packages: dict[str, Any],
    parse_full_table: bool,
    page_tag: str,
) -> tuple[dict[str, Any], Any | None, list[dict[str, Any]]]:
    manifest_path = run_root / "run_manifest.json"
    result_path = run_root / "ocr_result.json"
    manifest = _read_json(manifest_path, "PP-OCRv6 run manifest")
    result = _read_json(result_path, "PP-OCRv6 result")
    if manifest.get("state") != "OCR_COMPLETE":
        raise TargetedRereadEvidenceError("PP-OCRv6 run did not complete")
    if manifest.get("dataset_role") != "CALIBRATION":
        raise TargetedRereadEvidenceError("PP-OCRv6 dataset role drifted")
    if manifest.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY":
        raise TargetedRereadEvidenceError("PP-OCRv6 was assigned excess authority")
    code = manifest.get("code")
    if not isinstance(code, dict) or code.get("dirty") is not False:
        raise TargetedRereadEvidenceError("PP-OCRv6 inference did not record clean code")
    input_identity = manifest.get("input")
    if not isinstance(input_identity, dict):
        raise TargetedRereadEvidenceError("PP-OCRv6 input identity is absent")
    if input_identity.get("sha256") != sha256_file(original_path):
        raise TargetedRereadEvidenceError("PP-OCRv6 input hash differs from targeted crop")
    if not _path_matches(project_root, input_identity.get("path"), original_path):
        raise TargetedRereadEvidenceError("PP-OCRv6 manifest input path differs from crop")
    if not _path_matches(project_root, result.get("input_path"), original_path):
        raise TargetedRereadEvidenceError("PP-OCRv6 result input path differs from crop")
    configuration = manifest.get("configuration")
    if not isinstance(configuration, dict):
        raise TargetedRereadEvidenceError("PP-OCRv6 configuration record is absent")
    if configuration.get("sha256") != dependencies["ppocrv6_model_config"]["sha256"]:
        raise TargetedRereadEvidenceError("PP-OCRv6 model configuration hash drift")
    if configuration.get("runner_sha256") != dependencies["ppocrv6_runner"]["sha256"]:
        raise TargetedRereadEvidenceError("PP-OCRv6 runner hash drift")
    if configuration.get("network_policy") != "PROCESS_SOCKET_CONNECT_DENIED":
        raise TargetedRereadEvidenceError("PP-OCRv6 network policy was not fail-closed")
    if configuration.get("implicit_orientation_or_unwarp") is not False:
        raise TargetedRereadEvidenceError("PP-OCRv6 used an unrecorded geometry transform")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise TargetedRereadEvidenceError("PP-OCRv6 runtime record is absent")
    if runtime.get("manifest_sha256") != dependencies["gpu_runtime_manifest"]["sha256"]:
        raise TargetedRereadEvidenceError("PP-OCRv6 runtime manifest hash drift")
    if runtime.get("device") != "cpu" or runtime.get("compiled_with_cuda") is not False:
        raise TargetedRereadEvidenceError("PP-OCRv6 runtime device contract drift")
    for package in ("paddleocr", "paddlepaddle", "paddlex"):
        if str(runtime.get(package)) != str(runtime_packages.get(package)):
            raise TargetedRereadEvidenceError(f"PP-OCRv6 package version drift: {package}")
    run_models = runtime.get("models")
    if not isinstance(run_models, list) or len(run_models) != 2:
        raise TargetedRereadEvidenceError("PP-OCRv6 run lacks two model identities")
    for record in run_models:
        key = record.get("key") if isinstance(record, dict) else None
        expected = runtime_models.get(str(key))
        if expected is None:
            raise TargetedRereadEvidenceError(f"unexpected PP-OCRv6 model key: {key}")
        for field in ("repo_id", "revision", "weights_sha256", "weights_size_bytes"):
            if record.get(field) != expected.get(field):
                raise TargetedRereadEvidenceError(f"PP-OCRv6 model identity drift: {key}.{field}")
    artifact_identity = manifest.get("artifacts", {}).get("ocr_result")
    if not isinstance(artifact_identity, dict):
        raise TargetedRereadEvidenceError("PP-OCRv6 result identity is absent")
    if artifact_identity.get("path") != "ocr_result.json":
        raise TargetedRereadEvidenceError("PP-OCRv6 result path is unexpected")
    if artifact_identity.get("sha256") != sha256_file(result_path):
        raise TargetedRereadEvidenceError("PP-OCRv6 result hash drift")
    if artifact_identity.get("size_bytes") != result_path.stat().st_size:
        raise TargetedRereadEvidenceError("PP-OCRv6 result size drift")

    line_count, word_count, financial_lines = _validate_ppocrv6_result(result)
    run_metrics = manifest.get("metrics")
    if not isinstance(run_metrics, dict):
        raise TargetedRereadEvidenceError("PP-OCRv6 run metrics are absent")
    if (
        run_metrics.get("line_count") != line_count
        or run_metrics.get("word_token_count") != word_count
    ):
        raise TargetedRereadEvidenceError("PP-OCRv6 manifest/result counts disagree")
    parser_record: dict[str, Any] = {
        "status": "NOT_APPLICABLE_REGION_HAS_NO_PERIOD_HEADER",
        "axis_count": 0,
        "row_count": 0,
        "financial_row_count": 0,
        "invalid_cell_count": 0,
        "rows": [],
    }
    parsed = None
    if parse_full_table:
        parser_config = load_word_box_reconstruction_v2_config(
            _resolve_within(
                project_root,
                dependencies["word_box_reconstruction_config"]["path"],
                "word-box parser config",
            )
        )
        try:
            parsed = parse_ppocrv6_word_box_page_v2(
                result_path,
                parser_config,
                page_tag=page_tag,
                source_image_path=original_path,
            )
        except WordBoxReconstructionError as exc:
            parser_record = {
                **parser_record,
                "status": "UNRESOLVED_FULL_TABLE_PARSE",
                "error": str(exc),
            }
        else:
            financial_rows = sum(
                any(cell.observation in _OBSERVED for cell in row.row.cells) for row in parsed.rows
            )
            invalid_cells = sum(
                cell.observation is ObservationKind.INVALID
                for row in parsed.rows
                for cell in row.row.cells
            )
            parser_record = {
                "status": "PARSED_FULL_TABLE",
                "axis_count": len(parsed.axes),
                "axes": [
                    {
                        "axis_id": axis.axis_id,
                        "raw_header": axis.raw_header,
                        "right_edge": axis.right_edge,
                        "header_line_index": axis.header_line_index,
                    }
                    for axis in parsed.axes
                ],
                "row_count": len(parsed.rows),
                "financial_row_count": financial_rows,
                "invalid_cell_count": invalid_cells,
                "unassigned_numeric_line_indices": list(parsed.unassigned_numeric_line_indices),
                "trailing_context_row_count": len(parsed.trailing_context_rows),
                "rows": [_portable_geometry_row(project_root, row) for row in parsed.rows],
            }
    output_files = [
        _file_record(project_root, manifest_path),
        _file_record(project_root, result_path),
    ]
    record = {
        "state": manifest["state"],
        "evidence_role": manifest["evidence_role"],
        "code": code,
        "input": _file_record(project_root, original_path),
        "outputs": output_files,
        "runtime": runtime,
        "metrics": {
            **run_metrics,
            "strict_financial_token_line_count": financial_lines,
        },
        "recognized_lines": [
            {
                "line_index": index,
                "text": str(text),
                "score": float(score),
                "box": list(box),
            }
            for index, (text, score, box) in enumerate(
                zip(result["rec_texts"], result["rec_scores"], result["rec_boxes"], strict=True)
            )
        ],
        "parser": parser_record,
        "automatic_truth_or_schema_promotion": False,
    }
    return record, parsed, output_files


def _block_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = payload.get("parsing_res_list")
    if not isinstance(blocks, list):
        raise TargetedRereadEvidenceError("PaddleOCR-VL result has no parsing blocks")
    records = []
    for block in blocks:
        if not isinstance(block, dict):
            raise TargetedRereadEvidenceError("PaddleOCR-VL parsing block is not an object")
        bbox = block.get("block_bbox")
        if bbox is not None and (not isinstance(bbox, list) or len(bbox) != 4):
            raise TargetedRereadEvidenceError("PaddleOCR-VL block bbox is invalid")
        records.append(
            {
                "block_label": str(block.get("block_label", "")),
                "block_bbox": bbox,
                "block_content": str(block.get("block_content", "")),
            }
        )
    return records


def _verify_paddleocr_vl_run(
    *,
    project_root: Path,
    run_root: Path,
    metric_path: Path,
    original_path: Path,
    dependencies: dict[str, dict[str, Any]],
    page_tag: str,
) -> tuple[dict[str, Any], Any | None, list[dict[str, Any]]]:
    result_path = run_root / f"{original_path.stem}_res.json"
    result = _read_json(result_path, "PaddleOCR-VL result")
    metric = _read_json(metric_path, "PaddleOCR-VL execution metrics")
    if metric.get("status") != "PASS" or metric.get("return_code") != 0:
        raise TargetedRereadEvidenceError("PaddleOCR-VL process did not complete successfully")
    command = metric.get("command")
    expected_tail = [
        "bash",
        dependencies["paddleocr_vl_runner"]["path"],
        _project_relative(project_root, original_path),
        _project_relative(project_root, run_root),
    ]
    if not isinstance(command, list) or command[-4:] != expected_tail:
        raise TargetedRereadEvidenceError("PaddleOCR-VL metric command/input/output drift")
    if not _path_matches(project_root, result.get("input_path"), original_path):
        raise TargetedRereadEvidenceError("PaddleOCR-VL result input path differs from crop")
    width = result.get("width")
    height = result.get("height")
    if (
        not isinstance(width, int)
        or not isinstance(height, int)
        or isinstance(width, bool)
        or isinstance(height, bool)
        or width < 1
        or height < 1
    ):
        raise TargetedRereadEvidenceError("PaddleOCR-VL result dimensions are invalid")
    settings = result.get("model_settings")
    if not isinstance(settings, dict):
        raise TargetedRereadEvidenceError("PaddleOCR-VL model settings are absent")
    if settings.get("use_doc_preprocessor") is not False:
        raise TargetedRereadEvidenceError("PaddleOCR-VL used an implicit document preprocessor")
    if settings.get("use_layout_detection") is not True:
        raise TargetedRereadEvidenceError("PaddleOCR-VL omitted required layout detection")
    try:
        with Image.open(original_path) as image:
            source_dimensions = image.size
    except OSError as exc:
        raise TargetedRereadEvidenceError("cannot decode PaddleOCR-VL input crop") from exc
    if source_dimensions != (width, height):
        raise TargetedRereadEvidenceError("PaddleOCR-VL result dimensions differ from crop")
    blocks = _block_records(result)

    parser_config = load_vlm_table_parser_config(
        _resolve_within(
            project_root,
            dependencies["vlm_table_parser_config"]["path"],
            "VLM table parser config",
        )
    )
    parsed = None
    try:
        parsed = parse_paddle_vl_page_v2(result_path, parser_config, page_tag=page_tag)
    except ReaderOutputV2Error as exc:
        parser_record: dict[str, Any] = {
            "status": "NO_TABLE_BLOCK"
            if str(exc) == "PaddleOCR-VL result contains no table block"
            else "UNRESOLVED_PARSER_ERROR",
            "error": str(exc),
            "table_count": 0,
            "parsed_table_count": 0,
            "unresolved_table_count": 0,
            "row_count": 0,
            "financial_row_count": 0,
            "invalid_cell_count": 0,
            "tables": [],
        }
    else:
        parsed_tables = sum(table.status == "PARSED" for table in parsed.tables)
        financial_rows = sum(
            any(cell.observation in _OBSERVED for cell in row.cells) for row in parsed.reader_rows
        )
        invalid_cells = sum(
            cell.observation is ObservationKind.INVALID
            for row in parsed.reader_rows
            for cell in row.cells
        )
        parser_record = {
            "status": "PARSED" if parsed.unresolved_table_count == 0 else "PARTIALLY_UNRESOLVED",
            "table_count": len(parsed.tables),
            "parsed_table_count": parsed_tables,
            "unresolved_table_count": parsed.unresolved_table_count,
            "row_count": len(parsed.reader_rows),
            "financial_row_count": financial_rows,
            "invalid_cell_count": invalid_cells,
            "context_text": parsed.context_text,
            "tables": [_table_record(table) for table in parsed.tables],
        }

    if run_root.is_symlink() or not run_root.is_dir():
        raise TargetedRereadEvidenceError(f"PaddleOCR-VL output directory is absent: {run_root}")
    output_files = [
        _file_record(project_root, path) for path in sorted(run_root.rglob("*")) if path.is_file()
    ]
    if not output_files or result_path not in [
        project_root / item["path"] for item in output_files
    ]:
        raise TargetedRereadEvidenceError("PaddleOCR-VL result is absent from its output set")
    output_files.append(_file_record(project_root, metric_path))
    record = {
        "state": "OCR_COMPLETE",
        "inference_git_commit_evidence": "NOT_SELF_RECORDED_BY_RUNNER",
        "input": _file_record(project_root, original_path),
        "outputs": output_files,
        "execution_metrics": metric,
        "model_settings": settings,
        "blocks": blocks,
        "parser": parser_record,
        "automatic_truth_or_schema_promotion": False,
    }
    return record, parsed, output_files


def _baseline_pages(upstream: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for document in upstream.get("documents", []):
        key = document.get("key") if isinstance(document, dict) else None
        pages = document.get("pages") if isinstance(document, dict) else None
        if not isinstance(key, str) or not isinstance(pages, list):
            raise TargetedRereadEvidenceError("E-0015 document/page structure is invalid")
        for page in pages:
            number = page.get("page") if isinstance(page, dict) else None
            if not isinstance(number, int) or (key, number) in records:
                raise TargetedRereadEvidenceError("E-0015 page identity is invalid or duplicate")
            records[(key, number)] = page
    return records


def _baseline_summary(page: dict[str, Any]) -> dict[str, Any]:
    role_b = page.get("role_b")
    role_c = page.get("role_c")
    comparison = page.get("comparison")
    if not all(isinstance(value, dict) for value in (role_b, role_c, comparison)):
        raise TargetedRereadEvidenceError("E-0015 page lacks reader comparison evidence")
    tables = role_b.get("tables")
    counts = comparison.get("counts")
    if not isinstance(tables, list) or not isinstance(counts, dict):
        raise TargetedRereadEvidenceError("E-0015 page reader metrics are invalid")
    return {
        "role_b_row_count": counts.get("role_b_rows"),
        "role_c_row_count": counts.get("role_c_rows"),
        "role_b_invalid_cell_count": counts.get("role_b_invalid_cells"),
        "role_c_invalid_cell_count": counts.get("role_c_invalid_cells"),
        "role_b_table_statuses": [table.get("status") for table in tables],
        "role_b_raw_grid_row_count": sum(len(table.get("raw_grid", [])) for table in tables),
        "alignment_actions": counts.get("alignment_actions"),
        "scope_reason": page.get("scope_reason"),
        "mapping_eligible": page.get("mapping_eligible"),
    }


def _artifact_set_hash(records: list[dict[str, Any]]) -> str:
    unique = {record["path"]: record for record in records}
    if len(unique) != len(records):
        raise TargetedRereadEvidenceError("reader output artifact was recorded more than once")
    return stable_records_hash(
        f"{record['sha256']}  {path}  {record['size_bytes']}"
        for path, record in sorted(unique.items())
    )


def seal_targeted_reread_evidence(
    *,
    project_root: Path,
    config_path: Path,
    output_path: Path,
    git_state: dict[str, Any],
    allow_dirty: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    config_path = config_path.resolve()
    output_path = output_path.resolve()
    try:
        config_path.relative_to(project_root)
        output_path.relative_to(project_root)
    except ValueError as exc:
        raise TargetedRereadEvidenceError(
            "config and output must stay inside project root"
        ) from exc
    if output_path.exists():
        raise TargetedRereadEvidenceError(f"refusing to overwrite evidence: {output_path}")
    if not isinstance(git_state.get("commit"), str) or not isinstance(git_state.get("dirty"), bool):
        raise TargetedRereadEvidenceError("invalid Git state")
    if git_state["dirty"] and not allow_dirty:
        raise TargetedRereadEvidenceError("refusing formal E-0016 evidence from a dirty worktree")

    config = _load_config(config_path)
    dependencies: dict[str, dict[str, Any]] = config["dependencies"]
    verified_dependencies: dict[str, dict[str, Any]] = {}
    for name, identity in dependencies.items():
        path = _verify_identity(project_root, identity, f"E-0016 dependency {name}")
        verified_dependencies[name] = _file_record(project_root, path)
    input_manifest_path = _verify_identity(
        project_root, config.get("input_manifest"), "E-0016 input manifest"
    )
    input_payload = _read_json(input_manifest_path, "E-0016 input manifest")
    upstream, input_chain_file_count = _verify_input_chain(
        project_root, input_manifest_path, input_payload
    )
    baseline_pages = _baseline_pages(upstream)

    runtime_packages, runtime_model_list = _runtime_records(
        _resolve_within(
            project_root,
            dependencies["gpu_runtime_manifest"]["path"],
            "GPU runtime manifest",
        ),
        _resolve_within(
            project_root,
            dependencies["gpu_package_freeze"]["path"],
            "GPU package freeze",
        ),
    )
    runtime_models = {record["key"]: record for record in runtime_model_list}
    scope_policy = load_scope_policy(
        _resolve_within(project_root, dependencies["scope_policy"]["path"], "scope policy")
    )

    input_root = input_manifest_path.parent
    metrics: Counter[str] = Counter()
    output_artifacts: list[dict[str, Any]] = []
    expected_pp_results: set[Path] = set()
    expected_vlm_results: set[Path] = set()
    expected_vlm_metrics: set[Path] = set()
    document_records = []
    for document in input_payload["documents"]:
        key = document.get("key")
        if not isinstance(key, str) or not key:
            raise TargetedRereadEvidenceError("input document has no stable key")
        metrics["document_count"] += 1
        page_records = []
        for page in document["pages"]:
            plan = page.get("plan")
            if not isinstance(plan, dict):
                raise TargetedRereadEvidenceError(f"{key} page has no reread plan")
            regions = plan.get("regions")
            if not isinstance(regions, list):
                raise TargetedRereadEvidenceError(f"{key} page reread regions are invalid")
            if not regions:
                continue
            metrics["planned_page_count"] += 1
            if page.get("mapping_eligible") is not True:
                metrics["mapping_ineligible_region_count"] += len(regions)
                raise TargetedRereadEvidenceError("mapping-ineligible page received OCR regions")
            render_identity = page.get("render_manifest")
            page_manifest_path = _verify_identity(
                project_root,
                render_identity,
                f"{key} page render manifest",
                base=input_root,
            )
            page_manifest = _read_json(page_manifest_path, "targeted page render manifest")
            if (
                page_manifest.get("state") != "TARGETED_REREAD_INPUTS_RENDERED"
                or page_manifest.get("selection_status") != "PENDING_OCR_EVIDENCE"
                or page_manifest.get("safety") != _EXPECTED_PAGE_SAFETY
                or page_manifest.get("page") != page.get("page")
                or page_manifest.get("statement_type") != page.get("statement_type")
                or page_manifest.get("source") != document.get("source")
            ):
                raise TargetedRereadEvidenceError(f"{key} targeted page manifest drift")
            rendered_regions = page_manifest.get("regions")
            if not isinstance(rendered_regions, list) or len(rendered_regions) != len(regions):
                raise TargetedRereadEvidenceError(f"{key} rendered region count drift")
            baseline_page = baseline_pages.get((key, page["page"]))
            if not isinstance(baseline_page, dict):
                raise TargetedRereadEvidenceError(
                    f"E-0015 baseline page is absent: {key} {page['page']}"
                )
            baseline = _baseline_summary(baseline_page)
            region_records = []
            for planned, rendered in zip(regions, rendered_regions, strict=True):
                if rendered.get("plan") != planned:
                    raise TargetedRereadEvidenceError("planned/rendered targeted region drift")
                region_id = planned.get("region_id")
                region_kind = planned.get("region_kind")
                if not isinstance(region_id, str) or not isinstance(region_kind, str):
                    raise TargetedRereadEvidenceError("targeted region identity is invalid")
                metrics["region_count"] += 1
                kind_metric = {
                    "FULL_TABLE_STRUCTURAL_RECOVERY": "full_table_region_count",
                    "ROW_BAND_STRUCTURAL_RECOVERY": "row_band_region_count",
                    "NUMERIC_CELL_STRIP_REREAD": "numeric_cell_strip_region_count",
                }.get(region_kind)
                if kind_metric is None:
                    raise TargetedRereadEvidenceError(
                        f"unknown targeted region kind: {region_kind}"
                    )
                metrics[kind_metric] += 1
                variants = rendered.get("variants")
                if not isinstance(variants, list) or not variants:
                    raise TargetedRereadEvidenceError("targeted region has no image variants")
                original = None
                variant_records = []
                for variant in variants:
                    if not isinstance(variant, dict):
                        raise TargetedRereadEvidenceError("targeted image variant is invalid")
                    variant_path = _resolve_within(
                        page_manifest_path.parent,
                        variant.get("path"),
                        "targeted image variant",
                    )
                    if variant.get("sha256") != sha256_file(variant_path):
                        raise TargetedRereadEvidenceError("targeted image variant hash drift")
                    if variant.get("selection_status") != "PENDING_OCR_EVIDENCE":
                        raise TargetedRereadEvidenceError("targeted image variant was preselected")
                    metrics["source_variant_count"] += 1
                    record = {
                        **_file_record(project_root, variant_path),
                        "name": variant.get("name"),
                        "geometry_transform_kind": variant.get("geometry_transform_kind"),
                        "evaluated": variant.get("name") == "original",
                        "selected": False,
                    }
                    variant_records.append(record)
                    if variant.get("name") == "original":
                        if original is not None:
                            raise TargetedRereadEvidenceError(
                                "targeted region has duplicate originals"
                            )
                        original = variant_path
                        if variant.get("geometry_transform_kind") != "IDENTITY":
                            raise TargetedRereadEvidenceError(
                                "original crop has non-identity geometry"
                            )
                if original is None:
                    raise TargetedRereadEvidenceError("targeted region has no original crop")
                metrics["evaluated_original_variant_count"] += 1
                metrics["unevaluated_variant_count"] += len(variants) - 1

                original_relative_to_input = original.relative_to(input_root)
                reader_tail = original_relative_to_input.with_suffix("")
                requested = planned.get("readers")
                if (
                    not isinstance(requested, list)
                    or not requested
                    or len(set(requested)) != len(requested)
                ):
                    raise TargetedRereadEvidenceError("targeted region has no requested readers")
                metrics["requested_reader_run_count"] += len(requested)
                reader_records: dict[str, Any] = {}
                parsed_pp = None
                parsed_vlm = None
                if "PP_OCRV6_MEDIUM" in requested:
                    pp_root = input_root / "ocr" / "ppocrv6" / reader_tail
                    pp_result = pp_root / "ocr_result.json"
                    expected_pp_results.add(pp_result.resolve())
                    pp_record, parsed_pp, artifacts = _verify_ppocrv6_run(
                        project_root=project_root,
                        run_root=pp_root,
                        original_path=original,
                        dependencies=dependencies,
                        runtime_models=runtime_models,
                        runtime_packages=runtime_packages,
                        parse_full_table=region_kind == "FULL_TABLE_STRUCTURAL_RECOVERY",
                        page_tag=f"e0016-{len(document_records):02d}-{page['page']:04d}-{region_id}-c",
                    )
                    reader_records["PP_OCRV6_MEDIUM"] = pp_record
                    output_artifacts.extend(artifacts)
                    metrics["completed_reader_run_count"] += 1
                    metrics["ppocrv6_run_count"] += 1
                    metrics["ppocrv6_line_count"] += pp_record["metrics"]["line_count"]
                    metrics["ppocrv6_word_token_count"] += pp_record["metrics"]["word_token_count"]
                    metrics["ppocrv6_strict_financial_token_line_count"] += pp_record["metrics"][
                        "strict_financial_token_line_count"
                    ]
                    if region_kind == "FULL_TABLE_STRUCTURAL_RECOVERY" and parsed_pp is not None:
                        metrics["full_table_ppocrv6_parse_success_count"] += 1
                        metrics["full_table_ppocrv6_two_axis_count"] += len(parsed_pp.axes) == 2
                        metrics["full_table_ppocrv6_row_count"] += len(parsed_pp.rows)
                if "PADDLEOCR_VL_1_6" in requested:
                    vlm_root = input_root / "ocr" / "paddleocr-vl" / reader_tail
                    vlm_result = vlm_root / f"{original.stem}_res.json"
                    vlm_metric = (
                        input_root
                        / "metrics"
                        / "paddleocr-vl"
                        / original_relative_to_input.with_suffix(".json")
                    )
                    expected_vlm_results.add(vlm_result.resolve())
                    expected_vlm_metrics.add(vlm_metric.resolve())
                    vlm_record, parsed_vlm, artifacts = _verify_paddleocr_vl_run(
                        project_root=project_root,
                        run_root=vlm_root,
                        metric_path=vlm_metric,
                        original_path=original,
                        dependencies=dependencies,
                        page_tag=f"e0016-{len(document_records):02d}-{page['page']:04d}-{region_id}-b",
                    )
                    reader_records["PADDLEOCR_VL_1_6"] = vlm_record
                    output_artifacts.extend(artifacts)
                    metrics["completed_reader_run_count"] += 1
                    metrics["paddleocr_vl_run_count"] += 1
                    metrics["paddleocr_vl_pass_count"] += 1
                    parser = vlm_record["parser"]
                    metrics["paddleocr_vl_table_block_count"] += parser["table_count"]
                    metrics["paddleocr_vl_parsed_table_count"] += parser["parsed_table_count"]
                    metrics["paddleocr_vl_unresolved_table_count"] += parser[
                        "unresolved_table_count"
                    ]
                    metrics["paddleocr_vl_parsed_row_count"] += parser["row_count"]
                    metrics["paddleocr_vl_invalid_cell_count"] += parser["invalid_cell_count"]
                    metrics["paddleocr_vl_no_table_region_count"] += (
                        parser["status"] == "NO_TABLE_BLOCK"
                    )
                    if region_kind == "FULL_TABLE_STRUCTURAL_RECOVERY" and parsed_vlm is not None:
                        metrics["full_table_paddleocr_vl_parse_success_count"] += 1
                        metrics["full_table_paddleocr_vl_row_count"] += len(parsed_vlm.reader_rows)
                unknown_readers = set(requested) - {"PP_OCRV6_MEDIUM", "PADDLEOCR_VL_1_6"}
                if unknown_readers:
                    raise TargetedRereadEvidenceError(
                        f"unsupported targeted readers: {unknown_readers}"
                    )

                comparison = None
                if region_kind == "FULL_TABLE_STRUCTURAL_RECOVERY" and (
                    parsed_pp is not None and parsed_vlm is not None
                ):
                    role_b_rows = tuple(
                        StructuredReaderRow(row.row, row.row_code)
                        for table in parsed_vlm.tables
                        for row in table.rows
                    )
                    role_c_rows = tuple(
                        StructuredReaderRow(row.row, row.row_code) for row in parsed_pp.rows
                    )
                    comparison = compare_structural_readers_v2(
                        role_b_rows,
                        role_c_rows,
                        statement_type=page["statement_type"],
                        page_mapping_eligible=True,
                        upstream_scope_reason=str(baseline["scope_reason"]),
                        scope_policy=scope_policy,
                        role_b_context_text=parsed_vlm.context_text,
                    )
                    counts = comparison["counts"]
                    metrics["full_table_reader_row_count_disagreement_count"] += (
                        counts["role_b_rows"] != counts["role_c_rows"]
                    )
                    metrics["full_table_paired_observed_cell_count"] += counts[
                        "paired_observed_cells"
                    ]
                    metrics["full_table_exact_paired_observed_cell_count"] += counts[
                        "exact_paired_observed_cells"
                    ]

                region_records.append(
                    {
                        "region_id": region_id,
                        "region_kind": region_kind,
                        "target_dpi": planned.get("target_dpi"),
                        "includes_period_header_pixels": planned.get(
                            "includes_period_header_pixels"
                        ),
                        "period_binding_from_reread_allowed": planned.get(
                            "period_binding_from_reread_allowed"
                        ),
                        "escalations": planned.get("escalations"),
                        "upstream_role_b_indices": planned.get("role_b_indices"),
                        "upstream_role_c_indices": planned.get("role_c_indices"),
                        "upstream_page": baseline,
                        "variants": variant_records,
                        "evaluated_variant": "original",
                        "variant_selection_status": "NO_VARIANT_SELECTED_BASELINE_EVIDENCE_ONLY",
                        "readers": reader_records,
                        "full_table_comparison": comparison,
                        "automatic_value_replacement": False,
                        "automatic_confidence_promotion": False,
                    }
                )
            page_records.append(
                {
                    "page": page["page"],
                    "statement_type": page["statement_type"],
                    "mapping_eligible": page["mapping_eligible"],
                    "render_manifest": _file_record(project_root, page_manifest_path),
                    "regions": region_records,
                }
            )
        document_records.append(
            {
                "key": key,
                "source": document["source"],
                "pages_with_rereads": page_records,
            }
        )

    actual_pp_results = {
        path.resolve() for path in (input_root / "ocr" / "ppocrv6").rglob("ocr_result.json")
    }
    actual_vlm_results = {
        path.resolve() for path in (input_root / "ocr" / "paddleocr-vl").rglob("*_res.json")
    }
    actual_vlm_metrics = {
        path.resolve() for path in (input_root / "metrics" / "paddleocr-vl").rglob("*.json")
    }
    if actual_pp_results != expected_pp_results:
        raise TargetedRereadEvidenceError("PP-OCRv6 output set differs from requested originals")
    if actual_vlm_results != expected_vlm_results:
        raise TargetedRereadEvidenceError(
            "PaddleOCR-VL output set differs from requested originals"
        )
    if actual_vlm_metrics != expected_vlm_metrics:
        raise TargetedRereadEvidenceError(
            "PaddleOCR-VL metric set differs from requested originals"
        )

    metrics["automatic_variant_selection_count"] = 0
    metrics["automatic_value_replacement_count"] = 0
    metrics["automatic_confidence_promotion_count"] = 0
    metrics["mapping_ineligible_region_count"] += 0
    metrics["report_norm_ids_proposed_or_added"] = 0
    observed_metrics = dict(sorted(metrics.items()))
    if observed_metrics != config["expected_evidence_contract"]:
        raise TargetedRereadEvidenceError(
            "E-0016 OCR evidence contract mismatch: "
            f"observed={observed_metrics}, expected={config['expected_evidence_contract']}"
        )

    algorithm_hashes = {}
    for relative in config.get("algorithm_files", []):
        path = _resolve_within(project_root, relative, "evidence algorithm")
        if not path.is_file():
            raise TargetedRereadEvidenceError(f"evidence algorithm is absent: {relative}")
        algorithm_hashes[relative] = sha256_file(path)
    artifact = {
        "format_version": 1,
        "experiment_id": "E-0016",
        "phase": "ORIGINAL_VARIANT_OCR_EVIDENCE",
        "date": datetime.now(UTC).date().isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "design": "HASH_BOUND_TARGETED_ORIGINAL_CROP_READER_EVIDENCE_WITHOUT_SELECTION",
        "dataset_role": "CALIBRATION",
        "status": "PASS_ORIGINAL_CROP_OCR_EVIDENCE_WITH_RETAINED_FAILURES_NO_VALUE_SELECTION",
        "claim_boundary": config["claim_boundary"],
        "code": dict(git_state),
        "algorithm_files_sha256": dict(sorted(algorithm_hashes.items())),
        "configuration": {
            "experiment": _file_record(project_root, config_path),
            **verified_dependencies,
        },
        "upstream": {
            "targeted_reread_input_manifest": _file_record(project_root, input_manifest_path),
            "input_generation_code": input_payload["code"],
            "verified_input_chain_file_count": input_chain_file_count,
        },
        "runtime": {
            "packages": runtime_packages,
            "models": runtime_model_list,
            "paddleocr_vl_inference_git_commit_evidence": "NOT_SELF_RECORDED_BY_RUNNER",
            "ppocrv6_inference_git_commits": sorted(
                {
                    region["readers"]["PP_OCRV6_MEDIUM"]["code"]["commit"]
                    for document in document_records
                    for page in document["pages_with_rereads"]
                    for region in page["regions"]
                    if "PP_OCRV6_MEDIUM" in region["readers"]
                }
            ),
        },
        "reader_output_artifact_set": {
            "sha256": _artifact_set_hash(output_artifacts),
            "file_count": len(output_artifacts),
            "files": sorted(output_artifacts, key=lambda item: item["path"]),
        },
        "metrics": observed_metrics,
        "documents": document_records,
        "interpretation": {
            "reader_agreement_is_truth": False,
            "higher_dpi_guarantees_structural_recovery": False,
            "headerless_region_can_rebind_periods": False,
            "history_schema_arithmetic_or_report_norm_id_used": False,
            "original_variant_was_evaluated_as_baseline_not_selected_as_best": True,
            "full_table_agreement_is_conditional_cross_reader_evidence_not_accuracy": True,
        },
        "safety": {
            "automatic_variant_selection": False,
            "automatic_value_replacement": False,
            "automatic_confidence_promotion": False,
            "history_invoked": False,
            "schema_mapping_invoked": False,
            "arithmetic_invoked": False,
            "report_norm_id_order_or_magnitude_used": False,
            "report_norm_ids_proposed_or_added": 0,
        },
        "acceptance": {
            "configured": config["expected_evidence_contract"],
            "observed": observed_metrics,
            "contract_exact": True,
            "all_requested_original_reader_runs_complete": True,
            "variant_selection_evaluated": False,
            "human_gold_evaluated": False,
            "accuracy_threshold_evaluated": False,
            "production_accuracy_approved": False,
        },
    }
    digest = atomic_write_json(output_path, artifact)
    return {
        **artifact,
        "output_path": _project_relative(project_root, output_path),
        "sha256": digest,
    }
