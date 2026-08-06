from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import fitz
import yaml

from bctc_ai.core.contracts import DatasetRole, ValueStatus
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all
from bctc_ai.values.normalization import normalize_financial_cell

_AUTHORITY = "HUMAN_REVIEW_AUTHORITATIVE_FOR_HASH_BOUND_PDF_PAGES"
_DATA_AUTHORITY = "HUMAN_REVIEW_AUTHORITATIVE_FOR_CITED_SOURCE_HASH_AND_PAGE"
_STATUSES = tuple(status.value for status in ValueStatus)


class TemplateMembership(StrEnum):
    CURRENT_TARGET_TEMPLATE = "CURRENT_TARGET_TEMPLATE"
    OUTSIDE_CURRENT_TARGET_TEMPLATE = "OUTSIDE_CURRENT_TARGET_TEMPLATE"


@dataclass(frozen=True)
class ReviewedPeriodColumn:
    ordinal: int
    side: str
    role: str
    period_end: date
    raw_header: str


@dataclass(frozen=True)
class ReviewedPeriodMap:
    period_map_id: str
    statement_type: str
    unit: str
    applies_to_pages: tuple[int, ...]
    provenance: str
    columns: tuple[ReviewedPeriodColumn, ...]

    def column_for_role(self, role: str) -> ReviewedPeriodColumn:
        matches = [column for column in self.columns if column.role == role]
        if len(matches) != 1:
            raise ValueError(f"period map {self.period_map_id} does not have one {role} column")
        return matches[0]


@dataclass(frozen=True)
class ReviewedValue:
    raw_value: str
    normalized_numeric_value: Decimal


@dataclass(frozen=True)
class ReviewedDecision:
    document_key: str
    visible_row_id: str | None
    page: int
    statement_type: str
    reviewed_item_id: int
    template_membership: TemplateMembership
    canonical_name: str
    pdf_label: str | None
    period_map_id: str | None
    mapping_action: str
    value_status: ValueStatus
    current: ReviewedValue | None
    comparative: ReviewedValue | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ReviewedDocument:
    document_key: str
    bank: str
    scope: str
    source_path: str
    source_sha256: str
    size_bytes: int
    page_count: int
    period_maps: tuple[ReviewedPeriodMap, ...]
    decisions: tuple[ReviewedDecision, ...]

    @property
    def document_id(self) -> str:
        return f"sha256:{self.source_sha256}"


@dataclass(frozen=True)
class HumanReviewRegistry:
    version: int
    review_id: str
    policy_path: Path
    dataset_path: Path
    dataset_sha256: str
    target_schema_path: str
    target_schema_sha256: str
    documents: tuple[ReviewedDocument, ...]

    @property
    def decisions(self) -> tuple[ReviewedDecision, ...]:
        return tuple(decision for document in self.documents for decision in document.decisions)


@dataclass(frozen=True)
class ReviewedSourceVerification:
    document_key: str
    path: str
    present: bool
    hash_matches: bool | None
    size_matches: bool | None
    page_count_matches: bool | None


def _resolve_under_root(project_root: Path, relative_path: str) -> Path:
    path = (project_root / relative_path).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"human-review path escapes project root: {relative_path}") from exc
    return path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _load_policy(policy_path: Path, project_root: Path) -> tuple[dict[str, Any], Path]:
    payload: dict[str, Any] = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    safety = payload.get("safety")
    target_schema = payload.get("target_schema")
    if (
        payload.get("version") != 1
        or payload.get("authority") != _AUTHORITY
        or payload.get("required_dataset_role") != DatasetRole.CALIBRATION.value
        or payload.get("status_vocabulary") != list(_STATUSES)
        or not isinstance(safety, dict)
        or not isinstance(target_schema, dict)
    ):
        raise ValueError(f"invalid human-review policy identity: {policy_path}")
    forbidden = (
        "production_routing_allowed",
        "bank_or_page_hardcoding_allowed",
        "absent_row_can_be_zero",
        "outside_target_can_be_mapping_failure",
        "mongo_can_override_pdf",
        "numeric_id_order_allowed",
    )
    if any(safety.get(name) is not False for name in forbidden):
        raise ValueError(f"human-review policy weakens a safety invariant: {policy_path}")
    if safety.get("schema_order_source") != "TEMPLATE_WORKBOOK_ROW_ORDER":
        raise ValueError(
            f"human-review policy does not bind template workbook order: {policy_path}"
        )
    dataset = payload.get("dataset")
    dataset_sha256 = payload.get("dataset_sha256")
    if (
        not isinstance(dataset, str)
        or not isinstance(dataset_sha256, str)
        or len(dataset_sha256) != 64
    ):
        raise ValueError(f"human-review policy has no dataset: {policy_path}")
    dataset_path = _resolve_under_root(project_root, dataset)
    if sha256_file(dataset_path) != dataset_sha256:
        raise ValueError(f"human-review dataset hash drifted: {dataset_path}")
    return payload, dataset_path


