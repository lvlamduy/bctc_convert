from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_customer_collateral_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_customer_collateral_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def test_review_has_three_unique_regions_and_five_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["page_span"] for item in documents] == [
        None,
        None,
        [67, 67],
        None,
        [47, 47],
        None,
        None,
        [49, 49],
    ]


def test_result_has_exact_denominator_and_schema_union() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 6,
        "bound_report_detailed_note_absence_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 15,
        "open_source_row_count": 4,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 30,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1280,
        1281,
        1282,
        1283,
        1284,
        1285,
        1286,
        1288,
    ]


def test_source_only_rows_still_close_customer_parent_totals() -> None:
    result = _result()
    assert [row["row_id"] for row in _trial(result, "VCB")["verified_source_only_rows"]] == [
        "CC-001"
    ]
    assert [row["row_id"] for row in _trial(result, "VIB")["verified_source_only_rows"]] == [
        "CC-002",
        "CC-003",
        "CC-004",
    ]
    for code in ("VPB", "VCB", "VIB"):
        equations = _trial(result, code)["verified_accounting_equations"]
        assert [item["period_axis"] for item in equations] == ["CURRENT", "COMPARATIVE"]
        assert all(item["computed_value"] == item["visible_value"] for item in equations)


def test_vib_combined_gold_fx_papers_is_not_narrowed() -> None:
    vib = _trial(_result(), "VIB")
    row = next(item for item in vib["verified_source_only_rows"] if item["row_id"] == "CC-004")
    assert row["label_evidence"][0]["pixel_transcription"] == "Vàng, ngoại tệ, giấy tờ có giá"
    assert row["reason"] == (
        "COMBINED_GOLD_FX_VALUABLE_PAPERS_CANNOT_BE_NARROWED_TO_VALUABLE_PAPERS"
    )
    assert 1286 not in vib["mapped_report_norm_ids"]


def test_public_replay_rejects_coordinated_source_only_promotion() -> None:
    forged = copy.deepcopy(_result())
    vib = _trial(forged, "VIB")
    row = vib["verified_source_only_rows"].pop()
    row["schema_binding"] = {"report_norm_id": 1286}
    row["status"] = "VERIFIED_BY_CODEX"
    vib["verified_mappings"].append(row)
    forged["metrics"]["mapping_verified_count"] += 1
    forged["metrics"]["open_source_row_count"] -= 1
    forged["metrics"]["verified_value_cell_count"] += 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0096:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.CustomerCollateral8BankCodexVerifiedMappingV1Error,
        match="result ID drifted",
    ):
        builder.validate_live_customer_collateral_8bank_codex_verified_mapping_v1(forged)
