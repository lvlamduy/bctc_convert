"""Verify and map the eight-bank deposits-at-central-banks family."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

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
    "CentralBankDeposits8BankCodexVerifiedMappingV1Error",
    "build_live_annual_2025_central_bank_deposits_8bank_codex_verified_mapping_v1",
    "build_central_bank_deposits_8bank_codex_verified_mapping_v1",
    "build_live_central_bank_deposits_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_central_bank_deposits_8bank_codex_verified_mapping_replay_v1",
    "validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1",
    "validate_live_annual_2025_central_bank_deposits_8bank_codex_verified_mapping_v1",
    "validate_live_central_bank_deposits_8bank_codex_verified_mapping_v1",
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
    "trading_securities_verified_mapping_support_for_central_bank_deposits",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_experiment_module(
    "central_bank_deposits_full_document_scan_for_verified_mapping",
    "scan_central_bank_deposits_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_SHARED_VARIANT_ENGINE_"
    "CENTRAL_BANK_DEPOSIT_FIRST_LAST_CLUSTER_BOUNDARY_PERIOD_UNIT_STRUCTURE_"
    "VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_"
    "NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0061-central-bank-deposits-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0061-central-bank-deposits-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "cbdfdsv1:scan:46a3c2587d4802f3725bd7d004e6d264a5f14158dd5a4e66f0d284688c6d86d1"

ANNUAL_2025_FORMAT_VERSION = "ANNUAL_2025_CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFIED_MAPPING_V1"
ANNUAL_2025_REVIEW_FORMAT = "ANNUAL_2025_CENTRAL_BANK_DEPOSITS_8BANK_CODEX_PIXEL_REVIEW_V1"
ANNUAL_2025_CLAIM_BOUNDARY = (
    "FIXED_EIGHT_AUDITED_CONSOLIDATED_ANNUAL_2025_COMPLETE_PDF_FRESH_VIETOCR_"
    "SHARED_VARIANT_ENGINE_CENTRAL_BANK_DEPOSIT_FIRST_LAST_CLUSTER_BOUNDARY_"
    "ADAPTIVE_PERIOD_UNIT_NESTED_GEOGRAPHY_CURRENCY_STRUCTURE_VISIBLE_PIXEL_"
    "UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_"
    "PRODUCTION_AUTHORITY"
)
ANNUAL_2025_REVIEW_PATH = Path(
    "docs/experiments/E-0108-annual-2025-central-bank-deposits-8bank-codex-pixel-review-v1.json"
)
ANNUAL_2025_RESULT_PATH = Path(
    "docs/experiments/E-0108-annual-2025-central-bank-deposits-8bank-codex-verified-mapping-v1.json"
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
    "cbdfdsv1:scan:3279d4ab1da075ebfbe1663b1f16b63675cf06a83e67f0500846129f1eb45ea1"
)

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "DETAILED_NOTE_NOT_BALANCE_SHEET_RESERVE_RATIO_RISK_OR_LIQUIDITY_SURFACE",
    "FIRST_OWNER_AND_LAST_TOTAL_IN_PDF_ORDER",
    "OUTER_OWNER_PRECEDES_CENTRAL_BANK_PARENT_AND_REQUIRED_CHILDREN",
    "FAMILY_LEVEL_CHILD_ORDER_VARIANT_NOT_BANK_ROUTING",
    "CURRENT_PERIOD_MONETARY_AXIS_ONLY",
    "PERIOD_AND_UNIT_AXES_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_AND_SIGN",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "CURRENCY_SUBTOTAL_AND_VISIBLE_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
    "UNMAPPED_GEOGRAPHY_ROWS_NOT_SILENTLY_COERCED_TO_OTHER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "balance_sheet_reserve_ratio_risk_or_liquidity_surface_promoted": False,
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
    "mapping_authority_bounded_to_reviewed_central_bank_deposit_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reserve_ratio_auxiliary_table_used_as_balance_mapping": False,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_geography_rows_promoted_to_other": False,
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
    "CENTRAL_BANK_VIETNAM_PARENT": 570,
    "DEPOSIT_FOREIGN_CURRENCY": 572,
    "DEPOSIT_VND": 571,
    "TOTAL": 569,
    "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE": 574,
}


class CentralBankDeposits8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel ledger, accounting, or live schema drifted."""


