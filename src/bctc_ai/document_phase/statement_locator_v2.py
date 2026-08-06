from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.hashing import sha256_file
from bctc_ai.document_phase.statement_locator import (
    MatchEvidence,
    OCRLine,
    OCRPage,
    PageDecision,
    StatementLocatorError,
    StatementPageType,
    StatementScope,
    _best_match,
    _candidate_blocks,
    _header_lines,
    _normalized_anchors,
    _numeric_line_fraction,
    _off_balance_scope,
    detect_cash_flow_method,
    load_statement_locator_config,
)


@dataclass(frozen=True)
class FormFamilyEvidence:
    page_type: StatementPageType
    canonical_family: str
    suffix: str | None
    line_index: int
    text: str
    normalized_text: str


_FORM_ANCHOR = re.compile(r"^(b0[2345]) tctd(?: hn)?$")


def load_statement_locator_v2_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StatementLocatorError(f"cannot load statement-locator v2 config: {path}") from exc
    expected = {
        "version": 2,
        "policy": "GENERAL_ORDERED_STATEMENT_BLOCK_UNICODE_FORM_FAMILY_V2",
        "base_config": "statement-locator-v1.yaml",
        "form_family_matching": {
            "strategy": "REGEX_CANONICAL_FAMILY_WITH_OPTIONAL_SINGLE_ASCII_SUFFIX",
            "normalized_families": ["B02", "B03", "B04", "B05"],
            "required_context_token": "TCTD",
            "permit_optional_hn_token": True,
        },
        "title_matching": {
            "strategy": "TOKEN_BOUNDARY_CORE_CONTAINMENT_THEN_FULL_EDIT_RATIO",
            "exact_containment_score": 1.0,
            "require_existing_discriminator_and_table_gates": True,
        },
        "forbidden_inputs": [
            "bank_identity",
            "filename_identity",
            "page_number_rules",
            "numeric_values_for_page_type",
            "historical_values",
            "report_norm_id_numeric_order",
        ],
    }
    if not isinstance(payload, dict) or any(
        payload.get(key) != value for key, value in expected.items()
    ):
        raise StatementLocatorError("statement-locator v2 identity/safety policy drifted")
    base_path = (path.parent / str(payload["base_config"])).resolve()
    if base_path.parent != path.parent.resolve() or not base_path.is_file():
        raise StatementLocatorError("statement-locator v2 base config is absent or escapes")
    if sha256_file(base_path) != payload.get("base_config_sha256"):
        raise StatementLocatorError("statement-locator v2 base config hash drifted")
    config = copy.deepcopy(load_statement_locator_config(base_path))
    config["version"] = 2
    config["policy"] = payload["policy"]
    config["v2"] = {
        "configuration_name": path.name,
        "base_configuration_name": base_path.name,
        "base_configuration_sha256": payload["base_config_sha256"],
        "form_family_matching": payload["form_family_matching"],
        "title_matching": payload["title_matching"],
        "forbidden_inputs": payload["forbidden_inputs"],
    }
    reason = payload.get("cash_flow_schema_reason")
    if not isinstance(reason, str) or not reason.strip():
        raise StatementLocatorError("statement-locator v2 cash-flow schema reason is absent")
    config["cash_flow_method"]["schema_reason"] = reason.strip()
    return config


def _require_v2(config: dict[str, Any]) -> None:
    if config.get("version") != 2 or not isinstance(config.get("v2"), dict):
        raise StatementLocatorError("statement-locator v2 config is required")


def _form_family_evidence(
    lines: tuple[OCRLine, ...],
    form_anchors: dict[str, list[str]],
) -> tuple[FormFamilyEvidence, ...]:
    evidence = []
    for raw_type, raw_anchors in form_anchors.items():
        page_type = StatementPageType(raw_type)
        for raw_anchor in raw_anchors:
            anchor = _normalized_anchors([raw_anchor])[0]
            anchor_match = _FORM_ANCHOR.fullmatch(anchor)
            if anchor_match is None:
                raise StatementLocatorError(f"v2 form anchor is not a supported family: {anchor}")
            family = anchor_match.group(1)
            pattern = re.compile(
                rf"(?<![a-z0-9]){re.escape(family)}(?P<suffix>[a-z])?\s+"
                rf"tctd(?:\s+hn)?(?![a-z0-9])"
            )
            for line_index, line in enumerate(lines):
                match = pattern.search(line.key)
                if match is None:
                    continue
                evidence.append(
                    FormFamilyEvidence(
                        page_type=page_type,
                        canonical_family=family.upper(),
                        suffix=match.group("suffix"),
                        line_index=line_index,
                        text=line.text,
                        normalized_text=line.key,
                    )
                )
    unique = {
        (item.page_type, item.canonical_family, item.suffix, item.line_index): item
        for item in evidence
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.line_index,
                item.page_type.value,
                item.canonical_family,
                item.suffix or "",
            ),
        )
    )


