from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.text import retrieval_key


@dataclass(frozen=True)
class ScopeRule:
    statement_type: str
    excluded_section: str
    anchor_keys: tuple[str, ...]
    section_start_keys: tuple[str, ...]
    action: str
    rationale: str


@dataclass(frozen=True)
class ScopePolicy:
    version: int
    rules: tuple[ScopeRule, ...]
    source_path: Path


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    detected_section: str | None
    reason: str
    inherited_from_section: bool = False


def load_scope_policy(path: Path) -> ScopePolicy:
    """Load statement-scope exclusions from versioned project configuration."""
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    version = payload.get("version")
    if not isinstance(version, int):
        raise ValueError(f"scope policy has no integer version: {path}")

    rules: list[ScopeRule] = []
    for statement_type, raw_rule in payload.items():
        if statement_type == "version":
            continue
        if not isinstance(raw_rule, dict):
            raise ValueError(f"invalid scope rule for {statement_type}: {path}")
        anchors = raw_rule.get("exact_or_heading_anchors")
        if not isinstance(anchors, list) or not anchors:
            raise ValueError(f"scope rule has no anchors for {statement_type}: {path}")
        anchor_keys = tuple(retrieval_key(str(anchor)) for anchor in anchors)
        if any(not anchor for anchor in anchor_keys):
            raise ValueError(f"scope rule contains an empty anchor for {statement_type}: {path}")
        raw_section_starts = raw_rule.get("section_start_anchors", [])
        if not isinstance(raw_section_starts, list):
            raise ValueError(f"scope rule has invalid section starts for {statement_type}: {path}")
        section_start_keys = tuple(retrieval_key(str(anchor)) for anchor in raw_section_starts)
        if any(not anchor for anchor in section_start_keys):
            raise ValueError(
                f"scope rule contains an empty section start for {statement_type}: {path}"
            )
        rules.append(
            ScopeRule(
                statement_type=str(statement_type),
                excluded_section=str(raw_rule["excluded_section"]),
                anchor_keys=anchor_keys,
                section_start_keys=section_start_keys,
                action=str(raw_rule["action"]),
                rationale=str(raw_rule.get("rationale", "configured scope exclusion")),
            )
        )
    if not rules:
        raise ValueError(f"scope policy contains no rules: {path}")
    return ScopePolicy(version=version, rules=tuple(rules), source_path=path.resolve())


def classify_mapping_scope(
    statement_type: str,
    label: str,
    policy: ScopePolicy | None,
) -> ScopeDecision:
    """Reject configured out-of-scope sections; missing policy fails closed."""
    if policy is None:
        return ScopeDecision(
            allowed=False,
            detected_section=None,
            reason="scope policy missing; mapping is fail-closed",
        )

    key = retrieval_key(label)
    for rule in policy.rules:
        if rule.statement_type != statement_type:
            continue
        if any(key == anchor or key.startswith(f"{anchor} ") for anchor in rule.section_start_keys):
            return ScopeDecision(
                allowed=False,
                detected_section=rule.excluded_section,
                reason=f"configured excluded-section start ({rule.action}): {rule.rationale}",
            )
        if any(key == anchor or key.startswith(f"{anchor} ") for anchor in rule.anchor_keys):
            return ScopeDecision(
                allowed=False,
                detected_section=rule.excluded_section,
                reason=f"configured exclusion ({rule.action}): {rule.rationale}",
            )
    return ScopeDecision(
        allowed=True,
        detected_section=None,
        reason=f"no exclusion matched in scope policy v{policy.version}",
    )


def classify_mapping_scopes(
    rows: list[tuple[str, str]],
    policy: ScopePolicy | None,
    *,
    initial_section_label: str | None = None,
) -> list[ScopeDecision]:
    """Classify an ordered row sequence while carrying excluded-section state.

    State resets whenever the statement type changes. ``initial_section_label``
    lets a page-level heading outside the table establish scope for every table
    row on that page.
    """

    if policy is None:
        return [
            ScopeDecision(False, None, "scope policy missing; mapping is fail-closed")
            for _row in rows
        ]
    decisions: list[ScopeDecision] = []
    active_rule: ScopeRule | None = None
    previous_statement: str | None = None
    for index, (statement_type, label) in enumerate(rows):
        if statement_type != previous_statement:
            active_rule = None
            previous_statement = statement_type
            context = initial_section_label if index == 0 else None
            if context:
                context_key = retrieval_key(context)
                active_rule = next(
                    (
                        rule
                        for rule in policy.rules
                        if rule.statement_type == statement_type
                        and any(
                            context_key == anchor or anchor in context_key
                            for anchor in rule.section_start_keys
                        )
                    ),
                    None,
                )
        key = retrieval_key(label)
        section_start = next(
            (
                rule
                for rule in policy.rules
                if rule.statement_type == statement_type
                and any(key == anchor or key.startswith(f"{anchor} ") for anchor in rule.section_start_keys)
            ),
            None,
        )
        if section_start is not None:
            active_rule = section_start
        if active_rule is not None:
            decisions.append(
                ScopeDecision(
                    allowed=False,
                    detected_section=active_rule.excluded_section,
                    reason=(
                        f"inherited excluded-section state ({active_rule.action}): "
                        f"{active_rule.rationale}"
                    ),
                    inherited_from_section=section_start is None,
                )
            )
            continue
        decisions.append(classify_mapping_scope(statement_type, label, policy))
    return decisions
