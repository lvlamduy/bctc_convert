from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any


class EvidenceStatus(StrEnum):
    AUTO_VERIFIED_HIGH = "AUTO_VERIFIED_HIGH"
    AUTO_VERIFIED_MEDIUM = "AUTO_VERIFIED_MEDIUM"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_OBSERVED = "NOT_OBSERVED"


class ObservationKind(StrEnum):
    VALUE = "VALUE"
    BLANK = "BLANK"
    ZERO = "ZERO"
    DASH = "DASH"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"


class ValueStatus(StrEnum):
    """Semantic disposition of a target value, separate from confidence status."""

    OBSERVED_VALUE = "OBSERVED_VALUE"
    OBSERVED_ZERO = "OBSERVED_ZERO"
    NOT_OBSERVED = "NOT_OBSERVED"
    OUT_OF_SCOPE_FOR_TARGET_TEMPLATE = "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    REFERENCE_NOT_YET_BUILT = "REFERENCE_NOT_YET_BUILT"


class DatasetRole(StrEnum):
    LOGIC_DEVELOPMENT = "LOGIC_DEVELOPMENT"
    CALIBRATION = "CALIBRATION"
    UNTOUCHED_HOLDOUT = "UNTOUCHED_HOLDOUT"
    VALIDATION = "VALIDATION"
    PRODUCTION_INPUT = "PRODUCTION_INPUT"


class PipelineState(StrEnum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    RENDERED = "RENDERED"
    PREPROCESSED = "PREPROCESSED"
    OCR_PARTIAL = "OCR_PARTIAL"
    OCR_COMPLETE = "OCR_COMPLETE"
    PARSED = "PARSED"
    MAPPED = "MAPPED"
    VALIDATED = "VALIDATED"
    EXPORTED = "EXPORTED"
    REFERENCE_COMPLETE = "REFERENCE_COMPLETE"
    COMPARED = "COMPARED"
    FAILED = "FAILED"


class PagePhase(StrEnum):
    COVER = "COVER"
    AUDIT_REPORT = "AUDIT_REPORT"
    MAIN_STATEMENTS = "MAIN_STATEMENTS"
    ACCOUNTING_POLICIES = "ACCOUNTING_POLICIES"
    QUANTITATIVE_NOTES = "QUANTITATIVE_NOTES"
    APPENDIX = "APPENDIX"
    NON_DATA = "NON_DATA"
    UNKNOWN = "UNKNOWN"


class RowType(StrEnum):
    DATA_ROW = "DATA_ROW"
    PARENT_ROW = "PARENT_ROW"
    CHILD_ROW = "CHILD_ROW"
    SUBTOTAL_ROW = "SUBTOTAL_ROW"
    TOTAL_ROW = "TOTAL_ROW"
    SECTION_HEADER = "SECTION_HEADER"
    UNIT_HEADER = "UNIT_HEADER"
    PERIOD_HEADER = "PERIOD_HEADER"
    NARRATIVE = "NARRATIVE"
    NON_DATA = "NON_DATA"


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("invalid bounding box coordinates")


@dataclass
class Provenance:
    document_hash: str
    page: int
    table_id: str | None = None
    row_id: str | None = None
    column_id: str | None = None
    label_bbox: BoundingBox | None = None
    value_bbox: BoundingBox | None = None
    header_bbox: BoundingBox | None = None
    unit_bbox: BoundingBox | None = None
    source_image_hash: str | None = None

    @property
    def has_cell_geometry(self) -> bool:
        return self.label_bbox is not None and self.value_bbox is not None


@dataclass
class EvidenceGate:
    cell_visible: bool = False
    numeric_reader_verified: bool = False
    primary_parser_agrees: bool = False
    period_bound_to_header: bool = False
    unit_has_source: bool = False
    sign_verified: bool = False
    schema_context_verified: bool = False
    no_pdf_history_conflict: bool = False
    accounting_passed: bool = False
    candidate_gap_sufficient: bool = False
    cell_geometry_present: bool = False

    def high_confidence_allowed(self) -> bool:
        return all(asdict(self).values())


@dataclass
class PipelineRecord:
    document_id: str
    statement_type: str
    raw_value: str | None
    normalized_value: str | None
    status: EvidenceStatus
    value_status: ValueStatus | None = None
    observation: ObservationKind | None = None
    provenance: Provenance | None = None
    schema_id: int | None = None
    canonical_name: str | None = None
    pdf_label: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    period_type: str | None = None
    current_or_comparative: str | None = None
    unit: str | None = None
    sign: str | None = None
    primary_ocr: str | None = None
    independent_ocr: str | None = None
    mapping_reason: str | None = None
    confidence: float | None = None
    candidate_list: list[dict[str, Any]] = field(default_factory=list)
    model_votes: list[dict[str, Any]] = field(default_factory=list)
    acceptance_gate: EvidenceGate = field(default_factory=EvidenceGate)
    rejection_reason: str | None = None

    def validate(self) -> None:
        if self.status is EvidenceStatus.AUTO_VERIFIED_HIGH:
            if self.provenance is None or not self.provenance.has_cell_geometry:
                raise ValueError("AUTO_VERIFIED_HIGH requires cell provenance")
            if not self.acceptance_gate.high_confidence_allowed():
                raise ValueError("AUTO_VERIFIED_HIGH requires every evidence gate")
        self._validate_value_status()

    def _validate_value_status(self) -> None:
        if self.value_status is None:
            # Backward-compatible path for historical artifacts. New extraction
            # records are required by their versioned producer to populate it.
            return
        if self.value_status is ValueStatus.NOT_OBSERVED:
            if self.status is not EvidenceStatus.NOT_OBSERVED:
                raise ValueError("NOT_OBSERVED value requires NOT_OBSERVED evidence status")
            if self.raw_value is not None or self.normalized_value is not None:
                raise ValueError("NOT_OBSERVED cannot carry a raw or normalized value")
            if self.observation is not None:
                raise ValueError("NOT_OBSERVED cannot carry a cell observation")
            return
        if self.status is EvidenceStatus.NOT_OBSERVED:
            raise ValueError("a visible/reference value cannot use NOT_OBSERVED evidence status")
        if self.value_status not in {
            ValueStatus.OBSERVED_VALUE,
            ValueStatus.OBSERVED_ZERO,
        }:
            return
        if self.raw_value is None or self.normalized_value is None:
            raise ValueError(f"{self.value_status.value} requires raw and normalized values")
        try:
            numeric = Decimal(self.normalized_value)
        except InvalidOperation as exc:
            raise ValueError(
                f"{self.value_status.value} requires a numeric normalized value"
            ) from exc
        if self.value_status is ValueStatus.OBSERVED_VALUE:
            if numeric == 0 or self.observation is not ObservationKind.VALUE:
                raise ValueError("OBSERVED_VALUE requires a visible non-zero VALUE observation")
        elif numeric != 0 or self.observation not in {
            ObservationKind.ZERO,
            ObservationKind.DASH,
            ObservationKind.BLANK,
        }:
            raise ValueError(
                "OBSERVED_ZERO requires normalized zero and ZERO, DASH, or BLANK observation"
            )
