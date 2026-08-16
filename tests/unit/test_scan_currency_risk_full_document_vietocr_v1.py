from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_currency_risk_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location("scan_currency_risk_full_document_vietocr_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
scan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scan
_SPEC.loader.exec_module(scan)


def _matcher_result(*, accepted: bool, continuation: bool = False) -> dict[str, object]:
    count = int(accepted)
    return {
        "format_version": scan.MATCHER_FORMAT,
        "metrics": {
            "complete_region_count": count,
            "complete_table_page_count": 2 if continuation else count,
            "near_region_count": 2,
            "page_count_with_complete_region": 2 if continuation else count,
        },
        "uniqueness": {
            "complete_region_count": count,
            "status": "UNIQUE_FULL_MATCH" if accepted else "NOT_UNIQUE_FULL_MATCH",
        },
    }


def test_build_scans_all_eight_and_replay_rejects_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = {
        "documents": [
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "pages": [],
                "source_pdf": {"sha256": f"{ordinal:064x}"},
            }
            for ordinal, code in enumerate(scan.EXPECTED_DOCUMENT_ORDER, 1)
        ],
        "projection_id": "fdvaav1:projection:test",
        "semantic_axis_sha256": "a" * 64,
    }

    class Matcher:
        calls = 0

        @classmethod
        def build_currency_risk_variant_graph_document_v1(cls, pages: object) -> object:
            del pages
            cls.calls += 1
            return _matcher_result(accepted=cls.calls not in {1, 7}, continuation=cls.calls == 8)

    class Support:
        @staticmethod
        def _matcher_pages(document: object) -> list[object]:
            del document
            return []

    monkeypatch.setattr(scan, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    monkeypatch.setattr(scan, "_matcher", lambda: Matcher)
    monkeypatch.setattr(scan, "_support", lambda: Support)
    result = scan.build_currency_risk_full_document_scan_v1({})

    assert result["metrics"] == {
        "bounded_detailed_table_absence_count": 2,
        "complete_region_count": 6,
        "complete_table_page_count": 7,
        "document_count": 8,
        "document_unique_structural_match_count": 6,
        "mapping_verified_count": 0,
        "near_region_count": 16,
    }
    forged = copy.deepcopy(result)
    forged["trials"][0]["document_provenance"] = "MBB"
    with pytest.raises(scan.CurrencyRiskFullDocumentScanV1Error):
        scan.validate_currency_risk_full_document_scan_replay_v1(forged, {})


def test_float_metric_substitution_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    value = {
        "authority": copy.deepcopy(scan._AUTHORITY),
        "claim_boundary": scan.CLAIM_BOUNDARY,
        "format_version": scan.FORMAT_VERSION,
        "input_axis_projection_id": "fdvaav1:projection:test",
        "input_semantic_axis_sha256": "a" * 64,
        "metrics": {},
        "scan_id": "",
        "state": "FULL_DOCUMENT_CURRENCY_RISK_SCAN_COMPLETE",
        "trials": [],
    }
    monkeypatch.setattr(scan, "EXPECTED_DOCUMENT_ORDER", ())
    value["metrics"] = scan._metrics([])
    material = copy.deepcopy(value)
    material.pop("scan_id")
    value["scan_id"] = "crfdsv1:scan:" + scan.canonical_json_sha256_v1(material)
    assert scan._validate(value)["metrics"]["document_count"] == 0
    value["metrics"]["document_count"] = 0.0
    with pytest.raises(scan.CurrencyRiskFullDocumentScanV1Error):
        scan._validate(value)