def _error(message: str) -> CentralBankDeposits8BankCodexVerifiedMappingV1Error:
    return CentralBankDeposits8BankCodexVerifiedMappingV1Error(message)


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


def _fresh_challenged_value(
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


def _unmapped(
    role: str,
    label_line_index: int,
    label_pixel_transcription: str,
    value_line_index: int,
    pixel_value: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "reason": "NO_EXACT_LIVE_TM_SCHEMA_GEOGRAPHIC_CENTRAL_BANK_CHILD",
        "role": role,
        "value": _value(value_line_index, pixel_value),
    }


def _positive_document(
    bank_code: str,
    page_sequence: int,
    source_period: str,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[tuple[str, int | None, str | None, int, str, str]],
    equations: Sequence[tuple[str, Sequence[tuple[int, str]], tuple[int, str]]],
    unmapped_rows: Sequence[tuple[str, int, str, int, str]] = (),
) -> dict[str, Any]:
    disposition = (
        "VERIFIED_DETAILED_CENTRAL_BANK_DEPOSIT_NOTE_WITH_UNMAPPED_GEOGRAPHY_CHILDREN"
        if unmapped_rows
        else "VERIFIED_DETAILED_CENTRAL_BANK_DEPOSIT_NOTE"
    )
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": disposition,
        "equations": [
            {
                "component_values": [_value(*item) for item in components],
                "name": name,
                "visible_total": _value(*total),
            }
            for name, components, total in equations
        ],
        "evidence_owner_line_index": owner_line_index,
        "mappings": [_mapping(*row) for row in rows],
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": source_period,
        "unmapped_rows": [_unmapped(*row) for row in unmapped_rows],
    }


