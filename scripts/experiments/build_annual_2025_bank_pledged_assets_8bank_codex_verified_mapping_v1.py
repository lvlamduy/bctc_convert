"""Verify annual-2025 bank-owned pledged/discounted assets across eight banks."""

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

FORMAT_VERSION = "ANNUAL_2025_BANK_PLEDGED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_BANK_PLEDGED_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_BANK_PLEDGED_ASSETS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025bpa8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_BANK_PLEDGED_ASSETS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025bpa8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0152-annual-2025-bank-pledged-assets-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0152-annual-2025-bank-pledged-assets-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "bpafdsv1:scan:d2ced3689c970654608ad12504d685e1f45cfcf2b53025348b3eb1687b5a6a15"
EXPECTED_RESULT_ID: str | None = (
    "annual2025bpa8bcv1:result:2d79477e02e02eb7e38775dc8e2de8b01c1016ddd53181a33093efc452aed98a"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_BANK_OWNED_PLEDGED_DISCOUNTED_ASSET_GRAPH_VISIBLE_"
    "PDF_SOURCE_NUMERIC_CHALLENGER_AUTHENTICATED_DASH_ZERO_CHILD_TOTAL_"
    "CONTROLLED_CATCHALL_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "authenticated_pixel_dash_means_zero": True,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "controlled_catchall_sum_uses_only_authenticated_source_rows": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_bank_pledged_asset_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_printed_double_count_relabelled_as_accounting_identity": False,
    "source_printed_hierarchy_contradiction_retained": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "whole_pdf_uniqueness_replayed": True,
}

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 839),
    1289: (
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        1259,
        869,
    ),
    1290: ("Chứng khoán kinh doanh", 1289, 870),
    1291: ("Chứng khoán đầu tư", 1289, 871),
    1292: ("Tài sản cố định", 1289, 872),
    1293: ("Tài sản khác", 1289, 873),
}


class Annual2025BankPledgedAssets8BankError(ValueError):
    """The annual graph, pixels, values, equations, or live schema drifted."""


