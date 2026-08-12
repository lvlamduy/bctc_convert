from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
import test_source_structure_adjacent_page_table_geometry_relations_v1 as relation_helpers
from test_source_structure_adjacent_page_table_geometry_relations_v1 import (
    _aligned_rows,
    _narrative_rows,
    _ocr_page_graph,
    _ocr_terminal_page_graph,
)

from bctc_ai.source_structure import (
    adjacent_page_table_geometry_candidate_gate_v1 as gate_v1,
)
from bctc_ai.source_structure.adjacent_page_table_geometry_candidate_gate_v1 import (
    ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1,
    LOWER_QUARTILE_MARGINAL_ENVELOPE_V1,
    AdjacentPageTableGeometryCandidateGateError,
    build_adjacent_page_table_geometry_candidate_gate_v1,
    validate_adjacent_page_table_geometry_candidate_gate_v1,
)
from bctc_ai.source_structure.adjacent_page_table_geometry_relations_v1 import (
    build_adjacent_page_table_geometry_relations_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_TABLE_CAPS = {
    "normalized_left_edge_absolute_distance_ppm": 1_236,
    "normalized_right_edge_absolute_distance_ppm": 1_854,
    "normalized_width_absolute_distance_ppm": 2_473,
    "previous_distance_to_page_bottom_ppm": 94_587,
    "following_distance_from_page_top_ppm": 45_299,
}
_AXIS_CAPS = {
    "x0_median_absolute_distance_ppm": 53_505,
    "x2_median_absolute_distance_ppm": 53_011,
    "center2_median_absolute_distance_ppm": 106_492,
}
_RELATION_SEED = "GEOMETRY_SUPPORTED_EXPLORATORY_SEED_CANDIDATE"
_RELATION_INSUFFICIENT = (
    "RETAINED_WITH_INSUFFICIENT_BIDIRECTIONALLY_SINGLETON_AXIS_SUPPORT_UNRESOLVED"
)
_RELATION_OUTSIDE = "RETAINED_OUTSIDE_TABLE_OR_PAGE_ENVELOPE_UNRESOLVED"
_AXIS_SINGLETON = "WITHIN_AXIS_ENVELOPE_BIDIRECTIONALLY_SINGLETON_SEED_LINK"
_AXIS_AMBIGUOUS = "WITHIN_AXIS_ENVELOPE_AMBIGUOUS_SEED_LINK"
_AXIS_OUTSIDE = "RETAINED_OUTSIDE_AXIS_ENVELOPE_UNRESOLVED"


def _rows(
    y_values: tuple[int, ...],
    *,
    axis_count: int = 3,
) -> list[tuple[int, list[tuple[int, int]]]]:
    boxes = [(100 + 250 * index, 180 + 250 * index) for index in range(axis_count)]
    return [(y, boxes) for y in y_values]


def _boundary_pair(
    *,
    previous_axis_count: int = 3,
    following_axis_count: int = 3,
) -> tuple[
    tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
]:
    return (
        _ocr_page_graph(
            1,
            _rows((1_240, 1_320, 1_400, 1_480), axis_count=previous_axis_count),
        ),
        _ocr_page_graph(
            2,
            _rows((20, 100, 180, 260), axis_count=following_axis_count),
        ),
    )


def _upstream(
    previous: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    following: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> dict[str, Any]:
    return build_adjacent_page_table_geometry_relations_v1(*previous, *following)


def _set_table_and_boundary_pass(relation: dict[str, Any]) -> None:
    for field in _TABLE_CAPS:
        relation["table_distance_evidence"][field] = 0


def _set_all_axis_distances_outside(relation: dict[str, Any]) -> None:
    for distance in relation["axis_cartesian_distances"]:
        for field, cap in _AXIS_CAPS.items():
            distance[field] = cap + 1


def _set_axis_distance_pass(distance: dict[str, Any]) -> None:
    for field in _AXIS_CAPS:
        distance[field] = 0


def _set_diagonal_axis_distances_pass(relation: dict[str, Any]) -> None:
    _set_all_axis_distances_outside(relation)
    previous_ids = list(
        dict.fromkeys(
            distance["previous_axis_geometry_id"]
            for distance in relation["axis_cartesian_distances"]
        )
    )
    following_ids = list(
        dict.fromkeys(
            distance["following_axis_geometry_id"]
            for distance in relation["axis_cartesian_distances"]
        )
    )
    for distance in relation["axis_cartesian_distances"]:
        if previous_ids.index(distance["previous_axis_geometry_id"]) == following_ids.index(
            distance["following_axis_geometry_id"]
        ):
            _set_axis_distance_pass(distance)


def _rehash_gate(value: dict[str, Any]) -> None:
    value["artifact_identity"] = "apgcv1:artifact:" + canonical_json_sha256_v1(
        {key: item for key, item in value.items() if key != "artifact_identity"}
    )


def _assert_no_float(value: Any) -> None:
    assert type(value) is not float
    if type(value) is dict:
        for item in value.values():
            _assert_no_float(item)
    elif type(value) is list:
        for item in value:
            _assert_no_float(item)


def _decision_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "relation": [
            {
                "table": item["table_shape_envelope_mask"],
                "boundary": item["page_boundary_envelope_mask"],
                "joint": item["table_page_joint_envelope_mask"],
                "failure": item["relation_failure_mask"],
                "singleton_count": item["bidirectionally_singleton_axis_seed_link_count"],
                "primary": item["primary_disposition"],
            }
            for item in value["relation_dispositions"]
        ],
        "axis_distance": [
            {
                "mask": item["axis_envelope_mask"],
                "joint": item["axis_envelope_joint_pass"],
                "previous_degree": item["previous_axis_within_envelope_degree_in_relation"],
                "following_degree": item["following_axis_within_envelope_degree_in_relation"],
                "singleton": item["bidirectionally_singleton_axis_seed_link"],
                "primary": item["primary_disposition"],
            }
            for item in value["axis_distance_dispositions"]
        ],
        "fragment": [item["primary_disposition"] for item in value["fragment_dispositions"]],
        "axis": [item["primary_disposition"] for item in value["axis_dispositions"]],
        "pair": value["page_pair_disposition"]["primary_disposition"],
    }


def test_fused_public_gate_is_exact_integer_only_and_complete() -> None:
    previous, following = _boundary_pair()

    first = build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)
    repeated = build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)

    assert canonical_json_bytes_v1(first) == canonical_json_bytes_v1(repeated)
    assert (
        validate_adjacent_page_table_geometry_candidate_gate_v1(
            first,
            previous_projection=previous[0],
            previous_proposal_projection=previous[1],
            previous_graph=previous[2],
            following_projection=following[0],
            following_proposal_projection=following[1],
            following_graph=following[2],
        )
        == first
    )
    relation = first["relation_dispositions"][0]
    assert relation["table_shape_envelope_mask"] == [True, True, True]
    assert relation["page_boundary_envelope_mask"] == [True, True]
    assert relation["table_page_joint_envelope_mask"] == [True] * 5
    assert relation["bidirectionally_singleton_axis_seed_link_count"] == 3
    assert relation["primary_disposition"] == _RELATION_SEED
    assert relation["previous_fragment_geometry_supported_relation_degree"] == 1
    assert relation["following_fragment_geometry_supported_relation_degree"] == 1
    assert relation["reciprocal_singleton_fragment_seed_candidate"] is True
    assert first["metrics"]["input_relation_count"] == 1
    assert first["metrics"]["relation_disposition_count"] == 1
    assert first["metrics"]["input_axis_distance_count"] == 9
    assert first["metrics"]["axis_distance_disposition_count"] == 9
    assert first["metrics"]["input_fragment_count"] == 2
    assert first["metrics"]["fragment_disposition_count"] == 2
    assert first["metrics"]["input_physical_axis_count"] == 6
    assert first["metrics"]["physical_axis_disposition_count"] == 6
    assert all(
        first["metrics"][field]
        for field in (
            "relation_no_drop",
            "axis_distance_no_drop",
            "fragment_no_drop",
            "physical_axis_no_drop",
        )
    )
    assert set(first["upstream_binding"]["relation_ids"]) == {
        item["relation_id"] for item in first["relation_dispositions"]
    }
    assert set(first["upstream_binding"]["axis_distance_ids"]) == {
        item["axis_distance_id"] for item in first["axis_distance_dispositions"]
    }
    assert set(first["upstream_binding"]["fragment_ids"]) == {
        item["fragment_id"] for item in first["fragment_dispositions"]
    }
    assert set(first["upstream_binding"]["axis_geometry_ids"]) == {
        item["axis_geometry_id"] for item in first["axis_dispositions"]
    }
    assert first["page_pair_disposition"]["primary_disposition"] == (
        "ONE_OR_MORE_RECIPROCAL_SINGLETON_GEOMETRY_SEEDS_RETAINED"
    )
    assert first["safety"]["accepted_relation_claimed"] is False
    assert first["safety"]["same_table_claimed"] is False
    assert first["safety"]["continuation_claimed"] is False
    assert first["safety"]["merge_claimed"] is False
    assert first["safety"]["holdout_claimed"] is False
    assert first["safety"]["generalization_claimed"] is False
    _assert_no_float(first)


