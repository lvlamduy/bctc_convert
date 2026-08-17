"""Seal annual-2025 absence of finance-lease fixed-asset movement tables.

The complete-PDF matcher is bank blind.  A local absence is bounded by the
already verified tangible-fixed-asset family and the first following
intangible-fixed-asset family anchor; bank and page identities are evidence,
never routing inputs.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
TANGIBLE_RESULT_PATH = Path(
    "docs/experiments/E-0123-annual-2025-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0124-annual-2025-leased-fixed-assets-8bank-bound-report-absence-v1.json"
)
EXPECTED_SEMANTIC_INDEX = (
    "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d",
    30_802_711,
)
EXPECTED_TANGIBLE_RESULT = (
    "0fa5e1212ba840b456fa140670541b3f31a7038504c95ddbf170f4ef1c5d394a",
    234_208,
)
EXPECTED_TANGIBLE_RESULT_ID = (
    "annual2025tfa8bcv1:result:621c50fe4e1bbd001e35c57f5cc1ec08fd79ea9ddb851309d87ee47e8397a342"
)
FORMAT_VERSION = "ANNUAL_2025_LEASED_FIXED_ASSETS_8BANK_BOUND_REPORT_ABSENCE_V1"
SCAN_FORMAT = "ANNUAL_2025_LEASED_FIXED_ASSETS_8DOCUMENT_STRUCTURE_SCAN_V1"
SCAN_ID_PREFIX = "a2025lfafdsv1:scan:"
RESULT_ID_PREFIX = "e0124:result:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_REPORTING_PERIOD_GENERAL_LEASED_FIXED_ASSET_GRAPH_ADJACENT_"
    "LINE_ANCHOR_FUSION_ROTATED_SAME_TRANSFORMER_RESCUE_TANGIBLE_TO_"
    "INTANGIBLE_FAMILY_BOUNDARY_AND_FAMILY_LOCAL_TM_SCHEMA_ONLY_NO_EXPORT_"
    "AUTHORITY"
)
SCAN_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_COMPLETE_PDF_FRESH_VIETOCR_SHARED_"
    "LEASED_FIXED_ASSET_OWNER_COST_DEPRECIATION_REPORTING_PERIOD_GENERAL_"
    "ADJACENT_LINE_ANCHOR_FUSION_AND_ROTATED_RESCUE_SCAN_ONLY"
)
_AUTHORITY = {
    "absence_claim_bounded_to_exact_annual_2025_reports": True,
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "broad_corpus_or_other_period_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "finance_lease_policy_service_loan_or_income_text_promoted": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_live_replay_required": True,
    "schema_binding_is_family_local_id_name_parent_only": True,
    "split_owner_or_branch_lines_supported": True,
}
_SCAN_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "generic_finance_lease_text_can_accept_family": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_general_profile_used": True,
    "shared_fixed_asset_variant_engine_used": True,
    "split_owner_or_branch_lines_supported": True,
}
_EXPECTED_SCHEMA = {
    896: ("Tăng, giảm tài sản cố định thuê tài chính", 560),
    897: ("Nguyên giá TSCĐ thuê TC", 896),
    898: ("Số dư đầu kỳ", 897),
    899: ("+ Thuê tài chính trong kỳ", 897),
    900: ("+ Tăng khác", 897),
    901: ("+ Mua lại TSCĐ thuê tài chính (*)", 897),
    902: ("+ Trả lại TSCĐ thuê tài chính (*)", 897),
    903: ("+ Giảm khác", 897),
    904: ("Số dư cuối kỳ", 897),
    905: ("Giá trị hao mòn lũy kế", 896),
    906: ("Số dư đầu kỳ", 905),
    907: ("+ Khấu hao trong kỳ", 905),
    908: ("+ Tăng khác", 905),
    909: ("+ Mua lại TSCĐ thuê tài chính (*)", 905),
    910: ("+ Trả lại TSCĐ thuê tài chính (*)", 905),
    911: ("+ Giảm khác", 905),
    912: ("Số dư cuối kỳ", 905),
}
_NEXT_PIXEL_TRANSCRIPTIONS = {
    "ACB": "Tài sản cố định vô hình",
    "MBB": "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
    "VPB": "Tài sản cố định vô hình",
    "HDB": "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
    "VCB": "Tài sản cố định vô hình",
    "CTG": "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
    "BID": "Tài sản cố định vô hình",
    "VIB": "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
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


class Annual2025LeasedFixedAssetsAbsenceV1Error(ValueError):
    """The annual scan, boundary chain, schema or replay drifted."""


def _error(message: str) -> Annual2025LeasedFixedAssetsAbsenceV1Error:
    return Annual2025LeasedFixedAssetsAbsenceV1Error(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _scanner() -> ModuleType:
    scanner = _load_module(
        "annual_2025_leased_fixed_assets_scan_v1",
        "scripts/experiments/scan_leased_fixed_assets_full_document_vietocr_v1.py",
    )
    scanner.FORMAT_VERSION = SCAN_FORMAT
    scanner.MATCHER_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
    scanner.SCAN_ID_PREFIX = SCAN_ID_PREFIX
    scanner.CLAIM_BOUNDARY = SCAN_CLAIM_BOUNDARY
    scanner._AUTHORITY = canonical_clone_v1(_SCAN_AUTHORITY)
    return scanner


def _schema_family() -> dict[str, Any]:
    _authority, by_id = _authority_snapshot(PROJECT_ROOT)
    items = []
    family_ids = set(_EXPECTED_SCHEMA)
    for family_order, (schema_id, (name, parent_id)) in enumerate(_EXPECTED_SCHEMA.items(), 1):
        item = by_id.get(schema_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent_id
            or item.statement_type != "TM"
        ):
            raise _error(f"live leased-fixed-assets schema binding drifted: {schema_id}")
        items.append(
            {
                "canonical_name": name,
                "children_in_family": sorted(
                    child for child in item.children if child in family_ids
                ),
                "family_order": family_order,
                "parent_report_norm_id": parent_id,
                "report_norm_id": schema_id,
            }
        )
    material = {
        "first_report_norm_id": 896,
        "items": items,
        "last_report_norm_id": 912,
    }
    return {
        **material,
        "family_projection_id": "lfasfv1:family:" + canonical_json_sha256_v1(material),
    }


def _line_evidence(
    raw_document: Mapping[str, Any],
    line_ref: Mapping[str, Any],
    independent_pixel_transcription: str,
) -> dict[str, Any]:
    page_sequence = line_ref["page_sequence"]
    source_line_index = line_ref["source_line_index"]
    line = raw_document["pages"][page_sequence - 1]["lines"][source_line_index]
    normalized_pixel = normalize_vietnamese_anchor_v1(independent_pixel_transcription)
    normalized_proposal = normalize_vietnamese_anchor_v1(line_ref["semantic_text"])
    if normalized_pixel != normalized_proposal:
        raise _error("independent boundary pixel transcription and VietOCR anchor drifted")
    return {
        "bbox": list(line_ref["bbox"]),
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "fresh_vietocr_proposal": line_ref["semantic_text"],
        "independent_pixel_transcription": independent_pixel_transcription,
        "normalized_pixel_transcription": normalized_pixel,
        "normalized_vietocr_proposal": normalized_proposal,
        "page_sequence": page_sequence,
        "semantic_text_source": line_ref["semantic_text_source"],
        "source_line_index": source_line_index,
    }


def _next_intangible_region(
    matcher: ModuleType,
    pages: Sequence[Mapping[str, Any]],
    tangible_region: Mapping[str, Any],
) -> dict[str, Any]:
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(pages)
    candidates = [
        region
        for region in [*result["regions"], *result["near_regions"]]
        if region["start_global_ordinal"] > tangible_region["end_global_ordinal"]
        and {"OWNER", "COST"}.issubset(region["anchor_roles"])
        and region["numeric_line_count"] >= 4
    ]
    if not candidates:
        raise _error("no following intangible-fixed-assets family boundary was found")
    candidates.sort(key=lambda region: region["start_global_ordinal"])
    first_ordinal = candidates[0]["start_global_ordinal"]
    if sum(region["start_global_ordinal"] == first_ordinal for region in candidates) != 1:
        raise _error("following intangible-fixed-assets boundary is not unique")
    return canonical_clone_v1(candidates[0])


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "bound_report_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_ANNUAL_2025_REPORT"
            for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": sum(len(trial["mappings"]) for trial in trials),
        "negative_control_line_count": sum(len(trial["negative_controls"]) for trial in trials),
        "open_review_item_count": 0,
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual leased-fixed-assets result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_LEASED_FIXED_ASSETS_BOUND_REPORT_ABSENCE_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or type(value["input_refs"]) is not dict
        or type(value["schema_family"]) is not dict
    ):
        raise _error("annual leased-fixed-assets result identity drifted")
    for ordinal, trial in enumerate(value["trials"], 1):
        if type(trial) is not dict or set(trial) != {
            "boundary_order_status",
            "disposition",
            "document_ordinal",
            "document_provenance",
            "mappings",
            "negative_controls",
            "next_family_boundary",
            "previous_family_boundary",
            "rotated_rescue_line_count",
            "source_pdf_sha256",
            "source_period",
            "source_period_status",
            "structure_graph_id",
            "whole_document_scan_metrics",
        }:
            raise _error("annual leased-fixed-assets trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["disposition"] != "CONFIRMED_NOT_PRESENT_IN_BOUND_ANNUAL_2025_REPORT"
            or trial["boundary_order_status"]
            != "TANGIBLE_PRECEDES_INTANGIBLE_WITH_NO_LEASED_REGION"
            or trial["mappings"] != []
            or type(trial["negative_controls"]) is not list
            or type(trial["rotated_rescue_line_count"]) is not int
            or trial["source_period"] != "2025-12-31"
            or trial["source_period_status"] != "VERIFIED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE"
            or not same_typed_json_v1(
                trial["whole_document_scan_metrics"],
                {
                    "complete_region_count": 0,
                    "near_region_count": 0,
                    "owner_candidate_count": 0,
                },
            )
        ):
            raise _error("annual leased-fixed-assets trial content drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("annual leased-fixed-assets metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual leased-fixed-assets result identity drifted")
    return canonical_clone_v1(value)


def build_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1(
    semantic_index: Any,
    tangible_result: Any,
    rescue: dict[str, Any],
) -> dict[str, Any]:
    scanner = _scanner()
    scan = scanner.build_leased_fixed_assets_full_document_scan_v1(semantic_index, rescue)
    if scan["metrics"]["complete_region_count"] != 0 or scan["metrics"]["near_region_count"] != 0:
        raise _error("leased-fixed-assets region exists or needs review; absence cannot be sealed")
    if (
        type(tangible_result) is not dict
        or tangible_result.get("result_id") != EXPECTED_TANGIBLE_RESULT_ID
        or type(tangible_result.get("trials")) is not list
        or len(tangible_result["trials"]) != 8
    ):
        raise _error("annual tangible-fixed-assets predecessor result drifted")

    support = scanner._support()
    matcher = scanner._matcher()
    axis = scanner.project_full_document_vietocr_accounting_axis_v1(semantic_index)
    full_rescue = support._full_rescue_by_locator(rescue, axis["semantic_axis_sha256"])
    scan_by_code = {trial["document_provenance"]: trial for trial in scan["trials"]}
    predecessor_by_code = {
        trial["document_provenance"]: trial for trial in tangible_result["trials"]
    }
    trials = []
    for document, raw_document in zip(axis["documents"], semantic_index["documents"], strict=True):
        code = document["document_provenance"]
        pages, applied_count = support._matcher_pages(document, rescue, full_rescue)
        tangible_graph = matcher.build_tangible_fixed_assets_variant_graph_document_v1(
            pages,
            variant_profile=matcher.REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
        )
        if tangible_graph["uniqueness"]["status"] != "UNIQUE_FULL_MATCH":
            raise _error("annual tangible predecessor is not one unique structural region")
        tangible_region = tangible_graph["regions"][0]
        predecessor = predecessor_by_code.get(code)
        if (
            predecessor is None
            or predecessor["structure_graph_id"] != tangible_graph["result_id"]
            or predecessor["page_sequence"] != tangible_region["owner"]["page_sequence"]
            or predecessor["owner_evidence"]["source_line_index"]
            != tangible_region["owner"]["source_line_index"]
        ):
            raise _error("annual tangible predecessor binding drifted")
        next_region = _next_intangible_region(matcher, pages, tangible_region)
        next_boundary = _line_evidence(
            raw_document,
            next_region["owner"],
            _NEXT_PIXEL_TRANSCRIPTIONS[code],
        )
        previous_boundary = {
            **canonical_clone_v1(predecessor["owner_evidence"]),
            "page_sequence": predecessor["page_sequence"],
        }
        if next_region["start_global_ordinal"] <= tangible_region["end_global_ordinal"]:
            raise _error("annual family boundary order drifted")
        scan_trial = scan_by_code[code]
        trials.append(
            {
                "boundary_order_status": ("TANGIBLE_PRECEDES_INTANGIBLE_WITH_NO_LEASED_REGION"),
                "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_ANNUAL_2025_REPORT",
                "document_ordinal": document["document_ordinal"],
                "document_provenance": code,
                "mappings": [],
                "negative_controls": canonical_clone_v1(scan_trial["negative_controls"]),
                "next_family_boundary": next_boundary,
                "previous_family_boundary": previous_boundary,
                "rotated_rescue_line_count": applied_count,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
                "source_period": "2025-12-31",
                "source_period_status": ("VERIFIED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE"),
                "structure_graph_id": scan_trial["matcher_result"]["result_id"],
                "whole_document_scan_metrics": canonical_clone_v1(
                    scan_trial["matcher_result"]["metrics"]
                ),
            }
        )

    schema_family = _schema_family()
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "rotated_rescue_projection_id": rescue["projection_id"],
            "schema_family_projection_id": schema_family["family_projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "structure_scan_id": scan["scan_id"],
            "tangible_predecessor_result_id": tangible_result["result_id"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": "ANNUAL_2025_LEASED_FIXED_ASSETS_BOUND_REPORT_ABSENCE_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _live_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scanner = _scanner()
    support = scanner._support()
    semantic_index, _ = support._fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_SEMANTIC_INDEX)
    tangible_result, _ = support._fixed_json(TANGIBLE_RESULT_PATH, EXPECTED_TANGIBLE_RESULT)
    rescue = support._profile_rescue(semantic_index, support.DEFAULT_RESCUE_ROOT)
    if type(rescue) is not dict:
        raise _error("annual rotated semantic rescue is unavailable")
    return semantic_index, tangible_result, rescue


def build_live_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1() -> dict[str, Any]:
    return build_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1(*_live_inputs())


def validate_annual_2025_leased_fixed_assets_8bank_bound_report_absence_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual leased-fixed-assets absence does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write:
        result = build_live_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    if args.verify:
        scanner = _scanner()
        support = scanner._support()
        value, _ = support._fixed_json(RESULT_PATH)
        result = validate_annual_2025_leased_fixed_assets_8bank_bound_report_absence_replay_v1(
            value
        )
        print(result["result_id"])
        return 0
    parser.error("choose exactly one action")


if __name__ == "__main__":
    raise SystemExit(main())
