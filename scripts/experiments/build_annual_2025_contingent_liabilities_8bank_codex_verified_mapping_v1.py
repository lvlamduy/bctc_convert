"""Verify annual-2025 contingent liabilities and commitments across eight banks."""

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

FORMAT_VERSION = "ANNUAL_2025_CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CONTINGENT_LIABILITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025cl8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CONTINGENT_LIABILITIES_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025cl8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "clfdsv1:scan:d7dc67dc7a6af40e51da636ff2bec3d862a62cb7132d83924dee75d38ea0ae85"
EXPECTED_RESULT_ID: str | None = (
    "annual2025cl8bcv1:result:7f195ee3dae399390fe1808f8379c0d135fb94873823bec5beaf7b650f5c5199"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_CONTINGENT_LIABILITY_GRAPH_VISIBLE_PDF_SOURCE_"
    "NUMERIC_CHALLENGER_EXACT_GROUP_CHILD_MARGIN_AND_NET_ACCOUNTING_"
    "CLOSURE_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_note_absence_is_not_source_wide_family_absence": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_contingent_liability_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_group_parent_forced_into_schema_sibling_equation": False,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 839),
    1294: ("Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra", 1259, 874),
    1295: ("Cam kết nghiệp vụ thư tín dụng (L/C)", 1294, 875),
    1296: ("Bảo lãnh vay vốn", 1294, 879),
    1297: ("Bảo lãnh thanh toán", 1294, 880),
    1298: ("Bảo lãnh thực hiện hợp đồng", 1294, 881),
    1299: ("Bảo lãnh dự thầu", 1294, 882),
    1300: ("Các bảo lãnh khác", 1294, 883),
    1301: ("Cam kết giao dịch hối đoái", 1294, 884),
    1302: ("Cam kết giao dịch hoán đổi", 1301, 887),
    1303: ("Hợp đồng mua bán giấy tờ có giá", 1294, 890),
    1304: ("Cam kết khác", 1294, 891),
    5741: ("Cam kết mua ngoại tệ", 1301, 885),
    5742: ("Cam kết bán ngoại tệ", 1301, 886),
    5743: ("Cam kết mua giao dịch hoán đổi tiền tệ", 1302, 888),
    5744: ("Cam kết bán giao dịch hoán đổi tiền tệ", 1302, 889),
}


class Annual2025ContingentLiabilities8BankError(ValueError):
    """The annual graph, pixels, values, equations or live schema drifted."""


def _error(message: str) -> Annual2025ContingentLiabilities8BankError:
    return Annual2025ContingentLiabilities8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_contingent_liabilities_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_contingent_liabilities_mapping_base_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual contingent-liabilities support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: tuple[int, str] | None = None,
    comparative: tuple[int, str] | None = None,
    *,
    topology: str = "FAMILY_ROW_WITH_TWO_ANNUAL_PERIOD_AXES",
) -> dict[str, Any]:
    return base._mapping(
        role,
        report_norm_id,
        page,
        labels,
        current,
        comparative,
        topology=topology,
    )


def _source_row(
    base: ModuleType,
    row_id: str,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: tuple[int, str],
    comparative: tuple[int, str],
    reason: str,
    *,
    open_mapping: bool,
) -> dict[str, Any]:
    return base._source_row(
        row_id,
        page,
        labels,
        current,
        comparative,
        reason,
        open_mapping=open_mapping,
    )