def test_fused_builder_calls_the_public_upstream_builder_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous, following = _boundary_pair()
    original = gate_v1.build_adjacent_page_table_geometry_relations_v1
    calls = 0

    def counted(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(gate_v1, "build_adjacent_page_table_geometry_relations_v1", counted)

    build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)

    assert calls == 1


def test_policy_pins_exact_blind_receipt_selector_samples_and_source_bytes() -> None:
    policy = LOWER_QUARTILE_MARGINAL_ENVELOPE_V1
    selector = policy["percentile_selector"]
    reference = policy["full_wave_1_upstream_accounting_reference"]
    receipt = policy["measurement_receipt"]
    interpretation = policy["sample_interpretation"]
    payload = {
        key: value
        for key, value in policy.items()
        if key not in {"policy_payload_sha256", "policy_identity"}
    }

    assert selector["selection_formula"] == (
        "ordered[((len(ordered) - 1) * numerator) // denominator]"
    )
    assert selector["table_and_page_sample_count"] == 899
    assert selector["table_and_page_zero_based_rank"] == ((899 - 1) * 1) // 4 == 224
    assert selector["axis_sample_count"] == 122_573
    assert selector["axis_zero_based_rank"] == ((122_573 - 1) * 1) // 4 == 30_643
    assert policy["table_shape_envelope"] == {
        "mask_order": [
            "left_edge_within_cap",
            "right_edge_within_cap",
            "width_within_cap",
        ],
        "comparison": "INCLUSIVE_INTEGER_LESS_THAN_OR_EQUAL",
        "normalized_left_edge_absolute_distance_ppm_maximum": 1_236,
        "normalized_right_edge_absolute_distance_ppm_maximum": 1_854,
        "normalized_width_absolute_distance_ppm_maximum": 2_473,
        "sample_count_each": 899,
        "zero_based_rank_each": 224,
    }
    assert (
        policy["page_boundary_envelope"]["previous_distance_to_page_bottom_ppm_maximum"] == 94_587
    )
    assert (
        policy["page_boundary_envelope"]["following_distance_from_page_top_ppm_maximum"] == 45_299
    )
    assert policy["axis_envelope"]["x0_median_absolute_distance_ppm_maximum"] == 53_505
    assert policy["axis_envelope"]["x2_median_absolute_distance_ppm_maximum"] == 53_011
    assert (
        policy["axis_envelope"]["doubled_center2_median_absolute_distance_ppm_maximum"] == 106_492
    )
    assert policy["axis_envelope"]["doubled_center2_domain_maximum_ppm"] == 2_000_000
    assert receipt == {
        "transport": "RETAINED_STDOUT_JSON_ONLY",
        "sha256": "4f8f9e1672d3a1672a2e4a3bcc959922b4eb65b58ad6b987467b67cf17864c13",
        "size_bytes": 24_162,
        "status": (
            "PASS_EXHAUSTIVE_READ_ONLY_ADJACENT_PAGE_RELATION_SUMMARY_RECOVERY_OPTIMIZED_V1"
        ),
        "artifact_persisted": False,
        "clean_run_git_commit": "4d1506a24f4e180023b58689ea4cd770db0f0fde",
        "phase_close_git_commit": "f05bc37062530fbcd49d56d329fc656e82b5b3b1",
    }
    assert reference["page_pair_disposition_counts"] == {
        "MEASURED_CARTESIAN_FRAGMENT_PAIRS": 676,
        "NO_PREVIOUS_TABLE_CANDIDATE": 135,
        "NO_FOLLOWING_TABLE_CANDIDATE": 143,
        "NO_TABLE_CANDIDATES": 359,
        "UPSTREAM_TERMINAL_BARRIER": 109,
    }
    assert reference["fragment_occurrence_count"] == 1_909
    assert reference["measured_fragment_occurrence_count"] == 1_521
    assert reference["retained_fragment_occurrence_count"] == 388
    assert reference["axis_occurrence_count"] == 18_805
    assert reference["measured_axis_occurrence_count"] == 16_085
    assert reference["retained_axis_occurrence_count"] == 2_720
    assert reference["upstream_nonmeasured_page_pair_count"] == 746
    assert interpretation["same_corpus_gate_replay_is_holdout"] is False
    assert interpretation["independent_holdout_used"] is False
    assert interpretation["continuation_labels_present"] is False
    assert interpretation["policy_tuned_from_role_a"] is False
    assert interpretation["role_a_used"] is False
    assert interpretation["marginal_conjunction_is_twenty_five_percent_gate"] is False
    assert interpretation["scientific_calibration"] is False
    assert canonical_json_sha256_v1(payload) == policy["policy_payload_sha256"]
    assert policy["policy_identity"] == f"apgcv1:policy:{policy['policy_payload_sha256']}"

    upstream_module = (
        PROJECT_ROOT / "src/bctc_ai/source_structure/adjacent_page_table_geometry_relations_v1.py"
    )
    upstream_test = (
        PROJECT_ROOT
        / "tests/unit/test_source_structure_adjacent_page_table_geometry_relations_v1.py"
    )
    assert (
        sha256(upstream_module.read_bytes()).hexdigest()
        == policy["upstream_contract"]["module_sha256"]
    )
    assert (
        sha256(upstream_test.read_bytes()).hexdigest()
        == policy["upstream_contract"]["focused_test_sha256"]
    )


