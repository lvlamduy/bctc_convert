"""Verify and map the eight-bank cash/precious-metals note family.

The complete-PDF detector remains bank blind.  This bounded post-scan review
binds each unique detailed note to visible page/crop evidence, preserves the
first/last cluster boundary and PDF row order, selects only the current-period
money column, verifies cash plus gold to the visible total, and maps exact live
TM-schema rows.  A balance-sheet total or a cash-flow/risk disclosure is not
silently promoted to a detailed note cluster.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import struct
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
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
    "CashPreciousMetals8BankCodexVerifiedMappingV1Error",
    "build_cash_precious_metals_8bank_codex_verified_mapping_v1",
    "build_live_annual_2025_cash_precious_metals_8bank_codex_verified_mapping_v1",
    "build_live_cash_precious_metals_8bank_codex_verified_mapping_v1",
    "validate_live_annual_2025_cash_precious_metals_8bank_codex_verified_mapping_v1",
    "validate_live_cash_precious_metals_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_cash_precious_metals_8bank_codex_verified_mapping_replay_v1",
    "validate_cash_precious_metals_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_experiment_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_experiment_module(
    "trading_securities_verified_mapping_support_for_cash_precious_metals",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_experiment_module(
    "cash_precious_metals_full_document_scan_for_verified_mapping",
    "scan_cash_precious_metals_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CASH_PRECIOUS_METALS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CASH_PRECIOUS_METALS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_CASH_PRECIOUS_"
    "METALS_FIRST_LAST_CLUSTER_BOUNDARY_PERIOD_UNIT_STRUCTURE_PLUS_INDEPENDENT_"
    "VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_AND_LIVE_TM_SCHEMA_"
    "ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0060-cash-precious-metals-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0060-cash-precious-metals-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "cpmfdsv1:scan:e567cec37d01547ba51687388ae9a52578cd1075634d22f425eb8b76c5dcce31"

ANNUAL_2025_FORMAT_VERSION = "ANNUAL_2025_CASH_PRECIOUS_METALS_8BANK_CODEX_VERIFIED_MAPPING_V1"
ANNUAL_2025_REVIEW_FORMAT = "ANNUAL_2025_CASH_PRECIOUS_METALS_8BANK_CODEX_PIXEL_REVIEW_V1"
ANNUAL_2025_CLAIM_BOUNDARY = (
    "FIXED_EIGHT_AUDITED_CONSOLIDATED_ANNUAL_2025_COMPLETE_PDF_FRESH_VIETOCR_"
    "GENERIC_CASH_PRECIOUS_METALS_FIRST_LAST_CLUSTER_BOUNDARY_ADAPTIVE_PERIOD_"
    "UNIT_HEADER_GEOMETRY_VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_EXACT_"
    "ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
ANNUAL_2025_REVIEW_PATH = Path(
    "docs/experiments/E-0107-annual-2025-cash-precious-metals-8bank-codex-pixel-review-v1.json"
)
ANNUAL_2025_RESULT_PATH = Path(
    "docs/experiments/E-0107-annual-2025-cash-precious-metals-8bank-codex-verified-mapping-v1.json"
)
ANNUAL_2025_SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/semantic_index.json"
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
    "cpmfdsv1:scan:68dc2df9c71dbcc30712f8baaa66804403c1346de6e86f9e608ecdfc1c7c03c1"
)

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "DETAILED_NOTE_NOT_BALANCE_SHEET_CASHFLOW_OR_RISK_SURFACE",
    "FIRST_OWNER_AND_LAST_TOTAL_IN_PDF_ORDER",
    "PARENT_PRECEDES_REQUIRED_CHILDREN",
    "CURRENT_PERIOD_MONETARY_AXIS_ONLY",
    "PERIOD_AND_UNIT_AXES_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_AND_SIGN",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "VND_FOREIGN_AND_GOLD_TO_VISIBLE_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "balance_sheet_cashflow_or_risk_surface_promoted_to_detailed_note": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": ("VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER_AND_ACCOUNTING"),
    "old_ocr_used_as_semantic_anchor": False,
    "source_order_and_cluster_boundaries_required": True,
    "unlabeled_total_requires_topology_and_accounting": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_cash_precious_metals_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_mapping": False,
    "unlabeled_total_requires_topology_and_exact_equation": True,
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
_MAPPING_SCHEMA = {
    "CASH_VND": 562,
    "CASH_FOREIGN": 563,
    "FOREIGN_CURRENCY_VALUABLE_DOCUMENT": 564,
    "MONETARY_GOLD": 565,
    "NONMONETARY_GOLD": 566,
    "OTHER_PRECIOUS_METALS_GEMS": 567,
    "OTHER": 568,
    "TOTAL": 561,
}


class CashPreciousMetals8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel ledger, accounting, or live schema drifted."""


def _error(message: str) -> CashPreciousMetals8BankCodexVerifiedMappingV1Error:
    return CashPreciousMetals8BankCodexVerifiedMappingV1Error(message)


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


