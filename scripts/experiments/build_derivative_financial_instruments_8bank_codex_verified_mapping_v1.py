"""Pixel-review and map the derivative-financial-instruments TM family.

The fixed review is deliberately separate from the bank-blind full-document
matcher.  Bank/page identities below are evidence locators only: the mapping
is admitted solely after the shared graph has independently found one unique
region and bound its period, role and meaningful numeric lane.  Fresh VietOCR
supplies semantic anchors and crop geometry; visible pixels plus the sealed
source-number axis supply numeric truth.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error",
    "build_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
    "build_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
    "build_live_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
    "build_live_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1",
    "validate_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1",
    "validate_live_derivative_financial_instruments_8bank_codex_verified_mapping_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_module(
    "trading_securities_mapping_support_for_derivative_instruments",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "derivative_instruments_full_document_scan_for_mapping",
    "scan_derivative_financial_instruments_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_SHARED_DERIVATIVE_VARIANT_"
    "ENGINE_FIRST_LAST_BOUNDARY_STACKED_PERIOD_MEANINGFUL_LANE_VISIBLE_PIXEL_"
    "UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_"
    "PRODUCTION_OR_UNSUPPORTED_NET_INFLOW_OUTFLOW_MAPPING_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0063-derivative-financial-instruments-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0063-derivative-financial-instruments-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "dfifdsv1:scan:bb297f2baee9f5bec71b2db7a64efe2d5a1b519c161dec7889424670466a3d7f"

ANNUAL_2025_FORMAT_VERSION = (
    "ANNUAL_2025_DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
)
ANNUAL_2025_REVIEW_FORMAT = (
    "ANNUAL_2025_DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
)
ANNUAL_2025_CLAIM_BOUNDARY = (
    "FIXED_EIGHT_AUDITED_CONSOLIDATED_ANNUAL_2025_COMPLETE_PDF_FRESH_VIETOCR_"
    "SHARED_DERIVATIVE_VARIANT_ENGINE_MULTI_LEVEL_HEADER_CONTRACT_ASSET_"
    "LIABILITY_NET_OR_CASHFLOW_LAYOUT_VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_"
    "ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
ANNUAL_2025_REVIEW_PATH = Path(
    "docs/experiments/E-0111-annual-2025-derivative-financial-instruments-8bank-"
    "codex-pixel-review-v1.json"
)
ANNUAL_2025_RESULT_PATH = Path(
    "docs/experiments/E-0111-annual-2025-derivative-financial-instruments-8bank-"
    "codex-verified-mapping-v1.json"
)
ANNUAL_2025_SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
ANNUAL_2025_CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
ANNUAL_2025_EXPECTED_INDEX_SHA256 = (
    "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
)
ANNUAL_2025_EXPECTED_CROP_MANIFEST_SHA256 = (
    "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
)
ANNUAL_2025_EXPECTED_AXIS_SHA256 = (
    "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
)
ANNUAL_2025_EXPECTED_SCAN_ID = (
    "dfifdsv1:scan:a1c643ac4ebe2acecf765c2f5c990437fded68565ebcfda48d922e5c4bdc2b66"
)

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_DETAILED_DERIVATIVE_REGION",
    "FIRST_OWNER_AND_LAST_VISIBLE_DERIVATIVE_ROW_BOUNDARY",
    "POLICY_FAIR_VALUE_RISK_AND_BALANCE_SHEET_SURFACES_EXCLUDED",
    "PARENT_CHILD_AND_ROW_ORDER_TOPOLOGY",
    "CURRENT_AND_COMPARATIVE_PERIOD_BLOCKS",
    "MEANINGFUL_CONTRACT_ASSET_LIABILITY_LANES_ONLY",
    "NET_INFLOW_AND_OUTFLOW_RETAINED_ONLY_AS_ACCOUNTING_CHECKS",
    "VISIBLE_PIXEL_LABEL_DIGITS_AND_SIGN",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "GROUP_PARENT_CHILD_AND_NET_ACCOUNTING",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
    "FRESH_VIETOCR_NUMERIC_GLYPH_ERRORS_NEVER_REPAIRED_BY_TEXT_GUESSING",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_mapped_only_to_schema_beginning_period_axis": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "inflow_outflow_or_net_value_mapped_without_schema_axis": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER",
    "old_ocr_used_as_semantic_anchor": False,
    "source_order_and_cluster_boundaries_required": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "contract_asset_and_liability_schema_axes_only": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "inflow_outflow_and_net_columns_used_only_for_checks": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_derivative_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_mapping": False,
    "upstream_ppocrv6_or_native_text_used_only_as_numeric_challenger": True,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "state",
    "trials",
}

_ROLE_OFFSET = {
    "CURRENCY_DERIVATIVE_PARENT": 1,
    "FORWARD_CURRENCY": 2,
    "CURRENCY_SWAP": 3,
    "CURRENCY_FUTURE": 10,
    "OTHER_DERIVATIVE_PARENT": 11,
    "INTEREST_RATE_SWAP": 12,
}
_AXIS_BASE = {
    ("CURRENT_PERIOD", "CONTRACT_VALUE"): 632,
    ("COMPARATIVE_PERIOD", "CONTRACT_VALUE"): 646,
    ("CURRENT_PERIOD", "ASSET_CARRYING_VALUE"): 660,
    ("COMPARATIVE_PERIOD", "ASSET_CARRYING_VALUE"): 674,
    ("CURRENT_PERIOD", "LIABILITY_CARRYING_VALUE"): 688,
    ("COMPARATIVE_PERIOD", "LIABILITY_CARRYING_VALUE"): 702,
}
_SCHEMA_PARENT = {
    "CONTRACT_VALUE": 632,
    "ASSET_CARRYING_VALUE": 660,
    "LIABILITY_CARRYING_VALUE": 688,
}


class DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error(ValueError):
    """The derivative graph, pixel review, accounting, or live schema drifted."""


def _error(message: str) -> DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error:
    return DerivativeFinancialInstruments8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _row(
    period_role: str,
    role: str,
    label_line_index: int,
    pixel_label: str,
    lane_role: str,
    value_line_index: int,
    pixel_value: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": pixel_label,
        "lane_role": lane_role,
        "period_role": period_role,
        "pixel_binding": None,
        "pixel_value": pixel_value,
        "role": role,
        "value_line_index": value_line_index,
    }


def _dash_row(
    period_role: str,
    role: str,
    label_line_index: int,
    pixel_label: str,
    lane_role: str,
    bbox: list[int],
    rgb_sha256: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": pixel_label,
        "lane_role": lane_role,
        "period_role": period_role,
        "pixel_binding": {"bbox_raw_pixels": bbox, "rgb_sha256": rgb_sha256},
        "pixel_value": "-",
        "role": role,
        "value_line_index": None,
    }


def _equation(
    name: str,
    operation: str,
    components: Sequence[tuple[int, str]],
    total: tuple[int, str],
) -> dict[str, Any]:
    return {
        "component_values": [
            {"line_index": index, "pixel_transcription": text} for index, text in components
        ],
        "name": name,
        "operation": operation,
        "visible_total": {"line_index": total[0], "pixel_transcription": total[1]},
    }


# Each tuple is a fixed independent pixel readback.  It is evidence, not a
# bank-specific parser: the live shared graph must first produce the same
# period/role/lane intersection before any tuple is admitted.
_REVIEW_ROWS: dict[str, list[tuple[str, str, int, str, str, int, str]]] = {
    "ACB": [
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            18,
            "- Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            19,
            "7.897.725",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            18,
            "- Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            20,
            "120.159",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            21,
            "- Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            22,
            "100.716.158",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            21,
            "- Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            23,
            "275.578",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            25,
            "- Giao dịch hoán đổi lãi suất",
            "CONTRACT_VALUE",
            26,
            "7.734.608",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            25,
            "- Giao dịch hoán đổi lãi suất",
            "LIABILITY_CARRYING_VALUE",
            27,
            "40.508",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            41,
            "- Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            42,
            "3.646.093",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            41,
            "- Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            43,
            "31.284",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            44,
            "- Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            45,
            "80.034.373",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            44,
            "- Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            46,
            "350.144",
        ),
        (
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            48,
            "- Giao dịch hoán đổi lãi suất",
            "CONTRACT_VALUE",
            49,
            "3.104.030",
        ),
        (
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            48,
            "- Giao dịch hoán đổi lãi suất",
            "ASSET_CARRYING_VALUE",
            50,
            "5.438",
        ),
    ],
    "MBB": [
        (
            "CURRENT_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            61,
            "Công cụ TC phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            62,
            "(571.389)",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            64,
            "Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            65,
            "(161.250)",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            67,
            "Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            68,
            "(410.139)",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            71,
            "Công cụ TC phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            72,
            "(698.507)",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            74,
            "Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            75,
            "(19.293)",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            77,
            "Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            78,
            "(679.214)",
        ),
    ],
    "VPB": [
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            66,
            "Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            67,
            "16.857.857",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            71,
            "Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            72,
            "219.455.455",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            93,
            "Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            94,
            "24.642.959",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            98,
            "Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            99,
            "257.793.753",
        ),
    ],
    "HDB": [
        (
            "CURRENT_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            50,
            "Công cụ tài chính phái sinh tiền tệ",
            "CONTRACT_VALUE",
            51,
            "76.949.538",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            50,
            "Công cụ tài chính phái sinh tiền tệ",
            "ASSET_CARRYING_VALUE",
            52,
            "427.947",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            53,
            "- Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            54,
            "406.417",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            53,
            "- Giao dịch kỳ hạn tiền tệ",
            "ASSET_CARRYING_VALUE",
            55,
            "2.793",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            56,
            "- Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            57,
            "76.543.121",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            56,
            "- Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            58,
            "425.154",
        ),
        (
            "CURRENT_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            59,
            "Công cụ tài chính phái sinh lãi suất",
            "CONTRACT_VALUE",
            60,
            "1.499.641",
        ),
        (
            "CURRENT_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            59,
            "Công cụ tài chính phái sinh lãi suất",
            "LIABILITY_CARRYING_VALUE",
            61,
            "6.948",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            62,
            "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
            "CONTRACT_VALUE",
            63,
            "1.499.641",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            62,
            "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
            "LIABILITY_CARRYING_VALUE",
            64,
            "6.948",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            71,
            "Công cụ tài chính phái sinh tiền tệ",
            "CONTRACT_VALUE",
            72,
            "89.560.262",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            71,
            "Công cụ tài chính phái sinh tiền tệ",
            "ASSET_CARRYING_VALUE",
            73,
            "35.619",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            71,
            "Công cụ tài chính phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            74,
            "36.046",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            75,
            "- Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            76,
            "4.628.820",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            75,
            "- Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            77,
            "36.046",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            78,
            "- Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            79,
            "84.931.442",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            78,
            "- Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            80,
            "35.619",
        ),
    ],
    "CTG": [
        (
            "CURRENT_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            12,
            "1 - Công cụ tài chính phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            13,
            "105.943",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            14,
            "- Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            15,
            "47.442",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            16,
            "- Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            17,
            "58.501",
        ),
        (
            "CURRENT_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            19,
            "2 - Công cụ tài chính phái sinh lãi suất",
            "ASSET_CARRYING_VALUE",
            20,
            "17.126",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            22,
            "1 - Công cụ tài chính phái sinh tiền tệ",
            "ASSET_CARRYING_VALUE",
            23,
            "301.475",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            22,
            "1 - Công cụ tài chính phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            24,
            "15.179",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            25,
            "- Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            26,
            "15.179",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            27,
            "- Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            28,
            "301.360",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_FUTURE",
            29,
            "- Giao dịch tương lai tiền tệ",
            "ASSET_CARRYING_VALUE",
            30,
            "115",
        ),
        (
            "COMPARATIVE_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            31,
            "2 - Công cụ tài chính phái sinh lãi suất",
            "LIABILITY_CARRYING_VALUE",
            32,
            "57.848",
        ),
    ],
    "BID": [
        (
            "CURRENT_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            15,
            "Công cụ tài chính phái sinh tiền tệ",
            "ASSET_CARRYING_VALUE",
            16,
            "198,374,821",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            15,
            "Công cụ tài chính phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            17,
            "197,562,425",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            19,
            "- Giao dịch kỳ hạn tiền tệ",
            "ASSET_CARRYING_VALUE",
            20,
            "6,270,055",
        ),
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            19,
            "- Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            21,
            "6,286,090",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            23,
            "Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            24,
            "192,104,766",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            23,
            "Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            25,
            "191,276,335",
        ),
        (
            "CURRENT_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            27,
            "Công cụ tài chính phái sinh khác",
            "ASSET_CARRYING_VALUE",
            28,
            "13,553,181",
        ),
        (
            "CURRENT_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            27,
            "Công cụ tài chính phái sinh khác",
            "LIABILITY_CARRYING_VALUE",
            29,
            "13,609,595",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            31,
            "- Giao dịch hoán đổi lãi suất",
            "ASSET_CARRYING_VALUE",
            32,
            "13,553,181",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            31,
            "- Giao dịch hoán đổi lãi suất",
            "LIABILITY_CARRYING_VALUE",
            33,
            "13,609,595",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            39,
            "Công cụ tài chính phái sinh tiền tệ",
            "ASSET_CARRYING_VALUE",
            40,
            "139,457,357",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_DERIVATIVE_PARENT",
            39,
            "Công cụ tài chính phái sinh tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            41,
            "139,607,815",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            43,
            "Giao dịch kỳ hạn tiền tệ",
            "ASSET_CARRYING_VALUE",
            44,
            "23,359,604",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            43,
            "Giao dịch kỳ hạn tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            45,
            "23,532,939",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            47,
            "-Giao dịch hoán đổi tiền tệ",
            "ASSET_CARRYING_VALUE",
            48,
            "116,097,753",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            47,
            "-Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            49,
            "116,074,876",
        ),
        (
            "COMPARATIVE_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            51,
            "Công cụ tài chính phái sinh khác",
            "ASSET_CARRYING_VALUE",
            52,
            "3,799,595",
        ),
        (
            "COMPARATIVE_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            51,
            "Công cụ tài chính phái sinh khác",
            "LIABILITY_CARRYING_VALUE",
            53,
            "3,879,694",
        ),
        (
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            55,
            "-Giao dịch hoán đổi lãi suất",
            "ASSET_CARRYING_VALUE",
            56,
            "3,799,595",
        ),
        (
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            55,
            "-Giao dịch hoán đổi lãi suất",
            "LIABILITY_CARRYING_VALUE",
            57,
            "3,879,694",
        ),
    ],
    "VIB": [
        (
            "CURRENT_PERIOD",
            "FORWARD_CURRENCY",
            54,
            "Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            52,
            "20.769.284",
        ),
        (
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            55,
            "Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            56,
            "178.250.071",
        ),
        (
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            60,
            "Giao dịch hoán đổi lãi suất",
            "CONTRACT_VALUE",
            58,
            "12.126.217",
        ),
        (
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            64,
            "Giao dịch kỳ hạn tiền tệ",
            "CONTRACT_VALUE",
            65,
            "11.451.587",
        ),
        (
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            67,
            "Giao dịch hoán đổi tiền tệ",
            "CONTRACT_VALUE",
            68,
            "190.306.930",
        ),
        (
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            72,
            "Giao dịch hoán đổi lãi suất",
            "CONTRACT_VALUE",
            70,
            "8.559.343",
        ),
    ],
}

_DOCUMENT_META = {
    "ACB": (
        17,
        4,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN TÀI CHÍNH/NỢ TÀI CHÍNH KHÁC",
        "CONTRACT_ASSET_LIABILITY",
        "2026-06-30",
    ),
    "MBB": (
        43,
        52,
        "Các công cụ tài chính phái sinh và các tài sản/(công nợ) tài chính khác",
        "ASSET_LIABILITY_NET",
        "2026-06-30",
    ),
    "VPB": (
        41,
        45,
        "CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN NỢ PHẢI TRẢ TÀI CHÍNH KHÁC",
        "CONTRACT_INFLOW_OUTFLOW_NET",
        "2026-03-31",
    ),
    "HDB": (
        25,
        36,
        "Các công cụ tài chính phái sinh và các khoản tài sản/công nợ tài chính khác",
        "CONTRACT_ASSET_LIABILITY",
        "2026-06-30",
    ),
    "VCB": (None, None, None, None, "2026-06-30"),
    "CTG": (
        38,
        4,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÔNG NỢ TÀI CHÍNH KHÁC",
        "ASSET_LIABILITY",
        "2026-06-30",
    ),
    "BID": (
        21,
        5,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(CÔNG NỢ) TÀI CHÍNH KHÁC",
        "ASSET_LIABILITY_NET",
        "2026-06-30",
    ),
    "VIB": (
        32,
        40,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN NỢ TÀI CHÍNH KHÁC",
        "CONTRACT_NET",
        "2026-06-30",
    ),
}

_REVIEW_DASH_ROWS = {
    "HDB": [
        _dash_row(
            "CURRENT_PERIOD",
            "CURRENCY_SWAP",
            56,
            "- Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            [1492, 1414, 1516, 1428],
            "eb1273b4a742079543660b378aab378d2e0c157000403d2eb32c9a1d002b06cf",
        ),
        _dash_row(
            "CURRENT_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            59,
            "Công cụ tài chính phái sinh lãi suất",
            "ASSET_CARRYING_VALUE",
            [1218, 1448, 1236, 1464],
            "7d8930d8c29671912e734d1233e4d56426c192fab8f28ccb88583b79cf18a185",
        ),
        _dash_row(
            "CURRENT_PERIOD",
            "INTEREST_RATE_SWAP",
            62,
            "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
            "ASSET_CARRYING_VALUE",
            [1218, 1482, 1236, 1498],
            "40b638250674b49c7d5172b262c34ad9f6117ad75506b6034599f5bf2d5c687a",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "FORWARD_CURRENCY",
            75,
            "- Giao dịch kỳ hạn tiền tệ",
            "ASSET_CARRYING_VALUE",
            [1218, 1694, 1238, 1708],
            "7931b44334ab48aaaadb2fc6ba4ab817e498505dba1b3c0b70abe8375c042b15",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "CURRENCY_SWAP",
            78,
            "- Giao dịch hoán đổi tiền tệ",
            "LIABILITY_CARRYING_VALUE",
            [1492, 1726, 1516, 1740],
            "cfb479739614df25a11148de69c7c15ee0ab1f0cbfbdf40d842b8b30cf72fd33",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            81,
            "Công cụ tài chính phái sinh lãi suất",
            "CONTRACT_VALUE",
            [964, 1762, 988, 1778],
            "eda3546b33ff713fed82030117e1598fafc8ddb272d3a61cee9d75dafa2baab5",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            81,
            "Công cụ tài chính phái sinh lãi suất",
            "ASSET_CARRYING_VALUE",
            [1218, 1762, 1242, 1778],
            "66b8d8425ad1978138e6845f9bb4c2f9a522f8dda03f46ab8ceffb74ff5c1277",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "OTHER_DERIVATIVE_PARENT",
            81,
            "Công cụ tài chính phái sinh lãi suất",
            "LIABILITY_CARRYING_VALUE",
            [1492, 1762, 1516, 1778],
            "2a3040a63f9b9ba00f30ee5eea9b3a80d71eb044b947f0c596ee13eead44ccb0",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            82,
            "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
            "CONTRACT_VALUE",
            [964, 1796, 988, 1812],
            "54d8d70a14451a298c15607c4702728be3e5ebf2548c98397fbb7f68a58fd322",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            82,
            "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
            "ASSET_CARRYING_VALUE",
            [1218, 1796, 1242, 1812],
            "b417129fa9bfbea997ff12e52b3994a33e1de457337c768399038ce65658d8ad",
        ),
        _dash_row(
            "COMPARATIVE_PERIOD",
            "INTEREST_RATE_SWAP",
            82,
            "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
            "LIABILITY_CARRYING_VALUE",
            [1492, 1796, 1516, 1812],
            "a8e6ebae195d7041733d208bcecec5b421d2f37b82f3fe12d06ff7d7b1c33e80",
        ),
    ]
}


def _review_equations() -> dict[str, list[dict[str, Any]]]:
    return {
        "ACB": [],
        "MBB": [
            _equation(
                "CURRENT_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((65, "(161.250)"), (68, "(410.139)")),
                (62, "(571.389)"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((75, "(19.293)"), (78, "(679.214)")),
                (72, "(698.507)"),
            ),
        ],
        "VPB": [
            _equation(
                "CURRENT_FORWARD_INFLOW_PLUS_OUTFLOW_TO_NET",
                "SUM",
                ((68, "16.552.367"), (69, "(16.857.877)")),
                (70, "(305.510)"),
            ),
            _equation(
                "CURRENT_SWAP_INFLOW_PLUS_OUTFLOW_TO_NET",
                "SUM",
                ((73, "214.300.939"), (74, "(214.571.282)")),
                (75, "(270.343)"),
            ),
            _equation(
                "COMPARATIVE_FORWARD_INFLOW_PLUS_OUTFLOW_TO_NET",
                "SUM",
                ((95, "24.505.404"), (96, "(24.667.042)")),
                (97, "(161.638)"),
            ),
            _equation(
                "COMPARATIVE_SWAP_INFLOW_PLUS_OUTFLOW_TO_NET",
                "SUM",
                ((100, "250.947.145"), (101, "(251.141.228)")),
                (102, "(194.083)"),
            ),
        ],
        "HDB": [
            _equation(
                "CURRENT_CURRENCY_CONTRACT_CHILD_SUM",
                "SUM",
                ((54, "406.417"), (57, "76.543.121")),
                (51, "76.949.538"),
            ),
            _equation(
                "CURRENT_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((55, "2.793"), (58, "425.154")),
                (52, "427.947"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_CONTRACT_CHILD_SUM",
                "SUM",
                ((76, "4.628.820"), (79, "84.931.442")),
                (72, "89.560.262"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_ASSET_CHILD_SUM", "SUM", ((80, "35.619"),), (73, "35.619")
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM", "SUM", ((77, "36.046"),), (74, "36.046")
            ),
        ],
        "VCB": [],
        "CTG": [
            _equation(
                "CURRENT_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((15, "47.442"), (17, "58.501")),
                (13, "105.943"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((28, "301.360"), (30, "115")),
                (23, "301.475"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM", "SUM", ((26, "15.179"),), (24, "15.179")
            ),
        ],
        "BID": [
            _equation(
                "CURRENT_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((20, "6,270,055"), (24, "192,104,766")),
                (16, "198,374,821"),
            ),
            _equation(
                "CURRENT_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((21, "6,286,090"), (25, "191,276,335")),
                (17, "197,562,425"),
            ),
            _equation(
                "CURRENT_CURRENCY_NET_CHILD_SUM",
                "SUM",
                ((22, "(16,035)"), (26, "828,431")),
                (18, "812,396"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((44, "23,359,604"), (48, "116,097,753")),
                (40, "139,457,357"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((45, "23,532,939"), (49, "116,074,876")),
                (41, "139,607,815"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_NET_CHILD_SUM",
                "SUM",
                ((46, "(173,335)"), (50, "22,877")),
                (42, "(150,458)"),
            ),
            _equation(
                "CURRENT_CURRENCY_PARENT_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((16, "198,374,821"), (17, "197,562,425")),
                (18, "812,396"),
            ),
            _equation(
                "CURRENT_FORWARD_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((20, "6,270,055"), (21, "6,286,090")),
                (22, "(16,035)"),
            ),
            _equation(
                "CURRENT_SWAP_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((24, "192,104,766"), (25, "191,276,335")),
                (26, "828,431"),
            ),
            _equation(
                "CURRENT_OTHER_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((28, "13,553,181"), (29, "13,609,595")),
                (30, "(56,414)"),
            ),
            _equation(
                "CURRENT_INTEREST_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((32, "13,553,181"), (33, "13,609,595")),
                (34, "(56,414)"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_PARENT_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((40, "139,457,357"), (41, "139,607,815")),
                (42, "(150,458)"),
            ),
            _equation(
                "COMPARATIVE_FORWARD_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((44, "23,359,604"), (45, "23,532,939")),
                (46, "(173,335)"),
            ),
            _equation(
                "COMPARATIVE_SWAP_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((48, "116,097,753"), (49, "116,074,876")),
                (50, "22,877"),
            ),
            _equation(
                "COMPARATIVE_OTHER_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((52, "3,799,595"), (53, "3,879,694")),
                (54, "(80,099)"),
            ),
            _equation(
                "COMPARATIVE_INTEREST_ASSET_MINUS_LIABILITY",
                "DIFFERENCE",
                ((56, "3,799,595"), (57, "3,879,694")),
                (58, "(80,099)"),
            ),
        ],
        "VIB": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    equations = _review_equations()
    documents = []
    for code in EXPECTED_DOCUMENT_ORDER:
        page, owner_index, owner_text, mode, source_period = _DOCUMENT_META[code]
        rows = [
            *[_row(*item) for item in _REVIEW_ROWS.get(code, [])],
            *canonical_clone_v1(_REVIEW_DASH_ROWS.get(code, [])),
        ]
        documents.append(
            {
                "bank_code": code,
                "disposition": (
                    "UNIQUE_DETAILED_DERIVATIVE_REGION_PIXEL_REVIEWED"
                    if rows
                    else "NO_COMPLETE_DETAILED_DERIVATIVE_TRANSACTION_REGION_IN_BOUND_PDF"
                ),
                "equations": equations[code],
                "evidence_owner_line_index": owner_index,
                "layout_mode": mode,
                "mappings": rows,
                "owner_pixel_transcription": owner_text,
                "page_sequence": page,
                "source_period": source_period,
                "whole_document_family_absence_claim": False,
            }
        )
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0063"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0063:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex derivative pixel review differs from fixed ledger")
    return canonical_clone_v1(expected)


_ANNUAL_NOT_PRESENT = object()
_ANNUAL_GEOMETRY_DASH = {
    "derivation": "GRAPH_LANE_RIGHT_EDGE_AND_EVENT_ROW_GEOMETRY_VISIBLE_PIXEL_DASH"
}


def _annual_event(
    period: str,
    role: str,
    label_line_index: int,
    pixel_label: str,
    *,
    contract: object = _ANNUAL_NOT_PRESENT,
    asset: object = _ANNUAL_NOT_PRESENT,
    liability: object = _ANNUAL_NOT_PRESENT,
    net: object = _ANNUAL_NOT_PRESENT,
    inflow: object = _ANNUAL_NOT_PRESENT,
    outflow: object = _ANNUAL_NOT_PRESENT,
) -> dict[str, Any]:
    cells = {
        "CONTRACT_VALUE": contract,
        "ASSET_CARRYING_VALUE": asset,
        "LIABILITY_CARRYING_VALUE": liability,
    }
    mappings = []
    for lane, cell in cells.items():
        if cell is _ANNUAL_NOT_PRESENT:
            continue
        if cell is None:
            mappings.append(
                {
                    "label_line_index": label_line_index,
                    "label_pixel_transcription": pixel_label,
                    "lane_role": lane,
                    "period_role": period,
                    "pixel_binding": canonical_clone_v1(_ANNUAL_GEOMETRY_DASH),
                    "pixel_value": "-",
                    "role": role,
                    "value_line_index": None,
                }
            )
        else:
            if (
                type(cell) is not tuple
                or len(cell) != 2
                or type(cell[0]) is not int
                or type(cell[1]) is not str
            ):
                raise _error("annual derivative review cell specification drifted")
            mappings.append(
                _row(period, role, label_line_index, pixel_label, lane, cell[0], cell[1])
            )
    equations = []
    if (
        asset is not _ANNUAL_NOT_PRESENT
        and liability is not _ANNUAL_NOT_PRESENT
        and net is not _ANNUAL_NOT_PRESENT
        and asset is not None
        and liability is not None
    ):
        equations.append(
            _equation(
                f"{period}_{role}_ASSET_PLUS_LIABILITY_TO_NET",
                "SUM",
                (asset, liability),
                net,
            )
        )
    if (
        inflow is not _ANNUAL_NOT_PRESENT
        and outflow is not _ANNUAL_NOT_PRESENT
        and net is not _ANNUAL_NOT_PRESENT
    ):
        equations.append(
            _equation(
                f"{period}_{role}_INFLOW_PLUS_OUTFLOW_TO_NET",
                "SUM",
                (inflow, outflow),
                net,
            )
        )
    return {"equations": equations, "mappings": mappings}


def _annual_events_by_code() -> dict[str, list[dict[str, Any]]]:
    current = "CURRENT_PERIOD"
    comparative = "COMPARATIVE_PERIOD"
    return {
        "ACB": [
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                20,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(21, "3.646.093"),
                asset=None,
                liability=(22, "(31.284)"),
                net=(23, "(31.284)"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                24,
                "Giao dịch hoán đổi tiền tệ",
                contract=(25, "80.034.373"),
                asset=(26, "350.144"),
                liability=None,
                net=(27, "350.144"),
            ),
            _annual_event(
                current,
                "INTEREST_RATE_SWAP",
                29,
                "Giao dịch hoán đổi lãi suất",
                contract=(30, "3.104.030"),
                asset=(31, "5.438"),
                liability=None,
                net=(32, "5.438"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                51,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(52, "2.853.216"),
                asset=(53, "12.995"),
                liability=None,
                net=(54, "12.995"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                55,
                "Giao dịch hoán đổi tiền tệ",
                contract=(56, "95.715.115"),
                asset=(57, "203.660"),
                liability=None,
                net=(58, "203.660"),
            ),
            _annual_event(
                comparative,
                "INTEREST_RATE_SWAP",
                60,
                "Giao dịch hoán đổi lãi suất",
                contract=(61, "8.086.677"),
                asset=None,
                liability=(62, "(160.663)"),
                net=(63, "(160.663)"),
            ),
        ],
        "MBB": [
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                26,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(27, "29.867.112"),
                asset=(28, "29.934.146"),
                liability=(29, "(29.953.439)"),
                net=(30, "(19.293)"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                31,
                "Giao dịch hoán đổi tiền tệ",
                contract=(32, "298.419.232"),
                asset=(33, "297.861.282"),
                liability=(34, "(298.540.496)"),
                net=(35, "(679.214)"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                41,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(42, "29.002.492"),
                asset=(43, "29.129.292"),
                liability=(44, "(29.494.262)"),
                net=(45, "(364.970)"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                46,
                "Giao dịch hoán đổi tiền tệ",
                contract=(47, "135.536.141"),
                asset=(48, "136.362.265"),
                liability=(49, "(136.188.840)"),
                net=(50, "173.425"),
            ),
        ],
        "VPB": [
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                69,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(70, "24.642.959"),
                inflow=(71, "24.505.404"),
                outflow=(72, "(24.667.042)"),
                net=(73, "(161.638)"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                74,
                "Giao dịch hoán đổi tiền tệ",
                contract=(75, "257.793.753"),
                inflow=(76, "250.947.145"),
                outflow=(77, "(251.141.228)"),
                net=(78, "(194.083)"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                96,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(97, "36.417.208"),
                inflow=(98, "36.108.740"),
                outflow=(99, "(36.071.453)"),
                net=(100, "37.287"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                101,
                "Giao dịch hoán đổi tiền tệ",
                contract=(102, "138.875.904"),
                inflow=(103, "133.379.242"),
                outflow=(104, "(132.820.534)"),
                net=(105, "558.708"),
            ),
        ],
        "HDB": [
            _annual_event(
                current,
                "CURRENCY_DERIVATIVE_PARENT",
                30,
                "Công cụ tài chính phái sinh tiền tệ",
                contract=(31, "89.560.262"),
                asset=(32, "35.619"),
                liability=(33, "36.046"),
            ),
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                34,
                "- Giao dịch kỳ hạn tiền tệ",
                contract=(35, "4.628.820"),
                asset=None,
                liability=(36, "36.046"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                37,
                "- Giao dịch hoán đổi tiền tệ",
                contract=(38, "84.931.442"),
                asset=(39, "35.619"),
                liability=None,
            ),
            _annual_event(
                current,
                "OTHER_DERIVATIVE_PARENT",
                40,
                "Công cụ tài chính phái sinh lãi suất",
                contract=None,
                asset=None,
                liability=None,
            ),
            _annual_event(
                current,
                "INTEREST_RATE_SWAP",
                41,
                "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
                contract=None,
                asset=None,
                liability=None,
            ),
            _annual_event(
                comparative,
                "CURRENCY_DERIVATIVE_PARENT",
                48,
                "Công cụ tài chính phái sinh tiền tệ",
                contract=(49, "94.511.570"),
                asset=None,
                liability=(50, "14.649"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                51,
                "- Giao dịch kỳ hạn tiền tệ",
                contract=(52, "3.420.583"),
                asset=None,
                liability=(53, "3.182"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                54,
                "- Giao dịch hoán đổi tiền tệ",
                contract=(55, "91.090.987"),
                asset=None,
                liability=(56, "11.467"),
            ),
            _annual_event(
                comparative,
                "OTHER_DERIVATIVE_PARENT",
                57,
                "Công cụ tài chính phái sinh lãi suất",
                contract=(58, "977.800"),
                asset=None,
                liability=(59, "3.800"),
            ),
            _annual_event(
                comparative,
                "INTEREST_RATE_SWAP",
                60,
                "- Giao dịch hoán đổi lãi suất tiền tệ chéo",
                contract=(61, "977.800"),
                asset=None,
                liability=(62, "3.800"),
            ),
        ],
        "VCB": [],
        "CTG": [
            _annual_event(
                current,
                "CURRENCY_DERIVATIVE_PARENT",
                51,
                "Công cụ tài chính phái sinh tiền tệ",
                asset=(52, "301.475"),
                liability=(53, "(15.179)"),
                net=(54, "286.296"),
            ),
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                55,
                "Giao dịch kỳ hạn tiền tệ",
                asset=None,
                liability=(56, "(15.179)"),
                net=(57, "(15.179)"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                58,
                "Giao dịch hoán đổi tiền tệ",
                asset=(59, "301.360"),
                liability=None,
                net=(60, "301.360"),
            ),
            _annual_event(
                current,
                "CURRENCY_FUTURE",
                61,
                "Giao dịch tương lai tiền tệ",
                asset=(62, "115"),
                liability=None,
                net=(63, "115"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_DERIVATIVE_PARENT",
                79,
                "Công cụ tài chính phái sinh tiền tệ",
                asset=(80, "25.355"),
                liability=(81, "(298.910)"),
                net=(82, "(273.555)"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                83,
                "Giao dịch kỳ hạn tiền tệ",
                asset=None,
                liability=(84, "(298.910)"),
                net=(85, "(298.910)"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                86,
                "Giao dịch hoán đổi tiền tệ",
                asset=(87, "25.355"),
                liability=None,
                net=(88, "25.355"),
            ),
        ],
        "BID": [
            _annual_event(
                current,
                "CURRENCY_DERIVATIVE_PARENT",
                39,
                "Công cụ tài chính phái sinh tiền tệ",
                asset=(40, "139.457.357"),
                liability=(41, "(139.607.815)"),
                net=(42, "(150.458)"),
            ),
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                43,
                "Giao dịch kỳ hạn tiền tệ",
                asset=(44, "23.359.604"),
                liability=(45, "(23.532.939)"),
                net=(46, "(173.335)"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                47,
                "Giao dịch hoán đổi tiền tệ",
                asset=(48, "116.097.753"),
                liability=(49, "(116.074.876)"),
                net=(50, "22.877"),
            ),
            _annual_event(
                current,
                "OTHER_DERIVATIVE_PARENT",
                51,
                "Công cụ tài chính phái sinh khác",
                asset=(52, "3.799.595"),
                liability=(53, "(3.879.694)"),
                net=(54, "(80.099)"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_DERIVATIVE_PARENT",
                74,
                "Công cụ tài chính phái sinh tiền tệ",
                asset=(75, "75.548.664"),
                liability=(76, "(74.729.989)"),
                net=(77, "818.675"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                79,
                "Giao dịch kỳ hạn tiền tệ",
                asset=(80, "10.943.598"),
                liability=(81, "(10.947.498)"),
                net=(82, "(3.900)"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                83,
                "Giao dịch hoán đổi tiền tệ",
                asset=(84, "64.605.066"),
                liability=(85, "(63.782.491)"),
                net=(86, "822.575"),
            ),
            _annual_event(
                comparative,
                "OTHER_DERIVATIVE_PARENT",
                87,
                "Công cụ tài chính phái sinh khác",
                asset=(88, "6.249.793"),
                liability=(89, "(6.405.212)"),
                net=(90, "(155.419)"),
            ),
        ],
        "VIB": [
            _annual_event(
                current,
                "FORWARD_CURRENCY",
                19,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(20, "11.451.587"),
            ),
            _annual_event(
                current,
                "CURRENCY_SWAP",
                22,
                "Giao dịch hoán đổi tiền tệ",
                contract=(23, "190.306.930"),
            ),
            _annual_event(
                current,
                "INTEREST_RATE_SWAP",
                25,
                "Giao dịch hoán đổi lãi suất",
                contract=(26, "8.559.343"),
            ),
            _annual_event(
                comparative,
                "FORWARD_CURRENCY",
                31,
                "Giao dịch kỳ hạn tiền tệ",
                contract=(32, "15.309.657"),
            ),
            _annual_event(
                comparative,
                "CURRENCY_SWAP",
                34,
                "Giao dịch hoán đổi tiền tệ",
                contract=(35, "163.623.724"),
            ),
            _annual_event(
                comparative,
                "INTEREST_RATE_SWAP",
                37,
                "Giao dịch hoán đổi lãi suất",
                contract=(38, "13.594.442"),
            ),
        ],
    }


_ANNUAL_2025_DOCUMENT_META = {
    "ACB": (
        49,
        5,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN TÀI CHÍNH KHÁC",
        "CONTRACT_ASSET_LIABILITY_NET",
    ),
    "MBB": (
        66,
        10,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN NỢ TÀI CHÍNH KHÁC",
        "CONTRACT_ASSET_LIABILITY_NET",
    ),
    "VPB": (
        44,
        48,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN NỢ TÀI CHÍNH KHÁC",
        "CONTRACT_INFLOW_OUTFLOW_NET",
    ),
    "HDB": (
        35,
        16,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN TÀI SẢN/CÔNG NỢ TÀI CHÍNH KHÁC",
        "CONTRACT_ASSET_LIABILITY",
    ),
    "VCB": (None, None, None, None),
    "CTG": (
        42,
        41,
        "CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/KHOẢN NỢ TÀI CHÍNH KHÁC",
        "ASSET_LIABILITY_NET",
    ),
    "BID": (
        41,
        29,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(CÔNG NỢ) TÀI CHÍNH KHÁC",
        "ASSET_LIABILITY_NET",
    ),
    "VIB": (
        37,
        5,
        "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(KHOẢN NỢ) TÀI CHÍNH KHÁC",
        "CONTRACT_NET",
    ),
}


def _annual_extra_equations() -> dict[str, list[dict[str, Any]]]:
    return {
        "ACB": [
            _equation(
                "CURRENT_CONTRACT_CHILD_SUM",
                "SUM",
                ((21, "3.646.093"), (25, "80.034.373"), (30, "3.104.030")),
                (33, "86.784.496"),
            ),
            _equation(
                "CURRENT_ASSET_CHILD_SUM",
                "SUM",
                ((26, "350.144"), (31, "5.438")),
                (34, "355.582"),
            ),
            _equation("CURRENT_LIABILITY_CHILD_SUM", "SUM", ((22, "(31.284)"),), (35, "(31.284)")),
            _equation(
                "CURRENT_NET_CHILD_SUM",
                "SUM",
                ((23, "(31.284)"), (27, "350.144"), (32, "5.438")),
                (36, "324.298"),
            ),
            _equation(
                "COMPARATIVE_CONTRACT_CHILD_SUM",
                "SUM",
                ((52, "2.853.216"), (56, "95.715.115"), (61, "8.086.677")),
                (64, "106.655.008"),
            ),
            _equation(
                "COMPARATIVE_ASSET_CHILD_SUM",
                "SUM",
                ((53, "12.995"), (57, "203.660")),
                (65, "216.655"),
            ),
            _equation(
                "COMPARATIVE_LIABILITY_CHILD_SUM",
                "SUM",
                ((62, "(160.663)"),),
                (66, "(160.663)"),
            ),
            _equation(
                "COMPARATIVE_NET_CHILD_SUM",
                "SUM",
                ((54, "12.995"), (58, "203.660"), (63, "(160.663)")),
                (67, "55.992"),
            ),
        ],
        "MBB": [
            _equation(
                "CURRENT_CONTRACT_CHILD_SUM",
                "SUM",
                ((27, "29.867.112"), (32, "298.419.232")),
                (36, "328.286.344"),
            ),
            _equation(
                "CURRENT_ASSET_CHILD_SUM",
                "SUM",
                ((28, "29.934.146"), (33, "297.861.282")),
                (37, "327.795.428"),
            ),
            _equation(
                "CURRENT_LIABILITY_CHILD_SUM",
                "SUM",
                ((29, "(29.953.439)"), (34, "(298.540.496)")),
                (38, "(328.493.935)"),
            ),
            _equation(
                "CURRENT_NET_CHILD_SUM",
                "SUM",
                ((30, "(19.293)"), (35, "(679.214)")),
                (39, "(698.507)"),
            ),
            _equation(
                "COMPARATIVE_CONTRACT_CHILD_SUM",
                "SUM",
                ((42, "29.002.492"), (47, "135.536.141")),
                (51, "164.538.633"),
            ),
            _equation(
                "COMPARATIVE_ASSET_CHILD_SUM",
                "SUM",
                ((43, "29.129.292"), (48, "136.362.265")),
                (52, "165.491.557"),
            ),
            _equation(
                "COMPARATIVE_LIABILITY_CHILD_SUM",
                "SUM",
                ((44, "(29.494.262)"), (49, "(136.188.840)")),
                (53, "(165.683.102)"),
            ),
            _equation(
                "COMPARATIVE_NET_CHILD_SUM",
                "SUM",
                ((45, "(364.970)"), (50, "173.425")),
                (54, "(191.545)"),
            ),
        ],
        "VPB": [],
        "HDB": [
            _equation(
                "CURRENT_CURRENCY_CONTRACT_CHILD_SUM",
                "SUM",
                ((35, "4.628.820"), (38, "84.931.442")),
                (31, "89.560.262"),
            ),
            _equation("CURRENT_CURRENCY_ASSET_CHILD_SUM", "SUM", ((39, "35.619"),), (32, "35.619")),
            _equation(
                "CURRENT_CURRENCY_LIABILITY_CHILD_SUM", "SUM", ((36, "36.046"),), (33, "36.046")
            ),
            _equation(
                "CURRENT_ALL_CONTRACT_TOTAL",
                "SUM",
                ((35, "4.628.820"), (38, "84.931.442")),
                (42, "89.560.262"),
            ),
            _equation("CURRENT_ALL_ASSET_TOTAL", "SUM", ((39, "35.619"),), (43, "35.619")),
            _equation("CURRENT_ALL_LIABILITY_TOTAL", "SUM", ((36, "36.046"),), (44, "36.046")),
            _equation(
                "COMPARATIVE_CURRENCY_CONTRACT_CHILD_SUM",
                "SUM",
                ((52, "3.420.583"), (55, "91.090.987")),
                (49, "94.511.570"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((53, "3.182"), (56, "11.467")),
                (50, "14.649"),
            ),
            _equation(
                "COMPARATIVE_ALL_CONTRACT_TOTAL",
                "SUM",
                ((52, "3.420.583"), (55, "91.090.987"), (58, "977.800")),
                (63, "95.489.370"),
            ),
            _equation(
                "COMPARATIVE_ALL_LIABILITY_TOTAL",
                "SUM",
                ((53, "3.182"), (56, "11.467"), (59, "3.800")),
                (64, "18.449"),
            ),
        ],
        "VCB": [],
        "CTG": [
            _equation(
                "CURRENT_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((59, "301.360"), (62, "115")),
                (52, "301.475"),
            ),
            _equation(
                "CURRENT_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((56, "(15.179)"),),
                (53, "(15.179)"),
            ),
            _equation(
                "CURRENT_CURRENCY_NET_CHILD_SUM",
                "SUM",
                ((57, "(15.179)"), (60, "301.360"), (63, "115")),
                (54, "286.296"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_ASSET_CHILD_SUM", "SUM", ((87, "25.355"),), (80, "25.355")
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((84, "(298.910)"),),
                (81, "(298.910)"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_NET_CHILD_SUM",
                "SUM",
                ((85, "(298.910)"), (88, "25.355")),
                (82, "(273.555)"),
            ),
        ],
        "BID": [
            _equation(
                "CURRENT_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((44, "23.359.604"), (48, "116.097.753")),
                (40, "139.457.357"),
            ),
            _equation(
                "CURRENT_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((45, "(23.532.939)"), (49, "(116.074.876)")),
                (41, "(139.607.815)"),
            ),
            _equation(
                "CURRENT_CURRENCY_NET_CHILD_SUM",
                "SUM",
                ((46, "(173.335)"), (50, "22.877")),
                (42, "(150.458)"),
            ),
            _equation(
                "CURRENT_OTHER_ASSET_CHILD_SUM", "SUM", ((52, "3.799.595"),), (52, "3.799.595")
            ),
            _equation(
                "CURRENT_OTHER_LIABILITY_CHILD_SUM",
                "SUM",
                ((53, "(3.879.694)"),),
                (53, "(3.879.694)"),
            ),
            _equation("CURRENT_OTHER_NET_CHILD_SUM", "SUM", ((54, "(80.099)"),), (54, "(80.099)")),
            _equation(
                "COMPARATIVE_CURRENCY_ASSET_CHILD_SUM",
                "SUM",
                ((80, "10.943.598"), (84, "64.605.066")),
                (75, "75.548.664"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_LIABILITY_CHILD_SUM",
                "SUM",
                ((81, "(10.947.498)"), (85, "(63.782.491)")),
                (76, "(74.729.989)"),
            ),
            _equation(
                "COMPARATIVE_CURRENCY_NET_CHILD_SUM",
                "SUM",
                ((82, "(3.900)"), (86, "822.575")),
                (77, "818.675"),
            ),
            _equation(
                "COMPARATIVE_OTHER_ASSET_CHILD_SUM", "SUM", ((88, "6.249.793"),), (88, "6.249.793")
            ),
            _equation(
                "COMPARATIVE_OTHER_LIABILITY_CHILD_SUM",
                "SUM",
                ((89, "(6.405.212)"),),
                (89, "(6.405.212)"),
            ),
            _equation(
                "COMPARATIVE_OTHER_NET_CHILD_SUM",
                "SUM",
                ((90, "(155.419)"),),
                (90, "(155.419)"),
            ),
        ],
        "VIB": [],
    }


def _annual_2025_review_documents() -> list[dict[str, Any]]:
    events = _annual_events_by_code()
    extra_equations = _annual_extra_equations()
    documents = []
    for code in EXPECTED_DOCUMENT_ORDER:
        page, owner_index, owner_text, mode = _ANNUAL_2025_DOCUMENT_META[code]
        mappings = [row for event in events[code] for row in event["mappings"]]
        equations = [
            *[equation for event in events[code] for equation in event["equations"]],
            *extra_equations[code],
        ]
        documents.append(
            {
                "bank_code": code,
                "disposition": (
                    "UNIQUE_DETAILED_DERIVATIVE_REGION_PIXEL_REVIEWED"
                    if page is not None
                    else "CONFIRMED_NO_COMPLETE_DETAILED_DERIVATIVE_REGION_IN_BOUND_ANNUAL_REPORT"
                ),
                "equations": equations,
                "evidence_owner_line_index": owner_index,
                "layout_mode": mode,
                "mappings": mappings,
                "owner_pixel_transcription": owner_text,
                "page_sequence": page,
                "source_period": "2025-12-31",
                "whole_document_family_absence_claim": page is None,
            }
        )
    return documents


def _annual_2025_review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": ANNUAL_2025_CLAIM_BOUNDARY,
        "documents": _annual_2025_review_documents(),
        "format_version": ANNUAL_2025_REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0111",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
        "semantic_axis_sha256": ANNUAL_2025_EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": ANNUAL_2025_EXPECTED_INDEX_SHA256,
        "state": "ANNUAL_2025_CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {
        **material,
        "review_id": "e0111:pixel-review:" + canonical_json_sha256_v1(material),
    }


def _annual_2025_review(value: Any) -> dict[str, Any]:
    expected = _annual_2025_review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("annual-2025 Codex derivative pixel review differs from fixed ledger")
    return canonical_clone_v1(expected)


def _document_by_code(documents: Any, code: str, label: str) -> dict[str, Any]:
    if type(documents) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in documents
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page_by_number(document: Mapping[str, Any], page_number: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict
        and page.get("physical_page", page.get("page_sequence")) == page_number
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain page {page_number}")
    return matches[0]


def _axis_line(page: Mapping[str, Any], line_index: int) -> dict[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= line_index < len(lines):
        raise _error("fresh VietOCR line index drifted")
    line = lines[line_index]
    if type(line) is not dict or line.get("source_line_index") != line_index:
        raise _error("fresh VietOCR line identity drifted")
    return line


def _anchor_match(transformer_text: str, pixel_text: str, label: str) -> str:
    surface = re.sub(r"^\s*\(?\d{1,3}\)?\s*[.)\-–—:]?\s*", "", transformer_text)
    pixel_surface = re.sub(r"^\s*\(?\d{1,3}\)?\s*[.)\-–—:]?\s*", "", pixel_text)
    kind = match_vietnamese_anchor_alias_v1(surface, [pixel_surface])
    if kind is None:
        raise _error(f"visible {label} and fresh VietOCR disagree beyond tolerated glyph drift")
    return kind


def _event(region: Mapping[str, Any], period: str, role: str) -> dict[str, Any]:
    events = region.get("events")
    if type(events) is not list:
        raise _error("derivative graph event axis drifted")
    matches = [
        item
        for item in events
        if type(item) is dict and item.get("period_role") == period and item.get("role") == role
    ]
    if len(matches) != 1:
        raise _error(f"derivative graph does not contain one exact {period}/{role} row")
    return matches[0]


def _schema_id(period: str, lane: str, role: str) -> int:
    try:
        return _AXIS_BASE[(period, lane)] + _ROLE_OFFSET[role]
    except KeyError as exc:
        raise _error("review tried to map an unsupported derivative axis or role") from exc


def _schema_binding(item: Any, period: str, lane: str, role: str) -> dict[str, Any]:
    schema_id = _schema_id(period, lane, role)
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.parent_id != _SCHEMA_PARENT[lane]
        or not 631 <= item.schema_id <= 715
    ):
        raise _error("reviewed derivative mapping does not bind one exact live TM item")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    line_index: int,
    pixel_transcription: str,
) -> dict[str, Any]:
    try:
        return support._source_value(
            axis_page,
            semantic_page,
            crop_page,
            source_texts,
            {"line_index": line_index, "pixel_transcription": pixel_transcription},
        )
    except Exception as exc:
        raise _error(f"derivative source numeric evidence drifted: {exc}") from exc


def _render_bytes(crop_page: Mapping[str, Any]) -> bytes:
    binding = crop_page.get("render_binding")
    if (
        type(binding) is not dict
        or type(binding.get("path")) is not str
        or type(binding.get("size_bytes")) is not int
    ):
        raise _error("visible derivative page render binding drifted")
    payload = support._stable_bytes(Path(binding["path"]))
    if len(payload) != binding["size_bytes"] or hashlib.sha256(payload).hexdigest() != _sha256(
        binding.get("sha256"), "visible derivative page render"
    ):
        raise _error("visible derivative page render bytes drifted")
    return payload


def _dash_source_value(row: Mapping[str, Any], render_bytes: bytes) -> dict[str, Any]:
    binding = row.get("pixel_binding")
    if (
        row.get("value_line_index") is not None
        or row.get("pixel_value") != "-"
        or type(binding) is not dict
        or set(binding) != {"bbox_raw_pixels", "rgb_sha256"}
        or type(binding["bbox_raw_pixels"]) is not list
        or len(binding["bbox_raw_pixels"]) != 4
        or any(type(item) is not int for item in binding["bbox_raw_pixels"])
    ):
        raise _error("pixel-only derivative DASH evidence shape drifted")
    bbox = binding["bbox_raw_pixels"]
    if bbox[0] < 0 or bbox[1] < 0 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise _error("pixel-only derivative DASH bbox drifted")
    try:
        image = Image.open(BytesIO(render_bytes))
        image.load()
        rgb = image.convert("RGB")
    except Exception as exc:
        raise _error("visible derivative page render is not one decodable image") from exc
    if bbox[2] > rgb.width or bbox[3] > rgb.height:
        raise _error("pixel-only derivative DASH bbox exceeds visible page")
    digest = hashlib.sha256(rgb.crop(tuple(bbox)).tobytes()).hexdigest()
    if digest != _sha256(binding["rgb_sha256"], "pixel-only derivative DASH crop"):
        raise _error("pixel-only derivative DASH crop bytes drifted")
    return {
        "crop_ref": None,
        "fresh_vietocr_numeric_proposal": None,
        "normalized_value": 0,
        "pixel_binding": canonical_clone_v1(binding),
        "pixel_transcription": "-",
        "source_cell_status": "DASH",
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": "NO_TEXT_GEOMETRY_VISIBLE_PIXEL_DASH",
    }


def _annual_geometry_dash_source_value(
    row: Mapping[str, Any],
    event: Mapping[str, Any],
    region: Mapping[str, Any],
    render_bytes: bytes,
) -> dict[str, Any]:
    if not same_typed_json_v1(row.get("pixel_binding"), _ANNUAL_GEOMETRY_DASH):
        raise _error("annual derivative DASH derivation marker drifted")
    lane = row.get("lane_role")
    right_edges = sorted(
        item["bbox"][2]
        for candidate in region.get("events", [])
        for item in candidate.get("value_proposals", [])
        if item.get("lane_role") == lane
    )
    if not right_edges:
        raise _error("annual derivative DASH lane has no numeric right-edge geometry")
    midpoint = len(right_edges) // 2
    lane_right = (
        right_edges[midpoint]
        if len(right_edges) % 2
        else round((right_edges[midpoint - 1] + right_edges[midpoint]) / 2)
    )
    event_bbox = event.get("bbox")
    if (
        type(event_bbox) is not list
        or len(event_bbox) != 4
        or any(type(item) is not int for item in event_bbox)
    ):
        raise _error("annual derivative DASH event geometry drifted")
    row_center = round((event_bbox[1] + event_bbox[3]) / 2)
    bbox = [lane_right - 45, row_center - 13, lane_right + 5, row_center + 14]
    try:
        image = Image.open(BytesIO(render_bytes))
        image.load()
        rgb = image.convert("RGB")
    except Exception as exc:
        raise _error("annual derivative visible render is not one decodable image") from exc
    if bbox[0] < 0 or bbox[1] < 0 or bbox[2] > rgb.width or bbox[3] > rgb.height:
        raise _error("annual derivative DASH search window exceeds visible page")
    crop = rgb.crop(tuple(bbox))
    grayscale = crop.convert("L")
    dark = [
        (x, y)
        for y in range(grayscale.height)
        for x in range(grayscale.width)
        if grayscale.getpixel((x, y)) < 230
    ]
    if not dark:
        raise _error("annual derivative expected DASH has no visible dark glyph")
    remaining = set(dark)
    components: list[list[tuple[int, int]]] = []
    while remaining:
        pending = [remaining.pop()]
        component = []
        while pending:
            point = pending.pop()
            component.append(point)
            for delta_x in (-1, 0, 1):
                for delta_y in (-1, 0, 1):
                    neighbour = (point[0] + delta_x, point[1] + delta_y)
                    if neighbour in remaining:
                        remaining.remove(neighbour)
                        pending.append(neighbour)
        components.append(component)
    dash_component = max(components, key=len)
    dark_bbox = [
        min(x for x, _ in dash_component),
        min(y for _, y in dash_component),
        max(x for x, _ in dash_component) + 1,
        max(y for _, y in dash_component) + 1,
    ]
    width = dark_bbox[2] - dark_bbox[0]
    height = dark_bbox[3] - dark_bbox[1]
    if not (len(dash_component) >= 6 and 6 <= width <= 18 and 1 <= height <= 9 and width >= height):
        raise _error("annual derivative expected DASH pixel shape drifted")
    derived = canonical_clone_v1(row)
    derived["pixel_binding"] = {
        "bbox_raw_pixels": bbox,
        "rgb_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
    }
    result = _dash_source_value(derived, render_bytes)
    result["source_numeric_challenger_status"] = (
        "VISIBLE_AUTHENTICATED_PIXEL_DASH_DERIVED_FROM_GRAPH_ROW_AND_LANE_GEOMETRY"
    )
    return result


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count": sum(
            mapping["source_value"]["fresh_vietocr_numeric_proposal"] is not None
            and mapping["source_value"]["fresh_vietocr_numeric_proposal"]
            != mapping["source_value"]["pixel_transcription"]
            for trial in trials
            for mapping in trial["verified_mappings"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial.get("source_period_status") == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("derivative mapping result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("derivative mapping result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("verified_accounting_equations")) is not list
            or trial.get("status")
            not in {
                "UNRESOLVED",
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT",
            }
        ):
            raise _error("derivative mapping trial shape drifted")
        for mapping in trial["verified_mappings"]:
            if type(mapping) is not dict or mapping.get("status") != "VERIFIED_BY_CODEX":
                raise _error("derivative mapping status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "dfi8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("derivative mapping result identity drifted")
    return canonical_clone_v1(value)


def build_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build the exact bounded eight-document derivative mapping result."""

    review = _review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state")
        != "FULL_DOCUMENT_DERIVATIVE_FINANCIAL_INSTRUMENT_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("derivative mapping input authority drifted")
    _sha256(crop_manifest_sha256, "crop manifest")
    _sha256(review_sha256, "pixel review")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document_by_code(review["documents"], code, "pixel review")
        axis_document = _document_by_code(axis["documents"], code, "fresh VietOCR axis")
        semantic_document = _document_by_code(
            semantic_index.get("documents"), code, "semantic index"
        )
        crop_document = _document_by_code(crop_manifest.get("documents"), code, "crop manifest")
        scan_trial = _document_by_code(structure_scan.get("trials"), code, "structure scan")
        matcher = scan_trial.get("matcher_result")
        if scan_trial.get("document_ordinal") != ordinal or type(matcher) is not dict:
            raise _error("whole-PDF derivative scan identity drifted")
        if not reviewed["mappings"]:
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("regions") != []
                or reviewed["page_sequence"] is not None
                or reviewed["equations"]
            ):
                raise _error("negative derivative disposition drifted")
            trials.append(
                {
                    "cluster_boundary": None,
                    "disposition": reviewed["disposition"],
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "evidence_page_sequence": None,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": reviewed["source_period"],
                    "source_period_status": "VERIFIED_SOURCE_PERIOD_Q2_2026",
                    "status": "UNRESOLVED",
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "whole_document_family_absence_claim": False,
                    "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
                }
            )
            continue
        if (
            matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or matcher.get("uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or type(matcher.get("regions")) is not list
            or len(matcher["regions"]) != 1
        ):
            raise _error("whole-PDF derivative region is not exactly unique")
        region = matcher["regions"][0]
        page_number = reviewed["page_sequence"]
        if (
            region.get("page_sequence") != page_number
            or region.get("owner", {}).get("source_line_index")
            != reviewed["evidence_owner_line_index"]
            or region.get("layout", {}).get("presentation_mode") != reviewed["layout_mode"]
        ):
            raise _error("reviewed derivative page/layout disagrees with shared graph")
        axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
        semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
        crop_page = _page_by_number(crop_document, page_number, "crop manifest")
        owner = _axis_line(axis_page, reviewed["evidence_owner_line_index"])
        _anchor_match(owner["vietocr_text"], reviewed["owner_pixel_transcription"], "owner")
        try:
            source_texts = support._source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"derivative source line axis drifted: {exc}") from exc
        mapped_rows = []
        render_bytes: bytes | None = None
        seen_intersections: set[tuple[str, str, str]] = set()
        for row in reviewed["mappings"]:
            period = row["period_role"]
            role = row["role"]
            lane = row["lane_role"]
            intersection = (period, role, lane)
            if intersection in seen_intersections:
                raise _error("duplicate derivative period/role/lane mapping")
            seen_intersections.add(intersection)
            event = _event(region, period, role)
            if event.get("source_line_index") != row["label_line_index"]:
                raise _error("derivative graph/review label binding drifted")
            label_line = _axis_line(axis_page, row["label_line_index"])
            match_kind = _anchor_match(
                label_line["vietocr_text"], row["label_pixel_transcription"], role
            )
            if row["value_line_index"] is None:
                if any(item.get("lane_role") == lane for item in event.get("value_proposals", [])):
                    raise _error("pixel-only derivative DASH overlaps a graph text value")
                if render_bytes is None:
                    render_bytes = _render_bytes(crop_page)
                source_value = _dash_source_value(row, render_bytes)
            else:
                value_matches = [
                    item
                    for item in event.get("value_proposals", [])
                    if item.get("source_line_index") == row["value_line_index"]
                    and item.get("lane_role") == lane
                ]
                if len(value_matches) != 1 or row.get("pixel_binding") is not None:
                    raise _error("reviewed derivative value left its graph-bound lane")
                source_value = _source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    row["value_line_index"],
                    row["pixel_value"],
                )
            schema = _schema_binding(
                schema_by_id.get(_schema_id(period, lane, role)), period, lane, role
            )
            mapped_rows.append(
                {
                    **schema,
                    "anchor_match_kind": match_kind,
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "lane_role": lane,
                    "normalized_anchor": normalize_vietnamese_anchor_v1(label_line["vietocr_text"]),
                    "normalized_value": source_value["normalized_value"],
                    "period_role": period,
                    "physical_page": page_number,
                    "role": role,
                    "source_value": source_value,
                    "status": "VERIFIED_BY_CODEX",
                    "topology": "UNIQUE_PERIOD_ROLE_ROW_BY_MEANINGFUL_COLUMN_INTERSECTION",
                    "vietocr_transformer_text": [label_line["vietocr_text"]],
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            components = [
                _source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    item["line_index"],
                    item["pixel_transcription"],
                )
                for item in equation["component_values"]
            ]
            total = _source_value(
                axis_page,
                semantic_page,
                crop_page,
                source_texts,
                equation["visible_total"]["line_index"],
                equation["visible_total"]["pixel_transcription"],
            )
            if equation["operation"] == "SUM":
                computed = sum(item["normalized_value"] for item in components)
            elif equation["operation"] == "DIFFERENCE" and len(components) == 2:
                computed = components[0]["normalized_value"] - components[1]["normalized_value"]
            else:
                raise _error("derivative accounting operation drifted")
            if computed != total["normalized_value"]:
                raise _error(f"derivative accounting equation does not close: {code}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "operation": equation["operation"],
                    "physical_page": page_number,
                    "status": "CORROBORATED_EXACT",
                    "visible_total": total["normalized_value"],
                }
            )
        period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "cluster_boundary": canonical_clone_v1(region["cluster_boundary"]),
                "disposition": reviewed["disposition"],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "evidence_page_sequence": page_number,
                "layout": canonical_clone_v1(region["layout"]),
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                    if period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "verified_accounting_equations": equations,
                "verified_mappings": mapped_rows,
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
                "whole_document_family_absence_claim": False,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "state": "DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "dfi8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _annual_2025_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            mapping["source_value"]["source_numeric_challenger_status"].startswith(
                "VISIBLE_AUTHENTICATED_PIXEL_DASH"
            )
            for trial in trials
            for mapping in trial["verified_mappings"]
        ),
        "bound_report_absence_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count": sum(
            trial["fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count"]
            for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }


def _validate_annual_2025_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual derivative mapping result fields drifted")
    if (
        value["format_version"] != ANNUAL_2025_FORMAT_VERSION
        or value["claim_boundary"] != ANNUAL_2025_CLAIM_BOUNDARY
        or value["state"]
        != "ANNUAL_2025_DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _annual_2025_metrics(value["trials"]))
    ):
        raise _error("annual derivative mapping result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("verified_accounting_equations")) is not list
            or trial.get("status")
            not in {"CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT", "VERIFIED_BY_CODEX"}
        ):
            raise _error("annual derivative mapping trial shape drifted")
        for mapping in trial["verified_mappings"]:
            if type(mapping) is not dict or mapping.get("status") != "VERIFIED_BY_CODEX":
                raise _error("annual derivative mapping status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "annual2025dfi8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("annual derivative mapping result identity drifted")
    return canonical_clone_v1(value)


def build_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build the audited consolidated annual-2025 derivative mapping result."""

    review = _annual_2025_review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != ANNUAL_2025_EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != ANNUAL_2025_EXPECTED_SCAN_ID
        or structure_scan.get("state")
        != "FULL_DOCUMENT_DERIVATIVE_FINANCIAL_INSTRUMENT_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("annual derivative mapping input authority drifted")
    _sha256(crop_manifest_sha256, "annual crop manifest")
    _sha256(review_sha256, "annual pixel review")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document_by_code(review["documents"], code, "annual pixel review")
        axis_document = _document_by_code(axis["documents"], code, "annual fresh VietOCR axis")
        semantic_document = _document_by_code(
            semantic_index.get("documents"), code, "annual semantic index"
        )
        crop_document = _document_by_code(
            crop_manifest.get("documents"), code, "annual crop manifest"
        )
        scan_trial = _document_by_code(structure_scan.get("trials"), code, "annual structure scan")
        matcher = scan_trial.get("matcher_result")
        if scan_trial.get("document_ordinal") != ordinal or type(matcher) is not dict:
            raise _error("annual whole-PDF derivative scan identity drifted")
        page_number = reviewed["page_sequence"]
        if page_number is None:
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("regions") != []
                or reviewed["mappings"]
                or reviewed["equations"]
                or reviewed["whole_document_family_absence_claim"] is not True
            ):
                raise _error("annual bound-report derivative absence drifted")
            trials.append(
                {
                    "cluster_boundary": None,
                    "disposition": reviewed["disposition"],
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "evidence_page_sequence": None,
                    "fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count": 0,
                    "fresh_vietocr_numeric_disagreement_line_indices": [],
                    "layout": None,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": reviewed["source_period"],
                    "source_period_status": "VERIFIED_BOUND_ANNUAL_2025_REPORT",
                    "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "whole_document_family_absence_claim": True,
                    "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
                }
            )
            continue
        if (
            matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or not same_typed_json_v1(
                matcher.get("uniqueness"),
                {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"},
            )
            or type(matcher.get("regions")) is not list
            or len(matcher["regions"]) != 1
            or reviewed["whole_document_family_absence_claim"] is not False
        ):
            raise _error("annual whole-PDF derivative region is not exactly unique")
        region = matcher["regions"][0]
        if (
            region.get("page_sequence") != page_number
            or region.get("owner", {}).get("source_line_index")
            != reviewed["evidence_owner_line_index"]
            or region.get("layout", {}).get("presentation_mode") != reviewed["layout_mode"]
            or reviewed["source_period"] != "2025-12-31"
        ):
            raise _error("annual reviewed derivative page/layout/period disagrees with graph")
        axis_page = _page_by_number(axis_document, page_number, "annual fresh VietOCR axis")
        semantic_page = _page_by_number(semantic_document, page_number, "annual semantic index")
        crop_page = _page_by_number(crop_document, page_number, "annual crop manifest")
        owner = _axis_line(axis_page, reviewed["evidence_owner_line_index"])
        _anchor_match(owner["vietocr_text"], reviewed["owner_pixel_transcription"], "annual owner")
        try:
            source_texts = support._source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"annual derivative source line axis drifted: {exc}") from exc
        mapped_rows = []
        numeric_sources_by_line: dict[int, dict[str, Any]] = {}
        render_bytes: bytes | None = None
        seen_intersections: set[tuple[str, str, str]] = set()
        for row in reviewed["mappings"]:
            period = row["period_role"]
            role = row["role"]
            lane = row["lane_role"]
            intersection = (period, role, lane)
            if intersection in seen_intersections:
                raise _error("duplicate annual derivative period/role/lane mapping")
            seen_intersections.add(intersection)
            event = _event(region, period, role)
            if event.get("source_line_index") != row["label_line_index"]:
                raise _error("annual derivative graph/review label binding drifted")
            label_line = _axis_line(axis_page, row["label_line_index"])
            match_kind = _anchor_match(
                label_line["vietocr_text"], row["label_pixel_transcription"], role
            )
            if row["value_line_index"] is None:
                if any(item.get("lane_role") == lane for item in event.get("value_proposals", [])):
                    raise _error("annual derivative DASH overlaps a graph text value")
                if render_bytes is None:
                    render_bytes = _render_bytes(crop_page)
                source_value = _annual_geometry_dash_source_value(row, event, region, render_bytes)
            else:
                value_matches = [
                    item
                    for item in event.get("value_proposals", [])
                    if item.get("source_line_index") == row["value_line_index"]
                    and item.get("lane_role") == lane
                ]
                if len(value_matches) != 1 or row.get("pixel_binding") is not None:
                    raise _error("annual reviewed derivative value left its graph-bound lane")
                source_value = _source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    row["value_line_index"],
                    row["pixel_value"],
                )
            source_line_index = source_value.get("source_line_index")
            if type(source_line_index) is int:
                previous = numeric_sources_by_line.setdefault(source_line_index, source_value)
                if not same_typed_json_v1(previous, source_value):
                    raise _error(
                        "annual derivative numeric source line was transcribed inconsistently"
                    )
            schema = _schema_binding(
                schema_by_id.get(_schema_id(period, lane, role)), period, lane, role
            )
            mapped_rows.append(
                {
                    **schema,
                    "anchor_match_kind": match_kind,
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "lane_role": lane,
                    "normalized_anchor": normalize_vietnamese_anchor_v1(label_line["vietocr_text"]),
                    "normalized_value": source_value["normalized_value"],
                    "period_role": period,
                    "physical_page": page_number,
                    "role": role,
                    "source_value": source_value,
                    "status": "VERIFIED_BY_CODEX",
                    "topology": "UNIQUE_PERIOD_ROLE_ROW_BY_MEANINGFUL_COLUMN_INTERSECTION",
                    "vietocr_transformer_text": [label_line["vietocr_text"]],
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            components = [
                _source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    item["line_index"],
                    item["pixel_transcription"],
                )
                for item in equation["component_values"]
            ]
            total = _source_value(
                axis_page,
                semantic_page,
                crop_page,
                source_texts,
                equation["visible_total"]["line_index"],
                equation["visible_total"]["pixel_transcription"],
            )
            for source_value in [*components, total]:
                source_line_index = source_value["source_line_index"]
                previous = numeric_sources_by_line.setdefault(source_line_index, source_value)
                if not same_typed_json_v1(previous, source_value):
                    raise _error(
                        "annual derivative equation source line was transcribed inconsistently"
                    )
            if equation["operation"] == "SUM":
                computed = sum(item["normalized_value"] for item in components)
            elif equation["operation"] == "DIFFERENCE" and len(components) == 2:
                computed = components[0]["normalized_value"] - components[1]["normalized_value"]
            else:
                raise _error("annual derivative accounting operation drifted")
            if computed != total["normalized_value"]:
                raise _error(f"annual derivative accounting equation does not close: {code}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "operation": equation["operation"],
                    "physical_page": page_number,
                    "status": "CORROBORATED_EXACT",
                    "visible_total": total["normalized_value"],
                }
            )
        disagreement_lines = sorted(
            line_index
            for line_index, source_value in numeric_sources_by_line.items()
            if source_value["fresh_vietocr_numeric_proposal"] != source_value["pixel_transcription"]
        )
        trials.append(
            {
                "cluster_boundary": canonical_clone_v1(region["cluster_boundary"]),
                "disposition": reviewed["disposition"],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "evidence_page_sequence": page_number,
                "fresh_vietocr_numeric_disagreement_corrected_by_pixel_source_count": len(
                    disagreement_lines
                ),
                "fresh_vietocr_numeric_disagreement_line_indices": disagreement_lines,
                "layout": canonical_clone_v1(region["layout"]),
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": "VERIFIED_SOURCE_PERIOD_ANNUAL_2025",
                "status": "VERIFIED_BY_CODEX",
                "verified_accounting_equations": equations,
                "verified_mappings": mapped_rows,
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
                "whole_document_family_absence_claim": False,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": ANNUAL_2025_CLAIM_BOUNDARY,
        "format_version": ANNUAL_2025_FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": ANNUAL_2025_CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {
                "path": ANNUAL_2025_REVIEW_PATH.as_posix(),
                "sha256": review_sha256,
            },
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": ANNUAL_2025_EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": ANNUAL_2025_SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": ANNUAL_2025_EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
        },
        "metrics": _annual_2025_metrics(trials),
        "state": ("ANNUAL_2025_DERIVATIVE_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFICATION_COMPLETE"),
        "trials": trials,
    }
    return _validate_annual_2025_result(
        {
            **material,
            "result_id": "annual2025dfi8bcv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def validate_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    persisted = _validate_result(value)
    scanner.validate_derivative_financial_instruments_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    expected = build_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("derivative mapping does not replay exactly")
    return persisted


def build_live_derivative_financial_instruments_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crops, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    structure = scanner.build_derivative_financial_instruments_full_document_scan_v1(semantic)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
        semantic,
        crops,
        structure,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def build_live_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1() -> (
    dict[str, Any]
):
    semantic, _ = _stable_json(ANNUAL_2025_SEMANTIC_INDEX_PATH, ANNUAL_2025_EXPECTED_INDEX_SHA256)
    crops, crop_sha = _stable_json(
        ANNUAL_2025_CROP_MANIFEST_PATH, ANNUAL_2025_EXPECTED_CROP_MANIFEST_SHA256
    )
    review, review_sha = _stable_json(ANNUAL_2025_REVIEW_PATH)
    structure = scanner.build_derivative_financial_instruments_full_document_scan_v1(
        semantic, enable_multilevel_headers=True
    )
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
        semantic,
        crops,
        structure,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crops, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    structure = scanner.build_derivative_financial_instruments_full_document_scan_v1(semantic)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic,
        crops,
        structure,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    persisted = _validate_annual_2025_result(value)
    expected = (
        build_live_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1()
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("annual derivative mapping does not replay exactly")
    return expected


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annual-2025", action="store_true")
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.write_review:
        path = ANNUAL_2025_REVIEW_PATH if args.annual_2025 else REVIEW_PATH
        value = _annual_2025_review_blueprint() if args.annual_2025 else _review_blueprint()
        (PROJECT_ROOT / path).write_bytes(canonical_json_bytes_v1(value))
        return
    output = args.output or (ANNUAL_2025_RESULT_PATH if args.annual_2025 else RESULT_PATH)
    if args.validate:
        value = json.loads((PROJECT_ROOT / output).read_text(encoding="utf-8"))
        result = (
            validate_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_replay_v1(
                value
            )
            if args.annual_2025
            else validate_live_derivative_financial_instruments_8bank_codex_verified_mapping_v1(
                value
            )
        )
    else:
        result = (
            build_live_annual_2025_derivative_financial_instruments_8bank_codex_verified_mapping_v1()
            if args.annual_2025
            else build_live_derivative_financial_instruments_8bank_codex_verified_mapping_v1()
        )
        (PROJECT_ROOT / output).write_bytes(canonical_json_bytes_v1(result))
    print(result["result_id"])


if __name__ == "__main__":
    _main()
