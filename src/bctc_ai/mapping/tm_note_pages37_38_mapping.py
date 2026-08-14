"""Fail-closed Note 10 mapping for MBB consolidated PDF pages 37 and 38."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_pages37_38 import (
    ParsedTMFixedAssetPages37_38,
    TMFixedAssetLogicalRow,
)
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

TM_FIXED_ASSET_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-pages37-38-v1.yaml")
TM_FIXED_ASSET_SCHEMA_TOTAL = 1_705
TM_FIXED_ASSET_RECONCILED_SCHEMA_COUNT = 56
TM_FIXED_ASSET_MAPPED_SCHEMA_COUNT = 21
TM_FIXED_ASSET_UNRESOLVED_SCHEMA_COUNT = 0
TM_FIXED_ASSET_NOT_OBSERVED_SCHEMA_COUNT = 35
TM_FIXED_ASSET_UNASSESSED_SCHEMA_COUNT = 1_649
TM_FIXED_ASSET_SOURCE_ROW_COUNT = 35
TM_FIXED_ASSET_MAPPED_SOURCE_ROW_COUNT = 35
TM_FIXED_ASSET_SOURCE_ONLY_ROW_COUNT = 0
TM_FIXED_ASSET_SOURCE_QUESTION_ROW_COUNT = 0
TM_FIXED_ASSET_SOURCE_VALIDATION_ROW_COUNT = 0
TM_FIXED_ASSET_PARTIALLY_MAPPED_SOURCE_ROW_COUNT = 29
TM_FIXED_ASSET_FINANCIAL_SLOT_COUNT = 145
TM_FIXED_ASSET_VALUE_COUNT = 130
TM_FIXED_ASSET_DASH_COUNT = 15
TM_FIXED_ASSET_MAPPED_SLOT_COUNT = 29
TM_FIXED_ASSET_MAPPED_VALUE_COUNT = 28
TM_FIXED_ASSET_MAPPED_DASH_COUNT = 1
TM_FIXED_ASSET_SOURCE_ONLY_SLOT_COUNT = 116
TM_FIXED_ASSET_ASSET_CLASS_SLOT_COUNT = 116
TM_FIXED_ASSET_ACCOUNTING_CHECK_COUNT = 69
TM_FIXED_ASSET_ACCOUNTING_PASS_COUNT = 51
TM_FIXED_ASSET_ACCOUNTING_NOT_TESTABLE_COUNT = 18
TM_FIXED_ASSET_DUPLICATE_CHECK_COUNT = 15

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = set(range(868, 913)) | set(range(5962, 5967)) | set(range(5991, 5997))
_MAPPED_IDS = {
    868,
    869,
    870,
    879,
    882,
    883,
    884,
    887,
    891,
    895,
    *range(5962, 5967),
    *range(5991, 5997),
}
_FORMER_COMPONENT_IDS = {
    871,
    872,
    873,
    874,
    875,
    876,
    877,
    878,
    880,
    881,
    885,
    886,
    888,
    889,
    890,
    892,
    893,
    894,
}
_UNRESOLVED_IDS: set[int] = set()
_NOT_OBSERVED_IDS = _FORMER_COMPONENT_IDS | set(range(896, 913))
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
}
_FIXED_LOCATIONS = {
    ("Q1_2026", "GROSS_COST", 1): ("FIXED_STRUCTURAL_ROW", 869),
    ("Q1_2026", "GROSS_COST", 2): ("FIXED_TOTAL_CELL", 870),
    ("Q1_2026", "GROSS_COST", 3): ("FIXED_TOTAL_CELL", 5991),
    ("Q1_2026", "GROSS_COST", 4): ("FIXED_TOTAL_CELL", 5992),
    ("Q1_2026", "GROSS_COST", 5): ("FIXED_TOTAL_CELL", 5993),
    ("Q1_2026", "GROSS_COST", 6): ("FIXED_TOTAL_CELL", 5962),
    ("Q1_2026", "GROSS_COST", 7): ("FIXED_TOTAL_CELL", 882),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 1): ("FIXED_STRUCTURAL_ROW", 883),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 2): ("FIXED_TOTAL_CELL", 884),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 3): ("FIXED_TOTAL_CELL", 5994),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 4): ("FIXED_TOTAL_CELL", 5995),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 5): ("FIXED_TOTAL_CELL", 5996),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 6): ("FIXED_TOTAL_CELL", 5963),
    ("Q1_2026", "ACCUMULATED_DEPRECIATION", 7): ("FIXED_TOTAL_CELL", 895),
    ("Q1_2026", "NET_BOOK_VALUE", 1): ("FIXED_STRUCTURAL_ROW", 5964),
    ("Q1_2026", "NET_BOOK_VALUE", 2): ("FIXED_TOTAL_CELL", 5965),
    ("Q1_2026", "NET_BOOK_VALUE", 3): ("FIXED_TOTAL_CELL", 5966),
    ("FY_2025", "GROSS_COST", 1): ("FIXED_STRUCTURAL_ROW", 869),
    ("FY_2025", "GROSS_COST", 2): ("FIXED_TOTAL_CELL", 870),
    ("FY_2025", "GROSS_COST", 3): ("FIXED_TOTAL_CELL", 5991),
    ("FY_2025", "GROSS_COST", 4): ("FIXED_TOTAL_CELL", 5992),
    ("FY_2025", "GROSS_COST", 5): ("FIXED_TOTAL_CELL", 879),
    ("FY_2025", "GROSS_COST", 6): ("FIXED_TOTAL_CELL", 5962),
    ("FY_2025", "GROSS_COST", 7): ("FIXED_TOTAL_CELL", 882),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 1): ("FIXED_STRUCTURAL_ROW", 883),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 2): ("FIXED_TOTAL_CELL", 884),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 3): ("FIXED_TOTAL_CELL", 5994),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 4): ("FIXED_TOTAL_CELL", 5995),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 5): ("FIXED_TOTAL_CELL", 891),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 6): ("FIXED_TOTAL_CELL", 887),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 7): ("FIXED_TOTAL_CELL", 5963),
    ("FY_2025", "ACCUMULATED_DEPRECIATION", 8): ("FIXED_TOTAL_CELL", 895),
    ("FY_2025", "NET_BOOK_VALUE", 1): ("FIXED_STRUCTURAL_ROW", 5964),
    ("FY_2025", "NET_BOOK_VALUE", 2): ("FIXED_TOTAL_CELL", 5965),
    ("FY_2025", "NET_BOOK_VALUE", 3): ("FIXED_TOTAL_CELL", 5966),
}


class TMFixedAssetMappingError(ValueError):
    pass


class TMFixedAssetRuleDisposition(StrEnum):
    FIXED_STRUCTURAL_ROW = "FIXED_STRUCTURAL_ROW"
    FIXED_TOTAL_CELL = "FIXED_TOTAL_CELL"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMFixedAssetSchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNRESOLVED = "UNRESOLVED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMFixedAssetSourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMFixedAssetCellStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_ASSET_CLASS_AXIS = "SOURCE_ONLY_ASSET_CLASS_AXIS"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMFixedAssetSourcePanelPolicy:
    panel_key: str
    page_number: int
    page_tag: str
    source_render_sha256: str
    source_ocr_sha256: str


@dataclass(frozen=True)
class TMFixedAssetRowRule:
    panel_key: str
    section_key: str
    section_ordinal: int
    visible_label_anchor: str
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMFixedAssetRuleDisposition
    report_norm_id: int | None
    mapped_axis_role: str | None
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, str, int]:
        return self.panel_key, self.section_key, self.section_ordinal


@dataclass(frozen=True)
class TMFixedAssetMappingPolicy:
    source_path: Path
    document: str
    note_number: str
    report_scope: str
    mapping_authority_scope: str
    source_pdf_sha256: str
    source_panels: tuple[TMFixedAssetSourcePanelPolicy, ...]
    schema_total: int
    scoped_schema_ids: tuple[int, ...]
    title_panel_key: str
    title_report_norm_id: int
    visible_title_anchor: str
    minimum_visible_label_similarity: float
    rows: tuple[TMFixedAssetRowRule, ...]
    unresolved_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMFixedAssetSchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMFixedAssetCellDisposition:
    row_id: str
    cell_index: int
    axis_role: str
    status: str
    report_norm_ids: tuple[int, ...]
    candidate_report_norm_ids: tuple[int, ...]
    raw_text: str
    observation: str
    value: Decimal | None
    period_start: str
    period_end: str
    period_type: str
    period_role: str
    unit: str
    unit_multiplier: int
    source_line_ids: tuple[str, ...]
    value_bbox: BoundingBox | None
    visual_cell_evidence: VisualCellEvidence | None
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMFixedAssetSourceDisposition:
    row_id: str
    panel_key: str
    page_number: int
    section_key: str
    section_ordinal: int
    visible_label: str
    row_kind: str
    row_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    visible_label_similarity: float
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_start: str | None
    period_end: str | None
    period_type: str | None
    period_role: str | None
    source_line_ids: tuple[str, ...]
    label_bbox: BoundingBox
    cell_dispositions: tuple[TMFixedAssetCellDisposition, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMFixedAssetMappedAssignment:
    report_norm_id: int
    canonical_name: str
    row_id: str
    panel_key: str
    page_number: int
    cell_index: int
    axis_role: str
    mapping_role: str
    raw_text: str
    observation: str
    value: Decimal | None
    period_start: str
    period_end: str
    period_type: str
    period_role: str
    unit: str
    unit_multiplier: int
    source_line_ids: tuple[str, ...]
    label_bbox: BoundingBox
    value_bbox: BoundingBox | None
    visual_cell_evidence: VisualCellEvidence | None


@dataclass(frozen=True)
class TMFixedAssetTitleMapping:
    report_norm_id: int
    canonical_name: str
    panel_key: str
    page_number: int
    source_evidence_id: str
    visible_title: str
    source_line_ids: tuple[str, ...]
    title_bbox: BoundingBox
    visible_label_similarity: float
    mapping_role: str


@dataclass(frozen=True)
class TMFixedAssetAccountingCheck:
    check_id: str
    panel_key: str
    section_key: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMFixedAssetDuplicateCheck:
    check_id: str
    section_key: str
    axis_role: str
    comparative_close: Decimal
    current_open: Decimal
    residual: Decimal
    status: str


@dataclass(frozen=True)
class TMFixedAssetMappingResult:
    statement_type: str
    document: str
    note_number: str
    page_numbers: tuple[int, ...]
    report_scope: str
    status: str
    mapping_authority_scope: str
    mapping_authority_granted: bool
    schema_item_count: int
    status_reconciled_schema_count: int
    mapped_schema_count: int
    unresolved_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    ambiguous_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    source_validation_row_count: int
    partially_mapped_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_source_slot_count: int
    mapped_value_assignment_count: int
    mapped_dash_assignment_count: int
    source_only_slot_count: int
    asset_class_source_only_slot_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    duplicate_check_count: int
    duplicate_pass_count: int
    title_mapping: TMFixedAssetTitleMapping
    schema_dispositions: tuple[TMFixedAssetSchemaDisposition, ...]
    source_dispositions: tuple[TMFixedAssetSourceDisposition, ...]
    mapped_assignments: tuple[TMFixedAssetMappedAssignment, ...]
    accounting_checks: tuple[TMFixedAssetAccountingCheck, ...]
    duplicate_checks: tuple[TMFixedAssetDuplicateCheck, ...]
    source_pdf_sha256: str
    source_render_sha256s: tuple[str, ...]
    source_ocr_sha256s: tuple[str, ...]
    dash_pixel_evidence_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMFixedAssetMappingError(f"invalid positive TM pages37-38 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMFixedAssetMappingError(f"TM pages37-38 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMFixedAssetMappingError(f"TM pages37-38 {field} contains duplicates")
    return result


def load_tm_fixed_asset_pages37_38_mapping_policy(path: Path) -> TMFixedAssetMappingPolicy:
    """Load and pin the exact fixed rows, unresolved IDs, and assessed scope."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMFixedAssetMappingError(f"cannot load TM pages37-38 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGES37_38_SCOPED_TOTAL_COLUMN_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("report_scope") != "CONSOLIDATED"
        or payload.get("note_number") != "10"
    ):
        raise TMFixedAssetMappingError("TM pages37-38 mapping policy identity drifted")
    source_pdf_hash = payload.get("source_pdf_sha256")
    if not isinstance(source_pdf_hash, str) or not _SHA256.fullmatch(source_pdf_hash):
        raise TMFixedAssetMappingError("TM pages37-38 mapping PDF hash is invalid")
    raw_panels = payload.get("source_panels")
    if not isinstance(raw_panels, list) or len(raw_panels) != 2:
        raise TMFixedAssetMappingError("TM pages37-38 mapping source panels are incomplete")
    panels = []
    for record in raw_panels:
        if not isinstance(record, dict):
            raise TMFixedAssetMappingError("TM pages37-38 source-panel record is invalid")
        hashes = (record.get("source_render_sha256"), record.get("source_ocr_sha256"))
        if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
            raise TMFixedAssetMappingError("TM pages37-38 source-panel hash is invalid")
        panel = TMFixedAssetSourcePanelPolicy(
            panel_key=str(record.get("panel_key", "")),
            page_number=_positive_int(record, "page_number"),
            page_tag=str(record.get("page_tag", "")),
            source_render_sha256=hashes[0],
            source_ocr_sha256=hashes[1],
        )
        if panel.page_tag != f"page-{panel.page_number:04d}":
            raise TMFixedAssetMappingError("TM pages37-38 source-panel page tag drifted")
        panels.append(panel)
    if tuple((panel.panel_key, panel.page_number) for panel in panels) != (
        ("Q1_2026", 37),
        ("FY_2025", 38),
    ):
        raise TMFixedAssetMappingError("TM pages37-38 source-panel order drifted")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < threshold <= 1
    ):
        raise TMFixedAssetMappingError("TM pages37-38 label threshold is invalid")
    scoped_ids = _ids(payload.get("scoped_schema_ids"), "scoped schema IDs")
    unresolved = _ids(
        payload.get("unresolved_schema_ids"), "unresolved schema IDs", allow_empty=True
    )
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed schema IDs")
    title = payload.get("title_mapping")
    if not isinstance(title, dict):
        raise TMFixedAssetMappingError("TM pages37-38 title mapping is absent")
    title_id = title.get("report_norm_id")
    title_anchor = title.get("visible_title_anchor")
    if (
        title.get("panel_key") != "Q1_2026"
        or title_id != 868
        or not isinstance(title_anchor, str)
        or not retrieval_key(title_anchor)
    ):
        raise TMFixedAssetMappingError("TM pages37-38 title mapping drifted")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_FIXED_ASSET_SOURCE_ROW_COUNT:
        raise TMFixedAssetMappingError("TM pages37-38 mapping row denominator drifted")
    valid_observations = {observation.value for observation in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMFixedAssetMappingError("TM pages37-38 mapping row is invalid")
        try:
            disposition = TMFixedAssetRuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMFixedAssetMappingError("TM pages37-38 rule disposition is invalid") from exc
        observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        mapped_axis = record.get("mapped_axis_role")
        candidates = _ids(
            record.get("candidate_report_norm_ids"),
            "candidate ReportNormIds",
            allow_empty=True,
        )
        if (
            not isinstance(record.get("panel_key"), str)
            or not isinstance(record.get("section_key"), str)
            or isinstance(record.get("section_ordinal"), bool)
            or not isinstance(record.get("section_ordinal"), int)
            or record["section_ordinal"] <= 0
            or not isinstance(record.get("visible_label_anchor"), str)
            or not retrieval_key(record["visible_label_anchor"])
            or record.get("expected_row_kind") not in {kind.value for kind in TMNoteRowKind}
            or not isinstance(observations, list)
            or any(value not in valid_observations for value in observations)
        ):
            raise TMFixedAssetMappingError("TM pages37-38 row identity/status is invalid")
        if disposition is TMFixedAssetRuleDisposition.FIXED_STRUCTURAL_ROW:
            valid_fixed = (
                record["expected_row_kind"] == TMNoteRowKind.LABEL_ONLY.value
                and observations == []
                and isinstance(report_norm_id, int)
                and not isinstance(report_norm_id, bool)
                and mapped_axis is None
                and not candidates
            )
        elif disposition is TMFixedAssetRuleDisposition.FIXED_TOTAL_CELL:
            valid_fixed = (
                record["expected_row_kind"] == TMNoteRowKind.NUMERIC.value
                and len(observations) == 5
                and isinstance(report_norm_id, int)
                and not isinstance(report_norm_id, bool)
                and mapped_axis == "TOTAL"
                and not candidates
            )
        else:
            valid_fixed = report_norm_id is None and mapped_axis is None
        if not valid_fixed:
            raise TMFixedAssetMappingError("TM pages37-38 fixed/source-only rule is malformed")
        rows.append(
            TMFixedAssetRowRule(
                panel_key=record["panel_key"],
                section_key=record["section_key"],
                section_ordinal=record["section_ordinal"],
                visible_label_anchor=retrieval_key(record["visible_label_anchor"]),
                expected_row_kind=record["expected_row_kind"],
                expected_observations=tuple(str(value) for value in observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                mapped_axis_role=mapped_axis,
                candidate_report_norm_ids=candidates,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMFixedAssetMappingError("TM pages37-38 rule identities are duplicated")
    fixed_locations = {
        row.identity: (row.disposition.value, row.report_norm_id)
        for row in rows
        if row.disposition
        in {
            TMFixedAssetRuleDisposition.FIXED_STRUCTURAL_ROW,
            TMFixedAssetRuleDisposition.FIXED_TOTAL_CELL,
        }
    }
    if fixed_locations != _FIXED_LOCATIONS:
        raise TMFixedAssetMappingError("TM pages37-38 fixed mapping locations drifted")
    candidate_union = {candidate for row in rows for candidate in row.candidate_report_norm_ids}
    fixed_ids = {868} | {row.report_norm_id for row in rows if row.report_norm_id is not None}
    if (
        set(scoped_ids) != _SCOPED_IDS
        or fixed_ids != _MAPPED_IDS
        or set(unresolved) != _UNRESOLVED_IDS
        or candidate_union != _UNRESOLVED_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or fixed_ids | set(unresolved) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMFixedAssetMappingError("TM pages37-38 explicit schema reconciliation drifted")
    if (
        sum(row.disposition is TMFixedAssetRuleDisposition.SOURCE_ONLY_QUESTION for row in rows)
        != TM_FIXED_ASSET_SOURCE_QUESTION_ROW_COUNT
        or sum(
            row.disposition is TMFixedAssetRuleDisposition.SOURCE_ONLY_VALIDATION for row in rows
        )
        != TM_FIXED_ASSET_SOURCE_VALIDATION_ROW_COUNT
    ):
        raise TMFixedAssetMappingError("TM pages37-38 source-only row split drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMFixedAssetMappingError("TM pages37-38 forbidden mapping inputs drifted")
    mapping_scope = payload.get("mapping_authority_scope")
    document = payload.get("document")
    if not isinstance(mapping_scope, str) or not mapping_scope or not isinstance(document, str):
        raise TMFixedAssetMappingError("TM pages37-38 mapping scope/document is invalid")
    return TMFixedAssetMappingPolicy(
        source_path=path,
        document=document,
        note_number="10",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=source_pdf_hash,
        source_panels=tuple(panels),
        schema_total=_positive_int(payload, "schema_total"),
        scoped_schema_ids=scoped_ids,
        title_panel_key="Q1_2026",
        title_report_norm_id=title_id,
        visible_title_anchor=retrieval_key(title_anchor),
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        unresolved_schema_ids=unresolved,
        not_observed_schema_ids=not_observed,
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _similarity(visible: str, anchor: str) -> float:
    key = retrieval_key(visible)
    if not key or not anchor:
        return 0.0
    if key in anchor or anchor in key:
        return 1.0
    return ratio(key, anchor) / 100


def _schema_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [(item.schema_id, item.display_order, item.canonical_name) for item in items]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def _dash_evidence_hash(parsed: ParsedTMFixedAssetPages37_38) -> str:
    records = []
    for row in parsed.rows:
        for evidence in row.visual_cell_evidence:
            if evidence is None:
                continue
            record = asdict(evidence)
            record.pop("source_image_path")
            records.append(record)
    return hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _row(
    parsed: ParsedTMFixedAssetPages37_38,
    panel_key: str,
    section_key: str,
    row_role: str,
) -> TMFixedAssetLogicalRow:
    matches = [
        row
        for row in parsed.rows
        if row.panel_key == panel_key
        and row.section_key == section_key
        and row.row_role == row_role
    ]
    if len(matches) != 1:
        raise TMFixedAssetMappingError(
            f"TM fixed-asset validation row identity is not unique: {panel_key}/{section_key}/{row_role}"
        )
    return matches[0]


def _not_testable(
    check_id: str, panel_key: str, section_key: str, axis_role: str
) -> TMFixedAssetAccountingCheck:
    return TMFixedAssetAccountingCheck(
        check_id=check_id,
        panel_key=panel_key,
        section_key=section_key,
        axis_role=axis_role,
        status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
        expected_value=None,
        observed_value=None,
        residual=None,
        reason="visible DASH is an observation status and cannot be coerced to numeric zero",
    )


def _accounting_validation(
    parsed: ParsedTMFixedAssetPages37_38,
) -> tuple[TMFixedAssetAccountingCheck, ...]:
    checks = []
    for row in parsed.rows:
        if row.row_kind is not TMNoteRowKind.NUMERIC:
            continue
        cells = row.row.cells
        check_id = f"{row.row_id}:TOTAL_EQUALS_FOUR_VISIBLE_CLASSES"
        if any(cell.observation is ObservationKind.DASH for cell in cells):
            checks.append(_not_testable(check_id, row.panel_key, row.section_key, "TOTAL"))
            continue
        expected = sum((cell.value for cell in cells[:4] if cell.value is not None), Decimal(0))
        observed = cells[4].value
        if observed is None:
            raise TMFixedAssetMappingError("TM fixed-asset horizontal total lost its value")
        residual = observed - expected
        checks.append(
            TMFixedAssetAccountingCheck(
                check_id=check_id,
                panel_key=row.panel_key,
                section_key=row.section_key,
                axis_role="TOTAL",
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=residual,
                reason="visible TOTAL compared with the sum of four visible asset-class values",
            )
        )

    for panel in parsed.panels:
        for section_key in ("GROSS_COST", "ACCUMULATED_DEPRECIATION"):
            section_rows = [
                row
                for row in panel.rows
                if row.section_key == section_key and row.row_kind is TMNoteRowKind.NUMERIC
            ]
            opening = next(row for row in section_rows if row.row_role == "OPENING")
            closing = next(row for row in section_rows if row.row_role == "CLOSING")
            movements = [row for row in section_rows if row.row_role not in {"OPENING", "CLOSING"}]
            for axis_index, axis in enumerate(panel.axes):
                equation_cells = [
                    opening.row.cells[axis_index],
                    *(row.row.cells[axis_index] for row in movements),
                    closing.row.cells[axis_index],
                ]
                check_id = f"{panel.panel_key}:{section_key}:ROLLFORWARD"
                if any(cell.observation is ObservationKind.DASH for cell in equation_cells):
                    checks.append(
                        _not_testable(check_id, panel.panel_key, section_key, axis.axis_role)
                    )
                    continue
                values = [cell.value for cell in equation_cells]
                if any(value is None for value in values):
                    raise TMFixedAssetMappingError("TM fixed-asset rollforward lost a value")
                expected = values[0] + sum(values[1:-1], Decimal(0))
                observed = values[-1]
                residual = observed - expected
                checks.append(
                    TMFixedAssetAccountingCheck(
                        check_id=check_id,
                        panel_key=panel.panel_key,
                        section_key=section_key,
                        axis_role=axis.axis_role,
                        status="PASS" if residual == 0 else "FAIL",
                        expected_value=expected,
                        observed_value=observed,
                        residual=residual,
                        reason="opening plus all visible movements compared with visible closing",
                    )
                )

        for row_role in ("OPENING", "CLOSING"):
            gross = _row(parsed, panel.panel_key, "GROSS_COST", row_role)
            depreciation = _row(parsed, panel.panel_key, "ACCUMULATED_DEPRECIATION", row_role)
            net = _row(parsed, panel.panel_key, "NET_BOOK_VALUE", row_role)
            for axis_index, axis in enumerate(panel.axes):
                gross_value = gross.row.cells[axis_index].value
                depreciation_value = depreciation.row.cells[axis_index].value
                observed = net.row.cells[axis_index].value
                if gross_value is None or depreciation_value is None or observed is None:
                    raise TMFixedAssetMappingError("TM fixed-asset NBV equation lost a value")
                expected = gross_value - depreciation_value
                residual = observed - expected
                checks.append(
                    TMFixedAssetAccountingCheck(
                        check_id=f"{panel.panel_key}:{row_role}:NBV_EQUALS_GROSS_MINUS_DEPRECIATION",
                        panel_key=panel.panel_key,
                        section_key="NET_BOOK_VALUE",
                        axis_role=axis.axis_role,
                        status="PASS" if residual == 0 else "FAIL",
                        expected_value=expected,
                        observed_value=observed,
                        residual=residual,
                        reason="visible net book value compared with gross less accumulated depreciation",
                    )
                )
    return tuple(checks)


def _cross_panel_validation(
    parsed: ParsedTMFixedAssetPages37_38,
) -> tuple[TMFixedAssetDuplicateCheck, ...]:
    checks = []
    current = next(panel for panel in parsed.panels if panel.panel_key == "Q1_2026")
    for section_key in ("GROSS_COST", "ACCUMULATED_DEPRECIATION", "NET_BOOK_VALUE"):
        comparative_close = _row(parsed, "FY_2025", section_key, "CLOSING")
        current_open = _row(parsed, "Q1_2026", section_key, "OPENING")
        for axis_index, axis in enumerate(current.axes):
            left = comparative_close.row.cells[axis_index].value
            right = current_open.row.cells[axis_index].value
            if left is None or right is None:
                raise TMFixedAssetMappingError("TM cross-panel close/open check lost a value")
            residual = right - left
            checks.append(
                TMFixedAssetDuplicateCheck(
                    check_id="FY2025_CLOSE_EQUALS_Q1_2026_OPEN",
                    section_key=section_key,
                    axis_role=axis.axis_role,
                    comparative_close=left,
                    current_open=right,
                    residual=residual,
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    return tuple(checks)


def reconcile_tm_fixed_asset_pages37_38_items(
    parsed: ParsedTMFixedAssetPages37_38,
    *,
    schema: list[SchemaItem],
    policy: TMFixedAssetMappingPolicy,
    source_pdf_path: Path,
) -> TMFixedAssetMappingResult:
    """Map only fixed structural/total evidence and expose every aggregate ambiguity."""

    if (
        parsed.document != policy.document
        or parsed.note_number != policy.note_number
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
    ):
        raise TMFixedAssetMappingError("TM pages37-38 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMFixedAssetMappingError("TM pages37-38 source PDF hash drifted")
    if tuple(
        (
            panel.panel_key,
            panel.page_number,
            panel.page_tag,
            panel.source_render_sha256,
            panel.source_ocr_sha256,
        )
        for panel in parsed.panels
    ) != tuple(
        (
            panel.panel_key,
            panel.page_number,
            panel.page_tag,
            panel.source_render_sha256,
            panel.source_ocr_sha256,
        )
        for panel in policy.source_panels
    ):
        raise TMFixedAssetMappingError("TM pages37-38 panel source identity drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_FIXED_ASSET_SCHEMA_TOTAL:
        raise TMFixedAssetMappingError("TM schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMFixedAssetMappingError("TM pages37-38 policy references unknown ReportNormIds")
    parsed_by_identity = {
        (row.panel_key, row.section_key, row.section_ordinal): row for row in parsed.rows
    }
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMFixedAssetMappingError("TM pages37-38 parsed row order drifted from policy")

    title_panel = next(
        panel for panel in parsed.panels if panel.panel_key == policy.title_panel_key
    )
    if (
        title_panel.note_title_text is None
        or title_panel.note_title_bbox is None
        or not title_panel.note_title_line_indices
    ):
        raise TMFixedAssetMappingError("TM pages37-38 root title evidence is absent")
    title_similarity = _similarity(title_panel.note_title_text, policy.visible_title_anchor)
    if title_similarity < policy.minimum_visible_label_similarity:
        raise TMFixedAssetMappingError("TM pages37-38 root title anchor failed")
    title_source_id = f"{title_panel.page_tag}:note-title"
    title_mapping = TMFixedAssetTitleMapping(
        report_norm_id=policy.title_report_norm_id,
        canonical_name=schema_by_id[policy.title_report_norm_id].canonical_name,
        panel_key=title_panel.panel_key,
        page_number=title_panel.page_number,
        source_evidence_id=title_source_id,
        visible_title=title_panel.note_title_text,
        source_line_ids=tuple(
            f"{title_panel.page_tag}:line-{index:04d}"
            for index in title_panel.note_title_line_indices
        ),
        title_bbox=title_panel.note_title_bbox,
        visible_label_similarity=title_similarity,
        mapping_role="DIRECT_VISIBLE_NOTE_TITLE",
    )

    source_rows_by_schema: dict[int, list[str]] = {868: [title_source_id]}
    unresolved_rows_by_schema: dict[int, list[str]] = {
        report_norm_id: [] for report_norm_id in policy.unresolved_schema_ids
    }
    source_dispositions = []
    mapped_assignments = []
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMFixedAssetMappingError(f"TM fixed-asset row status drifted: {row.row_id}")
        similarity = _similarity(row.row.label, rule.visible_label_anchor)
        if similarity < policy.minimum_visible_label_similarity:
            raise TMFixedAssetMappingError(f"TM fixed-asset visible label failed: {row.row_id}")
        if rule.disposition in {
            TMFixedAssetRuleDisposition.FIXED_STRUCTURAL_ROW,
            TMFixedAssetRuleDisposition.FIXED_TOTAL_CELL,
        }:
            assert rule.report_norm_id is not None
            status = TMFixedAssetSourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = schema_by_id[rule.report_norm_id].canonical_name
            source_rows_by_schema.setdefault(rule.report_norm_id, []).append(row.row_id)
            question_required = False
            reason = (
                "fixed visible structural row passed its pinned source-scoped mapping"
                if rule.disposition is TMFixedAssetRuleDisposition.FIXED_STRUCTURAL_ROW
                else "only the visible TOTAL cell passed its pinned source-scoped mapping"
            )
        elif rule.disposition is TMFixedAssetRuleDisposition.SOURCE_ONLY_QUESTION:
            status = TMFixedAssetSourceStatus.SOURCE_ONLY_QUESTION.value
            canonical = None
            question_required = True
            reason = (
                "visible aggregate movement cannot be disaggregated to component IDs"
                if rule.candidate_report_norm_ids
                else "visible source row has no exact supplied-schema item and remains reviewable"
            )
            for candidate in rule.candidate_report_norm_ids:
                unresolved_rows_by_schema[candidate].append(row.row_id)
        else:
            status = TMFixedAssetSourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            question_required = False
            reason = "visible net-book-value evidence is retained for equations without export"

        panel = next(item for item in parsed.panels if item.panel_key == row.panel_key)
        cell_dispositions = []
        if row.row_kind is TMNoteRowKind.NUMERIC:
            assert row.period_start is not None and row.period_end is not None
            assert row.period_type is not None and row.period_role is not None
            for cell_index, (axis, cell) in enumerate(zip(panel.axes, row.row.cells, strict=True)):
                if not axis.is_total:
                    cell_status = TMFixedAssetCellStatus.SOURCE_ONLY_ASSET_CLASS_AXIS.value
                    report_norm_ids: tuple[int, ...] = ()
                    candidates: tuple[int, ...] = ()
                    cell_question = False
                    cell_reason = (
                        "asset-class axis retained as provenance/equation evidence; schema mapping "
                        "authority is limited to TOTAL"
                    )
                elif rule.disposition is TMFixedAssetRuleDisposition.FIXED_TOTAL_CELL:
                    assert rule.report_norm_id is not None
                    cell_status = TMFixedAssetCellStatus.MAPPED_AUTOMATIC_SCOPED.value
                    report_norm_ids = (rule.report_norm_id,)
                    candidates = ()
                    cell_question = False
                    cell_reason = "visible TOTAL cell mapped by a pinned row identity"
                elif rule.disposition is TMFixedAssetRuleDisposition.SOURCE_ONLY_QUESTION:
                    cell_status = TMFixedAssetCellStatus.SOURCE_ONLY_QUESTION.value
                    report_norm_ids = ()
                    candidates = rule.candidate_report_norm_ids
                    cell_question = True
                    cell_reason = reason
                else:
                    cell_status = TMFixedAssetCellStatus.SOURCE_ONLY_VALIDATION.value
                    report_norm_ids = ()
                    candidates = ()
                    cell_question = False
                    cell_reason = reason
                source_line_ids = tuple(
                    f"{row.page_tag}:line-{index:04d}"
                    for index in row.value_line_indices[cell_index]
                )
                disposition = TMFixedAssetCellDisposition(
                    row_id=row.row_id,
                    cell_index=cell_index,
                    axis_role=axis.axis_role,
                    status=cell_status,
                    report_norm_ids=report_norm_ids,
                    candidate_report_norm_ids=candidates,
                    raw_text=cell.raw_text,
                    observation=cell.observation.value,
                    value=cell.value,
                    period_start=row.period_start.isoformat(),
                    period_end=row.period_end.isoformat(),
                    period_type=row.period_type,
                    period_role=row.period_role,
                    unit=axis.canonical_unit,
                    unit_multiplier=axis.unit_multiplier,
                    source_line_ids=source_line_ids,
                    value_bbox=row.value_bboxes[cell_index],
                    visual_cell_evidence=row.visual_cell_evidence[cell_index],
                    question_required=cell_question,
                    reason=cell_reason,
                )
                cell_dispositions.append(disposition)
                if report_norm_ids:
                    report_norm_id = report_norm_ids[0]
                    mapped_assignments.append(
                        TMFixedAssetMappedAssignment(
                            report_norm_id=report_norm_id,
                            canonical_name=schema_by_id[report_norm_id].canonical_name,
                            row_id=row.row_id,
                            panel_key=row.panel_key,
                            page_number=row.page_number,
                            cell_index=cell_index,
                            axis_role=axis.axis_role,
                            mapping_role="TOTAL_COLUMN_DIRECT_VISIBLE_ROW",
                            raw_text=cell.raw_text,
                            observation=cell.observation.value,
                            value=cell.value,
                            period_start=row.period_start.isoformat(),
                            period_end=row.period_end.isoformat(),
                            period_type=row.period_type,
                            period_role=row.period_role,
                            unit=axis.canonical_unit,
                            unit_multiplier=axis.unit_multiplier,
                            source_line_ids=source_line_ids,
                            label_bbox=row.label_bbox,
                            value_bbox=row.value_bboxes[cell_index],
                            visual_cell_evidence=row.visual_cell_evidence[cell_index],
                        )
                    )
        source_dispositions.append(
            TMFixedAssetSourceDisposition(
                row_id=row.row_id,
                panel_key=row.panel_key,
                page_number=row.page_number,
                section_key=row.section_key,
                section_ordinal=row.section_ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                row_role=row.row_role,
                status=status,
                report_norm_id=rule.report_norm_id,
                canonical_name=canonical,
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                candidate_canonical_names=tuple(
                    schema_by_id[candidate].canonical_name
                    for candidate in rule.candidate_report_norm_ids
                ),
                visible_label_similarity=similarity,
                observations=observations,
                values=tuple(cell.value for cell in row.row.cells),
                period_start=row.period_start.isoformat() if row.period_start else None,
                period_end=row.period_end.isoformat() if row.period_end else None,
                period_type=row.period_type,
                period_role=row.period_role,
                source_line_ids=row.row.source_row_ids,
                label_bbox=row.label_bbox,
                cell_dispositions=tuple(cell_dispositions),
                question_required=question_required,
                reason=reason,
            )
        )

    accounting = _accounting_validation(parsed)
    duplicates = _cross_panel_validation(parsed)
    if (
        len(accounting) != TM_FIXED_ASSET_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in accounting)
        != TM_FIXED_ASSET_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting)
        != TM_FIXED_ASSET_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in accounting)
        or len(duplicates) != TM_FIXED_ASSET_DUPLICATE_CHECK_COUNT
        or any(check.status != "PASS" for check in duplicates)
    ):
        raise TMFixedAssetMappingError("TM pages37-38 accounting/cross-panel validation failed")

    schema_dispositions = []
    unresolved = set(policy.unresolved_schema_ids)
    not_observed = set(policy.not_observed_schema_ids)
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            schema_status = TMFixedAssetSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            schema_reason = "fixed title/row/TOTAL evidence passed source-scoped mapping"
        elif item.schema_id in unresolved:
            schema_status = TMFixedAssetSchemaStatus.UNRESOLVED.value
            source_ids = tuple(unresolved_rows_by_schema[item.schema_id])
            schema_reason = (
                "visible movement is aggregate; this component cannot be assigned without "
                "unsupported disaggregation"
            )
        elif item.schema_id in not_observed:
            schema_status = TMFixedAssetSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            schema_reason = "item belongs to the assessed finance-lease branch absent on pages37-38"
        else:
            schema_status = TMFixedAssetSchemaStatus.UNASSESSED.value
            source_ids = ()
            schema_reason = "outside the Note 10 schema scope assessed by this batch"
        schema_dispositions.append(
            TMFixedAssetSchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=schema_status,
                source_row_ids=source_ids,
                reason=schema_reason,
            )
        )

    all_cells = tuple(cell for source in source_dispositions for cell in source.cell_dispositions)
    result = TMFixedAssetMappingResult(
        statement_type="TM",
        document=policy.document,
        note_number=policy.note_number,
        page_numbers=(37, 38),
        report_scope=policy.report_scope,
        status="SCOPED_NOTE10_TOTAL_COLUMN_MAPPING_WITH_UNIVERSAL_AGGREGATE_ITEMS",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_rows_by_schema),
        unresolved_schema_count=len(unresolved),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            source.status == TMFixedAssetSourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for source in source_dispositions
        ),
        source_only_row_count=sum(
            source.status != TMFixedAssetSourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for source in source_dispositions
        ),
        source_question_row_count=sum(source.question_required for source in source_dispositions),
        source_validation_row_count=sum(
            source.status == TMFixedAssetSourceStatus.SOURCE_ONLY_VALIDATION.value
            for source in source_dispositions
        ),
        partially_mapped_source_row_count=sum(
            any(
                cell.status == TMFixedAssetCellStatus.MAPPED_AUTOMATIC_SCOPED.value
                for cell in source.cell_dispositions
            )
            and any(
                cell.status == TMFixedAssetCellStatus.SOURCE_ONLY_ASSET_CLASS_AXIS.value
                for cell in source.cell_dispositions
            )
            for source in source_dispositions
        ),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_source_slot_count=len(mapped_assignments),
        mapped_value_assignment_count=sum(
            assignment.observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for assignment in mapped_assignments
        ),
        mapped_dash_assignment_count=sum(
            assignment.observation == ObservationKind.DASH.value
            for assignment in mapped_assignments
        ),
        source_only_slot_count=sum(
            cell.status != TMFixedAssetCellStatus.MAPPED_AUTOMATIC_SCOPED.value
            for cell in all_cells
        ),
        asset_class_source_only_slot_count=sum(
            cell.status == TMFixedAssetCellStatus.SOURCE_ONLY_ASSET_CLASS_AXIS.value
            for cell in all_cells
        ),
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting
        ),
        duplicate_check_count=len(duplicates),
        duplicate_pass_count=sum(check.status == "PASS" for check in duplicates),
        title_mapping=title_mapping,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        mapped_assignments=tuple(mapped_assignments),
        accounting_checks=accounting,
        duplicate_checks=duplicates,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256s=tuple(panel.source_render_sha256 for panel in policy.source_panels),
        source_ocr_sha256s=tuple(panel.source_ocr_sha256 for panel in policy.source_panels),
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS_AND_NUMERIC_GEOMETRY",
            "VISIBLE_NOTE10_PANEL_SECTION_AND_ROW_ORDER",
            "VISIBLE_FOUR_ASSET_CLASS_AXES_PLUS_TOTAL",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "VISIBLE_PERIOD_SCOPE_AND_UNIT",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_AND_CROSS_PANEL_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
        ),
    )
    return validate_tm_fixed_asset_pages37_38_mapping_result(result)


def validate_tm_fixed_asset_pages37_38_mapping_result(
    result: TMFixedAssetMappingResult,
) -> TMFixedAssetMappingResult:
    """Enforce exact source, schema, mapping, and validation denominators."""

    if (
        result.schema_item_count != TM_FIXED_ASSET_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_FIXED_ASSET_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_FIXED_ASSET_MAPPED_SCHEMA_COUNT
        or result.unresolved_schema_count != TM_FIXED_ASSET_UNRESOLVED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_FIXED_ASSET_NOT_OBSERVED_SCHEMA_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unassessed_schema_count != TM_FIXED_ASSET_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_FIXED_ASSET_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_FIXED_ASSET_MAPPED_SOURCE_ROW_COUNT
        or result.source_only_row_count != TM_FIXED_ASSET_SOURCE_ONLY_ROW_COUNT
        or result.source_question_row_count != TM_FIXED_ASSET_SOURCE_QUESTION_ROW_COUNT
        or result.source_validation_row_count != TM_FIXED_ASSET_SOURCE_VALIDATION_ROW_COUNT
        or result.partially_mapped_source_row_count
        != TM_FIXED_ASSET_PARTIALLY_MAPPED_SOURCE_ROW_COUNT
        or result.financial_slot_count != TM_FIXED_ASSET_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_FIXED_ASSET_VALUE_COUNT
        or result.dash_count != TM_FIXED_ASSET_DASH_COUNT
        or result.mapped_source_slot_count != TM_FIXED_ASSET_MAPPED_SLOT_COUNT
        or result.mapped_value_assignment_count != TM_FIXED_ASSET_MAPPED_VALUE_COUNT
        or result.mapped_dash_assignment_count != TM_FIXED_ASSET_MAPPED_DASH_COUNT
        or result.source_only_slot_count != TM_FIXED_ASSET_SOURCE_ONLY_SLOT_COUNT
        or result.asset_class_source_only_slot_count != TM_FIXED_ASSET_ASSET_CLASS_SLOT_COUNT
        or result.accounting_check_count != TM_FIXED_ASSET_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_FIXED_ASSET_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_FIXED_ASSET_ACCOUNTING_NOT_TESTABLE_COUNT
        or result.duplicate_check_count != TM_FIXED_ASSET_DUPLICATE_CHECK_COUNT
        or result.duplicate_pass_count != TM_FIXED_ASSET_DUPLICATE_CHECK_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMFixedAssetMappingError("TM pages37-38 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.unresolved_schema_count
        + result.not_observed_schema_count
        != result.status_reconciled_schema_count
        or result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or result.mapped_source_row_count + result.source_only_row_count != result.source_row_count
        or result.mapped_source_slot_count + result.source_only_slot_count
        != result.financial_slot_count
    ):
        raise TMFixedAssetMappingError("TM pages37-38 status counts do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMFixedAssetSchemaStatus)
    }
    if (
        by_status[TMFixedAssetSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMFixedAssetSchemaStatus.UNRESOLVED.value] != _UNRESOLVED_IDS
        or by_status[TMFixedAssetSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMFixedAssetMappingError("TM pages37-38 schema status sets drifted")
    if (
        result.title_mapping.report_norm_id != 868
        or any(assignment.axis_role != "TOTAL" for assignment in result.mapped_assignments)
        or any(
            (
                assignment.visual_cell_evidence is None
                if assignment.observation == ObservationKind.DASH.value
                else assignment.visual_cell_evidence is not None
            )
            for assignment in result.mapped_assignments
        )
        or len(
            {(assignment.row_id, assignment.cell_index) for assignment in result.mapped_assignments}
        )
        != len(result.mapped_assignments)
    ):
        raise TMFixedAssetMappingError("TM pages37-38 TOTAL-only mapping authority drifted")
    dash_cells = [
        cell
        for source in result.source_dispositions
        for cell in source.cell_dispositions
        if cell.observation == ObservationKind.DASH.value
    ]
    if len(dash_cells) != TM_FIXED_ASSET_DASH_COUNT or any(
        cell.value is not None or cell.visual_cell_evidence is None for cell in dash_cells
    ):
        raise TMFixedAssetMappingError("TM pages37-38 DASH status lost pixel provenance")
    if any(check.status == "FAIL" for check in result.accounting_checks) or any(
        check.status != "PASS" for check in result.duplicate_checks
    ):
        raise TMFixedAssetMappingError("TM pages37-38 validation contains a failure")
    return result


__all__ = [
    "TM_FIXED_ASSET_MAPPING_POLICY_RELATIVE_PATH",
    "TMFixedAssetAccountingCheck",
    "TMFixedAssetCellStatus",
    "TMFixedAssetDuplicateCheck",
    "TMFixedAssetMappedAssignment",
    "TMFixedAssetMappingError",
    "TMFixedAssetMappingPolicy",
    "TMFixedAssetMappingResult",
    "TMFixedAssetSchemaStatus",
    "TMFixedAssetSourceStatus",
    "load_tm_fixed_asset_pages37_38_mapping_policy",
    "reconcile_tm_fixed_asset_pages37_38_items",
    "validate_tm_fixed_asset_pages37_38_mapping_result",
]
