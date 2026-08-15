"""Verify interest-expense disclosures across the fixed eight reports."""

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


income = _load_module(
    "interest_income_support_for_interest_expense_mapping",
    "build_interest_income_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "interest_expense_scan_for_verified_mapping",
    "scan_interest_expense_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INTEREST_EXPENSE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "INTEREST_EXPENSE_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_INTEREST_"
    "EXPENSE_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_NUMERIC_"
    "CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0081-interest-expense-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0081-interest-expense-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "iefdsv1:scan:ab7fa294ceb54ff50cf2cd3e0d203060b63c1e889689c54f2d08e4641ae8b0fe"

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        684,
    ),
    1151: ("Chi phí lãi và các khoản tương tự chi phí lãi", 1142, 693),
    1152: ("Trả lãi tiền gửi", 1151, 694),
    1153: ("Trả lãi tiền vay", 1151, 695),
    1154: ("Trả lãi phát hành giấy tờ có giá", 1151, 696),
    1155: ("Trả lãi tiền thuê tài chính", 1151, 697),
    1156: ("Chi phí khác cho hoạt động tín dụng", 1151, 698),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "finance_lease_interest_not_observed_in_bound_regions": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_interest_expense_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "vietocr_numeric_disagreement_is_retained_not_silently_repaired": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "document_period_or_unit_inheritance_recorded_explicitly": True,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "paddleocr_source_axis_used_as_semantic_anchor": False,
    "source_children_and_parent_total_double_counted": False,
    "vietocr_used_as_numeric_truth": False,
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


class InterestExpense8BankCodexVerifiedMappingV1Error(ValueError):
    """The fixed structure, pixel, numeric, equation or schema evidence drifted."""


def _error(message: str) -> InterestExpense8BankCodexVerifiedMappingV1Error:
    return InterestExpense8BankCodexVerifiedMappingV1Error(message)


_label = income._label
_value = income._value
_mapping = income._mapping
_doc = income._doc


