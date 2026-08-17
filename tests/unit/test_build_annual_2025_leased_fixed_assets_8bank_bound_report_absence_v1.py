from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live_result() -> dict[str, object]:
    return builder.build_live_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1()


def test_all_eight_annual_reports_have_bounded_absence(
    live_result: dict[str, object],
) -> None:
    assert live_result["metrics"] == {
        "bound_report_absence_count": 8,
        "document_count": 8,
        "mapping_verified_count": 0,
        "negative_control_line_count": 30,
        "open_review_item_count": 0,
        "rotated_rescue_line_count": 3338,
    }
    assert [trial["document_provenance"] for trial in live_result["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert all(trial["mappings"] == [] for trial in live_result["trials"])
    assert all(
        trial["whole_document_scan_metrics"]
        == {"complete_region_count": 0, "near_region_count": 0, "owner_candidate_count": 0}
        for trial in live_result["trials"]
    )


def test_family_boundaries_are_selected_by_structure_not_bank_routes(
    live_result: dict[str, object],
) -> None:
    assert [
        (
            trial["previous_family_boundary"]["page_sequence"],
            trial["next_family_boundary"]["page_sequence"],
        )
        for trial in live_result["trials"]
    ] == [(55, 56), (58, 60), (53, 54), (41, 42), (48, 49), (48, 49), (47, 48), (42, 43)]
    assert all(
        trial["boundary_order_status"] == "TANGIBLE_PRECEDES_INTANGIBLE_WITH_NO_LEASED_REGION"
        for trial in live_result["trials"]
    )
    assert all(
        trial["next_family_boundary"]["normalized_pixel_transcription"] == "tai san co dinh vo hinh"
        for trial in live_result["trials"]
    )
    assert (
        live_result["authority"]["bank_filename_note_or_page_used_as_matching_or_routing"] is False
    )


def test_family_local_schema_projection_ignores_unrelated_global_order_changes(
    live_result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, by_id = builder._authority_snapshot(builder.PROJECT_ROOT)
    original = by_id[899]
    shifted = dict(by_id)
    shifted[899] = SimpleNamespace(
        canonical_name=original.canonical_name,
        children=original.children,
        display_order=999_999,
        hierarchy_level=original.hierarchy_level,
        parent_id=original.parent_id,
        schema_id=original.schema_id,
        statement_type=original.statement_type,
    )
    monkeypatch.setattr(builder, "_authority_snapshot", lambda _root: (authority, shifted))

    assert builder._schema_family() == live_result["schema_family"]


def test_public_replay_rejects_a_coordinated_rehash(
    live_result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live_result)
    forged["trials"][0]["negative_controls"] = []
    forged["metrics"]["negative_control_line_count"] -= 7
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_leased_fixed_assets_8bank_bound_report_absence_v1",
        lambda: live_result,
    )

    with pytest.raises(
        builder.Annual2025LeasedFixedAssetsAbsenceV1Error,
        match="does not replay exactly",
    ):
        builder.validate_annual_2025_leased_fixed_assets_8bank_bound_report_absence_replay_v1(
            forged
        )


def test_persisted_result_equals_live_replay(live_result: dict[str, object]) -> None:
    scanner = builder._scanner()
    persisted, _ = scanner._support()._fixed_json(builder.RESULT_PATH)

    assert persisted == live_result
