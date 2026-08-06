from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import partial_ratio, ratio, token_set_ratio

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import parse_financial_number, retrieval_key


class StatementLocatorError(RuntimeError):
    pass


class StatementPageType(StrEnum):
    CDKT = "CDKT"
    KQKD = "KQKD"
    LCTT = "LCTT"
    TM = "TM"
    TABLE_OF_CONTENTS = "TABLE_OF_CONTENTS"
    AUDIT_REPORT = "AUDIT_REPORT"
    AMBIGUOUS = "AMBIGUOUS"
    OTHER = "OTHER"


class StatementScope(StrEnum):
    MAIN_STATEMENT = "MAIN_STATEMENT"
    OFF_BALANCE_SHEET = "OFF_BALANCE_SHEET"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class OCRLine:
    text: str
    bbox: tuple[float, float, float, float]
    score: float

    @property
    def key(self) -> str:
        return retrieval_key(self.text)


@dataclass(frozen=True)
class OCRPage:
    page: int
    width: int
    height: int
    lines: tuple[OCRLine, ...]

    def __post_init__(self) -> None:
        if self.page < 1 or self.width < 1 or self.height < 1:
            raise ValueError("OCR page identity/dimensions must be positive")


@dataclass(frozen=True)
class MatchEvidence:
    line_index: int
    text: str
    normalized_text: str
    anchor: str
    similarity: float


@dataclass(frozen=True)
class PageDecision:
    page: int
    page_type: StatementPageType
    scope: StatementScope
    mapping_eligible: bool
    confidence: float
    form_hits: tuple[str, ...]
    title_scores: dict[str, float]
    title_discriminator_scores: dict[str, float]
    evidence: tuple[str, ...]
    off_balance_item_hits: tuple[str, ...]
    numeric_line_fraction: float
    is_continuation: bool


@dataclass(frozen=True)
class OrderedSequenceEvidence:
    complete: bool
    matches: tuple[dict[str, Any], ...]


def load_statement_locator_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StatementLocatorError(f"cannot load statement-locator config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise StatementLocatorError("statement-locator config version must be 1")
    required_mappings = (
        "form_anchors",
        "title_anchors",
        "title_discriminator_anchors",
        "cash_flow_method",
        "candidate_score_weights",
    )
    if any(not isinstance(payload.get(key), dict) for key in required_mappings):
        raise StatementLocatorError("statement-locator config is missing mappings")
    ordered = payload.get("ordered_statement_types")
    if ordered != ["CDKT", "KQKD", "LCTT"]:
        raise StatementLocatorError("ordered statement types must be CDKT, KQKD, LCTT")
    expected_anchor_types = {"CDKT", "KQKD", "LCTT", "TM"}
    for key in ("form_anchors", "title_anchors", "title_discriminator_anchors"):
        mapping = payload[key]
        if set(mapping) != expected_anchor_types or any(
            not isinstance(values, list) or not values for values in mapping.values()
        ):
            raise StatementLocatorError(f"statement-locator {key} is incomplete")
    for key in (
        "audit_anchors",
        "toc_anchors",
        "continuation_anchors",
        "off_balance_heading_anchors",
        "off_balance_item_anchors",
    ):
        if not isinstance(payload.get(key), list) or not payload[key]:
            raise StatementLocatorError(f"statement-locator config has no {key}")
    thresholds = (
        "header_fraction",
        "title_min_similarity",
        "title_min_margin",
        "continuation_title_min_similarity",
        "continuation_anchor_min_similarity",
        "title_only_min_numeric_line_fraction",
        "title_discriminator_min_similarity",
        "audit_min_similarity",
        "toc_min_similarity",
        "off_balance_heading_min_similarity",
        "off_balance_item_min_similarity",
    )
    if any(
        isinstance(payload.get(key), bool)
        or not isinstance(payload.get(key), (int, float))
        or not 0 <= float(payload[key]) <= 1
        for key in thresholds
    ):
        raise StatementLocatorError("statement-locator thresholds must be within [0, 1]")
    if payload.get("max_interstitial_pages") != 0:
        raise StatementLocatorError("statement blocks may not silently skip interstitial pages")
    integer_gates = {
        "toc_min_distinct_statement_titles": len(expected_anchor_types),
        "off_balance_min_item_hits": len(payload["off_balance_item_anchors"]),
    }
    if any(
        isinstance(payload.get(key), bool)
        or not isinstance(payload.get(key), int)
        or not 1 <= payload[key] <= upper_bound
        for key, upper_bound in integer_gates.items()
    ):
        raise StatementLocatorError("statement-locator integer gates are invalid")
    margin = payload.get("minimum_candidate_margin")
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or float(margin) <= 0:
        raise StatementLocatorError("statement-block candidate margin is invalid")
    weights = payload["candidate_score_weights"]
    expected_weights = {
        "start_form_anchor",
        "form_anchor_page",
        "average_confidence",
    }
    if set(weights) != expected_weights or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0
        for value in weights.values()
    ):
        raise StatementLocatorError("statement-block candidate weights are invalid")
    cash_flow = payload["cash_flow_method"]
    if cash_flow.get("schema_branch_assignment_permitted") is not False:
        raise StatementLocatorError("cash-flow schema branch must remain fail-closed")
    if any(
        isinstance(cash_flow.get(key), bool)
        or not isinstance(cash_flow.get(key), (int, float))
        or not 0 <= float(cash_flow[key]) <= 1
        for key in ("title_min_similarity", "title_min_margin", "row_min_similarity")
    ):
        raise StatementLocatorError("cash-flow thresholds must be within [0, 1]")
    for method in ("direct", "indirect"):
        method_config = cash_flow.get(method)
        if (
            not isinstance(method_config, dict)
            or not isinstance(method_config.get("title_anchors"), list)
            or not method_config["title_anchors"]
            or len(method_config.get("ordered_row_anchors", [])) != 2
        ):
            raise StatementLocatorError(f"cash-flow {method} ordered anchors are incomplete")
    if not isinstance(cash_flow.get("schema_reason"), str) or not cash_flow["schema_reason"]:
        raise StatementLocatorError("cash-flow schema fail-closed reason is absent")
    return payload


