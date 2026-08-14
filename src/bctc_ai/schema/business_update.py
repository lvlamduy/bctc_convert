from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from bctc_ai.core.atomic import atomic_write_bytes, atomic_write_json
from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.xlsx_reader import read_rows

if TYPE_CHECKING:
    from bctc_ai.schema.registry import SchemaItem


BUSINESS_UPDATE_AUDIT = "data/registered/schema_business_update_5712_5713_5714_5718_6060.json"
PRIOR_BUSINESS_UPDATE_AUDIT = "data/registered/schema_business_update_5712_5713_5714_5718_6056.json"
PRIOR_BUSINESS_UPDATE_AUDIT_SHA256 = (
    "7a3ead7aa1e0c3b998c5d597d8014379592488927525270998cfd9cc2ff7385b"
)

CDKT_BASELINE_WORKBOOK = "template/Bank_CDKT_ReportNormId.xlsx"
KQKD_BASELINE_WORKBOOK = "template/Bank_KQKD_ReportNormId.xlsx"
LCTT_BASELINE_WORKBOOK = "template/Bank_LCTT_ReportNormId.xlsx"
TM_BASELINE_WORKBOOK = "template/Bank_TM_ReportNormId.xlsx"
CDKT_WORKBOOK = "template/Bank_CDKT_ReportNormId.v2.xlsx"
KQKD_WORKBOOK = "template/Bank_KQKD_ReportNormId.v2.xlsx"
LCTT_WORKBOOK = "template/Bank_LCTT_ReportNormId.v2.xlsx"
TM_WORKBOOK = "template/Bank_TM_ReportNormId.v2.xlsx"

CDKT_BEFORE_SHA256 = "a07ff47f7c41011fe4ca5a66681106d476586ded9013b5874cbb9f67a6ad8486"
KQKD_BEFORE_SHA256 = "6033001b85a236fce4b29437d56cc02d7c6a21f95e82b43de043b1268eb74615"
LCTT_BEFORE_SHA256 = "2c9d52737c492f115895eab9a571da2269fcfd3c3e77539ec581782e579d260a"
TM_BEFORE_SHA256 = "fa284e3af1f90c8a206308f63e6d35e77a9fbf1abcaf60abcb59877c47275140"

CDKT_BEFORE_ROW_COUNT = 78
KQKD_BEFORE_ROW_COUNT = 25
CDKT_AFTER_ROW_COUNT = 100
KQKD_AFTER_ROW_COUNT = 26
LCTT_BEFORE_ROW_COUNT = 108
LCTT_AFTER_ROW_COUNT = 111
TM_BEFORE_ROW_COUNT = 1386
TM_AFTER_ROW_COUNT = 1706

BASE_SCHEMA_ITEM_COUNT = 1593
PRIOR_UNIVERSAL_SCHEMA_ITEM_COUNT = 1935
UNIVERSAL_SCHEMA_ITEM_COUNT = 1939
PRIOR_UNIVERSAL_HIGH_WATERMARK = 6056
UNIVERSAL_HIGH_WATERMARK = 6060

PRIOR_UNIVERSAL_WORKBOOK_SHA256 = {
    "CDKT": "7f871941516d4591417f0f3f018bceb5fd6d91e474a0570f84eaeb141d24531c",
    "KQKD": "f860ff4267054e1dea330f91de498bd2a835fd77f824a5dc444abb412a6346c8",
    "LCTT": "dee9f2065b03da349c9c96174fc2affd7d86c2439c916d246164a2d4d67a5bc8",
    "TM": "82215c17f6d0aba33c01b03d6af76cc80ad53e0b129bf101f7e0b266cc9ea28f",
}
PRIOR_UNIVERSAL_IDENTITY_ORDER_SHA256 = {
    "CDKT": "da32848b4583ef3fc222be91d328a4a5cd062e8175fbd09659d1fc0385558f2a",
    "KQKD": "d96e239b125c07253fd7646c18db31b4c1ac4ee3ef662fbd787c151906f82693",
    "LCTT": "32a995a3d11af834e86dda84bcea639303197eebd148fa73be495b7ac89e345f",
    "TM": "46a31cab2ba33a15a666ed2ca3e974adbcf4298e1c0e17b04213e5d21979ec32",
}

PREVIOUS_V2_SHA256 = {
    "CDKT": (
        "2289c0ff2e988c36131f2b4e5675efc1d9ca40776c72439ef205aae43103951f",
        "8db357163a74826091552e3481698fcb2ed16a2eb45d60d2d3f96c1a18617f3a",
        "7f871941516d4591417f0f3f018bceb5fd6d91e474a0570f84eaeb141d24531c",
    ),
    "KQKD": (
        "12908b0acb8970e37f382f79898b7d2124079e1e16bab17d8e03811a7004cd52",
        "f860ff4267054e1dea330f91de498bd2a835fd77f824a5dc444abb412a6346c8",
    ),
    "LCTT": (
        "aa0f4912b1e343e404bc2490f6fe628db6b7980a180c6d03e27633b993afeb41",
        "0b61441567efff7b361d59dc31ac662e52f9f815c2c2e463236b5fc6b4af3257",
        "d1c277468eea7b8db754ee771d615278da3e307004e5d91f2c90418e21ab4493",
        "dee9f2065b03da349c9c96174fc2affd7d86c2439c916d246164a2d4d67a5bc8",
    ),
    "TM": (
        "bcffd9baa04a3e3aad1c80ce867e38b0145626969409213122ec3d1c0cd8451c",
        "71020164042f5c238677b14b6964be0e5864d011a658e461fc2653a3d3644571",
        "c94576df570e88ab86743dd29579c3bbe8578f566728ca60c8031c731bcc581e",
        "3436883c1880220a91d829a748d7c37e0279e82a43c79f49b25acf7737af44f5",
        "ea5b690e88c2986613e650663eaea3e05860053c5f56e6445d19e6f0a719a8e1",
        "b77ad754bb0162beec9c600dd0b91ca8750075bb96c3263b0d8640bdf02d37b0",
        "82215c17f6d0aba33c01b03d6af76cc80ad53e0b129bf101f7e0b266cc9ea28f",
    ),
}

CDKT_TOTAL_EQUITY_ID = 5712
CDKT_TOTAL_EQUITY_NAME = "TỔNG VỐN CHỦ SỞ HỮU"
CDKT_TOTAL_EQUITY_SOURCE_ROW = 78
CDKT_TOTAL_EQUITY_DISPLAY_ORDER = 76
CDKT_TOTAL_EQUITY_FINAL_SOURCE_ROW = 81
CDKT_TOTAL_EQUITY_FINAL_DISPLAY_ORDER = 79
CDKT_TOTAL_EQUITY_PREDECESSOR_ID = 4306
CDKT_TOTAL_EQUITY_SUCCESSOR_ID = 4305

KQKD_TOTAL_OPERATING_INCOME_ID = 5713
KQKD_TOTAL_OPERATING_INCOME_NAME = "TỔNG THU NHẬP HOẠT ĐỘNG"
KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW = 15
KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER = 13
KQKD_TOTAL_OPERATING_INCOME_PREDECESSOR_ID = 4393
KQKD_TOTAL_OPERATING_INCOME_SUCCESSOR_ID = 4391

LCTT_INVESTMENT_CONTRIBUTION_NET_ID = 5714
LCTT_INVESTMENT_CONTRIBUTION_NET_NAME = "Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác"
LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW = 94
LCTT_INVESTMENT_CONTRIBUTION_NET_DISPLAY_ORDER = 92
LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_SOURCE_ROW = 95
LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_DISPLAY_ORDER = 93
LCTT_INVESTMENT_CONTRIBUTION_NET_PREDECESSOR_ID = 4146
LCTT_INVESTMENT_CONTRIBUTION_NET_SUCCESSOR_ID = 4120

LCTT_INVESTMENT_PROPERTY_NET_ID = 6034
LCTT_INVESTMENT_PROPERTY_NET_NAME = "Tiền thu/(chi) bất động sản đầu tư"
LCTT_INVESTMENT_PROPERTY_NET_SOURCE_ROW = 90
LCTT_INVESTMENT_PROPERTY_NET_DISPLAY_ORDER = 88
LCTT_INVESTMENT_PROPERTY_NET_FINAL_SOURCE_ROW = 91
LCTT_INVESTMENT_PROPERTY_NET_FINAL_DISPLAY_ORDER = 89
LCTT_INVESTMENT_PROPERTY_NET_PREDECESSOR_ID = 4143
LCTT_INVESTMENT_PROPERTY_NET_SUCCESSOR_ID = 4144

VPB_PDF_SHA256 = "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
VPB_PDF_PATH = "vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf"
VPB_NATIVE_ROWS_SHA256 = "fa1c5d1cbc0237b2fc7c65791857b21e6f6884d2acbe9fc2a17d0da5e661521f"
VPB_NATIVE_ROWS_PATH = "output/development/vpb-q1-2026-native-rows-v1/statement-rows.json"

CTG_PDF_SHA256 = "f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318"
CTG_PDF_PATH = "vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf"
CTG_REVIEW_PATH = "reference/human_review/reviewed-mapping-corrections-2026-08-06.yaml"
CTG_REVIEW_SHA256 = "32c86c0bf7642d3bd7596225331fc6f10906970476e1a9ba982b2f478d0f8e74"

CDKT_OFF_BALANCE_TOTAL_ID = 6055
CDKT_OFF_BALANCE_TOTAL_NAME = "Tổng chỉ tiêu ngoại bảng"
CDKT_OFF_BALANCE_TOTAL_COMPONENTS = (6039, 6050)
CDKT_SWAP_COMMITMENT_TOTAL_ID = 6056
CDKT_SWAP_COMMITMENT_TOTAL_NAME = "Cam kết giao dịch hoán đổi"
CDKT_SWAP_COMMITMENT_TOTAL_COMPONENTS = (6044, 6045)
CDKT_CURRENT_SCHEMA_IDS = (
    CDKT_OFF_BALANCE_TOTAL_ID,
    CDKT_SWAP_COMMITMENT_TOTAL_ID,
)

CDKT_VPB_SCHEMA_ITEMS: tuple[
    tuple[int, str, int | None, int, str, int, str, tuple[str, str]], ...
] = (
    (
        6035,
        "Dự phòng rủi ro chứng khoán kinh doanh",
        4313,
        3,
        "BALANCE_SHEET_ASSETS",
        5,
        "page-0005:row-0009",
        ("(516.155)", "(172.266)"),
    ),
    (
        6036,
        "Dự phòng rủi ro chứng khoán đầu tư",
        4316,
        3,
        "BALANCE_SHEET_ASSETS",
        5,
        "page-0005:row-0018",
        ("(27.063)", "(28.864)"),
    ),
    (
        6037,
        "Tiền gửi và vay Chính phủ, NHNN",
        4318,
        4,
        "BALANCE_SHEET_LIABILITIES",
        6,
        "page-0006:row-0003",
        ("1.063.456", "15.305"),
    ),
    (
        6038,
        "CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
        None,
        0,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:heading",
        ("", ""),
    ),
    (
        6039,
        "Nghĩa vụ nợ tiềm ẩn",
        CDKT_OFF_BALANCE_TOTAL_ID,
        2,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0001",
        ("973.264.004", "1.050.492.773"),
    ),
    (
        6040,
        "Bảo lãnh vay vốn",
        6039,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0002",
        ("11.447.240", "11.447.240"),
    ),
    (
        6041,
        "Cam kết giao dịch hối đoái",
        6039,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0003",
        ("449.827.549", "545.548.780"),
    ),
    (
        6042,
        "- Cam kết mua ngoại tệ",
        6041,
        4,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0004",
        ("2.130.153", "6.965.590"),
    ),
    (
        6043,
        "- Cam kết bán ngoại tệ",
        6041,
        4,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0005",
        ("758.614", "9.281.743"),
    ),
    (
        6044,
        "- Cam kết nhận - giao dịch hoán đổi tiền tệ",
        CDKT_SWAP_COMMITMENT_TOTAL_ID,
        5,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0006",
        ("223.330.657", "264.549.403"),
    ),
    (
        6045,
        "- Cam kết trả - giao dịch hoán đổi tiền tệ",
        CDKT_SWAP_COMMITMENT_TOTAL_ID,
        5,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0007",
        ("223.608.125", "264.752.043"),
    ),
    (
        6046,
        "Cam kết trong nghiệp vụ L/C",
        6039,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0008",
        ("21.894.766", "19.751.533"),
    ),
    (
        6047,
        "Bảo lãnh khác",
        6039,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0009",
        ("47.666.649", "50.911.375"),
    ),
    (
        6048,
        "Các cam kết khác",
        6039,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0010",
        ("442.427.800", "422.833.846"),
    ),
    (
        6049,
        "Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang",
        6048,
        4,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0011",
        ("317.838.201", "294.728.542"),
    ),
    (
        6050,
        "Các khoản mục ngoại bảng khác",
        CDKT_OFF_BALANCE_TOTAL_ID,
        2,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0012",
        ("331.492.775", "316.568.156"),
    ),
    (
        6051,
        "Lãi cho vay và phí phải thu chưa thu được",
        6050,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0013",
        ("6.791.073", "6.286.715"),
    ),
    (
        6052,
        "Nợ khó đòi đã xử lý",
        6050,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0014",
        ("127.239.935", "116.784.980"),
    ),
    (
        6053,
        "Tài sản và chứng từ khác",
        6050,
        3,
        "OFF_BALANCE_SHEET",
        7,
        "page-0007:row-0015",
        ("197.461.767", "193.496.461"),
    ),
)
CDKT_VPB_SCHEMA_IDS = tuple(record[0] for record in CDKT_VPB_SCHEMA_ITEMS)
CDKT_OFF_BALANCE_DISPLAY_SEQUENCE = (
    6038,
    6039,
    6040,
    6041,
    6042,
    6043,
    CDKT_SWAP_COMMITMENT_TOTAL_ID,
    6044,
    6045,
    6046,
    6047,
    6048,
    6049,
    6050,
    6051,
    6052,
    6053,
    CDKT_OFF_BALANCE_TOTAL_ID,
)
CDKT_CUMULATIVE_DISPLAY_ORDERS = {
    6035: 9,
    6036: 21,
    6037: 51,
    **{schema_id: 81 + index for index, schema_id in enumerate(CDKT_OFF_BALANCE_DISPLAY_SEQUENCE)},
}
CDKT_CUMULATIVE_DISPLAY_ANCHORS = {
    6035: (4346, 4347),
    6036: (4351, 4352),
    6037: (4318, 4319),
    6038: (4305, 6039),
    **{
        schema_id: (
            CDKT_OFF_BALANCE_DISPLAY_SEQUENCE[index - 1],
            (
                CDKT_OFF_BALANCE_DISPLAY_SEQUENCE[index + 1]
                if index + 1 < len(CDKT_OFF_BALANCE_DISPLAY_SEQUENCE)
                else None
            ),
        )
        for index, schema_id in enumerate(CDKT_OFF_BALANCE_DISPLAY_SEQUENCE)
        if index > 0
    },
}
# Compatibility names retained for callers that need the earlier VPB-only set.
CDKT_VPB_DISPLAY_ORDERS = {
    schema_id: CDKT_CUMULATIVE_DISPLAY_ORDERS[schema_id] for schema_id in CDKT_VPB_SCHEMA_IDS
}
CDKT_VPB_DISPLAY_ANCHORS = {
    schema_id: CDKT_CUMULATIVE_DISPLAY_ANCHORS[schema_id] for schema_id in CDKT_VPB_SCHEMA_IDS
}

LCTT_VPB_COMBINED_LOAN_ID = 6054
LCTT_VPB_COMBINED_LOAN_NAME = "Tăng, giảm các khoản cho vay khách hàng và mua nợ"
LCTT_VPB_COMBINED_LOAN_PARENT_ID = 4107
LCTT_VPB_COMBINED_LOAN_HIERARCHY_LEVEL = 2
LCTT_VPB_COMBINED_LOAN_PREDECESSOR_ID = 4132
LCTT_VPB_COMBINED_LOAN_SUCCESSOR_ID = 4133
LCTT_VPB_COMBINED_LOAN_DISPLAY_ORDER = 72
LCTT_VPB_COMBINED_LOAN_SOURCE_ROW = 74

KQKD_4382_OLD_NAME = "Thuế Thu nhập doanh nghiệp phải nộp"
KQKD_4382_CORRECTED_NAME = "Tổng chi phí thuế thu nhập doanh nghiệp"
LCTT_4109_OLD_NAME = "Lợi nhuận từ hoạt động kinh doanh trước thay đổi vốn lưu động"
LCTT_4109_CORRECTED_NAME = (
    "Lưu chuyển tiền thuần từ hoạt động kinh doanh trước những thay đổi về tài sản "
    "và nợ phải trả hoạt động"
)

TM_TOTAL_INTERBANK_PROVISION_ID = 5718
TM_TOTAL_INTERBANK_PROVISION_NAME = (
    "Tổng dự phòng rủi ro tiền gửi và cho vay các tổ chức tín dụng khác"
)
TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW = 34
TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER = 32
TM_TOTAL_INTERBANK_PROVISION_PREDECESSOR_ID = 591
TM_TOTAL_INTERBANK_PROVISION_SUCCESSOR_ID = 592

TM_EDUCATION_ID = 737
TM_EDUCATION_OLD_NAME = " + Giáo dục và đào tạo, y tế"
TM_EDUCATION_NAME = "Giáo dục & Đào tạo"
TM_EDUCATION_BASELINE_SOURCE_ROW = 179

TM_HEALTH_SOCIAL_ID = 5719
TM_HEALTH_SOCIAL_NAME = "Y tế & hoạt động trợ giúp xã hội"
TM_HEALTH_SOCIAL_SOURCE_ROW = 182
TM_HEALTH_SOCIAL_DISPLAY_ORDER = 180
TM_HEALTH_SOCIAL_PREDECESSOR_ID = TM_EDUCATION_ID
TM_HEALTH_SOCIAL_SUCCESSOR_ID = 738

TM_ARTS_RECREATION_ID = 5720
TM_ARTS_RECREATION_NAME = "Ngành nghệ thuật vui chơi giải trí"
TM_ARTS_RECREATION_SOURCE_ROW = 189
TM_ARTS_RECREATION_DISPLAY_ORDER = 187
TM_ARTS_RECREATION_PREDECESSOR_ID = 743
TM_ARTS_RECREATION_SUCCESSOR_ID = 5721

TM_OTHER_SERVICES_ID = 5721
TM_OTHER_SERVICES_NAME = "Ngành hoạt động dịch vụ khác"
TM_OTHER_SERVICES_SOURCE_ROW = 190
TM_OTHER_SERVICES_DISPLAY_ORDER = 188
TM_OTHER_SERVICES_PREDECESSOR_ID = 5720
TM_OTHER_SERVICES_SUCCESSOR_ID = 5722

TM_HOUSEHOLD_EMPLOYMENT_ID = 5722
TM_HOUSEHOLD_EMPLOYMENT_NAME = (
    "Ngành hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất sản phẩm "
    "vật chất và dịch vụ tự tiêu dùng của hộ gia đình"
)
TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW = 191
TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER = 189
TM_HOUSEHOLD_EMPLOYMENT_PREDECESSOR_ID = 5721
TM_HOUSEHOLD_EMPLOYMENT_SUCCESSOR_ID = 744

TM_PURCHASED_PRINCIPAL_ID = 5738
TM_PURCHASED_PRINCIPAL_NAME = "Nợ gốc đã mua"
TM_PURCHASED_PRINCIPAL_SOURCE_ROW = 257
TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER = 255
TM_PURCHASED_PRINCIPAL_PREDECESSOR_ID = 803
TM_PURCHASED_PRINCIPAL_SUCCESSOR_ID = 5739

TM_PURCHASED_INTEREST_ID = 5739
TM_PURCHASED_INTEREST_NAME = "Lãi của khoản nợ đã mua"
TM_PURCHASED_INTEREST_SOURCE_ROW = 258
TM_PURCHASED_INTEREST_DISPLAY_ORDER = 256
TM_PURCHASED_INTEREST_PREDECESSOR_ID = 5738
TM_PURCHASED_INTEREST_SUCCESSOR_ID = 804

TM_GOVERNMENT_GUARANTEED_DEBT_ID = 5740
TM_GOVERNMENT_GUARANTEED_DEBT_NAME = "Chứng khoán nợ do Chính phủ bảo lãnh"
TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW = 263
TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER = 261
TM_GOVERNMENT_GUARANTEED_DEBT_PREDECESSOR_ID = 807
TM_GOVERNMENT_GUARANTEED_DEBT_SUCCESSOR_ID = 808

TM_FX_BUY_ID = 5741
TM_FX_BUY_NAME = "Cam kết mua ngoại tệ"
TM_FX_BUY_SOURCE_ROW = 779
TM_FX_BUY_DISPLAY_ORDER = 777
TM_FX_BUY_PREDECESSOR_ID = 1301
TM_FX_BUY_SUCCESSOR_ID = 5742

TM_FX_SELL_ID = 5742
TM_FX_SELL_NAME = "Cam kết bán ngoại tệ"
TM_FX_SELL_SOURCE_ROW = 780
TM_FX_SELL_DISPLAY_ORDER = 778
TM_FX_SELL_PREDECESSOR_ID = 5741
TM_FX_SELL_SUCCESSOR_ID = 1302

TM_SWAP_BUY_ID = 5743
TM_SWAP_BUY_NAME = "Cam kết mua giao dịch hoán đổi tiền tệ"
TM_SWAP_BUY_SOURCE_ROW = 782
TM_SWAP_BUY_DISPLAY_ORDER = 780
TM_SWAP_BUY_PREDECESSOR_ID = 1302
TM_SWAP_BUY_SUCCESSOR_ID = 5744

TM_SWAP_SELL_ID = 5744
TM_SWAP_SELL_NAME = "Cam kết bán giao dịch hoán đổi tiền tệ"
TM_SWAP_SELL_SOURCE_ROW = 783
TM_SWAP_SELL_DISPLAY_ORDER = 781
TM_SWAP_SELL_PREDECESSOR_ID = 5743
TM_SWAP_SELL_SUCCESSOR_ID = 1303

TM_MARGIN_LOAN_CANONICAL_NAME = "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
TM_MARGIN_LOAN_TYPE_ID = 5745
TM_MARGIN_LOAN_TYPE_SOURCE_ROW = 170
TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER = 168
TM_MARGIN_LOAN_TYPE_PREDECESSOR_ID = 726
TM_MARGIN_LOAN_TYPE_SUCCESSOR_ID = 727

TM_MARGIN_LOAN_QUALITY_ID = 5746
TM_MARGIN_LOAN_QUALITY_NAME = "Trong đó: Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
TM_MARGIN_LOAN_QUALITY_SOURCE_ROW = 197
TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER = 195
TM_MARGIN_LOAN_QUALITY_PREDECESSOR_ID = 747
TM_MARGIN_LOAN_QUALITY_SUCCESSOR_ID = 748

TM_MARGIN_LOAN_MATURITY_ID = 5747
TM_MARGIN_LOAN_MATURITY_SOURCE_ROW = 206
TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER = 204
TM_MARGIN_LOAN_MATURITY_PREDECESSOR_ID = 755
TM_MARGIN_LOAN_MATURITY_SUCCESSOR_ID = 756

TM_MARGIN_LOAN_BUSINESS_ID = 5748
TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW = 235
TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER = 233
TM_MARGIN_LOAN_BUSINESS_PREDECESSOR_ID = 782
TM_MARGIN_LOAN_BUSINESS_SUCCESSOR_ID = 783

TM_MARGIN_LOAN_INDUSTRY_ID = 5749
TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW = 194
TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER = 192
TM_MARGIN_LOAN_INDUSTRY_PREDECESSOR_ID = 745
TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID = 746

TM_PAGE50_TAX_INSERT_SOURCE_ROW = 706
TM_PAGE50_TAX_INSERT_DISPLAY_ORDER = 704
TM_PAGE50_TAX_SCHEMA_ITEMS: tuple[tuple[int, str], ...] = (
    (5723, "Chi phí thuế thu nhập hiện hành"),
    (5724, "Năm hiện hành"),
    (5725, "Chi phí/(hoàn nhập) thuế thu nhập hoãn lại"),
    (5726, "Chi phí/(thu nhập) thuế thu nhập hoãn lại"),
    (5727, "Chi phí thuế thu nhập"),
    (5728, "Tổng lợi nhuận theo kế toán trước thuế hợp nhất"),
    (
        5729,
        "Thu nhập không chịu thuế (bao gồm cổ tức, lợi nhuận từ các đơn vị, các khoản "
        "điều chỉnh hợp nhất không chịu thuế) và các khoản khác",
    ),
    (5730, "Các chi phí không được khấu trừ của riêng Ngân hàng"),
    (5731, "Thu nhập chịu thuế TNDN ước tính tại Việt Nam"),
    (5732, "Chi phí thuế TNDN hiện hành riêng Ngân hàng (i)"),
    (
        5733,
        "Điều chỉnh trong năm cho thuế thu nhập hiện hành của các năm trước (ii)",
    ),
    (5734, "Chi phí thuế TNDN chi nhánh nước ngoài (iii)"),
    (5735, "Chi phí thuế TNDN của các công ty con (iv)"),
    (5736, "Chi phí/(hoàn nhập) thuế TNDN hoãn lại (v)"),
    (5737, "Chi phí thuế TNDN (i+ii+iii+iv+v)"),
)
TM_PAGE50_TAX_SCHEMA_IDS = tuple(schema_id for schema_id, _name in TM_PAGE50_TAX_SCHEMA_ITEMS)
TM_PAGE50_TAX_PREDECESSOR_ID = 1246
TM_PAGE50_TAX_SUCCESSOR_ID = 1247

# Page 52 additions use the proposal-key allocation order frozen by the page
# mapper.  Source rows and display orders describe the final workbook after all
# additions in this migration have been inserted.  The deposit-geography branch
# follows the complete 1075 subtree (through 1091), preserving flattened-tree
# order rather than splitting the pre-existing branch.
TM_PAGE52_SCHEMA_ITEMS: tuple[tuple[int, str, int, int, int, int], ...] = (
    (5750, "Giao dịch với các bên liên quan", 786, 784, 1259, 1),
    (5751, "Giao dịch tiền gửi tại MB", 787, 785, 5750, 2),
    (5752, "+ Trong nước", 211, 209, 759, 3),
    (5753, "Phân tích theo khu vực địa lý", 548, 546, 1055, 2),
    (5754, "+ Trong nước", 549, 547, 5753, 3),
    (5755, "+ Nước ngoài", 550, 548, 5753, 3),
    (5756, "Phân tích theo khu vực địa lý", 770, 768, 1295, 3),
    (5757, "+ Trong nước", 771, 769, 5756, 4),
    (5758, "+ Nước ngoài", 772, 770, 5756, 4),
    (5759, "Kinh doanh và đầu tư chứng khoán", 788, 786, 1259, 1),
    (5760, "+ Trong nước", 789, 787, 5759, 2),
    (5761, "+ Nước ngoài", 790, 788, 5759, 2),
)
TM_PAGE52_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE52_SCHEMA_ITEMS)

TM_PAGE53_OVERALL_ROOT_ID = 5762
TM_PAGE53_GEOGRAPHIC_ROOT_ID = 5763
TM_PAGE53_AXIS_NAMES = (
    "Miền Bắc",
    "Miền Trung",
    "Miền Nam",
    "Khu vực khác",
    "Loại trừ/Phân loại",
    "Tổng cộng",
)
TM_PAGE53_METRIC_NAMES = (
    "Tài sản",
    "Nợ phải trả",
    "Tài sản cố định",
    "Doanh thu",
    "Chi phí",
    "Lợi nhuận trước thuế",
)


def _page53_schema_items() -> tuple[tuple[int, str, int, int, int, int], ...]:
    records: list[tuple[int, str, int, int, int, int]] = [
        (
            TM_PAGE53_OVERALL_ROOT_ID,
            "Báo cáo bộ phận hợp nhất",
            791,
            789,
            1259,
            1,
        ),
        (
            TM_PAGE53_GEOGRAPHIC_ROOT_ID,
            "Báo cáo bộ phận hợp nhất theo khu vực địa lý",
            792,
            790,
            TM_PAGE53_OVERALL_ROOT_ID,
            2,
        ),
    ]
    next_schema_id = 5764
    next_source_row = 793
    for axis_name in TM_PAGE53_AXIS_NAMES:
        axis_id = next_schema_id
        records.append((axis_id, axis_name, next_source_row, next_source_row - 2, 5763, 3))
        next_schema_id += 1
        next_source_row += 1
        for metric_name in TM_PAGE53_METRIC_NAMES:
            records.append(
                (
                    next_schema_id,
                    f"+ {metric_name}",
                    next_source_row,
                    next_source_row - 2,
                    axis_id,
                    4,
                )
            )
            next_schema_id += 1
            next_source_row += 1
    if next_schema_id != 5806 or next_source_row != 835:
        raise AssertionError("page-53 schema allocation drifted")
    return tuple(records)


TM_PAGE53_SCHEMA_ITEMS = _page53_schema_items()
TM_PAGE53_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE53_SCHEMA_ITEMS)

TM_PAGE54_BUSINESS_ROOT_ID = 5806
TM_PAGE54_DEBT_ASSET_AXIS_ID = 5828
TM_PAGE54_DEBT_ASSET_ALIAS = "Khai thác nợ Quản lý tài sản"
TM_PAGE54_AXIS_NAMES = (
    "Tài chính Ngân hàng",
    "Chứng khoán Quản lý quỹ",
    "Bảo hiểm",
    "Quản lý nợ và Khai thác tài sản",
    "Loại trừ/Phân loại",
    "Tổng cộng",
)


def _page54_schema_items() -> tuple[tuple[int, str, int, int, int, int], ...]:
    records: list[tuple[int, str, int, int, int, int]] = [
        (
            TM_PAGE54_BUSINESS_ROOT_ID,
            "Báo cáo bộ phận hợp nhất theo khu vực kinh doanh",
            835,
            833,
            TM_PAGE53_OVERALL_ROOT_ID,
            2,
        )
    ]
    next_schema_id = 5807
    next_source_row = 836
    for axis_name in TM_PAGE54_AXIS_NAMES:
        axis_id = next_schema_id
        records.append(
            (
                axis_id,
                axis_name,
                next_source_row,
                next_source_row - 2,
                TM_PAGE54_BUSINESS_ROOT_ID,
                3,
            )
        )
        next_schema_id += 1
        next_source_row += 1
        for metric_name in TM_PAGE53_METRIC_NAMES:
            records.append(
                (
                    next_schema_id,
                    f"+ {metric_name}",
                    next_source_row,
                    next_source_row - 2,
                    axis_id,
                    4,
                )
            )
            next_schema_id += 1
            next_source_row += 1
    if next_schema_id != 5849 or next_source_row != 878:
        raise AssertionError("page-54 schema allocation drifted")
    return tuple(records)