@pytest.mark.parametrize(
    ("field", "cap", "check_field"),
    [
        (
            "normalized_left_edge_absolute_distance_ppm",
            1_236,
            "left_edge_within_cap",
        ),
        (
            "normalized_right_edge_absolute_distance_ppm",
            1_854,
            "right_edge_within_cap",
        ),
        ("normalized_width_absolute_distance_ppm", 2_473, "width_within_cap"),
        (
            "previous_distance_to_page_bottom_ppm",
            94_587,
            "previous_bottom_within_cap",
        ),
        (
            "following_distance_from_page_top_ppm",
            45_299,
            "following_top_within_cap",
        ),
    ],
)
def test_each_table_and_page_cap_is_inclusive_and_cap_plus_one_fails(
    field: str,
    cap: int,
    check_field: str,
) -> None:
    previous, following = _boundary_pair()
    relation = deepcopy(_upstream(previous, following)["fragment_pair_relations"][0])
    _set_table_and_boundary_pass(relation)
    axis_dispositions = gate_v1._axis_distance_dispositions(relation)  # noqa: SLF001

    relation["table_distance_evidence"][field] = cap
    at_cap = gate_v1._relation_disposition(relation, axis_dispositions)  # noqa: SLF001
    relation["table_distance_evidence"][field] = cap + 1
    above_cap = gate_v1._relation_disposition(relation, axis_dispositions)  # noqa: SLF001

    checks_key = (
        "table_shape_envelope_checks"
        if check_field in {"left_edge_within_cap", "right_edge_within_cap", "width_within_cap"}
        else "page_boundary_envelope_checks"
    )
    assert at_cap[checks_key][check_field] is True
    assert above_cap[checks_key][check_field] is False
    assert at_cap["primary_disposition"] == _RELATION_SEED
    assert above_cap["primary_disposition"] == _RELATION_OUTSIDE


