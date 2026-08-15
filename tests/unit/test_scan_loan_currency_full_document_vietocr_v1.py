from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_loan_currency_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location("scan_loan_currency_full_document_vietocr_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
scan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scan
_SPEC.loader.exec_module(scan)


def _matcher_result(*, accepted: bool) -> dict[str, object]:
    return {
        "format_version": scan.MATCHER_FORMAT,
        "metrics": {
            "complete_loan_currency_region_count": int(accepted),
            "near_region_count": 3,
            "orphan_currency_pair_negative_control_count": 2,
        },
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH" if accepted else "UNRESOLVED_NO_COMPLETE_REGION"
        ),
        "uniqueness": {
            "complete_region_count": int(accepted),
            "status": "UNIQUE_FULL_MATCH" if accepted else "NO_FULL_MATCH",
        },
    }


def test_build_scans_all_eight_documents_and_replay_rejects_tamper(
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
        def build_loan_currency_variant_graph_document_v1(cls, pages: object) -> object:
            del pages
            cls.calls += 1
            return _matcher_result(accepted=cls.calls != 5)

    monkeypatch.setattr(scan, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    monkeypatch.setattr(scan, "_matcher", lambda: Matcher)
    monkeypatch.setattr(scan, "_matcher_pages", lambda _: [])
    result = scan.build_loan_currency_full_document_scan_v1({})

    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 7,
        "loan_currency_region_count": 7,
        "mapping_verified_count": 0,
        "near_region_count": 24,
        "orphan_currency_pair_negative_control_count": 16,
        "unresolved_document_count": 1,
    }
    forged = copy.deepcopy(result)
    forged["trials"][0]["document_provenance"] = "MBB"
    with pytest.raises(scan.LoanCurrencyFullDocumentScanV1Error):
        scan.validate_loan_currency_full_document_scan_replay_v1(forged, {})