def _negative_document(
    bank_code: str,
    evidence_page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
) -> dict[str, Any]:
    checks = {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS}
    checks["COMPLETE_PDF_UNIQUE_REGION_ENUMERATION"] = "PASS_NO_COMPLETE_REGION"
    checks["DETAILED_NOTE_NOT_BALANCE_SHEET_RESERVE_RATIO_RISK_OR_LIQUIDITY_SURFACE"] = "PASS"
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
        "unmapped_rows": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _negative_document("ACB", 3, 17, "Tiền gửi tại Ngân hàng Nhà nước"),
        _positive_document(
            "MBB",
            30,
            "2026-06-30",
            20,
            "Tiền gửi tại NHNN",
            [
                (
                    "CENTRAL_BANK_VIETNAM_PARENT",
                    25,
                    "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                    26,
                    "25.269.011",
                    "OWNER_INTERMEDIATE_PARENT",
                ),
                ("DEPOSIT_VND", 28, "Bằng VND", 29, "20.274.233", "PARENT_CHILD"),
                (
                    "DEPOSIT_FOREIGN_CURRENCY",
                    31,
                    "Bằng ngoại tệ",
                    32,
                    "4.994.778",
                    "PARENT_CHILD",
                ),
                (
                    "TOTAL",
                    None,
                    None,
                    40,
                    "27.417.370",
                    "OUTER_OWNER_TO_UNLABELED_TRAILING_TOTAL",
                ),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_VIETNAM_SUBTOTAL",
                    ((29, "20.274.233"), (32, "4.994.778")),
                    (26, "25.269.011"),
                ),
                (
                    "VIETNAM_PLUS_LAOS_PLUS_CAMBODIA_TO_TOTAL",
                    ((26, "25.269.011"), (35, "934.855"), (38, "1.213.504")),
                    (40, "27.417.370"),
                ),
            ],
            (
                (
                    "CENTRAL_BANK_LAOS",
                    34,
                    "Tiền gửi tại Ngân hàng Nhà nước Lào",
                    35,
                    "934.855",
                ),
                (
                    "CENTRAL_BANK_CAMBODIA",
                    37,
                    "Tiền gửi tại Ngân hàng Quốc gia Campuchia",
                    38,
                    "1.213.504",
                ),
            ),
        ),
        _positive_document(
            "VPB",
            38,
            "2026-03-31",
            24,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                ("DEPOSIT_VND", 33, "Bằng VND", 34, "14.221.344", "PARENT_CHILD"),
                (
                    "DEPOSIT_FOREIGN_CURRENCY",
                    37,
                    "Bằng ngoại tệ",
                    38,
                    "595.985",
                    "PARENT_CHILD",
                ),
                (
                    "TOTAL",
                    None,
                    None,
                    40,
                    "14.817.329",
                    "OUTER_OWNER_TO_UNLABELED_TRAILING_TOTAL",
                ),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((34, "14.221.344"), (38, "595.985")),
                    (40, "14.817.329"),
                )
            ],
        ),
        _negative_document("HDB", 3, 21, 'Tiền gửi tại Ngân hàng Nhà nước ("NHNN")'),
        _negative_document("VCB", 7, 22, "Tiền gửi tại Ngân hàng Nhà nước"),
        _negative_document("CTG", 3, 24, "Tiền gửi tại NHNN"),
        _negative_document("BID", 4, 21, "Tiền gửi tại Ngân hàng Trung ương"),
        _positive_document(
            "VIB",
            31,
            "2026-06-30",
            22,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                ("DEPOSIT_VND", 28, "Bằng VND", 29, "3.988.246", "PARENT_CHILD"),
                (
                    "DEPOSIT_FOREIGN_CURRENCY",
                    31,
                    "Bằng ngoại tệ",
                    32,
                    "1.137.029",
                    "PARENT_CHILD",
                ),
                (
                    "TOTAL",
                    None,
                    None,
                    34,
                    "5.125.275",
                    "OUTER_OWNER_TO_UNLABELED_TRAILING_TOTAL",
                ),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((29, "3.988.246"), (32, "1.137.029")),
                    (34, "5.125.275"),
                )
            ],
        ),
    ]


def _annual_mapping(
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


def _annual_other_aggregate(
    components: Sequence[tuple[str, int, str, int, str]],
    pixel_transcription: str,
) -> dict[str, Any]:
    return {
        "component_rows": [
            {
                "label_line_index": label_line_index,
                "label_pixel_transcription": label,
                "role": role,
                "value": _value(value_line_index, pixel_value),
            }
            for role, label_line_index, label, value_line_index, pixel_value in components
        ],
        "label_line_index": None,
        "label_pixel_transcription": None,
        "report_norm_id": 574,
        "role": "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE",
        "topology": "PROJECT_OWNER_APPROVED_GEOGRAPHY_COMPONENT_AGGREGATION",
        "value": {"pixel_transcription": pixel_transcription},
    }


def _annual_positive_document(
    bank_code: str,
    page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[Mapping[str, Any]],
    equations: Sequence[tuple[str, Sequence[tuple[int, str]], tuple[int, str]]],
) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_DETAILED_CENTRAL_BANK_DEPOSIT_NOTE",
        "equations": [
            {
                "component_values": [_value(*item) for item in components],
                "name": name,
                "visible_total": _value(*total),
            }
            for name, components, total in equations
        ],
        "evidence_owner_line_index": owner_line_index,
        "mappings": [canonical_clone_v1(row) for row in rows],
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": "2025-12-31",
        "unmapped_rows": [],
    }