@pytest.mark.parametrize(
    ("field", "cap", "check_field"),
    [
        ("x0_median_absolute_distance_ppm", 53_505, "x0_within_cap"),
        ("x2_median_absolute_distance_ppm", 53_011, "x2_within_cap"),
        (
            "center2_median_absolute_distance_ppm",
            106_492,
            "doubled_center2_within_cap",
        ),
    ],
)
def test_each_axis_cap_is_inclusive_and_cap_plus_one_fails(
    field: str,
    cap: int,
    check_field: str,
) -> None:
    previous, following = _boundary_pair(previous_axis_count=2, following_axis_count=2)
    relation = deepcopy(_upstream(previous, following)["fragment_pair_relations"][0])
    _set_all_axis_distances_outside(relation)
    distance = relation["axis_cartesian_distances"][0]
    _set_axis_distance_pass(distance)

    distance[field] = cap
    at_cap = gate_v1._axis_distance_dispositions(relation)[0]  # noqa: SLF001
    distance[field] = cap + 1
    above_cap = gate_v1._axis_distance_dispositions(relation)[0]  # noqa: SLF001

    assert at_cap["axis_envelope_checks"][check_field] is True
    assert at_cap["axis_envelope_joint_pass"] is True
    assert at_cap["primary_disposition"] == _AXIS_SINGLETON
    assert above_cap["axis_envelope_checks"][check_field] is False
    assert above_cap["axis_envelope_joint_pass"] is False
    assert above_cap["primary_disposition"] == _AXIS_OUTSIDE


def test_marginal_component_masks_do_not_imply_their_joint_or_a_selection_rate() -> None:
    previous, following = _boundary_pair(previous_axis_count=2, following_axis_count=2)
    relation = deepcopy(_upstream(previous, following)["fragment_pair_relations"][0])
    _set_table_and_boundary_pass(relation)
    relation["table_distance_evidence"]["normalized_right_edge_absolute_distance_ppm"] = 1_855
    relation["table_distance_evidence"]["following_distance_from_page_top_ppm"] = 45_300
    _set_all_axis_distances_outside(relation)
    distance = relation["axis_cartesian_distances"][0]
    distance["x0_median_absolute_distance_ppm"] = 53_505
    distance["x2_median_absolute_distance_ppm"] = 53_012
    distance["center2_median_absolute_distance_ppm"] = 106_492

    axis = gate_v1._axis_distance_dispositions(relation)  # noqa: SLF001
    disposition = gate_v1._relation_disposition(relation, axis)  # noqa: SLF001

    assert disposition["table_shape_envelope_mask"] == [True, False, True]
    assert disposition["page_boundary_envelope_mask"] == [True, False]
    assert disposition["table_page_joint_envelope_mask"] == [True, False, True, True, False]
    assert disposition["table_shape_envelope_joint_pass"] is False
    assert disposition["page_boundary_envelope_joint_pass"] is False
    assert disposition["table_page_joint_envelope_pass"] is False
    assert axis[0]["axis_envelope_mask"] == [True, False, True]
    assert axis[0]["axis_envelope_joint_pass"] is False
    assert disposition["relation_failure_mask"] == {
        "table_left_edge_outside_envelope": False,
        "table_right_edge_outside_envelope": True,
        "table_width_outside_envelope": False,
        "previous_bottom_outside_envelope": False,
        "following_top_outside_envelope": True,
        "fewer_than_two_bidirectionally_singleton_axis_links": True,
    }
    assert len(disposition["relation_failure_reason_codes"]) == 3
    assert disposition["primary_disposition"] == _RELATION_OUTSIDE


@pytest.mark.parametrize(
    ("singleton_count", "expected"),
    [
        (0, _RELATION_INSUFFICIENT),
        (1, _RELATION_INSUFFICIENT),
        (2, _RELATION_SEED),
    ],
)
def test_uncalibrated_conservative_support_rule_has_an_exact_zero_one_two_boundary(
    singleton_count: int,
    expected: str,
) -> None:
    previous, following = _boundary_pair()
    relation = deepcopy(_upstream(previous, following)["fragment_pair_relations"][0])
    _set_table_and_boundary_pass(relation)
    axis_dispositions = [
        {
            "axis_distance_id": f"distance-{index}",
            "axis_envelope_joint_pass": True,
            "bidirectionally_singleton_axis_seed_link": True,
            "primary_disposition": _AXIS_SINGLETON,
        }
        for index in range(singleton_count)
    ]

    disposition = gate_v1._relation_disposition(  # noqa: SLF001
        relation,
        axis_dispositions,
    )

    assert disposition["bidirectionally_singleton_axis_seed_link_count"] == singleton_count
    assert disposition["primary_disposition"] == expected
    assert disposition["outside_or_insufficient_is_negative_claim"] is False


