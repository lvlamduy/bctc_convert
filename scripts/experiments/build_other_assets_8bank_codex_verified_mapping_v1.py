"""Verify the eight-bank ``Tài sản Có khác`` family without bank routing."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
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


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_module(
    "trading_securities_support_for_other_assets",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "other_assets_scan_for_verified_mapping",
    "scan_other_assets_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "OTHER_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "OTHER_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
_RESULT_STATE = "OTHER_ASSETS_8BANK_CODEX_VERIFICATION_COMPLETE"
_RESULT_ID_PREFIX = "e0073:result:"
_REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0073:pixel-review:"
_REVIEW_RUN_ID = "E-0073"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_OTHER_ASSETS_"
    "VARIANT_GRAPH_VISIBLE_PDF_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_PERIOD_UNIT_"
    "ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_UNMAPPED_SOURCE_ROWS_RETAINED_NO_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "oafdsv1:scan:55c29177ffccafd01e69c463bbb0d1653dcf418f4ae75e627c421a6f9b0c21df"

_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION_OR_BOUND_REPORT_ABSENCE",
    "OWNER_PARENT_CHILD_AND_SIBLING_TOPOLOGY",
    "SPLIT_UMBRELLA_CONTINUATION_AND_SUBTABLE_VARIANTS",
    "CURRENT_AND_COMPARATIVE_PERIOD_AXES",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "OPTIONAL_CHILDREN_NOT_REQUIRED_FOR_REGION_LOCATION",
    "PARENT_CHILD_SUBTOTAL_AND_ROLLFORWARD_ACCOUNTING",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
    "UNMAPPED_SOURCE_ROWS_RETAINED_WITHOUT_FORCED_EQUIVALENCE",
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER",
    "old_ocr_used_as_semantic_anchor": False,
    "optional_children_required_in_every_bank": False,
    "source_rows_without_equivalent_schema_forced_into_nearest_item": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_other_asset_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
    "upstream_ppocrv6_or_native_text_used_only_as_numeric_challenger": True,
}
_RESULT_FIELDS = {
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
_SCHEMA_EXPECTED = {
    966: ("Tài sản Có khác", 560),
    967: ("Các khoản phải thu", 966),
    970: ("Các khoản phải thu nội bộ", 967),
    971: ("Các khoản phải thu bên ngoài", 967),
    972: ("+Trả trước cho người bán", 967),
    973: ("+Các khoản kỹ quỹ, bão lãnh, thế chấp, đặt cọc", 967),
    975: ("+Tạm ứng", 967),
    981: ("+Phải thu khác", 967),
    982: ("Các khoản lãi phí phải thu", 966),
    983: ("Từ cho vay khách hàng", 982),
    984: ("Từ tiền gửi và cho vay các tổ chức tín dụng khác", 982),
    985: ("Từ giao dịch phái sinh", 982),
    986: ("Từ các nguồn khác", 982),
    987: ("Tài sản Có khác (mục con)", 966),
    989: ("-Chi phí chờ phân bổ", 987),
    990: ("-Vật liệu, công cụ lao động", 987),
    993: ("-Tài sản gán nợ chờ xử lý", 987),
    994: ("+Bất động sản", 987),
    997: ("Tài sản khác", 987),
    999: ("-Tổng giá trị Lợi thế thương mại (LTTM)", 998),
    1000: ("-Thời gian phân bổ (năm)", 998),
    1001: ("-Giá trị LTTM đã phân bổ lũy kế đầu kỳ", 998),
    1002: ("-Giá trị LTTM chưa phân bổ đầu kỳ", 998),
    1006: ("-Lợi thế thương mại giảm trong kỳ", 998),
    1008: ("+Giá trị LTTM phân bổ trong kỳ", 998),
    1010: ("Tổng giá trị Lợi thế thương mại chưa phân bổ cuối kỳ", 998),
    1018: (
        "Phân tích chất lượng tài sản có khác được phân loại là tài sản có rủi ro tín dụng",
        966,
    ),
    1019: ("+ Nhóm 1: Nợ đủ tiêu chuẩn", 1018),
    1023: ("+ Nhóm 5: Nợ có khả năng mất vốn", 1018),
    5975: ("Phải thu liên quan đến dịch vụ thanh toán", 967),
    5976: ("Phải thu miễn truy đòi theo bộ chứng từ", 967),
    6007: ("Chi phí xây dựng cơ bản, mua sắm TSCĐ", 967),
}

_BOUNDARIES = {
    "ACB": (
        (19, 59, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (20, 4, "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC"),
    ),
    "HDB": ((30, 7, "Góp vốn, đầu tư dài hạn"), (30, 56, "Các khoản nợ Chính phủ và NHNN")),
    "VCB": (
        (33, 9, "Góp vốn đầu tư dài hạn"),
        (34, 8, "Các khoản nợ Chính Phủ và Ngân hàng Nhà nước"),
    ),
    "CTG": ((40, 66, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"), (41, 7, "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN")),
    "BID": (
        (24, 5, "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (24, 88, "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG"),
    ),
}


class OtherAssets8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel, numeric, accounting or schema evidence drifted."""


