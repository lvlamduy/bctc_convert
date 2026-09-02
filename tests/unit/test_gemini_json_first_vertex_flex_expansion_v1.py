from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import OPENROUTER_ROUTE
from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (
    GeminiJsonFirstVertexFlexExpansionV1Error,
    build_gemini_json_first_vertex_flex_expansion_v1,
    build_gemini_json_first_vietnamese_page_scope_v1,
    validate_gemini_json_first_vertex_flex_expansion_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _universe() -> dict[str, object]:
    processed = ["ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"]
    new = [f"N{ordinal:02d}" for ordinal in range(1, 20)]
    filings = []
    for ordinal, bank in enumerate(sorted([*processed, *new]), start=1):
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
                    if bank in processed
                    else "NEW_VERTEX_FLEX_FRONTIER"
                ),
                "source_authentication_flags": [],
                "year": 2025,
            }
        )
    return {
        "already_processed_bank_codes": processed,
        "already_processed_corpus_ref": {
            "bank_codes": processed,
            "document_count": 8,
            "manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
            "page_count": 8,
        },
        "authenticated_universe_id": "bankfilingauthv1:" + "a" * 64,
        "as_of_date": "2026-09-01",
        "filings": filings,
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1",
        "from_year": 2025,
        "local_source_authentication": {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        },
        "new_bank_codes": new,
        "summary": {
            "bank_count": 27,
            "already_processed_bank_count": 8,
            "candidate_filing_count": 27,
            "candidate_page_count": 27,
            "new_bank_count": 19,
            "provider_call_candidate_filing_count": 19,
            "provider_call_candidate_page_count": 19,
        },
    }


def _already_processed_manifest() -> dict[str, object]:
    processed = ["ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"]
    return {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
        "documents": [
            {
                "relative_path": f"vietstock_bctc/{bank}/2025/report.pdf",
                "source_sha256": f"{ordinal + 100:064x}",
            }
            for ordinal, bank in enumerate(processed, start=1)
        ],
        "format_version": "GEMINI_CURRENT_CORPUS_MANIFEST_INDEX_V1",
        "summary": {"document_count": 8, "page_count": 8},
    }


def _language_scope() -> dict[str, object]:
    return build_gemini_json_first_vietnamese_page_scope_v1([])


def test_expansion_plan_routes_every_document_only_to_openrouter_vertex_flex() -> None:
    result = build_gemini_json_first_vertex_flex_expansion_v1(
        _universe(),
        already_processed_corpus_manifest_index=_already_processed_manifest(),
        vietnamese_page_scope=_language_scope(),
    )

    assert result["execution_contract"] == {
        "allow_provider_fallbacks": False,
        "direct_google_api_allowed": False,
        "gateway": "OPENROUTER",
        "model": "google/gemini-3.7-flash",
        "provider": "google-vertex/global/flex",
        "service_tier": "flex",
        "supervisor_required_flag": "--openrouter-only",
    }
    assert result["corpus_plan"]["summary"]["route_pages"] == {
        "GOOGLE_GEMINI_BATCH_API": 0,
        OPENROUTER_ROUTE: 19,
    }
    assert result["corpus_plan"]["summary"]["document_count"] == 19
    assert {
        item["document"]["relative_path"].split("/")[1]
        for item in result["corpus_plan"]["documents"]
    } == {f"N{ordinal:02d}" for ordinal in range(1, 20)}
    assert all(item["route"] == OPENROUTER_ROUTE for item in result["corpus_plan"]["documents"])
    assert validate_gemini_json_first_vertex_flex_expansion_v1(result) == result


def test_provider_or_bundle_identity_tamper_is_rejected() -> None:
    result = build_gemini_json_first_vertex_flex_expansion_v1(
        _universe(),
        already_processed_corpus_manifest_index=_already_processed_manifest(),
        vietnamese_page_scope=_language_scope(),
    )
    forged = copy.deepcopy(result)
    forged["execution_contract"]["allow_provider_fallbacks"] = True

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="exclusive execution contract drifted",
    ):
        validate_gemini_json_first_vertex_flex_expansion_v1(forged)


def test_already_processed_bank_cannot_enter_paid_frontier() -> None:
    universe = _universe()
    acb = next(item for item in universe["filings"] if item["bank"] == "ACB")
    acb["provider_disposition"] = "NEW_VERTEX_FLEX_FRONTIER"

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="already-processed bank entered",
    ):
        build_gemini_json_first_vertex_flex_expansion_v1(
            universe,
            already_processed_corpus_manifest_index=_already_processed_manifest(),
            vietnamese_page_scope=_language_scope(),
        )


