"""Verify annual-2025 State-budget-obligation disclosures across eight banks."""

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

FORMAT_VERSION = "ANNUAL_2025_STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_STATE_BUDGET_OBLIGATIONS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025sbo8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_STATE_BUDGET_OBLIGATIONS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025sbo8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0150-annual-2025-state-budget-obligations-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0150-annual-2025-state-budget-obligations-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "sbofdsv1:scan:c0cc18a0a599448f685c600f50b87b52be64604e20025a17be010ae706aac6f4"
EXPECTED_RESULT_ID: str | None = (
    "annual2025sbo8bcv1:result:e51fbdfc0568a11c074bf817760bdaba6640942e2783a8de18b20ad08d39fa67"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_STATE_BUDGET_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_"
    "CHALLENGER_MOVEMENT_AXES_SIGNED_RECEIVABLE_PAYABLE_NETTING_DASH_ZERO_"
    "ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_normalized_to_zero_only_after_visible_pixel_review": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_state_budget_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "receivable_and_payable_branches_netted_only_by_authenticated_signed_sum": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "whole_pdf_uniqueness_replayed": True,
}

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 839),
    1269: ("Tình hình thực hiện nghĩa vụ với ngân sách nhà nước", 1259, 849),
    1270: ("Thuế giá trị gia tăng", 1269, 850),
    1271: ("Thuế TNDN", 1269, 851),
    1272: ("Thuế Thu nhập Cá nhân", 1269, 852),
    1273: ("Thuế xuất nhập khẩu", 1269, 853),
    1274: ("Thuế tài nguyên", 1269, 854),
    1275: ("Thuế sử dụng vốn NSNN", 1269, 855),
    1276: ("Thuế tiêu thụ đặc biệt", 1269, 856),
    1277: ("Thuế nhà - đất", 1269, 857),
    1278: ("Các loại thuế khác", 1269, 858),
    1279: ("Các khoản phải nộp khác", 1269, 859),
}


class Annual2025StateBudgetObligations8BankError(ValueError):
    """The annual State-budget graph, values, equations, or schema drifted."""


def _error(message: str) -> Annual2025StateBudgetObligations8BankError:
    return Annual2025StateBudgetObligations8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_state_budget_obligations_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_state_budget_obligations_mapping_base_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual State-budget support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _aggregate(
    base: ModuleType,
    page: int,
    components: Sequence[tuple[int, int, str]],
) -> dict[str, Any]:
    return {
        "components": [
            {"coefficient": coefficient, "ref": base._line(page, line, text)}
            for coefficient, line, text in components
        ],
        "kind": "AUTHENTICATED_SIGNED_AGGREGATE",
    }


def _pixel_dash(
    page: int,
    bbox: Sequence[int],
    rgb_sha256: str,
) -> dict[str, Any]:
    return {
        "bbox_raw_pixels": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "page_sequence": page,
        "pixel_rgb_sha256": rgb_sha256,
        "pixel_transcription": "-",
    }


def _values(
    base: ModuleType,
    page: int,
    opening: Mapping[str, Any] | tuple[int, str],
    payable: Mapping[str, Any] | tuple[int, str],
    paid: Mapping[str, Any] | tuple[int, str],
    closing: Mapping[str, Any] | tuple[int, str],
) -> list[tuple[str, Mapping[str, Any]]]:
    def ref(value: Mapping[str, Any] | tuple[int, str]) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else base._line(page, *value)

    return [
        ("OPENING", ref(opening)),
        ("PAYABLE_INCREASE", ref(payable)),
        ("PAID_DECREASE", ref(paid)),
        ("CLOSING", ref(closing)),
    ]


def _mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    values: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    topology: str = "ROW_WITH_VISIBLE_MOVEMENT_AXES",
) -> dict[str, Any]:
    return base._mapping(role, report_norm_id, page, labels, values, topology=topology)