TM_PAGE54_SCHEMA_ITEMS = _page54_schema_items()
TM_PAGE54_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE54_SCHEMA_ITEMS)

# Physical PDF page 58 / printed page 50 exposes four currency-risk axes.  The
# supplied schema separates fixed assets and investment property but lacks the
# combined source row and the visible total-liabilities row on every observed
# axis.  Rows are recorded at their final deterministic workbook positions.
TM_PAGE58_SCHEMA_ITEMS: tuple[tuple[int, str, int, int, int, int], ...] = (
    (5849, "Tài sản cố định và bất động sản đầu tư", 936, 934, 1353, 3),
    (5850, "Tổng nợ phải trả", 941, 939, 1366, 4),
    (5851, "Tài sản cố định và bất động sản đầu tư", 964, 962, 1379, 3),
    (5852, "Tổng nợ phải trả", 969, 967, 1392, 4),
    (5853, "Tài sản cố định và bất động sản đầu tư", 1018, 1016, 1431, 3),
    (5854, "Tổng nợ phải trả", 1023, 1021, 1444, 4),
    (5855, "Tài sản cố định và bất động sản đầu tư", 1046, 1044, 1457, 3),
    (5856, "Tổng nợ phải trả", 1051, 1049, 1470, 4),
)
TM_PAGE58_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE58_SCHEMA_ITEMS)

TM_PAGE57_COMBINED_LOAN_NAME = "Cho vay khách hàng và mua nợ"
TM_PAGE57_COMBINED_FIXED_NAME = "Tài sản cố định, bất động sản đầu tư"


def _page57_schema_items() -> tuple[tuple[int, str, int, int, int, int], ...]:
    records: list[tuple[int, str, int, int, int, int]] = [
        (5857, TM_PAGE57_COMBINED_LOAN_NAME, 1072, 1070, 1484, 3),
        (5858, TM_PAGE57_COMBINED_FIXED_NAME, 1076, 1074, 1484, 3),
        (5859, TM_PAGE57_COMBINED_LOAN_NAME, 1099, 1097, 1509, 3),
        (5860, TM_PAGE57_COMBINED_FIXED_NAME, 1103, 1101, 1509, 3),
        (5861, TM_PAGE57_COMBINED_LOAN_NAME, 1176, 1174, 1584, 3),
        (5862, TM_PAGE57_COMBINED_FIXED_NAME, 1180, 1178, 1584, 3),
        (5863, TM_PAGE57_COMBINED_LOAN_NAME, 1203, 1201, 1609, 3),
        (5864, TM_PAGE57_COMBINED_FIXED_NAME, 1207, 1205, 1609, 3),
        (5865, TM_PAGE57_COMBINED_LOAN_NAME, 1230, 1228, 1634, 3),
        (5866, TM_PAGE57_COMBINED_FIXED_NAME, 1234, 1232, 1634, 3),
        (5867, TM_PAGE57_COMBINED_LOAN_NAME, 1257, 1255, 1659, 3),
        (5868, TM_PAGE57_COMBINED_FIXED_NAME, 1261, 1259, 1659, 3),
        (
            5869,
            "Rủi ro lãi suất - Trong hạn trên 01 năm",
            1327,
            1325,
            1483,
            2,
        ),
    ]
    standard_children = (
        (5870, "Tổng Tài sản", 5869, 3),
        (5871, "Tiền mặt, vàng bạc đá quý", 5869, 3),
        (5872, "Tiền gửi tại NHNN", 5869, 3),
        (5873, "Tiền gửi và cho vay các TCTD khác", 5869, 3),
        (5874, "Chứng khoán kinh doanh", 5869, 3),
        (5875, "Công cụ tài chính phái sinh và các tài sản tài chính khác", 5869, 3),
        (5876, TM_PAGE57_COMBINED_LOAN_NAME, 5869, 3),
        (5877, "Cho vay khách hàng", 5869, 3),
        (5878, "Chứng khoán đầu tư", 5869, 3),
        (5879, "Góp vốn, đầu tư dài hạn", 5869, 3),
        (5880, TM_PAGE57_COMBINED_FIXED_NAME, 5869, 3),
        (5881, "Tài sản cố định", 5880, 4),
        (5882, "Bất động sản đầu tư", 5880, 4),
        (5883, "Tài sản Có khác", 5869, 3),
        (5884, "Tổng Nợ phải trả", 5869, 3),
        (5885, "Tiền gửi và vay từ NHNN và các TCTD khác", 5869, 3),
        (5886, "Các khoản nợ chính phủ và NHNN", 5869, 3),
        (5887, "Tiền gửi và cho vay các TCTD khác", 5869, 3),
        (5888, "Tiền gửi của khách hàng", 5869, 3),
        (5889, "Công cụ tài chính phái sinh và các khoản nợ tài chính khác", 5869, 3),
        (5890, "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro", 5869, 3),
        (5891, "Phát hành giấy tờ có giá", 5869, 3),
        (5892, "Các khoản nợ khác", 5869, 3),
        (5893, "Chênh lệch nhạy cảm với lãi suất nội bảng", 5869, 3),
        (5894, "Chênh lệch nhạy cảm với lãi suất ngoại bảng", 5869, 3),
        (5895, "Chênh lệch nhạy cảm với lãi suất nội, ngoại bảng", 5869, 3),
    )
    for offset, (schema_id, name, parent_id, level) in enumerate(standard_children):
        source_row = 1328 + offset
        records.append((schema_id, name, source_row, source_row - 2, parent_id, level))
    records.extend(
        (
            (5896, TM_PAGE57_COMBINED_LOAN_NAME, 1361, 1359, 1734, 3),
            (5897, TM_PAGE57_COMBINED_FIXED_NAME, 1365, 1363, 1734, 3),
        )
    )
    if len(records) != 41 or {item[0] for item in records} != set(range(5857, 5898)):
        raise AssertionError("page-57 schema allocation drifted")
    return tuple(records)


TM_PAGE57_SCHEMA_ITEMS = _page57_schema_items()
TM_PAGE57_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE57_SCHEMA_ITEMS)

TM_PAGE60_COMBINED_LOAN_NAME = "Cho vay khách hàng và mua nợ"
TM_PAGE60_COMBINED_LOAN_SOURCE_ALIAS = "Cho vay khách hàng và mua nợ (*)"
TM_PAGE60_COMBINED_FIXED_NAME = "Tài sản cố định, bất động sản đầu tư"


def _page60_schema_items() -> tuple[tuple[int, str, int, int, int, int], ...]:
    new_overdue_branch: tuple[tuple[int, str, int, int], ...] = (
        (5898, "Rủi ro thanh khoản - Quá hạn", 1759, 2),
        (5899, "Tổng Tài sản", 5898, 3),
        (5900, "Tiền mặt, vàng bạc đá quý", 5898, 3),
        (5901, "Tiền gửi tại NHNN", 5898, 3),
        (5902, "Tiền gửi và cho vay các TCTD khác", 5898, 3),
        (5903, "Chứng khoán kinh doanh", 5898, 3),
        (5904, "Công cụ tài chính phái sinh và các tài sản tài chính khác", 5898, 3),
        (5905, TM_PAGE60_COMBINED_LOAN_NAME, 5898, 3),
        (5906, "Cho vay khách hàng", 5898, 3),
        (5907, "Chứng khoán đầu tư", 5898, 3),
        (5908, "Góp vốn, đầu tư dài hạn", 5898, 3),
        (5909, TM_PAGE60_COMBINED_FIXED_NAME, 5898, 3),
        (5910, "Tài sản cố định", 5909, 4),
        (5911, "Bất động sản đầu tư", 5909, 4),
        (5912, "Tài sản Có khác", 5898, 3),
        (5913, "Tổng Nợ phải trả", 5898, 3),
        (5914, "Tiền gửi và vay từ NHNN và các TCTD khác", 5898, 3),
        (5915, "Các khoản nợ chính phủ và NHNN", 5898, 3),
        (5916, "Tiền gửi và cho vay các TCTD khác", 5898, 3),
        (5917, "Tiền gửi của khách hàng", 5898, 3),
        (5918, "Công cụ tài chính phái sinh và các khoản nợ tài chính khác", 5898, 3),
        (5919, "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro", 5898, 3),
        (5920, "Phát hành giấy tờ có giá", 5898, 3),
        (5921, "Các khoản nợ khác", 5898, 3),
        (5922, "Chênh lệch thanh khoản ròng", 5898, 3),
    )
    records = tuple(
        (schema_id, name, 1382 + offset, 1380 + offset, parent_id, level)
        for offset, (schema_id, name, parent_id, level) in enumerate(new_overdue_branch)
    )
    pair_records = (
        (5923, TM_PAGE60_COMBINED_LOAN_NAME, 1460, 1458, 1806, 3),
        (5924, TM_PAGE60_COMBINED_FIXED_NAME, 1464, 1462, 1806, 3),
        (5925, TM_PAGE60_COMBINED_LOAN_NAME, 1485, 1483, 1829, 3),
        (5926, TM_PAGE60_COMBINED_FIXED_NAME, 1489, 1487, 1829, 3),
        (5927, TM_PAGE60_COMBINED_LOAN_NAME, 1510, 1508, 1852, 3),
        (5928, TM_PAGE60_COMBINED_FIXED_NAME, 1514, 1512, 1852, 3),
        (5929, TM_PAGE60_COMBINED_LOAN_NAME, 1535, 1533, 1875, 3),
        (5930, TM_PAGE60_COMBINED_FIXED_NAME, 1539, 1537, 1875, 3),
        (5931, TM_PAGE60_COMBINED_LOAN_NAME, 1560, 1558, 1898, 3),
        (5932, TM_PAGE60_COMBINED_FIXED_NAME, 1564, 1562, 1898, 3),
        (5933, TM_PAGE60_COMBINED_LOAN_NAME, 1585, 1583, 1921, 3),
        (5934, TM_PAGE60_COMBINED_FIXED_NAME, 1589, 1587, 1921, 3),
    )
    result = (*records, *pair_records)
    if len(result) != 37 or {item[0] for item in result} != set(range(5898, 5935)):
        raise AssertionError("page-60 schema allocation drifted")
    return result


TM_PAGE60_SCHEMA_ITEMS = _page60_schema_items()
TM_PAGE60_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE60_SCHEMA_ITEMS)
TM_PAGE60_COMBINED_LOAN_IDS = (5905, 5923, 5925, 5927, 5929, 5931, 5933)
TM_PAGE60_COMBINED_FIXED_IDS = (5909, 5924, 5926, 5928, 5930, 5932, 5934)

TM_PAGE61_ROOT_ID = 5935
TM_PAGE61_ROOT_NAME = "Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo"
TM_PAGE61_ROOT_SOURCE_ALIAS = "6. Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo"
TM_PAGE61_CURRENCIES: tuple[tuple[int, str, str], ...] = (
    (5936, "USD", "Đô la Mỹ"),
    (5937, "EUR", "Euro"),
    (5938, "GBP", "Bảng Anh"),
    (5939, "JPY", "Yên Nhật"),
    (5940, "CHF", "Franc Thụy Sĩ"),
    (5941, "AUD", "Đô la Úc"),
    (5942, "CAD", "Đô la Canada"),
    (5943, "SGD", "Đô la Singapore"),
    (5944, "THB", "Baht Thái"),
    (5945, "SEK", "Krona Thụy Điển"),
)
TM_PAGE61_SCHEMA_ITEMS: tuple[tuple[int, str, int, int, int, int], ...] = (
    (TM_PAGE61_ROOT_ID, TM_PAGE61_ROOT_NAME, 1603, 1601, 1259, 1),
    *tuple(
        (schema_id, name, 1604 + offset, 1602 + offset, TM_PAGE61_ROOT_ID, 2)
        for offset, (schema_id, name, _alias) in enumerate(TM_PAGE61_CURRENCIES)
    ),
)
TM_PAGE61_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE61_SCHEMA_ITEMS)

# Coverage-first additions authorized from the itemized MBB TM questions Q030,
# Q031, Q034, Q036, Q040, Q041, Q044, Q046, Q048, Q052-Q054, Q056, Q060,
# Q062-Q063 and Q067.  IDs are append-only identities; workbook placement is
# governed separately by fail-closed predecessor/successor chains so adding a
# row never depends on fragile physical-row arithmetic.
TM_COVERAGE_SCHEMA_ITEMS: tuple[tuple[int, str, int, int], ...] = (
    (5946, "Lãi trên mỗi cổ phiếu", 1128, 2),
    (5947, "Bình quân gia quyền của số cổ phiếu phổ thông đang lưu hành", 5946, 3),
    (5948, "Lãi cơ bản trên mỗi cổ phiếu", 5946, 3),
    (5949, "Cổ phiếu", 1128, 2),
    (5950, "Số lượng cổ phiếu đăng ký phát hành", 5949, 3),
    (5951, "Số lượng cổ phiếu đã bán ra công chúng", 5949, 3),
    (5952, "- Cổ phiếu phổ thông", 5951, 4),
    (5953, "Số lượng cổ phiếu được mua lại", 5949, 3),
    (5954, "- Cổ phiếu phổ thông", 5953, 4),
    (5955, "- Cổ phiếu ưu đãi", 5953, 4),
    (5956, "Số lượng cổ phiếu đang lưu hành", 5949, 3),
    (5957, "- Cổ phiếu phổ thông", 5956, 4),
    (5958, "- Cổ phiếu ưu đãi", 5956, 4),
    (5959, "Dự phòng giảm giá", 862, 2),
    (5960, "Đầu tư vào tổ chức kinh tế, dự án dài hạn", 867, 3),
    (5961, "Đầu tư vào các Quỹ đầu tư", 867, 3),
    (5962, "+ Chênh lệch tỷ giá", 869, 3),
    (5963, "+ Chênh lệch tỷ giá", 883, 3),
    (5964, "Giá trị còn lại", 868, 2),
    (5965, "Số dư đầu kỳ", 5964, 3),
    (5966, "Số dư cuối kỳ", 5964, 3),
    (5967, "+ Chênh lệch tỷ giá", 914, 3),
    (5968, "+ Chênh lệch tỷ giá", 929, 3),
    (5969, "Giá trị còn lại", 913, 2),
    (5970, "Số dư đầu kỳ", 5969, 3),
    (5971, "Số dư cuối kỳ", 5969, 3),
    (5972, "Giá trị còn lại", 942, 2),
    (5973, "Số dư đầu kỳ", 5972, 3),
    (5974, "Số dư cuối kỳ", 5972, 3),
    (5975, "Phải thu liên quan đến dịch vụ thanh toán", 967, 3),
    (5976, "Phải thu miễn truy đòi theo bộ chứng từ", 967, 3),
    (5977, "Tiền gửi của TCKT", 1075, 3),
    (5978, "+ Lãi suất tối thiểu", 1101, 3),
    (5979, "+ Lãi suất tối đa", 1101, 3),
    (5980, "+ Lãi suất tối thiểu", 1109, 3),
    (5981, "+ Lãi suất tối đa", 1109, 3),
    (5982, "Số lượng cổ phiếu đã phát hành", 1128, 2),
    (5983, "Mệnh giá cổ phiếu", 1128, 2),
    (5984, "Vốn điều lệ của Ngân hàng", 1128, 2),
    (5985, "Thu nhập từ lãi thuần", 1142, 1),
    (5986, "Thu từ dịch vụ tư vấn", 1157, 2),
    (5987, "Chi về dịch vụ tư vấn", 1167, 2),
    (5988, "Chi về xử lý nợ, thẩm định giá và khai thác tài sản", 1167, 2),
    (5989, "Lãi thuần từ hoạt động dịch vụ", 1142, 1),
    (5990, "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư", 1142, 1),
)
TM_COVERAGE_SCHEMA_IDS = tuple(item[0] for item in TM_COVERAGE_SCHEMA_ITEMS)
TM_COVERAGE_DISPLAY_CHAINS: tuple[tuple[tuple[int, ...], int, int], ...] = (
    ((5960, 5961, 5959), 867, 868),
    ((5962,), 881, 882),
    ((5963,), 894, 895),
    ((5964, 5965, 5966), 895, 896),
    ((5967,), 927, 928),
    ((5968,), 940, 941),
    ((5969, 5970, 5971), 941, 942),
    ((5972, 5973, 5974), 965, 966),
    ((5975, 5976), 980, 981),
    ((5977,), 1075, 1076),
    ((5978, 5979), 1101, 1102),
    ((5980, 5981), 1109, 1110),
    ((5982, 5983, 5984), 1128, 1129),
    ((5946, 5947, 5948, 5949, 5950, 5951, 5952, 5953, 5954, 5955, 5956, 5957, 5958), 1141, 1142),
    ((5985,), 1156, 1157),
    ((5986,), 1165, 1166),
    ((5987, 5988), 1173, 1174),
    ((5989,), 1174, 1175),
    ((5990,), 1197, 1198),
)

if TM_COVERAGE_SCHEMA_IDS != tuple(range(5946, 5991)) or {
    schema_id
    for schema_ids, _predecessor, _successor in TM_COVERAGE_DISPLAY_CHAINS
    for schema_id in schema_ids
} != set(TM_COVERAGE_SCHEMA_IDS):
    raise AssertionError("TM coverage schema allocation drifted")

# Evidence-driven universal-schema additions discovered in the MBB consolidated
# Q1/2026 notes.  These are accounting identities, not bank coverage
# requirements: another bank may legitimately mark any of them NOT_OBSERVED or
# NOT_APPLICABLE.  Numeric ID allocation is append-only; the anchor chains below
# independently control accounting presentation order.
TM_UNIVERSAL_SCHEMA_ITEMS: tuple[tuple[int, str, int, int], ...] = (
    (5991, "Tổng tăng nguyên giá TSCĐ hữu hình trong kỳ", 869, 3),
    (5992, "Tổng giảm nguyên giá TSCĐ hữu hình trong kỳ", 869, 3),
    (5993, "Tăng/(Giảm) khác nguyên giá TSCĐ hữu hình trong kỳ", 869, 3),
    (5994, "Tổng tăng hao mòn TSCĐ hữu hình trong kỳ", 883, 3),
    (5995, "Tổng giảm hao mòn TSCĐ hữu hình trong kỳ", 883, 3),
    (5996, "Tăng/(Giảm) khác hao mòn TSCĐ hữu hình trong kỳ", 883, 3),
    (5997, "Tổng tăng nguyên giá TSCĐ vô hình trong kỳ", 914, 3),
    (5998, "Tăng/(Giảm) khác nguyên giá TSCĐ vô hình trong kỳ", 914, 3),
    (5999, "Tổng tăng hao mòn TSCĐ vô hình trong kỳ", 929, 3),
    (6000, "Tổng giảm hao mòn TSCĐ vô hình trong kỳ", 929, 3),
    (6001, "Tăng/(Giảm) khác hao mòn TSCĐ vô hình trong kỳ", 929, 3),
    (6002, "Tổng tăng nguyên giá bất động sản đầu tư trong kỳ", 943, 3),
    (6003, "Tổng giảm nguyên giá bất động sản đầu tư trong kỳ", 943, 3),
    (6004, "Tăng/(Giảm) khác nguyên giá bất động sản đầu tư trong kỳ", 943, 3),
    (6005, "Tổng tăng hao mòn bất động sản đầu tư trong kỳ", 956, 3),
    (6006, "Tăng/(Giảm) khác hao mòn bất động sản đầu tư trong kỳ", 956, 3),
    (6007, "Chi phí xây dựng cơ bản, mua sắm TSCĐ", 967, 3),
    (6008, "Từ 12 tháng trở xuống", 1101, 3),
    (6009, "Trên 12 tháng", 1101, 3),
    (6010, "Dưới 5 năm", 1109, 3),
    (6011, "Thặng dư vốn cổ phần", 1128, 2),
    (6012, "Vốn khác", 1128, 2),
    (6013, "Quỹ dự trữ bổ sung vốn điều lệ", 1128, 2),
    (6014, "Quỹ dự phòng tài chính", 1128, 2),
    (6015, "Quỹ khác", 1128, 2),
    (6016, "Chênh lệch tỷ giá hối đoái", 1128, 2),
    (6017, "Lợi nhuận chưa phân phối", 1128, 2),
    (6018, "Lợi ích cổ đông không kiểm soát", 1128, 2),
    (6019, "Trích lập/Tăng", 1128, 2),
    (6020, "Sử dụng/Giảm", 1128, 2),
    (6021, "Thu từ dịch vụ thanh toán và ngân quỹ", 1157, 2),
    (6022, "Thu từ xử lý nợ, thẩm định giá và khai thác tài sản", 1157, 2),
    (6023, "Chi về dịch vụ thanh toán và ngân quỹ", 1167, 2),
    (6024, "Chi phí hoa hồng môi giới", 1170, 3),
    (6025, "Chi về hoạt động môi giới chứng khoán", 1170, 3),
    (6026, "Thu từ kinh doanh ngoại tệ giao ngay và vàng", 1175, 2),
    (6027, "Chi về kinh doanh ngoại tệ giao ngay và vàng", 1175, 2),
    (
        6028,
        "(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn",
        1193,
        2,
    ),
    (6029, "Lãi thuần từ hoạt động kinh doanh khác", 1142, 1),
    (6030, "Thu nhập/(Chi phí) khác", 6029, 2),
    (6031, "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay khách hàng", 1221, 2),
    (6032, "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay TCTD", 1221, 2),
    (6033, "Chi phí/(Hoàn nhập) dự phòng mua nợ", 1221, 2),
    (6057, "+ Cho vay theo chỉ định của Chính phủ", 717, 3),
    (6058, "+ Cho vay tại Chi nhánh và ngân hàng con nước ngoài", 727, 3),
    (
        6059,
        "+ Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở",
        727,
        3,
    ),
    (6060, "+ Dịch vụ", 727, 3),
)
TM_UNIVERSAL_SCHEMA_IDS = tuple(item[0] for item in TM_UNIVERSAL_SCHEMA_ITEMS)
TM_UNIVERSAL_DISPLAY_CHAINS: tuple[tuple[tuple[int, ...], int, int], ...] = (
    ((5991,), 870, 871),
    ((5992,), 875, 876),
    ((5993,), 881, 5962),
    ((5994,), 884, 885),
    ((5995,), 887, 888),
    ((5996,), 894, 5963),
    ((5997,), 915, 916),
    ((5998,), 927, 5967),
    ((5999,), 930, 931),
    ((6000,), 933, 934),
    ((6001,), 940, 5968),
    ((6002,), 944, 945),
    ((6003,), 951, 952),
    ((6004,), 954, 955),
    ((6005,), 957, 958),
    ((6006,), 964, 965),
    ((6007,), 967, 968),
    ((6008, 6009), 5979, 1102),
    ((6010,), 5981, 1110),
    ((6011, 6012, 6013, 6014, 6015, 6016, 6017, 6018), 5984, 1129),
    ((6019,), 1129, 1130),
    ((6020,), 1136, 1137),
    ((6021,), 1157, 1158),
    ((6022,), 1162, 1163),
    ((6023,), 1167, 1168),
    ((6024, 6025), 1170, 1171),
    ((6026,), 1176, 1177),
    ((6027,), 1182, 1183),
    ((6028,), 1196, 1197),
    ((6029, 6030), 1228, 1229),
    ((6031,), 1223, 1224),
    ((6032,), 1221, 1222),
    ((6033,), 1225, 1226),
    ((6057,), 720, 721),
    ((6060,), 739, 740),
    ((6059,), 5722, 744),
    ((6058,), 745, 5749),
)
if TM_UNIVERSAL_SCHEMA_IDS != (*range(5991, 6034), *range(6057, 6061)):
    raise AssertionError("TM universal-schema allocation drifted")

FIRST_OBSERVED_PDF_PATH = "vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf"
FIRST_OBSERVED_PDF_SHA256 = "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
TM_UNIVERSAL_EVIDENCE: dict[int, dict[str, object]] = {
    5991: {
        "pdf_pages": [37, 38],
        "source_row_refs": ["GROSS_COST:3"],
        "visible_label": "Tăng trong kỳ",
        "observed_values": [56387, 754094],
    },
    5992: {
        "pdf_pages": [37, 38],
        "source_row_refs": ["GROSS_COST:4"],
        "visible_label": "Giảm trong kỳ",
        "observed_values": [-6224, -354092],
    },
    5993: {
        "pdf_pages": [37],
        "source_row_refs": ["GROSS_COST:5"],
        "visible_label": "Tăng/(Giảm) khác trong kỳ",
        "observed_values": [-480],
    },
    5994: {
        "pdf_pages": [37, 38],
        "source_row_refs": ["ACCUMULATED_DEPRECIATION:3"],
        "visible_label": "Tăng trong kỳ",
        "observed_values": [144587, 551766],
    },
    5995: {
        "pdf_pages": [37, 38],
        "source_row_refs": ["ACCUMULATED_DEPRECIATION:4"],
        "visible_label": "Giảm trong kỳ",
        "observed_values": [-5996, -201454],
    },
    5996: {
        "pdf_pages": [37],
        "source_row_refs": ["ACCUMULATED_DEPRECIATION:5"],
        "visible_label": "Tăng/(Giảm) khác trong kỳ",
        "observed_values": ["DASH"],
    },
    5997: {
        "pdf_pages": [39, 40],
        "source_row_refs": ["GROSS_COST:3"],
        "visible_label": "Tăng trong kỳ",
        "observed_values": [77097, 823072],
    },
    5998: {
        "pdf_pages": [40],
        "source_row_refs": ["GROSS_COST:other"],
        "visible_label": "Tăng/(Giảm) khác",
        "observed_values": [-10622],
    },
    5999: {
        "pdf_pages": [39, 40],
        "source_row_refs": ["ACCUMULATED_AMORTIZATION:3"],
        "visible_label": "Tăng trong kỳ",
        "observed_values": [104592, 601304],
    },
    6000: {
        "pdf_pages": [40],
        "source_row_refs": ["ACCUMULATED_AMORTIZATION:decrease"],
        "visible_label": "Giảm trong kỳ",
        "observed_values": [-21406],
    },
    6001: {
        "pdf_pages": [40],
        "source_row_refs": ["ACCUMULATED_AMORTIZATION:other"],
        "visible_label": "Tăng/(Giảm) khác",
        "observed_values": [-3348],
    },
    6002: {
        "pdf_pages": [41],
        "source_row_refs": ["GROSS_COST:increase"],
        "visible_label": "Tăng",
        "observed_values": ["DASH", 4971],
    },
    6003: {
        "pdf_pages": [41],
        "source_row_refs": ["GROSS_COST:decrease"],
        "visible_label": "Giảm",
        "observed_values": [-10260],
    },
    6004: {
        "pdf_pages": [41],
        "source_row_refs": ["GROSS_COST:other"],
        "visible_label": "Tăng/(Giảm) khác",
        "observed_values": [-4971],
    },
    6005: {
        "pdf_pages": [41],
        "source_row_refs": ["ACCUMULATED_DEPRECIATION:increase"],
        "visible_label": "Tăng trong kỳ",
        "observed_values": [1528, 6145],
    },
    6006: {
        "pdf_pages": [41],
        "source_row_refs": ["ACCUMULATED_DEPRECIATION:other"],
        "visible_label": "Tăng/(Giảm) khác",
        "observed_values": [-132],
    },
    6007: {
        "pdf_pages": [42],
        "source_row_refs": ["row-0001"],
        "visible_label": "Chi phí xây dựng cơ bản, mua sắm TSCĐ",
        "observed_values": [1295059, 1039654],
    },
    6008: {
        "pdf_pages": [44],
        "source_row_refs": ["CD:row-0006"],
        "visible_label": "Từ 12 tháng trở xuống",
        "observed_values": [85267048, 76253073],
    },
    6009: {
        "pdf_pages": [44],
        "source_row_refs": ["CD:row-0007"],
        "visible_label": "Trên 12 tháng",
        "observed_values": [79970220, 64577077],
    },
    6010: {
        "pdf_pages": [44],
        "source_row_refs": ["BOND:row-0003"],
        "visible_label": "Dưới 5 năm",
        "observed_values": [24009801, 23039165],
    },
    **{
        schema_id: {
            "pdf_pages": [44],
            "source_row_refs": [f"EQUITY_GRID:{name}"],
            "visible_label": name,
        }
        for schema_id, name, _parent_id, _level in TM_UNIVERSAL_SCHEMA_ITEMS
        if 6011 <= schema_id <= 6018
    },
    6019: {
        "pdf_pages": [44],
        "source_row_refs": ["EQUITY_GRID:movement-increase"],
        "visible_label": "Trích lập/Tăng",
        "observed_values": [7810203],
    },
    6020: {
        "pdf_pages": [44],
        "source_row_refs": ["EQUITY_GRID:movement-decrease"],
        "visible_label": "Sử dụng/Giảm",
        "observed_values": [-87403],
    },
    6021: {
        "pdf_pages": [46],
        "source_row_refs": ["NET_SERVICE:row-0003"],
        "visible_label": "Thu từ dịch vụ thanh toán và ngân quỹ",
        "observed_values": [1460480, 755554],
    },
    6022: {
        "pdf_pages": [46],
        "source_row_refs": ["NET_SERVICE:row-0007"],
        "visible_label": "Thu từ xử lý nợ, thẩm định giá và khai thác tài sản",
        "observed_values": [38898, 126730],
    },
    6023: {
        "pdf_pages": [46],
        "source_row_refs": ["NET_SERVICE:row-0012"],
        "visible_label": "Chi về dịch vụ thanh toán và ngân quỹ",
        "observed_values": [-675848, -551556],
    },
    6024: {
        "pdf_pages": [46],
        "source_row_refs": ["NET_SERVICE:row-0015"],
        "visible_label": "Chi phí hoa hồng môi giới",
        "observed_values": [-539743, -232408],
    },
    6025: {
        "pdf_pages": [46],
        "source_row_refs": ["NET_SERVICE:row-0018"],
        "visible_label": "Chi về hoạt động môi giới chứng khoán",
        "observed_values": [-59748, -32105],
    },
    6026: {
        "pdf_pages": [47],
        "source_row_refs": ["FX_GOLD:row-0003"],
        "visible_label": "Thu từ kinh doanh ngoại tệ giao ngay và vàng",
        "observed_values": [662413, 983504],
    },
    6027: {
        "pdf_pages": [47],
        "source_row_refs": ["FX_GOLD:row-0007"],
        "visible_label": "Chi về kinh doanh ngoại tệ giao ngay và vàng",
        "observed_values": [-486848, -221138],
    },
    6028: {
        "pdf_pages": [47],
        "source_row_refs": ["SECURITIES:row-0011"],
        "visible_label": "(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn",
        "observed_values": ["DASH", 20861],
    },
    6029: {
        "pdf_pages": [47],
        "source_row_refs": ["OTHER_ACTIVITY:row-0005"],
        "visible_label": "Lãi thuần từ hoạt động kinh doanh khác",
        "observed_values": [1090478, 1179210],
    },
    6030: {
        "pdf_pages": [47],
        "source_row_refs": ["OTHER_ACTIVITY:row-0004"],
        "visible_label": "Thu nhập/(Chi phí) khác",
        "observed_values": [252019, 113256],
    },
    6031: {
        "pdf_pages": [49],
        "source_row_refs": ["CREDIT_PROVISION:row-0002"],
        "visible_label": "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay khách hàng",
        "observed_values": [3451261, 2973316],
    },
    6032: {
        "pdf_pages": [49],
        "source_row_refs": ["CREDIT_PROVISION:row-0003"],
        "visible_label": "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay TCTD",
        "observed_values": [1648, 76],
    },
    6033: {
        "pdf_pages": [49],
        "source_row_refs": ["CREDIT_PROVISION:row-0004"],
        "visible_label": "Chi phí/(Hoàn nhập) dự phòng mua nợ",
        "observed_values": [1775, 24681],
    },
    6057: {
        "bank": "ACB",
        "period": "Q2/2026",
        "scope": "CONSOLIDATED",
        "source_document_path": ("vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf"),
        "source_document_sha256": (
            "db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86"
        ),
        "pdf_pages": [17],
        "source_row_refs": ["GOVERNMENT_DIRECTED_OR_FUNDED"],
        "visible_label": "Cho vay theo chỉ định của Chính phủ",
        "observed_values": ["DASH", "DASH"],
        "user_decision": "Q079",
    },
    6058: {
        "bank": "MBB",
        "period": "Q2/2026",
        "scope": "CONSOLIDATED",
        "source_document_path": ("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf"),
        "source_document_sha256": (
            "a86757a4499953264ca22dd57ae2e3257057631107742e1d04ad1ecd0e2c23d1"
        ),
        "pdf_pages": [33],
        "source_row_refs": ["FOREIGN_BRANCH_LOANS"],
        "visible_label": "Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
        "observed_values": ["9.295.704", "0,75%", "9.330.629", "0,86%"],
        "user_decision": "Q079",
    },
    6059: {
        "bank": "VPB",
        "period": "Q1/2026",
        "scope": "CONSOLIDATED",
        "source_document_path": ("vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf"),
        "source_document_sha256": (
            "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
        ),
        "pdf_pages": [44],
        "source_row_refs": ["PERSONAL_HOUSING_LOANS"],
        "visible_label": ("Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở"),
        "observed_values": ["139.410.297", "13,39%", "130.375.600", "13,81%"],
        "user_decision": "Q079",
    },
    6060: {
        "bank": "BID",
        "period": "Q2/2026",
        "scope": "CONSOLIDATED",
        "source_document_path": ("vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf"),
        "source_document_sha256": (
            "73d9ead38e4e60b2241ae7d41a6e5382f8f2e5cc59f2e7a70ca0bedb95792003"
        ),
        "pdf_pages": [22],
        "source_row_refs": ["BROAD_SERVICES"],
        "visible_label": "Dịch vụ",
        "observed_values": ["534.960.928", "444.190.319"],
        "user_decision": "Q079",
    },
}

