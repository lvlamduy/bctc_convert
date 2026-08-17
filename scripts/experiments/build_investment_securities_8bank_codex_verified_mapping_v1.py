"""Verify the investment-securities family in the eight fixed bank PDFs.

The complete-PDF matcher is bank blind.  This bounded post-scan stage binds
the unique source regions to independently reviewed PDF pixels, exact period
and unit axes, first/last/next-family boundaries, gross/net equations and the
live TM schema interval 804..861.  BID remains unresolved because the bound
page has no admitted local/document-unit inheritance.  VIB is verified for
the directly printed rows while its two TCTD source components remain one
explicit unresolved aggregation into ReportNormId 808.
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
    "InvestmentSecurities8BankCodexVerifiedMappingV1Error",
    "build_investment_securities_8bank_codex_verified_mapping_v1",
    "build_live_investment_securities_8bank_codex_verified_mapping_v1",
    "validate_investment_securities_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load investment-securities support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_module(
    "purchased_debt_support_for_investment_securities_v1",
    "build_purchased_debt_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "investment_securities_scan_for_codex_verified_mapping_v1",
    "scan_investment_securities_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INVESTMENT_SECURITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INVESTMENT_SECURITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
_RESULT_STATE = "CODEX_VERIFIED_INVESTMENT_SECURITIES_MAPPING_COMPLETE"
_RESULT_ID_PREFIX = "e0067:result:"
_REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0067:pixel-review:"
_REVIEW_RUN_ID = "E-0067"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_SHARED_INVESTMENT_SECURITIES_"
    "GRAPH_FIRST_LAST_NEXT_FAMILY_BOUNDARY_HORIZONTAL_VERTICAL_HYBRID_"
    "VISIBLE_PDF_PIXEL_PERIOD_UNIT_DASH_GROSS_NET_ACCOUNTING_AND_LIVE_TM_"
    "SCHEMA_ONLY_NO_EXPORT_CANONICALIZATION_OR_ALTERNATE_VIEW_DOUBLE_COUNT"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path("docs/experiments/E-0067-investment-securities-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0067-investment-securities-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_SCAN_ID = "isfdsv1:scan:fe231d0ded41210ec4c94504aac752fc813a5e941a9d8570277c6dd71e957f37"
REVIEW_SHA256 = "acf1cc5509b6cec833bf3e280f6d29f121e48f0d426681d9383e9ad3b5c43394"

_CHECKS = [
    "COMPLETE_PDF_REGION_ENUMERATION",
    "FIRST_LAST_AND_NEXT_FAMILY_BOUNDARY",
    "HORIZONTAL_VERTICAL_OR_HYBRID_LAYOUT",
    "PERIOD_UNIT_AND_REPORT_SCOPE",
    "VISIBLE_PIXEL_LABEL_DIGITS_DASH_AND_SIGN",
    "AFS_HTM_PROVISION_VAMC_GROSS_NET_EQUATIONS",
    "ALTERNATE_QUALITY_OR_LISTING_VIEW_NOT_DOUBLE_COUNTED",
    "LIVE_TM_SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_coerced_to_zero": False,
    "dash_coerced_to_zero_only_when_visible_in_pdf": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gross_and_net_rows_conflated": False,
    "mapping_decided_by_text_similarity_alone": False,
    "source_order_and_cluster_boundaries_required": True,
    "visible_pdf_pixels_used_for_numeric_truth": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_seven_unique_investment_regions": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "quality_listing_or_provision_movement_double_count_authority": False,
    "text_similarity_alone_used_for_mapping": False,
    "unresolved_unit_or_aggregation_promoted": False,
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
_SCHEMA_EXPECTED = {
    804: ("Chứng khoán đầu tư", 560, 266),
    805: ("Chứng khoán đầu tư sẵn sàng để bán", 804, 267),
    806: ("Chứng khoán nợ", 805, 268),
    807: ("+ Do Chính phủ phát hành (NHNN, Kho bạc)", 805, 269),
    5740: ("Chứng khoán nợ do Chính phủ bảo lãnh", 805, 270),
    808: ("+ Do các TCTD khác phát hành", 805, 271),
    809: ("+ Do các tổ chức kinh tế trong nước phát hành", 805, 272),
    810: ("+ Do các tổ chức kinh tế nước ngoài phát hành", 805, 273),
    812: ("Chứng khoán vốn", 805, 275),
    814: ("+ Do các TCTD khác phát hành", 805, 277),
    815: ("+ Do các tổ chức kinh tế trong nước phát hành", 805, 278),
    816: ("+ Do các tổ chức kinh tế nước ngoài phát hành", 805, 279),
    818: ("Chứng khoán đầu tư sẵn sàng để bán khác", 805, 281),
    824: ("Tổng chứng khoán sẵn sàng để bán", 805, 287),
    825: ("Dự phòng giảm giá chứng khoán sẵn sàng để bán", 805, 288),
    826: ("Trong đó: + Dự phòng giảm giá", 805, 289),
    827: ("+ Dự phòng chung", 805, 290),
    828: ("+ Dự phòng cụ thể", 805, 291),
    829: ("Chứng khoán đầu tư giữ đến ngày đáo hạn", 804, 292),
    830: ("Chứng khoán nợ", 829, 293),
    831: ("+ Do Chính phủ phát hành (NHNN, Kho bạc)", 829, 294),
    832: ("+ Do các TCTD khác phát hành", 829, 295),
    833: ("+ Do các tổ chức kinh tế trong nước phát hành", 829, 296),
    834: ("+ Do các tổ chức kinh tế nước ngoài phát hành", 829, 297),
    848: ("Tổng chứng khoán đầu tư giữ đến ngày đáo hạn", 829, 311),
    849: ("Dự phòng giảm giá đầu tư giữ đến ngày đáo hạn", 829, 312),
    851: ("+ Dự phòng chung", 829, 314),
    852: ("+ Dự phòng cụ thể", 829, 315),
    853: (
        "Phân tích chất lượng chứng khoán được phân loại là tài sản có rủi ro tín dụng",
        804,
        316,
    ),
    854: ("Nợ đủ tiêu chuẩn", 853, 317),
    859: ("Trái phiếu đặc biệt do VAMC phát hành", 804, 322),
    860: ("Mệnh giá trái phiếu đặc biệt", 859, 323),
    861: ("Dự phòng trái phiếu đặc biệt", 859, 324),
    862: ("Các khoản đầu tư dài hạn khác", 560, 325),
}
_EXPECTED_IDS = {
    "ACB": {806, 807, 808, 809, 812, 814, 815, 816, 825, 826, 827, 828, 831, 832, 833},
    "MBB": {807, 5740, 808, 809, 824, 825, 831, 832, 833, 848, 849},
    "VPB": {806, 807, 5740, 808, 809, 812, 815, 818, 824, 825, 826, 827, 854},
    "HDB": {806, 807, 808, 809, 824, 825, 827, 828, 830, 831, 833, 849, 851},
    "VCB": {807, 808, 809, 810, 824, 831, 832, 833, 834, 848, 849, 851, 852},
    "CTG": {806, 807, 808, 809, 812, 815, 825, 827, 828, 831, 832, 833, 848, 849, 852, 860, 861},
    "BID": set(),
    "VIB": {807, 824},
}


class InvestmentSecurities8BankCodexVerifiedMappingV1Error(ValueError):
    """The scan, pixel review, accounting, or live schema drifted."""


def _error(message: str) -> InvestmentSecurities8BankCodexVerifiedMappingV1Error:
    return InvestmentSecurities8BankCodexVerifiedMappingV1Error(message)


def _line(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": pixel_transcription}


def _dash(pixel_region_bbox: Sequence[int]) -> dict[str, Any]:
    return {
        "line_index": None,
        "pixel_region_bbox": list(pixel_region_bbox),
        "pixel_transcription": "-",
    }


def _row(
    role: str,
    report_norm_id: int,
    label_line: int,
    label_pixel: str,
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "label": _line(label_line, label_pixel),
        "report_norm_id": report_norm_id,
        "role": role,
        "values": [
            {"period_role": "CURRENT", **canonical_clone_v1(current)},
            {"period_role": "COMPARATIVE", **canonical_clone_v1(comparative)},
        ],
    }


def _period(
    current_date: str,
    current_heading: Sequence[tuple[int, str]],
    current_unit: tuple[int, str],
    comparative_date: str,
    comparative_heading: Sequence[tuple[int, str]],
    comparative_unit: tuple[int, str],
) -> list[dict[str, Any]]:
    def item(role: str, date: str, heading: Sequence[tuple[int, str]], unit: tuple[int, str]):
        return {
            "heading": [_line(index, text) for index, text in heading],
            "period": date,
            "period_role": role,
            "unit": _line(unit[0], unit[1]),
        }

    return [
        item("CURRENT", current_date, current_heading, current_unit),
        item("COMPARATIVE", comparative_date, comparative_heading, comparative_unit),
    ]


def _boundary(
    first: tuple[int, int, str], last: tuple[int, int, str], next_family: tuple[int, int, str]
) -> dict[str, Any]:
    def item(value: tuple[int, int, str]) -> dict[str, Any]:
        return {
            "line_index": value[1],
            "page_sequence": value[0],
            "pixel_transcription": value[2],
        }

    return {
        "first_item": item(first),
        "last_item": item(last),
        "next_family_boundary": item(next_family),
    }


def _equation_spec(
    role: str,
    page_sequence: int,
    render_sha256: str,
    addends: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "addends": [canonical_clone_v1(item) for item in addends],
        "page_sequence": page_sequence,
        "render_sha256": render_sha256,
        "role": role,
        "total": canonical_clone_v1(total),
    }


def _page_review(
    page_sequence: int,
    render_sha256: str,
    layout: str,
    periods: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "layout": layout,
        "page_sequence": page_sequence,
        "period_axes": [canonical_clone_v1(item) for item in periods],
        "render_sha256": render_sha256,
        "rows": [canonical_clone_v1(item) for item in rows],
    }


def _checks(verified: bool) -> dict[str, str]:
    if verified:
        return {check: "PASS" for check in _CHECKS}
    return {
        check: "UNRESOLVED_DOCUMENT_UNIT_INHERITANCE"
        if check == "PERIOD_UNIT_AND_REPORT_SCOPE"
        else "PASS_STRUCTURE_ONLY_NO_MAPPING_PROMOTION"
        for check in _CHECKS
    }


def _base_document(
    code: str,
    boundary: Mapping[str, Any],
    layout: str,
    pages: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    *,
    verified: bool = True,
    unresolved_items: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "checks": _checks(verified),
        "disposition": "VERIFIED_BY_CODEX" if verified else "UNRESOLVED_MAPPING",
        "equations": [canonical_clone_v1(item) for item in equations],
        "family_boundary": canonical_clone_v1(boundary),
        "layout": layout,
        "pages": [canonical_clone_v1(item) for item in pages],
        "unresolved_items": [canonical_clone_v1(item) for item in unresolved_items],
    }


def _review_documents() -> list[dict[str, Any]]:
    acb = "efdf2dd0f9a5125bb87ddb07fcc9078f2d75ce582b09c53523abe3ea08f5cd2a"
    mbb35 = "0db13918f14d088bce98cec6b51ecfe7d5d14e82a4c4057bc7d3b99f34abf107"
    mbb36 = "568e7ab0bf39e66dcaa1768a9f1125c2cdd9f3b64c929fbbc62978c5c168783d"
    vpb47 = "3c7d426e3402b3367e0119873696e5adcf9da3762f0742fbe07874fad2bbea04"
    vpb48 = "25ffd4f85759c5d77016286fad1797599a1e9ffbbd775cf5ef0ca41e7abd7bad"
    hdb = "fbb5d76db54e1bef2fdbe86d01c394955383ab3f91ad19664288bf7a5ccbbf0c"
    vcb = "e33bd90a3bff4fc42c22012c5c946cc2dd4a86eca2fa3ea0cf2b19cddcfa0391"
    ctg = "85f333d792ad13cae4c5539853bc8bef16fe5bd430a47a8dce1cda6c21224987"
    vib = "5409b12a869a9775994e9192119a83823a08c27ca2a8e9d692d0f147b718be66"

    def two_dates(a: int, b: int, c: tuple[int, str], d: tuple[int, str]) -> list[dict[str, Any]]:
        return _period(
            "2026-06-30",
            [(a, "30/06/2026")],
            c,
            "2025-12-31",
            [(b, "31/12/2025")],
            d,
        )

    docs: dict[str, dict[str, Any]] = {}
    docs["ACB"] = _base_document(
        "ACB",
        _boundary(
            (19, 4, "6. CHỨNG KHOÁN ĐẦU TƯ:"),
            (19, 58, "11.396.527"),
            (19, 59, "7. GÓP VỐN, ĐẦU TƯ DÀI HẠN:"),
        ),
        "ONE_PAGE_AFS_AND_HTM_TWO_DATE_COLUMNS_WITH_EXPLICIT_GROSS_NET_ROWS",
        [
            _page_review(
                19,
                acb,
                "AFS_THEN_HTM_VERTICAL_BRANCHES_SHARED_TWO_DATE_COLUMNS",
                _period(
                    "2026-06-30",
                    [(6, "30.6.2026")],
                    (8, "Triệu đồng"),
                    "2025-12-31",
                    [(7, "31.12.2025")],
                    (9, "Triệu đồng"),
                ),
                [
                    _row(
                        "AFS_DEBT",
                        806,
                        10,
                        "Chứng khoán Nợ",
                        _line(11, "154.846.878"),
                        _line(12, "132.714.613"),
                    ),
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        13,
                        "Chứng khoán Chính phủ",
                        _line(14, "40.155.963"),
                        _line(15, "39.410.741"),
                    ),
                    _row(
                        "AFS_TCTD",
                        808,
                        16,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        _line(17, "113.190.915"),
                        _line(18, "91.803.872"),
                    ),
                    _row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        19,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        _line(20, "1.500.000"),
                        _line(21, "1.500.000"),
                    ),
                    _row(
                        "AFS_EQUITY",
                        812,
                        22,
                        "Chứng khoán Vốn",
                        _line(23, "64.346"),
                        _line(24, "64.226"),
                    ),
                    _row(
                        "AFS_EQUITY_TCTD",
                        814,
                        25,
                        "Chứng khoán vốn do các TCTD khác trong nước phát hành",
                        _dash([1240, 761, 1325, 803]),
                        _dash([1440, 761, 1525, 803]),
                    ),
                    _row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        26,
                        "Chứng khoán vốn do các TCKT trong nước phát hành",
                        _dash([1240, 803, 1325, 844]),
                        _dash([1440, 803, 1525, 844]),
                    ),
                    _row(
                        "AFS_EQUITY_FOREIGN",
                        816,
                        27,
                        "Chứng khoán vốn nước ngoài",
                        _line(28, "64.346"),
                        _line(29, "64.226"),
                    ),
                    _row(
                        "AFS_PROVISION",
                        825,
                        30,
                        "Dự phòng rủi ro chứng khoán sẵn sàng để bán",
                        _line(31, "(11.250)"),
                        _line(32, "(11.250)"),
                    ),
                    _row(
                        "AFS_PRICE_PROVISION",
                        826,
                        33,
                        "Dự phòng giảm giá",
                        _dash([1240, 937, 1325, 976]),
                        _dash([1440, 937, 1525, 976]),
                    ),
                    _row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        34,
                        "Dự phòng chung",
                        _line(35, "(11.250)"),
                        _line(36, "(11.250)"),
                    ),
                    _row(
                        "AFS_SPECIFIC_PROVISION",
                        828,
                        37,
                        "Dự phòng cụ thể",
                        _dash([1240, 1020, 1325, 1058]),
                        _dash([1440, 1020, 1525, 1058]),
                    ),
                    _row(
                        "HTM_GOVERNMENT",
                        831,
                        46,
                        "Chứng khoán Chính phủ",
                        _line(47, "10.877.195"),
                        _line(48, "10.896.527"),
                    ),
                    _row(
                        "HTM_TCTD",
                        832,
                        49,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        _line(50, "500.000"),
                        _line(51, "500.000"),
                    ),
                    _row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        52,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        _dash([1240, 1421, 1325, 1462]),
                        _dash([1440, 1421, 1525, 1462]),
                    ),
                ],
            )
        ],
        [
            _equation_spec(
                "ACB_CURRENT_AFS_DEBT_CHILD_CLOSURE",
                19,
                acb,
                [_line(14, "40.155.963"), _line(17, "113.190.915"), _line(20, "1.500.000")],
                _line(11, "154.846.878"),
            ),
            _equation_spec(
                "ACB_CURRENT_AFS_NET",
                19,
                acb,
                [_line(11, "154.846.878"), _line(23, "64.346"), _line(31, "(11.250)")],
                _line(38, "154.899.974"),
            ),
            _equation_spec(
                "ACB_CURRENT_HTM_CHILD_CLOSURE",
                19,
                acb,
                [_line(47, "10.877.195"), _line(50, "500.000"), _dash([1240, 1421, 1325, 1462])],
                _line(57, "11.377.195"),
            ),
        ],
    )
    docs["MBB"] = _base_document(
        "MBB",
        _boundary(
            (35, 26, "Chứng khoán đầu tư"),
            (36, 30, "4.225.737"),
            (36, 37, "Góp vốn, đầu tư dài hạn"),
        ),
        "TWO_PAGE_AFS_THEN_HTM_WITH_DIRECT_ISSUER_CHILDREN_AND_PRINTED_GROSS_NET",
        [
            _page_review(
                35,
                mbb35,
                "AFS_DIRECT_ISSUER_ROWS",
                two_dates(30, 31, (32, "Triệu đồng"), (33, "Triệu đồng")),
                [
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        35,
                        "Chứng khoán nợ do Chính phủ phát hành",
                        _line(37, "41.232.503"),
                        _line(38, "41.676.117"),
                    ),
                    _row(
                        "AFS_GOVERNMENT_GUARANTEED",
                        5740,
                        39,
                        "Chứng khoán nợ do Chính phủ bảo lãnh",
                        _line(41, "22.052.709"),
                        _line(42, "22.204.008"),
                    ),
                    _row(
                        "AFS_TCTD",
                        808,
                        43,
                        "Chứng khoán nợ do các TCTD khác phát hành",
                        _line(46, "155.087.388"),
                        _line(47, "135.852.313"),
                    ),
                    _row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        48,
                        "Chứng khoán nợ do TCKT trong nước phát hành",
                        _line(51, "24.372.094"),
                        _line(52, "21.780.026"),
                    ),
                    _row(
                        "AFS_GROSS",
                        824,
                        34,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        _line(53, "242.744.694"),
                        _line(54, "221.512.464"),
                    ),
                    _row(
                        "AFS_PROVISION",
                        825,
                        55,
                        "Dự phòng giảm giá chứng khoán sẵn sàng để bán",
                        _line(57, "(182.792)"),
                        _line(58, "(163.351)"),
                    ),
                ],
            ),
            _page_review(
                36,
                mbb36,
                "HTM_DIRECT_ISSUER_ROWS",
                two_dates(3, 4, (5, "Triệu đồng"), (6, "Triệu đồng")),
                [
                    _row(
                        "HTM_GOVERNMENT",
                        831,
                        9,
                        "Chứng khoán nợ do Chính phủ phát hành",
                        _line(11, "268.823"),
                        _line(12, "269.099"),
                    ),
                    _row(
                        "HTM_TCTD",
                        832,
                        13,
                        "Chứng khoán nợ do các TCTD khác phát hành",
                        _line(16, "2.394.664"),
                        _line(17, "2.395.896"),
                    ),
                    _row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        18,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        _line(21, "1.910.162"),
                        _line(22, "1.630.130"),
                    ),
                    _row(
                        "HTM_GROSS",
                        848,
                        7,
                        "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                        _line(23, "4.573.649"),
                        _line(24, "4.295.125"),
                    ),
                    _row(
                        "HTM_PROVISION",
                        849,
                        25,
                        "Dự phòng giảm giá chứng khoán đầu tư giữ đến ngày đáo hạn",
                        _line(27, "(64.820)"),
                        _line(28, "(69.388)"),
                    ),
                ],
            ),
        ],
        [
            _equation_spec(
                "MBB_CURRENT_AFS_GROSS",
                35,
                mbb35,
                [
                    _line(37, "41.232.503"),
                    _line(41, "22.052.709"),
                    _line(46, "155.087.388"),
                    _line(51, "24.372.094"),
                ],
                _line(53, "242.744.694"),
            ),
            _equation_spec(
                "MBB_CURRENT_AFS_NET",
                35,
                mbb35,
                [_line(53, "242.744.694"), _line(57, "(182.792)")],
                _line(59, "242.561.902"),
            ),
            _equation_spec(
                "MBB_CURRENT_HTM_GROSS",
                36,
                mbb36,
                [_line(11, "268.823"), _line(16, "2.394.664"), _line(21, "1.910.162")],
                _line(23, "4.573.649"),
            ),
            _equation_spec(
                "MBB_CURRENT_HTM_NET",
                36,
                mbb36,
                [_line(23, "4.573.649"), _line(27, "(64.820)")],
                _line(29, "4.508.829"),
            ),
        ],
    )
    docs["VPB"] = _base_document(
        "VPB",
        _boundary(
            (47, 5, "CHỨNG KHOÁN ĐẦU TƯ"),
            (48, 82, "25.092.035"),
            (48, 84, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "AFS_MAIN_TABLE_THEN_PROVISION_MOVEMENT_AND_QUALITY_ALTERNATE_VIEW",
        [
            _page_review(
                47,
                vpb47,
                "AFS_WITH_SUBSET_GOVERNMENT_GUARANTEE",
                _period(
                    "2026-03-31",
                    [(8, "Ngày 31 tháng 3"), (10, "năm 2026")],
                    (12, "Triệu đồng"),
                    "2025-12-31",
                    [(9, "Ngày 31 tháng 12"), (11, "năm 2025")],
                    (13, "Triệu đồng"),
                ),
                [
                    _row(
                        "AFS_DEBT",
                        806,
                        14,
                        "Chứng khoán nợ",
                        _line(15, "64.671.684"),
                        _line(16, "63.730.573"),
                    ),
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        17,
                        "Chứng khoán Chính phủ, chính quyền địa phương",
                        _line(18, "37.968.313"),
                        _line(19, "37.452.901"),
                    ),
                    _row(
                        "AFS_GOVERNMENT_GUARANTEED_SUBSET",
                        5740,
                        23,
                        "Trong đó: Trái phiếu được Chính phủ bảo lãnh",
                        _line(24, "1.177.978"),
                        _line(25, "1.185.637"),
                    ),
                    _row(
                        "AFS_TCTD",
                        808,
                        20,
                        "Chứng khoán nợ do các TCTD khác trong nước",
                        _line(21, "24.138.647"),
                        _line(22, "23.472.758"),
                    ),
                    _row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        26,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        _line(27, "2.564.724"),
                        _line(28, "2.804.914"),
                    ),
                    _row(
                        "AFS_EQUITY",
                        812,
                        29,
                        "Chứng khoán vốn",
                        _line(30, "732.357"),
                        _line(31, "732.357"),
                    ),
                    _row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        32,
                        "Chứng khoán vốn do các TCKT trong nước phát hành",
                        _line(33, "732.357"),
                        _line(34, "732.357"),
                    ),
                    _row(
                        "AFS_OTHER",
                        818,
                        35,
                        "Tài sản tài chính khác",
                        _line(36, "456.159"),
                        _dash([1430, 727, 1530, 759]),
                    ),
                    _row(
                        "AFS_GROSS",
                        824,
                        7,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        _line(38, "65.860.200"),
                        _line(39, "64.462.930"),
                    ),
                    _row(
                        "AFS_PROVISION",
                        825,
                        40,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        _line(41, "(27.063)"),
                        _line(42, "(28.864)"),
                    ),
                    _row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        43,
                        "Dự phòng chung",
                        _line(44, "(19.236)"),
                        _line(45, "(21.037)"),
                    ),
                    _row(
                        "AFS_PRICE_PROVISION",
                        826,
                        46,
                        "Dự phòng giảm giá",
                        _line(47, "(7.827)"),
                        _line(48, "(7.827)"),
                    ),
                ],
            ),
            _page_review(
                48,
                vpb48,
                "QUALITY_ALTERNATE_VIEW_NOT_ADDED_TO_AFS_GROSS",
                _period(
                    "2026-03-31",
                    [(72, "Ngày 31 tháng 3"), (74, "năm 2026")],
                    (76, "Triệu đồng"),
                    "2025-12-31",
                    [(73, "Ngày 31 tháng 12"), (75, "năm 2025")],
                    (77, "Triệu đồng"),
                ),
                [
                    _row(
                        "QUALITY_STANDARD",
                        854,
                        78,
                        "Nợ đủ tiêu chuẩn",
                        _line(79, "25.525.393"),
                        _line(80, "25.092.035"),
                    ),
                ],
            ),
        ],
        [
            _equation_spec(
                "VPB_CURRENT_AFS_DEBT",
                47,
                vpb47,
                [_line(18, "37.968.313"), _line(21, "24.138.647"), _line(27, "2.564.724")],
                _line(15, "64.671.684"),
            ),
            _equation_spec(
                "VPB_CURRENT_AFS_GROSS",
                47,
                vpb47,
                [_line(15, "64.671.684"), _line(30, "732.357"), _line(36, "456.159")],
                _line(38, "65.860.200"),
            ),
            _equation_spec(
                "VPB_CURRENT_AFS_NET",
                47,
                vpb47,
                [_line(38, "65.860.200"), _line(41, "(27.063)")],
                _line(49, "65.833.137"),
            ),
            _equation_spec(
                "VPB_CURRENT_GENERAL_PROVISION_MOVEMENT_CHECK_ONLY",
                48,
                vpb48,
                [_line(22, "21.037"), _line(28, "(1.801)")],
                _line(33, "19.236"),
            ),
        ],
    )
    docs["HDB"] = _base_document(
        "HDB",
        _boundary(
            (29, 43, "Chứng khoán đầu tư"),
            (29, 97, "4.033.731"),
            (30, 7, "Góp vốn, đầu tư dài hạn"),
        ),
        "ONE_PAGE_AFS_AND_HTM_WITH_RELATIVE_PERIOD_AXES",
        [
            _page_review(
                29,
                hdb,
                "AFS_THEN_HTM_RELATIVE_PERIOD_COLUMNS",
                _period(
                    "2026-06-30",
                    [(46, "Số cuối kỳ")],
                    (48, "Triệu VND"),
                    "2025-12-31",
                    [(47, "Số đầu kỳ")],
                    (49, "Triệu VND"),
                ),
                [
                    _row(
                        "AFS_DEBT",
                        806,
                        51,
                        "Chứng khoán Nợ",
                        _line(52, "99.072.619"),
                        _line(53, "72.904.811"),
                    ),
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        54,
                        "Chứng khoán Chính phủ",
                        _line(55, "21.591.915"),
                        _line(56, "19.704.580"),
                    ),
                    _row(
                        "AFS_TCTD",
                        808,
                        57,
                        "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                        _line(58, "59.292.477"),
                        _line(59, "36.288.479"),
                    ),
                    _row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        60,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        _line(61, "18.188.227"),
                        _line(62, "16.911.752"),
                    ),
                    _row(
                        "AFS_GROSS",
                        824,
                        45,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        _line(63, "99.072.619"),
                        _line(64, "72.904.811"),
                    ),
                    _row(
                        "AFS_PROVISION",
                        825,
                        65,
                        "Dự phòng rủi ro chứng khoán đầu tư sẵn sàng để bán",
                        _line(66, "(137.141)"),
                        _line(67, "(126.838)"),
                    ),
                    _row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        68,
                        "Dự phòng chung",
                        _line(69, "(136.412)"),
                        _line(70, "(126.838)"),
                    ),
                    _row(
                        "AFS_SPECIFIC_PROVISION",
                        828,
                        71,
                        "Dự phòng cụ thể",
                        _line(72, "(729)"),
                        _dash([1390, 1415, 1505, 1450]),
                    ),
                    _row(
                        "HTM_DEBT",
                        830,
                        81,
                        "Chứng khoán Nợ",
                        _line(82, "5.228.294"),
                        _line(83, "4.039.836"),
                    ),
                    _row(
                        "HTM_GOVERNMENT",
                        831,
                        84,
                        "Chứng khoán Chính phủ",
                        _line(85, "3.220.483"),
                        _line(86, "3.225.821"),
                    ),
                    _row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        87,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        _line(88, "2.007.811"),
                        _line(89, "814.015"),
                    ),
                    _row(
                        "HTM_PROVISION",
                        849,
                        90,
                        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn",
                        _line(91, "(15.058)"),
                        _line(92, "(6.105)"),
                    ),
                    _row(
                        "HTM_GENERAL_PROVISION",
                        851,
                        93,
                        "Dự phòng chung",
                        _line(94, "(15.058)"),
                        _line(95, "(6.105)"),
                    ),
                ],
            )
        ],
        [
            _equation_spec(
                "HDB_CURRENT_AFS_DEBT",
                29,
                hdb,
                [_line(55, "21.591.915"), _line(58, "59.292.477"), _line(61, "18.188.227")],
                _line(52, "99.072.619"),
            ),
            _equation_spec(
                "HDB_CURRENT_AFS_NET",
                29,
                hdb,
                [_line(63, "99.072.619"), _line(66, "(137.141)")],
                _line(73, "98.935.478"),
            ),
            _equation_spec(
                "HDB_CURRENT_HTM_DEBT",
                29,
                hdb,
                [_line(85, "3.220.483"), _line(88, "2.007.811")],
                _line(82, "5.228.294"),
            ),
            _equation_spec(
                "HDB_CURRENT_HTM_NET",
                29,
                hdb,
                [_line(82, "5.228.294"), _line(91, "(15.058)")],
                _line(96, "5.213.236"),
            ),
        ],
    )
    docs["VCB"] = _base_document(
        "VCB",
        _boundary(
            (32, 8, "7. Chứng khoán đầu tư"),
            (32, 58, "162.104.164"),
            (33, 9, "Góp vốn đầu tư dài hạn"),
        ),
        "ONE_PAGE_AFS_AND_HTM_WITH_COMBINED_NET_TOTAL",
        [
            _page_review(
                32,
                vcb,
                "AFS_AND_HTM_TWO_DATE_COLUMNS",
                _period(
                    "2026-06-30",
                    [(9, "30/6/2026")],
                    (11, "Triệu VND"),
                    "2025-12-31",
                    [(10, "31/12/2025")],
                    (12, "Triệu VND"),
                ),
                [
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        16,
                        "Trái phiếu Chính phủ",
                        _line(17, "61.759.548"),
                        _line(18, "60.984.052"),
                    ),
                    _row(
                        "AFS_TCTD",
                        808,
                        19,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        _line(20, "62.362.195"),
                        _line(21, "77.174.749"),
                    ),
                    _row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        22,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        _line(23, "268.100"),
                        _dash([1380, 626, 1500, 662]),
                    ),
                    _row(
                        "AFS_FOREIGN",
                        810,
                        26,
                        "Chứng khoán nợ nước ngoài",
                        _line(24, "5.214.965"),
                        _line(25, "4.922.016"),
                    ),
                    _row(
                        "AFS_GROSS",
                        824,
                        14,
                        "Chứng khoán đầu tư sẵn sàng để bán",
                        _line(27, "129.604.808"),
                        _line(28, "143.080.817"),
                    ),
                    _row(
                        "HTM_GOVERNMENT",
                        831,
                        31,
                        "Trái phiếu Chính phủ",
                        _line(32, "16.586.880"),
                        _line(33, "11.688.254"),
                    ),
                    _row(
                        "HTM_TCTD",
                        832,
                        34,
                        "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                        _line(35, "1.235.327"),
                        _line(36, "1.252.443"),
                    ),
                    _row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        37,
                        "Chứng khoán nợ do các TCKT trong nước phát hành",
                        _line(38, "6.932.500"),
                        _line(39, "7.524.850"),
                    ),
                    _row(
                        "HTM_FOREIGN",
                        834,
                        40,
                        "Chứng khoán nợ nước ngoài",
                        _line(41, "1.397.284"),
                        _line(42, "1.919.415"),
                    ),
                    _row(
                        "HTM_GROSS",
                        848,
                        29,
                        "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                        _line(43, "26.151.991"),
                        _line(44, "22.384.962"),
                    ),
                    _row(
                        "HTM_PROVISION",
                        849,
                        47,
                        "Dự phòng chứng khoán đầu tư giữ đến ngày đáo hạn",
                        _line(45, "(1.348.044)"),
                        _line(46, "(3.361.615)"),
                    ),
                    _row(
                        "HTM_GENERAL_PROVISION",
                        851,
                        49,
                        "Dự phòng chung Trái phiếu doanh nghiệp chưa niêm yết",
                        _line(50, "(51.544)"),
                        _line(51, "(54.742)"),
                    ),
                    _row(
                        "HTM_SPECIFIC_PROVISION",
                        852,
                        54,
                        "Dự phòng cụ thể Trái phiếu doanh nghiệp chưa niêm yết",
                        _line(52, "(1.296.500)"),
                        _line(53, "(3.306.873)"),
                    ),
                ],
            )
        ],
        [
            _equation_spec(
                "VCB_CURRENT_AFS_GROSS",
                32,
                vcb,
                [
                    _line(17, "61.759.548"),
                    _line(20, "62.362.195"),
                    _line(23, "268.100"),
                    _line(24, "5.214.965"),
                ],
                _line(27, "129.604.808"),
            ),
            _equation_spec(
                "VCB_CURRENT_HTM_GROSS",
                32,
                vcb,
                [
                    _line(32, "16.586.880"),
                    _line(35, "1.235.327"),
                    _line(38, "6.932.500"),
                    _line(41, "1.397.284"),
                ],
                _line(43, "26.151.991"),
            ),
            _equation_spec(
                "VCB_CURRENT_HTM_PROVISION",
                32,
                vcb,
                [_line(50, "(51.544)"), _line(52, "(1.296.500)")],
                _line(45, "(1.348.044)"),
            ),
            _equation_spec(
                "VCB_CURRENT_COMBINED_NET",
                32,
                vcb,
                [_line(27, "129.604.808"), _line(43, "26.151.991"), _line(45, "(1.348.044)")],
                _line(57, "154.408.755"),
            ),
        ],
    )
    docs["CTG"] = _base_document(
        "CTG",
        _boundary(
            (40, 4, "5. CHỨNG KHOÁN ĐẦU TƯ"),
            (40, 65, "211.880.390"),
            (40, 66, "6. GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "ONE_PAGE_AFS_HTM_AND_VAMC_WITH_NET_BRANCH_ROWS",
        [
            _page_review(
                40,
                ctg,
                "AFS_THEN_HTM_WITH_VAMC_INCLUDED_IN_HTM_GROSS",
                _period(
                    "2026-06-30",
                    [(5, "30/06/2026")],
                    (7, "triệu đồng"),
                    "2025-12-31",
                    [(6, "31/12/2025")],
                    (8, "triệu đồng"),
                ),
                [
                    _row(
                        "AFS_DEBT",
                        806,
                        12,
                        "Chứng khoán Nợ",
                        _line(13, "176.457.966"),
                        _line(14, "203.166.496"),
                    ),
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        15,
                        "Chứng khoán Chính phủ",
                        _line(16, "106.603.307"),
                        _line(17, "101.533.661"),
                    ),
                    _row(
                        "AFS_TCTD",
                        808,
                        18,
                        "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                        _line(19, "67.935.288"),
                        _line(20, "99.697.917"),
                    ),
                    _row(
                        "AFS_DOMESTIC_TCKT",
                        809,
                        21,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        _line(22, "1.919.371"),
                        _line(23, "1.934.918"),
                    ),
                    _row(
                        "AFS_EQUITY",
                        812,
                        24,
                        "Chứng khoán Vốn",
                        _line(25, "373.138"),
                        _line(26, "438.615"),
                    ),
                    _row(
                        "AFS_EQUITY_DOMESTIC_TCKT",
                        815,
                        27,
                        "Chứng khoán Vốn do các TCKT trong nước phát hành",
                        _line(28, "373.138"),
                        _line(29, "438.615"),
                    ),
                    _row(
                        "AFS_PROVISION",
                        825,
                        30,
                        "Dự phòng rủi ro chứng khoán sẵn sàng để bán",
                        _line(31, "(111.893)"),
                        _line(32, "(113.762)"),
                    ),
                    _row(
                        "AFS_GENERAL_PROVISION",
                        827,
                        33,
                        "Dự phòng chung",
                        _line(34, "(11.893)"),
                        _line(35, "(13.762)"),
                    ),
                    _row(
                        "AFS_SPECIFIC_PROVISION",
                        828,
                        36,
                        "Dự phòng cụ thể",
                        _line(37, "(100.000)"),
                        _line(38, "(100.000)"),
                    ),
                    _row(
                        "HTM_GOVERNMENT",
                        831,
                        45,
                        "Chứng khoán Chính phủ",
                        _line(46, "590.000"),
                        _line(47, "183.000"),
                    ),
                    _row(
                        "HTM_TCTD",
                        832,
                        48,
                        "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                        _line(49, "50.000.000"),
                        _line(50, "8.000.000"),
                    ),
                    _row(
                        "VAMC_FACE_VALUE",
                        860,
                        51,
                        "Mệnh giá trái phiếu VAMC",
                        _line(52, "235.806"),
                        _line(53, "237.170"),
                    ),
                    _row(
                        "HTM_DOMESTIC_TCKT",
                        833,
                        54,
                        "Chứng khoán Nợ do các TCKT trong nước phát hành",
                        _dash([1680, 1502, 1855, 1556]),
                        _line(55, "386.748"),
                    ),
                    _row(
                        "HTM_GROSS",
                        848,
                        42,
                        "Giá trị chứng khoán",
                        _line(43, "50.825.806"),
                        _line(44, "8.806.918"),
                    ),
                    _row(
                        "HTM_PROVISION",
                        849,
                        56,
                        "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn",
                        _line(57, "(57.126)"),
                        _line(58, "(417.877)"),
                    ),
                    _row(
                        "HTM_SPECIFIC_PROVISION",
                        852,
                        59,
                        "Dự phòng cụ thể",
                        _dash([1690, 1615, 1860, 1670]),
                        _line(60, "(386.748)"),
                    ),
                    _row(
                        "VAMC_PROVISION",
                        861,
                        61,
                        "Dự phòng trái phiếu VAMC",
                        _line(62, "(57.126)"),
                        _line(63, "(31.129)"),
                    ),
                ],
            )
        ],
        [
            _equation_spec(
                "CTG_CURRENT_AFS_DEBT",
                40,
                ctg,
                [_line(16, "106.603.307"), _line(19, "67.935.288"), _line(22, "1.919.371")],
                _line(13, "176.457.966"),
            ),
            _equation_spec(
                "CTG_CURRENT_AFS_NET",
                40,
                ctg,
                [_line(13, "176.457.966"), _line(25, "373.138"), _line(31, "(111.893)")],
                _line(10, "176.719.211"),
            ),
            _equation_spec(
                "CTG_CURRENT_HTM_GROSS",
                40,
                ctg,
                [
                    _line(46, "590.000"),
                    _line(49, "50.000.000"),
                    _line(52, "235.806"),
                    _dash([1680, 1502, 1855, 1556]),
                ],
                _line(43, "50.825.806"),
            ),
            _equation_spec(
                "CTG_CURRENT_HTM_PROVISION",
                40,
                ctg,
                [_dash([1690, 1615, 1860, 1670]), _line(62, "(57.126)")],
                _line(57, "(57.126)"),
            ),
            _equation_spec(
                "CTG_CURRENT_HTM_NET",
                40,
                ctg,
                [_line(43, "50.825.806"), _line(57, "(57.126)")],
                _line(40, "50.768.680"),
            ),
            _equation_spec(
                "CTG_CURRENT_COMBINED_NET",
                40,
                ctg,
                [_line(10, "176.719.211"), _line(40, "50.768.680")],
                _line(64, "227.487.891"),
            ),
        ],
    )
    docs["BID"] = _base_document(
        "BID",
        _boundary(
            (23, 38, "5. CHỨNG KHOÁN ĐẦU TƯ"),
            (23, 90, "113.603.497"),
            (24, 5, "6. GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "AFS_AND_HTM_TWO_DATE_COLUMNS_WITHOUT_LOCAL_UNIT",
        [],
        [],
        verified=False,
        unresolved_items=[
            {
                "page_sequence": 23,
                "reason": "LOCAL_OR_REPLAY_BOUND_DOCUMENT_UNIT_NOT_ADMITTED",
                "source_label": "CHỨNG KHOÁN ĐẦU TƯ",
            }
        ],
    )
    docs["VIB"] = _base_document(
        "VIB",
        _boundary(
            (36, 5, "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN"),
            (36, 23, "51.149.531"),
            (36, 33, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        ),
        "IMPLICIT_FAMILY_OWNER_AFS_ONLY_WITH_TWO_TCTD_COMPONENT_ROWS",
        [
            _page_review(
                36,
                vib,
                "AFS_ONLY_TWO_DATE_COLUMNS",
                _period(
                    "2026-06-30",
                    [(7, "30/06/2026")],
                    (9, "triệu đồng"),
                    "2025-12-31",
                    [(8, "31/12/2025")],
                    (10, "triệu đồng"),
                ),
                [
                    _row(
                        "AFS_GOVERNMENT",
                        807,
                        12,
                        "Trái phiếu Chính phủ",
                        _line(13, "10.502.823"),
                        _line(14, "10.793.007"),
                    ),
                    _row(
                        "AFS_GROSS",
                        824,
                        5,
                        "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN",
                        _line(22, "49.276.373"),
                        _line(23, "51.149.531"),
                    ),
                ],
            )
        ],
        [
            _equation_spec(
                "VIB_CURRENT_AFS_GROSS_COMPONENT_CHECK",
                36,
                vib,
                [_line(13, "10.502.823"), _line(17, "5.894.320"), _line(20, "32.879.230")],
                _line(22, "49.276.373"),
            ),
            _equation_spec(
                "VIB_COMPARATIVE_AFS_GROSS_COMPONENT_CHECK",
                36,
                vib,
                [_line(14, "10.793.007"), _line(18, "12.104.102"), _line(21, "28.252.422")],
                _line(23, "51.149.531"),
            ),
        ],
        unresolved_items=[
            {
                "page_sequence": 36,
                "reason": "TWO_SOURCE_COMPONENTS_REQUIRE_EXPLICIT_AGGREGATION_INTO_REPORT_NORM_ID_808",
                "source_label": "Trái phiếu và chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
            }
        ],
    )
    return [docs[code] for code in EXPECTED_DOCUMENT_ORDER]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": _REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "state": _REVIEW_STATE,
    }
    return {**material, "review_id": _REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex investment-securities pixel review differs from fixed ledger")
    return canonical_clone_v1(expected)


def _schema_binding(item: Any, expected_id: int) -> dict[str, Any]:
    name, parent, _legacy_order = _SCHEMA_EXPECTED[expected_id]
    if (
        item.schema_id != expected_id
        or item.canonical_name != name
        or item.parent_id != parent
        or type(item.display_order) is not int
    ):
        raise _error(f"live TM schema item {expected_id} drifted")
    return {
        "canonical_name": name,
        "display_order": item.display_order,
        "parent_report_norm_id": parent,
        "report_norm_id": expected_id,
    }


def _equation(role: str, addends: Sequence[int], total: int) -> dict[str, Any]:
    computed = sum(addends)
    if computed != total:
        raise _error(f"visible investment-securities accounting equation does not close: {role}")
    return {
        "addends": list(addends),
        "computed_total": computed,
        "role": role,
        "visible_total": total,
    }


def _trial(
    code: str,
    ordinal: int,
    review_document: Mapping[str, Any],
    scan_trial: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    schema_bindings: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    semantic_document = support._document(semantic_index["documents"], code, "semantic index")
    manifest_document = support._document(crop_manifest["documents"], code, "crop manifest")
    matcher_result = scan_trial["matcher_result"]
    if matcher_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
        raise _error("reviewed investment-securities region is not unique in complete PDF")
    boundary = support._boundary_evidence(
        semantic_document, manifest_document, review_document["family_boundary"]
    )
    if review_document["disposition"] == "UNRESOLVED_MAPPING":
        return {
            "bank_provenance": code,
            "document_ordinal": ordinal,
            "family_boundary": boundary,
            "layout": review_document["layout"],
            "page_evidence": [],
            "source_pdf": canonical_clone_v1(semantic_document["source_pdf"]),
            "status": "UNRESOLVED_MAPPING",
            "structural_scan_result_id": matcher_result["result_id"],
            "unresolved_items": canonical_clone_v1(review_document["unresolved_items"]),
            "verified_accounting_equations": [],
            "verified_mappings": [],
        }
    page_evidence = []
    values_by_id: dict[int, list[dict[str, Any]]] = {}
    for page_review in review_document["pages"]:
        page_number = page_review["page_sequence"]
        render_sha = page_review["render_sha256"]
        periods = []
        for period in page_review["period_axes"]:
            periods.append(
                {
                    "heading": [
                        support._label_evidence(
                            semantic_document, manifest_document, page_number, item, render_sha
                        )
                        for item in period["heading"]
                    ],
                    "period": period["period"],
                    "period_role": period["period_role"],
                    "unit": support._label_evidence(
                        semantic_document,
                        manifest_document,
                        page_number,
                        period["unit"],
                        render_sha,
                    ),
                }
            )
        rows = []
        for row in page_review["rows"]:
            values = [
                {
                    "period_role": value["period_role"],
                    **support._money_evidence(
                        semantic_document, manifest_document, page_number, value, render_sha
                    ),
                }
                for value in row["values"]
            ]
            if row["report_norm_id"] in values_by_id:
                raise _error("one schema row received multiple unadjudicated source mappings")
            values_by_id[row["report_norm_id"]] = canonical_clone_v1(values)
            rows.append(
                {
                    "label": support._label_evidence(
                        semantic_document, manifest_document, page_number, row["label"], render_sha
                    ),
                    "report_norm_id": row["report_norm_id"],
                    "role": row["role"],
                    "values": values,
                }
            )
        semantic_page = support._page(semantic_document, page_number, "semantic index")
        page_evidence.append(
            {
                "geometry_mode": semantic_page["geometry_mode"],
                "layout": page_review["layout"],
                "page_sequence": page_number,
                "period_axes": periods,
                "render_ref": support._render(manifest_document, page_number, render_sha),
                "rows": rows,
                "source_projection": canonical_clone_v1(semantic_page["source_projection"]),
            }
        )
    equations = []
    for spec in review_document["equations"]:
        addends = [
            support._money_evidence(
                semantic_document,
                manifest_document,
                spec["page_sequence"],
                item,
                spec["render_sha256"],
            )
            for item in spec["addends"]
        ]
        total = support._money_evidence(
            semantic_document,
            manifest_document,
            spec["page_sequence"],
            spec["total"],
            spec["render_sha256"],
        )
        equations.append(
            {
                **_equation(
                    spec["role"],
                    [item["normalized_value"] for item in addends],
                    total["normalized_value"],
                ),
                "source_addends": addends,
                "source_total": total,
            }
        )
    mappings = [
        {
            **canonical_clone_v1(schema_bindings[report_norm_id]),
            "source_values": canonical_clone_v1(values),
            "status": "VERIFIED_BY_CODEX",
        }
        for report_norm_id, values in values_by_id.items()
    ]
    return {
        "bank_provenance": code,
        "document_ordinal": ordinal,
        "family_boundary": boundary,
        "layout": review_document["layout"],
        "page_evidence": page_evidence,
        "source_pdf": canonical_clone_v1(semantic_document["source_pdf"]),
        "status": "VERIFIED_BY_CODEX",
        "structural_scan_result_id": matcher_result["result_id"],
        "unresolved_items": canonical_clone_v1(review_document["unresolved_items"]),
        "verified_accounting_equations": equations,
        "verified_mappings": mappings,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "dash_cell_verified_as_zero_count": sum(
            value["source_cell_status"] == "DASH"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["source_values"]
        ),
        "document_count": len(trials),
        "document_unresolved_count": sum(
            trial["status"] == "UNRESOLVED_MAPPING" for trial in trials
        ),
        "document_verified_count": sum(trial["status"] == "VERIFIED_BY_CODEX" for trial in trials),
        "mapped_value_cell_count": sum(
            len(mapping["source_values"])
            for trial in trials
            for mapping in trial["verified_mappings"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "unresolved_mapping_count": sum(len(trial["unresolved_items"]) for trial in trials),
    }


def build_investment_securities_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build bounded investment-securities mappings from replayed inputs."""

    checked_review = _review(review)
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("fixed complete-PDF investment-securities scan identity drifted")
    if type(semantic_index) is not dict or type(crop_manifest) is not dict:
        raise _error("semantic index and crop manifest must be exact objects")
    if type(schema_authority) is not dict or type(schema_by_id) is not dict:
        raise _error("live TM schema authority drifted")
    schema_bindings = {
        report_norm_id: _schema_binding(schema_by_id[report_norm_id], report_norm_id)
        for report_norm_id in _SCHEMA_EXPECTED
    }
    if (
        schema_by_id[804].children != [805, 829, 853, 859]
        or schema_by_id[804].next_id != 805
        or schema_by_id[861].next_id != 862
        or schema_by_id[862].previous_id != 861
    ):
        raise _error("investment-securities first/last/next schema boundary drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        review_document = next(
            item for item in checked_review["documents"] if item["bank_code"] == code
        )
        scan_trial = next(
            item for item in structure_scan["trials"] if item["document_provenance"] == code
        )
        trials.append(
            _trial(
                code,
                ordinal,
                review_document,
                scan_trial,
                semantic_index,
                crop_manifest,
                schema_bindings,
            )
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": crop_manifest_sha256,
            "investment_securities_scan_id": structure_scan["scan_id"],
            "pixel_review_id": checked_review["review_id"],
            "pixel_review_sha256": review_sha256,
            "semantic_axis_sha256": structure_scan["input_semantic_axis_sha256"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-securities verified result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("investment-securities verified identity, authority or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("bank_provenance") != code
            or trial.get("status") not in {"VERIFIED_BY_CODEX", "UNRESOLVED_MAPPING"}
        ):
            raise _error("investment-securities verified trial identity drifted")
        ids = {mapping.get("report_norm_id") for mapping in trial["verified_mappings"]}
        if ids != _EXPECTED_IDS[code]:
            raise _error("verified investment-securities mapping shape drifted")
        if trial["status"] == "UNRESOLVED_MAPPING" and (
            trial["verified_mappings"]
            or trial["verified_accounting_equations"]
            or trial["page_evidence"]
            or not trial["unresolved_items"]
        ):
            raise _error("unresolved investment-securities trial was promoted")
        if trial["status"] == "VERIFIED_BY_CODEX" and any(
            mapping.get("status") != "VERIFIED_BY_CODEX" for mapping in trial["verified_mappings"]
        ):
            raise _error("verified investment-securities status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("investment-securities verified result identity drifted")
    return canonical_clone_v1(value)


def _stable_json(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload = support.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> tuple[Any, Any, Any, Any, Any, Any, str, str]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, manifest_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_investment_securities_full_document_scan_v1(semantic_index)
    if not REVIEW_SHA256:
        raise _error("fixed investment-securities review SHA is not sealed")
    review, review_sha = _stable_json(REVIEW_PATH, REVIEW_SHA256)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        manifest_sha,
        review_sha,
    )


def build_live_investment_securities_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay every fixed input and derive the bounded result."""

    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        authority,
        by_id,
        manifest_sha,
        review_sha,
    ) = _live_inputs()
    return build_investment_securities_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        authority,
        by_id,
        crop_manifest_sha256=manifest_sha,
        review_sha256=review_sha,
    )


def validate_investment_securities_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild one persisted result from all fixed live inputs."""

    persisted = _validate_result(value)
    rebuilt = build_live_investment_securities_8bank_codex_verified_mapping_v1()
    if same_typed_json_v1(persisted, rebuilt):
        return rebuilt

    # The global TM projection changes when unrelated families gain schema
    # leaves.  A historical bounded result remains replayable only when every
    # used row binding, value, equation and authority field is still exact.
    # Normalize that one global ledger digest (and the identity derived from
    # it); any relevant schema or evidence drift remains visible and fails.
    compatible = canonical_clone_v1(rebuilt)
    compatible["input_refs"]["tm_schema_projection_sha256"] = persisted["input_refs"][
        "tm_schema_projection_sha256"
    ]
    material = canonical_clone_v1(compatible)
    material.pop("result_id")
    compatible["result_id"] = _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)
    if same_typed_json_v1(persisted, compatible):
        return persisted
    raise _error("verified investment-securities result does not replay exactly")


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review_blueprint()))
        return
    result = build_live_investment_securities_8bank_codex_verified_mapping_v1()
    if args.write_result:
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    _main()
