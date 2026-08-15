from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_loan_geography_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_loan_geography_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def test_pixel_review_separates_exact_broad_and_segment_populations() -> None:
    review = mapping._review_blueprint()
    by_code = {document["bank_code"]: document for document in review["documents"]}

    assert [
        code
        for code in mapping.EXPECTED_DOCUMENT_ORDER
        if by_code[code]["disposition"] == "VERIFIED_EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    ] == ["MBB", "VIB"]
    assert by_code["VCB"]["disposition"] == (
        "UNRESOLVED_SEGMENT_REPORT_NEGATIVE_CONTROL_NO_LOAN_GEOGRAPHY"
    )
    assert (
        sum(
            document["disposition"]
            in {
                "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
                "UNRESOLVED_BROAD_MIXED_LOAN_POPULATION_SCOPE",
            }
            for document in review["documents"]
        )
        == 5
    )
    assert all(
        comparison["difference"] > 0
        for document in review["documents"]
        for comparison in document["scope_comparisons"]
        if comparison["relation"] == "BROADER"
    )


def test_review_tamper_and_bool_type_poison_fail_closed() -> None:
    forged = mapping._review_blueprint()
    forged["documents"][1]["pages"][0]["cells"][0]["value"]["pixel_transcription"] = "1.218.258.772"
    with pytest.raises(
        mapping.LoanGeography8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        mapping._review(forged)

    result = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    result["authority"]["dash_zero_requires_visible_pixel"] = 1
    with pytest.raises(
        mapping.LoanGeography8BankCodexVerifiedMappingV1Error,
        match="identity, authority or metrics",
    ):
        mapping._validate_result(result)


def test_persisted_result_maps_only_exact_mbb_and_vib_rows() -> None:
    persisted = mapping._validate_result(
        json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    )

    assert persisted["metrics"] == {
        "accounting_equation_verified_count": 3,
        "broad_scope_unresolved_document_count": 5,
        "document_count": 8,
        "document_verified_count": 2,
        "mapped_value_cell_count": 6,
        "mapping_verified_count": 4,
        "segment_report_negative_control_count": 1,
        "unresolved_document_count": 6,
    }
    verified = [trial for trial in persisted["trials"] if trial["status"] == "VERIFIED_BY_CODEX"]
    assert [trial["bank_provenance"] for trial in verified] == ["MBB", "VIB"]
    assert all(
        {mapping_row["report_norm_id"] for mapping_row in trial["verified_mappings"]} == {5752, 765}
        for trial in verified
    )
    vib = verified[1]
    foreign = next(row for row in vib["verified_mappings"] if row["report_norm_id"] == 765)
    assert [
        (value["normalized_value"], value["source_cell_status"])
        for value in foreign["source_values"]
    ] == [
        (0, "DASH"),
        (0, "DASH"),
    ]
    assert all(
        equation["computed_total"] == equation["visible_or_derived_total"]
        for trial in verified
        for equation in trial["verified_accounting_equations"]
    )


def test_coordinated_result_rehash_cannot_promote_broad_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())
    forged = copy.deepcopy(persisted)
    forged["trials"][0]["status"] = "VERIFIED_BY_CODEX"
    forged["trials"][0]["unresolved_reason"] = None
    forged["trials"][0]["verified_mappings"] = copy.deepcopy(
        forged["trials"][1]["verified_mappings"]
    )
    forged["metrics"] = mapping._metrics(forged["trials"])
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0065:result:" + mapping.canonical_json_sha256_v1(material)

    monkeypatch.setattr(
        mapping,
        "build_live_loan_geography_8bank_codex_verified_mapping_v1",
        lambda: persisted,
    )
    with pytest.raises(
        mapping.LoanGeography8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        mapping.validate_loan_geography_8bank_codex_verified_mapping_replay_v1(forged)
