from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.mapping.alignment_v2 import MappingDecisionStatus
from bctc_ai.mapping.ordered_subgraph import (
    MappingBlockContext,
    PdfGraphRow,
    SchemaGraphNode,
    align_ordered_subgraph,
    build_schema_graph,
    load_ordered_subgraph_policy,
)
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all


class OrderedSubgraphEvaluationError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise OrderedSubgraphEvaluationError(f"cannot read E-0023 config: {path}") from exc
    required = {
        "version": 1,
        "experiment_id": "E-0023",
        "dataset_role": "LOGIC_DEVELOPMENT",
        "fixture_id": "ordered-subgraph-six-to-three-v1",
        "baseline": "INDEPENDENT_LABEL_TOP1_NO_GLOBAL_CONSTRAINT",
        "baseline_uses_same_candidate_similarity_gate": True,
        "pdf_or_ocr_evidence_used": False,
        "holdout_evidence_used": False,
        "historical_evidence_used": False,
        "numeric_value_features_used": False,
        "numeric_report_norm_id_sort_used": False,
    }
    drift = {
        key: {"expected": value, "actual": payload.get(key)}
        for key, value in required.items()
        if payload.get(key) != value
    }
    if drift:
        raise OrderedSubgraphEvaluationError(f"E-0023 identity/safety drifted: {drift}")
    safety = payload.get("required_safety")
    if not isinstance(safety, dict) or safety != {
        "ambiguity_fixture_abstains": True,
        "verified_parent_overrides_wrong_semantic_score": True,
        "off_balance_exact_label_excluded": True,
        "workbook_display_order_used": True,
        "automatic_production_confidence_promotion": False,
    }:
        raise OrderedSubgraphEvaluationError("E-0023 required safety contract drifted")
    return payload


def _schema(
    specifications: list[tuple[int, str, int | None, int | None]],
) -> list[SchemaItem]:
    items = [
        SchemaItem(
            schema_id=schema_id,
            canonical_name=label,
            normalized_name=retrieval_key(label),
            statement_type="CDKT",
            display_order=order,
            parent_id=parent_id,
            hierarchy_level=level,
        )
        for order, (schema_id, label, parent_id, level) in enumerate(specifications)
    ]
    by_id = {item.schema_id: item for item in items}
    for index, item in enumerate(items):
        item.previous_id = items[index - 1].schema_id if index else None
        item.next_id = items[index + 1].schema_id if index + 1 < len(items) else None
        if item.parent_id is not None:
            by_id[item.parent_id].children.append(item.schema_id)
    return items


def _main_fixture():
    schema = _schema(
        [
            (900, "Tài sản cố định", None, 0),
            (50, "Nguyên giá tài sản cố định", 900, 1),
            (700, "Hao mòn tài sản cố định", 900, 1),
            (10, "Giá trị còn lại", 900, 1),
            (800, "Tổng tài sản", None, 0),
        ]
    )
    rows = (
        PdfGraphRow("p0", "Tài sản cố định", 0, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "p1",
            "Nguyên giá tài sản cố định",
            1,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="p0",
            indentation_level=1,
        ),
        PdfGraphRow("p2", "Chi phí xây dựng dở dang", 2, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "p3",
            "Hao mòn tài sản cố định",
            3,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="p0",
            indentation_level=1,
        ),
        PdfGraphRow("p4", "Thuyết minh bổ sung", 4, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "p5",
            "Giá trị còn lại",
            5,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="p0",
            indentation_level=1,
        ),
    )
    return schema, rows


def _label_similarity(row: PdfGraphRow, node: SchemaGraphNode) -> float:
    return max(
        ratio(retrieval_key(row.label), retrieval_key(alias)) / 100.0 for alias in node.aliases
    )


