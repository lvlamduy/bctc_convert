from __future__ import annotations

from fractions import Fraction
from math import isfinite


def round_fraction_half_away_from_zero(value: Fraction) -> int:
    """Round an exact rational to an integer, resolving ties away from zero."""

    if not isinstance(value, Fraction):
        raise TypeError("half-away rounding requires an exact Fraction")
    sign = -1 if value < 0 else 1
    absolute = abs(value)
    quotient, remainder = divmod(absolute.numerator, absolute.denominator)
    return sign * (quotient + (2 * remainder >= absolute.denominator))


def points_to_millipoints(value: int | float | Fraction) -> int:
    """Convert PDF points to integer millipoints with exact half-away rounding."""

    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise TypeError("millipoint source coordinate must be numeric")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("millipoint source coordinate must be finite")
    exact = value if isinstance(value, Fraction) else Fraction(str(value))
    return round_fraction_half_away_from_zero(exact * 1000)
