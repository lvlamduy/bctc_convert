"""Source-scoped ReportNormId reconciliation for MBB TM page 48."""

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
from bctc_ai.tables.tm_note_page48 import ParsedTMPage48

TM_PAGE48_POLICY_RELATIVE_PATH = Path("config/mapping/tm-note-page48-v1.yaml")
TM_PAGE48_SCHEMA_TOTAL = 1_717
TM_PAGE48_RECONCILED_SCHEMA_COUNT = 22
TM_PAGE48_MAPPED_SCHEMA_COUNT = 9
TM_PAGE48_NOT_OBSERVED_COUNT = 13
TM_PAGE48_UNASSESSED_COUNT = 1_695
TM_PAGE48_SOURCE_ROW_COUNT = 13
TM_PAGE48_MAPPED_SOURCE_COUNT = 9
TM_PAGE48_SOURCE_ONLY_COUNT = 4
TM_PAGE48_FINANCIAL_SLOT_COUNT = 20
TM_PAGE48_VALUE_COUNT = 19
TM_PAGE48_DASH_COUNT = 1
TM_PAGE48_MAPPED_VALUE_COUNT = 17
TM_PAGE48_AUXILIARY_ROW_COUNT = 11
TM_PAGE48_NARRATIVE_QUANTITY_COUNT = 2
TM_PAGE48_VALIDATION_CHECK_COUNT = 6
TM_PAGE48_VALIDATION_PASS_COUNT = 5
TM_PAGE48_VALIDATION_NOT_TESTABLE_COUNT = 1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCOPED_IDS = {*range(1198, 1218), 1219, 1220}
_MAPPED_IDS = {1198, 1205, 1206, 1207, 1212, 1213, 1214, 1217, 1220}
_NOT_OBSERVED_IDS = {1199, 1200, 1201, 1202, 1203, 1204, 1208, 1209, 1210, 1211, 1215, 1216, 1219}
_EXTERNAL_OWNER = (1218, "PAGE47_AMBIGUOUS_LONG_TERM_INVESTMENT_PROVISION")
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text",
    "numeric_cell_value_as_item_selector",
    "numeric_value_magnitude",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equation_result_as_item_selector",
    "auxiliary_variance_as_schema_value",
    "narrative_quantity_as_schema_value",
    "externally_owned_schema_id_as_page48_status",
}


class TMPage48MappingError(ValueError):
    pass


class TMPage48RuleDisposition(StrEnum):
    FIXED = "FIXED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


class TMPage48SchemaStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    UNASSESSED = "UNASSESSED"


class TMPage48SourceStatus(StrEnum):
    MAPPED_AUTOMATIC_SCOPED = "MAPPED_AUTOMATIC_SCOPED"
    SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"


@dataclass(frozen=True)
class TMPage48RowRule:
    table_key: str
    ordinal: int
    visible_label_anchor: str | None
    expected_row_kind: str
    expected_observations: tuple[str, ...]
    disposition: TMPage48RuleDisposition
    report_norm_id: int | None

    @property
    def identity(self) -> tuple[str, int]:
        return self.table_key, self.ordinal


@dataclass(frozen=True)
class TMPage48ExternalOwner:
    report_norm_id: int
    owner: str
    reason: str


@dataclass(frozen=True)
class TMPage48MappingPolicy:
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
    rows: tuple[TMPage48RowRule, ...]
    not_observed_schema_ids: tuple[int, ...]
    external_owners: tuple[TMPage48ExternalOwner, ...]
    forbidden_mapping_inputs: tuple[str, ...]
    policy_sha256: str


@dataclass(frozen=True)
class TMPage48SchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TMPage48SourceDisposition:
    row_id: str
    table_key: str
    ordinal: int
    visible_label: str
    row_kind: str
    source_role: str
    status: str
    report_norm_id: int | None
    canonical_name: str | None
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
class TMPage48ValidationCheck:
    check_id: str
    axis_role: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal
    residual: Decimal | None
    reason: str


