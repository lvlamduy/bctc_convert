"""Build the annual liquidity-risk rotated full-page PP-OCRv6 panel.

Selection is the intersection of the bank-blind unique liquidity graph and the
existing geometry-derived rotated-page closure.  The normalized page is the
canonical table coordinate space; PP-OCRv6 supplies an independent numeric and
word-box challenger, never schema or mapping authority.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = Path("output/calibration/annual-2025-liquidity-risk-rotated-ppocrv6-panel-v1")
MANIFEST_PATH = OUTPUT_ROOT / "panel_manifest.json"
EXPECTED_SCAN_ID = (
    "a2025lrrfdsv1:scan:912637b03ea6eec9fbdbbf8bfe11acdbf0eb39f850697220c6bc5a1043b62990"
)
EXPECTED_PAGE_COUNT = 5
FORMAT_VERSION = "ANNUAL_2025_LIQUIDITY_RISK_ROTATED_PPOCRV6_PANEL_V1"
PROJECTION_FORMAT = "ANNUAL_2025_LIQUIDITY_RISK_ROTATED_PPOCRV6_VERIFIED_PROJECTION_V1"
SELECTION_RULE = "UNIQUE_COMPLETE_LIQUIDITY_RISK_REGION_AND_GEOMETRY_ROTATED_SOURCE_AXIS_TRUE"
PANEL_ID_PREFIX = "a2025lrrrpv1:panel:"
PROJECTION_ID_PREFIX = "a2025lrrrpv1:projection:"
_AUTHORITY = {
    "bank_filename_or_page_number_used_as_selection_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "inverse_projection_to_source_pdf_required_for_table_reasoning": False,
    "mapping_or_schema_authority": False,
    "normalized_rotated_page_is_canonical_geometry_space": True,
    "ppocrv6_is_independent_numeric_challenger_only": True,
    "rotated_page_selected_from_generic_graph_and_geometry": True,
}


def _load(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load annual liquidity-risk panel support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_SUPPORT = _load(
    "annual_2025_liquidity_risk_rotated_ppocrv6_panel_support_v1",
    "scripts/experiments/build_annual_2025_interest_rate_risk_rotated_ppocrv6_panel_v1.py",
)
Annual2025LiquidityRiskRotatedPPocrV6PanelError = (
    _SUPPORT.Annual2025InterestRateRiskRotatedPPocrV6PanelError
)


def _liquidity_selection() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return _SUPPORT._interest_rate_risk_selection(
        scanner_module_name="annual_2025_liquidity_risk_rotated_ppocrv6_scanner_v1",
        scanner_filename="scan_annual_2025_liquidity_risk_full_document_vietocr_v1.py",
        scan_builder_name="build_annual_2025_liquidity_risk_full_document_scan_v1",
        expected_scan_id=EXPECTED_SCAN_ID,
        expected_page_count=EXPECTED_PAGE_COUNT,
    )


def _configured_core() -> ModuleType:
    core = _SUPPORT._CORE
    core.PROJECT_ROOT = PROJECT_ROOT
    core.OUTPUT_ROOT = OUTPUT_ROOT
    core.MANIFEST_PATH = MANIFEST_PATH
    core.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    core.EXPECTED_PAGE_COUNT = EXPECTED_PAGE_COUNT
    core.FORMAT_VERSION = FORMAT_VERSION
    core.PROJECTION_FORMAT = PROJECTION_FORMAT
    core.SELECTION_RULE = SELECTION_RULE
    core.PANEL_ID_PREFIX = PANEL_ID_PREFIX
    core.PROJECTION_ID_PREFIX = PROJECTION_ID_PREFIX
    core.INCLUDE_WORD_AXIS = True
    core._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    core._live_selection = _liquidity_selection
    return core


def build_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1() -> dict[str, Any]:
    return _configured_core().build_annual_2025_tangible_rotated_ppocrv6_panel_v1()


def read_verified_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1() -> dict[str, Any]:
    return _configured_core().read_verified_annual_2025_tangible_rotated_ppocrv6_panel_v1()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    value = (
        build_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1()
        if args.build
        else read_verified_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1()
    )
    print(value["panel_id"] if args.build else value["projection_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
