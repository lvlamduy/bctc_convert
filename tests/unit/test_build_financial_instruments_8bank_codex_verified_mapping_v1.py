from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_financial_instruments_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_financial_instruments_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def test_review_has_three_unique_tables_and_five_bounded_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["page_span"] for item in documents] == [
        None,
        None,
        [86, 86],
        None,
        [44, 45],
        [51, 51],
        None,
        None,
    ]


def test_result_has_exact_denominator_and_schema_union() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 12,
        "authenticated_pixel_dash_zero_count": 1,
        "bound_report_detailed_table_absence_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 64,
        "open_fair_value_group_count": 3,
        "q1_source_period_caveat_document_count": 1,
        "source_only_control_row_count": 3,
        "verified_value_cell_count": 55,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1305,
        1306,
        1307,
        1308,
        1309,
        1310,
        1311,
        1312,
        1313,
        1314,
        1315,
        1318,
        1319,
        1320,
        1321,
        1322,
        1323,
        1324,
        1325,
        1326,
        1328,
        1329,
        1331,
        1332,
    ]


def test_equations_close_and_vpb_q1_is_not_relabelled_q2() -> None:
    result = _result()
    for trial in result["trials"]:
        assert all(
            equation["computed_value"] == equation["visible_value"]
            for equation in trial["verified_accounting_equations"]
        )
    vp = _trial(result, "VPB")
    assert vp["source_period"] == "2026-03-31"
    assert vp["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"


def test_fair_value_asterisks_remain_open_and_never_become_zero() -> None:
    result = _result()
    for code in ("VPB", "VCB", "CTG"):
        trial = _trial(result, code)
        open_rows = [row for row in trial["verified_source_only_rows"] if row["open_mapping"]]
        assert len(open_rows) == 1
        assert open_rows[0]["status"] == "OPEN_UNAVAILABLE_FAIR_VALUE_NOT_ZERO"
        assert open_rows[0]["values"] == []
        assert open_rows[0]["affected_source_labels"]


def test_ctg_visible_book_dash_is_pixel_bound_zero() -> None:
    ctg = _trial(_result(), "CTG")
    derivative = next(
        mapping
        for mapping in ctg["verified_mappings"]
        if mapping["role"] == "BOOK_ASSET_DERIVATIVE"
    )
    value = derivative["values"][0]
    assert value["normalized_value"] == 0
    assert (
        value["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
    )


def test_public_replay_rejects_coordinated_asterisk_promotion() -> None:
    forged = copy.deepcopy(_result())
    vp = _trial(forged, "VPB")
    row = next(row for row in vp["verified_source_only_rows"] if row["open_mapping"])
    row["open_mapping"] = False
    row["status"] = "VERIFIED_SOURCE_ONLY_ACCOUNTING_CONTROL"
    forged["metrics"]["open_fair_value_group_count"] -= 1
    forged["metrics"]["source_only_control_row_count"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0099:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.FinancialInstruments8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_financial_instruments_8bank_codex_verified_mapping_v1(forged)
