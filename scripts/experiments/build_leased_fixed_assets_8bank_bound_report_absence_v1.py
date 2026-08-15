"""Seal the eight-bank bound-report absence of leased fixed-asset movements."""

from __future__ import annotations

import argparse
import importlib.util
import sys
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
RESULT_PATH = Path("docs/experiments/E-0070-leased-fixed-assets-8bank-bound-report-absence-v1.json")
FORMAT_VERSION = "LEASED_FIXED_ASSETS_8BANK_BOUND_REPORT_ABSENCE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_SUPPLIED_PDFS_COMPLETE_FRESH_VIETOCR_SHARED_FIXED_ASSET_"
    "VARIANT_GRAPH_PLUS_INDEPENDENT_VISIBLE_PDF_FAMILY_BOUNDARY_REVIEW_"
    "AND_LIVE_TM_SCHEMA_896_TO_912_ONLY_NO_BROAD_CORPUS_NUMERIC_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "absence_claim_bounded_to_supplied_pdf": True,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "finance_lease_policy_service_or_loan_text_promoted": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_896_to_912_mapping_emitted": False,
    "shared_fixed_asset_variant_engine_used": True,
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
_BOUNDARIES = {
    "ACB": (
        (19, "gop von dau tu dai han", "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (20, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC"),
    ),
    "MBB": (
        (37, "tai san co dinh huu hinh", "Tài sản cố định hữu hình"),
        (39, "tai san co dinh vo hinh", "Tài sản cố định vô hình"),
    ),
    "VPB": (
        (49, "tai san co dinh huu hinh", "Tài sản cố định hữu hình"),
        (50, "tai san co dinh vo hinh", "Tài sản cố định vô hình"),
    ),
    "HDB": (
        (30, "gop von dau tu dai han", "Góp vốn, đầu tư dài hạn"),
        (31, "vay cac tctd khac", "Vay các TCTD khác"),
    ),
    "VCB": (
        (33, "gop von dau tu dai han", "Góp vốn đầu tư dài hạn"),
        (34, "cac khoan no chinh phu", "Các khoản nợ Chính phủ và Ngân hàng Nhà nước"),
    ),
    "CTG": (
        (40, "chung khoan dau tu", "CHỨNG KHOÁN ĐẦU TƯ"),
        (41, "cac khoan no chinh phu", "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN"),
    ),
    "BID": (
        (24, "gop von dau tu dai han", "GÓP VỐN, ĐẦU TƯ DÀI HẠN"),
        (25, "tien gui va vay cac tctd khac", "TIỀN GỬI VÀ VAY CÁC TCTD KHÁC"),
    ),
    "VIB": (
        (37, "tai san co dinh huu hinh", "TÀI SẢN CỐ ĐỊNH HỮU HÌNH"),
        (38, "tai san co dinh vo hinh", "TÀI SẢN CỐ ĐỊNH VÔ HÌNH"),
    ),
}
_SOURCE_PERIOD = {
    **{code: ("2026-06-30", "VERIFIED_SOURCE_PERIOD_Q2_2026") for code in EXPECTED_DOCUMENT_ORDER},
    "VPB": ("2026-03-31", "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"),
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


class LeasedFixedAssets8BankBoundReportAbsenceV1Error(ValueError):
    """The complete-PDF scan, visible boundary review or schema drifted."""


def _error(message: str) -> LeasedFixedAssets8BankBoundReportAbsenceV1Error:
    return LeasedFixedAssets8BankBoundReportAbsenceV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _scanner() -> ModuleType:
    return _load_module(
        "leased_fixed_assets_scan_for_bound_absence",
        "scan_leased_fixed_assets_full_document_vietocr_v1.py",
    )


def _schema_family() -> tuple[dict[str, Any], dict[str, Any]]:
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    items = []
    for schema_id, (name, parent_id) in _EXPECTED_SCHEMA.items():
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
                "canonical_name": item.canonical_name,
                "children": list(item.children),
                "display_order": item.display_order,
                "hierarchy_level": item.hierarchy_level,
                "parent_report_norm_id": item.parent_id,
                "report_norm_id": item.schema_id,
            }
        )
    return authority, {"first_report_norm_id": 896, "items": items, "last_report_norm_id": 912}


