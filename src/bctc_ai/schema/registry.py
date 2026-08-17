from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.mapping.lctt import (
    CashFlowRules,
    assign_cash_flow_schema_branches,
    load_cash_flow_rules,
)
from bctc_ai.schema.append_only import verify_tm_1944_append
from bctc_ai.schema.business_update import verify_business_schema_update
from bctc_ai.schema.xlsx_reader import read_rows

_SCHEMA_NAME = "UNIVERSAL_BANK_BCTC_SCHEMA"
_SCHEMA_STRATEGY = "SOURCE_EVIDENCE_DRIVEN_APPEND_ONLY_SUPERSET"
_BASE_PROJECTION_SHA256 = "e63b77ebf99907843bea419cef32bc64cd709129813f89309f3b42fc818a1b10"
_BASE_ORDERED_IDS_SHA256 = "5cc0e9ea70b23af236ce43b920838299dbc91e9c0ef19d31165f4ce49eea4f9f"
_BASE_WORKBOOKS = {
    "CDKT": (
        "template/Bank_CDKT_ReportNormId.xlsx",
        77,
        "a07ff47f7c41011fe4ca5a66681106d476586ded9013b5874cbb9f67a6ad8486",
    ),
    "KQKD": (
        "template/Bank_KQKD_ReportNormId.xlsx",
        24,
        "6033001b85a236fce4b29437d56cc02d7c6a21f95e82b43de043b1268eb74615",
    ),
    "LCTT": (
        "template/Bank_LCTT_ReportNormId.xlsx",
        107,
        "2c9d52737c492f115895eab9a571da2269fcfd3c3e77539ec581782e579d260a",
    ),
    "TM": (
        "template/Bank_TM_ReportNormId.xlsx",
        1385,
        "fa284e3af1f90c8a206308f63e6d35e77a9fbf1abcaf60abcb59877c47275140",
    ),
}
UNIVERSAL_TM_SCHEMA_ITEM_COUNT = 1719
_UNIVERSAL_COUNTS = {
    "CDKT": 99,
    "KQKD": 25,
    "LCTT": 110,
    "TM": UNIVERSAL_TM_SCHEMA_ITEM_COUNT,
}


def _base_ids(project_root: Path) -> set[int]:
    identifiers: set[int] = set()
    for statement, (relative, expected_count, expected_sha256) in _BASE_WORKBOOKS.items():
        path = project_root / relative
        if sha256_file(path) != expected_sha256:
            raise ValueError(f"{statement} BASE_SCHEMA workbook hash drifted: {path}")
        statement_ids = {
            int(raw_id)
            for row in read_rows(path)
            if (raw_id := row.get("B", "").strip()) and raw_id != "ReportNormId"
        }
        if len(statement_ids) != expected_count:
            raise ValueError(f"{statement} BASE_SCHEMA item count drifted: {path}")
        if identifiers & statement_ids:
            raise ValueError(f"{statement} BASE_SCHEMA contains globally reused ReportNormIds")
        identifiers.update(statement_ids)
    if len(identifiers) != 1593:
        raise ValueError("BASE_SCHEMA global item count drifted")
    return identifiers


def _validate_schema_contract(payload: dict[str, Any], project_root: Path) -> dict[str, object]:
    expected_base_workbooks = {
        statement: {"path": relative, "item_count": count, "sha256": digest}
        for statement, (relative, count, digest) in _BASE_WORKBOOKS.items()
    }
    expected_base = {
        "name": "BASE_SCHEMA",
        "item_count": 1593,
        "counts": {"CDKT": 77, "KQKD": 24, "LCTT": 107, "TM": 1385},
        "ordered_canonical_projection_sha256": _BASE_PROJECTION_SHA256,
        "ordered_report_norm_ids_sha256": _BASE_ORDERED_IDS_SHA256,
        "workbooks": expected_base_workbooks,
    }
    expected_universal = {
        "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6074",
        "item_count": 1953,
        "counts": _UNIVERSAL_COUNTS,
        "high_watermark": 6074,
    }
    if (
        payload.get("schema_name") != _SCHEMA_NAME
        or payload.get("schema_strategy") != _SCHEMA_STRATEGY
        or payload.get("base_schema") != expected_base
        or payload.get("universal_schema") != expected_universal
    ):
        raise ValueError("schema source universal/base contract drifted")
    _base_ids(project_root)
    return {
        "schema_name": _SCHEMA_NAME,
        "schema_strategy": _SCHEMA_STRATEGY,
        "base_schema": expected_base,
        "universal_schema": expected_universal,
    }


def load_schema_contract(project_root: Path) -> dict[str, object]:
    config_path = project_root / "config/schemas/sources.yaml"
    payload: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return _validate_schema_contract(payload, project_root.resolve())