def _metrics(
    predictions: list[tuple[str, int]],
    expected: set[tuple[str, int]],
    extras: set[str],
) -> dict[str, int | float]:
    predicted = set(predictions)
    correct = len(predicted & expected)
    false_positive = len(predictions) - correct
    counts = Counter(schema_id for _row_id, schema_id in predictions)
    duplicate_assignments = sum(max(0, count - 1) for count in counts.values())
    predicted_rows = {row_id for row_id, _schema_id in predictions}
    return {
        "predicted_pairs": len(predictions),
        "correct_pairs": correct,
        "false_positive_pairs": false_positive,
        "duplicate_schema_assignments": duplicate_assignments,
        "retained_extra_pdf_rows": len(extras - predicted_rows),
        "precision": round(correct / len(predictions), 6) if predictions else 0.0,
        "recall": round(correct / len(expected), 6) if expected else 0.0,
    }


def _independent_label_top1(
    rows: tuple[PdfGraphRow, ...],
    nodes: tuple[SchemaGraphNode, ...],
    minimum_similarity: float,
) -> list[tuple[str, int]]:
    predictions = []
    for row in rows:
        ranked = sorted(
            ((_label_similarity(row, node), node.display_order, node.schema_id) for node in nodes),
            key=lambda item: (-item[0], item[1]),
        )
        similarity, _display_order, schema_id = ranked[0]
        if similarity >= minimum_similarity:
            predictions.append((row.row_id, schema_id))
    return predictions


def _safety_fixtures(policy, scope_policy) -> dict[str, Any]:
    duplicate_graph = build_schema_graph(
        _schema([(900, "Khác", None, 0), (10, "Khác", None, 0)]), "CDKT"
    )
    ambiguity = align_ordered_subgraph(
        [PdfGraphRow("r", "Khác", 0, "CDKT", "CONSOLIDATED", table_id="t")],
        duplicate_graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (900, 10)),
        policy=policy,
        scope_policy=scope_policy,
    )

    parent_graph = build_schema_graph(
        _schema(
            [
                (100, "Hữu hình", None, 0),
                (901, "Nguyên giá", 100, 1),
                (50, "Vô hình", None, 0),
                (801, "Nguyên giá", 50, 1),
            ]
        ),
        "CDKT",
    )
    parent = align_ordered_subgraph(
        [
            PdfGraphRow(
                "r",
                "Nguyên giá",
                0,
                "CDKT",
                "CONSOLIDATED",
                table_id="t",
                parent_schema_id=50,
                indentation_level=1,
            )
        ],
        parent_graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (901, 801)),
        policy=policy,
        scope_policy=scope_policy,
        accounting_semantic_scores={("r", 901): 1.0, ("r", 801): 0.0},
    )

    off_balance_graph = build_schema_graph(_schema([(5701, "Bảo lãnh vay vốn", None, 0)]), "CDKT")
    off_balance_heading = "CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH"
    off_balance = align_ordered_subgraph(
        [
            PdfGraphRow(
                "r",
                "Bảo lãnh vay vốn",
                0,
                "CDKT",
                "CONSOLIDATED",
                section_heading=off_balance_heading,
                table_id="t",
            )
        ],
        off_balance_graph,
        context=MappingBlockContext(
            "CDKT",
            "CONSOLIDATED",
            "t",
            (5701,),
            section_heading=off_balance_heading,
        ),
        policy=policy,
        scope_policy=scope_policy,
    )
    return {
        "ambiguity_fixture": {
            "status": ambiguity.status.value,
            "automatic_selection_allowed": ambiguity.automatic_selection_allowed,
            "score_margin": ambiguity.score_margin,
            "top_schema_ids": [path.matches[0].schema_id for path in ambiguity.ranked_paths[:2]],
        },
        "verified_parent_fixture": {
            "status": parent.status.value,
            "selected_schema_id": parent.best_path.matches[0].schema_id,
            "wrong_semantic_schema_id": 901,
            "wrong_semantic_candidate_appears_in_any_path": any(
                match.schema_id == 901 for path in parent.ranked_paths for match in path.matches
            ),
        },
        "off_balance_fixture": {
            "status": off_balance.status.value,
            "matched_pairs": len(off_balance.best_path.matches),
            "row_status": off_balance.row_dispositions[0].status,
        },
    }


