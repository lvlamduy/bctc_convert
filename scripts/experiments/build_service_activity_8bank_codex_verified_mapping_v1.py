"""Verify detailed service-activity disclosures in the fixed eight reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

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
    "interest_income_support_for_service_activity_mapping",
    "build_interest_income_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "service_activity_scan_for_verified_mapping",
    "scan_service_activity_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "SERVICE_ACTIVITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "SERVICE_ACTIVITY_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_SERVICE_"
    "ACTIVITY_GRAPH_VISIBLE_PDF_LABEL_PADDLEOCR_OR_NATIVE_SOURCE_NUMERIC_"
    "CHALLENGER_RENDER_PIXEL_DASH_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_"
    "SCHEMA_ONLY_NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0082-service-activity-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0082-service-activity-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "safdsv1:scan:ee086b67691a6cf777afb3e49758250a571a8fa4920305b1771d15f4664adcc9"

_SCHEMA_EXPECTED = {
    1157: ("Thu nhập từ hoạt động dịch vụ", 1142, 700),
    6021: ("Thu từ dịch vụ thanh toán và ngân quỹ", 1157, 701),
    1158: ("Dịch vụ thanh toán và tiền mặt", 1157, 702),
    1160: ("Dịch vụ chứng khoán", 1157, 704),
    6022: ("Thu từ xử lý nợ, thẩm định giá và khai thác tài sản", 1157, 707),
    1163: ("Thu từ nghiệp vụ ủy thác và đại lý", 1157, 708),
    1164: ("Hoạt động bảo hiểm", 1157, 709),
    5986: ("Thu từ dịch vụ tư vấn", 1157, 711),
    1166: ("Các dịch vụ khác", 1157, 712),
    1167: ("Chi phí từ hoạt động dịch vụ", 1142, 713),
    6023: ("Chi về dịch vụ thanh toán và ngân quỹ", 1167, 714),
    1168: ("Dịch vụ thanh toán", 1167, 715),
    1170: ("Dịch vụ môi giới chứng khoán", 1167, 717),
    6024: ("Chi phí hoa hồng môi giới", 1170, 718),
    6025: ("Chi về hoạt động môi giới chứng khoán", 1170, 719),
    1171: ("Hoạt động bảo hiểm", 1167, 720),
    1172: ("Chi về dịch vụ ủy thác và đại lý", 1167, 721),
    1173: ("Chi về dịch vụ viễn thông, nghiệp vụ ủy thác và đại lý", 1167, 722),
    5987: ("Chi về dịch vụ tư vấn", 1167, 723),
    5988: ("Chi về xử lý nợ, thẩm định giá và khai thác tài sản", 1167, 724),
    1174: ("Chi phí hoạt động khác", 1167, 725),
    5989: ("Lãi thuần từ hoạt động dịch vụ", 1142, 726),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_three_reviewed_detailed_service_regions": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "render_pixel_dash_used_only_for_visible_dash_zero": True,
    "statement_totals_or_segment_report_relabelled_as_detailed_note": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "optional_service_rows_required_in_every_bank": False,
    "paddleocr_or_native_source_axis_used_as_semantic_anchor": False,
    "source_subtotals_and_children_double_counted": False,
    "statement_and_segment_near_regions_preserved_as_negative_controls": True,
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


class ServiceActivity8BankCodexVerifiedMappingV1Error(ValueError):
    """The service structure, pixel, numeric, equation or schema evidence drifted."""


def _error(message: str) -> ServiceActivity8BankCodexVerifiedMappingV1Error:
    return ServiceActivity8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {
        "kind": "AUTHENTICATED_LINE",
        "line_index": line,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _dash(page: int, bbox: Sequence[int], pixel_rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "page_sequence": page,
        "pixel_rgb_sha256": pixel_rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    report_norm_id: int,
    role: str,
    label: dict[str, Any],
    current: dict[str, Any],
    comparative: dict[str, Any],
    *,
    topology: str = "DIRECT_VISIBLE_ROW_TWO_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "label": label,
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
    }


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    periods: Sequence[dict[str, Any]],
    units: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    presentation: str,
    *,
    source_period: str = "2026-06-30",
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "mappings": list(mappings),
        "owner": _label(page, owner_line, owner_text),
        "page_span": [page, page],
        "period_axis": list(periods),
        "presentation": presentation,
        "source_period": source_period,
        "unit_evidence": list(units),
    }


def _absent(code: str, pages: Sequence[int], reason: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "disposition": "CONFIRMED_NOT_PRESENT_AS_DETAILED_SERVICE_NOTE_IN_BOUND_REPORT",
            "near_region_pages": list(pages),
            "reason": reason,
        },
        "bank_code": code,
        "mappings": [],
        "owner": None,
        "page_span": None,
        "period_axis": [],
        "presentation": "NO_DETAILED_SERVICE_NOTE",
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    p = 46
    mbb = _doc(
        "MBB",
        p,
        50,
        "Lãi thuần từ hoạt động dịch vụ",
        [
            _label(p, 51, "Từ 01/01/2026"),
            _label(p, 53, "đến 30/06/2026"),
            _label(p, 52, "Từ 01/01/2025"),
            _label(p, 54, "đến 30/06/2025"),
        ],
        [_label(p, 55, "Triệu đồng"), _label(p, 56, "Triệu đồng")],
        [
            _mapping(
                1157,
                "INCOME_PARENT",
                _label(p, 57, "Thu nhập từ hoạt động dịch vụ"),
                _line(p, 80, "9.833.528"),
                _line(p, 81, "8.225.836"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                6021,
                "INCOME_PAYMENT_TREASURY",
                _label(p, 58, "Thu từ dịch vụ thanh toán và ngân quỹ"),
                _line(p, 59, "2.564.917"),
                _line(p, 60, "1.679.921"),
            ),
            _mapping(
                5986,
                "INCOME_CONSULTING",
                _label(p, 61, "Thu từ dịch vụ tư vấn"),
                _line(p, 62, "353.414"),
                _line(p, 63, "538.289"),
            ),
            _mapping(
                1164,
                "INCOME_INSURANCE",
                _label(p, 64, "Thu từ kinh doanh và dịch vụ bảo hiểm"),
                _line(p, 65, "5.051.364"),
                _line(p, 66, "4.578.594"),
            ),
            _mapping(
                1163,
                "INCOME_TRUST_AGENCY",
                _label(p, 67, "Thu từ dịch vụ đại lý nhận ủy thác"),
                _line(p, 68, "61.285"),
                _line(p, 69, "12.272"),
            ),
            _mapping(
                6022,
                "INCOME_DEBT_VALUATION",
                _label(p, 70, "Thu từ xử lý nợ, thẩm định giá và khai thác tài sản"),
                _line(p, 72, "80.604"),
                _line(p, 73, "250.580"),
            ),
            _mapping(
                1160,
                "INCOME_BROKERAGE",
                _label(p, 74, "Thu từ hoạt động môi giới chứng khoán"),
                _line(p, 75, "404.953"),
                _line(p, 76, "325.368"),
            ),
            _mapping(
                1166,
                "INCOME_OTHER",
                _label(p, 77, "Thu các dịch vụ khác"),
                _line(p, 78, "1.316.991"),
                _line(p, 79, "840.812"),
            ),
            _mapping(
                1167,
                "EXPENSE_PARENT",
                _label(p, 82, "Chi phí hoạt động dịch vụ"),
                _line(p, 106, "(6.319.109)"),
                _line(p, 107, "(5.074.877)"),
                topology="TRAILING_UNLABELED_PARENT_TOTAL",
            ),
            _mapping(
                6023,
                "EXPENSE_PAYMENT_TREASURY",
                _label(p, 83, "Chi về dịch vụ thanh toán và ngân quỹ"),
                _line(p, 84, "(1.339.474)"),
                _line(p, 85, "(1.153.442)"),
            ),
            _mapping(
                1172,
                "EXPENSE_TRUST_AGENCY",
                _label(p, 86, "Chi về nghiệp vụ ủy thác và đại lý"),
                _line(p, 87, "(11.695)"),
                _line(p, 88, "(10.829)"),
            ),
            _mapping(
                5987,
                "EXPENSE_CONSULTING",
                _label(p, 89, "Chi về dịch vụ tư vấn"),
                _dash(
                    p,
                    [1197, 1631, 1213, 1642],
                    "07a293394d9a977c22843a3e661b4a16f916d2b52b888e0136668aff7cc3a477",
                ),
                _dash(
                    p,
                    [1472, 1631, 1488, 1642],
                    "d42b56fc4dee5bdb7b42a7f403aa9aa06255238637c19a156c38239b12759a36",
                ),
            ),
            _mapping(
                6024,
                "EXPENSE_BROKERAGE_COMMISSION",
                _label(p, 90, "Chi phí hoa hồng môi giới"),
                _line(p, 91, "(1.005.707)"),
                _line(p, 92, "(408.931)"),
            ),
            _mapping(
                1171,
                "EXPENSE_INSURANCE",
                _label(p, 93, "Chi về hoạt động kinh doanh bảo hiểm"),
                _line(p, 94, "(3.664.752)"),
                _line(p, 95, "(3.185.772)"),
            ),
            _mapping(
                5988,
                "EXPENSE_DEBT_VALUATION",
                _label(p, 96, "Chi về xử lý nợ, thẩm định giá và khai thác tài sản"),
                _line(p, 98, "(131.046)"),
                _line(p, 99, "(157.689)"),
            ),
            _mapping(
                6025,
                "EXPENSE_SECURITIES_BROKERAGE",
                _label(p, 100, "Chi về hoạt động môi giới chứng khoán"),
                _line(p, 101, "(102.943)"),
                _line(p, 102, "(77.471)"),
            ),
            _mapping(
                1174,
                "EXPENSE_OTHER",
                _label(p, 103, "Chi các dịch vụ khác"),
                _line(p, 104, "(63.492)"),
                _line(p, 105, "(80.743)"),
            ),
            _mapping(
                5989,
                "NET_SERVICE_ACTIVITY",
                _label(p, 108, "Lãi thuần từ hoạt động dịch vụ"),
                _line(p, 109, "3.514.419"),
                _line(p, 110, "3.150.959"),
            ),
        ],
        "TRAILING_INCOME_AND_EXPENSE_TOTALS_LABELLED_TRAILING_NET",
    )

    p = 62
    vpb = _doc(
        "VPB",
        p,
        70,
        "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ",
        [
            _label(p, 73, "3 tháng kết thúc"),
            _label(p, 75, "ngày 31 tháng 3"),
            _label(p, 77, "năm 2026"),
            _label(p, 74, "3 tháng kết thúc"),
            _label(p, 76, "ngày 31 tháng 3"),
            _label(p, 78, "năm 2025"),
        ],
        [_label(p, 80, "Triệu đồng"), _label(p, 81, "Triệu đồng")],
        [
            _mapping(
                1157,
                "INCOME_PARENT",
                _label(p, 82, "Thu nhập từ hoạt động dịch vụ"),
                _line(p, 83, "3.843.225"),
                _line(p, 84, "2.850.616"),
                topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
            ),
            _mapping(
                6021,
                "INCOME_PAYMENT_TREASURY",
                _label(p, 85, "Thu từ dịch vụ thanh toán và ngân quỹ"),
                _line(p, 86, "547.871"),
                _line(p, 87, "562.124"),
            ),
            _mapping(
                5986,
                "INCOME_CONSULTING",
                _label(p, 88, "Thu từ dịch vụ tư vấn"),
                _line(p, 89, "34.812"),
                _line(p, 90, "19.711"),
            ),
            _mapping(
                1164,
                "INCOME_INSURANCE",
                _label(p, 91, "Thu từ kinh doanh và dịch vụ bảo hiểm"),
                _line(p, 92, "1.559.367"),
                _line(p, 93, "1.138.928"),
            ),
            _mapping(
                1158,
                "INCOME_CARD",
                _label(p, 94, "Thu phí liên quan đến các loại thẻ"),
                _line(p, 95, "545.450"),
                _line(p, 96, "523.100"),
            ),
            _mapping(
                1166,
                "INCOME_OTHER",
                _label(p, 97, "Thu khác"),
                _line(p, 98, "1.155.725"),
                _line(p, 99, "606.753"),
            ),
            _mapping(
                1167,
                "EXPENSE_PARENT",
                _label(p, 100, "Chi phí hoạt động dịch vụ"),
                _line(p, 101, "(1.778.702)"),
                _line(p, 102, "(1.708.591)"),
                topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
            ),
            _mapping(
                6023,
                "EXPENSE_PAYMENT_TREASURY",
                _label(p, 103, "Chi về dịch vụ thanh toán và ngân quỹ"),
                _line(p, 104, "(339.887)"),
                _line(p, 105, "(383.419)"),
            ),
            _mapping(
                1171,
                "EXPENSE_INSURANCE",
                _label(p, 106, "Chi về dịch vụ bảo hiểm"),
                _line(p, 107, "(545.414)"),
                _line(p, 108, "(420.269)"),
            ),
            _mapping(
                6024,
                "EXPENSE_BROKERAGE_COMMISSION",
                _label(p, 109, "Hoa hồng môi giới"),
                _line(p, 110, "(128.826)"),
                _line(p, 111, "(114.012)"),
            ),
            _mapping(
                1168,
                "EXPENSE_CARD",
                _label(p, 112, "Hoạt động thẻ"),
                _line(p, 113, "(340.507)"),
                _line(p, 114, "(311.663)"),
            ),
            _mapping(
                1174,
                "EXPENSE_OTHER",
                _label(p, 115, "Chi khác"),
                _line(p, 116, "(424.068)"),
                _line(p, 117, "(479.228)"),
            ),
            _mapping(
                5989,
                "NET_SERVICE_ACTIVITY",
                _label(p, 70, "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ"),
                _line(p, 118, "2.064.523"),
                _line(p, 119, "1.142.025"),
                topology="TRAILING_UNLABELED_NET_TOTAL",
            ),
        ],
        "LEADING_INCOME_AND_EXPENSE_TOTALS_UNLABELLED_TRAILING_NET",
        source_period="2026-03-31",
    )

    p = 45
    vib = _doc(
        "VIB",
        p,
        67,
        "LÃI THUẦN TỪ HOẠT ĐỘNG DỊCH VỤ",
        [
            _label(p, 68, "6 tháng đầu"),
            _label(p, 70, "năm 2026"),
            _label(p, 69, "6 tháng đầu"),
            _label(p, 71, "năm 2025"),
        ],
        [_label(p, 72, "triệu đồng"), _label(p, 73, "triệu đồng")],
        [
            _mapping(
                1157,
                "INCOME_PARENT",
                _label(p, 74, "Thu nhập từ hoạt động dịch vụ"),
                _line(p, 75, "4.172.405"),
                _line(p, 76, "1.725.358"),
                topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
            ),
            _mapping(
                1158,
                "INCOME_PAYMENT",
                _label(p, 77, "Dịch vụ thanh toán"),
                _line(p, 78, "3.202.296"),
                _line(p, 79, "1.358.475"),
            ),
            _mapping(
                1164,
                "INCOME_INSURANCE",
                _label(p, 80, "Dịch vụ đại lý bảo hiểm"),
                _line(p, 81, "790.046"),
                _line(p, 82, "191.050"),
            ),
            _mapping(
                1166,
                "INCOME_OTHER",
                _label(p, 83, "Dịch vụ khác"),
                _line(p, 84, "180.063"),
                _line(p, 85, "175.833"),
            ),
            _mapping(
                1167,
                "EXPENSE_PARENT",
                _label(p, 86, "Chi phí hoạt động dịch vụ"),
                _line(p, 87, "(1.107.944)"),
                _line(p, 88, "(946.590)"),
                topology="LEADING_PARENT_TOTAL_BEFORE_CHILDREN",
            ),
            _mapping(
                1168,
                "EXPENSE_PAYMENT",
                _label(p, 89, "Dịch vụ thanh toán"),
                _line(p, 90, "(838.257)"),
                _line(p, 91, "(708.287)"),
            ),
            _mapping(
                1173,
                "EXPENSE_TELECOM",
                _label(p, 92, "Cước phí bưu điện về mạng viễn thông"),
                _line(p, 93, "(38.787)"),
                _line(p, 94, "(37.808)"),
            ),
            _mapping(
                1172,
                "EXPENSE_TRUST_AGENCY",
                _label(p, 95, "Dịch vụ ủy thác và đại lý"),
                _line(p, 96, "(33.697)"),
                _line(p, 97, "(40.927)"),
            ),
            _mapping(
                1171,
                "EXPENSE_INSURANCE",
                _label(p, 98, "Dịch vụ đại lý bảo hiểm"),
                _line(p, 99, "(65.191)"),
                _line(p, 100, "(18.967)"),
            ),
            _mapping(
                1170,
                "EXPENSE_BROKERAGE",
                _label(p, 101, "Dịch vụ môi giới"),
                _line(p, 102, "(102.629)"),
                _line(p, 103, "(94.894)"),
            ),
            _mapping(
                1174,
                "EXPENSE_OTHER",
                _label(p, 104, "Dịch vụ khác"),
                _line(p, 105, "(29.383)"),
                _line(p, 106, "(45.707)"),
            ),
            _mapping(
                5989,
                "NET_SERVICE_ACTIVITY",
                _label(p, 107, "Lãi thuần từ hoạt động dịch vụ"),
                _line(p, 108, "3.064.461"),
                _line(p, 109, "778.768"),
            ),
        ],
        "LEADING_INCOME_AND_EXPENSE_TOTALS_LABELLED_TRAILING_NET",
    )

    return [
        _absent(
            "ACB", [6], "Only the KQKD aggregate trio is present; no detailed service children."
        ),
        mbb,
        vpb,
        _absent(
            "HDB", [6], "Only the KQKD aggregate trio is present; no detailed service children."
        ),
        _absent(
            "VCB",
            [10, 42, 43],
            "KQKD totals and segment-report rows lack detailed service children.",
        ),
        _absent(
            "CTG", [6], "Only the KQKD aggregate trio is present; no detailed service children."
        ),
        _absent(
            "BID", [7], "Only the KQKD aggregate trio is present; no detailed service children."
        ),
        vib,
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": "E-0082",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0082:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex service-activity pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return income._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return income.foundation._page(document, page_sequence, label)


def _semantic_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    item: Mapping[str, Any],
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


def _pixel_dash_value(crop_page: Mapping[str, Any], ref: Mapping[str, Any]) -> dict[str, Any]:
    payload = income.foundation.support._artifact_bytes(
        crop_page.get("render_binding"), "page render"
    )
    image = Image.open(io.BytesIO(payload)).convert("RGB")
    left, top, right, bottom = ref["bbox"]
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise _error("authenticated pixel dash bbox is out of bounds")
    digest = hashlib.sha256(image.crop((left, top, right, bottom)).tobytes()).hexdigest()
    if digest != ref["pixel_rgb_sha256"]:
        raise _error("authenticated pixel dash crop drifted")
    return {
        "fresh_vietocr_numeric_proposal": None,
        "fresh_vietocr_numeric_status": "NO_SEMANTIC_LINE_FOR_VISIBLE_DASH",
        "normalized_value": 0,
        "page_sequence": ref["page_sequence"],
        "pixel_bbox": list(ref["bbox"]),
        "pixel_rgb_sha256": digest,
        "pixel_transcription": "-",
        "render_ref": canonical_clone_v1(crop_page["render_binding"]),
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": (
            "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        ),
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            value.get("source_numeric_challenger_status")
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
        "detailed_note_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value.get("fresh_vietocr_numeric_status") == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
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
        raise _error("service-activity result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "SERVICE_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("service-activity result identity or metrics drifted")
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
            raise _error("service-activity trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0082:result:" + canonical_json_sha256_v1(material):
        raise _error("service-activity result identity drifted")
    return canonical_clone_v1(value)


def _equations(
    mappings: Sequence[Mapping[str, Any]], by_role: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    result = []
    for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):

        def axis(mapping: Mapping[str, Any], *, axis_role: str = axis_role) -> Mapping[str, Any]:
            return next(value for value in mapping["values"] if value["axis_role"] == axis_role)

        income_children = [
            m for m in mappings if m["role"].startswith("INCOME_") and m["role"] != "INCOME_PARENT"
        ]
        expense_children = [
            m
            for m in mappings
            if m["role"].startswith("EXPENSE_") and m["role"] != "EXPENSE_PARENT"
        ]
        for name, children, parent in (
            ("INCOME_CHILDREN_EQUAL_PRINTED_PARENT", income_children, by_role["INCOME_PARENT"]),
            ("EXPENSE_CHILDREN_EQUAL_PRINTED_PARENT", expense_children, by_role["EXPENSE_PARENT"]),
        ):
            terms = [axis(child) for child in children]
            total = axis(parent)
            computed = sum(term["normalized_value"] for term in terms)
            if computed != total["normalized_value"]:
                raise _error(f"service accounting equation does not close: {name} {axis_role}")
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
        net = axis(by_role["NET_SERVICE_ACTIVITY"])
        computed = income["normalized_value"] + expense["normalized_value"]
        if computed != net["normalized_value"]:
            raise _error(f"service net equation does not close: {axis_role}")
        result.append(
            {
                "computed_value": computed,
                "equation": "INCOME_PLUS_EXPENSE_EQUALS_NET_SERVICE_ACTIVITY",
                "period_role": axis_role,
                "status": "CORROBORATED_EXACT",
                "term_report_norm_ids": [1157, 1167],
                "total_report_norm_id": 5989,
            }
        )
    return result


def build_service_activity_8bank_codex_verified_mapping_v1(
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
                raise _error("absent detailed service note unexpectedly matched")
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
            raise _error("reviewed region is not the unique whole-PDF service graph")
        page_number = reviewed["page_span"][0]
        axis_document = _document(axis_projection["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_texts = income.foundation.support._source_line_axis(crop_page)
        verified_mappings = []
        for mapping in reviewed["mappings"]:
            values = []
            for axis_role, ref in mapping["values"].items():
                if ref["kind"] == "AUTHENTICATED_LINE":
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
                        proposal = income.foundation.support._money(
                            evidence["fresh_vietocr_numeric_proposal"]
                        )
                    except ValueError:
                        proposal = None
                    evidence = {
                        **evidence,
                        "fresh_vietocr_numeric_status": (
                            "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                            if proposal == evidence["normalized_value"]
                            else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                        ),
                        "page_sequence": ref["page_sequence"],
                    }
                elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
                    evidence = _pixel_dash_value(crop_page, ref)
                else:
                    raise _error("service value reference kind drifted")
                values.append({"axis_role": axis_role, **evidence})
            verified_mappings.append(
                {
                    "label_evidence": _semantic_evidence(
                        axis_document, semantic_document, mapping["label"]
                    ),
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]),
                        mapping["report_norm_id"],
                    ),
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": values,
                }
            )
        by_role = {mapping["role"]: mapping for mapping in verified_mappings}
        equations = _equations(verified_mappings, by_role)
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
            "expense_parent_report_norm_id": 1167,
            "income_parent_report_norm_id": 1157,
            "net_report_norm_id": 5989,
        },
        "state": "SERVICE_ACTIVITY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0082:result:" + canonical_json_sha256_v1(material)}
    )


def validate_service_activity_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_service_activity_8bank_codex_verified_mapping_v1(
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
        raise _error("service-activity verified mapping does not replay exactly")
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


def build_live_service_activity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_service_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_service_activity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_service_activity_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_service_activity_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_service_activity_8bank_codex_verified_mapping_replay_v1(
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
        _write(RESULT_PATH, build_live_service_activity_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_service_activity_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
