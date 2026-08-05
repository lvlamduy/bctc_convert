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
        rules.append(
            ScopeRule(
                statement_type=str(statement_type),
                excluded_section=str(raw_rule["excluded_section"]),
                anchor_keys=anchor_keys,
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
