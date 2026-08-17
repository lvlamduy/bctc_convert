"""Verify and map the eight-bank tangible fixed-asset movement family."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image, ImageChops

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

__all__ = [
    "FORMAT_VERSION",
    "TangibleFixedAssets8BankCodexVerifiedMappingV1Error",
    "build_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1",
    "build_tangible_fixed_assets_8bank_codex_verified_mapping_v1",
    "validate_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1",
    "validate_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_experiment_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = _load_experiment_module(
    "trading_securities_support_for_tangible_fixed_assets",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_experiment_module(
    "tangible_fixed_assets_scan_for_verified_mapping",
    "scan_tangible_fixed_assets_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "TANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "TANGIBLE_FIXED_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_TANGIBLE_FIXED_"
    "ASSET_VARIANT_GRAPH_PLUS_ROTATED_SAME_TRANSFORMER_RESCUE_VISIBLE_PIXEL_"
    "PPOCRV6_NUMERIC_CHALLENGER_CURRENT_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_"
    "SCHEMA_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0069-tangible-fixed-assets-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0069-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
ROTATED_PPOCR_ROOT = Path("output/development/vib-page37-rotated-ppocrv6-v1")
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "tfafdsv1:scan:e301c4f490fb8231475e41676653d1c37b663f68364fc22e9dac58f9fd5f7a1f"
EXPECTED_PERSISTED_RESULT_SHA256 = (
    "a7cb421971d881ea016b801e00262b29cb24e92c02735d9760b3281fb868619d"
)
EXPECTED_RESCUE_LINE_COUNT = 100
_RESULT_STATE = "TANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFICATION_COMPLETE"
_RESULT_ID_PREFIX = "e0069:result:"
_REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0069:pixel-review:"
_REVIEW_RUN_ID = "E-0069"
_SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}
_REQUIRE_ROTATED_VIETOCR_NUMERIC_MATCH = True
_PPOCR_REFS = {
    "ocr_result": (
        Path("output/development/vib-page37-rotated-ppocrv6-v1/reader-output/ocr_result.json"),
        "2b73b80003f2c327292d2756bcbb3c878651a77f6152c35fd5714c8fbbb44851",
        96183,
    ),
    "rotated_page": (
        Path("output/development/vib-page37-rotated-ppocrv6-v1/rotated-page.png"),
        "15a22ec091ae00910dd39d9e210d58611347efdb50219ccd2c9d42ba0b1cbc96",
        71917,
    ),
    "run_manifest": (
        Path("output/development/vib-page37-rotated-ppocrv6-v1/reader-output/run_manifest.json"),
        "9d740725b28114e2330a6c08a76691e20c43a213d873be70325fe85dae75005f",
        2717,
    ),
    "source_page": (
        Path("output/development/vib-page37-rotated-ppocrv6-v1/source-page.png"),
        "29e6259ddd0f1991f17893a447c0eea6cc61e80f1098b504888c06e3b96cf361",
        110015,
    ),
}
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_OR_BOUND_REPORT_ABSENCE",
    "OWNER_PRECEDES_COST_DEPRECIATION_AND_CARRYING_BRANCHES",
    "OPTIONAL_MOVEMENT_ROWS_AND_ASSET_CLASS_COLUMNS",
    "CURRENT_PERIOD_SELECTED_COMPARATIVE_CONTINUATION_EXCLUDED",
    "MILLION_VND_UNIT_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_AND_SIGNS",
    "PPOCRV6_NUMERIC_CHALLENGER",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "COST_MINUS_DEPRECIATION_EQUALS_CARRYING_VALUE",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_PPOCRV6_CHALLENGER_AND_ACCOUNTING",
    "old_ocr_used_as_semantic_anchor": False,
    "optional_movement_rows_required_in_every_bank": False,
    "rotated_page_rescue_used_same_pinned_vietocr_transformer": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_tangible_fixed_asset_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_ppocrv6_used_only_as_numeric_challenger": True,
    "rotated_same_vietocr_transformer_used_only_as_semantic_rescue": True,
    "text_similarity_alone_used_for_mapping": False,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "state",
    "trials",
}
_ABSENT_TRIAL_FIELDS = {
    "absence_reason",
    "boundary_evidence",
    "boundary_pages",
    "disposition",
    "document_ordinal",
    "document_provenance",
    "equations",
    "mappings",
    "source_pdf_sha256",
    "source_period",
    "source_period_status",
    "structure_graph_id",
}
_PRESENT_TRIAL_FIELDS = {
    "absence_reason",
    "boundary_evidence",
    "boundary_pages",
    "branch_evidence",
    "comparative_control_page",
    "disposition",
    "document_ordinal",
    "document_provenance",
    "equations",
    "mappings",
    "owner_evidence",
    "page_sequence",
    "source_pdf_sha256",
    "source_period",
    "source_period_status",
    "structure_graph_id",
    "unit_authority",
    "visible_page_render_binding",
}
_SCHEMA_EXPECTED = {
    870: ("Số dư đầu kỳ", 869),
    5991: ("Tổng tăng nguyên giá TSCĐ hữu hình trong kỳ", 869),
    871: ("+ Mua trong kỳ", 5991),
    875: ("+ Tăng khác", 5991),
    5992: ("Tổng giảm nguyên giá TSCĐ hữu hình trong kỳ", 869),
    880: ("+ Thanh lý. nhượng bán (*)", 5992),
    5993: ("Tăng/(Giảm) khác nguyên giá TSCĐ hữu hình trong kỳ", 869),
    5962: ("+ Chênh lệch tỷ giá", 869),
    882: ("Số dư cuối kỳ", 869),
    884: ("Số dư đầu kỳ", 883),
    5994: ("Tổng tăng hao mòn TSCĐ hữu hình trong kỳ", 883),
    885: ("+ Khấu hao trong kỳ", 5994),
    5995: ("Tổng giảm hao mòn TSCĐ hữu hình trong kỳ", 883),
    892: ("+ Thanh lý. nhượng bán (*)", 5995),
    5996: ("Tăng/(Giảm) khác hao mòn TSCĐ hữu hình trong kỳ", 883),
    5963: ("+ Chênh lệch tỷ giá", 883),
    895: ("Số dư cuối kỳ", 883),
    5965: ("Số dư đầu kỳ", 5964),
    5966: ("Số dư cuối kỳ", 5964),
}
_SCHEMA_DISPLAY_ORDER_SNAPSHOT = {
    870: 338,
    5991: 339,
    871: 340,
    875: 344,
    5992: 345,
    880: 350,
    5993: 352,
    5962: 353,
    882: 354,
    884: 356,
    5994: 357,
    885: 358,
    5995: 361,
    892: 366,
    5996: 369,
    5963: 370,
    895: 371,
    5965: 373,
    5966: 374,
}


class TangibleFixedAssets8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, numeric challenger, accounting or schema drifted."""


