"""Deterministic content-unique 2024 BCTC universe for all 27 banks."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date
from html import escape
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "BANK_FILING_UNIVERSE_27BANK_2024_V1"
SOURCE_FORMAT_VERSION = "BANK_CORPUS_SURVEY_INVENTORY_RESULT_V1"
REPORTING_YEAR = 2024


class BankFilingUniverse2024V1Error(ValueError):
    """The registered source inventory cannot support the sealed 2024 universe."""


def _error(message: str) -> BankFilingUniverse2024V1Error:
    return BankFilingUniverse2024V1Error(message)


def _checked_banks(values: tuple[str, ...]) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or len(values) != 27
        or values != tuple(sorted(set(values)))
        or any(type(value) is not str or not value or value != value.upper() for value in values)
    ):
        raise _error("2024 universe requires 27 sorted unique uppercase bank codes")
    return values


def _checked_date(value: str) -> date:
    if type(value) is not str:
        raise _error("as-of date must be one ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _error("as-of date is invalid") from exc
    if parsed.isoformat() != value or parsed < date(REPORTING_YEAR, 12, 31):
        raise _error("as-of date predates the complete 2024 reporting year")
    return parsed


def _checked_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise _error("source inventory document is not an object")
    required = {
        "bank",
        "dataset_role",
        "document_id",
        "duplicate_content_path_count",
        "filename_metadata",
        "relative_path",
        "sha256",
        "size_bytes",
        "source_survey_status",
        "year",
    }
    if set(value) != required:
        raise _error("source inventory document fields drifted")
    metadata = value["filename_metadata"]
    required_metadata = {
        "assurance_hint",
        "document_kind",
        "document_kind_evidence",
        "language_hint",
        "metadata_authority",
        "normalized_filename",
        "reporting_period_hint",
        "reporting_year",
        "scope_hint",
        "source_type_hint",
    }
    if not isinstance(metadata, Mapping) or set(metadata) != required_metadata:
        raise _error("source inventory filename metadata drifted")
    bank = value["bank"]
    year = value["year"]
    path = value["relative_path"]
    digest = value["sha256"]
    size = value["size_bytes"]
    if (
        type(bank) is not str
        or type(year) is not int
        or type(path) is not str
        or not path.startswith(f"vietstock_bctc/{bank}/{year}/")
        or not path.casefold().endswith(".pdf")
        or path.startswith("/")
        or ".." in path.split("/")
        or "\\" in path
    ):
        raise _error("source inventory bank/year/path binding is invalid")
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or value["document_id"] != f"sha256:{digest}"
        or type(size) is not int
        or size <= 0
        or metadata["reporting_year"] != year
        or metadata["metadata_authority"] != "FILENAME_DERIVED_NON_AUTHORITATIVE"
    ):
        raise _error("source inventory content or metadata identity is invalid")
    return canonical_clone_v1(dict(value))


def _duplicate_preference(document: Mapping[str, Any]) -> tuple[Any, ...]:
    metadata = document["filename_metadata"]
    searchable = int(metadata["source_type_hint"] == "SEARCHABLE_FILENAME_HINT")
    basename = document["relative_path"].rsplit("/", 1)[-1]
    return (searchable, len(basename), document["relative_path"])


def build_bank_filing_universe_2024_v1(
    source_inventory: Mapping[str, Any],
    *,
    bank_codes: tuple[str, ...],
    as_of_date: str,
    source_inventory_ref: Mapping[str, Any],
    source_snapshot_manifest_uri: str,
) -> dict[str, Any]:
    """Select every content-unique Vietnamese full-BCTC candidate from 2024."""

    banks = _checked_banks(bank_codes)
    through = _checked_date(as_of_date)
    if (
        not isinstance(source_inventory, Mapping)
        or source_inventory.get("format_version") != SOURCE_FORMAT_VERSION
        or source_inventory.get("status") != "COMPLETE_REGISTERED_BANK_PDF_METADATA_INVENTORY"
        or type(source_inventory.get("documents")) is not list
    ):
        raise _error("source inventory identity or completion state drifted")
    if not isinstance(source_inventory_ref, Mapping) or set(source_inventory_ref) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        raise _error("source inventory reference fields drifted")
    if (
        type(source_snapshot_manifest_uri) is not str
        or not source_snapshot_manifest_uri.startswith("s3://")
        or "/snapshots/" not in source_snapshot_manifest_uri
        or not source_snapshot_manifest_uri.endswith(".json")
    ):
        raise _error("source snapshot manifest URI is invalid")

    checked = [_checked_document(item) for item in source_inventory["documents"]]
    requested = [
        item for item in checked if item["bank"] in banks and item["year"] == REPORTING_YEAR
    ]
    if {item["bank"] for item in requested} != set(banks):
        raise _error("registered 2024 source paths do not represent all 27 banks")
    eligible = [
        item
        for item in requested
        if item["filename_metadata"]["document_kind"] == "FULL_FINANCIAL_STATEMENT_CANDIDATE"
        and item["filename_metadata"]["language_hint"] == "VI"
    ]
    by_digest: dict[str, list[dict[str, Any]]] = {}
    for item in eligible:
        by_digest.setdefault(item["sha256"], []).append(item)

    selected: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for digest, group in sorted(by_digest.items()):
        ranked = sorted(group, key=_duplicate_preference)
        kept = ranked[0]
        metadata = kept["filename_metadata"]
        flags = []
        if metadata["scope_hint"] in {"UNKNOWN", "AMBIGUOUS"}:
            flags.append("SCOPE_REQUIRES_SOURCE_AUTHENTICATION")
        if metadata["reporting_period_hint"] in {"UNKNOWN", "AMBIGUOUS"}:
            flags.append("PERIOD_REQUIRES_SOURCE_AUTHENTICATION")
        if metadata["assurance_hint"] in {"UNKNOWN", "AMBIGUOUS"}:
            flags.append("ASSURANCE_REQUIRES_SOURCE_AUTHENTICATION")
        selected.append(
            {
                "bank": kept["bank"],
                "content_ref": {
                    "path": kept["relative_path"],
                    "sha256": digest,
                    "size_bytes": kept["size_bytes"],
                },
                "filename_hints_non_authoritative": {
                    "assurance": metadata["assurance_hint"],
                    "period": metadata["reporting_period_hint"],
                    "scope": metadata["scope_hint"],
                },
                "provider_disposition": "NEW_VERTEX_FLEX_FRONTIER",
                "source_authentication_flags": flags,
                "year": REPORTING_YEAR,
            }
        )
        duplicates.extend(
            {
                "kept_path": kept["relative_path"],
                "omitted_path": duplicate["relative_path"],
                "sha256": digest,
            }
            for duplicate in ranked[1:]
        )
    selected.sort(key=lambda item: (item["bank"], item["content_ref"]["path"]))
    if {item["bank"] for item in selected} != set(banks):
        raise _error("eligible 2024 candidates do not represent all 27 banks")

    selected_paths = {item["content_ref"]["path"] for item in selected}
    duplicate_paths = {item["omitted_path"] for item in duplicates}
    excluded = Counter()
    for item in requested:
        if item["relative_path"] in selected_paths:
            continue
        metadata = item["filename_metadata"]
        if metadata["document_kind"] != "FULL_FINANCIAL_STATEMENT_CANDIDATE":
            excluded[metadata["document_kind"]] += 1
        elif metadata["language_hint"] != "VI":
            excluded["NON_VI_FULL_FINANCIAL_STATEMENT"] += 1
        elif item["relative_path"] in duplicate_paths:
            excluded["EXACT_DUPLICATE_CONTENT"] += 1
        else:
            raise _error("one registered 2024 source lacks an exhaustive disposition")

    material = {
        "as_of_date": through.isoformat(),
        "authority": {
            "filename_hints_used_as_accounting_evidence": False,
            "provider_route_authorized_here": False,
            "selection_rule": (
                "ALL_2024_VIETNAMESE_FULL_FINANCIAL_STATEMENT_CANDIDATES_EXACT_CONTENT_DEDUPLICATED"
            ),
            "source_visible_metadata_authentication_required": True,
        },
        "bank_codes": list(banks),
        "exact_duplicate_contents": duplicates,
        "excluded_counts": dict(sorted(excluded.items())),
        "filings": selected,
        "format_version": FORMAT_VERSION,
        "reporting_year": REPORTING_YEAR,
        "source_inventory_ref": canonical_clone_v1(dict(source_inventory_ref)),
        "source_snapshot_manifest_uri": source_snapshot_manifest_uri,
        "summary": {
            "bank_count": len(banks),
            "candidate_filing_count": len(selected),
            "candidate_source_bytes": sum(item["content_ref"]["size_bytes"] for item in selected),
            "exact_duplicate_path_count": len(duplicates),
            "registered_pdf_path_count": len(requested),
            "source_authentication_required_count": sum(
                bool(item["source_authentication_flags"]) for item in selected
            ),
        },
    }
    return {
        **material,
        "universe_id": "bankfiling2024v1:" + canonical_json_sha256_v1(material),
    }


def render_bank_filing_universe_2024_markdown_v1(universe: dict[str, Any]) -> str:
    """Render one human-readable 2024 source matrix after local authentication."""

    filings = universe.get("filings") if type(universe) is dict else None
    if type(filings) is not list or any(
        type(item.get("page_count")) is not int for item in filings
    ):
        raise _error("authenticated 2024 filing universe is required for rendering")
    by_bank: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for filing in filings:
        by_bank[filing["bank"]].append(filing)
    lines = [
        "# Ma trận nguồn BCTC 27 ngân hàng năm 2024",
        "",
        (
            "Đây là danh sách ứng viên nguồn đã xác thực byte/trang, chưa phải kết quả "
            "Gemini hay mapping schema. Tên file chỉ là gợi ý không có thẩm quyền kế toán."
        ),
        "",
        "## Tổng quan",
        "",
        "| Chỉ tiêu | Số lượng |",
        "|---|---:|",
        f"| Mã ngân hàng | {universe['summary']['bank_count']:,} |",
        f"| PDF đăng ký năm 2024 | {universe['summary']['registered_pdf_path_count']:,} |",
        f"| PDF BCTC tiếng Việt content-unique | {universe['summary']['candidate_filing_count']:,} |",
        f"| Trang nguồn trước language cutoff | {universe['summary']['candidate_page_count']:,} |",
        f"| Đường dẫn trùng nội dung đã loại | {universe['summary']['exact_duplicate_path_count']:,} |",
        "",
        "## Tiến độ theo mã",
        "",
        "| STT | Mã | PDF ứng viên | Trang nguồn | PDF trên 100 trang |",
        "|---:|---|---:|---:|---:|",
    ]
    for ordinal, bank in enumerate(universe["bank_codes"], 1):
        rows = by_bank[bank]
        lines.append(
            f"| {ordinal} | {bank} | {len(rows)} | "
            f"{sum(item['page_count'] for item in rows):,} | "
            f"{sum(item['page_count'] > 100 for item in rows)} |"
        )
    lines.extend(["", "## PDF cần kiểm tra", ""])
    for bank in universe["bank_codes"]:
        lines.extend(
            [
                f"### {bank}",
                "",
                "| File PDF | Trang | Kỳ | Phạm vi | Kiểm toán |",
                "|---|---:|---|---|---|",
            ]
        )
        for filing in sorted(by_bank[bank], key=lambda item: item["content_ref"]["path"]):
            path = filing["content_ref"]["path"]
            name = path.rsplit("/", 1)[-1]
            href = "../../" + path.replace(" ", "%20")
            hints = filing["filename_hints_non_authoritative"]
            lines.append(
                f"| [{escape(name)}](<{href}>) | {filing['page_count']} | "
                f"{hints['period']} | {hints['scope']} | {hints['assurance']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Trạng thái",
            "",
            "- File chưa qua language cutoff không được đưa vào paid ledger.",
            "- `NOT_OBSERVED` chỉ được kết luận sau khi Gemini và family evaluator đọc đúng phạm vi.",
            "- `UNRESOLVED` và `SOURCE_ONLY` không được suy ra từ tên file.",
            "",
        ]
    )
    return "\n".join(lines)
