from __future__ import annotations

from collections import Counter
from pathlib import Path

from bctc_ai.evaluation.family_first_filing_inventory_v1 import (
    read_family_first_filing_inventory_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def test_tracked_markdown_projects_exact_140_filing_axis_without_matching_authority() -> None:
    result = read_family_first_filing_inventory_v1(ROOT)

    assert result["metrics"] == {
        "explicit_missing_filing_count": 4,
        "selected_filing_count": 140,
    }
    assert result["s3_snapshot_prefix"] == (
        "s3://test-s3-duylv/bctc-ai/snapshots/20260806T050030130746Z-4a469fab2334/"
    )
    assert result["authority"] == {
        "bank_path_period_scope_used_for_family_matching": False,
        "inventory_is_provenance_and_coverage_axis_only": True,
        "related_party_family_in_scope": False,
    }
    filings = result["filings"]
    assert Counter(item["scope"] for item in filings) == {
        "CONSOLIDATED": 70,
        "PARENT_OR_SEPARATE": 70,
    }
    assert Counter(item["period"] for item in filings) == {
        "ANNUAL": 16,
        "H1": 28,
        "Q1": 32,
        "Q2": 32,
        "Q3": 16,
        "Q4": 16,
    }
    assert Counter(item["assurance"] for item in filings) == {
        "AUDITED": 16,
        "REVIEWED": 34,
        "UNAUDITED": 90,
    }
    assert all(item["content_ref"]["path"].startswith("vietstock_bctc/") for item in filings)
    assert all(len(item["content_ref"]["sha256"]) == 64 for item in filings)


def test_only_hdb_and_bid_h1_2026_are_explicitly_missing() -> None:
    result = read_family_first_filing_inventory_v1(ROOT)

    assert {
        (item["bank_provenance"], item["year"], item["period"], item["scope"])
        for item in result["missing_filings"]
    } == {
        ("HDB", 2026, "H1", "CONSOLIDATED"),
        ("HDB", 2026, "H1", "PARENT_OR_SEPARATE"),
        ("BID", 2026, "H1", "CONSOLIDATED"),
        ("BID", 2026, "H1", "PARENT_OR_SEPARATE"),
    }
