from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.source_structure import semantic_local_accounting_observation_v2 as semantic_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    FamilySpecV1,
    RowRoleSpecV1,
    local_accounting_family_spec_sha256_v1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
)


def _box(x: int, y: int, width: int = 120, height: int = 24) -> list[int]:
    return [x, y, x + width, y + height]


def _synthetic_page() -> tuple[dict, dict]:
    records = [
        ("CHO VAY KHÁCH HÀNG", "PPOCR_OWNER_IS_FORBIDDEN", _box(100, 100, 250)),
        (
            "Phân tích dư nợ theo thời hạn gốc của khoản vay",
            "PPOCR_BRANCH_IS_FORBIDDEN",
            _box(100, 140, 410),
        ),
        ("TRANSFORMER_DATE_UNUSED", "30/06/2026", _box(500, 180)),
        ("TRANSFORMER_DATE_UNUSED", "31/12/2025", _box(700, 180)),
        ("Triệu đồng", "PPOCR_UNIT_IS_FORBIDDEN", _box(500, 210)),
        ("Triệu đồng", "PPOCR_UNIT_IS_FORBIDDEN", _box(700, 210)),
        ("Nợ ngắn hạn", "PPOCR_ROW_IS_FORBIDDEN", _box(100, 250)),
        ("TRANSFORMER_NUMBER_UNUSED", "10", _box(500, 250)),
        ("TRANSFORMER_NUMBER_UNUSED", "1", _box(700, 250)),
        ("Nợ trung hạn", "PPOCR_ROW_IS_FORBIDDEN", _box(100, 290)),
        ("TRANSFORMER_NUMBER_UNUSED", "20", _box(500, 290)),
        ("TRANSFORMER_NUMBER_UNUSED", "2", _box(700, 290)),
        ("Nợ dài hạn", "PPOCR_ROW_IS_FORBIDDEN", _box(100, 330)),
        ("TRANSFORMER_NUMBER_UNUSED", "30", _box(500, 330)),
        ("TRANSFORMER_NUMBER_UNUSED", "3", _box(700, 330)),
        ("TRANSFORMER_NUMBER_UNUSED", "60", _box(500, 370)),
        ("TRANSFORMER_NUMBER_UNUSED", "6", _box(700, 370)),
    ]
    samples = []
    atoms = []
    lines = []
    for index, (transformer_text, ppocr_text, bbox) in enumerate(records):
        canonical = [coordinate * 10 for coordinate in bbox]
        atom_id = f"ssv1:atom:{index:064x}"
        samples.append(
            {
                "normalized_prediction": transformer_text,
                "source_line_index": index,
                "source_bbox_raw_pixels": bbox,
                "source_atom": {
                    "source_atom_id": atom_id,
                    "line_index": index,
                    "pixel_bbox": bbox,
                    "canonical_bbox_mpt": canonical,
                },
            }
        )
        atoms.append(
            {
                "source_local_id": atom_id,
                "kind": "LINE",
                "authority": "AUTHENTICATED_PRIMARY",
                "upstream_locator": {"kind": "OCR_LINE_INDEX", "line_index": index},
                "pixel_bbox": bbox,
                "canonical_bbox_mpt": canonical,
            }
        )
        lines.append(
            {
                "raw_text": ppocr_text,
                "raw_pixel_bbox": bbox,
                "canonical_bbox_mpt": canonical,
            }
        )
    projection = {
        "source_local_page_id": "ssv2:page:" + "1" * 64,
        "page_result_sha256": "2" * 64,
        "page_result": {"lines": lines},
        "neutral_page_v1": {"atoms": atoms},
    }
    binding = {
        "format_version": "GENERIC_VIETOCR_ALL_LINE_PAGE_BINDING_V2",
        "samples": samples,
    }
    return projection, binding


@pytest.fixture
def authenticated_inputs(monkeypatch: pytest.MonkeyPatch) -> tuple[dict, dict, object]:
    projection, binding = _synthetic_page()
    receipt = object()
    monkeypatch.setattr(
        semantic_v2,
        "validate_source_evidence_projection_v2",
        lambda value: value,
    )

    def validate_page(value: object, source: object, authority: object) -> dict:
        assert value is binding
        assert source is projection
        assert authority is receipt
        return binding

    monkeypatch.setattr(
        semantic_v2,
        "validate_vietocr_semantic_page_binding_v2",
        validate_page,
    )
    return projection, binding, receipt


def _index(*extra_specs: FamilySpecV1):
    return (
        LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        *extra_specs,
    )


def _assemble(
    authenticated_inputs: tuple[dict, dict, object],
    *,
    index=None,
) -> dict:
    projection, binding, receipt = authenticated_inputs
    return semantic_v2.build_semantic_local_accounting_observation_candidate_v2(
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        _index() if index is None else index,
    )


