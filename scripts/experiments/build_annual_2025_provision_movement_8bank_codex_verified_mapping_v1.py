"""Verify annual-2025 customer-loan provision movements for eight banks.

This is an annual-data profile of the existing generic provision-movement
matcher and E-0057 verifier.  The matcher still scans each complete PDF and
uses no bank, note or page routing.  The profile selects the current annual
roll-forward after the unique match, retains visible dashes as typed zero,
checks each lane equation, and binds only the general, specific and separately
meaningful margin-provision lanes to the live TM schema.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "Annual2025ProvisionMovement8BankError",
    "build_annual_2025_provision_movement_pixel_review_blueprint_v1",
    "build_live_annual_2025_provision_movement_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_provision_movement_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_PROVISION_MOVEMENT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT_VERSION = "ANNUAL_2025_PROVISION_MOVEMENT_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_PROVISION_MOVEMENT_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025pm8bcv1:result:"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0119-annual-2025-provision-movement-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0119-annual-2025-provision-movement-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "pmfdsv1:scan:89af751681a703ee5f93c7fb1381fbb3bda6c97a75a3e17e997173f27e9b862c"
EXPECTED_REVIEW_SHA256 = "9205f96b91708bd21e048e7175913ed1a069afa8dd350ee502b090bad44f8b26"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_EXPECTED_PAGES = {
    "ACB": 51,
    "MBB": 53,
    "VPB": 48,
    "HDB": 38,
    "VCB": 41,
    "CTG": 44,
    "BID": 43,
    "VIB": 39,
}
_EXPECTED_RENDER_SHA256 = {
    "ACB": "6a54bc510401937d7f563cad60bcf5d8e8da223c9e5a4e5e662bd2e6889202b1",
    "MBB": "af8418d13d7c4150e8af6ed49a2997474005d5e6a11aef92153a506d951b007c",
    "VPB": "1f58ce6a77c53d594b450e578c882a9790c957dd3dc49fdab4e1079a05580c22",
    "HDB": "8d218fd7497479555cdd0e485834f15373fa1c9a369d3418948fa19a741ec6eb",
    "VCB": "dc38ea562ffc6380f6b0e9b200aedf071802e6bc1b1385a4e4647c84d359d05b",
    "CTG": "06bac9233047b7679b7d40e2a11d40ebea3c3f69fc139a3da2d6419c1c0e5223",
    "BID": "4c1165cfdc08e96b6952784ea6d5c2ef5432751ff8d4a632f77e78d17f988311",
    "VIB": "dd74c6f0249eded4bc6b1509bb2a03847d2019c1ec369e5706ce0119b568f1ab",
}
_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "GENERIC_CUSTOMER_LOAN_PROVISION_MOVEMENT_WHOLE_PDF_UNIQUENESS_VISIBLE_"
    "PIXEL_PPOCRV6_NUMERIC_CHALLENGER_EXACT_ROLLFORWARD_AND_LIVE_TM_SCHEMA_"
    "ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_REVIEW_CLAIM_BOUNDARY = (
    "INDEPENDENT_VISIBLE_PAGE_REVIEW_OF_THE_EIGHT_UNIQUE_ANNUAL_2025_CUSTOMER_"
    "LOAN_PROVISION_MOVEMENT_TABLES_CURRENT_ROLLFORWARD_ONLY"
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_or_absent_cell_interpreted_as_zero": False,
    "comparison_rollforward_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_PPOCRV6_NUMERIC_CHALLENGER",
    "only_visible_dash_interpreted_as_zero": True,
    "source_only_combined_or_auxiliary_lanes_mapped_additively": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_rollforward_used_as_mapping_authority": False,
    "dash_zero_policy_applied_only_to_visible_dash": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_and_ppocrv6_challenger_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_checked": True,
    "mapping_authority_is_bounded_to_reviewed_current_annual_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_only_combined_or_auxiliary_lanes_exported_additively": False,
    "text_similarity_alone_used_for_mapping": False,
}


class Annual2025ProvisionMovement8BankError(ValueError):
    """The annual graph, review, numeric challenger, equation or schema drifted."""


def _error(message: str) -> Annual2025ProvisionMovement8BankError:
    return Annual2025ProvisionMovement8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _base() -> ModuleType:
    base = _load_module(
        "annual_2025_provision_movement_base_v1",
        "scripts/experiments/build_provision_movement_8bank_codex_verified_mapping_v1.py",
    )
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT_VERSION
    base.CLAIM_BOUNDARY = _CLAIM_BOUNDARY
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.REVIEW_SHA256 = EXPECTED_REVIEW_SHA256
    base._SELECTED_PERIOD_PREFIX = "2025-"
    base._FIXED_SOURCE_PERIOD_STATUS = "VERIFIED_SOURCE_PERIOD_ANNUAL_2025"
    base._SUCCESS_SOURCE_PERIOD_STATUS = "VERIFIED_SOURCE_PERIOD_ANNUAL_2025"
    base._CAVEAT_SOURCE_PERIOD_STATUS = None
    base._SUCCESS_TRIAL_STATUS = "VERIFIED_BY_CODEX"
    base._PERIOD_METRIC_KEY = "annual_source_period_document_count"
    base._PERIOD_METRIC_STATUS = "VERIFIED_SOURCE_PERIOD_ANNUAL_2025"
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    return base


def _scanner() -> ModuleType:
    return _load_module(
        "annual_2025_provision_movement_scan_v1",
        "scripts/experiments/scan_provision_movement_full_document_vietocr_v1.py",
    )


def _pixel(bbox: Sequence[int], digest: str) -> dict[str, Any]:
    return {"bbox_raw_pixels": list(bbox), "rgb_sha256": digest}


_DASH = {
    ("ACB", "GENERAL", "USE"): _pixel(
        [1117, 2001, 1132, 2011],
        "d132b4ac1b4e50d01ff949a6feb67a92e01c2cc6351a437859cfd1e2fbfe66a5",
    ),
    ("ACB", "MARGIN_ADVANCE", "PROVISION"): _pixel(
        [1352, 1968, 1367, 1978],
        "8b7e0b172230c9a56dd6c610f655ce247f119dbcb3a8015733d0c6ce0bfc32b3",
    ),
    ("ACB", "MARGIN_ADVANCE", "USE"): _pixel(
        [1352, 2001, 1367, 2012],
        "6f3e72742ee73ae32b481d0436a1b3047a94536c6c7cf385ec74753ff282c367",
    ),
    ("MBB", "GENERAL", "USE"): _pixel(
        [1042, 926, 1058, 937],
        "660b722bfe7625ea357dbe8da355bad5a0ad83dde2021704b100c2ee5b3fbba9",
    ),
    ("VPB", "MARGIN_ADVANCE", "USE"): _pixel(
        [1263, 1281, 1294, 1313],
        "0d9389b3b0416209763f0f3185a9b132742a8bd9984676c1d5db16008087aa18",
    ),
    ("HDB", "GENERAL", "USE"): _pixel(
        [999, 652, 1013, 663],
        "9ced4b39d3a586f5d421f711129e4184079202cbd353fade93f68ee716551d55",
    ),
    ("CTG", "GENERAL", "USE"): _pixel(
        [1284, 1777, 1300, 1787],
        "b55521bbdb832f8f38342f23a655c1aec2bf794a9e2d03f6d89a07e2ee1535fb",
    ),
    ("BID", "GENERAL", "USE"): _pixel(
        [1266, 907, 1281, 918],
        "2fe44946ba155b930f18adbcb41c44435e59f72d018dec62416fae05cc15d745",
    ),
    ("VIB", "GENERAL", "USE"): _pixel(
        [1103, 1735, 1118, 1746],
        "8962f20f08bfea0ff83b8823b438d8286f64370e9d1ce25bef7ca29aacc33eb2",
    ),
}


def _row(
    base: ModuleType,
    bank: str,
    lane: str,
    role: str,
    label: str,
    label_lines: Sequence[int],
    value_line: int | None,
    value: str,
) -> dict[str, Any]:
    return base._row(
        role,
        label,
        label_lines,
        value_line,
        value,
        _DASH.get((bank, lane, role)),
    )


def _lane(
    base: ModuleType,
    bank: str,
    lane: str,
    rows: Sequence[tuple[str, str, Sequence[int], int | None, str]],
) -> dict[str, Any]:
    return base._series(
        "2025-01-01_TO_2025-12-31",
        lane,
        _EXPECTED_PAGES[bank],
        [_row(base, bank, lane, *row) for row in rows],
    )


def _review_series(base: ModuleType) -> dict[str, list[dict[str, Any]]]:
    return {
        "ACB": [
            _lane(
                base,
                "ACB",
                "SPECIFIC",
                [
                    ("OPENING", "Tại ngày 31 tháng 12 năm 2024", [97], 98, "2.383.004"),
                    ("PROVISION", "Trích lập trong năm (Thuyết minh 32)", [102], 103, "2.592.268"),
                    ("USE", "Sử dụng trong năm", [106], 107, "(2.450.269)"),
                    ("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [109], 110, "2.525.003"),
                ],
            ),
            _lane(
                base,
                "ACB",
                "GENERAL",
                [
                    ("OPENING", "Tại ngày 31 tháng 12 năm 2024", [97], 99, "4.239.076"),
                    ("PROVISION", "Trích lập trong năm (Thuyết minh 32)", [102], 104, "743.174"),
                    ("USE", "Sử dụng trong năm", [106], None, "-"),
                    ("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [109], 111, "4.982.250"),
                ],
            ),
            _lane(
                base,
                "ACB",
                "MARGIN_ADVANCE",
                [
                    ("OPENING", "Tại ngày 31 tháng 12 năm 2024", [97], 100, "117.476"),
                    ("PROVISION", "Trích lập trong năm (Thuyết minh 32)", [102], None, "-"),
                    ("USE", "Sử dụng trong năm", [106], None, "-"),
                    ("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [109], 112, "117.476"),
                ],
            ),
        ],
        "MBB": [
            _lane(
                base,
                "MBB",
                "GENERAL",
                [
                    ("OPENING", "Số dư tại ngày 1 tháng 1 năm 2025", [33], 34, "5.795.573"),
                    ("PROVISION", "Trích lập trong năm (Thuyết minh 35)", [37], 38, "2.301.538"),
                    ("USE", "Sử dụng dự phòng trong năm", [41], None, "-"),
                    ("OTHER", "Điều chỉnh theo Kiểm toán Nhà nước", [44], 45, "(1.444)"),
                    ("FX", "Chênh lệch tỷ giá", [48], 49, "2.478"),
                    ("CLOSING", "Số dư tại ngày 31 tháng 12 năm 2025", [52], 53, "8.098.145"),
                ],
            ),
            _lane(
                base,
                "MBB",
                "SPECIFIC",
                [
                    ("OPENING", "Số dư tại ngày 1 tháng 1 năm 2025", [33], 35, "5.814.288"),
                    ("PROVISION", "Trích lập trong năm (Thuyết minh 35)", [37], 39, "11.388.818"),
                    ("USE", "Sử dụng dự phòng trong năm", [41], 42, "(12.185.137)"),
                    ("OTHER", "Điều chỉnh theo Kiểm toán Nhà nước", [44], 46, "33.942"),
                    ("FX", "Chênh lệch tỷ giá", [48], 50, "537"),
                    ("CLOSING", "Số dư tại ngày 31 tháng 12 năm 2025", [52], 54, "5.052.448"),
                ],
            ),
        ],
        "VPB": [
            _lane(
                base,
                "VPB",
                "GENERAL",
                [
                    ("OPENING", "Số dư đầu năm", [44], 45, "5.079.275"),
                    (
                        "PROVISION",
                        "Trích lập dự phòng rủi ro trong năm (Thuyết minh số 36)",
                        [49],
                        52,
                        "1.765.033",
                    ),
                    (
                        "USE",
                        "Sử dụng dự phòng xử lý rủi ro tín dụng và bán nợ trong năm",
                        [56],
                        58,
                        "(89.476)",
                    ),
                    ("CLOSING", "Số dư cuối năm", [62], 63, "6.754.832"),
                ],
            ),
            _lane(
                base,
                "VPB",
                "SPECIFIC",
                [
                    ("OPENING", "Số dư đầu năm", [44], 46, "11.203.918"),
                    (
                        "PROVISION",
                        "Trích lập dự phòng rủi ro trong năm (Thuyết minh số 36)",
                        [49],
                        53,
                        "23.551.496",
                    ),
                    (
                        "USE",
                        "Sử dụng dự phòng xử lý rủi ro tín dụng và bán nợ trong năm",
                        [56],
                        59,
                        "(24.242.889)",
                    ),
                    ("CLOSING", "Số dư cuối năm", [62], 64, "10.512.525"),
                ],
            ),
            _lane(
                base,
                "VPB",
                "MARGIN_ADVANCE",
                [
                    ("OPENING", "Số dư đầu năm", [44], 47, "83.762"),
                    (
                        "PROVISION",
                        "Trích lập dự phòng rủi ro trong năm (Thuyết minh số 36)",
                        [49],
                        54,
                        "77.852",
                    ),
                    (
                        "USE",
                        "Sử dụng dự phòng xử lý rủi ro tín dụng và bán nợ trong năm",
                        [56],
                        60,
                        "-",
                    ),
                    ("CLOSING", "Số dư cuối năm", [62], 65, "161.614"),
                ],
            ),
        ],
        "HDB": [
            _lane(
                base,
                "HDB",
                "GENERAL",
                [
                    ("OPENING", "Tại ngày 01 tháng 01 năm 2025", [23], 24, "3.216.873"),
                    ("PROVISION", "Trích lập/(Hoàn nhập) dự phòng trong năm", [28], 29, "852.382"),
                    ("USE", "Sử dụng dự phòng rủi ro tín dụng trong năm", [33], None, "-"),
                    ("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [36], 37, "4.069.255"),
                ],
            ),
            _lane(
                base,
                "HDB",
                "SPECIFIC",
                [
                    ("OPENING", "Tại ngày 01 tháng 01 năm 2025", [23], 25, "2.577.890"),
                    (
                        "PROVISION",
                        "Trích lập/(Hoàn nhập) dự phòng trong năm",
                        [28],
                        30,
                        "8.806.336",
                    ),
                    ("USE", "Sử dụng dự phòng rủi ro tín dụng trong năm", [33], 34, "(8.154.036)"),
                    ("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [36], 38, "3.230.190"),
                ],
            ),
        ],
        "VCB": [
            _lane(
                base,
                "VCB",
                "GENERAL",
                [
                    ("OPENING", "Số dư đầu năm", [30], 31, "10.687.999"),
                    (
                        "PROVISION",
                        "Trích lập dự phòng trong năm (Thuyết minh 32)",
                        [33],
                        34,
                        "1.733.057",
                    ),
                    ("FX", "Chênh lệch tỷ giá hối đoái", [36], 37, "1.628"),
                    ("CLOSING", "Số dư cuối năm", [39], 40, "12.422.684"),
                ],
            ),
            _lane(
                base,
                "VCB",
                "SPECIFIC",
                [
                    ("OPENING", "Số dư đầu năm", [51], 52, "20.495.176"),
                    (
                        "PROVISION",
                        "(Hoàn nhập)/trích lập dự phòng trong năm (Thuyết minh 32)",
                        [54],
                        56,
                        "(656.394)",
                    ),
                    (
                        "USE",
                        "Xử lý các khoản cho vay khó thu hồi bằng nguồn dự phòng",
                        [58],
                        59,
                        "(7.287.783)",
                    ),
                    ("FX", "Chênh lệch tỷ giá hối đoái", [61], 62, "1.996"),
                    ("CLOSING", "Số dư cuối năm", [64], 65, "12.552.995"),
                ],
            ),
        ],
        "CTG": [
            _lane(
                base,
                "CTG",
                "SPECIFIC",
                [
                    ("OPENING", "Số dư tại ngày 31 tháng 12 năm 2024", [86], 87, "23.881.694"),
                    ("PROVISION", "Trích lập trong năm", [90], 91, "15.212.526"),
                    ("USE", "Sử dụng trong năm", [94], 95, "(19.101.106)"),
                    ("CLOSING", "Số dư tại ngày 31 tháng 12 năm 2025", [97], 98, "19.993.114"),
                ],
            ),
            _lane(
                base,
                "CTG",
                "GENERAL",
                [
                    ("OPENING", "Số dư tại ngày 31 tháng 12 năm 2024", [86], 88, "12.782.431"),
                    ("PROVISION", "Trích lập trong năm", [90], 92, "2.034.820"),
                    ("USE", "Sử dụng trong năm", [94], None, "-"),
                    ("CLOSING", "Số dư tại ngày 31 tháng 12 năm 2025", [97], 99, "14.817.251"),
                ],
            ),
        ],
        "BID": [
            _lane(
                base,
                "BID",
                "SPECIFIC",
                [
                    ("OPENING", "Số dư đầu năm (Trình bày lại)", [29], 30, "22.712.857"),
                    ("PROVISION", "Số trích lập dự phòng rủi ro trong năm", [33], 34, "20.711.878"),
                    (
                        "USE",
                        "Số dự phòng đã sử dụng để xử lý rủi ro trong năm",
                        [37],
                        38,
                        "(26.117.579)",
                    ),
                    ("OTHER", "Tăng khác trong năm", [41], 42, "60.494"),
                    ("CLOSING", "Số dư cuối năm", [45], 46, "17.367.650"),
                ],
            ),
            _lane(
                base,
                "BID",
                "GENERAL",
                [
                    ("OPENING", "Số dư đầu năm (Trình bày lại)", [29], 31, "15.257.624"),
                    ("PROVISION", "Số trích lập dự phòng rủi ro trong năm", [33], 35, "2.305.906"),
                    ("USE", "Số dự phòng đã sử dụng để xử lý rủi ro trong năm", [37], None, "-"),
                    ("OTHER", "Tăng khác trong năm", [41], 43, "14.373"),
                    ("CLOSING", "Số dư cuối năm", [45], 47, "17.577.903"),
                ],
            ),
        ],
        "VIB": [
            _lane(
                base,
                "VIB",
                "GENERAL",
                [
                    ("OPENING", "Số dư đầu năm", [88], 89, "2.382.092"),
                    ("PROVISION", "Trích lập dự phòng trong năm", [92], 93, "434.989"),
                    ("USE", "Sử dụng dự phòng rủi ro tín dụng trong năm", [98], None, "-"),
                    ("CLOSING", "Số dư cuối năm", [102], 99, "2.817.081"),
                ],
            ),
            _lane(
                base,
                "VIB",
                "SPECIFIC",
                [
                    ("OPENING", "Số dư đầu năm", [88], 90, "3.311.542"),
                    ("PROVISION", "Trích lập dự phòng trong năm", [92], 94, "3.032.307"),
                    ("USE", "Sử dụng dự phòng rủi ro tín dụng trong năm", [98], 96, "(4.302.109)"),
                    ("CLOSING", "Số dư cuối năm", [102], 100, "2.041.740"),
                ],
            ),
        ],
    }


def _source_only_lanes(bank: str) -> list[str]:
    return {
        "ACB": ["OVERALL_COMBINED"],
        "MBB": ["OVERALL_COMBINED"],
        "VPB": ["OVERALL_COMBINED"],
        "HDB": ["DEFERRED_LC_PROVISION", "OVERALL_COMBINED"],
        "VCB": [],
        "CTG": ["OVERALL_COMBINED"],
        "BID": ["OVERALL_COMBINED"],
        "VIB": ["OVERALL_COMBINED"],
    }[bank]


def build_annual_2025_provision_movement_pixel_review_blueprint_v1(
    base: ModuleType | None = None,
) -> dict[str, Any]:
    """Return the fixed independently inspected annual current-period ledger."""

    configured = _base() if base is None else base
    series_by_bank = _review_series(configured)
    documents: list[dict[str, Any]] = []
    for bank in EXPECTED_DOCUMENT_ORDER:
        document = configured._document(
            bank,
            [_EXPECTED_PAGES[bank]],
            series_by_bank[bank],
            _source_only_lanes(bank),
        )
        document["comparison_periods_excluded_from_mapping"] = ["2024-01-01_TO_2024-12-31"]
        documents.append(document)
    material = {
        "claim_boundary": _REVIEW_CLAIM_BOUNDARY,
        "documents": documents,
        "format_version": REVIEW_FORMAT_VERSION,
        "review_checks": canonical_clone_v1(configured._REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_PDF_PIXEL_REVIEW",
            "review_run_id": "annual-2025-provision-movement-eight-bank-pixel-review-2026-08-17",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "ANNUAL_2025_PROVISION_MOVEMENT_CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {
        **material,
        "review_id": "e0119:pixel-review:" + configured.canonical_json_sha256_v1(material),
    }


def _trial(scan: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [item for item in scan["trials"] if item.get("document_provenance") == bank]
    if len(matches) != 1:
        raise _error(f"annual provision scan lacks exactly one {bank} trial")
    return matches[0]


def _verify_scan_and_renders(
    crop_manifest: Mapping[str, Any], structure_scan: Mapping[str, Any]
) -> None:
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual provision structure scan identity drifted")
    for bank in EXPECTED_DOCUMENT_ORDER:
        matcher = _trial(structure_scan, bank)["matcher_result"]
        if (
            matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or len(matcher.get("graphs", [])) != 1
            or matcher["graphs"][0].get("page_sequences") != [_EXPECTED_PAGES[bank]]
        ):
            raise _error(f"{bank} annual provision region/page is not uniquely bound")
        documents = [item for item in crop_manifest["documents"] if item.get("bank_code") == bank]
        if len(documents) != 1:
            raise _error(f"annual crop manifest lacks exactly one {bank} document")
        pages = [
            item
            for item in documents[0]["pages"]
            if item.get("physical_page") == _EXPECTED_PAGES[bank]
        ]
        if (
            len(pages) != 1
            or pages[0].get("render_binding", {}).get("sha256") != _EXPECTED_RENDER_SHA256[bank]
        ):
            raise _error(f"{bank} annual provision render identity drifted")


def _live_core(*, include_review: bool) -> tuple[Any, ...]:
    base = _base()
    semantic_index, _ = base._fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._fixed_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = _scanner().build_provision_movement_full_document_scan_v1(
        semantic_index,
        enable_extended_reporting_period_variants=True,
    )
    _verify_scan_and_renders(crop_manifest, structure_scan)
    expected_review = build_annual_2025_provision_movement_pixel_review_blueprint_v1(base)
    base._review_blueprint = lambda: canonical_clone_v1(expected_review)
    if not include_review:
        return base, semantic_index, crop_manifest, structure_scan, expected_review
    review, review_bytes = base._fixed_json(REVIEW_PATH, EXPECTED_REVIEW_SHA256)
    if hashlib.sha256(review_bytes).hexdigest() != EXPECTED_REVIEW_SHA256 or not same_typed_json_v1(
        review, expected_review
    ):
        raise _error("sealed annual provision pixel review does not rebuild exactly")
    return base, semantic_index, crop_manifest, structure_scan, review


def build_live_annual_2025_provision_movement_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed authorities and construct the bounded annual result."""

    base, semantic_index, crop_manifest, structure_scan, review = _live_core(include_review=True)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = base.build_provision_movement_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=EXPECTED_CROP_MANIFEST_SHA256,
        review_sha256=EXPECTED_REVIEW_SHA256,
    )
    if result["metrics"] != {
        "accounting_equation_verified_count": 18,
        "annual_source_period_document_count": 8,
        "current_period_lane_parent_verified_count": 18,
        "current_period_role_mapping_verified_count": 79,
        "document_count": 8,
        "document_unique_region_count": 8,
        "visible_dash_verified_as_zero_count": 9,
    }:
        raise _error("annual provision verified metrics drifted")
    return result


def validate_annual_2025_provision_movement_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the result from all live fixed authorities."""

    base, _, _, _, expected_review = _live_core(include_review=False)
    base._review_blueprint = lambda: canonical_clone_v1(expected_review)
    persisted = base._validate_result(value)
    rebuilt = build_live_annual_2025_provision_movement_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("annual provision verified result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-review-blueprint", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.print_review_blueprint:
        value = build_annual_2025_provision_movement_pixel_review_blueprint_v1()
    elif args.verify:
        value = validate_annual_2025_provision_movement_8bank_codex_verified_mapping_replay_v1(
            json.loads((PROJECT_ROOT / RESULT_PATH).read_text(encoding="utf-8"))
        )
    else:
        value = build_live_annual_2025_provision_movement_8bank_codex_verified_mapping_v1()
    sys.stdout.buffer.write(canonical_json_bytes_v1(value) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