def _core_is_token_bounded(line_key: str, anchor: str) -> bool:
    return f" {anchor} " in f" {line_key} "


def _best_title_match_v2(lines: tuple[OCRLine, ...], anchors: tuple[str, ...]) -> MatchEvidence:
    best = MatchEvidence(-1, "", "", "", 0.0)
    for line_index, line in enumerate(lines):
        if not line.key:
            continue
        for anchor in anchors:
            similarity = (
                1.0 if _core_is_token_bounded(line.key, anchor) else ratio(line.key, anchor) / 100.0
            )
            if similarity > best.similarity:
                best = MatchEvidence(
                    line_index=line_index,
                    text=line.text,
                    normalized_text=line.key,
                    anchor=anchor,
                    similarity=similarity,
                )
    return best


def _title_matches_v2(
    lines: tuple[OCRLine, ...], title_anchors: dict[str, list[str]]
) -> dict[StatementPageType, MatchEvidence]:
    return {
        StatementPageType(raw_type): _best_title_match_v2(lines, _normalized_anchors(raw_anchors))
        for raw_type, raw_anchors in title_anchors.items()
    }


def classify_statement_page_v2(page: OCRPage, config: dict[str, Any]) -> PageDecision:
    _require_v2(config)
    header = _header_lines(page, float(config["header_fraction"]))
    numeric_line_fraction = _numeric_line_fraction(page)
    form_evidence = _form_family_evidence(header, config["form_anchors"])
    forms = tuple(dict.fromkeys(item.page_type for item in form_evidence))
    header_titles = _title_matches_v2(header, config["title_anchors"])
    whole_titles = _title_matches_v2(page.lines, config["title_anchors"])
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
        matched_forms = [item for item in form_evidence if item.page_type is page_type]
        for item in matched_forms:
            evidence.append(
                f"header form family={item.canonical_family}, suffix={item.suffix or 'NONE'}: "
                f"{item.text}"
            )
        title = header_titles[page_type]
        if title.similarity >= float(config["title_min_similarity"]):
            mode = (
                "core_containment"
                if _core_is_token_bounded(title.normalized_text, title.anchor)
                else "full_edit_ratio"
            )
            evidence.append(
                f"corroborating title {mode} similarity={title.similarity:.6f}: {title.text}"
            )
        if is_continuation:
            evidence.append(
                f"continuation marker similarity={continuation.similarity:.6f}: {continuation.text}"
            )
    elif len(forms) > 1:
        page_type = StatementPageType.AMBIGUOUS
        confidence = 0.0
        evidence.append(f"conflicting header form families={[item.value for item in forms]}")
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
            mode = (
                "core_containment"
                if _core_is_token_bounded(best.normalized_text, best.anchor)
                else "full_edit_ratio"
            )
            evidence.append(
                f"unique header title {mode} similarity={best.similarity:.6f}, "
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


def locate_statement_pages_v2(pages: tuple[OCRPage, ...], config: dict[str, Any]) -> dict[str, Any]:
    _require_v2(config)
    if not pages:
        raise StatementLocatorError("statement location requires OCR pages")
    observed = tuple(page.page for page in pages)
    if observed != tuple(range(observed[0], observed[-1] + 1)):
        raise StatementLocatorError("statement location requires a contiguous OCR page sequence")
    decisions = tuple(classify_statement_page_v2(page, config) for page in pages)
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
    common = {
        "algorithm_revision": 2,
        "observed_pages": list(observed),
        "page_decisions": [asdict(decision) for decision in decisions],
        "candidate_count": len(candidates),
        "candidate_summaries": candidate_summaries,
        "runner_up_margin": round(margin, 6) if margin is not None else None,
    }
    if errors:
        return {"status": "UNRESOLVED", **common, "errors": errors}

    accepted = candidates[0]
    accepted_pages: list[PageDecision] = accepted["pages"]
    page_contracts = []
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
    lctt_numbers = {
        decision.page for decision in accepted_pages if decision.page_type is StatementPageType.LCTT
    }
    lctt_pages = tuple(page for page in pages if page.page in lctt_numbers)
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
        **common,
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
