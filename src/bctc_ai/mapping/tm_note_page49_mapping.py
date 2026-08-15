"""Source-scoped item mapping for MBB consolidated TM PDF page 49."""

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

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.schema.registry import SchemaItem
from bctc_ai.tables.tm_note_page49 import ParsedTMPage49

TM_PAGE49_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page49-v1.yaml")
TM_PAGE49_SCHEMA_TOTAL = 1_714
TM_PAGE49_RECONCILED_SCHEMA_COUNT = 22
TM_PAGE49_MAPPED_SCHEMA_COUNT = 10
TM_PAGE49_AMBIGUOUS_SCHEMA_COUNT = 0
TM_PAGE49_NOT_OBSERVED_COUNT = 12
TM_PAGE49_UNASSESSED_COUNT = 1_692
TM_PAGE49_SOURCE_ROW_COUNT = 12
TM_PAGE49_MAPPED_SOURCE_COUNT = 10
TM_PAGE49_AMBIGUOUS_SOURCE_COUNT = 0
TM_PAGE49_SOURCE_ONLY_COUNT = 2
TM_PAGE49_QUESTION_SOURCE_COUNT = 0
TM_PAGE49_FINANCIAL_SLOT_COUNT = 28
TM_PAGE49_VALUE_COUNT = 27
TM_PAGE49_DASH_COUNT = 1
TM_PAGE49_MAPPED_VALUE_COUNT = 27
TM_PAGE49_ACCOUNTING_CHECK_COUNT = 6
TM_PAGE49_ACCOUNTING_PASS_COUNT = 5
TM_PAGE49_ACCOUNTING_NOT_TESTABLE_COUNT = 1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = {*range(1221, 1229), *range(1269, 1280), *range(6031, 6034)}
_MAPPED_IDS = {1221, 1227, 1228, 1269, 1270, 1271, 1278, *range(6031, 6034)}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    1222,
    1223,
    1224,
    1225,
    1226,
    1272,
    1273,
    1274,
    1275,
    1276,
    1277,
    1279,
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
}


class TMPage49MappingError(ValueError):
    pass


class TMPage49RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class TMPage49SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage49SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


@dataclass(frozen=True)
class TMPage49RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage49RuleDisposition
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage49MappingPolicy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    report_scope: str
    mapping_authority_scope: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    schema_total: int
    scoped_schema_ids: tuple[int, ...]
    minimum_visible_label_similarity: float
    rows: tuple[TMPage49RowRule, ...]
    ambiguous_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage49SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage49SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
    candidate_report_norm_ids: tuple[int, ...]
    candidate_canonical_names: tuple[str, ...]
    visible_label_similarity: float | None
    observations: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    period_starts: tuple[str | None, ...]
    period_ends: tuple[str | None, ...]
    period_roles: tuple[str | None, ...]
    unit: str
    unit_multiplier: int
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    question_required: bool
    reason: str


