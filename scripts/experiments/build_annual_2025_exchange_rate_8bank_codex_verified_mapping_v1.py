#!/usr/bin/env python3
"""Verify annual-2025 end-period exchange-rate tables for eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_BASE_SCAN_ID = (
    "erfdsv1:scan:7da846ff330f40b46fee0cb94d716d5e91b622189173a90ba1f61dc55560a7c8"
)
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)

FORMAT_VERSION = "ANNUAL_2025_EXCHANGE_RATE_8BANK_CODEX_VERIFIED_MAPPING_V1"
STATE = "ANNUAL_2025_EXCHANGE_RATE_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025fxrate8bcv1:result:"
REVIEW_FORMAT = "ANNUAL_2025_EXCHANGE_RATE_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_STATE = "ANNUAL_2025_EXCHANGE_RATE_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025fxrate8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_EXCHANGE_RATE_GRAPH_EXPLICIT_OR_DOCUMENT_BOUND_RELATIVE_PERIOD_"
    "HEADER_PROVIDER_NUMERIC_CHALLENGER_ONE_BOUNDED_GEMMA4_CONFLICT_RESCUE_"
    "LIVE_TM_SCHEMA_SUPPORTED_ROWS_ONLY_OUT_OF_SCHEMA_ROWS_RETAINED_NO_EXPORT_"
    "AUTHORITY"
)

_SCHEMA = {
    "USD": (5936, "USD"),
    "EUR": (5937, "EUR"),
    "GBP": (5938, "GBP"),
    "JPY": (5939, "JPY"),
    "CHF": (5940, "CHF"),
    "AUD": (5941, "AUD"),
    "CAD": (5942, "CAD"),
    "SGD": (5943, "SGD"),
    "THB": (5944, "THB"),
    "SEK": (5945, "SEK"),
}
_GEMMA_RESCUE = {
    "bank_code": "HDB",
    "code": "NZD",
    "axis": "COMPARATIVE_PERIOD",
    "line_index": 42,
    "fresh_vietocr_text": "14.382",
    "source_numeric_challenger": "14.362",
    "gemma4_text": "14.362",
    "crop_sha256": "615106a36cb8bdd281cfeb16d299dfe152e83fae383126d88ab1323f43973ca3",
    "model": "GEMMA4_26B_A4B_IT_QAT_Q4_0_LOCAL_GPU_REASONING_OFF",
}
_AUTHORITY = {
    "accounting_equation_applicable": False,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "complete_pdf_scanned_for_every_document": True,
    "document_period_context_may_bind_relative_end_start_year_headers": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma4_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_visible_supported_currency_rows": True,
    "out_of_schema_source_rows_discarded": False,
    "provider_source_axis_used_as_numeric_challenger": True,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
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


class Annual2025ExchangeRate8BankError(ValueError):
    """The annual structure, periods, values, or schema drifted."""


def _error(message: str) -> Annual2025ExchangeRate8BankError:
    return Annual2025ExchangeRate8BankError(message)


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual exchange-rate support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _scanner() -> ModuleType:
    return _load(
        "annual_2025_exchange_rate_scan_support_v1",
        "scan_exchange_rate_full_document_vietocr_v1.py",
    )


def _support() -> ModuleType:
    return _load(
        "annual_2025_exchange_rate_source_axis_support_v1",
        "build_trading_securities_8bank_codex_verified_mapping_v1.py",
    )


def _matcher() -> ModuleType:
    return _scanner()._load_matcher()


def _stable_json(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload = _support()._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise _error(f"fixed annual exchange-rate input drifted: {path}")
    value = _support()._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error("annual exchange-rate JSON root drifted")
    return value, digest


def _document(items: Sequence[Mapping[str, Any]], code: str, label: str) -> dict[str, Any]:
    matches = [
        item for item in items if item.get("bank_code", item.get("document_provenance")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one {code} document")
    return canonical_clone_v1(matches[0])


def _page(document: Mapping[str, Any], number: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} pages drifted")
    matches = [
        page for page in pages if page.get("physical_page", page.get("page_sequence")) == number
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one page {number}")
    return canonical_clone_v1(matches[0])


def _date(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d{2})/(\d{2})/(20\d{2})", value)
    if match is None:
        raise _error(f"annual period date drifted: {value!r}")
    day, month, year = (int(part) for part in match.groups())
    return day, month, year


def _relative_period_region(
    matcher_result: Mapping[str, Any],
    axis_document: Mapping[str, Any],
    context: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    complete = [region for region in matcher_result["regions"] if region["status"] == "COMPLETE"]
    if len(complete) == 1:
        return canonical_clone_v1(complete[0]), "EXPLICIT_CURRENT_COMPARATIVE_DATE_HEADERS"
    if complete:
        raise _error("annual exchange-rate document has multiple complete regions")
    candidates = []
    for region in matcher_result["regions"]:
        if (
            region["status"] != "NEAR"
            or region["current_period"]
            or region["comparative_period"]
            or len(region["rows"]) < 2
            or not region["unit_context"]["unit_line_indices"]
        ):
            continue
        page = _page(axis_document, region["page_sequence"], "annual accounting axis")
        first_row = min(row["label_line_index"] for row in region["rows"])
        start = min(region["owner_line_indices"])
        header = [line for line in page["lines"] if start <= line["source_line_index"] < first_row]
        current = [
            line for line in header if "so cuoi nam" in _matcher()._accentless(line["vietocr_text"])
        ]
        comparative = [
            line for line in header if "so dau nam" in _matcher()._accentless(line["vietocr_text"])
        ]
        if len(current) != 1 or len(comparative) != 1:
            continue
        if current[0]["bbox"][0] >= comparative[0]["bbox"][0]:
            raise _error("relative annual exchange-rate period columns changed order")
        current_date = context["current_period_end"]
        comparative_date = context["balance_comparative_period_end"]
        current_day, current_month, current_year = _date(current_date)
        comp_day, comp_month, comp_year = _date(comparative_date)
        promoted = canonical_clone_v1(region)
        promoted["current_period"] = [
            {
                "day": current_day,
                "line_index": current[0]["source_line_index"],
                "month": current_month,
                "raw_text": current[0]["vietocr_text"],
                "year": current_year,
            }
        ]
        promoted["comparative_period"] = [
            {
                "day": comp_day,
                "line_index": comparative[0]["source_line_index"],
                "month": comp_month,
                "raw_text": comparative[0]["vietocr_text"],
                "year": comp_year,
            }
        ]
        promoted["status"] = "COMPLETE"
        candidates.append(promoted)
    if len(candidates) > 1:
        raise _error("relative annual exchange-rate period headers are not unique")
    return (
        (candidates[0], "DOCUMENT_PERIOD_CONTEXT_PLUS_RELATIVE_END_START_YEAR_HEADERS")
        if candidates
        else (None, None)
    )


def _rate_cents(value: Any) -> int:
    if type(value) is not str or value != value.strip() or not value:
        raise _error(f"exchange-rate surface drifted: {value!r}")
    if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)*", value) is None:
        raise _error(f"exchange-rate digits drifted: {value!r}")
    groups = re.split(r"[.,]", value)
    separators = re.findall(r"[.,]", value)
    if not separators:
        return int(groups[0]) * 100
    if len(groups[-1]) in {1, 2}:
        return int("".join(groups[:-1])) * 100 + int(groups[-1].ljust(2, "0"))
    if any(len(group) != 3 for group in groups[1:]):
        raise _error(f"exchange-rate grouping drifted: {value!r}")
    return int("".join(groups)) * 100


def _decimal(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _bound_line(
    semantic_page: Mapping[str, Any],
    source_axis: Sequence[str],
    index: int,
) -> tuple[dict[str, Any], str]:
    lines = semantic_page.get("lines")
    if type(lines) is not list or not 0 <= index < len(lines) or len(source_axis) != len(lines):
        raise _error("annual exchange-rate line denominator drifted")
    line = lines[index]
    if line.get("source_line_index") != index or type(line.get("crop_ref")) is not dict:
        raise _error("annual exchange-rate line identity drifted")
    return canonical_clone_v1(line), source_axis[index]


def _label_evidence(
    semantic_page: Mapping[str, Any],
    source_axis: Sequence[str],
    row: Mapping[str, Any],
) -> dict[str, Any]:
    line, source = _bound_line(semantic_page, source_axis, row["label_line_index"])
    expected = row["code"]
    source_code = _matcher()._code({"vietocr_text": source})
    fresh_code = _matcher()._code(line)
    if (
        source_code is None
        or source_code[0] != expected
        or fresh_code is None
        or fresh_code[0] != expected
    ):
        raise _error("annual exchange-rate label challengers disagree with structural code")
    return {
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "fresh_vietocr_label": line["vietocr_text"],
        "fresh_vietocr_label_status": fresh_code[1],
        "source_label_challenger": source,
        "source_line_index": row["label_line_index"],
    }


def _value_evidence(
    *,
    axis: str,
    bank_code: str,
    code: str,
    line_index: int,
    semantic_page: Mapping[str, Any],
    source_axis: Sequence[str],
) -> dict[str, Any]:
    line, source = _bound_line(semantic_page, source_axis, line_index)
    source_value = _rate_cents(source)
    try:
        fresh_value = _rate_cents(line["vietocr_text"])
    except Annual2025ExchangeRate8BankError:
        fresh_value = None
    rescue = None
    if fresh_value != source_value:
        expected = {
            "axis": axis,
            "bank_code": bank_code,
            "code": code,
            "crop_sha256": line["crop_ref"]["sha256"],
            "fresh_vietocr_text": line["vietocr_text"],
            "line_index": line_index,
            "source_numeric_challenger": source,
        }
        if any(_GEMMA_RESCUE[key] != value for key, value in expected.items()):
            raise _error("unreviewed annual exchange-rate numeric OCR conflict")
        rescue = canonical_clone_v1(_GEMMA_RESCUE)
    return {
        "axis": axis,
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "fresh_vietocr_numeric_proposal": line["vietocr_text"],
        "fresh_vietocr_numeric_status": (
            "NORMALIZES_TO_SOURCE_NUMERIC_CHALLENGER"
            if fresh_value == source_value
            else "DISAGREES_BOUNDED_GEMMA4_AND_PROVIDER_CHALLENGERS_AGREE"
        ),
        "gemma4_text_rescue": rescue,
        "normalized_decimal": _decimal(source_value),
        "normalized_value_cents": source_value,
        "source_line_index": line_index,
        "source_numeric_challenger": source,
        "source_numeric_challenger_status": "BOUND_PROVIDER_LINE_AXIS",
    }


def _schema_binding(item: Any, code: str) -> dict[str, Any]:
    schema_id, name = _SCHEMA[code]
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.canonical_name != name
        or item.parent_id != 5935
        or item.hierarchy_level != 2
        or type(item.display_order) is not int
    ):
        raise _error(f"annual exchange-rate schema binding drifted: {code}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _schema_family(item: Any) -> dict[str, Any]:
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != 5935
        or item.canonical_name != "Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo"
        or item.parent_id != 1259
        or item.hierarchy_level != 1
        or type(item.display_order) is not int
    ):
        raise _error("annual exchange-rate family schema drifted")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mappings = [row for trial in trials for row in trial["verified_mappings"]]
    source_only = [row for trial in trials for row in trial["verified_source_only_rows"]]
    all_rows = [*mappings, *source_only]
    return {
        "bounded_detailed_table_absence_count": sum(
            trial["status"] == "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT"
            for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["selected_region"] is not None for trial in trials
        ),
        "gemma4_bounded_numeric_conflict_rescue_count": sum(
            value["gemma4_text_rescue"] is not None for row in all_rows for value in row["values"]
        ),
        "mapping_verified_count": len(mappings),
        "out_of_schema_source_row_count": len(source_only),
        "relative_period_header_document_count": sum(
            trial["period_binding_status"]
            == "DOCUMENT_PERIOD_CONTEXT_PLUS_RELATIVE_END_START_YEAR_HEADERS"
            for trial in trials
        ),
        "verified_source_value_cell_count": sum(len(row["values"]) for row in all_rows),
        "verified_value_cell_count": sum(len(row["values"]) for row in mappings),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual exchange-rate result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["state"] != STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual exchange-rate result identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or any(row.get("status") != "VERIFIED_BY_CODEX" for row in trial["verified_mappings"])
            or any(
                row.get("status") != "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED"
                for row in trial["verified_source_only_rows"]
            )
        ):
            raise _error("annual exchange-rate trial shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual exchange-rate result ID drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_exchange_rate_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual exchange-rate semantic axis drifted")
    periods = validate_full_document_vietocr_reporting_period_contexts_replay_v1(
        project_full_document_vietocr_reporting_period_contexts_v1(semantic_index),
        semantic_index,
    )
    if periods["projection_id"] != EXPECTED_PERIOD_PROJECTION_ID:
        raise _error("annual exchange-rate period projection drifted")
    base_scan = _scanner().build_exchange_rate_full_document_scan_v1(semantic_index)
    if base_scan["scan_id"] != EXPECTED_BASE_SCAN_ID:
        raise _error("annual exchange-rate base scan drifted")
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    semantic_by = {item["bank_code"]: item for item in semantic_index["documents"]}
    crop_by = {item["bank_code"]: item for item in crop_manifest["documents"]}
    axis_by = {item["document_provenance"]: item for item in axis["documents"]}
    context_by = {
        item["document_provenance"]: item["reporting_period_context"]
        for item in periods["contexts"]
    }
    trials = []
    next_gap = 1
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        scan_trial = _document(base_scan["trials"], code, "annual exchange-rate base scan")
        region, period_binding = _relative_period_region(
            scan_trial["matcher_result"], axis_by[code], context_by[code]
        )
        common = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
        }
        if region is None:
            trials.append(
                {
                    **common,
                    "absence_evidence": {
                        "complete_pdf_pages_scanned": True,
                        "reason": "NO_UNIQUE_COMPLETE_EXCHANGE_RATE_REGION_IN_BOUND_PDF",
                        "source_scope_absence_only": True,
                    },
                    "period_binding_status": None,
                    "selected_region": None,
                    "status": "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                }
            )
            continue
        page_number = region["page_sequence"]
        semantic_page = _page(semantic_by[code], page_number, "annual semantic index")
        crop_page = _page(crop_by[code], page_number, "annual crop manifest")
        source_axis = _support()._source_line_axis(crop_page)
        mappings = []
        source_only = []
        for row in region["rows"]:
            label = _label_evidence(semantic_page, source_axis, row)
            values = [
                _value_evidence(
                    axis="CURRENT_PERIOD",
                    bank_code=code,
                    code=row["code"],
                    line_index=row["current_line_index"],
                    semantic_page=semantic_page,
                    source_axis=source_axis,
                ),
                _value_evidence(
                    axis="COMPARATIVE_PERIOD",
                    bank_code=code,
                    code=row["code"],
                    line_index=row["comparative_line_index"],
                    semantic_page=semantic_page,
                    source_axis=source_axis,
                ),
            ]
            if row["code"] in _SCHEMA:
                schema_id = _SCHEMA[row["code"]][0]
                mappings.append(
                    {
                        "code": row["code"],
                        "label_evidence": label,
                        "schema_binding": _schema_binding(schema_by_id.get(schema_id), row["code"]),
                        "status": "VERIFIED_BY_CODEX",
                        "values": values,
                    }
                )
            else:
                source_only.append(
                    {
                        "code": row["code"],
                        "gap_id": f"AFXRATE-{next_gap:03d}",
                        "label_evidence": label,
                        "reason": "NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD",
                        "status": "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED",
                        "values": values,
                    }
                )
                next_gap += 1
        current = region["current_period"][0]
        comparative = region["comparative_period"][0]
        if (current["day"], current["month"], current["year"]) != (31, 12, 2025) or (
            comparative["day"],
            comparative["month"],
            comparative["year"],
        ) != (31, 12, 2024):
            raise _error("annual exchange-rate local periods disagree with document context")
        trials.append(
            {
                **common,
                "absence_evidence": None,
                "period_binding_status": period_binding,
                "selected_region": {
                    "comparative_period": canonical_clone_v1(region["comparative_period"]),
                    "current_period": canonical_clone_v1(region["current_period"]),
                    "owner_line_indices": list(region["owner_line_indices"]),
                    "page_sequence": page_number,
                    "row_count": len(region["rows"]),
                    "unit_context": canonical_clone_v1(region["unit_context"]),
                },
                "status": (
                    "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS"
                    if source_only
                    else "VERIFIED_BY_CODEX"
                ),
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "base_structure_scan_id": base_scan["scan_id"],
            "crop_manifest": {"path": CROP_MANIFEST_PATH.as_posix(), "sha256": crop_sha},
            "period_projection_id": periods["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {"path": SEMANTIC_INDEX_PATH.as_posix(), "sha256": index_sha},
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": _schema_family(schema_by_id.get(5935)),
        "state": STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _review(result: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "input_result_id": result["result_id"],
        "metrics": canonical_clone_v1(result["metrics"]),
        "state": REVIEW_STATE,
        "trials": [
            {
                "document_provenance": trial["document_provenance"],
                "page_sequence": (
                    trial["selected_region"]["page_sequence"]
                    if trial["selected_region"] is not None
                    else None
                ),
                "status": "PASS",
                "verified_mapping_count": len(trial["verified_mappings"]),
                "visible_schema_gap_count": len(trial["verified_source_only_rows"]),
            }
            for trial in result["trials"]
        ],
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def validate_annual_2025_exchange_rate_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_annual_2025_exchange_rate_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual exchange-rate result does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        if RESULT_PATH.exists() or REVIEW_PATH.exists():
            raise _error("refusing to overwrite annual exchange-rate artifacts")
        result = build_live_annual_2025_exchange_rate_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result) + b"\n")
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review(result)) + b"\n")
        print(result["result_id"])
        return 0
    result, _digest = _stable_json(
        RESULT_PATH, hashlib.sha256((PROJECT_ROOT / RESULT_PATH).read_bytes()).hexdigest()
    )
    validated = validate_annual_2025_exchange_rate_8bank_codex_verified_mapping_replay_v1(result)
    review, _review_digest = _stable_json(
        REVIEW_PATH, hashlib.sha256((PROJECT_ROOT / REVIEW_PATH).read_bytes()).hexdigest()
    )
    if review != _review(validated):
        raise _error("annual exchange-rate review drifted")
    print(validated["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
