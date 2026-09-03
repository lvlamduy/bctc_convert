"""Provider-pinned 2024 Gemini frontier protected from all 2025-current reuse."""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    GOOGLE_ROUTE,
    OPENROUTER_ROUTE,
    build_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    OPENROUTER_MODEL,
    OPENROUTER_PROVIDER,
    OPENROUTER_SERVICE_TIER,
    OPENROUTER_STANDARD_FALLBACK_PROVIDER,
    OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
)
from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (
    validate_gemini_json_first_vertex_flex_expansion_v1,
    validate_gemini_json_first_vietnamese_page_scope_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_27BANK_2024_VERTEX_FLEX_EXPANSION_V1"
UNIVERSE_FORMAT_VERSION = "BANK_FILING_UNIVERSE_27BANK_2024_V1"
REPORTING_YEAR = 2024


class GeminiJsonFirstVertexFlexExpansion2024V1Error(ValueError):
    """The 2024 source frontier or its protected predecessor drifted."""


def _error(message: str) -> GeminiJsonFirstVertexFlexExpansion2024V1Error:
    return GeminiJsonFirstVertexFlexExpansion2024V1Error(message)


def _checked_digest(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error("source SHA-256 is invalid")
    return value


def _checked_authenticated_universe_v1(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value.get("format_version") != UNIVERSE_FORMAT_VERSION:
        raise _error("authenticated 2024 filing universe is required")
    filings = value.get("filings")
    banks = value.get("bank_codes")
    summary = value.get("summary")
    if (
        value.get("reporting_year") != REPORTING_YEAR
        or type(filings) is not list
        or type(banks) is not list
        or len(banks) != 27
        or banks != sorted(set(banks))
        or any(type(bank) is not str or bank != bank.upper() for bank in banks)
        or type(summary) is not dict
        or value.get("local_source_authentication")
        != {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        }
        or value.get("authority", {}).get("provider_route_authorized_here") is not False
    ):
        raise _error("authenticated 2024 filing universe denominator drifted")
    paths: list[str] = []
    digests: list[str] = []
    page_count = 0
    represented_banks = set()
    for filing in filings:
        content = filing.get("content_ref") if type(filing) is dict else None
        bank = filing.get("bank") if type(filing) is dict else None
        path = content.get("path") if type(content) is dict else None
        digest = content.get("sha256") if type(content) is dict else None
        size = content.get("size_bytes") if type(content) is dict else None
        pages = filing.get("page_count") if type(filing) is dict else None
        parts = path.split("/") if type(path) is str else []
        if (
            bank not in banks
            or len(parts) < 4
            or parts[:3] != ["vietstock_bctc", bank, str(REPORTING_YEAR)]
            or filing.get("year") != REPORTING_YEAR
            or filing.get("provider_disposition") != "NEW_VERTEX_FLEX_FRONTIER"
            or type(size) is not int
            or size <= 0
            or type(pages) is not int
            or pages <= 0
        ):
            raise _error("authenticated 2024 filing is invalid")
        paths.append(path)
        digests.append(_checked_digest(digest))
        page_count += pages
        represented_banks.add(bank)
    if (
        represented_banks != set(banks)
        or paths != sorted(set(paths))
        or len(digests) != len(set(digests))
        or summary.get("bank_count") != 27
        or summary.get("candidate_filing_count") != len(filings)
        or summary.get("candidate_page_count") != page_count
        or summary.get("provider_call_candidate_page_count") != page_count
        or summary.get("reuse_existing_candidate_page_count") != 0
    ):
        raise _error("authenticated 2024 filing frontier is not unique and exhaustive")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key not in {"authenticated_universe_id", "universe_id"}
    }
    if value.get("authenticated_universe_id") != "bankfilingauthv1:" + (
        canonical_json_sha256_v1(material)
    ):
        raise _error("authenticated 2024 universe identity drifted")
    return canonical_clone_v1(value)


def _protected_2025_current_binding_v1(value: Any) -> dict[str, Any]:
    checked = validate_gemini_json_first_vertex_flex_expansion_v1(value)
    prior = checked["already_processed_corpus_binding"]
    plan = checked["corpus_plan"]
    paths = list(prior["relative_paths"])
    digests = list(prior["source_sha256s"])
    for item in plan["documents"]:
        document = item["document"]
        paths.append(document["relative_path"])
        digests.append(_checked_digest(document["source_sha256"]))
    if len(paths) != len(set(paths)) or len(digests) != len(set(digests)):
        raise _error("protected 2025-current source identities are not unique")
    material = {
        "already_processed_corpus_manifest_index_id": prior["corpus_manifest_index_id"],
        "completed_document_count": prior["document_count"],
        "completed_page_count": prior["page_count"],
        "document_count": prior["document_count"] + plan["summary"]["document_count"],
        "expansion_plan_id": checked["expansion_plan_id"],
        "page_count": prior["page_count"] + plan["summary"]["page_count"],
        "paid_corpus_plan_id": plan["corpus_plan_id"],
        "paid_document_count": plan["summary"]["document_count"],
        "paid_page_count": plan["summary"]["page_count"],
        "protected_bundle_sha256": canonical_json_sha256_v1(checked),
        "relative_paths": sorted(paths),
        "source_sha256s": sorted(digests),
    }
    return {
        **material,
        "binding_id": "gjfprotectedv1:" + canonical_json_sha256_v1(material),
    }


def _execution_contract_v1() -> dict[str, Any]:
    return {
        "allow_provider_fallbacks": True,
        "direct_google_api_allowed": False,
        "fallback_condition": "VERTEX_FLEX_UNAVAILABLE",
        "fallback_policy": "CHEAPEST_COMPATIBLE_STANDARD_ENDPOINT",
        "fallback_provider": OPENROUTER_STANDARD_FALLBACK_PROVIDER,
        "fallback_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
        "gateway": "OPENROUTER",
        "model": OPENROUTER_MODEL,
        "provider": OPENROUTER_PROVIDER,
        "route_policy": "FLEX_THEN_STANDARD",
        "service_tier": OPENROUTER_SERVICE_TIER,
        "supervisor_required_flag": "--openrouter-only",
    }


def build_gemini_json_first_vertex_flex_expansion_2024_v1(
    authenticated_universe: dict[str, Any],
    *,
    protected_2025_current_expansion: dict[str, Any],
    vietnamese_page_scope: dict[str, Any],
    dpi: int = 300,
    workers: int = 20,
) -> dict[str, Any]:
    """Build the 2024 paid frontier after exact source/page no-resubmit checks."""

    universe = _checked_authenticated_universe_v1(authenticated_universe)
    protected = _protected_2025_current_binding_v1(protected_2025_current_expansion)
    language_scope = validate_gemini_json_first_vietnamese_page_scope_v1(vietnamese_page_scope)
    scope_by_path = {item["relative_path"]: item for item in language_scope["documents"]}
    expected_review_paths = {
        filing["content_ref"]["path"]
        for filing in universe["filings"]
        if filing["bank"] == "OCB"
        or filing["page_count"] > language_scope["policy"]["review_pdf_over_pages"]
    }
    if set(scope_by_path) != expected_review_paths:
        raise _error("Vietnamese page scope is not exhaustive for 2024 OCB and long PDFs")

    protected_paths = set(protected["relative_paths"])
    protected_digests = set(protected["source_sha256s"])
    documents = []
    for filing in universe["filings"]:
        content = filing["content_ref"]
        path = content["path"]
        digest = content["sha256"]
        if path in protected_paths or digest in protected_digests:
            raise _error("2024 paid frontier overlaps protected 2025-current source identity")
        source_pages = filing["page_count"]
        selected_pages = source_pages
        document = {
            "page_count": selected_pages,
            "relative_path": path,
            "source_sha256": digest,
            "source_size_bytes": content["size_bytes"],
        }
        scope = scope_by_path.get(path)
        if scope is not None:
            if scope["source_page_count"] != source_pages:
                raise _error("2024 Vietnamese page scope source page count drifted")
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
    plan = build_gemini_json_first_corpus_plan_v1(
        documents,
        dpi=dpi,
        openrouter_page_fraction="1.0",
        openrouter_workers=workers,
    )
    selected_pages = sum(document["page_count"] for document in documents)
    if (
        plan["summary"]["document_count"] != len(universe["filings"])
        or plan["summary"]["page_count"] != selected_pages
        or plan["summary"]["route_pages"] != {GOOGLE_ROUTE: 0, OPENROUTER_ROUTE: selected_pages}
        or any(item["route"] != OPENROUTER_ROUTE for item in plan["documents"])
        or any(
            task["route"] != OPENROUTER_ROUTE
            for item in plan["documents"]
            for task in item["tasks"]
        )
    ):
        raise _error("2024 plan is not exclusively routed through OpenRouter Vertex Flex")
    material = {
        "authenticated_universe_id": universe["authenticated_universe_id"],
        "corpus_plan": plan,
        "execution_contract": _execution_contract_v1(),
        "format_version": FORMAT_VERSION,
        "protected_2025_current_binding": protected,
        "vietnamese_page_scope": language_scope,
    }
    return {
        **canonical_clone_v1(material),
        "expansion_plan_id": "gjfvertexflex2024v1:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_first_vertex_flex_expansion_2024_v1(
    value: dict[str, Any],
    *,
    authenticated_universe: dict[str, Any],
    protected_2025_current_expansion: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild from both authorities and exact-compare the 2024 bundle."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("2024 Vertex Flex expansion bundle is invalid")
    plan = value.get("corpus_plan")
    policy = plan.get("policy") if type(plan) is dict else None
    if type(policy) is not dict:
        raise _error("2024 Vertex Flex plan policy is invalid")
    rebuilt = build_gemini_json_first_vertex_flex_expansion_2024_v1(
        authenticated_universe,
        protected_2025_current_expansion=protected_2025_current_expansion,
        vietnamese_page_scope=value.get("vietnamese_page_scope"),
        dpi=policy.get("dpi"),
        workers=policy.get("openrouter_workers"),
    )
    if rebuilt != value:
        raise _error("2024 Vertex Flex expansion does not replay from its authorities")
    return canonical_clone_v1(value)
