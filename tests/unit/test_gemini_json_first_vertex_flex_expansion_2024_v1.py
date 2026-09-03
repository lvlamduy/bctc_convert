from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_2024_v1 import (
    GeminiJsonFirstVertexFlexExpansion2024V1Error,
    build_gemini_json_first_vertex_flex_expansion_2024_v1,
    validate_gemini_json_first_vertex_flex_expansion_2024_v1,
)
from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (
    build_gemini_json_first_vertex_flex_expansion_v1,
    build_gemini_json_first_vietnamese_page_scope_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

BANKS = [
    "ABB",
    "ACB",
    "BAB",
    "BID",
    "BVB",
    "CTG",
    "EIB",
    "HDB",
    "KLB",
    "LPB",
    "MBB",
    "MSB",
    "NAB",
    "NVB",
    "OCB",
    "PGB",
    "SGB",
    "SHB",
    "SSB",
    "STB",
    "TCB",
    "TPB",
    "VAB",
    "VBB",
    "VCB",
    "VIB",
    "VPB",
]
OLD_BANKS = ["ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"]


def _protected_expansion() -> dict[str, object]:
    new_banks = [f"N{ordinal:02d}" for ordinal in range(1, 20)]
    filings = []
    for ordinal, bank in enumerate(sorted([*OLD_BANKS, *new_banks]), start=101):
        filings.append(
            {
                "bank": bank,
                "content_ref": {
                    "path": f"vietstock_bctc/{bank}/2025/report.pdf",
                    "sha256": f"{ordinal:064x}",
                    "size_bytes": 100,
                },
                "filename_hints_non_authoritative": {},
                "page_count": 1,
                "provider_disposition": (
                    "REUSE_EXISTING_GEMINI_JSON"
                    if bank in OLD_BANKS
                    else "NEW_VERTEX_FLEX_FRONTIER"
                ),
                "source_authentication_flags": [],
                "year": 2025,
            }
        )
    universe = {
        "already_processed_bank_codes": OLD_BANKS,
        "already_processed_corpus_ref": {
            "bank_codes": OLD_BANKS,
            "document_count": len(OLD_BANKS),
            "manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
            "page_count": len(OLD_BANKS),
        },
        "as_of_date": "2026-09-01",
        "authenticated_universe_id": "bankfilingauthv1:" + "a" * 64,
        "filings": filings,
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1",
        "from_year": 2025,
        "local_source_authentication": {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        },
        "new_bank_codes": new_banks,
        "summary": {
            "already_processed_bank_count": 8,
            "bank_count": 27,
            "candidate_filing_count": 27,
            "candidate_page_count": 27,
            "new_bank_count": 19,
            "provider_call_candidate_filing_count": 19,
            "provider_call_candidate_page_count": 19,
        },
    }
    manifest = {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
        "documents": [
            {
                "relative_path": f"vietstock_bctc/{bank}/2025/old-report.pdf",
                "source_sha256": f"{ordinal:064x}",
            }
            for ordinal, bank in enumerate(OLD_BANKS, start=201)
        ],
        "format_version": "GEMINI_CURRENT_CORPUS_MANIFEST_INDEX_V1",
        "summary": {"document_count": 8, "page_count": 8},
    }
    return build_gemini_json_first_vertex_flex_expansion_v1(
        universe,
        already_processed_corpus_manifest_index=manifest,
        vietnamese_page_scope=build_gemini_json_first_vietnamese_page_scope_v1([]),
    )


def _universe(*, long_acb: bool = False) -> dict[str, object]:
    filings = []
    for ordinal, bank in enumerate(BANKS, start=1):
        pages = 120 if long_acb and bank == "ACB" else 1
        filings.append(
            {
                "bank": bank,
                "content_ref": {
                    "path": f"vietstock_bctc/{bank}/2024/report.pdf",
                    "sha256": f"{ordinal:064x}",
                    "size_bytes": 100,
                },
                "filename_hints_non_authoritative": {},
                "page_count": pages,
                "provider_disposition": "NEW_VERTEX_FLEX_FRONTIER",
                "source_authentication_flags": [],
                "year": 2024,
            }
        )
    page_count = sum(item["page_count"] for item in filings)
    material = {
        "authority": {"provider_route_authorized_here": False},
        "bank_codes": BANKS,
        "filings": filings,
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2024_V1",
        "local_source_authentication": {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        },
        "reporting_year": 2024,
        "summary": {
            "bank_count": 27,
            "candidate_filing_count": 27,
            "candidate_page_count": page_count,
            "provider_call_candidate_page_count": page_count,
            "reuse_existing_candidate_page_count": 0,
        },
    }
    return {
        **material,
        "authenticated_universe_id": "bankfilingauthv1:" + canonical_json_sha256_v1(material),
        "universe_id": "bankfiling2024v1:" + "f" * 64,
    }


def _scope(universe: dict[str, object], *, acb_cutoff: int | None = None) -> dict[str, object]:
    documents = []
    for filing in universe["filings"]:
        if filing["bank"] != "OCB" and filing["page_count"] <= 100:
            continue
        included = acb_cutoff if filing["bank"] == "ACB" and acb_cutoff else filing["page_count"]
        documents.append(
            {
                "included_last_physical_page": included,
                "relative_path": filing["content_ref"]["path"],
                "review_conclusion": (
                    "FULL_DOCUMENT_VIETNAMESE"
                    if included == filing["page_count"]
                    else "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX"
                ),
                "source_page_count": filing["page_count"],
            }
        )
    return build_gemini_json_first_vietnamese_page_scope_v1(documents)


def _build(*, long_acb: bool = False, acb_cutoff: int | None = None) -> tuple[dict, dict, dict]:
    universe = _universe(long_acb=long_acb)
    protected = _protected_expansion()
    result = build_gemini_json_first_vertex_flex_expansion_2024_v1(
        universe,
        protected_2025_current_expansion=protected,
        vietnamese_page_scope=_scope(universe, acb_cutoff=acb_cutoff),
    )
    return result, universe, protected


def test_all_27_banks_including_old_eight_enter_only_the_new_2024_frontier() -> None:
    result, universe, protected = _build()

    assert result["execution_contract"] == {
        "allow_provider_fallbacks": True,
        "direct_google_api_allowed": False,
        "fallback_condition": "VERTEX_FLEX_UNAVAILABLE",
        "fallback_policy": "CHEAPEST_COMPATIBLE_STANDARD_ENDPOINT",
        "fallback_provider": "google-ai-studio",
        "fallback_service_tier": "standard",
        "gateway": "OPENROUTER",
        "model": "google/gemini-3.7-flash",
        "provider": "google-vertex/global/flex",
        "route_policy": "FLEX_THEN_STANDARD",
        "service_tier": "flex",
        "supervisor_required_flag": "--openrouter-only",
    }
    assert result["corpus_plan"]["summary"]["document_count"] == 27
    assert result["corpus_plan"]["summary"]["route_pages"] == {
        "GOOGLE_GEMINI_BATCH_API": 0,
        "OPENROUTER_VERTEX_FLEX": 27,
    }
    assert set(OLD_BANKS) <= {
        item["document"]["relative_path"].split("/")[1]
        for item in result["corpus_plan"]["documents"]
    }
    assert result["protected_2025_current_binding"]["document_count"] == 27
    assert (
        validate_gemini_json_first_vertex_flex_expansion_2024_v1(
            result,
            authenticated_universe=universe,
            protected_2025_current_expansion=protected,
        )
        == result
    )


def test_any_protected_source_byte_overlap_is_rejected_even_for_a_2024_path() -> None:
    universe = _universe()
    protected = _protected_expansion()
    universe["filings"][0]["content_ref"]["sha256"] = protected["already_processed_corpus_binding"][
        "source_sha256s"
    ][0]
    material = {
        key: value
        for key, value in universe.items()
        if key not in {"authenticated_universe_id", "universe_id"}
    }
    universe["authenticated_universe_id"] = "bankfilingauthv1:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansion2024V1Error,
        match="overlaps protected",
    ):
        build_gemini_json_first_vertex_flex_expansion_2024_v1(
            universe,
            protected_2025_current_expansion=protected,
            vietnamese_page_scope=_scope(universe),
        )