def evaluate_ordered_subgraph_logic(project_root: Path, config_path: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    config_path = config_path.resolve()
    config = _load_config(config_path)
    policy_path = project_root / str(config["mapping_policy"])
    scope_path = project_root / str(config["scope_policy"])
    policy = load_ordered_subgraph_policy(policy_path)
    scope_policy = load_scope_policy(scope_path)
    schema, rows = _main_fixture()
    graph = build_schema_graph(schema, "CDKT")
    by_id = graph.by_id()
    cluster_nodes = tuple(by_id[schema_id] for schema_id in (50, 700, 10))
    expected = {(str(row_id), int(schema_id)) for row_id, schema_id in config["expected_pairs"]}
    extras = {str(row_id) for row_id in config["expected_extra_pdf_rows"]}

    baseline_predictions = _independent_label_top1(
        rows, cluster_nodes, policy.minimum_candidate_similarity
    )
    ordered = align_ordered_subgraph(
        rows,
        graph,
        context=MappingBlockContext(
            "CDKT",
            "CONSOLIDATED",
            "t",
            (50, 700, 10),
            block_is_exhaustive_for_schema_cluster=True,
            minimum_schema_coverage=1.0,
        ),
        policy=policy,
        scope_policy=scope_policy,
    )
    ordered_predictions = [(match.row_id, match.schema_id) for match in ordered.best_path.matches]
    metrics = {
        "baseline": _metrics(baseline_predictions, expected, extras),
        "ordered_subgraph": _metrics(ordered_predictions, expected, extras),
    }
    if metrics != config.get("expected_metrics"):
        raise OrderedSubgraphEvaluationError(
            f"E-0023 expected metrics drifted: expected={config.get('expected_metrics')}, "
            f"observed={metrics}"
        )
    safety = _safety_fixtures(policy, scope_policy)
    if not (
        safety["ambiguity_fixture"]["status"] == MappingDecisionStatus.AMBIGUOUS_MAPPING.value
        and safety["ambiguity_fixture"]["automatic_selection_allowed"] is False
        and safety["ambiguity_fixture"]["score_margin"] == 0
        and safety["verified_parent_fixture"]["selected_schema_id"] == 801
        and safety["verified_parent_fixture"]["wrong_semantic_candidate_appears_in_any_path"]
        is False
        and safety["off_balance_fixture"]["status"]
        == MappingDecisionStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE.value
        and safety["off_balance_fixture"]["matched_pairs"] == 0
    ):
        raise OrderedSubgraphEvaluationError(f"E-0023 safety fixture failed: {safety}")

    _workbooks, real_schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml", project_root, real_schema
    )
    apply_hierarchy_reference(real_schema, hierarchy)
    real_graph = build_schema_graph(real_schema, "CDKT")
    real_by_id = real_graph.by_id()
    real_checks = {
        "cdkt_node_count": len(real_graph.nodes),
        "non_numeric_workbook_sequence": [node.schema_id for node in real_graph.nodes[64:67]],
        "fixed_asset_parent_ids": {
            "4367": real_by_id[4367].parent_id,
            "4369": real_by_id[4369].parent_id,
            "4371": real_by_id[4371].parent_id,
        },
        "graph_sha256": real_graph.graph_sha256,
    }
    if real_checks["non_numeric_workbook_sequence"] != [4337, 4373, 4338]:
        raise OrderedSubgraphEvaluationError("real graph was reordered numerically")

    tm_1944 = [item for item in real_schema if item.schema_id == 1944]
    if len(tm_1944) != 1 or tm_1944[0].canonical_name != (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    ):
        raise OrderedSubgraphEvaluationError("TM 1944 is missing from the shared schema registry")
    return {
        "format_version": 1,
        "experiment_id": "E-0023",
        "dataset_role": "LOGIC_DEVELOPMENT",
        "status": "PASS_LOGIC_DEVELOPMENT_NO_PRODUCTION_CONFIDENCE_PROMOTION",
        "fixture_id": config["fixture_id"],
        "claim_boundary": config["claim_boundary"],
        "baseline": {
            "name": config["baseline"],
            "minimum_candidate_similarity": policy.minimum_candidate_similarity,
            "predictions": [list(item) for item in baseline_predictions],
        },
        "ordered_subgraph": {
            "status": ordered.status.value,
            "automatic_selection_allowed_for_fixture": ordered.automatic_selection_allowed,
            "best_path": asdict(ordered.best_path),
            "runner_up_path": asdict(ordered.runner_up_path),
            "score_margin": ordered.score_margin,
            "row_dispositions": [asdict(item) for item in ordered.row_dispositions],
            "schema_dispositions": [asdict(item) for item in ordered.schema_dispositions],
            "search": asdict(ordered.search),
        },
        "metrics": metrics,
        "delta": {
            "precision": round(
                metrics["ordered_subgraph"]["precision"] - metrics["baseline"]["precision"],
                6,
            ),
            "false_positive_pairs": (
                metrics["ordered_subgraph"]["false_positive_pairs"]
                - metrics["baseline"]["false_positive_pairs"]
            ),
            "duplicate_schema_assignments": (
                metrics["ordered_subgraph"]["duplicate_schema_assignments"]
                - metrics["baseline"]["duplicate_schema_assignments"]
            ),
            "retained_extra_pdf_rows": (
                metrics["ordered_subgraph"]["retained_extra_pdf_rows"]
                - metrics["baseline"]["retained_extra_pdf_rows"]
            ),
        },
        "safety_fixtures": safety,
        "real_schema_graph": real_checks,
        "schema_registry": {
            "item_count": len(real_schema),
            "tm_1944_present": True,
            "numeric_report_norm_id_sort_used": False,
        },
        "authority": {
            "pdf_or_ocr_evidence_used": False,
            "holdout_evidence_used": False,
            "historical_evidence_used": False,
            "numeric_value_features_used": False,
            "production_confidence_promoted": False,
            "e0022_pipeline_changed": False,
        },
    }


