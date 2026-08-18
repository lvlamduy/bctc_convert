"""Verify annual-2025 cash-equivalent notes across eight bank reports.

This annual configuration reuses the shared bank-blind graph and numeric
challenger.  The only new structural variants are generic central-bank names,
one-edit OCR noise in the NHNN acronym, and wrapped interbank-term labels.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FORMAT_VERSION = "ANNUAL_2025_CASH_EQUIVALENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CASH_EQUIVALENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CASH_EQUIVALENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ce8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CASH_EQUIVALENTS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ce8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0147"
REVIEW_PATH = Path(
    "docs/experiments/E-0147-annual-2025-cash-equivalents-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0147-annual-2025-cash-equivalents-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "cefdsv1:scan:0e8514b256d4180323678e734bc13a5a316f9bd97cff19d020d09b56eac466b7"
EXPECTED_RESULT_ID: str | None = (
    "annual2025ce8bcv1:result:2d170cbc439b4e936dfa6c9a1938b492aa7b7daf361e8990fad47c381645bd68"
)
VARIANT_PROFILE = "GENERIC_CENTRAL_BANK_NAMES_AND_OCR_NOISE_V2"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_CASH_EQUIVALENTS_GRAPH_VISIBLE_PDF_PPOCRV6_OR_"
    "AUTHENTICATED_PIXEL_DASH_NUMERIC_CHALLENGER_ANNUAL_PERIOD_UNIT_"
    "PRINTED_TOTAL_EXACT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonicalization_or_export_authority": False,
    "cash_flow_or_policy_text_alone_used_as_mapping_evidence": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_cash_equivalent_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "visible_bound_dash_normalized_to_zero": True,
    "whole_pdf_uniqueness_replayed": True,
}

_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "only_visible_dash_interpreted_as_zero": True,
    "source_parent_and_children_double_counted": False,
    "unmapped_source_rows_retained": True,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}

_SCHEMA_EXPECTED = {
    1247: (
        "III. THÔNG TIN BỔ SUNG CHO MỘT SỐ KHOẢN MỤC TRÌNH BÀY TRONG LƯU CHUYỂN TIỀN TỆ",
        None,
        827,
    ),
    1248: ("Tiền và các khoản tương đương tiền", 1247, 828),
    1249: ("Tiền mặt và các khoản tương đương tiền tại quỹ", 1248, 829),
    1250: ("Tiền gửi tại NHNN", 1248, 830),
    1251: ("Tiền, ngoại hối gửi tại các TCTD khác", 1248, 831),
    1252: ("+ Không kỳ hạn", 1248, 832),
    1253: ("+ Có kỳ hạn không quá 3 tháng", 1248, 833),
    1254: (
        "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá 3 tháng kể từ ngày mua",
        1248,
        834,
    ),
}

_EXPECTED_PAGES = {
    "ACB": [73, 73],
    "MBB": [78, 78],
    "VPB": [73, 73],
    "HDB": [54, 54],
    "VCB": [64, 64],
    "CTG": [62, 62],
    "BID": [58, 58],
    "VIB": [50, 50],
}


class Annual2025CashEquivalents8BankError(ValueError):
    """The annual graph, pixels, numbers, equations, or schema drifted."""


def _error(message: str) -> Annual2025CashEquivalents8BankError:
    return Annual2025CashEquivalents8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_cash_equivalents_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_cash_equivalents_mapping_base_v1"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual cash-equivalents support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _both(
    base: ModuleType,
    page: int,
    current: tuple[int, str] | Mapping[str, Any],
    comparative: tuple[int, str] | Mapping[str, Any],
) -> dict[str, Any]:
    current_ref = base._line(page, *current) if type(current) is tuple else current
    comparative_ref = base._line(page, *comparative) if type(comparative) is tuple else comparative
    return {
        "COMPARATIVE_PERIOD": canonical_clone_v1(comparative_ref),
        "CURRENT_PERIOD": canonical_clone_v1(current_ref),
    }


def _mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    values: Mapping[str, Mapping[str, Any]],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return base._mapping(role, report_norm_id, page, labels, values, topology=topology)


def _equation(base: ModuleType, name: str, parent: str, terms: Sequence[str]) -> dict[str, Any]:
    return base._equation(name, parent, terms)


def _document(
    base: ModuleType,
    code: str,
    page: int,
    *,
    owner: Sequence[tuple[int, str]],
    graph_roles: Sequence[str],
    mappings: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    period_axis: Sequence[tuple[int, str]],
    units: Sequence[tuple[int, str]],
    presentation: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "equations": canonical_clone_v1(equations),
        "graph_roles": list(graph_roles),
        "mappings": canonical_clone_v1(mappings),
        "owner": [base._ref(page, line, text) for line, text in owner],
        "page_span": [page, page],
        "period_axis": [base._ref(page, line, text) for line, text in period_axis],
        "presentation": presentation,
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, line, text) for line, text in units],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    page = 73
    acb_dash = base._dash(
        page,
        [1299, 741, 1318, 754],
        "bc4df6609987d0292b9f6b153d215f7b51b3981d604640940b894fd495143abf",
    )
    docs.append(
        _document(
            base,
            "ACB",
            page,
            owner=[(5, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (23, "163.213.792"), (24, "139.824.608")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(10, "Tiền mặt, vàng bạc, đá quý")],
                    _both(base, page, (11, "8.624.548"), (12, "5.696.449")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(13, "Tiền gửi tại NHNN")],
                    _both(base, page, (14, "16.574.958"), (15, "25.219.753")),
                ),
                _mapping(
                    base,
                    "INTERBANK_GENERAL",
                    1251,
                    page,
                    [
                        (16, "Tiền gửi tại các TCTD khác (gồm tiền gửi không kỳ hạn và"),
                        (17, "tiền gửi có kỳ hạn không quá ba tháng)"),
                    ],
                    _both(base, page, (18, "138.014.286"), (19, "107.908.406")),
                ),
                _mapping(
                    base,
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (20, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá ba"),
                        (21, "tháng kể từ ngày mua"),
                    ],
                    _both(base, page, acb_dash, (22, "1.000.000")),
                    "VISIBLE_CURRENT_DASH_ZERO_AND_COMPARATIVE_VALUE",
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL", "SECURITIES"],
                )
            ],
            period_axis=[(6, "31.12.2025"), (7, "31.12.2024")],
            units=[(8, "Triệu VND"), (9, "Triệu VND")],
            presentation="COMBINED_INTERBANK_ROW_OPTIONAL_SECURITIES_AND_TRAILING_TOTAL",
        )
    )

    page = 78
    docs.append(
        _document(
            base,
            "MBB",
            page,
            owner=[(10, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (30, "239.259.989"), (31, "97.040.273")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(17, "Tiền mặt, vàng bạc, đá quý")],
                    _both(base, page, (18, "4.965.786"), (19, "3.349.166")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(20, "Tiền gửi tại Ngân hàng Nhà nước")],
                    _both(base, page, (21, "68.475.175"), (22, "29.803.270")),
                ),
                _mapping(
                    base,
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(23, "Tiền gửi không kỳ hạn tại các TCTD")],
                    _both(base, page, (24, "14.315.078"), (25, "11.260.009")),
                ),
                _mapping(
                    base,
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [(26, "Tiền gửi tại các TCTD khác có kỳ hạn không quá"), (27, "ba tháng")],
                    _both(base, page, (28, "151.503.950"), (29, "52.627.828")),
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM"],
                )
            ],
            period_axis=[(13, "31/12/2025"), (14, "31/12/2024")],
            units=[(15, "triệu đồng"), (16, "triệu đồng")],
            presentation="DEMAND_AND_WRAPPED_TERM_ROWS_THEN_TRAILING_TOTAL",
        )
    )

    page = 73
    vpb_dash = base._dash(
        page,
        [1458, 1435, 1478, 1451],
        "e39d38281e80b0063deac143275014596cff6ff07343fd6aba6c2af237cd3a53",
    )
    docs.append(
        _document(
            base,
            "VPB",
            page,
            owner=[(35, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (60, "196.097.219"), (61, "143.002.784")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(44, "Tiền mặt, vàng bạc, đá quý")],
                    _both(base, page, (45, "2.774.182"), (46, "2.148.289")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(47, "Tiền gửi tại Ngân hàng Nhà nước Việt Nam")],
                    _both(base, page, (48, "13.570.476"), (49, "14.327.215")),
                ),
                _mapping(
                    base,
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(50, "Tiền gửi thanh toán tại các TCTD khác")],
                    _both(base, page, (51, "12.195.493"), (52, "11.216.445")),
                ),
                _mapping(
                    base,
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [
                        (53, "Tiền gửi tại các TCTD khác có kỳ hạn không"),
                        (54, "quá ba tháng kể từ ngày gửi"),
                    ],
                    _both(base, page, (55, "165.860.746"), (56, "115.310.835")),
                ),
                _mapping(
                    base,
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (57, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn"),
                        (58, "không quá ba tháng kể từ ngày mua"),
                    ],
                    _both(base, page, (59, "1.696.322"), vpb_dash),
                    "CURRENT_VALUE_AND_VISIBLE_COMPARATIVE_DASH_ZERO",
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM", "SECURITIES"],
                )
            ],
            period_axis=[
                (38, "Ngày 31 tháng 12"),
                (40, "năm 2025"),
                (39, "Ngày 31 tháng 12"),
                (41, "năm 2024"),
            ],
            units=[(42, "Triệu đồng"), (43, "Triệu đồng")],
            presentation="DEMAND_WRAPPED_TERM_OPTIONAL_SECURITIES_AND_TRAILING_TOTAL",
        )
    )

    page = 54
    hdb_dash = base._dash(
        page,
        [1209, 677, 1227, 692],
        "90945acca58c02c217069eb411543249507552bb932b1f043e25a6671449893a",
    )
    docs.append(
        _document(
            base,
            "HDB",
            page,
            owner=[(8, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (30, "220.374.582"), (31, "137.261.526")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(15, "Tiền mặt, vàng")],
                    _both(base, page, (16, "4.126.643"), (17, "3.105.355")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(18, "Tiền gửi tại NHNN")],
                    _both(base, page, (19, "59.907.114"), (20, "26.680.270")),
                ),
                _mapping(
                    base,
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(21, "Tiền gửi thanh toán tại các TCTD khác")],
                    _both(base, page, (22, "31.362.169"), (23, "21.756.261")),
                ),
                _mapping(
                    base,
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [(24, "Tiền gửi tại các TCTD khác có kỳ hạn không quá 3 tháng")],
                    _both(base, page, (25, "124.978.656"), (26, "72.469.640")),
                ),
                _mapping(
                    base,
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (27, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không"),
                        (29, "quá 03 tháng kể từ ngày mua"),
                    ],
                    _both(base, page, hdb_dash, (28, "13.250.000")),
                    "VISIBLE_CURRENT_DASH_ZERO_AND_COMPARATIVE_VALUE",
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM", "SECURITIES"],
                )
            ],
            period_axis=[(11, "Số cuối năm"), (12, "Số đầu năm")],
            units=[(13, "Triệu VND"), (14, "Triệu VND")],
            presentation="ONE_EDIT_NHNN_OCR_VARIANT_DEMAND_TERM_SECURITIES_AND_TRAILING_TOTAL",
        )
    )

    page = 64
    docs.append(
        _document(
            base,
            "VCB",
            page,
            owner=[(8, "35. Tiền và các khoản tương đương tiền")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (24, "541.688.802"), (25, "430.614.185")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(13, "Tiền mặt, vàng bạc, đá quý")],
                    _both(base, page, (14, "15.542.769"), (15, "14.268.064")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(16, "Tiền gửi tại Ngân hàng Nhà nước")],
                    _both(base, page, (17, "37.445.504"), (18, "49.340.493")),
                ),
                _mapping(
                    base,
                    "INTERBANK_GENERAL",
                    1251,
                    page,
                    [
                        (19, "Tiền gửi tại và cho vay các TCTD khác với kỳ hạn gốc không"),
                        (21, "quá 3 tháng"),
                    ],
                    _both(base, page, (22, "488.700.529"), (23, "367.005.628")),
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
                )
            ],
            period_axis=[(9, "31/12/2025"), (10, "31/12/2024")],
            units=[(11, "Triệu VND"), (12, "Triệu VND")],
            presentation="COMBINED_INTERBANK_AND_LOAN_ROW_THEN_TRAILING_TOTAL",
        )
    )

    page = 62
    docs.append(
        _document(
            base,
            "CTG",
            page,
            owner=[(5, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
                "SECURITIES_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (27, "451.745.475"), (28, "373.319.556")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(10, "Tiền mặt và các khoản tương đương tiền tại quỹ")],
                    _both(base, page, (11, "12.583.484"), (12, "11.147.549")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(13, "Tiền gửi tại NHNN")],
                    _both(base, page, (14, "35.225.543"), (15, "34.431.657")),
                ),
                _mapping(
                    base,
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(16, "Tiền gửi không kỳ hạn tại các TCTD khác")],
                    _both(base, page, (17, "308.518.041"), (18, "243.465.753")),
                ),
                _mapping(
                    base,
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [(19, "Tiền gửi có kỳ hạn gốc không quá 3 tháng tại các TCTD khác")],
                    _both(base, page, (20, "95.235.407"), (21, "84.213.349")),
                ),
                _mapping(
                    base,
                    "SECURITIES",
                    1254,
                    page,
                    [
                        (23, "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá"),
                        (24, "3 tháng kể từ ngày mua"),
                    ],
                    _both(base, page, (25, "183.000"), (26, "61.248")),
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM", "SECURITIES"],
                )
            ],
            period_axis=[(6, "31.12.2025"), (7, "31.12.2024")],
            units=[(8, "Triệu đồng"), (9, "Triệu đồng")],
            presentation="DEMAND_TERM_SECURITIES_AND_TRAILING_TOTAL",
        )
    )

    page = 58
    docs.append(
        _document(
            base,
            "BID",
            page,
            owner=[(52, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=["INTERBANK_GENERAL", "CASH_AND_PRECIOUS_METALS", "CENTRAL_BANK_DEPOSIT"],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (76, "530.277.690"), (77, "324.724.464")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(61, "Tiền mặt, vàng bạc, đá quý")],
                    _both(base, page, (62, "13.075.066"), (63, "10.772.890")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(64, "Tiền gửi tại Ngân hàng Trung ương")],
                    _both(base, page, (65, "123.629.833"), (66, "92.341.029")),
                ),
                _mapping(
                    base,
                    "INTERBANK_GENERAL",
                    1251,
                    page,
                    [(67, "Tiền gửi tại các TCTD khác")],
                    _both(base, page, (68, "393.572.791"), (69, "221.610.545")),
                ),
                _mapping(
                    base,
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(70, "- Không kỳ hạn")],
                    _both(base, page, (71, "272.401.942"), (72, "140.061.497")),
                ),
                _mapping(
                    base,
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [(73, "- Có kỳ hạn không quá 3 tháng")],
                    _both(base, page, (74, "121.170.849"), (75, "81.549.048")),
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
                ),
                _equation(
                    base,
                    "INTERBANK_CHILDREN_EQUAL_INTERBANK_PARENT",
                    "INTERBANK_GENERAL",
                    ["INTERBANK_DEMAND", "INTERBANK_TERM"],
                ),
            ],
            period_axis=[(55, "Số cuối năm"), (56, "Số đầu năm")],
            units=[(58, "Triệu VND"), (59, "Triệu VND")],
            presentation="CENTRAL_BANK_SYNONYM_INTERBANK_PARENT_WITH_TWO_CHILDREN_AND_TRAILING_TOTAL",
        )
    )

    page = 50
    docs.append(
        _document(
            base,
            "VIB",
            page,
            owner=[(5, "TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN")],
            graph_roles=[
                "INTERBANK_GENERAL",
                "CASH_AND_PRECIOUS_METALS",
                "CENTRAL_BANK_DEPOSIT",
                "INTERBANK_DEMAND",
                "INTERBANK_TERM_UP_TO_3_MONTHS",
            ],
            mappings=[
                _mapping(
                    base,
                    "TOTAL",
                    1248,
                    page,
                    [],
                    _both(base, page, (23, "72.020.182"), (24, "61.395.986")),
                    "TRAILING_UNLABELED_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "CASH",
                    1249,
                    page,
                    [(10, "Tiền mặt và vàng")],
                    _both(base, page, (11, "3.552.574"), (12, "1.639.368")),
                ),
                _mapping(
                    base,
                    "CENTRAL_BANK",
                    1250,
                    page,
                    [(13, "Tiền gửi tại NHNN")],
                    _both(base, page, (14, "8.998.068"), (15, "9.909.074")),
                ),
                _mapping(
                    base,
                    "INTERBANK_DEMAND",
                    1252,
                    page,
                    [(16, "Tiền gửi không kỳ hạn tại các TCTD khác")],
                    _both(base, page, (17, "1.349.247"), (18, "947.544")),
                ),
                _mapping(
                    base,
                    "INTERBANK_TERM",
                    1253,
                    page,
                    [
                        (19, "Tiền gửi có kỳ hạn tại các TCTD khác với kỳ hạn"),
                        (22, "không quá 3 tháng"),
                    ],
                    _both(base, page, (20, "58.120.293"), (21, "48.900.000")),
                ),
            ],
            equations=[
                _equation(
                    base,
                    "COMPONENTS_EQUAL_TOTAL",
                    "TOTAL",
                    ["CASH", "CENTRAL_BANK", "INTERBANK_DEMAND", "INTERBANK_TERM"],
                )
            ],
            period_axis=[(6, "31/12/2025"), (7, "31/12/2024")],
            units=[(8, "triệu đồng"), (9, "triệu đồng")],
            presentation="DEMAND_AND_WRAPPED_TERM_ROWS_THEN_TRAILING_TOTAL",
        )
    )

    expected = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
    if [item["bank_code"] for item in docs] != expected:
        raise _error("annual cash-equivalents review document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.VARIANT_PROFILE = VARIANT_PROFILE
    base.FAMILY_END_DISPLAY_ORDER = 834
    base.SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
    }
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.EXPECTED_RESULT_ID = EXPECTED_RESULT_ID
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._review_documents = lambda: _review_documents(base)
    return base


def build_annual_2025_cash_equivalents_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_cash_equivalents_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        return _base().build_live_cash_equivalents_8bank_codex_verified_mapping_v1()
    except Annual2025CashEquivalents8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_cash_equivalents_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _base().validate_live_cash_equivalents_8bank_codex_verified_mapping_v1(value)
    except Annual2025CashEquivalents8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if sum((args.write_review, args.write_result, args.verify)) != 1:
        parser.error("choose exactly one action")
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(build_annual_2025_cash_equivalents_pixel_review_blueprint_v1())
        )
        return 0
    if args.write_result:
        result = build_live_annual_2025_cash_equivalents_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    result, _ = _base()._stable_json(RESULT_PATH)
    verified = validate_annual_2025_cash_equivalents_8bank_codex_verified_mapping_replay_v1(result)
    print(verified["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
