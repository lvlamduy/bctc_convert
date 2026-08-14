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
    PROJECT_ROOT / "scripts/experiments/build_loan_type_8bank_codex_verified_mapping_v1.py"
)
REVIEW_PATH = PROJECT_ROOT / "docs/experiments/E-0054-loan-type-8bank-codex-pixel-review-v1.json"
RESULT_PATH = (
    PROJECT_ROOT / "docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v2.json"
)


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("loan_type_codex_mapping_v1_test", MODULE_PATH)
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
    value["result_id"] = "lt8bcv2:result:" + module.canonical_json_sha256_v1(material)


def test_fixed_review_and_result_are_closed_exact_and_bounded() -> None:
    module = _module()
    review = module._review(_json(REVIEW_PATH))
    result = module._validate_result(_json(RESULT_PATH))

    assert [bank["bank_code"] for bank in review["banks"]] == list(module.EXPECTED_DOCUMENT_ORDER)
    assert result["metrics"] == {
        "document_count": 8,
        "document_unique_structure_count": 8,
        "intermediate_source_only_total_verified_count": 1,
        "mapped_dash_cell_count": 10,
        "mapped_item_verified_by_codex_count": 46,
        "mapped_money_value_cell_count": 82,
        "mapped_percentage_corroboration_cell_count": 14,
        "negative_family_control_count": 32,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": 6,
        "unresolved_schema_semantic_row_count": 0,
    }
    assert [len(trial["verified_mappings"]) for trial in result["trials"]] == [
        8,
        6,
        7,
        5,
        5,
        7,
        5,
        3,
    ]
    assert all(trial["unresolved_rows"] == [] for trial in result["trials"])
    adjudicated = {
        (mapping["role"], mapping["report_norm_id"])
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        if mapping["role"] in {"GOVERNMENT_DIRECTED_OR_FUNDED", "UNMAPPED_OTHER_CREDIT"}
    }
    assert adjudicated == {
        ("GOVERNMENT_DIRECTED_OR_FUNDED", 6057),
        ("UNMAPPED_OTHER_CREDIT", 726),
    }
    dash_cells = [
        value
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["money_values"]
        if value["source_cell_status"] == "DASH"
    ]
    assert len(dash_cells) == 10
    assert all(
        value["semantic_proposal"] is None
        and value["source_line_index"] is None
        and value["normalized_numeric_value"] == 0
        for value in dash_cells
    )


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: value["banks"][0].__setitem__("physical_page", True),
        lambda value: value["banks"][0].__setitem__("physical_page", 17.0),
        lambda value: value["banks"][0]["rows"][6].__setitem__("mapping_disposition", "MAP"),
        lambda value: value["safety"].__setitem__("mapping_decided_by_text_similarity_alone", True),
    ),
)
def test_review_rejects_type_laundering_promotion_and_unsafe_authority(mutator: Any) -> None:
    module = _module()
    review = _json(REVIEW_PATH)
    mutator(review)
    with pytest.raises(module.LoanType8BankCodexVerifiedMappingV1Error):
        module._review(review)


def test_visible_dash_retains_source_status_and_normalizes_to_schema_zero() -> None:
    module = _module()
    graph_cell = {
        "lane_index": 0,
        "lane_type": "MONEY",
        "semantic_surface": None,
        "source_line_index": None,
        "status": "SEMANTIC_CELL_ABSENT_NOT_IMPUTED",
    }
    dash = {"lane_type": "MONEY", "pixel_transcription": "-", "status": "DASH"}

    output, arithmetic_value = module._graph_cell(graph_cell, dash, [])
    assert arithmetic_value == 0
    assert output["source_cell_status"] == "DASH"
    assert output["semantic_proposal"] is None
    assert output["normalized_numeric_value"] == 0

    with pytest.raises(module.LoanType8BankCodexVerifiedMappingV1Error, match="visible value"):
        module._graph_cell(
            graph_cell,
            {"lane_type": "MONEY", "pixel_transcription": "0", "status": "VALUE"},
            [],
        )


def test_coordinated_digit_tamper_and_candidate_relabel_fail_public_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    exact = module._validate_result(_json(RESULT_PATH))
    monkeypatch.setattr(
        module,
        "build_live_loan_type_8bank_codex_verified_mapping_v1",
        lambda: exact,
    )

    digit = copy.deepcopy(exact)
    digit["trials"][0]["verified_mappings"][0]["money_values"][0][
        "independent_pixel_transcription"
    ] = "742.220.651"
    _rehash(module, digit)
    with pytest.raises(
        module.LoanType8BankCodexVerifiedMappingV1Error,
        match="normalization drifted|replay exactly",
    ):
        module.validate_loan_type_8bank_codex_verified_mapping_replay_v1(digit)

    relabel = copy.deepcopy(exact)
    government = next(
        mapping
        for mapping in relabel["trials"][0]["verified_mappings"]
        if mapping["role"] == "GOVERNMENT_DIRECTED_OR_FUNDED"
    )
    government["report_norm_id"] = 720
    _rehash(module, relabel)
    with pytest.raises(module.LoanType8BankCodexVerifiedMappingV1Error, match="replay exactly"):
        module.validate_loan_type_8bank_codex_verified_mapping_replay_v1(relabel)


def test_result_rejects_typed_metric_laundering_even_after_rehash() -> None:
    module = _module()
    tampered = _json(RESULT_PATH)
    tampered["metrics"]["document_count"] = True
    _rehash(module, tampered)

    with pytest.raises(module.LoanType8BankCodexVerifiedMappingV1Error):
        module._validate_result(tampered)


def test_persisted_result_exactly_replays_every_live_input() -> None:
    module = _module()
    persisted = _json(RESULT_PATH)

    assert module.validate_loan_type_8bank_codex_verified_mapping_replay_v1(persisted) == persisted
