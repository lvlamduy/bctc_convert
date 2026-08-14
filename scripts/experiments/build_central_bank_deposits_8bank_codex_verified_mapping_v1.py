"""Verify and map the eight-bank deposits-at-central-banks family."""

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
    match_vietnamese_anchor_alias_v1,
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
    "CentralBankDeposits8BankCodexVerifiedMappingV1Error",
    "build_central_bank_deposits_8bank_codex_verified_mapping_v1",
    "build_live_central_bank_deposits_8bank_codex_verified_mapping_v1",
    "validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1",
    "validate_live_central_bank_deposits_8bank_codex_verified_mapping_v1",
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
    "trading_securities_verified_mapping_support_for_central_bank_deposits",
    "build_trading_securities_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_experiment_module(
    "central_bank_deposits_full_document_scan_for_verified_mapping",
    "scan_central_bank_deposits_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_SHARED_VARIANT_ENGINE_"
    "CENTRAL_BANK_DEPOSIT_FIRST_LAST_CLUSTER_BOUNDARY_PERIOD_UNIT_STRUCTURE_"
    "VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_LIVE_TM_SCHEMA_ONLY_"
    "NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0061-central-bank-deposits-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0061-central-bank-deposits-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "cbdfdsv1:scan:46a3c2587d4802f3725bd7d004e6d264a5f14158dd5a4e66f0d284688c6d86d1"

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "DETAILED_NOTE_NOT_BALANCE_SHEET_RESERVE_RATIO_RISK_OR_LIQUIDITY_SURFACE",
    "FIRST_OWNER_AND_LAST_TOTAL_IN_PDF_ORDER",
    "OUTER_OWNER_PRECEDES_CENTRAL_BANK_PARENT_AND_REQUIRED_CHILDREN",
    "FAMILY_LEVEL_CHILD_ORDER_VARIANT_NOT_BANK_ROUTING",
    "CURRENT_PERIOD_MONETARY_AXIS_ONLY",
    "PERIOD_AND_UNIT_AXES_VISIBLE",
    "VISIBLE_PIXEL_LABELS_DIGITS_AND_SIGN",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "CURRENCY_SUBTOTAL_AND_VISIBLE_TOTAL_ACCOUNTING",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
    "UNMAPPED_GEOGRAPHY_ROWS_NOT_SILENTLY_COERCED_TO_OTHER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "balance_sheet_reserve_ratio_risk_or_liquidity_surface_promoted": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": ("VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER_AND_ACCOUNTING"),
    "old_ocr_used_as_semantic_anchor": False,
    "source_order_and_cluster_boundaries_required": True,
    "unlabeled_total_requires_topology_and_accounting": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_central_bank_deposit_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reserve_ratio_auxiliary_table_used_as_balance_mapping": False,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_geography_rows_promoted_to_other": False,
    "unlabeled_total_requires_topology_and_exact_equation": True,
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
_MAPPING_SCHEMA = {
    "CENTRAL_BANK_VIETNAM_PARENT": 570,
    "DEPOSIT_FOREIGN_CURRENCY": 572,
    "DEPOSIT_VND": 571,
    "TOTAL": 569,
}


