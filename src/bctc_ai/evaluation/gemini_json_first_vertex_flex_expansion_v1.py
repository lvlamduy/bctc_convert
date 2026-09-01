"""Pinned OpenRouter Google Vertex Flex plan for the 27-bank expansion."""

from __future__ import annotations

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
ALREADY_PROCESSED_BANKS = frozenset({"ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"})


class GeminiJsonFirstVertexFlexExpansionV1Error(ValueError):
    """The expansion universe or its exclusive provider route drifted."""


def _error(message: str) -> GeminiJsonFirstVertexFlexExpansionV1Error:
    return GeminiJsonFirstVertexFlexExpansionV1Error(message)


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


def build_gemini_json_first_vertex_flex_expansion_v1(
    authenticated_universe: dict[str, Any],
    *,
    already_processed_corpus_manifest_index: dict[str, Any],
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
    documents = []
    for filing in filings:
        if type(filing) is not dict or type(filing.get("content_ref")) is not dict:
            raise _error("filing universe record is malformed")
        disposition = filing.get("provider_disposition")
        bank = filing.get("bank")
        if bank in ALREADY_PROCESSED_BANKS and disposition != "REUSE_EXISTING_GEMINI_JSON":
            raise _error("already-processed bank entered the paid provider frontier")
        if bank not in ALREADY_PROCESSED_BANKS and disposition != "NEW_VERTEX_FLEX_FRONTIER":
            raise _error("new bank is absent from the paid provider frontier")
        if disposition == "REUSE_EXISTING_GEMINI_JSON":
            continue
        if disposition != "NEW_VERTEX_FLEX_FRONTIER":
            raise _error("filing provider disposition is invalid")
        content = filing["content_ref"]
        documents.append(
            {
                "page_count": filing["page_count"],
                "relative_path": content["path"],
                "source_sha256": content["sha256"],
                "source_size_bytes": content["size_bytes"],
            }
        )
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
            OPENROUTER_ROUTE: summary["provider_call_candidate_page_count"],
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
    processed_binding = value.get("already_processed_corpus_binding")
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
    for item in plan_documents:
        document = item.get("document") if type(item) is dict else None
        path = document.get("relative_path") if type(document) is dict else None
        digest = document.get("source_sha256") if type(document) is dict else None
        if type(path) is not str or type(digest) is not str:
            raise _error("Vertex Flex corpus plan document is invalid")
        path_parts = path.split("/")
        if len(path_parts) < 4 or path_parts[0] != "vietstock_bctc":
            raise _error("Vertex Flex corpus plan source path is invalid")
        planned_bank_codes.append(path_parts[1])
        planned_relative_paths.append(path)
        planned_source_sha256s.append(digest)
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
