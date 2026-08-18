"""Verify annual-2025 FX/gold activity disclosures across eight banks.

This annual profile reuses the existing FX/gold graph, numeric challenger,
schema binding and accounting-equation verifier.  The V2 graph adds only
family-wide wording variants (prepositions, combined FX/gold, revaluation and
implicit currency-derivative context).  Values may be direct visible cells or
controlled sums of visible source rows; visible dashes are authenticated from
the page render and normalized to zero.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_FX_GOLD_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025fxga8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_FX_GOLD_ACTIVITY_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025fxga8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0138"
REVIEW_PATH = Path(
    "docs/experiments/E-0138-annual-2025-fx-gold-activity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0138-annual-2025-fx-gold-activity-8bank-codex-verified-mapping-v1.json"
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
    "annual2025fxgfdsv2:scan:02536839b38b24f114309f8c93375d9b95ae5fd34a72a815b0ce40d2edb21bd8"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_FX_GOLD_V2_GRAPH_VISIBLE_PDF_UPSTREAM_PPOCRV6_"
    "NUMERIC_CHALLENGER_AUTHENTICATED_DASH_ZERO_PERIOD_UNIT_ACCOUNTING_"
    "LIVE_TM_SCHEMA_ONLY_NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_fx_gold_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_policy_risk_and_exchange_rate_regions_relabelled_as_detailed_note": False,
    "text_similarity_alone_used_for_mapping": False,
    "visible_dash_normalized_to_zero": True,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "combined_and_split_spot_gold_rows_double_counted": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "optional_gold_row_required_in_every_bank": False,
    "source_rows_silently_split_without_accounting_basis": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1175: ("Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối", 1142, 731),
    1176: ("Thu nhập từ hoạt động kinh doanh vàng và ngoại hối", 1175, 732),
    6026: ("Thu từ kinh doanh ngoại tệ giao ngay và vàng", 1175, 733),
    1177: ("Thu từ kinh doanh ngoại tệ giao ngay", 1175, 734),
    1178: ("Thu từ kinh doanh vàng", 1175, 735),
    1179: ("Thu từ các công cụ phái sính tiền tệ", 1175, 736),
    1180: ("Chênh lệch tỷ giá ngoại tệ kinh doanh", 1175, 737),
    1182: ("Chi phí từ hoạt động kinh doanh vàng và ngoại hối", 1175, 739),
    6027: ("Chi về kinh doanh ngoại tệ giao ngay và vàng", 1175, 740),
    1183: ("Chi từ kinh doanh ngoại tệ giao ngay", 1175, 741),
    1184: ("Chi từ kinh doanh vàng", 1175, 742),
    1185: ("Chi từ các công cụ phái sính tiền tệ", 1175, 743),
    1186: ("Chênh lệch tỷ giá ngoại tệ kinh doanh", 1175, 744),
}
_EXPECTED_PAGES = {
    "ACB": [68, 68],
    "MBB": [73, 73],
    "VPB": [69, 69],
    "HDB": [50, 50],
    "VCB": [59, 59],
    "CTG": [58, 58],
    "BID": [55, 55],
    "VIB": [51, 51],
}
_EXPECTED_REPORT_NORM_IDS = {
    "ACB": {1175, 1176, 1177, 1178, 1179, 1182, 1183, 1184, 1185},
    "MBB": {1175, 1176, 1179, 1182, 1185, 6026, 6027},
    "VPB": {1175, 1176, 1177, 1178, 1179, 1182, 1183, 1184, 1185},
    "HDB": {1175, 1176, 1177, 1178, 1179, 1182, 1183, 1184, 1185},
    "VCB": {1175, 1176, 1177, 1178, 1179, 1180, 1182, 1183, 1185, 1186},
    "CTG": {1175, 1176, 1177, 1178, 1179, 1182, 1183, 1184, 1185},
    "BID": {1175, 1176, 1177, 1178, 1179, 1182, 1183, 1184, 1185},
    "VIB": {1175, 1176, 1177, 1179, 1182, 1183, 1185},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 48,
    "authenticated_pixel_dash_zero_count": 5,
    "detailed_note_not_present_document_count": 0,
    "document_count": 8,
    "document_unique_region_count": 8,
    "fresh_vietocr_numeric_disagreement_count": 0,
    "mapping_verified_count": 69,
    "open_source_row_count": 0,
    "q1_source_period_caveat_document_count": 0,
    "verified_source_numeric_component_count": 152,
    "verified_value_cell_count": 138,
}


class Annual2025FxGoldActivity8BankError(ValueError):
    """Annual FX/gold structure, numeric, accounting or schema evidence drifted."""


def _error(message: str) -> Annual2025FxGoldActivity8BankError:
    return Annual2025FxGoldActivity8BankError(message)


def _load(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual FX/gold support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_base() -> ModuleType:
    return _load(
        "annual_2025_fx_gold_activity_base",
        "build_fx_gold_activity_8bank_codex_verified_mapping_v1.py",
    )


def _load_matcher() -> ModuleType:
    return _load("annual_2025_fx_gold_activity_matcher", "fx_gold_activity_variant_graph_v1.py")


def _label(base: ModuleType, item: tuple[int, int, str]) -> dict[str, Any]:
    page, line, text = item
    return base._ref(page, line, text)


def _line(base: ModuleType, item: tuple[int, int, str]) -> dict[str, Any]:
    page, line, text = item
    return base.service._line(page, line, text)


def _dash(
    base: ModuleType, page: int, bbox: Sequence[int], pixel_rgb_sha256: str
) -> dict[str, Any]:
    return base.service._dash(page, bbox, pixel_rgb_sha256)


def _mapped(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    labels: Sequence[tuple[int, int, str]],
    current: Sequence[dict[str, Any]],
    comparative: Sequence[dict[str, Any]],
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "labels": [_label(base, item) for item in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {
            "COMPARATIVE_PERIOD": list(comparative),
            "CURRENT_PERIOD": list(current),
        },
    }


def _direct(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    label: tuple[int, int, str],
    current: tuple[int, int, str],
    comparative: tuple[int, int, str],
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return _mapped(
        base,
        report_norm_id,
        role,
        [label],
        [_line(base, current)],
        [_line(base, comparative)],
        topology,
    )


def _document(
    base: ModuleType,
    code: str,
    page: int,
    periods: Sequence[tuple[int, int, str]],
    units: Sequence[tuple[int, int, str]],
    mappings: Sequence[dict[str, Any]],
    presentation: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": list(mappings),
        "page_span": [page, page],
        "period_axis": [_label(base, item) for item in periods],
        "presentation": presentation,
        "source_period": "2025-12-31",
        "unit_evidence": [_label(base, item) for item in units],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    p = 68
    acb_income = [(p, 12, "2.609.192"), (p, 15, "30.776"), (p, 18, "413.520")]
    acb_income_cmp = [(p, 13, "2.334.176"), (p, 16, "33.219"), (p, 19, "512.898")]
    acb_expense = [(p, 22, "(690.263)"), (p, 25, "(18)"), (p, 28, "(631.321)")]
    acb_expense_cmp = [(p, 23, "(850.749)"), (p, 26, "(2.107)"), (p, 29, "(856.685)")]
    documents.append(
        _document(
            base,
            "ACB",
            p,
            [(p, 6, "Năm 2025"), (p, 7, "Năm 2024")],
            [(p, 8, "Triệu VND"), (p, 9, "Triệu VND")],
            [
                _direct(
                    base,
                    1175,
                    "NET_FX_GOLD",
                    (p, 5, "LÃI THUẦN TỪ HOẠT ĐỘNG KINH DOANH NGOẠI HỐI"),
                    (p, 30, "1.731.886"),
                    (p, 31, "1.170.752"),
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _mapped(
                    base,
                    1176,
                    "INCOME_PARENT",
                    [(p, 10, "Thu nhập từ hoạt động kinh doanh ngoại hối")],
                    [_line(base, x) for x in acb_income],
                    [_line(base, x) for x in acb_income_cmp],
                    "PARENT_VALUE_DERIVED_AS_EXACT_SUM_OF_VISIBLE_CHILDREN",
                ),
                _direct(
                    base,
                    1177,
                    "INCOME_SPOT_FX",
                    (p, 11, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    acb_income[0],
                    acb_income_cmp[0],
                ),
                _direct(
                    base,
                    1178,
                    "INCOME_GOLD",
                    (p, 14, "Thu từ kinh doanh vàng"),
                    acb_income[1],
                    acb_income_cmp[1],
                ),
                _direct(
                    base,
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (p, 17, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    acb_income[2],
                    acb_income_cmp[2],
                ),
                _mapped(
                    base,
                    1182,
                    "EXPENSE_PARENT",
                    [(p, 20, "Chi phí hoạt động kinh doanh ngoại hối")],
                    [_line(base, x) for x in acb_expense],
                    [_line(base, x) for x in acb_expense_cmp],
                    "PARENT_VALUE_DERIVED_AS_EXACT_SUM_OF_VISIBLE_CHILDREN",
                ),
                _direct(
                    base,
                    1183,
                    "EXPENSE_SPOT_FX",
                    (p, 21, "Chi về kinh doanh ngoại tệ giao ngay"),
                    acb_expense[0],
                    acb_expense_cmp[0],
                ),
                _direct(
                    base,
                    1184,
                    "EXPENSE_GOLD",
                    (p, 24, "Chi về kinh doanh vàng"),
                    acb_expense[1],
                    acb_expense_cmp[1],
                ),
                _direct(
                    base,
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (p, 27, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    acb_expense[2],
                    acb_expense_cmp[2],
                ),
            ],
            "SPLIT_SPOT_GOLD_DERIVATIVES_DERIVED_PARENTS_TRAILING_NET",
        )
    )

    p = 73
    documents.append(
        _document(
            base,
            "MBB",
            p,
            [(p, 11, "Năm 2025"), (p, 12, "Năm 2024")],
            [(p, 13, "triệu đồng"), (p, 14, "triệu đồng")],
            [
                _direct(
                    base,
                    1175,
                    "NET_FX_GOLD",
                    (p, 33, "Lãi thuần từ hoạt động kinh doanh ngoại hối"),
                    (p, 34, "1.756.922"),
                    (p, 35, "2.000.164"),
                    "LABELLED_TRAILING_NET",
                ),
                _direct(
                    base,
                    1176,
                    "INCOME_PARENT",
                    (p, 15, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (p, 16, "5.077.663"),
                    (p, 17, "7.057.250"),
                    "LEADING_PARENT_TOTAL",
                ),
                _direct(
                    base,
                    6026,
                    "INCOME_SPOT_FX_AND_GOLD",
                    (p, 18, "Thu về kinh doanh ngoại tệ và vàng"),
                    (p, 19, "3.607.161"),
                    (p, 20, "3.996.204"),
                ),
                _direct(
                    base,
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (p, 21, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (p, 22, "1.470.502"),
                    (p, 23, "3.061.046"),
                ),
                _direct(
                    base,
                    1182,
                    "EXPENSE_PARENT",
                    (p, 24, "Chi phí về hoạt động kinh doanh ngoại hối"),
                    (p, 25, "(3.320.741)"),
                    (p, 26, "(5.057.086)"),
                    "LEADING_PARENT_TOTAL",
                ),
                _direct(
                    base,
                    6027,
                    "EXPENSE_SPOT_FX_AND_GOLD",
                    (p, 27, "Chi về kinh doanh ngoại tệ và vàng"),
                    (p, 28, "(964.614)"),
                    (p, 29, "(1.309.588)"),
                ),
                _direct(
                    base,
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (p, 30, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (p, 31, "(2.356.127)"),
                    (p, 32, "(3.747.498)"),
                ),
            ],
            "COMBINED_SPOT_FX_GOLD_LEADING_PARENTS_LABELLED_NET",
        )
    )

    def split_document(
        code: str,
        page: int,
        periods: Sequence[tuple[int, int, str]],
        units: Sequence[tuple[int, int, str]],
        rows: Sequence[tuple[int, str, tuple[int, str], tuple[int, str], tuple[int, str], str]],
        presentation: str,
    ) -> dict[str, Any]:
        return _document(
            base,
            code,
            page,
            periods,
            units,
            [
                _direct(
                    base,
                    report_id,
                    role,
                    (page, label[0], label[1]),
                    (page, current[0], current[1]),
                    (page, comparative[0], comparative[1]),
                    topology,
                )
                for report_id, role, label, current, comparative, topology in rows
            ],
            presentation,
        )

    p = 69
    documents.append(
        split_document(
            "VPB",
            p,
            [(p, 55, "Năm 2025"), (p, 56, "Năm 2024")],
            [(p, 57, "Triệu đồng"), (p, 58, "Triệu đồng")],
            [
                (
                    1175,
                    "NET_FX_GOLD",
                    (54, "LÃI THUẦN TỪ HOẠT ĐỘNG KINH DOANH NGOẠI HỐI"),
                    (83, "297.016"),
                    (84, "827.240"),
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                (
                    1176,
                    "INCOME_PARENT",
                    (59, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (60, "4.596.739"),
                    (61, "4.745.156"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1177,
                    "INCOME_SPOT_FX",
                    (62, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (63, "3.358.111"),
                    (64, "2.524.315"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1178,
                    "INCOME_GOLD",
                    (65, "Thu từ kinh doanh vàng"),
                    (66, "25.369"),
                    (67, "5.526"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (68, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (69, "1.213.259"),
                    (70, "2.215.315"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1182,
                    "EXPENSE_PARENT",
                    (71, "Chi phí từ hoạt động kinh doanh ngoại hối"),
                    (72, "(4.299.723)"),
                    (73, "(3.917.916)"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1183,
                    "EXPENSE_SPOT_FX",
                    (74, "Chi từ kinh doanh ngoại tệ giao ngay"),
                    (75, "(1.185.233)"),
                    (76, "(892.360)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1184,
                    "EXPENSE_GOLD",
                    (77, "Chi về kinh doanh vàng"),
                    (78, "(12.292)"),
                    (79, "(8.534)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (80, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (81, "(3.102.198)"),
                    (82, "(3.017.022)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
            ],
            "SPLIT_SPOT_GOLD_DERIVATIVES_LEADING_PARENTS_TRAILING_NET",
        )
    )

    p = 50
    documents.append(
        split_document(
            "HDB",
            p,
            [(p, 45, "Năm nay"), (p, 46, "Năm trước")],
            [(p, 47, "Triệu VND"), (p, 48, "Triệu VND")],
            [
                (
                    1175,
                    "NET_FX_GOLD",
                    (44, "LÃI THUẦN TỪ HOẠT ĐỘNG KINH DOANH NGOẠI HỐI"),
                    (73, "1.272.182"),
                    (74, "843.813"),
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                (
                    1176,
                    "INCOME_PARENT",
                    (49, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (50, "3.251.995"),
                    (51, "2.508.481"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1177,
                    "INCOME_SPOT_FX",
                    (52, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (53, "1.891.369"),
                    (54, "1.056.852"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (55, "Thu từ các công cụ tài chính phái sinh"),
                    (56, "1.351.097"),
                    (57, "1.447.279"),
                    "CURRENCY_CONTEXT_INHERITED_FROM_FX_PARENT",
                ),
                (
                    1178,
                    "INCOME_GOLD",
                    (58, "Thu từ kinh doanh vàng"),
                    (59, "9.529"),
                    (60, "4.350"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1182,
                    "EXPENSE_PARENT",
                    (61, "Chi phí hoạt động kinh doanh ngoại hối"),
                    (62, "(1.979.813)"),
                    (63, "(1.664.668)"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1183,
                    "EXPENSE_SPOT_FX",
                    (64, "Chi về kinh doanh ngoại tệ giao ngay"),
                    (65, "(1.410.596)"),
                    (66, "(463.140)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (67, "Chi về các công cụ tài chính phái sinh"),
                    (68, "(569.216)"),
                    (69, "(1.199.983)"),
                    "CURRENCY_CONTEXT_INHERITED_FROM_FX_PARENT",
                ),
                (
                    1184,
                    "EXPENSE_GOLD",
                    (70, "Chi về kinh doanh vàng"),
                    (71, "(1)"),
                    (72, "(1.545)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
            ],
            "SPLIT_SPOT_GOLD_DERIVATIVES_LEADING_PARENTS_TRAILING_NET",
        )
    )

    p = 59
    vcb_gold_current = [
        _dash(
            base,
            p,
            [1155, 620, 1190, 642],
            "2143668318532be7dcce16639d680492e9871e27050a06d4f2df77ac4eed71d0",
        ),
        _dash(
            base,
            p,
            [1155, 655, 1190, 677],
            "dcad0a904a5492ea2d50e1672ee1642267f7952937a9b154996db9b507ca5888",
        ),
    ]
    documents.append(
        _document(
            base,
            "VCB",
            p,
            [(p, 9, "2025"), (p, 10, "2024")],
            [(p, 11, "Triệu VND"), (p, 12, "Triệu VND")],
            [
                _direct(
                    base,
                    1175,
                    "NET_FX_GOLD",
                    (p, 8, "Lãi thuần từ hoạt động kinh doanh ngoại hối"),
                    (p, 48, "6.165.112"),
                    (p, 49, "5.291.751"),
                    "TRAILING_UNLABELED_NET_TOTAL",
                ),
                _direct(
                    base,
                    1176,
                    "INCOME_PARENT",
                    (p, 13, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (p, 32, "11.329.602"),
                    (p, 33, "10.217.498"),
                    "TRAILING_PARENT_TOTAL_AFTER_CHILDREN",
                ),
                _direct(
                    base,
                    1177,
                    "INCOME_SPOT_FX",
                    (p, 14, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (p, 15, "7.252.990"),
                    (p, 16, "6.858.615"),
                ),
                _mapped(
                    base,
                    1178,
                    "INCOME_GOLD",
                    [(p, 21, "Thu từ giao dịch bán vàng"), (p, 23, "Lãi đánh giá lại vàng")],
                    vcb_gold_current,
                    [_line(base, (p, 22, "47.864")), _line(base, (p, 24, "16.737"))],
                    "SUM_OF_GOLD_SALE_AND_REVALUATION_ROWS",
                ),
                _mapped(
                    base,
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    [
                        (p, 17, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                        (p, 29, "Lãi đánh giá lại các hợp đồng phái sinh"),
                    ],
                    [_line(base, (p, 18, "1.529.496")), _line(base, (p, 30, "2.535.847"))],
                    [_line(base, (p, 19, "1.251.901")), _line(base, (p, 31, "2.027.314"))],
                    "SUM_OF_DERIVATIVE_TRADING_AND_REVALUATION_ROWS",
                ),
                _direct(
                    base,
                    1180,
                    "INCOME_FX_DIFFERENCE",
                    (p, 27, "Lãi chênh lệch tỷ giá ngoại tệ kinh doanh"),
                    (p, 25, "11.269"),
                    (p, 28, "15.067"),
                ),
                _direct(
                    base,
                    1182,
                    "EXPENSE_PARENT",
                    (p, 34, "Chi phí hoạt động kinh doanh ngoại hối"),
                    (p, 46, "(5.164.490)"),
                    (p, 47, "(4.925.747)"),
                    "TRAILING_PARENT_TOTAL_AFTER_CHILDREN",
                ),
                _direct(
                    base,
                    1183,
                    "EXPENSE_SPOT_FX",
                    (p, 35, "Chi cho kinh doanh ngoại tệ giao ngay"),
                    (p, 36, "(256.441)"),
                    (p, 37, "(570.251)"),
                ),
                _mapped(
                    base,
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    [
                        (p, 38, "Chi cho các công cụ tài chính phái sinh tiền tệ"),
                        (p, 44, "Lỗ đánh giá lại các hợp đồng phái sinh"),
                    ],
                    [
                        _line(base, (p, 39, "(3.672.606)")),
                        _dash(
                            base,
                            p,
                            [1155, 1044, 1190, 1067],
                            "d848fed98b3205968ad8625fd15235b3576c27fe955a5f18eabf25b722343a27",
                        ),
                    ],
                    [_line(base, (p, 40, "(3.589.995)")), _line(base, (p, 45, "(6.708)"))],
                    "SUM_OF_DERIVATIVE_TRADING_AND_REVALUATION_ROWS",
                ),
                _direct(
                    base,
                    1186,
                    "EXPENSE_FX_DIFFERENCE",
                    (p, 41, "Lỗ chênh lệch tỷ giá ngoại tệ kinh doanh"),
                    (p, 42, "(1.235.443)"),
                    (p, 43, "(758.793)"),
                ),
            ],
            "SPLIT_SPOT_GOLD_REVALUATION_DERIVATIVES_FX_DIFFERENCE_TRAILING_TOTALS",
        )
    )

    p = 58
    documents.append(
        split_document(
            "CTG",
            p,
            [(p, 47, "31.12.2025"), (p, 48, "31.12.2024")],
            [(p, 49, "Triệu đồng"), (p, 50, "Triệu đồng")],
            [
                (
                    1175,
                    "NET_FX_GOLD",
                    (45, "LÃI THUẦN TỪ HOẠT ĐỘNG KINH DOANH NGOẠI HỐI"),
                    (76, "3.120.501"),
                    (77, "4.196.682"),
                    "TRAILING_LABELLED_NET",
                ),
                (
                    1176,
                    "INCOME_PARENT",
                    (51, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (52, "10.059.070"),
                    (53, "15.128.843"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1177,
                    "INCOME_SPOT_FX",
                    (54, "Thu nhập từ mua bán ngoại tệ giao ngay"),
                    (55, "4.200.940"),
                    (56, "6.592.377"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1178,
                    "INCOME_GOLD",
                    (57, "Thu nhập từ kinh doanh vàng"),
                    (58, "657.111"),
                    (59, "861.008"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (60, "Thu nhập từ công cụ tài chính phái sinh tiền tệ"),
                    (61, "5.201.019"),
                    (62, "7.675.458"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1182,
                    "EXPENSE_PARENT",
                    (63, "Chi phí từ hoạt động kinh doanh ngoại hối"),
                    (64, "(6.938.569)"),
                    (65, "(10.932.161)"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1183,
                    "EXPENSE_SPOT_FX",
                    (66, "Chi phí từ mua bán ngoại tệ giao ngay"),
                    (67, "(392.623)"),
                    (68, "(978.803)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1184,
                    "EXPENSE_GOLD",
                    (69, "Chi phí kinh doanh vàng"),
                    (70, "(633.689)"),
                    (71, "(807.582)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (72, "Chi phí từ công cụ tài chính phái sinh tiền tệ"),
                    (73, "(5.912.257)"),
                    (74, "(9.145.776)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
            ],
            "SPLIT_SPOT_GOLD_DERIVATIVES_LEADING_PARENTS_LABELLED_NET",
        )
    )

    p = 55
    documents.append(
        _document(
            base,
            "BID",
            p,
            [(p, 75, "Năm nay"), (p, 76, "Năm trước")],
            [(p, 77, "Triệu VND"), (p, 78, "Triệu VND")],
            [
                _direct(
                    base,
                    1175,
                    "NET_FX_GOLD",
                    (p, 101, "Lãi thuần từ hoạt động kinh doanh ngoại hối"),
                    (p, 102, "3.791.593"),
                    (p, 103, "5.361.499"),
                    "LABELLED_TRAILING_NET",
                ),
                _direct(
                    base,
                    1176,
                    "INCOME_PARENT",
                    (p, 79, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (p, 80, "8.154.420"),
                    (p, 81, "8.671.372"),
                    "LEADING_PARENT_TOTAL",
                ),
                _direct(
                    base,
                    1177,
                    "INCOME_SPOT_FX",
                    (p, 82, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (p, 83, "6.450.805"),
                    (p, 84, "5.987.286"),
                ),
                _mapped(
                    base,
                    1178,
                    "INCOME_GOLD",
                    [(p, 85, "Thu từ kinh doanh vàng")],
                    [
                        _dash(
                            base,
                            p,
                            [1208, 1528, 1245, 1550],
                            "d2be30f3b59901641dcce95a0c295fd6cccb00ea81af85ccec8cd9bca22a180a",
                        )
                    ],
                    [_line(base, (p, 86, "46.743"))],
                    "VISIBLE_DASH_CURRENT_NORMALIZED_ZERO",
                ),
                _direct(
                    base,
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (p, 87, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (p, 88, "1.703.615"),
                    (p, 89, "2.637.343"),
                ),
                _direct(
                    base,
                    1182,
                    "EXPENSE_PARENT",
                    (p, 90, "Chi phí hoạt động kinh doanh ngoại hối"),
                    (p, 91, "(4.362.827)"),
                    (p, 92, "(3.309.873)"),
                    "LEADING_PARENT_TOTAL",
                ),
                _direct(
                    base,
                    1183,
                    "EXPENSE_SPOT_FX",
                    (p, 93, "Chi về kinh doanh ngoại tệ giao ngay"),
                    (p, 94, "(2.287.260)"),
                    (p, 95, "(1.555.674)"),
                ),
                _mapped(
                    base,
                    1184,
                    "EXPENSE_GOLD",
                    [(p, 96, "Chi về kinh doanh vàng")],
                    [
                        _dash(
                            base,
                            p,
                            [1208, 1672, 1245, 1695],
                            "d8dd862f1b03a180e062802f16339b4cee75cd947212ca7d9deecbc5de708bc6",
                        )
                    ],
                    [_line(base, (p, 97, "(5.031)"))],
                    "VISIBLE_DASH_CURRENT_NORMALIZED_ZERO",
                ),
                _direct(
                    base,
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (p, 98, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (p, 99, "(2.075.567)"),
                    (p, 100, "(1.749.168)"),
                ),
            ],
            "SPLIT_SPOT_GOLD_DERIVATIVES_DASH_ZERO_LEADING_PARENTS_LABELLED_NET",
        )
    )

    p = 51
    documents.append(
        split_document(
            "VIB",
            p,
            [(p, 6, "2025"), (p, 7, "2024")],
            [(p, 8, "triệu đồng"), (p, 9, "triệu đồng")],
            [
                (
                    1175,
                    "NET_FX_GOLD",
                    (5, "(LỖ)/LÃI THUẦN TỪ HOẠT ĐỘNG KINH DOANH NGOẠI HỐI"),
                    (28, "(154.292)"),
                    (29, "500.968"),
                    "TRAILING_LABELLED_NET",
                ),
                (
                    1176,
                    "INCOME_PARENT",
                    (10, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (11, "1.417.164"),
                    (12, "1.980.740"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1177,
                    "INCOME_SPOT_FX",
                    (13, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (14, "701.486"),
                    (15, "538.060"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1179,
                    "INCOME_CURRENCY_DERIVATIVES",
                    (16, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (17, "715.678"),
                    (18, "1.442.680"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1182,
                    "EXPENSE_PARENT",
                    (19, "Chi phí hoạt động kinh doanh ngoại hối"),
                    (20, "(1.571.456)"),
                    (21, "(1.479.772)"),
                    "LEADING_PARENT_TOTAL",
                ),
                (
                    1183,
                    "EXPENSE_SPOT_FX",
                    (22, "Chi về kinh doanh ngoại tệ giao ngay"),
                    (23, "(481.616)"),
                    (24, "(348.962)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
                (
                    1185,
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    (25, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (26, "(1.089.840)"),
                    (27, "(1.130.810)"),
                    "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
                ),
            ],
            "SPLIT_SPOT_DERIVATIVES_NO_GOLD_LEADING_PARENTS_LABELLED_NET",
        )
    )
    return documents


def _annual_scan(base: ModuleType, semantic_index: Mapping[str, Any]) -> dict[str, Any]:
    matcher = _load_matcher()
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    trials = []
    for document in axis["documents"]:
        result = matcher.build_fx_gold_activity_variant_graph_document_v2(
            base.scanner._matcher_pages(document)
        )
        trials.append(
            {
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    material = {
        "format_version": "ANNUAL_2025_FX_GOLD_ACTIVITY_8DOCUMENT_STRUCTURE_SCAN_V2",
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "state": "ANNUAL_2025_FX_GOLD_ACTIVITY_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return {**material, "scan_id": "annual2025fxgfdsv2:scan:" + canonical_json_sha256_v1(material)}


def _configure(base: ModuleType, scan_id: str) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base.COMPONENT_VALUE_MODE = True
    base.INCLUDE_COMPONENT_METRICS = True
    base.SCHEMA_FAMILY_END_DISPLAY_ORDER = 745
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = scan_id
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._AUTHORITY = dict(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._review_documents = lambda: _review_documents(base)
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual FX/gold source period drifted"))
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual FX/gold exact metrics drifted")
    for trial, code in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        mapped_ids = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if (
            trial["document_provenance"] != code
            or trial["status"] != "VERIFIED_BY_CODEX"
            or trial["page_span"] != _EXPECTED_PAGES[code]
            or mapped_ids != _EXPECTED_REPORT_NORM_IDS[code]
            or len(trial["verified_accounting_equations"]) != 6
            or trial["source_period_status"]
            != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual FX/gold trial closure drifted")
    return value


def _inputs() -> tuple[ModuleType, dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = _load_base()
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    scan = _annual_scan(base, semantic_index)
    if EXPECTED_SCAN_ID and scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual FX/gold structure scan identity drifted")
    _configure(base, scan["scan_id"])
    return base, semantic_index, crop_manifest, scan


def build_annual_2025_fx_gold_activity_pixel_review_blueprint_v1() -> dict[str, Any]:
    base, _semantic_index, _crop_manifest, _scan = _inputs()
    return base._review_blueprint()


def build_live_annual_2025_fx_gold_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    base, semantic_index, crop_manifest, scan = _inputs()
    review = base._review_blueprint()
    crop_sha = hashlib.sha256(canonical_json_bytes_v1(crop_manifest)).hexdigest()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_fx_gold_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_fx_gold_activity_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return _assert_result(replayed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or (REVIEW_PATH if args.write_review else RESULT_PATH)
    value = (
        build_annual_2025_fx_gold_activity_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_fx_gold_activity_8bank_codex_verified_mapping_v1()
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes_v1(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
