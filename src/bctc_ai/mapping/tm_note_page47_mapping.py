"""Source-scoped item mapping for the three KQKD notes on MBB TM page 47."""

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
from bctc_ai.tables.tm_note_page47 import ParsedTMPage47

TM_PAGE47_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page47-v1.yaml")
TM_PAGE47_SCHEMA_TOTAL = 1_701
TM_PAGE47_RECONCILED_SCHEMA_COUNT = 48
TM_PAGE47_MAPPED_SCHEMA_COUNT = 21
TM_PAGE47_AMBIGUOUS_SCHEMA_COUNT = 0
TM_PAGE47_NOT_OBSERVED_COUNT = 27
TM_PAGE47_UNASSESSED_COUNT = 1_653
TM_PAGE47_SOURCE_ROW_COUNT = 28
TM_PAGE47_MAPPED_SOURCE_COUNT = 21
TM_PAGE47_AMBIGUOUS_SOURCE_COUNT = 0
TM_PAGE47_SOURCE_ONLY_COUNT = 7
TM_PAGE47_QUESTION_SOURCE_COUNT = 0
TM_PAGE47_FINANCIAL_SLOT_COUNT = 42
TM_PAGE47_VALUE_COUNT = 41
TM_PAGE47_DASH_COUNT = 1
TM_PAGE47_MAPPED_VALUE_COUNT = 41
TM_PAGE47_ACCOUNTING_CHECK_COUNT = 14
TM_PAGE47_ACCOUNTING_PASS_COUNT = 13
TM_PAGE47_ACCOUNTING_NOT_TESTABLE_COUNT = 1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = {
    *range(1175, 1198),
    5990,
    1218,
    *range(1229, 1247),
    *range(6026, 6031),
}
_MAPPED_IDS = {
    1175,
    1176,
    1179,
    1182,
    1185,
    1188,
    1189,
    1190,
    1191,
    1193,
    1194,
    1195,
    1196,
    1232,
    1234,
    5990,
    *range(6026, 6031),
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    1177,
    1178,
    1180,
    1181,
    1183,
    1184,
    1186,
    1187,
    1192,
    1197,
    1218,
    1229,
    1230,
    1231,
    1233,
    1235,
    1236,
    1237,
    1238,
    1239,
    1240,
    1241,
    1242,
    1243,
    1244,
    1245,
    1246,
}
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "accounting_equation_result_as_extracted_value",
}


class TMPage47MappingError(ValueError):
    pass


class TMPage47RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class TMPage47SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage47SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"
    SOURCE_ONLY_QUESTION = "SOURCE_ONLY_QUESTION"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