def _date(raw: object, *, field: str) -> date:
    if not isinstance(raw, str):
        raise ValueError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {raw!r}") from exc


def _period_map(raw: object, *, document_key: str) -> ReviewedPeriodMap:
    if not isinstance(raw, dict):
        raise ValueError(f"invalid period map in {document_key}")
    raw_columns = raw.get("columns")
    raw_pages = raw.get("applies_to_pages")
    if not isinstance(raw_columns, list) or not isinstance(raw_pages, list):
        raise ValueError(f"period map has invalid columns/pages in {document_key}")
    columns = tuple(
        ReviewedPeriodColumn(
            ordinal=int(column["ordinal"]),
            side=str(column["side"]),
            role=str(column["role"]),
            period_end=_date(column["period_end"], field="period_end"),
            raw_header=str(column["raw_header"]),
        )
        for column in raw_columns
        if isinstance(column, dict)
    )
    if len(columns) != len(raw_columns):
        raise ValueError(f"period map contains a non-object column in {document_key}")
    if tuple(column.ordinal for column in columns) != tuple(range(len(columns))):
        raise ValueError(f"period columns are not in left-to-right ordinal order in {document_key}")
    if tuple(column.side for column in columns) != ("LEFT", "RIGHT"):
        raise ValueError("reviewed two-column map must explicitly identify LEFT then RIGHT")
    if {column.role for column in columns} != {"CURRENT", "COMPARATIVE"}:
        raise ValueError(f"reviewed period map lacks current/comparative roles in {document_key}")
    if any(not column.raw_header for column in columns):
        raise ValueError(f"reviewed period map lacks visible header text in {document_key}")
    pages = tuple(int(page) for page in raw_pages)
    if not pages or len(pages) != len(set(pages)) or any(page < 1 for page in pages):
        raise ValueError(f"invalid reviewed page list in {document_key}")
    return ReviewedPeriodMap(
        period_map_id=str(raw["period_map_id"]),
        statement_type=str(raw["statement_type"]),
        unit=str(raw["unit"]),
        applies_to_pages=pages,
        provenance=str(raw["provenance"]),
        columns=columns,
    )


def _reviewed_value(raw: object, *, field: str) -> ReviewedValue:
    if not isinstance(raw, dict) or not isinstance(raw.get("raw_value"), str):
        raise ValueError(f"invalid {field} reviewed value")
    return ReviewedValue(
        raw_value=raw["raw_value"],
        normalized_numeric_value=Decimal(str(raw["normalized_numeric_value"])),
    )


def _validate_cell(
    value: ReviewedValue,
    *,
    row_status: ValueStatus,
    membership: TemplateMembership,
) -> None:
    normalized = normalize_financial_cell(
        value.raw_value,
        row_visible=True,
        cell_geometry_verified=True,
        table_structure_verified=True,
        target_template_in_scope=membership is TemplateMembership.CURRENT_TARGET_TEMPLATE,
        mapping_ambiguous=row_status is ValueStatus.AMBIGUOUS_MAPPING,
        reference_available=row_status is not ValueStatus.REFERENCE_NOT_YET_BUILT,
    )
    if normalized.normalized_numeric_value != value.normalized_numeric_value:
        raise ValueError(
            f"reviewed raw/numeric mismatch: {value.raw_value!r} != {value.normalized_numeric_value}"
        )
    if normalized.value_status is not row_status:
        raise ValueError(
            f"reviewed status {row_status.value} conflicts with raw cell {value.raw_value!r}"
        )


