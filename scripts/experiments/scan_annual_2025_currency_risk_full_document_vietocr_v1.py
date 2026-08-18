#!/usr/bin/env python3
"""Scan annual-2025 currency-risk tables with orientation-normalized geometry.

The historical matcher remains replay-stable.  This annual wrapper applies
four bank-blind extensions discovered by scanning the complete eight-report
corpus: an empty page is a valid negative page, one-edit core row anchors are
allowed only inside the complete table topology, a short ``usp`` OCR token can
stand for the USD column header, and four distinct asset rows are sufficient
when all currency axes, totals, liability rows, state rows, units and numeric
followers are present.  Pages whose LINE boxes are overwhelmingly vertical
are normalized by the pre-existing geometry-selected clockwise-rotation lane
and reread by the same pinned VietOCR Transformer.

Bank, filename, page, note number and reporting year are evidence locators
only.  They are not matching or routing inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import statistics
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
EXPECTED_INPUT_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_SEMANTIC_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_RESCUE_PROJECTION_ID = (
    "fdrrv1:projection:6ef48add635631c2ee6d96b309002fcbc79c2b9576351b7f5afc4463ab3a2fc7"
)
EXPECTED_RESCUE_REFS = {
    "crop_manifest": (
        "680c5981dcf0fba79b969fb33d14f15b418956d390cd541443475a4435289e45",
        2_139_367,
    ),
    "ocr_result": (
        "a7c04bdb9dafb0b2017525ef83dbf8c672230cc4bbb04ba957c4c52cb7d904a4",
        1_798_255,
    ),
    "reader_request": (
        "1b537bbad4b49d7e31389e4a42f37169305be0e907143d824c1c8d4223eedd43",
        955_265,
    ),
    "run_manifest": (
        "7b1507167dc21ff337500b7248b692f5d133fe59da63f996338c5830e9f22042",
        3_161,
    ),
}
EXPECTED_RESCUE_METRICS = {"document_count": 3, "line_count": 3_338, "page_count": 25}

FORMAT_VERSION = "ANNUAL_2025_CURRENCY_RISK_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "CURRENCY_RISK_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_CURRENCY_RISK_OPTIONAL_AXIS_ASSET_LIABILITY_STATE_AND_GEOMETRY_"
    "SELECTED_ROTATED_SAME_TRANSFORMER_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_page_or_year_used_as_matching_or_routing": False,
    "bounded_detailed_table_absence_only": True,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "pair_first_variant_graph_used": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_rescue_selected_by_geometry_not_bank_or_page": True,
    "text_similarity_alone_can_accept": False,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_axis_projection_id",
    "input_rescue",
    "input_semantic_axis_sha256",
    "metrics",
    "scan_id",
    "state",
    "trials",
}


class Annual2025CurrencyRiskFullDocumentScanV1Error(ValueError):
    """The pinned annual source, rotated rescue or graph drifted."""


def _error(message: str) -> Annual2025CurrencyRiskFullDocumentScanV1Error:
    return Annual2025CurrencyRiskFullDocumentScanV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual currency-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stable_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"annual currency-risk input path is unsafe: {path}")
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[:-1]:
            child_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            path.parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            payload = b""
            while chunk := os.read(descriptor, 1024 * 1024):
                payload += chunk
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"annual currency-risk input changed while read: {path}")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"annual currency-risk input is not strict JSON: {path}") from exc
    if type(value) is not dict:
        raise _error(f"annual currency-risk input must be one object: {path}")
    return value


def _configured_modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    matcher = _load(
        "annual_2025_currency_risk_matcher_v1",
        "currency_risk_variant_graph_v1.py",
    )
    rotated_support = _load(
        "annual_2025_currency_risk_rotated_scan_support_v1",
        "scan_capital_and_funds_full_document_vietocr_v1.py",
    )
    rescue_builder = _load(
        "annual_2025_currency_risk_rotated_rescue_v1",
        "build_full_document_rotated_vietocr_rescue_v1.py",
    )
    rotated_support._EXPECTED_RESCUE_REFS = EXPECTED_RESCUE_REFS
    rotated_support._EXPECTED_RESCUE_METRICS = EXPECTED_RESCUE_METRICS
    rotated_support._EXPECTED_SEMANTIC_AXIS_SHA256 = EXPECTED_SEMANTIC_AXIS_SHA256
    rescue_builder._activate_profile("annual-2025")

    original_axes = matcher._currency_axes
    original_role = matcher._raw_role
    original_table_features = matcher._table_features

    additional_iso_currency_codes = {
        "AUD",
        "CAD",
        "CHF",
        "CNY",
        "GBP",
        "HKD",
        "JPY",
        "KRW",
        "SGD",
        "THB",
    }

    def annual_axes(text: str) -> set[str]:
        roles = original_axes(text)
        value = matcher._strip(text)
        if len(value.split()) <= 4 and "usp" in value.split():
            roles.add("USD")
        if value in {"khac", "other"}:
            roles.add("OTHER")
        if len(value.split()) <= 4:
            roles.update(
                code
                for code in additional_iso_currency_codes
                if re.search(rf"\b{code.lower()}\b", value)
            )
        return roles

    def annual_header_band(page: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = [
            line
            for line in page["lines"]
            if annual_axes(line["normalized_text"]) or matcher._unit(line["normalized_text"])
        ]
        if not candidates:
            return []
        heights = [line["bbox"][3] - line["bbox"][1] for line in page["lines"]]
        page_height = max(line["bbox"][3] for line in page["lines"])
        tolerance = max(statistics.median(heights) * 3.0, page_height * 0.035)
        bands = []
        for seed in candidates:
            seed_y = (seed["bbox"][1] + seed["bbox"][3]) / 2
            band = [
                line
                for line in candidates
                if abs((line["bbox"][1] + line["bbox"][3]) / 2 - seed_y) <= tolerance
            ]
            axes = {axis for line in band for axis in annual_axes(line["normalized_text"])}
            units = sum(matcher._unit(line["normalized_text"]) for line in band)
            span = max(line["bbox"][3] for line in band) - min(line["bbox"][1] for line in band)
            bands.append(((len(axes) >= 3, len(axes), units, -span, -seed_y), band))
        _, selected = max(bands, key=lambda item: item[0])
        selected_axes = {axis for line in selected for axis in annual_axes(line["normalized_text"])}
        if len(selected_axes) < 3:
            return []
        minimum_center = min((line["bbox"][1] + line["bbox"][3]) / 2 for line in selected)
        maximum_center = max((line["bbox"][1] + line["bbox"][3]) / 2 for line in selected)
        horizontal_threshold = max(line["bbox"][2] for line in page["lines"]) * 0.35
        margin = tolerance * 0.2
        return [
            line
            for line in page["lines"]
            if line["bbox"][0] >= horizontal_threshold
            and minimum_center - margin
            <= (line["bbox"][1] + line["bbox"][3]) / 2
            <= maximum_center + margin
        ]

    def annual_role(text: str) -> str | None:
        value = matcher._strip(text)
        if match_vietnamese_anchor_alias_v1(value, ("Tổng nợ phải trả",)) is not None:
            return "LIABILITY_TOTAL"
        if value in {
            "trang thai tien te noi bang ngoai bang",
            "trang thai tien te noi va ngoai bang",
        }:
            return "STATE_COMBINED"
        if value == "tong trang thai":
            return "STATE_COMBINED"
        return original_role(text)

    matcher._currency_axes = annual_axes
    matcher._raw_role = annual_role

    def annual_header_features(
        page: dict[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]], int]:
        support = matcher._support()
        latest_axis_line: dict[str, dict[str, Any]] = {}
        composed_axis_text: dict[str, str] = {}
        unit_lines = []
        header_band = annual_header_band(page)
        for line in header_band:
            overlapping = sorted(
                (
                    other
                    for other in header_band
                    if min(line["bbox"][2], other["bbox"][2])
                    - max(line["bbox"][0], other["bbox"][0])
                    >= min(
                        line["bbox"][2] - line["bbox"][0],
                        other["bbox"][2] - other["bbox"][0],
                    )
                    * 0.25
                ),
                key=lambda item: (item["bbox"][1], item["bbox"][0]),
            )
            composed = " ".join(item["normalized_text"] for item in overlapping)
            for axis in annual_axes(line["normalized_text"]) | annual_axes(composed):
                latest_axis_line[axis] = line
                composed_axis_text[axis] = composed
            if matcher._unit(line["normalized_text"]):
                unit_lines.append(line)
        needles = {
            "EUR": "eur",
            "GOLD": "vang",
            "OTHER": "te khac",
            "TOTAL": "tong",
            "USD": "usd",
            "VND": "vnd",
        }
        axes = sorted(
            latest_axis_line,
            key=lambda axis: (
                latest_axis_line[axis]["bbox"][0],
                composed_axis_text[axis].find(needles.get(axis, axis.lower())),
            ),
        )
        events = [
            support._line_ref(latest_axis_line[axis], f"CURRENCY_AXIS_{axis}") for axis in axes
        ]
        events.extend(support._line_ref(line, "UNIT_AXIS") for line in unit_lines)
        return axes, events, len(unit_lines)

    matcher._header_features = annual_header_features

    def annual_joined_roles(page: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
        support = matcher._support()
        roles: list[str] = []
        events: list[dict[str, Any]] = []
        after_asset_total = False
        lines = page["lines"]
        if not lines:
            return roles, events
        header_lines = annual_header_band(page)
        if not header_lines:
            return roles, events
        header_bottom = max(line["bbox"][3] for line in header_lines)
        label_zone_limit = max(line["bbox"][2] for line in lines) * 0.48
        line_height = statistics.median(line["bbox"][3] - line["bbox"][1] for line in lines)
        label_lines = [
            line
            for line in lines
            if line["bbox"][0] <= label_zone_limit
            and support._NUMBER.fullmatch(line["normalized_text"]) is None
        ]
        for line in lines:
            if line["bbox"][3] <= header_bottom:
                continue
            candidates = [line["normalized_text"]]
            continuation_texts: list[str] = []
            current_is_label = (
                line["bbox"][0] <= label_zone_limit
                and support._NUMBER.fullmatch(line["normalized_text"]) is None
            )
            if current_is_label:
                center_y = (line["bbox"][1] + line["bbox"][3]) / 2
                continuations = sorted(
                    (
                        other
                        for other in label_lines
                        if other is not line
                        and 0
                        < (other["bbox"][1] + other["bbox"][3]) / 2 - center_y
                        <= line_height * 1.8
                    ),
                    key=lambda other: (
                        (other["bbox"][1] + other["bbox"][3]) / 2,
                        other["bbox"][0],
                    ),
                )[:2]
                for continuation in continuations:
                    continuation_texts.append(continuation["normalized_text"])
                    candidates.append(f"{candidates[-1]} {continuation['normalized_text']}")
            role = annual_role(candidates[0])
            for candidate, continuation_text in zip(
                candidates[1:], continuation_texts, strict=True
            ):
                continuation_role = annual_role(continuation_text)
                joined_role = annual_role(candidate)
                if continuation_role is not None:
                    break
                if joined_role is not None:
                    role = joined_role
            if role is None:
                continue
            if role == "ASSET_TOTAL":
                after_asset_total = True
            elif role == "DERIVATIVE_ROW":
                role = "LIABILITY_DERIVATIVE" if after_asset_total else "ASSET_DERIVATIVE"
            elif role == "INTERBANK_ROW":
                role = "LIABILITY_GOVERNMENT_INTERBANK" if after_asset_total else "ASSET_INTERBANK"
            if role not in roles:
                roles.append(role)
                events.append(support._line_ref(line, role))
        return roles, events

    matcher._joined_roles = annual_joined_roles

    def annual_table_features(page: dict[str, Any]) -> dict[str, Any]:
        features = original_table_features(page)
        observed = set(features["observed_source_roles"])
        features["complete"] = (
            "USD" in features["currency_axes"]
            and "TOTAL" in features["currency_axes"]
            and len(features["currency_axes"]) >= 4
            and features["unit_axis_count"] >= 1
            and features["asset_role_count"] >= 4
            and "ASSET_TOTAL" in observed
            and features["liability_role_count"] >= 3
            and "LIABILITY_TOTAL" in observed
            and "STATE_INTERNAL" in observed
            and features["numeric_token_count"] >= 20
            and not features["negative_families"]
        )
        return features

    matcher._table_features = annual_table_features
    return matcher, rotated_support, rescue_builder


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    return {
        "bounded_detailed_table_absence_count": len(trials) - unique,
        "complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials
        ),
        "complete_table_page_count": sum(
            trial["matcher_result"]["metrics"]["complete_table_page_count"] for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual currency-risk scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_CURRENCY_RISK_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual currency-risk scan identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial)
            != {
                "document_ordinal",
                "document_provenance",
                "matcher_result",
                "rotated_rescue_line_count",
                "source_pdf_sha256",
            }
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
            or type(trial["rotated_rescue_line_count"]) is not int
        ):
            raise _error("annual currency-risk trial identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "a2025crfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("annual currency-risk scan ID drifted")
    return canonical_clone_v1(value)


def build_annual_2025_currency_risk_full_document_scan_v1() -> dict[str, Any]:
    semantic_index = _stable_json(INPUT_PATH, EXPECTED_INPUT_SHA256)
    matcher, rotated_support, rescue_builder = _configured_modules()
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    if rescue["projection_id"] != EXPECTED_RESCUE_PROJECTION_ID:
        raise _error("annual currency-risk rotated-rescue projection drifted")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_SEMANTIC_AXIS_SHA256:
        raise _error("annual currency-risk semantic axis drifted")
    rescue_by_locator = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in rescue["samples"]
    }
    trials = []
    total_applied = 0
    for document in axis["documents"]:
        pages, applied = rotated_support._matcher_pages(document, rescue_by_locator)
        total_applied += applied
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": matcher.build_currency_risk_variant_graph_document_v1(pages),
                "rotated_rescue_line_count": applied,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    if total_applied != EXPECTED_RESCUE_METRICS["line_count"]:
        raise _error("annual currency-risk rotated rescue was not consumed exactly once")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_rescue": {
            "input_refs": rescue["input_refs"],
            "metrics": rescue["metrics"],
            "projection_id": rescue["projection_id"],
        },
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "ANNUAL_2025_CURRENCY_RISK_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate(
        {**material, "scan_id": "a2025crfdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_annual_2025_currency_risk_full_document_scan_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_annual_2025_currency_risk_full_document_scan_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual currency-risk scan does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    sys.stdout.buffer.write(
        canonical_json_bytes_v1(build_annual_2025_currency_risk_full_document_scan_v1())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
