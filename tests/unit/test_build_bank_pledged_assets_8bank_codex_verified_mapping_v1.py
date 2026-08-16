from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_bank_pledged_assets_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_bank_pledged_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def test_review_has_two_unique_regions_and_six_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["page_span"] for item in documents] == [
        None,
        None,
        [67, 67],
        None,
        None,
        None,
        None,
        [49, 49],
    ]


def test_result_has_exact_denominator_and_schema_union() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 6,
        "bound_report_detailed_note_absence_count": 6,
        "document_count": 8,
        "document_unique_region_count": 2,
        "mapping_verified_count": 5,
        "open_source_row_count": 3,
        "q1_source_period_caveat_document_count": 1,
        "source_hierarchy_double_count_contradiction_document_count": 1,
        "source_presentation_reconciliation_count": 2,
        "verified_value_cell_count": 10,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [1289, 1290, 1291, 1293]


def test_vpb_preserves_printed_hierarchy_contradiction_without_false_equation() -> None:
    vp = _trial(_result(), "VPB")
    assert vp["source_hierarchy_status"] == (
        "SOURCE_PRINTED_TOTAL_DOUBLE_COUNTS_COMBINED_PARENT_AND_IN_THAT_CHILDREN"
    )
    assert [row["row_id"] for row in vp["verified_source_only_rows"]] == ["BPA-001"]
    assert len(vp["verified_accounting_equations"]) == 4
    assert all(
        item["computed_value"] == item["visible_value"]
        for item in vp["verified_accounting_equations"]
    )
    assert len(vp["verified_source_presentation_reconciliations"]) == 2
    assert all(
        item["status"] == "SOURCE_PRESENTATION_REPRODUCED_NOT_ACCOUNTING_IDENTITY"
        for item in vp["verified_source_presentation_reconciliations"]
    )


def test_vib_generic_pledged_and_discounted_rows_are_not_narrowed() -> None:
    vib = _trial(_result(), "VIB")
    assert [row["row_id"] for row in vib["verified_source_only_rows"]] == [
        "BPA-002",
        "BPA-003",
    ]
    assert vib["mapped_report_norm_ids"] == [1289]
    assert all(
        item["computed_value"] == item["visible_value"]
        for item in vib["verified_accounting_equations"]
    )


def test_public_replay_rejects_coordinated_source_only_promotion() -> None:
    forged = copy.deepcopy(_result())
    vib = _trial(forged, "VIB")
    row = vib["verified_source_only_rows"].pop()
    row["schema_binding"] = {"report_norm_id": 1291}
    row["status"] = "VERIFIED_BY_CODEX"
    vib["verified_mappings"].append(row)
    forged["metrics"]["mapping_verified_count"] += 1
    forged["metrics"]["open_source_row_count"] -= 1
    forged["metrics"]["verified_value_cell_count"] += 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0097:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.BankPledgedAssets8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_bank_pledged_assets_8bank_codex_verified_mapping_v1(forged)