def _review_documents() -> list[dict[str, Any]]:
    p = 24
    acb = _doc(
        "ACB",
        p,
        39,
        "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ",
        [_label(p, 42, "30.6.2026"), _label(p, 43, "30.6.2025")],
        [_label(p, 44, "Triệu đồng"), _label(p, 45, "Triệu đồng")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 39, "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ"),
                _value(p, 58, "22.526.647"),
                _value(p, 59, "14.583.288"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 46, "Trả lãi tiền gửi"),
                _value(p, 47, "15.592.211"),
                _value(p, 48, "10.797.633"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 49, "Trả lãi tiền vay"),
                _value(p, 50, "1.721.889"),
                _value(p, 51, "746.231"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 52, "Trả lãi phát hành giấy tờ có giá"),
                _value(p, 53, "5.181.279"),
                _value(p, 54, "2.571.621"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 55, "Chi phí hoạt động tín dụng khác"),
                _value(p, 56, "31.268"),
                _value(p, 57, "467.803"),
            ),
        ],
    )

    p = 46
    mbb = _doc(
        "MBB",
        p,
        31,
        "Chi phí lãi và các chi phí tương tự",
        [
            _label(p, 4, "Từ 01/01/2026"),
            _label(p, 6, "đến 30/06/2026"),
            _label(p, 5, "Từ 01/01/2025"),
            _label(p, 7, "đến 30/06/2025"),
        ],
        [_label(p, 8, "Triệu đồng"), _label(p, 9, "Triệu đồng")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 31, "Chi phí lãi và các chi phí tương tự"),
                _value(p, 44, "(31.182.138)"),
                _value(p, 45, "(16.625.137)"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 32, "Chi lãi tiền gửi"),
                _value(p, 33, "(21.852.520)"),
                _value(p, 34, "(11.477.971)"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 35, "Chi lãi tiền vay"),
                _value(p, 36, "(2.607.619)"),
                _value(p, 37, "(901.318)"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 38, "Chi lãi phát hành giấy tờ có giá"),
                _value(p, 39, "(6.615.152)"),
                _value(p, 40, "(3.975.549)"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 41, "Chi các hoạt động tín dụng khác"),
                _value(p, 42, "(106.847)"),
                _value(p, 43, "(270.299)"),
            ),
        ],
    )

    p = 62
    vpb = _doc(
        "VPB",
        p,
        44,
        "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ",
        [
            _label(p, 47, "3 tháng kết thúc"),
            _label(p, 49, "ngày 31 tháng 3"),
            _label(p, 51, "năm 2026"),
            _label(p, 48, "3 tháng kết thúc"),
            _label(p, 50, "ngày 31 tháng 3"),
            _label(p, 52, "năm 2025"),
        ],
        [_label(p, 53, "Triệu đồng"), _label(p, 54, "Triệu đồng")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 44, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
                _value(p, 67, "14.588.966"),
                _value(p, 68, "8.828.531"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 55, "Trả lãi tiền gửi"),
                _value(p, 56, "9.775.329"),
                _value(p, 57, "6.274.417"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 58, "Trả lãi tiền vay"),
                _value(p, 59, "2.454.820"),
                _value(p, 60, "1.311.937"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 61, "Trả lãi phát hành giấy tờ có giá"),
                _value(p, 62, "2.020.716"),
                _value(p, 63, "1.063.976"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 64, "Chi phí hoạt động tín dụng khác"),
                _value(p, 65, "338.101"),
                _value(p, 66, "178.201"),
            ),
        ],
        source_period="2026-03-31",
    )

    p = 34
    hdb = _doc(
        "HDB",
        p,
        74,
        "Chi phí lãi và các khoản chi phí tương tự",
        [_label(p, 75, "Kỳ này"), _label(p, 76, "Kỳ trước")],
        [_label(p, 77, "Triệu VND"), _label(p, 78, "Triệu VND")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 74, "Chi phí lãi và các khoản chi phí tương tự"),
                _value(p, 91, "25.349.293"),
                _value(p, 92, "15.754.167"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 79, "Chi phí lãi tiền gửi"),
                _value(p, 80, "20.730.042"),
                _value(p, 81, "12.237.004"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 82, "Chi phí lãi tiền vay"),
                _value(p, 83, "1.159.696"),
                _value(p, 84, "726.606"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 85, "Chi phí lãi phát hành giấy tờ có giá"),
                _value(p, 86, "3.400.083"),
                _value(p, 87, "2.661.483"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 88, "Chi phí hoạt động tín dụng khác"),
                _value(p, 89, "59.472"),
                _value(p, 90, "129.074"),
            ),
        ],
    )

    p = 39
    vcb = _doc(
        "VCB",
        p,
        8,
        "Chi phí lãi và các khoản chi phí tương tự",
        [
            _label(p, 11, "từ 1/1/2026"),
            _label(p, 13, "đến 30/6/2026"),
            _label(p, 12, "từ 1/1/2025"),
            _label(p, 14, "đến 30/6/2025"),
        ],
        [_label(p, 15, "Triệu VND"), _label(p, 16, "Triệu VND")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 8, "Chi phí lãi và các khoản chi phí tương tự"),
                _value(p, 30, "31.771.899"),
                _value(p, 31, "21.945.058"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 18, "Trả lãi tiền gửi"),
                _value(p, 19, "29.974.807"),
                _value(p, 20, "21.026.955"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 21, "Trả lãi tiền gửi và vay các tổ chức tín dụng khác"),
                _value(p, 22, "841.567"),
                _value(p, 23, "356.191"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 24, "Trả lãi phát hành giấy tờ có giá"),
                _value(p, 25, "919.110"),
                _value(p, 26, "533.711"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 27, "Chi phí khác cho hoạt động tín dụng"),
                _value(p, 28, "36.415"),
                _value(p, 29, "28.201"),
            ),
        ],
    )

    p = 45
    ctg = _doc(
        "CTG",
        p,
        41,
        "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ",
        [
            _label(p, 44, "từ 01/01/2026 đến"),
            _label(p, 46, "hết 30/06/2026"),
            _label(p, 45, "từ 01/01/2025 đến"),
            _label(p, 47, "hết 30/06/2025"),
        ],
        [_label(p, 48, "triệu đồng"), _label(p, 49, "triệu đồng")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 41, "CHI PHÍ LÃI VÀ CÁC KHOẢN CHI PHÍ TƯƠNG TỰ"),
                _value(p, 62, "48.475.727"),
                _value(p, 63, "36.242.784"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 50, "Trả lãi tiền gửi"),
                _value(p, 51, "42.198.173"),
                _value(p, 52, "29.980.881"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 53, "Trả lãi tiền vay"),
                _value(p, 54, "1.300.560"),
                _value(p, 55, "746.841"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 56, "Trả lãi phát hành giấy tờ có giá"),
                _value(p, 57, "4.639.315"),
                _value(p, 58, "5.105.809"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 59, "Chi phí hoạt động tín dụng khác"),
                _value(p, 60, "337.679"),
                _value(p, 61, "409.253"),
            ),
        ],
    )

    p = 29
    bid = _doc(
        "BID",
        p,
        5,
        "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ",
        [
            _label(p, 6, "Từ 01/01/2026 đến"),
            _label(p, 8, "30/06/2026"),
            _label(p, 7, "Từ 01/01/2025 đến"),
            _label(p, 9, "30/06/2025"),
        ],
        [_label(28, 58, "Đơn vị: Triệu VND")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 5, "CHI PHÍ LÃI VÀ CÁC CHI PHÍ TƯƠNG TỰ"),
                _value(p, 22, "59.082.019"),
                _value(p, 23, "43.876.085"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 10, "Trả lãi tiền gửi"),
                _value(p, 11, "47.530.349"),
                _value(p, 12, "37.532.669"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 13, "Trả lãi tiền vay"),
                _value(p, 14, "2.722.737"),
                _value(p, 15, "875.913"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 16, "Trả lãi phát hành giấy tờ có giá"),
                _value(p, 17, "8.748.307"),
                _value(p, 18, "5.389.217"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 19, "Chi phí hoạt động tín dụng khác"),
                _value(p, 20, "80.626"),
                _value(p, 21, "78.286"),
            ),
        ],
    )

    p = 45
    vib = _doc(
        "VIB",
        p,
        48,
        "Chi phí lãi và các chi phí tương tự",
        [
            _label(p, 27, "6 tháng đầu"),
            _label(p, 29, "năm 2026"),
            _label(p, 28, "6 tháng đầu"),
            _label(p, 30, "năm 2025"),
        ],
        [_label(p, 31, "triệu đồng"), _label(p, 32, "triệu đồng")],
        [
            _mapping(
                1151,
                "TOTAL_INTEREST_EXPENSE",
                _label(p, 48, "Chi phí lãi và các chi phí tương tự"),
                _value(p, 49, "(13.576.823)"),
                _value(p, 50, "(9.388.783)"),
                topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
            ),
            _mapping(
                1152,
                "DEPOSIT_INTEREST",
                _label(p, 51, "Trả lãi tiền gửi"),
                _value(p, 52, "(11.054.969)"),
                _value(p, 53, "(7.899.206)"),
            ),
            _mapping(
                1153,
                "BORROWING_INTEREST",
                _label(p, 54, "Trả lãi tiền vay"),
                _value(p, 55, "(1.321.265)"),
                _value(p, 56, "(757.502)"),
            ),
            _mapping(
                1154,
                "ISSUED_PAPER_INTEREST",
                _label(p, 57, "Trả lãi phát hành giấy tờ có giá"),
                _value(p, 58, "(1.147.328)"),
                _value(p, 59, "(718.758)"),
            ),
            _mapping(
                1156,
                "OTHER_CREDIT_EXPENSE",
                _label(p, 60, "Chi phí hoạt động tín dụng khác"),
                _value(p, 61, "(53.261)"),
                _value(p, 62, "(13.317)"),
            ),
        ],
        presentation="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
    )
    return [acb, mbb, vpb, hdb, vcb, ctg, bid, vib]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0081"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0081:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex interest-expense pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return income._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return income.foundation._page(document, page_sequence, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any], semantic_document: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    page_number = item["page_sequence"]
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    line_index = item["line_index"]
    axis_line = income.foundation.support._axis_line(axis_page, line_index)
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
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            t["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for t in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            v["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for t in trials
            for m in t["verified_mappings"]
            for v in m["values"]
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": sum(
            len(m["values"]) for t in trials for m in t["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("interest-expense result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "INTEREST_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("interest-expense result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {"VERIFIED_BY_CODEX", "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"}
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
        ):
            raise _error("interest-expense trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0081:result:" + canonical_json_sha256_v1(material):
        raise _error("interest-expense result identity drifted")
    return canonical_clone_v1(value)


def build_interest_expense_8bank_codex_verified_mapping_v1(
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
        or structure_scan.get("state") != "FULL_DOCUMENT_INTEREST_EXPENSE_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic axis, crop manifest, or structure scan drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed region is not the unique whole-PDF interest-expense graph")
        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                page_number = ref["page_sequence"]
                axis_page = _page(axis_document, page_number, "accounting axis")
                semantic_page = _page(semantic_document, page_number, "semantic index")
                crop_page = _page(crop_document, page_number, "crop manifest")
                source_texts = income.foundation.support._source_line_axis(crop_page)
                evidence = income.foundation.support._source_value(
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
                    proposal_value = income.foundation.support._money(
                        evidence["fresh_vietocr_numeric_proposal"]
                    )
                except ValueError:
                    proposal_value = None
                value_cache[key] = {
                    **evidence,
                    "fresh_vietocr_numeric_status": "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                    if proposal_value == evidence["normalized_value"]
                    else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER",
                    "page_sequence": page_number,
                }
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        by_id: dict[int, dict[str, Any]] = {}
        for mapping in reviewed["mappings"]:
            result_mapping = {
                "label_evidence": _semantic_evidence(
                    axis_document, semantic_document, mapping["label"]
                ),
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": [
                    {"axis_role": axis_role, **verified(ref)}
                    for axis_role, ref in mapping["values"].items()
                ],
            }
            verified_mappings.append(result_mapping)
            by_id[mapping["report_norm_id"]] = result_mapping
        parent = by_id[1151]
        children = [by_id[rid] for rid in (1152, 1153, 1154, 1156)]
        equations = []
        for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            terms = [
                next(value for value in mapping["values"] if value["axis_role"] == axis_role)
                for mapping in children
            ]
            total = next(value for value in parent["values"] if value["axis_role"] == axis_role)
            computed = sum(term["normalized_value"] for term in terms)
            if computed != total["normalized_value"]:
                raise _error(
                    f"interest-expense parent equation does not close for {code}/{axis_role}"
                )
            equations.append(
                {
                    "axis_role": axis_role,
                    "computed_value": computed,
                    "name": "PARENT_TOTAL_EQUALS_DIRECT_VISIBLE_CHILDREN",
                    "status": "VERIFIED_EXACT",
                    "term_report_norm_ids": [1152, 1153, 1154, 1156],
                    "visible_total": total["normalized_value"],
                }
            )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        page_number = reviewed["page_span"][0]
        semantic_page = _page(semantic_document, page_number, "semantic index")
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "finance_lease_interest_disposition": "NOT_OBSERVED_IN_BOUND_DISCLOSURE_REGION",
                "owner_evidence": _semantic_evidence(
                    axis_document, semantic_document, reviewed["owner"]
                ),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "source_geometry_mode": semantic_page["geometry_mode"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                else "VERIFIED_BY_CODEX",
                "structure_graph_id": matcher["result_id"],
                "unit_evidence": [
                    _semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
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
        "schema_family": {
            "family_end_display_order": 698,
            "family_root": _schema_binding(schema_by_id.get(1151), 1151),
            "mapped_report_norm_ids": [1151, 1152, 1153, 1154, 1156],
            "not_observed_report_norm_ids": [1155],
            "section_root": _schema_binding(schema_by_id.get(1142), 1142),
        },
        "state": "INTEREST_EXPENSE_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0081:result:" + canonical_json_sha256_v1(material)}
    )


def validate_interest_expense_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_interest_expense_8bank_codex_verified_mapping_v1(
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
        raise _error("interest-expense verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def build_live_interest_expense_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_interest_expense_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_interest_expense_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_interest_expense_8bank_codex_verified_mapping_v1(value: Any) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_interest_expense_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_interest_expense_8bank_codex_verified_mapping_replay_v1(
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
        _write(RESULT_PATH, build_live_interest_expense_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_interest_expense_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
