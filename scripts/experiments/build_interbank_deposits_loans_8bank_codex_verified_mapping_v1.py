"""Verify and map deposits at and loans to other credit institutions."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
    "InterbankDepositsLoans8BankCodexVerifiedMappingV1Error",
    "build_live_annual_2025_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
    "build_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
    "build_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1",
    "validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1",
    "validate_live_annual_2025_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
    "validate_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
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
    "trading_securities_verified_mapping_support_for_interbank_deposits_loans",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_experiment_module(
    "interbank_deposits_loans_full_document_scan_for_verified_mapping",
    "scan_interbank_deposits_loans_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_SHARED_VARIANT_ENGINE_"
    "INTERBANK_DEPOSIT_LOAN_FIRST_LAST_CLUSTER_BOUNDARY_HORIZONTAL_VERTICAL_"
    "LAYOUT_PERIOD_UNIT_STRUCTURE_VISIBLE_PIXEL_DASH_ZERO_UPSTREAM_NUMERIC_"
    "CHALLENGER_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0062-interbank-deposits-loans-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0062-interbank-deposits-loans-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "idlfdsv1:scan:bbf6b7956601f8d66e2abf90f0b5f3b9e893b25acc9dc13151919f46a62a8253"

ANNUAL_2025_FORMAT_VERSION = "ANNUAL_2025_INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_VERIFIED_MAPPING_V1"
ANNUAL_2025_REVIEW_FORMAT = "ANNUAL_2025_INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_PIXEL_REVIEW_V1"
ANNUAL_2025_CLAIM_BOUNDARY = (
    "FIXED_EIGHT_AUDITED_CONSOLIDATED_ANNUAL_2025_COMPLETE_PDF_FRESH_VIETOCR_"
    "SHARED_VARIANT_ENGINE_INTERBANK_DEPOSIT_LOAN_FIRST_LAST_CLUSTER_BOUNDARY_"
    "ADAPTIVE_PERIOD_UNIT_NESTED_SUBTOTAL_OPTIONAL_PROVISION_VISIBLE_PIXEL_DASH_"
    "ZERO_UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
ANNUAL_2025_REVIEW_PATH = Path(
    "docs/experiments/E-0109-annual-2025-interbank-deposits-loans-8bank-codex-pixel-review-v1.json"
)
ANNUAL_2025_RESULT_PATH = Path(
    "docs/experiments/E-0109-annual-2025-interbank-deposits-loans-8bank-codex-verified-mapping-v1.json"
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
    "idlfdsv1:scan:36e679f758c14c5b4dbf864c013754af96ff258b61bb79fadaa67800185ea906"
)

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "DETAILED_NOTE_NOT_BALANCE_SHEET_FAIR_VALUE_FOREIGN_EXCHANGE_OR_POLICY_SURFACE",
    "FIRST_OWNER_AND_LAST_TOTAL_IN_PDF_ORDER",
    "OUTER_OWNER_PRECEDES_DEPOSIT_AND_LOAN_PARENTS_AND_REQUIRED_CHILDREN",
    "FAMILY_LEVEL_CHILD_ORDER_VARIANT_NOT_BANK_ROUTING",
    "CURRENT_PERIOD_MONETARY_AXIS_ONLY",
    "PERIOD_AND_PAGE_OR_DOCUMENT_LEVEL_UNIT_AXES_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGN_AND_DASH_ZERO_STATUS",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "DEPOSIT_LOAN_SUBTOTAL_AND_VISIBLE_FAMILY_TOTAL_ACCOUNTING",
    "DISCOUNT_REDISCOUNT_ROW_IS_NON_ADDITIVE_DETAIL",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "balance_sheet_fair_value_foreign_exchange_or_policy_surface_promoted": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "dash_pixel_status_preserved_before_zero_normalization": True,
    "document_level_unit_inheritance_requires_explicit_pdf_text": True,
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
    "dash_pixel_status_preserved_before_owner_approved_zero_normalization": True,
    "document_level_unit_inheritance_requires_explicit_pdf_text": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_interbank_deposit_loan_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "fair_value_foreign_exchange_or_policy_table_used_as_balance_mapping": False,
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
    "DEMAND_DEPOSIT": 577,
    "DEMAND_DEPOSIT_FOREIGN_CURRENCY": 579,
    "DEMAND_DEPOSIT_VND": 578,
    "FAMILY_TOTAL": 575,
    "INTERBANK_DEPOSIT_PARENT": 576,
    "INTERBANK_DEPOSIT_PROVISION": 583,
    "INTERBANK_LOAN": 585,
    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT": 587,
    "INTERBANK_LOAN_FOREIGN_CURRENCY": 588,
    "INTERBANK_LOAN_PROVISION": 590,
    "INTERBANK_LOAN_VND": 586,
    "TERM_DEPOSIT": 580,
    "TERM_DEPOSIT_FOREIGN_CURRENCY": 582,
    "TERM_DEPOSIT_VND": 581,
    "TOTAL_INTERBANK_PROVISION": 5718,
}
_SCHEMA_PARENT = {
    "DEMAND_DEPOSIT": 576,
    "DEMAND_DEPOSIT_FOREIGN_CURRENCY": 576,
    "DEMAND_DEPOSIT_VND": 576,
    "FAMILY_TOTAL": 560,
    "INTERBANK_DEPOSIT_PARENT": 575,
    "INTERBANK_DEPOSIT_PROVISION": 576,
    "INTERBANK_LOAN": 575,
    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT": 585,
    "INTERBANK_LOAN_FOREIGN_CURRENCY": 585,
    "INTERBANK_LOAN_PROVISION": 585,
    "INTERBANK_LOAN_VND": 585,
    "TERM_DEPOSIT": 576,
    "TERM_DEPOSIT_FOREIGN_CURRENCY": 576,
    "TERM_DEPOSIT_VND": 576,
    "TOTAL_INTERBANK_PROVISION": 575,
}


class InterbankDepositsLoans8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel ledger, accounting, or live schema drifted."""


def _error(message: str) -> InterbankDepositsLoans8BankCodexVerifiedMappingV1Error:
    return InterbankDepositsLoans8BankCodexVerifiedMappingV1Error(message)


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


def _value(
    line_index: int | None,
    pixel_transcription: str,
    pixel_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "line_index": line_index,
        "pixel_binding": canonical_clone_v1(pixel_binding),
        "pixel_transcription": pixel_transcription,
    }


def _fresh_challenged_value(
    line_index: int,
    pixel_transcription: str,
    fresh_vietocr_challenger_expected: str,
    source_numeric_challenger_expected: str | None = None,
) -> dict[str, Any]:
    return {
        "fresh_vietocr_challenger_expected": fresh_vietocr_challenger_expected,
        "line_index": line_index,
        "pixel_transcription": pixel_transcription,
        "resolution": (
            "INDEPENDENT_PIXEL_TRANSCRIPTION_CORROBORATED_BY_PROVIDER_AND_EXACT_ACCOUNTING_EQUATION"
        ),
        "source_numeric_challenger_expected": (
            pixel_transcription
            if source_numeric_challenger_expected is None
            else source_numeric_challenger_expected
        ),
    }


def _mapping(
    role: str,
    label_line_index: int | None,
    label_pixel_transcription: str | None,
    value_line_index: int | None,
    pixel_value: str,
    topology: str,
    pixel_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": _MAPPING_SCHEMA[role],
        "role": role,
        "topology": topology,
        "value": _value(value_line_index, pixel_value, pixel_binding),
    }