def test_all_to_all_axis_ties_preserve_ambiguity_without_selecting_a_nearest_link() -> None:
    previous, following = _boundary_pair()
    relation = deepcopy(_upstream(previous, following)["fragment_pair_relations"][0])
    _set_table_and_boundary_pass(relation)
    for distance in relation["axis_cartesian_distances"]:
        _set_axis_distance_pass(distance)

    axis = gate_v1._axis_distance_dispositions(relation)  # noqa: SLF001
    disposition = gate_v1._relation_disposition(relation, axis)  # noqa: SLF001

    assert len(axis) == 9
    assert all(item["axis_envelope_joint_pass"] for item in axis)
    assert all(
        item["previous_axis_within_envelope_degree_in_relation"] == 3
        and item["following_axis_within_envelope_degree_in_relation"] == 3
        and item["primary_disposition"] == _AXIS_AMBIGUOUS
        for item in axis
    )
    assert disposition["bidirectionally_singleton_axis_seed_link_ids"] == []
    assert disposition["primary_disposition"] == _RELATION_INSUFFICIENT
    assert ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1["winner_selected"] is False


def test_unequal_axis_counts_retain_unmatched_axes_and_two_singletons_can_seed() -> None:
    previous, _ = _boundary_pair(previous_axis_count=3, following_axis_count=3)
    following = _ocr_page_graph(
        2,
        [(y, [(100, 180), (600, 680)]) for y in (20, 100, 180, 260)],
    )

    result = build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)

    relation = result["relation_dispositions"][0]
    assert len(result["axis_distance_dispositions"]) == 6
    assert relation["bidirectionally_singleton_axis_seed_link_count"] == 2
    assert relation["primary_disposition"] == _RELATION_SEED
    assert len(result["axis_dispositions"]) == 5
    assert (
        sum(item["within_axis_envelope_degree"] == 0 for item in result["axis_dispositions"]) == 1
    )
    assert (
        sum(
            item["primary_disposition"] == "ONE_BIDIRECTIONALLY_SINGLETON_AXIS_SEED_CANDIDATE"
            for item in result["axis_dispositions"]
        )
        == 4
    )


def test_zero_axis_support_is_explicitly_insufficient_and_never_negative() -> None:
    previous, following = _boundary_pair()
    relation = deepcopy(_upstream(previous, following)["fragment_pair_relations"][0])
    _set_table_and_boundary_pass(relation)

    disposition = gate_v1._relation_disposition(relation, [])  # noqa: SLF001

    assert disposition["axis_distance_ids"] == []
    assert disposition["within_axis_envelope_distance_ids"] == []
    assert disposition["bidirectionally_singleton_axis_seed_link_ids"] == []
    assert disposition["primary_disposition"] == _RELATION_INSUFFICIENT
    assert disposition["geometry_supported_exploratory_seed_candidate"] is False
    assert disposition["outside_or_insufficient_is_negative_claim"] is False


@pytest.mark.parametrize(
    ("previous_rows", "following_rows", "upstream_pair", "retained_fragments"),
    [
        (_narrative_rows(), _aligned_rows(), "NO_PREVIOUS_TABLE_CANDIDATE", 1),
        (_aligned_rows(), _narrative_rows(), "NO_FOLLOWING_TABLE_CANDIDATE", 1),
        (_narrative_rows(), _narrative_rows(), "NO_TABLE_CANDIDATES", 0),
    ],
)
def test_every_zero_counterpart_pair_fragment_and_axis_is_retained_without_absence(
    previous_rows: list[tuple[int, list[tuple[int, int]]]],
    following_rows: list[tuple[int, list[tuple[int, int]]]],
    upstream_pair: str,
    retained_fragments: int,
) -> None:
    result = build_adjacent_page_table_geometry_candidate_gate_v1(
        *_ocr_page_graph(1, previous_rows),
        *_ocr_page_graph(2, following_rows),
    )

    assert result["relation_dispositions"] == []
    assert result["axis_distance_dispositions"] == []
    assert result["page_pair_disposition"]["upstream_primary_disposition"] == upstream_pair
    assert result["page_pair_disposition"]["primary_disposition"] == (
        "UPSTREAM_NONMEASURED_PAGE_PAIR_RETAINED_UNRESOLVED"
    )
    assert len(result["fragment_dispositions"]) == retained_fragments
    assert all(
        item["primary_disposition"] == "UPSTREAM_RETAINED_WITHOUT_MEASURED_COUNTERPART_UNRESOLVED"
        and item["upstream_incident_relation_ids"] == []
        for item in result["fragment_dispositions"]
    )
    assert len(result["axis_dispositions"]) == retained_fragments * 3
    assert all(
        item["primary_disposition"] == "UPSTREAM_RETAINED_WITHOUT_AXIS_COUNTERPART_UNRESOLVED"
        and item["upstream_incident_axis_distance_ids"] == []
        for item in result["axis_dispositions"]
    )
    assert result["page_pair_disposition"]["source_table_absence_claimed"] is False
    assert result["safety"]["absence_claimed"] is False


