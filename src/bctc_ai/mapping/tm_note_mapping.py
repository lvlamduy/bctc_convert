"""Scoped, value-blind item reconciliation for MBB TM PDF page 30."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import yaml
from PIL import Image
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.registry import SchemaItem

TM_PAGE30_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page30-v1.yaml")
TM_SCHEMA_ITEM_COUNT = 1705
TM_PAGE30_SOURCE_ROW_COUNT = 22
TM_PAGE30_FIXED_MAPPING_COUNT = 21
TM_PAGE30_SOURCE_MAPPED_COUNT = 22
TM_PAGE30_AGGREGATE_COMPONENT_COUNT = 2
TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT = 0
TM_PAGE30_SOURCE_ONLY_COUNT = 0
TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT = 2
TM_PAGE30_STRUCTURAL_BLANK_COUNT = 2
TM_PAGE30_NUMERIC_TARGET_COUNT = 19
TM_PAGE30_MAPPED_VALUE_COUNT = 38
TM_PAGE30_ACCOUNTING_CHECK_COUNT = 14
TM_PAGE30_FIXED_IDS = (
    561,
    562,
    563,
    565,
    569,
    570,
    571,
    572,
    574,
    575,
    576,
    577,
    578,
    579,
    580,
    581,
    582,
    585,
    586,
    588,
    5718,
)
# Public compatibility symbol: Q017 resolved the former pair to new aggregate ID 5718.
TM_PAGE30_AMBIGUOUS_IDS: tuple[int, ...] = ()
TM_PAGE30_NOT_OBSERVED_IDS = (583, 590)
TM_PAGE30_AGGREGATE_TARGET_ID = 574
TM_PAGE30_PROVISION_TOTAL_ID = 5718
TM_PAGE30_AGGREGATE_COMPONENT_IDENTITIES = (("2", 4), ("2", 5))
TM_PAGE30_EXPECTED_AGGREGATE_VALUES = (2_223_753, 2_258_533)
TM_PAGE30_EXPECTED_PROVISION_VALUES = (-10_785, -9_096)
TM_PAGE30_EXPECTED_SOURCE_TARGET_IDS = (
    562,
    563,
    565,
    561,
    570,
    571,
    572,
    574,
    574,
    569,
    576,
    577,
    578,
    579,
    580,
    581,
    582,
    585,
    586,
    588,
    5718,
    575,
)
TM_PAGE30_DEEPSEEK_CONFIG_SHA256 = (
    "aebbc2fb4c9d6da22d83b71ca79567fca2c904a48c686ced8121438d42f31d6d"
)
TM_PAGE30_DEEPSEEK_MODEL_SHA256 = "d8ff67a424ba6f4dd077885eb9d6a05d2537e76fe5491f0e2a9b712f8c8870fa"
TM_PAGE30_TARGETED_REREAD_ROW_IDS = (
    "page-0030:note-2:row-0003",
    "page-0030:note-3:row-0004",
    "page-0030:note-3:row-0007",
    "page-0030:note-3:row-0010",
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_INPUTS = {
    "numeric_cell_text",
    "numeric_cell_value",
    "numeric_value_magnitude",
    "accounting_equation_result",
    "period_or_unit_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "parser_candidate_report_norm_ids",
}
_BASE_MAPPING_INPUTS = (
    "TM_SCHEMA_ID_NAME_ORDER",
    "SOURCE_VISIBLE_PPOCR_LABELS",
    "VISIBLE_THREE_NOTE_HIERARCHY_AND_LOCAL_ROW_ORDER",
    "SOURCE_PDF_PIXEL_GEOMETRY_AT_LABEL_BOXES",
)


class TMNoteMappingError(ValueError):
    """Raised when page-30 mapping evidence or reconciliation is malformed."""


class TMRuleDisposition(StrEnum):
    FIXED = "FIXED"
    AGGREGATE_COMPONENT = "AGGREGATE_COMPONENT"
    AMBIGUOUS = "AMBIGUOUS"
    SOURCE_ONLY = "SOURCE_ONLY"


class TMSchemaMappingStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    UNASSESSED = "UNASSESSED"


class TMSourceMappingStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    SOURCE_ONLY_PDF_ROW = "SOURCE_ONLY_PDF_ROW"


class TMSemanticReaderStatus(StrEnum):
    COMPLETE = "COMPLETE"
    BLOCKED_RUNTIME_PACKAGE_DRIFT = "BLOCKED_RUNTIME_PACKAGE_DRIFT"
    NOT_RUN = "NOT_RUN"
    LABEL_DISAGREEMENT = "LABEL_DISAGREEMENT"


@dataclass(frozen=True)
class TMSemanticCropAttempt:
    attempt_kind: str
    crop_bbox: tuple[int, int, int, int]
    crop_sha256: str
    proposal_text: str
    status: str


@dataclass(frozen=True)
class TMSemanticLabelSample:
    row_id: str
    selected_attempt_index: int
    attempts: tuple[TMSemanticCropAttempt, ...]

    @property
    def selected_attempt(self) -> TMSemanticCropAttempt:
        return self.attempts[self.selected_attempt_index]


@dataclass(frozen=True)
class TMPage30SemanticEvidence:
    source_path: Path
    evidence_sha256: str
    reader_id: str
    reader_status: str
    source_render_sha256: str
    config_sha256: str
    model_weights_sha256: str
    samples: tuple[TMSemanticLabelSample, ...]

    @property
    def labels_by_row(self) -> dict[str, str]:
        return {sample.row_id: sample.selected_attempt.proposal_text for sample in self.samples}


@dataclass(frozen=True)
class TMPage30RowRule:
    note_number: str
    ordinal: int
    visible_label_anchor: str
    expected_row_kind: str
    expected_source_role: str
    disposition: TMRuleDisposition
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.note_number, self.ordinal


@dataclass(frozen=True)
class TMPage30MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    mapping_authority_scope: str
    source_pdf_sha256: str
    source_render_sha256: str
    render_dpi: int
    schema_total: int
    visible_source_row_total: int
    fixed_mapping_total: int
    aggregate_component_source_row_total: int
    ambiguous_source_row_total: int
    ambiguous_schema_item_total: int
    source_only_row_total: int
    not_observed_schema_item_total: int
    not_observed_schema_ids: tuple[int, ...]
    structural_blank_row_total: int
    minimum_independent_semantic_streams: int
    minimum_ppocr_anchor_similarity: float
    minimum_independent_anchor_similarity: float
    minimum_cross_reader_label_similarity: float
    minimum_label_crop_ink_fraction: float
    rows: tuple[TMPage30RowRule, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage30SourceRow:
    row_id: str
    order: int
    note_number: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    label_bbox: BoundingBox
    source_reader_id: str


@dataclass(frozen=True)
class TMPage30GeometryEvidence:
    source_pdf_path: str
    source_pdf_sha256: str
    page_number: int
    render_dpi: int
    rendered_width: int
    rendered_height: int
    source_render_sha256: str
    embedded_image_count: int
    pdf_text_token_count: int
    pdf_text_available: bool
    label_row_count: int
    verified_label_row_count: int
    minimum_observed_ink_fraction: float
    semantic_crop_attempt_count: int
    verified_semantic_crop_attempt_count: int
    semantic_crop_geometry_sha256: str | None
    geometry_sha256: str


@dataclass(frozen=True)
class TMSchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    ppocr_label_similarity: float | None
    independent_label_similarity: float | None
    cross_reader_label_similarity: float | None
    supporting_reader_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMSourceDisposition:
    row_id: str
    order: int
    note_number: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    value_presence: str
    status: str
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    ppocr_label_similarity: float
    independent_label_similarity: float | None
    cross_reader_label_similarity: float | None
    supporting_reader_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage30MappedValue:
    report_norm_id: int
    axis_id: str
    axis_ordinal: int
    current_or_comparative: str
    period_start: str
    period_end: str
    period_type: str
    canonical_unit: str
    unit_multiplier: int
    observation: str
    reported_value: str
    canonical_value_vnd: int
    aggregation: str
    source_row_ids: tuple[str, ...]
    source_raw_values: tuple[str, ...]
    source_reported_values: tuple[str, ...]
    source_value_line_indices: tuple[tuple[int, ...], ...]
    source_value_bboxes: tuple[BoundingBox, ...]


@dataclass(frozen=True)
class TMPage30AccountingCheck:
    check_id: str
    axis_id: str
    current_or_comparative: str
    target_report_norm_id: int
    target_reported_value: str
    operand_report_norm_ids: tuple[int, ...]
    operand_source_row_ids: tuple[str, ...]
    operand_reported_values: tuple[str, ...]
    residual_reported_unit: str
    status: str


@dataclass(frozen=True)
class TMPage30MappingResult:
    statement_type: str
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    status: str
    mapping_authority_scope: str
    mapping_authority_granted: bool
    automatic_fixed_selection_allowed: bool
    complete_page_mapping_resolved: bool
    independent_semantic_stream_count: int
    minimum_independent_semantic_streams: int
    source_reader_id: str
    independent_reader_id: str | None
    independent_reader_status: str
    independent_reader_blocker: str | None
    schema_item_count: int
    assessed_schema_count: int
    mapped_schema_count: int
    candidate_linked_schema_count: int
    not_observed_schema_count: int
    ambiguous_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    candidate_linked_source_row_count: int
    ambiguous_source_row_count: int
    source_only_row_count: int
    structural_blank_source_row_count: int
    mapped_value_count: int
    accounting_check_count: int
    accounting_pass_count: int
    schema_dispositions: tuple[TMSchemaDisposition, ...]
    source_dispositions: tuple[TMSourceDisposition, ...]
    mapped_values: tuple[TMPage30MappedValue, ...]
    accounting_checks: tuple[TMPage30AccountingCheck, ...]
    geometry_evidence: TMPage30GeometryEvidence
    schema_projection_sha256: str
    policy_sha256: str
    source_label_sha256: str
    independent_label_sha256: str | None
    independent_evidence_sha256: str | None
    mapping_inputs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _required_int(payload: Mapping[str, Any], name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TMNoteMappingError(f"invalid TM mapping integer: {name}")
    return value


def _required_score(payload: Mapping[str, Any], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise TMNoteMappingError(f"invalid TM mapping score: {name}")
    return float(value)


def _required_sha256(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise TMNoteMappingError(f"invalid TM mapping SHA-256: {name}")
    return value


def load_tm_page30_mapping_policy(path: Path) -> TMPage30MappingPolicy:
    """Load and validate the bounded MBB page-30 mapping policy."""

    resolved = path.resolve()
    try:
        source_bytes = resolved.read_bytes()
        payload = yaml.safe_load(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise TMNoteMappingError(f"cannot load TM page-30 mapping policy: {path}") from exc
    if not isinstance(payload, Mapping) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE30_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
    ):
        raise TMNoteMappingError("TM page-30 mapping policy identity drifted")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        raise TMNoteMappingError("TM page-30 row rules are absent")
    expected_keys = {
        "note_number",
        "ordinal",
        "visible_label_anchor",
        "expected_row_kind",
        "expected_source_role",
        "disposition",
        "candidate_report_norm_ids",
    }
    rules = []
    for raw in raw_rows:
        if not isinstance(raw, Mapping) or set(raw) != expected_keys:
            raise TMNoteMappingError("TM page-30 row rule keyset is invalid")
        note_number = str(raw.get("note_number", ""))
        ordinal = raw.get("ordinal")
        anchor = retrieval_key(str(raw.get("visible_label_anchor", "")))
        candidate_ids = raw.get("candidate_report_norm_ids")
        try:
            disposition = TMRuleDisposition(str(raw.get("disposition", "")))
        except ValueError as exc:
            raise TMNoteMappingError("TM row-rule disposition is invalid") from exc
        if (
            not note_number.isdigit()
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal < 1
            or not anchor
            or raw.get("expected_row_kind") not in {"NUMERIC", "LABEL_ONLY"}
            or raw.get("expected_source_role") not in {"DETAIL", "GROUP_LABEL", "TABLE_TOTAL"}
            or not isinstance(candidate_ids, list)
            or any(isinstance(item, bool) or not isinstance(item, int) for item in candidate_ids)
        ):
            raise TMNoteMappingError("TM page-30 row rule is malformed")
        if (
            (
                disposition in {TMRuleDisposition.FIXED, TMRuleDisposition.AGGREGATE_COMPONENT}
                and len(candidate_ids) != 1
            )
            or (disposition is TMRuleDisposition.AMBIGUOUS and len(candidate_ids) < 2)
            or (disposition is TMRuleDisposition.SOURCE_ONLY and candidate_ids)
        ):
            raise TMNoteMappingError("TM row-rule candidate cardinality is invalid")
        rules.append(
            TMPage30RowRule(
                note_number=note_number,
                ordinal=ordinal,
                visible_label_anchor=anchor,
                expected_row_kind=str(raw["expected_row_kind"]),
                expected_source_role=str(raw["expected_source_role"]),
                disposition=disposition,
                candidate_report_norm_ids=tuple(candidate_ids),
            )
        )
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _FORBIDDEN_INPUTS:
        raise TMNoteMappingError("TM forbidden mapping inputs drifted")
    raw_not_observed = payload.get("not_observed_schema_ids")
    if (
        not isinstance(raw_not_observed, list)
        or any(
            isinstance(report_norm_id, bool) or not isinstance(report_norm_id, int)
            for report_norm_id in raw_not_observed
        )
        or len(raw_not_observed) != len(set(raw_not_observed))
    ):
        raise TMNoteMappingError("TM page-30 not-observed schema IDs are invalid")
    policy = TMPage30MappingPolicy(
        source_path=resolved,
        document=str(payload.get("document", "")),
        page_number=_required_int(payload, "page_number"),
        page_tag=str(payload.get("page_tag", "")),
        report_scope=str(payload.get("report_scope", "")),
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=_required_sha256(payload, "source_pdf_sha256"),
        source_render_sha256=_required_sha256(payload, "source_render_sha256"),
        render_dpi=_required_int(payload, "render_dpi"),
        schema_total=_required_int(payload, "schema_total"),
        visible_source_row_total=_required_int(payload, "visible_source_row_total"),
        fixed_mapping_total=_required_int(payload, "fixed_mapping_total"),
        aggregate_component_source_row_total=_required_int(
            payload, "aggregate_component_source_row_total"
        ),
        ambiguous_source_row_total=_required_int(payload, "ambiguous_source_row_total"),
        ambiguous_schema_item_total=_required_int(payload, "ambiguous_schema_item_total"),
        source_only_row_total=_required_int(payload, "source_only_row_total"),
        not_observed_schema_item_total=_required_int(payload, "not_observed_schema_item_total"),
        not_observed_schema_ids=tuple(raw_not_observed),
        structural_blank_row_total=_required_int(payload, "structural_blank_row_total"),
        minimum_independent_semantic_streams=_required_int(
            payload, "minimum_independent_semantic_streams_for_automatic_fixed_selection"
        ),
        minimum_ppocr_anchor_similarity=_required_score(payload, "minimum_ppocr_anchor_similarity"),
        minimum_independent_anchor_similarity=_required_score(
            payload, "minimum_independent_anchor_similarity"
        ),
        minimum_cross_reader_label_similarity=_required_score(
            payload, "minimum_cross_reader_label_similarity"
        ),
        minimum_label_crop_ink_fraction=_required_score(payload, "minimum_label_crop_ink_fraction"),
        rows=tuple(rules),
        forbidden_mapping_inputs=tuple(str(item) for item in forbidden),
        policy_sha256=hashlib.sha256(source_bytes).hexdigest(),
    )
    identities = tuple(rule.identity for rule in policy.rows)
    fixed_ids = tuple(
        rule.candidate_report_norm_ids[0]
        for rule in policy.rows
        if rule.disposition in {TMRuleDisposition.FIXED, TMRuleDisposition.AGGREGATE_COMPONENT}
    )
    ambiguous_ids = tuple(
        report_norm_id
        for rule in policy.rows
        if rule.disposition is TMRuleDisposition.AMBIGUOUS
        for report_norm_id in rule.candidate_report_norm_ids
    )
    if (
        policy.document != "MBB_CONSOLIDATED_Q1_2026"
        or policy.page_number != 30
        or policy.page_tag != "page-0030"
        or policy.report_scope != "CONSOLIDATED"
        or not policy.mapping_authority_scope.endswith(
            "PDF_PAGE_30_FIXED_AND_DECLARED_AGGREGATE_ROWS_ONLY"
        )
        or policy.render_dpi != 300
        or policy.schema_total != TM_SCHEMA_ITEM_COUNT
        or policy.visible_source_row_total != TM_PAGE30_SOURCE_ROW_COUNT
        or policy.fixed_mapping_total != TM_PAGE30_FIXED_MAPPING_COUNT
        or policy.aggregate_component_source_row_total != TM_PAGE30_AGGREGATE_COMPONENT_COUNT
        or policy.ambiguous_source_row_total != 0
        or policy.ambiguous_schema_item_total != TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        or policy.source_only_row_total != TM_PAGE30_SOURCE_ONLY_COUNT
        or policy.not_observed_schema_item_total != TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT
        or policy.not_observed_schema_ids != TM_PAGE30_NOT_OBSERVED_IDS
        or policy.structural_blank_row_total != TM_PAGE30_STRUCTURAL_BLANK_COUNT
        or policy.minimum_independent_semantic_streams < 2
        or len(policy.rows) != TM_PAGE30_SOURCE_ROW_COUNT
        or len(set(identities)) != len(identities)
        or set(fixed_ids) != set(TM_PAGE30_FIXED_IDS)
        or len(fixed_ids) != TM_PAGE30_SOURCE_MAPPED_COUNT
        or fixed_ids.count(TM_PAGE30_AGGREGATE_TARGET_ID) != 2
        or any(
            fixed_ids.count(report_norm_id) != 1
            for report_norm_id in TM_PAGE30_FIXED_IDS
            if report_norm_id != TM_PAGE30_AGGREGATE_TARGET_ID
        )
        or ambiguous_ids
        or tuple(
            rule.identity
            for rule in policy.rows
            if rule.disposition is TMRuleDisposition.AGGREGATE_COMPONENT
        )
        != TM_PAGE30_AGGREGATE_COMPONENT_IDENTITIES
        or next(
            rule.candidate_report_norm_ids for rule in policy.rows if rule.identity == ("3", 11)
        )
        != (TM_PAGE30_PROVISION_TOTAL_ID,)
        or sum(rule.disposition is TMRuleDisposition.SOURCE_ONLY for rule in policy.rows)
        != TM_PAGE30_SOURCE_ONLY_COUNT
        or sum(rule.expected_row_kind == "LABEL_ONLY" for rule in policy.rows)
        != TM_PAGE30_STRUCTURAL_BLANK_COUNT
    ):
        raise TMNoteMappingError("TM page-30 policy coverage identity drifted")
    return policy


def load_tm_page30_deepseek_evidence(path: Path) -> TMPage30SemanticEvidence:
    """Load the reference-blind DeepSeek label stream and its crop provenance."""

    resolved = path.resolve()
    try:
        source_bytes = resolved.read_bytes()
        payload = json.loads(source_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TMNoteMappingError(f"cannot load TM page-30 DeepSeek evidence: {path}") from exc
    if not isinstance(payload, Mapping):
        raise TMNoteMappingError("TM DeepSeek evidence root is invalid")
    runtime = payload.get("runtime_packages")
    crop_policy = payload.get("crop_policy")
    if (
        payload.get("format_version") != 1
        or payload.get("document") != "MBB_CONSOLIDATED_Q1_2026"
        or payload.get("page_number") != 30
        or payload.get("page_tag") != "page-0030"
        or payload.get("reader") != "DEEPSEEK_OCR_2"
        or payload.get("reader_status") != TMSemanticReaderStatus.COMPLETE.value
        or payload.get("evidence_role") != "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"
        or payload.get("prompt") != "<image>\\nFree OCR."
        or payload.get("network_permitted") is not False
        or payload.get("numeric_values_available_to_reader") is not False
        or payload.get("reference_text_available_to_reader") is not False
        or payload.get("schema_available_to_reader") is not False
        or payload.get("config_sha256") != TM_PAGE30_DEEPSEEK_CONFIG_SHA256
        or payload.get("model_weights_sha256") != TM_PAGE30_DEEPSEEK_MODEL_SHA256
        or _SHA256.fullmatch(str(payload.get("base_config_sha256", ""))) is None
        or _SHA256.fullmatch(str(payload.get("source_render_sha256", ""))) is None
        or not isinstance(runtime, Mapping)
        or runtime.get("transformers") != "4.46.3"
        or runtime.get("addict") != "2.4.0"
        or runtime.get("matplotlib") != "3.10.8"
        or not isinstance(crop_policy, Mapping)
        or crop_policy.get("aspect_preservation") != "OFFICIAL_IMAGEOPS_PAD"
        or crop_policy.get("initial_padding_pixels") != {"x": 28, "y": 14}
        or crop_policy.get("targeted_tight_padding_pixels") != {"x": 4, "y": 8}
        or crop_policy.get("targeted_reread_trigger")
        != "PP_DEEPSEEK_RETRIEVAL_KEY_RATIO_BELOW_0_84"
        or payload.get("sample_count") != TM_PAGE30_SOURCE_ROW_COUNT
    ):
        raise TMNoteMappingError("TM DeepSeek evidence identity/runtime contract drifted")

    expected_row_ids = tuple(
        f"page-0030:note-{note_number}:row-{ordinal:04d}"
        for note_number, count in ((1, 4), (2, 6), (3, 12))
        for ordinal in range(1, count + 1)
    )
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list) or len(raw_samples) != len(expected_row_ids):
        raise TMNoteMappingError("TM DeepSeek evidence sample denominator drifted")
    samples = []
    for expected_row_id, raw_sample in zip(expected_row_ids, raw_samples, strict=True):
        if not isinstance(raw_sample, Mapping) or set(raw_sample) != {
            "row_id",
            "selected_attempt_index",
            "attempts",
        }:
            raise TMNoteMappingError("TM DeepSeek sample keyset is invalid")
        row_id = raw_sample.get("row_id")
        selected_index = raw_sample.get("selected_attempt_index")
        raw_attempts = raw_sample.get("attempts")
        expected_attempt_count = 2 if row_id in TM_PAGE30_TARGETED_REREAD_ROW_IDS else 1
        expected_selected_index = expected_attempt_count - 1
        if (
            row_id != expected_row_id
            or isinstance(selected_index, bool)
            or selected_index != expected_selected_index
            or not isinstance(raw_attempts, list)
            or len(raw_attempts) != expected_attempt_count
        ):
            raise TMNoteMappingError("TM DeepSeek sample identity/retry contract drifted")
        attempts = []
        for attempt_index, raw_attempt in enumerate(raw_attempts):
            if not isinstance(raw_attempt, Mapping) or set(raw_attempt) != {
                "attempt_kind",
                "crop_bbox",
                "crop_sha256",
                "proposal_text",
                "status",
            }:
                raise TMNoteMappingError("TM DeepSeek crop-attempt keyset is invalid")
            bbox = raw_attempt.get("crop_bbox")
            expected_kind = "TARGETED_TIGHT_LABEL" if attempt_index else "INITIAL_PADDED_LABEL"
            proposal = raw_attempt.get("proposal_text")
            if (
                raw_attempt.get("attempt_kind") != expected_kind
                or not isinstance(bbox, list)
                or len(bbox) != 4
                or any(isinstance(value, bool) or not isinstance(value, int) for value in bbox)
                or bbox[2] <= bbox[0]
                or bbox[3] <= bbox[1]
                or _SHA256.fullmatch(str(raw_attempt.get("crop_sha256", ""))) is None
                or not isinstance(proposal, str)
                or not retrieval_key(proposal)
                or raw_attempt.get("status") != "PARSED_SEMANTIC_PROPOSAL_ONLY"
            ):
                raise TMNoteMappingError("TM DeepSeek crop attempt is malformed")
            attempts.append(
                TMSemanticCropAttempt(
                    attempt_kind=expected_kind,
                    crop_bbox=tuple(bbox),
                    crop_sha256=str(raw_attempt["crop_sha256"]),
                    proposal_text=proposal,
                    status=str(raw_attempt["status"]),
                )
            )
        samples.append(
            TMSemanticLabelSample(
                row_id=expected_row_id,
                selected_attempt_index=selected_index,
                attempts=tuple(attempts),
            )
        )
    return TMPage30SemanticEvidence(
        source_path=resolved,
        evidence_sha256=hashlib.sha256(source_bytes).hexdigest(),
        reader_id="deepseek-ocr-2",
        reader_status=TMSemanticReaderStatus.COMPLETE.value,
        source_render_sha256=str(payload["source_render_sha256"]),
        config_sha256=str(payload["config_sha256"]),
        model_weights_sha256=str(payload["model_weights_sha256"]),
        samples=tuple(samples),
    )


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def adapt_tm_page30_rows(
    logical_rows: Sequence[object],
    *,
    source_reader_id: str = "ppocrv6-word-box",
) -> tuple[TMPage30SourceRow, ...]:
    """Read row identity, label, hierarchy and label geometry, never numeric cells."""

    if isinstance(logical_rows, (str, bytes)) or not isinstance(logical_rows, Sequence):
        raise TMNoteMappingError("TM page-30 logical rows must be a sequence")
    if not isinstance(source_reader_id, str) or not source_reader_id:
        raise TMNoteMappingError("TM source reader identity is invalid")
    rows = []
    for order, raw in enumerate(logical_rows):
        reader_row = _field(raw, "row")
        label = _field(reader_row, "label") if reader_row is not None else _field(raw, "label")
        row_id = _field(raw, "row_id")
        note_number = str(_field(raw, "note_number"))
        ordinal = _field(raw, "ordinal")
        row_kind = str(_field(raw, "row_kind"))
        source_role = str(_field(raw, "source_role"))
        label_bbox = _field(raw, "label_bbox")
        if (
            not isinstance(row_id, str)
            or not row_id
            or not note_number.isdigit()
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal < 1
            or not isinstance(label, str)
            or not retrieval_key(label)
            or row_kind not in {"NUMERIC", "LABEL_ONLY"}
            or source_role not in {"DETAIL", "GROUP_LABEL", "TABLE_TOTAL"}
            or not isinstance(label_bbox, BoundingBox)
            or label_bbox.x1 <= label_bbox.x0
            or label_bbox.y1 <= label_bbox.y0
        ):
            raise TMNoteMappingError("TM parser row label/hierarchy evidence is invalid")
        rows.append(
            TMPage30SourceRow(
                row_id=row_id,
                order=order,
                note_number=note_number,
                ordinal=ordinal,
                visible_label=label,
                row_kind=row_kind,
                source_role=source_role,
                label_bbox=label_bbox,
                source_reader_id=source_reader_id,
            )
        )
    if len(rows) != TM_PAGE30_SOURCE_ROW_COUNT or len({row.row_id for row in rows}) != len(rows):
        raise TMNoteMappingError("TM page-30 source row denominator or identity is invalid")
    return tuple(rows)


def _label_similarity(label: str, anchor: str) -> float:
    return ratio(retrieval_key(label), anchor) / 100


def _label_digest(rows: Sequence[TMPage30SourceRow]) -> str:
    payload = [
        {
            "row_id": row.row_id,
            "order": row.order,
            "note_number": row.note_number,
            "ordinal": row.ordinal,
            "visible_label": row.visible_label,
            "row_kind": row.row_kind,
            "source_role": row.source_role,
            "source_reader_id": row.source_reader_id,
        }
        for row in rows
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _independent_label_digest(reader_id: str, labels: Mapping[str, str]) -> str:
    payload = {
        "reader_id": reader_id,
        "labels": [{"row_id": row_id, "label": labels[row_id]} for row_id in sorted(labels)],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _schema_projection(items: Sequence[SchemaItem]) -> tuple[tuple[SchemaItem, ...], str]:
    tm = tuple(
        sorted(
            (item for item in items if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if (
        len(tm) != TM_SCHEMA_ITEM_COUNT
        or [item.display_order for item in tm] != list(range(TM_SCHEMA_ITEM_COUNT))
        or len({item.schema_id for item in tm}) != len(tm)
    ):
        raise TMNoteMappingError("TM schema denominator/order is not exactly 1,386")
    payload = [
        {
            "report_norm_id": item.schema_id,
            "display_order": item.display_order,
            "canonical_name": item.canonical_name,
        }
        for item in tm
    ]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return tm, digest


def verify_tm_page30_source_geometry(
    source_pdf_path: Path,
    rows: Sequence[TMPage30SourceRow],
    policy: TMPage30MappingPolicy,
    semantic_evidence: TMPage30SemanticEvidence | None = None,
) -> TMPage30GeometryEvidence:
    """Bind PP-OCR label boxes back to source PDF pixels and audit absent text."""

    if not source_pdf_path.is_file() or sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMNoteMappingError("TM source PDF is absent or hash-drifted")
    try:
        with fitz.open(source_pdf_path) as document:
            if document.needs_pass or document.page_count < policy.page_number:
                raise TMNoteMappingError("TM source PDF cannot expose requested page 30")
            page = document[policy.page_number - 1]
            pdf_words = page.get_text("words")
            embedded_image_count = len(page.get_image_info(xrefs=True))
            scale = policy.render_dpi / 72.0
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
            )
            payload = pixmap.tobytes("png")
    except (RuntimeError, ValueError, OSError) as exc:
        if isinstance(exc, TMNoteMappingError):
            raise
        raise TMNoteMappingError("cannot inspect TM page-30 PDF source geometry") from exc
    render_sha256 = hashlib.sha256(payload).hexdigest()
    if render_sha256 != policy.source_render_sha256:
        raise TMNoteMappingError("TM page-30 deterministic render hash drifted")
    try:
        source_image = Image.open(BytesIO(payload)).convert("RGB")
        source_image.load()
        image = source_image.convert("L")
        image.load()
    except OSError as exc:
        raise TMNoteMappingError("cannot decode deterministic TM page-30 render") from exc
    records = []
    for row in rows:
        bbox = row.label_bbox
        coordinates = (
            max(0, math.floor(bbox.x0)),
            max(0, math.floor(bbox.y0)),
            min(image.width, math.ceil(bbox.x1)),
            min(image.height, math.ceil(bbox.y1)),
        )
        if coordinates[2] <= coordinates[0] or coordinates[3] <= coordinates[1]:
            raise TMNoteMappingError(f"TM label box escapes render: {row.row_id}")
        crop = image.crop(coordinates)
        histogram = crop.histogram()
        dark_pixels = sum(histogram[:220])
        pixel_count = crop.width * crop.height
        ink_fraction = dark_pixels / pixel_count
        records.append(
            {
                "row_id": row.row_id,
                "bbox": coordinates,
                "dark_pixel_count": dark_pixels,
                "pixel_count": pixel_count,
                "ink_fraction": round(ink_fraction, 8),
            }
        )
    verified = sum(
        record["ink_fraction"] >= policy.minimum_label_crop_ink_fraction for record in records
    )
    if verified != len(rows):
        raise TMNoteMappingError("one or more TM label boxes lack visible source-pixel evidence")
    geometry_sha256 = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    semantic_records = []
    if semantic_evidence is not None:
        if semantic_evidence.source_render_sha256 != render_sha256 or tuple(
            sample.row_id for sample in semantic_evidence.samples
        ) != tuple(row.row_id for row in rows):
            raise TMNoteMappingError("TM DeepSeek evidence is not bound to this render/row order")
        row_by_id = {row.row_id: row for row in rows}
        for sample in semantic_evidence.samples:
            row = row_by_id[sample.row_id]
            for attempt in sample.attempts:
                pad_x, pad_y = (
                    (28, 14) if attempt.attempt_kind == "INITIAL_PADDED_LABEL" else (4, 8)
                )
                expected_bbox = (
                    max(0, math.floor(row.label_bbox.x0) - pad_x),
                    max(0, math.floor(row.label_bbox.y0) - pad_y),
                    min(source_image.width, math.ceil(row.label_bbox.x1) + pad_x),
                    min(source_image.height, math.ceil(row.label_bbox.y1) + pad_y),
                )
                if attempt.crop_bbox != expected_bbox:
                    raise TMNoteMappingError(f"TM DeepSeek crop geometry drifted: {sample.row_id}")
                crop_buffer = BytesIO()
                source_image.crop(expected_bbox).save(crop_buffer, format="PNG")
                actual_sha256 = hashlib.sha256(crop_buffer.getvalue()).hexdigest()
                if actual_sha256 != attempt.crop_sha256:
                    raise TMNoteMappingError(f"TM DeepSeek crop pixels drifted: {sample.row_id}")
                semantic_records.append(
                    {
                        "row_id": sample.row_id,
                        "attempt_kind": attempt.attempt_kind,
                        "crop_bbox": expected_bbox,
                        "crop_sha256": actual_sha256,
                    }
                )
    semantic_digest = (
        hashlib.sha256(
            json.dumps(semantic_records, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if semantic_records
        else None
    )
    return TMPage30GeometryEvidence(
        source_pdf_path=source_pdf_path.as_posix(),
        source_pdf_sha256=policy.source_pdf_sha256,
        page_number=policy.page_number,
        render_dpi=policy.render_dpi,
        rendered_width=image.width,
        rendered_height=image.height,
        source_render_sha256=render_sha256,
        embedded_image_count=embedded_image_count,
        pdf_text_token_count=len(pdf_words),
        pdf_text_available=bool(pdf_words),
        label_row_count=len(rows),
        verified_label_row_count=verified,
        minimum_observed_ink_fraction=round(min(record["ink_fraction"] for record in records), 8),
        semantic_crop_attempt_count=len(semantic_records),
        verified_semantic_crop_attempt_count=len(semantic_records),
        semantic_crop_geometry_sha256=semantic_digest,
        geometry_sha256=geometry_sha256,
    )


def _independent_support(
    rows: tuple[TMPage30SourceRow, ...],
    rules: tuple[TMPage30RowRule, ...],
    policy: TMPage30MappingPolicy,
    *,
    independent_labels_by_row: Mapping[str, str] | None,
    independent_reader_id: str | None,
    independent_reader_status: TMSemanticReaderStatus,
) -> tuple[
    bool,
    str,
    dict[str, tuple[float, float]],
    str | None,
]:
    if independent_labels_by_row is None:
        if independent_reader_status is TMSemanticReaderStatus.COMPLETE:
            raise TMNoteMappingError("complete independent reader omitted its label stream")
        return False, independent_reader_status.value, {}, None
    if independent_reader_status is not TMSemanticReaderStatus.COMPLETE:
        raise TMNoteMappingError("incomplete independent reader cannot provide labels")
    if (
        not isinstance(independent_reader_id, str)
        or not independent_reader_id
        or independent_reader_id == rows[0].source_reader_id
    ):
        raise TMNoteMappingError("TM independent semantic reader identity is invalid")
    row_ids = {row.row_id for row in rows}
    if set(independent_labels_by_row) != row_ids or any(
        not isinstance(value, str) or not retrieval_key(value)
        for value in independent_labels_by_row.values()
    ):
        raise TMNoteMappingError("TM independent semantic stream must cover all 22 labels")
    scores = {}
    all_supported = True
    for row, rule in zip(rows, rules, strict=True):
        independent_label = independent_labels_by_row[row.row_id]
        anchor_similarity = _label_similarity(independent_label, rule.visible_label_anchor)
        cross_similarity = (
            ratio(retrieval_key(row.visible_label), retrieval_key(independent_label)) / 100
        )
        scores[row.row_id] = (anchor_similarity, cross_similarity)
        all_supported &= (
            anchor_similarity >= policy.minimum_independent_anchor_similarity
            and cross_similarity >= policy.minimum_cross_reader_label_similarity
        )
    digest = _independent_label_digest(independent_reader_id, independent_labels_by_row)
    status = (
        TMSemanticReaderStatus.COMPLETE.value
        if all_supported
        else TMSemanticReaderStatus.LABEL_DISAGREEMENT.value
    )
    return all_supported, status, scores, digest


def _reported_integer_cell(raw_row: object, axis_index: int) -> tuple[Decimal, str, str]:
    reader_row = _field(raw_row, "row")
    cells = _field(reader_row, "cells")
    if isinstance(cells, (str, bytes)) or not isinstance(cells, Sequence) or len(cells) != 2:
        raise TMNoteMappingError("TM page-30 numeric row does not expose two cells")
    cell = cells[axis_index]
    observation = str(_field(cell, "observation"))
    value = _field(cell, "value")
    raw_text = _field(cell, "raw_text")
    if (
        observation not in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
        or not isinstance(value, Decimal)
        or value != value.to_integral_value()
        or not isinstance(raw_text, str)
        or not raw_text
    ):
        raise TMNoteMappingError("TM page-30 mapped numeric cell is invalid or non-integral")
    return value, raw_text, observation


def _validate_structural_blank_row(raw_row: object) -> None:
    reader_row = _field(raw_row, "row")
    cells = _field(reader_row, "cells")
    if (
        isinstance(cells, (str, bytes))
        or not isinstance(cells, Sequence)
        or len(cells) != 2
        or any(
            str(_field(cell, "observation")) != ObservationKind.BLANK.value
            or _field(cell, "value") is not None
            for cell in cells
        )
    ):
        raise TMNoteMappingError("TM page-30 structural row unexpectedly carries a value")


def _build_mapped_values_and_checks(
    parsed_page: object,
    rows_by_schema: Mapping[int, tuple[TMPage30SourceRow, ...]],
) -> tuple[tuple[TMPage30MappedValue, ...], tuple[TMPage30AccountingCheck, ...]]:
    raw_rows = _field(parsed_page, "rows")
    axes = _field(parsed_page, "axes")
    if (
        isinstance(raw_rows, (str, bytes))
        or not isinstance(raw_rows, Sequence)
        or isinstance(axes, (str, bytes))
        or not isinstance(axes, Sequence)
        or len(axes) != 2
    ):
        raise TMNoteMappingError("TM page-30 value/axis evidence is absent")
    raw_by_id = {_field(row, "row_id"): row for row in raw_rows}
    if len(raw_by_id) != TM_PAGE30_SOURCE_ROW_COUNT or set(raw_by_id) != {
        row.row_id for rows in rows_by_schema.values() for row in rows
    }:
        raise TMNoteMappingError("TM page-30 mapped-value source identity drifted")

    axis_records = []
    for expected_ordinal, axis in enumerate(axes, start=1):
        role = str(_field(axis, "current_or_comparative"))
        period_start = _field(axis, "period_start")
        period_end = _field(axis, "period_end")
        expected_period_end = "2026-03-31" if expected_ordinal == 1 else "2025-12-31"
        if (
            _field(axis, "ordinal") != expected_ordinal
            or str(_field(axis, "axis_id")) != f"value-{expected_ordinal}"
            or role != ("CURRENT" if expected_ordinal == 1 else "COMPARATIVE")
            or str(_field(axis, "period_type")) != "SNAPSHOT"
            or str(_field(axis, "canonical_unit")) != "VND"
            or _field(axis, "unit_multiplier") != 1_000_000
            or not hasattr(period_start, "isoformat")
            or not hasattr(period_end, "isoformat")
            or period_start.isoformat() != expected_period_end
            or period_end.isoformat() != expected_period_end
        ):
            raise TMNoteMappingError("TM page-30 mapped-value axis binding drifted")
        axis_records.append(
            (
                str(_field(axis, "axis_id")),
                expected_ordinal,
                role,
                period_start.isoformat(),
                period_end.isoformat(),
            )
        )

    mapped_values = []
    numeric_target_count = 0
    for report_norm_id in TM_PAGE30_FIXED_IDS:
        source_rows = rows_by_schema.get(report_norm_id)
        if not source_rows:
            raise TMNoteMappingError(f"TM page-30 mapped target has no source: {report_norm_id}")
        raw_target_rows = tuple(raw_by_id[row.row_id] for row in source_rows)
        row_kinds = {row.row_kind for row in source_rows}
        if row_kinds == {"LABEL_ONLY"}:
            if report_norm_id not in {577, 580} or len(source_rows) != 1:
                raise TMNoteMappingError("TM page-30 structural target identity drifted")
            _validate_structural_blank_row(raw_target_rows[0])
            continue
        if row_kinds != {"NUMERIC"}:
            raise TMNoteMappingError("TM page-30 target mixes structural and numeric sources")
        if report_norm_id == TM_PAGE30_AGGREGATE_TARGET_ID:
            if (
                tuple((row.note_number, row.ordinal) for row in source_rows)
                != TM_PAGE30_AGGREGATE_COMPONENT_IDENTITIES
            ):
                raise TMNoteMappingError("TM page-30 aggregate component identity drifted")
            aggregation = "SUM_SOURCE_ROWS"
        elif len(source_rows) == 1:
            aggregation = "DIRECT_SOURCE_ROW"
        else:
            raise TMNoteMappingError("TM page-30 undeclared multi-row target mapping")
        numeric_target_count += 1
        for axis_index, (
            axis_id,
            axis_ordinal,
            role,
            period_start,
            period_end,
        ) in enumerate(axis_records):
            source_values = []
            source_raw_values = []
            source_observations = []
            source_line_indices = []
            source_bboxes = []
            for raw_row in raw_target_rows:
                value, raw_text, observation = _reported_integer_cell(raw_row, axis_index)
                source_values.append(value)
                source_raw_values.append(raw_text)
                source_observations.append(observation)
                value_line_indices = _field(raw_row, "value_line_indices")
                value_bboxes = _field(raw_row, "value_bboxes")
                if (
                    isinstance(value_line_indices, (str, bytes))
                    or not isinstance(value_line_indices, Sequence)
                    or len(value_line_indices) != 2
                    or isinstance(value_bboxes, (str, bytes))
                    or not isinstance(value_bboxes, Sequence)
                    or len(value_bboxes) != 2
                    or not isinstance(value_bboxes[axis_index], BoundingBox)
                    or not value_line_indices[axis_index]
                ):
                    raise TMNoteMappingError("TM page-30 mapped cell provenance is incomplete")
                source_line_indices.append(tuple(int(i) for i in value_line_indices[axis_index]))
                source_bboxes.append(value_bboxes[axis_index])
            total = sum(source_values, start=Decimal(0))
            canonical = total * 1_000_000
            if canonical != canonical.to_integral_value():
                raise TMNoteMappingError("TM page-30 canonical VND amount is non-integral")
            mapped_values.append(
                TMPage30MappedValue(
                    report_norm_id=report_norm_id,
                    axis_id=axis_id,
                    axis_ordinal=axis_ordinal,
                    current_or_comparative=role,
                    period_start=period_start,
                    period_end=period_end,
                    period_type="SNAPSHOT",
                    canonical_unit="VND",
                    unit_multiplier=1_000_000,
                    observation=(
                        ObservationKind.ZERO.value
                        if len(source_observations) == 1
                        and source_observations[0] == ObservationKind.ZERO.value
                        else ObservationKind.VALUE.value
                    ),
                    reported_value=format(total, "f"),
                    canonical_value_vnd=int(canonical),
                    aggregation=aggregation,
                    source_row_ids=tuple(row.row_id for row in source_rows),
                    source_raw_values=tuple(source_raw_values),
                    source_reported_values=tuple(format(value, "f") for value in source_values),
                    source_value_line_indices=tuple(source_line_indices),
                    source_value_bboxes=tuple(source_bboxes),
                )
            )
    if (
        numeric_target_count != TM_PAGE30_NUMERIC_TARGET_COUNT
        or len(mapped_values) != TM_PAGE30_MAPPED_VALUE_COUNT
        or len({(value.report_norm_id, value.axis_id) for value in mapped_values})
        != TM_PAGE30_MAPPED_VALUE_COUNT
    ):
        raise TMNoteMappingError("TM page-30 mapped-value denominator or uniqueness drifted")

    values_by_key = {
        (value.report_norm_id, value.axis_id): Decimal(value.reported_value)
        for value in mapped_values
    }
    aggregate_values = tuple(
        int(values_by_key[(TM_PAGE30_AGGREGATE_TARGET_ID, axis_id)])
        for axis_id, *_rest in axis_records
    )
    provision_values = tuple(
        int(values_by_key[(TM_PAGE30_PROVISION_TOTAL_ID, axis_id)])
        for axis_id, *_rest in axis_records
    )
    if aggregate_values != TM_PAGE30_EXPECTED_AGGREGATE_VALUES:
        raise TMNoteMappingError("TM page-30 ID 574 aggregate value drifted")
    if provision_values != TM_PAGE30_EXPECTED_PROVISION_VALUES:
        raise TMNoteMappingError("TM page-30 ID 5718 provision total drifted")

    equation_specs = (
        ("CASH_TOTAL", 561, (562, 563, 565)),
        ("VIETNAM_CENTRAL_BANK_TOTAL", 570, (571, 572)),
        ("CENTRAL_BANK_DEPOSITS_TOTAL", 569, (570, 574)),
        ("INTERBANK_DEPOSITS_TOTAL", 576, (578, 579, 581, 582)),
        ("INTERBANK_LOANS_TOTAL", 585, (586, 588)),
        ("INTERBANK_NET_TOTAL", 575, (576, 585, 5718)),
    )
    accounting_checks = []
    aggregate_assignments = {
        value.axis_id: value
        for value in mapped_values
        if value.report_norm_id == TM_PAGE30_AGGREGATE_TARGET_ID
    }
    for axis_id, _ordinal, role, _start, _end in axis_records:
        aggregate = aggregate_assignments[axis_id]
        aggregate_residual = Decimal(aggregate.reported_value) - sum(
            (Decimal(value) for value in aggregate.source_reported_values),
            start=Decimal(0),
        )
        accounting_checks.append(
            TMPage30AccountingCheck(
                check_id="OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATION",
                axis_id=axis_id,
                current_or_comparative=role,
                target_report_norm_id=TM_PAGE30_AGGREGATE_TARGET_ID,
                target_reported_value=aggregate.reported_value,
                operand_report_norm_ids=(),
                operand_source_row_ids=aggregate.source_row_ids,
                operand_reported_values=aggregate.source_reported_values,
                residual_reported_unit=format(aggregate_residual, "f"),
                status="PASS" if aggregate_residual == 0 else "FAIL",
            )
        )
        for check_id, target_id, operand_ids in equation_specs:
            target = values_by_key[(target_id, axis_id)]
            operands = tuple(values_by_key[(operand_id, axis_id)] for operand_id in operand_ids)
            residual = target - sum(operands, start=Decimal(0))
            operand_source_ids = tuple(
                row.row_id for operand_id in operand_ids for row in rows_by_schema[operand_id]
            )
            accounting_checks.append(
                TMPage30AccountingCheck(
                    check_id=check_id,
                    axis_id=axis_id,
                    current_or_comparative=role,
                    target_report_norm_id=target_id,
                    target_reported_value=format(target, "f"),
                    operand_report_norm_ids=operand_ids,
                    operand_source_row_ids=operand_source_ids,
                    operand_reported_values=tuple(format(value, "f") for value in operands),
                    residual_reported_unit=format(residual, "f"),
                    status="PASS" if residual == 0 else "FAIL",
                )
            )
    if len(accounting_checks) != TM_PAGE30_ACCOUNTING_CHECK_COUNT or any(
        check.status != "PASS" for check in accounting_checks
    ):
        raise TMNoteMappingError("TM page-30 post-mapping accounting validation failed")
    return tuple(mapped_values), tuple(accounting_checks)


def reconcile_tm_page30_items(
    parsed_page: object,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage30MappingPolicy,
    source_pdf_path: Path,
    independent_evidence: TMPage30SemanticEvidence | None = None,
    independent_labels_by_row: Mapping[str, str] | None = None,
    independent_reader_id: str | None = None,
    independent_reader_status: TMSemanticReaderStatus | str = TMSemanticReaderStatus.NOT_RUN,
    independent_reader_blocker: str | None = None,
    source_reader_id: str = "ppocrv6-word-box",
) -> TMPage30MappingResult:
    """Reconcile all 1,386 TM items with bounded page-30 mapping and validation."""

    if independent_evidence is not None:
        if (
            independent_labels_by_row is not None
            or independent_reader_id is not None
            or str(independent_reader_status) != TMSemanticReaderStatus.NOT_RUN.value
            or independent_reader_blocker is not None
        ):
            raise TMNoteMappingError(
                "TM semantic evidence cannot be mixed with loose reader inputs"
            )
        independent_labels_by_row = independent_evidence.labels_by_row
        independent_reader_id = independent_evidence.reader_id
        semantic_status = TMSemanticReaderStatus(independent_evidence.reader_status)
    else:
        try:
            semantic_status = TMSemanticReaderStatus(str(independent_reader_status))
        except ValueError as exc:
            raise TMNoteMappingError("TM independent semantic reader status is invalid") from exc
    if semantic_status is TMSemanticReaderStatus.COMPLETE and independent_reader_blocker:
        raise TMNoteMappingError("complete independent reader cannot carry a blocker")
    if semantic_status is not TMSemanticReaderStatus.COMPLETE and not independent_reader_blocker:
        independent_reader_blocker = "independent semantic label stream is unavailable"
    if (
        _field(parsed_page, "page_tag") != policy.page_tag
        or str(_field(parsed_page, "scope")) != policy.report_scope
        or _field(parsed_page, "source_pdf_sha256") != policy.source_pdf_sha256
        or _field(parsed_page, "source_render_sha256") != policy.source_render_sha256
        or _field(parsed_page, "mapping_authority") is not False
    ):
        raise TMNoteMappingError("TM parsed page identity/safety boundary drifted")
    logical_rows = _field(parsed_page, "rows")
    if not isinstance(logical_rows, Sequence):
        raise TMNoteMappingError("TM parsed page contains no logical rows")
    rows = adapt_tm_page30_rows(logical_rows, source_reader_id=source_reader_id)
    identities = tuple((row.note_number, row.ordinal) for row in rows)
    if identities != tuple(rule.identity for rule in policy.rows):
        raise TMNoteMappingError("TM visible three-note hierarchy/order drifted")
    ppocr_scores = {}
    for row, rule in zip(rows, policy.rows, strict=True):
        if row.row_kind != rule.expected_row_kind or row.source_role != rule.expected_source_role:
            raise TMNoteMappingError(f"TM visible row role drifted: {row.row_id}")
        score = _label_similarity(row.visible_label, rule.visible_label_anchor)
        if score < policy.minimum_ppocr_anchor_similarity:
            raise TMNoteMappingError(f"TM PP-OCR label cannot support row rule: {row.row_id}")
        ppocr_scores[row.row_id] = score

    geometry = verify_tm_page30_source_geometry(source_pdf_path, rows, policy, independent_evidence)
    if geometry.pdf_text_available or geometry.pdf_text_token_count != 0:
        raise TMNoteMappingError("TM page-30 PDF text-layer absence unexpectedly changed")
    independent_ready, effective_reader_status, independent_scores, independent_digest = (
        _independent_support(
            rows,
            policy.rows,
            policy,
            independent_labels_by_row=independent_labels_by_row,
            independent_reader_id=independent_reader_id,
            independent_reader_status=semantic_status,
        )
    )
    stream_count = 2 if independent_ready else 1
    automatic_fixed = stream_count >= policy.minimum_independent_semantic_streams
    mapping_authority_granted = automatic_fixed

    tm_schema, schema_digest = _schema_projection(schema)
    schema_by_id = {item.schema_id: item for item in tm_schema}
    policy_ids = {
        report_norm_id for rule in policy.rows for report_norm_id in rule.candidate_report_norm_ids
    } | set(policy.not_observed_schema_ids)
    if any(report_norm_id not in schema_by_id for report_norm_id in policy_ids):
        raise TMNoteMappingError("TM page-30 policy references an unknown schema item")

    source_dispositions = []
    source_by_schema: dict[int, list[TMPage30SourceRow]] = {}
    rule_by_schema: dict[int, list[TMPage30RowRule]] = {}
    score_by_schema: dict[int, list[tuple[float, float | None, float | None]]] = {}
    for row, rule in zip(rows, policy.rows, strict=True):
        independent_score, cross_score = independent_scores.get(row.row_id, (None, None))
        if rule.disposition in {
            TMRuleDisposition.FIXED,
            TMRuleDisposition.AGGREGATE_COMPONENT,
        }:
            status = (
                TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED
                if automatic_fixed
                else TMSourceMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
            )
            if rule.disposition is TMRuleDisposition.AGGREGATE_COMPONENT:
                reason = (
                    "country-specific source row is retained as one component of the declared "
                    "ID 574 aggregate; both component provenances are preserved"
                    if automatic_fixed
                    else "country-specific source row is a declared ID 574 aggregate component; "
                    "selection is withheld until the independent label stream is available"
                )
            else:
                reason = (
                    "fixed page-30 mapping supported by PP-OCR, independent semantic label, and "
                    "visible note hierarchy/order"
                    if automatic_fixed
                    else "one-to-one page-30 candidate supported by PP-OCR and visible note "
                    "hierarchy/order; independent DeepSeek semantic stream is unavailable"
                )
            report_norm_id = rule.candidate_report_norm_ids[0]
            source_by_schema.setdefault(report_norm_id, []).append(row)
            rule_by_schema.setdefault(report_norm_id, []).append(rule)
            score_by_schema.setdefault(report_norm_id, []).append(
                (
                    ppocr_scores[row.row_id],
                    independent_score,
                    cross_score,
                )
            )
        else:
            raise TMNoteMappingError("TM page-30 unresolved row disposition escaped policy load")
        supporting = (source_reader_id,)
        if independent_ready and independent_reader_id is not None:
            supporting += (independent_reader_id,)
        source_dispositions.append(
            TMSourceDisposition(
                row_id=row.row_id,
                order=row.order,
                note_number=row.note_number,
                ordinal=row.ordinal,
                visible_label=row.visible_label,
                row_kind=row.row_kind,
                source_role=row.source_role,
                value_presence=(
                    "OBSERVED_STRUCTURAL_ITEM_WITH_BLANK_CELLS"
                    if row.row_kind == "LABEL_ONLY"
                    else "OBSERVED_NUMERIC_CELLS_READ_ONLY_AFTER_ITEM_SELECTION"
                ),
                status=status.value,
                candidate_report_norm_ids=rule.candidate_report_norm_ids,
                candidate_canonical_names=tuple(
                    schema_by_id[report_norm_id].canonical_name
                    for report_norm_id in rule.candidate_report_norm_ids
                ),
                ppocr_label_similarity=round(ppocr_scores[row.row_id], 6),
                independent_label_similarity=(
                    round(independent_score, 6) if independent_score is not None else None
                ),
                cross_reader_label_similarity=(
                    round(cross_score, 6) if cross_score is not None else None
                ),
                supporting_reader_ids=supporting,
                reason=reason,
            )
        )

    schema_dispositions = []
    for item in tm_schema:
        source_rows = tuple(source_by_schema.get(item.schema_id, ()))
        rules = tuple(rule_by_schema.get(item.schema_id, ()))
        score_records = tuple(score_by_schema.get(item.schema_id, ()))
        if item.schema_id in TM_PAGE30_NOT_OBSERVED_IDS:
            status = TMSchemaMappingStatus.NOT_OBSERVED_IN_THIS_PDF
            source_ids = ()
            supporting = ()
            scores: tuple[float, float | None, float | None] | None = None
            reason = (
                "schema item is a formula component of visible aggregate provision 5718; no "
                "separate source row is observed on PDF page 30"
            )
        elif not rules:
            status = TMSchemaMappingStatus.UNASSESSED
            source_ids: tuple[str, ...] = ()
            supporting = ()
            scores = None
            reason = "schema item is outside the currently assessed PDF page-30 batch"
        else:
            status = (
                TMSchemaMappingStatus.MAPPED_AUTOMATIC_SCOPED
                if automatic_fixed
                else TMSchemaMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
            )
            if not source_rows or len(score_records) != len(source_rows):
                raise TMNoteMappingError("TM page-30 schema/source evidence cardinality drifted")
            source_ids = tuple(row.row_id for row in source_rows)
            supporting = (source_reader_id,)
            if independent_ready and independent_reader_id is not None:
                supporting += (independent_reader_id,)
            scores = (
                min(score[0] for score in score_records),
                (
                    min(score[1] for score in score_records if score[1] is not None)
                    if all(score[1] is not None for score in score_records)
                    else None
                ),
                (
                    min(score[2] for score in score_records if score[2] is not None)
                    if all(score[2] is not None for score in score_records)
                    else None
                ),
            )
            if item.schema_id == TM_PAGE30_AGGREGATE_TARGET_ID:
                reason = (
                    "two visible country rows are deliberately aggregated once into ID 574 with "
                    "both source-row provenances retained"
                )
            else:
                reason = (
                    "selection authority is limited to the fixed rows on MBB PDF page 30"
                    if automatic_fixed
                    else "fixed candidate is withheld because the independent DeepSeek label "
                    "stream did not complete in the pinned runtime"
                )
        schema_dispositions.append(
            TMSchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status.value,
                source_row_ids=source_ids,
                ppocr_label_similarity=(round(scores[0], 6) if scores is not None else None),
                independent_label_similarity=(
                    round(scores[1], 6) if scores is not None and scores[1] is not None else None
                ),
                cross_reader_label_similarity=(
                    round(scores[2], 6) if scores is not None and scores[2] is not None else None
                ),
                supporting_reader_ids=supporting,
                reason=reason,
            )
        )

    frozen_source_by_schema = {
        report_norm_id: tuple(source_rows)
        for report_norm_id, source_rows in source_by_schema.items()
    }
    validated_mapped_values, accounting_checks = _build_mapped_values_and_checks(
        parsed_page,
        frozen_source_by_schema,
    )

    mapping_inputs = _BASE_MAPPING_INPUTS
    if independent_ready:
        mapping_inputs += ("DEEPSEEK_OCR_2_REFERENCE_BLIND_LABELS",)
    mapping_inputs += (
        "SOURCE_NUMERIC_CELLS_FOR_POST_SELECTION_VALUE_BINDING_ONLY",
        "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
    )
    mapped_schema = TM_PAGE30_FIXED_MAPPING_COUNT if automatic_fixed else 0
    candidate_schema = 0 if automatic_fixed else TM_PAGE30_FIXED_MAPPING_COUNT
    mapped_source = TM_PAGE30_SOURCE_MAPPED_COUNT if automatic_fixed else 0
    candidate_source = 0 if automatic_fixed else TM_PAGE30_SOURCE_MAPPED_COUNT
    mapped_values = validated_mapped_values if automatic_fixed else ()
    result = TMPage30MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=policy.page_number,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status=(
            "SCOPED_PAGE30_MAPPING_RESOLVED_WITH_AGGREGATION_AND_ACCOUNTING_VALIDATION"
            if automatic_fixed
            else "CANDIDATE_RECONCILIATION_SECOND_READER_BLOCKED"
        ),
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=mapping_authority_granted,
        automatic_fixed_selection_allowed=automatic_fixed,
        complete_page_mapping_resolved=automatic_fixed,
        independent_semantic_stream_count=stream_count,
        minimum_independent_semantic_streams=policy.minimum_independent_semantic_streams,
        source_reader_id=source_reader_id,
        independent_reader_id=independent_reader_id,
        independent_reader_status=effective_reader_status,
        independent_reader_blocker=(None if independent_ready else independent_reader_blocker),
        schema_item_count=TM_SCHEMA_ITEM_COUNT,
        assessed_schema_count=(TM_PAGE30_FIXED_MAPPING_COUNT + TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT),
        mapped_schema_count=mapped_schema,
        candidate_linked_schema_count=candidate_schema,
        not_observed_schema_count=TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT,
        ambiguous_schema_count=TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT,
        unassessed_schema_count=(
            TM_SCHEMA_ITEM_COUNT
            - TM_PAGE30_FIXED_MAPPING_COUNT
            - TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT
        ),
        fully_verified_schema_count=0,
        source_row_count=TM_PAGE30_SOURCE_ROW_COUNT,
        mapped_source_row_count=mapped_source,
        candidate_linked_source_row_count=candidate_source,
        ambiguous_source_row_count=0,
        source_only_row_count=TM_PAGE30_SOURCE_ONLY_COUNT,
        structural_blank_source_row_count=TM_PAGE30_STRUCTURAL_BLANK_COUNT,
        mapped_value_count=len(mapped_values),
        accounting_check_count=len(accounting_checks),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting_checks),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        mapped_values=mapped_values,
        accounting_checks=accounting_checks,
        geometry_evidence=geometry,
        schema_projection_sha256=schema_digest,
        policy_sha256=policy.policy_sha256,
        source_label_sha256=_label_digest(rows),
        independent_label_sha256=independent_digest,
        independent_evidence_sha256=(
            independent_evidence.evidence_sha256 if independent_evidence is not None else None
        ),
        mapping_inputs=mapping_inputs,
        reason=(
            "21 schema targets covering all 22 visible rows remain candidate-only because the "
            "independent semantic reader is unavailable; post-selection values and equations "
            "pass, but automatic mapping authority remains withheld"
            if not automatic_fixed
            else "all 22 page-30 source rows map to 21 schema targets; Laos and Cambodia are "
            "aggregated once into 574, total provision maps 5718, and component IDs 583/590 "
            "are separately classified as not observed"
        ),
    )
    return validate_tm_page30_mapping_result(result)


def validate_tm_page30_mapping_result(
    result: TMPage30MappingResult,
) -> TMPage30MappingResult:
    """Validate full schema/source denominators, statuses, and cross-links."""

    if (
        result.statement_type != "TM"
        or result.page_number != 30
        or result.page_tag != "page-0030"
        or result.report_scope != "CONSOLIDATED"
        or not result.mapping_authority_scope.endswith(
            "PDF_PAGE_30_FIXED_AND_DECLARED_AGGREGATE_ROWS_ONLY"
        )
        or result.complete_page_mapping_resolved != result.automatic_fixed_selection_allowed
        or result.schema_item_count != TM_SCHEMA_ITEM_COUNT
        or result.assessed_schema_count
        != TM_PAGE30_FIXED_MAPPING_COUNT + TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT
        or result.mapped_schema_count + result.candidate_linked_schema_count
        != TM_PAGE30_FIXED_MAPPING_COUNT
        or result.not_observed_schema_count != TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        or result.unassessed_schema_count
        != TM_SCHEMA_ITEM_COUNT
        - TM_PAGE30_FIXED_MAPPING_COUNT
        - TM_PAGE30_NOT_OBSERVED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE30_SOURCE_ROW_COUNT
        or result.mapped_source_row_count + result.candidate_linked_source_row_count
        != TM_PAGE30_SOURCE_MAPPED_COUNT
        or result.ambiguous_source_row_count != 0
        or result.source_only_row_count != TM_PAGE30_SOURCE_ONLY_COUNT
        or result.structural_blank_source_row_count != TM_PAGE30_STRUCTURAL_BLANK_COUNT
        or result.accounting_check_count != TM_PAGE30_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE30_ACCOUNTING_CHECK_COUNT
        or len(result.accounting_checks) != TM_PAGE30_ACCOUNTING_CHECK_COUNT
        or result.mapped_value_count != len(result.mapped_values)
        or result.mapped_schema_count
        + result.candidate_linked_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
        or any(
            _SHA256.fullmatch(value) is None
            for value in (
                result.schema_projection_sha256,
                result.policy_sha256,
                result.source_label_sha256,
                result.geometry_evidence.geometry_sha256,
            )
        )
    ):
        raise TMNoteMappingError("TM page-30 mapping result identity/counts are invalid")
    if result.mapping_authority_granted != result.automatic_fixed_selection_allowed:
        raise TMNoteMappingError("TM mapping authority and automatic fixed selection disagree")
    if result.automatic_fixed_selection_allowed:
        if (
            result.status
            != "SCOPED_PAGE30_MAPPING_RESOLVED_WITH_AGGREGATION_AND_ACCOUNTING_VALIDATION"
            or result.independent_semantic_stream_count
            < result.minimum_independent_semantic_streams
            or result.mapped_schema_count != TM_PAGE30_FIXED_MAPPING_COUNT
            or result.candidate_linked_schema_count != 0
            or result.mapped_source_row_count != TM_PAGE30_SOURCE_MAPPED_COUNT
            or result.candidate_linked_source_row_count != 0
            or result.mapped_value_count != TM_PAGE30_MAPPED_VALUE_COUNT
            or result.independent_label_sha256 is None
            or result.independent_evidence_sha256 is None
            or result.geometry_evidence.semantic_crop_attempt_count != 26
            or result.geometry_evidence.verified_semantic_crop_attempt_count != 26
            or result.geometry_evidence.semantic_crop_geometry_sha256 is None
            or "DEEPSEEK_OCR_2_REFERENCE_BLIND_LABELS" not in result.mapping_inputs
        ):
            raise TMNoteMappingError("TM automatic fixed mapping lacks dual-stream authority")
    elif (
        result.status != "CANDIDATE_RECONCILIATION_SECOND_READER_BLOCKED"
        or result.independent_semantic_stream_count >= result.minimum_independent_semantic_streams
        or result.mapped_schema_count != 0
        or result.candidate_linked_schema_count != TM_PAGE30_FIXED_MAPPING_COUNT
        or result.mapped_source_row_count != 0
        or result.candidate_linked_source_row_count != TM_PAGE30_SOURCE_MAPPED_COUNT
        or result.mapped_value_count != 0
    ):
        raise TMNoteMappingError("TM candidate-only fallback granted excess authority")
    if {
        "SOURCE_NUMERIC_CELLS_FOR_POST_SELECTION_VALUE_BINDING_ONLY",
        "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
    } - set(result.mapping_inputs) or _FORBIDDEN_INPUTS & set(result.mapping_inputs):
        raise TMNoteMappingError("TM page-30 mapping/validation input boundary drifted")
    schema = result.schema_dispositions
    source = result.source_dispositions
    expected_source_row_ids = tuple(
        f"page-0030:note-{note_number}:row-{ordinal:04d}"
        for note_number, count in ((1, 4), (2, 6), (3, 12))
        for ordinal in range(1, count + 1)
    )
    if (
        len(schema) != TM_SCHEMA_ITEM_COUNT
        or len({item.report_norm_id for item in schema}) != len(schema)
        or [item.display_order for item in schema] != list(range(TM_SCHEMA_ITEM_COUNT))
        or len(source) != TM_PAGE30_SOURCE_ROW_COUNT
        or len({item.row_id for item in source}) != len(source)
        or [item.order for item in source] != list(range(TM_PAGE30_SOURCE_ROW_COUNT))
        or tuple(item.row_id for item in source) != expected_source_row_ids
        or tuple(item.candidate_report_norm_ids[0] for item in source)
        != TM_PAGE30_EXPECTED_SOURCE_TARGET_IDS
        or any(len(item.candidate_report_norm_ids) != 1 for item in source)
    ):
        raise TMNoteMappingError("TM page-30 disposition coverage/order is incomplete")
    expected_schema_counts = {
        TMSchemaMappingStatus.MAPPED_AUTOMATIC_SCOPED.value: result.mapped_schema_count,
        TMSchemaMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value: (
            result.candidate_linked_schema_count
        ),
        TMSchemaMappingStatus.NOT_OBSERVED_IN_THIS_PDF.value: (result.not_observed_schema_count),
        TMSchemaMappingStatus.AMBIGUOUS_MAPPING.value: result.ambiguous_schema_count,
        TMSchemaMappingStatus.UNASSESSED.value: result.unassessed_schema_count,
    }
    if any(
        sum(item.status == status for item in schema) != count
        for status, count in expected_schema_counts.items()
    ):
        raise TMNoteMappingError("TM schema disposition counts drifted")
    expected_source_counts = {
        TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED.value: result.mapped_source_row_count,
        TMSourceMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value: (
            result.candidate_linked_source_row_count
        ),
        TMSourceMappingStatus.AMBIGUOUS_MAPPING.value: result.ambiguous_source_row_count,
        TMSourceMappingStatus.SOURCE_ONLY_PDF_ROW.value: result.source_only_row_count,
    }
    if any(
        sum(item.status == status for item in source) != count
        for status, count in expected_source_counts.items()
    ):
        raise TMNoteMappingError("TM source disposition counts drifted")
    source_by_id = {item.row_id: item for item in source}
    schema_by_id = {item.report_norm_id: item for item in schema}
    expected_sources_by_schema: dict[int, list[str]] = {}
    for row_id, report_norm_id in zip(
        expected_source_row_ids,
        TM_PAGE30_EXPECTED_SOURCE_TARGET_IDS,
        strict=True,
    ):
        expected_sources_by_schema.setdefault(report_norm_id, []).append(row_id)
    mapped_status = (
        TMSchemaMappingStatus.MAPPED_AUTOMATIC_SCOPED.value
        if result.automatic_fixed_selection_allowed
        else TMSchemaMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value
    )
    if (
        {item.report_norm_id for item in schema if item.status == mapped_status}
        != set(TM_PAGE30_FIXED_IDS)
        or {
            item.report_norm_id
            for item in schema
            if item.status == TMSchemaMappingStatus.NOT_OBSERVED_IN_THIS_PDF.value
        }
        != set(TM_PAGE30_NOT_OBSERVED_IDS)
        or any(
            tuple(expected_sources_by_schema.get(item.report_norm_id, ())) != item.source_row_ids
            for item in schema
            if item.status == mapped_status
        )
        or any(
            item.source_row_ids
            for item in schema
            if item.status
            in {
                TMSchemaMappingStatus.NOT_OBSERVED_IN_THIS_PDF.value,
                TMSchemaMappingStatus.UNASSESSED.value,
            }
        )
    ):
        raise TMNoteMappingError("TM page-30 exact schema classification/source links drifted")
    for item in schema:
        for row_id in item.source_row_ids:
            if (
                row_id not in source_by_id
                or item.report_norm_id not in source_by_id[row_id].candidate_report_norm_ids
            ):
                raise TMNoteMappingError("TM schema/source mapping cross-link is inconsistent")
    for item in source:
        if any(
            report_norm_id not in schema_by_id for report_norm_id in item.candidate_report_norm_ids
        ):
            raise TMNoteMappingError("TM source row references an unknown schema item")

    numeric_target_ids = set(TM_PAGE30_FIXED_IDS) - {577, 580}
    expected_value_keys = {
        (report_norm_id, axis_id)
        for report_norm_id in numeric_target_ids
        for axis_id in ("value-1", "value-2")
    }
    values_by_key = {(item.report_norm_id, item.axis_id): item for item in result.mapped_values}
    if result.automatic_fixed_selection_allowed:
        if (
            len(values_by_key) != len(result.mapped_values)
            or set(values_by_key) != expected_value_keys
        ):
            raise TMNoteMappingError("TM page-30 mapped target/axis uniqueness drifted")
        axis_contract = {
            "value-1": (1, "CURRENT", "2026-03-31"),
            "value-2": (2, "COMPARATIVE", "2025-12-31"),
        }
        for item in result.mapped_values:
            axis_ordinal, role, period = axis_contract[item.axis_id]
            expected_sources = tuple(expected_sources_by_schema[item.report_norm_id])
            expected_source_count = 2 if item.report_norm_id == TM_PAGE30_AGGREGATE_TARGET_ID else 1
            reported = Decimal(item.reported_value)
            if (
                item.axis_ordinal != axis_ordinal
                or item.current_or_comparative != role
                or item.period_start != period
                or item.period_end != period
                or item.period_type != "SNAPSHOT"
                or item.canonical_unit != "VND"
                or item.unit_multiplier != 1_000_000
                or item.observation != ObservationKind.VALUE.value
                or reported != reported.to_integral_value()
                or item.canonical_value_vnd != int(reported * 1_000_000)
                or item.source_row_ids != expected_sources
                or len(item.source_row_ids) != expected_source_count
                or len(item.source_raw_values) != expected_source_count
                or len(item.source_reported_values) != expected_source_count
                or len(item.source_value_line_indices) != expected_source_count
                or len(item.source_value_bboxes) != expected_source_count
                or any(not value for value in item.source_raw_values)
                or any(not indices for indices in item.source_value_line_indices)
                or any(
                    bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0 for bbox in item.source_value_bboxes
                )
                or item.aggregation
                != (
                    "SUM_SOURCE_ROWS"
                    if item.report_norm_id == TM_PAGE30_AGGREGATE_TARGET_ID
                    else "DIRECT_SOURCE_ROW"
                )
            ):
                raise TMNoteMappingError("TM page-30 mapped value/provenance contract drifted")
        if (
            tuple(
                int(values_by_key[(TM_PAGE30_AGGREGATE_TARGET_ID, axis_id)].reported_value)
                for axis_id in ("value-1", "value-2")
            )
            != TM_PAGE30_EXPECTED_AGGREGATE_VALUES
            or tuple(
                int(values_by_key[(TM_PAGE30_PROVISION_TOTAL_ID, axis_id)].reported_value)
                for axis_id in ("value-1", "value-2")
            )
            != TM_PAGE30_EXPECTED_PROVISION_VALUES
        ):
            raise TMNoteMappingError("TM page-30 mapped aggregate/provision values drifted")
    elif result.mapped_values:
        raise TMNoteMappingError("TM candidate-only result leaked mapped values")

    equation_contract = {
        "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATION": (574, ()),
        "CASH_TOTAL": (561, (562, 563, 565)),
        "VIETNAM_CENTRAL_BANK_TOTAL": (570, (571, 572)),
        "CENTRAL_BANK_DEPOSITS_TOTAL": (569, (570, 574)),
        "INTERBANK_DEPOSITS_TOTAL": (576, (578, 579, 581, 582)),
        "INTERBANK_LOANS_TOTAL": (585, (586, 588)),
        "INTERBANK_NET_TOTAL": (575, (576, 585, 5718)),
    }
    expected_check_keys = {
        (check_id, axis_id) for check_id in equation_contract for axis_id in ("value-1", "value-2")
    }
    if {
        (check.check_id, check.axis_id) for check in result.accounting_checks
    } != expected_check_keys or any(
        check.status != "PASS" or Decimal(check.residual_reported_unit) != 0
        for check in result.accounting_checks
    ):
        raise TMNoteMappingError("TM page-30 accounting check identity/status drifted")
    for check in result.accounting_checks:
        expected_target, expected_operands = equation_contract[check.check_id]
        expected_role = "CURRENT" if check.axis_id == "value-1" else "COMPARATIVE"
        calculated_residual = Decimal(check.target_reported_value) - sum(
            (Decimal(value) for value in check.operand_reported_values),
            start=Decimal(0),
        )
        if (
            check.target_report_norm_id != expected_target
            or check.operand_report_norm_ids != expected_operands
            or check.current_or_comparative != expected_role
            or calculated_residual != 0
            or (
                check.check_id == "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATION"
                and check.operand_source_row_ids
                != tuple(expected_sources_by_schema[TM_PAGE30_AGGREGATE_TARGET_ID])
            )
            or (
                check.check_id != "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATION"
                and check.operand_source_row_ids
                != tuple(
                    row_id
                    for report_norm_id in expected_operands
                    for row_id in expected_sources_by_schema[report_norm_id]
                )
            )
            or (
                result.automatic_fixed_selection_allowed
                and Decimal(
                    values_by_key[(check.target_report_norm_id, check.axis_id)].reported_value
                )
                != Decimal(check.target_reported_value)
            )
        ):
            raise TMNoteMappingError("TM page-30 accounting equation/provenance drifted")
    if (
        result.geometry_evidence.pdf_text_available
        or result.geometry_evidence.pdf_text_token_count != 0
        or result.geometry_evidence.verified_label_row_count != TM_PAGE30_SOURCE_ROW_COUNT
    ):
        raise TMNoteMappingError("TM PDF source geometry/text-layer facts drifted")
    return result


__all__ = [
    "TMNoteMappingError",
    "TMPage30AccountingCheck",
    "TMPage30GeometryEvidence",
    "TMPage30MappedValue",
    "TMPage30MappingPolicy",
    "TMPage30MappingResult",
    "TMPage30RowRule",
    "TMPage30SemanticEvidence",
    "TMPage30SourceRow",
    "TMRuleDisposition",
    "TMSchemaDisposition",
    "TMSchemaMappingStatus",
    "TMSemanticReaderStatus",
    "TMSemanticCropAttempt",
    "TMSemanticLabelSample",
    "TMSourceDisposition",
    "TMSourceMappingStatus",
    "TM_PAGE30_ACCOUNTING_CHECK_COUNT",
    "TM_PAGE30_AGGREGATE_TARGET_ID",
    "TM_PAGE30_AMBIGUOUS_IDS",
    "TM_PAGE30_FIXED_IDS",
    "TM_PAGE30_MAPPED_VALUE_COUNT",
    "TM_PAGE30_NOT_OBSERVED_IDS",
    "TM_PAGE30_PROVISION_TOTAL_ID",
    "TM_PAGE30_TARGETED_REREAD_ROW_IDS",
    "TM_PAGE30_POLICY_RELATIVE_PATH",
    "TM_SCHEMA_ITEM_COUNT",
    "adapt_tm_page30_rows",
    "load_tm_page30_deepseek_evidence",
    "load_tm_page30_mapping_policy",
    "reconcile_tm_page30_items",
    "validate_tm_page30_mapping_result",
    "verify_tm_page30_source_geometry",
]
