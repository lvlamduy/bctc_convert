from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_contingent_liabilities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_contingent_liabilities_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def test_review_has_five_unique_detailed_notes_and_three_bounded_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["page_span"] for item in documents] == [
        [26, 26],
        [51, 51],
        [68, 68],
        None,
        None,
        [48, 48],
        None,
        [50, 50],
    ]


def test_result_has_exact_denominator_and_schema_union() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 34,
        "bound_report_detailed_note_absence_count": 3,
        "document_count": 8,
        "document_unique_region_count": 5,
        "mapping_verified_count": 47,
        "open_source_row_count": 13,
        "q1_source_period_caveat_document_count": 1,
        "source_only_control_row_count": 9,
        "verified_value_cell_count": 92,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1294,
        1295,
        1296,
        1297,
        1298,
        1299,
        1300,
        1301,
        1302,
        1303,
        1304,
        5741,
        5742,
        5743,
        5744,
    ]


def test_every_accounting_equation_closes_and_q1_is_not_relabelled_q2() -> None:
    result = _result()
    for trial in result["trials"]:
        assert all(
            equation["computed_value"] == equation["visible_value"]
            for equation in trial["verified_accounting_equations"]
        )
    vp = _trial(result, "VPB")
    assert vp["source_period"] == "2026-03-31"
    assert vp["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"


def test_vib_maps_net_axis_and_retains_gross_margin_controls() -> None:
    vib = _trial(_result(), "VIB")
    assert vib["mapped_report_norm_ids"] == [
        1294,
        1295,
        1300,
        1301,
        1302,
        1304,
        5741,
        5742,
    ]
    assert all(not row["open_mapping"] for row in vib["verified_source_only_rows"])
    assert any(
        equation["name"] == "FAMILY_GROSS_MINUS_MARGIN_EQUALS_FAMILY_NET"
        for equation in vib["verified_accounting_equations"]
    )


def test_public_replay_rejects_coordinated_open_row_promotion() -> None:
    forged = copy.deepcopy(_result())
    vp = _trial(forged, "VPB")
    row = next(row for row in vp["verified_source_only_rows"] if row["open_mapping"])
    row["open_mapping"] = False
    row["status"] = "VERIFIED_SOURCE_ONLY_ACCOUNTING_CONTROL"
    forged["metrics"]["open_source_row_count"] -= 1
    forged["metrics"]["source_only_control_row_count"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0098:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.ContingentLiabilities8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_contingent_liabilities_8bank_codex_verified_mapping_v1(forged)