@dataclass(frozen=True)
class TMPage48MappingResult:
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
    not_observed_schema_count: int
    not_applicable_schema_count: int
    ambiguous_schema_count: int
    unassessed_schema_count: int
    fully_verified_schema_count: int
    externally_owned_schema_ids: tuple[int, ...]
    source_row_count: int
    mapped_source_row_count: int
    source_only_row_count: int
    source_question_row_count: int
    ambiguous_source_row_count: int
    financial_slot_count: int
    extracted_value_count: int
    dash_count: int
    mapped_value_count: int
    auxiliary_source_row_count: int
    auxiliary_value_count: int
    narrative_quantity_count: int
    validation_check_count: int
    validation_pass_count: int
    validation_not_testable_count: int
    schema_dispositions: tuple[TMPage48SchemaDisposition, ...]
    source_dispositions: tuple[TMPage48SourceDisposition, ...]
    validation_checks: tuple[TMPage48ValidationCheck, ...]
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
        raise TMPage48MappingError(f"invalid positive TM page-48 field: {field}")
    return value


def _ids(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[int, ...]:
    if (
        not isinstance(payload, list)
        or (not payload and not allow_empty)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload)
    ):
        raise TMPage48MappingError(f"TM page-48 {field} is invalid")
    result = tuple(payload)
    if len(set(result)) != len(result):
        raise TMPage48MappingError(f"TM page-48 {field} contains duplicates")
    return result


