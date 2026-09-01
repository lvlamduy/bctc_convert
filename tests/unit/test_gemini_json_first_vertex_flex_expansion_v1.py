from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import OPENROUTER_ROUTE
from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (
    GeminiJsonFirstVertexFlexExpansionV1Error,
    build_gemini_json_first_vertex_flex_expansion_v1,
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
        "filings": filings,
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1",
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


def test_expansion_plan_routes_every_document_only_to_openrouter_vertex_flex() -> None:
    result = build_gemini_json_first_vertex_flex_expansion_v1(
        _universe(),
        already_processed_corpus_manifest_index=_already_processed_manifest(),
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
        )


def test_validator_rejects_completed_bank_even_after_coherent_rehash() -> None:
    result = build_gemini_json_first_vertex_flex_expansion_v1(
        _universe(),
        already_processed_corpus_manifest_index=_already_processed_manifest(),
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
        )