def _document(
    base: ModuleType,
    code: str,
    page: int,
    owner: Sequence[tuple[int, str]],
    mappings: Sequence[Mapping[str, Any]],
    source_only_rows: Sequence[Mapping[str, Any]],
    units: Sequence[tuple[int, str]],
    hierarchy: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": canonical_clone_v1(mappings),
        "owner": [base._ref(page, *item) for item in owner],
        "page_span": [page, page],
        "source_hierarchy_status": hierarchy,
        "source_only_rows": canonical_clone_v1(source_only_rows),
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, *item) for item in units],
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "financial_statement_summary_exists": True,
            "reason": (
                "The bound annual filing contains the family narrative but no value-bearing "
                "detailed table with a local owner, two periods, unit, children and numeric cells."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_hierarchy_status": "NOT_APPLICABLE_VALUE_BEARING_DETAILED_TABLE_ABSENT",
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    page = 75
    docs.append(
        _document(
            base,
            "ACB",
            page,
            [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1294,
                    page,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (51, "216.998.033"),
                    (52, "241.802.978"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_LOAN",
                    1296,
                    page,
                    [(12, "Bảo lãnh vay vốn")],
                    (13, "83.036"),
                    (14, "54.784"),
                ),
                _mapping(
                    base,
                    "FX_PARENT",
                    1301,
                    page,
                    [(15, "Cam kết giao dịch hối đoái")],
                    (16, "165.444.063"),
                    (17, "195.824.188"),
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT",
                    1295,
                    page,
                    [(18, "Cam kết trong nghiệp vụ L/C")],
                    (19, "6.666.479"),
                    (20, "3.311.773"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER_PARENT",
                    1300,
                    page,
                    [(30, "Bảo lãnh khác")],
                    (31, "19.772.573"),
                    (32, "14.262.824"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_PAYMENT",
                    1297,
                    page,
                    [(33, "Bảo lãnh thanh toán")],
                    (34, "5.171.273"),
                    (35, "3.815.908"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_PERFORMANCE",
                    1298,
                    page,
                    [(36, "Bảo lãnh thực hiện hợp đồng")],
                    (37, "3.622.525"),
                    (38, "2.867.362"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_BID",
                    1299,
                    page,
                    [(39, "Bảo lãnh dự thầu")],
                    (40, "633.343"),
                    (41, "895.491"),
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS",
                    1304,
                    page,
                    [(48, "Các cam kết khác")],
                    (49, "25.031.882"),
                    (50, "28.349.409"),
                ),
            ],
            [
                _source_row(
                    base,
                    "CL-001",
                    page,
                    [(21, "Cam kết trong nghiệp vụ L/C trả ngay")],
                    (22, "3.393.925"),
                    (23, "1.999.681"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_SIGHT_LC",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-002",
                    page,
                    [(24, "Cam kết trong nghiệp vụ L/C trả chậm")],
                    (25, "3.531.929"),
                    (26, "1.519.333"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_DEFERRED_LC",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-003",
                    page,
                    [(27, "Trừ: Tiền ký quỹ")],
                    (28, "(259.375)"),
                    (29, "(207.241)"),
                    "LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-004",
                    page,
                    [(42, "Bảo lãnh khác")],
                    (43, "11.804.589"),
                    (44, "7.752.095"),
                    "GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-005",
                    page,
                    [(45, "Trừ: Tiền ký quỹ")],
                    (46, "(1.459.157)"),
                    (47, "(1.068.032)"),
                    "GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
            ],
            [(10, "Triệu VND"), (11, "Triệu VND")],
            "SOURCE_GUARANTEE_PARENT_SPANS_SCHEMA_SIBLING_ROWS",
        )
    )

    page = 79
    docs.append(
        _document(
            base,
            "MBB",
            page,
            [(10, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
            [
                _mapping(
                    base,
                    "FAMILY_OWNER",
                    1294,
                    page,
                    [
                        (10, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA"),
                        (34, "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra chi tiết như sau:"),
                    ],
                    topology="STRUCTURAL_FAMILY_OWNER_NO_PRINTED_TOTAL",
                ),
                _mapping(
                    base,
                    "GUARANTEE_LOAN",
                    1296,
                    page,
                    [(39, "Bảo lãnh vay vốn")],
                    (40, "1.684.717"),
                    (41, "238.395"),
                ),
                _mapping(
                    base,
                    "FX_PARENT",
                    1301,
                    page,
                    [(42, "Cam kết giao dịch hối đoái")],
                    (43, "618.888.427"),
                    (44, "263.133.210"),
                ),
                _mapping(
                    base,
                    "FX_BUY",
                    5741,
                    page,
                    [(45, "Cam kết mua ngoại tệ")],
                    (46, "9.738.358"),
                    (47, "4.416.403"),
                ),
                _mapping(
                    base,
                    "FX_SELL",
                    5742,
                    page,
                    [(48, "Cam kết bán ngoại tệ")],
                    (49, "8.752.345"),
                    (50, "4.492.239"),
                ),
                _mapping(
                    base,
                    "SWAP_BUY",
                    5743,
                    page,
                    [(51, "Cam kết mua giao dịch hoán đổi ngoại tệ")],
                    (52, "299.830.234"),
                    (53, "127.747.604"),
                ),
                _mapping(
                    base,
                    "SWAP_SELL",
                    5744,
                    page,
                    [(54, "Cam kết bán giao dịch hoán đổi ngoại tệ")],
                    (55, "300.567.490"),
                    (56, "126.476.964"),
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT",
                    1295,
                    page,
                    [(57, "Cam kết trong nghiệp vụ L/C")],
                    (58, "59.728.018"),
                    (59, "29.138.440"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER",
                    1300,
                    page,
                    [(60, "Bảo lãnh khác")],
                    (61, "190.317.517"),
                    (62, "135.649.614"),
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS",
                    1304,
                    page,
                    [(63, "Các cam kết khác")],
                    (64, "127.878.633"),
                    (65, "72.142.229"),
                ),
            ],
            [],
            [(37, "triệu đồng"), (38, "triệu đồng")],
            "SOURCE_AND_SCHEMA_COMPATIBLE",
        )
    )

    page = 75
    docs.append(
        _document(
            base,
            "VPB",
            page,
            [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1294,
                    page,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (80, "1.050.492.773"),
                    (81, "690.753.389"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_LOAN",
                    1296,
                    page,
                    [(13, "Bảo lãnh vay vốn")],
                    (14, "11.447.240"),
                    (15, "848.721"),
                ),
                _mapping(
                    base,
                    "FX_PARENT",
                    1301,
                    page,
                    [(16, "Cam kết giao dịch hối đoái")],
                    (17, "545.548.779"),
                    (18, "300.000.752"),
                ),
                _mapping(
                    base,
                    "FX_BUY",
                    5741,
                    page,
                    [(19, "Cam kết mua ngoại tệ")],
                    (20, "6.965.590"),
                    (21, "2.972.620"),
                ),
                _mapping(
                    base,
                    "FX_SELL",
                    5742,
                    page,
                    [(22, "Cam kết bán ngoại tệ")],
                    (23, "9.281.743"),
                    (24, "1.955.905"),
                ),
                _mapping(
                    base,
                    "SWAP_BUY",
                    5743,
                    page,
                    [(25, "Cam kết nhận - giao dịch hoán đổi ngoại tệ")],
                    (26, "264.549.403"),
                    (27, "147.811.792"),
                ),
                _mapping(
                    base,
                    "SWAP_SELL",
                    5744,
                    page,
                    [(28, "Cam kết trả - giao dịch hoán đổi ngoại tệ")],
                    (29, "264.752.043"),
                    (30, "147.260.435"),
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT",
                    1295,
                    page,
                    [(31, "Cam kết trong nghiệp vụ L/C")],
                    (32, "19.751.533"),
                    (33, "16.461.049"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER_PARENT",
                    1300,
                    page,
                    [(40, "Bảo lãnh khác")],
                    (41, "50.911.375"),
                    (42, "26.008.227"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_PAYMENT",
                    1297,
                    page,
                    [(43, "Cam kết bảo lãnh thanh toán")],
                    (44, "10.240.060"),
                    (45, "6.945.197"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_PERFORMANCE",
                    1298,
                    page,
                    [(46, "Cam kết bảo lãnh thực hiện hợp đồng")],
                    (47, "15.709.314"),
                    (48, "9.331.348"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_BID",
                    1299,
                    page,
                    [(49, "Cam kết bảo lãnh dự thầu")],
                    (50, "1.060.042"),
                    (51, "470.492"),
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS",
                    1304,
                    page,
                    [(58, "Cam kết khác")],
                    (59, "422.833.846"),
                    (60, "347.434.640"),
                ),
                _mapping(
                    base,
                    "VALUABLE_PAPER_COMMITMENT",
                    1303,
                    page,
                    [(70, "Cam kết mua bán giấy tờ có giá")],
                    (71, "9.097.005"),
                    (72, "6.558.266"),
                ),
            ],
            [
                _source_row(
                    base,
                    "CL-006",
                    page,
                    [(34, "Cam kết trong nghiệp vụ L/C")],
                    (35, "20.139.278"),
                    (36, "16.518.381"),
                    "LC_GROSS_SOURCE_ROW_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-007",
                    page,
                    [(37, "Trừ: Tiền ký quỹ")],
                    (38, "(387.745)"),
                    (39, "(57.332)"),
                    "LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-008",
                    page,
                    [(52, "Cam kết bảo lãnh khác")],
                    (53, "25.861.416"),
                    (54, "9.932.865"),
                    "GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-009",
                    page,
                    [(55, "Trừ: Tiền ký quỹ")],
                    (56, "(1.959.457)"),
                    (57, "(671.675)"),
                    "GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-010",
                    page,
                    [(61, "Cam kết hoán đổi lãi suất tiền tệ chéo - nhận")],
                    (62, "46.229.090"),
                    (63, "35.324.065"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_CROSS_CURRENCY_SWAP_RECEIVE",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-011",
                    page,
                    [(64, "Cam kết hoán đổi lãi suất tiền tệ chéo - trả")],
                    (65, "46.716.751"),
                    (66, "36.760.922"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_CROSS_CURRENCY_SWAP_PAY",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-012",
                    page,
                    [(67, "Cam kết hoán đổi lãi suất một đồng tiền")],
                    (68, "24.343.737"),
                    (69, "39.136.588"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_SINGLE_CURRENCY_INTEREST_SWAP",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-013",
                    page,
                    [(73, "Cam kết khác")],
                    (74, "296.447.263"),
                    (75, "229.654.799"),
                    "SOURCE_CHILD_REPEATS_OTHER_COMMITMENT_PARENT_LABEL",
                    open_mapping=True,
                ),
                _source_row(
                    base,
                    "CL-014",
                    page,
                    [(76, "Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang")],
                    (78, "294.728.542"),
                    (79, "229.511.446"),
                    "NON_ADDITIVE_WITHIN_SUBSET_HAS_NO_SCHEMA_LEAF",
                    open_mapping=True,
                ),
            ],
            [(11, "Triệu đồng"), (12, "Triệu đồng")],
            "SOURCE_GROUP_PARENTS_SPAN_SCHEMA_SIBLING_ROWS",
        )
    )

    page = 55
    docs.append(
        _document(
            base,
            "HDB",
            page,
            [(46, "CÁC HOẠT ĐỘNG NGOẠI BẢNG MÀ NGÂN HÀNG PHẢI CHỊU RỦI RO ĐÁNG KỂ")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1294,
                    page,
                    [(46, "CÁC HOẠT ĐỘNG NGOẠI BẢNG MÀ NGÂN HÀNG PHẢI CHỊU RỦI RO ĐÁNG KỂ")],
                    (75, "228.449.964"),
                    (76, "283.712.933"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_LOAN",
                    1296,
                    page,
                    [(54, "Bảo lãnh vay vốn")],
                    (55, "10.235"),
                    (56, "808.743"),
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT",
                    1295,
                    page,
                    [(57, "Cam kết trong nghiệp vụ L/C")],
                    (58, "22.150.762"),
                    (59, "46.647.030"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER",
                    1300,
                    page,
                    [(60, "Bảo lãnh khác")],
                    (61, "22.036.535"),
                    (62, "25.173.809"),
                ),
                _mapping(
                    base,
                    "FX_PARENT",
                    1301,
                    page,
                    [(66, "Cam kết giao dịch hối đoái")],
                    (67, "175.879.380"),
                    (68, "199.138.079"),
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS",
                    1304,
                    page,
                    [(69, "Các cam kết khác")],
                    (70, "8.754.277"),
                    (71, "12.364.361"),
                ),
            ],
            [
                _source_row(
                    base,
                    "CLA-001",
                    page,
                    [(51, "Nghĩa vụ tiềm ẩn")],
                    (52, "44.197.532"),
                    (53, "72.629.582"),
                    "INTERMEDIATE_CONTINGENT_GROUP_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CLA-002",
                    page,
                    [(63, "Các cam kết đưa ra")],
                    (64, "184.633.657"),
                    (65, "211.502.440"),
                    "INTERMEDIATE_COMMITMENT_GROUP_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CLA-003",
                    page,
                    [(72, "Trừ: Tiền ký quỹ")],
                    (73, "(381.225)"),
                    (74, "(419.089)"),
                    "FAMILY_MARGIN_DEDUCTION_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
            ],
            [(49, "Triệu VND"), (50, "Triệu VND")],
            "SOURCE_TWO_INTERMEDIATE_GROUP_TOTALS_AND_MARGIN_RETAINED_AS_CONTROLS",
        )
    )

    docs.append(_absence("VCB"))

    page = 63
    docs.append(
        _document(
            base,
            "CTG",
            page,
            [(42, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1294,
                    page,
                    [(42, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT")],
                    (68, "1.210.667.481"),
                    (69, "1.057.593.605"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_LOAN",
                    1296,
                    page,
                    [(48, "Bảo lãnh vốn vay")],
                    (49, "28.630.320"),
                    (50, "15.390.290"),
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT",
                    1295,
                    page,
                    [(51, "Cam kết trong nghiệp vụ L/C")],
                    (52, "91.019.626"),
                    (53, "66.691.329"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER",
                    1300,
                    page,
                    [(54, "Bảo lãnh khác")],
                    (55, "147.475.860"),
                    (56, "108.170.999"),
                ),
                _mapping(
                    base,
                    "FX_PARENT",
                    1301,
                    page,
                    [(60, "Cam kết giao dịch hối đoái")],
                    (61, "860.422.276"),
                    (62, "804.229.724"),
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS",
                    1304,
                    page,
                    [(63, "Các cam kết khác")],
                    (64, "83.119.399"),
                    (65, "63.111.263"),
                ),
            ],
            [
                _source_row(
                    base,
                    "CL-015",
                    page,
                    [(47, "Nghĩa vụ tiềm ẩn")],
                    (57, "267.125.806"),
                    (58, "190.252.618"),
                    "INTERMEDIATE_CONTINGENT_GROUP_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-016",
                    page,
                    [(59, "Các cam kết đưa ra")],
                    (66, "943.541.675"),
                    (67, "867.340.987"),
                    "INTERMEDIATE_COMMITMENT_GROUP_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
            ],
            [(45, "Triệu đồng"), (46, "Triệu đồng")],
            "SOURCE_TWO_INTERMEDIATE_GROUP_TOTALS_RETAINED_AS_ACCOUNTING_CONTROLS",
        )
    )

    page = 59
    docs.append(
        _document(
            base,
            "BID",
            page,
            [(52, "CÁC CAM KẾT NGOẠI BẢNG")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1294,
                    page,
                    [(52, "CÁC CAM KẾT NGOẠI BẢNG")],
                    (82, "332.646.648"),
                    (83, "283.258.085"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_LOAN",
                    1296,
                    page,
                    [(62, "Bảo lãnh vay vốn")],
                    (63, "5.051.135"),
                    (64, "7.003.205"),
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER",
                    1300,
                    page,
                    [(65, "Bảo lãnh khác")],
                    (66, "246.978.045"),
                    (67, "199.424.464"),
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT",
                    1295,
                    page,
                    [(68, "Cam kết thanh toán")],
                    (69, "67.407.887"),
                    (70, "62.266.136"),
                    topology="SOURCE_PAYMENT_COMMITMENT_EQUALS_LC_SIGHT_PLUS_DEFERRED",
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS",
                    1304,
                    page,
                    [(78, "Các cam kết khác")],
                    (79, "13.209.581"),
                    (80, "14.564.280"),
                ),
            ],
            [
                _source_row(
                    base,
                    "CLA-004",
                    page,
                    [(59, "Các khoản bảo lãnh")],
                    (60, "252.029.180"),
                    (61, "206.427.669"),
                    "INTERMEDIATE_GUARANTEE_GROUP_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CLA-005",
                    page,
                    [(71, "Thư tín dụng trả ngay")],
                    (72, "16.385.872"),
                    (73, "22.098.147"),
                    "SIGHT_LC_IS_A_COMPONENT_OF_THE_MAPPED_PAYMENT_COMMITMENT",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CLA-006",
                    page,
                    [(74, "Thư tín dụng trả chậm")],
                    (75, "51.022.015"),
                    (76, "40.167.989"),
                    "DEFERRED_LC_IS_A_COMPONENT_OF_THE_MAPPED_PAYMENT_COMMITMENT",
                    open_mapping=False,
                ),
            ],
            [(57, "Triệu VND"), (58, "Triệu VND")],
            "SOURCE_GUARANTEE_AND_PAYMENT_GROUP_TOTALS_RETAINED_AS_CONTROLS",
        )
    )

    page = 55
    docs.append(
        _document(
            base,
            "VIB",
            page,
            [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL_NET",
                    1294,
                    page,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (76, "482.937.751"),
                    (79, "423.477.076"),
                    topology="FAMILY_NET_AFTER_MARGIN_WITH_MULTI_LANE_AXES",
                ),
                _mapping(
                    base,
                    "FX_PARENT_NET",
                    1301,
                    page,
                    [(27, "Cam kết giao dịch"), (28, "hối đoái")],
                    (30, "391.971.912"),
                    (32, "345.248.653"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
                _mapping(
                    base,
                    "FX_BUY_NET",
                    5741,
                    page,
                    [(33, "Cam kết mua"), (34, "ngoại tệ")],
                    (36, "8.575.398"),
                    (38, "9.093.526"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
                _mapping(
                    base,
                    "FX_SELL_NET",
                    5742,
                    page,
                    [(39, "Cam kết bán"), (40, "ngoại tệ")],
                    (42, "4.764.085"),
                    (44, "7.688.387"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
                _mapping(
                    base,
                    "SWAP_PARENT_NET",
                    1302,
                    page,
                    [(45, "Cam kết giao"), (46, "dịch hoán đổi"), (47, "tiền tệ")],
                    (49, "378.632.429"),
                    (51, "328.466.740"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
                _mapping(
                    base,
                    "LETTER_OF_CREDIT_NET",
                    1295,
                    page,
                    [(52, "Cam kết trong"), (53, "nghiệp vụ thư"), (54, "tín dụng")],
                    (57, "3.582.917"),
                    (60, "2.750.599"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
                _mapping(
                    base,
                    "GUARANTEE_OTHER_NET",
                    1300,
                    page,
                    [(61, "Bảo lãnh khác")],
                    (64, "13.836.912"),
                    (67, "7.185.571"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
                _mapping(
                    base,
                    "OTHER_COMMITMENTS_NET",
                    1304,
                    page,
                    [(68, "Các cam kết"), (73, "khác")],
                    (70, "73.546.010"),
                    (72, "68.292.253"),
                    topology="NET_LANE_ONLY_FROM_GROSS_MARGIN_NET_TABLE",
                ),
            ],
            [
                _source_row(
                    base,
                    "CL-017",
                    page,
                    [(52, "Cam kết trong nghiệp vụ thư tín dụng")],
                    (55, "3.615.224"),
                    (58, "2.773.012"),
                    "LC_GROSS_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-018",
                    page,
                    [(52, "Cam kết trong nghiệp vụ thư tín dụng")],
                    (56, "32.307"),
                    (59, "22.413"),
                    "LC_MARGIN_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-019",
                    page,
                    [(61, "Bảo lãnh khác")],
                    (62, "13.872.533"),
                    (65, "7.194.683"),
                    "GUARANTEE_GROSS_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-020",
                    page,
                    [(61, "Bảo lãnh khác")],
                    (63, "35.621"),
                    (66, "9.112"),
                    "GUARANTEE_MARGIN_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-021",
                    page,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (74, "483.005.679"),
                    (77, "423.508.601"),
                    "FAMILY_GROSS_IS_AN_ACCOUNTING_CONTROL",
                    open_mapping=False,
                ),
                _source_row(
                    base,
                    "CL-022",
                    page,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (75, "67.928"),
                    (78, "31.525"),
                    "TOTAL_MARGIN_IS_AN_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
            ],
            [(8, "triệu đồng"), (9, "triệu đồng")],
            "SOURCE_AND_SCHEMA_COMPATIBLE_WITH_GROSS_MARGIN_NET_AXES",
        )
    )

    expected = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
    if [item["bank_code"] for item in docs] != expected:
        raise _error("annual contingent-liabilities document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.FAMILY_END_DISPLAY_ORDER = 891
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
    base.ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT = False
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._review_documents = lambda: _review_documents(base)
    return base


def build_annual_2025_contingent_liabilities_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    try:
        return _base().build_live_contingent_liabilities_8bank_codex_verified_mapping_v1()
    except Annual2025ContingentLiabilities8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _base().validate_live_contingent_liabilities_8bank_codex_verified_mapping_v1(value)
    except Annual2025ContingentLiabilities8BankError:
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
            canonical_json_bytes_v1(
                build_annual_2025_contingent_liabilities_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        RESULT_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_live_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_v1()
            )
        )
        return 0
    value, _ = _base()._stable_json(RESULT_PATH)
    validate_annual_2025_contingent_liabilities_8bank_codex_verified_mapping_replay_v1(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