class CentralBankDeposits8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel ledger, accounting, or live schema drifted."""


def _error(message: str) -> CentralBankDeposits8BankCodexVerifiedMappingV1Error:
    return CentralBankDeposits8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _value(line_index: int, pixel_transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": pixel_transcription}


def _mapping(
    role: str,
    label_line_index: int | None,
    label_pixel_transcription: str | None,
    value_line_index: int,
    pixel_value: str,
    topology: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "report_norm_id": _MAPPING_SCHEMA[role],
        "role": role,
        "topology": topology,
        "value": _value(value_line_index, pixel_value),
    }


def _unmapped(
    role: str,
    label_line_index: int,
    label_pixel_transcription: str,
    value_line_index: int,
    pixel_value: str,
) -> dict[str, Any]:
    return {
        "label_line_index": label_line_index,
        "label_pixel_transcription": label_pixel_transcription,
        "reason": "NO_EXACT_LIVE_TM_SCHEMA_GEOGRAPHIC_CENTRAL_BANK_CHILD",
        "role": role,
        "value": _value(value_line_index, pixel_value),
    }


def _positive_document(
    bank_code: str,
    page_sequence: int,
    source_period: str,
    owner_line_index: int,
    owner_pixel_transcription: str,
    rows: Sequence[tuple[str, int | None, str | None, int, str, str]],
    equations: Sequence[tuple[str, Sequence[tuple[int, str]], tuple[int, str]]],
    unmapped_rows: Sequence[tuple[str, int, str, int, str]] = (),
) -> dict[str, Any]:
    disposition = (
        "VERIFIED_DETAILED_CENTRAL_BANK_DEPOSIT_NOTE_WITH_UNMAPPED_GEOGRAPHY_CHILDREN"
        if unmapped_rows
        else "VERIFIED_DETAILED_CENTRAL_BANK_DEPOSIT_NOTE"
    )
    return {
        "bank_code": bank_code,
        "checks": {check: "PASS" for check in _REVIEW_CHECKS},
        "disposition": disposition,
        "equations": [
            {
                "component_values": [_value(*item) for item in components],
                "name": name,
                "visible_total": _value(*total),
            }
            for name, components, total in equations
        ],
        "evidence_owner_line_index": owner_line_index,
        "mappings": [_mapping(*row) for row in rows],
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": page_sequence,
        "source_period": source_period,
        "unmapped_rows": [_unmapped(*row) for row in unmapped_rows],
    }


def _negative_document(
    bank_code: str,
    evidence_page_sequence: int,
    owner_line_index: int,
    owner_pixel_transcription: str,
) -> dict[str, Any]:
    checks = {check: "NOT_APPLICABLE" for check in _REVIEW_CHECKS}
    checks["COMPLETE_PDF_UNIQUE_REGION_ENUMERATION"] = "PASS_NO_COMPLETE_REGION"
    checks["DETAILED_NOTE_NOT_BALANCE_SHEET_RESERVE_RATIO_RISK_OR_LIQUIDITY_SURFACE"] = "PASS"
    return {
        "bank_code": bank_code,
        "checks": checks,
        "disposition": "UNRESOLVED_NO_COMPLETE_DETAILED_NOTE_CLUSTER_IN_BOUND_PDF",
        "equations": [],
        "evidence_owner_line_index": owner_line_index,
        "mappings": [],
        "owner_pixel_transcription": owner_pixel_transcription,
        "page_sequence": evidence_page_sequence,
        "source_period": "2026-06-30",
        "unmapped_rows": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _negative_document("ACB", 3, 17, "Tiền gửi tại Ngân hàng Nhà nước"),
        _positive_document(
            "MBB",
            30,
            "2026-06-30",
            20,
            "Tiền gửi tại NHNN",
            [
                (
                    "CENTRAL_BANK_VIETNAM_PARENT",
                    25,
                    "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                    26,
                    "25.269.011",
                    "OWNER_INTERMEDIATE_PARENT",
                ),
                ("DEPOSIT_VND", 28, "Bằng VND", 29, "20.274.233", "PARENT_CHILD"),
                (
                    "DEPOSIT_FOREIGN_CURRENCY",
                    31,
                    "Bằng ngoại tệ",
                    32,
                    "4.994.778",
                    "PARENT_CHILD",
                ),
                (
                    "TOTAL",
                    None,
                    None,
                    40,
                    "27.417.370",
                    "OUTER_OWNER_TO_UNLABELED_TRAILING_TOTAL",
                ),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_VIETNAM_SUBTOTAL",
                    ((29, "20.274.233"), (32, "4.994.778")),
                    (26, "25.269.011"),
                ),
                (
                    "VIETNAM_PLUS_LAOS_PLUS_CAMBODIA_TO_TOTAL",
                    ((26, "25.269.011"), (35, "934.855"), (38, "1.213.504")),
                    (40, "27.417.370"),
                ),
            ],
            (
                (
                    "CENTRAL_BANK_LAOS",
                    34,
                    "Tiền gửi tại Ngân hàng Nhà nước Lào",
                    35,
                    "934.855",
                ),
                (
                    "CENTRAL_BANK_CAMBODIA",
                    37,
                    "Tiền gửi tại Ngân hàng Quốc gia Campuchia",
                    38,
                    "1.213.504",
                ),
            ),
        ),
        _positive_document(
            "VPB",
            38,
            "2026-03-31",
            24,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                ("DEPOSIT_VND", 33, "Bằng VND", 34, "14.221.344", "PARENT_CHILD"),
                (
                    "DEPOSIT_FOREIGN_CURRENCY",
                    37,
                    "Bằng ngoại tệ",
                    38,
                    "595.985",
                    "PARENT_CHILD",
                ),
                (
                    "TOTAL",
                    None,
                    None,
                    40,
                    "14.817.329",
                    "OUTER_OWNER_TO_UNLABELED_TRAILING_TOTAL",
                ),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((34, "14.221.344"), (38, "595.985")),
                    (40, "14.817.329"),
                )
            ],
        ),
        _negative_document("HDB", 3, 21, 'Tiền gửi tại Ngân hàng Nhà nước ("NHNN")'),
        _negative_document("VCB", 7, 22, "Tiền gửi tại Ngân hàng Nhà nước"),
        _negative_document("CTG", 3, 24, "Tiền gửi tại NHNN"),
        _negative_document("BID", 4, 21, "Tiền gửi tại Ngân hàng Trung ương"),
        _positive_document(
            "VIB",
            31,
            "2026-06-30",
            22,
            "TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
            [
                ("DEPOSIT_VND", 28, "Bằng VND", 29, "3.988.246", "PARENT_CHILD"),
                (
                    "DEPOSIT_FOREIGN_CURRENCY",
                    31,
                    "Bằng ngoại tệ",
                    32,
                    "1.137.029",
                    "PARENT_CHILD",
                ),
                (
                    "TOTAL",
                    None,
                    None,
                    34,
                    "5.125.275",
                    "OUTER_OWNER_TO_UNLABELED_TRAILING_TOTAL",
                ),
            ],
            [
                (
                    "VND_PLUS_FOREIGN_TO_TOTAL",
                    ((29, "3.988.246"), (32, "1.137.029")),
                    (34, "5.125.275"),
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
            "review_run_id": "E-0061",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0061:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex central-bank deposit pixel review differs from fixed ledger")
    return canonical_clone_v1(expected)


def _document_by_code(documents: Any, code: str, label: str) -> dict[str, Any]:
    if type(documents) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in documents
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page_by_number(document: Mapping[str, Any], page_number: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict
        and page.get("physical_page", page.get("page_sequence")) == page_number
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain page {page_number}")
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


def _anchor_match(transformer_text: str, pixel_text: str, label: str) -> str:
    kind = match_vietnamese_anchor_alias_v1(transformer_text, [pixel_text])
    if kind is None:
        raise _error(f"visible {label} and fresh VietOCR disagree beyond one base character")
    return kind


def _schema_binding(item: Any, role: str) -> dict[str, Any]:
    schema_id = _MAPPING_SCHEMA.get(role)
    expected_parent = 560 if role == "TOTAL" else 569
    if (
        item is None
        or schema_id is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.parent_id != expected_parent
    ):
        raise _error("reviewed mapping does not bind one exact live central-bank TM item")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _region_event(region: Mapping[str, Any], role: str) -> dict[str, Any]:
    events = region.get("events")
    if type(events) is not list:
        raise _error("central-bank deposit graph event axis drifted")
    matches = [event for event in events if type(event) is dict and event.get("role") == role]
    if len(matches) != 1:
        raise _error(f"central-bank deposit graph does not contain one exact role {role}")
    return matches[0]


def _source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return support._source_value(axis_page, semantic_page, crop_page, source_texts, value)
    except Exception as exc:
        raise _error(f"central-bank deposit source numeric evidence drifted: {exc}") from exc


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "partial_mapping_document_count": sum(
            bool(trial["unmapped_source_rows"]) for trial in trials
        ),
        "q1_source_period_caveat_document_count": sum(
            trial.get("source_period_status") == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unmapped_source_row_count": sum(len(trial["unmapped_source_rows"]) for trial in trials),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("central-bank deposit mapping result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("central-bank deposit mapping result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "UNRESOLVED",
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT",
                "VERIFIED_BY_CODEX_WITH_UNMAPPED_SOURCE_ROWS",
            }
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("verified_accounting_equations")) is not list
            or type(trial.get("unmapped_source_rows")) is not list
        ):
            raise _error("central-bank deposit mapping trial shape drifted")
        for mapping in trial["verified_mappings"]:
            if type(mapping) is not dict or mapping.get("status") != "VERIFIED_BY_CODEX":
                raise _error("central-bank deposit mapped row status drifted")
        for unresolved in trial["unmapped_source_rows"]:
            if (
                type(unresolved) is not dict
                or unresolved.get("status") != "UNRESOLVED_SCHEMA_ITEM_ABSENT"
            ):
                raise _error("central-bank deposit unmapped source row status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cbd8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("central-bank deposit mapping result identity drifted")
    return canonical_clone_v1(value)


def build_central_bank_deposits_8bank_codex_verified_mapping_v1(
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
    """Build the exact eight-bank bounded central-bank deposit mapping result."""

    review = _review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state")
        != "FULL_DOCUMENT_CENTRAL_BANK_DEPOSIT_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("central-bank deposit input authority drifted")
    _sha256(crop_manifest_sha256, "crop manifest")
    _sha256(review_sha256, "pixel review")
    trials: list[dict[str, Any]] = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document_by_code(review["documents"], code, "pixel review")
        semantic_document = _document_by_code(
            semantic_index.get("documents"), code, "semantic index"
        )
        axis_document = _document_by_code(axis["documents"], code, "fresh VietOCR axis")
        crop_document = _document_by_code(crop_manifest.get("documents"), code, "crop manifest")
        scan_trial = _document_by_code(structure_scan.get("trials"), code, "structure scan")
        matcher = scan_trial.get("matcher_result")
        if scan_trial.get("document_ordinal") != ordinal or type(matcher) is not dict:
            raise _error("whole-PDF central-bank deposit scan identity drifted")
        page_number = reviewed["page_sequence"]
        axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
        owner_line = _axis_line(axis_page, reviewed["evidence_owner_line_index"])
        _anchor_match(owner_line["vietocr_text"], reviewed["owner_pixel_transcription"], "owner")
        if not reviewed["mappings"]:
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("regions") != []
                or reviewed["equations"]
                or reviewed["unmapped_rows"]
            ):
                raise _error("negative central-bank deposit disposition drifted")
            trials.append(
                {
                    "cluster_boundary": None,
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "disposition": reviewed["disposition"],
                    "evidence_page_sequence": page_number,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": reviewed["source_period"],
                    "status": "UNRESOLVED",
                    "unmapped_source_rows": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "whole_document_family_absence_claim": False,
                    "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
                }
            )
            continue
        if (
            matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or matcher.get("uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or type(matcher.get("regions")) is not list
            or len(matcher["regions"]) != 1
        ):
            raise _error("whole-PDF central-bank deposit region is not exactly unique")
        region = matcher["regions"][0]
        axes = region.get("layout", {}).get("meaningful_axes", {})
        if (
            region.get("page_sequence") != page_number
            or axes.get("unit_header_count", 0) < 1
            or axes.get("period_header_count", 0) < 2
            or region.get("owner", {}).get("source_line_index")
            != reviewed["evidence_owner_line_index"]
        ):
            raise _error("reviewed page/layout disagrees with generic central-bank graph")
        semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
        crop_page = _page_by_number(crop_document, page_number, "crop manifest")
        try:
            source_texts = support._source_line_axis(crop_page)
        except Exception as exc:
            raise _error(f"central-bank deposit source line axis drifted: {exc}") from exc
        mapped_rows = []
        for row in reviewed["mappings"]:
            role = row["role"]
            event = _region_event(region, role)
            label_index = row["label_line_index"]
            match_kind = None
            if role == "TOTAL":
                if label_index is not None or row["label_pixel_transcription"] is not None:
                    raise _error("unlabeled total acquired a fabricated label")
            else:
                if type(label_index) is not int or event.get("source_line_index") != label_index:
                    raise _error("central-bank graph/review label binding drifted")
                match_kind = _anchor_match(
                    _axis_line(axis_page, label_index)["vietocr_text"],
                    row["label_pixel_transcription"],
                    role,
                )
            value_index = row["value"]["line_index"]
            if value_index not in {
                item["source_line_index"] for item in event.get("value_proposals", [])
            }:
                raise _error("reviewed value is outside the graph-bound row")
            source_value = _source_value(
                axis_page, semantic_page, crop_page, source_texts, row["value"]
            )
            schema = _schema_binding(schema_by_id.get(row["report_norm_id"]), role)
            mapped_rows.append(
                {
                    **schema,
                    "anchor_match_kind": match_kind,
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "normalized_anchor": (
                        normalize_vietnamese_anchor_v1(
                            _axis_line(axis_page, label_index)["vietocr_text"]
                        )
                        if label_index is not None
                        else None
                    ),
                    "normalized_value": source_value["normalized_value"],
                    "physical_page": page_number,
                    "role": role,
                    "source_value": source_value,
                    "status": "VERIFIED_BY_CODEX",
                    "topology": row["topology"],
                    "vietocr_transformer_text": (
                        [_axis_line(axis_page, label_index)["vietocr_text"]]
                        if label_index is not None
                        else []
                    ),
                }
            )
        unmapped_rows = []
        for row in reviewed["unmapped_rows"]:
            event = _region_event(region, row["role"])
            if event.get("source_line_index") != row["label_line_index"]:
                raise _error("unmapped geography row left its graph event")
            match_kind = _anchor_match(
                _axis_line(axis_page, row["label_line_index"])["vietocr_text"],
                row["label_pixel_transcription"],
                row["role"],
            )
            if row["value"]["line_index"] not in {
                item["source_line_index"] for item in event.get("value_proposals", [])
            }:
                raise _error("unmapped geography value left its graph row")
            source_value = _source_value(
                axis_page, semantic_page, crop_page, source_texts, row["value"]
            )
            unmapped_rows.append(
                {
                    "anchor_match_kind": match_kind,
                    "candidate_schema_status": "NO_EXACT_LIVE_TM_SCHEMA_ITEM",
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "normalized_value": source_value["normalized_value"],
                    "physical_page": page_number,
                    "reason": row["reason"],
                    "role": row["role"],
                    "source_value": source_value,
                    "status": "UNRESOLVED_SCHEMA_ITEM_ABSENT",
                    "vietocr_transformer_text": [
                        _axis_line(axis_page, row["label_line_index"])["vietocr_text"]
                    ],
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            components = [
                _source_value(axis_page, semantic_page, crop_page, source_texts, item)
                for item in equation["component_values"]
            ]
            total = _source_value(
                axis_page, semantic_page, crop_page, source_texts, equation["visible_total"]
            )
            computed = sum(item["normalized_value"] for item in components)
            if computed != total["normalized_value"]:
                raise _error(f"central-bank deposit equation does not close: {code}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "physical_page": page_number,
                    "status": "CORROBORATED_EXACT",
                    "visible_total": total["normalized_value"],
                }
            )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        status = (
            "VERIFIED_BY_CODEX_WITH_UNMAPPED_SOURCE_ROWS"
            if unmapped_rows
            else (
                "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                else "VERIFIED_BY_CODEX"
            )
        )
        trials.append(
            {
                "cluster_boundary": canonical_clone_v1(region["cluster_boundary"]),
                "document_ordinal": ordinal,
                "document_provenance": code,
                "disposition": reviewed["disposition"],
                "evidence_page_sequence": page_number,
                "layout": canonical_clone_v1(region["layout"]),
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": status,
                "unmapped_source_rows": unmapped_rows,
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
        "state": "CENTRAL_BANK_DEPOSITS_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "cbd8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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
    """Exact-rebuild structure, numeric, accounting and schema decisions."""

    persisted = _validate_result(value)
    structure_scan = scanner.build_central_bank_deposits_full_document_scan_v1(semantic_index)
    expected = build_central_bank_deposits_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("central-bank deposit mapping does not replay exactly")
    return persisted


def build_live_central_bank_deposits_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Read only the fixed live inputs and build the verified result."""

    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256:
        raise _error("semantic index digest drifted")
    structure_scan = scanner.build_central_bank_deposits_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = build_central_bank_deposits_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )
    return validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
        result,
        semantic_index,
        crop_manifest,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
    )


def validate_live_central_bank_deposits_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    """Replay one persisted result only from the fixed live trust roots."""

    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review, review_sha = _stable_json(REVIEW_PATH)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
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
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review and args.validate is not None:
        parser.error("--write-review and --validate are mutually exclusive")
    if args.write_review:
        args.output.write_bytes(canonical_json_bytes_v1(_review_blueprint()))
        return
    if args.validate is not None:
        value, _ = _stable_json(args.validate)
        result = validate_live_central_bank_deposits_8bank_codex_verified_mapping_v1(value)
        sys.stdout.write(result["result_id"] + "\n")
        return
    result = build_live_central_bank_deposits_8bank_codex_verified_mapping_v1()
    args.output.write_bytes(canonical_json_bytes_v1(result))
    sys.stdout.write(result["result_id"] + "\n")


if __name__ == "__main__":
    _main()
