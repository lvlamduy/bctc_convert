from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import parse_unit
from bctc_ai.evaluation.cross_reader_metrics import (
    aggregate_cross_reader_metrics,
    classify_cross_reader_error_classes,
)
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    load_frozen_suite,
    validate_evidence_manifest,
)
from bctc_ai.evaluation.native_reference import validate_native_reference_contracts
from bctc_ai.evaluation.reader_outputs import compare_reader_rows, reader_row_from_dict
from bctc_ai.evaluation.reader_outputs_v2 import (
    ParsedVLMPageV2,
    ParsedVLMTableV2,
    load_vlm_table_parser_config,
    parse_paddle_vl_page_v2,
    table_roles_to_dict,
)
from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.tables.continuation import TableFragment, build_continuation_graph


class PairedNativeEvaluationError(RuntimeError):
    pass


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _resolve(project_root: Path, path: Path | str) -> Path:
    candidate = Path(path)
    return candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise PairedNativeEvaluationError(
            f"sealed evaluation evidence must be inside project root: {path}"
        ) from exc


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PairedNativeEvaluationError(f"cannot load JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise PairedNativeEvaluationError(f"expected a JSON object: {path}")
    return payload


def _verify_role_a(project_root: Path, seal_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    seal = _load_json(seal_path)
    if seal.get("state") != "REFERENCE_COMPLETE":
        raise PairedNativeEvaluationError("Role A seal is incomplete")
    result_path = _resolve(project_root, str(seal.get("result_path", "")))
    if not result_path.is_file() or sha256_file(result_path) != seal.get("result_sha256"):
        raise PairedNativeEvaluationError("Role A result is absent or hash-drifted")
    return seal, _load_json(result_path)


def _verify_role_b(project_root: Path, seal_path: Path) -> dict[str, Any]:
    seal = _load_json(seal_path)
    if seal.get("state") != "OCR_COMPLETE":
        raise PairedNativeEvaluationError("Role B seal is incomplete")
    pages = seal.get("pages")
    if not isinstance(pages, list) or not pages:
        raise PairedNativeEvaluationError("Role B seal contains no pages")
    implementation = seal.get("seal_implementation")
    if not isinstance(implementation, dict):
        raise PairedNativeEvaluationError("Role B seal has no implementation identity")
    implementation_path = _resolve(project_root, str(implementation.get("path", "")))
    if sha256_file(implementation_path) != implementation.get("sha256"):
        raise PairedNativeEvaluationError("Role B seal implementation hash drift")
    for page in pages:
        for output in page.get("outputs", []):
            path = _resolve(project_root, str(output.get("path", "")))
            if not path.is_file() or sha256_file(path) != output.get("sha256"):
                raise PairedNativeEvaluationError(f"Role B output drift: {path}")
        for key in ("metrics", "render"):
            record = page.get(key)
            if not isinstance(record, dict):
                raise PairedNativeEvaluationError(f"Role B page has no {key} evidence")
            path = _resolve(project_root, str(record.get("path", "")))
            if not path.is_file() or sha256_file(path) != record.get("sha256"):
                raise PairedNativeEvaluationError(f"Role B {key} drift: {path}")
    return seal


def _result_path_for_page(project_root: Path, page_record: dict[str, Any]) -> Path:
    page = int(page_record["page"])
    suffix = f"page-{page:04d}_res.json"
    matches = [
        _resolve(project_root, output["path"])
        for output in page_record["outputs"]
        if str(output["path"]).endswith(suffix)
    ]
    if len(matches) != 1:
        raise PairedNativeEvaluationError(
            f"expected exactly one Role B result JSON for page {page}"
        )
    return matches[0]


def _primary_table(page: ParsedVLMPageV2) -> ParsedVLMTableV2:
    candidates = [table for table in page.tables if table.roles is not None and table.rows]
    if not candidates:
        raise PairedNativeEvaluationError("Role B page has no parsed financial table")
    return max(candidates, key=lambda table: (len(table.rows), len(table.raw_grid)))


def _table_fragment(page_number: int, page: ParsedVLMPageV2) -> TableFragment:
    table = _primary_table(page)
    assert table.roles is not None
    width = table.roles.width
    centers = tuple(index / max(1, width - 1) for index in table.roles.value_columns)
    header = table.header
    periods = tuple(
        header[index] for index in table.roles.value_columns if index < len(header)
    )
    parsed_unit = parse_unit(" ".join((*header, page.context_text)))
    unit = (
        f"{parsed_unit.canonical}:{parsed_unit.multiplier}"
        if parsed_unit.canonical and parsed_unit.multiplier
        else None
    )
    return TableFragment(
        table_id=f"role-b-page-{page_number:04d}-table-{table.table_index}",
        page=page_number,
        header_labels=header,
        column_centers=centers,
        unit=unit,
        period_labels=periods,
        notes_section=None,
        parent_section="LCTT_MAIN_STATEMENT",
        starts_with_repeated_header=bool(header),
    )


def _serialize_tables(page: ParsedVLMPageV2) -> list[dict[str, Any]]:
    return [
        {
            "table_index": table.table_index,
            "bbox": list(table.bbox),
            "status": table.status,
            "roles": table_roles_to_dict(table.roles),
            "header": list(table.header),
            "row_count": len(table.rows),
            "span_expansion_count": table.span_expansion_count,
            "warnings": list(table.warnings),
        }
        for table in page.tables
    ]


def compare_paired_native_readers(
    project_root: Path,
    *,
    suite_config: Path,
    role_a_seal: Path,
    role_b_seal: Path,
    output: Path,
    parser_config: Path = Path("config/tables/vlm-table-parser-v2.yaml"),
) -> dict[str, Any]:
    """Compare sealed image-only Role B output with a sealed native Role A reference."""

    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise PairedNativeEvaluationError("comparison must start from a clean Git worktree")
    suite_path = _resolve(project_root, suite_config)
    role_a_seal_path = _resolve(project_root, role_a_seal)
    role_b_seal_path = _resolve(project_root, role_b_seal)
    output_path = _resolve(project_root, output)
    parser_path = _resolve(project_root, parser_config)
    suite = load_frozen_suite(project_root, suite_path)
    contracts = validate_native_reference_contracts(suite)
    role_a_seal_payload, role_a = _verify_role_a(project_root, role_a_seal_path)
    role_b = _verify_role_b(project_root, role_b_seal_path)
    reference = suite.source(str(suite.pairing["reference_fixture_id"]))
    candidate = suite.source(str(suite.pairing["candidate_fixture_id"]))
    if role_a.get("experiment_id") != suite.experiment_id:
        raise PairedNativeEvaluationError("Role A experiment identity differs from suite")
    if role_a.get("source_sha256") != reference.sha256:
        raise PairedNativeEvaluationError("Role A source differs from frozen reference")
    if role_b.get("source_sha256") != candidate.sha256:
        raise PairedNativeEvaluationError("Role B source differs from frozen candidate")
    if role_a.get("suite_config", {}).get("sha256") != sha256_file(suite_path):
        raise PairedNativeEvaluationError("Role A suite-config hash drift")

    evidence = (
        EvidenceItem(
            EvidenceKind.ROLE_A_RESULT,
            str(role_a_seal_payload["result_path"]),
            str(role_a_seal_payload["result_sha256"]),
        ),
        EvidenceItem(
            EvidenceKind.ROLE_B_RESULT,
            _relative(project_root, role_b_seal_path),
            sha256_file(role_b_seal_path),
        ),
        EvidenceItem(EvidenceKind.CONFIG, _relative(project_root, suite_path), sha256_file(suite_path)),
        EvidenceItem(
            EvidenceKind.CONFIG,
            _relative(project_root, parser_path),
            sha256_file(parser_path),
        ),
    )
    validate_evidence_manifest(EvidenceStage.COMPARE, evidence)
    parser = load_vlm_table_parser_config(parser_path)
    scope_path = project_root / "config/mapping/scope_exclusions.yaml"
    scope_policy = load_scope_policy(scope_path)
    cash_flow_path = project_root / "config/mapping/lctt.yaml"
    cash_flow_rules = load_cash_flow_rules(cash_flow_path)
    role_a_pages = {int(page["reference_page"]): page for page in role_a["pages"]}
    role_b_pages = {int(page["page"]): page for page in role_b["pages"]}

    page_results = []
    lctt_labels: list[str] = []
    lctt_fragments: list[TableFragment] = []
    for contract in contracts:
        reference_page = int(contract["reference_page"])
        candidate_page = int(contract["candidate_page"])
        if reference_page not in role_a_pages or candidate_page not in role_b_pages:
            raise PairedNativeEvaluationError(
                f"sealed inputs do not cover page contract {reference_page}->{candidate_page}"
            )
        reference_record = role_a_pages[reference_page]
        candidate_record = role_b_pages[candidate_page]
        reference_rows = tuple(
            reader_row_from_dict(record) for record in reference_record["rows"]
        )
        parsed_page = parse_paddle_vl_page_v2(
            _result_path_for_page(project_root, candidate_record),
            parser,
            page_tag=f"role-b-page-{candidate_page:04d}",
        )
        candidate_rows = parsed_page.reader_rows
        comparison = compare_reader_rows(
            reference_rows,
            candidate_rows,
            statement_type=str(contract["statement_type"]),
            scope_policy=scope_policy,
            candidate_context_text=parsed_page.context_text,
        )
        if contract["expected_scope"] == "OFF_BALANCE_SHEET" and comparison["counts"][
            "scope_allowed_candidate_rows"
        ]:
            raise PairedNativeEvaluationError(
                "off-balance rows remained eligible for target CDKT mapping"
            )
        if contract["statement_type"] == "LCTT":
            lctt_labels.extend(row.label for row in candidate_rows)
            lctt_fragments.append(_table_fragment(candidate_page, parsed_page))
        page_results.append(
            {
                "reference_page": reference_page,
                "candidate_page": candidate_page,
                "statement_type": contract["statement_type"],
                "expected_scope": contract["expected_scope"],
                "reference_headers": reference_record["headers"],
                "candidate_tables": _serialize_tables(parsed_page),
                "candidate_unresolved_table_count": parsed_page.unresolved_table_count,
                "comparison": comparison,
            }
        )

    continuation_graph = build_continuation_graph(lctt_fragments)
    continuation = [
        {
            "previous_table_id": edge.previous_table_id,
            "next_table_id": edge.next_table_id,
            "accepted": edge.accepted,
            "reason": edge.reason,
            "evidence": asdict(edge.evidence),
        }
        for edge in continuation_graph.edges
    ]
    required_continuations = sum("continued_to_reference_page" in item for item in contracts)
    accepted_continuations = sum(item["accepted"] for item in continuation)
    if accepted_continuations < required_continuations:
        raise PairedNativeEvaluationError(
            "configured statement continuation did not pass the evidence gate"
        )
    comparisons = tuple(page["comparison"] for page in page_results)
    metrics = aggregate_cross_reader_metrics(comparisons)
    error_analysis = classify_cross_reader_error_classes(metrics, comparisons)
    cash_flow = classify_cash_flow_method(lctt_labels, cash_flow_rules)
    off_balance_eligible = sum(
        int(page["comparison"]["counts"]["scope_allowed_candidate_rows"])
        for page in page_results
        if page["expected_scope"] == "OFF_BALANCE_SHEET"
    )
    implementation_paths = (
        Path("src/bctc_ai/evaluation/reader_outputs_v2.py"),
        Path("src/bctc_ai/evaluation/cross_reader_metrics.py"),
        Path("src/bctc_ai/evaluation/paired_native_evaluation.py"),
        Path("src/bctc_ai/validation/reader_agreement.py"),
        Path("src/bctc_ai/mapping/scope.py"),
        Path("src/bctc_ai/tables/continuation.py"),
    )
    payload = {
        "format_version": 3,
        "experiment_id": suite.experiment_id,
        "status": "PASS_CALIBRATION_WITH_REQUIRED_ESCALATIONS",
        "dataset_role": suite.dataset_role.value,
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
        "suite_config": {
            "path": _relative(project_root, suite_path),
            "sha256": sha256_file(suite_path),
        },
        "sealed_inputs": {
            "role_a_seal": {
                "path": _relative(project_root, role_a_seal_path),
                "sha256": sha256_file(role_a_seal_path),
                "result_sha256": role_a_seal_payload["result_sha256"],
            },
            "role_b_seal": {
                "path": _relative(project_root, role_b_seal_path),
                "sha256": sha256_file(role_b_seal_path),
                "artifact_set_sha256": role_b["artifact_set_sha256"],
                "runtime_metrics": role_b["metrics"],
            },
        },
        "evidence_stage": EvidenceStage.COMPARE.value,
        "evidence_manifest": [
            {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}
            for item in evidence
        ],
        "metrics": metrics,
        "error_analysis": error_analysis,
        "cash_flow": {
            "method": cash_flow.method.value,
            "direct_anchor_positions": cash_flow.direct_anchor_positions,
            "indirect_anchor_positions": cash_flow.indirect_anchor_positions,
            "reason": cash_flow.reason,
            "semantic_high_confidence_allowed": cash_flow.semantic_high_confidence_allowed,
        },
        "continuation": continuation,
        "off_balance_gate": {
            "eligible_rows_on_off_balance_pages": off_balance_eligible,
            "status": "PASS_ZERO_CDKT_ELIGIBLE_ROWS",
        },
        "acceptance": {
            "auto_verified_high": 0,
            "reason": (
                "Cross-reader agreement lacks independently verified cell geometry and cannot "
                "alone satisfy the high-confidence gate."
            ),
            "disagreements_trigger_reread_or_review": True,
            "agreement_promotes_pdf_confidence": False,
        },
        "historical_weak_reference": {
            "invoked": False,
            "reason": "Rows are not schema-resolved, so resolved-ID-only history is unavailable.",
            "mapping_or_confidence_effect": "NONE",
            "policy": suite.historical_policy,
        },
        "pages": page_results,
        "algorithm_files_sha256": {
            path.as_posix(): sha256_file(project_root / path) for path in implementation_paths
        },
        "claim_boundary": (
            "Cross-reader calibration against a native machine reference; not human-gold, "
            "schema/full-tuple, holdout, or production accuracy."
        ),
    }
    atomic_write_json(output_path, payload)
    return payload
