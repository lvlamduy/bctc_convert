from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = (
    _ROOT / "scripts/experiments/build_trading_securities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_trading_securities_8bank_codex_verified_mapping_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))


def test_review_blueprint_preserves_pdf_order_layout_axes_and_q1_caveat() -> None:
    review = builder._review_blueprint()

    assert [item["document_provenance"] for item in review["documents"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [item["page_sequence"] for item in review["documents"]] == [
        16,
        31,
        40,
        24,
        30,
        37,
        20,
        None,
    ]
    assert review["documents"][1]["layout_variant"].startswith("LISTED_UNLISTED_CLASSIFICATION")
    assert review["documents"][2]["source_period"] == "2026-03-31"
    assert review["documents"][7]["whole_document_family_absence_claim"] is False
    assert review["documents"][7]["disposition"].startswith(
        "UNRESOLVED_NO_TRADING_SECURITIES_REGION"
    )


def test_current_persisted_result_replays_mapping_equations_and_boundaries() -> None:
    result = builder.validate_trading_securities_8bank_codex_verified_mapping_replay_v1(
        _persisted()
    )

    assert result["result_id"] == (
        "ts8bcv1:result:ec5bd96012040b1544f84325ec4fa67cc079267061b5db636398e15c6703a176"
    )
    assert result["metrics"] == {
        "accounting_equation_verified_count": 20,
        "document_count": 8,
        "document_unique_region_count": 7,
        "mapping_verified_count": 58,
        "q1_source_period_caveat_document_count": 1,
        "unresolved_document_count": 1,
    }
    assert [trial["status"] for trial in result["trials"]] == [
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "UNRESOLVED",
    ]
    assert [
        trial["cluster_boundary"]["last_item_role"] if trial["cluster_boundary"] else None
        for trial in result["trials"]
    ] == ["NET", "NET", "NET", "NET", "NET", "NET", "NET", None]
    assert all(
        trial["layout"]["row_order_preserved_from_pdf"] is True for trial in result["trials"][:7]
    )

    mbb = result["trials"][1]
    gross = next(item for item in mbb["verified_mappings"] if item["role"] == "GROSS")
    assert gross["report_norm_id"] == 626
    assert gross["independent_pixel_label"] is None
    assert gross["topology"] == ("UNLABELED_TOTAL_AFTER_LAST_EQUITY_CHILD_BEFORE_PROVISION")
    assert gross["normalized_value"] == 8_888_529

    hdb = result["trials"][3]
    debt = next(item for item in hdb["verified_mappings"] if item["role"] == "DEBT")
    assert debt["topology"] == "TRAILING_PARENT_TOTAL_AFTER_LAST_DEBT_CHILD"
    assert debt["normalized_value"] == 10_761_164

    assert result["trials"][7]["whole_document_family_absence_claim"] is False


def test_review_and_result_coordinated_rehashes_do_not_authenticate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = builder._review_blueprint()
    forged_review = copy.deepcopy(review)
    forged_review["documents"][0]["mappings"][0]["value"]["pixel_transcription"] = "999"
    review_material = copy.deepcopy(forged_review)
    review_material.pop("review_id")
    forged_review["review_id"] = "e0059:pixel-review:" + builder.canonical_json_sha256_v1(
        review_material
    )
    with pytest.raises(builder.TradingSecurities8BankCodexVerifiedMappingV1Error, match="ledger"):
        builder._review(forged_review)

    persisted = _persisted()
    forged_result = copy.deepcopy(persisted)
    forged_result["trials"][0]["verified_mappings"][0]["normalized_value"] = 999
    result_material = copy.deepcopy(forged_result)
    result_material.pop("result_id")
    forged_result["result_id"] = "ts8bcv1:result:" + builder.canonical_json_sha256_v1(
        result_material
    )
    monkeypatch.setattr(
        builder,
        "build_live_trading_securities_8bank_codex_verified_mapping_v1",
        _persisted,
    )
    with pytest.raises(builder.TradingSecurities8BankCodexVerifiedMappingV1Error, match="replay"):
        builder.validate_trading_securities_8bank_codex_verified_mapping_replay_v1(forged_result)


def test_signed_money_and_typed_identity_fail_closed() -> None:
    assert builder._money("1.234.567") == 1_234_567
    assert builder._money("(171.845)") == -171_845
    assert builder._money("-") == 0
    with pytest.raises(builder.TradingSecurities8BankCodexVerifiedMappingV1Error):
        builder._money(123)
