from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_loan_currency_8bank_codex_verified_absence_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_loan_currency_8bank_codex_verified_absence_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = module
_SPEC.loader.exec_module(module)


def _scan() -> dict[str, object]:
    return {
        "metrics": {
            "document_unique_structural_match_count": 0,
            "loan_currency_region_count": 0,
        },
        "scan_id": "lcfdsv1:scan:test",
        "trials": [
            {
                "document_ordinal": ordinal,
                "document_provenance": bank,
                "matcher_result": {
                    "result_id": f"lcvgv1:result:{ordinal}",
                    "status": "UNRESOLVED_NO_COMPLETE_REGION",
                },
                "source_pdf_sha256": f"{ordinal:064x}",
            }
            for ordinal, bank in enumerate(module.EXPECTED_DOCUMENT_ORDER, 1)
        ],
    }


def test_builds_bounded_absence_and_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = {
        "review_id": "e0064:review:test",
        "documents": [
            {"bank": bank, "loan_note_span_pages": [ordinal]}
            for ordinal, bank in enumerate(module.EXPECTED_DOCUMENT_ORDER, 1)
        ],
    }
    schema = {
        "order_authority": "test",
        "rows": [],
        "tm_context_projection_sha256": "a" * 64,
        "tm_schema_projection_sha256": "b" * 64,
    }
    monkeypatch.setattr(module, "_validate_review", lambda value, *_: value)
    monkeypatch.setattr(
        module.scanner, "build_loan_currency_full_document_scan_v1", lambda _: _scan()
    )
    monkeypatch.setattr(module, "_schema_projection", lambda _: schema)

    result = module.build_loan_currency_8bank_codex_verified_absence_v1(
        _ROOT, {}, {}, review, input_refs={"fixed": True}
    )
    assert result["metrics"] == {
        "bound_pdf_family_absence_verified_count": 8,
        "document_count": 8,
        "mapped_value_count": 0,
        "mapping_verified_count": 0,
        "schema_row_count": 3,
        "unresolved_item_count": 0,
    }
    assert all(
        item["status"] == "VERIFIED_NOT_OBSERVED_IN_BOUND_PDF"
        and item["report_norm_ids_not_observed"] == [756, 757, 758]
        for item in result["trials"]
    )

    forged = copy.deepcopy(result)
    forged["trials"][0]["status"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0064:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(module.LoanCurrency8BankCodexVerifiedAbsenceV1Error):
        module.validate_loan_currency_8bank_codex_verified_absence_replay_v1(
            forged, _ROOT, {}, {}, review, input_refs={"fixed": True}
        )


def test_review_exact_types_reject_bool_laundering() -> None:
    value = copy.deepcopy(module._REVIEW_SAFETY)
    value["fixed_eight_pdf_loan_note_absence_claim"] = 1
    assert not module.same_typed_json_v1(value, module._REVIEW_SAFETY)
