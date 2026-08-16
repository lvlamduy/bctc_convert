from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_liquidity_risk_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_liquidity_risk_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scan
_SPEC.loader.exec_module(scan)


def _axis() -> dict[str, object]:
    return {
        "documents": [
            {
                "document_ordinal": ordinal,
                "document_provenance": bank,
                "pages": [],
                "source_pdf": {"sha256": f"{ordinal:064x}"},
            }
            for ordinal, bank in enumerate(scan.EXPECTED_DOCUMENT_ORDER, 1)
        ],
        "projection_id": "fdvaav1:projection:test",
        "semantic_axis_sha256": "a" * 64,
    }


def _matcher_result() -> dict[str, object]:
    return {
        "format_version": scan.MATCHER_FORMAT,
        "metrics": {
            "complete_region_count": 0,
            "complete_table_page_count": 0,
            "near_region_count": 0,
        },
        "uniqueness": {"status": "NOT_UNIQUE_FULL_MATCH"},
    }


@pytest.mark.parametrize("rescue_lines", (None, 8))
def test_liquidity_scan_uses_only_a_supplied_corpus_bound_rescue(
    monkeypatch: pytest.MonkeyPatch, rescue_lines: int | None
) -> None:
    class Matcher:
        @staticmethod
        def build_liquidity_risk_variant_graph_document_v1(pages: object) -> object:
            del pages
            return _matcher_result()

    class Support:
        @staticmethod
        def _validate_rescue(value: object) -> object:
            assert rescue_lines is not None
            return value

        @staticmethod
        def _matcher_pages(document: object, lookup: object) -> tuple[list[object], int]:
            del document
            assert bool(lookup) is (rescue_lines is not None)
            return [], int(rescue_lines is not None)

    rescue = (
        {
            "input_refs": {},
            "metrics": {"document_count": 8, "line_count": 8, "page_count": 8},
            "projection_id": "fdrrv1:projection:test",
            "samples": [
                {
                    "document_ordinal": ordinal,
                    "physical_page": 1,
                    "source_line_index": 0,
                }
                for ordinal in range(1, 9)
            ],
        }
        if rescue_lines is not None
        else None
    )
    monkeypatch.setattr(scan, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis())
    monkeypatch.setattr(scan, "_matcher", lambda: Matcher)
    monkeypatch.setattr(scan, "_support", lambda: Support)

    result = scan.build_liquidity_risk_full_document_scan_v1({}, rescue)

    assert (result["input_rescue"] is None) is (rescue is None)
    assert result["metrics"]["rotated_rescue_line_count"] == (rescue_lines or 0)
