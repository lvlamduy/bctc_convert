"""Seal bounded absence of detailed subsidiary acquisition/disposal tables."""

from __future__ import annotations

import argparse
import importlib.util
import sys
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
RESULT_PATH = Path(
    "docs/experiments/E-0093-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
FORMAT_VERSION = "SUBSIDIARY_ACQUISITION_DISPOSAL_8BANK_BOUND_REPORT_ABSENCE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_SUPPLIED_PDFS_COMPLETE_FRESH_VIETOCR_BANK_BLIND_"
    "SUBSIDIARY_ACQUISITION_DISPOSAL_THREE_REQUIRED_DETAIL_ROWS_AND_LIVE_TM_"
    "SCHEMA_1255_TO_1258_ONLY_NO_BROAD_CORPUS_NUMERIC_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "absence_claim_bounded_to_supplied_pdf": True,
    "acquisition_or_disposal_history_absence_claim": False,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_other_report_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "cash_flow_caption_or_accounting_policy_promoted": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_schema_1255_to_1258_mapping_emitted": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
}
_SCHEMA_EXPECTED = {
    1255: ("Mua mới và thanh lý các công ty con", 1247, 831),
    1256: ("Tổng giá trị mua hoặc thanh lý", 1255, 832),
    1257: (
        "Phần giá trị mua hoặc thanh lý được thanh toán bằng tiền và các khoản tương đương tiền",
        1255,
        833,
    ),
    1258: (
        "Số tiền và các khoản tương đương tiền thực có trong công ty con hoặc đơn vị kinh doanh khác được mua hoặc thanh lý",
        1255,
        834,
    ),
}
_SOURCE_PERIOD = {
    **{code: ("2026-06-30", "VERIFIED_SOURCE_PERIOD_Q2_2026") for code in EXPECTED_DOCUMENT_ORDER},
    "VPB": ("2026-03-31", "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"),
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


class SubsidiaryAcquisitionDisposal8BankBoundReportAbsenceV1Error(ValueError):
    """The complete-PDF scan, schema or bounded absence drifted."""


def _error(
    message: str,
) -> SubsidiaryAcquisitionDisposal8BankBoundReportAbsenceV1Error:
    return SubsidiaryAcquisitionDisposal8BankBoundReportAbsenceV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load subsidiary-transaction support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _scanner() -> ModuleType:
    return _load(
        "subsidiary_transaction_scan_for_bound_absence",
        "scan_subsidiary_acquisition_disposal_full_document_vietocr_v1.py",
    )


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
        "first_display_order": 831,
        "items": items,
        "last_display_order": 834,
    }


def _near_controls(matcher_result: dict[str, Any]) -> list[dict[str, Any]]:
    controls = []
    for region in matcher_result["near_regions"]:
        anchor = region["anchor"]
        controls.append(
            {
                "observed_roles": list(region["layout"]["observed_roles"]),
                "page_sequence": anchor["page_sequence"],
                "source_line_index": anchor["source_line_index"],
                "vietocr_transformer_proposal": anchor["vietocr_text"],
            }
        )
    return controls


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "bound_report_detailed_note_absence_count": sum(
            trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "mapping_verified_count": sum(len(trial["mappings"]) for trial in trials),
        "near_control_count": sum(len(trial["near_controls"]) for trial in trials),
        "open_review_item_count": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("subsidiary-transaction absence result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "SUBSIDIARY_TRANSACTION_8BANK_BOUND_REPORT_ABSENCE_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(value["schema_family"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("subsidiary-transaction absence identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial)
            != {
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
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["disposition"] != "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
            or trial["mappings"] != []
            or type(trial["near_controls"]) is not list
        ):
            raise _error("subsidiary-transaction absence trial drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("subsidiary-transaction absence metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0093:result:" + canonical_json_sha256_v1(material):
        raise _error("subsidiary-transaction absence result ID drifted")
    return canonical_clone_v1(value)


def build_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(
    semantic_index: Any,
) -> dict[str, Any]:
    scanner = _scanner()
    scan = scanner.build_subsidiary_acquisition_disposal_full_document_scan_v1(semantic_index)
    if scan["metrics"]["complete_region_count"] != 0:
        raise _error("complete subsidiary-transaction detail exists; absence cannot be sealed")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scan_by_code = {trial["document_provenance"]: trial for trial in scan["trials"]}
    trials = []
    for document in axis["documents"]:
        code = document["document_provenance"]
        scan_trial = scan_by_code[code]
        source_period, period_status = _SOURCE_PERIOD[code]
        trials.append(
            {
                "disposition": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                "document_ordinal": document["document_ordinal"],
                "document_provenance": code,
                "mappings": [],
                "near_controls": _near_controls(scan_trial["matcher_result"]),
                "source_pdf_sha256": document["source_pdf"]["sha256"],
                "source_period": source_period,
                "source_period_status": period_status,
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
            "structure_scan_id": scan["scan_id"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": "SUBSIDIARY_TRANSACTION_8BANK_BOUND_REPORT_ABSENCE_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0093:result:" + canonical_json_sha256_v1(material)}
    )


def validate_subsidiary_acquisition_disposal_8bank_bound_report_absence_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("subsidiary-transaction absence result does not replay exactly")
    return supplied


def _live_index() -> Any:
    support = _scanner()._support()._support()
    return support._strict_json(
        support._stable_bytes(SEMANTIC_INDEX_PATH), SEMANTIC_INDEX_PATH.as_posix()
    )


def build_live_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1() -> dict[str, Any]:
    return build_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(_live_index())


def validate_live_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_subsidiary_acquisition_disposal_8bank_bound_report_absence_replay_v1(
        value, _live_index()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_result:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(
            canonical_json_bytes_v1(
                build_live_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1()
            )
        )
    if args.validate_result:
        support = _scanner()._support()._support()
        value = support._strict_json(support._stable_bytes(RESULT_PATH), RESULT_PATH.as_posix())
        validate_live_subsidiary_acquisition_disposal_8bank_bound_report_absence_v1(value)


if __name__ == "__main__":
    main()