def _normalized_anchors(values: list[str]) -> tuple[str, ...]:
    return tuple(retrieval_key(str(value)) for value in values)


def _best_match(
    lines: tuple[OCRLine, ...],
    anchors: tuple[str, ...],
    *,
    match_mode: str = "token_set",
) -> MatchEvidence:
    best = MatchEvidence(-1, "", "", "", 0.0)
    scorers = {
        "token_set": token_set_ratio,
        "ratio": ratio,
        "partial": partial_ratio,
    }
    try:
        scorer = scorers[match_mode]
    except KeyError as exc:
        raise ValueError(f"unsupported match mode: {match_mode}") from exc
    for line_index, line in enumerate(lines):
        if not line.key:
            continue
        for anchor in anchors:
            similarity = scorer(line.key, anchor) / 100.0
            if similarity > best.similarity:
                best = MatchEvidence(
                    line_index=line_index,
                    text=line.text,
                    normalized_text=line.key,
                    anchor=anchor,
                    similarity=similarity,
                )
    return best


def _header_lines(page: OCRPage, fraction: float) -> tuple[OCRLine, ...]:
    cutoff = page.height * fraction
    return tuple(line for line in page.lines if (line.bbox[1] + line.bbox[3]) / 2 <= cutoff)


def _numeric_line_fraction(page: OCRPage) -> float:
    accepted = {
        ObservationKind.VALUE,
        ObservationKind.ZERO,
        ObservationKind.DASH,
    }
    numeric_lines = sum(
        parse_financial_number(line.text).observation in accepted for line in page.lines
    )
    return numeric_lines / len(page.lines) if page.lines else 0.0


def _form_hits(
    lines: tuple[OCRLine, ...], form_anchors: dict[str, list[str]]
) -> tuple[StatementPageType, ...]:
    keys = tuple(line.key for line in lines)
    hits = []
    for raw_type, raw_anchors in form_anchors.items():
        page_type = StatementPageType(raw_type)
        anchors = _normalized_anchors(raw_anchors)
        if any(anchor in key for anchor in anchors for key in keys):
            hits.append(page_type)
    return tuple(hits)


def _title_matches(
    lines: tuple[OCRLine, ...], title_anchors: dict[str, list[str]]
) -> dict[StatementPageType, MatchEvidence]:
    return {
        StatementPageType(raw_type): _best_match(
            lines,
            _normalized_anchors(raw_anchors),
            match_mode="ratio",
        )
        for raw_type, raw_anchors in title_anchors.items()
    }


