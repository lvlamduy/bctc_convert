"""Compiled PRIMARY retrieval catalog bound to the pinned schema registry.

The registry (template workbooks + hierarchy reference) is the identity and
order authority. The YAML catalog only adds retrieval aliases, structural
constraints and explicit source-only/structural dispositions. Loading fails
closed on unknown ReportNormIds, statement mismatches, unconstrained alias
collisions, and keys shared between mapped and source-only entries.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all
from bctc_ai.primary_statements.text_v1 import NORMALIZATION_VERSION, label_key_v1

CATALOG_FORMAT_VERSION = "PRIMARY_STATEMENT_CATALOG_V1"
PRIMARY_STATEMENTS = ("CDKT", "KQKD", "LCTT")
CATALOG_RELATIVE_PATH = "config/primary_statements/catalog_v1.yaml"


class PrimaryCatalogError(ValueError):
    """The catalog does not bind exactly to the pinned schema."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise PrimaryCatalogError(message)


@dataclass(frozen=True)
class ItemSpec:
    statement: str
    report_norm_id: int
    canonical_name: str
    display_order: int
    section: str
    branch: str | None
    scope: tuple[str, ...]
    schema_parent_id: int | None
    requires_parent: tuple[str, ...]
    requires_top_level: bool
    requires_section: str | None
    requires_values: bool
    forbids_ancestor: tuple[str, ...] = ()
    forbids_preceded_by: tuple[str, ...] = ()

    @property
    def constrained(self) -> bool:
        return bool(self.requires_parent or self.requires_top_level or self.requires_section or self.requires_values
                    or self.forbids_ancestor or self.forbids_preceded_by)


@dataclass(frozen=True)
class SourceOnlySpec:
    reason: str
    requires_parent: tuple[str, ...] = ()
    requires_preceded_by: tuple[str, ...] = ()

    @property
    def constrained(self) -> bool:
        return bool(self.requires_parent or self.requires_preceded_by)


@dataclass(frozen=True)
class AliasHit:
    kind: str  # ITEM | PSEUDO_HEADING | SOURCE_ONLY | STRUCTURAL
    target: str  # ReportNormId as text, pseudo key, or reason
    alias_text: str
    source_only: SourceOnlySpec | None = None


@dataclass
class StatementCatalog:
    statement: str
    statement_type: str
    period_basis: str
    items: dict[int, ItemSpec]
    ordered_ids: list[int]
    section_headings: dict[str, str]
    index: dict[str, list[AliasHit]] = field(default_factory=dict)

    def lookup(self, key: str) -> list[AliasHit]:
        return list(self.index.get(key, ()))


@dataclass
class PrimaryCatalog:
    statements: dict[str, StatementCatalog]
    catalog_sha256: str
    compiled_sha256: str
    schema_revision: str
    template_sha256: dict[str, str]
    schema_items: dict[tuple[str, int], SchemaItem]

    def identity(self) -> dict[str, Any]:
        return {
            "catalog_format_version": CATALOG_FORMAT_VERSION,
            "catalog_path": CATALOG_RELATIVE_PATH,
            "catalog_sha256": self.catalog_sha256,
            "compiled_catalog_sha256": self.compiled_sha256,
            "normalization_version": NORMALIZATION_VERSION,
            "schema_revision": self.schema_revision,
            "template_sha256": dict(sorted(self.template_sha256.items())),
        }


def _section_of(ordered: list[int], blocks: dict[str, list[int]]) -> dict[int, str]:
    position = {rnid: index for index, rnid in enumerate(ordered)}
    result: dict[int, str] = {}
    for name, (start, end) in blocks.items():
        _require(start in position and end in position, f"section endpoint absent: {name}")
        _require(position[start] <= position[end], f"section block reversed: {name}")
        for rnid in ordered[position[start]: position[end] + 1]:
            _require(rnid not in result, f"ReportNormId {rnid} is in two sections")
            result[rnid] = name
    missing = [rnid for rnid in ordered if rnid not in result]
    _require(not missing, f"sections leave ReportNormIds unassigned: {missing}")
    return result


