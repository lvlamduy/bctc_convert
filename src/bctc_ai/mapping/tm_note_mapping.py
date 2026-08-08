"""Scoped, value-blind item reconciliation for MBB TM PDF page 30."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import yaml
from PIL import Image
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.registry import SchemaItem

TM_PAGE30_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page30-v1.yaml")
TM_SCHEMA_ITEM_COUNT = 1385
TM_PAGE30_SOURCE_ROW_COUNT = 22
TM_PAGE30_FIXED_MAPPING_COUNT = 19
TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT = 2
TM_PAGE30_SOURCE_ONLY_COUNT = 2
TM_PAGE30_STRUCTURAL_BLANK_COUNT = 2
TM_PAGE30_FIXED_IDS = (
    561,
    562,
    563,
    565,
    569,
    570,
    571,
    572,
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
)
TM_PAGE30_AMBIGUOUS_IDS = (583, 590)
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
    AMBIGUOUS = "AMBIGUOUS"
    SOURCE_ONLY = "SOURCE_ONLY"


class TMSchemaMappingStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
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
    ambiguous_source_row_total: int
    ambiguous_schema_item_total: int
    source_only_row_total: int
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
    ambiguous_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    candidate_linked_source_row_count: int
    ambiguous_source_row_count: int
    source_only_row_count: int
    structural_blank_source_row_count: int
    schema_dispositions: tuple[TMSchemaDisposition, ...]
    source_dispositions: tuple[TMSourceDisposition, ...]
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
            (disposition is TMRuleDisposition.FIXED and len(candidate_ids) != 1)
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
        ambiguous_source_row_total=_required_int(payload, "ambiguous_source_row_total"),
        ambiguous_schema_item_total=_required_int(payload, "ambiguous_schema_item_total"),
        source_only_row_total=_required_int(payload, "source_only_row_total"),
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
        if rule.disposition is TMRuleDisposition.FIXED
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
        or not policy.mapping_authority_scope.endswith("PDF_PAGE_30_FIXED_ROWS_ONLY")
        or policy.render_dpi != 300
        or policy.schema_total != TM_SCHEMA_ITEM_COUNT
        or policy.visible_source_row_total != TM_PAGE30_SOURCE_ROW_COUNT
        or policy.fixed_mapping_total != TM_PAGE30_FIXED_MAPPING_COUNT
        or policy.ambiguous_source_row_total != 1
        or policy.ambiguous_schema_item_total != TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        or policy.source_only_row_total != TM_PAGE30_SOURCE_ONLY_COUNT
        or policy.structural_blank_row_total != TM_PAGE30_STRUCTURAL_BLANK_COUNT
        or policy.minimum_independent_semantic_streams < 2
        or len(policy.rows) != TM_PAGE30_SOURCE_ROW_COUNT
        or len(set(identities)) != len(identities)
        or set(fixed_ids) != set(TM_PAGE30_FIXED_IDS)
        or len(fixed_ids) != len(set(fixed_ids))
        or ambiguous_ids != TM_PAGE30_AMBIGUOUS_IDS
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
        raise TMNoteMappingError("TM schema denominator/order is not exactly 1,385")
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
    """Reconcile all 1,385 TM items while limiting authority to page-30 fixed rows."""

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
    }
    if any(report_norm_id not in schema_by_id for report_norm_id in policy_ids):
        raise TMNoteMappingError("TM page-30 policy references an unknown schema item")

    source_dispositions = []
    source_by_schema: dict[int, TMPage30SourceRow] = {}
    rule_by_schema: dict[int, TMPage30RowRule] = {}
    score_by_schema: dict[int, tuple[float, float | None, float | None]] = {}
    for row, rule in zip(rows, policy.rows, strict=True):
        independent_score, cross_score = independent_scores.get(row.row_id, (None, None))
        if rule.disposition is TMRuleDisposition.FIXED:
            status = (
                TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED
                if automatic_fixed
                else TMSourceMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
            )
            reason = (
                "fixed page-30 mapping supported by PP-OCR, independent semantic label, and "
                "visible note hierarchy/order"
                if automatic_fixed
                else "one-to-one page-30 candidate supported by PP-OCR and visible note "
                "hierarchy/order; independent DeepSeek semantic stream is unavailable"
            )
            report_norm_id = rule.candidate_report_norm_ids[0]
            source_by_schema[report_norm_id] = row
            rule_by_schema[report_norm_id] = rule
            score_by_schema[report_norm_id] = (
                ppocr_scores[row.row_id],
                independent_score,
                cross_score,
            )
        elif rule.disposition is TMRuleDisposition.AMBIGUOUS:
            status = TMSourceMappingStatus.AMBIGUOUS_MAPPING
            reason = (
                "visible generic provision label remains compatible with deposit provision 583 "
                "and interbank-loan provision 590; single-ID selection is withheld"
            )
            for report_norm_id in rule.candidate_report_norm_ids:
                source_by_schema[report_norm_id] = row
                rule_by_schema[report_norm_id] = rule
                score_by_schema[report_norm_id] = (
                    ppocr_scores[row.row_id],
                    independent_score,
                    cross_score,
                )
        else:
            status = TMSourceMappingStatus.SOURCE_ONLY_PDF_ROW
            reason = (
                "visible country-specific central-bank row has no row-level ReportNormId in the "
                "supplied schema; aggregation policy is unresolved"
            )
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
                    else "OBSERVED_NUMERIC_CELLS_NOT_READ_BY_MAPPING"
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
        row = source_by_schema.get(item.schema_id)
        rule = rule_by_schema.get(item.schema_id)
        scores = score_by_schema.get(item.schema_id)
        if rule is None:
            status = TMSchemaMappingStatus.UNASSESSED
            source_ids: tuple[str, ...] = ()
            supporting = ()
            reason = "schema item is outside the currently assessed PDF page-30 batch"
        elif rule.disposition is TMRuleDisposition.AMBIGUOUS:
            status = TMSchemaMappingStatus.AMBIGUOUS_MAPPING
            assert row is not None
            source_ids = (row.row_id,)
            supporting = (source_reader_id,)
            if independent_ready and independent_reader_id is not None:
                supporting += (independent_reader_id,)
            reason = "one visible provision row has two hierarchy-compatible schema candidates"
        else:
            status = (
                TMSchemaMappingStatus.MAPPED_AUTOMATIC_SCOPED
                if automatic_fixed
                else TMSchemaMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
            )
            assert row is not None
            source_ids = (row.row_id,)
            supporting = (source_reader_id,)
            if independent_ready and independent_reader_id is not None:
                supporting += (independent_reader_id,)
            reason = (
                "selection authority is limited to the fixed rows on MBB PDF page 30"
                if automatic_fixed
                else "fixed candidate is withheld because the independent DeepSeek label stream "
                "did not complete in the pinned runtime"
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

    mapping_inputs = _BASE_MAPPING_INPUTS
    if independent_ready:
        mapping_inputs += ("DEEPSEEK_OCR_2_REFERENCE_BLIND_LABELS",)
    mapped_schema = TM_PAGE30_FIXED_MAPPING_COUNT if automatic_fixed else 0
    candidate_schema = 0 if automatic_fixed else TM_PAGE30_FIXED_MAPPING_COUNT
    mapped_source = mapped_schema
    candidate_source = candidate_schema
    result = TMPage30MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=policy.page_number,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status=(
            "SCOPED_FIXED_MAPPING_WITH_OPEN_AMBIGUITY"
            if automatic_fixed
            else "CANDIDATE_RECONCILIATION_SECOND_READER_BLOCKED"
        ),
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=mapping_authority_granted,
        automatic_fixed_selection_allowed=automatic_fixed,
        complete_page_mapping_resolved=False,
        independent_semantic_stream_count=stream_count,
        minimum_independent_semantic_streams=policy.minimum_independent_semantic_streams,
        source_reader_id=source_reader_id,
        independent_reader_id=independent_reader_id,
        independent_reader_status=effective_reader_status,
        independent_reader_blocker=(None if independent_ready else independent_reader_blocker),
        schema_item_count=TM_SCHEMA_ITEM_COUNT,
        assessed_schema_count=TM_PAGE30_FIXED_MAPPING_COUNT + TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT,
        mapped_schema_count=mapped_schema,
        candidate_linked_schema_count=candidate_schema,
        ambiguous_schema_count=TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT,
        unassessed_schema_count=(
            TM_SCHEMA_ITEM_COUNT - TM_PAGE30_FIXED_MAPPING_COUNT - TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        ),
        fully_verified_schema_count=0,
        source_row_count=TM_PAGE30_SOURCE_ROW_COUNT,
        mapped_source_row_count=mapped_source,
        candidate_linked_source_row_count=candidate_source,
        ambiguous_source_row_count=1,
        source_only_row_count=TM_PAGE30_SOURCE_ONLY_COUNT,
        structural_blank_source_row_count=TM_PAGE30_STRUCTURAL_BLANK_COUNT,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
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
            "19 fixed mappings remain candidate-only because the selected DeepSeek reader is "
            "blocked by pinned-runtime package drift; 583/590 remains ambiguous and two country "
            "rows remain source-only"
            if not automatic_fixed
            else "19 fixed page-30 mappings have two semantic streams; one provision row remains "
            "ambiguous and two country rows remain source-only"
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
        or result.complete_page_mapping_resolved
        or result.schema_item_count != TM_SCHEMA_ITEM_COUNT
        or result.assessed_schema_count
        != TM_PAGE30_FIXED_MAPPING_COUNT + TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        or result.mapped_schema_count + result.candidate_linked_schema_count
        != TM_PAGE30_FIXED_MAPPING_COUNT
        or result.ambiguous_schema_count != TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        or result.unassessed_schema_count
        != TM_SCHEMA_ITEM_COUNT - TM_PAGE30_FIXED_MAPPING_COUNT - TM_PAGE30_AMBIGUOUS_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE30_SOURCE_ROW_COUNT
        or result.mapped_source_row_count + result.candidate_linked_source_row_count
        != TM_PAGE30_FIXED_MAPPING_COUNT
        or result.ambiguous_source_row_count != 1
        or result.source_only_row_count != TM_PAGE30_SOURCE_ONLY_COUNT
        or result.structural_blank_source_row_count != TM_PAGE30_STRUCTURAL_BLANK_COUNT
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
            result.independent_semantic_stream_count < result.minimum_independent_semantic_streams
            or result.mapped_schema_count != TM_PAGE30_FIXED_MAPPING_COUNT
            or result.candidate_linked_schema_count != 0
            or result.independent_label_sha256 is None
            or result.independent_evidence_sha256 is None
            or result.geometry_evidence.semantic_crop_attempt_count != 26
            or result.geometry_evidence.verified_semantic_crop_attempt_count != 26
            or result.geometry_evidence.semantic_crop_geometry_sha256 is None
            or "DEEPSEEK_OCR_2_REFERENCE_BLIND_LABELS" not in result.mapping_inputs
        ):
            raise TMNoteMappingError("TM automatic fixed mapping lacks dual-stream authority")
    elif (
        result.independent_semantic_stream_count >= result.minimum_independent_semantic_streams
        or result.mapped_schema_count != 0
        or result.candidate_linked_schema_count != TM_PAGE30_FIXED_MAPPING_COUNT
        or result.independent_evidence_sha256 is not None
        or result.geometry_evidence.semantic_crop_attempt_count != 0
        or result.geometry_evidence.verified_semantic_crop_attempt_count != 0
        or result.geometry_evidence.semantic_crop_geometry_sha256 is not None
    ):
        raise TMNoteMappingError("TM candidate-only fallback granted excess authority")
    schema = result.schema_dispositions
    source = result.source_dispositions
    if (
        len(schema) != TM_SCHEMA_ITEM_COUNT
        or len({item.report_norm_id for item in schema}) != len(schema)
        or [item.display_order for item in schema] != list(range(TM_SCHEMA_ITEM_COUNT))
        or len(source) != TM_PAGE30_SOURCE_ROW_COUNT
        or len({item.row_id for item in source}) != len(source)
        or [item.order for item in source] != list(range(TM_PAGE30_SOURCE_ROW_COUNT))
    ):
        raise TMNoteMappingError("TM page-30 disposition coverage/order is incomplete")
    expected_schema_counts = {
        TMSchemaMappingStatus.MAPPED_AUTOMATIC_SCOPED.value: result.mapped_schema_count,
        TMSchemaMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value: (
            result.candidate_linked_schema_count
        ),
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
    if (
        result.geometry_evidence.pdf_text_available
        or result.geometry_evidence.pdf_text_token_count != 0
        or result.geometry_evidence.verified_label_row_count != TM_PAGE30_SOURCE_ROW_COUNT
    ):
        raise TMNoteMappingError("TM PDF source geometry/text-layer facts drifted")
    return result


__all__ = [
    "TMNoteMappingError",
    "TMPage30GeometryEvidence",
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
    "TM_PAGE30_AMBIGUOUS_IDS",
    "TM_PAGE30_FIXED_IDS",
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