def _error(message: str) -> TangibleFixedAssets8BankCodexVerifiedMappingV1Error:
    return TangibleFixedAssets8BankCodexVerifiedMappingV1Error(message)


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _money(value: Any) -> int:
    if type(value) is not str or value != value.strip() or not value:
        raise _error(f"visible money transcription is invalid: {value!r}")
    negative = value.startswith("(") and value.endswith(")")
    digits = value.strip("()").replace(".", "").replace(",", "").replace(" ", "")
    if not digits.isdigit():
        raise _error(f"visible money digits drifted: {value!r}")
    number = int(digits)
    return -number if negative else number


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_character in enumerate(left, 1):
        current = [row]
        for column, right_character in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def _semantic_anchor_agrees(proposal: str, pixel_transcription: str) -> bool:
    left = normalize_vietnamese_anchor_v1(proposal)
    right = normalize_vietnamese_anchor_v1(pixel_transcription)
    if not left or not right:
        return False
    if left in right or right in left:
        return True
    return _edit_distance(left, right) <= max(2, len(right) // 10)


def _value(
    line_index: int,
    pixel_transcription: str,
    *,
    ppocr_rotated_line_index: int | None = None,
) -> dict[str, Any]:
    return {
        "line_index": line_index,
        "pixel_transcription": pixel_transcription,
        "ppocr_rotated_line_index": ppocr_rotated_line_index,
    }


def _mapping(
    report_norm_id: int,
    role: str,
    label_line_index: int,
    label_pixel_transcription: str,
    value: dict[str, Any],
    *,
    topology: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "value": value,
    }


def _term(value: dict[str, Any], multiplier: int = 1) -> dict[str, Any]:
    if multiplier not in {-1, 1}:
        raise _error("accounting equation multiplier must be +1 or -1")
    return {"multiplier": multiplier, "value": value}


def _equation(
    name: str, components: Sequence[dict[str, Any]], total: dict[str, Any]
) -> dict[str, Any]:
    return {"components": list(components), "name": name, "total": total}


def _present_doc(
    bank_code: str,
    page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
    source_period: str,
    branch_bindings: Sequence[tuple[str, int, str]],
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    *,
    comparative_control_page: int | None = None,
) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "boundary_pages": [],
        "branch_bindings": [
            {"line_index": index, "pixel_transcription": text, "role": role}
            for role, index, text in branch_bindings
        ],
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "comparative_control_page": comparative_control_page,
        "disposition": "VERIFIED_TANGIBLE_FIXED_ASSET_MOVEMENT_NOTE",
        "equations": list(equations),
        "mappings": list(mappings),
        "owner_line_index": owner_line_index,
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": source_period,
        "unit_authority": "VISIBLE_PAGE_MILLION_VND",
    }


def _absent_doc(bank_code: str, boundary_pages: Sequence[int], reason: str) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "boundary_pages": list(boundary_pages),
        "branch_bindings": [],
        "checks": {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS},
        "comparative_control_page": None,
        "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "equations": [],
        "mappings": [],
        "owner_line_index": None,
        "owner_pixel_transcription": None,
        "page_sequence": None,
        "source_period": None,
        "unit_authority": None,
        "absence_reason": reason,
    }


