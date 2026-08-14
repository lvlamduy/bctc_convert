"""Verify and map the eight-bank customer-deposit note family.

The complete-PDF detector remains bank blind.  This bounded post-scan review
binds each unique region to the visible page/crop evidence, selects the current
reporting-period and meaningful monetary axes, checks parent/currency and table
totals, and maps only exact live TM-schema rows.  Bank identity is used solely
to join fixed source documents to their independently reviewed evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

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
    "CustomerDeposit8BankCodexVerifiedMappingV1Error",
    "build_customer_deposit_8bank_codex_verified_mapping_v1",
    "build_live_customer_deposit_8bank_codex_verified_mapping_v1",
    "validate_customer_deposit_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "CUSTOMER_DEPOSIT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CUSTOMER_DEPOSIT_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_CUSTOMER_DEPOSIT_"
    "BOUNDARY_LAYOUT_PERIOD_CURRENCY_STRUCTURE_PLUS_INDEPENDENT_VISIBLE_PIXEL_"
    "UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0058-customer-deposit-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0058-customer-deposit-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "cdfdsv1:scan:31a5c2f86cdcc4a30cd6b45c8974edb09ba0ce305dfdc7a8eb7ab74664c4094e"

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "VISIBLE_CONSOLIDATED_REPORT_SCOPE",
    "CUSTOMER_DEPOSIT_OWNER_AND_CLUSTER_BOUNDARIES",
    "FIRST_AND_LAST_CLUSTER_ITEMS_IN_PDF_ORDER",
    "HORIZONTAL_VERTICAL_OR_MIXED_LAYOUT",
    "CURRENT_PERIOD_AXIS_ONLY",
    "MEANINGFUL_MONETARY_COLUMNS_ONLY",
    "PARENT_PRECEDES_CHILD",
    "VISIBLE_PIXEL_DIGITS",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "PARENT_EQUALS_CURRENCY_CHILDREN_WHEN_DISCLOSED",
    "SOURCE_OWNER_OR_SUBTABLE_TOTAL_CLOSES",
    "PERCENT_COLUMNS_EXCLUDED_FROM_MONEY_MAPPING",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": ("VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER_AND_ACCOUNTING"),
    "old_ocr_used_as_semantic_anchor": False,
    "percentage_axis_mapped_as_money": False,
    "source_order_and_cluster_boundaries_required": True,
    "total_columns_used_as_duplicate_mapped_values": False,
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
    "mapping_authority_bounded_to_reviewed_customer_deposit_rows": True,
    "percentage_columns_used_only_as_checks": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_mapping": False,
    "total_columns_used_only_as_accounting_checks": True,
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
_HEX = set("0123456789abcdef")
_MONEY = re.compile(r"^[0-9][0-9.,]*$")


class CustomerDeposit8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel ledger, accounting, or live schema drifted."""


def _error(message: str) -> CustomerDeposit8BankCodexVerifiedMappingV1Error:
    return CustomerDeposit8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _relative_parts(path: Path) -> tuple[str, ...]:
    if not isinstance(path, Path) or path.is_absolute() or not path.parts:
        raise _error(f"fixed path is not one safe relative path: {path}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"fixed path escapes the project root: {path}")
    return tuple(path.parts)


def _stable_bytes(path: Path) -> bytes:
    parts = _relative_parts(path)
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise _error(f"fixed artifact is not a regular file: {path}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_size,
            item.st_mtime_ns,
        )

    if identity(before) != identity(after):
        raise _error(f"fixed artifact changed while reading: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise _error(f"fixed artifact read was incomplete: {path}")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} root is not one object")
    return value


def _fixed_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], bytes]:
    payload = _stable_bytes(path)
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    return _strict_json(payload, path.as_posix()), payload


def _scanner() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/scan_customer_deposit_full_document_vietocr_v1.py"
    spec = importlib.util.spec_from_file_location("customer_deposit_scan_for_e0058", path)
    if spec is None or spec.loader is None:
        raise _error("cannot load customer-deposit full-document scanner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _value(line_index: int, transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": transcription}


def _mapping(
    report_norm_id: int,
    role: str,
    page: int,
    label: str,
    label_lines: Sequence[int],
    values: Sequence[Mapping[str, Any]],
    *,
    aggregation: str = "DIRECT_VISIBLE_VALUE",
    section: str = "TYPE_AND_CURRENCY",
    additivity: str = "ADDITIVE_WITHIN_DECLARED_SOURCE_EQUATION",
) -> dict[str, Any]:
    return {
        "additivity": additivity,
        "aggregation": aggregation,
        "label_line_indices": list(label_lines),
        "label_pixel_transcription": label,
        "physical_page": page,
        "report_norm_id": report_norm_id,
        "role": role,
        "section": section,
        "values": canonical_clone_v1(values),
    }


def _equation(
    name: str,
    page: int,
    components: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "component_values": canonical_clone_v1(components),
        "equation": "SUM_COMPONENTS_EQUALS_PRINTED_TOTAL",
        "name": name,
        "physical_page": page,
        "printed_total": canonical_clone_v1(total),
    }


def _unresolved(
    page: int,
    label: str,
    label_lines: Sequence[int],
    value: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "label_line_indices": list(label_lines),
        "physical_page": page,
        "reason": reason,
        "source_label": label,
        "status": "UNRESOLVED_NO_EXACT_SCHEMA_ITEM",
        "value": canonical_clone_v1(value),
    }


def _doc(
    code: str,
    pages: Sequence[int],
    layout: str,
    period: str,
    mappings: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    unresolved: Sequence[Mapping[str, Any]] = (),
    *,
    customer_type_subview: str = "NOT_OBSERVED_IN_BOUND_REPORT",
) -> dict[str, Any]:
    return {
        "comparison_period_excluded": "31/12/2025",
        "customer_type_subview": customer_type_subview,
        "disposition": "UNIQUE_COMPLETE_REGION_VISIBLE_PIXEL_REVIEWED",
        "document_provenance": code,
        "equations": canonical_clone_v1(equations),
        "layout_variant": layout,
        "mappings": canonical_clone_v1(mappings),
        "page_sequences": list(pages),
        "selected_monetary_axis": (
            "CURRENT_PERIOD_MONETARY_VALUES_ONLY_TOTAL_AND_PERCENT_COLUMNS_CHECK_ONLY"
        ),
        "source_period": period,
        "unresolved_items": canonical_clone_v1(list(unresolved)),
        "whole_document_family_absence_claim": False,
    }


