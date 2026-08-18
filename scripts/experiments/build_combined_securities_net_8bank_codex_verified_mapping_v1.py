"""Verify the optional combined trading/investment-securities net row."""

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


def _load_module(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


trading = _load_module(
    "trading_activity_support_for_combined_securities_net",
    "build_trading_securities_activity_8bank_codex_verified_mapping_v1.py",
)
investment = _load_module(
    "investment_activity_support_for_combined_securities_net",
    "build_investment_securities_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load_module(
    "combined_securities_net_scan_for_verified_mapping",
    "scan_combined_securities_net_full_document_vietocr_v1.py",
)
support = investment.support

FORMAT_VERSION = "COMBINED_SECURITIES_NET_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "COMBINED_SECURITIES_NET_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "COMBINED_SECURITIES_NET_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0086:result:"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0086:pixel-review:"
REVIEW_RUN_ID = "E-0086"
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
SCHEMA_FAMILY_END_DISPLAY_ORDER = 753
REQUIRE_COMPONENT_RESULTS = True
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_COMBINED_"
    "TRADING_AND_INVESTMENT_SECURITIES_NET_ROW_VISIBLE_PDF_LABEL_PADDLEOCR_"
    "SOURCE_NUMERIC_CHALLENGER_TWO_COMPONENT_ACCOUNTING_EQUATION_AND_LIVE_"
    "TM_SCHEMA_ONLY_NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0086-combined-securities-net-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0086-combined-securities-net-8bank-codex-verified-mapping-v1.json"
)
TRADING_RESULT_PATH = trading.RESULT_PATH
INVESTMENT_RESULT_PATH = investment.RESULT_PATH
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = investment.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = investment.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = investment.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = investment.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "csnfdsv1:scan:96f14b4858ea001d1768d5ca65c7137e05329c182c34075ad6f84f4de7fc07dc"
EXPECTED_TRADING_RESULT_ID = (
    "e0084:result:2c5a9db8db6a01d1098c3b54a940406d0206b4a16ae4733af521b378fe935f74"
)
EXPECTED_INVESTMENT_RESULT_ID = (
    "e0085:result:257898e302b323b14119a3178e0931417acce6629b6ba5391510ac9b4b45985d"
)
EXPECTED_RESULT_ID = "e0086:result:13afdff8c0629dec2f8094e0215a6005e37e6965bce7a8db5b31ee905a4c3724"

