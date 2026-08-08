from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import fitz
from PIL import Image

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.tables.kqkd_word_box import ParsedKQKDWordBoxPage


class KQKDNumericVerificationError(ValueError):
    pass


_PDF_NUMERIC_TOKEN = re.compile(r"^[\d\s.,()\-+–—−]+$")
_GROUPED_INTEGER = re.compile(r"^(?:\d+|\d{1,3}(?:[.,]\d{3})+)$")


@dataclass(frozen=True, slots=True)
class KQKDPDFTextToken:
    token_index: int
    text: str
    pdf_bbox: BoundingBox
    render_bbox: BoundingBox


@dataclass(frozen=True, slots=True)
class KQKDNumericCellVerification:
    row_id: str
    row_ordinal: int
    axis_id: str
    axis_ordinal: int
    ppocr_raw_text: str
    ppocr_signed_integer_reported_unit: str
    pdf_text_tokens: tuple[KQKDPDFTextToken, ...]
    pdf_text_joined: str
    pdf_text_signed_integer_reported_unit: str
    observed: bool
    numeric_verified: bool

    @property
    def mapping_authority(self) -> bool:
        return False

    @property
    def fully_verified(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class KQKDAccountingOperand:
    row_ordinal: int
    coefficient: int


@dataclass(frozen=True, slots=True)
class KQKDAccountingEquationSpec:
    equation_id: str
    target_row_ordinal: int
    operands: tuple[KQKDAccountingOperand, ...]


@dataclass(frozen=True, slots=True)
class KQKDAccountingEquationResult:
    equation_id: str
    target_row_ordinal: int
    operands: tuple[KQKDAccountingOperand, ...]
    residuals_by_axis: tuple[str, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class KQKDNumericVerificationResult:
    source_pdf_path: str
    source_pdf_sha256: str
    source_page_number: int
    source_render_path: str
    source_render_sha256: str
    source_ocr_sha256: str
    assigned_pdf_text_token_count: int
    cells: tuple[KQKDNumericCellVerification, ...]
    accounting_equations: tuple[KQKDAccountingEquationResult, ...]

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    @property
    def observed_cell_count(self) -> int:
        return sum(cell.observed for cell in self.cells)

    @property
    def numeric_verified_cell_count(self) -> int:
        return sum(cell.numeric_verified for cell in self.cells)

    @property
    def numeric_verified(self) -> bool:
        return bool(self.cells) and self.numeric_verified_cell_count == self.cell_count

    @property
    def accounting_equation_count(self) -> int:
        return len(self.accounting_equations)

    @property
    def accounting_check_count(self) -> int:
        return sum(len(equation.residuals_by_axis) for equation in self.accounting_equations)

    @property
    def accounting_passed_check_count(self) -> int:
        return sum(
            residual == "0"
            for equation in self.accounting_equations
            for residual in equation.residuals_by_axis
        )

    @property
    def accounting_verified(self) -> bool:
        return bool(self.accounting_equations) and all(
            equation.passed for equation in self.accounting_equations
        )

    @property
    def mapping_authority(self) -> bool:
        return False

    @property
    def fully_verified(self) -> bool:
        return False

    def cell_by_key(self) -> dict[tuple[str, str], KQKDNumericCellVerification]:
        return {(cell.row_id, cell.axis_id): cell for cell in self.cells}

    def verification_payload(self) -> list[dict[str, object]]:
        return [
            {
                "row_ordinal": cell.row_ordinal,
                "axis_ordinal": cell.axis_ordinal,
                "pdf_text_tokens": [token.text for token in cell.pdf_text_tokens],
                "pdf_text_joined": cell.pdf_text_joined,
                "normalized_signed_integer_reported_unit": (
                    cell.pdf_text_signed_integer_reported_unit
                ),
                "ppocr_signed_integer_reported_unit": cell.ppocr_signed_integer_reported_unit,
                "match": cell.numeric_verified,
            }
            for cell in self.cells
        ]

    def accounting_payload(self) -> list[dict[str, object]]:
        return [
            {
                "equation_id": equation.equation_id,
                "target_row_ordinal": equation.target_row_ordinal,
                "operands": [
                    {
                        "row_ordinal": operand.row_ordinal,
                        "coefficient": operand.coefficient,
                    }
                    for operand in equation.operands
                ],
                "residuals_by_axis": list(equation.residuals_by_axis),
                "pass": equation.passed,
            }
            for equation in self.accounting_equations
        ]

    @property
    def verification_payload_sha256(self) -> str:
        return _canonical_sha256(self.verification_payload())

    @property
    def accounting_payload_sha256(self) -> str:
        return _canonical_sha256(self.accounting_payload())


@dataclass(frozen=True, slots=True)
class _CellGeometry:
    row_id: str
    row_ordinal: int
    axis_id: str
    axis_ordinal: int
    bbox: BoundingBox

    @property
    def x_center(self) -> float:
        return (self.bbox.x0 + self.bbox.x1) / 2

    @property
    def y_center(self) -> float:
        return (self.bbox.y0 + self.bbox.y1) / 2


def _operand(row_ordinal: int, coefficient: int = 1) -> KQKDAccountingOperand:
    return KQKDAccountingOperand(row_ordinal=row_ordinal, coefficient=coefficient)


MBB_Q1_2026_KQKD_EQUATIONS: tuple[KQKDAccountingEquationSpec, ...] = (
    KQKDAccountingEquationSpec("NET_INTEREST", 3, (_operand(1), _operand(2))),
    KQKDAccountingEquationSpec("NET_SERVICE", 6, (_operand(4), _operand(5))),
    KQKDAccountingEquationSpec(
        "TOTAL_OPERATING_INCOME_SOURCE_ONLY",
        12,
        tuple(_operand(ordinal) for ordinal in (3, 6, 7, 8, 9, 10, 11)),
    ),
    KQKDAccountingEquationSpec("PRE_PROVISION_PROFIT", 14, (_operand(12), _operand(13))),
    KQKDAccountingEquationSpec("PRETAX_PROFIT", 16, (_operand(14), _operand(15))),
    KQKDAccountingEquationSpec("TOTAL_TAX_EXPENSE", 19, (_operand(17), _operand(18))),
    KQKDAccountingEquationSpec("AFTER_TAX_PROFIT", 20, (_operand(16), _operand(19))),
    KQKDAccountingEquationSpec("PARENT_PROFIT_ATTRIBUTION", 22, (_operand(20), _operand(21, -1))),
)


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_pdf_text_reported_integer(raw_tokens: Sequence[str]) -> Decimal:
    """Normalize visible integer amounts while retaining source punctuation separately."""

    if not raw_tokens or any(not isinstance(token, str) for token in raw_tokens):
        raise KQKDNumericVerificationError("PDF text-layer numeric token group is empty")
    raw = "".join(raw_tokens)
    compact = re.sub(r"\s+", "", raw).translate(str.maketrans({"–": "-", "—": "-", "−": "-"}))
    if not compact or _PDF_NUMERIC_TOKEN.fullmatch(compact) is None:
        raise KQKDNumericVerificationError("PDF text-layer group is not numeric")

    negative = False
    if "(" in compact or ")" in compact:
        if compact.count("(") != 1 or compact.count(")") != 1:
            raise KQKDNumericVerificationError("PDF text-layer parentheses are unbalanced")
        if not compact.startswith("(") or not compact.endswith(")"):
            raise KQKDNumericVerificationError("PDF text-layer parentheses do not enclose value")
        negative = True
        compact = compact[1:-1]
    if compact.startswith("-") or compact.endswith("-"):
        if negative or compact.count("-") != 1:
            raise KQKDNumericVerificationError("PDF text-layer value has conflicting signs")
        negative = True
        compact = compact.removeprefix("-").removesuffix("-")
    elif compact.startswith("+"):
        compact = compact[1:]
    if "+" in compact or "-" in compact or _GROUPED_INTEGER.fullmatch(compact) is None:
        raise KQKDNumericVerificationError("PDF text-layer value is not a grouped integer")

    digits = compact.replace(".", "").replace(",", "")
    value = Decimal(digits)
    return -value if negative else value


def _cell_geometries(parsed: ParsedKQKDWordBoxPage) -> tuple[_CellGeometry, ...]:
    if not parsed.rows or not parsed.axes:
        raise KQKDNumericVerificationError("KQKD parser result has no rows or axes")
    if [row.ordinal for row in parsed.rows] != list(range(1, len(parsed.rows) + 1)):
        raise KQKDNumericVerificationError("KQKD row ordinals are not contiguous")
    if [axis.ordinal for axis in parsed.axes] != list(range(1, len(parsed.axes) + 1)):
        raise KQKDNumericVerificationError("KQKD axis ordinals are not contiguous")
    if len({row.row_id for row in parsed.rows}) != len(parsed.rows):
        raise KQKDNumericVerificationError("KQKD row identities are duplicate")
    if len({axis.axis_id for axis in parsed.axes}) != len(parsed.axes):
        raise KQKDNumericVerificationError("KQKD axis identities are duplicate")
    if any(
        axis.canonical_unit != "VND"
        or type(axis.unit_multiplier) is not int
        or axis.unit_multiplier <= 0
        for axis in parsed.axes
    ):
        raise KQKDNumericVerificationError("KQKD axes are not integer-reported VND units")
    geometries = []
    for row in parsed.rows:
        if len(row.value_bboxes) != len(parsed.axes) or len(row.row.cells) != len(parsed.axes):
            raise KQKDNumericVerificationError("KQKD row/axis denominator differs")
        for axis, bbox in zip(parsed.axes, row.value_bboxes, strict=True):
            if bbox is None:
                raise KQKDNumericVerificationError("KQKD numeric cell has no source geometry")
            geometries.append(
                _CellGeometry(
                    row_id=row.row_id,
                    row_ordinal=row.ordinal,
                    axis_id=axis.axis_id,
                    axis_ordinal=axis.ordinal,
                    bbox=bbox,
                )
            )
    return tuple(geometries)


def _extract_and_align_pdf_tokens(
    *,
    source_pdf_path: Path,
    page_number: int,
    render_width: int,
    render_height: int,
    geometries: tuple[_CellGeometry, ...],
) -> dict[tuple[str, str], tuple[KQKDPDFTextToken, ...]]:
    if page_number < 1:
        raise KQKDNumericVerificationError("source PDF page number must be one-based")
    widths = [geometry.bbox.x1 - geometry.bbox.x0 for geometry in geometries]
    heights = [geometry.bbox.y1 - geometry.bbox.y0 for geometry in geometries]
    maximum_x_distance = statistics.median(widths) * 0.9
    maximum_y_distance = statistics.median(heights)
    if maximum_x_distance <= 0 or maximum_y_distance <= 0:
        raise KQKDNumericVerificationError("KQKD cell geometry is degenerate")

    grouped: dict[tuple[str, str], list[KQKDPDFTextToken]] = defaultdict(list)
    try:
        with fitz.open(source_pdf_path) as document:
            if page_number > len(document):
                raise KQKDNumericVerificationError("source PDF page is absent")
            page = document[page_number - 1]
            if page.rect.width <= 0 or page.rect.height <= 0:
                raise KQKDNumericVerificationError("source PDF page geometry is invalid")
            scale_x = render_width / page.rect.width
            scale_y = render_height / page.rect.height
            words = page.get_text("words", sort=True)
    except KQKDNumericVerificationError:
        raise
    except Exception as exc:
        raise KQKDNumericVerificationError("cannot read source PDF text layer") from exc

    for token_index, word in enumerate(words):
        if len(word) < 5:
            raise KQKDNumericVerificationError("source PDF text-layer word is malformed")
        x0, y0, x1, y1 = (float(word[index]) for index in range(4))
        text = str(word[4])
        if not any(character.isdigit() for character in text):
            continue
        if _PDF_NUMERIC_TOKEN.fullmatch(text) is None:
            continue
        pdf_bbox = BoundingBox(x0, y0, x1, y1)
        render_bbox = BoundingBox(x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y)
        x_center = (render_bbox.x0 + render_bbox.x1) / 2
        y_center = (render_bbox.y0 + render_bbox.y1) / 2
        nearest = min(
            geometries,
            key=lambda geometry: (
                ((geometry.x_center - x_center) / maximum_x_distance) ** 2
                + ((geometry.y_center - y_center) / maximum_y_distance) ** 2,
                geometry.row_ordinal,
                geometry.axis_ordinal,
            ),
        )
        if (
            abs(nearest.x_center - x_center) > maximum_x_distance
            or abs(nearest.y_center - y_center) > maximum_y_distance
        ):
            continue
        grouped[(nearest.row_id, nearest.axis_id)].append(
            KQKDPDFTextToken(
                token_index=token_index,
                text=text,
                pdf_bbox=pdf_bbox,
                render_bbox=render_bbox,
            )
        )

    return {
        key: tuple(sorted(tokens, key=lambda token: (token.pdf_bbox.x0, token.token_index)))
        for key, tokens in grouped.items()
    }


def _verify_cells(
    parsed: ParsedKQKDWordBoxPage,
    token_groups: dict[tuple[str, str], tuple[KQKDPDFTextToken, ...]],
) -> tuple[KQKDNumericCellVerification, ...]:
    results = []
    expected_keys = {(row.row_id, axis.axis_id) for row in parsed.rows for axis in parsed.axes}
    if set(token_groups) != expected_keys:
        missing = sorted(expected_keys - set(token_groups))
        unexpected = sorted(set(token_groups) - expected_keys)
        raise KQKDNumericVerificationError(
            f"PDF text-layer/cell denominator differs: missing={missing}, unexpected={unexpected}"
        )
    for row in parsed.rows:
        for axis, cell in zip(parsed.axes, row.row.cells, strict=True):
            if cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}:
                raise KQKDNumericVerificationError("KQKD cell is not an observed numeric value")
            if cell.value is None or cell.value != cell.value.to_integral_value():
                raise KQKDNumericVerificationError("PP-OCR KQKD value is not an integer")
            tokens = token_groups[(row.row_id, axis.axis_id)]
            pdf_value = normalize_pdf_text_reported_integer(tuple(token.text for token in tokens))
            if pdf_value != cell.value:
                raise KQKDNumericVerificationError(
                    f"independent numeric disagreement at {row.row_id}/{axis.axis_id}: "
                    f"PP-OCR={cell.value}, PDF_TEXT_LAYER={pdf_value}"
                )
            results.append(
                KQKDNumericCellVerification(
                    row_id=row.row_id,
                    row_ordinal=row.ordinal,
                    axis_id=axis.axis_id,
                    axis_ordinal=axis.ordinal,
                    ppocr_raw_text=cell.raw_text,
                    ppocr_signed_integer_reported_unit=str(cell.value),
                    pdf_text_tokens=tokens,
                    pdf_text_joined="".join(token.text for token in tokens),
                    pdf_text_signed_integer_reported_unit=str(pdf_value),
                    observed=True,
                    numeric_verified=True,
                )
            )
    return tuple(results)


def _validate_equation_specs(
    specs: Sequence[KQKDAccountingEquationSpec], *, row_count: int
) -> tuple[KQKDAccountingEquationSpec, ...]:
    frozen = tuple(specs)
    if not frozen or len({spec.equation_id for spec in frozen}) != len(frozen):
        raise KQKDNumericVerificationError("accounting equation identities are empty or duplicate")
    for spec in frozen:
        if not 1 <= spec.target_row_ordinal <= row_count or not spec.operands:
            raise KQKDNumericVerificationError(
                "accounting equation row is outside source denominator"
            )
        if any(
            not 1 <= operand.row_ordinal <= row_count
            or type(operand.coefficient) is not int
            or operand.coefficient == 0
            for operand in spec.operands
        ):
            raise KQKDNumericVerificationError("accounting equation operand is invalid")
    return frozen


def _verify_accounting(
    cells: tuple[KQKDNumericCellVerification, ...],
    *,
    row_count: int,
    axis_count: int,
    equation_specs: Sequence[KQKDAccountingEquationSpec],
) -> tuple[KQKDAccountingEquationResult, ...]:
    specs = _validate_equation_specs(equation_specs, row_count=row_count)
    values = {
        (cell.row_ordinal, cell.axis_ordinal): Decimal(cell.pdf_text_signed_integer_reported_unit)
        for cell in cells
    }
    results = []
    for spec in specs:
        residuals = []
        for axis_ordinal in range(1, axis_count + 1):
            target = values[(spec.target_row_ordinal, axis_ordinal)]
            computed = sum(
                (
                    values[(operand.row_ordinal, axis_ordinal)] * operand.coefficient
                    for operand in spec.operands
                ),
                Decimal(0),
            )
            residuals.append(str(target - computed))
        passed = all(residual == "0" for residual in residuals)
        if not passed:
            raise KQKDNumericVerificationError(
                f"accounting equation {spec.equation_id} has non-zero residual"
            )
        results.append(
            KQKDAccountingEquationResult(
                equation_id=spec.equation_id,
                target_row_ordinal=spec.target_row_ordinal,
                operands=spec.operands,
                residuals_by_axis=tuple(residuals),
                passed=True,
            )
        )
    return tuple(results)


def verify_kqkd_numeric_page(
    parsed: ParsedKQKDWordBoxPage,
    source_pdf_path: Path,
    *,
    page_number: int,
    render_path: Path | None = None,
    equation_specs: Sequence[KQKDAccountingEquationSpec] = MBB_Q1_2026_KQKD_EQUATIONS,
) -> KQKDNumericVerificationResult:
    """Verify KQKD numbers against the source PDF text layer, without mapping authority."""

    source_pdf_path = source_pdf_path.resolve()
    render_path = (Path(parsed.input_path) if render_path is None else render_path).resolve()
    if not source_pdf_path.is_file():
        raise KQKDNumericVerificationError("source PDF is absent")
    if not render_path.is_file():
        raise KQKDNumericVerificationError("source render is absent")
    try:
        with Image.open(render_path) as image:
            render_width, render_height = image.size
    except Exception as exc:
        raise KQKDNumericVerificationError("cannot read source render geometry") from exc
    if render_width <= 0 or render_height <= 0:
        raise KQKDNumericVerificationError("source render geometry is invalid")

    geometries = _cell_geometries(parsed)
    token_groups = _extract_and_align_pdf_tokens(
        source_pdf_path=source_pdf_path,
        page_number=page_number,
        render_width=render_width,
        render_height=render_height,
        geometries=geometries,
    )
    cells = _verify_cells(parsed, token_groups)
    equations = _verify_accounting(
        cells,
        row_count=len(parsed.rows),
        axis_count=len(parsed.axes),
        equation_specs=equation_specs,
    )
    return KQKDNumericVerificationResult(
        source_pdf_path=source_pdf_path.as_posix(),
        source_pdf_sha256=sha256_file(source_pdf_path),
        source_page_number=page_number,
        source_render_path=render_path.as_posix(),
        source_render_sha256=sha256_file(render_path),
        source_ocr_sha256=parsed.source_sha256,
        assigned_pdf_text_token_count=sum(len(tokens) for tokens in token_groups.values()),
        cells=cells,
        accounting_equations=equations,
    )


__all__ = [
    "KQKDAccountingEquationResult",
    "KQKDAccountingEquationSpec",
    "KQKDAccountingOperand",
    "KQKDNumericCellVerification",
    "KQKDNumericVerificationError",
    "KQKDNumericVerificationResult",
    "KQKDPDFTextToken",
    "MBB_Q1_2026_KQKD_EQUATIONS",
    "normalize_pdf_text_reported_integer",
    "verify_kqkd_numeric_page",
]