def _annual_2025_review_documents() -> list[dict[str, Any]]:
    direct = _value
    row = _annual_mapping
    return [
        _annual_positive_document(
            "ACB",
            45,
            22,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC",
            [
                row(
                    "DEPOSIT_VND",
                    28,
                    "Bằng Đồng Việt Nam",
                    direct(29, "14.882.677"),
                    "PARENT_CHILD",
                ),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    31,
                    "Bằng ngoại tệ",
                    direct(32, "1.692.281"),
                    "PARENT_CHILD",
                ),
                row("TOTAL", None, None, direct(34, "16.574.958"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((29, "14.882.677"), (32, "1.692.281")),
                    (34, "16.574.958"),
                )
            ],
        ),
        _annual_positive_document(
            "MBB",
            46,
            27,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC",
            [
                row(
                    "CENTRAL_BANK_VIETNAM_PARENT",
                    32,
                    "Tiền gửi tại NHNNVN (i)",
                    direct(33, "66.235.893"),
                    "OWNER_INTERMEDIATE_PARENT",
                ),
                row("DEPOSIT_VND", 35, "Bằng VND", direct(36, "55.806.369"), "PARENT_CHILD"),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    38,
                    "Bằng ngoại tệ",
                    direct(39, "10.429.524"),
                    "PARENT_CHILD",
                ),
                _annual_other_aggregate(
                    (
                        (
                            "CENTRAL_BANK_LAOS",
                            41,
                            "Tiền gửi tại Ngân hàng Nhà nước Lào (ii)",
                            42,
                            "667.675",
                        ),
                        (
                            "CENTRAL_BANK_CAMBODIA",
                            44,
                            "Tiền gửi tại Ngân hàng Quốc gia Campuchia (iii)",
                            45,
                            "1.590.858",
                        ),
                    ),
                    "2.258.533",
                ),
                row("TOTAL", None, None, direct(47, "68.494.426"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_VIETNAM_SUBTOTAL",
                    ((36, "55.806.369"), (39, "10.429.524")),
                    (33, "66.235.893"),
                ),
                (
                    "VIETNAM_PLUS_GEOGRAPHY_COMPONENTS_TO_TOTAL",
                    ((33, "66.235.893"), (42, "667.675"), (45, "1.590.858")),
                    (47, "68.494.426"),
                ),
            ],
        ),
        _annual_positive_document(
            "VPB",
            41,
            24,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                row("DEPOSIT_VND", 32, "Bằng VND", direct(33, "12.837.890"), "PARENT_CHILD"),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    35,
                    "Bằng ngoại tệ",
                    direct(36, "732.586"),
                    "PARENT_CHILD",
                ),
                row("TOTAL", None, None, direct(38, "13.570.476"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((33, "12.837.890"), (36, "732.586")),
                    (38, "13.570.476"),
                )
            ],
        ),
        _annual_positive_document(
            "HDB",
            33,
            50,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC",
            [
                row("DEPOSIT_VND", 57, "Bằng VND", direct(58, "51.490.556"), "PARENT_CHILD"),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    60,
                    "Bằng ngoại tệ",
                    _fresh_challenged_value(61, "8.416.558", "B.416.558"),
                    "PARENT_CHILD",
                ),
                row("TOTAL", None, None, direct(63, "59.907.114"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((58, "51.490.556"), (61, "8.416.558")),
                    (63, "59.907.114"),
                )
            ],
        ),
        _annual_positive_document(
            "VCB",
            35,
            29,
            "Tiền gửi tại Ngân hàng Nhà nước",
            [
                row(
                    "CENTRAL_BANK_VIETNAM_PARENT",
                    34,
                    "Tiền gửi tại Ngân hàng Nhà nước Việt Nam (i)",
                    direct(35, "37.212.251"),
                    "OWNER_INTERMEDIATE_PARENT",
                ),
                _annual_other_aggregate(
                    (
                        (
                            "CENTRAL_BANK_LAOS",
                            37,
                            "Tiền gửi tại Ngân hàng Nhà nước Lào (ii)",
                            38,
                            "233.253",
                        ),
                    ),
                    "233.253",
                ),
                row("TOTAL", None, None, direct(40, "37.445.504"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VIETNAM_PLUS_OTHER_TO_TOTAL",
                    ((35, "37.212.251"), (38, "233.253")),
                    (40, "37.445.504"),
                )
            ],
        ),
        _annual_positive_document(
            "CTG",
            39,
            53,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                row("DEPOSIT_VND", 59, "Bằng VND", direct(60, "31.611.208"), "PARENT_CHILD"),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    62,
                    "Bằng ngoại tệ",
                    direct(63, "3.614.335"),
                    "PARENT_CHILD",
                ),
                row("TOTAL", None, None, direct(65, "35.225.543"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((60, "31.611.208"), (63, "3.614.335")),
                    (65, "35.225.543"),
                )
            ],
        ),
        _annual_positive_document(
            "BID",
            39,
            21,
            "TIỀN GỬI TẠI NGÂN HÀNG TRUNG ƯƠNG",
            [
                row(
                    "CENTRAL_BANK_VIETNAM_PARENT",
                    26,
                    "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                    direct(27, "117.802.342"),
                    "OWNER_INTERMEDIATE_PARENT",
                ),
                row("DEPOSIT_VND", 29, "Bằng VND", direct(30, "104.938.156"), "PARENT_CHILD"),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    32,
                    "Bằng ngoại tệ",
                    direct(33, "12.864.186"),
                    "PARENT_CHILD",
                ),
                _annual_other_aggregate(
                    (
                        (
                            "CENTRAL_BANK_CAMBODIA",
                            35,
                            "Tiền gửi tại Ngân hàng Quốc gia Campuchia",
                            36,
                            "2.460.732",
                        ),
                        (
                            "CENTRAL_BANK_LAOS",
                            41,
                            "Tiền gửi tại Ngân hàng Trung ương Lào",
                            42,
                            "3.366.759",
                        ),
                    ),
                    "5.827.491",
                ),
                row("TOTAL", None, None, direct(49, "123.629.833"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_VIETNAM_SUBTOTAL",
                    ((30, "104.938.156"), (33, "12.864.186")),
                    (27, "117.802.342"),
                ),
                (
                    "VIETNAM_PLUS_GEOGRAPHY_COMPONENTS_TO_TOTAL",
                    ((27, "117.802.342"), (36, "2.460.732"), (42, "3.366.759")),
                    (49, "123.629.833"),
                ),
            ],
        ),
        _annual_positive_document(
            "VIB",
            35,
            22,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                row("DEPOSIT_VND", 28, "Bằng VND", direct(29, "8.630.240"), "PARENT_CHILD"),
                row(
                    "DEPOSIT_FOREIGN_CURRENCY",
                    33,
                    "Bằng ngoại tệ",
                    direct(31, "367.828"),
                    "VALUE_PRECEDES_LABEL_IN_PROVIDER_READING_ORDER",
                ),
                row("TOTAL", None, None, direct(34, "8.998.068"), "UNLABELED_TRAILING_TOTAL"),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((29, "8.630.240"), (31, "367.828")),
                    (34, "8.998.068"),
                )
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
            "review_run_id": "E-0061",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0061:pixel-review:" + canonical_json_sha256_v1(material)}


