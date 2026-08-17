from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_annual_2025_other_assets_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_other_assets_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict[str, object]:
    return builder.build_live_annual_2025_other_assets_8bank_codex_verified_mapping_v1()


def test_all_eight_documents_have_one_unique_annual_region(
    live: dict[str, object],
) -> None:
    assert live["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in live["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert all(
        trial["source_period"] == "2025-12-31"
        and trial["whole_document_uniqueness"]["complete_region_count"] == 1
        and trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
        for trial in live["trials"]
    )


def test_exact_schema_coverage_and_all_accounting_equations_close(
    live: dict[str, object],
) -> None:
    for trial in live["trials"]:
        actual = {
            mapping["schema_binding"]["report_norm_id"] for mapping in trial["verified_mappings"]
        }
        assert actual == builder._EXPECTED_IDS[trial["document_provenance"]]
        assert all(
            equation["status"] == "VERIFIED_EXACT"
            and equation["computed_total"] == equation["visible_total"]
            for equation in trial["verified_accounting_equations"]
        )
        assert all(
            mapping["status"] == "VERIFIED_BY_CODEX" for mapping in trial["verified_mappings"]
        )


def test_every_unmapped_source_row_remains_open(live: dict[str, object]) -> None:
    rows = [row for trial in live["trials"] for row in trial["unmapped_source_rows"]]
    assert [row["item_id"] for row in rows] == [
        f"A2025-OA-{ordinal:03d}" for ordinal in range(1, 36)
    ]
    assert all(row["status"] == "UNRESOLVED" for row in rows)


def test_exact_replay_rejects_coordinated_mapping_rehash(
    live: dict[str, object],
) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    base = builder._configure_base()
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + base.canonical_json_sha256_v1(material)

    with pytest.raises(builder.Annual2025OtherAssets8BankError):
        builder.validate_annual_2025_other_assets_8bank_codex_verified_mapping_replay_v1(forged)


def test_persisted_review_and_result_equal_live_bytes(live: dict[str, object]) -> None:
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert persisted_review == builder.build_annual_2025_other_assets_pixel_review_blueprint_v1()
    assert persisted_result == live
