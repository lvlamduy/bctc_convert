"""Verify annual-2025 customer-collateral disclosures across eight banks."""

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

FORMAT_VERSION = "ANNUAL_2025_CUSTOMER_COLLATERAL_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_CUSTOMER_COLLATERAL_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_CUSTOMER_COLLATERAL_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025cc8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_CUSTOMER_COLLATERAL_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025cc8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0151-annual-2025-customer-collateral-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0151-annual-2025-customer-collateral-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "ccfdsv1:scan:041a954d98c457c52b285b453bd616f9d01b79293bb3ab4998f360f95d631cee"
EXPECTED_RESULT_ID: str | None = (
    "annual2025cc8bcv1:result:4be8b090abea4c021deee5144deaf78e5bc825c1a18b85e4ccbe1043fd56b8ad"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_CUSTOMER_COLLATERAL_GRAPH_VISIBLE_PDF_SOURCE_"
    "NUMERIC_CHALLENGER_CHILD_TOTAL_NESTED_DETAIL_CONTROLLED_CATCHALL_"
    "LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "controlled_catchall_sum_uses_only_authenticated_source_rows": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_customer_collateral_rows": True,
    "nested_detail_counted_twice_in_family_total": False,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "whole_pdf_uniqueness_replayed": True,
}

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 839),
    1280: ("Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ", 1259, 860),
    1281: ("Bất động sản", 1280, 861),
    1282: ("Động sản", 1280, 862),
    1283: ("Máy móc, thiết bị", 1280, 863),
    1284: ("Phương tiện vận tải", 1280, 864),
    1285: ("Hàng tồn kho", 1280, 865),
    1286: ("Giấy tờ có giá", 1280, 866),
    1287: ("-Trong đó: Giấy tờ có giá do doanh nghiệp phát hành", 1280, 867),
    1288: ("Khác", 1280, 868),
}


class Annual2025CustomerCollateral8BankError(ValueError):
    """The annual customer-collateral graph, values, equations, or schema drifted."""


def _error(message: str) -> Annual2025CustomerCollateral8BankError:
    return Annual2025CustomerCollateral8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_customer_collateral_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_customer_collateral_mapping_base_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual customer-collateral support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _controlled_sum(
    base: ModuleType,
    page: int,
    components: Sequence[tuple[int, str]],
) -> dict[str, Any]:
    if len(components) < 2:
        raise _error("annual customer-collateral controlled sum needs at least two rows")
    return {
        "components": [base._line(page, line, text) for line, text in components],
        "kind": "AUTHENTICATED_CONTROLLED_SUM",
        "page_sequence": page,
    }


def _mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Mapping[str, Any] | tuple[int, str],
    comparative: Mapping[str, Any] | tuple[int, str],
    *,
    equality_parent_role: str | None = None,
    non_additive_nested_detail: bool = False,
) -> dict[str, Any]:
    def ref(value: Mapping[str, Any] | tuple[int, str]) -> dict[str, Any]:
        return canonical_clone_v1(value) if isinstance(value, Mapping) else base._line(page, *value)

    item = {
        "labels": [base._ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": (
            "VISIBLE_NESTED_DETAIL_EQUAL_TO_PARENT_NOT_ADDITIVE_TO_FAMILY_TOTAL"
            if non_additive_nested_detail
            else "CUSTOMER_SCOPED_COLLATERAL_ROW_WITH_TWO_PERIOD_AXES"
        ),
        "values": [
            {"axis_role": "CURRENT", **ref(current)},
            {"axis_role": "COMPARATIVE", **ref(comparative)},
        ],
    }
    if non_additive_nested_detail:
        if equality_parent_role is None:
            raise _error("nested customer-collateral detail needs an equality parent")
        item["equality_parent_role"] = equality_parent_role
        item["family_total_contribution"] = "NON_ADDITIVE_NESTED_DETAIL"
    return item