def _off_balance_scope(
    page: OCRPage,
    header: tuple[OCRLine, ...],
    config: dict[str, Any],
) -> tuple[StatementScope, tuple[str, ...], tuple[str, ...]]:
    # A normal statement title is a token subset of an off-balance heading.
    # Plain edit similarity prevents that subset from becoming a false positive.
    heading = _best_match(
        header,
        _normalized_anchors(config["off_balance_heading_anchors"]),
        match_mode="ratio",
    )
    evidence = []
    if heading.similarity >= float(config["off_balance_heading_min_similarity"]):
        evidence.append(f"off-balance heading similarity={heading.similarity:.6f}: {heading.text}")
    item_hits = []
    for raw_anchor in config["off_balance_item_anchors"]:
        anchor = retrieval_key(str(raw_anchor))
        match = _best_match(page.lines, (anchor,))
        if match.similarity >= float(config["off_balance_item_min_similarity"]):
            item_hits.append(raw_anchor)
    if evidence or len(item_hits) >= int(config["off_balance_min_item_hits"]):
        evidence.append(f"off-balance item anchors={len(item_hits)}")
        return StatementScope.OFF_BALANCE_SHEET, tuple(item_hits), tuple(evidence)
    return StatementScope.MAIN_STATEMENT, tuple(item_hits), tuple(evidence)


def classify_statement_page(page: OCRPage, config: dict[str, Any]) -> PageDecision:
    header = _header_lines(page, float(config["header_fraction"]))
    numeric_line_fraction = _numeric_line_fraction(page)
    forms = _form_hits(header, config["form_anchors"])
    header_titles = _title_matches(header, config["title_anchors"])
    whole_titles = _title_matches(page.lines, config["title_anchors"])
    discriminators = {
        StatementPageType(raw_type): _best_match(
            header,
            _normalized_anchors(raw_anchors),
            match_mode="partial",
        )
        for raw_type, raw_anchors in config["title_discriminator_anchors"].items()
    }
    title_scores = {
        page_type.value: round(match.similarity, 6) for page_type, match in header_titles.items()
    }
    title_discriminator_scores = {
        page_type.value: round(match.similarity, 6) for page_type, match in discriminators.items()
    }
    evidence: list[str] = []

    audit = _best_match(
        header,
        _normalized_anchors(config["audit_anchors"]),
        match_mode="ratio",
    )
    toc = _best_match(
        header,
        _normalized_anchors(config["toc_anchors"]),
        match_mode="ratio",
    )
    continuation = _best_match(
        header,
        _normalized_anchors(config["continuation_anchors"]),
    )
    is_continuation = continuation.similarity >= float(config["continuation_anchor_min_similarity"])
    distinct_whole_titles = sum(
        match.similarity >= float(config["title_min_similarity"]) for match in whole_titles.values()
    )
    if audit.similarity >= float(config["audit_min_similarity"]):
        page_type = StatementPageType.AUDIT_REPORT
        confidence = audit.similarity
        evidence.append(f"audit title similarity={audit.similarity:.6f}: {audit.text}")
    elif toc.similarity >= float(config["toc_min_similarity"]) or (
        not forms and distinct_whole_titles >= int(config["toc_min_distinct_statement_titles"])
    ):
        page_type = StatementPageType.TABLE_OF_CONTENTS
        confidence = max(toc.similarity, min(1.0, distinct_whole_titles / 4))
        evidence.append(
            f"contents evidence: title_similarity={toc.similarity:.6f}, "
            f"distinct_statement_titles={distinct_whole_titles}"
        )
    elif len(forms) == 1:
        page_type = forms[0]
        confidence = 1.0
        evidence.append(f"header form anchor={page_type.value}")
        title = header_titles[page_type]
        if title.similarity >= float(config["title_min_similarity"]):
            evidence.append(f"corroborating title similarity={title.similarity:.6f}: {title.text}")
        if is_continuation:
            evidence.append(
                f"continuation marker similarity={continuation.similarity:.6f}: {continuation.text}"
            )
    elif len(forms) > 1:
        page_type = StatementPageType.AMBIGUOUS
        confidence = 0.0
        evidence.append(f"conflicting header form anchors={[item.value for item in forms]}")
    else:
        ranked = sorted(header_titles.items(), key=lambda item: item[1].similarity, reverse=True)
        best_type, best = ranked[0]
        runner_up = ranked[1][1].similarity
        discriminator = discriminators[best_type]
        discriminator_pass = discriminator.similarity >= float(
            config["title_discriminator_min_similarity"]
        )
        table_evidence_pass = best_type is StatementPageType.TM or (
            numeric_line_fraction >= float(config["title_only_min_numeric_line_fraction"])
        )
        if (
            discriminator_pass
            and table_evidence_pass
            and best.similarity >= float(config["title_min_similarity"])
            and best.similarity - runner_up >= float(config["title_min_margin"])
        ):
            page_type = best_type
            confidence = best.similarity
            evidence.append(
                f"unique header title similarity={best.similarity:.6f}, "
                f"margin={best.similarity - runner_up:.6f}: {best.text}"
            )
        elif (
            discriminator_pass
            and table_evidence_pass
            and best.similarity >= float(config["continuation_title_min_similarity"])
            and best.similarity - runner_up >= float(config["title_min_margin"])
            and is_continuation
        ):
            page_type = best_type
            confidence = min(best.similarity, continuation.similarity)
            evidence.append(
                f"continuation title similarity={best.similarity:.6f}, "
                f"marker_similarity={continuation.similarity:.6f}: {best.text}"
            )
        elif (
            discriminator_pass
            and table_evidence_pass
            and best.similarity >= float(config["title_min_similarity"])
        ):
            page_type = StatementPageType.AMBIGUOUS
            confidence = best.similarity
            evidence.append(f"header title margin too small={best.similarity - runner_up:.6f}")
        elif (not discriminator_pass or not table_evidence_pass) and best.similarity >= float(
            config["title_min_similarity"]
        ):
            page_type = StatementPageType.OTHER
            confidence = 0.0
            evidence.append(
                "title-only statement candidate rejected: "
                f"numeric_line_fraction={numeric_line_fraction:.6f}, "
                f"discriminator_similarity={discriminator.similarity:.6f}"
            )
        else:
            page_type = StatementPageType.OTHER
            confidence = max(0.0, 1.0 - best.similarity)

    scope = StatementScope.NOT_APPLICABLE
    off_balance_hits: tuple[str, ...] = ()
    if page_type is StatementPageType.CDKT:
        scope, off_balance_hits, off_balance_evidence = _off_balance_scope(page, header, config)
        evidence.extend(off_balance_evidence)
    elif page_type in {StatementPageType.KQKD, StatementPageType.LCTT}:
        scope = StatementScope.MAIN_STATEMENT
    mapping_eligible = (
        page_type in {StatementPageType.CDKT, StatementPageType.KQKD, StatementPageType.LCTT}
        and scope is StatementScope.MAIN_STATEMENT
    )
    return PageDecision(
        page=page.page,
        page_type=page_type,
        scope=scope,
        mapping_eligible=mapping_eligible,
        confidence=round(confidence, 6),
        form_hits=tuple(item.value for item in forms),
        title_scores=title_scores,
        title_discriminator_scores=title_discriminator_scores,
        evidence=tuple(evidence),
        off_balance_item_hits=off_balance_hits,
        numeric_line_fraction=round(numeric_line_fraction, 6),
        is_continuation=is_continuation,
    )


