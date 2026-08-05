from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import parse_unit
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
from bctc_ai.mapping.lctt import classify_cash_flow_method, load_cash_flow_rules
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.tables.continuation import TableFragment, build_continuation_graph


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare sealed E-0010 Role A and Role B")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--suite-config",
        type=Path,
        default=Path("config/experiments/e0009-frozen-paired-calibration.yaml"),
    )
    parser.add_argument("--role-a-seal", type=Path, required=True)
    parser.add_argument("--role-b-seal", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0010-tcb-cross-reader-calibration.json"),
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _resolve(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _git(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=project_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _verify_role_a(project_root: Path, seal_path: Path) -> tuple[dict, dict]:
    seal = _load_json(seal_path)
    if seal.get("state") != "REFERENCE_COMPLETE":
        raise RuntimeError("Role A seal is incomplete")
    result_path = _resolve(project_root, str(seal["result_path"]))
    if sha256_file(result_path) != seal.get("result_sha256"):
        raise RuntimeError("Role A result hash does not match its seal")
    return seal, _load_json(result_path)


def _verify_role_b(project_root: Path, seal_path: Path) -> dict:
    seal = _load_json(seal_path)
    if seal.get("state") != "OCR_COMPLETE":
        raise RuntimeError("Role B seal is incomplete")
    pages = seal.get("pages")
    if not isinstance(pages, list):
        raise RuntimeError("Role B seal contains no pages")
    implementation = seal.get("seal_implementation")
    if not isinstance(implementation, dict):
        raise RuntimeError("Role B seal contains no implementation identity")
    implementation_path = _resolve(project_root, str(implementation["path"]))
    if sha256_file(implementation_path) != implementation.get("sha256"):
        raise RuntimeError("Role B seal implementation hash drift")
    for page in pages:
        for output in page["outputs"]:
            path = _resolve(project_root, output["path"])
            if not path.is_file() or sha256_file(path) != output["sha256"]:
                raise RuntimeError(f"Role B sealed output drift: {path}")
        metric_path = _resolve(project_root, page["metrics"]["path"])
        render_path = _resolve(project_root, page["render"]["path"])
        if sha256_file(metric_path) != page["metrics"]["sha256"]:
            raise RuntimeError(f"Role B metric drift: {metric_path}")
        if sha256_file(render_path) != page["render"]["sha256"]:
            raise RuntimeError(f"Role B render drift: {render_path}")
    return seal


def _result_path_for_page(project_root: Path, page_record: dict) -> Path:
    suffix = f"page-{int(page_record['page']):04d}_res.json"
    matches = [
        _resolve(project_root, output["path"])
        for output in page_record["outputs"]
        if str(output["path"]).endswith(suffix)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one Role B result file for page {page_record['page']}")
    return matches[0]


def _table_fragment(page: int, header: tuple[str, ...]) -> TableFragment:
    width = len(header)
    centers = tuple(index / max(1, width - 1) for index in range(width))
    parsed_unit = parse_unit(" ".join(header))
    unit = (
        f"{parsed_unit.canonical}:{parsed_unit.multiplier}"
        if parsed_unit.canonical and parsed_unit.multiplier
        else None
    )
    return TableFragment(
        table_id=f"role-b-page-{page:04d}-table-1",
        page=page,
        header_labels=header,
        column_centers=centers,
        unit=unit,
        period_labels=header[2:],
        notes_section=None,
        parent_section="LCTT_DIRECT_STRUCTURAL_BLOCK",
        starts_with_repeated_header=True,
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def main() -> int:
    args = _parse_args()
    project_root = args.project_root.resolve()
    if _git(project_root, "status", "--porcelain"):
        raise RuntimeError("comparison must start from a clean Git worktree")
    suite_path = _resolve(project_root, args.suite_config).resolve()
    suite = load_frozen_suite(project_root, suite_path)
    role_a_seal_path = _resolve(project_root, args.role_a_seal).resolve()
    role_b_seal_path = _resolve(project_root, args.role_b_seal).resolve()
    role_a_seal, role_a = _verify_role_a(project_root, role_a_seal_path)
    role_b = _verify_role_b(project_root, role_b_seal_path)
    reference_source = suite.source(str(suite.pairing["reference_fixture_id"]))
    candidate_source = suite.source(str(suite.pairing["candidate_fixture_id"]))
    if role_a.get("source_sha256") != reference_source.sha256:
        raise RuntimeError("Role A source differs from the frozen paired reference")
    if role_b.get("source_sha256") != candidate_source.sha256:
        raise RuntimeError("Role B source differs from the frozen paired candidate")
    if role_a.get("suite_config", {}).get("sha256") != sha256_file(suite_path):
        raise RuntimeError("Role A suite config hash drift")

    compare_evidence = (
        EvidenceItem(
            EvidenceKind.ROLE_A_RESULT,
            str(role_a_seal["result_path"]),
            str(role_a_seal["result_sha256"]),
        ),
        EvidenceItem(
            EvidenceKind.ROLE_B_RESULT,
            role_b_seal_path.relative_to(project_root).as_posix(),
            sha256_file(role_b_seal_path),
        ),
        EvidenceItem(
            EvidenceKind.CONFIG,
            suite_path.relative_to(project_root).as_posix(),
            sha256_file(suite_path),
        ),
    )
    validate_evidence_manifest(EvidenceStage.COMPARE, compare_evidence)
    scope_policy_path = project_root / "config/mapping/scope_exclusions.yaml"
    scope_policy = load_scope_policy(scope_policy_path)
    cash_flow_rules_path = project_root / "config/mapping/lctt.yaml"
    cash_flow_rules = load_cash_flow_rules(cash_flow_rules_path)

    role_a_pages = {
        int(page["reference_page"]): page for page in role_a["pages"]
    }
    role_b_pages = {int(page["page"]): page for page in role_b["pages"]}
    page_results = []
    lctt_candidate_labels: list[str] = []
    lctt_fragments = []
    for contract in suite.pairing["target_page_contracts"]:
        reference_page = int(contract["reference_page"])
        candidate_page = int(contract["candidate_page"])
        reference_record = role_a_pages[reference_page]
        candidate_record = role_b_pages[candidate_page]
        reference_rows = tuple(
            reader_row_from_dict(record) for record in reference_record["rows"]
        )
        vlm_page = parse_paddle_vl_page(
            _result_path_for_page(project_root, candidate_record)
        )
        candidate_rows = tuple(row for table in vlm_page.tables for row in table.rows)
        comparison = compare_reader_rows(
            reference_rows,
            candidate_rows,
            statement_type=str(contract["statement_type"]),
            scope_policy=scope_policy,
            candidate_context_text=vlm_page.context_text,
        )
        if contract["expected_scope"] == "OFF_BALANCE_SHEET":
            if comparison["counts"]["scope_allowed_candidate_rows"]:
                raise RuntimeError("off-balance candidate rows remained eligible for CDKT mapping")
        if contract["statement_type"] == "LCTT":
            lctt_candidate_labels.extend(row.label for row in candidate_rows)
            lctt_fragments.append(_table_fragment(candidate_page, vlm_page.tables[0].header))
        page_results.append(
            {
                "reference_page": reference_page,
                "candidate_page": candidate_page,
                "statement_type": contract["statement_type"],
                "expected_scope": contract["expected_scope"],
                "reference_headers": reference_record["headers"],
                "candidate_headers": [list(table.header) for table in vlm_page.tables],
                "candidate_table_bboxes": [list(table.bbox) for table in vlm_page.tables],
                "comparison": comparison,
            }
        )

    continuation_graph = build_continuation_graph(lctt_fragments)
    accepted_continuation = any(edge.accepted for edge in continuation_graph.edges)
    if not accepted_continuation:
        raise RuntimeError("paired LCTT pages did not pass the continuation gate")
    cash_flow = classify_cash_flow_method(lctt_candidate_labels, cash_flow_rules)

    sum_fields = (
        "reference_rows",
        "candidate_rows",
        "matched_rows",
        "source_exact_labels",
        "semantic_key_exact_labels",
        "financial_rows",
        "exact_financial_rows",
        "compared_cells",
        "exact_cells",
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
    escalations: Counter[str] = Counter()
    actions: Counter[str] = Counter()
    for page in page_results:
        escalations.update(page["comparison"]["counts"]["escalations"])
        actions.update(page["comparison"]["counts"]["alignment_actions"])
    totals["alignment_actions"] = dict(sorted(actions.items()))
    totals["escalations"] = dict(sorted(escalations.items()))
    totals["source_exact_label_rate"] = _ratio(
        totals["source_exact_labels"], totals["matched_rows"]
    )
    totals["semantic_key_exact_label_rate"] = _ratio(
        totals["semantic_key_exact_labels"], totals["matched_rows"]
    )
    totals["exact_cell_agreement_rate"] = _ratio(
        totals["exact_cells"], totals["compared_cells"]
    )
    totals["exact_financial_row_agreement_rate"] = _ratio(
        totals["exact_financial_rows"], totals["financial_rows"]
    )

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
    implementation_paths = (
        Path("src/bctc_ai/core/text.py"),
        Path("src/bctc_ai/evaluation/reader_outputs.py"),
        Path("src/bctc_ai/validation/reader_agreement.py"),
        Path("src/bctc_ai/mapping/scope.py"),
        Path("src/bctc_ai/tables/continuation.py"),
        Path("scripts/experiments/compare_e0010_paired_readers.py"),
    )
    payload = {
        "format_version": 1,
        "experiment_id": "E-0010",
        "status": "PASS_CALIBRATION_WITH_REQUIRED_ESCALATIONS",
        "dataset_role": suite.dataset_role.value,
        "code": {
            "git_commit": _git(project_root, "rev-parse", "HEAD"),
            "git_dirty": False,
        },
        "suite_config": {
            "path": suite_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(suite_path),
        },
        "sealed_inputs": {
            "role_a_seal": {
                "path": role_a_seal_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(role_a_seal_path),
                "result_sha256": role_a_seal["result_sha256"],
            },
            "role_b_seal": {
                "path": role_b_seal_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(role_b_seal_path),
                "artifact_set_sha256": role_b["artifact_set_sha256"],
                "runtime_metrics": role_b["metrics"],
            },
        },
        "evidence_stage": EvidenceStage.COMPARE.value,
        "evidence_manifest": [
            {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}
            for item in compare_evidence
        ],
        "metrics": totals,
        "cash_flow": {
            "method": cash_flow.method.value,
            "direct_anchor_positions": cash_flow.direct_anchor_positions,
            "indirect_anchor_positions": cash_flow.indirect_anchor_positions,
            "reason": cash_flow.reason,
            "semantic_high_confidence_allowed": cash_flow.semantic_high_confidence_allowed,
        },
        "continuation": continuation,
        "off_balance_gate": {
            "eligible_rows_on_off_balance_pages": sum(
                page["comparison"]["counts"]["scope_allowed_candidate_rows"]
                for page in page_results
                if page["expected_scope"] == "OFF_BALANCE_SHEET"
            ),
            "status": "PASS_ZERO_CDKT_ELIGIBLE_ROWS",
        },
        "acceptance": {
            "auto_verified_high": 0,
            "reason": (
                "PaddleOCR-VL exposes table-level but not independently verified cell geometry; "
                "reader agreement alone cannot satisfy the high-confidence gate."
            ),
            "disagreements_trigger_reread_or_review": True,
            "agreement_promotes_pdf_confidence": False,
        },
        "historical_weak_reference": {
            "invoked": False,
            "reason": "Rows are not schema-resolved; resolved-ID-only history lookup is unavailable.",
            "mapping_or_confidence_effect": "NONE",
            "policy": suite.historical_policy,
        },
        "pages": page_results,
        "algorithm_files_sha256": {
            path.as_posix(): sha256_file(project_root / path) for path in implementation_paths
        },
        "claim_boundary": (
            "Metrics are cross-reader agreement against a native machine reference on one "
            "calibration filing. They are not human-gold, schema, full-tuple, holdout, or "
            "production accuracy."
        ),
    }
    output_path = _resolve(project_root, args.output).resolve()
    atomic_write_json(output_path, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "metrics": totals,
                "cash_flow_method": cash_flow.method.value,
                "off_balance_gate": payload["off_balance_gate"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