@dataclass
class SchemaItem:
    schema_id: int
    canonical_name: str
    normalized_name: str
    statement_type: str
    display_order: int
    notes_section: str | None = None
    parent_id: int | None = None
    children: list[int] = field(default_factory=list)
    siblings: list[int] = field(default_factory=list)
    previous_id: int | None = None
    next_id: int | None = None
    allowed_period_type: list[str] = field(default_factory=list)
    allowed_unit: list[str] = field(default_factory=list)
    allowed_sign: list[str] = field(default_factory=lambda: ["POSITIVE", "NEGATIVE", "ZERO"])
    scope: list[str] = field(default_factory=lambda: ["SEPARATE", "CONSOLIDATED"])
    cash_flow_branch: str | None = None
    hierarchy_level: int | None = None
    hierarchy_source: str | None = None
    historical_aliases: list[str] = field(default_factory=list)
    historical_banks: list[str] = field(default_factory=list)
    structural_aliases: list[str] = field(default_factory=list)
    source_workbook: str = ""
    source_row: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SchemaWorkbook:
    path: str
    sha256: str
    statement_type: str
    item_count: int
    minimum_id: int
    maximum_id: int


def load_workbook(
    path: Path,
    project_root: Path,
    *,
    statement: str,
    cash_flow_rules: CashFlowRules,
) -> tuple[SchemaWorkbook, list[SchemaItem]]:
    items: list[SchemaItem] = []
    seen: set[int] = set()
    for row_number, row in enumerate(read_rows(path), start=1):
        raw_id = row.get("B", "").strip()
        if not raw_id or raw_id == "ReportNormId":
            continue
        try:
            schema_id = int(raw_id)
        except ValueError as exc:
            raise ValueError(f"non-integer ReportNormId at {path}:{row_number}") from exc
        if schema_id in seen:
            raise ValueError(f"duplicate ReportNormId {schema_id} in {path}")
        seen.add(schema_id)
        canonical = normalize_text(row.get("C", ""))
        if not canonical:
            raise ValueError(f"blank ReportNormName at {path}:{row_number}")
        item = SchemaItem(
            schema_id=schema_id,
            canonical_name=canonical,
            normalized_name=retrieval_key(canonical),
            statement_type=statement,
            display_order=len(items),
            previous_id=items[-1].schema_id if items else None,
            source_workbook=path.relative_to(project_root).as_posix(),
            source_row=row_number,
        )
        item.allowed_period_type = {
            "CDKT": ["SNAPSHOT"],
            "KQKD": ["DURATION"],
            "LCTT": ["DURATION"],
            "TM": ["SNAPSHOT", "DURATION"],
        }[statement]
        items.append(item)
    if statement == "LCTT":
        assignments = assign_cash_flow_schema_branches(
            [item.schema_id for item in items],
            cash_flow_rules,
        )
        for item in items:
            item.cash_flow_branch = assignments[item.schema_id].value
    for current, following in zip(items, items[1:], strict=False):
        current.next_id = following.schema_id
    workbook = SchemaWorkbook(
        path=path.relative_to(project_root).as_posix(),
        sha256=sha256_file(path),
        statement_type=statement,
        item_count=len(items),
        minimum_id=min(item.schema_id for item in items),
        maximum_id=max(item.schema_id for item in items),
    )
    return workbook, items


