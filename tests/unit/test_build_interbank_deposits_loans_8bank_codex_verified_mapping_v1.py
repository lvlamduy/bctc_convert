from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_interbank_deposits_loans_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_interbank_deposits_loans_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_fixed_review_has_six_unique_detail_notes_and_three_pixel_dash_zeros() -> None:
    review = mapping._review_blueprint()
    positive = [document for document in review["documents"] if document["mappings"]]
    negative = [document for document in review["documents"] if not document["mappings"]]

    assert [document["bank_code"] for document in positive] == [
        "ACB",
        "MBB",
        "VPB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["bank_code"] for document in negative] == ["HDB", "VCB"]
    assert sum(len(document["mappings"]) for document in positive) == 63
    dash_rows = [
        row
        for document in positive
        for row in document["mappings"]
        if row["value"]["pixel_transcription"] == "-"
    ]
    assert len(dash_rows) == 3
    assert all(row["value"]["line_index"] is None for row in dash_rows)
    assert all(row["value"]["pixel_binding"] is not None for row in dash_rows)
    assert positive[2]["source_period"] == "2026-03-31"


def test_persisted_result_locks_boundaries_numbers_equations_schema_and_dash_status() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 23,
        "document_count": 8,
        "document_unique_region_count": 6,
        "mapping_verified_count": 63,
        "partial_mapping_document_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "unmapped_source_row_count": 0,
        "unresolved_document_count": 2,
    }
    mapped = [trial for trial in persisted["trials"] if trial["verified_mappings"]]
    assert [trial["document_provenance"] for trial in mapped] == [
        "ACB",
        "MBB",
        "VPB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in mapped
        for equation in trial["verified_accounting_equations"]
    )
    acb_dash = [
        row
        for row in mapped[0]["verified_mappings"]
        if row["source_value"].get("source_cell_status") == "DASH"
    ]
    assert {row["role"] for row in acb_dash} == {
        "INTERBANK_DEPOSIT_PROVISION",
        "INTERBANK_LOAN_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_PROVISION",
    }
    assert all(row["normalized_value"] == 0 for row in acb_dash)
    assert {row["report_norm_id"] for row in mapped[3]["verified_mappings"]} >= {
        575,
        577,
        578,
        579,
        580,
        581,
        582,
        585,
        586,
        587,
        588,
    }


def test_review_tamper_bool_poison_and_coordinated_rehash_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged_review = mapping._review_blueprint()
    dash = next(
        row
        for row in forged_review["documents"][0]["mappings"]
        if row["value"]["pixel_transcription"] == "-"
    )
    dash["value"]["pixel_binding"]["rgb_sha256"] = "0" * 64
    with pytest.raises(
        mapping.InterbankDepositsLoans8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._review(forged_review)

    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    poisoned = copy.deepcopy(persisted)
    poisoned["authority"]["current_reporting_period_only_mapped"] = 1
    with pytest.raises(
        mapping.InterbankDepositsLoans8BankCodexVerifiedMappingV1Error,
        match="identity or metrics",
    ):
        mapping._validate_result(poisoned)

    forged = copy.deepcopy(persisted)
    forged["trials"][0]["verified_mappings"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "idl8bcv1:result:" + mapping.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        mapping.scanner,
        "build_interbank_deposits_loans_full_document_scan_v1",
        lambda _: {},
    )
    monkeypatch.setattr(
        mapping,
        "build_interbank_deposits_loans_8bank_codex_verified_mapping_v1",
        lambda *args, **kwargs: persisted,
    )
    with pytest.raises(
        mapping.InterbankDepositsLoans8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        mapping.validate_interbank_deposits_loans_8bank_codex_verified_mapping_replay_v1(
            forged,
            {},
            {},
            {},
            {},
            {},
            crop_manifest_sha256="a" * 64,
            review_sha256="b" * 64,
        )