if set(TM_UNIVERSAL_EVIDENCE) != set(TM_UNIVERSAL_SCHEMA_IDS):
    raise AssertionError("TM universal-schema evidence ledger drifted")

TM_PAGE52_61_SCHEMA_ITEMS = (
    *TM_PAGE52_SCHEMA_ITEMS,
    *TM_PAGE53_SCHEMA_ITEMS,
    *TM_PAGE54_SCHEMA_ITEMS,
    *TM_PAGE58_SCHEMA_ITEMS,
    *TM_PAGE57_SCHEMA_ITEMS,
    *TM_PAGE60_SCHEMA_ITEMS,
    *TM_PAGE61_SCHEMA_ITEMS,
)
TM_PAGE52_61_SCHEMA_IDS = tuple(item[0] for item in TM_PAGE52_61_SCHEMA_ITEMS)


def _chain_anchors(
    schema_ids: tuple[int, ...], *, predecessor: int, successor: int
) -> dict[int, tuple[int, int]]:
    return {
        schema_id: (
            predecessor if offset == 0 else schema_ids[offset - 1],
            successor if offset == len(schema_ids) - 1 else schema_ids[offset + 1],
        )
        for offset, schema_id in enumerate(schema_ids)
    }


TM_PAGE52_61_ANCHORS = {
    **_chain_anchors((5752,), predecessor=759, successor=760),
    **_chain_anchors((5753, 5754, 5755), predecessor=1091, successor=1092),
    **_chain_anchors((5756, 5757, 5758), predecessor=1295, successor=1296),
    **_chain_anchors(
        (
            5750,
            5751,
            5759,
            5760,
            5761,
            *TM_PAGE53_SCHEMA_IDS,
            *TM_PAGE54_SCHEMA_IDS,
        ),
        predecessor=1304,
        successor=1305,
    ),
    5849: (1362, 1363),
    5850: (1366, 1367),
    5851: (1388, 1389),
    5852: (1392, 1393),
    5853: (1440, 1441),
    5854: (1444, 1445),
    5855: (1466, 1467),
    5856: (1470, 1471),
    5857: (1490, 1491),
    5858: (1493, 1494),
    5859: (1515, 1516),
    5860: (1518, 1519),
    5861: (1590, 1591),
    5862: (1593, 1594),
    5863: (1615, 1616),
    5864: (1618, 1619),
    5865: (1640, 1641),
    5866: (1643, 1644),
    5867: (1665, 1666),
    5868: (1668, 1669),
    **_chain_anchors(tuple(range(5869, 5896)), predecessor=1733, successor=1734),
    5896: (1740, 1741),
    5897: (1743, 1744),
    **_chain_anchors(tuple(range(5898, 5923)), predecessor=1759, successor=1760),
    5923: (1812, 1813),
    5924: (1815, 1816),
    5925: (1835, 1836),
    5926: (1838, 1839),
    5927: (1858, 1859),
    5928: (1861, 1862),
    5929: (1881, 1882),
    5930: (1884, 1885),
    5931: (1904, 1905),
    5932: (1907, 1908),
    5933: (1927, 1928),
    5934: (1930, 1931),
    **_chain_anchors(TM_PAGE61_SCHEMA_IDS, predecessor=1943, successor=1944),
}
TM_COVERAGE_ANCHORS = {
    schema_id: anchors
    for schema_ids, predecessor, successor in TM_COVERAGE_DISPLAY_CHAINS
    for schema_id, anchors in _chain_anchors(
        schema_ids, predecessor=predecessor, successor=successor
    ).items()
}
TM_UNIVERSAL_ANCHORS = {
    schema_id: anchors
    for schema_ids, predecessor, successor in TM_UNIVERSAL_DISPLAY_CHAINS
    for schema_id, anchors in _chain_anchors(
        schema_ids, predecessor=predecessor, successor=successor
    ).items()
}
if set(TM_UNIVERSAL_ANCHORS) != set(TM_UNIVERSAL_SCHEMA_IDS):
    raise AssertionError("TM universal-schema anchor allocation drifted")
# Later universal insertions legitimately become the immediate display neighbor
# of these earlier append-only identities.  Identity and relative order remain
# unchanged; only their final cumulative-audit anchors advance.
TM_COVERAGE_ANCHORS.update(
    {
        5962: (5993, 882),
        5963: (5996, 895),
        5967: (5998, 928),
        5968: (6001, 941),
        5979: (5978, 6008),
        5981: (5980, 6010),
        5984: (5983, 6011),
    }
)
# Q079 insertions become the final immediate display neighbors of two earlier
# append-only TM identities.  Their IDs, names, and relative order are
# unchanged; only the cumulative-revision neighbor projection advances.
TM_PAGE52_61_ANCHORS[5722] = (5721, 6059)

TM_LOAN_INDUSTRY_PARENT_ID = 727
TM_LOAN_BUSINESS_PARENT_ID = 766
TM_LOAN_BUSINESS_OTHER_ID = 782
TM_PROVISION_MOVEMENT_ID = 783
TM_GENERAL_PROVISION_MOVEMENT_ID = 784
TM_SPECIFIC_PROVISION_MOVEMENT_ID = 792

CDKT_4350_OLD_NAME = "Chứng khoán đầu tư sẵn sàng để hàng"
CDKT_4350_CORRECTED_NAME = "Chứng khoán đầu tư sẵn sàng để bán"
CDKT_4319_OLD_NAME = "Tiền gửi và vay các TCTD khác"
CDKT_4319_CORRECTED_NAME = "Tiền gửi và vay các TCTC, TCTD khác"
CDKT_4360_OLD_NAME = "Vay các TCTD khác"
CDKT_4360_CORRECTED_NAME = "Vay các TCTC, TCTD khác"
LCTT_4136_OLD_NAME = "Tăng, giảm các khoản tiền gửi và vay các TCTD"
LCTT_4136_CORRECTED_NAME = "Tăng, giảm các khoản tiền gửi và vay các TCTC, TCTD"
LCTT_4136_LEGACY_SOURCE_ALIAS = "Tăng/(Giảm) tiền gửi, tiền vay các TCTD khác"
TM_770_OLD_NAME = "+ Công ty TNHH MTV vốn nhà nước trên 50%"
TM_770_CORRECTED_NAME = "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%"
TM_770_BASELINE_SOURCE_ROW = 212

VPB_STRUCTURAL_ALIAS_CANDIDATES: tuple[tuple[str, int, int, int, str], ...] = (
    ("CDKT", 4311, 5, 3, 'Tiền gửi tại Ngân hàng Nhà nước Việt Nam ("NHNN")'),
    (
        "CDKT",
        4312,
        5,
        4,
        'Tiền gửi và cấp tín dụng cho các tổ chức tín dụng ("TCTD") khác',
    ),
    ("CDKT", 4344, 5, 5, "Tiền gửi tại các TCTD khác"),
    ("CDKT", 4326, 5, 6, "Cấp tín dụng cho các TCTD khác"),
    ("CDKT", 4348, 5, 11, "Cho vay khách hàng"),
    ("CDKT", 4368, 5, 24, "Hao mòn tài sản cố định hữu hình"),
    ("CDKT", 4372, 5, 27, "Hao mòn tài sản cố định vô hình"),
    ("CDKT", 4335, 5, 31, "Tài sản thuế thu nhập doanh nghiệp hoãn lại"),
    ("CDKT", 4358, 5, 33, "Dự phòng rủi ro cho các tài sản Có nội bảng khác"),
    ("CDKT", 4375, 5, 34, "TỔNG TÀI SẢN"),
    (
        "CDKT",
        4318,
        6,
        2,
        'Các khoản nợ Chính phủ và Ngân hàng Nhà nước Việt Nam ("NHNN")',
    ),
    (
        "CDKT",
        4319,
        6,
        4,
        'Tiền gửi và vay các tổ chức tài chính ("TCTC"), TCTD khác',
    ),
    ("CDKT", 4336, 6, 13, "Thuế thu nhập doanh nghiệp hoãn lại phải trả"),
    ("CDKT", 4364, 6, 18, "Vốn"),
    ("CDKT", 4365, 6, 21, "Các quỹ của TCTD"),
    ("CDKT", 5699, 6, 23, "Lợi ích của cổ đông không kiểm soát"),
    ("KQKD", 4386, 8, 6, "Lãi thuần từ hoạt động dịch vụ"),
    ("KQKD", 4387, 8, 7, "(Lỗ)/lãi thuần từ hoạt động kinh doanh ngoại hối"),
    ("KQKD", 4388, 8, 8, "(Lỗ)/lãi thuần từ mua bán chứng khoán kinh doanh"),
    ("KQKD", 4395, 8, 11, "Chi phí cho hoạt động khác"),
    ("KQKD", 4390, 8, 12, "Lãi thuần từ hoạt động khác"),
    ("KQKD", 4391, 8, 15, "TỔNG CHI PHÍ HOẠT ĐỘNG"),
    (
        "KQKD",
        4376,
        8,
        16,
        "Lợi nhuận thuần từ HĐKD trước chi phí dự phòng rủi ro tín dụng",
    ),
    ("KQKD", 4384, 8, 20, "Thu nhập/(Chi phí) thuế TNDN hoãn lại"),
    ("KQKD", 4382, 8, 21, KQKD_4382_CORRECTED_NAME),
    ("KQKD", 4379, 8, 23, "Lợi ích của cổ đông không kiểm soát"),
    ("KQKD", 4380, 8, 24, "Lợi nhuận thuần cổ đông ngân hàng"),
    ("KQKD", 4381, 8, 25, "Lãi cơ bản trên cổ phiếu (VND)"),
    (
        "LCTT",
        4126,
        9,
        5,
        "Chênh lệch số tiền thực thu/thực chi từ hoạt động kinh doanh chứng khoán, "
        "vàng bạc, ngoại tệ",
    ),
    ("LCTT", 4154, 9, 6, "Thu nhập khác nhận được"),
    ("LCTT", 4128, 9, 9, "Tiền thuế thu nhập doanh nghiệp thực nộp trong kỳ"),
    ("LCTT", 4109, 9, 10, LCTT_4109_CORRECTED_NAME),
    ("LCTT", 4129, 9, 12, "Giảm các khoản tiền gửi và cho vay các tổ chức tín dụng khác"),
    ("LCTT", 4130, 9, 13, "Tăng Chứng khoán đầu tư và chứng khoán kinh doanh"),
    (
        "LCTT",
        4131,
        9,
        14,
        "Giảm/(Tăng) công cụ tài chính phái sinh và các công cụ tài chính khác",
    ),
    (
        "LCTT",
        4133,
        9,
        16,
        "Giảm nguồn dự phòng để bù đắp tổn thất các khoản tín dụng, chứng khoán, đầu tư dài hạn",
    ),
    ("LCTT", 4134, 9, 17, "Tăng khác về tài sản hoạt động"),
    ("LCTT", 4108, 9, 18, "Những thay đổi về nợ phải trả hoạt động"),
    (
        "LCTT",
        4135,
        9,
        19,
        "Tăng các khoản nợ Chính phủ và Ngân hàng Nhà nước Việt Nam",
    ),
    (
        "LCTT",
        4136,
        9,
        20,
        "Tăng/(Giảm) tiền gửi, tiền vay từ các tổ chức tài chính, tổ chức tín dụng khác",
    ),
    ("LCTT", 4137, 9, 21, "Tăng tiền gửi của khách hàng"),
    (
        "LCTT",
        4138,
        9,
        22,
        "Tăng phát hành giấy tờ có giá (ngoại trừ GTCG phát hành được tính vào hoạt "
        "động tài chính)",
    ),
    (
        "LCTT",
        4139,
        9,
        23,
        "Tăng/(Giảm) vốn tài trợ, ủy thác, cho vay tổ chức tín dụng chịu rủi ro",
    ),
    (
        "LCTT",
        4140,
        9,
        24,
        "Tăng/(Giảm) công cụ tài chính phái sinh và nợ tài chính khác",
    ),
    ("LCTT", 4141, 9, 25, "Tăng khác về công nợ hoạt động"),
    ("LCTT", 4115, 10, 7, "Tiền và các khoản tương đương tiền đầu kỳ"),
    ("LCTT", 4116, 10, 8, "Tiền và các khoản tương đương tiền cuối kỳ"),
)
VPB_ALIAS_CANONICAL_AFTER_CORRECTION = frozenset({("KQKD", 4382), ("LCTT", 4109)})
VPB_ALIAS_CANONICAL_COLLISIONS = {("CDKT", 4348): 4315}
DISPLAY_NAME_COMPATIBILITY_ALIASES = (
    ("CDKT", 4319, CDKT_4319_OLD_NAME),
    ("CDKT", 4360, CDKT_4360_OLD_NAME),
    ("KQKD", 4382, KQKD_4382_OLD_NAME),
    ("LCTT", 4109, LCTT_4109_OLD_NAME),
    ("LCTT", 4136, LCTT_4136_OLD_NAME),
    ("LCTT", 4136, LCTT_4136_LEGACY_SOURCE_ALIAS),
)
NEW_ITEM_SOURCE_ALIASES = (
    ("LCTT", LCTT_VPB_COMBINED_LOAN_ID, 9, 15, "Tăng các khoản cho vay khách hàng và mua nợ"),
)
MBB_OFF_BALANCE_OCR_PATH = (
    "output/calibration/recovery-e0027-mbb-q1-2026-role-c-20260807/"
    "ppocrv6-page-0005/ocr_result.json"
)
MBB_OFF_BALANCE_OCR_SHA256 = "27e5cc72f71a4b759bd0a72e28a9178aa55faaf04aa2cd67812322d83b591d68"
MBB_OFF_BALANCE_RENDER_PATH = (
    "output/calibration/recovery-e0027-mbb-q1-2026-20260807/"
    "eebeda2ebc09b0d42032/renders/page-0005.png"
)
MBB_OFF_BALANCE_RENDER_SHA256 = "7f2574bf11ad7df3d93dc6256c8aa631f6851f8e0056e7bed3c0195d8eeccc6a"
MBB_OFF_BALANCE_SOURCE_ALIASES = (
    ("CDKT", 6044, 5, 27, "Cam kết mua giao dịch hoán đổi ngoại tệ"),
    ("CDKT", 6045, 5, 30, "Cam kết bán giao dịch hoán đổi ngoại tệ"),
)
MBB_OFF_BALANCE_WORDING_ALIASES = (
    (
        "CDKT",
        6038,
        5,
        5,
        "CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
    ),
)

REVIEWED_EXTERNAL_IDS = frozenset((*range(5701, 5712), 5715, 5716, 5717))
NEW_SCHEMA_IDS = frozenset(
    {
        CDKT_TOTAL_EQUITY_ID,
        KQKD_TOTAL_OPERATING_INCOME_ID,
        LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
        TM_TOTAL_INTERBANK_PROVISION_ID,
        TM_HEALTH_SOCIAL_ID,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
        *TM_PAGE50_TAX_SCHEMA_IDS,
        TM_PURCHASED_PRINCIPAL_ID,
        TM_PURCHASED_INTEREST_ID,
        TM_GOVERNMENT_GUARANTEED_DEBT_ID,
        TM_FX_BUY_ID,
        TM_FX_SELL_ID,
        TM_SWAP_BUY_ID,
        TM_SWAP_SELL_ID,
        TM_MARGIN_LOAN_TYPE_ID,
        TM_MARGIN_LOAN_QUALITY_ID,
        TM_MARGIN_LOAN_MATURITY_ID,
        TM_MARGIN_LOAN_BUSINESS_ID,
        TM_MARGIN_LOAN_INDUSTRY_ID,
        *TM_PAGE52_61_SCHEMA_IDS,
        *TM_COVERAGE_SCHEMA_IDS,
        *TM_UNIVERSAL_SCHEMA_IDS,
        LCTT_INVESTMENT_PROPERTY_NET_ID,
        *CDKT_VPB_SCHEMA_IDS,
        LCTT_VPB_COMBINED_LOAN_ID,
        *CDKT_CURRENT_SCHEMA_IDS,
    }
)
CURRENT_MIGRATION_SCHEMA_IDS = frozenset(range(6057, 6061))

CDKT_4325_COMPONENTS = (4364, 4365, 4342, 4341, 4343, 5699)
CDKT_TOTAL_EQUITY_COMPONENTS = (4325, 4306)
KQKD_TOTAL_OPERATING_INCOME_COMPONENTS = (4385, 4386, 4387, 4388, 4389, 4390, 4393)
LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS = (4120, 4121)
LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS = (4144, 4145, 4146)
TM_TOTAL_INTERBANK_PROVISION_COMPONENTS = (583, 590)
CDKT_FX_COMMITMENT_COMPONENTS = (6042, 6043, CDKT_SWAP_COMMITMENT_TOTAL_ID)
TM_PROVISION_MOVEMENT_COMPONENTS = (
    TM_GENERAL_PROVISION_MOVEMENT_ID,
    TM_SPECIFIC_PROVISION_MOVEMENT_ID,
)
TM_PAGE50_TAX_FORMULAS = (
    (5727, (5723, 5725)),
    (5731, (5728, 5729, 5730)),
    (5737, (5732, 5733, 5734, 5735, 5736)),
)
TM_FX_COMMITMENT_COMPONENTS = (TM_FX_BUY_ID, TM_FX_SELL_ID, 1302)
TM_SWAP_COMMITMENT_COMPONENTS = (TM_SWAP_BUY_ID, TM_SWAP_SELL_ID)
TM_PAGE52_FORMULAS = (
    (5750, (5751,)),
    (5753, (5754, 5755)),
    (5756, (5757, 5758)),
    (5759, (5760, 5761)),
)
TM_PAGE53_TOTAL_FORMULAS = tuple(
    (
        5800 + metric_offset,
        tuple(5765 + axis_offset * 7 + metric_offset for axis_offset in range(5)),
    )
    for metric_offset in range(6)
)
TM_PAGE53_PBT_FORMULAS = tuple(
    (
        5770 + axis_offset * 7,
        (5768 + axis_offset * 7, 5769 + axis_offset * 7),
    )
    for axis_offset in range(5)
)
TM_PAGE54_TOTAL_FORMULAS = tuple(
    (
        5843 + metric_offset,
        tuple(5808 + axis_offset * 7 + metric_offset for axis_offset in range(5)),
    )
    for metric_offset in range(6)
)
TM_PAGE54_PBT_FORMULAS = tuple(
    (
        5813 + axis_offset * 7,
        (5811 + axis_offset * 7, 5812 + axis_offset * 7),
    )
    for axis_offset in range(5)
)
TM_PAGE58_COMBINED_FIXED_FORMULAS = (
    (5849, (1363, 1364)),
    (5851, (1389, 1390)),
    (5853, (1441, 1442)),
    (5855, (1467, 1468)),
)
TM_PAGE58_TOTAL_LIABILITY_FORMULAS = (
    (5850, (1367, 1370, 1371, 1372, 1373, 1374)),
    (5852, (1393, 1396, 1397, 1398, 1399, 1400)),
    (5854, (1445, 1448, 1449, 1450, 1451, 1452)),
    (5856, (1471, 1474, 1475, 1476, 1477, 1478)),
)
TM_PAGE57_COMBINED_FIXED_FORMULAS = (
    (5858, (1494, 1495)),
    (5860, (1519, 1520)),
    (5862, (1594, 1595)),
    (5864, (1619, 1620)),
    (5866, (1644, 1645)),
    (5868, (1669, 1670)),
    (5880, (5881, 5882)),
    (5897, (1744, 1745)),
)
TM_PAGE57_SUM_FORMULAS = (
    (5870, (5871, 5872, 5873, 5874, 5875, 5876, 5878, 5879, 5880, 5883)),
    (5884, (5885, 5886, 5887, 5888, 5889, 5890, 5891, 5892)),
    (5895, (5893, 5894)),
)
TM_PAGE57_SUBTRACT_FORMULAS = ((5893, (5870, 5884)),)
TM_COVERAGE_SUM_FORMULAS = (
    (862, (867, 5959)),
    (867, (5960, 5961)),
    (1055, (5977, 1089)),
    (5985, (1143, 1151)),
    (5989, (1157, 1167)),
    (5990, (1188, 1193)),
)
TM_COVERAGE_SUBTRACT_FORMULAS = (
    (5965, (870, 884)),
    (5966, (882, 895)),
    (5970, (915, 930)),
    (5971, (928, 941)),
    (5973, (944, 957)),
    (5974, (955, 965)),
)
TM_UNIVERSAL_SUM_FORMULAS = (
    (5991, tuple(range(871, 876))),
    (5992, tuple(range(876, 882))),
    (5994, tuple(range(885, 888))),
    (5995, tuple(range(888, 895))),
    (5997, tuple(range(916, 921))),
    (5999, tuple(range(931, 934))),
    (6000, tuple(range(934, 941))),
    (6002, tuple(range(945, 952))),
    (6003, tuple(range(952, 955))),
    (6005, tuple(range(958, 961))),
    (6019, tuple(range(1130, 1137))),
    (6020, tuple(range(1137, 1141))),
    (1170, (6024, 6025)),
)

BUSINESS_FORMULAS: tuple[dict[str, object], ...] = (
    {
        "statement_type": "CDKT",
        "schema_id": CDKT_OFF_BALANCE_TOTAL_ID,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_OFF_BALANCE_TOTAL_COMPONENTS),
    },
    {
        "statement_type": "CDKT",
        "schema_id": 6041,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_FX_COMMITMENT_COMPONENTS),
    },
    {
        "statement_type": "CDKT",
        "schema_id": CDKT_SWAP_COMMITMENT_TOTAL_ID,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_SWAP_COMMITMENT_TOTAL_COMPONENTS),
    },
    {
        "statement_type": "CDKT",
        "schema_id": 4325,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_4325_COMPONENTS),
    },
    {
        "statement_type": "CDKT",
        "schema_id": CDKT_TOTAL_EQUITY_ID,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_TOTAL_EQUITY_COMPONENTS),
    },
    {
        "statement_type": "KQKD",
        "schema_id": KQKD_TOTAL_OPERATING_INCOME_ID,
        "operator": "SUM",
        "component_schema_ids": list(KQKD_TOTAL_OPERATING_INCOME_COMPONENTS),
    },
    {
        "statement_type": "LCTT",
        "schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
        "operator": "SUM",
        "component_schema_ids": list(LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS),
    },
    {
        "statement_type": "LCTT",
        "schema_id": LCTT_INVESTMENT_PROPERTY_NET_ID,
        "operator": "SUM",
        "component_schema_ids": list(LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS),
    },
    {
        "statement_type": "TM",
        "schema_id": TM_TOTAL_INTERBANK_PROVISION_ID,
        "operator": "SUM",
        "component_schema_ids": list(TM_TOTAL_INTERBANK_PROVISION_COMPONENTS),
    },
    {
        "statement_type": "TM",
        "schema_id": TM_PROVISION_MOVEMENT_ID,
        "operator": "SUM",
        "component_schema_ids": list(TM_PROVISION_MOVEMENT_COMPONENTS),
    },
    *(
        {
            "statement_type": "TM",
            "schema_id": schema_id,
            "operator": "SUM",
            "component_schema_ids": list(component_ids),
        }
        for schema_id, component_ids in TM_PAGE50_TAX_FORMULAS
    ),
    {
        "statement_type": "TM",
        "schema_id": 1301,
        "operator": "SUM",
        "component_schema_ids": list(TM_FX_COMMITMENT_COMPONENTS),
    },
    {
        "statement_type": "TM",
        "schema_id": 1302,
        "operator": "SUM",
        "component_schema_ids": list(TM_SWAP_COMMITMENT_COMPONENTS),
    },
    *(
        {
            "statement_type": "TM",
            "schema_id": schema_id,
            "operator": "SUM",
            "component_schema_ids": list(component_ids),
        }
        for schema_id, component_ids in (
            *TM_PAGE52_FORMULAS,
            *TM_PAGE53_TOTAL_FORMULAS,
            *TM_PAGE54_TOTAL_FORMULAS,
            *TM_PAGE58_COMBINED_FIXED_FORMULAS,
            *TM_PAGE58_TOTAL_LIABILITY_FORMULAS,
            *TM_PAGE57_COMBINED_FIXED_FORMULAS,
            *TM_PAGE57_SUM_FORMULAS,
            *TM_COVERAGE_SUM_FORMULAS,
            *TM_UNIVERSAL_SUM_FORMULAS,
        )
    ),
    *(
        {
            "statement_type": "TM",
            "schema_id": schema_id,
            "operator": "SUBTRACT",
            "component_schema_ids": list(component_ids),
        }
        for schema_id, component_ids in (
            *TM_PAGE53_PBT_FORMULAS,
            *TM_PAGE54_PBT_FORMULAS,
            *TM_PAGE57_SUBTRACT_FORMULAS,
            *TM_COVERAGE_SUBTRACT_FORMULAS,
        )
    ),
    {
        "statement_type": "TM",
        "schema_id": 5948,
        "operator": "MULTIPLY_DIVIDE_ROUND_HALF_UP",
        "component_schema_ids": [1131, 5947],
        "multiply_component_schema_id": 1131,
        "multiplier": 1_000_000,
        "divide_component_schema_id": 5947,
        "round_to_decimal_places": 0,
    },
    {
        "statement_type": "TM",
        "schema_id": 5984,
        "operator": "MULTIPLY_DIVIDE_ROUND_HALF_UP",
        "component_schema_ids": [5982, 5983],
        "multiply_component_schema_ids": [5982, 5983],
        "divisor": 1_000_000,
        "round_to_decimal_places": 0,
    },
)

_SHEET_MEMBER = "xl/worksheets/sheet1.xml"
_SHARED_STRINGS_MEMBER = "xl/sharedStrings.xml"
_TARGET_MEMBERS = frozenset({_SHEET_MEMBER, _SHARED_STRINGS_MEMBER})
_ROW_PATTERN = re.compile(rb'<row r="(?P<row>\d+)"[^>]*>.*?</row>', re.DOTALL)


class BusinessSchemaUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class BusinessSchemaUpdateResult:
    status: str
    audit_path: str
    workbook_sha256: dict[str, str]


def _member_hashes(payload: bytes) -> dict[str, str]:
    with ZipFile(io.BytesIO(payload)) as archive:
        return {
            info.filename: hashlib.sha256(archive.read(info.filename)).hexdigest()
            for info in archive.infolist()
        }


def _identity_records(path: Path) -> list[dict[str, object]]:
    return [
        {
            "source_row": source_row,
            "ordinal": row.get("A", ""),
            "report_norm_id": row.get("B", ""),
            "report_norm_name": row.get("C", ""),
        }
        for source_row, row in enumerate(read_rows(path), start=1)
    ]


def _item_pairs(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "report_norm_id": record["report_norm_id"],
            "report_norm_name": record["report_norm_name"],
        }
        for record in records
        if record["report_norm_id"] != "ReportNormId"
    ]


def _records_hash(records: Iterable[dict[str, object]]) -> str:
    return stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records
    )


