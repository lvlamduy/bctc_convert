"""Pinned five-repair registration and synthetic private-clone safety tests.

These fixtures exercise exact registered locators, not real PDF authentication.
Real restored PDF/SQLite proof is a separate bounded, non-release witness.
"""

from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as adapter
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

CONFIG = Path(__file__).resolve().parents[2] / "config/families"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CORRECTION = (
    Path(__file__).resolve().parents[2]
    / "docs/experiments/staging/family-36-pgb-render-receipt-metadata-correction-v1.json"
)
HISTORICAL_FIRST_FIFTEEN_AXIS_SHA = (
    "65e28415acdbc40158fc0b6c256e8970d0cced7d662b4b912c51be60b1a2c427"
)
CORRECTED_FIRST_FIFTEEN_AXIS_SHA = (
    "0bbd77cbf56376a79fcd47b185b2a0f577b29ff7c38ab4a507c013cd3d9d3b25"
)
NEW_AXIS_SHA = "f578fb2daab243c7c98675c685af95574808c63f4373d176ca2c84368dce84e0"
HISTORICAL_COMBINED_AXIS_SHA = (
    "d423ba692bd0d2668b4a34c325612f3c1b1abda61b4151204f6e34a7494591d5"
)
COMBINED_AXIS_SHA = "2ad0c7a2196605cbbcc58f14eb114925d60de867286490e048f8480076d51907"
HISTORICAL_SPEC_SHA = "6266031157ecaebd0e33e608cd3554c0330aa53b0a03ce3edcf7e75020f3061f"
SPEC_SHA = "1e1e46c301b67ba21cc829ad0f0b70263da47fa6af0f884bf676d088b01624cb"
PGB_SOURCE_SHA = "031a48ab510b901bef9b418fd70f6b10bc4c98d846f242d30b324d21ac9fd604"
PGB_HISTORICAL_RECEIPT_SHA = (
    "87af56b85eac5d429dae4d62fa8622a8a29632c89bd5d35000830ebee5844d35"
)
PGB_CANONICAL_RECEIPT_SHA = (
    "d12d81ec0e4545aaaddb9c0ceb174cad8d6a1a43a877cee9d5ef04d3dec37868"
)
PGB_HISTORICAL_REPAIR_ID = (
    "gjoefav1:source-repair:c85ec5959db7218399ef9f7f77e785b4063bf9258d6d1b2601b1f57ea4b52b2d"
)
PGB_CORRECTED_REPAIR_ID = (
    "gjoefav1:source-repair:f1879cc27122e54d55521a02bc334f9e2a88bae3382c4f8fcb981222197925b6"
)


def _spec():
    return json.loads((CONFIG / "tm-operating-expense-source-repair-v1.json").read_bytes())


def _compiled():
    configs = [
        json.loads((CONFIG / f"tm-operating-expense-{name}-v1.json").read_bytes())
        for name in ("topology", "evaluation", "schema-binding", "source-repair")
    ]
    return adapter.compile_gemini_json_operating_expense_family_specs_v1(*configs)


def _fixture(source_ordinal):
    """Synthetic pages at registered locators; every unregistered blank stays null."""

    repairs = _spec()["repairs"][15:]
    source_hashes = list(dict.fromkeys(r["source"]["source_sha256"] for r in repairs))
    selected = [r for r in repairs if r["source"]["source_sha256"] == source_hashes[source_ordinal]]
    locator = selected[0]["locator"]
    rows = [
        {"label_exact": f"synthetic row {i + 1}", "values_exact": ["17", None, None]}
        for i in range(max(r["locator"]["row_ordinal"] for r in selected) + 1)
    ]
    table = {"title_exact": "synthetic; not PDF proof", "rows": rows}
    tables = [{} for _ in range(int(locator["table_id"][1:]) - 1)] + [table]
    sections = [{} for _ in range(int(locator["section_id"][1:]) - 1)]
    sections.append({"title_exact": "synthetic", "tables": tables})
    pages = {locator["page_json_version_id"]: {"sections": sections}}
    region = {key: locator[key] for key in (
        "page_json_version_id", "physical_page", "section_id", "table_id"
    )}
    region.update(selected[0]["source"])
    return pages, [region], selected


def _apply(pages, regions):
    return adapter._apply_authenticated_source_repairs(
        pages=pages, regions=regions, compiled_specs=_compiled()
    )