_SCHEMA_EXPECTED = (
    "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư",
    1142,
    753,
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_one_reviewed_combined_net_row": True,
    "paddleocr_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "section_heading_without_same_row_values_accepted": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "component_equation_checked_for_both_periods": True,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "paddleocr_source_axis_used_as_semantic_anchor": False,
    "section_heading_confused_with_numeric_total_row": False,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
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


class CombinedSecuritiesNet8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, components, equation, or TM schema drifted."""


def _error(message: str) -> CombinedSecuritiesNet8BankCodexVerifiedMappingV1Error:
    return CombinedSecuritiesNet8BankCodexVerifiedMappingV1Error(message)


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _review_documents() -> list[dict[str, Any]]:
    documents = []
    for code in EXPECTED_DOCUMENT_ORDER:
        if code == "MBB":
            documents.append(
                {
                    "absence_evidence": None,
                    "bank_code": code,
                    "label_lines": [
                        _ref(47, 67, "Lãi thuần từ chứng khoán kinh doanh, chứng"),
                        _ref(47, 68, "khoán đầu tư"),
                    ],
                    "page_span": [47, 47],
                    "period_axis": [
                        _ref(47, 31, "Từ 01/01/2026"),
                        _ref(47, 32, "Từ 01/01/2025"),
                        _ref(47, 33, "đến 30/06/2026"),
                        _ref(47, 34, "đến 30/06/2025"),
                    ],
                    "presentation": "WRAPPED_COMBINED_LABEL_AND_TWO_SAME_ROW_PERIOD_VALUES",
                    "unit_evidence": [
                        _ref(47, 35, "Triệu đồng"),
                        _ref(47, 36, "Triệu đồng"),
                    ],
                    "values": {
                        "COMPARATIVE_PERIOD": _ref(47, 70, "1.710.973"),
                        "CURRENT_PERIOD": _ref(47, 69, "253.111"),
                    },
                }
            )
        else:
            documents.append(
                {
                    "absence_evidence": {
                        "combined_net_numeric_row_match_count": 0,
                        "complete_pdf_pages_scanned": True,
                        "reason": (
                            "The bound report has no complete combined trading-and-investment "
                            "securities net label with two same-row period values."
                        ),
                        "source_scope_absence_only": True,
                    },
                    "bank_code": code,
                    "label_lines": [],
                    "page_span": None,
                    "period_axis": [],
                    "presentation": "NO_COMBINED_SECURITIES_NET_NUMERIC_ROW_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "values": {},
                }
            )
    return documents


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": REVIEW_STATE,
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex combined-securities pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return investment._document(items, code, label)


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    return investment._page(document, page_sequence, label)


def _schema_binding(item: Any) -> dict[str, Any]:
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != 5990
        or item.canonical_name != _SCHEMA_EXPECTED[0]
        or item.parent_id != _SCHEMA_EXPECTED[1]
        or (
            not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT
            and item.display_order != _SCHEMA_EXPECTED[2]
        )
    ):
        raise _error("mapping does not bind exact live TM schema row 5990")
    return {
        "canonical_name": item.canonical_name,
        "display_order": _SCHEMA_EXPECTED[2],
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "combined_net_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_row_count": 0,
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("combined-securities result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("combined-securities result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {"CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT", "VERIFIED_BY_CODEX"}
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
        ):
            raise _error("combined-securities trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("combined-securities result identity drifted")
    return canonical_clone_v1(value)


def _net_mapping(result: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    trial = _document(result["trials"], "MBB", "component result")
    matches = [item for item in trial["verified_mappings"] if item.get("role") == role]
    if len(matches) != 1 or matches[0].get("status") != "VERIFIED_BY_CODEX":
        raise _error(f"MBB component result does not contain one verified {role}")
    return matches[0]


def _value(mapping: Mapping[str, Any], axis_role: str) -> Mapping[str, Any]:
    matches = [item for item in mapping["values"] if item.get("axis_role") == axis_role]
    if len(matches) != 1 or type(matches[0].get("normalized_value")) is not int:
        raise _error(f"component result does not contain one exact {axis_role} value")
    return matches[0]


def build_combined_securities_net_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    trading_result: Any,
    investment_result: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
    trading_result_sha256: str | None,
    investment_result_sha256: str | None,
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis_projection = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_combined_securities_net_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if (
        axis_projection.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or type(crop_manifest) is not dict
    ):
        raise _error("fixed semantic, scan, or crop input drifted")
    _schema_binding(schema_by_id.get(5990))
    if REQUIRE_COMPONENT_RESULTS:
        trading_result = trading._validate_result(trading_result)
        investment_result = investment._validate_result(investment_result)
        if (
            trading_result.get("result_id") != EXPECTED_TRADING_RESULT_ID
            or investment_result.get("result_id") != EXPECTED_INVESTMENT_RESULT_ID
            or type(trading_result_sha256) is not str
            or type(investment_result_sha256) is not str
        ):
            raise _error("fixed component result input drifted")
        trading_net = _net_mapping(trading_result, "NET_TRADING_SECURITIES")
        investment_net = _net_mapping(investment_result, "NET_INVESTMENT_SECURITIES")
    else:
        if any(
            value is not None
            for value in (
                trading_result,
                investment_result,
                trading_result_sha256,
                investment_result_sha256,
            )
        ):
            raise _error("component results must be absent when the profile does not require them")
        trading_net = None
        investment_net = None
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
                raise _error("absent combined-net row unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "page_span": None,
                    "period_evidence": [],
                    "presentation": reviewed["presentation"],
                    "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                }
            )
            continue
        if not REQUIRE_COMPONENT_RESULTS or trading_net is None or investment_net is None:
            raise _error("a present combined-net row requires both verified component results")
        if not same_typed_json_v1(
            matcher["uniqueness"], {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ) or not same_typed_json_v1(matcher["regions"][0]["page_span"], reviewed["page_span"]):
            raise _error("reviewed combined-net row is not the unique whole-PDF graph")
        owner_refs = matcher["regions"][0]["owner"]
        value_refs = matcher["regions"][0]["value_lines"]
        if [item["source_line_index"] for item in owner_refs] != [67, 68] or [
            item["source_line_index"] for item in value_refs
        ] != [69, 70]:
            raise _error("unique combined-net graph line axis drifted")
        axis_document = _document(axis_projection["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        page_number = reviewed["page_span"][0]
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_texts = support._source_line_axis(crop_page)
        values = []
        equations = []
        for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            reference = reviewed["values"][axis_role]
            evidence = support._source_value(
                axis_page,
                semantic_page,
                crop_page,
                source_texts,
                {
                    "line_index": reference["line_index"],
                    "pixel_transcription": reference["pixel_transcription"],
                },
            )
            trading_value = _value(trading_net, axis_role)["normalized_value"]
            investment_value = _value(investment_net, axis_role)["normalized_value"]
            computed = trading_value + investment_value
            if evidence["normalized_value"] != computed:
                raise _error(f"combined securities equation does not close: {axis_role}")
            values.append({"axis_role": axis_role, **evidence, "page_sequence": page_number})
            equations.append(
                {
                    "component_report_norm_ids": [1188, 1193],
                    "component_values": [trading_value, investment_value],
                    "computed_value": computed,
                    "equation": "NET_TRADING_SECURITIES_PLUS_NET_INVESTMENT_SECURITIES_EQUALS_COMBINED_NET",
                    "period_role": axis_role,
                    "status": "CORROBORATED_EXACT",
                    "total_report_norm_id": 5990,
                }
            )
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "page_span": list(reviewed["page_span"]),
                "period_evidence": [
                    investment._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["period_axis"]
                ],
                "presentation": reviewed["presentation"],
                "status": "VERIFIED_BY_CODEX",
                "unit_evidence": [
                    investment._semantic_evidence(axis_document, semantic_document, item)
                    for item in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": [
                    {
                        "label_evidence": [
                            investment._semantic_evidence(axis_document, semantic_document, item)
                            for item in reviewed["label_lines"]
                        ],
                        "role": "COMBINED_NET_SECURITIES",
                        "schema_binding": _schema_binding(schema_by_id.get(5990)),
                        "status": "VERIFIED_BY_CODEX",
                        "topology": reviewed["presentation"],
                        "values": values,
                    }
                ],
            }
        )
    input_refs = {
        "crop_manifest_sha256": crop_manifest_sha256,
        "pixel_review_sha256": review_sha256,
        "schema_authority": canonical_clone_v1(schema_authority),
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "structure_scan_id": EXPECTED_SCAN_ID,
    }
    if REQUIRE_COMPONENT_RESULTS:
        input_refs.update(
            {
                "investment_result_id": EXPECTED_INVESTMENT_RESULT_ID,
                "investment_result_sha256": investment_result_sha256,
                "trading_result_id": EXPECTED_TRADING_RESULT_ID,
                "trading_result_sha256": trading_result_sha256,
            }
        )
    else:
        input_refs["component_results_required"] = False
    mapped_report_norm_ids = sorted(
        {
            mapping["schema_binding"]["report_norm_id"]
            for trial in trials
            for mapping in trial["verified_mappings"]
        }
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": input_refs,
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": SCHEMA_FAMILY_END_DISPLAY_ORDER,
            "family_root_report_norm_id": 5990,
            "mapped_report_norm_ids": mapped_report_norm_ids,
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_combined_securities_net_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    trading_result: Any,
    investment_result: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
    trading_result_sha256: str | None,
    investment_result_sha256: str | None,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_combined_securities_net_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        trading_result,
        investment_result,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
        review_sha256=review_sha256,
        trading_result_sha256=trading_result_sha256,
        investment_result_sha256=investment_result_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("combined-securities verified mapping does not replay exactly")
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


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_combined_securities_net_full_document_scan_v1()
    review, review_sha = _stable_json(REVIEW_PATH)
    trading_result, trading_sha = _stable_json(TRADING_RESULT_PATH)
    investment_result, investment_sha = _stable_json(INVESTMENT_RESULT_PATH)
    trading.validate_live_trading_securities_activity_8bank_codex_verified_mapping_v1(
        trading_result
    )
    investment.validate_live_investment_securities_activity_8bank_codex_verified_mapping_v1(
        investment_result
    )
    historical_result, _ = _stable_json(RESULT_PATH)
    historical_result = _validate_result(historical_result)
    if historical_result.get("result_id") != EXPECTED_RESULT_ID:
        raise _error("fixed historical combined-securities result identity drifted")
    schema_authority = canonical_clone_v1(historical_result["input_refs"]["schema_authority"])
    _live_schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, expected_name in (
        (1188, "Lãi thuần từ hoạt động mua bán chứng khoán kinh doanh"),
        (1193, "Lãi thuần từ hoạt động mua bán chứng khoán đầu tư"),
    ):
        item = schema_by_id.get(report_norm_id)
        if (
            item is None
            or item.statement_type != "TM"
            or item.canonical_name != expected_name
            or item.parent_id != 1142
        ):
            raise _error("live component-family schema binding drifted")
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "investment_result": investment_result,
        "investment_result_sha256": investment_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": structure_scan,
        "trading_result": trading_result,
        "trading_result_sha256": trading_sha,
    }


def build_live_combined_securities_net_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_combined_securities_net_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_combined_securities_net_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_combined_securities_net_8bank_codex_verified_mapping_replay_v1(
        value, **_live_inputs()
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
        _write(RESULT_PATH, build_live_combined_securities_net_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        result, _ = _stable_json(RESULT_PATH)
        validate_live_combined_securities_net_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