def _ordered_sequence(
    page_lines: tuple[tuple[int, int, OCRLine], ...],
    raw_anchors: list[str],
    minimum_similarity: float,
) -> OrderedSequenceEvidence:
    states: list[tuple[float, tuple[int, ...], tuple[dict[str, Any], ...]]] = [(0.0, (), ())]
    for raw_anchor in raw_anchors:
        anchor = retrieval_key(str(raw_anchor))
        candidates: list[tuple[int, dict[str, Any], float]] = []
        for flat_index, (page, line_index, line) in enumerate(page_lines):
            similarity = token_set_ratio(line.key, anchor) / 100.0
            if similarity >= minimum_similarity:
                candidates.append(
                    (
                        flat_index,
                        {
                            "anchor": raw_anchor,
                            "page": page,
                            "line_index": line_index,
                            "text": line.text,
                            "similarity": round(similarity, 6),
                        },
                        similarity,
                    )
                )
        next_states = []
        for score, indices, matches in states:
            for flat_index, match, similarity in candidates:
                if indices and flat_index <= indices[-1]:
                    continue
                next_states.append(
                    (
                        score + similarity,
                        (*indices, flat_index),
                        (*matches, match),
                    )
                )
        if not next_states:
            best_partial = max(
                states,
                key=lambda state: (state[0], tuple(-index for index in state[1])),
            )
            return OrderedSequenceEvidence(False, best_partial[2])
        states = next_states
    best = max(
        states,
        key=lambda state: (state[0], tuple(-index for index in state[1])),
    )
    return OrderedSequenceEvidence(True, best[2])


