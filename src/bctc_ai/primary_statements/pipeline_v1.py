"""Document-level orchestration of PRIMARY statement digitization.

Retrieval is region-first and bounded: one batched label census over the
selected pages of the corpus decides candidate pages (PRIMARY metadata or a
catalog fingerprint), only those pages are hydrated through the authenticated
loader, and every non-candidate page keeps an explicit census disposition so
the bounded whole-document scan is auditable.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bctc_ai.primary_statements.assembly_v1 import (
    STATEMENT_OF_TYPE,
    StatementInstance,
    assemble_document_instances_v1,
    assign_parents_v1,
    classify_table_v1,
    instance_page_sections,
    iter_source_tables,
    rebind_document_period_context_v1,
    resolve_cash_flow_branch_v1,
    resolve_document_scope_v1,
    resolve_instance_lanes_v1,
    resolve_instance_scope_v1,
)
from bctc_ai.primary_statements.catalog_v1 import PrimaryCatalog
from bctc_ai.primary_statements.mapping_v1 import (
    RowDisposition,
    map_instance_rows_v1,
    resolve_duplicate_presentations_v1,
)
from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles, evidence_roles_v1
from bctc_ai.primary_statements.source_v1 import (
    CorpusSelection,
    PrimarySourceError,
    SelectedDocument,
    SourceMetrics,
    load_original_pages_v1,
    selected_section_titles_v1,
    selected_table_label_census_v1,
)
from bctc_ai.primary_statements.text_v1 import fold_vietnamese, label_key_v1
from bctc_ai.primary_statements.validation_v1 import load_equation_config_v1, validate_instance_v1

PIPELINE_VERSION = "PRIMARY_STATEMENT_PIPELINE_V1"
PREFILTER_MIN_HITS = 2


@dataclass
class DocumentRun:
    document: SelectedDocument
    page_census: list[dict[str, Any]]
    tables: list[Any]
    instances: list[StatementInstance]
    dispositions: dict[str, list[RowDisposition]]
    other_tables: list[Any]
    presentation_receipts: list[dict[str, Any]]
    statement_status: dict[str, Any] = field(default_factory=dict)
    validations: dict[str, list[Any]] = field(default_factory=dict)
    notes_start_page: int | None = None


def candidate_pages_v1(
    corpus: CorpusSelection, catalog: PrimaryCatalog, metrics: SourceMetrics
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """Census every selected page; return per-page census and per-version titles."""

    ids = [page.page_json_version_id for document in corpus.documents for page in document.pages]
    with metrics.timed("census_sql"):
        rows = selected_table_label_census_v1(corpus.db_path, page_json_version_ids=ids, metrics=metrics)
        titles = selected_section_titles_v1(corpus.db_path, page_json_version_ids=ids, metrics=metrics)
    with metrics.timed("census_fingerprint"):
        per_table: dict[tuple[str, str, str], dict[str, Any]] = {}
        cache: dict[str, dict[str, set[str]]] = {}
        for row in rows:
            key = (row["page_json_version_id"], row["section_id"], row["table_id"])
            table = per_table.setdefault(key, {
                "content_kind": row["content_kind"], "statement_type": row["statement_type"],
                "targets": defaultdict(set),
            })
            label = row["label_exact"]
            if label not in cache:
                normalized = label_key_v1(label).key
                cache[label] = {
                    statement: {hit.target for hit in statement_catalog.lookup(normalized) if hit.kind == "ITEM"}
                    for statement, statement_catalog in catalog.statements.items()
                }
            for statement, targets in cache[label].items():
                table["targets"][statement] |= targets
        census: dict[str, dict[str, Any]] = {}
        for (version, _section, _table), table in per_table.items():
            page = census.setdefault(version, {"primary_metadata": False, "max_hits": {}, "tables": 0})
            page["tables"] += 1
            if table["content_kind"] == "PRIMARY_STATEMENT" or table["statement_type"] in STATEMENT_OF_TYPE:
                page["primary_metadata"] = True
            for statement, targets in table["targets"].items():
                page["max_hits"][statement] = max(page["max_hits"].get(statement, 0), len(targets))
        for version in ids:
            page = census.setdefault(version, {"primary_metadata": False, "max_hits": {}, "tables": 0})
            best = max(page["max_hits"].values(), default=0)
            page["candidate"] = page["primary_metadata"] or best >= PREFILTER_MIN_HITS
            page["census_reason"] = (
                "PRIMARY_METADATA" if page["primary_metadata"] else
                "CATALOG_FINGERPRINT" if best >= PREFILTER_MIN_HITS else
                "NO_TABLES" if not page["tables"] else "NO_PRIMARY_SIGNAL"
            )
    by_version_titles: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in titles:
        if row["title_exact"]:
            by_version_titles[row["page_json_version_id"]].append((row["title_exact"], row["content_kind"]))
    return census, by_version_titles


def notes_start_page_v1(document, titles, first_primary_page: int | None) -> int | None:
    """First page after the statements whose note section carries a "Thuyết minh" title."""

    if first_primary_page is None:
        return None
    for page in document.pages:
        if page.physical_page <= first_primary_page:
            continue
        for title, kind in titles.get(page.page_json_version_id, []):
            if kind == "FINANCIAL_NOTE" and "thuyet minh" in fold_vietnamese(title):
                return page.physical_page
    return None


def run_corpus_v1(
    corpus: CorpusSelection,
    catalog: PrimaryCatalog,
    *,
    project_root: Path,
    metrics: SourceMetrics,
    document_ordinals: set[int] | None = None,
) -> list[DocumentRun]:
    census, titles = candidate_pages_v1(corpus, catalog, metrics)
    documents = [d for d in corpus.documents if document_ordinals is None or d.ordinal in document_ordinals]
    wanted = [page.page_json_version_id for document in documents for page in document.pages
              if census[page.page_json_version_id]["candidate"]]
    with metrics.timed("authenticated_page_load"):
        loaded = load_original_pages_v1(corpus.db_path, page_json_version_ids=wanted, metrics=metrics)
    rules_path = project_root / "config/mapping/lctt-v2.yaml"
    equations = load_equation_config_v1(project_root)
    runs = []
    with metrics.timed("assemble_map_validate"):
        for document in documents:
            runs.append(run_document_v1(document, census, titles, loaded, catalog, rules_path, equations))
    return runs


def run_document_v1(document, census, titles, loaded, catalog, rules_path, equations) -> DocumentRun:
    page_census = []
    tables = []
    for page in document.pages:
        entry = dict(census[page.page_json_version_id])
        entry["max_hits"] = dict(entry["max_hits"])
        entry.update({"physical_page": page.physical_page, "page_json_version_id": page.page_json_version_id,
                      "page_status": page.status})
        page_census.append(entry)
        if entry["candidate"]:
            item = loaded[page.page_json_version_id]
            # The authenticated loader's provenance must be this selected page of this document.
            if (item.get("page_json_version_id"), item.get("source_logical_name"), item.get("source_sha256"),
                    item.get("physical_page")) != (page.page_json_version_id, document.relative_path,
                                                   document.source_sha256, page.physical_page):
                raise PrimarySourceError(f"loaded page provenance is not the selected page {page.page_json_version_id}")
            for source in iter_source_tables(document.ordinal, page, item["page_json"]):
                source.classification = classify_table_v1(source, catalog)
                tables.append(source)
    document_roles = SeparatorRoles()
    for source in tables:
        if source.classification["decision"] in catalog.statements:
            for row in source.table.get("rows") or []:
                for value, column in zip(row.get("values_exact") or [], source.table.get("columns") or [], strict=False):
                    if column.get("value_kind") == "MONEY":
                        document_roles = document_roles.merge(evidence_roles_v1(value))
    statement_pages = [source.physical_page for source in tables if source.classification["decision"] in catalog.statements]
    notes_start = notes_start_page_v1(document, titles, min(statement_pages) if statement_pages else None)
    instances, others = assemble_document_instances_v1(tables, catalog, notes_start_page=notes_start)
    document_titles = [title for page in document.pages for title, _ in titles.get(page.page_json_version_id, [])]
    page_sections = {
        page.page_json_version_id: _page_sections(loaded[page.page_json_version_id]["page_json"])
        for page in document.pages if page.page_json_version_id in loaded
    }
    dispositions = {}
    for instance in instances:
        others_on_pages = instance_page_sections(instance, page_sections)
        own_texts = [
            text for source in instance.tables
            for text in [source.section.get("title_exact"), source.table.get("title_exact"),
                         *(source.section.get("narratives_exact") or [])] if text
        ]
        other_texts = [text for section in others_on_pages
                       if section["content_kind"] != "FINANCIAL_NOTE"
                       for text in [section["title"], *section["narratives"]] if text]
        resolve_instance_scope_v1(instance, document_titles, own_texts + other_texts)
    resolve_document_scope_v1(instances, document_titles)
    for instance in instances:
        resolve_cash_flow_branch_v1(instance, rules_path, catalog)
        resolve_instance_lanes_v1(instance, catalog, document_roles, instance_page_sections(instance, page_sections))
    rebind_document_period_context_v1(instances, catalog, document_roles,
                                      lambda instance: instance_page_sections(instance, page_sections))
    for instance in instances:
        assign_parents_v1(instance)
        dispositions[instance.key] = map_instance_rows_v1(instance, catalog)
    receipts = resolve_duplicate_presentations_v1(instances, dispositions)
    run = DocumentRun(document, page_census, tables, instances, dispositions, others, receipts)
    run.notes_start_page = notes_start
    for instance in instances:
        run.validations[instance.key] = validate_instance_v1(instance, dispositions[instance.key], catalog, equations)
    run.statement_status = _statement_status(run)
    return run


def _page_sections(page_json: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for ordinal, section in enumerate(page_json.get("sections") or [], 1):
        result.append({
            "section_ordinal": ordinal,
            "content_kind": section.get("content_kind"),
            "statement_type": section.get("statement_type"),
            "title": section.get("title_exact"),
            "narratives": [text for text in section.get("narratives_exact") or [] if text],
            "table_titles": [t.get("title_exact") for t in section.get("tables") or [] if t.get("title_exact")],
            "table_units": [t.get("unit_exact") for t in section.get("tables") or [] if t.get("unit_exact")],
        })
    return result


def _statement_status(run: DocumentRun) -> dict[str, Any]:
    result = {}
    for statement in ("CDKT", "KQKD", "LCTT"):
        chosen = [i for i in run.instances if i.statement == statement and i.presentation_role == "PRIMARY"]
        scopes = Counter(i.scope or "SCOPE_UNRESOLVED" for i in chosen)
        result[statement] = {
            "instances": [i.key for i in chosen],
            "scopes": dict(scopes),
            "status": "FOUND" if chosen else "NOT_FOUND_AFTER_BOUNDED_SCAN",
            "multiple_same_scope": any(count > 1 for count in scopes.values()),
        }
    return result
