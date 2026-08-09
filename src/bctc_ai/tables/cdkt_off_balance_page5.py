from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping

CDKT_OFF_BALANCE_PAGE5_POLICY_RELATIVE_PATH = Path("config/tables/cdkt-off-balance-page5-v1.yaml")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_EXPECTED_SCHEMA_IDS = tuple(range(6038, 6049))


class CDKTOffBalancePage5Error(ValueError):
    """Raised when immutable page-5 evidence or its reconstruction drifts."""


@dataclass(frozen=True)
class CDKTOffBalanceAxis:
    ordinal: int
    role: str
    period_end: date
    header_line_index: int
    unit_line_index: int


@dataclass(frozen=True)
class CDKTOffBalanceRowRule:
    report_norm_id: int
    row_id: str
    row_role: str
    visible_label: str
    label_line_index: int
    value_line_indices: tuple[int, ...]


@dataclass(frozen=True)
class CDKTOffBalanceAccountingCheck:
    target_report_norm_id: int
    component_report_norm_ids: tuple[int, ...]
    operator: str


@dataclass(frozen=True)
class CDKTOffBalancePage5Policy:
    source_path: Path
    policy_sha256: str
    page_number: int
    scope: str
    source_pdf_path: Path
    source_pdf_sha256: str
    source_ocr_path: Path
    source_ocr_sha256: str
    source_render_path: Path
    source_render_sha256: str
    minimum_label_similarity: float
    minimum_label_score: float
    minimum_numeric_score: float
    unit: str
    unit_multiplier: int
    axes: tuple[CDKTOffBalanceAxis, ...]
    rows: tuple[CDKTOffBalanceRowRule, ...]
    accounting_checks: tuple[CDKTOffBalanceAccountingCheck, ...]


@dataclass(frozen=True)
class CDKTOffBalanceCell:
    axis_ordinal: int
    period_role: str
    period_end: date
    observation: ObservationKind
    raw_text: str
    displayed_value: int | None
    canonical_value: int | None
    value_line_index: int | None
    value_bbox: BoundingBox | None
    recognition_score: float | None


@dataclass(frozen=True)
class CDKTOffBalanceRow:
    report_norm_id: int
    row_id: str
    ordinal: int
    row_role: str
    visible_label: str
    ocr_label: str
    label_line_index: int
    label_bbox: BoundingBox
    label_score: float
    label_similarity: float
    cells: tuple[CDKTOffBalanceCell, ...]


@dataclass(frozen=True)
class ParsedCDKTOffBalancePage5:
    page_number: int
    scope: str
    unit: str
    unit_multiplier: int
    source_pdf_path: str
    source_pdf_sha256: str
    source_ocr_path: str
    source_ocr_sha256: str
    source_render_path: str
    source_render_sha256: str
    render_width: int
    render_height: int
    policy_path: str
    policy_sha256: str
    axes: tuple[CDKTOffBalanceAxis, ...]
    rows: tuple[CDKTOffBalanceRow, ...]
    accounting_checks_passed: tuple[str, ...]

    @property
    def source_row_count(self) -> int:
        return len(self.rows)

    @property
    def physical_cell_count(self) -> int:
        return sum(len(row.cells) for row in self.rows)

    @property
    def value_cell_count(self) -> int:
        return sum(
            cell.observation is ObservationKind.VALUE for row in self.rows for cell in row.cells
        )

    @property
    def blank_cell_count(self) -> int:
        return sum(
            cell.observation is ObservationKind.BLANK for row in self.rows for cell in row.cells
        )


@dataclass(frozen=True)
class _OCRLine:
    index: int
    text: str
    bbox: BoundingBox
    score: float


def _required_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} must be a mapping")
    return value


def _required_score(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} must be a score")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} is outside [0,1]")
    return result


def _required_int(payload: dict[str, Any], field: str, *, positive: bool = False) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or (positive and value <= 0):
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} must be an integer")
    return value


def _resolve_evidence_path(project_root: Path, relative: Any, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} path is invalid")
    candidate = (project_root / relative).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} escapes project root") from exc
    if not candidate.is_file():
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} evidence is absent")
    return candidate


def _evidence_binding(payload: dict[str, Any], project_root: Path, field: str) -> tuple[Path, str]:
    record = _required_mapping(payload.get(field), field)
    path = _resolve_evidence_path(project_root, record.get("path"), field)
    digest = record.get("sha256")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} hash is invalid")
    if sha256_file(path) != digest:
        raise CDKTOffBalancePage5Error(f"page-5 policy {field} hash drifted")
    return path, digest


