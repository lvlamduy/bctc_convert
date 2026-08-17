from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "scripts/experiments/build_loan_enterprise_8bank_codex_verified_mapping_v1.py"
)
REVIEW_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0056-loan-enterprise-8bank-codex-pixel-review-v1.json"
)


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "loan_enterprise_codex_mapping_v1_test", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _rehash(module: ModuleType, value: dict[str, Any]) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "le8bcv1:result:" + module.canonical_json_sha256_v1(material)


@pytest.fixture(scope="module")
def live() -> tuple[ModuleType, dict[str, Any]]:
    module = _module()
    return module, module.build_live_loan_enterprise_8bank_codex_verified_mapping_v1()


def test_live_result_maps_all_safe_rows_and_retains_every_unresolved_boundary(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, result = live
    assert result["result_id"] == (
        "le8bcv1:result:a0d9c7cb7211241f30ec315fb80a73272e4055068774c8f01e677a8986785aae"
    )
    assert result["metrics"] == {
        "document_count": 8,
        "document_no_complete_region_count": 4,
        "document_unique_structure_count": 4,
        "mapped_item_verified_by_codex_count": 44,
        "mapped_money_value_cell_count": 88,
        "mapped_percentage_corroboration_cell_count": 72,
        "negative_family_control_count": 32,
        "source_group_equation_verified_count": 6,
        "source_only_total_verified_count": 4,
        "transformer_disagreement_preserved_count": 28,
        "typed_dash_cell_verified_count": 1,
        "unresolved_schema_semantic_row_count": 0,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        module.EXPECTED_DOCUMENT_ORDER
    )
    assert [
        (
            trial["document_provenance"],
            trial["physical_page"],
            len(trial["verified_mappings"]),
            len(trial["unresolved_rows"]),
        )
        for trial in result["trials"]
    ] == [
        ("ACB", None, 0, 0),
        ("MBB", 32, 14, 0),
        ("VPB", 43, 14, 0),
        ("HDB", 26, 8, 0),
        ("VCB", None, 0, 0),
        ("CTG", None, 0, 0),
        ("BID", None, 0, 0),
        ("VIB", 34, 8, 0),
    ]
    assert all(trial["whole_document_family_absence_claim"] is False for trial in result["trials"])


def test_wave1_semantic_graph_contract_is_independent_of_schema_growth() -> None:
    module = _module()
    semantic = module._json_bytes(
        module._fixed_bytes(module.SEMANTIC_INDEX_PATH, module.EXPECTED_INDEX_SHA256),
        "semantic",
    )
    scan = module._scanner().build_loan_enterprise_full_document_scan_v1(semantic)
    serialized_scan = json.dumps(scan, ensure_ascii=False, sort_keys=True)
    assert "report_norm_id" not in serialized_scan
    assert "schema_revision" not in serialized_scan
    observed = []
    for trial in scan["trials"]:
        matcher = trial["matcher_result"]
        observed.append(
            (
                trial["document_provenance"],
                matcher["status"],
                [module.canonical_json_sha256_v1(graph) for graph in matcher.get("graphs", [])],
            )
        )
    assert observed == [
        ("ACB", "UNRESOLVED_NO_COMPLETE_REGION", []),
        (
            "MBB",
            "ACCEPTED_UNIQUE_VARIANT_GRAPH",
            ["aa6a520e03eaa8a7b77a78b005c7e7ba525a7484e459ac117ecfb6046189d6dc"],
        ),
        (
            "VPB",
            "ACCEPTED_UNIQUE_VARIANT_GRAPH",
            ["ee5ce61f97a46fe27950a711334b89eff1a70fb88d65f007df5ce2b89d73d9cd"],
        ),
        (
            "HDB",
            "ACCEPTED_UNIQUE_VARIANT_GRAPH",
            ["3b81bc38cd8ae0f1a0c379f5ea8f895c95c37b5bbec79f0c248f07e585b83fb4"],
        ),
        ("VCB", "UNRESOLVED_NO_COMPLETE_REGION", []),
        ("CTG", "UNRESOLVED_NO_COMPLETE_REGION", []),
        ("BID", "UNRESOLVED_NO_COMPLETE_REGION", []),
        (
            "VIB",
            "ACCEPTED_UNIQUE_VARIANT_GRAPH",
            ["78c0494a725f3884ba2759db239922558affc4295a64e710d07a8d396d7c8159"],
        ),
    ]


def test_schema_ids_are_live_parent_children_and_foreign_population_reuses_exact_schema_item(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    _, result = live
    observed = {
        (mapping["role"], mapping["report_norm_id"])
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert observed == {
        ("STATE_ENTERPRISE", 767),
        ("STATE_OWNED_SINGLE_MEMBER_LLC", 769),
        ("STATE_CONTROLLED_MULTI_MEMBER_LLC", 770),
        ("OTHER_LLC", 771),
        ("STATE_CONTROLLED_JOINT_STOCK", 772),
        ("OTHER_JOINT_STOCK", 773),
        ("PRIVATE_ENTERPRISE", 774),
        ("COOPERATIVE", 776),
        ("PARTNERSHIP", 778),
        ("FOREIGN_INVESTED_ENTERPRISE", 779),
        ("HOUSEHOLD_INDIVIDUAL", 780),
        ("ADMIN_PUBLIC_ASSOCIATION", 781),
        ("OTHER", 782),
        ("MARGIN_AND_SECURITIES_ADVANCE", 5748),
        ("FOREIGN_BRANCH_LOANS_SOURCE_ONLY", 6058),
    }
    mbb = result["trials"][1]
    assert mbb["unresolved_rows"] == []
    foreign = next(
        item
        for item in mbb["verified_mappings"]
        if item["role"] == "FOREIGN_BRANCH_LOANS_SOURCE_ONLY"
    )
    assert foreign["report_norm_id"] == 6058
    assert foreign["schema_parent_report_norm_id"] == 727
    by_label = {item["source_label"]: item for item in mbb["source_group_equations"]}
    assert by_label["Cho vay các TCKT"]["mapping_status"] == (
        "SOURCE_ONLY_GRAPH_NODE_RETAINED_FOR_CHECK"
    )
    assert by_label["Cho vay các TCKT"]["schema_equivalence_report_norm_id"] is None
    assert by_label["Cho vay cá nhân"]["schema_equivalence_report_norm_id"] == 780
    assert by_label["Cho vay khác"]["schema_equivalence_report_norm_id"] == 782
    assert (
        by_label["Cho vay tại Chi nhánh và ngân hàng con nước ngoài"][
            "schema_equivalence_report_norm_id"
        ]
        == 6058
    )
    assert all(
        by_label[label]["mapping_status"] == "VERIFIED_NON_ADDITIVE_SCHEMA_EQUIVALENCE"
        for label in (
            "Cho vay cá nhân",
            "Cho vay khác",
            "Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
        )
    )


def test_grouped_mbb_equations_and_margin_are_independently_closed(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    _, result = live
    mbb = result["trials"][1]
    assert [item["kind"] for item in mbb["source_group_equations"]] == [
        "PARENT_EQUALS_GRAPH_CHILD_ROLES",
        "PARENT_EQUALS_GRAPH_CHILD_ROLES",
        "PARENT_EQUALS_GRAPH_CHILD_ROLES",
        "PARENT_EQUALS_SOURCE_ONLY_CHILDREN",
        "CORE_SUBTOTAL_EQUALS_POPULATION_BRANCHES",
        "GRAND_TOTAL_EQUALS_CORE_PLUS_MARGIN",
    ]
    assert mbb["source_group_equations"][-2]["visible_values"] == [
        "1210726423",
        "98.63",
        "1068978785",
        "98.61",
    ]
    assert mbb["source_group_equations"][-1]["visible_values"] == [
        "1227554477",
        "100.00",
        "1084019370",
        "100.00",
    ]


def test_pixel_digit_and_dash_corrections_preserve_raw_semantic_disagreement(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    _, result = live
    hdb = result["trials"][3]
    private = next(
        item for item in hdb["verified_mappings"] if item["role"] == "PRIVATE_ENTERPRISE"
    )
    current = private["money_values"][0]
    assert current["semantic_proposal"] is None
    assert current["independent_pixel_transcription"] == "-"
    assert current["normalized_value"] == 0
    assert current["value_status"] == "DASH"
    assert current["verification_status"] == "VERIFIED_VISIBLE_PIXEL_DASH"
    assert current["pixel_binding"]["rgb_sha256"] == (
        "599a2c07ee5e4072e51f66057edebb4557f8662ed98c51c0f4ef31b5727b9570"
    )

    vib = result["trials"][7]
    joint_stock = next(
        item for item in vib["verified_mappings"] if item["role"] == "OTHER_JOINT_STOCK"
    )
    assert joint_stock["money_values"][0]["semantic_proposal"] == "97.043.85"
    assert joint_stock["money_values"][0]["independent_pixel_transcription"] == "97.043.851"
    assert joint_stock["money_values"][0]["normalized_value"] == 97043851


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: value["documents"][1].__setitem__("physical_page", True),
        lambda value: value["documents"][1].__setitem__(
            "schema_unresolved_roles", ["FOREIGN_BRANCH_LOANS_SOURCE_ONLY"]
        ),
        lambda value: value["documents"][1]["source_group_equations"][1].__setitem__(
            "schema_equivalence_report_norm_id", 782
        ),
        lambda value: value["documents"][3]["pixel_accounting"]["typed_dash_cells"][0].__setitem__(
            "status", "OBSERVED_ZERO"
        ),
        lambda value: value["safety"].__setitem__("mapping_decided_by_text_similarity_alone", True),
    ),
)
def test_pixel_review_rejects_type_laundering_dash_drift_and_unsafe_authority(
    mutator: Any,
) -> None:
    module = _module()
    review = _json(REVIEW_PATH)
    mutator(review)
    with pytest.raises(module.LoanEnterprise8BankCodexVerifiedMappingV1Error):
        module._review(review)


def test_pixel_binding_digest_tamper_fails_against_the_exact_render(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, _ = live
    semantic = module._json_bytes(
        module._fixed_bytes(module.SEMANTIC_INDEX_PATH, module.EXPECTED_INDEX_SHA256), "semantic"
    )
    crop = module._json_bytes(
        module._fixed_bytes(module.CROP_MANIFEST_PATH, module.EXPECTED_CROP_MANIFEST_SHA256),
        "crop",
    )
    review = _json(REVIEW_PATH)
    review["documents"][3]["transformer_disagreements"][0]["pixel_binding"]["rgb_sha256"] = "0" * 64
    scan = module._scanner().build_loan_enterprise_full_document_scan_v1(semantic)
    schema_authority, schema_by_id = module._authority_snapshot(PROJECT_ROOT)

    with pytest.raises(
        module.LoanEnterprise8BankCodexVerifiedMappingV1Error,
        match="pixel-only evidence crop changed",
    ):
        module.build_loan_enterprise_8bank_codex_verified_mapping_v1(
            semantic,
            crop,
            scan,
            review,
            schema_authority,
            schema_by_id,
            crop_manifest_sha256=module.EXPECTED_CROP_MANIFEST_SHA256,
            review_sha256=module.REVIEW_SHA256,
        )


def test_group_equation_tamper_fails_even_with_valid_review_shape(
    live: tuple[ModuleType, dict[str, Any]],
) -> None:
    module, _ = live
    semantic = module._json_bytes(
        module._fixed_bytes(module.SEMANTIC_INDEX_PATH, module.EXPECTED_INDEX_SHA256), "semantic"
    )
    crop = module._json_bytes(
        module._fixed_bytes(module.CROP_MANIFEST_PATH, module.EXPECTED_CROP_MANIFEST_SHA256),
        "crop",
    )
    review = _json(REVIEW_PATH)
    review["documents"][1]["source_group_equations"][0]["visible_values"][0] = "721497619"
    scanner = module._scanner()
    scan = scanner.build_loan_enterprise_full_document_scan_v1(semantic)
    schema_authority, schema_by_id = module._authority_snapshot(PROJECT_ROOT)
    with pytest.raises(
        module.LoanEnterprise8BankCodexVerifiedMappingV1Error,
        match="visible source-group value is absent from semantic page|equation does not close",
    ):
        module.build_loan_enterprise_8bank_codex_verified_mapping_v1(
            semantic,
            crop,
            scan,
            review,
            schema_authority,
            schema_by_id,
            crop_manifest_sha256=module.EXPECTED_CROP_MANIFEST_SHA256,
            review_sha256=module.REVIEW_SHA256,
        )


def test_coordinated_digit_status_and_metric_rehash_fail_closed(
    live: tuple[ModuleType, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, exact = live
    monkeypatch.setattr(
        module,
        "build_live_loan_enterprise_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )

    digit = copy.deepcopy(exact)
    digit["trials"][7]["verified_mappings"][4]["money_values"][0][
        "independent_pixel_transcription"
    ] = "97.043.85"
    _rehash(module, digit)
    with pytest.raises(
        module.LoanEnterprise8BankCodexVerifiedMappingV1Error, match="replay exactly"
    ):
        module.validate_loan_enterprise_8bank_codex_verified_mapping_replay_v1(digit)

    relabelled = copy.deepcopy(exact)
    foreign = next(
        item
        for item in relabelled["trials"][1]["verified_mappings"]
        if item["role"] == "FOREIGN_BRANCH_LOANS_SOURCE_ONLY"
    )
    foreign["report_norm_id"] = 999_999
    _rehash(module, relabelled)
    with pytest.raises(module.LoanEnterprise8BankCodexVerifiedMappingV1Error):
        module.validate_loan_enterprise_8bank_codex_verified_mapping_replay_v1(relabelled)

    typed = copy.deepcopy(exact)
    typed["metrics"]["document_count"] = 8.0
    _rehash(module, typed)
    with pytest.raises(module.LoanEnterprise8BankCodexVerifiedMappingV1Error):
        module._validate_result(typed)