@dataclass(frozen=True)
class TMPage47RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage47RuleDisposition
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage47MappingPolicy:
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
    rows: tuple[TMPage47RowRule, ...]
    ambiguous_schema_ids: tuple[int, ...]
    not_observed_schema_ids: tuple[int, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage47SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage47SourceDisposition:
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
class TMPage47AccountingCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage47MappingResult:
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
    schema_dispositions: tuple[TMPage47SchemaDisposition, ...]
    source_dispositions: tuple[TMPage47SourceDisposition, ...]
    accounting_checks: tuple[TMPage47AccountingCheck, ...]
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
        raise TMPage47MappingError(f"invalid positive TM page-47 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage47MappingError(f"TM page-47 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage47MappingError(f"TM page-47 {field} contains duplicates")
    return result


def load_tm_page47_mapping_policy(path: Path) -> TMPage47MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage47MappingError(f"cannot load TM page-47 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE47_SCOPED_DURATION_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 47
        or payload.get("page_tag") != "page-0047"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage47MappingError("TM page-47 mapping policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage47MappingError("TM page-47 mapping source hashes are invalid")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise TMPage47MappingError("TM page-47 mapping similarity threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE47_SOURCE_ROW_COUNT:
        raise TMPage47MappingError("TM page-47 mapping row denominator drifted")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage47MappingError("TM page-47 mapping row is invalid")
        table_key = record.get("table_key")
        ordinal = record.get("ordinal")
        anchor = record.get("visible_label_anchor")
        row_kind = record.get("expected_row_kind")
        raw_observations = record.get("expected_observations")
        report_norm_id = record.get("report_norm_id")
        if (
            table_key not in {"NET_FX", "NET_SECURITIES", "NET_OTHER"}
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal <= 0
            or (anchor is not None and not isinstance(anchor, str))
            or row_kind not in {"NUMERIC", "LABEL_ONLY"}
            or not isinstance(raw_observations, list)
            or len(raw_observations) != 2
            or any(value not in {"VALUE", "DASH", "BLANK"} for value in raw_observations)
            or (
                report_norm_id is not None
                and (isinstance(report_norm_id, bool) or not isinstance(report_norm_id, int))
            )
        ):
            raise TMPage47MappingError("TM page-47 mapping row fields are invalid")
        try:
            disposition = TMPage47RuleDisposition(record.get("disposition"))
        except ValueError as exc:
            raise TMPage47MappingError("TM page-47 row disposition is invalid") from exc
        candidates = _ids(
            record.get("candidate_report_norm_ids"),
            "candidate ReportNormIds",
            allow_empty=True,
        )
        if disposition is TMPage47RuleDisposition.FIXED:
            if report_norm_id is None or candidates:
                raise TMPage47MappingError("TM page-47 fixed row binding is invalid")
        elif report_norm_id is not None:
            raise TMPage47MappingError("TM page-47 non-fixed row cannot carry a ReportNormId")
        if disposition is TMPage47RuleDisposition.AMBIGUOUS_MAPPING and not candidates:
            raise TMPage47MappingError("TM page-47 ambiguous row has no candidates")
        if disposition is not TMPage47RuleDisposition.AMBIGUOUS_MAPPING and candidates:
            raise TMPage47MappingError("TM page-47 non-ambiguous row has candidates")
        rows.append(
            TMPage47RowRule(
                table_key=table_key,
                ordinal=ordinal,
                visible_label_anchor=(retrieval_key(anchor) if anchor is not None else None),
                expected_row_kind=row_kind,
                expected_observations=tuple(raw_observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
                candidate_report_norm_ids=candidates,
            )
        )
    identities = tuple(rule.identity for rule in rows)
    expected_identities = tuple(
        [("NET_FX", ordinal) for ordinal in range(1, 11)]
        + [("NET_SECURITIES", ordinal) for ordinal in range(1, 14)]
        + [("NET_OTHER", ordinal) for ordinal in range(1, 6)]
    )
    if identities != expected_identities:
        raise TMPage47MappingError("TM page-47 mapping row order drifted")
    ambiguous = _ids(payload.get("ambiguous_schema_ids"), "ambiguous schema IDs", allow_empty=True)
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not-observed schema IDs")
    fixed_ids = {rule.report_norm_id for rule in rows if rule.report_norm_id is not None}
    candidate_ids = {candidate for rule in rows for candidate in rule.candidate_report_norm_ids}
    if (
        fixed_ids != _MAPPED_IDS
        or set(ambiguous) != _AMBIGUOUS_IDS
        or candidate_ids != _AMBIGUOUS_IDS
        or set(not_observed) != _NOT_OBSERVED_IDS
        or fixed_ids | set(ambiguous) | set(not_observed) != _SCOPED_IDS
    ):
        raise TMPage47MappingError("TM page-47 scoped schema partition drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage47MappingError("TM page-47 forbidden mapping inputs drifted")
    scoped_ids = _ids(payload.get("scoped_schema_ids"), "scoped schema IDs")
    if set(scoped_ids) != _SCOPED_IDS:
        raise TMPage47MappingError("TM page-47 scoped schema IDs drifted")
    return TMPage47MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=47,
        page_tag="page-0047",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        schema_total=_positive_int(payload, "schema_total"),
        scoped_schema_ids=scoped_ids,
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


def _dash_evidence_hash(parsed: ParsedTMPage47) -> str:
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


def _value(parsed: ParsedTMPage47, table_key: str, ordinal: int, axis: int) -> Decimal:
    row = next(row for row in parsed.rows if row.table_key == table_key and row.ordinal == ordinal)
    value = row.row.cells[axis].value
    if value is None:
        raise TMPage47MappingError("TM page-47 accounting validation received a non-value cell")
    return value


def _validation(parsed: ParsedTMPage47) -> tuple[TMPage47AccountingCheck, ...]:
    equations = (
        ("NET_FX_INCOME_TOTAL", "NET_FX", (3, 4), 5),
        ("NET_FX_EXPENSE_TOTAL", "NET_FX", (7, 8), 9),
        ("NET_FX_NET", "NET_FX", (5, 9), 10),
        ("NET_SECURITIES_TRADING_TOTAL", "NET_SECURITIES", (3, 4, 5), 6),
        ("NET_SECURITIES_COMBINED_TOTAL", "NET_SECURITIES", (6, 12), 13),
        ("NET_OTHER_TOTAL", "NET_OTHER", (2, 3, 4), 5),
    )
    checks = []
    for check_id, table_key, components, total in equations:
        table = next(table for table in parsed.tables if table.table_key == table_key)
        for axis_index, axis in enumerate(table.axes):
            expected = sum(
                (_value(parsed, table_key, ordinal, axis_index) for ordinal in components),
                Decimal(0),
            )
            observed = _value(parsed, table_key, total, axis_index)
            residual = observed - expected
            checks.append(
                TMPage47AccountingCheck(
                    check_id=check_id,
                    axis_role=axis.current_or_comparative,
                    status="PASS" if residual == 0 else "FAIL",
                    expected_value=expected,
                    observed_value=observed,
                    residual=residual,
                    reason="visible VALUE cells combined without blank/dash coercion",
                )
            )
    securities = next(table for table in parsed.tables if table.table_key == "NET_SECURITIES")
    mixed = securities.rows[10]
    for axis_index, axis in enumerate(securities.axes):
        if mixed.row.cells[axis_index].observation is ObservationKind.DASH:
            checks.append(
                TMPage47AccountingCheck(
                    check_id="NET_SECURITIES_INVESTMENT_TOTAL",
                    axis_role=axis.current_or_comparative,
                    status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                    expected_value=None,
                    observed_value=_value(parsed, "NET_SECURITIES", 12, axis_index),
                    residual=None,
                    reason="visible DASH is an observation status and cannot be coerced to zero",
                )
            )
            continue
        expected = sum(
            (_value(parsed, "NET_SECURITIES", ordinal, axis_index) for ordinal in (8, 9, 10, 11)),
            Decimal(0),
        )
        observed = _value(parsed, "NET_SECURITIES", 12, axis_index)
        residual = observed - expected
        checks.append(
            TMPage47AccountingCheck(
                check_id="NET_SECURITIES_INVESTMENT_TOTAL",
                axis_role=axis.current_or_comparative,
                status="PASS" if residual == 0 else "FAIL",
                expected_value=expected,
                observed_value=observed,
                residual=residual,
                reason="visible VALUE cells combined without blank/dash coercion",
            )
        )
    return tuple(checks)


def reconcile_tm_page47_items(
    parsed: ParsedTMPage47,
    *,
    schema: list[SchemaItem],
    policy: TMPage47MappingPolicy,
    source_pdf_path: Path,
) -> TMPage47MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage47MappingError("TM page-47 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage47MappingError("TM page-47 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE47_SCHEMA_TOTAL:
        raise TMPage47MappingError("TM page-47 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not _SCOPED_IDS <= set(schema_by_id):
        raise TMPage47MappingError("TM page-47 scoped ReportNormIds are absent")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage47MappingError("TM page-47 parsed row order drifted from policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage47MappingError(f"TM page-47 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage47MappingError(f"TM page-47 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage47MappingError(f"TM page-47 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage47RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            question_required = False
            reason = "fixed page-47 note/section hierarchy and visible-label rule passed"
        elif rule.disposition is TMPage47RuleDisposition.SOURCE_ONLY_VALIDATION:
            status = TMPage47SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            question_required = False
            reason = "visible structural duplicate retained as source provenance without export"
        elif rule.disposition is TMPage47RuleDisposition.SOURCE_ONLY_QUESTION:
            status = TMPage47SourceStatus.SOURCE_ONLY_QUESTION.value
            canonical = None
            question_required = True
            reason = "visible source row has no sufficiently specific supplied schema identity"
        else:
            status = TMPage47SourceStatus.AMBIGUOUS_MAPPING.value
            canonical = None
            question_required = True
            reason = "visible source row cannot be split or aggregated across candidate identities safely"
        source_dispositions.append(
            TMPage47SourceDisposition(
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
                unit=parsed.axes[0].canonical_unit,
                unit_multiplier=parsed.axes[0].unit_multiplier,
                visual_cell_evidence=row.visual_cell_evidence,
                question_required=question_required,
                reason=reason,
            )
        )
    accounting = _validation(parsed)
    if (
        len(accounting) != TM_PAGE47_ACCOUNTING_CHECK_COUNT
        or sum(check.status == "PASS" for check in accounting) != TM_PAGE47_ACCOUNTING_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in accounting)
        != TM_PAGE47_ACCOUNTING_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in accounting)
    ):
        raise TMPage47MappingError("TM page-47 accounting validation failed")
    ambiguous = set(policy.ambiguous_schema_ids)
    not_observed = set(policy.not_observed_schema_ids)
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage47SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one fixed page-47 source row passed source-scoped mapping"
        elif item.schema_id in ambiguous:
            status = TMPage47SchemaStatus.AMBIGUOUS_MAPPING.value
            source_ids = tuple(
                source.row_id
                for source in source_dispositions
                if item.schema_id in source.candidate_report_norm_ids
            )
            reason = "one or more visible rows are compatible but mapping/splitting is unresolved"
        elif item.schema_id in not_observed:
            status = TMPage47SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to the fully assessed page-47 scope but was not visible"
        else:
            status = TMPage47SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the exact page-47 schema scope"
        schema_dispositions.append(
            TMPage47SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    result = TMPage47MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=47,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE47_UNIVERSAL_DURATION_MAPPING",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_rows_by_schema),
        ambiguous_schema_count=len(ambiguous),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        ambiguous_source_row_count=sum(
            item.status == TMPage47SourceStatus.AMBIGUOUS_MAPPING.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status
            in {
                TMPage47SourceStatus.SOURCE_ONLY_VALIDATION.value,
                TMPage47SourceStatus.SOURCE_ONLY_QUESTION.value,
            }
            for item in source_dispositions
        ),
        source_question_row_count=sum(item.question_required for item in source_dispositions),
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=sum(
            observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for item in source_dispositions
            if item.status == TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for observation in item.observations
        ),
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
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE47_NOTE_SECTION_AND_LOCAL_ROW_ORDER",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
        ),
    )
    return validate_tm_page47_mapping_result(result)


def validate_tm_page47_mapping_result(
    result: TMPage47MappingResult,
) -> TMPage47MappingResult:
    if (
        result.schema_item_count != TM_PAGE47_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE47_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE47_MAPPED_SCHEMA_COUNT
        or result.ambiguous_schema_count != TM_PAGE47_AMBIGUOUS_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE47_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE47_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != TM_PAGE47_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE47_MAPPED_SOURCE_COUNT
        or result.ambiguous_source_row_count != TM_PAGE47_AMBIGUOUS_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE47_SOURCE_ONLY_COUNT
        or result.source_question_row_count != TM_PAGE47_QUESTION_SOURCE_COUNT
        or result.financial_slot_count != TM_PAGE47_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE47_VALUE_COUNT
        or result.dash_count != TM_PAGE47_DASH_COUNT
        or result.mapped_value_count != TM_PAGE47_MAPPED_VALUE_COUNT
        or result.accounting_check_count != TM_PAGE47_ACCOUNTING_CHECK_COUNT
        or result.accounting_pass_count != TM_PAGE47_ACCOUNTING_PASS_COUNT
        or result.accounting_not_testable_count != TM_PAGE47_ACCOUNTING_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage47MappingError("TM page-47 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.ambiguous_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage47MappingError("TM page-47 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage47SchemaStatus)
    }
    if (
        by_status[TMPage47SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage47SchemaStatus.AMBIGUOUS_MAPPING.value] != _AMBIGUOUS_IDS
        or by_status[TMPage47SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage47MappingError("TM page-47 exact schema partition drifted")
    dash_rows = [
        item for item in result.source_dispositions if item.observations == ("DASH", "VALUE")
    ]
    if (
        len(dash_rows) != 1
        or dash_rows[0].status != TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        or dash_rows[0].report_norm_id != 6028
        or dash_rows[0].candidate_report_norm_ids
        or dash_rows[0].visual_cell_evidence[0] is None
        or dash_rows[0].visual_cell_evidence[1] is not None
        or dash_rows[0].values != (None, Decimal(20_861))
    ):
        raise TMPage47MappingError("TM page-47 mapped mixed DASH/VALUE status lost pixel evidence")
    return result


__all__ = [
    "TM_PAGE47_POLICY_RELATIVE_PATH",
    "TMPage47AccountingCheck",
    "TMPage47MappingError",
    "TMPage47MappingPolicy",
    "TMPage47MappingResult",
    "TMPage47SchemaDisposition",
    "TMPage47SchemaStatus",
    "TMPage47SourceDisposition",
    "TMPage47SourceStatus",
    "load_tm_page47_mapping_policy",
    "reconcile_tm_page47_items",
    "validate_tm_page47_mapping_result",
]
