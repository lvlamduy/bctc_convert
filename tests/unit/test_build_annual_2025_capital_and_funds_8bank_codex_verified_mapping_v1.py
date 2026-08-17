from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_capital_and_funds_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_capital_and_funds_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_one_unique_annual_region_per_bank() -> None:
    review = builder.build_annual_2025_capital_and_funds_pixel_review_blueprint_v1()
    assert [item["bank_code"] for item in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_span"] for item in review["documents"]] == [
        [65, 66],
        [69, 70],
        [66, 67],
        [48, 49],
        [56, 57],
        [55, 56],
        [53, 54],
        [49, 50],
    ]
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])


def test_all_eight_tables_map_balances_after_full_page_rotated_redetection() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    for trial in result["trials"]:
        code = trial["document_provenance"]
        actual = {row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]}
        assert actual == builder._EXPECTED_IDS[code]
        if code in {"CTG", "BID", "VIB"}:
            assert trial["status"] == "VERIFIED_BY_CODEX_WITH_OPEN_SOURCE_ROWS"
            assert trial["rotated_rescue_line_count"] > 0
        else:
            assert trial["status"].startswith("VERIFIED_BY_CODEX")


def test_optional_source_columns_are_retained_without_forced_schema_mapping() -> None:
    result = _persisted()
    unresolved = {
        (trial["document_provenance"], row["source_label"])
        for trial in result["trials"]
        for row in trial["unmapped_source_rows"]
    }
    assert unresolved == {
        ("VPB", "Quỹ đầu tư phát triển"),
        ("HDB", "Cổ phiếu quỹ"),
        ("HDB", "Vốn đầu tư xây dựng cơ bản"),
        ("VCB", "Quỹ đầu tư phát triển"),
        ("CTG", "Quỹ đầu tư phát triển"),
        ("BID", "Quỹ đầu tư phát triển"),
        ("VIB", "Quỹ đầu tư phát triển"),
    }


def test_hdb_transformer_digit_error_is_vetoed_by_pixel_and_source_numeric_axis() -> None:
    hdb = next(item for item in _persisted()["trials"] if item["document_provenance"] == "HDB")
    component = next(
        component
        for mapping in hdb["verified_mappings"]
        for value in mapping["values"]
        for component in value["components"]
        if component["source_line_index"] == 86
    )
    assert component["fresh_vietocr_numeric_proposal"] == "835.956"
    assert component["pixel_transcription"] == "535.956"
    assert component["source_numeric_challenger"] == "535.956"
    assert component["normalized_value"] == 535_956


def test_every_verified_balance_closes_against_visible_equity_total() -> None:
    result = _persisted()
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 18
    assert all(item["computed_value"] == item["visible_total"] for item in equations)
    assert all(item["status"] == "VERIFIED_EXACT" for item in equations)


def test_persisted_result_matches_exact_live_replay() -> None:
    rebuilt = builder.build_live_annual_2025_capital_and_funds_8bank_codex_verified_mapping_v1()
    assert rebuilt == _persisted()
    assert rebuilt["result_id"] == (
        "annual2025caf8bcv1:result:bec70b336aac76091fd67757cae2e7ce6c3e9154fe6c8cd4030f7562634f37a5"
    )


def test_merged_bid_closing_cells_use_independent_word_boxes() -> None:
    bid = next(item for item in _persisted()["trials"] if item["document_provenance"] == "BID")
    values = {
        mapping["role"]: mapping["values"]
        for mapping in bid["verified_mappings"]
        if mapping["role"] in {"FINANCIAL_RESERVE", "CAPITAL_RESERVE"}
    }
    financial = next(
        value for value in values["FINANCIAL_RESERVE"] if value["axis_role"] == "CLOSING"
    )
    capital = next(value for value in values["CAPITAL_RESERVE"] if value["axis_role"] == "CLOSING")
    assert financial["components"][0]["word_indices"] == [0]
    assert capital["components"][0]["word_indices"] == [2]
    assert financial["normalized_value"] == 15_152_519
    assert capital["normalized_value"] == 11_582_717
    assert financial["components"][0]["coordinate_space"] == (
        "NORMALIZED_ROTATED_PAGE_TOP_LEFT_X_RIGHT_Y_DOWN"
    )
