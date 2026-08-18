"""Seal annual-2025 absence of a numeric combined-securities net row.

The existing complete-PDF graph distinguishes a numeric summary row from a
section heading.  The audited annual reports contain no numeric row for TM
5990.  BID has one combined-family heading followed by separate trading and
investment subsections; it is retained as an explicit negative control rather
than promoted to a value-bearing row.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_COMBINED_SECURITIES_NET_8BANK_BOUND_REPORT_ABSENCE_V1"
REVIEW_FORMAT = "ANNUAL_2025_COMBINED_SECURITIES_NET_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_COMBINED_SECURITIES_NET_BOUND_REPORT_ABSENCE_COMPLETE"
RESULT_ID_PREFIX = "annual2025csn8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_COMBINED_SECURITIES_NET_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025csn8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0141"
REVIEW_PATH = Path(
    "docs/experiments/E-0141-annual-2025-combined-securities-net-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0141-annual-2025-combined-securities-net-8bank-bound-report-absence-v1.json"
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
EXPECTED_SCAN_ID = "csnfdsv1:scan:fcc954ca8ef0c7a3b74ad724e11d29fb8f93bfbcfda6ce78f0dc610e33824bc0"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_COMBINED_TRADING_AND_INVESTMENT_SECURITIES_NET_"
    "NUMERIC_ROW_ABSENCE_BID_SECTION_HEADING_NEGATIVE_CONTROL_AND_LIVE_"
    "TM_SCHEMA_ONLY_NO_OTHER_PERIOD_CORPUS_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "absence_claim_bounded_to_exact_annual_2025_reports": True,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_period_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "section_heading_without_same_row_values_accepted": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "component_equation_claimed_without_combined_numeric_row": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "paddleocr_source_axis_used_as_semantic_anchor": False,
    "section_heading_confused_with_numeric_total_row": False,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}
_EXPECTED_METRICS = {
    "accounting_equation_verified_count": 0,
    "combined_net_not_present_document_count": 8,
    "document_count": 8,
    "document_unique_region_count": 0,
    "mapping_verified_count": 0,
    "open_source_row_count": 0,
    "verified_value_cell_count": 0,
}
_PAGE_COUNTS = {
    "ACB": 100,
    "MBB": 103,
    "VPB": 100,
    "HDB": 71,
    "VCB": 84,
    "CTG": 85,
    "BID": 74,
    "VIB": 78,
}


class Annual2025CombinedSecuritiesNetAbsenceV1Error(ValueError):
    """The annual structure scan, negative control, schema or replay drifted."""


def _error(message: str) -> Annual2025CombinedSecuritiesNetAbsenceV1Error:
    return Annual2025CombinedSecuritiesNetAbsenceV1Error(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_combined_securities_net_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_combined_securities_net_base"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load combined-securities support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    documents = []
    for code in EXPECTED_DOCUMENT_ORDER:
        negative_controls = []
        if code == "BID":
            negative_controls.append(
                {
                    "disposition": "SECTION_HEADING_WITHOUT_SAME_ROW_MONETARY_VALUES",
                    "label_lines": [
                        base._ref(
                            56,
                            4,
                            "LÃI THUẦN TỪ MUA BÁN CHỨNG KHOÁN KINH DOANH VÀ CHỨNG KHOÁN ĐẦU TƯ",
                        )
                    ],
                    "page_span": [56, 56],
                    "reason": (
                        "This is a section umbrella followed by distinct trading and "
                        "investment subsections, not a numeric TM 5990 row."
                    ),
                }
            )
        documents.append(
            {
                "absence_evidence": {
                    "combined_net_numeric_row_match_count": 0,
                    "complete_pdf_page_count": _PAGE_COUNTS[code],
                    "complete_pdf_pages_scanned": True,
                    "near_section_heading_match_count": len(negative_controls),
                    "negative_controls": negative_controls,
                    "reason": (
                        "The bound annual report has no complete combined trading-and-"
                        "investment securities net label with two same-row period values."
                    ),
                    "source_scope_absence_only": True,
                },
                "bank_code": code,
                "label_lines": [],
                "page_span": None,
                "period_axis": [],
                "presentation": "NO_COMBINED_SECURITIES_NET_NUMERIC_ROW_IN_BOUND_REPORT",
                "unit_evidence": [],
                "values": {},
            }
        )
    return documents


def _configure(base: ModuleType) -> None:
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base.SCHEMA_FAMILY_END_DISPLAY_ORDER = 757
    base.REQUIRE_COMPONENT_RESULTS = False
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base._SCHEMA_EXPECTED = (
        "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư",
        1142,
        757,
    )
    base._AUTHORITY = dict(_AUTHORITY)
    base._REVIEW_SAFETY = dict(_REVIEW_SAFETY)
    base._review_documents = lambda: _review_documents(base)


def _inputs() -> tuple[ModuleType, dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = _load_base()
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = base.scanner.build_combined_securities_net_full_document_scan_v1(
        semantic_index
    )
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual combined-securities scan identity drifted")
    _configure(base)
    return base, semantic_index, crop_manifest, structure_scan


def _assert_result(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("metrics") != _EXPECTED_METRICS:
        raise _error("annual combined-securities absence metrics drifted")
    if value.get("schema_family") != {
        "family_end_display_order": 757,
        "family_root_report_norm_id": 5990,
        "mapped_report_norm_ids": [],
    }:
        raise _error("annual combined-securities schema family drifted")
    for trial, code in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        evidence = trial["absence_evidence"]
        expected_near = 1 if code == "BID" else 0
        if (
            trial["document_provenance"] != code
            or trial["status"] != "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            or trial["page_span"] is not None
            or trial["verified_mappings"] != []
            or trial["verified_accounting_equations"] != []
            or evidence["complete_pdf_page_count"] != _PAGE_COUNTS[code]
            or evidence["near_section_heading_match_count"] != expected_near
            or len(evidence["negative_controls"]) != expected_near
            or trial["whole_document_uniqueness"]
            != {"complete_region_count": 0, "status": "NOT_UNIQUE_FULL_MATCH"}
        ):
            raise _error("annual combined-securities trial closure drifted")
    return value


def build_annual_2025_combined_securities_net_pixel_review_blueprint_v1() -> dict[str, Any]:
    base, _semantic_index, _crop_manifest, _structure_scan = _inputs()
    return base._review_blueprint()


def build_live_annual_2025_combined_securities_net_8bank_bound_report_absence_v1() -> dict[
    str, Any
]:
    base, semantic_index, crop_manifest, structure_scan = _inputs()
    review = base._review_blueprint()
    crop_sha = hashlib.sha256(canonical_json_bytes_v1(crop_manifest)).hexdigest()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    result = base.build_combined_securities_net_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        None,
        None,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        trading_result_sha256=None,
        investment_result_sha256=None,
    )
    replayed = base.validate_combined_securities_net_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        None,
        None,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        trading_result_sha256=None,
        investment_result_sha256=None,
    )
    return _assert_result(replayed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or (REVIEW_PATH if args.write_review else RESULT_PATH)
    value = (
        build_annual_2025_combined_securities_net_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_combined_securities_net_8bank_bound_report_absence_v1()
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes_v1(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
