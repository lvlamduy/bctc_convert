"""Run one notes family over an authenticated corpus.

Retrieval (one SQL query) -> load candidate tables (four SQL queries) ->
per-table evaluation by the family's shape -> cross-table write-key check ->
per-document coverage. A write key is (document, scope, concept, axis,
member, classification basis, period); two accepted cells on one key are both
held, whatever their values (no first/last wins).
"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from bctc_ai.notes.config_v1 import NotesConfig
from bctc_ai.notes.kernel_v1 import (
    KERNEL_VERSION,
    DocumentContext,
    NotesSource,
    assemble_continuations_v1,
    continuation_neighbors_v1,
    page_texts_v1,
    stable_json_sha256,
    table_context_v1,
)
from functools import partial

from bctc_ai.notes.concept_list_shape_v1 import evaluate_concept_table_v1
from bctc_ai.notes.coordinate_shape_v1 import evaluate_coordinate_table_v1
from bctc_ai.notes.list_shape_v1 import TableEvaluation, evaluate_table_v1
from bctc_ai.notes.source_bridge_v1 import original_cell_v1

SHAPES = {"LIST_BY_AXIS": evaluate_table_v1, "COORDINATE_LIST": evaluate_coordinate_table_v1,
          "CONCEPT_LIST": evaluate_concept_table_v1}


@dataclass
class FamilyRun:
    family: str
    evaluations: list[Any] = field(default_factory=list)
    cells: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[int, dict[str, Any]] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


def run_family_v1(
    family_name: str, config: NotesConfig, source: NotesSource, contexts: dict[int, DocumentContext],
    *, document_ordinals: set[int] | None = None,
) -> FamilyRun:
    family = config.families[family_name]
    evaluate = SHAPES[family.shape]
    if family.shape == "COORDINATE_LIST":
        evaluate = partial(evaluate, axes=[config.axes[name] for name in family.raw["axes"]])
    started = time.perf_counter()
    candidates = source.candidate_tables(family.retrieval_patterns)
    if document_ordinals is not None:
        candidates = {k: v for k, v in candidates.items() if source.page_of[k[0]][0] in document_ordinals}
    t_retrieve = time.perf_counter()
    tables = source.load_tables(set(candidates) | continuation_neighbors_v1(source, candidates))
    tables, joins = assemble_continuations_v1(source, tables)
    wanted = set(candidates)
    tables = [t for t in tables
              if any((f["page_json_version_id"], f["section_id"], f["table_id"]) in wanted for f in (t.fragments or [t.locator()]))]
    t_load = time.perf_counter()
    outline = source.outline()
    run = FamilyRun(family_name)
    corpus_documents = {document.ordinal: document for document in source.corpus.documents}
    corpus_identity = source.corpus.identity()
    for table in tables:
        # PRIMARY context only by exact source + corpus identity, never by ordinal alone.
        document = contexts.get(table.document_ordinal)
        mismatch = ("PRIMARY_CONTEXT_MISSING" if document is None
                    else document.identity_mismatch(corpus_documents[table.document_ordinal], corpus_identity))
        # Every source fragment must be proven against its ORIGINAL page before any reading.
        mismatch = mismatch or table.bridge_failure()
        if mismatch:
            run.evaluations.append(TableEvaluation(table, "REJECTED", [mismatch]))
            continue
        context = table_context_v1(table, outline.get(table.document_ordinal, []))
        table.section_table_count = sum(1 for e in outline.get(table.document_ordinal, [])
                                        if e["table_id"] is not None and e["version"] == table.page_json_version_id
                                        and e["section_id"] == table.section_id)
        for evaluation in evaluate(table, family, document, context, page_texts_v1(source, table)):
            run.evaluations.append(evaluation)
            for cell in evaluation.cells:
                cell["original_cell"] = original_cell_v1(evaluation.table, cell["locator"])
                if cell["original_cell"] is None and cell["acceptance"] != "HOLD":
                    cell["acceptance"] = "HOLD"
                    cell["hold_reasons"].append("SOURCE_BRIDGE_CELL_NOT_BIJECTIVE")
                cell["write_key"] = [cell["document_plan_id"], cell["scope"], cell["concept"], cell["axis"], cell["member"],
                                     cell["classification_basis"], cell["period_key"]]
                run.cells.append(cell)
    _assign_legacy_ids(run.cells, config)
    run.joins = joins
    hold_write_key_collisions_v1(run.cells)
    ordinals = sorted(document_ordinals if document_ordinals is not None else contexts)
    run.coverage = document_coverage_v1(run.evaluations, run.cells, ordinals, family.shape)
    run.metrics = {
        "kernel_version": KERNEL_VERSION, "family_sha256": family.sha256, "config_pins": config.pins,
        "candidate_tables": len(candidates), "loaded_tables": len(tables),
        "seconds": {"retrieve": round(t_retrieve - started, 3), "load": round(t_load - t_retrieve, 3),
                    "evaluate": round(time.perf_counter() - t_load, 3)},
        "source": source.metrics.to_dict(),
        "cells_sha256": stable_json_sha256(run.cells),
    }
    return run


COVERAGE_FORMAT = "NOTES_COVERAGE_STATUS_V2"
_ONLY_LINES = re.compile(r"ONLY_[0-9]+_LINES")


def document_coverage_v1(evaluations: list[Any], cells: list[dict[str, Any]], ordinals: list[int],
                         shape: str) -> dict[int, dict[str, Any]]:
    """Per-document coverage status (metadata only; cells, roles and thresholds are not touched).

    FOUND - at least one EVALUATED table (precedence, unchanged meaning).
    OBSERVED_UNRESOLVED (Codex 0157) - no EVALUATED table, but a CONCEPT_LIST table that passed the page,
      notes-start and owner checks, has an explicitly resolved printed subject, and was REJECTED with exactly
      one reason ONLY_<n>_LINES: the note was observed, its lines are not (yet) provable.
    NOT_OBSERVED_AFTER_FULL_RETRIEVAL - everything else (incl. NO_TITLE weak evidence, a foreign owner,
      primary-statement pages, pages before the notes, source-bridge or PRIMARY-context rejections).
    Every rejected table keeps its own reasons in dispositions; this only adds an auditable status split.
    """

    coverage: dict[int, dict[str, Any]] = {}
    for ordinal in ordinals:
        own = [e for e in evaluations if e.table.document_ordinal == ordinal]
        evaluated = [e for e in own if e.status == "EVALUATED"]
        unresolved = [e for e in own if shape == "CONCEPT_LIST" and e.status == "REJECTED" and e.subject is not None
                      and len(e.reasons) == 1 and isinstance(e.reasons[0], str) and _ONLY_LINES.fullmatch(e.reasons[0])]
        subjects = Counter(e.subject for e in evaluated)
        accepted = Counter(c["concept"] for c in cells if c["document_ordinal"] == ordinal and c["acceptance"] == "ACCEPTED")
        status = "FOUND" if evaluated else ("OBSERVED_UNRESOLVED" if unresolved else "NOT_OBSERVED_AFTER_FULL_RETRIEVAL")
        entry = {"coverage_format": COVERAGE_FORMAT, "evaluated_tables": len(evaluated),
                 "subjects": {str(k): v for k, v in subjects.items()}, "accepted_cells_by_concept": dict(accepted),
                 "status": status}
        if status == "OBSERVED_UNRESOLVED":
            entry["unresolved_tables"] = [{"locator": e.table.locator(), "fragments": list(e.table.fragments),
                                           "subject": e.subject, "reasons": list(e.reasons)} for e in unresolved]
            entry["unresolved_row_reasons"] = dict(Counter(
                r.reason for e in unresolved for r in e.roles if r.disposition in ("SOURCE_ONLY", "AMBIGUOUS")))
        coverage[ordinal] = entry
    return coverage


def hold_write_key_collisions_v1(cells: list[dict[str, Any]]) -> None:
    """Hold every non-held cell sharing a write key with another (Codex 0123).

    Equal amounts do not prove that two source occurrences have one population or meaning, and no
    table order may choose a winner: every occurrence is held, keeping its own evidence and the
    locators of the others it collided with.
    """

    by_key = defaultdict(list)
    for cell in cells:
        if cell["acceptance"] != "HOLD" and None not in cell["write_key"]:
            by_key[tuple(cell["write_key"])].append(cell)
    for colliding in by_key.values():
        if len(colliding) < 2:
            continue
        identical = len({(c["value"], c["unit"], c["observation_state"]) for c in colliding}) == 1
        reason = "WRITE_KEY_COLLISION_EQUAL_VALUES" if identical else "WRITE_KEY_COLLISION_DIFFERENT_VALUES"
        for cell in colliding:
            cell["acceptance"] = "HOLD"
            cell["hold_reasons"].append(reason)
            cell["collides_with"] = [other["locator"] for other in colliding if other is not cell]


def dispositions_v1(run: FamilyRun) -> list[dict[str, Any]]:
    """Every retrieved table of a family run with its status/reasons and, when evaluated, every row's disposition.

    The denominator artifact: rejected tables, unread (SOURCE_ONLY), ambiguous and
    heading rows stay visible with their reason; nothing is silently dropped.
    """

    out = []
    for evaluation in run.evaluations:
        table = evaluation.table
        out.append({
            "family": run.family, "status": evaluation.status, "reasons": list(evaluation.reasons),
            "locator": table.locator(), "fragments": list(table.fragments), "subject": evaluation.subject,
            "source_bridges": list(table.fragment_bridges) if table.fragments else [table.bridge],
            "rows": [{"row_id": table.rows[r.row_index].row_id, "label_exact": table.rows[r.row_index].label,
                      "parent_row_id": table.rows[r.row_index].parent_row_id,
                      "line": getattr(r, "role", None) or getattr(r, "coordinate", None), "disposition": r.disposition,
                      "reason": r.reason, "candidates": list(getattr(r, "candidates", None) or [])} for r in evaluation.roles],
            "lanes": [{"column_id": lane.column.column_id, "header": lane.column.header_text, "period_key": lane.period_key,
                       "period_basis": lane.period_basis, "candidates": list(getattr(lane, "candidates", []) or []),
                       "unit": lane.unit, "reasons": list(lane.reasons)} for lane in evaluation.lanes],
            "equations": [{k: v for k, v in e.items()} for e in evaluation.equations],
        })
    return out


def summarize_v1(run: FamilyRun) -> dict[str, Any]:
    acceptance = Counter((c["concept"], c["acceptance"]) for c in run.cells)
    reasons = Counter(r.split(":")[0] for c in run.cells for r in c["hold_reasons"])
    statuses = Counter((e.status, tuple(e.reasons)) for e in run.evaluations)
    equations = Counter((e.get("name") or "PARENT_EQUALS_CHILDREN", e["status"]) for ev in run.evaluations for e in ev.equations)
    corroboration = Counter(c.get("status") for ev in run.evaluations for c in ev.corroboration)
    coverage = Counter(v["status"] for v in run.coverage.values())
    loans_docs = sum(1 for v in run.coverage.values() if v["accepted_cells_by_concept"].get("LOANS_TO_CUSTOMERS"))
    return {
        "acceptance": {f"{k[0]}|{k[1]}": v for k, v in sorted(acceptance.items(), key=str)},
        "hold_reasons": dict(reasons.most_common()),
        "table_status": {f"{k[0]}|{','.join(k[1])}": v for k, v in statuses.most_common()},
        "equations": {f"{k[0]}|{k[1]}": v for k, v in sorted(equations.items())},
        "primary_corroboration": dict(corroboration),
        "coverage": dict(coverage),
        "documents_with_accepted_loans": loans_docs,
        "metrics": run.metrics,
    }


def _assign_legacy_ids(cells: list[dict[str, Any]], config: NotesConfig) -> None:
    """Legacy ReportNormId for each cell from the crosswalk.

    A member list in the crosswalk is a preference order inside one table lane
    (e.g. 746 = GRAND_TOTAL when printed, else TOTAL_FIVE_GROUPS). A document
    printing the same breakdown under two classification bases (e.g. "theo
    TT31/2024" and the bank's own) gets legacy IDs only for AS_PRESENTED; a
    single basis maps whatever its label.
    """

    bases = defaultdict(set)
    lanes = defaultdict(set)
    for cell in cells:
        bases[(cell["document_ordinal"], cell["concept"], cell["axis"])].add(cell["classification_basis"])
        locator = cell["locator"]
        lanes[(locator["page_json_version_id"], locator["section_id"], locator["table_id"], locator["column_id"])].add(cell["member"])
    for cell in cells:
        cell["report_norm_id"] = None
        if len(bases[(cell["document_ordinal"], cell["concept"], cell["axis"])]) > 1 and cell["classification_basis"] != "AS_PRESENTED":
            continue
        locator = cell["locator"]
        present = lanes[(locator["page_json_version_id"], locator["section_id"], locator["table_id"], locator["column_id"])]
        for (concept, axis, members), rnid in config.crosswalk.items():
            if concept == cell["concept"] and axis == cell["axis"] and cell["member"] in members:
                if next((m for m in members if m in present), None) == cell["member"]:
                    cell["report_norm_id"] = rnid