def load_tm_page48_mapping_policy(path: Path) -> TMPage48MappingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMPage48MappingError(f"cannot load TM page-48 mapping policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE48_SCOPED_MAPPING_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 48
        or payload.get("page_tag") != "page-0048"
        or payload.get("report_scope") != "CONSOLIDATED"
    ):
        raise TMPage48MappingError("TM page-48 mapping identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in ("source_pdf_sha256", "source_render_sha256", "source_ocr_sha256")
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMPage48MappingError("TM page-48 mapping hashes are invalid")
    schema_total = _positive_int(payload, "schema_total")
    scoped = _ids(payload.get("scoped_schema_ids"), "scoped_schema_ids")
    not_observed = _ids(payload.get("not_observed_schema_ids"), "not_observed_schema_ids")
    if set(scoped) != _SCOPED_IDS or set(not_observed) != _NOT_OBSERVED_IDS:
        raise TMPage48MappingError("TM page-48 exact schema scope drifted")
    threshold = payload.get("minimum_visible_label_similarity")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise TMPage48MappingError("TM page-48 label threshold is invalid")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != TM_PAGE48_SOURCE_ROW_COUNT:
        raise TMPage48MappingError("TM page-48 row rules are incomplete")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMPage48MappingError("TM page-48 row rule is invalid")
        try:
            disposition = TMPage48RuleDisposition(str(record.get("disposition")))
        except ValueError as exc:
            raise TMPage48MappingError("TM page-48 disposition is invalid") from exc
        observations = record.get("expected_observations")
        if (
            not isinstance(observations, list)
            or len(observations) != 2
            or any(value not in {item.value for item in ObservationKind} for value in observations)
        ):
            raise TMPage48MappingError("TM page-48 expected observations are invalid")
        report_norm_id = record.get("report_norm_id")
        if disposition is TMPage48RuleDisposition.FIXED:
            if isinstance(report_norm_id, bool) or not isinstance(report_norm_id, int):
                raise TMPage48MappingError("TM page-48 fixed rule lacks ReportNormId")
        elif report_norm_id is not None:
            raise TMPage48MappingError("TM page-48 source-only rule carries ReportNormId")
        anchor = record.get("visible_label_anchor")
        if anchor is not None and (not isinstance(anchor, str) or not retrieval_key(anchor)):
            raise TMPage48MappingError("TM page-48 visible label anchor is invalid")
        rows.append(
            TMPage48RowRule(
                table_key=str(record.get("table_key", "")),
                ordinal=_positive_int(record, "ordinal"),
                visible_label_anchor=retrieval_key(anchor) if anchor is not None else None,
                expected_row_kind=str(record.get("expected_row_kind", "")),
                expected_observations=tuple(str(value) for value in observations),
                disposition=disposition,
                report_norm_id=report_norm_id,
            )
        )
    if len({row.identity for row in rows}) != len(rows):
        raise TMPage48MappingError("TM page-48 row identities are duplicated")
    mapped_ids = {row.report_norm_id for row in rows if row.report_norm_id is not None}
    if mapped_ids != _MAPPED_IDS or mapped_ids | set(not_observed) != set(scoped):
        raise TMPage48MappingError("TM page-48 mapped/not-observed partition drifted")
    raw_external = payload.get("external_owners")
    if not isinstance(raw_external, list) or len(raw_external) != 1:
        raise TMPage48MappingError("TM page-48 external owner assertion is absent")
    external = raw_external[0]
    if not isinstance(external, dict):
        raise TMPage48MappingError("TM page-48 external owner record is invalid")
    owner = TMPage48ExternalOwner(
        report_norm_id=_positive_int(external, "report_norm_id"),
        owner=str(external.get("owner", "")),
        reason=str(external.get("reason", "")),
    )
    if (
        (owner.report_norm_id, owner.owner) != _EXTERNAL_OWNER
        or not owner.reason
        or owner.report_norm_id in set(scoped)
    ):
        raise TMPage48MappingError("TM page-48 external owner assertion drifted")
    forbidden = payload.get("forbidden_mapping_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMPage48MappingError("TM page-48 forbidden mapping inputs drifted")
    return TMPage48MappingPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=48,
        page_tag="page-0048",
        report_scope="CONSOLIDATED",
        mapping_authority_scope=str(payload.get("mapping_authority_scope", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        schema_total=schema_total,
        scoped_schema_ids=scoped,
        minimum_visible_label_similarity=float(threshold),
        rows=tuple(rows),
        not_observed_schema_ids=not_observed,
        external_owners=(owner,),
        forbidden_mapping_inputs=tuple(str(value) for value in forbidden),
        policy_sha256=sha256_file(path),
    )


def _similarity(visible: str, anchor: str) -> float:
    left = retrieval_key(visible)
    if anchor in left:
        return 1.0
    return ratio(left, anchor) / 100.0


def _schema_hash(items: tuple[SchemaItem, ...]) -> str:
    payload = [(item.schema_id, item.display_order, item.canonical_name) for item in items]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dash_evidence_hash(parsed: ParsedTMPage48) -> str:
    payload = [
        asdict(evidence)
        for row in parsed.rows
        for evidence in row.visual_cell_evidence
        if evidence is not None
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _row(parsed: ParsedTMPage48, table_key: str, ordinal: int):
    return next(row for row in parsed.rows if (row.table_key, row.ordinal) == (table_key, ordinal))


def _value(parsed: ParsedTMPage48, table_key: str, ordinal: int, axis: int) -> Decimal:
    value = _row(parsed, table_key, ordinal).row.cells[axis].value
    if value is None:
        raise TMPage48MappingError(f"TM page-48 expected a finite value: {table_key}/{ordinal}")
    return value


def _validation(parsed: ParsedTMPage48) -> tuple[TMPage48ValidationCheck, ...]:
    checks = []
    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        detail = _value(parsed, "CONTRIBUTION_INCOME", 2, axis)
        total = _value(parsed, "CONTRIBUTION_INCOME", 3, axis)
        checks.append(
            TMPage48ValidationCheck(
                check_id=f"CONTRIBUTION_DUPLICATE_{role}",
                axis_role=role,
                status="PASS" if detail == total else "FAIL",
                expected_value=detail,
                observed_value=total,
                residual=total - detail,
                reason="visible detail equals the independently printed terminal total",
            )
        )
    component_ordinals = (2, 3, 4, 7, 8, 9)
    for axis, role in enumerate(("CURRENT", "COMPARATIVE")):
        total = _value(parsed, "OPERATING_EXPENSE", 10, axis)
        cells = [
            _row(parsed, "OPERATING_EXPENSE", ordinal).row.cells[axis]
            for ordinal in component_ordinals
        ]
        if any(cell.observation is ObservationKind.DASH for cell in cells):
            checks.append(
                TMPage48ValidationCheck(
                    check_id=f"OPERATING_EXPENSE_SUM_{role}",
                    axis_role=role,
                    status="NOT_TESTABLE_DASH_IS_NOT_ZERO",
                    expected_value=None,
                    observed_value=total,
                    residual=None,
                    reason="a visible DASH is preserved as unknown/not stated and is not coerced to zero",
                )
            )
        else:
            expected = sum((cell.value for cell in cells if cell.value is not None), Decimal(0))
            checks.append(
                TMPage48ValidationCheck(
                    check_id=f"OPERATING_EXPENSE_SUM_{role}",
                    axis_role=role,
                    status="PASS" if expected == total else "FAIL",
                    expected_value=expected,
                    observed_value=total,
                    residual=total - expected,
                    reason="visible operating-expense components sum to the terminal total; memo depreciation excluded",
                )
            )
    drivers = [row.value for row in parsed.auxiliary_rows if row.source_role == "DRIVER"]
    auxiliary_total = next(row.value for row in parsed.auxiliary_rows if row.source_role == "TOTAL")
    expected_auxiliary = sum(drivers, Decimal(0))
    checks.append(
        TMPage48ValidationCheck(
            check_id="AUXILIARY_VARIANCE_DRIVER_SUM",
            axis_role="CURRENT_MINUS_COMPARATIVE",
            status="PASS" if expected_auxiliary == auxiliary_total else "FAIL",
            expected_value=expected_auxiliary,
            observed_value=auxiliary_total,
            residual=auxiliary_total - expected_auxiliary,
            reason="ten visible variance drivers sum to the separately printed auxiliary total",
        )
    )
    narrative_amount = next(
        quantity.value
        for quantity in parsed.narrative_quantities
        if quantity.semantic_role == "DISCLOSED_PROFIT_AFTER_TAX_CHANGE"
    )
    checks.append(
        TMPage48ValidationCheck(
            check_id="AUXILIARY_TOTAL_EQUALS_NARRATIVE_CHANGE",
            axis_role="CURRENT_MINUS_COMPARATIVE",
            status="PASS" if narrative_amount == auxiliary_total else "FAIL",
            expected_value=narrative_amount,
            observed_value=auxiliary_total,
            residual=auxiliary_total - narrative_amount,
            reason="auxiliary total agrees with the visible narrative change amount",
        )
    )
    return tuple(checks)


def reconcile_tm_page48_items(
    parsed: ParsedTMPage48,
    *,
    schema: list[SchemaItem],
    policy: TMPage48MappingPolicy,
    source_pdf_path: Path,
) -> TMPage48MappingResult:
    if (
        parsed.page_tag != policy.page_tag
        or parsed.scope != policy.report_scope
        or parsed.mapping_authority
        or parsed.source_pdf_sha256 != policy.source_pdf_sha256
        or parsed.source_render_sha256 != policy.source_render_sha256
        or parsed.source_sha256 != policy.source_ocr_sha256
    ):
        raise TMPage48MappingError("TM page-48 parser/mapping source identity drifted")
    if sha256_file(source_pdf_path) != policy.source_pdf_sha256:
        raise TMPage48MappingError("TM page-48 source PDF hash drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    if len(tm_schema) != policy.schema_total or len(tm_schema) != TM_PAGE48_SCHEMA_TOTAL:
        raise TMPage48MappingError("TM page-48 schema denominator drifted")
    schema_by_id = {item.schema_id: item for item in tm_schema}
    if not (_SCOPED_IDS | {_EXTERNAL_OWNER[0]}) <= set(schema_by_id):
        raise TMPage48MappingError("TM page-48 scoped/external ReportNormIds are absent")
    parsed_by_identity = {(row.table_key, row.ordinal): row for row in parsed.rows}
    if tuple(parsed_by_identity) != tuple(rule.identity for rule in policy.rows):
        raise TMPage48MappingError("TM page-48 parsed row order drifted from policy")
    source_dispositions = []
    source_rows_by_schema: dict[int, list[str]] = {}
    for rule in policy.rows:
        row = parsed_by_identity[rule.identity]
        observations = tuple(cell.observation.value for cell in row.row.cells)
        if (
            row.row_kind.value != rule.expected_row_kind
            or observations != rule.expected_observations
        ):
            raise TMPage48MappingError(f"TM page-48 row status drifted: {row.row_id}")
        if rule.visible_label_anchor is None:
            if row.row.label:
                raise TMPage48MappingError(f"TM page-48 expected unlabeled total: {row.row_id}")
            similarity = None
        else:
            similarity = _similarity(row.row.label, rule.visible_label_anchor)
            if similarity < policy.minimum_visible_label_similarity:
                raise TMPage48MappingError(f"TM page-48 label anchor failed: {row.row_id}")
        if rule.disposition is TMPage48RuleDisposition.FIXED:
            assert rule.report_norm_id is not None
            item = schema_by_id[rule.report_norm_id]
            status = TMPage48SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            canonical = item.canonical_name
            source_rows_by_schema.setdefault(item.schema_id, []).append(row.row_id)
            reason = "fixed page-48 note hierarchy, row order and visible-label rule passed"
        else:
            status = TMPage48SourceStatus.SOURCE_ONLY_VALIDATION.value
            canonical = None
            reason = "visible structural or duplicate row retained as provenance without export"
        source_dispositions.append(
            TMPage48SourceDisposition(
                row_id=row.row_id,
                table_key=row.table_key,
                ordinal=row.ordinal,
                visible_label=row.row.label,
                row_kind=row.row_kind.value,
                source_role=row.source_role,
                status=status,
                report_norm_id=rule.report_norm_id,
                canonical_name=canonical,
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
                question_required=False,
                reason=reason,
            )
        )
    checks = _validation(parsed)
    if (
        len(checks) != TM_PAGE48_VALIDATION_CHECK_COUNT
        or sum(check.status == "PASS" for check in checks) != TM_PAGE48_VALIDATION_PASS_COUNT
        or sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks)
        != TM_PAGE48_VALIDATION_NOT_TESTABLE_COUNT
        or any(check.status == "FAIL" for check in checks)
    ):
        raise TMPage48MappingError("TM page-48 validation failed")
    not_observed = set(policy.not_observed_schema_ids)
    external_by_id = {owner.report_norm_id: owner for owner in policy.external_owners}
    schema_dispositions = []
    for item in tm_schema:
        if item.schema_id in source_rows_by_schema:
            status = TMPage48SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
            source_ids = tuple(source_rows_by_schema[item.schema_id])
            reason = "one fixed page-48 source row passed source-scoped mapping"
        elif item.schema_id in not_observed:
            status = TMPage48SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            source_ids = ()
            reason = "item belongs to the fully assessed page-48 scope but was not visible"
        elif item.schema_id in external_by_id:
            status = TMPage48SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = (
                f"excluded from page-48 reconciliation; external owner "
                f"{external_by_id[item.schema_id].owner}: {external_by_id[item.schema_id].reason}"
            )
        else:
            status = TMPage48SchemaStatus.UNASSESSED.value
            source_ids = ()
            reason = "outside the exact page-48 schema scope"
        schema_dispositions.append(
            TMPage48SchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                status=status,
                source_row_ids=source_ids,
                reason=reason,
            )
        )
    result = TMPage48MappingResult(
        statement_type="TM",
        document=policy.document,
        page_number=48,
        page_tag=policy.page_tag,
        report_scope=policy.report_scope,
        status="SCOPED_PAGE48_MAPPING_WITH_AUXILIARY_PROVENANCE_AND_NO_OPEN_AMBIGUITIES",
        mapping_authority_scope=policy.mapping_authority_scope,
        mapping_authority_granted=True,
        schema_item_count=len(tm_schema),
        status_reconciled_schema_count=len(_SCOPED_IDS),
        mapped_schema_count=len(source_rows_by_schema),
        not_observed_schema_count=len(not_observed),
        not_applicable_schema_count=0,
        ambiguous_schema_count=0,
        unassessed_schema_count=len(tm_schema) - len(_SCOPED_IDS),
        fully_verified_schema_count=0,
        externally_owned_schema_ids=tuple(external_by_id),
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == TMPage48SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == TMPage48SourceStatus.SOURCE_ONLY_VALIDATION.value
            for item in source_dispositions
        ),
        source_question_row_count=0,
        ambiguous_source_row_count=0,
        financial_slot_count=parsed.financial_slot_count,
        extracted_value_count=parsed.observation_count(ObservationKind.VALUE),
        dash_count=parsed.observation_count(ObservationKind.DASH),
        mapped_value_count=sum(
            observation in {ObservationKind.VALUE.value, ObservationKind.ZERO.value}
            for item in source_dispositions
            if item.status == TMPage48SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
            for observation in item.observations
        ),
        auxiliary_source_row_count=len(parsed.auxiliary_rows),
        auxiliary_value_count=len(parsed.auxiliary_rows),
        narrative_quantity_count=len(parsed.narrative_quantities),
        validation_check_count=len(checks),
        validation_pass_count=sum(check.status == "PASS" for check in checks),
        validation_not_testable_count=sum(
            check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in checks
        ),
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        validation_checks=checks,
        source_pdf_sha256=policy.source_pdf_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_ocr_sha256=policy.source_ocr_sha256,
        dash_pixel_evidence_sha256=_dash_evidence_hash(parsed),
        schema_projection_sha256=_schema_hash(tm_schema),
        policy_sha256=policy.policy_sha256,
        mapping_inputs=(
            "SOURCE_VISIBLE_PPOCR_LABELS",
            "VISIBLE_PAGE48_NOTE_SECTION_AND_LOCAL_ROW_ORDER",
            "SOURCE_RENDER_SHA256",
            "CONSTRAINED_PIXEL_DASH_EVIDENCE_FOR_STATUS_ONLY",
            "TM_SCHEMA_ID_NAME_ORDER",
            "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
            "AUXILIARY_VARIANCE_AND_NARRATIVE_AS_PROVENANCE_ONLY",
            "EXTERNAL_PAGE47_OWNER_ASSERTION_FOR_REPORT_NORM_ID_1218",
        ),
    )
    return validate_tm_page48_mapping_result(result)


def validate_tm_page48_mapping_result(result: TMPage48MappingResult) -> TMPage48MappingResult:
    if (
        result.schema_item_count != TM_PAGE48_SCHEMA_TOTAL
        or result.status_reconciled_schema_count != TM_PAGE48_RECONCILED_SCHEMA_COUNT
        or result.mapped_schema_count != TM_PAGE48_MAPPED_SCHEMA_COUNT
        or result.not_observed_schema_count != TM_PAGE48_NOT_OBSERVED_COUNT
        or result.not_applicable_schema_count != 0
        or result.ambiguous_schema_count != 0
        or result.unassessed_schema_count != TM_PAGE48_UNASSESSED_COUNT
        or result.fully_verified_schema_count != 0
        or result.externally_owned_schema_ids != (_EXTERNAL_OWNER[0],)
        or result.source_row_count != TM_PAGE48_SOURCE_ROW_COUNT
        or result.mapped_source_row_count != TM_PAGE48_MAPPED_SOURCE_COUNT
        or result.source_only_row_count != TM_PAGE48_SOURCE_ONLY_COUNT
        or result.source_question_row_count != 0
        or result.ambiguous_source_row_count != 0
        or result.financial_slot_count != TM_PAGE48_FINANCIAL_SLOT_COUNT
        or result.extracted_value_count != TM_PAGE48_VALUE_COUNT
        or result.dash_count != TM_PAGE48_DASH_COUNT
        or result.mapped_value_count != TM_PAGE48_MAPPED_VALUE_COUNT
        or result.auxiliary_source_row_count != TM_PAGE48_AUXILIARY_ROW_COUNT
        or result.auxiliary_value_count != TM_PAGE48_AUXILIARY_ROW_COUNT
        or result.narrative_quantity_count != TM_PAGE48_NARRATIVE_QUANTITY_COUNT
        or result.validation_check_count != TM_PAGE48_VALIDATION_CHECK_COUNT
        or result.validation_pass_count != TM_PAGE48_VALIDATION_PASS_COUNT
        or result.validation_not_testable_count != TM_PAGE48_VALIDATION_NOT_TESTABLE_COUNT
        or not result.mapping_authority_granted
    ):
        raise TMPage48MappingError("TM page-48 mapping result denominator drifted")
    if (
        result.mapped_schema_count
        + result.not_observed_schema_count
        + result.unassessed_schema_count
        != result.schema_item_count
    ):
        raise TMPage48MappingError("TM page-48 schema statuses do not reconcile")
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage48SchemaStatus)
    }
    if (
        by_status[TMPage48SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] != _MAPPED_IDS
        or by_status[TMPage48SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] != _NOT_OBSERVED_IDS
    ):
        raise TMPage48MappingError("TM page-48 exact schema partition drifted")
    external = next(
        item for item in result.schema_dispositions if item.report_norm_id == _EXTERNAL_OWNER[0]
    )
    if (
        external.status != TMPage48SchemaStatus.UNASSESSED.value
        or _EXTERNAL_OWNER[1] not in external.reason
    ):
        raise TMPage48MappingError("TM page-48 external page-47 owner assertion was lost")
    dash_rows = [
        item for item in result.source_dispositions if item.observations == ("VALUE", "DASH")
    ]
    if (
        len(dash_rows) != 1
        or dash_rows[0].report_norm_id != 1220
        or dash_rows[0].values != (Decimal(-2_033), None)
        or dash_rows[0].visual_cell_evidence[0] is not None
        or dash_rows[0].visual_cell_evidence[1] is None
    ):
        raise TMPage48MappingError("TM page-48 mixed VALUE/DASH evidence drifted")
    return result


__all__ = [
    "TM_PAGE48_POLICY_RELATIVE_PATH",
    "TMPage48MappingError",
    "TMPage48MappingPolicy",
    "TMPage48MappingResult",
    "TMPage48SchemaDisposition",
    "TMPage48SchemaStatus",
    "TMPage48SourceDisposition",
    "TMPage48SourceStatus",
    "TMPage48ValidationCheck",
    "load_tm_page48_mapping_policy",
    "reconcile_tm_page48_items",
    "validate_tm_page48_mapping_result",
]