def test_complete_topology_promotes_collision_free_accentless_candidates(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    candidate = _assemble(authenticated_inputs)

    assert candidate["status"] == "READY_FOR_GRAPH_V2"
    assert candidate["readiness"] == {
        "complete_topology_count": 1,
        "unique_complete_topology": True,
        "accentless_candidates_promoted_by_topology": True,
        "ready_within_supplied_family_collision_scope": True,
        "globally_collision_free_claimed": False,
        "graph_v1_accepted": False,
    }
    region = candidate["candidate_regions"][0]
    assert region["owner_label"]["transformer_text_nfc"] == "CHO VAY KHÁCH HÀNG"
    assert region["owner_label"]["accentless_comparison_key"] == "cho vay khach hang"
    assert region["branch_label"]["role"] == "BRANCH"
    assert region["branch_label"]["match_kind"] == "ACCENTLESS_PREFIX_ALIAS"
    assert [row["role"] for row in region["rows"]] == [
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
        "TOTAL",
    ]
    assert [axis["period"] for axis in region["axes"]] == [
        "DATE:2026-06-30",
        "DATE:2025-12-31",
    ]
    assert [unit["unit"] for unit in region["local_unit_labels"]] == [
        {"basis": "LOCAL_VISIBLE_UNIT", "currency": "VND", "scale": 1_000_000},
        {"basis": "LOCAL_VISIBLE_UNIT", "currency": "VND", "scale": 1_000_000},
    ]
    assert region["rows"][0]["value_positions"][0]["raw_text"] == "10"
    assert region["rows"][0]["value_positions"][0]["text_source"] == ("PPOCRV6_NUMERIC_ONLY")
    assert region["arithmetic"] == {
        "status": "CORROBORATED",
        "evaluated_axis_indexes": [0, 1],
    }
    assert region["topology"]["internal_additive_closure"] is True
    assert region["topology"]["same_population_claimed"] is False
    assert candidate["safety"]["ppocr_transcript_used_for_semantic_identity"] is False
    assert candidate["safety"]["accentless_key_alone_can_accept"] is False
    assert candidate["safety"]["output_is_accepted_graph"] is False
    assert candidate["safety"]["supplied_family_collision_scope_only"] is True
    assert candidate["safety"]["family_registry_exhaustiveness_claimed"] is False
    assert candidate["safety"]["page_family_exhaustiveness_claimed"] is False


def test_omitting_a_decoy_only_claims_readiness_within_the_supplied_scope(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    candidate = _assemble(authenticated_inputs)

    assert candidate["status"] == "READY_FOR_GRAPH_V2"
    assert candidate["readiness"]["ready_within_supplied_family_collision_scope"] is True
    assert candidate["readiness"]["globally_collision_free_claimed"] is False
    assert candidate["supplied_family_collision_scope_spec_sha256_by_id"] == {
        "LOAN_MATURITY_BUCKETS": local_accounting_family_spec_sha256_v1(
            LOAN_MATURITY_BUCKETS_SPEC_V1
        ),
        "LOAN_QUALITY_CLASSIFICATION": local_accounting_family_spec_sha256_v1(
            LOAN_QUALITY_CLASSIFICATION_SPEC_V1
        ),
    }
    assert "DECOY_MATURITY" not in candidate["supplied_family_collision_scope_spec_sha256_by_id"]


def test_ppocr_semantic_text_cannot_rescue_a_bad_transformer_branch(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    projection, binding, _receipt = authenticated_inputs
    projection["page_result"]["lines"][1]["raw_text"] = (
        "Phan tich du no theo thoi han goc cua khoan vay"
    )
    binding["samples"][1]["normalized_prediction"] = "VĂN BẢN KHÔNG LIÊN QUAN"

    candidate = _assemble(authenticated_inputs)

    assert candidate["status"] == "UNRESOLVED"
    assert "BRANCH_NOT_RESOLVED_FROM_TRANSFORMER" in candidate["unresolved_reasons"]
    assert candidate["candidate_regions"] == []


def test_matched_maturity_rows_without_customer_loan_owner_are_a_hard_control(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    _projection, binding, _receipt = authenticated_inputs
    binding["samples"][0]["normalized_prediction"] = "RỦI RO THANH KHOẢN"

    candidate = _assemble(authenticated_inputs)

    assert candidate["status"] == "UNRESOLVED"
    assert "OWNER_NOT_RESOLVED_FROM_TRANSFORMER" in candidate["unresolved_reasons"]
    assert candidate["readiness"]["complete_topology_count"] == 0


def test_accentless_alias_collision_is_not_promoted_by_numeric_shape(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    decoy = FamilySpecV1(
        family_id="DECOY_MATURITY",
        owner_aliases=("nguon von",),
        branch_aliases=("phan tich nguon von",),
        ordered_children=(RowRoleSpecV1("OTHER_SHORT", ("ngan han",)),),
        optional_children=(),
        total_aliases=("tong",),
        closure_child_roles=("OTHER_SHORT",),
    )

    candidate = _assemble(authenticated_inputs, index=_index(decoy))

    assert candidate["status"] == "UNRESOLVED"
    assert "SEMANTIC_ALIAS_COLLISION" in candidate["unresolved_reasons"]
    assert candidate["readiness"]["accentless_candidates_promoted_by_topology"] is False


def test_observed_optional_child_stays_unresolved_until_generic_mode_exists(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    _projection, binding, _receipt = authenticated_inputs
    binding["samples"][2]["normalized_prediction"] = "Nợ khác"
    spec = FamilySpecV1(
        family_id="OPTIONAL_MATURITY",
        owner_aliases=("cho vay khach hang",),
        branch_aliases=("phan tich du no theo thoi han",),
        ordered_children=(
            RowRoleSpecV1("SHORT_TERM", ("ngan han",)),
            RowRoleSpecV1("MEDIUM_TERM", ("trung han",)),
            RowRoleSpecV1("LONG_TERM", ("dai han",)),
        ),
        optional_children=(RowRoleSpecV1("OTHER", ("no khac",)),),
        total_aliases=("tong",),
        closure_child_roles=("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"),
    )
    projection, page_binding, receipt = authenticated_inputs

    candidate = semantic_v2.build_semantic_local_accounting_observation_candidate_v2(
        projection,
        page_binding,
        receipt,
        spec,
        _index(spec),
    )

    assert candidate["status"] == "UNRESOLVED"
    assert "OPTIONAL_CHILD_TOPOLOGY_NOT_IMPLEMENTED" in candidate["unresolved_reasons"]


def test_exact_utf8_surfaces_need_no_accentless_promotion(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    exact = FamilySpecV1(
        family_id="EXACT_MATURITY",
        owner_aliases=("CHO VAY KHÁCH HÀNG",),
        branch_aliases=("Phân tích dư nợ theo thời hạn gốc của khoản vay",),
        ordered_children=(
            RowRoleSpecV1("SHORT_TERM", ("Nợ ngắn hạn",)),
            RowRoleSpecV1("MEDIUM_TERM", ("Nợ trung hạn",)),
            RowRoleSpecV1("LONG_TERM", ("Nợ dài hạn",)),
        ),
        optional_children=(),
        total_aliases=("Tổng cộng",),
        closure_child_roles=("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"),
    )
    projection, binding, receipt = authenticated_inputs

    candidate = semantic_v2.build_semantic_local_accounting_observation_candidate_v2(
        projection,
        binding,
        receipt,
        exact,
        (exact,),
    )

    assert candidate["status"] == "READY_FOR_GRAPH_V2"
    assert candidate["readiness"]["accentless_candidates_promoted_by_topology"] is False
    assert all(
        label["promotion_status"] == "EXACT_SURFACE_IN_COMPLETE_TOPOLOGY"
        for label in (
            candidate["candidate_regions"][0]["owner_label"],
            candidate["candidate_regions"][0]["branch_label"],
            *(row["label"] for row in candidate["candidate_regions"][0]["rows"][:-1]),
        )
    )


def test_precompiled_or_mutated_alias_index_is_not_an_input_authority(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    projection, binding, receipt = authenticated_inputs
    compiled = compile_vietnamese_family_alias_index_v1(_index())

    with pytest.raises(semantic_v2.SemanticLocalAccountingObservationV2Error):
        semantic_v2.build_semantic_local_accounting_observation_candidate_v2(
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            compiled,
        )


def test_unequal_per_axis_units_stay_unresolved(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    _projection, binding, _receipt = authenticated_inputs
    binding["samples"][5]["normalized_prediction"] = "Nghìn đồng"

    candidate = _assemble(authenticated_inputs)

    assert candidate["status"] == "UNRESOLVED"
    assert "PER_AXIS_UNIT_SCOPE_NOT_RESOLVED" in candidate["unresolved_reasons"]


def test_arithmetic_mismatch_vetoes_readiness(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    projection, _binding, _receipt = authenticated_inputs
    projection["page_result"]["lines"][15]["raw_text"] = "61"

    candidate = _assemble(authenticated_inputs)

    assert candidate["status"] == "UNRESOLVED"
    assert "ARITHMETIC_CLOSURE_VETO" in candidate["unresolved_reasons"]


def test_candidate_validator_rebuilds_the_authenticated_result(
    authenticated_inputs: tuple[dict, dict, object],
) -> None:
    candidate = _assemble(authenticated_inputs)

    replayed = semantic_v2.validate_semantic_local_accounting_observation_candidate_v2(
        candidate,
        *authenticated_inputs,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        _index(),
    )

    assert replayed == candidate
    forged = deepcopy(candidate)
    forged["candidate_regions"][0]["owner_label"]["transformer_text_nfc"] = "forged"
    with pytest.raises(semantic_v2.SemanticLocalAccountingObservationV2Error):
        semantic_v2.validate_semantic_local_accounting_observation_candidate_v2(
            forged,
            *authenticated_inputs,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            _index(),
        )
