from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.evaluation.reader_outputs_v2 import (
    load_vlm_table_parser_config,
    parse_paddle_vl_page_v2,
    table_roles_to_dict,
)
from bctc_ai.evaluation.structural_fusion_v2 import (
    StructuredReaderRow,
    compare_structural_readers_v2,
    preserve_continuation_boundary_v2,
)
from bctc_ai.evaluation.word_box_rows_v2 import (
    geometry_row_v2_to_dict,
    load_word_box_reconstruction_v2_config,
    parse_ppocrv6_word_box_page_v2,
)
from bctc_ai.mapping.scope import load_scope_policy

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StructuralFusionExperimentError(RuntimeError):
    pass


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {"commit": commit, "dirty": dirty}


def _resolve(relative: str) -> Path:
    path = (PROJECT_ROOT / relative).resolve()
    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise StructuralFusionExperimentError(f"path escapes project root: {relative}") from exc
    return path


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise StructuralFusionExperimentError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise StructuralFusionExperimentError(f"JSON artifact is not an object: {path}")
    return payload


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise StructuralFusionExperimentError("E-0015 config must be version 1")
    if payload.get("experiment_id") != "E-0015":
        raise StructuralFusionExperimentError("unexpected structural-fusion experiment ID")
    if payload.get("dataset_role") != "CALIBRATION":
        raise StructuralFusionExperimentError("E-0015 must remain CALIBRATION")
    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        raise StructuralFusionExperimentError("E-0015 has no document contracts")
    return payload


def _verify_file(identity: dict[str, Any], label: str) -> Path:
    raw_path = identity.get("path")
    expected_hash = identity.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
        raise StructuralFusionExperimentError(f"{label} lacks path/hash identity")
    path = _resolve(raw_path)
    if not path.is_file():
        raise StructuralFusionExperimentError(f"{label} is absent: {path}")
    if sha256_file(path) != expected_hash:
        raise StructuralFusionExperimentError(f"{label} hash drift: {path}")
    size = identity.get("size_bytes")
    if size is not None and path.stat().st_size != size:
        raise StructuralFusionExperimentError(f"{label} size drift: {path}")
    return path


def _result_output(role_b_page: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    outputs = role_b_page.get("outputs")
    if not isinstance(outputs, list):
        raise StructuralFusionExperimentError("Role B page has no output list")
    matches = [
        output
        for output in outputs
        if isinstance(output, dict) and str(output.get("path", "")).endswith("_res.json")
    ]
    if len(matches) != 1:
        raise StructuralFusionExperimentError("Role B page does not have exactly one result JSON")
    return matches[0], _verify_file(matches[0], "Role B result")


def _page_contracts(document: dict[str, Any]) -> list[dict[str, Any]]:
    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        raise StructuralFusionExperimentError("document has no page contracts")
    seen: set[int] = set()
    contracts = []
    for raw in pages:
        if not isinstance(raw, dict):
            raise StructuralFusionExperimentError("page contract is not an object")
        page = raw.get("page")
        statement_type = raw.get("statement_type")
        eligible = raw.get("mapping_eligible")
        reason = raw.get("scope_reason")
        if not isinstance(page, int) or page < 1 or page in seen:
            raise StructuralFusionExperimentError("page contracts contain invalid/duplicate pages")
        if statement_type not in {"CDKT", "KQKD", "LCTT"}:
            raise StructuralFusionExperimentError(f"invalid statement type on page {page}")
        if not isinstance(eligible, bool) or not isinstance(reason, str) or not reason:
            raise StructuralFusionExperimentError(f"invalid scope contract on page {page}")
        seen.add(page)
        contracts.append(raw)
    if [record["page"] for record in contracts] != sorted(seen):
        raise StructuralFusionExperimentError("page contracts must be in document order")
    return contracts


def _verify_contract_against_e0014(
    config_document: dict[str, Any], acquisition_document: dict[str, Any]
) -> None:
    contracts = _page_contracts(config_document)
    page_contract = acquisition_document.get("page_contract")
    if not isinstance(page_contract, dict):
        raise StructuralFusionExperimentError("E-0014 document has no page contract")
    pages = [record["page"] for record in contracts]
    if pages != page_contract.get("selected_pages"):
        raise StructuralFusionExperimentError("E-0015 selected pages drift from E-0014")
    eligible: dict[str, list[int]] = defaultdict(list)
    excluded = []
    for record in contracts:
        if record["mapping_eligible"]:
            eligible[record["statement_type"]].append(record["page"])
        else:
            excluded.append(record["page"])
    if dict(eligible) != page_contract.get("mapping_eligible_pages_by_statement_type"):
        raise StructuralFusionExperimentError("E-0015 eligible page types drift from E-0014")
    if excluded != page_contract.get("off_balance_exclusion_pages"):
        raise StructuralFusionExperimentError("E-0015 exclusion pages drift from E-0014")


def _portable_geometry(record: dict[str, Any]) -> dict[str, Any]:
    evidence = record["geometry"]["visual_cell_evidence"]
    for item in evidence:
        if item is None:
            continue
        path = Path(item["source_image_path"])
        item["source_image_path"] = _relative(path) if path.is_absolute() else path.as_posix()
    return record


def _table_record(table) -> dict[str, Any]:
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
                "row_code": item.row_code,
                "source_grid_row": item.source_grid_row,
                "row": reader_row_to_dict(item.row),
                "warnings": list(item.warnings),
            }
            for item in table.rows
        ],
    }


