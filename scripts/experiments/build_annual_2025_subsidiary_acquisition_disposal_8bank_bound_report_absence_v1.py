"""Seal bounded annual-2025 absence of subsidiary transaction detail tables."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_PATH = Path(
    "docs/experiments/E-0148-annual-2025-subsidiary-acquisition-disposal-"
    "8bank-bound-report-absence-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "sadfdsv1:scan:57b71c38a5d5f014e700bc0cbce1038e03c952d4e58a7465a27cdd31a8b1f456"
EXPECTED_RESULT_ID: str | None = (
    "annual2025sad8bcv1:result:fc2d5c340cb2fe6b467dcf78d16f2300b7b312046524cc1b4399be7c45cbb03d"
)

FORMAT_VERSION = "ANNUAL_2025_SUBSIDIARY_ACQUISITION_DISPOSAL_8BANK_BOUND_REPORT_ABSENCE_V1"
STATE = "ANNUAL_2025_SUBSIDIARY_TRANSACTION_BOUND_REPORT_ABSENCE_COMPLETE"
RESULT_ID_PREFIX = "annual2025sad8bcv1:result:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_SUBSIDIARY_ACQUISITION_DISPOSAL_THREE_REQUIRED_"
    "DETAIL_ROWS_AND_LIVE_TM_SCHEMA_1255_TO_1258_ONLY_NO_OTHER_PERIOD_"
    "CORPUS_NUMERIC_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "absence_claim_bounded_to_exact_annual_2025_reports": True,
    "acquisition_or_disposal_history_absence_claim": False,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_period_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "cash_flow_caption_or_accounting_policy_promoted": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_schema_1255_to_1258_mapping_emitted": False,
    "fresh_vietocr_transformer_text_required": True,
    "live_tm_schema_checked": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
}
_SCHEMA_EXPECTED = {
    1255: ("Mua mới và thanh lý các công ty con", 1247, 835),
    1256: ("Tổng giá trị mua hoặc thanh lý", 1255, 836),
    1257: (
        "Phần giá trị mua hoặc thanh lý được thanh toán bằng tiền và các khoản tương đương tiền",
        1255,
        837,
    ),
    1258: (
        "Số tiền và các khoản tương đương tiền thực có trong công ty con hoặc đơn vị kinh doanh khác được mua hoặc thanh lý",
        1255,
        838,
    ),
}
_PAGE_COUNTS = dict(zip(EXPECTED_DOCUMENT_ORDER, (100, 103, 100, 71, 84, 85, 74, 78), strict=True))
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
_TRIAL_FIELDS = {
    "complete_pdf_page_count",
    "disposition",
    "document_ordinal",
    "document_provenance",
    "mappings",
    "near_controls",
    "source_pdf_sha256",
    "source_period",
    "source_period_status",
    "structure_graph_id",
    "whole_document_scan_metrics",
}


class Annual2025SubsidiaryAcquisitionDisposalAbsenceV1Error(ValueError):
    """The annual input, graph, schema or bounded absence drifted."""


def _error(message: str) -> Annual2025SubsidiaryAcquisitionDisposalAbsenceV1Error:
    return Annual2025SubsidiaryAcquisitionDisposalAbsenceV1Error(message)


def _scanner() -> ModuleType:
    name = "annual_2025_subsidiary_acquisition_disposal_scan"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name(
        "scan_subsidiary_acquisition_disposal_full_document_vietocr_v1.py"
    )
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load subsidiary-transaction scanner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stable_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    support = _scanner()._support()._support()
    payload = support._stable_bytes(path)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed annual semantic index drifted: {path}")
    value = support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error("annual semantic index must be one JSON object")
    return value


def _near_controls(matcher_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "observed_roles": list(region["layout"]["observed_roles"]),
            "page_sequence": region["anchor"]["page_sequence"],
            "source_line_index": region["anchor"]["source_line_index"],
            "vietocr_transformer_proposal": region["anchor"]["vietocr_text"],
        }
        for region in matcher_result["near_regions"]
    ]


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "bound_report_detailed_note_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "complete_region_count": sum(
            trial["whole_document_scan_metrics"]["complete_region_count"] for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": sum(len(trial["mappings"]) for trial in trials),
        "near_control_count": sum(len(trial["near_controls"]) for trial in trials),
        "open_review_item_count": 0,
        "page_count": sum(trial["complete_pdf_page_count"] for trial in trials),
    }


def _schema_family() -> tuple[dict[str, Any], dict[str, Any]]:
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    items = []
    for report_norm_id, (name, parent_id, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent_id
            or item.display_order != display_order
            or item.statement_type != "TM"
        ):
            raise _error(f"live subsidiary-transaction schema drifted: {report_norm_id}")
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
    return authority, {
        "family_root_report_norm_id": 1255,
        "first_display_order": 835,
        "items": items,
        "last_display_order": 838,
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual subsidiary-transaction result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual subsidiary-transaction result identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["complete_pdf_page_count"] != _PAGE_COUNTS[code]
            or trial["disposition"] != "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            or trial["mappings"] != []
            or type(trial["near_controls"]) is not list
            or trial["source_period"] != "2025-12-31"
            or trial["source_period_status"] != "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025"
            or trial["whole_document_scan_metrics"]["complete_region_count"] != 0
        ):
            raise _error("annual subsidiary-transaction trial drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material) or (
        EXPECTED_RESULT_ID is not None and identity != EXPECTED_RESULT_ID
    ):
        raise _error("annual subsidiary-transaction result ID drifted")
    return canonical_clone_v1(value)


def build_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(
    semantic_index: Any,
) -> dict[str, Any]:
    scanner = _scanner()
    scan = scanner.build_subsidiary_acquisition_disposal_full_document_scan_v1(semantic_index)
    if scan["scan_id"] != EXPECTED_SCAN_ID or scan["metrics"] != {
        "bounded_detailed_note_absence_count": 8,
        "complete_region_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 0,
        "mapping_verified_count": 0,
        "near_region_count": 25,
    }:
        raise _error("annual subsidiary-transaction complete-PDF scan drifted")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual subsidiary-transaction semantic axis drifted")
    scan_by_code = {trial["document_provenance"]: trial for trial in scan["trials"]}
    trials = []
    for document in axis["documents"]:
        code = document["document_provenance"]
        scan_trial = scan_by_code[code]
        if len(document["pages"]) != _PAGE_COUNTS[code]:
            raise _error("annual subsidiary-transaction page denominator drifted")
        trials.append(
            {
                "complete_pdf_page_count": len(document["pages"]),
                "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                "document_ordinal": document["document_ordinal"],
                "document_provenance": code,
                "mappings": [],
                "near_controls": _near_controls(scan_trial["matcher_result"]),
                "source_pdf_sha256": document["source_pdf"]["sha256"],
                "source_period": "2025-12-31",
                "source_period_status": "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025",
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
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": scan["scan_id"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": STATE,
        "trials": trials,
    }
    return _validate(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def build_live_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1() -> dict[
    str, Any
]:
    return build_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(
        _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    )


def validate_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_live_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual subsidiary-transaction absence does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write_result == args.verify:
        parser.error("choose exactly one action")
    if args.write_result:
        result = (
            build_live_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1()
        )
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    support = _scanner()._support()._support()
    value = support._strict_json(support._stable_bytes(RESULT_PATH), RESULT_PATH.as_posix())
    verified = (
        validate_annual_2025_subsidiary_acquisition_disposal_8bank_bound_report_absence_replay_v1(
            value
        )
    )
    print(verified["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