def test_registration_corrects_only_pgb_receipt_metadata_and_preserves_five_additions():
    spec = _spec()
    assert len(adapter._validate_source_repairs(spec)) == 20
    assert canonical_json_sha256_v1(spec["repairs"][:15]) == CORRECTED_FIRST_FIFTEEN_AXIS_SHA
    assert canonical_json_sha256_v1(spec["repairs"][15:]) == NEW_AXIS_SHA
    assert spec["repair_axis_sha256"] == COMBINED_AXIS_SHA
    assert canonical_json_sha256_v1(spec) == SPEC_SHA
    assert _compiled()["operating_expense_source_repair_spec_sha256"] == SPEC_SHA

    pgb = [repair for repair in spec["repairs"] if repair["source"]["source_sha256"] == PGB_SOURCE_SHA]
    assert len(pgb) == 1
    assert pgb[0]["render"]["render_receipt_sha256"] == PGB_CANONICAL_RECEIPT_SHA
    assert pgb[0]["repair_id"] == PGB_CORRECTED_REPAIR_ID

    historical = copy.deepcopy(spec)
    historical_pgb = next(
        repair
        for repair in historical["repairs"]
        if repair["source"]["source_sha256"] == PGB_SOURCE_SHA
    )
    historical_pgb["render"]["render_receipt_sha256"] = PGB_HISTORICAL_RECEIPT_SHA
    historical_pgb["repair_id"] = PGB_HISTORICAL_REPAIR_ID
    historical["repair_axis_sha256"] = HISTORICAL_COMBINED_AXIS_SHA
    assert canonical_json_sha256_v1(historical["repairs"][:15]) == (
        HISTORICAL_FIRST_FIFTEEN_AXIS_SHA
    )
    assert canonical_json_sha256_v1(historical["repairs"][15:]) == NEW_AXIS_SHA
    assert canonical_json_sha256_v1(historical["repairs"]) == HISTORICAL_COMBINED_AXIS_SHA
    assert canonical_json_sha256_v1(historical) == HISTORICAL_SPEC_SHA

    with pytest.raises(ValueError, match="source-repair identity drifted"):
        stale_identity = copy.deepcopy(spec)
        stale_pgb = next(
            repair
            for repair in stale_identity["repairs"]
            if repair["source"]["source_sha256"] == PGB_SOURCE_SHA
        )
        stale_pgb["repair_id"] = PGB_HISTORICAL_REPAIR_ID
        adapter._validate_source_repairs(stale_identity)

    with pytest.raises(ValueError, match="axis seal drifted"):
        stale_axis = copy.deepcopy(spec)
        stale_axis["repair_axis_sha256"] = HISTORICAL_COMBINED_AXIS_SHA
        adapter._validate_source_repairs(stale_axis)

    for repair in spec["repairs"][15:]:
        assert repair["before_exact"] is None
        assert repair["after_exact"] == repair["observed_pdf_glyph"] == "-"
        assert repair["repair_kind"] == "MONEY_CELL_VISIBLE_DASH"
        assert repair["locator"]["column_ordinal"] == 2


def test_pgb_registered_receipt_hash_requires_the_canonical_final_lf():
    receipt_bytes = (FIXTURES / "f36-pgb-p040-render-receipt.canonical.json").read_bytes()
    assert len(receipt_bytes) == 685
    assert receipt_bytes.endswith(b"\n")
    assert canonical_json_bytes_v1(json.loads(receipt_bytes)) == receipt_bytes
    assert sha256(receipt_bytes).hexdigest() == PGB_CANONICAL_RECEIPT_SHA
    assert sha256(receipt_bytes[:-1]).hexdigest() == PGB_HISTORICAL_RECEIPT_SHA


