from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import Any

import fitz

from bctc_ai.core.coordinates import (
    points_to_millipoints,
    round_fraction_half_away_from_zero,
)
from bctc_ai.core.hashing import sha256_bytes


class PageReaderRenderError(RuntimeError):
    """A page render or its coordinate authority cannot be established exactly."""


Rational = tuple[int, int]
RationalMatrix = tuple[tuple[Rational, Rational, Rational], ...]


def _fraction_record(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _matrix_record(matrix: RationalMatrix) -> list[list[dict[str, int]]]:
    return [[_fraction_record(Fraction(*coefficient)) for coefficient in row] for row in matrix]


def _as_fraction_matrix(matrix: RationalMatrix) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(tuple(Fraction(*coefficient) for coefficient in row) for row in matrix)


def _normalize_matrix(matrix: Iterable[Iterable[Fraction]]) -> RationalMatrix:
    return tuple(
        tuple((value.numerator, value.denominator) for value in row)  # type: ignore[misc]
        for row in matrix
    )  # type: ignore[return-value]


def _multiply(left: RationalMatrix, right: RationalMatrix) -> RationalMatrix:
    a = _as_fraction_matrix(left)
    b = _as_fraction_matrix(right)
    product = tuple(
        tuple(sum((a[row][k] * b[k][column] for k in range(3)), Fraction()) for column in range(3))
        for row in range(3)
    )
    return _normalize_matrix(product)


def _inverse_affine(matrix: RationalMatrix) -> RationalMatrix:
    source = _as_fraction_matrix(matrix)
    a, c, e = source[0]
    b, d, f = source[1]
    if source[2] != (Fraction(0), Fraction(0), Fraction(1)):
        raise PageReaderRenderError("coordinate matrix is not affine")
    determinant = a * d - b * c
    if determinant == 0:
        raise PageReaderRenderError("coordinate matrix is singular")
    inverse = (
        (d / determinant, -c / determinant, (c * f - d * e) / determinant),
        (-b / determinant, a / determinant, (b * e - a * f) / determinant),
        (Fraction(0), Fraction(0), Fraction(1)),
    )
    return _normalize_matrix(inverse)


def apply_rational_matrix(
    matrix: RationalMatrix,
    x: int | float | Fraction,
    y: int | float | Fraction,
) -> tuple[Fraction, Fraction]:
    values = _as_fraction_matrix(matrix)
    point_x = x if isinstance(x, Fraction) else Fraction(str(x))
    point_y = y if isinstance(y, Fraction) else Fraction(str(y))
    return (
        values[0][0] * point_x + values[0][1] * point_y + values[0][2],
        values[1][0] * point_x + values[1][1] * point_y + values[1][2],
    )


def _rational(value: int, denominator: int = 1) -> Rational:
    divisor = gcd(value, denominator)
    return value // divisor, denominator // divisor


def coordinate_authority(
    page: fitz.Page,
    *,
    pixel_width: int,
    pixel_height: int,
) -> dict[str, Any]:
    """Return exact pixel/displayed/unrotated coordinate transforms.

    Matrices use homogeneous column vectors.  Pixel coordinates refer to the
    composited displayed raster.  Canonical coordinates are integer
    millipoints in the unrotated crop-box, top-left coordinate system used by
    PyMuPDF text extraction.
    """

    if pixel_width <= 0 or pixel_height <= 0:
        raise PageReaderRenderError("render dimensions must be positive")
    rotation = int(page.rotation)
    if rotation not in {0, 90, 180, 270}:
        raise PageReaderRenderError("PDF page rotation must be orthogonal")
    displayed_width = points_to_millipoints(page.rect.width)
    displayed_height = points_to_millipoints(page.rect.height)
    unrotated_width = points_to_millipoints(page.cropbox.width)
    unrotated_height = points_to_millipoints(page.cropbox.height)
    pixel_to_displayed: RationalMatrix = (
        (_rational(displayed_width, pixel_width), (0, 1), (0, 1)),
        ((0, 1), _rational(displayed_height, pixel_height), (0, 1)),
        ((0, 1), (0, 1), (1, 1)),
    )
    if rotation == 0:
        displayed_to_unrotated: RationalMatrix = (
            ((1, 1), (0, 1), (0, 1)),
            ((0, 1), (1, 1), (0, 1)),
            ((0, 1), (0, 1), (1, 1)),
        )
    elif rotation == 90:
        displayed_to_unrotated = (
            ((0, 1), (1, 1), (0, 1)),
            ((-1, 1), (0, 1), (unrotated_height, 1)),
            ((0, 1), (0, 1), (1, 1)),
        )
    elif rotation == 180:
        displayed_to_unrotated = (
            ((-1, 1), (0, 1), (unrotated_width, 1)),
            ((0, 1), (-1, 1), (unrotated_height, 1)),
            ((0, 1), (0, 1), (1, 1)),
        )
    else:
        displayed_to_unrotated = (
            ((0, 1), (-1, 1), (unrotated_width, 1)),
            ((1, 1), (0, 1), (0, 1)),
            ((0, 1), (0, 1), (1, 1)),
        )
    pixel_to_unrotated = _multiply(displayed_to_unrotated, pixel_to_displayed)
    unrotated_to_pixel = _inverse_affine(pixel_to_unrotated)
    return {
        "matrix_convention": "COLUMN_VECTOR_3X3_RATIONAL",
        "pixel_coordinate_system": "DISPLAYED_PAGE_RASTER_PIXELS_TOP_LEFT",
        "displayed_coordinate_system": "DISPLAYED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_origin": "UNROTATED_CROP_BOX_TOP_LEFT_RELATIVE",
        "pixel_dimensions": [pixel_width, pixel_height],
        "displayed_dimensions_mpt": [displayed_width, displayed_height],
        "unrotated_dimensions_mpt": [unrotated_width, unrotated_height],
        "pdf_rotation_degrees": rotation,
        "pixel_to_displayed_mpt": _matrix_record(pixel_to_displayed),
        "displayed_mpt_to_unrotated_mpt": _matrix_record(displayed_to_unrotated),
        "pixel_to_unrotated_mpt": _matrix_record(pixel_to_unrotated),
        "unrotated_mpt_to_pixel": _matrix_record(unrotated_to_pixel),
        "_pixel_to_unrotated_matrix": pixel_to_unrotated,
        "_unrotated_to_pixel_matrix": unrotated_to_pixel,
    }


def transform_pixel_polygon_to_unrotated_mpt(
    points: Iterable[Iterable[int | float]],
    authority: dict[str, Any],
) -> list[list[int]]:
    matrix = authority.get("_pixel_to_unrotated_matrix")
    if not isinstance(matrix, tuple):
        raise PageReaderRenderError("in-memory coordinate authority is absent")
    transformed: list[list[int]] = []
    for point in points:
        coordinates = tuple(point)
        if len(coordinates) != 2:
            raise PageReaderRenderError("polygon point must contain x and y")
        x, y = apply_rational_matrix(matrix, coordinates[0], coordinates[1])
        transformed.append(
            [
                round_fraction_half_away_from_zero(x),
                round_fraction_half_away_from_zero(y),
            ]
        )
    return transformed


def public_coordinate_authority(authority: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in authority.items() if not key.startswith("_")}


@dataclass(frozen=True)
class CompositePageRender:
    payload: bytes
    sha256: str
    size_bytes: int
    dpi: int
    pixel_width: int
    pixel_height: int
    coordinate_authority: dict[str, Any]


def render_composited_displayed_page(page: fitz.Page, *, dpi: int) -> CompositePageRender:
    if dpi not in {200, 300}:
        raise PageReaderRenderError("Wave 1 composited render DPI must be 200 or 300")
    scale = dpi / 72
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale),
        colorspace=fitz.csRGB,
        alpha=False,
        annots=True,
    )
    if pixmap.alpha or pixmap.n != 3:
        raise PageReaderRenderError("composited render is not opaque RGB")
    payload = pixmap.tobytes("png")
    authority = coordinate_authority(
        page,
        pixel_width=int(pixmap.width),
        pixel_height=int(pixmap.height),
    )
    return CompositePageRender(
        payload=payload,
        sha256=sha256_bytes(payload),
        size_bytes=len(payload),
        dpi=dpi,
        pixel_width=int(pixmap.width),
        pixel_height=int(pixmap.height),
        coordinate_authority=authority,
    )