def _value(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": pixel_transcription}


def _challenged_value(
    line_index: int,
    pixel_transcription: str,
    fresh_vietocr_challenger_expected: str,
) -> dict[str, Any]:
    return {
        "fresh_vietocr_challenger_expected": fresh_vietocr_challenger_expected,
        "line_index": line_index,
        "pixel_transcription": pixel_transcription,
        "resolution": (
            "INDEPENDENT_PIXEL_TRANSCRIPTION_CORROBORATED_BY_PROVIDER_AND_EXACT_ACCOUNTING_EQUATION"
        ),
        "source_numeric_challenger_expected": pixel_transcription,
    }


def _render_dash_value(
    *,
    bbox: Sequence[int],
    lane_reference_line_index: int,
    raw_rgb_sha256: str,
    row_label_line_index: int,
) -> dict[str, Any]:
    return {
        "line_index": None,
        "pixel_transcription": "-",
        "render_cell": {
            "bbox": list(bbox),
            "lane_reference_line_index": lane_reference_line_index,
            "raw_rgb_sha256": raw_rgb_sha256,
            "row_label_line_index": row_label_line_index,
            "status": "VISIBLE_DASH_WITHOUT_PROVIDER_DETECTION_BOUND_BY_ROW_AND_NUMERIC_LANE",
        },
    }


def _mapping(
    role: str,
    label_line_index: int | None,
    label_pixel_transcription: str | None,
    value_line_index: int,
    pixel_value: str,
    topology: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": _MAPPING_SCHEMA[role],
        "role": role,
        "topology": topology,
        "value": _value(value_line_index, pixel_value),
    }


def _mapping_evidence(
    role: str,
    label_line_index: int | None,
    label_pixel_transcription: str | None,
    value: Mapping[str, Any],
    topology: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": _MAPPING_SCHEMA[role],
        "role": role,
        "topology": topology,
        "value": canonical_clone_v1(value),
    }


def _positive_document(
    bank_code: str,
    page_sequence: int,
    source_period: str,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[tuple[str, int | None, str | None, int, str, str]],
    *,
    equation_name: str = "CASH_VND_PLUS_FOREIGN_PLUS_MONETARY_GOLD_TO_TOTAL",
) -> dict[str, Any]:
    mappings = [_mapping(*row) for row in rows]
    components = [row["value"] for row in mappings if row["role"] != "TOTAL"]
    total = next(row["value"] for row in mappings if row["role"] == "TOTAL")
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_DETAILED_CASH_PRECIOUS_METALS_NOTE",
        "equations": [
            {
                "component_values": components,
                "name": equation_name,
                "visible_total": total,
            }
        ],
        "evidence_owner_line_index": owner_line_index,
        "mappings": mappings,
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": source_period,
    }


