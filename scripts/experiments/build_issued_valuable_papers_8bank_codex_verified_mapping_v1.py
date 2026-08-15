"""Verify issued valuable papers across the fixed eight-bank PDF corpus.

The complete-PDF matcher is bank blind.  This bounded review binds the one
unique region in each document to visible PDF pixels, fresh VietOCR semantic
anchors, the original numeric line axis, exact accounting equations, and the
live TM schema.  Layout variants remain explicit: vertical instrument/tenor
tables, book-value versus face-value lanes, combined promissory-note/bond
parents, and the horizontal CTG instrument-column table.
"""

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

__all__ = [
    "FORMAT_VERSION",
    "IssuedValuablePapers8BankCodexVerifiedMappingV1Error",
    "build_issued_valuable_papers_8bank_codex_verified_mapping_v1",
    "build_live_issued_valuable_papers_8bank_codex_verified_mapping_v1",
    "validate_issued_valuable_papers_8bank_codex_verified_mapping_replay_v1",
    "validate_live_issued_valuable_papers_8bank_codex_verified_mapping_v1",
]

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


foundation = _load_module(
    "government_nhnn_support_for_issued_valuable_papers",
    "build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "issued_valuable_papers_scan_for_verified_mapping",
    "scan_issued_valuable_papers_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "ISSUED_VALUABLE_PAPERS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ISSUED_VALUABLE_PAPERS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_ISSUED_VALUABLE_"
    "PAPERS_OWNER_INSTRUMENT_TENOR_PERIOD_UNIT_LAYOUT_PLUS_INDEPENDENT_VISIBLE_"
    "PIXEL_SOURCE_NUMERIC_CHALLENGER_DASH_ZERO_ACCOUNTING_AND_LIVE_TM_SCHEMA_"
    "ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0076-issued-valuable-papers-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "ivpfdsv1:scan:ce6ff7a92671d311354a45489164377e79cbd530d412f3c8433f6bc7c5eca1ad"

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_PRECEDES_INSTRUMENT_AND_TENOR_CHILDREN",
    "OPTIONAL_INTERMEDIATE_BRANCHES_AND_LAYOUT_AXES",
    "CURRENT_AND_COMPARATIVE_OR_SINGLE_PERIOD_AXIS",
    "LOCAL_OR_DOCUMENT_INHERITED_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "SOURCE_NUMERIC_CHALLENGER_OR_AUTHENTICATED_PIXEL_DASH",
    "INSTRUMENT_TENORS_AND_PRINTED_TOTALS_RECONCILE",
    "BROADER_OR_ALTERNATE_AXES_NOT_FORCED_INTO_NARROW_SCHEMA_LEAVES",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "dash_visible_in_authenticated_pixels_normalized_to_zero": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_SOURCE_NUMERIC_CHALLENGER_OR_BOUND_DASH_CROP",
    "old_ocr_used_as_semantic_anchor": False,
    "optional_children_required_in_every_bank": False,
    "source_rows_without_equivalent_schema_forced_into_nearest_item": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "dash_zero_semantics_require_visible_authenticated_pixel_crop": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_issued_valuable_paper_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_retained": True,
    "upstream_source_text_used_only_as_numeric_challenger": True,
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
_SCHEMA_EXPECTED = {
    1100: ("Phát hành giấy tờ có giá", 560, 606),
    1101: ("Chứng chỉ tiền gửi", 1100, 607),
    1102: ("Dưới 12 tháng", 1100, 612),
    1103: ("Từ 12 tháng đến dưới 5 năm", 1100, 613),
    1104: ("Trên 5 năm", 1100, 614),
    1105: ("Kỳ phiếu", 1100, 615),
    1106: ("Dưới 12 tháng", 1100, 616),
    1107: ("Từ 12 tháng đến dưới 5 năm", 1100, 617),
    1108: ("Trên 5 năm", 1100, 618),
    1109: ("Trái phiếu", 1100, 619),
    1110: ("Dưới 12 tháng", 1100, 623),
    1111: ("Từ 12 tháng đến dưới 5 năm", 1100, 624),
    1112: ("Trên 5 năm", 1100, 625),
    1113: ("Tổng kỳ phiếu và trái phiếu", 1100, 626),
    1114: ("Dưới 12 tháng", 1100, 627),
    1115: ("Từ 12 tháng đến dưới 5 năm", 1100, 628),
    1116: ("Trên 5 năm", 1100, 629),
    1117: ("Các loại giấy tờ có giá khác", 1100, 630),
}


class IssuedValuablePapers8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel, numeric, accounting, or schema evidence drifted."""


def _error(message: str) -> IssuedValuablePapers8BankCodexVerifiedMappingV1Error:
    return IssuedValuablePapers8BankCodexVerifiedMappingV1Error(message)


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str, multiplier: int = 1) -> dict[str, Any]:
    return {
        "kind": "AUTHENTICATED_LINE",
        "line_index": line,
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _dash(page: int, bbox: Sequence[int], pixel_rgb_sha256: str) -> dict[str, Any]:
    return {
        "bbox": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "multiplier": 1,
        "page_sequence": page,
        "pixel_rgb_sha256": pixel_rgb_sha256,
        "pixel_transcription": "-",
    }


def _mapping(
    report_norm_id: int,
    role: str,
    labels: Sequence[dict[str, Any]],
    values: Mapping[str, Sequence[dict[str, Any]]],
    topology: str,
) -> dict[str, Any]:
    return {
        "labels": list(labels),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {key: list(items) for key, items in values.items()},
    }


def _equation(
    name: str, period_role: str, terms: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"name": name, "period_role": period_role, "terms": list(terms), "total": total}


def _unmapped(
    item_id: str,
    labels: Sequence[dict[str, Any]],
    values: Mapping[str, Sequence[dict[str, Any]]],
    reason: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "labels": list(labels),
        "reason": reason,
        "status": "UNRESOLVED",
        "values": {key: list(items) for key, items in values.items()},
    }


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    periods: Sequence[dict[str, Any]],
    units: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    unmapped: Sequence[dict[str, Any]] = (),
    *,
    source_period: str = "2026-06-30",
    presentation: str = "VERTICAL_INSTRUMENT_THEN_TENOR_ROWS",
    unit_authority: str = "VISIBLE_PAGE_MILLION_VND",
) -> dict[str, Any]:
    return {
        "bank_code": code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": (
            "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS" if unmapped else "VERIFIED_BY_CODEX"
        ),
        "equations": list(equations),
        "mappings": list(mappings),
        "owner": _label(page, owner_line, owner_text),
        "page_span": [page, page],
        "period_axis": list(periods),
        "presentation": presentation,
        "source_period": source_period,
        "unit_authority": unit_authority,
        "unit_evidence": list(units),
        "unmapped_source_rows": list(unmapped),
    }


def _review_documents() -> list[dict[str, Any]]:
    ctg_ky_medium = _dash(
        42,
        [930, 2270, 1040, 2315],
        "d0fc9c80d8ceb33dc4f3984db0260060035874b6b3723d72d891f51cc51374de",
    )
    ctg_ky_long = _dash(
        42,
        [930, 2470, 1040, 2515],
        "e23ac4307e74c0671700b402814babf8be5800b8ebc695e0e97bb0d56a1a5997",
    )
    ctg_cd_long = _dash(
        42,
        [1760, 2470, 1960, 2515],
        "1f4e2eb70b1ede66e0661e2a618fb2e388cc57c467d25fd568259acbcdee3f4a",
    )
    ctg_bond_short = _dash(
        42,
        [1090, 2008, 1610, 2055],
        "9497511575134f6108f56dd34ab1e88da8c0e01ddbbee6f6ffefb7383db37752",
    )
    documents = [
        _doc(
            "ACB",
            21,
            74,
            "11. PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
            [_label(21, 75, "30.6.2026"), _label(21, 76, "Giá trị ghi sổ")],
            [_label(21, 78, "Triệu đồng")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(21, 74, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                    {"CURRENT": [_line(21, 110, "199.012.993")]},
                    "PRINTED_BOOK_VALUE_TOTAL",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(21, 95, "Chứng chỉ tiền gửi")],
                    {"CURRENT": [_line(21, 96, "160.355.867")]},
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1102,
                    "CD_SHORT",
                    [_label(21, 95, "Chứng chỉ tiền gửi"), _label(21, 98, "Kỳ hạn dưới 1 năm")],
                    {"CURRENT": [_line(21, 99, "104.290.314")]},
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1103,
                    "CD_MEDIUM",
                    [
                        _label(21, 95, "Chứng chỉ tiền gửi"),
                        _label(21, 101, "Kỳ hạn từ 1 năm đến 2 năm"),
                        _label(21, 104, "Kỳ hạn 3 năm"),
                    ],
                    {"CURRENT": [_line(21, 102, "36.000.000"), _line(21, 105, "17.735.553")]},
                    "INSTRUMENT_CONTEXT_PLUS_MULTIPLE_MEDIUM_TENORS",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(21, 80, "Trái phiếu")],
                    {"CURRENT": [_line(21, 81, "38.657.126")]},
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1111,
                    "BOND_MEDIUM",
                    [
                        _label(21, 80, "Trái phiếu"),
                        _label(21, 83, "Kỳ hạn từ 1 năm đến 2 năm"),
                        _label(21, 86, "Kỳ hạn 3 năm"),
                    ],
                    {"CURRENT": [_line(21, 84, "25.849.503"), _line(21, 87, "5.369.727")]},
                    "INSTRUMENT_CONTEXT_PLUS_MULTIPLE_MEDIUM_TENORS",
                ),
                _mapping(
                    1112,
                    "BOND_LONG",
                    [_label(21, 80, "Trái phiếu"), _label(21, 92, "Kỳ hạn 10 năm")],
                    {"CURRENT": [_line(21, 93, "2.421.841")]},
                    "INSTRUMENT_CONTEXT_PLUS_LONG_TENOR",
                ),
            ],
            [
                _equation(
                    "BOND_PLUS_CD_TO_BOOK_TOTAL",
                    "CURRENT",
                    [_line(21, 81, "38.657.126"), _line(21, 96, "160.355.867")],
                    _line(21, 110, "199.012.993"),
                ),
                _equation(
                    "BOND_TENOR_DETAIL_TO_PARENT",
                    "CURRENT",
                    [
                        _line(21, 84, "25.849.503"),
                        _line(21, 87, "5.369.727"),
                        _line(21, 90, "5.016.055"),
                        _line(21, 93, "2.421.841"),
                    ],
                    _line(21, 81, "38.657.126"),
                ),
                _equation(
                    "CD_TENOR_DETAIL_TO_PARENT",
                    "CURRENT",
                    [
                        _line(21, 99, "104.290.314"),
                        _line(21, 102, "36.000.000"),
                        _line(21, 105, "17.735.553"),
                        _line(21, 108, "2.330.000"),
                    ],
                    _line(21, 96, "160.355.867"),
                ),
            ],
            [
                _unmapped(
                    "ACB-BOND-EXACT-5Y",
                    [_label(21, 89, "Kỳ hạn 5 năm")],
                    {"CURRENT": [_line(21, 90, "5.016.055")]},
                    "EXACT_FIVE_YEAR_TENOR_IS_NEITHER_SCHEMA_UNDER_FIVE_NOR_OVER_FIVE",
                ),
                _unmapped(
                    "ACB-CD-EXACT-5Y",
                    [_label(21, 107, "Kỳ hạn 5 năm")],
                    {"CURRENT": [_line(21, 108, "2.330.000")]},
                    "EXACT_FIVE_YEAR_TENOR_IS_NEITHER_SCHEMA_UNDER_FIVE_NOR_OVER_FIVE",
                ),
            ],
            presentation="SINGLE_PERIOD_BOOK_VALUE_AND_FACE_VALUE_COLUMNS",
        ),
        _doc(
            "MBB",
            44,
            0,
            "Phát hành giấy tờ có giá",
            [_label(44, 1, "30/06/2026"), _label(44, 2, "31/12/2025")],
            [_label(44, 3, "Triệu đồng"), _label(44, 4, "Triệu đồng")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(44, 0, "Phát hành giấy tờ có giá")],
                    {
                        "CURRENT": [_line(44, 23, "233.503.962")],
                        "COMPARATIVE": [_line(44, 24, "187.236.104")],
                    },
                    "UNLABELED_TOTAL_AFTER_INSTRUMENTS",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(44, 14, "Chứng chỉ tiền gửi")],
                    {
                        "CURRENT": [_line(44, 15, "185.970.279")],
                        "COMPARATIVE": [_line(44, 16, "140.830.150")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1102,
                    "CD_SHORT",
                    [_label(44, 14, "Chứng chỉ tiền gửi"), _label(44, 17, "Từ 12 tháng trở xuống")],
                    {
                        "CURRENT": [_line(44, 18, "90.844.018")],
                        "COMPARATIVE": [_line(44, 19, "76.253.073")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(44, 5, "Trái phiếu")],
                    {
                        "CURRENT": [_line(44, 6, "47.533.683")],
                        "COMPARATIVE": [_line(44, 7, "46.405.954")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1112,
                    "BOND_LONG",
                    [_label(44, 5, "Trái phiếu"), _label(44, 11, "Trên 5 năm")],
                    {
                        "CURRENT": [_line(44, 12, "24.723.441")],
                        "COMPARATIVE": [_line(44, 13, "23.366.789")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_LONG_TENOR",
                ),
            ],
            [
                _equation(
                    "BOND_PLUS_CD_TO_TOTAL",
                    "CURRENT",
                    [_line(44, 6, "47.533.683"), _line(44, 15, "185.970.279")],
                    _line(44, 23, "233.503.962"),
                ),
                _equation(
                    "BOND_PLUS_CD_TO_TOTAL",
                    "COMPARATIVE",
                    [_line(44, 7, "46.405.954"), _line(44, 16, "140.830.150")],
                    _line(44, 24, "187.236.104"),
                ),
            ],
            [
                _unmapped(
                    "MBB-BOND-BELOW-5Y",
                    [_label(44, 8, "Dưới 5 năm")],
                    {
                        "CURRENT": [_line(44, 9, "22.810.242")],
                        "COMPARATIVE": [_line(44, 10, "23.039.165")],
                    },
                    "BROAD_TENOR_COMBINES_SCHEMA_SHORT_AND_MEDIUM",
                ),
                _unmapped(
                    "MBB-CD-OVER-12M",
                    [_label(44, 20, "Trên 12 tháng")],
                    {
                        "CURRENT": [_line(44, 21, "95.126.261")],
                        "COMPARATIVE": [_line(44, 22, "64.577.077")],
                    },
                    "BROAD_TENOR_COMBINES_SCHEMA_MEDIUM_AND_LONG",
                ),
            ],
        ),
        _doc(
            "VPB",
            56,
            19,
            "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
            [
                _label(56, 39, "Ngày 31 tháng 3"),
                _label(56, 41, "năm 2026"),
                _label(56, 40, "Ngày 31 tháng 12"),
                _label(56, 42, "năm 2025"),
            ],
            [_label(56, 43, "Triệu đồng"), _label(56, 44, "Triệu đồng")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(56, 19, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                    {
                        "CURRENT": [_line(56, 54, "138.840.016")],
                        "COMPARATIVE": [_line(56, 55, "107.120.653")],
                    },
                    "PRINTED_TOTAL_AFTER_INSTRUMENT_VIEW",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [
                        _label(56, 45, "Chứng chỉ tiền gửi phát hành cho khách hàng cá nhân"),
                        _label(56, 48, "Chứng chỉ tiền gửi phát hành cho các tổ chức kinh tế"),
                    ],
                    {
                        "CURRENT": [_line(56, 46, "42.993.100"), _line(56, 49, "52.194.703")],
                        "COMPARATIVE": [_line(56, 47, "26.306.000"), _line(56, 50, "37.156.844")],
                    },
                    "SUM_OF_TWO_CD_POPULATIONS",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(56, 51, "Trái phiếu (*)")],
                    {
                        "CURRENT": [_line(56, 52, "43.652.213")],
                        "COMPARATIVE": [_line(56, 53, "43.657.809")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
            ],
            [
                _equation(
                    "CD_POPULATIONS_PLUS_BOND_TO_TOTAL",
                    "CURRENT",
                    [
                        _line(56, 46, "42.993.100"),
                        _line(56, 49, "52.194.703"),
                        _line(56, 52, "43.652.213"),
                    ],
                    _line(56, 54, "138.840.016"),
                ),
                _equation(
                    "CD_POPULATIONS_PLUS_BOND_TO_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(56, 47, "26.306.000"),
                        _line(56, 50, "37.156.844"),
                        _line(56, 53, "43.657.809"),
                    ],
                    _line(56, 55, "107.120.653"),
                ),
            ],
            [
                _unmapped(
                    "VPB-WHOLE-FAMILY-SHORT",
                    [
                        _label(56, 20, "Phát hành giấy tờ có giá theo kỳ hạn gốc"),
                        _label(56, 27, "Dưới 12 tháng"),
                    ],
                    {
                        "CURRENT": [_line(56, 28, "43.183.811")],
                        "COMPARATIVE": [_line(56, 29, "25.699.521")],
                    },
                    "WHOLE_FAMILY_TENOR_AXIS_IS_NOT_ONE_INSTRUMENT_SPECIFIC_SCHEMA_LEAF",
                ),
                _unmapped(
                    "VPB-WHOLE-FAMILY-MEDIUM",
                    [_label(56, 30, "Từ trên 12 tháng đến 5 năm")],
                    {
                        "CURRENT": [_line(56, 31, "70.378.837")],
                        "COMPARATIVE": [_line(56, 32, "72.134.379")],
                    },
                    "WHOLE_FAMILY_TENOR_AXIS_IS_NOT_ONE_INSTRUMENT_SPECIFIC_SCHEMA_LEAF",
                ),
                _unmapped(
                    "VPB-WHOLE-FAMILY-LONG",
                    [_label(56, 33, "Từ trên 5 năm trở lên")],
                    {
                        "CURRENT": [_line(56, 34, "25.277.368")],
                        "COMPARATIVE": [_line(56, 35, "9.286.753")],
                    },
                    "WHOLE_FAMILY_TENOR_AXIS_IS_NOT_ONE_INSTRUMENT_SPECIFIC_SCHEMA_LEAF",
                ),
            ],
            source_period="2026-03-31",
            presentation="TWO_ALTERNATE_VIEWS_WHOLE_FAMILY_TENOR_AND_INSTRUMENT_POPULATION",
        ),
        _doc(
            "HDB",
            31,
            60,
            "Phát hành giấy tờ có giá thông thường (không bao gồm công cụ tài chính phức hợp)",
            [_label(31, 61, "Số cuối kỳ"), _label(31, 62, "Số đầu kỳ")],
            [_label(31, 63, "Triệu VND"), _label(31, 64, "Triệu VND")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(31, 60, "Phát hành giấy tờ có giá thông thường")],
                    {
                        "CURRENT": [_line(31, 86, "103.010.954")],
                        "COMPARATIVE": [_line(31, 87, "83.106.603")],
                    },
                    "PRINTED_TOTAL_AFTER_INSTRUMENTS",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(31, 65, "Chứng chỉ tiền gửi")],
                    {
                        "CURRENT": [_line(31, 66, "44.491.000")],
                        "COMPARATIVE": [_line(31, 67, "24.972.000")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1102,
                    "CD_SHORT",
                    [_label(31, 65, "Chứng chỉ tiền gửi"), _label(31, 68, "Dưới 12 tháng")],
                    {
                        "CURRENT": [_line(31, 69, "38.559.000")],
                        "COMPARATIVE": [_line(31, 70, "18.710.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1103,
                    "CD_MEDIUM",
                    [
                        _label(31, 65, "Chứng chỉ tiền gửi"),
                        _label(31, 71, "Từ 12 tháng đến dưới 05 năm"),
                    ],
                    {
                        "CURRENT": [_line(31, 72, "5.717.000")],
                        "COMPARATIVE": [_line(31, 73, "6.047.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1104,
                    "CD_LONG",
                    [_label(31, 65, "Chứng chỉ tiền gửi"), _label(31, 74, "Từ 05 năm trở lên")],
                    {
                        "CURRENT": [_line(31, 75, "215.000")],
                        "COMPARATIVE": [_line(31, 76, "215.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(31, 77, "Trái phiếu thường")],
                    {
                        "CURRENT": [_line(31, 78, "58.519.954")],
                        "COMPARATIVE": [_line(31, 79, "58.134.603")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1111,
                    "BOND_MEDIUM",
                    [
                        _label(31, 77, "Trái phiếu thường"),
                        _label(31, 80, "Từ 12 tháng đến dưới 05 năm"),
                    ],
                    {
                        "CURRENT": [_line(31, 81, "16.222.511")],
                        "COMPARATIVE": [_line(31, 82, "18.213.965")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1112,
                    "BOND_LONG",
                    [_label(31, 77, "Trái phiếu thường"), _label(31, 83, "Từ 05 năm trở lên")],
                    {
                        "CURRENT": [_line(31, 84, "42.297.443")],
                        "COMPARATIVE": [_line(31, 85, "39.920.638")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
            ],
            [
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "CURRENT",
                    [
                        _line(31, 69, "38.559.000"),
                        _line(31, 72, "5.717.000"),
                        _line(31, 75, "215.000"),
                    ],
                    _line(31, 66, "44.491.000"),
                ),
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [
                        _line(31, 70, "18.710.000"),
                        _line(31, 73, "6.047.000"),
                        _line(31, 76, "215.000"),
                    ],
                    _line(31, 67, "24.972.000"),
                ),
                _equation(
                    "BOND_TENORS_TO_PARENT",
                    "CURRENT",
                    [_line(31, 81, "16.222.511"), _line(31, 84, "42.297.443")],
                    _line(31, 78, "58.519.954"),
                ),
                _equation(
                    "BOND_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [_line(31, 82, "18.213.965"), _line(31, 85, "39.920.638")],
                    _line(31, 79, "58.134.603"),
                ),
                _equation(
                    "BOND_PLUS_CD_TO_TOTAL",
                    "CURRENT",
                    [_line(31, 66, "44.491.000"), _line(31, 78, "58.519.954")],
                    _line(31, 86, "103.010.954"),
                ),
                _equation(
                    "BOND_PLUS_CD_TO_TOTAL",
                    "COMPARATIVE",
                    [_line(31, 67, "24.972.000"), _line(31, 79, "58.134.603")],
                    _line(31, 87, "83.106.603"),
                ),
            ],
        ),
        _doc(
            "VCB",
            35,
            40,
            "12. Phát hành giấy tờ có giá",
            [_label(35, 41, "30/6/2026"), _label(35, 42, "31/12/2025")],
            [_label(35, 43, "Triệu VND"), _label(35, 44, "Triệu VND")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(35, 40, "Phát hành giấy tờ có giá")],
                    {
                        "CURRENT": [_line(35, 77, "39.345.465")],
                        "COMPARATIVE": [_line(35, 78, "27.101.221")],
                    },
                    "PRINTED_TOTAL_AFTER_INSTRUMENTS",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(35, 46, "Chứng chỉ tiền gửi")],
                    {
                        "CURRENT": [_line(35, 47, "29.340.321")],
                        "COMPARATIVE": [_line(35, 48, "17.596.115")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1102,
                    "CD_SHORT",
                    [_label(35, 46, "Chứng chỉ tiền gửi"), _label(35, 49, "Ngắn hạn bằng VND")],
                    {
                        "CURRENT": [_line(35, 50, "28.313.473")],
                        "COMPARATIVE": [_line(35, 51, "17.096.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_CURRENCY_TENOR",
                ),
                _mapping(
                    1103,
                    "CD_MEDIUM",
                    [_label(35, 46, "Chứng chỉ tiền gửi"), _label(35, 52, "Trung hạn bằng VND")],
                    {"CURRENT": [_line(35, 53, "26.848")], "COMPARATIVE": [_line(35, 54, "115")]},
                    "INSTRUMENT_CONTEXT_PLUS_CURRENCY_TENOR",
                ),
                _mapping(
                    1104,
                    "CD_LONG",
                    [_label(35, 46, "Chứng chỉ tiền gửi"), _label(35, 55, "Dài hạn bằng VND")],
                    {
                        "CURRENT": [_line(35, 56, "1.000.000")],
                        "COMPARATIVE": [_line(35, 57, "500.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_CURRENCY_TENOR",
                ),
                _mapping(
                    1113,
                    "PROMISSORY_AND_BOND_TOTAL",
                    [_label(35, 58, "Kỳ phiếu, trái phiếu")],
                    {
                        "CURRENT": [_line(35, 59, "10.005.144")],
                        "COMPARATIVE": [_line(35, 60, "9.505.106")],
                    },
                    "COMBINED_SOURCE_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1114,
                    "PROMISSORY_AND_BOND_SHORT",
                    [
                        _label(35, 58, "Kỳ phiếu, trái phiếu"),
                        _label(35, 61, "Ngắn hạn bằng VND"),
                        _label(35, 64, "Ngắn hạn bằng ngoại tệ"),
                    ],
                    {
                        "CURRENT": [_line(35, 62, "47"), _line(35, 65, "35")],
                        "COMPARATIVE": [_line(35, 63, "47"), _line(35, 66, "35")],
                    },
                    "COMBINED_PARENT_PLUS_CURRENCY_TENOR",
                ),
                _mapping(
                    1115,
                    "PROMISSORY_AND_BOND_MEDIUM",
                    [
                        _label(35, 58, "Kỳ phiếu, trái phiếu"),
                        _label(35, 67, "Trung hạn bằng VND"),
                        _label(35, 71, "Trung hạn bằng ngoại tệ"),
                    ],
                    {
                        "CURRENT": [_line(35, 68, "4.000.000"), _line(35, 72, "15")],
                        "COMPARATIVE": [_line(35, 69, "4.000.000"), _line(35, 73, "14")],
                    },
                    "COMBINED_PARENT_PLUS_CURRENCY_TENOR",
                ),
                _mapping(
                    1116,
                    "PROMISSORY_AND_BOND_LONG",
                    [_label(35, 58, "Kỳ phiếu, trái phiếu"), _label(35, 74, "Dài hạn bằng VND")],
                    {
                        "CURRENT": [_line(35, 75, "6.005.047")],
                        "COMPARATIVE": [_line(35, 76, "5.505.010")],
                    },
                    "COMBINED_PARENT_PLUS_CURRENCY_TENOR",
                ),
            ],
            [
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "CURRENT",
                    [
                        _line(35, 50, "28.313.473"),
                        _line(35, 53, "26.848"),
                        _line(35, 56, "1.000.000"),
                    ],
                    _line(35, 47, "29.340.321"),
                ),
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [_line(35, 51, "17.096.000"), _line(35, 54, "115"), _line(35, 57, "500.000")],
                    _line(35, 48, "17.596.115"),
                ),
                _equation(
                    "COMBINED_TENORS_TO_PARENT",
                    "CURRENT",
                    [
                        _line(35, 62, "47"),
                        _line(35, 65, "35"),
                        _line(35, 68, "4.000.000"),
                        _line(35, 72, "15"),
                        _line(35, 75, "6.005.047"),
                    ],
                    _line(35, 59, "10.005.144"),
                ),
                _equation(
                    "COMBINED_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [
                        _line(35, 63, "47"),
                        _line(35, 66, "35"),
                        _line(35, 69, "4.000.000"),
                        _line(35, 73, "14"),
                        _line(35, 76, "5.505.010"),
                    ],
                    _line(35, 60, "9.505.106"),
                ),
                _equation(
                    "INSTRUMENTS_TO_TOTAL",
                    "CURRENT",
                    [_line(35, 47, "29.340.321"), _line(35, 59, "10.005.144")],
                    _line(35, 77, "39.345.465"),
                ),
                _equation(
                    "INSTRUMENTS_TO_TOTAL",
                    "COMPARATIVE",
                    [_line(35, 48, "17.596.115"), _line(35, 60, "9.505.106")],
                    _line(35, 78, "27.101.221"),
                ),
            ],
            presentation="VERTICAL_COMBINED_PROMISSORY_AND_BOND_PARENT_WITH_CURRENCY_TENORS",
        ),
        _doc(
            "CTG",
            42,
            47,
            "10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
            [],
            [_label(42, 48, "Đơn vị tính: triệu đồng")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(42, 47, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                    {"CURRENT": [_line(42, 83, "142.990.024")]},
                    "HORIZONTAL_TABLE_GRAND_TOTAL",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(42, 53, "Chứng chỉ tiền gửi")],
                    {"CURRENT": [_line(42, 82, "87.268.585")]},
                    "HORIZONTAL_INSTRUMENT_COLUMN_TOTAL",
                ),
                _mapping(
                    1102,
                    "CD_SHORT",
                    [_label(42, 53, "Chứng chỉ tiền gửi"), _label(42, 56, "Dưới 12 tháng")],
                    {"CURRENT": [_line(42, 59, "82.507.608")]},
                    "HORIZONTAL_COLUMN_AND_TENOR_ROW_INTERSECTION",
                ),
                _mapping(
                    1103,
                    "CD_MEDIUM",
                    [_label(42, 53, "Chứng chỉ tiền gửi"), _label(42, 63, "Từ 12 tháng đến 5 năm")],
                    {"CURRENT": [_line(42, 66, "4.760.977")]},
                    "HORIZONTAL_COLUMN_AND_TENOR_ROW_INTERSECTION",
                ),
                _mapping(
                    1104,
                    "CD_LONG",
                    [_label(42, 53, "Chứng chỉ tiền gửi"), _label(42, 70, "Trên 5 năm")],
                    {"CURRENT": [ctg_cd_long]},
                    "HORIZONTAL_VISIBLE_DASH_INTERSECTION",
                ),
                _mapping(
                    1105,
                    "PROMISSORY_NOTE",
                    [_label(42, 51, "Kỳ phiếu")],
                    {"CURRENT": [_line(42, 79, "143")]},
                    "HORIZONTAL_INSTRUMENT_COLUMN_TOTAL",
                ),
                _mapping(
                    1106,
                    "PROMISSORY_SHORT",
                    [_label(42, 51, "Kỳ phiếu"), _label(42, 56, "Dưới 12 tháng")],
                    {"CURRENT": [_line(42, 58, "143")]},
                    "HORIZONTAL_COLUMN_AND_TENOR_ROW_INTERSECTION",
                ),
                _mapping(
                    1107,
                    "PROMISSORY_MEDIUM",
                    [_label(42, 51, "Kỳ phiếu"), _label(42, 63, "Từ 12 tháng đến 5 năm")],
                    {"CURRENT": [ctg_ky_medium]},
                    "HORIZONTAL_VISIBLE_DASH_INTERSECTION",
                ),
                _mapping(
                    1108,
                    "PROMISSORY_LONG",
                    [_label(42, 51, "Kỳ phiếu"), _label(42, 70, "Trên 5 năm")],
                    {"CURRENT": [ctg_ky_long]},
                    "HORIZONTAL_VISIBLE_DASH_INTERSECTION",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(42, 49, "Trái phiếu vô danh"), _label(42, 52, "Trái phiếu hữu danh")],
                    {"CURRENT": [_line(42, 80, "166"), _line(42, 81, "55.721.130")]},
                    "SUM_OF_TWO_BOND_COLUMNS",
                ),
                _mapping(
                    1110,
                    "BOND_SHORT",
                    [
                        _label(42, 49, "Trái phiếu vô danh"),
                        _label(42, 52, "Trái phiếu hữu danh"),
                        _label(42, 56, "Dưới 12 tháng"),
                    ],
                    {"CURRENT": [ctg_bond_short]},
                    "HORIZONTAL_TWO_VISIBLE_DASH_INTERSECTIONS",
                ),
                _mapping(
                    1111,
                    "BOND_MEDIUM",
                    [_label(42, 49, "Trái phiếu vô danh"), _label(42, 63, "Từ 12 tháng đến 5 năm")],
                    {"CURRENT": [_line(42, 80, "166")]},
                    "HORIZONTAL_COLUMN_AND_TENOR_ROW_INTERSECTION",
                ),
                _mapping(
                    1112,
                    "BOND_LONG",
                    [_label(42, 52, "Trái phiếu hữu danh"), _label(42, 70, "Trên 5 năm")],
                    {"CURRENT": [_line(42, 81, "55.721.130")]},
                    "FACE_VALUE_PLUS_VISIBLE_PREMIUM",
                ),
                _mapping(
                    1113,
                    "PROMISSORY_AND_BOND_TOTAL",
                    [
                        _label(42, 51, "Kỳ phiếu"),
                        _label(42, 49, "Trái phiếu vô danh"),
                        _label(42, 52, "Trái phiếu hữu danh"),
                    ],
                    {
                        "CURRENT": [
                            _line(42, 79, "143"),
                            _line(42, 80, "166"),
                            _line(42, 81, "55.721.130"),
                        ]
                    },
                    "SUM_OF_PROMISSORY_AND_BOND_COLUMNS",
                ),
                _mapping(
                    1114,
                    "PROMISSORY_AND_BOND_SHORT",
                    [_label(42, 56, "Dưới 12 tháng")],
                    {"CURRENT": [_line(42, 58, "143"), ctg_bond_short]},
                    "TENOR_ROW_SUM_ACROSS_PROMISSORY_AND_BOND_COLUMNS",
                ),
                _mapping(
                    1115,
                    "PROMISSORY_AND_BOND_MEDIUM",
                    [_label(42, 63, "Từ 12 tháng đến 5 năm")],
                    {"CURRENT": [ctg_ky_medium, _line(42, 80, "166")]},
                    "TENOR_ROW_SUM_ACROSS_PROMISSORY_AND_BOND_COLUMNS",
                ),
                _mapping(
                    1116,
                    "PROMISSORY_AND_BOND_LONG",
                    [_label(42, 70, "Trên 5 năm")],
                    {"CURRENT": [ctg_ky_long, _line(42, 81, "55.721.130")]},
                    "TENOR_ROW_SUM_ACROSS_PROMISSORY_AND_BOND_COLUMNS",
                ),
            ],
            [
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "CURRENT",
                    [_line(42, 59, "82.507.608"), _line(42, 66, "4.760.977"), ctg_cd_long],
                    _line(42, 82, "87.268.585"),
                ),
                _equation(
                    "PROMISSORY_TENORS_TO_PARENT",
                    "CURRENT",
                    [_line(42, 58, "143"), ctg_ky_medium, ctg_ky_long],
                    _line(42, 79, "143"),
                ),
                _equation(
                    "INSTRUMENT_COLUMNS_TO_TOTAL",
                    "CURRENT",
                    [
                        _line(42, 79, "143"),
                        _line(42, 80, "166"),
                        _line(42, 81, "55.721.130"),
                        _line(42, 82, "87.268.585"),
                    ],
                    _line(42, 83, "142.990.024"),
                ),
            ],
            presentation="HORIZONTAL_TENOR_ROWS_BY_INSTRUMENT_COLUMNS",
        ),
        _doc(
            "BID",
            25,
            78,
            "10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
            [_label(25, 79, "30/06/2026"), _label(25, 80, "31/12/2025")],
            [],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(25, 78, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                    {
                        "CURRENT": [_line(25, 114, "301.731.655")],
                        "COMPARATIVE": [_line(25, 115, "225.407.774")],
                    },
                    "PRINTED_TOTAL_AFTER_INSTRUMENTS",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(25, 81, "Chứng chỉ tiền gửi")],
                    {
                        "CURRENT": [_line(25, 82, "223.543.332")],
                        "COMPARATIVE": [_line(25, 83, "153.360.747")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1102,
                    "CD_SHORT",
                    [_label(25, 81, "Chứng chỉ tiền gửi"), _label(25, 84, "Dưới 12 tháng")],
                    {
                        "CURRENT": [_line(25, 85, "156.756.150")],
                        "COMPARATIVE": [_line(25, 86, "109.732.844")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1103,
                    "CD_MEDIUM",
                    [
                        _label(25, 81, "Chứng chỉ tiền gửi"),
                        _label(25, 87, "Từ 12 tháng đến dưới 5 năm"),
                    ],
                    {
                        "CURRENT": [_line(25, 88, "66.767.186")],
                        "COMPARATIVE": [_line(25, 89, "43.607.907")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1104,
                    "CD_LONG",
                    [_label(25, 81, "Chứng chỉ tiền gửi"), _label(25, 90, "Từ 5 năm trở lên")],
                    {
                        "CURRENT": [_line(25, 91, "19.996")],
                        "COMPARATIVE": [_line(25, 92, "19.996")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1105,
                    "PROMISSORY_NOTE",
                    [_label(25, 93, "Kỳ phiếu")],
                    {"CURRENT": [_line(25, 94, "519")], "COMPARATIVE": [_line(25, 95, "519")]},
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1106,
                    "PROMISSORY_SHORT",
                    [_label(25, 93, "Kỳ phiếu"), _label(25, 96, "Dưới 12 tháng")],
                    {"CURRENT": [_line(25, 97, "312")], "COMPARATIVE": [_line(25, 98, "312")]},
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1107,
                    "PROMISSORY_MEDIUM",
                    [_label(25, 93, "Kỳ phiếu"), _label(25, 99, "Từ 12 tháng đến dưới 5 năm")],
                    {"CURRENT": [_line(25, 100, "207")], "COMPARATIVE": [_line(25, 101, "207")]},
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(25, 102, "Trái phiếu"), _label(25, 111, "Trái phiếu tăng vốn BIDV")],
                    {
                        "CURRENT": [_line(25, 103, "14.160.381"), _line(25, 112, "64.027.423")],
                        "COMPARATIVE": [_line(25, 104, "14.160.381"), _line(25, 113, "57.886.127")],
                    },
                    "SUM_OF_STANDARD_AND_CAPITAL_INCREASE_BONDS",
                ),
                _mapping(
                    1111,
                    "STANDARD_BOND_MEDIUM",
                    [_label(25, 102, "Trái phiếu"), _label(25, 105, "Từ 12 tháng đến dưới 5 năm")],
                    {
                        "CURRENT": [_line(25, 106, "8.660.061")],
                        "COMPARATIVE": [_line(25, 107, "8.660.061")],
                    },
                    "STANDARD_BOND_SUBPOPULATION_TENOR",
                ),
                _mapping(
                    1112,
                    "STANDARD_BOND_LONG",
                    [_label(25, 102, "Trái phiếu"), _label(25, 108, "Từ 5 năm trở lên")],
                    {
                        "CURRENT": [_line(25, 109, "5.500.320")],
                        "COMPARATIVE": [_line(25, 110, "5.500.320")],
                    },
                    "STANDARD_BOND_SUBPOPULATION_TENOR",
                ),
            ],
            [
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "CURRENT",
                    [
                        _line(25, 85, "156.756.150"),
                        _line(25, 88, "66.767.186"),
                        _line(25, 91, "19.996"),
                    ],
                    _line(25, 82, "223.543.332"),
                ),
                _equation(
                    "CD_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [
                        _line(25, 86, "109.732.844"),
                        _line(25, 89, "43.607.907"),
                        _line(25, 92, "19.996"),
                    ],
                    _line(25, 83, "153.360.747"),
                ),
                _equation(
                    "PROMISSORY_TENORS_TO_PARENT",
                    "CURRENT",
                    [_line(25, 97, "312"), _line(25, 100, "207")],
                    _line(25, 94, "519"),
                ),
                _equation(
                    "PROMISSORY_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [_line(25, 98, "312"), _line(25, 101, "207")],
                    _line(25, 95, "519"),
                ),
                _equation(
                    "STANDARD_BOND_TENORS_TO_PARENT",
                    "CURRENT",
                    [_line(25, 106, "8.660.061"), _line(25, 109, "5.500.320")],
                    _line(25, 103, "14.160.381"),
                ),
                _equation(
                    "STANDARD_BOND_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [_line(25, 107, "8.660.061"), _line(25, 110, "5.500.320")],
                    _line(25, 104, "14.160.381"),
                ),
                _equation(
                    "INSTRUMENTS_TO_TOTAL",
                    "CURRENT",
                    [
                        _line(25, 82, "223.543.332"),
                        _line(25, 94, "519"),
                        _line(25, 103, "14.160.381"),
                        _line(25, 112, "64.027.423"),
                    ],
                    _line(25, 114, "301.731.655"),
                ),
                _equation(
                    "INSTRUMENTS_TO_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(25, 83, "153.360.747"),
                        _line(25, 95, "519"),
                        _line(25, 104, "14.160.381"),
                        _line(25, 113, "57.886.127"),
                    ],
                    _line(25, 115, "225.407.774"),
                ),
            ],
            [
                _unmapped(
                    "BID-CAPITAL-INCREASE-BOND",
                    [_label(25, 111, "Trái phiếu tăng vốn BIDV")],
                    {
                        "CURRENT": [_line(25, 112, "64.027.423")],
                        "COMPARATIVE": [_line(25, 113, "57.886.127")],
                    },
                    "INCLUDED_IN_BOND_PARENT_BUT_NO_STANDALONE_SCHEMA_LEAF_OR_VISIBLE_TENOR_BREAKDOWN",
                )
            ],
            unit_authority="DOCUMENT_LEVEL_MILLION_VND_INHERITED",
        ),
        _doc(
            "VIB",
            43,
            5,
            "PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
            [_label(43, 7, "30/06/2026"), _label(43, 8, "31/12/2025")],
            [_label(43, 9, "triệu đồng"), _label(43, 10, "triệu đồng")],
            [
                _mapping(
                    1100,
                    "FAMILY_TOTAL",
                    [_label(43, 5, "PHÁT HÀNH GIẤY TỜ CÓ GIÁ")],
                    {
                        "CURRENT": [_line(43, 26, "37.970.700")],
                        "COMPARATIVE": [_line(43, 27, "35.070.700")],
                    },
                    "PRINTED_TOTAL_AFTER_INSTRUMENTS",
                ),
                _mapping(
                    1101,
                    "CERTIFICATE_OF_DEPOSIT",
                    [_label(43, 20, "Chứng chỉ tiền gửi")],
                    {
                        "CURRENT": [_line(43, 21, "14.770.700")],
                        "COMPARATIVE": [_line(43, 22, "11.870.700")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1103,
                    "CD_MEDIUM",
                    [
                        _label(43, 20, "Chứng chỉ tiền gửi"),
                        _label(43, 23, "Từ 12 tháng đến dưới 5 năm"),
                    ],
                    {
                        "CURRENT": [_line(43, 24, "14.770.700")],
                        "COMPARATIVE": [_line(43, 25, "11.870.700")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1109,
                    "BOND",
                    [_label(43, 11, "Trái phiếu")],
                    {
                        "CURRENT": [_line(43, 12, "23.200.000")],
                        "COMPARATIVE": [_line(43, 13, "23.200.000")],
                    },
                    "OWNER_INSTRUMENT_PARENT",
                ),
                _mapping(
                    1111,
                    "BOND_MEDIUM",
                    [_label(43, 11, "Trái phiếu"), _label(43, 14, "Từ 12 tháng đến dưới 5 năm")],
                    {
                        "CURRENT": [_line(43, 15, "17.200.000")],
                        "COMPARATIVE": [_line(43, 16, "17.200.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
                _mapping(
                    1112,
                    "BOND_LONG",
                    [_label(43, 11, "Trái phiếu"), _label(43, 17, "Từ 5 năm trở lên")],
                    {
                        "CURRENT": [_line(43, 18, "6.000.000")],
                        "COMPARATIVE": [_line(43, 19, "6.000.000")],
                    },
                    "INSTRUMENT_CONTEXT_PLUS_TENOR",
                ),
            ],
            [
                _equation(
                    "CD_TENOR_TO_PARENT",
                    "CURRENT",
                    [_line(43, 24, "14.770.700")],
                    _line(43, 21, "14.770.700"),
                ),
                _equation(
                    "CD_TENOR_TO_PARENT",
                    "COMPARATIVE",
                    [_line(43, 25, "11.870.700")],
                    _line(43, 22, "11.870.700"),
                ),
                _equation(
                    "BOND_TENORS_TO_PARENT",
                    "CURRENT",
                    [_line(43, 15, "17.200.000"), _line(43, 18, "6.000.000")],
                    _line(43, 12, "23.200.000"),
                ),
                _equation(
                    "BOND_TENORS_TO_PARENT",
                    "COMPARATIVE",
                    [_line(43, 16, "17.200.000"), _line(43, 19, "6.000.000")],
                    _line(43, 13, "23.200.000"),
                ),
                _equation(
                    "INSTRUMENTS_TO_TOTAL",
                    "CURRENT",
                    [_line(43, 12, "23.200.000"), _line(43, 21, "14.770.700")],
                    _line(43, 26, "37.970.700"),
                ),
                _equation(
                    "INSTRUMENTS_TO_TOTAL",
                    "COMPARATIVE",
                    [_line(43, 13, "23.200.000"), _line(43, 22, "11.870.700")],
                    _line(43, 27, "35.070.700"),
                ),
            ],
        ),
    ]
    if [item["bank_code"] for item in documents] != list(EXPECTED_DOCUMENT_ORDER):
        raise _error("review bank order drifted")
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0076"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0076:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex issued-valuable-papers pixel review differs from fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    try:
        return foundation._document(items, code, label)
    except Exception as exc:
        raise _error(f"{label} document axis drifted: {exc}") from exc


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    try:
        return foundation._page(document, page_sequence, label)
    except Exception as exc:
        raise _error(f"{label} page axis drifted: {exc}") from exc


def _semantic_evidence(
    axis_page: Mapping[str, Any], semantic_page: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        return foundation._semantic_evidence(axis_page, semantic_page, item)
    except Exception as exc:
        raise _error(f"semantic/pixel evidence drifted: {exc}") from exc


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
    payload = foundation.support._artifact_bytes(crop_page.get("render_binding"), "page render")
    image = Image.open(io.BytesIO(payload)).convert("RGB")
    left, top, right, bottom = ref["bbox"]
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise _error("authenticated pixel dash bbox is out of bounds")
    digest = hashlib.sha256(image.crop((left, top, right, bottom)).tobytes()).hexdigest()
    if digest != ref["pixel_rgb_sha256"]:
        raise _error("authenticated pixel dash crop drifted")
    return {
        "normalized_value": 0,
        "page_sequence": ref["page_sequence"],
        "pixel_bbox": list(ref["bbox"]),
        "pixel_rgb_sha256": digest,
        "pixel_transcription": "-",
        "render_ref": canonical_clone_v1(crop_page["render_binding"]),
        "source_line_index": None,
        "source_numeric_challenger": None,
        "source_numeric_challenger_status": "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE",
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "authenticated_pixel_dash_zero_count": len(
            {
                (
                    component["render_ref"]["sha256"],
                    tuple(component["pixel_bbox"]),
                    component["pixel_rgb_sha256"],
                )
                for trial in trials
                for mapping in trial["verified_mappings"]
                for value in mapping["values"]
                for component in value["components"]
                if component["source_numeric_challenger_status"]
                == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            }
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            t["whole_document_uniqueness"]["complete_region_count"] == 1 for t in trials
        ),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["unmapped_source_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_document_count": sum(t["status"].startswith("VERIFIED_BY_CODEX") for t in trials),
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("issued-valuable-papers result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ISSUED_VALUABLE_PAPERS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("issued-valuable-papers result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or not str(trial.get("status", "")).startswith("VERIFIED_BY_CODEX")
            or any(
                row.get("status") != "VERIFIED_BY_CODEX"
                for row in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED" for row in trial.get("unmapped_source_rows", [])
            )
        ):
            raise _error("issued-valuable-papers trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0076:result:" + canonical_json_sha256_v1(material):
        raise _error("issued-valuable-papers result identity drifted")
    return canonical_clone_v1(value)


def build_issued_valuable_papers_8bank_codex_verified_mapping_v1(
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
        or structure_scan.get("metrics", {}).get("complete_region_count") != 8
    ):
        raise _error("fixed semantic axis or structure scan identity drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or len(matcher["regions"]) != 1
            or matcher["regions"][0]["owner"]["page_sequence"] != reviewed["owner"]["page_sequence"]
            or matcher["regions"][0]["owner"]["source_line_index"]
            != reviewed["owner"]["line_index"]
        ):
            raise _error(f"{code} reviewed region is not the unique whole-PDF graph")
        page = reviewed["owner"]["page_sequence"]
        axis_page = _page(axis_document, page, "accounting axis")
        semantic_page = _page(semantic_document, page, "semantic index")
        crop_page = _page(crop_document, page, "crop manifest")
        source_texts = foundation.support._source_line_axis(crop_page)

        def evidence(
            item: Mapping[str, Any],
            *,
            page: int = page,
            axis_page: Mapping[str, Any] = axis_page,
            semantic_page: Mapping[str, Any] = semantic_page,
        ) -> dict[str, Any]:
            if item["page_sequence"] != page:
                raise _error("review evidence escaped unique one-page region")
            return {"page_sequence": page, **_semantic_evidence(axis_page, semantic_page, item)}

        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            axis_page: Mapping[str, Any] = axis_page,
            semantic_page: Mapping[str, Any] = semantic_page,
            crop_page: Mapping[str, Any] = crop_page,
            source_texts: Sequence[str] = source_texts,
            page: int = page,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                if ref["kind"] == "AUTHENTICATED_LINE":
                    item = foundation.support._source_value(
                        axis_page,
                        semantic_page,
                        crop_page,
                        source_texts,
                        {
                            "line_index": ref["line_index"],
                            "pixel_transcription": ref["pixel_transcription"],
                        },
                    )
                    value_cache[key] = {**item, "page_sequence": page}
                elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
                    value_cache[key] = _pixel_dash_value(crop_page, ref)
                else:
                    raise _error("reviewed numeric evidence kind drifted")
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        for mapping in reviewed["mappings"]:
            values = []
            for period_role, refs in mapping["values"].items():
                components = [verified(ref) for ref in refs]
                values.append(
                    {
                        "aggregation": "DIRECT_VISIBLE_VALUE"
                        if len(components) == 1
                        else "SUM_OF_VISIBLE_SOURCE_ROWS",
                        "components": components,
                        "normalized_value": sum(
                            component["normalized_value"] for component in components
                        ),
                        "period_role": period_role,
                    }
                )
            verified_mappings.append(
                {
                    "label_evidence": [evidence(item) for item in mapping["labels"]],
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "status": "VERIFIED_BY_CODEX",
                    "topology": mapping["topology"],
                    "values": values,
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            terms = [verified(item) for item in equation["terms"]]
            total = verified(equation["total"])
            computed = sum(
                item["normalized_value"] * ref["multiplier"]
                for item, ref in zip(terms, equation["terms"], strict=True)
            )
            if computed != total["normalized_value"]:
                raise _error(
                    f"{code} issued-valuable-papers accounting equation {equation['name']} does not close"
                )
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "period_role": equation["period_role"],
                    "status": "VERIFIED_EXACT",
                    "term_source_line_indices": [item["source_line_index"] for item in terms],
                    "visible_total": total["normalized_value"],
                    "visible_total_source_line_index": total["source_line_index"],
                }
            )
        unresolved = []
        for row in reviewed["unmapped_source_rows"]:
            unresolved.append(
                {
                    "item_id": row["item_id"],
                    "label_evidence": [evidence(item) for item in row["labels"]],
                    "reason": row["reason"],
                    "status": "UNRESOLVED",
                    "values": [
                        {
                            "components": [verified(ref) for ref in refs],
                            "normalized_value": sum(
                                verified(ref)["normalized_value"] for ref in refs
                            ),
                            "period_role": role,
                        }
                        for role, refs in row["values"].items()
                    ],
                }
            )
        period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner_evidence": evidence(reviewed["owner"]),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": [evidence(item) for item in reviewed["period_axis"]],
                "presentation": reviewed["presentation"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS_AND_Q1_PERIOD_CAVEAT"
                    if unresolved and period_status.endswith("NOT_Q2")
                    else "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS"
                    if unresolved
                    else "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if period_status.endswith("NOT_Q2")
                    else "VERIFIED_BY_CODEX"
                ),
                "structure_graph_id": matcher["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "unit_evidence": [evidence(item) for item in reviewed["unit_evidence"]],
                "unmapped_source_rows": unresolved,
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    mapped_ids = sorted(
        {
            row["schema_binding"]["report_norm_id"]
            for trial in trials
            for row in trial["verified_mappings"]
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
            "family_display_order_range": [606, 630],
            "family_root": _schema_binding(schema_by_id.get(1100), 1100),
            "mapped_report_norm_ids": mapped_ids,
        },
        "state": "ISSUED_VALUABLE_PAPERS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0076:result:" + canonical_json_sha256_v1(material)}
    )


def validate_issued_valuable_papers_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    review: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    structure_scan = scanner.build_issued_valuable_papers_full_document_scan_v1(semantic_index)
    rebuilt = build_issued_valuable_papers_8bank_codex_verified_mapping_v1(
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
        raise _error("issued-valuable-papers verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    try:
        return foundation._stable_json(path, expected_sha256)
    except Exception as exc:
        raise _error(f"fixed JSON drifted: {path}: {exc}") from exc


def build_live_issued_valuable_papers_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    structure_scan = scanner.build_issued_valuable_papers_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_issued_valuable_papers_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return validate_issued_valuable_papers_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_issued_valuable_papers_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_issued_valuable_papers_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def _write(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.write_review and args.validate is not None:
        parser.error("--write-review and --validate are mutually exclusive")
    if args.write_review:
        _write(args.output or REVIEW_PATH, _review_blueprint())
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        result = validate_live_issued_valuable_papers_8bank_codex_verified_mapping_v1(value)
        sys.stdout.write(result["result_id"] + "\n")
        return
    result = build_live_issued_valuable_papers_8bank_codex_verified_mapping_v1()
    _write(args.output or RESULT_PATH, result)
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    main()