def _review_documents() -> list[dict[str, Any]]:
    acb_mappings = [
        _mapping(1057, "NO_TERM", 21, "Tiền gửi không kỳ hạn", [13], [_value(16, "115.492.484")]),
        _mapping(1058, "NO_TERM_VND", 21, "Bằng tiền đồng", [7, 13], [_value(14, "99.924.470")]),
        _mapping(1059, "NO_TERM_FOREIGN", 21, "Bằng ngoại tệ", [8, 13], [_value(15, "15.568.014")]),
        _mapping(1060, "TERM", 21, "Tiền gửi có kỳ hạn", [17], [_value(20, "144.190.231")]),
        _mapping(1061, "TERM_VND", 21, "Bằng tiền đồng", [7, 17], [_value(18, "143.528.787")]),
        _mapping(1062, "TERM_FOREIGN", 21, "Bằng ngoại tệ", [8, 17], [_value(19, "661.444")]),
        _mapping(
            1063,
            "SAVINGS",
            21,
            "Tiền gửi tiết kiệm",
            [21, 25],
            [_value(24, "7.985.207"), _value(28, "305.787.377")],
            aggregation="SUM_OF_VISIBLE_SAVINGS_PARENTS",
        ),
        _mapping(
            1064,
            "SAVINGS_VND",
            21,
            "Tiền gửi tiết kiệm bằng tiền đồng",
            [7, 21, 25],
            [_value(22, "126.086"), _value(26, "302.998.978")],
            aggregation="SUM_OF_VISIBLE_SAVINGS_ROWS",
        ),
        _mapping(
            1065,
            "SAVINGS_FOREIGN",
            21,
            "Tiền gửi tiết kiệm bằng ngoại tệ",
            [8, 21, 25],
            [_value(23, "7.859.121"), _value(27, "2.788.399")],
            aggregation="SUM_OF_VISIBLE_SAVINGS_ROWS",
        ),
        _mapping(1066, "ESCROW", 21, "Tiền gửi ký quỹ", [29], [_value(32, "2.845.034")]),
        _mapping(
            1067,
            "ESCROW_VND",
            21,
            "Tiền gửi ký quỹ bằng tiền đồng",
            [7, 29],
            [_value(30, "2.568.065")],
        ),
        _mapping(
            1068,
            "ESCROW_FOREIGN",
            21,
            "Tiền gửi ký quỹ bằng ngoại tệ",
            [8, 29],
            [_value(31, "276.969")],
        ),
        _mapping(1069, "DEDICATED", 21, "Tiền gửi vốn chuyên dùng", [33], [_value(36, "303.269")]),
        _mapping(
            1070,
            "DEDICATED_VND",
            21,
            "Tiền gửi vốn chuyên dùng bằng tiền đồng",
            [7, 33],
            [_value(34, "112.310")],
        ),
        _mapping(
            1071,
            "DEDICATED_FOREIGN",
            21,
            "Tiền gửi vốn chuyên dùng bằng ngoại tệ",
            [8, 33],
            [_value(35, "190.959")],
        ),
    ]
    acb_equations = [
        _equation(
            "NO_TERM_EQUALS_VND_PLUS_FOREIGN",
            21,
            [_value(14, "99.924.470"), _value(15, "15.568.014")],
            _value(16, "115.492.484"),
        ),
        _equation(
            "TERM_EQUALS_VND_PLUS_FOREIGN",
            21,
            [_value(18, "143.528.787"), _value(19, "661.444")],
            _value(20, "144.190.231"),
        ),
        _equation(
            "SAVINGS_NO_TERM_EQUALS_VND_PLUS_FOREIGN",
            21,
            [_value(22, "126.086"), _value(23, "7.859.121")],
            _value(24, "7.985.207"),
        ),
        _equation(
            "SAVINGS_TERM_EQUALS_VND_PLUS_FOREIGN",
            21,
            [_value(26, "302.998.978"), _value(27, "2.788.399")],
            _value(28, "305.787.377"),
        ),
        _equation(
            "ESCROW_EQUALS_VND_PLUS_FOREIGN",
            21,
            [_value(30, "2.568.065"), _value(31, "276.969")],
            _value(32, "2.845.034"),
        ),
        _equation(
            "DEDICATED_EQUALS_VND_PLUS_FOREIGN",
            21,
            [_value(34, "112.310"), _value(35, "190.959")],
            _value(36, "303.269"),
        ),
        _equation(
            "OWNER_TOTAL_EQUALS_SOURCE_PARENTS",
            21,
            [
                _value(16, "115.492.484"),
                _value(20, "144.190.231"),
                _value(24, "7.985.207"),
                _value(28, "305.787.377"),
                _value(32, "2.845.034"),
                _value(36, "303.269"),
            ],
            _value(39, "576.603.602"),
        ),
        _equation(
            "VND_COLUMN_TOTAL",
            21,
            [
                _value(14, "99.924.470"),
                _value(18, "143.528.787"),
                _value(22, "126.086"),
                _value(26, "302.998.978"),
                _value(30, "2.568.065"),
                _value(34, "112.310"),
            ],
            _value(37, "549.258.696"),
        ),
        _equation(
            "FOREIGN_COLUMN_TOTAL",
            21,
            [
                _value(15, "15.568.014"),
                _value(19, "661.444"),
                _value(23, "7.859.121"),
                _value(27, "2.788.399"),
                _value(31, "276.969"),
                _value(35, "190.959"),
            ],
            _value(38, "27.344.906"),
        ),
    ]

    mbb_mappings = [
        _mapping(1057, "NO_TERM", 43, "Tiền gửi không kỳ hạn", [6], [_value(7, "324.045.154")]),
        _mapping(
            1058,
            "NO_TERM_VND",
            43,
            "Tiền gửi không kỳ hạn bằng VND",
            [9],
            [_value(10, "283.968.111")],
        ),
        _mapping(
            1059,
            "NO_TERM_FOREIGN",
            43,
            "Tiền gửi không kỳ hạn bằng ngoại tệ",
            [12],
            [_value(13, "40.077.043")],
        ),
        _mapping(1060, "TERM", 43, "Tiền gửi có kỳ hạn", [15], [_value(16, "630.236.029")]),
        _mapping(
            1061, "TERM_VND", 43, "Tiền gửi có kỳ hạn bằng VND", [18], [_value(19, "619.953.010")]
        ),
        _mapping(
            1062,
            "TERM_FOREIGN",
            43,
            "Tiền gửi có kỳ hạn bằng ngoại tệ",
            [21],
            [_value(22, "10.283.019")],
        ),
        _mapping(
            1069, "DEDICATED", 43, "Tiền gửi vốn chuyên dùng", [24], [_value(25, "1.707.241")]
        ),
        _mapping(
            1070,
            "DEDICATED_VND",
            43,
            "Tiền gửi vốn chuyên dùng — đưa vào VND vì nguồn không tách tiền tệ",
            [24],
            [_value(25, "1.707.241")],
            aggregation="USER_DIRECTED_PARENT_VALUE_TO_VND_NO_SEPARATE_FX",
            additivity="NONADDITIVE_DUPLICATE_AXIS_VIEW",
        ),
        _mapping(1066, "ESCROW", 43, "Tiền ký quỹ", [27], [_value(28, "7.826.933")]),
        _mapping(
            1067, "ESCROW_VND", 43, "Tiền gửi ký quỹ bằng VND", [30], [_value(31, "5.364.992")]
        ),
        _mapping(
            1068,
            "ESCROW_FOREIGN",
            43,
            "Tiền gửi ký quỹ bằng ngoại tệ",
            [33],
            [_value(34, "2.461.941")],
        ),
        _mapping(
            1084,
            "CUSTOMER_TCKT",
            43,
            "Tiền gửi của TCKT",
            [43],
            [_value(44, "402.838.837")],
            section="CUSTOMER_TYPE",
            additivity="ADDITIVE_WITHIN_CUSTOMER_TYPE_TABLE",
        ),
        _mapping(
            1089,
            "CUSTOMER_INDIVIDUAL",
            43,
            "Tiền gửi của cá nhân",
            [46],
            [_value(47, "560.976.520")],
            section="CUSTOMER_TYPE",
            additivity="ADDITIVE_WITHIN_CUSTOMER_TYPE_TABLE",
        ),
    ]
    mbb_equations = [
        _equation(
            "NO_TERM_EQUALS_VND_PLUS_FOREIGN",
            43,
            [_value(10, "283.968.111"), _value(13, "40.077.043")],
            _value(7, "324.045.154"),
        ),
        _equation(
            "TERM_EQUALS_VND_PLUS_FOREIGN",
            43,
            [_value(19, "619.953.010"), _value(22, "10.283.019")],
            _value(16, "630.236.029"),
        ),
        _equation(
            "ESCROW_EQUALS_VND_PLUS_FOREIGN",
            43,
            [_value(31, "5.364.992"), _value(34, "2.461.941")],
            _value(28, "7.826.933"),
        ),
        _equation(
            "OWNER_TOTAL_EQUALS_SOURCE_PARENTS",
            43,
            [
                _value(7, "324.045.154"),
                _value(16, "630.236.029"),
                _value(25, "1.707.241"),
                _value(28, "7.826.933"),
            ],
            _value(36, "963.815.357"),
        ),
        _equation(
            "CUSTOMER_TYPE_TOTAL",
            43,
            [_value(44, "402.838.837"), _value(47, "560.976.520")],
            _value(49, "963.815.357"),
        ),
    ]

    vpb_main = [
        _mapping(1057, "NO_TERM", 55, "Tiền gửi không kỳ hạn", [12], [_value(13, "89.343.913")]),
        _mapping(1058, "NO_TERM_VND", 55, "Bằng VND", [16], [_value(17, "87.011.116")]),
        _mapping(1059, "NO_TERM_FOREIGN", 55, "Bằng ngoại tệ", [20], [_value(21, "2.332.797")]),
        _mapping(1060, "TERM", 55, "Tiền gửi có kỳ hạn", [23], [_value(24, "587.582.551")]),
        _mapping(1061, "TERM_VND", 55, "Bằng VND", [27], [_value(28, "581.150.785")]),
        _mapping(1062, "TERM_FOREIGN", 55, "Bằng ngoại tệ", [31], [_value(32, "6.431.766")]),
        _mapping(1069, "DEDICATED", 55, "Tiền gửi vốn chuyên dùng", [34], [_value(35, "550.169")]),
        _mapping(1070, "DEDICATED_VND", 55, "Bằng VND", [38], [_value(39, "452.778")]),
        _mapping(1071, "DEDICATED_FOREIGN", 55, "Bằng ngoại tệ", [42], [_value(43, "97.391")]),
        _mapping(1066, "ESCROW", 55, "Tiền gửi ký quỹ", [45], [_value(46, "5.242.740")]),
        _mapping(1067, "ESCROW_VND", 55, "Bằng VND", [49], [_value(50, "5.014.768")]),
        _mapping(1068, "ESCROW_FOREIGN", 55, "Bằng ngoại tệ", [53], [_value(54, "227.972")]),
    ]
    vpb_customer_specs = [
        (1076, "STATE_COMPANY", "Công ty Nhà nước", [67], 68, "2.134.886"),
        (
            1078,
            "STATE_100_TNHH",
            "Công ty TNHH một thành viên do Nhà nước sở hữu 100% vốn điều lệ",
            [72, 73],
            74,
            "1.892.391",
        ),
        (1080, "OTHER_TNHH", "Công ty TNHH khác", [85], 86, "66.634.740"),
        (
            1081,
            "STATE_OVER_50_JSC",
            "Công ty cổ phần có vốn Nhà nước trên 50%",
            [90, 91, 92, 93, 94],
            95,
            "4.364.821",
        ),
        (1082, "OTHER_JSC", "Công ty cổ phần khác", [99], 100, "209.319.334"),
        (1087, "PARTNERSHIP", "Công ty hợp danh", [104], 105, "4.615"),
        (1083, "PRIVATE_ENTERPRISE", "Doanh nghiệp tư nhân", [109], 110, "585.044"),
        (
            1088,
            "FOREIGN_INVESTED",
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            [114],
            115,
            "2.495.445",
        ),
        (1085, "COOPERATIVE", "Hợp tác xã và liên hiệp hợp tác xã", [119], 120, "125.279"),
        (1089, "HOUSEHOLD_INDIVIDUAL", "Hộ kinh doanh, cá nhân", [124], 125, "389.577.670"),
        (
            1090,
            "ADMIN_ASSOCIATION",
            "Đơn vị hành chính sự nghiệp, Đảng, đoàn thể và hiệp hội",
            [129, 130],
            131,
            "5.350.839",
        ),
        (1091, "OTHER_CUSTOMER", "Khác", [135], 136, "170.144"),
    ]
    vpb_mappings = vpb_main + [
        _mapping(
            identifier,
            role,
            55,
            label,
            lines,
            [_value(value_line, value)],
            section="CUSTOMER_TYPE",
            additivity="ADDITIVE_WITHIN_CUSTOMER_TYPE_TABLE",
        )
        for identifier, role, label, lines, value_line, value in vpb_customer_specs
    ]
    vpb_equations = [
        _equation(
            "NO_TERM_EQUALS_VND_PLUS_FOREIGN",
            55,
            [_value(17, "87.011.116"), _value(21, "2.332.797")],
            _value(13, "89.343.913"),
        ),
        _equation(
            "TERM_EQUALS_VND_PLUS_FOREIGN",
            55,
            [_value(28, "581.150.785"), _value(32, "6.431.766")],
            _value(24, "587.582.551"),
        ),
        _equation(
            "DEDICATED_EQUALS_VND_PLUS_FOREIGN",
            55,
            [_value(39, "452.778"), _value(43, "97.391")],
            _value(35, "550.169"),
        ),
        _equation(
            "ESCROW_EQUALS_VND_PLUS_FOREIGN",
            55,
            [_value(50, "5.014.768"), _value(54, "227.972")],
            _value(46, "5.242.740"),
        ),
        _equation(
            "OWNER_TOTAL_EQUALS_SOURCE_PARENTS",
            55,
            [
                _value(13, "89.343.913"),
                _value(24, "587.582.551"),
                _value(35, "550.169"),
                _value(46, "5.242.740"),
            ],
            _value(56, "682.719.373"),
        ),
        _equation(
            "CUSTOMER_TYPE_TOTAL_INCLUDING_UNMAPPED_SOURCE_ROW",
            55,
            [
                _value(68, "2.134.886"),
                _value(74, "1.892.391"),
                _value(81, "64.165"),
                _value(86, "66.634.740"),
                _value(95, "4.364.821"),
                _value(100, "209.319.334"),
                _value(105, "4.615"),
                _value(110, "585.044"),
                _value(115, "2.495.445"),
                _value(120, "125.279"),
                _value(125, "389.577.670"),
                _value(131, "5.350.839"),
                _value(136, "170.144"),
            ],
            _value(140, "682.719.373"),
        ),
    ]

    def compact_type_rows(code: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        specs = {
            "HDB": (
                31,
                [
                    (1057, "NO_TERM", 33, 34, "72.867.051"),
                    (1058, "NO_TERM_VND", 36, 37, "56.755.388"),
                    (1059, "NO_TERM_FOREIGN", 39, 40, "16.111.663"),
                    (1060, "TERM", 42, 43, "599.616.658"),
                    (1061, "TERM_VND", 45, 46, "599.298.989"),
                    (1062, "TERM_FOREIGN", 48, 49, "317.669"),
                    (1069, "DEDICATED", 51, 52, "972.219"),
                    (1066, "ESCROW", 54, 55, "602.773"),
                ],
                [
                    ("NO_TERM", [(37, "56.755.388"), (40, "16.111.663")], (34, "72.867.051")),
                    ("TERM", [(46, "599.298.989"), (49, "317.669")], (43, "599.616.658")),
                    (
                        "OWNER",
                        [(34, "72.867.051"), (43, "599.616.658"), (52, "972.219"), (55, "602.773")],
                        (57, "674.058.701"),
                    ),
                ],
            ),
            "VCB": (
                35,
                [
                    (1057, "NO_TERM", 14, 15, "559.193.794"),
                    (1058, "NO_TERM_VND", 17, 18, "435.064.614"),
                    (1059, "NO_TERM_FOREIGN", 20, 21, "124.129.180"),
                    (1060, "TERM", 23, 24, "1.142.239.293"),
                    (1061, "TERM_VND", 26, 27, "1.024.944.616"),
                    (1062, "TERM_FOREIGN", 29, 30, "117.294.677"),
                    (1069, "DEDICATED", 32, 33, "19.904.421"),
                    (1066, "ESCROW", 35, 36, "7.483.059"),
                ],
                [
                    ("NO_TERM", [(18, "435.064.614"), (21, "124.129.180")], (15, "559.193.794")),
                    ("TERM", [(27, "1.024.944.616"), (30, "117.294.677")], (24, "1.142.239.293")),
                    (
                        "OWNER",
                        [
                            (15, "559.193.794"),
                            (24, "1.142.239.293"),
                            (33, "19.904.421"),
                            (36, "7.483.059"),
                        ],
                        (38, "1.728.820.567"),
                    ),
                ],
            ),
            "CTG": (
                42,
                [
                    (1057, "NO_TERM", 9, 10, "429.532.340"),
                    (1058, "NO_TERM_VND", 12, 13, "345.054.765"),
                    (1059, "NO_TERM_FOREIGN", 15, 16, "84.477.575"),
                    (1060, "TERM", 18, 19, "1.446.501.419"),
                    (1061, "TERM_VND", 21, 22, "1.397.336.136"),
                    (1062, "TERM_FOREIGN", 24, 25, "49.165.283"),
                    (1069, "DEDICATED", 27, 28, "6.261.403"),
                    (1070, "DEDICATED_VND", 30, 31, "5.530.197"),
                    (1071, "DEDICATED_FOREIGN", 33, 34, "731.206"),
                    (1066, "ESCROW", 36, 37, "8.514.391"),
                    (1067, "ESCROW_VND", 39, 40, "6.862.449"),
                    (1068, "ESCROW_FOREIGN", 42, 43, "1.651.942"),
                ],
                [
                    ("NO_TERM", [(13, "345.054.765"), (16, "84.477.575")], (10, "429.532.340")),
                    ("TERM", [(22, "1.397.336.136"), (25, "49.165.283")], (19, "1.446.501.419")),
                    ("DEDICATED", [(31, "5.530.197"), (34, "731.206")], (28, "6.261.403")),
                    ("ESCROW", [(40, "6.862.449"), (43, "1.651.942")], (37, "8.514.391")),
                    (
                        "OWNER",
                        [
                            (10, "429.532.340"),
                            (19, "1.446.501.419"),
                            (28, "6.261.403"),
                            (37, "8.514.391"),
                        ],
                        (45, "1.890.809.553"),
                    ),
                ],
            ),
            "BID": (
                25,
                [
                    (1057, "NO_TERM", 40, 41, "455.240.197"),
                    (1058, "NO_TERM_VND", 43, 44, "383.197.726"),
                    (1059, "NO_TERM_FOREIGN", 46, 47, "72.042.471"),
                    (1060, "TERM", 49, 50, "1.790.591.105"),
                    (1061, "TERM_VND", 52, 53, "1.647.614.641"),
                    (1062, "TERM_FOREIGN", 55, 56, "142.976.464"),
                    (1069, "DEDICATED", 58, 59, "10.371.497"),
                    (1070, "DEDICATED_VND", 61, 62, "4.213.387"),
                    (1071, "DEDICATED_FOREIGN", 64, 65, "6.158.110"),
                    (1066, "ESCROW", 67, 68, "5.517.595"),
                    (1067, "ESCROW_VND", 70, 71, "5.211.365"),
                    (1068, "ESCROW_FOREIGN", 73, 74, "306.230"),
                ],
                [
                    ("NO_TERM", [(44, "383.197.726"), (47, "72.042.471")], (41, "455.240.197")),
                    ("TERM", [(53, "1.647.614.641"), (56, "142.976.464")], (50, "1.790.591.105")),
                    ("DEDICATED", [(62, "4.213.387"), (65, "6.158.110")], (59, "10.371.497")),
                    ("ESCROW", [(71, "5.211.365"), (74, "306.230")], (68, "5.517.595")),
                    (
                        "OWNER",
                        [
                            (41, "455.240.197"),
                            (50, "1.790.591.105"),
                            (59, "10.371.497"),
                            (68, "5.517.595"),
                        ],
                        (76, "2.261.720.394"),
                    ),
                ],
            ),
        }
        page, rows, checks = specs[code]
        mappings = [
            _mapping(
                identifier,
                role,
                page,
                role.replace("_", " "),
                [label_line],
                [_value(value_line, value)],
            )
            for identifier, role, label_line, value_line, value in rows
        ]
        equations = [
            _equation(
                f"{name}_EQUATION",
                page,
                [_value(line, value) for line, value in components],
                _value(total_line, total_value),
            )
            for name, components, (total_line, total_value) in checks
        ]
        return mappings, equations

    vib_main = [
        _mapping(1057, "NO_TERM", 41, "Tiền gửi không kỳ hạn", [12], [_value(13, "37.334.817")]),
        _mapping(
            1058,
            "NO_TERM_VND",
            41,
            "Tiền gửi không kỳ hạn bằng VND gồm tiết kiệm",
            [15, 18],
            [_value(16, "33.555.941"), _value(19, "149")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        _mapping(
            1059,
            "NO_TERM_FOREIGN",
            41,
            "Tiền gửi không kỳ hạn bằng ngoại tệ gồm tiết kiệm",
            [21, 24],
            [_value(22, "3.778.335"), _value(25, "392")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        _mapping(1060, "TERM", 41, "Tiền gửi có kỳ hạn", [27], [_value(28, "279.589.942")]),
        _mapping(
            1061,
            "TERM_VND",
            41,
            "Tiền gửi có kỳ hạn bằng VND gồm tiết kiệm",
            [30, 33],
            [_value(31, "161.212.711"), _value(34, "97.320.225")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        _mapping(
            1062,
            "TERM_FOREIGN",
            41,
            "Tiền gửi có kỳ hạn bằng ngoại tệ gồm tiết kiệm",
            [36, 39],
            [_value(37, "1.244.811"), _value(40, "19.812.195")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        _mapping(
            1063,
            "SAVINGS",
            41,
            "Tiền gửi tiết kiệm",
            [18, 24, 33, 39],
            [
                _value(19, "149"),
                _value(25, "392"),
                _value(34, "97.320.225"),
                _value(40, "19.812.195"),
            ],
            aggregation="SUM_NESTED_SAVINGS_ROWS",
            additivity="NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM",
        ),
        _mapping(
            1064,
            "SAVINGS_VND",
            41,
            "Tiền gửi tiết kiệm bằng VND",
            [18, 33],
            [_value(19, "149"), _value(34, "97.320.225")],
            aggregation="SUM_NESTED_SAVINGS_ROWS",
            additivity="NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM",
        ),
        _mapping(
            1065,
            "SAVINGS_FOREIGN",
            41,
            "Tiền gửi tiết kiệm bằng ngoại tệ",
            [24, 39],
            [_value(25, "392"), _value(40, "19.812.195")],
            aggregation="SUM_NESTED_SAVINGS_ROWS",
            additivity="NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM",
        ),
        _mapping(1069, "DEDICATED", 41, "Tiền gửi vốn chuyên dùng", [42], [_value(43, "111.483")]),
        _mapping(
            1070,
            "DEDICATED_VND",
            41,
            "Tiền gửi vốn chuyên dùng bằng VND",
            [45],
            [_value(46, "86.708")],
        ),
        _mapping(
            1071,
            "DEDICATED_FOREIGN",
            41,
            "Tiền gửi vốn chuyên dùng bằng ngoại tệ",
            [48],
            [_value(49, "24.775")],
        ),
        _mapping(1066, "ESCROW", 41, "Tiền gửi ký quỹ", [51], [_value(52, "415.306")]),
        _mapping(1067, "ESCROW_VND", 41, "Tiền gửi ký quỹ bằng VND", [54], [_value(55, "397.878")]),
        _mapping(
            1068,
            "ESCROW_FOREIGN",
            41,
            "Tiền gửi ký quỹ bằng ngoại tệ",
            [57],
            [_value(58, "17.428")],
        ),
    ]
    vib_customer_specs = [
        (1076, "STATE_COMPANY", "Công ty Nhà nước", [19], [(20, "13.034.518")]),
        (
            1078,
            "STATE_100_TNHH",
            "Công ty TNHH MTV do Nhà nước sở hữu 100% vốn điều lệ",
            [24, 25],
            [(26, "2.580.702")],
        ),
        (1080, "OTHER_TNHH", "Công ty TNHH khác", [37], [(38, "17.293.683")]),
        (
            1081,
            "STATE_OVER_50_JSC",
            "Công ty cổ phần có vốn Nhà nước trên 50%",
            [42, 43, 44, 45, 46],
            [(47, "7.038.430")],
        ),
        (1082, "OTHER_JSC", "Công ty cổ phần khác", [51], [(52, "51.897.857")]),
        (1087, "PARTNERSHIP", "Công ty hợp danh", [56], [(57, "1.449")]),
        (1083, "PRIVATE_ENTERPRISE", "Doanh nghiệp tư nhân", [61], [(62, "16.314")]),
        (
            1088,
            "FOREIGN_INVESTED",
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            [66],
            [(67, "22.360.768")],
        ),
        (1085, "COOPERATIVE", "Hợp tác xã và liên hiệp hợp tác xã", [71], [(72, "78.197")]),
        (
            1089,
            "HOUSEHOLD_INDIVIDUAL",
            "Hộ kinh doanh, cá nhân",
            [76, 87],
            [(77, "188.155"), (88, "199.527.518")],
        ),
        (
            1090,
            "ADMIN_ASSOCIATION",
            "Đơn vị hành chính sự nghiệp, đảng, đoàn thể và hiệp hội",
            [81, 82],
            [(83, "3.433.783")],
        ),
    ]
    vib_mappings = vib_main + [
        _mapping(
            identifier,
            role,
            42,
            label,
            lines,
            [_value(line, value) for line, value in values],
            aggregation="SUM_OF_VISIBLE_ROWS" if len(values) > 1 else "DIRECT_VISIBLE_VALUE",
            section="CUSTOMER_TYPE",
            additivity="ADDITIVE_WITHIN_CUSTOMER_TYPE_DETAIL",
        )
        for identifier, role, label, lines, values in vib_customer_specs
    ]
    vib_equations = [
        _equation(
            "NO_TERM_INCLUDES_REGULAR_AND_SAVINGS_CURRENCY_ROWS",
            41,
            [
                _value(16, "33.555.941"),
                _value(19, "149"),
                _value(22, "3.778.335"),
                _value(25, "392"),
            ],
            _value(13, "37.334.817"),
        ),
        _equation(
            "TERM_INCLUDES_REGULAR_AND_SAVINGS_CURRENCY_ROWS",
            41,
            [
                _value(31, "161.212.711"),
                _value(34, "97.320.225"),
                _value(37, "1.244.811"),
                _value(40, "19.812.195"),
            ],
            _value(28, "279.589.942"),
        ),
        _equation(
            "DEDICATED_EQUALS_VND_PLUS_FOREIGN",
            41,
            [_value(46, "86.708"), _value(49, "24.775")],
            _value(43, "111.483"),
        ),
        _equation(
            "ESCROW_EQUALS_VND_PLUS_FOREIGN",
            41,
            [_value(55, "397.878"), _value(58, "17.428")],
            _value(52, "415.306"),
        ),
        _equation(
            "OWNER_TOTAL_EXCLUDES_NESTED_SAVINGS_DOUBLE_COUNT",
            41,
            [
                _value(13, "37.334.817"),
                _value(28, "279.589.942"),
                _value(43, "111.483"),
                _value(52, "415.306"),
            ],
            _value(60, "317.451.548"),
        ),
        _equation(
            "TCKT_DETAIL_TOTAL_INCLUDING_UNMAPPED_SOURCE_ROW",
            42,
            [
                _value(20, "13.034.518"),
                _value(26, "2.580.702"),
                _value(33, "174"),
                _value(38, "17.293.683"),
                _value(47, "7.038.430"),
                _value(52, "51.897.857"),
                _value(57, "1.449"),
                _value(62, "16.314"),
                _value(67, "22.360.768"),
                _value(72, "78.197"),
                _value(77, "188.155"),
                _value(83, "3.433.783"),
            ],
            _value(15, "117.924.030"),
        ),
        _equation(
            "CUSTOMER_TYPE_GROUP_TOTAL",
            42,
            [_value(15, "117.924.030"), _value(88, "199.527.518")],
            _value(92, "317.451.548"),
        ),
    ]

    hdb_mappings, hdb_equations = compact_type_rows("HDB")
    vcb_mappings, vcb_equations = compact_type_rows("VCB")
    ctg_mappings, ctg_equations = compact_type_rows("CTG")
    bid_mappings, bid_equations = compact_type_rows("BID")
    missing_tnhh_reason = (
        "SOURCE_IS_TNHH_TWO_OR_MORE_MEMBERS_WITH_STATE_OWNERSHIP_OVER_50_PERCENT_"
        "BUT_LIVE_ID_1079_IS_LIMITED_TO_ONE_MEMBER_TNHH"
    )
    return [
        _doc(
            "ACB",
            [21],
            "PERIOD_STACKED_ROWS_X_CURRENCY_COLUMNS",
            "2026-06-30",
            acb_mappings,
            acb_equations,
        ),
        _doc(
            "MBB",
            [43],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_PLUS_CUSTOMER_TYPE_SUBTABLE",
            "2026-06-30",
            mbb_mappings,
            mbb_equations,
            customer_type_subview="MAPPED_TWO_ROW_CUSTOMER_TYPE_SUBTABLE",
        ),
        _doc(
            "VPB",
            [55],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_PLUS_MONEY_PERCENT_CUSTOMER_TYPE_SUBTABLE",
            "2026-03-31",
            vpb_mappings,
            vpb_equations,
            [
                _unresolved(
                    55,
                    "Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50%",
                    [78, 79, 80],
                    _value(81, "64.165"),
                    missing_tnhh_reason,
                )
            ],
            customer_type_subview="PARTIALLY_MAPPED_DETAILED_CUSTOMER_TYPE_SUBTABLE",
        ),
        _doc(
            "HDB",
            [31],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_WITH_RELATIVE_PERIOD_HEADERS",
            "2026-06-30",
            hdb_mappings,
            hdb_equations,
        ),
        _doc(
            "VCB",
            [35],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            vcb_mappings,
            vcb_equations,
        ),
        _doc(
            "CTG",
            [42],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            ctg_mappings,
            ctg_equations,
        ),
        _doc(
            "BID",
            [25],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            bid_mappings,
            bid_equations,
        ),
        _doc(
            "VIB",
            [41, 42],
            "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_WITH_NESTED_SAVINGS_AND_CROSS_PAGE_CUSTOMER_TYPE",
            "2026-06-30",
            vib_mappings,
            vib_equations,
            [
                _unresolved(
                    42,
                    "Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50%",
                    [30, 31, 32],
                    _value(33, "174"),
                    missing_tnhh_reason,
                )
            ],
            customer_type_subview="PARTIALLY_MAPPED_CROSS_PAGE_DETAILED_CUSTOMER_TYPE_SUBTABLE",
        ),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0058"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0058:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex customer-deposit pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _money(value: Any) -> int:
    if type(value) is not str or value != value.strip() or _MONEY.fullmatch(value) is None:
        raise _error(f"visible money transcription is invalid: {value!r}")
    digits = value.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error("visible money digits drifted")
    return int(digits)


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


def _artifact_bytes(reference: Any, label: str) -> bytes:
    if (
        type(reference) is not dict
        or set(reference) != {"path", "sha256", "size_bytes"}
        or type(reference["path"]) is not str
        or type(reference["size_bytes"]) is not int
    ):
        raise _error(f"{label} reference fields drifted")
    payload = _stable_bytes(Path(reference["path"]))
    if len(payload) != reference["size_bytes"] or hashlib.sha256(payload).hexdigest() != _sha256(
        reference["sha256"], label
    ):
        raise _error(f"{label} bytes drifted")
    return payload


def _source_line_axis(page: Mapping[str, Any]) -> list[str]:
    result = _strict_json(_artifact_bytes(page.get("result_ref"), "page result"), "page result")
    lines = result.get("lines")
    if type(lines) is list and lines:
        texts = [line.get("raw_text") if type(line) is dict else None for line in lines]
        if len(texts) != page.get("primary_line_count") or not all(
            type(text) is str for text in texts
        ):
            raise _error("page result source line axis drifted")
        return texts
    backend = _strict_json(_artifact_bytes(page.get("backend_ref"), "page backend"), "page backend")
    raw = backend.get("raw_provider_payload")
    texts = raw.get("rec_texts") if type(raw) is dict else None
    if (
        type(texts) is not list
        or len(texts) != page.get("supplement_line_count")
        or not all(type(text) is str for text in texts)
    ):
        raise _error("terminal backend source line axis drifted")
    return list(texts)


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


def _source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"line_index", "pixel_transcription"}
        or type(value["line_index"]) is not int
    ):
        raise _error("reviewed source value fields drifted")
    line_index = value["line_index"]
    pixel_value = _money(value["pixel_transcription"])
    axis = _axis_line(axis_page, line_index)
    semantic_lines = semantic_page.get("lines")
    if type(semantic_lines) is not list or not 0 <= line_index < len(semantic_lines):
        raise _error("semantic-index crop line axis drifted")
    semantic_line = semantic_lines[line_index]
    if (
        type(semantic_line) is not dict
        or semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis["vietocr_text"]
        or type(semantic_line.get("crop_ref")) is not dict
        or type(semantic_line.get("sample_id")) is not str
    ):
        raise _error("semantic-index crop binding drifted")
    if not 0 <= line_index < len(source_texts):
        raise _error("source numeric challenger index drifted")
    source_raw = source_texts[line_index]
    if _money(source_raw) != pixel_value:
        raise _error("visible pixel transcription and source numeric challenger disagree")
    crop_ref = semantic_line["crop_ref"]
    sample_first = crop_page.get("sample_offset_start")
    sample_stop = crop_page.get("sample_offset_stop")
    sample_id = semantic_line["sample_id"]
    if type(sample_first) is not int or type(sample_stop) is not int or type(sample_id) is not str:
        raise _error("crop page/sample binding drifted")
    expected_sample_ordinal = sample_first + line_index + 1
    expected_sample_id = f"sample-{expected_sample_ordinal:08d}"
    if (
        not sample_first <= expected_sample_ordinal - 1 < sample_stop
        or sample_id != expected_sample_id
        or type(crop_ref.get("path")) is not str
        or not crop_ref["path"].endswith(f"/{expected_sample_id}.png")
    ):
        raise _error("crop page/sample ordinal or content binding drifted")
    return {
        "crop_ref": canonical_clone_v1(crop_ref),
        "fresh_vietocr_numeric_proposal": axis["vietocr_text"],
        "normalized_value": pixel_value,
        "pixel_transcription": value["pixel_transcription"],
        "source_line_index": line_index,
        "source_numeric_challenger": source_raw,
        "source_numeric_challenger_status": "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
    }


def _schema_binding(item: Any) -> dict[str, Any]:
    if item is None or item.statement_type != "TM" or item.schema_id not in range(1057, 1092):
        raise _error("reviewed mapping does not bind one supported live TM item")
    if item.parent_id not in {1056, 1075}:
        raise _error("customer-deposit live schema parent drifted")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def build_customer_deposit_8bank_codex_verified_mapping_v1(
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
    """Build the exact eight-bank bounded customer-deposit mapping result."""

    review = _review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state") != "FULL_DOCUMENT_CUSTOMER_DEPOSIT_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("customer-deposit input authority drifted")
    _sha256(crop_manifest_sha256, "crop manifest")
    _sha256(review_sha256, "pixel review")
    trials: list[dict[str, Any]] = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        review_document = _document_by_code(review["documents"], code, "pixel review")
        semantic_document = _document_by_code(
            semantic_index.get("documents"), code, "semantic index"
        )
        axis_document = _document_by_code(axis["documents"], code, "fresh VietOCR axis")
        crop_document = _document_by_code(crop_manifest.get("documents"), code, "crop manifest")
        scan_trial = _document_by_code(structure_scan.get("trials"), code, "structure scan")
        matcher = scan_trial.get("matcher_result")
        if (
            scan_trial.get("document_ordinal") != ordinal
            or type(matcher) is not dict
            or matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or matcher.get("uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or type(matcher.get("regions")) is not list
            or len(matcher["regions"]) != 1
        ):
            raise _error("whole-PDF customer-deposit region is not exactly unique")
        region = matcher["regions"][0]
        if (
            region.get("page_sequences") != review_document["page_sequences"]
            or region.get("layout", {}).get("primary_mode") not in review_document["layout_variant"]
        ):
            # The review may add a semantically meaningful subtable/continuation suffix,
            # but its primary structural orientation must remain the matcher orientation.
            raise _error("reviewed pages/layout disagree with the generic structure graph")
        mapped_rows: list[dict[str, Any]] = []
        page_render_refs: dict[int, Any] = {}
        page_source_axes: dict[int, list[str]] = {}
        for row in review_document["mappings"]:
            page_number = row.get("physical_page")
            axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
            semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
            crop_page = _page_by_number(crop_document, page_number, "crop manifest")
            page_render_refs[page_number] = canonical_clone_v1(crop_page.get("render_binding"))
            if page_number not in page_source_axes:
                page_source_axes[page_number] = _source_line_axis(crop_page)
            source_texts = page_source_axes[page_number]
            label_lines = row.get("label_line_indices")
            if (
                type(label_lines) is not list
                or not label_lines
                or any(type(index) is not int for index in label_lines)
            ):
                raise _error("reviewed customer-deposit label line axis drifted")
            transformer_text = [
                _axis_line(axis_page, index)["vietocr_text"] for index in label_lines
            ]
            source_values = [
                _source_value(axis_page, semantic_page, crop_page, source_texts, value)
                for value in row.get("values", [])
            ]
            if not source_values:
                raise _error("reviewed customer-deposit mapping lacks visible values")
            schema = _schema_binding(schema_by_id.get(row.get("report_norm_id")))
            mapped_rows.append(
                {
                    **schema,
                    "additivity": row["additivity"],
                    "aggregation": row["aggregation"],
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "normalized_anchor": normalize_vietnamese_anchor_v1(" ".join(transformer_text)),
                    "normalized_value": sum(item["normalized_value"] for item in source_values),
                    "physical_page": page_number,
                    "role": row["role"],
                    "section": row["section"],
                    "source_values": source_values,
                    "status": "VERIFIED_BY_CODEX",
                    "vietocr_transformer_text": transformer_text,
                }
            )
        equations = []
        for equation in review_document["equations"]:
            page_number = equation.get("physical_page")
            axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
            semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
            crop_page = _page_by_number(crop_document, page_number, "crop manifest")
            if page_number not in page_source_axes:
                page_source_axes[page_number] = _source_line_axis(crop_page)
            source_texts = page_source_axes[page_number]
            components = [
                _source_value(axis_page, semantic_page, crop_page, source_texts, value)
                for value in equation["component_values"]
            ]
            total = _source_value(
                axis_page,
                semantic_page,
                crop_page,
                source_texts,
                equation["printed_total"],
            )
            computed = sum(item["normalized_value"] for item in components)
            if computed != total["normalized_value"]:
                raise _error(f"customer-deposit accounting equation does not close: {code}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "physical_page": page_number,
                    "printed_total": total["normalized_value"],
                    "status": "CORROBORATED_EXACT",
                }
            )
        unresolved_items = []
        for item in review_document["unresolved_items"]:
            page_number = item["physical_page"]
            axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
            semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
            crop_page = _page_by_number(crop_document, page_number, "crop manifest")
            if page_number not in page_source_axes:
                page_source_axes[page_number] = _source_line_axis(crop_page)
            source_texts = page_source_axes[page_number]
            value = _source_value(axis_page, semantic_page, crop_page, source_texts, item["value"])
            unresolved_items.append(
                {
                    **canonical_clone_v1(item),
                    "source_value_binding": value,
                    "vietocr_transformer_text": [
                        _axis_line(axis_page, index)["vietocr_text"]
                        for index in item["label_line_indices"]
                    ],
                }
            )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if review_document["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "cluster_boundary": canonical_clone_v1(region["cluster_boundary"]),
                "customer_type_subview": review_document["customer_type_subview"],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "layout": canonical_clone_v1(region["layout"]),
                "layout_variant": review_document["layout_variant"],
                "selected_axes": {
                    "comparison_period_excluded": review_document["comparison_period_excluded"],
                    "monetary_axis": review_document["selected_monetary_axis"],
                    "percentage_axis_mapped_as_money": False,
                    "total_columns_used_as_checks_only": True,
                },
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": review_document["source_period"],
                "source_period_status": source_period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                    if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "unresolved_items": unresolved_items,
                "verified_accounting_equations": equations,
                "verified_mappings": mapped_rows,
                "visible_page_render_bindings": [
                    {"physical_page": page, "render_binding": page_render_refs[page]}
                    for page in sorted(page_render_refs)
                ],
                "whole_document_family_absence_claim": False,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    metrics = {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unresolved_source_item_count": sum(len(trial["unresolved_items"]) for trial in trials),
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "codex_pixel_review": {
                "path": REVIEW_PATH.as_posix(),
                "sha256": review_sha256,
            },
            "crop_manifest_sha256": crop_manifest_sha256,
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_authority": canonical_clone_v1(schema_authority),
        },
        "metrics": metrics,
        "state": "CUSTOMER_DEPOSIT_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "cd8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified customer-deposit result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "CUSTOMER_DEPOSIT_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
    ):
        raise _error("verified customer-deposit result identity/authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cd8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("verified customer-deposit result identity drifted")
    return canonical_clone_v1(value)


def build_live_customer_deposit_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_bytes = _fixed_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review_value, review_bytes = _fixed_json(REVIEW_PATH)
    scan = _scanner().build_customer_deposit_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_customer_deposit_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=hashlib.sha256(crop_bytes).hexdigest(),
        review_sha256=hashlib.sha256(review_bytes).hexdigest(),
    )


def validate_customer_deposit_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    persisted = _validate_result(value)
    rebuilt = build_live_customer_deposit_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified customer-deposit result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        output = REVIEW_PATH
        value = _review_blueprint()
    else:
        output = args.output
        value = build_live_customer_deposit_8bank_codex_verified_mapping_v1()
    if output.exists() and not args.replace:
        raise _error(f"refusing to overwrite fixed customer-deposit artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes_v1(value))
    print(output.as_posix())
    print(hashlib.sha256(output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
