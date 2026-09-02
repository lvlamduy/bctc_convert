"""Pinned OpenRouter Google Vertex Flex plan for the 27-bank expansion."""

from __future__ import annotations

from datetime import date
from typing import Any

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    OPENROUTER_ROUTE,
    build_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    OPENROUTER_MODEL,
    OPENROUTER_PROVIDER,
    OPENROUTER_SERVICE_TIER,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_27BANK_VERTEX_FLEX_EXPANSION_V1"
LANGUAGE_SCOPE_FORMAT_VERSION = "GEMINI_JSON_FIRST_VIETNAMESE_PAGE_SCOPE_V1"
ALREADY_PROCESSED_BANKS = frozenset({"ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"})


class GeminiJsonFirstVertexFlexExpansionV1Error(ValueError):
    """The expansion universe or its exclusive provider route drifted."""


def _error(message: str) -> GeminiJsonFirstVertexFlexExpansionV1Error:
    return GeminiJsonFirstVertexFlexExpansionV1Error(message)


def _authenticated_period_scope_v1(value: dict[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"as_of_date", "from_year"}:
        raise _error("authenticated 2025-current period scope is invalid")
    from_year = value.get("from_year")
    as_of_date = value.get("as_of_date")
    try:
        parsed_as_of_date = date.fromisoformat(as_of_date) if type(as_of_date) is str else None
    except ValueError as error:
        raise _error("authenticated 2025-current period scope is invalid") from error
    if from_year != 2025 or parsed_as_of_date is None or parsed_as_of_date < date(from_year, 1, 1):
        raise _error("authenticated 2025-current period scope is invalid")
    return {"as_of_date": as_of_date, "from_year": from_year}


def _already_processed_corpus_binding_v1(
    manifest_index: dict[str, Any], *, expected_ref: dict[str, Any]
) -> dict[str, Any]:
    if (
        type(manifest_index) is not dict
        or manifest_index.get("format_version") != "GEMINI_CURRENT_CORPUS_MANIFEST_INDEX_V1"
        or manifest_index.get("corpus_manifest_index_id") != expected_ref.get("manifest_index_id")
        or type(manifest_index.get("documents")) is not list
        or type(manifest_index.get("summary")) is not dict
        or manifest_index["summary"].get("document_count") != expected_ref.get("document_count")
        or manifest_index["summary"].get("page_count") != expected_ref.get("page_count")
    ):
        raise _error("already-processed corpus manifest disagrees with the filing universe")
    source_sha256s = []
    relative_paths = []
    for item in manifest_index["documents"]:
        if type(item) is not dict:
            raise _error("already-processed corpus document is invalid")
        digest = item.get("source_sha256")
        path = item.get("relative_path")
        path_parts = path.split("/") if type(path) is str else []
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or len(path_parts) < 4
            or path_parts[0] != "vietstock_bctc"
            or path_parts[1] not in ALREADY_PROCESSED_BANKS
        ):
            raise _error("already-processed corpus source identity is invalid")
        source_sha256s.append(digest)
        relative_paths.append(path)
    if (
        len(source_sha256s) != expected_ref["document_count"]
        or len(set(source_sha256s)) != len(source_sha256s)
        or len(set(relative_paths)) != len(relative_paths)
    ):
        raise _error("already-processed corpus source frontier is not unique and exhaustive")
    return {
        "corpus_manifest_index_id": manifest_index["corpus_manifest_index_id"],
        "document_count": expected_ref["document_count"],
        "page_count": expected_ref["page_count"],
        "relative_paths": sorted(relative_paths),
        "source_sha256s": sorted(source_sha256s),
    }