def test_terminal_barrier_preserves_every_upstream_retained_occurrence() -> None:
    result = build_adjacent_page_table_geometry_candidate_gate_v1(
        *_ocr_page_graph(1, _aligned_rows(second_block=True)),
        *_ocr_terminal_page_graph(2),
    )

    assert result["page_pair_disposition"]["upstream_primary_disposition"] == (
        "UPSTREAM_TERMINAL_BARRIER"
    )
    assert result["page_pair_disposition"]["primary_disposition"] == (
        "UPSTREAM_NONMEASURED_PAGE_PAIR_RETAINED_UNRESOLVED"
    )
    assert result["relation_dispositions"] == []
    assert result["axis_distance_dispositions"] == []
    assert len(result["fragment_dispositions"]) == 2
    assert len(result["axis_dispositions"]) == 6
    assert result["metrics"]["upstream_retained_fragment_count"] == 2
    assert result["metrics"]["upstream_retained_physical_axis_count"] == 6
    assert all(
        "UPSTREAM_TERMINAL" in item["upstream_reason_code"]
        for item in result["fragment_dispositions"]
    )
    assert all(
        "UPSTREAM_TERMINAL" in item["upstream_reason_code"] for item in result["axis_dispositions"]
    )


def test_competing_supported_relations_are_all_retained_and_physical_axis_mixing_is_explicit() -> (
    None
):
    previous = _ocr_page_graph(
        1,
        _rows((1_240, 1_320, 1_400, 1_480), axis_count=4),
    )
    following_rows = [
        *_rows((20, 100, 180, 260), axis_count=4),
        *_rows((900, 980, 1_060, 1_140), axis_count=4),
    ]
    following = _ocr_page_graph(2, following_rows)
    upstream = deepcopy(_upstream(previous, following))
    assert len(upstream["fragment_pair_relations"]) == 2
    first, second = upstream["fragment_pair_relations"]
    for relation in (first, second):
        _set_table_and_boundary_pass(relation)
    _set_diagonal_axis_distances_pass(first)
    _set_all_axis_distances_outside(second)
    previous_ids = list(
        dict.fromkeys(
            item["previous_axis_geometry_id"] for item in second["axis_cartesian_distances"]
        )
    )
    following_ids = list(
        dict.fromkeys(
            item["following_axis_geometry_id"] for item in second["axis_cartesian_distances"]
        )
    )
    for distance in second["axis_cartesian_distances"]:
        previous_index = previous_ids.index(distance["previous_axis_geometry_id"])
        following_index = following_ids.index(distance["following_axis_geometry_id"])
        if previous_index == following_index and previous_index < 2:
            _set_axis_distance_pass(distance)
        elif previous_index >= 2 and following_index >= 2:
            _set_axis_distance_pass(distance)

    result = gate_v1._derive_from_validated_relation(upstream)  # noqa: SLF001

    supported_ids = result["page_pair_disposition"]["geometry_supported_relation_ids"]
    assert supported_ids == [first["relation_id"], second["relation_id"]]
    assert all(
        item["primary_disposition"] == _RELATION_SEED for item in result["relation_dispositions"]
    )
    assert result["page_pair_disposition"]["primary_disposition"] == (
        "GEOMETRY_SEEDS_WITH_FRAGMENT_AMBIGUITY_RETAINED"
    )
    assert result["page_pair_disposition"]["reciprocal_singleton_fragment_relation_ids"] == []
    assert (
        result["page_pair_disposition"]["fragment_ambiguous_geometry_supported_relation_ids"]
        == supported_ids
    )
    assert any(
        item["primary_disposition"] == "MULTIPLE_OR_MIXED_AXIS_SEED_LINKS_AMBIGUOUS_UNRESOLVED"
        and item["bidirectionally_singleton_axis_seed_link_ids"]
        and item["ambiguous_axis_envelope_distance_ids"]
        for item in result["axis_dispositions"]
    )
    assert any(
        item["primary_disposition"] == "MULTIPLE_FRAGMENT_SEEDS_AMBIGUOUS_UNRESOLVED"
        for item in result["fragment_dispositions"]
    )
    assert (
        sum(
            item["primary_disposition"] == "ONE_NONRECIPROCAL_FRAGMENT_SEED_AMBIGUOUS_UNRESOLVED"
            for item in result["fragment_dispositions"]
        )
        == 2
    )