def _replace_once(payload: bytes, old: bytes, new: bytes, *, description: str) -> bytes:
    if payload.count(old) != 1:
        raise BusinessSchemaUpdateError(f"expected exactly one {description} marker")
    return payload.replace(old, new, 1)


def _xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _patch_shared_strings(
    payload: bytes,
    *,
    append_name: str,
    replace_name: tuple[str, str] | None = None,
) -> tuple[bytes, int]:
    escaped_append_name = _xml_escape(append_name).encode("utf-8")
    exact_name_pattern = re.compile(rb"<t(?:\s[^>]*)?>" + re.escape(escaped_append_name) + rb"</t>")
    if exact_name_pattern.search(payload):
        raise BusinessSchemaUpdateError(f"shared string already contains {append_name!r}")
    if replace_name is not None:
        old_name, new_name = replace_name
        payload = _replace_once(
            payload,
            f"<t>{_xml_escape(old_name)}</t>".encode(),
            f"<t>{_xml_escape(new_name)}</t>".encode(),
            description=f"shared-string correction {old_name!r}",
        )

    root_match = re.search(rb"<sst\b[^>]*>", payload)
    if root_match is None:
        raise BusinessSchemaUpdateError("sharedStrings.xml has no sst root")
    root = root_match.group(0)
    count_match = re.search(rb'\bcount="(\d+)"', root)
    unique_match = re.search(rb'\buniqueCount="(\d+)"', root)
    if count_match is None or unique_match is None:
        raise BusinessSchemaUpdateError("sharedStrings.xml lacks count metadata")
    count = int(count_match.group(1))
    unique_count = int(unique_match.group(1))
    if unique_count != payload.count(b"<si>"):
        raise BusinessSchemaUpdateError("shared-string declared/actual unique counts differ")
    new_root = root.replace(
        count_match.group(0), f'count="{count + 1}"'.encode("ascii"), 1
    ).replace(unique_match.group(0), f'uniqueCount="{unique_count + 1}"'.encode("ascii"), 1)
    patched = _replace_once(payload, root, new_root, description="shared-string root")
    appended = f"<si><t>{_xml_escape(append_name)}</t></si></sst>".encode()
    patched = _replace_once(
        patched,
        b"</sst>",
        appended,
        description="shared-string closing tag",
    )
    return patched, unique_count


def _append_or_reuse_shared_string(payload: bytes, *, name: str) -> tuple[bytes, int]:
    escaped_name = _xml_escape(name).encode("utf-8")
    exact_name_pattern = re.compile(rb"<t(?:\s[^>]*)?>" + re.escape(escaped_name) + rb"</t>")
    blocks = re.findall(rb"<si>.*?</si>", payload, re.DOTALL)
    matches = [index for index, block in enumerate(blocks) if exact_name_pattern.search(block)]
    if len(matches) > 1:
        raise BusinessSchemaUpdateError(f"shared string is not unique for {name!r}")
    if matches:
        return payload, matches[0]
    return _patch_shared_strings(payload, append_name=name)


def _shift_row(payload: bytes, *, source_row: int) -> bytes:
    shifted = source_row + 1
    result = _replace_once(
        payload,
        f'<row r="{source_row}"'.encode("ascii"),
        f'<row r="{shifted}"'.encode("ascii"),
        description=f"row {source_row} coordinate",
    )
    for column in "ABC":
        result = _replace_once(
            result,
            f'r="{column}{source_row}"'.encode("ascii"),
            f'r="{column}{shifted}"'.encode("ascii"),
            description=f"cell {column}{source_row} coordinate",
        )
    ordinal_pattern = re.compile(
        rb'(<c r="A' + str(shifted).encode("ascii") + rb'"[^>]*><v>)(\d+)(</v></c>)'
    )
    match = ordinal_pattern.search(result)
    if match is None:
        raise BusinessSchemaUpdateError(f"row {source_row} has no ordinal cell")
    ordinal = int(match.group(2))
    return ordinal_pattern.sub(
        match.group(1) + str(ordinal + 1).encode("ascii") + match.group(3),
        result,
        count=1,
    )


def _insert_sheet_row(
    payload: bytes,
    *,
    before_row_count: int,
    insert_source_row: int,
    schema_id: int,
    display_order: int,
    shared_string_index: int,
) -> bytes:
    patched = _replace_once(
        payload,
        f'<dimension ref="A1:C{before_row_count}"/>'.encode("ascii"),
        f'<dimension ref="A1:C{before_row_count + 1}"/>'.encode("ascii"),
        description="worksheet dimension",
    )
    matches = list(_ROW_PATTERN.finditer(patched))
    row_numbers = [int(match.group("row")) for match in matches]
    if row_numbers != list(range(1, before_row_count + 1)):
        raise BusinessSchemaUpdateError("worksheet row coordinates are not contiguous")

    parts: list[bytes] = []
    cursor = 0
    inserted = False
    row_attributes = (
        ' spans="1:3" ht="15" x14ac:dyDescent="0.2"'
        if b"xmlns:x14ac=" in patched
        else ' spans="1:3"'
    )
    new_row = (
        f'<row r="{insert_source_row}"{row_attributes}>'
        f'<c r="A{insert_source_row}" s="1"><v>{display_order}</v></c>'
        f'<c r="B{insert_source_row}"><v>{schema_id}</v></c>'
        f'<c r="C{insert_source_row}" t="s"><v>{shared_string_index}</v></c></row>'
    ).encode("ascii")
    for match in matches:
        source_row = int(match.group("row"))
        parts.append(patched[cursor : match.start()])
        if source_row == insert_source_row:
            parts.append(new_row)
            inserted = True
        row_payload = match.group(0)
        parts.append(
            _shift_row(row_payload, source_row=source_row)
            if source_row >= insert_source_row
            else row_payload
        )
        cursor = match.end()
    parts.append(patched[cursor:])
    if not inserted and insert_source_row == before_row_count + 1:
        patched_tail = parts.pop()
        closing = b"</sheetData>"
        if patched_tail.count(closing) != 1:
            raise BusinessSchemaUpdateError("worksheet sheetData closing tag drifted")
        parts.append(patched_tail.replace(closing, new_row + closing, 1))
        inserted = True
    if not inserted:
        raise BusinessSchemaUpdateError(f"worksheet insertion row {insert_source_row} is absent")
    return b"".join(parts)


def _insert_ordered_schema_row(
    payload: bytes,
    *,
    before_row_count: int,
    schema_id: int,
    predecessor_id: int,
    successor_id: int | None,
    shared_string_index: int,
) -> bytes:
    order = _sheet_schema_id_order(payload, row_count=before_row_count)
    try:
        predecessor_index = order.index(predecessor_id)
    except ValueError as exc:
        raise BusinessSchemaUpdateError(
            f"schema insertion predecessor is absent: {predecessor_id}"
        ) from exc
    if successor_id is None:
        if predecessor_index != len(order) - 1:
            raise BusinessSchemaUpdateError(
                f"schema insertion predecessor is not final: {predecessor_id}"
            )
        insert_source_row = before_row_count + 1
    else:
        try:
            successor_index = order.index(successor_id)
        except ValueError as exc:
            raise BusinessSchemaUpdateError(
                f"schema insertion successor is absent: {successor_id}"
            ) from exc
        if successor_index != predecessor_index + 1:
            raise BusinessSchemaUpdateError(
                f"schema insertion anchors are not adjacent: {predecessor_id}/{successor_id}"
            )
        insert_source_row = successor_index + 2
    return _insert_sheet_row(
        payload,
        before_row_count=before_row_count,
        insert_source_row=insert_source_row,
        schema_id=schema_id,
        display_order=insert_source_row - 2,
        shared_string_index=shared_string_index,
    )


def _source_row_for_schema_id(payload: bytes, *, row_count: int, schema_id: int) -> int:
    order = _sheet_schema_id_order(payload, row_count=row_count)
    try:
        return order.index(schema_id) + 2
    except ValueError as exc:
        raise BusinessSchemaUpdateError(f"schema ID is absent from worksheet: {schema_id}") from exc


def _sheet_schema_id_order(payload: bytes, *, row_count: int) -> tuple[int, ...]:
    """Read the numeric schema-ID order and fail if row/ordinal geometry drifted."""

    matches = list(_ROW_PATTERN.finditer(payload))
    row_numbers = [int(match.group("row")) for match in matches]
    if row_numbers != list(range(1, row_count + 1)):
        raise BusinessSchemaUpdateError("worksheet row coordinates are not contiguous")
    schema_ids: list[int] = []
    for source_row, match in enumerate(matches[1:], start=2):
        row_payload = match.group(0)
        ordinal_match = re.search(
            rb'<c r="A' + str(source_row).encode("ascii") + rb'"[^>]*><v>(\d+)</v></c>',
            row_payload,
        )
        schema_id_match = re.search(
            rb'<c r="B' + str(source_row).encode("ascii") + rb'"[^>]*><v>(\d+)</v></c>',
            row_payload,
        )
        if (
            ordinal_match is None
            or int(ordinal_match.group(1)) != source_row - 2
            or schema_id_match is None
        ):
            raise BusinessSchemaUpdateError(
                f"worksheet schema identity/ordinal drifted at row {source_row}"
            )
        schema_ids.append(int(schema_id_match.group(1)))
    if len(schema_ids) != len(set(schema_ids)):
        raise BusinessSchemaUpdateError("worksheet contains duplicate schema IDs")
    return tuple(schema_ids)


def _insert_tm_coverage_rows(
    payload: bytes,
    *,
    before_row_count: int,
    shared_string_indices: dict[int, int],
) -> bytes:
    """Insert all coverage additions by adjacent ID anchors, never row arithmetic."""

    patched = payload
    row_count = before_row_count
    for schema_ids, predecessor, successor in TM_COVERAGE_DISPLAY_CHAINS:
        active_predecessor = predecessor
        for schema_id in schema_ids:
            order = _sheet_schema_id_order(patched, row_count=row_count)
            if active_predecessor not in order or successor not in order:
                raise BusinessSchemaUpdateError(
                    f"TM {schema_id} insertion anchor is absent: {active_predecessor}/{successor}"
                )
            predecessor_index = order.index(active_predecessor)
            successor_index = order.index(successor)
            if successor_index != predecessor_index + 1:
                raise BusinessSchemaUpdateError(
                    f"TM {schema_id} insertion anchors are not adjacent: "
                    f"{active_predecessor}/{successor}"
                )
            insert_source_row = successor_index + 2
            patched = _insert_sheet_row(
                patched,
                before_row_count=row_count,
                insert_source_row=insert_source_row,
                schema_id=schema_id,
                display_order=insert_source_row - 2,
                shared_string_index=shared_string_indices[schema_id],
            )
            row_count += 1
            active_predecessor = schema_id
    if row_count != TM_AFTER_ROW_COUNT - len(TM_UNIVERSAL_SCHEMA_ITEMS):
        raise BusinessSchemaUpdateError("TM coverage insertion row count drifted")
    return patched


def _insert_tm_universal_rows(
    payload: bytes,
    *,
    before_row_count: int,
    shared_string_indices: dict[int, int],
) -> bytes:
    """Insert evidence-backed universal items using accounting-order anchors."""

    patched = payload
    row_count = before_row_count
    for schema_ids, predecessor, successor in TM_UNIVERSAL_DISPLAY_CHAINS:
        active_predecessor = predecessor
        for schema_id in schema_ids:
            order = _sheet_schema_id_order(patched, row_count=row_count)
            if active_predecessor not in order or successor not in order:
                raise BusinessSchemaUpdateError(
                    f"TM {schema_id} universal insertion anchor is absent: "
                    f"{active_predecessor}/{successor}"
                )
            predecessor_index = order.index(active_predecessor)
            successor_index = order.index(successor)
            if successor_index != predecessor_index + 1:
                raise BusinessSchemaUpdateError(
                    f"TM {schema_id} universal insertion anchors are not adjacent: "
                    f"{active_predecessor}/{successor}"
                )
            insert_source_row = successor_index + 2
            patched = _insert_sheet_row(
                patched,
                before_row_count=row_count,
                insert_source_row=insert_source_row,
                schema_id=schema_id,
                display_order=insert_source_row - 2,
                shared_string_index=shared_string_indices[schema_id],
            )
            row_count += 1
            active_predecessor = schema_id
    if row_count != TM_AFTER_ROW_COUNT:
        raise BusinessSchemaUpdateError("TM universal insertion row count drifted")
    return patched


def _retarget_shared_string_cell(
    payload: bytes,
    *,
    source_row: int,
    shared_string_index: int,
) -> bytes:
    pattern = re.compile(
        rb'(<c r="C' + str(source_row).encode("ascii") + rb'" t="s"><v>)(\d+)(</v></c>)'
    )
    matches = list(pattern.finditer(payload))
    if len(matches) != 1:
        raise BusinessSchemaUpdateError(f"expected exactly one shared-string cell at C{source_row}")
    return pattern.sub(
        lambda match: match.group(1) + str(shared_string_index).encode("ascii") + match.group(3),
        payload,
        count=1,
    )


def _build_updated_workbook(
    before: bytes,
    *,
    statement_type: str,
) -> tuple[bytes, dict[str, str], dict[str, str]]:
    before_hashes = _member_hashes(before)
    with ZipFile(io.BytesIO(before)) as source:
        if statement_type == "CDKT":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=CDKT_TOTAL_EQUITY_NAME,
                replace_name=(CDKT_4350_OLD_NAME, CDKT_4350_CORRECTED_NAME),
            )
            sheet = _insert_sheet_row(
                source.read(_SHEET_MEMBER),
                before_row_count=CDKT_BEFORE_ROW_COUNT,
                insert_source_row=CDKT_TOTAL_EQUITY_SOURCE_ROW,
                schema_id=CDKT_TOTAL_EQUITY_ID,
                display_order=CDKT_TOTAL_EQUITY_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
            vpb_string_indices: dict[int, int] = {}
            for schema_id, name, *_rest in CDKT_VPB_SCHEMA_ITEMS:
                shared_strings, vpb_string_indices[schema_id] = _append_or_reuse_shared_string(
                    shared_strings,
                    name=name,
                )
            for schema_id, name in (
                (CDKT_OFF_BALANCE_TOTAL_ID, CDKT_OFF_BALANCE_TOTAL_NAME),
                (CDKT_SWAP_COMMITMENT_TOTAL_ID, CDKT_SWAP_COMMITMENT_TOTAL_NAME),
            ):
                shared_strings, vpb_string_indices[schema_id] = _append_or_reuse_shared_string(
                    shared_strings,
                    name=name,
                )
            shared_strings, borrowing_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=CDKT_4360_CORRECTED_NAME,
            )
            shared_strings, deposit_borrowing_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=CDKT_4319_CORRECTED_NAME,
            )
            row_count = CDKT_BEFORE_ROW_COUNT + 1
            for schema_id, predecessor_id, successor_id in (
                (6035, 4346, 4347),
                (6036, 4351, 4352),
                (6037, 4318, 4319),
                (6038, 4305, None),
                *(
                    (schema_id, CDKT_OFF_BALANCE_DISPLAY_SEQUENCE[index - 1], None)
                    for index, schema_id in enumerate(CDKT_OFF_BALANCE_DISPLAY_SEQUENCE)
                    if index > 0
                ),
            ):
                sheet = _insert_ordered_schema_row(
                    sheet,
                    before_row_count=row_count,
                    schema_id=schema_id,
                    predecessor_id=predecessor_id,
                    successor_id=successor_id,
                    shared_string_index=vpb_string_indices[schema_id],
                )
                row_count += 1
            sheet = _retarget_shared_string_cell(
                sheet,
                source_row=_source_row_for_schema_id(
                    sheet,
                    row_count=CDKT_AFTER_ROW_COUNT,
                    schema_id=4360,
                ),
                shared_string_index=borrowing_string_index,
            )
            sheet = _retarget_shared_string_cell(
                sheet,
                source_row=_source_row_for_schema_id(
                    sheet,
                    row_count=CDKT_AFTER_ROW_COUNT,
                    schema_id=4319,
                ),
                shared_string_index=deposit_borrowing_string_index,
            )
        elif statement_type == "KQKD":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=KQKD_TOTAL_OPERATING_INCOME_NAME,
            )
            sheet = _insert_sheet_row(
                source.read(_SHEET_MEMBER),
                before_row_count=KQKD_BEFORE_ROW_COUNT,
                insert_source_row=KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW,
                schema_id=KQKD_TOTAL_OPERATING_INCOME_ID,
                display_order=KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
            shared_strings, correction_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=KQKD_4382_CORRECTED_NAME,
            )
            sheet = _retarget_shared_string_cell(
                sheet,
                source_row=_source_row_for_schema_id(
                    sheet,
                    row_count=KQKD_AFTER_ROW_COUNT,
                    schema_id=4382,
                ),
                shared_string_index=correction_string_index,
            )
        elif statement_type == "LCTT":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=LCTT_INVESTMENT_CONTRIBUTION_NET_NAME,
            )
            shared_strings, property_net_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=LCTT_INVESTMENT_PROPERTY_NET_NAME,
            )
            sheet = _insert_sheet_row(
                source.read(_SHEET_MEMBER),
                before_row_count=LCTT_BEFORE_ROW_COUNT,
                insert_source_row=LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW - 1,
                schema_id=LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
                display_order=LCTT_INVESTMENT_CONTRIBUTION_NET_DISPLAY_ORDER - 1,
                shared_string_index=shared_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=LCTT_BEFORE_ROW_COUNT + 1,
                insert_source_row=LCTT_INVESTMENT_PROPERTY_NET_SOURCE_ROW,
                schema_id=LCTT_INVESTMENT_PROPERTY_NET_ID,
                display_order=LCTT_INVESTMENT_PROPERTY_NET_DISPLAY_ORDER,
                shared_string_index=property_net_string_index,
            )
            shared_strings, combined_loan_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=LCTT_VPB_COMBINED_LOAN_NAME,
            )
            sheet = _insert_ordered_schema_row(
                sheet,
                before_row_count=LCTT_BEFORE_ROW_COUNT + 2,
                schema_id=LCTT_VPB_COMBINED_LOAN_ID,
                predecessor_id=LCTT_VPB_COMBINED_LOAN_PREDECESSOR_ID,
                successor_id=LCTT_VPB_COMBINED_LOAN_SUCCESSOR_ID,
                shared_string_index=combined_loan_string_index,
            )
            shared_strings, correction_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=LCTT_4109_CORRECTED_NAME,
            )
            sheet = _retarget_shared_string_cell(
                sheet,
                source_row=_source_row_for_schema_id(
                    sheet,
                    row_count=LCTT_AFTER_ROW_COUNT,
                    schema_id=4109,
                ),
                shared_string_index=correction_string_index,
            )
            shared_strings, deposit_borrowing_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=LCTT_4136_CORRECTED_NAME,
            )
            sheet = _retarget_shared_string_cell(
                sheet,
                source_row=_source_row_for_schema_id(
                    sheet,
                    row_count=LCTT_AFTER_ROW_COUNT,
                    schema_id=4136,
                ),
                shared_string_index=deposit_borrowing_string_index,
            )
        elif statement_type == "TM":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=TM_TOTAL_INTERBANK_PROVISION_NAME,
            )
            shared_strings, correction_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_770_CORRECTED_NAME,
            )
            shared_strings, education_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_EDUCATION_NAME,
            )
            shared_strings, health_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_HEALTH_SOCIAL_NAME,
            )
            shared_strings, arts_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_ARTS_RECREATION_NAME,
            )
            shared_strings, other_services_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_OTHER_SERVICES_NAME,
            )
            shared_strings, household_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_HOUSEHOLD_EMPLOYMENT_NAME,
            )
            shared_strings, purchased_principal_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_PURCHASED_PRINCIPAL_NAME,
            )
            shared_strings, purchased_interest_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_PURCHASED_INTEREST_NAME,
            )
            shared_strings, guaranteed_debt_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_GOVERNMENT_GUARANTEED_DEBT_NAME,
            )
            shared_strings, fx_buy_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_FX_BUY_NAME,
            )
            shared_strings, fx_sell_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_FX_SELL_NAME,
            )
            shared_strings, swap_buy_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_SWAP_BUY_NAME,
            )
            shared_strings, swap_sell_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_SWAP_SELL_NAME,
            )
            shared_strings, margin_loan_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_MARGIN_LOAN_CANONICAL_NAME,
            )
            shared_strings, margin_quality_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_MARGIN_LOAN_QUALITY_NAME,
            )
            tax_string_indices: dict[int, int] = {}
            for schema_id, name in TM_PAGE50_TAX_SCHEMA_ITEMS:
                shared_strings, tax_string_indices[schema_id] = _append_or_reuse_shared_string(
                    shared_strings,
                    name=name,
                )
            page52_61_string_indices: dict[int, int] = {}
            for (
                schema_id,
                name,
                _source_row,
                _order,
                _parent_id,
                _level,
            ) in TM_PAGE52_61_SCHEMA_ITEMS:
                shared_strings, page52_61_string_indices[schema_id] = (
                    _append_or_reuse_shared_string(shared_strings, name=name)
                )
            coverage_string_indices: dict[int, int] = {}
            for schema_id, name, _parent_id, _level in TM_COVERAGE_SCHEMA_ITEMS:
                shared_strings, coverage_string_indices[schema_id] = _append_or_reuse_shared_string(
                    shared_strings, name=name
                )
            universal_string_indices: dict[int, int] = {}
            for schema_id, name, _parent_id, _level in TM_UNIVERSAL_SCHEMA_ITEMS:
                shared_strings, universal_string_indices[schema_id] = (
                    _append_or_reuse_shared_string(shared_strings, name=name)
                )
            baseline_sheet = _retarget_shared_string_cell(
                source.read(_SHEET_MEMBER),
                source_row=TM_770_BASELINE_SOURCE_ROW,
                shared_string_index=correction_string_index,
            )
            baseline_sheet = _retarget_shared_string_cell(
                baseline_sheet,
                source_row=TM_EDUCATION_BASELINE_SOURCE_ROW,
                shared_string_index=education_string_index,
            )
            sheet = _insert_sheet_row(
                baseline_sheet,
                before_row_count=TM_BEFORE_ROW_COUNT,
                insert_source_row=TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW,
                schema_id=TM_TOTAL_INTERBANK_PROVISION_ID,
                display_order=TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 1,
                insert_source_row=TM_MARGIN_LOAN_TYPE_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_TYPE_ID,
                display_order=TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 2,
                insert_source_row=TM_HEALTH_SOCIAL_SOURCE_ROW,
                schema_id=TM_HEALTH_SOCIAL_ID,
                display_order=TM_HEALTH_SOCIAL_DISPLAY_ORDER,
                shared_string_index=health_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 3,
                insert_source_row=TM_ARTS_RECREATION_SOURCE_ROW,
                schema_id=TM_ARTS_RECREATION_ID,
                display_order=TM_ARTS_RECREATION_DISPLAY_ORDER,
                shared_string_index=arts_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 4,
                insert_source_row=TM_OTHER_SERVICES_SOURCE_ROW,
                schema_id=TM_OTHER_SERVICES_ID,
                display_order=TM_OTHER_SERVICES_DISPLAY_ORDER,
                shared_string_index=other_services_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 5,
                insert_source_row=TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW,
                schema_id=TM_HOUSEHOLD_EMPLOYMENT_ID,
                display_order=TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER,
                shared_string_index=household_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 6,
                insert_source_row=TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_INDUSTRY_ID,
                display_order=TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 7,
                insert_source_row=TM_MARGIN_LOAN_QUALITY_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_QUALITY_ID,
                display_order=TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER,
                shared_string_index=margin_quality_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 8,
                insert_source_row=TM_MARGIN_LOAN_MATURITY_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_MATURITY_ID,
                display_order=TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 9,
                insert_source_row=TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW - 1,
                schema_id=TM_MARGIN_LOAN_BUSINESS_ID,
                display_order=TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER - 1,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 10,
                insert_source_row=TM_PURCHASED_PRINCIPAL_SOURCE_ROW - 1,
                schema_id=TM_PURCHASED_PRINCIPAL_ID,
                display_order=TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER - 1,
                shared_string_index=purchased_principal_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 11,
                insert_source_row=TM_PURCHASED_INTEREST_SOURCE_ROW - 1,
                schema_id=TM_PURCHASED_INTEREST_ID,
                display_order=TM_PURCHASED_INTEREST_DISPLAY_ORDER - 1,
                shared_string_index=purchased_interest_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 12,
                insert_source_row=TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW - 1,
                schema_id=TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                display_order=TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER - 1,
                shared_string_index=guaranteed_debt_string_index,
            )
            for offset, (schema_id, _name) in enumerate(TM_PAGE50_TAX_SCHEMA_ITEMS):
                sheet = _insert_sheet_row(
                    sheet,
                    before_row_count=TM_BEFORE_ROW_COUNT + 13 + offset,
                    insert_source_row=TM_PAGE50_TAX_INSERT_SOURCE_ROW - 4 + offset,
                    schema_id=schema_id,
                    display_order=TM_PAGE50_TAX_INSERT_DISPLAY_ORDER - 4 + offset,
                    shared_string_index=tax_string_indices[schema_id],
                )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 28,
                insert_source_row=TM_FX_BUY_SOURCE_ROW - 7,
                schema_id=TM_FX_BUY_ID,
                display_order=TM_FX_BUY_DISPLAY_ORDER - 7,
                shared_string_index=fx_buy_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 29,
                insert_source_row=TM_FX_SELL_SOURCE_ROW - 7,
                schema_id=TM_FX_SELL_ID,
                display_order=TM_FX_SELL_DISPLAY_ORDER - 7,
                shared_string_index=fx_sell_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 30,
                insert_source_row=TM_SWAP_BUY_SOURCE_ROW - 7,
                schema_id=TM_SWAP_BUY_ID,
                display_order=TM_SWAP_BUY_DISPLAY_ORDER - 7,
                shared_string_index=swap_buy_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 31,
                insert_source_row=TM_SWAP_SELL_SOURCE_ROW - 7,
                schema_id=TM_SWAP_SELL_ID,
                display_order=TM_SWAP_SELL_DISPLAY_ORDER - 7,
                shared_string_index=swap_sell_string_index,
            )
            before_new_business_rows = (
                TM_AFTER_ROW_COUNT
                - len(TM_PAGE52_61_SCHEMA_ITEMS)
                - len(TM_COVERAGE_SCHEMA_ITEMS)
                - len(TM_UNIVERSAL_SCHEMA_ITEMS)
            )
            for offset, (
                schema_id,
                _name,
                source_row,
                display_order,
                _parent_id,
                _level,
            ) in enumerate(sorted(TM_PAGE52_61_SCHEMA_ITEMS, key=lambda item: item[2])):
                sheet = _insert_sheet_row(
                    sheet,
                    before_row_count=before_new_business_rows + offset,
                    insert_source_row=source_row,
                    schema_id=schema_id,
                    display_order=display_order,
                    shared_string_index=page52_61_string_indices[schema_id],
                )
            sheet = _insert_tm_coverage_rows(
                sheet,
                before_row_count=(
                    TM_AFTER_ROW_COUNT
                    - len(TM_COVERAGE_SCHEMA_ITEMS)
                    - len(TM_UNIVERSAL_SCHEMA_ITEMS)
                ),
                shared_string_indices=coverage_string_indices,
            )
            sheet = _insert_tm_universal_rows(
                sheet,
                before_row_count=TM_AFTER_ROW_COUNT - len(TM_UNIVERSAL_SCHEMA_ITEMS),
                shared_string_indices=universal_string_indices,
            )
        else:
            raise BusinessSchemaUpdateError(
                f"unsupported business update statement {statement_type}"
            )

        output = io.BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as destination:
            destination.comment = source.comment
            for info in source.infolist():
                member = source.read(info.filename)
                if info.filename == _SHARED_STRINGS_MEMBER:
                    member = shared_strings
                elif info.filename == _SHEET_MEMBER:
                    member = sheet
                destination.writestr(info, member)
    after = output.getvalue()
    after_hashes = _member_hashes(after)
    if set(before_hashes) != set(after_hashes):
        raise BusinessSchemaUpdateError("XLSX ZIP member set changed during business update")
    changed = {name for name in before_hashes if before_hashes[name] != after_hashes[name]}
    if changed != _TARGET_MEMBERS:
        raise BusinessSchemaUpdateError(f"unexpected XLSX members changed: {sorted(changed)}")
    return after, before_hashes, after_hashes


def _assert_contiguous_ordinals(records: Sequence[dict[str, object]], *, statement: str) -> None:
    items = [record for record in records if record["report_norm_id"] != "ReportNormId"]
    ordinals = [record["ordinal"] for record in items]
    if ordinals != [str(index) for index in range(len(items))]:
        raise BusinessSchemaUpdateError(f"{statement} display ordinals are not contiguous")


