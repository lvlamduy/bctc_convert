"""Verify Government/SBV-liability rows across eight reports without bank routing."""

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


support = _load_module(
    "trading_securities_support_for_government_nhnn_liabilities",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "government_nhnn_liabilities_scan_for_verified_mapping",
    "scan_government_nhnn_liabilities_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
_RESULT_STATE = "GOVERNMENT_NHNN_LIABILITIES_8BANK_CODEX_VERIFICATION_COMPLETE"
_RESULT_ID_PREFIX = "e0074:result:"
_REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0074:pixel-review:"
_REVIEW_RUN_ID = "E-0074"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_GOVERNMENT_"
    "NHNN_LIABILITY_VARIANT_GRAPH_VISIBLE_PDF_PIXEL_SOURCE_NUMERIC_CHALLENGER_"
    "PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_UNMAPPED_ROWS_RETAINED_NO_"
    "EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0074-government-nhnn-liabilities-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0074-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "gnlfdsv1:scan:fb7f69c0c2cbb81c1f130a3ce37cf248df0d830884abc0dc7009a40efc290ac2"

_REVIEW_CHECKS = (
    "COMPLETE_PDF_UNIQUE_REGION",
    "OWNER_CHILD_SIBLING_AND_OPTIONAL_BRANCH_TOPOLOGY",
    "AGGREGATE_LOAN_TREASURY_CURRENCY_TENOR_REPO_VARIANTS",
    "CURRENT_AND_COMPARATIVE_SNAPSHOT_AXES",
    "LOCAL_OR_DOCUMENT_INHERITED_MILLION_VND_UNIT",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGNS_AND_DASHES",
    "SOURCE_NUMERIC_CHALLENGER_OR_AUTHENTICATED_PIXEL_DASH",
    "OPTIONAL_CHILDREN_NOT_REQUIRED_FOR_REGION_LOCATION",
    "PARENT_CHILD_AND_FAMILY_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
    "UNMAPPED_SOURCE_ROWS_RETAINED_WITHOUT_FORCED_EQUIVALENCE",
)
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
    "mapping_authority_bounded_to_reviewed_government_nhnn_liability_rows": True,
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
    1024: ("Các khoản nợ Chính phủ và Ngân hàng Nhà nước", 560),
    1025: ("Vay theo hồ sơ tín dụng", 1024),
    1026: ("Vay chiết khấu, tái chiết khấu giấy tờ có giá", 1024),
    1027: ("Vay cầm cố các giấy tờ có giá", 1024),
    1033: ("Vay khác", 1024),
    1035: ("Tiền gửi thanh toán của Kho bạc NN", 1024),
    1036: ("Trong đó: + Bằng tiền VNĐ", 1024),
    1037: ("+ Bằng ngoại tệ", 1024),
    1039: ("Các khoản nợ khác", 1024),
}


