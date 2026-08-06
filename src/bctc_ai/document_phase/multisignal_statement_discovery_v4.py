from __future__ import annotations

import copy
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.document_phase import multisignal_statement_discovery as v3
from bctc_ai.document_phase.statement_locator import (
    OCRPage,
    StatementLocatorError,
    StatementPageType,
    StatementScope,
    detect_cash_flow_method,
)

_MAIN_TYPES = (
    StatementPageType.CDKT,
    StatementPageType.KQKD,
    StatementPageType.LCTT,
)
_TARGET_TYPES = (*_MAIN_TYPES, StatementPageType.TM)
_GROUP_ORDER = {
    "HEADER_IDENTITY": 0,
    "PERIOD_AXIS": 1,
    "REPORTING_PERIOD": 1,
    "UNIT": 2,
    "ACCOUNTING_ROWS": 3,
    "NOTES_ANCHORS": 3,
    "NUMERIC_GEOMETRY": 4,
    "NOTES_STRUCTURE": 4,
    "OFF_BALANCE_SCOPE": 5,
    "CONTINUATION": 6,
}


def load_multisignal_statement_config_v4(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StatementLocatorError(f"cannot load statement-discovery v4 config: {path}") from exc
    if not isinstance(payload, dict):
        raise StatementLocatorError("statement-discovery v4 config must be a mapping")
    identities = {
        "version": 4,
        "policy": "MULTI_LINE_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V4",
        "change_scope": "ACCOUNTING_ROW_ANCHOR_SCORER_ONLY",
    }
    if any(payload.get(key) != value for key, value in identities.items()):
        raise StatementLocatorError("statement-discovery v4 identity/change scope drifted")
    base_name = payload.get("base_policy_config")
    if not isinstance(base_name, str) or Path(base_name).name != base_name:
        raise StatementLocatorError("statement-discovery v4 base config path is invalid")
    base_path = (path.parent / base_name).resolve()
    if not base_path.is_file() or base_path.parent != path.parent.resolve():
        raise StatementLocatorError("statement-discovery v4 base config is absent or escapes")
    if sha256_file(base_path) != payload.get("base_policy_config_sha256"):
        raise StatementLocatorError("statement-discovery v4 base config hash drifted")

    matcher = payload.get("ordered_anchor_matching")
    expected_matcher_identity = {
        "policy": "FULL_LINE_OR_BOUNDED_CONTIGUOUS_ORDERED_TOKEN_WINDOW",
        "apply_to": "ACCOUNTING_ROWS_ONLY",
        "preserve_v3_matches": True,
        "require_contiguous_token_order": True,
    }
    if not isinstance(matcher, dict) or any(
        matcher.get(key) != value for key, value in expected_matcher_identity.items()
    ):
        raise StatementLocatorError("statement-discovery v4 matcher identity drifted")
    minimum_anchor_tokens = matcher.get("minimum_anchor_tokens")
    maximum_source_tokens = matcher.get("maximum_source_tokens")
    maximum_delta = matcher.get("maximum_token_count_delta")
    minimum_similarity = matcher.get("minimum_window_similarity")
    if (
        isinstance(minimum_anchor_tokens, bool)
        or not isinstance(minimum_anchor_tokens, int)
        or minimum_anchor_tokens < 4
        or isinstance(maximum_source_tokens, bool)
        or not isinstance(maximum_source_tokens, int)
        or maximum_source_tokens < minimum_anchor_tokens
        or isinstance(maximum_delta, bool)
        or not isinstance(maximum_delta, int)
        or not 0 <= maximum_delta <= 2
        or isinstance(minimum_similarity, bool)
        or not isinstance(minimum_similarity, (int, float))
        or not 0.75 <= float(minimum_similarity) <= 1.0
    ):
        raise StatementLocatorError("statement-discovery v4 matcher bounds are invalid")

    config = copy.deepcopy(v3.load_multisignal_statement_config(base_path))
    config["version"] = 4
    config["policy"] = payload["policy"]
    config["change_scope"] = payload["change_scope"]
    config["base_policy_config"] = base_name
    config["base_policy_config_sha256"] = payload["base_policy_config_sha256"]
    config["ordered_anchor_matching"] = copy.deepcopy(matcher)
    return config


def bounded_ordered_anchor_similarity(
    source_key: str,
    anchor_key: str,
    policy: dict[str, Any],
) -> float:
    """Score an anchor against a bounded contiguous token window.

    The V3 whole-line/token-bounded score is always retained. The window path
    is deliberately unavailable to short anchors and very long prose lines.
    """

    baseline = v3._similarity(source_key, anchor_key)
    source_tokens = source_key.split()
    anchor_tokens = anchor_key.split()
    minimum_anchor_tokens = int(policy["minimum_anchor_tokens"])
    if (
        baseline >= 1.0
        or len(anchor_tokens) < minimum_anchor_tokens
        or len(source_tokens) < minimum_anchor_tokens
        or len(source_tokens) > int(policy["maximum_source_tokens"])
    ):
        return baseline

    delta = int(policy["maximum_token_count_delta"])
    best_window = 0.0
    minimum_size = max(minimum_anchor_tokens, len(anchor_tokens) - delta)
    maximum_size = min(len(source_tokens), len(anchor_tokens) + delta)
    for size in range(minimum_size, maximum_size + 1):
        for start in range(0, len(source_tokens) - size + 1):
            candidate = " ".join(source_tokens[start : start + size])
            best_window = max(best_window, ratio(candidate, anchor_key) / 100.0)
    if best_window < float(policy["minimum_window_similarity"]):
        return baseline
    return max(baseline, best_window)


def _bounded_anchor_proposals(
    windows: tuple[v3.TextWindow, ...],
    raw_anchors: list[str],
    minimum: float,
    policy: dict[str, Any],
) -> tuple[v3.AnchorHit, ...]:
    proposals = []
    for raw_anchor in raw_anchors:
        anchor = retrieval_key(str(raw_anchor))
        for window in windows:
            similarity = bounded_ordered_anchor_similarity(window.key, anchor, policy)
            if similarity >= minimum:
                proposals.append(
                    v3.AnchorHit(
                        anchor=str(raw_anchor),
                        source=window.source,
                        line_indices=window.line_indices,
                        text=window.text,
                        bbox=window.bbox,
                        similarity=round(similarity, 6),
                    )
                )
    return tuple(
        sorted(
            proposals,
            key=lambda item: (
                -item.similarity,
                item.anchor,
                item.source,
                item.line_indices,
            ),
        )
    )


def _extend_preserving_v3_hits(
    baseline: tuple[v3.AnchorHit, ...],
    proposals: tuple[v3.AnchorHit, ...],
) -> tuple[v3.AnchorHit, ...]:
    selected = list(baseline)
    used_anchors = {item.anchor for item in selected}
    used_line_indices: dict[str, set[int]] = {}
    used_vertical_intervals = []
    for item in selected:
        used_line_indices.setdefault(item.source, set()).update(item.line_indices)
        used_vertical_intervals.append((item.bbox[1], item.bbox[3]))
    for proposal in proposals:
        source_indices = used_line_indices.setdefault(proposal.source, set())
        overlaps_source_lines = bool(source_indices.intersection(proposal.line_indices))
        proposal_height = max(1.0, proposal.bbox[3] - proposal.bbox[1])
        overlaps_spatially = any(
            max(0.0, min(proposal.bbox[3], y1) - max(proposal.bbox[1], y0))
            / min(proposal_height, max(1.0, y1 - y0))
            >= 0.50
            for y0, y1 in used_vertical_intervals
        )
        if proposal.anchor in used_anchors or overlaps_source_lines or overlaps_spatially:
            continue
        selected.append(proposal)
        used_anchors.add(proposal.anchor)
        source_indices.update(proposal.line_indices)
        used_vertical_intervals.append((proposal.bbox[1], proposal.bbox[3]))
    return tuple(sorted(selected, key=lambda item: (item.line_indices, item.anchor, item.source)))


def _candidate_with_extended_hits(
    record: v3.PageSignalRecord,
    candidate: v3.PageTypeCandidate,
    hits: tuple[v3.AnchorHit, ...],
    config: dict[str, Any],
) -> v3.PageTypeCandidate:
    minimum_hits = int(config["accounting_rows"]["min_distinct_hits"])
    accounting_pass = len(hits) >= minimum_hits
    groups = list(candidate.independent_signal_groups)
    group = "NOTES_ANCHORS" if candidate.page_type is StatementPageType.TM else "ACCOUNTING_ROWS"
    score = candidate.score
    if accounting_pass and group not in groups:
        groups.append(group)
        groups.sort(key=lambda item: (_GROUP_ORDER.get(item, 99), item))
        score += float(config["signal_weights"]["accounting_rows"])

    header_pass = record.header_candidate_type is candidate.page_type and not record.header_conflict
    acceptance = config["acceptance"]
    if candidate.page_type is StatementPageType.TM:
        gate = (
            header_pass
            and accounting_pass
            and record.notes_structure
            and len(groups) >= int(acceptance["notes_min_independent_groups"])
        )
    else:
        row_gate = accounting_pass or (
            candidate.page_type is StatementPageType.CDKT
            and candidate.scope is StatementScope.OFF_BALANCE_SHEET
        )
        gate = (
            header_pass
            and row_gate
            and record.numeric_geometry.passes
            and len(groups) >= int(acceptance["main_min_independent_groups"])
        )
    locally_accepted = (
        gate
        and not record.header_conflict
        and not record.audit_suppression
        and not record.toc_suppression
        and score >= float(acceptance["min_local_score"])
    )
    return replace(
        candidate,
        score=round(score, 6),
        independent_signal_groups=tuple(groups),
        accounting_hits=hits,
        locally_accepted=locally_accepted,
    )


def _extend_accounting_evidence(
    geometry_pages: tuple[OCRPage, ...],
    semantic_by_page: dict[int, OCRPage],
    records: tuple[v3.PageSignalRecord, ...],
    config: dict[str, Any],
) -> tuple[tuple[v3.PageSignalRecord, ...], list[dict[str, Any]]]:
    matcher = config["ordered_anchor_matching"]
    accounting = config["accounting_rows"]
    minimum = float(accounting["min_similarity"])
    updated_records = []
    diagnostics = []
    for geometry_page, record in zip(geometry_pages, records, strict=True):
        label_windows = v3._semantic_windows(
            geometry_page,
            semantic_by_page.get(geometry_page.page),
            config,
            header_only=False,
        )
        candidates = []
        page_diagnostics = []
        for candidate in record.candidates:
            proposals = _bounded_anchor_proposals(
                label_windows,
                accounting["anchors"][candidate.page_type.value],
                minimum,
                matcher,
            )
            hits = _extend_preserving_v3_hits(candidate.accounting_hits, proposals)
            baseline_anchors = {item.anchor for item in candidate.accounting_hits}
            added = [item for item in hits if item.anchor not in baseline_anchors]
            candidates.append(_candidate_with_extended_hits(record, candidate, hits, config))
            if added:
                page_diagnostics.append(
                    {
                        "statement_type": candidate.page_type.value,
                        "baseline_hit_count": len(candidate.accounting_hits),
                        "extended_hit_count": len(hits),
                        "added_hits": [asdict(item) for item in added],
                    }
                )

        accepted = sorted(
            (candidate for candidate in candidates if candidate.locally_accepted),
            key=lambda item: (-item.score, item.page_type.value),
        )
        if len(accepted) > 1 and accepted[0].score - accepted[1].score < float(
            config["acceptance"]["page_type_runner_up_margin"]
        ):
            candidates = [
                replace(candidate, locally_accepted=False)
                if candidate.locally_accepted
                else candidate
                for candidate in candidates
            ]
        updated_records.append(replace(record, candidates=tuple(candidates)))
        if page_diagnostics:
            diagnostics.append({"page": geometry_page.page, "statement_types": page_diagnostics})
    return tuple(updated_records), diagnostics


def _result_from_records(
    geometry_pages: tuple[OCRPage, ...],
    records: tuple[v3.PageSignalRecord, ...],
    diagnostics: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    records = v3._add_bounded_neighbor_inference(records, config)
    paths = v3._k_best_document_paths(records, config)
    summaries = [v3._path_summary(path, records) for path in paths]
    margin = paths[0].score - paths[1].score if len(paths) > 1 else None
    observed = tuple(page.page for page in geometry_pages)
    common = {
        "algorithm_revision": 4,
        "base_algorithm_revision": 3,
        "policy": config["policy"],
        "change_scope": config["change_scope"],
        "geometry_authority": config["geometry_authority"],
        "semantic_reader_authority": config["semantic_reader_authority"],
        "ordered_anchor_matching": {
            **config["ordered_anchor_matching"],
            "incremental_evidence": diagnostics,
        },
        "observed_pages": list(observed),
        "page_signals": [v3._json_record(record) for record in records],
        "candidate_path_count": len(paths),
        "candidate_path_summaries": summaries,
        "runner_up_margin": round(margin, 6) if margin is not None else None,
    }
    errors = []
    if not paths:
        errors.append("no complete multi-signal CDKT->KQKD->LCTT->TM path")
    elif margin is not None and margin < float(
        config["acceptance"]["document_path_runner_up_margin"]
    ):
        errors.append(f"document-path runner-up margin too small: {margin:.6f}")
    if errors:
        return {"status": "UNRESOLVED", **common, "errors": errors}

    accepted = paths[0]
    typed = [
        (index, records[index], StatementPageType(state))
        for index, state in enumerate(accepted.states)
        if state in {item.value for item in _TARGET_TYPES}
    ]
    statement_pages = [item for item in typed if item[2] is not StatementPageType.TM]
    notes_page = next(record.page for _, record, kind in typed if kind is StatementPageType.TM)
    page_contracts = []
    for position, (_, record, page_type) in enumerate(statement_pages):
        candidate = v3._candidate(record, page_type)
        previous = statement_pages[position - 1] if position else None
        following = statement_pages[position + 1] if position + 1 < len(statement_pages) else None
        page_contracts.append(
            {
                "page": record.page,
                "statement_type": page_type.value,
                "scope": candidate.scope.value,
                "mapping_eligible": candidate.scope is StatementScope.MAIN_STATEMENT,
                "continuation_from_page": (
                    previous[1].page if previous and previous[2] is page_type else None
                ),
                "continuation_to_page": (
                    following[1].page if following and following[2] is page_type else None
                ),
                "locally_accepted": candidate.locally_accepted,
                "inferred_from_page": candidate.inferred_from_page,
                "inference_direction": candidate.inference_direction,
                "inference_checks": list(candidate.inference_checks),
                "score": candidate.score,
                "independent_signal_groups": list(candidate.independent_signal_groups),
            }
        )
    recognized = {
        page_type.value: [
            record.page
            for _, record, observed_type in statement_pages
            if observed_type is page_type
        ]
        for page_type in _MAIN_TYPES
    }
    eligible = {
        page_type.value: [
            record.page
            for _, record, observed_type in statement_pages
            if observed_type is page_type
            and v3._candidate(record, page_type).scope is StatementScope.MAIN_STATEMENT
        ]
        for page_type in _MAIN_TYPES
    }
    lctt_page_numbers = set(recognized[StatementPageType.LCTT.value])
    lctt_pages = tuple(page for page in geometry_pages if page.page in lctt_page_numbers)
    return {
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        **common,
        "block": {
            "start_page": statement_pages[0][1].page,
            "end_page": statement_pages[-1][1].page,
            "notes_boundary_page": notes_page,
            "score": round(accepted.score, 6),
            "recognized_pages_by_statement_type": recognized,
            "mapping_eligible_pages_by_statement_type": eligible,
            "mapping_eligible_pages": [
                contract["page"] for contract in page_contracts if contract["mapping_eligible"]
            ],
            "off_balance_excluded_pages": [
                contract["page"]
                for contract in page_contracts
                if contract["scope"] == StatementScope.OFF_BALANCE_SHEET.value
            ],
            "page_contracts": page_contracts,
        },
        "cash_flow": detect_cash_flow_method(lctt_pages, config["header_candidate"]),
        "errors": [],
    }


def discover_statement_pages_v4(
    geometry_pages: tuple[OCRPage, ...],
    config: dict[str, Any],
    *,
    semantic_pages: tuple[OCRPage, ...] | None = None,
) -> dict[str, Any]:
    if config.get("version") != 4 or not isinstance(config.get("ordered_anchor_matching"), dict):
        raise StatementLocatorError("statement-discovery v4 config is required")
    if not geometry_pages:
        raise StatementLocatorError("statement discovery requires geometry pages")
    observed = tuple(page.page for page in geometry_pages)
    if observed != tuple(range(observed[0], observed[-1] + 1)):
        raise StatementLocatorError("statement discovery requires contiguous geometry pages")
    semantic_by_page: dict[int, OCRPage] = {}
    if semantic_pages is not None:
        semantic_by_page = {page.page: page for page in semantic_pages}
        if len(semantic_by_page) != len(semantic_pages) or set(semantic_by_page) != set(observed):
            raise StatementLocatorError(
                "semantic-reader pages must be unique and cover the geometry-page sequence"
            )
    records = tuple(
        v3._signal_record(page, semantic_by_page.get(page.page), config) for page in geometry_pages
    )
    records, diagnostics = _extend_accounting_evidence(
        geometry_pages, semantic_by_page, records, config
    )
    return _result_from_records(geometry_pages, records, diagnostics, config)