def _assert_candidate(
    before_path: Path,
    candidate_path: Path,
    *,
    statement: str,
) -> None:
    before = _identity_records(before_path)
    after = _identity_records(candidate_path)
    _assert_contiguous_ordinals(after, statement=statement)
    if statement == "CDKT":
        if len(after) != CDKT_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("CDKT candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        if by_id["4350"]["report_norm_name"] != CDKT_4350_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("CDKT 4350 display correction is absent")
        if by_id["4319"]["report_norm_name"] != CDKT_4319_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("CDKT 4319 display correction is absent")
        if by_id["4360"]["report_norm_name"] != CDKT_4360_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("CDKT 4360 display correction is absent")
        inserted = by_id[str(CDKT_TOTAL_EQUITY_ID)]
        if inserted != {
            "source_row": CDKT_TOTAL_EQUITY_FINAL_SOURCE_ROW,
            "ordinal": str(CDKT_TOTAL_EQUITY_FINAL_DISPLAY_ORDER),
            "report_norm_id": str(CDKT_TOTAL_EQUITY_ID),
            "report_norm_name": CDKT_TOTAL_EQUITY_NAME,
        }:
            raise BusinessSchemaUpdateError("CDKT total-equity identity/position drifted")
        ids = [record["report_norm_id"] for record in after]
        index = ids.index(str(CDKT_TOTAL_EQUITY_ID))
        if (ids[index - 1], ids[index + 1]) != (
            str(CDKT_TOTAL_EQUITY_PREDECESSOR_ID),
            str(CDKT_TOTAL_EQUITY_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("CDKT total-equity anchors drifted")
        expected_vpb_positions = {
            schema_id: (
                CDKT_CUMULATIVE_DISPLAY_ORDERS[schema_id],
                CDKT_CUMULATIVE_DISPLAY_ANCHORS[schema_id][0],
                CDKT_CUMULATIVE_DISPLAY_ANCHORS[schema_id][1],
            )
            for schema_id in (*CDKT_VPB_SCHEMA_IDS, *CDKT_CURRENT_SCHEMA_IDS)
        }
        names = {schema_id: name for schema_id, name, *_rest in CDKT_VPB_SCHEMA_ITEMS}
        names.update(
            {
                CDKT_OFF_BALANCE_TOTAL_ID: CDKT_OFF_BALANCE_TOTAL_NAME,
                CDKT_SWAP_COMMITMENT_TOTAL_ID: CDKT_SWAP_COMMITMENT_TOTAL_NAME,
            }
        )
        for schema_id, (
            display_order,
            predecessor_id,
            successor_id,
        ) in expected_vpb_positions.items():
            record = by_id[str(schema_id)]
            if record != {
                "source_row": display_order + 2,
                "ordinal": str(display_order),
                "report_norm_id": str(schema_id),
                "report_norm_name": names[schema_id],
            }:
                raise BusinessSchemaUpdateError(f"CDKT {schema_id} identity/position drifted")
            position = ids.index(str(schema_id))
            actual_predecessor = ids[position - 1] if position else None
            actual_successor = ids[position + 1] if position + 1 < len(ids) else None
            if (actual_predecessor, actual_successor) != (
                str(predecessor_id) if predecessor_id is not None else None,
                str(successor_id) if successor_id is not None else None,
            ):
                raise BusinessSchemaUpdateError(f"CDKT {schema_id} anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"]
            not in {
                str(CDKT_TOTAL_EQUITY_ID),
                *(str(item) for item in CDKT_VPB_SCHEMA_IDS),
                *(str(item) for item in CDKT_CURRENT_SCHEMA_IDS),
            }
        ]
        for record in new_pairs:
            if record["report_norm_id"] == "4350":
                record["report_norm_name"] = CDKT_4350_OLD_NAME
            elif record["report_norm_id"] == "4319":
                record["report_norm_name"] = CDKT_4319_OLD_NAME
            elif record["report_norm_id"] == "4360":
                record["report_norm_name"] = CDKT_4360_OLD_NAME
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("CDKT candidate changed an unauthorized identity/order")
    elif statement == "KQKD":
        if len(after) != KQKD_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("KQKD candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        if by_id["4382"]["report_norm_name"] != KQKD_4382_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("KQKD 4382 display correction is absent")
        inserted = by_id[str(KQKD_TOTAL_OPERATING_INCOME_ID)]
        if inserted != {
            "source_row": KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW,
            "ordinal": str(KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER),
            "report_norm_id": str(KQKD_TOTAL_OPERATING_INCOME_ID),
            "report_norm_name": KQKD_TOTAL_OPERATING_INCOME_NAME,
        }:
            raise BusinessSchemaUpdateError("KQKD total-operating-income identity/position drifted")
        ids = [record["report_norm_id"] for record in after]
        index = ids.index(str(KQKD_TOTAL_OPERATING_INCOME_ID))
        if (ids[index - 1], ids[index + 1]) != (
            str(KQKD_TOTAL_OPERATING_INCOME_PREDECESSOR_ID),
            str(KQKD_TOTAL_OPERATING_INCOME_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("KQKD total-operating-income anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"] != str(KQKD_TOTAL_OPERATING_INCOME_ID)
        ]
        for record in new_pairs:
            if record["report_norm_id"] == "4382":
                record["report_norm_name"] = KQKD_4382_OLD_NAME
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("KQKD candidate changed an existing identity/order")
    elif statement == "LCTT":
        if len(after) != LCTT_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("LCTT candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        inserted = by_id[str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID)]
        if inserted != {
            "source_row": LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_SOURCE_ROW,
            "ordinal": str(LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_DISPLAY_ORDER),
            "report_norm_id": str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID),
            "report_norm_name": LCTT_INVESTMENT_CONTRIBUTION_NET_NAME,
        }:
            raise BusinessSchemaUpdateError(
                "LCTT investment-contribution aggregate identity/position drifted"
            )
        ids = [record["report_norm_id"] for record in after]
        index = ids.index(str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID))
        if (ids[index - 1], ids[index + 1]) != (
            str(LCTT_INVESTMENT_CONTRIBUTION_NET_PREDECESSOR_ID),
            str(LCTT_INVESTMENT_CONTRIBUTION_NET_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("LCTT investment-contribution anchors drifted")
        property_net = by_id[str(LCTT_INVESTMENT_PROPERTY_NET_ID)]
        if property_net != {
            "source_row": LCTT_INVESTMENT_PROPERTY_NET_FINAL_SOURCE_ROW,
            "ordinal": str(LCTT_INVESTMENT_PROPERTY_NET_FINAL_DISPLAY_ORDER),
            "report_norm_id": str(LCTT_INVESTMENT_PROPERTY_NET_ID),
            "report_norm_name": LCTT_INVESTMENT_PROPERTY_NET_NAME,
        }:
            raise BusinessSchemaUpdateError(
                "LCTT investment-property aggregate identity/position drifted"
            )
        property_index = ids.index(str(LCTT_INVESTMENT_PROPERTY_NET_ID))
        if (ids[property_index - 1], ids[property_index + 1]) != (
            str(LCTT_INVESTMENT_PROPERTY_NET_PREDECESSOR_ID),
            str(LCTT_INVESTMENT_PROPERTY_NET_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("LCTT investment-property anchors drifted")
        if by_id["4109"]["report_norm_name"] != LCTT_4109_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("LCTT 4109 display correction is absent")
        if by_id["4136"]["report_norm_name"] != LCTT_4136_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("LCTT 4136 display correction is absent")
        combined_loan = by_id[str(LCTT_VPB_COMBINED_LOAN_ID)]
        if combined_loan != {
            "source_row": LCTT_VPB_COMBINED_LOAN_SOURCE_ROW,
            "ordinal": str(LCTT_VPB_COMBINED_LOAN_DISPLAY_ORDER),
            "report_norm_id": str(LCTT_VPB_COMBINED_LOAN_ID),
            "report_norm_name": LCTT_VPB_COMBINED_LOAN_NAME,
        }:
            raise BusinessSchemaUpdateError("LCTT VPB combined-loan identity/position drifted")
        combined_index = ids.index(str(LCTT_VPB_COMBINED_LOAN_ID))
        if (ids[combined_index - 1], ids[combined_index + 1]) != (
            str(LCTT_VPB_COMBINED_LOAN_PREDECESSOR_ID),
            str(LCTT_VPB_COMBINED_LOAN_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("LCTT VPB combined-loan anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"]
            not in {
                str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID),
                str(LCTT_INVESTMENT_PROPERTY_NET_ID),
                str(LCTT_VPB_COMBINED_LOAN_ID),
            }
        ]
        for record in new_pairs:
            if record["report_norm_id"] == "4109":
                record["report_norm_name"] = LCTT_4109_OLD_NAME
            elif record["report_norm_id"] == "4136":
                record["report_norm_name"] = LCTT_4136_OLD_NAME
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("LCTT candidate changed an existing identity/order")
    elif statement == "TM":
        if len(after) != TM_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("TM candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        if by_id["770"]["report_norm_name"] != TM_770_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("TM 770 display correction is absent")
        if by_id[str(TM_EDUCATION_ID)]["report_norm_name"] != TM_EDUCATION_NAME:
            raise BusinessSchemaUpdateError("TM 737 education display correction is absent")
        additions = (
            (
                TM_TOTAL_INTERBANK_PROVISION_ID,
                TM_TOTAL_INTERBANK_PROVISION_NAME,
                TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW,
                TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER,
            ),
            (
                TM_HEALTH_SOCIAL_ID,
                TM_HEALTH_SOCIAL_NAME,
                TM_HEALTH_SOCIAL_SOURCE_ROW,
                TM_HEALTH_SOCIAL_DISPLAY_ORDER,
            ),
            (
                TM_ARTS_RECREATION_ID,
                TM_ARTS_RECREATION_NAME,
                TM_ARTS_RECREATION_SOURCE_ROW,
                TM_ARTS_RECREATION_DISPLAY_ORDER,
            ),
            (
                TM_OTHER_SERVICES_ID,
                TM_OTHER_SERVICES_NAME,
                TM_OTHER_SERVICES_SOURCE_ROW,
                TM_OTHER_SERVICES_DISPLAY_ORDER,
            ),
            (
                TM_HOUSEHOLD_EMPLOYMENT_ID,
                TM_HOUSEHOLD_EMPLOYMENT_NAME,
                TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW,
                TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER,
            ),
            (
                TM_PURCHASED_PRINCIPAL_ID,
                TM_PURCHASED_PRINCIPAL_NAME,
                TM_PURCHASED_PRINCIPAL_SOURCE_ROW,
                TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER,
            ),
            (
                TM_PURCHASED_INTEREST_ID,
                TM_PURCHASED_INTEREST_NAME,
                TM_PURCHASED_INTEREST_SOURCE_ROW,
                TM_PURCHASED_INTEREST_DISPLAY_ORDER,
            ),
            (
                TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                TM_GOVERNMENT_GUARANTEED_DEBT_NAME,
                TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW,
                TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER,
            ),
            (
                TM_FX_BUY_ID,
                TM_FX_BUY_NAME,
                TM_FX_BUY_SOURCE_ROW,
                TM_FX_BUY_DISPLAY_ORDER,
            ),
            (
                TM_FX_SELL_ID,
                TM_FX_SELL_NAME,
                TM_FX_SELL_SOURCE_ROW,
                TM_FX_SELL_DISPLAY_ORDER,
            ),
            (
                TM_SWAP_BUY_ID,
                TM_SWAP_BUY_NAME,
                TM_SWAP_BUY_SOURCE_ROW,
                TM_SWAP_BUY_DISPLAY_ORDER,
            ),
            (
                TM_SWAP_SELL_ID,
                TM_SWAP_SELL_NAME,
                TM_SWAP_SELL_SOURCE_ROW,
                TM_SWAP_SELL_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_TYPE_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_TYPE_SOURCE_ROW,
                TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_QUALITY_ID,
                TM_MARGIN_LOAN_QUALITY_NAME,
                TM_MARGIN_LOAN_QUALITY_SOURCE_ROW,
                TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_MATURITY_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_MATURITY_SOURCE_ROW,
                TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_BUSINESS_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW,
                TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_INDUSTRY_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW,
                TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER,
            ),
            *(
                (
                    schema_id,
                    name,
                    TM_PAGE50_TAX_INSERT_SOURCE_ROW + offset,
                    TM_PAGE50_TAX_INSERT_DISPLAY_ORDER + offset,
                )
                for offset, (schema_id, name) in enumerate(TM_PAGE50_TAX_SCHEMA_ITEMS)
            ),
        )
        for schema_id, name, _source_row, _display_order in additions:
            record = by_id[str(schema_id)]
            if record["report_norm_name"] != name or record["ordinal"] != str(
                int(record["source_row"]) - 2
            ):
                raise BusinessSchemaUpdateError(f"TM {schema_id} dynamic identity/position drifted")
        dynamic_additions = (
            *(
                (schema_id, name)
                for schema_id, name, _source_row, _order, _parent_id, _level in (
                    TM_PAGE52_61_SCHEMA_ITEMS
                )
            ),
            *(
                (schema_id, name)
                for schema_id, name, _parent_id, _level in TM_COVERAGE_SCHEMA_ITEMS
            ),
            *(
                (schema_id, name)
                for schema_id, name, _parent_id, _level in TM_UNIVERSAL_SCHEMA_ITEMS
            ),
        )
        for schema_id, name in dynamic_additions:
            record = by_id[str(schema_id)]
            if record["report_norm_name"] != name or record["ordinal"] != str(
                int(record["source_row"]) - 2
            ):
                raise BusinessSchemaUpdateError(f"TM {schema_id} dynamic identity/position drifted")
        ids = [record["report_norm_id"] for record in after]
        expected_anchors = {
            TM_TOTAL_INTERBANK_PROVISION_ID: (
                TM_TOTAL_INTERBANK_PROVISION_PREDECESSOR_ID,
                TM_TOTAL_INTERBANK_PROVISION_SUCCESSOR_ID,
            ),
            TM_HEALTH_SOCIAL_ID: (
                TM_HEALTH_SOCIAL_PREDECESSOR_ID,
                TM_HEALTH_SOCIAL_SUCCESSOR_ID,
            ),
            TM_ARTS_RECREATION_ID: (
                TM_ARTS_RECREATION_PREDECESSOR_ID,
                TM_ARTS_RECREATION_SUCCESSOR_ID,
            ),
            TM_OTHER_SERVICES_ID: (
                TM_OTHER_SERVICES_PREDECESSOR_ID,
                TM_OTHER_SERVICES_SUCCESSOR_ID,
            ),
            TM_HOUSEHOLD_EMPLOYMENT_ID: (
                TM_HOUSEHOLD_EMPLOYMENT_PREDECESSOR_ID,
                TM_HOUSEHOLD_EMPLOYMENT_SUCCESSOR_ID,
            ),
            TM_PURCHASED_PRINCIPAL_ID: (
                TM_PURCHASED_PRINCIPAL_PREDECESSOR_ID,
                TM_PURCHASED_PRINCIPAL_SUCCESSOR_ID,
            ),
            TM_PURCHASED_INTEREST_ID: (
                TM_PURCHASED_INTEREST_PREDECESSOR_ID,
                TM_PURCHASED_INTEREST_SUCCESSOR_ID,
            ),
            TM_GOVERNMENT_GUARANTEED_DEBT_ID: (
                TM_GOVERNMENT_GUARANTEED_DEBT_PREDECESSOR_ID,
                TM_GOVERNMENT_GUARANTEED_DEBT_SUCCESSOR_ID,
            ),
            TM_FX_BUY_ID: (
                TM_FX_BUY_PREDECESSOR_ID,
                TM_FX_BUY_SUCCESSOR_ID,
            ),
            TM_FX_SELL_ID: (
                TM_FX_SELL_PREDECESSOR_ID,
                TM_FX_SELL_SUCCESSOR_ID,
            ),
            TM_SWAP_BUY_ID: (
                TM_SWAP_BUY_PREDECESSOR_ID,
                TM_SWAP_BUY_SUCCESSOR_ID,
            ),
            TM_SWAP_SELL_ID: (
                TM_SWAP_SELL_PREDECESSOR_ID,
                TM_SWAP_SELL_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_TYPE_ID: (
                TM_MARGIN_LOAN_TYPE_PREDECESSOR_ID,
                TM_MARGIN_LOAN_TYPE_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_QUALITY_ID: (
                TM_MARGIN_LOAN_QUALITY_PREDECESSOR_ID,
                TM_MARGIN_LOAN_QUALITY_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_MATURITY_ID: (
                TM_MARGIN_LOAN_MATURITY_PREDECESSOR_ID,
                TM_MARGIN_LOAN_MATURITY_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_BUSINESS_ID: (
                TM_MARGIN_LOAN_BUSINESS_PREDECESSOR_ID,
                TM_MARGIN_LOAN_BUSINESS_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_INDUSTRY_ID: (
                TM_MARGIN_LOAN_INDUSTRY_PREDECESSOR_ID,
                TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID,
            ),
            **{
                schema_id: (
                    (
                        TM_PAGE50_TAX_PREDECESSOR_ID
                        if offset == 0
                        else TM_PAGE50_TAX_SCHEMA_IDS[offset - 1]
                    ),
                    (
                        TM_PAGE50_TAX_SUCCESSOR_ID
                        if offset == len(TM_PAGE50_TAX_SCHEMA_IDS) - 1
                        else TM_PAGE50_TAX_SCHEMA_IDS[offset + 1]
                    ),
                )
                for offset, schema_id in enumerate(TM_PAGE50_TAX_SCHEMA_IDS)
            },
            **TM_PAGE52_61_ANCHORS,
            **TM_COVERAGE_ANCHORS,
            **TM_UNIVERSAL_ANCHORS,
        }
        expected_anchors[TM_MARGIN_LOAN_INDUSTRY_ID] = (
            6058,
            TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID,
        )
        for schema_id, anchors in expected_anchors.items():
            index = ids.index(str(schema_id))
            if (ids[index - 1], ids[index + 1]) != tuple(str(item) for item in anchors):
                raise BusinessSchemaUpdateError(f"TM {schema_id} anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"] not in {str(schema_id) for schema_id in NEW_SCHEMA_IDS}
        ]
        for record in new_pairs:
            if record["report_norm_id"] == "770":
                record["report_norm_name"] = TM_770_OLD_NAME
            elif record["report_norm_id"] == str(TM_EDUCATION_ID):
                record["report_norm_name"] = TM_EDUCATION_OLD_NAME
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("TM candidate changed an unauthorized identity/order")
    else:
        raise BusinessSchemaUpdateError(f"unsupported candidate statement {statement}")


def _schema_ids(paths: dict[str, Path]) -> dict[int, str]:
    seen: dict[int, str] = {}
    for statement, path in paths.items():
        for row in read_rows(path):
            raw = row.get("B", "").strip()
            if not raw or raw == "ReportNormId":
                continue
            try:
                schema_id = int(raw)
            except ValueError as exc:
                raise BusinessSchemaUpdateError(
                    f"non-integer schema ID in collision scan: {statement} {raw!r}"
                ) from exc
            if schema_id in seen:
                raise BusinessSchemaUpdateError(
                    f"global schema ID collision: {schema_id} in {seen[schema_id]} and {statement}"
                )
            seen[schema_id] = statement
    return seen


def _assert_global_identity(
    project_root: Path,
    *,
    cdkt_path: Path | None = None,
    kqkd_path: Path | None = None,
    lctt_path: Path | None = None,
    tm_path: Path | None = None,
    overrides: dict[str, Path] | None = None,
    expected_count: int,
) -> dict[int, str]:
    paths = {
        "CDKT": cdkt_path or project_root / CDKT_WORKBOOK,
        "KQKD": kqkd_path or project_root / KQKD_WORKBOOK,
        "LCTT": lctt_path or project_root / LCTT_WORKBOOK,
        "TM": tm_path or project_root / TM_WORKBOOK,
    }
    paths.update(overrides or {})
    seen = _schema_ids(paths)
    if len(seen) != expected_count:
        raise BusinessSchemaUpdateError(
            f"global schema count drifted: expected={expected_count}, actual={len(seen)}"
        )
    if NEW_SCHEMA_IDS & REVIEWED_EXTERNAL_IDS:
        raise BusinessSchemaUpdateError("new schema IDs collide with reviewed external IDs")
    return seen


def _expected_formulas() -> list[dict[str, object]]:
    return [dict(record) for record in BUSINESS_FORMULAS]


def _allowed_existing_name_corrections(statement: str) -> list[dict[str, object]]:
    return {
        "CDKT": [
            {
                "schema_id": 4319,
                "before": CDKT_4319_OLD_NAME,
                "after": CDKT_4319_CORRECTED_NAME,
            },
            {
                "schema_id": 4350,
                "before": CDKT_4350_OLD_NAME,
                "after": CDKT_4350_CORRECTED_NAME,
            },
            {
                "schema_id": 4360,
                "before": CDKT_4360_OLD_NAME,
                "after": CDKT_4360_CORRECTED_NAME,
            },
        ],
        "KQKD": [
            {
                "schema_id": 4382,
                "before": KQKD_4382_OLD_NAME,
                "after": KQKD_4382_CORRECTED_NAME,
            }
        ],
        "LCTT": [
            {
                "schema_id": 4109,
                "before": LCTT_4109_OLD_NAME,
                "after": LCTT_4109_CORRECTED_NAME,
            },
            {
                "schema_id": 4136,
                "before": LCTT_4136_OLD_NAME,
                "after": LCTT_4136_CORRECTED_NAME,
            },
        ],
        "TM": [
            {
                "schema_id": 770,
                "before": TM_770_OLD_NAME,
                "after": TM_770_CORRECTED_NAME,
            },
            {
                "schema_id": TM_EDUCATION_ID,
                "before": TM_EDUCATION_OLD_NAME,
                "after": TM_EDUCATION_NAME,
            },
        ],
    }[statement]


def _expected_schema_strategy(
    *,
    after_workbook_sha256: dict[str, str],
) -> dict[str, object]:
    return {
        "schema_name": "UNIVERSAL_BANK_BCTC_SCHEMA",
        "evolution_policy": "SOURCE_EVIDENCE_DRIVEN_APPEND_ONLY",
        "base_schema": {
            "name": "BASE_SCHEMA",
            "item_count": BASE_SCHEMA_ITEM_COUNT,
            "counts": {"CDKT": 77, "KQKD": 24, "LCTT": 107, "TM": 1385},
            "workbook_sha256": {
                "CDKT": CDKT_BEFORE_SHA256,
                "KQKD": KQKD_BEFORE_SHA256,
                "LCTT": LCTT_BEFORE_SHA256,
                "TM": TM_BEFORE_SHA256,
            },
            "ordered_canonical_projection_sha256": (
                "e63b77ebf99907843bea419cef32bc64cd709129813f89309f3b42fc818a1b10"
            ),
            "ordered_report_norm_ids_sha256": (
                "5cc0e9ea70b23af236ce43b920838299dbc91e9c0ef19d31165f4ce49eea4f9f"
            ),
        },
        "previous_universal_schema": {
            "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6056",
            "item_count": PRIOR_UNIVERSAL_SCHEMA_ITEM_COUNT,
            "counts": {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1701},
            "high_watermark": PRIOR_UNIVERSAL_HIGH_WATERMARK,
            "workbook_sha256": PRIOR_UNIVERSAL_WORKBOOK_SHA256,
            "identity_order_sha256": PRIOR_UNIVERSAL_IDENTITY_ORDER_SHA256,
            "audit_path": PRIOR_BUSINESS_UPDATE_AUDIT,
            "audit_sha256": PRIOR_BUSINESS_UPDATE_AUDIT_SHA256,
        },
        "universal_schema": {
            "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6060",
            "item_count": UNIVERSAL_SCHEMA_ITEM_COUNT,
            "counts": {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1705},
            "high_watermark": UNIVERSAL_HIGH_WATERMARK,
            "workbook_sha256": after_workbook_sha256,
        },
        "migration_delta": {
            "new_report_norm_ids": sorted(CURRENT_MIGRATION_SCHEMA_IDS),
            "item_count": len(CURRENT_MIGRATION_SCHEMA_IDS),
            "existing_report_norm_ids_renumbered": False,
            "report_norm_id_defines_display_order": False,
        },
    }


def _vpb_evidence(
    *,
    page: int,
    source_row_ref: str,
    visible_label: str,
    observed_values: Sequence[str],
) -> dict[str, object]:
    return {
        "bank": "VPB",
        "period": "Q1/2026",
        "scope": "CONSOLIDATED",
        "source_document_path": VPB_PDF_PATH,
        "source_document_sha256": VPB_PDF_SHA256,
        "native_rows_path": VPB_NATIVE_ROWS_PATH,
        "native_rows_sha256": VPB_NATIVE_ROWS_SHA256,
        "pdf_pages": [page],
        "source_row_refs": [source_row_ref],
        "visible_label": visible_label,
        "observed_values": list(observed_values),
        "unit": "VND_MILLION",
        "decision": "TRUE_SCHEMA_GAP_ACCEPTED",
        "reason_existing_items_insufficient": (
            "No existing canonical item preserves this visible accounting concept and "
            "its source hierarchy without force-mapping or loss."
        ),
    }


def _expected_structural_alias_changes() -> list[dict[str, object]]:
    changes: list[dict[str, object]] = [
        {
            "statement_type": statement,
            "schema_id": schema_id,
            "alias": alias,
            "disposition": "ADDED_BACKWARD_COMPATIBILITY_ALIAS",
            "added_to_structural_aliases": True,
            "provenance": "CANONICAL_DISPLAY_NAME_CORRECTION",
        }
        for statement, schema_id, alias in DISPLAY_NAME_COMPATIBILITY_ALIASES
    ]
    for change in changes:
        if (
            change["statement_type"],
            change["schema_id"],
            change["alias"],
        ) == ("LCTT", 4136, LCTT_4136_OLD_NAME):
            change["collision_handling"] = "OPPOSITE_CASH_FLOW_BRANCH_TYPED_ALIAS"
            change["collision_schema_ids"] = [4179]
    for statement, schema_id, page, row, alias in VPB_STRUCTURAL_ALIAS_CANDIDATES:
        key = (statement, schema_id)
        if key in VPB_ALIAS_CANONICAL_AFTER_CORRECTION:
            disposition = "CANONICAL_AFTER_CORRECTION_NOT_DUPLICATED_AS_ALIAS"
            added = False
            collision_schema_id = None
        elif key in VPB_ALIAS_CANONICAL_COLLISIONS:
            disposition = "REJECTED_CANONICAL_LABEL_COLLISION"
            added = False
            collision_schema_id = VPB_ALIAS_CANONICAL_COLLISIONS[key]
        else:
            disposition = "ADDED_ID_SCOPED_STRUCTURAL_ALIAS"
            added = True
            collision_schema_id = None
        record: dict[str, object] = {
            "statement_type": statement,
            "schema_id": schema_id,
            "alias": alias,
            "disposition": disposition,
            "added_to_structural_aliases": added,
            "evidence": {
                "bank": "VPB",
                "period": "Q1/2026",
                "scope": "CONSOLIDATED",
                "source_document_path": VPB_PDF_PATH,
                "source_document_sha256": VPB_PDF_SHA256,
                "native_rows_path": VPB_NATIVE_ROWS_PATH,
                "native_rows_sha256": VPB_NATIVE_ROWS_SHA256,
                "pdf_page": page,
                "source_row_ref": f"page-{page:04d}:row-{row:04d}",
            },
        }
        if collision_schema_id is not None:
            record["collision_schema_id"] = collision_schema_id
        changes.append(record)
    changes.extend(
        {
            "statement_type": statement,
            "schema_id": schema_id,
            "alias": alias,
            "disposition": "ADDED_MINOR_WORDING_SOURCE_ALIAS",
            "added_to_structural_aliases": True,
            "evidence": {
                "bank": "MBB",
                "period": "Q1/2026",
                "scope": "CONSOLIDATED",
                "source_document_path": FIRST_OBSERVED_PDF_PATH,
                "source_document_sha256": FIRST_OBSERVED_PDF_SHA256,
                "source_ocr_path": MBB_OFF_BALANCE_OCR_PATH,
                "source_ocr_sha256": MBB_OFF_BALANCE_OCR_SHA256,
                "source_render_path": MBB_OFF_BALANCE_RENDER_PATH,
                "source_render_sha256": MBB_OFF_BALANCE_RENDER_SHA256,
                "pdf_page": page,
                "source_row_ref": f"page-{page:04d}:line-{row:04d}",
                "accounting_basis": "MINOR_PLURAL_WORDING_SAME_STRUCTURAL_HEADING",
            },
        }
        for statement, schema_id, page, row, alias in MBB_OFF_BALANCE_WORDING_ALIASES
    )
    changes.extend(
        {
            "statement_type": statement,
            "schema_id": schema_id,
            "alias": alias,
            "disposition": "ADDED_NEW_ITEM_SOURCE_ALIAS",
            "added_to_structural_aliases": True,
            "evidence": {
                "bank": "VPB",
                "period": "Q1/2026",
                "scope": "CONSOLIDATED",
                "source_document_path": VPB_PDF_PATH,
                "source_document_sha256": VPB_PDF_SHA256,
                "native_rows_path": VPB_NATIVE_ROWS_PATH,
                "native_rows_sha256": VPB_NATIVE_ROWS_SHA256,
                "pdf_page": page,
                "source_row_ref": f"page-{page:04d}:row-{row:04d}",
            },
        }
        for statement, schema_id, page, row, alias in NEW_ITEM_SOURCE_ALIASES
    )
    changes.extend(
        {
            "statement_type": statement,
            "schema_id": schema_id,
            "alias": alias,
            "disposition": "ADDED_ACCOUNTING_EQUIVALENT_SOURCE_ALIAS",
            "added_to_structural_aliases": True,
            "evidence": {
                "bank": "MBB",
                "period": "Q1/2026",
                "scope": "CONSOLIDATED",
                "source_document_path": FIRST_OBSERVED_PDF_PATH,
                "source_document_sha256": FIRST_OBSERVED_PDF_SHA256,
                "source_ocr_path": MBB_OFF_BALANCE_OCR_PATH,
                "source_ocr_sha256": MBB_OFF_BALANCE_OCR_SHA256,
                "source_render_path": MBB_OFF_BALANCE_RENDER_PATH,
                "source_render_sha256": MBB_OFF_BALANCE_RENDER_SHA256,
                "pdf_page": page,
                "source_row_ref": f"page-{page:04d}:line-{row:04d}",
                "accounting_basis": "BUY_SWAP_RECEIVE_LEG_AND_SELL_SWAP_PAY_LEG_EQUIVALENCE",
            },
        }
        for statement, schema_id, page, row, alias in MBB_OFF_BALANCE_SOURCE_ALIASES
    )
    return changes


def _expected_schema_changes() -> list[dict[str, object]]:
    changes = [
        {
            "change": "ADD",
            "statement_type": "CDKT",
            "schema_id": CDKT_TOTAL_EQUITY_ID,
            "canonical_name": CDKT_TOTAL_EQUITY_NAME,
            "source_row": CDKT_TOTAL_EQUITY_FINAL_SOURCE_ROW,
            "display_order_zero_based": CDKT_TOTAL_EQUITY_FINAL_DISPLAY_ORDER,
            "previous_schema_id": CDKT_TOTAL_EQUITY_PREDECESSOR_ID,
            "next_schema_id": CDKT_TOTAL_EQUITY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "KQKD",
            "schema_id": KQKD_TOTAL_OPERATING_INCOME_ID,
            "canonical_name": KQKD_TOTAL_OPERATING_INCOME_NAME,
            "source_row": KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW,
            "display_order_zero_based": KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER,
            "previous_schema_id": KQKD_TOTAL_OPERATING_INCOME_PREDECESSOR_ID,
            "next_schema_id": KQKD_TOTAL_OPERATING_INCOME_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "LCTT",
            "schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
            "canonical_name": LCTT_INVESTMENT_CONTRIBUTION_NET_NAME,
            "source_row": LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_SOURCE_ROW,
            "display_order_zero_based": LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_DISPLAY_ORDER,
            "previous_schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_PREDECESSOR_ID,
            "next_schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "LCTT",
            "schema_id": LCTT_INVESTMENT_PROPERTY_NET_ID,
            "canonical_name": LCTT_INVESTMENT_PROPERTY_NET_NAME,
            "source_row": LCTT_INVESTMENT_PROPERTY_NET_FINAL_SOURCE_ROW,
            "display_order_zero_based": LCTT_INVESTMENT_PROPERTY_NET_FINAL_DISPLAY_ORDER,
            "previous_schema_id": LCTT_INVESTMENT_PROPERTY_NET_PREDECESSOR_ID,
            "next_schema_id": LCTT_INVESTMENT_PROPERTY_NET_SUCCESSOR_ID,
            "parent_schema_id": 4111,
            "hierarchy_level": 2,
            "section": "DIRECT_CASH_FLOW_INVESTING_ACTIVITIES",
            "schema_status": "ACCEPTED_UNIVERSAL",
            "evidence": {
                "bank": "MBB",
                "period": "Q1/2026",
                "scope": "CONSOLIDATED",
                "source_document_sha256": FIRST_OBSERVED_PDF_SHA256,
                "pdf_pages": [7],
                "source_row_refs": ["page-0007:row-0031"],
                "visible_label": LCTT_INVESTMENT_PROPERTY_NET_NAME,
                "observed_values": ["DASH", "DASH"],
                "unit": "VND_MILLION",
                "decision": "TRUE_SCHEMA_GAP_ACCEPTED",
                "reason_existing_items_insufficient": (
                    "The PDF reports a net investment-property cash-flow row; existing "
                    "4144/4145/4146 are its distinct components."
                ),
            },
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_TOTAL_INTERBANK_PROVISION_ID,
            "canonical_name": TM_TOTAL_INTERBANK_PROVISION_NAME,
            "source_row": TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW,
            "display_order_zero_based": TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER,
            "previous_schema_id": TM_TOTAL_INTERBANK_PROVISION_PREDECESSOR_ID,
            "next_schema_id": TM_TOTAL_INTERBANK_PROVISION_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_HEALTH_SOCIAL_ID,
            "canonical_name": TM_HEALTH_SOCIAL_NAME,
            "source_row": TM_HEALTH_SOCIAL_SOURCE_ROW,
            "display_order_zero_based": TM_HEALTH_SOCIAL_DISPLAY_ORDER,
            "previous_schema_id": TM_HEALTH_SOCIAL_PREDECESSOR_ID,
            "next_schema_id": TM_HEALTH_SOCIAL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_ARTS_RECREATION_ID,
            "canonical_name": TM_ARTS_RECREATION_NAME,
            "source_row": TM_ARTS_RECREATION_SOURCE_ROW,
            "display_order_zero_based": TM_ARTS_RECREATION_DISPLAY_ORDER,
            "previous_schema_id": TM_ARTS_RECREATION_PREDECESSOR_ID,
            "next_schema_id": TM_ARTS_RECREATION_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_OTHER_SERVICES_ID,
            "canonical_name": TM_OTHER_SERVICES_NAME,
            "source_row": TM_OTHER_SERVICES_SOURCE_ROW,
            "display_order_zero_based": TM_OTHER_SERVICES_DISPLAY_ORDER,
            "previous_schema_id": TM_OTHER_SERVICES_PREDECESSOR_ID,
            "next_schema_id": TM_OTHER_SERVICES_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_HOUSEHOLD_EMPLOYMENT_ID,
            "canonical_name": TM_HOUSEHOLD_EMPLOYMENT_NAME,
            "source_row": TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW,
            "display_order_zero_based": TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER,
            "previous_schema_id": TM_HOUSEHOLD_EMPLOYMENT_PREDECESSOR_ID,
            "next_schema_id": 6059,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_PURCHASED_PRINCIPAL_ID,
            "canonical_name": TM_PURCHASED_PRINCIPAL_NAME,
            "source_row": TM_PURCHASED_PRINCIPAL_SOURCE_ROW,
            "display_order_zero_based": TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER,
            "previous_schema_id": TM_PURCHASED_PRINCIPAL_PREDECESSOR_ID,
            "next_schema_id": TM_PURCHASED_PRINCIPAL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_PURCHASED_INTEREST_ID,
            "canonical_name": TM_PURCHASED_INTEREST_NAME,
            "source_row": TM_PURCHASED_INTEREST_SOURCE_ROW,
            "display_order_zero_based": TM_PURCHASED_INTEREST_DISPLAY_ORDER,
            "previous_schema_id": TM_PURCHASED_INTEREST_PREDECESSOR_ID,
            "next_schema_id": TM_PURCHASED_INTEREST_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_GOVERNMENT_GUARANTEED_DEBT_ID,
            "canonical_name": TM_GOVERNMENT_GUARANTEED_DEBT_NAME,
            "source_row": TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW,
            "display_order_zero_based": TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER,
            "previous_schema_id": TM_GOVERNMENT_GUARANTEED_DEBT_PREDECESSOR_ID,
            "next_schema_id": TM_GOVERNMENT_GUARANTEED_DEBT_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_FX_BUY_ID,
            "canonical_name": TM_FX_BUY_NAME,
            "source_row": TM_FX_BUY_SOURCE_ROW,
            "display_order_zero_based": TM_FX_BUY_DISPLAY_ORDER,
            "previous_schema_id": TM_FX_BUY_PREDECESSOR_ID,
            "next_schema_id": TM_FX_BUY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_FX_SELL_ID,
            "canonical_name": TM_FX_SELL_NAME,
            "source_row": TM_FX_SELL_SOURCE_ROW,
            "display_order_zero_based": TM_FX_SELL_DISPLAY_ORDER,
            "previous_schema_id": TM_FX_SELL_PREDECESSOR_ID,
            "next_schema_id": TM_FX_SELL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_SWAP_BUY_ID,
            "canonical_name": TM_SWAP_BUY_NAME,
            "source_row": TM_SWAP_BUY_SOURCE_ROW,
            "display_order_zero_based": TM_SWAP_BUY_DISPLAY_ORDER,
            "previous_schema_id": TM_SWAP_BUY_PREDECESSOR_ID,
            "next_schema_id": TM_SWAP_BUY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_SWAP_SELL_ID,
            "canonical_name": TM_SWAP_SELL_NAME,
            "source_row": TM_SWAP_SELL_SOURCE_ROW,
            "display_order_zero_based": TM_SWAP_SELL_DISPLAY_ORDER,
            "previous_schema_id": TM_SWAP_SELL_PREDECESSOR_ID,
            "next_schema_id": TM_SWAP_SELL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_TYPE_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_TYPE_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_TYPE_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_TYPE_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_QUALITY_ID,
            "canonical_name": TM_MARGIN_LOAN_QUALITY_NAME,
            "source_row": TM_MARGIN_LOAN_QUALITY_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_QUALITY_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_QUALITY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_MATURITY_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_MATURITY_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_MATURITY_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_MATURITY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_BUSINESS_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_BUSINESS_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_BUSINESS_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_INDUSTRY_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER,
            "previous_schema_id": 6058,
            "next_schema_id": TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID,
        },
        *(
            {
                "change": "ADD",
                "statement_type": "TM",
                "schema_id": schema_id,
                "canonical_name": name,
                "source_row": TM_PAGE50_TAX_INSERT_SOURCE_ROW + offset,
                "display_order_zero_based": TM_PAGE50_TAX_INSERT_DISPLAY_ORDER + offset,
                "previous_schema_id": (
                    TM_PAGE50_TAX_PREDECESSOR_ID
                    if offset == 0
                    else TM_PAGE50_TAX_SCHEMA_IDS[offset - 1]
                ),
                "next_schema_id": (
                    TM_PAGE50_TAX_SUCCESSOR_ID
                    if offset == len(TM_PAGE50_TAX_SCHEMA_IDS) - 1
                    else TM_PAGE50_TAX_SCHEMA_IDS[offset + 1]
                ),
            }
            for offset, (schema_id, name) in enumerate(TM_PAGE50_TAX_SCHEMA_ITEMS)
        ),
        *(
            {
                "change": "ADD",
                "statement_type": "TM",
                "schema_id": schema_id,
                "canonical_name": name,
                "parent_schema_id": parent_id,
                "hierarchy_level": level,
                "previous_schema_id": TM_PAGE52_61_ANCHORS[schema_id][0],
                "next_schema_id": TM_PAGE52_61_ANCHORS[schema_id][1],
            }
            for schema_id, name, _source_row, _display_order, parent_id, level in (
                TM_PAGE52_61_SCHEMA_ITEMS
            )
        ),
        *(
            {
                "change": "ADD",
                "statement_type": "TM",
                "schema_id": schema_id,
                "canonical_name": name,
                "parent_schema_id": parent_id,
                "hierarchy_level": level,
                "previous_schema_id": TM_COVERAGE_ANCHORS[schema_id][0],
                "next_schema_id": TM_COVERAGE_ANCHORS[schema_id][1],
            }
            for schema_id, name, parent_id, level in TM_COVERAGE_SCHEMA_ITEMS
        ),
        *(
            {
                "change": "ADD",
                "statement_type": "TM",
                "schema_id": schema_id,
                "canonical_name": name,
                "parent_schema_id": parent_id,
                "hierarchy_level": level,
                "section": (
                    "BALANCE_SHEET_NOTES"
                    if schema_id <= 6020 or schema_id >= 6057
                    else "INCOME_STATEMENT_NOTES"
                ),
                "schema_status": "ACCEPTED_UNIVERSAL",
                "previous_schema_id": TM_UNIVERSAL_ANCHORS[schema_id][0],
                "next_schema_id": TM_UNIVERSAL_ANCHORS[schema_id][1],
                "evidence": {
                    "bank": "MBB",
                    "period": "Q1/2026",
                    "scope": "CONSOLIDATED",
                    "source_document_sha256": FIRST_OBSERVED_PDF_SHA256,
                    "unit": "VND_MILLION",
                    "decision": "TRUE_SCHEMA_GAP_ACCEPTED",
                    "reason_existing_items_insufficient": (
                        "No existing canonical item preserves this visible accounting "
                        "concept and its source hierarchy without force-mapping or loss."
                    ),
                    **TM_UNIVERSAL_EVIDENCE[schema_id],
                },
            }
            for schema_id, name, parent_id, level in TM_UNIVERSAL_SCHEMA_ITEMS
        ),
        *(
            {
                "change": "ADD",
                "statement_type": "CDKT",
                "schema_id": schema_id,
                "canonical_name": name,
                "source_row": CDKT_VPB_DISPLAY_ORDERS[schema_id] + 2,
                "display_order_zero_based": CDKT_VPB_DISPLAY_ORDERS[schema_id],
                "previous_schema_id": CDKT_VPB_DISPLAY_ANCHORS[schema_id][0],
                "next_schema_id": CDKT_VPB_DISPLAY_ANCHORS[schema_id][1],
                "parent_schema_id": parent_id,
                "hierarchy_level": level,
                "section": section,
                "applicable_scope": (
                    ["CONSOLIDATED"] if schema_id >= 6038 else ["SEPARATE", "CONSOLIDATED"]
                ),
                "schema_status": "ACCEPTED_UNIVERSAL",
                "evidence": _vpb_evidence(
                    page=page,
                    source_row_ref=source_row_ref,
                    visible_label=name,
                    observed_values=values,
                ),
            }
            for (
                schema_id,
                name,
                parent_id,
                level,
                section,
                page,
                source_row_ref,
                values,
            ) in CDKT_VPB_SCHEMA_ITEMS
        ),
        {
            "change": "ADD",
            "statement_type": "CDKT",
            "schema_id": CDKT_OFF_BALANCE_TOTAL_ID,
            "canonical_name": CDKT_OFF_BALANCE_TOTAL_NAME,
            "source_row": CDKT_CUMULATIVE_DISPLAY_ORDERS[CDKT_OFF_BALANCE_TOTAL_ID] + 2,
            "display_order_zero_based": CDKT_CUMULATIVE_DISPLAY_ORDERS[CDKT_OFF_BALANCE_TOTAL_ID],
            "previous_schema_id": CDKT_CUMULATIVE_DISPLAY_ANCHORS[CDKT_OFF_BALANCE_TOTAL_ID][0],
            "next_schema_id": CDKT_CUMULATIVE_DISPLAY_ANCHORS[CDKT_OFF_BALANCE_TOTAL_ID][1],
            "parent_schema_id": 6038,
            "hierarchy_level": 1,
            "section": "OFF_BALANCE_SHEET",
            "applicable_scope": ["CONSOLIDATED"],
            "schema_status": "ACCEPTED_UNIVERSAL",
            "evidence": {
                **_vpb_evidence(
                    page=7,
                    source_row_ref="page-0007:row-0016",
                    visible_label="[UNLABELED_TERMINAL_TOTAL]",
                    observed_values=("1.304.756.779", "1.367.060.929"),
                ),
                "decision": "USER_NAMED_EXACT_AGGREGATE_ACCEPTED",
                "user_decision": "Q075",
                "exact_component_schema_ids": list(CDKT_OFF_BALANCE_TOTAL_COMPONENTS),
                "mapping_guard": (
                    "UNIQUE_TERMINAL_UNLABELED_COMPLETE_DIRECT_CHILD_TOPOLOGY_"
                    "WITH_EXACT_PER_AXIS_SUM"
                ),
            },
        },
        {
            "change": "ADD",
            "statement_type": "CDKT",
            "schema_id": CDKT_SWAP_COMMITMENT_TOTAL_ID,
            "canonical_name": CDKT_SWAP_COMMITMENT_TOTAL_NAME,
            "source_row": CDKT_CUMULATIVE_DISPLAY_ORDERS[CDKT_SWAP_COMMITMENT_TOTAL_ID] + 2,
            "display_order_zero_based": CDKT_CUMULATIVE_DISPLAY_ORDERS[
                CDKT_SWAP_COMMITMENT_TOTAL_ID
            ],
            "previous_schema_id": CDKT_CUMULATIVE_DISPLAY_ANCHORS[CDKT_SWAP_COMMITMENT_TOTAL_ID][0],
            "next_schema_id": CDKT_CUMULATIVE_DISPLAY_ANCHORS[CDKT_SWAP_COMMITMENT_TOTAL_ID][1],
            "parent_schema_id": 6041,
            "hierarchy_level": 4,
            "section": "OFF_BALANCE_SHEET",
            "applicable_scope": ["CONSOLIDATED"],
            "schema_status": "ACCEPTED_UNIVERSAL",
            "evidence": {
                "bank": "CTG",
                "period": "Q2/2026",
                "scope": "CONSOLIDATED",
                "source_document_path": CTG_PDF_PATH,
                "source_document_sha256": CTG_PDF_SHA256,
                "pdf_page": 5,
                "zero_based_pdf_page": 4,
                "printed_page": 3,
                "source_row_ref": "ctg-p5-5705",
                "visible_label": CDKT_SWAP_COMMITMENT_TOTAL_NAME,
                "observed_values": ["937.179.489", "849.738.846"],
                "unit": "VND_MILLION",
                "reviewed_evidence_path": CTG_REVIEW_PATH,
                "reviewed_evidence_sha256": CTG_REVIEW_SHA256,
                "reviewed_evidence_bridge": {
                    "review_id": "HR-2026-08-06-CTG-ACB-MBB",
                    "document_key": "ctg-q2-2026-consolidated",
                    "visible_row_id": "ctg-p5-5705",
                    "reviewed_item_id": 5705,
                    "period_map_id": "ctg-off-balance-2026q2",
                    "period_axes": {
                        "CURRENT": "2026-06-30",
                        "COMPARATIVE": "2025-12-31",
                    },
                    "sealed_historical_template_membership": ("OUTSIDE_CURRENT_TARGET_TEMPLATE"),
                    "sealed_historical_mapping_action": "DO_NOT_MAP_TO_TARGET_CDKT",
                    "sealed_history_mutated": False,
                    "current_schema_target_authority": "Q076",
                    "current_schema_target_id": CDKT_SWAP_COMMITMENT_TOTAL_ID,
                },
                "decision": "USER_CONFIRMED_COMBINED_SWAP_SUBTOTAL",
                "user_decision": "Q076",
                "exact_parent_equation": {
                    "target_schema_id": 6041,
                    "component_schema_ids": list(CDKT_FX_COMMITMENT_COMPONENTS),
                    "current": "953123645=7973593+7970563+937179489",
                    "comparative": "860422276=5341651+5341779+849738846",
                },
            },
        },
        {
            "change": "ADD",
            "statement_type": "LCTT",
            "schema_id": LCTT_VPB_COMBINED_LOAN_ID,
            "canonical_name": LCTT_VPB_COMBINED_LOAN_NAME,
            "source_row": LCTT_VPB_COMBINED_LOAN_SOURCE_ROW,
            "display_order_zero_based": LCTT_VPB_COMBINED_LOAN_DISPLAY_ORDER,
            "previous_schema_id": LCTT_VPB_COMBINED_LOAN_PREDECESSOR_ID,
            "next_schema_id": LCTT_VPB_COMBINED_LOAN_SUCCESSOR_ID,
            "parent_schema_id": LCTT_VPB_COMBINED_LOAN_PARENT_ID,
            "hierarchy_level": LCTT_VPB_COMBINED_LOAN_HIERARCHY_LEVEL,
            "section": "DIRECT_CASH_FLOW_OPERATING_ASSET_CHANGES",
            "schema_status": "ACCEPTED_UNIVERSAL",
            "evidence": _vpb_evidence(
                page=9,
                source_row_ref="page-0009:row-0015",
                visible_label="Tăng các khoản cho vay khách hàng và mua nợ",
                observed_values=("(96.572.655)", "(37.671.928)"),
            ),
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "CDKT",
            "schema_id": 4350,
            "before": CDKT_4350_OLD_NAME,
            "after": CDKT_4350_CORRECTED_NAME,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "CDKT",
            "schema_id": 4319,
            "before": CDKT_4319_OLD_NAME,
            "after": CDKT_4319_CORRECTED_NAME,
            "user_decision": "Q077",
            "backward_compatible_alias_preserved": True,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "CDKT",
            "schema_id": 4360,
            "before": CDKT_4360_OLD_NAME,
            "after": CDKT_4360_CORRECTED_NAME,
            "user_decision": "Q074",
            "backward_compatible_alias_preserved": True,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "LCTT",
            "schema_id": 4136,
            "before": LCTT_4136_OLD_NAME,
            "after": LCTT_4136_CORRECTED_NAME,
            "user_decision": "Q078",
            "backward_compatible_alias_preserved": True,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "TM",
            "schema_id": 770,
            "before": TM_770_OLD_NAME,
            "after": TM_770_CORRECTED_NAME,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "TM",
            "schema_id": TM_EDUCATION_ID,
            "before": TM_EDUCATION_OLD_NAME,
            "after": TM_EDUCATION_NAME,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "KQKD",
            "schema_id": 4382,
            "before": KQKD_4382_OLD_NAME,
            "after": KQKD_4382_CORRECTED_NAME,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "LCTT",
            "schema_id": 4109,
            "before": LCTT_4109_OLD_NAME,
            "after": LCTT_4109_CORRECTED_NAME,
        },
    ]
    for record in changes:
        if record.get("statement_type") == "TM" and record.get("change") == "ADD":
            record.pop("source_row", None)
            record.pop("display_order_zero_based", None)
    return changes


def _expected_hierarchy_changes() -> list[dict[str, object]]:
    groups: tuple[tuple[str, tuple[int, ...], int, int, int, int], ...] = (
        ("LCTT", LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS, 4111, 6034, 2, 3),
        ("TM", tuple(range(871, 876)), 869, 5991, 3, 4),
        ("TM", tuple(range(876, 882)), 869, 5992, 3, 4),
        ("TM", tuple(range(885, 888)), 883, 5994, 3, 4),
        ("TM", tuple(range(888, 895)), 883, 5995, 3, 4),
        ("TM", tuple(range(916, 921)), 914, 5997, 3, 4),
        ("TM", tuple(range(931, 934)), 929, 5999, 3, 4),
        ("TM", tuple(range(934, 941)), 929, 6000, 3, 4),
        ("TM", tuple(range(945, 952)), 943, 6002, 3, 4),
        ("TM", tuple(range(952, 955)), 943, 6003, 3, 4),
        ("TM", tuple(range(958, 961)), 956, 6005, 3, 4),
        ("TM", tuple(range(1130, 1137)), 1128, 6019, 2, 3),
        ("TM", tuple(range(1137, 1141)), 1128, 6020, 2, 3),
    )
    changes = [
        {
            "change": "REPARENT_WITH_SOURCE_EVIDENCE",
            "statement_type": statement,
            "schema_id": schema_id,
            "before_parent_schema_id": before_parent,
            "after_parent_schema_id": after_parent,
            "before_hierarchy_level": before_level,
            "after_hierarchy_level": after_level,
            "reason": "VISIBLE_PARENT_OR_SUBTOTAL_PRESERVES_ACCOUNTING_HIERARCHY",
        }
        for statement, schema_ids, before_parent, after_parent, before_level, after_level in groups
        for schema_id in schema_ids
    ]
    changes.extend(
        {
            "change": "ADD_HIERARCHY_NODE_WITH_SOURCE_EVIDENCE",
            "statement_type": "CDKT",
            "schema_id": schema_id,
            "parent_schema_id": parent_id,
            "hierarchy_level": level,
            "section": section,
            **({"relationship_semantics": "NON_ADDITIVE_SUBSET"} if schema_id == 6049 else {}),
        }
        for schema_id, _name, parent_id, level, section, *_rest in CDKT_VPB_SCHEMA_ITEMS
    )
    changes.extend(
        (
            {
                "change": "ADD_HIERARCHY_NODE_WITH_USER_AUTHORITY",
                "statement_type": "CDKT",
                "schema_id": CDKT_OFF_BALANCE_TOTAL_ID,
                "parent_schema_id": 6038,
                "hierarchy_level": 1,
                "section": "OFF_BALANCE_SHEET",
                "component_schema_ids": list(CDKT_OFF_BALANCE_TOTAL_COMPONENTS),
                "user_decision": "Q075",
            },
            {
                "change": "ADD_HIERARCHY_NODE_WITH_USER_AUTHORITY",
                "statement_type": "CDKT",
                "schema_id": CDKT_SWAP_COMMITMENT_TOTAL_ID,
                "parent_schema_id": 6041,
                "hierarchy_level": 4,
                "section": "OFF_BALANCE_SHEET",
                "component_schema_ids": list(CDKT_SWAP_COMMITMENT_TOTAL_COMPONENTS),
                "user_decision": "Q076",
            },
        )
    )
    changes.extend(
        {
            "change": "REPARENT_WITH_USER_AUTHORITY",
            "statement_type": "CDKT",
            "schema_id": schema_id,
            "before_parent_schema_id": before_parent,
            "after_parent_schema_id": after_parent,
            "before_hierarchy_level": before_level,
            "after_hierarchy_level": after_level,
            "user_decision": decision,
        }
        for schema_id, before_parent, after_parent, before_level, after_level, decision in (
            (6039, 6038, CDKT_OFF_BALANCE_TOTAL_ID, 1, 2, "Q075"),
            (6050, 6038, CDKT_OFF_BALANCE_TOTAL_ID, 1, 2, "Q075"),
            (6044, 6041, CDKT_SWAP_COMMITMENT_TOTAL_ID, 3, 5, "Q076"),
            (6045, 6041, CDKT_SWAP_COMMITMENT_TOTAL_ID, 3, 5, "Q076"),
        )
    )
    changes.extend(
        {
            "change": "RELEVEL_AFTER_USER_AUTHORIZED_ANCESTOR_INSERTION",
            "statement_type": "CDKT",
            "schema_id": schema_id,
            "parent_schema_id": parent_id,
            "before_hierarchy_level": before_level,
            "after_hierarchy_level": after_level,
            "user_decision": decision,
        }
        for schema_id, parent_id, before_level, after_level, decision in (
            (6040, 6039, 2, 3, "Q075"),
            (6041, 6039, 2, 3, "Q075"),
            (6042, 6041, 3, 4, "Q075"),
            (6043, 6041, 3, 4, "Q075"),
            (6046, 6039, 2, 3, "Q075"),
            (6047, 6039, 2, 3, "Q075"),
            (6048, 6039, 2, 3, "Q075"),
            (6049, 6048, 3, 4, "Q075"),
            (6051, 6050, 2, 3, "Q075"),
            (6052, 6050, 2, 3, "Q075"),
            (6053, 6050, 2, 3, "Q075"),
        )
    )
    changes.append(
        {
            "change": "ADD_HIERARCHY_NODE_WITH_SOURCE_EVIDENCE",
            "statement_type": "LCTT",
            "schema_id": LCTT_VPB_COMBINED_LOAN_ID,
            "parent_schema_id": LCTT_VPB_COMBINED_LOAN_PARENT_ID,
            "hierarchy_level": LCTT_VPB_COMBINED_LOAN_HIERARCHY_LEVEL,
            "section": "DIRECT_CASH_FLOW_OPERATING_ASSET_CHANGES",
            "relationship_semantics": "SIBLING_ALTERNATIVE_NO_FORMULA",
        }
    )
    changes.extend(
        {
            "change": "REPARENT_WITH_SOURCE_EVIDENCE",
            "statement_type": "LCTT",
            "schema_id": schema_id,
            "before_parent_schema_id": before_parent,
            "after_parent_schema_id": after_parent,
            "before_hierarchy_level": level,
            "after_hierarchy_level": level,
            "reason": "VISIBLE_DIRECT_CASH_FLOW_ASSET_LIABILITY_GROUPING",
        }
        for schema_id, before_parent, after_parent, level in (
            (4107, None, 4110, 1),
            (4108, None, 4110, 1),
            *((schema_id, 4110, 4107, 2) for schema_id in range(4129, 4135)),
            *((schema_id, 4110, 4108, 2) for schema_id in range(4135, 4142)),
        )
    )
    return changes


def verify_business_schema_update(project_root: Path, audit_path: Path) -> dict[str, object]:
    project_root = project_root.resolve()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        audit.get("format_version") != 1
        or audit.get("migration_id") != "BUSINESS-SCHEMA-5712-5713-5714-5718-6060"
        or audit.get("status") != "APPLIED_AND_VERIFIED"
    ):
        raise BusinessSchemaUpdateError("invalid business-schema update audit identity")
    if audit.get("business_formulas") != _expected_formulas():
        raise BusinessSchemaUpdateError("business formula audit drifted")
    if audit.get("schema_changes") != _expected_schema_changes():
        raise BusinessSchemaUpdateError("business schema-change audit drifted")
    if audit.get("hierarchy_changes") != _expected_hierarchy_changes():
        raise BusinessSchemaUpdateError("business hierarchy-change audit drifted")
    if audit.get("structural_alias_changes") != _expected_structural_alias_changes():
        raise BusinessSchemaUpdateError("business structural-alias audit drifted")
    if audit.get("authority") != {
        "approved_on": "2026-08-09",
        "policy": "USER_AUTHORIZED_EVOLVING_UNIVERSAL_BANK_BCTC_SCHEMA",
        "decision_ids": ["Q074", "Q075", "Q076", "Q077", "Q078", "Q079"],
    }:
        raise BusinessSchemaUpdateError("business schema authority drifted")
    collision = audit.get("collision_safety")
    if not isinstance(collision, dict) or collision.get("reviewed_external_ids") != sorted(
        REVIEWED_EXTERNAL_IDS
    ):
        raise BusinessSchemaUpdateError("reviewed-external collision audit drifted")
    if collision.get("new_ids_disjoint_from_reviewed_external_ids") is not True:
        raise BusinessSchemaUpdateError("business update lacks external-ID disjointness proof")
    if collision != {
        "baseline_global_schema_count": BASE_SCHEMA_ITEM_COUNT,
        "result_global_schema_count": UNIVERSAL_SCHEMA_ITEM_COUNT,
        "new_ids": sorted(NEW_SCHEMA_IDS),
        "reviewed_external_ids": sorted(REVIEWED_EXTERNAL_IDS),
        "new_ids_disjoint_from_reviewed_external_ids": True,
        "result_ids_globally_unique": True,
    }:
        raise BusinessSchemaUpdateError("business update collision proof drifted")

    raw_workbooks = audit.get("workbooks")
    if not isinstance(raw_workbooks, dict):
        raise BusinessSchemaUpdateError("business update workbook audit is absent")
    after_workbook_sha256 = {
        statement: str(record.get("after_sha256"))
        for statement, record in raw_workbooks.items()
        if isinstance(record, dict)
    }
    if audit.get("schema_strategy") != _expected_schema_strategy(
        after_workbook_sha256=after_workbook_sha256
    ):
        raise BusinessSchemaUpdateError("universal schema strategy audit drifted")
    if sha256_file(project_root / PRIOR_BUSINESS_UPDATE_AUDIT) != (
        PRIOR_BUSINESS_UPDATE_AUDIT_SHA256
    ):
        raise BusinessSchemaUpdateError("prior universal-schema audit changed")

    expected_workbooks = {
        "CDKT": (
            CDKT_BASELINE_WORKBOOK,
            CDKT_WORKBOOK,
            CDKT_BEFORE_SHA256,
            CDKT_AFTER_ROW_COUNT,
        ),
        "KQKD": (
            KQKD_BASELINE_WORKBOOK,
            KQKD_WORKBOOK,
            KQKD_BEFORE_SHA256,
            KQKD_AFTER_ROW_COUNT,
        ),
        "LCTT": (
            LCTT_BASELINE_WORKBOOK,
            LCTT_WORKBOOK,
            LCTT_BEFORE_SHA256,
            LCTT_AFTER_ROW_COUNT,
        ),
        "TM": (
            TM_BASELINE_WORKBOOK,
            TM_WORKBOOK,
            TM_BEFORE_SHA256,
            TM_AFTER_ROW_COUNT,
        ),
    }
    if not isinstance(raw_workbooks, dict) or set(raw_workbooks) != set(expected_workbooks):
        raise BusinessSchemaUpdateError("business update workbook audit set drifted")
    for statement, (
        baseline_relative,
        relative,
        before_hash,
        row_count,
    ) in expected_workbooks.items():
        record = raw_workbooks[statement]
        if not isinstance(record, dict):
            raise BusinessSchemaUpdateError(f"invalid {statement} workbook audit")
        if (
            record.get("baseline_path") != baseline_relative
            or record.get("path") != relative
            or record.get("before_sha256") != before_hash
            or record.get("before_row_count_including_header")
            != {
                "CDKT": CDKT_BEFORE_ROW_COUNT,
                "KQKD": KQKD_BEFORE_ROW_COUNT,
                "LCTT": LCTT_BEFORE_ROW_COUNT,
                "TM": TM_BEFORE_ROW_COUNT,
            }[statement]
            or record.get("after_row_count_including_header") != row_count
        ):
            raise BusinessSchemaUpdateError(f"{statement} baseline identity drifted")
        if sha256_file(project_root / baseline_relative) != before_hash:
            raise BusinessSchemaUpdateError(f"{statement} sealed baseline workbook changed")
        path = project_root / relative
        current_payload = path.read_bytes()
        if sha256_bytes(current_payload) != record.get("after_sha256"):
            raise BusinessSchemaUpdateError(f"{statement} workbook differs from audited result")
        reproduced, _, _ = _build_updated_workbook(
            (project_root / baseline_relative).read_bytes(),
            statement_type=statement,
        )
        if current_payload != reproduced:
            raise BusinessSchemaUpdateError(
                f"{statement} workbook is not byte-identical to deterministic replay"
            )
        records = _identity_records(path)
        if len(records) != row_count:
            raise BusinessSchemaUpdateError(f"{statement} audited row count drifted")
        _assert_contiguous_ordinals(records, statement=statement)
        _assert_candidate(project_root / baseline_relative, path, statement=statement)
        delta_ids = {
            "CDKT": set(),
            "KQKD": set(),
            "LCTT": set(),
            "TM": set(CURRENT_MIGRATION_SCHEMA_IDS),
        }[statement]
        prior_pairs = [
            pair
            for pair in _item_pairs(records)
            if int(str(pair["report_norm_id"])) not in delta_ids
        ]
        prior_name_by_id = {
            ("CDKT", "4319"): CDKT_4319_OLD_NAME,
            ("CDKT", "4360"): CDKT_4360_OLD_NAME,
            ("LCTT", "4136"): LCTT_4136_OLD_NAME,
        }
        for pair in prior_pairs:
            prior_name = prior_name_by_id.get((statement, str(pair["report_norm_id"])))
            if prior_name is not None:
                pair["report_norm_name"] = prior_name
        if _records_hash(prior_pairs) != PRIOR_UNIVERSAL_IDENTITY_ORDER_SHA256[statement]:
            raise BusinessSchemaUpdateError(
                f"{statement} prior universal identity/order was not preserved"
            )
        if record.get("prior_universal_preservation") != {
            "before_sha256": PRIOR_UNIVERSAL_WORKBOOK_SHA256[statement],
            "existing_item_id_name_order_sha256": (
                PRIOR_UNIVERSAL_IDENTITY_ORDER_SHA256[statement]
            ),
            "existing_ids_and_relative_order_preserved": True,
        }:
            raise BusinessSchemaUpdateError(
                f"{statement} prior universal preservation audit drifted"
            )
        preservation = record.get("preservation")
        if not isinstance(preservation, dict):
            raise BusinessSchemaUpdateError(f"{statement} preservation audit is absent")
        baseline_records = _identity_records(project_root / baseline_relative)
        if preservation.get("existing_item_id_name_order_sha256") != _records_hash(
            _item_pairs(baseline_records)
        ):
            raise BusinessSchemaUpdateError(f"{statement} baseline item/order hash drifted")
        if (
            preservation.get("existing_ids_and_relative_order_preserved") is not True
            or preservation.get("zip_member_set_preserved") is not True
            or preservation.get("only_changed_zip_members") != sorted(_TARGET_MEMBERS)
            or preservation.get("allowed_existing_name_corrections")
            != _allowed_existing_name_corrections(statement)
        ):
            raise BusinessSchemaUpdateError(f"{statement} preservation claims drifted")
        baseline_member_hashes = _member_hashes((project_root / baseline_relative).read_bytes())
        if preservation.get("changed_zip_members_before_sha256") != {
            member: baseline_member_hashes[member] for member in sorted(_TARGET_MEMBERS)
        }:
            raise BusinessSchemaUpdateError(f"{statement} changed-member baseline hashes drifted")
        member_hashes = _member_hashes(path.read_bytes())
        for member, expected_hash in preservation.get("unchanged_zip_members_sha256", {}).items():
            if member_hashes.get(member) != expected_hash:
                raise BusinessSchemaUpdateError(f"{statement} unchanged member drift: {member}")
        if preservation.get("changed_zip_members_after_sha256") != {
            member: member_hashes[member] for member in sorted(_TARGET_MEMBERS)
        }:
            raise BusinessSchemaUpdateError(f"{statement} changed-member result hashes drifted")

    cdkt_records = _identity_records(project_root / CDKT_WORKBOOK)
    kqkd_records = _identity_records(project_root / KQKD_WORKBOOK)
    lctt_records = _identity_records(project_root / LCTT_WORKBOOK)
    tm_records = _identity_records(project_root / TM_WORKBOOK)
    cdkt_by_id = {record["report_norm_id"]: record for record in cdkt_records}
    kqkd_by_id = {record["report_norm_id"]: record for record in kqkd_records}
    lctt_by_id = {record["report_norm_id"]: record for record in lctt_records}
    tm_by_id = {record["report_norm_id"]: record for record in tm_records}
    if cdkt_by_id["4350"]["report_norm_name"] != CDKT_4350_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("CDKT 4350 correction drifted")
    if cdkt_by_id["4319"]["report_norm_name"] != CDKT_4319_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("CDKT 4319 correction drifted")
    if cdkt_by_id["4360"]["report_norm_name"] != CDKT_4360_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("CDKT 4360 correction drifted")
    if lctt_by_id["4136"]["report_norm_name"] != LCTT_4136_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("LCTT 4136 correction drifted")
    for schema_id, name in (
        (CDKT_OFF_BALANCE_TOTAL_ID, CDKT_OFF_BALANCE_TOTAL_NAME),
        (CDKT_SWAP_COMMITMENT_TOTAL_ID, CDKT_SWAP_COMMITMENT_TOTAL_NAME),
    ):
        record = cdkt_by_id[str(schema_id)]
        if (
            record["report_norm_name"] != name
            or record["source_row"] != CDKT_CUMULATIVE_DISPLAY_ORDERS[schema_id] + 2
        ):
            raise BusinessSchemaUpdateError(f"CDKT {schema_id} identity/position drifted")
    if cdkt_by_id[str(CDKT_TOTAL_EQUITY_ID)]["source_row"] != CDKT_TOTAL_EQUITY_FINAL_SOURCE_ROW:
        raise BusinessSchemaUpdateError("CDKT 5712 row position drifted")
    if (
        kqkd_by_id[str(KQKD_TOTAL_OPERATING_INCOME_ID)]["source_row"]
        != KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("KQKD 5713 row position drifted")
    if (
        lctt_by_id[str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID)]["source_row"]
        != LCTT_INVESTMENT_CONTRIBUTION_NET_FINAL_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("LCTT 5714 row position drifted")
    if (
        lctt_by_id[str(LCTT_INVESTMENT_PROPERTY_NET_ID)]["source_row"]
        != LCTT_INVESTMENT_PROPERTY_NET_FINAL_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("LCTT 6034 row position drifted")
    if kqkd_by_id["4382"]["report_norm_name"] != KQKD_4382_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("KQKD 4382 correction drifted")
    if lctt_by_id["4109"]["report_norm_name"] != LCTT_4109_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("LCTT 4109 correction drifted")
    if (
        lctt_by_id[str(LCTT_VPB_COMBINED_LOAN_ID)]["source_row"]
        != LCTT_VPB_COMBINED_LOAN_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("LCTT 6054 row position drifted")
    if tm_by_id["770"]["report_norm_name"] != TM_770_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("TM 770 correction drifted")
    if tm_by_id[str(TM_EDUCATION_ID)]["report_norm_name"] != TM_EDUCATION_NAME:
        raise BusinessSchemaUpdateError("TM 737 correction drifted")
    if (
        tm_by_id[str(TM_TOTAL_INTERBANK_PROVISION_ID)]["source_row"]
        != TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("TM 5718 row position drifted")
    unaffected = audit.get("unaffected_workbooks_sha256")
    expected_unaffected: dict[str, str] = {}
    if unaffected != expected_unaffected:
        raise BusinessSchemaUpdateError("unaffected workbook pins drifted")
    for relative, expected_hash in expected_unaffected.items():
        if sha256_file(project_root / relative) != expected_hash:
            raise BusinessSchemaUpdateError(f"unaffected workbook changed: {relative}")

    seen = _assert_global_identity(project_root, expected_count=UNIVERSAL_SCHEMA_ITEM_COUNT)
    if seen.get(CDKT_TOTAL_EQUITY_ID) != "CDKT":
        raise BusinessSchemaUpdateError("CDKT 5712 is not globally unique and correctly scoped")
    if seen.get(KQKD_TOTAL_OPERATING_INCOME_ID) != "KQKD":
        raise BusinessSchemaUpdateError("KQKD 5713 is not globally unique and correctly scoped")
    if seen.get(LCTT_INVESTMENT_CONTRIBUTION_NET_ID) != "LCTT":
        raise BusinessSchemaUpdateError("LCTT 5714 is not globally unique and correctly scoped")
    if seen.get(LCTT_INVESTMENT_PROPERTY_NET_ID) != "LCTT":
        raise BusinessSchemaUpdateError("LCTT 6034 is not globally unique and correctly scoped")
    if seen.get(TM_TOTAL_INTERBANK_PROVISION_ID) != "TM":
        raise BusinessSchemaUpdateError("TM 5718 is not globally unique and correctly scoped")
    for schema_id in CDKT_VPB_SCHEMA_IDS:
        if seen.get(schema_id) != "CDKT":
            raise BusinessSchemaUpdateError(
                f"CDKT {schema_id} is not globally unique and correctly scoped"
            )
    for schema_id in CDKT_CURRENT_SCHEMA_IDS:
        if seen.get(schema_id) != "CDKT":
            raise BusinessSchemaUpdateError(
                f"CDKT {schema_id} is not globally unique and correctly scoped"
            )
    if seen.get(LCTT_VPB_COMBINED_LOAN_ID) != "LCTT":
        raise BusinessSchemaUpdateError("LCTT 6054 is not globally unique and correctly scoped")
    for schema_id in (
        TM_HEALTH_SOCIAL_ID,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
        *TM_PAGE50_TAX_SCHEMA_IDS,
        TM_PURCHASED_PRINCIPAL_ID,
        TM_PURCHASED_INTEREST_ID,
        TM_GOVERNMENT_GUARANTEED_DEBT_ID,
        TM_FX_BUY_ID,
        TM_FX_SELL_ID,
        TM_SWAP_BUY_ID,
        TM_SWAP_SELL_ID,
        TM_MARGIN_LOAN_TYPE_ID,
        TM_MARGIN_LOAN_QUALITY_ID,
        TM_MARGIN_LOAN_MATURITY_ID,
        TM_MARGIN_LOAN_BUSINESS_ID,
        TM_MARGIN_LOAN_INDUSTRY_ID,
        *TM_PAGE52_61_SCHEMA_IDS,
        *TM_COVERAGE_SCHEMA_IDS,
        *TM_UNIVERSAL_SCHEMA_IDS,
    ):
        if seen.get(schema_id) != "TM":
            raise BusinessSchemaUpdateError(
                f"TM {schema_id} is not globally unique and correctly scoped"
            )
    if set(seen) & REVIEWED_EXTERNAL_IDS:
        raise BusinessSchemaUpdateError("current schema collides with reviewed external IDs")

    supporting = audit.get("supporting_hierarchy_workbooks_sha256")
    if (
        audit.get("supporting_hierarchy_workbooks_mutated") is not False
        or not isinstance(supporting, dict)
        or not supporting
    ):
        raise BusinessSchemaUpdateError("supporting hierarchy preservation audit is absent")
    for relative, expected_hash in supporting.items():
        if sha256_file(project_root / relative) != expected_hash:
            raise BusinessSchemaUpdateError(f"supporting hierarchy workbook changed: {relative}")
    return audit


def apply_business_schema_update(
    project_root: Path,
    *,
    audit_path: Path | None = None,
) -> BusinessSchemaUpdateResult:
    project_root = project_root.resolve()
    audit_path = (
        audit_path.resolve() if audit_path is not None else project_root / BUSINESS_UPDATE_AUDIT
    )
    if audit_path.is_file():
        audit = verify_business_schema_update(project_root, audit_path)
        return BusinessSchemaUpdateResult(
            status="ALREADY_APPLIED_AND_VERIFIED",
            audit_path=str(audit_path),
            workbook_sha256={
                statement: str(record["after_sha256"])
                for statement, record in audit["workbooks"].items()
            },
        )

    baseline_paths = {
        "CDKT": project_root / CDKT_BASELINE_WORKBOOK,
        "KQKD": project_root / KQKD_BASELINE_WORKBOOK,
        "LCTT": project_root / LCTT_BASELINE_WORKBOOK,
        "TM": project_root / TM_BASELINE_WORKBOOK,
    }
    workbook_paths = {
        "CDKT": project_root / CDKT_WORKBOOK,
        "KQKD": project_root / KQKD_WORKBOOK,
        "LCTT": project_root / LCTT_WORKBOOK,
        "TM": project_root / TM_WORKBOOK,
    }
    preexisting_paths = {path for path in workbook_paths.values() if path.exists()}
    before_payloads = {statement: path.read_bytes() for statement, path in baseline_paths.items()}
    if sha256_bytes(before_payloads["CDKT"]) != CDKT_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("CDKT workbook is not the authorized baseline")
    if sha256_bytes(before_payloads["KQKD"]) != KQKD_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("KQKD workbook is not the authorized baseline")
    if sha256_bytes(before_payloads["LCTT"]) != LCTT_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("LCTT workbook is not the authorized baseline")
    if sha256_bytes(before_payloads["TM"]) != TM_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("TM workbook is not the authorized baseline")
    before_seen = _assert_global_identity(
        project_root,
        cdkt_path=baseline_paths["CDKT"],
        kqkd_path=baseline_paths["KQKD"],
        lctt_path=baseline_paths["LCTT"],
        tm_path=baseline_paths["TM"],
        expected_count=BASE_SCHEMA_ITEM_COUNT,
    )
    if NEW_SCHEMA_IDS & set(before_seen):
        raise BusinessSchemaUpdateError("one or more authorized new IDs already exist")
    if set(before_seen) & REVIEWED_EXTERNAL_IDS:
        raise BusinessSchemaUpdateError("baseline schema collides with reviewed external IDs")

    candidate_payloads: dict[str, bytes] = {}
    before_member_hashes: dict[str, dict[str, str]] = {}
    after_member_hashes: dict[str, dict[str, str]] = {}
    for statement in ("CDKT", "KQKD", "LCTT", "TM"):
        after, before_members, after_members = _build_updated_workbook(
            before_payloads[statement], statement_type=statement
        )
        candidate_payloads[statement] = after
        before_member_hashes[statement] = before_members
        after_member_hashes[statement] = after_members
        if workbook_paths[statement].exists():
            existing_sha256 = sha256_file(workbook_paths[statement])
            if existing_sha256 not in {
                sha256_bytes(after),
                *PREVIOUS_V2_SHA256[statement],
            }:
                raise BusinessSchemaUpdateError(
                    f"existing {statement} v2 workbook is neither the prior sealed result "
                    "nor the deterministic candidate"
                )

    candidate_paths: dict[str, Path] = {}
    try:
        for statement, payload in candidate_payloads.items():
            descriptor, name = tempfile.mkstemp(
                prefix=f".{statement.lower()}-business-schema-candidate-",
                suffix=".xlsx",
                dir=workbook_paths[statement].parent,
            )
            path = Path(name)
            candidate_paths[statement] = path
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            _assert_candidate(baseline_paths[statement], path, statement=statement)
        candidate_seen = _assert_global_identity(
            project_root,
            overrides=candidate_paths,
            expected_count=UNIVERSAL_SCHEMA_ITEM_COUNT,
        )
        if (
            candidate_seen.get(CDKT_TOTAL_EQUITY_ID) != "CDKT"
            or candidate_seen.get(KQKD_TOTAL_OPERATING_INCOME_ID) != "KQKD"
            or candidate_seen.get(LCTT_INVESTMENT_CONTRIBUTION_NET_ID) != "LCTT"
            or candidate_seen.get(LCTT_INVESTMENT_PROPERTY_NET_ID) != "LCTT"
            or candidate_seen.get(LCTT_VPB_COMBINED_LOAN_ID) != "LCTT"
            or candidate_seen.get(TM_TOTAL_INTERBANK_PROVISION_ID) != "TM"
            or any(candidate_seen.get(schema_id) != "CDKT" for schema_id in CDKT_VPB_SCHEMA_IDS)
            or any(
                candidate_seen.get(schema_id) != "TM"
                for schema_id in (
                    TM_HEALTH_SOCIAL_ID,
                    TM_ARTS_RECREATION_ID,
                    TM_OTHER_SERVICES_ID,
                    TM_HOUSEHOLD_EMPLOYMENT_ID,
                    *TM_PAGE50_TAX_SCHEMA_IDS,
                    TM_PURCHASED_PRINCIPAL_ID,
                    TM_PURCHASED_INTEREST_ID,
                    TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                    TM_FX_BUY_ID,
                    TM_FX_SELL_ID,
                    TM_SWAP_BUY_ID,
                    TM_SWAP_SELL_ID,
                    TM_MARGIN_LOAN_TYPE_ID,
                    TM_MARGIN_LOAN_QUALITY_ID,
                    TM_MARGIN_LOAN_MATURITY_ID,
                    TM_MARGIN_LOAN_BUSINESS_ID,
                    TM_MARGIN_LOAN_INDUSTRY_ID,
                    *TM_PAGE52_61_SCHEMA_IDS,
                    *TM_COVERAGE_SCHEMA_IDS,
                    *TM_UNIVERSAL_SCHEMA_IDS,
                )
            )
        ):
            raise BusinessSchemaUpdateError("candidate global ID/statement bindings drifted")
    finally:
        for path in candidate_paths.values():
            path.unlink(missing_ok=True)

    hierarchy_paths = (
        "vst_level/vst_bank_balance_sheet.xlsx",
        "vst_level/vst_bank_income_sheet.xlsx",
        "vst_level/vst_bank_cashflow_sheet.xlsx",
        "vst_level/vst_bank_detailed_notes_sheet.xlsx",
    )
    supporting_hashes = {
        relative: sha256_file(project_root / relative) for relative in hierarchy_paths
    }
    workbook_audit: dict[str, dict[str, object]] = {}
    for statement in ("CDKT", "KQKD", "LCTT", "TM"):
        before_records = _identity_records(baseline_paths[statement])
        unchanged_members = {
            name: digest
            for name, digest in before_member_hashes[statement].items()
            if name not in _TARGET_MEMBERS
        }
        workbook_audit[statement] = {
            "baseline_path": {
                "CDKT": CDKT_BASELINE_WORKBOOK,
                "KQKD": KQKD_BASELINE_WORKBOOK,
                "LCTT": LCTT_BASELINE_WORKBOOK,
                "TM": TM_BASELINE_WORKBOOK,
            }[statement],
            "path": {
                "CDKT": CDKT_WORKBOOK,
                "KQKD": KQKD_WORKBOOK,
                "LCTT": LCTT_WORKBOOK,
                "TM": TM_WORKBOOK,
            }[statement],
            "before_sha256": {
                "CDKT": CDKT_BEFORE_SHA256,
                "KQKD": KQKD_BEFORE_SHA256,
                "LCTT": LCTT_BEFORE_SHA256,
                "TM": TM_BEFORE_SHA256,
            }[statement],
            "after_sha256": sha256_bytes(candidate_payloads[statement]),
            "before_row_count_including_header": len(before_records),
            "after_row_count_including_header": {
                "CDKT": CDKT_AFTER_ROW_COUNT,
                "KQKD": KQKD_AFTER_ROW_COUNT,
                "LCTT": LCTT_AFTER_ROW_COUNT,
                "TM": TM_AFTER_ROW_COUNT,
            }[statement],
            "prior_universal_preservation": {
                "before_sha256": PRIOR_UNIVERSAL_WORKBOOK_SHA256[statement],
                "existing_item_id_name_order_sha256": (
                    PRIOR_UNIVERSAL_IDENTITY_ORDER_SHA256[statement]
                ),
                "existing_ids_and_relative_order_preserved": True,
            },
            "preservation": {
                "existing_item_id_name_order_sha256": _records_hash(_item_pairs(before_records)),
                "existing_ids_and_relative_order_preserved": True,
                "allowed_existing_name_corrections": _allowed_existing_name_corrections(statement),
                "zip_member_set_preserved": True,
                "only_changed_zip_members": sorted(_TARGET_MEMBERS),
                "unchanged_zip_members_sha256": unchanged_members,
                "changed_zip_members_before_sha256": {
                    name: before_member_hashes[statement][name] for name in sorted(_TARGET_MEMBERS)
                },
                "changed_zip_members_after_sha256": {
                    name: after_member_hashes[statement][name] for name in sorted(_TARGET_MEMBERS)
                },
            },
        }

    audit: dict[str, object] = {
        "format_version": 1,
        "migration_id": "BUSINESS-SCHEMA-5712-5713-5714-5718-6060",
        "status": "APPLIED_AND_VERIFIED",
        "applied_at": "2026-08-09T00:00:00+00:00",
        "authority": {
            "approved_on": "2026-08-09",
            "policy": "USER_AUTHORIZED_EVOLVING_UNIVERSAL_BANK_BCTC_SCHEMA",
            "decision_ids": ["Q074", "Q075", "Q076", "Q077", "Q078", "Q079"],
        },
        "collision_safety": {
            "baseline_global_schema_count": BASE_SCHEMA_ITEM_COUNT,
            "result_global_schema_count": UNIVERSAL_SCHEMA_ITEM_COUNT,
            "new_ids": sorted(NEW_SCHEMA_IDS),
            "reviewed_external_ids": sorted(REVIEWED_EXTERNAL_IDS),
            "new_ids_disjoint_from_reviewed_external_ids": True,
            "result_ids_globally_unique": True,
        },
        "schema_changes": _expected_schema_changes(),
        "hierarchy_changes": _expected_hierarchy_changes(),
        "structural_alias_changes": _expected_structural_alias_changes(),
        "business_formulas": _expected_formulas(),
        "workbooks": workbook_audit,
        "schema_strategy": _expected_schema_strategy(
            after_workbook_sha256={
                statement: sha256_bytes(payload)
                for statement, payload in candidate_payloads.items()
            }
        ),
        "unaffected_workbooks_sha256": {},
        "supporting_hierarchy_workbooks_mutated": False,
        "supporting_hierarchy_workbooks_sha256": supporting_hashes,
    }

    try:
        for statement in ("CDKT", "KQKD", "LCTT", "TM"):
            mode = baseline_paths[statement].stat().st_mode & 0o777
            atomic_write_bytes(workbook_paths[statement], candidate_payloads[statement], mode=mode)
        atomic_write_json(audit_path, audit)
        verify_business_schema_update(project_root, audit_path)
    except Exception:
        for path in workbook_paths.values():
            if path not in preexisting_paths:
                path.unlink(missing_ok=True)
        audit_path.unlink(missing_ok=True)
        raise

    return BusinessSchemaUpdateResult(
        status="APPLIED_AND_VERIFIED",
        audit_path=str(audit_path),
        workbook_sha256={
            statement: sha256_bytes(payload) for statement, payload in candidate_payloads.items()
        },
    )


def _apply_structural_alias_changes(
    schema: Sequence[SchemaItem],
    by_key: dict[tuple[str, int], SchemaItem],
) -> None:
    for change in _expected_structural_alias_changes():
        statement = str(change["statement_type"])
        schema_id = int(change["schema_id"])
        alias = str(change["alias"])
        target = by_key[(statement, schema_id)]
        alias_key = retrieval_key(alias)
        target_keys = {
            retrieval_key(target.canonical_name),
            *(retrieval_key(value) for value in target.structural_aliases),
        }
        other_owners = sorted(
            item.schema_id
            for item in schema
            if item.statement_type == statement
            and item.schema_id != schema_id
            and alias_key
            in {
                retrieval_key(item.canonical_name),
                *(retrieval_key(value) for value in item.structural_aliases),
            }
        )
        if change["added_to_structural_aliases"] is True:
            if alias_key in target_keys:
                raise BusinessSchemaUpdateError(
                    f"audited structural alias already registered at {statement}/{schema_id}"
                )
            allowed_branch_collision = (
                change.get("collision_handling") == "OPPOSITE_CASH_FLOW_BRANCH_TYPED_ALIAS"
                and bool(other_owners)
                and change.get("collision_schema_ids") == other_owners
                and statement == "LCTT"
                and target.cash_flow_branch in {"DIRECT", "INDIRECT"}
                and all(
                    by_key[(statement, owner)].cash_flow_branch in {"DIRECT", "INDIRECT"}
                    and by_key[(statement, owner)].cash_flow_branch != target.cash_flow_branch
                    for owner in other_owners
                )
            )
            declared_branch_collision = (
                change.get("collision_handling") == "OPPOSITE_CASH_FLOW_BRANCH_TYPED_ALIAS"
            )
            if (declared_branch_collision or other_owners) and not allowed_branch_collision:
                raise BusinessSchemaUpdateError(
                    f"audited structural alias collision at {statement}/{schema_id}: {other_owners}"
                )
            target.structural_aliases.append(alias)
        elif change["disposition"] == "CANONICAL_AFTER_CORRECTION_NOT_DUPLICATED_AS_ALIAS":
            if alias_key != retrieval_key(target.canonical_name) or other_owners:
                raise BusinessSchemaUpdateError(
                    f"canonical alias disposition drifted at {statement}/{schema_id}"
                )
        elif change["disposition"] == "REJECTED_CANONICAL_LABEL_COLLISION":
            if other_owners != [int(change["collision_schema_id"])]:
                raise BusinessSchemaUpdateError(
                    f"structural alias collision disposition drifted at {statement}/{schema_id}"
                )
        else:
            raise BusinessSchemaUpdateError(
                f"unknown structural alias disposition at {statement}/{schema_id}"
            )


def apply_business_formula_hierarchy(schema: Sequence[SchemaItem]) -> None:
    """Apply the authorized formula hierarchy after the supplied VST hierarchy.

    The VST workbooks stay immutable. Their original edges are loaded first, then
    this small, audited overlay introduces the new totals and corrects the
    pre-existing 4325 component boundary required by the approved formulas.
    """

    by_key = {(item.statement_type, item.schema_id): item for item in schema}
    if not any(
        key in by_key
        for key in (
            ("CDKT", 5712),
            ("KQKD", 5713),
            ("LCTT", 5714),
            ("TM", 5718),
        )
    ):
        return
    required = (
        {
            ("CDKT", schema_id)
            for schema_id in (
                4304,
                4305,
                4306,
                4325,
                4364,
                *CDKT_4325_COMPONENTS,
                5712,
                *CDKT_VPB_SCHEMA_IDS,
                *CDKT_CURRENT_SCHEMA_IDS,
                4313,
                4316,
                4318,
            )
        }
        | {
            ("KQKD", schema_id)
            for schema_id in (4376, 4391, *KQKD_TOTAL_OPERATING_INCOME_COMPONENTS, 5713)
        }
        | {
            ("LCTT", schema_id)
            for schema_id in (
                4111,
                4118,
                4119,
                4143,
                4144,
                4145,
                4146,
                4147,
                4120,
                4121,
                5714,
                LCTT_INVESTMENT_PROPERTY_NET_ID,
                LCTT_VPB_COMBINED_LOAN_ID,
                4107,
                4108,
                4109,
                4110,
                *range(4129, 4142),
            )
        }
        | {("TM", schema_id) for schema_id in (575, *TM_TOTAL_INTERBANK_PROVISION_COMPONENTS, 5718)}
        | {
            ("TM", schema_id)
            for schema_id in (
                TM_LOAN_INDUSTRY_PARENT_ID,
                TM_EDUCATION_ID,
                TM_HEALTH_SOCIAL_ID,
                TM_ARTS_RECREATION_ID,
                TM_OTHER_SERVICES_ID,
                TM_HOUSEHOLD_EMPLOYMENT_ID,
                TM_LOAN_BUSINESS_PARENT_ID,
                TM_LOAN_BUSINESS_OTHER_ID,
                *range(784, 800),
                1142,
                *TM_PAGE50_TAX_SCHEMA_IDS,
                800,
                805,
                TM_PURCHASED_PRINCIPAL_ID,
                TM_PURCHASED_INTEREST_ID,
                TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                1294,
                1301,
                1302,
                TM_FX_BUY_ID,
                TM_FX_SELL_ID,
                TM_SWAP_BUY_ID,
                TM_SWAP_SELL_ID,
                717,
                747,
                752,
                TM_MARGIN_LOAN_TYPE_ID,
                TM_MARGIN_LOAN_QUALITY_ID,
                TM_MARGIN_LOAN_MATURITY_ID,
                TM_MARGIN_LOAN_BUSINESS_ID,
                TM_MARGIN_LOAN_INDUSTRY_ID,
                759,
                *range(760, 766),
                1055,
                1259,
                1295,
                *TM_PAGE52_61_SCHEMA_IDS,
                *TM_COVERAGE_SCHEMA_IDS,
                *TM_UNIVERSAL_SCHEMA_IDS,
                862,
                867,
                868,
                869,
                881,
                882,
                883,
                894,
                895,
                913,
                914,
                927,
                928,
                929,
                940,
                941,
                942,
                943,
                944,
                955,
                956,
                957,
                965,
                967,
                980,
                981,
                1075,
                1089,
                *range(1100, 1118),
                1128,
                1131,
                1151,
                1157,
                1167,
                1188,
                1193,
                *range(1352, 1483),
                *range(1483, 1759),
                *range(1759, 1945),
            )
        }
        | {
            (statement, schema_id)
            for statement, schema_id, _page, _row, _alias in VPB_STRUCTURAL_ALIAS_CANDIDATES
        }
        | {
            (statement, schema_id)
            for statement, schema_id, _alias in DISPLAY_NAME_COMPATIBILITY_ALIASES
        }
        | {
            (statement, schema_id)
            for statement, schema_id, _page, _row, _alias in NEW_ITEM_SOURCE_ALIASES
        }
        | {
            (statement, schema_id)
            for statement, schema_id, _page, _row, _alias in MBB_OFF_BALANCE_SOURCE_ALIASES
        }
        | {
            (statement, schema_id)
            for statement, schema_id, _page, _row, _alias in MBB_OFF_BALANCE_WORDING_ALIASES
        }
    )
    missing = sorted(required - set(by_key))
    if missing:
        raise BusinessSchemaUpdateError(f"business-formula hierarchy lacks schema items: {missing}")

    expected_initial_parents = {
        ("CDKT", 4325): 4305,
        ("CDKT", 4306): 4305,
        ("CDKT", 4365): 4364,
        **{("KQKD", schema_id): 4376 for schema_id in KQKD_TOTAL_OPERATING_INCOME_COMPONENTS},
        ("KQKD", 4391): 4376,
        ("LCTT", 4120): 4111,
        ("LCTT", 4121): 4111,
        **{("LCTT", schema_id): 4111 for schema_id in LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS},
        ("LCTT", LCTT_INVESTMENT_PROPERTY_NET_ID): None,
        ("LCTT", LCTT_VPB_COMBINED_LOAN_ID): None,
        ("LCTT", 4107): None,
        ("LCTT", 4108): None,
        **{("LCTT", schema_id): 4110 for schema_id in range(4129, 4142)},
        **{("CDKT", schema_id): None for schema_id in CDKT_VPB_SCHEMA_IDS},
        **{("CDKT", schema_id): None for schema_id in CDKT_CURRENT_SCHEMA_IDS},
        ("TM", TM_EDUCATION_ID): TM_LOAN_INDUSTRY_PARENT_ID,
        ("TM", TM_LOAN_BUSINESS_OTHER_ID): TM_LOAN_BUSINESS_PARENT_ID,
        **{("TM", schema_id): TM_PROVISION_MOVEMENT_ID for schema_id in range(784, 800)},
        ("TM", 1301): 1294,
        ("TM", 1302): 1294,
        ("TM", TM_MARGIN_LOAN_TYPE_ID): None,
        ("TM", TM_MARGIN_LOAN_QUALITY_ID): None,
        ("TM", TM_MARGIN_LOAN_MATURITY_ID): None,
        ("TM", TM_MARGIN_LOAN_BUSINESS_ID): None,
        ("TM", TM_MARGIN_LOAN_INDUSTRY_ID): None,
        **{("TM", schema_id): 759 for schema_id in range(760, 766)},
        **{("TM", schema_id): None for schema_id in TM_PAGE52_61_SCHEMA_IDS},
        **{("TM", schema_id): None for schema_id in TM_COVERAGE_SCHEMA_IDS},
        **{("TM", schema_id): None for schema_id in TM_UNIVERSAL_SCHEMA_IDS},
        **{
            ("TM", schema_id): parent_id
            for parent_id, schema_ids in (
                (869, tuple(range(871, 882))),
                (883, tuple(range(885, 895))),
                (914, tuple(range(916, 921))),
                (929, tuple(range(931, 941))),
                (943, tuple(range(945, 955))),
                (956, tuple(range(958, 961))),
                (1128, tuple(range(1130, 1141))),
            )
            for schema_id in schema_ids
        },
        **{("TM", schema_id): 1100 for schema_id in range(1101, 1118)},
        **{
            ("TM", schema_id): parent_id
            for parent_id, schema_ids in (
                (1353, (1363, 1364, 1366, 1367, 1368, 1369, 1375)),
                (1379, (1389, 1390, 1392, 1393, 1394, 1395, 1401)),
                (1431, (1441, 1442, 1444, 1445, 1446, 1447, 1453)),
                (1457, (1467, 1468, 1470, 1471, 1472, 1473, 1479)),
                (1484, (1491, 1494, 1495)),
                (1509, (1516, 1519, 1520)),
                (1584, (1591, 1594, 1595)),
                (1609, (1616, 1619, 1620)),
                (1634, (1641, 1644, 1645)),
                (1659, (1666, 1669, 1670)),
                (1734, (1741, 1744, 1745)),
                (1806, (1816, 1817)),
                (1829, (1839, 1840)),
                (1852, (1862, 1863)),
                (1875, (1885, 1886)),
                (1898, (1908, 1909)),
                (1921, (1931, 1932)),
            )
            for schema_id in schema_ids
        },
    }
    for key, expected_parent in expected_initial_parents.items():
        if by_key[key].parent_id != expected_parent:
            raise BusinessSchemaUpdateError(
                f"pre-overlay hierarchy parent drift at {key}: "
                f"expected={expected_parent}, actual={by_key[key].parent_id}"
            )

    by_key[("CDKT", 4365)].parent_id = 4325
    by_key[("CDKT", 4325)].parent_id = CDKT_TOTAL_EQUITY_ID
    by_key[("CDKT", 4306)].parent_id = CDKT_TOTAL_EQUITY_ID
    by_key[("CDKT", CDKT_TOTAL_EQUITY_ID)].parent_id = 4305
    by_key[("CDKT", CDKT_TOTAL_EQUITY_ID)].hierarchy_level = 2
    by_key[("CDKT", CDKT_TOTAL_EQUITY_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id, _name, parent_id, level, section, *_rest in CDKT_VPB_SCHEMA_ITEMS:
        item = by_key[("CDKT", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.notes_section = section
        if schema_id >= 6038:
            item.scope = ["CONSOLIDATED"]
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id, parent_id, level in (
        (CDKT_OFF_BALANCE_TOTAL_ID, 6038, 1),
        (CDKT_SWAP_COMMITMENT_TOTAL_ID, 6041, 4),
    ):
        item = by_key[("CDKT", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.notes_section = "OFF_BALANCE_SHEET"
        item.scope = ["CONSOLIDATED"]
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in KQKD_TOTAL_OPERATING_INCOME_COMPONENTS:
        by_key[("KQKD", schema_id)].parent_id = KQKD_TOTAL_OPERATING_INCOME_ID
    by_key[("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID)].parent_id = 4376
    by_key[("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID)].hierarchy_level = 0
    by_key[("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS:
        by_key[("LCTT", schema_id)].parent_id = LCTT_INVESTMENT_CONTRIBUTION_NET_ID
    by_key[("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID)].parent_id = 4111
    by_key[("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID)].hierarchy_level = 3
    by_key[("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS:
        item = by_key[("LCTT", schema_id)]
        item.parent_id = LCTT_INVESTMENT_PROPERTY_NET_ID
        item.hierarchy_level = 3
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    property_net = by_key[("LCTT", LCTT_INVESTMENT_PROPERTY_NET_ID)]
    property_net.parent_id = 4111
    property_net.hierarchy_level = 2
    property_net.notes_section = "DIRECT_CASH_FLOW_INVESTING_ACTIVITIES"
    property_net.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (4107, 4108):
        item = by_key[("LCTT", schema_id)]
        item.parent_id = 4110
        item.hierarchy_level = 1
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id in range(4129, 4135):
        item = by_key[("LCTT", schema_id)]
        item.parent_id = 4107
        item.hierarchy_level = 2
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id in range(4135, 4142):
        item = by_key[("LCTT", schema_id)]
        item.parent_id = 4108
        item.hierarchy_level = 2
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    combined_loan = by_key[("LCTT", LCTT_VPB_COMBINED_LOAN_ID)]
    combined_loan.parent_id = LCTT_VPB_COMBINED_LOAN_PARENT_ID
    combined_loan.hierarchy_level = LCTT_VPB_COMBINED_LOAN_HIERARCHY_LEVEL
    combined_loan.notes_section = "DIRECT_CASH_FLOW_OPERATING_ASSET_CHANGES"
    combined_loan.hierarchy_source = BUSINESS_UPDATE_AUDIT

    by_key[("TM", TM_TOTAL_INTERBANK_PROVISION_ID)].parent_id = 575
    by_key[("TM", TM_TOTAL_INTERBANK_PROVISION_ID)].hierarchy_level = 2
    by_key[("TM", TM_TOTAL_INTERBANK_PROVISION_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (
        TM_HEALTH_SOCIAL_ID,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
    ):
        by_key[("TM", schema_id)].parent_id = TM_LOAN_INDUSTRY_PARENT_ID
        by_key[("TM", schema_id)].hierarchy_level = 3
        by_key[("TM", schema_id)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in range(785, 792):
        by_key[("TM", schema_id)].parent_id = TM_GENERAL_PROVISION_MOVEMENT_ID
    for schema_id in range(793, 800):
        by_key[("TM", schema_id)].parent_id = TM_SPECIFIC_PROVISION_MOVEMENT_ID

    page50_parent_by_id = {
        5723: 5727,
        5724: 5723,
        5725: 5727,
        5726: 5725,
        5727: 1142,
        5728: 5731,
        5729: 5731,
        5730: 5731,
        5731: 1142,
        5732: 5737,
        5733: 5737,
        5734: 5737,
        5735: 5737,
        5736: 5737,
        5737: 1142,
    }
    page50_level_by_id = {
        5723: 2,
        5724: 3,
        5725: 2,
        5726: 3,
        5727: 1,
        5728: 2,
        5729: 2,
        5730: 2,
        5731: 1,
        5732: 2,
        5733: 2,
        5734: 2,
        5735: 2,
        5736: 2,
        5737: 1,
    }
    for schema_id in TM_PAGE50_TAX_SCHEMA_IDS:
        item = by_key[("TM", schema_id)]
        item.parent_id = page50_parent_by_id[schema_id]
        item.hierarchy_level = page50_level_by_id[schema_id]
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (TM_PURCHASED_PRINCIPAL_ID, TM_PURCHASED_INTEREST_ID):
        item = by_key[("TM", schema_id)]
        item.parent_id = 800
        item.hierarchy_level = 2
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    guaranteed = by_key[("TM", TM_GOVERNMENT_GUARANTEED_DEBT_ID)]
    guaranteed.parent_id = 805
    guaranteed.hierarchy_level = 3
    guaranteed.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (TM_FX_BUY_ID, TM_FX_SELL_ID):
        item = by_key[("TM", schema_id)]
        item.parent_id = 1301
        item.hierarchy_level = 3
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    swap = by_key[("TM", 1302)]
    swap.parent_id = 1301
    swap.hierarchy_level = 3
    swap.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id in (TM_SWAP_BUY_ID, TM_SWAP_SELL_ID):
        item = by_key[("TM", schema_id)]
        item.parent_id = 1302
        item.hierarchy_level = 4
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    margin_hierarchy = {
        TM_MARGIN_LOAN_TYPE_ID: (717, 3),
        TM_MARGIN_LOAN_QUALITY_ID: (747, 4),
        TM_MARGIN_LOAN_MATURITY_ID: (752, 3),
        TM_MARGIN_LOAN_BUSINESS_ID: (766, 3),
        TM_MARGIN_LOAN_INDUSTRY_ID: (727, 3),
    }
    for schema_id, (parent_id, level) in margin_hierarchy.items():
        item = by_key[("TM", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in range(760, 765):
        item = by_key[("TM", schema_id)]
        item.parent_id = 5752
        item.hierarchy_level = 4
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id, _name, _source_row, _order, parent_id, level in TM_PAGE52_61_SCHEMA_ITEMS:
        item = by_key[("TM", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id, _name, parent_id, level in TM_COVERAGE_SCHEMA_ITEMS:
        item = by_key[("TM", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id, _name, parent_id, level in TM_UNIVERSAL_SCHEMA_ITEMS:
        item = by_key[("TM", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.notes_section = (
            "BALANCE_SHEET_NOTES"
            if schema_id <= 6020 or schema_id >= 6057
            else "INCOME_STATEMENT_NOTES"
        )
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    universal_reparent_groups = (
        (5991, tuple(range(871, 876)), 4),
        (5992, tuple(range(876, 882)), 4),
        (5994, tuple(range(885, 888)), 4),
        (5995, tuple(range(888, 895)), 4),
        (5997, tuple(range(916, 921)), 4),
        (5999, tuple(range(931, 934)), 4),
        (6000, tuple(range(934, 941)), 4),
        (6002, tuple(range(945, 952)), 4),
        (6003, tuple(range(952, 955)), 4),
        (6005, tuple(range(958, 961)), 4),
        (6019, tuple(range(1130, 1137)), 3),
        (6020, tuple(range(1137, 1141)), 3),
    )
    for parent_id, schema_ids, level in universal_reparent_groups:
        for schema_id in schema_ids:
            item = by_key[("TM", schema_id)]
            item.parent_id = parent_id
            item.hierarchy_level = level
            item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    currency_hierarchy = (
        (
            5849,
            (1363, 1364),
            1366,
            5850,
            (1367, 1370, 1371, 1372, 1373, 1374),
            1367,
            (1368, 1369),
            1375,
        ),
        (
            5851,
            (1389, 1390),
            1392,
            5852,
            (1393, 1396, 1397, 1398, 1399, 1400),
            1393,
            (1394, 1395),
            1401,
        ),
        (
            5853,
            (1441, 1442),
            1444,
            5854,
            (1445, 1448, 1449, 1450, 1451, 1452),
            1445,
            (1446, 1447),
            1453,
        ),
        (
            5855,
            (1467, 1468),
            1470,
            5856,
            (1471, 1474, 1475, 1476, 1477, 1478),
            1471,
            (1472, 1473),
            1479,
        ),
    )
    for (
        fixed_parent,
        fixed_children,
        liability_and_equity,
        total_liability,
        liability_children,
        interbank_parent,
        interbank_children,
        equity,
    ) in currency_hierarchy:
        for schema_id in fixed_children:
            item = by_key[("TM", schema_id)]
            item.parent_id = fixed_parent
            item.hierarchy_level = 4
            item.hierarchy_source = BUSINESS_UPDATE_AUDIT
        equity_item = by_key[("TM", equity)]
        equity_item.parent_id = liability_and_equity
        equity_item.hierarchy_level = 4
        equity_item.hierarchy_source = BUSINESS_UPDATE_AUDIT
        for schema_id in liability_children:
            item = by_key[("TM", schema_id)]
            item.parent_id = total_liability
            item.hierarchy_level = 5
            item.hierarchy_source = BUSINESS_UPDATE_AUDIT
        for schema_id in interbank_children:
            item = by_key[("TM", schema_id)]
            item.parent_id = interbank_parent
            item.hierarchy_level = 6
            item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for fixed_parent, fixed_children in (
        (5858, (1494, 1495)),
        (5860, (1519, 1520)),
        (5862, (1594, 1595)),
        (5864, (1619, 1620)),
        (5866, (1644, 1645)),
        (5868, (1669, 1670)),
        (5897, (1744, 1745)),
        (5924, (1816, 1817)),
        (5926, (1839, 1840)),
        (5928, (1862, 1863)),
        (5930, (1885, 1886)),
        (5932, (1908, 1909)),
        (5934, (1931, 1932)),
    ):
        for schema_id in fixed_children:
            item = by_key[("TM", schema_id)]
            item.parent_id = fixed_parent
            item.hierarchy_level = 4
            item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    debt_asset_axis = by_key[("TM", TM_PAGE54_DEBT_ASSET_AXIS_ID)]
    if TM_PAGE54_DEBT_ASSET_ALIAS not in debt_asset_axis.structural_aliases:
        debt_asset_axis.structural_aliases.append(TM_PAGE54_DEBT_ASSET_ALIAS)
    for schema_id in TM_PAGE60_COMBINED_LOAN_IDS:
        item = by_key[("TM", schema_id)]
        if TM_PAGE60_COMBINED_LOAN_SOURCE_ALIAS not in item.structural_aliases:
            item.structural_aliases.append(TM_PAGE60_COMBINED_LOAN_SOURCE_ALIAS)
    page61_root = by_key[("TM", TM_PAGE61_ROOT_ID)]
    if TM_PAGE61_ROOT_SOURCE_ALIAS not in page61_root.structural_aliases:
        page61_root.structural_aliases.append(TM_PAGE61_ROOT_SOURCE_ALIAS)
    for schema_id, _name, alias in TM_PAGE61_CURRENCIES:
        item = by_key[("TM", schema_id)]
        if alias not in item.structural_aliases:
            item.structural_aliases.append(alias)

    _apply_structural_alias_changes(schema, by_key)

    for item in schema:
        item.children = []
        item.siblings = []
    for item in sorted(
        schema, key=lambda candidate: (candidate.statement_type, candidate.display_order)
    ):
        if item.parent_id is not None:
            by_key[(item.statement_type, item.parent_id)].children.append(item.schema_id)
    for item in schema:
        if item.parent_id is not None:
            siblings = by_key[(item.statement_type, item.parent_id)].children
            item.siblings = [schema_id for schema_id in siblings if schema_id != item.schema_id]

    exact_edges = {
        ("CDKT", 4364): (4337, 4373, 4338, 4340, 4374, 4339),
        ("CDKT", 4325): CDKT_4325_COMPONENTS,
        ("CDKT", CDKT_TOTAL_EQUITY_ID): CDKT_TOTAL_EQUITY_COMPONENTS,
        ("CDKT", 4305): (4304, CDKT_TOTAL_EQUITY_ID),
        ("CDKT", 4313): (4346, 6035, 4347),
        ("CDKT", 4316): (4350, 4351, 6036, 4352),
        ("CDKT", 4318): (6037,),
        ("CDKT", 6038): (CDKT_OFF_BALANCE_TOTAL_ID,),
        ("CDKT", CDKT_OFF_BALANCE_TOTAL_ID): CDKT_OFF_BALANCE_TOTAL_COMPONENTS,
        ("CDKT", 6039): (6040, 6041, 6046, 6047, 6048),
        ("CDKT", 6041): CDKT_FX_COMMITMENT_COMPONENTS,
        ("CDKT", CDKT_SWAP_COMMITMENT_TOTAL_ID): CDKT_SWAP_COMMITMENT_TOTAL_COMPONENTS,
        ("CDKT", 6048): (6049,),
        ("CDKT", 6050): (6051, 6052, 6053),
        ("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID): KQKD_TOTAL_OPERATING_INCOME_COMPONENTS,
        ("KQKD", 4376): (KQKD_TOTAL_OPERATING_INCOME_ID, 4391),
        ("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID): (
            LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS
        ),
        ("LCTT", LCTT_INVESTMENT_PROPERTY_NET_ID): (LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS),
        ("LCTT", 4111): (
            4118,
            4119,
            4143,
            LCTT_INVESTMENT_PROPERTY_NET_ID,
            5714,
            4147,
        ),
        ("LCTT", 4110): (4109, 4107, 4108, 4142),
        ("LCTT", 4107): (4129, 4130, 4131, 4132, 6054, 4133, 4134),
        ("LCTT", 4108): tuple(range(4135, 4142)),
        ("TM", 575): (576, 585, 5718),
        ("TM", 576): (577, 578, 579, 580, 581, 582, 583, 584),
        ("TM", 585): (586, 587, 588, 589, 590, 591),
        ("TM", 5718): (),
        ("TM", 862): (863, 864, 865, 866, 867, 5959),
        ("TM", 867): (5960, 5961),
        ("TM", 868): (869, 883, 5964),
        ("TM", 869): (870, 5991, 5992, 5993, 5962, 882),
        ("TM", 5991): tuple(range(871, 876)),
        ("TM", 5992): tuple(range(876, 882)),
        ("TM", 883): (884, 5994, 5995, 5996, 5963, 895),
        ("TM", 5994): tuple(range(885, 888)),
        ("TM", 5995): tuple(range(888, 895)),
        ("TM", 5964): (5965, 5966),
        ("TM", 913): (914, 929, 5969),
        ("TM", 914): (915, 5997, *range(921, 928), 5998, 5967, 928),
        ("TM", 5997): tuple(range(916, 921)),
        ("TM", 929): (930, 5999, 6000, 6001, 5968, 941),
        ("TM", 5999): tuple(range(931, 934)),
        ("TM", 6000): tuple(range(934, 941)),
        ("TM", 5969): (5970, 5971),
        ("TM", 942): (943, 956, 5972),
        ("TM", 943): (944, 6002, 6003, 6004, 955),
        ("TM", 6002): tuple(range(945, 952)),
        ("TM", 6003): tuple(range(952, 955)),
        ("TM", 956): (957, 6005, 961, 962, 963, 964, 6006, 965),
        ("TM", 6005): tuple(range(958, 961)),
        ("TM", 5972): (5973, 5974),
        ("TM", 967): (6007, *range(968, 981), 5975, 5976, 981),
        ("TM", 1075): (5977, *range(1076, 1092)),
        ("TM", 1100): tuple(range(1101, 1118)),
        ("TM", 1101): (5978, 5979, 6008, 6009),
        ("TM", 1109): (5980, 5981, 6010),
        ("TM", 1128): (
            5982,
            5983,
            5984,
            *range(6011, 6019),
            1129,
            6019,
            6020,
            1141,
            5946,
            5949,
        ),
        ("TM", 6019): tuple(range(1130, 1137)),
        ("TM", 6020): tuple(range(1137, 1141)),
        ("TM", 5946): (5947, 5948),
        ("TM", 5949): (5950, 5951, 5953, 5956),
        ("TM", 5951): (5952,),
        ("TM", 5953): (5954, 5955),
        ("TM", 5956): (5957, 5958),
        ("TM", TM_LOAN_INDUSTRY_PARENT_ID): (
            728,
            729,
            730,
            731,
            732,
            733,
            734,
            735,
            736,
            TM_EDUCATION_ID,
            TM_HEALTH_SOCIAL_ID,
            738,
            739,
            6060,
            740,
            741,
            742,
            743,
            TM_ARTS_RECREATION_ID,
            TM_OTHER_SERVICES_ID,
            TM_HOUSEHOLD_EMPLOYMENT_ID,
            6059,
            744,
            745,
            6058,
            TM_MARGIN_LOAN_INDUSTRY_ID,
        ),
        ("TM", 717): (718, 719, 720, 6057, *range(721, 727), TM_MARGIN_LOAN_TYPE_ID),
        ("TM", 747): (TM_MARGIN_LOAN_QUALITY_ID,),
        ("TM", 752): (753, 754, 755, TM_MARGIN_LOAN_MATURITY_ID),
        ("TM", TM_LOAN_BUSINESS_PARENT_ID): (
            *range(767, 783),
            TM_MARGIN_LOAN_BUSINESS_ID,
        ),
        ("TM", TM_PROVISION_MOVEMENT_ID): TM_PROVISION_MOVEMENT_COMPONENTS,
        ("TM", TM_GENERAL_PROVISION_MOVEMENT_ID): tuple(range(785, 792)),
        ("TM", TM_SPECIFIC_PROVISION_MOVEMENT_ID): tuple(range(793, 800)),
        ("TM", 1142): (
            1143,
            1151,
            5985,
            1157,
            1167,
            5989,
            1175,
            1188,
            1193,
            5990,
            1198,
            1205,
            1221,
            6029,
            1229,
            1240,
            5727,
            5731,
            5737,
        ),
        ("TM", 1157): (6021, *range(1158, 1163), 6022, *range(1163, 1166), 5986, 1166),
        ("TM", 1167): (6023, *range(1168, 1174), 5987, 5988, 1174),
        ("TM", 1170): (6024, 6025),
        ("TM", 1175): (1176, 6026, *range(1177, 1183), 6027, *range(1183, 1188)),
        ("TM", 1193): (1194, 1195, 1196, 6028, 1197),
        ("TM", 1221): (6032, 1222, 1223, 6031, 1224, 1225, 6033, 1226, 1227, 1228),
        ("TM", 6029): (6030,),
        ("TM", 5723): (5724,),
        ("TM", 5725): (5726,),
        ("TM", 5727): (5723, 5725),
        ("TM", 5731): (5728, 5729, 5730),
        ("TM", 5737): (5732, 5733, 5734, 5735, 5736),
        ("TM", 800): (801, 802, 803, 5738, 5739),
        ("TM", 805): (
            806,
            807,
            5740,
            808,
            809,
            810,
            811,
            812,
            813,
            814,
            815,
            816,
            817,
            818,
            819,
            820,
            821,
            822,
            823,
            824,
            825,
            826,
            827,
            828,
        ),
        ("TM", 1294): (1295, 1296, 1297, 1298, 1299, 1300, 1301, 1303, 1304),
        ("TM", 1301): TM_FX_COMMITMENT_COMPONENTS,
        ("TM", 1302): TM_SWAP_COMMITMENT_COMPONENTS,
        ("TM", 759): (5752, 765),
        ("TM", 5752): tuple(range(760, 765)),
        ("TM", 1055): (1056, 1075, 5753),
        ("TM", 5753): (5754, 5755),
        ("TM", 1295): (5756,),
        ("TM", 5756): (5757, 5758),
        ("TM", 5750): (5751,),
        ("TM", 5759): (5760, 5761),
        ("TM", 1259): (
            1260,
            1269,
            1280,
            1289,
            1294,
            5750,
            5759,
            5762,
            1305,
            1352,
            1483,
            1759,
            5935,
        ),
        ("TM", 5762): (5763, 5806),
        ("TM", 5763): (5764, 5771, 5778, 5785, 5792, 5799),
        **{
            ("TM", axis_id): tuple(range(axis_id + 1, axis_id + 7))
            for axis_id in (5764, 5771, 5778, 5785, 5792, 5799)
        },
        ("TM", 5806): (5807, 5814, 5821, 5828, 5835, 5842),
        **{
            ("TM", axis_id): tuple(range(axis_id + 1, axis_id + 7))
            for axis_id in (5807, 5814, 5821, 5828, 5835, 5842)
        },
        ("TM", 1353): (
            1354,
            1355,
            1356,
            1357,
            1358,
            1359,
            1360,
            1361,
            1362,
            5849,
            1365,
            1366,
            1376,
            1377,
            1378,
        ),
        ("TM", 5849): (1363, 1364),
        ("TM", 1366): (5850, 1375),
        ("TM", 5850): (1367, 1370, 1371, 1372, 1373, 1374),
        ("TM", 1367): (1368, 1369),
        ("TM", 1379): (
            1380,
            1381,
            1382,
            1383,
            1384,
            1385,
            1386,
            1387,
            1388,
            5851,
            1391,
            1392,
            1402,
            1403,
            1404,
        ),
        ("TM", 5851): (1389, 1390),
        ("TM", 1392): (5852, 1401),
        ("TM", 5852): (1393, 1396, 1397, 1398, 1399, 1400),
        ("TM", 1393): (1394, 1395),
        ("TM", 1431): (
            1432,
            1433,
            1434,
            1435,
            1436,
            1437,
            1438,
            1439,
            1440,
            5853,
            1443,
            1444,
            1454,
            1455,
            1456,
        ),
        ("TM", 5853): (1441, 1442),
        ("TM", 1444): (5854, 1453),
        ("TM", 5854): (1445, 1448, 1449, 1450, 1451, 1452),
        ("TM", 1445): (1446, 1447),
        ("TM", 1457): (
            1458,
            1459,
            1460,
            1461,
            1462,
            1463,
            1464,
            1465,
            1466,
            5855,
            1469,
            1470,
            1480,
            1481,
            1482,
        ),
        ("TM", 5855): (1467, 1468),
        ("TM", 1470): (5856, 1479),
        ("TM", 5856): (1471, 1474, 1475, 1476, 1477, 1478),
        ("TM", 1471): (1472, 1473),
        ("TM", 1483): (1484, 1509, 1584, 1609, 1634, 1659, 1684, 1709, 5869, 1734),
        ("TM", 1484): (*range(1485, 1491), 5857, 1491, 1492, 1493, 5858, *range(1496, 1509)),
        ("TM", 5858): (1494, 1495),
        ("TM", 1509): (
            *range(1510, 1516),
            5859,
            1516,
            1517,
            1518,
            5860,
            *range(1521, 1534),
            1534,
            1559,
        ),
        ("TM", 5860): (1519, 1520),
        ("TM", 1584): (*range(1585, 1591), 5861, 1591, 1592, 1593, 5862, *range(1596, 1609)),
        ("TM", 5862): (1594, 1595),
        ("TM", 1609): (*range(1610, 1616), 5863, 1616, 1617, 1618, 5864, *range(1621, 1634)),
        ("TM", 5864): (1619, 1620),
        ("TM", 1634): (*range(1635, 1641), 5865, 1641, 1642, 1643, 5866, *range(1646, 1659)),
        ("TM", 5866): (1644, 1645),
        ("TM", 1659): (*range(1660, 1666), 5867, 1666, 1667, 1668, 5868, *range(1671, 1684)),
        ("TM", 5868): (1669, 1670),
        ("TM", 5869): (*range(5870, 5881), *range(5883, 5896)),
        ("TM", 5880): (5881, 5882),
        ("TM", 1734): (*range(1735, 1741), 5896, 1741, 1742, 1743, 5897, *range(1746, 1759)),
        ("TM", 5897): (1744, 1745),
        ("TM", 1759): (5898, 1760, 1783, 1806, 1829, 1852, 1875, 1898, 1921),
        ("TM", 5898): (*range(5899, 5910), *range(5912, 5923)),
        ("TM", 5909): (5910, 5911),
        ("TM", 1806): (
            *range(1807, 1813),
            5923,
            1813,
            1814,
            1815,
            5924,
            *range(1818, 1829),
        ),
        ("TM", 5924): (1816, 1817),
        ("TM", 1829): (
            *range(1830, 1836),
            5925,
            1836,
            1837,
            1838,
            5926,
            *range(1841, 1852),
        ),
        ("TM", 5926): (1839, 1840),
        ("TM", 1852): (
            *range(1853, 1859),
            5927,
            1859,
            1860,
            1861,
            5928,
            *range(1864, 1875),
        ),
        ("TM", 5928): (1862, 1863),
        ("TM", 1875): (
            *range(1876, 1882),
            5929,
            1882,
            1883,
            1884,
            5930,
            *range(1887, 1898),
        ),
        ("TM", 5930): (1885, 1886),
        ("TM", 1898): (
            *range(1899, 1905),
            5931,
            1905,
            1906,
            1907,
            5932,
            *range(1910, 1921),
        ),
        ("TM", 5932): (1908, 1909),
        ("TM", 1921): (
            *range(1922, 1928),
            5933,
            1928,
            1929,
            1930,
            5934,
            *range(1933, 1944),
        ),
        ("TM", 5934): (1931, 1932),
        ("TM", 5935): tuple(range(5936, 5946)),
    }
    for key, expected_children in exact_edges.items():
        if tuple(by_key[key].children) != expected_children:
            raise BusinessSchemaUpdateError(
                f"business-formula hierarchy children drift at {key}: "
                f"expected={expected_children}, actual={tuple(by_key[key].children)}"
            )
    for schema_id in (*TM_PAGE60_COMBINED_LOAN_IDS, *range(5936, 5946), 1944):
        item = by_key[("TM", schema_id)]
        if item.children:
            raise BusinessSchemaUpdateError(
                f"business-formula hierarchy leaf drift at TM/{schema_id}: {item.children}"
            )
    margin_final = by_key[("TM", 1944)]
    if margin_final.parent_id is not None or margin_final.display_order != TM_AFTER_ROW_COUNT - 2:
        raise BusinessSchemaUpdateError("TM 1944 parentless/workbook-last invariant drifted")
