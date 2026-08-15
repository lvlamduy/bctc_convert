"""Hierarchy-safe mapping for MBB consolidated TM page 45 EPS/share disclosures."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_page45 import (
    ParsedTMPage45,
    TMPage45BlankEvidence,
    TMPage45LogicalRow,
    TMPage45StructuralRow,
)

TM_PAGE45_MAPPING_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page45-v1.yaml")
TM_PAGE45_SCHEMA_TOTAL = 1_714
TM_PAGE45_SCOPE_SCHEMA_COUNT = 13
TM_PAGE45_MAPPED_SCHEMA_COUNT = 13
TM_PAGE45_STRUCTURAL_MAPPED_SCHEMA_COUNT = 2
TM_PAGE45_VALUE_BEARING_MAPPED_SCHEMA_COUNT = 11
TM_PAGE45_UNASSESSED_SCHEMA_COUNT = 1_701
TM_PAGE45_SOURCE_ROW_COUNT = 14
TM_PAGE45_MAPPED_SOURCE_ROW_COUNT = 13
TM_PAGE45_SOURCE_ONLY_VALIDATION_ROW_COUNT = 1
TM_PAGE45_FINANCIAL_SLOT_COUNT = 24
TM_PAGE45_VALUE_COUNT = 14
TM_PAGE45_DASH_COUNT = 8
TM_PAGE45_BLANK_COUNT = 2
TM_PAGE45_ASSIGNMENT_COUNT = 22
TM_PAGE45_MAPPED_VALUE_COUNT = 12
TM_PAGE45_EXTERNAL_VALIDATION_OBSERVATION_COUNT = 2
TM_PAGE45_ACCOUNTING_CHECK_COUNT = 2

TM_PAGE45_SCOPE_IDS = frozenset(range(5946, 5959))
TM_PAGE45_MAPPED_SCHEMA_IDS = TM_PAGE45_SCOPE_IDS
TM_PAGE45_NOT_OBSERVED_SCHEMA_IDS: frozenset[int] = frozenset()

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STRUCTURAL_TARGETS = {"EARNINGS_PER_SHARE": 5946, "SHARE_COUNTS": 5949}
_ROW_TARGETS = {
    "WEIGHTED_AVERAGE_ORDINARY_SHARES": 5947,
    "BASIC_EARNINGS_PER_SHARE": 5948,
    "REGISTERED_FOR_ISSUANCE": 5950,
    "SOLD_TO_PUBLIC": 5951,
    "SOLD_TO_PUBLIC_ORDINARY": 5952,
    "REPURCHASED": 5953,
    "REPURCHASED_ORDINARY": 5954,
    "REPURCHASED_PREFERRED": 5955,
    "OUTSTANDING": 5956,
    "OUTSTANDING_ORDINARY": 5957,
    "OUTSTANDING_PREFERRED": 5958,
}
_EXTERNAL_ROLE = "PROFIT_ATTRIBUTABLE_TO_BANK_SHAREHOLDERS"
_EXTERNAL_ID = 1131
_EXTERNAL_OWNER = "page-0044"
_CANONICAL_NAMES = {
    5946: "Lãi trên mỗi cổ phiếu",
    5947: "Bình quân gia quyền của số cổ phiếu phổ thông đang lưu hành",
    5948: "Lãi cơ bản trên mỗi cổ phiếu",
    5949: "Cổ phiếu",
    5950: "Số lượng cổ phiếu đăng ký phát hành",
    5951: "Số lượng cổ phiếu đã bán ra công chúng",
    5952: "- Cổ phiếu phổ thông",
    5953: "Số lượng cổ phiếu được mua lại",
    5954: "- Cổ phiếu phổ thông",
    5955: "- Cổ phiếu ưu đãi",
    5956: "Số lượng cổ phiếu đang lưu hành",
    5957: "- Cổ phiếu phổ thông",
    5958: "- Cổ phiếu ưu đãi",
}
_DURATION_PERIOD_CONTRACT = (
    ("CURRENT", "DURATION", "2026-01-01", "2026-03-31"),
    ("COMPARATIVE", "DURATION", "2025-01-01", "2025-03-31"),
)
_SNAPSHOT_PERIOD_CONTRACT = (
    ("CURRENT", "SNAPSHOT", "2026-03-31", "2026-03-31"),
    ("COMPARATIVE", "SNAPSHOT", "2025-12-31", "2025-12-31"),
)
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_as_item_selector",
    "numeric_value_magnitude_as_item_selector",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "blank_as_zero",
    "zero_as_blank_or_dash",
    "header_trieu_dong_as_share_or_eps_unit",
    "schema_id_outside_page45_scope",
    "external_owner_1131_as_page45_owned_item",
    "profit_row_as_duplicate_mapped_assignment",
    "period_axis_swapping",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
}


class TMPage45MappingError(ValueError):
    pass


class TMPage45SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    UNASSESSED = "UNASSESSED"


class TMPage45SourceStatus(StrEnum):
    MAPPED_STRUCTURAL_SCOPED = "MAPPED_STRUCTURAL_SCOPED"
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_EXTERNAL_VALIDATION = "SOURCE_ONLY_EXTERNAL_VALIDATION"


@dataclass(frozen=True)
class TMPage45MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    mapping_authority_scope: str
    source_table_policy: str
    source_table_policy_sha256: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_workbook_sha256: str
    schema_projection_sha256: str
    schema_total: int
    scope_schema_ids: tuple[int, ...]
    schema_scope_sha256: str
    structural_target_ids: tuple[tuple[str, int], ...]
    row_target_ids: tuple[tuple[str, int], ...]
    external_validation_role: str
    external_validation_report_norm_id: int
    external_validation_owner_scope: str
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage45SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage45SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    semantic_role: str
    status: str
    report_norm_id: int | None
    external_validation_report_norm_id: int | None
    external_owner_scope: str | None
    observations: tuple[str, ...]
    raw_values: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_starts: tuple[str, ...]
    period_ends: tuple[str, ...]
    period_roles: tuple[str, ...]
    period_type: str | None
    unit: str | None
    unit_multiplier: int | None
    unit_source_line_indices: tuple[int, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage45MappedAssignment:
    source_row_id: str
    semantic_role: str
    cell_index: int
    report_norm_id: int
    observation: str
    raw_value: str
    value: Decimal | None
    period_start: str
    period_end: str
    period_role: str
    period_type: str
    unit: str
    unit_multiplier: int
    unit_source_line_indices: tuple[int, ...]
    mapping_basis: str


@dataclass(frozen=True)
class TMPage45ExternalValidationObservation:
    source_row_id: str
    semantic_role: str
    cell_index: int
    external_report_norm_id: int
    external_owner_scope: str
    observation: str
    raw_value: str
    value: Decimal
    period_start: str
    period_end: str
    period_role: str
    period_type: str
    unit: str
    unit_multiplier: int
    mapping_authority_granted: bool
    reason: str


@dataclass(frozen=True)
class TMPage45AccountingCheck:
    check_id: str
    period_role: str
    status: str
    expected_value: Decimal
    observed_value: Decimal
    residual: Decimal
    reason: str


@dataclass(frozen=True)
class TMPage45MappingResult:
    statement_type: str
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    status: str
    mapping_authority_scope: str
    mapping_authority_granted: bool
    schema_item_count: int
    status_reconciled_schema_count: int
    mapped_schema_count: int
    structural_mapped_schema_count: int
    value_bearing_mapped_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    ambiguous_schema_count: int
    unresolved_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    source_only_validation_row_count: int
    source_question_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    blank_count: int
    zero_count: int
    mapped_assignment_count: int
    mapped_value_count: int
    external_validation_observation_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_fail_count: int
    schema_dispositions: tuple[TMPage45SchemaDisposition, ...]
    source_dispositions: tuple[TMPage45SourceDisposition, ...]
    mapped_assignments: tuple[TMPage45MappedAssignment, ...]
    external_validation_observations: tuple[TMPage45ExternalValidationObservation, ...]
    accounting_checks: tuple[TMPage45AccountingCheck, ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    schema_workbook_sha256: str
    schema_projection_sha256: str
    status_evidence_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage45MappingError(f"invalid positive TM page-45 field: {field}")
    return value


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


def _schema_scope_hash(schema_by_id: dict[int, SchemaItem]) -> str:
    payload = [
        (
            schema_id,
            schema_by_id[schema_id].canonical_name,
            schema_by_id[schema_id].parent_id,
            tuple(schema_by_id[schema_id].children),
        )
        for schema_id in sorted(TM_PAGE45_SCOPE_IDS)
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_tm_page45_mapping_policy(path: Path) -> TMPage45MappingPolicy:
    """Load the source- and schema-hash-bound page-45 mapping policy."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage45MappingError(f"cannot load TM page-45 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE45_EPS_SHARE_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("document") != "MBB_CONSOLIDATED_Q1_2026"
        or payload.get("page_number") != 45
        or payload.get("page_tag") != "page-0045"
        or payload.get("report_scope") != "CONSOLIDATED"
        or payload.get("mapping_authority_scope")
        != "MBB_CONSOLIDATED_Q1_2026_PAGE45_IDS_5946_5958_ONLY"
    ):
        raise TMPage45MappingError("TM page-45 mapping identity drifted")
    hash_fields = (
        "source_table_policy_sha256",
        "source_pdf_sha256",
        "source_render_sha256",
        "source_ocr_sha256",
        "upstream_ocr_sha256",
        "schema_workbook_sha256",
        "schema_projection_sha256",
        "schema_scope_sha256",
    )
    hashes = tuple(payload.get(field) for field in hash_fields)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage45MappingError("TM page-45 mapping hashes are invalid")
    table_policy = payload.get("source_table_policy")
    if table_policy != "config/tables/tm-note-page45-v1.yaml":
        raise TMPage45MappingError("TM page-45 source table policy path drifted")
    table_path = (path.parents[2] / str(table_policy)).resolve()
    if not table_path.is_file() or sha256_file(table_path) != hashes[0]:
        raise TMPage45MappingError("TM page-45 source table policy hash drifted")
    if (
        payload.get("schema_total") != TM_PAGE45_SCHEMA_TOTAL
        or payload.get("scope_schema_ids") != [{"start": 5946, "end": 5958}]
        or payload.get("scope_schema_total") != TM_PAGE45_SCOPE_SCHEMA_COUNT
    ):
        raise TMPage45MappingError("TM page-45 schema denominator/scope drifted")
    structural = payload.get("structural_target_ids")
    row_targets = payload.get("row_target_ids")
    if (
        not isinstance(structural, dict)
        or tuple(structural) != tuple(_STRUCTURAL_TARGETS)
        or structural != _STRUCTURAL_TARGETS
        or not isinstance(row_targets, dict)
        or tuple(row_targets) != tuple(_ROW_TARGETS)
        or row_targets != _ROW_TARGETS
    ):
        raise TMPage45MappingError("TM page-45 fixed target order drifted")
    external = payload.get("external_validation_row")
    if external != {
        "semantic_role": _EXTERNAL_ROLE,
        "report_norm_id": _EXTERNAL_ID,
        "owner_scope": _EXTERNAL_OWNER,
        "canonical_unit": "VND",
        "unit_multiplier": 1_000_000,
        "period_type": "DURATION",
    }:
        raise TMPage45MappingError("TM page-45 external validation ownership drifted")
    if payload.get("hierarchy_contract") != {
        "common_parent_report_norm_id": 1128,
        "roots": {5946: [5947, 5948], 5949: [5950, 5951, 5953, 5956]},
        "nested_parents": {5951: [5952], 5953: [5954, 5955], 5956: [5957, 5958]},
        "leaf_report_norm_ids": [5947, 5948, 5950, 5952, 5954, 5955, 5957, 5958],
    }:
        raise TMPage45MappingError("TM page-45 hierarchy contract drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage45MappingError("TM page-45 forbidden mapping inputs drifted")
    return TMPage45MappingPolicy(
        source_path=path,
        document=str(payload["document"]),
        page_number=_positive_int(payload, "page_number"),
        page_tag=str(payload["page_tag"]),
        report_scope=str(payload["report_scope"]),
        mapping_authority_scope=str(payload["mapping_authority_scope"]),
        source_table_policy=str(table_policy),
        source_table_policy_sha256=str(hashes[0]),
        source_pdf_sha256=str(hashes[1]),
        source_render_sha256=str(hashes[2]),
        source_ocr_sha256=str(hashes[3]),
        upstream_ocr_sha256=str(hashes[4]),
        schema_workbook_sha256=str(hashes[5]),
        schema_projection_sha256=str(hashes[6]),
        schema_total=TM_PAGE45_SCHEMA_TOTAL,
        scope_schema_ids=tuple(sorted(TM_PAGE45_SCOPE_IDS)),
        schema_scope_sha256=str(hashes[7]),
        structural_target_ids=tuple((str(key), int(value)) for key, value in structural.items()),
        row_target_ids=tuple((str(key), int(value)) for key, value in row_targets.items()),
        external_validation_role=_EXTERNAL_ROLE,
        external_validation_report_norm_id=_EXTERNAL_ID,
        external_validation_owner_scope=_EXTERNAL_OWNER,
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _validate_schema_branch(schema_by_id: dict[int, SchemaItem]) -> None:
    expected = {
        5946: (1128, (5947, 5948)),
        5947: (5946, ()),
        5948: (5946, ()),
        5949: (1128, (5950, 5951, 5953, 5956)),
        5950: (5949, ()),
        5951: (5949, (5952,)),
        5952: (5951, ()),
        5953: (5949, (5954, 5955)),
        5954: (5953, ()),
        5955: (5953, ()),
        5956: (5949, (5957, 5958)),
        5957: (5956, ()),
        5958: (5956, ()),
    }
    for schema_id, (parent_id, children) in expected.items():
        item = schema_by_id[schema_id]
        if (
            item.parent_id != parent_id
            or tuple(item.children) != children
            or item.canonical_name != _CANONICAL_NAMES[schema_id]
        ):
            raise TMPage45MappingError(f"TM page-45 schema hierarchy drifted: {schema_id}")
    external = schema_by_id[_EXTERNAL_ID]
    if external.parent_id != 6019 or external.canonical_name != "+ Lãi trong kỳ":
        raise TMPage45MappingError("TM page-45 external validation schema identity drifted")


def _period_contract(row: TMPage45LogicalRow) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        (
            role,
            row.period_type,
            start.isoformat(),
            end.isoformat(),
        )
        for role, start, end in zip(
            row.cell_period_roles,
            row.cell_period_starts,
            row.cell_period_ends,
            strict=True,
        )
    )


def _expected_row_contract(role: str) -> tuple[str, int, tuple[tuple[str, str, str, str], ...]]:
    if role == _EXTERNAL_ROLE:
        return "VND", 1_000_000, _DURATION_PERIOD_CONTRACT
    if role == "WEIGHTED_AVERAGE_ORDINARY_SHARES":
        return "SHARE", 1, _DURATION_PERIOD_CONTRACT
    if role == "BASIC_EARNINGS_PER_SHARE":
        return "VND_PER_SHARE", 1, _DURATION_PERIOD_CONTRACT
    return "SHARE", 1, _SNAPSHOT_PERIOD_CONTRACT


def _status_evidence_hash(parsed: ParsedTMPage45) -> str:
    records = []
    for row in parsed.rows:
        if not isinstance(row, TMPage45LogicalRow):
            continue
        for cell_index, (cell, evidence) in enumerate(
            zip(row.row.cells, row.visual_cell_evidence, strict=True)
        ):
            if cell.observation not in {ObservationKind.DASH, ObservationKind.BLANK}:
                continue
            if isinstance(evidence, VisualCellEvidence):
                evidence_payload = {
                    key: value
                    for key, value in asdict(evidence).items()
                    if key != "source_image_path"
                }
            elif isinstance(evidence, TMPage45BlankEvidence):
                evidence_payload = {
                    key: value
                    for key, value in asdict(evidence).items()
                    if key != "source_image_path"
                }
            else:
                raise TMPage45MappingError("TM page-45 DASH/BLANK evidence is absent")
            records.append((row.row_id, cell_index, cell.observation.value, evidence_payload))
    return hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _accounting_checks(rows: dict[str, TMPage45LogicalRow]) -> tuple[TMPage45AccountingCheck, ...]:
    profit = rows[_EXTERNAL_ROLE]
    weighted = rows["WEIGHTED_AVERAGE_ORDINARY_SHARES"]
    eps = rows["BASIC_EARNINGS_PER_SHARE"]
    checks = []
    for cell_index, period_role in enumerate(profit.cell_period_roles):
        profit_value = profit.row.cells[cell_index].value
        weighted_value = weighted.row.cells[cell_index].value
        observed = eps.row.cells[cell_index].value
        if (
            profit_value is None
            or weighted_value is None
            or observed is None
            or weighted_value == 0
        ):
            raise TMPage45MappingError("TM page-45 EPS validation inputs are invalid")
        expected = (profit_value * 1_000_000 / weighted_value).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        residual = observed - expected
        checks.append(
            TMPage45AccountingCheck(
                check_id=f"EPS_ROUND_HALF_UP:{period_role}",
                period_role=period_role,
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=residual,
                reason=(
                    "source-visible EPS agrees with profit attributable to bank shareholders "
                    "times one million divided by weighted shares, rounded half up; the equation "
                    "validates but never imputes or selects a mapping"
                ),
            )
        )
    return tuple(checks)


def reconcile_tm_page45_items(
    parsed: ParsedTMPage45,
    *,
    schema: Sequence[SchemaItem],
    policy: TMPage45MappingPolicy,
    source_pdf_path: Path,
    schema_workbook_path: Path,
) -> TMPage45MappingResult:
    """Bind the thirteen frozen page-45 items and retain profit as external validation."""

    if (
        policy.mapping_authority_scope != "MBB_CONSOLIDATED_Q1_2026_PAGE45_IDS_5946_5958_ONLY"
        or dict(policy.structural_target_ids) != _STRUCTURAL_TARGETS
        or dict(policy.row_target_ids) != _ROW_TARGETS
        or policy.external_validation_report_norm_id != _EXTERNAL_ID
        or policy.external_validation_owner_scope != _EXTERNAL_OWNER
        or set(policy.forbidden_mapping_inputs) != _REQUIRED_FORBIDDEN
    ):
        raise TMPage45MappingError("TM page-45 mapping policy target drifted")
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
        or parsed.upstream_ocr_sha256 != policy.upstream_ocr_sha256
    ):
        raise TMPage45MappingError("TM page-45 parser/mapping identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage45MappingError("TM page-45 source PDF hash drifted")
    if sha256_file(schema_workbook_path) != policy.schema_workbook_sha256:
        raise TMPage45MappingError("TM page-45 schema workbook hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != TM_PAGE45_SCHEMA_TOTAL or len(tm_schema) != policy.schema_total:
        raise TMPage45MappingError("TM page-45 schema denominator drifted")
    projection_hash = _schema_projection_hash(tm_schema)
    if projection_hash != policy.schema_projection_sha256:
        raise TMPage45MappingError("TM page-45 full schema projection drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if (
        set(policy.scope_schema_ids) != TM_PAGE45_SCOPE_IDS
        or _schema_scope_hash(schema_by_id) != policy.schema_scope_sha256
    ):
        raise TMPage45MappingError("TM page-45 owned schema scope drifted")
    _validate_schema_branch(schema_by_id)
    if (
        [table.table_key for table in parsed.tables] != ["EARNINGS_PER_SHARE", "SHARE_COUNTS"]
        or [len(table.rows) for table in parsed.tables] != [4, 10]
        or len(parsed.rows) != TM_PAGE45_SOURCE_ROW_COUNT
        or parsed.financial_slot_count != TM_PAGE45_FINANCIAL_SLOT_COUNT
        or parsed.observation_count(ObservationKind.VALUE) != TM_PAGE45_VALUE_COUNT
        or parsed.observation_count(ObservationKind.DASH) != TM_PAGE45_DASH_COUNT
        or parsed.observation_count(ObservationKind.BLANK) != TM_PAGE45_BLANK_COUNT
        or parsed.observation_count(ObservationKind.ZERO) != 0
    ):
        raise TMPage45MappingError("TM page-45 parser denominator drifted")

    source_by_schema: dict[int, list[str]] = {schema_id: [] for schema_id in TM_PAGE45_SCOPE_IDS}
    assignments: list[TMPage45MappedAssignment] = []
    external_observations: list[TMPage45ExternalValidationObservation] = []
    source_dispositions: list[TMPage45SourceDisposition] = []
    logical_by_role: dict[str, TMPage45LogicalRow] = {}
    for row in parsed.rows:
        if isinstance(row, TMPage45StructuralRow):
            schema_id = _STRUCTURAL_TARGETS[row.table_key]
            source_by_schema[schema_id].append(row.row_id)
            source_dispositions.append(
                TMPage45SourceDisposition(
                    row_id=row.row_id,
                    table_key=row.table_key,
                    ordinal=row.ordinal,
                    semantic_role=row.semantic_role,
                    status=TMPage45SourceStatus.MAPPED_STRUCTURAL_SCOPED.value,
                    report_norm_id=schema_id,
                    external_validation_report_norm_id=None,
                    external_owner_scope=None,
                    observations=(),
                    raw_values=(),
                    values=(),
                    period_starts=(),
                    period_ends=(),
                    period_roles=(),
                    period_type=None,
                    unit=None,
                    unit_multiplier=None,
                    unit_source_line_indices=(),
                    question_required=False,
                    reason="visible note title uniquely binds the frozen page-45 structural root",
                )
            )
            continue
        logical_by_role[row.semantic_role] = row
        expected_unit, expected_multiplier, expected_periods = _expected_row_contract(
            row.semantic_role
        )
        if (
            row.canonical_unit != expected_unit
            or row.unit_multiplier != expected_multiplier
            or _period_contract(row) != expected_periods
        ):
            raise TMPage45MappingError(
                f"TM page-45 row-local period/unit drifted: {row.semantic_role}"
            )
        if row.semantic_role == _EXTERNAL_ROLE:
            if any(
                cell.observation is not ObservationKind.VALUE or cell.value is None
                for cell in row.row.cells
            ):
                raise TMPage45MappingError("TM page-45 external profit validation is not finite")
            for cell_index, cell in enumerate(row.row.cells):
                assert cell.value is not None
                external_observations.append(
                    TMPage45ExternalValidationObservation(
                        source_row_id=row.row_id,
                        semantic_role=row.semantic_role,
                        cell_index=cell_index,
                        external_report_norm_id=_EXTERNAL_ID,
                        external_owner_scope=_EXTERNAL_OWNER,
                        observation=cell.observation.value,
                        raw_value=cell.raw_text,
                        value=cell.value,
                        period_start=row.cell_period_starts[cell_index].isoformat(),
                        period_end=row.cell_period_ends[cell_index].isoformat(),
                        period_role=row.cell_period_roles[cell_index],
                        period_type=row.period_type,
                        unit=row.canonical_unit,
                        unit_multiplier=row.unit_multiplier,
                        mapping_authority_granted=False,
                        reason=(
                            "profit row validates externally owned ReportNormID 1131 and is excluded "
                            "from page-45 ownership and mapped assignments"
                        ),
                    )
                )
            source_dispositions.append(
                TMPage45SourceDisposition(
                    row_id=row.row_id,
                    table_key=row.table_key,
                    ordinal=row.ordinal,
                    semantic_role=row.semantic_role,
                    status=TMPage45SourceStatus.SOURCE_ONLY_EXTERNAL_VALIDATION.value,
                    report_norm_id=None,
                    external_validation_report_norm_id=_EXTERNAL_ID,
                    external_owner_scope=_EXTERNAL_OWNER,
                    observations=tuple(cell.observation.value for cell in row.row.cells),
                    raw_values=tuple(cell.raw_text for cell in row.row.cells),
                    values=tuple(cell.value for cell in row.row.cells),
                    period_starts=tuple(value.isoformat() for value in row.cell_period_starts),
                    period_ends=tuple(value.isoformat() for value in row.cell_period_ends),
                    period_roles=row.cell_period_roles,
                    period_type=row.period_type,
                    unit=row.canonical_unit,
                    unit_multiplier=row.unit_multiplier,
                    unit_source_line_indices=row.unit_source_line_indices,
                    question_required=False,
                    reason=(
                        "visible profit cells are source-only validation of externally owned 1131; "
                        "page 45 does not duplicate the page-44 schema owner"
                    ),
                )
            )
            continue
        schema_id = _ROW_TARGETS[row.semantic_role]
        source_by_schema[schema_id].append(row.row_id)
        for cell_index, (cell, evidence) in enumerate(
            zip(row.row.cells, row.visual_cell_evidence, strict=True)
        ):
            if cell.observation is ObservationKind.DASH and not isinstance(
                evidence, VisualCellEvidence
            ):
                raise TMPage45MappingError("TM page-45 mapped DASH lost pixel evidence")
            if cell.observation is ObservationKind.BLANK and not isinstance(
                evidence, TMPage45BlankEvidence
            ):
                raise TMPage45MappingError("TM page-45 mapped BLANK lost pixel evidence")
            if cell.observation is ObservationKind.ZERO:
                raise TMPage45MappingError("TM page-45 ZERO cannot replace DASH or BLANK")
            assignments.append(
                TMPage45MappedAssignment(
                    source_row_id=row.row_id,
                    semantic_role=row.semantic_role,
                    cell_index=cell_index,
                    report_norm_id=schema_id,
                    observation=cell.observation.value,
                    raw_value=cell.raw_text,
                    value=cell.value,
                    period_start=row.cell_period_starts[cell_index].isoformat(),
                    period_end=row.cell_period_ends[cell_index].isoformat(),
                    period_role=row.cell_period_roles[cell_index],
                    period_type=row.period_type,
                    unit=row.canonical_unit,
                    unit_multiplier=row.unit_multiplier,
                    unit_source_line_indices=row.unit_source_line_indices,
                    mapping_basis=(
                        "VISIBLE_PAGE45_SEMANTIC_ROW_X_FIXED_TABLE_LOCAL_PERIOD_AND_UNIT_TO_FROZEN_SCHEMA"
                    ),
                )
            )
        source_dispositions.append(
            TMPage45SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                semantic_role=row.semantic_role,
                status=TMPage45SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
                report_norm_id=schema_id,
                external_validation_report_norm_id=None,
                external_owner_scope=None,
                observations=tuple(cell.observation.value for cell in row.row.cells),
                raw_values=tuple(cell.raw_text for cell in row.row.cells),
                values=tuple(cell.value for cell in row.row.cells),
                period_starts=tuple(value.isoformat() for value in row.cell_period_starts),
                period_ends=tuple(value.isoformat() for value in row.cell_period_ends),
                period_roles=row.cell_period_roles,
                period_type=row.period_type,
                unit=row.canonical_unit,
                unit_multiplier=row.unit_multiplier,
                unit_source_line_indices=row.unit_source_line_indices,
                question_required=False,
                reason=(
                    "visible row identity uniquely binds its frozen page-45 schema item while "
                    "preserving both cell statuses, periods, and the row-local unit"
                ),
            )
        )
    if set(logical_by_role) != {_EXTERNAL_ROLE, *_ROW_TARGETS}:
        raise TMPage45MappingError("TM page-45 logical role partition drifted")
    if any(not source_by_schema[schema_id] for schema_id in TM_PAGE45_SCOPE_IDS):
        raise TMPage45MappingError("TM page-45 mapped item lacks source provenance")
    accounting_checks = _accounting_checks(logical_by_role)
    schema_dispositions = tuple(
        TMPage45SchemaDisposition(
            report_norm_id=item.schema_id,
            display_order=item.display_order,
            canonical_name=item.canonical_name,
            status=(
                TMPage45SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
                if item.schema_id in TM_PAGE45_SCOPE_IDS
                else TMPage45SchemaStatus.UNASSESSED.value
            ),
            source_ids=tuple(dict.fromkeys(source_by_schema.get(item.schema_id, ()))),
            reason=(
                "page 45 is the unique owner of this EPS/share structural or value-bearing item"
                if item.schema_id in TM_PAGE45_SCOPE_IDS
                else "outside the page-45 owned schema scope"
            ),
        )
        for item in tm_schema
    )
    result = TMPage45MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=45,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="PAGE45_EPS_SHARE_SCOPE_RECONCILED_MAPPED",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=TM_PAGE45_SCOPE_SCHEMA_COUNT,
        mapped_schema_count=TM_PAGE45_MAPPED_SCHEMA_COUNT,
        structural_mapped_schema_count=TM_PAGE45_STRUCTURAL_MAPPED_SCHEMA_COUNT,
        value_bearing_mapped_schema_count=TM_PAGE45_VALUE_BEARING_MAPPED_SCHEMA_COUNT,
        not_observed_schema_count=0,
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unresolved_schema_count=0,
        unassessed_schema_count=TM_PAGE45_UNASSESSED_SCHEMA_COUNT,
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status != TMPage45SourceStatus.SOURCE_ONLY_EXTERNAL_VALIDATION.value
            for item in source_dispositions
        ),
        source_only_validation_row_count=sum(
            item.status == TMPage45SourceStatus.SOURCE_ONLY_EXTERNAL_VALIDATION.value
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        blank_count=parsed.observation_count(ObservationKind.BLANK),
        zero_count=parsed.observation_count(ObservationKind.ZERO),
        mapped_assignment_count=len(assignments),
        mapped_value_count=sum(
            item.observation == ObservationKind.VALUE.value for item in assignments
        ),
        external_validation_observation_count=len(external_observations),
        accounting_check_count=len(accounting_checks),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting_checks),
        accounting_fail_count=sum(check.status == "FAIL" for check in accounting_checks),
        schema_dispositions=schema_dispositions,
        source_dispositions=tuple(source_dispositions),
        mapped_assignments=tuple(assignments),
        external_validation_observations=tuple(external_observations),
        accounting_checks=accounting_checks,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        schema_workbook_sha256=policy.schema_workbook_sha256,
        schema_projection_sha256=projection_hash,
        status_evidence_sha256=_status_evidence_hash(parsed),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PAGE45_PPOCR_LABELS_AND_GEOMETRY",
            "VISIBLE_TABLE_LOCAL_DURATION_AND_SNAPSHOT_PERIODS",
            "VISIBLE_ROW_LOCAL_VND_MILLION_SHARE_AND_VND_PER_SHARE_UNITS",
            "PIXEL_BACKED_DASH_AND_ALL_WHITE_REGISTERED_BLANK_EVIDENCE",
            "FROZEN_TM_SCHEMA_SCOPE_IDS_5946_THROUGH_5958",
            "REPORT_NORM_ID_1131_AS_PAGE44_EXTERNAL_OWNER_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page45_mapping_result(result)


