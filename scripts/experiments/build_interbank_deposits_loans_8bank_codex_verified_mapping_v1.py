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
    "build_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
    "build_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
    "validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1",
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


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
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


def _region_event(region: Mapping[str, Any], role: str) -> dict[str, Any]:
    events = region.get("events")
    if type(events) is not list:
        raise _error("interbank deposit/loan graph event axis drifted")
    matches = [event for event in events if type(event) is dict and event.get("role") == role]
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


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("interbank deposit/loan mapping result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_VERIFICATION_COMPLETE"
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
    if identity != "idl8bcv1:result:" + canonical_json_sha256_v1(material):
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
) -> dict[str, Any]:
    """Build the exact eight-bank bounded interbank deposit/loan mapping result."""

    review = _review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
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
            source_texts = support._source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"interbank deposit/loan source line axis drifted: {exc}") from exc
        render_bytes: bytes | None = None
        mapped_rows = []
        for row in reviewed["mappings"]:
            role = row["role"]
            event = _region_event(region, role)
            label_index = row["label_line_index"]
            match_kind = None
            if label_index is None:
                if (
                    row["label_pixel_transcription"] is not None
                    or event.get("source_line_index") is not None
                    and role not in {"FAMILY_TOTAL", "INTERBANK_DEPOSIT_PARENT"}
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
            value_index = row["value"]["line_index"]
            if value_index is None:
                if role not in {
                    "INTERBANK_DEPOSIT_PROVISION",
                    "INTERBANK_LOAN_FOREIGN_CURRENCY",
                    "INTERBANK_LOAN_PROVISION",
                } or event.get("value_proposals"):
                    raise _error("pixel-only DASH is outside an exact empty graph row")
                if render_bytes is None:
                    render_bytes = _render_bytes(crop_page)
                source_value = _dash_source_value(row["value"], render_bytes)
            else:
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
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
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
        "state": "INTERBANK_DEPOSITS_LOANS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "idl8bcv1:result:" + canonical_json_sha256_v1(material)}
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
) -> dict[str, Any]:
    """Exact-rebuild structure, numeric, accounting and schema decisions."""

    persisted = _validate_result(value)
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
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("interbank deposit/loan mapping does not replay exactly")
    return persisted


def build_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Read only the fixed live inputs and build the verified result."""

    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256:
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
    )


def validate_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    """Replay one persisted result only from the fixed live trust roots."""

    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
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
    )


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review and args.validate is not None:
        parser.error("--write-review and --validate are mutually exclusive")
    if args.write_review:
        args.output.write_bytes(canonical_json_bytes_v1(_review_blueprint()))
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        result = validate_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1(value)
        sys.stdout.write(result["result_id"] + "\n")
        return
    result = build_live_interbank_deposits_loans_8bank_codex_verified_mapping_v1()
    args.output.write_bytes(canonical_json_bytes_v1(result))
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    _main()
