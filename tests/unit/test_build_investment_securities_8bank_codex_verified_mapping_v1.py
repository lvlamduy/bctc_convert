from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_investment_securities_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_investment_securities_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
mapping = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = mapping
_SPEC.loader.exec_module(mapping)


def _persisted() -> dict[str, object]:
    return json.loads((mapping.PROJECT_ROOT / mapping.RESULT_PATH).read_text())


def test_review_records_all_eight_unique_regions_and_layout_variants() -> None:
    review = mapping._review_blueprint()
    by_code = {document["bank_code"]: document for document in review["documents"]}

    assert list(by_code) == list(mapping.EXPECTED_DOCUMENT_ORDER)
    assert {document["layout"] for document in by_code.values()} == {
        "AFS_AND_HTM_TWO_DATE_COLUMNS_WITHOUT_LOCAL_UNIT",
        "AFS_MAIN_TABLE_THEN_PROVISION_MOVEMENT_AND_QUALITY_ALTERNATE_VIEW",
        "IMPLICIT_FAMILY_OWNER_AFS_ONLY_WITH_TWO_TCTD_COMPONENT_ROWS",
        "ONE_PAGE_AFS_AND_HTM_TWO_DATE_COLUMNS_WITH_EXPLICIT_GROSS_NET_ROWS",
        "ONE_PAGE_AFS_AND_HTM_WITH_COMBINED_NET_TOTAL",
        "ONE_PAGE_AFS_AND_HTM_WITH_RELATIVE_PERIOD_AXES",
        "ONE_PAGE_AFS_HTM_AND_VAMC_WITH_NET_BRANCH_ROWS",
        "TWO_PAGE_AFS_THEN_HTM_WITH_DIRECT_ISSUER_CHILDREN_AND_PRINTED_GROSS_NET",
    }
    assert (
        sum(document["disposition"] == "UNRESOLVED_MAPPING" for document in by_code.values()) == 1
    )
    assert by_code["BID"]["unresolved_items"][0]["reason"] == (
        "LOCAL_OR_REPLAY_BOUND_DOCUMENT_UNIT_NOT_ADMITTED"
    )
    assert by_code["VIB"]["family_boundary"]["first_item"]["pixel_transcription"] == (
        "CHỨNG KHOÁN ĐẦU TƯ SẴN SÀNG ĐỂ BÁN"
    )


def test_persisted_result_has_exact_status_mapping_and_accounting_metrics() -> None:
    result = mapping._validate_result(_persisted())

    assert result["metrics"] == {
        "accounting_equation_verified_count": 27,
        "dash_cell_verified_as_zero_count": 15,
        "document_count": 8,
        "document_unresolved_count": 1,
        "document_verified_count": 7,
        "mapped_value_cell_count": 168,
        "mapping_verified_count": 84,
        "unresolved_mapping_count": 2,
    }
    by_code = {trial["bank_provenance"]: trial for trial in result["trials"]}
    assert [
        code
        for code in mapping.EXPECTED_DOCUMENT_ORDER
        if by_code[code]["status"] == "VERIFIED_BY_CODEX"
    ] == ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "VIB"]
    assert by_code["BID"]["status"] == "UNRESOLVED_MAPPING"
    assert {row["report_norm_id"] for row in by_code["CTG"]["verified_mappings"]} == (
        mapping._EXPECTED_IDS["CTG"]
    )
    assert all(
        equation["computed_total"] == equation["visible_total"]
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    )


def test_review_tamper_and_bool_type_poison_fail_closed() -> None:
    forged_review = mapping._review_blueprint()
    forged_review["documents"][0]["pages"][0]["rows"][0]["values"][0]["pixel_transcription"] = (
        "154.846.879"
    )
    with pytest.raises(
        mapping.InvestmentSecurities8BankCodexVerifiedMappingV1Error,
        match="differs from fixed ledger",
    ):
        mapping._review(forged_review)

    forged_result = _persisted()
    forged_result["authority"]["dash_zero_requires_visible_pixel"] = 1
    with pytest.raises(
        mapping.InvestmentSecurities8BankCodexVerifiedMappingV1Error,
        match="identity, authority or metrics",
    ):
        mapping._validate_result(forged_result)


def test_coordinated_rehash_cannot_promote_unresolved_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = _persisted()
    forged = copy.deepcopy(persisted)
    forged["trials"][6] = copy.deepcopy(forged["trials"][5])
    forged["trials"][6]["bank_provenance"] = "BID"
    forged["trials"][6]["document_ordinal"] = 7
    forged["trials"][6]["verified_mappings"] = []
    forged["metrics"] = mapping._metrics(forged["trials"])
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0067:result:" + mapping.canonical_json_sha256_v1(material)

    monkeypatch.setattr(
        mapping,
        "build_live_investment_securities_8bank_codex_verified_mapping_v1",
        lambda: persisted,
    )
    with pytest.raises(
        mapping.InvestmentSecurities8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        mapping.validate_investment_securities_8bank_codex_verified_mapping_replay_v1(forged)


def test_unrelated_global_schema_extension_keeps_exact_used_bindings_replayable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = _persisted()
    extended = copy.deepcopy(persisted)
    extended["input_refs"]["tm_schema_projection_sha256"] = "f" * 64
    material = copy.deepcopy(extended)
    material.pop("result_id")
    extended["result_id"] = "e0067:result:" + mapping.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        mapping,
        "build_live_investment_securities_8bank_codex_verified_mapping_v1",
        lambda: extended,
    )
    assert (
        mapping.validate_investment_securities_8bank_codex_verified_mapping_replay_v1(persisted)
        == persisted
    )

    extended["trials"][0]["verified_mappings"][0]["canonical_name"] += " drift"
    material = copy.deepcopy(extended)
    material.pop("result_id")
    extended["result_id"] = "e0067:result:" + mapping.canonical_json_sha256_v1(material)
    with pytest.raises(
        mapping.InvestmentSecurities8BankCodexVerifiedMappingV1Error,
        match="does not replay exactly",
    ):
        mapping.validate_investment_securities_8bank_codex_verified_mapping_replay_v1(persisted)


def test_vib_aggregation_gap_is_retained_without_mapping_808() -> None:
    result = mapping._validate_result(_persisted())
    vib = next(trial for trial in result["trials"] if trial["bank_provenance"] == "VIB")

    assert {row["report_norm_id"] for row in vib["verified_mappings"]} == {807, 824}
    assert vib["unresolved_items"] == [
        {
            "page_sequence": 36,
            "reason": "TWO_SOURCE_COMPONENTS_REQUIRE_EXPLICIT_AGGREGATION_INTO_REPORT_NORM_ID_808",
            "source_label": (
                "Trái phiếu và chứng chỉ tiền gửi do các TCTD khác trong nước phát hành"
            ),
        }
    ]
