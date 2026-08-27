#!/usr/bin/env python3
"""Consume family repair jobs, escalate thinking, and validate only affected candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    READY,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    pending_gemini_family_region_repair_plans_v1,
    record_gemini_family_region_repair_attempt_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    load_page_json_versions_v1,
)
from scripts.experiments.run_gemini_json_region_repair_v1 import (  # noqa: E402
    run as run_region_repair_v1,
)


class RunGeminiJsonFamilyRegionRepairWorkerV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--family-run-id")
    parser.add_argument("--repair-job-id", action="append")
    parser.add_argument("--page-database", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--openrouter-retries", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    parser.add_argument("--max-jobs", type=int, default=100)
    return parser


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunGeminiJsonFamilyRegionRepairWorkerV1Error(f"invalid JSON input: {path}") from exc
    if type(value) is not dict:
        raise RunGeminiJsonFamilyRegionRepairWorkerV1Error("spec is not one JSON object")
    return value


def _repair_args(
    args: argparse.Namespace,
    *,
    plan: dict[str, Any],
    thinking_level: str,
    attempt_ordinal: int,
) -> argparse.Namespace:
    return argparse.Namespace(
        artifact_dir=(
            args.artifact_root
            / plan["repair_job_id"].replace(":", "_")
            / f"attempt-{attempt_ordinal}-{thinking_level}"
        ),
        base_page_json_version_id=plan["base_page_json_version_id"],
        database=args.page_database,
        dpi=args.dpi,
        openrouter_key_file=args.openrouter_key_file,
        openrouter_retries=args.openrouter_retries,
        pdf=args.pdf_root / plan["source_logical_name"],
        physical_page=plan["physical_page"],
        retry_delay_seconds=args.retry_delay_seconds,
        repair_scope=plan.get("repair_scope", "ROW_VALUES"),
        source_logical_name=plan["source_logical_name"],
        target_id=plan["target_ids"],
        target_table_ref=[
            f"{ref['section_id']}:{ref['table_id']}" for ref in plan.get("target_table_refs", [])
        ],
        thinking_level=thinking_level,
        timeout_seconds=args.timeout_seconds,
    )


def _targeted_repair_is_accepted(plan: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if candidate["status"] == READY:
        return True
    before = set(plan["trigger_reasons"])
    after = set(candidate["reasons"])
    if not after <= before:
        return False
    if "INVALID_MONEY_CELL" in plan["trigger_kinds"] and any(
        "MONEY_CELL_IS_NOT_EXACT_INTEGER" in reason
        or reason.startswith("ROW_CELL_ERROR:")
        or reason.startswith("ROW_VALUE_AXIS_INCOMPLETE:")
        for reason in after
    ):
        return False
    if "INVALID_PERCENT_CELL" in plan["trigger_kinds"] and any(
        reason.startswith("ROW_PERCENT_CELL_IS_NOT_EXACT_DECIMAL:") for reason in after
    ):
        return False
    if "UNMATCHED_SOURCE_LABEL" in plan["trigger_kinds"] and any(
        reason.startswith("UNBOUND_VISIBLE_NUMERIC_ROWS:") for reason in after
    ):
        return False
    if "UNSATISFIED_EXACT_EQUATION" in plan["trigger_kinds"] and any(
        reason.startswith("EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:")
        or reason.startswith("NESTED_PARENT_NOT_EXACT_CHILD_SUM:")
        or reason.startswith("VISIBLE_LANE_EQUATION_NOT_EXACT:")
        or reason.startswith("STRUCTURAL_SUBTOTAL_NOT_EXACT:")
        or reason.startswith("VISIBLE_FAMILY_TOTAL_NOT_EXACT_DIRECT_FRONTIER:")
        or reason.startswith("PRESENTATION_NET_ROW_NOT_ONE_EXACT_LANE_EQUATION:")
        for reason in after
    ):
        return False
    if "TABLE_PERIOD_AXIS_INCOMPLETE" in plan["trigger_kinds"] and any(
        reason == "Gemini JSON stacked-period region does not expose exactly two periods"
        or reason.startswith("PERIOD_HAS_NO_DECLARED_ROLE:")
        or "no exact period carrier" in reason
        for reason in after
    ):
        return False
    if "TABLE_EXPLICIT_FAMILY_TITLE_MISSING" in plan["trigger_kinds"] and any(
        reason.startswith("FAMILY_PARENT_NOT_VISIBLE") for reason in after
    ):
        return False
    return True


def _target_evidence(page_json: dict[str, Any], target_ids: list[str]) -> list[dict[str, Any]]:
    evidence = []
    for target_id in target_ids:
        section_id, table_id, row_id = target_id.split(":")
        row = page_json["sections"][int(section_id[1:]) - 1]["tables"][int(table_id[1:]) - 1][
            "rows"
        ][int(row_id[1:]) - 1]
        evidence.append(
            {
                "hierarchy_path_exact": row["hierarchy_path_exact"],
                "label_exact": row["label_exact"],
                "values_exact": row["values_exact"],
            }
        )
    return evidence


def _repair_target_evidence(
    page_json: dict[str, Any], plan: dict[str, Any]
) -> list[dict[str, Any]]:
    if plan.get("repair_scope") not in {"TABLE_PERIOD_AXIS", "TABLE_TITLE_AND_COLUMNS"}:
        return _target_evidence(page_json, plan["target_ids"])
    evidence = []
    for ref in plan.get("target_table_refs", []):
        table = page_json["sections"][int(ref["section_id"][1:]) - 1]["tables"][
            int(ref["table_id"][1:]) - 1
        ]
        evidence.append(
            {
                "columns_header_path_exact": [
                    column["header_path_exact"] for column in table["columns"]
                ],
                "table_title_exact": table["title_exact"],
            }
        )
    return evidence


def _repair_attempt_outcome_v1(*, resolved: bool, stable_source: bool, thinking_level: str) -> str:
    """Keep unchanged evidence retryable until the bounded final source read."""

    if (
        type(resolved) is not bool
        or type(stable_source) is not bool
        or thinking_level not in {"low", "medium", "high"}
    ):
        raise RunGeminiJsonFamilyRegionRepairWorkerV1Error(
            "repair attempt outcome input is invalid"
        )
    if resolved:
        return "RESOLVED"
    if stable_source and thinking_level == "high":
        return "STABLE_SOURCE_EVIDENCE"
    return "RETRYABLE_VALIDATION_FAILURE"


def run(args: argparse.Namespace) -> dict[str, Any]:
    compiled = compile_gemini_json_flat_family_specs_v1(
        _json(args.topology_spec),
        _json(args.evaluation_spec),
        _json(args.schema_binding_spec),
    )
    outcomes = []
    processed_jobs = set()
    while len(processed_jobs) < args.max_jobs:
        pending = pending_gemini_family_region_repair_plans_v1(
            args.results_database, family_run_id=args.family_run_id
        )
        if args.repair_job_id:
            pending = [item for item in pending if item["repair_job_id"] in args.repair_job_id]
        selected = next(
            (item for item in pending if item["repair_job_id"] not in processed_jobs), None
        )
        if selected is None:
            break
        plan = selected["plan"]
        if plan["family_id"] != compiled["topology"]["family_id"]:
            processed_jobs.add(selected["repair_job_id"])
            continue
        # One invocation owns this job through its bounded low -> medium -> high
        # frontier.  Each pass is independent and source-bound.
        while True:
            current = next(
                (
                    item
                    for item in pending_gemini_family_region_repair_plans_v1(
                        args.results_database, family_run_id=selected["family_run_id"]
                    )
                    if item["repair_job_id"] == selected["repair_job_id"]
                ),
                None,
            )
            if current is None:
                break
            thinking_level = current["next_thinking_level"]
            attempt_ordinal = current["attempt_count"] + 1
            try:
                observation = run_region_repair_v1(
                    _repair_args(
                        args,
                        plan=plan,
                        thinking_level=thinking_level,
                        attempt_ordinal=attempt_ordinal,
                    )
                )
                version_id = observation["database_identities"]["page_json_version_id"]
                repaired_page = load_page_json_versions_v1(
                    args.page_database,
                    page_json_version_ids=[version_id],
                )[0]["page_json"]
                base_page = load_page_json_versions_v1(
                    args.page_database,
                    page_json_version_ids=[plan["base_page_json_version_id"]],
                )[0]["page_json"]
                if (
                    compiled.get("engine_format_version")
                    == "GEMINI_JSON_STACKED_PERIOD_ACCOUNTING_FAMILY_V1"
                ):
                    from bctc_ai.evaluation.gemini_json_stacked_period_accounting_family_v1 import (
                        evaluate_gemini_json_stacked_period_family_region_v1,
                    )

                    candidate = evaluate_gemini_json_stacked_period_family_region_v1(
                        page_json=repaired_page,
                        page_json_version_id=version_id,
                        physical_page=plan["physical_page"],
                        table_refs=[
                            (ref["section_id"], ref["table_id"])
                            for ref in plan["component_table_refs"]
                        ],
                        compiled_specs=compiled,
                    )
                else:
                    candidate = evaluate_gemini_json_flat_family_table_v1(
                        page_json=repaired_page,
                        page_json_version_id=version_id,
                        physical_page=plan["physical_page"],
                        section_id=plan["section_id"],
                        table_id=plan["table_id"],
                        compiled_specs=compiled,
                    )
                resolved = _targeted_repair_is_accepted(plan, candidate)
                stable_source = not resolved and _repair_target_evidence(
                    base_page, plan
                ) == _repair_target_evidence(repaired_page, plan)
                # An unchanged low/medium reread is not proof that the source is
                # inconsistent.  A detached sign, dense header, or small glyph can
                # require the wider context and stronger reasoning of the next
                # bounded pass.  Only the final high pass may seal unchanged source
                # evidence; graph/arithmetic validation remains the acceptance gate.
                outcome = _repair_attempt_outcome_v1(
                    resolved=resolved,
                    stable_source=stable_source,
                    thinking_level=thinking_level,
                )
                state = record_gemini_family_region_repair_attempt_v1(
                    args.results_database,
                    repair_job_id=plan["repair_job_id"],
                    thinking_level=thinking_level,
                    outcome=outcome,
                    page_json_version_id=(
                        version_id if outcome in {"RESOLVED", "STABLE_SOURCE_EVIDENCE"} else None
                    ),
                    usage=observation["usage"],
                    reasons=candidate["reasons"],
                )
            except Exception as exc:  # Every failure becomes traceable bounded state.
                state = record_gemini_family_region_repair_attempt_v1(
                    args.results_database,
                    repair_job_id=plan["repair_job_id"],
                    thinking_level=thinking_level,
                    outcome="PROVIDER_OR_VALIDATION_FAILURE",
                    page_json_version_id=None,
                    usage=None,
                    reasons=[f"{type(exc).__name__}:{exc}"],
                )
            outcomes.append(state)
            if state["next_status"] in {"RESOLVED", "ABSTAINED"}:
                break
        processed_jobs.add(selected["repair_job_id"])
    return {
        "attempt_count": len(outcomes),
        "format_version": "GEMINI_JSON_FAMILY_REGION_REPAIR_WORKER_V1",
        "job_count": len(processed_jobs),
        "outcomes": outcomes,
    }


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