def _negative_document(
    bank_code: str,
    evidence_page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
) -> dict[str, Any]:
    checks = {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS}
    checks["COMPLETE_PDF_UNIQUE_REGION_ENUMERATION"] = "PASS_NO_COMPLETE_REGION"
    checks["DETAILED_NOTE_NOT_BALANCE_SHEET_CASHFLOW_OR_RISK_SURFACE"] = "PASS"
    return {
        "bank_code": bank_code,
        "checks": checks,
        "disposition": "UNRESOLVED_NO_COMPLETE_DETAILED_NOTE_CLUSTER_IN_BOUND_PDF",
        "equations": [],
        "evidence_owner_line_index": owner_line_index,
        "mappings": [],
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": evidence_page_sequence,
        "source_period": "2026-06-30",
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _negative_document("ACB", 3, 13, "Tiền mặt, vàng bạc, đá quý"),
        _positive_document(
            "MBB",
            30,
            "2026-06-30",
            3,
            "Tiền mặt, vàng bạc, đá quý",
            [
                ("CASH_VND", 8, "Tiền mặt bằng VND", 9, "4.534.511", "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    11,
                    "Tiền mặt bằng ngoại tệ",
                    12,
                    "500.036",
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 14, "Vàng tiền tệ", 15, "16.697", "OWNER_CHILD"),
                ("TOTAL", None, None, 17, "5.051.244", "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _positive_document(
            "VPB",
            38,
            "2026-03-31",
            5,
            "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
            [
                ("CASH_VND", 12, "Tiền mặt bằng VND", 13, "2.970.048", "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    15,
                    "Tiền mặt bằng ngoại tệ",
                    16,
                    "1.094.895",
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 18, "Vàng tiền tệ", 19, "209", "OWNER_CHILD"),
                ("TOTAL", None, None, 21, "4.065.152", "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _negative_document("HDB", 3, 17, "Tiền mặt, vàng"),
        _negative_document("VCB", 7, 18, "Tiền mặt, vàng bạc, đá quý"),
        _negative_document("CTG", 3, 20, "Tiền mặt, vàng bạc, đá quý"),
        _negative_document("BID", 4, 17, "Tiền mặt, vàng bạc, đá quý"),
        _positive_document(
            "VIB",
            31,
            "2026-06-30",
            5,
            "TIỀN MẶT, VÀNG",
            [
                ("CASH_VND", 10, "Tiền mặt bằng VND", 11, "1.447.227", "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    13,
                    "Tiền mặt bằng ngoại tệ",
                    14,
                    "934.758",
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 16, "Vàng", 17, "94", "OWNER_CHILD"),
                ("TOTAL", None, None, 19, "2.382.079", "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
    ]


def _annual_2025_positive_document(
    bank_code: str,
    page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[tuple[str, int | None, str | None, Mapping[str, Any], str]],
) -> dict[str, Any]:
    mappings = [_mapping_evidence(*row) for row in rows]
    components = [row["value"] for row in mappings if row["role"] != "TOTAL"]
    total = next(row["value"] for row in mappings if row["role"] == "TOTAL")
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_DETAILED_CASH_PRECIOUS_METALS_NOTE",
        "equations": [
            {
                "component_values": components,
                "name": "ALL_VISIBLE_CURRENT_PERIOD_CHILDREN_TO_VISIBLE_TOTAL",
                "visible_total": total,
            }
        ],
        "evidence_owner_line_index": owner_line_index,
        "mappings": mappings,
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": "2025-12-31",
    }


def _annual_2025_review_documents() -> list[dict[str, Any]]:
    direct = _value
    return [
        _annual_2025_positive_document(
            "ACB",
            45,
            5,
            "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
            [
                (
                    "CASH_VND",
                    10,
                    "Tiền mặt bằng Đồng Việt Nam",
                    direct(11, "6.834.569"),
                    "OWNER_CHILD",
                ),
                (
                    "CASH_FOREIGN",
                    13,
                    "Tiền mặt bằng ngoại tệ",
                    direct(14, "1.778.776"),
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 16, "Vàng", direct(17, "11.203"), "OWNER_CHILD"),
                ("TOTAL", None, None, direct(19, "8.624.548"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "MBB",
            46,
            10,
            "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
            [
                ("CASH_VND", 15, "Tiền mặt bằng VND", direct(16, "4.543.336"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    18,
                    "Tiền mặt bằng ngoại tệ",
                    direct(19, "413.281"),
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 21, "Vàng tiền tệ", direct(22, "9.169"), "OWNER_CHILD"),
                ("TOTAL", None, None, direct(24, "4.965.786"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "VPB",
            41,
            5,
            "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
            [
                ("CASH_VND", 12, "Tiền mặt bằng VND", direct(13, "2.292.077"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    15,
                    "Tiền mặt bằng ngoại tệ",
                    direct(16, "481.921"),
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 18, "Vàng tiền tệ", direct(19, "184"), "OWNER_CHILD"),
                ("TOTAL", None, None, direct(21, "2.774.182"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "HDB",
            33,
            33,
            "TIỀN MẶT, VÀNG",
            [
                ("CASH_VND", 38, "Tiền mặt bằng VND", direct(39, "2.912.247"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    41,
                    "Tiền mặt bằng ngoại tệ",
                    _challenged_value(42, "1.194.085", "1.194.005"),
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 44, "Vàng tiền tệ", direct(45, "20.311"), "OWNER_CHILD"),
                ("TOTAL", None, None, direct(47, "4.126.643"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "VCB",
            35,
            9,
            "Tiền mặt, vàng bạc, đá quý",
            [
                ("CASH_VND", 15, "Tiền mặt bằng VND", direct(16, "12.274.515"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    18,
                    "Tiền mặt bằng ngoại tệ",
                    direct(19, "3.267.710"),
                    "OWNER_CHILD",
                ),
                (
                    "FOREIGN_CURRENCY_VALUABLE_DOCUMENT",
                    21,
                    "Chứng từ có giá bằng ngoại tệ",
                    direct(22, "544"),
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 24, "Vàng tiền tệ", direct(26, "-"), "OWNER_CHILD"),
                ("TOTAL", None, None, direct(27, "15.542.769"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "CTG",
            39,
            31,
            "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
            [
                ("CASH_VND", 36, "Tiền mặt bằng VND", direct(37, "11.206.287"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    39,
                    "Tiền mặt bằng ngoại tệ",
                    direct(40, "1.349.621"),
                    "OWNER_CHILD",
                ),
                ("MONETARY_GOLD", 42, "Vàng tiền tệ", direct(43, "12.488"), "OWNER_CHILD"),
                (
                    "NONMONETARY_GOLD",
                    45,
                    "Vàng phi tiền tệ",
                    _render_dash_value(
                        bbox=(1258, 1413, 1292, 1447),
                        lane_reference_line_index=43,
                        raw_rgb_sha256=(
                            "27be220cce5b7a5a97a48b48d322f3e032c8883258e4379a617e7fb8ac2a74be"
                        ),
                        row_label_line_index=45,
                    ),
                    "OWNER_CHILD_MISSING_PROVIDER_CELL_RECONSTRUCTED_FROM_ROW_X_LANE",
                ),
                (
                    "OTHER_PRECIOUS_METALS_GEMS",
                    47,
                    "Kim loại quý, đá quý khác",
                    direct(48, "15.088"),
                    "OWNER_CHILD",
                ),
                ("TOTAL", None, None, direct(50, "12.583.484"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "BID",
            39,
            4,
            "TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
            [
                ("CASH_VND", 9, "Tiền mặt bằng VND", direct(10, "9.973.994"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    12,
                    "Tiền mặt bằng ngoại tệ",
                    direct(13, "3.046.310"),
                    "OWNER_CHILD",
                ),
                (
                    "FOREIGN_CURRENCY_VALUABLE_DOCUMENT",
                    15,
                    "Chứng từ có giá trị ngoại tệ",
                    direct(16, "54.762"),
                    "OWNER_CHILD",
                ),
                ("TOTAL", None, None, direct(18, "13.075.066"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
        _annual_2025_positive_document(
            "VIB",
            35,
            5,
            "TIỀN MẶT, VÀNG",
            [
                ("CASH_VND", 10, "Tiền mặt bằng VND", direct(11, "1.592.688"), "OWNER_CHILD"),
                (
                    "CASH_FOREIGN",
                    13,
                    "Tiền mặt bằng ngoại tệ",
                    direct(14, "1.959.792"),
                    "OWNER_CHILD",
                ),
                (
                    "MONETARY_GOLD",
                    18,
                    "Vàng",
                    direct(16, "94"),
                    "PIXEL_ROW_VALUE_PRECEDES_LABEL_IN_PROVIDER_READING_ORDER",
                ),
                ("TOTAL", None, None, direct(19, "3.552.574"), "UNLABELED_TRAILING_TOTAL"),
            ],
        ),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0060",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0060:pixel-review:" + canonical_json_sha256_v1(material)}


def _annual_2025_review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": ANNUAL_2025_CLAIM_BOUNDARY,
        "documents": _annual_2025_review_documents(),
        "format_version": ANNUAL_2025_REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0107-ANNUAL-2025",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
        "semantic_axis_sha256": ANNUAL_2025_EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": ANNUAL_2025_EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0107:pixel-review:" + canonical_json_sha256_v1(material)}


def _profile(name: str) -> dict[str, Any]:
    if name == "wave1-2026":
        return {
            "axis_sha256": EXPECTED_AXIS_SHA256,
            "claim_boundary": CLAIM_BOUNDARY,
            "crop_manifest_path": CROP_MANIFEST_PATH,
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "format_version": FORMAT_VERSION,
            "index_path": SEMANTIC_INDEX_PATH,
            "index_sha256": EXPECTED_INDEX_SHA256,
            "result_id_prefix": "cpm8bcv1:result:",
            "result_path": RESULT_PATH,
            "review_blueprint": _review_blueprint,
            "review_path": REVIEW_PATH,
            "scan_id": EXPECTED_SCAN_ID,
            "state": "CASH_PRECIOUS_METALS_8BANK_CODEX_VERIFICATION_COMPLETE",
        }
    if name == "annual-2025":
        return {
            "axis_sha256": ANNUAL_2025_EXPECTED_AXIS_SHA256,
            "claim_boundary": ANNUAL_2025_CLAIM_BOUNDARY,
            "crop_manifest_path": ANNUAL_2025_CROP_MANIFEST_PATH,
            "crop_manifest_sha256": ANNUAL_2025_EXPECTED_CROP_MANIFEST_SHA256,
            "format_version": ANNUAL_2025_FORMAT_VERSION,
            "index_path": ANNUAL_2025_SEMANTIC_INDEX_PATH,
            "index_sha256": ANNUAL_2025_EXPECTED_INDEX_SHA256,
            "result_id_prefix": "annual2025cpm8bcv1:result:",
            "result_path": ANNUAL_2025_RESULT_PATH,
            "review_blueprint": _annual_2025_review_blueprint,
            "review_path": ANNUAL_2025_REVIEW_PATH,
            "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
            "state": "ANNUAL_2025_CASH_PRECIOUS_METALS_8BANK_CODEX_VERIFICATION_COMPLETE",
        }
    raise _error("cash/precious-metals mapping profile is unsupported")


def _review(value: Any, profile_name: str = "wave1-2026") -> dict[str, Any]:
    expected = _profile(profile_name)["review_blueprint"]()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex cash/precious-metals pixel review differs from the fixed ledger")
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
    if (
        type(line) is not dict
        or line.get("source_line_index") != line_index
        or type(line.get("vietocr_text")) is not str
    ):
        raise _error("fresh VietOCR semantic line identity drifted")
    return line


def _source_line_axis(page: Mapping[str, Any]) -> list[str]:
    """Read the exact provider text axis used only as a numeric challenger."""

    result = support._strict_json(
        support._artifact_bytes(page.get("result_ref"), "page result"),
        "page result",
    )
    provider_texts = result.get("rec_texts")
    if provider_texts is not None:
        if (
            page.get("route") != "DOMINANT_RASTER_OCR"
            or page.get("geometry_mode") != "PPOCRV6_BATCH_PROVIDER_LINE_GEOMETRY_V1"
            or page.get("supplement_line_count") != 0
            or type(page.get("primary_line_count")) is not int
            or type(provider_texts) is not list
            or len(provider_texts) != page["primary_line_count"]
            or not all(type(text) is str for text in provider_texts)
        ):
            raise _error("raw provider source line axis drifted")
        return list(provider_texts)
    try:
        return support._source_line_axis(page)
    except Exception as exc:
        raise _error(f"page result source line axis drifted: {exc}") from exc


def _schema_binding(item: Any, role: str) -> dict[str, Any]:
    schema_id = _MAPPING_SCHEMA.get(role)
    expected_parent = 560 if role == "TOTAL" else 561
    if (
        item is None
        or schema_id is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.parent_id != expected_parent
    ):
        raise _error("reviewed mapping does not bind one exact live cash TM item")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _region_event(region: Mapping[str, Any], role: str) -> dict[str, Any]:
    events = region.get("events")
    if type(events) is not list:
        raise _error("cash/precious-metals graph event axis drifted")
    matches = [event for event in events if type(event) is dict and event.get("role") == role]
    if len(matches) != 1:
        raise _error(f"cash/precious-metals graph does not contain one exact role {role}")
    return matches[0]


def _source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is dict and set(value) == {
        "line_index",
        "pixel_transcription",
        "render_cell",
    }:
        return _render_cell_value(axis_page, crop_page, value)
    if type(value) is dict and set(value) == {
        "fresh_vietocr_challenger_expected",
        "line_index",
        "pixel_transcription",
        "resolution",
        "source_numeric_challenger_expected",
    }:
        return _challenged_source_value(
            axis_page,
            semantic_page,
            crop_page,
            source_texts,
            value,
        )
    try:
        return support._source_value(axis_page, semantic_page, crop_page, source_texts, value)
    except Exception as exc:
        raise _error(f"cash/precious-metals source numeric evidence drifted: {exc}") from exc


def _challenged_source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        value["resolution"]
        != "INDEPENDENT_PIXEL_TRANSCRIPTION_CORROBORATED_BY_PROVIDER_AND_EXACT_ACCOUNTING_EQUATION"
        or type(value["line_index"]) is not int
        or type(value["fresh_vietocr_challenger_expected"]) is not str
        or type(value["source_numeric_challenger_expected"]) is not str
    ):
        raise _error("challenged numeric review fields drifted")
    line_index = value["line_index"]
    pixel_value = support._money(value["pixel_transcription"])
    axis = _axis_line(axis_page, line_index)
    semantic_lines = semantic_page.get("lines")
    if type(semantic_lines) is not list or not 0 <= line_index < len(semantic_lines):
        raise _error("challenged semantic-index crop line axis drifted")
    semantic_line = semantic_lines[line_index]
    if (
        type(semantic_line) is not dict
        or semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis["vietocr_text"]
        or type(semantic_line.get("crop_ref")) is not dict
        or type(semantic_line.get("sample_id")) is not str
        or not 0 <= line_index < len(source_texts)
    ):
        raise _error("challenged semantic-index crop/source binding drifted")
    source_raw = source_texts[line_index]
    if source_raw != value["source_numeric_challenger_expected"]:
        raise _error("challenged source numeric transcription drifted")
    source_value = support._money(source_raw)
    if source_value != pixel_value:
        raise _error("challenged provider numeric transcription disagrees with visible pixels")
    if axis["vietocr_text"] != value["fresh_vietocr_challenger_expected"]:
        raise _error("challenged fresh VietOCR transcription drifted")
    if support._money(axis["vietocr_text"]) == pixel_value:
        raise _error("challenged fresh VietOCR unexpectedly agrees with visible pixels")
    crop_ref = semantic_line["crop_ref"]
    crop_payload = support._stable_bytes(Path(crop_ref["path"]))
    if (
        type(crop_ref.get("sha256")) is not str
        or type(crop_ref.get("size_bytes")) is not int
        or len(crop_payload) != crop_ref["size_bytes"]
        or hashlib.sha256(crop_payload).hexdigest() != crop_ref["sha256"]
    ):
        raise _error("challenged crop bytes drifted")
    sample_first = crop_page.get("sample_offset_start")
    sample_stop = crop_page.get("sample_offset_stop")
    expected_sample_ordinal = sample_first + line_index + 1 if type(sample_first) is int else None
    if (
        type(sample_first) is not int
        or type(sample_stop) is not int
        or expected_sample_ordinal is None
        or not sample_first <= expected_sample_ordinal - 1 < sample_stop
        or semantic_line["sample_id"] != f"sample-{expected_sample_ordinal:08d}"
    ):
        raise _error("challenged crop sample ordinal drifted")
    return {
        "crop_ref": canonical_clone_v1(crop_ref),
        "fresh_vietocr_numeric_proposal": axis["vietocr_text"],
        "normalized_value": pixel_value,
        "pixel_transcription": value["pixel_transcription"],
        "resolution": value["resolution"],
        "source_line_index": line_index,
        "source_numeric_challenger": source_raw,
        "source_numeric_challenger_normalized_value": source_value,
        "source_numeric_challenger_status": "MATCHED_INDEPENDENT_PIXEL_TRANSCRIPTION",
        "vietocr_numeric_challenger_status": "DISAGREES_WITH_INDEPENDENT_PIXEL_TRANSCRIPTION",
    }


def _render_cell_value(
    axis_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    cell = value["render_cell"]
    if (
        value["line_index"] is not None
        or value["pixel_transcription"] != "-"
        or type(cell) is not dict
        or set(cell)
        != {
            "bbox",
            "lane_reference_line_index",
            "raw_rgb_sha256",
            "row_label_line_index",
            "status",
        }
        or cell["status"] != "VISIBLE_DASH_WITHOUT_PROVIDER_DETECTION_BOUND_BY_ROW_AND_NUMERIC_LANE"
        or type(cell["bbox"]) is not list
        or len(cell["bbox"]) != 4
        or any(type(coordinate) is not int for coordinate in cell["bbox"])
    ):
        raise _error("render-derived dash evidence fields drifted")
    left, top, right, bottom = cell["bbox"]
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise _error("render-derived dash bbox drifted")
    label = _axis_line(axis_page, cell["row_label_line_index"])
    lane = _axis_line(axis_page, cell["lane_reference_line_index"])
    label_bbox = label.get("bbox")
    lane_bbox = lane.get("bbox")
    if (
        type(label_bbox) is not list
        or len(label_bbox) != 4
        or type(lane_bbox) is not list
        or len(lane_bbox) != 4
        or not label_bbox[1] <= (top + bottom) / 2 <= label_bbox[3]
        or abs(right - lane_bbox[2]) > max(20, (lane_bbox[2] - lane_bbox[0]) // 4)
    ):
        raise _error("render-derived dash row/lane binding drifted")
    render_ref = crop_page.get("render_binding")
    if (
        type(render_ref) is not dict
        or set(render_ref) != {"path", "sha256", "size_bytes"}
        or type(render_ref["path"]) is not str
        or type(render_ref["size_bytes"]) is not int
    ):
        raise _error("render-derived dash page render binding drifted")
    render_payload = support._stable_bytes(Path(render_ref["path"]))
    if (
        len(render_payload) != render_ref["size_bytes"]
        or hashlib.sha256(render_payload).hexdigest() != render_ref["sha256"]
    ):
        raise _error("render-derived dash page render bytes drifted")
    try:
        image = Image.open(io.BytesIO(render_payload))
        image.load()
    except Exception as exc:
        raise _error("render-derived dash page render is not a decodable image") from exc
    if image.mode != "RGB" or right > image.width or bottom > image.height:
        raise _error("render-derived dash render mode/dimensions drifted")
    crop = image.crop((left, top, right, bottom))
    raw_material = struct.pack(">II", crop.width, crop.height) + crop.tobytes()
    if hashlib.sha256(raw_material).hexdigest() != _sha256(
        cell["raw_rgb_sha256"], "render-derived dash raw RGB"
    ):
        raise _error("render-derived dash pixels drifted")
    gray = crop.convert("L")
    dark = [
        (x, y) for y in range(gray.height) for x in range(gray.width) if gray.getpixel((x, y)) < 180
    ]
    if not dark:
        raise _error("render-derived dash crop contains no visible ink")
    ink_width = max(x for x, _y in dark) - min(x for x, _y in dark) + 1
    ink_height = max(y for _x, y in dark) - min(y for _x, y in dark) + 1
    if ink_width <= ink_height or len(dark) > 100:
        raise _error("render-derived dash crop is not one bounded horizontal glyph")
    return {
        "normalized_value": 0,
        "pixel_transcription": "-",
        "render_cell": canonical_clone_v1(cell),
        "render_ref": canonical_clone_v1(render_ref),
        "source": "VISIBLE_RENDER_DASH_WITHOUT_PROVIDER_DETECTION",
        "source_numeric_challenger_status": "PROVIDER_OMITTED_VISIBLE_DASH_CELL",
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial.get("source_period_status") == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }


def _validate_result(value: Any, profile_name: str = "wave1-2026") -> dict[str, Any]:
    profile = _profile(profile_name)
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("cash/precious-metals mapping result fields drifted")
    if (
        value["format_version"] != profile["format_version"]
        or value["claim_boundary"] != profile["claim_boundary"]
        or value["state"] != profile["state"]
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("cash/precious-metals mapping result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "UNRESOLVED",
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT",
            }
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("verified_accounting_equations")) is not list
        ):
            raise _error("cash/precious-metals mapping trial shape drifted")
        for mapping in trial["verified_mappings"]:
            if type(mapping) is not dict or mapping.get("status") != "VERIFIED_BY_CODEX":
                raise _error("cash/precious-metals mapping row status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != profile["result_id_prefix"] + canonical_json_sha256_v1(material):
        raise _error("cash/precious-metals mapping result identity drifted")
    return canonical_clone_v1(value)


def build_cash_precious_metals_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
    _profile_name: str = "wave1-2026",
) -> dict[str, Any]:
    """Build the exact eight-bank bounded cash/precious-metals mapping result."""

    profile = _profile(_profile_name)
    review = _review(review_value, _profile_name)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != profile["axis_sha256"]
        or structure_scan.get("scan_id") != profile["scan_id"]
        or structure_scan.get("state")
        != "FULL_DOCUMENT_CASH_PRECIOUS_METALS_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("cash/precious-metals input authority drifted")
    _sha256(crop_manifest_sha256, "crop manifest")
    _sha256(review_sha256, "pixel review")
    trials: list[dict[str, Any]] = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document_by_code(review["documents"], code, "pixel review")
        semantic_document = _document_by_code(
            semantic_index.get("documents"), code, "semantic index"
        )
        axis_document = _document_by_code(axis["documents"], code, "fresh VietOCR axis")
        crop_document = _document_by_code(crop_manifest.get("documents"), code, "crop manifest")
        scan_trial = _document_by_code(structure_scan.get("trials"), code, "structure scan")
        matcher = scan_trial.get("matcher_result")
        if scan_trial.get("document_ordinal") != ordinal or type(matcher) is not dict:
            raise _error("whole-PDF cash/precious-metals scan identity drifted")
        page_number = reviewed["page_sequence"]
        axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
        owner_line = _axis_line(axis_page, reviewed["evidence_owner_line_index"])
        if normalize_vietnamese_anchor_v1(
            owner_line["vietocr_text"]
        ) != normalize_vietnamese_anchor_v1(reviewed["owner_pixel_transcription"]):
            raise _error("visible owner and fresh VietOCR owner disagree beyond accents")
        if not reviewed["mappings"]:
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("regions") != []
                or reviewed["equations"]
            ):
                raise _error("negative cash/precious-metals disposition drifted")
            trials.append(
                {
                    "cluster_boundary": None,
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "disposition": reviewed["disposition"],
                    "evidence_page_sequence": page_number,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": reviewed["source_period"],
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
            raise _error("whole-PDF cash/precious-metals region is not exactly unique")
        region = matcher["regions"][0]
        meaningful_axes = region.get("layout", {}).get("meaningful_axes", {})
        if (
            region.get("page_sequence") != page_number
            or meaningful_axes.get("unit_header_count", 0) < 1
            or meaningful_axes.get("period_header_count", 0) < 2
            or region.get("owner", {}).get("source_line_index")
            != reviewed["evidence_owner_line_index"]
        ):
            raise _error("reviewed page/layout disagrees with generic cash graph")
        semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
        crop_page = _page_by_number(crop_document, page_number, "crop manifest")
        try:
            source_texts = _source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"cash/precious-metals source line axis drifted: {exc}") from exc
        mapped_rows = []
        for row in reviewed["mappings"]:
            role = row["role"]
            event = _region_event(region, role)
            label_index = row["label_line_index"]
            if role == "TOTAL":
                if label_index is not None or row["label_pixel_transcription"] is not None:
                    raise _error("unlabeled total acquired a fabricated label")
            else:
                if type(label_index) is not int or event.get("source_line_index") != label_index:
                    raise _error("cash/precious-metals graph/review label binding drifted")
                transformer_text = _axis_line(axis_page, label_index)["vietocr_text"]
                if normalize_vietnamese_anchor_v1(
                    transformer_text
                ) != normalize_vietnamese_anchor_v1(row["label_pixel_transcription"]):
                    raise _error("visible label and fresh VietOCR label disagree beyond accents")
            value_index = row["value"]["line_index"]
            is_render_cell = "render_cell" in row["value"]
            if not is_render_cell and value_index not in {
                item["source_line_index"] for item in event.get("value_proposals", [])
            }:
                raise _error("reviewed value is outside the graph-bound row")
            source_value = _source_value(
                axis_page, semantic_page, crop_page, source_texts, row["value"]
            )
            schema = _schema_binding(schema_by_id.get(row["report_norm_id"]), role)
            mapped_rows.append(
                {
                    **schema,
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "normalized_anchor": (
                        normalize_vietnamese_anchor_v1(
                            _axis_line(axis_page, label_index)["vietocr_text"]
                        )
                        if label_index is not None
                        else None
                    ),
                    "normalized_value": source_value["normalized_value"],
                    "physical_page": page_number,
                    "role": role,
                    "source_value": source_value,
                    "status": "VERIFIED_BY_CODEX",
                    "topology": row["topology"],
                    "vietocr_transformer_text": (
                        [_axis_line(axis_page, label_index)["vietocr_text"]]
                        if label_index is not None
                        else []
                    ),
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            components = [
                _source_value(axis_page, semantic_page, crop_page, source_texts, item)
                for item in equation["component_values"]
            ]
            total = _source_value(
                axis_page, semantic_page, crop_page, source_texts, equation["visible_total"]
            )
            computed = sum(item["normalized_value"] for item in components)
            if computed != total["normalized_value"]:
                raise _error(f"cash/precious-metals accounting equation does not close: {code}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "physical_page": page_number,
                    "status": "CORROBORATED_EXACT",
                    "visible_total": total["normalized_value"],
                }
            )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_ANNUAL_2025"
            if _profile_name == "annual-2025"
            else "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "cluster_boundary": canonical_clone_v1(region["cluster_boundary"]),
                "document_ordinal": ordinal,
                "document_provenance": code,
                "disposition": reviewed["disposition"],
                "evidence_page_sequence": page_number,
                "layout": canonical_clone_v1(region["layout"]),
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                    if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
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
        "claim_boundary": profile["claim_boundary"],
        "format_version": profile["format_version"],
        "input_refs": {
            "crop_manifest": {
                "path": profile["crop_manifest_path"].as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {
                "path": profile["review_path"].as_posix(),
                "sha256": review_sha256,
            },
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": profile["axis_sha256"],
            "semantic_index": {
                "path": profile["index_path"].as_posix(),
                "sha256": profile["index_sha256"],
            },
            "structure_scan_id": profile["scan_id"],
        },
        "metrics": _metrics(trials),
        "state": profile["state"],
        "trials": trials,
    }
    return _validate_result(
        {
            **material,
            "result_id": profile["result_id_prefix"] + canonical_json_sha256_v1(material),
        },
        _profile_name,
    )


def validate_cash_precious_metals_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
    _profile_name: str = "wave1-2026",
) -> dict[str, Any]:
    """Exact-rebuild structure, numeric, accounting and schema decisions."""

    persisted = _validate_result(value, _profile_name)
    structure_scan = scanner.build_cash_precious_metals_full_document_scan_v1(semantic_index)
    expected = build_cash_precious_metals_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
        _profile_name=_profile_name,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("cash/precious-metals mapping does not replay exactly")
    return persisted


def validate_annual_2025_cash_precious_metals_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Exact-rebuild the annual-2025 eight-bank result."""

    return validate_cash_precious_metals_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
        _profile_name="annual-2025",
    )


def _build_live(profile_name: str) -> dict[str, Any]:
    profile = _profile(profile_name)

    semantic_index, index_sha = _stable_json(profile["index_path"], profile["index_sha256"])
    crop_manifest, crop_sha = _stable_json(
        profile["crop_manifest_path"], profile["crop_manifest_sha256"]
    )
    review, review_sha = _stable_json(profile["review_path"])
    if index_sha != profile["index_sha256"]:
        raise _error("semantic index digest drifted")
    structure_scan = scanner.build_cash_precious_metals_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_cash_precious_metals_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        _profile_name=profile_name,
    )
    return validate_cash_precious_metals_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        _profile_name=profile_name,
    )


def build_live_cash_precious_metals_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Read the fixed wave-1 inputs and build the verified result."""

    return _build_live("wave1-2026")


def build_live_annual_2025_cash_precious_metals_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Read the fixed annual-2025 inputs and build the verified result."""

    return _build_live("annual-2025")


def _validate_live(value: Any, profile_name: str) -> dict[str, Any]:
    profile = _profile(profile_name)

    semantic_index, _ = _stable_json(profile["index_path"], profile["index_sha256"])
    crop_manifest, crop_sha = _stable_json(
        profile["crop_manifest_path"], profile["crop_manifest_sha256"]
    )
    review, review_sha = _stable_json(profile["review_path"])
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_cash_precious_metals_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        _profile_name=profile_name,
    )


def validate_live_cash_precious_metals_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    """Replay one wave-1 result only from the fixed live trust roots."""

    return _validate_live(value, "wave1-2026")


def validate_live_annual_2025_cash_precious_metals_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    """Replay one annual-2025 result only from the fixed live trust roots."""

    return _validate_live(value, "annual-2025")


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("wave1-2026", "annual-2025"), default="wave1-2026")
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profile = _profile(args.profile)
    output = args.output or (
        profile["review_path"] if args.write_review else profile["result_path"]
    )
    if args.write_review and args.validate is not None:
        parser.error("--write-review and --validate are mutually exclusive")
    if args.write_review:
        payload = canonical_json_bytes_v1(profile["review_blueprint"]())
        output.write_bytes(payload)
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        result = _validate_live(value, args.profile)
        sys.stdout.write(result["result_id"] + "\n")
        return
    result = _build_live(args.profile)
    payload = canonical_json_bytes_v1(result)
    output.write_bytes(payload)
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    _main()