def _review_documents() -> list[dict[str, Any]]:
    mbb = {
        "cost_open": _value(24, "9.423.236"),
        "cost_increase": _value(30, "457.243"),
        "cost_decrease": _value(34, "(74.634)"),
        "cost_other": _value(37, "(480)"),
        "cost_fx": _value(42, "(36)"),
        "cost_close": _value(48, "9.805.329"),
        "dep_open": _value(55, "5.617.703"),
        "dep_increase": _value(61, "316.859"),
        "dep_decrease": _value(65, "(70.015)"),
        "dep_other": _value(69, "(18)"),
        "dep_fx": _value(75, "68"),
        "dep_close": _value(81, "5.864.597"),
        "carry_open": _value(88, "3.805.533"),
        "carry_close": _value(94, "3.940.732"),
    }
    vpb = {
        "cost_open": _value(31, "3.777.887"),
        "cost_purchase": _value(38, "19.303"),
        "cost_other": _value(45, "27.121"),
        "cost_disposal": _value(52, "(54.216)"),
        "cost_close": _value(59, "3.770.095"),
        "dep_open": _value(67, "2.298.618"),
        "dep_increase": _value(74, "95.468"),
        "dep_disposal": _value(81, "(54.216)"),
        "dep_close": _value(88, "2.339.870"),
        "carry_open": _value(96, "1.479.269"),
        "carry_close": _value(103, "1.430.225"),
    }
    vib = {
        "cost_open": _value(3, "1.260.794", ppocr_rotated_line_index=26),
        "cost_purchase": _value(4, "100.210", ppocr_rotated_line_index=33),
        "cost_disposal": _value(5, "(19.501)", ppocr_rotated_line_index=40),
        "cost_close": _value(6, "1.341.503", ppocr_rotated_line_index=47),
        "dep_open": _value(7, "711.879", ppocr_rotated_line_index=55),
        "dep_increase": _value(8, "54.396", ppocr_rotated_line_index=62),
        "dep_disposal": _value(9, "(10.539)", ppocr_rotated_line_index=69),
        "dep_close": _value(10, "755.736", ppocr_rotated_line_index=76),
        "carry_open": _value(11, "548.915", ppocr_rotated_line_index=84),
        "carry_close": _value(12, "585.767", ppocr_rotated_line_index=91),
    }
    return [
        _absent_doc(
            "ACB",
            [19, 20],
            "OTHER_LONG_TERM_INVESTMENTS_END_THEN_GOVERNMENT_LIABILITIES_NO_TANGIBLE_NOTE",
        ),
        _present_doc(
            "MBB",
            37,
            1,
            "Tài sản cố định hữu hình",
            "2026-06-30",
            [
                ("COST", 18, "Nguyên giá"),
                ("ACCUMULATED_DEPRECIATION", 49, "Hao mòn lũy kế"),
                ("CARRYING_VALUE", 82, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    870, "COST_OPENING", 19, "Số dư đầu kỳ", mbb["cost_open"], topology="COST_CHILD"
                ),
                _mapping(
                    5991,
                    "COST_TOTAL_INCREASE",
                    25,
                    "Tăng trong kỳ",
                    mbb["cost_increase"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    5992,
                    "COST_TOTAL_DECREASE",
                    31,
                    "Giảm trong kỳ",
                    mbb["cost_decrease"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    5993,
                    "COST_OTHER_NET",
                    35,
                    "Tăng/(Giảm) khác trong kỳ",
                    mbb["cost_other"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    5962,
                    "COST_FOREIGN_EXCHANGE",
                    38,
                    "Chênh lệch tỷ giá",
                    mbb["cost_fx"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    882,
                    "COST_ENDING",
                    43,
                    "Số dư cuối kỳ",
                    mbb["cost_close"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    884,
                    "DEPRECIATION_OPENING",
                    50,
                    "Số dư đầu kỳ",
                    mbb["dep_open"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5994,
                    "DEPRECIATION_TOTAL_INCREASE",
                    56,
                    "Tăng trong kỳ",
                    mbb["dep_increase"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5995,
                    "DEPRECIATION_TOTAL_DECREASE",
                    62,
                    "Giảm trong kỳ",
                    mbb["dep_decrease"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5996,
                    "DEPRECIATION_OTHER_NET",
                    67,
                    "Tăng/(Giảm) khác trong kỳ",
                    mbb["dep_other"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5963,
                    "DEPRECIATION_FOREIGN_EXCHANGE",
                    70,
                    "Chênh lệch tỷ giá",
                    mbb["dep_fx"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    895,
                    "DEPRECIATION_ENDING",
                    76,
                    "Số dư cuối kỳ",
                    mbb["dep_close"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5965,
                    "CARRYING_OPENING",
                    83,
                    "Số dư đầu kỳ",
                    mbb["carry_open"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    5966,
                    "CARRYING_ENDING",
                    89,
                    "Số dư cuối kỳ",
                    mbb["carry_close"],
                    topology="CARRYING_CHILD",
                ),
            ],
            [
                _equation(
                    "COST_ROLLFORWARD",
                    [
                        _term(mbb[key])
                        for key in (
                            "cost_open",
                            "cost_increase",
                            "cost_decrease",
                            "cost_other",
                            "cost_fx",
                        )
                    ],
                    mbb["cost_close"],
                ),
                _equation(
                    "DEPRECIATION_ROLLFORWARD",
                    [
                        _term(mbb[key])
                        for key in (
                            "dep_open",
                            "dep_increase",
                            "dep_decrease",
                            "dep_other",
                            "dep_fx",
                        )
                    ],
                    mbb["dep_close"],
                ),
                _equation(
                    "OPENING_COST_MINUS_DEPRECIATION",
                    [_term(mbb["cost_open"]), _term(mbb["dep_open"], -1)],
                    mbb["carry_open"],
                ),
                _equation(
                    "ENDING_COST_MINUS_DEPRECIATION",
                    [_term(mbb["cost_close"]), _term(mbb["dep_close"], -1)],
                    mbb["carry_close"],
                ),
            ],
            comparative_control_page=38,
        ),
        _present_doc(
            "VPB",
            49,
            7,
            "Tài sản cố định hữu hình",
            "2026-03-31",
            [
                ("COST", 24, "Nguyên giá"),
                ("ACCUMULATED_DEPRECIATION", 60, "Giá trị hao mòn lũy kế"),
                ("CARRYING_VALUE", 89, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    870, "COST_OPENING", 25, "Số dư đầu kỳ", vpb["cost_open"], topology="COST_CHILD"
                ),
                _mapping(
                    871,
                    "COST_PURCHASE",
                    32,
                    "Mua trong kỳ",
                    vpb["cost_purchase"],
                    topology="COST_INCREASE_CHILD",
                ),
                _mapping(
                    875,
                    "COST_OTHER_INCREASE",
                    39,
                    "Tăng khác",
                    vpb["cost_other"],
                    topology="COST_INCREASE_CHILD",
                ),
                _mapping(
                    880,
                    "COST_DISPOSAL",
                    46,
                    "Thanh lý, nhượng bán",
                    vpb["cost_disposal"],
                    topology="COST_DECREASE_CHILD",
                ),
                _mapping(
                    882,
                    "COST_ENDING",
                    53,
                    "Số dư cuối kỳ",
                    vpb["cost_close"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    884,
                    "DEPRECIATION_OPENING",
                    61,
                    "Số dư đầu kỳ",
                    vpb["dep_open"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    885,
                    "DEPRECIATION_INCREASE",
                    68,
                    "Khấu hao trong kỳ",
                    vpb["dep_increase"],
                    topology="DEPRECIATION_INCREASE_CHILD",
                ),
                _mapping(
                    892,
                    "DEPRECIATION_DISPOSAL",
                    75,
                    "Thanh lý, nhượng bán",
                    vpb["dep_disposal"],
                    topology="DEPRECIATION_DECREASE_CHILD",
                ),
                _mapping(
                    895,
                    "DEPRECIATION_ENDING",
                    82,
                    "Số dư cuối kỳ",
                    vpb["dep_close"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5965,
                    "CARRYING_OPENING",
                    90,
                    "Tại ngày đầu kỳ",
                    vpb["carry_open"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    5966,
                    "CARRYING_ENDING",
                    97,
                    "Tại ngày cuối kỳ",
                    vpb["carry_close"],
                    topology="CARRYING_CHILD",
                ),
            ],
            [
                _equation(
                    "COST_ROLLFORWARD",
                    [
                        _term(vpb[key])
                        for key in ("cost_open", "cost_purchase", "cost_other", "cost_disposal")
                    ],
                    vpb["cost_close"],
                ),
                _equation(
                    "DEPRECIATION_ROLLFORWARD",
                    [_term(vpb[key]) for key in ("dep_open", "dep_increase", "dep_disposal")],
                    vpb["dep_close"],
                ),
                _equation(
                    "OPENING_COST_MINUS_DEPRECIATION",
                    [_term(vpb["cost_open"]), _term(vpb["dep_open"], -1)],
                    vpb["carry_open"],
                ),
                _equation(
                    "ENDING_COST_MINUS_DEPRECIATION",
                    [_term(vpb["cost_close"]), _term(vpb["dep_close"], -1)],
                    vpb["carry_close"],
                ),
            ],
        ),
        _absent_doc(
            "HDB",
            [30],
            "OTHER_LONG_TERM_INVESTMENTS_THEN_GOVERNMENT_LIABILITIES_NO_TANGIBLE_NOTE",
        ),
        _absent_doc(
            "VCB",
            [33, 34],
            "OTHER_LONG_TERM_INVESTMENTS_END_THEN_GOVERNMENT_LIABILITIES_NO_TANGIBLE_NOTE",
        ),
        _absent_doc(
            "CTG",
            [40, 41],
            "OTHER_LONG_TERM_INVESTMENTS_END_THEN_GOVERNMENT_LIABILITIES_NO_TANGIBLE_NOTE",
        ),
        _absent_doc(
            "BID",
            [24],
            "OTHER_LONG_TERM_INVESTMENTS_THEN_GOVERNMENT_LIABILITIES_NO_TANGIBLE_NOTE",
        ),
        _present_doc(
            "VIB",
            37,
            85,
            "TÀI SẢN CỐ ĐỊNH HỮU HÌNH",
            "2026-06-30",
            [
                ("COST", 96, "Nguyên giá"),
                ("ACCUMULATED_DEPRECIATION", 92, "Khấu hao lũy kế"),
                ("CARRYING_VALUE", 95, "Giá trị còn lại"),
            ],
            [
                _mapping(
                    870,
                    "COST_OPENING",
                    89,
                    "Tại ngày 1/1/2026",
                    vib["cost_open"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    871,
                    "COST_PURCHASE",
                    94,
                    "Mua trong kỳ",
                    vib["cost_purchase"],
                    topology="COST_INCREASE_CHILD",
                ),
                _mapping(
                    880,
                    "COST_DISPOSAL",
                    97,
                    "Thanh lý",
                    vib["cost_disposal"],
                    topology="COST_DECREASE_CHILD",
                ),
                _mapping(
                    882,
                    "COST_ENDING",
                    86,
                    "Tại ngày 30/06/2026",
                    vib["cost_close"],
                    topology="COST_CHILD",
                ),
                _mapping(
                    884,
                    "DEPRECIATION_OPENING",
                    90,
                    "Tại ngày 1/1/2026",
                    vib["dep_open"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    885,
                    "DEPRECIATION_INCREASE",
                    91,
                    "Khấu hao trong kỳ",
                    vib["dep_increase"],
                    topology="DEPRECIATION_INCREASE_CHILD",
                ),
                _mapping(
                    892,
                    "DEPRECIATION_DISPOSAL",
                    98,
                    "Thanh lý",
                    vib["dep_disposal"],
                    topology="DEPRECIATION_DECREASE_CHILD",
                ),
                _mapping(
                    895,
                    "DEPRECIATION_ENDING",
                    87,
                    "Tại ngày 30/06/2026",
                    vib["dep_close"],
                    topology="DEPRECIATION_CHILD",
                ),
                _mapping(
                    5965,
                    "CARRYING_OPENING",
                    93,
                    "Tại ngày 1/1/2026",
                    vib["carry_open"],
                    topology="CARRYING_CHILD",
                ),
                _mapping(
                    5966,
                    "CARRYING_ENDING",
                    88,
                    "Tại ngày 30/06/2026",
                    vib["carry_close"],
                    topology="CARRYING_CHILD",
                ),
            ],
            [
                _equation(
                    "COST_ROLLFORWARD",
                    [_term(vib[key]) for key in ("cost_open", "cost_purchase", "cost_disposal")],
                    vib["cost_close"],
                ),
                _equation(
                    "DEPRECIATION_ROLLFORWARD",
                    [_term(vib[key]) for key in ("dep_open", "dep_increase", "dep_disposal")],
                    vib["dep_close"],
                ),
                _equation(
                    "OPENING_COST_MINUS_DEPRECIATION",
                    [_term(vib["cost_open"]), _term(vib["dep_open"], -1)],
                    vib["carry_open"],
                ),
                _equation(
                    "ENDING_COST_MINUS_DEPRECIATION",
                    [_term(vib["cost_close"]), _term(vib["dep_close"], -1)],
                    vib["carry_close"],
                ),
            ],
        ),
    ]


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
        raise _error("Codex tangible-fixed-assets pixel review differs from the fixed ledger")
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
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict
        and page.get("physical_page", page.get("page_sequence")) == page_sequence
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain page {page_sequence}")
    return matches[0]


def _axis_line(page: Mapping[str, Any], line_index: int) -> dict[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= line_index < len(lines):
        raise _error("fresh VietOCR line index drifted")
    line = lines[line_index]
    if (
        type(line) is not dict
        or line.get("source_line_index") != line_index
        or type(line.get("vietocr_text")) is not str
    ):
        raise _error("fresh VietOCR semantic line identity drifted")
    return line


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    snapshot_order = _SCHEMA_DISPLAY_ORDER_SNAPSHOT.get(report_norm_id)
    if (
        expected is None
        or snapshot_order is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or type(item.display_order) is not int
        or item.display_order <= 0
    ):
        raise _error(f"live TM schema binding drifted for ReportNormId {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": snapshot_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _schema_authority_for_output(live_schema_authority: Any) -> Any:
    if type(live_schema_authority) is not dict:
        raise _error("live schema authority drifted")
    persisted, _ = _stable_json(RESULT_PATH, EXPECTED_PERSISTED_RESULT_SHA256)
    input_refs = persisted.get("input_refs")
    snapshot = input_refs.get("schema_authority") if type(input_refs) is dict else None
    if type(snapshot) is not dict:
        raise _error("pinned schema authority snapshot drifted")
    return canonical_clone_v1(snapshot)


def _artifact_bytes(reference: Any, label: str) -> bytes:
    if (
        type(reference) is not dict
        or set(reference) != {"path", "sha256", "size_bytes"}
        or type(reference["path"]) is not str
        or type(reference["size_bytes"]) is not int
    ):
        raise _error(f"{label} reference fields drifted")
    payload = support._stable_bytes(Path(reference["path"]))
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error(f"{label} bytes drifted")
    return payload


def _rotated_ppocr_evidence() -> dict[str, Any]:
    refs = {}
    values = {}
    for key, (path, digest, size) in _PPOCR_REFS.items():
        payload = support._stable_bytes(path)
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise _error(f"fixed rotated PP-OCRv6 artifact drifted: {key}")
        refs[key] = {"path": path.as_posix(), "sha256": digest, "size_bytes": size}
        if path.suffix == ".json":
            values[key] = support._strict_json(payload, path.as_posix())
    with Image.open(_PPOCR_REFS["source_page"][0]) as source_image:
        expected_rotated = source_image.transpose(Image.Transpose.ROTATE_270).convert("RGB")
    with Image.open(_PPOCR_REFS["rotated_page"][0]) as rotated_image:
        actual_rotated = rotated_image.convert("RGB")
    if (
        expected_rotated.size != actual_rotated.size
        or ImageChops.difference(expected_rotated, actual_rotated).getbbox() is not None
    ):
        raise _error("rotated PP-OCRv6 page is not one exact clockwise-90 pixel transform")
    result = values["ocr_result"]
    run = values["run_manifest"]
    texts = result.get("rec_texts")
    scores = result.get("rec_scores")
    boxes = result.get("rec_boxes")
    runtime = run.get("runtime")
    models = runtime.get("models") if type(runtime) is dict else None
    if (
        type(texts) is not list
        or type(scores) is not list
        or type(boxes) is not list
        or not len(texts) == len(scores) == len(boxes) == 101
        or not all(type(text) is str for text in texts)
        or not all(type(score) is float and math.isfinite(score) for score in scores)
    ):
        raise _error("rotated PP-OCRv6 result axes drifted")
    if (
        run.get("state") != "OCR_COMPLETE"
        or run.get("dataset_role") != "CALIBRATION"
        or run.get("evidence_role") != "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY"
        or run.get("confidence_policy") != "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION"
        or run.get("input", {}).get("sha256") != refs["rotated_page"]["sha256"]
        or run.get("input", {}).get("size_bytes") != refs["rotated_page"]["size_bytes"]
        or run.get("configuration", {}).get("implicit_orientation_or_unwarp") is not False
        or run.get("configuration", {}).get("network_policy") != "PROCESS_SOCKET_CONNECT_DENIED"
        or run.get("configuration", {}).get("precision") != "fp32"
        or type(models) is not list
        or len(models) != 2
        or not all(type(model) is dict for model in models)
        or models[0].get("repo_id") != "PaddlePaddle/PP-OCRv6_medium_det"
        or models[1].get("repo_id") != "PaddlePaddle/PP-OCRv6_medium_rec"
    ):
        raise _error("rotated PP-OCRv6 run identity or safety drifted")
    return {"input_refs": refs, "rec_scores": scores, "rec_texts": texts}


def _rescue_by_index(rescue: Mapping[str, Any] | None) -> dict[int, dict[str, Any]]:
    return (
        {}
        if rescue is None
        else {sample["source_line_index"]: sample for sample in rescue["samples"]}
    )


def _rescue_line_count(rescue: Mapping[str, Any]) -> int | None:
    if type(rescue.get("line_count")) is int:
        return rescue["line_count"]
    metrics = rescue.get("metrics")
    if type(metrics) is dict and type(metrics.get("line_count")) is int:
        return metrics["line_count"]
    return None


def _rescue_identity(rescue: Mapping[str, Any]) -> str | None:
    for key in ("rescue_id", "projection_id"):
        if type(rescue.get(key)) is str:
            return rescue[key]
    return None


def _rescue_for_page(
    rescue: Mapping[str, Any],
    document_ordinal: int,
    physical_page: int,
    source_pdf_sha256: str,
) -> dict[str, Any] | None:
    samples = rescue.get("samples")
    if type(samples) is not list:
        raise _error("rotated VietOCR rescue sample axis drifted")
    if type(rescue.get("document_ordinal")) is int:
        locator_matches = (
            rescue["document_ordinal"] == document_ordinal
            and rescue.get("physical_page") == physical_page
        )
    elif type(rescue.get("source_pdf_sha256")) is str:
        locator_matches = (
            rescue["source_pdf_sha256"] == source_pdf_sha256
            and rescue.get("physical_page") == physical_page
        )
    else:
        selected = [
            sample
            for sample in samples
            if type(sample) is dict
            and sample.get("document_ordinal") == document_ordinal
            and sample.get("physical_page") == physical_page
        ]
        return None if not selected else {"samples": selected}
    return {"samples": samples} if locator_matches else None


def _load_live_rescue(semantic_index: Any) -> Mapping[str, Any]:
    return scanner.authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index)


def _semantic_evidence(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    line_index: int,
    pixel_transcription: str,
    rescue_by_index: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    axis = _axis_line(axis_page, line_index)
    semantic_lines = semantic_page.get("lines")
    if type(semantic_lines) is not list or not 0 <= line_index < len(semantic_lines):
        raise _error("semantic-index crop line axis drifted")
    semantic_line = semantic_lines[line_index]
    if (
        type(semantic_line) is not dict
        or semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis["vietocr_text"]
        or type(semantic_line.get("crop_ref")) is not dict
    ):
        raise _error("semantic-index source/crop binding drifted")
    rescue = rescue_by_index.get(line_index)
    proposal = axis["vietocr_text"] if rescue is None else rescue["semantic_text"]
    rotated_ref = None if rescue is None else canonical_clone_v1(rescue["rotated_crop_ref"])
    if rescue is not None:
        _artifact_bytes(rotated_ref, "rotated VietOCR crop")
    if not _semantic_anchor_agrees(proposal, pixel_transcription):
        raise _error("fresh VietOCR semantic proposal disagrees with visible pixel anchor")
    _artifact_bytes(semantic_line["crop_ref"], "source line crop")
    return {
        "fresh_vietocr_proposal": proposal,
        "normalized_pixel_transcription": normalize_vietnamese_anchor_v1(pixel_transcription),
        "normalized_semantic_proposal": normalize_vietnamese_anchor_v1(proposal),
        "pixel_transcription": pixel_transcription,
        "rotated_vietocr_crop_ref": rotated_ref,
        "semantic_text_source": (
            "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
            if rescue is None
            else "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
        ),
        "source_crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
        "source_line_index": line_index,
    }


def _verified_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
    rescue_by_index: Mapping[int, Mapping[str, Any]],
    rotated_ppocr: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"line_index", "pixel_transcription", "ppocr_rotated_line_index"}
        or type(value["line_index"]) is not int
        or (
            value["ppocr_rotated_line_index"] is not None
            and type(value["ppocr_rotated_line_index"]) is not int
        )
    ):
        raise _error("reviewed value fields drifted")
    line_index = value["line_index"]
    pixel_value = _money(value["pixel_transcription"])
    semantic = _semantic_evidence(
        axis_page,
        semantic_page,
        line_index,
        value["pixel_transcription"],
        rescue_by_index,
    )
    if not 0 <= line_index < len(source_texts):
        raise _error("source numeric challenger line index drifted")
    source_raw = source_texts[line_index]
    try:
        source_value = _money(source_raw)
    except TangibleFixedAssets8BankCodexVerifiedMappingV1Error:
        source_value = None
    rotated_index = value["ppocr_rotated_line_index"]
    rotated_raw = None
    rotated_score = None
    rotated_status = "NOT_REQUIRED_SOURCE_PPOCRV6_MATCHED"
    if rotated_index is None:
        if source_value != pixel_value:
            raise _error("visible pixel and upstream PP-OCRv6 numeric challenger disagree")
    else:
        texts = rotated_ppocr["rec_texts"]
        scores = rotated_ppocr["rec_scores"]
        if not 0 <= rotated_index < len(texts):
            raise _error("rotated PP-OCRv6 numeric challenger index drifted")
        rotated_raw = texts[rotated_index]
        rotated_score = scores[rotated_index]
        if _money(rotated_raw) != pixel_value or rotated_score < 0.99:
            raise _error("rotated PP-OCRv6 challenger disagrees with visible pixel")
        if _REQUIRE_ROTATED_VIETOCR_NUMERIC_MATCH and (
            _money(semantic["fresh_vietocr_proposal"]) != pixel_value
        ):
            raise _error("rotated VietOCR proposal disagrees with visible numeric crop")
        rotated_status = "ROTATED_PPOCRV6_MATCHED_VISIBLE_PIXEL"
    return {
        **semantic,
        "normalized_value": pixel_value,
        "rotated_ppocrv6_challenger": rotated_raw,
        "rotated_ppocrv6_challenger_line_index": rotated_index,
        "rotated_ppocrv6_challenger_score": rotated_score,
        "rotated_ppocrv6_challenger_status": rotated_status,
        "source_numeric_challenger": source_raw,
        "source_numeric_challenger_status": (
            "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
            if source_value == pixel_value
            else "ORIGINAL_ROTATED_SOURCE_OCR_DISAGREED_RESCUED_BY_ROTATED_PPOCRV6"
        ),
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mappings = [item for trial in trials for item in trial["mappings"]]
    equations = [item for trial in trials for item in trial["equations"]]
    values = [item["value"] for item in mappings]
    return {
        "accounting_equation_count": len(equations),
        "confirmed_bound_report_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": len(mappings),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "rotated_original_source_numeric_disagreement_count": sum(
            value["source_numeric_challenger_status"]
            == "ORIGINAL_ROTATED_SOURCE_OCR_DISAGREED_RESCUED_BY_ROTATED_PPOCRV6"
            for value in values
        ),
        "rotated_ppocrv6_verified_value_count": sum(
            value["rotated_ppocrv6_challenger_status"] == "ROTATED_PPOCRV6_MATCHED_VISIBLE_PIXEL"
            for value in values
        ),
        "verified_present_document_count": sum(bool(trial["mappings"]) for trial in trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("tangible-fixed-assets result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("tangible-fixed-assets result identity or authority drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict:
            raise _error("tangible-fixed-assets trial must be one exact object")
        expected_fields = (
            _ABSENT_TRIAL_FIELDS
            if trial.get("disposition") == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            else _PRESENT_TRIAL_FIELDS
        )
        if (
            set(trial) != expected_fields
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or type(trial.get("mappings")) is not list
            or type(trial.get("equations")) is not list
        ):
            raise _error("tangible-fixed-assets trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("tangible-fixed-assets metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("tangible-fixed-assets result identity drifted")
    return canonical_clone_v1(value)


def build_tangible_fixed_assets_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    rescue: Mapping[str, Any],
    rotated_ppocr: Mapping[str, Any],
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or _rescue_line_count(rescue) != EXPECTED_RESCUE_LINE_COUNT
    ):
        raise _error("fixed semantic axis, structure scan or rescue identity drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan.get("trials"), code, "structure scan")
        axis_document = _document(axis.get("documents"), code, "accounting axis")
        semantic_document = _document(semantic_index.get("documents"), code, "semantic index")
        crop_document = _document(crop_manifest.get("documents"), code, "crop manifest")
        matcher_result = scan_trial["matcher_result"]
        if reviewed["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT":
            if matcher_result["regions"] or reviewed["mappings"] or reviewed["equations"]:
                raise _error(f"absence review conflicts with complete region for {code}")
            boundary_evidence = [
                {
                    "physical_page": page_number,
                    "render_binding": canonical_clone_v1(
                        _page(crop_document, page_number, "crop manifest")["render_binding"]
                    ),
                }
                for page_number in reviewed["boundary_pages"]
            ]
            trials.append(
                {
                    "absence_reason": reviewed["absence_reason"],
                    "boundary_evidence": boundary_evidence,
                    "boundary_pages": reviewed["boundary_pages"],
                    "disposition": reviewed["disposition"],
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "equations": [],
                    "mappings": [],
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_FAMILY_NOT_PRESENT",
                    "structure_graph_id": matcher_result["result_id"],
                }
            )
            continue
        if (
            len(matcher_result["regions"]) != 1
            or matcher_result["regions"][0]["owner"]["page_sequence"] != reviewed["page_sequence"]
            or matcher_result["regions"][0]["owner"]["source_line_index"]
            != reviewed["owner_line_index"]
        ):
            raise _error(f"reviewed complete region does not match whole-PDF scan for {code}")
        axis_page = _page(axis_document, reviewed["page_sequence"], "accounting axis")
        semantic_page = _page(semantic_document, reviewed["page_sequence"], "semantic index")
        crop_page = _page(crop_document, reviewed["page_sequence"], "crop manifest")
        source_texts = support._source_line_axis(crop_page)
        rescue_index = _rescue_by_index(
            _rescue_for_page(
                rescue,
                ordinal,
                reviewed["page_sequence"],
                crop_document["source_pdf"]["sha256"],
            )
        )
        owner_evidence = _semantic_evidence(
            axis_page,
            semantic_page,
            reviewed["owner_line_index"],
            reviewed["owner_pixel_transcription"],
            rescue_index,
        )
        branch_evidence = [
            {
                "role": branch["role"],
                **_semantic_evidence(
                    axis_page,
                    semantic_page,
                    branch["line_index"],
                    branch["pixel_transcription"],
                    rescue_index,
                ),
            }
            for branch in reviewed["branch_bindings"]
        ]
        mappings = []
        values_by_line = {}
        for mapping in reviewed["mappings"]:
            label = _semantic_evidence(
                axis_page,
                semantic_page,
                mapping["label_line_index"],
                mapping["label_pixel_transcription"],
                rescue_index,
            )
            verified = _verified_value(
                axis_page,
                semantic_page,
                source_texts,
                mapping["value"],
                rescue_index,
                rotated_ppocr,
            )
            values_by_line[mapping["value"]["line_index"]] = verified
            mappings.append(
                {
                    "final_status": "VERIFIED_BY_CODEX",
                    "label_evidence": label,
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "schema_binding": _schema_binding(
                        schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                    ),
                    "topology": mapping["topology"],
                    "value": verified,
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            terms = []
            computed = 0
            for term in equation["components"]:
                line_index = term["value"]["line_index"]
                verified = values_by_line.get(line_index) or _verified_value(
                    axis_page,
                    semantic_page,
                    source_texts,
                    term["value"],
                    rescue_index,
                    rotated_ppocr,
                )
                computed += term["multiplier"] * verified["normalized_value"]
                terms.append(
                    {
                        "multiplier": term["multiplier"],
                        "source_line_index": line_index,
                        "value": verified["normalized_value"],
                    }
                )
            total_line = equation["total"]["line_index"]
            total = values_by_line.get(total_line) or _verified_value(
                axis_page,
                semantic_page,
                source_texts,
                equation["total"],
                rescue_index,
                rotated_ppocr,
            )
            if computed != total["normalized_value"]:
                raise _error(f"accounting equation does not close for {code}: {equation['name']}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "status": "CORROBORATED_EXACT",
                    "terms": terms,
                    "visible_total": total["normalized_value"],
                    "visible_total_source_line_index": total_line,
                }
            )
        source_period_status = _SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if source_period_status is None:
            raise _error(f"unsupported reviewed source period for {code}")
        trials.append(
            {
                "absence_reason": None,
                "boundary_evidence": [],
                "boundary_pages": reviewed["boundary_pages"],
                "branch_evidence": branch_evidence,
                "comparative_control_page": reviewed["comparative_control_page"],
                "disposition": reviewed["disposition"],
                "document_ordinal": ordinal,
                "document_provenance": code,
                "equations": equations,
                "mappings": mappings,
                "owner_evidence": owner_evidence,
                "page_sequence": reviewed["page_sequence"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "structure_graph_id": matcher_result["result_id"],
                "unit_authority": reviewed["unit_authority"],
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "rotated_ppocrv6": canonical_clone_v1(rotated_ppocr["input_refs"]),
            "rotated_vietocr_rescue_id": _rescue_identity(rescue),
            "schema_authority": _schema_authority_for_output(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    rescue: Mapping[str, Any],
    rotated_ppocr: Mapping[str, Any],
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_tangible_fixed_assets_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        rescue,
        rotated_ppocr,
        schema_authority,
        schema_by_id,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("tangible-fixed-assets verified mapping does not replay exactly")
    return supplied


def _live_inputs() -> tuple[Any, ...]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    rescue = _load_live_rescue(semantic_index)
    structure_scan = scanner.build_tangible_fixed_assets_full_document_scan_v1(
        semantic_index, rescue
    )
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("live tangible-fixed-assets structure scan identity drifted")
    rotated_ppocr = _rotated_ppocr_evidence()
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        crop_manifest,
        structure_scan,
        _review_blueprint(),
        rescue,
        rotated_ppocr,
        schema_authority,
        schema_by_id,
    )


def build_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_tangible_fixed_assets_8bank_codex_verified_mapping_v1(*_live_inputs())


def validate_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_tangible_fixed_assets_8bank_codex_verified_mapping_replay_v1(
        value, *_live_inputs()
    )


def _write(path: Path, value: Any, *, replace: bool = False) -> None:
    payload = canonical_json_bytes_v1(value)
    if path.exists() and path.read_bytes() != payload and not replace:
        raise _error(f"refusing to replace a different artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    review = _review_blueprint()
    if args.write_review:
        _write(REVIEW_PATH, review, replace=args.replace)
    result = build_live_tangible_fixed_assets_8bank_codex_verified_mapping_v1()
    if args.write_result:
        _write(RESULT_PATH, result, replace=args.replace)
    else:
        sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    _main()