def _annual_2025_review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": ANNUAL_2025_CLAIM_BOUNDARY,
        "documents": _annual_2025_review_documents(),
        "format_version": ANNUAL_2025_REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0108-ANNUAL-2025",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
        "semantic_axis_sha256": ANNUAL_2025_EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": ANNUAL_2025_EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0108:pixel-review:" + canonical_json_sha256_v1(material)}


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
            "result_id_prefix": "cbd8bcv1:result:",
            "result_path": RESULT_PATH,
            "review_blueprint": _review_blueprint,
            "review_path": REVIEW_PATH,
            "scan_id": EXPECTED_SCAN_ID,
            "state": "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFICATION_COMPLETE",
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
            "result_id_prefix": "annual2025cbd8bcv1:result:",
            "result_path": ANNUAL_2025_RESULT_PATH,
            "review_blueprint": _annual_2025_review_blueprint,
            "review_path": ANNUAL_2025_REVIEW_PATH,
            "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
            "state": "ANNUAL_2025_CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFICATION_COMPLETE",
        }
    raise _error("central-bank deposit mapping profile is unsupported")


def _review(value: Any, profile_name: str = "wave1-2026") -> dict[str, Any]:
    expected = _profile(profile_name)["review_blueprint"]()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex central-bank deposit pixel review differs from fixed ledger")
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