def load_cdkt_off_balance_page5_policy(path: Path, project_root: Path) -> CDKTOffBalancePage5Policy:
    path = Path(path).resolve()
    project_root = Path(project_root).resolve()
    try:
        path.relative_to(project_root)
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise CDKTOffBalancePage5Error("cannot load CDKT off-balance page-5 policy") from exc
    raw = _required_mapping(payload, "root")
    if (
        raw.get("format_version") != 1
        or raw.get("statement_type") != "CDKT"
        or raw.get("section") != "OFF_BALANCE_SHEET"
        or raw.get("page_number") != 5
        or raw.get("scope") != "CONSOLIDATED"
        or raw.get("unit") != "VND"
    ):
        raise CDKTOffBalancePage5Error("page-5 policy identity drifted")
    source_pdf_path, source_pdf_sha256 = _evidence_binding(raw, project_root, "source_pdf")
    source_ocr_path, source_ocr_sha256 = _evidence_binding(raw, project_root, "source_ocr")
    source_render_path, source_render_sha256 = _evidence_binding(raw, project_root, "source_render")
    axes_raw = raw.get("axes")
    rows_raw = raw.get("rows")
    checks_raw = raw.get("accounting_checks")
    if (
        not isinstance(axes_raw, list)
        or not isinstance(rows_raw, list)
        or not isinstance(checks_raw, list)
    ):
        raise CDKTOffBalancePage5Error("page-5 policy row/axis inventory is invalid")
    axes = []
    for ordinal, record in enumerate(axes_raw):
        axis = _required_mapping(record, "axis")
        role = axis.get("role")
        period_end = axis.get("period_end")
        if role not in {"CURRENT", "COMPARATIVE"} or not isinstance(period_end, date):
            raise CDKTOffBalancePage5Error("page-5 policy axis identity is invalid")
        axes.append(
            CDKTOffBalanceAxis(
                ordinal=ordinal,
                role=role,
                period_end=period_end,
                header_line_index=_required_int(axis, "header_line_index"),
                unit_line_index=_required_int(axis, "unit_line_index"),
            )
        )
    if tuple(axis.role for axis in axes) != ("CURRENT", "COMPARATIVE"):
        raise CDKTOffBalancePage5Error("page-5 policy axis order drifted")
    rows = []
    for record in rows_raw:
        row = _required_mapping(record, "row")
        report_norm_id = _required_int(row, "report_norm_id", positive=True)
        row_id = row.get("row_id")
        row_role = row.get("row_role")
        visible_label = row.get("visible_label")
        raw_value_indices = row.get("value_line_indices", [])
        if (
            not isinstance(row_id, str)
            or not row_id
            or row_role not in {"HEADING", "GROUP", "VALUE"}
            or not isinstance(visible_label, str)
            or not retrieval_key(visible_label)
            or not isinstance(raw_value_indices, list)
            or any(
                isinstance(value, bool) or not isinstance(value, int) for value in raw_value_indices
            )
            or (row_role == "VALUE") != (len(raw_value_indices) == len(axes))
        ):
            raise CDKTOffBalancePage5Error("page-5 policy row identity is invalid")
        rows.append(
            CDKTOffBalanceRowRule(
                report_norm_id=report_norm_id,
                row_id=row_id,
                row_role=row_role,
                visible_label=visible_label,
                label_line_index=_required_int(row, "label_line_index"),
                value_line_indices=tuple(raw_value_indices),
            )
        )
    if tuple(row.report_norm_id for row in rows) != _EXPECTED_SCHEMA_IDS or len(
        {row.row_id for row in rows}
    ) != len(rows):
        raise CDKTOffBalancePage5Error("page-5 policy schema row order drifted")
    checks = []
    for record in checks_raw:
        check = _required_mapping(record, "accounting check")
        components = check.get("component_report_norm_ids")
        if (
            check.get("operator") != "SUM"
            or not isinstance(components, list)
            or any(isinstance(value, bool) or not isinstance(value, int) for value in components)
        ):
            raise CDKTOffBalancePage5Error("page-5 accounting check is invalid")
        checks.append(
            CDKTOffBalanceAccountingCheck(
                target_report_norm_id=_required_int(check, "target_report_norm_id", positive=True),
                component_report_norm_ids=tuple(components),
                operator="SUM",
            )
        )
    if checks != [CDKTOffBalanceAccountingCheck(6041, (6042, 6043, 6044, 6045), "SUM")]:
        raise CDKTOffBalancePage5Error("page-5 accounting check inventory drifted")
    return CDKTOffBalancePage5Policy(
        source_path=path,
        policy_sha256=sha256_file(path),
        page_number=5,
        scope="CONSOLIDATED",
        source_pdf_path=source_pdf_path,
        source_pdf_sha256=source_pdf_sha256,
        source_ocr_path=source_ocr_path,
        source_ocr_sha256=source_ocr_sha256,
        source_render_path=source_render_path,
        source_render_sha256=source_render_sha256,
        minimum_label_similarity=_required_score(raw, "minimum_label_similarity"),
        minimum_label_score=_required_score(raw, "minimum_label_score"),
        minimum_numeric_score=_required_score(raw, "minimum_numeric_score"),
        unit="VND",
        unit_multiplier=_required_int(raw, "unit_multiplier", positive=True),
        axes=tuple(axes),
        rows=tuple(rows),
        accounting_checks=tuple(checks),
    )