def _annual_mapping(
    role: str,
    label_line_index: int | None,
    label_pixel_transcription: str | None,
    value: Mapping[str, Any],
    topology: str,
    *,
    graph_role: str | None = None,
) -> dict[str, Any]:
    return {
        "graph_role": role if graph_role is None else graph_role,
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": _MAPPING_SCHEMA[role],
        "role": role,
        "topology": topology,
        "value": canonical_clone_v1(value),
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
        "reason": "NO_EXACT_LIVE_TM_SCHEMA_INTERBANK_DEPOSIT_LOAN_CHILD",
        "role": role,
        "value": _value(value_line_index, pixel_value),
    }


def _positive_document(
    bank_code: str,
    page_sequence: int,
    source_period: str,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[tuple[Any, ...]],
    equations: Sequence[tuple[str, Sequence[tuple[int, str]], tuple[int, str]]],
    unmapped_rows: Sequence[tuple[str, int, str, int, str]] = (),
) -> dict[str, Any]:
    disposition = (
        "VERIFIED_DETAILED_INTERBANK_DEPOSIT_LOAN_NOTE_WITH_UNMAPPED_SOURCE_ROWS"
        if unmapped_rows
        else "VERIFIED_DETAILED_INTERBANK_DEPOSIT_LOAN_NOTE"
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
    checks["DETAILED_NOTE_NOT_BALANCE_SHEET_FAIR_VALUE_FOREIGN_EXCHANGE_OR_POLICY_SURFACE"] = "PASS"
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
    dash_deposit = {
        "bbox_raw_pixels": [1288, 934, 1308, 949],
        "rgb_sha256": "c07d0cfa9af407d33be900f755a51423388e6d544eac1cf04aa05f7661d0ba6e",
    }
    dash_loan_foreign = {
        "bbox_raw_pixels": [1286, 1124, 1306, 1139],
        "rgb_sha256": "f9d058fd06f0f87b2f1c441e8081bccd4ab57b51ce1c16bb7a21c3f9a2752dba",
    }
    dash_loan_provision = {
        "bbox_raw_pixels": [1286, 1161, 1306, 1175],
        "rgb_sha256": "2d07484bc167018b3027243449173c69a023bac5d07a44df143c9a5e88510fcb",
    }
    return [
        _positive_document(
            "ACB",
            16,
            "2026-06-30",
            6,
            "1. TIỀN GỬI VÀ CHO VAY CÁC TỔ CHỨC TÍN DỤNG KHÁC:",
            [
                (
                    "FAMILY_TOTAL",
                    39,
                    "Tổng tiền gửi và cho vay các TCTD khác",
                    40,
                    "123.441.277",
                    "OUTER_OWNER_EXPLICIT_TOTAL",
                ),
                (
                    "INTERBANK_DEPOSIT_PARENT",
                    11,
                    "Tiền gửi tại các TCTD khác",
                    31,
                    "117.048.437",
                    "OWNER_INTERMEDIATE_PARENT_TRAILING_SUBTOTAL",
                ),
                (
                    "DEMAND_DEPOSIT",
                    12,
                    "Tiền gửi không kỳ hạn",
                    13,
                    "23.176.605",
                    "PARENT_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_VND",
                    15,
                    "Bằng đồng Việt Nam",
                    16,
                    "12.834.486",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    18,
                    "Bằng ngoại tệ",
                    19,
                    "10.342.119",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT",
                    21,
                    "Tiền gửi có kỳ hạn",
                    22,
                    "93.871.832",
                    "PARENT_CHILD",
                ),
                (
                    "TERM_DEPOSIT_VND",
                    24,
                    "Bằng đồng Việt Nam",
                    25,
                    "87.903.321",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    27,
                    "Bằng ngoại tệ",
                    28,
                    "5.968.511",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_DEPOSIT_PROVISION",
                    30,
                    "Dự phòng rủi ro",
                    None,
                    "-",
                    "DEPOSIT_PROVISION_VISIBLE_DASH",
                    dash_deposit,
                ),
                (
                    "INTERBANK_LOAN",
                    33,
                    "Cho vay các TCTD khác",
                    38,
                    "6.392.840",
                    "OWNER_INTERMEDIATE_PARENT_TRAILING_SUBTOTAL",
                ),
                (
                    "INTERBANK_LOAN_VND",
                    34,
                    "Bằng đồng Việt Nam",
                    35,
                    "6.392.840",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    36,
                    "Bằng ngoại tệ",
                    None,
                    "-",
                    "PARENT_CURRENCY_CHILD_VISIBLE_DASH",
                    dash_loan_foreign,
                ),
                (
                    "INTERBANK_LOAN_PROVISION",
                    37,
                    "Dự phòng rủi ro cho vay các TCTD khác",
                    None,
                    "-",
                    "LOAN_PROVISION_VISIBLE_DASH",
                    dash_loan_provision,
                ),
            ],
            [
                (
                    "DEMAND_VND_PLUS_FOREIGN_TO_DEMAND_SUBTOTAL",
                    ((16, "12.834.486"), (19, "10.342.119")),
                    (13, "23.176.605"),
                ),
                (
                    "TERM_VND_PLUS_FOREIGN_TO_TERM_SUBTOTAL",
                    ((25, "87.903.321"), (28, "5.968.511")),
                    (22, "93.871.832"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    ((13, "23.176.605"), (22, "93.871.832")),
                    (31, "117.048.437"),
                ),
                (
                    "LOAN_VND_TO_LOAN_SUBTOTAL",
                    ((35, "6.392.840"),),
                    (38, "6.392.840"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_TO_FAMILY_TOTAL",
                    ((31, "117.048.437"), (38, "6.392.840")),
                    (40, "123.441.277"),
                ),
            ],
        ),
        _positive_document(
            "MBB",
            30,
            "2026-06-30",
            43,
            "Tiền gửi và cho vay các TCTD khác",
            [
                (
                    "FAMILY_TOTAL",
                    None,
                    None,
                    78,
                    "174.745.578",
                    "OUTER_OWNER_UNLABELED_TRAILING_TOTAL",
                ),
                (
                    "INTERBANK_DEPOSIT_PARENT",
                    48,
                    "Tiền gửi tại các TCTD khác",
                    49,
                    "154.948.823",
                    "OWNER_INTERMEDIATE_PARENT_INLINE_TOTAL",
                ),
                (
                    "DEMAND_DEPOSIT_VND",
                    53,
                    "Bằng VND",
                    54,
                    "55.447.867",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    56,
                    "Bằng ngoại tệ",
                    57,
                    "9.009.228",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_VND",
                    60,
                    "Bằng VND",
                    61,
                    "83.918.168",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    63,
                    "Bằng ngoại tệ",
                    64,
                    "6.573.560",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN",
                    66,
                    "Cho vay các TCTD khác",
                    67,
                    "19.808.571",
                    "OWNER_INTERMEDIATE_PARENT_INLINE_TOTAL",
                ),
                (
                    "INTERBANK_LOAN_VND",
                    69,
                    "Bằng VND",
                    70,
                    "14.279.358",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    72,
                    "Bằng ngoại tệ",
                    73,
                    "5.529.213",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_PROVISION",
                    75,
                    "Dự phòng rủi ro",
                    76,
                    "(11.816)",
                    "LOAN_PARENT_TRAILING_PROVISION",
                ),
            ],
            [
                (
                    "FOUR_DEPOSIT_CURRENCY_CHILDREN_TO_DEPOSIT_SUBTOTAL",
                    (
                        (54, "55.447.867"),
                        (57, "9.009.228"),
                        (61, "83.918.168"),
                        (64, "6.573.560"),
                    ),
                    (49, "154.948.823"),
                ),
                (
                    "LOAN_VND_PLUS_FOREIGN_TO_LOAN_SUBTOTAL",
                    ((70, "14.279.358"), (73, "5.529.213")),
                    (67, "19.808.571"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_PLUS_NEGATIVE_PROVISION_TO_FAMILY_TOTAL",
                    (
                        (49, "154.948.823"),
                        (67, "19.808.571"),
                        (76, "(11.816)"),
                    ),
                    (78, "174.745.578"),
                ),
            ],
        ),
        _positive_document(
            "VPB",
            39,
            "2026-03-31",
            5,
            "TIỀN GỬI VÀ CẤP TÍN DỤNG CHO CÁC TỔ CHỨC TÍN DỤNG KHÁC",
            [
                (
                    "INTERBANK_DEPOSIT_PARENT",
                    7,
                    "Tiền gửi tại các TCTD khác",
                    36,
                    "189.087.178",
                    "OWNER_INTERMEDIATE_PARENT_TRAILING_SUBTOTAL",
                ),
                (
                    "DEMAND_DEPOSIT",
                    14,
                    "Tiền gửi không kỳ hạn",
                    15,
                    "12.126.080",
                    "PARENT_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_VND",
                    18,
                    "Bằng VND",
                    19,
                    "10.331.044",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    22,
                    "Bằng ngoại tệ",
                    23,
                    "1.795.036",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT",
                    25,
                    "Tiền gửi có kỳ hạn",
                    26,
                    "176.961.098",
                    "PARENT_CHILD",
                ),
                (
                    "TERM_DEPOSIT_VND",
                    29,
                    "Bằng VND",
                    30,
                    "149.419.100",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    33,
                    "Bằng ngoại tệ",
                    34,
                    "27.541.998",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN",
                    39,
                    "Cấp tín dụng cho TCTD khác",
                    53,
                    "5.929.400",
                    "OWNER_INTERMEDIATE_PARENT_TRAILING_SUBTOTAL",
                ),
                (
                    "INTERBANK_LOAN_VND",
                    47,
                    "Bằng VND",
                    48,
                    "5.929.400",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    50,
                    "Trong đó: chiết khấu, tái chiết khấu",
                    51,
                    "4.743.324",
                    "NON_ADDITIVE_LOAN_DETAIL",
                ),
            ],
            [
                (
                    "DEMAND_VND_PLUS_FOREIGN_TO_DEMAND_SUBTOTAL",
                    ((19, "10.331.044"), (23, "1.795.036")),
                    (15, "12.126.080"),
                ),
                (
                    "TERM_VND_PLUS_FOREIGN_TO_TERM_SUBTOTAL",
                    ((30, "149.419.100"), (34, "27.541.998")),
                    (26, "176.961.098"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    ((15, "12.126.080"), (26, "176.961.098")),
                    (36, "189.087.178"),
                ),
                (
                    "LOAN_VND_TO_LOAN_SUBTOTAL",
                    ((48, "5.929.400"),),
                    (53, "5.929.400"),
                ),
            ],
        ),
        _negative_document("HDB", 3, 25, "Tiền gửi tại và cho vay các TCTD khác"),
        _negative_document("VCB", 7, 26, "Tiền gửi tại và cho vay các tổ chức tín dụng khác"),
        _positive_document(
            "CTG",
            41,
            "2026-06-30",
            27,
            "8. TIỀN GỬI VÀ VAY CÁC TCTD KHÁC",
            [
                (
                    "FAMILY_TOTAL",
                    None,
                    None,
                    63,
                    "472.518.030",
                    "OUTER_OWNER_UNLABELED_TRAILING_TOTAL",
                ),
                (
                    "DEMAND_DEPOSIT",
                    33,
                    "Tiền gửi không kỳ hạn",
                    34,
                    "352.009.534",
                    "OWNER_DIRECT_GROUP_PARENT",
                ),
                (
                    "DEMAND_DEPOSIT_VND",
                    36,
                    "Bằng VND",
                    37,
                    "167.636.256",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    39,
                    "Bằng ngoại tệ",
                    40,
                    "184.373.278",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT",
                    42,
                    "Tiền gửi có kỳ hạn",
                    43,
                    "98.318.004",
                    "OWNER_DIRECT_GROUP_PARENT",
                ),
                (
                    "TERM_DEPOSIT_VND",
                    45,
                    "Bằng VND",
                    46,
                    "85.458.000",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    48,
                    "Bằng ngoại tệ",
                    49,
                    "12.860.004",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN",
                    51,
                    "Vay các TCTD khác",
                    52,
                    "22.190.492",
                    "OWNER_DIRECT_GROUP_PARENT",
                ),
                (
                    "INTERBANK_LOAN_VND",
                    54,
                    "Bằng VND",
                    55,
                    "11.590.877",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    57,
                    "Trong đó: Vay chiết khấu, tái chiết khấu",
                    58,
                    "999.315",
                    "NON_ADDITIVE_LOAN_DETAIL",
                ),
                (
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    60,
                    "Bằng ngoại tệ",
                    61,
                    "10.599.615",
                    "PARENT_CURRENCY_CHILD",
                ),
            ],
            [
                (
                    "DEMAND_VND_PLUS_FOREIGN_TO_DEMAND_SUBTOTAL",
                    ((37, "167.636.256"), (40, "184.373.278")),
                    (34, "352.009.534"),
                ),
                (
                    "TERM_VND_PLUS_FOREIGN_TO_TERM_SUBTOTAL",
                    ((46, "85.458.000"), (49, "12.860.004")),
                    (43, "98.318.004"),
                ),
                (
                    "LOAN_VND_PLUS_FOREIGN_TO_LOAN_SUBTOTAL",
                    ((55, "11.590.877"), (61, "10.599.615")),
                    (52, "22.190.492"),
                ),
                (
                    "DEMAND_PLUS_TERM_PLUS_LOAN_TO_FAMILY_TOTAL",
                    (
                        (34, "352.009.534"),
                        (43, "98.318.004"),
                        (52, "22.190.492"),
                    ),
                    (63, "472.518.030"),
                ),
            ],
        ),
        _positive_document(
            "BID",
            25,
            "2026-06-30",
            5,
            "8. TIỀN GỬI VÀ VAY CÁC TCTD KHÁC",
            [
                (
                    "FAMILY_TOTAL",
                    None,
                    None,
                    35,
                    "372,094,003",
                    "OUTER_OWNER_UNLABELED_TRAILING_TOTAL",
                ),
                (
                    "DEMAND_DEPOSIT",
                    8,
                    "Tiền, vàng gửi không kỳ hạn",
                    9,
                    "253,850,615",
                    "OWNER_DIRECT_GROUP_PARENT",
                ),
                (
                    "DEMAND_DEPOSIT_VND",
                    11,
                    "Bằng VND",
                    12,
                    "213,146,125",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    14,
                    "Bằng vàng và ngoại tệ",
                    15,
                    "40,704,490",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT",
                    17,
                    "Tiền, vàng gửi có kỳ hạn",
                    18,
                    "78,175,536",
                    "OWNER_DIRECT_GROUP_PARENT",
                ),
                (
                    "TERM_DEPOSIT_VND",
                    20,
                    "Bằng VND",
                    21,
                    "66,345,000",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    23,
                    "Bằng vàng và ngoại tệ",
                    24,
                    "11,830,536",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN",
                    26,
                    "Vay các TCTD khác",
                    27,
                    "40,067,852",
                    "OWNER_DIRECT_GROUP_PARENT",
                ),
                (
                    "INTERBANK_LOAN_VND",
                    29,
                    "Bằng VND",
                    30,
                    "20,663,374",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    32,
                    "Bằng vàng và ngoại tệ",
                    33,
                    "19,404,478",
                    "PARENT_CURRENCY_CHILD",
                ),
            ],
            [
                (
                    "DEMAND_VND_PLUS_GOLD_FOREIGN_TO_DEMAND_SUBTOTAL",
                    ((12, "213,146,125"), (15, "40,704,490")),
                    (9, "253,850,615"),
                ),
                (
                    "TERM_VND_PLUS_GOLD_FOREIGN_TO_TERM_SUBTOTAL",
                    ((21, "66,345,000"), (24, "11,830,536")),
                    (18, "78,175,536"),
                ),
                (
                    "LOAN_VND_PLUS_GOLD_FOREIGN_TO_LOAN_SUBTOTAL",
                    ((30, "20,663,374"), (33, "19,404,478")),
                    (27, "40,067,852"),
                ),
                (
                    "DEMAND_PLUS_TERM_PLUS_LOAN_TO_FAMILY_TOTAL",
                    (
                        (9, "253,850,615"),
                        (18, "78,175,536"),
                        (27, "40,067,852"),
                    ),
                    (35, "372,094,003"),
                ),
            ],
        ),
        _positive_document(
            "VIB",
            32,
            "2026-06-30",
            5,
            "TIỀN GỬI VÀ CHO VAY CÁC TCTD KHÁC",
            [
                (
                    "FAMILY_TOTAL",
                    None,
                    None,
                    36,
                    "118.506.345",
                    "OUTER_OWNER_UNLABELED_TRAILING_TOTAL",
                ),
                (
                    "INTERBANK_DEPOSIT_PARENT",
                    None,
                    None,
                    25,
                    "61.739.104",
                    "OWNER_DIRECT_UNLABELED_DEPOSIT_SUBTOTAL",
                ),
                (
                    "DEMAND_DEPOSIT_VND",
                    11,
                    "Bằng VND",
                    12,
                    "454.278",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    14,
                    "Bằng ngoại tệ",
                    15,
                    "592.566",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_VND",
                    21,
                    "Bằng VND",
                    18,
                    "58.850.000",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    22,
                    "Bằng ngoại tệ",
                    23,
                    "1.842.260",
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN",
                    27,
                    "Cho vay các TCTD khác",
                    34,
                    "56.767.241",
                    "OWNER_INTERMEDIATE_PARENT_TRAILING_SUBTOTAL",
                ),
                (
                    "INTERBANK_LOAN_VND",
                    28,
                    "Bằng VND",
                    29,
                    "56.767.241",
                    "PARENT_CURRENCY_CHILD",
                ),
                (
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    31,
                    "Trong đó: chiết khấu, tái chiết khấu",
                    32,
                    "47.474.762",
                    "NON_ADDITIVE_LOAN_DETAIL",
                ),
            ],
            [
                (
                    "FOUR_DEPOSIT_CURRENCY_CHILDREN_TO_DEPOSIT_SUBTOTAL",
                    (
                        (12, "454.278"),
                        (15, "592.566"),
                        (18, "58.850.000"),
                        (23, "1.842.260"),
                    ),
                    (25, "61.739.104"),
                ),
                (
                    "LOAN_VND_TO_LOAN_SUBTOTAL",
                    ((29, "56.767.241"),),
                    (34, "56.767.241"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_TO_FAMILY_TOTAL",
                    ((25, "61.739.104"), (34, "56.767.241")),
                    (36, "118.506.345"),
                ),
            ],
        ),
    ]


def _annual_positive_document(
    bank_code: str,
    page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[Mapping[str, Any]],
    equations: Sequence[tuple[str, Sequence[Mapping[str, Any]], Mapping[str, Any]]],
) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_DETAILED_INTERBANK_DEPOSIT_LOAN_NOTE",
        "equations": [
            {
                "component_values": canonical_clone_v1(list(components)),
                "name": name,
                "visible_total": canonical_clone_v1(total),
            }
            for name, components, total in equations
        ],
        "evidence_owner_line_index": owner_line_index,
        "mappings": canonical_clone_v1(list(rows)),
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": "2025-12-31",
        "unmapped_rows": [],
    }


def _annual_2025_review_documents() -> list[dict[str, Any]]:
    value = _value
    row = _annual_mapping
    acb_loan_vnd_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1288, 1028, 1308, 1047],
            "rgb_sha256": "8eabbe750a3c2320a96f30f0a4b6fea8119006de42f71b92a679c855a20723ac",
        },
    )
    acb_discount_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1288, 1090, 1308, 1108],
            "rgb_sha256": "89b909fb441a223c74641b269f8d5a6913902ebe34b4c482fb11a7adcf4043d6",
        },
    )
    acb_provision_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1288, 1122, 1308, 1140],
            "rgb_sha256": "0c055b8f76237ae480bbf22de4363a80a38e0034eba06038fe964fa0e844ccc6",
        },
    )
    acb_loan_total_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1288, 1184, 1308, 1202],
            "rgb_sha256": "02a8653b4d05ba197cf05d6db8052ff51129e1f941782ff786ce9c33eec405fe",
        },
    )
    hdb_upas_vnd_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1205, 878, 1228, 899],
            "rgb_sha256": "92d3b2d38b635ee51556f17ad293d3ba83d43ff7ee7135082c1a5fef52d5b218",
        },
    )
    vcb_loan_fx_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1147, 1657, 1168, 1675],
            "rgb_sha256": "217eafad68eed1ef04f24ca8a6cb8e7e2021a433fea4bcbe82520bb948b73cb8",
        },
    )
    vcb_provision_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1147, 1815, 1168, 1834],
            "rgb_sha256": "de0230fbb076517a9a80c5e70223179b4df9e8ce4604818dda227e04e5e33fb3",
        },
    )
    vib_loan_fx_dash = value(
        None,
        "-",
        {
            "bbox_raw_pixels": [1210, 880, 1230, 897],
            "rgb_sha256": "68fb7e2abd4507961c9680c18537c673c68797614c0c3162c9c7e2fe6fade189",
        },
    )
    vp_term_vnd = value(32, "131.259.100")
    hdb_loan_total = _fresh_challenged_value(53, "27.921.384", "27.921.364")
    return [
        _annual_positive_document(
            "ACB",
            46,
            5,
            "TIỀN GỬI VÀ CHO VAY CÁC TỔ CHỨC TÍN DỤNG KHÁC",
            [
                row(
                    "FAMILY_TOTAL",
                    44,
                    "Tổng tiền gửi và cho vay các TCTD khác",
                    value(45, "149.990.681"),
                    "OUTER_OWNER_EXPLICIT_TOTAL",
                ),
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    12,
                    "Tiền gửi tại các TCTD khác",
                    value(32, "149.990.681"),
                    "EXPLICIT_LABELED_DEPOSIT_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT",
                    13,
                    "Tiền gửi không kỳ hạn",
                    value(20, "29.984.900"),
                    "PARENT_TRAILING_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    14,
                    "Bằng Đồng Việt Nam",
                    value(15, "22.160.438"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    17,
                    "Bằng ngoại tệ",
                    value(18, "7.824.462"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT",
                    22,
                    "Tiền gửi có kỳ hạn (i)",
                    value(29, "120.005.781"),
                    "PARENT_TRAILING_SUBTOTAL",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    23,
                    "Bằng Đồng Việt Nam",
                    value(24, "107.959.785"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    26,
                    "Bằng ngoại tệ",
                    value(27, "12.045.996"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    34,
                    "Cho vay các TCTD khác",
                    acb_loan_total_dash,
                    "EXPLICIT_LABELED_LOAN_SUBTOTAL_VISIBLE_DASH",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    35,
                    "Bằng Đồng Việt Nam",
                    acb_loan_vnd_dash,
                    "PARENT_CURRENCY_CHILD_VISIBLE_DASH",
                ),
                row(
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    38,
                    "Chiết khấu, tái chiết khấu",
                    acb_discount_dash,
                    "NON_ADDITIVE_DETAIL_VISIBLE_DASH",
                ),
                row(
                    "INTERBANK_LOAN_PROVISION",
                    40,
                    "Dự phòng rủi ro cho vay các TCTD khác",
                    acb_provision_dash,
                    "LOAN_PROVISION_VISIBLE_DASH",
                ),
            ],
            [
                (
                    "DEMAND_CURRENCIES_TO_DEMAND_SUBTOTAL",
                    [value(15, "22.160.438"), value(18, "7.824.462")],
                    value(20, "29.984.900"),
                ),
                (
                    "TERM_CURRENCIES_TO_TERM_SUBTOTAL",
                    [value(24, "107.959.785"), value(27, "12.045.996")],
                    value(29, "120.005.781"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    [value(20, "29.984.900"), value(29, "120.005.781")],
                    value(32, "149.990.681"),
                ),
                (
                    "LOAN_VND_PLUS_PROVISION_TO_LOAN_SUBTOTAL",
                    [acb_loan_vnd_dash, acb_provision_dash],
                    acb_loan_total_dash,
                ),
                (
                    "DEPOSIT_PLUS_LOAN_TO_FAMILY_TOTAL",
                    [value(32, "149.990.681"), acb_loan_total_dash],
                    value(45, "149.990.681"),
                ),
            ],
        ),
        _annual_positive_document(
            "MBB",
            48,
            10,
            "TIỀN GỬI VÀ CHO VAY CÁC TCTD KHÁC",
            [
                row(
                    "FAMILY_TOTAL",
                    None,
                    None,
                    value(48, "182.923.726"),
                    "OUTER_OWNER_UNLABELED_TRAILING_TOTAL",
                ),
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    15,
                    "Tiền gửi tại các TCTD khác",
                    value(16, "165.819.028"),
                    "INLINE_PARENT_TOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT",
                    18,
                    "Tiền gửi không kỳ hạn",
                    value(19, "14.315.078"),
                    "PARENT_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    21,
                    "Bằng VND",
                    value(22, "4.492.129"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    24,
                    "Bằng ngoại tệ",
                    value(25, "9.822.949"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT",
                    27,
                    "Tiền gửi có kỳ hạn",
                    value(28, "151.503.950"),
                    "PARENT_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    30,
                    "Bằng VND",
                    value(31, "148.618.970"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    33,
                    "Bằng ngoại tệ",
                    value(34, "2.884.980"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    36,
                    "Cho vay các TCTD khác",
                    value(37, "17.113.794"),
                    "INLINE_PARENT_TOTAL",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    39,
                    "Bằng VND",
                    value(40, "15.025.322"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    42,
                    "Bằng ngoại tệ",
                    value(43, "2.088.472"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TOTAL_INTERBANK_PROVISION",
                    45,
                    "Dự phòng rủi ro",
                    value(46, "(9.096)"),
                    "FAMILY_LEVEL_PROVISION",
                    graph_role="INTERBANK_LOAN_PROVISION",
                ),
            ],
            [
                (
                    "DEMAND_CURRENCIES_TO_DEMAND_SUBTOTAL",
                    [value(22, "4.492.129"), value(25, "9.822.949")],
                    value(19, "14.315.078"),
                ),
                (
                    "TERM_CURRENCIES_TO_TERM_SUBTOTAL",
                    [value(31, "148.618.970"), value(34, "2.884.980")],
                    value(28, "151.503.950"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    [value(19, "14.315.078"), value(28, "151.503.950")],
                    value(16, "165.819.028"),
                ),
                (
                    "LOAN_CURRENCIES_TO_LOAN_SUBTOTAL",
                    [value(40, "15.025.322"), value(43, "2.088.472")],
                    value(37, "17.113.794"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_PLUS_PROVISION_TO_FAMILY_TOTAL",
                    [value(16, "165.819.028"), value(37, "17.113.794"), value(46, "(9.096)")],
                    value(48, "182.923.726"),
                ),
            ],
        ),
        _annual_positive_document(
            "VPB",
            42,
            5,
            "TIỀN GỬI VÀ CẤP TÍN DỤNG CHO CÁC TỔ CHỨC TÍN DỤNG KHÁC",
            [
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    7,
                    "Tiền gửi tại các TCTD khác",
                    value(38, "178.800.339"),
                    "TRAILING_DEPOSIT_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT",
                    15,
                    "Tiền gửi không kỳ hạn",
                    value(16, "12.195.493"),
                    "PARENT_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    19,
                    "Bằng VND",
                    value(20, "9.603.896"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    23,
                    "Bằng ngoại tệ",
                    value(24, "2.591.597"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT",
                    27,
                    "Tiền gửi có kỳ hạn",
                    value(28, "166.604.846"),
                    "PARENT_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    31,
                    "Bằng VND",
                    vp_term_vnd,
                    "PARENT_CURRENCY_CHILD_CHALLENGED_TEXT",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    35,
                    "Bằng ngoại tệ",
                    value(36, "35.345.746"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    41,
                    "Cấp tín dụng cho các TCTD khác",
                    value(54, "7.428.599"),
                    "TRAILING_LOAN_SUBTOTAL",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    48,
                    "Bằng VND",
                    value(49, "7.428.599"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    51,
                    "Trong đó: chiết khấu, tái chiết khấu",
                    value(52, "5.324.990"),
                    "NON_ADDITIVE_DETAIL",
                ),
            ],
            [
                (
                    "DEMAND_CURRENCIES_TO_DEMAND_SUBTOTAL",
                    [value(20, "9.603.896"), value(24, "2.591.597")],
                    value(16, "12.195.493"),
                ),
                (
                    "TERM_CURRENCIES_TO_TERM_SUBTOTAL",
                    [vp_term_vnd, value(36, "35.345.746")],
                    value(28, "166.604.846"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    [value(16, "12.195.493"), value(28, "166.604.846")],
                    value(38, "178.800.339"),
                ),
                ("LOAN_VND_TO_LOAN_SUBTOTAL", [value(49, "7.428.599")], value(54, "7.428.599")),
            ],
        ),
        _annual_positive_document(
            "HDB",
            34,
            8,
            "TIỀN GỬI VÀ CHO VAY CÁC TCTD KHÁC",
            [
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    10,
                    "Tiền gửi tại các TCTD khác",
                    value(33, "156.340.825"),
                    "TRAILING_DEPOSIT_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT",
                    15,
                    "Tiền gửi không kỳ hạn",
                    value(16, "31.362.169"),
                    "PARENT_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    18,
                    "Bằng VND",
                    value(19, "2.307.744"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    21,
                    "Bằng ngoại tệ",
                    value(22, "29.054.425"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT",
                    24,
                    "Tiền gửi có kỳ hạn",
                    value(25, "124.978.656"),
                    "PARENT_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    27,
                    "Bằng VND",
                    value(28, "119.100.000"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    30,
                    "Bằng ngoại tệ",
                    value(31, "5.878.656"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    36,
                    "Cho vay các TCTD khác",
                    hdb_loan_total,
                    "TRAILING_LOAN_SUBTOTAL_CHALLENGED_TEXT",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    48,
                    "Bằng VND",
                    value(49, "27.921.384"),
                    "POSITIVE_VND_COMPONENT_WITH_ZERO_UPAS_COMPONENT",
                ),
                row(
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    51,
                    "Trong đó: Chiết khấu, tái chiết khấu",
                    value(52, "4.216.686"),
                    "NON_ADDITIVE_DETAIL",
                ),
            ],
            [
                (
                    "DEMAND_CURRENCIES_TO_DEMAND_SUBTOTAL",
                    [value(19, "2.307.744"), value(22, "29.054.425")],
                    value(16, "31.362.169"),
                ),
                (
                    "TERM_CURRENCIES_TO_TERM_SUBTOTAL",
                    [value(28, "119.100.000"), value(31, "5.878.656")],
                    value(25, "124.978.656"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    [value(16, "31.362.169"), value(25, "124.978.656")],
                    value(33, "156.340.825"),
                ),
                (
                    "ZERO_UPAS_VND_PLUS_OTHER_VND_TO_LOAN_SUBTOTAL",
                    [hdb_upas_vnd_dash, value(49, "27.921.384")],
                    hdb_loan_total,
                ),
            ],
        ),
        _annual_positive_document(
            "VCB",
            36,
            38,
            "Tiền gửi và cho vay các tổ chức tín dụng khác",
            [
                row(
                    "FAMILY_TOTAL",
                    None,
                    None,
                    value(68, "522.474.362"),
                    "UNLABELED_TRAILING_FAMILY_TOTAL",
                ),
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    43,
                    "Tiền gửi tại các tổ chức tín dụng khác",
                    value(56, "515.588.640"),
                    "TRAILING_DEPOSIT_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    44,
                    "Tiền gửi không kỳ hạn bằng VND",
                    value(45, "151.960.460"),
                    "FLATTENED_PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    47,
                    "Tiền gửi không kỳ hạn bằng ngoại tệ",
                    value(48, "99.414.101"),
                    "FLATTENED_PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    50,
                    "Tiền gửi có kỳ hạn bằng VND",
                    value(51, "170.402.161"),
                    "FLATTENED_PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    53,
                    "Tiền gửi có kỳ hạn bằng ngoại tệ",
                    value(54, "93.811.918"),
                    "FLATTENED_PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    58,
                    "Cho vay các tổ chức tín dụng khác",
                    value(64, "6.885.722"),
                    "TRAILING_GROSS_LOAN_SUBTOTAL",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    59,
                    "Cho vay bằng VND",
                    value(60, "6.885.722"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    62,
                    "Cho vay bằng ngoại tệ",
                    vcb_loan_fx_dash,
                    "PARENT_CURRENCY_CHILD_VISIBLE_DASH",
                ),
                row(
                    "TOTAL_INTERBANK_PROVISION",
                    66,
                    "Dự phòng rủi ro",
                    vcb_provision_dash,
                    "FAMILY_LEVEL_PROVISION_VISIBLE_DASH",
                    graph_role="INTERBANK_LOAN_PROVISION",
                ),
            ],
            [
                (
                    "FOUR_DEPOSIT_CURRENCY_ROWS_TO_DEPOSIT_SUBTOTAL",
                    [
                        value(45, "151.960.460"),
                        value(48, "99.414.101"),
                        value(51, "170.402.161"),
                        value(54, "93.811.918"),
                    ],
                    value(56, "515.588.640"),
                ),
                (
                    "LOAN_CURRENCIES_TO_GROSS_LOAN_SUBTOTAL",
                    [value(60, "6.885.722"), vcb_loan_fx_dash],
                    value(64, "6.885.722"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_PLUS_PROVISION_TO_FAMILY_TOTAL",
                    [value(56, "515.588.640"), value(64, "6.885.722"), vcb_provision_dash],
                    value(68, "522.474.362"),
                ),
            ],
        ),
        _annual_positive_document(
            "CTG",
            40,
            5,
            'TIỀN GỬI VÀ CHO VAY CÁC TỔ CHỨC TÍN DỤNG ("TCTD") KHÁC',
            [
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    7,
                    "Tiền gửi tại các TCTD khác",
                    value(30, "463.381.166"),
                    "TRAILING_DEPOSIT_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT",
                    12,
                    "Tiền gửi không kỳ hạn",
                    value(13, "308.518.041"),
                    "PARENT_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    15,
                    "Bằng VND",
                    value(16, "174.853.579"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    18,
                    "Bằng ngoại tệ",
                    value(19, "133.664.462"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT",
                    21,
                    "Tiền gửi có kỳ hạn",
                    value(22, "154.863.125"),
                    "PARENT_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    24,
                    "Bằng VND",
                    value(25, "78.950.830"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    27,
                    "Bằng ngoại tệ",
                    value(28, "75.912.295"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    33,
                    "Cho vay các TCTD khác",
                    value(44, "13.106.364"),
                    "TRAILING_LOAN_SUBTOTAL",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    38,
                    "Bằng VND",
                    value(39, "4.222.473"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    41,
                    "Bằng ngoại tệ",
                    value(42, "8.883.891"),
                    "PARENT_CURRENCY_CHILD",
                ),
            ],
            [
                (
                    "DEMAND_CURRENCIES_TO_DEMAND_SUBTOTAL",
                    [value(16, "174.853.579"), value(19, "133.664.462")],
                    value(13, "308.518.041"),
                ),
                (
                    "TERM_CURRENCIES_TO_TERM_SUBTOTAL",
                    [value(25, "78.950.830"), value(28, "75.912.295")],
                    value(22, "154.863.125"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    [value(13, "308.518.041"), value(22, "154.863.125")],
                    value(30, "463.381.166"),
                ),
                (
                    "LOAN_CURRENCIES_TO_LOAN_SUBTOTAL",
                    [value(39, "4.222.473"), value(42, "8.883.891")],
                    value(44, "13.106.364"),
                ),
            ],
        ),
        _annual_positive_document(
            "BID",
            39,
            55,
            "TIỀN GỬI TẠI VÀ CHO VAY CÁC TCTD KHÁC",
            [
                row(
                    "FAMILY_TOTAL",
                    None,
                    None,
                    value(107, "457.353.489"),
                    "UNLABELED_TRAILING_FAMILY_TOTAL",
                ),
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    64,
                    "Tiền gửi tại các TCTD khác",
                    value(65, "443.325.963"),
                    "INLINE_PARENT_TOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT",
                    68,
                    "Tiền gửi không kỳ hạn",
                    value(69, "272.401.942"),
                    "PARENT_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    72,
                    "Bằng VND",
                    value(73, "190.354.397"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    75,
                    "Bằng ngoại tệ",
                    value(76, "82.047.545"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT",
                    79,
                    "Tiền gửi có kỳ hạn",
                    value(80, "170.924.021"),
                    "PARENT_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    82,
                    "Bằng VND",
                    value(83, "158.660.808"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    85,
                    "Bằng ngoại tệ",
                    value(86, "12.263.213"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    89,
                    "Cho vay các TCTD khác",
                    value(90, "14.090.848"),
                    "INLINE_PARENT_TOTAL",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    92,
                    "Bằng VND",
                    value(93, "12.534.844"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    96,
                    "Bằng ngoại tệ",
                    value(97, "1.556.004"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "TOTAL_INTERBANK_PROVISION",
                    101,
                    "Dự phòng rủi ro tiền gửi và cho vay các TCTD",
                    value(102, "(63.322)"),
                    "FAMILY_LEVEL_PROVISION",
                    graph_role="INTERBANK_LOAN_PROVISION",
                ),
            ],
            [
                (
                    "DEMAND_CURRENCIES_TO_DEMAND_SUBTOTAL",
                    [value(73, "190.354.397"), value(76, "82.047.545")],
                    value(69, "272.401.942"),
                ),
                (
                    "TERM_CURRENCIES_TO_TERM_SUBTOTAL",
                    [value(83, "158.660.808"), value(86, "12.263.213")],
                    value(80, "170.924.021"),
                ),
                (
                    "DEMAND_PLUS_TERM_TO_DEPOSIT_SUBTOTAL",
                    [value(69, "272.401.942"), value(80, "170.924.021")],
                    value(65, "443.325.963"),
                ),
                (
                    "LOAN_CURRENCIES_TO_LOAN_SUBTOTAL",
                    [value(93, "12.534.844"), value(97, "1.556.004")],
                    value(90, "14.090.848"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_PLUS_PROVISION_TO_FAMILY_TOTAL",
                    [value(65, "443.325.963"), value(90, "14.090.848"), value(102, "(63.322)")],
                    value(107, "457.353.489"),
                ),
            ],
        ),
        _annual_positive_document(
            "VIB",
            36,
            5,
            "TIỀN GỬI VÀ CHO VAY CÁC TCTD KHÁC",
            [
                row(
                    "FAMILY_TOTAL",
                    None,
                    None,
                    value(36, "104.411.120"),
                    "UNLABELED_TRAILING_FAMILY_TOTAL",
                ),
                row(
                    "INTERBANK_DEPOSIT_PARENT",
                    None,
                    None,
                    value(23, "59.469.540"),
                    "OWNER_DIRECT_UNLABELED_DEPOSIT_SUBTOTAL",
                ),
                row(
                    "DEMAND_DEPOSIT_VND",
                    11,
                    "Bằng VND",
                    value(12, "678.429"),
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                row(
                    "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                    14,
                    "Bằng ngoại tệ",
                    value(15, "670.818"),
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_VND",
                    18,
                    "Bằng VND",
                    value(19, "55.360.000"),
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                row(
                    "TERM_DEPOSIT_FOREIGN_CURRENCY",
                    21,
                    "Bằng ngoại tệ",
                    value(22, "2.760.293"),
                    "DEPOSIT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN",
                    25,
                    "Cho vay các TCTD khác",
                    value(34, "44.941.580"),
                    "TRAILING_LOAN_SUBTOTAL",
                ),
                row(
                    "INTERBANK_LOAN_VND",
                    26,
                    "Bằng VND",
                    value(27, "44.941.580"),
                    "PARENT_CURRENCY_CHILD",
                ),
                row(
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    29,
                    "Trong đó: chiết khấu, tái chiết khấu",
                    value(30, "35.351.374"),
                    "NON_ADDITIVE_DETAIL",
                ),
                row(
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    33,
                    "Bằng ngoại tệ",
                    vib_loan_fx_dash,
                    "PARENT_CURRENCY_CHILD_VISIBLE_DASH",
                ),
            ],
            [
                (
                    "FOUR_DEPOSIT_CURRENCY_ROWS_TO_DEPOSIT_SUBTOTAL",
                    [
                        value(12, "678.429"),
                        value(15, "670.818"),
                        value(19, "55.360.000"),
                        value(22, "2.760.293"),
                    ],
                    value(23, "59.469.540"),
                ),
                (
                    "LOAN_CURRENCIES_TO_LOAN_SUBTOTAL",
                    [value(27, "44.941.580"), vib_loan_fx_dash],
                    value(34, "44.941.580"),
                ),
                (
                    "DEPOSIT_PLUS_LOAN_TO_FAMILY_TOTAL",
                    [value(23, "59.469.540"), value(34, "44.941.580")],
                    value(36, "104.411.120"),
                ),
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
            "review_run_id": "E-0062",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0062:pixel-review:" + canonical_json_sha256_v1(material)}


def _annual_2025_review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": ANNUAL_2025_CLAIM_BOUNDARY,
        "documents": _annual_2025_review_documents(),
        "format_version": ANNUAL_2025_REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0109-ANNUAL-2025",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
        "semantic_axis_sha256": ANNUAL_2025_EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": ANNUAL_2025_EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0109:pixel-review:" + canonical_json_sha256_v1(material)}


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
            "result_id_prefix": "idl8bcv1:result:",
            "result_path": RESULT_PATH,
            "review_blueprint": _review_blueprint,
            "review_path": REVIEW_PATH,
            "scan_id": EXPECTED_SCAN_ID,
            "state": "INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_VERIFICATION_COMPLETE",
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
            "result_id_prefix": "annual2025idl8bcv1:result:",
            "result_path": ANNUAL_2025_RESULT_PATH,
            "review_blueprint": _annual_2025_review_blueprint,
            "review_path": ANNUAL_2025_REVIEW_PATH,
            "scan_id": ANNUAL_2025_EXPECTED_SCAN_ID,
            "state": "ANNUAL_2025_INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_VERIFICATION_COMPLETE",
        }
    raise _error("interbank deposit/loan mapping profile is unsupported")


def _review(value: Any, profile_name: str = "wave1-2026") -> dict[str, Any]:
    expected = _profile(profile_name)["review_blueprint"]()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex interbank deposit/loan pixel review differs from fixed ledger")
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
    expected_parent = _SCHEMA_PARENT.get(role)
    if (
        item is None
        or schema_id is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.parent_id != expected_parent
    ):
        raise _error("reviewed mapping does not bind one exact live interbank TM item")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _region_event(
    region: Mapping[str, Any],
    role: str,
    *,
    label_line_index: int | None = None,
    value_line_index: int | None = None,
) -> dict[str, Any]:
    events = region.get("events")
    if type(events) is not list:
        raise _error("interbank deposit/loan graph event axis drifted")
    matches = [event for event in events if type(event) is dict and event.get("role") == role]
    if label_line_index is not None:
        matches = [event for event in matches if event.get("source_line_index") == label_line_index]
    if value_line_index is not None:
        matches = [
            event
            for event in matches
            if value_line_index
            in {
                item.get("source_line_index")
                for item in event.get("value_proposals", [])
                if type(item) is dict
            }
        ]
    if len(matches) != 1:
        raise _error(f"interbank deposit/loan graph does not contain one exact role {role}")
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
    if value.get("pixel_binding") is not None or type(value.get("line_index")) is not int:
        raise _error("ordinary source value unexpectedly uses pixel-only binding")
    try:
        return support._source_value(
            axis_page,
            semantic_page,
            crop_page,
            source_texts,
            {
                "line_index": value["line_index"],
                "pixel_transcription": value["pixel_transcription"],
            },
        )
    except Exception as exc:
        raise _error(f"interbank deposit/loan source numeric evidence drifted: {exc}") from exc


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
        "source_numeric_challenger_status": "MATCHES_INDEPENDENT_PIXEL_TRANSCRIPTION",
    }


def _render_bytes(crop_page: Mapping[str, Any]) -> bytes:
    binding = crop_page.get("render_binding")
    if (
        type(binding) is not dict
        or type(binding.get("path")) is not str
        or type(binding.get("size_bytes")) is not int
    ):
        raise _error("visible page render binding drifted")
    expected = _sha256(binding.get("sha256"), "visible page render")
    payload = support._stable_bytes(Path(binding["path"]))
    if len(payload) != binding["size_bytes"] or hashlib.sha256(payload).hexdigest() != expected:
        raise _error("visible page render bytes drifted")
    return payload


def _dash_source_value(value: Mapping[str, Any], render_bytes: bytes) -> dict[str, Any]:
    binding = value.get("pixel_binding")
    if (
        value.get("line_index") is not None
        or value.get("pixel_transcription") != "-"
        or type(binding) is not dict
        or set(binding) != {"bbox_raw_pixels", "rgb_sha256"}
        or type(binding["bbox_raw_pixels"]) is not list
        or len(binding["bbox_raw_pixels"]) != 4
        or any(type(item) is not int for item in binding["bbox_raw_pixels"])
    ):
        raise _error("pixel-only DASH evidence shape drifted")
    bbox = binding["bbox_raw_pixels"]
    if bbox[0] < 0 or bbox[1] < 0 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise _error("pixel-only DASH bbox drifted")
    try:
        image = Image.open(BytesIO(render_bytes))
        image.load()
        rgb = image.convert("RGB")
    except Exception as exc:
        raise _error("visible page render is not one decodable image") from exc
    if bbox[2] > rgb.width or bbox[3] > rgb.height:
        raise _error("pixel-only DASH bbox exceeds visible page")
    digest = hashlib.sha256(rgb.crop(tuple(bbox)).tobytes()).hexdigest()
    if digest != _sha256(binding["rgb_sha256"], "pixel-only DASH crop"):
        raise _error("pixel-only DASH crop bytes drifted")
    return {
        "fresh_vietocr_numeric_proposal": None,
        "normalized_value": 0,
        "pixel_binding": canonical_clone_v1(binding),
        "pixel_transcription": "-",
        "source_cell_status": "DASH",
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": "NO_TEXT_GEOMETRY_VISIBLE_PIXEL_DASH",
    }


def _resolved_source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
    render_bytes: bytes | None,
) -> tuple[dict[str, Any], bytes | None]:
    if value.get("pixel_binding") is not None or value.get("line_index") is None:
        if render_bytes is None:
            render_bytes = _render_bytes(crop_page)
        return _dash_source_value(value, render_bytes), render_bytes
    return (
        _source_value(axis_page, semantic_page, crop_page, source_texts, value),
        render_bytes,
    )


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
        raise _error("interbank deposit/loan mapping result fields drifted")
    if (
        value["format_version"] != profile["format_version"]
        or value["claim_boundary"] != profile["claim_boundary"]
        or value["state"] != profile["state"]
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("interbank deposit/loan mapping result identity or metrics drifted")
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
            raise _error("interbank deposit/loan mapping trial shape drifted")
        for mapping in trial["verified_mappings"]:
            if type(mapping) is not dict or mapping.get("status") != "VERIFIED_BY_CODEX":
                raise _error("interbank deposit/loan mapped row status drifted")
        for unresolved in trial["unmapped_source_rows"]:
            if (
                type(unresolved) is not dict
                or unresolved.get("status") != "UNRESOLVED_SCHEMA_ITEM_ABSENT"
            ):
                raise _error("interbank deposit/loan unmapped source row status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != profile["result_id_prefix"] + canonical_json_sha256_v1(material):
        raise _error("interbank deposit/loan mapping result identity drifted")
    return canonical_clone_v1(value)


def build_interbank_deposits_loans_8bank_codex_verified_mapping_v1(
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
    """Build the exact eight-bank bounded interbank deposit/loan mapping result."""

    profile = _profile(_profile_name)
    review = _review(review_value, _profile_name)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != profile["axis_sha256"]
        or structure_scan.get("scan_id") != profile["scan_id"]
        or structure_scan.get("state")
        != "FULL_DOCUMENT_INTERBANK_DEPOSIT_LOAN_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("interbank deposit/loan input authority drifted")
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
            raise _error("whole-PDF interbank deposit/loan scan identity drifted")
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
                raise _error("negative interbank deposit/loan disposition drifted")
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
            raise _error("whole-PDF interbank deposit/loan region is not exactly unique")
        region = matcher["regions"][0]
        axes = region.get("layout", {}).get("meaningful_axes", {})
        if (
            region.get("page_sequence") != page_number
            or axes.get("unit_header_count", 0) < 1
            or axes.get("period_header_count", 0) < 2
            or region.get("owner", {}).get("source_line_index")
            != reviewed["evidence_owner_line_index"]
        ):
            raise _error("reviewed page/layout disagrees with generic interbank graph")
        semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
        crop_page = _page_by_number(crop_document, page_number, "crop manifest")
        try:
            source_texts = _source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"interbank deposit/loan source line axis drifted: {exc}") from exc
        render_bytes: bytes | None = None
        mapped_rows = []
        for row in reviewed["mappings"]:
            role = row["role"]
            graph_role = row.get("graph_role", role)
            label_index = row["label_line_index"]
            value_index = row["value"]["line_index"]
            event = _region_event(
                region,
                graph_role,
                label_line_index=label_index,
                value_line_index=value_index,
            )
            match_kind = None
            if label_index is None:
                if (
                    row["label_pixel_transcription"] is not None
                    or event.get("source_line_index") is not None
                    and graph_role not in {"FAMILY_TOTAL", "INTERBANK_DEPOSIT_PARENT"}
                ):
                    raise _error("unlabeled graph event acquired a fabricated label")
            else:
                if type(label_index) is not int or event.get("source_line_index") != label_index:
                    raise _error("interbank graph/review label binding drifted")
                match_kind = _anchor_match(
                    _axis_line(axis_page, label_index)["vietocr_text"],
                    row["label_pixel_transcription"],
                    role,
                )
            if value_index is None:
                allowed_dash_roles = {
                    "INTERBANK_DEPOSIT_PROVISION",
                    "INTERBANK_LOAN",
                    "INTERBANK_LOAN_DISCOUNT_REDISCOUNT",
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_PROVISION",
                    "INTERBANK_LOAN_VND",
                    "TOTAL_INTERBANK_PROVISION",
                }
                if role not in allowed_dash_roles or (
                    _profile_name == "wave1-2026" and event.get("value_proposals")
                ):
                    raise _error("pixel-only DASH is outside an exact empty graph row")
                source_value, render_bytes = _resolved_source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    row["value"],
                    render_bytes,
                )
            else:
                if value_index not in {
                    item["source_line_index"] for item in event.get("value_proposals", [])
                }:
                    raise _error("reviewed value is outside the graph-bound row")
                source_value, render_bytes = _resolved_source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    row["value"],
                    render_bytes,
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
            components = []
            for item in equation["component_values"]:
                component, render_bytes = _resolved_source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    item,
                    render_bytes,
                )
                components.append(component)
            total, render_bytes = _resolved_source_value(
                axis_page,
                semantic_page,
                crop_page,
                source_texts,
                equation["visible_total"],
                render_bytes,
            )
            computed = sum(item["normalized_value"] for item in components)
            if computed != total["normalized_value"]:
                raise _error(f"interbank deposit/loan equation does not close: {code}")
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
            else (
                "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                if reviewed["source_period"] == "2026-03-31"
                else "VERIFIED_SOURCE_PERIOD_Q2_2026"
            )
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
        {**material, "result_id": profile["result_id_prefix"] + canonical_json_sha256_v1(material)},
        _profile_name,
    )


def validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1(
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
    structure_scan = scanner.build_interbank_deposits_loans_full_document_scan_v1(semantic_index)
    expected = build_interbank_deposits_loans_8bank_codex_verified_mapping_v1(
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
        raise _error("interbank deposit/loan mapping does not replay exactly")
    return persisted


def validate_annual_2025_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1(
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

    return validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1(
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
    structure_scan = scanner.build_interbank_deposits_loans_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_interbank_deposits_loans_8bank_codex_verified_mapping_v1(
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
    return validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1(
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


def build_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Read only the fixed wave-1 inputs and build the verified result."""

    return _build_live("wave1-2026")


def build_live_annual_2025_interbank_deposits_loans_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    """Read only the fixed annual-2025 inputs and build the verified result."""

    return _build_live("annual-2025")


def _validate_live(value: Any, profile_name: str) -> dict[str, Any]:
    profile = _profile(profile_name)

    semantic_index, _ = _stable_json(profile["index_path"], profile["index_sha256"])
    crop_manifest, crop_sha = _stable_json(
        profile["crop_manifest_path"], profile["crop_manifest_sha256"]
    )
    review, review_sha = _stable_json(profile["review_path"])
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1(
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


def validate_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    """Replay one wave-1 result only from the fixed live trust roots."""

    return _validate_live(value, "wave1-2026")


def validate_live_annual_2025_interbank_deposits_loans_8bank_codex_verified_mapping_v1(
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
