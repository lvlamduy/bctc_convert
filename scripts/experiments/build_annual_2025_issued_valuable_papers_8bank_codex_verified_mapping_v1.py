"""Verify annual-2025 issued valuable papers across the fixed eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_ISSUED_VALUABLE_PAPERS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_ISSUED_VALUABLE_PAPERS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_ISSUED_VALUABLE_PAPERS_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ivp8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_ISSUED_VALUABLE_PAPERS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ivp8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0131"
REVIEW_PATH = Path(
    "docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-"
    "verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "ivpfdsv1:scan:8775a2364e34ca06b0e5c2efae787fb497cc26fc0621b3080baae09658171297"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_ISSUED_VALUABLE_PAPERS_OWNER_INSTRUMENT_TENOR_OPTIONAL_"
    "VALUATION_PERIOD_UNIT_ADJACENT_CONTINUATION_VISIBLE_PIXEL_UPSTREAM_"
    "PPOCRV6_DASH_ZERO_ACCOUNTING_PROJECT_OWNER_APPROVED_INCLUSIVE_AND_BROAD_"
    "TENORS_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_PRECEDES_INSTRUMENT_AND_TENOR_CHILDREN",
    "PAIR_FIRST_GENERIC_VARIANT_GRAPH",
    "OPTIONAL_INSTRUMENT_VALUATION_CURRENCY_AND_CONTINUATION_BRANCHES",
    "CURRENT_2025_AND_COMPARATIVE_2024_AXES",
    "VISIBLE_LOCAL_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_OR_AUTHENTICATED_PIXEL_DASH_NUMERIC_CHALLENGER",
    "INCLUSIVE_EXACT_FIVE_YEAR_AND_PRINTED_BROAD_TENOR_SEMANTICS",
    "INSTRUMENT_TENOR_AND_PRINTED_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_PPOCRV6_AND_ACCOUNTING",
    "reporting_period_dates_derived_from_pdf": True,
    "source_rows_without_instrument_specific_scope_retained_unresolved": True,
    "visible_bound_dash_normalized_to_zero": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_upstream_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_issued_paper_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_dates_derived_from_pdf": True,
    "text_similarity_alone_used_for_mapping": False,
}
_SCHEMA_EXPECTED = {
    6009: ("Trên 12 tháng", 1101, 616),
    6010: ("Dưới 5 năm", 1109, 627),
    1100: ("Phát hành giấy tờ có giá", 560, 611),
    1101: ("Chứng chỉ tiền gửi", 1100, 612),
    1102: ("Dưới 12 tháng", 1101, 617),
    1103: ("Từ 12 tháng đến 5 năm", 1101, 618),
    1104: ("Trên 5 năm", 1101, 619),
    1105: ("Kỳ phiếu", 1100, 620),
    1106: ("Dưới 12 tháng", 1105, 621),
    1107: ("Từ 12 tháng đến 5 năm", 1105, 622),
    1108: ("Trên 5 năm", 1105, 623),
    1109: ("Trái phiếu", 1100, 624),
    1110: ("Dưới 12 tháng", 1109, 628),
    1111: ("Từ 12 tháng đến 5 năm", 1109, 629),
    1112: ("Trên 5 năm", 1109, 630),
    1113: ("Tổng kỳ phiếu và trái phiếu", 1100, 631),
    1114: ("Dưới 12 tháng", 1113, 632),
    1115: ("Từ 12 tháng đến 5 năm", 1113, 633),
    1116: ("Trên 5 năm", 1113, 634),
    1117: (
        "Các loại giấy tờ có giá khác (bao gồm trái phiếu tăng vốn)",
        1100,
        635,
    ),
}
_EXPECTED_IDS = {
    "ACB": {1100, 1101, 1102, 1103, 1109, 1111, 1112},
    "MBB": {1100, 1101, 1102, 6009, 1109, 6010, 1112},
    "VPB": {1100, 1101, 1109},
    "HDB": {1100, 1101, 1102, 1103, 1104, 1109, 1111, 1112},
    "VCB": {1100, 1101, 1102, 1103, 1104, 1113, 1114, 1115, 1116},
    "CTG": {
        1100,
        1101,
        1102,
        1103,
        1104,
        1105,
        1106,
        1107,
        1108,
        1109,
        1110,
        1111,
        1112,
        1113,
        1114,
        1115,
        1116,
    },
    "BID": {1100, 1101, 1102, 1103, 1104, 1105, 1106, 1107, 1109, 1111, 1112, 1117},
    "VIB": {1100, 1101, 1103, 1104, 1109, 1111, 1112},
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 34,
    "authenticated_pixel_dash_zero_count": 11,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 70,
    "open_source_row_count": 5,
    "q1_source_period_caveat_document_count": 0,
    "verified_document_count": 8,
    "verified_value_cell_count": 188,
}
_EXPECTED_OPEN_IDS = {
    "ACB": set(),
    "MBB": set(),
    "VPB": {
        "VPB-WHOLE-FAMILY-SHORT",
        "VPB-WHOLE-FAMILY-MEDIUM",
        "VPB-WHOLE-FAMILY-LONG",
    },
    "HDB": {"HDB-ISSUANCE-COST-CONTRA"},
    "VCB": {"VCB-COMBINED-MEDIUM-LONG-FOREIGN-CURRENCY"},
    "CTG": set(),
    "BID": set(),
    "VIB": set(),
}


class Annual2025IssuedValuablePapers8BankError(ValueError):
    """Annual issued-paper evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025IssuedValuablePapers8BankError:
    return Annual2025IssuedValuablePapers8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_issued_valuable_papers_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location("annual_2025_issued_papers_base", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load issued-paper support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    label, line = base._label, base._line

    def mapping(
        schema_id: int,
        role: str,
        labels: Sequence[dict[str, Any]],
        current: Sequence[dict[str, Any]],
        comparative: Sequence[dict[str, Any]],
        topology: str,
    ) -> dict[str, Any]:
        values = {}
        if current:
            values["CURRENT"] = list(current)
        if comparative:
            values["COMPARATIVE"] = list(comparative)
        return base._mapping(schema_id, role, labels, values, topology)

    def unresolved(
        item_id: str,
        labels: Sequence[dict[str, Any]],
        current: Sequence[dict[str, Any]],
        comparative: Sequence[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        values = {}
        if current:
            values["CURRENT"] = list(current)
        if comparative:
            values["COMPARATIVE"] = list(comparative)
        return base._unmapped(item_id, labels, values, reason)

    def doc(
        code: str,
        page: int,
        owner_line: int,
        owner_text: str,
        periods: Sequence[dict[str, Any]],
        units: Sequence[dict[str, Any]],
        mappings: Sequence[dict[str, Any]],
        equations: Sequence[dict[str, Any]],
        unmapped: Sequence[dict[str, Any]] = (),
        *,
        presentation: str,
        page_span: Sequence[int] | None = None,
    ) -> dict[str, Any]:
        result = base._doc(
            code,
            page,
            owner_line,
            owner_text,
            periods,
            units,
            mappings,
            equations,
            unmapped,
            source_period="2025-12-31",
            presentation=presentation,
        )
        if page_span is not None:
            result["page_span"] = list(page_span)
        return result

    acb = doc(
        "ACB",
        63,
        31,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [
            label(63, 32, "31.12.2025"),
            label(63, 33, "Giá trị ghi sổ"),
            label(63, 65, "31.12.2024"),
            label(63, 66, "Giá trị ghi sổ"),
        ],
        [label(63, 35, "Triệu VND"), label(63, 68, "Triệu VND")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(63, 31, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                [line(63, 63, "133.294.422")],
                [line(63, 91, "101.650.446")],
                "PRINTED_BOOK_VALUE_TOTAL",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [label(63, 50, "Chứng chỉ tiền gửi"), label(63, 85, "Chứng chỉ tiền gửi")],
                [
                    line(63, 52, "73.249.767"),
                    line(63, 55, "5.400.000"),
                    line(63, 58, "290.000"),
                    line(63, 61, "2.000.000"),
                ],
                [line(63, 88, "55.950.000")],
                "SUM_OF_VISIBLE_TENOR_ROWS",
            ),
            mapping(
                1102,
                "CD_SHORT",
                [
                    label(63, 50, "Chứng chỉ tiền gửi"),
                    label(63, 51, "Chứng chỉ tiền gửi kỳ hạn dưới một năm"),
                ],
                [line(63, 52, "73.249.767")],
                [line(63, 88, "55.950.000")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1103,
                "CD_INCLUSIVE_ONE_TO_FIVE_YEARS",
                [
                    label(63, 50, "Chứng chỉ tiền gửi"),
                    label(63, 54, "Chứng chỉ tiền gửi kỳ hạn từ một năm đến hai năm"),
                    label(63, 57, "Chứng chỉ tiền gửi kỳ hạn ba năm"),
                    label(63, 60, "Chứng chỉ tiền gửi kỳ hạn năm năm"),
                ],
                [line(63, 55, "5.400.000"), line(63, 58, "290.000"), line(63, 61, "2.000.000")],
                [],
                "PROJECT_OWNER_APPROVED_INCLUSIVE_EXACT_FIVE_YEAR_TENOR",
            ),
            mapping(
                1109,
                "BOND",
                [label(63, 37, "Trái phiếu"), label(63, 70, "Trái phiếu")],
                [
                    line(63, 39, "39.849.045"),
                    line(63, 42, "5.369.637"),
                    line(63, 45, "4.715.768"),
                    line(63, 48, "2.420.205"),
                ],
                [
                    line(63, 72, "37.399.160"),
                    line(63, 75, "2.069.789"),
                    line(63, 79, "3.814.587"),
                    line(63, 82, "2.416.910"),
                ],
                "SUM_OF_VISIBLE_TENOR_ROWS",
            ),
            mapping(
                1111,
                "BOND_INCLUSIVE_ONE_TO_FIVE_YEARS",
                [
                    label(63, 37, "Trái phiếu"),
                    label(63, 38, "Trái phiếu kỳ hạn từ một năm đến hai năm"),
                    label(63, 41, "Trái phiếu kỳ hạn ba năm"),
                    label(63, 44, "Trái phiếu kỳ hạn năm năm"),
                ],
                [line(63, 39, "39.849.045"), line(63, 42, "5.369.637"), line(63, 45, "4.715.768")],
                [line(63, 72, "37.399.160"), line(63, 75, "2.069.789"), line(63, 79, "3.814.587")],
                "PROJECT_OWNER_APPROVED_INCLUSIVE_EXACT_FIVE_YEAR_TENOR",
            ),
            mapping(
                1112,
                "BOND_LONG",
                [label(63, 37, "Trái phiếu"), label(63, 47, "Trái phiếu kỳ hạn mười năm")],
                [line(63, 48, "2.420.205")],
                [line(63, 82, "2.416.910")],
                "INSTRUMENT_CONTEXT_PLUS_LONG_TENOR",
            ),
        ],
        [
            base._equation(
                "ALL_VISIBLE_BOOK_VALUE_ROWS_TO_TOTAL",
                "CURRENT",
                [
                    line(63, i, text)
                    for i, text in [
                        (39, "39.849.045"),
                        (42, "5.369.637"),
                        (45, "4.715.768"),
                        (48, "2.420.205"),
                        (52, "73.249.767"),
                        (55, "5.400.000"),
                        (58, "290.000"),
                        (61, "2.000.000"),
                    ]
                ],
                line(63, 63, "133.294.422"),
            ),
            base._equation(
                "ALL_VISIBLE_BOOK_VALUE_ROWS_TO_TOTAL",
                "COMPARATIVE",
                [
                    line(63, i, text)
                    for i, text in [
                        (72, "37.399.160"),
                        (75, "2.069.789"),
                        (79, "3.814.587"),
                        (82, "2.416.910"),
                        (88, "55.950.000"),
                    ]
                ],
                line(63, 91, "101.650.446"),
            ),
        ],
        presentation="STACKED_PERIOD_BLOCKS_WITH_BOOK_VALUE_AND_FACE_VALUE_LANES",
    )

    mbb = doc(
        "MBB",
        66,
        65,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [label(66, 67, "31/12/2025"), label(66, 68, "31/12/2024")],
        [label(66, 69, "triệu đồng"), label(66, 70, "triệu đồng")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(66, 65, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                [line(66, 89, "187.236.104")],
                [line(66, 90, "128.964.033")],
                "UNLABELED_TOTAL_AFTER_INSTRUMENTS",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [label(66, 80, "Chứng chỉ tiền gửi bằng VND")],
                [line(66, 81, "140.830.150")],
                [line(66, 82, "91.492.561")],
                "OWNER_INSTRUMENT_PARENT",
            ),
            mapping(
                1102,
                "CD_SHORT",
                [label(66, 80, "Chứng chỉ tiền gửi bằng VND"), label(66, 83, "Dưới 12 tháng")],
                [line(66, 84, "76.253.073")],
                [line(66, 85, "66.520.415")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                6009,
                "CD_PRINTED_OVER_TWELVE_MONTHS",
                [label(66, 80, "Chứng chỉ tiền gửi bằng VND"), label(66, 86, "Trên 12 tháng")],
                [line(66, 87, "64.577.077")],
                [line(66, 88, "24.972.146")],
                "PRINTED_BROAD_TENOR_NOT_ARTIFICIALLY_SPLIT",
            ),
            mapping(
                1109,
                "BOND",
                [label(66, 71, "Trái phiếu bằng VND")],
                [line(66, 72, "46.405.954")],
                [line(66, 73, "37.471.472")],
                "OWNER_INSTRUMENT_PARENT",
            ),
            mapping(
                6010,
                "BOND_PRINTED_BELOW_FIVE_YEARS",
                [label(66, 71, "Trái phiếu bằng VND"), label(66, 74, "Dưới 5 năm")],
                [line(66, 75, "23.039.165")],
                [line(66, 76, "20.836.457")],
                "PRINTED_BROAD_TENOR_NOT_ARTIFICIALLY_SPLIT",
            ),
            mapping(
                1112,
                "BOND_OVER_FIVE_YEARS",
                [label(66, 71, "Trái phiếu bằng VND"), label(66, 77, "Trên 5 năm")],
                [line(66, 78, "23.366.789")],
                [line(66, 79, "16.635.015")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
        ],
        [
            base._equation(
                "BOND_TENORS_TO_PARENT", role, [line(66, a, x), line(66, b, y)], line(66, c, z)
            )
            for role, a, x, b, y, c, z in [
                ("CURRENT", 75, "23.039.165", 78, "23.366.789", 72, "46.405.954"),
                ("COMPARATIVE", 76, "20.836.457", 79, "16.635.015", 73, "37.471.472"),
            ]
        ]
        + [
            base._equation(
                "CD_TENORS_TO_PARENT", role, [line(66, a, x), line(66, b, y)], line(66, c, z)
            )
            for role, a, x, b, y, c, z in [
                ("CURRENT", 84, "76.253.073", 87, "64.577.077", 81, "140.830.150"),
                ("COMPARATIVE", 85, "66.520.415", 88, "24.972.146", 82, "91.492.561"),
            ]
        ]
        + [
            base._equation(
                "INSTRUMENTS_TO_TOTAL", role, [line(66, a, x), line(66, b, y)], line(66, c, z)
            )
            for role, a, x, b, y, c, z in [
                ("CURRENT", 72, "46.405.954", 81, "140.830.150", 89, "187.236.104"),
                ("COMPARATIVE", 73, "37.471.472", 82, "91.492.561", 90, "128.964.033"),
            ]
        ],
        presentation="TWO_PERIOD_VERTICAL_INSTRUMENT_AND_BROAD_TENOR_ROWS",
    )

    vpb = doc(
        "VPB",
        62,
        20,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [
            label(62, 22, "Ngày 31 tháng 12"),
            label(62, 24, "năm 2025"),
            label(62, 23, "Ngày 31 tháng 12"),
            label(62, 25, "năm 2024"),
        ],
        [label(62, 26, "Triệu đồng"), label(62, 27, "Triệu đồng")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(62, 20, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                [line(62, 58, "107.120.653")],
                [line(62, 59, "66.975.704")],
                "PRINTED_TOTAL_AFTER_INSTRUMENT_ROWS",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [
                    label(62, 48, "Chứng chỉ tiền gửi phát hành cho khách hàng cá nhân"),
                    label(62, 51, "Chứng chỉ tiền gửi phát hành cho các tổ chức kinh tế"),
                ],
                [line(62, 50, "26.306.000"), line(62, 53, "37.156.844")],
                [line(62, 54, "62.016.478")],
                "SUM_OF_VISIBLE_CUSTOMER_TYPE_ROWS",
            ),
            mapping(
                1109,
                "BOND",
                [label(62, 55, "Trái phiếu (*)")],
                [line(62, 56, "43.657.809")],
                [line(62, 57, "4.959.226")],
                "OWNER_INSTRUMENT_PARENT",
            ),
        ],
        [
            base._equation(
                "INSTRUMENTS_TO_TOTAL",
                "CURRENT",
                [
                    line(62, 50, "26.306.000"),
                    line(62, 53, "37.156.844"),
                    line(62, 56, "43.657.809"),
                ],
                line(62, 58, "107.120.653"),
            ),
            base._equation(
                "INSTRUMENTS_TO_TOTAL",
                "COMPARATIVE",
                [line(62, 54, "62.016.478"), line(62, 57, "4.959.226")],
                line(62, 59, "66.975.704"),
            ),
        ],
        [
            unresolved(
                "VPB-WHOLE-FAMILY-SHORT",
                [label(62, 28, "Dưới 12 tháng")],
                [line(62, 29, "25.699.521")],
                [line(62, 30, "53.256.694")],
                "WHOLE_FAMILY_TENOR_AXIS_IS_NOT_INSTRUMENT_SPECIFIC",
            ),
            unresolved(
                "VPB-WHOLE-FAMILY-MEDIUM",
                [label(62, 31, "Từ 12 tháng đến dưới 5 năm")],
                [line(62, 32, "72.134.379")],
                [line(62, 33, "12.723.428")],
                "WHOLE_FAMILY_TENOR_AXIS_IS_NOT_INSTRUMENT_SPECIFIC",
            ),
            unresolved(
                "VPB-WHOLE-FAMILY-LONG",
                [label(62, 34, "Từ 5 năm trở lên")],
                [line(62, 35, "9.286.753")],
                [line(62, 36, "995.582")],
                "WHOLE_FAMILY_TENOR_AXIS_IS_NOT_INSTRUMENT_SPECIFIC",
            ),
        ],
        presentation="PARALLEL_WHOLE_FAMILY_TENOR_AND_INSTRUMENT_TABLES",
    )

    hdb = doc(
        "HDB",
        46,
        8,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [label(46, 9, "Số cuối năm"), label(46, 10, "Số đầu năm")],
        [label(46, 11, "Triệu VND"), label(46, 12, "Triệu VND")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(46, 8, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                [line(46, 45, "87.434.265")],
                [line(46, 46, "81.349.744")],
                "NET_CARRYING_VALUE_AFTER_ISSUANCE_COST",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [
                    label(46, 16, "Mệnh giá chứng chỉ tiền gửi bằng VND"),
                    label(46, 22, "Mệnh giá chứng chỉ tiền gửi bằng VND"),
                    label(46, 33, "Mệnh giá chứng chỉ tiền gửi bằng VND"),
                ],
                [line(46, 17, "18.710.000"), line(46, 23, "6.047.000"), line(46, 34, "215.000")],
                [line(46, 18, "11.705.000"), line(46, 24, "12.756.000"), line(46, 35, "80.000")],
                "SUM_OF_VISIBLE_TENOR_ROWS",
            ),
            mapping(
                1102,
                "CD_SHORT",
                [
                    label(46, 13, "Dưới 12 tháng"),
                    label(46, 16, "Mệnh giá chứng chỉ tiền gửi bằng VND"),
                ],
                [line(46, 17, "18.710.000")],
                [line(46, 18, "11.705.000")],
                "TENOR_CONTEXT_PLUS_INSTRUMENT_ROW",
            ),
            mapping(
                1103,
                "CD_MEDIUM",
                [
                    label(46, 19, "Từ 12 tháng đến dưới 5 năm"),
                    label(46, 22, "Mệnh giá chứng chỉ tiền gửi bằng VND"),
                ],
                [line(46, 23, "6.047.000")],
                [line(46, 24, "12.756.000")],
                "TENOR_CONTEXT_PLUS_INSTRUMENT_ROW",
            ),
            mapping(
                1104,
                "CD_LONG",
                [
                    label(46, 30, "Từ 05 năm trở lên"),
                    label(46, 33, "Mệnh giá chứng chỉ tiền gửi bằng VND"),
                ],
                [line(46, 34, "215.000")],
                [line(46, 35, "80.000")],
                "TENOR_CONTEXT_PLUS_INSTRUMENT_ROW",
            ),
            mapping(
                1109,
                "BOND",
                [
                    label(46, 25, "Mệnh giá trái phiếu bằng VND"),
                    label(46, 28, "Mệnh giá trái phiếu bằng USD (*)"),
                    label(46, 36, "Mệnh giá trái phiếu bằng VND"),
                    label(46, 39, "Mệnh giá trái phiếu chuyển đổi bằng USD (**)"),
                ],
                [
                    line(46, 26, "15.630.000"),
                    line(46, 29, "2.624.400"),
                    line(46, 37, "39.952.600"),
                    line(46, 40, "4.330.260"),
                ],
                [line(46, 27, "16.550.000"), line(46, 38, "32.031.000"), line(46, 41, "8.263.450")],
                "SUM_OF_VISIBLE_TENOR_AND_CURRENCY_ROWS",
            ),
            mapping(
                1111,
                "BOND_MEDIUM",
                [
                    label(46, 19, "Từ 12 tháng đến dưới 5 năm"),
                    label(46, 25, "Mệnh giá trái phiếu bằng VND"),
                    label(46, 28, "Mệnh giá trái phiếu bằng USD (*)"),
                ],
                [line(46, 26, "15.630.000"), line(46, 29, "2.624.400")],
                [line(46, 27, "16.550.000")],
                "TENOR_CONTEXT_PLUS_CURRENCY_ROWS",
            ),
            mapping(
                1112,
                "BOND_LONG",
                [
                    label(46, 30, "Từ 05 năm trở lên"),
                    label(46, 36, "Mệnh giá trái phiếu bằng VND"),
                    label(46, 39, "Mệnh giá trái phiếu chuyển đổi bằng USD (**)"),
                ],
                [line(46, 37, "39.952.600"), line(46, 40, "4.330.260")],
                [line(46, 38, "32.031.000"), line(46, 41, "8.263.450")],
                "TENOR_CONTEXT_PLUS_CURRENCY_ROWS",
            ),
        ],
        [
            base._equation(
                "GROSS_INSTRUMENT_ROWS_LESS_ISSUANCE_COST_TO_NET_TOTAL",
                "CURRENT",
                [
                    line(46, 17, "18.710.000"),
                    line(46, 23, "6.047.000"),
                    line(46, 26, "15.630.000"),
                    line(46, 29, "2.624.400"),
                    line(46, 34, "215.000"),
                    line(46, 37, "39.952.600"),
                    line(46, 40, "4.330.260"),
                    line(46, 43, "(74.995)"),
                ],
                line(46, 45, "87.434.265"),
            ),
            base._equation(
                "GROSS_INSTRUMENT_ROWS_LESS_ISSUANCE_COST_TO_NET_TOTAL",
                "COMPARATIVE",
                [
                    line(46, 18, "11.705.000"),
                    line(46, 24, "12.756.000"),
                    line(46, 27, "16.550.000"),
                    line(46, 35, "80.000"),
                    line(46, 38, "32.031.000"),
                    line(46, 41, "8.263.450"),
                    line(46, 44, "(35.706)"),
                ],
                line(46, 46, "81.349.744"),
            ),
        ],
        [
            unresolved(
                "HDB-ISSUANCE-COST-CONTRA",
                [label(46, 42, "Chi phí phát hành")],
                [line(46, 43, "(74.995)")],
                [line(46, 44, "(35.706)")],
                "ISSUANCE_COST_CONTRA_ROW_HAS_NO_DEDICATED_SCHEMA_LEAF",
            )
        ],
        presentation="TENOR_PARENT_WITH_INSTRUMENT_AND_CURRENCY_CHILDREN_PLUS_NET_COST",
    )

    vcb = doc(
        "VCB",
        54,
        8,
        "20. Phát hành giấy tờ có giá",
        [label(54, 9, "31/12/2025"), label(54, 10, "31/12/2024")],
        [label(54, 11, "Triệu VND"), label(54, 12, "Triệu VND")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(54, 8, "20. Phát hành giấy tờ có giá")],
                [line(54, 44, "27.101.221")],
                [line(54, 45, "24.125.059")],
                "UNLABELED_TOTAL_AFTER_INSTRUMENTS",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [label(54, 13, "Chứng chỉ tiền gửi")],
                [line(54, 14, "17.596.115")],
                [line(54, 15, "14.520.115")],
                "OWNER_INSTRUMENT_PARENT",
            ),
            mapping(
                1102,
                "CD_SHORT",
                [label(54, 13, "Chứng chỉ tiền gửi"), label(54, 17, "Ngắn hạn bằng VND")],
                [line(54, 18, "17.096.000")],
                [line(54, 19, "14.520.000")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1103,
                "CD_MEDIUM",
                [label(54, 13, "Chứng chỉ tiền gửi"), label(54, 20, "Trung hạn bằng VND")],
                [line(54, 21, "115")],
                [line(54, 22, "115")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1104,
                "CD_LONG",
                [label(54, 13, "Chứng chỉ tiền gửi"), label(54, 23, "Dài hạn bằng VND")],
                [line(54, 24, "500.000")],
                [],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1113,
                "PROMISSORY_AND_BOND_TOTAL",
                [label(54, 26, "Kỳ phiếu, trái phiếu")],
                [line(54, 27, "9.505.106")],
                [line(54, 28, "9.604.944")],
                "PRINTED_COMBINED_INSTRUMENT_PARENT",
            ),
            mapping(
                1114,
                "PROMISSORY_AND_BOND_SHORT",
                [
                    label(54, 26, "Kỳ phiếu, trái phiếu"),
                    label(54, 29, "Ngắn hạn bằng VND"),
                    label(54, 32, "Ngắn hạn bằng ngoại tệ"),
                ],
                [line(54, 30, "47"), line(54, 33, "35")],
                [line(54, 31, "47"), line(54, 34, "31")],
                "COMBINED_INSTRUMENT_TENOR_PLUS_CURRENCY",
            ),
            mapping(
                1115,
                "PROMISSORY_AND_BOND_MEDIUM",
                [label(54, 26, "Kỳ phiếu, trái phiếu"), label(54, 35, "Trung hạn bằng VND")],
                [line(54, 36, "4.000.000")],
                [line(54, 37, "2.000.000")],
                "COMBINED_INSTRUMENT_TENOR",
            ),
            mapping(
                1116,
                "PROMISSORY_AND_BOND_LONG",
                [label(54, 26, "Kỳ phiếu, trái phiếu"), label(54, 41, "Dài hạn bằng VND")],
                [line(54, 42, "5.505.010")],
                [line(54, 43, "7.604.852")],
                "COMBINED_INSTRUMENT_TENOR",
            ),
        ],
        [
            base._equation(
                "CD_TENORS_TO_PARENT",
                "CURRENT",
                [line(54, 18, "17.096.000"), line(54, 21, "115"), line(54, 24, "500.000")],
                line(54, 14, "17.596.115"),
            ),
            base._equation(
                "CD_TENORS_TO_PARENT",
                "COMPARATIVE",
                [line(54, 19, "14.520.000"), line(54, 22, "115")],
                line(54, 15, "14.520.115"),
            ),
            base._equation(
                "COMBINED_TENOR_CURRENCY_ROWS_TO_PARENT",
                "CURRENT",
                [
                    line(54, 30, "47"),
                    line(54, 33, "35"),
                    line(54, 36, "4.000.000"),
                    line(54, 39, "14"),
                    line(54, 42, "5.505.010"),
                ],
                line(54, 27, "9.505.106"),
            ),
            base._equation(
                "COMBINED_TENOR_CURRENCY_ROWS_TO_PARENT",
                "COMPARATIVE",
                [
                    line(54, 31, "47"),
                    line(54, 34, "31"),
                    line(54, 37, "2.000.000"),
                    line(54, 40, "14"),
                    line(54, 43, "7.604.852"),
                ],
                line(54, 28, "9.604.944"),
            ),
            base._equation(
                "INSTRUMENTS_TO_TOTAL",
                "CURRENT",
                [line(54, 14, "17.596.115"), line(54, 27, "9.505.106")],
                line(54, 44, "27.101.221"),
            ),
            base._equation(
                "INSTRUMENTS_TO_TOTAL",
                "COMPARATIVE",
                [line(54, 15, "14.520.115"), line(54, 28, "9.604.944")],
                line(54, 45, "24.125.059"),
            ),
        ],
        [
            unresolved(
                "VCB-COMBINED-MEDIUM-LONG-FOREIGN-CURRENCY",
                [label(54, 38, "Trung, dài hạn bằng ngoại tệ")],
                [line(54, 39, "14")],
                [line(54, 40, "14")],
                "ONE_SOURCE_ROW_COMBINES_MEDIUM_AND_LONG_TENORS_WITHOUT_ALLOCATION",
            )
        ],
        presentation="TWO_PERIOD_INSTRUMENT_PARENT_WITH_CURRENCY_TENOR_CHILDREN",
    )

    ctg_current_ky_medium = base._dash(
        53,
        [700, 1405, 747, 1445],
        "18a5e475b6a425bd5519ea7d204bb9ebacc4145a0377f72d2f13c109627fcd0b",
    )
    ctg_current_ky_long = base._dash(
        53,
        [700, 1535, 747, 1575],
        "e88c458e1bc5b2a284c57d5520a7f9e18b6b469550e277cfd989ab39cd78d373",
    )
    ctg_current_bond_short_anon = base._dash(
        53,
        [880, 1275, 922, 1320],
        "e3696c0ea0897e207b6f7d11ad3e57cbbaa76198818b7bf76b8bfc2c0c40db58",
    )
    ctg_current_bond_short_registered = base._dash(
        53,
        [1080, 1275, 1124, 1320],
        "abaf9f325024363382677da0bc30551850ee7500061da0c32ea3e336338489f4",
    )
    ctg_current_cd_long = base._dash(
        53,
        [1280, 1535, 1323, 1575],
        "d6149ec1c009d84c56aefd2be7c91e981bf683acc59f7c7f7887dc2e8dfeb60a",
    )
    ctg_comparative_ky_medium = base._dash(
        54,
        [728, 575, 772, 620],
        "ecd2d3d3dd2b80ec4b2d3179c19af2c5cdb9500631d49fba73427d8869dee812",
    )
    ctg_comparative_ky_long = base._dash(
        54,
        [728, 705, 774, 748],
        "be6fba33fb73028723a0540ffa33a350c70870ee63dbe06e9e692a4d2eea8879",
    )
    ctg_comparative_bond_short_anon = base._dash(
        54,
        [900, 445, 944, 493],
        "311f9a242903b1e08bab6d5630ef2bcbb0c3e6a4765b6c9361684ba7b806e7e1",
    )
    ctg_comparative_bond_short_registered = base._dash(
        54,
        [1090, 445, 1134, 493],
        "a44cbadda48e3d5ee520065bdaa8cf902b218754b2f51a5a1cfa38d07aac311a",
    )
    ctg_comparative_cd_long = base._dash(
        54,
        [1280, 705, 1324, 748],
        "276988da27b09e7de04a4370d51bb3e557707c190007d03ff429fc898dd5bbc1",
    )
    ctg = doc(
        "CTG",
        53,
        20,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [label(53, 21, "31.12.2025"), label(53, 43, "31.12.2025"), label(54, 6, "31.12.2024")],
        [label(53, 23, "Triệu đồng"), label(53, 52, "Triệu đồng"), label(54, 15, "Triệu đồng")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [
                    label(53, 20, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ"),
                    label(54, 5, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ (TIẾP THEO)"),
                ],
                [line(53, 40, "174.030.352")],
                [line(54, 65, "151.678.090")],
                "PRINTED_CARRYING_VALUE_TOTAL_ACROSS_ADJACENT_PERIOD_PAGES",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [label(53, 46, "Chứng chỉ tiền gửi"), label(54, 9, "Chứng chỉ tiền gửi")],
                [line(53, 100, "120.530.393")],
                [line(54, 64, "104.500.671")],
                "INSTRUMENT_COLUMN_TOTAL",
            ),
            mapping(
                1102,
                "CD_SHORT",
                [label(53, 46, "Chứng chỉ tiền gửi"), label(53, 57, "Dưới 12 tháng")],
                [line(53, 59, "111.067.679")],
                [line(54, 23, "96.457.274")],
                "INSTRUMENT_COLUMN_AND_TENOR_ROW",
            ),
            mapping(
                1103,
                "CD_MEDIUM",
                [label(53, 46, "Chứng chỉ tiền gửi"), label(53, 69, "Từ 12 tháng đến dưới 5 năm")],
                [line(53, 72, "9.462.714")],
                [line(54, 36, "8.043.397")],
                "INSTRUMENT_COLUMN_AND_TENOR_ROW",
            ),
            mapping(
                1104,
                "CD_LONG",
                [label(53, 46, "Chứng chỉ tiền gửi"), label(53, 85, "Từ 5 năm trở lên")],
                [ctg_current_cd_long],
                [ctg_comparative_cd_long],
                "VISIBLE_PIXEL_DASH_ZERO_IN_INSTRUMENT_TENOR_CELL",
            ),
            mapping(
                1105,
                "PROMISSORY_NOTE",
                [label(53, 47, "Kỳ phiếu"), label(54, 10, "Kỳ phiếu")],
                [line(53, 97, "153")],
                [line(54, 61, "153")],
                "INSTRUMENT_COLUMN_TOTAL",
            ),
            mapping(
                1106,
                "PROMISSORY_SHORT",
                [label(53, 47, "Kỳ phiếu"), label(53, 57, "Dưới 12 tháng")],
                [line(53, 58, "153")],
                [line(54, 22, "153")],
                "INSTRUMENT_COLUMN_AND_TENOR_ROW",
            ),
            mapping(
                1107,
                "PROMISSORY_MEDIUM",
                [label(53, 47, "Kỳ phiếu"), label(53, 69, "Từ 12 tháng đến dưới 5 năm")],
                [ctg_current_ky_medium],
                [ctg_comparative_ky_medium],
                "VISIBLE_PIXEL_DASH_ZERO_IN_INSTRUMENT_TENOR_CELL",
            ),
            mapping(
                1108,
                "PROMISSORY_LONG",
                [label(53, 47, "Kỳ phiếu"), label(53, 85, "Từ 5 năm trở lên")],
                [ctg_current_ky_long],
                [ctg_comparative_ky_long],
                "VISIBLE_PIXEL_DASH_ZERO_IN_INSTRUMENT_TENOR_CELL",
            ),
            mapping(
                1109,
                "BOND",
                [
                    label(53, 44, "Trái phiếu vô danh"),
                    label(53, 45, "Trái phiếu ghi sổ"),
                    label(54, 7, "Trái phiếu vô danh"),
                    label(54, 8, "Trái phiếu ghi sổ"),
                ],
                [line(53, 98, "166"), line(53, 99, "53.499.640")],
                [line(54, 62, "166"), line(54, 63, "47.177.100")],
                "SUM_OF_TWO_BOND_INSTRUMENT_COLUMNS",
            ),
            mapping(
                1110,
                "BOND_SHORT",
                [
                    label(53, 44, "Trái phiếu vô danh"),
                    label(53, 45, "Trái phiếu ghi sổ"),
                    label(53, 57, "Dưới 12 tháng"),
                ],
                [ctg_current_bond_short_anon, ctg_current_bond_short_registered],
                [ctg_comparative_bond_short_anon, ctg_comparative_bond_short_registered],
                "TWO_VISIBLE_PIXEL_DASH_ZERO_CELLS",
            ),
            mapping(
                1111,
                "BOND_MEDIUM",
                [label(53, 44, "Trái phiếu vô danh"), label(53, 69, "Từ 12 tháng đến dưới 5 năm")],
                [line(53, 71, "166")],
                [line(54, 35, "166")],
                "NONZERO_BOND_COLUMN_IN_TENOR_ROW",
            ),
            mapping(
                1112,
                "BOND_LONG",
                [label(53, 45, "Trái phiếu ghi sổ"), label(53, 85, "Từ 5 năm trở lên")],
                [line(53, 86, "53.499.640")],
                [line(54, 50, "47.177.100")],
                "NONZERO_BOND_COLUMN_IN_TENOR_ROW",
            ),
            mapping(
                1113,
                "PROMISSORY_AND_BOND_TOTAL",
                [
                    label(53, 47, "Kỳ phiếu"),
                    label(53, 44, "Trái phiếu vô danh"),
                    label(53, 45, "Trái phiếu ghi sổ"),
                ],
                [line(53, 97, "153"), line(53, 98, "166"), line(53, 99, "53.499.640")],
                [line(54, 61, "153"), line(54, 62, "166"), line(54, 63, "47.177.100")],
                "SUM_OF_PROMISSORY_AND_TWO_BOND_COLUMNS",
            ),
            mapping(
                1114,
                "PROMISSORY_AND_BOND_SHORT",
                [label(53, 57, "Dưới 12 tháng")],
                [
                    line(53, 58, "153"),
                    ctg_current_bond_short_anon,
                    ctg_current_bond_short_registered,
                ],
                [
                    line(54, 22, "153"),
                    ctg_comparative_bond_short_anon,
                    ctg_comparative_bond_short_registered,
                ],
                "SUM_OF_PROMISSORY_AND_BOND_TENOR_CELLS",
            ),
            mapping(
                1115,
                "PROMISSORY_AND_BOND_MEDIUM",
                [label(53, 69, "Từ 12 tháng đến dưới 5 năm")],
                [ctg_current_ky_medium, line(53, 71, "166")],
                [ctg_comparative_ky_medium, line(54, 35, "166")],
                "SUM_OF_PROMISSORY_AND_BOND_TENOR_CELLS",
            ),
            mapping(
                1116,
                "PROMISSORY_AND_BOND_LONG",
                [label(53, 85, "Từ 5 năm trở lên")],
                [ctg_current_ky_long, line(53, 86, "53.499.640")],
                [ctg_comparative_ky_long, line(54, 50, "47.177.100")],
                "SUM_OF_PROMISSORY_AND_BOND_TENOR_CELLS",
            ),
        ],
        [
            base._equation(
                "CD_TENORS_TO_PARENT",
                "CURRENT",
                [line(53, 59, "111.067.679"), line(53, 72, "9.462.714"), ctg_current_cd_long],
                line(53, 100, "120.530.393"),
            ),
            base._equation(
                "CD_TENORS_TO_PARENT",
                "COMPARATIVE",
                [line(54, 23, "96.457.274"), line(54, 36, "8.043.397"), ctg_comparative_cd_long],
                line(54, 64, "104.500.671"),
            ),
            base._equation(
                "PROMISSORY_TENORS_TO_PARENT",
                "CURRENT",
                [line(53, 58, "153"), ctg_current_ky_medium, ctg_current_ky_long],
                line(53, 97, "153"),
            ),
            base._equation(
                "PROMISSORY_TENORS_TO_PARENT",
                "COMPARATIVE",
                [line(54, 22, "153"), ctg_comparative_ky_medium, ctg_comparative_ky_long],
                line(54, 61, "153"),
            ),
            base._equation(
                "INSTRUMENT_COLUMNS_TO_TOTAL",
                "CURRENT",
                [
                    line(53, 97, "153"),
                    line(53, 98, "166"),
                    line(53, 99, "53.499.640"),
                    line(53, 100, "120.530.393"),
                ],
                line(53, 40, "174.030.352"),
            ),
            base._equation(
                "INSTRUMENT_COLUMNS_TO_TOTAL",
                "COMPARATIVE",
                [
                    line(54, 61, "153"),
                    line(54, 62, "166"),
                    line(54, 63, "47.177.100"),
                    line(54, 64, "104.500.671"),
                ],
                line(54, 65, "151.678.090"),
            ),
        ],
        presentation="ADJACENT_PERIOD_PAGES_WITH_MULTI_LEVEL_INSTRUMENT_COLUMN_HEADER",
        page_span=[53, 54],
    )

    bid = doc(
        "BID",
        52,
        4,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [label(52, 5, "Số cuối năm"), label(52, 6, "Số đầu năm")],
        [label(52, 7, "Triệu VND"), label(52, 8, "Triệu VND")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(52, 4, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                [line(52, 42, "225.407.774")],
                [line(52, 43, "198.900.165")],
                "UNLABELED_TOTAL_AFTER_INSTRUMENTS",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [label(52, 9, "Chứng chỉ tiền gửi")],
                [line(52, 10, "153.360.747")],
                [line(52, 11, "148.259.629")],
                "OWNER_INSTRUMENT_PARENT",
            ),
            mapping(
                1102,
                "CD_SHORT",
                [label(52, 9, "Chứng chỉ tiền gửi"), label(52, 12, "Dưới 12 tháng")],
                [line(52, 13, "110.776.844")],
                [line(52, 14, "123.548.788")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1103,
                "CD_MEDIUM",
                [label(52, 9, "Chứng chỉ tiền gửi"), label(52, 15, "Từ 12 tháng đến dưới 05 năm")],
                [line(52, 16, "42.563.907")],
                [line(52, 17, "24.690.896")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1104,
                "CD_LONG",
                [label(52, 9, "Chứng chỉ tiền gửi"), label(52, 18, "Từ 05 năm trở lên")],
                [line(52, 19, "19.996")],
                [line(52, 20, "19.945")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1105,
                "PROMISSORY_NOTE",
                [label(52, 21, "Kỳ phiếu")],
                [line(52, 22, "519")],
                [line(52, 23, "513")],
                "OWNER_INSTRUMENT_PARENT",
            ),
            mapping(
                1106,
                "PROMISSORY_SHORT",
                [label(52, 21, "Kỳ phiếu"), label(52, 24, "Dưới 12 tháng")],
                [line(52, 25, "312")],
                [line(52, 26, "306")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1107,
                "PROMISSORY_MEDIUM",
                [label(52, 21, "Kỳ phiếu"), label(52, 27, "Từ 12 tháng đến dưới 05 năm")],
                [line(52, 28, "207")],
                [line(52, 29, "207")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1109,
                "BOND",
                [label(52, 30, "Trái phiếu")],
                [line(52, 31, "14.160.381")],
                [line(52, 32, "5.500.376")],
                "OWNER_INSTRUMENT_PARENT",
            ),
            mapping(
                1111,
                "BOND_MEDIUM",
                [label(52, 30, "Trái phiếu"), label(52, 33, "Từ 12 tháng đến dưới 05 năm")],
                [line(52, 34, "8.660.061")],
                [line(52, 35, "61")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1112,
                "BOND_LONG",
                [label(52, 30, "Trái phiếu"), label(52, 36, "Từ 05 năm trở lên")],
                [line(52, 37, "5.500.320")],
                [line(52, 38, "5.500.315")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1117,
                "CAPITAL_INCREASE_BOND",
                [label(52, 39, "Trái phiếu tăng vốn BIDV")],
                [line(52, 40, "57.886.127")],
                [line(52, 41, "45.139.647")],
                "PROJECT_OWNER_APPROVED_OTHER_ISSUED_PAPER_LEAF",
            ),
        ],
        [
            base._equation(
                "CD_TENORS_TO_PARENT",
                "CURRENT",
                [line(52, 13, "110.776.844"), line(52, 16, "42.563.907"), line(52, 19, "19.996")],
                line(52, 10, "153.360.747"),
            ),
            base._equation(
                "CD_TENORS_TO_PARENT",
                "COMPARATIVE",
                [line(52, 14, "123.548.788"), line(52, 17, "24.690.896"), line(52, 20, "19.945")],
                line(52, 11, "148.259.629"),
            ),
            base._equation(
                "PROMISSORY_TENORS_TO_PARENT",
                "CURRENT",
                [line(52, 25, "312"), line(52, 28, "207")],
                line(52, 22, "519"),
            ),
            base._equation(
                "PROMISSORY_TENORS_TO_PARENT",
                "COMPARATIVE",
                [line(52, 26, "306"), line(52, 29, "207")],
                line(52, 23, "513"),
            ),
            base._equation(
                "BOND_TENORS_TO_PARENT",
                "CURRENT",
                [line(52, 34, "8.660.061"), line(52, 37, "5.500.320")],
                line(52, 31, "14.160.381"),
            ),
            base._equation(
                "BOND_TENORS_TO_PARENT",
                "COMPARATIVE",
                [line(52, 35, "61"), line(52, 38, "5.500.315")],
                line(52, 32, "5.500.376"),
            ),
            base._equation(
                "INSTRUMENTS_AND_CAPITAL_BOND_TO_TOTAL",
                "CURRENT",
                [
                    line(52, 10, "153.360.747"),
                    line(52, 22, "519"),
                    line(52, 31, "14.160.381"),
                    line(52, 40, "57.886.127"),
                ],
                line(52, 42, "225.407.774"),
            ),
            base._equation(
                "INSTRUMENTS_AND_CAPITAL_BOND_TO_TOTAL",
                "COMPARATIVE",
                [
                    line(52, 11, "148.259.629"),
                    line(52, 23, "513"),
                    line(52, 32, "5.500.376"),
                    line(52, 41, "45.139.647"),
                ],
                line(52, 43, "198.900.165"),
            ),
        ],
        presentation="TWO_PERIOD_VERTICAL_INSTRUMENT_TENOR_ROWS_PLUS_CAPITAL_BOND",
    )

    vib_cd_long_current = base._dash(
        47,
        [1165, 2050, 1223, 2105],
        "c2945012b65d0375e9153bfcf7714344f20b303073ec82f0ce4098bd3d602ec0",
    )
    vib = doc(
        "VIB",
        47,
        108,
        "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
        [label(47, 110, "31/12/2025"), label(47, 111, "31/12/2024")],
        [label(47, 112, "triệu đồng"), label(47, 113, "triệu đồng")],
        [
            mapping(
                1100,
                "FAMILY_TOTAL",
                [label(47, 108, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                [line(47, 127, "35.070.700")],
                [line(47, 128, "23.262.579")],
                "UNLABELED_TOTAL_AFTER_INSTRUMENTS",
            ),
            mapping(
                1101,
                "CERTIFICATE_OF_DEPOSIT",
                [label(47, 121, "Chứng chỉ tiền gửi")],
                [line(47, 123, "11.870.700"), vib_cd_long_current],
                [line(47, 124, "2.260.000"), line(47, 126, "54.579")],
                "SUM_OF_VISIBLE_TENOR_ROWS_WITH_DASH_ZERO",
            ),
            mapping(
                1103,
                "CD_MEDIUM",
                [label(47, 121, "Chứng chỉ tiền gửi"), label(47, 122, "Từ 12 tháng đến 5 năm")],
                [line(47, 123, "11.870.700")],
                [line(47, 124, "2.260.000")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1104,
                "CD_LONG",
                [label(47, 121, "Chứng chỉ tiền gửi"), label(47, 125, "Từ 5 năm trở lên")],
                [vib_cd_long_current],
                [line(47, 126, "54.579")],
                "VISIBLE_PIXEL_DASH_ZERO_AND_COMPARATIVE_VALUE",
            ),
            mapping(
                1109,
                "BOND",
                [label(47, 114, "Trái phiếu")],
                [line(47, 116, "17.200.000"), line(47, 119, "6.000.000")],
                [line(47, 117, "16.948.000"), line(47, 120, "4.000.000")],
                "SUM_OF_VISIBLE_TENOR_ROWS",
            ),
            mapping(
                1111,
                "BOND_MEDIUM",
                [label(47, 114, "Trái phiếu"), label(47, 115, "Từ 12 tháng đến dưới 5 năm")],
                [line(47, 116, "17.200.000")],
                [line(47, 117, "16.948.000")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
            mapping(
                1112,
                "BOND_LONG",
                [label(47, 114, "Trái phiếu"), label(47, 118, "Từ 5 năm trở lên")],
                [line(47, 119, "6.000.000")],
                [line(47, 120, "4.000.000")],
                "INSTRUMENT_CONTEXT_PLUS_TENOR",
            ),
        ],
        [
            base._equation(
                "ALL_TENOR_ROWS_TO_TOTAL",
                "CURRENT",
                [
                    line(47, 116, "17.200.000"),
                    line(47, 119, "6.000.000"),
                    line(47, 123, "11.870.700"),
                    vib_cd_long_current,
                ],
                line(47, 127, "35.070.700"),
            ),
            base._equation(
                "ALL_TENOR_ROWS_TO_TOTAL",
                "COMPARATIVE",
                [
                    line(47, 117, "16.948.000"),
                    line(47, 120, "4.000.000"),
                    line(47, 124, "2.260.000"),
                    line(47, 126, "54.579"),
                ],
                line(47, 128, "23.262.579"),
            ),
        ],
        presentation="TWO_PERIOD_VERTICAL_INSTRUMENT_AND_TENOR_ROWS_WITH_DASH_ZERO",
    )

    return [acb, mbb, vpb, hdb, vcb, ctg, bid, vib]


def _configure(base: ModuleType) -> None:
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
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._REVIEW_RUN_ID = REVIEW_RUN_ID
    base._EXPECTED_COMPLETE_REGION_COUNT = 8
    base._FAMILY_DISPLAY_ORDER_RANGE = [611, 635]
    base._REVIEW_CHECKS = list(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._AUTHORITY = dict(_AUTHORITY)
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._review_documents = lambda: _review_documents(base)
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        if source_period == "2025-12-31"
        else "INVALID_ANNUAL_SOURCE_PERIOD"
    )


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual issued-paper result metrics drifted")
    for trial in value.get("trials", []):
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error("annual issued-paper mapped schema set drifted")
        open_ids = {row["item_id"] for row in trial["unmapped_source_rows"]}
        if open_ids != _EXPECTED_OPEN_IDS[trial["document_provenance"]]:
            raise _error("annual issued-paper unresolved source set drifted")
        if trial["source_period_status"] != (
            "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        ):
            raise _error("annual issued-paper period status drifted")
    return value


def build_annual_2025_issued_valuable_papers_pixel_review_blueprint_v1() -> dict[str, Any]:
    base = _load_base()
    _configure(base)
    return base._review_blueprint()


def build_live_annual_2025_issued_valuable_papers_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    base = _load_base()
    _configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review = base._review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    scan = base.scanner.build_issued_valuable_papers_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_issued_valuable_papers_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    replayed = base.validate_issued_valuable_papers_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
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
    if args.write_review:
        output.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_issued_valuable_papers_pixel_review_blueprint_v1()
            )
        )
    else:
        result = build_live_annual_2025_issued_valuable_papers_8bank_codex_verified_mapping_v1()
        output.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
