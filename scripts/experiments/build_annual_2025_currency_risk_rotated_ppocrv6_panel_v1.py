"""Build the annual currency-risk rotated full-page PP-OCRv6 panel.

The complete-PDF currency-risk graph selects the table region.  A page enters
this panel only when that selected region also belongs to the pre-existing
geometry-selected rotated semantic lane.  Bank identity, page number and note
number are provenance only.  The clockwise-normalized raster and its PP-OCRv6
line/word boxes are the canonical table coordinate space; inverse projection
to the source PDF is deferred to provenance/display boundaries.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = Path("output/calibration/annual-2025-currency-risk-rotated-ppocrv6-panel-v1")
MANIFEST_PATH = OUTPUT_ROOT / "panel_manifest.json"
EXPECTED_SCAN_ID = (
    "a2025crfdsv1:scan:3423250f79d91c015bd36031c6eb20bfe4aebbb096be25d4c47faa040c0b3ec8"
)
EXPECTED_PAGE_COUNT = 1
FORMAT_VERSION = "ANNUAL_2025_CURRENCY_RISK_ROTATED_PPOCRV6_PANEL_V1"
PROJECTION_FORMAT = "ANNUAL_2025_CURRENCY_RISK_ROTATED_PPOCRV6_VERIFIED_PROJECTION_V1"
SELECTION_RULE = "UNIQUE_COMPLETE_CURRENCY_RISK_REGION_AND_GEOMETRY_ROTATED_SOURCE_AXIS_TRUE"
PANEL_ID_PREFIX = "a2025crrpv1:panel:"
PROJECTION_ID_PREFIX = "a2025crrpv1:projection:"
_AUTHORITY = {
    "bank_filename_or_page_number_used_as_selection_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "inverse_projection_to_source_pdf_required_for_table_reasoning": False,
    "mapping_or_schema_authority": False,
    "normalized_rotated_page_is_canonical_geometry_space": True,
    "ppocrv6_is_independent_numeric_challenger_only": True,
    "rotated_page_selected_from_generic_graph_and_geometry": True,
}


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load annual currency-risk rotated support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_CORE = _load_module(
    "annual_2025_currency_risk_rotated_ppocrv6_core_v1",
    "scripts/experiments/build_annual_2025_tangible_fixed_assets_rotated_ppocrv6_panel_v1.py",
)
Annual2025CurrencyRiskRotatedPPocrV6PanelError = _CORE.Annual2025TangibleRotatedPPocrV6PanelError


def _currency_risk_selection() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scanner = _load_module(
        "annual_2025_currency_risk_rotated_ppocrv6_scanner_v1",
        "scripts/experiments/scan_annual_2025_currency_risk_full_document_vietocr_v1.py",
    )
    semantic_index, semantic_payload = _CORE._json(
        _CORE.SEMANTIC_INDEX_PATH, _CORE.EXPECTED_SEMANTIC_INDEX_SHA256
    )
    crop_manifest, crop_payload = _CORE._json(
        _CORE.CROP_MANIFEST_PATH, _CORE.EXPECTED_CROP_MANIFEST_SHA256
    )
    rotated_manifest, rotated_payload = _CORE._json(
        _CORE.ROTATED_RESCUE_MANIFEST_PATH,
        _CORE.EXPECTED_ROTATED_RESCUE_MANIFEST_SHA256,
    )
    scan = scanner.build_annual_2025_currency_risk_full_document_scan_v1()
    if scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
            "annual currency-risk scan identity drifted"
        )
    _matcher, rotated_support, rescue_builder = scanner._configured_modules()
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    if type(rescue) is not dict or type(rescue.get("samples")) is not list:
        raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
            "annual rotated semantic rescue is unavailable"
        )
    rotated_ref = _CORE._ref(_CORE.ROTATED_RESCUE_MANIFEST_PATH, rotated_payload)
    if not same_typed_json_v1(rescue.get("input_refs", {}).get("crop_manifest"), rotated_ref):
        raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
            "semantic rescue does not authenticate its rotated crop manifest"
        )
    if type(rotated_manifest.get("samples")) is not list:
        raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
            "rotated crop-manifest sample denominator drifted"
        )
    rescue_pages = {
        (sample["document_ordinal"], sample["physical_page"]) for sample in rescue["samples"]
    }
    selected: list[dict[str, Any]] = []
    for trial in scan["trials"]:
        matcher_result = trial["matcher_result"]
        if (
            matcher_result["uniqueness"]["status"] != "UNIQUE_FULL_MATCH"
            or len(matcher_result["regions"]) != 1
        ):
            raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
                "one annual document lost its unique currency-risk region"
            )
        document_ordinal = trial["document_ordinal"]
        for physical_page in matcher_result["regions"][0]["table_page_sequences"]:
            if (document_ordinal, physical_page) not in rescue_pages:
                continue
            crop_document = _CORE._one(
                crop_manifest["documents"],
                "document_ordinal",
                document_ordinal,
                "crop document",
            )
            crop_page = _CORE._one(
                crop_document["pages"], "physical_page", physical_page, "crop page"
            )
            page_samples = sorted(
                (
                    sample
                    for sample in rescue["samples"]
                    if sample["document_ordinal"] == document_ordinal
                    and sample["physical_page"] == physical_page
                ),
                key=lambda sample: sample.get("source_line_index", -1),
            )
            raw_samples = sorted(
                (
                    sample
                    for sample in rotated_manifest["samples"]
                    if type(sample) is dict
                    and sample.get("document_ordinal") == document_ordinal
                    and sample.get("physical_page") == physical_page
                ),
                key=lambda sample: sample.get("source_line_index", -1),
            )
            if (
                len(page_samples) != crop_page["line_count"]
                or len(raw_samples) != crop_page["line_count"]
            ):
                raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
                    "rotated semantic and source line denominators drifted"
                )
            for projected, raw in zip(page_samples, raw_samples, strict=True):
                rotated_crop_ref = raw.get("rotated_crop_ref")
                source_crop_ref = raw.get("source_crop_ref")
                if (
                    type(rotated_crop_ref) is not dict
                    or set(rotated_crop_ref) != _CORE._REF_FIELDS
                    or type(source_crop_ref) is not dict
                    or set(source_crop_ref) != _CORE._REF_FIELDS
                    or projected.get("source_line_index") != raw.get("source_line_index")
                    or projected.get("source_crop_sha256") != source_crop_ref.get("sha256")
                ):
                    raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
                        "semantic rescue and rotated source axes drifted"
                    )
            render_ref = canonical_clone_v1(crop_page["render_binding"])
            render_payload = _CORE._stable_bytes(Path(render_ref["path"]))
            if (
                set(render_ref) != _CORE._REF_FIELDS
                or len(render_payload) != render_ref["size_bytes"]
                or _CORE._sha256(render_payload) != render_ref["sha256"]
            ):
                raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
                    "selected source render binding drifted"
                )
            axis_material = [
                {
                    "rotated_crop_sha256": sample["rotated_crop_ref"]["sha256"],
                    "source_line_index": sample["source_line_index"],
                }
                for sample in raw_samples
            ]
            selected.append(
                {
                    "document_ordinal": document_ordinal,
                    "line_count": crop_page["line_count"],
                    "physical_page": physical_page,
                    "render_payload": render_payload,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_render_ref": render_ref,
                    "source_semantic_line_axis_sha256": canonical_json_sha256_v1(axis_material),
                }
            )
    if len(selected) != EXPECTED_PAGE_COUNT:
        raise Annual2025CurrencyRiskRotatedPPocrV6PanelError(
            "rotated currency-risk page denominator drifted"
        )
    return selected, {
        "crop_manifest": _CORE._ref(_CORE.CROP_MANIFEST_PATH, crop_payload),
        "rotated_rescue_crop_manifest": rotated_ref,
        "semantic_index": _CORE._ref(_CORE.SEMANTIC_INDEX_PATH, semantic_payload),
        "structure_scan_id": EXPECTED_SCAN_ID,
    }


def _configured_core() -> ModuleType:
    _CORE.PROJECT_ROOT = PROJECT_ROOT
    _CORE.OUTPUT_ROOT = OUTPUT_ROOT
    _CORE.MANIFEST_PATH = MANIFEST_PATH
    _CORE.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    _CORE.EXPECTED_PAGE_COUNT = EXPECTED_PAGE_COUNT
    _CORE.FORMAT_VERSION = FORMAT_VERSION
    _CORE.PROJECTION_FORMAT = PROJECTION_FORMAT
    _CORE.SELECTION_RULE = SELECTION_RULE
    _CORE.PANEL_ID_PREFIX = PANEL_ID_PREFIX
    _CORE.PROJECTION_ID_PREFIX = PROJECTION_ID_PREFIX
    _CORE.INCLUDE_WORD_AXIS = True
    _CORE._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    _CORE._live_selection = _currency_risk_selection
    return _CORE


def build_annual_2025_currency_risk_rotated_ppocrv6_panel_v1() -> dict[str, Any]:
    """Materialize graph-selected normalized currency-risk page pixels."""

    return _configured_core().build_annual_2025_tangible_rotated_ppocrv6_panel_v1()


def read_verified_annual_2025_currency_risk_rotated_ppocrv6_panel_v1() -> dict[str, Any]:
    """Replay selection and return normalized PP-OCRv6 line/word axes."""

    return _configured_core().read_verified_annual_2025_tangible_rotated_ppocrv6_panel_v1()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    value = (
        build_annual_2025_currency_risk_rotated_ppocrv6_panel_v1()
        if args.build
        else read_verified_annual_2025_currency_risk_rotated_ppocrv6_panel_v1()
    )
    print(value["panel_id"] if args.build else value["projection_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
