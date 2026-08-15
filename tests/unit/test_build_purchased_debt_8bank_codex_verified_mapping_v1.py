from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_purchased_debt_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_purchased_debt_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def _persisted() -> dict[str, object]:
    return json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())


def test_review_records_four_layout_variants_and_exact_family_boundaries() -> None:
    review = mapping._review_blueprint()
    by_code = {document["bank_code"]: document for document in review["documents"]}

    assert list(by_code) == list(mapping.EXPECTED_DOCUMENT_ORDER)
    assert {
        code
        for code, document in by_code.items()
        if document["disposition"] == "VERIFIED_UNIQUE_COMPLETE_PURCHASED_DEBT_REGION"
    } == {"MBB", "VPB", "HDB", "VIB"}
    assert {
        code
        for code, document in by_code.items()
        if document["disposition"] == "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE"
    } == {"ACB", "VCB", "CTG", "BID"}
    assert all(
        document["family_boundary"]["first_item"]["pixel_transcription"]
        .casefold()
        .endswith("hoạt động mua nợ")
        for document in by_code.values()
        if document["family_boundary"] is not None
    )
    assert all(
        "chứng khoán đầu tư"
        in document["family_boundary"]["next_family_boundary"]["pixel_transcription"].casefold()
        for document in by_code.values()
        if document["family_boundary"] is not None
    )
    hdb_ids = {row["report_norm_id"] for row in by_code["HDB"]["pages"][0]["rows"]}
    assert hdb_ids == {801, 802, 803, 5738, 5739}
    assert len(by_code["VPB"]["optional_equations"]) == 2
    assert len(by_code["VIB"]["optional_equations"]) == 1


def test_persisted_result_has_exact_mappings_dash_cells_and_equations() -> None:
    result = mapping._validate_result(_persisted())

    assert result["metrics"] == {
        "accounting_equation_verified_count": 19,
        "core_accounting_equation_verified_count": 16,
        "dash_cell_verified_as_zero_count": 5,
        "document_count": 8,
        "document_not_observed_count": 4,
        "document_verified_count": 4,
        "mapped_value_cell_count": 34,
        "mapping_verified_count": 17,
        "optional_check_equation_count": 3,
        "unresolved_mapping_count": 0,
    }
    by_code = {trial["bank_provenance"]: trial for trial in result["trials"]}
    assert [
        code
        for code in mapping.EXPECTED_DOCUMENT_ORDER
        if by_code[code]["status"] == "VERIFIED_BY_CODEX"
    ] == ["MBB", "VPB", "HDB", "VIB"]
    assert {row["report_norm_id"] for row in by_code["HDB"]["verified_mappings"]} == {
        801,
        802,
        803,
        5738,
        5739,
    }
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in result["trials"]
        for equation in (trial["verified_accounting_equations"] + trial["optional_check_equations"])
    )
    assert (
        sum(
            value["source_cell_status"] == "DASH"
            for trial in result["trials"]
            for row in trial["verified_mappings"]
            for value in row["source_values"]
        )
        == 5
    )


def test_review_tamper_and_bool_type_poison_fail_closed() -> None:
    forged_review = mapping._review_blueprint()
    forged_review["documents"][1]["pages"][0]["rows"][0]["values"][0]["pixel_transcription"] = (
        "2.247.702"
    )
    with pytest.raises(
        mapping.PurchasedDebt8BankCodexVerifiedMappingV1Error,
        match="differs from the fixed ledger",
    ):
        mapping._review(forged_review)

    forged_result = _persisted()
    forged_result["authority"]["dash_zero_requires_visible_pixel"] = 1
    with pytest.raises(
        mapping.PurchasedDebt8BankCodexVerifiedMappingV1Error,
        match="identity, authority or metrics",
    ):
        mapping._validate_result(forged_result)


def test_coordinated_rehash_cannot_promote_not_observed_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = _persisted()
    forged = copy.deepcopy(persisted)
    forged["trials"][0] = copy.deepcopy(forged["trials"][1])
    forged["trials"][0]["bank_provenance"] = "ACB"
    forged["trials"][0]["document_ordinal"] = 1
    forged["metrics"] = mapping._metrics(forged["trials"])
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0066:result:" + mapping.canonical_json_sha256_v1(material)

    monkeypatch.setattr(
        mapping,
        "build_live_purchased_debt_8bank_codex_verified_mapping_v1",
        lambda: persisted,
    )
    with pytest.raises(
        mapping.PurchasedDebt8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        mapping.validate_purchased_debt_8bank_codex_verified_mapping_replay_v1(forged)


def test_optional_branches_are_check_only_not_schema_mappings() -> None:
    result = mapping._validate_result(_persisted())
    by_code = {trial["bank_provenance"]: trial for trial in result["trials"]}

    assert {equation["role"] for equation in by_code["VPB"]["optional_check_equations"]} == {
        "CURRENT_PROVISION_MOVEMENT_CHECK_ONLY",
        "COMPARATIVE_PROVISION_MOVEMENT_CHECK_ONLY",
    }
    assert [equation["role"] for equation in by_code["VIB"]["optional_check_equations"]] == [
        "HISTORICAL_2017_ACQUISITION_CHECK_ONLY"
    ]
    assert all(
        equation["mapping_authority"] is False
        for code in ("VPB", "VIB")
        for equation in by_code[code]["optional_check_equations"]
    )
    assert all(
        row["report_norm_id"] in {801, 802, 803, 5738, 5739}
        for trial in result["trials"]
        for row in trial["verified_mappings"]
    )
