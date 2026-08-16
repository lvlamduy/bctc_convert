"""Verify contingent liabilities and commitments across eight reports."""

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
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load contingent-liabilities support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_contingent_liabilities",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "contingent_liabilities_scan_for_verified_mapping",
    "scan_contingent_liabilities_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CONTINGENT_LIABILITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_CONTINGENT_"
    "LIABILITIES_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_CHALLENGER_EXACT_ACCOUNTING_"
    "CLOSURE_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "clfdsv1:scan:2a90b44582432ae9e0934b27986eb422cf22faba6cb0e1ec5d79006a58c021f5"

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 835),
    1294: ("Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra", 1259, 870),
    1295: ("Cam kết nghiệp vụ thư tín dụng (L/C)", 1294, 871),
    1296: ("Bảo lãnh vay vốn", 1294, 875),
    1297: ("Bảo lãnh thanh toán", 1294, 876),
    1298: ("Bảo lãnh thực hiện hợp đồng", 1294, 877),
    1299: ("Bảo lãnh dự thầu", 1294, 878),
    1300: ("Các bảo lãnh khác", 1294, 879),
    1301: ("Cam kết giao dịch hối đoái", 1294, 880),
    1302: ("Cam kết giao dịch hoán đổi", 1301, 883),
    1303: ("Hợp đồng mua bán giấy tờ có giá", 1294, 886),
    1304: ("Cam kết khác", 1294, 887),
    5741: ("Cam kết mua ngoại tệ", 1301, 881),
    5742: ("Cam kết bán ngoại tệ", 1301, 882),
    5743: ("Cam kết mua giao dịch hoán đổi tiền tệ", 1302, 884),
    5744: ("Cam kết bán giao dịch hoán đổi tiền tệ", 1302, 885),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_note_absence_is_not_source_wide_family_absence": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_contingent_liability_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_group_parent_forced_into_schema_sibling_equation": False,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "schema_family",
    "state",
    "trials",
}


