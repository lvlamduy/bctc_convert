from __future__ import annotations

from bctc_ai.evaluation.bank_filing_universe_2024_v1 import (
    build_bank_filing_universe_2024_v1,
)

BANKS = tuple(f"B{ordinal:02d}" for ordinal in range(1, 28))


def _record(
    bank: str,
    *,
    digest: str,
    filename: str = "BCTC Hợp nhất năm 2024.pdf",
    kind: str = "FULL_FINANCIAL_STATEMENT_CANDIDATE",
    language: str = "VI",
    source_type: str = "UNASSESSED_REQUIRES_PDF_INSPECTION",
) -> dict[str, object]:
    value = digest if len(digest) == 64 else digest * 64
    path = f"vietstock_bctc/{bank}/2024/{filename}"
    return {
        "bank": bank,
        "dataset_role": None,
        "document_id": f"sha256:{value}",
        "duplicate_content_path_count": 1,
        "filename_metadata": {
            "assurance_hint": "AUDITED",
            "document_kind": kind,
            "document_kind_evidence": ["bctc"],
            "language_hint": language,
            "metadata_authority": "FILENAME_DERIVED_NON_AUTHORITATIVE",
            "normalized_filename": filename.casefold(),
            "reporting_period_hint": "ANNUAL",
            "reporting_year": 2024,
            "scope_hint": "CONSOLIDATED",
            "source_type_hint": source_type,
        },
        "relative_path": path,
        "sha256": value,
        "size_bytes": 1000,
        "source_survey_status": "NOT_YET_SOURCE_INSPECTED",
        "year": 2024,
    }


def _build(documents: list[dict[str, object]]) -> dict[str, object]:
    return build_bank_filing_universe_2024_v1(
        {
            "documents": documents,
            "format_version": "BANK_CORPUS_SURVEY_INVENTORY_RESULT_V1",
            "status": "COMPLETE_REGISTERED_BANK_PDF_METADATA_INVENTORY",
        },
        bank_codes=BANKS,
        as_of_date="2026-09-02",
        source_inventory_ref={
            "path": "inventory.json",
            "sha256": "a" * 64,
            "size_bytes": 1,
        },
        source_snapshot_manifest_uri=(
            "s3://bucket/prefix/snapshots/snapshot/manifest-" + "b" * 64 + ".json"
        ),
    )


def test_selects_all_27_banks_as_new_2024_content_frontier() -> None:
    documents = [
        _record(bank, digest=f"{ordinal:064x}") for ordinal, bank in enumerate(BANKS, start=1)
    ]

    result = _build(documents)

    assert result["format_version"] == "BANK_FILING_UNIVERSE_27BANK_2024_V1"
    assert result["reporting_year"] == 2024
    assert result["summary"] == {
        "bank_count": 27,
        "candidate_filing_count": 27,
        "candidate_source_bytes": 27_000,
        "exact_duplicate_path_count": 0,
        "registered_pdf_path_count": 27,
        "source_authentication_required_count": 0,
    }
    assert {item["provider_disposition"] for item in result["filings"]} == {
        "NEW_VERTEX_FLEX_FRONTIER"
    }
    assert result["authority"]["provider_route_authorized_here"] is False


def test_deduplicates_exact_content_and_accounts_every_excluded_source() -> None:
    documents = [
        _record(bank, digest=f"{ordinal:064x}") for ordinal, bank in enumerate(BANKS, start=1)
    ]
    kept = _record(BANKS[0], digest="f", filename="BCTC năm 2024.pdf")
    duplicate = _record(
        BANKS[0],
        digest="f",
        filename="BCTC năm 2024 bản tra cứu.pdf",
        source_type="SEARCHABLE_FILENAME_HINT",
    )
    documents[0] = kept
    documents.extend(
        [
            duplicate,
            _record(
                BANKS[0],
                digest="e",
                filename="Thuyết minh riêng.pdf",
                kind="SUPPORTING_OR_PARTIAL_DOCUMENT",
            ),
            _record(
                BANKS[0],
                digest="d",
                filename="Financial statements.pdf",
                language="EN",
            ),
        ]
    )

    result = _build(documents)

    assert result["summary"]["candidate_filing_count"] == 27
    assert result["summary"]["registered_pdf_path_count"] == 30
    assert result["summary"]["exact_duplicate_path_count"] == 1
    assert result["excluded_counts"] == {
        "EXACT_DUPLICATE_CONTENT": 1,
        "NON_VI_FULL_FINANCIAL_STATEMENT": 1,
        "SUPPORTING_OR_PARTIAL_DOCUMENT": 1,
    }
    assert result["exact_duplicate_contents"] == [
        {
            "kept_path": kept["relative_path"],
            "omitted_path": duplicate["relative_path"],
            "sha256": "f" * 64,
        }
    ]
