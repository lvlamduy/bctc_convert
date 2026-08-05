from __future__ import annotations

from pathlib import Path

from bctc_ai.core.hashing import sha256_file
from bctc_ai.schema.xlsx_reader import read_rows

CATEGORY_BY_COLUMN = {"B": "BANK", "C": "INSURANCE", "D": "SECURITIES_OR_FUND"}


def load_bank_registry(path: Path, project_root: Path) -> dict[str, object]:
    rows = list(read_rows(path))
    if not rows:
        raise ValueError(f"bank list is empty: {path}")
    headings = rows[0]
    entities = []
    seen: set[str] = set()
    for row_number, row in enumerate(rows[1:], start=2):
        for column, category in CATEGORY_BY_COLUMN.items():
            code = row.get(column, "").strip().upper()
            if not code:
                continue
            if code in seen:
                raise ValueError(f"duplicate entity code {code} at {path}:{row_number}")
            seen.add(code)
            entities.append(
                {
                    "code": code,
                    "category": category,
                    "source_column": column,
                    "source_heading": headings.get(column),
                    "source_row": row_number,
                }
            )
    return {
        "format_version": 1,
        "source": path.relative_to(project_root).as_posix(),
        "source_sha256": sha256_file(path),
        "counts": {
            category: sum(entity["category"] == category for entity in entities)
            for category in CATEGORY_BY_COLUMN.values()
        },
        "entities": entities,
    }