def test_two_disjoint_reciprocal_fragment_seeds_both_survive_without_a_winner() -> None:
    previous = _ocr_page_graph(1, _aligned_rows(second_block=True))
    following = _ocr_page_graph(2, _aligned_rows(second_block=True))
    upstream = deepcopy(_upstream(previous, following))
    relations = upstream["fragment_pair_relations"]
    assert len(relations) == 4
    for relation in relations:
        _set_table_and_boundary_pass(relation)
        _set_all_axis_distances_outside(relation)
    for relation in (relations[0], relations[3]):
        _set_diagonal_axis_distances_pass(relation)

    result = gate_v1._derive_from_validated_relation(upstream)  # noqa: SLF001

    expected = [relations[0]["relation_id"], relations[3]["relation_id"]]
    assert result["page_pair_disposition"]["geometry_supported_relation_ids"] == expected
    assert result["page_pair_disposition"]["reciprocal_singleton_fragment_relation_ids"] == expected
    assert (
        result["page_pair_disposition"]["fragment_ambiguous_geometry_supported_relation_ids"] == []
    )
    assert result["page_pair_disposition"]["primary_disposition"] == (
        "ONE_OR_MORE_RECIPROCAL_SINGLETON_GEOMETRY_SEEDS_RETAINED"
    )
    assert (
        sum(
            item["primary_disposition"] == _RELATION_SEED
            for item in result["relation_dispositions"]
        )
        == 2
    )
    assert all(
        item["primary_disposition"] == "ONE_RECIPROCAL_SINGLETON_FRAGMENT_SEED_CANDIDATE"
        for item in result["fragment_dispositions"]
    )
    assert result["safety"]["winner_selected"] is False


def test_reciprocal_and_ambiguous_fragment_seeds_coexist_without_loss() -> None:
    previous = _ocr_page_graph(1, _aligned_rows(second_block=True))
    following = _ocr_page_graph(
        2,
        [
            *_rows((20, 100, 180, 260)),
            *_rows((620, 700, 780, 860)),
            *_rows((1_220, 1_300, 1_380, 1_460)),
        ],
    )
    upstream = deepcopy(_upstream(previous, following))
    relations = upstream["fragment_pair_relations"]
    assert len(relations) == 6
    for relation in relations:
        _set_table_and_boundary_pass(relation)
        _set_all_axis_distances_outside(relation)
    supported_relations = [relations[0], relations[4], relations[5]]
    for relation in supported_relations:
        _set_diagonal_axis_distances_pass(relation)

    result = gate_v1._derive_from_validated_relation(upstream)  # noqa: SLF001

    supported_ids = [item["relation_id"] for item in supported_relations]
    assert result["page_pair_disposition"]["geometry_supported_relation_ids"] == supported_ids
    assert result["page_pair_disposition"]["reciprocal_singleton_fragment_relation_ids"] == [
        relations[0]["relation_id"]
    ]
    assert result["page_pair_disposition"][
        "fragment_ambiguous_geometry_supported_relation_ids"
    ] == [relations[4]["relation_id"], relations[5]["relation_id"]]
    assert result["page_pair_disposition"]["primary_disposition"] == (
        "GEOMETRY_SEEDS_WITH_FRAGMENT_AMBIGUITY_RETAINED"
    )
    by_id = {item["relation_id"]: item for item in result["relation_dispositions"]}
    assert (
        by_id[relations[0]["relation_id"]]["reciprocal_singleton_fragment_seed_candidate"] is True
    )
    assert all(
        by_id[relation["relation_id"]]["reciprocal_singleton_fragment_seed_candidate"] is False
        for relation in relations[4:6]
    )
    assert (
        sum(
            item["primary_disposition"] == _RELATION_SEED
            for item in result["relation_dispositions"]
        )
        == 3
    )
    assert (
        sum(
            item["primary_disposition"] == "ONE_RECIPROCAL_SINGLETON_FRAGMENT_SEED_CANDIDATE"
            for item in result["fragment_dispositions"]
        )
        == 2
    )
    assert any(
        item["primary_disposition"] == "MULTIPLE_FRAGMENT_SEEDS_AMBIGUOUS_UNRESOLVED"
        for item in result["fragment_dispositions"]
    )


def test_visible_text_and_unused_raw_scale_changes_do_not_change_geometry_decisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous, following = _boundary_pair()
    baseline = build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)
    original_line = relation_helpers._line

    def changed_line(y0: int, boxes: list[tuple[int, int, str]]) -> dict[str, Any]:
        return original_line(
            y0,
            [(x0, x1, f"changed-visible-value-{text}") for x0, x1, text in boxes],
        )

    monkeypatch.setattr(relation_helpers, "_line", changed_line)
    changed_previous, changed_following = _boundary_pair()
    changed = build_adjacent_page_table_geometry_candidate_gate_v1(
        *changed_previous,
        *changed_following,
    )
    assert (
        baseline["upstream_binding"]["upstream_artifact_identity"]
        != changed["upstream_binding"]["upstream_artifact_identity"]
    )
    assert _decision_projection(baseline) == _decision_projection(changed)

    upstream = deepcopy(_upstream(previous, following))
    scaled = deepcopy(upstream)
    for relation in scaled["fragment_pair_relations"]:
        evidence = relation["table_distance_evidence"]
        evidence["previous_distance_to_page_bottom_mpt"] *= 2
        evidence["following_distance_from_page_top_mpt"] *= 2
        for field in (
            "exact_left_edge_absolute_distance_page_width_fraction",
            "exact_right_edge_absolute_distance_page_width_fraction",
            "exact_width_absolute_distance_page_width_fraction",
            "previous_distance_to_page_bottom_page_height_fraction",
            "following_distance_from_page_top_page_height_fraction",
        ):
            evidence[field]["numerator"] *= 2
            evidence[field]["denominator"] *= 2
    assert _decision_projection(
        gate_v1._derive_from_validated_relation(upstream)  # noqa: SLF001
    ) == _decision_projection(
        gate_v1._derive_from_validated_relation(scaled)  # noqa: SLF001
    )


