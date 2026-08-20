#!/usr/bin/env python3
"""Scan annual-2025 interest-rate-risk tables with the existing graph engine.

The historical family matcher remains replay-stable.  This annual adapter adds
only corpus-generic presentation handling found by scanning all eight complete
audited reports: vertically split headers, one header cell carrying both an
overdue and a non-interest axis, one-edit core row anchors, OCR-tolerant range
endpoints inside a complete header topology, and optional external/combined
state rows.  Geometry-selected landscape pages are reread by the already
sealed, same VietOCR Transformer rescue lane.

Bank, filename, page, note number and reporting year are evidence locators
only.  They are never matching or routing inputs.
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

FORMAT_VERSION = "ANNUAL_2025_INTEREST_RATE_RISK_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "INTEREST_RATE_RISK_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_INTEREST_RATE_RISK_OPTIONAL_REPRICING_AXIS_ASSET_LIABILITY_"
    "STATE_AND_GEOMETRY_SELECTED_ROTATED_SAME_TRANSFORMER_STRUCTURE_ONLY_NO_"
    "NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
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


class Annual2025InterestRateRiskFullDocumentScanV1Error(ValueError):
    """The pinned annual source, rotated rescue or family graph drifted."""


def _error(message: str) -> Annual2025InterestRateRiskFullDocumentScanV1Error:
    return Annual2025InterestRateRiskFullDocumentScanV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual interest-rate-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stable_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"annual interest-rate-risk input path is unsafe: {path}")
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
        raise _error(f"annual interest-rate-risk input changed while read: {path}")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"annual interest-rate-risk input is not strict JSON: {path}") from exc
    if type(value) is not dict:
        raise _error("annual interest-rate-risk input must be one object")
    return value


def _configured_modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    matcher = _load(
        "annual_2025_interest_rate_risk_matcher_v1",
        "interest_rate_risk_variant_graph_v1.py",
    )
    rotated_support = _load(
        "annual_2025_interest_rate_risk_rotated_support_v1",
        "scan_capital_and_funds_full_document_vietocr_v1.py",
    )
    rescue_builder = _load(
        "annual_2025_interest_rate_risk_rotated_rescue_v1",
        "build_full_document_rotated_vietocr_rescue_v1.py",
    )
    rotated_support._EXPECTED_RESCUE_REFS = EXPECTED_RESCUE_REFS
    rotated_support._EXPECTED_RESCUE_METRICS = EXPECTED_RESCUE_METRICS
    rotated_support._EXPECTED_SEMANTIC_AXIS_SHA256 = EXPECTED_SEMANTIC_AXIS_SHA256
    rescue_builder._activate_profile("annual-2025")

    original_axis_role = matcher._axis_role
    original_raw_role = matcher._raw_role
    original_table_features = matcher._table_features

    def annual_axis_roles(text: str) -> list[str]:
        value = matcher._strip(text)
        no_interest = (
            "khong chiu l" in value
            or (
                "khong" in value
                and "anh huong" in value
                and "thay doi" in value
                and "lai suat" in value
            )
            or "khong bi dinh gia lai" in value
        )
        overdue = "qua han" in value
        if no_interest and overdue:
            # A detector may merge two adjacent header cells into one text
            # line.  These remain two physical/accounting axes.  Downstream
            # geometry binds them to separate numeric column centres; this
            # structural scan must not invent a compound schema axis.
            return ["OVERDUE", "NO_INTEREST"]
        ranges = []
        if re.search(r"\btu\s+0?1\s+thang.*\bden\s+0?3\s+thang\b", value):
            ranges.append("WITHIN_1_3M")
        if re.search(r"\btu\s+(?:tren\s+)?0?3\s+thang.*\bden\s+0?6\s+thang\b", value):
            ranges.append("WITHIN_3_6M")
        if re.search(
            r"\btu\s+(?:tren\s+)?0?6\s+(?:thang|mang).*\bden\s+12\s+thang\b",
            value,
        ):
            ranges.append("WITHIN_6_12M")
        if re.search(r"\btu\s+tren\b.*\bden\s+0?5\s+nam\b", value):
            ranges.append("WITHIN_1_5Y")
        if ranges:
            return list(dict.fromkeys(ranges))
        roles = []
        original = original_axis_role(text)
        if original is not None:
            roles.append(original)
        if no_interest:
            roles.append("NO_INTEREST")
        if overdue:
            if re.search(r"\btren\s+0?3\s+thang\b", value):
                roles.append("OVERDUE_GT3M")
            elif re.search(r"\bden\s+0?3\s+thang\b", value):
                roles.append("OVERDUE_LE3M")
            else:
                roles.append("OVERDUE")
        return list(dict.fromkeys(roles))

    core_aliases = {
        "ASSET_TOTAL": ("Tổng tài sản",),
        "LIABILITY_TOTAL": ("Tổng nợ phải trả",),
        "STATE_INTERNAL": (
            "Mức chênh nhạy cảm với lãi suất nội bảng",
            "Mức chênh lệch nhạy cảm với lãi suất nội bảng",
        ),
        "STATE_EXTERNAL": (
            "Mức chênh nhạy cảm với lãi suất ngoại bảng",
            "Các cam kết ngoại bảng có tác động tới mức độ nhạy cảm với lãi suất",
        ),
        "STATE_COMBINED": (
            "Mức chênh nhạy cảm với lãi suất nội, ngoại bảng",
            "Mức chênh lệch nhạy cảm với lãi suất nội, ngoại bảng",
        ),
    }

    def annual_raw_role(text: str) -> str | None:
        role = original_raw_role(text)
        if role is not None:
            return role
        value = matcher._strip(text)
        for candidate, aliases in core_aliases.items():
            if match_vietnamese_anchor_alias_v1(value, aliases) is not None:
                return candidate
        return None

    matcher._raw_role = annual_raw_role

    def annual_header_features(
        page: dict[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]], int]:
        support = matcher._support()
        if not page["lines"]:
            return [], [], 0
        body_roles = matcher._ASSET_ROLES | {
            "ASSET_SECTION",
            "ASSET_TOTAL",
            "DERIVATIVE_ROW",
            "INTERBANK_ROW",
        }
        body_lines = [
            line for line in page["lines"] if annual_raw_role(line["normalized_text"]) in body_roles
        ]
        cutoff_y = min(
            (line["bbox"][1] for line in body_lines),
            default=max(line["bbox"][3] for line in page["lines"]),
        )
        header = [line for line in page["lines"] if line["bbox"][1] < cutoff_y]
        if not header:
            return [], [], 0
        median_height = statistics.median(line["bbox"][3] - line["bbox"][1] for line in header)
        vertical_tolerance = max(median_height * 3.5, 80)
        candidates: list[tuple[str, dict[str, Any], str]] = []
        for line in header:
            aligned = sorted(
                (
                    other
                    for other in header
                    if min(line["bbox"][2], other["bbox"][2])
                    - max(line["bbox"][0], other["bbox"][0])
                    >= min(
                        line["bbox"][2] - line["bbox"][0],
                        other["bbox"][2] - other["bbox"][0],
                    )
                    * 0.25
                    and abs(
                        (other["bbox"][1] + other["bbox"][3] - line["bbox"][1] - line["bbox"][3])
                        / 2
                    )
                    <= vertical_tolerance
                ),
                key=lambda item: (item["bbox"][1], item["bbox"][0]),
            )
            composed = " ".join(item["normalized_text"] for item in aligned)
            # Interpret the complete geometric header surface once.
            # Independently reading fragments would turn one range into a
            # false overdue axis.  A surface containing both overdue and
            # no-interest intentionally yields two ordered semantic axes;
            # the exact physical split is proven later from numeric columns.
            roles = annual_axis_roles(composed) or annual_axis_roles(line["normalized_text"])
            candidates.extend((role, line, composed) for role in roles)
        latest = {role: (line, text) for role, line, text in candidates}
        if {"OVERDUE_GT3M", "OVERDUE_LE3M"} & set(latest):
            latest.pop("OVERDUE", None)
        same_cell_order = {
            "OVERDUE": 0,
            "OVERDUE_LE3M": 0,
            "OVERDUE_GT3M": 0,
            "NO_INTEREST": 1,
        }
        axes = sorted(
            latest,
            key=lambda role: (
                (latest[role][0]["bbox"][0] + latest[role][0]["bbox"][2]) / 2,
                same_cell_order.get(role, 0),
            ),
        )
        unit_lines = [line for line in header if matcher._unit(line["normalized_text"])]
        events = [support._line_ref(latest[role][0], f"REPRICING_AXIS_{role}") for role in axes]
        events.extend(support._line_ref(line, "UNIT_AXIS") for line in unit_lines)
        return axes, events, len(unit_lines)

    matcher._header_features = annual_header_features

    def annual_joined_roles(page: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
        support = matcher._support()
        if not page["lines"]:
            return [], []
        lines = page["lines"]
        page_width = max(line["bbox"][2] for line in lines)
        label_limit = page_width * 0.48
        median_height = statistics.median(line["bbox"][3] - line["bbox"][1] for line in lines)
        labels = sorted(
            (
                line
                for line in lines
                if line["bbox"][0] <= label_limit
                and support._NUMBER.fullmatch(line["normalized_text"]) is None
            ),
            key=lambda line: (
                (line["bbox"][1] + line["bbox"][3]) / 2,
                line["bbox"][0],
            ),
        )
        roles: list[str] = []
        events: list[dict[str, Any]] = []
        after_asset_total = False
        for line in labels:
            center_y = (line["bbox"][1] + line["bbox"][3]) / 2
            followers = [
                other
                for other in labels
                if other is not line
                and 0 < (other["bbox"][1] + other["bbox"][3]) / 2 - center_y <= median_height * 4
                and min(line["bbox"][2], other["bbox"][2]) - max(line["bbox"][0], other["bbox"][0])
                >= -page_width * 0.03
            ][:3]
            phrases = [line["normalized_text"]]
            for follower in followers:
                phrases.append(f"{phrases[-1]} {follower['normalized_text']}")
            role = next(
                (found for phrase in phrases if (found := annual_raw_role(phrase)) is not None),
                None,
            )
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
        term_axes = {
            "WITHIN_1_3M",
            "WITHIN_1_5Y",
            "WITHIN_3_6M",
            "WITHIN_6_12M",
            "WITHIN_GT1Y",
            "WITHIN_GT5Y",
            "WITHIN_LE1M",
        }
        features["complete"] = (
            "TOTAL" in features["repricing_axes"]
            and bool(
                {
                    "NO_INTEREST",
                    "OVERDUE",
                    "OVERDUE_LE3M",
                    "OVERDUE_GT3M",
                }
                & set(features["repricing_axes"])
            )
            and len(set(features["repricing_axes"]) & term_axes) >= 3
            and len(features["repricing_axes"]) >= 7
            and features["unit_axis_count"] >= 1
            and features["asset_role_count"] >= 3
            and "ASSET_TOTAL" in observed
            and features["liability_role_count"] >= 1
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
        raise _error("annual interest-rate-risk scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_INTEREST_RATE_RISK_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual interest-rate-risk scan identity or metrics drifted")
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
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
            or type(trial["rotated_rescue_line_count"]) is not int
        ):
            raise _error("annual interest-rate-risk trial identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "a2025irrfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("annual interest-rate-risk scan ID drifted")
    return canonical_clone_v1(value)


def build_annual_2025_interest_rate_risk_full_document_scan_v1() -> dict[str, Any]:
    semantic_index = _stable_json(INPUT_PATH, EXPECTED_INPUT_SHA256)
    matcher, rotated_support, rescue_builder = _configured_modules()
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    if rescue["projection_id"] != EXPECTED_RESCUE_PROJECTION_ID:
        raise _error("annual interest-rate-risk rotated-rescue projection drifted")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_SEMANTIC_AXIS_SHA256:
        raise _error("annual interest-rate-risk semantic axis drifted")
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
                "matcher_result": matcher.build_interest_rate_risk_variant_graph_document_v1(pages),
                "rotated_rescue_line_count": applied,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    if total_applied != EXPECTED_RESCUE_METRICS["line_count"]:
        raise _error("annual interest-rate-risk rotated rescue was not consumed exactly once")
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
        "state": "ANNUAL_2025_INTEREST_RATE_RISK_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate(
        {
            **material,
            "scan_id": "a2025irrfdsv1:scan:" + canonical_json_sha256_v1(material),
        }
    )


def validate_annual_2025_interest_rate_risk_full_document_scan_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_annual_2025_interest_rate_risk_full_document_scan_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual interest-rate-risk scan does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    sys.stdout.buffer.write(
        canonical_json_bytes_v1(build_annual_2025_interest_rate_risk_full_document_scan_v1())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