def test_every_ocb_and_long_pdf_requires_one_exact_human_reviewed_scope() -> None:
    universe = _universe(long_acb=True)
    protected = _protected_expansion()
    complete_scope = _scope(universe, acb_cutoff=60)
    scope = build_gemini_json_first_vietnamese_page_scope_v1(
        [item for item in complete_scope["documents"] if "/OCB/" not in item["relative_path"]]
    )

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansion2024V1Error,
        match="not exhaustive",
    ):
        build_gemini_json_first_vertex_flex_expansion_2024_v1(
            universe,
            protected_2025_current_expansion=protected,
            vietnamese_page_scope=scope,
        )


def test_reviewed_prefix_is_explicit_in_plan_and_task_physical_pages() -> None:
    result, universe, protected = _build(long_acb=True, acb_cutoff=60)
    acb = next(
        item
        for item in result["corpus_plan"]["documents"]
        if item["document"]["relative_path"].split("/")[1] == "ACB"
    )

    assert acb["document"]["page_count"] == 60
    assert acb["document"]["source_page_count"] == 120
    assert acb["document"]["page_selection"]["included_last_physical_page"] == 60
    assert acb["tasks"] == [
        {
            **acb["tasks"][0],
            "first_physical_page": 1,
            "last_physical_page": 60,
        }
    ]
    assert validate_gemini_json_first_vertex_flex_expansion_2024_v1(
        result,
        authenticated_universe=universe,
        protected_2025_current_expansion=protected,
    )


def test_bundle_or_external_protected_authority_drift_is_rejected() -> None:
    result, universe, protected = _build()
    forged = copy.deepcopy(result)
    forged["execution_contract"]["direct_google_api_allowed"] = True

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansion2024V1Error,
        match="does not replay",
    ):
        validate_gemini_json_first_vertex_flex_expansion_2024_v1(
            forged,
            authenticated_universe=universe,
            protected_2025_current_expansion=protected,
        )

    changed_protected = copy.deepcopy(protected)
    changed_protected["execution_contract"]["allow_provider_fallbacks"] = True
    with pytest.raises(ValueError, match="exclusive execution contract drifted"):
        validate_gemini_json_first_vertex_flex_expansion_2024_v1(
            result,
            authenticated_universe=universe,
            protected_2025_current_expansion=changed_protected,
        )