def _load_ocr_lines(policy: CDKTOffBalancePage5Policy) -> tuple[_OCRLine, ...]:
    try:
        payload = json.loads(policy.source_ocr_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CDKTOffBalancePage5Error("cannot decode CDKT off-balance page-5 OCR") from exc
    if not isinstance(payload, dict):
        raise CDKTOffBalancePage5Error("page-5 OCR root is invalid")
    texts = payload.get("rec_texts")
    boxes = payload.get("rec_boxes")
    scores = payload.get("rec_scores")
    if (
        not isinstance(texts, list)
        or not isinstance(boxes, list)
        or not isinstance(scores, list)
        or not len(texts) == len(boxes) == len(scores)
        or len(texts) < 42
    ):
        raise CDKTOffBalancePage5Error("page-5 OCR line arrays are invalid")
    input_path = payload.get("input_path")
    project_root = policy.source_path.parents[2]
    render_relative = policy.source_render_path.relative_to(project_root)
    input_parts = Path(input_path).parts if isinstance(input_path, str) else ()
    if (
        not input_parts
        or len(input_parts) < len(render_relative.parts)
        or tuple(input_parts[-len(render_relative.parts) :]) != render_relative.parts
    ):
        raise CDKTOffBalancePage5Error("page-5 OCR/render binding drifted")
    lines = []
    for index, (text, box, score) in enumerate(zip(texts, boxes, scores, strict=True)):
        if (
            not isinstance(text, str)
            or not isinstance(box, list)
            or len(box) != 4
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in box)
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or not 0.0 <= float(score) <= 1.0
        ):
            raise CDKTOffBalancePage5Error("page-5 OCR line is malformed")
        lines.append(
            _OCRLine(
                index=index,
                text=text,
                bbox=BoundingBox(*(float(value) for value in box)),
                score=float(score),
            )
        )
    return tuple(lines)


def _validate_render(
    policy: CDKTOffBalancePage5Policy, lines: tuple[_OCRLine, ...]
) -> tuple[int, int]:
    try:
        with Image.open(policy.source_render_path) as image:
            width, height = image.size
            image.verify()
    except Exception as exc:
        raise CDKTOffBalancePage5Error("page-5 source render cannot be decoded") from exc
    if (
        width <= 0
        or height <= 0
        or any(
            line.bbox.x0 < 0 or line.bbox.y0 < 0 or line.bbox.x1 > width or line.bbox.y1 > height
            for line in lines
        )
    ):
        raise CDKTOffBalancePage5Error("page-5 OCR geometry escapes source pixels")
    return width, height