def capture_ordered_subgraph_evaluation(
    project_root: Path, *, config_path: Path, output_path: Path
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise OrderedSubgraphEvaluationError("formal E-0023 capture requires a clean Git worktree")
    output = output_path if output_path.is_absolute() else project_root / output_path
    output = output.resolve()
    try:
        output.relative_to(project_root)
    except ValueError as exc:
        raise OrderedSubgraphEvaluationError(
            "E-0023 output must remain inside the project"
        ) from exc
    if output.exists():
        raise OrderedSubgraphEvaluationError(f"refusing to overwrite E-0023 artifact: {output}")
    config = config_path if config_path.is_absolute() else project_root / config_path
    payload = evaluate_ordered_subgraph_logic(project_root, config.resolve())
    algorithm_paths = (
        "src/bctc_ai/mapping/ordered_subgraph.py",
        "src/bctc_ai/evaluation/ordered_subgraph_evaluation.py",
        "src/bctc_ai/schema/registry.py",
        "src/bctc_ai/schema/hierarchy.py",
        "src/bctc_ai/mapping/scope.py",
        "src/bctc_ai/core/text.py",
    )
    payload["code"] = {"git_commit": _git(project_root, "rev-parse", "HEAD"), "git_dirty": False}
    payload["config"] = {
        "experiment": {
            "path": config.resolve().relative_to(project_root).as_posix(),
            "sha256": sha256_file(config),
        },
        "mapping_policy": {
            "path": "config/mapping/ordered-subgraph-v1.yaml",
            "sha256": sha256_file(project_root / "config/mapping/ordered-subgraph-v1.yaml"),
        },
        "scope_policy": {
            "path": "config/mapping/scope_exclusions.yaml",
            "sha256": sha256_file(project_root / "config/mapping/scope_exclusions.yaml"),
        },
    }
    payload["algorithm_files_sha256"] = {
        relative: sha256_file(project_root / relative) for relative in algorithm_paths
    }
    payload["source_documents_read"] = []
    atomic_write_json(output, payload)
    return payload