def load_all(
    template_root: Path, project_root: Path
) -> tuple[list[SchemaWorkbook], list[SchemaItem]]:
    config_path = project_root / "config/schemas/sources.yaml"
    payload: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    sources = payload.get("sources")
    if not isinstance(payload.get("version"), int) or not isinstance(sources, dict):
        raise ValueError(f"invalid schema source configuration: {config_path}")
    schema_contract = _validate_schema_contract(payload, project_root)
    if payload.get("append_only") is not True:
        raise ValueError(f"schema sources must remain append-only: {config_path}")
    raw_cash_flow_rules = payload.get("cash_flow_rules")
    if not isinstance(raw_cash_flow_rules, str) or not raw_cash_flow_rules:
        raise ValueError(f"schema source configuration has no cash_flow_rules: {config_path}")
    cash_flow_rules_path = (project_root / raw_cash_flow_rules).resolve()
    try:
        cash_flow_rules_path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"cash-flow rules escape project root: {config_path}") from exc
    cash_flow_rules = load_cash_flow_rules(cash_flow_rules_path)
    workbooks: list[SchemaWorkbook] = []
    all_items: list[SchemaItem] = []
    global_ids: dict[int, str] = {}
    configured_paths: set[Path] = set()
    for statement, relative_path in sources.items():
        if not isinstance(statement, str) or not isinstance(relative_path, str):
            raise ValueError(f"invalid schema source entry: {config_path}")
        path = (project_root / relative_path).resolve()
        configured_paths.add(path)
        if not path.is_file():
            raise FileNotFoundError(f"required schema workbook missing: {path}")
        workbook, items = load_workbook(
            path,
            project_root,
            statement=statement,
            cash_flow_rules=cash_flow_rules,
        )
        for item in items:
            if item.schema_id in global_ids:
                raise ValueError(
                    f"schema ID {item.schema_id} reused by {global_ids[item.schema_id]} and {item.statement_type}"
                )
            global_ids[item.schema_id] = item.statement_type
        workbooks.append(workbook)
        all_items.extend(items)
    expected_root = template_root.resolve()
    if any(expected_root not in path.parents for path in configured_paths):
        raise ValueError(f"schema source is outside configured template root: {config_path}")
    business_audits = payload.get("approved_business_update_audits", [])
    if not isinstance(business_audits, list) or not all(
        isinstance(relative, str) and relative for relative in business_audits
    ):
        raise ValueError(f"invalid approved business-update audit list: {config_path}")
    verified_business_audits: list[tuple[str, dict[str, object]]] = []
    for relative in business_audits:
        audit_path = (project_root / relative).resolve()
        try:
            audit_path.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"business-update audit escapes project root: {relative}") from exc
        verified_business_audits.append(
            (relative, verify_business_schema_update(project_root, audit_path))
        )
    append_audits = payload.get("approved_append_audits", [])
    if not isinstance(append_audits, list) or not all(
        isinstance(relative, str) and relative for relative in append_audits
    ):
        raise ValueError(f"invalid approved append audit list: {config_path}")
    for relative in append_audits:
        audit_path = (project_root / relative).resolve()
        try:
            audit_path.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"schema append audit escapes project root: {relative}") from exc
        # Q-BOOT-004 is the first append-only migration. Its verifier binds the
        # baseline workbook, unchanged prefix, authorized row and resulting hash.
        audit = verify_tm_1944_append(project_root, audit_path)
        appended = audit["appended_item"]
        matched = [
            item
            for item in all_items
            if item.statement_type == appended["statement_type"]
            and item.schema_id == appended["schema_id"]
        ]
        if len(matched) != 1 or matched[0].canonical_name != appended["canonical_name"]:
            raise ValueError(f"approved schema append is not loaded exactly: {relative}")
        # The approved append was the baseline workbook's final row. Every later
        # business-schema ADD is explicitly inserted before that preserved final
        # row, including complete new branches whose final display ordinals can
        # exceed the append's original ordinal after earlier insertions shift it.
        subsequent_insertions = sum(
            1
            for _, business_audit in verified_business_audits
            for change in business_audit["schema_changes"]
            if change["change"] == "ADD" and change["statement_type"] == appended["statement_type"]
        )
        expected_display_order = appended["display_order_zero_based"] + subsequent_insertions
        if matched[0].display_order != expected_display_order:
            raise ValueError(f"approved schema append order drift: {relative}")
    for relative, audit in verified_business_audits:
        for change in audit["schema_changes"]:
            if change["change"] == "ADD":
                matched = [
                    item
                    for item in all_items
                    if item.statement_type == change["statement_type"]
                    and item.schema_id == change["schema_id"]
                ]
                if len(matched) != 1 or matched[0].canonical_name != change["canonical_name"]:
                    raise ValueError(f"approved business schema item is not loaded: {relative}")
                applicable_scope = change.get("applicable_scope")
                if applicable_scope is not None:
                    if (
                        not isinstance(applicable_scope, list)
                        or not applicable_scope
                        or not all(
                            scope in {"SEPARATE", "CONSOLIDATED"} for scope in applicable_scope
                        )
                        or len(applicable_scope) != len(set(applicable_scope))
                    ):
                        raise ValueError(f"approved business schema scope is invalid: {relative}")
                    matched[0].scope = list(applicable_scope)
                expected_display_order = change.get("display_order_zero_based")
                if expected_display_order is not None:
                    if matched[0].display_order != expected_display_order:
                        raise ValueError(f"approved business schema order drift: {relative}")
                elif matched[0].previous_id != change.get("previous_schema_id") or matched[
                    0
                ].next_id != change.get("next_schema_id"):
                    raise ValueError(f"approved business schema anchors drift: {relative}")
            elif change["change"] == "CORRECT_DISPLAY_NAME":
                matched = [
                    item
                    for item in all_items
                    if item.statement_type == change["statement_type"]
                    and item.schema_id == change["schema_id"]
                ]
                if len(matched) != 1 or matched[0].canonical_name != change["after"]:
                    raise ValueError(f"approved display-name correction is not loaded: {relative}")
            else:
                raise ValueError(f"unknown approved business schema change: {relative}")
    base_identifiers = _base_ids(project_root)
    audited_additions = {
        int(change["schema_id"])
        for _, audit in verified_business_audits
        for change in audit["schema_changes"]
        if change["change"] == "ADD"
    }
    current_identifiers = {item.schema_id for item in all_items}
    if base_identifiers & audited_additions:
        raise ValueError("audited universal additions collide with BASE_SCHEMA")
    if current_identifiers != base_identifiers | audited_additions:
        raise ValueError("current universal schema is not BASE_SCHEMA plus audited additions")
    universal = schema_contract["universal_schema"]
    if not isinstance(universal, dict):
        raise ValueError("invalid universal schema contract")
    counts = {
        statement: sum(item.statement_type == statement for item in all_items)
        for statement in sources
    }
    if (
        len(all_items) != universal["item_count"]
        or counts != universal["counts"]
        or max(current_identifiers) != universal["high_watermark"]
    ):
        raise ValueError("loaded universal schema revision/count/high-watermark drifted")
    return workbooks, all_items