def _error(message: str) -> Annual2025BankPledgedAssets8BankError:
    return Annual2025BankPledgedAssets8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_bank_pledged_assets_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_bank_pledged_assets_mapping_base_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual bank-pledged-assets support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _controlled_sum(
    base: ModuleType,
    page: int,
    components: Sequence[Mapping[str, Any] | tuple[int, str]],
) -> dict[str, Any]:
    if len(components) < 2:
        raise _error("annual bank-pledged-assets controlled sum needs at least two rows")
    return {
        "components": [
            canonical_clone_v1(item) if isinstance(item, Mapping) else base._line(page, *item)
            for item in components
        ],
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
    topology: str = "BANK_OWN_ASSET_ROW_WITH_TWO_PERIOD_AXES",
) -> dict[str, Any]:
    return {
        "labels": [base._ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": base._values(page, current, comparative),
    }


def _document(
    base: ModuleType,
    code: str,
    page: int,
    owner: Sequence[tuple[int, str]],
    mappings: Sequence[Mapping[str, Any]],
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


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No bank-owned pledged/collateralized/discounted table with an owner, at least "
                "one source child, two reporting periods and a unit was found; customer and "
                "other-credit-institution collateral branches do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    page = 74
    acb_trading_comparative_dash = base.other._dash(
        page,
        [1389, 1746, 1535, 1774],
        "ed67e9691c498e57685321f1b2549d377279035d3fde686b6655ac82bfbb0cd2",
    )
    acb_fixed_current_dash = base.other._dash(
        page,
        [1177, 1818, 1320, 1847],
        "a602cb03a6295c8d87331a24a1b210f302c4a8932cba11666b098216d99339cd",
    )
    docs.append(
        _document(
            base,
            "ACB",
            page,
            [(51, "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1289,
                    page,
                    [(51, "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu")],
                    (70, "65.662.617"),
                    (71, "37.555.880"),
                ),
                _mapping(
                    base,
                    "OTHER_ASSETS",
                    1293,
                    page,
                    [(57, "Tiền gửi có kỳ hạn tại các TCTD khác (Thuyết minh 6.1(i))")],
                    (58, "14.868.385"),
                    (59, "20.484.125"),
                    "SOURCE_ACCOUNTING_ROW_MAPPED_TO_CONTROLLED_SCHEMA_CATCHALL",
                ),
                _mapping(
                    base,
                    "TRADING_SECURITIES",
                    1290,
                    page,
                    [(60, "Chứng khoán kinh doanh (Thuyết minh 7.1(ii))")],
                    (61, "770.000"),
                    acb_trading_comparative_dash,
                ),
                _mapping(
                    base,
                    "INVESTMENT_SECURITIES",
                    1291,
                    page,
                    [(63, "Chứng khoán đầu tư (Thuyết minh 10.1(i))")],
                    (64, "50.024.232"),
                    (65, "17.042.745"),
                ),
                _mapping(
                    base,
                    "FIXED_ASSETS",
                    1292,
                    page,
                    [(67, "Tài sản cố định (Thuyết minh 12.1)")],
                    acb_fixed_current_dash,
                    (68, "29.010"),
                ),
            ],
            [(54, "Triệu VND"), (55, "Triệu VND")],
        )
    )

    page = 78
    docs.append(
        _document(
            base,
            "MBB",
            page,
            [(59, "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1289,
                    page,
                    [
                        (
                            59,
                            "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
                        )
                    ],
                    (65, "4.508.464"),
                    (66, "12.260.320"),
                    "SOLE_VISIBLE_CHILD_IS_THE_FAMILY_TOTAL",
                ),
                _mapping(
                    base,
                    "OTHER_ASSETS",
                    1293,
                    page,
                    [(64, "Giấy tờ có giá")],
                    (65, "4.508.464"),
                    (66, "12.260.320"),
                    "GENERIC_VALUABLE_PAPERS_MAPPED_TO_CONTROLLED_SCHEMA_CATCHALL",
                ),
            ],
            [(62, "triệu đồng"), (63, "triệu đồng")],
        )
    )

    page = 74
    docs.append(
        _document(
            base,
            "VPB",
            page,
            [
                (
                    45,
                    "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
                ),
                (
                    46,
                    "Chi tiết các tài sản, giấy tờ có giá của Ngân hàng được đưa đi thế chấp, cầm cố, chiết khấu, tái",
                ),
                (
                    47,
                    "chiết khấu tại các TCTD khác và thiết lập hạn mức tại Ngân hàng Nhà nước vào thời điểm cuối",
                ),
                (48, "năm như sau:"),
            ],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1289,
                    page,
                    [
                        (
                            45,
                            "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
                        )
                    ],
                    (66, "19.709.750"),
                    (67, "13.644.923"),
                ),
                _mapping(
                    base,
                    "OTHER_ASSETS",
                    1293,
                    page,
                    [
                        (55, "Giấy tờ có giá đưa đi thế chấp, cầm cố"),
                        (59, "Giấy tờ có giá bán và cam kết mua lại"),
                        (63, "Tài sản khác đưa đi thế chấp, cầm cố"),
                    ],
                    _controlled_sum(
                        base,
                        page,
                        [(57, "6.741.000"), (61, "6.000.000"), (64, "6.968.750")],
                    ),
                    _controlled_sum(
                        base,
                        page,
                        [(58, "5.686.000"), (62, "2.000.000"), (65, "5.958.923")],
                    ),
                    "ALL_SOURCE_ROWS_AGGREGATED_ONCE_TO_CONTROLLED_SCHEMA_CATCHALL",
                ),
            ],
            [(53, "Triệu đồng"), (54, "Triệu đồng")],
        )
    )

    docs.extend([_absence("HDB"), _absence("VCB")])

    page = 63
    ctg_repo_comparative_dash = base.other._dash(
        page,
        [1367, 982, 1511, 1017],
        "af4f9a71cadae58e54fe8779abca11b0983d70169ee3562e2c12a267ba39e104",
    )
    docs.append(
        _document(
            base,
            "CTG",
            page,
            [(27, "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu")],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1289,
                    page,
                    [(27, "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu")],
                    (39, "17.256.980"),
                    (40, "20.381.856"),
                ),
                _mapping(
                    base,
                    "OTHER_ASSETS",
                    1293,
                    page,
                    [
                        (32, "Chứng khoán Nợ đưa đi cầm cố trong giao dịch vay cầm"),
                        (33, "cố các giấy tờ có giá"),
                        (36, "Chứng khoán Nợ đưa đi cầm cố trong giao dịch bán và"),
                        (37, "mua lại trái phiếu Chính phủ với Kho bạc Nhà nước"),
                    ],
                    _controlled_sum(base, page, [(34, "13.806.980"), (38, "3.450.000")]),
                    _controlled_sum(base, page, [(35, "20.381.856"), ctg_repo_comparative_dash]),
                    "ALL_SOURCE_ROWS_AGGREGATED_ONCE_TO_CONTROLLED_SCHEMA_CATCHALL",
                ),
            ],
            [(30, "Triệu đồng"), (31, "Triệu đồng")],
        )
    )

    docs.append(_absence("BID"))

    page = 54
    docs.append(
        _document(
            base,
            "VIB",
            page,
            [
                (
                    75,
                    "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu bởi Ngân hàng",
                )
            ],
            [
                _mapping(
                    base,
                    "FAMILY_TOTAL",
                    1289,
                    page,
                    [
                        (
                            75,
                            "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu bởi Ngân hàng",
                        )
                    ],
                    (86, "29.745.000"),
                    (87, "37.958.207"),
                ),
                _mapping(
                    base,
                    "OTHER_ASSETS",
                    1293,
                    page,
                    [
                        (80, "Giấy tờ có giá đưa đi thế chấp, cầm cố"),
                        (83, "Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu"),
                    ],
                    _controlled_sum(base, page, [(81, "10.587.000"), (84, "19.158.000")]),
                    _controlled_sum(base, page, [(82, "15.620.000"), (85, "22.338.207")]),
                    "ALL_SOURCE_ROWS_AGGREGATED_ONCE_TO_CONTROLLED_SCHEMA_CATCHALL",
                ),
            ],
            [(78, "triệu đồng"), (79, "triệu đồng")],
        )
    )

    expected = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
    if [item["bank_code"] for item in docs] != expected:
        raise _error("annual bank-pledged-assets document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.FAMILY_END_DISPLAY_ORDER = 873
    base.FAMILY_CHILD_TOTAL_EQUATION_NAME = (
        "ALL_VISIBLE_BANK_OWNED_PLEDGED_OR_DISCOUNTED_ASSET_CHILDREN_EQUAL_PARENT"
    )
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


def build_annual_2025_bank_pledged_assets_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        return _base().build_live_bank_pledged_assets_8bank_codex_verified_mapping_v1()
    except Annual2025BankPledgedAssets8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _base().validate_live_bank_pledged_assets_8bank_codex_verified_mapping_v1(value)
    except Annual2025BankPledgedAssets8BankError:
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
                build_annual_2025_bank_pledged_assets_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        RESULT_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_live_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_v1()
            )
        )
        return 0
    value, _ = _base()._stable_json(RESULT_PATH)
    validate_annual_2025_bank_pledged_assets_8bank_codex_verified_mapping_replay_v1(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