class ContingentLiabilities8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, values, axes, schema or result drifted."""


def _error(message: str) -> ContingentLiabilities8BankCodexVerifiedMappingV1Error:
    return ContingentLiabilities8BankCodexVerifiedMappingV1Error(message)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or item.display_order != expected[2]
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _values(
    page: int, current: tuple[int, str], comparative: tuple[int, str]
) -> list[dict[str, Any]]:
    return [
        {"axis_role": "CURRENT", **_line(page, *current)},
        {"axis_role": "COMPARATIVE", **_line(page, *comparative)},
    ]


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: tuple[int, str] | None = None,
    comparative: tuple[int, str] | None = None,
    *,
    topology: str = "FAMILY_ROW_WITH_TWO_PERIOD_AXES",
) -> dict[str, Any]:
    if (current is None) != (comparative is None):
        raise _error("mapping axes must both be present or both absent")
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": [] if current is None else _values(page, current, comparative),
    }


def _source_row(
    row_id: str,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: tuple[int, str],
    comparative: tuple[int, str],
    reason: str,
    *,
    open_mapping: bool,
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "open_mapping": open_mapping,
        "reason": reason,
        "row_id": row_id,
        "values": _values(page, current, comparative),
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "financial_statement_summary_exists": True,
            "reason": (
                "The report contains the B02a off-balance-sheet summary but no detailed B05a "
                "contingent-liabilities note with a family owner, child depth or two explicit "
                "intermediate groups and accounting total."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_hierarchy_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        {
            "absence_evidence": None,
            "bank_code": "ACB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1294,
                    26,
                    [(31, "2. NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA:")],
                    (75, "277.059.307"),
                    (76, "216.998.033"),
                ),
                _mapping(
                    "GUARANTEE_LOAN",
                    1296,
                    26,
                    [(36, "Bảo lãnh vay vốn")],
                    (37, "72.692"),
                    (38, "83.036"),
                ),
                _mapping(
                    "FX_PARENT",
                    1301,
                    26,
                    [(39, "Cam kết giao dịch hối đoái")],
                    (40, "209.313.359"),
                    (41, "165.444.063"),
                ),
                _mapping(
                    "LETTER_OF_CREDIT",
                    1295,
                    26,
                    [(42, "Cam kết trong nghiệp vụ L/C")],
                    (43, "6.849.052"),
                    (44, "6.666.479"),
                ),
                _mapping(
                    "GUARANTEE_OTHER_PARENT",
                    1300,
                    26,
                    [(54, "Bảo lãnh khác")],
                    (55, "22.640.795"),
                    (56, "19.772.573"),
                ),
                _mapping(
                    "GUARANTEE_PAYMENT",
                    1297,
                    26,
                    [(57, "Bảo lãnh thanh toán")],
                    (58, "6.242.759"),
                    (59, "5.171.273"),
                ),
                _mapping(
                    "GUARANTEE_PERFORMANCE",
                    1298,
                    26,
                    [(60, "Bảo lãnh thực hiện hợp đồng")],
                    (61, "4.358.363"),
                    (62, "3.622.525"),
                ),
                _mapping(
                    "GUARANTEE_BID",
                    1299,
                    26,
                    [(63, "Bảo lãnh dự thầu")],
                    (64, "650.575"),
                    (65, "633.343"),
                ),
                _mapping(
                    "OTHER_COMMITMENTS",
                    1304,
                    26,
                    [(72, "Các cam kết khác")],
                    (73, "38.183.409"),
                    (74, "25.031.882"),
                ),
            ],
            "owner": [_ref(26, 31, "2. NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA:")],
            "page_span": [26, 26],
            "source_hierarchy_status": "SOURCE_GUARANTEE_PARENT_SPANS_SCHEMA_SIBLING_ROWS",
            "source_only_rows": [
                _source_row(
                    "CL-001",
                    26,
                    [(45, "Thư tín dụng trả ngay")],
                    (46, "2.908.946"),
                    (47, "3.393.925"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_SIGHT_LC",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-002",
                    26,
                    [(48, "Thư tín dụng trả chậm")],
                    (49, "4.229.592"),
                    (50, "3.531.929"),
                    "NO_DEDICATED_SCHEMA_LEAF_FOR_DEFERRED_LC",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-003",
                    26,
                    [(51, "Trừ: tiền ký quỹ")],
                    (52, "(289.486)"),
                    (53, "(259.375)"),
                    "LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-004",
                    26,
                    [(66, "Bảo lãnh khác")],
                    (67, "12.781.477"),
                    (68, "11.804.589"),
                    "GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-005",
                    26,
                    [(69, "Trừ: tiền ký quỹ")],
                    (70, "(1.392.379)"),
                    (71, "(1.459.157)"),
                    "GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(26, 34, "Triệu đồng"), _ref(26, 35, "Triệu đồng")],
        },
        {
            "absence_evidence": None,
            "bank_code": "MBB",
            "mappings": [
                _mapping(
                    "FAMILY_OWNER",
                    1294,
                    51,
                    [
                        (3, "Các cam kết ngoại bảng"),
                        (36, "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra"),
                    ],
                    topology="STRUCTURAL_FAMILY_OWNER_NO_PRINTED_TOTAL",
                ),
                _mapping(
                    "GUARANTEE_LOAN",
                    1296,
                    51,
                    [(9, "Bảo lãnh vay vốn")],
                    (10, "1.690.753"),
                    (11, "1.684.717"),
                ),
                _mapping(
                    "FX_PARENT",
                    1301,
                    51,
                    [(12, "Các cam kết giao dịch hối đoái")],
                    (13, "697.041.592"),
                    (14, "618.888.427"),
                ),
                _mapping(
                    "FX_BUY",
                    5741,
                    51,
                    [(15, "- Cam kết mua ngoại tệ")],
                    (16, "1.292.442"),
                    (17, "9.738.358"),
                ),
                _mapping(
                    "FX_SELL",
                    5742,
                    51,
                    [(18, "- Cam kết bán ngoại tệ")],
                    (19, "759.384"),
                    (20, "8.752.345"),
                ),
                _mapping(
                    "SWAP_BUY",
                    5743,
                    51,
                    [(21, "Cam kết mua giao dịch hoán đổi tiền tệ")],
                    (22, "346.687.448"),
                    (23, "299.830.234"),
                ),
                _mapping(
                    "SWAP_SELL",
                    5744,
                    51,
                    [(24, "- Cam kết bán giao dịch hoán đổi tiền tệ")],
                    (25, "348.302.318"),
                    (26, "300.567.490"),
                ),
                _mapping(
                    "LETTER_OF_CREDIT",
                    1295,
                    51,
                    [(27, "Cam kết trong nghiệp vụ LC")],
                    (28, "77.029.906"),
                    (29, "59.728.018"),
                ),
                _mapping(
                    "GUARANTEE_OTHER",
                    1300,
                    51,
                    [(30, "Bảo lãnh khác")],
                    (31, "208.475.133"),
                    (32, "190.317.517"),
                ),
                _mapping(
                    "OTHER_COMMITMENTS",
                    1304,
                    51,
                    [(33, "Cam kết khác")],
                    (34, "106.250.017"),
                    (35, "127.878.633"),
                ),
            ],
            "owner": [
                _ref(51, 3, "Các cam kết ngoại bảng"),
                _ref(51, 36, "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra"),
            ],
            "page_span": [51, 51],
            "source_hierarchy_status": "SOURCE_AND_SCHEMA_COMPATIBLE",
            "source_only_rows": [],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(51, 7, "Triệu đồng"), _ref(51, 8, "Triệu đồng")],
        },
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1294,
                    68,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (96, "973.264.004"),
                    (97, "1.050.492.773"),
                ),
                _mapping(
                    "GUARANTEE_LOAN",
                    1296,
                    68,
                    [(13, "Bảo lãnh vay vốn")],
                    (14, "11.447.240"),
                    (15, "11.447.240"),
                ),
                _mapping(
                    "FX_PARENT",
                    1301,
                    68,
                    [(16, "Cam kết giao dịch hối đoái")],
                    (17, "449.827.549"),
                    (18, "545.548.779"),
                ),
                _mapping(
                    "FX_BUY",
                    5741,
                    68,
                    [(20, "Cam kết mua ngoại tệ")],
                    (21, "2.130.153"),
                    (22, "6.965.590"),
                ),
                _mapping(
                    "FX_SELL",
                    5742,
                    68,
                    [(24, "Cam kết bán ngoại tệ")],
                    (25, "758.614"),
                    (26, "9.281.743"),
                ),
                _mapping(
                    "SWAP_BUY",
                    5743,
                    68,
                    [(28, "Cam kết nhận - giao dịch hoán đổi ngoại tệ")],
                    (29, "223.330.657"),
                    (30, "264.549.403"),
                ),
                _mapping(
                    "SWAP_SELL",
                    5744,
                    68,
                    [(32, "Cam kết trả - giao dịch hoán đổi ngoại tệ")],
                    (33, "223.608.125"),
                    (34, "264.752.043"),
                ),
                _mapping(
                    "LETTER_OF_CREDIT",
                    1295,
                    68,
                    [(35, "Cam kết trong nghiệp vụ L/C")],
                    (36, "21.894.766"),
                    (37, "19.751.533"),
                ),
                _mapping(
                    "GUARANTEE_OTHER_PARENT",
                    1300,
                    68,
                    [(46, "Bảo lãnh khác")],
                    (47, "47.666.649"),
                    (48, "50.911.375"),
                ),
                _mapping(
                    "GUARANTEE_PAYMENT",
                    1297,
                    68,
                    [(50, "Cam kết bảo lãnh thanh toán")],
                    (51, "10.042.188"),
                    (52, "10.240.060"),
                ),
                _mapping(
                    "GUARANTEE_PERFORMANCE",
                    1298,
                    68,
                    [(54, "Cam kết bảo lãnh thực hiện hợp đồng")],
                    (55, "10.572.150"),
                    (56, "15.709.314"),
                ),
                _mapping(
                    "GUARANTEE_BID",
                    1299,
                    68,
                    [(58, "Cam kết bảo lãnh dự thầu")],
                    (59, "1.210.167"),
                    (60, "1.060.042"),
                ),
                _mapping(
                    "OTHER_COMMITMENTS",
                    1304,
                    68,
                    [(69, "Cam kết khác")],
                    (70, "442.427.800"),
                    (71, "422.833.846"),
                ),
                _mapping(
                    "VALUABLE_PAPER_COMMITMENT",
                    1303,
                    68,
                    [(85, "Cam kết mua bán giấy tờ có giá")],
                    (86, "6.913.909"),
                    (87, "9.097.005"),
                ),
            ],
            "owner": [_ref(68, 5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
            "page_span": [68, 68],
            "source_hierarchy_status": "SOURCE_GROUP_PARENTS_SPAN_SCHEMA_SIBLING_ROWS",
            "source_only_rows": [
                _source_row(
                    "CL-006",
                    68,
                    [(39, "Cam kết trong nghiệp vụ L/C")],
                    (40, "22.114.007"),
                    (41, "20.139.278"),
                    "GROSS_LC_BEFORE_MARGIN_IS_A_CONTROL_NOT_THE_SCHEMA_NET_VALUE",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-007",
                    68,
                    [(43, "Trừ: Tiền ký quỹ")],
                    (44, "(219.241)"),
                    (45, "(387.745)"),
                    "LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-008",
                    68,
                    [(62, "Cam kết bảo lãnh khác")],
                    (63, "27.704.636"),
                    (64, "25.861.416"),
                    "GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-009",
                    68,
                    [(66, "Trừ: Tiền ký quỹ")],
                    (67, "(1.862.492)"),
                    (68, "(1.959.457)"),
                    "GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-010",
                    68,
                    [(73, "Cam kết hoán đổi lãi suất tiền tệ chéo - nhận")],
                    (74, "43.841.924"),
                    (75, "46.229.090"),
                    "NO_SCHEMA_LEAF_FOR_CROSS_CURRENCY_INTEREST_SWAP_RECEIVE_LEG",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-011",
                    68,
                    [(77, "Cam kết hoán đổi lãi suất tiền tệ chéo - trả")],
                    (78, "44.290.156"),
                    (79, "46.716.751"),
                    "NO_SCHEMA_LEAF_FOR_CROSS_CURRENCY_INTEREST_SWAP_PAY_LEG",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-012",
                    68,
                    [(81, "Cam kết hoán đổi lãi suất một đồng tiền")],
                    (82, "23.725.463"),
                    (83, "24.343.737"),
                    "NO_SCHEMA_LEAF_FOR_SINGLE_CURRENCY_INTEREST_SWAP",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-013",
                    68,
                    [(89, "Cam kết khác")],
                    (90, "323.656.348"),
                    (91, "296.447.263"),
                    "GRANULAR_OTHER_COMMITMENT_REPEATS_ITS_GROUP_PARENT_LABEL",
                    open_mapping=True,
                ),
                _source_row(
                    "CL-014",
                    68,
                    [(92, "Trong đó: hạn mức tín dụng chưa sử dụng có thể"), (93, "hủy ngang")],
                    (94, "317.838.201"),
                    (95, "294.728.542"),
                    "IN_THAT_UNUSED_CANCELLABLE_LIMIT_IS_NON_ADDITIVE_AND_HAS_NO_DEDICATED_SCHEMA_LEAF",
                    open_mapping=True,
                ),
            ],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(68, 11, "Triệu đồng"), _ref(68, 12, "Triệu đồng")],
        },
        _absence("HDB"),
        _absence("VCB"),
        {
            "absence_evidence": None,
            "bank_code": "CTG",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1294,
                    48,
                    [
                        (4, "21. CÁC HOẠT ĐỘNG NGOẠI BẢNG KHÁC MÀ TCTD PHẢI CHỊU RỦI RO ĐÁNG"),
                        (5, "KỂ (TRỌNG YẾU)"),
                    ],
                    (32, "1.339.705.266"),
                    (33, "1.210.667.481"),
                ),
                _mapping(
                    "GUARANTEE_LOAN",
                    1296,
                    48,
                    [(13, "Cam kết bảo lãnh vay vốn")],
                    (14, "36.255.058"),
                    (15, "28.630.320"),
                ),
                _mapping(
                    "LETTER_OF_CREDIT",
                    1295,
                    48,
                    [(16, "Cam kết trong nghiệp vụ L/C")],
                    (17, "104.889.002"),
                    (18, "91.019.626"),
                ),
                _mapping(
                    "GUARANTEE_OTHER",
                    1300,
                    48,
                    [
                        (19, "Cam kết bảo lãnh khác (thanh toán, thực"),
                        (22, "hiện hợp đồng, dự thầu, khác)"),
                    ],
                    (20, "155.889.602"),
                    (21, "147.475.860"),
                ),
                _mapping(
                    "FX_PARENT",
                    1301,
                    48,
                    [(26, "Cam kết giao dịch hối đoái")],
                    (27, "953.123.645"),
                    (28, "860.422.276"),
                ),
                _mapping(
                    "OTHER_COMMITMENTS",
                    1304,
                    48,
                    [(29, "Cam kết khác")],
                    (30, "89.547.959"),
                    (31, "83.119.399"),
                ),
            ],
            "owner": [
                _ref(48, 4, "21. CÁC HOẠT ĐỘNG NGOẠI BẢNG KHÁC MÀ TCTD PHẢI CHỊU RỦI RO ĐÁNG"),
                _ref(48, 5, "KỂ (TRỌNG YẾU)"),
            ],
            "page_span": [48, 48],
            "source_hierarchy_status": "SOURCE_TWO_INTERMEDIATE_GROUP_TOTALS_RETAINED_AS_ACCOUNTING_CONTROLS",
            "source_only_rows": [
                _source_row(
                    "CL-015",
                    48,
                    [(10, "Nghĩa vụ nợ tiềm ẩn")],
                    (11, "297.033.662"),
                    (12, "267.125.806"),
                    "SOURCE_INTERMEDIATE_GROUP_TOTAL_WITHOUT_DEDICATED_SCHEMA_ID",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-016",
                    48,
                    [(23, "Các cam kết đưa ra")],
                    (24, "1.042.671.604"),
                    (25, "943.541.675"),
                    "SOURCE_INTERMEDIATE_GROUP_TOTAL_WITHOUT_DEDICATED_SCHEMA_ID",
                    open_mapping=False,
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(48, 8, "triệu đồng"), _ref(48, 9, "triệu đồng")],
        },
        _absence("BID"),
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL_NET",
                    1294,
                    50,
                    [(5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
                    (72, "486.056.309"),
                    (75, "482.937.751"),
                    topology="GROSS_MINUS_MARGIN_EQUALS_NET_SCHEMA_VALUE",
                ),
                _mapping(
                    "FX_PARENT_NET",
                    1301,
                    50,
                    [(25, "Cam kết giao dịch"), (26, "hối đoái")],
                    (28, "382.318.306"),
                    (30, "391.971.912"),
                ),
                _mapping(
                    "FX_BUY_NET",
                    5741,
                    50,
                    [(31, "- Cam kết mua ngoại"), (32, "tệ")],
                    (34, "14.475.337"),
                    (36, "8.575.398"),
                ),
                _mapping(
                    "FX_SELL_NET",
                    5742,
                    50,
                    [(37, "Cam kết bán ngoại"), (38, "tệ")],
                    (40, "13.572.833"),
                    (42, "4.764.085"),
                ),
                _mapping(
                    "SWAP_PARENT_NET",
                    1302,
                    50,
                    [(43, "Cam kết giao dịch"), (44, "hoán đổi tiền tệ")],
                    (46, "354.270.136"),
                    (48, "378.632.429"),
                ),
                _mapping(
                    "LETTER_OF_CREDIT_NET",
                    1295,
                    50,
                    [(49, "Cam kết trong"), (50, "nghiệp vụ thư tín"), (51, "dụng")],
                    (54, "3.828.527"),
                    (57, "3.582.917"),
                    topology="GROSS_MINUS_MARGIN_EQUALS_NET_SCHEMA_VALUE",
                ),
                _mapping(
                    "GUARANTEE_OTHER_NET",
                    1300,
                    50,
                    [(58, "Bảo lãnh khác")],
                    (61, "15.873.012"),
                    (64, "13.836.912"),
                    topology="GROSS_MINUS_MARGIN_EQUALS_NET_SCHEMA_VALUE",
                ),
                _mapping(
                    "OTHER_COMMITMENTS_NET",
                    1304,
                    50,
                    [(65, "Các cam kết khác")],
                    (67, "84.036.464"),
                    (69, "73.546.010"),
                ),
            ],
            "owner": [_ref(50, 5, "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT ĐƯA RA")],
            "page_span": [50, 50],
            "source_hierarchy_status": "SOURCE_AND_SCHEMA_COMPATIBLE_WITH_GROSS_MARGIN_NET_AXES",
            "source_only_rows": [
                _source_row(
                    "CL-017",
                    50,
                    [(49, "Cam kết trong"), (50, "nghiệp vụ thư tín"), (51, "dụng")],
                    (52, "3.862.479"),
                    (55, "3.615.224"),
                    "GROSS_LC_IS_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-018",
                    50,
                    [(19, "Tiền gửi ký quỹ")],
                    (53, "33.952"),
                    (56, "32.307"),
                    "LC_MARGIN_IS_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-019",
                    50,
                    [(58, "Bảo lãnh khác")],
                    (59, "15.899.970"),
                    (62, "13.872.533"),
                    "GROSS_GUARANTEE_IS_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-020",
                    50,
                    [(19, "Tiền gửi ký quỹ")],
                    (60, "26.958"),
                    (63, "35.621"),
                    "GUARANTEE_MARGIN_IS_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-021",
                    50,
                    [(18, "Giá trị theo hợp đồng gộp")],
                    (70, "486.117.219"),
                    (73, "483.005.679"),
                    "GROSS_FAMILY_TOTAL_IS_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
                _source_row(
                    "CL-022",
                    50,
                    [(19, "Tiền gửi ký quỹ")],
                    (71, "60.910"),
                    (74, "67.928"),
                    "TOTAL_MARGIN_IS_ACCOUNTING_CONTROL_FOR_NET_SCHEMA_VALUE",
                    open_mapping=False,
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(50, 8, "triệu đồng"), _ref(50, 9, "triệu đồng")],
        },
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": "CONTINGENT_LIABILITIES_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0098:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("contingent-liabilities pixel review drifted")
    return canonical_clone_v1(value)


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "bound_report_detailed_note_absence_count": sum(
            t["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(t["page_span"] is not None for t in trials),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(
            sum(r["open_mapping"] for r in t["verified_source_only_rows"]) for t in trials
        ),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "source_only_control_row_count": sum(
            sum(not r["open_mapping"] for r in t["verified_source_only_rows"]) for t in trials
        ),
        "verified_value_cell_count": sum(
            len(m["values"]) for t in trials for m in t["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("contingent-liabilities result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("contingent-liabilities result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0098:result:" + canonical_json_sha256_v1(material):
        raise _error("contingent-liabilities result ID drifted")
    return canonical_clone_v1(value)


def _value(row: Mapping[str, Any], axis_role: str) -> int:
    return next(
        item["normalized_value"] for item in row["values"] if item["axis_role"] == axis_role
    )


def _equation(name: str, axis: str, computed: int, visible: int) -> dict[str, Any]:
    if computed != visible:
        raise _error(f"accounting equation does not close: {name}/{axis}")
    return {
        "computed_value": computed,
        "name": name,
        "period_axis": axis,
        "status": "VERIFIED_EXACT",
        "visible_value": visible,
    }


def build_contingent_liabilities_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_contingent_liabilities_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if (
        axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or structure_scan["scan_id"] != EXPECTED_SCAN_ID
    ):
        raise _error("contingent-liabilities fixed inputs drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = other._document(reviewed_documents, code, "pixel review")
        scan_trial = other._document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "structure_graph_id": matcher["result_id"],
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["regions"]:
                raise _error("absent detailed contingent-liabilities note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "source_hierarchy_status": reviewed["source_hierarchy_status"],
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "status": "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed contingent-liabilities region is not unique")
        axis_document = other._document(axis["documents"], code, "accounting axis")
        semantic_document = other._document(semantic_index["documents"], code, "semantic index")
        crop_document = other._document(crop_manifest["documents"], code, "crop manifest")

        def verified_values(
            items: Sequence[Mapping[str, Any]],
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "axis_role": item["axis_role"],
                    **other._verified_value(axis_document, semantic_document, crop_document, item),
                }
                for item in items
            ]

        mappings = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX"
                if mapping["values"]
                else "VERIFIED_BY_CODEX_STRUCTURAL_ONLY",
                "topology": mapping["topology"],
                "values": verified_values(mapping["values"]),
            }
            for mapping in reviewed["mappings"]
        ]
        source_only = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in row["labels"]
                ],
                "open_mapping": row["open_mapping"],
                "reason": row["reason"],
                "row_id": row["row_id"],
                "status": "OPEN_UNRESOLVED_SCHEMA_MAPPING"
                if row["open_mapping"]
                else "VERIFIED_SOURCE_ONLY_ACCOUNTING_CONTROL",
                "values": verified_values(row["values"]),
            }
            for row in reviewed["source_only_rows"]
        ]
        by_role = {m["role"]: m for m in mappings}
        by_row = {r["row_id"]: r for r in source_only}
        equations = []
        for period in ("CURRENT", "COMPARATIVE"):
            if code == "ACB":
                equations.extend(
                    [
                        _equation(
                            "LC_SIGHT_PLUS_DEFERRED_MINUS_MARGIN_EQUALS_LC_NET",
                            period,
                            _value(by_row["CL-001"], period)
                            + _value(by_row["CL-002"], period)
                            + _value(by_row["CL-003"], period),
                            _value(by_role["LETTER_OF_CREDIT"], period),
                        ),
                        _equation(
                            "PAYMENT_PLUS_PERFORMANCE_PLUS_BID_PLUS_OTHER_MINUS_MARGIN_EQUALS_OTHER_GUARANTEE",
                            period,
                            _value(by_role["GUARANTEE_PAYMENT"], period)
                            + _value(by_role["GUARANTEE_PERFORMANCE"], period)
                            + _value(by_role["GUARANTEE_BID"], period)
                            + _value(by_row["CL-004"], period)
                            + _value(by_row["CL-005"], period),
                            _value(by_role["GUARANTEE_OTHER_PARENT"], period),
                        ),
                        _equation(
                            "FIVE_PRIMARY_BRANCHES_EQUAL_FAMILY_TOTAL",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in (
                                    "GUARANTEE_LOAN",
                                    "FX_PARENT",
                                    "LETTER_OF_CREDIT",
                                    "GUARANTEE_OTHER_PARENT",
                                    "OTHER_COMMITMENTS",
                                )
                            ),
                            _value(by_role["FAMILY_TOTAL"], period),
                        ),
                    ]
                )
            elif code == "MBB":
                equations.append(
                    _equation(
                        "FOUR_FX_LEGS_EQUAL_FX_PARENT",
                        period,
                        sum(
                            _value(by_role[r], period)
                            for r in ("FX_BUY", "FX_SELL", "SWAP_BUY", "SWAP_SELL")
                        ),
                        _value(by_role["FX_PARENT"], period),
                    )
                )
            elif code == "VPB":
                equations.extend(
                    [
                        _equation(
                            "FOUR_FX_LEGS_EQUAL_FX_PARENT",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in ("FX_BUY", "FX_SELL", "SWAP_BUY", "SWAP_SELL")
                            ),
                            _value(by_role["FX_PARENT"], period),
                        ),
                        _equation(
                            "LC_GROSS_MINUS_MARGIN_EQUALS_LC_NET",
                            period,
                            _value(by_row["CL-006"], period) + _value(by_row["CL-007"], period),
                            _value(by_role["LETTER_OF_CREDIT"], period),
                        ),
                        _equation(
                            "GUARANTEE_CHILDREN_MINUS_MARGIN_EQUAL_GUARANTEE_PARENT",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in (
                                    "GUARANTEE_PAYMENT",
                                    "GUARANTEE_PERFORMANCE",
                                    "GUARANTEE_BID",
                                )
                            )
                            + _value(by_row["CL-008"], period)
                            + _value(by_row["CL-009"], period),
                            _value(by_role["GUARANTEE_OTHER_PARENT"], period),
                        ),
                        _equation(
                            "OTHER_COMMITMENT_CHILDREN_EQUAL_OTHER_COMMITMENT_PARENT",
                            period,
                            sum(
                                _value(by_row[r], period)
                                for r in ("CL-010", "CL-011", "CL-012", "CL-013")
                            )
                            + _value(by_role["VALUABLE_PAPER_COMMITMENT"], period),
                            _value(by_role["OTHER_COMMITMENTS"], period),
                        ),
                        _equation(
                            "FIVE_PRIMARY_BRANCHES_EQUAL_FAMILY_TOTAL",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in (
                                    "GUARANTEE_LOAN",
                                    "FX_PARENT",
                                    "LETTER_OF_CREDIT",
                                    "GUARANTEE_OTHER_PARENT",
                                    "OTHER_COMMITMENTS",
                                )
                            ),
                            _value(by_role["FAMILY_TOTAL"], period),
                        ),
                    ]
                )
            elif code == "CTG":
                equations.extend(
                    [
                        _equation(
                            "CONTINGENT_GROUP_EQUALS_THREE_CHILDREN",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in ("GUARANTEE_LOAN", "LETTER_OF_CREDIT", "GUARANTEE_OTHER")
                            ),
                            _value(by_row["CL-015"], period),
                        ),
                        _equation(
                            "COMMITMENT_GROUP_EQUALS_TWO_CHILDREN",
                            period,
                            _value(by_role["FX_PARENT"], period)
                            + _value(by_role["OTHER_COMMITMENTS"], period),
                            _value(by_row["CL-016"], period),
                        ),
                        _equation(
                            "TWO_INTERMEDIATE_GROUPS_EQUAL_FAMILY_TOTAL",
                            period,
                            _value(by_row["CL-015"], period) + _value(by_row["CL-016"], period),
                            _value(by_role["FAMILY_TOTAL"], period),
                        ),
                    ]
                )
            elif code == "VIB":
                equations.extend(
                    [
                        _equation(
                            "FX_BUY_PLUS_SELL_PLUS_SWAP_EQUALS_FX_PARENT",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in ("FX_BUY_NET", "FX_SELL_NET", "SWAP_PARENT_NET")
                            ),
                            _value(by_role["FX_PARENT_NET"], period),
                        ),
                        _equation(
                            "LC_GROSS_MINUS_MARGIN_EQUALS_LC_NET",
                            period,
                            _value(by_row["CL-017"], period) - _value(by_row["CL-018"], period),
                            _value(by_role["LETTER_OF_CREDIT_NET"], period),
                        ),
                        _equation(
                            "GUARANTEE_GROSS_MINUS_MARGIN_EQUALS_GUARANTEE_NET",
                            period,
                            _value(by_row["CL-019"], period) - _value(by_row["CL-020"], period),
                            _value(by_role["GUARANTEE_OTHER_NET"], period),
                        ),
                        _equation(
                            "FAMILY_GROSS_MINUS_MARGIN_EQUALS_FAMILY_NET",
                            period,
                            _value(by_row["CL-021"], period) - _value(by_row["CL-022"], period),
                            _value(by_role["FAMILY_TOTAL_NET"], period),
                        ),
                        _equation(
                            "FOUR_NET_BRANCHES_EQUAL_FAMILY_NET",
                            period,
                            sum(
                                _value(by_role[r], period)
                                for r in (
                                    "FX_PARENT_NET",
                                    "LETTER_OF_CREDIT_NET",
                                    "GUARANTEE_OTHER_NET",
                                    "OTHER_COMMITMENTS_NET",
                                )
                            ),
                            _value(by_role["FAMILY_TOTAL_NET"], period),
                        ),
                    ]
                )
        period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        has_open = any(row["open_mapping"] for row in source_only)
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(
                    {m["schema_binding"]["report_norm_id"] for m in mappings}
                ),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "source_hierarchy_status": reviewed["source_hierarchy_status"],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS"
                if has_open
                else "VERIFIED_BY_CODEX",
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
            }
        )
    mapped_union = sorted(
        {m["schema_binding"]["report_norm_id"] for t in trials for m in t["verified_mappings"]}
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": 887,
            "family_root": _schema_binding(schema_by_id.get(1294), 1294),
            "mapped_report_norm_ids": mapped_union,
            "section_root": _schema_binding(schema_by_id.get(1259), 1259),
        },
        "state": "CONTINGENT_LIABILITIES_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0098:result:" + canonical_json_sha256_v1(material)}
    )


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    support = scanner._support()._support()
    raw = support._stable_bytes(path)
    return support._strict_json(raw, path.as_posix()), hashlib.sha256(raw).hexdigest()


def _live_inputs() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256 or crop_sha != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("contingent-liabilities fixed input hash drifted")
    scan = scanner.build_contingent_liabilities_full_document_scan_v1(semantic_index)
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, (name, parent, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or item.display_order != display_order
            or item.statement_type != "TM"
        ):
            raise _error(f"contingent-liabilities live schema drifted: {report_norm_id}")
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": authority,
        "schema_by_id": by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_contingent_liabilities_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_contingent_liabilities_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_contingent_liabilities_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_contingent_liabilities_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("contingent-liabilities result does not replay exactly")
    return supplied


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        _write(REVIEW_PATH, _review_blueprint())
    if args.write_result:
        _write(RESULT_PATH, build_live_contingent_liabilities_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_contingent_liabilities_8bank_codex_verified_mapping_v1(value)


if __name__ == "__main__":
    main()
