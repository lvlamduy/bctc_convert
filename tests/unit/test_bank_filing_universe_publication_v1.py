from __future__ import annotations

import hashlib
from pathlib import Path

import fitz

from bctc_ai.evaluation.bank_filing_universe_publication_v1 import (
    authenticate_bank_filing_universe_sources_v1,
    render_bank_filing_universe_markdown_v1,
)


def test_authenticates_page_count_and_renders_human_first_inventory(tmp_path: Path) -> None:
    relative = "vietstock_bctc/AAA/2025/BCTC Hợp nhất năm 2025.pdf"
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(source)
    document.close()
    (tmp_path / "authenticated-hardlink.pdf").hardlink_to(source)
    payload = source.read_bytes()
    filing = {
        "bank": "AAA",
        "content_ref": {
            "path": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "filename_hints_non_authoritative": {
            "assurance": "AUDITED",
            "period": "ANNUAL",
            "scope": "CONSOLIDATED",
        },
        "provider_disposition": "NEW_VERTEX_FLEX_FRONTIER",
        "source_authentication_flags": [],
        "year": 2025,
    }
    universe = {
        "as_of_date": "2025-12-31",
        "already_processed_bank_codes": [],
        "already_processed_corpus_ref": {
            "bank_codes": [],
            "document_count": 0,
            "manifest_index_id": "gjfccmiv1:index:test",
            "page_count": 0,
        },
        "authority": {},
        "bank_codes": ["AAA"],
        "exact_duplicate_contents": [],
        "excluded_counts": {},
        "filings": [filing],
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1",
        "from_year": 2025,
        "new_bank_codes": ["AAA"],
        "source_inventory_ref": {},
        "source_snapshot_manifest_uri": "s3://bucket/snapshots/x/manifest-x.json",
        "summary": {
            "bank_count": 1,
            "already_processed_bank_count": 0,
            "candidate_filing_count": 1,
            "candidate_source_bytes": len(payload),
            "exact_duplicate_path_count": 0,
            "new_bank_count": 1,
            "provider_call_candidate_filing_count": 1,
            "provider_call_candidate_source_bytes": len(payload),
            "provider_call_source_authentication_required_count": 0,
            "requested_registered_pdf_path_count": 1,
            "reuse_existing_candidate_filing_count": 0,
            "source_authentication_required_count": 0,
        },
        "universe_id": "bankfilinguniversev1:test",
    }

    authenticated = authenticate_bank_filing_universe_sources_v1(universe, source_root=tmp_path)
    markdown = render_bank_filing_universe_markdown_v1(authenticated)

    assert authenticated["summary"]["candidate_page_count"] == 2
    assert authenticated["summary"]["provider_call_candidate_page_count"] == 2
    assert authenticated["filings"][0]["page_count"] == 2
    assert "| 1 | AAA | Vertex Flex mới | 1 | 0 | 1 | 2 | 0 |" in markdown
    assert "BCTC Hợp nhất năm 2025.pdf" in markdown
    assert "NOT_OBSERVED" in markdown
    assert "SHA" not in markdown.split("## Truy vết kỹ thuật", 1)[0]
