#!/usr/bin/env python3
"""Run one multi-table hierarchical family over an authenticated JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
    resolved_gemini_family_region_repair_overlay_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (  # noqa: E402
    apply_gemini_family_effective_page_frontier_v1,
    effective_page_frontier_stages_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    page_json_region_repair_lineages_v1,
    query_selected_multitable_hierarchical_family_regions_v1,
    validate_selected_multitable_hierarchical_family_candidate_replays_v1,
)


class RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error(RuntimeError):
    """The corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error:
    return RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_MULTITABLE_HIERARCHICAL_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "2ef86d5406a1db4d7a4809a010e03b910a2ab2a784578854dcfde0eece93fbe0"
    ),
    "accepted_cluster_count": 78,
    "accepted_fragment_count": 297,
    "candidate_disposition_axis_sha256": (
        "3eb52512f32c57ad6d1616abb0a4e4c32b35e71dc05e77e3b83281409d8de8ec"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 62, READY: 78, UNRESOLVED: 0},
    "query_policy_sha256": "0b1196a0b9f7d4eb7a77b278411414615ab1f654eddce4f3196b809d9269dfc8",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 1290,
    "not_observed_count": 62,
    "ready_count": 78,
    "unresolved_count": 0,
}
PINNED_RELEASE_AUDIT_METRICS = {
    "equation_count": 374,
    "historical_comparator_exact_count": 208,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 192,
    "historical_mapping_record_count": 192,
    "mapping_count": 1290,
}
PINNED_RELEASE_AXIS_SHA256 = {
    "clusters": "6fb676b0da7ca42e7822505aeeff6403a506331cb9450753a984b97debb08da9",
    "equations": "854ce081fde9b8e8d801112a727677e1dbc9302e67138804177690688ed4e52d",
    "historical_comparator": ("cd9cedf6863246de57d4fc01896e00a350a6ae0ec2ce1698a3cff8b76d988496"),
    "mappings": "5f33a63aee79f1dba66c0328d39e8532db98127652000c3ef7e798fce12220e3",
}
PINNED_HISTORICAL_ORACLES = (
    {
        "format_version": "OTHER_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "3af246132f56e8ac1a09592ce8cd4c9e302fc2ee778fe03be6fe102a0e939f5f",
        "size_bytes": 175245,
    },
    {
        "format_version": "ANNUAL_2025_OTHER_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "9cdd259b4d0d3787e7f8f9da11dfbb654cedeaf10b6c227956edead2a7ee0548",
        "size_bytes": 396487,
    },
)
PINNED_GOVERNMENT_SBV_LIABILITIES_HISTORICAL_ORACLES = (
    {
        "format_version": "GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0074-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "0ccfc5b9d9c10ed288de065f0194668df47f51674d9034423559dd06c0ad5de6",
        "size_bytes": 105806,
    },
    {
        "format_version": (
            "ANNUAL_2025_GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
        ),
        "path": (
            "docs/experiments/"
            "E-0128-annual-2025-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "c5832f9d8a40e48dbb262cb2ecf4a1d442276b2f601da5c7be519e8b6538eea4",
        "size_bytes": 148324,
    },
)
PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_HISTORICAL_ORACLES = (
    {
        "format_version": "ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0075-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "72b9058963274d3a9a3fe509d183c46bcdbaf15f8220ae2e6b09a11a0862403e",
        "size_bytes": 39614,
    },
    {
        "format_version": (
            "ANNUAL_2025_ENTRUSTED_INVESTMENT_RISK_CAPITAL_8BANK_CODEX_VERIFIED_MAPPING_V1"
        ),
        "path": (
            "docs/experiments/"
            "E-0130-annual-2025-entrusted-investment-risk-capital-8bank-"
            "codex-verified-mapping-v1.json"
        ),
        "sha256": "2ce4fe69f7e8a0c73f2169fde63da1b067e68192efbaf95697d175a0dc219b14",
        "size_bytes": 81492,
    },
)
PINNED_ISSUED_VALUABLE_PAPERS_HISTORICAL_ORACLES = (
    {
        "format_version": "ISSUED_VALUABLE_PAPERS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "d2c9a85c2d5a0a4fbdfb47321a27054a85ed2bdf81db022ae0ec1015d16117af",
        "size_bytes": 196147,
    },
    {
        "format_version": ("ANNUAL_2025_ISSUED_VALUABLE_PAPERS_8BANK_CODEX_VERIFIED_MAPPING_V1"),
        "path": (
            "docs/experiments/"
            "E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "f2af00de94712cb2d46bdac149e401919b5681ccdb8fcb9afcc3afa161ad2e03",
        "size_bytes": 244921,
    },
)
PINNED_OTHER_PAYABLES_LIABILITIES_HISTORICAL_ORACLES = (
    {
        "format_version": "OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0077-other-payables-liabilities-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "0c5e01ee030f99a2743e65206c24ae2068424314eec0982c8693176fccea8347",
        "size_bytes": 153436,
    },
    {
        "format_version": (
            "ANNUAL_2025_OTHER_PAYABLES_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
        ),
        "path": (
            "docs/experiments/"
            "E-0132-annual-2025-other-payables-liabilities-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "db7f0ee789b83fb0482562740ad5bd514a901a910d7cc5cabb36d855cc2e7121",
        "size_bytes": 247155,
    },
)
PINNED_INTEREST_INCOME_HISTORICAL_ORACLES = (
    {
        "format_version": "INTEREST_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0079-interest-income-8bank-codex-verified-mapping-v1.json",
        "sha256": "6a3e862b0896c63f5270563bc8785a2f5bbe89a75536aad0de5bf14da1ee68fc",
        "size_bytes": 147949,
    },
    {
        "format_version": "ANNUAL_2025_INTEREST_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0134-annual-2025-interest-income-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "09b63070d3aec7af65787eb05e2bb35c7519a380d97695a103091f0b5c4613f3",
        "size_bytes": 146768,
    },
)
PINNED_INTEREST_EXPENSE_HISTORICAL_ORACLES = (
    {
        "format_version": "INTEREST_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0081-interest-expense-8bank-codex-verified-mapping-v1.json",
        "sha256": "e9a49c0d594290da6082c42798bc1904c5a58ca23de122a3d2140cd59790c580",
        "size_bytes": 119015,
    },
    {
        "format_version": "ANNUAL_2025_INTEREST_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0135-annual-2025-interest-expense-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "52fe4c56b2d0dd1d4528752301eca771414f132f30ff3e7ef11a44189bf77774",
        "size_bytes": 114053,
    },
)
PINNED_SERVICE_ACTIVITY_HISTORICAL_ORACLES = (
    {
        "format_version": "SERVICE_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0082-service-activity-8bank-codex-verified-mapping-v1.json",
        "sha256": "a49d6f3c8704faaf1e586aef6a8641a934ff0ba720c837c823e7e4395745c327",
        "size_bytes": 107708,
    },
    {
        "format_version": "ANNUAL_2025_SERVICE_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "99b47e270fce24884c19c524d72e972feda530098618b6cad0cde02588d20f86",
        "size_bytes": 238146,
    },
)
PINNED_FX_GOLD_ACTIVITY_HISTORICAL_ORACLES = (
    {
        "format_version": "FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0083-fx-gold-activity-8bank-codex-verified-mapping-v1.json",
        "sha256": "fcda9c3cbf06a639b375af5ef453553eefabb47a9116d91540ebcb361622cefe",
        "size_bytes": 68488,
    },
    {
        "format_version": "ANNUAL_2025_FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0138-annual-2025-fx-gold-activity-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "6dbbae7357fcfee17f3f427be649518f01bdd227151e1e39eeb08a5390647f3b",
        "size_bytes": 195470,
    },
)
PINNED_TRADING_SECURITIES_ACTIVITY_HISTORICAL_ORACLES = (
    {
        "format_version": "TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0084-trading-securities-activity-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "bd50c841fb1f6ca0c9a0e1a976d407c4aad9077fd52313bc9251be6d4ed393da",
        "size_bytes": 89945,
    },
    {
        "format_version": (
            "ANNUAL_2025_TRADING_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
        ),
        "path": (
            "docs/experiments/"
            "E-0139-annual-2025-trading-securities-activity-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "baadd83a53c6040f6b92774386ece52cc9f6d4d99fe2ee110b28a76970caed50",
        "size_bytes": 82198,
    },
)
PINNED_INVESTMENT_SECURITIES_ACTIVITY_HISTORICAL_ORACLES = (
    {
        "format_version": "INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0085-investment-securities-activity-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "86f0a03859ff2d2283483c2792644562e190b6b5e2968c3e57720335c1acf823",
        "size_bytes": 92485,
    },
    {
        "format_version": (
            "ANNUAL_2025_INVESTMENT_SECURITIES_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
        ),
        "path": (
            "docs/experiments/"
            "E-0140-annual-2025-investment-securities-activity-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "59d48f9f89cb5d658faaa1ed07a8747ffcc630462b4dd84feeacc41ed772fefa",
        "size_bytes": 101812,
    },
)
PINNED_COMBINED_SECURITIES_NET_HISTORICAL_ORACLES = (
    {
        "format_version": "COMBINED_SECURITIES_NET_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/E-0086-combined-securities-net-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "491965eff2494421c6f95334ed97ccc52333e11c7178f9410cee8cc41c4ca2cf",
        "size_bytes": 15453,
    },
    {
        "format_version": ("ANNUAL_2025_COMBINED_SECURITIES_NET_8BANK_BOUND_REPORT_ABSENCE_V1"),
        "path": (
            "docs/experiments/"
            "E-0141-annual-2025-combined-securities-net-8bank-bound-report-absence-v1.json"
        ),
        "sha256": "fc591e1acd8a167b8d252da7eaf30073ae14b1e77630cd6210dec3407b5b6b89",
        "size_bytes": 10803,
    },
)
PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_HISTORICAL_ORACLES = (
    {
        "format_version": "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0087-capital-contribution-dividend-income-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "362f7538a1f52e9390337aee122ec1d772e93bd3c1c100abe11b20c8292841d7",
        "size_bytes": 93030,
    },
    {
        "format_version": (
            "ANNUAL_2025_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
        ),
        "path": (
            "docs/experiments/"
            "E-0142-annual-2025-capital-contribution-dividend-income-8bank-"
            "codex-verified-mapping-v1.json"
        ),
        "sha256": "119c2430655e7264d8b5be4d5cb5abe29e5c7601ef3a7378248c9986972ac781",
        "size_bytes": 91880,
    },
)
PINNED_GOVERNMENT_SBV_LIABILITIES_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "c33d90d1ac9405426fe8e87ddfe0947f8d12a5c1f679eb4b53a3e6d58dc6b97a"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 140,
    "candidate_disposition_axis_sha256": (
        "b952e106b3a54b188cc35c4aecbb5e08247b8eae139ee5d4fae4a509370b3b4d"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "65365467af2bca6d6ab349c52714fc1ddc1d6c79e608ae5ff8aaf1a75138df49",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 739,
    "not_observed_count": 0,
    "ready_count": 140,
    "unresolved_count": 0,
}
PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_AUDIT_METRICS = {
    "equation_count": 411,
    "historical_comparator_exact_count": 86,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 70,
    "historical_mapping_record_count": 75,
    "mapping_count": 739,
}
PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_AXIS_COUNTS = {
    "clusters": 140,
    "equations": 411,
    "historical_comparator": 91,
    "mappings": 739,
}
PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_AXIS_SHA256 = {
    "clusters": "b4fddfc1e44bd58c4820242d80ca87f874a277278358e32a12b9ec7624037893",
    "equations": "f2684f572e744bcda4f1a61b8256348b529d27dff5b76a34a8422f210677ae26",
    "historical_comparator": ("5dd650fc8d33d024990b98cf743ceb3a178aa095dbd46ffac32394a43368246f"),
    "mappings": "1fbb965bf98a05fa59b00cb2ba96b8f49ac73938b952dbbe601375f79993578c",
}
PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "b6ac9de71f72508a99ab1888807209f318e2de610b489f0d79d339a01a50dd16"
    ),
    "accepted_cluster_count": 76,
    "accepted_fragment_count": 76,
    "candidate_disposition_axis_sha256": (
        "d103fb00f844c66a419624cd8f03727ca39dad3b4dd3a993067c548206f3fba6"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 64, READY: 76, UNRESOLVED: 0},
    "query_policy_sha256": "f9a0fc4c4ddb7f8bc65c4f6499ad7813307bfee3ff3c06ed97227a65981f36bc",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 174,
    "not_observed_count": 64,
    "ready_count": 76,
    "unresolved_count": 0,
}
PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_AUDIT_METRICS = {
    "equation_count": 117,
    "historical_comparator_exact_count": 42,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 26,
    "historical_mapping_record_count": 26,
    "mapping_count": 174,
}
PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_AXIS_COUNTS = {
    "clusters": 76,
    "equations": 117,
    "historical_comparator": 42,
    "mappings": 174,
}
PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_AXIS_SHA256 = {
    "clusters": "179b0f2771e28300e38c180d96144fd186c77b32855dfd8aec0d00e3f1b5da70",
    "equations": "baa4e5a6337dacec9edd8ca4dccaec71b818020b5f0bb5aff85ccc1a76026b40",
    "historical_comparator": ("6e4a1eccf284b716b6e840fc9e180624bff707bdb9ff35ad531fdb9887081714"),
    "mappings": "01d7eb41b11f0463be239a29e01157127492efce028b37f265c43f55eccc117e",
}
PINNED_ISSUED_VALUABLE_PAPERS_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "173895e78e18a5a453932c43d82411410234b3dec75ea20a1c7e01ee17adb219"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 186,
    "candidate_disposition_axis_sha256": (
        "8c9eebd1c56b4adcb4e8c0792607cdc32c48834e83b089b8470d92dc11025b77"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "12ac98c49f074f9f126e502d1032a320fb4a445688f8171026acc01514741cad",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 1228,
    "not_observed_count": 0,
    "ready_count": 140,
    "unresolved_count": 0,
}
PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_AUDIT_METRICS = {
    "equation_count": 849,
    "historical_comparator_exact_count": 150,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 134,
    "historical_mapping_record_count": 136,
    "mapping_count": 1228,
}
PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_AXIS_COUNTS = {
    "clusters": 140,
    "equations": 849,
    "historical_comparator": 152,
    "mappings": 1228,
}
PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_AXIS_SHA256 = {
    "clusters": "c12b0e487f28e195bde11afcbec7be41650a5bc477dd4c0667270356dc75c9d9",
    "equations": "2b8862a72ac0bf0057a63bc00416fbf92866bd4fdbbdebe367f4dda801c917dc",
    "historical_comparator": ("8c3b19d3b7cfedfcbfb79f642502a9b404ecf567dd22c2888a89efc0a191d74c"),
    "mappings": "5174aa74075b050642b1f25179e4d210aa02336cdfe1237a12266ac57f914435",
}
PINNED_OTHER_PAYABLES_LIABILITIES_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "22c30626613d286a61bb26cf053135b2b9008911a59dd11accf9a3e5ecef0993"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 220,
    "candidate_disposition_axis_sha256": (
        "18b3ce56818fd037f0cf52a94704b6ee0c3c875517e8696b59dcba9ff9aaee62"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "7189792c6199f2f09ef9dd2984ae03fb097f01f21e9c5b41fefb7c21e3f764c9",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 809,
    "not_observed_count": 0,
    "ready_count": 140,
    "unresolved_count": 0,
}
PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_AUDIT_METRICS = {
    "equation_count": 334,
    "historical_comparator_exact_count": 108,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 92,
    "historical_mapping_record_count": 92,
    "mapping_count": 809,
}
PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_AXIS_COUNTS = {
    "clusters": 140,
    "equations": 334,
    "historical_comparator": 108,
    "mappings": 809,
}
PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_AXIS_SHA256 = {
    "clusters": "dedb7b712f81d211b768deee734a789cba367048c1457fe5920d00211210e42d",
    "equations": "74f1398805b19474e39f18fd931875bd6ec403a6219a25741be6fd4601466997",
    "historical_comparator": ("9a00eff31bba2a9c5bff712e64e8ac7a3d5aa049d0f9c48c8d69bd18e2d90fc5"),
    "mappings": "add70a2dccdb1ab37759697090a8aaf4db5728f8f6a80cbc4c147038367c6427",
}
PINNED_INTEREST_INCOME_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "4833f0f9229669e2b9ab7962b14a36b7ed8d1f9f26c390e4bbae95e22c249733"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 140,
    "candidate_disposition_axis_sha256": (
        "952172b79cc874abef4c8492da6d15d22db52a81ea5fff412a12ed49adc932b4"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "8de63bdd8a4e061ef119cd5fe114111cb3664a285e8116d4f78af0fce52472d2",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_INTEREST_INCOME_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 882,
    "not_observed_count": 0,
    "ready_count": 136,
    "unresolved_count": 4,
}
PINNED_INTEREST_INCOME_RELEASE_AUDIT_METRICS = {
    "equation_count": 310,
    "historical_comparator_exact_count": 125,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 109,
    "historical_mapping_record_count": 109,
    "mapping_count": 882,
}
PINNED_INTEREST_INCOME_RELEASE_AXIS_COUNTS = {
    "clusters": 136,
    "equations": 310,
    "historical_comparator": 125,
    "mappings": 882,
}
PINNED_INTEREST_INCOME_RELEASE_AXIS_SHA256 = {
    "clusters": "d267aed5c6c05db26f42da92360a980c97bea6a72d4fcb601be7d3507d41e68c",
    "equations": "58158027dd2172dab3cb57297a60f474791a03dcf4a2c378bf52811cfd52822a",
    "historical_comparator": ("4405674348550483e6cf30e67d3cb9a20526c89bf83bba843a42d1565f8cc388"),
    "mappings": "8e9173f5b9f7bba7f8e81ab349a6b285e5afcedf028ddf580953de5d9ca8fca1",
}
PINNED_INTEREST_EXPENSE_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "d868b479c6e9e36dddb9f2a011a8c9ca6077b14d73858921004b0d5f1c26c3b0"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 140,
    "candidate_disposition_axis_sha256": (
        "674877e5145ad45ee02b7eb378daf9d97b166d1897f9e5cad11139fabe933918"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "3a17f65c1feefa0c72e9229bb46100d928d1df93edc1676a80ac049f6609af34",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_INTEREST_EXPENSE_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 701,
    "not_observed_count": 0,
    "ready_count": 140,
    "unresolved_count": 0,
}
PINNED_INTEREST_EXPENSE_RELEASE_AUDIT_METRICS = {
    "equation_count": 140,
    "historical_comparator_exact_count": 96,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 80,
    "historical_mapping_record_count": 80,
    "mapping_count": 701,
}
PINNED_INTEREST_EXPENSE_RELEASE_AXIS_COUNTS = {
    "clusters": 140,
    "equations": 140,
    "historical_comparator": 96,
    "mappings": 701,
}
PINNED_INTEREST_EXPENSE_RELEASE_AXIS_SHA256 = {
    "clusters": "d290c7167c2b483dccfe98952b87181815be0de535288b0afaab26616b310b3a",
    "equations": "4ad1ecf1856b100e9fa129ba75debdd191d186d7d10fafa9d9ec6b22866eb9c9",
    "historical_comparator": "a5c67153914dc233d191373559d01e8d896d0a6632e079071827d2ffbd90150e",
    "mappings": "e5e1afac7053bae79597a52594b97cfe960941f2f4ec775ea402fda320e64203",
}
PINNED_SERVICE_ACTIVITY_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "3aba5b4db43e39cee7d34ac9b8692be99c718a34db4db8df9554a74c067d05d3"
    ),
    "accepted_cluster_count": 68,
    "accepted_fragment_count": 139,
    "candidate_disposition_axis_sha256": (
        "1a8e084668152fcdd4b13d76b26b580c7135d0db35e92bb96b3aafe5cced09b1"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 72, READY: 68, UNRESOLVED: 0},
    "query_policy_sha256": "cf3cddf0257154edf53f5d89084aa58a0b4778d2d899066bd5c5e34f0e557072",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_SERVICE_ACTIVITY_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 869,
    "not_observed_count": 72,
    "ready_count": 68,
    "unresolved_count": 0,
}
PINNED_SERVICE_ACTIVITY_RELEASE_AUDIT_METRICS = {
    "equation_count": 289,
    "historical_comparator_exact_count": 160,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 144,
    "historical_mapping_record_count": 144,
    "mapping_count": 869,
}
PINNED_SERVICE_ACTIVITY_RELEASE_AXIS_COUNTS = {
    "clusters": 68,
    "equations": 289,
    "historical_comparator": 160,
    "mappings": 869,
}
PINNED_SERVICE_ACTIVITY_RELEASE_AXIS_SHA256 = {
    "clusters": "756eb6669e5d7a2faa1891c8ebe3bfba45b901a175346b54f67e7fd527fd5b94",
    "equations": "1a95f36b9a461de9b5ed0d4cc8132fe444d5c0052652213e60cb1d279fe9725e",
    "historical_comparator": "877ef3a3aa48059abb8014bfeebcbed8e9d59823933d6a293ab288e5033c337f",
    "mappings": "a18ee4e8f5b7e00f76eafda633c3b25b1152fd97a2420b9bfd42db735e6bf310",
}
PINNED_FX_GOLD_ACTIVITY_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "3fd5ff6a500702b2fea8a04ce497d5211b602691c53c6ca6005e7f9b8e8b8e89"
    ),
    "accepted_cluster_count": 72,
    "accepted_fragment_count": 138,
    "candidate_disposition_axis_sha256": (
        "7bcdbf49f396deeb0064841069a7c302b891c3ea31e0657e9dba581e8c1ae4e9"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 68, READY: 72, UNRESOLVED: 0},
    "query_policy_sha256": "a2b3ef02b185e81d42a075bd118571e4498f20c2d4cc77392caa9ee6c41b0977",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_FX_GOLD_ACTIVITY_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 580,
    "not_observed_count": 68,
    "ready_count": 72,
    "unresolved_count": 0,
}
PINNED_FX_GOLD_ACTIVITY_RELEASE_AUDIT_METRICS = {
    "equation_count": 220,
    "historical_comparator_exact_count": 108,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 92,
    "historical_mapping_record_count": 92,
    "mapping_count": 580,
}
PINNED_FX_GOLD_ACTIVITY_RELEASE_AXIS_COUNTS = {
    "clusters": 72,
    "equations": 220,
    "historical_comparator": 108,
    "mappings": 580,
}
PINNED_FX_GOLD_ACTIVITY_RELEASE_AXIS_SHA256 = {
    "clusters": "53f89011bc75c13b2837a23e06de60e0336c66556a715169ee9c66710fce360e",
    "equations": "796c9f16c0fc489a5eae1da03a9272d812e8521591db1cedd6146ecbf506124e",
    "historical_comparator": "16cb778e84ab9c16eb37f2002a5a43a105384f6b05257ab65468532a4eb19acf",
    "mappings": "9448338aed22d159d34fdbbfa9858f1ff7c488a8a75c386a6fbe7ee279f72114",
}
PINNED_TRADING_SECURITIES_ACTIVITY_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "5968f4acfd69e49804297bad02ea1541f98386fd1d6efc2d0b6db412f8550d03"
    ),
    "accepted_cluster_count": 103,
    "accepted_fragment_count": 103,
    "candidate_disposition_axis_sha256": (
        "a3d6df18649a0d63631642c6d744556a82f46183b59f0daacdd6faddf0261fa3"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 37, READY: 103, UNRESOLVED: 0},
    "query_policy_sha256": "44792ff6846e9041864d96290bdbe9319369d64dd1cb3205b2975d3baa81302f",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 371,
    "not_observed_count": 37,
    "ready_count": 103,
    "unresolved_count": 0,
}
PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_AUDIT_METRICS = {
    "equation_count": 103,
    "historical_comparator_exact_count": 71,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 55,
    "historical_mapping_record_count": 55,
    "mapping_count": 371,
}
PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_AXIS_COUNTS = {
    "clusters": 103,
    "equations": 103,
    "historical_comparator": 71,
    "mappings": 371,
}
PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_AXIS_SHA256 = {
    "clusters": "eaacef5564f7596d414ad0554d64c6cda073fa1bea2c2d3852cb33301936dd25",
    "equations": "b5f544098fa9f19559269b29e7713734de14eb4a855d76143f129de95c2c65de",
    "historical_comparator": ("62dece4056c6ee503e9b839d483b84c3477171032e3fd93761b0f60986269925"),
    "mappings": "76eb6855cb631d2acb384e7fabdafc71da92d42ab71a2104607d8ea0cd7a81ea",
}
PINNED_INVESTMENT_SECURITIES_ACTIVITY_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "541096621eb8ba45c0238ad0a5fee7532090f047f500d1d3101331c6291fbb80"
    ),
    "accepted_cluster_count": 112,
    "accepted_fragment_count": 112,
    "candidate_disposition_axis_sha256": (
        "14154f7f53198ca6da3ee477fb7d9f02ce245c1425304ad41a020fc15571acc3"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 28, READY: 112, UNRESOLVED: 0},
    "query_policy_sha256": "532f11e15f638f07438f05e63996999c5d85e5bfedd33d0b6b3e96f4a4ab231a",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "ea864a4965be25215d92ad29ca797b836ca03277986ff90df884e919b1b80419"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": (
        "5073c20d35c695aa2f8242f61f5c40abd5f8bab0cbb33bc2066bc2a01024d91b"
    ),
}
PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 424,
    "not_observed_count": 28,
    "ready_count": 112,
    "unresolved_count": 0,
}
PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_AUDIT_METRICS = {
    "equation_count": 128,
    "historical_comparator_exact_count": 76,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 60,
    "historical_mapping_record_count": 60,
    "mapping_count": 424,
}
PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_AXIS_COUNTS = {
    "clusters": 112,
    "equations": 128,
    "historical_comparator": 76,
    "mappings": 424,
}
PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_AXIS_SHA256 = {
    "clusters": "e8b3a0903cdf1b03f8bffa07c0f99722b832a15019eadc36c0d21c4551726791",
    "equations": "19f6412d14278eeb1844ac82b9832b6fbe9afc452c510eae1c80d35039c2a483",
    "historical_comparator": "463ab58fadb3d04c3350cbce4f0acac7e7dc8ee13e92f38b2e0cb9d72b6e3630",
    "mappings": "fed1239c0a2b32fd05d2832f3254f3f9c857f24ff05b4b03509ecef7f482e1a1",
}
PINNED_COMBINED_SECURITIES_NET_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "54b827bf82be6aa986d48528569fae3086c78e5af1fc2bec293e768317ecefdf"
    ),
    "accepted_cluster_count": 12,
    "accepted_fragment_count": 12,
    "candidate_disposition_axis_sha256": (
        "aa6290d125515a671a178be75f5a518db038362d66478bc3174823161cf29f0d"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 128, READY: 12, UNRESOLVED: 0},
    "query_policy_sha256": "5a72a96edc619eadc18455d3b34911b0c437402deb08800585e028282eaf20d1",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_COMBINED_SECURITIES_NET_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 12,
    "not_observed_count": 128,
    "ready_count": 12,
    "unresolved_count": 0,
}
PINNED_COMBINED_SECURITIES_NET_RELEASE_AUDIT_METRICS = {
    "equation_count": 36,
    "historical_comparator_exact_count": 17,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 1,
    "historical_mapping_record_count": 1,
    "mapping_count": 12,
}
PINNED_COMBINED_SECURITIES_NET_RELEASE_AXIS_COUNTS = {
    "clusters": 12,
    "equations": 36,
    "historical_comparator": 17,
    "mappings": 12,
}
PINNED_COMBINED_SECURITIES_NET_RELEASE_AXIS_SHA256 = {
    "clusters": "0f495a5e881bd73c47474db9dc1af2a601cc563ec7c24526c3988c0c579edab8",
    "equations": "6530a7051632c79bb7b7d45b52e7ae59f8650d8fa82dfb1847fe301a6eaf77fa",
    "historical_comparator": "c393c8cae9ca78a5090f37446cd0a110737f33c93eabc22fbc2624e6d36532e1",
    "mappings": "15b63c810403094504df94c9062c83ca2ddd3ed63d604ed583114f1f4aa525c3",
}
PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "c7c162404310937555328afb855e20706490ddba48f17a91ec54fc90b96e66c2"
    ),
    "accepted_cluster_count": 118,
    "accepted_fragment_count": 118,
    "candidate_disposition_axis_sha256": (
        "224737ec3138e52f93ba10cba59c73aa2ad80f66e525fcb1b3fc4c758ced1b21"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 22, READY: 118, UNRESOLVED: 0},
    "query_policy_sha256": "cbecc6b3e93fb2c3017d1f0cb118d4eb7af0dfa9e49b3045c569281e1506953e",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 428,
    "not_observed_count": 22,
    "ready_count": 118,
    "unresolved_count": 0,
}
PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_AUDIT_METRICS = {
    "equation_count": 192,
    "historical_comparator_exact_count": 71,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 55,
    "historical_mapping_record_count": 55,
    "mapping_count": 428,
}
PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_AXIS_COUNTS = {
    "clusters": 118,
    "equations": 192,
    "historical_comparator": 71,
    "mappings": 428,
}
PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_AXIS_SHA256 = {
    "clusters": "54fbb2fadbd2db789dbbd8db38967bdfb1f5bd389600273e6c39bf32bb825222",
    "equations": "743ddf853e7fc01ffc7cc8c4c7dc930efd63b789174732e30c15b68005b8e5bb",
    "historical_comparator": "f75e22988ff9cb5c4b454efdd4683fd7ce4904192f479b13321b85edd67a79be",
    "mappings": "2315d7036a6405caed1ab20b4d0cabf13998da9b12b32da36232cc4e3a21677a",
}
_SQLITE_SIDECAR_SUFFIXES = ("-journal", "-shm", "-wal")


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"JSON input is absent or not regular: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"JSON input is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error("JSON input is not one object")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _file_ref(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"traceable input is absent or not regular: {path}")
    resolved = path.resolve()
    logical = str(resolved.relative_to(root.resolve())) if root is not None else str(resolved)
    return {"path": logical, "sha256": _sha256(resolved), "size_bytes": resolved.stat().st_size}


