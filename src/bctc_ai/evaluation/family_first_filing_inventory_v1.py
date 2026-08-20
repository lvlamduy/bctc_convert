"""Read the tracked eight-bank filing matrix for family-first evaluation.

The Markdown inventory is the human-readable source of truth.  This reader
turns only its selected filing links into a typed provenance axis; it does not
use bank, path, period, scope, or assurance metadata for family matching.
Those fields remain available solely for coverage accounting and joining a
validated family result back to its source filing.
"""

from __future__ import annotations

import hashlib
import re
import stat
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

__all__ = [
    "INVENTORY_PATH",
    "FamilyFirstFilingInventoryV1Error",
    "read_family_first_filing_inventory_v1",
]


INVENTORY_PATH = Path("docs/experiments/FINANCIAL_REPORT_INVENTORY_8BANK.md")
_BANKS = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_HEADING = re.compile(r"^### (ACB|MBB|VPB|HDB|VCB|CTG|BID|VIB) — (20[0-9]{2})$")
_LINK = re.compile(r"\[[^]]+\]\(<\.\./\.\./(vietstock_bctc/[^>]+\.pdf)>\)")
_ASSURANCE = re.compile(r"\*\*(Kiểm toán|Soát xét|Không kiểm toán)\*\*")
_SNAPSHOT = re.compile(r"`(s3://[^`]+/snapshots/[^`]+/)`")
_PERIODS = {
    "Năm 2025": "ANNUAL",
    "H1 soát xét": "H1",
    "Q1": "Q1",
    "Q2": "Q2",
    "Q3": "Q3",
    "Q4": "Q4",
}
_SCOPES = ("CONSOLIDATED", "PARENT_OR_SEPARATE")


class FamilyFirstFilingInventoryV1Error(ValueError):
    """The tracked inventory or one selected local filing drifted."""


def _error(message: str) -> FamilyFirstFilingInventoryV1Error:
    return FamilyFirstFilingInventoryV1Error(message)


def _stable_regular_file(path: Path) -> tuple[bytes, os_stat_result]:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise _error(f"inventory source must be one single-link regular file: {path}")
    payload = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or len(payload) != before.st_size:
        raise _error(f"inventory source changed while being read: {path}")
    return payload, before


# Keep the return annotation readable without importing the platform-private
# concrete stat_result class under a public name.
os_stat_result = Any


def _safe_source_path(project_root: Path, relative: str) -> Path:
    supplied = Path(relative)
    if (
        supplied.is_absolute()
        or ".." in supplied.parts
        or len(supplied.parts) < 4
        or supplied.parts[0] != "vietstock_bctc"
        or supplied.suffix.casefold() != ".pdf"
    ):
        raise _error(f"inventory filing path is unsafe: {relative}")
    cursor = project_root
    for component in supplied.parts[:-1]:
        cursor /= component
        metadata = cursor.stat(follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode):
            raise _error(f"inventory filing parent is not one nofollow directory: {cursor}")
    path = project_root / supplied
    metadata = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise _error(f"inventory filing is not one single-link regular file: {relative}")
    return path


def _period(label: str, year: int) -> str:
    if label == f"Năm {year}":
        return "ANNUAL"
    result = _PERIODS.get(label)
    if result is None:
        raise _error(f"inventory period label is unsupported: {label}")
    return result


def _selected_record(
    *,
    project_root: Path,
    bank: str,
    year: int,
    period_label: str,
    scope: str,
    cell: str,
) -> dict[str, Any] | None:
    links = _LINK.findall(cell)
    if not links:
        if "CHƯA CÓ" not in cell:
            raise _error("inventory matrix cell is neither selected nor explicitly missing")
        return None
    if len(links) != 1:
        raise _error("inventory matrix cell must select exactly one filing")
    assurance_matches = _ASSURANCE.findall(cell)
    if len(assurance_matches) != 1:
        raise _error("selected inventory cell must expose one assurance state")
    relative = links[0]
    path = _safe_source_path(project_root, relative)
    payload, metadata = _stable_regular_file(path)
    if not payload.startswith(b"%PDF-"):
        raise _error(f"selected inventory source lacks a PDF signature: {relative}")
    return {
        "assurance": {
            "Kiểm toán": "AUDITED",
            "Soát xét": "REVIEWED",
            "Không kiểm toán": "UNAUDITED",
        }[assurance_matches[0]],
        "bank_provenance": bank,
        "content_ref": {
            "path": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": metadata.st_size,
        },
        "period": _period(period_label, year),
        "scope": scope,
        "year": year,
    }


def read_family_first_filing_inventory_v1(project_root: Path) -> dict[str, Any]:
    """Read and authenticate the selected 140-filing family-first axis."""

    if not isinstance(project_root, Path):
        raise _error("project root must be one pathlib Path")
    root = project_root.resolve()
    inventory_path = root / INVENTORY_PATH
    inventory_bytes, inventory_stat = _stable_regular_file(inventory_path)
    try:
        text = inventory_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _error("tracked filing inventory is not strict UTF-8") from exc
    snapshot_matches = _SNAPSHOT.findall(text)
    if len(snapshot_matches) != 1:
        raise _error("tracked filing inventory must bind one S3 snapshot prefix")

    records: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    current_bank: str | None = None
    current_year: int | None = None
    for line in text.splitlines():
        heading = _HEADING.fullmatch(line)
        if heading is not None:
            current_bank = heading.group(1)
            current_year = int(heading.group(2))
            continue
        if (
            current_bank is None
            or current_year is None
            or not line.startswith("|")
            or line.startswith("|---")
            or line.startswith("| Kỳ ")
        ):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3:
            continue
        period_label = cells[0]
        if period_label not in _PERIODS and period_label != f"Năm {current_year}":
            continue
        for scope, cell in zip(_SCOPES, cells[1:], strict=True):
            record = _selected_record(
                project_root=root,
                bank=current_bank,
                year=current_year,
                period_label=period_label,
                scope=scope,
                cell=cell,
            )
            if record is None:
                missing.append(
                    {
                        "bank_provenance": current_bank,
                        "period": _period(period_label, current_year),
                        "scope": scope,
                        "year": current_year,
                    }
                )
            else:
                records.append(record)

    keys = [
        (item["bank_provenance"], item["year"], item["period"], item["scope"]) for item in records
    ]
    if len(records) != 140 or len(keys) != len(set(keys)):
        raise _error("tracked family-first filing denominator or logical identities drifted")
    if tuple(sorted({item["bank_provenance"] for item in records})) != tuple(sorted(_BANKS)):
        raise _error("tracked family-first bank axis drifted")
    if len(missing) != 4:
        raise _error("tracked family-first explicit-missing denominator drifted")
    return canonical_clone_v1(
        {
            "authority": {
                "bank_path_period_scope_used_for_family_matching": False,
                "inventory_is_provenance_and_coverage_axis_only": True,
                "related_party_family_in_scope": False,
            },
            "filings": records,
            "format_version": "FAMILY_FIRST_FILING_INVENTORY_PROJECTION_V1",
            "inventory_ref": {
                "path": INVENTORY_PATH.as_posix(),
                "sha256": hashlib.sha256(inventory_bytes).hexdigest(),
                "size_bytes": inventory_stat.st_size,
            },
            "metrics": {
                "explicit_missing_filing_count": len(missing),
                "selected_filing_count": len(records),
            },
            "missing_filings": missing,
            "s3_snapshot_prefix": snapshot_matches[0],
        }
    )