def _error(message: str) -> OtherAssets8BankCodexVerifiedMappingV1Error:
    return OtherAssets8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str, multiplier: int = 1) -> dict[str, Any]:
    return {
        "line_index": line,
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _mapping(
    report_norm_id: int,
    role: str,
    labels: Sequence[dict[str, Any]],
    current: Sequence[dict[str, Any]],
    comparative: Sequence[dict[str, Any]],
    topology: str,
) -> dict[str, Any]:
    return {
        "labels": list(labels),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE": list(comparative), "CURRENT": list(current)},
    }


def _direct(
    report_norm_id: int,
    role: str,
    page: int,
    label_line: int,
    label_text: str,
    current: tuple[int, str],
    comparative: tuple[int, str],
    topology: str = "OWNER_DESCENDANT",
) -> dict[str, Any]:
    return _mapping(
        report_norm_id,
        role,
        [_label(page, label_line, label_text)],
        [_ref(page, *current)],
        [_ref(page, *comparative)],
        topology,
    )


def _equation(
    name: str,
    period_role: str,
    terms: Sequence[dict[str, Any]],
    total: dict[str, Any],
) -> dict[str, Any]:
    return {"name": name, "period_role": period_role, "terms": list(terms), "total": total}


def _unmapped(
    item_id: str,
    page: int,
    label_line: int,
    label_text: str,
    current: tuple[int, str],
    comparative: tuple[int, str],
    reason: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "label": _label(page, label_line, label_text),
        "reason": reason,
        "status": "UNRESOLVED",
        "values": {
            "COMPARATIVE": [_ref(page, *comparative)],
            "CURRENT": [_ref(page, *current)],
        },
    }


def _mbb_review() -> dict[str, Any]:
    mappings = [
        _direct(
            967, "RECEIVABLES", 42, 1, "Các khoản phải thu", (12, "25.431.187"), (13, "28.125.764")
        ),
        _direct(
            970,
            "INTERNAL_RECEIVABLES",
            42,
            6,
            "Các khoản phải thu nội bộ",
            (7, "518.828"),
            (8, "359.532"),
        ),
        _direct(
            971,
            "EXTERNAL_RECEIVABLES",
            42,
            9,
            "Các khoản phải thu bên ngoài",
            (10, "24.912.359"),
            (11, "27.766.232"),
        ),
        _direct(
            6007,
            "CAPEX_RECEIVABLE",
            42,
            19,
            "Chi phí xây dựng cơ bản, mua sắm TSCĐ",
            (20, "1.088.365"),
            (21, "1.039.654"),
        ),
        _direct(
            973,
            "DEPOSITS_COLLATERAL",
            42,
            22,
            "Ký quỹ, thế chấp, cầm cố",
            (23, "774.639"),
            (24, "891.504"),
        ),
        _direct(
            5975,
            "PAYMENT_SERVICE_RECEIVABLE",
            42,
            25,
            "Phải thu liên quan đến dịch vụ thanh toán",
            (26, "1.485.682"),
            (27, "1.525.624"),
        ),
        _direct(
            5976,
            "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE",
            42,
            28,
            "Phải thu miễn truy đòi theo bộ chứng từ",
            (29, "16.175.613"),
            (30, "8.046.079"),
        ),
        _direct(
            981,
            "OTHER_RECEIVABLE",
            42,
            31,
            "Các khoản phải thu khác",
            (32, "5.388.060"),
            (33, "16.263.371"),
        ),
        _direct(
            987,
            "OTHER_ASSET_BRANCH",
            42,
            37,
            "Tài sản Có khác",
            (48, "8.297.454"),
            (49, "7.894.091"),
            "SPLIT_SIBLING_NOTE_TOTAL",
        ),
        _direct(
            989, "PREPAID_COST", 42, 42, "Chi phí chờ phân bổ", (43, "4.850.194"), (44, "3.478.007")
        ),
        _direct(997, "OTHER_ASSET", 42, 45, "Các khoản khác", (46, "3.447.260"), (47, "4.416.084")),
    ]
    equations = []
    for period, left, right, total in (
        ("CURRENT", (7, "518.828"), (10, "24.912.359"), (12, "25.431.187")),
        ("COMPARATIVE", (8, "359.532"), (11, "27.766.232"), (13, "28.125.764")),
    ):
        equations.append(
            _equation(
                "INTERNAL_PLUS_EXTERNAL_TO_RECEIVABLES",
                period,
                [_ref(42, *left), _ref(42, *right)],
                _ref(42, *total),
            )
        )
    for period, components, total in (
        (
            "CURRENT",
            [
                (20, "1.088.365"),
                (23, "774.639"),
                (26, "1.485.682"),
                (29, "16.175.613"),
                (32, "5.388.060"),
            ],
            (34, "24.912.359"),
        ),
        (
            "COMPARATIVE",
            [
                (21, "1.039.654"),
                (24, "891.504"),
                (27, "1.525.624"),
                (30, "8.046.079"),
                (33, "16.263.371"),
            ],
            (35, "27.766.232"),
        ),
    ):
        equations.append(
            _equation(
                "EXTERNAL_DETAIL_TO_EXTERNAL_RECEIVABLES",
                period,
                [_ref(42, *item) for item in components],
                _ref(42, *total),
            )
        )
    for period, components, total in (
        ("CURRENT", [(43, "4.850.194"), (46, "3.447.260")], (48, "8.297.454")),
        ("COMPARATIVE", [(44, "3.478.007"), (47, "4.416.084")], (49, "7.894.091")),
    ):
        equations.append(
            _equation(
                "OTHER_ASSET_CHILDREN_TO_TOTAL",
                period,
                [_ref(42, *item) for item in components],
                _ref(42, *total),
            )
        )
    return {
        "bank_code": "MBB",
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_BY_CODEX",
        "equations": equations,
        "mappings": mappings,
        "owner": _label(42, 1, "Các khoản phải thu"),
        "page_span": [42, 42],
        "source_period": "2026-06-30",
        "unit_authority": "VISIBLE_PAGE_MILLION_VND",
        "unmapped_source_rows": [],
    }


def _vpb_review() -> dict[str, Any]:
    mappings = [
        _direct(
            967, "RECEIVABLES", 51, 7, "Các khoản phải thu", (68, "17.321.796"), (69, "17.522.681")
        ),
        _direct(
            970,
            "INTERNAL_RECEIVABLES",
            51,
            14,
            "Các khoản phải thu nội bộ",
            (15, "732.193"),
            (16, "571.962"),
        ),
        _direct(
            971,
            "EXTERNAL_RECEIVABLES",
            51,
            17,
            "Các khoản phải thu bên ngoài",
            (18, "10.989.693"),
            (19, "11.432.753"),
        ),
        _mapping(
            5976,
            "WITHOUT_RECOURSE_DOCUMENT_RECEIVABLE",
            [
                _label(
                    51,
                    21,
                    "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do chính NH phát hành",
                ),
                _label(
                    51,
                    26,
                    "Mua hẳn miễn truy đòi bộ chứng từ theo thư tín dụng do NH khác phát hành",
                ),
            ],
            [_ref(51, 23, "2.998.590"), _ref(51, 28, "74.632")],
            [_ref(51, 24, "3.197.773"), _ref(51, 29, "87.709")],
            "SUM_OF_TWO_SOURCE_VARIANTS",
        ),
        _mapping(
            973,
            "DEPOSITS_COLLATERAL",
            [_label(51, 31, "Ký quỹ"), _label(51, 35, "Đặt cọc theo các hợp đồng kinh tế")],
            [_ref(51, 32, "38.152"), _ref(51, 36, "2.540.778")],
            [_ref(51, 33, "36.061"), _ref(51, 37, "2.163.423")],
            "SUM_OF_DEPOSIT_AND_ECONOMIC_CONTRACT_DEPOSIT",
        ),
        _direct(
            5975,
            "PAYMENT_SERVICE_RECEIVABLE",
            51,
            46,
            "Phải thu về hoạt động thanh toán",
            (47, "1.367.455"),
            (48, "2.169.215"),
        ),
        _direct(
            972,
            "ADVANCE_TO_SUPPLIER",
            51,
            50,
            "Tạm ứng nhà cung cấp",
            (51, "592.695"),
            (52, "400.932"),
        ),
        _direct(
            981,
            "OTHER_RECEIVABLE",
            51,
            59,
            "Các khoản phải thu bên ngoài khác",
            (60, "1.560.075"),
            (61, "1.612.712"),
        ),
        _mapping(
            6007,
            "CAPEX_RECEIVABLE",
            [_label(51, 62, "Mua sắm tài sản cố định"), _label(51, 65, "Xây dựng cơ bản dở dang")],
            [_ref(51, 63, "5.508.019"), _ref(51, 66, "91.891")],
            [_ref(51, 64, "5.474.874"), _ref(51, 67, "43.092")],
            "SUM_OF_CAPEX_COMPONENTS",
        ),
        _direct(
            1018,
            "CREDIT_RISK_QUALITY_TOTAL",
            51,
            70,
            "Phân tích chất lượng tài sản Có khác được phân loại là tài sản có rủi ro tín dụng",
            (84, "158.709"),
            (85, "171.786"),
        ),
        _direct(1019, "GRADE_1", 51, 78, "Nợ đủ tiêu chuẩn", (79, "74.632"), (80, "87.709")),
        _direct(1023, "GRADE_5", 51, 81, "Nợ có khả năng mất vốn", (82, "84.077"), (83, "84.077")),
        _direct(
            982,
            "INTEREST_FEE_RECEIVABLES",
            51,
            87,
            "Các khoản lãi, phí phải thu",
            (112, "18.141.278"),
            (113, "14.279.226"),
        ),
        _direct(
            984,
            "DEPOSIT_INTEREST",
            51,
            94,
            "Lãi phải thu từ tiền gửi",
            (95, "110.668"),
            (96, "112.249"),
        ),
        _mapping(
            986,
            "OTHER_INTEREST_AND_FEES",
            [
                _label(51, 97, "Lãi phải thu từ đầu tư chứng khoán"),
                _label(51, 103, "Lãi phải thu từ hoạt động mua nợ"),
                _label(51, 109, "Phí phải thu"),
            ],
            [_ref(51, 98, "1.199.809"), _ref(51, 104, "1.337"), _ref(51, 110, "795.406")],
            [_ref(51, 99, "1.262.447"), _ref(51, 105, "718"), _ref(51, 111, "830.843")],
            "SUM_OF_OTHER_INTEREST_AND_FEE_SOURCES",
        ),
        _direct(
            983,
            "CREDIT_INTEREST",
            51,
            100,
            "Lãi phải thu từ hoạt động tín dụng",
            (101, "14.235.543"),
            (102, "10.755.619"),
        ),
        _direct(
            985,
            "DERIVATIVE_INTEREST",
            51,
            106,
            "Lãi phải thu từ công cụ tài chính phái sinh",
            (107, "1.798.515"),
            (108, "1.317.350"),
        ),
        _direct(
            987,
            "OTHER_ASSET_BRANCH",
            52,
            7,
            "Tài sản Có khác",
            (33, "6.579.263"),
            (34, "6.381.713"),
        ),
        _direct(990, "MATERIAL", 52, 14, "Vật liệu", (15, "32.149"), (16, "28.999")),
        _direct(
            989,
            "PREPAID_COST",
            52,
            17,
            "Chi phí trả trước chờ phân bổ",
            (18, "5.967.020"),
            (19, "5.783.367"),
        ),
        _direct(
            993,
            "COLLATERAL_ASSET",
            52,
            20,
            "Tài sản bảo đảm nhận thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm đã chuyển quyền sở hữu cho tổ chức tín dụng chờ xử lý",
            (23, "564.117"),
            (24, "568.108"),
        ),
        _direct(
            994,
            "COLLATERAL_REAL_ESTATE",
            52,
            26,
            "Trong đó: Bất động sản",
            (27, "564.117"),
            (28, "568.108"),
            "EXACT_SUBSET_OF_COLLATERAL_ASSET",
        ),
        _direct(997, "OTHER_ASSET", 52, 29, "Tài sản có khác", (30, "15.977"), (31, "1.239")),
        _direct(
            999,
            "GOODWILL_GROSS",
            53,
            16,
            "Tổng giá trị Lợi thế thương mại",
            (17, "-"),
            (18, "231.167"),
        ),
        _direct(
            1000,
            "GOODWILL_ALLOCATION_YEARS",
            53,
            19,
            "Thời gian phân bổ (năm)",
            (20, "-"),
            (21, "3"),
        ),
        _direct(
            1001,
            "GOODWILL_ALLOCATED_OPEN",
            53,
            22,
            "Giá trị Lợi thế thương mại đã phân bổ lũy kế đầu kỳ",
            (23, "-"),
            (24, "189.856"),
        ),
        _direct(
            1002,
            "GOODWILL_UNALLOCATED_OPEN",
            53,
            25,
            "Giá trị Lợi thế thương mại chưa phân bổ đầu kỳ",
            (26, "-"),
            (27, "41.310"),
        ),
        _direct(
            1006,
            "GOODWILL_DECREASE",
            53,
            28,
            "Lợi thế thương mại giảm trong kỳ",
            (29, "-"),
            (30, "12.947"),
        ),
        _direct(
            1008,
            "GOODWILL_ALLOCATION",
            53,
            31,
            "Giá trị Lợi thế thương mại phân bổ trong kỳ",
            (32, "-"),
            (33, "12.947"),
        ),
        _direct(
            1010,
            "GOODWILL_UNALLOCATED_CLOSE",
            53,
            34,
            "Tổng giá trị Lợi thế thương mại chưa phân bổ cuối kỳ",
            (36, "-"),
            (37, "28.363"),
        ),
    ]
    equations: list[dict[str, Any]] = []
    pairs = [
        (
            "RECEIVABLES_WITH_CAPEX_TO_TOTAL",
            [(15, "732.193"), (18, "10.989.693"), (63, "5.508.019"), (66, "91.891")],
            (68, "17.321.796"),
            [(16, "571.962"), (19, "11.432.753"), (64, "5.474.874"), (67, "43.092")],
            (69, "17.522.681"),
        ),
        (
            "EXTERNAL_DETAIL_TO_EXTERNAL_TOTAL",
            [
                (23, "2.998.590"),
                (28, "74.632"),
                (32, "38.152"),
                (36, "2.540.778"),
                (40, "280.897"),
                (47, "1.367.455"),
                (51, "592.695"),
                (56, "1.536.419"),
                (60, "1.560.075"),
            ],
            (18, "10.989.693"),
            [
                (24, "3.197.773"),
                (29, "87.709"),
                (33, "36.061"),
                (37, "2.163.423"),
                (41, "453.295"),
                (48, "2.169.215"),
                (52, "400.932"),
                (57, "1.311.633"),
                (61, "1.612.712"),
            ],
            (19, "11.432.753"),
        ),
        (
            "QUALITY_CHILDREN_TO_TOTAL",
            [(79, "74.632"), (82, "84.077")],
            (84, "158.709"),
            [(80, "87.709"), (83, "84.077")],
            (85, "171.786"),
        ),
        (
            "INTEREST_FEE_CHILDREN_TO_TOTAL",
            [
                (95, "110.668"),
                (98, "1.199.809"),
                (101, "14.235.543"),
                (104, "1.337"),
                (107, "1.798.515"),
                (110, "795.406"),
            ],
            (112, "18.141.278"),
            [
                (96, "112.249"),
                (99, "1.262.447"),
                (102, "10.755.619"),
                (105, "718"),
                (108, "1.317.350"),
                (111, "830.843"),
            ],
            (113, "14.279.226"),
        ),
    ]
    for name, current, current_total, comparative, comparative_total in pairs:
        equations.extend(
            [
                _equation(
                    name, "CURRENT", [_ref(51, *item) for item in current], _ref(51, *current_total)
                ),
                _equation(
                    name,
                    "COMPARATIVE",
                    [_ref(51, *item) for item in comparative],
                    _ref(51, *comparative_total),
                ),
            ]
        )
    for period, components, total in (
        (
            "CURRENT",
            [(15, "32.149"), (18, "5.967.020"), (23, "564.117"), (30, "15.977")],
            (33, "6.579.263"),
        ),
        (
            "COMPARATIVE",
            [(16, "28.999"), (19, "5.783.367"), (24, "568.108"), (31, "1.239")],
            (34, "6.381.713"),
        ),
    ):
        equations.append(
            _equation(
                "OTHER_ASSET_CHILDREN_TO_TOTAL",
                period,
                [_ref(52, *item) for item in components],
                _ref(52, *total),
            )
        )
    for period, child, parent in (
        ("CURRENT", (27, "564.117"), (23, "564.117")),
        ("COMPARATIVE", (28, "568.108"), (24, "568.108")),
    ):
        equations.append(
            _equation(
                "COLLATERAL_REAL_ESTATE_EQUALS_PARENT",
                period,
                [_ref(52, *child)],
                _ref(52, *parent),
            )
        )
    equations.extend(
        [
            _equation(
                "GOODWILL_OPEN_MINUS_DECREASE_TO_CLOSE",
                "CURRENT",
                [_ref(53, 26, "-"), _ref(53, 29, "-", -1)],
                _ref(53, 36, "-"),
            ),
            _equation(
                "GOODWILL_OPEN_MINUS_DECREASE_TO_CLOSE",
                "COMPARATIVE",
                [_ref(53, 27, "41.310"), _ref(53, 30, "12.947", -1)],
                _ref(53, 37, "28.363"),
            ),
        ]
    )
    unmapped = [
        _unmapped(
            "OA-001",
            51,
            39,
            "Phải thu bán tài sản tài chính",
            (40, "280.897"),
            (41, "453.295"),
            "Source is broader than schema 976 Phải thu từ bán chứng khoán; no forced narrowing.",
        ),
        _unmapped(
            "OA-002",
            51,
            54,
            "Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm",
            (56, "1.536.419"),
            (57, "1.311.633"),
            "No equivalent receivable child in family 966-1023.",
        ),
        _unmapped(
            "OA-003",
            52,
            48,
            "Số dư đầu kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác",
            (49, "190.401"),
            (50, "226.231"),
            "Other-asset provision roll-forward has no equivalent branch in family 966-1023.",
        ),
        _unmapped(
            "OA-004",
            52,
            51,
            "Trích lập dự phòng rủi ro trong kỳ",
            (52, "494"),
            (53, "1.676"),
            "Other-asset provision roll-forward has no equivalent branch in family 966-1023.",
        ),
        _unmapped(
            "OA-005",
            52,
            60,
            "Số dư cuối kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác",
            (61, "190.895"),
            (62, "227.907"),
            "Other-asset provision roll-forward has no equivalent branch in family 966-1023.",
        ),
        _unmapped(
            "OA-006",
            52,
            70,
            "Dự phòng tài sản Có rủi ro tín dụng",
            (71, "84.077"),
            (72, "84.077"),
            "Closing provision decomposition is not the asset-quality population 1018.",
        ),
        _unmapped(
            "OA-007",
            52,
            74,
            "Dự phòng cụ thể",
            (75, "84.077"),
            (76, "84.077"),
            "No equivalent other-asset provision child in family 966-1023.",
        ),
        _unmapped(
            "OA-008",
            52,
            77,
            "Dự phòng rủi ro phải thu khó đòi",
            (78, "106.818"),
            (79, "106.324"),
            "No equivalent other-asset provision child in family 966-1023.",
        ),
    ]
    return {
        "bank_code": "VPB",
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS",
        "equations": equations,
        "mappings": mappings,
        "owner": _label(51, 5, "TÀI SẢN CÓ KHÁC"),
        "page_span": [51, 53],
        "source_period": "2026-03-31",
        "unit_authority": "VISIBLE_PAGE_MILLION_VND",
        "unmapped_source_rows": unmapped,
    }


def _vib_review() -> dict[str, Any]:
    mappings = [
        _direct(
            966, "FAMILY_TOTAL", 39, 5, "TÀI SẢN CÓ KHÁC", (46, "12.564.438"), (47, "9.951.086")
        ),
        _direct(
            967, "RECEIVABLES", 39, 10, "Các khoản phải thu", (11, "5.045.223"), (12, "4.017.129")
        ),
        _direct(
            970,
            "INTERNAL_RECEIVABLES",
            39,
            13,
            "Các khoản phải thu nội bộ",
            (14, "533.320"),
            (15, "430.070"),
        ),
        _direct(
            971,
            "EXTERNAL_RECEIVABLES",
            39,
            16,
            "Các khoản phải thu bên ngoài",
            (17, "4.511.903"),
            (18, "3.587.059"),
        ),
        _direct(
            975,
            "ADVANCE",
            39,
            25,
            "Tạm ứng chi phí xử lý tài sản bảo đảm",
            (26, "7.448"),
            (27, "7.448"),
        ),
        _direct(
            981,
            "OTHER_RECEIVABLE",
            39,
            31,
            "Các khoản phải thu khác từ bên ngoài",
            (32, "1.390.529"),
            (33, "1.370.000"),
        ),
        _direct(
            6007,
            "CAPEX_RECEIVABLE",
            39,
            34,
            "Chi phí mua sắm tài sản cố định và xây dựng cơ bản dở dang",
            (35, "568.618"),
            (36, "884.906"),
        ),
        _direct(
            982,
            "INTEREST_FEE_RECEIVABLES",
            39,
            37,
            "Các khoản lãi, phí phải thu",
            (38, "4.695.670"),
            (39, "3.902.271"),
        ),
        _direct(
            983,
            "CREDIT_INTEREST",
            39,
            59,
            "Lãi phải thu từ hoạt động tín dụng",
            (60, "2.464.954"),
            (61, "2.091.737"),
        ),
        _direct(
            984,
            "DEPOSIT_INTEREST",
            39,
            53,
            "Lãi phải thu từ tiền gửi",
            (54, "35.272"),
            (55, "24.385"),
        ),
        _direct(
            985,
            "DERIVATIVE_INTEREST",
            39,
            62,
            "Lãi phải thu từ công cụ tài chính phái sinh",
            (63, "638.973"),
            (64, "573.794"),
        ),
        _direct(
            986,
            "OTHER_INTEREST",
            39,
            56,
            "Lãi phải thu từ đầu tư chứng khoán",
            (57, "1.556.471"),
            (58, "1.212.355"),
        ),
        _direct(
            987,
            "OTHER_ASSET_BRANCH",
            39,
            40,
            "Tài sản Có khác",
            (41, "2.822.580"),
            (42, "2.030.721"),
        ),
        _direct(990, "MATERIAL", 39, 72, "Vật liệu", (73, "20.875"), (74, "19.197")),
        _direct(
            993,
            "COLLATERAL_ASSET",
            39,
            75,
            "Tài sản gán nợ đã chuyển quyền sở hữu cho TCTD chờ xử lý",
            (77, "107.399"),
            (78, "106.184"),
        ),
        _direct(
            989, "PREPAID_COST", 39, 79, "Chi phí trả trước", (80, "1.459.277"), (81, "1.036.984")
        ),
        _direct(997, "OTHER_ASSET", 39, 82, "Tài sản có khác", (83, "1.235.029"), (84, "868.356")),
    ]
    equations: list[dict[str, Any]] = []
    pairs = [
        (
            "INTERNAL_PLUS_EXTERNAL_TO_RECEIVABLES",
            [(14, "533.320"), (17, "4.511.903")],
            (11, "5.045.223"),
            [(15, "430.070"), (18, "3.587.059")],
            (12, "4.017.129"),
        ),
        (
            "EXTERNAL_DETAIL_TO_EXTERNAL_TOTAL",
            [
                (20, "31.213"),
                (23, "1.734.316"),
                (26, "7.448"),
                (29, "779.779"),
                (32, "1.390.529"),
                (35, "568.618"),
            ],
            (17, "4.511.903"),
            [
                (21, "36.602"),
                (24, "738.924"),
                (27, "7.448"),
                (30, "549.179"),
                (33, "1.370.000"),
                (36, "884.906"),
            ],
            (18, "3.587.059"),
        ),
        (
            "INTEREST_CHILDREN_TO_TOTAL",
            [(54, "35.272"), (57, "1.556.471"), (60, "2.464.954"), (63, "638.973")],
            (65, "4.695.670"),
            [(55, "24.385"), (58, "1.212.355"), (61, "2.091.737"), (64, "573.794")],
            (66, "3.902.271"),
        ),
        (
            "OTHER_ASSET_CHILDREN_TO_TOTAL",
            [(73, "20.875"), (77, "107.399"), (80, "1.459.277"), (83, "1.235.029")],
            (85, "2.822.580"),
            [(74, "19.197"), (78, "106.184"), (81, "1.036.984"), (84, "868.356")],
            (86, "2.030.721"),
        ),
        (
            "FAMILY_BRANCHES_TO_TOTAL",
            [(11, "5.045.223"), (38, "4.695.670"), (41, "2.822.580"), (44, "965")],
            (46, "12.564.438"),
            [(12, "4.017.129"), (39, "3.902.271"), (42, "2.030.721"), (45, "965")],
            (47, "9.951.086"),
        ),
    ]
    for name, current, current_total, comparative, comparative_total in pairs:
        equations.extend(
            [
                _equation(
                    name, "CURRENT", [_ref(39, *item) for item in current], _ref(39, *current_total)
                ),
                _equation(
                    name,
                    "COMPARATIVE",
                    [_ref(39, *item) for item in comparative],
                    _ref(39, *comparative_total),
                ),
            ]
        )
    unmapped = [
        _unmapped(
            "OA-009",
            39,
            19,
            "Phải thu từ Ngân sách Nhà nước",
            (20, "31.213"),
            (21, "36.602"),
            "Not equivalent to schema 979 Phải thu từ NHNN Việt Nam.",
        ),
        _unmapped(
            "OA-010",
            39,
            22,
            "Phải thu từ hoạt động tài trợ thương mại",
            (23, "1.734.316"),
            (24, "738.924"),
            "No equivalent receivable child in family 966-1023.",
        ),
        _unmapped(
            "OA-011",
            39,
            28,
            "Phải thu hoa hồng bảo hiểm",
            (29, "779.779"),
            (30, "549.179"),
            "Not proven equivalent to receivable from an insurance subsidiary.",
        ),
        _unmapped(
            "OA-012",
            39,
            43,
            "Tài sản thuế TNDN hoãn lại",
            (44, "965"),
            (45, "965"),
            "No equivalent child in family 966-1023.",
        ),
    ]
    return {
        "bank_code": "VIB",
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS",
        "equations": equations,
        "mappings": mappings,
        "owner": _label(39, 5, "TÀI SẢN CÓ KHÁC"),
        "page_span": [39, 40],
        "source_period": "2026-06-30",
        "unit_authority": "VISIBLE_PAGE_MILLION_VND",
        "unmapped_source_rows": unmapped,
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_reason": "The bound report moves directly from long-term investments to government/central-bank liabilities without one detailed other-assets family note.",
        "bank_code": code,
        "boundaries": [_label(page, line, text) for page, line, text in _BOUNDARIES[code]],
        "checks": {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS},
        "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "equations": [],
        "mappings": [],
        "owner": None,
        "page_span": None,
        "source_period": None,
        "unit_authority": None,
        "unmapped_source_rows": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    present = {"MBB": _mbb_review(), "VPB": _vpb_review(), "VIB": _vib_review()}
    return [present.get(code) or _absence(code) for code in EXPECTED_DOCUMENT_ORDER]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": _REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": _REVIEW_STATE,
    }
    return {**material, "review_id": _REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex other-assets pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in items
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return support._page_by_number(document, page_sequence, label)


def _semantic_evidence(
    axis_page: Mapping[str, Any], semantic_page: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    line_index = item["line_index"]
    axis_line = support._axis_line(axis_page, line_index)
    semantic_line = semantic_page["lines"][line_index]
    if (
        semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis_line["vietocr_text"]
        or type(item["pixel_transcription"]) is not str
    ):
        raise _error("semantic/pixel evidence axis drifted")
    return {
        "crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
        "fresh_vietocr_proposal": axis_line["vietocr_text"],
        "line_index": line_index,
        "normalized_fresh_vietocr": normalize_vietnamese_anchor_v1(axis_line["vietocr_text"]),
        "normalized_pixel_transcription": normalize_vietnamese_anchor_v1(
            item["pixel_transcription"]
        ),
        "pixel_transcription": item["pixel_transcription"],
        "source_bbox_raw_pixels": list(axis_line["bbox"]),
    }


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "confirmed_bound_report_absence_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": sum(len(trial["unmapped_source_rows"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _source_period_status(source_period: str) -> str:
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("other-assets result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("other-assets result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS",
                "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS_AND_Q1_PERIOD_CAVEAT",
            }
            or any(
                row.get("status") != "VERIFIED_BY_CODEX"
                for row in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED" for row in trial.get("unmapped_source_rows", [])
            )
        ):
            raise _error("other-assets trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("other-assets result identity drifted")
    return canonical_clone_v1(value)


def build_other_assets_8bank_codex_verified_mapping_v1(
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
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
    ):
        raise _error("fixed semantic axis or structure scan identity drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if reviewed["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT":
            if matcher["regions"]:
                raise _error(f"absence review conflicts with complete region for {code}")
            boundary_evidence = []
            for item in reviewed["boundaries"]:
                boundary_evidence.append(
                    {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(
                            _page(axis_document, item["page_sequence"], "accounting axis"),
                            _page(semantic_document, item["page_sequence"], "semantic index"),
                            item,
                        ),
                    }
                )
            trials.append(
                {
                    "absence_reason": reviewed["absence_reason"],
                    "boundary_evidence": boundary_evidence,
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "page_span": None,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_FAMILY_NOT_PRESENT",
                    "status": reviewed["disposition"],
                    "structure_graph_id": matcher["result_id"],
                    "unmapped_source_rows": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["owner"]["page_sequence"] != reviewed["owner"]["page_sequence"]
            or matcher["regions"][0]["owner"]["source_line_index"]
            != reviewed["owner"]["line_index"]
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed other-assets region is not the unique whole-PDF graph")
        page_cache: dict[int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]] = {}

        def context(
            page_sequence: int,
            *,
            page_cache: dict[
                int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]
            ] = page_cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
            if page_sequence not in page_cache:
                axis_page = _page(axis_document, page_sequence, "accounting axis")
                semantic_page = _page(semantic_document, page_sequence, "semantic index")
                crop_page = _page(crop_document, page_sequence, "crop manifest")
                page_cache[page_sequence] = (
                    axis_page,
                    semantic_page,
                    crop_page,
                    support._source_line_axis(crop_page),
                )
            return page_cache[page_sequence]

        value_cache: dict[tuple[int, int, str], dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[tuple[int, int, str], dict[str, Any]] = value_cache,
            context: Any = context,
        ) -> dict[str, Any]:
            key = (ref["page_sequence"], ref["line_index"], ref["pixel_transcription"])
            if key not in value_cache:
                axis_page, semantic_page, crop_page, source_texts = context(ref["page_sequence"])
                evidence = support._source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    {
                        "line_index": ref["line_index"],
                        "pixel_transcription": ref["pixel_transcription"],
                    },
                )
                value_cache[key] = {**evidence, "page_sequence": ref["page_sequence"]}
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        for mapping in reviewed["mappings"]:
            labels = []
            for item in mapping["labels"]:
                axis_page, semantic_page, _, _ = context(item["page_sequence"])
                labels.append(
                    {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    }
                )
            values = []
            for period_role in ("CURRENT", "COMPARATIVE"):
                components = [verified(item) for item in mapping["values"][period_role]]
                values.append(
                    {
                        "aggregation": (
                            "DIRECT_VISIBLE_VALUE"
                            if len(components) == 1
                            else "SUM_OF_VISIBLE_SOURCE_ROWS"
                        ),
                        "components": components,
                        "normalized_value": sum(item["normalized_value"] for item in components),
                        "period_role": period_role,
                    }
                )
            verified_mappings.append(
                {
                    "label_evidence": labels,
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": values,
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            terms = []
            computed = 0
            for ref in equation["terms"]:
                evidence = verified(ref)
                computed += ref["multiplier"] * evidence["normalized_value"]
                terms.append(
                    {
                        "multiplier": ref["multiplier"],
                        "page_sequence": ref["page_sequence"],
                        "source_line_index": ref["line_index"],
                        "value": evidence["normalized_value"],
                    }
                )
            total = verified(equation["total"])
            if computed != total["normalized_value"]:
                raise _error(f"other-assets accounting equation does not close: {equation['name']}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "period_role": equation["period_role"],
                    "status": "VERIFIED_EXACT",
                    "terms": terms,
                    "visible_total": total["normalized_value"],
                    "visible_total_page_sequence": equation["total"]["page_sequence"],
                    "visible_total_source_line_index": equation["total"]["line_index"],
                }
            )
        unmapped_rows = []
        for row in reviewed["unmapped_source_rows"]:
            item = row["label"]
            axis_page, semantic_page, _, _ = context(item["page_sequence"])
            unmapped_rows.append(
                {
                    "item_id": row["item_id"],
                    "label_evidence": {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    },
                    "reason": row["reason"],
                    "status": "UNRESOLVED",
                    "values": [
                        {
                            "components": [verified(ref) for ref in row["values"][period_role]],
                            "period_role": period_role,
                        }
                        for period_role in ("CURRENT", "COMPARATIVE")
                    ],
                }
            )
        owner_page, owner_semantic_page, _, _ = context(reviewed["owner"]["page_sequence"])
        source_period_status = _source_period_status(reviewed["source_period"])
        status = reviewed["disposition"]
        if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2":
            status = "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS_AND_Q1_PERIOD_CAVEAT"
        trials.append(
            {
                "absence_reason": None,
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner_evidence": _semantic_evidence(
                    owner_page, owner_semantic_page, reviewed["owner"]
                ),
                "page_span": reviewed["page_span"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": status,
                "structure_graph_id": matcher["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "unmapped_source_rows": unmapped_rows,
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    schema_family = {
        "family_end_display_order": max(
            _schema_binding(schema_by_id.get(item), item)["display_order"]
            for item in _SCHEMA_EXPECTED
        ),
        "family_root": _schema_binding(schema_by_id.get(966), 966),
        "mapped_report_norm_ids": sorted(
            {
                mapping["schema_binding"]["report_norm_id"]
                for trial in trials
                for mapping in trial["verified_mappings"]
            }
        ),
    }
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
        "schema_family": schema_family,
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_other_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
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
    supplied = _validate_result(value)
    rebuilt = build_other_assets_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("other-assets verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> tuple[Any, ...]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_other_assets_full_document_scan_v1(semantic_index)
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("live other-assets structure scan identity drifted")
    review = _review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_sha,
        review_sha,
    )


def build_live_other_assets_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_sha,
        review_sha,
    ) = _live_inputs()
    return build_other_assets_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_other_assets_8bank_codex_verified_mapping_v1(value: Any) -> dict[str, Any]:
    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_sha,
        review_sha,
    ) = _live_inputs()
    return validate_other_assets_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def _write(path: Path, value: Any) -> None:
    payload = canonical_json_bytes_v1(value)
    if path.exists() and path.read_bytes() != payload:
        raise _error(f"refusing to replace a different artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    review = _review_blueprint()
    if args.write_review:
        _write(REVIEW_PATH, review)
    result = build_live_other_assets_8bank_codex_verified_mapping_v1()
    if args.write_result:
        _write(RESULT_PATH, result)
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