def _decision(
    raw: object,
    *,
    document_key: str,
    document_scope: str,
    period_maps: dict[str, ReviewedPeriodMap],
    schema_by_id: dict[int, SchemaItem],
    all_schema_ids: set[int],
) -> ReviewedDecision:
    if not isinstance(raw, dict):
        raise ValueError(f"invalid reviewed decision in {document_key}")
    membership = TemplateMembership(str(raw["template_membership"]))
    status = ValueStatus(str(raw["value_status"]))
    item_id = int(raw["reviewed_item_id"])
    page = int(raw["page"])
    canonical = str(raw["canonical_name"])
    period_map_id = str(raw["period_map_id"]) if raw.get("period_map_id") else None
    current = _reviewed_value(raw["current"], field="current") if "current" in raw else None
    comparative = (
        _reviewed_value(raw["comparative"], field="comparative") if "comparative" in raw else None
    )

    if membership is TemplateMembership.CURRENT_TARGET_TEMPLATE:
        item = schema_by_id.get(item_id)
        if item is None:
            raise ValueError(f"reviewed current-template ID {item_id} is absent from target schema")
        if item.statement_type != str(raw["statement_type"]):
            raise ValueError(f"reviewed ID {item_id} has the wrong statement type")
        if document_scope not in item.scope:
            raise ValueError(f"reviewed ID {item_id} is incompatible with scope {document_scope}")
        if normalize_text(item.canonical_name).casefold() != normalize_text(canonical).casefold():
            raise ValueError(f"reviewed canonical name differs from target schema for ID {item_id}")
        for field, actual in (
            ("parent_id", item.parent_id),
            ("previous_id", item.previous_id),
            ("next_id", item.next_id),
        ):
            if field in raw and int(raw[field]) != actual:
                raise ValueError(
                    f"reviewed {field}={raw[field]} conflicts with template/hierarchy {actual} for {item_id}"
                )
    else:
        if item_id in all_schema_ids:
            raise ValueError(
                f"outside-target reviewed ID {item_id} collides with an existing ReportNormId"
            )
        if status is not ValueStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE:
            raise ValueError(f"outside-target item {item_id} has non-scope status {status.value}")

    if status is ValueStatus.NOT_OBSERVED:
        if current is not None or comparative is not None or raw.get("visible_row_id") is not None:
            raise ValueError(f"NOT_OBSERVED ID {item_id} cannot carry visible row/value evidence")
        if raw.get("mapping_action") != "NO_VISIBLE_ROW":
            raise ValueError(f"NOT_OBSERVED ID {item_id} requires NO_VISIBLE_ROW action")
    else:
        if not raw.get("visible_row_id") or current is None or comparative is None:
            raise ValueError(f"visible reviewed ID {item_id} requires row and two values")
        if period_map_id is None or period_map_id not in period_maps:
            raise ValueError(f"visible reviewed ID {item_id} has no valid period map")
        period_map = period_maps[period_map_id]
        if page not in period_map.applies_to_pages:
            raise ValueError(f"reviewed ID {item_id} page is outside its period map")
        if period_map.statement_type != str(raw["statement_type"]):
            raise ValueError(f"reviewed ID {item_id} period map has wrong statement type")
        _validate_cell(current, row_status=status, membership=membership)
        _validate_cell(comparative, row_status=status, membership=membership)

    known = {
        "visible_row_id",
        "page",
        "statement_type",
        "reviewed_item_id",
        "template_membership",
        "canonical_name",
        "pdf_label",
        "normalized_label",
        "period_map_id",
        "mapping_action",
        "value_status",
        "current",
        "comparative",
    }
    return ReviewedDecision(
        document_key=document_key,
        visible_row_id=str(raw["visible_row_id"]) if raw.get("visible_row_id") else None,
        page=page,
        statement_type=str(raw["statement_type"]),
        reviewed_item_id=item_id,
        template_membership=membership,
        canonical_name=canonical,
        pdf_label=str(raw["pdf_label"]) if raw.get("pdf_label") else None,
        period_map_id=period_map_id,
        mapping_action=str(raw["mapping_action"]),
        value_status=status,
        current=current,
        comparative=comparative,
        metadata={key: value for key, value in raw.items() if key not in known},
    )


def _registry_records_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        document_id = str(record.get("document_id", ""))
        if document_id in result:
            raise ValueError(f"duplicate document ID in supporting registry: {document_id}")
        result[document_id] = record
    return result