def detect_cash_flow_method(pages: tuple[OCRPage, ...], config: dict[str, Any]) -> dict[str, Any]:
    cash_flow = config["cash_flow_method"]
    flattened = tuple(
        (page.page, line_index, line)
        for page in pages
        for line_index, line in enumerate(page.lines)
    )
    method_evidence = {}
    title_matches = {}
    sequences = {}
    for method in ("direct", "indirect"):
        method_config = cash_flow[method]
        title = _best_match(
            tuple(line for _, _, line in flattened),
            _normalized_anchors(method_config["title_anchors"]),
        )
        sequence = _ordered_sequence(
            flattened,
            method_config["ordered_row_anchors"],
            float(cash_flow["row_min_similarity"]),
        )
        title_matches[method] = title
        sequences[method] = sequence

    ranked_titles = sorted(title_matches.items(), key=lambda item: item[1].similarity, reverse=True)
    title_winner = None
    if ranked_titles[0][1].similarity >= float(cash_flow["title_min_similarity"]) and ranked_titles[
        0
    ][1].similarity - ranked_titles[1][1].similarity >= float(cash_flow["title_min_margin"]):
        title_winner = ranked_titles[0][0]

    detected = set()
    if title_winner is not None:
        detected.add(title_winner.upper())
    for method in ("direct", "indirect"):
        title = title_matches[method]
        sequence = sequences[method]
        title_pass = method == title_winner
        if sequence.complete:
            detected.add(method.upper())
        method_evidence[method] = {
            "title_pass": title_pass,
            "title_similarity": round(title.similarity, 6),
            "title_text": title.text or None,
            "ordered_row_sequence": asdict(sequence),
        }
    method = next(iter(detected)) if len(detected) == 1 else "CONFLICT" if detected else "UNKNOWN"
    return {
        "method": method,
        "evidence": method_evidence,
        "schema_branch_assignment_permitted": cash_flow["schema_branch_assignment_permitted"],
        "schema_reason": cash_flow["schema_reason"],
    }