def _document(
    base: ModuleType,
    code: str,
    page: int,
    owner: Sequence[tuple[int, str]],
    mappings: Sequence[dict[str, Any]],
    units: Sequence[tuple[int, str]],
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": canonical_clone_v1(mappings),
        "owner": [base._ref(page, *item) for item in owner],
        "page_span": [page, page],
        "source_only_rows": [],
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, *item) for item in units],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    page = 74
    docs.append(
        _document(
            base,
            "ACB",
            page,
            [
                (
                    5,
                    'TÀI SẢN, GIẤY TỜ CÓ GIÁ ("GTCG") THẾ CHẤP, CẦM CỐ VÀ CHIẾT KHẤU, TÁI CHIẾT KHẤU',
                ),
                (7, "Tài sản, GTCG nhận thế chấp, cầm cố và chiết khấu, tái chiết khấu"),
                (12, "Tài sản, GTCG nhận thế chấp, cầm cố và chiết khấu của"),
                (13, "khách hàng"),
            ],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1280,
                    page,
                    [],
                    (33, "1.246.316.786"),
                    (34, "1.269.762.743"),
                ),
                _mapping(
                    base,
                    "REAL_ESTATE",
                    1281,
                    page,
                    [(14, "Bất động sản")],
                    (15, "1.067.681.534"),
                    (16, "1.050.007.290"),
                ),
                _mapping(
                    base,
                    "INVENTORY",
                    1285,
                    page,
                    [(17, "Hàng tồn kho")],
                    (18, "3.508.908"),
                    (19, "785.201"),
                ),
                _mapping(
                    base,
                    "MACHINERY_EQUIPMENT",
                    1283,
                    page,
                    [(20, "Máy móc, thiết bị")],
                    (21, "6.201.234"),
                    (22, "4.006.319"),
                ),
                _mapping(
                    base,
                    "VALUABLE_PAPERS",
                    1286,
                    page,
                    [(23, "Giấy tờ có giá")],
                    (24, "115.564.606"),
                    (25, "179.447.364"),
                ),
                _mapping(
                    base,
                    "VALUABLE_PAPERS_ENTERPRISE_ISSUER_DETAIL",
                    1287,
                    page,
                    [(26, "Trong đó:"), (27, "GTCG do doanh nghiệp phát hành")],
                    (28, "115.564.606"),
                    (29, "179.447.364"),
                    equality_parent_role="VALUABLE_PAPERS",
                    non_additive_nested_detail=True,
                ),
                _mapping(
                    base,
                    "OTHER_COLLATERAL",
                    1288,
                    page,
                    [(30, "Tài sản khác")],
                    (31, "53.360.504"),
                    (32, "35.516.569"),
                ),
            ],
            [(10, "Triệu VND"), (11, "Triệu VND")],
        )
    )

    docs.append(base._absence("MBB"))

    page = 74
    docs.append(
        _document(
            base,
            "VPB",
            page,
            [
                (5, "LOẠI HÌNH VÀ GIÁ TRỊ SỔ SÁCH TÀI SẢN THẾ CHẤP"),
                (7, "Tài sản, giấy tờ có giá nhận thế chấp, cầm cố và chiết khấu, tái chiết khấu"),
                (
                    8,
                    "Bảng dưới đây trình bày giá trị sổ sách của tài sản thế chấp của khách hàng tại thời điểm cuối",
                ),
                (9, "năm như sau:"),
            ],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1280,
                    page,
                    [],
                    (30, "2.755.231.997"),
                    (31, "1.908.343.272"),
                ),
                _mapping(
                    base,
                    "REAL_ESTATE",
                    1281,
                    page,
                    [(18, "Bất động sản")],
                    (19, "682.891.731"),
                    (20, "616.660.384"),
                ),
                _mapping(
                    base,
                    "MOVABLE_PROPERTY",
                    1282,
                    page,
                    [(21, "Động sản")],
                    (22, "110.180.116"),
                    (23, "93.763.257"),
                ),
                _mapping(
                    base,
                    "VALUABLE_PAPERS",
                    1286,
                    page,
                    [(24, "Giấy tờ có giá")],
                    (25, "44.046.168"),
                    (26, "54.089.579"),
                ),
                _mapping(
                    base,
                    "OTHER_COLLATERAL",
                    1288,
                    page,
                    [(27, "Các tài sản đảm bảo khác")],
                    (28, "1.918.113.982"),
                    (29, "1.143.830.052"),
                ),
            ],
            [(16, "Triệu đồng"), (17, "Triệu đồng")],
        )
    )

    page = 54
    docs.append(
        _document(
            base,
            "HDB",
            page,
            [
                (57, "TÀI SẢN, GIẤY TỜ CÓ GIÁ THẾ CHẤP, CẦM CỐ VÀ CHIẾT KHẤU, TÁI CHIẾT KHẤU"),
                (
                    59,
                    "Tài sản, giấy tờ có giá nhận thế chấp, cầm cố và chiết khấu, tái chiết khấu đảm bảo cho các",
                ),
                (60, "khoản nợ nội bảng"),
                (65, "Của khách hàng"),
            ],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1280,
                    page,
                    [(65, "Của khách hàng")],
                    (66, "1.042.159.932"),
                    (67, "706.190.899"),
                ),
                _mapping(
                    base,
                    "REAL_ESTATE",
                    1281,
                    page,
                    [(68, "Bất động sản")],
                    (69, "444.247.241"),
                    (70, "388.639.341"),
                ),
                _mapping(
                    base,
                    "VALUABLE_PAPERS",
                    1286,
                    page,
                    [(71, "Cổ phiếu, giấy tờ có giá")],
                    (72, "96.400.745"),
                    (73, "87.864.753"),
                ),
                _mapping(
                    base,
                    "MACHINERY_EQUIPMENT",
                    1283,
                    page,
                    [(74, "Máy móc, thiết bị")],
                    (75, "11.018.807"),
                    (76, "11.814.167"),
                ),
                _mapping(
                    base,
                    "TRANSPORT_EQUIPMENT",
                    1284,
                    page,
                    [(77, "Phương tiện vận chuyển")],
                    (78, "22.862.848"),
                    (79, "13.747.796"),
                ),
                _mapping(
                    base,
                    "INVENTORY",
                    1285,
                    page,
                    [(80, "Hàng hóa, nguyên vật liệu")],
                    (81, "2.547.513"),
                    (82, "2.223.155"),
                ),
                _mapping(
                    base,
                    "OTHER_COLLATERAL",
                    1288,
                    page,
                    [(83, "Tài sản khác")],
                    (84, "465.082.778"),
                    (85, "201.901.687"),
                ),
            ],
            [(63, "Triệu VND"), (64, "Triệu VND")],
        )
    )

    docs.extend([base._absence("VCB"), base._absence("CTG"), base._absence("BID")])

    page = 54
    current_other = _controlled_sum(
        base,
        page,
        [(41, "64.072.713"), (44, "20.974.160"), (47, "59.317.931"), (55, "9.136.802")],
    )
    comparative_other = _controlled_sum(
        base,
        page,
        [(42, "20.111.880"), (45, "16.920.803"), (48, "44.024.363"), (56, "8.303.474")],
    )
    docs.append(
        _document(
            base,
            "VIB",
            page,
            [
                (20, 'TÀI SẢN, GIẤY TỜ CÓ GIÁ ("GTCG") THẾ CHẤP, CẦM CỐ VÀ CHIẾT KHẤU, TÁI CHIẾT'),
                (21, "KHẤU"),
                (
                    23,
                    "Tài sản, GTCG nhận thế chấp, cầm cố và chiết khấu, tái chiết khấu cho Ngân hàng",
                ),
                (28, "Của khách hàng"),
            ],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1280,
                    page,
                    [(28, "Của khách hàng")],
                    (29, "702.878.947"),
                    (30, "626.151.273"),
                ),
                _mapping(
                    base,
                    "REAL_ESTATE",
                    1281,
                    page,
                    [(31, "Bất động sản")],
                    (32, "428.015.337"),
                    (33, "415.144.780"),
                ),
                _mapping(
                    base,
                    "TRANSPORT_EQUIPMENT",
                    1284,
                    page,
                    [(34, "Phương tiện vận tải")],
                    (35, "73.845.042"),
                    (36, "76.096.187"),
                ),
                _mapping(
                    base,
                    "MACHINERY_EQUIPMENT",
                    1283,
                    page,
                    [(37, "Máy móc thiết bị")],
                    (38, "23.104.419"),
                    (39, "26.277.312"),
                ),
                _mapping(
                    base,
                    "INVENTORY",
                    1285,
                    page,
                    [(50, "Hàng hóa lưu kho")],
                    (51, "24.412.543"),
                    (52, "19.272.474"),
                ),
                _mapping(
                    base,
                    "OTHER_COLLATERAL",
                    1288,
                    page,
                    [
                        (40, "Quyền khai thác tài sản"),
                        (43, "Bảo lãnh"),
                        (46, "Vàng, ngoại tệ, giấy tờ có giá"),
                        (54, "Tài sản đảm bảo khác"),
                    ],
                    current_other,
                    comparative_other,
                ),
            ],
            [(26, "triệu đồng"), (27, "triệu đồng")],
        )
    )

    expected = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
    if [item["bank_code"] for item in docs] != expected:
        raise _error("annual customer-collateral document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.FAMILY_END_DISPLAY_ORDER = 868
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


def build_annual_2025_customer_collateral_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_customer_collateral_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        return _base().build_live_customer_collateral_8bank_codex_verified_mapping_v1()
    except Annual2025CustomerCollateral8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_customer_collateral_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _base().validate_live_customer_collateral_8bank_codex_verified_mapping_v1(value)
    except Annual2025CustomerCollateral8BankError:
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
                build_annual_2025_customer_collateral_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        RESULT_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_live_annual_2025_customer_collateral_8bank_codex_verified_mapping_v1()
            )
        )
        return 0
    value, _ = _base()._stable_json(RESULT_PATH)
    validate_annual_2025_customer_collateral_8bank_codex_verified_mapping_replay_v1(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