def _document(
    base: ModuleType,
    code: str,
    page: int,
    owner: Sequence[tuple[int, str]],
    mappings: Sequence[dict[str, Any]],
    units: Sequence[tuple[int, str]],
    *,
    presentation: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": canonical_clone_v1(mappings),
        "owner": [base._ref(page, *item) for item in owner],
        "page_span": [page, page],
        "presentation": presentation,
        "source_only_rows": [],
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, *item) for item in units],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    page = 73
    docs.append(
        _document(
            base,
            "ACB",
            page,
            [(51, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (79, "2.582.875"),
                        (80, "5.373.476"),
                        (81, "5.781.601"),
                        (82, "2.174.750"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(62, "Thuế giá trị gia tăng")],
                    _values(
                        base, page, (63, "53.192"), (64, "449.545"), (65, "451.650"), (66, "51.087")
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(67, "Thuế thu nhập doanh nghiệp")],
                    _values(
                        base,
                        page,
                        (68, "2.385.237"),
                        (69, "3.914.022"),
                        (70, "4.335.459"),
                        (71, "1.963.800"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(72, "Các loại thuế khác")],
                    _values(
                        base,
                        page,
                        (73, "144.446"),
                        (74, "1.009.909"),
                        (75, "994.492"),
                        (76, "159.863"),
                    ),
                ),
            ],
            [(57, "Triệu VND")],
            presentation="DIRECT_FOUR_MOVEMENT_LANES",
        )
    )

    page = 68
    docs.append(
        _document(
            base,
            "MBB",
            page,
            [(10, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (37, "3.574.209"),
                        (38, "10.637.127"),
                        (39, "(9.993.077)"),
                        (40, "4.218.259"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(22, "Thuế giá trị gia tăng")],
                    _values(
                        base,
                        page,
                        (23, "118.529"),
                        (24, "1.161.323"),
                        (25, "(1.104.805)"),
                        (26, "175.047"),
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(27, "Thuế thu nhập doanh nghiệp")],
                    _values(
                        base,
                        page,
                        (28, "3.200.018"),
                        (29, "7.215.707"),
                        (30, "(6.517.907)"),
                        (31, "3.897.818"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(32, "Các loại thuế khác")],
                    _values(
                        base,
                        page,
                        (33, "255.662"),
                        (34, "2.260.097"),
                        (35, "(2.370.365)"),
                        (36, "145.394"),
                    ),
                ),
            ],
            [(18, "triệu đồng")],
            presentation="CURRENT_ANNUAL_MOVEMENT_BLOCK_WITH_PRIOR_YEAR_CONTROL_BLOCK_EXCLUDED",
        )
    )

    page = 64
    docs.append(
        _document(
            base,
            "VPB",
            page,
            [(5, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (31, "2.576.458"),
                        (32, "9.019.017"),
                        (33, "(6.883.323)"),
                        (34, "4.712.152"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(16, "Thuế giá trị gia tăng")],
                    _values(
                        base,
                        page,
                        (17, "115.620"),
                        (18, "935.947"),
                        (19, "(879.329)"),
                        (20, "172.238"),
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(21, "Thuế thu nhập doanh nghiệp")],
                    _values(
                        base,
                        page,
                        (22, "2.320.313"),
                        (23, "6.216.323"),
                        (24, "(4.127.774)"),
                        (25, "4.408.862"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(26, "Thuế khác")],
                    _values(
                        base,
                        page,
                        (27, "140.525"),
                        (28, "1.866.747"),
                        (29, "(1.876.220)"),
                        (30, "131.052"),
                    ),
                ),
            ],
            [(12, "Triệu đồng")],
            presentation="DIRECT_FOUR_MOVEMENT_LANES_WITH_PAYABLE_AND_ADJUSTMENT_HEADER",
        )
    )

    page = 47
    docs.append(
        _document(
            base,
            "HDB",
            page,
            [(66, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (101, "1.074.508"),
                        (102, "5.304.421"),
                        (103, "3.744.496"),
                        (104, "2.634.433"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(76, "Thuế giá trị gia tăng")],
                    _values(
                        base, page, (77, "60.055"), (78, "518.855"), (79, "521.347"), (80, "57.563")
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(81, "Thuế thu nhập doanh nghiệp")],
                    _values(
                        base,
                        page,
                        (82, "915.608"),
                        (83, "4.189.679"),
                        (84, "2.591.536"),
                        (85, "2.513.751"),
                    ),
                ),
                _mapping(
                    base,
                    "PERSONAL_INCOME_TAX",
                    1272,
                    page,
                    [(86, "Thuế thu nhập cá nhân")],
                    _values(
                        base, page, (87, "73.845"), (88, "458.606"), (89, "498.948"), (90, "33.503")
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(91, "Thuế nhà thầu")],
                    _values(
                        base, page, (92, "16.394"), (93, "127.115"), (94, "113.893"), (95, "29.616")
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_PAYABLE",
                    1279,
                    page,
                    [(96, "Các loại thuế khác, các khoản phí,"), (100, "lệ phí và phải nộp khác")],
                    _values(
                        base,
                        page,
                        (97, "8.606"),
                        (98, "10.166"),
                        (99, "18.772"),
                        _pixel_dash(
                            page,
                            [1478, 1577, 1494, 1588],
                            "96a1c3343acd9ccf5d5535db1b8e8310dd16718e8385b353344162062b87e934",
                        ),
                    ),
                    topology="WRAPPED_OTHER_TAX_FEE_PAYABLE_ROW_WITH_VISIBLE_DASH_CLOSING",
                ),
            ],
            [(72, "Triệu VND")],
            presentation="DIRECT_FOUR_MOVEMENT_LANES_WITH_WRAPPED_OTHER_PAYABLE_ROW",
        )
    )

    page = 65
    docs.append(
        _document(
            base,
            "VCB",
            page,
            [(7, "Tình hình thực hiện nghĩa vụ với Ngân sách Nhà nước")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (62, "4.096.542"),
                        (63, "11.094.860"),
                        (64, "(12.508.026)"),
                        (67, "2.683.376"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(23, "Thuế giá trị gia tăng")],
                    _values(
                        base,
                        page,
                        (24, "36.934"),
                        (25, "764.685"),
                        (26, "(831.914)"),
                        (29, "(30.295)"),
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(30, "Thuế TNDN")],
                    _values(
                        base,
                        page,
                        (31, "3.867.377"),
                        (32, "7.844.436"),
                        (33, "(9.241.965)"),
                        (36, "2.469.848"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(55, "Các loại thuế khác")],
                    _values(
                        base,
                        page,
                        (56, "192.231"),
                        (57, "2.485.739"),
                        (58, "(2.434.147)"),
                        (61, "243.823"),
                    ),
                ),
            ],
            [(17, "Triệu VND")],
            presentation="CLOSING_PAYABLE_PLUS_ADVANCE_LANES_WITH_AUTHENTICATED_NET_TOTAL",
        )
    )

    page = 62
    docs.append(
        _document(
            base,
            "CTG",
            page,
            [(54, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        _aggregate(base, page, [(1, 96, "3.601.656"), (-1, 76, "6.920")]),
                        _aggregate(base, page, [(1, 97, "11.099.608"), (-1, 77, "(7.287)")]),
                        _aggregate(base, page, [(1, 98, "(10.057.095)"), (-1, 78, "6.611")]),
                        _aggregate(base, page, [(1, 99, "4.644.169"), (-1, 79, "6.244")]),
                    ),
                    topology="PAYABLE_BRANCH_MINUS_RECEIVABLE_BRANCH_SIGNED_NET_MOVEMENT",
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(67, "Thuế GTGT"), (81, "Thuế GTGT đầu ra")],
                    _values(
                        base,
                        page,
                        _aggregate(base, page, [(1, 82, "104.946"), (-1, 68, "6.019")]),
                        _aggregate(base, page, [(1, 83, "1.004.193"), (-1, 69, "30")]),
                        (84, "(998.440)"),
                        _aggregate(base, page, [(1, 85, "110.699"), (-1, 70, "6.049")]),
                    ),
                    topology="PAYABLE_BRANCH_MINUS_RECEIVABLE_BRANCH_SIGNED_NET_MOVEMENT",
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(71, "Thuế TNDN"), (86, "Thuế TNDN")],
                    _values(
                        base,
                        page,
                        _aggregate(base, page, [(1, 87, "3.337.834"), (-1, 72, "901")]),
                        _aggregate(base, page, [(1, 88, "8.562.687"), (-1, 73, "(7.317)")]),
                        _aggregate(base, page, [(1, 89, "(7.540.879)"), (-1, 74, "6.611")]),
                        _aggregate(base, page, [(1, 90, "4.359.642"), (-1, 75, "195")]),
                    ),
                    topology="PAYABLE_BRANCH_MINUS_RECEIVABLE_BRANCH_SIGNED_NET_MOVEMENT",
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(91, "Các loại thuế khác")],
                    _values(
                        base,
                        page,
                        (92, "158.876"),
                        (93, "1.532.728"),
                        (94, "(1.517.776)"),
                        (95, "173.828"),
                    ),
                ),
            ],
            [(62, "Triệu đồng")],
            presentation="SEPARATE_RECEIVABLE_AND_PAYABLE_BRANCHES_NETTED_BY_SIGNED_ACCOUNTING_SUM",
        )
    )

    page = 52
    docs.append(
        _document(
            base,
            "BID",
            page,
            [(87, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (124, "3.366.055"),
                        (125, "12.090.394"),
                        (126, "(11.375.096)"),
                        (127, "4.081.353"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(103, "Thuế GTGT")],
                    _values(
                        base,
                        page,
                        (104, "2.355"),
                        (105, "1.555.989"),
                        (106, "(1.429.729)"),
                        (107, "128.615"),
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(108, "Thuế TNDN")],
                    _values(
                        base,
                        page,
                        (109, "2.992.028"),
                        (110, "7.368.944"),
                        (111, "(6.769.278)"),
                        (112, "3.591.694"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(113, "Các loại thuế khác")],
                    _values(
                        base,
                        page,
                        (114, "194.333"),
                        (115, "3.075.794"),
                        (116, "(3.085.988)"),
                        (117, "184.139"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_PAYABLE",
                    1279,
                    page,
                    [(118, "Các khoản phải nộp khác và"), (123, "các khoản phí, lệ phí")],
                    _values(
                        base,
                        page,
                        (119, "177.339"),
                        (120, "89.667"),
                        (121, "(90.101)"),
                        (122, "176.905"),
                    ),
                ),
            ],
            [(97, "Triệu VND")],
            presentation="DIRECT_FOUR_MOVEMENT_LANES_WITH_WRAPPED_OTHER_PAYABLE_ROW",
        )
    )

    page = 52
    docs.append(
        _document(
            base,
            "VIB",
            page,
            [(63, "TÌNH HÌNH THỰC HIỆN NGHĨA VỤ VỚI NGÂN SÁCH NHÀ NƯỚC")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1269,
                    page,
                    [],
                    _values(
                        base,
                        page,
                        (87, "1.367.507"),
                        (88, "2.652.618"),
                        (89, "(2.730.519)"),
                        (90, "1.289.606"),
                    ),
                ),
                _mapping(
                    base,
                    "CORPORATE_INCOME_TAX",
                    1271,
                    page,
                    [(72, "Thuế thu nhập doanh nghiệp")],
                    _values(
                        base,
                        page,
                        (73, "1.309.653"),
                        (74, "1.819.149"),
                        (75, "(1.943.702)"),
                        (76, "1.185.100"),
                    ),
                ),
                _mapping(
                    base,
                    "VAT",
                    1270,
                    page,
                    [(77, "Thuế giá trị gia tăng")],
                    _values(
                        base,
                        page,
                        (78, "18.505"),
                        (79, "304.400"),
                        (80, "(262.331)"),
                        (81, "60.574"),
                    ),
                ),
                _mapping(
                    base,
                    "OTHER_TAX",
                    1278,
                    page,
                    [(82, "Các loại thuế khác")],
                    _values(
                        base,
                        page,
                        (83, "39.349"),
                        (84, "529.069"),
                        (85, "(524.486)"),
                        (86, "43.932"),
                    ),
                ),
            ],
            [(64, "Đơn vị: triệu đồng")],
            presentation="DIRECT_FOUR_MOVEMENT_LANES",
        )
    )

    if [item["bank_code"] for item in docs] != [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]:
        raise _error("annual State-budget document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.FAMILY_END_DISPLAY_ORDER = 859
    base.SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_MOVEMENT_PERIOD"
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


def build_annual_2025_state_budget_obligations_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    try:
        return _base().build_live_state_budget_obligations_8bank_codex_verified_mapping_v1()
    except Annual2025StateBudgetObligations8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _base().validate_live_state_budget_obligations_8bank_codex_verified_mapping_v1(value)
    except Annual2025StateBudgetObligations8BankError:
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
                build_annual_2025_state_budget_obligations_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        result = build_live_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    result, _ = _base()._stable_json(RESULT_PATH)
    verified = validate_annual_2025_state_budget_obligations_8bank_codex_verified_mapping_replay_v1(
        result
    )
    print(verified["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
