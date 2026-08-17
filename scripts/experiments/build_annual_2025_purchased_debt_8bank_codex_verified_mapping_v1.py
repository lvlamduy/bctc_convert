"""Verify purchased-debt disclosures in eight annual-2025 bank PDFs.

This annual profile reuses the bank-blind full-document purchased-debt graph.
It binds the four unique regions to visible pixels, PaddleOCR6 numeric
challengers, annual period/unit axes, exact accounting equations and the live
TM schema.  Interest and foreign-currency rows remain optional family
branches; their absence is never filled from another bank.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

__all__ = [
    "Annual2025PurchasedDebt8BankError",
    "build_annual_2025_purchased_debt_pixel_review_blueprint_v1",
    "build_live_annual_2025_purchased_debt_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_purchased_debt_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_PURCHASED_DEBT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_PURCHASED_DEBT_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_PURCHASED_DEBT_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025pd8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_PURCHASED_DEBT_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025pd8bcv1:pixel-review:"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0120-annual-2025-purchased-debt-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0120-annual-2025-purchased-debt-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_SCAN_ID = "pdfdsv1:scan:874bf428575b2702e0b19879baa481341483d51bfd385bf53193b8ffb423e38f"
EXPECTED_REVIEW_SHA256 = "7de507f10887c8eff157628d8e697d9a606e890ea86703e9e07c39aa5362a9c6"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_MAPPED_CODES = {"MBB", "VPB", "HDB", "VIB"}
_ABSENT_CODES = set(EXPECTED_DOCUMENT_ORDER) - _MAPPED_CODES
_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "GENERIC_PURCHASED_DEBT_WHOLE_PDF_UNIQUENESS_OPTIONAL_INTEREST_OR_FOREIGN_"
    "CURRENCY_VISIBLE_PIXEL_PPOCRV6_NUMERIC_CHALLENGER_EXACT_ACCOUNTING_AND_"
    "LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_coerced_to_zero": False,
    "dash_coerced_to_zero_only_when_visible_in_pdf": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "historical_or_optional_branch_mapped_into_current_core": False,
    "mapping_decided_by_text_similarity_alone": False,
    "source_order_and_cluster_boundaries_required": True,
    "visible_pdf_pixels_and_ppocrv6_used_for_numeric_truth": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_absence_authority": True,
    "broad_corpus_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_and_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_four_unique_annual_purchased_debt_regions": True,
    "optional_quality_provision_movement_or_historical_mapping_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
}


class Annual2025PurchasedDebt8BankError(ValueError):
    """The annual purchased-debt graph, pixels, numbers or schema drifted."""


def _error(message: str) -> Annual2025PurchasedDebt8BankError:
    return Annual2025PurchasedDebt8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents = {code: base._absent(code) for code in _ABSENT_CODES}
    documents["MBB"] = {
        "bank_code": "MBB",
        "checks": base._checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": base._boundary(
            (54, 10, "HOẠT ĐỘNG MUA NỢ"),
            (54, 32, "Lãi của khoản nợ đã mua"),
            (54, 37, "CHỨNG KHOÁN ĐẦU TƯ"),
        ),
        "layout": "ROWS_BY_ITEM_COLUMNS_BY_ANNUAL_DATE",
        "optional_equations": [],
        "pages": [
            base._page_review(
                54,
                "bff8e9dbff90c73a720eb7599a481e61a264a67dcc16b838404983a8c2c478a6",
                "TWO_ANNUAL_DATE_COLUMNS_SHARED_ROW_AXIS",
                [
                    base._period("CURRENT", "2025-12-31", [(11, "31/12/2025")], (13, "triệu đồng")),
                    base._period(
                        "COMPARATIVE", "2024-12-31", [(12, "31/12/2024")], (14, "triệu đồng")
                    ),
                ],
                [
                    base._row(
                        "PURCHASE_VND",
                        801,
                        15,
                        "Mua nợ bằng VND",
                        base._line(16, "2.465.314"),
                        base._line(17, "1.041.362"),
                    ),
                    base._row(
                        "PROVISION",
                        803,
                        18,
                        "Dự phòng rủi ro",
                        base._line(19, "(21.419)"),
                        base._line(20, "(89.853)"),
                    ),
                    base._row(
                        "PRINCIPAL",
                        5738,
                        29,
                        "Nợ gốc đã mua",
                        base._line(30, "2.465.314"),
                        base._line(31, "1.041.069"),
                    ),
                    base._row(
                        "INTEREST",
                        5739,
                        32,
                        "Lãi của khoản nợ đã mua",
                        base._dash([1050, 868, 1265, 912]),
                        base._line(33, "293"),
                    ),
                ],
                [base._line(21, "2.443.895"), base._line(22, "951.509")],
                [base._line(34, "2.465.314"), base._line(35, "1.041.362")],
            )
        ],
    }
    documents["VPB"] = {
        "bank_code": "VPB",
        "checks": base._checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": base._boundary(
            (49, 5, "HOẠT ĐỘNG MUA NỢ"),
            (49, 30, "Lãi của khoản nợ đã mua và chênh lệch giá mua nợ"),
            (50, 5, "CHỨNG KHOÁN ĐẦU TƯ"),
        ),
        "layout": "ROWS_BY_ITEM_SPLIT_ANNUAL_DATE_HEADER_WITH_OPTIONAL_TABLES",
        "optional_equations": [
            base._optional_equation(
                "CURRENT_PROVISION_MOVEMENT_CHECK_ONLY",
                49,
                "3e134e16f49f56ea2a8b850c17f981f35e9c03ac633ed93b27268263d579ab59",
                [base._line(53, "6.044"), base._line(57, "4.168")],
                base._line(60, "10.212"),
            ),
            base._optional_equation(
                "COMPARATIVE_PROVISION_MOVEMENT_CHECK_ONLY",
                49,
                "3e134e16f49f56ea2a8b850c17f981f35e9c03ac633ed93b27268263d579ab59",
                [base._line(54, "6.210"), base._line(58, "(166)")],
                base._line(61, "6.044"),
            ),
        ],
        "pages": [
            base._page_review(
                49,
                "3e134e16f49f56ea2a8b850c17f981f35e9c03ac633ed93b27268263d579ab59",
                "TWO_ANNUAL_DATE_COLUMNS_SPLIT_OVER_TWO_HEADER_LINES",
                [
                    base._period(
                        "CURRENT",
                        "2025-12-31",
                        [(6, "Ngày 31 tháng 12"), (8, "năm 2025")],
                        (10, "Triệu đồng"),
                    ),
                    base._period(
                        "COMPARATIVE",
                        "2024-12-31",
                        [(7, "Ngày 31 tháng 12"), (9, "năm 2024")],
                        (11, "Triệu đồng"),
                    ),
                ],
                [
                    base._row(
                        "PURCHASE_VND",
                        801,
                        12,
                        "Mua nợ bằng VND",
                        base._line(13, "1.361.635"),
                        base._line(14, "805.869"),
                    ),
                    base._row(
                        "PROVISION",
                        803,
                        15,
                        "Dự phòng rủi ro hoạt động mua nợ",
                        base._line(16, "(10.212)"),
                        base._line(17, "(6.044)"),
                    ),
                    base._row(
                        "PRINCIPAL",
                        5738,
                        27,
                        "Nợ gốc đã mua",
                        base._line(28, "1.356.908"),
                        base._line(29, "805.869"),
                    ),
                    base._row(
                        "INTEREST",
                        5739,
                        30,
                        "Lãi của khoản nợ đã mua và chênh lệch giá mua nợ",
                        base._line(32, "4.727"),
                        base._dash([1245, 824, 1485, 904]),
                    ),
                ],
                [base._line(18, "1.351.423"), base._line(19, "799.825")],
                [base._line(33, "1.361.635"), base._line(34, "805.869")],
            )
        ],
    }
    documents["HDB"] = {
        "bank_code": "HDB",
        "checks": base._checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": base._boundary(
            (39, 8, "HOẠT ĐỘNG MUA NỢ"),
            (39, 23, "Nợ gốc đã mua"),
            (39, 35, "CHỨNG KHOÁN ĐẦU TƯ"),
        ),
        "layout": "ROWS_BY_ITEM_COLUMNS_BY_RELATIVE_ANNUAL_PERIOD_WITH_OPTIONAL_INTEREST_ABSENT",
        "optional_equations": [],
        "pages": [
            base._page_review(
                39,
                "548718289b9148db34e90938512495b68f4f2fbed7395d66bae3b25dbc4fd690",
                "CURRENT_AND_OPENING_YEAR_COLUMNS_WITH_VISIBLE_DASH_COMPARATIVES",
                [
                    base._period("CURRENT", "2025-12-31", [(9, "Số cuối năm")], (11, "Triệu VND")),
                    base._period(
                        "COMPARATIVE", "2024-12-31", [(10, "Số đầu năm")], (12, "Triệu VND")
                    ),
                ],
                [
                    base._row(
                        "PURCHASE_VND",
                        801,
                        13,
                        "Mua nợ bằng VND",
                        base._line(14, "23.925.869"),
                        base._dash([1290, 410, 1495, 453]),
                    ),
                    base._row(
                        "PROVISION",
                        803,
                        15,
                        "Dự phòng chung",
                        base._line(16, "(179.444)"),
                        base._dash([1290, 444, 1495, 488]),
                    ),
                    base._row(
                        "PRINCIPAL",
                        5738,
                        23,
                        "Nợ gốc đã mua",
                        base._line(24, "23.925.869"),
                        base._dash([1290, 676, 1495, 719]),
                    ),
                ],
                [base._line(17, "23.746.425"), base._dash([1290, 482, 1495, 522])],
                [base._line(25, "23.925.869"), base._dash([1290, 716, 1495, 755])],
            )
        ],
    }
    documents["VIB"] = {
        "bank_code": "VIB",
        "checks": base._checks(True),
        "disposition": "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION",
        "family_boundary": base._boundary(
            (40, 5, "HOẠT ĐỘNG MUA NỢ"),
            (40, 44, "Lãi từ các khoản nợ đã mua"),
            (40, 49, "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN"),
        ),
        "layout": "HISTORICAL_ACQUISITION_BLOCK_THEN_CURRENT_ANNUAL_TWO_COLUMN_BALANCE",
        "optional_equations": [
            base._optional_equation(
                "HISTORICAL_2017_ACQUISITION_CHECK_ONLY",
                40,
                "31e7c3a92bf012ed0aa0da07f9b2e70d89555d166c0afb745aca8e5c199b07ce",
                [base._line(13, "1.147.463"), base._line(15, "3.426"), base._line(17, "(18.940)")],
                base._line(18, "1.131.949"),
            )
        ],
        "pages": [
            base._page_review(
                40,
                "31e7c3a92bf012ed0aa0da07f9b2e70d89555d166c0afb745aca8e5c199b07ce",
                "HISTORICAL_VERTICAL_BLOCK_PLUS_TWO_ANNUAL_DATE_COLUMNS",
                [
                    base._period("CURRENT", "2025-12-31", [(21, "31/12/2025")], (23, "triệu đồng")),
                    base._period(
                        "COMPARATIVE", "2024-12-31", [(22, "31/12/2024")], (24, "triệu đồng")
                    ),
                ],
                [
                    base._row(
                        "PURCHASE_VND",
                        801,
                        25,
                        "Mua nợ bằng VND",
                        base._line(26, "4.366"),
                        base._line(27, "8.846"),
                    ),
                    base._row(
                        "PROVISION",
                        803,
                        30,
                        "Dự phòng rủi ro mua nợ",
                        base._line(28, "(34)"),
                        base._line(29, "(67)"),
                    ),
                    base._row(
                        "PRINCIPAL",
                        5738,
                        39,
                        "Nợ gốc đã mua",
                        base._line(40, "4.477"),
                        base._line(41, "8.956"),
                    ),
                    base._row(
                        "INTEREST",
                        5739,
                        44,
                        "Lãi từ các khoản nợ đã mua",
                        base._line(42, "20"),
                        base._line(43, "52"),
                    ),
                ],
                [base._line(31, "4.332"), base._line(32, "8.779")],
                [base._line(45, "4.497"), base._line(46, "9.008")],
            )
        ],
    }
    return [documents[code] for code in EXPECTED_DOCUMENT_ORDER]


def _base() -> ModuleType:
    base = _load_module(
        "annual_2025_purchased_debt_base_v1",
        "scripts/experiments/build_purchased_debt_8bank_codex_verified_mapping_v1.py",
    )
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.CLAIM_BOUNDARY = _CLAIM_BOUNDARY
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.REVIEW_SHA256 = EXPECTED_REVIEW_SHA256
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._REVIEW_RUN_ID = "annual-2025-purchased-debt-eight-bank-pixel-review-2026-08-17"
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._review_documents = lambda: _review_documents(base)
    _install_primary_numeric_challenger(base)
    return base


def _strict_provider(payload: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(f"{label} is not strict JSON") from error
    if type(value) is not dict:
        raise _error(f"{label} root must be one object")
    return value


def _install_primary_numeric_challenger(base: ModuleType) -> None:
    original = base._money_evidence
    cache: dict[str, dict[str, Any]] = {}

    def provider(manifest_document: Mapping[str, Any], page_number: int) -> dict[str, Any]:
        manifest_page = base._page(manifest_document, page_number, "crop manifest")
        ref = manifest_page.get("result_ref")
        if (
            type(ref) is not dict
            or type(ref.get("path")) is not str
            or type(ref.get("sha256")) is not str
        ):
            raise _error("PaddleOCR6 result ref drifted")
        path = ref["path"]
        if path not in cache:
            payload = base.support._stable_bytes(Path(path))
            if hashlib.sha256(payload).hexdigest() != ref["sha256"]:
                raise _error("PaddleOCR6 result bytes drifted")
            cache[path] = _strict_provider(payload, path)
        return cache[path]

    def money_evidence(
        semantic_document: Mapping[str, Any],
        manifest_document: Mapping[str, Any],
        page_number: int,
        spec: Mapping[str, Any],
        render_sha256: str,
    ) -> dict[str, Any]:
        evidence = original(
            semantic_document,
            manifest_document,
            page_number,
            spec,
            render_sha256,
        )
        index = spec.get("line_index")
        if index is None:
            evidence["primary_numeric_challenger"] = {
                "raw_text": None,
                "source_line_index": None,
                "status": "VISIBLE_PIXEL_DASH_WITH_NO_PROVIDER_TEXT_LINE",
            }
            return evidence
        result = provider(manifest_document, page_number)
        texts = result.get("rec_texts")
        boxes = result.get("rec_boxes")
        if (
            type(index) is not int
            or type(texts) is not list
            or type(boxes) is not list
            or len(texts) != len(boxes)
            or not 0 <= index < len(texts)
            or type(texts[index]) is not str
            or boxes[index] != evidence["source_bbox_raw_pixels"]
        ):
            raise _error("PaddleOCR6 numeric line axis drifted")
        try:
            challenger_value = base.support._money(texts[index])
        except Exception as error:
            raise _error("PaddleOCR6 numeric challenger is not an exact money value") from error
        if challenger_value != evidence["normalized_value"]:
            raise _error("visible pixel and PaddleOCR6 numeric challenger disagree")
        evidence["primary_numeric_challenger"] = {
            "raw_text": texts[index],
            "source_line_index": index,
            "status": "PPOCRV6_NUMERIC_CHALLENGER_MATCHED_VISIBLE_PIXEL",
        }
        return evidence

    base._money_evidence = money_evidence


def build_annual_2025_purchased_debt_pixel_review_blueprint_v1() -> dict[str, Any]:
    """Return the fixed independent visible-page review."""

    return _base()._review_blueprint()


def build_live_annual_2025_purchased_debt_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay every fixed annual input and build the bounded mapping result."""

    return _base().build_live_purchased_debt_8bank_codex_verified_mapping_v1()


def validate_annual_2025_purchased_debt_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the annual purchased-debt result."""

    return _base().validate_purchased_debt_8bank_codex_verified_mapping_replay_v1(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(build_annual_2025_purchased_debt_pixel_review_blueprint_v1())
        )
        return 0
    result = build_live_annual_2025_purchased_debt_8bank_codex_verified_mapping_v1()
    if args.verify:
        persisted = json.loads((PROJECT_ROOT / RESULT_PATH).read_text(encoding="utf-8"))
        validate_annual_2025_purchased_debt_8bank_codex_verified_mapping_replay_v1(persisted)
        return 0
    if args.write_result:
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
