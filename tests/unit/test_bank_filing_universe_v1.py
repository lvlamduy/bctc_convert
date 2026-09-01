from __future__ import annotations

from bctc_ai.evaluation.bank_filing_universe_v1 import build_bank_filing_universe_v1

BANKS = tuple(f"B{ordinal:02d}" for ordinal in range(1, 28))


def _record(
    bank: str,
    *,
    digest_character: str,
    filename: str = "BCTC Hợp nhất quý 1 năm 2025.pdf",
    kind: str = "FULL_FINANCIAL_STATEMENT_CANDIDATE",
    language: str = "VI",
    scope: str = "CONSOLIDATED",
    period: str = "Q1",
    assurance: str = "UNKNOWN",
    source_type: str = "UNASSESSED_REQUIRES_PDF_INSPECTION",
) -> dict[str, object]:
    digest = digest_character if len(digest_character) == 64 else digest_character * 64
    path = f"vietstock_bctc/{bank}/2025/{filename}"
    return {
        "bank": bank,
        "dataset_role": None,
        "document_id": f"sha256:{digest}",
        "duplicate_content_path_count": 1,
        "filename_metadata": {
            "assurance_hint": assurance,
            "document_kind": kind,
            "document_kind_evidence": ["bctc"],
            "language_hint": language,
            "metadata_authority": "FILENAME_DERIVED_NON_AUTHORITATIVE",
            "normalized_filename": filename.casefold(),
            "reporting_period_hint": period,
            "reporting_year": 2025,
            "scope_hint": scope,
            "source_type_hint": source_type,
        },
        "relative_path": path,
        "sha256": digest,
        "size_bytes": 1000,
        "source_survey_status": "NOT_YET_SOURCE_INSPECTED",
        "year": 2025,
    }


def _inventory(documents: list[dict[str, object]]) -> dict[str, object]:
    return {
        "documents": documents,
        "format_version": "BANK_CORPUS_SURVEY_INVENTORY_RESULT_V1",
        "status": "COMPLETE_REGISTERED_BANK_PDF_METADATA_INVENTORY",
    }


def _build(documents: list[dict[str, object]]) -> dict[str, object]:
    return build_bank_filing_universe_v1(
        _inventory(documents),
        bank_codes=BANKS,
        from_year=2025,
        as_of_date="2026-09-01",
        source_inventory_ref={"path": "inventory.json", "sha256": "a" * 64, "size_bytes": 1},
        source_snapshot_manifest_uri=(
            "s3://bucket/prefix/snapshots/snapshot/manifest-" + "b" * 64 + ".json"
        ),
        already_processed_bank_codes=BANKS[:8],
        already_processed_corpus_ref={
            "bank_codes": list(BANKS[:8]),
            "document_count": 140,
            "manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
            "page_count": 8_947,
        },
    )


def test_keeps_all_vietnamese_full_statements_and_seals_ambiguous_hints() -> None:
    documents = [
        _record(bank, digest_character=f"{ordinal:064x}")
        for ordinal, bank in enumerate(BANKS, start=1)
    ]
    documents[0] = _record(
        BANKS[0],
        digest_character="e",
        scope="UNKNOWN",
        period="UNKNOWN",
        assurance="UNKNOWN",
    )

    result = _build(documents)

    assert result["summary"] == {
        "bank_count": 27,
        "already_processed_bank_count": 8,
        "already_processed_corpus_filing_count": 140,
        "already_processed_corpus_page_count": 8_947,
        "candidate_filing_count": 27,
        "candidate_source_bytes": 27_000,
        "exact_duplicate_path_count": 0,
        "new_bank_count": 19,
        "provider_call_candidate_filing_count": 19,
        "provider_call_candidate_source_bytes": 19_000,
        "provider_call_source_authentication_required_count": 19,
        "requested_registered_pdf_path_count": 27,
        "reuse_existing_candidate_filing_count": 8,
        "source_authentication_required_count": 27,
    }
    first = result["filings"][0]
    assert first["source_authentication_flags"] == [
        "SCOPE_REQUIRES_SOURCE_AUTHENTICATION",
        "PERIOD_REQUIRES_SOURCE_AUTHENTICATION",
        "ASSURANCE_REQUIRES_SOURCE_AUTHENTICATION",
    ]
    assert result["authority"]["filename_hints_used_as_accounting_evidence"] is False
    assert result["filings"][0]["provider_disposition"] == "REUSE_EXISTING_GEMINI_JSON"
    assert result["filings"][-1]["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER"


def test_exact_content_duplicates_are_omitted_but_searchable_copy_is_not_preferred() -> None:
    documents = [
        _record(bank, digest_character=f"{ordinal:064x}")
        for ordinal, bank in enumerate(BANKS, start=1)
    ]
    raw = _record(BANKS[0], digest_character="f", filename="BCTC quý 1.pdf")
    searchable = _record(
        BANKS[0],
        digest_character="f",
        filename="BCTC quý 1 bản tra cứu.pdf",
        source_type="SEARCHABLE_FILENAME_HINT",
    )
    documents[0] = raw
    documents.append(searchable)

    result = _build(documents)

    assert result["summary"]["candidate_filing_count"] == 27
    assert result["summary"]["exact_duplicate_path_count"] == 1
    assert result["filings"][0]["content_ref"]["path"] == raw["relative_path"]
    assert result["exact_duplicate_contents"] == [
        {
            "kept_path": raw["relative_path"],
            "omitted_path": searchable["relative_path"],
            "sha256": "f" * 64,
        }
    ]


def test_supporting_and_non_vietnamese_documents_receive_non_candidate_dispositions() -> None:
    documents = [
        _record(bank, digest_character=f"{ordinal:064x}")
        for ordinal, bank in enumerate(BANKS, start=1)
    ]
    documents.extend(
        [
            _record(
                BANKS[0],
                digest_character="d",
                filename="Thuyết minh BCTC.pdf",
                kind="SUPPORTING_OR_PARTIAL_DOCUMENT",
            ),
            _record(
                BANKS[0],
                digest_character="c",
                filename="Financial statements.pdf",
                language="EN",
            ),
        ]
    )

    result = _build(documents)

    assert result["excluded_counts"] == {
        "NON_VI_FULL_FINANCIAL_STATEMENT": 1,
        "SUPPORTING_OR_PARTIAL_DOCUMENT": 1,
    }
    assert result["summary"]["requested_registered_pdf_path_count"] == 29
