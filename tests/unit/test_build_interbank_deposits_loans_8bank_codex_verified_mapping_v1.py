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


def test_annual_2025_review_covers_eight_unique_interbank_notes() -> None:
    review = mapping._annual_2025_review_blueprint()

    assert [document["bank_code"] for document in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["page_sequence"] for document in review["documents"]] == [
        46,
        48,
        42,
        34,
        36,
        40,
        39,
        36,
    ]
    assert sum(len(document["mappings"]) for document in review["documents"]) == 86
    assert all(document["unmapped_rows"] == [] for document in review["documents"])


def test_annual_2025_dash_and_fresh_vietocr_disagreements_are_explicit() -> None:
    review = mapping._annual_2025_review_blueprint()
    mapped_dashes = [
        row
        for document in review["documents"]
        for row in document["mappings"]
        if row["value"]["line_index"] is None
    ]
    assert len(mapped_dashes) == 7
    assert all(row["value"]["pixel_transcription"] == "-" for row in mapped_dashes)
    assert all(row["value"]["pixel_binding"] is not None for row in mapped_dashes)

    hdb = next(document for document in review["documents"] if document["bank_code"] == "HDB")
    loan = next(row for row in hdb["mappings"] if row["role"] == "INTERBANK_LOAN")
    assert loan["value"]["fresh_vietocr_challenger_expected"] == "27.921.364"
    assert loan["value"]["pixel_transcription"] == "27.921.384"
    assert loan["value"]["source_numeric_challenger_expected"] == "27.921.384"


def test_annual_2025_persisted_result_is_complete_and_accounting_closed() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.ANNUAL_2025_RESULT_PATH).read_text()),
        "annual-2025",
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 33,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 86,
        "partial_mapping_document_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "unmapped_source_row_count": 0,
        "unresolved_document_count": 0,
    }
    assert all(trial["status"] == "VERIFIED_BY_CODEX" for trial in persisted["trials"])
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in persisted["trials"]
        for equation in trial["verified_accounting_equations"]
    )
    hdb = next(trial for trial in persisted["trials"] if trial["document_provenance"] == "HDB")
    loan = next(row for row in hdb["verified_mappings"] if row["role"] == "INTERBANK_LOAN")
    assert loan["normalized_value"] == 27_921_384
    assert loan["source_value"]["fresh_vietocr_numeric_proposal"] == "27.921.364"
    for code in ("MBB", "VCB", "BID"):
        trial = next(trial for trial in persisted["trials"] if trial["document_provenance"] == code)
        provision = next(
            row for row in trial["verified_mappings"] if row["role"] == "TOTAL_INTERBANK_PROVISION"
        )
        assert provision["report_norm_id"] == 5718


def test_annual_2025_pixel_dash_tamper_fails_closed() -> None:
    forged = mapping._annual_2025_review_blueprint()
    acb = next(document for document in forged["documents"] if document["bank_code"] == "ACB")
    dash = next(row for row in acb["mappings"] if row["value"]["line_index"] is None)
    dash["value"]["pixel_binding"]["rgb_sha256"] = "0" * 64
    with pytest.raises(
        mapping.InterbankDepositsLoans8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._review(forged, "annual-2025")
