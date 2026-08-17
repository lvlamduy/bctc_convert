"""Verify and map the eight-bank other-long-term-investments family."""

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

__all__ = [
    "FORMAT_VERSION",
    "LongTermInvestments8BankCodexVerifiedMappingV1Error",
    "build_live_long_term_investments_8bank_codex_verified_mapping_v1",
    "build_long_term_investments_8bank_codex_verified_mapping_v1",
    "validate_live_long_term_investments_8bank_codex_verified_mapping_v1",
    "validate_long_term_investments_8bank_codex_verified_mapping_replay_v1",
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
    "trading_securities_support_for_long_term_investments",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_experiment_module(
    "long_term_investments_scan_for_verified_mapping",
    "scan_long_term_investments_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "LONG_TERM_INVESTMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "LONG_TERM_INVESTMENTS_8BANK_CODEX_PIXEL_REVIEW_V1"
_RESULT_STATE = "LONG_TERM_INVESTMENTS_8BANK_CODEX_VERIFICATION_COMPLETE"
_RESULT_ID_PREFIX = "lti8bcv1:result:"
_REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
_REVIEW_ID_PREFIX = "e0068:pixel-review:"
_REVIEW_RUN_ID = "E-0068"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_LONG_TERM_"
    "INVESTMENT_VARIANT_GRAPH_PLUS_INDEPENDENT_VISIBLE_PIXEL_UPSTREAM_NUMERIC_"
    "CHALLENGER_PERIOD_UNIT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_"
    "PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0068-long-term-investments-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0068-long-term-investments-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "ltifdsv1:scan:6889236ce0183b78f765e88fcb1657c0ac6832e57c04f8813fac577d20926284"
REVIEW_SHA256 = "7a20a878fd705505e8e5bc908d6306d3da4826dfe58a0987bb8b9651c1489e48"
_SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}
_TRIAL_STATUS_BY_SOURCE_PERIOD_STATUS = {
    "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2": (
        "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
    ),
    "VERIFIED_SOURCE_PERIOD_Q2_2026": "VERIFIED_BY_CODEX",
}

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "OWNER_PRECEDES_ACCOUNTING_CHILDREN",
    "OPTIONAL_JOINT_VENTURE_ASSOCIATE_OTHER_AND_DETAIL_BRANCHES",
    "CURRENT_AND_COMPARATIVE_PERIOD_AXES",
    "MILLION_VND_UNIT_VISIBLE_OR_DOCUMENT_INHERITED",
    "VISIBLE_PIXEL_LABELS_DIGITS_SIGN_AND_DASH",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "TRAILING_NET_TOTAL_ACCOUNTING_CLOSURE",
    "DETAIL_TABLE_NOT_DOUBLE_COUNTED_WITH_PARENT",
    "LIVE_TM_SCHEMA_HIERARCHY_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER",
    "old_ocr_used_as_semantic_anchor": False,
    "optional_children_required_in_every_bank": False,
    "source_detail_rows_double_counted_with_parent": False,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_long_term_investment_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_detail_rows_double_counted_with_parent": False,
    "text_similarity_alone_used_for_mapping": False,
    "upstream_ppocrv6_or_native_text_used_only_as_numeric_challenger": True,
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
_SCHEMA_EXPECTED = {
    862: ("Các khoản đầu tư dài hạn khác", 560),
    867: ("Đầu tư dài hạn khác", 862),
    5959: ("Dự phòng giảm giá", 862),
    5960: ("Đầu tư vào tổ chức kinh tế, dự án dài hạn", 867),
    5961: ("Đầu tư vào các Quỹ đầu tư", 867),
    6066: ("Đầu tư vào công ty liên doanh", 862),
    6067: ("Đầu tư vào công ty liên kết", 862),
}


class LongTermInvestments8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, accounting, schema or exact replay drifted."""


def _error(message: str) -> LongTermInvestments8BankCodexVerifiedMappingV1Error:
    return LongTermInvestments8BankCodexVerifiedMappingV1Error(message)


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _value(
    period_role: str,
    line_index: int | None,
    pixel_transcription: str,
    *,
    dash_anchor_line_index: int | None = None,
) -> dict[str, Any]:
    return {
        "dash_anchor_line_index": dash_anchor_line_index,
        "line_index": line_index,
        "period_role": period_role,
        "pixel_transcription": pixel_transcription,
    }


def _mapping(
    report_norm_id: int,
    role: str,
    label_line_index: int | None,
    label_pixel_transcription: str | None,
    current: tuple[int | None, str],
    comparative: tuple[int | None, str],
    *,
    topology: str = "OWNER_DIRECT_CHILD",
    dash_anchor_line_index: int | None = None,
    comparative_dash_anchor_line_index: int | None = None,
    page_sequence: int | None = None,
) -> dict[str, Any]:
    result = {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": [
            _value(
                "CURRENT",
                current[0],
                current[1],
                dash_anchor_line_index=dash_anchor_line_index if current[0] is None else None,
            ),
            _value(
                "COMPARATIVE",
                comparative[0],
                comparative[1],
                dash_anchor_line_index=(
                    comparative_dash_anchor_line_index if comparative[0] is None else None
                ),
            ),
        ],
    }
    if page_sequence is not None:
        result["page_sequence"] = page_sequence
    return result


def _equation(
    name: str,
    current_components: Sequence[tuple[int | None, str]],
    current_total: tuple[int, str],
    comparative_components: Sequence[tuple[int | None, str]],
    comparative_total: tuple[int, str],
    *,
    dash_anchor_line_index: int | None = None,
    comparative_dash_anchor_line_index: int | None = None,
    page_sequence: int | None = None,
) -> dict[str, Any]:
    result = {
        "axes": [
            {
                "components": [
                    _value(
                        "CURRENT",
                        line_index,
                        text,
                        dash_anchor_line_index=(
                            dash_anchor_line_index if line_index is None else None
                        ),
                    )
                    for line_index, text in current_components
                ],
                "period_role": "CURRENT",
                "total": _value("CURRENT", current_total[0], current_total[1]),
            },
            {
                "components": [
                    _value(
                        "COMPARATIVE",
                        line_index,
                        text,
                        dash_anchor_line_index=(
                            comparative_dash_anchor_line_index if line_index is None else None
                        ),
                    )
                    for line_index, text in comparative_components
                ],
                "period_role": "COMPARATIVE",
                "total": _value("COMPARATIVE", comparative_total[0], comparative_total[1]),
            },
        ],
        "name": name,
    }
    if page_sequence is not None:
        result["page_sequence"] = page_sequence
    return result


def _doc(
    bank_code: str,
    page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
    source_period: str,
    mappings: Sequence[dict[str, Any]],
    equations: Sequence[dict[str, Any]],
    *,
    unit_authority: str = "VISIBLE_PAGE_MILLION_VND",
) -> dict[str, Any]:
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": "VERIFIED_OTHER_LONG_TERM_INVESTMENTS_NOTE",
        "equations": list(equations),
        "mappings": list(mappings),
        "owner_line_index": owner_line_index,
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": source_period,
        "unit_authority": unit_authority,
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _doc(
            "ACB",
            19,
            59,
            "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
            "2026-06-30",
            [
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    65,
                    "Các khoản đầu tư dài hạn khác",
                    (66, "233.739"),
                    (67, "233.739"),
                ),
                _mapping(
                    5959,
                    "PROVISION",
                    68,
                    "Dự phòng giảm giá đầu tư dài hạn",
                    (69, "(159.428)"),
                    (70, "(159.040)"),
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (71, "74.311"),
                    (72, "74.699"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
            ],
            [
                _equation(
                    "OTHER_PLUS_PROVISION_TO_NET",
                    [(66, "233.739"), (69, "(159.428)")],
                    (71, "74.311"),
                    [(67, "233.739"), (70, "(159.040)")],
                    (72, "74.699"),
                )
            ],
        ),
        _doc(
            "MBB",
            36,
            37,
            "Góp vốn, đầu tư dài hạn",
            "2026-06-30",
            [
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    43,
                    "Đầu tư dài hạn khác",
                    (44, "527.198"),
                    (45, "559.624"),
                ),
                _mapping(
                    5959, "PROVISION", 48, "Dự phòng giảm giá", (49, "(91.228)"), (50, "(91.228)")
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (51, "435.970"),
                    (52, "468.396"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
                _mapping(
                    5960,
                    "ORGANIZATION_PROJECT",
                    59,
                    "Đầu tư vào tổ chức kinh tế, dự án dài hạn",
                    (60, "457.458"),
                    (61, "493.184"),
                    topology="OTHER_LONG_TERM_CHILD",
                ),
                _mapping(
                    5961,
                    "INVESTMENT_FUND",
                    62,
                    "Đầu tư vào các Quỹ đầu tư",
                    (63, "69.740"),
                    (64, "66.440"),
                    topology="OTHER_LONG_TERM_CHILD",
                ),
            ],
            [
                _equation(
                    "ORGANIZATION_PLUS_FUND_TO_OTHER",
                    [(60, "457.458"), (63, "69.740")],
                    (65, "527.198"),
                    [(61, "493.184"), (64, "66.440")],
                    (66, "559.624"),
                ),
                _equation(
                    "OTHER_PLUS_PROVISION_TO_NET",
                    [(44, "527.198"), (49, "(91.228)")],
                    (51, "435.970"),
                    [(45, "559.624"), (50, "(91.228)")],
                    (52, "468.396"),
                ),
            ],
        ),
        _doc(
            "VPB",
            48,
            84,
            "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
            "2026-03-31",
            [
                _mapping(
                    5960,
                    "ORGANIZATION_PROJECT",
                    95,
                    "Đầu tư vào tổ chức kinh tế",
                    (116, "191.960"),
                    (117, "191.960"),
                    topology="ORGANIZATION_DETAIL_PARENT_TOTAL",
                )
            ],
            [
                _equation(
                    "THREE_ORGANIZATIONS_TO_PARENT",
                    [(98, "3.934"), (104, "185.276"), (112, "2.750")],
                    (116, "191.960"),
                    [(100, "3.934"), (106, "185.276"), (114, "2.750")],
                    (117, "191.960"),
                )
            ],
        ),
        _doc(
            "HDB",
            30,
            7,
            "Góp vốn, đầu tư dài hạn",
            "2026-06-30",
            [
                _mapping(
                    6067,
                    "ASSOCIATE",
                    13,
                    "Đầu tư vào công ty liên kết",
                    (None, "-"),
                    (14, "1.040.690"),
                    dash_anchor_line_index=13,
                ),
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    15,
                    "Các khoản đầu tư dài hạn khác",
                    (16, "125.667"),
                    (17, "125.667"),
                ),
                _mapping(
                    5959,
                    "PROVISION",
                    18,
                    "Dự phòng giảm giá các khoản đầu tư dài hạn khác",
                    (19, "(7.975)"),
                    (20, "(8.173)"),
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (21, "117.692"),
                    (22, "1.158.184"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
            ],
            [
                _equation(
                    "ASSOCIATE_OTHER_PROVISION_TO_NET",
                    [(None, "-"), (16, "125.667"), (19, "(7.975)")],
                    (21, "117.692"),
                    [(14, "1.040.690"), (17, "125.667"), (20, "(8.173)")],
                    (22, "1.158.184"),
                    dash_anchor_line_index=13,
                )
            ],
        ),
        _doc(
            "VCB",
            33,
            9,
            "Góp vốn đầu tư dài hạn",
            "2026-06-30",
            [
                _mapping(
                    6066,
                    "JOINT_VENTURE",
                    16,
                    "Các khoản đầu tư vào công ty liên doanh",
                    (17, "182.306"),
                    (18, "734.296"),
                ),
                _mapping(
                    6067,
                    "ASSOCIATE",
                    19,
                    "Các khoản đầu tư vào công ty liên kết",
                    (20, "15.073"),
                    (21, "12.342"),
                ),
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    22,
                    "Các khoản đầu tư dài hạn khác",
                    (23, "1.589.089"),
                    (24, "1.589.089"),
                ),
                _mapping(
                    5959,
                    "PROVISION",
                    25,
                    "Dự phòng giảm giá đầu tư dài hạn",
                    (26, "(75.000)"),
                    (27, "(75.000)"),
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (28, "1.711.468"),
                    (29, "2.260.727"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
            ],
            [
                _equation(
                    "JOINT_ASSOCIATE_OTHER_PROVISION_TO_NET",
                    [(17, "182.306"), (20, "15.073"), (23, "1.589.089"), (26, "(75.000)")],
                    (28, "1.711.468"),
                    [(18, "734.296"), (21, "12.342"), (24, "1.589.089"), (27, "(75.000)")],
                    (29, "2.260.727"),
                )
            ],
        ),
        _doc(
            "CTG",
            40,
            66,
            "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
            "2026-06-30",
            [
                _mapping(
                    6066,
                    "JOINT_VENTURE",
                    71,
                    "Các khoản đầu tư vào công ty liên doanh",
                    (72, "4.352.017"),
                    (73, "4.193.834"),
                ),
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    74,
                    "Các khoản đầu tư dài hạn khác",
                    (75, "234.462"),
                    (76, "234.462"),
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (77, "4.586.479"),
                    (78, "4.428.296"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
            ],
            [
                _equation(
                    "JOINT_PLUS_OTHER_TO_NET",
                    [(72, "4.352.017"), (75, "234.462")],
                    (77, "4.586.479"),
                    [(73, "4.193.834"), (76, "234.462")],
                    (78, "4.428.296"),
                )
            ],
        ),
        _doc(
            "BID",
            24,
            5,
            "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
            "2026-06-30",
            [
                _mapping(
                    6066,
                    "JOINT_VENTURE",
                    9,
                    "Các khoản đầu tư vào công ty liên doanh",
                    (10, "3,423,613"),
                    (11, "3,083,714"),
                ),
                _mapping(
                    6067,
                    "ASSOCIATE",
                    12,
                    "Các khoản đầu tư vào công ty liên kết",
                    (13, "1,179,542"),
                    (14, "1,211,083"),
                ),
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    15,
                    "Các khoản đầu tư dài hạn khác",
                    (16, "182,941"),
                    (17, "183,050"),
                ),
                _mapping(
                    5959,
                    "PROVISION",
                    18,
                    "Dự phòng giảm giá đầu tư dài hạn",
                    (19, "(104,197)"),
                    (20, "(104,203)"),
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (21, "4,681,899"),
                    (22, "4,373,644"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
            ],
            [
                _equation(
                    "JOINT_ASSOCIATE_OTHER_PROVISION_TO_NET",
                    [(10, "3,423,613"), (13, "1,179,542"), (16, "182,941"), (19, "(104,197)")],
                    (21, "4,681,899"),
                    [(11, "3,083,714"), (14, "1,211,083"), (17, "183,050"), (20, "(104,203)")],
                    (22, "4,373,644"),
                )
            ],
            unit_authority="DOCUMENT_LEVEL_MILLION_VND",
        ),
        _doc(
            "VIB",
            36,
            33,
            "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
            "2026-06-30",
            [
                _mapping(
                    867,
                    "OTHER_LONG_TERM",
                    38,
                    "Đầu tư dài hạn khác",
                    (39, "69.667"),
                    (40, "69.667"),
                ),
                _mapping(
                    5959,
                    "PROVISION",
                    41,
                    "Dự phòng giảm giá góp vốn, đầu tư dài hạn",
                    (42, "(210)"),
                    (43, "(210)"),
                ),
                _mapping(
                    862,
                    "NET_TOTAL",
                    None,
                    None,
                    (44, "69.457"),
                    (45, "69.457"),
                    topology="UNLABELED_TRAILING_NET_TOTAL",
                ),
            ],
            [
                _equation(
                    "OTHER_PLUS_PROVISION_TO_NET",
                    [(39, "69.667"), (42, "(210)")],
                    (44, "69.457"),
                    [(40, "69.667"), (43, "(210)")],
                    (45, "69.457"),
                )
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
        raise _error("Codex long-term-investment pixel review differs from the fixed ledger")
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
    if type(line) is not dict or line.get("source_line_index") != line_index:
        raise _error("fresh VietOCR line identity drifted")
    return line


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
        raise _error("reviewed mapping does not bind one exact live TM item")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _verified_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "dash_anchor_line_index",
        "line_index",
        "period_role",
        "pixel_transcription",
    }:
        raise _error("reviewed value fields drifted")
    if value["period_role"] not in {"CURRENT", "COMPARATIVE"}:
        raise _error("reviewed period role drifted")
    if value["line_index"] is None:
        if value["pixel_transcription"] != "-" or type(value["dash_anchor_line_index"]) is not int:
            raise _error("DASH review evidence drifted")
        anchor = _axis_line(axis_page, value["dash_anchor_line_index"])
        return {
            "dash_anchor_bbox": list(anchor["bbox"]),
            "dash_anchor_line_index": value["dash_anchor_line_index"],
            "fresh_vietocr_numeric_proposal": None,
            "normalized_value": 0,
            "period_role": value["period_role"],
            "pixel_transcription": "-",
            "source_line_index": None,
            "source_numeric_challenger": None,
            "source_numeric_challenger_status": "VISIBLE_DASH_CELL_WITH_NO_TEXT_LINE_NORMALIZED_TO_ZERO",
            "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
        }
    if value["dash_anchor_line_index"] is not None or type(value["line_index"]) is not int:
        raise _error("non-DASH value line identity drifted")
    try:
        evidence = support._source_value(
            axis_page,
            semantic_page,
            crop_page,
            source_texts,
            {
                "line_index": value["line_index"],
                "pixel_transcription": value["pixel_transcription"],
            },
        )
    except Exception as exc:
        raise _error(f"long-term-investment numeric evidence drifted: {exc}") from exc
    return {**evidence, "period_role": value["period_role"]}


def _normalized(value: Mapping[str, Any]) -> int:
    parsed = support._money(value["pixel_transcription"])
    if type(parsed) is not int:
        raise _error("normalized accounting value is not exact int")
    return parsed


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
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
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("long-term-investment mapping result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != _RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("long-term-investment mapping identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {"VERIFIED_BY_CODEX", "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"}
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("verified_accounting_equations")) is not list
        ):
            raise _error("long-term-investment mapping trial shape drifted")
        if any(
            mapping.get("status") != "VERIFIED_BY_CODEX" for mapping in trial["verified_mappings"]
        ):
            raise _error("long-term-investment mapping row status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != _RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("long-term-investment mapping result identity drifted")
    return canonical_clone_v1(value)


def build_long_term_investments_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build the exact eight-bank bounded mapping result."""

    review = _review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state")
        != "FULL_DOCUMENT_LONG_TERM_INVESTMENTS_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("long-term-investment input authority drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(review["documents"], code, "pixel review")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        scan_trial = _document(structure_scan["trials"], code, "structure scan")
        page_sequence = reviewed["page_sequence"]
        axis_page = _page(axis_document, page_sequence, "accounting axis")
        semantic_page = _page(semantic_document, page_sequence, "semantic index")
        crop_page = _page(crop_document, page_sequence, "crop manifest")
        matcher = scan_trial["matcher_result"]
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["owner"]["page_sequence"] != page_sequence
            or matcher["regions"][0]["owner"]["source_line_index"] != reviewed["owner_line_index"]
        ):
            raise _error("reviewed region is not the unique full-PDF graph")
        owner = _axis_line(axis_page, reviewed["owner_line_index"])
        if "gop von" not in normalize_vietnamese_anchor_v1(owner["vietocr_text"]):
            raise _error("reviewed owner is not supported by fresh VietOCR")
        page_cache: dict[int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any]] = {
            page_sequence: (
                axis_page,
                semantic_page,
                crop_page,
                support._source_line_axis(crop_page),
            )
        }

        def evidence_page(
            requested_page_sequence: int,
            *,
            _page_cache: dict[
                int, tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any]
            ] = page_cache,
            _axis_document: dict[str, Any] = axis_document,
            _semantic_document: dict[str, Any] = semantic_document,
            _crop_document: dict[str, Any] = crop_document,
        ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any]:
            if requested_page_sequence not in _page_cache:
                requested_axis_page = _page(
                    _axis_document, requested_page_sequence, "accounting axis"
                )
                requested_semantic_page = _page(
                    _semantic_document, requested_page_sequence, "semantic index"
                )
                requested_crop_page = _page(
                    _crop_document, requested_page_sequence, "crop manifest"
                )
                _page_cache[requested_page_sequence] = (
                    requested_axis_page,
                    requested_semantic_page,
                    requested_crop_page,
                    support._source_line_axis(requested_crop_page),
                )
            return _page_cache[requested_page_sequence]

        mapped_rows = []
        for mapping in reviewed["mappings"]:
            mapping_page_sequence = mapping.get("page_sequence", page_sequence)
            if type(mapping_page_sequence) is not int:
                raise _error("reviewed mapping page identity drifted")
            mapping_axis_page, mapping_semantic_page, mapping_crop_page, source_texts = (
                evidence_page(mapping_page_sequence)
            )
            label_proposal = None
            if mapping["label_line_index"] is not None:
                label_proposal = _axis_line(mapping_axis_page, mapping["label_line_index"])[
                    "vietocr_text"
                ]
                if type(mapping["label_pixel_transcription"]) is not str:
                    raise _error("reviewed mapping pixel label drifted")
                try:
                    support._anchor_match(
                        label_proposal,
                        mapping["label_pixel_transcription"],
                        "long-term-investment row label",
                    )
                except Exception as exc:
                    raise _error(
                        f"long-term-investment semantic label evidence drifted: {exc}"
                    ) from exc
            values = [
                _verified_value(
                    mapping_axis_page,
                    mapping_semantic_page,
                    mapping_crop_page,
                    source_texts,
                    item,
                )
                for item in mapping["values"]
            ]
            mapped_row = {
                "fresh_vietocr_label_proposal": label_proposal,
                "label_line_index": mapping["label_line_index"],
                "label_pixel_transcription": mapping["label_pixel_transcription"],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": values,
            }
            if "page_sequence" in mapping:
                mapped_row["page_sequence"] = mapping_page_sequence
            mapped_rows.append(mapped_row)
        equations = []
        for equation in reviewed["equations"]:
            equation_page_sequence = equation.get("page_sequence", page_sequence)
            if type(equation_page_sequence) is not int:
                raise _error("reviewed equation page identity drifted")
            equation_axis_page, equation_semantic_page, equation_crop_page, source_texts = (
                evidence_page(equation_page_sequence)
            )
            axes = []
            for equation_axis in equation["axes"]:
                components = [
                    _verified_value(
                        equation_axis_page,
                        equation_semantic_page,
                        equation_crop_page,
                        source_texts,
                        item,
                    )
                    for item in equation_axis["components"]
                ]
                total = _verified_value(
                    equation_axis_page,
                    equation_semantic_page,
                    equation_crop_page,
                    source_texts,
                    equation_axis["total"],
                )
                computed = sum(_normalized(item) for item in components)
                visible = _normalized(total)
                if computed != visible:
                    raise _error("visible long-term-investment accounting equation does not close")
                axes.append(
                    {
                        "component_values": [item["normalized_value"] for item in components],
                        "computed_total": computed,
                        "period_role": equation_axis["period_role"],
                        "status": "EXACT",
                        "visible_total": visible,
                    }
                )
            verified_equation = {
                "axes": axes,
                "name": equation["name"],
                "status": "VERIFIED_EXACT",
            }
            if "page_sequence" in equation:
                verified_equation["page_sequence"] = equation_page_sequence
            equations.append(verified_equation)
        source_period_status = _SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if source_period_status is None:
            raise _error("reviewed source period is not admitted by this profile")
        trial_status = _TRIAL_STATUS_BY_SOURCE_PERIOD_STATUS.get(source_period_status)
        if trial_status is None:
            raise _error("reviewed source-period trial status drifted")
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "owner": {
                    "fresh_vietocr_proposal": owner["vietocr_text"],
                    "line_index": reviewed["owner_line_index"],
                    "pixel_transcription": reviewed["owner_pixel_transcription"],
                },
                "page_sequence": page_sequence,
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": trial_status,
                "unit_authority": reviewed["unit_authority"],
                "verified_accounting_equations": equations,
                "verified_mappings": mapped_rows,
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
                "whole_document_family_absence_claim": False,
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
        "state": _RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": _RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_long_term_investments_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    persisted = _validate_result(value)
    scan = scanner.build_long_term_investments_full_document_scan_v1(semantic_index)
    expected = build_long_term_investments_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("long-term-investment mapping does not replay exactly")
    return persisted


def build_live_long_term_investments_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH, REVIEW_SHA256 or None)
    scan = scanner.build_long_term_investments_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_long_term_investments_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return validate_long_term_investments_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_long_term_investments_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH, REVIEW_SHA256 or None)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_long_term_investments_8bank_codex_verified_mapping_replay_v1(
        value,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.write_review:
        output = REVIEW_PATH if args.output is None else args.output
        output.write_bytes(canonical_json_bytes_v1(_review_blueprint()))
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        sys.stdout.write(
            validate_live_long_term_investments_8bank_codex_verified_mapping_v1(value)["result_id"]
            + "\n"
        )
        return
    result = build_live_long_term_investments_8bank_codex_verified_mapping_v1()
    output = RESULT_PATH if args.output is None else args.output
    output.write_bytes(canonical_json_bytes_v1(result))
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    _main()
