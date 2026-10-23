"""Load and check the declarative notes configuration (axes, families, crosswalk)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.primary_statements.text_v1 import fold_vietnamese


class NotesConfigError(ValueError):
    pass


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise NotesConfigError(message)


def phrase_in(phrase: str, text: str) -> bool:
    """Whole-word containment of a folded phrase in a folded text."""

    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def all_phrases(groups: list[list[str]], text: str) -> bool:
    """True when some group has every phrase present."""

    return any(all(phrase_in(phrase, text) for phrase in group) for group in groups)


@dataclass(frozen=True)
class Axis:
    name: str
    members: dict[str, dict[str, Any]]
    outside_members: dict[str, dict[str, Any]]

    def match(self, key: str) -> list[str]:
        """Members (regular or outside) whose aliases/phrases the row key carries."""

        found = []
        for member, spec in self.members.items():
            if all_phrases(spec.get("none_of", []), key):
                continue  # an excluding phrase is printed: never this member
            if any(key == alias or phrase_in(alias, key) for alias in spec.get("aliases", [])) \
                    or key in spec.get("exact", []) or all_phrases(spec.get("all_of", []), key):
                found.append(member)
        for member, spec in self.outside_members.items():
            if all_phrases(spec.get("contains_all", []), key):
                found.append(member)
        # A more specific member printed with a broader one wins ("tiết kiệm có kỳ hạn" is savings).
        dominated = {d for member in found for d in (self.members.get(member) or {}).get("dominates", [])}
        return [member for member in found if member not in dominated]


@dataclass(frozen=True)
class Family:
    name: str
    shape: str
    axis: Axis
    period_basis: str
    raw: dict[str, Any]
    sha256: str

    @property
    def retrieval_patterns(self) -> list[str]:
        return list(self.raw["retrieval"]["row_label_like"])

    @property
    def min_distinct_members(self) -> int:
        return int(self.raw["retrieval"].get("min_distinct_members", 1))

    def subjects_in(self, folded: str) -> list[str]:
        found = []
        for subject, spec in self.raw["subjects"].items():
            if all_phrases(spec.get("any", []), folded) and not all_phrases(spec.get("none", []), folded):
                found.append(subject)
        return found

    def rejects(self, folded: str) -> bool:
        return all_phrases(self.raw.get("reject_context", []), folded)

    def row_veto(self, key: str) -> str | None:
        """The first declared row veto (a printed stock/movement basis, a foreign population) the row key carries."""

        for name, groups in self.raw.get("row_vetoes", {}).items():
            if all_phrases(groups, key):
                return name
        return None


@dataclass(frozen=True)
class NotesConfig:
    axes: dict[str, Axis]
    families: dict[str, Family]
    crosswalk: dict[tuple[str, str, tuple[str, ...]], int]
    pins: dict[str, str]


def _load(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def load_notes_config_v1(project_root: Path) -> NotesConfig:
    base = project_root / "config" / "notes"
    axes_raw, axes_sha = _load(base / "axes_v1.yaml")
    _require(axes_raw.get("format_version") == "NOTES_AXES_V1", "axes format")
    axes = {}
    for name, spec in axes_raw["axes"].items():
        members = {m: {**s, "aliases": [fold_vietnamese(str(a)) for a in s.get("aliases", [])],
                       "exact": [fold_vietnamese(str(a)) for a in s.get("exact", [])],
                       "all_of": [[fold_vietnamese(str(p)) for p in g] for g in s.get("all_of", [])],
                       "none_of": [[fold_vietnamese(str(p)) for p in g] for g in s.get("none_of", [])]}
                   for m, s in spec["members"].items()}
        _require(all(s.get("parent") in (None, *members) for s in members.values()), f"axis {name}: unknown member parent")
        outside = {m: {**s, "contains_all": [[fold_vietnamese(str(p)) for p in g] for g in s.get("contains_all", [])]}
                   for m, s in (spec.get("outside_members") or {}).items()}
        _require(not set(members) & set(outside), f"axis {name}: member defined twice")
        axes[name] = Axis(name, members, outside)
    families = {}
    pins = {"axes_v1.yaml": axes_sha}
    for path in sorted((base / "families").glob("*.yaml")):
        raw, sha = _load(path)
        _require(raw.get("format_version") == "NOTES_FAMILY_V1", f"{path.name}: format")
        _require(raw["axis"] in axes, f"{path.name}: unknown axis")
        _require(all(name in axes for name in raw.get("axes", [])) and (not raw.get("axes") or raw["axes"][0] == raw["axis"]),
                 f"{path.name}: axes must exist and start with the family axis")
        for subject, spec in raw["subjects"].items():
            spec["any"] = [[fold_vietnamese(str(p)) for p in g] for g in spec.get("any", [])]
            spec["none"] = [[fold_vietnamese(str(p)) for p in g] for g in spec.get("none", [])]
        raw["reject_context"] = [[fold_vietnamese(str(p)) for p in g] for g in raw.get("reject_context", [])]
        raw["row_vetoes"] = {str(name): [[fold_vietnamese(str(p)) for p in g] for g in groups]
                             for name, groups in (raw.get("row_vetoes") or {}).items()}
        _require(all(line in axes[raw["axis"]].members for line in raw.get("foreign_row_holds") or []),
                 f"{path.name}: foreign_row_holds must name lines of the family axis")
        raw["retrieval"]["explicit_title_phrases"] = [
            [fold_vietnamese(str(p)) for p in g] for g in raw["retrieval"].get("explicit_title_phrases", [])
        ]
        families[raw["family"]] = Family(raw["family"], raw["shape"], axes[raw["axis"]], raw["period_basis"], raw, sha)
        pins[f"families/{path.name}"] = sha
    crosswalk_raw, crosswalk_sha = _load(base / "crosswalk_v1.yaml")
    _require(crosswalk_raw.get("format_version") == "NOTES_CROSSWALK_V1", "crosswalk format")
    crosswalk = {}
    for entry in crosswalk_raw["entries"]:
        members = tuple(entry["members_in_preference"]) if "members_in_preference" in entry else (entry["member"],)
        key = (entry["concept"], entry["axis"], members)
        _require(key not in crosswalk, f"crosswalk duplicate {key}")
        _require(entry["report_norm_id"] not in crosswalk.values(), f"crosswalk ReportNormId reused {entry['report_norm_id']}")
        crosswalk[key] = entry["report_norm_id"]
    pins["crosswalk_v1.yaml"] = crosswalk_sha
    return NotesConfig(axes, families, crosswalk, pins)
