from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.line_recognition_metrics import (
    normalize_evaluation_line,
    score_reader,
)
from bctc_ai.mapping.ordered_subgraph import (
    MappingBlockContext,
    PdfGraphRow,
    align_ordered_subgraph,
    build_schema_graph,
    load_ordered_subgraph_policy,
)
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)
from bctc_ai.reference.human_review import (
    ReviewedDecision,
    ReviewedDocument,
    TemplateMembership,
    load_human_review_registry,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all


class LogicalRowLabelReviewEvaluationError(RuntimeError):
    """Raised when sealed E-0036 outputs cannot be evaluated without leakage."""


_READER_FIELDS = {
    "vietocr": ("VIETOCR_VGG_TRANSFORMER", "raw_prediction"),
    "deepseek_ocr2": ("DEEPSEEK_OCR_2", "proposal_text"),
}
_INFERENCE_STATE = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
_SEAL_STATE = "BASELINE_OUTPUTS_HASH_SEALED_BEFORE_REVIEW_ACCESS"


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, value: Path | str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise LogicalRowLabelReviewEvaluationError(
            f"unsafe project-relative evaluation path: {value}"
        )
    path = (project_root / raw).resolve()
    if not path.is_relative_to(project_root):
        raise LogicalRowLabelReviewEvaluationError(f"path escapes project root: {value}")
    return path


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LogicalRowLabelReviewEvaluationError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelReviewEvaluationError(f"{label} must be an object")
    return payload


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise LogicalRowLabelReviewEvaluationError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise LogicalRowLabelReviewEvaluationError(f"{label} must be an object")
    return payload


def _artifact(project_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LogicalRowLabelReviewEvaluationError(f"artifact is absent: {path}")
    return {
        "path": path.relative_to(project_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _verify_artifact(project_root: Path, record: object, label: str) -> Path:
    if not isinstance(record, dict) or set(record) != {"path", "size_bytes", "sha256"}:
        raise LogicalRowLabelReviewEvaluationError(f"{label} identity is invalid")
    path = _resolve(project_root, str(record["path"]))
    if (
        not path.is_file()
        or path.stat().st_size != int(record["size_bytes"])
        or sha256_file(path) != str(record["sha256"])
    ):
        raise LogicalRowLabelReviewEvaluationError(f"{label} is absent or hash-drifted")
    return path


def _verify_config_record(project_root: Path, record: object, label: str) -> Path:
    if not isinstance(record, dict):
        raise LogicalRowLabelReviewEvaluationError(f"{label} registry is invalid")
    path = _resolve(project_root, str(record.get("path", "")))
    if (
        not path.is_file()
        or path.stat().st_size != int(record.get("size_bytes", -1))
        or sha256_file(path) != str(record.get("sha256", ""))
    ):
        raise LogicalRowLabelReviewEvaluationError(f"{label} is absent or hash-drifted")
    return path


def _load_control(project_root: Path, path: Path) -> dict[str, Any]:
    config = _load_yaml(path, "E-0036 experiment control")
    evaluation = config.get("evaluation_only_after_both_baseline_seals")
    if (
        config.get("version") != 1
        or config.get("experiment_id") != "E-0036"
        or config.get("dataset_role") != "CALIBRATION"
        or not isinstance(evaluation, dict)
        or evaluation.get("exact_reviewed_row_count") != 6
        or evaluation.get("reviewed_rows_are_not_reader_routing_inputs") is not True
    ):
        raise LogicalRowLabelReviewEvaluationError("E-0036 evaluation control drifted")
    return config


def _load_sealed_outputs(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[
    dict[str, Any],
    list[dict[str, str]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    evaluation = config["evaluation_only_after_both_baseline_seals"]
    seal_path = _verify_config_record(
        project_root, evaluation.get("baseline_output_seal"), "E-0036 baseline output seal"
    )
    seal = _load_json(seal_path, "E-0036 baseline output seal")
    s3_snapshot = seal.get("s3_artifact_snapshot")
    if (
        seal.get("state") != _SEAL_STATE
        or seal.get("seal_git_dirty") is not False
        or seal.get("sample_count_per_reader") != 64
        or seal.get("same_ordered_sample_ids") is not True
        or seal.get("reference_or_human_review_loaded_by_sealer") is not False
        or seal.get("evaluation_allowed_only_after_this_seal") is not True
        or not isinstance(s3_snapshot, dict)
        or s3_snapshot.get("restore_verified") is not True
        or s3_snapshot.get("hydrate_probe", {}).get("status") != "PASS"
    ):
        raise LogicalRowLabelReviewEvaluationError("E-0036 baseline seal is incomplete")
    request_path = _verify_artifact(project_root, seal.get("request"), "E-0036 request")
    request = _load_json(request_path, "E-0036 request")
    try:
        request_samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise LogicalRowLabelReviewEvaluationError(str(error)) from error
    if request.get("git_commit") != seal.get("inference_git_commit"):
        raise LogicalRowLabelReviewEvaluationError("E-0036 inference commit identity drifted")
    readers: dict[str, dict[str, Any]] = {}
    sealed_readers = seal.get("readers")
    if not isinstance(sealed_readers, dict) or set(sealed_readers) != set(_READER_FIELDS):
        raise LogicalRowLabelReviewEvaluationError("E-0036 sealed reader registry drifted")
    for reader_key, (reader_name, label_field) in _READER_FIELDS.items():
        record = sealed_readers[reader_key]
        if not isinstance(record, dict):
            raise LogicalRowLabelReviewEvaluationError(f"sealed {reader_key} record is invalid")
        result_path = _verify_artifact(
            project_root, record.get("result"), f"sealed {reader_key} result"
        )
        _verify_artifact(project_root, record.get("manifest"), f"sealed {reader_key} manifest")
        result = _load_json(result_path, f"sealed {reader_key} result")
        raw_samples = result.get("samples")
        if (
            result.get("experiment_id") != "E-0036"
            or result.get("reader") != reader_name
            or result.get("state") != _INFERENCE_STATE
            or result.get("reference_text_available_to_reader") is not False
            or result.get("sample_count") != 64
            or not isinstance(raw_samples, list)
            or len(raw_samples) != 64
        ):
            raise LogicalRowLabelReviewEvaluationError(f"sealed {reader_key} result drifted")
        samples_by_id: dict[str, dict[str, Any]] = {}
        ordered_labels: list[str] = []
        for raw, request_sample in zip(raw_samples, request_samples, strict=True):
            if not isinstance(raw, dict):
                raise LogicalRowLabelReviewEvaluationError(f"sealed {reader_key} sample is invalid")
            sample_id = request_sample["sample_id"]
            if (
                raw.get("sample_id") != sample_id
                or raw.get("crop_path") != request_sample["crop_path"]
                or raw.get("crop_sha256") != request_sample["crop_sha256"]
                or not isinstance(raw.get(label_field), str)
                or sample_id in samples_by_id
            ):
                raise LogicalRowLabelReviewEvaluationError(
                    f"sealed {reader_key} sample identity drifted: {sample_id}"
                )
            samples_by_id[sample_id] = raw
            ordered_labels.append(str(raw[label_field]))
        readers[reader_key] = {
            "reader_name": reader_name,
            "label_field": label_field,
            "result_path": result_path,
            "samples_by_id": samples_by_id,
            "ordered_labels": ordered_labels,
            "runtime_metrics": record.get("metrics"),
        }
    return seal, request_samples, readers, request


def _map_before_review_load(
    project_root: Path,
    config: dict[str, Any],
    request_samples: list[dict[str, str]],
    readers: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    evaluation = config["evaluation_only_after_both_baseline_seals"]
    mapping_policy_path = _verify_config_record(
        project_root, evaluation.get("ordered_mapping_policy"), "ordered mapping policy"
    )
    scope_policy_path = _verify_config_record(
        project_root, evaluation.get("scope_policy"), "mapping scope policy"
    )
    hierarchy_path = _verify_config_record(
        project_root, evaluation.get("hierarchy_reference"), "schema hierarchy reference"
    )
    target_schema_path = _verify_config_record(
        project_root, evaluation.get("target_schema"), "target CDKT schema"
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(hierarchy_path, project_root, schema)
    apply_hierarchy_reference(schema, hierarchy)
    graph = build_schema_graph(schema, "CDKT")
    graph_control = evaluation.get("schema_graph")
    if (
        not isinstance(graph_control, dict)
        or graph_control.get("node_count") != len(graph.nodes)
        or graph_control.get("sha256") != graph.graph_sha256
        or target_schema_path.name != "Bank_CDKT_ReportNormId.xlsx"
    ):
        raise LogicalRowLabelReviewEvaluationError("CDKT SchemaGraph identity drifted")
    policy = load_ordered_subgraph_policy(mapping_policy_path)
    scope_policy = load_scope_policy(scope_policy_path)
    mappings: dict[str, Any] = {}
    for reader_key, reader in readers.items():
        rows = [
            PdfGraphRow(
                row_id=sample["sample_id"],
                label=reader["ordered_labels"][index],
                order=index,
                statement_type="CDKT",
                scope="CONSOLIDATED",
                table_id="mbb-cdkt-pages-3-4",
            )
            for index, sample in enumerate(request_samples)
        ]
        result = align_ordered_subgraph(
            rows,
            graph,
            context=MappingBlockContext(
                statement_type="CDKT",
                scope="CONSOLIDATED",
                table_id="mbb-cdkt-pages-3-4",
                schema_cluster_ids=tuple(node.schema_id for node in graph.nodes),
                block_is_exhaustive_for_schema_cluster=False,
            ),
            policy=policy,
            scope_policy=scope_policy,
        )
        mappings[reader_key] = result
    graph_record = {
        "statement_type": graph.statement_type,
        "node_count": len(graph.nodes),
        "graph_sha256": graph.graph_sha256,
        "workbook_display_order_used": True,
        "numeric_report_norm_id_sort_used": False,
    }
    return mappings, graph_record


def _numeric_rows(payload: dict[str, Any]) -> dict[tuple[int, int], dict[int, Decimal | None]]:
    after = payload.get("after")
    cells = after.get("cells") if isinstance(after, dict) else None
    if (
        payload.get("experiment_id") != "E-0034"
        or payload.get("status") != "PASS_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
        or not isinstance(cells, list)
        or len(cells) != 128
    ):
        raise LogicalRowLabelReviewEvaluationError("E-0034 numeric evidence drifted")
    rows: dict[tuple[int, int], dict[int, Decimal | None]] = {}
    for cell in cells:
        if not isinstance(cell, dict):
            raise LogicalRowLabelReviewEvaluationError("E-0034 numeric cell is invalid")
        key = (int(cell["page"]), int(cell["row_ordinal"]))
        axis = int(cell["axis_ordinal"])
        if axis in rows.setdefault(key, {}):
            raise LogicalRowLabelReviewEvaluationError("E-0034 numeric axis is duplicated")
        value = cell.get("normalized_numeric_value")
        rows[key][axis] = None if value is None else Decimal(str(value))
    if len(rows) != 64 or any(set(axes) != {0, 1} for axes in rows.values()):
        raise LogicalRowLabelReviewEvaluationError("E-0034 numeric row grid drifted")
    return rows


def _crop_rows(payload: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    samples = payload.get("samples")
    if (
        payload.get("experiment_id") != "E-0035"
        or payload.get("state") != "FROZEN_ALL_LOGICAL_ROW_LABEL_CROPS_NO_SEMANTIC_INFERENCE"
        or payload.get("sample_count") != 64
        or not isinstance(samples, list)
        or len(samples) != 64
    ):
        raise LogicalRowLabelReviewEvaluationError("E-0035 crop manifest drifted")
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    for sample in samples:
        if not isinstance(sample, dict):
            raise LogicalRowLabelReviewEvaluationError("E-0035 crop sample is invalid")
        key = (int(sample["page"]), int(sample["row_ordinal"]))
        if key in rows or not isinstance(sample.get("ppocr_text"), str):
            raise LogicalRowLabelReviewEvaluationError("E-0035 crop row identity drifted")
        rows[key] = sample
    return rows


def _select_review_document(registry, document_key: str) -> ReviewedDocument:
    matches = [document for document in registry.documents if document.document_key == document_key]
    if len(matches) != 1:
        raise LogicalRowLabelReviewEvaluationError(
            f"review document identity is absent or duplicated: {document_key}"
        )
    document = matches[0]
    decisions = [
        decision
        for decision in document.decisions
        if decision.template_membership is TemplateMembership.CURRENT_TARGET_TEMPLATE
        and decision.mapping_action == "MAP_ONCE"
        and decision.statement_type == "CDKT"
        and decision.page in {3, 4}
    ]
    if len(decisions) != 6 or any(decision.pdf_label is None for decision in decisions):
        raise LogicalRowLabelReviewEvaluationError("reviewed MBB row denominator drifted")
    return ReviewedDocument(
        document_key=document.document_key,
        bank=document.bank,
        scope=document.scope,
        source_path=document.source_path,
        source_sha256=document.source_sha256,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        period_maps=document.period_maps,
        decisions=tuple(decisions),
    )


def bind_reviewed_rows(
    decisions: tuple[ReviewedDecision, ...],
    numeric_rows: dict[tuple[int, int], dict[int, Decimal | None]],
    crop_rows: dict[tuple[int, int], dict[str, Any]],
    *,
    minimum_label_similarity: float,
    minimum_runner_up_margin: float,
) -> tuple[dict[str, ReviewedDecision], list[dict[str, Any]]]:
    """Bind reviewed rows to physical crops using numbers first and labels only as a tie-break."""

    bound: dict[str, ReviewedDecision] = {}
    evidence: list[dict[str, Any]] = []
    for decision in decisions:
        if decision.current is None or decision.comparative is None or decision.pdf_label is None:
            raise LogicalRowLabelReviewEvaluationError("reviewed visible row lacks evidence")
        expected = (
            decision.current.normalized_numeric_value,
            decision.comparative.normalized_numeric_value,
        )
        candidates: list[tuple[float, tuple[int, int], dict[str, Any], int]] = []
        for key, axes in numeric_rows.items():
            if key[0] != decision.page:
                continue
            observed_count = sum(axes[axis] is not None for axis in (0, 1))
            if observed_count == 0 or any(
                axes[axis] is not None and axes[axis] != expected[axis] for axis in (0, 1)
            ):
                continue
            crop = crop_rows.get(key)
            if crop is None:
                raise LogicalRowLabelReviewEvaluationError("numeric row lacks E-0035 crop")
            similarity = (
                ratio(retrieval_key(decision.pdf_label), retrieval_key(str(crop["ppocr_text"])))
                / 100.0
            )
            candidates.append((similarity, key, crop, observed_count))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        if not candidates:
            raise LogicalRowLabelReviewEvaluationError(
                f"reviewed row has no numeric-compatible crop: {decision.reviewed_item_id}"
            )
        best_similarity, key, crop, observed_count = candidates[0]
        runner_up_similarity = candidates[1][0] if len(candidates) > 1 else None
        margin = (
            best_similarity - runner_up_similarity if runner_up_similarity is not None else None
        )
        if best_similarity < minimum_label_similarity or (
            margin is not None and margin < minimum_runner_up_margin
        ):
            raise LogicalRowLabelReviewEvaluationError(
                f"reviewed row binding is ambiguous: {decision.reviewed_item_id}"
            )
        sample_id = str(crop["sample_id"])
        if sample_id in bound:
            raise LogicalRowLabelReviewEvaluationError("reviewed rows bind one crop more than once")
        bound[sample_id] = decision
        evidence.append(
            {
                "reviewed_item_id": decision.reviewed_item_id,
                "visible_row_id": decision.visible_row_id,
                "sample_id": sample_id,
                "page": key[0],
                "row_ordinal": key[1],
                "reviewed_numeric_pair": [str(value) for value in expected],
                "e0034_observed_numeric_pair": [
                    None if numeric_rows[key][axis] is None else str(numeric_rows[key][axis])
                    for axis in (0, 1)
                ],
                "numeric_observed_cell_count": observed_count,
                "numeric_compatible_candidate_count": len(candidates),
                "ppocr_tiebreak_similarity": round(best_similarity, 6),
                "ppocr_tiebreak_runner_up_similarity": (
                    None if runner_up_similarity is None else round(runner_up_similarity, 6)
                ),
                "ppocr_tiebreak_margin": None if margin is None else round(margin, 6),
            }
        )
    if len(bound) != len(decisions):
        raise LogicalRowLabelReviewEvaluationError("reviewed row binding denominator drifted")
    return bound, evidence


def _score_reviewed_labels(
    reader: dict[str, Any],
    bindings: dict[str, ReviewedDecision],
) -> dict[str, Any]:
    inputs = [
        {
            "sample_id": sample_id,
            "document": decision.document_key,
            "category": "LOGICAL_ROW_LABEL",
            "reference": str(decision.pdf_label),
            "prediction": str(reader["samples_by_id"][sample_id][reader["label_field"]]),
        }
        for sample_id, decision in sorted(
            bindings.items(), key=lambda item: (item[1].page, item[0])
        )
    ]
    return score_reader(inputs, title_categories=set())


def _score_reviewed_mapping(mapping, bindings: dict[str, ReviewedDecision]) -> dict[str, Any]:
    best_by_row = (
        {match.row_id: match.schema_id for match in mapping.best_path.matches}
        if mapping.best_path is not None
        else {}
    )
    automatic_by_row = best_by_row if mapping.automatic_selection_allowed else {}
    rows = []
    for sample_id, decision in sorted(bindings.items(), key=lambda item: (item[1].page, item[0])):
        best_id = best_by_row.get(sample_id)
        automatic_id = automatic_by_row.get(sample_id)
        rows.append(
            {
                "sample_id": sample_id,
                "reviewed_report_norm_id": decision.reviewed_item_id,
                "best_path_report_norm_id": best_id,
                "best_path_exact": best_id == decision.reviewed_item_id,
                "automatically_accepted_report_norm_id": automatic_id,
                "automatically_accepted_exact": automatic_id == decision.reviewed_item_id,
            }
        )
    return {
        "status": mapping.status.value,
        "automatic_selection_allowed": mapping.automatic_selection_allowed,
        "reason": mapping.reason,
        "score_margin": mapping.score_margin,
        "best_path": None if mapping.best_path is None else asdict(mapping.best_path),
        "runner_up_path": (
            None if mapping.runner_up_path is None else asdict(mapping.runner_up_path)
        ),
        "reviewed_best_path_exact_count": sum(row["best_path_exact"] for row in rows),
        "reviewed_automatically_accepted_exact_count": sum(
            row["automatically_accepted_exact"] for row in rows
        ),
        "reviewed_mapping_abstention_count": sum(
            row["automatically_accepted_report_norm_id"] is None for row in rows
        ),
        "reviewed_rows": rows,
        "search": asdict(mapping.search),
    }


def _cross_reader_agreement(readers: dict[str, dict[str, Any]]) -> dict[str, int]:
    left = readers["vietocr"]["ordered_labels"]
    right = readers["deepseek_ocr2"]["ordered_labels"]
    pairs = list(zip(left, right, strict=True))
    return {
        "sample_count": len(pairs),
        "normalized_exact_count": sum(
            normalize_evaluation_line(a) == normalize_evaluation_line(b) for a, b in pairs
        ),
        "normalized_casefold_exact_count": sum(
            normalize_evaluation_line(a).casefold() == normalize_evaluation_line(b).casefold()
            for a, b in pairs
        ),
        "retrieval_key_exact_count": sum(retrieval_key(a) == retrieval_key(b) for a, b in pairs),
        "both_nonempty_count": sum(bool(a.strip()) and bool(b.strip()) for a, b in pairs),
    }


def determine_qwen_trigger(reader_evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_inexact = {
        key: 6 - int(value["labels"]["aggregate"]["exact_line_count"])
        for key, value in reader_evaluations.items()
    }
    wrong_best_path = {
        key: 6 - int(value["mapping"]["reviewed_best_path_exact_count"])
        for key, value in reader_evaluations.items()
    }
    triggered = any(source_inexact.values()) or any(wrong_best_path.values())
    return {
        "triggered": triggered,
        "predeclared_rule": (
            "AT_LEAST_ONE_REVIEWED_ROW_SOURCE_INEXACT_OR_WRONG_REPORT_NORM_ID_"
            "AFTER_BOTH_BASELINE_SEALS"
        ),
        "reviewed_source_inexact_count_by_reader": source_inexact,
        "reviewed_wrong_best_path_report_norm_id_count_by_reader": wrong_best_path,
        "decision": "RUN_QWEN_SAME_REQUEST" if triggered else "DO_NOT_RUN_QWEN",
    }


def capture_logical_row_label_review_evaluation(
    project_root: Path,
    *,
    config_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    config_file = _resolve(project_root, config_path)
    destination = _resolve(project_root, output_path)
    if destination.exists():
        raise LogicalRowLabelReviewEvaluationError(
            f"refusing to overwrite E-0036 evaluation: {destination}"
        )
    if _git(project_root, "status", "--porcelain"):
        raise LogicalRowLabelReviewEvaluationError(
            "formal E-0036 reviewed evaluation requires clean Git"
        )
    config = _load_control(project_root, config_file)
    seal, request_samples, readers, request = _load_sealed_outputs(project_root, config)

    # This call deliberately precedes loading the human-review registry.
    mappings, graph_record = _map_before_review_load(project_root, config, request_samples, readers)

    evaluation = config["evaluation_only_after_both_baseline_seals"]
    review_policy_path = _verify_config_record(
        project_root, evaluation.get("human_review_policy"), "human-review policy"
    )
    review_registry = load_human_review_registry(review_policy_path, project_root)
    document = _select_review_document(review_registry, str(evaluation["document_key"]))
    if document.scope != "CONSOLIDATED":
        raise LogicalRowLabelReviewEvaluationError("reviewed MBB scope drifted")

    crop_manifest_path = _verify_config_record(
        project_root, config["frozen_input"].get("crop_manifest"), "E-0035 crop manifest"
    )
    numeric_path = _verify_config_record(
        project_root, evaluation.get("numeric_row_linkage"), "E-0034 numeric row linkage"
    )
    crop_manifest = _load_json(crop_manifest_path, "E-0035 crop manifest")
    numeric = _load_json(numeric_path, "E-0034 numeric verification")
    binding_policy = evaluation.get("reviewed_row_binding")
    if not isinstance(binding_policy, dict):
        raise LogicalRowLabelReviewEvaluationError("reviewed row binding policy is absent")
    bindings, binding_evidence = bind_reviewed_rows(
        document.decisions,
        _numeric_rows(numeric),
        _crop_rows(crop_manifest),
        minimum_label_similarity=float(binding_policy["minimum_ppocr_label_similarity"]),
        minimum_runner_up_margin=float(binding_policy["minimum_ppocr_runner_up_margin"]),
    )

    reader_evaluations: dict[str, dict[str, Any]] = {}
    for reader_key, reader in readers.items():
        reader_evaluations[reader_key] = {
            "reader": reader["reader_name"],
            "labels": _score_reviewed_labels(reader, bindings),
            "mapping": _score_reviewed_mapping(mappings[reader_key], bindings),
            "runtime_metrics": reader["runtime_metrics"],
        }
    trigger = determine_qwen_trigger(reader_evaluations)
    qwen_control = config.get("conditional_qwen_challenger")
    if not isinstance(qwen_control, dict) or qwen_control.get(
        "required_same_request_sha256"
    ) not in {
        "TO_BE_FILLED_AFTER_CLEAN_REQUEST_CAPTURE",
        sha256_file(_resolve(project_root, seal["request"]["path"])),
    }:
        raise LogicalRowLabelReviewEvaluationError("conditional Qwen control drifted")

    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": (
            "BASELINES_REVIEWED_QWEN_TRIGGERED"
            if trigger["triggered"]
            else "BASELINES_REVIEWED_QWEN_NOT_REQUIRED"
        ),
        "dataset_role": "CALIBRATION",
        "evaluation_git_commit": _git(project_root, "rev-parse", "HEAD"),
        "evaluation_git_dirty": False,
        "mapping_completed_before_human_review_registry_load": True,
        "baseline_output_seal": _artifact(
            project_root,
            _resolve(project_root, evaluation["baseline_output_seal"]["path"]),
        ),
        "request": dict(seal["request"]),
        "crop_manifest": _artifact(project_root, crop_manifest_path),
        "numeric_row_linkage": _artifact(project_root, numeric_path),
        "human_review": {
            "review_id": review_registry.review_id,
            "policy": _artifact(project_root, review_policy_path),
            "dataset": {
                "path": review_registry.dataset_path.relative_to(project_root).as_posix(),
                "size_bytes": review_registry.dataset_path.stat().st_size,
                "sha256": review_registry.dataset_sha256,
            },
            "document_key": document.document_key,
            "source_sha256": document.source_sha256,
            "reviewed_row_count": len(bindings),
            "row_bindings": binding_evidence,
        },
        "schema_graph": graph_record,
        "reader_evaluations": reader_evaluations,
        "all_row_pairwise_agreement": _cross_reader_agreement(readers),
        "conditional_qwen": trigger
        | {
            "model_repo_id": qwen_control["model_repo_id"],
            "model_revision": qwen_control["model_revision"],
            "required_same_request_sha256": sha256_file(
                _resolve(project_root, seal["request"]["path"])
            ),
        },
        "authority": {
            "geometry": False,
            "numeric_value_sign_blank_dash_or_status": False,
            "period_unit_scope_or_statement_type": False,
            "report_norm_id_truth_from_reader": False,
            "mapping_best_path_may_bypass_abstention": False,
            "automatic_model_promotion": False,
            "holdout_or_production_accuracy": False,
        },
        "claim_boundary": (
            "This evaluation scores two previously sealed reference-blind readers on six "
            "pre-existing MBB calibration rows and the fixed ordered CDKT SchemaGraph. "
            "Reviewed values bind physical rows only after mapping is complete. Best-path "
            "correctness does not override mapping abstention. The result makes no holdout "
            "or production-accuracy claim and grants no numeric or schema authority."
        ),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(destination, payload)
    return payload


__all__ = [
    "LogicalRowLabelReviewEvaluationError",
    "bind_reviewed_rows",
    "capture_logical_row_label_review_evaluation",
    "determine_qwen_trigger",
]
