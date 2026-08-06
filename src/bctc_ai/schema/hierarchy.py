from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.schema.xlsx_reader import read_rows


@dataclass(frozen=True)
class HierarchyItem:
    statement_type: str
    schema_id: int
    label: str
    level: int
    parent_id: int
    source_path: str
    source_row: int


@dataclass(frozen=True)
class HierarchyWorkbook:
    statement_type: str
    path: str
    sha256: str
    coverage: str
    item_count: int
    skipped_blank_rows: int
    non_id_labels: tuple[str, ...]
    schema_only_append_ids: tuple[int, ...]
    minimum_id: int
    maximum_id: int


@dataclass(frozen=True)
class HierarchyRegistry:
    version: int
    authority: str
    workbooks: tuple[HierarchyWorkbook, ...]
    item_count: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _integer(raw: str, *, field: str, path: Path, row_number: int) -> int:
    try:
        numeric = Decimal(raw.strip())
    except InvalidOperation as exc:
        raise ValueError(f"non-numeric {field} at {path}:{row_number}") from exc
    if numeric != numeric.to_integral_value():
        raise ValueError(f"non-integer {field} at {path}:{row_number}")
    return int(numeric)


def _load_source(
    path: Path,
    project_root: Path,
    statement_type: str,
    source_config: dict[str, Any],
) -> tuple[HierarchyWorkbook, list[HierarchyItem]]:
    columns = source_config.get("columns")
    if not isinstance(columns, dict) or set(columns) != {
        "label",
        "schema_id",
        "level",
        "parent_id",
    }:
        raise ValueError(f"invalid hierarchy columns for {statement_type}: {path}")
    rows = iter(read_rows(path))
    try:
        raw_header = next(rows)
    except StopIteration as exc:
        raise ValueError(f"empty hierarchy workbook: {path}") from exc
    header_to_letter = {
        normalize_text(value): letter
        for letter, value in raw_header.items()
        if normalize_text(value)
    }
    missing = [name for name in columns.values() if name not in header_to_letter]
    if missing:
        raise ValueError(f"missing hierarchy columns {missing} in {path}")

    result: list[HierarchyItem] = []
    skipped_blank_rows = 0
    non_id_labels: list[str] = []
    seen: set[int] = set()
    for row_number, raw_row in enumerate(rows, start=2):
        values = {
            logical_name: normalize_text(raw_row.get(header_to_letter[column_name], ""))
            for logical_name, column_name in columns.items()
        }
        if not any(values.values()):
            skipped_blank_rows += 1
            continue
        label = values["label"]
        raw_id = values["schema_id"]
        if not raw_id:
            if label and source_config.get("allow_labeled_rows_without_id") is True:
                non_id_labels.append(label)
                continue
            raise ValueError(f"hierarchy row has no schema ID at {path}:{row_number}")
        if not label:
            raise ValueError(f"hierarchy row has no label at {path}:{row_number}")
        schema_id = _integer(raw_id, field="schema ID", path=path, row_number=row_number)
        if schema_id in seen:
            raise ValueError(f"duplicate hierarchy schema ID {schema_id} in {path}")
        seen.add(schema_id)
        level = _integer(values["level"], field="level", path=path, row_number=row_number)
        parent_id = _integer(
            values["parent_id"],
            field="parent ID",
            path=path,
            row_number=row_number,
        )
        if level < 0:
            raise ValueError(f"negative hierarchy level at {path}:{row_number}")
        result.append(
            HierarchyItem(
                statement_type=statement_type,
                schema_id=schema_id,
                label=label,
                level=level,
                parent_id=parent_id,
                source_path=path.relative_to(project_root).as_posix(),
                source_row=row_number,
            )
        )

    ids = {item.schema_id for item in result}
    missing_parents = sorted({item.parent_id for item in result} - ids)
    if missing_parents:
        raise ValueError(f"hierarchy has missing parent IDs {missing_parents} in {path}")
    _reject_cycles(result, path)
    raw_schema_only_append_ids = source_config.get("schema_only_append_ids", [])
    if not isinstance(raw_schema_only_append_ids, list) or not all(
        isinstance(item, int) and item > 0 for item in raw_schema_only_append_ids
    ):
        raise ValueError(f"invalid schema-only append IDs for {statement_type}: {path}")
    if len(raw_schema_only_append_ids) != len(set(raw_schema_only_append_ids)):
        raise ValueError(f"duplicate schema-only append IDs for {statement_type}: {path}")
    workbook = HierarchyWorkbook(
        statement_type=statement_type,
        path=path.relative_to(project_root).as_posix(),
        sha256=sha256_file(path),
        coverage=str(source_config.get("coverage", "UNSPECIFIED")),
        item_count=len(result),
        skipped_blank_rows=skipped_blank_rows,
        non_id_labels=tuple(non_id_labels),
        schema_only_append_ids=tuple(raw_schema_only_append_ids),
        minimum_id=min(ids),
        maximum_id=max(ids),
    )
    return workbook, result


