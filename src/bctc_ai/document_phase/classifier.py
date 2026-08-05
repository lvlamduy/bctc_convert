from __future__ import annotations

import math
from dataclasses import dataclass

from bctc_ai.core.contracts import PagePhase
from bctc_ai.core.text import retrieval_key


@dataclass(frozen=True)
class PageObservation:
    page: int
    text: str
    numeric_density: float = 0.0
    table_density: float = 0.0


@dataclass(frozen=True)
class PhaseDecision:
    page: int
    phase: PagePhase
    emission_score: float
    confidence: float
    evidence: tuple[str, ...]


_ORDER = {
    PagePhase.COVER: 0,
    PagePhase.AUDIT_REPORT: 1,
    PagePhase.NON_DATA: 1,
    PagePhase.MAIN_STATEMENTS: 2,
    PagePhase.ACCOUNTING_POLICIES: 3,
    PagePhase.QUANTITATIVE_NOTES: 4,
    PagePhase.APPENDIX: 5,
    PagePhase.UNKNOWN: 2,
}


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(retrieval_key(phrase) in text for phrase in phrases)


def _emissions(
    observation: PageObservation,
) -> tuple[dict[PagePhase, float], dict[PagePhase, list[str]]]:
    text = retrieval_key(observation.text)
    scores = {phase: -1.0 for phase in PagePhase}
    evidence = {phase: [] for phase in PagePhase}
    scores[PagePhase.UNKNOWN] = -0.2

    if observation.page == 1 and _contains_any(text, ("báo cáo tài chính", "financial statements")):
        scores[PagePhase.COVER] += 5.0
        evidence[PagePhase.COVER].append("first-page financial-statements title")
    if _contains_any(
        text,
        (
            "báo cáo kiểm toán độc lập",
            "báo cáo soát xét",
            "independent auditors report",
            "review report",
        ),
    ):
        scores[PagePhase.AUDIT_REPORT] += 5.0
        evidence[PagePhase.AUDIT_REPORT].append("audit/review report anchor")
    if _contains_any(text, ("mục lục", "table of contents", "thông tin chung")):
        scores[PagePhase.NON_DATA] += 3.5
        evidence[PagePhase.NON_DATA].append("contents/general-information anchor")
    if _contains_any(
        text,
        (
            "báo cáo tình hình tài chính",
            "bảng cân đối kế toán",
            "statement of financial position",
            "báo cáo kết quả hoạt động",
            "báo cáo kết quả kinh doanh",
            "statement of profit or loss",
            "báo cáo lưu chuyển tiền tệ",
            "cash flow statement",
        ),
    ):
        scores[PagePhase.MAIN_STATEMENTS] += 6.0
        evidence[PagePhase.MAIN_STATEMENTS].append("main-statement title anchor")
    if _contains_any(
        text,
        (
            "chính sách kế toán",
            "cơ sở lập báo cáo",
            "summary of significant accounting policies",
            "applied accounting standards",
        ),
    ):
        scores[PagePhase.ACCOUNTING_POLICIES] += 5.0
        evidence[PagePhase.ACCOUNTING_POLICIES].append("accounting-policy anchor")
    notes_anchor = _contains_any(
        text,
        (
            "thuyết minh báo cáo tài chính",
            "note to the financial statements",
            "notes to the financial statements",
        ),
    )
    if notes_anchor:
        scores[PagePhase.QUANTITATIVE_NOTES] += 1.0
        evidence[PagePhase.QUANTITATIVE_NOTES].append("notes running-header anchor")
    if notes_anchor and (observation.numeric_density >= 0.08 or observation.table_density >= 0.15):
        scores[PagePhase.QUANTITATIVE_NOTES] += 3.0
        evidence[PagePhase.QUANTITATIVE_NOTES].append("numeric/table-dense notes evidence")
    if _contains_any(text, ("phụ lục", "appendix")):
        scores[PagePhase.APPENDIX] += 4.0
        evidence[PagePhase.APPENDIX].append("appendix anchor")
    # A policy anchor is a strong negative anchor for quantitative mapping even
    # when every Notes page repeats the same running header.
    if evidence[PagePhase.ACCOUNTING_POLICIES]:
        scores[PagePhase.QUANTITATIVE_NOTES] -= 4.0
        evidence[PagePhase.QUANTITATIVE_NOTES].append("negative policy anchor")
    return scores, evidence


def _transition(previous: PagePhase, current: PagePhase) -> float:
    if previous == current:
        return 0.0
    if previous is PagePhase.UNKNOWN or current is PagePhase.UNKNOWN:
        return -0.6
    previous_order, current_order = _ORDER[previous], _ORDER[current]
    if current_order < previous_order:
        return -5.0 - (previous_order - current_order)
    jump = current_order - previous_order
    return -0.25 - 0.35 * max(0, jump - 1)


def classify_page_sequence(observations: list[PageObservation]) -> list[PhaseDecision]:
    if not observations:
        return []
    states = list(PagePhase)
    emissions_and_evidence = [_emissions(observation) for observation in observations]
    dynamic: list[dict[PagePhase, float]] = []
    back: list[dict[PagePhase, PagePhase | None]] = []
    for index, (emissions, _) in enumerate(emissions_and_evidence):
        scores: dict[PagePhase, float] = {}
        parents: dict[PagePhase, PagePhase | None] = {}
        for state in states:
            if index == 0:
                prior = 0.5 if state is PagePhase.COVER else 0.0
                scores[state] = prior + emissions[state]
                parents[state] = None
                continue
            choices = {
                previous: dynamic[index - 1][previous] + _transition(previous, state)
                for previous in states
            }
            parent, prior_score = max(choices.items(), key=lambda item: item[1])
            scores[state] = prior_score + emissions[state]
            parents[state] = parent
        dynamic.append(scores)
        back.append(parents)

    final_state = max(dynamic[-1], key=dynamic[-1].get)
    path = [final_state]
    for index in range(len(observations) - 1, 0, -1):
        parent = back[index][path[-1]]
        if parent is None:
            raise RuntimeError("phase decoder backtrace is incomplete")
        path.append(parent)
    path.reverse()
    decisions = []
    for index, (observation, state) in enumerate(zip(observations, path, strict=True)):
        emissions, evidence = emissions_and_evidence[index]
        ordered_scores = sorted(emissions.values(), reverse=True)
        margin = ordered_scores[0] - ordered_scores[1]
        confidence = 1.0 / (1.0 + math.exp(-margin))
        decisions.append(
            PhaseDecision(
                page=observation.page,
                phase=state,
                emission_score=round(emissions[state], 6),
                confidence=round(confidence, 6),
                evidence=tuple(evidence[state]),
            )
        )
    return decisions
