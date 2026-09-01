"""Read-only adapters for the family result store and canonical Gemini page store."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)

from .constants import (
    FAMILY_ORDER,
    STATUS_NAMES_VI,
    VALUE_STATE_NAMES_VI,
    family_name,
    reason_name,
    status_bucket,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_RESULTS_DATABASES = (
    Path(
        "/tmp/gemini-json-first-corpus-production-v2/artifacts/"
        "current-family-results/family-results.sqlite3"
    ),
)
_DEFAULT_PAGE_DATABASES = (
    Path(
        "/tmp/gemini-json-first-corpus-production-v2/artifacts/"
        "current-corpus-freeze-inputs/"
        "store-5962a19e86001f2effed5d954808a707ee43e562b807f40511bb19df772d3c1b.sqlite3"
    ),
)
_DEFAULT_PDF_ROOTS = (
    Path("/tmp/f3-final-remediation-compose.vFeCcM/worktree/vietstock_bctc"),
    Path("/tmp/f12-family-first.9s7arm/worktree/vietstock_bctc"),
    _PROJECT_ROOT / "vietstock_bctc",
)
_PERIOD_PATTERNS = (
    (re.compile(r"qu[ýy]\s*1", re.IGNORECASE), "Q1", "Quý 1"),
    (re.compile(r"qu[ýy]\s*2", re.IGNORECASE), "Q2", "Quý 2"),
    (re.compile(r"qu[ýy]\s*3", re.IGNORECASE), "Q3", "Quý 3"),
    (re.compile(r"qu[ýy]\s*4", re.IGNORECASE), "Q4", "Quý 4"),
    (re.compile(r"6\s*th[áa]ng|b[áa]n\s*ni[êe]n", re.IGNORECASE), "H1", "6 tháng"),
    (re.compile(r"(?:^|\D)1q(?:20\d{2})", re.IGNORECASE), "Q1", "Quý 1"),
    (re.compile(r"(?:^|\D)2q(?:20\d{2})", re.IGNORECASE), "Q2", "Quý 2"),
    (re.compile(r"(?:^|\D)3q(?:20\d{2})", re.IGNORECASE), "Q3", "Quý 3"),
    (re.compile(r"(?:^|\D)4q(?:20\d{2})", re.IGNORECASE), "Q4", "Quý 4"),
)

_LOAN_ENTERPRISE_CURRENT_POLICY_ROLES = {
    "COMBINED_JOINT_STOCK_LLC_PRIVATE_ENTERPRISE_LOANS",
    "COOPERATIVE_AND_COOPERATIVE_UNION_LOANS",
    "HOUSEHOLD_AND_INDIVIDUAL_LOANS",
    "OTHER_ENTERPRISE_LOANS",
}


def _configured_path(variable: str, candidates: Iterable[Path]) -> Path | None:
    explicit = os.environ.get(variable)
    if explicit:
        return Path(explicit).expanduser().resolve(strict=False)
    return next((candidate.resolve() for candidate in candidates if candidate.exists()), None)


@dataclass(frozen=True)
class ReviewSettings:
    """Paths needed by the read-only review application."""

    results_database: Path | None
    page_database: Path | None
    pdf_root: Path | None
    schema_path: Path
    cache_directory: Path

    @classmethod
    def from_environment(cls) -> ReviewSettings:
        cache = Path(
            os.environ.get("BCTC_REVIEW_CACHE_DIR", "/tmp/bctc-ai-review-page-cache")
        ).expanduser()
        return cls(
            results_database=_configured_path("BCTC_FAMILY_RESULTS_DB", _DEFAULT_RESULTS_DATABASES),
            page_database=_configured_path("BCTC_PAGE_STORE_DB", _DEFAULT_PAGE_DATABASES),
            pdf_root=_configured_path("BCTC_PDF_ROOT", _DEFAULT_PDF_ROOTS),
            schema_path=Path(
                os.environ.get(
                    "BCTC_SCHEMA_PATH", str(_PROJECT_ROOT / "reference/schemas/schema_graph.jsonl")
                )
            ).expanduser(),
            cache_directory=cache,
        )


def _json_load(value: bytes | str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return default


def _read_only_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _ordinal(value: Any, prefix: str) -> int | None:
    if isinstance(value, int):
        return value
    match = re.fullmatch(rf"{prefix}(\d+)", str(value or ""), re.IGNORECASE)
    return int(match.group(1)) if match else None


def _leaf(values: Any) -> str | None:
    if not isinstance(values, list):
        return None
    for value in reversed(values):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _header_label(values: Any) -> str | None:
    """Preserve the complete visible column hierarchy, including date and unit."""

    if not isinstance(values, list):
        return None
    lines: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        for line in value.splitlines():
            normalized = line.strip()
            if normalized and normalized not in lines:
                lines.append(normalized)
    return "\n".join(lines) if lines else None


def _semantic_label(value: Any) -> str:
    """Fold a human label for conservative exact-alias comparison."""

    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    folded = without_marks.casefold().replace("đ", "d")
    folded = re.sub(r"^\s*[+\-–—]*\s*", "", folded)
    folded = re.sub(r"^\s*(?:[ivxlcdm]+|\d+(?:\.\d+)*)[.)]?\s+", "", folded)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())


def _has_visible_value(values: Any) -> bool:
    return isinstance(values, list) and any(
        value is not None and str(value).strip() for value in values
    )


def _collect_page_refs(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("page_json_version_id"):
            yield {
                "page_json_version_id": value["page_json_version_id"],
                "physical_page": value.get("physical_page"),
                "section_id": value.get("section_id"),
                "table_id": value.get("table_id"),
                "row_id": value.get("row_id"),
                "column_id": value.get("column_id"),
            }
        for child in value.values():
            yield from _collect_page_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _collect_page_refs(child)


def _document_metadata(source_logical_name: str) -> dict[str, str]:
    normalized = source_logical_name.replace("\\", "/")
    parts = normalized.split("/")
    filename = parts[-1]
    bank = parts[-3].upper() if len(parts) >= 3 else "KHÁC"
    path_year = parts[-2] if len(parts) >= 2 and parts[-2].isdigit() else ""
    year_match = re.search(r"\b(20\d{2})\b", filename)
    year = path_year or (year_match.group(1) if year_match else "Không rõ")

    period_code, period_label = "ANNUAL", "Năm"
    for pattern, code, label in _PERIOD_PATTERNS:
        if pattern.search(filename):
            period_code, period_label = code, label
            break
    # A few VPB source filenames contain only a bundle ordinal. These names are
    # stable in the authenticated corpus, so make their human filter explicit
    # instead of incorrectly presenting every file as an annual report.
    if bank == "VPB" and period_code == "ANNUAL":
        vp_name = filename.casefold()
        if year == "2025" and vp_name in {"1-bctc-hop-nhat.pdf", "2-bctc-rieng-le.pdf"}:
            period_code, period_label = "Q3", "Quý 3"
        elif year == "2025" and vp_name in {
            "bctc-hop-nhat-1901.pdf",
            "bctc-rieng-le.pdf",
        }:
            period_code, period_label = "Q4", "Quý 4"
        elif year == "2026" and vp_name in {
            "1.-bctc-hop-nhat.pdf",
            "2.-bctc-rieng-le.pdf",
        }:
            period_code, period_label = "Q1", "Quý 1"
        elif year == "2026" and vp_name in {
            "3-bctc-hop-nhat-ban-tra-cuu.pdf",
            "4-bctc-rieng-le-ban-tra-cuu.pdf",
        }:
            period_code, period_label = "Q2", "Quý 2"

    lower = filename.casefold()
    if "hợp nhất" in lower or "hop nhat" in lower:
        scope_code, scope_label = "CONSOLIDATED", "Hợp nhất"
    elif "công ty mẹ" in lower or "cong ty me" in lower:
        scope_code, scope_label = "PARENT", "Công ty mẹ"
    elif "riêng" in lower or "rieng" in lower:
        scope_code, scope_label = "SEPARATE", "Riêng lẻ"
    else:
        scope_code, scope_label = "UNKNOWN", "Chưa xác định"

    if "kiểm toán" in lower or "kiem toan" in lower:
        assurance_code, assurance_label = "AUDITED", "Kiểm toán"
    elif "soát xét" in lower or "soat xet" in lower:
        assurance_code, assurance_label = "REVIEWED", "Soát xét"
    else:
        assurance_code, assurance_label = "UNAUDITED", "Chưa kiểm toán"

    return {
        "bank": bank,
        "year": year,
        "period_code": period_code,
        "period_label": f"{period_label} {year}",
        "scope_code": scope_code,
        "scope_label": scope_label,
        "assurance_code": assurance_code,
        "assurance_label": assurance_label,
        "filename": filename,
        "source_logical_name": source_logical_name,
    }


class ReviewRepository:
    """Query and normalize immutable Family results for the browser."""

    def __init__(self, settings: ReviewSettings):
        self.settings = settings
        self._schema_names = self._load_schema_names(settings.schema_path)
        self._spec_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _load_schema_names(path: Path) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        if not path.exists():
            return result
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = _json_load(line, {})
                schema_id = record.get("schema_id")
                if isinstance(schema_id, int):
                    result[schema_id] = {
                        "name": record.get("canonical_name") or f"ReportNormId {schema_id}",
                        "parent_id": record.get("parent_id"),
                        "statement_type": record.get("statement_type"),
                        "children": record.get("children") or [],
                        "display_order": record.get("display_order"),
                        "hierarchy_level": record.get("hierarchy_level"),
                    }
        return result

    @property
    def ready(self) -> bool:
        return bool(
            self.settings.results_database
            and self.settings.results_database.exists()
            and self.settings.page_database
            and self.settings.page_database.exists()
        )

    def configuration_status(self) -> dict[str, Any]:
        return {
            "results_database": bool(
                self.settings.results_database and self.settings.results_database.exists()
            ),
            "page_database": bool(
                self.settings.page_database and self.settings.page_database.exists()
            ),
            "pdf_root": bool(self.settings.pdf_root and self.settings.pdf_root.exists()),
            "schema": self.settings.schema_path.exists(),
            "ready": self.ready,
        }

    def _results(self) -> sqlite3.Connection:
        if not self.settings.results_database or not self.settings.results_database.exists():
            raise FileNotFoundError("Chưa cấu hình BCTC_FAMILY_RESULTS_DB hợp lệ")
        return _read_only_connection(self.settings.results_database)

    def _pages(self) -> sqlite3.Connection:
        if not self.settings.page_database or not self.settings.page_database.exists():
            raise FileNotFoundError("Chưa cấu hình BCTC_PAGE_STORE_DB hợp lệ")
        return _read_only_connection(self.settings.page_database)

    def families(self) -> list[dict[str, Any]]:
        with self._results() as connection:
            rows = connection.execute(
                """
                SELECT selection.family_id, run.document_count, run.ready_count,
                       run.not_observed_count, run.unresolved_count, run.mapping_count
                FROM family_current_selection AS selection
                JOIN family_run AS run USING (family_run_id)
                ORDER BY selection.family_id
                """
            ).fetchall()
        order_by_family = {
            family_id: index for index, family_id in enumerate(FAMILY_ORDER, start=1)
        }
        families = [
            {
                "id": row["family_id"],
                "name": family_name(row["family_id"]),
                "order": order_by_family.get(row["family_id"], len(FAMILY_ORDER) + 1),
                "document_count": row["document_count"],
                "ready_count": row["ready_count"],
                "not_observed_count": row["not_observed_count"],
                "unresolved_count": row["unresolved_count"],
                "mapping_count": row["mapping_count"],
            }
            for row in rows
        ]
        return sorted(families, key=lambda item: (item["order"], item["name"]))

    def _document_rows(self, family_id: str) -> list[sqlite3.Row]:
        with self._results() as connection:
            return connection.execute(
                """
                SELECT trial.document_ordinal, trial.source_logical_name,
                       trial.source_sha256, trial.status, trial.candidate_count,
                       trial.mapping_count, trial.reasons_json
                FROM family_current_selection AS selection
                JOIN family_trial AS trial USING (family_run_id)
                WHERE selection.family_id = ?
                ORDER BY trial.document_ordinal
                """,
                (family_id,),
            ).fetchall()

    def options(self) -> dict[str, Any]:
        families = self.families()
        family_id = (
            "LOAN_QUALITY_CLASSIFICATION"
            if any(item["id"] == "LOAN_QUALITY_CLASSIFICATION" for item in families)
            else families[0]["id"]
            if families
            else ""
        )
        rows = self._document_rows(family_id) if family_id else []
        metadata = [_document_metadata(row["source_logical_name"]) for row in rows]
        return {
            "families": families,
            "banks": sorted({item["bank"] for item in metadata}),
            "years": sorted({item["year"] for item in metadata}, reverse=True),
            "periods": [
                {"id": code, "name": label}
                for code, label in (
                    ("Q1", "Quý 1"),
                    ("Q2", "Quý 2"),
                    ("Q3", "Quý 3"),
                    ("Q4", "Quý 4"),
                    ("H1", "6 tháng"),
                    ("ANNUAL", "Năm"),
                )
            ],
            "scopes": [
                {"id": "CONSOLIDATED", "name": "Hợp nhất"},
                {"id": "SEPARATE", "name": "Riêng lẻ"},
                {"id": "PARENT", "name": "Công ty mẹ"},
                {"id": "UNKNOWN", "name": "Chưa xác định"},
            ],
            "assurance": [
                {"id": "AUDITED", "name": "Kiểm toán"},
                {"id": "REVIEWED", "name": "Soát xét"},
                {"id": "UNAUDITED", "name": "Chưa kiểm toán"},
            ],
            "default_family": family_id,
            "configuration": self.configuration_status(),
        }

    def documents(self, family_id: str, filters: dict[str, str]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        query = filters.get("query", "").strip().casefold()
        for row in self._document_rows(family_id):
            item = _document_metadata(row["source_logical_name"])
            if filters.get("bank") and item["bank"] != filters["bank"]:
                continue
            if filters.get("year") and item["year"] != filters["year"]:
                continue
            if filters.get("period") and item["period_code"] != filters["period"]:
                continue
            if filters.get("scope") and item["scope_code"] != filters["scope"]:
                continue
            if filters.get("assurance") and item["assurance_code"] != filters["assurance"]:
                continue
            normalized_status = status_bucket(row["status"])
            if filters.get("status") and normalized_status != filters["status"]:
                continue
            if query and query not in row["source_logical_name"].casefold():
                continue
            reasons = _json_load(row["reasons_json"], [])
            item.update(
                {
                    "source_sha256": row["source_sha256"],
                    "document_ordinal": row["document_ordinal"],
                    "status": normalized_status,
                    "raw_status": row["status"],
                    "status_label": STATUS_NAMES_VI.get(normalized_status, normalized_status),
                    "candidate_count": row["candidate_count"],
                    "mapping_count": row["mapping_count"],
                    "reasons": [reason_name(reason) for reason in reasons],
                }
            )
            documents.append(item)
        return documents

    def _trial(self, family_id: str, source_sha256: str) -> sqlite3.Row:
        with self._results() as connection:
            row = connection.execute(
                """
                SELECT trial.*, selection.family_run_id
                FROM family_current_selection AS selection
                JOIN family_trial AS trial USING (family_run_id)
                WHERE selection.family_id = ? AND trial.source_sha256 = ?
                """,
                (family_id, source_sha256),
            ).fetchone()
        if row is None:
            raise LookupError("Không tìm thấy PDF trong family đang chọn")
        return row

    def _family_specs(self, family_run_id: str) -> dict[str, Any]:
        """Read the human-relevant embedded family specifications once per run."""

        if family_run_id in self._spec_cache:
            return self._spec_cache[family_run_id]
        try:
            with self._results() as connection:
                row = connection.execute(
                    "SELECT sweep_bytes FROM family_run WHERE family_run_id = ?",
                    (family_run_id,),
                ).fetchone()
        except sqlite3.OperationalError:
            return {}
        sweep = _json_load(row["sweep_bytes"] if row else None, {})
        specs = sweep.get("specs") if isinstance(sweep, dict) else {}
        result: dict[str, Any] = {}
        for name in ("topology", "schema_binding"):
            envelope = specs.get(name) if isinstance(specs, dict) else None
            value = envelope.get("value") if isinstance(envelope, dict) else None
            if isinstance(value, dict):
                result[name] = value

        # The store remains the authority for persisted mappings.  Coverage review,
        # however, should also expose rows recognized by the latest tracked alias
        # policy so a human can distinguish "old run has not mapped this yet" from
        # "no matching schema row exists".
        family_id = result.get("topology", {}).get("family_id")
        if family_id == "LOAN_ENTERPRISE_FAMILY12":
            from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
                build_loan_enterprise_family12_topology_spec_v1,
            )

            topology = build_loan_enterprise_family12_topology_spec_v1()
            branch = next(
                child for child in topology["children"] if child["role"] == "ENTERPRISE_TYPE_BRANCH"
            )
            branch["matchers"][0]["aliases"].extend(
                ["Phân tích theo đối tượng khách hàng", "Theo đối tượng khách hàng"]
            )
            result["topology"] = topology
        elif family_id == "TRADING_SECURITIES":
            config_root = _PROJECT_ROOT / "config/families"
            for name, filename in (
                ("topology", "tm-trading-securities-topology-v1.json"),
                ("schema_binding", "tm-trading-securities-schema-binding-v1.json"),
            ):
                value = _json_load((config_root / filename).read_bytes(), {})
                if isinstance(value, dict):
                    result[name] = value
        self._spec_cache[family_run_id] = result
        return result

    def _candidate_payloads(
        self, family_run_id: str, document_ordinal: int
    ) -> list[dict[str, Any]]:
        with self._results() as connection:
            rows = connection.execute(
                """
                SELECT candidate_id, page_json_version_id, physical_page, section_id,
                       table_id, status, reason_count, mapping_count, candidate_bytes
                FROM family_candidate
                WHERE family_run_id = ? AND document_ordinal = ?
                ORDER BY physical_page, section_id, table_id, candidate_id
                """,
                (family_run_id, document_ordinal),
            ).fetchall()
        payloads = []
        for row in rows:
            payload = _json_load(row["candidate_bytes"], {})
            payload["_index"] = {
                key: row[key]
                for key in (
                    "candidate_id",
                    "page_json_version_id",
                    "physical_page",
                    "section_id",
                    "table_id",
                    "status",
                    "reason_count",
                    "mapping_count",
                )
            }
            payloads.append(payload)
        return payloads

    def _mapping_payloads(self, family_run_id: str, document_ordinal: int) -> list[dict[str, Any]]:
        with self._results() as connection:
            rows = connection.execute(
                """
                SELECT mapping_ordinal, report_norm_id, role, row_id, mapping_bytes
                FROM family_mapping
                WHERE family_run_id = ? AND document_ordinal = ?
                ORDER BY mapping_ordinal
                """,
                (family_run_id, document_ordinal),
            ).fetchall()
        payloads = []
        for row in rows:
            payload = _json_load(row["mapping_bytes"], {})
            payload.setdefault("report_norm_id", row["report_norm_id"])
            payload.setdefault("role", row["role"])
            payload.setdefault("row_id", row["row_id"])
            payload["mapping_ordinal"] = row["mapping_ordinal"]
            payloads.append(payload)
        return payloads

    def _page_payloads(
        self, source_sha256: str, page_refs: Iterable[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        version_ids = sorted(
            {
                str(ref["page_json_version_id"])
                for ref in page_refs
                if ref.get("page_json_version_id")
            }
        )
        if not version_ids:
            return []
        placeholders = ",".join("?" for _ in version_ids)
        with self._pages() as connection:
            rows = connection.execute(
                f"""
                SELECT version.page_json_version_id, version.page_status,
                       version.canonical_json_bytes, page.physical_page,
                       page.pixel_width AS width, page.pixel_height AS height,
                       document.source_logical_name, document.source_sha256
                FROM page_json_version AS version
                JOIN page USING (page_id)
                JOIN document USING (document_id)
                WHERE version.page_json_version_id IN ({placeholders})
                ORDER BY page.physical_page
                """,
                version_ids,
            ).fetchall()
        result = []
        for row in rows:
            if row["source_sha256"] != source_sha256:
                continue
            result.append(
                {
                    "page_json_version_id": row["page_json_version_id"],
                    "page_status": row["page_status"],
                    "physical_page": row["physical_page"],
                    "width": row["width"],
                    "height": row["height"],
                    "source_logical_name": row["source_logical_name"],
                    "canonical": _json_load(row["canonical_json_bytes"], {}),
                }
            )
        return result

    def _preceding_page_payloads(
        self, source_sha256: str, physical_pages: Iterable[int]
    ) -> list[dict[str, Any]]:
        """Load a unique immediately preceding page as bounded owner context."""

        target_pages = sorted({page - 1 for page in physical_pages if page > 1})
        if not target_pages:
            return []
        placeholders = ",".join("?" for _ in target_pages)
        with self._pages() as connection:
            rows = connection.execute(
                f"""
                SELECT version.page_json_version_id, version.page_status,
                       version.canonical_json_bytes, page.physical_page,
                       page.pixel_width AS width, page.pixel_height AS height,
                       document.source_logical_name, document.source_sha256
                FROM page_json_version AS version
                JOIN page USING (page_id)
                JOIN document USING (document_id)
                WHERE document.source_sha256 = ?
                  AND page.physical_page IN ({placeholders})
                ORDER BY page.physical_page, version.page_json_version_id
                """,
                [source_sha256, *target_pages],
            ).fetchall()
        rows_by_page: dict[int, list[sqlite3.Row]] = {}
        for row in rows:
            rows_by_page.setdefault(row["physical_page"], []).append(row)
        result = []
        for physical_page in target_pages:
            page_rows = rows_by_page.get(physical_page, [])
            if len(page_rows) != 1:
                continue
            row = page_rows[0]
            result.append(
                {
                    "page_json_version_id": row["page_json_version_id"],
                    "page_status": row["page_status"],
                    "physical_page": row["physical_page"],
                    "width": row["width"],
                    "height": row["height"],
                    "source_logical_name": row["source_logical_name"],
                    "canonical": _json_load(row["canonical_json_bytes"], {}),
                }
            )
        return result

    def _gemini_tables(
        self,
        pages: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        selected_candidate_id: str | None,
        mapping_refs: Iterable[dict[str, Any]] = (),
    ) -> list[dict[str, Any]]:
        candidate_by_ref = {
            (
                candidate.get("_index", {}).get("page_json_version_id"),
                candidate.get("_index", {}).get("section_id"),
                candidate.get("_index", {}).get("table_id"),
            ): candidate
            for candidate in candidates
            if candidate.get("_index", {}).get("table_id")
        }
        mapped_table_refs = {
            (
                ref.get("page_json_version_id"),
                ref.get("section_id"),
                ref.get("table_id"),
            )
            for ref in mapping_refs
            if ref.get("page_json_version_id") and ref.get("section_id") and ref.get("table_id")
        }
        tables: list[dict[str, Any]] = []
        for page in pages:
            canonical = page["canonical"]
            for section_index, section in enumerate(canonical.get("sections", []), start=1):
                section_id = f"s{section_index}"
                for table_index, table in enumerate(section.get("tables", []), start=1):
                    table_id = f"t{table_index}"
                    columns = []
                    for column_index, column in enumerate(table.get("columns", []), start=1):
                        columns.append(
                            {
                                "id": f"c{column_index}",
                                "label": _header_label(column.get("header_path_exact"))
                                or f"Cột {column_index}",
                                "value_kind": column.get("value_kind"),
                            }
                        )
                    rows = []
                    for row_index, row in enumerate(table.get("rows", []), start=1):
                        values = row.get("values_exact") or []
                        rows.append(
                            {
                                "id": f"r{row_index}",
                                "label": row.get("label_exact")
                                or _leaf(row.get("hierarchy_path_exact"))
                                or f"Dòng {row_index}",
                                "hierarchy": row.get("hierarchy_path_exact") or [],
                                "row_kind": row.get("row_kind"),
                                "values": [
                                    values[index] if index < len(values) else None
                                    for index in range(len(columns))
                                ],
                            }
                        )
                    reference = (page["page_json_version_id"], section_id, table_id)
                    candidate = candidate_by_ref.get(reference)
                    candidate_index = candidate.get("_index", {}) if candidate else {}
                    candidate_reasons = candidate.get("reasons") or [] if candidate else []
                    tables.append(
                        {
                            "key": ":".join(map(str, reference)),
                            "page_json_version_id": page["page_json_version_id"],
                            "physical_page": page["physical_page"],
                            "section_id": section_id,
                            "table_id": table_id,
                            "section_title": section.get("title_exact"),
                            "table_title": table.get("title_exact"),
                            "unit": table.get("unit_exact"),
                            "continuation": table.get("continuation"),
                            "columns": columns,
                            "rows": rows,
                            "selected": candidate_index.get("candidate_id")
                            == selected_candidate_id,
                            "candidate_id": candidate_index.get("candidate_id"),
                            "candidate_status": status_bucket(candidate_index.get("status") or ""),
                            "candidate_status_label": STATUS_NAMES_VI.get(
                                status_bucket(candidate_index.get("status") or ""),
                                candidate_index.get("status") or "Không phải bảng ứng viên",
                            ),
                            "candidate_reasons": candidate_reasons,
                            "candidate_reason_labels": [
                                reason_name(reason) for reason in candidate_reasons
                            ],
                        }
                    )
        candidate_tables = [
            table
            for table in tables
            if table["candidate_id"]
            or (table["page_json_version_id"], table["section_id"], table["table_id"])
            in mapped_table_refs
        ]
        return candidate_tables or tables

    def _normalized_mapping(
        self,
        mapping: dict[str, Any],
        default_locator: dict[str, Any] | None = None,
        physical_page_by_version: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        physical_page_by_version = physical_page_by_version or {}
        report_norm_id = mapping.get("report_norm_id")
        schema = self._schema_names.get(report_norm_id, {})
        raw_source_refs = (
            mapping.get("source_refs") if isinstance(mapping.get("source_refs"), list) else []
        )

        source_refs: list[dict[str, Any]] = []
        for source_ref in raw_source_refs:
            if not isinstance(source_ref, dict):
                continue
            source_cell = source_ref.get("cell") if isinstance(source_ref.get("cell"), dict) else {}
            locator = (
                source_ref.get("locator")
                if isinstance(source_ref.get("locator"), dict)
                else source_cell.get("source_locator")
                if isinstance(source_cell.get("source_locator"), dict)
                else {}
            )
            page_json_version_id = locator.get("page_json_version_id")
            source_refs.append(
                {
                    "page_json_version_id": page_json_version_id,
                    "physical_page": locator.get("physical_page")
                    or physical_page_by_version.get(str(page_json_version_id or "")),
                    "section_id": locator.get("section_id"),
                    "table_id": locator.get("table_id"),
                    "row_id": locator.get("row_id") or source_ref.get("row_id"),
                    "column_id": locator.get("column_id"),
                    "money_column_ordinals": source_ref.get("money_column_ordinals") or [],
                    "label_exact": source_ref.get("label_exact"),
                    "hierarchy_path_exact": source_ref.get("hierarchy_path_exact") or [],
                    "coefficient": source_cell.get("coefficient"),
                    "source_text": source_cell.get("source_text"),
                    "state": source_cell.get("state"),
                }
            )

        top_level_locator = (
            mapping.get("locator") if isinstance(mapping.get("locator"), dict) else {}
        )
        top_level_column_id = mapping.get("column_id")
        column_ordinal = mapping.get("column_ordinal")
        if not top_level_column_id and isinstance(column_ordinal, int) and column_ordinal > 0:
            top_level_column_id = f"c{column_ordinal}"
        if top_level_locator and mapping.get("row_id"):
            page_json_version_id = top_level_locator.get("page_json_version_id")
            source_refs.append(
                {
                    "page_json_version_id": page_json_version_id,
                    "physical_page": top_level_locator.get("physical_page")
                    or physical_page_by_version.get(str(page_json_version_id or "")),
                    "section_id": top_level_locator.get("section_id"),
                    "table_id": top_level_locator.get("table_id"),
                    "row_id": mapping.get("row_id"),
                    "column_id": top_level_column_id,
                    "label_exact": mapping.get("row_label_exact") or mapping.get("label_exact"),
                    "hierarchy_path_exact": mapping.get("row_hierarchy_path_exact") or [],
                    "coefficient": (mapping.get("cell") or {}).get("coefficient")
                    if isinstance(mapping.get("cell"), dict)
                    else None,
                    "source_text": (mapping.get("cell") or {}).get("source_text")
                    if isinstance(mapping.get("cell"), dict)
                    else None,
                    "state": (mapping.get("cell") or {}).get("state")
                    if isinstance(mapping.get("cell"), dict)
                    else None,
                }
            )

        source_label = (
            mapping.get("label_exact")
            or mapping.get("row_label_exact")
            or next(
                (
                    source_ref.get("label_exact")
                    for source_ref in source_refs
                    if source_ref.get("label_exact")
                ),
                None,
            )
            or _leaf(mapping.get("hierarchy_path_exact"))
            or mapping.get("role")
            or mapping.get("row_id")
        )
        columns = mapping.get("columns") if isinstance(mapping.get("columns"), list) else []
        raw_values = mapping.get("values") if isinstance(mapping.get("values"), list) else []
        if not raw_values and any(
            key in mapping for key in ("coefficient", "source_text", "state")
        ):
            raw_values = [mapping]
        if not raw_values and isinstance(mapping.get("cell"), dict):
            raw_values = [mapping["cell"]]
        values = []
        for index, value in enumerate(raw_values):
            if not isinstance(value, dict):
                continue
            cell_ref = value.get("cell_ref") if isinstance(value.get("cell_ref"), dict) else {}
            locator = cell_ref.get("locator") if isinstance(cell_ref.get("locator"), dict) else {}
            effective_locator = {
                **(default_locator or {}),
                **{key: item for key, item in top_level_locator.items() if item is not None},
                **{key: item for key, item in cell_ref.items() if item is not None},
                **{key: item for key, item in locator.items() if item is not None},
            }
            page_json_version_id = effective_locator.get("page_json_version_id")
            column = (
                columns[index] if index < len(columns) and isinstance(columns[index], dict) else {}
            )
            header = (
                value.get("period_end")
                or value.get("axis_role")
                or _header_label(column.get("header_path_exact"))
                or f"Giá trị {index + 1}"
            )
            values.append(
                {
                    "header": header,
                    "axis_role": value.get("axis_role"),
                    "period_end": value.get("period_end"),
                    "coefficient": value.get("coefficient"),
                    "source_text": value.get("source_text"),
                    "state": value.get("state"),
                    "state_label": VALUE_STATE_NAMES_VI.get(
                        value.get("state"),
                        str(value.get("state") or "Không có trạng thái kỹ thuật"),
                    ),
                    "physical_page": effective_locator.get("physical_page")
                    or physical_page_by_version.get(str(page_json_version_id or "")),
                    "page_json_version_id": page_json_version_id,
                    "section_id": effective_locator.get("section_id"),
                    "table_id": effective_locator.get("table_id"),
                    "row_id": cell_ref.get("row_id") or mapping.get("row_id"),
                    "column_id": cell_ref.get("column_id") or top_level_column_id,
                }
            )
        return {
            "mapping_ordinal": mapping.get("mapping_ordinal"),
            "report_norm_id": report_norm_id,
            "schema_name": schema.get("name") or f"ReportNormId {report_norm_id}",
            "schema_parent_id": schema.get("parent_id"),
            "schema_parent_name": self._schema_names.get(schema.get("parent_id"), {}).get("name"),
            "schema_display_order": schema.get("display_order"),
            "schema_parent_display_order": self._schema_names.get(schema.get("parent_id"), {}).get(
                "display_order"
            ),
            "schema_hierarchy_level": schema.get("hierarchy_level"),
            "role": mapping.get("role"),
            "row_id": mapping.get("row_id"),
            "source_label": source_label,
            "derived_from_row_ids": mapping.get("derived_from_row_ids") or [],
            "derived_from_roles": mapping.get("derived_from_roles") or [],
            "is_derived": bool(mapping.get("derived_from_row_ids"))
            or str(mapping.get("row_id") or "").startswith(("aggregate:", "corroborated:"))
            or len(source_refs) > 1,
            "unit": mapping.get("unit"),
            # Opening/closing roll-forward rows carry an exact endpoint in addition
            # to the report period. Prefer that visible date for the review header.
            "period_date": mapping.get("endpoint_date") or mapping.get("period_date"),
            "values": values,
            "source_locator": default_locator or {},
            "source_refs": source_refs,
        }

    @staticmethod
    def _attach_mapping_headers(
        mappings: list[dict[str, Any]], gemini_tables: list[dict[str, Any]]
    ) -> None:
        """Recover visible period/column headers from the exact source receipts."""

        tables = {
            (table["physical_page"], table["section_id"], table["table_id"]): table
            for table in gemini_tables
        }
        for mapping in mappings:
            period_date = mapping.get("period_date")
            date_label = None
            if isinstance(period_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_date):
                year, month, day = period_date.split("-")
                date_label = f"{day}.{month}.{year}"

            visible_headers: list[str] = []
            for source_ref in mapping.get("source_refs", []):
                table = tables.get(
                    (
                        source_ref.get("physical_page"),
                        source_ref.get("section_id"),
                        source_ref.get("table_id"),
                    )
                )
                if not table:
                    continue
                column_ids: list[str] = []
                if source_ref.get("column_id"):
                    column_ids.append(source_ref["column_id"])
                column_ids.extend(
                    f"c{ordinal}"
                    for ordinal in source_ref.get("money_column_ordinals", [])
                    if isinstance(ordinal, int)
                )
                columns = (
                    [column for column in table["columns"] if column["id"] in column_ids]
                    if column_ids
                    else [
                        column for column in table["columns"] if column.get("value_kind") == "MONEY"
                    ]
                )
                for column in columns:
                    label = column.get("label")
                    if label and label not in visible_headers:
                        visible_headers.append(label)

            for index, value in enumerate(mapping.get("values", [])):
                if not str(value.get("header") or "").startswith("Giá trị "):
                    continue
                visible = visible_headers[index] if index < len(visible_headers) else None
                if date_label and visible and date_label not in visible:
                    value["header"] = f"{date_label}\n{visible}"
                elif date_label:
                    value["header"] = date_label
                elif visible:
                    value["header"] = visible

    @staticmethod
    def _attach_derived_source_context(
        mappings: list[dict[str, Any]], gemini_tables: list[dict[str, Any]]
    ) -> None:
        """Join derived mappings to an unambiguous visible Gemini source row."""

        rows_by_id: dict[str, list[dict[str, Any]]] = {}
        for table in gemini_tables:
            for row in table["rows"]:
                rows_by_id.setdefault(row["id"], []).append(
                    {
                        "row_id": row["id"],
                        "label": row["label"],
                        "values": row["values"],
                        "physical_page": table["physical_page"],
                        "section_id": table["section_id"],
                        "table_id": table["table_id"],
                    }
                )
        for mapping in mappings:
            locator = mapping.get("source_locator") or {}
            source_rows = []
            for row_id in mapping["derived_from_row_ids"]:
                occurrences = rows_by_id.get(row_id, [])
                bounded = [
                    occurrence
                    for occurrence in occurrences
                    if (
                        not locator.get("physical_page")
                        or occurrence["physical_page"] == locator["physical_page"]
                    )
                    and (
                        not locator.get("section_id")
                        or occurrence["section_id"] == locator["section_id"]
                    )
                    and (
                        not locator.get("table_id") or occurrence["table_id"] == locator["table_id"]
                    )
                ]
                if len(bounded) == 1:
                    source_rows.append(bounded[0])
            mapping["derived_source_rows"] = source_rows
            if len(source_rows) != 1:
                continue
            source_row = source_rows[0]
            for index, value in enumerate(mapping["values"]):
                if value["source_text"] is None and index < len(source_row["values"]):
                    value["display_source_text"] = source_row["values"][index]
                    value["display_source_row_id"] = source_row["row_id"]
                    value["display_source_label"] = source_row["label"]

    @staticmethod
    def _trading_page_context(pages: list[dict[str, Any]]) -> dict[int, dict[str, bool]]:
        """Identify the visible family owner on each trading-security page."""

        direct: dict[int, dict[str, bool]] = {}
        for page in pages:
            surfaces: list[str] = []
            for section in page.get("canonical", {}).get("sections", []):
                surfaces.append(_semantic_label(section.get("title_exact")))
                surfaces.extend(
                    _semantic_label(table.get("title_exact")) for table in section.get("tables", [])
                )
            direct[page["physical_page"]] = {
                "trading": any("chung khoan kinh doanh" in surface for surface in surfaces),
                "investment": any("chung khoan dau tu" in surface for surface in surfaces),
            }
        result = {physical_page: dict(context) for physical_page, context in direct.items()}
        for physical_page in sorted(direct):
            context = direct[physical_page]
            preceding = direct.get(physical_page - 1)
            if not context["trading"] and not context["investment"] and preceding:
                result[physical_page] = dict(preceding)
        return result

    def _current_policy_mappings(
        self,
        family_id: str,
        pages: list[dict[str, Any]],
        gemini_tables: list[dict[str, Any]],
        mappings: list[dict[str, Any]],
        specs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Project exact tracked aliases that post-date the persisted review run.

        These rows are deliberately marked as a current-policy projection.  The
        persisted store remains immutable until the authenticated family replay,
        while the human review screen no longer hides an exact schema match.
        """

        if family_id not in {"TRADING_SECURITIES", "LOAN_ENTERPRISE_FAMILY12"}:
            return []
        catalog = self._role_catalog(specs)
        page_context = self._trading_page_context(pages)
        eligible_roles = (
            {
                role
                for role in catalog["report_norm_id_by_role"]
                if catalog["children"].get(role, {}).get("role_kind") != "STRUCTURAL_GROUP"
            }
            if family_id == "TRADING_SECURITIES"
            else _LOAN_ENTERPRISE_CURRENT_POLICY_ROLES
        )
        persisted_ids = {
            mapping.get("report_norm_id")
            for mapping in mappings
            if isinstance(mapping.get("report_norm_id"), int)
        }
        matches_by_role: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
        for table in gemini_tables:
            reasons = set(table.get("candidate_reasons") or [])
            if family_id == "TRADING_SECURITIES":
                context = page_context.get(table["physical_page"], {})
                if not context.get("trading") or context.get("investment"):
                    continue
                if table.get("candidate_status") not in {"READY", "UNRESOLVED"}:
                    continue
            elif table.get("candidate_status") != "READY" or reasons:
                continue

            active_group_role: str | None = None
            table_surfaces = {
                _semantic_label(table.get("table_title")),
                _semantic_label(table.get("section_title")),
            }
            structural_surface_roles = {
                role
                for role, child in catalog["children"].items()
                if child.get("role_kind") == "STRUCTURAL_GROUP"
                and table_surfaces.intersection(catalog["aliases_by_role"].get(role, set()))
            }
            if len(structural_surface_roles) == 1:
                active_group_role = next(iter(structural_surface_roles))
            for row in table["rows"]:
                role, ambiguity = self._row_role(row, catalog, active_group_role)
                child = catalog["children"].get(role, {}) if role else {}
                if child.get("role_kind") == "STRUCTURAL_GROUP":
                    active_group_role = role
                if ambiguity or role not in eligible_roles:
                    continue
                report_norm_id = catalog["report_norm_id_by_role"].get(role)
                if not isinstance(report_norm_id, int) or report_norm_id in persisted_ids:
                    continue
                matches_by_role.setdefault(role, []).append((table, row))

        projected: list[dict[str, Any]] = []
        for role in sorted(matches_by_role):
            matches = matches_by_role[role]
            if len(matches) != 1:
                continue
            table, row = matches[0]
            values: list[dict[str, Any]] = []
            safe = True
            money_columns = [
                (ordinal, column, row["values"][ordinal - 1])
                for ordinal, column in enumerate(table["columns"], start=1)
                if column.get("value_kind") == "MONEY"
            ]
            if not money_columns:
                continue
            for _ordinal, column, raw_value in money_columns:
                if raw_value is None or not str(raw_value).strip():
                    coefficient = None
                    state = "SOURCE_BLANK"
                else:
                    parsed = parse_visible_financial_numeric_token_v1(str(raw_value))
                    coefficient = parsed.get("coefficient")
                    if coefficient is None:
                        safe = False
                        break
                    state = (
                        "DASH_ZERO"
                        if parsed.get("classification") == "DASH_ZERO"
                        else "RAW_SIGNED_INTEGER"
                    )
                values.append(
                    {
                        "header": column["label"],
                        "axis_role": None,
                        "period_end": None,
                        "coefficient": coefficient,
                        "source_text": raw_value,
                        "state": state,
                        "state_label": VALUE_STATE_NAMES_VI[state],
                        "physical_page": table["physical_page"],
                        "page_json_version_id": table["page_json_version_id"],
                        "section_id": table["section_id"],
                        "table_id": table["table_id"],
                        "row_id": row["id"],
                        "column_id": column["id"],
                    }
                )
            if not safe:
                continue
            if not any(value["coefficient"] is not None for value in values):
                continue
            report_norm_id = catalog["report_norm_id_by_role"][role]
            schema = self._schema_names.get(report_norm_id, {})
            projected.append(
                {
                    "mapping_ordinal": (
                        f"current-policy:{report_norm_id}:p{table['physical_page']}:"
                        f"{table['section_id']}:{table['table_id']}:{row['id']}"
                    ),
                    "report_norm_id": report_norm_id,
                    "schema_name": schema.get("name") or f"ReportNormId {report_norm_id}",
                    "schema_parent_id": schema.get("parent_id"),
                    "schema_parent_name": self._schema_names.get(schema.get("parent_id"), {}).get(
                        "name"
                    ),
                    "schema_display_order": schema.get("display_order"),
                    "schema_parent_display_order": self._schema_names.get(
                        schema.get("parent_id"), {}
                    ).get("display_order"),
                    "schema_hierarchy_level": schema.get("hierarchy_level"),
                    "role": role,
                    "row_id": row["id"],
                    "source_label": row["label"],
                    "derived_from_row_ids": [],
                    "derived_from_roles": [],
                    "derived_source_rows": [],
                    "is_derived": False,
                    "unit": table.get("unit"),
                    "period_date": None,
                    "values": values,
                    "source_locator": {
                        "physical_page": table["physical_page"],
                        "page_json_version_id": table["page_json_version_id"],
                        "section_id": table["section_id"],
                        "table_id": table["table_id"],
                    },
                    "source_refs": [
                        {
                            "physical_page": table["physical_page"],
                            "page_json_version_id": table["page_json_version_id"],
                            "section_id": table["section_id"],
                            "table_id": table["table_id"],
                            "row_id": row["id"],
                            "column_id": None,
                            "money_column_ordinals": [
                                ordinal for ordinal, _column, _value in money_columns
                            ],
                            "label_exact": row["label"],
                            "hierarchy_path_exact": row["hierarchy"],
                            "coefficient": None,
                            "source_text": None,
                            "state": None,
                        }
                    ],
                    "policy_overlay": True,
                    "policy_overlay_label": (
                        "Đã map theo rule hiện hành; chờ replay để ghi vào kho kết quả"
                    ),
                }
            )
        return projected

    @staticmethod
    def _role_catalog(specs: dict[str, Any]) -> dict[str, Any]:
        topology = specs.get("topology") if isinstance(specs.get("topology"), dict) else {}
        binding = (
            specs.get("schema_binding") if isinstance(specs.get("schema_binding"), dict) else {}
        )
        report_norm_id_by_role = {
            item.get("role"): item.get("report_norm_id")
            for item in binding.get("role_bindings", [])
            if isinstance(item, dict)
            and isinstance(item.get("role"), str)
            and isinstance(item.get("report_norm_id"), int)
        }
        children = {
            item.get("role"): item
            for item in topology.get("children", [])
            if isinstance(item, dict) and isinstance(item.get("role"), str)
        }
        aliases_by_role: dict[str, set[str]] = {}
        for role, child in children.items():
            aliases_by_role[role] = {
                normalized
                for matcher in child.get("matchers", [])
                if isinstance(matcher, dict)
                for alias in matcher.get("aliases", [])
                if (normalized := _semantic_label(alias))
            }
        return {
            "family_report_norm_id": binding.get("family_report_norm_id")
            or binding.get("family_root_report_norm_id"),
            "report_norm_id_by_role": report_norm_id_by_role,
            "children": children,
            "aliases_by_role": aliases_by_role,
            "hard_negative_aliases": [
                normalized
                for alias in topology.get("hard_negative_aliases", [])
                if (normalized := _semantic_label(alias))
            ],
        }

    @staticmethod
    def _row_role(
        row: dict[str, Any], catalog: dict[str, Any], active_group_role: str | None
    ) -> tuple[str | None, str | None]:
        label = _semantic_label(row.get("label"))
        ancestors = {
            _semantic_label(value)
            for value in (row.get("hierarchy") or [])[:-1]
            if _semantic_label(value)
        }
        matches: list[tuple[int, str]] = []
        for role, child in catalog["children"].items():
            for matcher in child.get("matchers", []):
                if not isinstance(matcher, dict):
                    continue
                aliases = {
                    normalized
                    for alias in matcher.get("aliases", [])
                    if (normalized := _semantic_label(alias))
                }
                if label not in aliases:
                    continue
                within_role = matcher.get("within_role")
                if within_role:
                    within_aliases = catalog["aliases_by_role"].get(within_role, set())
                    if active_group_role != within_role and not ancestors.intersection(
                        within_aliases
                    ):
                        continue
                    matches.append((2, role))
                else:
                    matches.append((1, role))
        if not matches:
            return None, None
        strongest = max(strength for strength, _role in matches)
        roles = sorted({role for strength, role in matches if strength == strongest})
        if len(roles) != 1:
            return None, "Nhiều ID có thể phù hợp với cùng nhãn nguồn"
        return roles[0], None

    def _schema_coverage(
        self,
        pages: list[dict[str, Any]],
        gemini_tables: list[dict[str, Any]],
        mappings: list[dict[str, Any]],
        specs: dict[str, Any],
    ) -> dict[str, Any]:
        catalog = self._role_catalog(specs)
        topology = specs.get("topology") if isinstance(specs.get("topology"), dict) else {}
        trading_page_context = (
            self._trading_page_context(pages)
            if topology.get("family_id") == "TRADING_SECURITIES"
            else {}
        )
        mapped_ids = {
            mapping["report_norm_id"]
            for mapping in mappings
            if isinstance(mapping.get("report_norm_id"), int)
        }
        mapped_source_rows: set[tuple[Any, Any, Any, Any]] = set()
        for mapping in mappings:
            source_row_ids = {
                row_id
                for row_id in [mapping.get("row_id"), *mapping.get("derived_from_row_ids", [])]
                if isinstance(row_id, str) and not row_id.startswith("derived:")
            }
            for value in mapping.get("values", []):
                for row_id in source_row_ids | (
                    {value.get("row_id")} if value.get("row_id") else set()
                ):
                    mapped_source_rows.add(
                        (
                            value.get("physical_page"),
                            value.get("section_id"),
                            value.get("table_id"),
                            row_id,
                        )
                    )
            for source_ref in mapping.get("source_refs", []):
                row_id = source_ref.get("row_id")
                if not row_id:
                    continue
                mapped_source_rows.add(
                    (
                        source_ref.get("physical_page"),
                        source_ref.get("section_id"),
                        source_ref.get("table_id"),
                        row_id,
                    )
                )

        visible_unmapped: list[dict[str, Any]] = []
        corroborating: list[dict[str, Any]] = []
        source_only: list[dict[str, Any]] = []
        seen_roles: set[str] = set()
        structural_count = 0
        for table in gemini_tables:
            # A page may legitimately contain several sibling families.  A hard-negative
            # title elsewhere on that page must not relabel rows in a selected READY table.
            # Only the evaluator's table/cluster-scoped veto is authoritative here.
            hard_negative = any(
                "HARD_NEGATIVE" in str(reason).upper()
                for reason in table.get("candidate_reasons", [])
            )
            page_context = trading_page_context.get(table["physical_page"], {})
            outside_trading_scope = topology.get(
                "family_id"
            ) == "TRADING_SECURITIES" and not page_context.get("trading")
            if page_context.get("investment") and not page_context.get("trading"):
                hard_negative = True
            active_group_role: str | None = None
            table_surfaces = {
                _semantic_label(table.get("table_title")),
                _semantic_label(table.get("section_title")),
            }
            structural_surface_roles = {
                role
                for role, child in catalog["children"].items()
                if child.get("role_kind") == "STRUCTURAL_GROUP"
                and table_surfaces.intersection(catalog["aliases_by_role"].get(role, set()))
            }
            if len(structural_surface_roles) == 1:
                active_group_role = next(iter(structural_surface_roles))
            for row in table["rows"]:
                role, ambiguity = self._row_role(row, catalog, active_group_role)
                child = catalog["children"].get(role, {}) if role else {}
                if child.get("role_kind") == "STRUCTURAL_GROUP":
                    active_group_role = role
                report_norm_id = catalog["report_norm_id_by_role"].get(role)
                schema = self._schema_names.get(report_norm_id, {})
                key = (
                    table["physical_page"],
                    table["section_id"],
                    table["table_id"],
                    row["id"],
                )
                is_mapped = key in mapped_source_rows
                row["mapping_state"] = "MAPPED" if is_mapped else "SOURCE_ONLY"
                row["schema_match"] = None
                if is_mapped:
                    continue
                if not _has_visible_value(row.get("values")):
                    structural_count += 1
                    row["mapping_state"] = "STRUCTURAL"
                    continue
                common = {
                    "physical_page": table["physical_page"],
                    "section_id": table["section_id"],
                    "table_id": table["table_id"],
                    "row_id": row["id"],
                    "source_label": row["label"],
                    "hierarchy": row["hierarchy"],
                    "values": row["values"],
                    "table_title": table.get("table_title"),
                    "candidate_status": table.get("candidate_status"),
                    "candidate_status_label": table.get("candidate_status_label"),
                    "candidate_reason_labels": table.get("candidate_reason_labels") or [],
                }
                if role and isinstance(report_norm_id, int) and report_norm_id in mapped_ids:
                    seen_roles.add(role)
                    row["mapping_state"] = "CORROBORATING"
                    row["schema_match"] = {
                        "report_norm_id": report_norm_id,
                        "schema_name": schema.get("name") or f"ReportNormId {report_norm_id}",
                    }
                    corroborating.append(
                        common
                        | {
                            "classification": "DÒNG ĐỐI CHIẾU — ID ĐÃ ĐƯỢC MAP",
                            "role": role,
                            "report_norm_id": report_norm_id,
                            "schema_name": schema.get("name") or f"ReportNormId {report_norm_id}",
                            "explanation": (
                                "Cùng khoản mục schema đã được map từ một bảng/ô nguồn khác; "
                                "dòng này được giữ làm bằng chứng đối chiếu, không phải thiếu mapping."
                            ),
                        }
                    )
                    continue
                if outside_trading_scope:
                    source_only.append(
                        common
                        | {
                            "classification": "NGHI THUỘC FAMILY KHÁC",
                            "explanation": (
                                "Nhãn dòng gần với schema chứng khoán kinh doanh, nhưng không "
                                "có tiêu đề/chủ sở hữu bảng xác nhận family này trong phạm vi "
                                "liền kề. Giữ SOURCE_ONLY để tránh nhầm với chứng khoán đầu tư."
                            ),
                        }
                    )
                    continue
                if hard_negative:
                    source_only.append(
                        common
                        | {
                            "classification": "NGHI THUỘC FAMILY KHÁC",
                            "explanation": (
                                "Điều kiện chặn đã được evaluator xác thực trong đúng cụm bảng; "
                                "không được ép vào schema của family đang xem."
                            ),
                        }
                    )
                    continue
                if role and isinstance(report_norm_id, int):
                    seen_roles.add(role)
                    parent_id = schema.get("parent_id")
                    invalid_money = any(
                        "MONEY_CELL_IS_NOT_EXACT_INTEGER" in str(reason).upper()
                        for reason in table.get("candidate_reasons", [])
                    )
                    item = common | {
                        "classification": "CÓ TRÊN PDF NHƯNG CHƯA MAP",
                        "role": role,
                        "report_norm_id": report_norm_id,
                        "schema_name": schema.get("name") or f"ReportNormId {report_norm_id}",
                        "schema_parent_id": parent_id,
                        "schema_parent_name": self._schema_names.get(parent_id, {}).get("name"),
                        "explanation": (
                            "Nhãn nguồn khớp schema nhưng có ít nhất một ô số không đọc được "
                            "thành số nguyên chính xác; cần kiểm tra trực tiếp PDF/OCR, không "
                            "được tự đoán giá trị."
                            if invalid_money
                            else "Nhãn nguồn khớp một khoản mục schema, nhưng candidate bảng "
                            "chưa được chọn hoặc đang bị chặn bởi điều kiện cấu trúc."
                        ),
                    }
                    row["mapping_state"] = "VISIBLE_UNMAPPED"
                    row["schema_match"] = {
                        "report_norm_id": report_norm_id,
                        "schema_name": item["schema_name"],
                    }
                    visible_unmapped.append(item)
                else:
                    source_only.append(
                        common
                        | {
                            "classification": (
                                "NHIỀU ID CÓ THỂ PHÙ HỢP" if ambiguity else "SOURCE_ONLY"
                            ),
                            "explanation": ambiguity
                            or (
                                "Dòng có số liệu nhưng chưa khớp duy nhất với một vai trò schema; "
                                "giữ lại để đối chiếu, chưa kết luận là thiếu schema."
                            ),
                        }
                    )

        not_seen = []
        for role, report_norm_id in catalog["report_norm_id_by_role"].items():
            if role in seen_roles or report_norm_id in mapped_ids:
                continue
            schema = self._schema_names.get(report_norm_id, {})
            parent_id = schema.get("parent_id")
            not_seen.append(
                {
                    "role": role,
                    "report_norm_id": report_norm_id,
                    "schema_name": schema.get("name") or f"ReportNormId {report_norm_id}",
                    "schema_parent_id": parent_id,
                    "schema_parent_name": self._schema_names.get(parent_id, {}).get("name"),
                    "classification": "CHƯA THẤY TRONG PDF",
                    "explanation": (
                        "Khoản mục được family hỗ trợ nhưng không thấy dòng nguồn phù hợp "
                        "trong các bảng Gemini liên quan của PDF này."
                    ),
                }
            )
        not_seen.sort(
            key=lambda item: (
                self._schema_names.get(item["report_norm_id"], {}).get("display_order") or 10**9,
                item["report_norm_id"],
            )
        )

        structural_context: dict[int, dict[str, Any]] = {}
        family_root_id = catalog.get("family_report_norm_id")
        parent_starts = [
            self._schema_names.get(report_norm_id, {}).get("parent_id")
            for report_norm_id in mapped_ids
        ] + [item.get("schema_parent_id") for item in visible_unmapped]
        for parent_id in parent_starts:
            while isinstance(parent_id, int) and parent_id != family_root_id:
                parent = self._schema_names.get(parent_id, {})
                if not parent:
                    break
                if parent_id not in mapped_ids:
                    structural_context[parent_id] = {
                        "report_norm_id": parent_id,
                        "schema_name": parent.get("name") or f"ReportNormId {parent_id}",
                        "classification": "NÚT CHA CẤU TRÚC",
                        "explanation": (
                            "Nút này mô tả nhánh phân loại; thường không có một ô số riêng. "
                            "Các giá trị được map vào những khoản mục con bên dưới; "
                            "không được tạo thêm một giá trị trùng cho nút cha."
                        ),
                    }
                parent_id = parent.get("parent_id")

        unresolved_tables = [
            {
                "physical_page": table["physical_page"],
                "section_id": table["section_id"],
                "table_id": table["table_id"],
                "table_title": table.get("table_title") or table.get("section_title"),
                "reason_labels": table.get("candidate_reason_labels") or [],
            }
            for table in gemini_tables
            if table.get("candidate_status") == "UNRESOLVED"
        ]
        return {
            "summary": {
                "mapped_schema_items": len(mapped_ids),
                "visible_unmapped_items": len(visible_unmapped),
                "corroborating_rows": len(corroborating),
                "not_seen_schema_items": len(not_seen),
                "source_only_rows": len(source_only),
                "structural_rows": structural_count,
                "unresolved_tables": len(unresolved_tables),
            },
            "visible_unmapped": visible_unmapped,
            "corroborating": corroborating,
            "not_seen": not_seen,
            "source_only": source_only,
            "structural_context": sorted(
                structural_context.values(), key=lambda item: item["report_norm_id"]
            ),
            "unresolved_tables": unresolved_tables,
        }

    def review(self, family_id: str, source_sha256: str) -> dict[str, Any]:
        trial = self._trial(family_id, source_sha256)
        normalized_status = status_bucket(trial["status"])
        candidates = self._candidate_payloads(trial["family_run_id"], trial["document_ordinal"])
        mappings = self._mapping_payloads(trial["family_run_id"], trial["document_ordinal"])
        refs = list(_collect_page_refs(mappings))
        for candidate in candidates:
            index = candidate.get("_index", {})
            if index.get("page_json_version_id"):
                refs.append(index)
            refs.extend(_collect_page_refs(candidate.get("component_regions", [])))
            refs.extend(_collect_page_refs(candidate.get("mappings", [])))
        pages = self._page_payloads(source_sha256, refs)
        policy_pages = pages
        if family_id == "TRADING_SECURITIES":
            preceding_pages = self._preceding_page_payloads(
                source_sha256, [page["physical_page"] for page in pages]
            )
            known_versions = {page["page_json_version_id"] for page in pages}
            policy_pages = pages + [
                page
                for page in preceding_pages
                if page["page_json_version_id"] not in known_versions
            ]
        reasons = _json_load(trial["reasons_json"], [])
        document = _document_metadata(trial["source_logical_name"])
        document.update(
            {
                "source_sha256": source_sha256,
                "document_ordinal": trial["document_ordinal"],
                "pdf_available": self.pdf_path(trial["source_logical_name"]) is not None,
            }
        )
        page_summaries = [
            {
                key: page[key]
                for key in (
                    "page_json_version_id",
                    "page_status",
                    "physical_page",
                    "width",
                    "height",
                )
            }
            | {
                "image_url": f"/api/page-image/{source_sha256}/{page['physical_page']}",
                "image_available": document["pdf_available"],
            }
            for page in pages
        ]
        candidate_summary = []
        for candidate in candidates:
            index = candidate.get("_index", {})
            candidate_reasons = candidate.get("reasons") or []
            candidate_summary.append(
                {
                    **index,
                    "selected": index.get("candidate_id") == trial["selected_candidate_id"],
                    "status_bucket": status_bucket(index.get("status") or ""),
                    "reasons": candidate_reasons,
                    "reason_labels": [reason_name(reason) for reason in candidate_reasons],
                }
            )
        selected_candidate = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("_index", {}).get("candidate_id") == trial["selected_candidate_id"]
            ),
            None,
        )
        selected_locator = dict(selected_candidate.get("_index", {})) if selected_candidate else {}
        gemini_tables = self._gemini_tables(
            pages,
            candidates,
            trial["selected_candidate_id"],
            _collect_page_refs(mappings),
        )
        normalized_mappings = [
            self._normalized_mapping(
                mapping,
                selected_locator,
                {page["page_json_version_id"]: page["physical_page"] for page in pages},
            )
            for mapping in mappings
        ]
        specs = self._family_specs(trial["family_run_id"])
        normalized_mappings.extend(
            self._current_policy_mappings(
                family_id,
                policy_pages,
                gemini_tables,
                normalized_mappings,
                specs,
            )
        )
        normalized_mappings.sort(
            key=lambda mapping: (
                mapping.get("schema_display_order")
                if isinstance(mapping.get("schema_display_order"), int)
                else 10**9,
                mapping.get("report_norm_id")
                if isinstance(mapping.get("report_norm_id"), int)
                else 10**9,
                str(mapping.get("mapping_ordinal") or ""),
            )
        )
        self._attach_mapping_headers(normalized_mappings, gemini_tables)
        self._attach_derived_source_context(normalized_mappings, gemini_tables)
        coverage = self._schema_coverage(
            policy_pages,
            gemini_tables,
            normalized_mappings,
            specs,
        )
        return {
            "family": {"id": family_id, "name": family_name(family_id)},
            "document": document,
            "disposition": {
                "status": normalized_status,
                "raw_status": trial["status"],
                "status_label": STATUS_NAMES_VI.get(normalized_status, normalized_status),
                "candidate_count": trial["candidate_count"],
                "mapping_count": len(normalized_mappings),
                "persisted_mapping_count": trial["mapping_count"],
                "reasons": reasons,
                "reason_labels": [reason_name(reason) for reason in reasons],
            },
            "pages": page_summaries,
            "gemini_tables": gemini_tables,
            "mappings": normalized_mappings,
            "candidates": candidate_summary,
            "coverage": coverage,
        }

    def pdf_path(self, source_logical_name: str) -> Path | None:
        root = self.settings.pdf_root
        if not root or not root.exists():
            return None
        logical = Path(source_logical_name.replace("\\", "/"))
        parts = logical.parts
        if parts and parts[0] == "vietstock_bctc":
            logical = Path(*parts[1:])
        candidate = (root / logical).resolve(strict=False)
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def source_logical_name(self, source_sha256: str) -> str:
        with self._pages() as connection:
            row = connection.execute(
                "SELECT source_logical_name FROM document WHERE source_sha256 = ?",
                (source_sha256,),
            ).fetchone()
        if row is None:
            raise LookupError("Không tìm thấy PDF trong page store")
        return row["source_logical_name"]

    def render_page(self, source_sha256: str, physical_page: int) -> Path:
        if physical_page < 1:
            raise LookupError("Số trang không hợp lệ")
        logical_name = self.source_logical_name(source_sha256)
        pdf_path = self.pdf_path(logical_name)
        if pdf_path is None:
            raise FileNotFoundError("Chưa cấu hình đúng BCTC_PDF_ROOT để hiển thị ảnh trang")
        self.settings.cache_directory.mkdir(parents=True, exist_ok=True)
        cache_path = self.settings.cache_directory / f"{source_sha256}-p{physical_page}-144dpi.png"
        if cache_path.exists():
            return cache_path
        document = fitz.open(pdf_path)
        try:
            if physical_page > document.page_count:
                raise LookupError("Trang PDF nằm ngoài phạm vi tài liệu")
            page = document.load_page(physical_page - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            temporary = cache_path.with_suffix(".tmp.png")
            pixmap.save(temporary)
            temporary.replace(cache_path)
        finally:
            document.close()
        return cache_path