def load_human_review_registry(
    policy_path: Path,
    project_root: Path,
) -> HumanReviewRegistry:
    project_root = project_root.resolve()
    policy_path = policy_path.resolve()
    policy, dataset_path = _load_policy(policy_path, project_root)
    target = policy["target_schema"]
    target_schema_path = _resolve_under_root(project_root, str(target["path"]))
    if sha256_file(target_schema_path) != str(target["sha256"]):
        raise ValueError("human-review target schema hash drifted")

    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    schema_by_id = {
        item.schema_id: item for item in schema if item.statement_type == target["statement_type"]
    }
    all_schema_ids = {item.schema_id for item in schema}
    payload: dict[str, Any] = yaml.safe_load(dataset_path.read_text(encoding="utf-8")) or {}
    raw_documents = payload.get("documents")
    if (
        payload.get("version") != 1
        or payload.get("authority") != _DATA_AUTHORITY
        or payload.get("source_page_numbering") != "PDF_ONE_BASED"
        or not isinstance(payload.get("review_id"), str)
        or not isinstance(raw_documents, list)
    ):
        raise ValueError(f"invalid human-review dataset identity: {dataset_path}")

    source_registry = _read_jsonl(_resolve_under_root(project_root, str(policy["source_registry"])))
    role_registry = _registry_records_by_id(
        _read_jsonl(_resolve_under_root(project_root, str(policy["dataset_role_registry"])))
    )
    documents: list[ReviewedDocument] = []
    seen_document_keys: set[str] = set()
    seen_document_hashes: set[str] = set()
    for raw_document in raw_documents:
        if not isinstance(raw_document, dict) or not isinstance(raw_document.get("source"), dict):
            raise ValueError("human-review document is not an object")
        document_key = str(raw_document["document_key"])
        source = raw_document["source"]
        source_hash = str(source["sha256"])
        document_id = f"sha256:{source_hash}"
        if document_key in seen_document_keys or source_hash in seen_document_hashes:
            raise ValueError(f"duplicate reviewed document identity: {document_key}")
        seen_document_keys.add(document_key)
        seen_document_hashes.add(source_hash)
        source_matches = [
            record
            for record in source_registry
            if record.get("document_id") == document_id
            and record.get("relative_path") == source["path"]
        ]
        source_record = source_matches[0] if len(source_matches) == 1 else None
        if (
            source_record is None
            or source_record.get("relative_path") != source["path"]
            or source_record.get("sha256") != source_hash
            or int(source_record.get("size_bytes", -1)) != int(source["size_bytes"])
        ):
            raise ValueError(
                f"reviewed source is not identity-bound in source registry: {document_key}"
            )
        role_record = role_registry.get(document_id)
        if (
            role_record is None
            or role_record.get("dataset_role") != DatasetRole.CALIBRATION.value
            or role_record.get("source_path") != source["path"]
            or role_record.get("immutable") is not True
        ):
            raise ValueError(f"reviewed source is not frozen as CALIBRATION: {document_key}")

        raw_period_maps = raw_document.get("period_maps")
        raw_decisions = raw_document.get("decisions")
        if not isinstance(raw_period_maps, list) or not isinstance(raw_decisions, list):
            raise ValueError(f"reviewed document lacks period maps/decisions: {document_key}")
        period_maps = tuple(_period_map(raw, document_key=document_key) for raw in raw_period_maps)
        period_by_id = {period.period_map_id: period for period in period_maps}
        if len(period_by_id) != len(period_maps):
            raise ValueError(f"duplicate period map IDs in {document_key}")
        decisions = tuple(
            _decision(
                raw,
                document_key=document_key,
                document_scope=str(raw_document["scope"]),
                period_maps=period_by_id,
                schema_by_id=schema_by_id,
                all_schema_ids=all_schema_ids,
            )
            for raw in raw_decisions
        )
        item_ids = [decision.reviewed_item_id for decision in decisions]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError(f"duplicate reviewed item ID within {document_key}")
        row_ids = [decision.visible_row_id for decision in decisions if decision.visible_row_id]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError(f"one visible row is assigned more than once in {document_key}")
        page_count = int(source["page_count"])
        if any(decision.page > page_count for decision in decisions):
            raise ValueError(f"reviewed page exceeds PDF page count in {document_key}")
        documents.append(
            ReviewedDocument(
                document_key=document_key,
                bank=str(raw_document["bank"]),
                scope=str(raw_document["scope"]),
                source_path=str(source["path"]),
                source_sha256=source_hash,
                size_bytes=int(source["size_bytes"]),
                page_count=page_count,
                period_maps=period_maps,
                decisions=decisions,
            )
        )

    return HumanReviewRegistry(
        version=1,
        review_id=str(payload["review_id"]),
        policy_path=policy_path,
        dataset_path=dataset_path,
        dataset_sha256=str(policy["dataset_sha256"]),
        target_schema_path=str(target["path"]),
        target_schema_sha256=str(target["sha256"]),
        documents=tuple(documents),
    )


def verify_human_review_source_files(
    registry: HumanReviewRegistry,
    project_root: Path,
    *,
    require_present: bool,
) -> tuple[ReviewedSourceVerification, ...]:
    project_root = project_root.resolve()
    results: list[ReviewedSourceVerification] = []
    for document in registry.documents:
        path = _resolve_under_root(project_root, document.source_path)
        if not path.is_file():
            if require_present:
                raise FileNotFoundError(path)
            results.append(
                ReviewedSourceVerification(
                    document.document_key,
                    document.source_path,
                    False,
                    None,
                    None,
                    None,
                )
            )
            continue
        size_matches = path.stat().st_size == document.size_bytes
        hash_matches = sha256_file(path) == document.source_sha256
        with fitz.open(path) as pdf:
            page_count_matches = pdf.page_count == document.page_count
        if not (size_matches and hash_matches and page_count_matches):
            raise ValueError(f"reviewed source identity drifted: {document.document_key}")
        results.append(
            ReviewedSourceVerification(
                document.document_key,
                document.source_path,
                True,
                hash_matches,
                size_matches,
                page_count_matches,
            )
        )
    return tuple(results)
