"""Verify detailed FX/gold activity disclosures in the fixed eight reports."""

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


service = _load_module(
    "service_activity_support_for_fx_gold_mapping",
    "build_service_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "fx_gold_activity_scan_for_verified_mapping",
    "scan_fx_gold_activity_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "FX_GOLD_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_FX_GOLD_"
    "ACTIVITY_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_NUMERIC_"
    "CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0083-fx-gold-activity-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0083-fx-gold-activity-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "fxgfdsv1:scan:4cf1f5177d526e20aea9ea10955567095981f9967c30dd0fc86807fe8b6b4172"

_SCHEMA_EXPECTED = {
    1175: ("Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối", 1142, 727),
    1176: ("Thu nhập từ hoạt động kinh doanh vàng và ngoại hối", 1175, 728),
    6026: ("Thu từ kinh doanh ngoại tệ giao ngay và vàng", 1175, 729),
    1177: ("Thu từ kinh doanh ngoại tệ giao ngay", 1175, 730),
    1178: ("Thu từ kinh doanh vàng", 1175, 731),
    1179: ("Thu từ các công cụ phái sính tiền tệ", 1175, 732),
    1182: ("Chi phí từ hoạt động kinh doanh vàng và ngoại hối", 1175, 735),
    6027: ("Chi về kinh doanh ngoại tệ giao ngay và vàng", 1175, 736),
    1183: ("Chi từ kinh doanh ngoại tệ giao ngay", 1175, 737),
    1184: ("Chi từ kinh doanh vàng", 1175, 738),
    1185: ("Chi từ các công cụ phái sính tiền tệ", 1175, 739),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_three_reviewed_detailed_fx_gold_regions": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_policy_risk_and_exchange_rate_regions_relabelled_as_detailed_note": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "combined_and_split_spot_gold_rows_double_counted": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_gold_row_required_in_every_bank": False,
    "paddleocr_or_native_source_axis_used_as_semantic_anchor": False,
    "statement_policy_risk_and_exchange_rate_controls_preserved": True,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
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


class FxGoldActivity8BankCodexVerifiedMappingV1Error(ValueError):
    """The FX/gold structure, pixel, numeric, equation or schema evidence drifted."""


def _error(message: str) -> FxGoldActivity8BankCodexVerifiedMappingV1Error:
    return FxGoldActivity8BankCodexVerifiedMappingV1Error(message)


def _assert_no_combined_split_spot_gold_overlap(roles: set[str]) -> None:
    for prefix in ("INCOME", "EXPENSE"):
        combined = f"{prefix}_SPOT_FX_AND_GOLD"
        split = {f"{prefix}_SPOT_FX", f"{prefix}_GOLD"}
        if combined in roles and roles & split:
            raise _error("combined and split spot/gold roles were double counted")


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _mapping(
    role: str,
    report_norm_id: int,
    label: tuple[int, str],
    current: tuple[int, str],
    comparative: tuple[int, str],
    topology: str,
    *,
    page: int,
) -> dict[str, Any]:
    return {
        "label": _ref(page, label[0], label[1]),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {
            "CURRENT_PERIOD": {
                "kind": "AUTHENTICATED_LINE",
                **_ref(page, current[0], current[1]),
            },
            "COMPARATIVE_PERIOD": {
                "kind": "AUTHENTICATED_LINE",
                **_ref(page, comparative[0], comparative[1]),
            },
        },
    }


def _mapped_document(
    code: str,
    page: int,
    source_period: str,
    presentation: str,
    period_lines: Sequence[tuple[int, str]],
    unit_lines: Sequence[tuple[int, str]],
    mappings: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": list(mappings),
        "page_span": [page, page],
        "period_axis": [_ref(page, line, text) for line, text in period_lines],
        "presentation": presentation,
        "source_period": source_period,
        "unit_evidence": [_ref(page, line, text) for line, text in unit_lines],
    }


def _absent(code: str, pages: Sequence[int], reason: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_income_expense_child_graph_match_count": 0,
            "negative_control_pages": list(pages),
            "reason": reason,
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_FX_GOLD_NOTE_IN_BOUND_REPORT",
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    trailing = "TRAILING_UNLABELED_PARENT_TOTALS"
    leading = "LEADING_PRINTED_PARENT_TOTALS"
    return [
        _absent(
            "ACB",
            [6, 10, 23],
            "The income statement reports only the net FX total; policy and FX-difference regions do not contain the detailed income/expense child graph.",
        ),
        _mapped_document(
            "MBB",
            47,
            "2026-06-30",
            trailing,
            [
                (2, "Từ 01/01/2026"),
                (3, "Từ 01/01/2025"),
                (4, "đến 30/06/2026"),
                (5, "đến 30/06/2025"),
            ],
            [(6, "Triệu đồng"), (7, "Triệu đồng")],
            [
                _mapping(
                    "NET_FX_GOLD",
                    1175,
                    (26, "Lãi thuần từ hoạt động kinh doanh ngoại hối"),
                    (27, "105.534"),
                    (28, "1.071.921"),
                    trailing,
                    page=47,
                ),
                _mapping(
                    "INCOME_PARENT",
                    1176,
                    (8, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (15, "4.283.802"),
                    (16, "2.424.156"),
                    trailing,
                    page=47,
                ),
                _mapping(
                    "INCOME_SPOT_FX_AND_GOLD",
                    6026,
                    (9, "Thu từ kinh doanh ngoại tệ giao ngay và vàng"),
                    (10, "1.265.277"),
                    (11, "1.957.541"),
                    trailing,
                    page=47,
                ),
                _mapping(
                    "INCOME_CURRENCY_DERIVATIVES",
                    1179,
                    (12, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (13, "3.018.525"),
                    (14, "466.615"),
                    trailing,
                    page=47,
                ),
                _mapping(
                    "EXPENSE_PARENT",
                    1182,
                    (17, "Chi phí hoạt động kinh doanh ngoại hối"),
                    (24, "(4.178.268)"),
                    (25, "(1.352.235)"),
                    trailing,
                    page=47,
                ),
                _mapping(
                    "EXPENSE_SPOT_FX_AND_GOLD",
                    6027,
                    (18, "Chi về kinh doanh ngoại tệ giao ngay và vàng"),
                    (19, "(493.514)"),
                    (20, "(385.203)"),
                    trailing,
                    page=47,
                ),
                _mapping(
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    1185,
                    (21, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (22, "(3.684.754)"),
                    (23, "(967.032)"),
                    trailing,
                    page=47,
                ),
            ],
        ),
        _mapped_document(
            "VPB",
            63,
            "2026-03-31",
            leading,
            [(10, "ngày 31 tháng 3"), (11, "ngày 31 tháng 3"), (12, "năm 2026"), (13, "năm 2025")],
            [(14, "Triệu đồng"), (15, "Triệu đồng")],
            [
                _mapping(
                    "NET_FX_GOLD",
                    1175,
                    (5, "(LỖ)/LÃI THUẦN TỪ HOẠT ĐỘNG KINH DOANH NGOẠI HỐI"),
                    (40, "(419.768)"),
                    (41, "119.466"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "INCOME_PARENT",
                    1176,
                    (16, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (17, "1.061.345"),
                    (18, "1.162.900"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "INCOME_SPOT_FX",
                    1177,
                    (19, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (20, "436.010"),
                    (21, "932.560"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "INCOME_GOLD",
                    1178,
                    (22, "Thu từ kinh doanh vàng"),
                    (23, "38"),
                    (24, "24.874"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "INCOME_CURRENCY_DERIVATIVES",
                    1179,
                    (25, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (26, "625.297"),
                    (27, "205.466"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "EXPENSE_PARENT",
                    1182,
                    (28, "Chi phí từ hoạt động kinh doanh ngoại hối"),
                    (29, "(1.481.113)"),
                    (30, "(1.043.434)"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "EXPENSE_SPOT_FX",
                    1183,
                    (31, "Chi từ kinh doanh ngoại tệ giao ngay"),
                    (32, "(375.808)"),
                    (33, "(266.794)"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "EXPENSE_GOLD",
                    1184,
                    (34, "Chi về kinh doanh vàng"),
                    (35, "(1)"),
                    (36, "(7.084)"),
                    leading,
                    page=63,
                ),
                _mapping(
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    1185,
                    (37, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (38, "(1.105.304)"),
                    (39, "(769.556)"),
                    leading,
                    page=63,
                ),
            ],
        ),
        _absent(
            "HDB",
            [6, 14, 39],
            "The bound report has an income-statement net total and policy/currency-risk controls but no detailed FX income/expense note.",
        ),
        _absent(
            "VCB",
            [2, 16, 42, 43, 51],
            "Forecast/segment, policy, income-statement and currency-risk regions are near controls; none contains both detailed FX parents and children.",
        ),
        _absent(
            "CTG",
            [6, 20, 61],
            "The bound report exposes the net income-statement line plus policy and exchange-rate notes only, not a detailed income/expense child graph.",
        ),
        _absent(
            "BID",
            [7, 13, 35],
            "The bound report exposes the net income-statement line plus policy and exchange-rate notes only, not a detailed income/expense child graph.",
        ),
        _mapped_document(
            "VIB",
            46,
            "2026-06-30",
            leading,
            [(6, "6 tháng đầu"), (7, "6 tháng đầu"), (8, "năm 2026"), (9, "năm 2025")],
            [(10, "triệu đồng"), (11, "triệu đồng")],
            [
                _mapping(
                    "NET_FX_GOLD",
                    1175,
                    (30, "(Lỗ)/Lãi thuần từ hoạt động kinh doanh ngoại hối"),
                    (31, "(778.876)"),
                    (32, "222.500"),
                    leading,
                    page=46,
                ),
                _mapping(
                    "INCOME_PARENT",
                    1176,
                    (12, "Thu nhập từ hoạt động kinh doanh ngoại hối"),
                    (13, "1.273.796"),
                    (14, "724.709"),
                    leading,
                    page=46,
                ),
                _mapping(
                    "INCOME_SPOT_FX",
                    1177,
                    (15, "Thu từ kinh doanh ngoại tệ giao ngay"),
                    (16, "180.403"),
                    (17, "457.918"),
                    leading,
                    page=46,
                ),
                _mapping(
                    "INCOME_CURRENCY_DERIVATIVES",
                    1179,
                    (18, "Thu từ các công cụ tài chính phái sinh tiền tệ"),
                    (19, "1.093.393"),
                    (20, "266.791"),
                    leading,
                    page=46,
                ),
                _mapping(
                    "EXPENSE_PARENT",
                    1182,
                    (21, "Chi phí hoạt động kinh doanh ngoại hối"),
                    (22, "(2.052.672)"),
                    (23, "(502.209)"),
                    leading,
                    page=46,
                ),
                _mapping(
                    "EXPENSE_SPOT_FX",
                    1183,
                    (24, "Chi về kinh doanh ngoại tệ giao ngay"),
                    (25, "(116.066)"),
                    (26, "(217.889)"),
                    leading,
                    page=46,
                ),
                _mapping(
                    "EXPENSE_CURRENCY_DERIVATIVES",
                    1185,
                    (27, "Chi về các công cụ tài chính phái sinh tiền tệ"),
                    (28, "(1.936.606)"),
                    (29, "(284.320)"),
                    leading,
                    page=46,
                ),
            ],
        ),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0083",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0083:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex FX/gold pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return service._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return service._page(document, page_sequence, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    page_number = item["page_sequence"]
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    line_index = item["line_index"]
    axis_line = service.income.foundation.support._axis_line(axis_page, line_index)
    semantic_line = semantic_page["lines"][line_index]
    if (
        semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis_line["vietocr_text"]
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
        "page_sequence": page_number,
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


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "detailed_note_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("FX/gold result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("FX/gold result identity or metrics drifted")
    allowed = {
        "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
    }
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status") not in allowed
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
        ):
            raise _error("FX/gold trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0083:result:" + canonical_json_sha256_v1(material):
        raise _error("FX/gold result identity drifted")
    return canonical_clone_v1(value)


def _equations(
    mappings: Sequence[Mapping[str, Any]], by_role: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    result = []
    for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):

        def axis(mapping: Mapping[str, Any], *, axis_role: str = axis_role) -> Mapping[str, Any]:
            return next(value for value in mapping["values"] if value["axis_role"] == axis_role)

        income_children = [
            item
            for item in mappings
            if item["role"].startswith("INCOME_") and item["role"] != "INCOME_PARENT"
        ]
        expense_children = [
            item
            for item in mappings
            if item["role"].startswith("EXPENSE_") and item["role"] != "EXPENSE_PARENT"
        ]
        for name, children, parent in (
            ("INCOME_CHILDREN_EQUAL_PRINTED_PARENT", income_children, by_role["INCOME_PARENT"]),
            ("EXPENSE_CHILDREN_EQUAL_PRINTED_PARENT", expense_children, by_role["EXPENSE_PARENT"]),
        ):
            terms = [axis(child) for child in children]
            total = axis(parent)
            computed = sum(term["normalized_value"] for term in terms)
            if computed != total["normalized_value"]:
                raise _error(f"FX/gold accounting equation does not close: {name} {axis_role}")
            result.append(
                {
                    "computed_value": computed,
                    "equation": name,
                    "period_role": axis_role,
                    "status": "CORROBORATED_EXACT",
                    "term_report_norm_ids": [
                        child["schema_binding"]["report_norm_id"] for child in children
                    ],
                    "total_report_norm_id": parent["schema_binding"]["report_norm_id"],
                }
            )
        income = axis(by_role["INCOME_PARENT"])
        expense = axis(by_role["EXPENSE_PARENT"])
        net = axis(by_role["NET_FX_GOLD"])
        computed = income["normalized_value"] + expense["normalized_value"]
        if computed != net["normalized_value"]:
            raise _error(f"FX/gold net equation does not close: {axis_role}")
        result.append(
            {
                "computed_value": computed,
                "equation": "INCOME_PLUS_EXPENSE_EQUALS_NET_FX_GOLD_ACTIVITY",
                "period_role": axis_role,
                "status": "CORROBORATED_EXACT",
                "term_report_norm_ids": [1176, 1182],
                "total_report_norm_id": 1175,
            }
        )
    return result


def build_fx_gold_activity_8bank_codex_verified_mapping_v1(
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
    axis_projection = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis_projection.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest, or structure scan drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["uniqueness"]["status"] == "UNIQUE_FULL_MATCH":
                raise _error("absent detailed FX/gold note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "page_span": None,
                    "period_evidence": [],
                    "presentation": reviewed["presentation"],
                    "source_period_status": "NOT_APPLICABLE_NO_DETAILED_NOTE",
                    "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                }
            )
            continue
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF FX/gold graph")
        page_number = reviewed["page_span"][0]
        axis_document = _document(axis_projection["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_texts = service.income.foundation.support._source_line_axis(crop_page)
        verified_mappings = []
        for mapping in reviewed["mappings"]:
            values = []
            for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
                ref = mapping["values"][axis_role]
                evidence = service.income.foundation.support._source_value(
                    axis_page,
                    semantic_page,
                    crop_page,
                    source_texts,
                    {
                        "line_index": ref["line_index"],
                        "pixel_transcription": ref["pixel_transcription"],
                    },
                )
                try:
                    proposal = service.income.foundation.support._money(
                        evidence["fresh_vietocr_numeric_proposal"]
                    )
                except ValueError:
                    proposal = None
                values.append(
                    {
                        "axis_role": axis_role,
                        **evidence,
                        "fresh_vietocr_numeric_status": (
                            "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                            if proposal == evidence["normalized_value"]
                            else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                        ),
                        "page_sequence": page_number,
                    }
                )
            verified_mappings.append(
                {
                    "label_evidence": _semantic_evidence(
                        axis_document, semantic_document, mapping["label"]
                    ),
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": values,
                }
            )
        roles = {mapping["role"] for mapping in verified_mappings}
        _assert_no_combined_split_spot_gold_overlap(roles)
        equations = _equations(
            verified_mappings, {item["role"]: item for item in verified_mappings}
        )
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "page_span": list(reviewed["page_span"]),
                "period_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_period_status": (
                    "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    if reviewed["source_period"] == "2026-03-31"
                    else "VERIFIED_SOURCE_PERIOD_Q2_2026"
                ),
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if reviewed["source_period"] == "2026-03-31"
                    else "VERIFIED_BY_CODEX"
                ),
                "unit_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": crop_manifest_sha256,
            "pixel_review_sha256": review_sha256,
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": 741,
            "family_root_report_norm_id": 1175,
            "mapped_report_norm_ids": sorted(_SCHEMA_EXPECTED),
        },
        "state": "FX_GOLD_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0083:result:" + canonical_json_sha256_v1(material)}
    )


def validate_fx_gold_activity_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_fx_gold_activity_8bank_codex_verified_mapping_v1(
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
        raise _error("FX/gold verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = service.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = service.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def build_live_fx_gold_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_fx_gold_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_fx_gold_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_fx_gold_activity_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_fx_gold_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_fx_gold_activity_8bank_codex_verified_mapping_replay_v1(
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
        _write(RESULT_PATH, build_live_fx_gold_activity_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_fx_gold_activity_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