def _sum_counter(target: Counter, values: dict[str, int]) -> None:
    for key, value in values.items():
        target[key] += int(value)


def _continuation_records(
    config_document: dict[str, Any],
    pages: list[dict[str, Any]],
    page_rows: dict[int, tuple[tuple[StructuredReaderRow, ...], tuple[StructuredReaderRow, ...]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contracts = _page_contracts(config_document)
    contract_by_page = {record["page"]: record for record in contracts}
    configured_edges = config_document.get("continuation_edges")
    if not isinstance(configured_edges, list):
        raise StructuralFusionExperimentError("continuation_edges must be a list")
    edge_records = []
    statement_results = []
    by_statement: dict[str, list[int]] = defaultdict(list)
    for record in contracts:
        if record["mapping_eligible"]:
            by_statement[record["statement_type"]].append(record["page"])
    for edge in configured_edges:
        if not isinstance(edge, dict):
            raise StructuralFusionExperimentError("continuation edge is not an object")
        statement_type = edge.get("statement_type")
        from_page = edge.get("from_page")
        to_page = edge.get("to_page")
        sequence = by_statement.get(str(statement_type), [])
        accepted = (
            isinstance(from_page, int)
            and isinstance(to_page, int)
            and from_page in sequence
            and to_page in sequence
            and sequence.index(to_page) == sequence.index(from_page) + 1
            and contracts.index(contract_by_page[to_page])
            == contracts.index(contract_by_page[from_page]) + 1
        )
        if not accepted:
            raise StructuralFusionExperimentError(f"invalid continuation edge: {edge}")
        b_from, c_from = page_rows[from_page]
        b_to, c_to = page_rows[to_page]
        edge_records.append(
            preserve_continuation_boundary_v2(
                statement_type=statement_type,
                from_page=from_page,
                to_page=to_page,
                role_b_from=b_from,
                role_b_to=b_to,
                role_c_from=c_from,
                role_c_to=c_to,
            )
        )
    page_result_by_page = {record["page"]: record for record in pages}
    for statement_type, statement_pages in by_statement.items():
        if len(statement_pages) < 2:
            continue
        actions: Counter = Counter()
        escalations: Counter = Counter()
        role_b_rows = 0
        role_c_rows = 0
        for page in statement_pages:
            counts = page_result_by_page[page]["comparison"]["counts"]
            _sum_counter(actions, counts["alignment_actions"])
            _sum_counter(escalations, counts["escalations"])
            role_b_rows += counts["role_b_rows"]
            role_c_rows += counts["role_c_rows"]
        statement_results.append(
            {
                "statement_type": statement_type,
                "pages": statement_pages,
                "page_separated_counts": {
                    "role_b_rows": role_b_rows,
                    "role_c_rows": role_c_rows,
                    "alignment_actions": dict(sorted(actions.items())),
                    "escalations": dict(sorted(escalations.items())),
                },
                "page_boundaries_are_hard_alignment_separators": True,
                "automatic_cross_page_row_merge": False,
                "values_or_notes_affect_alignment": False,
                "automatic_confidence_effect": "NONE",
            }
        )
    return edge_records, statement_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare sealed E-0014 Role B/Role C rows using structural fusion v2"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0015-mbb-vcb-structural-fusion.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    git = _git_state()
    if git["dirty"] and not args.allow_dirty:
        raise StructuralFusionExperimentError("refusing formal E-0015 from a dirty worktree")
    output_path = args.output.resolve()
    if output_path.exists():
        raise StructuralFusionExperimentError(f"refusing to overwrite output: {output_path}")
    try:
        output_path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise StructuralFusionExperimentError("output must remain inside the project root") from exc

    config_path = args.config.resolve()
    config = _load_config(config_path)
    upstream_identity = config["upstream"]["reader_acquisition_artifact"]
    acquisition_path = _verify_file(upstream_identity, "E-0014 acquisition artifact")
    acquisition = _load_json(acquisition_path)
    if acquisition.get("experiment_id") != "E-0014":
        raise StructuralFusionExperimentError("upstream artifact is not E-0014")
    role_b_config_path = _resolve(config["upstream"]["role_b_parser_config"])
    role_c_config_path = _resolve(config["upstream"]["role_c_reconstruction_config"])
    scope_path = _resolve(config["upstream"]["scope_policy"])
    role_b_config = load_vlm_table_parser_config(role_b_config_path)
    role_c_config = load_word_box_reconstruction_v2_config(role_c_config_path)
    scope_policy = load_scope_policy(scope_path)

    acquisition_documents = {
        document["key"]: document for document in acquisition.get("documents", [])
    }
    document_results = []
    total_actions: Counter = Counter()
    total_escalations: Counter = Counter()
    totals: Counter = Counter()
    off_balance_eligible = 0
    for config_document in config["documents"]:
        key = config_document.get("key")
        acquisition_document = acquisition_documents.get(key)
        if not isinstance(key, str) or not isinstance(acquisition_document, dict):
            raise StructuralFusionExperimentError(f"missing E-0014 document: {key}")
        _verify_contract_against_e0014(config_document, acquisition_document)
        source_path = _verify_file(acquisition_document["source"], f"{key} source")
        role_b_seal_path = _verify_file(
            acquisition_document["role_b"]["seal"], f"{key} Role B seal"
        )
        role_c_seal_path = _verify_file(
            acquisition_document["role_c"]["seal"], f"{key} Role C seal"
        )
        role_b_seal = _load_json(role_b_seal_path)
        role_c_seal = _load_json(role_c_seal_path)
        if (
            role_b_seal.get("state") != "OCR_COMPLETE"
            or role_c_seal.get("state") != "GEOMETRY_OCR_COMPLETE"
        ):
            raise StructuralFusionExperimentError(f"{key} reader seal is incomplete")
        if role_b_seal.get("source_sha256") != acquisition_document["source"]["sha256"]:
            raise StructuralFusionExperimentError(f"{key} Role B source drift")
        if role_c_seal.get("source_sha256") != acquisition_document["source"]["sha256"]:
            raise StructuralFusionExperimentError(f"{key} Role C source drift")
        if role_c_seal.get("upstream_role_b_seal", {}).get("sha256") != sha256_file(
            role_b_seal_path
        ):
            raise StructuralFusionExperimentError(f"{key} Role C/Role B seal link drift")
        b_pages = {record["page"]: record for record in role_b_seal["pages"]}
        c_pages = {record["page"]: record for record in role_c_seal["pages"]}
        page_results = []
        structured_by_page = {}
        for contract in _page_contracts(config_document):
            page = contract["page"]
            if page not in b_pages or page not in c_pages:
                raise StructuralFusionExperimentError(f"{key} page {page} is absent from a seal")
            b_identity, b_result_path = _result_output(b_pages[page])
            c_identity = c_pages[page]["ocr_result"]
            c_result_path = _verify_file(c_identity, f"{key} page {page} Role C result")
            b_render = _verify_file(b_pages[page]["render"], f"{key} page {page} Role B render")
            c_render = _verify_file(c_pages[page]["render"], f"{key} page {page} Role C render")
            if b_render != c_render:
                raise StructuralFusionExperimentError(f"{key} page {page} reader render mismatch")
            page_tag = f"{key.casefold()}-page-{page:04d}"
            parsed_b = parse_paddle_vl_page_v2(
                b_result_path,
                role_b_config,
                page_tag=page_tag,
            )
            parsed_c = parse_ppocrv6_word_box_page_v2(
                c_result_path,
                role_c_config,
                page_tag=page_tag,
                source_image_path=b_render,
            )
            structured_b = tuple(
                StructuredReaderRow(item.row, item.row_code)
                for table in parsed_b.tables
                for item in table.rows
            )
            structured_c = tuple(
                StructuredReaderRow(item.row, item.row_code) for item in parsed_c.rows
            )
            structured_by_page[page] = (structured_b, structured_c)
            comparison = compare_structural_readers_v2(
                structured_b,
                structured_c,
                statement_type=contract["statement_type"],
                page_mapping_eligible=contract["mapping_eligible"],
                upstream_scope_reason=contract["scope_reason"],
                scope_policy=scope_policy,
                role_b_context_text=parsed_b.context_text,
            )
            _sum_counter(total_actions, comparison["counts"]["alignment_actions"])
            _sum_counter(total_escalations, comparison["counts"]["escalations"])
            totals["page_count"] += 1
            totals["role_b_table_blocks"] += len(parsed_b.tables)
            totals["role_b_unresolved_table_blocks"] += parsed_b.unresolved_table_count
            totals["role_b_header_only_blocks"] += sum(
                table.status == "HEADER_ONLY" for table in parsed_b.tables
            )
            totals["role_b_rows"] += len(structured_b)
            totals["role_c_rows"] += len(structured_c)
            totals["role_c_two_axis_pages"] += len(parsed_c.axes) == 2
            totals["role_c_index_band_pages"] += parsed_c.index_band is not None
            totals["role_c_unassigned_numeric_lines"] += len(
                parsed_c.unassigned_numeric_line_indices
            )
            totals["role_c_trailing_context_rows"] += len(parsed_c.trailing_context_rows)
            totals["role_c_pixel_dash_cells"] += sum(
                evidence is not None
                for row in parsed_c.rows
                for evidence in row.visual_cell_evidence
            )
            totals["role_b_invalid_cells"] += comparison["counts"]["role_b_invalid_cells"]
            totals["role_c_invalid_cells"] += comparison["counts"]["role_c_invalid_cells"]
            totals["paired_cells"] += comparison["counts"]["paired_cells"]
            totals["exact_paired_cells"] += comparison["counts"]["exact_paired_cells"]
            if not contract["mapping_eligible"]:
                off_balance_eligible += comparison["counts"]["mapping_eligible_alignment_units"]
            page_results.append(
                {
                    "page": page,
                    "statement_type": contract["statement_type"],
                    "mapping_eligible": contract["mapping_eligible"],
                    "scope_reason": contract["scope_reason"],
                    "role_b": {
                        "result": b_identity,
                        "table_block_count": len(parsed_b.tables),
                        "unresolved_table_count": parsed_b.unresolved_table_count,
                        "context_text": parsed_b.context_text,
                        "tables": [_table_record(table) for table in parsed_b.tables],
                    },
                    "role_c": {
                        "result": c_identity,
                        "axes": [
                            {
                                "axis_id": axis.axis_id,
                                "raw_header": axis.raw_header,
                                "right_edge": axis.right_edge,
                                "header_line_index": axis.header_line_index,
                            }
                            for axis in parsed_c.axes
                        ],
                        "note_right_edge": parsed_c.note_right_edge,
                        "index_band": None
                        if parsed_c.index_band is None
                        else {
                            "right_edge": parsed_c.index_band.right_edge,
                            "supporting_line_indices": list(
                                parsed_c.index_band.supporting_line_indices
                            ),
                            "header_detected": parsed_c.index_band.header_detected,
                        },
                        "table_bbox": list(parsed_c.table_bbox),
                        "line_height": parsed_c.line_height,
                        "unassigned_numeric_line_indices": list(
                            parsed_c.unassigned_numeric_line_indices
                        ),
                        "excluded_after_table_line_indices": list(
                            parsed_c.excluded_after_table_line_indices
                        ),
                        "rows": [
                            _portable_geometry(geometry_row_v2_to_dict(row))
                            for row in parsed_c.rows
                        ],
                        "trailing_context_rows": [
                            _portable_geometry(geometry_row_v2_to_dict(row))
                            for row in parsed_c.trailing_context_rows
                        ],
                    },
                    "comparison": comparison,
                }
            )
        edges, statement_results = _continuation_records(
            config_document,
            page_results,
            structured_by_page,
        )
        document_results.append(
            {
                "key": key,
                "source": {
                    "path": _relative(source_path),
                    "sha256": sha256_file(source_path),
                    "size_bytes": source_path.stat().st_size,
                },
                "reader_seals": {
                    "role_b": {
                        "path": _relative(role_b_seal_path),
                        "sha256": sha256_file(role_b_seal_path),
                    },
                    "role_c": {
                        "path": _relative(role_c_seal_path),
                        "sha256": sha256_file(role_c_seal_path),
                    },
                },
                "continuation_edges": edges,
                "statement_level_comparisons": statement_results,
                "pages": page_results,
            }
        )

    acceptance = config["acceptance"]
    observed = {
        "document_count": len(document_results),
        "page_count": totals["page_count"],
        "role_b_table_block_count": totals["role_b_table_blocks"],
        "role_b_unresolved_table_blocks": totals["role_b_unresolved_table_blocks"],
        "role_c_two_axis_pages": totals["role_c_two_axis_pages"],
        "off_balance_mapping_eligible_alignment_units": off_balance_eligible,
        "report_norm_ids_proposed_or_added": 0,
    }
    required = {
        "document_count": acceptance["required_document_count"],
        "page_count": acceptance["required_page_count"],
        "role_b_table_block_count": acceptance["required_role_b_table_block_count"],
        "role_b_unresolved_table_blocks": acceptance["required_role_b_unresolved_table_blocks"],
        "role_c_two_axis_pages": acceptance["required_role_c_two_axis_pages"],
        "off_balance_mapping_eligible_alignment_units": acceptance[
            "required_off_balance_mapping_eligible_alignment_units"
        ],
        "report_norm_ids_proposed_or_added": acceptance[
            "required_report_norm_ids_proposed_or_added"
        ],
    }
    acceptance_passed = observed == required
    safety = config["safety"]
    if any(safety.values()):
        raise StructuralFusionExperimentError("E-0015 safety permissions must all be false")
    implementation_paths = [
        Path("scripts/experiments/compare_e0015_structural_fusion.py"),
        Path("src/bctc_ai/evaluation/financial_cells_v2.py"),
        Path("src/bctc_ai/evaluation/reader_outputs_v2.py"),
        Path("src/bctc_ai/evaluation/structural_fusion_v2.py"),
        Path("src/bctc_ai/evaluation/word_box_rows_v2.py"),
        Path("src/bctc_ai/evaluation/reader_outputs.py"),
        Path("src/bctc_ai/evaluation/word_box_rows.py"),
        Path("src/bctc_ai/validation/reader_agreement.py"),
        Path("src/bctc_ai/mapping/scope.py"),
    ]
    payload = {
        "format_version": 1,
        "experiment_id": "E-0015",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_role": "CALIBRATION",
        "design": config["design"],
        "status": (
            "PASS_STRUCTURAL_COMPARISON_WITH_RETAINED_DISAGREEMENTS_NO_ACCURACY_CLAIM"
            if acceptance_passed and not git["dirty"]
            else "DEVELOPMENT_SMOKE_OR_FAILED_CONTRACT"
        ),
        "code": git,
        "configuration": {
            "experiment": {"path": _relative(config_path), "sha256": sha256_file(config_path)},
            "role_b_parser": {
                "path": _relative(role_b_config_path),
                "sha256": sha256_file(role_b_config_path),
            },
            "role_c_reconstruction": {
                "path": _relative(role_c_config_path),
                "sha256": sha256_file(role_c_config_path),
            },
            "role_c_base_reconstruction": {
                "path": _relative(role_c_config.base_path),
                "sha256": sha256_file(role_c_config.base_path),
            },
            "scope_policy": {"path": _relative(scope_path), "sha256": sha256_file(scope_path)},
        },
        "upstream": {
            "reader_acquisition_artifact": upstream_identity,
            "reader_acquisition_status": acquisition["status"],
        },
        "algorithm_files_sha256": {
            path.as_posix(): sha256_file(PROJECT_ROOT / path) for path in implementation_paths
        },
        "policy": {
            "alignment_features": ["DOCUMENT_ORDER", "NORMALIZED_LABEL_TEXT"],
            "values_notes_codes_history_schema_arithmetic_affect_alignment": False,
            "page_scope_applied_before_mapping": True,
            "reader_agreement_is_truth": False,
            "automatic_confidence_effect": "NONE",
        },
        "metrics": {
            **dict(sorted(totals.items())),
            "alignment_actions": dict(sorted(total_actions.items())),
            "escalations": dict(sorted(total_escalations.items())),
            "off_balance_mapping_eligible_alignment_units": off_balance_eligible,
        },
        "acceptance": {
            "configured": acceptance,
            "observed": observed,
            "contract_exact": acceptance_passed,
            "accuracy_threshold_evaluated": False,
            "human_gold_evaluated": False,
            "production_accuracy_approved": False,
        },
        "safety": {
            "role_a_or_searchable_reference_used": False,
            "historical_reference_invoked": False,
            "arithmetic_value_generation_invoked": False,
            "schema_mapping_attempted": False,
            "cash_flow_schema_branch_assignment_attempted": False,
            "automatic_truth_promotion": False,
            "automatic_schema_promotion": False,
            "automatic_pdf_confidence_promotion": False,
            "ytd_derivation_invoked": False,
        },
        "report_norm_id": {
            "ids_proposed_or_added": 0,
            "collision_check_invoked": False,
            "reason": "No schema mapping or ReportNormId proposal occurs in E-0015.",
        },
        "software_or_model_change": False,
        "documents": document_results,
        "claim_boundary": (
            "This post-inspection calibration compares two machine readers and measures "
            "structural coverage/agreement only. It is not human-gold row/cell accuracy, "
            "schema mapping, holdout evidence, confidence calibration, or production approval."
        ),
    }
    atomic_write_json(output_path, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "output": _relative(output_path),
                "metrics": payload["metrics"],
                "acceptance": payload["acceptance"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if acceptance_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