def validate_gemini_json_first_vietnamese_page_scope_v1(
    value: dict[str, Any],
) -> dict[str, Any]:
    """Validate one human-reviewed Vietnamese physical-page frontier."""

    if type(value) is not dict or set(value) != {
        "documents",
        "format_version",
        "policy",
        "scope_id",
        "summary",
    }:
        raise _error("Vietnamese page scope fields drifted")
    policy = value.get("policy")
    documents = value.get("documents")
    summary = value.get("summary")
    if (
        value.get("format_version") != LANGUAGE_SCOPE_FORMAT_VERSION
        or policy
        != {
            "always_review_bank_codes": ["OCB"],
            "included_language": "VIETNAMESE",
            "page_selection": "PHYSICAL_PAGE_PREFIX",
            "review_pdf_over_pages": 100,
        }
        or type(documents) is not list
        or type(summary) is not dict
    ):
        raise _error("Vietnamese page scope policy is invalid")
    paths: list[str] = []
    source_pages = 0
    included_pages = 0
    excluded_documents = 0
    for item in documents:
        if type(item) is not dict or set(item) != {
            "included_last_physical_page",
            "relative_path",
            "review_conclusion",
            "source_page_count",
        }:
            raise _error("Vietnamese page scope document fields drifted")
        path = item["relative_path"]
        total = item["source_page_count"]
        included = item["included_last_physical_page"]
        conclusion = item["review_conclusion"]
        parts = path.split("/") if type(path) is str else []
        if (
            len(parts) < 4
            or parts[0] != "vietstock_bctc"
            or type(total) is not int
            or total <= 0
            or type(included) is not int
            or not 1 <= included <= total
            or conclusion
            not in {
                "FULL_DOCUMENT_VIETNAMESE",
                "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX",
            }
            or (conclusion == "FULL_DOCUMENT_VIETNAMESE" and included != total)
            or (
                conclusion == "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX"
                and included >= total
            )
        ):
            raise _error("Vietnamese page scope document is invalid")
        paths.append(path)
        source_pages += total
        included_pages += included
        excluded_documents += int(included < total)
    if paths != sorted(set(paths)):
        raise _error("Vietnamese page scope paths are not unique and ordered")
    expected_summary = {
        "excluded_document_count": excluded_documents,
        "excluded_page_count": source_pages - included_pages,
        "included_page_count": included_pages,
        "reviewed_document_count": len(documents),
        "source_page_count": source_pages,
    }
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "scope_id"}
    if summary != expected_summary or value.get(
        "scope_id"
    ) != "gjfvietnamesev1:" + canonical_json_sha256_v1(material):
        raise _error("Vietnamese page scope identity or summary drifted")
    return canonical_clone_v1(value)


