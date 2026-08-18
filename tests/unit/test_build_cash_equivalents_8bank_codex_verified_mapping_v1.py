from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_cash_equivalents_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_cash_equivalents_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_review_finds_six_unique_regions_and_two_bounded_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["bank_code"] for item in documents] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_span"] for item in documents] == [
        [8, 8],
        [50, 50],
        [66, 66],
        None,
        [40, 40],
        [47, 47],
        None,
        [45, 45],
    ]


def test_persisted_result_has_exact_denominator_and_schema_union() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 12,
        "blank_optional_axis_count": 2,
        "detailed_note_not_present_document_count": 2,
        "document_count": 8,
        "document_unique_region_count": 6,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 31,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 60,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == list(range(1248, 1255))


def test_acb_total_before_components_is_reconstructed_and_closes() -> None:
    acb = _result()["trials"][0]
    total = _mapping(acb, "TOTAL")
    assert [(item["axis_role"], item["normalized_value"]) for item in total["values"]] == [
        ("COMPARATIVE_PERIOD", 125_090_372),
        ("CURRENT_PERIOD", 116_533_043),
    ]
    assert [len(item["component_evidence"]) for item in total["values"]] == [4, 3]
    assert len(acb["verified_accounting_equations"]) == 2


def test_optional_securities_axes_stay_blank_instead_of_becoming_zero() -> None:
    result = _result()
    acb_security = _mapping(result["trials"][0], "SECURITIES")
    vcb_security = _mapping(result["trials"][4], "SECURITIES")
    assert acb_security["blank_axes"] == ["CURRENT_PERIOD"]
    assert [(item["axis_role"], item["normalized_value"]) for item in acb_security["values"]] == [
        ("COMPARATIVE_PERIOD", 1_455_373)
    ]
    assert vcb_security["blank_axes"] == ["COMPARATIVE_PERIOD"]
    assert [(item["axis_role"], item["normalized_value"]) for item in vcb_security["values"]] == [
        ("CURRENT_PERIOD", 952_227)
    ]


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0092:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.CashEquivalents8BankCodexVerifiedMappingV1Error,
        match="result identity drifted",
    ):
        builder.validate_live_cash_equivalents_8bank_codex_verified_mapping_v1(forged)