def _anchor_match(transformer_text: str, pixel_text: str, label: str) -> str:
    kind = match_vietnamese_anchor_alias_v1(transformer_text, [pixel_text])
    if kind is None:
        raise _error(f"visible {label} and fresh VietOCR disagree beyond one base character")
    return kind


def _schema_binding(item: Any, role: str) -> dict[str, Any]:
    schema_id = _MAPPING_SCHEMA.get(role)
    expected_parent = 560 if role == "TOTAL" else 569
    if (
        item is None
        or schema_id is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.parent_id != expected_parent
    ):
        raise _error("reviewed mapping does not bind one exact live central-bank TM item")
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
        raise _error("central-bank deposit graph event axis drifted")
    matches = [event for event in events if type(event) is dict and event.get("role") == role]
    if len(matches) != 1:
        raise _error(f"central-bank deposit graph does not contain one exact role {role}")
    return matches[0]


def _source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is dict and set(value) == {
        "fresh_vietocr_challenger_expected",
        "line_index",
        "pixel_transcription",
        "resolution",
        "source_numeric_challenger_expected",
    }:
        return _fresh_challenged_source_value(
            axis_page,
            semantic_page,
            crop_page,
            source_texts,
            value,
        )
    try:
        return support._source_value(axis_page, semantic_page, crop_page, source_texts, value)
    except Exception as exc:
        raise _error(f"central-bank deposit source numeric evidence drifted: {exc}") from exc