def test_mutated_exported_policy_or_safety_fails_closed_and_restores_cleanly() -> None:
    previous, following = _boundary_pair()
    policy_original = deepcopy(LOWER_QUARTILE_MARGINAL_ENVELOPE_V1)
    safety_original = deepcopy(ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1)

    try:
        LOWER_QUARTILE_MARGINAL_ENVELOPE_V1["table_shape_envelope"][
            "normalized_left_edge_absolute_distance_ppm_maximum"
        ] += 1
        with pytest.raises(
            AdjacentPageTableGeometryCandidateGateError,
            match="policy metadata drifted",
        ):
            build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)
    finally:
        LOWER_QUARTILE_MARGINAL_ENVELOPE_V1.clear()
        LOWER_QUARTILE_MARGINAL_ENVELOPE_V1.update(policy_original)

    try:
        ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1["winner_selected"] = True
        with pytest.raises(
            AdjacentPageTableGeometryCandidateGateError,
            match="safety metadata drifted",
        ):
            build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)
    finally:
        ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1.clear()
        ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1.update(safety_original)

    assert build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)


def test_validator_rejects_self_rehashed_delete_duplicate_foreign_reorder_crosslink_and_bool_drift() -> (
    None
):
    previous, following = _boundary_pair()
    result = build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *following)

    forged_values = []
    deleted = deepcopy(result)
    deleted["axis_dispositions"].pop()
    forged_values.append(deleted)
    duplicated = deepcopy(result)
    duplicated["relation_dispositions"].append(deepcopy(duplicated["relation_dispositions"][0]))
    forged_values.append(duplicated)
    foreign = deepcopy(result)
    foreign["fragment_dispositions"][0]["fragment_id"] = "apgrv1:fragment:" + "f" * 64
    forged_values.append(foreign)
    reordered = deepcopy(result)
    reordered["axis_distance_dispositions"].reverse()
    forged_values.append(reordered)
    crosslinked = deepcopy(result)
    crosslinked["axis_distance_dispositions"][0]["page_pair_id"] = "apgrv1:page_pair:" + "e" * 64
    forged_values.append(crosslinked)
    typed = deepcopy(result)
    typed["relation_dispositions"][0]["table_shape_envelope_mask"][0] = 1
    forged_values.append(typed)

    for forged in forged_values:
        _rehash_gate(forged)
        with pytest.raises(
            AdjacentPageTableGeometryCandidateGateError,
            match="drifted from exact fused replay",
        ):
            validate_adjacent_page_table_geometry_candidate_gate_v1(
                forged,
                previous_projection=previous[0],
                previous_proposal_projection=previous[1],
                previous_graph=previous[2],
                following_projection=following[0],
                following_proposal_projection=following[1],
                following_graph=following[2],
            )


def test_public_gate_rejects_foreign_or_mismatched_authenticated_page_inputs() -> None:
    previous, following = _boundary_pair()
    third = _ocr_page_graph(3, _rows((20, 100, 180, 260)))

    with pytest.raises(
        AdjacentPageTableGeometryCandidateGateError,
        match="exact adjacent-page relation construction",
    ):
        build_adjacent_page_table_geometry_candidate_gate_v1(*previous, *third)
    with pytest.raises(
        AdjacentPageTableGeometryCandidateGateError,
        match="exact adjacent-page relation construction",
    ):
        build_adjacent_page_table_geometry_candidate_gate_v1(
            previous[0],
            previous[1],
            previous[2],
            following[0],
            following[1],
            previous[2],
        )


def test_module_ast_has_no_semantic_identity_model_network_float_or_unsafe_relation_api() -> None:
    source_path = (
        PROJECT_ROOT
        / "src/bctc_ai/source_structure/adjacent_page_table_geometry_candidate_gate_v1.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    subscript_keys = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    assert subscript_keys.isdisjoint(
        {
            "bank",
            "bank_name",
            "filename",
            "header",
            "historical_values",
            "mapping",
            "note",
            "path",
            "period",
            "raw_text",
            "report_norm_id",
            "role_a",
            "schema",
            "scope",
            "statement_family",
            "title",
            "unit",
            "value",
        }
    )
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert {name for name in imported if name.startswith("bctc_ai.")} == {
        "bctc_ai.source_structure.adjacent_page_table_geometry_relations_v1",
        "bctc_ai.source_structure.contracts_v1",
    }
    assert not any(
        isinstance(node, ast.Constant) and type(node.value) is float for node in ast.walk(tree)
    )
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert (
        "build_adjacent_page_table_geometry_candidate_gate_from_relation_v1" not in function_names
    )
    assert function_names.intersection({"predict", "classify", "merge", "select_winner"}) == set()
    assert ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1["model_or_reader_invoked"] is False
    assert ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1["network_used"] is False
