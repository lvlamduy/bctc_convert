"""Shared foreground-component geometry for authenticated accounting crops."""

from __future__ import annotations

from statistics import median
from typing import Any

from PIL import Image

__all__ = ["AccountingPixelGlyphsV1Error", "foreground_components_v1"]


class AccountingPixelGlyphsV1Error(ValueError):
    """A proposed pixel region cannot support stable glyph components."""


def _error(message: str) -> AccountingPixelGlyphsV1Error:
    return AccountingPixelGlyphsV1Error(message)


def foreground_components_v1(image: Any) -> dict[str, Any]:
    """Return glyph-like dark connected components in one crop.

    The crop-local border estimates the background.  Isolated antialias noise
    and components spanning almost the complete crop (usually table rules or a
    filled background) are rejected.  This function classifies geometry only;
    it does not decide whether a component is a digit, dash, or text.
    """

    if not isinstance(image, Image.Image) or image.width <= 0 or image.height <= 0:
        raise _error("foreground analysis requires one positive-area PIL image")
    grayscale = image.convert("L")
    width, height = grayscale.size
    pixels = list(grayscale.get_flattened_data())
    border = [
        *pixels[:width],
        *pixels[-width:],
        *(pixels[row * width] for row in range(height)),
        *(pixels[row * width + width - 1] for row in range(height)),
    ]
    background = float(median(border))
    threshold = max(80, min(220, int(round(background - 35))))
    mask = bytearray(value < threshold for value in pixels)
    visited = bytearray(width * height)
    components: list[dict[str, Any]] = []
    minimum_area = max(3, int(round(width * height * 0.0002)))
    for start in range(width * height):
        if not mask[start] or visited[start]:
            continue
        visited[start] = 1
        stack = [start]
        count = 0
        min_x = max_x = start % width
        min_y = max_y = start // width
        while stack:
            current = stack.pop()
            x = current % width
            y = current // width
            count += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
                for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = neighbor_y * width + neighbor_x
                    if mask[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        stack.append(neighbor)
        component_width = max_x - min_x + 1
        component_height = max_y - min_y + 1
        if (
            count >= minimum_area
            and component_width < width * 0.85
            and component_height < height * 0.85
        ):
            components.append(
                {
                    "bbox": [min_x, min_y, max_x + 1, max_y + 1],
                    "ink_pixel_count": count,
                }
            )
    return {
        "background_luma": background,
        "components": components,
        "crop_height": height,
        "crop_width": width,
        "threshold_luma": threshold,
    }