def build_gemini_json_first_vietnamese_page_scope_v1(
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one deterministic human-reviewed Vietnamese page scope."""

    if type(documents) is not list or any(type(item) is not dict for item in documents):
        raise _error("Vietnamese page scope documents are invalid")
    checked_documents = sorted(
        (canonical_clone_v1(item) for item in documents),
        key=lambda item: item.get("relative_path", "") if type(item) is dict else "",
    )
    source_pages = sum(item.get("source_page_count", 0) for item in checked_documents)
    included_pages = sum(item.get("included_last_physical_page", 0) for item in checked_documents)
    material = {
        "documents": checked_documents,
        "format_version": LANGUAGE_SCOPE_FORMAT_VERSION,
        "policy": {
            "always_review_bank_codes": ["OCB"],
            "included_language": "VIETNAMESE",
            "page_selection": "PHYSICAL_PAGE_PREFIX",
            "review_pdf_over_pages": 100,
        },
        "summary": {
            "excluded_document_count": sum(
                item.get("included_last_physical_page") != item.get("source_page_count")
                for item in checked_documents
            ),
            "excluded_page_count": source_pages - included_pages,
            "included_page_count": included_pages,
            "reviewed_document_count": len(checked_documents),
            "source_page_count": source_pages,
        },
    }
    result = {
        **material,
        "scope_id": "gjfvietnamesev1:" + canonical_json_sha256_v1(material),
    }
    return validate_gemini_json_first_vietnamese_page_scope_v1(result)


def build_gemini_json_first_vertex_flex_expansion_v1(
    authenticated_universe: dict[str, Any],
    *,
    already_processed_corpus_manifest_index: dict[str, Any],
    vietnamese_page_scope: dict[str, Any],
    dpi: int = 300,
    workers: int = 20,
) -> dict[str, Any]:
    """Build one all-document Flex plan and a fail-closed execution contract."""

    if (
        type(authenticated_universe) is not dict
        or authenticated_universe.get("format_version")
        != "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1"
        or type(authenticated_universe.get("authenticated_universe_id")) is not str
        or not authenticated_universe["authenticated_universe_id"].startswith("bankfilingauthv1:")
        or authenticated_universe.get("local_source_authentication")
        != {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        }
    ):
        raise _error("authenticated 2025-current filing universe is required")
    period_scope = _authenticated_period_scope_v1(
        {
            "as_of_date": authenticated_universe.get("as_of_date"),
            "from_year": authenticated_universe.get("from_year"),
        }
    )
    summary = authenticated_universe.get("summary")
    filings = authenticated_universe.get("filings")
    processed_corpus_ref = authenticated_universe.get("already_processed_corpus_ref")
    processed_banks = authenticated_universe.get("already_processed_bank_codes")
    new_banks = authenticated_universe.get("new_bank_codes")
    if (
        type(summary) is not dict
        or summary.get("bank_count") != 27
        or summary.get("already_processed_bank_count") != 8
        or summary.get("new_bank_count") != 19
        or type(filings) is not list
        or len(filings) != summary.get("candidate_filing_count")
        or type(processed_banks) is not list
        or set(processed_banks) != ALREADY_PROCESSED_BANKS
        or type(new_banks) is not list
        or len(new_banks) != 19
        or set(new_banks) & ALREADY_PROCESSED_BANKS
        or type(processed_corpus_ref) is not dict
    ):
        raise _error("filing universe denominator drifted")
    processed_binding = _already_processed_corpus_binding_v1(
        already_processed_corpus_manifest_index,
        expected_ref=processed_corpus_ref,
    )
    checked_language_scope = validate_gemini_json_first_vietnamese_page_scope_v1(
        vietnamese_page_scope
    )
    scope_by_path = {item["relative_path"]: item for item in checked_language_scope["documents"]}
    documents = []
    expected_review_paths = set()
    for filing in filings:
        if type(filing) is not dict or type(filing.get("content_ref")) is not dict:
            raise _error("filing universe record is malformed")
        content = filing["content_ref"]
        path = content.get("path")
        path_parts = path.split("/") if type(path) is str else []
        filing_year = filing.get("year")
        bank = filing.get("bank")
        if (
            type(filing_year) is not int
            or not period_scope["from_year"]
            <= filing_year
            <= date.fromisoformat(period_scope["as_of_date"]).year
            or len(path_parts) < 4
            or path_parts[0] != "vietstock_bctc"
            or path_parts[1] != bank
            or path_parts[2] != str(filing_year)
        ):
            raise _error("filing is outside the authenticated 2025-current period scope")
        disposition = filing.get("provider_disposition")
        if bank in ALREADY_PROCESSED_BANKS and disposition != "REUSE_EXISTING_GEMINI_JSON":
            raise _error("already-processed bank entered the paid provider frontier")
        if bank not in ALREADY_PROCESSED_BANKS and disposition != "NEW_VERTEX_FLEX_FRONTIER":
            raise _error("new bank is absent from the paid provider frontier")
        if disposition == "REUSE_EXISTING_GEMINI_JSON":
            continue
        if disposition != "NEW_VERTEX_FLEX_FRONTIER":
            raise _error("filing provider disposition is invalid")
        source_pages = filing["page_count"]
        if (
            bank == "OCB"
            or source_pages > checked_language_scope["policy"]["review_pdf_over_pages"]
        ):
            expected_review_paths.add(path)
        scope = scope_by_path.get(path)
        selected_pages = source_pages
        document = {
            "page_count": selected_pages,
            "relative_path": path,
            "source_sha256": content["sha256"],
            "source_size_bytes": content["size_bytes"],
        }
        if scope is not None:
            if scope["source_page_count"] != source_pages:
                raise _error("Vietnamese page scope source page count drifted")
            selected_pages = scope["included_last_physical_page"]
            document.update(
                {
                    "page_count": selected_pages,
                    "source_page_count": source_pages,
                    "page_selection": {
                        "included_first_physical_page": 1,
                        "included_last_physical_page": selected_pages,
                        "review_basis": "HUMAN_VISUAL_LANGUAGE_BOUNDARY",
                        "selection_kind": scope["review_conclusion"],
                    },
                }
            )
        documents.append(document)
    if set(scope_by_path) != expected_review_paths:
        raise _error("Vietnamese page scope is not exhaustive for OCB and long PDFs")
    plan = build_gemini_json_first_corpus_plan_v1(
        documents,
        dpi=dpi,
        openrouter_page_fraction="1.0",
        openrouter_workers=workers,
    )
    if (
        plan["summary"]["route_pages"]
        != {
            "GOOGLE_GEMINI_BATCH_API": 0,
            OPENROUTER_ROUTE: sum(document["page_count"] for document in documents),
        }
        or plan["summary"]["document_count"] != summary["provider_call_candidate_filing_count"]
        or any(document["route"] != OPENROUTER_ROUTE for document in plan["documents"])
        or any(
            task["route"] != OPENROUTER_ROUTE
            for document in plan["documents"]
            for task in document["tasks"]
        )
    ):
        raise _error("corpus plan is not exclusively routed through OpenRouter")
    new_source_sha256s = {item["document"]["source_sha256"] for item in plan["documents"]}
    new_relative_paths = {item["document"]["relative_path"] for item in plan["documents"]}
    if new_source_sha256s.intersection(processed_binding["source_sha256s"]) or (
        new_relative_paths.intersection(processed_binding["relative_paths"])
    ):
        raise _error("paid frontier overlaps the already-processed corpus")
    material = {
        "already_processed_corpus_binding": processed_binding,
        "authenticated_universe_id": authenticated_universe["authenticated_universe_id"],
        "corpus_plan": plan,
        "execution_contract": {
            "allow_provider_fallbacks": False,
            "direct_google_api_allowed": False,
            "gateway": "OPENROUTER",
            "model": OPENROUTER_MODEL,
            "provider": OPENROUTER_PROVIDER,
            "service_tier": OPENROUTER_SERVICE_TIER,
            "supervisor_required_flag": "--openrouter-only",
        },
        "format_version": FORMAT_VERSION,
        "period_scope": period_scope,
        "vietnamese_page_scope": checked_language_scope,
    }
    return {
        **canonical_clone_v1(material),
        "expansion_plan_id": "gjfvertexflexv1:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_first_vertex_flex_expansion_v1(
    value: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild and exact-compare the provider-pinned expansion bundle."""

    if type(value) is not dict or type(value.get("corpus_plan")) is not dict:
        raise _error("Vertex Flex expansion bundle is invalid")
    contract = value.get("execution_contract")
    expected_contract = {
        "allow_provider_fallbacks": False,
        "direct_google_api_allowed": False,
        "gateway": "OPENROUTER",
        "model": OPENROUTER_MODEL,
        "provider": OPENROUTER_PROVIDER,
        "service_tier": OPENROUTER_SERVICE_TIER,
        "supervisor_required_flag": "--openrouter-only",
    }
    plan = value["corpus_plan"]
    period_scope = value.get("period_scope")
    if type(period_scope) is not dict:
        raise _error("authenticated 2025-current period scope is invalid")
    checked_period_scope = _authenticated_period_scope_v1(period_scope)
    as_of_year = date.fromisoformat(checked_period_scope["as_of_date"]).year
    processed_binding = value.get("already_processed_corpus_binding")
    checked_language_scope = validate_gemini_json_first_vietnamese_page_scope_v1(
        value.get("vietnamese_page_scope")
    )
    if (
        type(processed_binding) is not dict
        or set(processed_binding)
        != {
            "corpus_manifest_index_id",
            "document_count",
            "page_count",
            "relative_paths",
            "source_sha256s",
        }
        or type(processed_binding.get("document_count")) is not int
        or processed_binding["document_count"] <= 0
        or type(processed_binding.get("page_count")) is not int
        or processed_binding["page_count"] <= 0
        or type(processed_binding.get("relative_paths")) is not list
        or type(processed_binding.get("source_sha256s")) is not list
        or len(processed_binding["relative_paths"]) != processed_binding["document_count"]
        or len(processed_binding["source_sha256s"]) != processed_binding["document_count"]
        or processed_binding["relative_paths"] != sorted(set(processed_binding["relative_paths"]))
        or processed_binding["source_sha256s"] != sorted(set(processed_binding["source_sha256s"]))
        or type(processed_binding.get("corpus_manifest_index_id")) is not str
        or not processed_binding["corpus_manifest_index_id"].startswith("gjfccmiv1:index:")
        or any(
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in processed_binding["source_sha256s"]
        )
        or any(
            type(path) is not str
            or len(path.split("/")) < 4
            or path.split("/")[0] != "vietstock_bctc"
            or path.split("/")[1] not in ALREADY_PROCESSED_BANKS
            for path in processed_binding["relative_paths"]
        )
    ):
        raise _error("already-processed corpus binding is invalid")
    plan_documents = plan.get("documents", [])
    if type(plan_documents) is not list:
        raise _error("Vertex Flex corpus plan document axis is invalid")
    planned_bank_codes = []
    planned_source_sha256s = []
    planned_relative_paths = []
    planned_by_path = {}
    for item in plan_documents:
        document = item.get("document") if type(item) is dict else None
        path = document.get("relative_path") if type(document) is dict else None
        digest = document.get("source_sha256") if type(document) is dict else None
        if type(path) is not str or type(digest) is not str:
            raise _error("Vertex Flex corpus plan document is invalid")
        path_parts = path.split("/")
        if (
            len(path_parts) < 4
            or path_parts[0] != "vietstock_bctc"
            or not path_parts[2].isdigit()
            or not checked_period_scope["from_year"] <= int(path_parts[2]) <= as_of_year
        ):
            raise _error("Vertex Flex corpus plan source path is invalid")
        planned_bank_codes.append(path_parts[1])
        planned_relative_paths.append(path)
        planned_source_sha256s.append(digest)
        planned_by_path[path] = document
    scope_by_path = {item["relative_path"]: item for item in checked_language_scope["documents"]}
    expected_review_paths = {
        path
        for path, document in planned_by_path.items()
        if path.split("/")[1] == "OCB"
        or document.get("source_page_count", document.get("page_count")) > 100
    }
    if set(scope_by_path) != expected_review_paths:
        raise _error("Vietnamese page scope no longer covers OCB and long PDFs")
    for path, scope in scope_by_path.items():
        document = planned_by_path[path]
        expected_document_scope = {
            "included_first_physical_page": 1,
            "included_last_physical_page": scope["included_last_physical_page"],
            "review_basis": "HUMAN_VISUAL_LANGUAGE_BOUNDARY",
            "selection_kind": scope["review_conclusion"],
        }
        if (
            document.get("source_page_count") != scope["source_page_count"]
            or document.get("page_count") != scope["included_last_physical_page"]
            or document.get("page_selection") != expected_document_scope
        ):
            raise _error("Vietnamese page scope and corpus plan drifted")
    if (
        value.get("format_version") != FORMAT_VERSION
        or contract != expected_contract
        or any(document.get("route") != OPENROUTER_ROUTE for document in plan_documents)
        or plan.get("summary", {}).get("route_pages", {}).get("GOOGLE_GEMINI_BATCH_API") != 0
        or not planned_bank_codes
        or ALREADY_PROCESSED_BANKS.intersection(planned_bank_codes)
        or set(planned_source_sha256s).intersection(processed_binding["source_sha256s"])
        or set(planned_relative_paths).intersection(processed_binding["relative_paths"])
    ):
        raise _error("Vertex Flex exclusive execution contract drifted")
    material = {
        key: canonical_clone_v1(item) for key, item in value.items() if key != "expansion_plan_id"
    }
    expected_id = "gjfvertexflexv1:" + canonical_json_sha256_v1(material)
    if value.get("expansion_plan_id") != expected_id:
        raise _error("Vertex Flex expansion bundle identity drifted")
    return canonical_clone_v1(value)