def load_primary_catalog_v1(project_root: Path) -> PrimaryCatalog:
    """Load and compile the catalog against the pinned schema registry."""

    root = project_root.resolve()
    workbooks, schema = load_all(root / "template", root)
    _, hierarchy = load_hierarchy_reference(root / "config/schemas/hierarchy_reference.yaml", root, schema)
    apply_hierarchy_reference(schema, hierarchy)
    by_key = {(item.statement_type, item.schema_id): item for item in schema}
    raw = (root / CATALOG_RELATIVE_PATH).read_bytes()
    payload = yaml.safe_load(raw.decode("utf-8"))
    _require(payload.get("format_version") == CATALOG_FORMAT_VERSION, "catalog format drifted")
    _require(payload.get("schema_revision") == "UNIVERSAL_BANK_BCTC_SCHEMA@6076", "catalog schema revision drifted")
    _require(payload.get("normalization_version") == NORMALIZATION_VERSION, "catalog normalization drifted")
    statements = {}
    for statement in PRIMARY_STATEMENTS:
        spec = payload["statements"][statement]
        ordered = [item.schema_id for item in sorted(
            (item for item in schema if item.statement_type == statement), key=lambda item: item.display_order
        )]
        sections = _section_of(ordered, spec["sections"])
        raw_items = {int(key): value or {} for key, value in spec.get("items", {}).items()}
        unknown = sorted(set(raw_items) - set(ordered))
        _require(not unknown, f"{statement} catalog names unknown ReportNormIds {unknown}")
        pseudo = spec.get("pseudo_headings", {}) or {}
        headings = {str(key): value for key, value in (spec.get("section_headings") or {}).items()}
        items: dict[int, ItemSpec] = {}
        for rnid in ordered:
            schema_item = by_key[(statement, rnid)]
            entry = raw_items.get(rnid, {})
            parents = tuple(str(value) for value in entry.get("requires_parent", ()) or ())
            forbidden = tuple(str(value) for value in entry.get("forbids_ancestor", ()) or ())
            not_after = tuple(str(value) for value in entry.get("forbids_preceded_by", ()) or ())
            for parent in parents + forbidden + not_after:
                _require(parent in pseudo or (parent.isdigit() and int(parent) in set(ordered)),
                         f"{statement}/{rnid} requires an unknown parent {parent}")
            items[rnid] = ItemSpec(
                statement=statement,
                report_norm_id=rnid,
                canonical_name=schema_item.canonical_name,
                display_order=schema_item.display_order,
                section=sections[rnid],
                branch=schema_item.cash_flow_branch if statement == "LCTT" else None,
                scope=tuple(schema_item.scope),
                schema_parent_id=schema_item.parent_id,
                requires_parent=parents,
                requires_top_level=bool(entry.get("requires_top_level", False)),
                requires_section=entry.get("requires_section"),
                requires_values=bool(entry.get("requires_values", False)),
                forbids_ancestor=forbidden,
                forbids_preceded_by=not_after,
            )
        index: dict[str, list[AliasHit]] = defaultdict(list)

        def add(key_text: str, hit: AliasHit) -> None:
            key = label_key_v1(key_text).key
            _require(key, f"{statement} alias normalizes to an empty key: {key_text!r}")
            if not any(existing.kind == hit.kind and existing.target == hit.target for existing in index[key]):
                index[key].append(hit)

        for rnid in ordered:
            schema_item = by_key[(statement, rnid)]
            texts = [schema_item.canonical_name, *schema_item.structural_aliases, *raw_items.get(rnid, {}).get("aliases", [])]
            for text in texts:
                add(text, AliasHit("ITEM", str(rnid), text))
        for key, value in pseudo.items():
            for text in value.get("aliases", []):
                add(text, AliasHit("PSEUDO_HEADING", key, text))
        for entry in spec.get("source_only", []) or []:
            only = SourceOnlySpec(
                entry["reason"],
                tuple(str(value) for value in entry.get("requires_parent", ()) or ()),
                tuple(str(value) for value in entry.get("requires_preceded_by", ()) or ()),
            )
            for text in entry["aliases"]:
                add(text, AliasHit("SOURCE_ONLY", entry["reason"], text, only))
        for entry in spec.get("structural", []) or []:
            for text in entry["aliases"]:
                add(text, AliasHit("STRUCTURAL", entry["reason"], text))
        for key, hits in index.items():
            kinds = {hit.kind for hit in hits}
            if len(hits) == 1:
                continue
            _require(kinds == {"ITEM"} or (kinds <= {"ITEM", "PSEUDO_HEADING", "SOURCE_ONLY"} and all(
                hit.kind == "PSEUDO_HEADING"
                or (hit.kind == "SOURCE_ONLY" and hit.source_only.constrained)
                or (hit.kind == "ITEM" and items[int(hit.target)].constrained)
                for hit in hits
            )), f"{statement} alias key {key!r} mixes dispositions {sorted(kinds)} without constraints")
            item_hits = [hit for hit in hits if hit.kind == "ITEM"]
            by_branch: dict[str | None, list[ItemSpec]] = defaultdict(list)
            for hit in item_hits:
                spec_item = items[int(hit.target)]
                by_branch[spec_item.branch].append(spec_item)
            for group in by_branch.values():
                if len(group) > 1:
                    _require(all(item.constrained for item in group),
                             f"{statement} alias key {key!r} is shared by unconstrained identities "
                             f"{sorted(item.report_norm_id for item in group if not item.constrained)}")
        statements[statement] = StatementCatalog(
            statement=statement,
            statement_type=spec["statement_type"],
            period_basis=spec["period_basis"],
            items=items,
            ordered_ids=ordered,
            section_headings=headings,
            index=dict(index),
        )
    compiled = {
        statement: {
            "items": [
                {
                    "id": item.report_norm_id, "order": item.display_order, "section": item.section,
                    "branch": item.branch, "scope": list(item.scope), "parent": item.schema_parent_id,
                    "requires_parent": list(item.requires_parent), "top": item.requires_top_level,
                    "requires_section": item.requires_section, "requires_values": item.requires_values,
                    "forbids_ancestor": list(item.forbids_ancestor),
                    "forbids_preceded_by": list(item.forbids_preceded_by),
                }
                for item in catalog.items.values()
            ],
            "index": {key: [[hit.kind, hit.target, None if hit.source_only is None else
                             [list(hit.source_only.requires_parent), list(hit.source_only.requires_preceded_by)]]
                            for hit in hits] for key, hits in sorted(catalog.index.items())},
        }
        for statement, catalog in statements.items()
    }
    compiled_bytes = json.dumps(compiled, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return PrimaryCatalog(
        statements=statements,
        catalog_sha256=hashlib.sha256(raw).hexdigest(),
        compiled_sha256=hashlib.sha256(compiled_bytes).hexdigest(),
        schema_revision="UNIVERSAL_BANK_BCTC_SCHEMA@6076",
        template_sha256={wb.statement_type: wb.sha256 for wb in workbooks if wb.statement_type in PRIMARY_STATEMENTS},
        schema_items=by_key,
    )
