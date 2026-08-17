"""Verify annual-2025 customer-deposit disclosures across eight banks.

The existing complete-PDF graph supplies one unique region per report.  This
annual wrapper selects only the visible 2025 monetary axis, preserves source
order and optional continuation/customer-type subviews, and uses the existing
generic verifier without routing on bank, page, note number or filename.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_CUSTOMER_DEPOSIT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CUSTOMER_DEPOSIT_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CUSTOMER_DEPOSIT_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025cd8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CUSTOMER_DEPOSIT_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025cd8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0129"
REVIEW_PATH = Path(
    "docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "cdfdsv1:scan:27f724972325d722b1fbc4ae9ad9cad41ae2179f27bd629b96f6e7659be2700a"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_CUSTOMER_DEPOSIT_BOUNDARY_PARENT_CHILD_CURRENCY_CUSTOMER_TYPE_"
    "CONTINUATION_VISIBLE_PIXEL_UPSTREAM_PPOCRV6_CURRENT_2025_MONETARY_AXIS_"
    "ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_UNMAPPED_COMBINED_ROWS_RETAINED_NO_EXPORT"
)
_EXPECTED_IDS = {
    "ACB": {
        1057,
        1058,
        1059,
        1060,
        1061,
        1062,
        1063,
        1064,
        1065,
        1066,
        1067,
        1068,
        1069,
        1070,
        1071,
        1076,
        1084,
        1085,
        1088,
        1089,
        1091,
    },
    "MBB": {1057, 1058, 1059, 1060, 1061, 1062, 1066, 1067, 1068, 1069, 1070, 1071, 1084, 1089},
    "VPB": {
        770,
        1057,
        1058,
        1059,
        1060,
        1061,
        1062,
        1066,
        1067,
        1068,
        1069,
        1070,
        1071,
        1076,
        1078,
        1080,
        1081,
        1082,
        1083,
        1085,
        1087,
        1088,
        1089,
        1090,
        1091,
    },
    "HDB": {
        1057,
        1058,
        1059,
        1060,
        1061,
        1062,
        1066,
        1067,
        1068,
        1069,
        1070,
        1071,
        1076,
        1080,
        1082,
        1085,
        1088,
        1089,
        1090,
        1091,
    },
    "VCB": {1057, 1058, 1059, 1060, 1061, 1062, 1066, 1069, 1084, 1089},
    "CTG": {
        1057,
        1058,
        1059,
        1060,
        1061,
        1062,
        1066,
        1067,
        1068,
        1069,
        1070,
        1071,
        1076,
        1078,
        1079,
        1080,
        1081,
        1082,
        1083,
        1085,
        1087,
        1088,
        1089,
        1090,
        1091,
    },
    "BID": {
        1057,
        1058,
        1059,
        1060,
        1061,
        1062,
        1066,
        1067,
        1068,
        1069,
        1070,
        1071,
        1076,
        1077,
        1088,
        1091,
    },
    "VIB": {
        770,
        1057,
        1058,
        1059,
        1060,
        1061,
        1062,
        1063,
        1064,
        1065,
        1066,
        1067,
        1068,
        1069,
        1070,
        1071,
        1076,
        1078,
        1080,
        1081,
        1082,
        1083,
        1085,
        1087,
        1088,
        1089,
        1090,
        5977,
    },
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 43,
    "document_count": 8,
    "document_unique_region_count": 8,
    "mapping_verified_count": 159,
    "q1_source_period_caveat_document_count": 0,
    "unresolved_source_item_count": 2,
}


class Annual2025CustomerDeposit8BankError(ValueError):
    """Annual customer-deposit evidence, accounting, schema or replay drifted."""


def _error(message: str) -> Annual2025CustomerDeposit8BankError:
    return Annual2025CustomerDeposit8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual customer-deposit support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _currency_rows(
    base: ModuleType,
    page: int,
    rows: Sequence[tuple[Any, ...]],
    owner_total: tuple[int, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mappings: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    parent_values: list[dict[str, Any]] = []
    for (
        role,
        parent_id,
        parent_label,
        parent_lines,
        parent_value,
        vnd_id,
        vnd_label,
        vnd_lines,
        vnd_value,
        foreign_id,
        foreign_label,
        foreign_lines,
        foreign_value,
    ) in rows:
        parent_ref = base._value(*parent_value)
        vnd_ref = base._value(*vnd_value)
        foreign_ref = base._value(*foreign_value)
        mappings.extend(
            [
                base._mapping(parent_id, role, page, parent_label, parent_lines, [parent_ref]),
                base._mapping(vnd_id, f"{role}_VND", page, vnd_label, vnd_lines, [vnd_ref]),
                base._mapping(
                    foreign_id,
                    f"{role}_FOREIGN",
                    page,
                    foreign_label,
                    foreign_lines,
                    [foreign_ref],
                ),
            ]
        )
        equations.append(
            base._equation(
                f"{role}_EQUALS_VND_PLUS_FOREIGN",
                page,
                [vnd_ref, foreign_ref],
                parent_ref,
            )
        )
        parent_values.append(parent_ref)
    equations.append(
        base._equation(
            "OWNER_TOTAL_EQUALS_SOURCE_PARENTS",
            page,
            parent_values,
            base._value(*owner_total),
        )
    )
    return mappings, equations


def _customer_mapping(
    base: ModuleType,
    report_norm_id: int,
    role: str,
    page: int,
    label: str,
    lines: Sequence[int],
    values: Sequence[tuple[int, str]],
    *,
    aggregation: str = "DIRECT_VISIBLE_VALUE",
    additivity: str = "ADDITIVE_WITHIN_CUSTOMER_TYPE_TABLE",
) -> dict[str, Any]:
    return base._mapping(
        report_norm_id,
        role,
        page,
        label,
        lines,
        [base._value(*value) for value in values],
        aggregation=aggregation,
        section="CUSTOMER_TYPE",
        additivity=additivity,
    )


def _acb(base: ModuleType) -> dict[str, Any]:
    v, m, e = base._value, base._mapping, base._equation
    mappings = [
        m(
            1057,
            "NO_TERM",
            62,
            "Tiền gửi không kỳ hạn",
            [12],
            [v(14, "111.715.178"), v(17, "12.823.805")],
            aggregation="SUM_OF_VISIBLE_CURRENCY_ROWS",
        ),
        m(1058, "NO_TERM_VND", 62, "Bằng Đồng Việt Nam", [13], [v(14, "111.715.178")]),
        m(1059, "NO_TERM_FOREIGN", 62, "Bằng ngoại tệ", [16], [v(17, "12.823.805")]),
        m(
            1060,
            "TERM",
            62,
            "Tiền gửi có kỳ hạn",
            [19],
            [v(21, "159.296.370"), v(24, "1.052.565")],
            aggregation="SUM_OF_VISIBLE_CURRENCY_ROWS",
        ),
        m(1061, "TERM_VND", 62, "Bằng Đồng Việt Nam", [20], [v(21, "159.296.370")]),
        m(1062, "TERM_FOREIGN", 62, "Bằng ngoại tệ", [23], [v(24, "1.052.565")]),
        m(
            1063,
            "SAVINGS",
            62,
            "Tiền gửi tiết kiệm",
            [26, 33],
            [v(28, "573.909"), v(31, "5.210.013"), v(35, "289.874.053"), v(38, "1.501.370")],
            aggregation="SUM_OF_VISIBLE_SAVINGS_ROWS",
        ),
        m(
            1064,
            "SAVINGS_VND",
            62,
            "Tiền gửi tiết kiệm bằng Đồng Việt Nam",
            [26, 27, 33, 34],
            [v(28, "573.909"), v(35, "289.874.053")],
            aggregation="SUM_OF_VISIBLE_SAVINGS_ROWS",
        ),
        m(
            1065,
            "SAVINGS_FOREIGN",
            62,
            "Tiền gửi tiết kiệm bằng ngoại tệ",
            [26, 30, 33, 37],
            [v(31, "5.210.013"), v(38, "1.501.370")],
            aggregation="SUM_OF_VISIBLE_SAVINGS_ROWS",
        ),
        m(
            1066,
            "ESCROW",
            62,
            "Tiền gửi ký quỹ",
            [40],
            [v(42, "2.564.158"), v(45, "241.061")],
            aggregation="SUM_OF_VISIBLE_CURRENCY_ROWS",
        ),
        m(1067, "ESCROW_VND", 62, "Bằng Đồng Việt Nam", [41], [v(42, "2.564.158")]),
        m(1068, "ESCROW_FOREIGN", 62, "Bằng ngoại tệ", [44], [v(45, "241.061")]),
        m(
            1069,
            "DEDICATED",
            62,
            "Tiền gửi vốn chuyên dùng",
            [47],
            [v(49, "105.792"), v(52, "221.901")],
            aggregation="SUM_OF_VISIBLE_CURRENCY_ROWS",
        ),
        m(1070, "DEDICATED_VND", 62, "Bằng Đồng Việt Nam", [48], [v(49, "105.792")]),
        m(1071, "DEDICATED_FOREIGN", 62, "Bằng ngoại tệ", [51], [v(52, "221.901")]),
        _customer_mapping(
            base, 1076, "STATE_COMPANY", 62, "Doanh nghiệp Nhà nước", [63], [(64, "1.673.146")]
        ),
        _customer_mapping(
            base,
            1088,
            "FOREIGN_INVESTED",
            62,
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            [66],
            [(67, "10.634.177")],
        ),
        _customer_mapping(
            base,
            1084,
            "COMBINED_COMPANY",
            62,
            "Công ty cổ phần, công ty TNHH và doanh nghiệp khác",
            [69],
            [(70, "102.644.034")],
        ),
        _customer_mapping(base, 1085, "COOPERATIVE", 62, "Hợp tác xã", [72], [(73, "98.369")]),
        _customer_mapping(
            base,
            1089,
            "HOUSEHOLD_INDIVIDUAL",
            62,
            "Cá nhân và hộ kinh doanh",
            [75],
            [(76, "455.461.007")],
        ),
        _customer_mapping(
            base, 1091, "OTHER_CUSTOMER", 62, "Các đối tượng khác", [78], [(79, "14.669.442")]
        ),
    ]
    # ACB prints no parent subtotal for each currency pair.  The owner total and
    # customer-type total are the two exact printed equations; currency rows are
    # mapped by their visible axes without inventing hidden subtotals.
    equations = [
        e(
            "OWNER_TOTAL_EQUALS_ALL_VISIBLE_TYPE_ROWS",
            62,
            [
                v(14, "111.715.178"),
                v(17, "12.823.805"),
                v(21, "159.296.370"),
                v(24, "1.052.565"),
                v(28, "573.909"),
                v(31, "5.210.013"),
                v(35, "289.874.053"),
                v(38, "1.501.370"),
                v(42, "2.564.158"),
                v(45, "241.061"),
                v(49, "105.792"),
                v(52, "221.901"),
            ],
            v(54, "585.180.175"),
        ),
        e(
            "CUSTOMER_TYPE_TOTAL",
            62,
            [
                v(64, "1.673.146"),
                v(67, "10.634.177"),
                v(70, "102.644.034"),
                v(73, "98.369"),
                v(76, "455.461.007"),
                v(79, "14.669.442"),
            ],
            v(81, "585.180.175"),
        ),
    ]
    return base._doc(
        "ACB",
        [62],
        "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_PLUS_CUSTOMER_TYPE_SUBTABLE",
        "2025-12-31",
        mappings,
        equations,
        customer_type_subview="MAPPED_DETAILED_CUSTOMER_TYPE_SUBTABLE",
    )


def _mbb(base: ModuleType) -> dict[str, Any]:
    rows = [
        (
            "NO_TERM",
            1057,
            "Tiền gửi không kỳ hạn",
            [15],
            (16, "339.352.789"),
            1058,
            "Tiền gửi không kỳ hạn bằng VND",
            [18],
            (19, "304.453.535"),
            1059,
            "Tiền gửi không kỳ hạn bằng ngoại tệ",
            [21],
            (22, "34.899.254"),
        ),
        (
            "TERM",
            1060,
            "Tiền gửi có kỳ hạn",
            [24],
            (25, "573.482.507"),
            1061,
            "Tiền gửi có kỳ hạn bằng VND",
            [27],
            (28, "563.989.870"),
            1062,
            "Tiền gửi có kỳ hạn bằng ngoại tệ",
            [30],
            (31, "9.492.637"),
        ),
        (
            "DEDICATED",
            1069,
            "Tiền gửi vốn chuyên dùng",
            [33],
            (34, "1.226.310"),
            1070,
            "Tiền gửi vốn chuyên dùng bằng VND",
            [36],
            (37, "557.357"),
            1071,
            "Tiền gửi vốn chuyên dùng bằng ngoại tệ",
            [39],
            (40, "668.953"),
        ),
        (
            "ESCROW",
            1066,
            "Tiền gửi ký quỹ",
            [42],
            (43, "7.306.526"),
            1067,
            "Tiền gửi ký quỹ bằng VND",
            [45],
            (46, "4.544.143"),
            1068,
            "Tiền gửi ký quỹ bằng ngoại tệ",
            [48],
            (49, "2.762.383"),
        ),
    ]
    mappings, equations = _currency_rows(base, 65, rows, (51, "921.368.132"))
    mappings.extend(
        [
            _customer_mapping(
                base, 1084, "CUSTOMER_TCKT", 65, "Tổ chức kinh tế", [79], [(80, "402.397.512")]
            ),
            _customer_mapping(
                base, 1089, "CUSTOMER_INDIVIDUAL", 65, "Cá nhân", [84], [(85, "518.970.620")]
            ),
        ]
    )
    equations.append(
        base._equation(
            "CUSTOMER_TYPE_TOTAL",
            65,
            [base._value(80, "402.397.512"), base._value(85, "518.970.620")],
            base._value(90, "921.368.132"),
        )
    )
    return base._doc(
        "MBB",
        [65],
        "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_PLUS_MONEY_PERCENT_CUSTOMER_TYPE_SUBTABLE",
        "2025-12-31",
        mappings,
        equations,
        customer_type_subview="MAPPED_TWO_ROW_CUSTOMER_TYPE_SUBTABLE",
    )


def _vpb(base: ModuleType) -> dict[str, Any]:
    rows = [
        (
            "NO_TERM",
            1057,
            "Tiền gửi không kỳ hạn",
            [12],
            (14, "85.753.335"),
            1058,
            "Bằng VND",
            [16],
            (17, "83.254.251"),
            1059,
            "Bằng ngoại tệ",
            [19],
            (20, "2.499.084"),
        ),
        (
            "TERM",
            1060,
            "Tiền gửi có kỳ hạn",
            [22],
            (23, "537.300.864"),
            1061,
            "Bằng VND",
            [25],
            (26, "534.083.187"),
            1062,
            "Bằng ngoại tệ",
            [28],
            (29, "3.217.677"),
        ),
        (
            "DEDICATED",
            1069,
            "Tiền gửi vốn chuyên dùng",
            [32],
            (33, "1.319.162"),
            1070,
            "Bằng VND",
            [35],
            (36, "1.268.588"),
            1071,
            "Bằng ngoại tệ",
            [38],
            (40, "50.574"),
        ),
        (
            "ESCROW",
            1066,
            "Tiền ký quỹ",
            [42],
            (43, "3.671.255"),
            1067,
            "Bằng VND",
            [45],
            (46, "3.426.331"),
            1068,
            "Bằng ngoại tệ",
            [48],
            (49, "244.924"),
        ),
    ]
    mappings, equations = _currency_rows(base, 60, rows, (51, "628.044.616"))
    specs = [
        (1076, "STATE_COMPANY", "Công ty nhà nước", [16], 17, "2.339.098"),
        (
            1078,
            "STATE_100_TNHH",
            "Công ty TNHH 1 thành viên do Nhà nước sở hữu 100% vốn điều lệ",
            [21, 22],
            23,
            "1.685.701",
        ),
        (
            770,
            "STATE_OVER_50_MULTI_MEMBER_TNHH",
            "Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50%",
            [27, 28, 29, 30],
            31,
            "80.149",
        ),
        (1080, "OTHER_TNHH", "Công ty TNHH khác", [35], 36, "61.427.977"),
        (
            1081,
            "STATE_OVER_50_JSC",
            "Công ty cổ phần có vốn góp của Nhà nước trên 50%",
            [40, 41, 42, 43, 44],
            45,
            "3.318.903",
        ),
        (1082, "OTHER_JSC", "Công ty cổ phần khác", [49], 50, "196.357.171"),
        (1087, "PARTNERSHIP", "Công ty hợp danh", [54], 55, "2.155"),
        (1083, "PRIVATE_ENTERPRISE", "Doanh nghiệp tư nhân", [59], 60, "588.407"),
        (1088, "FOREIGN_INVESTED", "Doanh nghiệp có vốn đầu tư nước ngoài", [64], 65, "3.546.653"),
        (1085, "COOPERATIVE", "Hợp tác xã và liên hiệp hợp tác xã", [69], 70, "120.660"),
        (1089, "HOUSEHOLD_INDIVIDUAL", "Hộ kinh doanh, cá nhân", [74], 75, "353.454.878"),
        (
            1090,
            "ADMIN_ASSOCIATION",
            "Đơn vị hành chính sự nghiệp, Đảng, đoàn thể và hiệp hội",
            [79, 80],
            81,
            "4.975.266",
        ),
        (1091, "OTHER_CUSTOMER", "Khác", [85], 86, "147.598"),
    ]
    mappings.extend(
        _customer_mapping(base, i, role, 61, label, lines, [(value_line, value)])
        for i, role, label, lines, value_line, value in specs
    )
    equations.append(
        base._equation(
            "CUSTOMER_TYPE_TOTAL",
            61,
            [base._value(value_line, value) for _, _, _, _, value_line, value in specs],
            base._value(90, "628.044.616"),
        )
    )
    return base._doc(
        "VPB",
        [60, 61],
        "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_WITH_CROSS_PAGE_MONEY_PERCENT_CUSTOMER_TYPE",
        "2025-12-31",
        mappings,
        equations,
        customer_type_subview="MAPPED_CROSS_PAGE_DETAILED_CUSTOMER_TYPE_SUBTABLE",
    )


def _standard_document(
    base: ModuleType,
    *,
    code: str,
    page: int,
    rows: Sequence[tuple[Any, ...]],
    owner_total: tuple[int, str],
    customer_specs: Sequence[tuple[Any, ...]],
    customer_total: tuple[int, str],
    unresolved: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    mappings, equations = _currency_rows(base, page, rows, owner_total)
    mappings.extend(
        _customer_mapping(base, i, role, page, label, lines, [(value_line, value)])
        for i, role, label, lines, value_line, value in customer_specs
    )
    equations.append(
        base._equation(
            "CUSTOMER_TYPE_TOTAL_INCLUDING_ALL_SOURCE_ROWS",
            page,
            [base._value(value_line, value) for _, _, _, _, value_line, value in customer_specs]
            + [item["value"] for item in unresolved],
            base._value(*customer_total),
        )
    )
    return base._doc(
        code,
        [page],
        "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_PLUS_CUSTOMER_TYPE_SUBTABLE",
        "2025-12-31",
        mappings,
        equations,
        unresolved,
        customer_type_subview=(
            "PARTIALLY_MAPPED_DETAILED_CUSTOMER_TYPE_SUBTABLE"
            if unresolved
            else "MAPPED_DETAILED_CUSTOMER_TYPE_SUBTABLE"
        ),
    )


def _hdb(base: ModuleType) -> dict[str, Any]:
    rows = [
        (
            "NO_TERM",
            1057,
            "Tiền gửi không kỳ hạn",
            [13],
            (14, "67.857.913"),
            1058,
            "Tiền gửi không kỳ hạn bằng VND",
            [16],
            (17, "55.684.718"),
            1059,
            "Tiền gửi không kỳ hạn bằng ngoại tệ",
            [19],
            (20, "12.173.195"),
        ),
        (
            "TERM",
            1060,
            "Tiền gửi có kỳ hạn",
            [22],
            (23, "491.206.575"),
            1061,
            "Tiền gửi có kỳ hạn bằng VND",
            [25],
            (26, "490.858.842"),
            1062,
            "Tiền gửi có kỳ hạn bằng ngoại tệ",
            [28],
            (29, "347.733"),
        ),
        (
            "DEDICATED",
            1069,
            "Tiền gửi vốn chuyên dùng",
            [31],
            (32, "985.313"),
            1070,
            "Tiền gửi vốn chuyên dùng bằng VND",
            [34],
            (35, "889.717"),
            1071,
            "Tiền gửi vốn chuyên dùng bằng ngoại tệ",
            [37],
            (38, "95.596"),
        ),
        (
            "ESCROW",
            1066,
            "Tiền gửi ký quỹ",
            [40],
            (41, "664.481"),
            1067,
            "Tiền gửi ký quỹ bằng VND",
            [43],
            (44, "525.228"),
            1068,
            "Tiền gửi ký quỹ bằng ngoại tệ",
            [46],
            (47, "139.253"),
        ),
    ]
    customers = [
        (1089, "HOUSEHOLD_INDIVIDUAL", "Hộ kinh doanh, cá nhân", [56], 57, "445.550.141"),
        (1082, "OTHER_JSC", "Công ty cổ phần khác", [59], 60, "46.412.314"),
        (1080, "OTHER_TNHH", "Công ty TNHH khác", [62], 63, "33.747.248"),
        (1076, "STATE_COMPANY", "Doanh nghiệp nhà nước", [65], 66, "12.248.227"),
        (1088, "FOREIGN_INVESTED", "Doanh nghiệp có vốn đầu tư nước ngoài", [68], 69, "13.597.542"),
        (
            1090,
            "ADMIN_ASSOCIATION",
            "Đơn vị hành chính sự nghiệp, Đảng, đoàn thể và hiệp hội",
            [71],
            72,
            "3.573.749",
        ),
        (1085, "COOPERATIVE", "Hợp tác xã và liên hiệp hợp tác xã", [74], 75, "263.675"),
        (1091, "OTHER_CUSTOMER", "Khác", [77], 78, "5.321.386"),
    ]
    return _standard_document(
        base,
        code="HDB",
        page=45,
        rows=rows,
        owner_total=(49, "560.714.282"),
        customer_specs=customers,
        customer_total=(80, "560.714.282"),
    )


def _vcb(base: ModuleType) -> dict[str, Any]:
    v, m, e = base._value, base._mapping, base._equation
    mappings = [
        m(1057, "NO_TERM", 53, "Tiền gửi không kỳ hạn", [14], [v(15, "563.957.715")]),
        m(1058, "NO_TERM_VND", 53, "Tiền gửi không kỳ hạn bằng VND", [18], [v(19, "432.070.265")]),
        m(
            1059,
            "NO_TERM_FOREIGN",
            53,
            "Tiền gửi không kỳ hạn bằng vàng, ngoại tệ",
            [21],
            [v(22, "131.887.450")],
        ),
        m(1060, "TERM", 53, "Tiền gửi có kỳ hạn", [24], [v(25, "1.080.116.563")]),
        m(1061, "TERM_VND", 53, "Tiền gửi có kỳ hạn bằng VND", [27], [v(28, "967.967.469")]),
        m(
            1062,
            "TERM_FOREIGN",
            53,
            "Tiền gửi có kỳ hạn bằng vàng, ngoại tệ",
            [30],
            [v(31, "112.149.094")],
        ),
        m(1069, "DEDICATED", 53, "Tiền gửi vốn chuyên dùng", [33], [v(34, "20.093.867")]),
        m(1066, "ESCROW", 53, "Tiền gửi ký quỹ", [36], [v(37, "8.366.701")]),
        _customer_mapping(
            base, 1084, "CUSTOMER_TCKT", 53, "Các tổ chức kinh tế", [49], [(50, "858.491.427")]
        ),
        _customer_mapping(
            base, 1089, "CUSTOMER_INDIVIDUAL", 53, "Cá nhân", [52], [(53, "814.043.419")]
        ),
    ]
    equations = [
        e(
            "NO_TERM_CURRENCY_SUM",
            53,
            [v(19, "432.070.265"), v(22, "131.887.450")],
            v(15, "563.957.715"),
        ),
        e(
            "TERM_CURRENCY_SUM",
            53,
            [v(28, "967.967.469"), v(31, "112.149.094")],
            v(25, "1.080.116.563"),
        ),
        e(
            "OWNER_TOTAL",
            53,
            [v(15, "563.957.715"), v(25, "1.080.116.563"), v(34, "20.093.867"), v(37, "8.366.701")],
            v(39, "1.672.534.846"),
        ),
        e(
            "CUSTOMER_TYPE_TOTAL",
            53,
            [v(50, "858.491.427"), v(53, "814.043.419")],
            v(55, "1.672.534.846"),
        ),
    ]
    return base._doc(
        "VCB",
        [53],
        "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_PLUS_TWO_ROW_CUSTOMER_TYPE",
        "2025-12-31",
        mappings,
        equations,
        customer_type_subview="MAPPED_TWO_ROW_CUSTOMER_TYPE_SUBTABLE",
    )


def _ctg(base: ModuleType) -> dict[str, Any]:
    rows = [
        (
            "NO_TERM",
            1057,
            "Tiền gửi không kỳ hạn",
            [12],
            (13, "445.508.702"),
            1058,
            "Bằng VND",
            [15],
            (16, "364.161.636"),
            1059,
            "Bằng ngoại tệ",
            [18],
            (19, "81.347.066"),
        ),
        (
            "TERM",
            1060,
            "Tiền gửi có kỳ hạn",
            [21],
            (22, "1.335.632.038"),
            1061,
            "Bằng VND",
            [24],
            (25, "1.286.750.366"),
            1062,
            "Bằng ngoại tệ",
            [27],
            (28, "48.881.672"),
        ),
        (
            "DEDICATED",
            1069,
            "Tiền gửi vốn chuyên dùng",
            [30],
            (31, "5.787.395"),
            1070,
            "Bằng VND",
            [33],
            (34, "4.827.196"),
            1071,
            "Bằng ngoại tệ",
            [36],
            (37, "960.199"),
        ),
        (
            "ESCROW",
            1066,
            "Tiền gửi ký quỹ",
            [39],
            (40, "6.803.922"),
            1067,
            "Bằng VND",
            [42],
            (43, "6.225.421"),
            1068,
            "Bằng ngoại tệ",
            [45],
            (46, "578.501"),
        ),
    ]
    customers = [
        (1076, "STATE_COMPANY", "Công ty Nhà nước", [56], 57, "278.848.991"),
        (1078, "STATE_100_TNHH", "Công ty TNHH MTV vốn Nhà nước 100%", [59], 60, "32.884.087"),
        (
            1079,
            "STATE_OVER_50_ONE_MEMBER_TNHH",
            "Công ty TNHH MTV vốn Nhà nước trên 50%",
            [62],
            63,
            "2.509.027",
        ),
        (1080, "OTHER_TNHH", "Công ty TNHH khác", [65], 66, "74.182.543"),
        (
            1081,
            "STATE_OVER_50_JSC",
            "Công ty cổ phần vốn Nhà nước trên 50%",
            [68],
            69,
            "50.907.591",
        ),
        (1082, "OTHER_JSC", "Công ty cổ phần khác", [71], 72, "157.639.190"),
        (1087, "PARTNERSHIP", "Công ty hợp danh", [74], 75, "388.056"),
        (1083, "PRIVATE_ENTERPRISE", "Doanh nghiệp tư nhân", [77], 78, "3.525.800"),
        (
            1088,
            "FOREIGN_INVESTED",
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            [80],
            81,
            "162.662.832",
        ),
        (1085, "COOPERATIVE", "Hợp tác xã và Liên hiệp Hợp tác xã", [83], 84, "733.219"),
        (1089, "HOUSEHOLD_INDIVIDUAL", "Hộ kinh doanh, cá nhân", [86], 87, "863.073.129"),
        (
            1090,
            "ADMIN_ASSOCIATION",
            "Đơn vị hành chính sự nghiệp, Đảng, đoàn thể và hiệp hội",
            [89],
            90,
            "104.619.921",
        ),
        (1091, "OTHER_CUSTOMER", "Thành phần kinh tế khác", [92], 93, "61.757.671"),
    ]
    return _standard_document(
        base,
        code="CTG",
        page=52,
        rows=rows,
        owner_total=(48, "1.793.732.057"),
        customer_specs=customers,
        customer_total=(95, "1.793.732.057"),
    )


def _bid(base: ModuleType) -> dict[str, Any]:
    rows = [
        (
            "NO_TERM",
            1057,
            "Tiền gửi không kỳ hạn",
            [10],
            (11, "469.554.645"),
            1058,
            "Bằng VND",
            [13],
            (14, "407.669.514"),
            1059,
            "Bằng ngoại tệ",
            [16],
            (17, "61.885.131"),
        ),
        (
            "TERM",
            1060,
            "Tiền gửi có kỳ hạn",
            [19],
            (20, "1.738.093.116"),
            1061,
            "Bằng VND",
            [22],
            (23, "1.597.705.317"),
            1062,
            "Bằng ngoại tệ",
            [25],
            (26, "140.387.799"),
        ),
        (
            "DEDICATED",
            1069,
            "Tiền gửi vốn chuyên dụng",
            [28],
            (29, "10.326.526"),
            1070,
            "Bằng VND",
            [31],
            (32, "4.497.661"),
            1071,
            "Bằng ngoại tệ",
            [34],
            (35, "5.828.865"),
        ),
        (
            "ESCROW",
            1066,
            "Tiền gửi ký quỹ",
            [37],
            (38, "5.017.341"),
            1067,
            "Bằng VND",
            [40],
            (41, "4.580.188"),
            1068,
            "Bằng ngoại tệ",
            [43],
            (44, "437.153"),
        ),
    ]
    customers = [
        (1076, "STATE_COMPANY", "Doanh nghiệp Nhà nước", [55], 56, "307.807.850"),
        (1077, "TNHH", "Công ty trách nhiệm hữu hạn", [60], 61, "106.337.219"),
        (
            1088,
            "FOREIGN_INVESTED",
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            [71, 76],
            72,
            "146.119.118",
        ),
        (1091, "OTHER_CUSTOMER", "Khác", [85], 86, "349.120.963"),
    ]
    unresolved = [
        base._unresolved(
            51,
            "Công ty cổ phần",
            [65],
            base._value(66, "204.344.052"),
            "The broad printed JSC row does not distinguish State-over-50% from other JSC leaves 1081/1082.",
        ),
        base._unresolved(
            51,
            "Doanh nghiệp tư nhân, cá nhân",
            [80],
            base._value(81, "1.109.262.426"),
            "One printed value combines private enterprises and individuals, so it cannot be allocated between 1083 and 1089.",
        ),
    ]
    return _standard_document(
        base,
        code="BID",
        page=51,
        rows=rows,
        owner_total=(46, "2.222.991.628"),
        customer_specs=customers,
        customer_total=(91, "2.222.991.628"),
        unresolved=unresolved,
    )


def _vib(base: ModuleType) -> dict[str, Any]:
    v, m, e = base._value, base._mapping, base._equation
    mappings = [
        m(1057, "NO_TERM", 46, "Tiền gửi không kỳ hạn", [12], [v(13, "42.377.916")]),
        m(
            1058,
            "NO_TERM_VND",
            46,
            "Tiền gửi không kỳ hạn bằng VND gồm tiết kiệm",
            [15, 18],
            [v(16, "37.871.705"), v(19, "1.459")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        m(
            1059,
            "NO_TERM_FOREIGN",
            46,
            "Tiền gửi không kỳ hạn bằng ngoại tệ gồm tiết kiệm",
            [21, 24],
            [v(22, "4.504.360"), v(25, "392")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        m(1060, "TERM", 46, "Tiền gửi có kỳ hạn", [27], [v(28, "251.612.097")]),
        m(
            1061,
            "TERM_VND",
            46,
            "Tiền gửi có kỳ hạn bằng VND gồm tiết kiệm",
            [30, 33],
            [v(31, "125.104.053"), v(34, "108.898.034")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        m(
            1062,
            "TERM_FOREIGN",
            46,
            "Tiền gửi có kỳ hạn bằng ngoại tệ gồm tiết kiệm",
            [36, 39],
            [v(37, "1.234.633"), v(40, "16.375.377")],
            aggregation="SUM_REGULAR_AND_NESTED_SAVINGS",
        ),
        m(
            1063,
            "SAVINGS",
            46,
            "Tiền gửi tiết kiệm",
            [18, 24, 33, 39],
            [v(19, "1.459"), v(25, "392"), v(34, "108.898.034"), v(40, "16.375.377")],
            aggregation="SUM_NESTED_SAVINGS_ROWS",
            additivity="NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM",
        ),
        m(
            1064,
            "SAVINGS_VND",
            46,
            "Tiền gửi tiết kiệm bằng VND",
            [18, 33],
            [v(19, "1.459"), v(34, "108.898.034")],
            aggregation="SUM_NESTED_SAVINGS_ROWS",
            additivity="NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM",
        ),
        m(
            1065,
            "SAVINGS_FOREIGN",
            46,
            "Tiền gửi tiết kiệm bằng ngoại tệ",
            [24, 39],
            [v(25, "392"), v(40, "16.375.377")],
            aggregation="SUM_NESTED_SAVINGS_ROWS",
            additivity="NONADDITIVE_SUBSET_OF_NO_TERM_AND_TERM",
        ),
        m(1069, "DEDICATED", 46, "Tiền gửi vốn chuyên dùng", [42], [v(43, "124.984")]),
        m(1070, "DEDICATED_VND", 46, "Tiền gửi vốn chuyên dùng bằng VND", [45], [v(46, "95.560")]),
        m(
            1071,
            "DEDICATED_FOREIGN",
            46,
            "Tiền gửi vốn chuyên dùng bằng ngoại tệ",
            [48],
            [v(49, "29.424")],
        ),
        m(1066, "ESCROW", 46, "Tiền gửi ký quỹ", [52], [v(53, "462.664")]),
        m(1067, "ESCROW_VND", 46, "Tiền gửi ký quỹ bằng VND", [55], [v(56, "453.986")]),
        m(1068, "ESCROW_FOREIGN", 46, "Tiền gửi ký quỹ bằng ngoại tệ", [59], [v(60, "8.678")]),
        _customer_mapping(
            base,
            5977,
            "CUSTOMER_TCKT",
            47,
            "Tiền gửi của các tổ chức kinh tế",
            [14],
            [(15, "103.570.002")],
            additivity="NONADDITIVE_GROUP_PARENT_FOR_DETAIL_CONTROL",
        ),
    ]
    specs = [
        (1076, "STATE_COMPANY", "Công ty nhà nước", [19], 20, "14.679.689"),
        (
            1078,
            "STATE_100_TNHH",
            "Công ty TNHH MTV do nhà nước sở hữu 100% vốn điều lệ",
            [24, 25],
            26,
            "2.484.176",
        ),
        (
            770,
            "STATE_OVER_50_MULTI_MEMBER_TNHH",
            "Công ty TNHH 2 thành viên trở lên có phần vốn góp của nhà nước trên 50%",
            [30, 31, 32],
            33,
            "508",
        ),
        (1080, "OTHER_TNHH", "Công ty TNHH khác", [37], 38, "16.684.638"),
        (
            1081,
            "STATE_OVER_50_JSC",
            "Công ty cổ phần có vốn nhà nước trên 50%",
            [42, 43, 44, 45, 46],
            47,
            "6.504.281",
        ),
        (1082, "OTHER_JSC", "Công ty cổ phần khác", [51], 52, "47.903.888"),
        (1087, "PARTNERSHIP", "Công ty hợp danh", [56], 57, "849"),
        (1083, "PRIVATE_ENTERPRISE", "Doanh nghiệp tư nhân", [61], 62, "76.776"),
        (1088, "FOREIGN_INVESTED", "Doanh nghiệp có vốn đầu tư nước ngoài", [66], 67, "13.198.445"),
        (1085, "COOPERATIVE", "Hợp tác xã và liên hiệp hợp tác xã", [71], 72, "43.602"),
        (
            1090,
            "ADMIN_ASSOCIATION",
            "Đơn vị hành chính sự nghiệp, đảng, đoàn thể và hiệp hội",
            [81, 82],
            83,
            "1.956.388",
        ),
    ]
    mappings.extend(
        _customer_mapping(base, i, role, 47, label, lines, [(value_line, value)])
        for i, role, label, lines, value_line, value in specs
    )
    mappings.append(
        _customer_mapping(
            base,
            1089,
            "HOUSEHOLD_INDIVIDUAL",
            47,
            "Hộ kinh doanh và tiền gửi của cá nhân",
            [76, 87],
            [(77, "36.762"), (88, "191.007.659")],
            aggregation="SUM_OF_VISIBLE_HOUSEHOLD_AND_INDIVIDUAL_ROWS",
        )
    )
    equations = [
        e(
            "NO_TERM_INCLUDES_REGULAR_AND_SAVINGS_CURRENCY_ROWS",
            46,
            [v(16, "37.871.705"), v(19, "1.459"), v(22, "4.504.360"), v(25, "392")],
            v(13, "42.377.916"),
        ),
        e(
            "TERM_INCLUDES_REGULAR_AND_SAVINGS_CURRENCY_ROWS",
            46,
            [v(31, "125.104.053"), v(34, "108.898.034"), v(37, "1.234.633"), v(40, "16.375.377")],
            v(28, "251.612.097"),
        ),
        e("DEDICATED_CURRENCY_SUM", 46, [v(46, "95.560"), v(49, "29.424")], v(43, "124.984")),
        e("ESCROW_CURRENCY_SUM", 46, [v(56, "453.986"), v(60, "8.678")], v(53, "462.664")),
        e(
            "OWNER_TOTAL_EXCLUDES_NESTED_SAVINGS_DOUBLE_COUNT",
            46,
            [v(13, "42.377.916"), v(28, "251.612.097"), v(43, "124.984"), v(53, "462.664")],
            v(63, "294.577.661"),
        ),
        e(
            "TCKT_DETAIL_TOTAL",
            47,
            [v(value_line, value) for _, _, _, _, value_line, value in specs] + [v(77, "36.762")],
            v(15, "103.570.002"),
        ),
        e(
            "CUSTOMER_TYPE_TOTAL",
            47,
            [v(15, "103.570.002"), v(88, "191.007.659")],
            v(92, "294.577.661"),
        ),
    ]
    return base._doc(
        "VIB",
        [46, 47],
        "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS_WITH_NESTED_SAVINGS_AND_CROSS_PAGE_CUSTOMER_TYPE",
        "2025-12-31",
        mappings,
        equations,
        customer_type_subview="MAPPED_CROSS_PAGE_DETAILED_CUSTOMER_TYPE_SUBTABLE",
    )


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    return [
        _acb(base),
        _mbb(base),
        _vpb(base),
        _hdb(base),
        _vcb(base),
        _ctg(base),
        _bid(base),
        _vib(base),
    ]


def _configure_base() -> ModuleType:
    base = _load_module(
        "annual_2025_customer_deposit_mapping_base",
        "scripts/experiments/build_customer_deposit_8bank_codex_verified_mapping_v1.py",
    )
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
    base._COMPARISON_PERIOD_EXCLUDED = "31/12/2024"
    base._review_documents = lambda: _review_documents(base)
    base._source_period_status = lambda source_period: (
        "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_PERIOD"
        if source_period == "2025-12-31"
        else (_ for _ in ()).throw(_error("annual customer-deposit source period drifted"))
    )

    def annual_schema_binding(item: Any) -> dict[str, Any]:
        if (
            item is None
            or item.statement_type != "TM"
            or not (
                (1057 <= item.schema_id < 1092 and item.parent_id in {1056, 1075})
                or (item.schema_id == 5977 and item.parent_id == 1075)
                or (item.schema_id == 770 and item.parent_id == 766)
            )
        ):
            raise _error("annual customer-deposit mapping does not bind an approved live TM item")
        return {
            "canonical_name": item.canonical_name,
            "display_order": item.display_order,
            "hierarchy_level": item.hierarchy_level,
            "report_norm_id": item.schema_id,
            "schema_parent_report_norm_id": item.parent_id,
        }

    base._schema_binding = annual_schema_binding
    return base


def _validate_expected(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual customer-deposit metrics drifted")
    trials = value.get("trials")
    if type(trials) is not list or len(trials) != 8:
        raise _error("annual customer-deposit trial denominator drifted")
    for trial in trials:
        if (
            trial.get("source_period") != "2025-12-31"
            or trial.get("source_period_status")
            != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_PERIOD"
            or trial.get("whole_document_uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ):
            raise _error("annual customer-deposit period or uniqueness drifted")
        actual = {mapping["report_norm_id"] for mapping in trial["verified_mappings"]}
        if actual != _EXPECTED_IDS[trial["document_provenance"]]:
            raise _error(
                f"annual customer-deposit schema coverage drifted: {trial['document_provenance']}"
            )
    return value


def build_annual_2025_customer_deposit_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _configure_base()._review_blueprint()


def build_live_annual_2025_customer_deposit_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        base = _configure_base()
        semantic_index, _ = base._fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
        crop_manifest, crop_bytes = base._fixed_json(
            CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256
        )
        review = base._review_blueprint()
        scan = base._scanner().build_customer_deposit_full_document_scan_v1(semantic_index)
        schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
        return _validate_expected(
            base.build_customer_deposit_8bank_codex_verified_mapping_v1(
                semantic_index,
                crop_manifest,
                scan,
                review,
                schema_authority,
                schema_by_id,
                crop_manifest_sha256=base.hashlib.sha256(crop_bytes).hexdigest(),
                review_sha256=base.hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest(),
            )
        )
    except Annual2025CustomerDeposit8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_customer_deposit_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _configure_base()._validate_result(value)
    rebuilt = build_live_annual_2025_customer_deposit_8bank_codex_verified_mapping_v1()
    if supplied != rebuilt:
        raise _error("annual customer-deposit result does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    base = _configure_base()
    if args.write_review:
        base.REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        base.REVIEW_PATH.write_bytes(canonical_json_bytes_v1(base._review_blueprint()))
    result = build_live_annual_2025_customer_deposit_8bank_codex_verified_mapping_v1()
    if args.write_result:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
    elif args.verify:
        persisted, _ = base._fixed_json(RESULT_PATH)
        validate_annual_2025_customer_deposit_8bank_codex_verified_mapping_replay_v1(persisted)
        print(persisted["result_id"])
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