@dataclass(frozen=True)
class TMPage49AccountingCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage49MappingResult:
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
    ambiguous_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    ambiguous_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_value_count: int
    accounting_check_count: int
    accounting_pass_count: int
    accounting_not_testable_count: int
    schema_dispositions: tuple[TMPage49SchemaDisposition, ...]
    source_dispositions: tuple[TMPage49SourceDisposition, ...]
    accounting_checks: tuple[TMPage49AccountingCheck, ...]
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    dash_pixel_evidence_sha256: str
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMPage49MappingError(f"invalid positive TM page-49 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage49MappingError(f"TM page-49 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage49MappingError(f"TM page-49 {field} contains duplicates")
    return result


def load_tm_page49_mapping_policy(path: Path) -> TMPage49MappingPolicy:
    """Load and validate the exact row-level mapping authority for page 49."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage49MappingError(f"cannot load TM page-49 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE49_SCOPED_MIXED_AXIS_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 49
        or payload.get("page_tag") != "page-0049"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage49MappingError("TM page-49 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage49MappingError("TM page-49 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < float(threshold) <= 1
    ):
        raise TMPage49MappingError("TM page-49 mapping similarity threshold is invalid")
    scoped = _ids(payload.get("scoped_schema_ids"), "scoped schema IDs")
    if set(scoped) != _SCOPED_IDS:
        raise TMPage49MappingError("TM page-49 scoped schema branches drifted")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE49_SOURCE_ROW_COUNT:
        raise TMPage49MappingError("TM page-49 mapping row denominator drifted")
    valid_observations = {observation.value for observation in ObservationKind}
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage49MappingError("TM page-49 mapping row is invalid")
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        label = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        try:
            disposition = TMPage49RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage49MappingError("TM page-49 rule disposition is invalid") from exc
        candidates = _ids(
            record.get("candidate_report_norm_ids"),
            "candidate ReportNormIds",
            allow_empty=True,
        )
        expected_width = 2 if table_key == "RISK_PROVISION_EXPENSE" else 4
        if (
            table_key not in {"RISK_PROVISION_EXPENSE", "STATE_BUDGET_OBLIGATIONS"}
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (label is not None and not isinstance(label, str))
            or row_kind not in {"NUMERIC", "LABEL_ONLY"}
            or not isinstance(observations, list)
            or len(observations) != expected_width
            or any(value not in valid_observations for value in observations)
        ):
            raise TMPage49MappingError("TM page-49 mapping row identity is invalid")
        if disposition is TMPage49RuleDisposition.FIXED:
            if (
                isinstance(report_norm_id, bool)
                or not isinstance(report_norm_id, int)
                or candidates
            ):
                raise TMPage49MappingError("fixed TM page-49 mapping rule is malformed")
        elif disposition is TMPage49RuleDisposition.AMBIGUOUS_MAPPING:
            if report_norm_id is not None or not candidates:
                raise TMPage49MappingError("ambiguous TM page-49 mapping rule is malformed")
        elif report_norm_id is not None or candidates:
            raise TMPage49MappingError("source-only TM page-49 rule cannot select an identity")
        rows.append(
            TMPage49RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=retrieval_key(label) if label is not None else None,
                expected_row_kind=row_kind,
                expected_observations=tuple(observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                candidate_report_norm_ids=candidates,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage49MappingError("TM page-49 mapping rule identities are duplicated")
    fixed_ids = {
        row.report_norm_id for row in rows if row.disposition is TMPage49RuleDisposition.FIXED
    }
    candidate_ids = {
        candidate
        for row in rows
        if row.disposition is TMPage49RuleDisposition.AMBIGUOUS_MAPPING
        for candidate in row.candidate_report_norm_ids
    }
    ambiguous = _ids(payload.get("ambiguous_schema_ids"), "ambiguous schema IDs", allow_empty=True)
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed schema IDs")
    if (
        fixed_ids != _MAPPED_IDS
        or candidate_ids != _AMBIGUOUS_IDS
        or set(ambiguous) != _AMBIGUOUS_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or fixed_ids | set(ambiguous) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage49MappingError("TM page-49 schema reconciliation sets drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage49MappingError("TM page-49 forbidden mapping inputs drifted")
    document = payload.get("document")
    mapping_scope = payload.get("mapping_authority_scope")
    if not isinstance(document, str) or not isinstance(mapping_scope, str) or not mapping_scope:
        raise TMPage49MappingError("TM page-49 mapping scope is invalid")
    return TMPage49MappingPolicy(
        source_path=path,
        document=document,
        page_number=49,
        page_tag="page-0049",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=mapping_scope,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        scoped_schema_ids=scoped,
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        ambiguous_schema_ids=ambiguous,
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


def _dash_hash(parsed: ParsedTMPage49) -> str:
    payload = [
        asdict(evidence)
        for row in parsed.rows
        for evidence in row.visual_cell_evidence
        if evidence is not None
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _numeric_row(parsed: ParsedTMPage49, table_key: str, ordinal: int):
    row = next(
        (row for row in parsed.rows if row.table_key == table_key and row.ordinal == ordinal),
        None,
    )
    if row is None:
        raise TMPage49MappingError(f"TM page-49 row is absent: {table_key}/{ordinal}")
    return row


def _validation(parsed: ParsedTMPage49) -> tuple[TMPage49AccountingCheck, ...]:
    checks = []
    provision = next(
        table for table in parsed.tables if table.table_key == "RISK_PROVISION_EXPENSE"
    )
    for axis_index, axis in enumerate(provision.axes):
        components = [
            _numeric_row(parsed, "RISK_PROVISION_EXPENSE", ordinal).row.cells[axis_index]
            for ordinal in range(2, 7)
        ]
        observed = _numeric_row(parsed, "RISK_PROVISION_EXPENSE", 7).row.cells[axis_index].value
        if any(cell.observation is ObservationKind.DASH for cell in components):
            checks.append(
                TMPage49AccountingCheck(
                    check_id="RISK_PROVISION_TOTAL_EQUALS_FIVE_VISIBLE_DETAILS",
                    axis_role=axis.axis_role,
                    status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                    expected_value=None,
                    observed_value=observed,
                    residual=None,
                    reason="visible DASH is an observation status and cannot be coerced to zero",
                )
            )
            continue
        if any(cell.value is None for cell in components) or observed is None:
            raise TMPage49MappingError("TM page-49 provision validation received a blank")
        expected = sum((cell.value for cell in components if cell.value is not None), Decimal(0))
        residual = observed - expected
        checks.append(
            TMPage49AccountingCheck(
                check_id="RISK_PROVISION_TOTAL_EQUALS_FIVE_VISIBLE_DETAILS",
                axis_role=axis.axis_role,
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=residual,
                reason="visible finite detail values combined only as post-mapping validation",
            )
        )
    obligations = next(
        table for table in parsed.tables if table.table_key == "STATE_BUDGET_OBLIGATIONS"
    )
    for ordinal in range(2, 6):
        row = _numeric_row(parsed, "STATE_BUDGET_OBLIGATIONS", ordinal)
        values = tuple(cell.value for cell in row.row.cells)
        if any(value is None for value in values):
            raise TMPage49MappingError("TM page-49 obligation validation received a blank")
        opening, payable, paid, closing = (value for value in values if value is not None)
        expected = opening + payable + paid
        residual = closing - expected
        checks.append(
            TMPage49AccountingCheck(
                check_id=f"STATE_BUDGET_ROW_{ordinal:04d}_ROLLFORWARD",
                axis_role="OPENING_PLUS_PAYABLE_PLUS_PAID_EQUALS_CLOSING",
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=closing,
                residual=residual,
                reason=(
                    "visible four-axis rollforward checked after extraction; parentheses remain negative"
                ),
            )
        )
    if [axis.axis_role for axis in obligations.axes] != [
        "OPENING_BALANCE",
        "PAYABLE_ACTIVITY",
        "PAID_ACTIVITY",
        "CLOSING_BALANCE",
    ]:
        raise TMPage49MappingError("TM page-49 obligation axis order drifted")
    return tuple(checks)


def _source_reason(rule: TMPage49RowRule) -> str:
    if rule.identity == ("RISK_PROVISION_EXPENSE", 2):
        return (
            "one visible customer-loan provision amount cannot be split between IDs 1224 and 1225"
        )
    if rule.identity == ("RISK_PROVISION_EXPENSE", 3):
        return "one visible TCTD-loan provision amount cannot be split between IDs 1222 and 1223"
    if rule.identity == ("RISK_PROVISION_EXPENSE", 4):
        return "visible purchased-debt provision is broader than VAMC-only schema ID 1226"
    if rule.disposition is TMPage49RuleDisposition.SOURCE_ONLY_VALIDATION:
        return (
            "visible note title retained as structural provenance; terminal total carries the root"
        )
    return "fixed page-49 note hierarchy, row order, visible label and observation rule passed"


def reconcile_tm_page49_items(
    parsed: ParsedTMPage49,
    *,
    schema: list[SchemaItem],
    policy: TMPage49MappingPolicy,
    source_pdf_path: Path,
) -> TMPage49MappingResult:
    """Reconcile the two disjoint page-49 branches without value-based item selection."""

    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage49MappingError("TM page-49 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage49MappingError("TM page-49 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE49_SCHEMA_TOTAL:
        raise TMPage49MappingError("TM page-49 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage49MappingError("TM page-49 scoped ReportNormIds are absent")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage49MappingError("TM page-49 parsed row order drifted from mapping policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    candidate_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage49MappingError(f"TM page-49 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage49MappingError(f"TM page-49 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage49MappingError(f"TM page-49 label anchor failed: {row.row_id}")
        reason = _source_reason(rule)
        if rule.disposition is TMPage49RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage49SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            question_required = False
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
        elif rule.disposition is TMPage49RuleDisposition.AMBIGUOUS_MAPPING:
            status = TMPage49SourceStatus.AMBIGUOUS_MAPPING.value
            canonical = None
            question_required = True
            for candidate in rule.candidate_report_norm_ids:
                candidate_rows_by_schema.setdefault(candidate, []).append(row.row_id)
        else:
            status = TMPage49SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            question_required = False
        table = next(table for table in parsed.tables if table.table_key == row.table_key)
        source_dispositions.append(
            TMPage49SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
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
                period_starts=tuple(
                    value.isoformat() if value is not None else None
                    for value in row.cell_period_starts
                ),
                period_ends=tuple(
                    value.isoformat() if value is not None else None
                    for value in row.cell_period_ends
                ),
                period_roles=row.cell_period_roles,
                unit=table.axes[0].canonical_unit,
                unit_multiplier=table.axes[0].unit_multiplier,
                visual_cell_evidence=row.visual_cell_evidence,
                question_required=question_required,
                reason=reason,
            )
        )
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in _MAPPED_IDS:
            status = TMPage49SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one fixed source row passed the page-49 scoped mapping rule"
        elif item.schema_id in _AMBIGUOUS_IDS:
            status = TMPage49SchemaStatus.AMBIGUOUS_MAPPING.value
            source_ids = tuple(candidate_rows_by_schema[item.schema_id])
            reason = "visible combined/broader row cannot select or split this identity safely"
        elif item.schema_id in _NOT_OBSERVED_IDS:
            status = TMPage49SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "scoped schema child is not separately reported in this PDF note"
        else:
            status = TMPage49SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the two disjoint page-49 schema branches"
        schema_dispositions.append(
            TMPage49SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    accounting = _validation(parsed)
    mapped_values = sum(
        value is not None
        for source in source_dispositions
        if source.status == TMPage49SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        for value in source.values
    )
    result = TMPage49MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=49,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="UNIVERSAL_SCOPED_MAPPING_COMPLETE",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(_MAPPED_IDS),
        ambiguous_schema_count=len(_AMBIGUOUS_IDS),
        not_observed_schema_count=len(_NOT_OBSERVED_IDS),
        not_applicable_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage49SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        ambiguous_source_row_count=sum(
            item.status == TMPage49SourceStatus.AMBIGUOUS_MAPPING.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage49SourceStatus.SOURCE_ONLY_VALIDATION.value
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=mapped_values,
        accounting_check_count=len(accounting),
        accounting_pass_count=sum(check.status == "PASS" for check in accounting),
        accounting_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting
        ),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        accounting_checks=accounting,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "source-scoped page/note/row order",
            "visible row label anchors",
            "row observation status including pixel-backed DASH",
            "visible or report-bound period/unit/scope axes",
            "supplied SchemaGraph hierarchy within two disjoint branches",
        ),
    )
    if (
        result.schema_item_count != TM_PAGE49_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE49_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE49_MAPPED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_PAGE49_AMBIGUOUS_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE49_NOT_OBSERVED_COUNT
        or result.unassessed_schema_count != TM_PAGE49_UNASSESSED_COUNT
        or result.source_row_count != TM_PAGE49_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE49_MAPPED_SOURCE_COUNT
        or result.ambiguous_source_row_count != TM_PAGE49_AMBIGUOUS_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE49_SOURCE_ONLY_COUNT
        or result.source_question_row_count != TM_PAGE49_QUESTION_SOURCE_COUNT
        or result.financial_slot_count != TM_PAGE49_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE49_VALUE_COUNT
        or result.dash_count != TM_PAGE49_DASH_COUNT
        or result.mapped_value_count != TM_PAGE49_MAPPED_VALUE_COUNT
        or result.accounting_check_count != TM_PAGE49_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE49_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE49_ACCOUNTING_NOT_TESTABLE_COUNT
    ):
        raise TMPage49MappingError("TM page-49 result denominator drifted")
    return result


__all__ = [
    "TMPage49MappingError",
    "TMPage49MappingPolicy",
    "TMPage49MappingResult",
    "TMPage49SchemaStatus",
    "TMPage49SourceStatus",
    "load_tm_page49_mapping_policy",
    "reconcile_tm_page49_items",
]