def _candidate_blocks(
    decisions: tuple[PageDecision, ...], config: dict[str, Any]
) -> list[dict[str, Any]]:
    order = {
        StatementPageType.CDKT: 0,
        StatementPageType.KQKD: 1,
        StatementPageType.LCTT: 2,
    }
    candidates = []
    for start, decision in enumerate(decisions):
        if (
            decision.page_type is not StatementPageType.CDKT
            or not decision.mapping_eligible
            or decision.is_continuation
        ):
            continue
        stage = 0
        gaps: list[int] = []
        pages: list[PageDecision] = []
        notes_boundary = None
        valid = True
        for current in decisions[start:]:
            if current.page_type is StatementPageType.TM:
                notes_boundary = current.page
                break
            if current.page_type in order:
                current_stage = order[current.page_type]
                if current_stage < stage or current_stage > stage + 1:
                    valid = False
                    break
                stage = current_stage
                pages.append(current)
                continue
            if len(gaps) < int(config["max_interstitial_pages"]):
                gaps.append(current.page)
                continue
            valid = False
            break
        observed_types = {page.page_type for page in pages}
        if (
            valid
            and notes_boundary is not None
            and observed_types
            == {StatementPageType.CDKT, StatementPageType.KQKD, StatementPageType.LCTT}
        ):
            weights = config["candidate_score_weights"]
            form_anchor_page_count = sum(bool(page.form_hits) for page in pages)
            average_confidence = sum(page.confidence for page in pages) / len(pages)
            start_form_anchor = bool(pages[0].form_hits)
            score = (
                float(weights["start_form_anchor"]) * start_form_anchor
                + float(weights["form_anchor_page"]) * form_anchor_page_count
                + float(weights["average_confidence"]) * average_confidence
            )
            candidates.append(
                {
                    "start_page": pages[0].page,
                    "end_page": pages[-1].page,
                    "notes_boundary_page": notes_boundary,
                    "pages": pages,
                    "interstitial_pages": gaps,
                    "score": round(score, 6),
                    "score_components": {
                        "start_form_anchor": start_form_anchor,
                        "form_anchor_page_count": form_anchor_page_count,
                        "average_confidence": round(average_confidence, 6),
                    },
                }
            )
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def locate_statement_pages(pages: tuple[OCRPage, ...], config: dict[str, Any]) -> dict[str, Any]:
    if not pages:
        raise StatementLocatorError("statement location requires OCR pages")
    observed = tuple(page.page for page in pages)
    if observed != tuple(range(observed[0], observed[-1] + 1)):
        raise StatementLocatorError("statement location requires a contiguous OCR page sequence")
    decisions = tuple(classify_statement_page(page, config) for page in pages)
    candidates = _candidate_blocks(decisions, config)
    candidate_summaries = [
        {
            "start_page": candidate["start_page"],
            "end_page": candidate["end_page"],
            "notes_boundary_page": candidate["notes_boundary_page"],
            "recognized_pages": [page.page for page in candidate["pages"]],
            "score": candidate["score"],
            "score_components": candidate["score_components"],
        }
        for candidate in candidates
    ]
    errors = []
    if not candidates:
        errors.append("no complete ordered CDKT->KQKD->LCTT->TM block")
    margin = None
    if len(candidates) > 1:
        margin = candidates[0]["score"] - candidates[1]["score"]
        if margin < float(config["minimum_candidate_margin"]):
            errors.append(f"statement-block runner-up margin too small: {margin:.6f}")
    if errors:
        return {
            "status": "UNRESOLVED",
            "observed_pages": list(observed),
            "page_decisions": [asdict(decision) for decision in decisions],
            "candidate_count": len(candidates),
            "candidate_summaries": candidate_summaries,
            "runner_up_margin": round(margin, 6) if margin is not None else None,
            "errors": errors,
        }

    accepted = candidates[0]
    page_contracts = []
    accepted_pages: list[PageDecision] = accepted["pages"]
    for index, decision in enumerate(accepted_pages):
        previous = accepted_pages[index - 1] if index else None
        following = accepted_pages[index + 1] if index + 1 < len(accepted_pages) else None
        page_contracts.append(
            {
                "page": decision.page,
                "statement_type": decision.page_type.value,
                "scope": decision.scope.value,
                "mapping_eligible": decision.mapping_eligible,
                "continuation_from_page": (
                    previous.page
                    if previous
                    and previous.page_type is decision.page_type
                    and previous.scope is decision.scope
                    else None
                ),
                "continuation_to_page": (
                    following.page
                    if following
                    and following.page_type is decision.page_type
                    and following.scope is decision.scope
                    else None
                ),
                "confidence": decision.confidence,
                "numeric_line_fraction": decision.numeric_line_fraction,
                "continuation_marker_detected": decision.is_continuation,
                "evidence": list(decision.evidence),
                "off_balance_item_hits": list(decision.off_balance_item_hits),
            }
        )
    lctt_page_numbers = {
        decision.page for decision in accepted_pages if decision.page_type is StatementPageType.LCTT
    }
    lctt_pages = tuple(page for page in pages if page.page in lctt_page_numbers)
    recognized_by_form = {
        page_type.value: [page.page for page in accepted_pages if page.page_type is page_type]
        for page_type in (
            StatementPageType.CDKT,
            StatementPageType.KQKD,
            StatementPageType.LCTT,
        )
    }
    eligible_by_type = {
        page_type.value: [
            page.page
            for page in accepted_pages
            if page.page_type is page_type and page.mapping_eligible
        ]
        for page_type in (
            StatementPageType.CDKT,
            StatementPageType.KQKD,
            StatementPageType.LCTT,
        )
    }
    return {
        "status": "ACCEPTED_ORDERED_STATEMENT_BLOCK",
        "observed_pages": list(observed),
        "page_decisions": [asdict(decision) for decision in decisions],
        "candidate_count": len(candidates),
        "candidate_summaries": candidate_summaries,
        "runner_up_margin": round(margin, 6) if margin is not None else None,
        "block": {
            "start_page": accepted["start_page"],
            "end_page": accepted["end_page"],
            "notes_boundary_page": accepted["notes_boundary_page"],
            "score": accepted["score"],
            "score_components": accepted["score_components"],
            "interstitial_pages": accepted["interstitial_pages"],
            "recognized_pages_by_statement_form": recognized_by_form,
            "mapping_eligible_pages_by_statement_type": eligible_by_type,
            "mapping_eligible_pages": [
                decision.page for decision in accepted_pages if decision.mapping_eligible
            ],
            "off_balance_excluded_pages": [
                decision.page
                for decision in accepted_pages
                if decision.scope is StatementScope.OFF_BALANCE_SHEET
            ],
            "page_contracts": page_contracts,
        },
        "cash_flow": detect_cash_flow_method(lctt_pages, config),
        "errors": [],
    }
