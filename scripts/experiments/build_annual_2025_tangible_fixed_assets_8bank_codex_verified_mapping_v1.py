"""Verify tangible fixed-asset movement notes in eight annual-2025 PDFs.

The annual profile reuses the bank-blind whole-document variant graph.  It
binds schema identities only after structural and numeric verification, and
keeps one family-local schema-order snapshot so unrelated schema insertions do
not invalidate this evidence.
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
FORMAT_VERSION = "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025tfa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025tfa8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0123-annual-2025-tangible-fixed-assets-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0123-annual-2025-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "tfafdsv1:scan:3bbda7c0a4b2b6228cfeb9edbdd9209c2344fc88a8d90e8df3ce75873cb2ead2"
EXPECTED_RESCUE_LINE_COUNT = 3338
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")

_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_GENERIC_TANGIBLE_FIXED_ASSET_VARIANT_GRAPH_OPTIONAL_MOVEMENT_"
    "ROWS_ROTATED_PPOCRV6_NUMERIC_CHALLENGER_VISIBLE_PIXEL_ANNUAL_PERIOD_"
    "ACCOUNTING_AND_FAMILY_LOCAL_STABLE_TM_SCHEMA_BINDING_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "OWNER_PRECEDES_COST_DEPRECIATION_AND_CARRYING_BRANCHES",
    "OPTIONAL_MOVEMENT_ROWS_AND_ASSET_CLASS_COLUMNS",
    "ANNUAL_CURRENT_AND_OPENING_PERIOD_AXES",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_AND_SIGNS",
    "PPOCRV6_NUMERIC_CHALLENGER_MATCHES_VISIBLE_PIXEL",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "COST_AND_DEPRECIATION_EQUAL_CARRYING_VALUE",
    "LIVE_TM_SCHEMA_ID_NAME_AND_PARENT_COMPATIBILITY",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_PPOCRV6_NUMERIC_CHALLENGER",
    "optional_movement_rows_required_in_every_bank": False,
    "schema_global_display_order_used_as_stable_identity": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_and_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_id_name_and_parent_checked": True,
    "mapping_authority_bounded_to_eight_unique_annual_tangible_asset_regions": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_additions_outside_family_change_detection_or_mapping": False,
    "text_similarity_alone_used_for_mapping": False,
}
_SCHEMA_AUTHORITY = {
    "binding_mode": "FAMILY_LOCAL_STABLE_REPORT_NORM_ID_NAME_AND_PARENT",
    "family_root_report_norm_id": 868,
    "global_display_order_is_identity": False,
    "live_compatibility_rechecked_on_every_replay": True,
    "snapshot_label": "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_FAMILY_V1",
}
_SCHEMA_EXPECTED = {
    870: ("Số dư đầu kỳ", 869),
    5991: ("Tổng tăng nguyên giá TSCĐ hữu hình trong kỳ", 869),
    871: ("+ Mua trong kỳ", 5991),
    872: ("+ Đầu tư XDCB hoàn thành", 5991),
    875: ("+ Tăng khác", 5991),
    5992: ("Tổng giảm nguyên giá TSCĐ hữu hình trong kỳ", 869),
    879: ("+ Phân loại lại", 5992),
    880: ("+ Thanh lý. nhượng bán (*)", 5992),
    881: ("+ Giảm khác (*)", 5992),
    5993: ("Tăng/(Giảm) khác nguyên giá TSCĐ hữu hình trong kỳ", 869),
    5962: ("+ Chênh lệch tỷ giá", 869),
    882: ("Số dư cuối kỳ", 869),
    884: ("Số dư đầu kỳ", 883),
    5994: ("Tổng tăng hao mòn TSCĐ hữu hình trong kỳ", 883),
    885: ("+ Khấu hao trong kỳ", 5994),
    887: ("+ Tăng khác", 5994),
    5995: ("Tổng giảm hao mòn TSCĐ hữu hình trong kỳ", 883),
    891: ("+ Phân loại lại", 5995),
    892: ("+ Thanh lý. nhượng bán (*)", 5995),
    894: ("+ Giảm khác (*)", 5995),
    5996: ("Tăng/(Giảm) khác hao mòn TSCĐ hữu hình trong kỳ", 883),
    5963: ("+ Chênh lệch tỷ giá", 883),
    895: ("Số dư cuối kỳ", 883),
    5965: ("Số dư đầu kỳ", 5964),
    5966: ("Số dư cuối kỳ", 5964),
}
_SCHEMA_DISPLAY_ORDER_SNAPSHOT = {
    870: 340,
    5991: 341,
    871: 342,
    872: 343,
    875: 346,
    5992: 347,
    879: 351,
    880: 352,
    881: 353,
    5993: 354,
    5962: 355,
    882: 356,
    884: 358,
    5994: 359,
    885: 360,
    887: 362,
    5995: 363,
    891: 367,
    892: 368,
    894: 370,
    5996: 371,
    5963: 372,
    895: 373,
    5965: 375,
    5966: 376,
}
_EXPECTED_IDS = {
    "ACB": {870, 5991, 872, 879, 880, 5993, 882, 884, 885, 892, 895, 5965, 5966},
    "MBB": {
        870,
        5991,
        879,
        880,
        5962,
        882,
        884,
        885,
        887,
        891,
        892,
        5963,
        895,
        5965,
        5966,
    },
    "VPB": {870, 871, 875, 880, 882, 884, 885, 892, 895, 5965, 5966},
    "HDB": {870, 5991, 880, 881, 882, 884, 885, 892, 894, 895, 5965, 5966},
    "VCB": {
        870,
        5991,
        871,
        875,
        5992,
        880,
        881,
        882,
        884,
        5994,
        885,
        887,
        5995,
        892,
        894,
        895,
        5965,
        5966,
    },
    "CTG": {870, 871, 872, 880, 5993, 882, 884, 885, 892, 5996, 895, 5965, 5966},
    "BID": {870, 871, 872, 880, 5993, 882, 884, 885, 892, 5996, 895, 5965, 5966},
    "VIB": {870, 871, 880, 882, 884, 885, 892, 895, 5965, 5966},
}


class Annual2025TangibleFixedAssets8BankError(ValueError):
    """Annual tangible-asset graph, pixels, numbers or schema drifted."""


def _error(message: str) -> Annual2025TangibleFixedAssets8BankError:
    return Annual2025TangibleFixedAssets8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _values(base: ModuleType, entries: Mapping[str, tuple[int, str, int | None]]) -> dict[str, Any]:
    return {
        key: base._value(line_index, text, ppocr_rotated_line_index=ppocr_index)
        for key, (line_index, text, ppocr_index) in entries.items()
    }


def _mapping(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    label_line_index: int,
    label: str,
    value: dict[str, Any],
    topology: str,
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        label_line_index,
        label,
        value,
        topology=topology,
    )


def _four_equations(
    base: ModuleType,
    values: Mapping[str, dict[str, Any]],
    cost_movements: Sequence[str],
    depreciation_movements: Sequence[str],
    *,
    depreciation_is_negative: bool = False,
) -> list[dict[str, Any]]:
    depreciation_multiplier = 1 if depreciation_is_negative else -1
    return [
        base._equation(
            "COST_ROLLFORWARD",
            [base._term(values[name]) for name in ("cost_open", *cost_movements)],
            values["cost_close"],
        ),
        base._equation(
            "DEPRECIATION_ROLLFORWARD",
            [base._term(values[name]) for name in ("dep_open", *depreciation_movements)],
            values["dep_close"],
        ),
        base._equation(
            "OPENING_COST_AND_DEPRECIATION_TO_CARRYING_VALUE",
            [
                base._term(values["cost_open"]),
                base._term(values["dep_open"], depreciation_multiplier),
            ],
            values["carry_open"],
        ),
        base._equation(
            "ENDING_COST_AND_DEPRECIATION_TO_CARRYING_VALUE",
            [
                base._term(values["cost_close"]),
                base._term(values["dep_close"], depreciation_multiplier),
            ],
            values["carry_close"],
        ),
    ]


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    acb = _values(
        base,
        {
            "cost_open": (25, "6.504.276", None),
            "cost_increase": (31, "203.419", None),
            "cost_xdcb": (37, "235.497", None),
            "cost_disposal": (43, "(131.723)", None),
            "cost_reclass": (46, "(4.869)", None),
            "cost_other": (50, "(492)", None),
            "cost_close": (56, "6.806.108", None),
            "dep_open": (63, "3.282.078", None),
            "dep_charge": (69, "452.335", None),
            "dep_disposal": (75, "(128.792)", None),
            "dep_close": (81, "3.605.621", None),
            "carry_open": (88, "3.222.198", None),
            "carry_close": (94, "3.200.487", None),
        },
    )
    docs.append(
        base._present_doc(
            "ACB",
            55,
            7,
            "Tài sản cố định (TSCĐ) hữu hình",
            "2025-12-31",
            [
                ("COST", 19, "Nguyên giá"),
                ("ACCUMULATED_DEPRECIATION", 57, "Hao mòn lũy kế"),
                ("CARRYING_VALUE", 82, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    base,
                    870,
                    "COST_OPENING",
                    20,
                    "Tại ngày 1 tháng 1 năm 2025",
                    acb["cost_open"],
                    "COST_CHILD",
                ),
                _mapping(
                    base,
                    5991,
                    "COST_TOTAL_INCREASE",
                    26,
                    "Tăng trong năm",
                    acb["cost_increase"],
                    "COST_CHILD",
                ),
                _mapping(
                    base,
                    872,
                    "COST_XDCB_COMPLETED",
                    32,
                    "Đầu tư xây dựng cơ bản hoàn thành",
                    acb["cost_xdcb"],
                    "COST_CHILD",
                ),
                _mapping(
                    base, 880, "COST_DISPOSAL", 38, "Thanh lý", acb["cost_disposal"], "COST_CHILD"
                ),
                _mapping(
                    base,
                    879,
                    "COST_RECLASSIFICATION",
                    44,
                    "Phân loại lại",
                    acb["cost_reclass"],
                    "COST_CHILD",
                ),
                _mapping(
                    base,
                    5993,
                    "COST_OTHER_NET",
                    47,
                    "Biến động khác",
                    acb["cost_other"],
                    "COST_CHILD",
                ),
                _mapping(
                    base,
                    882,
                    "COST_ENDING",
                    51,
                    "Tại ngày 31 tháng 12 năm 2025",
                    acb["cost_close"],
                    "COST_CHILD",
                ),
                _mapping(
                    base,
                    884,
                    "DEPRECIATION_OPENING",
                    58,
                    "Tại ngày 1 tháng 1 năm 2025",
                    acb["dep_open"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    885,
                    "DEPRECIATION_CHARGE",
                    64,
                    "Khấu hao trong năm",
                    acb["dep_charge"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    892,
                    "DEPRECIATION_DISPOSAL",
                    70,
                    "Thanh lý",
                    acb["dep_disposal"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    895,
                    "DEPRECIATION_ENDING",
                    76,
                    "Tại ngày 31 tháng 12 năm 2025",
                    acb["dep_close"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    5965,
                    "CARRYING_OPENING",
                    83,
                    "Tại ngày 1 tháng 1 năm 2025",
                    acb["carry_open"],
                    "CARRYING_CHILD",
                ),
                _mapping(
                    base,
                    5966,
                    "CARRYING_ENDING",
                    89,
                    "Tại ngày 31 tháng 12 năm 2025",
                    acb["carry_close"],
                    "CARRYING_CHILD",
                ),
            ],
            _four_equations(
                base,
                acb,
                ("cost_increase", "cost_xdcb", "cost_disposal", "cost_reclass", "cost_other"),
                ("dep_charge", "dep_disposal"),
            ),
        )
    )

    mbb = _values(
        base,
        {
            "cost_open": (30, "9.014.672", None),
            "cost_increase": (36, "754.094", None),
            "cost_disposal": (42, "(354.092)", None),
            "cost_reclass": (47, "(44)", None),
            "cost_fx": (53, "8.606", None),
            "cost_close": (59, "9.423.236", None),
            "dep_open": (66, "5.263.976", None),
            "dep_charge": (72, "551.766", None),
            "dep_disposal": (78, "(201.454)", None),
            "dep_audit": (81, "1.221", None),
            "dep_reclass": (86, "(31)", None),
            "dep_fx": (92, "2.225", None),
            "dep_close": (98, "5.617.703", None),
            "carry_open": (105, "3.750.696", None),
            "carry_close": (111, "3.805.533", None),
        },
    )
    docs.append(
        base._present_doc(
            "MBB",
            58,
            8,
            "TÀI SẢN CỐ ĐỊNH HỮU HÌNH",
            "2025-12-31",
            [
                ("COST", 24, "Nguyên giá"),
                ("ACCUMULATED_DEPRECIATION", 60, "Giá trị hao mòn lũy kế"),
                ("CARRYING_VALUE", 99, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    base, 870, "COST_OPENING", 25, "Số dư đầu năm", mbb["cost_open"], "COST_CHILD"
                ),
                _mapping(
                    base,
                    5991,
                    "COST_TOTAL_INCREASE",
                    31,
                    "Tăng trong năm",
                    mbb["cost_increase"],
                    "COST_CHILD",
                ),
                _mapping(
                    base, 880, "COST_DISPOSAL", 37, "Thanh lý", mbb["cost_disposal"], "COST_CHILD"
                ),
                _mapping(
                    base,
                    879,
                    "COST_RECLASSIFICATION",
                    43,
                    "Phân loại lại trong năm",
                    mbb["cost_reclass"],
                    "COST_CHILD",
                ),
                _mapping(
                    base,
                    5962,
                    "COST_FOREIGN_EXCHANGE",
                    48,
                    "Chênh lệch tỷ giá",
                    mbb["cost_fx"],
                    "COST_CHILD",
                ),
                _mapping(
                    base, 882, "COST_ENDING", 54, "Số dư cuối năm", mbb["cost_close"], "COST_CHILD"
                ),
                _mapping(
                    base,
                    884,
                    "DEPRECIATION_OPENING",
                    61,
                    "Số dư đầu năm",
                    mbb["dep_open"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    885,
                    "DEPRECIATION_CHARGE",
                    67,
                    "Khấu hao trong năm",
                    mbb["dep_charge"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    892,
                    "DEPRECIATION_DISPOSAL",
                    73,
                    "Thanh lý",
                    mbb["dep_disposal"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    887,
                    "DEPRECIATION_OTHER_INCREASE",
                    79,
                    "Điều chỉnh theo Kiểm toán Nhà nước",
                    mbb["dep_audit"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    891,
                    "DEPRECIATION_RECLASSIFICATION",
                    82,
                    "Phân loại lại trong năm",
                    mbb["dep_reclass"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    5963,
                    "DEPRECIATION_FOREIGN_EXCHANGE",
                    87,
                    "Chênh lệch tỷ giá",
                    mbb["dep_fx"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    895,
                    "DEPRECIATION_ENDING",
                    93,
                    "Số dư cuối năm",
                    mbb["dep_close"],
                    "DEPRECIATION_CHILD",
                ),
                _mapping(
                    base,
                    5965,
                    "CARRYING_OPENING",
                    100,
                    "Số dư đầu năm",
                    mbb["carry_open"],
                    "CARRYING_CHILD",
                ),
                _mapping(
                    base,
                    5966,
                    "CARRYING_ENDING",
                    106,
                    "Số dư cuối năm",
                    mbb["carry_close"],
                    "CARRYING_CHILD",
                ),
            ],
            _four_equations(
                base,
                mbb,
                ("cost_increase", "cost_disposal", "cost_reclass", "cost_fx"),
                ("dep_charge", "dep_disposal", "dep_audit", "dep_reclass", "dep_fx"),
            ),
        )
    )

    vpb = _values(
        base,
        {
            "cost_open": (33, "3.406.801", None),
            "cost_purchase": (38, "88.193", None),
            "cost_other": (42, "320.549", None),
            "cost_disposal": (48, "(37.656)", None),
            "cost_close": (55, "3.777.887", None),
            "dep_open": (63, "1.969.719", None),
            "dep_charge": (70, "366.500", None),
            "dep_disposal": (76, "(37.601)", None),
            "dep_close": (83, "2.298.618", None),
            "carry_open": (91, "1.437.082", None),
            "carry_close": (97, "1.479.269", None),
        },
    )
    docs.append(
        _simple_document(
            base,
            "VPB",
            53,
            7,
            (26, 56, 84),
            vpb,
            [
                (870, "COST_OPENING", 27, "Số dư đầu năm", "cost_open"),
                (871, "COST_PURCHASE", 34, "Mua trong năm", "cost_purchase"),
                (875, "COST_OTHER_INCREASE", 39, "Tăng khác", "cost_other"),
                (880, "COST_DISPOSAL", 43, "Thanh lý, nhượng bán", "cost_disposal"),
                (882, "COST_ENDING", 49, "Số dư cuối năm", "cost_close"),
                (884, "DEPRECIATION_OPENING", 57, "Số dư đầu năm", "dep_open"),
                (885, "DEPRECIATION_CHARGE", 64, "Khấu hao trong năm", "dep_charge"),
                (892, "DEPRECIATION_DISPOSAL", 71, "Thanh lý, nhượng bán", "dep_disposal"),
                (895, "DEPRECIATION_ENDING", 77, "Số dư cuối năm", "dep_close"),
                (5965, "CARRYING_OPENING", 85, "Số dư đầu năm", "carry_open"),
                (5966, "CARRYING_ENDING", 92, "Số dư cuối năm", "carry_close"),
            ],
            ("cost_purchase", "cost_other", "cost_disposal"),
            ("dep_charge", "dep_disposal"),
            branch_labels=("Nguyên giá", "Giá trị khấu hao lũy kế", "Giá trị còn lại"),
        )
    )

    hdb = _values(
        base,
        {
            "cost_open": (88, "1.983.500", None),
            "cost_increase": (95, "249.286", None),
            "cost_disposal": (102, "(63.576)", None),
            "cost_other": (105, "(30)", None),
            "cost_close": (112, "2.169.180", None),
            "dep_open": (120, "1.096.045", None),
            "dep_charge": (127, "159.797", None),
            "dep_disposal": (134, "(59.816)", None),
            "dep_other": (137, "(3)", None),
            "dep_close": (144, "1.196.023", None),
            "carry_open": (152, "887.455", None),
            "carry_close": (159, "973.157", None),
        },
    )
    docs.append(
        _simple_document(
            base,
            "HDB",
            41,
            67,
            (81, 113, 145),
            hdb,
            [
                (870, "COST_OPENING", 82, "Số đầu năm", "cost_open"),
                (5991, "COST_TOTAL_INCREASE", 89, "Tăng trong năm", "cost_increase"),
                (880, "COST_DISPOSAL", 96, "Thanh lý, nhượng bán", "cost_disposal"),
                (881, "COST_OTHER_DECREASE", 103, "Giảm khác", "cost_other"),
                (882, "COST_ENDING", 106, "Số cuối năm", "cost_close"),
                (884, "DEPRECIATION_OPENING", 114, "Số đầu năm", "dep_open"),
                (885, "DEPRECIATION_CHARGE", 121, "Khấu hao trong năm", "dep_charge"),
                (892, "DEPRECIATION_DISPOSAL", 128, "Thanh lý, nhượng bán", "dep_disposal"),
                (894, "DEPRECIATION_OTHER_DECREASE", 135, "Giảm khác", "dep_other"),
                (895, "DEPRECIATION_ENDING", 138, "Số cuối năm", "dep_close"),
                (5965, "CARRYING_OPENING", 146, "Số đầu năm", "carry_open"),
                (5966, "CARRYING_ENDING", 153, "Số cuối năm", "carry_close"),
            ],
            ("cost_increase", "cost_disposal", "cost_other"),
            ("dep_charge", "dep_disposal", "dep_other"),
        )
    )

    vcb = _values(
        base,
        {
            "cost_open": (40, "15.808.302", None),
            "cost_inc_total": (46, "1.237.452", None),
            "cost_purchase": (52, "1.231.878", None),
            "cost_other_inc": (57, "5.574", None),
            "cost_dec_total": (64, "(773.874)", None),
            "cost_disposal": (70, "(766.748)", None),
            "cost_other_dec": (75, "(7.126)", None),
            "cost_close": (81, "16.271.880", None),
            "dep_open": (88, "10.277.723", None),
            "dep_inc_total": (94, "1.155.152", None),
            "dep_charge": (100, "1.134.454", None),
            "dep_other_inc": (105, "20.698", None),
            "dep_dec_total": (112, "(779.788)", None),
            "dep_disposal": (119, "(766.097)", None),
            "dep_other_dec": (123, "(13.691)", None),
            "dep_close": (131, "10.653.087", None),
            "carry_open": (138, "5.530.579", None),
            "carry_close": (144, "5.618.793", None),
        },
    )
    docs.append(
        _simple_document(
            base,
            "VCB",
            48,
            9,
            (34, 82, 132),
            vcb,
            [
                (870, "COST_OPENING", 35, "Số dư đầu năm", "cost_open"),
                (5991, "COST_TOTAL_INCREASE", 41, "Tăng trong năm", "cost_inc_total"),
                (871, "COST_PURCHASE", 47, "Mua mới", "cost_purchase"),
                (875, "COST_OTHER_INCREASE", 53, "Tăng khác", "cost_other_inc"),
                (5992, "COST_TOTAL_DECREASE", 59, "Giảm trong năm", "cost_dec_total"),
                (880, "COST_DISPOSAL", 65, "Thanh lý, nhượng bán", "cost_disposal"),
                (881, "COST_OTHER_DECREASE", 71, "Giảm khác", "cost_other_dec"),
                (882, "COST_ENDING", 76, "Số dư cuối năm", "cost_close"),
                (884, "DEPRECIATION_OPENING", 83, "Số dư đầu năm", "dep_open"),
                (5994, "DEPRECIATION_TOTAL_INCREASE", 89, "Tăng trong năm", "dep_inc_total"),
                (885, "DEPRECIATION_CHARGE", 95, "Khấu hao", "dep_charge"),
                (887, "DEPRECIATION_OTHER_INCREASE", 101, "Tăng khác", "dep_other_inc"),
                (5995, "DEPRECIATION_TOTAL_DECREASE", 107, "Giảm trong năm", "dep_dec_total"),
                (892, "DEPRECIATION_DISPOSAL", 114, "Thanh lý, nhượng bán", "dep_disposal"),
                (894, "DEPRECIATION_OTHER_DECREASE", 120, "Giảm khác", "dep_other_dec"),
                (895, "DEPRECIATION_ENDING", 126, "Số dư cuối năm", "dep_close"),
                (5965, "CARRYING_OPENING", 133, "Số dư đầu năm", "carry_open"),
                (5966, "CARRYING_ENDING", 139, "Số dư cuối năm", "carry_close"),
            ],
            ("cost_inc_total", "cost_dec_total"),
            ("dep_inc_total", "dep_dec_total"),
        )
    )

    ctg = _values(
        base,
        {
            "cost_open": (3, "17.253.570", 26),
            "cost_purchase": (4, "1.138.737", 31),
            "cost_xdcb": (5, "387.792", 39),
            "cost_disposal": (6, "(268.711)", 47),
            "cost_other": (7, "(479)", 53),
            "cost_close": (8, "18.510.909", 59),
            "dep_open": (9, "(11.104.354)", 65),
            "dep_charge": (10, "(938.137)", 72),
            "dep_disposal": (11, "263.932", 81),
            "dep_other": (12, "(3.333)", 87),
            "dep_close": (13, "(11.781.892)", 93),
            "carry_open": (14, "6.149.216", 100),
            "carry_close": (15, "6.729.017", 106),
        },
    )
    docs.append(
        _rotated_document(
            base,
            "CTG",
            48,
            96,
            (108, 100, 107),
            ctg,
            [
                (870, "COST_OPENING", 97, "Tại ngày 1 tháng 1 năm 2025", "cost_open"),
                (871, "COST_PURCHASE", 106, "Mua trong năm", "cost_purchase"),
                (872, "COST_XDCB_COMPLETED", 92, "Đầu tư xây dựng cơ bản hoàn thành", "cost_xdcb"),
                (880, "COST_DISPOSAL", 101, "Thanh lý, nhượng bán", "cost_disposal"),
                (5993, "COST_OTHER_NET", 104, "Tăng/(giảm) khác", "cost_other"),
                (882, "COST_ENDING", 93, "Tại ngày 31 tháng 12 năm 2025", "cost_close"),
                (884, "DEPRECIATION_OPENING", 98, "Tại ngày 1 tháng 1 năm 2025", "dep_open"),
                (885, "DEPRECIATION_CHARGE", 103, "Khấu hao trong năm", "dep_charge"),
                (892, "DEPRECIATION_DISPOSAL", 102, "Thanh lý, nhượng bán", "dep_disposal"),
                (5996, "DEPRECIATION_OTHER_NET", 105, "Tăng/(giảm) khác", "dep_other"),
                (895, "DEPRECIATION_ENDING", 94, "Tại ngày 31 tháng 12 năm 2025", "dep_close"),
                (5965, "CARRYING_OPENING", 99, "Tại ngày 1 tháng 1 năm 2025", "carry_open"),
                (5966, "CARRYING_ENDING", 95, "Tại ngày 31 tháng 12 năm 2025", "carry_close"),
            ],
            ("cost_purchase", "cost_xdcb", "cost_disposal", "cost_other"),
            ("dep_charge", "dep_disposal", "dep_other"),
            depreciation_is_negative=True,
        )
    )

    bid = _values(
        base,
        {
            "cost_open": (2, "16.745.119", 140),
            "cost_purchase": (3, "992.032", 147),
            "cost_xdcb": (4, "343.380", 154),
            "cost_disposal": (5, "(323.514)", 161),
            "cost_other": (6, "101.265", 168),
            "cost_close": (7, "17.858.282", 175),
            "dep_open": (8, "9.900.882", 183),
            "dep_charge": (9, "964.385", 190),
            "dep_disposal": (10, "(314.371)", 197),
            "dep_other": (11, "(233.423)", 204),
            "dep_close": (12, "10.317.473", 211),
            "carry_open": (14, "6.844.237", 219),
            "carry_close": (15, "7.540.809", 226),
        },
    )
    docs.append(
        _rotated_document(
            base,
            "BID",
            47,
            103,
            (102, 105, 99),
            bid,
            [
                (870, "COST_OPENING", 114, "Số dư đầu năm", "cost_open"),
                (871, "COST_PURCHASE", 118, "Mua trong năm", "cost_purchase"),
                (872, "COST_XDCB_COMPLETED", 104, "Đầu tư XDCB hoàn thành", "cost_xdcb"),
                (880, "COST_DISPOSAL", 106, "Thanh lý, nhượng bán", "cost_disposal"),
                (5993, "COST_OTHER_NET", 111, "Tăng/(Giảm) khác", "cost_other"),
                (882, "COST_ENDING", 115, "Số dư cuối năm", "cost_close"),
                (884, "DEPRECIATION_OPENING", 100, "Số dư đầu năm", "dep_open"),
                (885, "DEPRECIATION_CHARGE", 108, "Khấu hao trong năm", "dep_charge"),
                (892, "DEPRECIATION_DISPOSAL", 107, "Thanh lý, nhượng bán", "dep_disposal"),
                (5996, "DEPRECIATION_OTHER_NET", 112, "Tăng/(Giảm) khác", "dep_other"),
                (895, "DEPRECIATION_ENDING", 116, "Số dư cuối năm", "dep_close"),
                (5965, "CARRYING_OPENING", 101, "Số dư đầu năm", "carry_open"),
                (5966, "CARRYING_ENDING", 117, "Số dư cuối năm", "carry_close"),
            ],
            ("cost_purchase", "cost_xdcb", "cost_disposal", "cost_other"),
            ("dep_charge", "dep_disposal", "dep_other"),
        )
    )

    vib = _values(
        base,
        {
            "cost_open": (2, "1.252.507", 256),
            "cost_purchase": (12, "164.021", 263),
            "cost_disposal": (3, "(155.734)", 270),
            "cost_close": (4, "1.260.794", 277),
            "dep_open": (13, "759.301", 285),
            "dep_charge": (5, "98.401", 292),
            "dep_disposal": (6, "(145.823)", 299),
            "dep_close": (7, "711.879", 306),
            "carry_open": (8, "493.206", 314),
            "carry_close": (9, "548.915", 321),
        },
    )
    docs.append(
        _rotated_document(
            base,
            "VIB",
            42,
            87,
            (100, 97, 99),
            vib,
            [
                (870, "COST_OPENING", 94, "Tại ngày 1/1/2025", "cost_open"),
                (871, "COST_PURCHASE", 98, "Mua trong năm", "cost_purchase"),
                (880, "COST_DISPOSAL", 92, "Thanh lý trong năm", "cost_disposal"),
                (882, "COST_ENDING", 88, "Tại ngày 31/12/2025", "cost_close"),
                (884, "DEPRECIATION_OPENING", 95, "Tại ngày 1/1/2025", "dep_open"),
                (885, "DEPRECIATION_CHARGE", 89, "Khấu hao trong năm", "dep_charge"),
                (892, "DEPRECIATION_DISPOSAL", 93, "Thanh lý trong năm", "dep_disposal"),
                (895, "DEPRECIATION_ENDING", 90, "Tại ngày 31/12/2025", "dep_close"),
                (5965, "CARRYING_OPENING", 96, "Tại ngày 1/1/2025", "carry_open"),
                (5966, "CARRYING_ENDING", 91, "Tại ngày 31/12/2025", "carry_close"),
            ],
            ("cost_purchase", "cost_disposal"),
            ("dep_charge", "dep_disposal"),
            branch_labels=("Nguyên giá", "Khấu hao lũy kế", "Giá trị còn lại"),
        )
    )
    return docs


def _simple_document(
    base: ModuleType,
    code: str,
    page: int,
    owner: int,
    branches: tuple[int, int, int],
    values: Mapping[str, dict[str, Any]],
    mappings: Sequence[tuple[int, str, int, str, str]],
    cost_movements: Sequence[str],
    dep_movements: Sequence[str],
    *,
    branch_labels: tuple[str, str, str] = (
        "Nguyên giá",
        "Giá trị hao mòn lũy kế",
        "Giá trị còn lại",
    ),
) -> dict[str, Any]:
    return base._present_doc(
        code,
        page,
        owner,
        "TÀI SẢN CỐ ĐỊNH HỮU HÌNH",
        "2025-12-31",
        [
            ("COST", branches[0], branch_labels[0]),
            ("ACCUMULATED_DEPRECIATION", branches[1], branch_labels[1]),
            ("CARRYING_VALUE", branches[2], branch_labels[2]),
        ],
        [
            _mapping(
                base,
                schema_id,
                role,
                label_index,
                label,
                values[value_key],
                "COST_CHILD"
                if role.startswith("COST_")
                else "DEPRECIATION_CHILD"
                if role.startswith("DEPRECIATION_")
                else "CARRYING_CHILD",
            )
            for schema_id, role, label_index, label, value_key in mappings
        ],
        _four_equations(base, values, cost_movements, dep_movements),
    )


def _rotated_document(
    base: ModuleType,
    code: str,
    page: int,
    owner: int,
    branches: tuple[int, int, int],
    values: Mapping[str, dict[str, Any]],
    mappings: Sequence[tuple[int, str, int, str, str]],
    cost_movements: Sequence[str],
    dep_movements: Sequence[str],
    *,
    depreciation_is_negative: bool = False,
    branch_labels: tuple[str, str, str] = (
        "Nguyên giá",
        "Giá trị hao mòn lũy kế",
        "Giá trị còn lại",
    ),
) -> dict[str, Any]:
    return base._present_doc(
        code,
        page,
        owner,
        "TÀI SẢN CỐ ĐỊNH HỮU HÌNH",
        "2025-12-31",
        [
            ("COST", branches[0], branch_labels[0]),
            ("ACCUMULATED_DEPRECIATION", branches[1], branch_labels[1]),
            ("CARRYING_VALUE", branches[2], branch_labels[2]),
        ],
        [
            _mapping(
                base,
                schema_id,
                role,
                label_index,
                label,
                values[value_key],
                "COST_CHILD"
                if role.startswith("COST_")
                else "DEPRECIATION_CHILD"
                if role.startswith("DEPRECIATION_")
                else "CARRYING_CHILD",
            )
            for schema_id, role, label_index, label, value_key in mappings
        ],
        _four_equations(
            base,
            values,
            cost_movements,
            dep_movements,
            depreciation_is_negative=depreciation_is_negative,
        ),
    )


def _annual_metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mappings = [mapping for trial in trials for mapping in trial["mappings"]]
    values = [mapping["value"] for mapping in mappings]
    return {
        "accounting_equation_count": sum(len(trial["equations"]) for trial in trials),
        "document_count": len(trials),
        "mapping_verified_count": len(mappings),
        "rotated_original_source_numeric_disagreement_count": sum(
            value["source_numeric_challenger_status"]
            == "ORIGINAL_ROTATED_SOURCE_OCR_DISAGREED_RESCUED_BY_ROTATED_PPOCRV6"
            for value in values
        ),
        "rotated_ppocrv6_verified_value_count": sum(
            value["rotated_ppocrv6_challenger_status"] == "ROTATED_PPOCRV6_MATCHED_VISIBLE_PIXEL"
            for value in values
        ),
        "unresolved_document_count": 0,
        "verified_present_document_count": sum(bool(trial["mappings"]) for trial in trials),
    }


def _enriched_rescue(
    base: ModuleType, panel: ModuleType, semantic_index: Any, projection: Mapping[str, Any]
) -> dict[str, Any]:
    rescue = base.scanner._profile_rescue(semantic_index, base.scanner.DEFAULT_RESCUE_ROOT)
    if (
        type(rescue) is not dict
        or rescue.get("metrics", {}).get("line_count") != EXPECTED_RESCUE_LINE_COUNT
    ):
        raise _error("annual rotated VietOCR semantic rescue drifted")
    raw_manifest, _ = panel._json(
        panel.ROTATED_RESCUE_MANIFEST_PATH, panel.EXPECTED_ROTATED_RESCUE_MANIFEST_SHA256
    )
    raw_by_key = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in raw_manifest["samples"]
    }
    samples = []
    for sample in rescue["samples"]:
        key = (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"])
        raw = raw_by_key.get(key)
        if raw is None or raw["source_crop_ref"]["sha256"] != sample["source_crop_sha256"]:
            raise _error("annual semantic rescue and rotated crop axes drifted")
        samples.append(
            {
                **canonical_clone_v1(sample),
                "rotated_crop_ref": canonical_clone_v1(raw["rotated_crop_ref"]),
            }
        )
    if (
        projection["input_refs"]["rotated_rescue_crop_manifest"]["sha256"]
        != panel.EXPECTED_ROTATED_RESCUE_MANIFEST_SHA256
    ):
        raise _error("numeric panel does not bind the semantic rescue manifest")
    return {**canonical_clone_v1(rescue), "samples": samples}


def _numeric_panel(projection: Mapping[str, Any]) -> dict[str, Any]:
    texts: list[str] = []
    scores: list[float] = []
    page_refs = []
    for page in projection["pages"]:
        page_refs.append(
            {
                "document_ordinal": page["document_ordinal"],
                "ocr_result_ref": canonical_clone_v1(page["ocr_result_ref"]),
                "run_manifest_ref": canonical_clone_v1(page["run_manifest_ref"]),
            }
        )
        texts.extend(page["rec_texts"])
        scores.extend(page["rec_scores"])
    if len(texts) != 333 or len(scores) != 333:
        raise _error("annual rotated PP-OCRv6 flattened axis drifted")
    return {
        "input_refs": {
            "panel_id": projection["panel_id"],
            "projection_id": projection["projection_id"],
            "pages": page_refs,
        },
        "rec_scores": scores,
        "rec_texts": texts,
    }


def _validate_expected_ids(result: dict[str, Any]) -> dict[str, Any]:
    for trial, code in zip(result["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        ids = {mapping["report_norm_id"] for mapping in trial["mappings"]}
        if ids != _EXPECTED_IDS[code]:
            raise _error(f"annual tangible-asset mapping set drifted for {code}")
    return result


def _base() -> ModuleType:
    base = _load_module(
        "annual_2025_tangible_fixed_assets_base_v1",
        "scripts/experiments/build_tangible_fixed_assets_8bank_codex_verified_mapping_v1.py",
    )
    panel = _load_module(
        "annual_2025_tangible_fixed_assets_numeric_panel_v1",
        "scripts/experiments/build_annual_2025_tangible_fixed_assets_rotated_ppocrv6_panel_v1.py",
    )
    cache: dict[str, Any] = {}

    def projection() -> dict[str, Any]:
        if "projection" not in cache:
            cache["projection"] = (
                panel.read_verified_annual_2025_tangible_rotated_ppocrv6_panel_v1()
            )
        return cache["projection"]

    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.CLAIM_BOUNDARY = _CLAIM_BOUNDARY
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
    base._REVIEW_RUN_ID = "E-0123"
    base._SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": "VERIFIED_ANNUAL_2025_CURRENT_AND_2024_OPENING_PERIODS"
    }
    base._REQUIRE_ROTATED_VIETOCR_NUMERIC_MATCH = False
    base._REVIEW_CHECKS = list(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._SCHEMA_DISPLAY_ORDER_SNAPSHOT = dict(_SCHEMA_DISPLAY_ORDER_SNAPSHOT)
    base._schema_authority_for_output = lambda _live: canonical_clone_v1(_SCHEMA_AUTHORITY)
    base._metrics = _annual_metrics
    base._review_documents = lambda: _review_documents(base)
    base.scanner.MATCHER_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
    base._load_live_rescue = lambda semantic: _enriched_rescue(base, panel, semantic, projection())
    base._rotated_ppocr_evidence = lambda: _numeric_panel(projection())
    return base


def build_annual_2025_tangible_fixed_assets_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_tangible_fixed_assets_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    try:
        return _validate_expected_ids(
            _base().build_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1()
        )
    except Annual2025TangibleFixedAssets8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _validate_expected_ids(
            _base().validate_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1(value)
        )
    except Annual2025TangibleFixedAssets8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_tangible_fixed_assets_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        result = build_live_annual_2025_tangible_fixed_assets_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    if args.verify:
        value, _ = _base()._stable_json(RESULT_PATH)
        result = validate_annual_2025_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
            value
        )
        print(result["result_id"])
        return 0
    parser.error("choose exactly one action")


if __name__ == "__main__":
    raise SystemExit(main())
