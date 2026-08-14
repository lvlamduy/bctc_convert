from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes, stable_records_hash
from bctc_ai.schema.registry import SchemaItem

TM_CONTEXT_POLICY_RELATIVE_PATH = Path("config/schemas/tm-context-v1.yaml")

_POLICY_NAME = "UNIVERSAL_BANK_BCTC_TM_SCHEMA_CONTEXT_V1"
_STATEMENT_TYPE = "TM"
_ORDER_AUTHORITY = "WORKBOOK_DISPLAY_ORDER"
_RESOLVED_STATUS = "RESOLVED"
_ORPHAN_STATUS = "UNRESOLVED_ORPHAN"
_LEVEL_MISMATCH_STATUS = "UNRESOLVED_LEVEL_MISMATCH"
_SECTION_ROOT_IDS = (560, 1142, 1247, 1259)
_ORPHAN_IDS = (1944,)
_LEVEL_MISMATCH_SHAPES: tuple[tuple[int, int, int, int], ...] = ()
_ACCOUNTING_SECTIONS = (
    "BALANCE_SHEET_NOTES",
    "INCOME_STATEMENT_NOTES",
    "CASH_FLOW_NOTES",
    "OTHER_QUANTITATIVE_NOTES",
)


class TmContextError(ValueError):
    """Raised when the TM hierarchy cannot support safe mapping context."""


@dataclass(frozen=True, slots=True)
class TmSectionRootPolicy:
    report_norm_id: int
    section: str
    canonical_name: str


@dataclass(frozen=True, slots=True)
class TmOrphanPolicy:
    report_norm_id: int
    canonical_name: str
    expected_parent_report_norm_id: int | None
    expected_hierarchy_level: int | None
    status: str
    mapping_eligible: bool


@dataclass(frozen=True, slots=True)
class TmLevelMismatchPolicy:
    report_norm_id: int
    canonical_name: str
    expected_parent_report_norm_id: int
    expected_declared_hierarchy_level: int
    expected_derived_hierarchy_level: int
    status: str
    mapping_eligible: bool


@dataclass(frozen=True, slots=True)
class TmContextPolicy:
    version: int
    policy: str
    statement_type: str
    order_authority: str
    section_roots: tuple[TmSectionRootPolicy, ...]
    resolved_status: str
    resolved_mapping_eligible: bool
    level_mismatch_items: tuple[TmLevelMismatchPolicy, ...]
    orphan_items: tuple[TmOrphanPolicy, ...]
    source_path: Path
    source_sha256: str


