"""Verify other long-term investments in eight audited annual-2025 PDFs.

This annual profile reuses the existing bank-blind complete-document graph and
the existing visible-pixel/PaddleOCR6 numeric evidence path.  It only adds
annual period wording, optional summary-to-detail continuation and multi-page
evidence for notes whose associate table continues on the next page.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
)

__all__ = [
    "Annual2025LongTermInvestments8BankError",
    "build_annual_2025_long_term_investments_pixel_review_blueprint_v1",
    "build_live_annual_2025_long_term_investments_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_long_term_investments_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_LONG_TERM_INVESTMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_LONG_TERM_INVESTMENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_LONG_TERM_INVESTMENTS_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025lti8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_LONG_TERM_INVESTMENTS_CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025lti8bcv1:pixel-review:"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0122-annual-2025-long-term-investments-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0122-annual-2025-long-term-investments-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "ltifdsv1:scan:1749d4cb64d38971e55989817287de553698967c513d323e7bc1c39427ab9e4a"
EXPECTED_REVIEW_SHA256 = "7914eeeba56726cb354812e5c39906e4d5df1678eae7bd371713d78905690254"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")

_EXPECTED_IDS = {
    "ACB": {862, 867, 5959, 5960},
    "MBB": {862, 867, 5959, 5960, 5961},
    "VPB": {5960},
    "HDB": {862, 867, 5959, 6067},
    "VCB": {6066, 6067},
    "CTG": {862, 867, 5959, 6066},
    "BID": {862, 867, 5959, 6066, 6067},
    "VIB": {862, 867, 5959},
}

_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_GENERIC_OTHER_LONG_TERM_INVESTMENT_WHOLE_PDF_UNIQUENESS_"
    "OPTIONAL_JOINT_VENTURE_ASSOCIATE_ORGANIZATION_PROJECT_FUND_SUMMARY_"
    "DETAIL_CONTINUATION_VISIBLE_PIXEL_PPOCRV6_NUMERIC_EXACT_ACCOUNTING_"
    "AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "OWNER_PRECEDES_ACCOUNTING_CHILDREN",
    "OPTIONAL_SUMMARY_DETAIL_AND_CONTINUATION_BRANCHES",
    "ANNUAL_CURRENT_AND_COMPARATIVE_PERIOD_AXES",
    "MILLION_VND_UNIT_VISIBLE_OR_DOCUMENT_INHERITED",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGN_AND_DASH",
    "PPOCRV6_NUMERIC_CHALLENGER_MATCHES_VISIBLE_PIXEL",
    "PARENT_CHILD_AND_NET_ACCOUNTING_CLOSURE",
    "DETAIL_TABLE_NOT_DOUBLE_COUNTED_WITH_PARENT",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_coerced_to_zero": False,
    "comparison_period_used_as_mapping_authority": False,
    "dash_coerced_to_zero_only_when_visible_in_pdf": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_PPOCRV6_NUMERIC_CHALLENGER",
    "optional_children_required_in_every_bank": False,
    "source_detail_rows_double_counted_with_parent": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "independent_pdf_pixel_and_ppocrv6_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_eight_unique_annual_long_term_investment_regions": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_detail_rows_double_counted_with_parent": False,
    "text_similarity_alone_used_for_mapping": False,
}


class Annual2025LongTermInvestments8BankError(ValueError):
    """The annual graph, visible pixels, numbers, equations or schema drifted."""


def _error(message: str) -> Annual2025LongTermInvestments8BankError:
    return Annual2025LongTermInvestments8BankError(message)


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
    mapping = base._mapping
    equation = base._equation
    document = base._doc

    docs: dict[str, dict[str, Any]] = {}
    docs["ACB"] = document(
        "ACB",
        54,
        5,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                867, "OTHER_LONG_TERM", 14, "Đầu tư dài hạn khác", (16, "233.739"), (17, "292.867")
            ),
            mapping(
                5960,
                "ORGANIZATION_PROJECT",
                30,
                "Đầu tư vào các TCKT trong nước",
                (37, "233.739"),
                (38, "292.867"),
                topology="OWNER_DETAIL_SUBTOTAL",
            ),
            mapping(
                5959,
                "PROVISION",
                18,
                "Dự phòng giảm giá đầu tư dài hạn",
                (20, "(159.040)"),
                (21, "(167.932)"),
            ),
            mapping(
                862,
                "NET_TOTAL",
                None,
                None,
                (22, "74.699"),
                (23, "124.935"),
                topology="UNLABELED_TRAILING_NET_TOTAL",
            ),
        ],
        [
            equation(
                "ACB_LISTED_AND_UNLISTED_TO_ORGANIZATION_SUBTOTAL",
                [(32, "177.739"), (35, "56.000")],
                (37, "233.739"),
                [(33, "181.339"), (36, "111.528")],
                (38, "292.867"),
            ),
            equation(
                "ACB_OTHER_PLUS_PROVISION_TO_NET",
                [(16, "233.739"), (20, "(159.040)")],
                (22, "74.699"),
                [(17, "292.867"), (21, "(167.932)")],
                (23, "124.935"),
            ),
        ],
    )
    docs["MBB"] = document(
        "MBB",
        57,
        10,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                867, "OTHER_LONG_TERM", 15, "Đầu tư dài hạn khác", (16, "559.624"), (17, "775.670")
            ),
            mapping(
                5960,
                "ORGANIZATION_PROJECT",
                29,
                "Đầu tư vào các tổ chức kinh tế, đầu tư vào các dự án dài hạn",
                (31, "493.184"),
                (32, "687.266"),
                topology="OWNER_DETAIL_CHILD",
            ),
            mapping(
                5961,
                "INVESTMENT_FUND",
                33,
                "Đầu tư vào các quỹ đầu tư",
                (34, "66.440"),
                (35, "88.404"),
                topology="OWNER_DETAIL_CHILD",
            ),
            mapping(
                5959,
                "PROVISION",
                18,
                "Dự phòng giảm giá đầu tư dài hạn",
                (19, "(91.228)"),
                (20, "(166.193)"),
            ),
            mapping(
                862,
                "NET_TOTAL",
                None,
                None,
                (21, "468.396"),
                (22, "609.477"),
                topology="UNLABELED_TRAILING_NET_TOTAL",
            ),
        ],
        [
            equation(
                "MBB_ORGANIZATION_AND_FUND_TO_OTHER_LONG_TERM",
                [(31, "493.184"), (34, "66.440")],
                (36, "559.624"),
                [(32, "687.266"), (35, "88.404")],
                (37, "775.670"),
            ),
            equation(
                "MBB_OTHER_PLUS_PROVISION_TO_NET",
                [(16, "559.624"), (19, "(91.228)")],
                (21, "468.396"),
                [(17, "775.670"), (20, "(166.193)")],
                (22, "609.477"),
            ),
        ],
    )
    docs["VPB"] = document(
        "VPB",
        52,
        57,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                5960,
                "ORGANIZATION_PROJECT",
                66,
                "Đầu tư vào tổ chức kinh tế",
                (82, "191.960"),
                (83, "189.210"),
                topology="OWNER_ORGANIZATION_COMPONENTS_TO_SUBTOTAL",
            )
        ],
        [
            equation(
                "VPB_THREE_ORGANIZATIONS_TO_TOTAL",
                [(68, "3.934"), (73, "185.276"), (80, "2.750")],
                (82, "191.960"),
                [(70, "3.934"), (75, "185.276"), (None, "-")],
                (83, "189.210"),
                comparative_dash_anchor_line_index=79,
            )
        ],
    )
    docs["HDB"] = document(
        "HDB",
        41,
        8,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                6067,
                "ASSOCIATE",
                14,
                "Đầu tư vào công ty liên kết",
                (15, "1.040.690"),
                (16, "729.739"),
            ),
            mapping(
                867,
                "OTHER_LONG_TERM",
                17,
                "Các khoản đầu tư dài hạn khác",
                (18, "125.667"),
                (19, "146.546"),
            ),
            mapping(
                5959,
                "PROVISION",
                23,
                "Dự phòng giảm giá các khoản đầu tư dài hạn khác",
                (24, "(8.173)"),
                (25, "(18.502)"),
            ),
            mapping(
                862,
                "NET_TOTAL",
                None,
                None,
                (26, "1.158.184"),
                (27, "857.783"),
                topology="UNLABELED_TRAILING_NET_TOTAL",
            ),
        ],
        [
            equation(
                "HDB_ASSOCIATE_OTHER_PROVISION_TO_NET",
                [(15, "1.040.690"), (18, "125.667"), (24, "(8.173)")],
                (26, "1.158.184"),
                [(16, "729.739"), (19, "146.546"), (25, "(18.502)")],
                (27, "857.783"),
            )
        ],
    )
    docs["VCB"] = document(
        "VCB",
        44,
        9,
        "Góp vốn, đầu tư dài hạn",
        "2025-12-31",
        [
            mapping(
                6066,
                "JOINT_VENTURE",
                11,
                "Vốn góp liên doanh",
                (37, "734.296"),
                (66, "763.736"),
                topology="OWNER_JOINT_VENTURE_CARRYING_VALUE_TOTAL",
            ),
            mapping(
                6067,
                "ASSOCIATE",
                9,
                "Đầu tư vào công ty liên kết",
                (28, "12.342"),
                (46, "10.440"),
                topology="CONTINUATION_PAGE_ASSOCIATE_CARRYING_VALUE_TOTAL",
                page_sequence=45,
            ),
        ],
        [
            equation(
                "VCB_TWO_JOINT_VENTURES_TO_CARRYING_TOTAL",
                [(28, "564.109"), (35, "170.187")],
                (37, "734.296"),
                [(53, "537.445"), (61, "226.291")],
                (66, "763.736"),
            ),
            equation(
                "VCB_ASSOCIATE_ROW_TO_CARRYING_TOTAL",
                [(26, "12.342")],
                (28, "12.342"),
                [(44, "10.440")],
                (46, "10.440"),
                page_sequence=45,
            ),
        ],
    )
    docs["CTG"] = document(
        "CTG",
        47,
        5,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                6066,
                "JOINT_VENTURE",
                12,
                "Vốn góp liên doanh",
                (13, "4.193.834"),
                (14, "3.706.673"),
            ),
            mapping(
                867,
                "OTHER_LONG_TERM",
                15,
                "Các khoản đầu tư dài hạn khác",
                (16, "234.462"),
                (17, "234.462"),
            ),
            mapping(
                5959,
                "PROVISION",
                18,
                "Trừ: Dự phòng giảm giá đầu tư dài hạn",
                (None, "-"),
                (19, "(7.291)"),
                dash_anchor_line_index=18,
            ),
            mapping(
                862,
                "NET_TOTAL",
                None,
                None,
                (20, "4.428.296"),
                (21, "3.933.844"),
                topology="UNLABELED_TRAILING_NET_TOTAL",
            ),
        ],
        [
            equation(
                "CTG_JOINT_OTHER_PROVISION_TO_NET",
                [(13, "4.193.834"), (16, "234.462"), (None, "-")],
                (20, "4.428.296"),
                [(14, "3.706.673"), (17, "234.462"), (19, "(7.291)")],
                (21, "3.933.844"),
                dash_anchor_line_index=18,
            )
        ],
    )
    docs["BID"] = document(
        "BID",
        45,
        46,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                6066,
                "JOINT_VENTURE",
                51,
                "Các khoản đầu tư vào công ty liên doanh",
                (52, "3.083.714"),
                (53, "2.608.671"),
            ),
            mapping(
                6067,
                "ASSOCIATE",
                54,
                "Các khoản đầu tư vào công ty liên kết",
                (55, "1.211.083"),
                (56, "739.841"),
            ),
            mapping(
                867,
                "OTHER_LONG_TERM",
                57,
                "Các khoản đầu tư dài hạn khác",
                (58, "183.050"),
                (59, "182.914"),
            ),
            mapping(
                5959,
                "PROVISION",
                60,
                "Dự phòng giảm giá đầu tư dài hạn khác",
                (61, "(104.203)"),
                (62, "(107.832)"),
            ),
            mapping(
                862,
                "NET_TOTAL",
                None,
                None,
                (63, "4.373.644"),
                (64, "3.423.594"),
                topology="UNLABELED_TRAILING_NET_TOTAL",
            ),
        ],
        [
            equation(
                "BID_JOINT_ASSOCIATE_OTHER_PROVISION_TO_NET",
                [
                    (52, "3.083.714"),
                    (55, "1.211.083"),
                    (58, "183.050"),
                    (61, "(104.203)"),
                ],
                (63, "4.373.644"),
                [
                    (53, "2.608.671"),
                    (56, "739.841"),
                    (59, "182.914"),
                    (62, "(107.832)"),
                ],
                (64, "3.423.594"),
            )
        ],
    )
    docs["VIB"] = document(
        "VIB",
        41,
        29,
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "2025-12-31",
        [
            mapping(
                867,
                "OTHER_LONG_TERM",
                34,
                "Đầu tư dài hạn khác",
                (35, "69.667"),
                (36, "69.667"),
            ),
            mapping(
                5959,
                "PROVISION",
                39,
                "Dự phòng giảm giá góp vốn, đầu tư dài hạn",
                (37, "(210)"),
                (38, "(210)"),
                topology="OWNER_VALUES_PRECEDE_TRAILING_LABEL",
            ),
            mapping(
                862,
                "NET_TOTAL",
                None,
                None,
                (40, "69.457"),
                (41, "69.457"),
                topology="UNLABELED_TRAILING_NET_TOTAL",
            ),
        ],
        [
            equation(
                "VIB_OTHER_PLUS_PROVISION_TO_NET",
                [(35, "69.667"), (37, "(210)")],
                (40, "69.457"),
                [(36, "69.667"), (38, "(210)")],
                (41, "69.457"),
            )
        ],
    )
    return [docs[code] for code in EXPECTED_DOCUMENT_ORDER]


def _annual_metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "dash_cell_normalized_to_zero_count": sum(
            value["pixel_transcription"] == "-"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_expected_ids(result: dict[str, Any]) -> dict[str, Any]:
    for trial, code in zip(result["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        ids = {item["schema_binding"]["report_norm_id"] for item in trial["verified_mappings"]}
        if ids != _EXPECTED_IDS[code]:
            raise _error(f"annual long-term-investment mapping set drifted for {code}")
    return result


def _base() -> ModuleType:
    base = _load_module(
        "annual_2025_long_term_investments_base_v1",
        "scripts/experiments/build_long_term_investments_8bank_codex_verified_mapping_v1.py",
    )
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base._RESULT_STATE = RESULT_STATE
    base._RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base._REVIEW_STATE = REVIEW_STATE
    base._REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base._REVIEW_RUN_ID = "annual-2025-long-term-investments-eight-bank-review-2026-08-17"
    base.CLAIM_BOUNDARY = _CLAIM_BOUNDARY
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.REVIEW_SHA256 = EXPECTED_REVIEW_SHA256
    base._SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": "VERIFIED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
    }
    base._TRIAL_STATUS_BY_SOURCE_PERIOD_STATUS = {
        "VERIFIED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS": "VERIFIED_BY_CODEX"
    }
    base._REVIEW_CHECKS = list(_REVIEW_CHECKS)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._metrics = _annual_metrics
    base._review_documents = lambda: _review_documents(base)
    base.scanner.MATCHER_VARIANT_PROFILE = "ANNUAL_2025_V1"
    return base


def build_annual_2025_long_term_investments_pixel_review_blueprint_v1() -> dict[str, Any]:
    """Return the fixed annual visible-pixel review ledger."""

    return _base()._review_blueprint()


def build_live_annual_2025_long_term_investments_8bank_codex_verified_mapping_v1() -> dict[
    str, Any
]:
    """Replay all annual inputs and build the bounded eight-bank result."""

    try:
        return _validate_expected_ids(
            _base().build_live_long_term_investments_8bank_codex_verified_mapping_v1()
        )
    except Annual2025LongTermInvestments8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def validate_annual_2025_long_term_investments_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the annual result and reject coordinated rehashes."""

    try:
        return _validate_expected_ids(
            _base().validate_live_long_term_investments_8bank_codex_verified_mapping_v1(value)
        )
    except Annual2025LongTermInvestments8BankError:
        raise
    except Exception as error:
        raise _error(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_annual_2025_long_term_investments_pixel_review_blueprint_v1()
            )
        )
        return 0
    if args.write_result:
        result = build_live_annual_2025_long_term_investments_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    if args.verify:
        value, _ = _base()._stable_json(RESULT_PATH)
        result = validate_annual_2025_long_term_investments_8bank_codex_verified_mapping_replay_v1(
            value
        )
        print(result["result_id"])
        return 0
    parser.error("choose exactly one action")


if __name__ == "__main__":
    raise SystemExit(main())
