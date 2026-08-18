"""Verify assets pledged or discounted by the bank across eight reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

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


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bank-pledged-assets support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_bank_pledged_assets",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "bank_pledged_assets_scan_for_verified_mapping",
    "scan_bank_pledged_assets_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "BANK_PLEDGED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "BANK_PLEDGED_ASSETS_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "BANK_PLEDGED_ASSETS_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0097:result:"
REVIEW_STATE = "BANK_PLEDGED_ASSETS_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0097:pixel-review:"
FAMILY_END_DISPLAY_ORDER = 869
FAMILY_CHILD_TOTAL_EQUATION_NAME = "PLEDGED_PLUS_DISCOUNTED_VALUABLE_PAPERS_EQUAL_PARENT"
SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}
EXPECTED_RESULT_ID: str | None = (
    "e0097:result:01f38f70ea232def0a49e001aedf287a412bb312961e9843ebefc726e8dcf53d"
)
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT = True
_HISTORICAL_STRUCTURE_GRAPH_ID_BY_CODE = {
    "ACB": "bpavgv1:graph:c58f608070da6ad3fadda5da736e31801bb8b04611baea3edb0d61e88c0154e9",
    "MBB": "bpavgv1:graph:c58f608070da6ad3fadda5da736e31801bb8b04611baea3edb0d61e88c0154e9",
    "VPB": "bpavgv1:graph:343f3bc174bd36b00b1eacddde5b9ffcdfb6adf22d21205d52d6a1f29d3339ae",
    "HDB": "bpavgv1:graph:c58f608070da6ad3fadda5da736e31801bb8b04611baea3edb0d61e88c0154e9",
    "VCB": "bpavgv1:graph:c58f608070da6ad3fadda5da736e31801bb8b04611baea3edb0d61e88c0154e9",
    "CTG": "bpavgv1:graph:c58f608070da6ad3fadda5da736e31801bb8b04611baea3edb0d61e88c0154e9",
    "BID": "bpavgv1:graph:c58f608070da6ad3fadda5da736e31801bb8b04611baea3edb0d61e88c0154e9",
    "VIB": "bpavgv1:graph:7f340e858608c03cc947a93df19d877cf798a68c03d04bc21349692aa0f48575",
}
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_BANK_PLEDGED_"
    "ASSETS_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_CHALLENGER_EXPLICIT_DUPLICATED_"
    "SOURCE_HIERARCHY_FALSIFIER_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0097-bank-pledged-assets-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "bpafdsv1:scan:4cb6191dc211a0b4b141b9ee2aa17bf194e7cb3a98f561654ed9970520ec0474"

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 835),
    1289: (
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        1259,
        865,
    ),
    1290: ("Chứng khoán kinh doanh", 1289, 866),
    1291: ("Chứng khoán đầu tư", 1289, 867),
    1292: ("Tài sản cố định", 1289, 868),
    1293: ("Tài sản khác", 1289, 869),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_bank_pledged_asset_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_printed_double_count_relabelled_as_accounting_identity": False,
    "source_printed_hierarchy_contradiction_retained": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}
_FIELDS = {
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


class BankPledgedAssets8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, values, axes, schema or result drifted."""


def _error(message: str) -> BankPledgedAssets8BankCodexVerifiedMappingV1Error:
    return BankPledgedAssets8BankCodexVerifiedMappingV1Error(message)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != expected[2])
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": expected[2],
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _sum_ref(page: int, components: Sequence[tuple[int, str]]) -> dict[str, Any]:
    return {
        "components": [_line(page, line, text) for line, text in components],
        "kind": "AUTHENTICATED_CONTROLLED_SUM",
        "page_sequence": page,
    }


def _values(
    page: int,
    current: Mapping[str, Any] | tuple[int, str],
    comparative: Mapping[str, Any] | tuple[int, str],
) -> list[dict[str, Any]]:
    def normalized(item: Mapping[str, Any] | tuple[int, str]) -> dict[str, Any]:
        return canonical_clone_v1(item) if type(item) is dict else _line(page, *item)

    return [
        {"axis_role": "CURRENT", **normalized(current)},
        {"axis_role": "COMPARATIVE", **normalized(comparative)},
    ]


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Mapping[str, Any] | tuple[int, str],
    comparative: Mapping[str, Any] | tuple[int, str],
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": "BANK_OWN_ASSET_ROW_WITH_TWO_PERIOD_AXES",
        "values": _values(page, current, comparative),
    }


