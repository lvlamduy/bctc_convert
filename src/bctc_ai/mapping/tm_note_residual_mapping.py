"""Fail-closed reconciliation for the final non-page-owned TM schema items."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.registry import UNIVERSAL_TM_SCHEMA_ITEM_COUNT, SchemaItem

TM_RESIDUAL_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-residual-v1.yaml")
TM_RESIDUAL_SCHEMA_TOTAL = UNIVERSAL_TM_SCHEMA_ITEM_COUNT
TM_RESIDUAL_BASELINE_SCHEMA_TOTAL = 1_717
TM_RESIDUAL_BASELINE_SCHEMA_HIGH_WATERMARK = 6_072
TM_RESIDUAL_SCOPE_SCHEMA_COUNT = 94
TM_RESIDUAL_MAPPED_SCHEMA_COUNT = 2
TM_RESIDUAL_NOT_OBSERVED_SCHEMA_COUNT = 92
TM_RESIDUAL_STRUCTURAL_EVIDENCE_COUNT = 2
TM_RESIDUAL_FINANCIAL_SLOT_COUNT = 0
TM_RESIDUAL_MAPPED_ASSIGNMENT_COUNT = 0
TM_RESIDUAL_EXTRACTION_MISS_COUNT = 0

TM_RESIDUAL_MAPPED_IDS = frozenset({560, 1259})
TM_RESIDUAL_NOT_OBSERVED_IDS = frozenset(
    {
        564,
        566,
        567,
        568,
        573,
        584,
        587,
        589,
        591,
        1255,
        1256,
        1257,
        1258,
        *range(1260, 1269),
        *range(1280, 1294),
        *range(1305, 1352),
        *range(6061, 6066),
        6069,
        6070,
        6071,
        6072,
    }
)
TM_RESIDUAL_SCOPE_IDS = TM_RESIDUAL_MAPPED_IDS | TM_RESIDUAL_NOT_OBSERVED_IDS

TM_BASELINE_FINAL_MAPPED_SCHEMA_COUNT = 890
TM_BASELINE_FINAL_UNRESOLVED_SCHEMA_COUNT = 0
TM_BASELINE_FINAL_NOT_OBSERVED_SCHEMA_COUNT = 804
TM_BASELINE_FINAL_NOT_APPLICABLE_SCHEMA_COUNT = 23

_EXPECTED_CANONICAL_NAMES = {
    560: "I. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG CÂN ĐỐI KẾ TOÁN",
    1259: "IV. MỘT SỐ THÔNG TIN KHÁC",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value",
    "numeric_value_magnitude",
    "accounting_equation_result",
    "period_or_unit_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "source_row_or_financial_slot_reassignment",
    "schema_id_outside_exact_residual_scope",
}


class TMResidualMappingError(ValueError):
    pass


class TMResidualSchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNRESOLVED = "UNRESOLVED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


@dataclass(frozen=True)
class TMResidualEvidenceRule:
    report_norm_id: int
    page_number: int
    page_tag: str
    fixture_path: Path
    fixture_sha256: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    line_indices: tuple[int, ...]
    visible_label_anchor: str
    minimum_visible_label_similarity: float
    source_id: str
    source_role: str


@dataclass(frozen=True)
class TMResidualMappingPolicy:
    source_path: Path
    document: str
    report_scope: str
    mapping_authority_scope: str
    schema_workbook_sha256: str
    schema_projection_sha256: str
    schema_total: int
    scope_schema_total: int
    mapped_structural_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    structural_evidence: tuple[TMResidualEvidenceRule, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMResidualStructuralEvidence:
    report_norm_id: int
    canonical_name: str
    page_number: int
    page_tag: str
    source_id: str
    source_role: str
    line_indices: tuple[int, ...]
    visible_label: str
    visible_label_similarity: float
    bbox: tuple[int, int, int, int]
    minimum_ocr_score: float
    value_status: str
    source_fixture_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str


@dataclass(frozen=True)
class TMResidualSchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMOwnedSchemaPartition:
    owner_scope: str
    mapped_ids: frozenset[int]
    unresolved_ids: frozenset[int]
    not_observed_ids: frozenset[int]
    not_applicable_ids: frozenset[int]

    @property
    def scope_ids(self) -> frozenset[int]:
        return frozenset(
            self.mapped_ids | self.unresolved_ids | self.not_observed_ids | self.not_applicable_ids
        )


@dataclass(frozen=True)
class TMFullSchemaPartition:
    schema_item_count: int
    owner_scope_count: int
    mapped_schema_count: int
    unresolved_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    unassessed_schema_count: int
    ownership_sha256: str


@dataclass(frozen=True)
class TMResidualMappingResult:
    statement_type: str
    document: str
    report_scope: str
    status: str
    mapping_authority_scope: str
    mapping_authority_granted: bool
    schema_item_count: int
    status_reconciled_schema_count: int
    mapped_schema_count: int
    not_observed_schema_count: int
    ambiguous_schema_count: int
    unresolved_schema_count: int
    not_applicable_schema_count: int
    extraction_miss_schema_count: int
    unassessed_schema_count: int
    structural_evidence_count: int
    source_row_count_delta: int
    financial_slot_count: int
    mapped_assignment_count: int
    schema_dispositions: tuple[TMResidualSchemaDisposition, ...]
    structural_evidence: tuple[TMResidualStructuralEvidence, ...]
    schema_workbook_sha256: str
    schema_projection_sha256: str
    policy_sha256: str

    @property
    def owned_partition(self) -> TMOwnedSchemaPartition:
        ids_by_status = {
            status: frozenset(
                item.report_norm_id for item in self.schema_dispositions if item.status == status
            )
            for status in (item.value for item in TMResidualSchemaStatus)
        }
        return TMOwnedSchemaPartition(
            owner_scope=self.mapping_authority_scope,
            mapped_ids=ids_by_status[TMResidualSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value],
            unresolved_ids=ids_by_status[TMResidualSchemaStatus.UNRESOLVED.value],
            not_observed_ids=ids_by_status[TMResidualSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value],
            not_applicable_ids=frozenset(),
        )


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise TMResidualMappingError(f"TM residual policy field {key} must be a mapping")
    return value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TMResidualMappingError(f"TM residual policy field {key} must be a string")
    return value.strip()


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TMResidualMappingError(f"TM residual policy field {key} must be an integer")
    return value


def _expand_schema_ids(raw: object) -> tuple[int, ...]:
    if not isinstance(raw, list):
        raise TMResidualMappingError("TM residual schema IDs must be a list")
    result: list[int] = []
    for entry in raw:
        if isinstance(entry, int) and not isinstance(entry, bool):
            result.append(entry)
            continue
        if isinstance(entry, dict):
            start = entry.get("start")
            end = entry.get("end")
            if (
                isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
                and start <= end
            ):
                result.extend(range(start, end + 1))
                continue
        raise TMResidualMappingError("TM residual schema ID entry is invalid")
    if len(result) != len(set(result)):
        raise TMResidualMappingError("TM residual schema IDs contain duplicates")
    return tuple(result)


def load_tm_residual_mapping_policy(path: Path) -> TMResidualMappingPolicy:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TMResidualMappingError("TM residual policy must be a mapping")
    if (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_RESIDUAL_RECONCILIATION_V1"
        or payload.get("statement_type") != "TM"
    ):
        raise TMResidualMappingError("TM residual policy identity drifted")
    hashes = tuple(
        _required_string(payload, key)
        for key in ("schema_workbook_sha256", "schema_projection_sha256")
    )
    if any(not _SHA256.fullmatch(value) for value in hashes):
        raise TMResidualMappingError("TM residual schema hash is invalid")
    mapped_ids = _expand_schema_ids(payload.get("mapped_structural_schema_ids"))
    not_observed_ids = _expand_schema_ids(payload.get("not_observed_schema_ids"))
    raw_evidence = payload.get("structural_evidence")
    if not isinstance(raw_evidence, list) or len(raw_evidence) != 2:
        raise TMResidualMappingError("TM residual structural evidence is incomplete")
    evidence: list[TMResidualEvidenceRule] = []
    for raw in raw_evidence:
        if not isinstance(raw, dict):
            raise TMResidualMappingError("TM residual structural evidence entry is invalid")
        fixture_path = Path(_required_string(raw, "fixture_path"))
        line_indices = _expand_schema_ids(raw.get("line_indices"))
        record_hashes = tuple(
            _required_string(raw, key)
            for key in (
                "fixture_sha256",
                "source_pdf_sha256",
                "source_render_sha256",
                "source_ocr_sha256",
            )
        )
        similarity = raw.get("minimum_visible_label_similarity")
        if (
            any(not _SHA256.fullmatch(value) for value in record_hashes)
            or not isinstance(similarity, (int, float))
            or isinstance(similarity, bool)
            or not 0.9 <= float(similarity) <= 1.0
            or fixture_path.is_absolute()
            or ".." in fixture_path.parts
        ):
            raise TMResidualMappingError("TM residual structural evidence contract is invalid")
        evidence.append(
            TMResidualEvidenceRule(
                report_norm_id=_required_int(raw, "report_norm_id"),
                page_number=_required_int(raw, "page_number"),
                page_tag=_required_string(raw, "page_tag"),
                fixture_path=fixture_path,
                fixture_sha256=record_hashes[0],
                source_pdf_sha256=record_hashes[1],
                source_render_sha256=record_hashes[2],
                source_ocr_sha256=record_hashes[3],
                line_indices=line_indices,
                visible_label_anchor=_required_string(raw, "visible_label_anchor"),
                minimum_visible_label_similarity=float(similarity),
                source_id=_required_string(raw, "source_id"),
                source_role=_required_string(raw, "source_role"),
            )
        )
    forbidden = payload.get("forbidden_mapping_inputs")
    if (
        not isinstance(forbidden, list)
        or any(not isinstance(item, str) or not item for item in forbidden)
        or set(forbidden) != _REQUIRED_FORBIDDEN
    ):
        raise TMResidualMappingError("TM residual forbidden-input contract drifted")
    policy = TMResidualMappingPolicy(
        source_path=path,
        document=_required_string(payload, "document"),
        report_scope=_required_string(payload, "report_scope"),
        mapping_authority_scope=_required_string(payload, "mapping_authority_scope"),
        schema_workbook_sha256=hashes[0],
        schema_projection_sha256=hashes[1],
        schema_total=_required_int(payload, "schema_total"),
        scope_schema_total=_required_int(payload, "scope_schema_total"),
        mapped_structural_schema_ids=mapped_ids,
        not_observed_schema_ids=not_observed_ids,
        structural_evidence=tuple(evidence),
        forbidden_mapping_inputs=tuple(forbidden),
        policy_sha256=sha256_file(path),
    )
    if (
        policy.schema_total != TM_RESIDUAL_SCHEMA_TOTAL
        or policy.scope_schema_total != TM_RESIDUAL_SCOPE_SCHEMA_COUNT
        or frozenset(policy.mapped_structural_schema_ids) != TM_RESIDUAL_MAPPED_IDS
        or frozenset(policy.not_observed_schema_ids) != TM_RESIDUAL_NOT_OBSERVED_IDS
        or {item.report_norm_id for item in policy.structural_evidence} != TM_RESIDUAL_MAPPED_IDS
        or {item.page_number for item in policy.structural_evidence} != {30, 51}
        or {item.source_id for item in policy.structural_evidence}
        != {
            "page-0030:section-title",
            "page-0051:off_balance_commitments:row-0001",
        }
        or any(item.line_indices != (0, 1) for item in policy.structural_evidence)
        or any(item.source_role != "STATEMENT_SECTION_TITLE" for item in policy.structural_evidence)
        or policy.mapping_authority_scope != "MBB_CONSOLIDATED_Q1_2026_EXACT_RESIDUAL_94_ONLY"
        or policy.report_scope != "CONSOLIDATED"
    ):
        raise TMResidualMappingError("TM residual exact scope contract drifted")
    return policy


def _schema_projection_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [
        (
            item.schema_id,
            item.display_order,
            item.canonical_name,
            item.parent_id,
            tuple(item.children),
        )
        for item in items
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_structural_evidence(
    rule: TMResidualEvidenceRule,
    *,
    project_root: Path,
    canonical_name: str,
) -> TMResidualStructuralEvidence:
    fixture_path = (project_root / rule.fixture_path).resolve()
    if project_root.resolve() not in fixture_path.parents or not fixture_path.is_file():
        raise TMResidualMappingError("TM residual evidence fixture escapes the project root")
    if sha256_file(fixture_path) != rule.fixture_sha256:
        raise TMResidualMappingError("TM residual evidence fixture hash drifted")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TMResidualMappingError("TM residual evidence fixture must be an object")
    texts = payload.get("rec_texts")
    boxes = payload.get("rec_boxes")
    scores = payload.get("rec_scores")
    if (
        not isinstance(texts, list)
        or not isinstance(boxes, list)
        or not isinstance(scores, list)
        or not len(texts) == len(boxes) == len(scores)
        or payload.get("source_pdf_sha256") != rule.source_pdf_sha256
        or payload.get("source_render_sha256") != rule.source_render_sha256
        or payload.get("source_ocr_sha256") != rule.source_ocr_sha256
    ):
        raise TMResidualMappingError("TM residual evidence fixture identity drifted")
    try:
        selected_texts = tuple(texts[index] for index in rule.line_indices)
        selected_boxes = tuple(boxes[index] for index in rule.line_indices)
        selected_scores = tuple(scores[index] for index in rule.line_indices)
    except IndexError as exc:
        raise TMResidualMappingError("TM residual evidence line index is absent") from exc
    if (
        any(not isinstance(text, str) or not text.strip() for text in selected_texts)
        or any(
            not isinstance(box, list)
            or len(box) != 4
            or any(not isinstance(value, int) for value in box)
            for box in selected_boxes
        )
        or any(
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 < float(score) <= 1
            for score in selected_scores
        )
    ):
        raise TMResidualMappingError("TM residual structural evidence geometry is invalid")
    visible_label = " ".join(text.strip() for text in selected_texts)
    similarity = ratio(retrieval_key(visible_label), retrieval_key(rule.visible_label_anchor)) / 100
    if similarity < rule.minimum_visible_label_similarity:
        raise TMResidualMappingError("TM residual structural heading anchor failed")
    return TMResidualStructuralEvidence(
        report_norm_id=rule.report_norm_id,
        canonical_name=canonical_name,
        page_number=rule.page_number,
        page_tag=rule.page_tag,
        source_id=rule.source_id,
        source_role=rule.source_role,
        line_indices=rule.line_indices,
        visible_label=visible_label,
        visible_label_similarity=round(similarity, 6),
        bbox=(
            min(box[0] for box in selected_boxes),
            min(box[1] for box in selected_boxes),
            max(box[2] for box in selected_boxes),
            max(box[3] for box in selected_boxes),
        ),
        minimum_ocr_score=round(min(float(score) for score in selected_scores), 6),
        value_status="STRUCTURAL_HEADING_NO_VALUE_NO_FINANCIAL_SLOT",
        source_fixture_sha256=rule.fixture_sha256,
        source_render_sha256=rule.source_render_sha256,
        source_ocr_sha256=rule.source_ocr_sha256,
    )


def reconcile_tm_residual_items(
    schema: Sequence[SchemaItem],
    *,
    policy: TMResidualMappingPolicy,
    project_root: Path,
    source_pdf_path: Path,
    schema_workbook_path: Path,
    existing_owned_schema_ids: Collection[int],
) -> TMResidualMappingResult:
    if (
        policy.schema_total != TM_RESIDUAL_SCHEMA_TOTAL
        or policy.scope_schema_total != TM_RESIDUAL_SCOPE_SCHEMA_COUNT
        or frozenset(policy.mapped_structural_schema_ids) != TM_RESIDUAL_MAPPED_IDS
        or frozenset(policy.not_observed_schema_ids) != TM_RESIDUAL_NOT_OBSERVED_IDS
        or {item.report_norm_id for item in policy.structural_evidence} != TM_RESIDUAL_MAPPED_IDS
        or any(item.source_role != "STATEMENT_SECTION_TITLE" for item in policy.structural_evidence)
        or set(policy.forbidden_mapping_inputs) != _REQUIRED_FORBIDDEN
        or policy.mapping_authority_scope != "MBB_CONSOLIDATED_Q1_2026_EXACT_RESIDUAL_94_ONLY"
    ):
        raise TMResidualMappingError("TM residual in-memory policy contract drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if (
        len(tm_schema) != TM_RESIDUAL_SCHEMA_TOTAL
        or [item.display_order for item in tm_schema] != list(range(TM_RESIDUAL_SCHEMA_TOTAL))
        or len({item.schema_id for item in tm_schema}) != len(tm_schema)
    ):
        raise TMResidualMappingError("TM residual schema denominator/order drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    existing_owned_ids = set(existing_owned_schema_ids)
    if existing_owned_ids - set(schema_by_id):
        raise TMResidualMappingError("TM existing page owner references an unknown schema ID")
    if existing_owned_ids & TM_RESIDUAL_SCOPE_IDS:
        raise TMResidualMappingError("TM residual scope overlaps an existing page owner")
    baseline_ids = frozenset(
        item.schema_id
        for item in tm_schema
        if item.schema_id <= TM_RESIDUAL_BASELINE_SCHEMA_HIGH_WATERMARK
    )
    append_only_ids = frozenset(schema_by_id) - baseline_ids
    unclaimed_ids = frozenset(schema_by_id) - existing_owned_ids - TM_RESIDUAL_SCOPE_IDS
    if (
        len(baseline_ids) != TM_RESIDUAL_BASELINE_SCHEMA_TOTAL
        or not unclaimed_ids <= append_only_ids
    ):
        raise TMResidualMappingError(
            "TM legacy page ownership drifted outside the append-only schema quarantine"
        )
    extension_unresolved_ids = unclaimed_ids
    if (
        any(schema_id not in schema_by_id for schema_id in TM_RESIDUAL_SCOPE_IDS)
        or any(
            schema_by_id[schema_id].canonical_name != canonical_name
            for schema_id, canonical_name in _EXPECTED_CANONICAL_NAMES.items()
        )
        or sha256_file(source_pdf_path)
        != next(iter({item.source_pdf_sha256 for item in policy.structural_evidence}))
        or sha256_file(schema_workbook_path) != policy.schema_workbook_sha256
        or _schema_projection_hash(tm_schema) != policy.schema_projection_sha256
    ):
        raise TMResidualMappingError("TM residual source/schema identity drifted")
    evidence = tuple(
        _load_structural_evidence(
            rule,
            project_root=project_root,
            canonical_name=schema_by_id[rule.report_norm_id].canonical_name,
        )
        for rule in policy.structural_evidence
    )
    source_by_schema = {item.report_norm_id: item.source_id for item in evidence}
    dispositions = tuple(
        TMResidualSchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMResidualSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in TM_RESIDUAL_MAPPED_IDS
                else TMResidualSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
                if item.schema_id in TM_RESIDUAL_NOT_OBSERVED_IDS
                else TMResidualSchemaStatus.UNRESOLVED.value
                if item.schema_id in extension_unresolved_ids
                else TMResidualSchemaStatus.UNASSESSED.value
            ),
            source_ids=(source_by_schema[item.schema_id],)
            if item.schema_id in source_by_schema
            else (),
            reason=(
                "visible section-title semantics and page context uniquely bind this legacy "
                "schema root; the source is structural-only"
                if item.schema_id in TM_RESIDUAL_MAPPED_IDS
                else "explicit residual schema item is not visible anywhere in this PDF"
                if item.schema_id in TM_RESIDUAL_NOT_OBSERVED_IDS
                else "append-only schema item has no Q1-2026 page-family owner yet"
                if item.schema_id in extension_unresolved_ids
                else "owned by another page scope or an existing unresolved partition"
            ),
        )
        for item in tm_schema
    )
    result = TMResidualMappingResult(
        statement_type="TM",
        document=policy.document,
        report_scope=policy.report_scope,
        status="BASE_RESIDUAL_RECONCILED_WITH_APPEND_ONLY_SCHEMA_QUARANTINE",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=(
            TM_RESIDUAL_SCOPE_SCHEMA_COUNT + len(extension_unresolved_ids)
        ),
        mapped_schema_count=TM_RESIDUAL_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=TM_RESIDUAL_NOT_OBSERVED_SCHEMA_COUNT,
        ambiguous_schema_count=0,
        unresolved_schema_count=len(extension_unresolved_ids),
        not_applicable_schema_count=0,
        extraction_miss_schema_count=TM_RESIDUAL_EXTRACTION_MISS_COUNT,
        unassessed_schema_count=(
            TM_RESIDUAL_SCHEMA_TOTAL
            - TM_RESIDUAL_SCOPE_SCHEMA_COUNT
            - len(extension_unresolved_ids)
        ),
        structural_evidence_count=len(evidence),
        source_row_count_delta=0,
        financial_slot_count=TM_RESIDUAL_FINANCIAL_SLOT_COUNT,
        mapped_assignment_count=TM_RESIDUAL_MAPPED_ASSIGNMENT_COUNT,
        schema_dispositions=dispositions,
        structural_evidence=evidence,
        schema_workbook_sha256=policy.schema_workbook_sha256,
        schema_projection_sha256=policy.schema_projection_sha256,
        policy_sha256=policy.policy_sha256,
    )
    return validate_tm_residual_mapping_result(result)


def validate_tm_residual_mapping_result(
    result: TMResidualMappingResult,
) -> TMResidualMappingResult:
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMResidualSchemaStatus)
    }
    extension_unresolved_ids = by_status[TMResidualSchemaStatus.UNRESOLVED.value]
    expected_status_reconciled_count = TM_RESIDUAL_SCOPE_SCHEMA_COUNT + len(
        extension_unresolved_ids
    )
    expected_unassessed_count = TM_RESIDUAL_SCHEMA_TOTAL - expected_status_reconciled_count
    if (
        result.schema_item_count != TM_RESIDUAL_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != expected_status_reconciled_count
        or result.mapped_schema_count != TM_RESIDUAL_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_RESIDUAL_NOT_OBSERVED_SCHEMA_COUNT
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != len(extension_unresolved_ids)
        or result.not_applicable_schema_count != 0
        or result.extraction_miss_schema_count != 0
        or result.unassessed_schema_count != expected_unassessed_count
        or result.structural_evidence_count != TM_RESIDUAL_STRUCTURAL_EVIDENCE_COUNT
        or result.source_row_count_delta != 0
        or result.financial_slot_count != 0
        or result.mapped_assignment_count != 0
        or not result.mapping_authority_granted
        or len(result.schema_dispositions) != TM_RESIDUAL_SCHEMA_TOTAL
        or by_status[TMResidualSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != TM_RESIDUAL_MAPPED_IDS
        or by_status[TMResidualSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value]
        != TM_RESIDUAL_NOT_OBSERVED_IDS
        or any(
            item.report_norm_id <= TM_RESIDUAL_BASELINE_SCHEMA_HIGH_WATERMARK
            for item in result.schema_dispositions
            if item.status == TMResidualSchemaStatus.UNRESOLVED.value
        )
        or len(by_status[TMResidualSchemaStatus.UNASSESSED.value]) != expected_unassessed_count
        or {item.report_norm_id for item in result.structural_evidence} != TM_RESIDUAL_MAPPED_IDS
        or any(
            item.value_status != "STRUCTURAL_HEADING_NO_VALUE_NO_FINANCIAL_SLOT"
            for item in result.structural_evidence
        )
        or any(
            not item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id in TM_RESIDUAL_MAPPED_IDS
        )
        or any(
            item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id not in TM_RESIDUAL_MAPPED_IDS
        )
    ):
        raise TMResidualMappingError("TM residual result partition drifted")
    return result


def validate_tm_full_schema_partition(
    schema: Sequence[SchemaItem],
    partitions: Sequence[TMOwnedSchemaPartition],
) -> TMFullSchemaPartition:
    tm_items = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    tm_ids = frozenset(item.schema_id for item in tm_items)
    if (
        len(tm_ids) != TM_RESIDUAL_SCHEMA_TOTAL
        or [item.display_order for item in tm_items] != list(range(TM_RESIDUAL_SCHEMA_TOTAL))
        or not partitions
    ):
        raise TMResidualMappingError("TM full partition schema denominator drifted")
    baseline_ids = frozenset(
        item.schema_id
        for item in tm_items
        if item.schema_id <= TM_RESIDUAL_BASELINE_SCHEMA_HIGH_WATERMARK
    )
    extension_ids = tm_ids - baseline_ids
    seen: set[int] = set()
    status_sets = {
        "mapped": set(),
        "unresolved": set(),
        "not_observed": set(),
        "not_applicable": set(),
    }
    ownership_payload = []
    for partition in partitions:
        local_sets = (
            partition.mapped_ids,
            partition.unresolved_ids,
            partition.not_observed_ids,
            partition.not_applicable_ids,
        )
        if (
            not partition.owner_scope
            or any(
                left & right
                for index, left in enumerate(local_sets)
                for right in local_sets[index + 1 :]
            )
            or seen & partition.scope_ids
            or not partition.scope_ids <= tm_ids
        ):
            raise TMResidualMappingError("TM page-owner partitions are not pairwise disjoint")
        seen.update(partition.scope_ids)
        status_sets["mapped"].update(partition.mapped_ids)
        status_sets["unresolved"].update(partition.unresolved_ids)
        status_sets["not_observed"].update(partition.not_observed_ids)
        status_sets["not_applicable"].update(partition.not_applicable_ids)
        ownership_payload.append(
            {
                "owner_scope": partition.owner_scope,
                "mapped": sorted(partition.mapped_ids),
                "unresolved": sorted(partition.unresolved_ids),
                "not_observed": sorted(partition.not_observed_ids),
                "not_applicable": sorted(partition.not_applicable_ids),
            }
        )
    unassessed = tm_ids - seen
    counts = (
        len(status_sets["mapped"]),
        len(status_sets["unresolved"]),
        len(status_sets["not_observed"]),
        len(status_sets["not_applicable"]),
        len(unassessed),
    )
    baseline_counts = (
        len(status_sets["mapped"] - extension_ids),
        len(status_sets["unresolved"] - extension_ids),
        len(status_sets["not_observed"] - extension_ids),
        len(status_sets["not_applicable"] - extension_ids),
    )
    if (
        len(baseline_ids) != TM_RESIDUAL_BASELINE_SCHEMA_TOTAL
        or baseline_counts
        != (
            TM_BASELINE_FINAL_MAPPED_SCHEMA_COUNT,
            TM_BASELINE_FINAL_UNRESOLVED_SCHEMA_COUNT,
            TM_BASELINE_FINAL_NOT_OBSERVED_SCHEMA_COUNT,
            TM_BASELINE_FINAL_NOT_APPLICABLE_SCHEMA_COUNT,
        )
        or unassessed
    ):
        raise TMResidualMappingError(f"TM final business partition drifted: {counts}")
    ownership_sha256 = hashlib.sha256(
        json.dumps(
            ownership_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return TMFullSchemaPartition(
        schema_item_count=len(tm_ids),
        owner_scope_count=len(partitions),
        mapped_schema_count=counts[0],
        unresolved_schema_count=counts[1],
        not_observed_schema_count=counts[2],
        not_applicable_schema_count=counts[3],
        unassessed_schema_count=counts[4],
        ownership_sha256=ownership_sha256,
    )