def parse_cdkt_off_balance_page5(
    policy: CDKTOffBalancePage5Policy,
) -> ParsedCDKTOffBalancePage5:
    if not isinstance(policy, CDKTOffBalancePage5Policy):
        raise CDKTOffBalancePage5Error("page-5 policy model is required")
    lines = _load_ocr_lines(policy)
    width, height = _validate_render(policy, lines)
    for axis in policy.axes:
        header = lines[axis.header_line_index]
        unit = lines[axis.unit_line_index]
        if (
            retrieval_key(header.text) != axis.period_end.strftime("%d %m %Y")
            or ratio(retrieval_key(unit.text), "trieu dong") / 100 < 0.75
        ):
            raise CDKTOffBalancePage5Error("page-5 visible period/unit header drifted")
    rows = []
    for ordinal, rule in enumerate(policy.rows):
        label = lines[rule.label_line_index]
        similarity = ratio(retrieval_key(label.text), retrieval_key(rule.visible_label)) / 100
        if label.score < policy.minimum_label_score or similarity < policy.minimum_label_similarity:
            raise CDKTOffBalancePage5Error(
                f"page-5 visible label evidence failed for {rule.report_norm_id}"
            )
        cells = []
        for axis in policy.axes:
            if rule.row_role != "VALUE":
                cells.append(
                    CDKTOffBalanceCell(
                        axis_ordinal=axis.ordinal,
                        period_role=axis.role,
                        period_end=axis.period_end,
                        observation=ObservationKind.BLANK,
                        raw_text="",
                        displayed_value=None,
                        canonical_value=None,
                        value_line_index=None,
                        value_bbox=None,
                        recognition_score=None,
                    )
                )
                continue
            value_line = lines[rule.value_line_indices[axis.ordinal]]
            parsed = parse_financial_number_strict_grouping(value_line.text)
            if (
                value_line.score < policy.minimum_numeric_score
                or parsed.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}
                or parsed.value is None
                or parsed.value != parsed.value.to_integral_value()
            ):
                raise CDKTOffBalancePage5Error(
                    f"page-5 visible numeric evidence failed for {rule.report_norm_id}"
                )
            displayed_value = int(parsed.value)
            cells.append(
                CDKTOffBalanceCell(
                    axis_ordinal=axis.ordinal,
                    period_role=axis.role,
                    period_end=axis.period_end,
                    observation=(
                        ObservationKind.ZERO if displayed_value == 0 else ObservationKind.VALUE
                    ),
                    raw_text=value_line.text,
                    displayed_value=displayed_value,
                    canonical_value=displayed_value * policy.unit_multiplier,
                    value_line_index=value_line.index,
                    value_bbox=value_line.bbox,
                    recognition_score=value_line.score,
                )
            )
        rows.append(
            CDKTOffBalanceRow(
                report_norm_id=rule.report_norm_id,
                row_id=rule.row_id,
                ordinal=ordinal,
                row_role=rule.row_role,
                visible_label=rule.visible_label,
                ocr_label=label.text,
                label_line_index=label.index,
                label_bbox=label.bbox,
                label_score=label.score,
                label_similarity=similarity,
                cells=tuple(cells),
            )
        )
    by_id = {row.report_norm_id: row for row in rows}
    passed_checks = []
    for check in policy.accounting_checks:
        for axis in policy.axes:
            target = by_id[check.target_report_norm_id].cells[axis.ordinal].displayed_value
            components = [
                by_id[report_norm_id].cells[axis.ordinal].displayed_value
                for report_norm_id in check.component_report_norm_ids
            ]
            if (
                target is None
                or any(value is None for value in components)
                or target != sum(value for value in components if value is not None)
            ):
                raise CDKTOffBalancePage5Error("page-5 accounting equation failed")
            passed_checks.append(
                f"{check.target_report_norm_id}=SUM({','.join(map(str, check.component_report_norm_ids))})/{axis.role}"
            )
    project_root = policy.source_path.parents[2]
    result = ParsedCDKTOffBalancePage5(
        page_number=policy.page_number,
        scope=policy.scope,
        unit=policy.unit,
        unit_multiplier=policy.unit_multiplier,
        source_pdf_path=policy.source_pdf_path.relative_to(project_root).as_posix(),
        source_pdf_sha256=policy.source_pdf_sha256,
        source_ocr_path=policy.source_ocr_path.relative_to(project_root).as_posix(),
        source_ocr_sha256=policy.source_ocr_sha256,
        source_render_path=policy.source_render_path.relative_to(project_root).as_posix(),
        source_render_sha256=policy.source_render_sha256,
        render_width=width,
        render_height=height,
        policy_path=policy.source_path.relative_to(project_root).as_posix(),
        policy_sha256=policy.policy_sha256,
        axes=policy.axes,
        rows=tuple(rows),
        accounting_checks_passed=tuple(passed_checks),
    )
    if (
        result.source_row_count != 11
        or result.physical_cell_count != 22
        or result.value_cell_count != 18
        or result.blank_cell_count != 4
    ):
        raise CDKTOffBalancePage5Error("page-5 source coverage drifted")
    return result


__all__ = [
    "CDKT_OFF_BALANCE_PAGE5_POLICY_RELATIVE_PATH",
    "CDKTOffBalanceCell",
    "CDKTOffBalancePage5Error",
    "CDKTOffBalancePage5Policy",
    "CDKTOffBalanceRow",
    "ParsedCDKTOffBalancePage5",
    "load_cdkt_off_balance_page5_policy",
    "parse_cdkt_off_balance_page5",
]
