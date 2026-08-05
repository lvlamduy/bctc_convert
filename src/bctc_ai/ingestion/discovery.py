from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveredSource:
    path: Path
    kind: str
    bank: str | None = None
    year: int | None = None


def discover_pdfs(root: Path) -> list[DiscoveredSource]:
    sources: list[DiscoveredSource] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() != ".pdf":
            continue
        relative = path.relative_to(root)
        bank = relative.parts[0] if len(relative.parts) >= 1 else None
        try:
            year = int(relative.parts[1]) if len(relative.parts) >= 2 else None
        except ValueError:
            year = None
        sources.append(DiscoveredSource(path=path, kind="PDF", bank=bank, year=year))
    return sources
