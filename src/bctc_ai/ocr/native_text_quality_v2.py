from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord, extract_pdf_text


class NativeTextQualityV2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeTextQualityAssessment:
    status: str
    corruption_markers: tuple[str, ...]
    marker_counts: dict[str, int]
    replacement_ratio: float
    unexpected_control_count: int
    legitimate_vietnamese_tokens: dict[str, tuple[str, ...]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_native_text_quality_v2_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NativeTextQualityV2Error(f"cannot load native-text quality config: {path}") from exc
    expected = {
        "version": 2,
        "policy": "UNICODE_AWARE_VIETNAMESE_NATIVE_TEXT_QUALITY",
        "replacement_character": "�",
        "contextual_safe_follow": "ASCII_CHARACTER_OR_BOUNDARY",
        "reject_unexpected_control_characters": True,
    }
    if not isinstance(payload, dict) or any(
        payload.get(key) != value for key, value in expected.items()
    ):
        raise NativeTextQualityV2Error("native-text quality identity/policy drifted")
    ratio = payload.get("maximum_replacement_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1:
        raise NativeTextQualityV2Error("maximum replacement ratio must be within [0, 1]")
    expected_lists = {
        "always_suspicious_leads": ["Ä", "Æ"],
        "contextual_leads": ["Ã", "Â"],
        "double_encoded_prefixes": ["á»", "áº"],
        "legitimate_vietnamese_letters": ["Â", "Ã"],
    }
    if any(payload.get(key) != value for key, value in expected_lists.items()):
        raise NativeTextQualityV2Error("native-text mojibake policy drifted")
    return payload


def _contextual_fragments(raw: str, leads: tuple[str, ...]) -> tuple[str, ...]:
    fragments = []
    for index, character in enumerate(raw):
        if character not in leads:
            continue
        following = raw[index + 1] if index + 1 < len(raw) else ""
        if following and not following.isascii():
            fragments.append(character + following)
    return tuple(fragments)


def assess_native_text_quality_v2(
    words: list[PDFWord],
    config: dict[str, Any],
) -> NativeTextQualityAssessment:
    if config.get("version") != 2:
        raise NativeTextQualityV2Error("native-text quality v2 config is required")
    if not words:
        return NativeTextQualityAssessment(
            status="NO_TEXT_LAYER",
            corruption_markers=(),
            marker_counts={},
            replacement_ratio=0.0,
            unexpected_control_count=0,
            legitimate_vietnamese_tokens={letter: () for letter in ("Â", "Ã")},
        )

    raw = " ".join(word.raw_text for word in words)
    replacement = str(config["replacement_character"])
    marker_counts: dict[str, int] = {}
    replacement_count = raw.count(replacement)
    if replacement_count:
        marker_counts[replacement] = replacement_count
    for prefix in config["double_encoded_prefixes"]:
        count = raw.count(str(prefix))
        if count:
            marker_counts[str(prefix)] = count
    for lead in config["always_suspicious_leads"]:
        count = raw.count(str(lead))
        if count:
            marker_counts[str(lead)] = count
    for fragment in _contextual_fragments(raw, tuple(config["contextual_leads"])):
        marker_counts[fragment] = marker_counts.get(fragment, 0) + 1

    unexpected_controls = tuple(
        character
        for character in raw
        if unicodedata.category(character) == "Cc" and character not in "\t\n\r"
    )
    for character in unexpected_controls:
        label = f"U+{ord(character):04X}"
        marker_counts[label] = marker_counts.get(label, 0) + 1

    replacement_ratio = replacement_count / max(1, len(raw))
    status = (
        "CORRUPT_TEXT_LAYER"
        if marker_counts or replacement_ratio > float(config["maximum_replacement_ratio"])
        else "USABLE_TEXT_LAYER"
    )
    legitimate = {
        letter: tuple(sorted({word.raw_text for word in words if letter in word.raw_text}))
        for letter in config["legitimate_vietnamese_letters"]
    }
    return NativeTextQualityAssessment(
        status=status,
        corruption_markers=tuple(sorted(marker_counts)),
        marker_counts=dict(sorted(marker_counts.items())),
        replacement_ratio=replacement_ratio,
        unexpected_control_count=len(unexpected_controls),
        legitimate_vietnamese_tokens=legitimate,
    )


def apply_native_text_quality_v2(
    page: PDFTextPage,
    config: dict[str, Any],
) -> PDFTextPage:
    assessment = assess_native_text_quality_v2(page.words, config)
    return replace(
        page,
        text_quality=assessment.status,
        corruption_markers=assessment.corruption_markers,
    )


def extract_pdf_text_v2(
    path: Path,
    *,
    config: dict[str, Any],
    page_numbers: set[int] | None = None,
) -> list[PDFTextPage]:
    return [
        apply_native_text_quality_v2(page, config)
        for page in extract_pdf_text(path, page_numbers=page_numbers)
    ]