@dataclass(frozen=True, slots=True)
class TmSchemaContext:
    report_norm_id: int
    canonical_name: str
    statement_type: str
    section: str | None
    section_root_id: int | None
    note_family_root_id: int | None
    ancestor_path: tuple[int, ...]
    parent_report_norm_id: int | None
    hierarchy_level: int | None
    derived_hierarchy_level: int | None
    display_order: int
    context_status: str
    mapping_eligible: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _exact_mapping(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise TmContextError(f"{label} fields are invalid")
    return value


def _positive_id(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TmContextError(f"{label} must be a positive ReportNormId")
    return value


def _optional_nonnegative_integer(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TmContextError(f"{label} must be null or a non-negative integer")
    return value


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise TmContextError(f"{label} must be non-blank normalized text")
    return value


def load_tm_context_policy(path: Path) -> TmContextPolicy:
    """Load the bank-independent TM hierarchy-context policy from one byte snapshot."""

    path = path.resolve()
    try:
        source_bytes = path.read_bytes()
        raw_payload = yaml.safe_load(source_bytes) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise TmContextError(f"cannot load TM context policy: {path}") from exc
    payload = _exact_mapping(
        raw_payload,
        {
            "version",
            "policy",
            "statement_type",
            "order_authority",
            "section_roots",
            "resolved_context",
            "level_mismatch_items",
            "orphan_items",
        },
        "TM context policy",
    )
    if (
        type(payload["version"]) is not int
        or payload["version"] != 1
        or payload["policy"] != _POLICY_NAME
        or payload["statement_type"] != _STATEMENT_TYPE
        or payload["order_authority"] != _ORDER_AUTHORITY
    ):
        raise TmContextError("TM context policy identity is invalid")

    raw_roots = payload["section_roots"]
    if not isinstance(raw_roots, list) or len(raw_roots) != len(_ACCOUNTING_SECTIONS):
        raise TmContextError("TM context policy must define every accounting section root")
    roots: list[TmSectionRootPolicy] = []
    for index, raw_root in enumerate(raw_roots):
        root = _exact_mapping(
            raw_root,
            {"report_norm_id", "section", "canonical_name"},
            f"TM section root {index}",
        )
        roots.append(
            TmSectionRootPolicy(
                report_norm_id=_positive_id(
                    root["report_norm_id"], f"TM section root {index} ReportNormId"
                ),
                section=_required_text(root["section"], f"TM section root {index} section"),
                canonical_name=_required_text(
                    root["canonical_name"], f"TM section root {index} canonical name"
                ),
            )
        )
    if (
        tuple(root.report_norm_id for root in roots) != _SECTION_ROOT_IDS
        or tuple(root.section for root in roots) != _ACCOUNTING_SECTIONS
        or len({root.report_norm_id for root in roots}) != len(roots)
        or len({root.canonical_name for root in roots}) != len(roots)
    ):
        raise TmContextError("TM accounting section roots are duplicated or out of order")

    resolved = _exact_mapping(
        payload["resolved_context"],
        {"status", "mapping_eligible"},
        "TM resolved context",
    )
    if resolved["status"] != _RESOLVED_STATUS or resolved["mapping_eligible"] is not True:
        raise TmContextError("TM resolved-context behavior was weakened")

    raw_level_mismatches = payload["level_mismatch_items"]
    if not isinstance(raw_level_mismatches, list):
        raise TmContextError("TM level-mismatch quarantine must be a list")
    level_mismatches: list[TmLevelMismatchPolicy] = []
    for index, raw_level_mismatch in enumerate(raw_level_mismatches):
        mismatch = _exact_mapping(
            raw_level_mismatch,
            {
                "report_norm_id",
                "canonical_name",
                "expected_parent_report_norm_id",
                "expected_declared_hierarchy_level",
                "expected_derived_hierarchy_level",
                "status",
                "mapping_eligible",
            },
            f"TM level-mismatch item {index}",
        )
        declared_level = _optional_nonnegative_integer(
            mismatch["expected_declared_hierarchy_level"],
            f"TM level-mismatch item {index} expected declared level",
        )
        derived_level = _optional_nonnegative_integer(
            mismatch["expected_derived_hierarchy_level"],
            f"TM level-mismatch item {index} expected derived level",
        )
        if declared_level is None or derived_level is None:
            raise TmContextError("TM level-mismatch levels must be non-negative integers")
        level_mismatches.append(
            TmLevelMismatchPolicy(
                report_norm_id=_positive_id(
                    mismatch["report_norm_id"],
                    f"TM level-mismatch item {index} ReportNormId",
                ),
                canonical_name=_required_text(
                    mismatch["canonical_name"],
                    f"TM level-mismatch item {index} canonical name",
                ),
                expected_parent_report_norm_id=_positive_id(
                    mismatch["expected_parent_report_norm_id"],
                    f"TM level-mismatch item {index} expected parent",
                ),
                expected_declared_hierarchy_level=declared_level,
                expected_derived_hierarchy_level=derived_level,
                status=_required_text(mismatch["status"], f"TM level-mismatch item {index} status"),
                mapping_eligible=mismatch["mapping_eligible"],
            )
        )
    mismatch_shapes = tuple(
        (
            mismatch.report_norm_id,
            mismatch.expected_parent_report_norm_id,
            mismatch.expected_declared_hierarchy_level,
            mismatch.expected_derived_hierarchy_level,
        )
        for mismatch in level_mismatches
    )
    if mismatch_shapes != _LEVEL_MISMATCH_SHAPES or any(
        mismatch.status != _LEVEL_MISMATCH_STATUS or mismatch.mapping_eligible is not False
        for mismatch in level_mismatches
    ):
        raise TmContextError("TM level-mismatch quarantine policy is invalid")

    raw_orphans = payload["orphan_items"]
    if not isinstance(raw_orphans, list) or not raw_orphans:
        raise TmContextError("TM context policy must explicitly quarantine unresolved orphans")
    orphans: list[TmOrphanPolicy] = []
    for index, raw_orphan in enumerate(raw_orphans):
        orphan = _exact_mapping(
            raw_orphan,
            {
                "report_norm_id",
                "canonical_name",
                "expected_parent_report_norm_id",
                "expected_hierarchy_level",
                "status",
                "mapping_eligible",
            },
            f"TM orphan item {index}",
        )
        orphans.append(
            TmOrphanPolicy(
                report_norm_id=_positive_id(
                    orphan["report_norm_id"], f"TM orphan item {index} ReportNormId"
                ),
                canonical_name=_required_text(
                    orphan["canonical_name"], f"TM orphan item {index} canonical name"
                ),
                expected_parent_report_norm_id=(
                    None
                    if orphan["expected_parent_report_norm_id"] is None
                    else _positive_id(
                        orphan["expected_parent_report_norm_id"],
                        f"TM orphan item {index} expected parent",
                    )
                ),
                expected_hierarchy_level=_optional_nonnegative_integer(
                    orphan["expected_hierarchy_level"],
                    f"TM orphan item {index} expected hierarchy level",
                ),
                status=_required_text(orphan["status"], f"TM orphan item {index} status"),
                mapping_eligible=orphan["mapping_eligible"],
            )
        )
    if (
        tuple(orphan.report_norm_id for orphan in orphans) != _ORPHAN_IDS
        or len({orphan.report_norm_id for orphan in orphans}) != len(orphans)
        or {orphan.report_norm_id for orphan in orphans} & {root.report_norm_id for root in roots}
        or any(
            orphan.expected_parent_report_norm_id is not None
            or orphan.expected_hierarchy_level is not None
            or orphan.status != _ORPHAN_STATUS
            or orphan.mapping_eligible is not False
            for orphan in orphans
        )
    ):
        raise TmContextError("TM orphan quarantine policy is invalid")

    return TmContextPolicy(
        version=1,
        policy=_POLICY_NAME,
        statement_type=_STATEMENT_TYPE,
        order_authority=_ORDER_AUTHORITY,
        section_roots=tuple(roots),
        resolved_status=_RESOLVED_STATUS,
        resolved_mapping_eligible=True,
        level_mismatch_items=tuple(level_mismatches),
        orphan_items=tuple(orphans),
        source_path=path,
        source_sha256=sha256_bytes(source_bytes),
    )


def _validate_tm_order(items: Sequence[SchemaItem]) -> None:
    display_orders = [item.display_order for item in items]
    if display_orders != sorted(display_orders) or display_orders != list(range(len(items))):
        raise TmContextError(
            "TM schema items must be complete and ordered by contiguous workbook display order"
        )


def _validate_declared_children(
    tm_items: Sequence[SchemaItem],
    by_tm_id: Mapping[int, SchemaItem],
    by_global_id: Mapping[int, SchemaItem],
) -> None:
    expected: dict[int, list[int]] = {item.schema_id: [] for item in tm_items}
    for item in tm_items:
        if item.parent_id is None:
            continue
        parent = by_global_id.get(item.parent_id)
        if parent is None:
            raise TmContextError(
                f"TM ReportNormId {item.schema_id} has missing parent {item.parent_id}"
            )
        if parent.statement_type != _STATEMENT_TYPE:
            raise TmContextError(
                f"TM ReportNormId {item.schema_id} has cross-statement parent {item.parent_id}"
            )
        expected[item.parent_id].append(item.schema_id)
    for item in tm_items:
        declared = list(item.children)
        if len(declared) != len(set(declared)):
            raise TmContextError(f"TM ReportNormId {item.schema_id} repeats a declared child")
        for child_id in declared:
            child = by_global_id.get(child_id)
            if child is None:
                raise TmContextError(
                    f"TM ReportNormId {item.schema_id} has missing child {child_id}"
                )
            if child.statement_type != _STATEMENT_TYPE:
                raise TmContextError(
                    f"TM ReportNormId {item.schema_id} has cross-statement child {child_id}"
                )
            if child_id not in by_tm_id:
                raise TmContextError(f"TM child {child_id} is absent from the TM projection")
        if declared != expected[item.schema_id]:
            raise TmContextError(
                f"TM ReportNormId {item.schema_id} children differ from parent relationships"
            )


def build_tm_schema_context(
    schema_items: Sequence[SchemaItem],
    policy: TmContextPolicy,
) -> tuple[TmSchemaContext, ...]:
    """Derive an ordered, bank-independent TM context from an applied hierarchy."""

    if (
        policy.statement_type != _STATEMENT_TYPE
        or policy.order_authority != _ORDER_AUTHORITY
        or tuple(root.report_norm_id for root in policy.section_roots) != _SECTION_ROOT_IDS
        or tuple(root.section for root in policy.section_roots) != _ACCOUNTING_SECTIONS
        or tuple(
            (
                mismatch.report_norm_id,
                mismatch.expected_parent_report_norm_id,
                mismatch.expected_declared_hierarchy_level,
                mismatch.expected_derived_hierarchy_level,
            )
            for mismatch in policy.level_mismatch_items
        )
        != _LEVEL_MISMATCH_SHAPES
        or any(
            mismatch.status != _LEVEL_MISMATCH_STATUS or mismatch.mapping_eligible is not False
            for mismatch in policy.level_mismatch_items
        )
        or tuple(orphan.report_norm_id for orphan in policy.orphan_items) != _ORPHAN_IDS
        or any(
            orphan.expected_parent_report_norm_id is not None
            or orphan.expected_hierarchy_level is not None
            or orphan.status != _ORPHAN_STATUS
            or orphan.mapping_eligible is not False
            for orphan in policy.orphan_items
        )
        or policy.resolved_status != _RESOLVED_STATUS
        or policy.resolved_mapping_eligible is not True
    ):
        raise TmContextError("TM context policy is not mapping-safe")
    if not schema_items:
        raise TmContextError("schema has no items")
    global_ids = [item.schema_id for item in schema_items]
    if len(global_ids) != len(set(global_ids)):
        raise TmContextError("schema has globally duplicated ReportNormIds")
    by_global_id = {item.schema_id: item for item in schema_items}
    tm_items = [item for item in schema_items if item.statement_type == policy.statement_type]
    if not tm_items:
        raise TmContextError("schema has no TM items")
    _validate_tm_order(tm_items)
    by_tm_id = {item.schema_id: item for item in tm_items}
    _validate_declared_children(tm_items, by_tm_id, by_global_id)

    section_by_root_id = {root.report_norm_id: root for root in policy.section_roots}
    level_mismatch_by_id = {
        mismatch.report_norm_id: mismatch for mismatch in policy.level_mismatch_items
    }
    orphan_by_id = {orphan.report_norm_id: orphan for orphan in policy.orphan_items}
    for root in policy.section_roots:
        item = by_tm_id.get(root.report_norm_id)
        if item is None:
            raise TmContextError(f"TM accounting section root {root.report_norm_id} is missing")
        if (
            item.canonical_name != root.canonical_name
            or item.parent_id is not None
            or item.hierarchy_level != 0
        ):
            raise TmContextError(
                f"TM accounting section root {root.report_norm_id} identity drifted"
            )
    for mismatch in policy.level_mismatch_items:
        item = by_tm_id.get(mismatch.report_norm_id)
        if item is None:
            raise TmContextError(
                f"TM quarantined level mismatch {mismatch.report_norm_id} is missing"
            )
        if (
            item.canonical_name != mismatch.canonical_name
            or item.parent_id != mismatch.expected_parent_report_norm_id
            or item.hierarchy_level != mismatch.expected_declared_hierarchy_level
        ):
            raise TmContextError(
                f"TM quarantined level mismatch {mismatch.report_norm_id} identity drifted"
            )
    for orphan in policy.orphan_items:
        item = by_tm_id.get(orphan.report_norm_id)
        if item is None:
            raise TmContextError(f"TM quarantined orphan {orphan.report_norm_id} is missing")
        if (
            item.canonical_name != orphan.canonical_name
            or item.parent_id != orphan.expected_parent_report_norm_id
            or item.hierarchy_level != orphan.expected_hierarchy_level
            or item.children
        ):
            raise TmContextError(f"TM quarantined orphan {orphan.report_norm_id} drifted")

    path_cache: dict[int, tuple[int, ...]] = {}

    def ancestor_path(item: SchemaItem) -> tuple[int, ...]:
        cached = path_cache.get(item.schema_id)
        if cached is not None:
            return cached
        path: list[int] = []
        positions: dict[int, int] = {}
        current = item
        while True:
            if current.schema_id in positions:
                cycle = path[positions[current.schema_id] :] + [current.schema_id]
                raise TmContextError(f"TM hierarchy cycle detected: {cycle}")
            positions[current.schema_id] = len(path)
            path.append(current.schema_id)
            if current.parent_id is None:
                break
            parent = by_global_id.get(current.parent_id)
            if parent is None:
                raise TmContextError(
                    f"TM ReportNormId {current.schema_id} has missing parent {current.parent_id}"
                )
            if parent.statement_type != _STATEMENT_TYPE:
                raise TmContextError(
                    f"TM ReportNormId {current.schema_id} has cross-statement parent "
                    f"{current.parent_id}"
                )
            current = parent
        result = tuple(reversed(path))
        path_cache[item.schema_id] = result
        return result

    contexts: list[TmSchemaContext] = []
    for item in tm_items:
        path = ancestor_path(item)
        if item.schema_id in orphan_by_id:
            orphan = orphan_by_id[item.schema_id]
            contexts.append(
                TmSchemaContext(
                    report_norm_id=item.schema_id,
                    canonical_name=item.canonical_name,
                    statement_type=item.statement_type,
                    section=None,
                    section_root_id=None,
                    note_family_root_id=None,
                    ancestor_path=path,
                    parent_report_norm_id=item.parent_id,
                    hierarchy_level=item.hierarchy_level,
                    derived_hierarchy_level=None,
                    display_order=item.display_order,
                    context_status=orphan.status,
                    mapping_eligible=orphan.mapping_eligible,
                )
            )
            continue
        root = section_by_root_id.get(path[0])
        if root is None:
            raise TmContextError(
                f"TM ReportNormId {item.schema_id} does not descend from an accounting section"
            )
        if item.hierarchy_level is None or item.hierarchy_level < 0:
            raise TmContextError(f"TM ReportNormId {item.schema_id} lacks resolved hierarchy level")
        derived_hierarchy_level = len(path) - 1
        mismatch = level_mismatch_by_id.get(item.schema_id)
        if mismatch is not None:
            if derived_hierarchy_level != mismatch.expected_derived_hierarchy_level:
                raise TmContextError(
                    f"TM quarantined level mismatch {item.schema_id} derived level drifted"
                )
            context_status = mismatch.status
            mapping_eligible = mismatch.mapping_eligible
        else:
            if item.hierarchy_level != derived_hierarchy_level:
                raise TmContextError(
                    f"TM ReportNormId {item.schema_id} declared hierarchy level "
                    f"{item.hierarchy_level} does not match ancestor depth "
                    f"{derived_hierarchy_level}"
                )
            context_status = policy.resolved_status
            mapping_eligible = policy.resolved_mapping_eligible
        contexts.append(
            TmSchemaContext(
                report_norm_id=item.schema_id,
                canonical_name=item.canonical_name,
                statement_type=item.statement_type,
                section=root.section,
                section_root_id=root.report_norm_id,
                note_family_root_id=path[1] if len(path) > 1 else None,
                ancestor_path=path,
                parent_report_norm_id=item.parent_id,
                hierarchy_level=item.hierarchy_level,
                derived_hierarchy_level=derived_hierarchy_level,
                display_order=item.display_order,
                context_status=context_status,
                mapping_eligible=mapping_eligible,
            )
        )
    if len(contexts) != len(tm_items) or [item.display_order for item in contexts] != list(
        range(len(contexts))
    ):
        raise TmContextError("TM context projection denominator or order drifted")
    unresolved_count = len(orphan_by_id) + len(level_mismatch_by_id)
    if sum(not context.mapping_eligible for context in contexts) != unresolved_count:
        raise TmContextError("TM context mapping eligibility drifted")
    return tuple(contexts)


def tm_context_projection(
    contexts: Sequence[TmSchemaContext],
) -> tuple[dict[str, object], ...]:
    """Return the canonical JSON-compatible context projection in display order."""

    if [context.display_order for context in contexts] != list(range(len(contexts))):
        raise TmContextError("TM contexts are not in complete workbook display order")
    report_norm_ids = [context.report_norm_id for context in contexts]
    if len(report_norm_ids) != len(set(report_norm_ids)):
        raise TmContextError("TM context projection repeats a ReportNormId")
    return tuple(context.to_dict() for context in contexts)


def tm_context_projection_sha256(contexts: Sequence[TmSchemaContext]) -> str:
    """Hash the exact ordered context records with canonical JSON serialization."""

    return stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for record in tm_context_projection(contexts)
    )


__all__ = [
    "TM_CONTEXT_POLICY_RELATIVE_PATH",
    "TmContextError",
    "TmContextPolicy",
    "TmLevelMismatchPolicy",
    "TmOrphanPolicy",
    "TmSchemaContext",
    "TmSectionRootPolicy",
    "build_tm_schema_context",
    "load_tm_context_policy",
    "tm_context_projection",
    "tm_context_projection_sha256",
]