def _reject_cycles(items: list[HierarchyItem], path: Path) -> None:
    parents = {item.schema_id: item.parent_id for item in items}
    for start in parents:
        visited: set[int] = set()
        current = start
        while parents[current] != current:
            if current in visited:
                raise ValueError(f"hierarchy cycle containing {current} in {path}")
            visited.add(current)
            current = parents[current]


def _expected_ids(
    statement_type: str,
    coverage: str,
    schema: list[SchemaItem],
) -> set[int]:
    statement_items = [item for item in schema if item.statement_type == statement_type]
    if coverage == "FULL_STATEMENT":
        return {item.schema_id for item in statement_items}
    if coverage.startswith("BRANCH_"):
        branch = coverage.removeprefix("BRANCH_")
        return {item.schema_id for item in statement_items if item.cash_flow_branch == branch}
    raise ValueError(f"unsupported hierarchy coverage: {coverage}")


def load_hierarchy_reference(
    config_path: Path,
    project_root: Path,
    schema: list[SchemaItem],
) -> tuple[HierarchyRegistry, list[HierarchyItem]]:
    payload: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    version = payload.get("version")
    root = payload.get("root")
    sources = payload.get("sources")
    if not isinstance(version, int) or not isinstance(root, str) or not isinstance(sources, dict):
        raise ValueError(f"invalid hierarchy configuration: {config_path}")

    hierarchy_root = (project_root / root).resolve()
    workbooks: list[HierarchyWorkbook] = []
    all_items: list[HierarchyItem] = []
    for statement_type, source_config in sources.items():
        if not isinstance(statement_type, str) or not isinstance(source_config, dict):
            raise ValueError(f"invalid hierarchy source entry: {config_path}")
        relative_path = source_config.get("path")
        if not isinstance(relative_path, str):
            raise ValueError(f"hierarchy source has no path: {statement_type}")
        path = (hierarchy_root / relative_path).resolve()
        if hierarchy_root not in path.parents or not path.is_file():
            raise FileNotFoundError(f"required hierarchy workbook missing or out of root: {path}")
        workbook, items = _load_source(path, project_root, statement_type, source_config)
        full_expected = _expected_ids(statement_type, workbook.coverage, schema)
        schema_only_appends = set(workbook.schema_only_append_ids)
        statement_schema = {
            item.schema_id: item for item in schema if item.statement_type == statement_type
        }
        unknown_appends = schema_only_appends - set(statement_schema)
        if unknown_appends:
            raise ValueError(
                f"schema-only append IDs are absent from {statement_type}: {sorted(unknown_appends)}"
            )
        expected = full_expected - schema_only_appends
        actual = {item.schema_id for item in items}
        represented_appends = actual & schema_only_appends
        if represented_appends:
            raise ValueError(
                f"schema-only append IDs unexpectedly occur in hierarchy: {sorted(represented_appends)}"
            )
        if actual != expected:
            raise ValueError(
                f"hierarchy coverage mismatch for {statement_type}: "
                f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
            )
        workbooks.append(workbook)
        all_items.extend(items)

    has_schema_only_appends = any(workbook.schema_only_append_ids for workbook in workbooks)
    registry = HierarchyRegistry(
        version=version,
        authority=str(payload.get("authority", "UNSPECIFIED")),
        workbooks=tuple(workbooks),
        item_count=len(all_items),
        status=(
            "VALIDATED_SUPPORTING_REFERENCE_WITH_SCHEMA_ONLY_APPENDS"
            if has_schema_only_appends
            else "VALIDATED_SUPPORTING_REFERENCE"
        ),
    )
    return registry, all_items


def apply_hierarchy_reference(schema: list[SchemaItem], hierarchy: list[HierarchyItem]) -> None:
    """Attach validated supporting edges without changing schema IDs or display order."""
    by_key = {(item.statement_type, item.schema_id): item for item in schema}
    child_groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for reference in hierarchy:
        item = by_key[(reference.statement_type, reference.schema_id)]
        item.parent_id = None if reference.parent_id == reference.schema_id else reference.parent_id
        item.hierarchy_level = reference.level
        item.hierarchy_source = reference.source_path
        if retrieval_key(reference.label) != item.normalized_name:
            item.structural_aliases.append(reference.label)
        if item.parent_id is not None:
            child_groups[(item.statement_type, item.parent_id)].append(item.schema_id)

    for (statement_type, parent_id), children in child_groups.items():
        parent = by_key[(statement_type, parent_id)]
        parent.children = children
        for child_id in children:
            by_key[(statement_type, child_id)].siblings = [
                sibling_id for sibling_id in children if sibling_id != child_id
            ]