def validate_tm_page45_mapping_result(
    result: TMPage45MappingResult,
) -> TMPage45MappingResult:
    if (
        result.schema_item_count != TM_PAGE45_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE45_SCOPE_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE45_MAPPED_SCHEMA_COUNT
        or result.structural_mapped_schema_count != TM_PAGE45_STRUCTURAL_MAPPED_SCHEMA_COUNT
        or result.value_bearing_mapped_schema_count != TM_PAGE45_VALUE_BEARING_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != 0
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unresolved_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE45_UNASSESSED_SCHEMA_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE45_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE45_MAPPED_SOURCE_ROW_COUNT
        or result.source_only_validation_row_count != TM_PAGE45_SOURCE_ONLY_VALIDATION_ROW_COUNT
        or result.source_question_row_count != 0
        or result.financial_slot_count != TM_PAGE45_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE45_VALUE_COUNT
        or result.dash_count != TM_PAGE45_DASH_COUNT
        or result.blank_count != TM_PAGE45_BLANK_COUNT
        or result.zero_count != 0
        or result.mapped_assignment_count != TM_PAGE45_ASSIGNMENT_COUNT
        or result.mapped_value_count != TM_PAGE45_MAPPED_VALUE_COUNT
        or result.external_validation_observation_count
        != TM_PAGE45_EXTERNAL_VALIDATION_OBSERVATION_COUNT
        or result.accounting_check_count != TM_PAGE45_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE45_ACCOUNTING_CHECK_COUNT
        or result.accounting_fail_count != 0
        or not result.mapping_authority_granted
    ):
        raise TMPage45MappingError("TM page-45 mapping denominator drifted")
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage45SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage45SchemaStatus.UNASSESSED.value
    }
    if (
        result.status_reconciled_schema_count + result.unassessed_schema_count
        != result.schema_item_count
        or mapped != TM_PAGE45_MAPPED_SCHEMA_IDS
        or len(unassessed) != TM_PAGE45_UNASSESSED_SCHEMA_COUNT
        or mapped | unassessed != {item.report_norm_id for item in result.schema_dispositions}
        or any(
            not item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id in mapped
        )
        or any(
            item.source_ids
            for item in result.schema_dispositions
            if item.report_norm_id not in mapped
        )
    ):
        raise TMPage45MappingError("TM page-45 schema disposition partition drifted")
    assignment_statuses = [item.observation for item in result.mapped_assignments]
    if (
        {item.report_norm_id for item in result.mapped_assignments} != set(_ROW_TARGETS.values())
        or any(
            sum(item.report_norm_id == schema_id for item in result.mapped_assignments) != 2
            for schema_id in _ROW_TARGETS.values()
        )
        or assignment_statuses.count(ObservationKind.VALUE.value) != 12
        or assignment_statuses.count(ObservationKind.DASH.value) != 8
        or assignment_statuses.count(ObservationKind.BLANK.value) != 2
        or ObservationKind.ZERO.value in assignment_statuses
        or any(
            (item.observation == ObservationKind.VALUE.value) != (item.value is not None)
            for item in result.mapped_assignments
        )
        or any(item.report_norm_id == _EXTERNAL_ID for item in result.mapped_assignments)
    ):
        raise TMPage45MappingError("TM page-45 assignment status partition drifted")
    external = result.external_validation_observations
    if (
        len(external) != 2
        or {item.external_report_norm_id for item in external} != {_EXTERNAL_ID}
        or {item.external_owner_scope for item in external} != {_EXTERNAL_OWNER}
        or {item.observation for item in external} != {ObservationKind.VALUE.value}
        or any(item.mapping_authority_granted for item in external)
        or {(item.period_role, item.period_start, item.period_end) for item in external}
        != {
            ("CURRENT", "2026-01-01", "2026-03-31"),
            ("COMPARATIVE", "2025-01-01", "2025-03-31"),
        }
        or {(item.unit, item.unit_multiplier) for item in external} != {("VND", 1_000_000)}
    ):
        raise TMPage45MappingError("TM page-45 external validation partition drifted")
    source_statuses = [item.status for item in result.source_dispositions]
    if (
        source_statuses.count(TMPage45SourceStatus.MAPPED_STRUCTURAL_SCOPED.value) != 2
        or source_statuses.count(TMPage45SourceStatus.MAPPED_AUTOMATIC_SCOPED.value) != 11
        or source_statuses.count(TMPage45SourceStatus.SOURCE_ONLY_EXTERNAL_VALIDATION.value) != 1
        or any(item.question_required for item in result.source_dispositions)
        or any(check.status != "PASS" or check.residual != 0 for check in result.accounting_checks)
        or not _SHA256.fullmatch(result.status_evidence_sha256)
    ):
        raise TMPage45MappingError("TM page-45 source/validation partition drifted")
    return result


__all__ = [
    "TM_PAGE45_MAPPING_POLICY_RELATIVE_PATH",
    "TM_PAGE45_MAPPED_SCHEMA_IDS",
    "TM_PAGE45_NOT_OBSERVED_SCHEMA_IDS",
    "TM_PAGE45_SCOPE_IDS",
    "TMPage45AccountingCheck",
    "TMPage45ExternalValidationObservation",
    "TMPage45MappedAssignment",
    "TMPage45MappingError",
    "TMPage45MappingPolicy",
    "TMPage45MappingResult",
    "TMPage45SchemaDisposition",
    "TMPage45SchemaStatus",
    "TMPage45SourceDisposition",
    "TMPage45SourceStatus",
    "load_tm_page45_mapping_policy",
    "reconcile_tm_page45_items",
    "validate_tm_page45_mapping_result",
]