class GovernmentNHNNLiabilities8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel, numeric, accounting or schema evidence drifted."""


def _error(message: str) -> GovernmentNHNNLiabilities8BankCodexVerifiedMappingV1Error:
    return GovernmentNHNNLiabilities8BankCodexVerifiedMappingV1Error(message)


def _line(page: int, line: int, text: str, multiplier: int = 1) -> dict[str, Any]:
    return {
        "kind": "AUTHENTICATED_LINE",
        "line_index": line,
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_transcription": text,
    }


def _dash(
    page: int, bbox: Sequence[int], pixel_rgb_sha256: str, multiplier: int = 1
) -> dict[str, Any]:
    return {
        "bbox": list(bbox),
        "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
        "multiplier": multiplier,
        "page_sequence": page,
        "pixel_rgb_sha256": pixel_rgb_sha256,
        "pixel_transcription": "-",
    }


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _mapping(
    report_norm_id: int,
    role: str,
    labels: Sequence[dict[str, Any]],
    current: Sequence[dict[str, Any]],
    comparative: Sequence[dict[str, Any]],
    topology: str = "OWNER_DESCENDANT",
) -> dict[str, Any]:
    return {
        "labels": list(labels),
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": {"COMPARATIVE": list(comparative), "CURRENT": list(current)},
    }


def _direct(
    report_norm_id: int,
    role: str,
    page: int,
    label_line: int,
    label_text: str,
    current: dict[str, Any],
    comparative: dict[str, Any],
    topology: str = "OWNER_DESCENDANT",
) -> dict[str, Any]:
    return _mapping(
        report_norm_id,
        role,
        [_label(page, label_line, label_text)],
        [current],
        [comparative],
        topology,
    )


def _equation(
    name: str, period_role: str, terms: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"name": name, "period_role": period_role, "terms": list(terms), "total": total}


def _unmapped(
    item_id: str,
    page: int,
    line: int,
    text: str,
    current: dict[str, Any],
    comparative: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "label": _label(page, line, text),
        "reason": reason,
        "status": "UNRESOLVED",
        "values": {"COMPARATIVE": [comparative], "CURRENT": [current]},
    }


def _doc(
    code: str,
    page: int,
    owner_line: int,
    owner_text: str,
    period_refs: Sequence[dict[str, Any]],
    unit_refs: Sequence[dict[str, Any]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    unmapped: Sequence[dict[str, Any]] = (),
    *,
    source_period: str = "2026-06-30",
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
        "period_axis": list(period_refs),
        "source_period": source_period,
        "unit_authority": unit_authority,
        "unit_evidence": list(unit_refs),
        "unmapped_source_rows": list(unmapped),
    }


def _review_documents() -> list[dict[str, Any]]:
    hdb_dash = _dash(
        30,
        [1170, 1230, 1210, 1260],
        "3cbe12882b9e76d2cdfa06efed8f597353443576b9a9dfff252f35930d91c25a",
    )
    vib_dash = _dash(
        40,
        [1410, 620, 1460, 650],
        "cd40b408ec34fb3ad2104ed1c49cfce29011af2a51413560f833d2f7e3742573",
    )
    documents = [
        _doc(
            "ACB",
            20,
            4,
            "8. CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC:",
            [_label(20, 5, "30.6.2026"), _label(20, 6, "31.12.2025")],
            [_label(20, 7, "Triệu đồng"), _label(20, 8, "Triệu đồng")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    20,
                    4,
                    "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC",
                    _line(20, 19, "21.018.876"),
                    _line(20, 20, "32.976.139"),
                    "UNLABELED_TOTAL_AFTER_LAST_CHILD",
                ),
                _direct(
                    1035,
                    "TREASURY_DEPOSIT",
                    20,
                    12,
                    "Tiền gửi của Kho bạc Nhà nước",
                    _line(20, 13, "30.777"),
                    _line(20, 14, "18.758"),
                ),
                _direct(
                    1039,
                    "OTHER_GOVERNMENT_LIABILITY_REPO",
                    20,
                    15,
                    "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                    _line(20, 17, "5.611.968"),
                    _line(20, 18, "1.805.161"),
                ),
            ],
            [
                _equation(
                    "LOAN_TREASURY_REPO_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(20, 10, "15.376.131"),
                        _line(20, 13, "30.777"),
                        _line(20, 17, "5.611.968"),
                    ],
                    _line(20, 19, "21.018.876"),
                ),
                _equation(
                    "LOAN_TREASURY_REPO_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(20, 11, "31.152.220"),
                        _line(20, 14, "18.758"),
                        _line(20, 18, "1.805.161"),
                    ],
                    _line(20, 20, "32.976.139"),
                ),
            ],
            [
                _unmapped(
                    "GN-001",
                    20,
                    9,
                    "Vay Ngân hàng Nhà nước",
                    _line(20, 10, "15.376.131"),
                    _line(20, 11, "31.152.220"),
                    "The source does not identify which exact facility in schema 1025-1033 produced this central-bank loan balance.",
                ),
            ],
        ),
        _doc(
            "MBB",
            42,
            51,
            "Các khoản nợ chính phủ và NHNN",
            [_label(42, 52, "30/06/2026"), _label(42, 53, "31/12/2025")],
            [_label(42, 54, "Triệu đồng"), _label(42, 55, "Triệu đồng")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    42,
                    56,
                    "Các khoản nợ chính phủ và NHNN",
                    _line(42, 59, "22.574.102"),
                    _line(42, 60, "47.474.800"),
                    "AGGREGATE_ONLY_REPEATED_ROW_THEN_UNLABELED_TOTAL",
                ),
            ],
            [
                _equation(
                    "REPEATED_FAMILY_ROW_EQUALS_TOTAL",
                    "CURRENT",
                    [_line(42, 57, "22.574.102")],
                    _line(42, 59, "22.574.102"),
                ),
                _equation(
                    "REPEATED_FAMILY_ROW_EQUALS_TOTAL",
                    "COMPARATIVE",
                    [_line(42, 58, "47.474.800")],
                    _line(42, 60, "47.474.800"),
                ),
            ],
        ),
        _doc(
            "VPB",
            53,
            39,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                _label(53, 40, "Ngày 31 tháng 3"),
                _label(53, 42, "năm 2026"),
                _label(53, 41, "Ngày 31 tháng 12"),
                _label(53, 43, "năm 2025"),
            ],
            [_label(53, 44, "Triệu đồng"), _label(53, 45, "Triệu đồng")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    53,
                    39,
                    "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
                    _line(53, 60, "1.063.456"),
                    _line(53, 61, "15.305"),
                    "UNLABELED_TOTAL_AFTER_LOAN_AND_TREASURY_BRANCHES",
                ),
                _direct(
                    1033,
                    "OTHER_LOAN",
                    53,
                    50,
                    "Vay khác",
                    _line(53, 51, "1.130"),
                    _line(53, 52, "1.752"),
                ),
                _direct(
                    1035,
                    "TREASURY_DEPOSIT",
                    53,
                    57,
                    "Tiền gửi của Kho bạc Nhà nước",
                    _line(53, 58, "1.062.326"),
                    _line(53, 59, "13.553"),
                ),
            ],
            [
                _equation(
                    "OTHER_LOAN_EQUALS_CENTRAL_BANK_LOAN_GROUP",
                    "CURRENT",
                    [_line(53, 51, "1.130")],
                    _line(53, 47, "1.130"),
                ),
                _equation(
                    "OTHER_LOAN_EQUALS_CENTRAL_BANK_LOAN_GROUP",
                    "COMPARATIVE",
                    [_line(53, 52, "1.752")],
                    _line(53, 48, "1.752"),
                ),
                _equation(
                    "TREASURY_CHILD_EQUALS_TREASURY_GROUP",
                    "CURRENT",
                    [_line(53, 58, "1.062.326")],
                    _line(53, 54, "1.062.326"),
                ),
                _equation(
                    "TREASURY_CHILD_EQUALS_TREASURY_GROUP",
                    "COMPARATIVE",
                    [_line(53, 59, "13.553")],
                    _line(53, 55, "13.553"),
                ),
                _equation(
                    "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [_line(53, 47, "1.130"), _line(53, 54, "1.062.326")],
                    _line(53, 60, "1.063.456"),
                ),
                _equation(
                    "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [_line(53, 48, "1.752"), _line(53, 55, "13.553")],
                    _line(53, 61, "15.305"),
                ),
            ],
            source_period="2026-03-31",
        ),
        _doc(
            "HDB",
            30,
            56,
            "Các khoản nợ Chính phủ và NHNN",
            [_label(30, 57, "Số cuối kỳ"), _label(30, 58, "Số đầu kỳ")],
            [_label(30, 59, "Triệu VND"), _label(30, 60, "Triệu VND")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    30,
                    56,
                    "Các khoản nợ Chính phủ và NHNN",
                    _line(30, 71, "5.214"),
                    _line(30, 72, "11.425.972"),
                    "UNLABELED_TOTAL_AFTER_LAST_CHILD",
                ),
                _direct(
                    1026,
                    "DISCOUNT_LOAN",
                    30,
                    63,
                    "Vay chiết khấu các giấy tờ có giá",
                    hdb_dash,
                    _line(30, 64, "11.418.077"),
                ),
                _direct(
                    1035,
                    "TREASURY_DEPOSIT",
                    30,
                    65,
                    "Tiền gửi của Kho bạc Nhà nước",
                    _line(30, 66, "35"),
                    _line(30, 67, "168"),
                ),
                _direct(
                    1039,
                    "OTHER_LIABILITY",
                    30,
                    68,
                    "Các khoản nợ khác",
                    _line(30, 69, "5.179"),
                    _line(30, 70, "7.727"),
                ),
            ],
            [
                _equation(
                    "MAPPED_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [hdb_dash, _line(30, 66, "35"), _line(30, 69, "5.179")],
                    _line(30, 71, "5.214"),
                ),
                _equation(
                    "MAPPED_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [_line(30, 64, "11.418.077"), _line(30, 67, "168"), _line(30, 70, "7.727")],
                    _line(30, 72, "11.425.972"),
                ),
            ],
        ),
        _doc(
            "VCB",
            34,
            8,
            "Các khoản nợ Chính Phủ và Ngân hàng Nhà nước",
            [_label(34, 9, "30/6/2026"), _label(34, 10, "31/12/2025")],
            [_label(34, 11, "Triệu VND"), _label(34, 12, "Triệu VND")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    34,
                    8,
                    "Các khoản nợ Chính Phủ và Ngân hàng Nhà nước",
                    _line(34, 38, "192.563.126"),
                    _line(34, 39, "160.128.325"),
                    "UNLABELED_TOTAL_AFTER_LOAN_AND_TREASURY_BRANCHES",
                ),
                _direct(
                    1025,
                    "CREDIT_FILE_LOAN",
                    34,
                    17,
                    "Vay theo hồ sơ tín dụng",
                    _line(34, 18, "294.777"),
                    _line(34, 19, "355.322"),
                ),
                _direct(
                    1027,
                    "COLLATERAL_LOAN",
                    34,
                    20,
                    "Vay cầm cố giấy tờ có giá",
                    _line(34, 21, "5.927.089"),
                    _line(34, 22, "23.748.932"),
                ),
                _direct(
                    1033,
                    "OTHER_LOAN",
                    34,
                    23,
                    "Vay khác",
                    _line(34, 24, "13.415"),
                    _line(34, 25, "22.905"),
                ),
                _direct(
                    1035,
                    "TREASURY_DEPOSIT",
                    34,
                    26,
                    "Tiền gửi thanh toán của Kho bạc Nhà nước",
                    _line(34, 27, "186.327.845"),
                    _line(34, 28, "136.001.166"),
                ),
                _mapping(
                    1036,
                    "TREASURY_VND",
                    [
                        _label(34, 29, "Tiền gửi không kỳ hạn bằng VND"),
                        _label(34, 35, "Tiền gửi có kỳ hạn bằng VND"),
                    ],
                    [_line(34, 30, "696.132"), _line(34, 36, "184.255.000")],
                    [_line(34, 31, "490.536"), _line(34, 37, "134.625.000")],
                    "SUM_OF_VISIBLE_VND_TENOR_ROWS",
                ),
                _direct(
                    1037,
                    "TREASURY_FOREIGN_CURRENCY",
                    34,
                    32,
                    "Tiền gửi không kỳ hạn bằng ngoại tệ",
                    _line(34, 33, "1.376.713"),
                    _line(34, 34, "885.630"),
                ),
            ],
            [
                _equation(
                    "LOAN_CHILDREN_TO_LOAN_GROUP",
                    "CURRENT",
                    [_line(34, 18, "294.777"), _line(34, 21, "5.927.089"), _line(34, 24, "13.415")],
                    _line(34, 15, "6.235.281"),
                ),
                _equation(
                    "LOAN_CHILDREN_TO_LOAN_GROUP",
                    "COMPARATIVE",
                    [
                        _line(34, 19, "355.322"),
                        _line(34, 22, "23.748.932"),
                        _line(34, 25, "22.905"),
                    ],
                    _line(34, 16, "24.127.159"),
                ),
                _equation(
                    "TREASURY_CURRENCY_ROWS_TO_TREASURY_GROUP",
                    "CURRENT",
                    [
                        _line(34, 30, "696.132"),
                        _line(34, 36, "184.255.000"),
                        _line(34, 33, "1.376.713"),
                    ],
                    _line(34, 27, "186.327.845"),
                ),
                _equation(
                    "TREASURY_CURRENCY_ROWS_TO_TREASURY_GROUP",
                    "COMPARATIVE",
                    [
                        _line(34, 31, "490.536"),
                        _line(34, 37, "134.625.000"),
                        _line(34, 34, "885.630"),
                    ],
                    _line(34, 28, "136.001.166"),
                ),
                _equation(
                    "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [_line(34, 15, "6.235.281"), _line(34, 27, "186.327.845")],
                    _line(34, 38, "192.563.126"),
                ),
                _equation(
                    "LOAN_PLUS_TREASURY_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [_line(34, 16, "24.127.159"), _line(34, 28, "136.001.166")],
                    _line(34, 39, "160.128.325"),
                ),
            ],
        ),
        _doc(
            "CTG",
            41,
            7,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
            [_label(41, 8, "30/06/2026"), _label(41, 9, "31/12/2025")],
            [_label(41, 10, "triệu đồng"), _label(41, 11, "triệu đồng")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    41,
                    7,
                    "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
                    _line(41, 25, "194,570,607"),
                    _line(41, 26, "144,592,357"),
                    "UNLABELED_TOTAL_AFTER_LAST_CHILD",
                ),
                _direct(
                    1035,
                    "TREASURY_DEPOSIT",
                    41,
                    15,
                    "Tiền gửi của KBNN",
                    _line(41, 16, "184,240,000"),
                    _line(41, 17, "134,625,341"),
                ),
                _direct(
                    1036,
                    "TREASURY_VND",
                    41,
                    18,
                    "Tiền gửi bằng đồng Việt Nam",
                    _line(41, 19, "184,240,000"),
                    _line(41, 20, "134,625,341"),
                ),
                _direct(
                    1039,
                    "OTHER_GOVERNMENT_LIABILITY_REPO",
                    41,
                    21,
                    "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                    _line(41, 22, "1,889,919"),
                    _line(41, 23, "2,965,201"),
                ),
            ],
            [
                _equation(
                    "TREASURY_VND_EQUALS_TREASURY_GROUP",
                    "CURRENT",
                    [_line(41, 19, "184,240,000")],
                    _line(41, 16, "184,240,000"),
                ),
                _equation(
                    "TREASURY_VND_EQUALS_TREASURY_GROUP",
                    "COMPARATIVE",
                    [_line(41, 20, "134,625,341")],
                    _line(41, 17, "134,625,341"),
                ),
                _equation(
                    "LOAN_TREASURY_REPO_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(41, 12, "8,440,688"),
                        _line(41, 16, "184,240,000"),
                        _line(41, 22, "1,889,919"),
                    ],
                    _line(41, 25, "194,570,607"),
                ),
                _equation(
                    "LOAN_TREASURY_REPO_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(41, 14, "7,001,815"),
                        _line(41, 17, "134,625,341"),
                        _line(41, 23, "2,965,201"),
                    ],
                    _line(41, 26, "144,592,357"),
                ),
            ],
            [
                _unmapped(
                    "GN-002",
                    41,
                    13,
                    "Vay NHNN",
                    _line(41, 12, "8,440,688"),
                    _line(41, 14, "7,001,815"),
                    "The source does not identify which exact facility in schema 1025-1033 produced this central-bank loan balance.",
                ),
            ],
        ),
        _doc(
            "BID",
            24,
            88,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG",
            [_label(24, 89, "30/06/2026"), _label(24, 90, "31/12/2025")],
            [
                _label(
                    13,
                    49,
                    "các số liệu được làm tròn đến hàng triệu và trình bày theo đơn vị triệu VND",
                )
            ],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    24,
                    88,
                    "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG",
                    _line(24, 103, "236,367,270"),
                    _line(24, 104, "218,825,525"),
                    "UNLABELED_TOTAL_AFTER_LAST_CHILD",
                ),
                _direct(
                    1035,
                    "TREASURY_PAYMENT_DEPOSIT",
                    24,
                    94,
                    "Tiền gửi không kỳ hạn của KBNN",
                    _line(24, 95, "1,688,901"),
                    _line(24, 96, "1,240,317"),
                ),
                _direct(
                    1039,
                    "OTHER_GOVERNMENT_LIABILITY_FINANCE_MINISTRY_DEPOSIT",
                    24,
                    100,
                    "Tiền gửi của Bộ Tài chính",
                    _line(24, 101, "8,763,329"),
                    _line(24, 102, "6,834,201"),
                ),
            ],
            [
                _equation(
                    "ALL_VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [
                        _line(24, 92, "41,660,040"),
                        _line(24, 95, "1,688,901"),
                        _line(24, 98, "184,255,000"),
                        _line(24, 101, "8,763,329"),
                    ],
                    _line(24, 103, "236,367,270"),
                ),
                _equation(
                    "ALL_VISIBLE_CHILDREN_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [
                        _line(24, 93, "76,126,007"),
                        _line(24, 96, "1,240,317"),
                        _line(24, 99, "134,625,000"),
                        _line(24, 102, "6,834,201"),
                    ],
                    _line(24, 104, "218,825,525"),
                ),
            ],
            [
                _unmapped(
                    "GN-003",
                    24,
                    91,
                    "Vay Ngân hàng Trung ương",
                    _line(24, 92, "41,660,040"),
                    _line(24, 93, "76,126,007"),
                    "The source does not identify which exact facility in schema 1025-1033 produced this central-bank loan balance.",
                ),
                _unmapped(
                    "GN-004",
                    24,
                    97,
                    "Tiền gửi có kỳ hạn của KBNN",
                    _line(24, 98, "184,255,000"),
                    _line(24, 99, "134,625,000"),
                    "Schema 1035 is payment Treasury deposits; no existing row independently represents term Treasury deposits.",
                ),
            ],
            unit_authority="DOCUMENT_LEVEL_MILLION_VND_INHERITED_TO_NOTE",
        ),
        _doc(
            "VIB",
            40,
            5,
            "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
            [_label(40, 6, "30/06/2026"), _label(40, 7, "31/12/2025")],
            [_label(40, 8, "triệu đồng"), _label(40, 9, "triệu đồng")],
            [
                _direct(
                    1024,
                    "FAMILY_TOTAL",
                    40,
                    5,
                    "CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NHNN",
                    _line(40, 20, "24.335.557"),
                    _line(40, 21, "10.980.813"),
                    "UNLABELED_TOTAL_AFTER_LAST_CHILD",
                ),
                _direct(
                    1026,
                    "DISCOUNT_REDISCOUNT_LOAN",
                    40,
                    13,
                    "Vay chiết khấu, tái chiết khấu các giấy tờ có giá",
                    _line(40, 14, "8.787.200"),
                    _line(40, 15, "10.980.813"),
                ),
                _direct(
                    1039,
                    "OTHER_GOVERNMENT_LIABILITY_REPO",
                    40,
                    16,
                    "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                    _line(40, 19, "15.548.357"),
                    vib_dash,
                ),
            ],
            [
                _equation(
                    "DISCOUNT_LOAN_EQUALS_CENTRAL_BANK_LOAN_GROUP",
                    "CURRENT",
                    [_line(40, 14, "8.787.200")],
                    _line(40, 11, "8.787.200"),
                ),
                _equation(
                    "DISCOUNT_LOAN_EQUALS_CENTRAL_BANK_LOAN_GROUP",
                    "COMPARATIVE",
                    [_line(40, 15, "10.980.813")],
                    _line(40, 12, "10.980.813"),
                ),
                _equation(
                    "LOAN_PLUS_REPO_TO_FAMILY_TOTAL",
                    "CURRENT",
                    [_line(40, 11, "8.787.200"), _line(40, 19, "15.548.357")],
                    _line(40, 20, "24.335.557"),
                ),
                _equation(
                    "LOAN_PLUS_REPO_TO_FAMILY_TOTAL",
                    "COMPARATIVE",
                    [_line(40, 12, "10.980.813"), vib_dash],
                    _line(40, 21, "10.980.813"),
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
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": _REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": _REVIEW_STATE,
    }
    return {**material, "review_id": _REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex Government/SBV pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in items
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return support._page_by_number(document, page_sequence, label)


def _semantic_evidence(
    axis_page: Mapping[str, Any], semantic_page: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    line_index = item["line_index"]
    axis_line = support._axis_line(axis_page, line_index)
    semantic_line = semantic_page["lines"][line_index]
    if (
        semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis_line["vietocr_text"]
        or type(item["pixel_transcription"]) is not str
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
    if (
        type(ref) is not dict
        or set(ref)
        != {
            "bbox",
            "kind",
            "multiplier",
            "page_sequence",
            "pixel_rgb_sha256",
            "pixel_transcription",
        }
        or ref["kind"] != "AUTHENTICATED_RENDER_PIXEL_DASH"
        or ref["pixel_transcription"] != "-"
        or type(ref["bbox"]) is not list
        or len(ref["bbox"]) != 4
        or any(type(item) is not int for item in ref["bbox"])
    ):
        raise _error("authenticated pixel dash reference drifted")
    payload = support._artifact_bytes(crop_page.get("render_binding"), "page render")
    image = Image.open(io.BytesIO(payload)).convert("RGB")
    left, top, right, bottom = ref["bbox"]
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise _error("authenticated pixel dash bbox is out of bounds")
    crop = image.crop((left, top, right, bottom))
    digest = hashlib.sha256(crop.tobytes()).hexdigest()
    if digest != ref["pixel_rgb_sha256"]:
        raise _error("authenticated pixel dash crop drifted")
    return {
        "pixel_bbox": list(ref["bbox"]),
        "pixel_rgb_sha256": digest,
        "pixel_transcription": "-",
        "normalized_value": 0,
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
        "authenticated_pixel_dash_zero_count": sum(
            component["source_numeric_challenger_status"]
            == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
            for component in value["components"]
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
        "verified_value_cell_count": sum(
            len(value["components"])
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["values"]
        ),
    }


def _source_period_status(source_period: str) -> str:
    return (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if source_period == "2026-03-31"
        else "VERIFIED_SOURCE_PERIOD_Q2_2026"
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("Government/SBV result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("Government/SBV result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS",
                "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT",
            }
            or any(
                row.get("status") != "VERIFIED_BY_CODEX"
                for row in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED" for row in trial.get("unmapped_source_rows", [])
            )
        ):
            raise _error("Government/SBV trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("Government/SBV result identity drifted")
    return canonical_clone_v1(value)


def build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1(
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
            or matcher["regions"][0]["owner"]["page_sequence"] != reviewed["owner"]["page_sequence"]
            or matcher["regions"][0]["owner"]["source_line_index"]
            != reviewed["owner"]["line_index"]
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed Government/SBV region is not the unique whole-PDF graph")
        page_cache: dict[int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]] = {}

        def context(
            page_sequence: int,
            *,
            page_cache: dict[
                int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]
            ] = page_cache,
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
            if page_sequence not in page_cache:
                axis_page = _page(axis_document, page_sequence, "accounting axis")
                semantic_page = _page(semantic_document, page_sequence, "semantic index")
                crop_page = _page(crop_document, page_sequence, "crop manifest")
                page_cache[page_sequence] = (
                    axis_page,
                    semantic_page,
                    crop_page,
                    support._source_line_axis(crop_page),
                )
            return page_cache[page_sequence]

        value_cache: dict[str, dict[str, Any]] = {}

        def verified(
            ref: Mapping[str, Any],
            *,
            value_cache: dict[str, dict[str, Any]] = value_cache,
            context: Any = context,
        ) -> dict[str, Any]:
            key = canonical_json_sha256_v1(ref)
            if key not in value_cache:
                axis_page, semantic_page, crop_page, source_texts = context(ref["page_sequence"])
                if ref["kind"] == "AUTHENTICATED_LINE":
                    evidence = support._source_value(
                        axis_page,
                        semantic_page,
                        crop_page,
                        source_texts,
                        {
                            "line_index": ref["line_index"],
                            "pixel_transcription": ref["pixel_transcription"],
                        },
                    )
                    value_cache[key] = {**evidence, "page_sequence": ref["page_sequence"]}
                elif ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH":
                    value_cache[key] = {
                        **_pixel_dash_value(crop_page, ref),
                        "page_sequence": ref["page_sequence"],
                    }
                else:
                    raise _error("reviewed numeric evidence kind drifted")
            return canonical_clone_v1(value_cache[key])

        verified_mappings = []
        for mapping in reviewed["mappings"]:
            labels = []
            for item in mapping["labels"]:
                axis_page, semantic_page, _, _ = context(item["page_sequence"])
                labels.append(
                    {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    }
                )
            values = []
            for period_role in ("CURRENT", "COMPARATIVE"):
                components = [verified(item) for item in mapping["values"][period_role]]
                values.append(
                    {
                        "aggregation": "DIRECT_VISIBLE_VALUE"
                        if len(components) == 1
                        else "SUM_OF_VISIBLE_SOURCE_ROWS",
                        "components": components,
                        "normalized_value": sum(item["normalized_value"] for item in components),
                        "period_role": period_role,
                    }
                )
            verified_mappings.append(
                {
                    "label_evidence": labels,
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
            terms = []
            computed = 0
            for ref in equation["terms"]:
                evidence = verified(ref)
                computed += ref["multiplier"] * evidence["normalized_value"]
                terms.append(
                    {
                        "multiplier": ref["multiplier"],
                        "page_sequence": ref["page_sequence"],
                        "source_line_index": evidence["source_line_index"],
                        "value": evidence["normalized_value"],
                    }
                )
            total = verified(equation["total"])
            if computed != total["normalized_value"]:
                raise _error(
                    f"Government/SBV accounting equation does not close: {equation['name']}"
                )
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "period_role": equation["period_role"],
                    "status": "VERIFIED_EXACT",
                    "terms": terms,
                    "visible_total": total["normalized_value"],
                    "visible_total_page_sequence": equation["total"]["page_sequence"],
                    "visible_total_source_line_index": total["source_line_index"],
                }
            )
        unmapped_rows = []
        for row in reviewed["unmapped_source_rows"]:
            item = row["label"]
            axis_page, semantic_page, _, _ = context(item["page_sequence"])
            unmapped_rows.append(
                {
                    "item_id": row["item_id"],
                    "label_evidence": {
                        "page_sequence": item["page_sequence"],
                        **_semantic_evidence(axis_page, semantic_page, item),
                    },
                    "reason": row["reason"],
                    "status": "UNRESOLVED",
                    "values": [
                        {
                            "components": [verified(ref) for ref in row["values"][period_role]],
                            "period_role": period_role,
                        }
                        for period_role in ("CURRENT", "COMPARATIVE")
                    ],
                }
            )
        owner_page, owner_semantic_page, _, _ = context(reviewed["owner"]["page_sequence"])
        period_evidence = []
        for item in reviewed["period_axis"]:
            axis_page, semantic_page, _, _ = context(item["page_sequence"])
            period_evidence.append(
                {
                    "page_sequence": item["page_sequence"],
                    **_semantic_evidence(axis_page, semantic_page, item),
                }
            )
        unit_evidence = []
        for item in reviewed["unit_evidence"]:
            axis_page, semantic_page, _, _ = context(item["page_sequence"])
            unit_evidence.append(
                {
                    "page_sequence": item["page_sequence"],
                    **_semantic_evidence(axis_page, semantic_page, item),
                }
            )
        source_period_status = _source_period_status(reviewed["source_period"])
        status = reviewed["disposition"]
        if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2":
            status = "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner_evidence": _semantic_evidence(
                    owner_page, owner_semantic_page, reviewed["owner"]
                ),
                "page_span": reviewed["page_span"],
                "period_axis_evidence": period_evidence,
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": status,
                "structure_graph_id": matcher["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "unit_evidence": unit_evidence,
                "unmapped_source_rows": unmapped_rows,
                "verified_accounting_equations": equations,
                "verified_mappings": verified_mappings,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    schema_family = {
        "family_end_display_order": max(
            _schema_binding(schema_by_id.get(item), item)["display_order"]
            for item in _SCHEMA_EXPECTED
        ),
        "family_root": _schema_binding(schema_by_id.get(1024), 1024),
        "mapped_report_norm_ids": sorted(
            {
                mapping["schema_binding"]["report_norm_id"]
                for trial in trials
                for mapping in trial["verified_mappings"]
            }
        ),
    }
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
        "schema_family": schema_family,
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_government_nhnn_liabilities_8bank_codex_verified_mapping_replay_v1(
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
    rebuilt = build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1(
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
        raise _error("Government/SBV verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> tuple[Any, ...]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_government_nhnn_liabilities_full_document_scan_v1(semantic_index)
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("live Government/SBV structure scan identity drifted")
    review = _review_blueprint()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_sha,
        review_sha,
    )


def build_live_government_nhnn_liabilities_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_sha,
        review_sha,
    ) = _live_inputs()
    return build_government_nhnn_liabilities_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_government_nhnn_liabilities_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_sha,
        review_sha,
    ) = _live_inputs()
    return validate_government_nhnn_liabilities_8bank_codex_verified_mapping_replay_v1(
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
    payload = canonical_json_bytes_v1(value)
    if path.exists() and path.read_bytes() != payload:
        raise _error(f"refusing to replace a different artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    review = _review_blueprint()
    if args.write_review:
        _write(REVIEW_PATH, review)
    result = build_live_government_nhnn_liabilities_8bank_codex_verified_mapping_v1()
    if args.write_result:
        _write(RESULT_PATH, result)
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
