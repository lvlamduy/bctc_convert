from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_interest_rate_risk_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_interest_rate_risk_full_document_vietocr_v1", _PATH
)
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


def _axis() -> dict[str, object]:
    return {
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


def _rescue() -> dict[str, object]:
    return {
        "input_refs": {},
        "metrics": {"document_count": 3, "line_count": 8, "page_count": 3},
        "projection_id": "fdrrv1:projection:test",
        "samples": [],
    }


def test_build_scans_all_eight_joins_rescue_and_replay_rejects_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Matcher:
        calls = 0

        @classmethod
        def build_interest_rate_risk_variant_graph_document_v1(cls, pages: object) -> object:
            del pages
            cls.calls += 1
            return _matcher_result(accepted=cls.calls not in {1, 7}, continuation=cls.calls == 8)

    class Support:
        calls = 0

        @staticmethod
        def _validate_rescue(value: object) -> object:
            return value

        @classmethod
        def _matcher_pages(cls, document: object, lookup: object) -> tuple[list[object], int]:
            del document, lookup
            cls.calls += 1
            return [], 1

    monkeypatch.setattr(scan, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis())
    monkeypatch.setattr(scan, "_matcher", lambda: Matcher)
    monkeypatch.setattr(scan, "_support", lambda: Support)
    result = scan.build_interest_rate_risk_full_document_scan_v1({}, _rescue())

    assert result["metrics"] == {
        "bounded_detailed_table_absence_count": 2,
        "complete_region_count": 6,
        "complete_table_page_count": 7,
        "document_count": 8,
        "document_unique_structural_match_count": 6,
        "mapping_verified_count": 0,
        "near_region_count": 16,
        "rotated_rescue_line_count": 8,
    }
    forged = copy.deepcopy(result)
    forged["trials"][0]["document_provenance"] = "MBB"
    Matcher.calls = 0
    Support.calls = 0
    with pytest.raises(scan.InterestRateRiskFullDocumentScanV1Error):
        scan.validate_interest_rate_risk_full_document_scan_replay_v1(forged, {}, _rescue())


def test_rescue_denominator_and_typed_metric_substitution_reject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Matcher:
        @staticmethod
        def build_interest_rate_risk_variant_graph_document_v1(pages: object) -> object:
            del pages
            return _matcher_result(accepted=False)

    class Support:
        @staticmethod
        def _validate_rescue(value: object) -> object:
            return value

        @staticmethod
        def _matcher_pages(document: object, lookup: object) -> tuple[list[object], int]:
            del document, lookup
            return [], 0

    monkeypatch.setattr(scan, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis())
    monkeypatch.setattr(scan, "_matcher", lambda: Matcher)
    monkeypatch.setattr(scan, "_support", lambda: Support)
    with pytest.raises(scan.InterestRateRiskFullDocumentScanV1Error):
        scan.build_interest_rate_risk_full_document_scan_v1({}, _rescue())

    monkeypatch.setattr(scan, "EXPECTED_DOCUMENT_ORDER", ())
    value = {
        "authority": copy.deepcopy(scan._AUTHORITY),
        "claim_boundary": scan.CLAIM_BOUNDARY,
        "format_version": scan.FORMAT_VERSION,
        "input_axis_projection_id": "fdvaav1:projection:test",
        "input_rescue": {},
        "input_semantic_axis_sha256": "a" * 64,
        "metrics": scan._metrics([]),
        "scan_id": "",
        "state": "FULL_DOCUMENT_INTEREST_RATE_RISK_SCAN_COMPLETE",
        "trials": [],
    }
    material = copy.deepcopy(value)
    material.pop("scan_id")
    value["scan_id"] = "irrfdsv1:scan:" + scan.canonical_json_sha256_v1(material)
    assert scan._validate(value)["metrics"]["document_count"] == 0
    value["metrics"]["document_count"] = 0.0
    with pytest.raises(scan.InterestRateRiskFullDocumentScanV1Error):
        scan._validate(value)


def test_another_corpus_runs_without_stale_rotated_rescue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Matcher:
        @staticmethod
        def build_interest_rate_risk_variant_graph_document_v1(pages: object) -> object:
            del pages
            return _matcher_result(accepted=False)

    class Support:
        @staticmethod
        def _validate_rescue(_value: object) -> object:
            raise AssertionError("an absent rescue must not be validated")

        @staticmethod
        def _matcher_pages(document: object, lookup: object) -> tuple[list[object], int]:
            del document
            assert lookup == {}
            return [], 0

    monkeypatch.setattr(scan, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis())
    monkeypatch.setattr(scan, "_matcher", lambda: Matcher)
    monkeypatch.setattr(scan, "_support", lambda: Support)

    result = scan.build_interest_rate_risk_full_document_scan_v1({}, None)

    assert result["input_rescue"] is None
    assert result["metrics"]["rotated_rescue_line_count"] == 0