def _content_ref(root: Path, reference: Any) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("corpus content reference escapes its artifact root")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("corpus content reference does not authenticate")
    return path


def _file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _assert_no_sqlite_sidecars(path: Path) -> None:
    if any(os.path.lexists(f"{path}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES):
        raise _error("multi-table hierarchical SQLite source has a journal/WAL sidecar")


def _fd_sha256(descriptor: int) -> str:
    prior = os.lseek(descriptor, 0, os.SEEK_CUR)
    digest = sha256()
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.lseek(descriptor, prior, os.SEEK_SET)
    return digest.hexdigest()


class _AuthenticatedSqliteSnapshot:
    def __init__(
        self,
        *,
        source: Path,
        source_descriptor: int,
        source_identity: tuple[int, ...],
        snapshot: Path,
        snapshot_identity: tuple[int, ...],
        expected_sha256: str,
        expected_size_bytes: int,
    ) -> None:
        self.source = source
        self.source_descriptor = source_descriptor
        self.source_identity = source_identity
        self.path = snapshot
        self.snapshot_identity = snapshot_identity
        self.expected_sha256 = expected_sha256
        self.expected_size_bytes = expected_size_bytes

    def validate(self) -> None:
        _assert_no_sqlite_sidecars(self.source)
        _assert_no_sqlite_sidecars(self.path)
        try:
            source_named = os.stat(self.source, follow_symlinks=False)
            snapshot_stat = os.stat(self.path, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise _error("authenticated multi-table SQLite path disappeared") from exc
        source_fd = os.fstat(self.source_descriptor)
        if (
            not stat.S_ISREG(source_named.st_mode)
            or not stat.S_ISREG(snapshot_stat.st_mode)
            or _file_identity(source_fd) != self.source_identity
            or _file_identity(source_named) != self.source_identity
            or _file_identity(snapshot_stat) != self.snapshot_identity
            or source_fd.st_size != self.expected_size_bytes
            or snapshot_stat.st_size != self.expected_size_bytes
            or _fd_sha256(self.source_descriptor) != self.expected_sha256
            or _sha256(self.path) != self.expected_sha256
        ):
            raise _error("authenticated multi-table SQLite bytes changed during use")


@contextmanager
def _authenticated_sqlite_snapshot(
    source: Path, *, reference: Mapping[str, Any]
) -> Iterator[_AuthenticatedSqliteSnapshot]:
    """Create one immutable source view for the whole family run."""

    _assert_no_sqlite_sidecars(source)
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        source_stat = os.fstat(descriptor)
        source_identity = _file_identity(source_stat)
        if (
            not stat.S_ISREG(source_stat.st_mode)
            or source_identity != _file_identity(os.stat(source, follow_symlinks=False))
            or source_stat.st_size != reference.get("size_bytes")
        ):
            raise _error("multi-table SQLite source identity drifted before snapshot")
        with tempfile.TemporaryDirectory(prefix="family22-authenticated-sqlite-") as directory:
            snapshot = Path(directory) / "page-store.sqlite3"
            output_descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            digest = sha256()
            copied = 0
            try:
                with os.fdopen(output_descriptor, "wb") as output:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    while block := os.read(descriptor, 1024 * 1024):
                        output.write(block)
                        digest.update(block)
                        copied += len(block)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                snapshot.unlink(missing_ok=True)
                raise
            if copied != reference.get("size_bytes") or digest.hexdigest() != reference.get(
                "sha256"
            ):
                raise _error("multi-table SQLite snapshot bytes do not authenticate")
            os.chmod(snapshot, 0o444)
            guard = _AuthenticatedSqliteSnapshot(
                source=source,
                source_descriptor=descriptor,
                source_identity=source_identity,
                snapshot=snapshot,
                snapshot_identity=_file_identity(os.stat(snapshot, follow_symlinks=False)),
                expected_sha256=reference["sha256"],
                expected_size_bytes=reference["size_bytes"],
            )
            guard.validate()
            try:
                yield guard
            finally:
                guard.validate()
    finally:
        os.close(descriptor)


def _selected_page_axis(*, index: Mapping[str, Any], artifact_root: Path) -> list[str]:
    version_ids = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        pages = manifest.get("pages")
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(pages) is not list
            or len(pages) != document["page_count"]
        ):
            raise _error("selected document manifest identity or page axis drifted")
        version_ids.extend(page.get("page_json_version_id") for page in pages)
    if (
        len(version_ids) != index["summary"]["page_count"]
        or len(version_ids) != len(set(version_ids))
        or any(type(version_id) is not str for version_id in version_ids)
    ):
        raise _error("selected multi-table JSON frontier is incomplete or duplicate")
    return version_ids


def _historical_oracle_refs(
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    family_id = compiled_specs["topology"]["family_id"]
    if family_id == "OTHER_ASSETS":
        return PINNED_HISTORICAL_ORACLES
    if family_id == "GOVERNMENT_SBV_LIABILITIES":
        return PINNED_GOVERNMENT_SBV_LIABILITIES_HISTORICAL_ORACLES
    if family_id == "ENTRUSTED_INVESTMENT_RISK_CAPITAL":
        return PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_HISTORICAL_ORACLES
    if family_id == "ISSUED_VALUABLE_PAPERS":
        return PINNED_ISSUED_VALUABLE_PAPERS_HISTORICAL_ORACLES
    if family_id == "OTHER_PAYABLES_LIABILITIES":
        return PINNED_OTHER_PAYABLES_LIABILITIES_HISTORICAL_ORACLES
    if family_id == "INTEREST_INCOME":
        return PINNED_INTEREST_INCOME_HISTORICAL_ORACLES
    if family_id == "INTEREST_EXPENSE":
        return PINNED_INTEREST_EXPENSE_HISTORICAL_ORACLES
    if family_id == "SERVICE_ACTIVITY":
        return PINNED_SERVICE_ACTIVITY_HISTORICAL_ORACLES
    if family_id == "FX_GOLD_ACTIVITY":
        return PINNED_FX_GOLD_ACTIVITY_HISTORICAL_ORACLES
    if family_id == "TRADING_SECURITIES_ACTIVITY":
        return PINNED_TRADING_SECURITIES_ACTIVITY_HISTORICAL_ORACLES
    if family_id == "INVESTMENT_SECURITIES_ACTIVITY":
        return PINNED_INVESTMENT_SECURITIES_ACTIVITY_HISTORICAL_ORACLES
    if family_id == "COMBINED_SECURITIES_NET":
        return PINNED_COMBINED_SECURITIES_NET_HISTORICAL_ORACLES
    if family_id == "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME":
        return PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_HISTORICAL_ORACLES
    raise _error("multi-table hierarchical family has no pinned historical oracle profile")


def _release_profile(compiled_specs: Mapping[str, Any]) -> dict[str, Any]:
    family_id = compiled_specs["topology"]["family_id"]
    if family_id == "OTHER_ASSETS":
        return {
            "axis_counts": {
                "clusters": 78,
                "equations": 374,
                "historical_comparator": 208,
                "mappings": 1290,
            },
            "axis_sha256": PINNED_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_QUERY_RECEIPT,
            "sweep_metrics": PINNED_RELEASE_METRICS,
        }
    if family_id == "GOVERNMENT_SBV_LIABILITIES":
        return {
            "axis_counts": PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_GOVERNMENT_SBV_LIABILITIES_QUERY_RECEIPT,
            "sweep_metrics": PINNED_GOVERNMENT_SBV_LIABILITIES_RELEASE_METRICS,
        }
    if family_id == "ENTRUSTED_INVESTMENT_RISK_CAPITAL":
        return {
            "axis_counts": PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_AXIS_SHA256,
            "audit_metrics": (PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_AUDIT_METRICS),
            "query_receipt": PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_QUERY_RECEIPT,
            "sweep_metrics": PINNED_ENTRUSTED_INVESTMENT_RISK_CAPITAL_RELEASE_METRICS,
        }
    if family_id == "ISSUED_VALUABLE_PAPERS":
        return {
            "axis_counts": PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_ISSUED_VALUABLE_PAPERS_QUERY_RECEIPT,
            "sweep_metrics": PINNED_ISSUED_VALUABLE_PAPERS_RELEASE_METRICS,
        }
    if family_id == "OTHER_PAYABLES_LIABILITIES":
        return {
            "axis_counts": PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_OTHER_PAYABLES_LIABILITIES_QUERY_RECEIPT,
            "sweep_metrics": PINNED_OTHER_PAYABLES_LIABILITIES_RELEASE_METRICS,
        }
    if family_id == "INTEREST_INCOME":
        return {
            "axis_counts": PINNED_INTEREST_INCOME_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_INTEREST_INCOME_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_INTEREST_INCOME_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_INTEREST_INCOME_QUERY_RECEIPT,
            "sweep_metrics": PINNED_INTEREST_INCOME_RELEASE_METRICS,
        }
    if family_id == "INTEREST_EXPENSE":
        return {
            "axis_counts": PINNED_INTEREST_EXPENSE_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_INTEREST_EXPENSE_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_INTEREST_EXPENSE_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_INTEREST_EXPENSE_QUERY_RECEIPT,
            "sweep_metrics": PINNED_INTEREST_EXPENSE_RELEASE_METRICS,
        }
    if family_id == "SERVICE_ACTIVITY":
        return {
            "axis_counts": PINNED_SERVICE_ACTIVITY_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_SERVICE_ACTIVITY_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_SERVICE_ACTIVITY_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_SERVICE_ACTIVITY_QUERY_RECEIPT,
            "sweep_metrics": PINNED_SERVICE_ACTIVITY_RELEASE_METRICS,
        }
    if family_id == "FX_GOLD_ACTIVITY":
        return {
            "axis_counts": PINNED_FX_GOLD_ACTIVITY_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_FX_GOLD_ACTIVITY_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_FX_GOLD_ACTIVITY_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_FX_GOLD_ACTIVITY_QUERY_RECEIPT,
            "sweep_metrics": PINNED_FX_GOLD_ACTIVITY_RELEASE_METRICS,
        }
    if family_id == "TRADING_SECURITIES_ACTIVITY":
        return {
            "axis_counts": PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_TRADING_SECURITIES_ACTIVITY_QUERY_RECEIPT,
            "sweep_metrics": PINNED_TRADING_SECURITIES_ACTIVITY_RELEASE_METRICS,
        }
    if family_id == "INVESTMENT_SECURITIES_ACTIVITY":
        return {
            "axis_counts": PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_INVESTMENT_SECURITIES_ACTIVITY_QUERY_RECEIPT,
            "selected_page_json_frontier_sha256": (
                "5073c20d35c695aa2f8242f61f5c40abd5f8bab0cbb33bc2066bc2a01024d91b"
            ),
            "sweep_metrics": PINNED_INVESTMENT_SECURITIES_ACTIVITY_RELEASE_METRICS,
        }
    if family_id == "COMBINED_SECURITIES_NET":
        return {
            "axis_counts": PINNED_COMBINED_SECURITIES_NET_RELEASE_AXIS_COUNTS,
            "axis_sha256": PINNED_COMBINED_SECURITIES_NET_RELEASE_AXIS_SHA256,
            "audit_metrics": PINNED_COMBINED_SECURITIES_NET_RELEASE_AUDIT_METRICS,
            "query_receipt": PINNED_COMBINED_SECURITIES_NET_QUERY_RECEIPT,
            "sweep_metrics": PINNED_COMBINED_SECURITIES_NET_RELEASE_METRICS,
        }
    if family_id == "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME":
        return {
            "axis_counts": (PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_AXIS_COUNTS),
            "axis_sha256": (PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_AXIS_SHA256),
            "audit_metrics": (PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_AUDIT_METRICS),
            "query_receipt": PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_QUERY_RECEIPT,
            "sweep_metrics": PINNED_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_RELEASE_METRICS,
        }
    raise _error("multi-table hierarchical family has no pinned release profile")


def _historical_oracles(
    *, compiled_specs: Mapping[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for pinned in _historical_oracle_refs(compiled_specs):
        path = ROOT / pinned["path"]
        value = _json(path)
        metrics = value.get("metrics")
        trials = value.get("trials")
        if (
            _sha256(path) != pinned["sha256"]
            or path.stat().st_size != pinned["size_bytes"]
            or value.get("format_version") != pinned["format_version"]
            or type(metrics) is not dict
            or type(metrics.get("mapping_verified_count")) is not int
            or type(trials) is not list
            or len(trials) != 8
            or sum(
                len(trial.get("verified_mappings", [])) for trial in trials if type(trial) is dict
            )
            != metrics["mapping_verified_count"]
        ):
            raise _error("pinned multi-table historical oracle drifted")
        result.append((dict(pinned), value))
    return result


def _trial_by_source(trials: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("multi-table trial source axis is ambiguous")
        result[source_sha256] = trial
    return result


def _historical_comparator_axis(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_trials = _trial_by_source(trials)
    current_role_by_id = {
        report_norm_id: role for role, report_norm_id in compiled_specs["bindings"].items()
    }
    axis = []
    oracle_refs = []
    joined_sources = set()
    expected_mapping_count = 0
    for oracle_ref, oracle in _historical_oracles(compiled_specs=compiled_specs):
        oracle_refs.append(oracle_ref)
        expected_mapping_count += oracle["metrics"]["mapping_verified_count"]
        for oracle_trial in oracle["trials"]:
            source_sha256 = oracle_trial.get("source_pdf_sha256")
            if type(source_sha256) is not str or source_sha256 in joined_sources:
                raise _error("historical multi-table source join is duplicate or invalid")
            joined_sources.add(source_sha256)
            trial = current_trials.get(source_sha256)
            if trial is None:
                raise _error("historical multi-table source does not join one current trial")
            historical_mappings = oracle_trial.get("verified_mappings", [])
            if type(historical_mappings) is not list:
                raise _error("historical multi-table mapping axis is invalid")
            expected_status = READY if historical_mappings else NOT_OBSERVED
            axis.append(
                {
                    "actual_status": trial.get("status"),
                    "bank_provenance": oracle_trial.get("document_provenance"),
                    "disposition": (
                        "EXACT" if trial.get("status") == expected_status else "MISMATCH"
                    ),
                    "expected_status": expected_status,
                    "oracle_format_version": oracle["format_version"],
                    "record_kind": "DOCUMENT_DISPOSITION",
                    "source_sha256": source_sha256,
                }
            )
            candidates = trial.get("candidates")
            candidate = (
                candidates[0]
                if trial.get("status") == READY
                and type(candidates) is list
                and len(candidates) == 1
                else None
            )
            actual_by_id = {}
            for mapping in candidate.get("mappings", []) if candidate is not None else []:
                report_norm_id = mapping.get("report_norm_id")
                values = mapping.get("values")
                if (
                    type(report_norm_id) is not int
                    or report_norm_id in actual_by_id
                    or type(values) is not list
                    or len(values) not in {1, 2}
                    or any(
                        type(value) is not dict or type(value.get("coefficient")) is not int
                        for value in values
                    )
                ):
                    raise _error("current multi-table comparator mapping axis is invalid")
                actual_by_id[report_norm_id] = mapping
            historical_report_norm_ids = {
                binding.get("report_norm_id")
                for historical in historical_mappings
                if type(historical) is dict
                and type(binding := historical.get("schema_binding")) is dict
            }
            for historical in historical_mappings:
                binding = historical.get("schema_binding")
                source_values = historical.get("values")
                old_report_norm_id = (
                    binding.get("report_norm_id") if type(binding) is dict else None
                )
                historical_coefficients = None
                if type(source_values) is list:
                    period_role_items = []
                    for value in source_values:
                        if type(value) is not dict:
                            continue
                        period_role = value.get("period_role")
                        axis_role = value.get("axis_role")
                        if (
                            period_role is not None
                            and axis_role is not None
                            and period_role != axis_role
                        ):
                            continue
                        role = period_role if type(period_role) is str else axis_role
                        if type(role) is str:
                            period_role_items.append((role, value.get("normalized_value")))
                    by_period_role = {
                        role: normalized_value for role, normalized_value in period_role_items
                    }
                    if len(by_period_role) == len(source_values) and set(by_period_role) in (
                        {"CURRENT"},
                        {"CURRENT", "COMPARATIVE"},
                        {"CURRENT_PERIOD"},
                        {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"},
                    ):
                        current_key = "CURRENT" if "CURRENT" in by_period_role else "CURRENT_PERIOD"
                        comparative_key = (
                            "COMPARATIVE"
                            if "COMPARATIVE" in by_period_role
                            else "COMPARATIVE_PERIOD"
                        )
                        historical_coefficients = [by_period_role[current_key]]
                        if comparative_key in by_period_role:
                            historical_coefficients.append(by_period_role[comparative_key])
                current = actual_by_id.get(old_report_norm_id)
                full_current_coefficients = (
                    [value["coefficient"] for value in current["values"]]
                    if type(current) is dict
                    else None
                )
                current_role = current.get("role") if type(current) is dict else None
                bond_report_norm_id = compiled_specs["bindings"].get("BOND")
                other_report_norm_id = compiled_specs["bindings"].get("OTHER_ISSUED_PAPER")
                if (
                    compiled_specs["topology"]["family_id"] == "ISSUED_VALUABLE_PAPERS"
                    and old_report_norm_id == bond_report_norm_id
                    and other_report_norm_id not in historical_report_norm_ids
                    and type(current) is dict
                    and type(other := actual_by_id.get(other_report_norm_id)) is dict
                    and len(current["values"]) == len(other["values"])
                ):
                    # The earlier oracle schema folded capital-raising/other
                    # issued papers into BOND.  The current schema has an
                    # explicit RNID 1117.  Compare the exact additive legacy
                    # projection without changing either current mapping.
                    full_current_coefficients = [
                        left["coefficient"] + right["coefficient"]
                        for left, right in zip(current["values"], other["values"], strict=True)
                    ]
                    current_role = "BOND_PLUS_OTHER_ISSUED_PAPER_LEGACY_PROJECTION"
                direct_dividend_report_norm_id = compiled_specs["bindings"].get("DIRECT_DIVIDEND")
                long_term_dividend_report_norm_id = compiled_specs["bindings"].get(
                    "LONG_TERM_CAPITAL_DIVIDEND"
                )
                derived_direct_receipts = [
                    receipt
                    for table_receipt in (
                        candidate.get("closure_receipt", {}).get("table_receipts", [])
                        if candidate is not None
                        else []
                    )
                    for receipt in table_receipt.get("derived_structural_parent_receipts", [])
                    if receipt.get("parent_role") == "DIRECT_DIVIDEND"
                    and set(receipt.get("component_roles", []))
                    == {
                        "COMBINED_EQUITY_DIVIDEND_SOURCE_ONLY",
                        "LONG_TERM_CAPITAL_DIVIDEND",
                    }
                ]
                if (
                    compiled_specs["topology"]["family_id"]
                    == "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME"
                    and old_report_norm_id == direct_dividend_report_norm_id
                    and type(current) is dict
                    and type(long_term := actual_by_id.get(long_term_dividend_report_norm_id))
                    is dict
                    and current.get("state")
                    == "STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER"
                    and len(derived_direct_receipts) == 1
                    and len(current["values"]) == len(long_term["values"])
                ):
                    # The earlier CTG comparator assigned one source-only
                    # combined equity-dividend row to RNID 1199 because the
                    # printed intermediate subtotal was absent.  The current
                    # graph correctly keeps that row source-only and derives
                    # DIRECT_DIVIDEND from its complete child frontier.  This
                    # subtraction is a comparator-only projection back to the
                    # old source row; it never changes a released mapping.
                    full_current_coefficients = [
                        parent["coefficient"] - child["coefficient"]
                        for parent, child in zip(
                            current["values"], long_term["values"], strict=True
                        )
                    ]
                    current_role = (
                        "DIRECT_DIVIDEND_MINUS_LONG_TERM_CAPITAL_DIVIDEND_"
                        "LEGACY_SOURCE_ONLY_PROJECTION"
                    )
                current_coefficients = (
                    full_current_coefficients[: len(historical_coefficients)]
                    if type(full_current_coefficients) is list
                    and type(historical_coefficients) is list
                    else full_current_coefficients
                )
                exact = (
                    type(old_report_norm_id) is int
                    and type(historical_coefficients) is list
                    and len(historical_coefficients) in {1, 2}
                    and all(type(value) is int for value in historical_coefficients)
                    and current is not None
                    and current_coefficients == historical_coefficients
                )
                axis.append(
                    {
                        "bank_provenance": oracle_trial.get("document_provenance"),
                        "canonical_name": (
                            binding.get("canonical_name") if type(binding) is dict else None
                        ),
                        "current_coefficients": current_coefficients,
                        "current_role": current_role,
                        "declared_role": current_role_by_id.get(old_report_norm_id),
                        "disposition": "EXACT" if exact else "MISMATCH",
                        "historical_coefficients": historical_coefficients,
                        "historical_report_norm_id": old_report_norm_id,
                        "oracle_format_version": oracle["format_version"],
                        "record_kind": "MAPPING_VALUE",
                        "source_sha256": source_sha256,
                    }
                )
    if len(axis) != expected_mapping_count + 16:
        raise _error("historical multi-table comparator denominator drifted")
    return axis, oracle_refs


def _audit_axes(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    mappings = []
    equations = []
    clusters = []
    for trial in trials:
        candidates = trial.get("candidates")
        if trial.get("status") != READY or type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        clusters.append(
            {
                **document,
                "component_regions": candidate["component_regions"],
                "query_receipt_sha256": canonical_json_sha256_v1(
                    candidate["closure_receipt"]["query_receipt"]
                ),
            }
        )
        for mapping in candidate["mappings"]:
            mappings.append(
                {
                    **document,
                    "coefficients": [value["coefficient"] for value in mapping["values"]],
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "row_id": mapping["row_id"],
                    "states": [value["state"] for value in mapping["values"]],
                    "unit": mapping["unit"],
                }
            )
        for equation in candidate["closure_receipt"]["equations"]:
            equations.append({**document, "equation": equation})
    comparator, oracle_refs = _historical_comparator_axis(
        trials=trials, compiled_specs=compiled_specs
    )
    return {
        "clusters": clusters,
        "equations": equations,
        "historical_comparator": comparator,
        "mappings": mappings,
    }, oracle_refs


def build_multitable_hierarchical_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build transparent semantic axes after the exact SQLite candidate replay."""

    axes, oracle_refs = _audit_axes(trials=trials, compiled_specs=compiled_specs)
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    comparator = axes["historical_comparator"]
    audit_metrics = {
        "equation_count": axis_counts["equations"],
        "historical_comparator_exact_count": sum(
            item["disposition"] == "EXACT" for item in comparator
        ),
        "historical_disposition_exact_count": sum(
            item["record_kind"] == "DOCUMENT_DISPOSITION" and item["disposition"] == "EXACT"
            for item in comparator
        ),
        "historical_mapping_exact_count": sum(
            item["record_kind"] == "MAPPING_VALUE" and item["disposition"] == "EXACT"
            for item in comparator
        ),
        "historical_mapping_record_count": sum(
            item["record_kind"] == "MAPPING_VALUE" for item in comparator
        ),
        "mapping_count": axis_counts["mappings"],
    }
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": audit_metrics,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_REPLAY_AND_HISTORICAL_ROLE_VALUE_"
            "COMPARATOR_ONLY_NO_PROVIDER_NO_GEOMETRY_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "spec_refs": dict(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjmthfeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_multitable_hierarchical_experimental_audit_content_v1(
    value: Any,
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "claim_boundary",
        "format_version",
        "historical_oracle_refs",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "equations",
        "historical_comparator",
        "mappings",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != axis_names
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("multi-table experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("multi-table experimental audit axis seal drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjmthfeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("multi-table experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_multitable_hierarchical_experimental_audit_replay_v1(
    value: Any,
    *,
    database: Path,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("multi-table caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("multi-table audit sweep/query/trial axis drifted")
    validate_selected_multitable_hierarchical_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_multitable_hierarchical_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_multitable_hierarchical_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("multi-table experimental audit does not replay exactly")
    return expected


def _validate_multitable_hierarchical_experimental_audit_after_sqlite_candidate_replay_v1(
    value: Any,
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the audit envelope after the immediately preceding SQLite gate.

    The public audit replay above remains the source-authenticating entry point.
    This private runner helper avoids a third identical 8,947-page query only
    after ``validate_selected_*_candidate_replays_v1`` has already rebuilt the
    exhaustive query and every candidate from the authenticated SQLite
    snapshot in the same call frame.
    """

    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("multi-table caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("multi-table audit sweep/query/trial axis drifted")
    expected = build_multitable_hierarchical_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_multitable_hierarchical_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("multi-table post-SQLite audit envelope does not replay exactly")
    return expected


def _assert_release_pins(
    *,
    compiled_specs: Mapping[str, Any],
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    sweep: Mapping[str, Any],
    indexed: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> None:
    profile = _release_profile(compiled_specs)
    actual = {
        "audit_metrics": audit.get("audit_metrics"),
        "axis_counts": audit.get("axis_counts"),
        "axis_sha256": audit.get("axis_sha256"),
        "corpus_manifest_index_id": index.get("corpus_manifest_index_id"),
        "query_receipt": indexed.get("query_receipt"),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(list(selected_ids)),
        "sweep_metrics": sweep.get("metrics"),
    }
    mismatches = []
    if actual["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID:
        mismatches.append("corpus_manifest_index_id")
    expected_frontier_sha256 = profile.get(
        "selected_page_json_frontier_sha256", PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256
    )
    if actual["selected_page_json_frontier_sha256"] != expected_frontier_sha256:
        mismatches.append("selected_page_json_frontier_sha256")
    if not same_typed_json_v1(actual["query_receipt"], profile["query_receipt"]):
        mismatches.append("query_receipt")
    if not same_typed_json_v1(actual["sweep_metrics"], profile["sweep_metrics"]):
        mismatches.append("sweep_metrics")
    if not same_typed_json_v1(actual["audit_metrics"], profile["audit_metrics"]):
        mismatches.append("audit_metrics")
    if not same_typed_json_v1(audit.get("axis_sha256"), profile["axis_sha256"]):
        mismatches.append("axis_sha256")
    if any(
        actual["axis_counts"].get(name) != count for name, count in profile["axis_counts"].items()
    ):
        mismatches.append("axis_counts")
    if mismatches:
        raise _error(
            "multi-table hierarchical frozen corpus release pin drifted: "
            + ",".join(mismatches)
            + "; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("multi-table output exists with different bytes")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _trials(
    *, indexed: Mapping[str, Any], candidates_by_ordinal: Mapping[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    trials = []
    for document, disposition in zip(
        indexed["selected_document_axis"], indexed["candidate_dispositions"], strict=True
    ):
        ordinal = document["document_ordinal"]
        candidate = candidates_by_ordinal.get(ordinal)
        if candidate is not None and candidate["status"] == READY:
            status = READY
            reasons = []
            mappings = candidate["mappings"]
            selected_candidate_id = candidate["candidate_id"]
        elif candidate is not None:
            status = UNRESOLVED
            reasons = candidate["reasons"]
            mappings = []
            selected_candidate_id = None
        elif disposition["disposition"] == NOT_OBSERVED:
            status = NOT_OBSERVED
            reasons = []
            mappings = []
            selected_candidate_id = None
        else:
            status = UNRESOLVED
            reasons = disposition["cluster"]["reasons"]
            mappings = []
            selected_candidate_id = None
        trials.append(
            {
                "candidate_count": int(candidate is not None),
                "candidates": [] if candidate is None else [candidate],
                "document_ordinal": ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    return trials


def _load_selected_pages_by_document(
    database: Path,
    *,
    selected_ids: Sequence[str],
    selected_page_axis: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, dict[str, Any]]]:
    """Decode the exact caller frontier from the already authenticated snapshot."""

    axis_by_version = {item["page_json_version_id"]: item for item in selected_page_axis}
    if len(axis_by_version) != len(selected_ids) or list(axis_by_version) != list(selected_ids):
        raise _error("multi-table selected page/evidence order drifted")
    result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_multitable_hierarchical_runner_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_multitable_hierarchical_runner_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_multitable_hierarchical_runner_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        loaded_ids = []
        for page_json_version_id, canonical_json_bytes in rows:
            loaded_ids.append(page_json_version_id)
            try:
                page_json = json.loads(bytes(canonical_json_bytes))
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("multi-table selected canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("multi-table selected canonical page is not one object")
            axis = axis_by_version[page_json_version_id]
            result[axis["document_ordinal"]][page_json_version_id] = page_json
    finally:
        connection.close()
    if loaded_ids != list(selected_ids):
        raise _error("multi-table selected canonical page frontier is incomplete")
    return result


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: _AuthenticatedSqliteSnapshot,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
    effective_page_frontier: dict[str, Any] | None,
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    page_json_by_document = _load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        candidates_by_ordinal[cluster["document_ordinal"]] = (
            evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                    regions
                ),
            )
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        effective_page_frontier=effective_page_frontier,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    replayed_trials = validate_selected_multitable_hierarchical_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    if not same_typed_json_v1(replayed_trials, trials):
        raise _error("multi-table SQLite candidate replay returned a different trial axis")
    audit = build_multitable_hierarchical_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _validate_multitable_hierarchical_experimental_audit_after_sqlite_candidate_replay_v1(
        audit,
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _assert_release_pins(
        compiled_specs=compiled,
        index=index,
        selected_ids=selected_ids,
        sweep=sweep,
        indexed=indexed,
        audit=audit,
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    _write_once(args.output, sweep)
    _write_once(audit_output, audit)
    implementation_paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
    )
    if effective_page_frontier is not None:
        implementation_paths = (
            *implementation_paths,
            ROOT / "src/bctc_ai/evaluation/gemini_json_region_repair_v1.py",
            ROOT / "src/bctc_ai/storage/gemini_family_effective_page_frontier_v1.py",
        )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(args.corpus_index),
        implementation_refs=[_file_ref(path, root=ROOT) for path in implementation_paths],
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored multi-table sweep differs from authenticated evaluation")
    output_ref = record_gemini_accounting_family_export_v1(
        args.results_database, family_run_id=stored["family_run_id"], output_path=args.output
    )
    database_guard.validate()
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "effective_page_frontier_id": (
            None
            if effective_page_frontier is None
            else effective_page_frontier["effective_page_frontier_id"]
        ),
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    database = _content_ref(artifact_root, index["database_ref"])
    database_reference = index["database_ref"]
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    effective_page_frontier = None
    effective_page_frontier_path = getattr(args, "effective_page_frontier", None)
    if effective_page_frontier_path is not None:
        effective_page_frontier, selected_ids = apply_gemini_family_effective_page_frontier_v1(
            _json(effective_page_frontier_path),
            base_page_json_version_ids=selected_ids,
        )
        if (
            effective_page_frontier["base_corpus_manifest_index_id"]
            != index["corpus_manifest_index_id"]
            or effective_page_frontier["family_id"] != compiled["topology"]["family_id"]
        ):
            raise _error("effective page frontier does not bind this corpus and family")
        for stage in effective_page_frontier_stages_v1(effective_page_frontier):
            database = _content_ref(artifact_root, stage["database_ref"])
            database_reference = stage["database_ref"]
            repair_results_database = _content_ref(artifact_root, stage["results_database_ref"])
            source_overlay = resolved_gemini_family_region_repair_overlay_v1(
                repair_results_database,
                family_run_id=stage["repair_source_family_run_id"],
            )
            if (
                source_overlay["family_id"] != stage["family_id"]
                or source_overlay["job_status_counts"] != stage["job_status_counts"]
            ):
                raise _error("effective page frontier source family jobs do not replay")
            lineages = page_json_region_repair_lineages_v1(
                database,
                observed_page_json_version_ids=[
                    replacement["selected_page_json_version_id"]
                    for replacement in source_overlay["replacements"]
                ],
            )
            replacements = []
            for replacement, lineage in zip(source_overlay["replacements"], lineages, strict=True):
                if (
                    lineage["base_page_json_version_id"] != replacement["base_page_json_version_id"]
                    or lineage["observed_page_json_version_id"]
                    != replacement["selected_page_json_version_id"]
                ):
                    raise _error("effective page frontier repair lineage does not replay")
                replacements.append(
                    {
                        **replacement,
                        "repair_id": lineage["repair_id"],
                        "repair_receipt_sha256": lineage["repair_receipt_sha256"],
                    }
                )
            if replacements != stage["replacements"]:
                raise _error("effective page frontier replacement evidence drifted")
    spec_refs = {
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    with _authenticated_sqlite_snapshot(database, reference=database_reference) as database_guard:
        return _run_with_authenticated_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
            spec_refs=spec_refs,
            effective_page_frontier=effective_page_frontier,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument(
        "--effective-page-frontier",
        type=Path,
        help="Optional immutable repair overlay; never mutates the frozen base corpus index.",
    )
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