def _source_row(
    row_id: str,
    page: int,
    label: tuple[int, str],
    current: tuple[int, str],
    comparative: tuple[int, str],
    reason: str,
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, *label)],
        "reason": reason,
        "row_id": row_id,
        "values": _values(page, current, comparative),
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No bank-own-assets pledged/collateralized/discounted table with at least two "
                "source use or accounting-class rows, two periods and unit was found; customer "
                "collateral, borrowing facilities and policy text do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _absence("ACB"),
        _absence("MBB"),
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1289,
                    67,
                    [
                        (
                            43,
                            "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
                        )
                    ],
                    (73, "28.204.745"),
                    (74, "26.450.750"),
                ),
                _mapping(
                    "TRADING_SECURITIES",
                    1290,
                    67,
                    [
                        (58, "- Giấy tờ có giá thuộc chứng khoán kinh doanh"),
                        (59, "(Thuyết minh số 8.1)"),
                    ],
                    (60, "2.400.000"),
                    (61, "4.350.000"),
                ),
                _mapping(
                    "INVESTMENT_SECURITIES",
                    1291,
                    67,
                    [
                        (62, "- Giấy tờ có giá thuộc chứng khoán đầu tư"),
                        (63, "(Thuyết minh số 13.1)"),
                        (66, "Giấy tờ có giá bán và cam kết mua lại"),
                        (67, "(Thuyết minh số 13.1)"),
                    ],
                    _sum_ref(67, [(64, "5.518.000"), (68, "5.000.000")]),
                    _sum_ref(67, [(65, "2.391.000"), (69, "6.000.000")]),
                ),
                _mapping(
                    "OTHER_ASSETS",
                    1293,
                    67,
                    [(70, "Tài sản khác đưa đi thế chấp, cầm cố")],
                    (71, "7.368.745"),
                    (72, "6.968.750"),
                ),
            ],
            "owner": [
                _ref(
                    67,
                    43,
                    "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
                ),
                _ref(
                    67,
                    44,
                    "Chi tiết các tài sản, giấy tờ có giá của Ngân hàng được đưa đi thế chấp, cầm cố, chiết khấu, tái",
                ),
                _ref(
                    67,
                    45,
                    "chiết khấu tại các TCTD khác và thiết lập hạn mức tại Ngân hàng Nhà nước vào thời điểm cuối kỳ",
                ),
            ],
            "page_span": [67, 67],
            "source_only_rows": [
                _source_row(
                    "BPA-001",
                    67,
                    (54, "Giấy tờ có giá đưa đi thế chấp, cầm cố"),
                    (55, "7.918.000"),
                    (56, "6.741.000"),
                    "SOURCE_COMBINED_PARENT_EQUALS_ITS_TRADING_AND_INVESTMENT_PLEDGED_CHILDREN_BUT_IS_ADDED_AGAIN_IN_PRINTED_TOTAL",
                ),
            ],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(67, 52, "Triệu đồng"), _ref(67, 53, "Triệu đồng")],
        },
        _absence("HDB"),
        _absence("VCB"),
        _absence("CTG"),
        _absence("BID"),
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1289,
                    49,
                    [
                        (
                            75,
                            "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu bởi Ngân hàng",
                        )
                    ],
                    (86, "34.512.402"),
                    (87, "29.745.000"),
                ),
            ],
            "owner": [
                _ref(
                    49,
                    75,
                    "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu bởi Ngân hàng",
                ),
            ],
            "page_span": [49, 49],
            "source_only_rows": [
                _source_row(
                    "BPA-002",
                    49,
                    (80, "Giấy tờ có giá đưa đi thế chấp, cầm cố"),
                    (81, "3.274.600"),
                    (82, "10.587.000"),
                    "GENERIC_VALUABLE_PAPERS_NOT_SPLIT_BETWEEN_TRADING_AND_INVESTMENT_SCHEMA_LEAVES",
                ),
                _source_row(
                    "BPA-003",
                    49,
                    (83, "Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu"),
                    (84, "31.237.802"),
                    (85, "19.158.000"),
                    "GENERIC_VALUABLE_PAPERS_NOT_SPLIT_BETWEEN_TRADING_AND_INVESTMENT_SCHEMA_LEAVES",
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(49, 78, "triệu đồng"), _ref(49, 79, "triệu đồng")],
        },
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": REVIEW_STATE,
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("bank-pledged-assets pixel review drifted")
    return canonical_clone_v1(value)


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "bound_report_detailed_note_absence_count": sum(
            t["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(t["page_span"] is not None for t in trials),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "source_hierarchy_double_count_contradiction_document_count": sum(
            t["source_hierarchy_status"]
            == "SOURCE_PRINTED_TOTAL_DOUBLE_COUNTS_COMBINED_PARENT_AND_IN_THAT_CHILDREN"
            for t in trials
        ),
        "source_presentation_reconciliation_count": sum(
            len(t["verified_source_presentation_reconciliations"]) for t in trials
        ),
        "verified_value_cell_count": sum(
            len(m["values"]) for t in trials for m in t["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("bank-pledged-assets result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("bank-pledged-assets result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material) or (
        EXPECTED_RESULT_ID is not None and identity != EXPECTED_RESULT_ID
    ):
        raise _error("bank-pledged-assets result ID drifted")
    return canonical_clone_v1(value)


def _value(row: Mapping[str, Any], axis_role: str) -> int:
    return next(
        item["normalized_value"] for item in row["values"] if item["axis_role"] == axis_role
    )


def build_bank_pledged_assets_8bank_codex_verified_mapping_v1(
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
    scanner.validate_bank_pledged_assets_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256 or (
        not ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT
        and structure_scan["scan_id"] != EXPECTED_SCAN_ID
    ):
        raise _error("bank-pledged-assets fixed inputs drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = other._document(reviewed_documents, code, "pixel review")
        scan_trial = other._document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "structure_graph_id": (
                _HISTORICAL_STRUCTURE_GRAPH_ID_BY_CODE[code]
                if ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT
                else matcher["result_id"]
            ),
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["regions"]:
                raise _error("absent bank-pledged-assets note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "source_hierarchy_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "status": "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                    "verified_source_presentation_reconciliations": [],
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed bank-pledged-assets region is not unique")
        axis_document = other._document(axis["documents"], code, "accounting axis")
        semantic_document = other._document(semantic_index["documents"], code, "semantic index")
        crop_document = other._document(crop_manifest["documents"], code, "crop manifest")

        def verified_values(
            items: Sequence[Mapping[str, Any]],
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "axis_role": item["axis_role"],
                    **other._verified_value(axis_document, semantic_document, crop_document, item),
                }
                for item in items
            ]

        mappings = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]), mapping["report_norm_id"]
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": verified_values(mapping["values"]),
            }
            for mapping in reviewed["mappings"]
        ]
        source_only = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in row["labels"]
                ],
                "reason": row["reason"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_OR_SOURCE_HIERARCHY_ROW_RETAINED",
                "values": verified_values(row["values"]),
            }
            for row in reviewed["source_only_rows"]
        ]
        by_role = {item["role"]: item for item in mappings}
        by_row = {item["row_id"]: item for item in source_only}
        equations = []
        reconciliations = []
        hierarchy_status = "SOURCE_HIERARCHY_ACCOUNTING_CONSISTENT"
        has_combined_parent_contradiction = "BPA-001" in by_row and {
            "FAMILY_TOTAL",
            "TRADING_SECURITIES",
            "INVESTMENT_SECURITIES",
            "OTHER_ASSETS",
        }.issubset(by_role)
        if has_combined_parent_contradiction:
            investment = by_role["INVESTMENT_SECURITIES"]
            trading = by_role["TRADING_SECURITIES"]
            combined_parent = by_row["BPA-001"]
            other_assets = by_role["OTHER_ASSETS"]
            total = by_role["FAMILY_TOTAL"]
            for axis_role in ("CURRENT", "COMPARATIVE"):
                investment_components = next(
                    item["component_evidence"]
                    for item in investment["values"]
                    if item["axis_role"] == axis_role
                )
                pledged_investment = investment_components[0]["normalized_value"]
                repo_investment = investment_components[1]["normalized_value"]
                if pledged_investment + repo_investment != _value(investment, axis_role):
                    raise _error("investment controlled sum does not close")
                equations.append(
                    {
                        "computed_value": pledged_investment + repo_investment,
                        "name": "PLEDGED_INVESTMENT_PLUS_REPO_INVESTMENT_EQUALS_INVESTMENT_SECURITIES",
                        "period_axis": axis_role,
                        "status": "VERIFIED_EXACT",
                        "visible_value": _value(investment, axis_role),
                    }
                )
                if _value(trading, axis_role) + pledged_investment != _value(
                    combined_parent, axis_role
                ):
                    raise _error("combined valuable-paper parent does not close")
                equations.append(
                    {
                        "computed_value": _value(trading, axis_role) + pledged_investment,
                        "name": "TRADING_PLUS_PLEDGED_INVESTMENT_EQUALS_COMBINED_PLEDGED_PAPERS_PARENT",
                        "period_axis": axis_role,
                        "status": "VERIFIED_EXACT",
                        "visible_value": _value(combined_parent, axis_role),
                    }
                )
                printed_reconciliation = (
                    _value(combined_parent, axis_role)
                    + _value(trading, axis_role)
                    + pledged_investment
                    + repo_investment
                    + _value(other_assets, axis_role)
                )
                if printed_reconciliation != _value(total, axis_role):
                    raise _error("printed source total cannot be reproduced")
                reconciliations.append(
                    {
                        "computed_value": printed_reconciliation,
                        "hierarchy_double_count_detected": True,
                        "name": "PRINTED_TOTAL_INCLUDES_COMBINED_PARENT_AND_ITS_IN_THAT_CHILDREN",
                        "period_axis": axis_role,
                        "status": "SOURCE_PRESENTATION_REPRODUCED_NOT_ACCOUNTING_IDENTITY",
                        "visible_value": _value(total, axis_role),
                    }
                )
            hierarchy_status = (
                "SOURCE_PRINTED_TOTAL_DOUBLE_COUNTS_COMBINED_PARENT_AND_IN_THAT_CHILDREN"
            )
        else:
            total = by_role["FAMILY_TOTAL"]
            components = [
                row for role, row in by_role.items() if role != "FAMILY_TOTAL"
            ] + source_only
            if not components:
                raise _error("bank-pledged-assets family has no verified child rows")
            for axis_role in ("CURRENT", "COMPARATIVE"):
                computed = sum(_value(row, axis_role) for row in components)
                if computed != _value(total, axis_role):
                    raise _error("bank-pledged-assets child total does not close")
                equations.append(
                    {
                        "computed_value": computed,
                        "name": FAMILY_CHILD_TOTAL_EQUATION_NAME,
                        "period_axis": axis_role,
                        "status": "VERIFIED_EXACT",
                        "visible_value": _value(total, axis_role),
                    }
                )
        period_status = SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if period_status is None:
            raise _error("bank-pledged-assets source period is not configured")
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(
                    item["schema_binding"]["report_norm_id"] for item in mappings
                ),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "source_hierarchy_status": hierarchy_status,
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SOURCE_HIERARCHY_CONTRADICTION_AND_UNRESOLVED_ROW"
                    if has_combined_parent_contradiction
                    else "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SOURCE_ROWS"
                    if source_only
                    else "VERIFIED_BY_CODEX"
                ),
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
                "verified_source_presentation_reconciliations": reconciliations,
            }
        )
    mapped_union = sorted(
        {
            item["schema_binding"]["report_norm_id"]
            for trial in trials
            for item in trial["verified_mappings"]
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
            "pixel_review": {
                "path": REVIEW_PATH.as_posix(),
                "sha256": review_sha256,
            },
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
            "family_end_display_order": FAMILY_END_DISPLAY_ORDER,
            "family_root": _schema_binding(schema_by_id.get(1289), 1289),
            "mapped_report_norm_ids": mapped_union,
            "section_root": _schema_binding(schema_by_id.get(1259), 1259),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    support = scanner._support()._support()
    raw = support._stable_bytes(path)
    return support._strict_json(raw, path.as_posix()), hashlib.sha256(raw).hexdigest()


def _live_inputs() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256 or crop_sha != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("bank-pledged-assets fixed input hash drifted")
    scan = scanner.build_bank_pledged_assets_full_document_scan_v1(semantic_index)
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, (name, parent, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != display_order)
            or item.statement_type != "TM"
        ):
            raise _error(f"bank-pledged-assets live schema drifted: {report_norm_id}")
    if ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT:
        persisted_result, _ = _stable_json(RESULT_PATH)
        persisted_result = _validate_result(persisted_result)
        authority = canonical_clone_v1(persisted_result["input_refs"]["schema_authority"])
        if ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT:
            for code in EXPECTED_DOCUMENT_ORDER:
                scan_trial = other._document(scan["trials"], code, "current structure scan")
                persisted_trial = other._document(
                    persisted_result["trials"], code, "persisted historical result"
                )
                matcher = scan_trial["matcher_result"]
                expected_span = persisted_trial["page_span"]
                actual_span = matcher["regions"][0]["page_span"] if matcher["regions"] else None
                if not same_typed_json_v1(
                    matcher["uniqueness"], persisted_trial["whole_document_uniqueness"]
                ) or not same_typed_json_v1(actual_span, expected_span):
                    raise _error("historical bank-pledged-assets structural disposition drifted")
                if persisted_trial["structure_graph_id"] != (
                    _HISTORICAL_STRUCTURE_GRAPH_ID_BY_CODE.get(code)
                ):
                    raise _error("historical bank-pledged-assets graph identity drifted")
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": authority,
        "schema_by_id": by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_bank_pledged_assets_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_bank_pledged_assets_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_bank_pledged_assets_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_bank_pledged_assets_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("bank-pledged-assets result does not replay exactly")
    return supplied


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
        _write(RESULT_PATH, build_live_bank_pledged_assets_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_bank_pledged_assets_8bank_codex_verified_mapping_v1(value)


if __name__ == "__main__":
    main()