@pytest.mark.parametrize("year", [2024, 2027])
def test_filing_outside_2025_current_period_scope_is_rejected(year: int) -> None:
    universe = _universe()
    filing = next(
        item
        for item in universe["filings"]
        if item["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER"
    )
    filing["year"] = year
    filing["content_ref"]["path"] = filing["content_ref"]["path"].replace("/2025/", f"/{year}/")

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="outside the authenticated 2025-current period scope",
    ):
        build_gemini_json_first_vertex_flex_expansion_v1(
            universe,
            already_processed_corpus_manifest_index=_already_processed_manifest(),
            vietnamese_page_scope=_language_scope(),
        )


def test_validator_rejects_a_2024_plan_path_even_before_identity_check() -> None:
    result = build_gemini_json_first_vertex_flex_expansion_v1(
        _universe(),
        already_processed_corpus_manifest_index=_already_processed_manifest(),
        vietnamese_page_scope=_language_scope(),
    )
    forged = copy.deepcopy(result)
    forged["corpus_plan"]["documents"][0]["document"]["relative_path"] = forged["corpus_plan"][
        "documents"
    ][0]["document"]["relative_path"].replace("/2025/", "/2024/")

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="corpus plan source path is invalid",
    ):
        validate_gemini_json_first_vertex_flex_expansion_v1(forged)


def test_validator_rejects_completed_bank_even_after_coherent_rehash() -> None:
    result = build_gemini_json_first_vertex_flex_expansion_v1(
        _universe(),
        already_processed_corpus_manifest_index=_already_processed_manifest(),
        vietnamese_page_scope=_language_scope(),
    )
    forged = copy.deepcopy(result)
    document = forged["corpus_plan"]["documents"][0]["document"]
    document["relative_path"] = document["relative_path"].replace(
        "vietstock_bctc/N01/", "vietstock_bctc/ACB/"
    )
    material = {key: value for key, value in forged.items() if key != "expansion_plan_id"}
    forged["expansion_plan_id"] = "gjfvertexflexv1:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="exclusive execution contract drifted",
    ):
        validate_gemini_json_first_vertex_flex_expansion_v1(forged)


def test_paid_frontier_cannot_repeat_prior_corpus_bytes_under_a_new_bank() -> None:
    universe = _universe()
    new_filing = next(
        filing
        for filing in universe["filings"]
        if filing["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER"
    )
    new_filing["content_ref"]["sha256"] = _already_processed_manifest()["documents"][0][
        "source_sha256"
    ]

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="overlaps the already-processed corpus",
    ):
        build_gemini_json_first_vertex_flex_expansion_v1(
            universe,
            already_processed_corpus_manifest_index=_already_processed_manifest(),
            vietnamese_page_scope=_language_scope(),
        )


def test_long_pdf_is_trimmed_only_by_an_exact_human_reviewed_vietnamese_scope() -> None:
    universe = _universe()
    filing = next(item for item in universe["filings"] if item["bank"] == "N01")
    filing["page_count"] = 120
    scope = build_gemini_json_first_vietnamese_page_scope_v1(
        [
            {
                "included_last_physical_page": 60,
                "relative_path": filing["content_ref"]["path"],
                "review_conclusion": "VIETNAMESE_PREFIX_EXCLUDES_NON_VIETNAMESE_APPENDIX",
                "source_page_count": 120,
            }
        ]
    )

    result = build_gemini_json_first_vertex_flex_expansion_v1(
        universe,
        already_processed_corpus_manifest_index=_already_processed_manifest(),
        vietnamese_page_scope=scope,
    )

    planned = next(
        item
        for item in result["corpus_plan"]["documents"]
        if item["document"]["relative_path"] == filing["content_ref"]["path"]
    )
    assert planned["document"]["page_count"] == 60
    assert planned["document"]["source_page_count"] == 120
    assert planned["tasks"][0]["last_physical_page"] == 60
    assert result["corpus_plan"]["summary"]["page_count"] == 78
    assert validate_gemini_json_first_vertex_flex_expansion_v1(result) == result

    with pytest.raises(
        GeminiJsonFirstVertexFlexExpansionV1Error,
        match="not exhaustive",
    ):
        build_gemini_json_first_vertex_flex_expansion_v1(
            universe,
            already_processed_corpus_manifest_index=_already_processed_manifest(),
            vietnamese_page_scope=_language_scope(),
        )
