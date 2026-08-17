"""Verify annual-2025 intangible fixed-asset movement notes for eight banks.

The evidence ledger names banks and pages only after the bank-blind complete-
PDF matcher has selected one unique region.  Reporting dates are read from the
PDF profile; schema bindings are family-local so unrelated schema insertions do
not reseal this result.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ifa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ifa8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0125-annual-2025-intangible-fixed-assets-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0125-annual-2025-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = (
    "a2025ifafdsv1:scan:eba4527624e7e6ba18f70f921eb975aefc6da148361edf6c494dd1c8146859b7"
)
EXPECTED_RESCUE_LINE_COUNT = 3_338
SCAN_FORMAT = "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_8DOCUMENT_STRUCTURE_SCAN_V1"
SCAN_ID_PREFIX = "a2025ifafdsv1:scan:"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_REPORTING_PERIOD_GENERAL_INTANGIBLE_FIXED_ASSET_"
    "VARIANT_GRAPH_ROTATED_SAME_TRANSFORMER_SEMANTIC_RESCUE_VISIBLE_PIXEL_"
    "UPSTREAM_PPOCRV6_NUMERIC_AXIS_ACCOUNTING_AND_FAMILY_LOCAL_STABLE_TM_"
    "SCHEMA_BINDING_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "OWNER_PRECEDES_COST_AMORTIZATION_AND_CARRYING_BRANCHES",
    "FIRST_COMPLETE_CORE_CYCLE_EXCLUDES_LATER_DETAIL_ROWS",
    "LATEST_EXPLICIT_LOCAL_REPORTING_PERIOD_SELECTED",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_NUMERIC_AXIS_MATCHES_VISIBLE_PIXEL",
    "INLINE_DISCLOSURE_NUMERIC_TOKEN_BOUND_TO_FULL_SENTENCE",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "COST_AND_AMORTIZATION_EQUAL_CARRYING_VALUE",
    "LIVE_TM_SCHEMA_ID_NAME_AND_PARENT_COMPATIBILITY",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf_not_fixed_calendar_constants": True,
    "rotated_page_uses_same_pinned_vietocr_transformer_for_semantic_rescue": True,
    "schema_global_display_order_used_as_identity": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_id_name_and_parent_checked": True,
    "mapping_authority_bounded_to_eight_unique_annual_intangible_asset_regions": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "schema_additions_outside_family_change_detection_or_mapping": False,
    "text_similarity_alone_used_for_mapping": False,
}
_SCHEMA_AUTHORITY = {
    "binding_mode": "FAMILY_LOCAL_STABLE_REPORT_NORM_ID_NAME_AND_PARENT",
    "family_root_report_norm_id": 913,
    "global_display_order_is_identity": False,
    "live_compatibility_rechecked_on_every_replay": True,
    "snapshot_label": "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_FAMILY_V1",
}
_SCHEMA_EXPECTED = {
    913: ("Tăng, giảm tài sản cố định vô hình", 560),
    914: ("Nguyên giá", 913),
    915: ("Số dư đầu kỳ", 914),
    5997: ("Tổng tăng nguyên giá TSCĐ vô hình trong kỳ", 914),
    916: ("+ Mua trong kỳ", 5997),
    917: ("+ Đầu tư XDCB hoàn thành", 5997),
    918: ("+ Chuyển từ chi phí xây dựng CBDD", 5997),
    919: ("+ Tăng do hợp nhất kinh doanh", 5997),
    920: ("+ Tăng khác", 5997),
    6068: ("Tổng giảm nguyên giá TSCĐ vô hình trong kỳ", 914),
    921: ("+ Chuyển sang BĐS đầu tư (*)", 6068),
    922: ("+ Chuyển sang công cụ dụng cụ", 6068),
    923: ("+ Chuyển sang chi phí chờ phân bổ", 6068),
    924: ("+ Phân loại lại", 6068),
    925: ("+ Thanh lý. nhượng bán (*)", 6068),
    926: ("+ Trích lập quỹ", 6068),
    927: ("+ Giảm khác (*)", 6068),
    5998: ("Tăng/(Giảm) khác nguyên giá TSCĐ vô hình trong kỳ", 914),
    5967: ("+ Chênh lệch tỷ giá", 914),
    928: ("Số dư cuối kỳ", 914),
    929: ("Giá trị hao mòn luỹ kế", 913),
    930: ("Số dư đầu kỳ", 929),
    5999: ("Tổng tăng hao mòn TSCĐ vô hình trong kỳ", 929),
    931: ("+ Khấu hao trong kỳ", 5999),
    932: ("+ Tăng do hợp nhất kinh doanh", 5999),
    933: ("+ Tăng khác", 5999),
    6000: ("Tổng giảm hao mòn TSCĐ vô hình trong kỳ", 929),
    934: ("+ Chuyển sang BĐS đầu tư (*)", 6000),
    935: ("+ Chuyển sang công cụ dụng cụ", 6000),
    936: ("+ Chuyển sang chi phí chờ phân bổ", 6000),
    937: ("+ Phân loại lại", 6000),
    938: ("+ Thanh lý. nhượng bán (*)", 6000),
    939: ("+ Trích lập quỹ", 6000),
    940: ("+ Giảm khác (*)", 6000),
    6001: ("Tăng/(Giảm) khác hao mòn TSCĐ vô hình trong kỳ", 929),
    5968: ("+ Chênh lệch tỷ giá", 929),
    941: ("Số dư cuối kỳ", 929),
    5969: ("Giá trị còn lại", 913),
    5970: ("Số dư đầu kỳ", 5969),
    5971: ("Số dư cuối kỳ", 5969),
    6069: ("Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng", 913),
}
_SCHEMA_DISPLAY_ORDER_SNAPSHOT = {
    913: 394,
    914: 395,
    915: 396,
    5997: 397,
    916: 398,
    917: 399,
    918: 400,
    919: 401,
    920: 402,
    6068: 403,
    921: 404,
    922: 405,
    923: 406,
    924: 407,
    925: 408,
    926: 409,
    927: 410,
    5998: 411,
    5967: 412,
    928: 413,
    929: 414,
    930: 415,
    5999: 416,
    931: 417,
    932: 418,
    933: 419,
    6000: 420,
    934: 421,
    935: 422,
    936: 423,
    937: 424,
    938: 425,
    939: 426,
    940: 427,
    6001: 428,
    5968: 429,
    941: 430,
    5969: 431,
    5970: 432,
    5971: 433,
    6069: 434,
}
_EXPECTED_IDS = {
    "ACB": {915, 5997, 917, 925, 5998, 928, 930, 931, 938, 941, 5970, 5971, 6069},
    "MBB": {
        915,
        5997,
        925,
        927,
        5967,
        928,
        930,
        931,
        938,
        940,
        5968,
        941,
        5970,
        5971,
        6069,
    },
    "VPB": {915, 916, 920, 925, 928, 930, 931, 933, 940, 941, 5970, 5971, 6069},
    "HDB": {915, 5997, 925, 928, 930, 931, 938, 941, 5970, 5971, 6069},
    "VCB": {
        915,
        5997,
        916,
        920,
        6068,
        925,
        927,
        928,
        930,
        5999,
        931,
        933,
        6000,
        938,
        940,
        941,
        5970,
        5971,
        6069,
    },
    "CTG": {915, 916, 925, 927, 928, 930, 931, 938, 940, 941, 5970, 5971, 6069},
    "BID": {915, 916, 920, 925, 928, 930, 931, 933, 938, 941, 5970, 5971, 6069},
    "VIB": {915, 916, 925, 928, 930, 931, 941, 5970, 5971, 6069},
}


class Annual2025IntangibleFixedAssets8BankError(ValueError):
    """Annual intangible-asset graph, pixels, numbers or schema drifted."""


def _error(message: str) -> Annual2025IntangibleFixedAssets8BankError:
    return Annual2025IntangibleFixedAssets8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _values(base: ModuleType, entries: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    values = {}
    for key, raw in entries.items():
        if len(raw) == 2:
            values[key] = base._value(raw[0], raw[1])
        elif len(raw) == 3:
            values[key] = base._inline_value(raw[0], raw[1], raw[2])
        else:
            raise _error(f"review value specification drifted: {key}")
    return values


def _mapping(
    base: ModuleType,
    values: Mapping[str, dict[str, Any]],
    raw: Sequence[Any],
) -> dict[str, Any]:
    report_norm_id, role, label_index, label, value_key, topology = raw
    return base._mapping(
        report_norm_id,
        role,
        label_index,
        label,
        values[value_key],
        topology=topology,
    )


def _four_equations(
    base: ModuleType,
    values: Mapping[str, dict[str, Any]],
    cost_movements: Sequence[str],
    amortization_movements: Sequence[str],
    *,
    amortization_is_negative: bool = False,
) -> list[dict[str, Any]]:
    amortization_multiplier = 1 if amortization_is_negative else -1
    return [
        base._equation(
            "COST_ROLLFORWARD",
            [base._term(values[name]) for name in ("cost_open", *cost_movements)],
            values["cost_close"],
        ),
        base._equation(
            "AMORTIZATION_ROLLFORWARD",
            [base._term(values[name]) for name in ("dep_open", *amortization_movements)],
            values["dep_close"],
        ),
        base._equation(
            "OPENING_COST_AND_AMORTIZATION_TO_CARRYING_VALUE",
            [
                base._term(values["cost_open"]),
                base._term(values["dep_open"], amortization_multiplier),
            ],
            values["carry_open"],
        ),
        base._equation(
            "ENDING_COST_AND_AMORTIZATION_TO_CARRYING_VALUE",
            [
                base._term(values["cost_close"]),
                base._term(values["dep_close"], amortization_multiplier),
            ],
            values["carry_close"],
        ),
    ]


_DOCUMENT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "code": "ACB",
        "page": 56,
        "owner": (7, "Tài sản cố định vô hình"),
        "branches": (
            ("COST", 15, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 40, "Hao mòn lũy kế"),
            ("CARRYING_VALUE", 56, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (19, "2.950.265"),
            "cost_increase": (23, "98.705"),
            "cost_xdcb": (28, "122.430"),
            "cost_disposal": (32, "(58.742)"),
            "cost_reclass": (35, "4.869"),
            "cost_close": (39, "3.117.527"),
            "dep_open": (44, "760.093"),
            "dep_charge": (48, "120.319"),
            "dep_disposal": (51, "(948)"),
            "dep_close": (55, "879.464"),
            "carry_open": (60, "2.190.172"),
            "carry_close": (64, "2.238.063"),
            "fully": (72, "536.070"),
        },
        "mappings": (
            (915, "COST_OPENING", 16, "Tại ngày 1 tháng 1 năm 2025", "cost_open", "COST_CHILD"),
            (5997, "COST_TOTAL_INCREASE", 20, "Tăng trong năm", "cost_increase", "COST_CHILD"),
            (
                917,
                "COST_XDCB_COMPLETED",
                24,
                "Đầu tư xây dựng cơ bản hoàn thành",
                "cost_xdcb",
                "COST_INCREASE_CHILD",
            ),
            (925, "COST_DISPOSAL", 29, "Thanh lý", "cost_disposal", "COST_DECREASE_CHILD"),
            (5998, "COST_OTHER_NET", 33, "Phân loại lại", "cost_reclass", "COST_CHILD"),
            (928, "COST_ENDING", 36, "Tại ngày 31 tháng 12 năm 2025", "cost_close", "COST_CHILD"),
            (
                930,
                "AMORTIZATION_OPENING",
                41,
                "Tại ngày 1 tháng 1 năm 2025",
                "dep_open",
                "AMORTIZATION_CHILD",
            ),
            (
                931,
                "AMORTIZATION_CHARGE",
                45,
                "Khấu hao trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                938,
                "AMORTIZATION_DISPOSAL",
                49,
                "Thanh lý",
                "dep_disposal",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                941,
                "AMORTIZATION_ENDING",
                52,
                "Tại ngày 31 tháng 12 năm 2025",
                "dep_close",
                "AMORTIZATION_CHILD",
            ),
            (
                5970,
                "CARRYING_OPENING",
                57,
                "Tại ngày 1 tháng 1 năm 2025",
                "carry_open",
                "CARRYING_CHILD",
            ),
            (
                5971,
                "CARRYING_ENDING",
                61,
                "Tại ngày 31 tháng 12 năm 2025",
                "carry_close",
                "CARRYING_CHILD",
            ),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                70,
                "Nguyên giá TSCĐ vô hình đã khấu hao hết nhưng vẫn còn",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_increase", "cost_xdcb", "cost_disposal", "cost_reclass"),
        "dep_movements": ("dep_charge", "dep_disposal"),
    },
    {
        "code": "MBB",
        "page": 60,
        "owner": (10, "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        "branches": (
            ("COST", 24, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 49, "Giá trị hao mòn luỹ kế"),
            ("CARRYING_VALUE", 74, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (29, "4.976.669"),
            "cost_increase": (34, "823.072"),
            "cost_disposal": (37, "(105.478)"),
            "cost_other": (40, "(10.622)"),
            "cost_fx": (43, "1.263"),
            "cost_close": (48, "5.684.904"),
            "dep_open": (54, "3.296.949"),
            "dep_charge": (59, "601.304"),
            "dep_disposal": (62, "(21.406)"),
            "dep_other": (65, "(3.348)"),
            "dep_fx": (68, "391"),
            "dep_close": (73, "3.873.890"),
            "carry_open": (79, "1.679.720"),
            "carry_close": (84, "1.811.014"),
            "fully": (
                159,
                "nhưng vẫn đang được sử dụng là 2.667.798 triệu VND (31/12/2024: 1.855.349 triệu VND).",
                "2.667.798",
            ),
        },
        "mappings": (
            (915, "COST_OPENING", 25, "Số dư đầu năm", "cost_open", "COST_CHILD"),
            (5997, "COST_TOTAL_INCREASE", 30, "Tăng trong năm", "cost_increase", "COST_CHILD"),
            (925, "COST_DISPOSAL", 35, "Thanh lý", "cost_disposal", "COST_DECREASE_CHILD"),
            (927, "COST_OTHER_DECREASE", 38, "Giảm khác", "cost_other", "COST_DECREASE_CHILD"),
            (5967, "COST_FOREIGN_EXCHANGE", 41, "Chênh lệch tỷ giá", "cost_fx", "COST_CHILD"),
            (928, "COST_ENDING", 44, "Số dư cuối năm", "cost_close", "COST_CHILD"),
            (930, "AMORTIZATION_OPENING", 50, "Số dư đầu năm", "dep_open", "AMORTIZATION_CHILD"),
            (
                931,
                "AMORTIZATION_CHARGE",
                55,
                "Khấu hao trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                938,
                "AMORTIZATION_DISPOSAL",
                60,
                "Thanh lý",
                "dep_disposal",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                940,
                "AMORTIZATION_OTHER_DECREASE",
                63,
                "Giảm khác",
                "dep_other",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                5968,
                "AMORTIZATION_FOREIGN_EXCHANGE",
                66,
                "Chênh lệch tỷ giá",
                "dep_fx",
                "AMORTIZATION_CHILD",
            ),
            (941, "AMORTIZATION_ENDING", 69, "Số dư cuối năm", "dep_close", "AMORTIZATION_CHILD"),
            (5970, "CARRYING_OPENING", 75, "Số dư đầu năm", "carry_open", "CARRYING_CHILD"),
            (5971, "CARRYING_ENDING", 80, "Số dư cuối năm", "carry_close", "CARRYING_CHILD"),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                158,
                "Tại ngày 31 tháng 12 năm 2025, nguyên giá các tài sản cố định vô hình đã khấu hao hết",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_increase", "cost_disposal", "cost_other", "cost_fx"),
        "dep_movements": ("dep_charge", "dep_disposal", "dep_other", "dep_fx"),
    },
    {
        "code": "VPB",
        "page": 54,
        "owner": (7, "Tài sản cố định vô hình"),
        "branches": (
            ("COST", 17, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 36, "Giá trị hao mòn lũy kế"),
            ("CARRYING_VALUE", 54, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (21, "2.086.191"),
            "cost_purchase": (24, "42.902"),
            "cost_other": (27, "123.125"),
            "cost_disposal": (31, "(47.037)"),
            "cost_close": (35, "2.205.181"),
            "dep_open": (40, "1.499.374"),
            "dep_charge": (43, "183.088"),
            "dep_other_increase": (46, "2.201"),
            "dep_other_decrease": (49, "(29.037)"),
            "dep_close": (53, "1.655.626"),
            "carry_open": (58, "586.817"),
            "carry_close": (62, "549.555"),
            "fully": (
                64,
                "12 năm 2025 là 1.158.286 triệu đồng (31 tháng 12 năm 2024: 809.788 triệu đồng).",
                "1.158.286",
            ),
        },
        "mappings": (
            (915, "COST_OPENING", 18, "Số dư đầu năm", "cost_open", "COST_CHILD"),
            (916, "COST_PURCHASE", 22, "Mua trong năm", "cost_purchase", "COST_INCREASE_CHILD"),
            (920, "COST_OTHER_INCREASE", 25, "Tăng khác", "cost_other", "COST_INCREASE_CHILD"),
            (925, "COST_DISPOSAL", 28, "Thanh lý", "cost_disposal", "COST_DECREASE_CHILD"),
            (928, "COST_ENDING", 32, "Số dư cuối năm", "cost_close", "COST_CHILD"),
            (930, "AMORTIZATION_OPENING", 37, "Số dư đầu năm", "dep_open", "AMORTIZATION_CHILD"),
            (
                931,
                "AMORTIZATION_CHARGE",
                41,
                "Hao mòn trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                933,
                "AMORTIZATION_OTHER_INCREASE",
                44,
                "Tăng khác",
                "dep_other_increase",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                940,
                "AMORTIZATION_OTHER_DECREASE",
                47,
                "Giảm khác",
                "dep_other_decrease",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (941, "AMORTIZATION_ENDING", 50, "Số dư cuối năm", "dep_close", "AMORTIZATION_CHILD"),
            (5970, "CARRYING_OPENING", 55, "Số dư đầu năm", "carry_open", "CARRYING_CHILD"),
            (5971, "CARRYING_ENDING", 59, "Số dư cuối năm", "carry_close", "CARRYING_CHILD"),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                63,
                "Nguyên giá tài sản cố định vô hình đã khấu hao hết nhưng vẫn còn sử dụng tại ngày 31 tháng",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_purchase", "cost_other", "cost_disposal"),
        "dep_movements": ("dep_charge", "dep_other_increase", "dep_other_decrease"),
    },
    {
        "code": "HDB",
        "page": 42,
        "owner": (8, "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        "branches": (
            ("COST", 24, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 43, "Giá trị hao mòn lũy kế"),
            ("CARRYING_VALUE", 61, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (30, "1.291.428"),
            "cost_increase": (33, "101.017"),
            "cost_disposal": (36, "(57)"),
            "cost_close": (42, "1.392.388"),
            "dep_open": (48, "412.956"),
            "dep_charge": (52, "92.210"),
            "dep_disposal": (55, "(57)"),
            "dep_close": (60, "505.109"),
            "carry_open": (67, "878.472"),
            "carry_close": (73, "887.279"),
            "fully": (80, "351.964"),
        },
        "mappings": (
            (915, "COST_OPENING", 25, "Số đầu năm", "cost_open", "COST_CHILD"),
            (5997, "COST_TOTAL_INCREASE", 31, "Tăng trong năm", "cost_increase", "COST_CHILD"),
            (
                925,
                "COST_DISPOSAL",
                34,
                "Thanh lý, nhượng bán",
                "cost_disposal",
                "COST_DECREASE_CHILD",
            ),
            (928, "COST_ENDING", 37, "Số cuối năm", "cost_close", "COST_CHILD"),
            (930, "AMORTIZATION_OPENING", 44, "Số đầu năm", "dep_open", "AMORTIZATION_CHILD"),
            (
                931,
                "AMORTIZATION_CHARGE",
                49,
                "Khấu hao trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                938,
                "AMORTIZATION_DISPOSAL",
                53,
                "Thanh lý, nhượng bán",
                "dep_disposal",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (941, "AMORTIZATION_ENDING", 56, "Số cuối năm", "dep_close", "AMORTIZATION_CHILD"),
            (5970, "CARRYING_OPENING", 62, "Số đầu năm", "carry_open", "CARRYING_CHILD"),
            (5971, "CARRYING_ENDING", 68, "Số cuối năm", "carry_close", "CARRYING_CHILD"),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                79,
                "Nguyên giá tài sản cố định vô hình khấu hao hết nhưng",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_increase", "cost_disposal"),
        "dep_movements": ("dep_charge", "dep_disposal"),
    },
    {
        "code": "VCB",
        "page": 49,
        "owner": (9, "Tài sản cố định vô hình"),
        "branches": (
            ("COST", 22, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 58, "Hao mòn lũy kế"),
            ("CARRYING_VALUE", 96, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (28, "5.072.735"),
            "cost_increase": (33, "303.093"),
            "cost_purchase": (37, "221.610"),
            "cost_other_increase": (42, "81.483"),
            "cost_decrease": (46, "(91.016)"),
            "cost_disposal": (49, "(18.032)"),
            "cost_other_decrease": (52, "(72.984)"),
            "cost_close": (57, "5.284.812"),
            "dep_open": (63, "2.510.437"),
            "dep_increase": (68, "303.200"),
            "dep_charge": (73, "251.244"),
            "dep_other_increase": (77, "51.956"),
            "dep_decrease": (82, "(73.344)"),
            "dep_disposal": (85, "(18.032)"),
            "dep_other_decrease": (90, "(55.312)"),
            "dep_close": (95, "2.740.293"),
            "carry_open": (101, "2.562.298"),
            "carry_close": (106, "2.544.519"),
            "fully": (
                108,
                "vẫn đang được sử dụng là 1.888.216 triệu VND (ngày 31 tháng 12 năm 2024: 1.729.254 triệu VND).",
                "1.888.216",
            ),
        },
        "mappings": (
            (915, "COST_OPENING", 24, "Số dư đầu năm", "cost_open", "COST_CHILD"),
            (5997, "COST_TOTAL_INCREASE", 29, "Tăng trong năm", "cost_increase", "COST_CHILD"),
            (916, "COST_PURCHASE", 34, "Mua mới", "cost_purchase", "COST_INCREASE_CHILD"),
            (
                920,
                "COST_OTHER_INCREASE",
                39,
                "Tăng khác",
                "cost_other_increase",
                "COST_INCREASE_CHILD",
            ),
            (6068, "COST_TOTAL_DECREASE", 43, "Giảm trong năm", "cost_decrease", "COST_CHILD"),
            (
                925,
                "COST_DISPOSAL",
                47,
                "Thanh lý, nhượng bán",
                "cost_disposal",
                "COST_DECREASE_CHILD",
            ),
            (
                927,
                "COST_OTHER_DECREASE",
                50,
                "Giảm khác",
                "cost_other_decrease",
                "COST_DECREASE_CHILD",
            ),
            (928, "COST_ENDING", 53, "Số dư cuối năm", "cost_close", "COST_CHILD"),
            (930, "AMORTIZATION_OPENING", 59, "Số dư đầu năm", "dep_open", "AMORTIZATION_CHILD"),
            (
                5999,
                "AMORTIZATION_TOTAL_INCREASE",
                64,
                "Tăng trong năm",
                "dep_increase",
                "AMORTIZATION_CHILD",
            ),
            (
                931,
                "AMORTIZATION_CHARGE",
                69,
                "Hao mòn",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                933,
                "AMORTIZATION_OTHER_INCREASE",
                74,
                "Tăng khác",
                "dep_other_increase",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                6000,
                "AMORTIZATION_TOTAL_DECREASE",
                78,
                "Giảm trong năm",
                "dep_decrease",
                "AMORTIZATION_CHILD",
            ),
            (
                938,
                "AMORTIZATION_DISPOSAL",
                83,
                "Thanh lý, nhượng bán",
                "dep_disposal",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                940,
                "AMORTIZATION_OTHER_DECREASE",
                86,
                "Giảm khác",
                "dep_other_decrease",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (941, "AMORTIZATION_ENDING", 91, "Số dư cuối năm", "dep_close", "AMORTIZATION_CHILD"),
            (5970, "CARRYING_OPENING", 97, "Số dư đầu năm", "carry_open", "CARRYING_CHILD"),
            (5971, "CARRYING_ENDING", 102, "Số dư cuối năm", "carry_close", "CARRYING_CHILD"),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                107,
                "Tại ngày 31 tháng 12 năm 2025, nguyên giá các tài sản cố định vô hình đã được hao mòn hết nhưng",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_increase", "cost_decrease"),
        "dep_movements": ("dep_increase", "dep_decrease"),
    },
    {
        "code": "CTG",
        "page": 49,
        "owner": (16, "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        "branches": (
            ("COST", 26, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 47, "Giá trị hao mòn lũy kế"),
            ("CARRYING_VALUE", 67, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (30, "6.927.826"),
            "cost_purchase": (34, "525.220"),
            "cost_disposal": (38, "(85.998)"),
            "cost_other": (42, "(3.189)"),
            "cost_close": (46, "7.363.859"),
            "dep_open": (51, "(3.074.885)"),
            "dep_charge": (55, "(204.750)"),
            "dep_disposal": (59, "10.712"),
            "dep_other": (62, "2.790"),
            "dep_close": (66, "(3.266.133)"),
            "carry_open": (71, "3.852.941"),
            "carry_close": (75, "4.097.726"),
            "fully": (83, "2.295.278"),
        },
        "mappings": (
            (915, "COST_OPENING", 27, "Tại ngày 1 tháng 1 năm 2025", "cost_open", "COST_CHILD"),
            (916, "COST_PURCHASE", 31, "Mua trong năm", "cost_purchase", "COST_INCREASE_CHILD"),
            (
                925,
                "COST_DISPOSAL",
                35,
                "Thanh lý, nhượng bán",
                "cost_disposal",
                "COST_DECREASE_CHILD",
            ),
            (927, "COST_OTHER_DECREASE", 39, "Giảm khác", "cost_other", "COST_DECREASE_CHILD"),
            (928, "COST_ENDING", 43, "Tại ngày 31 tháng 12 năm 2025", "cost_close", "COST_CHILD"),
            (
                930,
                "AMORTIZATION_OPENING",
                48,
                "Tại ngày 1 tháng 1 năm 2025",
                "dep_open",
                "AMORTIZATION_CHILD",
            ),
            (
                931,
                "AMORTIZATION_CHARGE",
                52,
                "Khấu hao trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                938,
                "AMORTIZATION_DISPOSAL",
                56,
                "Thanh lý, nhượng bán",
                "dep_disposal",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                940,
                "AMORTIZATION_OTHER_DECREASE",
                60,
                "Giảm khác",
                "dep_other",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                941,
                "AMORTIZATION_ENDING",
                63,
                "Tại ngày 31 tháng 12 năm 2025",
                "dep_close",
                "AMORTIZATION_CHILD",
            ),
            (
                5970,
                "CARRYING_OPENING",
                68,
                "Tại ngày 1 tháng 1 năm 2025",
                "carry_open",
                "CARRYING_CHILD",
            ),
            (
                5971,
                "CARRYING_ENDING",
                72,
                "Tại ngày 31 tháng 12 năm 2025",
                "carry_close",
                "CARRYING_CHILD",
            ),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                81,
                "Nguyên giá TSCĐ vô hình đã khấu hao hết nhưng",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_purchase", "cost_disposal", "cost_other"),
        "dep_movements": ("dep_charge", "dep_disposal", "dep_other"),
        "amortization_is_negative": True,
    },
    {
        "code": "BID",
        "page": 48,
        "owner": (19, "Tài sản cố định vô hình"),
        "branches": (
            ("COST", 32, "Nguyên giá TSCĐ vô hình"),
            ("ACCUMULATED_AMORTIZATION", 56, "Giá trị hao mòn lũy kế"),
            ("CARRYING_VALUE", 80, "Giá trị còn lại của TSCĐ vô hình"),
        ),
        "values": {
            "cost_open": (37, "8.103.328"),
            "cost_purchase": (42, "573.664"),
            "cost_disposal": (45, "(2.414)"),
            "cost_other": (50, "10.194"),
            "cost_close": (55, "8.684.772"),
            "dep_open": (61, "2.782.716"),
            "dep_charge": (66, "316.106"),
            "dep_disposal": (69, "(2.414)"),
            "dep_other": (73, "6.104"),
            "dep_close": (78, "3.102.512"),
            "carry_open": (86, "5.320.612"),
            "carry_close": (91, "5.582.260"),
            "fully": (109, "1.760.913"),
        },
        "mappings": (
            (915, "COST_OPENING", 33, "Số dư đầu năm", "cost_open", "COST_CHILD"),
            (916, "COST_PURCHASE", 38, "Mua trong năm", "cost_purchase", "COST_INCREASE_CHILD"),
            (
                925,
                "COST_DISPOSAL",
                43,
                "Thanh lý, nhượng bán",
                "cost_disposal",
                "COST_DECREASE_CHILD",
            ),
            (920, "COST_OTHER_INCREASE", 46, "Tăng khác", "cost_other", "COST_INCREASE_CHILD"),
            (928, "COST_ENDING", 51, "Số dư cuối năm", "cost_close", "COST_CHILD"),
            (930, "AMORTIZATION_OPENING", 57, "Số dư đầu năm", "dep_open", "AMORTIZATION_CHILD"),
            (
                931,
                "AMORTIZATION_CHARGE",
                62,
                "Khấu hao trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                938,
                "AMORTIZATION_DISPOSAL",
                67,
                "Thanh lý, nhượng bán",
                "dep_disposal",
                "AMORTIZATION_DECREASE_CHILD",
            ),
            (
                933,
                "AMORTIZATION_OTHER_INCREASE",
                70,
                "Tăng khác",
                "dep_other",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (941, "AMORTIZATION_ENDING", 74, "Số dư cuối năm", "dep_close", "AMORTIZATION_CHILD"),
            (5970, "CARRYING_OPENING", 82, "Số dư đầu năm", "carry_open", "CARRYING_CHILD"),
            (5971, "CARRYING_ENDING", 87, "Số dư cuối năm", "carry_close", "CARRYING_CHILD"),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                108,
                "Nguyên giá của TSCĐ vô hình đã khấu",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_purchase", "cost_disposal", "cost_other"),
        "dep_movements": ("dep_charge", "dep_disposal", "dep_other"),
    },
    {
        "code": "VIB",
        "page": 43,
        "owner": (5, "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
        "branches": (
            ("COST", 14, "Nguyên giá"),
            ("ACCUMULATED_AMORTIZATION", 29, "Hao mòn luỹ kế"),
            ("CARRYING_VALUE", 41, "Giá trị còn lại"),
        ),
        "values": {
            "cost_open": (18, "777.031"),
            "cost_purchase": (21, "66.813"),
            "cost_disposal": (24, "(341)"),
            "cost_close": (28, "843.503"),
            "dep_open": (33, "474.968"),
            "dep_charge": (36, "70.591"),
            "dep_close": (40, "545.559"),
            "carry_open": (44, "302.063"),
            "carry_close": (48, "297.944"),
            "fully": (55, "297.661"),
        },
        "mappings": (
            (915, "COST_OPENING", 15, "Tại ngày 1/1/2025", "cost_open", "COST_CHILD"),
            (916, "COST_PURCHASE", 19, "Mua trong năm", "cost_purchase", "COST_INCREASE_CHILD"),
            (
                925,
                "COST_DISPOSAL",
                22,
                "Thanh lý trong năm",
                "cost_disposal",
                "COST_DECREASE_CHILD",
            ),
            (928, "COST_ENDING", 25, "Tại ngày 31/12/2025", "cost_close", "COST_CHILD"),
            (
                930,
                "AMORTIZATION_OPENING",
                30,
                "Tại ngày 1/1/2025",
                "dep_open",
                "AMORTIZATION_CHILD",
            ),
            (
                931,
                "AMORTIZATION_CHARGE",
                34,
                "Hao mòn trong năm",
                "dep_charge",
                "AMORTIZATION_INCREASE_CHILD",
            ),
            (
                941,
                "AMORTIZATION_ENDING",
                37,
                "Tại ngày 31/12/2025",
                "dep_close",
                "AMORTIZATION_CHILD",
            ),
            (5970, "CARRYING_OPENING", 42, "Tại ngày 1/1/2025", "carry_open", "CARRYING_CHILD"),
            (5971, "CARRYING_ENDING", 46, "Tại ngày 31/12/2025", "carry_close", "CARRYING_CHILD"),
            (
                6069,
                "FULLY_AMORTIZED_STILL_IN_USE",
                54,
                "Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn",
                "fully",
                "FAMILY_DISCLOSURE_CHILD",
            ),
        ),
        "cost_movements": ("cost_purchase", "cost_disposal"),
        "dep_movements": ("dep_charge",),
    },
)


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents = []
    for spec in _DOCUMENT_SPECS:
        values = _values(base, spec["values"])
        documents.append(
            base._present_doc(
                spec["code"],
                spec["page"],
                spec["owner"][0],
                spec["owner"][1],
                "2025-12-31",
                spec["branches"],
                [_mapping(base, values, raw) for raw in spec["mappings"]],
                _four_equations(
                    base,
                    values,
                    spec["cost_movements"],
                    spec["dep_movements"],
                    amortization_is_negative=spec.get("amortization_is_negative", False),
                ),
            )
        )
    return documents


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mappings = [mapping for trial in trials for mapping in trial["mappings"]]
    values = [mapping["value"] for mapping in mappings]
    return {
        "accounting_equation_count": sum(len(trial["equations"]) for trial in trials),
        "document_count": len(trials),
        "inline_disclosure_value_count": sum(
            mapping["role"] == "FULLY_AMORTIZED_STILL_IN_USE"
            and " " in mapping["value"]["source_numeric_challenger"]
            for mapping in mappings
        ),
        "mapping_verified_count": len(mappings),
        "open_review_item_count": 0,
        "rotated_semantic_rescue_line_count": EXPECTED_RESCUE_LINE_COUNT,
        "source_ppocrv6_numeric_match_count": sum(
            value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
            for value in values
        ),
        "verified_present_document_count": sum(bool(trial["mappings"]) for trial in trials),
    }


def _configure_base() -> ModuleType:
    base = _load_module(
        "annual_2025_intangible_fixed_assets_mapping_base",
        "scripts/experiments/build_tangible_fixed_assets_8bank_codex_verified_mapping_v1.py",
    )
    scanner = _load_module(
        "annual_2025_intangible_fixed_assets_scanner",
        "scripts/experiments/scan_intangible_fixed_assets_full_document_vietocr_v1.py",
    )
    scanner.FORMAT_VERSION = SCAN_FORMAT
    scanner.MATCHER_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
    scanner.SCAN_ID_PREFIX = SCAN_ID_PREFIX
    scanner.build_tangible_fixed_assets_full_document_scan_v1 = (
        scanner.build_intangible_fixed_assets_full_document_scan_v1
    )
    support = scanner._support()

    base.scanner = scanner
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.EXPECTED_RESCUE_LINE_COUNT = EXPECTED_RESCUE_LINE_COUNT
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._REVIEW_RUN_ID = "E-0125"
    base._SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": "VERIFIED_AUDITED_ANNUAL_2025_CURRENT_AND_2024_OPENING_PERIODS"
    }
    base._REQUIRE_ROTATED_VIETOCR_NUMERIC_MATCH = False
    base._NUMERIC_CHALLENGER_INPUT_KEY = "upstream_ppocrv6_numeric_axis"
    base._REVIEW_CHECKS = list(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._SCHEMA_DISPLAY_ORDER_SNAPSHOT = dict(_SCHEMA_DISPLAY_ORDER_SNAPSHOT)
    base._schema_authority_for_output = lambda _live: canonical_clone_v1(_SCHEMA_AUTHORITY)
    base._metrics = _annual_metrics
    base._review_documents = lambda: _review_documents(base)
    base._load_live_rescue = lambda semantic: support._profile_rescue(
        semantic, support.DEFAULT_RESCUE_ROOT
    )
    base._rotated_ppocr_evidence = lambda: {
        "input_refs": {
            "mode": "CROP_MANIFEST_BOUND_UPSTREAM_PPOCRV6_COMPLETE_LINE_AXIS",
            "separate_rotated_numeric_run_required": False,
        },
        "rec_scores": [],
        "rec_texts": [],
    }
    return base


def _validate_expected_ids(value: dict[str, Any]) -> dict[str, Any]:
    trials = value.get("trials")
    if type(trials) is not list or len(trials) != 8:
        raise _error("annual intangible-fixed-assets trial denominator drifted")
    for trial in trials:
        code = trial.get("document_provenance")
        actual = {mapping.get("report_norm_id") for mapping in trial.get("mappings", [])}
        if actual != _EXPECTED_IDS.get(code):
            raise _error(f"annual intangible-fixed-assets schema coverage drifted: {code}")
    if value.get("metrics") != {
        "accounting_equation_count": 32,
        "document_count": 8,
        "inline_disclosure_value_count": 3,
        "mapping_verified_count": 107,
        "open_review_item_count": 0,
        "rotated_semantic_rescue_line_count": 3338,
        "source_ppocrv6_numeric_match_count": 107,
        "verified_present_document_count": 8,
    }:
        raise _error("annual intangible-fixed-assets metrics drifted")
    return value


def build_annual_2025_intangible_fixed_assets_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _configure_base()._review_blueprint()


def build_live_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    try:
        return _validate_expected_ids(
            _configure_base().build_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1()
        )
    except Annual2025IntangibleFixedAssets8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _validate_expected_ids(
            _configure_base().validate_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1(
                value
            )
        )
    except Annual2025IntangibleFixedAssets8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    base = _configure_base()
    if args.write_review:
        base._write(REVIEW_PATH, base._review_blueprint())
    result = build_live_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_v1()
    if args.write_result:
        base._write(RESULT_PATH, result)
    elif args.verify:
        persisted, _ = base._stable_json(RESULT_PATH)
        validate_annual_2025_intangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
            persisted
        )
        print(persisted["result_id"])
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
