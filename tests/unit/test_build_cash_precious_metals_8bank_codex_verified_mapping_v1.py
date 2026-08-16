from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_cash_precious_metals_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_cash_precious_metals_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_fixed_pixel_review_has_three_detailed_notes_and_five_negative_controls() -> None:
    review = mapping._review_blueprint()
    positive = [document for document in review["documents"] if document["mappings"]]
    negative = [document for document in review["documents"] if not document["mappings"]]

    assert [document["bank_code"] for document in positive] == ["MBB", "VPB", "VIB"]
    assert len(negative) == 5
    assert sum(len(document["mappings"]) for document in positive) == 12
    assert all(len(document["equations"]) == 1 for document in positive)
    assert positive[1]["source_period"] == "2026-03-31"


def test_review_tamper_and_bool_type_poison_fail_closed() -> None:
    forged = mapping._review_blueprint()
    forged["documents"][1]["mappings"][0]["value"]["pixel_transcription"] = "4.534.512"
    with pytest.raises(
        mapping.CashPreciousMetals8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        mapping._review(forged)

    result = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    result["authority"]["current_reporting_period_only_mapped"] = 1
    with pytest.raises(
        mapping.CashPreciousMetals8BankCodexVerifiedMappingV1Error,
        match="identity or metrics",
    ):
        mapping._validate_result(result)


def test_persisted_result_shape_locks_pixels_numbers_accounting_and_schema() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 3,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 12,
        "q1_source_period_caveat_document_count": 1,
        "unresolved_document_count": 5,
    }
    mapped = [trial for trial in persisted["trials"] if trial["verified_mappings"]]
    assert [trial["document_provenance"] for trial in mapped] == ["MBB", "VPB", "VIB"]
    assert all(
        {row["report_norm_id"] for row in trial["verified_mappings"]} == {561, 562, 563, 565}
        for trial in mapped
    )
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in mapped
        for equation in trial["verified_accounting_equations"]
    )


def test_coordinated_result_rehash_cannot_replace_verified_digit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    forged = copy.deepcopy(persisted)
    row = forged["trials"][1]["verified_mappings"][0]
    row["normalized_value"] += 1
    row["source_value"]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "cpm8bcv1:result:" + mapping.canonical_json_sha256_v1(material)

    monkeypatch.setattr(
        mapping.scanner, "build_cash_precious_metals_full_document_scan_v1", lambda _: {}
    )
    monkeypatch.setattr(
        mapping,
        "build_cash_precious_metals_8bank_codex_verified_mapping_v1",
        lambda *args, **kwargs: persisted,
    )
    with pytest.raises(
        mapping.CashPreciousMetals8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        mapping.validate_cash_precious_metals_8bank_codex_verified_mapping_replay_v1(
            forged,
            {},
            {},
            {},
            {},
            {},
            crop_manifest_sha256="a" * 64,
            review_sha256="b" * 64,
        )


def test_annual_2025_review_covers_eight_unique_notes_and_all_visible_children() -> None:
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
    assert sum(len(document["mappings"]) for document in review["documents"]) == 35
    assert all(len(document["equations"]) == 1 for document in review["documents"])


def test_annual_2025_hdb_vietocr_disagreement_and_ctg_omitted_dash_are_explicit() -> None:
    review = mapping._annual_2025_review_blueprint()
    hdb = next(document for document in review["documents"] if document["bank_code"] == "HDB")
    hdb_foreign = next(row for row in hdb["mappings"] if row["role"] == "CASH_FOREIGN")
    assert hdb_foreign["value"] == {
        "fresh_vietocr_challenger_expected": "1.194.005",
        "line_index": 42,
        "pixel_transcription": "1.194.085",
        "resolution": (
            "INDEPENDENT_PIXEL_TRANSCRIPTION_CORROBORATED_BY_PROVIDER_AND_EXACT_ACCOUNTING_EQUATION"
        ),
        "source_numeric_challenger_expected": "1.194.085",
    }

    ctg = next(document for document in review["documents"] if document["bank_code"] == "CTG")
    nonmonetary = next(row for row in ctg["mappings"] if row["role"] == "NONMONETARY_GOLD")
    assert nonmonetary["value"]["pixel_transcription"] == "-"
    assert nonmonetary["value"]["render_cell"]["status"] == (
        "VISIBLE_DASH_WITHOUT_PROVIDER_DETECTION_BOUND_BY_ROW_AND_NUMERIC_LANE"
    )


def test_annual_2025_persisted_result_is_complete_and_accounting_closed() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.ANNUAL_2025_RESULT_PATH).read_text()),
        "annual-2025",
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 8,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 35,
        "q1_source_period_caveat_document_count": 0,
        "unresolved_document_count": 0,
    }
    assert all(trial["status"] == "VERIFIED_BY_CODEX" for trial in persisted["trials"])
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in persisted["trials"]
        for equation in trial["verified_accounting_equations"]
    )


def test_annual_2025_review_tamper_fails_closed() -> None:
    forged = mapping._annual_2025_review_blueprint()
    hdb = next(document for document in forged["documents"] if document["bank_code"] == "HDB")
    hdb_foreign = next(row for row in hdb["mappings"] if row["role"] == "CASH_FOREIGN")
    hdb_foreign["value"]["pixel_transcription"] = "1.194.005"
    with pytest.raises(
        mapping.CashPreciousMetals8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        mapping._review(forged, "annual-2025")
