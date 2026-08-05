from __future__ import annotations

import re
from dataclasses import dataclass

from bctc_ai.core.text import normalize_text

_NOTE_PATTERN = re.compile(
    r"(?:thuy[eế]t\s*minh|note)\s*(?:s[oố]\s*)?(?P<section>\d+(?:[.]\d+)*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NoteReference:
    raw_text: str
    notes_section: str
    start: int
    end: int


def extract_note_references(text: str) -> list[NoteReference]:
    normalized = normalize_text(text)
    return [
        NoteReference(normalized, match.group("section"), match.start(), match.end())
        for match in _NOTE_PATTERN.finditer(normalized)
    ]
