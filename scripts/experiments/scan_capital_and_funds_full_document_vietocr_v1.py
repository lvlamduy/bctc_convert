"""Scan all eight fresh-VietOCR PDFs for capital-and-funds disclosures."""

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
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
FORMAT_VERSION = "CAPITAL_AND_FUNDS_8DOCUMENT_FULL_VIETOCR_SCAN_V2"
MATCHER_FORMAT = "CAPITAL_AND_FUNDS_VARIANT_GRAPH_DOCUMENT_V1"
RESCUE_FORMAT = "FULL_DOCUMENT_ROTATED_VIETOCR_RESCUE_PROJECTION_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_CAPITAL_FUNDS_OWNER_"
    "STATEMENT_OF_CHANGES_CORE_EQUITY_CHILD_PERIOD_UNIT_AND_GEOMETRY_SELECTED_"
    "ROTATED_SAME_TRANSFORMER_RESCUE_SCAN_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_first_variant_graph_used": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_rescue_selected_by_geometry_not_bank_or_page": True,
    "rotated_rescue_uses_same_pinned_vietocr_transformer": True,
}
_RESULT_FIELDS = {
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
_EXPECTED_RESCUE_REFS = {
    "crop_manifest": (
        "2c61c6475f12a0034e43a0e4317b38168930d915c591c400d31e5648183e1dd3",
        1_148_957,
    ),
    "ocr_result": (
        "a41046013fbc5e94eb2a24779a41c2e631992491c803e1f2a059974498812cdc",
        971_193,
    ),
    "reader_request": (
        "2acefd188cc2e17f79af6098cce1589b97545bb73bba13c2779d5cff43731423",
        499_863,
    ),
    "run_manifest": (
        "b6630753cb0d8d71cfca1078de464628915de69670f80ba486c7203f554f297f",
        3_142,
    ),
}
_EXPECTED_RESCUE_METRICS = {"document_count": 3, "line_count": 1_863, "page_count": 15}
_EXPECTED_SEMANTIC_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"


class CapitalAndFundsFullDocumentScanV1Error(ValueError):
    """The semantic axis or capital-and-funds scan drifted."""


def _error(message: str) -> CapitalAndFundsFullDocumentScanV1Error:
    return CapitalAndFundsFullDocumentScanV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _support() -> ModuleType:
    return _load_module(
        "tangible_fixed_assets_support_for_capital_and_funds",
        "scan_tangible_fixed_assets_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "capital_and_funds_matcher_for_full_document_scan",
        "capital_and_funds_variant_graph_v1.py",
    )


def _rescue_builder() -> ModuleType:
    return _load_module(
        "full_document_rotated_vietocr_rescue_for_capital_and_funds",
        "build_full_document_rotated_vietocr_rescue_v1.py",
    )


def _profile_rescue(semantic_index: Any) -> Any | None:
    metrics = semantic_index.get("metrics") if type(semantic_index) is dict else None
    semantic_axis = metrics.get("semantic_axis_sha256") if type(metrics) is dict else None
    if semantic_axis == _EXPECTED_SEMANTIC_AXIS_SHA256:
        return _rescue_builder().read_verified_full_document_rotated_vietocr_rescue_v1()
    return None


def _validate_rescue(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "authority",
            "format_version",
            "input_refs",
            "metrics",
            "pages",
            "projection_id",
            "samples",
            "source_semantic_axis_sha256",
            "state",
        }
        or value["format_version"] != RESCUE_FORMAT
        or value["state"] != "VERIFIED_ROTATED_VIETOCR_SEMANTIC_RESCUE_COMPLETE"
        or value["source_semantic_axis_sha256"] != _EXPECTED_SEMANTIC_AXIS_SHA256
        or not same_typed_json_v1(value["metrics"], _EXPECTED_RESCUE_METRICS)
        or type(value["input_refs"]) is not dict
        or set(value["input_refs"]) != set(_EXPECTED_RESCUE_REFS)
        or type(value["pages"]) is not list
        or len(value["pages"]) != _EXPECTED_RESCUE_METRICS["page_count"]
        or type(value["samples"]) is not list
        or len(value["samples"]) != _EXPECTED_RESCUE_METRICS["line_count"]
    ):
        raise _error("rotated semantic rescue identity or denominator drifted")
    for name, (expected_sha, expected_size) in _EXPECTED_RESCUE_REFS.items():
        reference = value["input_refs"][name]
        if (
            type(reference) is not dict
            or reference.get("sha256") != expected_sha
            or reference.get("size_bytes") != expected_size
        ):
            raise _error(f"rotated semantic rescue {name} selection drifted")
    material = canonical_clone_v1(value)
    projection_id = material.pop("projection_id")
    if projection_id != "fdrrv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("rotated semantic rescue projection identity drifted")
    seen: set[tuple[int, int, int]] = set()
    for sample in value["samples"]:
        if (
            type(sample) is not dict
            or set(sample)
            != {
                "document_ordinal",
                "mean_decoded_character_probability",
                "physical_page",
                "semantic_text",
                "source_crop_sha256",
                "source_line_index",
            }
            or type(sample["document_ordinal"]) is not int
            or type(sample["physical_page"]) is not int
            or type(sample["source_line_index"]) is not int
            or type(sample["semantic_text"]) is not str
        ):
            raise _error("rotated semantic rescue sample shape drifted")
        key = (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"])
        if key in seen:
            raise _error("rotated semantic rescue repeats one source line")
        seen.add(key)
    return canonical_clone_v1(value)


def _matcher_pages(
    document: dict[str, Any], rescue_by_locator: dict[tuple[int, int, int], dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    pages = []
    applied = 0
    for page in document["pages"]:
        source_lines = list(page["lines"])
        rescue_count = sum(
            (
                document["document_ordinal"],
                page["page_sequence"],
                line["source_line_index"],
            )
            in rescue_by_locator
            for line in source_lines
        )
        if rescue_count not in {0, len(source_lines)}:
            raise _error("rotated rescue must cover the selected page's complete line denominator")
        if rescue_count:
            # A clockwise page rotation maps source x to logical y and reverses
            # source y into logical x.  This is a geometry-derived reading-order
            # normalization, not a bank/page/family rule.
            logical_extent = max(line["bbox"][3] for line in source_lines) + 1
            source_lines = [
                {
                    **line,
                    "bbox": [
                        logical_extent - line["bbox"][3],
                        line["bbox"][0],
                        logical_extent - line["bbox"][1],
                        line["bbox"][2],
                    ],
                }
                for line in source_lines
            ]
            source_lines.sort(
                key=lambda line: (
                    line["bbox"][1],
                    line["bbox"][0],
                    line["source_line_index"],
                )
            )
        lines = []
        for line in source_lines:
            key = (
                document["document_ordinal"],
                page["page_sequence"],
                line["source_line_index"],
            )
            sample = rescue_by_locator.get(key)
            if sample is None:
                semantic_text = line["vietocr_text"]
                semantic_source = "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
            else:
                semantic_text = sample["semantic_text"]
                semantic_source = "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
                applied += 1
            lines.append(
                {
                    "bbox": line["bbox"],
                    "semantic_text": semantic_text,
                    "semantic_text_source": semantic_source,
                    "source_line_index": line["source_line_index"],
                    "source_text": line["source_text"],
                    "vietocr_text": semantic_text,
                }
            )
        pages.append(
            {
                "lines": lines,
                "page_sequence": page["page_sequence"],
                "primary_numeric_authority": page["primary_numeric_authority"],
            }
        )
    return pages, applied


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    complete = sum(trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials)
    near = sum(trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials)
    return {
        "complete_region_count": complete,
        "document_count": len(trials),
        "document_multiple_complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] > 1 for trial in trials
        ),
        "document_unique_structural_match_count": sum(
            trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
            for trial in trials
        ),
        "mapping_verified_count": 0,
        "near_region_count": near,
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
        "unresolved_document_count": sum(
            trial["matcher_result"]["uniqueness"]["status"] != "UNIQUE_FULL_MATCH"
            for trial in trials
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("capital-and-funds scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_CAPITAL_AND_FUNDS_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("capital-and-funds scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "rotated_rescue_line_count",
            "source_pdf_sha256",
        }:
            raise _error("capital-and-funds scan trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
            or type(trial["rotated_rescue_line_count"]) is not int
        ):
            raise _error("capital-and-funds scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("capital-and-funds scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "caffdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("capital-and-funds scan identity drifted")
    return canonical_clone_v1(value)


def build_capital_and_funds_full_document_scan_v1(
    semantic_index: Any, rescue: Any | None = None
) -> dict[str, Any]:
    """Build the exact eight-document capital-and-funds structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    authenticated_rescue = _validate_rescue(rescue) if rescue is not None else None
    rescue_by_locator = (
        {
            (
                sample["document_ordinal"],
                sample["physical_page"],
                sample["source_line_index"],
            ): sample
            for sample in authenticated_rescue["samples"]
        }
        if authenticated_rescue is not None
        else {}
    )
    trials = []
    total_applied = 0
    for document in axis["documents"]:
        pages, applied_count = _matcher_pages(document, rescue_by_locator)
        total_applied += applied_count
        result = matcher.build_capital_and_funds_variant_graph_document_v1(pages)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "rotated_rescue_line_count": applied_count,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    if (
        authenticated_rescue is not None
        and total_applied != authenticated_rescue["metrics"]["line_count"]
    ):
        raise _error("rotated semantic rescue did not join its exact source-line denominator")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_rescue": (
            {
                "input_refs": authenticated_rescue["input_refs"],
                "metrics": authenticated_rescue["metrics"],
                "projection_id": authenticated_rescue["projection_id"],
            }
            if authenticated_rescue is not None
            else None
        ),
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "FULL_DOCUMENT_CAPITAL_AND_FUNDS_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "caffdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_capital_and_funds_full_document_scan_replay_v1(
    value: Any, semantic_index: Any, rescue: Any | None = None
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_capital_and_funds_full_document_scan_v1(semantic_index, rescue)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("capital-and-funds scan does not replay exactly")
    return supplied


def build_live_capital_and_funds_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    rescue = _profile_rescue(semantic_index)
    return build_capital_and_funds_full_document_scan_v1(semantic_index, rescue)


def validate_live_capital_and_funds_full_document_scan_v1(
    value: Any, input_path: Path = DEFAULT_INPUT
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    rescue = _profile_rescue(semantic_index)
    return validate_capital_and_funds_full_document_scan_replay_v1(value, semantic_index, rescue)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_capital_and_funds_full_document_scan_v1(args.input)
    payload = canonical_json_bytes_v1(result)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
