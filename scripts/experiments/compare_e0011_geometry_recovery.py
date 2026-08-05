from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.core.text import normalize_text
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    load_frozen_suite,
    validate_evidence_manifest,
)
from bctc_ai.evaluation.reader_outputs import (
    compare_reader_rows,
    parse_paddle_vl_page,
    reader_row_from_dict,
)
from bctc_ai.evaluation.word_box_rows import (
    ParsedGeometryPage,
    geometry_row_to_dict,
    load_word_box_reconstruction_config,
    parse_ppocrv6_word_box_page,
)
from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.tables.continuation import TableFragment, build_continuation_graph
from bctc_ai.validation.arithmetic import NumericOperand, check_sum


class GeometryRecoveryComparisonError(RuntimeError):
    pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare sealed E-0011 word geometry")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0011-tcb-geometry-recovery.yaml"),
    )
    parser.add_argument(
        "--role-a-seal",
        type=Path,
        default=Path(
            "output/calibration/e0010-tcb-role-a/f48ff3a87b68d7bccc72/role_a_seal.json"
        ),
    )
    parser.add_argument(
        "--role-b-seal",
        type=Path,
        default=Path(
            "output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/role_b_ocr_seal.json"
        ),
    )
    parser.add_argument(
        "--role-c-seal",
        type=Path,
        default=Path(
            "output/calibration/e0011-tcb-role-c/7e3f491783a9895d7716/role_c_geometry_seal.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0011-tcb-geometry-recovery.json"),
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise GeometryRecoveryComparisonError(f"cannot read JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise GeometryRecoveryComparisonError(f"JSON artifact is not an object: {path}")
    return payload


def _load_experiment_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GeometryRecoveryComparisonError(f"experiment config is absent: {path}") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("version") != 1
        or payload.get("experiment_id") != "E-0011"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("design") != "TARGETED_POST_FAILURE_ANALYSIS"
        or payload.get("content_inspected_before_design") is not True
    ):
        raise GeometryRecoveryComparisonError("invalid E-0011 targeted calibration config")
    if not isinstance(payload.get("acceptance"), dict) or not isinstance(
        payload.get("arithmetic_policy"), dict
    ):
        raise GeometryRecoveryComparisonError("E-0011 lacks acceptance or arithmetic policy")
    return payload


def _resolve(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise GeometryRecoveryComparisonError(f"artifact escapes project root: {path}") from exc


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _verify_record(project_root: Path, record: dict[str, Any], label: str) -> Path:
    path = _resolve(project_root, str(record.get("path", "")))
    if not path.is_file() or sha256_file(path) != record.get("sha256"):
        raise GeometryRecoveryComparisonError(f"sealed {label} is absent or hash-drifted: {path}")
    return path


def _verify_role_a(project_root: Path, seal_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    seal = _load_json(seal_path)
    if seal.get("state") != "REFERENCE_COMPLETE":
        raise GeometryRecoveryComparisonError("Role A seal is incomplete")
    result_path = _resolve(project_root, str(seal.get("result_path", "")))
    if not result_path.is_file() or sha256_file(result_path) != seal.get("result_sha256"):
        raise GeometryRecoveryComparisonError("Role A result hash differs from its seal")
    return seal, _load_json(result_path)


def _verify_role_b(project_root: Path, seal_path: Path) -> dict[str, Any]:
    seal = _load_json(seal_path)
    if seal.get("state") != "OCR_COMPLETE":
        raise GeometryRecoveryComparisonError("Role B seal is incomplete")
    implementation = seal.get("seal_implementation")
    if not isinstance(implementation, dict):
        raise GeometryRecoveryComparisonError("Role B seal lacks implementation identity")
    _verify_record(project_root, implementation, "Role B seal implementation")
    pages = seal.get("pages")
    if not isinstance(pages, list):
        raise GeometryRecoveryComparisonError("Role B seal contains no pages")
    for page in pages:
        if not isinstance(page, dict):
            raise GeometryRecoveryComparisonError("Role B page record is invalid")
        _verify_record(project_root, page["render"], "Role B render")
        _verify_record(project_root, page["metrics"], "Role B metrics")
        outputs = page.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            raise GeometryRecoveryComparisonError("Role B page has no sealed outputs")
        for output in outputs:
            _verify_record(project_root, output, "Role B output")
    return seal


def _verify_role_c(
    project_root: Path, seal_path: Path, role_b_seal_path: Path
) -> dict[str, Any]:
    seal = _load_json(seal_path)
    if seal.get("state") != "GEOMETRY_OCR_COMPLETE":
        raise GeometryRecoveryComparisonError("Role C geometry seal is incomplete")
    if seal.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY":
        raise GeometryRecoveryComparisonError("Role C evidence role is unsafe")
    upstream = seal.get("upstream_role_b_seal")
    if not isinstance(upstream, dict) or upstream.get("sha256") != sha256_file(role_b_seal_path):
        raise GeometryRecoveryComparisonError("Role C was not derived from the supplied Role B seal")
    if _resolve(project_root, str(upstream.get("path", ""))) != role_b_seal_path:
        raise GeometryRecoveryComparisonError("Role C upstream Role B path differs")
    implementation = seal.get("seal_implementation")
    if not isinstance(implementation, dict):
        raise GeometryRecoveryComparisonError("Role C seal lacks implementation identity")
    _verify_record(project_root, implementation, "Role C seal implementation")
    runtime = seal.get("runtime")
    if not isinstance(runtime, dict):
        raise GeometryRecoveryComparisonError("Role C seal lacks runtime identity")
    for prefix in ("manifest", "inference_config", "package_freeze", "runner"):
        record = {"path": runtime.get(f"{prefix}_path"), "sha256": runtime.get(f"{prefix}_sha256")}
        _verify_record(project_root, record, f"Role C {prefix}")
    pages = seal.get("pages")
    if not isinstance(pages, list):
        raise GeometryRecoveryComparisonError("Role C seal contains no pages")
    artifact_lines = []
    for page in pages:
        if not isinstance(page, dict):
            raise GeometryRecoveryComparisonError("Role C page record is invalid")
        for key in ("render", "run_manifest", "ocr_result"):
            record = page.get(key)
            if not isinstance(record, dict):
                raise GeometryRecoveryComparisonError(f"Role C page lacks {key}")
            path = _verify_record(project_root, record, f"Role C {key}")
            artifact_lines.append(f"{record['sha256']}  {_relative(project_root, path)}")
    if stable_records_hash(sorted(artifact_lines)) != seal.get("artifact_set_sha256"):
        raise GeometryRecoveryComparisonError("Role C artifact-set digest drift")
    return seal


def _role_b_result_path(project_root: Path, page_record: dict[str, Any]) -> Path:
    page = int(page_record["page"])
    suffix = f"page-{page:04d}_res.json"
    matches = [
        _resolve(project_root, str(output["path"]))
        for output in page_record["outputs"]
        if str(output["path"]).endswith(suffix)
    ]
    if len(matches) != 1:
        raise GeometryRecoveryComparisonError(f"expected one Role B JSON result on page {page}")
    return matches[0]


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _geometry_fragment(page: int, parsed: ParsedGeometryPage) -> TableFragment:
    note_axis = parsed.note_right_edge
    header = ("label", "note", *(axis.raw_header for axis in parsed.axes))
    centers = (
        0.0,
        note_axis if note_axis is not None else parsed.axes[0].right_edge / 2,
        *(axis.right_edge for axis in parsed.axes),
    )
    return TableFragment(
        table_id=f"role-c-page-{page:04d}-table-1",
        page=page,
        header_labels=header,
        column_centers=centers,
        unit=None,
        period_labels=tuple(axis.raw_header for axis in parsed.axes),
        notes_section="visible-note-axis" if note_axis is not None else None,
        parent_section="LCTT_STATEMENT_BLOCK",
        starts_with_repeated_header=True,
    )


def _portable_row(record: dict[str, Any], project_root: Path) -> dict[str, Any]:
    evidence = record["geometry"]["visual_cell_evidence"]
    for item in evidence:
        if item is not None:
            item["source_image_path"] = _relative(
                project_root, Path(str(item["source_image_path"]))
            )
    return record


def _cash_flow_record(evidence) -> dict[str, Any]:
    return {
        "method": evidence.method.value,
        "indirect_anchor_positions": evidence.indirect_anchor_positions,
        "direct_anchor_positions": evidence.direct_anchor_positions,
        "reason": evidence.reason,
        "semantic_high_confidence_allowed": evidence.semantic_high_confidence_allowed,
    }


def _operand(
    pages: dict[int, ParsedGeometryPage],
    spec: dict[str, Any],
    period_index: int,
) -> NumericOperand:
    page = int(spec["page"])
    row_index = int(spec["row_index"])
    try:
        row = pages[page].rows[row_index].row
        cell = row.cells[period_index]
    except (KeyError, IndexError) as exc:
        raise GeometryRecoveryComparisonError(
            f"arithmetic operand is outside reconstructed evidence: page={page}, row={row_index}"
        ) from exc
    value = (
        cell.value
        if cell.observation in {ObservationKind.VALUE, ObservationKind.ZERO}
        else None
    )
    return NumericOperand(
        operand_id=f"page-{page:04d}:row-{row_index:04d}:value-{period_index + 1}",
        value=value,
        page=page,
        cell_id=f"value-{period_index + 1}",
    )


def _arithmetic_findings(
    policy: dict[str, Any], pages: dict[int, ParsedGeometryPage]
) -> tuple[list[dict[str, Any]], Counter[str]]:
    if (
        policy.get("purpose") != "VALIDATION_AND_REREAD_TRIGGER_ONLY"
        or policy.get("may_generate_or_overwrite_values") is not False
        or policy.get("blank_operand_policy") != "NOT_TESTABLE"
        or policy.get("dash_operand_policy") != "NOT_TESTABLE"
    ):
        raise GeometryRecoveryComparisonError("arithmetic policy permits unsafe value inference")
    equations = policy.get("equations")
    if not isinstance(equations, list) or not equations:
        raise GeometryRecoveryComparisonError("no frozen arithmetic equations")
    tolerance = Decimal(str(policy.get("tolerance", "0")))
    records = []
    counts: Counter[str] = Counter()
    for equation in equations:
        if not isinstance(equation, dict) or not isinstance(equation.get("components"), list):
            raise GeometryRecoveryComparisonError("invalid arithmetic equation")
        for period_index in range(2):
            total = _operand(pages, equation["total"], period_index)
            components = [
                _operand(pages, component, period_index)
                for component in equation["components"]
            ]
            finding = check_sum(
                total,
                components,
                check_type=f"CONFIGURED_SUM:{equation['equation_id']}",
                tolerance=tolerance,
            )
            counts[finding.result.value] += 1
            records.append(
                {
                    "equation_id": equation["equation_id"],
                    "period_index": period_index,
                    "check_type": finding.check_type,
                    "result": finding.result.value,
                    "expected": str(finding.expected) if finding.expected is not None else None,
                    "observed": str(finding.observed) if finding.observed is not None else None,
                    "residual": str(finding.residual) if finding.residual is not None else None,
                    "tolerance": str(finding.tolerance),
                    "operand_ids": list(finding.operand_ids),
                    "remediation": list(finding.remediation),
                    "may_generate_value": finding.may_generate_value,
                }
            )
    return records, counts


def _validate_acceptance(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    mismatches = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise GeometryRecoveryComparisonError(f"E-0011 acceptance mismatch: {mismatches}")


def main() -> int:
    args = _parse_args()
    project_root = args.project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise GeometryRecoveryComparisonError("comparison must start from a clean Git worktree")
    output_path = _resolve(project_root, args.output)
    if output_path.exists():
        raise GeometryRecoveryComparisonError(f"refusing to overwrite immutable output: {output_path}")
    experiment_config_path = _resolve(project_root, args.experiment_config)
    experiment = _load_experiment_config(experiment_config_path)
    upstream = experiment["upstream"]
    suite_path = _resolve(project_root, str(upstream["frozen_suite"]))
    reconstruction_config_path = _resolve(
        project_root, str(upstream["reconstruction_config"])
    )
    baseline_path = _resolve(project_root, str(upstream["baseline_result"]))
    suite = load_frozen_suite(project_root, suite_path)
    reconstruction_config = load_word_box_reconstruction_config(reconstruction_config_path)
    baseline = _load_json(baseline_path)
    if baseline.get("experiment_id") != "E-0010":
        raise GeometryRecoveryComparisonError("configured baseline is not E-0010")

    role_a_seal_path = _resolve(project_root, args.role_a_seal)
    role_b_seal_path = _resolve(project_root, args.role_b_seal)
    role_c_seal_path = _resolve(project_root, args.role_c_seal)
    role_a_seal, role_a = _verify_role_a(project_root, role_a_seal_path)
    role_b = _verify_role_b(project_root, role_b_seal_path)
    role_c = _verify_role_c(project_root, role_c_seal_path, role_b_seal_path)
    reference_source = suite.source(str(suite.pairing["reference_fixture_id"]))
    candidate_source = suite.source(str(suite.pairing["candidate_fixture_id"]))
    if role_a.get("source_sha256") != reference_source.sha256:
        raise GeometryRecoveryComparisonError("Role A source differs from frozen reference")
    if role_b.get("source_sha256") != candidate_source.sha256:
        raise GeometryRecoveryComparisonError("Role B source differs from frozen candidate")
    if role_c.get("source_sha256") != candidate_source.sha256:
        raise GeometryRecoveryComparisonError("Role C source differs from frozen candidate")

    evidence = (
        EvidenceItem(
            EvidenceKind.ROLE_A_RESULT,
            str(role_a_seal["result_path"]),
            str(role_a_seal["result_sha256"]),
        ),
        EvidenceItem(
            EvidenceKind.ROLE_B_RESULT,
            _relative(project_root, role_b_seal_path),
            sha256_file(role_b_seal_path),
        ),
        EvidenceItem(
            EvidenceKind.INDEPENDENT_GEOMETRY_RESULT,
            _relative(project_root, role_c_seal_path),
            sha256_file(role_c_seal_path),
        ),
        EvidenceItem(EvidenceKind.CONFIG, _relative(project_root, suite_path), sha256_file(suite_path)),
        EvidenceItem(
            EvidenceKind.CONFIG,
            _relative(project_root, experiment_config_path),
            sha256_file(experiment_config_path),
        ),
        EvidenceItem(
            EvidenceKind.CONFIG,
            _relative(project_root, reconstruction_config_path),
            sha256_file(reconstruction_config_path),
        ),
    )
    validate_evidence_manifest(EvidenceStage.INDEPENDENT_GEOMETRY_COMPARE, evidence)

    scope_policy_path = project_root / "config/mapping/scope_exclusions.yaml"
    cash_flow_rules_path = project_root / "config/mapping/lctt.yaml"
    scope_policy = load_scope_policy(scope_policy_path)
    cash_flow_rules = load_cash_flow_rules(cash_flow_rules_path)
    role_a_pages = {int(page["reference_page"]): page for page in role_a["pages"]}
    role_b_pages = {int(page["page"]): page for page in role_b["pages"]}
    role_c_pages = {int(page["page"]): page for page in role_c["pages"]}

    parsed_pages: dict[int, ParsedGeometryPage] = {}
    page_results = []
    lctt_role_b_labels: list[str] = []
    lctt_role_c_labels: list[str] = []
    lctt_fragments = []
    pixel_recoveries = []
    alias_recoveries = []
    for contract in suite.pairing["target_page_contracts"]:
        reference_page = int(contract["reference_page"])
        candidate_page = int(contract["candidate_page"])
        if candidate_page not in role_b_pages or candidate_page not in role_c_pages:
            raise GeometryRecoveryComparisonError(f"sealed page is missing: {candidate_page}")
        reference_record = role_a_pages[reference_page]
        role_b_record = role_b_pages[candidate_page]
        role_c_record = role_c_pages[candidate_page]
        render_path = _verify_record(project_root, role_c_record["render"], "Role C render")
        result_path = _verify_record(
            project_root, role_c_record["ocr_result"], "Role C OCR result"
        )
        parsed = parse_ppocrv6_word_box_page(
            result_path,
            reconstruction_config,
            page_tag=f"page-{candidate_page:04d}",
            source_image_path=render_path,
        )
        parsed_pages[candidate_page] = parsed
        raw_geometry = _load_json(result_path)
        reference_rows = tuple(
            reader_row_from_dict(record) for record in reference_record["rows"]
        )
        vlm_page = parse_paddle_vl_page(_role_b_result_path(project_root, role_b_record))
        comparison = compare_reader_rows(
            reference_rows,
            tuple(proposal.row for proposal in parsed.rows),
            statement_type=str(contract["statement_type"]),
            scope_policy=scope_policy,
            candidate_context_text=vlm_page.context_text,
        )
        if contract["expected_scope"] == "OFF_BALANCE_SHEET" and comparison["counts"][
            "scope_allowed_candidate_rows"
        ]:
            raise GeometryRecoveryComparisonError(
                "off-balance Role C rows remained eligible for CDKT mapping"
            )
        for row_index, proposal in enumerate(parsed.rows):
            for axis_index, (cell, line_indices, visual) in enumerate(
                zip(
                    proposal.row.cells,
                    proposal.value_line_indices,
                    proposal.visual_cell_evidence,
                    strict=True,
                )
            ):
                if visual is not None:
                    pixel_recoveries.append(
                        {
                            "page": candidate_page,
                            "row_index": row_index,
                            "axis_index": axis_index,
                            "label": proposal.row.label,
                            "evidence": _portable_row(
                                geometry_row_to_dict(proposal), project_root
                            )["geometry"]["visual_cell_evidence"][axis_index],
                            "confidence_effect": "NO_PROMOTION",
                        }
                    )
                elif cell.observation is ObservationKind.DASH and line_indices:
                    raw_tokens = [str(raw_geometry["rec_texts"][index]) for index in line_indices]
                    normalized_tokens = [normalize_text(token) for token in raw_tokens]
                    if any(token not in {"-", "--"} for token in normalized_tokens):
                        alias_recoveries.append(
                            {
                                "page": candidate_page,
                                "row_index": row_index,
                                "axis_index": axis_index,
                                "label": proposal.row.label,
                                "raw_ocr_tokens": raw_tokens,
                                "source_line_indices": list(line_indices),
                                "normalized_observation": "DASH",
                                "confidence_effect": "NO_PROMOTION",
                            }
                        )
        if contract["statement_type"] == "LCTT":
            lctt_role_b_labels.extend(row.label for table in vlm_page.tables for row in table.rows)
            lctt_role_c_labels.extend(proposal.row.label for proposal in parsed.rows)
            lctt_fragments.append(_geometry_fragment(candidate_page, parsed))
        page_results.append(
            {
                "reference_page": reference_page,
                "candidate_page": candidate_page,
                "statement_type": contract["statement_type"],
                "expected_scope": contract["expected_scope"],
                "context_source": "SEALED_ROLE_B_NON_TABLE_BLOCKS",
                "comparison": comparison,
                "geometry": {
                    "render": role_c_record["render"],
                    "ocr_result": role_c_record["ocr_result"],
                    "line_height": parsed.line_height,
                    "table_bbox": list(parsed.table_bbox),
                    "note_right_edge": parsed.note_right_edge,
                    "axes": [asdict(axis) for axis in parsed.axes],
                    "rows": [
                        _portable_row(geometry_row_to_dict(proposal), project_root)
                        for proposal in parsed.rows
                    ],
                    "trailing_context_rows": [
                        _portable_row(geometry_row_to_dict(proposal), project_root)
                        for proposal in parsed.trailing_context_rows
                    ],
                    "unassigned_numeric_line_indices": list(
                        parsed.unassigned_numeric_line_indices
                    ),
                    "excluded_after_table_line_indices": list(
                        parsed.excluded_after_table_line_indices
                    ),
                },
            }
        )

    sum_fields = (
        "reference_rows",
        "candidate_rows",
        "structurally_comparable_rows",
        "source_exact_labels",
        "semantic_key_exact_labels",
        "reference_financial_rows",
        "covered_reference_financial_rows",
        "exact_reference_financial_rows",
        "reference_financial_cells",
        "compared_reference_financial_cells",
        "exact_reference_financial_cells",
        "candidate_invalid_cells",
        "note_rows",
        "exact_note_references",
        "scope_allowed_candidate_rows",
        "scope_excluded_candidate_rows",
    )
    totals = {
        field: sum(int(page["comparison"]["counts"][field]) for page in page_results)
        for field in sum_fields
    }
    actions: Counter[str] = Counter()
    escalations: Counter[str] = Counter()
    for page in page_results:
        actions.update(page["comparison"]["counts"]["alignment_actions"])
        escalations.update(page["comparison"]["counts"]["escalations"])
    totals["alignment_actions"] = dict(sorted(actions.items()))
    totals["escalations"] = dict(sorted(escalations.items()))
    totals["source_exact_label_rate"] = _ratio(
        totals["source_exact_labels"], totals["structurally_comparable_rows"]
    )
    totals["semantic_key_exact_label_rate"] = _ratio(
        totals["semantic_key_exact_labels"], totals["structurally_comparable_rows"]
    )
    totals["reference_financial_row_coverage_rate"] = _ratio(
        totals["covered_reference_financial_rows"], totals["reference_financial_rows"]
    )
    totals["reference_financial_cell_coverage_rate"] = _ratio(
        totals["compared_reference_financial_cells"], totals["reference_financial_cells"]
    )
    totals["conditional_exact_cell_agreement_rate"] = _ratio(
        totals["exact_reference_financial_cells"], totals["compared_reference_financial_cells"]
    )
    totals["conditional_exact_financial_row_agreement_rate"] = _ratio(
        totals["exact_reference_financial_rows"], totals["covered_reference_financial_rows"]
    )
    totals["strict_exact_reference_cell_agreement_rate"] = _ratio(
        totals["exact_reference_financial_cells"], totals["reference_financial_cells"]
    )
    totals["strict_exact_reference_financial_row_agreement_rate"] = _ratio(
        totals["exact_reference_financial_rows"], totals["reference_financial_rows"]
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
    arithmetic_findings, arithmetic_counts = _arithmetic_findings(
        experiment["arithmetic_policy"], parsed_pages
    )
    role_b_cash_flow = classify_cash_flow_method(lctt_role_b_labels, cash_flow_rules)
    role_c_cash_flow = classify_cash_flow_method(lctt_role_c_labels, cash_flow_rules)
    off_balance_eligible = sum(
        page["comparison"]["counts"]["scope_allowed_candidate_rows"]
        for page in page_results
        if page["expected_scope"] == "OFF_BALANCE_SHEET"
    )
    trailing_context_count = sum(
        len(page["geometry"]["trailing_context_rows"]) for page in page_results
    )
    accepted_continuations = sum(edge["accepted"] for edge in continuation)
    acceptance_actual = {
        "required_alignment_actions": totals["alignment_actions"],
        "required_reference_financial_row_coverage_rate": totals[
            "reference_financial_row_coverage_rate"
        ],
        "required_strict_exact_reference_financial_row_agreement_rate": totals[
            "strict_exact_reference_financial_row_agreement_rate"
        ],
        "required_reference_financial_cell_coverage_rate": totals[
            "reference_financial_cell_coverage_rate"
        ],
        "required_strict_exact_reference_cell_agreement_rate": totals[
            "strict_exact_reference_cell_agreement_rate"
        ],
        "required_candidate_invalid_cells": totals["candidate_invalid_cells"],
        "required_exact_note_references": totals["exact_note_references"],
        "required_off_balance_eligible_rows": off_balance_eligible,
        "required_pixel_dash_recoveries": len(pixel_recoveries),
        "required_ocr_dash_alias_recoveries": len(alias_recoveries),
        "required_trailing_context_rows": trailing_context_count,
        "required_accepted_continuation_edges": accepted_continuations,
        "required_arithmetic_passes": arithmetic_counts["PASS"],
        "required_arithmetic_not_testable": arithmetic_counts["NOT_TESTABLE"],
        "required_arithmetic_failures": arithmetic_counts["FAIL"],
    }
    _validate_acceptance(experiment["acceptance"], acceptance_actual)

    baseline_metrics = baseline["metrics"]
    implementation_paths = (
        Path("src/bctc_ai/core/text.py"),
        Path("src/bctc_ai/evaluation/reader_outputs.py"),
        Path("src/bctc_ai/evaluation/word_box_rows.py"),
        Path("src/bctc_ai/validation/reader_agreement.py"),
        Path("src/bctc_ai/validation/arithmetic.py"),
        Path("src/bctc_ai/mapping/scope.py"),
        Path("src/bctc_ai/mapping/lctt.py"),
        Path("src/bctc_ai/tables/continuation.py"),
        Path("scripts/experiments/compare_e0011_geometry_recovery.py"),
    )
    payload = {
        "format_version": 1,
        "experiment_id": "E-0011",
        "status": "PASS_TARGETED_GEOMETRY_RECOVERY_CALIBRATION",
        "dataset_role": suite.dataset_role.value,
        "design": experiment["design"],
        "content_inspected_before_design": experiment["content_inspected_before_design"],
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
        "experiment_config": {
            "path": _relative(project_root, experiment_config_path),
            "sha256": sha256_file(experiment_config_path),
        },
        "suite_config": {
            "path": _relative(project_root, suite_path),
            "sha256": sha256_file(suite_path),
        },
        "reconstruction_config": {
            "path": _relative(project_root, reconstruction_config_path),
            "sha256": sha256_file(reconstruction_config_path),
        },
        "sealed_inputs": {
            "role_a_seal": {
                "path": _relative(project_root, role_a_seal_path),
                "sha256": sha256_file(role_a_seal_path),
                "result_sha256": role_a_seal["result_sha256"],
            },
            "role_b_seal": {
                "path": _relative(project_root, role_b_seal_path),
                "sha256": sha256_file(role_b_seal_path),
                "artifact_set_sha256": role_b["artifact_set_sha256"],
            },
            "role_c_seal": {
                "path": _relative(project_root, role_c_seal_path),
                "sha256": sha256_file(role_c_seal_path),
                "artifact_set_sha256": role_c["artifact_set_sha256"],
                "runtime_metrics": role_c["metrics"],
            },
        },
        "evidence_stage": EvidenceStage.INDEPENDENT_GEOMETRY_COMPARE.value,
        "evidence_manifest": [
            {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}
            for item in evidence
        ],
        "reader_roles": {
            "role_a": "SEALED_SEARCHABLE_MACHINE_REFERENCE_FOR_CALIBRATION_ONLY",
            "role_b": "SEALED_LABEL_AND_PAGE_CONTEXT_PROPOSAL",
            "role_c": "SEALED_INDEPENDENT_WORD_GEOMETRY_AND_VALUE_PROPOSAL",
            "rule": "No reader agreement promotes a row to verified-high confidence.",
        },
        "metrics": totals,
        "recovery_evidence": {
            "pixel_dash_recoveries": pixel_recoveries,
            "ocr_dash_alias_recoveries": alias_recoveries,
            "trailing_context_rows_preserved_but_mapping_ineligible": trailing_context_count,
            "automatic_confidence_effect": "NONE",
        },
        "arithmetic_validation": {
            "policy": {
                key: value
                for key, value in experiment["arithmetic_policy"].items()
                if key != "equations"
            },
            "counts": dict(sorted(arithmetic_counts.items())),
            "findings": arithmetic_findings,
            "value_generation_or_overwrite": False,
        },
        "cash_flow": {
            "role_b_label_reader": _cash_flow_record(role_b_cash_flow),
            "role_c_geometry_reader": _cash_flow_record(role_c_cash_flow),
            "combined_structural_observation": "DIRECT_LIKE_VISIBLE_ORDER",
            "schema_branch_assignment_permitted": False,
            "reason": (
                "Role B sees the configured direct anchor order and Role C recovers its rows, "
                "but Q-BOOT-001/workbook branch semantics remain REOPENED_EVIDENCE_CONFLICT."
            ),
        },
        "continuation": continuation,
        "off_balance_gate": {
            "eligible_rows_on_off_balance_pages": off_balance_eligible,
            "excluded_rows_on_off_balance_pages": sum(
                page["comparison"]["counts"]["scope_excluded_candidate_rows"]
                for page in page_results
                if page["expected_scope"] == "OFF_BALANCE_SHEET"
            ),
            "status": "PASS_ZERO_CDKT_ELIGIBLE_ROWS",
        },
        "acceptance": {
            "configured": experiment["acceptance"],
            "observed": acceptance_actual,
            "auto_verified_high": 0,
            "agreement_promotes_pdf_confidence": False,
            "geometry_reader_can_override_label_or_schema_identity": False,
            "status": "PASS_ALL_TARGETED_GATES_WITHOUT_CONFIDENCE_PROMOTION",
        },
        "baseline_delta": {
            "reporting_only_not_input_to_reconstruction": True,
            "baseline": {
                "path": _relative(project_root, baseline_path),
                "sha256": sha256_file(baseline_path),
                "experiment_id": baseline["experiment_id"],
            },
            "financial_row_coverage_rate": {
                "before": baseline_metrics["reference_financial_row_coverage_rate"],
                "after": totals["reference_financial_row_coverage_rate"],
            },
            "strict_exact_financial_row_agreement_rate": {
                "before": baseline_metrics[
                    "strict_exact_reference_financial_row_agreement_rate"
                ],
                "after": totals["strict_exact_reference_financial_row_agreement_rate"],
            },
            "financial_cell_coverage_rate": {
                "before": baseline_metrics["reference_financial_cell_coverage_rate"],
                "after": totals["reference_financial_cell_coverage_rate"],
            },
            "strict_exact_financial_cell_agreement_rate": {
                "before": baseline_metrics["strict_exact_reference_cell_agreement_rate"],
                "after": totals["strict_exact_reference_cell_agreement_rate"],
            },
            "candidate_invalid_cells": {
                "before": baseline_metrics["candidate_invalid_cells"],
                "after": totals["candidate_invalid_cells"],
            },
        },
        "historical_weak_reference": {
            "invoked": False,
            "reason": "Rows are not schema-resolved; resolved-ID-only history lookup is unavailable.",
            "mapping_or_confidence_effect": "NONE",
            "policy": suite.historical_policy,
        },
        "report_norm_id": {
            "ids_proposed_or_added": 0,
            "collision_check_invoked": False,
            "reason": "E-0011 performs no schema assignment and adds no ReportNormID.",
        },
        "ytd_derivation": {
            "invoked": False,
            "reason": "The tested statements expose annual current/comparative values; no YTD subtraction applies.",
        },
        "pages": page_results,
        "algorithm_files_sha256": {
            path.as_posix(): sha256_file(project_root / path) for path in implementation_paths
        },
        "claim_boundary": (
            "This is a targeted, post-failure calibration against one sealed TCB machine "
            "reference. It demonstrates recovery of these pages, not human-gold, schema, "
            "multi-bank holdout, or production accuracy."
        ),
    }
    atomic_write_json(output_path, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "metrics": totals,
                "dash_recoveries": {
                    "pixel": len(pixel_recoveries),
                    "ocr_alias": len(alias_recoveries),
                },
                "arithmetic": dict(sorted(arithmetic_counts.items())),
                "off_balance_gate": payload["off_balance_gate"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