def _line_ref(
    pages: list[dict[str, Any]], page_sequence: int, phrase: str, pixel_text: str
) -> dict[str, Any]:
    page_matches = [page for page in pages if page["page_sequence"] == page_sequence]
    if len(page_matches) != 1:
        raise _error("visible family-boundary page is not unique")
    candidates = [
        line
        for line in page_matches[0]["lines"]
        if phrase in normalize_vietnamese_anchor_v1(line["semantic_text"])
    ]
    if not candidates:
        raise _error("visible family-boundary anchor was not found")
    line = min(
        candidates, key=lambda item: (len(item["semantic_text"].split()), item["source_line_index"])
    )
    if phrase not in normalize_vietnamese_anchor_v1(pixel_text):
        raise _error("independent pixel transcription does not preserve the boundary anchor")
    return {
        "bbox": list(line["bbox"]),
        "independent_pixel_transcription": pixel_text,
        "page_sequence": page_sequence,
        "semantic_text_source": line["semantic_text_source"],
        "source_line_index": line["source_line_index"],
        "vietocr_transformer_proposal": line["semantic_text"],
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "bound_report_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": sum(len(trial["mappings"]) for trial in trials),
        "negative_control_line_count": sum(len(trial["negative_controls"]) for trial in trials),
        "open_review_item_count": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("leased-fixed-assets absence result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "LEASED_FIXED_ASSETS_8BANK_BOUND_REPORT_ABSENCE_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or type(value["schema_family"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("leased-fixed-assets absence result identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "boundary_evidence",
            "disposition",
            "document_ordinal",
            "document_provenance",
            "independent_review",
            "mappings",
            "negative_controls",
            "source_pdf_sha256",
            "source_period",
            "source_period_status",
            "structure_graph_id",
            "whole_document_scan_metrics",
        }:
            raise _error("leased-fixed-assets absence trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["disposition"] != "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            or trial["independent_review"] != "CODEX_VISIBLE_PDF_BOUNDARY_REVIEW"
            or type(trial["boundary_evidence"]) is not list
            or len(trial["boundary_evidence"]) != 2
            or trial["mappings"] != []
            or type(trial["negative_controls"]) is not list
        ):
            raise _error("leased-fixed-assets absence trial content drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("leased-fixed-assets absence metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0070:result:" + canonical_json_sha256_v1(material):
        raise _error("leased-fixed-assets absence identity drifted")
    return canonical_clone_v1(value)


def build_leased_fixed_assets_8bank_bound_report_absence_v1(
    semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    scanner = _scanner()
    scan = scanner.build_leased_fixed_assets_full_document_scan_v1(semantic_index, rescue)
    if scan["metrics"]["complete_region_count"] != 0 or scan["metrics"]["near_region_count"] != 0:
        raise _error("leased-fixed-assets region exists or needs review; absence cannot be sealed")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = scanner._support()
    scan_by_code = {trial["document_provenance"]: trial for trial in scan["trials"]}
    trials = []
    for document in axis["documents"]:
        code = document["document_provenance"]
        pages, _ = support._matcher_pages(document, rescue)
        boundary_evidence = [
            _line_ref(pages, page, phrase, pixel_text)
            for page, phrase, pixel_text in _BOUNDARIES[code]
        ]
        scan_trial = scan_by_code[code]
        source_period, source_period_status = _SOURCE_PERIOD[code]
        trials.append(
            {
                "boundary_evidence": boundary_evidence,
                "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                "document_ordinal": document["document_ordinal"],
                "document_provenance": code,
                "independent_review": "CODEX_VISIBLE_PDF_BOUNDARY_REVIEW",
                "mappings": [],
                "negative_controls": canonical_clone_v1(scan_trial["negative_controls"]),
                "source_pdf_sha256": document["source_pdf"]["sha256"],
                "source_period": source_period,
                "source_period_status": source_period_status,
                "structure_graph_id": scan_trial["matcher_result"]["result_id"],
                "whole_document_scan_metrics": canonical_clone_v1(
                    scan_trial["matcher_result"]["metrics"]
                ),
            }
        )
    schema_authority, schema_family = _schema_family()
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "schema_authority": schema_authority,
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "structure_scan_id": scan["scan_id"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": "LEASED_FIXED_ASSETS_8BANK_BOUND_REPORT_ABSENCE_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0070:result:" + canonical_json_sha256_v1(material)}
    )


def build_live_leased_fixed_assets_8bank_bound_report_absence_v1() -> dict[str, Any]:
    scanner = _scanner()
    support = scanner._support()
    semantic_index, _ = support._fixed_json(scanner.DEFAULT_INPUT)
    rescue = support.authenticate_rotated_vietocr_semantic_rescue_v1(
        semantic_index, scanner.DEFAULT_RESCUE_ROOT
    )
    return build_leased_fixed_assets_8bank_bound_report_absence_v1(semantic_index, rescue)


def validate_live_leased_fixed_assets_8bank_bound_report_absence_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_leased_fixed_assets_8bank_bound_report_absence_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("leased-fixed-assets absence result does not replay exactly")
    return supplied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    result = build_live_leased_fixed_assets_8bank_bound_report_absence_v1()
    args.output.write_bytes(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
