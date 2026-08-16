from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_central_bank_deposits_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_central_bank_deposits_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_fixed_review_has_three_detailed_notes_and_two_explicit_schema_gaps() -> None:
    review = mapping._review_blueprint()
    positive = [document for document in review["documents"] if document["mappings"]]
    negative = [document for document in review["documents"] if not document["mappings"]]

    assert [document["bank_code"] for document in positive] == ["MBB", "VPB", "VIB"]
    assert len(negative) == 5
    assert sum(len(document["mappings"]) for document in positive) == 10
    assert sum(len(document["unmapped_rows"]) for document in positive) == 2
    assert positive[0]["unmapped_rows"][0]["label_pixel_transcription"] == (
        "Tiền gửi tại Ngân hàng Nhà nước Lào"
    )
    assert positive[1]["source_period"] == "2026-03-31"


def test_review_tamper_and_bool_type_poison_fail_closed() -> None:
    forged = mapping._review_blueprint()
    forged["documents"][1]["unmapped_rows"][0]["value"]["pixel_transcription"] = "934.856"
    with pytest.raises(
        mapping.CentralBankDeposits8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._review(forged)

    result = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    result["authority"]["current_reporting_period_only_mapped"] = 1
    with pytest.raises(
        mapping.CentralBankDeposits8BankCodexVerifiedMappingV1Error,
        match="identity or metrics",
    ):
        mapping._validate_result(result)


def test_persisted_result_locks_cluster_layout_numbers_schema_and_unmapped_rows() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 4,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 10,
        "partial_mapping_document_count": 1,
        "q1_source_period_caveat_document_count": 1,
        "unmapped_source_row_count": 2,
        "unresolved_document_count": 5,
    }
    mapped = [trial for trial in persisted["trials"] if trial["verified_mappings"]]
    assert [trial["document_provenance"] for trial in mapped] == ["MBB", "VPB", "VIB"]
    assert mapped[0]["status"] == "VERIFIED_BY_CODEX_WITH_UNMAPPED_SOURCE_ROWS"
    assert {row["report_norm_id"] for row in mapped[0]["verified_mappings"]} == {
        569,
        570,
        571,
        572,
    }
    assert {row["role"] for row in mapped[0]["unmapped_source_rows"]} == {
        "CENTRAL_BANK_LAOS",
        "CENTRAL_BANK_CAMBODIA",
    }
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in mapped
        for equation in trial["verified_accounting_equations"]
    )


def test_coordinated_rehash_cannot_promote_unmapped_geography_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    forged = copy.deepcopy(persisted)
    forged["trials"][1]["unmapped_source_rows"][0]["status"] = "VERIFIED_BY_CODEX"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "cbd8bcv1:result:" + mapping.canonical_json_sha256_v1(material)

    monkeypatch.setattr(
        mapping.scanner, "build_central_bank_deposits_full_document_scan_v1", lambda _: {}
    )
    monkeypatch.setattr(
        mapping,
        "build_central_bank_deposits_8bank_codex_verified_mapping_v1",
        lambda *args, **kwargs: persisted,
    )
    with pytest.raises(
        mapping.CentralBankDeposits8BankCodexVerifiedMappingV1Error,
        match="unmapped source row status",
    ):
        mapping.validate_central_bank_deposits_8bank_codex_verified_mapping_replay_v1(
            forged,
            {},
            {},
            {},
            {},
            {},
            crop_manifest_sha256="a" * 64,
            review_sha256="b" * 64,
        )


def test_annual_2025_review_covers_eight_unique_central_bank_notes() -> None:
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
        45,
        46,
        41,
        33,
        35,
        39,
        39,
        35,
    ]
    assert sum(len(document["mappings"]) for document in review["documents"]) == 28
    assert all(document["unmapped_rows"] == [] for document in review["documents"])


def test_annual_2025_geography_aggregates_and_hdb_ocr_disagreement_are_explicit() -> None:
    review = mapping._annual_2025_review_blueprint()
    aggregates = {}
    for document in review["documents"]:
        for row in document["mappings"]:
            if row["role"] == "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE":
                aggregates[document["bank_code"]] = row
    assert {bank: row["value"]["pixel_transcription"] for bank, row in aggregates.items()} == {
        "MBB": "2.258.533",
        "VCB": "233.253",
        "BID": "5.827.491",
    }
    assert [component["role"] for component in aggregates["BID"]["component_rows"]] == [
        "CENTRAL_BANK_CAMBODIA",
        "CENTRAL_BANK_LAOS",
    ]

    hdb = next(document for document in review["documents"] if document["bank_code"] == "HDB")
    foreign = next(row for row in hdb["mappings"] if row["role"] == "DEPOSIT_FOREIGN_CURRENCY")
    assert foreign["value"]["fresh_vietocr_challenger_expected"] == "B.416.558"
    assert foreign["value"]["pixel_transcription"] == "8.416.558"
    assert foreign["value"]["source_numeric_challenger_expected"] == "8.416.558"


def test_annual_2025_persisted_result_is_complete_and_nested_total_is_correct() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.ANNUAL_2025_RESULT_PATH).read_text()),
        "annual-2025",
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 10,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 28,
        "partial_mapping_document_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "unmapped_source_row_count": 0,
        "unresolved_document_count": 0,
    }
    assert all(trial["status"] == "VERIFIED_BY_CODEX" for trial in persisted["trials"])
    bid = next(trial for trial in persisted["trials"] if trial["document_provenance"] == "BID")
    assert bid["cluster_boundary"]["last_source_line_index"] == 50
    assert (
        next(row for row in bid["verified_mappings"] if row["role"] == "TOTAL")["normalized_value"]
        == 123_629_833
    )


def test_annual_2025_aggregate_component_tamper_fails_closed() -> None:
    forged = mapping._annual_2025_review_blueprint()
    mbb = next(document for document in forged["documents"] if document["bank_code"] == "MBB")
    aggregate = next(
        row for row in mbb["mappings"] if row["role"] == "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE"
    )
    aggregate["component_rows"][0]["value"]["pixel_transcription"] = "667.676"
    with pytest.raises(
        mapping.CentralBankDeposits8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._review(forged, "annual-2025")