def test_pgb_metadata_correction_receipt_preserves_failed_gate_and_requires_fresh_run():
    correction = json.loads(CORRECTION.read_bytes())
    material = {key: value for key, value in correction.items() if key != "receipt_id"}
    assert correction["receipt_id"] == (
        "f36pgbcorrectionv1:receipt:" + canonical_json_sha256_v1(material)
    )
    assert correction["status"] == "FAMILY_LOCAL_METADATA_CORRECTION_NO_RELEASE_PROMOTION"
    assert correction["cause"] == {
        "canonical_byte_count": 685,
        "canonical_final_byte_hex": "0a",
        "canonical_receipt_sha256": PGB_CANONICAL_RECEIPT_SHA,
        "historical_noncanonical_byte_count": 684,
        "historical_noncanonical_receipt_sha256": PGB_HISTORICAL_RECEIPT_SHA,
        "historical_preimage_rule": (
            "OFFICIAL_CANONICAL_BYTES_WITH_EXACTLY_THE_FINAL_LF_REMOVED"
        ),
        "official_serializer": (
            "bctc_ai.source_structure.contracts_v1.canonical_json_bytes_v1"
        ),
    }
    assert correction["correction"]["before"]["repair_id"] == PGB_HISTORICAL_REPAIR_ID
    assert correction["correction"]["after"]["repair_id"] == PGB_CORRECTED_REPAIR_ID
    assert correction["correction"]["new_five_repair_axis_sha256_preserved"] == NEW_AXIS_SHA
    assert {
        item["artifact"]: item["sha256"]
        for item in correction["historical_failed_gate_evidence"]
    } == {
        "FAILURE_AND_REPAIR_AUTH_DIAGNOSIS.md": (
            "b372d7c728fb267640b8fe4bdfbac9d6b593285de9484127372712c18d299fe7"
        ),
        "process-result.json": (
            "7e3e8c24e83c51e2cf524ccd14839f669c965c3f3d334de069f64346212ad8d6"
        ),
        "receipt-newline-preimage-proof.json": (
            "aa1d1cd3996ac064ae2a4a370d8637145f03618ad360cbd14f5b6aba5db07c30"
        ),
    }
    assert "FRESH_AUTHENTICATION_AND_ALL_DEPENDENT_RUN_RECEIPTS_REQUIRED" in (
        correction["preserved_invariants"]
    )


@pytest.mark.parametrize("source_ordinal", range(4))
def test_registered_private_clone_changes_only_target_cells_and_replays_once(source_ordinal):
    pages, regions, repairs = _fixture(source_ordinal)
    before = canonical_json_bytes_v1(pages)
    projected, receipts = _apply(pages, regions)
    expected = copy.deepcopy(pages)
    for repair in repairs:
        loc = repair["locator"]
        _, table = adapter._source_table(
            expected[loc["page_json_version_id"]],
            section_id=loc["section_id"], table_id=loc["table_id"],
        )
        table["rows"][loc["row_ordinal"] - 1]["values_exact"][1] = "-"
    assert projected == expected
    assert canonical_json_bytes_v1(pages) == before
    assert len(receipts) == len(repairs)
    assert [r["repair"]["repair_id"] for r in receipts] == [r["repair_id"] for r in repairs]
    assert len({r["receipt_id"] for r in receipts}) == len(repairs)
    for receipt in receipts:
        material = {k: v for k, v in receipt.items() if k != "receipt_id"}
        assert receipt["receipt_id"] == (
            "gjoefav1:source-repair-receipt:" + canonical_json_sha256_v1(material)
        )
        assert receipt["source_repair_spec_sha256"] == SPEC_SHA
    assert _apply(pages, regions) == (projected, receipts)
    with pytest.raises(ValueError, match="before-image drifted"):
        _apply(projected, regions)


@pytest.mark.parametrize("source_ordinal", range(4))
def test_registered_repairs_reject_missing_page_duplicate_region_and_wrong_identity(source_ordinal):
    pages, regions, _ = _fixture(source_ordinal)
    with pytest.raises(ValueError, match="outside selected document"):
        _apply({}, regions)
    with pytest.raises(ValueError, match="outside its selected table"):
        _apply(pages, regions + copy.deepcopy(regions))
    wrong_name = copy.deepcopy(regions)
    wrong_name[0]["source_logical_name"] += ".wrong"
    with pytest.raises(ValueError, match="logical source identity drifted"):
        _apply(pages, wrong_name)
    wrong_hash = copy.deepcopy(regions)
    wrong_hash[0]["source_sha256"] = "f" * 64
    assert _apply(pages, wrong_hash) == (pages, [])


@pytest.mark.parametrize("bad_before", [0, "0", "", "-", False])
def test_null_only_registration_never_repairs_a_different_typed_before_image(bad_before):
    pages, regions, repairs = _fixture(0)
    loc = repairs[0]["locator"]
    _, table = adapter._source_table(
        pages[loc["page_json_version_id"]],
        section_id=loc["section_id"], table_id=loc["table_id"],
    )
    table["rows"][loc["row_ordinal"] - 1]["values_exact"][1] = bad_before
    before = canonical_json_bytes_v1(pages)
    with pytest.raises(ValueError, match="before-image drifted"):
        _apply(pages, regions)
    assert canonical_json_bytes_v1(pages) == before
