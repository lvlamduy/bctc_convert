from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    build_accounting_family_topology_scan_v1,
    validate_accounting_family_topology_scan_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "config/families/tm-cash-precious-metals-topology-v1.json"
PROFILES = {
    "ANNUAL_2025_CONSOLIDATED": ROOT
    / "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/semantic_index.json",
    "CURRENT_SELECTED_CONSOLIDATED": ROOT
    / "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json",
}


def _pages(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": line["source_bbox_raw_pixels"],
                    "source_line_index": line["source_line_index"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page_sequence,
        }
        for page_sequence, page in enumerate(document["pages"], 1)
    ]


def test_declarative_cash_topology_replays_two_real_eight_bank_profiles() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    observed: dict[str, dict[str, tuple[str, list[int]]]] = {}
    for profile, path in PROFILES.items():
        semantic_index = json.loads(path.read_text(encoding="utf-8"))
        profile_records = {}
        for document in semantic_index["documents"]:
            pages = _pages(document)
            result = build_accounting_family_topology_scan_v1(pages, spec)
            validate_accounting_family_topology_scan_replay_v1(result, pages, spec)
            profile_records[document["bank_code"]] = (
                result["status"],
                [region["page_sequence"] for region in result["regions"]],
            )
        observed[profile] = profile_records

    assert observed["ANNUAL_2025_CONSOLIDATED"] == {
        "ACB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [45]),
        "MBB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [46]),
        "VPB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [41]),
        "HDB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [33]),
        "VCB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [35]),
        "CTG": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [39]),
        "BID": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [39]),
        "VIB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [35]),
    }
    assert observed["CURRENT_SELECTED_CONSOLIDATED"] == {
        "ACB": ("UNRESOLVED_NO_COMPLETE_REGION", []),
        "MBB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [30]),
        "VPB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [38]),
        "HDB": ("UNRESOLVED_NO_COMPLETE_REGION", []),
        "VCB": ("UNRESOLVED_NO_COMPLETE_REGION", []),
        "CTG": ("UNRESOLVED_NO_COMPLETE_REGION", []),
        "BID": ("UNRESOLVED_NO_COMPLETE_REGION", []),
        "VIB": ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL", [31]),
    }
