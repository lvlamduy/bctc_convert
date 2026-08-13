from __future__ import annotations

import copy
import json
import pickle
from pathlib import Path
from typing import Any, cast

import pytest

import bctc_ai.evaluation.loan_maturity_8bank_ready_panel_v1 as ready
from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import BANK_ORDER


def _sha(character: str) -> str:
    return character * 64


def _pages() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "geometry_authority": "REPLAYED_E0044_READY_V2_CAS",
            "line_bboxes": [[0, index + 1, 10, index + 2] for index in range(count)],
            "line_count": count,
            "pixel_height": 1000,
            "pixel_width": 800,
            "render_sha256": _sha("a"),
            "render_size_bytes": 100,
        }
        for count in ready.EXPECTED_LINE_COUNT_VECTOR
    )


def _selection() -> dict[str, Any]:
    return {
        "manifest_sha256": _sha("b"),
        "manifest_size_bytes": 123,
        "slots": [],
    }


def _audit() -> dict[str, Any]:
    slots = []
    for bank, count in zip(BANK_ORDER, ready.EXPECTED_LINE_COUNT_VECTOR, strict=True):
        page, source_sha = ready.EXPECTED_LOCATORS[bank]
        slots.append(
            {
                "bank_code": bank,
                "geometry_authority": "REPLAYED_E0044_READY_V2_CAS",
                "line_count": count,
                "line_axis_sha256": _sha("c"),
                "physical_page": page,
                "render_sha256": _sha("d"),
                "render_size_bytes": 100,
                "source_pdf_sha256": source_sha,
            }
        )
    return ready._build_audit_receipt(_selection(), slots)


def test_exact_denominator_and_anonymous_projection_excludes_provenance() -> None:
    projection = ready._anonymous_projection(_pages(), _audit())

    assert projection["page_count"] == 8
    assert projection["line_count_vector"] == [85, 109, 110, 101, 91, 88, 87, 164]
    assert projection["sample_count"] == 835
    assert projection["authority"]["live_capability_required"] is True
    assert projection["authority"]["raw_projection_self_authenticates"] is False
    assert projection["authority"]["freezer_input_authority"] is False
    assert [page["page_id"] for page in projection["pages"]] == [
        f"page-{index:04d}" for index in range(1, 9)
    ]
    serialized = json.dumps(projection)
    for forbidden in (
        "ACB",
        "MBB",
        "VPB",
        "bank_code",
        "source_pdf_sha256",
        "physical_page",
        "adapter",
        "receipt",
        "result_ref",
        "raw_text",
    ):
        assert forbidden not in serialized


def test_raw_projection_and_forged_capability_never_grant_page_access() -> None:
    projection = ready._anonymous_projection(_pages(), _audit())
    forged = object.__new__(ready.AuthenticatedLoanMaturity8BankReadyPanelV1)

    with pytest.raises(ready.LoanMaturity8BankReadyPanelV1Error, match="exact live"):
        ready.read_authenticated_loan_maturity_8bank_anonymous_page_v1(cast(Any, projection), 1)
    with pytest.raises(ready.LoanMaturity8BankReadyPanelV1Error, match="unknown or expired"):
        ready.read_authenticated_loan_maturity_8bank_anonymous_page_v1(forged, 1)
    with pytest.raises(ready.LoanMaturity8BankReadyPanelV1Error, match="caller-constructed"):
        ready.AuthenticatedLoanMaturity8BankReadyPanelV1(object())


def test_capability_is_uncopyable_and_unserializable() -> None:
    capability = ready.AuthenticatedLoanMaturity8BankReadyPanelV1(ready._MINT_TOKEN)
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(ready.LoanMaturity8BankReadyPanelV1Error):
            operation(capability)


def test_path_contract_accepts_real_posixpath_and_rejects_escape() -> None:
    assert ready._safe_relative(Path("docs/panel.json"), "manifest", ".json") == Path(
        "docs/panel.json"
    )
    with pytest.raises(ready.LoanMaturity8BankReadyPanelV1Error, match="canonical"):
        ready._safe_relative(Path("../panel.json"), "manifest", ".json")


def test_hydration_join_key_includes_locator_and_full_source_state() -> None:
    slot = {
        "source_pdf_sha256": _sha("e"),
        "physical_page": 42,
        "inventory_evidence": {
            "result_format_version": "NATIVE",
            "route": "CAUSAL_NATIVE_TEXT",
            "status": "COMPLETE",
            "unresolved": False,
        },
    }
    assert ready._expected_hydration_key(slot) == (
        _sha("e"),
        42,
        "NATIVE",
        "CAUSAL_NATIVE_TEXT",
        "COMPLETE",
        False,
    )


def test_audit_receipt_is_separate_from_anonymous_projection() -> None:
    audit = _audit()
    anonymous = ready._anonymous_projection(_pages(), audit)

    assert audit["format_version"] == ready.AUDIT_RECEIPT_FORMAT_VERSION
    assert audit["slots"][0]["bank_code"] == "ACB"
    assert anonymous["format_version"] == ready.ANONYMOUS_BATCH_FORMAT_VERSION
    assert "slots" not in anonymous