def _fresh_challenged_source_value(
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
    try:
        fresh_value = support._money(axis["vietocr_text"])
    except Exception:
        fresh_value = None
    if fresh_value == pixel_value:
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
        "partial_mapping_document_count": sum(
            bool(trial["unmapped_source_rows"]) for trial in trials
        ),
        "q1_source_period_caveat_document_count": sum(
            trial.get("source_period_status") == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unmapped_source_row_count": sum(len(trial["unmapped_source_rows"]) for trial in trials),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }


def _validate_result(value: Any, profile_name: str = "wave1-2026") -> dict[str, Any]:
    profile = _profile(profile_name)
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("central-bank deposit mapping result fields drifted")
    if (
        value["format_version"] != profile["format_version"]
        or value["claim_boundary"] != profile["claim_boundary"]
        or value["state"] != profile["state"]
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("central-bank deposit mapping result identity or metrics drifted")
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
                "VERIFIED_BY_CODEX_WITH_UNMAPPED_SOURCE_ROWS",
            }
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("verified_accounting_equations")) is not list
            or type(trial.get("unmapped_source_rows")) is not list
        ):
            raise _error("central-bank deposit mapping trial shape drifted")
        for mapping in trial["verified_mappings"]:
            if type(mapping) is not dict or mapping.get("status") != "VERIFIED_BY_CODEX":
                raise _error("central-bank deposit mapped row status drifted")
        for unresolved in trial["unmapped_source_rows"]:
            if (
                type(unresolved) is not dict
                or unresolved.get("status") != "UNRESOLVED_SCHEMA_ITEM_ABSENT"
            ):
                raise _error("central-bank deposit unmapped source row status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != profile["result_id_prefix"] + canonical_json_sha256_v1(material):
        raise _error("central-bank deposit mapping result identity drifted")
    return canonical_clone_v1(value)


def build_central_bank_deposits_8bank_codex_verified_mapping_v1(
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
    """Build the exact eight-bank bounded central-bank deposit mapping result."""

    profile = _profile(_profile_name)
    review = _review(review_value, _profile_name)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != profile["axis_sha256"]
        or structure_scan.get("scan_id") != profile["scan_id"]
        or structure_scan.get("state")
        != "FULL_DOCUMENT_CENTRAL_BANK_DEPOSIT_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("central-bank deposit input authority drifted")
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
            raise _error("whole-PDF central-bank deposit scan identity drifted")
        page_number = reviewed["page_sequence"]
        axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
        owner_line = _axis_line(axis_page, reviewed["evidence_owner_line_index"])
        _anchor_match(owner_line["vietocr_text"], reviewed["owner_pixel_transcription"], "owner")
        if not reviewed["mappings"]:
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("regions") != []
                or reviewed["equations"]
                or reviewed["unmapped_rows"]
            ):
                raise _error("negative central-bank deposit disposition drifted")
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
                    "unmapped_source_rows": [],
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
            raise _error("whole-PDF central-bank deposit region is not exactly unique")
        region = matcher["regions"][0]
        axes = region.get("layout", {}).get("meaningful_axes", {})
        if (
            region.get("page_sequence") != page_number
            or axes.get("unit_header_count", 0) < 1
            or axes.get("period_header_count", 0) < 2
            or region.get("owner", {}).get("source_line_index")
            != reviewed["evidence_owner_line_index"]
        ):
            raise _error("reviewed page/layout disagrees with generic central-bank graph")
        semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
        crop_page = _page_by_number(crop_document, page_number, "crop manifest")
        try:
            source_texts = _source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"central-bank deposit source line axis drifted: {exc}") from exc
        mapped_rows = []
        for row in reviewed["mappings"]:
            role = row["role"]
            if role == "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE":
                components = row.get("component_rows")
                aggregate_value = row.get("value")
                if (
                    row.get("label_line_index") is not None
                    or row.get("label_pixel_transcription") is not None
                    or type(components) is not list
                    or not components
                    or type(aggregate_value) is not dict
                    or set(aggregate_value) != {"pixel_transcription"}
                ):
                    raise _error("other-central-bank aggregate review fields drifted")
                component_evidence = []
                for component in components:
                    if (
                        type(component) is not dict
                        or set(component)
                        != {
                            "label_line_index",
                            "label_pixel_transcription",
                            "role",
                            "value",
                        }
                        or component["role"] not in {"CENTRAL_BANK_LAOS", "CENTRAL_BANK_CAMBODIA"}
                        or type(component["label_line_index"]) is not int
                    ):
                        raise _error("other-central-bank aggregate component fields drifted")
                    event = _region_event(region, component["role"])
                    label_index = component["label_line_index"]
                    if event.get("source_line_index") != label_index:
                        raise _error("other-central-bank component left its graph event")
                    match_kind = _anchor_match(
                        _axis_line(axis_page, label_index)["vietocr_text"],
                        component["label_pixel_transcription"],
                        component["role"],
                    )
                    value_index = component["value"]["line_index"]
                    if value_index not in {
                        item["source_line_index"] for item in event.get("value_proposals", [])
                    }:
                        raise _error("other-central-bank component value left its graph row")
                    source_value = _source_value(
                        axis_page,
                        semantic_page,
                        crop_page,
                        source_texts,
                        component["value"],
                    )
                    component_evidence.append(
                        {
                            "anchor_match_kind": match_kind,
                            "independent_pixel_label": component["label_pixel_transcription"],
                            "role": component["role"],
                            "source_value": source_value,
                            "vietocr_transformer_text": _axis_line(axis_page, label_index)[
                                "vietocr_text"
                            ],
                        }
                    )
                normalized_value = sum(
                    item["source_value"]["normalized_value"] for item in component_evidence
                )
                if normalized_value != support._money(aggregate_value["pixel_transcription"]):
                    raise _error("other-central-bank aggregate does not equal its components")
                schema = _schema_binding(schema_by_id.get(row["report_norm_id"]), role)
                mapped_rows.append(
                    {
                        **schema,
                        "anchor_match_kind": None,
                        "independent_pixel_label": None,
                        "normalized_anchor": None,
                        "normalized_value": normalized_value,
                        "physical_page": page_number,
                        "role": role,
                        "source_value": {
                            "component_rows": component_evidence,
                            "normalized_value": normalized_value,
                            "pixel_transcription": aggregate_value["pixel_transcription"],
                            "resolution": (
                                "PROJECT_OWNER_APPROVED_GEOGRAPHY_COMPONENT_AGGREGATION_TO_"
                                "OTHER_DEPOSITS_574"
                            ),
                        },
                        "status": "VERIFIED_BY_CODEX",
                        "topology": row["topology"],
                        "vietocr_transformer_text": [
                            item["vietocr_transformer_text"] for item in component_evidence
                        ],
                    }
                )
                continue
            event = _region_event(region, role)
            label_index = row["label_line_index"]
            match_kind = None
            if role == "TOTAL":
                if label_index is not None or row["label_pixel_transcription"] is not None:
                    raise _error("unlabeled total acquired a fabricated label")
            else:
                if type(label_index) is not int or event.get("source_line_index") != label_index:
                    raise _error("central-bank graph/review label binding drifted")
                match_kind = _anchor_match(
                    _axis_line(axis_page, label_index)["vietocr_text"],
                    row["label_pixel_transcription"],
                    role,
                )
            value_index = row["value"]["line_index"]
            if value_index not in {
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
                    "anchor_match_kind": match_kind,
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
        unmapped_rows = []
        for row in reviewed["unmapped_rows"]:
            event = _region_event(region, row["role"])
            if event.get("source_line_index") != row["label_line_index"]:
                raise _error("unmapped geography row left its graph event")
            match_kind = _anchor_match(
                _axis_line(axis_page, row["label_line_index"])["vietocr_text"],
                row["label_pixel_transcription"],
                row["role"],
            )
            if row["value"]["line_index"] not in {
                item["source_line_index"] for item in event.get("value_proposals", [])
            }:
                raise _error("unmapped geography value left its graph row")
            source_value = _source_value(
                axis_page, semantic_page, crop_page, source_texts, row["value"]
            )
            unmapped_rows.append(
                {
                    "anchor_match_kind": match_kind,
                    "candidate_schema_status": "NO_EXACT_LIVE_TM_SCHEMA_ITEM",
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "normalized_value": source_value["normalized_value"],
                    "physical_page": page_number,
                    "reason": row["reason"],
                    "role": row["role"],
                    "source_value": source_value,
                    "status": "UNRESOLVED_SCHEMA_ITEM_ABSENT",
                    "vietocr_transformer_text": [
                        _axis_line(axis_page, row["label_line_index"])["vietocr_text"]
                    ],
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
                raise _error(f"central-bank deposit equation does not close: {code}")
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
        status = (
            "VERIFIED_BY_CODEX_WITH_UNMAPPED_SOURCE_ROWS"
            if unmapped_rows
            else (
                "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                else "VERIFIED_BY_CODEX"
            )
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
                "status": status,
                "unmapped_source_rows": unmapped_rows,
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


def validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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
    structure_scan = scanner.build_central_bank_deposits_full_document_scan_v1(semantic_index)
    expected = build_central_bank_deposits_8bank_codex_verified_mapping_v1(
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
        raise _error("central-bank deposit mapping does not replay exactly")
    return persisted


def validate_annual_2025_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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
    """Exact-rebuild the annual-2025 result."""

    return validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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
    structure_scan = scanner.build_central_bank_deposits_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_central_bank_deposits_8bank_codex_verified_mapping_v1(
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
    return validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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


def build_live_central_bank_deposits_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Read the fixed wave-1 inputs and build the verified result."""

    return _build_live("wave1-2026")


def build_live_annual_2025_central_bank_deposits_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
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
    return validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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


def validate_live_central_bank_deposits_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    """Replay one wave-1 result only from the fixed live trust roots."""

    return _validate_live(value, "wave1-2026")


def validate_live_annual_2025_central_bank_deposits_8bank_codex_verified_mapping_v1(
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
        output.write_bytes(canonical_json_bytes_v1(profile["review_blueprint"]()))
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        result = _validate_live(value, args.profile)
        sys.stdout.write(result["result_id"] + "\n")
        return
    result = _build_live(args.profile)
    output.write_bytes(canonical_json_bytes_v1(result))
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    _main()
